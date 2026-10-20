#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr2_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ofr2_b(std::uint32_t value) {return value&255U;}
// The low WORD / BYTE as a signed value (BLE / BGE / BPL on WORDs and BYTEs).
std::int32_t ofr2_signed_word(std::uint32_t value) {
    const std::uint32_t w=value&65535U;return (w&0x8000U)!=0U?static_cast<std::int32_t>(w)-65536:static_cast<std::int32_t>(w);
}
std::int32_t ofr2_signed_byte(std::uint32_t value) {
    const std::uint32_t b=value&255U;return (b&0x80U)!=0U?static_cast<std::int32_t>(b)-256:static_cast<std::int32_t>(b);
}
// A LONG as a signed value (CMPI.L / BGE), without relying on a narrowing conversion.
std::int64_t ofr2_signed_long(std::uint32_t value) {
    return (value&0x80000000U)!=0U?static_cast<std::int64_t>(value)-4294967296LL:static_cast<std::int64_t>(value);
}
// ASR.L #count (1..8) of a 32-bit value: arithmetic, the sign bit is replicated (no signed shift in C++).
std::uint32_t ofr2_asr_long(std::uint32_t value,unsigned int count) {
    const std::uint32_t fill=(value&0x80000000U)!=0U?~(0xffffffffU>>count):0U;return (value>>count)|fill;
}
bool ofr2_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr2_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG); the fall-through enters the installed callback.
bool ofr2_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ofr2_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// BCC / BCS on a known C (returned by a callee): clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ofr2_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr2 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ORI.B #1,CCR / ANDI.B #fe,CCR; RTS.
bool ofr2_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// BTST.B #bit,d(An); BEQ.W zero_pc (bit clear); otherwise set_pc.
bool ofr2_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!ofr2_get(c,base,displacement,1,value))return false;c.s.pc=((value>>bit)&1U)==0U?zero_pc:set_pc;return true;
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus).
bool ofr2_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr2_put(c,c.s.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr2_put(c,c.s.a[6],0x22,4,value))return false;
    am_word(c.s.d[0],0x100);c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr2_get(c,c.s.a[6],0x22,4,value))return false;c.s.a[1]=value;
    if(!ofr2_get(c,c.s.a[1],displacement,4,value))return false;c.s.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #d0,D0; MOVE.W #d1,D1; MOVE.B #0,D2; JSR c6a96.l.
