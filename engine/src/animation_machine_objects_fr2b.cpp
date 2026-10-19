#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr2b_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ofr2b_b(std::uint32_t value) {return value&255U;}
// ASR.L #count (1..8) of a 32-bit value: arithmetic, the sign bit is replicated (no signed shift in C++).
std::uint32_t ofr2b_asr_long(std::uint32_t value,unsigned int count) {
    const std::uint32_t fill=(value&0x80000000U)!=0U?~(0xffffffffU>>count):0U;return (value>>count)|fill;
}
bool ofr2b_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr2b_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG) whose fall-through is the installed callback itself: enter it.
bool ofr2b_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ofr2b_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVE.L #value,(A6) that only writes the callback LONG for a later frame (contract decision 2); then next_pc.
bool ofr2b_callback(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr2b_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// BCC / BCS on a known C (returned by a callee): clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ofr2b_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr2b caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ORI.B #1,CCR / ANDI.B #fe,CCR; RTS.
bool ofr2b_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// BTST.B #bit,d(An); BEQ.W zero_pc (bit clear); otherwise set_pc.
bool ofr2b_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!ofr2b_get(c,base,displacement,1,value))return false;c.s.pc=((value>>bit)&1U)==0U?zero_pc:set_pc;return true;
}
// TST.W / TST.B d(A6); BNE.W nonzero_pc (otherwise zero_pc).
bool ofr2b_test(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t nonzero_pc) {
    std::uint32_t value=0;if(!ofr2b_get(c,c.s.a[6],displacement,size,value))return false;c.s.pc=value!=0U?nonzero_pc:zero_pc;return true;
}
// BSET / BCLR / BCHG.B #bit,d(An) (the Z it leaves is never read).
bool ofr2b_set_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int mode) {
    std::uint32_t value=0;if(!ofr2b_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;const std::uint32_t next=mode==0U?(value|mask):(mode==1U?(value&~mask):(value^mask));
    return ofr2b_put(c,base,displacement,1,next);
}
// MOVE.W #value,d(A6); then next_pc.
bool ofr2b_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr2b_put(c,c.s.a[6],displacement,2,value))return false;c.s.pc=next_pc;return true;
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus).
bool ofr2b_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr2b_put(c,c.s.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr2b_put(c,c.s.a[6],0x22,4,value))return false;
    am_word(c.s.d[0],0x100);c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr2b_get(c,c.s.a[6],0x22,4,value))return false;c.s.a[1]=value;
    if(!ofr2b_get(c,c.s.a[1],displacement,4,value))return false;c.s.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #d0,D0; MOVE.W #d1,D1; MOVE.B #0,D2; JSR c6a96.l.
