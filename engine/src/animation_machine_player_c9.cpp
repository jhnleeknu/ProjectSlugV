#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc9_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc9_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR / BCHG #bit,d16(A6) (a memory operand: BYTE, bit modulo 8). op 0 tests, 1 sets, 2 clears, 3 changes; old is the bit before
// (the Z of the instruction is old = 0).
bool pc9_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!pc9_get(c,c.s.a[6],displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    std::uint32_t next=value&~mask;
    if(op==1U || (op==3U && !old))next=value|mask;
    return pc9_put(c,c.s.a[6],displacement,1,next);
}
// BTST #bit,d16(A6); BEQ.W zero_pc (the bit clear) / other_pc.
bool pc9_field_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t other_pc) {
    bool old=false;if(!pc9_bit(c,displacement,bit,0,old))return false;
    c.s.pc=old?other_pc:zero_pc;return true;
}
// BTST #bit,D0 (a data register operand: the LONG bit, bit < 32); BEQ.W zero_pc / other_pc.
void pc9_input_bit(AnimationMachineState& r,unsigned int bit,std::uint32_t zero_pc,std::uint32_t other_pc) {
    r.pc=(r.d[0]&(1U<<bit))==0U?zero_pc:other_pc;
}
// TST.B / CMPI.B #k,d16(A6); BEQ / BNE: equal_pc when the BYTE is k, else other_pc.
bool pc9_byte_is(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc9_get(c,c.s.a[6],displacement,1,value))return false;
    c.s.pc=value==k?equal_pc:other_pc;return true;
}
// MOVE.W #mask,D1; AND.W D0,D1 (WORD: D1 bits 16..31 kept); zero_pc when the WORD result is 0, else other_pc.
void pc9_mask(AnimationMachineState& r,std::uint32_t mask,std::uint32_t zero_pc,std::uint32_t other_pc) {
    am_word(r.d[1],mask);am_word(r.d[1],r.d[1]&r.d[0]);r.pc=(r.d[1]&0xffffU)==0U?zero_pc:other_pc;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc9_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c9 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W d16(A6),D0 (D0 bits 16..31 kept); JSR target.
bool pc9_field_call(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc9_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MOVE.L #v,(A6): the node callback LONG, then next_pc.
bool pc9_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc9_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #v,84(A6) (the second callback slot of the player node), then next_pc.
bool pc9_slot84(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc9_put(c,c.s.a[6],0x84,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #21602,84(A6); MOVE.B #0,9c(A6); MOVE.B #1,aa(A6); CLR.W 7a(A6) (the slot part of the states 1f492 20ac4 20b6e 20d0a 213b4).
bool pc9_slot(AnimationMachineContext& c) {
    const std::uint32_t a6=c.s.a[6];
    return pc9_put(c,a6,0x84,4,0x21602) && pc9_put(c,a6,0x9c,1,0) && pc9_put(c,a6,0xaa,1,1) && pc9_put(c,a6,0x7a,2,0);
}
// ASR.L #count,Dn (count 1..8 immediate or a register count modulo 64): the sign fills from the left; 32 or more leaves only the sign.  Written
// without a signed shift (no implementation-defined right shift of a negative value).
std::uint32_t pc9_asr(std::uint32_t value,unsigned int count) {
    count&=63U;
    if(count==0U)return value;
    const bool negative=(value&0x80000000U)!=0U;
    if(count>=32U)return negative?0xffffffffU:0U;
    const std::uint32_t shifted=value>>count;
    return negative?(shifted|(0xffffffffU<<(32U-count))):shifted;
}
// ASR.W #count,Dn (count 1..8): the WORD part shifted with its sign bit 15; Dn bits 16..31 kept.
void pc9_asr_word(std::uint32_t& r,unsigned int count) {
    const std::uint32_t word=r&0xffffU;
    std::uint32_t shifted=word>>count;
    if((word&0x8000U)!=0U)shifted|=(0xffffU<<(16U-count))&0xffffU;
    am_word(r,shifted);
}
// MOVEA.L #callback,A0; MOVE.W #1e,D0 (D0 bits 16..31 kept); JSR 28ae.l (the child object: 36350 / 371f8 / eaac0, contract scope).
bool pc9_child(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t return_pc) {
    c.s.a[0]=callback;am_word(c.s.d[0],0x1e);return am_call(c,0x28ae,return_pc);
}
// MOVE.W 76(A6),D0; LEA table(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0 (fixed ROM WORD table, index sign-extended, live bus); MOVE.B #0,D1;
// JSR 8ebe.l.  D0 / D1 keep their upper bits.
bool pc9_table_sound(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!pc9_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.a[0]=table;am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);
    return am_call(c,0x8ebe,return_pc);
}
// MOVEQ #0,D2; MOVE.L #k,D3; SUB.L 36(A6),D2; BMI.W minus_pc (N of the LONG result) / plus_pc (the ADDQ.L #7,D2 block).
bool pc9_settle(AnimationMachineContext& c,std::uint32_t k,std::uint32_t plus_pc,std::uint32_t minus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.d[2]=0;r.d[3]=k;if(!pc9_get(c,r.a[6],0x36,4,value))return false;r.d[2]=0U-value;
    r.pc=(r.d[2]&0x80000000U)!=0U?minus_pc:plus_pc;return true;
}
// ASR.L #3,D2; ADD.L D2,36(A6); SUB.L 3a(A6),D3; BMI.W minus_pc / plus_pc.
bool pc9_settle_x(AnimationMachineContext& c,std::uint32_t plus_pc,std::uint32_t minus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.d[2]=pc9_asr(r.d[2],3);if(!pc9_get(c,r.a[6],0x36,4,value) || !pc9_put(c,r.a[6],0x36,4,value+r.d[2]))return false;
    if(!pc9_get(c,r.a[6],0x3a,4,value))return false;r.d[3]-=value;
    r.pc=(r.d[3]&0x80000000U)!=0U?minus_pc:plus_pc;return true;
}
// ASR.L #3,D3; ADD.L D3,3a(A6), then next_pc (0: RTS).
bool pc9_settle_y(AnimationMachineContext& c,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.d[3]=pc9_asr(r.d[3],3);if(!pc9_get(c,r.a[6],0x3a,4,value) || !pc9_put(c,r.a[6],0x3a,4,value+r.d[3]))return false;
    if(next_pc==0U)return am_return(c);
    r.pc=next_pc;return true;
}
// MOVE.B #k,9d(A6); LEA record(PC),A0; BSR.W 1cabe (the 223a0 .. 223e8 entries; return = the BRA.W 22408 block).
bool pc9_turn(AnimationMachineContext& c,std::uint32_t k,std::uint32_t record,std::uint32_t return_pc) {
    if(!pc9_put(c,c.s.a[6],0x9d,1,k))return false;c.s.a[0]=record;return am_call(c,0x1cabe,return_pc);
}
// The handlers of the (handler LONG, key WORD) lists that C3 215e6 matched (contract decision 2; ROM bytes):
//   21aee (21602,0) (21d60,2) (21e48,3) (21e3a,4) 0 for JMP (A1) 21ce4;  216c8 (21602,0) 0 for JMP (A1) 21d36 2224c 22428.
// All the handlers are routed since C9 (21e48 is a C9 start).
const std::uint32_t PC9_LIST_21AEE[4]={0x21602,0x21d60,0x21e48,0x21e3a};
const std::uint32_t PC9_LIST_216C8[1]={0x21602};
// JMP (A1) (contract decision 2): A1 one of the list handlers (the LONG that 215e6 loaded with MOVEA.L (A0)+,A1; compared as a LONG), else the
// checked jump-target error.
bool pc9_list_jump(AnimationMachineContext& c,const std::uint32_t* list,unsigned int count) {
    for(unsigned int i=0;i<count;++i)if(list[i]==c.s.a[1]){c.s.pc=c.s.a[1];return true;}
    return am_error(c,"unsupported animation player c9 jump target");
}
}
// Player C9 (220 block starts, contract docs/analysis/animation-machine-player-c9-contract.md; area-C plan 10.8, the first unit of the extended-input
// IO observation): the player states 1ec74 -> 1ecb8 (1cb08, 1cab6, 1cd98, 4bfc0 ce02 49fc6, 201a2; the child 36350), 1f070 / 1f086 -> 1f0ae (the
// motion record helper 1d092), 1f48a -> 1f4b6 (1cec2, the helper 1d086), the callbacks 1f3e8 / 1fb28 / 20720, the ground / air states 208fa (ea680,
// 1aa3a) -> 20a98 -> 20aec, 20b42 -> 20b96 (the settle helpers 20a4a / 20a6e: LONG SUB / ASR.L #3 / ADD), 20cd8 -> 20d36 (the child eaac0, 4970a),
// 21370 (8ebe on the WORD tables 1b170 / 1b178, 20efc), and the slot-84 states 21ca4 / 21cd8, 21d0e / 21d2a, 21e48, 2210c -> 22128 -> 22174 (the
// ROM LONG tables 22074 / 220c0 / 22028), 22238 / 22240, 223a0 .. 223e8 -> 22408 / 2241c, 22452 with the JMP (A1) 21ce4 21d36 2224c 22428 on the
// 215e6 lists 21aee / 216c8.
// C: the 14 consumers 1eca0 (BCC, 1cb08), 1ed14 1f118 1f52a (BCC, 49fc6), 20900 20a50 20bd2 (BCC, ea680), 21cae 21cb6 21cbe (BCS, 21bc6 / 21baa /
// 21c1c), 21ce0 21d32 22248 22424 (BCC, 215e6) read a known C or fail; every C9 block leaves C Unknown (the RTS 20a54 20a90 22284 22450: no caller
// reads it).  N / Z: 22180 (BLT after the TST.B 9d(A6) of 22174 and a LEA) recomputes the N from the BYTE 9d(A6) (work RAM / fixed ROM only, else the
// checked flag-source error); no other flag crosses a C9 block boundary.
bool animation_player_c9_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool old=false;
    switch(r.pc) {
    // ---- 1d086 / 1d092 (BSR from 1f510 / 1f0fe): BSR.W 1cfbe (C4: A0 = the motion record) / MOVE.L 8(A0) / 4(A0),D1; BRA.W 1d0a4 (C4).
    case 0x1d086:case 0x1d092:return am_call(c,0x1cfbe,r.pc+4U);
    case 0x1d08a:case 0x1d096:if(!pc9_get(c,r.a[0],r.pc==0x1d08aU?8U:4U,4,r.d[1]))return false;r.pc=0x1d0a4;return true;
    // ---- 1ec74 (installed by 1fb28): CMPI.B #1,9e(A6); BNE.W 1ec98 / MOVEA.L #36350,A0; MOVE.W #1e,D0; JSR 28ae.l / MOVEQ #0,D0; MOVEQ #0,D1; JSR
    // 49214.l / LEA 1b764(PC),A0; BSR.W 1cb08 / BCC.W 1eba0 (C6; C of 1cb08) / BSR.W 1cab6 / CLR.L 64(A6); MOVE.B #1,a9(A6); MOVE.L #1ecb8,(A6) /
    // 1ecb8: JSR 1cd98(PC) / BTST.B #7,15(A6); BEQ.W 1fae8 / BTST.B #5,D0; BEQ.W 1ecee / CMPI.B #0,9e(A6); BNE.W 1ece0 / BTST.B #1,D0; BNE.W 1f7a4 /
    // MOVE.W #c,D1; AND.W D0,D1; BNE.W 1fa68 / BRA.W 1fa3c / BTST.B #1,D0; BNE.W 1f2a4 / BTST.B #7,D0; BNE.W 1f1d8 / JSR 4bfc0.l / MOVE.W 1e(A6),D0;
    // JSR ce02.l / JSR 49fc6.l / BCC.W 1ed1e (C of 49fc6) / MOVE.L #1ed78,(A6) / BRA.W 201a2.
    case 0x1ec74:return pc9_byte_is(c,0x9e,1,0x1ec7e,0x1ec98);
    case 0x1ec7e:return pc9_child(c,0x36350,0x1ec8e);
    case 0x1ec8e:r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,0x1ec98);
    case 0x1ec98:r.a[0]=0x1b764;return am_call(c,0x1cb08,0x1eca0);
    case 0x1eca0:return pc9_carry(c,0x1eba0,0x1eca4);
    case 0x1eca4:case 0x1f086:return am_call(c,0x1cab6,r.pc+4U);                                         // BSR.W 1cab6.
    case 0x1eca8:
        if(!pc9_put(c,r.a[6],0x64,4,0) || !pc9_put(c,r.a[6],0xa9,1,1))return false;return pc9_install(c,0x1ecb8,0x1ecb8);
    case 0x1ecb8:case 0x1f0ae:case 0x1f4b6:case 0x21ce6:case 0x21d38:case 0x2224e:case 0x2242a:return am_call(c,0x1cd98,r.pc+4U);  // BSR.W / JSR (PC) 1cd98.
    case 0x1ecbc:case 0x1f0b2:return pc9_field_bit(c,0x15,7,0x1fae8,r.pc+0xaU);
    case 0x1ecc6:pc9_input_bit(r,5,0x1ecee,0x1ecce);return true;
    case 0x1ecce:return pc9_byte_is(c,0x9e,0,0x1ecd8,0x1ece0);
    case 0x1ecd8:pc9_input_bit(r,1,0x1ece0,0x1f7a4);return true;
    case 0x1ece0:pc9_mask(r,0xc,0x1ecea,0x1fa68);return true;
    case 0x1ecea:case 0x1f0e0:r.pc=0x1fa3c;return true;                                                   // BRA.W 1fa3c.
    case 0x1ecee:pc9_input_bit(r,1,0x1ecf6,0x1f2a4);return true;
    case 0x1ecf6:pc9_input_bit(r,7,0x1ecfe,0x1f1d8);return true;
    case 0x1ecfe:case 0x1f102:case 0x1f514:return am_call(c,0x4bfc0,r.pc+6U);                            // JSR 4bfc0.l.
    case 0x1ed04:case 0x1f108:case 0x1f51a:case 0x20b2e:case 0x20c1c:return pc9_field_call(c,0x1e,0xce02,r.pc+0xaU);  // MOVE.W 1e(A6),D0; JSR ce02.l.
    case 0x1ed0e:case 0x1f112:case 0x1f524:case 0x20b38:case 0x20c26:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.l.
    case 0x1ed14:return pc9_carry(c,0x1ed1e,0x1ed18);
    case 0x1ed18:return pc9_install(c,0x1ed78,0x1ed1e);                                                   // MOVE.L #1ed78,(A6) (C2).
    case 0x1ed1e:case 0x1f122:case 0x1f534:r.pc=0x201a2;return true;                                     // BRA.W 201a2.
    // ---- 1f070 (C4 1ef0e state branch): BCHG.B #0,15(A6); LEA 1b1ec(PC),A0; TST.B 9d(A6); BLE.W 1f086 (0 or negative BYTE) / 1f082 (C10) / 1f086:
    // BSR.W 1cab6 / MOVE.B #1,a9(A6); MOVE.L #21602,84(A6); MOVE.B #0,9c(A6); MOVE.B #1,aa(A6); CLR.W 7a(A6); MOVE.L #1f0ae,(A6) / 1f0ae: BSR.W 1cd98 /
    // BTST.B #7,15(A6); BEQ.W 1fae8 / BTST.B #5,D0; BEQ.W 1f0e4 / CMPI.B #0,9e(A6); BNE.W 1f0d6 / BTST.B #1,D0; BNE.W 1f7a4 / MOVE.W #c,D1; AND.W
    // D0,D1; BNE.W 1fa68 / BRA.W 1fa3c / BTST.B #1,D0; BNE.W 1f2a4 / BTST.B #7,D0; BNE.W 1f1d8 / MOVE.W #50,D1; AND.W D0,D1; BNE.W 1eeea / BSR.W
    // 1d092 / JSR 4bfc0.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l / BCC.W 1f122 (C of 49fc6) / MOVE.L #1eeea,(A6) / BRA.W 201a2.
    case 0x1f070:
        if(!pc9_bit(c,0x15,0,3,old))return false;r.a[0]=0x1b1ec;if(!pc9_get(c,r.a[6],0x9d,1,value))return false;
        r.pc=(value==0U || (value&0x80U)!=0U)?0x1f086:0x1f082;return true;
    case 0x1f08a:
        if(!pc9_put(c,r.a[6],0xa9,1,1) || !pc9_put(c,r.a[6],0x84,4,0x21602) || !pc9_put(c,r.a[6],0x9c,1,0) || !pc9_put(c,r.a[6],0xaa,1,1) ||
           !pc9_put(c,r.a[6],0x7a,2,0))return false;
        return pc9_install(c,0x1f0ae,0x1f0ae);
    case 0x1f0bc:pc9_input_bit(r,5,0x1f0e4,0x1f0c4);return true;
    case 0x1f0c4:return pc9_byte_is(c,0x9e,0,0x1f0ce,0x1f0d6);
    case 0x1f0ce:pc9_input_bit(r,1,0x1f0d6,0x1f7a4);return true;
    case 0x1f0d6:pc9_mask(r,0xc,0x1f0e0,0x1fa68);return true;
    case 0x1f0e4:pc9_input_bit(r,1,0x1f0ec,0x1f2a4);return true;
    case 0x1f0ec:pc9_input_bit(r,7,0x1f0f4,0x1f1d8);return true;
    case 0x1f0f4:pc9_mask(r,0x50,0x1f0fe,0x1eeea);return true;
    case 0x1f0fe:return am_call(c,0x1d092,0x1f102);
    case 0x1f118:return pc9_carry(c,0x1f122,0x1f11c);
    case 0x1f11c:return pc9_install(c,0x1eeea,0x1f122);                                                   // MOVE.L #1eeea,(A6) (C2).
    // ---- 1f3e8 (written by C7 1f334 1f5c8, C8 1f480, C9 1f52e): LEA 1b26e(PC),A0 (falls into C8 1f3ec).
    case 0x1f3e8:r.a[0]=0x1b26e;r.pc=0x1f3ec;return true;
    // ---- 1f48a (C8 1f462 BNE): LEA 1b2cc(PC),A0; BSR.W 1cab6 / MOVE.L #21602,84(A6); MOVE.B #0,9c(A6); MOVE.B #1,aa(A6); CLR.W 7a(A6); MOVE.B
    // #2,a9(A6); MOVE.L #1f4b6,(A6) / 1f4b6: BSR.W 1cd98 / BTST.B #7,15(A6); BEQ.W 1fad2 / BTST.B #5,D0; BEQ.W 1f4e2 / CMPI.B #0,9e(A6); BNE.W 1f4de /
    // BTST.B #1,D0; BNE.W 1f7a4 / BRA.W 1f76e / BTST.B #1,D0; BEQ.W 1eb98 / BSR.W 1cec2 / CMPI.W #1,D1; BEQ.W 1f538 / MOVE.W #c,D1; AND.W D0,D1;
    // BEQ.W 1f3e8 / BTST.B #6,D0; BNE.W 1f5d2 / BTST.B #4,D0; BNE.W 1f5f2 / BSR.W 1d086 / JSR 4bfc0.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l /
    // BCC.W 1f534 (C of 49fc6) / MOVE.L #1f3e8,(A6) / BRA.W 201a2.
    case 0x1f48a:r.a[0]=0x1b2cc;return am_call(c,0x1cab6,0x1f492);
    case 0x1f492:if(!pc9_slot(c) || !pc9_put(c,r.a[6],0xa9,1,2))return false;return pc9_install(c,0x1f4b6,0x1f4b6);
    case 0x1f4ba:return pc9_field_bit(c,0x15,7,0x1fad2,0x1f4c4);
    case 0x1f4c4:pc9_input_bit(r,5,0x1f4e2,0x1f4cc);return true;
    case 0x1f4cc:return pc9_byte_is(c,0x9e,0,0x1f4d6,0x1f4de);
    case 0x1f4d6:pc9_input_bit(r,1,0x1f4de,0x1f7a4);return true;
    case 0x1f4de:r.pc=0x1f76e;return true;                                                                 // BRA.W 1f76e (C7).
    case 0x1f4e2:pc9_input_bit(r,1,0x1eb98,0x1f4ea);return true;
    case 0x1f4ea:return am_call(c,0x1cec2,0x1f4ee);
    case 0x1f4ee:r.pc=(r.d[1]&0xffffU)==1U?0x1f538:0x1f4f6;return true;                                 // CMPI.W #1,D1; BEQ.W 1f538 (C7).
    case 0x1f4f6:pc9_mask(r,0xc,0x1f3e8,0x1f500);return true;                                            // ... BEQ.W 1f3e8.
    case 0x1f500:pc9_input_bit(r,6,0x1f508,0x1f5d2);return true;
    case 0x1f508:pc9_input_bit(r,4,0x1f510,0x1f5f2);return true;
    case 0x1f510:return am_call(c,0x1d086,0x1f514);
    case 0x1f52a:return pc9_carry(c,0x1f534,0x1f52e);
    case 0x1f52e:return pc9_install(c,0x1f3e8,0x1f534);
    // ---- 1fb28 (C8 1fb24 BEQ fall-through): MOVE.L #1ec74,(A6) (falls into C8 1fb2e).
    case 0x1fb28:return pc9_install(c,0x1ec74,0x1fb2e);
    // ---- 20720 (falls into C5 20738): CMPI.W #a0,42(A6); SPL.B 5f(A6) (ff when the WORD difference is not negative: bit 15 clear); MOVE.L
    // #a9800,3a(A6); MOVE.B #ff,5e(A6).
    case 0x20720:
        if(!pc9_get(c,r.a[6],0x42,2,value))return false;
        if(!pc9_put(c,r.a[6],0x5f,1,(((value-0xa0U)&0x8000U)==0U)?0xffU:0U) || !pc9_put(c,r.a[6],0x3a,4,0xa9800) || !pc9_put(c,r.a[6],0x5e,1,0xff))
            return false;
        r.pc=0x20738;return true;
    // ---- 208fa (state branch): JSR ea680.l / BCC.W 2091e (C of ea680) / JSR 1aa3a.l / BTST.B #1,D0; BNE.W 20a98 / BTST.B #b,D0 (the LONG bit 11);
    // BNE.W 21370 / BRA.W 20b42 / JSR 1aa3a.l / BTST.B #9,D0; BNE.W 20cd8 / (2092c, C5).
    case 0x208fa:case 0x20a4a:case 0x20bcc:return am_call(c,0xea680,r.pc+6U);                            // JSR ea680.l.
    case 0x20900:return pc9_carry(c,0x2091e,0x20904);
    case 0x20904:case 0x2091e:case 0x20b42:return am_call(c,0x1aa3a,r.pc+6U);                            // JSR 1aa3a.l.
    case 0x2090a:pc9_input_bit(r,1,0x20912,0x20a98);return true;
    case 0x20912:pc9_input_bit(r,11,0x2091a,0x21370);return true;
    case 0x2091a:r.pc=0x20b42;return true;
    case 0x20924:pc9_input_bit(r,9,0x2092c,0x20cd8);return true;
    // ---- 20a4a (BSR from 20af4 20b9e): JSR ea680.l / BCC.W 20a6e (C of ea680) / ADD.L 18(A0),D1 (A0 / D1 of ea680); SUB.L 46(A6),D1; ASR.L #3,D1;
    // MOVE.L D1,3a(A6); MOVE.L 36(A6),D0; ASR.L #3,D0; SUB.L D0,36(A6); RTS / MOVEQ #0,D2; MOVE.L #fffc0000,D3; SUB.L 36(A6),D2; BMI.W 20a80 /
    // ADDQ.L #7,D2 / ASR.L #3,D2; ADD.L D2,36(A6); SUB.L 3a(A6),D3; BMI.W 20a90 / ADDQ.L #7,D3 / ASR.L #3,D3; ADD.L D3,3a(A6); RTS.  (LONG arithmetic
    // modulo 2^32; no caller reads the flags of the RTS.)
    case 0x20a50:return pc9_carry(c,0x20a6e,0x20a54);
    case 0x20a54:
        if(!pc9_get(c,r.a[0],0x18,4,value))return false;r.d[1]+=value;if(!pc9_get(c,r.a[6],0x46,4,value))return false;r.d[1]-=value;
        r.d[1]=pc9_asr(r.d[1],3);if(!pc9_put(c,r.a[6],0x3a,4,r.d[1]) || !pc9_get(c,r.a[6],0x36,4,r.d[0]))return false;r.d[0]=pc9_asr(r.d[0],3);
        if(!pc9_get(c,r.a[6],0x36,4,value) || !pc9_put(c,r.a[6],0x36,4,value-r.d[0]))return false;
        return am_return(c);
    case 0x20a6e:return pc9_settle(c,0xfffc0000U,0x20a7e,0x20a80);
    case 0x20b00:return pc9_settle(c,0xfffc0000U,0x20b10,0x20b12);
    case 0x20bee:return pc9_settle(c,0xfffd0000U,0x20bfe,0x20c00);                                      // 20bfe: ADDQ.L #7,D2 (C10).
    case 0x20a7e:case 0x20b10:r.d[2]+=7U;r.pc+=2U;return true;                                           // ADDQ.L #7,D2.
    case 0x20a8e:case 0x20b20:case 0x20c0e:r.d[3]+=7U;r.pc+=2U;return true;                              // ADDQ.L #7,D3.
    case 0x20a80:return pc9_settle_x(c,0x20a8e,0x20a90);
    case 0x20b12:return pc9_settle_x(c,0x20b20,0x20b22);
    case 0x20c00:return pc9_settle_x(c,0x20c0e,0x20c10);
    case 0x20a90:return pc9_settle_y(c,0);
    case 0x20b22:return pc9_settle_y(c,0x20b28);
    case 0x20c10:return pc9_settle_y(c,0x20c16);
    // ---- 20a98 (2090a BNE): JSR 49274.l / JSR 8ff4.l / the sound WORD of the table 1b178 (8ebe) / LEA 1bc5a(PC),A0; BSR.W 1cb38 / CLR.L 3a(A6);
    // MOVE.W #1e,88(A6); the slot part; MOVE.L #20aec,(A6) / 20aec: TST.W 88(A6); BEQ.W 20b00 / SUBQ.W #1,88(A6); BSR.W 20a4a / BRA.W 20b28 / (20b00:
    // the settle above) / JSR 43ea4.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l / BRA.W 21520 (C5).
    case 0x20a98:case 0x20b60:return am_call(c,0x49274,r.pc+6U);                                         // JSR 49274.l.
    case 0x20a9e:case 0x21370:return am_call(c,0x8ff4,r.pc+6U);                                          // JSR 8ff4.l.
    case 0x20aa4:return pc9_table_sound(c,0x1b178,0x20abc);
    case 0x20abc:r.a[0]=0x1bc5a;return am_call(c,0x1cb38,0x20ac4);
    case 0x20ac4:
        if(!pc9_put(c,r.a[6],0x3a,4,0) || !pc9_put(c,r.a[6],0x88,2,0x1e) || !pc9_slot(c))return false;return pc9_install(c,0x20aec,0x20aec);
    case 0x20aec:if(!pc9_get(c,r.a[6],0x88,2,value))return false;r.pc=value==0U?0x20b00:0x20af4;return true;
    case 0x20af4:if(!pc9_get(c,r.a[6],0x88,2,value) || !pc9_put(c,r.a[6],0x88,2,value-1U))return false;return am_call(c,0x20a4a,0x20afc);
    case 0x20afc:r.pc=0x20b28;return true;
    case 0x20b28:case 0x20c16:case 0x20d36:return am_call(c,0x43ea4,r.pc+6U);                            // JSR 43ea4.l.
    case 0x20b3e:case 0x20c2c:case 0x20d6e:r.pc=0x21520;return true;                                     // BRA.W 21520 (C5).
    // ---- 20b42 (2091a): JSR 1aa3a.l / BTST.B #4,D0; BEQ.W 20b60 / the child 371f8 (28ae) / JSR 49274.l / LEA 1bc5c(PC),A0; BSR.W 1cb38 / CLR.L
    // 3a(A6); MOVE.W #14,88(A6); the slot part; MOVE.L #20b96,(A6) / 20b96: TST.W 88(A6); BEQ.W 20bb8 / SUBQ.W #1,88(A6); MOVE.W #40,D0; SUB.W
    // 2c(A6),D0; ASR.W #3,D0; ADD.W D0,2c(A6); BSR.W 20a4a / BRA.W 20c16 / MOVE.W #100,2c(A6); JSR 1aa3a.l / BTST.B #4,D0; BEQ.W 20bee / JSR ea680.l /
    // BCC.W 20bee (C of ea680) / SWAP D1; ADD.W 18(A0),D1; SUB.W 46(A6),D1; CMPI.W #28,D1; BCS.W 20bee (unsigned WORD) / MOVE.L #20c30,(A6) (written
    // only) / (20bee: the settle above with fffd0000) / JSR 43ea4.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l / BRA.W 21520.
    case 0x20b48:pc9_input_bit(r,4,0x20b60,0x20b50);return true;
    case 0x20b50:return pc9_child(c,0x371f8,0x20b60);
    case 0x20b66:case 0x20d02:r.a[0]=0x1bc5c;return am_call(c,0x1cb38,r.pc+8U);                          // LEA 1bc5c(PC),A0; BSR.W 1cb38.
    case 0x20b6e:
        if(!pc9_put(c,r.a[6],0x3a,4,0) || !pc9_put(c,r.a[6],0x88,2,0x14) || !pc9_slot(c))return false;return pc9_install(c,0x20b96,0x20b96);
    case 0x20b96:if(!pc9_get(c,r.a[6],0x88,2,value))return false;r.pc=value==0U?0x20bb8:0x20b9e;return true;
    case 0x20b9e:
        if(!pc9_get(c,r.a[6],0x88,2,value) || !pc9_put(c,r.a[6],0x88,2,value-1U) || !pc9_get(c,r.a[6],0x2c,2,value))return false;
        am_word(r.d[0],0x40U-value);pc9_asr_word(r.d[0],3);
        if(!pc9_get(c,r.a[6],0x2c,2,value) || !pc9_put(c,r.a[6],0x2c,2,value+r.d[0]))return false;return am_call(c,0x20a4a,0x20bb4);
    case 0x20bb4:r.pc=0x20c16;return true;
    case 0x20bb8:if(!pc9_put(c,r.a[6],0x2c,2,0x100))return false;return am_call(c,0x1aa3a,0x20bc4);
    case 0x20bc4:pc9_input_bit(r,4,0x20bee,0x20bcc);return true;
    case 0x20bd2:return pc9_carry(c,0x20bee,0x20bd6);
    case 0x20bd6:
        am_swap(r.d[1]);if(!pc9_get(c,r.a[0],0x18,2,value))return false;am_word(r.d[1],r.d[1]+value);
        if(!pc9_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],r.d[1]-value);
        r.pc=(r.d[1]&0xffffU)<0x28U?0x20bee:0x20be8;return true;
    case 0x20be8:return pc9_install(c,0x20c30,0x20bee);                                                   // MOVE.L #20c30,(A6) (written only).
    // ---- 20cd8 (20924 BNE): the child eaac0 (28ae) / MOVE.W #0,D0; MOVE.W #0,D1; JSR 4970a.l / MOVE.W #2,76(A0) (A0 of 4970a); JSR 49274.l /
    // LEA 1bc5c(PC),A0; BSR.W 1cb38 / CLR.L 3a(A6); CLR.L 36(A6); MOVE.W #14,88(A6); the slot part; MOVE.L #20d36,(A6) / 20d36: JSR 43ea4.l /
    // SUBQ.W #1,88(A6); BCC.W 20d6e (no borrow: the WORD was not 0) / the child eaac0 / MOVE.W #0,D0; MOVE.W #0,D1; JSR 4970a.l / MOVE.W #1,76(A0);
    // MOVE.L #21542,(A6) / BRA.W 21520.
    case 0x20cd8:case 0x20d44:return pc9_child(c,0xeaac0,r.pc+0x10U);
    case 0x20ce8:case 0x20d54:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,r.pc+0xeU);
    case 0x20cf6:if(!pc9_put(c,r.a[0],0x76,2,2))return false;return am_call(c,0x49274,0x20d02);
    case 0x20d0a:
        if(!pc9_put(c,r.a[6],0x3a,4,0) || !pc9_put(c,r.a[6],0x36,4,0) || !pc9_put(c,r.a[6],0x88,2,0x14) || !pc9_slot(c))return false;
        return pc9_install(c,0x20d36,0x20d36);
    case 0x20d3c:if(!pc9_get(c,r.a[6],0x88,2,value) || !pc9_put(c,r.a[6],0x88,2,value-1U))return false;r.pc=value!=0U?0x20d6e:0x20d44;return true;
    case 0x20d62:if(!pc9_put(c,r.a[0],0x76,2,1))return false;return pc9_install(c,0x21542,0x20d6e);
    // ---- 21370 (20912 BNE): JSR 8ff4.l / the sound WORD of the table 1b170 (8ebe), twice / MOVE.B 19(A6),14(A6); LEA 1bc56(PC),A0; BSR.W 1cb38 /
    // the slot part; BSR.W 20efc (C5) / MOVE.W #80,88(A6); BRA.W 21430 (C5).
    case 0x21376:return pc9_table_sound(c,0x1b170,0x2138e);
    case 0x2138e:return pc9_table_sound(c,0x1b170,0x213a6);
    case 0x213a6:if(!pc9_get(c,r.a[6],0x19,1,value) || !pc9_put(c,r.a[6],0x14,1,value))return false;r.a[0]=0x1bc56;return am_call(c,0x1cb38,0x213b4);
    case 0x213b4:if(!pc9_slot(c))return false;return am_call(c,0x20efc,0x213d0);
    case 0x213d0:if(!pc9_put(c,r.a[6],0x88,2,0x80))return false;r.pc=0x21430;return true;
    // ---- 21ca4 (C3 21c22 BGT): BCLR.B #5,a7(A6); BSR.W 21bc6 / BCS.W 223b2 / BSR.W 21baa / BCS.W 223b2 / BSR.W 21c1c / BCS.W 223b2 (C of 21bc6 /
    // 21baa / 21c1c) / LEA 1b880(PC),A0; BSR.W 1cabe / MOVE.B #1,aa(A6); MOVE.L #21cd8,84(A6) / 21cd8: LEA 21aee(PC),A0; BSR.W 215e6 / BCC.W 21ce6 (C
    // of 215e6) / JMP (A1) (list 21aee) / BSR.W 1cd98 / BTST.B #1 / #0 / #6 / #4,D0: BNE 223c4 / BEQ 223b2 / BNE 21ffc / BNE 2210c / BRA.W 2156a.
    case 0x21ca4:if(!pc9_bit(c,0xa7,5,2,old))return false;return am_call(c,0x21bc6,0x21cae);
    case 0x21cae:case 0x21cb6:case 0x21cbe:return pc9_carry(c,r.pc+4U,0x223b2);
    case 0x21cb2:return am_call(c,0x21baa,0x21cb6);
    case 0x21cba:return am_call(c,0x21c1c,0x21cbe);
    case 0x21cc2:r.a[0]=0x1b880;return am_call(c,0x1cabe,0x21cca);
    case 0x21cca:if(!pc9_put(c,r.a[6],0xaa,1,1))return false;return pc9_slot84(c,0x21cd8,0x21cd8);
    case 0x21cd8:r.a[0]=0x21aee;return am_call(c,0x215e6,0x21ce0);
    case 0x21ce0:return pc9_carry(c,0x21ce6,0x21ce4);
    case 0x21ce4:return pc9_list_jump(c,PC9_LIST_21AEE,4U);
    case 0x21cea:pc9_input_bit(r,1,0x21cf2,0x223c4);return true;
    case 0x21cf2:pc9_input_bit(r,0,0x223b2,0x21cfa);return true;
    case 0x21cfa:case 0x21d4c:case 0x22252:case 0x2242e:pc9_input_bit(r,6,r.pc+8U,0x21ffc);return true; // BTST.B #6,D0; BNE.W 21ffc (C3).
    case 0x21d02:case 0x21d54:case 0x22436:pc9_input_bit(r,4,r.pc+8U,0x2210c);return true;              // BTST.B #4,D0; BNE.W 2210c.
    case 0x21d0a:case 0x21d5c:r.pc=0x2156a;return true;                                                   // BRA.W 2156a (C3).
    // ---- 21d0e (C3 21c22 BLT, C8 21e5a BLT): BCLR.B #5,a7(A6); LEA 1b942(PC),A0; BSR.W 1cabe / MOVE.B #1,aa(A6); MOVE.L #21d2a,84(A6) / 21d2a: LEA
    // 216c8(PC),A0; BSR.W 215e6 / BCC.W 21d38 / JMP (A1) (list 216c8) / BSR.W 1cd98 / BTST.B #0 / #1 / #6 / #4,D0: BNE 223fa (C10) / BEQ 223e8 /
    // BNE 21ffc / BNE 2210c / BRA.W 2156a.
    case 0x21d0e:if(!pc9_bit(c,0xa7,5,2,old))return false;r.a[0]=0x1b942;return am_call(c,0x1cabe,0x21d1c);
    case 0x21d1c:if(!pc9_put(c,r.a[6],0xaa,1,1))return false;return pc9_slot84(c,0x21d2a,0x21d2a);
    case 0x21d2a:case 0x22240:case 0x2241c:r.a[0]=0x216c8;return am_call(c,0x215e6,r.pc+8U);           // LEA 216c8(PC),A0; BSR.W 215e6.
    case 0x21d32:return pc9_carry(c,0x21d38,0x21d36);
    case 0x21d36:case 0x2224c:case 0x22428:return pc9_list_jump(c,PC9_LIST_216C8,1U);
    case 0x21d3c:pc9_input_bit(r,0,0x21d44,0x223fa);return true;
    case 0x21d44:pc9_input_bit(r,1,0x223e8,0x21d4c);return true;
    // ---- 21e48 (a handler of the lists 21622 / 21aee / 21b0a / 21b26): MOVE.B #1,aa(A6); LEA 1b9a8(PC),A0 (falls into C8 21e52).
    case 0x21e48:if(!pc9_put(c,r.a[6],0xaa,1,1))return false;r.a[0]=0x1b9a8;r.pc=0x21e52;return true;
    // ---- 2210c (slot-84 value; BNE from 21d06 21d58 2243a 22268, C3 21c90 / C8 21e98): BCLR.B #5,a7(A6); BSR.W 1cd98 / BTST.B #0,D0; SEQ.B D1; BTST.B
    // #1,D0; SEQ.B D2; SUB.B D2,D1; MOVE.B D1,9d(A6) / 22128 (slot-84 value): CLR.B 7e(A6); ANDI.B #ef,a5(A6); ANDI.B #ef,a6(A6); MOVE.B #2,aa(A6);
    // BTST.B #0,a7(A6); BEQ.W 22174 / (22148, C10) / TST.B 9d(A6); LEA 22074(PC),A0; BGT.W 2218c (signed BYTE) / LEA 220c0(PC),A0; BLT.W 2218c (the N of
    // the same TST, recomputed from the BYTE 9d) / LEA 22028(PC),A0 / MOVEA.L 8c(A6),A4; MOVEQ #0,D0; MOVE.B 4(A4),D0; ADD.W D0,D0; ADD.W D0,D0;
    // MOVEA.L (A0,D0.W),A0 (fixed ROM LONG table, live bus); BSR.W 1cabe / MOVEA.L 8c(A6),A4; MOVE.B 4(A4),D0; CMPI.B #5 / #a,D0; BEQ.W 22286 (C10) /
    // CMPI.B #6 / #b,D0; BEQ.W 22238 / (221ca, C3).
    case 0x2210c:if(!pc9_bit(c,0xa7,5,2,old))return false;return am_call(c,0x1cd98,0x22116);
    case 0x22116:
        am_byte(r.d[1],(r.d[0]&1U)==0U?0xffU:0U);am_byte(r.d[2],(r.d[0]&2U)==0U?0xffU:0U);am_byte(r.d[1],r.d[1]-r.d[2]);
        if(!pc9_put(c,r.a[6],0x9d,1,r.d[1]))return false;r.pc=0x22128;return true;
    case 0x22128:
        if(!pc9_put(c,r.a[6],0x7e,1,0) || !pc9_get(c,r.a[6],0xa5,1,value) || !pc9_put(c,r.a[6],0xa5,1,value&0xefU) ||
           !pc9_get(c,r.a[6],0xa6,1,value) || !pc9_put(c,r.a[6],0xa6,1,value&0xefU) || !pc9_put(c,r.a[6],0xaa,1,2))return false;
        return pc9_field_bit(c,0xa7,0,0x22174,0x22148);
    case 0x22174:
        if(!pc9_get(c,r.a[6],0x9d,1,value))return false;r.a[0]=0x22074;r.pc=(value!=0U && (value&0x80U)==0U)?0x2218c:0x22180;return true;
    case 0x22180: {
        const std::uint32_t at=am_index(r.a[6],0x9d);
        if((at&0xffffffU)>=0x200000U)return am_error(c,"unsupported animation player c9 flag source");
        if(!am_read(c,at,1,value))return false;r.a[0]=0x220c0;r.pc=(value&0x80U)!=0U?0x2218c:0x22188;return true;
    }
    case 0x22188:r.a[0]=0x22028;r.pc=0x2218c;return true;
    case 0x2218c:
        if(!pc9_get(c,r.a[6],0x8c,4,r.a[4]))return false;r.d[0]=0;if(!pc9_get(c,r.a[4],4,1,value))return false;am_byte(r.d[0],value);
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),4,r.a[0]))return false;
        return am_call(c,0x1cabe,0x221a2);
    case 0x221a2:
        if(!pc9_get(c,r.a[6],0x8c,4,r.a[4]) || !pc9_get(c,r.a[4],4,1,value))return false;am_byte(r.d[0],value);
        r.pc=value==5U?0x22286:0x221b2;return true;
    case 0x221b2:r.pc=(r.d[0]&0xffU)==0xaU?0x22286:0x221ba;return true;
    case 0x221ba:r.pc=(r.d[0]&0xffU)==6U?0x22238:0x221c2;return true;
    case 0x221c2:r.pc=(r.d[0]&0xffU)==0xbU?0x22238:0x221ca;return true;
    // ---- 22238: MOVE.L #22240,84(A6) / 22240 (slot-84 value): LEA 216c8(PC),A0; BSR.W 215e6 / BCC.W 2224e / JMP (A1) (list 216c8) / BSR.W 1cd98 /
    // BTST.B #6,D0; BNE.W 21ffc / TST.B 7e(A6); BEQ.W 22272 / BTST.B #4,a5(A6); BNE.W 2210c / BTST.B #1,aa(A6) (its Z is not read) / BSR.W 2156a /
    // TST.W D7; BEQ.W 22284 / MOVE.L #22452,84(A6) / RTS.
    case 0x22238:return pc9_slot84(c,0x22240,0x22240);
    case 0x22248:return pc9_carry(c,0x2224e,0x2224c);
    case 0x2225a:return pc9_byte_is(c,0x7e,0,0x22272,0x22262);
    case 0x22262:return pc9_field_bit(c,0xa5,4,0x2226c,0x2210c);
    case 0x2226c:if(!pc9_bit(c,0xaa,1,0,old))return false;r.pc=0x22272;return true;
    case 0x22272:case 0x2243e:return am_call(c,0x2156a,r.pc+4U);                                         // BSR.W 2156a.
    case 0x22276:case 0x22442:r.pc=(r.d[7]&0xffffU)==0U?r.pc+0xeU:r.pc+6U;return true;                  // TST.W D7; BEQ.W the RTS.
    case 0x2227c:case 0x22448:return pc9_slot84(c,0x22452,r.pc+8U);                                     // MOVE.L #22452,84(A6).
    case 0x22284:case 0x22450:return am_return(c);                                                        // RTS (no caller reads its flags).
    // ---- 223a0 / 223b2 / 223c4 / 223d6 / 223e8: MOVE.B #1 / #0 / #ff / #ff / #0,9d(A6); LEA 1b85e / 1b8ba / 1b8fe / 1b920 / 1b964(PC),A0; BSR.W 1cabe
    // / BRA.W 22408 / 22408: BCLR.B #5,a7(A6); MOVE.B #0,aa(A6); MOVE.L #2241c,84(A6) / 2241c (slot-84 value): LEA 216c8(PC),A0; BSR.W 215e6 / BCC.W
    // 2242a / JMP (A1) (list 216c8) / BSR.W 1cd98 / BTST.B #6,D0; BNE.W 21ffc / BTST.B #4,D0; BNE.W 2210c / BSR.W 2156a / TST.W D7; BEQ.W 22450 / MOVE.L
    // #22452,84(A6) / RTS / 22452 (slot-84 value): MOVE.B 9c(A6),D0; CMPI.B #3,D0; SEQ.B D1; CMPI.B #4,D0; SEQ.B D2; OR.B D2,D1; BEQ.W 2246e / MOVE.B
    // #1,9c(A6) / BRA.W 21602 (C3).
    case 0x223a0:return pc9_turn(c,1,0x1b85e,0x223ae);
    case 0x223b2:return pc9_turn(c,0,0x1b8ba,0x223c0);
    case 0x223c4:return pc9_turn(c,0xff,0x1b8fe,0x223d2);
    case 0x223d6:return pc9_turn(c,0xff,0x1b920,0x223e4);
    case 0x223e8:return pc9_turn(c,0,0x1b964,0x223f6);
    case 0x223ae:case 0x223c0:case 0x223d2:case 0x223e4:case 0x223f6:r.pc=0x22408;return true;          // BRA.W 22408.
    case 0x22408:
        if(!pc9_bit(c,0xa7,5,2,old) || !pc9_put(c,r.a[6],0xaa,1,0))return false;return pc9_slot84(c,0x2241c,0x2241c);
    case 0x22424:return pc9_carry(c,0x2242a,0x22428);
    case 0x22452:
        if(!pc9_get(c,r.a[6],0x9c,1,value))return false;am_byte(r.d[0],value);am_byte(r.d[1],value==3U?0xffU:0U);
        am_byte(r.d[2],value==4U?0xffU:0U);am_byte(r.d[1],r.d[1]|r.d[2]);r.pc=(r.d[1]&0xffU)==0U?0x2246e:0x22468;return true;
    case 0x22468:if(!pc9_put(c,r.a[6],0x9c,1,1))return false;r.pc=0x2246e;return true;
    case 0x2246e:r.pc=0x21602;return true;
    default:return am_error(c,"unsupported animation player c9 PC");
    }
}
}
