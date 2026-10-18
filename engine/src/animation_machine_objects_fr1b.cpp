#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr1b_b(std::uint32_t value) {return value&255U;}
std::uint32_t ofr1b_w(std::uint32_t value) {return value&65535U;}
// The low WORD as a signed value (CMP.W / BGT on WORDs).
std::int32_t ofr1b_signed_word(std::uint32_t value) {
    const std::uint32_t w=value&65535U;return (w&0x8000U)!=0U?static_cast<std::int32_t>(w)-65536:static_cast<std::int32_t>(w);
}
bool ofr1b_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr1b_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG); the fall-through enters the installed callback.
bool ofr1b_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ofr1b_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVE.L #value,(A6) followed by the next block (not the installed value).
bool ofr1b_callback(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next) {
    if(!ofr1b_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next;return true;
}
// MOVE.W #value,d(A6) then MOVE.L #install,(A6) (the fall-through enters the installed value).
bool ofr1b_set_install(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,std::uint32_t install) {
    if(!ofr1b_put(c,c.s.a[6],displacement,2,value))return false;return ofr1b_install(c,install);
}
// ADDQ.W / SUBQ.W #k,d(A6) (WORD wrap; the flags are not read).
bool ofr1b_add_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t delta) {
    std::uint32_t value=0;if(!ofr1b_get(c,c.s.a[6],displacement,2,value))return false;return ofr1b_put(c,c.s.a[6],displacement,2,value+delta);
}
// SUBQ.W #1,d(A6); BEQ.W zero_pc / BNE.W (Z of the WORD result); otherwise other_pc.
bool ofr1b_tick(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr1b_get(c,c.s.a[6],displacement,2,value))return false;value=ofr1b_w(value-1U);
    if(!ofr1b_put(c,c.s.a[6],displacement,2,value))return false;c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// TST.W d(A6); BEQ.W zero_pc; otherwise other_pc.
bool ofr1b_test_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr1b_get(c,c.s.a[6],displacement,2,value))return false;c.s.pc=ofr1b_w(value)==0U?zero_pc:other_pc;return true;
}
// BTST.B #bit,d(A6); BEQ.W zero_pc (bit clear); otherwise set_pc.
bool ofr1b_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!ofr1b_get(c,c.s.a[6],displacement,1,value))return false;c.s.pc=((value>>bit)&1U)==0U?zero_pc:set_pc;return true;
}
// BSET.B #bit,d(A6) (only Z changes; Z is not read).
bool ofr1b_bset(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;if(!ofr1b_get(c,c.s.a[6],displacement,1,value))return false;return ofr1b_put(c,c.s.a[6],displacement,1,value|(1U<<bit));
}
// BCC / BCS on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ofr1b_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr1b caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #n,D0; JSR 28ae.l (28ae child).
bool ofr1b_28ae(AnimationMachineContext& c,std::uint32_t child,std::uint32_t n,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],n);return am_call(c,0x28ae,return_pc);
}
// MOVEQ #d012,D0; MOVEQ #d012,D1; MOVEQ #d012,D2; MOVEQ #d3,D3 (sign-extended LONGs); JSR 8c16.l.
bool ofr1b_8c16(AnimationMachineContext& c,std::uint32_t d012,std::uint32_t d3,std::uint32_t return_pc) {
    c.s.d[0]=d012;c.s.d[1]=d012;c.s.d[2]=d012;c.s.d[3]=d3;return am_call(c,0x8c16,return_pc);
}
// MOVEA.L #a1,A1; MOVE.W #100,D0; JSR 49f8c.l.
bool ofr1b_49f8c(AnimationMachineContext& c,std::uint32_t a1,std::uint32_t return_pc) {
    c.s.a[1]=a1;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L bank.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus).
bool ofr1b_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t bank,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr1b_put(c,c.s.a[6],0x20,2,n) || !am_read(c,bank,4,value) || !ofr1b_put(c,c.s.a[6],0x22,4,value))return false;
    am_word(c.s.d[0],0x100);c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr1b_get(c,c.s.a[6],0x22,4,value))return false;c.s.a[1]=value;
    if(!ofr1b_get(c,c.s.a[1],displacement,4,value))return false;c.s.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVEQ #ff,D1; MOVE.W #style,D1; MOVE.L #id,D7; MOVE.L #a00180,D0; MOVEQ #0,D5; JSR cd58.l (the fixed sprite of de15c / de1b4 / de210).
