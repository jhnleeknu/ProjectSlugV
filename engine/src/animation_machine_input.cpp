#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (LEA/CMPA/MOVE xxx.L) and the PC-relative ROM data/code addresses.
const std::uint32_t IN_PLAYER1=0x100cb8,IN_PLAYER2=0x100da8;   // 49b1c/49b72 LEA, 49ebc/49ef2 CMPA.L memory, 49f68/49f76 CMPA.L #
const std::uint32_t IN_USER_MASK1=0x10f01c,IN_USER_MASK2=0x10f020; // 49b42/49b98 LEA
const std::uint32_t IN_TARGET1=0x10d73c,IN_TARGET2=0x10d73e;   // MOVE.W xxx.L,D1 (49df0/49dfa, 49da4/49dae, 49e52/49e5c)
const std::uint32_t IN_DEFAULT_MASK=0x49ab0;                   // LEA 49ab0(PC),A4 (fixed ROM, read through the live bus)
const std::uint32_t IN_RECORD_TABLE=0x4cf64;                   // LEA 4cf64(PC),A4 (fixed ROM, read through the live bus)
// d16(A5) operands use the live A5.
bool in_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool in_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// d16(An) operand (live register; WORD/LONG alignment is checked by the bus).
bool in_at(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
// BTST #n,d16(An) or BTST Dn,d16(A5): memory BYTE, bit number mod 8. Branch on the tested bit (Z=inverted bit).
bool in_test(AnimationMachineContext& c,std::uint32_t address,std::uint32_t bit,std::uint32_t set_pc,std::uint32_t clear_pc) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    c.s.pc=((value>>(bit&7U))&1U)?set_pc:clear_pc;return true;
}
// BSET Dn,d16(A5): memory BYTE read-modify-write, bit number mod 8 (Z not consumed).
bool in_set(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t bit) {
    std::uint32_t value=0;if(!in_read(c,displacement,1,value))return false;
    return in_write(c,displacement,1,(value|(1U<<(bit&7U)))&255U);
}
// BSET #n,Dn / BSET Dn,Dn: LONG register, bit number mod 32.
void in_bset(std::uint32_t& r,std::uint32_t bit) {r|=1U<<(bit&31U);}
// BCC/BCS after JSR 289e or 4836e: consumes the known C (289e CMPI.L equal Clear / ORI CCR Set;
// 48378 ANDI CCR Clear / 4837e ORI CCR Set).
bool in_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"input caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// 49b0c/49b62: MOVEQ #0,D7; MOVEQ #0,D6; MOVEA.L slot(A5),A1 (live RAM at this point); CMPA.W #0,A1 (whole LONG);
// BEQ null_pc.
bool in_slot(AnimationMachineContext& c,std::uint32_t slot,std::uint32_t object_pc,std::uint32_t null_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[7]=0;r.d[6]=0;
    if(!in_read(c,slot,4,value))return false;r.a[1]=value;r.pc=value?object_pc:null_pc;return true;
}
// 49b3a/49b90: MOVE.B held(A5),D0; MOVE.B edge(A5),D1; LEA user.L,A4; CMPI.B #2,-7fee(A5); BEQ user_pc.
bool in_null(AnimationMachineContext& c,std::uint32_t held,std::uint32_t user,std::uint32_t user_pc,std::uint32_t default_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!in_read(c,held,1,value))return false;am_byte(r.d[0],value);
    if(!in_read(c,held+1U,1,value))return false;am_byte(r.d[1],value);
    r.a[4]=user;if(!in_read(c,0x8012,1,value))return false;r.pc=value==2U?user_pc:default_pc;return true;
}
// 1d664/1d6c2/1da60: MOVEQ #0,D7; MOVE.W cur(A0),D1; SUB.W camera(A5),D1; SUB.W ae(A0),D1; BEQ zero_pc.
bool in_axis(AnimationMachineContext& c,std::uint32_t field,std::uint32_t camera,std::uint32_t zero_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[7]=0;
    if(!in_at(c,r.a[0],field,2,value))return false;am_word(r.d[1],value);
    if(!in_read(c,camera,2,value))return false;am_word(r.d[1],r.d[1]-value);
    if(!in_at(c,r.a[0],0xae,2,value))return false;am_word(r.d[1],r.d[1]-value);
    r.pc=(r.d[1]&65535U)?next_pc:zero_pc;return true;
}
// MOVE.W prev(A0),D2; SUB.W camera(A5),D2; SUB.W ae(A0),D2; EOR.W D2,D1; BMI cross_pc.
bool in_cross(AnimationMachineContext& c,std::uint32_t field,std::uint32_t camera,std::uint32_t cross_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!in_at(c,r.a[0],field,2,value))return false;am_word(r.d[2],value);
    if(!in_read(c,camera,2,value))return false;am_word(r.d[2],r.d[2]-value);
    if(!in_at(c,r.a[0],0xae,2,value))return false;am_word(r.d[2],r.d[2]-value);
    am_word(r.d[1],r.d[1]^r.d[2]);r.pc=(r.d[1]&0x8000U)?cross_pc:next_pc;return true;
}
// MOVE.W 78(A0),D0; BNE second_pc.
bool in_select(AnimationMachineContext& c,std::uint32_t second_pc,std::uint32_t first_pc) {
    std::uint32_t value=0;if(!in_at(c,c.s.a[0],0x78,2,value))return false;am_word(c.s.d[0],value);
    c.s.pc=(value&65535U)?second_pc:first_pc;return true;
}
// MOVE.W xxx.L,D1 (low WORD only).
bool in_target(AnimationMachineContext& c,std::uint32_t address,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!am_read(c,address,2,value))return false;am_word(c.s.d[1],value);c.s.pc=next_pc;return true;
}
// 49eba/49ef0: CLR.B D0; CMPA.L 100cb8.L,A0 (LONG memory value, not the address); BEQ equal_pc.
bool in_owner(AnimationMachineContext& c,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;am_byte(c.s.d[0],0);if(!am_read(c,IN_PLAYER1,4,value))return false;
    c.s.pc=value==c.s.a[0]?equal_pc:other_pc;return true;
}
// 49f3e/49f46 TST.B latch(A5), then the 49f4a..49f4e body shared by both predecessors (folded here):
// SNE D2 (Z of that TST.B); EOR.B D2,D1; BEQ 49f64.
bool in_latch(AnimationMachineContext& c,std::uint32_t displacement) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!in_read(c,displacement,1,value))return false;
    am_byte(r.d[2],(value&255U)?0xffU:0U);am_byte(r.d[1],r.d[1]^r.d[2]);
    r.pc=(r.d[1]&255U)?0x49f52:0x49f64;return true;
}
// TST.W D2; BEQ done_pc; BMI negative_pc (the BMI block start is folded: it consumes the same TST.W N).
void in_sign(AnimationMachineContext& c,std::uint32_t done_pc,std::uint32_t negative_pc,std::uint32_t positive_pc) {
    const std::uint32_t word=c.s.d[2]&65535U;c.s.pc=word==0U?done_pc:((word&0x8000U)?negative_pc:positive_pc);
}
}
// 480bc frame helper U6: input 49b0c (two player slots LONG 10d734/10d738, marker test through 289e, dynamic
// JSR (A1) callback, 49afe edge merge, 49ab4 mask loop with the ROM default mask 49ab0 or the user mask
// 10f01c/10f020, 49bb4 one-shot mask store), the slot setter 49c20/49c32/49c66 and the callbacks 49e34 1d8cc
// e73f2 49de6 1bec0 49f66 1d5ac(4836e) 1d5e2 1d61a 1d628 1d664 1d6c2 1da60(4d7a6) and 49d88 49e38 49e9c 49eba
// 49ef0 49f2c. Existing executor called: 289e (readiness, known C). JSR (A1) follows the computed-PC policy: the
// full LONG becomes the PC (a non-zero top BYTE is never folded to 24 bits and has no executor; odd targets fail
// as unaligned). 4d7f0 (TRAP #f, index BYTE 0) is a boundary without an executor. 49dd4/49e8a (BMI on the
// previous TST.W) are folded into 49dcc/49e84; 49f4a (SNE D2 on the previous TST.B) is duplicated into
// 49f3e/49f46. ROM data 49ab0..49ab4 and 4cf7e..4df60 are read through the live bus (physical program ROM).
// All d16(A5) operands use the live A5.
bool animation_input_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // 49b0c: first player.
    case 0x49b0c:return in_slot(c,0x5734,0x49b1c,0x49b3a);
    case 0x49b1c:r.a[0]=IN_PLAYER1;return am_call(c,0x289e,0x49b28);
    case 0x49b28:return in_carry(c,0x49b36,0x49b2c); // BCC 49b36: LONG (A0)=270e skips the callback.
    case 0x49b2c:return am_call(c,r.a[1],0x49b2e);  // JSR (A1): computed PC.
    case 0x49b2e:r.a[1]=am_index(r.a[5],0x5726);return am_call(c,0x49afe,0x49b36);
    case 0x49b36:r.pc=0x49b5a;return true;
    case 0x49b3a:return in_null(c,0xccaa,IN_USER_MASK1,0x49b56,0x49b52);
    case 0x49b52:r.a[4]=IN_DEFAULT_MASK;r.pc=0x49b56;return true;
    case 0x49b56:return am_call(c,0x49ab4,0x49b5a);
    case 0x49b5a:r.a[1]=am_index(r.a[5],0x5726);return am_call(c,0x49bb4,0x49b62);
    // 49b62: second player (slot read from live RAM after the first player).
    case 0x49b62:return in_slot(c,0x5738,0x49b72,0x49b90);
    case 0x49b72:r.a[0]=IN_PLAYER2;return am_call(c,0x289e,0x49b7e);
    case 0x49b7e:return in_carry(c,0x49b8c,0x49b82);
    case 0x49b82:return am_call(c,r.a[1],0x49b84);
    case 0x49b84:r.a[1]=am_index(r.a[5],0x572c);return am_call(c,0x49afe,0x49b8c);
    case 0x49b8c:r.pc=0x49bb0;return true;
    case 0x49b90:return in_null(c,0xccb0,IN_USER_MASK2,0x49bac,0x49ba8);
    case 0x49ba8:r.a[4]=IN_DEFAULT_MASK;r.pc=0x49bac;return true;
    case 0x49bac:return am_call(c,0x49ab4,0x49bb0);
    case 0x49bb0:r.a[1]=am_index(r.a[5],0x572c);r.pc=0x49bb4;return true;
    // 49bb4: MOVE.W 4(A1),D0; MOVE.W #ffff,4(A1); AND.W D0,D7; AND.W D0,D6; MOVE.W D7,2(A1); MOVE.W D6,(A1); RTS.
    case 0x49bb4:
        if(!in_at(c,r.a[1],4,2,value))return false;am_word(r.d[0],value);
        if(!am_write(c,am_index(r.a[1],4),2,0xffff))return false;
        am_word(r.d[7],r.d[7]&r.d[0]);am_word(r.d[6],r.d[6]&r.d[0]);
        if(!am_write(c,am_index(r.a[1],2),2,r.d[7]&65535U) || !am_write(c,r.a[1],2,r.d[6]&65535U))return false;
        return am_return(c);

    // 49ab4: MOVEQ #0,D7; MOVE.B D0,D7; ANDI.B #f,D7; MOVE.B D7,D6 (upper D6 kept); MOVEQ #4,D2.
    case 0x49ab4:r.d[7]=r.d[0]&15U;am_byte(r.d[6],r.d[7]);r.d[2]=4;r.pc=0x49ac0;return true;
    // MOVE.B (A4)+,D5; MOVE.B D0,D4; AND.B D5,D4; CMP.B D5,D4; BNE 49ad6.
    case 0x49ac0:
        if(!am_read(c,r.a[4],1,value))return false;r.a[4]+=1U;am_byte(r.d[5],value);
        am_byte(r.d[4],r.d[0]&r.d[5]);r.pc=((r.d[4]^r.d[5])&255U)?0x49ad6:0x49acc;return true;
    // BSET D2,D7; AND.B D1,D4; BEQ 49ad6.
    case 0x49acc:in_bset(r.d[7],r.d[2]);am_byte(r.d[4],r.d[4]&r.d[1]);r.pc=(r.d[4]&255U)?0x49ad4:0x49ad6;return true;
    case 0x49ad4:in_bset(r.d[6],r.d[2]);r.pc=0x49ad6;return true;
    // ADDQ.B #1,D2; CMPI.B #8,D2; BCS 49ac0 (C produced and consumed here).
    case 0x49ad6:am_byte(r.d[2],r.d[2]+1U);r.pc=(r.d[2]&255U)<8U?0x49ac0:0x49ade;return true;
    // SUBQ.W #4,A4 (whole A4); MOVE.B 2(A4),D2; AND.B 1(A4),D2; BEQ 49afc.
    case 0x49ade:
        r.a[4]-=4U;if(!in_at(c,r.a[4],2,1,value))return false;am_byte(r.d[2],value);
        if(!in_at(c,r.a[4],1,1,value))return false;am_byte(r.d[2],r.d[2]&value);
        r.pc=(r.d[2]&255U)?0x49aec:0x49afc;return true;
    case 0x49aec:r.pc=((r.d[6]>>6)&1U)?0x49af4:0x49afc;return true; // BTST #6,D6; BEQ 49afc.
    case 0x49af4:r.d[7]&=~0x20U;r.d[6]&=~0x20U;r.pc=0x49afc;return true;
    case 0x49afc:return am_return(c);
    // 49afe: MOVE.W 2(A1),D6; ANDI.W #fff0,D6; EOR.W D7,D6; AND.W D7,D6; RTS.
    case 0x49afe:
        if(!in_at(c,r.a[1],2,2,value))return false;
        am_word(r.d[6],((value&0xfff0U)^r.d[7])&r.d[7]);return am_return(c);

    // Single-block callbacks.
    case 0x49e34:r.d[7]=0;return am_return(c);
    case 0x1d8cc:return am_return(c);
    case 0xe73f2:if(!in_read(c,0x5e24,2,value))return false;am_word(r.d[7],value);return am_return(c);

    // 49c20: ANDI.W #1,D0; LSL.W #2,D0; LEA 5734(A5),A1; LEA 0(A1,D0.W),A1; MOVE.L A0,(A1); RTS.
    case 0x49c20:
        am_word(r.d[0],r.d[0]&1U);am_word(r.d[0],r.d[0]<<2);
        r.a[1]=am_index(am_index(r.a[5],0x5734),r.d[0]);
        if(!am_write(c,r.a[1],4,r.a[0]))return false;return am_return(c);
    case 0x49c32:r.a[0]=0;r.pc=0x49c20;return true;            // MOVEA.W #0,A0; BRA 49c20.
    case 0x49c66:r.a[0]=0x49e34;r.pc=0x49c20;return true;      // LEA 49e34(PC),A0; BRA 49c20.

    // 49de6: MOVEQ #0,D7; MOVE.W 78(A0),D0; BNE 49dfa.
    case 0x49de6:r.d[7]=0;return in_select(c,0x49dfa,0x49df0);
    case 0x49df0:return in_target(c,IN_TARGET1,0x49e00);
    case 0x49dfa:return in_target(c,IN_TARGET2,0x49e00);
    // MOVE.L 42(A0),D2; SUB.L 53a2(A5),D2; MOVE.L 4a(A0),D3; SUB.L 53aa(A5),D3; SWAP D2; SWAP D3; SUB.W D1,D2;
    // BEQ 49c66.
    case 0x49e00:
        if(!in_at(c,r.a[0],0x42,4,value))return false;r.d[2]=value;
        if(!in_read(c,0x53a2,4,value))return false;r.d[2]-=value;
        if(!in_at(c,r.a[0],0x4a,4,value))return false;r.d[3]=value;
        if(!in_read(c,0x53aa,4,value))return false;r.d[3]-=value;
        am_swap(r.d[2]);am_swap(r.d[3]);am_word(r.d[2],r.d[2]-r.d[1]);
        r.pc=(r.d[2]&65535U)?0x49e1a:0x49c66;return true;
    // SUB.W D1,D3; EOR.W D2,D3; BMI 49c66.
    case 0x49e1a:am_word(r.d[3],r.d[3]-r.d[1]);am_word(r.d[3],r.d[3]^r.d[2]);r.pc=(r.d[3]&0x8000U)?0x49c66:0x49e22;return true;
    case 0x49e22:r.pc=(r.d[2]&0x8000U)?0x49e2e:0x49e28;return true; // TST.W D2; BMI 49e2e.
    case 0x49e28:in_bset(r.d[7],2);return am_return(c);
    case 0x49e2e:in_bset(r.d[7],3);return am_return(c);

    // 49f66: MOVEQ #0,D0; CMPA.L #100cb8,A0; BNE 49f76 / MOVE.B -3356(A5),D0.
    case 0x49f66:r.d[0]=0;r.pc=r.a[0]==IN_PLAYER1?0x49f72:0x49f76;return true;
    case 0x49f72:if(!in_read(c,0xccaa,1,value))return false;am_byte(r.d[0],value);r.pc=0x49f76;return true;
    case 0x49f76:r.pc=r.a[0]==IN_PLAYER2?0x49f80:0x49f84;return true;
    case 0x49f80:if(!in_read(c,0xccb0,1,value))return false;am_byte(r.d[0],value);r.pc=0x49f84;return true;
    case 0x49f84:r.a[4]=IN_DEFAULT_MASK;r.pc=0x49ab4;return true; // LEA 49ab0(PC),A4; BRA 49ab4.

    // 1bec0: BTST #7,15(A0); BEQ 1bed8 / BTST #7,a7(A0); BNE 1bed8 / MOVEQ #0,D7; RTS.
    case 0x1bec0:return in_test(c,am_index(r.a[0],0x15),7,0x1beca,0x1bed8);
    case 0x1beca:return in_test(c,am_index(r.a[0],0xa7),7,0x1bed8,0x1bed4);
    case 0x1bed4:r.d[7]=0;return am_return(c);
    case 0x1bed8:return am_call(c,0x49f66,0x1bede);
    case 0x1bede:am_word(r.d[7],r.d[7]&15U);return am_return(c);

    // 1d5ac: JSR 4836e; BCS 1d5c0 / MOVE.W 78(A0),D0; JSR 49c32 / MOVEQ #0,D7; RTS.
    case 0x1d5ac:return am_call(c,0x4836e,0x1d5b2);
    case 0x1d5b2:return in_carry(c,0x1d5b6,0x1d5c0);
    case 0x1d5b6:if(!in_at(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49c32,0x1d5c0);
    case 0x1d5c0:r.d[7]=0;return am_return(c);
    // 4836e: BTST #2,5683(A5); BEQ 4837e / ANDI #fe,CCR; RTS / ORI #1,CCR; RTS.
    case 0x4836e:return in_test(c,am_index(r.a[5],0x5683),2,0x48378,0x4837e);
    case 0x48378:r.carry=AnimationCarryClear;return am_return(c);
    case 0x4837e:r.carry=AnimationCarrySet;return am_return(c);

    // 1d5e2: BTST #7,15(A0); BNE 1d628 / MOVEQ #0,D7; TST.W 3a(A6); BMI 1d5fa / MOVE.W #8,D7 / RTS.
    case 0x1d5e2:return in_test(c,am_index(r.a[0],0x15),7,0x1d628,0x1d5ec);
    case 0x1d5ec:r.d[7]=0;if(!in_at(c,r.a[6],0x3a,2,value))return false;r.pc=(value&0x8000U)?0x1d5fa:0x1d5f6;return true;
    case 0x1d5f6:am_word(r.d[7],8);r.pc=0x1d5fa;return true;
    case 0x1d5fa:return am_return(c);
    // 1d61a: BTST #7,15(A0); BNE 1d628 / MOVEQ #0,D7; RTS.
    case 0x1d61a:return in_test(c,am_index(r.a[0],0x15),7,0x1d628,0x1d624);
    case 0x1d624:r.d[7]=0;return am_return(c);
    // 1d628: MOVE.W 78(A0),D0; JSR 49c32 (A0 becomes 0); JSR 49f66; RTS.
    case 0x1d628:if(!in_at(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49c32,0x1d632);
    case 0x1d632:return am_call(c,0x49f66,0x1d638);
    case 0x1d638:return am_return(c);

    // 1d664 (X: 42/4a, 53a2; ORI #8 negative / #4 positive).
    case 0x1d664:return in_axis(c,0x42,0x53a2,0x1d628,0x1d674);
    case 0x1d674:r.pc=(r.d[1]&0x8000U)?0x1d67a:0x1d682;return true; // TST.W D1; BPL 1d682.
    case 0x1d67a:am_word(r.d[7],r.d[7]|8U);r.pc=0x1d686;return true;
    case 0x1d682:am_word(r.d[7],r.d[7]|4U);r.pc=0x1d686;return true;
    case 0x1d686:return in_cross(c,0x4a,0x53a2,0x1d628,0x1d696);
    case 0x1d696:return am_return(c);
    // 1d6c2 (Y: 46/4e, 53a6; ORI #1 negative / #2 positive).
    case 0x1d6c2:return in_axis(c,0x46,0x53a6,0x1d628,0x1d6d4);
    case 0x1d6d4:r.pc=(r.d[1]&0x8000U)?0x1d6da:0x1d6e2;return true;
    case 0x1d6da:am_word(r.d[7],r.d[7]|1U);r.pc=0x1d6e6;return true;
    case 0x1d6e2:am_word(r.d[7],r.d[7]|2U);r.pc=0x1d6e6;return true;
    case 0x1d6e6:return in_cross(c,0x4e,0x53a6,0x1d628,0x1d6f8);
    case 0x1d6f8:return am_return(c);
    // 1da60 (X like 1d664; zero or crossing goes to 1da98).
    case 0x1da60:return in_axis(c,0x42,0x53a2,0x1da98,0x1da72);
    case 0x1da72:r.pc=(r.d[1]&0x8000U)?0x1da78:0x1da80;return true;
    case 0x1da78:am_word(r.d[7],r.d[7]|8U);r.pc=0x1da84;return true;
    case 0x1da80:am_word(r.d[7],r.d[7]|4U);r.pc=0x1da84;return true;
    case 0x1da84:return in_cross(c,0x4a,0x53a2,0x1da98,0x1da96);
    case 0x1da96:return am_return(c);
    // 1da98: MOVE.W 78(A0),D0; JSR 4d7a6 / TST.B D0; BEQ 1dab8 / MOVE.W 78(A0),D0 (returned A0); JSR 49c32 /
    // JSR 49f66 / RTS.
    case 0x1da98:if(!in_at(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4d7a6,0x1daa2);
    case 0x1daa2:r.pc=(r.d[0]&255U)?0x1daa8:0x1dab8;return true;
    case 0x1daa8:if(!in_at(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49c32,0x1dab2);
    case 0x1dab2:return am_call(c,0x49f66,0x1dab8);
    case 0x1dab8:return am_return(c);

    // 4d7a6: TST.B D0; BNE 4d7b8 / A4=5cba(A5), A0=-7348(A5); BRA 4d7c0 / A4=5ce6(A5), A0=-7258(A5) / JSR 289e.
    case 0x4d7a6:r.pc=(r.d[0]&255U)?0x4d7b8:0x4d7ac;return true;
    case 0x4d7ac:r.a[4]=am_index(r.a[5],0x5cba);r.a[0]=am_index(r.a[5],0x8cb8);r.pc=0x4d7c0;return true;
    case 0x4d7b8:r.a[4]=am_index(r.a[5],0x5ce6);r.a[0]=am_index(r.a[5],0x8da8);r.pc=0x4d7c0;return true;
    case 0x4d7c0:return am_call(c,0x289e,0x4d7c6);
    case 0x4d7c6:return in_carry(c,0x4d7d0,0x4d7ca); // BCC 4d7d0.
    case 0x4d7ca:if(!am_read(c,r.a[4],2,value))return false;r.pc=(value&65535U)?0x4d7e2:0x4d7d0;return true;
    // MOVE.W #0,D0 (upper kept); MOVEQ #0,D1..D4; MOVEQ #-1,D5; MOVEQ #0,D6; RTS.
    case 0x4d7d0:am_word(r.d[0],0);r.d[1]=0;r.d[2]=0;r.d[3]=0;r.d[4]=0;r.d[5]=0xffffffffU;r.d[6]=0;return am_return(c);
    // MOVEQ #0,D0; MOVE.B 27(A4),D0; CMPI.W #0,D0; BNE 4d7f2 (index 0 reaches the 4d7f0 TRAP boundary).
    case 0x4d7e2:
        if(!in_at(c,r.a[4],0x27,1,value))return false;r.d[0]=value&255U;r.pc=r.d[0]?0x4d7f2:0x4d7f0;return true;
    // MOVE.B 25(A4),D1; MOVE.B 26(A4),D2; MOVE.W 1c(A4),D3; MOVE.W 20(A4),D5; MOVE.B 2a(A4),D6; MOVE.W D0,D4;
    // ANDI.W #ff,D4; MULU.W #10,D4 (LONG); LEA 4cf64(PC),A4; ADDA.W D4,A4; MOVE.W a(A4),D4; RTS.
    case 0x4d7f2:
        if(!in_at(c,r.a[4],0x25,1,value))return false;am_byte(r.d[1],value);
        if(!in_at(c,r.a[4],0x26,1,value))return false;am_byte(r.d[2],value);
        if(!in_at(c,r.a[4],0x1c,2,value))return false;am_word(r.d[3],value);
        if(!in_at(c,r.a[4],0x20,2,value))return false;am_word(r.d[5],value);
        if(!in_at(c,r.a[4],0x2a,1,value))return false;am_byte(r.d[6],value);
        am_word(r.d[4],r.d[0]&255U);r.d[4]=(r.d[4]&65535U)*16U;
        r.a[4]=am_index(IN_RECORD_TABLE,r.d[4]);
        if(!in_at(c,r.a[4],0xa,2,value))return false;am_word(r.d[4],value);return am_return(c);

    // 49d88 (no install path found): MOVE.L 42/4a(A0),D2/D3; SUB.L 53a2/53aa(A5); SWAP; MOVE.W 78(A0),D0; BNE 49dae.
    case 0x49d88:
        if(!in_at(c,r.a[0],0x42,4,value))return false;r.d[2]=value;
        if(!in_at(c,r.a[0],0x4a,4,value))return false;r.d[3]=value;
        if(!in_read(c,0x53a2,4,value))return false;r.d[2]-=value;
        if(!in_read(c,0x53aa,4,value))return false;r.d[3]-=value;
        am_swap(r.d[2]);am_swap(r.d[3]);return in_select(c,0x49dae,0x49da4);
    case 0x49da4:return in_target(c,IN_TARGET1,0x49db4);
    case 0x49dae:return in_target(c,IN_TARGET2,0x49db4);
    // SUB.W D1,D2; SUB.W D1,D3; EOR.W D2,D3; BPL 49dcc.
    case 0x49db4:
        am_word(r.d[2],r.d[2]-r.d[1]);am_word(r.d[3],r.d[3]-r.d[1]);am_word(r.d[3],r.d[3]^r.d[2]);
        r.pc=(r.d[3]&0x8000U)?0x49dbe:0x49dcc;return true;
    // MOVE.W D2,-(A7); MOVE.L A0,-(A7); BSR 49c32.
    case 0x49dbe:if(!am_push(c,2,r.d[2]&65535U) || !am_push(c,4,r.a[0]))return false;return am_call(c,0x49c32,0x49dc6);
    // MOVEA.L (A7)+,A0; MOVE.W (A7)+,D2; NEG.W D2.
    case 0x49dc6:
        if(!am_pop(c,4,value))return false;r.a[0]=value;
        if(!am_pop(c,2,value))return false;am_word(r.d[2],0U-value);r.pc=0x49dcc;return true;
    // MOVEQ #0,D7; TST.W D2; BEQ 49de4; BMI 49de0 (49dd4 folded).
    case 0x49dcc:r.d[7]=0;in_sign(c,0x49de4,0x49de0,0x49dd8);return true;
    case 0x49dd8:in_bset(r.d[7],2);r.pc=0x49de4;return true;
    case 0x49de0:in_bset(r.d[7],3);r.pc=0x49de4;return true;
    case 0x49de4:return am_return(c);

    // 49e38: MOVEQ #0,D7; MOVE.W 42/4a(A0),D2/D3; SUB.W 53a2/53aa(A5); MOVE.W 78(A0),D0; BNE 49e5c.
    case 0x49e38:
        r.d[7]=0;
        if(!in_at(c,r.a[0],0x42,2,value))return false;am_word(r.d[2],value);
        if(!in_at(c,r.a[0],0x4a,2,value))return false;am_word(r.d[3],value);
        if(!in_read(c,0x53a2,2,value))return false;am_word(r.d[2],r.d[2]-value);
        if(!in_read(c,0x53aa,2,value))return false;am_word(r.d[3],r.d[3]-value);
        return in_select(c,0x49e5c,0x49e52);
    case 0x49e52:return in_target(c,IN_TARGET1,0x49e62);
    case 0x49e5c:return in_target(c,IN_TARGET2,0x49e62);
    case 0x49e62:am_word(r.d[2],r.d[2]-r.d[1]);r.pc=(r.d[2]&65535U)?0x49e68:0x49e70;return true; // SUB.W D1,D2; BEQ 49e70.
    // SUB.W D1,D3; EOR.W D2,D3; BPL 49e84.
    case 0x49e68:am_word(r.d[3],r.d[3]-r.d[1]);am_word(r.d[3],r.d[3]^r.d[2]);r.pc=(r.d[3]&0x8000U)?0x49e70:0x49e84;return true;
    case 0x49e70:return in_test(c,am_index(r.a[0],0x15),7,0x49e7a,0x49e84); // BTST #7,15(A0); BEQ 49e84.
    case 0x49e7a:r.d[7]=0;r.a[0]=0x49f2c;r.pc=0x49c20;return true;       // MOVEQ #0,D7; LEA 49f2c(PC),A0; BRA 49c20.
    case 0x49e84:in_sign(c,0x49e9a,0x49e96,0x49e8e);return true;            // TST.W D2; BEQ 49e9a; BMI 49e96 (49e8a folded).
    case 0x49e8e:in_bset(r.d[7],2);r.pc=0x49e9a;return true;
    case 0x49e96:in_bset(r.d[7],3);r.pc=0x49e9a;return true;
    case 0x49e9a:return am_return(c);

    // 49e9c: BSR 49de6 / MOVEM.L D0,-(A7); MOVE.W D7,D0; ANDI.W #c,D0; BNE 49eb4 / MOVEQ #0,D7; BSET #5,D7 /
    // MOVEM.L (A7)+,D0; RTS.
    case 0x49e9c:return am_call(c,0x49de6,0x49ea0);
    case 0x49ea0:
        if(!am_push(c,4,r.d[0]))return false;am_word(r.d[0],r.d[7]&12U);
        r.pc=(r.d[0]&65535U)?0x49eb4:0x49eae;return true;
    case 0x49eae:r.d[7]=0;in_bset(r.d[7],5);r.pc=0x49eb4;return true;
    case 0x49eb4:if(!am_pop(c,4,value))return false;r.d[0]=value;return am_return(c);

    // 49eba: CLR.B D0; CMPA.L 100cb8.L,A0; BEQ 49eca / MOVE.B #1,D0 / BTST D0,5732(A5); BNE 49eea /
    // BSET D0,5732(A5); BSR 49de6 / MOVEM.L D0,-(A7); MOVE.W D7,D0; ORI.W #20,D0; MOVEM.L (A7)+,D0; RTS
    // (the OR result is discarded) / BSR 49de6 / RTS.
    case 0x49eba:return in_owner(c,0x49eca,0x49ec6);
    case 0x49ec6:am_byte(r.d[0],1);r.pc=0x49eca;return true;
    case 0x49eca:return in_test(c,am_index(r.a[5],0x5732),r.d[0],0x49eea,0x49ed2);
    case 0x49ed2:if(!in_set(c,0x5732,r.d[0]))return false;return am_call(c,0x49de6,0x49eda);
    case 0x49eda:
        if(!am_push(c,4,r.d[0]))return false;am_word(r.d[0],r.d[7]|0x20U);
        if(!am_pop(c,4,value))return false;r.d[0]=value;return am_return(c);
    case 0x49eea:return am_call(c,0x49de6,0x49eee);
    case 0x49eee:return am_return(c);

    // 49ef0: CLR.B D0; CMPA.L 100cb8.L,A0; BEQ 49f00 / MOVE.B #1,D0 / BTST D0,5732(A5); BEQ 49f10 /
    // MOVE.W 78(A0),D0; CLR.L D7; RTS / MOVEM.L D0,-(A7); BSR 49de6 / MOVEM.L (A7)+,D1; MOVE.W D7,D2;
    // ANDI.W #c,D2; BNE 49f2a / BSET D1,5732(A5) / RTS.
    case 0x49ef0:return in_owner(c,0x49f00,0x49efc);
    case 0x49efc:am_byte(r.d[0],1);r.pc=0x49f00;return true;
    case 0x49f00:return in_test(c,am_index(r.a[5],0x5732),r.d[0],0x49f08,0x49f10);
    case 0x49f08:if(!in_at(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);r.d[7]=0;return am_return(c);
    case 0x49f10:if(!am_push(c,4,r.d[0]))return false;return am_call(c,0x49de6,0x49f18);
    case 0x49f18:
        if(!am_pop(c,4,value))return false;r.d[1]=value;am_word(r.d[2],r.d[7]&12U);
        r.pc=(r.d[2]&65535U)?0x49f2a:0x49f26;return true;
    case 0x49f26:if(!in_set(c,0x5732,r.d[1]))return false;r.pc=0x49f2a;return true;
    case 0x49f2a:return am_return(c);

    // 49f2c: MOVEQ #0,D7; BTST #0,15(A0); SNE D1; MOVE.W 78(A0),D0; BNE 49f46.
    case 0x49f2c:
        r.d[7]=0;if(!in_at(c,r.a[0],0x15,1,value))return false;am_byte(r.d[1],(value&1U)?0xffU:0U);
        return in_select(c,0x49f46,0x49f3e);
    case 0x49f3e:return in_latch(c,0x5740); // TST.B 5740(A5); BRA 49f4a (49f4a body duplicated).
    case 0x49f46:return in_latch(c,0x5741); // TST.B 5741(A5) and the 49f4a body.
    case 0x49f52:r.pc=(r.d[2]&255U)?0x49f60:0x49f58;return true; // TST.B D2; BNE 49f60.
    case 0x49f58:in_bset(r.d[7],3);r.pc=0x49f64;return true;
    case 0x49f60:in_bset(r.d[7],2);r.pc=0x49f64;return true;
    case 0x49f64:return am_return(c);
    default:return am_error(c,"unsupported animation input PC");
    }
}
}
