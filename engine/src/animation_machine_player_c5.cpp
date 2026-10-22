#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc5_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc5_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR #bit,d16(An) (a memory operand: BYTE, bit = the immediate modulo 8). op 0 tests, 1 sets, 2 clears; old is the bit before (the Z
// of the instruction is old = 0).
bool pc5_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!pc5_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return pc5_put(c,base,displacement,1,op==1U?(value|mask):(value&~mask));
}
// TST.B / CMPI.B #k,d16(base); BEQ.W / BNE.W: equal_pc when BYTE = k, else other_pc.
bool pc5_byte_is(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc5_get(c,base,displacement,1,value))return false;
    c.s.pc=value==k?equal_pc:other_pc;return true;
}
// TST.B d16(A6); BMI.W / BPL.W: negative_pc when bit 7 of the BYTE is set, else other_pc.
bool pc5_byte_negative(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t negative_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc5_get(c,c.s.a[6],displacement,1,value))return false;
    c.s.pc=(value&0x80U)!=0U?negative_pc:other_pc;return true;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc5_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c5 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ANDI.B #fe,CCR / ORI.B #1,CCR; RTS: the C returned to the caller.
bool pc5_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// MOVE.W d16(A6),D0 (D0 bits 16..31 kept); JSR / BSR target.
bool pc5_field_call(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc5_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MULU.W #k,Dn (68000): the unsigned low WORD of Dn times the WORD k, the 32-bit product into the whole LONG Dn (bits 16..31 of Dn are not read).
void pc5_mulu(std::uint32_t& reg,std::uint32_t k) {
    reg=(reg&0xffffU)*(k&0xffffU);
}
// ASR.L #5,Dn: arithmetic LONG shift (the sign bit fills bits 27..31).
std::uint32_t pc5_asr5(std::uint32_t value) {
    return (value>>5)|((value&0x80000000U)!=0U?0xf8000000U:0U);
}
// MOVE.L #v,(A6): the node callback LONG.
bool pc5_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc5_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #21602,84(A6); MOVE.B #0,9c(A6); MOVE.B #1,aa(A6); CLR.W 7a(A6) (the slot-84 reset of 20e20 / 21314 / 21412).
bool pc5_slot_reset(AnimationMachineContext& c) {
    const std::uint32_t a6=c.s.a[6];
    return pc5_put(c,a6,0x84,4,0x21602) && pc5_put(c,a6,0x9c,1,0) && pc5_put(c,a6,0xaa,1,1) && pc5_put(c,a6,0x7a,2,0);
}
// MOVEQ #0,Dx; MOVE.L #k,Dy; SUB.L 36(A6),Dx; BMI.W skip_pc (the N of the LONG difference) / ADDI.L #1f,Dx (20de6 / 21446): Dx := 0 - LONG 36(A6).
bool pc5_drift_start(AnimationMachineContext& c,std::uint32_t k,std::uint32_t skip_pc,std::uint32_t round_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.d[2]=0;r.d[3]=k;if(!pc5_get(c,r.a[6],0x36,4,value))return false;r.d[2]=r.d[2]-value;
    r.pc=(r.d[2]&0x80000000U)!=0U?skip_pc:round_pc;return true;
}
// ASR.L #5,Dx; ADD.L Dx,d16(A6) (the LONG field, carry out lost).
bool pc5_drift_add(AnimationMachineContext& c,std::uint32_t& reg,std::uint32_t displacement) {
    std::uint32_t value=0;reg=pc5_asr5(reg);
    if(!pc5_get(c,c.s.a[6],displacement,4,value))return false;return pc5_put(c,c.s.a[6],displacement,4,value+reg);
}
// MOVE.W 76(A6),D0; LEA 1b128(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0 (fixed ROM WORD table 1b128 + sext(2 x WORD 76)); MOVE.B #1,D1; JSR 8ebe.l.
bool pc5_sound_call(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!pc5_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.a[0]=0x1b128;am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],1);return am_call(c,0x8ebe,return_pc);
}
// JMP table(PC,D0.W) of a BRA.W table (contract decision 2, FR4 rule): only the executed entry is a block of the unit; a displacement 0 .. last moves
// the PC to the table entry (an unrouted entry is the next dispatch's 'unsupported animation machine PC', a declared stop), any other D0.W is the
// checked jump-target error.  The displacements are multiples of 4 (two ADD.W D0,D0 before the JMP).
bool pc5_table_jump(AnimationMachineContext& c,std::uint32_t table,std::uint32_t last) {
    const std::uint32_t displacement=c.s.d[0]&0xffffU;
    if(displacement>last)return am_error(c,"unsupported animation player c5 jump target");
    c.s.pc=table+displacement;return true;
}
// SUBQ.B #1,88(A6); BCS.W 21564 (the borrow: the BYTE was 0).
bool pc5_count_down(AnimationMachineContext& c,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!pc5_get(c,c.s.a[6],0x88,1,value) || !pc5_put(c,c.s.a[6],0x88,1,value-1U))return false;
    c.s.pc=value==0U?0x21564U:next_pc;return true;
}
// MOVE.L A3,-(A7); MOVE.L A0,-(A7); JSR target.l (1c390 4d7a6 / 1c3c0 4d628).
bool pc5_save_call(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    if(!am_push(c,4,c.s.a[3]) || !am_push(c,4,c.s.a[0]))return false;return am_call(c,target,return_pc);
}
// MOVEA.L (A7)+,A0; MOVEA.L (A7)+,A3 (1c39a / 1c3ca).
bool pc5_restore(AnimationMachineContext& c) {
    return am_pop(c,4,c.s.a[0]) && am_pop(c,4,c.s.a[3]);
}
// The handlers of the (handler LONG, key WORD) list 21b26 that C3 215e6 matched for C3 21f70 (contract decision 2; JMP (A1) 21f7c).
const std::uint32_t PC5_LIST_21B26[3]={0x21602,0x21e48,0x21e3a};
}
// Player C5 (203 block starts, contract docs/analysis/animation-machine-player-c5-contract.md; area C plan unit C5 without the C3 block 202a0, with the
// plan block 202ac and the branch target 20f04, contract decision 1): the player state 20738 (installed by C3 2066a and 20554 / 2055e; 1cc1a, 206ec,
// the BRA.W table 20792 -> 20796 -> 208d2 loop, 2092c, the tables 2094e -> 2095a -> 212ce and 209d6), the landing states 212ce / 213da / 20e18 ->
// 2143c / 20e3e (installed and entered at once) -> 214c0 -> 214d6 -> 21520 -> 21542 / 21556, the record helper 1c356 (MULU tables 1c298, the C helper
// 4d628 with the LONG table 4cf64, the bit table 1c52c read by 1c51c, the 28ae child 1c4b0), the C2 record tail 1cb1a / 1cb38 / 1cb44, the C3 tails
// 20240 20268 202ac 20544 21c12 21f4c 21f78 (the JMP (A1) 21f7c of the list 21b26), 1d182 (4d106, 4de7a), 20de6, 20efc, cddee (28ae child cde42).
// C: the 7 consumers 1c374 (BCC, 289e), 1c3ca (BCC, 4d628), 20288 (BCS, 49c38), 20e56 214b2 (BCC, 49fc6), 21f78 (BCC, 215e6), cddfe (BCC, 28ae) read a
// known C or fail; 1cb30 (RTS) passes the Clear of the 1cb1a TST.L back to the 1cb08 callers (dispatcher carry list); 1cb1a 1c4aa 4d6a8 leave Clear,
// 1cb32 1c494 4d69c cde10 Set.  Z: 1c3e2 BEQ recomputes the Z of the BTST.L D1,D7 that ends 1c51c from fixed ROM (contract decision 3).
bool animation_player_c5_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool old=false;
    switch(r.pc) {
    // ---- 1c356 (JSR from 202ac 20764 and later units; D0.W the player index, D1.B the record type): CMPI.B #13,D1; BCC.W 1c4aa (unsigned BYTE).
    case 0x1c356:r.pc=(r.d[1]&0xffU)>=0x13U?0x1c4aa:0x1c35e;return true;
    // LEA -7348(A5),A0; ANDI.W #1,D0; BEQ.W 1c36e / LEA -7258(A5),A0 / JSR 289e.l / BCC.W 1c4aa (C of 289e).
    case 0x1c35e:r.a[0]=am_index(r.a[5],0x8cb8);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&0xffffU)==0U?0x1c36e:0x1c36a;return true;
    case 0x1c36a:r.a[0]=am_index(r.a[5],0x8da8);r.pc=0x1c36e;return true;
    case 0x1c36e:return am_call(c,0x289e,0x1c374);
    case 0x1c374:return pc5_carry(c,0x1c4aa,0x1c378);
    // LEA 1c298(PC),A3; MOVEA.L 8c(A0),A4; MOVE.W D1,D7; MULU.W #a,D7; LEA (A3,D7.W),A3 (the 10-byte record 1c298 + sext(product WORD)); TST.B D1;
    // BEQ.W 1c3dc.
    case 0x1c378:
        r.a[3]=0x1c298;if(!pc5_get(c,r.a[0],0x8c,4,r.a[4]))return false;am_word(r.d[7],r.d[1]);pc5_mulu(r.d[7],0xa);
        r.a[3]=am_index(r.a[3],r.d[7]&0xffffU);r.pc=(r.d[1]&0xffU)==0U?0x1c3dc:0x1c390;return true;
    case 0x1c390:return pc5_save_call(c,0x4d7a6,0x1c39a);
    case 0x1c39a:if(!pc5_restore(c))return false;r.pc=(r.d[0]&0xffU)==0U?0x1c3dc:0x1c3a4;return true;    // TST.B D0; BEQ.W 1c3dc.
    // MOVE.W 78(A0),D0; MOVE.B 1(A3),D2; MOVE.W 4(A3),D1; SUB.B D2,D6; BNE.W 1c3c0 (the Z of the BYTE difference).
    case 0x1c3a4:
        if(!pc5_get(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);if(!pc5_get(c,r.a[3],1,1,value))return false;am_byte(r.d[2],value);
        if(!pc5_get(c,r.a[3],4,2,value))return false;am_word(r.d[1],value);am_byte(r.d[6],r.d[6]-r.d[2]);r.pc=(r.d[6]&0xffU)!=0U?0x1c3c0:0x1c3b6;return true;
    case 0x1c3b6:r.pc=(r.d[5]&0xffffU)==0U?0x1c3c0:0x1c3bc;return true;                                 // TST.W D5; BEQ.W 1c3c0.
    case 0x1c3bc:if(!pc5_get(c,r.a[3],6,2,value))return false;am_word(r.d[1],value);r.pc=0x1c3c0;return true;   // MOVE.W 6(A3),D1.
    case 0x1c3c0:return pc5_save_call(c,0x4d628,0x1c3ca);
    case 0x1c3ca:if(!pc5_restore(c))return false;return pc5_carry(c,0x1c3dc,0x1c3d2);                    // BCC.W 1c3dc (C of 4d628).
    case 0x1c3d2:r.pc=(r.d[7]&0xffffU)==0U?0x1c4aa:0x1c3d8;return true;                                 // TST.W D7; BEQ.W 1c4aa.
    case 0x1c3d8:r.pc=0x1c462;return true;                                                                 // BRA.W 1c462.
    case 0x1c3dc:if(!am_read(c,r.a[3],1,value))return false;am_byte(r.d[1],value);return am_call(c,0x1c51c,0x1c3e2);   // MOVE.B (A3),D1; BSR.W 1c51c.
    // BEQ.W 1c4aa on the Z of the BTST.L D1,D7 that ends 1c51c (contract decision 3): D7 is the LONG of the fixed ROM table 1c52c + sext(4 x BYTE
    // 9e(A0)) and D1 the bit number (modulo 32); 1c51c and its RTS keep D1, D7, A0 and the BYTE.  The LONG is read again from fixed ROM; a BYTE 9e(A0)
    // outside work RAM / fixed ROM (a second device read) or a D7 that is not that LONG is the checked flag-source error.
    case 0x1c3e2: {
        const std::uint32_t at=am_index(r.a[0],0x9e);
        if((at&0xffffffU)>=0x200000U)return am_error(c,"unsupported animation player c5 flag source");
        if(!am_read(c,at,1,value))return false;
        std::uint32_t table=0;if(!am_read(c,am_index(0x1c52c,(value<<2)&0xffffU),4,table))return false;
        if(table!=r.d[7])return am_error(c,"unsupported animation player c5 flag source");
        r.pc=((table>>(r.d[1]&31U))&1U)==0U?0x1c4aa:0x1c3e6;return true;
    }
    // MOVE.W 78(A0),D0; MOVEA.L 8c(A0),A4; MOVEQ #0,D1; MOVE.B 4(A4),D1; MULU.W #a,D1; LEA 1c298(PC),A2; MOVE.B 1(A2,D1.W),D1; CMP.B 1(A3),D1;
    // BEQ.W 1c412.
    case 0x1c3e6:
        if(!pc5_get(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);if(!pc5_get(c,r.a[0],0x8c,4,r.a[4]))return false;
        r.d[1]=0;if(!pc5_get(c,r.a[4],4,1,value))return false;am_byte(r.d[1],value);pc5_mulu(r.d[1],0xa);r.a[2]=0x1c298;
        if(!am_read(c,am_index(r.a[2]+1U,r.d[1]&0xffffU),1,value))return false;am_byte(r.d[1],value);
        if(!pc5_get(c,r.a[3],1,1,value))return false;r.pc=(r.d[1]&0xffU)==value?0x1c412:0x1c408;return true;
    case 0x1c408:if(!pc5_get(c,r.a[3],4,2,value) || !pc5_put(c,r.a[4],0xc,2,value))return false;r.pc=0x1c432;return true;   // MOVE.W 4(A3),c(A4).
    // MOVE.W c(A4),D7; CMPI.W #3e7,D7; BCC.W 1c4aa (unsigned) / ADD.W 6(A3),D7; CMPI.W #3e7,D7; BCS.W 1c42e / MOVE.W #3e7,D7 / MOVE.W D7,c(A4).
    case 0x1c412:if(!pc5_get(c,r.a[4],0xc,2,value))return false;am_word(r.d[7],value);r.pc=value>=0x3e7U?0x1c4aa:0x1c41e;return true;
    case 0x1c41e:if(!pc5_get(c,r.a[3],6,2,value))return false;am_word(r.d[7],r.d[7]+value);r.pc=(r.d[7]&0xffffU)<0x3e7U?0x1c42e:0x1c42a;return true;
    case 0x1c42a:am_word(r.d[7],0x3e7);r.pc=0x1c42e;return true;
    case 0x1c42e:if(!pc5_put(c,r.a[4],0xc,2,r.d[7]))return false;r.pc=0x1c432;return true;
    // MOVE.B (A3),D1; CMP.B 4(A4),D1; BEQ.W 1c454 / MOVE.B 4(A4),5(A4); MOVE.B D1,4(A4); MOVE.B 2(A3),3(A4); CLR.B 2(A4); CLR.B a1(A0).
    case 0x1c432:if(!am_read(c,r.a[3],1,value))return false;am_byte(r.d[1],value);return pc5_byte_is(c,r.a[4],4,r.d[1]&0xffU,0x1c454,0x1c43c);
    case 0x1c43c:
        if(!pc5_get(c,r.a[4],4,1,value) || !pc5_put(c,r.a[4],5,1,value) || !pc5_put(c,r.a[4],4,1,r.d[1]) || !pc5_get(c,r.a[3],2,1,value) ||
           !pc5_put(c,r.a[4],3,1,value) || !pc5_put(c,r.a[4],2,1,0) || !pc5_put(c,r.a[0],0xa1,1,0))return false;
        r.pc=0x1c454;return true;
    case 0x1c454:if(!am_push(c,4,r.a[3]))return false;r.d[0]=0;return am_call(c,0x1c1f4,0x1c45c);     // MOVE.L A3,-(A7); MOVEQ #0,D0; BSR.W 1c1f4.
    case 0x1c45c:if(!pc5_get(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);if(!am_pop(c,4,r.a[3]))return false;r.pc=0x1c462;return true;
    // MOVE.W 8(A3),D1; MOVEM.W D0,-(A7) (the WORD D0); CMPI.L #0,b2(A6); BEQ.W 1c480 / MOVEA.L b2(A6),A0; MOVE.B #1,7a(A0).
    case 0x1c462:
        if(!pc5_get(c,r.a[3],8,2,value))return false;am_word(r.d[1],value);if(!am_push(c,2,r.d[0]&0xffffU))return false;
        if(!pc5_get(c,r.a[6],0xb2,4,value))return false;r.pc=value==0U?0x1c480:0x1c476;return true;
    case 0x1c476:if(!pc5_get(c,r.a[6],0xb2,4,r.a[0]) || !pc5_put(c,r.a[0],0x7a,1,1))return false;r.pc=0x1c480;return true;
    // MOVEM.L D1,-(A7); MOVEA.L #1c4b0,A0; MOVE.W #0,D0; JSR 28ae.l (the child 1c4b0).
    case 0x1c480:if(!am_push(c,4,r.d[1]))return false;r.a[0]=0x1c4b0;am_word(r.d[0],0);return am_call(c,0x28ae,0x1c494);
    // MOVEM.L (A7)+,D1; MOVE.W D1,76(A0); MOVE.L A0,b2(A6); MOVEM.W (A7)+,D0 (the WORD sign-extended into the whole LONG D0); ORI.B #1,CCR; RTS.
    case 0x1c494:
        if(!am_pop(c,4,r.d[1]) || !pc5_put(c,r.a[0],0x76,2,r.d[1]) || !pc5_put(c,r.a[6],0xb2,4,r.a[0]) || !am_pop(c,2,value))return false;
        r.d[0]=am_extend_word(value);return pc5_return_carry(c,AnimationCarrySet);
    case 0x1c4aa:return pc5_return_carry(c,AnimationCarryClear);                                          // ANDI.B #fe,CCR; RTS.
    // ---- 1c51c (BSR from 1c3dc and a later unit): MOVEQ #0,D7; MOVE.B 9e(A0),D7; LSL.W #2,D7; MOVE.L 1c52c(PC,D7.W),D7 (fixed ROM LONG table
    // 1c52c + sext(D7.W)); BTST.L D1,D7 (its Z is recomputed by the reader 1c3e2); RTS.
    case 0x1c51c:
        r.d[7]=0;if(!pc5_get(c,r.a[0],0x9e,1,value))return false;am_byte(r.d[7],value);am_word(r.d[7],r.d[7]<<2);
        if(!am_read(c,am_index(0x1c52c,r.d[7]&0xffffU),4,r.d[7]))return false;return am_return(c);
    // ---- 1cb1a (the Set side of C2 1cb08 BNE.W, D7.W = the WORD that was not 0): LEA (A0,D7.W),A1; MOVE.W (A1),D7; ADD.W D7,D7 twice; MOVEA.L 22(A6),A1;
    // TST.L (A1,D7.W) (C := Clear); BNE.W 1cb32 / RTS (1cb30 passes the Clear) / ORI.B #1,CCR; RTS.
    case 0x1cb1a:
        r.a[1]=am_index(r.a[0],r.d[7]&0xffffU);if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[7],value);
        am_word(r.d[7],r.d[7]+r.d[7]);am_word(r.d[7],r.d[7]+r.d[7]);if(!pc5_get(c,r.a[6],0x22,4,r.a[1]))return false;
        if(!am_read(c,am_index(r.a[1],r.d[7]&0xffffU),4,value))return false;r.carry=AnimationCarryClear;r.pc=value!=0U?0x1cb32:0x1cb30;return true;
    case 0x1cb30:case 0x1cce6:case 0x1d196:case 0x20f20:case 0x21540:case 0x21562:case 0x21fa4:case 0xcde14:return am_return(c);   // RTS.
    case 0x1cb32:return pc5_return_carry(c,AnimationCarrySet);                                         // ORI.B #1,CCR; RTS.
    // ---- 1cb38 (BSR from 21310 2140e 20e18 and later units): LEA 26(A6),A1; BRA.W 1cb44.
    case 0x1cb38:r.a[1]=am_index(r.a[6],0x26);r.pc=0x1cb44;return true;
    // ---- 1cb44 (and the fall-through of C3 1cb40): MOVE.W (A0),D7; ADD.W D7,D7 twice; MOVEA.L 22(A6),A0; MOVE.L (A0,D7.W),D7; BNE.W 1cb5c /
    // MOVE.L #1cafe,D7 / MOVEA.L D7,A0; EXG A0,A1; MOVE.W #100,D0; JMP 49f96.l.
    case 0x1cb44:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[7],value);am_word(r.d[7],r.d[7]+r.d[7]);am_word(r.d[7],r.d[7]+r.d[7]);
        if(!pc5_get(c,r.a[6],0x22,4,r.a[0]) || !am_read(c,am_index(r.a[0],r.d[7]&0xffffU),4,r.d[7]))return false;
        r.pc=r.d[7]!=0U?0x1cb5c:0x1cb56;return true;
    case 0x1cb56:r.d[7]=0x1cafe;r.pc=0x1cb5c;return true;
    case 0x1cb5c:r.a[0]=r.a[1];r.a[1]=r.d[7];am_word(r.d[0],0x100);r.pc=0x49f96;return true;
    // ---- 1cc1a (BSR from 20768 208e4 and later units): MOVEQ #0,D0; MOVE.B a0(A6),D0; MULU.W #9,D0; MOVEQ #0,D1; MOVE.B 9f(A6),D1; ADD.W D1,D0;
    // LEA 1cbb2(PC),A1; MOVE.B (A1,D0.W),D0 (fixed ROM BYTE table 1cbb2 + sext(D0.W)); BEQ.W 1cc6a.
    case 0x1cc1a:
        r.d[0]=0;if(!pc5_get(c,r.a[6],0xa0,1,value))return false;am_byte(r.d[0],value);pc5_mulu(r.d[0],9);
        r.d[1]=0;if(!pc5_get(c,r.a[6],0x9f,1,value))return false;am_byte(r.d[1],value);am_word(r.d[0],r.d[0]+r.d[1]);r.a[1]=0x1cbb2;
        if(!am_read(c,am_index(r.a[1],r.d[0]&0xffffU),1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x1cc6a:0x1cc38;return true;
    // MOVEQ #0,D1; MOVE.B D0,D1; ADD.W D1,D1 twice; MOVEA.L 1cc04(PC,D1.W),A0 (fixed ROM LONG table 1cc04 + sext(D1.W)); MOVE.W #1e,D0;
    // MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0x1cc38:
        r.d[1]=0;am_byte(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]+r.d[1]);am_word(r.d[1],r.d[1]+r.d[1]);
        if(!am_read(c,am_index(0x1cc04,r.d[1]&0xffffU),4,r.a[0]))return false;am_word(r.d[0],0x1e);r.a[1]=0x100bf4;return am_call(c,0x2986,0x1cc54);
    case 0x1cc54:r.d[0]=0;r.d[1]=0;return pc5_byte_is(c,r.a[6],0xa9,3,0x1cc66,0x1cc62);                 // MOVEQ #0,D0; MOVEQ #0,D1; CMPI.B #3,a9(A6).
    case 0x1cc62:r.d[0]=0;r.d[1]=0x10;r.pc=0x1cc66;return true;                                          // MOVEQ #0,D0; MOVEQ #10,D1.
    case 0x1cc66:return am_call(c,0x1cd00,0x1cc6a);                                                       // BSR.W 1cd00.
    // LEA 1cc10(PC),A1; MOVEQ #0,D0; MOVE.B 9f(A6),D0; TST.B (A1,D0.W); BEQ.W 1cce6 / MOVE.B a0(A6),D0; TST.B (A1,D0.W); BNE.W 1cce6 (fixed ROM
    // BYTE table 1cc10 + sext(D0.W); 1cc7c keeps D0 bits 8..31).
    case 0x1cc6a:
        r.a[1]=0x1cc10;r.d[0]=0;if(!pc5_get(c,r.a[6],0x9f,1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,am_index(r.a[1],r.d[0]&0xffffU),1,value))return false;r.pc=value==0U?0x1cce6:0x1cc7c;return true;
    case 0x1cc7c:
        if(!pc5_get(c,r.a[6],0xa0,1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,am_index(r.a[1],r.d[0]&0xffffU),1,value))return false;r.pc=value!=0U?0x1cce6:0x1cc88;return true;
    case 0x1cc88:r.a[0]=0x365fc;am_word(r.d[0],0x1e);r.a[1]=0x100bf4;return am_call(c,0x2986,0x1cc9e);   // MOVEA.L #365fc,A0; MOVE.W #1e,D0; ... JSR 2986.l.
    case 0x1cc9e:if(!pc5_get(c,r.a[6],0x76,2,value) || !pc5_put(c,r.a[0],0x76,2,value))return false;return am_call(c,0x491b6,0x1ccaa);   // MOVE.W 76(A6),76(A0).
    case 0x1ccaa:return pc5_byte_is(c,r.a[6],0xa9,3,0x1ccd0,0x1ccb4);                                    // CMPI.B #3,a9(A6); BEQ.W 1ccd0.
    case 0x1ccb4:r.d[0]=0;am_word(r.d[1],0x10);return pc5_byte_is(c,r.a[6],0xa9,2,0x1cd00,0x1ccc4);      // MOVEQ #0,D0; MOVE.W #10,D1; CMPI.B #2,a9.
    case 0x1ccc4:am_word(r.d[0],0);am_word(r.d[1],0x20);r.pc=0x1cd00;return true;                       // MOVE.W #0,D0; MOVE.W #20,D1; BRA.W 1cd00.
    // MOVEQ #0,D7; MOVE.B 7c(A6),D7; ADD.W D7,D7 twice; LEA 1cce8(PC,D7.W),A1; MOVE.W (A1)+,D0; MOVE.W (A1)+,D1 (fixed ROM WORD pairs); BRA.W 1cd00.
    case 0x1ccd0:
        r.d[7]=0;if(!pc5_get(c,r.a[6],0x7c,1,value))return false;am_byte(r.d[7],value);am_word(r.d[7],r.d[7]+r.d[7]);am_word(r.d[7],r.d[7]+r.d[7]);
        r.a[1]=am_index(0x1cce8,r.d[7]&0xffffU);if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[0],value);r.a[1]+=2U;
        if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[1],value);r.a[1]+=2U;r.pc=0x1cd00;return true;
    // ---- 1cd00: BTST.B #0,15(A6); BEQ.W 1cd0c / NEG.W D0 / JMP 49214.l.
    case 0x1cd00:if(!pc5_bit(c,r.a[6],0x15,0,0,old))return false;r.pc=old?0x1cd0a:0x1cd0c;return true;
    case 0x1cd0a:am_word(r.d[0],0U-r.d[0]);r.pc=0x1cd0c;return true;
    case 0x1cd0c:r.pc=0x49214;return true;
    // ---- 1d182 (BSR from 21520 21556 and later units): MOVE.W 78(A6),D0; JSR 4d106.l / MOVE.W 78(A6),D0; JSR 4de7a.l / RTS.
    case 0x1d182:return pc5_field_call(c,0x78,0x4d106,0x1d18c);
    case 0x1d18c:return pc5_field_call(c,0x78,0x4de7a,0x1d196);
    // ---- C3 tails: 20240 (fall-through of 20238): BCLR.B #2,a7(A6); BRA.W 20264.
    case 0x20240:if(!pc5_bit(c,r.a[6],0xa7,2,2,old))return false;r.pc=0x20264;return true;
    // 20268 (BEQ.W from 20234): BTST.B #0,a8(A6); BNE.W 20290 / BTST.B #7,10f000.l; BNE.W 20290 / MOVE.W 78(A6),D0; JSR 49c38.l / BCS.W 20290 (C of
    // 49c38) / BRA.W 202a0.
    case 0x20268:if(!pc5_bit(c,r.a[6],0xa8,0,0,old))return false;r.pc=old?0x20290:0x20272;return true;
    case 0x20272:if(!am_read(c,0x10f000,1,value))return false;r.pc=(value&0x80U)!=0U?0x20290:0x2027e;return true;
    case 0x2027e:return pc5_field_call(c,0x78,0x49c38,0x20288);
    case 0x20288:return pc5_carry(c,0x2028c,0x20290);
    case 0x2028c:r.pc=0x202a0;return true;
    // 202ac (fall-through of 202a0): MOVE.W 78(A6),D0; MOVEQ #0,D1; JSR 1c356(PC) (returns to C3 202b6).
    case 0x202ac:if(!pc5_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);r.d[1]=0;return am_call(c,0x1c356,0x202b6);
    // 20544 (fall-through of 2053c): MOVE.B 9e(A6),D0; CMPI.B #0,D0; BEQ.W 2055e / BRA.W 20554 / MOVE.L #20738,(A6) (written only); BRA.W 20626 /
    // MOVE.L #20738,(A6); BTST.B #7,61(A6); BNE.W 20574 / MOVE.L #1ff6c,(A6) (written only) / BRA.W 20626.
    case 0x20544:if(!pc5_get(c,r.a[6],0x9e,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x2055e:0x20550;return true;
    case 0x20550:r.pc=0x20554;return true;
    case 0x20554:return pc5_install(c,0x20738,0x20626);
    case 0x2055e:if(!pc5_put(c,r.a[6],0,4,0x20738) || !pc5_bit(c,r.a[6],0x61,7,0,old))return false;r.pc=old?0x20574:0x2056e;return true;
    case 0x2056e:return pc5_install(c,0x1ff6c,0x20574);
    case 0x20574:r.pc=0x20626;return true;
    // ---- 206ec (BSR from 20774): LEA 20710(PC),A0; MOVE.W 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0 (fixed ROM WORD table 20710 + sext(2 x WORD
    // 76)); JMP 3af8.l.
    case 0x206ec:
        r.a[0]=0x20710;if(!pc5_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);
        if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),2,value))return false;am_word(r.d[0],value);r.pc=0x3af8;return true;
    // ---- 20738 (node callback, installed by C3 2066a / 20554 / 2055e): BCLR.B #0,15(A6); TST.B 5f(A6); BMI.W 2074c / BSET.B #0,15(A6) /
    // BSET.B #7,61(A6); BCLR.B #7,a7(A6); BCLR.B #6,a7(A6); MOVE.W 78(A6),D0; MOVEQ #0,D1; JSR 1c356(PC).
    case 0x20738:if(!pc5_bit(c,r.a[6],0x15,0,2,old))return false;return pc5_byte_negative(c,0x5f,0x2074c,0x20746);
    case 0x20746:if(!pc5_bit(c,r.a[6],0x15,0,1,old))return false;r.pc=0x2074c;return true;
    case 0x2074c:
        if(!pc5_bit(c,r.a[6],0x61,7,1,old) || !pc5_bit(c,r.a[6],0xa7,7,2,old) || !pc5_bit(c,r.a[6],0xa7,6,2,old) || !pc5_get(c,r.a[6],0x78,2,value))return false;
        am_word(r.d[0],value);r.d[1]=0;return am_call(c,0x1c356,0x20768);
    case 0x20768:case 0x208e4:return am_call(c,0x1cc1a,r.pc+4U);                                         // BSR.W 1cc1a.
    case 0x2076c:case 0x208e8:return am_call(c,0x1c1e2,r.pc+4U);                                         // BSR.W 1c1e2.
    case 0x20770:case 0x208ee:return am_call(c,0x1d15a,r.pc+4U);                                         // BSR.W 1d15a.
    case 0x20774:return am_call(c,0x206ec,0x20778);                                                       // BSR.W 206ec.
    // CLR.L 56(A6); MOVE.W #e0ec,68(A6); MOVE.W #e0ec,1e(A6); MOVEQ #0,D0; MOVE.B 9e(A6),D0; ADD.W D0,D0 twice; JMP 20796(PC,D0.W) (contract
    // decision 2: the BRA.W table 20796..207a6 of 4 entries for BYTE 9e 0..3, only the executed entry 20796 is a block).
    case 0x20778:
        if(!pc5_put(c,r.a[6],0x56,4,0) || !pc5_put(c,r.a[6],0x68,2,0xe0ec) || !pc5_put(c,r.a[6],0x1e,2,0xe0ec))return false;
        r.d[0]=0;if(!pc5_get(c,r.a[6],0x9e,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        return pc5_table_jump(c,0x20796,0xc);
    case 0x20796:case 0x208ec:r.pc=0x208d2;return true;                                                  // BRA.W 208d2 (208ec: BRA.B 208d2).
    // ---- 208d2: CMPI.B #0,9e(A6); BEQ.W 208ee / MOVEQ #6,D0; MOVEA.L A6,A0; BSR.W 1c1f4 / BSR.W 1cc1a / BSR.W 1c1e2 / BRA.B 208d2.
    case 0x208d2:return pc5_byte_is(c,r.a[6],0x9e,0,0x208ee,0x208dc);
    case 0x208dc:r.d[0]=6;r.a[0]=r.a[6];return am_call(c,0x1c1f4,0x208e4);
    case 0x208f2:return pc5_byte_negative(c,0x5e,0x208fa,0x2092c);                                      // TST.B 5e(A6); BPL.W 2092c (208fa deferred).
    case 0x2092c:return am_call(c,0x1aa3a,0x20932);                                                       // JSR 1aa3a.l.
    case 0x20932:r.pc=(r.d[0]&8U)!=0U?0x209c2:0x2093a;return true;                                      // BTST.B #3,D0 (LONG bit 3); BNE.W 209c2.
    // MOVE.B 5e(A6),D0; CMPI.B #1b,D0; BCC.W 213da (unsigned BYTE) / ANDI.W #ff,D0; ADD.W D0,D0 twice; JMP 20952(PC,D0.W) (contract decision 2: the
    // BRA.W table 20952..209c2; the guard admits the entries 0..1a, only the executed entry 2095a is a block).
    case 0x2093a:case 0x209c2:
        if(!pc5_get(c,r.a[6],0x5e,1,value))return false;am_byte(r.d[0],value);
        r.pc=value>=0x1bU?(r.pc==0x2093aU?0x213daU:0x20e18U):r.pc+0xcU;return true;
    case 0x20946:case 0x209ce:
        am_word(r.d[0],r.d[0]&0xffU);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        return pc5_table_jump(c,r.pc==0x20946U?0x20952U:0x209daU,0x68);
    case 0x2095a:r.pc=0x212ce;return true;                                                                 // BRA.W 212ce (the entry 2 of 20952).
    // ---- 20de6 (BSR from 20e3e 21502 and later units): MOVEQ #0,D2; MOVE.L #30000,D3; SUB.L 36(A6),D2; BMI.W 20dfc / ADDI.L #1f,D2 / ASR.L #5,D2;
    // ADD.L D2,36(A6); SUB.L 3a(A6),D3; BMI.W 20e10 / ADDI.L #1f,D3 / ASR.L #5,D3; ADD.L D3,3a(A6); RTS.  21446 .. 21470 is the same with D3 =
    // ffea0000 and JSR 4be82.l at the end.
    case 0x20de6:return pc5_drift_start(c,0x30000,0x20dfc,0x20df6);
    case 0x21446:return pc5_drift_start(c,0xffea0000U,0x2145c,0x21456);
    case 0x20df6:case 0x21456:r.d[2]+=0x1fU;r.pc=r.pc==0x20df6U?0x20dfc:0x2145c;return true;
    case 0x20e0a:case 0x2146a:r.d[3]+=0x1fU;r.pc=r.pc==0x20e0aU?0x20e10:0x21470;return true;
    case 0x20dfc:case 0x2145c:
        if(!pc5_drift_add(c,r.d[2],0x36) || !pc5_get(c,r.a[6],0x3a,4,value))return false;r.d[3]=r.d[3]-value;
        r.pc=(r.d[3]&0x80000000U)!=0U?(r.pc==0x20dfcU?0x20e10U:0x21470U):(r.pc==0x20dfcU?0x20e0aU:0x2146aU);return true;
    case 0x20e10:if(!pc5_drift_add(c,r.d[3],0x3a))return false;return am_return(c);
    case 0x21470:if(!pc5_drift_add(c,r.d[3],0x3a))return false;return am_call(c,0x4be82,0x2147c);
    // ---- 20e18 (BCC.W from 209ca and the table 209da): LEA 1bc82(PC),A0; BSR.W 1cb38 / the slot-84 reset; MOVE.L #20e3e,(A6) (installed and
    // entered at once) / BSR.B 20de6 / JSR 4be82.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l / BCC.W 20e60 (C of 49fc6) / MOVE.L #214c0,(A6)
    // (written only) / BRA.W 21520.
    case 0x20e18:r.a[0]=0x1bc82;return am_call(c,0x1cb38,0x20e20);
    case 0x20e20:if(!pc5_slot_reset(c))return false;return pc5_install(c,0x20e3e,0x20e3e);
    case 0x20e3e:case 0x21502:return am_call(c,0x20de6,r.pc==0x20e3eU?0x20e40U:0x21506U);
    case 0x20e40:case 0x21506:return am_call(c,0x4be82,r.pc+6U);                                         // JSR 4be82.l.
    case 0x20e46:case 0x2150c:case 0x21494:
        if(r.pc==0x21494U) {
            // MOVE.W 88(A6),D0; SUB.W 2c(A6),D0; ASR.W #4,D0 (arithmetic WORD shift); ADD.W D0,2c(A6) first.
            if(!pc5_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);if(!pc5_get(c,r.a[6],0x2c,2,value))return false;
            am_word(r.d[0],r.d[0]-value);const std::uint32_t w=r.d[0]&0xffffU;am_word(r.d[0],(w>>4)|((w&0x8000U)!=0U?0xf000U:0U));
            if(!pc5_get(c,r.a[6],0x2c,2,value) || !pc5_put(c,r.a[6],0x2c,2,value+r.d[0]))return false;
        }
        return pc5_field_call(c,0x1e,0xce02,r.pc==0x21494U?0x214acU:r.pc+0xaU);                            // MOVE.W 1e(A6),D0; JSR ce02.l.
    case 0x20e50:case 0x214ac:case 0x21516:return am_call(c,0x49fc6,r.pc+6U);                            // JSR 49fc6.l.
    case 0x20e56:return pc5_carry(c,0x20e60,0x20e5a);                                                     // BCC.W 20e60.
    case 0x20e5a:return pc5_install(c,0x214c0,0x20e60);
    case 0x20e60:case 0x214bc:case 0x2151c:r.pc=0x21520;return true;                                     // BRA.W 21520.
    // ---- 20efc (BSR from 213da and later units): MOVE.L #a9800,3a(A6) / 20f04 (BSR target of later units): TST.B 5f(A6); BMI.W 20f18 /
    // MOVE.L #20000,36(A6); BRA.W 20f20 / MOVE.L #fffe0000,36(A6) / RTS.
    case 0x20efc:if(!pc5_put(c,r.a[6],0x3a,4,0xa9800))return false;r.pc=0x20f04;return true;
    case 0x20f04:return pc5_byte_negative(c,0x5f,0x20f18,0x20f0c);
    case 0x20f0c:case 0x20f18:if(!pc5_put(c,r.a[6],0x36,4,r.pc==0x20f0cU?0x20000U:0xfffe0000U))return false;r.pc=0x20f20;return true;
    // ---- 212ce (the table entry 2095a): JSR 8ff4.l / the sound call 8ebe / JSR cddee.l / BTST.B #7,15(A6); BEQ.W 2130c / CLR.L 36(A6); CLR.L 3a(A6);
    // LEA 1bc52(PC),A0; BRA.W 21310 / LEA 1bc4c(PC),A0 / BSR.W 1cb38 / the slot-84 reset; MOVE.W #100,88(A6); BRA.W 21430.
    case 0x212ce:case 0x213de:return am_call(c,0x8ff4,r.pc+6U);
    case 0x212d4:return pc5_sound_call(c,0x212ec);
    case 0x213e4:return pc5_sound_call(c,0x213fc);
    case 0x212ec:return am_call(c,0xcddee,0x212f2);
    case 0x212f2:if(!pc5_bit(c,r.a[6],0x15,7,0,old))return false;r.pc=old?0x212fc:0x2130c;return true;
    case 0x212fc:if(!pc5_put(c,r.a[6],0x36,4,0) || !pc5_put(c,r.a[6],0x3a,4,0))return false;r.a[0]=0x1bc52;r.pc=0x21310;return true;
    case 0x2130c:r.a[0]=0x1bc4c;r.pc=0x21310;return true;
    case 0x21310:case 0x2140e:return am_call(c,0x1cb38,r.pc+4U);                                         // BSR.W 1cb38.
    case 0x21314:case 0x21412:
        if(!pc5_slot_reset(c) || !pc5_put(c,r.a[6],0x88,2,r.pc==0x21314U?0x100U:0x20U))return false;r.pc=0x21430;return true;
    // ---- 213da (BCC.W from 2093a and the table 20952): BSR.W 20efc / JSR 8ff4.l / the sound call 8ebe / LEA 1bc4c(PC),A0; BTST.B #7,15(A6);
    // BEQ.W 2140e / LEA 1bc4a(PC),A0 / BSR.W 1cb38 / the slot-84 reset; MOVE.W #20,88(A6) (falls into 21430).
    case 0x213da:return am_call(c,0x20efc,0x213de);
    case 0x213fc:r.a[0]=0x1bc4c;if(!pc5_bit(c,r.a[6],0x15,7,0,old))return false;r.pc=old?0x2140a:0x2140e;return true;
    case 0x2140a:r.a[0]=0x1bc4a;r.pc=0x2140e;return true;
    // ---- 21430: BCLR.B #7,15(A6); MOVE.L #2143c,(A6) (installed and entered at once).
    case 0x21430:if(!pc5_bit(c,r.a[6],0x15,7,2,old))return false;return pc5_install(c,0x2143c,0x2143c);
    // ---- 2143c (node callback): BTST.B #7,15(A6); BNE.W 21480 / the drift 21446 .. 21470 / BRA.W 21494 / MOVE.W #100,88(A6); MOVE.L #0,64(A6);
    // JSR 4bfc0.l / 21494 (WORD 2c) / JSR 49fc6.l / BCC.W 214bc (C of 49fc6) / MOVE.L #214c0,(A6) (written only) / BRA.W 21520.
    case 0x2143c:if(!pc5_bit(c,r.a[6],0x15,7,0,old))return false;r.pc=old?0x21480:0x21446;return true;
    case 0x2147c:r.pc=0x21494;return true;
    case 0x21480:if(!pc5_put(c,r.a[6],0x88,2,0x100) || !pc5_put(c,r.a[6],0x64,4,0))return false;return am_call(c,0x4bfc0,0x21494);
    case 0x214b2:return pc5_carry(c,0x214bc,0x214b6);                                                     // BCC.W 214bc.
    case 0x214b6:return pc5_install(c,0x214c0,0x214bc);
    // ---- 214c0 (node callback): CLR.B 82(A6); MOVE.B #1e,88(A6); BSET.B #3,61(A6); MOVE.L #214d6,(A6) (installed and entered at once) /
    // 214d6: SUBQ.B #1,88(A6); BCS.W 21564 (C6) / JSR 1aa3a.l twice / BTST.B #3,D0; BNE.W 21502 / CLR.L 36(A6); ADDI.L #ffffb000,3a(A6);
    // BRA.W 21506 / BSR.W 20de6 / JSR 4be82.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l / BRA.W 21520.
    case 0x214c0:
        if(!pc5_put(c,r.a[6],0x82,1,0) || !pc5_put(c,r.a[6],0x88,1,0x1e) || !pc5_bit(c,r.a[6],0x61,3,1,old))return false;return pc5_install(c,0x214d6,0x214d6);
    case 0x214d6:return pc5_count_down(c,0x214de);
    case 0x214de:case 0x214e4:return am_call(c,0x1aa3a,r.pc+6U);                                         // JSR 1aa3a.l.
    case 0x214ea:r.pc=(r.d[0]&8U)!=0U?0x21502:0x214f2;return true;                                      // BTST.B #3,D0 (LONG bit 3); BNE.W 21502.
    case 0x214f2:
        if(!pc5_put(c,r.a[6],0x36,4,0) || !pc5_get(c,r.a[6],0x3a,4,value) || !pc5_put(c,r.a[6],0x3a,4,value+0xffffb000U))return false;r.pc=0x21506;return true;
    // ---- 21520: BSR.W 1d182 / MOVE.W 42(A6),D0; CMPI.W #140,D0; BCC.W 21542 (unsigned) / MOVE.W 46(A6),D0; SUBI.W #c0,D0; CMPI.W #200,D0;
    // BCC.W 21542 / RTS / MOVE.B #1e,88(A6); CLR.B 81(A6); CLR.B 82(A6); MOVE.L #21556,(A6) (installed and entered at once) / 21556: BSR.W 1d182 /
    // SUBQ.B #1,88(A6); BCS.W 21564 (C6) / RTS.
    case 0x21520:case 0x21556:return am_call(c,0x1d182,r.pc+4U);
    case 0x21524:if(!pc5_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value);r.pc=value>=0x140U?0x21542:0x21530;return true;
    case 0x21530:
        if(!pc5_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],value-0xc0U);r.pc=(r.d[0]&0xffffU)>=0x200U?0x21542:0x21540;return true;
    case 0x21542:
        if(!pc5_put(c,r.a[6],0x88,1,0x1e) || !pc5_put(c,r.a[6],0x81,1,0) || !pc5_put(c,r.a[6],0x82,1,0))return false;return pc5_install(c,0x21556,0x21556);
    case 0x2155a:return pc5_count_down(c,0x21562);
    // ---- 21c12 (the Set side of C3 21c06): LEA 1b7ba(PC),A0; BSR.W 1cb08 (returns to C3 21c1a).  21f4c (BCS.W from C3 21c9c / C4 21dc8): LEA
    // 1b7ba(PC),A0; BSR.W 1cabe / CLR.B a3(A6) (falls into C3 21f58).
    case 0x21c12:r.a[0]=0x1b7ba;return am_call(c,0x1cb08,0x21c1a);
    case 0x21f4c:r.a[0]=0x1b7ba;return am_call(c,0x1cabe,0x21f54);
    case 0x21f54:if(!pc5_put(c,r.a[6],0xa3,1,0))return false;r.pc=0x21f58;return true;
    // ---- 21f78 (the return of C3 21f70 BSR.W 215e6): BCC.W 21f7e (C of 215e6) / JMP (A1) (contract decision 2: a handler of the list 21b26, else
    // checked) / BSR.W 1cd98 / BTST.B #6 / #4,D0; BNE.W 21ffc / 2210c (C12) / BSR.W 2156a / TST.W D7; BEQ.W 21fa4 / MOVE.L #21602,84(A6) / RTS.
    case 0x21f78:return pc5_carry(c,0x21f7e,0x21f7c);
    case 0x21f7c:
        for(unsigned int i=0;i<3U;++i)if(PC5_LIST_21B26[i]==r.a[1]){r.pc=r.a[1];return true;}
        return am_error(c,"unsupported animation player c5 jump target");
    case 0x21f7e:return am_call(c,0x1cd98,0x21f82);
    case 0x21f82:r.pc=(r.d[0]&0x40U)!=0U?0x21ffc:0x21f8a;return true;
    case 0x21f8a:r.pc=(r.d[0]&0x10U)!=0U?0x2210c:0x21f92;return true;
    case 0x21f92:return am_call(c,0x2156a,0x21f96);
    case 0x21f96:r.pc=(r.d[7]&0xffffU)==0U?0x21fa4:0x21f9c;return true;
    case 0x21f9c:if(!pc5_put(c,r.a[6],0x84,4,0x21602))return false;r.pc=0x21fa4;return true;
    // ---- 4d106 (JSR from 1d182): TST.W 78(A6); BNE.W 4d116 / LEA 5cba(A5),A4; BRA.W 4d11a / LEA 5ce6(A5),A4 / MOVE.W #0,(A4); MOVE.B #2,22(A4); RTS.
    case 0x4d106:if(!pc5_get(c,r.a[6],0x78,2,value))return false;r.pc=value!=0U?0x4d116:0x4d10e;return true;
    case 0x4d10e:case 0x4d62e:r.a[4]=am_index(r.a[5],0x5cba);r.pc=r.pc==0x4d10eU?0x4d11a:0x4d63a;return true;
    case 0x4d116:case 0x4d636:r.a[4]=am_index(r.a[5],0x5ce6);r.pc=r.pc==0x4d116U?0x4d11a:0x4d63a;return true;
    case 0x4d11a:if(!pc5_put(c,r.a[4],0,2,0) || !pc5_put(c,r.a[4],0x22,1,2))return false;return am_return(c);
    // ---- 4d628 (JSR from 1c3c0): TST.B D0; BNE.W 4d636 / LEA 5cba(A5),A4; BRA.W 4d63a / LEA 5ce6(A5),A4 / TST.W (A4); BEQ.W 4d6a8.
    case 0x4d628:r.pc=(r.d[0]&0xffU)!=0U?0x4d636:0x4d62e;return true;
    case 0x4d63a:if(!am_read(c,r.a[4],2,value))return false;r.pc=value==0U?0x4d6a8:0x4d640;return true;
    // MOVE.B 27(A4),D7; ANDI.W #ff,D7; MULU.W #10,D7; LEA 4cf64(PC),A2; ADDA.W D7,A2 (sext); MOVE.L 4(A2),D7 (the 16-byte records of fixed ROM
    // 4cf64); BTST.L D2,D7; BEQ.W 4d6a8.
    case 0x4d640:
        if(!pc5_get(c,r.a[4],0x27,1,value))return false;am_byte(r.d[7],value);am_word(r.d[7],r.d[7]&0xffU);pc5_mulu(r.d[7],0x10);
        r.a[2]=am_index(0x4cf64,r.d[7]&0xffffU);if(!pc5_get(c,r.a[2],4,4,r.d[7]))return false;r.pc=((r.d[7]>>(r.d[2]&31U))&1U)==0U?0x4d6a8:0x4d65c;return true;
    // BSET.B #2,2b(A4); TST.B D2; BEQ.W 4d67a / CMP.B 2a(A4),D2; BEQ.W 4d676 / MOVE.W #0,20(A4) / MOVE.B D2,2a(A4).
    case 0x4d65c:if(!pc5_bit(c,r.a[4],0x2b,2,1,old))return false;r.pc=(r.d[2]&0xffU)==0U?0x4d67a:0x4d668;return true;
    case 0x4d668:return pc5_byte_is(c,r.a[4],0x2a,r.d[2]&0xffU,0x4d676,0x4d670);
    case 0x4d670:if(!pc5_put(c,r.a[4],0x20,2,0))return false;r.pc=0x4d676;return true;
    case 0x4d676:if(!pc5_put(c,r.a[4],0x2a,1,r.d[2]))return false;r.pc=0x4d67a;return true;
    // MOVE.W 20(A4),D7; BMI.W 4d69c / ADD.W 20(A4),D1; CMPI.W #3e8,D1; BCS.W 4d692 (unsigned) / MOVE.W #3e7,D1 / MOVE.W D1,20(A4); SUB.W 20(A4),D7;
    // NEG.W D7 (D7.W := new - old).
    case 0x4d67a:if(!pc5_get(c,r.a[4],0x20,2,value))return false;am_word(r.d[7],value);r.pc=(value&0x8000U)!=0U?0x4d69c:0x4d682;return true;
    case 0x4d682:if(!pc5_get(c,r.a[4],0x20,2,value))return false;am_word(r.d[1],r.d[1]+value);r.pc=(r.d[1]&0xffffU)<0x3e8U?0x4d692:0x4d68e;return true;
    case 0x4d68e:am_word(r.d[1],0x3e7);r.pc=0x4d692;return true;
    case 0x4d692:
        if(!pc5_put(c,r.a[4],0x20,2,r.d[1]) || !pc5_get(c,r.a[4],0x20,2,value))return false;am_word(r.d[7],r.d[7]-value);am_word(r.d[7],0U-r.d[7]);
        r.pc=0x4d69c;return true;
    // MOVEQ #0,D1; MOVE.B 2a(A4),D1; ORI.B #1,CCR; RTS / MOVE.W #0,D1; MOVEQ #0,D7; ANDI.B #fe,CCR; RTS.
    case 0x4d69c:r.d[1]=0;if(!pc5_get(c,r.a[4],0x2a,1,value))return false;am_byte(r.d[1],value);return pc5_return_carry(c,AnimationCarrySet);
    case 0x4d6a8:am_word(r.d[1],0);r.d[7]=0;return pc5_return_carry(c,AnimationCarryClear);
    // ---- 4de7a (JSR from 1d18c): LEA 5d12(A5),A4; ANDI.W #1,D0; BEQ.W 4de8a / LEA 5d18(A5),A4 / MOVE.W #ffff,4(A4); MOVE.B #ff,1(A4); MOVE.B #2,(A4);
    // RTS.
    case 0x4de7a:r.a[4]=am_index(r.a[5],0x5d12);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&0xffffU)==0U?0x4de8a:0x4de86;return true;
    case 0x4de86:r.a[4]=am_index(r.a[5],0x5d18);r.pc=0x4de8a;return true;
    case 0x4de8a:if(!pc5_put(c,r.a[4],4,2,0xffff) || !pc5_put(c,r.a[4],1,1,0xff) || !pc5_put(c,r.a[4],0,1,2))return false;return am_return(c);
    // ---- cddee (JSR from 212ec): MOVEA.L #cde42,A0; MOVE.W #1e,D0; JSR 28ae.l (the child cde42, FR7) / BCC.W cde14 (C of 28ae) / MOVE.W #8,D0;
    // MOVE.W #0,D1; JSR 4970a.l / ORI.B #1,CCR / RTS (cde14 passes no C to a reader: Unknown after it).
    case 0xcddee:r.a[0]=0xcde42;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0xcddfe);
    case 0xcddfe:return pc5_carry(c,0xcde14,0xcde02);
    case 0xcde02:am_word(r.d[0],8);am_word(r.d[1],0);return am_call(c,0x4970a,0xcde10);
    case 0xcde10:r.carry=AnimationCarrySet;r.pc=0xcde14;return true;                                     // ORI.B #1,CCR (falls into the RTS cde14).
    default:return am_error(c,"unsupported animation player c5 PC");
    }
}
}