bool ofr1b_sprite_fixed(AnimationMachineContext& c,std::uint32_t return_pc) {
    c.s.d[1]=0xffff1500U;c.s.d[7]=0x2152;c.s.d[0]=0xa00180;c.s.d[5]=0;return am_call(c,0xcd58,return_pc);
}
// MOVEQ #ff,D1; MOVE.W #1600,D1; MOVE.L #2952,D7; MOVE.W 7a(A6),D0; SWAP D0; MOVE.W 7c(A6),D0; MOVEQ #0,D5; JSR cd58.l.
bool ofr1b_sprite_moving(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.d[1]=0xffff1600U;c.s.d[7]=0x2952;
    if(!ofr1b_get(c,c.s.a[6],0x7a,2,value))return false;am_word(c.s.d[0],value);am_swap(c.s.d[0]);
    if(!ofr1b_get(c,c.s.a[6],0x7c,2,value))return false;am_word(c.s.d[0],value);c.s.d[5]=0;return am_call(c,0xcd58,return_pc);
}
// MOVEQ #ff,D1; MOVE.W (A0)+,D1; BMI.W end_pc (N of the WORD); otherwise next_pc.
bool ofr1b_list_word(AnimationMachineContext& c,std::uint32_t end_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[0],2,value))return false;c.s.d[1]=0xffff0000U|ofr1b_w(value);c.s.a[0]+=2U;
    c.s.pc=(value&0x8000U)!=0U?end_pc:next_pc;return true;
}
// MOVE.L (A0)+,D7; MOVE.L #a00180,D0; MOVEQ #0,D5; MOVE.L A0,-(A7); JSR cd58.l.
bool ofr1b_list_sprite(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[0],4,value))return false;c.s.d[7]=value;c.s.a[0]+=4U;c.s.d[0]=0xa00180;c.s.d[5]=0;
    if(!am_push(c,4,c.s.a[0]))return false;return am_call(c,0xcd58,return_pc);
}
// MOVEA.L (A7)+,A0; BRA.B loop_pc.
bool ofr1b_list_pop(AnimationMachineContext& c,std::uint32_t loop_pc) {
    std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.a[0]=value;c.s.pc=loop_pc;return true;
}
// SUBQ.W #1,76(A6); BNE.W rts_pc; otherwise MOVE.L #install,(A6) (only installed) and the same RTS block.
bool ofr1b_step(AnimationMachineContext& c,std::uint32_t install_pc,std::uint32_t rts_pc) {
    std::uint32_t value=0;if(!ofr1b_get(c,c.s.a[6],0x76,2,value))return false;value=ofr1b_w(value-1U);
    if(!ofr1b_put(c,c.s.a[6],0x76,2,value))return false;c.s.pc=value!=0U?rts_pc:install_pc;return true;
}
// ASR.L #2 of a 32-bit value (arithmetic: the sign bit is replicated; no signed shift in C++).
std::uint32_t ofr1b_asr2(std::uint32_t value) {return (value>>2)|((value&0x80000000U)!=0U?0xc0000000U:0U);}
}
// Objects FR1b (211 block starts, contract docs/analysis/animation-machine-frontier-fr1b-contract.md): the IO-frontier objects 5a376 (N13 state;
// 5a376..5a460, 5a54e..5a5ba, installs 5a3c6 5a3e4 5a41e 5a43a 5a54e 5a574; the next state LONG of the table 5a5ba is only installed), b30f6
// (b30ba..b336a, b3460..b3484, installs b31dc b3246) with the helper e9112 / e9114 (e9112..e9148), the E-area demo / title objects de024 and de376
// (ddfdc..de00c, de024..de260, de2b6..de31e, de376..de3e6; installs de054 de0d8 de0ee de112 de15c de1a8 de1b4 de204 de210 de2b6 de2cc de3c2; de05e
// writes the PVC bank ports through am_zero_bank), the U05 end state b97c0 (b97c0..b9822, install b97ee) and the HUD list sibling 515fc
// (515fc..51602). Every exit is routed. Known C: b3474 (ORI.B #1,CCR; RTS) Set and b347e (ANDI.B #fe,CCR; RTS) Clear for the consumer b31f4;
// b32ea b331c b334e (ORI) Set without a reader. The 11 consumers 5a3f8 (5ab5a) 5a58e (BCS, 4945e) b30ea b335e b9816 (1ab02) b31f4 (b3460) b3470
// (493bc) b32d8 b330a b333c (28ae) b97fa (49fc6) read a known C or fail. Data through the live bus (no limit test, as in the original): the LONG
// table 5a5ba, the bank-window LONGs 20017c / 2001d0 / 20000c and the LONGs behind them, the LONG table de34e, the WORD / LONG list (A0)+ (de3e6).
bool animation_objects_fr1b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    case 0xb30ee:case 0xb3352:case 0xb3362:r.pc=0x2a00;return true;                          // JMP 2a00.l.
    case 0xb981a:r.pc=0x2a24;return true;                                                     // JMP 2a24.l.
    case 0x5a41a:case 0x5a45c:r.pc=0x5a9c2;return true;                                       // BRA.W 5a9c2.
    case 0xb30f4:case 0xb3368:case 0xb9820:case 0xde00a:case 0xde05c:case 0xde0e0:case 0xde0f6:case 0xde11a:case 0xde1a6:case 0xde202:
    case 0xde25e:case 0xde31c:case 0xde3e4:
        return am_return(c);                                                                  // RTS.
    // ---- 515fc: LEA 5160e(PC),A0; BRA.B 515e0 (the FR1a HUD list loop).
    case 0x515fc:r.a[0]=0x5160e;r.pc=0x515e0;return true;
    // ---- 5a376 (N13 installed state): MOVE.L #5a376,98(A6); BTST.B #1,80(A6); BNE.W 5a39c.
    case 0x5a376:if(!ofr1b_put(c,r.a[6],0x98,4,0x5a376))return false;return ofr1b_bit(c,0x80,1,0x5a388,0x5a39c);
    case 0x5a388:r.a[0]=0x5dd3e;return am_call(c,0x490ba,0x5a394);                           // LEA 5dd3e.l,A0; JSR 490ba.l.
    case 0x5a39c:r.a[0]=0x5dd88;return am_call(c,0x490ba,0x5a3a8);                           // LEA 5dd88.l,A0; JSR 490ba.l.
    case 0x5a394:case 0x5a3a8:if(!ofr1b_put(c,r.a[6],0x8c,1,r.d[0]))return false;r.pc=0x5a3ac;return true;   // MOVE.B D0,8c(A6) (BRA.W / fall-through 5a3ac).
    case 0x5a3ac:return am_call(c,0x496c2,0x5a3b2);                                           // JSR 496c2.l.
    case 0x5a568:return am_call(c,0x496c2,0x5a56e);
    case 0x5a3b2:return ofr1b_49f8c(c,0x5b784,0x5a3c2);                                       // MOVEA.L #5b784,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x5a3c6:return ofr1b_49f8c(c,0x5b7ea,0x5a3d6);                                       // (installed value)
    case 0x5a41e:return ofr1b_49f8c(c,0x5b66e,0x5a42e);                                       // (installed value)
    case 0x5a558:return ofr1b_49f8c(c,0x5b66e,0x5a568);
    case 0x5a3c2:r.pc=0x5a3d6;return true;                                                    // BRA.W 5a3d6.
    // CLR.B 9c(A6); SUBQ.B #1,8c(A6); MOVE.L #5a3e4,(A6).
    case 0x5a3d6:
        if(!ofr1b_put(c,r.a[6],0x9c,1,0) || !ofr1b_get(c,r.a[6],0x8c,1,value) || !ofr1b_put(c,r.a[6],0x8c,1,value-1U))return false;
        return ofr1b_install(c,0x5a3e4);
    case 0x5a3e4:return ofr1b_bit(c,0x80,0,0x5a3ee,0x5a802);                                  // BTST.B #0,80(A6); BNE.W 5a802 (installed values).
    case 0x5a43a:return ofr1b_bit(c,0x80,0,0x5a444,0x5a802);
    case 0x5a574:return ofr1b_bit(c,0x80,0,0x5a57e,0x5a802);
    case 0x5a3ee:case 0x5a444:case 0x5a57e:return am_call(c,0x43ea4,r.pc+6U);                // JSR 43ea4.l.
    case 0x5a3f4:case 0x5a44a:case 0x5a584:return am_call(c,0x5ab5a,r.pc+4U);                // BSR.W 5ab5a.
    case 0x5a3f8:return ofr1b_carry(c,0x5a402,0x5a3fc);                                       // BCC.W 5a402 (C of 5ab5a).
    case 0x5a3fc:return ofr1b_callback(c,0x5a41e,0x5a402);                                    // MOVE.L #5a41e,(A6).
    // TST.B 8c(A6); SNE.B D0; TST.B 9c(A6); SNE.B D1; AND.B D0,D1; BEQ.W 5a41a.
    case 0x5a402:
        if(!ofr1b_get(c,r.a[6],0x8c,1,value) || !ofr1b_get(c,r.a[6],0x9c,1,other))return false;
        am_byte(r.d[0],ofr1b_b(value)!=0U?0xffU:0U);am_byte(r.d[1],ofr1b_b(other)!=0U?0xffU:0U);am_byte(r.d[1],r.d[1]&r.d[0]);
        r.pc=ofr1b_b(r.d[1])==0U?0x5a41a:0x5a414;return true;
    case 0x5a414:return ofr1b_callback(c,0x5a3c6,0x5a41a);                                    // MOVE.L #5a3c6,(A6).
    case 0x5a42e:return ofr1b_set_install(c,0x84,0x10,0x5a43a);                               // MOVE.W #10,84(A6); MOVE.L #5a43a,(A6).
    case 0x5a44e:return ofr1b_tick(c,0x84,0x5a456,0x5a45c);                                   // SUBQ.W #1,84(A6); BNE.W 5a45c.
    case 0x5a456:return ofr1b_callback(c,0x5a54e,0x5a45c);                                    // MOVE.L #5a54e,(A6).
    case 0x5a54e:am_word(r.d[0],0x743);return am_call(c,0x3af8,0x5a558);                     // MOVE.W #743,D0; JSR 3af8.l (installed value).
    case 0x5a56e:return ofr1b_install(c,0x5a574);                                             // MOVE.L #5a574,(A6).
    case 0x5a588:return am_call(c,0x4945e,0x5a58e);                                           // JSR 4945e.l.
    case 0x5a58e:return ofr1b_carry(c,0x5a592,0x5a9c2);                                       // BCS.W 5a9c2 (C of 4945e).
    case 0x5a592:am_word(r.d[7],5);r.pc=0x5a596;return true;                                 // MOVE.W #5,D7.
    case 0x5a596:return am_call(c,0x49a58,0x5a59c);                                           // JSR 49a58.l.
    // ANDI.W #3,D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L 5a5ba(PC,D0.W),A0; SUBQ.W #1,D7; BEQ.W 5a5b4.
    case 0x5a59c:
        am_word(r.d[0],(r.d[0]&3U)*4U);if(!am_read(c,am_index(0x5a5ba,r.d[0]),4,value))return false;r.a[0]=value;
        am_word(r.d[7],r.d[7]-1U);r.pc=ofr1b_w(r.d[7])==0U?0x5a5b4:0x5a5ae;return true;
    case 0x5a5ae:if(!ofr1b_get(c,r.a[6],0x98,4,value))return false;r.pc=r.a[0]==value?0x5a596:0x5a5b4;return true;   // CMPA.L 98(A6),A0; BEQ.B 5a596.
    case 0x5a5b4:if(!ofr1b_put(c,r.a[6],0,4,r.a[0]))return false;r.pc=0x5a9c2;return true;   // MOVE.L A0,(A6); BRA.W 5a9c2.
    // ---- b30f6 (node callback): MOVEQ #0,D0; MOVE.W 7c(A6),D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,82(A6); TST.W 78(A6); BNE.W b3114.
    case 0xb30f6:
        if(!ofr1b_get(c,r.a[6],0x7c,2,value))return false;r.d[0]=am_extend_word(value)<<8;
        if(!ofr1b_put(c,r.a[6],0x82,4,r.d[0]))return false;return ofr1b_test_word(c,0x78,0xb310c,0xb3114);
    case 0xb310c:if(!ofr1b_put(c,r.a[6],0x3a,4,r.d[0]))return false;r.pc=0xb3118;return true;   // MOVE.L D0,3a(A6); BRA.W b3118.
    case 0xb3114:if(!ofr1b_put(c,r.a[6],0x36,4,r.d[0]))return false;r.pc=0xb3118;return true;   // MOVE.L D0,36(A6).
    case 0xb3118:return ofr1b_test_word(c,0x7a,0xb3130,0xb3120);                              // TST.W 7a(A6); BEQ.W b3130.
    // BSET.B #0,15(A6); MOVE.L 36(A6),D0; NEG.L D0; MOVE.L D0,36(A6).
    case 0xb3120:
        if(!ofr1b_bset(c,0x15,0) || !ofr1b_get(c,r.a[6],0x36,4,value))return false;r.d[0]=0U-value;
        if(!ofr1b_put(c,r.a[6],0x36,4,r.d[0]))return false;r.pc=0xb3130;return true;
    // MOVE.W #8800,68(A6); MOVE.W #8800,1e(A6); MOVE.W #5e,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xb3130:
        if(!ofr1b_put(c,r.a[6],0x68,2,0x8800) || !ofr1b_put(c,r.a[6],0x1e,2,0x8800))return false;
        am_word(r.d[0],0x5e);am_word(r.d[1],1);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xb314e);
    case 0xb314e:return ofr1b_test_word(c,0x76,0xb3156,0xb3164);                              // TST.W 76(A6); BNE.W b3164.
    case 0xb3156:if(!ofr1b_put(c,r.a[6],0x54,2,0xc8))return false;am_word(r.d[0],4);r.pc=0xb316e;return true;   // MOVE.W #c8,54(A6); MOVE.W #4,D0; BRA.W.
    case 0xb3164:if(!ofr1b_put(c,r.a[6],0x54,2,0x64))return false;am_word(r.d[0],1);r.pc=0xb316e;return true;   // MOVE.W #64,54(A6); MOVE.W #1,D0.
    // LEA 26(A6),A0; MOVE.W #15b,20(A6); MOVE.L 20017c.l,22(A6); LEA 26(A6),A0; MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 20017c.l,A1;
    // MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xb316e:
        r.a[0]=r.a[6]+0x26U;if(!ofr1b_put(c,r.a[6],0x20,2,0x15b) || !am_read(c,0x20017c,4,value) || !ofr1b_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[1],r.d[0]*4U);if(!am_read(c,0x20017c,4,value))return false;r.a[1]=value;
        if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xb319e);
    case 0xb319e:return ofr1b_28ae(c,0xb336a,0xa,0xb31ae);                                    // MOVEA.L #b336a,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0xb31ae:r.d[0]=0;am_word(r.d[1],0);return am_call(c,0x49214,0xb31ba);               // MOVEQ #0,D0; MOVE.W #0,D1; JSR 49214.l.
    case 0xb31ba:return am_call(c,0x491b6,0xb31c0);                                           // JSR 491b6.l.
    case 0xb31c0:return ofr1b_28ae(c,0xb33d8,0xa,0xb31d0);
    case 0xb31d0:return am_call(c,0x491b6,0xb31d6);
    case 0xb31d6:return ofr1b_install(c,0xb31dc);                                             // MOVE.L #b31dc,(A6).
    case 0xb31dc:return ofr1b_test_word(c,0x76,0xb3218,0xb31e4);                              // TST.W 76(A6); BEQ.W b3218 (installed value).
    case 0xb31e4:return ofr1b_test_word(c,0x80,0xb3218,0xb31ec);                              // TST.W 80(A6); BEQ.W b3218.
    case 0xb31ec:if(!ofr1b_add_word(c,0x80,0xffffU))return false;return am_call(c,0xb3460,0xb31f4);   // SUBQ.W #1,80(A6); JSR b3460(PC).
    case 0xb31f4:return ofr1b_carry(c,0xb3218,0xb31f8);                                       // BCC.W b3218 (C of b3460).
    // MOVE.L 82(A6),D1; MOVE.W 46(A0),D0; SUB.W 46(A6),D0; BPL.W b320c.
    case 0xb31f8:
        if(!ofr1b_get(c,r.a[6],0x82,4,value))return false;r.d[1]=value;
        if(!ofr1b_get(c,r.a[0],0x46,2,value) || !ofr1b_get(c,r.a[6],0x46,2,other))return false;am_word(r.d[0],value-other);
        r.pc=(r.d[0]&0x8000U)==0U?0xb320c:0xb3208;return true;
    case 0xb3208:r.d[1]=0U-r.d[1];am_word(r.d[0],0U-r.d[0]);r.pc=0xb320c;return true;        // NEG.L D1; NEG.W D0.
    // CMP.W 7e(A6),D0; BGT.W b3218 (signed D0.W > WORD).
    case 0xb320c:if(!ofr1b_get(c,r.a[6],0x7e,2,value))return false;r.pc=ofr1b_signed_word(r.d[0])>ofr1b_signed_word(value)?0xb3218:0xb3214;return true;
    case 0xb3214:if(!ofr1b_put(c,r.a[6],0x3a,4,r.d[1]))return false;r.pc=0xb3218;return true;   // MOVE.L D1,3a(A6).
    case 0xb3218:return am_call(c,0x43ea4,0xb321e);                                           // JSR 43ea4.l.
    case 0xb321e:return am_call(c,0x49fc6,0xb3224);                                           // JSR 49fc6.l.
    case 0xb3224:if(!ofr1b_get(c,r.a[6],0x72,4,value))return false;r.d[0]=value;r.pc=value==0U?0xb3234:0xb322c;return true;   // MOVE.L 72(A6),D0; BEQ.W.
    case 0xb322c:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0xb3234);                            // MOVEA.L D0,A0; JSR 4ae4a.l.
    case 0xb3234:r.pc=ofr1b_w(r.d[0])==0U?0xb3242:0xb323c;return true;                       // CMPI.W #0,D0; BEQ.W b3242.
    case 0xb323c:return ofr1b_callback(c,0xb3246,0xb3242);                                    // MOVE.L #b3246,(A6).
    case 0xb3242:r.pc=0xb30ba;return true;                                                    // BRA.W b30ba.
    case 0xb30ba:return am_call(c,0x4b54e,0xb30c0);                                           // JSR 4b54e.l.
    case 0xb30c0:return ofr1b_bit(c,0x61,7,0xb30d0,0xb30ca);                                  // BTST.B #7,61(A6); BEQ.W b30d0.
    case 0xb30ca:return ofr1b_callback(c,0xb3246,0xb30d0);                                    // MOVE.L #b3246,(A6).
    case 0xb30d0:return ofr1b_test_word(c,0x76,0xb30d8,0xb30e0);                              // TST.W 76(A6); BNE.W b30e0.
    case 0xb32a2:return ofr1b_test_word(c,0x76,0xb32aa,0xb32b2);
    case 0xb30d8:r.a[0]=0xb30aa;r.pc=0xb30e4;return true;                                    // LEA b30aa(PC),A0; BRA.W b30e4.
    case 0xb30e0:r.a[0]=0xb30b2;r.pc=0xb30e4;return true;                                    // LEA b30b2(PC),A0.
    case 0xb32aa:r.a[0]=0xb30aa;r.pc=0xb32b6;return true;
    case 0xb32b2:r.a[0]=0xb30b2;r.pc=0xb32b6;return true;
    case 0xb30e4:return am_call(c,0x1ab02,0xb30ea);                                           // JSR 1ab02.l.
    case 0xb3358:return am_call(c,0x1ab02,0xb335e);
    case 0xb30ea:return ofr1b_carry(c,0xb30f4,0xb30ee);                                       // BCC.W b30f4 (C of 1ab02).
    case 0xb335e:return ofr1b_carry(c,0xb3368,0xb3362);                                       // BCC.W b3368 (C of 1ab02).
    case 0xb3246:return am_call(c,0xe9112,0xb324c);                                           // JSR e9112.l (installed value).
    // BSET.B #3,61(A6); SUBI.L #4000,36(A6); MOVE.L 3a(A6),82(A6); JSR 4be2c.l.
    case 0xb324c:
        if(!ofr1b_bset(c,0x61,3) || !ofr1b_get(c,r.a[6],0x36,4,value) || !ofr1b_put(c,r.a[6],0x36,4,value-0x4000U) ||
           !ofr1b_get(c,r.a[6],0x3a,4,value) || !ofr1b_put(c,r.a[6],0x82,4,value))return false;
        return am_call(c,0x4be2c,0xb3266);
    case 0xb3266:return ofr1b_bit(c,0x15,7,0xb3284,0xb3270);                                  // BTST.B #7,15(A6); BEQ.W b3284.
    // MOVE.L 82(A6),D0; NEG.L D0; MOVE.L D0,3a(A6); MOVE.L 36(A6),D0; ASR.L #2,D0; SUB.L D0,36(A6).
    case 0xb3270:
        if(!ofr1b_get(c,r.a[6],0x82,4,value))return false;r.d[0]=0U-value;if(!ofr1b_put(c,r.a[6],0x3a,4,r.d[0]))return false;
        if(!ofr1b_get(c,r.a[6],0x36,4,value))return false;r.d[0]=ofr1b_asr2(value);
        if(!ofr1b_put(c,r.a[6],0x36,4,value-r.d[0]))return false;r.pc=0xb3284;return true;
    case 0xb3284:return ofr1b_test_word(c,0x76,0xb328c,0xb3296);                              // TST.W 76(A6); BNE.W b3296.
    case 0xb328c:if(!ofr1b_put(c,r.a[6],0x86,2,0x1e))return false;r.pc=0xb329c;return true;  // MOVE.W #1e,86(A6); BRA.W b329c.
    case 0xb3296:if(!ofr1b_put(c,r.a[6],0x86,2,0x14))return false;r.pc=0xb329c;return true;  // MOVE.W #14,86(A6).
    case 0xb329c:return am_call(c,0x49fc6,0xb32a2);                                           // JSR 49fc6.l.
    // MOVE.W 86(A6),D0; BEQ.W b3358.
    case 0xb32b6:if(!ofr1b_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],value);r.pc=ofr1b_w(value)==0U?0xb3358:0xb32be;return true;
    case 0xb32be:am_word(r.d[0],r.d[0]-1U);r.pc=ofr1b_w(r.d[0])!=0x14U?0xb32f2:0xb32c8;return true;   // SUBQ.W #1,D0; CMPI.W #14,D0; BNE.W b32f2.
    case 0xb32f2:r.pc=ofr1b_w(r.d[0])!=0xaU?0xb3324:0xb32fa;return true;                     // CMPI.W #a,D0; BNE.W b3324.
    case 0xb3324:r.pc=ofr1b_w(r.d[0])!=5U?0xb3358:0xb332c;return true;                       // CMPI.W #5,D0; BNE.W b3358.
    case 0xb32c8:return ofr1b_28ae(c,0xd1d08,0x1e,0xb32d8);                                   // MOVEA.L #d1d08,A0; MOVE.W #1e,D0; JSR 28ae.l.
    case 0xb32fa:return ofr1b_28ae(c,0xd1d08,0x1e,0xb330a);
    case 0xb332c:return ofr1b_28ae(c,0xd1d38,0x1e,0xb333c);
    case 0xb32d8:return ofr1b_carry(c,0xb32ee,0xb32dc);                                       // BCC.W b32ee (C of 28ae).
    case 0xb330a:return ofr1b_carry(c,0xb3320,0xb330e);
    case 0xb333c:return ofr1b_carry(c,0xb3352,0xb3340);
    case 0xb32dc:am_word(r.d[0],0x60);am_word(r.d[1],0);return am_call(c,0x4970a,0xb32ea);   // MOVE.W #60,D0; MOVE.W #0,D1; JSR 4970a.l.
    case 0xb330e:am_word(r.d[0],0x30);am_word(r.d[1],0);return am_call(c,0x4970a,0xb331c);
    case 0xb3340:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0xb334e);
    case 0xb32ea:case 0xb331c:case 0xb334e:r.carry=AnimationCarrySet;r.pc=r.pc+4U;return true; // ORI.B #1,CCR (no reader).
    case 0xb32ee:case 0xb3320:r.pc=0xb3358;return true;                                      // BRA.W b3358.
    // ---- b3460: MOVE.L 88(A6),D0; BMI.W b347e / MOVEA.L D0,A0; JSR 493bc.l / BCC.W b347e / MOVEA.L 88(A6),A0; ORI.B #1,CCR; RTS / ANDI.B #fe,CCR; RTS.
    case 0xb3460:if(!ofr1b_get(c,r.a[6],0x88,4,value))return false;r.d[0]=value;r.pc=(value&0x80000000U)!=0U?0xb347e:0xb3468;return true;
    case 0xb3468:r.a[0]=r.d[0];return am_call(c,0x493bc,0xb3470);
    case 0xb3470:return ofr1b_carry(c,0xb347e,0xb3474);                                       // BCC.W b347e (C of 493bc).
    case 0xb3474:if(!ofr1b_get(c,r.a[6],0x88,4,value))return false;r.a[0]=value;r.carry=AnimationCarrySet;return am_return(c);
    case 0xb347e:r.carry=AnimationCarryClear;return am_return(c);
    // ---- e9112: MOVEQ #ff,D0 / e9114 (JSR entry of d6664 e9106): LEA 5e30(A5),A1; MOVEQ #0,D1; MOVE.B 6b(A6),D1; CMPI.B #c,D1; BCC.W e912a.
    case 0xe9112:r.d[0]=0xffffffffU;r.pc=0xe9114;return true;
    case 0xe9114:
        r.a[1]=r.a[5]+0x5e30U;if(!ofr1b_get(c,r.a[6],0x6b,1,value))return false;r.d[1]=ofr1b_b(value);r.pc=r.d[1]>=0xcU?0xe912a:0xe9126;return true;
    // SUBQ.B #1,(A1,D1.W).
    case 0xe9126:other=am_index(r.a[1],r.d[1]);if(!am_read(c,other,1,value) || !am_write(c,other,1,ofr1b_b(value-1U)))return false;r.pc=0xe912a;return true;
    case 0xe912a:r.pc=ofr1b_b(r.d[0])>=0xcU?0xe913e:0xe9132;return true;                     // CMPI.B #c,D0; BCC.W e913e.
    // ANDI.W #ff,D0; ADDQ.B #1,(A1,D0.W); BRA.W e9140.
    case 0xe9132:
        am_word(r.d[0],r.d[0]&0xffU);other=am_index(r.a[1],r.d[0]);
        if(!am_read(c,other,1,value) || !am_write(c,other,1,ofr1b_b(value+1U)))return false;r.pc=0xe9140;return true;
    case 0xe913e:r.d[0]=0xffffffffU;r.pc=0xe9140;return true;                                // MOVEQ #ff,D0.
    case 0xe9140:if(!ofr1b_put(c,r.a[6],0x6b,1,r.d[0]))return false;r.pc=0xe932c;return true; // MOVE.B D0,6b(A6); BRA.W e932c.
    // ---- b97c0 (U05 installed value): bank animation 2001d0 / 50; MOVE.L #b97ee,(A6).
    case 0xb97c0:return ofr1b_bank_anim(c,0x203,0x2001d0,0x50,0xb97e8);
    case 0xb97e8:return ofr1b_install(c,0xb97ee);
    case 0xb97ee:return am_call(c,0x43e34,0xb97f4);                                           // JSR 43e34.l (installed value).
    case 0xb97f4:return am_call(c,0x49fc6,0xb97fa);                                           // JSR 49fc6.l.
    case 0xb97fa:return ofr1b_carry(c,0xb980a,0xb97fe);                                       // BCC.W b980a (C of 49fc6).
    case 0xb97fe:if(!ofr1b_put(c,r.a[6],0x76,2,0))return false;return ofr1b_callback(c,0xb970e,0xb980a);   // MOVE.W #0,76(A6); MOVE.L #b970e,(A6).
    case 0xb980a:r.a[0]=0xba3d6;return am_call(c,0x1ab02,0xb9816);                           // LEA ba3d6.l,A0; JSR 1ab02.l.
    case 0xb9816:return ofr1b_carry(c,0xb9820,0xb981a);                                       // BCC.W b9820 (C of 1ab02).
    // ---- ddfdc: LEA ddf7c(PC),A0; CMPI.B #0,-7fff(A5); BEQ.W ddfee / ddfea: LEA ddf5e(PC),A0.
    case 0xddfdc:r.a[0]=0xddf7c;if(!ofr1b_get(c,r.a[5],0x8001,1,value))return false;r.pc=ofr1b_b(value)==0U?0xddfee:0xddfea;return true;
    case 0xddfea:r.a[0]=0xddf5e;r.pc=0xddfee;return true;
    case 0xddfee:return am_call(c,0xe89da,0xddff4);                                           // JSR e89da.l.
    // MOVE.W #717b,D0; MOVE.W #e317,D1; MOVE.W #1,D2; MOVE.W #1,D3; JSR 35f0.l.
    case 0xddff4:am_word(r.d[0],0x717b);am_word(r.d[1],0xe317);am_word(r.d[2],1);am_word(r.d[3],1);return am_call(c,0x35f0,0xde00a);
    // ---- de024 (C3 28ae child) / de11c / de380: MOVEA.W #0,A0; JSR 43ffc.l.
    case 0xde024:case 0xde11c:case 0xde380:r.a[0]=0;return am_call(c,0x43ffc,r.pc+0xaU);
    case 0xde02e:case 0xde38a:return am_call(c,0xcaf0,r.pc+6U);                               // JSR caf0.l.
    case 0xde034:case 0xde126:case 0xde390:return am_call(c,0xe7c16,r.pc+6U);                // JSR e7c16.l.
    case 0xde03a:return ofr1b_8c16(c,0xffffffe1U,0,0xde048);                                  // MOVEQ #e1,D0/D1/D2; MOVEQ #0,D3; JSR 8c16.l.
    case 0xde0be:return ofr1b_8c16(c,0,8,0xde0cc);
    case 0xde0f8:return ofr1b_8c16(c,0xffffffe1U,8,0xde106);
    case 0xde136:return ofr1b_8c16(c,0,0,0xde144);
    case 0xde3a0:return ofr1b_8c16(c,0,0,0xde3ae);
    case 0xde048:return ofr1b_set_install(c,0x76,2,0xde054);                                  // MOVE.W #2,76(A6); MOVE.L #de054,(A6).
    case 0xde0cc:return ofr1b_set_install(c,0x76,0x3c,0xde0d8);
    case 0xde0e2:return ofr1b_set_install(c,0x76,0x3c,0xde0ee);
    case 0xde106:return ofr1b_set_install(c,0x76,0x14,0xde112);
    case 0xde054:return ofr1b_tick(c,0x76,0xde05e,0xde05c);                                   // SUBQ.W #1,76(A6); BEQ.W (installed values).
    case 0xde0d8:return ofr1b_tick(c,0x76,0xde0e2,0xde0e0);
    case 0xde0ee:return ofr1b_tick(c,0x76,0xde0f8,0xde0f6);
    case 0xde112:return ofr1b_tick(c,0x76,0xde11c,0xde11a);
    // MOVE.W #3b,D0; MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.l; MOVE.W #0,2ffff0.l (am_zero_bank); MOVEA.L 20000c.l,A0; LSL.W #2,D0;
    // MOVEA.L (A0,D0.W),A0; JSR 8da2.l (the bank-window LONG is read after the bank write).
    case 0xde05e:
        am_word(r.d[0],0x3b);if(!am_zero_bank(c) || !am_read(c,0x20000c,4,value))return false;r.a[0]=value;am_word(r.d[0],r.d[0]<<2);
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;return am_call(c,0x8da2,0xde08a);
    case 0xde08a:r.a[0]=0xde00c;return am_call(c,0x43ffc,0xde094);                           // LEA de00c(PC),A0; JSR 43ffc.l.
    case 0xde094:r.a[0]=0x109156;return am_call(c,0x16fac,0xde0a0);                          // LEA 109156.l,A0; JSR 16fac.l.
    // LEA de01c(PC),A1; MOVEA.W #0,A2; MOVEQ #0,D0; MOVEQ #1f,D1; JSR 16ff8.l.
    case 0xde0a0:r.a[1]=0xde01c;r.a[2]=0;r.d[0]=0;r.d[1]=0x1f;return am_call(c,0x16ff8,0xde0b2);
    case 0xde0b2:return am_call(c,0x1861a,0xde0b8);                                           // JSR 1861a.l.
    case 0xde0b8:return am_call(c,0x17012,0xde0be);                                           // JSR 17012.l.
    case 0xde12c:case 0xde396:r.a[0]=0xddf08;return am_call(c,0x8da2,r.pc+0xaU);             // LEA ddf08(PC),A0; JSR 8da2.l.
    // MOVE.W #0,7a(A6); MOVE.W #1b8,7c(A6); MOVE.W #1e,76(A6); MOVE.L #de15c,(A6).
    case 0xde144:if(!ofr1b_put(c,r.a[6],0x7a,2,0) || !ofr1b_put(c,r.a[6],0x7c,2,0x1b8))return false;return ofr1b_set_install(c,0x76,0x1e,0xde15c);
    case 0xde15c:case 0xde1b4:case 0xde210:return ofr1b_sprite_fixed(c,r.pc+0x1aU);         // (installed values) ...; JSR cd58.l.
    case 0xde176:case 0xde1ce:case 0xde22a:return ofr1b_sprite_moving(c,r.pc+0x1eU);
    case 0xde194:if(!ofr1b_add_word(c,0x7a,8))return false;return ofr1b_step(c,0xde1a0,0xde1a6);   // ADDQ.W #8,7a(A6); SUBQ.W #1,76(A6); BNE.W de1a6.
    case 0xde1ec:                                                                             // SUBQ.W #4,7a(A6); SUBQ.W #4,7c(A6); SUBQ.W #1,76(A6); BNE.W de202.
        if(!ofr1b_add_word(c,0x7a,0xfffcU) || !ofr1b_add_word(c,0x7c,0xfffcU))return false;return ofr1b_step(c,0xde1fc,0xde202);
    case 0xde248:                                                                             // ADDQ.W #6,7a(A6); ADDQ.W #6,7c(A6); SUBQ.W #1,76(A6); BNE.W de25e.
        if(!ofr1b_add_word(c,0x7a,6) || !ofr1b_add_word(c,0x7c,6))return false;return ofr1b_step(c,0xde258,0xde25e);
    case 0xde1a0:return ofr1b_callback(c,0xde1a8,0xde1a6);                                    // MOVE.L #de1a8,(A6).
    case 0xde1fc:return ofr1b_callback(c,0xde204,0xde202);
    case 0xde258:return ofr1b_callback(c,0xde2b6,0xde25e);
    case 0xde1a8:return ofr1b_set_install(c,0x76,0x1e,0xde1b4);                               // MOVE.W #1e,76(A6); MOVE.L #de1b4,(A6) (installed value).
    case 0xde204:return ofr1b_set_install(c,0x76,0x14,0xde210);
    case 0xde2b6:am_word(r.d[0],0x74b);return am_call(c,0x3af8,0xde2c0);                     // MOVE.W #74b,D0; JSR 3af8.l (installed value).
    case 0xde2c0:return ofr1b_set_install(c,0x78,0,0xde2cc);                                  // MOVE.W #0,78(A6); MOVE.L #de2cc,(A6).
    // LEA de34e(PC),A0; MOVEQ #ff,D1; MOVE.W #1800,D1; MOVE.W 78(A6),D7; ADD.W D7,D7; ADD.W D7,D7; MOVE.L (A0,D7.W),D7; BMI.W de3ae.
    case 0xde2cc:
        r.a[0]=0xde34e;r.d[1]=0xffff1800U;if(!ofr1b_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[7],value*4U);
        if(!am_read(c,am_index(r.a[0],r.d[7]),4,value))return false;r.d[7]=value;r.pc=(value&0x80000000U)!=0U?0xde3ae:0xde2e6;return true;
    case 0xde2e6:r.d[0]=0xa00180;am_word(r.d[5],0x1000);return am_call(c,0xcd58,0xde2f6);   // MOVE.L #a00180,D0; MOVE.W #1000,D5; JSR cd58.l.
    case 0xde2f6:if(!ofr1b_add_word(c,0x78,1))return false;r.a[0]=0xde3e6;r.pc=0xde2fe;return true;   // ADDQ.W #1,78(A6); LEA de3e6(PC),A0.
    case 0xde2fe:return ofr1b_list_word(c,0xde31c,0xde306);                                   // MOVEQ #ff,D1; MOVE.W (A0)+,D1; BMI.W de31c.
    case 0xde3c6:return ofr1b_list_word(c,0xde3e4,0xde3ce);
    case 0xde306:return ofr1b_list_sprite(c,0xde318);                                         // MOVE.L (A0)+,D7; ...; MOVE.L A0,-(A7); JSR cd58.l.
    case 0xde3ce:return ofr1b_list_sprite(c,0xde3e0);
    case 0xde318:return ofr1b_list_pop(c,0xde2fe);                                            // MOVEA.L (A7)+,A0; BRA.B de2fe.
    case 0xde3e0:return ofr1b_list_pop(c,0xde3c6);
    // ---- de376 (C3 28ae child): MOVE.B #2,D0; JSR 101c.l.
    case 0xde376:am_byte(r.d[0],2);return am_call(c,0x101c,0xde380);
    case 0xde3ae:return am_call(c,0xddfdc,0xde3b2);                                           // BSR.W ddfdc.
    // MOVEA.L c(A6),A0; MOVE.B #1,62(A0); MOVE.L #de3c2,(A6).
    case 0xde3b2:if(!ofr1b_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr1b_put(c,r.a[0],0x62,1,1))return false;return ofr1b_install(c,0xde3c2);
    case 0xde3c2:r.a[0]=0xde3e6;r.pc=0xde3c6;return true;                                    // LEA de3e6(PC),A0 (installed value).
    default:return am_error(c,"unsupported animation objects fr1b PC");
    }
}
}