bool ofr2_c6a96(AnimationMachineContext& c,std::uint32_t d0,std::uint32_t d1,std::uint32_t return_pc) {
    am_word(c.s.d[0],d0);am_word(c.s.d[1],d1);am_byte(c.s.d[2],0);return am_call(c,0xc6a96,return_pc);
}
// ANDI.W #7fff,D0; ADDI.L #10000,D0; MOVE.L D0,d(A6) (c0ad6 / c0aec).
bool ofr2_speed(AnimationMachineContext& c,std::uint32_t displacement) {
    am_word(c.s.d[0],c.s.d[0]&0x7fffU);c.s.d[0]=c.s.d[0]+0x10000U;return ofr2_put(c,c.s.a[6],displacement,4,c.s.d[0]);
}
// MOVE.L d(A6),D0; ASR.L #4,D0; ADD.L D0,d(A6) (c0b64 / c0b82).
bool ofr2_decay(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ofr2_get(c,c.s.a[6],displacement,4,value))return false;c.s.d[0]=ofr2_asr_long(value,4);
    if(!ofr2_get(c,c.s.a[6],displacement,4,value) || !ofr2_put(c,c.s.a[6],displacement,4,value+c.s.d[0]))return false;c.s.pc=next_pc;return true;
}
// MOVE.B d(A6),D0; LSR.B #6,D0; ADDQ.B #1,D0; LSL.B #3,D0; ADD.B D0,d(A6); SCS.B D0; OR.B D0,d(A6) (b496c / b498a: the C of the BYTE add).
bool ofr2_blink(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    std::uint32_t value=0;AnimationMachineState& r=c.s;if(!ofr2_get(c,r.a[6],displacement,1,value))return false;
    am_byte(r.d[0],((value>>6)+1U)<<3);
    if(!ofr2_get(c,r.a[6],displacement,1,value))return false;const std::uint32_t sum=value+ofr2_b(r.d[0]);
    if(!ofr2_put(c,r.a[6],displacement,1,sum))return false;am_byte(r.d[0],sum>0xffU?0xffU:0U);
    if(!ofr2_get(c,r.a[6],displacement,1,value) || !ofr2_put(c,r.a[6],displacement,1,value|ofr2_b(r.d[0])))return false;r.pc=next_pc;return true;
}
// CMPI.B #ff,d(A6); BEQ.W equal_pc.
bool ofr2_ff(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t equal_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ofr2_get(c,c.s.a[6],displacement,1,value))return false;c.s.pc=value==0xffU?equal_pc:next_pc;return true;
}
// LEA list.l,A0; CMPI.W #8000,(A0); BEQ.W empty_pc (b4772 / b4796).
bool ofr2_player_list(AnimationMachineContext& c,std::uint32_t list,std::uint32_t empty_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;c.s.a[0]=list;if(!am_read(c,list,2,value))return false;c.s.pc=value==0x8000U?empty_pc:next_pc;return true;
}
// LEA b433c(PC),A1; MOVE.W 90(A6),D0; MOVEA.L (A1,D0.W),A1; JSR (A1): the test of the table LONG (live target through the routing).
bool ofr2_table_call(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;AnimationMachineState& r=c.s;
    if(!ofr2_get(c,r.a[6],0x90,2,value))return false;am_word(r.d[0],value);
    if(!am_read(c,am_index(0xb433c,r.d[0]),4,value))return false;r.a[1]=value;return am_call(c,r.a[1],return_pc);
}
// MOVE.W d(A5),Dn; SUB.W 42(A6),Dn; BPL.W next_pc (N of the WORD), otherwise neg_pc (b47c2 / b47d0).
bool ofr2_distance(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t displacement,std::uint32_t next_pc,std::uint32_t neg_pc) {
    std::uint32_t value=0;std::uint32_t other=0;
    if(!ofr2_get(c,c.s.a[5],displacement,2,value) || !ofr2_get(c,c.s.a[6],0x42,2,other))return false;am_word(d,value-other);
    c.s.pc=(d&0x8000U)==0U?next_pc:neg_pc;return true;
}
// MOVE.W -7ff2(A5),D0; ANDI.W #1,D0; BNE.W odd_pc (b489e / b48be).
bool ofr2_frame_bit(AnimationMachineContext& c,std::uint32_t odd_pc,std::uint32_t even_pc) {
    std::uint32_t value=0;if(!ofr2_get(c,c.s.a[5],0x800e,2,value))return false;am_word(c.s.d[0],value&1U);
    c.s.pc=(value&1U)!=0U?odd_pc:even_pc;return true;
}
// ABCD -(A0),-(A1) as the project's original-CPU oracle (Unicorn M68000) computes it, all 131072 inputs (contract decision 3): t = src + 66,
// s = t + dst + X, carry bits c = s ^ (t ^ dst), result = s - ((~c & 110) >> 2 | (~c & 110) >> 3); X = C = bit 8. For two decimal digits this is
// the 68000 definition (low digit > 9 -> +6, sum > 99 -> C).
std::uint32_t ofr2_abcd(std::uint32_t source,std::uint32_t destination,bool& extend) {
    const std::uint32_t t=(source&0xffU)+0x66U;const std::uint32_t s=t+(destination&0xffU)+(extend?1U:0U);
    const std::uint32_t carries=s^(t^(destination&0xffU));const std::uint32_t none=(~carries)&0x110U;
    const std::uint32_t result=s-((none>>2)|(none>>3));extend=((result>>8)&1U)!=0U;return result&0xffU;
}
// e62ce: ADDQ.W #4,A0; ADDI.B #0,D0 (X = 0); ABCD -(A0),-(A1) four times; BCC.W e62ea.
bool ofr2_bcd_add(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;r.a[0]=r.a[0]+4U;bool extend=false;
    for(unsigned int k=0;k<4;++k){std::uint32_t source=0;std::uint32_t destination=0;r.a[0]=r.a[0]-1U;r.a[1]=r.a[1]-1U;
        if(!am_read(c,r.a[0],1,source) || !am_read(c,r.a[1],1,destination) || !am_write(c,r.a[1],1,ofr2_abcd(source,destination,extend)))return false;}
    r.pc=extend?0xe62e0:0xe62ea;return true;
}
// DIVU.W D2,D1 (68000): zero divisor -> checked error (the original takes the vector 5 exception, not modeled); quotient > ffff sets V and
// leaves D1 unchanged; otherwise D1 = remainder:quotient. The flags are not read (TST.B D1 follows).
bool ofr2_divu(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t divisor) {
    const std::uint32_t v=divisor&0xffffU;
    if(v==0U)return am_error(c,"objects fr2 DIVU zero divisor");
    const std::uint32_t quotient=d/v;const std::uint32_t remainder=d%v;
    if(quotient>0xffffU)return true;
    d=(remainder<<16)|quotient;return true;
}
// MOVEA.L -ee(A5),A2 (the menu record pointer, 9ee6 / 9ef8 / 9f12).
bool ofr2_menu_record(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!ofr2_get(c,c.s.a[5],0xff12,4,value))return false;c.s.a[2]=value;return true;
}
}
// Objects FR2a (218 block starts, contract docs/analysis/animation-machine-frontier-fr2-contract.md): the IO-frontier objects c0ace (b3dbc kind
// handler; c0ace..c0ba8, install c0b52) with the shared item routines b4958 (b489e..b4a24, b4760..b4806, b4664..b466c, b4680..b46be, b46c0..b46f6,
// b4ab0, b4aca, b4334..b433c, b442e..b4464, c1d2e), the table tests b4354 / b437a (b4354..b43de) of the LONG table b433c, the item handler b445e, the
// player touch helpers 1c8a4 / 1c1f4, the BCD score add e62a8 (ABCD) and the score display child e991c / e9b5a; the result-screen rank entry e5580
// (e5580..e5614, installs e5596 e55e2) with the rank table helpers e6556 e6516 e65b0 e63ec and the 28ae child maker e693a; the FR1b child b33d8
// (b33d8..b3460, install b342e); the card-menu draw handler a8ee with a770 / a772 (DIVU) and 9ee6 / 9ef8 / 9f12. Every exit is routed except the
// live JSR (A1) targets (item record LONG 4, table b433c, list record LONG 6) and the TRAP #15 sites b466c / e6570. Known C: 1c1f4 (CMP.B borrow;
// Clear when equal -> 1c230 RTS passes it), 1c232 b4374 b43d2 b4458 (ORI; RTS) Set, b43d8 b445e (ANDI; RTS) Clear; b433a (RTS) passes the C of
// 49fc6. The 7 consumers b3454 (288c) b46ac (item handler) b478e b47b2 b491a (table test) b48e8 (289e) b4a18 (1aa7e) read a known C or fail.
// b47f4 recomputes the C of its only predecessor b47de (CMP.W D0,D1); b48ba recomputes the Z of TST.W (A1) (both predecessors) from WORD (A1).
// Data through the live bus (no limit test, as in the original).
bool animation_objects_fr2_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    case 0x1c230:case 0xb433a:case 0xb4434:case 0xb46bc:case 0xb4804:case 0xb4a22:case 0xb345e:case 0xc0ba6:case 0xe559e:case 0xe55ea:case 0xe62cc:
    case 0xe62ea:case 0xe63f8:case 0xe6566:case 0xe65ae:case 0xe65b8:case 0xe65c0:case 0xe65da:case 0x1c8b8:case 0x1c8ee:
        return am_return(c);                                                                  // RTS (1c230 / b433a pass the known C).
    case 0x1c232:case 0xb4374:case 0xb43d2:case 0xb4458:return ofr2_return_carry(c,AnimationCarrySet);     // ORI.B #1,CCR; RTS.
    case 0xb43d8:case 0xb445e:return ofr2_return_carry(c,AnimationCarryClear);                           // ANDI.B #fe,CCR; RTS.
    case 0xb3448:case 0xb3458:case 0xb4a06:case 0xb4a1c:case 0xc1d2e:r.pc=0x2a00;return true;            // JMP 2a00.l.
    // ---- a8ee (card menu record LONG): MOVE.L #d22b,D7; BRA.W a770.
    case 0xa8ee:r.d[7]=0xd22b;r.pc=0xa770;return true;
    case 0xa770:r.d[0]=0;r.pc=0xa772;return true;                                            // MOVEQ #0,D0.
    case 0xa772:if(!am_push(c,4,r.d[7]))return false;return am_call(c,0x9ee6,0xa77a);       // MOVE.L D7,-(A7); JSR 9ee6.l.
    // MOVE.W #fd00,D1; TST.B D7; BNE.W a788 / a784: MOVE.W #fe00,D1.
    case 0xa77a:am_word(r.d[1],0xfd00);r.pc=ofr2_b(r.d[7])!=0U?0xa788:0xa784;return true;
    case 0xa784:am_word(r.d[1],0xfe00);r.pc=0xa788;return true;
    // MOVE.L (A7)+,D7; MOVE.W D1,-(A7); MOVE.L D0,-(A7); MOVE.L D7,-(A7); JSR 9f12.l.
    case 0xa788:
        if(!am_pop(c,4,value))return false;r.d[7]=value;
        if(!am_push(c,2,ofr2_w(r.d[1])) || !am_push(c,4,r.d[0]) || !am_push(c,4,r.d[7]))return false;return am_call(c,0x9f12,0xa796);
    // LSL.W #3,D0; LSL.W #3,D1; ADDQ.W #8,D0; SWAP D0; MOVE.W #1f8,D0; SUB.W D1,D0; MOVE.L D0,-(A7); JSR 9ef8.l.
    case 0xa796:
        am_word(r.d[0],r.d[0]<<3);am_word(r.d[1],r.d[1]<<3);am_word(r.d[0],r.d[0]+8U);am_swap(r.d[0]);am_word(r.d[0],0x1f8U-r.d[1]);
        if(!am_push(c,4,r.d[0]))return false;return am_call(c,0x9ef8,0xa7ac);
    // ANDI.L #ffff,D1; LSL.L #8,D1; DIVU.W D2,D1; TST.B D1; CMPI.W #80,D1; BCS.W a7c2.
    case 0xa7ac:
        r.d[1]=(r.d[1]&0xffffU)<<8;if(!ofr2_divu(c,r.d[1],r.d[2]))return false;r.pc=ofr2_w(r.d[1])<0x80U?0xa7c2:0xa7c0;return true;
    case 0xa7c0:am_word(r.d[1],r.d[1]-1U);r.pc=0xa7c2;return true;                          // SUBQ.W #1,D1.
    // ORI.W #ff00,D1; MOVE.W #ffff,D5; MOVE.L (A7)+,D0; MOVE.L (A7)+,D7; SWAP D0; ADD.W (A7)+,D0; SWAP D0; ADD.W (A7)+,D0; SWAP D1;
    // MOVE.W (A7)+,D1; JMP cd58.l.
    case 0xa7c2:
        am_word(r.d[1],r.d[1]|0xff00U);am_word(r.d[5],0xffff);
        if(!am_pop(c,4,value))return false;r.d[0]=value;if(!am_pop(c,4,value))return false;r.d[7]=value;
        am_swap(r.d[0]);if(!am_pop(c,2,value))return false;am_word(r.d[0],r.d[0]+value);
        am_swap(r.d[0]);if(!am_pop(c,2,value))return false;am_word(r.d[0],r.d[0]+value);
        am_swap(r.d[1]);if(!am_pop(c,2,value))return false;am_word(r.d[1],value);r.pc=0xcd58;return true;
    // MOVEA.L -ee(A5),A2; CMPA.L -f2(A5),A2; SEQ.B D7; RTS.
    case 0x9ee6:
        if(!ofr2_menu_record(c) || !ofr2_get(c,r.a[5],0xff0e,4,value))return false;am_byte(r.d[7],r.a[2]==value?0xffU:0U);return am_return(c);
    // MOVEA.L -ee(A5),A2; MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B b(A2),D0; MOVE.B 4(A2),D1; MOVE.W D0,D2; MOVEQ #0,D3; MOVE.B c(A2),D2; RTS.
    case 0x9ef8:
        if(!ofr2_menu_record(c))return false;r.d[0]=0;r.d[1]=0;if(!ofr2_get(c,r.a[2],0xb,1,value))return false;am_byte(r.d[0],value);
        if(!ofr2_get(c,r.a[2],4,1,value))return false;am_byte(r.d[1],value);am_word(r.d[2],r.d[0]);r.d[3]=0;
        if(!ofr2_get(c,r.a[2],0xc,1,value))return false;am_byte(r.d[2],value);return am_return(c);
    // MOVEA.L -ee(A5),A2; MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B 9(A2),D0; MOVE.B a(A2),D1; RTS.
    case 0x9f12:
        if(!ofr2_menu_record(c))return false;r.d[0]=0;r.d[1]=0;if(!ofr2_get(c,r.a[2],9,1,value))return false;am_byte(r.d[0],value);
        if(!ofr2_get(c,r.a[2],0xa,1,value))return false;am_byte(r.d[1],value);return am_return(c);
    // ---- 1c1f4: MOVEA.L 8c(A0),A4; MOVEQ #0,D1; MOVE.B 4(A4),D1; LEA 1c1c4(PC),A1; MOVE.B (A1,D1.W),D1; MULU.W #3,D0; ADD.W D1,D0; MOVE.B 9e(A0),D1;
    // LEA 1c1c0(PC),A1; MOVE.B (A1,D1.W),D1; MULU.W #4,D0; ADD.W D1,D0; MOVE.B 1c238(PC,D0.W),D0; MOVE.B 9f(A0),D1; MOVE.B D0,a0(A0); CMP.B D0,D1;
    // BNE.W 1c232 (C = the unsigned BYTE borrow; equal -> 1c230 with C Clear).
    case 0x1c1f4:
        if(!ofr2_get(c,r.a[0],0x8c,4,value))return false;r.a[4]=value;r.d[1]=0;if(!ofr2_get(c,r.a[4],4,1,value))return false;am_byte(r.d[1],value);
        r.a[1]=0x1c1c4;if(!am_read(c,am_index(r.a[1],r.d[1]),1,value))return false;am_byte(r.d[1],value);
        r.d[0]=ofr2_w(r.d[0])*3U;am_word(r.d[0],r.d[0]+r.d[1]);
        if(!ofr2_get(c,r.a[0],0x9e,1,value))return false;am_byte(r.d[1],value);
        r.a[1]=0x1c1c0;if(!am_read(c,am_index(r.a[1],r.d[1]),1,value))return false;am_byte(r.d[1],value);
        r.d[0]=ofr2_w(r.d[0])*4U;am_word(r.d[0],r.d[0]+r.d[1]);
        if(!am_read(c,am_index(0x1c238,r.d[0]),1,value))return false;am_byte(r.d[0],value);
        if(!ofr2_get(c,r.a[0],0x9f,1,value))return false;am_byte(r.d[1],value);
        if(!ofr2_put(c,r.a[0],0xa0,1,r.d[0]))return false;
        r.carry=ofr2_b(r.d[1])<ofr2_b(r.d[0])?AnimationCarrySet:AnimationCarryClear;r.pc=ofr2_b(r.d[1])!=ofr2_b(r.d[0])?0x1c232:0x1c230;return true;
    // ---- 1c8a4: MOVE.W D0,-(A7); JSR 1aa3a.l.
    case 0x1c8a4:if(!am_push(c,2,ofr2_w(r.d[0])))return false;return am_call(c,0x1aa3a,0x1c8ac);
    // MOVE.W D0,D1; MOVE.W (A7)+,D0; BTST.B #5,D1; BNE.W 1c8ba.
    case 0x1c8ac:am_word(r.d[1],r.d[0]);if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.pc=((r.d[1]>>5)&1U)!=0U?0x1c8ba:0x1c8b8;return true;
    // LEA 100cb8.l,A0; ANDI.W #1,D0; BEQ.W 1c8ce / 1c8c8: LEA 100da8.l,A0.
    case 0x1c8ba:r.a[0]=0x100cb8;am_word(r.d[0],r.d[0]&1U);r.pc=ofr2_w(r.d[0])==0U?0x1c8ce:0x1c8c8;return true;
    case 0x1c8c8:r.a[0]=0x100da8;r.pc=0x1c8ce;return true;
    // BSET.B #4,a7(A0); MOVEA.L 8c(A0),A4; ADDI.W #1f0,8(A4); CMPI.W #780,8(A4); BCS.W 1c8ee.
    case 0x1c8ce:
        if(!ofr2_get(c,r.a[0],0xa7,1,value) || !ofr2_put(c,r.a[0],0xa7,1,value|0x10U))return false;
        if(!ofr2_get(c,r.a[0],0x8c,4,value))return false;r.a[4]=value;
        if(!ofr2_get(c,r.a[4],8,2,value) || !ofr2_put(c,r.a[4],8,2,value+0x1f0U))return false;
        if(!ofr2_get(c,r.a[4],8,2,value))return false;r.pc=value<0x780U?0x1c8ee:0x1c8e8;return true;
    case 0x1c8e8:r.d[0]=1;return am_call(c,0x1c1f4,0x1c8ee);                                // MOVEQ #1,D0; BSR.W 1c1f4.
    // ---- b33d8 (FR1b 28ae child): MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0xb33d8:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0xb33e2);
    // MOVE.W #e0ed,68(A6); MOVE.W #e0ed,1e(A6); MOVE.W #5e,D0; MOVE.W #2,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xb33e2:if(!ofr2_put(c,r.a[6],0x68,2,0xe0ed) || !ofr2_put(c,r.a[6],0x1e,2,0xe0ed))return false;return ofr2_c6a96(c,0x5e,2,0xb3400);
    case 0xb3400:return ofr2_bank_anim(c,0x15b,0x20017c,8,0xb3428);
    case 0xb3428:return ofr2_install(c,0xb342e);                                              // MOVE.L #b342e,(A6).
    case 0xb342e:return am_call(c,0x43e34,0xb3434);                                           // JSR 43e34.l (installed value).
    case 0xb3434:return am_call(c,0x49fc6,0xb343a);                                           // JSR 49fc6.l.
    // MOVEA.L c(A6),A0; BTST.B #7,61(A0); BEQ.W b344e.
    case 0xb343a:if(!ofr2_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;return ofr2_bit(c,r.a[0],0x61,7,0xb344e,0xb3448);
    case 0xb344e:return am_call(c,0x288c,0xb3454);                                            // JSR 288c.l.
    case 0xb3454:return ofr2_carry(c,0xb3458,0xb345e);                                        // BCS.W b345e (C of 288c).
    // ---- b4334: JSR 49fc6.l (b433a RTS passes its C).
    case 0xb4334:return am_call(c,0x49fc6,0xb433a);
    // ---- b4354 (table b433c): MOVE.W (A0)+,D0; MOVE.L (A0)+,D1; ADD.W D1,D0; SUB.W 4a(A6),D0; CMP.W D1,D0; BCC.W b43d8.
    case 0xb4354:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.a[0]=r.a[0]+2U;
        if(!am_read(c,r.a[0],4,value))return false;r.d[1]=value;r.a[0]=r.a[0]+4U;
        am_word(r.d[0],r.d[0]+r.d[1]);if(!ofr2_get(c,r.a[6],0x4a,2,value))return false;am_word(r.d[0],r.d[0]-value);
        r.pc=ofr2_w(r.d[0])>=ofr2_w(r.d[1])?0xb43d8:0xb4364;return true;
    // SWAP D1; MOVE.W (A0)+,D0; ADD.W D0,D1; SUB.W 4a(A6),D1; CMP.W D0,D1; BCC.W b43d8.
    case 0xb4364:
        am_swap(r.d[1]);if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.a[0]=r.a[0]+2U;
        am_word(r.d[1],r.d[1]+r.d[0]);if(!ofr2_get(c,r.a[6],0x4a,2,value))return false;am_word(r.d[1],r.d[1]-value);
        r.pc=ofr2_w(r.d[1])>=ofr2_w(r.d[0])?0xb43d8:0xb4374;return true;
    // ---- b437a (table b433c): MOVE.L A0,-(A7); JSR b4aca(PC).
    case 0xb437a:if(!am_push(c,4,r.a[0]))return false;return am_call(c,0xb4aca,0xb4380);
    case 0xb4380:r.a[1]=r.a[0];if(!am_pop(c,4,value))return false;r.a[0]=value;r.pc=0xb4388;return true;   // MOVEA.L A0,A1; MOVEA.L (A7)+,A0; BRA.W b4388.
    // MOVE.W (A1)+,D0; MOVE.L (A1)+,D1; BTST.B #0,15(A6); BEQ.W b439a.
    case 0xb4388:
        if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[0],value);r.a[1]=r.a[1]+2U;
        if(!am_read(c,r.a[1],4,value))return false;r.d[1]=value;r.a[1]=r.a[1]+4U;return ofr2_bit(c,r.a[6],0x15,0,0xb439a,0xb4396);
    case 0xb4396:am_word(r.d[0],r.d[0]+r.d[1]);am_word(r.d[0],0U-r.d[0]);r.pc=0xb439a;return true;         // ADD.W D1,D0; NEG.W D0.
    // ADD.W D1,D0; ADD.W 4a(A6),D0; SUB.W (A0),D0; ADD.W 4(A0),D1; CMP.W D1,D0; BCC.W b43d8.
    case 0xb439a:
        am_word(r.d[0],r.d[0]+r.d[1]);if(!ofr2_get(c,r.a[6],0x4a,2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],r.d[0]-value);
        if(!ofr2_get(c,r.a[0],4,2,value))return false;am_word(r.d[1],r.d[1]+value);r.pc=ofr2_w(r.d[0])>=ofr2_w(r.d[1])?0xb43d8:0xb43ac;return true;
    // SWAP D1; MOVE.W (A1)+,D0; BTST.B #1,15(A6); BEQ.W b43be.
    case 0xb43ac:
        am_swap(r.d[1]);if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[0],value);r.a[1]=r.a[1]+2U;return ofr2_bit(c,r.a[6],0x15,1,0xb43be,0xb43ba);
    case 0xb43ba:am_word(r.d[1],r.d[1]+r.d[0]);am_word(r.d[1],0U-r.d[1]);r.pc=0xb43be;return true;         // ADD.W D0,D1; NEG.W D1.
    // ADD.W D0,D1; ADD.W 4e(A6),D1; SUB.W 2(A0),D1; ADD.W 6(A0),D0; CMP.W D0,D1; BCC.W b43d8.
    case 0xb43be:
        am_word(r.d[1],r.d[1]+r.d[0]);if(!ofr2_get(c,r.a[6],0x4e,2,value))return false;am_word(r.d[1],r.d[1]+value);
        if(!ofr2_get(c,r.a[0],2,2,value))return false;am_word(r.d[1],r.d[1]-value);
        if(!ofr2_get(c,r.a[0],6,2,value))return false;am_word(r.d[0],r.d[0]+value);r.pc=ofr2_w(r.d[1])>=ofr2_w(r.d[0])?0xb43d8:0xb43d2;return true;
    // ---- b442e: TST.L (A0); BPL.W b4436.
    case 0xb442e:if(!am_read(c,r.a[0],4,value))return false;r.pc=(value&0x80000000U)==0U?0xb4436:0xb4434;return true;
    // MOVE.W D0,-(A7); ADDQ.W #1,D0; JSR e62a8.l.
    case 0xb4436:if(!am_push(c,2,ofr2_w(r.d[0])))return false;am_word(r.d[0],r.d[0]+1U);return am_call(c,0xe62a8,0xb4440);
    // MOVE.W (A7)+,D0; MOVE.L (A0),D1; JSR e991c.l.
    case 0xb4440:if(!am_pop(c,2,value))return false;am_word(r.d[0],value);if(!am_read(c,r.a[0],4,value))return false;r.d[1]=value;return am_call(c,0xe991c,0xb444a);
    case 0xb444a:return am_call(c,0xb46c0,0xb444e);                                           // JSR b46c0(PC).
    case 0xb444e:am_word(r.d[0],0x1acf);return am_call(c,0x3af8,0xb4458);                    // MOVE.W #1acf,D0; JSR 3af8.l.
    // ---- b4664: CMPI.W #6e,D1; BCS.W b4680 (otherwise the TRAP #15 boundary b466c).
    case 0xb4664:r.pc=ofr2_w(r.d[1])<0x6eU?0xb4680:0xb466c;return true;
    // MULU.W #c,D1; LEA b3894(PC),A0; ADDA.W D1,A0; BTST.B #0,1(A0); BEQ.W b46a2.
    case 0xb4680:r.d[1]=ofr2_w(r.d[1])*0xcU;r.a[0]=am_index(0xb3894,r.d[1]);return ofr2_bit(c,r.a[0],1,0,0xb46a2,0xb4694);
    // MOVEM.L D0/A0,-(A7); JSR 1c8a4.l.
    case 0xb4694:if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.d[0]))return false;return am_call(c,0x1c8a4,0xb469e);
    // MOVEM.L (A7)+,D0/A0.
    case 0xb469e:if(!am_pop(c,4,value))return false;r.d[0]=value;if(!am_pop(c,4,value))return false;r.a[0]=value;r.pc=0xb46a2;return true;
    // MOVEA.L 4(A0),A1; MOVEM.L D0/A0,-(A7); JSR (A1) (the item record handler, live target through the routing).
    case 0xb46a2:
        if(!ofr2_get(c,r.a[0],4,4,value))return false;r.a[1]=value;if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.d[0]))return false;
        return am_call(c,r.a[1],0xb46ac);
    // MOVEM.L (A7)+,D0/A0; BCS.W b46bc (C of the item handler).
    case 0xb46ac:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects fr2 caller requires known carry");
        if(!am_pop(c,4,value))return false;r.d[0]=value;if(!am_pop(c,4,value))return false;r.a[0]=value;return ofr2_carry(c,0xb46b4,0xb46bc);
    case 0xb46b4:r.a[0]=r.a[0]+8U;return am_call(c,0xb442e,0xb46bc);                         // LEA 8(A0),A0; JSR b442e(PC).
    // ---- b46c0: ANDI.W #7,D1; ADD.W D1,D1; MOVE.W b46f6(PC,D1.W),D1; LEA 100cb8.l,A1; TST.B D0; BEQ.W b46dc / b46d6: LEA 100da8.l,A1.
    case 0xb46c0:
        am_word(r.d[1],r.d[1]&7U);am_word(r.d[1],r.d[1]+r.d[1]);if(!am_read(c,am_index(0xb46f6,r.d[1]),2,value))return false;am_word(r.d[1],value);
        r.a[1]=0x100cb8;r.pc=ofr2_b(r.d[0])==0U?0xb46dc:0xb46d6;return true;
    case 0xb46d6:r.a[1]=0x100da8;r.pc=0xb46dc;return true;
    // MOVE.W 42(A1),D0; ADD.W 46(A1),D1; LEA 538e(A5),A1; SUB.W 1c(A1),D0; SUB.W 20(A1),D1; JMP 49260.l.
    case 0xb46dc:
        if(!ofr2_get(c,r.a[1],0x42,2,value))return false;am_word(r.d[0],value);if(!ofr2_get(c,r.a[1],0x46,2,value))return false;am_word(r.d[1],r.d[1]+value);
        r.a[1]=r.a[5]+0x538eU;if(!ofr2_get(c,r.a[1],0x1c,2,value))return false;am_word(r.d[0],r.d[0]-value);
        if(!ofr2_get(c,r.a[1],0x20,2,value))return false;am_word(r.d[1],r.d[1]-value);r.pc=0x49260;return true;
    // ---- b4760: JSR b4aca(PC) / b4764: JMP 1aa7e.l (its RTS returns the C to b4a18).
    case 0xb4760:return am_call(c,0xb4aca,0xb4764);
    case 0xb4764:r.pc=0x1aa7e;return true;
    // ---- b476a: BTST #2,D7; BNE.W b4804.
    case 0xb476a:r.pc=((r.d[7]>>2)&1U)!=0U?0xb4804:0xb4772;return true;
    case 0xb4772:return ofr2_player_list(c,0x10dd48,0xb4796,0xb4780);
    case 0xb4796:return ofr2_player_list(c,0x10dd50,0xb47ba,0xb47a4);
    case 0xb4780:return ofr2_table_call(c,0xb478e);
    case 0xb47a4:return ofr2_table_call(c,0xb47b2);
    case 0xb478e:return ofr2_carry(c,0xb4796,0xb4792);                                        // BCC.W b4796 (C of the table test).
    case 0xb47b2:return ofr2_carry(c,0xb47ba,0xb47b6);
    case 0xb4792:am_byte(r.d[7],r.d[7]|1U);r.pc=0xb4796;return true;                         // ORI.B #1,D7.
    case 0xb47b6:am_byte(r.d[7],r.d[7]|2U);r.pc=0xb47ba;return true;                         // ORI.B #2,D7.
    case 0xb47ba:r.pc=ofr2_b(r.d[7])!=3U?0xb4804:0xb47c2;return true;                        // CMPI.B #3,D7; BNE.W b4804.
    case 0xb47c2:return ofr2_distance(c,r.d[0],0x5d48,0xb47d0,0xb47ce);
    case 0xb47ce:am_word(r.d[0],0U-r.d[0]);r.pc=0xb47d0;return true;                         // NEG.W D0.
    case 0xb47d0:return ofr2_distance(c,r.d[1],0x5d50,0xb47de,0xb47dc);
    case 0xb47dc:am_word(r.d[1],0U-r.d[1]);r.pc=0xb47de;return true;                         // NEG.W D1.
    case 0xb47de:r.pc=ofr2_w(r.d[1])!=ofr2_w(r.d[0])?0xb47f4:0xb47e4;return true;            // CMP.W D0,D1; BNE.W b47f4.
    case 0xb47e4:return am_call(c,0x49a58,0xb47ea);                                           // JSR 49a58.l.
    // ANDI.B #1,D0; ADDQ.B #1,D0; MOVE.B D0,D7; RTS.
    case 0xb47ea:am_byte(r.d[0],(r.d[0]&1U)+1U);am_byte(r.d[7],r.d[0]);return am_return(c);
    // BCC.W b47fe: the C of the only predecessor b47de (CMP.W D0,D1) recomputed from the registers (unsigned D1.W < D0.W).
    case 0xb47f4:r.pc=ofr2_w(r.d[1])<ofr2_w(r.d[0])?0xb47f8:0xb47fe;return true;
    case 0xb47f8:am_byte(r.d[7],2);return am_return(c);                                      // MOVE.B #2,D7; RTS.
    case 0xb47fe:am_byte(r.d[7],1);return am_return(c);                                      // MOVE.B #1,D7; RTS.
    // ---- b489e: MOVE.W D7,-(A7); MOVE.W -7ff2(A5),D0; ANDI.W #1,D0; BNE.W b48b4.
    case 0xb489e:if(!am_push(c,2,ofr2_w(r.d[7])))return false;return ofr2_frame_bit(c,0xb48b4,0xb48ac);
    case 0xb48ac:r.a[1]=r.a[5]+0x5d98U;r.pc=0xb48b8;return true;                             // LEA 5d98(A5),A1; BRA.W b48b8.
    case 0xb48b4:r.a[1]=r.a[5]+0x5d5cU;r.pc=0xb48b8;return true;                             // LEA 5d5c(A5),A1.
    case 0xb48b8:if(!am_read(c,r.a[1],2,value))return false;r.pc=0xb48ba;return true;        // TST.W (A1) (Z recomputed by b48ba).
    // BEQ.W b494c: the Z of TST.W (A1) of both predecessors (b48b8, b4942) recomputed from WORD (A1).
    case 0xb48ba:if(!am_read(c,r.a[1],2,value))return false;r.pc=value==0U?0xb494c:0xb48be;return true;
    case 0xb48be:return ofr2_frame_bit(c,0xb48d2,0xb48ca);
    case 0xb48ca:r.a[2]=r.a[5]+0x5dd4U;r.pc=0xb48d6;return true;                             // LEA 5dd4(A5),A2; BRA.W b48d6.
    case 0xb48d2:r.a[2]=r.a[5]+0x5d98U;r.pc=0xb48d6;return true;                             // LEA 5d98(A5),A2.
    case 0xb48d6:r.pc=r.a[1]==r.a[2]?0xb494c:0xb48dc;return true;                            // CMPA.L A1,A2; BEQ.W b494c.
    // MOVE.L A6,D7; MOVE.W (A1),D7; MOVEA.L D7,A0; JSR 289e.l.
    case 0xb48dc:r.d[7]=r.a[6];if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[7],value);r.a[0]=r.d[7];return am_call(c,0x289e,0xb48e8);
    case 0xb48e8:return ofr2_carry(c,0xb4942,0xb48ec);                                        // BCC.W b4942 (C of 289e).
    // MOVE.L A1,-(A7); MOVEA.L A0,A2; LEA 5dd4(A5),A0; MOVEA.L 2(A1),A3; MOVE.L (A3)+,(A0); MOVE.L (A3)+,4(A0); MOVE.W 42(A2),D0; MOVE.W 46(A2),D1;
    // ADD.W D0,(A0); ADD.W D1,2(A0); LEA b433c(PC),A1; MOVE.W 90(A6),D0; MOVEA.L (A1,D0.W),A1; JSR (A1).
    case 0xb48ec:
        if(!am_push(c,4,r.a[1]))return false;r.a[2]=r.a[0];r.a[0]=r.a[5]+0x5dd4U;if(!ofr2_get(c,r.a[1],2,4,value))return false;r.a[3]=value;
        if(!am_read(c,r.a[3],4,value) || !am_write(c,r.a[0],4,value))return false;r.a[3]=r.a[3]+4U;
        if(!am_read(c,r.a[3],4,value) || !ofr2_put(c,r.a[0],4,4,value))return false;r.a[3]=r.a[3]+4U;
        if(!ofr2_get(c,r.a[2],0x42,2,value))return false;am_word(r.d[0],value);if(!ofr2_get(c,r.a[2],0x46,2,value))return false;am_word(r.d[1],value);
        if(!am_read(c,r.a[0],2,value) || !am_write(c,r.a[0],2,ofr2_w(value+r.d[0])))return false;
        if(!ofr2_get(c,r.a[0],2,2,value) || !ofr2_put(c,r.a[0],2,2,value+r.d[1]))return false;
        return ofr2_table_call(c,0xb491a);
    // MOVEM.L (A7)+,A1; BCC.W b4942 (C of the table test).
    case 0xb491a:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects fr2 caller requires known carry");
        if(!am_pop(c,4,value))return false;r.a[1]=value;return ofr2_carry(c,0xb4942,0xb4922);
    // MOVEM.L A1/A6,-(A7); MOVE.W 8a(A6),D0; MOVE.L A6,D7; MOVE.W (A1),D7; MOVEA.L D7,A6; MOVEA.L 6(A1),A1; JSR (A1) (live target).
    case 0xb4922:
        if(!am_push(c,4,r.a[6]) || !am_push(c,4,r.a[1]))return false;if(!ofr2_get(c,r.a[6],0x8a,2,value))return false;am_word(r.d[0],value);
        r.d[7]=r.a[6];if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[7],value);r.a[6]=r.d[7];
        if(!ofr2_get(c,r.a[1],6,4,value))return false;r.a[1]=value;return am_call(c,r.a[1],0xb4936);
    // MOVEM.L (A7)+,A1/A6; CMP.W 8a(A6),D0; BNE.W b4950.
    case 0xb4936:
        if(!am_pop(c,4,value))return false;r.a[1]=value;if(!am_pop(c,4,value))return false;r.a[6]=value;
        if(!ofr2_get(c,r.a[6],0x8a,2,value))return false;r.pc=ofr2_w(r.d[0])!=value?0xb4950:0xb4942;return true;
    // ADDA.W #a,A1; TST.W (A1); BRA.W b48ba.
    case 0xb4942:r.a[1]=r.a[1]+0xaU;if(!am_read(c,r.a[1],2,value))return false;r.pc=0xb48ba;return true;
    case 0xb494c:if(!am_pop(c,2,value))return false;am_word(r.d[7],value);return am_return(c);                          // MOVE.W (A7)+,D7; RTS.
    case 0xb4950:if(!am_pop(c,2,value))return false;am_word(r.d[7],value);am_byte(r.d[7],r.d[7]|4U);return am_return(c);  // ...; ORI.B #4,D7; RTS.
    // ---- b4958 (shared item update): BTST.B #3,95(A6); BNE.W b499e.
    case 0xb4958:return ofr2_bit(c,r.a[6],0x95,3,0xb4962,0xb499e);
    case 0xb4962:return ofr2_ff(c,0x12,0xb4980,0xb496c);                                      // CMPI.B #ff,12(A6); BEQ.W b4980.
    case 0xb496c:return ofr2_blink(c,0x12,0xb4980);
    case 0xb4980:return ofr2_ff(c,0x13,0xb499e,0xb498a);
    case 0xb498a:return ofr2_blink(c,0x13,0xb499e);
    case 0xb499e:return ofr2_bit(c,r.a[6],0x96,2,0xb49a8,0xb49e4);                           // BTST.B #2,96(A6); BNE.W b49e4.
    case 0xb49a8:if(!ofr2_get(c,r.a[6],0x94,1,value))return false;r.pc=value==0U?0xb49b8:0xb49b0;return true;    // TST.B 94(A6); BEQ.W b49b8.
    case 0xb49b0:if(!ofr2_get(c,r.a[6],0x94,1,value) || !ofr2_put(c,r.a[6],0x94,1,value-1U))return false;r.pc=0xb49e4;return true;
    case 0xb49b8:r.d[7]=0;return am_call(c,0xb489e,0xb49be);                                 // MOVEQ #0,D7; JSR b489e(PC).
    case 0xb49be:return am_call(c,0xb476a,0xb49c2);                                           // JSR b476a(PC).
    case 0xb49c2:r.pc=ofr2_b(r.d[7])==0U?0xb49e4:0xb49c8;return true;                        // TST.B D7; BEQ.W b49e4.
    // ORI.B #4,D7; OR.B D7,96(A6); MOVE.B D7,D0; ANDI.W #3,D0; BEQ.W b49e4.
    case 0xb49c8:
        am_byte(r.d[7],r.d[7]|4U);if(!ofr2_get(c,r.a[6],0x96,1,value) || !ofr2_put(c,r.a[6],0x96,1,value|ofr2_b(r.d[7])))return false;
        am_byte(r.d[0],r.d[7]);am_word(r.d[0],r.d[0]&3U);r.pc=ofr2_w(r.d[0])==0U?0xb49e4:0xb49da;return true;
    // SUBQ.W #1,D0; MOVE.W 8a(A6),D1; BRA.W b4664.
    case 0xb49da:am_word(r.d[0],r.d[0]-1U);if(!ofr2_get(c,r.a[6],0x8a,2,value))return false;am_word(r.d[1],value);r.pc=0xb4664;return true;
    // MOVE.W 8c(A6),D0; BEQ.W b4a14.
    case 0xb49e4:if(!ofr2_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],value);r.pc=ofr2_w(value)==0U?0xb4a14:0xb49ec;return true;
    case 0xb49ec:am_word(r.d[0],r.d[0]-1U);r.pc=ofr2_w(r.d[0])!=0U?0xb4a10:0xb49f2;return true;          // SUBQ.W #1,D0; BNE.W b4a10.
    case 0xb49f2:return ofr2_bit(c,r.a[6],0x95,4,0xb49fc,0xb4a10);                           // BTST.B #4,95(A6); BNE.W b4a10.
    // BSET.B #3,61(A6); BEQ.W b4a0c (the old bit was clear).
    case 0xb49fc:
        if(!ofr2_get(c,r.a[6],0x61,1,value) || !ofr2_put(c,r.a[6],0x61,1,value|8U))return false;r.pc=(value&8U)==0U?0xb4a0c:0xb4a06;return true;
    case 0xb4a0c:am_word(r.d[0],0x24);r.pc=0xb4a10;return true;                              // MOVE.W #24,D0.
    case 0xb4a10:if(!ofr2_put(c,r.a[6],0x8c,2,r.d[0]))return false;r.pc=0xb4a14;return true;  // MOVE.W D0,8c(A6).
    case 0xb4a14:return am_call(c,0xb4760,0xb4a18);                                           // JSR b4760(PC).
    case 0xb4a18:return ofr2_carry(c,0xb4a22,0xb4a1c);                                        // BCC.W b4a22 (C of 1aa7e).
    case 0xb4ab0:if(!ofr2_get(c,r.a[6],0x96,1,value))return false;am_byte(r.d[0],value);return am_return(c);   // MOVE.B 96(A6),D0; RTS.
    // MOVE.W 90(A6),D0; MOVEA.L b4ad4(PC,D0.W),A0; RTS.
    case 0xb4aca:
        if(!ofr2_get(c,r.a[6],0x90,2,value))return false;am_word(r.d[0],value);if(!am_read(c,am_index(0xb4ad4,r.d[0]),4,value))return false;
        r.a[0]=value;return am_return(c);
    // ---- c0ace (b3dbc kind handler): MOVEQ #0,D0; JSR 49a58.l.
    case 0xc0ace:r.d[0]=0;return am_call(c,0x49a58,0xc0ad6);
    case 0xc0ad6:if(!ofr2_speed(c,0x36))return false;r.d[0]=0;return am_call(c,0x49a58,0xc0aec);          // ...; MOVE.L D0,36(A6); MOVEQ #0,D0; JSR 49a58.l.
    case 0xc0aec:if(!ofr2_speed(c,0x3a))return false;am_word(r.d[0],0x1836);return am_call(c,0x3af8,0xc0b04);   // ...; MOVE.W #1836,D0; JSR 3af8.l.
    case 0xc0b04:return ofr2_bit(c,r.a[6],0x15,0,0xc0b0e,0xc0b12);                           // BTST.B #0,15(A6); BNE.W c0b12.
    case 0xc0b0e:if(!ofr2_get(c,r.a[6],0x36,4,value) || !ofr2_put(c,r.a[6],0x36,4,0U-value))return false;r.pc=0xc0b12;return true;  // NEG.L 36(A6).
    case 0xc0b12:return ofr2_c6a96(c,0x70,5,0xc0b24);
    case 0xc0b24:return ofr2_bank_anim(c,0x1eb,0x2001c4,0x14,0xc0b4c);
    case 0xc0b4c:return ofr2_install(c,0xc0b52);                                              // MOVE.L #c0b52,(A6).
    case 0xc0b52:return am_call(c,0x43ea4,0xc0b58);                                           // JSR 43ea4.l (installed value).
    // CMPI.L #20000,3a(A6); BGE.W c0b6e (signed LONG).
    case 0xc0b58:if(!ofr2_get(c,r.a[6],0x3a,4,value))return false;r.pc=ofr2_signed_long(value)>=0x20000LL?0xc0b6e:0xc0b64;return true;
    case 0xc0b64:return ofr2_decay(c,0x3a,0xc0b6e);
    // MOVE.L 36(A6),D0; ADDI.L #28000,D0; CMPI.L #50000,D0; BCC.W c0b8c (unsigned).
    case 0xc0b6e:if(!ofr2_get(c,r.a[6],0x36,4,value))return false;r.d[0]=value+0x28000U;r.pc=r.d[0]>=0x50000U?0xc0b8c:0xc0b82;return true;
    case 0xc0b82:return ofr2_decay(c,0x36,0xc0b8c);
    case 0xc0b8c:return am_call(c,0xb4958,0xc0b92);                                           // JSR b4958.l.
    case 0xc0b92:return am_call(c,0xb4ab0,0xc0b98);                                           // JSR b4ab0.l.
    case 0xc0b98:r.pc=((r.d[0]>>2)&1U)!=0U?0xc1d2e:0xc0ba0;return true;                      // BTST #2,D0; BNE.W c1d2e.
    case 0xc0ba0:return am_call(c,0xb4334,0xc0ba6);                                           // JSR b4334.l.
    // ---- e5580 (e5324 28ae child): CMPI.W #a,80(A6); BCS.W e55a4.
    case 0xe5580:if(!ofr2_get(c,r.a[6],0x80,2,value))return false;r.pc=value<0xaU?0xe55a4:0xe558a;return true;
    case 0xe558a:if(!ofr2_put(c,r.a[6],0x7a,2,0x3c))return false;return ofr2_install(c,0xe5596);         // MOVE.W #3c,7a(A6); MOVE.L #e5596,(A6).
    // SUBQ.W #1,7a(A6); BEQ.W e55a0 (installed value).
    case 0xe5596:
        if(!ofr2_get(c,r.a[6],0x7a,2,value))return false;value=ofr2_w(value-1U);if(!ofr2_put(c,r.a[6],0x7a,2,value))return false;
        r.pc=value==0U?0xe55a0:0xe559e;return true;
    case 0xe55a0:r.pc=0xe5606;return true;                                                    // BRA.W e5606.
    case 0xe55a4:if(!ofr2_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[0],value);return am_call(c,0xe693a,0xe55ae);   // MOVE.W 80(A6),D0; JSR e693a.l.
    // MOVE.W 7c(A6),76(A0); BNE.W e55c6.
    case 0xe55ae:if(!ofr2_get(c,r.a[6],0x7c,2,value) || !ofr2_put(c,r.a[0],0x76,2,value))return false;r.pc=value!=0U?0xe55c6:0xe55b8;return true;
    case 0xe55b8:am_word(r.d[0],0x70d8);r.a[1]=0x10de18;r.pc=0xe55d0;return true;            // MOVE.W #70d8,D0; LEA 10de18.l,A1; BRA.W e55d0.
    case 0xe55c6:am_word(r.d[0],0x7318);r.a[1]=0x10de20;r.pc=0xe55d0;return true;            // MOVE.W #7318,D0; LEA 10de20.l,A1.
    // MOVE.W D0,78(A0); MOVE.L A1,7a(A0); CLR.B 62(A6); MOVE.L #e55e2,(A6).
    case 0xe55d0:
        if(!ofr2_put(c,r.a[0],0x78,2,r.d[0]) || !ofr2_put(c,r.a[0],0x7a,4,r.a[1]) || !ofr2_put(c,r.a[6],0x62,1,0))return false;return ofr2_install(c,0xe55e2);
    case 0xe55e2:if(!ofr2_get(c,r.a[6],0x62,1,value))return false;r.pc=value!=0U?0xe55ec:0xe55ea;return true;   // TST.B 62(A6); BNE.W e55ec.
    // LEA 10de14.l,A0; TST.W 7c(A6); BEQ.W e5600 / e55fa: LEA 10de1c.l,A0.
    case 0xe55ec:r.a[0]=0x10de14;if(!ofr2_get(c,r.a[6],0x7c,2,value))return false;r.pc=value==0U?0xe5600:0xe55fa;return true;
    case 0xe55fa:r.a[0]=0x10de1c;r.pc=0xe5600;return true;
    case 0xe5600:return am_call(c,0xe6556,0xe5606);                                           // JSR e6556.l.
    // MOVEA.L c(A6),A0; ST.B 62(A0); JMP 2a00.l.
    case 0xe5606:if(!ofr2_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr2_put(c,r.a[0],0x62,1,0xff))return false;r.pc=0x2a00;return true;
    // ---- e62a8: BTST #0,D0; BEQ.W e62ba / e62b0: LEA 10de18.l,A1; BSR.W e62ce.
    case 0xe62a8:r.pc=(r.d[0]&1U)==0U?0xe62ba:0xe62b0;return true;
    case 0xe62b0:r.a[1]=0x10de18;return am_call(c,0xe62ce,0xe62ba);
    case 0xe62ba:r.pc=(r.d[0]&2U)==0U?0xe62cc:0xe62c2;return true;                           // BTST #1,D0; BEQ.W e62cc.
    case 0xe62c2:r.a[1]=0x10de20;return am_call(c,0xe62ce,0xe62cc);
    case 0xe62ce:return ofr2_bcd_add(c);
    // MOVE.W #9999,(A1); MOVE.B #99,2(A1).
    case 0xe62e0:if(!am_write(c,r.a[1],2,0x9999) || !ofr2_put(c,r.a[1],2,1,0x99))return false;r.pc=0xe62ea;return true;
    // ---- e63ec: SUBQ.W #1,D0; BCS.W e63f8 (the old WORD was 0).
    case 0xe63ec:value=ofr2_w(r.d[0]);am_word(r.d[0],r.d[0]-1U);r.pc=value==0U?0xe63f8:0xe63f2;return true;
    // MOVE.B (A0)+,(A1)+; DBRA D0,e63f2.
    case 0xe63f2:
        if(!am_read(c,r.a[0],1,value) || !am_write(c,r.a[1],1,value))return false;r.a[0]=r.a[0]+1U;r.a[1]=r.a[1]+1U;
        am_word(r.d[0],r.d[0]-1U);r.pc=ofr2_w(r.d[0])!=0xffffU?0xe63f2:0xe63f8;return true;
    // ---- e6516: LEA 10f02e.l,A1; MOVEQ #1,D0; MOVEQ #1,D1; MOVE.L (A0),D3.
    case 0xe6516:r.a[1]=0x10f02e;r.d[0]=1;r.d[1]=1;if(!am_read(c,r.a[0],4,value))return false;r.d[3]=value;r.pc=0xe6522;return true;
    // MOVE.L (A1),D4; CMP.L D4,D3; BCC.W e652e (unsigned D3 >= D4).
    case 0xe6522:if(!am_read(c,r.a[1],4,value))return false;r.d[4]=value;r.pc=r.d[3]>=r.d[4]?0xe652e:0xe652a;return true;
    case 0xe652a:am_word(r.d[0],r.d[1]);am_word(r.d[0],r.d[0]+1U);r.pc=0xe652e;return true;  // MOVE.W D1,D0; ADDQ.W #1,D0.
    // CMP.L D4,D3; BHI.W e6552; BCS.W e6540.
    case 0xe652e:r.pc=r.d[3]>r.d[4]?0xe6552:(r.d[3]<r.d[4]?0xe6540:0xe6538);return true;
    case 0xe6538:r.pc=ofr2_w(r.d[1])==0xaU?0xe654c:0xe6540;return true;                      // CMPI.W #a,D1; BEQ.W e654c.
    // ADDA.W #8,A1; ADDQ.W #1,D1; CMPI.W #a,D1; BLE.B e6522 (signed WORD).
    case 0xe6540:r.a[1]=r.a[1]+8U;am_word(r.d[1],r.d[1]+1U);r.pc=ofr2_signed_word(r.d[1])<=0xa?0xe6522:0xe654c;return true;
    case 0xe654c:r.d[0]=0xffffffffU;r.d[1]=0xffffffffU;return am_return(c);                 // MOVEQ #ff,D0; MOVEQ #ff,D1; RTS.
    case 0xe6552:am_word(r.d[1],r.d[1]-1U);return am_return(c);                             // SUBQ.W #1,D1; RTS.
    case 0xe6556:if(!am_push(c,4,r.a[0]))return false;return am_call(c,0xe6516,0xe655c);   // MOVE.L A0,-(A7); JSR e6516(PC).
    // MOVEA.L (A7)+,A0; CMPI.W #a,D0; BLS.W e6568 (unsigned).
    case 0xe655c:if(!am_pop(c,4,value))return false;r.a[0]=value;r.pc=ofr2_w(r.d[0])<=0xaU?0xe6568:0xe6566;return true;
    // CMPI.W #a,D0; BLE.W e6582 (signed; otherwise the TRAP #15 boundary e6570, never reached from e655c: contract decision 6).
    case 0xe6568:r.pc=ofr2_signed_word(r.d[0])<=0xa?0xe6582:0xe6570;return true;
    case 0xe6582:r.d[1]=0xa;r.pc=0xe6584;return true;                                        // MOVEQ #a,D1.
    // MOVEM.L D0-D1/A0,-(A7); JSR e65b0(PC).
    case 0xe6584:if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;return am_call(c,0xe65b0,0xe658c);
    // MOVEM.L (A7)+,D0-D1/A0; CMP.W D0,D1; BEQ.W e659a.
    case 0xe658c:
        if(!am_pop(c,4,value))return false;r.d[0]=value;if(!am_pop(c,4,value))return false;r.d[1]=value;if(!am_pop(c,4,value))return false;r.a[0]=value;
        r.pc=ofr2_w(r.d[1])==ofr2_w(r.d[0])?0xe659a:0xe6596;return true;
    case 0xe6596:am_word(r.d[1],r.d[1]-1U);r.pc=0xe6584;return true;                         // SUBQ.W #1,D1; BRA.B e6584.
    // SUBQ.W #1,D0; MULU.W #8,D0; LEA 10f02e.l,A1; ADDA.W D0,A1; MOVEQ #8,D0; JSR e63ec(PC).
    case 0xe659a:am_word(r.d[0],r.d[0]-1U);r.d[0]=ofr2_w(r.d[0])*8U;r.a[1]=am_index(0x10f02e,r.d[0]);r.d[0]=8;return am_call(c,0xe63ec,0xe65ae);
    case 0xe65b0:r.pc=ofr2_signed_word(r.d[1])<=0xa?0xe65ba:0xe65b8;return true;            // CMPI.W #a,D1; BLE.W e65ba.
    case 0xe65ba:am_word(r.d[1],r.d[1]-1U);r.pc=(r.d[1]&0x8000U)==0U?0xe65c2:0xe65c0;return true;   // SUBQ.W #1,D1; BPL.W e65c2.
    // MULU.W #8,D1; LEA 10f02e.l,A1; ADDA.W D1,A1; MOVEA.L A1,A0; SUBA.W #8,A0; MOVEQ #8,D0; JSR e63ec(PC).
    case 0xe65c2:r.d[1]=ofr2_w(r.d[1])*8U;r.a[1]=am_index(0x10f02e,r.d[1]);r.a[0]=r.a[1]-8U;r.d[0]=8;return am_call(c,0xe63ec,0xe65da);
    // ---- e693a: MOVE.W D0,-(A7); MOVEA.L #e6952,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0xe693a:if(!am_push(c,2,ofr2_w(r.d[0])))return false;r.a[0]=0xe6952;am_word(r.d[0],0x14);return am_call(c,0x28ae,0xe694c);
    case 0xe694c:if(!am_pop(c,2,value) || !ofr2_put(c,r.a[0],0x7e,2,value))return false;return am_return(c);   // MOVE.W (A7)+,7e(A0); RTS.
    // ---- e991c: MOVE.L D1,-(A7); JSR e9b5a(PC).
    case 0xe991c:if(!am_push(c,4,r.d[1]))return false;return am_call(c,0xe9b5a,0xe9922);
    // MOVE.L (A7)+,D3; LEA 76(A0),A1; MOVEQ #0,D7; MOVEQ #7,D4; MOVE.B #7,D6.
    case 0xe9922:if(!am_pop(c,4,value))return false;r.d[3]=value;r.a[1]=r.a[0]+0x76U;r.d[7]=0;r.d[4]=7;am_byte(r.d[6],7);r.pc=0xe9930;return true;
    // ROL.L #4,D3; MOVE.B D3,D5; ANDI.B #f,D5; BNE.W e9942.
    case 0xe9930:r.d[3]=(r.d[3]<<4)|(r.d[3]>>28);am_byte(r.d[5],r.d[3]&0xfU);r.pc=ofr2_b(r.d[5])!=0U?0xe9942:0xe993c;return true;
    // SUBQ.B #1,D6; BGE.W e9952 (N = V: the old signed BYTE was >= 1).
    case 0xe993c:other=r.d[6];am_byte(r.d[6],r.d[6]-1U);r.pc=ofr2_signed_byte(other)>=1?0xe9952:0xe9942;return true;
    // MOVE.B D5,D6; ADD.B D5,D5; ADD.B D6,D5; MOVE.B D5,(A1,D7.W); ADDQ.W #1,D7; MOVE.B #0,D6.
    case 0xe9942:
        am_byte(r.d[6],r.d[5]);am_byte(r.d[5],r.d[5]+r.d[5]);am_byte(r.d[5],r.d[5]+r.d[6]);
        if(!am_write(c,am_index(r.a[1],r.d[7]),1,ofr2_b(r.d[5])))return false;am_word(r.d[7],r.d[7]+1U);am_byte(r.d[6],0);r.pc=0xe9952;return true;
    case 0xe9952:am_word(r.d[4],r.d[4]-1U);r.pc=ofr2_w(r.d[4])!=0xffffU?0xe9930:0xe9956;return true;      // DBRA D4,e9930.
    case 0xe9956:if(!ofr2_put(c,r.a[0],0x8f,1,r.d[7]))return false;return am_return(c);   // MOVE.B D7,8f(A0); RTS.
    // MOVE.W D0,-(A7); MOVEA.L #e9b8a,A0; MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0xe9b5a:if(!am_push(c,2,ofr2_w(r.d[0])))return false;r.a[0]=0xe9b8a;am_word(r.d[0],0xa);r.a[1]=0x100bf4;return am_call(c,0x2986,0xe9b72);
    // MOVE.W (A7)+,D0; MOVE.W D0,88(A0); LEA 5e4a(A5),A1; ADDA.W D0,A1; ADDA.W D0,A1; MOVE.W (A1),D1; MOVE.W D1,8a(A0); ADDQ.W #1,(A1); RTS.
    case 0xe9b72:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);if(!ofr2_put(c,r.a[0],0x88,2,r.d[0]))return false;
        r.a[1]=am_index(am_index(r.a[5]+0x5e4aU,r.d[0]),r.d[0]);if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[1],value);
        if(!ofr2_put(c,r.a[0],0x8a,2,r.d[1]) || !am_read(c,r.a[1],2,value) || !am_write(c,r.a[1],2,ofr2_w(value+1U)))return false;return am_return(c);
    default:return am_error(c,"unsupported animation objects fr2 PC");
    }
}
}