bool ofr2b_c6a96(AnimationMachineContext& c,std::uint32_t d0,std::uint32_t d1,std::uint32_t return_pc) {
    am_word(c.s.d[0],d0);am_word(c.s.d[1],d1);am_byte(c.s.d[2],0);return am_call(c,0xc6a96,return_pc);
}
// MOVE.W #sound,D0; MOVE.B #0,D1; JSR 8ebe.l.
bool ofr2b_sound(AnimationMachineContext& c,std::uint32_t sound,std::uint32_t return_pc) {
    am_word(c.s.d[0],sound);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// ADD.B D2,D2 (X := the old bit 7); SUBX.W D3,D1 (D1.W - D3.W - X; C := the unsigned borrow). Returns the C read by the following BCS.W 703f4.
bool ofr2b_subx_step(AnimationMachineState& r) {
    const std::uint32_t extend=(ofr2b_b(r.d[2])>>7)&1U;am_byte(r.d[2],r.d[2]<<1);
    const std::uint32_t subtrahend=ofr2b_w(r.d[3])+extend;const bool borrow=subtrahend>ofr2b_w(r.d[1]);
    am_word(r.d[1],r.d[1]-subtrahend);return borrow;
}
// dd574 / dd5c6 / dd618 / dd66a: LEA 10b1d6.l,A1; MOVE.L #fffa0000,8(A1); MOVE.L #high,c(A1); LEA 10d256.l,A1; MOVE.L #ffffa000,8(A1);
// MOVE.L #0,c(A1); MOVE.L #install,(A6) (entered).
bool ofr2b_dd_speed(AnimationMachineContext& c,std::uint32_t high,std::uint32_t install) {
    AnimationMachineState& r=c.s;r.a[1]=0x10b1d6;
    if(!ofr2b_put(c,r.a[1],8,4,0xfffa0000U) || !ofr2b_put(c,r.a[1],0xc,4,high))return false;r.a[1]=0x10d256;
    if(!ofr2b_put(c,r.a[1],8,4,0xffffa000U) || !ofr2b_put(c,r.a[1],0xc,4,0))return false;return ofr2b_install(c,install);
}
// dd5a6 / dd5f8 / dd64a: MOVE.L 76(A6),D0; ADDI.L #60000,D0; CMPI.L #limit,D0; BCS.W below_pc (unsigned) / otherwise at_pc.
bool ofr2b_dd_step(AnimationMachineContext& c,std::uint32_t limit,std::uint32_t below_pc,std::uint32_t at_pc) {
    std::uint32_t value=0;if(!ofr2b_get(c,c.s.a[6],0x76,4,value))return false;c.s.d[0]=value+0x60000U;c.s.pc=c.s.d[0]<limit?below_pc:at_pc;return true;
}
}
// Objects FR2b (214 block starts, contract docs/analysis/animation-machine-frontier-fr2b-contract.md): the IO-frontier roots of the FR2a IO rerun
// 48256 (stage BYTE helper), 76852 (U09 28ae child; install 768b6, the N15-family tail 70674 / 70764 and its install 718c8 with 702cc), b336a (FR1b
// 28ae child; install b33bc), the card-menu handlers a92a / a8d0 (a8dc, 9ef2, bb6), and their natural successors: the install 70c0c (70c76) with the
// helpers 70302 (702f0) / 70606, the 28ae child 76944 (install 76984) with its makers 769ac / 769b2 / 769f4, the U01 install chain dd574..dd69c,
// the FR1c child bc844 up to its install bc93c (bc8b6 bc8f2 bc924) and the terrain helper 4c2cc. Every exit is routed; MOVE.L #v,(A6) enters v only
// when v is the next PC, otherwise it only writes the callback LONG (stops 71884 70d92 70e2a 71468 72978 72f8a bc93c and the 70d72 table values).
// Known C: 7061e (ORI; RTS) Set, 70624 (ANDI; RTS) Clear, 4c2ee (ORI; RTS) Set; 4c2ec (RTS) passes the Clear of the consumer 4c2e8. The 10
// consumers 7031e (494c0) 7686e (497a6) 76938 (288c) 769a0 bc930 (49fc6) 70cf8 (7054c) 70d06 (705ca) 70d14 (7028e) 70d4c (70606) 4c2e8 (46d72)
// read a known C or fail. X lives only inside a block (7036a ADDX chain, 70394..703e4 SUBX steps). Data through the live bus (no limit test).
bool animation_objects_fr2b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    case 0xa8ec:case 0xa938:case 0xa950:case 0x4c2ec:case 0x703f4:case 0x76942:case 0x769aa:case 0x769f2:case 0xb33d6:case 0xbc8f0:case 0xbc93a:
        return am_return(c);                                                                  // RTS (4c2ec passes the known C).
    case 0x7061e:return ofr2b_return_carry(c,AnimationCarrySet);                              // ORI.B #1,CCR; RTS.
    case 0x70624:return ofr2b_return_carry(c,AnimationCarryClear);                            // ANDI.B #fe,CCR; RTS.
    case 0x7693c:case 0x769a4:case 0xb33d0:r.pc=0x2a00;return true;                          // JMP 2a00.l.
    // ---- card-menu handlers: OR.B D0,100014.l; RTS / MOVE.B -e6(A5),D0; RTS.
    case 0xbb6:if(!am_read(c,0x100014,1,value) || !am_write(c,0x100014,1,ofr2b_b(value|r.d[0])))return false;return am_return(c);
    case 0x9ef2:if(!ofr2b_get(c,r.a[5],0xff1a,1,value))return false;am_byte(r.d[0],value);return am_return(c);
    case 0xa8d0:return am_call(c,0xa73e,0xa8d4);                                             // BSR.W a73e.
    case 0xa8d4:r.pc=ofr2b_w(r.d[0])==3U?0xa70a:0xa8dc;return true;                          // CMPI.W #3,D0; BEQ.W a70a.
    case 0xa8dc:r.pc=ofr2b_w(r.d[0])==4U?0xa70a:0xa8e4;return true;                          // CMPI.W #4,D0; BEQ.W a70a.
    case 0xa8e4:r.pc=ofr2b_w(r.d[0])==1U?0xa70a:0xa8ec;return true;                          // CMPI.W #1,D0; BEQ.W a70a.
    case 0xa92a:return am_call(c,0xa73e,0xa92e);                                             // JSR a73e(PC).
    case 0xa92e:return am_call(c,0xa8dc,0xa930);                                             // BSR.B a8dc.
    case 0xa930:r.pc=ofr2b_w(r.d[0])==3U?0xa93a:0xa938;return true;                          // CMPI.W #3,D0; BEQ.W a93a.
    // MOVEA.L c(A6),A0; MOVE.B #1,62(A0); JSR 9ef2.l.
    case 0xa93a:if(!ofr2b_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr2b_put(c,r.a[0],0x62,1,1))return false;return am_call(c,0x9ef2,0xa94a);
    case 0xa94a:return am_call(c,0xbb6,0xa950);                                              // JSR bb6.l.
    // ---- 48256: MOVE.B -7453(A5),D0; ADDQ.B #1,D0; MOVE.B D0,5681(A5); RTS.
    case 0x48256:
        if(!ofr2b_get(c,r.a[5],0x8bad,1,value))return false;am_byte(r.d[0],value+1U);if(!ofr2b_put(c,r.a[5],0x5681,1,r.d[0]))return false;return am_return(c);
    // ---- 4c2cc: JSR 4bc44(PC).
    case 0x4c2cc:return am_call(c,0x4bc44,0x4c2d0);
    // MOVEQ #0,D2; MOVEQ #0,D3; MOVE.W D0,D3; SWAP D3; MOVEM.L 2e(A6),D0-D1; MOVEA.L 3e(A6),A0; JSR 46d72.l.
    case 0x4c2d0:
        r.d[2]=0;r.d[3]=0;am_word(r.d[3],r.d[0]);am_swap(r.d[3]);
        if(!ofr2b_get(c,r.a[6],0x2e,4,value) || !ofr2b_get(c,r.a[6],0x32,4,other))return false;r.d[0]=value;r.d[1]=other;
        if(!ofr2b_get(c,r.a[6],0x3e,4,value))return false;r.a[0]=value;return am_call(c,0x46d72,0x4c2e8);
    case 0x4c2e8:return ofr2b_carry(c,0x4c2ec,0x4c2ee);                                      // BCS.W 4c2ee (C of 46d72).
    // SWAP D6; MOVE.W D6,D0; NEG.W D0; ORI.B #1,CCR; RTS.
    case 0x4c2ee:am_swap(r.d[6]);am_word(r.d[0],r.d[6]);am_word(r.d[0],0U-r.d[0]);return ofr2b_return_carry(c,AnimationCarrySet);
    // ---- 702cc: MOVE.L 64(A6),D0; SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6); MOVE.L #fff00000,D0; SUB.L 3a(A6),D0; ASR.L #5,D0;
    // ADD.L D0,3a(A6); JMP 4be34.l.
    case 0x702cc:
        if(!ofr2b_get(c,r.a[6],0x64,4,value) || !ofr2b_get(c,r.a[6],0x36,4,other))return false;r.d[0]=ofr2b_asr_long(value-other,5);
        if(!ofr2b_get(c,r.a[6],0x36,4,value) || !ofr2b_put(c,r.a[6],0x36,4,value+r.d[0]))return false;
        if(!ofr2b_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ofr2b_asr_long(0xfff00000U-value,5);
        if(!ofr2b_get(c,r.a[6],0x3a,4,value) || !ofr2b_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;r.pc=0x4be34;return true;
    case 0x702f0:r.a[0]=0x702fa;r.pc=0x494c0;return true;                                    // LEA 702fa(PC),A0; JMP 494c0.l.
    // ---- 70302: TST.W 78(A6); BNE.W 703f0 / BTST.B #3,82(A6); BEQ.W 703f0 / TST.B 86(A6); BMI.W 703f0 / BSR.B 702f0 / BCC.W 703f0.
    case 0x70302:return ofr2b_test(c,0x78,2,0x7030a,0x703f0);
    case 0x7030a:return ofr2b_bit(c,r.a[6],0x82,3,0x703f0,0x70314);
    case 0x70314:if(!ofr2b_get(c,r.a[6],0x86,1,value))return false;r.pc=(value&0x80U)!=0U?0x703f0:0x7031c;return true;
    case 0x7031c:return am_call(c,0x702f0,0x7031e);
    case 0x7031e:return ofr2b_carry(c,0x703f0,0x70322);                                      // BCC.W 703f0 (C of 494c0).
    // MOVE.B 87(A6),D1; BTST.B #7,15(A6); BNE.W 70334 / 70330: ANDI.B #2,D1.
    case 0x70322:if(!ofr2b_get(c,r.a[6],0x87,1,value))return false;am_byte(r.d[1],value);return ofr2b_bit(c,r.a[6],0x15,7,0x70330,0x70334);
    case 0x70330:am_byte(r.d[1],r.d[1]&2U);r.pc=0x70334;return true;
    case 0x70334:return ofr2b_bit(c,r.a[6],0x82,6,0x70364,0x7033e);                          // BTST.B #6,82(A6); BEQ.W 70364.
    // BCLR.B #1,D1 (register: LONG bit 1); BEQ.W 70364 (the old bit was clear).
    case 0x7033e:value=(r.d[1]>>1)&1U;r.d[1]=r.d[1]&~2U;r.pc=value==0U?0x70364:0x70346;return true;
    case 0x70346:return ofr2b_bit(c,r.a[6],0x82,1,0x70364,0x70350);                          // BTST.B #1,82(A6); BEQ.W 70364.
    // MOVE.W D1,-(A7); MOVE.W #ff,D0; MOVE.W 42(A6),D2; MOVE.W 46(A6),D3; BSR.W 70036.
    case 0x70350:
        if(!am_push(c,2,ofr2b_w(r.d[1])))return false;am_word(r.d[0],0xff);
        if(!ofr2b_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[2],value);if(!ofr2b_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[3],value);
        return am_call(c,0x70036,0x70362);
    case 0x70362:if(!am_pop(c,2,value))return false;am_word(r.d[1],value);r.pc=0x70364;return true;   // MOVE.W (A7)+,D1.
    case 0x70364:r.pc=ofr2b_b(r.d[1])==0U?0x703f0:0x7036a;return true;                       // TST.B D1; BEQ.W 703f0.
    // MOVEQ #0,D0; MOVEQ #0,D2; 8 x (ADD.B D1,D1; ADDX.W D2,D0) (counts the set bits of D1.B); JSR 49a84.l.
    case 0x7036a:
        r.d[0]=0;r.d[2]=0;
        for(unsigned int k=0;k<8;++k){const std::uint32_t extend=(ofr2b_b(r.d[1])>>7)&1U;am_byte(r.d[1],r.d[1]<<1);
            am_word(r.d[0],ofr2b_w(r.d[0])+ofr2b_w(r.d[2])+extend);}
        return am_call(c,0x49a84,0x70394);
    // MOVE.W D0,D1; MOVE.B 87(A6),D2; MOVEQ #0,D3; MOVE.W #7,D0; ADD.B D2,D2; SUBX.W D3,D1; BCS.W 703f4.
    case 0x70394:
        am_word(r.d[1],r.d[0]);if(!ofr2b_get(c,r.a[6],0x87,1,value))return false;am_byte(r.d[2],value);r.d[3]=0;am_word(r.d[0],7);
        r.pc=ofr2b_subx_step(r)?0x703f4:0x703a8;return true;
    // SUBQ.W #1,D0; ADD.B D2,D2; SUBX.W D3,D1; BCS.W 703f4.
    case 0x703a8:case 0x703b2:case 0x703bc:case 0x703c6:case 0x703d0:case 0x703da:case 0x703e4:
        am_word(r.d[0],r.d[0]-1U);other=r.pc+10U;r.pc=ofr2b_subx_step(r)?0x703f4:other;return true;
    case 0x703ee:am_word(r.d[0],r.d[0]-1U);r.pc=0x703f0;return true;                         // SUBQ.W #1,D0.
    case 0x703f0:r.d[0]=0;return am_return(c);                                               // MOVEQ #0,D0; RTS.
    // ---- 70606: MOVE.W 42(A6),D0; SUBI.W #18,D0; CMPI.W #110,D0; BCC.W 70624 / TST.B 86(A6); BPL.W 70624.
    case 0x70606:if(!ofr2b_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value-0x18U);r.pc=ofr2b_w(r.d[0])>=0x110U?0x70624:0x70616;return true;
    case 0x70616:if(!ofr2b_get(c,r.a[6],0x86,1,value))return false;r.pc=(value&0x80U)==0U?0x70624:0x7061e;return true;
    // ---- 70674 / 70764 (JMP from 76916 / 76926): TST.W 70(A6); BNE.W -> MOVE.W #1,9c(A6), otherwise MOVE.W #0,9c(A6).
    case 0x70674:return ofr2b_test(c,0x70,2,0x7067c,0x70686);
    case 0x7067c:return ofr2b_word(c,0x9c,0,0x7068c);
    case 0x70686:return ofr2b_word(c,0x9c,1,0x7068c);
    // MOVE.B #e2,-(A7); TST.B 6a(A6); BEQ.W 706fe.
    case 0x7068c:if(!am_push(c,1,0xe2))return false;return ofr2b_test(c,0x6a,1,0x706fe,0x70698);
    case 0x70698:return ofr2b_test(c,0x9c,2,0x706a0,0x706cc);                                // TST.W 9c(A6); BNE.W 706cc.
    case 0x706a0:return ofr2b_bank_anim(c,3,0x2000d0,0x180,0x706c8);
    case 0x706c8:r.pc=0x706f4;return true;                                                   // BRA.W 706f4.
    case 0x706cc:return ofr2b_bank_anim(c,0xb,0x2000d4,0x1cc,0x706f4);
    case 0x706f4:return ofr2b_callback(c,0x71884,0x70760);                                   // MOVE.L #71884,(A6); BRA.W 70760.
    case 0x706fe:return ofr2b_test(c,0x9c,2,0x70706,0x70732);                                // TST.W 9c(A6); BNE.W 70732.
    case 0x70706:return ofr2b_bank_anim(c,3,0x2000d0,0x20,0x7072e);
    case 0x7072e:r.pc=0x7075a;return true;                                                   // BRA.W 7075a.
    case 0x70732:return ofr2b_bank_anim(c,0xb,0x2000d4,0x20,0x7075a);
    case 0x7075a:return ofr2b_callback(c,0x718c8,0x70760);                                   // MOVE.L #718c8,(A6).
    case 0x70760:r.pc=0x707e2;return true;                                                   // BRA.W 707e2.
    case 0x70764:return ofr2b_test(c,0x70,2,0x7076c,0x70776);
    case 0x7076c:return ofr2b_word(c,0x9c,0,0x7077c);
    case 0x70776:return ofr2b_word(c,0x9c,1,0x7077c);
    // MOVE.B #10,-(A7); TST.W 9c(A6); BNE.W 707b4.
    case 0x7077c:if(!am_push(c,1,0x10))return false;return ofr2b_test(c,0x9c,2,0x70788,0x707b4);
    case 0x70788:return ofr2b_bank_anim(c,3,0x2000d0,0x28,0x707b0);
    case 0x707b0:r.pc=0x707dc;return true;                                                   // BRA.W 707dc.
    case 0x707b4:return ofr2b_bank_anim(c,0xb,0x2000d4,0x28,0x707dc);
    case 0x707dc:return ofr2b_callback(c,0x71b04,0x707e2);                                   // MOVE.L #71b04,(A6).
    // BSET.B #3,15(A6); TST.W 70(A6); BNE.W 707fa.
    case 0x707e2:if(!ofr2b_set_bit(c,r.a[6],0x15,3,0))return false;return ofr2b_test(c,0x70,2,0x707f0,0x707fa);
    case 0x707f0:return ofr2b_word(c,0x9c,0,0x70800);
    case 0x707fa:return ofr2b_word(c,0x9c,1,0x70800);
    case 0x70800:return am_call(c,0x8ff4,0x70806);                                           // JSR 8ff4.l.
    // MOVE.W #2,76(A6); MOVE.W #3c,7a(A6); MOVE.W #3c,78(A6); MOVE.W #5a,7c(A6); MOVE.W #0,7e(A6); MOVE.W #0,80(A6); MOVE.B 15(A6),-(A7);
    // JSR 70418(PC).
    case 0x70806:
        if(!ofr2b_put(c,r.a[6],0x76,2,2) || !ofr2b_put(c,r.a[6],0x7a,2,0x3c) || !ofr2b_put(c,r.a[6],0x78,2,0x3c) || !ofr2b_put(c,r.a[6],0x7c,2,0x5a) ||
           !ofr2b_put(c,r.a[6],0x7e,2,0) || !ofr2b_put(c,r.a[6],0x80,2,0) || !ofr2b_get(c,r.a[6],0x15,1,value) || !am_push(c,1,value))return false;
        return am_call(c,0x70418,0x70832);
    // MOVE.B (A7)+,D0; ANDI.B #1,D0; ANDI.B #fe,15(A6); OR.B D0,15(A6); MOVE.B (A7)+,87(A6); MOVE.L #28000,D0; MOVE.L #fffccccd,D1;
    // BTST.B #0,15(A6); BEQ.W 70860.
    case 0x70832:
        if(!am_pop(c,1,value))return false;am_byte(r.d[0],value&1U);
        if(!ofr2b_get(c,r.a[6],0x15,1,value) || !ofr2b_put(c,r.a[6],0x15,1,value&0xfeU))return false;
        if(!ofr2b_get(c,r.a[6],0x15,1,value) || !ofr2b_put(c,r.a[6],0x15,1,value|ofr2b_b(r.d[0])))return false;
        if(!am_pop(c,1,value) || !ofr2b_put(c,r.a[6],0x87,1,value))return false;r.d[0]=0x28000;r.d[1]=0xfffccccdU;
        return ofr2b_bit(c,r.a[6],0x15,0,0x70860,0x7085c);
    case 0x7085c:r.d[0]=0U-r.d[0];r.d[1]=0U-r.d[1];r.pc=0x70860;return true;                // NEG.L D0; NEG.L D1.
    case 0x70860:if(!ofr2b_put(c,r.a[6],0x64,4,r.d[0]) || !ofr2b_put(c,r.a[6],0x36,4,r.d[1]))return false;return am_return(c);   // ...; RTS.
    // ---- 70c0c (installed value): TST.W 9c(A6); BNE.W 70c40.
    case 0x70c0c:return ofr2b_test(c,0x9c,2,0x70c14,0x70c40);
    case 0x70c14:return ofr2b_bank_anim(c,3,0x2000d0,0xc,0x70c3c);
    case 0x70c3c:r.pc=0x70c68;return true;                                                   // BRA.W 70c68.
    case 0x70c40:return ofr2b_bank_anim(c,0xb,0x2000d4,0xc,0x70c68);
    case 0x70c68:if(!ofr2b_put(c,r.a[6],0x64,4,0))return false;return ofr2b_install(c,0x70c76);   // MOVE.L #0,64(A6); MOVE.L #70c76,(A6).
    case 0x70c76:return ofr2b_bit(c,r.a[6],0x15,7,0x71c90,0x70c80);                          // BTST.B #7,15(A6); BEQ.W 71c90.
    case 0x70c80:return am_call(c,0x4bfa4,0x70c86);                                          // JSR 4bfa4.l.
    case 0x70c86:return am_call(c,0x49fc6,0x70c8c);                                          // JSR 49fc6.l.
    case 0x70c8c:if(!ofr2b_get(c,r.a[6],0x6e,1,value))return false;r.pc=value==3U?0x70d10:0x70c96;return true;   // CMPI.B #3,6e(A6); BEQ.W 70d10.
    // MOVE.W 8e(A6),D0; SUB.W 42(A6),D0; BTST.B #0,15(A6); SEQ.B D1; EXT.W D1; EOR.W D0,D1; TST.W D0; BPL.W 70cb2.
    case 0x70c96:
        if(!ofr2b_get(c,r.a[6],0x8e,2,value) || !ofr2b_get(c,r.a[6],0x42,2,other))return false;am_word(r.d[0],value-other);
        if(!ofr2b_get(c,r.a[6],0x15,1,value))return false;am_byte(r.d[1],(value&1U)==0U?0xffU:0U);
        am_word(r.d[1],(r.d[1]&0x80U)!=0U?(0xff00U|ofr2b_b(r.d[1])):ofr2b_b(r.d[1]));am_word(r.d[1],r.d[1]^r.d[0]);
        r.pc=(r.d[0]&0x8000U)==0U?0x70cb2:0x70cb0;return true;
    case 0x70cb0:am_word(r.d[0],0U-r.d[0]);r.pc=0x70cb2;return true;                         // NEG.W D0.
    case 0x70cb2:r.pc=ofr2b_w(r.d[0])<0x10U?0x70cc0:0x70cba;return true;                     // CMPI.W #10,D0; BCS.W 70cc0.
    case 0x70cba:return ofr2b_callback(c,0x70e2a,0x70cc0);                                   // MOVE.L #70e2a,(A6).
    case 0x70cc0:r.pc=(r.d[1]&0x8000U)!=0U?0x70cd8:0x70cc6;return true;                      // TST.W D1; BMI.W 70cd8.
    case 0x70cc6:r.pc=ofr2b_w(r.d[0])<0x30U?0x70cd4:0x70cce;return true;                     // CMPI.W #30,D0; BCS.W 70cd4.
    case 0x70cce:return ofr2b_callback(c,0x71032,0x70cd4);                                   // MOVE.L #71032,(A6).
    case 0x70cd4:r.pc=0x70cf4;return true;                                                   // BRA.W 70cf4.
    case 0x70cd8:r.pc=ofr2b_w(r.d[0])<0x30U?0x70ce6:0x70ce0;return true;                     // CMPI.W #30,D0; BCS.W 70ce6.
    case 0x70ce0:return ofr2b_callback(c,0x71bc0,0x70ce6);                                   // MOVE.L #71bc0,(A6).
    case 0x70ce6:r.pc=ofr2b_w(r.d[0])<0x48U?0x70cf4:0x70cee;return true;                     // CMPI.W #48,D0; BCS.W 70cf4.
    case 0x70cee:return ofr2b_callback(c,0x71468,0x70cf4);                                   // MOVE.L #71468,(A6).
    case 0x70cf4:return am_call(c,0x7054c,0x70cf8);                                          // BSR.W 7054c.
    case 0x70cf8:return ofr2b_carry(c,0x70d02,0x70cfc);                                      // BCC.W 70d02 (C of 7054c).
    case 0x70cfc:return ofr2b_callback(c,0x71a80,0x70d02);                                   // MOVE.L #71a80,(A6).
    case 0x70d02:return am_call(c,0x705ca,0x70d06);                                          // BSR.W 705ca.
    case 0x70d06:return ofr2b_carry(c,0x70d10,0x70d0a);                                      // BCC.W 70d10 (C of 705ca).
    case 0x70d0a:return ofr2b_callback(c,0x71dd6,0x70d10);                                   // MOVE.L #71dd6,(A6).
    case 0x70d10:return am_call(c,0x7028e,0x70d14);                                          // BSR.W 7028e.
    case 0x70d14:return ofr2b_carry(c,0x70d1e,0x70d18);                                      // BCC.W 70d1e (C of 7028e).
    case 0x70d18:return ofr2b_callback(c,0x72978,0x70d1e);                                   // MOVE.L #72978,(A6).
    case 0x70d1e:return am_call(c,0x70302,0x70d22);                                          // BSR.W 70302.
    // LEA 70d72(PC),A0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A0,D0.W),A0; CMPA.W #0,A0; BEQ.W 70d38.
    case 0x70d22:
        r.a[0]=0x70d72;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;
        r.a[0]=value;r.pc=value==0U?0x70d38:0x70d36;return true;
    case 0x70d36:return ofr2b_callback(c,r.a[0],0x70d38);                                    // MOVE.L A0,(A6).
    case 0x70d38:return ofr2b_bit(c,r.a[6],0x82,0,0x70d42,0x70d48);                          // BTST.B #0,82(A6); BNE.W 70d48.
    case 0x70d42:return ofr2b_callback(c,0x70d92,0x70d48);                                   // MOVE.L #70d92,(A6).
    case 0x70d48:return am_call(c,0x70606,0x70d4c);                                          // BSR.W 70606.
    case 0x70d4c:return ofr2b_carry(c,0x70d60,0x70d50);                                      // BCC.W 70d60 (C of 70606).
    case 0x70d50:return ofr2b_bit(c,r.a[6],0x15,3,0x70d5a,0x70d60);                          // BTST.B #3,15(A6); BNE.W 70d60.
    case 0x70d5a:return ofr2b_callback(c,0x72a18,0x70d60);                                   // MOVE.L #72a18,(A6).
    case 0x70d60:return ofr2b_test(c,0x7c,2,0x70d68,0x70d6e);                                // TST.W 7c(A6); BNE.W 70d6e.
    case 0x70d68:return ofr2b_callback(c,0x72f8a,0x70d6e);                                   // MOVE.L #72f8a,(A6).
    case 0x70d6e:case 0x718e8:r.pc=0x72dd2;return true;                                      // BRA.W 72dd2.
    // ---- 718c8 (installed value): BSR.W 702cc / JSR 49fc6.l / BTST.B #7,15(A6); BEQ.W 718e8 / BCLR.B #3,15(A6); MOVE.L #71d48,(A6).
    case 0x718c8:return am_call(c,0x702cc,0x718cc);
    case 0x718cc:return am_call(c,0x49fc6,0x718d2);
    case 0x718d2:return ofr2b_bit(c,r.a[6],0x15,7,0x718e8,0x718dc);
    case 0x718dc:if(!ofr2b_set_bit(c,r.a[6],0x15,3,1))return false;return ofr2b_callback(c,0x71d48,0x718e8);
    // ---- 76852 (U09 28ae child): MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l / JSR 491c4.l / MOVE.W 1e(A0),1e(A6); JSR 497a6.l / BCC.W 76884.
    case 0x76852:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x7685c);
    case 0x7685c:return am_call(c,0x491c4,0x76862);
    case 0x76862:if(!ofr2b_get(c,r.a[0],0x1e,2,value) || !ofr2b_put(c,r.a[6],0x1e,2,value))return false;return am_call(c,0x497a6,0x7686e);
    case 0x7686e:return ofr2b_carry(c,0x76884,0x76872);                                      // BCC.W 76884 (C of 497a6).
    case 0x76872:return ofr2b_sound(c,0xc54,0x76880);
    case 0x76880:r.pc=0x76892;return true;                                                   // BRA.W 76892.
    case 0x76884:return ofr2b_sound(c,0xc4e,0x76892);
    // MOVE.W #b,20(A6); MOVEA.L #76c46,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x76892:if(!ofr2b_put(c,r.a[6],0x20,2,0xb))return false;r.a[1]=0x76c46;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x768a8);
    case 0x768a8:if(!ofr2b_put(c,r.a[6],0x7e,4,0x76a1c))return false;return ofr2b_install(c,0x768b6);   // MOVE.L #76a1c,7e(A6); MOVE.L #768b6,(A6).
    // MOVEA.L 7e(A6),A0; MOVEQ #0,D0; MOVEQ #0,D1; MOVE.W (A0)+,D0; MOVE.W (A0)+,D1; CMPA.L #76aa0,A0; BCC.W 768f8.
    case 0x768b6:
        if(!ofr2b_get(c,r.a[6],0x7e,4,value))return false;r.a[0]=value;r.d[0]=0;r.d[1]=0;
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.a[0]=r.a[0]+2U;
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);r.a[0]=r.a[0]+2U;r.pc=r.a[0]>=0x76aa0U?0x768f8:0x768cc;return true;
    // MOVE.L A0,7e(A6); BTST.B #0,15(A6); BEQ.W 768dc / 768da: NEG.W D0.
    case 0x768cc:if(!ofr2b_put(c,r.a[6],0x7e,4,r.a[0]))return false;return ofr2b_bit(c,r.a[6],0x15,0,0x768dc,0x768da);
    case 0x768da:am_word(r.d[0],0U-r.d[0]);r.pc=0x768dc;return true;
    // SWAP D0; SWAP D1; MOVE.L D0,2e(A6); MOVE.L D1,32(A6); JSR 43e34.l.
    case 0x768dc:am_swap(r.d[0]);am_swap(r.d[1]);if(!ofr2b_put(c,r.a[6],0x2e,4,r.d[0]) || !ofr2b_put(c,r.a[6],0x32,4,r.d[1]))return false;return am_call(c,0x43e34,0x768ee);
    case 0x768ee:return am_call(c,0x49fc6,0x768f4);
    case 0x768f4:r.pc=0x76932;return true;                                                   // BRA.W 76932.
    case 0x768f8:return am_call(c,0x43e34,0x768fe);
    case 0x768fe:return am_call(c,0x49fc6,0x76904);
    case 0x76904:return am_call(c,0x49274,0x7690a);
    // MOVEA.L c(A6),A0; TST.B 89(A0); BNE.W 76926.
    case 0x7690a:if(!ofr2b_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr2b_get(c,r.a[0],0x89,1,value))return false;r.pc=value!=0U?0x76926:0x76916;return true;
    case 0x76916:return ofr2b_word(c,0x70,1,0x70674);                                        // MOVE.W #1,70(A6); JMP 70674.l.
    case 0x76926:return ofr2b_word(c,0x70,1,0x70764);                                        // MOVE.W #1,70(A6); JMP 70764.l.
    case 0x76932:return am_call(c,0x288c,0x76938);                                           // JSR 288c.l.
    case 0x76938:return ofr2b_carry(c,0x7693c,0x76942);                                      // BCS.W 76942 (C of 288c).
    // ---- 76944 (28ae child of 769b4): MOVE.W #c53,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x76944:return ofr2b_sound(c,0xc53,0x76952);
    // MOVE.W #8821,68(A6); MOVE.W #8821,1e(A6); MOVE.W #b,20(A6); MOVEA.L #76c84,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x76952:
        if(!ofr2b_put(c,r.a[6],0x68,2,0x8821) || !ofr2b_put(c,r.a[6],0x1e,2,0x8821) || !ofr2b_put(c,r.a[6],0x20,2,0xb))return false;
        r.a[1]=0x76c84;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x76974);
    // MOVEQ #0,D0; MOVE.L D0,36(A6); MOVE.L D0,3a(A6); MOVE.L #76984,(A6).
    case 0x76974:r.d[0]=0;if(!ofr2b_put(c,r.a[6],0x36,4,0) || !ofr2b_put(c,r.a[6],0x3a,4,0))return false;return ofr2b_install(c,0x76984);
    // MOVE.L #fffe0000,D0; SUB.L 3a(A6),D0; ASR.L #4,D0; ADD.L D0,3a(A6); JSR 43ea4.l.
    case 0x76984:
        if(!ofr2b_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ofr2b_asr_long(0xfffe0000U-value,4);
        if(!ofr2b_get(c,r.a[6],0x3a,4,value) || !ofr2b_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;return am_call(c,0x43ea4,0x7699a);
    case 0x7699a:return am_call(c,0x49fc6,0x769a0);
    case 0x769a0:return ofr2b_carry(c,0x769aa,0x769a4);                                      // BCC.W 769aa (C of 49fc6).
    // ---- 769ac / 769b2 (LONG table 4a720 / 4a724): MOVEQ #0,D0; BRA.W 769b4 / MOVEQ #1,D0.
    case 0x769ac:r.d[0]=0;r.pc=0x769b4;return true;
    case 0x769b2:r.d[0]=1;r.pc=0x769b4;return true;
    // MOVE.B D0,-(A7); MOVE.L A0,-(A7); MOVEA.L #76944,A0; MOVE.W #1e,D0; JSR 28ae.l.
    case 0x769b4:if(!am_push(c,1,ofr2b_b(r.d[0])) || !am_push(c,4,r.a[0]))return false;r.a[0]=0x76944;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0x769c8);
    // MOVEA.L (A7)+,A1; MOVE.W (A1)+,D0; MOVE.W (A1)+,D1; BTST.B #0,15(A6); BEQ.W 769da / 769d8: NEG.W D0.
    case 0x769c8:
        if(!am_pop(c,4,value))return false;r.a[1]=value;if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[0],value);r.a[1]=r.a[1]+2U;
        if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[1],value);r.a[1]=r.a[1]+2U;return ofr2b_bit(c,r.a[6],0x15,0,0x769da,0x769d8);
    case 0x769d8:am_word(r.d[0],0U-r.d[0]);r.pc=0x769da;return true;
    case 0x769da:return am_call(c,0x49214,0x769e0);
    case 0x769e0:return am_call(c,0x491b6,0x769e6);
    case 0x769e6:if(!am_pop(c,1,value))return false;r.pc=value==0U?0x769f2:0x769ec;return true;   // TST.B (A7)+; BEQ.W 769f2.
    case 0x769ec:if(!ofr2b_set_bit(c,r.a[0],0x15,0,2))return false;r.pc=0x769f2;return true;     // BCHG.B #0,15(A0).
    case 0x769f4:if(!ofr2b_set_bit(c,r.a[6],0x61,3,0))return false;return am_return(c);      // BSET.B #3,61(A6); RTS.
    // ---- b336a (FR1b 28ae child): MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); MOVE.W #5e,D0; MOVE.W #3,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xb336a:if(!ofr2b_put(c,r.a[6],0x68,2,0x1001) || !ofr2b_put(c,r.a[6],0x1e,2,0x1001))return false;return ofr2b_c6a96(c,0x5e,3,0xb3388);
    case 0xb3388:return ofr2b_bank_anim(c,0x15b,0x20017c,0xc,0xb33b0);
    case 0xb33b0:if(!ofr2b_put(c,r.a[6],0x86,2,0xc))return false;return ofr2b_install(c,0xb33bc);   // MOVE.W #c,86(A6); MOVE.L #b33bc,(A6).
    case 0xb33bc:return am_call(c,0x43e34,0xb33c2);
    case 0xb33c2:return am_call(c,0x49fc6,0xb33c8);
    // SUBQ.W #1,86(A6); BCC.W b33d6 (no borrow: the old WORD was not 0).
    case 0xb33c8:if(!ofr2b_get(c,r.a[6],0x86,2,value) || !ofr2b_put(c,r.a[6],0x86,2,value-1U))return false;r.pc=value!=0U?0xb33d6:0xb33d0;return true;
    // ---- bc844 (FR1c 28ae child): BSET.B #0,15(A6); MOVE.W #4f,D0; MOVE.W #7,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xbc844:if(!ofr2b_set_bit(c,r.a[6],0x15,0,0))return false;return ofr2b_c6a96(c,0x4f,7,0xbc85c);
    case 0xbc85c:return ofr2b_bank_anim(c,0xe3,0x200140,0x1c,0xbc884);
    // MOVE.W #8800,68(A6); MOVE.W #8800,1e(A6); MOVE.L #30000,36(A6); MOVE.L #30000,64(A6); MOVE.L #0,3a(A6); MOVE.W #8,D0; MOVE.W D0,76(A6);
    // MOVE.L #bc8b6,(A6).
    case 0xbc884:
        if(!ofr2b_put(c,r.a[6],0x68,2,0x8800) || !ofr2b_put(c,r.a[6],0x1e,2,0x8800) || !ofr2b_put(c,r.a[6],0x36,4,0x30000) ||
           !ofr2b_put(c,r.a[6],0x64,4,0x30000) || !ofr2b_put(c,r.a[6],0x3a,4,0))return false;
        am_word(r.d[0],8);if(!ofr2b_put(c,r.a[6],0x76,2,r.d[0]))return false;return ofr2b_install(c,0xbc8b6);
    case 0xbc8b6:return ofr2b_bit(c,r.a[6],0x15,7,0xbc8ca,0xbc8c0);                          // BTST.B #7,15(A6); BEQ.W bc8ca.
    case 0xbc8c0:return am_call(c,0x4be2c,0xbc8c6);
    case 0xbc8c6:r.pc=0xbc8d0;return true;                                                   // BRA.W bc8d0.
    case 0xbc8ca:return am_call(c,0x4bfa4,0xbc8d0);
    // MOVEA.L c(A6),A0; TST.B 62(A0); BEQ.W bc8ea.
    case 0xbc8d0:if(!ofr2b_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr2b_get(c,r.a[0],0x62,1,value))return false;r.pc=value==0U?0xbc8ea:0xbc8dc;return true;
    // SUBQ.W #1,76(A6); BCC.W bc8ea (no borrow).
    case 0xbc8dc:if(!ofr2b_get(c,r.a[6],0x76,2,value) || !ofr2b_put(c,r.a[6],0x76,2,value-1U))return false;r.pc=value!=0U?0xbc8ea:0xbc8e4;return true;
    case 0xbc8e4:return ofr2b_callback(c,0xbc8f2,0xbc8ea);                                   // MOVE.L #bc8f2,(A6).
    case 0xbc8ea:return am_call(c,0x49fc6,0xbc8f0);
    case 0xbc8f2:if(!ofr2b_put(c,r.a[6],0x62,1,0xff))return false;return ofr2b_bank_anim(c,0xe3,0x200140,0x8c,0xbc91e);   // ST.B 62(A6); anim.
    case 0xbc91e:return ofr2b_install(c,0xbc924);                                            // MOVE.L #bc924,(A6).
    case 0xbc924:return am_call(c,0x43e34,0xbc92a);
    case 0xbc92a:return am_call(c,0x49fc6,0xbc930);
    case 0xbc930:return ofr2b_carry(c,0xbc93a,0xbc934);                                      // BCC.W bc93a (C of 49fc6).
    case 0xbc934:return ofr2b_callback(c,0xbc93c,0xbc93a);                                   // MOVE.L #bc93c,(A6).
    // ---- dd574 (U01 install): the speeds of the records 10b1d6 / 10d256, then the steps on LONG 76(A6).
    case 0xdd574:return ofr2b_dd_speed(c,0xfffa0000U,0xdd5a6);
    case 0xdd5c6:return ofr2b_dd_speed(c,0,0xdd5f8);
    case 0xdd618:return ofr2b_dd_speed(c,0xfffa0000U,0xdd64a);
    case 0xdd66a:return ofr2b_dd_speed(c,0,0xdd69c);
    case 0xdd5a6:return ofr2b_dd_step(c,0x8b00000U,0xdd5c0,0xdd5ba);
    case 0xdd5f8:return ofr2b_dd_step(c,0x14900000U,0xdd612,0xdd60c);
    case 0xdd64a:return ofr2b_dd_step(c,0x15900000U,0xdd664,0xdd65e);
    case 0xdd5ba:return ofr2b_callback(c,0xdd5c6,0xdd5c0);                                   // MOVE.L #dd5c6,(A6).
    case 0xdd60c:return ofr2b_callback(c,0xdd618,0xdd612);                                   // MOVE.L #dd618,(A6).
    case 0xdd65e:return ofr2b_callback(c,0xdd66a,0xdd664);                                   // MOVE.L #dd66a,(A6).
    case 0xdd5c0:case 0xdd612:case 0xdd664:if(!ofr2b_put(c,r.a[6],0x76,4,r.d[0]))return false;return am_return(c);   // MOVE.L D0,76(A6); RTS.
    // MOVE.L 76(A6),D0; ADDI.L #60000,D0; CMPI.L #1e000000,D0 (flags not read); MOVE.L D0,76(A6); RTS.
    case 0xdd69c:if(!ofr2b_get(c,r.a[6],0x76,4,value))return false;r.d[0]=value+0x60000U;if(!ofr2b_put(c,r.a[6],0x76,4,r.d[0]))return false;return am_return(c);
    default:return am_error(c,"unsupported animation objects fr2b PC");
    }
}
}
