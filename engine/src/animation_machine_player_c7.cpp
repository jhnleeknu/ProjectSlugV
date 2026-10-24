#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc7_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc7_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR / BCHG #bit,<memory BYTE> (bit modulo 8). op 0 tests, 1 sets, 2 clears, 3 changes; old is the bit before (Z = old is 0).
bool pc7_bit(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    std::uint32_t next=value&~mask;
    if(op==1U || (op==3U && !old))next=value|mask;
    return am_write(c,address,1,next);
}
// BTST #bit,d16(A6); BEQ.W zero_pc (the bit clear) / other_pc.
bool pc7_field_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t other_pc) {
    bool old=false;if(!pc7_bit(c,am_index(c.s.a[6],displacement),bit,0,old))return false;
    c.s.pc=old?other_pc:zero_pc;return true;
}
// BTST #bit,D0 (a register operand: the LONG bit); BEQ.W zero_pc / other_pc.
void pc7_input_bit(AnimationMachineState& r,unsigned int bit,std::uint32_t zero_pc,std::uint32_t other_pc) {
    r.pc=(r.d[0]&(1U<<bit))==0U?zero_pc:other_pc;
}
// TST.B / CMPI.B #0,d16(A6); BEQ.W zero_pc / other_pc (BNE: the same with the targets swapped by the caller).
bool pc7_byte_zero(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc7_get(c,base,displacement,1,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc7_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c7 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ANDI.B #fe,CCR / ORI.B #1,CCR; RTS: the C returned to the caller.
bool pc7_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// MOVE.W d16(A6),D0 (D0 bits 16..31 kept); JSR target.
bool pc7_field_call(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc7_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MOVE.W #k,D0 (bits 16..31 kept); JSR target.
bool pc7_word_call(AnimationMachineContext& c,std::uint32_t k,std::uint32_t target,std::uint32_t return_pc) {
    am_word(c.s.d[0],k);return am_call(c,target,return_pc);
}
// MOVE.W #202,D0; MOVE.B #0,D1; JSR 8ebe.l (24fec / 25276 / 253f4).
bool pc7_8ebe_call(AnimationMachineContext& c,std::uint32_t return_pc) {
    am_word(c.s.d[0],0x202);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.L #v,(A6): the node callback LONG.
bool pc7_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc7_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #21602,84(A6); MOVE.B #0,9c(A6); MOVE.B #1,aa(A6); CLR.W 7a(A6) (the common part of 1f2ac / 1f546 / 1f6ae / 1f782).
bool pc7_slot(AnimationMachineContext& c) {
    const std::uint32_t a6=c.s.a[6];
    return pc7_put(c,a6,0x84,4,0x21602) && pc7_put(c,a6,0x9c,1,0) && pc7_put(c,a6,0xaa,1,1) && pc7_put(c,a6,0x7a,2,0);
}
// CLR.L 64(A6) (1f2ac / 1f6ae) and the slot part, MOVE.B #2,a9(A6).
bool pc7_slot_state(AnimationMachineContext& c,bool clear64) {
    if(clear64 && !pc7_put(c,c.s.a[6],0x64,4,0))return false;
    return pc7_slot(c) && pc7_put(c,c.s.a[6],0xa9,1,2);
}
// ANDI.W #f,D0; SUBQ.W #7,D0; ADD.W D0,d16(A6) (WORD; D0 bits 16..31 kept, the carry out of the field lost).
bool pc7_jitter(AnimationMachineContext& c,std::uint32_t displacement) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    am_word(r.d[0],r.d[0]&0xfU);am_word(r.d[0],r.d[0]-7U);
    if(!pc7_get(c,r.a[6],displacement,2,value))return false;return pc7_put(c,r.a[6],displacement,2,value+r.d[0]);
}
// MOVE.W 42(A6),D0; CMPI.W #140,D0; BCS.W in_pc (unsigned WORD below 140) / JMP 2a00.l (25172 / 2545e).
bool pc7_x_bound(AnimationMachineContext& c,std::uint32_t in_pc,std::uint32_t out_pc) {
    std::uint32_t value=0;if(!pc7_get(c,c.s.a[6],0x42,2,value))return false;am_word(c.s.d[0],value);
    c.s.pc=(c.s.d[0]&0xffffU)<0x140U?in_pc:out_pc;return true;
}
// MOVE.W 46(A6),D0; SUBI.W #100,D0; CMPI.W #100,D0; BCS.W in_pc (unsigned WORD) / JMP 2a00.l (25184 / 25470).
bool pc7_y_bound(AnimationMachineContext& c,std::uint32_t in_pc,std::uint32_t out_pc) {
    std::uint32_t value=0;if(!pc7_get(c,c.s.a[6],0x46,2,value))return false;am_word(c.s.d[0],value);am_word(c.s.d[0],c.s.d[0]-0x100U);
    c.s.pc=(c.s.d[0]&0xffffU)<0x100U?in_pc:out_pc;return true;
}
// MOVE.W (A1)+,x; MOVE.W (A1)+,y; MOVE.W (A1)+,z (WORDs, bits 16..31 kept; A1 += 6).
bool pc7_triple(AnimationMachineContext& c,std::uint32_t& x,std::uint32_t& y,std::uint32_t& z) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,r.a[1],2,value))return false;am_word(x,value);r.a[1]+=2U;
    if(!am_read(c,r.a[1],2,value))return false;am_word(y,value);r.a[1]+=2U;
    if(!am_read(c,r.a[1],2,value))return false;am_word(z,value);r.a[1]+=2U;
    return true;
}
// NEG.B x; ADDI.B #80,x; NEG.W y (the mirrored direction: BYTE and WORD, carries lost, upper bits kept).
void pc7_mirror(std::uint32_t& x,std::uint32_t& y) {
    am_byte(x,0U-(x&0xffU));am_byte(x,x+0x80U);am_word(y,0U-(y&0xffffU));
}
// MOVE.L A0,-(A7); MOVEA.L child,A0; MOVE.W #k,D0 (bits 16..31 kept); MOVEA.L #100bf4,A1; JSR 2986.l.
bool pc7_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t k,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;
    if(!am_push(c,4,r.a[0]))return false;r.a[0]=child;am_word(r.d[0],k);r.a[1]=0x100bf4;return am_call(c,0x2986,return_pc);
}
// ADD.W D0,D0 twice (WORD, bits 16..31 kept).
void pc7_times4(std::uint32_t& reg) {
    am_word(reg,reg+reg);am_word(reg,reg+reg);
}
// DIVU.W #3,D0 (contract decision 4, the C4 rule): the LONG D0 divided by the unsigned WORD 3; a quotient above ffff is the overflow (V, D0 unchanged),
// else D0 := remainder WORD << 16 | quotient WORD.  The divisor is the immediate 3 (no zero divide); the flags are not read (SWAP follows).
void pc7_divu3(std::uint32_t& reg) {
    const std::uint32_t quotient=reg/3U;
    if(quotient>0xffffU)return;
    reg=((reg%3U)<<16)|quotient;
}
// MULS.W D7,D0: the signed low WORDs, the signed 32-bit product in D0 (|product| <= 2^30: no overflow in std::int32_t).
std::uint32_t pc7_muls(std::uint32_t a,std::uint32_t b) {
    const std::int32_t x=static_cast<std::int32_t>(a&0x7fffU)-static_cast<std::int32_t>(a&0x8000U);
    const std::int32_t y=static_cast<std::int32_t>(b&0x7fffU)-static_cast<std::int32_t>(b&0x8000U);
    return static_cast<std::uint32_t>(x*y);                                                             // modulo 2^32 (well defined).
}
// MOVE.B d16(A6),Dn; EXT.W Dn: the BYTE sign-extended to the WORD (Dn bits 16..31 kept by the caller's am_word).
std::uint32_t pc7_ext(std::uint32_t byte) {
    return (byte&0x80U)!=0U?(byte|0xff00U):(byte&0xffU);
}
// JMP 2529c(PC,D0.W) (contract decision 2): the BRA.W table 2529c..252c0 of 9 entries (D0.W 0..8 after CMPI.W #9; BCC.W at 2528c), only the executed
// entries are blocks: 252a4 (C7) and, since player C10, 252b4 (BRA.W 252ce, a C10 block: main decision 4, C10 contract decision 2; was: 252a4 only);
// a displacement 0 .. 20 moves the PC to the table entry (an unrouted entry is the next dispatch's 'unsupported animation machine PC', a declared
// stop), any other D0.W (a direct 25294 entry) is the checked jump-target error.
bool pc7_table_jump(AnimationMachineContext& c) {
    const std::uint32_t displacement=c.s.d[0]&0xffffU;
    if(displacement>0x20U)return am_error(c,"unsupported animation player c7 jump target");
    c.s.pc=0x2529cU+displacement;return true;
}
}
// Player C7 (214 block starts, contract docs/analysis/animation-machine-player-c7-contract.md; area C plan unit C7 without the C3 blocks 1cde0 1cdf0
// 1cdfa, contract decision 1; demo-only code of the IO observation): the player input state 1f2a4 -> 1f2d4 / 1f538 -> 1f56a / 1f5d2 / 1f5f2 -> 1f6aa
// -> 1f6da (1cab6, 1cd98, 1cb08, 1cec2, 4bfc0 ce02 49fc6, 201a2), the C helper 1c9ec / 1ca4c (the BYTE records 5450 / 5460(A5)), the interpreter
// script callbacks 22480 (4ae4a and the sounds 3af8), 22656 (the BYTE table 22642, the LONG tables 225f6 / 225e6, the 2986 children, DIVU / MULS) and
// 2285c (the 2986 child 23c56, the LONG table 2284c), the 2986 child 24fb0 -> 25102 (443d2, the LONG tables 25082 / 250c2, 4ae4a, the BRA.W table
// 2529c) and its child 253f4 -> 25448.
// C: the 10 consumers 1ca0e (BCS, 1ca4c of C7), 1f330 1f5c4 1f752 25454 (BCC, 49fc6), 1f644 1f776 (BCS, 1cb08), 22674 (BCS, 1c9ec of C7), 22704 (BCC,
// 2986), 25140 (SCS, ea69c) read a known C or fail; 1ca04 1ca28 Clear, 1ca46 1ca56 1ca6a Set, 1ca5c (CMP.B 3(A4),D2) leaves the compare borrow; the RTS
// 1ca12 / 1ca68 pass the C of 1ca0e / 1ca5c back to the callers (dispatcher carry list).  No Z crosses a return.
bool animation_player_c7_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool old=false;
    switch(r.pc) {
    // ---- 1c9ec (BSR from 22670 and the later 227ba; D0.W & 1 the player, D1.B the key): LEA 5450(A5),A4; ANDI.W #1,D0; BEQ.W 1c9fc / LEA 5460(A5),A4 /
    // CMP.B 4(A4),D1; BEQ.W 1ca0a / ANDI.B #fe,CCR; RTS.
    case 0x1c9ec:r.a[4]=am_index(r.a[5],0x5450);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&0xffffU)==0U?0x1c9fc:0x1c9f8;return true;
    case 0x1c9f8:r.a[4]=am_index(r.a[5],0x5460);r.pc=0x1c9fc;return true;
    case 0x1c9fc:if(!pc7_get(c,r.a[4],4,1,value))return false;r.pc=value==(r.d[1]&0xffU)?0x1ca0a:0x1ca04;return true;
    case 0x1ca04:case 0x1ca28:return pc7_return_carry(c,AnimationCarryClear);
    // BSR.W 1ca4c / BCS.W 1ca14 (C of 1ca4c) / RTS (1ca12 passes the Clear) / BTST.B #3,10f001.l; BNE.W 1ca46 / TST.W c(A4); BNE.W 1ca2e / ANDI.B #fe,CCR;
    // RTS / MOVE.W c(A4),D2; CMPI.W #ffff,D2; BEQ.W 1ca46 / SUBQ.W #1,D2; BCC.W 1ca42 / MOVEQ #0,D2 / MOVE.W D2,c(A4) / ORI.B #1,CCR; RTS.
    case 0x1ca0a:return am_call(c,0x1ca4c,0x1ca0e);
    case 0x1ca0e:return pc7_carry(c,0x1ca12,0x1ca14);
    case 0x1ca12:case 0x1ca68:return am_return(c);                                                        // RTS (passes the C, dispatcher carry list).
    case 0x1ca14:if(!pc7_bit(c,0x10f001,3,0,old))return false;r.pc=old?0x1ca46:0x1ca20;return true;
    case 0x1ca20:if(!pc7_get(c,r.a[4],0xc,2,value))return false;r.pc=value==0U?0x1ca28:0x1ca2e;return true;
    case 0x1ca2e:if(!pc7_get(c,r.a[4],0xc,2,value))return false;am_word(r.d[2],value);r.pc=(r.d[2]&0xffffU)==0xffffU?0x1ca46:0x1ca3a;return true;
    case 0x1ca3a:value=r.d[2]&0xffffU;am_word(r.d[2],value-1U);r.pc=value==0U?0x1ca40:0x1ca42;return true;
    case 0x1ca40:r.d[2]=0;r.pc=0x1ca42;return true;
    case 0x1ca42:if(!pc7_put(c,r.a[4],0xc,2,r.d[2]))return false;r.pc=0x1ca46;return true;
    case 0x1ca46:case 0x1ca56:return pc7_return_carry(c,AnimationCarrySet);
    // ---- 1ca4c (BSR from 1ca0a): CMPI.B #ff,3(A4); BNE.W 1ca5c / ORI.B #1,CCR; RTS / MOVE.B 2(A4),D2; CMP.B 3(A4),D2; BCS.W 1ca6a (unsigned BYTE: the
    // borrow is the C of both successors; 1ca68 RTS passes the Clear) / ADDQ.B #1,2(A4); ORI.B #1,CCR; RTS.
    case 0x1ca4c:if(!pc7_get(c,r.a[4],3,1,value))return false;r.pc=value==0xffU?0x1ca56:0x1ca5c;return true;
    case 0x1ca5c:
        if(!pc7_get(c,r.a[4],2,1,value) || !pc7_get(c,r.a[4],3,1,other))return false;am_byte(r.d[2],value);
        if(value<other) {r.carry=AnimationCarrySet;r.pc=0x1ca6a;} else {r.carry=AnimationCarryClear;r.pc=0x1ca68;}
        return true;
    case 0x1ca6a:if(!pc7_get(c,r.a[4],2,1,value) || !pc7_put(c,r.a[4],2,1,value+1U))return false;return pc7_return_carry(c,AnimationCarrySet);
    // ---- 1f2a4 (BNE.W from C6 1ec2c and the later 1ecf2 1edea 1ef70 1f01e 1f0e8): LEA 1b24c(PC),A0; BSR.W 1cab6 / CLR.L 64(A6); the slot part; MOVE.B
    // #2,a9(A6); MOVE.L #1f2d4,(A6) / 1f2d4: BSR.W 1cd98.
    case 0x1f2a4:r.a[0]=0x1b24c;return am_call(c,0x1cab6,0x1f2ac);
    case 0x1f2ac:if(!pc7_slot_state(c,true))return false;return pc7_install(c,0x1f2d4,0x1f2d4);
    case 0x1f2d4:case 0x1f56a:case 0x1f6da:return am_call(c,0x1cd98,r.pc+4U);                           // BSR.W 1cd98.
    // BTST.B #7,15(A6); BEQ.W 1fae8 / BTST.B #5,D0; BEQ.W 1f30a / CMPI.B #0,9e(A6); BNE.W 1f2fc / BTST.B #1,D0; BNE.W 1f7a4 / MOVE.W #c,D1; AND.W D0,D1;
    // BNE.W 1fa68 / BRA.W 1fa3c / BTST.B #6,D0; BNE.W 1f5d2 / BTST.B #4,D0; BNE.W 1f5f2 / JSR 4bfc0.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l /
    // BCC.W 1f33a (C of 49fc6) / MOVE.L #1f3e8,(A6) (written only) / BRA.W 201a2.
    case 0x1f2d8:return pc7_field_bit(c,0x15,7,0x1fae8,0x1f2e2);
    case 0x1f2e2:pc7_input_bit(r,5,0x1f30a,0x1f2ea);return true;
    case 0x1f2ea:return pc7_byte_zero(c,r.a[6],0x9e,0x1f2f4,0x1f2fc);
    case 0x1f2f4:pc7_input_bit(r,1,0x1f2fc,0x1f7a4);return true;
    case 0x1f2fc:am_word(r.d[1],0xc);am_word(r.d[1],r.d[1]&r.d[0]);r.pc=(r.d[1]&0xffffU)!=0U?0x1fa68:0x1f306;return true;
    case 0x1f306:case 0x1f77a:r.pc=0x1fa3c;return true;                                                   // BRA.W 1fa3c.
    case 0x1f30a:pc7_input_bit(r,6,0x1f312,0x1f5d2);return true;
    case 0x1f312:pc7_input_bit(r,4,0x1f31a,0x1f5f2);return true;
    case 0x1f31a:case 0x1f5ae:case 0x1f73c:return am_call(c,0x4bfc0,r.pc+6U);                           // JSR 4bfc0.l.
    case 0x1f320:case 0x1f5b4:case 0x1f742:return pc7_field_call(c,0x1e,0xce02,r.pc+0xaU);              // MOVE.W 1e(A6),D0; JSR ce02.l.
    case 0x1f32a:case 0x1f5be:case 0x1f74c:return am_call(c,0x49fc6,r.pc+6U);                           // JSR 49fc6.l.
    case 0x1f330:return pc7_carry(c,0x1f33a,0x1f334);
    case 0x1f5c4:return pc7_carry(c,0x1f5ce,0x1f5c8);
    case 0x1f334:case 0x1f5c8:return pc7_install(c,0x1f3e8,r.pc+6U);
    case 0x1f33a:case 0x1f5ce:case 0x1f76a:r.pc=0x201a2;return true;                                      // BRA.W 201a2.
    // ---- 1f538 (BEQ.W from 1f70e and the later 1f4f2): BCHG.B #0,15(A6); LEA 1b2ee(PC),A0; BSR.W 1cab6 / the slot part; MOVE.B #2,a9(A6); MOVE.L
    // #1f56a,(A6) / 1f56a: BSR.W 1cd98 / BTST.B #7,15(A6); BEQ.W 1fad2 / BTST.B #5,D0; BEQ.W 1f596 / CMPI.B #0,9e(A6); BNE.W 1f592 / BTST.B #1,D0;
    // BNE.W 1f7a4 / BRA.W 1f76e / BTST.B #1,D0; BEQ.W 1eb98 / BTST.B #6,D0; BNE.W 1f5d2 / BTST.B #4,D0; BNE.W 1f5f2 / the 4bfc0 / ce02 / 49fc6 tail.
    case 0x1f538:if(!pc7_bit(c,am_index(r.a[6],0x15),0,3,old))return false;r.a[0]=0x1b2ee;return am_call(c,0x1cab6,0x1f546);
    case 0x1f546:if(!pc7_slot_state(c,false))return false;return pc7_install(c,0x1f56a,0x1f56a);
    case 0x1f56e:return pc7_field_bit(c,0x15,7,0x1fad2,0x1f578);
    case 0x1f578:pc7_input_bit(r,5,0x1f596,0x1f580);return true;
    case 0x1f580:return pc7_byte_zero(c,r.a[6],0x9e,0x1f58a,0x1f592);
    case 0x1f58a:pc7_input_bit(r,1,0x1f592,0x1f7a4);return true;
    case 0x1f592:case 0x1f702:r.pc=0x1f76e;return true;                                                   // BRA.W 1f76e.
    case 0x1f596:pc7_input_bit(r,1,0x1eb98,0x1f59e);return true;
    case 0x1f59e:pc7_input_bit(r,6,0x1f5a6,0x1f5d2);return true;
    case 0x1f5a6:pc7_input_bit(r,4,0x1f5ae,0x1f5f2);return true;
    // ---- 1f5d2: ANDI.B #bf,a5(A6); ANDI.B #bf,a6(A6); MOVE.B #2,aa(A6); MOVE.B #0,88(A6); LEA 1b482(PC),A0; BRA.W 1f6aa.
    case 0x1f5d2:
        if(!pc7_get(c,r.a[6],0xa5,1,value) || !pc7_put(c,r.a[6],0xa5,1,value&0xbfU) || !pc7_get(c,r.a[6],0xa6,1,value) ||
           !pc7_put(c,r.a[6],0xa6,1,value&0xbfU) || !pc7_put(c,r.a[6],0xaa,1,2) || !pc7_put(c,r.a[6],0x88,1,0))return false;
        r.a[0]=0x1b482;r.pc=0x1f6aa;return true;
    // ---- 1f5f2: ANDI.B #ef,a5(A6); ANDI.B #ef,a6(A6); MOVE.B #2,aa(A6); MOVE.B #1,88(A6); BTST.B #0,a7(A6); BEQ.W 1f648 / MOVE.B #0,aa(A6); LEA
    // 1b632(PC),A0; LEA 1b610(PC),A1; CMPI.B #5,6e(A6); BNE.W 1f634 / LEA 1b6a8(PC),A0; LEA 1b68a(PC),A1 / BCHG.B #1,a7(A6); BNE.W 1f640 (the old bit
    // set) / MOVEA.L A1,A0 / JSR 1cb08(PC) / BCS.W 1f6aa (C of 1cb08).
    case 0x1f5f2:
        if(!pc7_get(c,r.a[6],0xa5,1,value) || !pc7_put(c,r.a[6],0xa5,1,value&0xefU) || !pc7_get(c,r.a[6],0xa6,1,value) ||
           !pc7_put(c,r.a[6],0xa6,1,value&0xefU) || !pc7_put(c,r.a[6],0xaa,1,2) || !pc7_put(c,r.a[6],0x88,1,1))return false;
        return pc7_field_bit(c,0xa7,0,0x1f648,0x1f614);
    case 0x1f614:
        if(!pc7_put(c,r.a[6],0xaa,1,0) || !pc7_get(c,r.a[6],0x6e,1,value))return false;
        r.a[0]=0x1b632;r.a[1]=0x1b610;r.pc=value!=5U?0x1f634:0x1f62c;return true;
    case 0x1f62c:r.a[0]=0x1b6a8;r.a[1]=0x1b68a;r.pc=0x1f634;return true;
    case 0x1f634:if(!pc7_bit(c,am_index(r.a[6],0xa7),1,3,old))return false;r.pc=old?0x1f640:0x1f63e;return true;
    case 0x1f63e:r.a[0]=r.a[1];r.pc=0x1f640;return true;
    case 0x1f640:return am_call(c,0x1cb08,0x1f644);
    case 0x1f644:return pc7_carry(c,0x1f648,0x1f6aa);
    // MOVEA.L 8c(A6),A4; MOVEQ #0,D7; MOVE.B 4(A4),D7; ADD.W D7,D7 twice; MOVEA.L 1f65e(PC,D7.W),A0 (fixed ROM LONG table 1f65e + sext(D7.W)); BRA.W 1f6aa.
    case 0x1f648:
        if(!pc7_get(c,r.a[6],0x8c,4,r.a[4]) || !pc7_get(c,r.a[4],4,1,value))return false;r.d[7]=value;pc7_times4(r.d[7]);
        if(!am_read(c,am_index(0x1f65e,r.d[7]&0xffffU),4,r.a[0]))return false;r.pc=0x1f6aa;return true;
    // ---- 1f6aa: BSR.W 1cab6 / CLR.L 64(A6); the slot part; MOVE.B #2,a9(A6); CLR.B 7e(A6); MOVE.L #1f6da,(A6) / 1f6da: BSR.W 1cd98 / BTST.B #7,15(A6);
    // BEQ.W 1fad2 / BTST.B #5,D0; BEQ.W 1f706 / CMPI.B #0,9e(A6); BNE.W 1f702 / BTST.B #1,D0; BNE.W 1f7a4 / BRA.W 1f76e / BSR.W 1cec2 / CMPI.B #1,D1;
    // BEQ.W 1f538 / TST.B 7e(A6); BEQ.W 1f73c / MOVE.B #1,aa(A6); BTST.B #1,D0; BEQ.W 1eb98 / BTST.B #6,a5(A6); BNE.W 1f5d2 / BTST.B #4,a5(A6); BNE.W
    // 1f5f2 / the 4bfc0 / ce02 / 49fc6 tail; BCC.W 1f76a (C of 49fc6) / (1f756, C8) / BRA.W 201a2.
    case 0x1f6aa:case 0x1f77e:return am_call(c,0x1cab6,r.pc+4U);                                         // BSR.W 1cab6.
    case 0x1f6ae:
        if(!pc7_slot_state(c,true) || !pc7_put(c,r.a[6],0x7e,1,0))return false;return pc7_install(c,0x1f6da,0x1f6da);
    case 0x1f6de:return pc7_field_bit(c,0x15,7,0x1fad2,0x1f6e8);
    case 0x1f6e8:pc7_input_bit(r,5,0x1f706,0x1f6f0);return true;
    case 0x1f6f0:return pc7_byte_zero(c,r.a[6],0x9e,0x1f6fa,0x1f702);
    case 0x1f6fa:pc7_input_bit(r,1,0x1f702,0x1f7a4);return true;
    case 0x1f706:return am_call(c,0x1cec2,0x1f70a);
    case 0x1f70a:r.pc=(r.d[1]&0xffU)==1U?0x1f538:0x1f712;return true;
    case 0x1f712:return pc7_byte_zero(c,r.a[6],0x7e,0x1f73c,0x1f71a);
    case 0x1f71a:if(!pc7_put(c,r.a[6],0xaa,1,1))return false;pc7_input_bit(r,1,0x1eb98,0x1f728);return true;
    case 0x1f728:return pc7_field_bit(c,0xa5,6,0x1f732,0x1f5d2);
    case 0x1f732:return pc7_field_bit(c,0xa5,4,0x1f73c,0x1f5f2);
    case 0x1f752:return pc7_carry(c,0x1f76a,0x1f756);
    // ---- 1f76e (BRA.W from 1f592 1f702 and the later 1f396 1f440 1f4de 1f872 1f962 1f9b2): LEA 1b310(PC),A0; BSR.W 1cb08 / BCS.W 1f77e (C of 1cb08) /
    // BRA.W 1fa3c / BSR.W 1cab6 / MOVE.B #1,a9(A6); the slot part; BRA.W 1faa0.
    case 0x1f76e:r.a[0]=0x1b310;return am_call(c,0x1cb08,0x1f776);
    case 0x1f776:return pc7_carry(c,0x1f77a,0x1f77e);
    case 0x1f782:if(!pc7_put(c,r.a[6],0xa9,1,1) || !pc7_slot(c))return false;r.pc=0x1faa0;return true;
    // ---- 22480 (interpreter script callback, table 4a500; A0 the script LONG): MOVE.W 42(A6),-(A7); MOVE.W 46(A6),-(A7); MOVE.B 7a / 7b(A6),D0 / D1;
    // EXT.W D0 / D1; SUB.W D0,42(A6); SUB.W D1,46(A6); MOVEA.L (A0),A0; MOVE.L A0,-(A7); JSR 4ae4a.l / MOVEA.L (A7)+,A0; MOVE.W (A7)+,46(A6); MOVE.W
    // (A7)+,42(A6); CMPI.B #6,D0; BEQ.W 224c2 / CMPI.B #8,D0; BEQ.W 224f6 / RTS / CMPI.W #2,(A0); BNE.W 224d6 / MOVE.W #1a6b,D0; JSR 3af8.l / RTS /
    // CMPI.W #8,(A0); BNE.W 224ea / #18d1 / #1a69 / #1a4b.
    case 0x22480:
        if(!pc7_get(c,r.a[6],0x42,2,value) || !am_push(c,2,value) || !pc7_get(c,r.a[6],0x46,2,value) || !am_push(c,2,value))return false;
        if(!pc7_get(c,r.a[6],0x7a,1,value) || !pc7_get(c,r.a[6],0x7b,1,other))return false;
        am_word(r.d[0],pc7_ext(value));am_word(r.d[1],pc7_ext(other));
        if(!pc7_get(c,r.a[6],0x42,2,value) || !pc7_put(c,r.a[6],0x42,2,value-r.d[0]) || !pc7_get(c,r.a[6],0x46,2,value) ||
           !pc7_put(c,r.a[6],0x46,2,value-r.d[1]) || !am_read(c,r.a[0],4,r.a[0]) || !am_push(c,4,r.a[0]))return false;
        return am_call(c,0x4ae4a,0x224a6);
    case 0x224a6:
        if(!am_pop(c,4,r.a[0]) || !am_pop(c,2,value) || !pc7_put(c,r.a[6],0x46,2,value) || !am_pop(c,2,value) || !pc7_put(c,r.a[6],0x42,2,value))return false;
        r.pc=(r.d[0]&0xffU)==6U?0x224c2:0x224b8;return true;
    case 0x224b8:r.pc=(r.d[0]&0xffU)==8U?0x224f6:0x224c0;return true;
    case 0x224c0:case 0x224d4:case 0x224e8:case 0x224f4:case 0x22500:case 0x22678:case 0x22758:case 0x22786:case 0x228b6:case 0x251c0:case 0x25486:
        return am_return(c);                                                                              // RTS.
    case 0x224c2:if(!am_read(c,r.a[0],2,value))return false;r.pc=value!=2U?0x224d6:0x224ca;return true;
    case 0x224d6:if(!am_read(c,r.a[0],2,value))return false;r.pc=value!=8U?0x224ea:0x224de;return true;
    case 0x224ca:return pc7_word_call(c,0x1a6b,0x3af8,0x224d4);
    case 0x224de:return pc7_word_call(c,0x18d1,0x3af8,0x224e8);
    case 0x224ea:return pc7_word_call(c,0x1a69,0x3af8,0x224f4);
    case 0x224f6:return pc7_word_call(c,0x1a4b,0x3af8,0x22500);
    // ---- 22656 (interpreter script callback, table 4a500; the later JMP 6f2a2 / 6f2e4): MOVEA.L 8c(A6),A4; MOVE.W 78(A6),D0; MOVEQ #0,D1; MOVE.B
    // 4(A4),D1; LEA 22642(PC),A3; TST.B (A3,D1.W) (fixed ROM BYTE table 22642 + D1.W); BNE.W 2267a / BSR.W 1c9ec / BCS.W 2267a (C of 1c9ec) / RTS.
    case 0x22656:
        if(!pc7_get(c,r.a[6],0x8c,4,r.a[4]) || !pc7_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);
        if(!pc7_get(c,r.a[4],4,1,value))return false;r.d[1]=value;r.a[3]=0x22642;
        if(!am_read(c,am_index(r.a[3],r.d[1]&0xffffU),1,value))return false;r.pc=value!=0U?0x2267a:0x22670;return true;
    case 0x22670:return am_call(c,0x1c9ec,0x22674);
    case 0x22674:return pc7_carry(c,0x22678,0x2267a);
    // ADD.W D1,D1 twice; LEA 225f6(PC),A1; MOVE.L (A1,D1.W),D0 (fixed ROM LONG table 225f6 + sext(D1.W)); BEQ.W 226ca / the child of the table (D0 := 1e),
    // JSR 2986.l / MOVEA.L (A7),A1; the three WORDs D7 / D0 / D1; BTST.B #0,15(A6); BEQ.W 226b8 / the mirror of D7 / D0 / MOVE.B D7,76(A0); JSR 49214.l /
    // JSR 491b6.l / MOVEA.L (A7)+,A0.
    case 0x2267a:
        pc7_times4(r.d[1]);r.a[1]=0x225f6;if(!am_read(c,am_index(r.a[1],r.d[1]&0xffffU),4,r.d[0]))return false;r.pc=r.d[0]==0U?0x226ca:0x2268a;return true;
    case 0x2268a:return pc7_child(c,r.d[0],0x1e,0x2269e);
    case 0x2269e:if(!am_read(c,r.a[7],4,r.a[1]) || !pc7_triple(c,r.d[7],r.d[0],r.d[1]))return false;return pc7_field_bit(c,0x15,0,0x226b8,0x226b0);
    case 0x226b0:pc7_mirror(r.d[7],r.d[0]);r.pc=0x226b8;return true;
    case 0x226b8:if(!pc7_put(c,r.a[0],0x76,1,r.d[7]))return false;return am_call(c,0x49214,0x226c2);
    case 0x226c2:return am_call(c,0x491b6,0x226c8);
    case 0x226c8:if(!am_pop(c,4,r.a[0]))return false;r.pc=0x226ca;return true;
    // LEA 225e6(PC),A1; MOVEQ #0,D0; MOVE.B 9e(A6),D0; ADD.W D0,D0 twice; MOVEA.L (A1,D0.W),A1 (fixed ROM LONG table 225e6); MOVEA.L 8c(A6),A4; MOVE.B
    // 4(A4),D0 (the BYTE only: bits 8..15 of 4 x BYTE 9e stay); ADD.W D0,D0 twice; MOVE.L (A1,D0.W),D7; BEQ.W 22786 / the child D7 (D0 := a), JSR 2986.l /
    // MOVEA.L (A7)+,A1; BCC.W 22786 (C of 2986).
    case 0x226ca:
        r.a[1]=0x225e6;r.d[0]=0;if(!pc7_get(c,r.a[6],0x9e,1,value))return false;am_byte(r.d[0],value);pc7_times4(r.d[0]);
        if(!am_read(c,am_index(r.a[1],r.d[0]&0xffffU),4,r.a[1]) || !pc7_get(c,r.a[6],0x8c,4,r.a[4]) || !pc7_get(c,r.a[4],4,1,value))return false;
        am_byte(r.d[0],value);pc7_times4(r.d[0]);if(!am_read(c,am_index(r.a[1],r.d[0]&0xffffU),4,r.d[7]))return false;
        r.pc=r.d[7]==0U?0x22786:0x226f0;return true;
    case 0x226f0:return pc7_child(c,r.d[7],0xa,0x22704);
    case 0x22704:if(!am_pop(c,4,r.a[1]))return false;return pc7_carry(c,0x22786,0x2270a);
    // ADDQ.B #1,a1(A6); the three WORDs D7 / D2 / D3; BTST.B #0,15(A6); BEQ.W 22726 / the mirror of D7 / D2 / MOVE.B D7,76(A0); MOVE.W 78(A6),78(A0);
    // MOVE.B 60(A6),60(A0); MOVEQ #-1,D0; BSR.W 2291a.
    case 0x2270a:
        if(!pc7_get(c,r.a[6],0xa1,1,value) || !pc7_put(c,r.a[6],0xa1,1,value+1U) || !pc7_triple(c,r.d[7],r.d[2],r.d[3]))return false;
        return pc7_field_bit(c,0x15,0,0x22726,0x2271e);
    case 0x2271e:pc7_mirror(r.d[7],r.d[2]);r.pc=0x22726;return true;
    case 0x22726:
        if(!pc7_put(c,r.a[0],0x76,1,r.d[7]) || !pc7_get(c,r.a[6],0x78,2,value) || !pc7_put(c,r.a[0],0x78,2,value) || !pc7_get(c,r.a[6],0x60,1,value) ||
           !pc7_put(c,r.a[0],0x60,1,value))return false;
        r.d[0]=0xffffffffU;return am_call(c,0x2291a,0x2273c);
    // MOVEA.L 8c(A6),A4; MOVE.B 4(A4),D0; MOVEQ #2,D7; CMPI.B #5,D0; BEQ.W 2275a / MOVEQ #3,D7; CMPI.B #a,D0; BEQ.W 2275a / RTS / CMPI.B #1,9e(A6); BNE.W
    // 22766 / ADDQ.W #1,D7 / MOVE.B 76(A0),D0; ANDI.B #3f,D0; BNE.W 22786 / MOVEQ #0,D0; MOVE.B a1(A6),D0; DIVU.W #3,D0; SWAP D0; SUBQ.W #1,D0; MULS.W
    // D7,D0; ADD.B D0,76(A0) / RTS.
    case 0x2273c:
        if(!pc7_get(c,r.a[6],0x8c,4,r.a[4]) || !pc7_get(c,r.a[4],4,1,value))return false;am_byte(r.d[0],value);r.d[7]=2;
        r.pc=(r.d[0]&0xffU)==5U?0x2275a:0x2274e;return true;
    case 0x2274e:r.d[7]=3;r.pc=(r.d[0]&0xffU)==0xaU?0x2275a:0x22758;return true;
    case 0x2275a:if(!pc7_get(c,r.a[6],0x9e,1,value))return false;r.pc=value!=1U?0x22766:0x22764;return true;
    case 0x22764:am_word(r.d[7],r.d[7]+1U);r.pc=0x22766;return true;
    case 0x22766:if(!pc7_get(c,r.a[0],0x76,1,value))return false;am_byte(r.d[0],value&0x3fU);r.pc=(r.d[0]&0xffU)!=0U?0x22786:0x22772;return true;
    case 0x22772:
        r.d[0]=0;if(!pc7_get(c,r.a[6],0xa1,1,value))return false;am_byte(r.d[0],value);pc7_divu3(r.d[0]);am_swap(r.d[0]);am_word(r.d[0],r.d[0]-1U);
        r.d[0]=pc7_muls(r.d[0],r.d[7]);if(!pc7_get(c,r.a[0],0x76,1,value) || !pc7_put(c,r.a[0],0x76,1,value+r.d[0]))return false;r.pc=0x22786;return true;
    // ---- 2285c (interpreter script callback, table 4a500; BSR from the later 1e10c / 1e654): MOVEA.L 8c(A6),A4; BCLR.B #5,a8(A6); BEQ.W 22894 / TST.W
    // a(A4); BEQ.W 22894 / SUBQ.W #1,a(A4); the child 23c56 (D0 := a), JSR 2986.l / MOVEA.L (A7)+,A1; BRA.W 228e8.
    case 0x2285c:
        if(!pc7_get(c,r.a[6],0x8c,4,r.a[4]) || !pc7_bit(c,am_index(r.a[6],0xa8),5,2,old))return false;r.pc=old?0x2286a:0x22894;return true;
    case 0x2286a:if(!pc7_get(c,r.a[4],0xa,2,value))return false;r.pc=value==0U?0x22894:0x22872;return true;
    case 0x22872:if(!pc7_get(c,r.a[4],0xa,2,value) || !pc7_put(c,r.a[4],0xa,2,value-1U))return false;return pc7_child(c,0x23c56,0xa,0x2288e);
    case 0x2288e:if(!am_pop(c,4,r.a[1]))return false;r.pc=0x228e8;return true;
    // MOVEQ #0,D0; MOVE.B 9e(A6),D0; ADD.W D0,D0 twice; MOVEA.L 2284c(PC,D0.W),A1 (fixed ROM LONG table 2284c); BTST.B #2,10f001.l; BNE.W 228bc / TST.B
    // 7(A4); BNE.W 228b8 / RTS / SUBQ.B #1,7(A4) / MOVEQ #0,D0; MOVE.B 6(A4),D0; CMPI.B #4,D0; BCS.W 228cc (unsigned) / MOVEQ #0,D0 / ADD.W D0,D0 twice;
    // MOVE.L A0,-(A7); MOVEA.L (A1,D0.W),A0 (the child of the RAM / ROM LONG list A1); MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.l / MOVEA.L (A7)+,A1.
    case 0x22894:
        r.d[0]=0;if(!pc7_get(c,r.a[6],0x9e,1,value))return false;am_byte(r.d[0],value);pc7_times4(r.d[0]);
        if(!am_read(c,am_index(0x2284c,r.d[0]&0xffffU),4,r.a[1]) || !pc7_bit(c,0x10f001,2,0,old))return false;r.pc=old?0x228bc:0x228ae;return true;
    case 0x228ae:return pc7_byte_zero(c,r.a[4],7,0x228b6,0x228b8);
    case 0x228b8:if(!pc7_get(c,r.a[4],7,1,value) || !pc7_put(c,r.a[4],7,1,value-1U))return false;r.pc=0x228bc;return true;
    case 0x228bc:r.d[0]=0;if(!pc7_get(c,r.a[4],6,1,value))return false;am_byte(r.d[0],value);r.pc=value<4U?0x228cc:0x228ca;return true;
    case 0x228ca:r.d[0]=0;r.pc=0x228cc;return true;
    case 0x228cc:
        pc7_times4(r.d[0]);if(!am_push(c,4,r.a[0]) || !am_read(c,am_index(r.a[1],r.d[0]&0xffffU),4,r.a[0]))return false;am_word(r.d[0],0xa);r.a[1]=0x100bf4;
        return am_call(c,0x2986,0x228e6);
    case 0x228e6:if(!am_pop(c,4,r.a[1]))return false;r.pc=0x228e8;return true;
    // MOVE.W 78(A6),76(A0); MOVE.W 76(A6),7a(A0); MOVE.B 60(A6),60(A0); the three WORDs D0 / D2 / D3; BTST.B #0,15(A6); BEQ.W 22912 / the mirror of D0 /
    // D2 / MOVE.B D0,78(A0); MOVE.B #ff,D0 (falls into the routed 2291a).
    case 0x228e8:
        if(!pc7_get(c,r.a[6],0x78,2,value) || !pc7_put(c,r.a[0],0x76,2,value) || !pc7_get(c,r.a[6],0x76,2,value) || !pc7_put(c,r.a[0],0x7a,2,value) ||
           !pc7_get(c,r.a[6],0x60,1,value) || !pc7_put(c,r.a[0],0x60,1,value) || !pc7_triple(c,r.d[0],r.d[2],r.d[3]))return false;
        return pc7_field_bit(c,0x15,0,0x22912,0x2290a);
    case 0x2290a:pc7_mirror(r.d[0],r.d[2]);r.pc=0x22912;return true;
    case 0x22912:if(!pc7_put(c,r.a[0],0x78,1,r.d[0]))return false;am_byte(r.d[0],0xff);r.pc=0x2291a;return true;
    // ---- 24fb0 (the 2986 child of the LONG tables 22502 / 2254e): MOVE.W #12a,20(A6); MOVE.L 2000b8.l,22(A6) (bank window); MOVE.W #1a68,D0; JSR 3af8.l /
    // MOVE.L #6f364,84(A6); MOVE.L #100000,7a(A6); CLR.B 88(A6); MOVEA.L #255ba,A1; MOVE.W #100,D0; JSR 49f8c.l / MOVE.W #202,D0; MOVE.B #0,D1; JSR
    // 8ebe.l.
    case 0x24fb0:
        if(!pc7_put(c,r.a[6],0x20,2,0x12a) || !am_read(c,0x2000b8,4,value) || !pc7_put(c,r.a[6],0x22,4,value))return false;
        return pc7_word_call(c,0x1a68,0x3af8,0x24fc8);
    case 0x24fc8:
        if(!pc7_put(c,r.a[6],0x84,4,0x6f364) || !pc7_put(c,r.a[6],0x7a,4,0x100000) || !pc7_put(c,r.a[6],0x88,1,0))return false;r.a[1]=0x255ba;
        return pc7_word_call(c,0x100,0x49f8c,0x24fec);
    case 0x24fec:case 0x25276:case 0x253f4:return pc7_8ebe_call(c,r.pc==0x24fecU?0x24ffa:(r.pc==0x25276U?0x25284:0x25402));
    // MOVE.B #3,82(A6); BSET.B #3,15(A6); MOVE.W #e000,68(A6); MOVE.W #e000,1e(A6); BCLR.B #0,15(A6); MOVE.L 7a(A6),D0; MOVE.B 76(A6),D1; JSR 443d2.l.
    case 0x24ffa:
        if(!pc7_put(c,r.a[6],0x82,1,3) || !pc7_bit(c,am_index(r.a[6],0x15),3,1,old) || !pc7_put(c,r.a[6],0x68,2,0xe000) || !pc7_put(c,r.a[6],0x1e,2,0xe000) ||
           !pc7_bit(c,am_index(r.a[6],0x15),0,2,old) || !pc7_get(c,r.a[6],0x7a,4,r.d[0]) || !pc7_get(c,r.a[6],0x76,1,value))return false;
        am_byte(r.d[1],value);return am_call(c,0x443d2,0x25026);
    // MOVE.L D0,36(A6); MOVE.L D1,3a(A6); MOVE.B 76(A6),D0; BTST.B #5,D0; BEQ.W 2503e / ADDI.B #f,D0 / LSR.W #4,D0; ANDI.W #f,D0; MOVE.B D0,77(A6);
    // MOVE.B 76(A6),D0; BTST.B #5,D0; BEQ.W 25056 / ADDQ.B #7,D0 / LSR.W #3,D0; ANDI.B #1f,D0; MOVE.B D0,78(A6); MOVE.B 76(A6),D0; BTST.B #5,D0; BEQ.W
    // 2506e / ADDQ.B #3,D0 / LSR.W #2,D0; ANDI.W #3f,D0; MOVE.B D0,79(A6); MOVE.L #25102,(A6); BRA.W 25102 (BYTE adds lose the carry, WORD shifts keep
    // bits 16..31).
    case 0x25026:
        if(!pc7_put(c,r.a[6],0x36,4,r.d[0]) || !pc7_put(c,r.a[6],0x3a,4,r.d[1]) || !pc7_get(c,r.a[6],0x76,1,value))return false;am_byte(r.d[0],value);
        pc7_input_bit(r,5,0x2503e,0x2503a);return true;
    case 0x2503a:am_byte(r.d[0],r.d[0]+0xfU);r.pc=0x2503e;return true;
    case 0x2503e:
        am_word(r.d[0],(r.d[0]&0xffffU)>>4);am_word(r.d[0],r.d[0]&0xfU);if(!pc7_put(c,r.a[6],0x77,1,r.d[0]) || !pc7_get(c,r.a[6],0x76,1,value))return false;
        am_byte(r.d[0],value);pc7_input_bit(r,5,0x25056,0x25054);return true;
    case 0x25054:am_byte(r.d[0],r.d[0]+7U);r.pc=0x25056;return true;
    case 0x25056:
        am_word(r.d[0],(r.d[0]&0xffffU)>>3);am_byte(r.d[0],r.d[0]&0x1fU);if(!pc7_put(c,r.a[6],0x78,1,r.d[0]) || !pc7_get(c,r.a[6],0x76,1,value))return false;
        am_byte(r.d[0],value);pc7_input_bit(r,5,0x2506e,0x2506c);return true;
    case 0x2506c:am_byte(r.d[0],r.d[0]+3U);r.pc=0x2506e;return true;
    case 0x2506e:
        am_word(r.d[0],(r.d[0]&0xffffU)>>2);am_word(r.d[0],r.d[0]&0x3fU);if(!pc7_put(c,r.a[6],0x79,1,r.d[0]))return false;return pc7_install(c,0x25102,0x25102);
    // ---- 25102: JSR 4be34.l / MOVE.B 77(A6),D0; ANDI.W #f,D0; LSL.W #2,D0; LEA 25082(PC),A0; TST.B 88(A6); BEQ.W 25122 / LEA 250c2(PC),A0 / MOVEA.L
    // (A0,D0.W),A0 (fixed ROM LONG tables 25082 / 250c2); JSR 4ae4a.l / TST.B D0; BNE.W 2528c.
    case 0x25102:return am_call(c,0x4be34,0x25108);
    case 0x25108:
        if(!pc7_get(c,r.a[6],0x77,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]&0xfU);am_word(r.d[0],r.d[0]<<2);r.a[0]=0x25082;
        return pc7_byte_zero(c,r.a[6],0x88,0x25122,0x2511e);
    case 0x2511e:r.a[0]=0x250c2;r.pc=0x25122;return true;
    case 0x25122:if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),4,r.a[0]))return false;return am_call(c,0x4ae4a,0x2512c);
    case 0x2512c:r.pc=(r.d[0]&0xffU)!=0U?0x2528c:0x25132;return true;
    // TST.B 83(A6); BNE.W 25144 / JSR ea69c.l / SCS.B 83(A6) (C of ea69c) / BTST.B #5,15(A6); BEQ.W 2516c / BTST.B #7,15(A6); BEQ.W 2515e / JSR 4bb52.l /
    // TST.B 83(A6); BEQ.W 251c2 / JMP 2a00.l / JSR 49fc6.l / the x / y bounds (JMP 2a00.l outside) / ADDQ.B #3,8a(A6); ANDI.B #f,8a(A6); SUBQ.B #1,8b(A6);
    // BGT.W 251c0 (signed BYTE) / CMPI.B #5,89(A6); BCC.W 251ba (unsigned) / ADDQ.B #1,89(A6) / MOVE.B #1,8b(A6) / RTS.
    case 0x25132:return pc7_byte_zero(c,r.a[6],0x83,0x2513a,0x25144);
    case 0x2513a:return am_call(c,0xea69c,0x25140);
    case 0x25140:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"player c7 caller requires known carry");
        if(!pc7_put(c,r.a[6],0x83,1,r.carry==AnimationCarrySet?0xffU:0U))return false;r.pc=0x25144;return true;
    case 0x25144:return pc7_field_bit(c,0x15,5,0x2516c,0x2514e);
    case 0x2514e:return pc7_field_bit(c,0x15,7,0x2515e,0x25158);
    case 0x25158:return am_call(c,0x4bb52,0x2515e);
    case 0x2515e:return pc7_byte_zero(c,r.a[6],0x83,0x251c2,0x25166);
    case 0x25166:case 0x2517e:case 0x25194:case 0x253ee:case 0x25458:case 0x2546a:case 0x25480:r.pc=0x2a00;return true;   // JMP 2a00.l.
    case 0x2516c:return am_call(c,0x49fc6,0x25172);
    case 0x25172:return pc7_x_bound(c,0x25184,0x2517e);
    case 0x25184:return pc7_y_bound(c,0x2519a,0x25194);
    case 0x2519a:
        if(!pc7_get(c,r.a[6],0x8a,1,value) || !pc7_put(c,r.a[6],0x8a,1,(value+3U)&0xfU) || !pc7_get(c,r.a[6],0x8b,1,value) ||
           !pc7_put(c,r.a[6],0x8b,1,value-1U))return false;
        r.pc=(value>=2U && value<0x80U)?0x251c0:0x251ac;return true;                                  // BGT: the signed BYTE minus 1 above 0.
    case 0x251ac:if(!pc7_get(c,r.a[6],0x89,1,value))return false;r.pc=value>=5U?0x251ba:0x251b6;return true;
    case 0x251b6:if(!pc7_get(c,r.a[6],0x89,1,value) || !pc7_put(c,r.a[6],0x89,1,value+1U))return false;r.pc=0x251ba;return true;
    case 0x251ba:if(!pc7_put(c,r.a[6],0x8b,1,1))return false;r.pc=0x251c0;return true;
    // ---- 251c2: MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6) (bank window); CMPI.B #40,76(A6); BMI.W 251e0 (the N of the BYTE difference) / BSET.B
    // #0,15(A6) / MOVE.W #e0ed,68(A6); MOVE.W #e0ed,1e(A6); BTST.B #0,61(A6); BEQ.W 25210 / JSR 49a58.l / the jitter of 32(A6); LEA 26178.l,A0; BRA.W
    // 2526a / BTST.B #1,61(A6); BEQ.W 2523a / JSR 49a58.l / the jitter of 2e(A6); BSET.B #1,15(A6); LEA 26112.l,A0; BRA.W 2526a / JSR 49a58.l / the jitter
    // of 2e(A6); CMPI.B #40,6f(A6); BEQ.W 25264 / JSR 49a58.l / the jitter of 32(A6) / LEA 26112.l,A0 / MOVEA.L A0,A1; MOVE.W #100,D0; JSR 49f8c.l / MOVE.W
    // #202,D0; MOVE.B #0,D1; JSR 8ebe.l / MOVE.L #25448,(A6) (written only); RTS.
    case 0x251c2:
        if(!pc7_put(c,r.a[6],0x20,2,0xe2) || !am_read(c,0x200094,4,value) || !pc7_put(c,r.a[6],0x22,4,value) || !pc7_get(c,r.a[6],0x76,1,value))return false;
        r.pc=((value-0x40U)&0x80U)!=0U?0x251e0:0x251da;return true;
    case 0x251da:if(!pc7_bit(c,am_index(r.a[6],0x15),0,1,old))return false;r.pc=0x251e0;return true;
    case 0x251e0:if(!pc7_put(c,r.a[6],0x68,2,0xe0ed) || !pc7_put(c,r.a[6],0x1e,2,0xe0ed))return false;return pc7_field_bit(c,0x61,0,0x25210,0x251f6);
    case 0x251f6:case 0x2521a:case 0x2523a:case 0x25254:case 0x25422:return am_call(c,0x49a58,r.pc+6U);    // JSR 49a58.l.
    case 0x251fc:if(!pc7_jitter(c,0x32))return false;r.a[0]=0x26178;r.pc=0x2526a;return true;
    case 0x25210:return pc7_field_bit(c,0x61,1,0x2523a,0x2521a);
    case 0x25220:if(!pc7_jitter(c,0x2e) || !pc7_bit(c,am_index(r.a[6],0x15),1,1,old))return false;r.a[0]=0x26112;r.pc=0x2526a;return true;
    case 0x25240:if(!pc7_jitter(c,0x2e) || !pc7_get(c,r.a[6],0x6f,1,value))return false;r.pc=value==0x40U?0x25264:0x25254;return true;
    case 0x2525a:if(!pc7_jitter(c,0x32))return false;r.pc=0x25264;return true;
    case 0x25264:r.a[0]=0x26112;r.pc=0x2526a;return true;
    case 0x2526a:r.a[1]=r.a[0];return pc7_word_call(c,0x100,0x49f8c,0x25276);
    case 0x25284:if(!pc7_put(c,r.a[6],0,4,0x25448))return false;return am_return(c);
    // ---- 2528c: CMPI.W #9,D0; BCC.W 252c0 (unsigned WORD) / ADD.W D0,D0 twice; JMP 2529c(PC,D0.W) (contract decision 2) / 252a4: BRA.W 252c0 (the entry
    // 2) / MOVE.W #1a5d,D0; JSR 3af8.l / BRA.W 253c8 / the child 253f4 (D0 := 1e), JSR 2986.l / MOVE.L 84(A6),84(A0); MOVEQ #0,D0; MOVEQ #0,D1; JSR
    // 49214.l / JMP 2a00.l.
    case 0x2528c:r.pc=(r.d[0]&0xffffU)>=9U?0x252c0:0x25294;return true;
    case 0x25294:pc7_times4(r.d[0]);return pc7_table_jump(c);
    case 0x252a4:r.pc=0x252c0;return true;
    case 0x252c0:return pc7_word_call(c,0x1a5d,0x3af8,0x252ca);
    case 0x252ca:r.pc=0x253c8;return true;
    case 0x253c8:r.a[0]=0x253f4;am_word(r.d[0],0x1e);r.a[1]=0x100bf4;return am_call(c,0x2986,0x253de);
    case 0x253de:if(!pc7_get(c,r.a[6],0x84,4,value) || !pc7_put(c,r.a[0],0x84,4,value))return false;r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,0x253ee);
    // ---- 253f4 (the 2986 child of 253c8): MOVE.W #202,D0; MOVE.B #0,D1; JSR 8ebe.l / MOVE.W #e0ed,68(A6); MOVE.W #e0ed,1e(A6); JSR 16ed2.l / MOVEA.L
    // 84(A6),A1; MOVE.W #100,D0; JSR 49f8c.l / JSR 49a58.l / the jitter of 2e(A6); JSR 49a58.l / the jitter of 32(A6); MOVE.L #25448,(A6) / 25448: JSR
    // 43e34.l / JSR 49fc6.l / BCC.W 2545e (C of 49fc6) / JMP 2a00.l / the x / y bounds / RTS.
    case 0x25402:if(!pc7_put(c,r.a[6],0x68,2,0xe0ed) || !pc7_put(c,r.a[6],0x1e,2,0xe0ed))return false;return am_call(c,0x16ed2,0x25414);
    case 0x25414:if(!pc7_get(c,r.a[6],0x84,4,r.a[1]))return false;return pc7_word_call(c,0x100,0x49f8c,0x25422);
    case 0x25428:if(!pc7_jitter(c,0x2e))return false;return am_call(c,0x49a58,0x25438);
    case 0x25438:if(!pc7_jitter(c,0x32))return false;return pc7_install(c,0x25448,0x25448);
    case 0x25448:return am_call(c,0x43e34,0x2544e);
    case 0x2544e:return am_call(c,0x49fc6,0x25454);
    case 0x25454:return pc7_carry(c,0x2545e,0x25458);
    case 0x2545e:return pc7_x_bound(c,0x25470,0x2546a);
    case 0x25470:return pc7_y_bound(c,0x25486,0x25480);
    default:return am_error(c,"unsupported animation player c7 PC");
    }
}
}
