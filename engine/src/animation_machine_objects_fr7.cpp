#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr7_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ofr7_b(std::uint32_t value) {return value&255U;}
// Signed value of the low WORD (CMPI.W + BLE, MULS.W operands).
int ofr7_sw(std::uint32_t value) {const int v=static_cast<int>(value&65535U);return v>=32768?v-65536:v;}
bool ofr7_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr7_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BCLR.B / BSET.B #bit,d(An): read-modify-write of one BYTE.
bool ofr7_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!ofr7_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;return ofr7_put(c,base,displacement,1,set?(value|mask):(value&~mask));
}
// BTST.B #bit,d(An); BEQ zero_pc (bit clear) / one_pc (bit set).
bool ofr7_btst(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    std::uint32_t value=0;if(!ofr7_get(c,base,displacement,1,value))return false;
    c.s.pc=(value&(1U<<bit))==0U?zero_pc:one_pc;return true;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool ofr7_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr7 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ASR.L #n (1..8): arithmetic shift of the LONG (the sign bit is replicated; no signed shift in C++).
std::uint32_t ofr7_asr(std::uint32_t value,unsigned int n) {return (value>>n)|((value&0x80000000U)!=0U?~(0xffffffffU>>n):0U);}
// ASR.W #1: arithmetic shift of the low WORD by one (bit 15 is kept).
std::uint32_t ofr7_asr_word1(std::uint32_t value) {const std::uint32_t w=ofr7_w(value);return (w>>1)|(w&0x8000U);}
// MULS.W: signed WORD x signed WORD = LONG (|product| <= 2^30, no int overflow; the conversion to uint32 is modulo 2^32).
std::uint32_t ofr7_muls(std::uint32_t a,std::uint32_t b) {return static_cast<std::uint32_t>(ofr7_sw(a)*ofr7_sw(b));}
// Signed LONG a <= b without a signed conversion: compare with the sign bits flipped.
bool ofr7_le_long(std::uint32_t a,std::uint32_t b) {return (a^0x80000000U)<=(b^0x80000000U);}
// ADD.W Dy,Dx; NEG.W Dx: Dx.W := -(Dx.W + Dy.W) (the upper WORD of Dx kept).
void ofr7_negadd(std::uint32_t& x,std::uint32_t y) {am_word(x,0U-(x+y));}
// ASR.W #1,D2; ADD.W D0,D2; LSR.W #1,D2 (the midpoint of 4ae0e).
void ofr7_mid(std::uint32_t& d2,std::uint32_t d0) {am_word(d2,ofr7_asr_word1(d2));am_word(d2,d2+d0);am_word(d2,ofr7_w(d2)>>1);}
// 4add8 / 4adfe: ADD.W field(A2),D2; ADD.W D3,D2; SUB.W D0,D2; ADD.W D1,D3; CMP.W D3,D2; BCC.W miss_pc (unsigned D2.W >= D3.W) / hit_pc.
bool ofr7_span(AnimationMachineContext& c,std::uint32_t field,std::uint32_t miss_pc,std::uint32_t hit_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!ofr7_get(c,r.a[2],field,2,value))return false;
    am_word(r.d[2],r.d[2]+value);am_word(r.d[2],r.d[2]+r.d[3]);am_word(r.d[2],r.d[2]-r.d[0]);am_word(r.d[3],r.d[3]+r.d[1]);
    r.pc=ofr7_w(r.d[2])>=ofr7_w(r.d[3])?miss_pc:hit_pc;return true;
}
// 4abe6 / 4abf6 / 4ac00: ASR.W #1,D3; BCC.W skip_pc (the bit shifted out is 0) / add_pc.
void ofr7_shift_test(AnimationMachineContext& c,std::uint32_t skip_pc,std::uint32_t add_pc) {
    AnimationMachineState& r=c.s;const bool out=(r.d[3]&1U)!=0U;am_word(r.d[3],ofr7_asr_word1(r.d[3]));r.pc=out?add_pc:skip_pc;
}
// 4abf2 / 4abfc / 4ac06: ADD.W field(A0),D2.
bool ofr7_add_damage(AnimationMachineContext& c,std::uint32_t field,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ofr7_get(c,c.s.a[0],field,2,value))return false;am_word(c.s.d[2],c.s.d[2]+value);c.s.pc=next_pc;return true;
}
// 4c112 / 4c16c: MOVE.L 42(A6),D0; MOVE.L 46(A6),D1; MOVE.L (A7),D3; NEG.L D3; MOVEA.W #0,A0; JSR 46d72.l.
bool ofr7_probe(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr7_get(c,r.a[6],0x42,4,r.d[0]) || !ofr7_get(c,r.a[6],0x46,4,r.d[1]) || !am_read(c,r.a[7],4,value))return false;
    r.d[3]=0U-value;r.a[0]=0;return am_call(c,0x46d72,return_pc);
}
// 4c12c / 4c186: CMP.L (A7),D6; BCC.W done_pc (unsigned D6 >= LONG (A7)) / next_pc.
bool ofr7_height(AnimationMachineContext& c,std::uint32_t done_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[7],4,value))return false;c.s.pc=c.s.d[6]>=value?done_pc:next_pc;return true;
}
// 4c132 / 4c18c: SUBQ.W #1,4(A7); BCC.W done_pc (no borrow: the WORD was not 0) / next_pc.
bool ofr7_count(AnimationMachineContext& c,std::uint32_t done_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;const std::uint32_t at=c.s.a[7]+4U;
    if(!am_read(c,at,2,value) || !am_write(c,at,2,ofr7_w(value-1U)))return false;c.s.pc=value!=0U?done_pc:next_pc;return true;
}
// 4c14a / 4c15c / 4c1a4: MOVE.W #4,4(A7).
bool ofr7_reset(AnimationMachineContext& c,std::uint32_t next_pc) {if(!am_write(c,c.s.a[7]+4U,2,4))return false;c.s.pc=next_pc;return true;}
// 4c150 / 4c1aa: SUBQ.W #5 / ADDQ.W #5,42(A6); BRA.B loop_pc.
bool ofr7_step_x(AnimationMachineContext& c,std::uint32_t addend,std::uint32_t loop_pc) {
    std::uint32_t value=0;if(!ofr7_get(c,c.s.a[6],0x42,2,value) || !ofr7_put(c,c.s.a[6],0x42,2,value+addend))return false;c.s.pc=loop_pc;return true;
}
// 4c13a / 4c194: MOVE.W 42(A6),D0; ADDI.W / SUBI.W #a,D0; BRA.W 4c1be.
bool ofr7_land(AnimationMachineContext& c,std::uint32_t addend) {
    std::uint32_t value=0;if(!ofr7_get(c,c.s.a[6],0x42,2,value))return false;am_word(c.s.d[0],value+addend);c.s.pc=0x4c1be;return true;
}
// ADDQ.W #6,A7; ANDI.B #fe,CCR / ORI.B #1,CCR; RTS (4c1b6 Clear / 4c1d6 Set): the block sets its own C.
bool ofr7_frame_return(AnimationMachineContext& c,AnimationCarryState carry) {c.s.a[7]=c.s.a[7]+6U;c.s.carry=carry;return am_return(c);}
// d2776 d2782 d278e d279a: MOVE.W #167,D0; LEA record(PC),A0; BRA.W d2f90.
bool ofr7_stub(AnimationMachineContext& c,std::uint32_t record) {am_word(c.s.d[0],0x167);c.s.a[0]=record;c.s.pc=0xd2f90;return true;}
}
// Objects FR7 (205 block starts, contract docs/analysis/animation-machine-frontier-fr7-contract.md): the C-gated area-D roots after FR6, the hit test
// 4ad6c (BSR from the 64 N08 candidate blocks) with the damage part 4abc0 (BRA from 4ae2a) and the ground search 4c0f0, the tail e8b7e / e8b80 of
// the C helper e8b5a (e8b80 is the target of its BEQ.W e8b7a), the object cde42 (28ae child of cddee; install cded2), the table handler 36118, the
// objects d2776 d2782 d278e d279a with their tail d2f90 (install d3062), the object cdd2e with cc5e8 / cc958, and the object 3ad48 (2986 child of
// B2E 3ac2c; install 3add4) with the sound helper 4356e.  No computed jump, no TRAP; every exit is a routed block start.  MOVE.L #v,(A6) always
// installs the next PC here (3add4 cded2 d3062).  The 8 consumers 3ae78 d308e (1ab80), 4c128 4c182 (46d72), cdd3c cdede d3080 (49fc6) and cde9c
// (497a6) read a known C or fail; 4c1b6 (ANDI; RTS) / 4c1d6 (ORI; RTS) set their own C.  Data through the live bus (no limit test).
bool animation_objects_fr7_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    case 0x36126:case 0x3ae82:case 0x4358a:case 0x4ad6a:case 0x4ae48:case 0xcc5fe:case 0xcdd84:case 0xcdee8:case 0xd3092:
        return am_return(c);                                                                              // RTS.
    case 0x3adfe:case 0x3ae7c:case 0xcc5e2:case 0xcdd40:case 0xcdd78:case 0xcdee2:case 0xd3094:
        r.pc=0x2a00;return true;                                                                          // JMP 2a00.l.
    // ---- 36118 (handler of the LONG table 4a55c): JSR 1aa3a.l / BTST.B #2,D0; BNE.W 36128 / RTS.
    case 0x36118:return am_call(c,0x1aa3a,0x3611e);
    case 0x3611e:r.pc=(r.d[0]&4U)!=0U?0x36128U:0x36126U;return true;
    // MOVE.L A0,-(A7); MOVEA.L #3614a,A0 (28ae child value); MOVE.W #1e,D0; JSR 28ae.l.
    case 0x36128:if(!am_push(c,4,r.a[0]))return false;r.a[0]=0x3614a;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0x3613a);
    // MOVEA.L (A7)+,A1; MOVE.W (A1)+,2e(A0); MOVE.W (A1)+,32(A0); MOVE.W (A1)+,68(A0); RTS.
    case 0x3613a:
        if(!am_pop(c,4,value))return false;r.a[1]=value;
        if(!am_read(c,r.a[1],2,value))return false;r.a[1]=r.a[1]+2U;if(!ofr7_put(c,r.a[0],0x2e,2,value))return false;
        if(!am_read(c,r.a[1],2,value))return false;r.a[1]=r.a[1]+2U;if(!ofr7_put(c,r.a[0],0x32,2,value))return false;
        if(!am_read(c,r.a[1],2,value))return false;r.a[1]=r.a[1]+2U;if(!ofr7_put(c,r.a[0],0x68,2,value))return false;
        return am_return(c);
    // ---- 3ad48 (2986 child of B2E 3ac2c): MOVE.W #122,20(A6); MOVE.L 2000b4.l,22(A6) (bank window); MOVE.W #3,D0; JSR 49a84.l.
    case 0x3ad48:
        if(!ofr7_put(c,r.a[6],0x20,2,0x122) || !am_read(c,0x2000b4,4,value) || !ofr7_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[0],3);return am_call(c,0x49a84,0x3ad60);
    // LEA 3cd26.l,A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3ad60:
        r.a[1]=0x3cd26;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3ad78);
    case 0x3ad78:am_word(r.d[0],0xdb5);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3ad86);               // MOVE.W #db5,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); JSR 49a58.l.
    case 0x3ad86:if(!ofr7_put(c,r.a[6],0x68,2,0x1001) || !ofr7_put(c,r.a[6],0x1e,2,0x1001))return false;return am_call(c,0x49a58,0x3ad98);
    // ANDI.W #1f,D0; ADDI.W #50,D0; MOVE.W D0,D1; MOVE.L #60000,D0; JSR 443d2.l.
    case 0x3ad98:am_word(r.d[0],r.d[0]&0x1fU);am_word(r.d[0],r.d[0]+0x50U);am_word(r.d[1],r.d[0]);r.d[0]=0x60000;return am_call(c,0x443d2,0x3adae);
    case 0x3adae:return ofr7_btst(c,r.a[6],0x15,0,0x3adba,0x3adb8);                                       // BTST.B #0,15(A6); BEQ.W 3adba.
    case 0x3adb8:r.d[0]=0U-r.d[0];r.pc=0x3adba;return true;                                               // NEG.L D0.
    // MOVEM.L D0-D1,36(A6); JSR 49a58.l.
    case 0x3adba:if(!ofr7_put(c,r.a[6],0x36,4,r.d[0]) || !ofr7_put(c,r.a[6],0x3a,4,r.d[1]))return false;return am_call(c,0x49a58,0x3adc6);
    // ANDI.B #2,D0; MOVE.B D0,b6(A6); MOVE.L #3add4,(A6) (next PC).
    case 0x3adc6:
        am_byte(r.d[0],r.d[0]&2U);if(!ofr7_put(c,r.a[6],0xb6,1,r.d[0]) || !ofr7_put(c,r.a[6],0,4,0x3add4))return false;r.pc=0x3add4;return true;
    // ---- 3add4 (installed value): MOVE.L 36(A6),D0; ASR.L #4,D0; SUB.L D0,36(A6); MOVE.L 3a(A6),-(A7); MOVE.L 36(A6),-(A7); JSR 4be2c.l.
    case 0x3add4:
        if(!ofr7_get(c,r.a[6],0x36,4,value))return false;r.d[0]=ofr7_asr(value,4);
        if(!ofr7_get(c,r.a[6],0x36,4,value) || !ofr7_put(c,r.a[6],0x36,4,value-r.d[0]))return false;
        if(!ofr7_get(c,r.a[6],0x3a,4,value) || !am_push(c,4,value) || !ofr7_get(c,r.a[6],0x36,4,value) || !am_push(c,4,value))return false;
        return am_call(c,0x4be2c,0x3adec);
    case 0x3adec:return ofr7_btst(c,r.a[6],0x15,7,0x3ae04,0x3adf6);                                       // BTST.B #7,15(A6); BEQ.W 3ae04.
    // SUBQ.B #1,b6(A6); BPL.W 3ae04 (bit 7 of the new BYTE clear).
    case 0x3adf6:
        if(!ofr7_get(c,r.a[6],0xb6,1,value))return false;value=ofr7_b(value-1U);if(!ofr7_put(c,r.a[6],0xb6,1,value))return false;
        r.pc=(value&0x80U)==0U?0x3ae04U:0x3adfeU;return true;
    // MOVEM.L (A7)+,D2-D3; BTST.B #5,15(A6); BEQ.W 3ae68.
    case 0x3ae04:if(!am_pop(c,4,value) || !am_pop(c,4,other))return false;r.d[2]=value;r.d[3]=other;return ofr7_btst(c,r.a[6],0x15,5,0x3ae68,0x3ae12);
    case 0x3ae12:return am_call(c,0x49a58,0x3ae18);                                                       // JSR 49a58.l.
    // ANDI.B #1c,D0; SUBI.B #c,D0; LSR.W #8,D4; ADD.B D0,D4; ASR.L #1,D2; ASR.L #1,D3; LEA 4411e.l,A0; LEA 4419e.l,A1; ADD.W D4,D4; MOVE.L D2,D0;
    // MOVE.L D3,D1; ASR.L #8,D2; ASR.L #8,D3; MULS.W (A0,D4.W),D2; MULS.W (A1,D4.W),D3; SUB.L D3,D2; ASR.L #8,D2; MOVE.L D2,D3; MULS.W (A0,D4.W),D2;
    // MULS.W (A1,D4.W),D3; NEG.L D3; SUB.L D2,D0; SUB.L D3,D1; NEG.L D0; NEG.L D1; ADD.L D2,D0; ADD.L D3,D1; MOVEM.L D0-D1,36(A6).
    case 0x3ae18:
        am_byte(r.d[0],(r.d[0]&0x1cU)-0xcU);am_word(r.d[4],ofr7_w(r.d[4])>>8);am_byte(r.d[4],r.d[4]+r.d[0]);
        r.d[2]=ofr7_asr(r.d[2],1);r.d[3]=ofr7_asr(r.d[3],1);r.a[0]=0x4411e;r.a[1]=0x4419e;am_word(r.d[4],r.d[4]+r.d[4]);
        r.d[0]=r.d[2];r.d[1]=r.d[3];r.d[2]=ofr7_asr(r.d[2],8);r.d[3]=ofr7_asr(r.d[3],8);
        if(!am_read(c,am_index(r.a[0],r.d[4]),2,value))return false;r.d[2]=ofr7_muls(value,r.d[2]);
        if(!am_read(c,am_index(r.a[1],r.d[4]),2,value))return false;r.d[3]=ofr7_muls(value,r.d[3]);
        r.d[2]=ofr7_asr(r.d[2]-r.d[3],8);r.d[3]=r.d[2];
        if(!am_read(c,am_index(r.a[0],r.d[4]),2,value))return false;r.d[2]=ofr7_muls(value,r.d[2]);
        if(!am_read(c,am_index(r.a[1],r.d[4]),2,value))return false;r.d[3]=0U-ofr7_muls(value,r.d[3]);
        r.d[0]=(0U-(r.d[0]-r.d[2]))+r.d[2];r.d[1]=(0U-(r.d[1]-r.d[3]))+r.d[3];
        if(!ofr7_put(c,r.a[6],0x36,4,r.d[0]) || !ofr7_put(c,r.a[6],0x3a,4,r.d[1]))return false;r.pc=0x3ae68;return true;
    case 0x3ae68:return am_call(c,0x49fc6,0x3ae6e);                                                       // JSR 49fc6.l.
    case 0x3ae6e:r.a[0]=0x3b73e;return am_call(c,0x1ab80,0x3ae78);                                        // LEA 3b73e(PC),A0; JSR 1ab80.l.
    case 0x3ae78:return ofr7_carry(c,0x3ae82,0x3ae7c);                                                    // BCC.W 3ae82 (C of 1ab80).
    // ---- 4356e: MOVE.W -7ff2(A5),D6; MOVE.W 5492(A5),D7; SUB.W D6,D7; ADDI.W #c,D7; BCS.W 4358a (the carry out of the WORD add).
    case 0x4356e:
        if(!ofr7_get(c,r.a[5],0x800e,2,value))return false;am_word(r.d[6],value);
        if(!ofr7_get(c,r.a[5],0x5492,2,value))return false;am_word(r.d[7],value-r.d[6]);
        other=ofr7_w(r.d[7])+0xcU;am_word(r.d[7],other);r.pc=other>0xffffU?0x4358aU:0x43580U;return true;
    case 0x43580:if(!ofr7_put(c,r.a[5],0x5492,2,r.d[6]))return false;return am_call(c,0x3af8,0x4358a);    // MOVE.W D6,5492(A5); JSR 3af8.l.
    // ---- 4abc0 (damage, BRA.W from 4ae2a): CMPA.L #0,A0; BEQ.W 4ad6a.
    case 0x4abc0:r.pc=r.a[0]==0U?0x4ad6aU:0x4abcaU;return true;
    // MOVE.W (A0),D0; MOVEA.L 56(A2),A1; MOVE.W 8(A1),D1; CMPI.B #1,11(A1); BNE.W 4abe6.
    case 0x4abca:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);if(!ofr7_get(c,r.a[2],0x56,4,value))return false;r.a[1]=value;
        if(!ofr7_get(c,r.a[1],8,2,value))return false;am_word(r.d[1],value);if(!ofr7_get(c,r.a[1],0x11,1,value))return false;
        r.pc=value!=1U?0x4abe6U:0x4abdeU;return true;
    case 0x4abde:if(!ofr7_get(c,r.a[2],0x5e,1,value))return false;r.pc=value!=0U?0x4ad6aU:0x4abe6U;return true;   // TST.B 5e(A2); BNE.W.
    // MOVEQ #0,D2; MOVE.W a(A1),D3; ASR.W #1,D3; BCC.W 4abf6.
    case 0x4abe6:r.d[2]=0;if(!ofr7_get(c,r.a[1],0xa,2,value))return false;am_word(r.d[3],value);ofr7_shift_test(c,0x4abf6,0x4abf2);return true;
    case 0x4abf2:return ofr7_add_damage(c,4,0x4abf6);                                                    // ADD.W 4(A0),D2.
    case 0x4abf6:ofr7_shift_test(c,0x4ac00,0x4abfc);return true;                                          // ASR.W #1,D3; BCC.W 4ac00.
    case 0x4abfc:return ofr7_add_damage(c,6,0x4ac00);                                                    // ADD.W 6(A0),D2.
    case 0x4ac00:ofr7_shift_test(c,0x4ac0a,0x4ac06);return true;                                          // ASR.W #1,D3; BCC.W 4ac0a.
    case 0x4ac06:return ofr7_add_damage(c,8,0x4ac0a);                                                    // ADD.W 8(A0),D2.
    case 0x4ac0a:r.pc=ofr7_w(r.d[2])==0U?0x4ac1eU:0x4ac10U;return true;                                   // TST.W D2; BEQ.W 4ac1e.
    case 0x4ac10:if(!ofr7_get(c,r.a[1],0x10,1,value))return false;r.pc=value==0U?0x4ac1eU:0x4ac18U;return true;   // TST.B 10(A1); BEQ.W.
    case 0x4ac18:if(!ofr7_get(c,r.a[1],0x10,1,value))return false;r.d[2]=value;r.pc=0x4ac1e;return true;   // MOVEQ #0,D2; MOVE.B 10(A1),D2.
    // MOVEA.L c(A1),A1; CMPA.W #0,A1; BEQ.W 4ac3a.
    case 0x4ac1e:if(!ofr7_get(c,r.a[1],0xc,4,value))return false;r.a[1]=value;r.pc=r.a[1]==0U?0x4ac3aU:0x4ac2aU;return true;
    // MOVE.W D0,D3; ADD.W D3,D3; MOVE.W (A1,D3.W),D3; BEQ.W 4ad6a.
    case 0x4ac2a:
        am_word(r.d[3],r.d[0]);am_word(r.d[3],r.d[3]+r.d[3]);if(!am_read(c,am_index(r.a[1],r.d[3]),2,value))return false;am_word(r.d[3],value);
        r.pc=value==0U?0x4ad6aU:0x4ac36U;return true;
    case 0x4ac36:r.d[2]=ofr7_asr(ofr7_w(r.d[2])*ofr7_w(r.d[3]),8);r.pc=0x4ac3a;return true;              // MULU.W D3,D2; ASR.L #8,D2.
    case 0x4ac3a:if(!ofr7_get(c,r.a[5],0x5af2,2,value))return false;r.pc=ofr7_w(r.d[1])<value?0x4ac4aU:0x4ac42U;return true;   // CMP.W; BCS.W.
    // MOVE.W D1,5af2(A5); MOVE.L A2,5af4(A5).
    case 0x4ac42:if(!ofr7_put(c,r.a[5],0x5af2,2,r.d[1]) || !ofr7_put(c,r.a[5],0x5af4,4,r.a[2]))return false;r.pc=0x4ac4a;return true;
    // MOVE.B 2(A0),D3; CMP.B 5e(A2),D3; BLS.W 4acda (unsigned).
    case 0x4ac4a:
        if(!ofr7_get(c,r.a[0],2,1,value))return false;am_byte(r.d[3],value);if(!ofr7_get(c,r.a[2],0x5e,1,value))return false;
        r.pc=ofr7_b(r.d[3])<=value?0x4acdaU:0x4ac56U;return true;
    // MOVE.B D3,5e(A2); ORI.B #6,17(A2); MOVEQ #0,D4; MOVE.W 42(A2),D3; SUB.W 4a(A6),D3; SMI.B D4; ADD.W D4,D4; MOVE.W 46(A2),D3; SUB.W 4e(A6),D3;
    // SMI.B D4; ASR.W #1,D4; ANDI.W #c0,D4; MOVE.B D4,5f(A2); MOVEM.L D0-D2/D6-D7/A0,-(A7); MOVE.L 42(A6),D0; SUB.L 4a(A6),D0; SUB.L 42(A2),D0;
    // ADD.L 4a(A2),D0; the same for D1 with 46 / 4e; ADD.L D0,D0; ADD.L D1,D1; SWAP D0; SWAP D1; JSR 44602.l.
    case 0x4ac56:
        if(!ofr7_put(c,r.a[2],0x5e,1,r.d[3]) || !ofr7_get(c,r.a[2],0x17,1,value) || !ofr7_put(c,r.a[2],0x17,1,value|6U))return false;r.d[4]=0;
        if(!ofr7_get(c,r.a[2],0x42,2,value) || !ofr7_get(c,r.a[6],0x4a,2,other))return false;am_word(r.d[3],value-other);
        am_byte(r.d[4],(r.d[3]&0x8000U)!=0U?0xffU:0U);am_word(r.d[4],r.d[4]+r.d[4]);
        if(!ofr7_get(c,r.a[2],0x46,2,value) || !ofr7_get(c,r.a[6],0x4e,2,other))return false;am_word(r.d[3],value-other);
        am_byte(r.d[4],(r.d[3]&0x8000U)!=0U?0xffU:0U);am_word(r.d[4],ofr7_asr_word1(r.d[4]));am_word(r.d[4],r.d[4]&0xc0U);
        if(!ofr7_put(c,r.a[2],0x5f,1,r.d[4]))return false;
        if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.d[7]) || !am_push(c,4,r.d[6]) || !am_push(c,4,r.d[2]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))
            return false;
        if(!ofr7_get(c,r.a[6],0x42,4,r.d[0]) || !ofr7_get(c,r.a[6],0x4a,4,value))return false;r.d[0]-=value;
        if(!ofr7_get(c,r.a[2],0x42,4,value))return false;r.d[0]-=value;if(!ofr7_get(c,r.a[2],0x4a,4,value))return false;r.d[0]+=value;
        if(!ofr7_get(c,r.a[6],0x46,4,r.d[1]) || !ofr7_get(c,r.a[6],0x4e,4,value))return false;r.d[1]-=value;
        if(!ofr7_get(c,r.a[2],0x46,4,value))return false;r.d[1]-=value;if(!ofr7_get(c,r.a[2],0x4e,4,value))return false;r.d[1]+=value;
        r.d[0]+=r.d[0];r.d[1]+=r.d[1];am_swap(r.d[0]);am_swap(r.d[1]);return am_call(c,0x44602,0x4acb4);
    // LSR.L #4,D0; ANDI.W #f,D0; OR.B D0,5f(A2); MOVE.B 60(A6),D0; MOVE.B 60(A2),D1; ANDI.B #3,D0; LSL.W #2,D0; ANDI.B #f3,D1; OR.B D1,D0;
    // MOVE.B D0,60(A2); MOVEM.L (A7)+,D0-D2/D6-D7/A0.
    case 0x4acb4:
        r.d[0]=r.d[0]>>4;am_word(r.d[0],r.d[0]&0xfU);if(!ofr7_get(c,r.a[2],0x5f,1,value) || !ofr7_put(c,r.a[2],0x5f,1,value|ofr7_b(r.d[0])))return false;
        if(!ofr7_get(c,r.a[6],0x60,1,value))return false;am_byte(r.d[0],value);if(!ofr7_get(c,r.a[2],0x60,1,value))return false;am_byte(r.d[1],value);
        am_byte(r.d[0],r.d[0]&3U);am_word(r.d[0],ofr7_w(r.d[0])<<2);am_byte(r.d[1],r.d[1]&0xf3U);am_byte(r.d[0],r.d[0]|ofr7_b(r.d[1]));
        if(!ofr7_put(c,r.a[2],0x60,1,r.d[0]))return false;
        if(!am_pop(c,4,r.d[0]) || !am_pop(c,4,r.d[1]) || !am_pop(c,4,r.d[2]) || !am_pop(c,4,r.d[6]) || !am_pop(c,4,r.d[7]) || !am_pop(c,4,r.a[0]))
            return false;
        r.pc=0x4acda;return true;
    case 0x4acda:return ofr7_btst(c,r.a[2],0x61,7,0x4ace4,0x4ad6a);                                       // BTST.B #7,61(A2); BNE.W 4ad6a.
    case 0x4ace4:return ofr7_btst(c,r.a[2],0x61,6,0x4acee,0x4ad6a);                                       // BTST.B #6,61(A2); BNE.W 4ad6a.
    // MOVE.W 54(A2),D3; CMP.W 5b7c(A5),D3; BCS.W 4ad02.
    case 0x4acee:
        if(!ofr7_get(c,r.a[2],0x54,2,value))return false;am_word(r.d[3],value);if(!ofr7_get(c,r.a[5],0x5b7c,2,value))return false;
        r.pc=ofr7_w(r.d[3])<value?0x4ad02U:0x4acfaU;return true;
    // MOVE.W D3,5b7c(A5); MOVE.L A2,5b78(A5).
    case 0x4acfa:if(!ofr7_put(c,r.a[5],0x5b7c,2,r.d[3]) || !ofr7_put(c,r.a[5],0x5b78,4,r.a[2]))return false;r.pc=0x4ad02;return true;
    case 0x4ad02:if(!ofr7_get(c,r.a[5],0x5b82,2,value))return false;r.pc=ofr7_w(r.d[3])>value?0x4ad12U:0x4ad0aU;return true;   // CMP.W; BHI.W.
    // MOVE.W D3,5b82(A5); MOVE.L A2,5b7e(A5).
    case 0x4ad0a:if(!ofr7_put(c,r.a[5],0x5b82,2,r.d[3]) || !ofr7_put(c,r.a[5],0x5b7e,4,r.a[2]))return false;r.pc=0x4ad12;return true;
    case 0x4ad12:r.pc=ofr7_w(r.d[2])==0U?0x4ad6aU:0x4ad18U;return true;                                   // TST.W D2; BEQ.W 4ad6a.
    // MOVE.W 54(A2),D3; SUB.W D2,D3; BHI.W 4ad38 (unsigned WORD 54 > D2.W).
    case 0x4ad18:
        if(!ofr7_get(c,r.a[2],0x54,2,value))return false;am_word(r.d[3],value-r.d[2]);r.pc=value>ofr7_w(r.d[2])?0x4ad38U:0x4ad22U;return true;
    // BSET.B #7,61(A2); BTST.B #0,3(A0); BNE.W 4ad36.
    case 0x4ad22:if(!ofr7_bit(c,r.a[2],0x61,7,true))return false;return ofr7_btst(c,r.a[0],3,0,0x4ad32,0x4ad36);
    case 0x4ad32:return am_call(c,0x4bb52,0x4ad36);                                                       // BSR.W 4bb52.
    case 0x4ad36:r.d[3]=0;r.pc=0x4ad38;return true;                                                       // MOVEQ #0,D3.
    // MOVE.W D3,54(A2); TST.B D1; BEQ.W 4ad6a.
    case 0x4ad38:if(!ofr7_put(c,r.a[2],0x54,2,r.d[3]))return false;r.pc=ofr7_b(r.d[1])==0U?0x4ad6aU:0x4ad42U;return true;
    case 0x4ad42:if(!ofr7_get(c,r.a[2],0x60,1,value))return false;r.pc=(value&0x80U)!=0U?0x4ad6aU:0x4ad4aU;return true;   // TST.B; BMI.W.
    // MOVEM.L D1-D7/A0-A4,-(A7); LEA 48a3a.l,A0; MOVE.W D0,D3; ADD.W D3,D3; ADDA.W D3,A0; MOVE.W D0,D1; MOVE.B 60(A6),D0; JSR e625e.l.
    case 0x4ad4a:
        for(int k=4;k>=0;--k)if(!am_push(c,4,r.a[k]))return false;
        for(int k=7;k>=1;--k)if(!am_push(c,4,r.d[k]))return false;
        r.a[0]=0x48a3a;am_word(r.d[3],r.d[0]);am_word(r.d[3],r.d[3]+r.d[3]);r.a[0]=r.a[0]+am_extend_word(r.d[3]);am_word(r.d[1],r.d[0]);
        if(!ofr7_get(c,r.a[6],0x60,1,value))return false;am_byte(r.d[0],value);return am_call(c,0xe625e,0x4ad66);
    // MOVEM.L (A7)+,D1-D7/A0-A4.
    case 0x4ad66:
        for(int k=1;k<=7;++k)if(!am_pop(c,4,r.d[k]))return false;
        for(int k=0;k<=4;++k)if(!am_pop(c,4,r.a[k]))return false;
        r.pc=0x4ad6a;return true;
    // ---- 4ad6c (hit test, BSR from N08): LEA 5a(A2),A1; TST.B 5744(A5); BMI.W 4ad7c / LEA 1(A1),A1.
    case 0x4ad6c:r.a[1]=r.a[2]+0x5aU;if(!ofr7_get(c,r.a[5],0x5744,1,value))return false;r.pc=(value&0x80U)!=0U?0x4ad7cU:0x4ad78U;return true;
    case 0x4ad78:r.a[1]=r.a[1]+1U;r.pc=0x4ad7c;return true;
    case 0x4ad7c:if(!am_read(c,r.a[1],1,value))return false;r.pc=value!=ofr7_b(r.d[4])?0x4ae48U:0x4ad82U;return true;   // CMP.B (A1),D4; BNE.W.
    // MOVEA.L 56(A2),A1; CMPA.W #0,A1; BEQ.W 4ae48.
    case 0x4ad82:if(!ofr7_get(c,r.a[2],0x56,4,value))return false;r.a[1]=value;r.pc=r.a[1]==0U?0x4ae48U:0x4ad8eU;return true;
    // LEA 12(A0),A3; MOVE.L (A3)+,D0.
    case 0x4ad8e:r.a[3]=r.a[0]+0x12U;if(!am_read(c,r.a[3],4,value))return false;r.d[0]=value;r.a[3]=r.a[3]+4U;r.pc=0x4ad94;return true;
    // MOVE.L (A3)+,D1; BTST.B #1,15(A6); BEQ.W 4ada4.
    case 0x4ad94:if(!am_read(c,r.a[3],4,value))return false;r.d[1]=value;r.a[3]=r.a[3]+4U;return ofr7_btst(c,r.a[6],0x15,1,0x4ada4,0x4ada0);
    case 0x4ada0:ofr7_negadd(r.d[0],r.d[1]);r.pc=0x4ada4;return true;                                     // ADD.W D1,D0; NEG.W D0.
    // ADD.W 46(A6),D0; SWAP D0; SWAP D1; BTST.B #0,15(A6); BEQ.W 4adba.
    case 0x4ada4:
        if(!ofr7_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],r.d[0]+value);am_swap(r.d[0]);am_swap(r.d[1]);
        return ofr7_btst(c,r.a[6],0x15,0,0x4adba,0x4adb6);
    case 0x4adb6:ofr7_negadd(r.d[0],r.d[1]);r.pc=0x4adba;return true;                                     // ADD.W D1,D0; NEG.W D0.
    // ADD.W 42(A6),D0; LEA 12(A1),A1; MOVE.L (A1)+,D2.
    case 0x4adba:
        if(!ofr7_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],r.d[0]+value);r.a[1]=r.a[1]+0x12U;
        if(!am_read(c,r.a[1],4,value))return false;r.d[2]=value;r.a[1]=r.a[1]+4U;r.pc=0x4adc4;return true;
    // MOVE.L (A1)+,D3; SWAP D2; SWAP D3; BTST.B #0,15(A2); BEQ.W 4add8.
    case 0x4adc4:
        if(!am_read(c,r.a[1],4,value))return false;r.d[3]=value;r.a[1]=r.a[1]+4U;am_swap(r.d[2]);am_swap(r.d[3]);
        return ofr7_btst(c,r.a[2],0x15,0,0x4add8,0x4add4);
    case 0x4add4:ofr7_negadd(r.d[2],r.d[3]);r.pc=0x4add8;return true;                                     // ADD.W D3,D2; NEG.W D2.
    case 0x4add8:return ofr7_span(c,0x4a,0x4ae32,0x4ade8);
    // SWAP D0; SWAP D1; SWAP D2; SWAP D3; BTST.B #1,15(A2); BEQ.W 4adfe.
    case 0x4ade8:am_swap(r.d[0]);am_swap(r.d[1]);am_swap(r.d[2]);am_swap(r.d[3]);return ofr7_btst(c,r.a[2],0x15,1,0x4adfe,0x4adfa);
    case 0x4adfa:ofr7_negadd(r.d[2],r.d[3]);r.pc=0x4adfe;return true;                                     // ADD.W D3,D2; NEG.W D2.
    case 0x4adfe:return ofr7_span(c,0x4e,0x4ae2e,0x4ae0e);
    // ASR.W #1,D2; ADD.W D0,D2; LSR.W #1,D2; MOVE.B D2,5d(A2); SWAP D0..D3; ASR.W #1,D2; ADD.W D0,D2; LSR.W #1,D2; MOVE.B D2,5c(A2); BRA.W 4abc0.
    case 0x4ae0e:
        ofr7_mid(r.d[2],r.d[0]);if(!ofr7_put(c,r.a[2],0x5d,1,r.d[2]))return false;am_swap(r.d[0]);am_swap(r.d[1]);am_swap(r.d[2]);am_swap(r.d[3]);
        ofr7_mid(r.d[2],r.d[0]);if(!ofr7_put(c,r.a[2],0x5c,1,r.d[2]))return false;r.pc=0x4abc0;return true;
    case 0x4ae2e:am_swap(r.d[0]);am_swap(r.d[1]);r.pc=0x4ae32;return true;                                // SWAP D0; SWAP D1.
    // MOVE.L (A1)+,D2; CMPI.W #8000,D2; BNE.B 4adc4.
    case 0x4ae32:if(!am_read(c,r.a[1],4,value))return false;r.d[2]=value;r.a[1]=r.a[1]+4U;r.pc=ofr7_w(r.d[2])!=0x8000U?0x4adc4U:0x4ae3aU;return true;
    // MOVEA.L 56(A2),A1; MOVE.L (A3)+,D0; CMPI.W #8000,D0; BNE.W 4ad94.
    case 0x4ae3a:
        if(!ofr7_get(c,r.a[2],0x56,4,value))return false;r.a[1]=value;if(!am_read(c,r.a[3],4,value))return false;r.d[0]=value;r.a[3]=r.a[3]+4U;
        r.pc=ofr7_w(r.d[0])!=0x8000U?0x4ad94U:0x4ae48U;return true;
    // ---- 4c0f0 (ground search): SUBQ.W #6,A7; MOVE.W #4,4(A7); SWAP D0; CLR.W D0; MOVE.L D0,(A7); JSR 4bce0(PC).
    case 0x4c0f0:
        r.a[7]=r.a[7]-6U;if(!am_write(c,r.a[7]+4U,2,4))return false;am_swap(r.d[0]);am_word(r.d[0],0);if(!am_write(c,r.a[7],4,r.d[0]))return false;
        return am_call(c,0x4bce0,0x4c102);
    case 0x4c102:return am_call(c,0x43e34,0x4c108);                                                       // JSR 43e34.l.
    // CMPI.W #20,42(A6); BMI.W 4c156 (bit 15 of the WORD difference).
    case 0x4c108:if(!ofr7_get(c,r.a[6],0x42,2,value))return false;r.pc=((value-0x20U)&0x8000U)!=0U?0x4c156U:0x4c112U;return true;
    case 0x4c112:return ofr7_probe(c,0x4c128);
    case 0x4c128:return ofr7_carry(c,0x4c14a,0x4c12c);                                                    // BCC.W 4c14a (C of 46d72).
    case 0x4c12c:return ofr7_height(c,0x4c146,0x4c132);
    case 0x4c132:return ofr7_count(c,0x4c146,0x4c13a);
    case 0x4c13a:return ofr7_land(c,0xa);
    case 0x4c146:r.pc=0x4c150;return true;                                                                // BRA.W 4c150.
    case 0x4c14a:return ofr7_reset(c,0x4c150);
    case 0x4c150:return ofr7_step_x(c,0xfffbU,0x4c108);                                                   // SUBQ.W #5,42(A6); BRA.B 4c108.
    case 0x4c156:return am_call(c,0x43e34,0x4c15c);                                                       // JSR 43e34.l.
    case 0x4c15c:return ofr7_reset(c,0x4c162);
    // CMPI.W #120,42(A6); BPL.W 4c1b0.
    case 0x4c162:if(!ofr7_get(c,r.a[6],0x42,2,value))return false;r.pc=((value-0x120U)&0x8000U)==0U?0x4c1b0U:0x4c16cU;return true;
    case 0x4c16c:return ofr7_probe(c,0x4c182);
    case 0x4c182:return ofr7_carry(c,0x4c1a4,0x4c186);                                                    // BCC.W 4c1a4 (C of 46d72).
    case 0x4c186:return ofr7_height(c,0x4c1a0,0x4c18c);
    case 0x4c18c:return ofr7_count(c,0x4c1a0,0x4c194);
    case 0x4c194:return ofr7_land(c,0xfff6U);
    case 0x4c1a0:r.pc=0x4c1aa;return true;                                                                // BRA.W 4c1aa.
    case 0x4c1a4:return ofr7_reset(c,0x4c1aa);
    case 0x4c1aa:return ofr7_step_x(c,5,0x4c162);                                                         // ADDQ.W #5,42(A6); BRA.B 4c162.
    case 0x4c1b0:return am_call(c,0x43e34,0x4c1b6);                                                       // JSR 43e34.l.
    case 0x4c1b6:return ofr7_frame_return(c,AnimationCarryClear);
    // MOVEA.L 3e(A6),A0; SUB.W (A0),D0; SWAP D0; CLR.W D0; MOVE.L D0,2e(A6); JSR 43e34.l.
    case 0x4c1be:
        if(!ofr7_get(c,r.a[6],0x3e,4,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],r.d[0]-value);
        am_swap(r.d[0]);am_word(r.d[0],0);if(!ofr7_put(c,r.a[6],0x2e,4,r.d[0]))return false;return am_call(c,0x43e34,0x4c1d2);
    case 0x4c1d2:return am_call(c,0x4c0b0,0x4c1d6);                                                       // JSR 4c0b0(PC).
    case 0x4c1d6:return ofr7_frame_return(c,AnimationCarrySet);
    // ---- cc5e8: MOVE.W 42(A6),D0; ADDI.W #20,D0; CMPI.W #180,D0; BCC.B cc5e2 / CMPI.W #e0,46(A6); BCS.B cc5e2 / RTS.
    case 0xcc5e8:if(!ofr7_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value+0x20U);r.pc=ofr7_w(r.d[0])>=0x180U?0xcc5e2U:0xcc5f6U;return true;
    case 0xcc5f6:if(!ofr7_get(c,r.a[6],0x46,2,value))return false;r.pc=value<0xe0U?0xcc5e2U:0xcc5feU;return true;
    // ---- cc958: BTST.B #7,15(A6); BEQ.W cc9bc.
    case 0xcc958:return ofr7_btst(c,r.a[6],0x15,7,0xcc9bc,0xcc962);
    // MOVE.L 7e(A6),D0; SUB.L 64(A6),D0; ASR.L #2,D0; ADD.L D0,64(A6); JSR 4bfa4.l.
    case 0xcc962:
        if(!ofr7_get(c,r.a[6],0x7e,4,r.d[0]) || !ofr7_get(c,r.a[6],0x64,4,value))return false;r.d[0]=ofr7_asr(r.d[0]-value,2);
        if(!ofr7_get(c,r.a[6],0x64,4,value) || !ofr7_put(c,r.a[6],0x64,4,value+r.d[0]))return false;return am_call(c,0x4bfa4,0xcc976);
    // MOVE.W #20 / #100,D5; AND.W D6,D5; BEQ.W / MOVE.B #ff,7a(A6).
    case 0xcc976:am_word(r.d[5],0x20U&r.d[6]);r.pc=ofr7_w(r.d[5])==0U?0xcc986U:0xcc980U;return true;
    case 0xcc980:if(!ofr7_put(c,r.a[6],0x7a,1,0xff))return false;r.pc=0xcc986;return true;
    case 0xcc986:am_word(r.d[5],0x100U&r.d[6]);r.pc=ofr7_w(r.d[5])==0U?0xcc996U:0xcc990U;return true;
    case 0xcc990:if(!ofr7_put(c,r.a[6],0x7a,1,0xff))return false;r.pc=0xcc996;return true;
    case 0xcc996:return ofr7_btst(c,r.a[6],0x15,4,0xcc9b8,0xcc9a0);                                       // BTST.B #4,15(A6); BEQ.W cc9b8.
    // MOVE.B 6e(A6),D0; CMPI.B #5,D0; BNE.W cc9b8.
    case 0xcc9a0:if(!ofr7_get(c,r.a[6],0x6e,1,value))return false;am_byte(r.d[0],value);r.pc=value!=5U?0xcc9b8U:0xcc9acU;return true;
    // BCLR.B #7,15(A6); MOVE.B #ff,7c(A6).
    case 0xcc9ac:if(!ofr7_bit(c,r.a[6],0x15,7,false) || !ofr7_put(c,r.a[6],0x7c,1,0xff))return false;r.pc=0xcc9b8;return true;
    case 0xcc9b8:case 0xcca18:r.pc=0xcca38;return true;                                                   // BRA.W cca38.
    // MOVE.L #fff40000,D0; SUB.L 3a(A6),D0; ASR.L #5,D0; ADD.L D0,3a(A6); MOVE.L 7e(A6),D0; SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6);
    // MOVE.L 36(A6),64(A6); TST.B 7c(A6); BNE.W cca1c.
    case 0xcc9bc:
        if(!ofr7_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ofr7_asr(0xfff40000U-value,5);
        if(!ofr7_get(c,r.a[6],0x3a,4,value) || !ofr7_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;
        if(!ofr7_get(c,r.a[6],0x7e,4,r.d[0]) || !ofr7_get(c,r.a[6],0x36,4,value))return false;r.d[0]=ofr7_asr(r.d[0]-value,5);
        if(!ofr7_get(c,r.a[6],0x36,4,value) || !ofr7_put(c,r.a[6],0x36,4,value+r.d[0]))return false;
        if(!ofr7_get(c,r.a[6],0x36,4,value) || !ofr7_put(c,r.a[6],0x64,4,value) || !ofr7_get(c,r.a[6],0x7c,1,value))return false;
        r.pc=value!=0U?0xcca1cU:0xcc9e8U;return true;
    case 0xcc9e8:return ofr7_btst(c,r.a[6],0x15,4,0xcca04,0xcc9f2);                                       // BTST.B #4,15(A6); BEQ.W cca04.
    case 0xcc9f2:if(!ofr7_get(c,r.a[6],0x7a,1,value))return false;r.pc=value==0U?0xcca04U:0xcc9faU;return true;   // TST.B 7a(A6); BEQ.W.
    case 0xcc9fa:return am_call(c,0x4be50,0xcca00);                                                       // JSR 4be50.l.
    case 0xcca00:r.pc=0xcca0a;return true;                                                                // BRA.W cca0a.
    case 0xcca04:return am_call(c,0x4be34,0xcca0a);                                                       // JSR 4be34.l.
    case 0xcca0a:r.pc=(r.d[6]&0x20U)==0U?0xcca18U:0xcca12U;return true;                                   // BTST.B #5,D6; BEQ.W cca18.
    case 0xcca12:if(!ofr7_bit(c,r.a[6],0x15,4,true))return false;r.pc=0xcca18;return true;               // BSET.B #4,15(A6).
    // LEA 538e(A5),A1; MOVEM.L 2e(A6),D0-D3/A0; JSR 43eb8.l.
    case 0xcca1c:
        r.a[1]=am_index(r.a[5],0x538e);
        if(!ofr7_get(c,r.a[6],0x2e,4,r.d[0]) || !ofr7_get(c,r.a[6],0x32,4,r.d[1]) || !ofr7_get(c,r.a[6],0x36,4,r.d[2]) || !ofr7_get(c,r.a[6],0x3a,4,r.d[3]) ||
           !ofr7_get(c,r.a[6],0x3e,4,value))return false;
        r.a[0]=value;return am_call(c,0x43eb8,0xcca2c);
    // MOVEM.L D0-D3/A1,2e(A6); JSR 43ea4.l.
    case 0xcca2c:
        if(!ofr7_put(c,r.a[6],0x2e,4,r.d[0]) || !ofr7_put(c,r.a[6],0x32,4,r.d[1]) || !ofr7_put(c,r.a[6],0x36,4,r.d[2]) || !ofr7_put(c,r.a[6],0x3a,4,r.d[3]) ||
           !ofr7_put(c,r.a[6],0x3e,4,r.a[1]))return false;
        return am_call(c,0x43ea4,0xcca38);
    // BTST.B #7,15(A6); SNE.B 78(A6); RTS.
    case 0xcca38:
        if(!ofr7_get(c,r.a[6],0x15,1,value) || !ofr7_put(c,r.a[6],0x78,1,(value&0x80U)!=0U?0xffU:0U))return false;return am_return(c);
    // ---- cdd2e (installed / BRA value): BSR.W cc5e8 / BSR.W cc958 / JSR 49fc6.l / BCC.W cdd46.
    case 0xcdd2e:return am_call(c,0xcc5e8,0xcdd32);
    case 0xcdd32:return am_call(c,0xcc958,0xcdd36);
    case 0xcdd36:return am_call(c,0x49fc6,0xcdd3c);
    case 0xcdd3c:return ofr7_carry(c,0xcdd46,0xcdd40);                                                    // BCC.W cdd46 (C of 49fc6).
    case 0xcdd46:return ofr7_btst(c,r.a[6],0x61,3,0xcdd50,0xcdd70);                                       // BTST.B #3,61(A6); BNE.W cdd70.
    // MOVE.B 79(A6),D0; BEQ.W cdd6c / SUBQ.B #1,D0; BNE.W cdd68 / BSET.B #3,61(A6); MOVE.B #1e,D0 / MOVE.B D0,79(A6).
    case 0xcdd50:if(!ofr7_get(c,r.a[6],0x79,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0xcdd6cU:0xcdd58U;return true;
    case 0xcdd58:am_byte(r.d[0],r.d[0]-1U);r.pc=ofr7_b(r.d[0])!=0U?0xcdd68U:0xcdd5eU;return true;
    case 0xcdd5e:if(!ofr7_bit(c,r.a[6],0x61,3,true))return false;am_byte(r.d[0],0x1e);r.pc=0xcdd68;return true;
    case 0xcdd68:if(!ofr7_put(c,r.a[6],0x79,1,r.d[0]))return false;r.pc=0xcdd6c;return true;
    case 0xcdd6c:r.pc=0xcdd84;return true;                                                                // BRA.W cdd84.
    case 0xcdd70:if(!ofr7_get(c,r.a[6],0x79,1,value))return false;am_byte(r.d[0],value);r.pc=value!=0U?0xcdd7eU:0xcdd78U;return true;
    case 0xcdd7e:am_byte(r.d[0],r.d[0]-1U);if(!ofr7_put(c,r.a[6],0x79,1,r.d[0]))return false;r.pc=0xcdd84;return true;   // SUBQ.B; MOVE.B.
    // ---- cde42 (28ae child of cddee): LEA 26(A6),A0; MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6) (bank window); MOVE.W #100,D0; LEA 26(A6),A0;
    // MOVEA.L 22(A6),A1; MOVEA.L 40(A1),A1; JSR 49f8c.l.
    case 0xcde42:
        r.a[0]=r.a[6]+0x26U;if(!ofr7_put(c,r.a[6],0x20,2,0xe2) || !am_read(c,0x200094,4,value) || !ofr7_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[0],0x100);r.a[0]=r.a[6]+0x26U;if(!ofr7_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
        if(!ofr7_get(c,r.a[1],0x40,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,0xcde6a);
    case 0xcde6a:r.pc=0xcde96;return true;                                                                // BRA.W cde96.
    case 0xcde96:return am_call(c,0x497a6,0xcde9c);                                                       // JSR 497a6.l.
    case 0xcde9c:return ofr7_carry(c,0xcdea0,0xcdeb2);                                                    // BCS.W cdeb2 (C of 497a6).
    case 0xcdea0:am_word(r.d[0],0x37a);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xcdeae);               // MOVE.W #37a,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0xcdeae:r.pc=0xcdec0;return true;                                                                // BRA.W cdec0.
    case 0xcdeb2:am_word(r.d[0],0x3ba);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xcdec0);               // MOVE.W #3ba,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVE.W #e0ed,68(A6); MOVE.W #e0ed,1e(A6); MOVE.L #cded2,(A6) (next PC).
    case 0xcdec0:
        if(!ofr7_put(c,r.a[6],0x68,2,0xe0ed) || !ofr7_put(c,r.a[6],0x1e,2,0xe0ed) || !ofr7_put(c,r.a[6],0,4,0xcded2))return false;r.pc=0xcded2;return true;
    case 0xcded2:return am_call(c,0x43e34,0xcded8);                                                       // JSR 43e34.l.
    case 0xcded8:return am_call(c,0x49fc6,0xcdede);                                                       // JSR 49fc6.l.
    case 0xcdede:return ofr7_carry(c,0xcdee8,0xcdee2);                                                    // BCC.W cdee8 (C of 49fc6).
    // ---- d2776 d2782 d278e d279a (callbacks of the LONG table bbf1a..): MOVE.W #167,D0; LEA record(PC),A0; BRA.W d2f90.
    case 0xd2776:return ofr7_stub(c,0xd2652);
    case 0xd2782:return ofr7_stub(c,0xd265a);
    case 0xd278e:return ofr7_stub(c,0xd2662);
    case 0xd279a:return ofr7_stub(c,0xd266a);
    // MOVE.L A0,-(A7); MOVEQ #0,D1; JSR 8ebe.l.
    case 0xd2f90:if(!am_push(c,4,r.a[0]))return false;r.d[1]=0;return am_call(c,0x8ebe,0xd2f9a);
    // MOVEA.L (A7)+,A0; MOVE.L (A0)+,92(A6); MOVE.L (A0),D0; LEA 26(A6),A0; MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); LEA 26(A6),A0; MOVE.W D0,D1;
    // ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 200094.l,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xd2f9a:
        if(!am_pop(c,4,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],4,value))return false;r.a[0]=r.a[0]+4U;
        if(!ofr7_put(c,r.a[6],0x92,4,value) || !am_read(c,r.a[0],4,r.d[0]))return false;r.a[0]=r.a[6]+0x26U;
        if(!ofr7_put(c,r.a[6],0x20,2,0xe2) || !am_read(c,0x200094,4,value) || !ofr7_put(c,r.a[6],0x22,4,value))return false;r.a[0]=r.a[6]+0x26U;
        am_word(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]+r.d[1]);am_word(r.d[1],r.d[1]+r.d[1]);
        if(!am_read(c,0x200094,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;
        am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xd2fd2);
    case 0xd2fd2:return am_call(c,0xd3c2a,0xd2fd6);                                                       // JSR d3c2a(PC).
    // MOVE.L #80000,3a(A6); MOVE.L #ffffbbbc,8e(A6); MOVE.L #20000,36(A6); JSR 49a58.l.
    case 0xd2fd6:
        if(!ofr7_put(c,r.a[6],0x3a,4,0x80000) || !ofr7_put(c,r.a[6],0x8e,4,0xffffbbbcU) || !ofr7_put(c,r.a[6],0x36,4,0x20000))return false;
        return am_call(c,0x49a58,0xd2ff4);
    // MOVE.L D0,D1; SWAP D0; LSR.L #1,D0; ANDI.L #38000,D0; BTST.B #0,D1; BNE.W d300a.
    case 0xd2ff4:r.d[1]=r.d[0];am_swap(r.d[0]);r.d[0]=(r.d[0]>>1)&0x38000U;r.pc=(r.d[1]&1U)!=0U?0xd300aU:0xd3008U;return true;
    case 0xd3008:r.d[0]=0U-r.d[0];r.pc=0xd300a;return true;                                               // NEG.L D0.
    case 0xd300a:if(!ofr7_put(c,r.a[6],0x36,4,r.d[0]))return false;return am_call(c,0x49a58,0xd3014);    // MOVE.L D0,36(A6); JSR 49a58.l.
    // SWAP D0; LSR.L #1,D0; ANDI.L #78000,D0; SUB.L D0,3a(A6); CMPI.W #fb,3a(A6); BLE.W d3032 (signed WORD).
    case 0xd3014:
        am_swap(r.d[0]);r.d[0]=(r.d[0]>>1)&0x78000U;if(!ofr7_get(c,r.a[6],0x3a,4,value) || !ofr7_put(c,r.a[6],0x3a,4,value-r.d[0]))return false;
        if(!ofr7_get(c,r.a[6],0x3a,2,value))return false;r.pc=ofr7_sw(value)<=0xfb?0xd3032U:0xd302cU;return true;
    case 0xd302c:if(!ofr7_put(c,r.a[6],0x3a,2,0xfb))return false;r.pc=0xd3032;return true;               // MOVE.W #fb,3a(A6).
    // CMPI.L #fffff000,8e(A6); BLE.W d3046 (signed LONG).
    case 0xd3032:if(!ofr7_get(c,r.a[6],0x8e,4,value))return false;r.pc=ofr7_le_long(value,0xfffff000U)?0xd3046U:0xd303eU;return true;
    case 0xd303e:if(!ofr7_put(c,r.a[6],0x8e,4,0xfffff000U))return false;r.pc=0xd3046;return true;        // MOVE.L #fffff000,8e(A6).
    // BSET.B #3,15(A6); CLR.L 56(A6); MOVE.B #ff,12(A6); MOVE.B #ff,13(A6); MOVE.L #d3062,(A6) (next PC).
    case 0xd3046:
        if(!ofr7_bit(c,r.a[6],0x15,3,true) || !ofr7_put(c,r.a[6],0x56,4,0) || !ofr7_put(c,r.a[6],0x12,1,0xff) || !ofr7_put(c,r.a[6],0x13,1,0xff) ||
           !ofr7_put(c,r.a[6],0,4,0xd3062))return false;
        r.pc=0xd3062;return true;
    case 0xd3062:return am_call(c,0x4be34,0xd3068);                                                       // JSR 4be34.l.
    case 0xd3068:return ofr7_btst(c,r.a[6],0x15,7,0xd3072,0xd3094);                                       // BTST.B #7,15(A6); BNE.W d3094.
    // MOVE.L 8e(A6),D0; ADD.L D0,3a(A6); JSR 49fc6.l.
    case 0xd3072:
        if(!ofr7_get(c,r.a[6],0x8e,4,r.d[0]) || !ofr7_get(c,r.a[6],0x3a,4,value) || !ofr7_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;
        return am_call(c,0x49fc6,0xd3080);
    case 0xd3080:return ofr7_carry(c,0xd3084,0xd3094);                                                    // BCS.W d3094 (C of 49fc6).
    case 0xd3084:if(!ofr7_get(c,r.a[6],0x92,4,value))return false;r.a[0]=value;return am_call(c,0x1ab80,0xd308e);   // MOVEA.L 92(A6),A0; JSR 1ab80.l.
    case 0xd308e:return ofr7_carry(c,0xd3092,0xd3094);                                                    // BCS.W d3094 (C of 1ab80).
    // ---- e8b7e / e8b80 (the tail of the C helper e8b5a; e8b80 is the target of its BEQ.W e8b7a): SUB.W (A1),D2 / BTST.B #0,4(A4); BEQ.W e8b92.
    case 0xe8b7e:if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[2],r.d[2]-value);r.pc=0xe8b80;return true;
    case 0xe8b80:return ofr7_btst(c,r.a[4],4,0,0xe8b92,0xe8b8a);
    // ADDI.W #100,D3; SUB.W 4(A1),D3.
    case 0xe8b8a:am_word(r.d[3],r.d[3]+0x100U);if(!ofr7_get(c,r.a[1],4,2,value))return false;am_word(r.d[3],r.d[3]-value);r.pc=0xe8b92;return true;
    // MOVE.W D2,D0; MOVE.W D3,D1; LEA 2e(A6),A0; JSR 43e08.l.
    case 0xe8b92:am_word(r.d[0],r.d[2]);am_word(r.d[1],r.d[3]);r.a[0]=r.a[6]+0x2eU;return am_call(c,0x43e08,0xe8ba0);
    // MOVEA.L 5e26(A5),A4; MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B 5(A4),D0; MOVE.B 6(A4),D1; EXT.W D0; EXT.W D1; SWAP D0; SWAP D1; TST.W (A7)+; BEQ.W e8bc2.
    case 0xe8ba0:
        if(!ofr7_get(c,r.a[5],0x5e26,4,value))return false;r.a[4]=value;
        if(!ofr7_get(c,r.a[4],5,1,value))return false;r.d[0]=(value&0x80U)!=0U?(value|0xff00U):value;
        if(!ofr7_get(c,r.a[4],6,1,value))return false;r.d[1]=(value&0x80U)!=0U?(value|0xff00U):value;
        am_swap(r.d[0]);am_swap(r.d[1]);if(!am_pop(c,2,value))return false;r.pc=ofr7_w(value)==0U?0xe8bc2U:0xe8bbeU;return true;
    case 0xe8bbe:r.d[0]=0U-r.d[0];r.d[1]=0U-r.d[1];r.pc=0xe8bc2;return true;                              // NEG.L D0; NEG.L D1.
    // MOVE.L D0,36(A6); MOVE.L D1,3a(A6); JSR 4be34.l.
    case 0xe8bc2:if(!ofr7_put(c,r.a[6],0x36,4,r.d[0]) || !ofr7_put(c,r.a[6],0x3a,4,r.d[1]))return false;return am_call(c,0x4be34,0xe8bd0);
    case 0xe8bd0:return am_call(c,0x43e38,0xe8bd6);                                                       // JSR 43e38.l.
    // MOVEA.L 5e26(A5),A4; MOVEQ #0,D7; MOVEQ #0,D6; MOVE.B 7(A4),D7; CMPI.B #b,D7; BNE.W e8c04.
    case 0xe8bd6:
        if(!ofr7_get(c,r.a[5],0x5e26,4,value))return false;r.a[4]=value;r.d[6]=0;if(!ofr7_get(c,r.a[4],7,1,value))return false;r.d[7]=value;
        r.pc=value!=0xbU?0xe8c04U:0xe8beaU;return true;
    case 0xe8bea:return am_call(c,0x1a988,0xe8bf0);                                                       // JSR 1a988.l.
    // SUB.W 46(A6),D0; NEG.W D0; BMI.W e8c00.
    case 0xe8bf0:if(!ofr7_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],0U-(r.d[0]-value));r.pc=(r.d[0]&0x8000U)!=0U?0xe8c00U:0xe8bfaU;return true;
    case 0xe8bfa:return am_call(c,0x4c0f0,0xe8c00);                                                       // JSR 4c0f0.l.
    case 0xe8c00:am_word(r.d[7],0xb);r.pc=0xe8c04;return true;                                            // MOVE.W #b,D7.
    // CLR.L 36(A6); CLR.L 3a(A6); RTS.
    case 0xe8c04:if(!ofr7_put(c,r.a[6],0x36,4,0) || !ofr7_put(c,r.a[6],0x3a,4,0))return false;return am_return(c);
    default:return am_error(c,"unsupported animation objects fr7 PC");
    }
}
}
