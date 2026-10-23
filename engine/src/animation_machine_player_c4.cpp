#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc4_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc4_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR / BCHG #bit,d16(A6) (a memory operand: BYTE, bit = the immediate modulo 8). op 0 tests, 1 sets, 2 clears, 3 changes; old is the
// bit before (the Z of the instruction is old = 0).
bool pc4_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!pc4_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return pc4_put(c,base,displacement,1,op==1U?(value|mask):(op==2U?(value&~mask):(value^mask)));
}
// TST.B / CMPI.B d16(base) against k; BNE.W / BEQ.W: equal_pc when BYTE = k, else other_pc.
bool pc4_byte_is(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc4_get(c,base,displacement,1,value))return false;
    c.s.pc=value==k?equal_pc:other_pc;return true;
}
// TST.W / CMPI.W #0,d16(A6); BEQ.W / BNE.W: zero_pc when the WORD is 0, else other_pc.
bool pc4_word_zero(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc4_get(c,c.s.a[6],displacement,2,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc4_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c4 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// SCS.B D0 on the known C returned by the callee (D0.B := ff when set, 00 when clear; D0 bits 8..31 kept).
bool pc4_scs(AnimationMachineContext& c) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c4 caller requires known carry");
    am_byte(c.s.d[0],c.s.carry==AnimationCarrySet?0xffU:0U);return true;
}
// ANDI.B #fe,CCR / ORI.B #1,CCR; RTS (and MOVEQ #0,D7; RTS): the C returned to the caller.
bool pc4_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// DIVU.W divisor,Dn (68000): the LONG Dn divided by the unsigned WORD divisor.  Quotient <= ffff: Dn := remainder WORD << 16 | quotient WORD.  Quotient
// above ffff: the overflow (V set) leaves Dn unchanged; no C4 block reads the flags of a DIVU (contract decision 4).  Divisor 0: the 68000 takes the
// zero-divide exception (vector 5), which the machine does not model: checked error (rollback), never a C++ division by zero.
bool pc4_divu(AnimationMachineContext& c,std::uint32_t& reg,std::uint32_t divisor) {
    const std::uint32_t d=divisor&0xffffU;
    if(d==0U)return am_error(c,"unsupported animation player c4 divide by zero");
    const std::uint32_t quotient=reg/d;
    if(quotient>0xffffU)return true;
    reg=((reg%d)<<16)|quotient;return true;
}
// MOVE.L D0,3c0000.l: one original LONG write to the video address / data port is one observed video event (card menu / HUD convention).
void pc4_video(AnimationMachineContext& c,std::uint32_t value) {
    VideoPortWrite port;port.address=0x3c0000;port.size=4;port.value=value;c.ports.push_back(port);
}
// MOVE.W d16(A6),D0 (D0 bits 16..31 kept); JSR target.l.
bool pc4_field_call(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc4_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MOVE.B #0,9a(A6); MOVE.W d16(A6),D0; MOVE.W #320,D1; MOVE.W #d2,D2; MOVE.W #d3,D3 (bits 16..31 kept), then JSR / JMP 35a2.
bool pc4_digits(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t d2,std::uint32_t d3) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!pc4_put(c,r.a[6],0x9a,1,0) || !pc4_get(c,r.a[6],displacement,2,value))return false;
    am_word(r.d[0],value);am_word(r.d[1],0x320);am_word(r.d[2],d2);am_word(r.d[3],d3);return true;
}
// The number output loops 371e / 3786 (D4.W digits, D7.W value, D3.B the leading-digit flag): MOVEQ #0,D2; MOVE.W D4,D5; CMPI.W #6,D5; BCC.W skip_pc
// (unsigned D5.W >= 6: no division, D2 = 0).
void pc4_digit_count(AnimationMachineState& r,std::uint32_t skip_pc,std::uint32_t divide_pc) {
    r.d[2]=0;am_word(r.d[5],r.d[4]);r.pc=(r.d[5]&0xffffU)>=6U?skip_pc:divide_pc;
}
// MOVE.W D7,D2; ADD.W D5,D5; DIVU.W 377a(PC,D5.W),D2 (fixed ROM WORD table 377a + sext(D5.W): 0 1 a 64 3e8 2710); ANDI.L #ffff,D2; DIVU.W #a,D2;
// SWAP D2 (D2.W := the decimal digit).  The dividend is the whole LONG D2 (bits 16..31 as they come in).
bool pc4_digit_divide(AnimationMachineContext& c,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t divisor=0;
    am_word(r.d[2],r.d[7]);am_word(r.d[5],r.d[5]+r.d[5]);
    if(!am_read(c,am_index(0x377a,r.d[5]&0xffffU),2,divisor) || !pc4_divu(c,r.d[2],divisor))return false;
    r.d[2]&=0xffffU;if(!pc4_divu(c,r.d[2],0xa))return false;am_swap(r.d[2]);r.pc=next_pc;return true;
}
// LEA 370c(PC),A0; MOVE.B (A0,D2.W),D2 (fixed ROM BYTE table 370c + sext(D2.W): the characters "0123456789ABCDEF "); LEA 3650(PC),A0; JSR (A1)
// (contract decision 2: A1 = 3650, written by the LEA 3650(PC),A1 of 371e / 3786; any other A1 is the checked jump-target error).
bool pc4_digit_put(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=0x370c;if(!am_read(c,am_index(0x370c,r.d[2]&0xffffU),1,value))return false;am_byte(r.d[2],value);r.a[0]=0x3650;
    if(r.a[1]!=0x3650U)return am_error(c,"unsupported animation player c4 jump target");
    return am_call(c,r.a[1],return_pc);
}
// The handlers of the (handler LONG, key WORD) list 21aee that 215e6 matched for 21c66 (contract decision 2; JMP (A1) 21c72).
const std::uint32_t PC4_LIST_21AEE[4]={0x21602,0x21d60,0x21e48,0x21e3a};
}
// Player C4 (231 block starts, contract docs/analysis/animation-machine-player-c4-contract.md; area C plan unit C4 and the hidden straight-line block
// 4e57e, contract decision 1): the body of the slot callback 4e94e (4e962 / 4e986 .. 4eb4c: the HUD of the player slot, the number output 371e / 3786
// (DIVU table 377a, JSR (A1) = 3650), 4ee7a, 4eef4, the energy gauge 4f22c and 4f13c / 4f118 / 4f152 .. 4f2b8 (DIVU / MULU, video port writes
// 3c0000)), the slot state 4e758 (4a974 Z, 4e538 / 4e564 / 4e57e), 4e4e2 (35a2 digits), the helpers 1be3a 1bf94 1c052 1c086 4d9a2 4da08, the player
// state 1eeea / 1ef0e (installed at 1ef08; 1cfbe record LONG table 1cfce, 1d09e, 1cec2, 1ceb0), the slot-84 state 21d60 / 21d92 (list 21b0a) and the
// JMP (A1) 21c72 of 21c66 (list 21aee).  C: the 11 consumers read a known C or fail (1be50 1bf9a 1c058 1efb4 21d6c 21d74 21d9a 21dc8 4f144 BCC / BCS,
// 4e75e 4e96c SCS: their CMP.B sets C again and leaves it Unknown); 1efb0 (BSR 1ed34) keeps the incoming C (dispatcher carry list); 1ef9a (AND.W)
// 1be64 4da1c 4f126 leave Clear, 1be5e 4da20 4f130 Set.  Z: 4e77a BEQ recomputes the Z of the TST.B (A0) that ends 4a974 from memory (contract decision 3).
bool animation_player_c4_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool old=false;
    switch(r.pc) {
    // ---- 371e / 3786 (JSR from 4ead6 4eb3e / 4ea0e): LEA 3650(PC),A1, then the digit loop (D4.W digits).
    case 0x371e:case 0x3786:r.a[1]=0x3650;r.pc=r.pc+4U;return true;
    case 0x3722:case 0x378a:r.pc=(r.d[4]&0xffffU)!=1U?r.pc+0xcU:r.pc+8U;return true;                 // CMPI.W #1,D4; BNE.W 372e / 3796.
    case 0x372a:case 0x3792:case 0x3754:case 0x37bc:am_byte(r.d[3],0xff);                            // MOVE.B #ff,D3 (3754 / 37bc: BRA.W 3766 / 37ca).
        r.pc=r.pc==0x3754U?0x3766U:(r.pc==0x37bcU?0x37caU:r.pc+4U);return true;
    case 0x372e:pc4_digit_count(r,0x374e,0x373a);return true;
    case 0x3796:pc4_digit_count(r,0x37b6,0x37a2);return true;
    case 0x373a:return pc4_digit_divide(c,0x374e);
    case 0x37a2:return pc4_digit_divide(c,0x37b6);
    case 0x374e:r.pc=(r.d[2]&0xffffU)==0U?0x375c:0x3754;return true;                                   // TST.W D2; BEQ.W 375c.
    case 0x37b6:r.pc=(r.d[2]&0xffffU)==0U?0x37c4:0x37bc;return true;                                   // TST.W D2; BEQ.W 37c4.
    case 0x375c:r.pc=(r.d[3]&0xffU)!=0U?0x3766:0x3762;return true;                                     // TST.B D3; BNE.W 3766.
    case 0x37c4:r.pc=(r.d[3]&0xffU)==0U?0x37dc:0x37ca;return true;                                     // TST.B D3; BEQ.W 37dc.
    case 0x3762:am_word(r.d[2],0x10);r.pc=0x3766;return true;                                           // MOVE.W #10,D2 (the space).
    case 0x3766:return pc4_digit_put(c,0x3774);
    case 0x37ca:if(!am_push(c,4,r.a[0]))return false;return pc4_digit_put(c,0x37da);                  // MOVE.L A0,-(A7) first.
    case 0x37da:if(!am_pop(c,4,r.a[0]))return false;r.pc=0x37dc;return true;                          // MOVEA.L (A7)+,A0.
    // SUBQ.W #1,D4; BNE.B 3722 / 378a.
    case 0x3774:case 0x37dc:am_word(r.d[4],r.d[4]-1U);r.pc=(r.d[4]&0xffffU)!=0U?(r.pc==0x3774U?0x3722U:0x378aU):r.pc+4U;return true;
    // ---- 1be3a (JSR from 4e966): LEA -7348(A5),A0; ANDI.W #1,D0; BEQ.W 1be4a / LEA -7258(A5),A0 / JSR 289e.l / BCC.W 1be64 (C of 289e) /
    // BTST.B #4,a8(A0); BEQ.W 1be64 / ORI.B #1,CCR; RTS / ANDI.B #fe,CCR; RTS.
    case 0x1be3a:r.a[0]=am_index(r.a[5],0x8cb8);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&0xffffU)==0U?0x1be4a:0x1be46;return true;
    case 0x1be46:r.a[0]=am_index(r.a[5],0x8da8);r.pc=0x1be4a;return true;
    case 0x1be4a:case 0x1bf94:return am_call(c,0x289e,r.pc+6U);
    case 0x1be50:return pc4_carry(c,0x1be64,0x1be54);
    case 0x1be54:if(!pc4_bit(c,r.a[0],0xa8,4,0,old))return false;r.pc=old?0x1be5e:0x1be64;return true;
    case 0x1be5e:return pc4_return_carry(c,AnimationCarrySet);
    case 0x1be64:return pc4_return_carry(c,AnimationCarryClear);
    // ---- 1bf94 (JSR from 4ea1e and others): JSR 289e.l / BCS.W 1bfa8 / MOVE.W #ffff,D0; MOVE.W #ffff,D2; RTS / CLR.W D0; MOVE.B 9e(A0),D0;
    // MOVE.W 76(A0),D2; RTS.
    case 0x1bf9a:return pc4_carry(c,0x1bf9e,0x1bfa8);
    case 0x1bf9e:am_word(r.d[0],0xffff);am_word(r.d[2],0xffff);return am_return(c);
    case 0x1bfa8:
        am_word(r.d[0],0);if(!pc4_get(c,r.a[0],0x9e,1,value))return false;am_byte(r.d[0],value);
        if(!pc4_get(c,r.a[0],0x76,2,value))return false;am_word(r.d[2],value);return am_return(c);
    // ---- 1c052 (JSR from 4ea70): JSR 4da08.l / BCC.W 1c05e (C of 4da08) / RTS / ANDI.W #1,D0; BNE.W 1c06c / MOVE.W 545c(A5),D7; RTS /
    // MOVE.W 546c(A5),D7; RTS.
    case 0x1c052:return am_call(c,0x4da08,0x1c058);
    case 0x1c058:return pc4_carry(c,0x1c05e,0x1c05c);
    case 0x1c05c:case 0x1d0c0:case 0x4ef06:case 0x4f150:case 0x4f25c:case 0x4f2b8:case 0x3778:case 0x37e0:return am_return(c);   // RTS.
    case 0x1c05e:am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&0xffffU)!=0U?0x1c06c:0x1c066;return true;
    case 0x1c066:case 0x1c06c:if(!pc4_get(c,r.a[5],r.pc==0x1c066U?0x545cU:0x546cU,2,value))return false;am_word(r.d[7],value);return am_return(c);
    // ---- 1c086 (JSR from 4eae0): ANDI.W #1,D0; MOVE.W D0,-(A7); JSR 4d7a6.l / MOVE.W D0,D7; MOVE.W (A7)+,D0; TST.B D7; BEQ.W 1c0b4 / JSR 4d9a2.l /
    // CMPI.B #1,D7; BNE.W 1c0b4 / MOVEQ #0,D0; MOVE.B D1,D0; MOVEQ #0,D1; MOVE.B D2,D1; RTS.
    case 0x1c086:am_word(r.d[0],r.d[0]&1U);if(!am_push(c,2,r.d[0]&0xffffU))return false;return am_call(c,0x4d7a6,0x1c092);
    case 0x1c092:am_word(r.d[7],r.d[0]);if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.pc=(r.d[7]&0xffU)==0U?0x1c0b4:0x1c09c;return true;
    case 0x1c09c:return am_call(c,0x4d9a2,0x1c0a2);
    case 0x1c0a2:r.pc=(r.d[7]&0xffU)!=1U?0x1c0b4:0x1c0aa;return true;
    case 0x1c0aa:r.d[0]=r.d[1]&0xffU;r.d[1]=r.d[2]&0xffU;return am_return(c);
    // LEA 5450(A5),A4; ANDI.W #1,D0; BEQ.W 1c0c4 / LEA 5460(A5),A4 / MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B 7(A4),D0; MOVE.B 6(A4),D1; RTS.
    case 0x1c0b4:r.a[4]=am_index(r.a[5],0x5450);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&0xffffU)==0U?0x1c0c4:0x1c0c0;return true;
    case 0x1c0c0:r.a[4]=am_index(r.a[5],0x5460);r.pc=0x1c0c4;return true;
    case 0x1c0c4:
        r.d[0]=0;r.d[1]=0;if(!pc4_get(c,r.a[4],7,1,value))return false;r.d[0]=value;if(!pc4_get(c,r.a[4],6,1,value))return false;r.d[1]=value;
        return am_return(c);
    // ---- 1ceb0 (C2 1ce98 .. fall-through): BTST.B #0,15(A6); BEQ.W 1cec0 / BSET.B #3,a7(A6) (falls into the C2 RTS 1cec0).
    case 0x1ceb0:if(!pc4_bit(c,r.a[6],0x15,0,0,old))return false;r.pc=old?0x1ceba:0x1cec0;return true;
    case 0x1ceba:if(!pc4_bit(c,r.a[6],0xa7,3,1,old))return false;r.pc=0x1cec0;return true;
    // ---- 1cec2 (BSR from 1ef7c and later units): CMPI.B #0,aa(A6); BEQ.W 1cef4 / BTST.B #3,a7(A6); BEQ.W 1cef4 / CMPI.B #1,aa(A6); BNE.W 1cee4 /
    // MOVEQ #1,D1; RTS / BCHG.B #0,15(A6); BCLR.B #3,a7(A6); MOVEQ #2,D1; RTS / MOVEQ #0,D1; RTS.
    case 0x1cec2:return pc4_byte_is(c,r.a[6],0xaa,0,0x1cef4,0x1cecc);
    case 0x1cecc:if(!pc4_bit(c,r.a[6],0xa7,3,0,old))return false;r.pc=old?0x1ced6:0x1cef4;return true;
    case 0x1ced6:return pc4_byte_is(c,r.a[6],0xaa,1,0x1cee0,0x1cee4);
    case 0x1cee0:r.d[1]=1;return am_return(c);
    case 0x1cee4:if(!pc4_bit(c,r.a[6],0x15,0,3,old) || !pc4_bit(c,r.a[6],0xa7,3,2,old))return false;r.d[1]=2;return am_return(c);
    case 0x1cef4:r.d[1]=0;return am_return(c);
    // ---- 1cfbe: MOVEQ #0,D7; MOVE.B 9e(A6),D7; ADD.W D7,D7 twice; MOVEA.L 1cfce(PC,D7.W),A0 (fixed ROM LONG table 1cfce + 4 x BYTE 9e); RTS.
    case 0x1cfbe:
        r.d[7]=0;if(!pc4_get(c,r.a[6],0x9e,1,value))return false;am_byte(r.d[7],value);am_word(r.d[7],r.d[7]+r.d[7]);am_word(r.d[7],r.d[7]+r.d[7]);
        if(!am_read(c,am_index(0x1cfce,r.d[7]&0xffffU),4,r.a[0]))return false;return am_return(c);
    // ---- 1d09e (BSR from 1efb8): BSR.W 1cfbe / MOVE.L (A0),D1 (falls into 1d0a4) / CLR.L 64(A6); BTST.B #2,D0; BEQ.W 1d0b4 / SUB.L D1,64(A6) /
    // BTST.B #3,D0; BEQ.W 1d0c0 / ADD.L D1,64(A6) / RTS.
    case 0x1d09e:return am_call(c,0x1cfbe,0x1d0a2);
    case 0x1d0a2:if(!am_read(c,r.a[0],4,r.d[1]))return false;r.pc=0x1d0a4;return true;
    case 0x1d0a4:if(!pc4_put(c,r.a[6],0x64,4,0))return false;r.pc=(r.d[0]&4U)==0U?0x1d0b4:0x1d0b0;return true;
    case 0x1d0b0:case 0x1d0bc:
        if(!pc4_get(c,r.a[6],0x64,4,value) || !pc4_put(c,r.a[6],0x64,4,r.pc==0x1d0b0U?value-r.d[1]:value+r.d[1]))return false;
        r.pc=r.pc==0x1d0b0U?0x1d0b4:0x1d0c0;return true;
    case 0x1d0b4:r.pc=(r.d[0]&8U)==0U?0x1d0c0:0x1d0bc;return true;
    // ---- 1eeea (branch from 1ef8c and the C2 / later states): CLR.B 7f(A6); LEA 1b6e0(PC),A0; BSR.W 1cab6 / MOVE.W #3f,88(A6); MOVE.B #1,a9(A6);
    // MOVE.B #2,9c(A6) (falls into 1ef08) / MOVE.L #1ef0e,(A6) (installed and entered at once).
    case 0x1eeea:if(!pc4_put(c,r.a[6],0x7f,1,0))return false;r.a[0]=0x1b6e0;return am_call(c,0x1cab6,0x1eef6);
    case 0x1eef6:
        if(!pc4_put(c,r.a[6],0x88,2,0x3f) || !pc4_put(c,r.a[6],0xa9,1,1) || !pc4_put(c,r.a[6],0x9c,1,2))return false;r.pc=0x1ef08;return true;
    case 0x1ef08:if(!pc4_put(c,r.a[6],0,4,0x1ef0e))return false;r.pc=0x1ef0e;return true;
    // ---- 1ef0e (node callback): ADDQ.B #1,92(A6); SCS.B D0 (the carry out of the ADDQ); OR.B D0,92(A6) (ff saturates); LSR.W 88(A6) (WORD >> 1);
    // BSR.W 1cfbe.
    case 0x1ef0e: {
        if(!pc4_get(c,r.a[6],0x92,1,value))return false;const bool carry=value==0xffU;
        if(!pc4_put(c,r.a[6],0x92,1,value+1U))return false;am_byte(r.d[0],carry?0xffU:0U);
        if(!pc4_get(c,r.a[6],0x92,1,value) || !pc4_put(c,r.a[6],0x92,1,value|(r.d[0]&0xffU)))return false;
        if(!pc4_get(c,r.a[6],0x88,2,value) || !pc4_put(c,r.a[6],0x88,2,value>>1))return false;
        return am_call(c,0x1cfbe,0x1ef20);
    }
    // MOVE.W 1c(A0),2c(A6); CMPI.B #8,6e(A6); BNE.W 1ef36 / MOVE.W 1e(A0),2c(A6).
    case 0x1ef20:if(!pc4_get(c,r.a[0],0x1c,2,value) || !pc4_put(c,r.a[6],0x2c,2,value))return false;return pc4_byte_is(c,r.a[6],0x6e,8,0x1ef30,0x1ef36);
    case 0x1ef30:if(!pc4_get(c,r.a[0],0x1e,2,value) || !pc4_put(c,r.a[6],0x2c,2,value))return false;r.pc=0x1ef36;return true;
    case 0x1ef36:case 0x21da0:return am_call(c,0x1cd98,r.pc+4U);                                         // BSR.W 1cd98.
    case 0x1ef3a:if(!pc4_bit(c,r.a[6],0x15,7,0,old))return false;r.pc=old?0x1ef44:0x1fae8;return true;   // BTST.B #7,15(A6); BEQ.W 1fae8.
    case 0x1ef44:r.pc=(r.d[0]&0x20U)==0U?0x1ef6c:0x1ef4c;return true;                                   // BTST.B #5,D0; BEQ.W 1ef6c (1ef4c is C8).
    case 0x1ef6c:r.pc=(r.d[0]&2U)!=0U?0x1f2a4:0x1ef74;return true;                                      // BTST.B #1,D0; BNE.W 1f2a4 (C7).
    case 0x1ef74:r.pc=(r.d[0]&0x80U)!=0U?0x1f1d8:0x1ef7c;return true;                                   // BTST.B #7,D0; BNE.W 1f1d8.
    case 0x1ef7c:return am_call(c,0x1cec2,0x1ef80);                                                       // BSR.W 1cec2.
    case 0x1ef80:r.pc=(r.d[1]&0xffU)==1U?0x1f070:0x1ef88;return true;                                   // CMPI.B #1,D1; BEQ.W 1f070 (C11).
    case 0x1ef88:r.pc=(r.d[1]&0xffU)==2U?0x1eeea:0x1ef90;return true;                                   // CMPI.B #2,D1; BEQ.W 1eeea.
    case 0x1ef90:if(!pc4_bit(c,r.a[6],0xa7,3,0,old))return false;r.pc=old?0x1efd6:0x1ef9a;return true;   // BTST.B #3,a7(A6); BNE.W 1efd6 (C11).
    // MOVE.W #c,D1; AND.W D0,D1 (C := Clear); BNE.W 1efb0 (1efa4 is C6).
    case 0x1ef9a:am_word(r.d[1],0xc);am_word(r.d[1],r.d[1]&r.d[0]);r.carry=AnimationCarryClear;r.pc=(r.d[1]&0xffffU)!=0U?0x1efb0:0x1efa4;return true;
    case 0x1efb0:return am_call(c,0x1ed34,0x1efb4);                                                       // BSR.W 1ed34 (the BSR keeps the C).
    case 0x1efb4:return pc4_carry(c,0x1efb8,0x1f126);                                                     // BCS.W 1f126.
    case 0x1efb8:return am_call(c,0x1d09e,0x1efbc);                                                       // BSR.W 1d09e.
    case 0x1efbc:return am_call(c,0x4bfc0,0x1efc2);                                                       // JSR 4bfc0.l.
    case 0x1efc2:return pc4_field_call(c,0x1e,0xce02,0x1efcc);                                           // MOVE.W 1e(A6),D0; JSR ce02.l.
    case 0x1efcc:return am_call(c,0x49fc6,0x1efd2);                                                       // JSR 49fc6.l.
    case 0x1efd2:r.pc=0x201a2;return true;                                                                 // BRA.W 201a2.
    // ---- 21c72 (the Set side of 21c6e BCC): JMP (A1) (contract decision 2: a handler of the list 21aee, else checked).
    case 0x21c72:
        for(unsigned int i=0;i<4U;++i)if(PC4_LIST_21AEE[i]==r.a[1]){r.pc=r.a[1];return true;}
        return am_error(c,"unsupported animation player c4 jump target");
    // ---- 21d60 (handler of the lists 21622 / 21aee): TST.B 9d(A6); BGT.W 21dd0 (C12; signed BYTE) / BSR.W 21bc6 / BCS.W 21f40 / BSR.W 21baa /
    // BCS.W 21f30 / LEA 1b7da(PC),A0; BSR.W 1cabe / MOVE.B #1,aa(A6); CLR.B a3(A6); MOVE.L #21d92,84(A6) (slot 84, entered at once) /
    // LEA 21b0a(PC),A0; BSR.W 215e6 / BCC.W 21da0 (21d9e JMP (A1) is C8).
    case 0x21d60:
        if(!pc4_get(c,r.a[6],0x9d,1,value))return false;r.pc=(value&0x80U)==0U && value!=0U?0x21dd0:0x21d68;return true;
    case 0x21d68:return am_call(c,0x21bc6,0x21d6c);
    case 0x21d6c:return pc4_carry(c,0x21d70,0x21f40);
    case 0x21d70:return am_call(c,0x21baa,0x21d74);
    case 0x21d74:return pc4_carry(c,0x21d78,0x21f30);
    case 0x21d78:r.a[0]=0x1b7da;return am_call(c,0x1cabe,0x21d80);
    case 0x21d80:
        if(!pc4_put(c,r.a[6],0xaa,1,1) || !pc4_put(c,r.a[6],0xa3,1,0) || !pc4_put(c,r.a[6],0x84,4,0x21d92))return false;r.pc=0x21d92;return true;
    case 0x21d92:r.a[0]=0x21b0a;return am_call(c,0x215e6,0x21d9a);
    case 0x21d9a:return pc4_carry(c,0x21da0,0x21d9e);
    // BTST.B #0 / #1 / #6 / #4,D0; BNE.W 223a0 (C13) / 223d6 (C13) / 21ffc / 2210c (C12) / BSR.W 21be6 / BCS.W 21f4c (C5) / BRA.W 2156a.
    case 0x21da4:r.pc=(r.d[0]&1U)!=0U?0x223a0:0x21dac;return true;
    case 0x21dac:r.pc=(r.d[0]&2U)!=0U?0x223d6:0x21db4;return true;
    case 0x21db4:r.pc=(r.d[0]&0x40U)!=0U?0x21ffc:0x21dbc;return true;
    case 0x21dbc:r.pc=(r.d[0]&0x10U)!=0U?0x2210c:0x21dc4;return true;
    case 0x21dc4:return am_call(c,0x21be6,0x21dc8);
    case 0x21dc8:return pc4_carry(c,0x21dcc,0x21f4c);
    case 0x21dcc:r.pc=0x2156a;return true;
    // ---- 4d9a2 (JSR from 1c09c): TST.B D0; BNE.W 4d9b0 / LEA 5cba(A5),A4; BRA.W 4d9b4 / LEA 5ce6(A5),A4 / MOVE.B 29(A4),D7; RTS.
    case 0x4d9a2:r.pc=(r.d[0]&0xffU)!=0U?0x4d9b0:0x4d9a8;return true;
    case 0x4d9a8:r.a[4]=am_index(r.a[5],0x5cba);r.pc=0x4d9b4;return true;
    case 0x4d9b0:case 0x4da12:r.a[4]=am_index(r.a[5],0x5ce6);r.pc=r.pc==0x4d9b0U?0x4d9b4:0x4da16;return true;
    case 0x4d9b4:if(!pc4_get(c,r.a[4],0x29,1,value))return false;am_byte(r.d[7],value);return am_return(c);
    // ---- 4da08 (JSR from 1c052): LEA 5cba(A5),A4; TST.B D0; BEQ.W 4da16 / LEA 5ce6(A5),A4 / TST.W (A4); BNE.W 4da20 / MOVEQ #0,D7; RTS (MOVEQ
    // clears C) / MOVE.W 20(A4),D7; ORI.B #1,CCR; RTS.
    case 0x4da08:r.a[4]=am_index(r.a[5],0x5cba);r.pc=(r.d[0]&0xffU)==0U?0x4da16:0x4da12;return true;
    case 0x4da16:if(!am_read(c,r.a[4],2,value))return false;r.pc=value!=0U?0x4da20:0x4da1c;return true;
    case 0x4da1c:r.d[7]=0;return pc4_return_carry(c,AnimationCarryClear);
    case 0x4da20:if(!pc4_get(c,r.a[4],0x20,2,value))return false;am_word(r.d[7],value);return pc4_return_carry(c,AnimationCarrySet);
    // ---- 4e4e2 (fall-through of C1 4e4da): three numbers through 35a2: WORD 7c / 82 / 80(A6) at D1 = 320 (JSR, JSR, JMP 35a2.l).
    case 0x4e4e2:if(!pc4_digits(c,0x7c,0x10,3))return false;return am_call(c,0x35a2,0x4e4fe);
    case 0x4e4fe:if(!pc4_digits(c,0x82,2,4))return false;return am_call(c,0x35a2,0x4e51a);
    case 0x4e51a:if(!pc4_digits(c,0x80,6,3))return false;r.pc=0x35a2;return true;
    // ---- 4e538 / 4e564 (JSR from 4e79e / 4e796 and others): MOVE.W 7c(A6),D0; CMPI.W #0,76(A6); BNE.W 4e54e / 4e57a.
    case 0x4e538:case 0x4e564:
        if(!pc4_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[0],value);
        return pc4_word_zero(c,0x76,r.pc==0x4e538U?0x4e546U:0x4e572U,r.pc==0x4e538U?0x4e54eU:0x4e57aU);   // 4e572 is C6.
    case 0x4e546:am_word(r.d[0],r.d[0]+0x20U);r.pc=0x4e552;return true;                                 // ADDI.W #20,D0; BRA.W 4e552.
    case 0x4e54e:case 0x4e57a:am_word(r.d[0],r.d[0]+0x80U);r.pc=r.pc+4U;return true;                    // ADDI.W #80,D0.
    case 0x4e552:am_word(r.d[1],0x320);am_word(r.d[2],0xb);am_word(r.d[3],2);r.pc=0x35a2;return true;   // MOVE.W #320,D1; #b,D2; #2,D3; JMP 35a2.l.
    case 0x4e57e:r.a[1]=0xe84c8;r.pc=0x3918;return true;                                                  // LEA e84c8.l,A1; JMP 3918.l.
    // ---- 4e758 (the 4e732 state after C1 4e74c): JSR ca32.l / SCS.B D0 (C of ca32); CMP.B 9a(A6),D0; BEQ.W 4e7a2 / MOVE.B D0,9a(A6); BEQ.W 4e79e /
    // MOVE.W 76(A6),D0; JSR 4a974.l / BEQ.W 4e786 (Z of 4a974, decision 3) / LEA 4e35e(PC),A0; BRA.W 4e78a / LEA 4e33a(PC),A0 / TST.B a1(A6);
    // BEQ.W 4e796 / LEA 4e34c(PC),A0 / JSR 4e564(PC) / BRA.W 4e7a2 / JSR 4e538(PC) (returns to C1 4e7a2).
    case 0x4e758:return am_call(c,0xca32,0x4e75e);
    // SCS.B D0 reads the known C; the CMP.B that follows sets C again, which no block reads: C is left Unknown (contract decision 5).
    case 0x4e75e:if(!pc4_scs(c) || !pc4_get(c,r.a[6],0x9a,1,value))return false;r.carry=AnimationCarryUnknown;r.pc=(r.d[0]&0xffU)==value?0x4e7a2:0x4e768;return true;
    case 0x4e768:if(!pc4_put(c,r.a[6],0x9a,1,r.d[0]))return false;r.pc=(r.d[0]&0xffU)==0U?0x4e79e:0x4e770;return true;
    case 0x4e770:return pc4_field_call(c,0x76,0x4a974,0x4e77a);
    // BEQ.W 4e786 on the Z of the TST.B (A0); RTS that ends 4a974 (4a9b0 / 4a9c6; contract decision 3, controller C1 rule): A0 is 10fdb0 / 10fdb1 or
    // 100004 / 100005 and the RTS does not change that BYTE, so it is read again; any other A0 is the checked flag-source error.
    case 0x4e77a:
        if(r.a[0]!=0x10fdb0U && r.a[0]!=0x10fdb1U && r.a[0]!=0x100004U && r.a[0]!=0x100005U)return am_error(c,"unsupported animation player c4 flag source");
        if(!am_read(c,r.a[0],1,value))return false;r.pc=value==0U?0x4e786:0x4e77e;return true;
    case 0x4e77e:r.a[0]=0x4e35e;r.pc=0x4e78a;return true;
    case 0x4e786:r.a[0]=0x4e33a;r.pc=0x4e78a;return true;
    case 0x4e78a:return pc4_byte_is(c,r.a[6],0xa1,0,0x4e796,0x4e792);
    case 0x4e792:r.a[0]=0x4e34c;r.pc=0x4e796;return true;
    case 0x4e796:return am_call(c,0x4e564,0x4e79a);
    case 0x4e79a:r.pc=0x4e7a2;return true;
    case 0x4e79e:return am_call(c,0x4e538,0x4e7a2);
    // ---- 4e8e6 (the straight-line continuation of C1 4e8e0 and the BCC.B 4e8e6 of C1 4e958, contract decision 1): MOVE.W 76(A6),D0; JSR b7a28.l
    // (returns to C1 4e8f0).
    case 0x4e8e6:return pc4_field_call(c,0x76,0xb7a28,0x4e8f0);
    // ---- 4e962 (4e94e state, BYTE 9a set): MOVE.W 76(A6),D0; JSR 1be3a.l / SCS.B D0 (C of 1be3a); CMP.B a1(A6),D0; BEQ.W 4e97a / CLR.B 9a(A6) /
    // MOVE.B D0,a1(A6) (falls into C1 4e97e).
    case 0x4e962:return pc4_field_call(c,0x76,0x1be3a,0x4e96c);
    case 0x4e96c:if(!pc4_scs(c) || !pc4_get(c,r.a[6],0xa1,1,value))return false;r.carry=AnimationCarryUnknown;r.pc=(r.d[0]&0xffU)==value?0x4e97a:0x4e976;return true;
    case 0x4e976:if(!pc4_put(c,r.a[6],0x9a,1,0))return false;r.pc=0x4e97a;return true;
    case 0x4e97a:if(!pc4_put(c,r.a[6],0xa1,1,r.d[0]))return false;r.pc=0x4e97e;return true;
    // ---- 4e986 (after C1 4e97e, D0.B = BYTE 5d1f(A5)): CMP.B 9a(A6),D0; BEQ.W 4ea38 / LEA 4e47a(PC),A0; JSR 8da2.l / BSR.W 4e4da / TST.B a1(A6);
    // BEQ.W 4e9b0 / LEA 4e34c(PC),A0; BSR.W 4e564 / BRA.W 4eb50.
    case 0x4e986:return pc4_byte_is(c,r.a[6],0x9a,r.d[0]&0xffU,0x4ea38,0x4e98e);
    case 0x4e98e:r.a[0]=0x4e47a;return am_call(c,0x8da2,0x4e998);
    case 0x4e998:return am_call(c,0x4e4da,0x4e99c);
    case 0x4e99c:return pc4_byte_is(c,r.a[6],0xa1,0,0x4e9b0,0x4e9a4);
    case 0x4e9a4:r.a[0]=0x4e34c;return am_call(c,0x4e564,0x4e9ac);
    case 0x4e9ac:r.pc=0x4eb50;return true;
    // LEA 4e3aa(PC),A0; TST.W 76(A6); BEQ.W 4e9c0 / LEA 4e3bc(PC),A0 / MOVE.W 82(A6),D0; JSR 3902.l / MOVE.W 84(A6),D0; LEA 4e3ce(PC),A0; JSR 3902.l.
    case 0x4e9b0:r.a[0]=0x4e3aa;return pc4_word_zero(c,0x76,0x4e9c0,0x4e9bc);
    case 0x4e9bc:r.a[0]=0x4e3bc;r.pc=0x4e9c0;return true;
    case 0x4e9c0:return pc4_field_call(c,0x82,0x3902,0x4e9ca);
    case 0x4e9ca:r.a[0]=0x4e3ce;return pc4_field_call(c,0x84,0x3902,0x4e9d8);
    // MOVEQ #0,D7; MOVE.W 82(A6),D0; ADDI.W #22,D0; MOVE.W #103,D1; MOVE.B 99(A6),D7; BPL.W 4e9fc (N of the BYTE).
    case 0x4e9d8:
        r.d[7]=0;if(!pc4_get(c,r.a[6],0x82,2,value))return false;am_word(r.d[0],value+0x22U);am_word(r.d[1],0x103);
        if(!pc4_get(c,r.a[6],0x99,1,value))return false;am_byte(r.d[7],value);r.pc=(value&0x80U)==0U?0x4e9fc:0x4e9ee;return true;
    case 0x4e9ee:case 0x4eabe:
        if(r.pc==0x4eabeU && !pc4_bit(c,r.a[6],0x9d,0,2,old))return false;                               // 4eabe: BCLR.B #0,9d(A6) first.
        r.a[0]=0x4e3f1;return am_call(c,0x3902,r.pc==0x4e9eeU?0x4e9f8U:0x4eaceU);                        // LEA 4e3f1(PC),A0; JSR 3902.l.
    case 0x4e9f8:r.pc=0x4ea14;return true;                                                                 // BRA.W 4ea14.
    case 0x4e9fc:r.pc=(r.d[7]&0xffU)<0x10U?0x4ea08:0x4ea04;return true;                                // CMPI.B #10,D7; BCS.W 4ea08 (unsigned).
    case 0x4ea04:am_word(r.d[0],r.d[0]-0x20U);r.pc=0x4ea08;return true;                                 // SUBI.W #20,D0.
    case 0x4ea08:am_byte(r.d[3],0);am_word(r.d[4],2);return am_call(c,0x3786,0x4ea14);                // CLR.B D3; MOVE.W #2,D4; JSR 3786.l.
    case 0x4ea14:return am_call(c,0x4ee7a,0x4ea18);                                                       // BSR.W 4ee7a.
    case 0x4ea18:if(!pc4_get(c,r.a[6],0x78,4,r.a[0]))return false;r.d[2]=0;return am_call(c,0x1bf94,0x4ea24);   // MOVEA.L 78(A6),A0; CLR.L D2; JSR 1bf94.
    // LSL.W #2,D2; LEA 4e4a2(PC),A0; MOVEA.L (A0,D2.W),A0 (fixed ROM LONG table 4e4a2 + sext(D2.W)); MOVE.W 82(A6),D0; JSR 362a.l.
    case 0x4ea24:
        am_word(r.d[2],r.d[2]<<2);if(!am_read(c,am_index(0x4e4a2,r.d[2]&0xffffU),4,r.a[0]))return false;return pc4_field_call(c,0x82,0x362a,0x4ea38);
    case 0x4ea38:return pc4_byte_is(c,r.a[6],0xa1,0,0x4ea40,0x4eb50);                                    // TST.B a1(A6); BNE.W 4eb50.
    // MOVE.W 7e(A6),D0; MOVE.W #3,D1; LEA 5e1c(A5),A0; TST.W 76(A6); BNE.W 4ea5c / ADDI.W #20,D0; LEA 5e14(A5),A0.
    case 0x4ea40:
        if(!pc4_get(c,r.a[6],0x7e,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],3);r.a[0]=am_index(r.a[5],0x5e1c);
        return pc4_word_zero(c,0x76,0x4ea54,0x4ea5c);
    case 0x4ea54:am_word(r.d[0],r.d[0]+0x20U);r.a[0]=am_index(r.a[5],0x5e14);r.pc=0x4ea5c;return true;
    // MOVE.B (A0),D3; ANDI.B #f0,D3; MOVE.W #7,D4; JSR 36ba.l.
    case 0x4ea5c:if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[3],value&0xf0U);am_word(r.d[4],7);return am_call(c,0x36ba,0x4ea6c);
    case 0x4ea6c:return pc4_field_call(c,0x76,0x1c052,0x4ea76);                                         // MOVE.W 76(A6),D0; JSR 1c052.l.
    // MOVE.W 84(A6),D0; ADDI.W #21,D0; MOVE.W #203,D1; CMP.W 86(A6),D7; BEQ.W 4eaa4.
    case 0x4ea76:
        if(!pc4_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[0],value+0x21U);am_word(r.d[1],0x203);
        if(!pc4_get(c,r.a[6],0x86,2,value))return false;r.pc=(r.d[7]&0xffffU)==value?0x4eaa4:0x4ea8a;return true;
    case 0x4ea8a:if(!pc4_put(c,r.a[6],0x86,2,r.d[7]))return false;r.pc=(r.d[7]&0x8000U)!=0U?0x4eab6:0x4ea92;return true;  // MOVE.W D7,86(A6); BMI.W 4eab6.
    case 0x4ea92:if(!pc4_bit(c,r.a[6],0x9d,0,3,old))return false;r.pc=old?0x4eaa0:0x4ea9c;return true;   // BCHG.B #0,9d(A6); BNE.W 4eaa0.
    case 0x4ea9c:am_word(r.d[1],0x303);r.pc=0x4eaa0;return true;                                        // MOVE.W #303,D1.
    case 0x4eaa0:r.pc=0x4eab6;return true;                                                                 // BRA.W 4eab6.
    case 0x4eaa4:if(!pc4_bit(c,r.a[6],0x9d,0,2,old))return false;r.pc=old?0x4eab6:0x4eaae;return true;   // BCLR.B #0,9d(A6); BNE.W 4eab6.
    case 0x4eaae:return pc4_byte_is(c,r.a[6],0x9a,0,0x4eab6,0x4eadc);                                    // TST.B 9a(A6); BNE.W 4eadc.
    case 0x4eab6:r.pc=(r.d[7]&0xffffU)!=0xffffU?0x4ead2:0x4eabe;return true;                            // CMPI.W #ffff,D7; BNE.W 4ead2.
    case 0x4eace:r.pc=0x4eadc;return true;                                                                 // BRA.W 4eadc.
    case 0x4ead2:am_byte(r.d[3],0);r.d[4]=3;return am_call(c,0x371e,0x4eadc);                           // CLR.B D3; MOVEQ #3,D4; JSR 371e.l.
    case 0x4eadc:return pc4_field_call(c,0x76,0x1c086,0x4eae6);                                         // MOVE.W 76(A6),D0; JSR 1c086.l.
    // MOVE.W D0,-(A7); CMP.B 9f(A6),D1; BNE.W 4eafc / TST.B 9a(A6); BEQ.W 4eafc / BRA.W 4eb18.
    case 0x4eae6:if(!am_push(c,2,r.d[0]&0xffffU))return false;return pc4_byte_is(c,r.a[6],0x9f,r.d[1]&0xffU,0x4eaf0,0x4eafc);
    case 0x4eaf0:return pc4_byte_is(c,r.a[6],0x9a,0,0x4eafc,0x4eaf8);
    case 0x4eaf8:r.pc=0x4eb18;return true;
    // MOVE.B D1,9f(A6); LEA 4e43e(PC),A0; LSL.W #2,D1; MOVEA.L (A0,D1.W),A0 (fixed ROM LONG table 4e43e + sext(D1.W)); MOVE.W 84(A6),D0;
    // ADDI.W #80,D0; JSR 3902.l.
    case 0x4eafc:
        if(!pc4_put(c,r.a[6],0x9f,1,r.d[1]))return false;am_word(r.d[1],r.d[1]<<2);
        if(!am_read(c,am_index(0x4e43e,r.d[1]&0xffffU),4,r.a[0]) || !pc4_get(c,r.a[6],0x84,2,value))return false;
        am_word(r.d[0],value+0x80U);return am_call(c,0x3902,0x4eb18);
    // MOVE.W (A7)+,D7; CMP.B 9e(A6),D7; BNE.W 4eb2a / TST.B 9a(A6); BNE.W 4eb44.
    case 0x4eb18:if(!am_pop(c,2,value))return false;am_word(r.d[7],value);return pc4_byte_is(c,r.a[6],0x9e,r.d[7]&0xffU,0x4eb22,0x4eb2a);
    case 0x4eb22:return pc4_byte_is(c,r.a[6],0x9a,0,0x4eb2a,0x4eb44);
    // MOVE.B D7,9e(A6); MOVE.W 84(A6),D0; ADDI.W #a1,D0; MOVE.W #203,D1; CLR.B D3; MOVEQ #2,D4; JSR 371e.l.
    case 0x4eb2a:
        if(!pc4_put(c,r.a[6],0x9e,1,r.d[7]) || !pc4_get(c,r.a[6],0x84,2,value))return false;
        am_word(r.d[0],value+0xa1U);am_word(r.d[1],0x203);am_byte(r.d[3],0);r.d[4]=2;return am_call(c,0x371e,0x4eb44);
    case 0x4eb44:return am_call(c,0x4eef4,0x4eb48);                                                       // BSR.W 4eef4.
    case 0x4eb48:return am_call(c,0x4f22c,0x4eb4c);                                                       // BSR.W 4f22c.
    case 0x4eb4c:return am_call(c,0x4f13c,0x4eb50);                                                       // BSR.W 4f13c (returns to C1 4eb50).
    // ---- 4ee7a (BSR from 4ea14, BNE from 4f14c): MOVE.W #0,88 / 8a / 8c / 8e / 90 / 94(A6); BRA.W 4f08a.
    case 0x4ee7a:
        if(!pc4_put(c,r.a[6],0x88,2,0) || !pc4_put(c,r.a[6],0x8a,2,0) || !pc4_put(c,r.a[6],0x8c,2,0) || !pc4_put(c,r.a[6],0x8e,2,0) ||
           !pc4_put(c,r.a[6],0x90,2,0) || !pc4_put(c,r.a[6],0x94,2,0))return false;
        r.pc=0x4f08a;return true;
    // ---- 4eef4: MOVE.W 76(A6),D0; JSR 4d7a6.l / CMPI.B #0,D0; BNE.W 4ef08 (C13) / RTS.
    case 0x4eef4:return pc4_field_call(c,0x76,0x4d7a6,0x4eefe);
    case 0x4eefe:r.pc=(r.d[0]&0xffU)!=0U?0x4ef08:0x4ef06;return true;
    // ---- 4f118 (BSR from 4f142): MOVE.W #28,D6; CLR.L D0; MOVE.W 94(A6),D0; BNE.W 4f130 / MOVE.W #0,D7; ANDI.B #fe,CCR; RTS / DIVU.W 92(A6),D0;
    // MOVE.W D0,D7; ORI.B #1,CCR; RTS.
    case 0x4f118:am_word(r.d[6],0x28);r.d[0]=0;if(!pc4_get(c,r.a[6],0x94,2,value))return false;r.d[0]=value;r.pc=value!=0U?0x4f130:0x4f126;return true;
    case 0x4f126:am_word(r.d[7],0);return pc4_return_carry(c,AnimationCarryClear);
    case 0x4f130:if(!pc4_get(c,r.a[6],0x92,2,value) || !pc4_divu(c,r.d[0],value))return false;am_word(r.d[7],r.d[0]);return pc4_return_carry(c,AnimationCarrySet);
    // ---- 4f13c (BSR from 4eb4c): MOVE.W 76(A6),D0; MOVEQ #0,D1; BSR.B 4f118 / BCS.W 4f152 / TST.W 8c(A6); BNE.W 4ee7a / RTS.
    case 0x4f13c:if(!pc4_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.d[1]=0;return am_call(c,0x4f118,0x4f144);
    case 0x4f144:return pc4_carry(c,0x4f148,0x4f152);
    case 0x4f148:return pc4_word_zero(c,0x8c,0x4f150,0x4ee7a);
    // TST.W D6; BNE.W 4f160 / MOVE.W #0,D7; BRA.W 4f174 / CMP.W D6,D7; BCS.W 4f16e (unsigned) / MOVE.W #2800,D7; BRA.W 4f174 / MULU.W #2800,D7;
    // DIVU.W D6,D7.
    case 0x4f152:r.pc=(r.d[6]&0xffffU)!=0U?0x4f160:0x4f158;return true;
    case 0x4f158:case 0x4f166:am_word(r.d[7],r.pc==0x4f158U?0U:0x2800U);r.pc=0x4f174;return true;
    case 0x4f160:r.pc=(r.d[7]&0xffffU)<(r.d[6]&0xffffU)?0x4f16e:0x4f166;return true;
    case 0x4f16e:r.d[7]=(r.d[7]&0xffffU)*0x2800U;if(!pc4_divu(c,r.d[7],r.d[6]))return false;r.pc=0x4f174;return true;
    // TST.B 9a(A6) (flags not read); MOVE.W D7,8e(A6); MOVE.W D7,8c(A6); BRA.W 4f1ac.
    case 0x4f174:
        if(!pc4_get(c,r.a[6],0x9a,1,value) || !pc4_put(c,r.a[6],0x8e,2,r.d[7]) || !pc4_put(c,r.a[6],0x8c,2,r.d[7]))return false;r.pc=0x4f1ac;return true;
    // ---- 4f1ac: MOVE.W 80(A6),D0; SWAP D0; MOVE.W #8440,D0; MOVE.W 8e(A6),D7; MOVE.W 8c(A6),D1; BPL.W 4f1c4 / MOVEQ #0,D1.
    case 0x4f1ac:
        if(!pc4_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[0],value);am_swap(r.d[0]);am_word(r.d[0],0x8440);
        if(!pc4_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[7],value);if(!pc4_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[1],value);
        r.pc=(value&0x8000U)==0U?0x4f1c4:0x4f1c2;return true;
    case 0x4f1c2:r.d[1]=0;r.pc=0x4f1c4;return true;
    // MOVE.L D0,3c0000.l; ADDI.L #200000,D0 (LONG, carry out lost); MOVE.W #5,D2; MOVE.B #49,D0.
    case 0x4f1c4:pc4_video(c,r.d[0]);r.d[0]+=0x200000U;am_word(r.d[2],5);am_byte(r.d[0],0x49);r.pc=0x4f1d8;return true;
    // SUBI.W #800,D1; BMI.W 4f1f4 (N of the WORD result).
    case 0x4f1d8:am_word(r.d[1],r.d[1]-0x800U);r.pc=(r.d[1]&0x8000U)!=0U?0x4f1f4:0x4f1e0;return true;
    // MOVE.L D0,3c0000.l; ADDI.L #200000,D0; SUBQ.W #1,D2; BEQ.W 4f220 (4f1e0: falls into BRA.B 4f1d8 at 4f1f2; 4f210: BNE.B 4f210).
    case 0x4f1e0:case 0x4f210:
        pc4_video(c,r.d[0]);r.d[0]+=0x200000U;am_word(r.d[2],r.d[2]-1U);
        r.pc=(r.d[2]&0xffffU)==0U?0x4f220:(r.pc==0x4f1e0U?0x4f1f2U:0x4f210U);return true;
    case 0x4f1f2:r.pc=0x4f1d8;return true;
    // MOVE.W D1,D7; ASR.W #8,D7 (arithmetic WORD shift); ADD.B D7,D0; MOVE.L D0,3c0000.l; ADDI.L #200000,D0; SUBQ.W #1,D2; BEQ.W 4f220.
    case 0x4f1f4: {
        am_word(r.d[7],r.d[1]);const std::uint32_t w=r.d[7]&0xffffU;am_word(r.d[7],(w>>8)|((w&0x8000U)!=0U?0xff00U:0U));
        am_byte(r.d[0],r.d[0]+r.d[7]);pc4_video(c,r.d[0]);r.d[0]+=0x200000U;am_word(r.d[2],r.d[2]-1U);
        r.pc=(r.d[2]&0xffffU)==0U?0x4f220:0x4f20c;return true;
    }
    case 0x4f20c:am_byte(r.d[0],0x41);r.pc=0x4f210;return true;                                         // MOVE.B #41,D0.
    case 0x4f220:am_byte(r.d[0],0x4a);pc4_video(c,r.d[0]);return am_return(c);                           // MOVE.B #4a,D0; MOVE.L D0,3c0000.l; RTS.
    // ---- 4f22c (BSR from 4eb48, JSR from C1 4e8f8): LEA 10dddc.l,A0; TST.W 76(A6); BEQ.W 4f240 / LEA 10dde4.l,A0 / MOVE.W (A0),D7; MOVEQ #e,D6;
    // CMP.W D6,D7; BCS.W 4f24c (unsigned) / MOVE.W D6,D7 / CMP.B a0(A6),D7; BNE.W 4f25e / TST.B 9a(A6); BEQ.W 4f25e / RTS.
    case 0x4f22c:r.a[0]=0x10dddc;return pc4_word_zero(c,0x76,0x4f240,0x4f23a);
    case 0x4f23a:r.a[0]=0x10dde4;r.pc=0x4f240;return true;
    case 0x4f240:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[7],value);r.d[6]=0xe;r.pc=value<0xeU?0x4f24c:0x4f24a;return true;
    case 0x4f24a:am_word(r.d[7],r.d[6]);r.pc=0x4f24c;return true;
    case 0x4f24c:return pc4_byte_is(c,r.a[6],0xa0,r.d[7]&0xffU,0x4f254,0x4f25e);
    case 0x4f254:return pc4_byte_is(c,r.a[6],0x9a,0,0x4f25e,0x4f25c);
    // MOVE.B D7,a0(A6); SUB.W D7,D6; TST.W 76(A6); BNE.W 4f278 / MOVE.W #707c,D0; MOVE.W #20,D1; BRA.W 4f280 / MOVE.W #749c,D0; MOVE.W #ffe0,D1.
    case 0x4f25e:if(!pc4_put(c,r.a[6],0xa0,1,r.d[7]))return false;am_word(r.d[6],r.d[6]-r.d[7]);return pc4_word_zero(c,0x76,0x4f26c,0x4f278);
    case 0x4f26c:am_word(r.d[0],0x707c);am_word(r.d[1],0x20);r.pc=0x4f280;return true;
    case 0x4f278:am_word(r.d[0],0x749c);am_word(r.d[1],0xffe0);r.pc=0x4f280;return true;
    // SWAP D0; SWAP D1; CLR.W D1; MOVE.W #310,D0; MOVEQ #e,D3.
    case 0x4f280:am_swap(r.d[0]);am_swap(r.d[1]);am_word(r.d[1],0);am_word(r.d[0],0x310);r.d[3]=0xe;r.pc=0x4f28c;return true;
    // CMPI.W #0,D7 / D6; BEQ.W 4f2a0 / 4f2b8; MOVE.L D0,3c0000.l; ADD.L D1,D0; SUBQ.W #1,D7 / D6; BRA.B 4f28c / 4f2a4.
    case 0x4f28c:r.pc=(r.d[7]&0xffffU)==0U?0x4f2a0:0x4f294;return true;
    case 0x4f2a4:r.pc=(r.d[6]&0xffffU)==0U?0x4f2b8:0x4f2ac;return true;
    case 0x4f294:pc4_video(c,r.d[0]);r.d[0]+=r.d[1];am_word(r.d[7],r.d[7]-1U);r.pc=0x4f28c;return true;
    case 0x4f2ac:pc4_video(c,r.d[0]);r.d[0]+=r.d[1];am_word(r.d[6],r.d[6]-1U);r.pc=0x4f2a4;return true;
    case 0x4f2a0:am_word(r.d[0],0x320);r.pc=0x4f2a4;return true;                                        // MOVE.W #320,D0.
    default:return am_error(c,"unsupported animation player c4 PC");
    }
}
}
