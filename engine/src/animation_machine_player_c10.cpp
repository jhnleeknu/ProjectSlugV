#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc10_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc10_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR / BCHG #bit,d16(A6) (a memory operand: BYTE, bit modulo 8). op 0 tests, 1 sets, 2 clears, 3 changes; old is the bit before
// (the Z of the instruction is old = 0).
bool pc10_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!pc10_get(c,c.s.a[6],displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    std::uint32_t next=value&~mask;
    if(op==1U || (op==3U && !old))next=value|mask;
    return pc10_put(c,c.s.a[6],displacement,1,next);
}
// BTST #bit,d16(A6); BEQ.W zero_pc (the bit clear) / other_pc.
bool pc10_field_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t other_pc) {
    bool old=false;if(!pc10_bit(c,displacement,bit,0,old))return false;
    c.s.pc=old?other_pc:zero_pc;return true;
}
// BTST #bit,D0 (a data register operand: the LONG bit, bit < 32); BEQ.W zero_pc / other_pc.
void pc10_input_bit(AnimationMachineState& r,unsigned int bit,std::uint32_t zero_pc,std::uint32_t other_pc) {
    r.pc=(r.d[0]&(1U<<bit))==0U?zero_pc:other_pc;
}
// TST.B / CMPI.B #k,d16(A6); BEQ / BNE: equal_pc when the BYTE is k, else other_pc.
bool pc10_byte_is(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc10_get(c,c.s.a[6],displacement,1,value))return false;
    c.s.pc=value==k?equal_pc:other_pc;return true;
}
// MOVE.W #mask,D1; AND.W D0,D1 (WORD: D1 bits 16..31 kept); zero_pc when the WORD result is 0, else other_pc.
void pc10_mask(AnimationMachineState& r,std::uint32_t mask,std::uint32_t zero_pc,std::uint32_t other_pc) {
    am_word(r.d[1],mask);am_word(r.d[1],r.d[1]&r.d[0]);r.pc=(r.d[1]&0xffffU)==0U?zero_pc:other_pc;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc10_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c10 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W d16(A6),D0 (D0 bits 16..31 kept); JSR target.
bool pc10_field_call(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc10_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MOVE.W #k,D0 (D0 bits 16..31 kept); JSR target (3af8: the sound request).
bool pc10_word_call(AnimationMachineContext& c,std::uint32_t k,std::uint32_t target,std::uint32_t return_pc) {
    am_word(c.s.d[0],k);return am_call(c,target,return_pc);
}
// MOVE.L #v,(A6): the node callback LONG, then next_pc.
bool pc10_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc10_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #v,84(A6) (the second callback slot of the player node), then next_pc.
bool pc10_slot84(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc10_put(c,c.s.a[6],0x84,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.B #k,9d(A6); LEA record(PC),A0; BRA.W 22348 (the four turn entries 22314 22322 22330 2233e; 2233e falls into 22348).
bool pc10_turn(AnimationMachineContext& c,std::uint32_t k,std::uint32_t record) {
    if(!pc10_put(c,c.s.a[6],0x9d,1,k))return false;c.s.a[0]=record;c.s.pc=0x22348;return true;
}
// The re-read flag source of a Z reader (contract decision 3): the 24-bit address must be work RAM / fixed ROM (< 200000), else the re-read could be
// a device read: the checked flag-source error.
bool pc10_flag_byte(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t& value) {
    const std::uint32_t at=am_index(base,displacement);
    if((at&0xffffffU)>=0x200000U)return am_error(c,"unsupported animation player c10 flag source");
    return am_read(c,at,1,value);
}
// The handlers of the (handler LONG, key WORD) lists that C3 215e6 matched (contract decision 2; ROM bytes):
//   21b0a (21602,0) (21c22,1) (21e48,3) (21e3a,4) 0 for JMP (A1) 21e10 (as C8 21d9e);  216c8 (21602,0) 0 for JMP (A1) 2229a 22378.
// All the handlers are routed (21602 21c22 C3, 21e48 C9, 21e3a C8).
const std::uint32_t PC10_LIST_21B0A[4]={0x21602,0x21c22,0x21e48,0x21e3a};
const std::uint32_t PC10_LIST_216C8[1]={0x21602};
// JMP (A1) (contract decision 2): A1 one of the list handlers (the LONG that 215e6 loaded with MOVEA.L (A0)+,A1; compared as a LONG), else the
// checked jump-target error.
bool pc10_list_jump(AnimationMachineContext& c,const std::uint32_t* list,unsigned int count) {
    for(unsigned int i=0;i<count;++i)if(list[i]==c.s.a[1]){c.s.pc=c.s.a[1];return true;}
    return am_error(c,"unsupported animation player c10 jump target");
}
// JMP 203b0(PC,D0.W) (contract decision 2): the BRA.W table 203b0..203d4 of 9 entries (D0.W = 4 x BYTE 9f(A6); the ROM writers of the player node's
// BYTE 9f are 1c1e8 (the BYTE a0, 0..8) and 1bd46 (0)); only the executed entry 203b0 (-> 20414) is a block, a displacement 0 .. 20 moves the PC to the
// table entry (an unrouted entry is the next dispatch's 'unsupported animation machine PC', a declared stop), any other D0.W is the checked
// jump-target error.
bool pc10_table_jump(AnimationMachineContext& c) {
    const std::uint32_t displacement=c.s.d[0]&0xffffU;
    if(displacement>0x20U)return am_error(c,"unsupported animation player c10 jump target");
    c.s.pc=0x203b0U+displacement;return true;
}
}
// Player C10 (132 block starts, contract docs/analysis/animation-machine-player-c10-contract.md; area-C plan 10.5 unit C-2 with the C7 table entry
// 252b4 -> 252ce .. 252e2 (main decision 4) and the branch target 2041a): the 28ae child callback 1c4b0 -> 1c4d2 -> 1c500 (C5 1c484; sounds 3af8, JMP
// 2a00), the Set / Clear successors 1dc8e / 1dccc of the routed interpreter stub 1dc84 / 1dc8a (1d1d0, 1aa3a, the callback 1f3e0), the player input
// state 1efd6 -> 1efe4, the record entries 1f082 / 1f3e0, the C3 table entry 20324 -> 203a0 (the BRA.W table jump 203ac, entry 203b0) -> 20414 ->
// 204e0 (1cc1a 492c8 1c1e2 1c51c 1c356), 20bfe (ADDQ.L #7,D2 of the C9 settle), the slot-84 states 21dd0 -> 21e04 (JMP (A1) 21e10 on the list 21b0a),
// 22148 (1cb08), 22286 -> 2228e (JMP (A1) 2229a) -> 22360 (JMP (A1) 22378) and 223fa, the sound helper 24b78 and the 2986 child callback 24ecc (the
// bank window LONG 200038, 49f8c, 8ebe), the C7 table entry 252b4 -> 252ce (BYTE 61(A2) bit 7, 3af8) -> 252e2.
// C: the 7 consumers 21dda 21de2 21dea (BCS, 21bc6 / 21baa / 21c1c), 21e0c 22296 22374 (BCC, 215e6), 22164 (BCC, 1cb08) read a known C or fail; every
// C10 block leaves C Unknown (no C10 block produces or passes a C that a reader uses).  Z: 1efee (BEQ after the BTST.B #7,15(A6) of 1efe8) re-reads
// the BYTE 15(A6) (work RAM / fixed ROM only, else the checked flag-source error); 1eff6 (BEQ after the BTST #5,D0 of 1eff2) recomputes the Z from D0
// bit 5; 20508 (BNE after the BTST.L D1,D7; RTS of C5 1c51c) recomputes the Z from D7 bit (D1 mod 32).
bool animation_player_c10_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool old=false;
    switch(r.pc) {
    // ---- 1c4b0 (the 28ae child callback of C5 1c484): TST.W 76(A6); BEQ.W 1c500 / MOVE.W #1a6d,D0; JSR 3af8.l / MOVE.W #c,78(A6); CLR.B 7a(A6); MOVE.L
    // #1c4d2,(A6) / 1c4d2: CMPI.B #0,7a(A6); BEQ.W 1c4e0 / BRA.W 1c500 / SUBQ.W #1,78(A6); BEQ.W 1c4ea / RTS / MOVE.W 76(A6),D0; BEQ.W 1c500 / JSR
    // 3af8.l / MOVE.L #1c500,(A6); RTS / 1c500: MOVE.L c(A6),D0; CMPI.L #0,D0; BEQ.W 1c514 / MOVEA.L D0,A0; CLR.L b2(A0) / JMP 2a00.l.
    case 0x1c4b0:if(!pc10_get(c,r.a[6],0x76,2,value))return false;r.pc=value==0U?0x1c500:0x1c4b8;return true;
    case 0x1c4b8:return pc10_word_call(c,0x1a6d,0x3af8,0x1c4c2);
    case 0x1c4c2:if(!pc10_put(c,r.a[6],0x78,2,0xc) || !pc10_put(c,r.a[6],0x7a,1,0))return false;return pc10_install(c,0x1c4d2,0x1c4d2);
    case 0x1c4d2:return pc10_byte_is(c,0x7a,0,0x1c4e0,0x1c4dc);
    case 0x1c4dc:r.pc=0x1c500;return true;
    case 0x1c4e0:
        if(!pc10_get(c,r.a[6],0x78,2,value) || !pc10_put(c,r.a[6],0x78,2,value-1U))return false;r.pc=((value-1U)&0xffffU)==0U?0x1c4ea:0x1c4e8;return true;
    case 0x1c4e8:return am_return(c);                                                                     // RTS (the dispatcher reads no flag).
    case 0x1c4ea:if(!pc10_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.pc=value==0U?0x1c500:0x1c4f2;return true;
    case 0x1c4f2:return am_call(c,0x3af8,0x1c4f8);
    case 0x1c4f8:if(!pc10_put(c,r.a[6],0,4,0x1c500))return false;return am_return(c);
    case 0x1c500:if(!pc10_get(c,r.a[6],0xc,4,r.d[0]))return false;r.pc=r.d[0]==0U?0x1c514:0x1c50e;return true;
    case 0x1c50e:r.a[0]=r.d[0];if(!pc10_put(c,r.a[0],0xb2,4,0))return false;r.pc=0x1c514;return true;
    case 0x1c514:r.pc=0x2a00;return true;                                                                 // JMP 2a00.l.
    // ---- 1dc8e (the Set side of the interpreter stub 1dc8a; contract decision 5): BSR.W 1d1d0 / BSET.B #2,a7(A6); MOVE.W #8834,68(A6); MOVE.W
    // #8834,1e(A6); MOVE.L #1f3e0,(A6); JSR 1aa3a.l / BTST.B #3,D0; BEQ.W 1dcbe / MOVE.L #1e21c,(A6) (written only) / BTST.B #6,D0; BEQ.W 1dccc /
    // MOVE.L #1e8de,(A6) (written only) / 1dccc (the Clear side): BRA.W 201a2.
    case 0x1dc8e:return am_call(c,0x1d1d0,0x1dc92);
    case 0x1dc92:
        if(!pc10_bit(c,0xa7,2,1,old) || !pc10_put(c,r.a[6],0x68,2,0x8834) || !pc10_put(c,r.a[6],0x1e,2,0x8834) || !pc10_put(c,r.a[6],0,4,0x1f3e0))
            return false;
        return am_call(c,0x1aa3a,0x1dcb0);
    case 0x1dcb0:pc10_input_bit(r,3,0x1dcbe,0x1dcb8);return true;
    case 0x1dcb8:return pc10_install(c,0x1e21c,0x1dcbe);
    case 0x1dcbe:pc10_input_bit(r,6,0x1dccc,0x1dcc6);return true;
    case 0x1dcc6:return pc10_install(c,0x1e8de,0x1dccc);
    case 0x1dccc:case 0x1f06c:r.pc=0x201a2;return true;                                                  // BRA.W 201a2 (C3).
    // ---- 1efd6 (C4 1ef96 BNE): LEA 1b6fc(PC),A0; BSR.W 1cab6 / MOVE.L #1efe4,(A6) / 1efe4: BSR.W 1cd98 / BTST.B #7,15(A6) / BEQ.W 1fae8 (the Z of
    // that BTST, re-read) / BTST.B #5,D0 / BEQ.W 1f01a (D0 bit 5) / CMPI.B #0,9e(A6); BNE.W 1f00c / BTST.B #1,D0; BNE.W 1f7a4 / MOVE.W #c,D1; AND.W
    // D0,D1; BNE.W 1fa68 / BRA.W 1fa3c / BTST.B #1,D0; BNE.W 1f2a4 / BTST.B #7,D0; BNE.W 1f1d8 / BSR.W 1cec2 / CMPI.B #1,D1; BEQ.W 1f070 / CMPI.B
    // #2,D1; BEQ.W 1eeea / BTST.B #3,a7(A6); BEQ.W 1eeea / MOVE.W #c,D1; AND.W D0,D1; BEQ.W 1ed78 / BSR.W 1d09e / JSR 4bfc0.l / MOVE.W 1e(A6),D0;
    // JSR ce02.l / JSR 49fc6.l / BRA.W 201a2.
    case 0x1efd6:r.a[0]=0x1b6fc;return am_call(c,0x1cab6,0x1efde);
    case 0x1efde:return pc10_install(c,0x1efe4,0x1efe4);
    case 0x1efe4:return am_call(c,0x1cd98,0x1efe8);
    case 0x1efe8:if(!pc10_bit(c,0x15,7,0,old))return false;r.pc=0x1efee;return true;                     // BTST.B #7,15(A6) (its Z read by 1efee).
    case 0x1efee:if(!pc10_flag_byte(c,r.a[6],0x15,value))return false;r.pc=(value&0x80U)==0U?0x1fae8:0x1eff2;return true;
    case 0x1eff2:r.pc=0x1eff6;return true;                                                                 // BTST.B #5,D0 (its Z read by 1eff6).
    case 0x1eff6:pc10_input_bit(r,5,0x1f01a,0x1effa);return true;
    case 0x1effa:return pc10_byte_is(c,0x9e,0,0x1f004,0x1f00c);
    case 0x1f004:pc10_input_bit(r,1,0x1f00c,0x1f7a4);return true;
    case 0x1f00c:pc10_mask(r,0xc,0x1f016,0x1fa68);return true;
    case 0x1f016:r.pc=0x1fa3c;return true;                                                                 // BRA.W 1fa3c (C2).
    case 0x1f01a:pc10_input_bit(r,1,0x1f022,0x1f2a4);return true;
    case 0x1f022:pc10_input_bit(r,7,0x1f02a,0x1f1d8);return true;
    case 0x1f02a:return am_call(c,0x1cec2,0x1f02e);
    case 0x1f02e:r.pc=(r.d[1]&0xffU)==1U?0x1f070:0x1f036;return true;                                     // CMPI.B #1,D1; BEQ.W 1f070 (C9).
    case 0x1f036:r.pc=(r.d[1]&0xffU)==2U?0x1eeea:0x1f03e;return true;                                     // CMPI.B #2,D1; BEQ.W 1eeea (C4).
    case 0x1f03e:return pc10_field_bit(c,0xa7,3,0x1eeea,0x1f048);
    case 0x1f048:pc10_mask(r,0xc,0x1ed78,0x1f052);return true;
    case 0x1f052:return am_call(c,0x1d09e,0x1f056);
    case 0x1f056:return am_call(c,0x4bfc0,0x1f05c);
    case 0x1f05c:return pc10_field_call(c,0x1e,0xce02,0x1f066);
    case 0x1f066:return am_call(c,0x49fc6,0x1f06c);
    // ---- 1f082 (C9 1f07e BLE fall-through): LEA 1b20e(PC),A0 (falls into C9 1f086).  1f3e0 (written by 1dca4, C8 1f764, 1f3ce): LEA 1b290(PC),A0;
    // BRA.W 1f3ec (C8).
    case 0x1f082:r.a[0]=0x1b20e;r.pc=0x1f086;return true;
    case 0x1f3e0:r.a[0]=0x1b290;r.pc=0x1f3ec;return true;
    // ---- 20324 (the entry 1 of the C3 table 2031c): BRA.W 203a0 / 203a0: MOVE.W #0,D0; MOVE.B 9f(A6),D0 (D0 bits 16..31 kept); ADD.W D0,D0 twice; JMP
    // 203b0(PC,D0.W) (contract decision 2) / 203b0 (the entry 0): BRA.W 20414 / MOVE.B #6,a4(A6) / 2041a: TST.B 9c(A6); BEQ.W 2042e / MOVE.L #21602,84(A6);
    // BRA.W 20440 / MOVEQ #0,D7; MOVE.B a9(A6),D7; LSL.W #2,D7; MOVE.L 20444(PC,D7.W),D7 (fixed ROM LONG table, live bus); BEQ.W 20516 (C3) / MOVE.L
    // D7,(A6) (written only) / BRA.W 204e0.
    case 0x20324:r.pc=0x203a0;return true;
    case 0x203a0:
        am_word(r.d[0],0);if(!pc10_get(c,r.a[6],0x9f,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);
        am_word(r.d[0],r.d[0]+r.d[0]);return pc10_table_jump(c);
    case 0x203b0:r.pc=0x20414;return true;
    case 0x20414:if(!pc10_put(c,r.a[6],0xa4,1,6))return false;r.pc=0x2041a;return true;
    case 0x2041a:return pc10_byte_is(c,0x9c,0,0x2042e,0x20422);
    case 0x20422:return pc10_slot84(c,0x21602,0x20440);
    case 0x2042e:
        r.d[7]=0;if(!pc10_get(c,r.a[6],0xa9,1,value))return false;am_byte(r.d[7],value);am_word(r.d[7],(r.d[7]&0xffffU)<<2);
        if(!am_read(c,am_index(0x20444,r.d[7]&0xffffU),4,r.d[7]))return false;r.pc=r.d[7]==0U?0x20516:0x2043e;return true;
    case 0x2043e:if(!pc10_put(c,r.a[6],0,4,r.d[7]))return false;r.pc=0x20440;return true;
    case 0x20440:r.pc=0x204e0;return true;
    // ---- 204e0: BSR.W 1cc1a / MOVE.W #8834,68(A6); MOVE.W #8834,1e(A6); JSR 492c8.l / BSR.W 1c1e2 / MOVEA.L A6,A0; MOVEA.L 8c(A6),A4; MOVE.B 4(A4),D1;
    // BSR.W 1c51c / BNE.W 20516 (the Z of the BTST.L D1,D7 that ends 1c51c, recomputed from D7 / D1) / MOVE.W 78(A6),D0; MOVEQ #0,D1; JSR 1c356(PC)
    // (return 20516, C3).
    case 0x204e0:return am_call(c,0x1cc1a,0x204e4);
    case 0x204e4:if(!pc10_put(c,r.a[6],0x68,2,0x8834) || !pc10_put(c,r.a[6],0x1e,2,0x8834))return false;return am_call(c,0x492c8,0x204f6);
    case 0x204f6:return am_call(c,0x1c1e2,0x204fa);
    case 0x204fa:
        r.a[0]=r.a[6];if(!pc10_get(c,r.a[6],0x8c,4,r.a[4]) || !pc10_get(c,r.a[4],4,1,value))return false;am_byte(r.d[1],value);
        return am_call(c,0x1c51c,0x20508);
    case 0x20508:r.pc=(r.d[7]&(1U<<(r.d[1]&31U)))!=0U?0x20516:0x2050c;return true;
    case 0x2050c:if(!pc10_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);r.d[1]=0;return am_call(c,0x1c356,0x20516);
    // ---- 20bfe (C9 20bfa BMI fall-through): ADDQ.L #7,D2 (LONG; falls into C9 20c00).
    case 0x20bfe:r.d[2]+=7U;r.pc=0x20c00;return true;
    // ---- 21dd0 (C4 21d64 BGT): BCLR.B #5,a7(A6); BSR.W 21bc6 / BCS.W 223b2 / BSR.W 21baa / BCS.W 223b2 / BSR.W 21c1c / BCS.W 223b2 (C of 21bc6 / 21baa /
    // 21c1c) / LEA 1b8a2(PC),A0; BSR.W 1cabe / MOVE.B #1,aa(A6); MOVE.L #21e04,84(A6) / 21e04: LEA 21b0a(PC),A0; BSR.W 215e6 / BCC.W 21e12 (C of 215e6)
    // / JMP (A1) (list 21b0a) / BSR.W 1cd98 / BTST.B #1 / #0 / #6 / #4,D0: BNE 223c4 / BEQ 223b2 / BNE 21ffc / BNE 2210c / BRA.W 2156a.
    case 0x21dd0:if(!pc10_bit(c,0xa7,5,2,old))return false;return am_call(c,0x21bc6,0x21dda);
    case 0x21dda:case 0x21de2:case 0x21dea:return pc10_carry(c,r.pc+4U,0x223b2);
    case 0x21dde:return am_call(c,0x21baa,0x21de2);
    case 0x21de6:return am_call(c,0x21c1c,0x21dea);
    case 0x21dee:r.a[0]=0x1b8a2;return am_call(c,0x1cabe,0x21df6);
    case 0x21df6:if(!pc10_put(c,r.a[6],0xaa,1,1))return false;return pc10_slot84(c,0x21e04,0x21e04);
    case 0x21e04:r.a[0]=0x21b0a;return am_call(c,0x215e6,0x21e0c);
    case 0x21e0c:return pc10_carry(c,0x21e12,0x21e10);
    case 0x21e10:return pc10_list_jump(c,PC10_LIST_21B0A,4U);
    case 0x21e12:case 0x2229c:case 0x22360:return am_call(c,0x1cd98,r.pc+4U);                            // BSR.W 1cd98.
    case 0x21e16:pc10_input_bit(r,1,0x21e1e,0x223c4);return true;
    case 0x21e1e:pc10_input_bit(r,0,0x223b2,0x21e26);return true;
    case 0x21e26:case 0x222a0:case 0x22364:pc10_input_bit(r,6,r.pc+8U,0x21ffc);return true;              // BTST.B #6,D0; BNE.W 21ffc (C3).
    case 0x21e2e:pc10_input_bit(r,4,0x21e36,0x2210c);return true;
    case 0x21e36:r.pc=0x2156a;return true;                                                                 // BRA.W 2156a (C3).
    // ---- 22148 (C9 22144 BEQ fall-through): MOVE.B #0,aa(A6); LEA 1b7fc(PC),A0; BCHG.B #1,a7(A6); BNE.W 22160 (the bit was set) / LEA 1b81e(PC),A0 /
    // BSR.W 1cb08 / BCC.W 22174 (C of 1cb08) / CLR.B 9d(A6); BSR.W 1cabe / BRA.W 221ca (C3).
    case 0x22148:
        if(!pc10_put(c,r.a[6],0xaa,1,0))return false;r.a[0]=0x1b7fc;if(!pc10_bit(c,0xa7,1,3,old))return false;r.pc=old?0x22160:0x2215c;return true;
    case 0x2215c:r.a[0]=0x1b81e;r.pc=0x22160;return true;
    case 0x22160:return am_call(c,0x1cb08,0x22164);
    case 0x22164:return pc10_carry(c,0x22174,0x22168);
    case 0x22168:if(!pc10_put(c,r.a[6],0x9d,1,0))return false;return am_call(c,0x1cabe,0x22170);
    case 0x22170:r.pc=0x221ca;return true;
    // ---- 22286 (C9 221ae / 221b6 BEQ): MOVE.L #2228e,84(A6) / 2228e (slot-84 value): LEA 216c8(PC),A0; BSR.W 215e6 / BCC.W 2229c / JMP (A1) (list 216c8)
    // / BSR.W 1cd98 / BTST.B #6,D0; BNE.W 21ffc / TST.B 7e(A6); BEQ.W 222c0 / BTST.B #4,a5(A6); BNE.W 22128 (C9) / MOVE.B #1,aa(A6) / BTST.B #0,D0;
    // BEQ.W 222d8 / TST.B 9d(A6); BEQ.W 22322; BLT.W 2233e / BRA.W 22300 / BTST.B #1,D0; BEQ.W 222f0 / TST.B 9d(A6); BEQ.W 22314; BGT.W 22330 / BRA.W
    // 22300 / TST.B 9d(A6); BEQ.W 22300; BGT.W 22330; BLT.W 2233e / BSR.W 2156a / TST.W D7; BEQ.W 22312 / MOVE.L #22452,84(A6) / RTS.
    case 0x22286:return pc10_slot84(c,0x2228e,0x2228e);
    case 0x2228e:case 0x2236c:r.a[0]=0x216c8;return am_call(c,0x215e6,r.pc+8U);                         // LEA 216c8(PC),A0; BSR.W 215e6.
    case 0x22296:return pc10_carry(c,0x2229c,0x2229a);
    case 0x2229a:case 0x22378:return pc10_list_jump(c,PC10_LIST_216C8,1U);
    case 0x222a8:return pc10_byte_is(c,0x7e,0,0x222c0,0x222b0);
    case 0x222b0:return pc10_field_bit(c,0xa5,4,0x222ba,0x22128);
    case 0x222ba:if(!pc10_put(c,r.a[6],0xaa,1,1))return false;r.pc=0x222c0;return true;
    case 0x222c0:pc10_input_bit(r,0,0x222d8,0x222c8);return true;
    case 0x222c8:
        if(!pc10_get(c,r.a[6],0x9d,1,value))return false;r.pc=value==0U?0x22322:((value&0x80U)!=0U?0x2233e:0x222d4);return true;
    case 0x222d4:case 0x222ec:r.pc=0x22300;return true;                                                  // BRA.W 22300.
    case 0x222d8:pc10_input_bit(r,1,0x222f0,0x222e0);return true;
    case 0x222e0:
        if(!pc10_get(c,r.a[6],0x9d,1,value))return false;r.pc=value==0U?0x22314:((value&0x80U)==0U?0x22330:0x222ec);return true;
    case 0x222f0:
        if(!pc10_get(c,r.a[6],0x9d,1,value))return false;r.pc=value==0U?0x22300:((value&0x80U)==0U?0x22330:0x2233e);return true;
    case 0x22300:case 0x2237a:return am_call(c,0x2156a,r.pc+4U);                                         // BSR.W 2156a.
    case 0x22304:r.pc=(r.d[7]&0xffffU)==0U?0x22312:0x2230a;return true;                                 // TST.W D7; BEQ.W 22312.
    case 0x2230a:return pc10_slot84(c,0x22452,0x22312);                                                   // MOVE.L #22452,84(A6).
    case 0x22312:case 0x2239e:return am_return(c);                                                        // RTS (no caller reads its flags).
    // ---- 22314 / 22322 / 22330 / 2233e: MOVE.B #ff / #1 / #0 / #0,9d(A6); LEA 1bbf2 / 1bbd6 / 1bc0e / 1bc2a(PC),A0 / 22348: BSR.W 1cabe / ANDI.B
    // #ef,a5(A6); ANDI.B #ef,a6(A6); MOVE.L #22360,84(A6) / 22360 (slot-84 value): BSR.W 1cd98 / BTST.B #6,D0; BNE.W 21ffc / LEA 216c8(PC),A0; BSR.W 215e6
    // / BCC.W 2237a / JMP (A1) (list 216c8) / BSR.W 2156a / TST.W D7; BEQ.W 2239e / MOVE.L #22452,84(A6); BTST.B #4,a5(A6); BEQ.W 2239e / MOVE.L
    // #22128,84(A6) / RTS.
    case 0x22314:return pc10_turn(c,0xff,0x1bbf2);
    case 0x22322:return pc10_turn(c,1,0x1bbd6);
    case 0x22330:return pc10_turn(c,0,0x1bc0e);
    case 0x2233e:return pc10_turn(c,0,0x1bc2a);
    case 0x22348:return am_call(c,0x1cabe,0x2234c);
    case 0x2234c:
        if(!pc10_get(c,r.a[6],0xa5,1,value) || !pc10_put(c,r.a[6],0xa5,1,value&0xefU) || !pc10_get(c,r.a[6],0xa6,1,value) ||
           !pc10_put(c,r.a[6],0xa6,1,value&0xefU))return false;
        return pc10_slot84(c,0x22360,0x22360);
    case 0x22374:return pc10_carry(c,0x2237a,0x22378);
    case 0x2237e:r.pc=(r.d[7]&0xffffU)==0U?0x2239e:0x22384;return true;                                 // TST.W D7; BEQ.W 2239e.
    case 0x22384:if(!pc10_put(c,r.a[6],0x84,4,0x22452))return false;return pc10_field_bit(c,0xa5,4,0x2239e,0x22396);
    case 0x22396:return pc10_slot84(c,0x22128,0x2239e);
    // ---- 223fa (C9 21d40 BNE): MOVE.B #1,9d(A6); LEA 1b986(PC),A0; BSR.W 1cabe (return 22408, C9).
    case 0x223fa:if(!pc10_put(c,r.a[6],0x9d,1,1))return false;r.a[0]=0x1b986;return am_call(c,0x1cabe,0x22408);
    // ---- 24b78 (BSR from 24ede and the later-unit 24ba8 .. 24f76): MOVE.W -7ff2(A5),D6; MOVE.W 547e(A5),D7; SUB.W D6,D7; ADDI.W #c,D7; BCS.W 24b94 (the
    // carry out of the WORD add) / MOVE.W D6,547e(A5); JSR 3af8.l / RTS (its flags are read by no caller).
    case 0x24b78: {
        if(!pc10_get(c,r.a[5],0x800e,2,value))return false;am_word(r.d[6],value);
        if(!pc10_get(c,r.a[5],0x547e,2,value))return false;am_word(r.d[7],value);am_word(r.d[7],r.d[7]-r.d[6]);
        const std::uint32_t sum=(r.d[7]&0xffffU)+0xcU;am_word(r.d[7],sum);
        r.pc=sum>0xffffU?0x24b94:0x24b8a;return true;
    }
    case 0x24b8a:if(!pc10_put(c,r.a[5],0x547e,2,r.d[6]))return false;return am_call(c,0x3af8,0x24b94);
    case 0x24b94:return am_return(c);
    // ---- 24ecc (the 2986 child callback of the C7 LONG table 22502): MOVE.W #2a,20(A6); MOVE.L 200038.l,22(A6) (bank window); MOVE.W #1a65,D0; BSR.W
    // 24b78 / MOVE.L #6f364,84(A6); MOVE.L #100000,7a(A6); CLR.B 88(A6); MOVEA.L #25642,A1; MOVE.W #100,D0; JSR 49f8c.l / MOVE.W #202,D0; MOVE.B #0,D1;
    // JSR 8ebe.l / BRA.W 24ffa (C7).
    case 0x24ecc:
        if(!pc10_put(c,r.a[6],0x20,2,0x2a) || !am_read(c,0x200038,4,value) || !pc10_put(c,r.a[6],0x22,4,value))return false;
        return pc10_word_call(c,0x1a65,0x24b78,0x24ee2);
    case 0x24ee2:
        if(!pc10_put(c,r.a[6],0x84,4,0x6f364) || !pc10_put(c,r.a[6],0x7a,4,0x100000) || !pc10_put(c,r.a[6],0x88,1,0))return false;
        r.a[1]=0x25642;return pc10_word_call(c,0x100,0x49f8c,0x24f06);
    case 0x24f06:am_byte(r.d[1],0);return pc10_word_call(c,0x202,0x8ebe,0x24f14);
    case 0x24f14:r.pc=0x24ffa;return true;
    // ---- 252b4 (the entry 6 of the C7 table 2529c; main decision 4): BRA.W 252ce / BTST.B #7,61(A2); BNE.W 252e2 / MOVE.W #189d,D0; JSR 3af8.l / 252e2:
    // BRA.W 253c8 (C7).
    case 0x252b4:r.pc=0x252ce;return true;
    case 0x252ce:if(!pc10_get(c,r.a[2],0x61,1,value))return false;r.pc=(value&0x80U)!=0U?0x252e2:0x252d8;return true;
    case 0x252d8:return pc10_word_call(c,0x189d,0x3af8,0x252e2);
    case 0x252e2:r.pc=0x253c8;return true;
    default:return am_error(c,"unsupported animation player c10 PC");
    }
}
}
