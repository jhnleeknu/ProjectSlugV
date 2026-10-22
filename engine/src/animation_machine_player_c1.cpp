#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc1_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc1_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// TST.B d16(An) / MOVE.B d16(An),...; BEQ zero_pc (fall through to other_pc).
bool pc1_byte_zero(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc1_get(c,base,displacement,1,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// TST.B 5d1f(A5); BEQ zero_pc (fall through to other_pc).
bool pc1_gate(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    return pc1_byte_zero(c,c.s.a[5],0x5d1f,zero_pc,other_pc);
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc1_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c1 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// Z of the TST.B -7699(A5) that ended ca50 (RTS ca54), recomputed from that BYTE (contract decision 3): the RTS reads only the stack and A5 is
// unchanged, so the BYTE is the one ca50 tested.  The address must be work RAM (100000..1fffff): a second read of a device would not be the original.
bool pc1_flag_zero(AnimationMachineContext& c,bool& zero) {
    const std::uint32_t address=am_index(c.s.a[5],0x8967U);
    if((address&0xffffffU)<0x100000U || (address&0xffffffU)>=0x200000U)return am_error(c,"unsupported animation player c1 flag source");
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    zero=value==0U;return true;
}
// SNE.B a1(A6) on the Z of ca50 (BYTE := ff when Z = 0, else 0); then BEQ / BNE on the same Z: zero_pc when Z = 1, else other_pc.
bool pc1_sne(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    bool zero=false;if(!pc1_flag_zero(c,zero))return false;
    if(!pc1_put(c,c.s.a[6],0xa1,1,zero?0U:0xffU))return false;
    c.s.pc=zero?zero_pc:other_pc;return true;
}
// BSET.B / BCLR.B Dn,5d1e(A5): the bit number is Dn modulo 8 (memory operand); returns the old bit (the Z of the instruction is old = 0).
bool pc1_slot_bit(AnimationMachineContext& c,bool set,bool& old) {
    std::uint32_t value=0;if(!pc1_get(c,c.s.a[5],0x5d1e,1,value))return false;
    const std::uint32_t mask=1U<<(c.s.d[0]&7U);
    old=(value&mask)!=0U;
    return pc1_put(c,c.s.a[5],0x5d1e,1,set?(value|mask):(value&~mask));
}
// LEA table(PC),A4; MOVE.B (A4,D0.W),D0 (ROM BYTE at table + sext(D0.W); D0 bits 8..31 kept).
bool pc1_table(AnimationMachineContext& c,std::uint32_t table) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[4]=table;
    if(!am_read(c,am_index(r.a[4],r.d[0]&0xffffU),1,value))return false;am_byte(r.d[0],value);return true;
}
// MOVE.W 76(A6),D0 (D0 bits 16..31 kept).
bool pc1_slot_index(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!pc1_get(c,c.s.a[6],0x76,2,value))return false;am_word(c.s.d[0],value);return true;
}
// MOVE.W 78(A6),D0 (1d1fa / 1d20c: the slot index of the player object; D0 bits 16..31 kept).
bool pc1_slot_index_78(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!pc1_get(c,c.s.a[6],0x78,2,value))return false;am_word(c.s.d[0],value);return true;
}
// MOVE.L #v,(A6): the next PC is v (installed value entered at once).
bool pc1_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!pc1_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVE.L #record,78(A6) and the five WORDs 7c..84 of the slot (4e6a2 / 4e6cc).
bool pc1_slot_words(AnimationMachineContext& c,std::uint32_t record,const std::uint32_t* words) {
    if(!pc1_put(c,c.s.a[6],0x78,4,record))return false;
    for(unsigned int i=0;i<5U;++i)if(!pc1_put(c,c.s.a[6],0x7cU+2U*i,2,words[i]))return false;
    c.s.pc=0x4e6f2;return true;
}
// MOVE.W #id,D0; MOVE.B #1,D1; JSR 8ebe.l (4f358 4f366 4f374 4f382).
bool pc1_light(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);am_byte(c.s.d[1],1);return am_call(c,0x8ebe,return_pc);
}
// MOVE.B field(A6),D0; CMPI.B #k,78(A6); BNE.W other_pc (fall through to equal_pc).
bool pc1_mark(AnimationMachineContext& c,std::uint32_t field,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!pc1_get(c,r.a[6],field,1,value))return false;am_byte(r.d[0],value);
    if(!pc1_get(c,r.a[6],0x78,1,value))return false;
    r.pc=value!=k?other_pc:equal_pc;return true;
}
// BTST.B #bit,5d1e(A5); BNE.W set_pc (fall through to clear_pc).
bool pc1_slot_test(AnimationMachineContext& c,unsigned int bit,std::uint32_t clear_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!pc1_get(c,c.s.a[5],0x5d1e,1,value))return false;
    c.s.pc=(value&(1U<<bit))!=0U?set_pc:clear_pc;return true;
}
// MOVEA.L c(A6),A0; CMPI.B #1,9c(A0); BEQ.W equal_pc (fall through to the JMP 2a00 block other_pc).
bool pc1_parent_state(AnimationMachineContext& c,std::uint32_t equal_pc,std::uint32_t other_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!pc1_get(c,r.a[6],0xc,4,r.a[0]) || !pc1_get(c,r.a[0],0x9c,1,value))return false;
    r.pc=value==1U?equal_pc:other_pc;return true;
}
// MOVEA.L c(A6),A0; TST.B a1(A0); BEQ.W zero_pc (fall through to other_pc).
bool pc1_parent_a1(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    AnimationMachineState& r=c.s;
    if(!pc1_get(c,r.a[6],0xc,4,r.a[0]))return false;return pc1_byte_zero(c,r.a[0],0xa1,zero_pc,other_pc);
}
const std::uint32_t PC1_P1_WORDS[5]={0x7043,0x7043,0x7064,0x7023,0x7143};
const std::uint32_t PC1_P2_WORDS[5]={0x72c3,0x73c3,0x73c4,0x74a3,0x72c3};
}
// Player C1 (139 block starts, contract docs/analysis/animation-machine-player-c1-contract.md; area C plan unit C1): the player slot callback
// 4e68e (the controller C2 install 4e1cc; WORD 76 = 0 / 1, >= 2 reaches the TRAP #15 4e69a outside the routing) with its states 4e732 4e7ec 4e83c and
// the player creation 4e8f0..4e962 / 4e94e (LEA 1d1f4; JSR 2a28), the 28ae child 4f2e0 with its states 4f32e / 4f396 (bank-window LONG 2001e4),
// the slot helpers 4e0f6 4e4da 4e58a 4e5c2 (BYTE table 4e4d2 / 4e4d6 in the fixed ROM), the player object entry 1d1f4 / 1d20c, the helpers ca3a
// ca50 48346 (Clear side 48368) 49bca and the leaf b7a28.  C: the consumers 1d21c (BCS, C of 48346), 4e808 (SCS, C of ca32; the CMP.B after it makes
// the C Unknown) and 4e958 (BCC, C of 289e) read a known C or fail; 48368 (ANDI.B #fe,CCR; RTS) returns C Clear.  Z: 4e7da 4e7f2 4e842 (SNE.B + BEQ /
// BNE) recompute the Z of ca50 from BYTE -7699(A5) (work RAM only, contract decision 3).  MOVE.L #v,(A6) enters v at once (v is the next PC).
bool animation_player_c1_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool old=false;
    switch(r.pc) {
    // ---- helpers in the area E address range (contract decision 6 of the plan).
    case 0xca3a:                                                                                          // MOVE.W -76a0(A5),-76a2(A5); RTS.
        if(!pc1_get(c,r.a[5],0x8960,2,value) || !pc1_put(c,r.a[5],0x895e,2,value))return false;return am_return(c);
    case 0xca50:if(!pc1_get(c,r.a[5],0x8967,1,value))return false;return am_return(c);                   // TST.B -7699(A5); RTS (Z read by the caller).
    // ---- player object 1d1f4 (installed by 4e91c / 1bd9c / 47772).
    case 0x1d1f4:return am_call(c,0x2a0a,0x1d1fa);                                                        // JSR 2a0a.l.
    case 0x1d1fa:if(!pc1_slot_index_78(c))return false;return am_call(c,0x49be0,0x1d204);                // MOVE.W 78(A6),D0; JSR 49be0.l.
    case 0x1d204:if(!am_write(c,r.a[0],4,0))return false;return pc1_install(c,0x1d20c);                 // CLR.L (A0); MOVE.L #1d20c,(A6).
    case 0x1d20c:if(!pc1_slot_index_78(c))return false;return am_call(c,0x49bca,0x1d216);                // MOVE.W 78(A6),D0; JSR 49bca.l.
    case 0x1d216:return am_call(c,0x48346,0x1d21c);                                                       // JSR 48346.l.
    case 0x1d21c:return pc1_carry(c,0x1d220,0x1d222);                                                     // BCS.W 1d222 (C returned by 48346).
    case 0x1d220:case 0x4e536:case 0x4e7a2:case 0x4e82a:case 0x4e8d4:case 0x4f356:case 0x4f4b8:return am_return(c);   // RTS.
    // ---- 48346: BTST.B #1,5683(A5); BEQ.W 48368 (the Set side 48350 is unit C3).
    case 0x48346:if(!pc1_get(c,r.a[5],0x5683,1,value))return false;r.pc=(value&2U)==0U?0x48368:0x48350;return true;
    case 0x48368:r.carry=AnimationCarryClear;return am_return(c);                                       // ANDI.B #fe,CCR; RTS (returns C Clear).
    // ---- 49bca: LEA 5726(A5),A0; ANDI.W #1,D0; BEQ.W 49bda / LEA 572c(A5),A0; CLR.W 4(A0); RTS.
    case 0x49bca:r.a[0]=am_index(r.a[5],0x5726);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&0xffffU)==0U?0x49bda:0x49bd6;return true;
    case 0x49bd6:r.a[0]=am_index(r.a[5],0x572c);r.pc=0x49bda;return true;
    case 0x49bda:if(!pc1_put(c,r.a[0],4,2,0))return false;return am_return(c);
    // ---- 4e0f6: ANDI.W #1,D0; ADD.W D0,D0; LEA 5d22(A5),A0; MOVE.W #0,(A0,D0.W); LEA 5d26(A5),A0; MOVE.W #0,(A0,D0.W); RTS.
    case 0x4e0f6:
        am_word(r.d[0],r.d[0]&1U);am_word(r.d[0],r.d[0]+r.d[0]);
        r.a[0]=am_index(r.a[5],0x5d22);if(!pc1_put(c,r.a[0],r.d[0]&0xffffU,2,0))return false;
        r.a[0]=am_index(r.a[5],0x5d26);if(!pc1_put(c,r.a[0],r.d[0]&0xffffU,2,0))return false;return am_return(c);
    case 0x4e4da:return pc1_gate(c,0x4e536,0x4e4e2);                                                      // TST.B 5d1f(A5); BEQ.W 4e536 (4e4e2 is C4).
    // ---- slot allocation 4e58a: ANDI.W #ff,D0; LEA 4e4d2(PC),A4; MOVE.B (A4,D0.W),D0.
    case 0x4e58a:am_word(r.d[0],r.d[0]&0xffU);if(!pc1_table(c,0x4e4d2))return false;r.pc=0x4e596;return true;
    case 0x4e596:if(!pc1_slot_bit(c,true,old))return false;r.pc=old?0x4e59e:0x4e5a6;return true;        // BSET.B D0,5d1e(A5); BEQ.W 4e5a6.
    case 0x4e59e:am_word(r.d[0],r.d[0]+1U);am_word(r.d[0],r.d[0]&3U);r.pc=0x4e596;return true;          // ADDQ.W #1,D0; ANDI.W #3,D0; BRA.B 4e596.
    case 0x4e5a6:case 0x4e5de:if(!pc1_table(c,0x4e4d6))return false;return am_return(c);                // LEA 4e4d6(PC),A4; MOVE.B (A4,D0.W),D0; RTS.
    // ---- slot move 4e5c2: ANDI.W #ff,D0; LEA 4e4d2(PC),A4; MOVE.B (A4,D0.W),D0; BCLR.B D0,5d1e(A5).
    case 0x4e5c2:am_word(r.d[0],r.d[0]&0xffU);if(!pc1_table(c,0x4e4d2) || !pc1_slot_bit(c,false,old))return false;r.pc=0x4e5d2;return true;
    // ADD.B D1,D0; ANDI.W #3,D0; BSET.B D0,5d1e(A5); BNE.B 4e5d2.
    case 0x4e5d2:am_byte(r.d[0],r.d[0]+r.d[1]);am_word(r.d[0],r.d[0]&3U);if(!pc1_slot_bit(c,true,old))return false;r.pc=old?0x4e5d2:0x4e5de;return true;
    // ---- slot callback 4e68e: MOVE.W 76(A6),D0; CMPI.W #2,D0; BCS.W 4e69c (fall through to the TRAP #15 4e69a, outside the routing).
    case 0x4e68e:if(!pc1_slot_index(c))return false;r.pc=(r.d[0]&0xffffU)<2U?0x4e69c:0x4e69a;return true;
    case 0x4e69c:r.pc=(r.d[0]&0xffffU)!=0U?0x4e6cc:0x4e6a2;return true;                                 // TST.W D0; BNE.W 4e6cc.
    case 0x4e6a2:return pc1_slot_words(c,0x100cb8,PC1_P1_WORDS);                                         // slot 0: record 100cb8 (BRA.W 4e6f2).
    case 0x4e6cc:return pc1_slot_words(c,0x100da8,PC1_P2_WORDS);                                         // slot 1: record 100da8.
    // MOVE.B #0,9c(A6); MOVE.W 76(A6),D0; JSR e62ec.l.
    case 0x4e6f2:if(!pc1_put(c,r.a[6],0x9c,1,0) || !pc1_slot_index(c))return false;return am_call(c,0xe62ec,0x4e702);
    case 0x4e702:r.d[0]=0;if(!pc1_get(c,r.a[6],0x76,2,value))return false;r.pc=value==0U?0x4e70e:0x4e70c;return true; // MOVEQ #0,D0; TST.W 76(A6).
    case 0x4e70c:r.d[0]=3;r.pc=0x4e70e;return true;                                                       // MOVEQ #3,D0.
    // MOVE.B D0,98(A6); MOVE.W 76(A6),D0; JSR 4e0f6(PC).
    case 0x4e70e:if(!pc1_put(c,r.a[6],0x98,1,r.d[0]) || !pc1_slot_index(c))return false;return am_call(c,0x4e0f6,0x4e71a);
    case 0x4e71a:if(!pc1_slot_index(c))return false;return am_call(c,0xe62ec,0x4e724);                   // MOVE.W 76(A6),D0; JSR e62ec.l.
    case 0x4e724:return am_call(c,0x4e4da,0x4e728);                                                       // BSR.W 4e4da.
    case 0x4e728:if(!pc1_slot_index(c))return false;return pc1_install(c,0x4e732);                       // MOVE.W 76(A6),D0; MOVE.L #4e732,(A6).
    // ---- 4e732 (installed): LEA 7db6(A5),A0; ADDA.W 76(A6),A0; MOVE.B (A0),D0; CMPI.B #1,D0; BEQ.W 4e7a4.
    case 0x4e732:
        if(!pc1_get(c,r.a[6],0x76,2,value))return false;r.a[0]=am_index(am_index(r.a[5],0x7db6),value);
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[0],value);r.pc=(r.d[0]&0xffU)==1U?0x4e7a4:0x4e744;return true;
    // MOVE.W 76(A6),D0; BTST.B D0,7004(A5) (bit D0 mod 8); SEQ.B a1(A6); TST.B 5d1f(A5); BEQ.W 4e7a2 (4e758 is C4).
    case 0x4e744:
        if(!pc1_slot_index(c) || !pc1_get(c,r.a[5],0x7004,1,value))return false;
        if(!pc1_put(c,r.a[6],0xa1,1,(value&(1U<<(r.d[0]&7U)))==0U?0xffU:0U))return false;return pc1_gate(c,0x4e7a2,0x4e758);
    case 0x4e7a4:if(!pc1_get(c,r.a[6],0x98,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x4e58a,0x4e7ac); // MOVE.B 98(A6),D0; BSR.
    // MOVE.B D0,98(A6); CMPI.B #f,5d1e(A5); BEQ.W 4e8d6.
    case 0x4e7ac:
        if(!pc1_put(c,r.a[6],0x98,1,r.d[0]) || !pc1_get(c,r.a[5],0x5d1e,1,value))return false;r.pc=value==0xfU?0x4e8d6:0x4e7ba;return true;
    case 0x4e7ba:r.a[0]=0x4f2e0;am_word(r.d[0],0);return am_call(c,0x28ae,0x4e7ca);                     // MOVEA.L #4f2e0,A0; MOVE.W #0,D0; JSR 28ae.l.
    case 0x4e7ca:if(!pc1_put(c,r.a[6],0x9c,1,1))return false;return am_call(c,0x4e4da,0x4e7d4);          // MOVE.B #1,9c(A6); BSR.W 4e4da.
    case 0x4e7d4:return am_call(c,0xca50,0x4e7da);                                                        // JSR ca50.l.
    case 0x4e7da:return pc1_sne(c,0x4e82c,0x4e7e2);                                                       // SNE.B a1(A6); BEQ.W 4e82c (Z of ca50).
    case 0x4e7e2:return am_call(c,0x4e4da,0x4e7e6);                                                       // BSR.W 4e4da.
    case 0x4e7e6:return pc1_install(c,0x4e7ec);                                                           // MOVE.L #4e7ec,(A6).
    case 0x4e7ec:return am_call(c,0xca50,0x4e7f2);                                                        // JSR ca50.l.
    case 0x4e7f2:return pc1_sne(c,0x4e82c,0x4e7fa);                                                       // SNE.B a1(A6); BEQ.W 4e82c (Z of ca50).
    case 0x4e7fa:return pc1_gate(c,0x4e82a,0x4e802);                                                      // TST.B 5d1f(A5); BEQ.W 4e82a.
    case 0x4e802:return am_call(c,0xca32,0x4e808);                                                        // JSR ca32.l.
    // SCS.B D0 (C of ca32); CMP.B 9a(A6),D0; BEQ.W 4e82a.  The CMP.B rewrites C: the C after the block is Unknown.
    case 0x4e808:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"player c1 caller requires known carry");
        am_byte(r.d[0],r.carry==AnimationCarrySet?0xffU:0U);r.carry=AnimationCarryUnknown;
        if(!pc1_get(c,r.a[6],0x9a,1,value))return false;r.pc=(r.d[0]&0xffU)==value?0x4e82a:0x4e812;return true;
    case 0x4e812:if(!pc1_put(c,r.a[6],0x9a,1,r.d[0]))return false;r.pc=(r.d[0]&0xffU)!=0U?0x4e826:0x4e81a;return true; // MOVE.B D0,9a(A6); BNE.W.
    case 0x4e81a:r.a[0]=0x4e34c;return am_call(c,0x4e564,0x4e822);                                      // LEA 4e34c(PC),A0; BSR.W 4e564 (C4).
    case 0x4e822:r.pc=0x4e82a;return true;                                                                // BRA.W 4e82a.
    case 0x4e826:return am_call(c,0x4e538,0x4e82a);                                                       // BSR.W 4e538 (C4).
    case 0x4e82c:return am_call(c,0xca3a,0x4e832);                                                        // JSR ca3a.l.
    case 0x4e832:return am_call(c,0x4e4da,0x4e836);                                                       // BSR.W 4e4da.
    case 0x4e836:return pc1_install(c,0x4e83c);                                                           // MOVE.L #4e83c,(A6).
    case 0x4e83c:return am_call(c,0xca50,0x4e842);                                                        // JSR ca50.l.
    case 0x4e842:return pc1_sne(c,0x4e848,0x4e7e2);                                                       // SNE.B a1(A6); BNE.B 4e7e2 (Z of ca50).
    case 0x4e848:return am_call(c,0xca42,0x4e84e);                                                        // JSR ca42.l.
    case 0x4e84e:if(!am_read(c,r.a[0],2,value))return false;r.pc=value==0U?0x4e8d6:0x4e854;return true; // TST.W (A0); BEQ.W 4e8d6.
    // LEA 104ca8.l,A0; TST.W 76(A6); BEQ.W 4e868 / LEA 104cae.l,A0.
    case 0x4e854:r.a[0]=0x104ca8;if(!pc1_get(c,r.a[6],0x76,2,value))return false;r.pc=value==0U?0x4e868:0x4e862;return true;
    case 0x4e862:r.a[0]=0x104cae;r.pc=0x4e868;return true;
    // MOVE.B 4(A0),D0; BTST.B #4,D0; BNE.W 4e8d6.
    case 0x4e868:if(!pc1_get(c,r.a[0],4,1,value))return false;am_byte(r.d[0],value);r.pc=(r.d[0]&0x10U)!=0U?0x4e8d6:0x4e874;return true;
    case 0x4e874:r.d[1]=0xffffffffU;r.pc=(r.d[0]&4U)!=0U?0x4e888:0x4e87e;return true;                  // MOVEQ #-1,D1; BTST.B #2,D0; BNE.W 4e888.
    case 0x4e87e:r.d[1]=1;r.pc=(r.d[0]&8U)==0U?0x4e894:0x4e888;return true;                             // MOVEQ #1,D1; BTST.B #3,D0; BEQ.W 4e894.
    case 0x4e888:if(!pc1_get(c,r.a[6],0x98,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x4e5c2,0x4e890); // MOVE.B 98(A6),D0; BSR.
    case 0x4e890:if(!pc1_put(c,r.a[6],0x98,1,r.d[0]))return false;r.pc=0x4e894;return true;             // MOVE.B D0,98(A6).
    // MOVE.B 5d1f(A5),9a(A6); BEQ.W 4e8d4.
    case 0x4e894:if(!pc1_get(c,r.a[5],0x5d1f,1,value) || !pc1_put(c,r.a[6],0x9a,1,value))return false;r.pc=value==0U?0x4e8d4:0x4e89e;return true;
    // MOVE.W 7c(A6),D0; ADDI.W #20,D0; TST.W 76(A6); BEQ.W 4e8b2 / ADDI.W #1a0,D0.
    case 0x4e89e:
        if(!pc1_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[0],value+0x20U);
        if(!pc1_get(c,r.a[6],0x76,2,value))return false;r.pc=value==0U?0x4e8b2:0x4e8ae;return true;
    case 0x4e8ae:am_word(r.d[0],r.d[0]+0x1a0U);r.pc=0x4e8b2;return true;
    case 0x4e8b2:return am_call(c,0xca42,0x4e8b8);                                                        // JSR ca42.l.
    case 0x4e8b8:if(!am_read(c,r.a[0],1,value))return false;r.pc=value>=0xaU?0x4e8d4:0x4e8c0;return true; // CMPI.B #a,(A0); BCC.W 4e8d4.
    // LEA e84c8.l,A1; MOVE.W #431,D1; MOVEQ #0,D3; MOVEQ #1,D4; JSR 3670.l.
    case 0x4e8c0:r.a[1]=0xe84c8;am_word(r.d[1],0x431);r.d[3]=0;r.d[4]=1;return am_call(c,0x3670,0x4e8d4);
    // MOVE.B 7d88(A5),99(A6); BNE.W 4e8e6 (C6) / MOVE.B #1,99(A6) (fall through to 4e8e6).
    case 0x4e8d6:if(!pc1_get(c,r.a[5],0x7d88,1,value) || !pc1_put(c,r.a[6],0x99,1,value))return false;r.pc=value!=0U?0x4e8e6:0x4e8e0;return true;
    case 0x4e8e0:if(!pc1_put(c,r.a[6],0x99,1,1))return false;r.pc=0x4e8e6;return true;
    // ---- player creation.
    case 0x4e8f0:return pc1_gate(c,0x4e8fc,0x4e8f8);                                                      // TST.B 5d1f(A5); BEQ.W 4e8fc (4e8f8 is C6).
    case 0x4e8fc:return pc1_byte_zero(c,r.a[6],0x99,0x4eb58,0x4e904);                                    // TST.B 99(A6); BEQ.W 4eb58 (C6).
    case 0x4e904:if(!pc1_put(c,r.a[6],0x9c,1,2))return false;return am_call(c,0x4e4da,0x4e90e);          // MOVE.B #2,9c(A6); BSR.W 4e4da.
    // SUBQ.B #1,99(A6); JSR 48398.l.
    case 0x4e90e:if(!pc1_get(c,r.a[6],0x99,1,value) || !pc1_put(c,r.a[6],0x99,1,value-1U))return false;return am_call(c,0x48398,0x4e918);
    // MOVEA.L 78(A6),A0; LEA 1d1f4.l,A1; JSR 2a28.l.
    case 0x4e918:if(!pc1_get(c,r.a[6],0x78,4,r.a[0]))return false;r.a[1]=0x1d1f4;return am_call(c,0x2a28,0x4e928);
    // MOVEQ #0,D0; MOVE.B 98(A6),D0; MOVE.W D0,76(A0); MOVE.W 76(A6),D0; MOVE.W D0,78(A0); JSR 1bd2e.l.
    case 0x4e928:
        r.d[0]=0;if(!pc1_get(c,r.a[6],0x98,1,value))return false;am_byte(r.d[0],value);if(!pc1_put(c,r.a[0],0x76,2,r.d[0]))return false;
        if(!pc1_slot_index(c) || !pc1_put(c,r.a[0],0x78,2,r.d[0]))return false;return am_call(c,0x1bd2e,0x4e940);
    // CLR.B 9a(A6); CLR.B a1(A6); MOVE.L #4e94e,(A6).
    case 0x4e940:if(!pc1_put(c,r.a[6],0x9a,1,0) || !pc1_put(c,r.a[6],0xa1,1,0))return false;return pc1_install(c,0x4e94e);
    case 0x4e94e:if(!pc1_get(c,r.a[6],0x78,4,r.a[0]))return false;return am_call(c,0x289e,0x4e958);    // MOVEA.L 78(A6),A0; JSR 289e.l.
    case 0x4e958:return pc1_carry(c,0x4e8e6,0x4e95a);                                                     // BCC.B 4e8e6 (C returned by 289e).
    case 0x4e95a:return pc1_byte_zero(c,r.a[6],0x9a,0x4e97e,0x4e962);                                    // TST.B 9a(A6); BEQ.W 4e97e (4e962 is C4).
    // MOVE.B 5d1f(A5),D0; BEQ.W 4eb50 (4e986 is C4).
    case 0x4e97e:if(!pc1_get(c,r.a[5],0x5d1f,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x4eb50:0x4e986;return true;
    // MOVE.B 5d1f(A5),9a(A6); RTS.
    case 0x4eb50:if(!pc1_get(c,r.a[5],0x5d1f,1,value) || !pc1_put(c,r.a[6],0x9a,1,value))return false;return am_return(c);
    // ---- 28ae child 4f2e0: MOVE.W #22b,20(A6); MOVE.L 2001e4.l,22(A6) (bank window); MOVE.W #1d0,46(A6); MOVEA.L #4f4ba,A1; MOVE.W #100,D0;
    // JSR 49f8c.l.
    case 0x4f2e0:
        if(!pc1_put(c,r.a[6],0x20,2,0x22b) || !am_read(c,0x2001e4,4,value) || !pc1_put(c,r.a[6],0x22,4,value) || !pc1_put(c,r.a[6],0x46,2,0x1d0))return false;
        r.a[1]=0x4f4ba;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x4f304);
    // MOVE.B #ff,79(A6) .. 7c(A6); MOVE.W #ffff,1e(A6) (fall through to 4f322).
    case 0x4f304:
        for(unsigned int i=0;i<4U;++i)if(!pc1_put(c,r.a[6],0x79U+i,1,0xff))return false;
        if(!pc1_put(c,r.a[6],0x1e,2,0xffff))return false;r.pc=0x4f322;return true;
    case 0x4f322:return am_call(c,0x8ff4,0x4f328);                                                        // JSR 8ff4.l.
    case 0x4f328:return pc1_install(c,0x4f32e);                                                           // MOVE.L #4f32e,(A6).
    case 0x4f32e:return pc1_parent_state(c,0x4f342,0x4f33c);                                              // parent BYTE 9c = 1 -> 4f342.
    case 0x4f33c:case 0x4f3a4:r.pc=0x2a00;return true;                                                    // JMP 2a00.l.
    case 0x4f342:return pc1_gate(c,0x4f356,0x4f34a);                                                      // TST.B 5d1f(A5); BEQ.W 4f356.
    case 0x4f34a:return pc1_parent_a1(c,0x4f358,0x4f356);                                                 // parent BYTE a1 = 0 -> 4f358.
    case 0x4f358:return pc1_light(c,0x7a,0x4f366);
    case 0x4f366:return pc1_light(c,0x7c,0x4f374);
    case 0x4f374:return pc1_light(c,0x7e,0x4f382);
    case 0x4f382:return pc1_light(c,0x80,0x4f390);
    case 0x4f390:return pc1_install(c,0x4f396);                                                           // MOVE.L #4f396,(A6).
    case 0x4f396:return pc1_parent_state(c,0x4f3aa,0x4f3a4);                                              // parent BYTE 9c = 1 -> 4f3aa.
    case 0x4f3aa:return pc1_gate(c,0x4f322,0x4f3b2);                                                      // TST.B 5d1f(A5); BEQ.W 4f322.
    case 0x4f3b2:return pc1_parent_a1(c,0x4f3be,0x4f322);                                                 // parent BYTE a1 != 0 -> 4f322.
    // MOVEQ #0,D0; MOVE.B 98(A0),D0; LEA 4e4d2(PC),A4; MOVE.B (A4,D0.W),78(A6); JSR 16ed2.l.
    case 0x4f3be:
        r.d[0]=0;if(!pc1_get(c,r.a[0],0x98,1,value))return false;am_byte(r.d[0],value);r.a[4]=0x4e4d2;
        if(!am_read(c,am_index(r.a[4],r.d[0]&0xffffU),1,value) || !pc1_put(c,r.a[6],0x78,1,value))return false;return am_call(c,0x16ed2,0x4f3d4);
    // the four slot marks: MOVE.B 19+k(A6),D0; CMPI.B #k,78(A6); BNE.W / BTST.B #k,5d1e(A5); MOVE.W #id,D1; JSR 8d34.l.
    case 0x4f3d4:return pc1_mark(c,0x19,0,0x4f3e2,0x4f3ea);
    case 0x4f406:return pc1_mark(c,0x1a,1,0x4f414,0x4f41c);
    case 0x4f438:return pc1_mark(c,0x1b,2,0x4f446,0x4f44e);
    case 0x4f46a:return pc1_mark(c,0x1c,3,0x4f478,0x4f480);
    case 0x4f3ea:return pc1_slot_test(c,0,0x4f3f4,0x4f3fc);
    case 0x4f41c:return pc1_slot_test(c,1,0x4f426,0x4f42e);
    case 0x4f44e:return pc1_slot_test(c,2,0x4f458,0x4f460);
    case 0x4f480:return pc1_slot_test(c,3,0x4f48a,0x4f492);
    case 0x4f3e2:am_word(r.d[1],0x79);r.pc=0x4f400;return true;                                          // MOVE.W #id,D1; BRA.W (or fall through).
    case 0x4f3f4:am_word(r.d[1],0x7a);r.pc=0x4f400;return true;
    case 0x4f3fc:am_word(r.d[1],0x81);r.pc=0x4f400;return true;
    case 0x4f414:am_word(r.d[1],0x7b);r.pc=0x4f432;return true;
    case 0x4f426:am_word(r.d[1],0x7c);r.pc=0x4f432;return true;
    case 0x4f42e:am_word(r.d[1],0x82);r.pc=0x4f432;return true;
    case 0x4f446:am_word(r.d[1],0x7d);r.pc=0x4f464;return true;
    case 0x4f458:am_word(r.d[1],0x7e);r.pc=0x4f464;return true;
    case 0x4f460:am_word(r.d[1],0x83);r.pc=0x4f464;return true;
    case 0x4f478:am_word(r.d[1],0x7f);r.pc=0x4f496;return true;
    case 0x4f48a:am_word(r.d[1],0x80);r.pc=0x4f496;return true;
    case 0x4f492:am_word(r.d[1],0x84);r.pc=0x4f496;return true;
    case 0x4f400:return am_call(c,0x8d34,0x4f406);                                                        // JSR 8d34.l.
    case 0x4f432:return am_call(c,0x8d34,0x4f438);
    case 0x4f464:return am_call(c,0x8d34,0x4f46a);
    case 0x4f496:return am_call(c,0x8d34,0x4f49c);
    case 0x4f49c:return am_call(c,0x49fc6,0x4f4a2);                                                       // JSR 49fc6.l (C not read).
    // ADDI.W #2a,76(A6); CMPI.W #600,76(A6); BCS.W 4f4b8 (unsigned new WORD < 600) / SUBI.W #600,76(A6).
    case 0x4f4a2:
        if(!pc1_get(c,r.a[6],0x76,2,value) || !pc1_put(c,r.a[6],0x76,2,value+0x2aU))return false;r.pc=((value+0x2aU)&0xffffU)<0x600U?0x4f4b8:0x4f4b2;return true;
    case 0x4f4b2:if(!pc1_get(c,r.a[6],0x76,2,value) || !pc1_put(c,r.a[6],0x76,2,value-0x600U))return false;r.pc=0x4f4b8;return true;
    // ---- b7a28: TST.B D0; BNE.W b7a48 (fall through to b7a2e).
    case 0xb7a28:r.pc=(r.d[0]&0xffU)!=0U?0xb7a48:0xb7a2e;return true;
    default:
        return am_error(c,"unsupported animation player c1 PC");
    }
}
}
