#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc6_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc6_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR #bit,d16(An) and Dn,abs / d16(An) (a memory operand: BYTE, bit = the immediate or Dn modulo 8). op 0 tests, 1 sets, 2 clears; old is
// the bit before (the Z of the instruction is old = 0).
bool pc6_bit(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return am_write(c,address,1,op==1U?(value|mask):(value&~mask));
}
// TST.W d16(A6); BEQ.W / BNE.W: zero_pc when the WORD is 0, else other_pc.
bool pc6_word_zero(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc6_get(c,c.s.a[6],displacement,2,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc6_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c6 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ANDI.B #fe,CCR / ORI.B #1,CCR; RTS: the C returned to the caller.
bool pc6_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// MOVE.W d16(A6),D0 (D0 bits 16..31 kept); JSR / BSR target.
bool pc6_field_call(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc6_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MOVE.L #v,(A6): the node callback LONG.
bool pc6_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc6_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.W #f,b0(A6); MOVE.L #v,(A6) (1dac2 / 1dcea / 1dd3e): the 15-frame counter and the callback that is entered at once.
bool pc6_counter_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!pc6_put(c,c.s.a[6],0xb0,2,0xf))return false;return pc6_install(c,value,value);
}
// SUBQ.W #1,b0(A6); BCS.W borrow_pc (the borrow: the WORD was 0) / RTS (1dade / 1dd06 / 1dd5a).
bool pc6_count_down(AnimationMachineContext& c,std::uint32_t borrow_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc6_get(c,c.s.a[6],0xb0,2,value) || !pc6_put(c,c.s.a[6],0xb0,2,value-1U))return false;
    c.s.pc=value==0U?borrow_pc:other_pc;return true;
}
// LEA 2e(A6),A0; JSR 43e08.l (1daf2 1dd1a 1dd6e 1dd8c 1ddac 1e83e).  A1 := 0 and the D0 / D1 values are set by the callers (WORD or LONG as the
// original instruction).
bool pc6_motion_call(AnimationMachineContext& c,std::uint32_t return_pc) {
    c.s.a[0]=am_index(c.s.a[6],0x2e);return am_call(c,0x43e08,return_pc);
}
// MOVE.W d16(A6),D1; SUB.W d16(A5),D1; MOVE.W D1,ae(A6) (WORD; D1 bits 16..31 kept) of 1d648 / 1d6a6.
bool pc6_offset(AnimationMachineContext& c,std::uint32_t node_displacement,std::uint32_t a5_displacement) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,base=0;
    if(!pc6_get(c,r.a[6],node_displacement,2,value) || !pc6_get(c,r.a[5],a5_displacement,2,base))return false;
    am_word(r.d[1],value-base);return pc6_put(c,r.a[6],0xae,2,r.d[1]);
}
// The table index of b0c: D7.W := 4 x D1.B (the MOVEQ #0 / MOVE.B / LSL.W #2 of b2a) or 4 (the MOVE.W #4 of b40), then ADD.B (A0,D0.W),D7 (the BYTE
// 10fdb6 + sext(D0.W); the carry out of the BYTE add is lost, bits 8..15 kept) and TST.B (A1,D7.W) (fixed ROM BYTE table b58 + sext(D7.W)).
bool pc6_b58(AnimationMachineContext& c,std::uint32_t& entry) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),1,value))return false;am_byte(r.d[7],r.d[7]+value);
    return am_read(c,am_index(r.a[1],r.d[7]&0xffffU),1,entry);
}
// MOVE.W 76(A6),D0 (bits 16..31 kept); MOVEQ #k,D1; JSR b0c.l (4ed3c / 4ee50).
bool pc6_b0c_call(AnimationMachineContext& c,std::uint32_t k,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc6_get(c,c.s.a[6],0x76,2,value))return false;am_word(c.s.d[0],value);c.s.d[1]=k;return am_call(c,0xb0c,return_pc);
}
// ADDQ.W #1,D0; ADDQ.W #1,D1 (WORD adds, bits 16..31 kept) of e6496's e64f0 / e6510.
void pc6_rank_up(AnimationMachineState& r) {
    am_word(r.d[0],r.d[0]+1U);am_word(r.d[1],r.d[1]+1U);
}
}
// Player C6 (212 block starts, contract docs/analysis/animation-machine-player-c6-contract.md; area C plan unit C6 without the C4 blocks 4e57e and 4e8e6,
// contract decision 1): the E helpers b0c (bit tables 10f006 / 10f007, the BYTE slots 10fdb6, the fixed ROM BYTE table b58) and e6496 (the rank of the
// LONG (A0) in the LONG table 10f02e), the player-slot state 4eb58 -> 4ed3c -> 4edc0 / 4ee04 (4e5b0 bit table 4e4d2, the 28ae child e695a, 4a974 Z),
// the player body tail 1d398 (the D7 type chain) -> 1daba / 1dc1a / 1dce2 / 1dd36 / 1dd88 / 1dda8 (the 15-frame counters, 1d63a / 1d698, 43e08),
// 1d90a / 1d510 (the LONG table 1d468, 481b2, 2986), 1dbc6, 1dcd0 -> 1e824 (the 28ae child 1e67a, 1e60a, 1e65c, state 1e89e), 1eba0 / 1efa4 / 1ebf6
// (the input dispatch), 206cc, 21564, 21662, 4838c, 4e572, 4e8f8.
// C: the 8 consumers 1d644 1d6a2 (BCS, 49c38), 1d934 (BCC, 1d510), 1dc36 (BCC, 4836e), 1dc62 1ebba (BCC, 1cb08), 1ec66 (BCC, 49fc6), 4ed8c (BCC, 28ae)
// read a known C or fail; 1d514 (CMPI.W #14,D1) leaves the compare borrow, 1d54c (MOVE.L) and 1d546 Clear, 1d574 and 4838c Set; the RTS 1d51c / 1d580
// pass the C of 1d514 / 1d54c back to the callers of 1d510 (dispatcher carry list).  Z: 4ee30 BEQ recomputes the Z of the TST.B (A0) that ends 4a974
// from memory (contract decision 3, the controller C1 / C4 rule).
bool animation_player_c6_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool old=false;
    switch(r.pc) {
    // ---- b0c (JSR from 4ed3c 4ee50 and the E / later callers 4ebd0 4ec5e 4ec76; D0.W the player, D1.B the request): LEA 10fdb6.l,A0; LEA b58(PC),A1;
    // BCLR.B D0,10f007.l; BTST.B D0,10f006.l; BNE.W b40; BNE.W b40 (the same Z: one block) / MOVEQ #0,D7; MOVE.B D1,D7; LSL.W #2,D7; ADD.B (A0,D0.W),D7;
    // TST.B (A1,D7.W); BEQ.W b40 / MOVE.B D1,(A0,D0.W) / MOVE.W #4,D7; ADD.B (A0,D0.W),D7; TST.B (A1,D7.W); BEQ.W b56 / BSET.B D0,10f007.l / RTS.
    case 0xb0c:
        r.a[0]=0x10fdb6;r.a[1]=0xb58;if(!pc6_bit(c,0x10f007,r.d[0],2,old) || !pc6_bit(c,0x10f006,r.d[0],0,old))return false;r.pc=old?0xb40:0xb2a;return true;
    case 0xb2a:r.d[7]=0;am_byte(r.d[7],r.d[1]);am_word(r.d[7],r.d[7]<<2);if(!pc6_b58(c,value))return false;r.pc=value==0U?0xb40:0xb3c;return true;
    case 0xb3c:if(!am_write(c,am_index(r.a[0],r.d[0]&0xffffU),1,r.d[1]&0xffU))return false;r.pc=0xb40;return true;
    case 0xb40:am_word(r.d[7],4);if(!pc6_b58(c,value))return false;r.pc=value==0U?0xb56:0xb50;return true;
    case 0xb50:if(!pc6_bit(c,0x10f007,r.d[0],1,old))return false;r.pc=0xb56;return true;
    case 0xb56:case 0x1d662:case 0x1d6c0:case 0x1dae6:case 0x1dc3a:case 0x1dd0e:case 0x1dd62:case 0x21662:case 0x4edc8:case 0x4ee78:case 0xe6514:
        return am_return(c);                                                                               // RTS.
    // ---- 1d398 (the straight-line continuation of C2 1d388 / 1d390: the type D7.W): CMPI.W #k,D7; BEQ.W target (WORD compare).
    case 0x1d398:r.pc=(r.d[7]&0xffffU)==5U?0x1ddfc:0x1d3a0;return true;
    case 0x1d3a0:r.pc=(r.d[7]&0xffffU)==6U?0x1ddc8:0x1d3a8;return true;
    case 0x1d3a8:r.pc=(r.d[7]&0xffffU)==7U?0x1dce2:0x1d3b0;return true;
    case 0x1d3b0:r.pc=(r.d[7]&0xffffU)==8U?0x1dd36:0x1d3b8;return true;
    case 0x1d3b8:r.pc=(r.d[7]&0xffffU)==9U?0x1dd88:0x1d3c0;return true;
    case 0x1d3c0:r.pc=(r.d[7]&0xffffU)==0xaU?0x1dda8:0x1d3c8;return true;
    case 0x1d3c8:r.pc=(r.d[7]&0xffffU)==0xbU?0x1dc1a:0x1d3d0;return true;
    case 0x1d3d0:r.pc=(r.d[7]&0xffffU)==3U?0x1dc1a:0x1d3d8;return true;
    case 0x1d3d8:r.pc=(r.d[7]&0xffffU)==0xeU?0x1daba:0x1d3e0;return true;
    // ---- 1d510 (BSR from 1d92e and the later callers 1d70a 1d8f6): LEA 1d468(PC),A0 / CMPI.W #14,D1; BCS.W 1d51e (unsigned WORD) / RTS (1d51c passes
    // the Clear of the compare).
    case 0x1d510:r.a[0]=0x1d468;r.pc=0x1d514;return true;
    // The C of CMPI.W #14,D1 is the borrow (D1.W < 14 unsigned): Clear on the fall-through to the RTS 1d51c that returns it, Set on the branch.
    case 0x1d514:
        if((r.d[1]&0xffffU)<0x14U) {r.carry=AnimationCarrySet;r.pc=0x1d51e;} else {r.carry=AnimationCarryClear;r.pc=0x1d51c;}
        return true;
    case 0x1d51c:case 0x1d580:return am_return(c);                                                        // RTS (passes the C, dispatcher carry list).
    // MOVE.L A0,-(A7); MOVE.W D1,-(A7); MOVE.W 78(A6),D0; JSR 481b2.l / JSR 1aa3a.l / MOVE.W (A7)+,D1; MOVEA.L (A7)+,A0; BTST.B #3,D0; BEQ.W 1d54c /
    // CMPI.W #9,D1; BEQ.W 1d54c / ANDI.B #fe,CCR; RTS.
    case 0x1d51e:if(!am_push(c,4,r.a[0]) || !am_push(c,2,r.d[1]&0xffffU))return false;return pc6_field_call(c,0x78,0x481b2,0x1d52c);
    case 0x1d52c:return am_call(c,0x1aa3a,0x1d532);
    case 0x1d532:
        if(!am_pop(c,2,value))return false;am_word(r.d[1],value);if(!am_pop(c,4,r.a[0]))return false;r.pc=(r.d[0]&8U)==0U?0x1d54c:0x1d53e;return true;
    case 0x1d53e:r.pc=(r.d[1]&0xffffU)==9U?0x1d54c:0x1d546;return true;
    case 0x1d546:return pc6_return_carry(c,AnimationCarryClear);
    // ADD.W D1,D1 twice; MOVE.L (A0,D1.W),D1 (the LONG table 1d468 + sext(4 x D1.W); MOVE clears C); BEQ.W 1d580 / MOVEA.L D1,A0; MOVE.W #0,D0;
    // MOVEA.L #100bf4,A1; JSR 2986.l (the child from the table).
    case 0x1d54c:
        am_word(r.d[1],r.d[1]+r.d[1]);am_word(r.d[1],r.d[1]+r.d[1]);if(!am_read(c,am_index(r.a[0],r.d[1]&0xffffU),4,r.d[1]))return false;
        r.carry=AnimationCarryClear;r.pc=r.d[1]==0U?0x1d580:0x1d558;return true;
    case 0x1d558:r.a[0]=r.d[1];am_word(r.d[0],0);r.a[1]=0x100bf4;return am_call(c,0x2986,0x1d56a);
    case 0x1d56a:r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,0x1d574);                                    // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.l.
    // MOVE.W 78(A6),76(A0); ORI.B #1,CCR; RTS.
    case 0x1d574:if(!pc6_get(c,r.a[6],0x78,2,value) || !pc6_put(c,r.a[0],0x76,2,value))return false;return pc6_return_carry(c,AnimationCarrySet);
    // ---- 1d63a / 1d698 (BSR from 1daee 1dd16 1dd6a / 1dd88 1dda8 and later callers): MOVE.W 78(A6),D0; JSR 49c38.l / BCS.W rts (C of 49c38) /
    // MOVE.W 78(A6),D0; MOVE.W 42 / 46(A6),D1; SUB.W 53a2 / 53a6(A5),D1; MOVE.W D1,ae(A6); LEA 1d664 / 1d6c2(PC),A0; JSR 49c20.l / RTS.
    case 0x1d63a:return pc6_field_call(c,0x78,0x49c38,0x1d644);
    case 0x1d644:return pc6_carry(c,0x1d648,0x1d662);
    case 0x1d648:
        if(!pc6_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);if(!pc6_offset(c,0x42,0x53a2))return false;
        r.a[0]=0x1d664;return am_call(c,0x49c20,0x1d662);
    case 0x1d698:return pc6_field_call(c,0x78,0x49c38,0x1d6a2);
    case 0x1d6a2:return pc6_carry(c,0x1d6a6,0x1d6c0);
    case 0x1d6a6:
        if(!pc6_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);if(!pc6_offset(c,0x46,0x53a6))return false;
        r.a[0]=0x1d6c2;return am_call(c,0x49c20,0x1d6c0);
    // ---- 1d90a (the 1db06 loop and the later 1db24 / 1db42): MOVE.W 78(A6),D0; JSR 48210.l / TST.W D1; BEQ.W 1ddd0 / MOVE.W D1,-(A7); LEA 1d8ce(PC),A0;
    // TST.B (A0,D1.W) (fixed ROM BYTE table 1d8ce + sext(D1.W)); BNE.W 1d92e / JSR 4c0ea.l / MOVE.W (A7)+,D1; BSR.W 1d510 / BCC.W 1d93c (C of 1d510) /
    // BRA.W 1dbc6 / BRA.W 1ddd0.
    case 0x1d90a:return pc6_field_call(c,0x78,0x48210,0x1d914);
    case 0x1d914:r.pc=(r.d[1]&0xffffU)==0U?0x1ddd0:0x1d91a;return true;
    case 0x1d91a:
        if(!am_push(c,2,r.d[1]&0xffffU))return false;r.a[0]=0x1d8ce;if(!am_read(c,am_index(r.a[0],r.d[1]&0xffffU),1,value))return false;
        r.pc=value!=0U?0x1d92e:0x1d928;return true;
    case 0x1d928:return am_call(c,0x4c0ea,0x1d92e);
    case 0x1d92e:if(!am_pop(c,2,value))return false;am_word(r.d[1],value);return am_call(c,0x1d510,0x1d934);
    case 0x1d934:return pc6_carry(c,0x1d93c,0x1d938);
    case 0x1d938:r.pc=0x1dbc6;return true;
    case 0x1d93c:case 0x1dcde:r.pc=0x1ddd0;return true;                                                    // BRA.W 1ddd0.
    // ---- 1daba / 1dce2 / 1dd36 (the types e / 7 / 8 of 1d398): TST.W 78(A6); BEQ.W skip / MOVE.W #f,b0(A6); MOVE.L #state,(A6) / state: MOVE.W 78(A6),D0;
    // JSR 49bca.l / JSR ea626.l / SUBQ.W #1,b0(A6); BCS.W next / RTS / MOVE.L #skip,(A6) / skip: BSR.W 1d63a / A1 := 0; D0 / D1; LEA 2e(A6),A0;
    // JSR 43e08.l.
    case 0x1daba:return pc6_word_zero(c,0x78,0x1daee,0x1dac2);
    case 0x1dac2:return pc6_counter_install(c,0x1dace);
    case 0x1dace:case 0x1dc20:return pc6_field_call(c,0x78,0x49bca,r.pc==0x1dace?0x1dad8:0x1dc2a);
    case 0x1dad8:return am_call(c,0xea626,0x1dade);
    case 0x1dade:return pc6_count_down(c,0x1dae8,0x1dae6);
    case 0x1dae8:return pc6_install(c,0x1daee,0x1daee);
    case 0x1daee:return am_call(c,0x1d63a,0x1daf2);
    // MOVEA.W #0,A1; MOVEQ #0,D0; MOVE.W 46(A6),D1; LEA 2e(A6),A0; JSR 43e08.l / BRA.W 1d90a.
    case 0x1daf2:r.a[1]=0;r.d[0]=0;if(!pc6_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],value);return pc6_motion_call(c,0x1db06);
    case 0x1db06:r.pc=0x1d90a;return true;
    // ---- 1dbc6 (1d938 and the later 1d70e 1d8fe 1d9ae 1db9c): BSR.W 1d1d0 / BSET.B #7,a7(A6); MOVE.L #1fcd4,(A6) (written only); RTS.
    case 0x1dbc6:return am_call(c,0x1d1d0,0x1dbca);
    case 0x1dbca:if(!pc6_bit(c,am_index(r.a[6],0xa7),7,1,old) || !pc6_put(c,r.a[6],0,4,0x1fcd4))return false;return am_return(c);
    // ---- 1dc1a (the types b / 3 of 1d398): MOVE.L #1dc20,(A6) / 1dc20: MOVE.W 78(A6),D0; JSR 49bca.l / JSR ea626.l / JSR 4836e.l / BCC.W 1dc3c (C of
    // 4836e) / RTS / JSR 43e34.l / the BYTE / WORD fields, LEA 1b1b0(PC),A0; BSR.W 1cb08 / BCC.W 1dcd0 (C of 1cb08) / BSR.W 1cab6 / MOVE.L #1dc70,(A6) /
    // BSR.W 1d182 / JSR 4bfc0.l / MOVE.W 1e(A6),D0; JSR ce02.l (returns to the interpreter stub 1dc84).
    case 0x1dc1a:return pc6_install(c,0x1dc20,0x1dc20);
    case 0x1dc2a:return am_call(c,0xea626,0x1dc30);
    case 0x1dc30:return am_call(c,0x4836e,0x1dc36);
    case 0x1dc36:return pc6_carry(c,0x1dc3c,0x1dc3a);
    case 0x1dc3c:return am_call(c,0x43e34,0x1dc42);
    // MOVE.B #ff,81(A6); MOVE.B #ff,82(A6); MOVE.W #e0ec,68(A6); MOVE.W #e0ec,1e(A6); LEA 1b1b0(PC),A0; BSR.W 1cb08.
    case 0x1dc42:
        if(!pc6_put(c,r.a[6],0x81,1,0xff) || !pc6_put(c,r.a[6],0x82,1,0xff) || !pc6_put(c,r.a[6],0x68,2,0xe0ec) || !pc6_put(c,r.a[6],0x1e,2,0xe0ec))return false;
        r.a[0]=0x1b1b0;return am_call(c,0x1cb08,0x1dc62);
    case 0x1dc62:return pc6_carry(c,0x1dcd0,0x1dc66);
    case 0x1dc66:return am_call(c,0x1cab6,0x1dc6a);
    case 0x1dc6a:return pc6_install(c,0x1dc70,0x1dc70);
    case 0x1dc70:return am_call(c,0x1d182,0x1dc74);
    case 0x1dc74:return am_call(c,0x4bfc0,0x1dc7a);
    case 0x1dc7a:return pc6_field_call(c,0x1e,0xce02,0x1dc84);
    // ---- 1dcd0 (the Clear side of 1dc62): JSR 1aa3a.l / BTST.L #6,D0; BNE.W 1e824 / BRA.W 1ddd0.
    case 0x1dcd0:return am_call(c,0x1aa3a,0x1dcd6);
    case 0x1dcd6:r.pc=(r.d[0]&0x40U)!=0U?0x1e824:0x1dcde;return true;
    case 0x1dce2:return pc6_word_zero(c,0x78,0x1dd16,0x1dcea);
    case 0x1dcea:return pc6_counter_install(c,0x1dcf6);
    case 0x1dcf6:case 0x1dd4a:return pc6_field_call(c,0x78,0x49bca,r.pc==0x1dcf6?0x1dd00:0x1dd54);
    case 0x1dd00:return am_call(c,0xea626,0x1dd06);
    case 0x1dd06:return pc6_count_down(c,0x1dd10,0x1dd0e);
    case 0x1dd10:return pc6_install(c,0x1dd16,0x1dd16);
    case 0x1dd16:return am_call(c,0x1d63a,0x1dd1a);
    // MOVEA.L #0,A1; MOVE.W #0,D0 (bits 16..31 kept); MOVE.W 46(A6),D1; LEA 2e(A6),A0; JSR 43e08.l / BRA.W 1ddc8.
    case 0x1dd1a:r.a[1]=0;am_word(r.d[0],0);if(!pc6_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],value);return pc6_motion_call(c,0x1dd32);
    case 0x1dd32:case 0x1dd84:case 0x1ddc4:r.pc=0x1ddc8;return true;                                       // BRA.W 1ddc8.
    case 0x1dd36:return pc6_word_zero(c,0x78,0x1dd6a,0x1dd3e);
    case 0x1dd3e:return pc6_counter_install(c,0x1dd4a);
    case 0x1dd54:return am_call(c,0xea626,0x1dd5a);
    case 0x1dd5a:return pc6_count_down(c,0x1dd64,0x1dd62);
    case 0x1dd64:return pc6_install(c,0x1dd6a,0x1dd6a);
    case 0x1dd6a:return am_call(c,0x1d63a,0x1dd6e);
    // MOVEA.W #0,A1; MOVE.W #140,D0; MOVE.W 46(A6),D1; LEA 2e(A6),A0; JSR 43e08.l / BRA.W 1ddc8.
    case 0x1dd6e:r.a[1]=0;am_word(r.d[0],0x140);if(!pc6_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],value);return pc6_motion_call(c,0x1dd84);
    // ---- 1dd88 / 1dda8 (the types 9 / a of 1d398): BSR.W 1d698 / MOVEA.L #0,A1; MOVE.W 42(A6),D0; MOVE.W #200 / #e0,D1; LEA 2e(A6),A0; JSR 43e08.l /
    // BRA.W 1de06 / 1ddc8.
    case 0x1dd88:return am_call(c,0x1d698,0x1dd8c);
    case 0x1dd8c:case 0x1ddac:
        r.a[1]=0;if(!pc6_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],r.pc==0x1dd8c?0x200U:0xe0U);
        return pc6_motion_call(c,r.pc==0x1dd8c?0x1dda4:0x1ddc4);
    case 0x1dda4:case 0x1ddcc:r.pc=0x1de06;return true;                                                    // BRA.W 1de06.
    case 0x1dda8:return am_call(c,0x1d698,0x1ddac);
    case 0x1ddc8:return am_call(c,0x1dbd8,0x1ddcc);                                                       // BSR.W 1dbd8.
    // ---- 1e60a (BSR from 1e8a8 and the later 1e946 1e9a2 1ea16): MOVE.W #280,D1; BTST.L #0,D0; BNE.W 1e626 / MOVE.W #80,D1; BTST.L #1,D0; BNE.W 1e626 /
    // MOVE.W #180,D1 / SUB.W 7c(A6),D1; BMI.W 1e630 (N of the WORD difference) / ADDQ.W #3,D1 / ASR.W #2,D1; ADD.W D1,7c(A6); RTS.
    case 0x1e60a:am_word(r.d[1],0x280);r.pc=(r.d[0]&1U)!=0U?0x1e626:0x1e616;return true;
    case 0x1e616:am_word(r.d[1],0x80);r.pc=(r.d[0]&2U)!=0U?0x1e626:0x1e622;return true;
    case 0x1e622:am_word(r.d[1],0x180);r.pc=0x1e626;return true;
    case 0x1e626:if(!pc6_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[1],r.d[1]-value);r.pc=(r.d[1]&0x8000U)!=0U?0x1e630:0x1e62e;return true;
    case 0x1e62e:am_word(r.d[1],r.d[1]+3U);r.pc=0x1e630;return true;
    // ASR.W #2,D1 (arithmetic WORD shift: bits 14..15 copy the sign); ADD.W D1,7c(A6) (WORD, carry out lost); RTS.
    case 0x1e630:
        value=r.d[1]&0xffffU;am_word(r.d[1],(value>>2)|((value&0x8000U)!=0U?0xc000U:0U));
        if(!pc6_get(c,r.a[6],0x7c,2,value) || !pc6_put(c,r.a[6],0x7c,2,value+r.d[1]))return false;return am_return(c);
    // ---- 1e65c (JSR from 1e8c4 and the later 1e954 1e9b0 1ea24 1ea70): MOVEQ #9,D0; MOVE.W 42(A6),D7; SUB.W 4a(A6),D7; SUB.W 53a2(A5),D7;
    // ADD.W 53aa(A5),D7; BPL.W 1e674 (N of the WORD sum) / MOVEQ #a,D0 / MOVE.B D0,9c(A6); RTS.
    case 0x1e65c:
        r.d[0]=9;if(!pc6_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[7],value);
        if(!pc6_get(c,r.a[6],0x4a,2,value))return false;am_word(r.d[7],r.d[7]-value);
        if(!pc6_get(c,r.a[5],0x53a2,2,value))return false;am_word(r.d[7],r.d[7]-value);
        if(!pc6_get(c,r.a[5],0x53aa,2,value))return false;am_word(r.d[7],r.d[7]+value);r.pc=(r.d[7]&0x8000U)==0U?0x1e674:0x1e672;return true;
    case 0x1e672:r.d[0]=0xa;r.pc=0x1e674;return true;
    case 0x1e674:if(!pc6_put(c,r.a[6],0x9c,1,r.d[0]))return false;return am_return(c);
    // ---- 1e824 (the BTST #6 side of 1dcd6): BSR.W 1d1d0 / BSET.B #2,a7(A6); MOVEA.L #1e67a,A0; MOVE.W #0,D0; JSR 28ae.l (the child 1e67a; its C is not
    // read) / the slot-84 reset, BCLR.B #0,15(A6), WORD 7c := 180, WORD ae := WORD 42, MOVE.W #ffe0,D0; MOVE.W 46(A6),D1; MOVEA.W #0,A1; LEA 2e(A6),A0;
    // JSR 43e08.l / MOVE.L #50000,36(A6); CLR.L 3a(A6); LEA 1bcce(PC),A0; BSR.W 1cb38 / MOVE.B #0,a9(A6); MOVE.L #1e89e,(A6).
    case 0x1e824:return am_call(c,0x1d1d0,0x1e828);
    case 0x1e828:if(!pc6_bit(c,am_index(r.a[6],0xa7),2,1,old))return false;r.a[0]=0x1e67a;am_word(r.d[0],0);return am_call(c,0x28ae,0x1e83e);
    case 0x1e83e:
        if(!pc6_put(c,r.a[6],0x84,4,0x21602) || !pc6_put(c,r.a[6],0x9c,1,0) || !pc6_put(c,r.a[6],0xaa,1,1) || !pc6_put(c,r.a[6],0x7a,2,0) ||
           !pc6_bit(c,am_index(r.a[6],0x15),0,2,old) || !pc6_put(c,r.a[6],0x7c,2,0x180) || !pc6_get(c,r.a[6],0x42,2,value) || !pc6_put(c,r.a[6],0xae,2,value))
            return false;
        am_word(r.d[0],0xffe0);if(!pc6_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],value);r.a[1]=0;return pc6_motion_call(c,0x1e87e);
    case 0x1e87e:
        if(!pc6_put(c,r.a[6],0x36,4,0x50000) || !pc6_put(c,r.a[6],0x3a,4,0))return false;r.a[0]=0x1bcce;return am_call(c,0x1cb38,0x1e892);
    case 0x1e892:if(!pc6_put(c,r.a[6],0xa9,1,0))return false;return pc6_install(c,0x1e89e,0x1e89e);
    // 1e89e (the state): MOVE.W 78(A6),D0; JSR 49bca.l / MOVEQ #0,D0; BSR.W 1e60a / JSR 43ea4.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l (its C is
    // not read) / JSR 1e65c(PC) / MOVE.W 42(A6),D0; CMP.W ae(A6),D0; BLE.W 1e8da (signed WORD) / MOVE.L #1e918,(A6) (written only) / BRA.W 201a2.
    case 0x1e89e:return pc6_field_call(c,0x78,0x49bca,0x1e8a8);
    case 0x1e8a8:r.d[0]=0;return am_call(c,0x1e60a,0x1e8ae);
    case 0x1e8ae:return am_call(c,0x43ea4,0x1e8b4);
    case 0x1e8b4:return pc6_field_call(c,0x1e,0xce02,0x1e8be);
    case 0x1e8be:return am_call(c,0x49fc6,0x1e8c4);
    case 0x1e8c4:return am_call(c,0x1e65c,0x1e8c8);
    case 0x1e8c8:
        if(!pc6_get(c,r.a[6],0x42,2,value) || !pc6_get(c,r.a[6],0xae,2,other))return false;am_word(r.d[0],value);
        r.pc=static_cast<std::int32_t>(am_extend_word(value))<=static_cast<std::int32_t>(am_extend_word(other))?0x1e8da:0x1e8d4;return true;
    case 0x1e8d4:return pc6_install(c,0x1e918,0x1e8da);
    case 0x1e8da:case 0x1ec70:r.pc=0x201a2;return true;                                                    // BRA.W 201a2.
    // ---- 1eba0 (the 1efac loop and the later BCC 1eca0): TST.B 9d(A6); BGT.W 1ed78 (signed BYTE > 0) / BTST.B #5,a7(A6); BEQ.W 1ed78 / LEA 1b1ca(PC),A0;
    // BSR.W 1cb08 / BCC.W 1ed78 (C of 1cb08) / BSR.W 1cab6 / the field resets, MOVE.L #1ebf6,(A6).
    case 0x1eba0:
        if(!pc6_get(c,r.a[6],0x9d,1,value))return false;r.pc=(value!=0U && (value&0x80U)==0U)?0x1ed78:0x1eba8;return true;
    case 0x1eba8:if(!pc6_bit(c,am_index(r.a[6],0xa7),5,0,old))return false;r.pc=old?0x1ebb2:0x1ed78;return true;
    case 0x1ebb2:r.a[0]=0x1b1ca;return am_call(c,0x1cb08,0x1ebba);
    case 0x1ebba:return pc6_carry(c,0x1ed78,0x1ebbe);
    case 0x1ebbe:return am_call(c,0x1cab6,0x1ebc2);
    // CLR.B 9d; CLR.L 64; CLR.B 92; CLR.B a2; MOVE.L #21602,84; MOVE.B #0,9c; MOVE.B #1,aa; CLR.W 7a; MOVE.B #1,a9 (A6); MOVE.L #1ebf6,(A6).
    case 0x1ebc2:
        if(!pc6_put(c,r.a[6],0x9d,1,0) || !pc6_put(c,r.a[6],0x64,4,0) || !pc6_put(c,r.a[6],0x92,1,0) || !pc6_put(c,r.a[6],0xa2,1,0) ||
           !pc6_put(c,r.a[6],0x84,4,0x21602) || !pc6_put(c,r.a[6],0x9c,1,0) || !pc6_put(c,r.a[6],0xaa,1,1) || !pc6_put(c,r.a[6],0x7a,2,0) ||
           !pc6_put(c,r.a[6],0xa9,1,1))return false;
        return pc6_install(c,0x1ebf6,0x1ebf6);
    // 1ebf6 (the state): BSR.W 1cd98 (the input bits in D0) / BTST.B #7,15(A6); BEQ.W 1fae8 / BTST.L #5,D0; BEQ.W 1ec2c / CMPI.B #0,9e(A6); BNE.W 1ec1e /
    // BTST.L #1,D0; BNE.W 1f7a4 / MOVE.W #c,D1; AND.W D0,D1; BNE.W 1fa68 / BRA.W 1fa3c.
    case 0x1ebf6:return am_call(c,0x1cd98,0x1ebfa);
    case 0x1ebfa:if(!pc6_bit(c,am_index(r.a[6],0x15),7,0,old))return false;r.pc=old?0x1ec04:0x1fae8;return true;
    case 0x1ec04:r.pc=(r.d[0]&0x20U)==0U?0x1ec2c:0x1ec0c;return true;
    case 0x1ec0c:if(!pc6_get(c,r.a[6],0x9e,1,value))return false;r.pc=value!=0U?0x1ec1e:0x1ec16;return true;
    case 0x1ec16:r.pc=(r.d[0]&2U)!=0U?0x1f7a4:0x1ec1e;return true;
    case 0x1ec1e:am_word(r.d[1],0xcU&r.d[0]);r.pc=(r.d[1]&0xffffU)!=0U?0x1fa68:0x1ec28;return true;
    case 0x1ec28:r.pc=0x1fa3c;return true;
    // BTST.L #1,D0; BNE.W 1f2a4 / BTST.L #7,D0; BNE.W 1f1d8 / MOVE.W #c,D1; AND.W D0,D1; BNE.W 1eeea / MOVE.W #50,D1; AND.W D1,D0 (D0.W changed);
    // BNE.W 1ed78 / JSR 4bfc0.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l / BCC.W 1ec70 (C of 49fc6) / MOVE.L #1ed78,(A6) (written only) /
    // BRA.W 201a2.
    case 0x1ec2c:r.pc=(r.d[0]&2U)!=0U?0x1f2a4:0x1ec34;return true;
    case 0x1ec34:r.pc=(r.d[0]&0x80U)!=0U?0x1f1d8:0x1ec3c;return true;
    case 0x1ec3c:am_word(r.d[1],0xcU&r.d[0]);r.pc=(r.d[1]&0xffffU)!=0U?0x1eeea:0x1ec46;return true;
    case 0x1ec46:am_word(r.d[1],0x50);am_word(r.d[0],r.d[0]&0x50U);r.pc=(r.d[0]&0xffffU)!=0U?0x1ed78:0x1ec50;return true;
    case 0x1ec50:return am_call(c,0x4bfc0,0x1ec56);
    case 0x1ec56:return pc6_field_call(c,0x1e,0xce02,0x1ec60);
    case 0x1ec60:return am_call(c,0x49fc6,0x1ec66);
    case 0x1ec66:return pc6_carry(c,0x1ec70,0x1ec6a);
    case 0x1ec6a:return pc6_install(c,0x1ed78,0x1ec70);
    // ---- 1efa4 (the straight-line continuation of C4 1ef9a): TST.W 88(A6); BNE.W 1ed78 / BRA.W 1eba0.
    case 0x1efa4:return pc6_word_zero(c,0x88,0x1efac,0x1ed78);
    case 0x1efac:r.pc=0x1eba0;return true;
    // ---- 206cc (the straight-line continuation of C3 206c0 when TST.B D0 is not 0): BSET.B #0,a7(A6) (falls into C3 206d2).
    case 0x206cc:if(!pc6_bit(c,am_index(r.a[6],0xa7),0,1,old))return false;r.pc=0x206d2;return true;
    // ---- 21564 (the SUBQ.B borrow of C5 214d6 / 2155a and the later 1fcbe 210b4): JMP 2a00.l.
    case 0x21564:r.pc=0x2a00;return true;
    // ---- 481b2 (JSR from 1d51e and the later 1d982 1d9e8): LEA 5694(A5),A0; ANDI.W #1,D0; BEQ.W 481c2 / LEA 569c(A5),A0 / MOVE.B (A0),D1;
    // MOVE.B 3(A0),D2; MOVE.B 2(A0),D3; MOVE.W 4(A0),D4; MOVE.W 6(A0),D5; MOVE.B 1(A0),D6; JMP 4d50e.l.
    case 0x481b2:r.a[0]=am_index(r.a[5],0x5694);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&0xffffU)==0U?0x481c2:0x481be;return true;
    case 0x481be:r.a[0]=am_index(r.a[5],0x569c);r.pc=0x481c2;return true;
    case 0x481c2:
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[1],value);if(!pc6_get(c,r.a[0],3,1,value))return false;am_byte(r.d[2],value);
        if(!pc6_get(c,r.a[0],2,1,value))return false;am_byte(r.d[3],value);if(!pc6_get(c,r.a[0],4,2,value))return false;am_word(r.d[4],value);
        if(!pc6_get(c,r.a[0],6,2,value))return false;am_word(r.d[5],value);if(!pc6_get(c,r.a[0],1,1,value))return false;am_byte(r.d[6],value);
        r.pc=0x4d50e;return true;
    // ---- 4838c (the Set side of C3 48384: TST.B 5684(A5) not 0): ORI.B #1,CCR; RTS.
    case 0x4838c:return pc6_return_carry(c,AnimationCarrySet);
    // ---- 4e572 (the WORD 76 = 0 side of C4 4e564): ADDI.W #20,D0 (bits 16..31 kept); BRA.W 4e57e.
    case 0x4e572:am_word(r.d[0],r.d[0]+0x20U);r.pc=0x4e57e;return true;
    // ---- 4e5b0 (BSR from 4eb5c): ANDI.W #ff,D0; LEA 4e4d2(PC),A4; MOVE.B (A4,D0.W),D0 (fixed ROM BYTE table 4e4d2 + D0.W); BCLR.B D0,5d1e(A5); RTS.
    case 0x4e5b0:
        am_word(r.d[0],r.d[0]&0xffU);r.a[4]=0x4e4d2;if(!am_read(c,am_index(r.a[4],r.d[0]&0xffffU),1,value))return false;am_byte(r.d[0],value);
        if(!pc6_bit(c,am_index(r.a[5],0x5d1e),r.d[0],2,old))return false;return am_return(c);
    // ---- 4e8f8 (the BYTE 5d1f not 0 side of C1 4e8f0): JSR 4f22c(PC) (returns to C1 4e8fc).
    case 0x4e8f8:return am_call(c,0x4f22c,0x4e8fc);
    // ---- 4eb58 (the BEQ.W 4eb58 of C1 4e8fc..4e900): MOVE.B 98(A6),D0; BSR.W 4e5b0 / TST.B 10fd8a.l; BEQ.W 4ed3c (4eb6a: deferred leader).
    case 0x4eb58:if(!pc6_get(c,r.a[6],0x98,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x4e5b0,0x4eb60);
    case 0x4eb60:if(!am_read(c,0x10fd8a,1,value))return false;r.pc=value==0U?0x4ed3c:0x4eb6a;return true;
    // ---- 4ed3c: MOVE.W 76(A6),D0; MOVEQ #3,D1; JSR b0c.l / BSR.W 4e4da / TST.W 76(A6); BNE.W 4ed5e / LEA 10de14.l,A0; BRA.W 4ed64 / LEA 10de1c.l,A0 /
    // JSR e6496.l / TST.W D0; BMI.W 4edf2.
    case 0x4ed3c:return pc6_b0c_call(c,3,0x4ed48);
    case 0x4ed48:return am_call(c,0x4e4da,0x4ed4c);
    case 0x4ed4c:return pc6_word_zero(c,0x76,0x4ed54,0x4ed5e);
    case 0x4ed54:case 0x4eddc:r.a[0]=0x10de14;r.pc=r.pc==0x4ed54?0x4ed64:0x4edec;return true;
    case 0x4ed5e:case 0x4ede6:r.a[0]=0x10de1c;r.pc=r.pc==0x4ed5e?0x4ed64:0x4edec;return true;
    case 0x4ed64:return am_call(c,0xe6496,0x4ed6a);
    case 0x4ed6a:r.pc=(r.d[0]&0x8000U)!=0U?0x4edf2:0x4ed70;return true;
    // MOVE.B #4,9c(A6); MOVE.B #0,62(A6); MOVEA.L #e695a,A0; MOVE.W #0,D0; JSR 28ae.l / BCC.W 4edd4 (C of 28ae) / MOVE.W 76(A6),76(A0); BNE.W 4eda4 /
    // LEA 10de18.l,A1; BRA.W 4edaa / LEA 10de20.l,A1 / MOVE.W 7c(A6),D0; ADDI.W #40,D0; MOVE.W D0,78(A0); MOVE.L A1,7a(A0); MOVE.L #4edc0,(A6).
    case 0x4ed70:
        if(!pc6_put(c,r.a[6],0x9c,1,4) || !pc6_put(c,r.a[6],0x62,1,0))return false;r.a[0]=0xe695a;am_word(r.d[0],0);return am_call(c,0x28ae,0x4ed8c);
    case 0x4ed8c:return pc6_carry(c,0x4edd4,0x4ed90);
    case 0x4ed90:
        if(!pc6_get(c,r.a[6],0x76,2,value) || !pc6_put(c,r.a[0],0x76,2,value))return false;r.pc=value!=0U?0x4eda4:0x4ed9a;return true;
    case 0x4ed9a:r.a[1]=0x10de18;r.pc=0x4edaa;return true;
    case 0x4eda4:r.a[1]=0x10de20;r.pc=0x4edaa;return true;
    case 0x4edaa:
        if(!pc6_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[0],value+0x40U);
        if(!pc6_put(c,r.a[0],0x78,2,r.d[0]) || !pc6_put(c,r.a[0],0x7a,4,r.a[1]))return false;return pc6_install(c,0x4edc0,0x4edc0);
    // 4edc0 (the state): TST.B 62(A6); BNE.W 4edca / RTS / BSR.W 4e4da / JSR 2a0a.l / TST.W 76(A6); BNE.W 4ede6 / LEA 10de14.l,A0; BRA.W 4edec /
    // LEA 10de1c.l,A0 / JSR e6556.l / MOVE.B #5,9c(A6); MOVE.W #1e,96(A6); MOVE.L #4ee04,(A6).
    case 0x4edc0:if(!pc6_get(c,r.a[6],0x62,1,value))return false;r.pc=value!=0U?0x4edca:0x4edc8;return true;
    case 0x4edca:return am_call(c,0x4e4da,0x4edce);
    case 0x4edce:return am_call(c,0x2a0a,0x4edd4);
    case 0x4edd4:return pc6_word_zero(c,0x76,0x4eddc,0x4ede6);
    case 0x4edec:return am_call(c,0xe6556,0x4edf2);
    case 0x4edf2:if(!pc6_put(c,r.a[6],0x9c,1,5) || !pc6_put(c,r.a[6],0x96,2,0x1e))return false;return pc6_install(c,0x4ee04,0x4ee04);
    // 4ee04 (the state): LEA 7db6(A5),A0; ADDA.W 76(A6),A0 (sext); MOVE.B (A0),D0; CMPI.B #0,D0; BEQ.W 4e6f2 / CMPI.B #1,D0; BEQ.W 4e6f2 /
    // TST.B 7d82(A5); BNE.W 4ee34 / MOVE.W 76(A6),D0; JSR 4a974.l / BEQ.W 4ee5c (Z of 4a974, decision 3).
    case 0x4ee04:
        if(!pc6_get(c,r.a[6],0x76,2,value))return false;r.a[0]=am_index(am_index(r.a[5],0x7db6),value);
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x4e6f2:0x4ee16;return true;
    case 0x4ee16:r.pc=(r.d[0]&0xffU)==1U?0x4e6f2:0x4ee1e;return true;
    case 0x4ee1e:if(!pc6_get(c,r.a[5],0x7d82,1,value))return false;r.pc=value!=0U?0x4ee34:0x4ee26;return true;
    case 0x4ee26:return pc6_field_call(c,0x76,0x4a974,0x4ee30);
    // BEQ.W 4ee5c on the Z of the TST.B (A0); RTS that ends 4a974 (4a9b0 / 4a9c6; contract decision 3, controller C1 / player C4 rule): A0 is 10fdb0 /
    // 10fdb1 or 100004 / 100005 and the RTS does not change that BYTE, so it is read again; any other A0 is the checked flag-source error.
    case 0x4ee30:
        if(r.a[0]!=0x10fdb0U && r.a[0]!=0x10fdb1U && r.a[0]!=0x100004U && r.a[0]!=0x100005U)return am_error(c,"unsupported animation player c6 flag source");
        if(!am_read(c,r.a[0],1,value))return false;r.pc=value==0U?0x4ee5c:0x4ee34;return true;
    // TST.W 96(A6); BEQ.W 4ee44 / SUBQ.W #1,96(A6); BRA.W 4ee5c / MOVE.W 76(A6),D0; BTST.B D0,7004(A5); BEQ.W 4ee5c / MOVE.W 76(A6),D0; MOVEQ #0,D1;
    // JSR b0c.l.
    case 0x4ee34:return pc6_word_zero(c,0x96,0x4ee44,0x4ee3c);
    case 0x4ee3c:if(!pc6_get(c,r.a[6],0x96,2,value) || !pc6_put(c,r.a[6],0x96,2,value-1U))return false;r.pc=0x4ee5c;return true;
    case 0x4ee44:
        if(!pc6_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);if(!pc6_bit(c,am_index(r.a[5],0x7004),r.d[0],0,old))return false;
        r.pc=old?0x4ee50:0x4ee5c;return true;
    case 0x4ee50:return pc6_b0c_call(c,0,0x4ee5c);
    // MOVE.B 5d1f(A5),D0; CMP.B 9a(A6),D0; BEQ.W 4ee78 / MOVE.B D0,9a(A6); BEQ.W 4ee78 / LEA 4e370(PC),A0; BSR.W 4e564 / RTS.
    case 0x4ee5c:
        if(!pc6_get(c,r.a[5],0x5d1f,1,value))return false;am_byte(r.d[0],value);if(!pc6_get(c,r.a[6],0x9a,1,other))return false;
        r.pc=value==other?0x4ee78:0x4ee68;return true;
    case 0x4ee68:if(!pc6_put(c,r.a[6],0x9a,1,r.d[0]))return false;r.pc=(r.d[0]&0xffU)==0U?0x4ee78:0x4ee70;return true;
    case 0x4ee70:r.a[0]=0x4e370;return am_call(c,0x4e564,0x4ee78);
    // ---- e6496 (JSR from 4ed64 and the later e50c4 e6a5c; A0 the LONG): LEA 10f02e.l,A1; MOVEQ #1,D0; MOVEQ #1,D1; MOVE.L (A0),D3 / MOVE.L (A1),D4;
    // CMP.L D4,D3; BCC.W e64ae (unsigned D3 >= D4) / MOVE.W D1,D0; ADDQ.W #1,D0 / CMP.L D4,D3; BHI.W e64d2; BCS.W e64c0 (one compare, three ways) /
    // CMPI.W #a,D1; BEQ.W e64cc / ADDA.W #8,A1; ADDQ.W #1,D1; CMPI.W #a,D1; BLE.B e64a2 (signed WORD) / MOVEQ #-1,D0; MOVEQ #-1,D1; RTS.
    case 0xe6496:r.a[1]=0x10f02e;r.d[0]=1;r.d[1]=1;if(!am_read(c,r.a[0],4,r.d[3]))return false;r.pc=0xe64a2;return true;
    case 0xe64a2:if(!am_read(c,r.a[1],4,r.d[4]))return false;r.pc=r.d[3]>=r.d[4]?0xe64ae:0xe64aa;return true;
    case 0xe64aa:am_word(r.d[0],r.d[1]+1U);r.pc=0xe64ae;return true;
    case 0xe64ae:r.pc=r.d[3]>r.d[4]?0xe64d2:(r.d[3]<r.d[4]?0xe64c0:0xe64b8);return true;
    case 0xe64b8:r.pc=(r.d[1]&0xffffU)==0xaU?0xe64cc:0xe64c0;return true;
    case 0xe64c0:
        r.a[1]+=8U;am_word(r.d[1],r.d[1]+1U);r.pc=static_cast<std::int32_t>(am_extend_word(r.d[1]))<=0xa?0xe64a2:0xe64cc;return true;
    case 0xe64cc:r.d[0]=0xffffffffU;r.d[1]=0xffffffffU;return am_return(c);
    // SUBQ.W #1,D1; CMPA.L #10de14,A0; BNE.W e64f4 / TST.B 5e13(A5); BEQ.W e64f4 / MOVE.L (A0),D3; CMP.L 5e1c(A5),D3; BCC.W e64f4 / ADDQ.W #1,D0;
    // ADDQ.W #1,D1 / CMPA.L #10de1c,A0; BNE.W e6514 / TST.B 5e12(A5); BEQ.W e6514 / MOVE.L (A0),D3; CMP.L 5e14(A5),D3; BCC.W e6514 / ADDQ.W #1,D0;
    // ADDQ.W #1,D1 / RTS.
    case 0xe64d2:am_word(r.d[1],r.d[1]-1U);r.pc=r.a[0]==0x10de14U?0xe64de:0xe64f4;return true;
    case 0xe64de:case 0xe64fe:
        if(!pc6_get(c,r.a[5],r.pc==0xe64de?0x5e13U:0x5e12U,1,value))return false;
        r.pc=value==0U?(r.pc==0xe64de?0xe64f4:0xe6514):(r.pc==0xe64de?0xe64e6:0xe6506);return true;
    case 0xe64e6:case 0xe6506:
        if(!am_read(c,r.a[0],4,r.d[3]) || !pc6_get(c,r.a[5],r.pc==0xe64e6?0x5e1cU:0x5e14U,4,value))return false;
        r.pc=r.d[3]>=value?(r.pc==0xe64e6?0xe64f4:0xe6514):(r.pc==0xe64e6?0xe64f0:0xe6510);return true;
    case 0xe64f0:pc6_rank_up(r);r.pc=0xe64f4;return true;
    case 0xe64f4:r.pc=r.a[0]==0x10de1cU?0xe64fe:0xe6514;return true;
    case 0xe6510:pc6_rank_up(r);r.pc=0xe6514;return true;
    default:return am_error(c,"unsupported animation player c6 PC");
    }
}
}
