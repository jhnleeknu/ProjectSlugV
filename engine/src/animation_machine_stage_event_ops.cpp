#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (MOVE.L #, MOVEA.L #, LEA d16(PC), d(PC,Xn) tables).
const std::uint32_t SO_CHILD_FRAME=0xe9362;     // e935c MOVE.L #e9362,(A6)
const std::uint32_t SO_CHILD_CALLBACK=0xe9350;  // e963a MOVEA.L #e9350,A0
const std::uint32_t SO_EVENT_NODE=0x100bf4;     // e956a MOVEA.L #100bf4,A1
const std::uint32_t SO_OBJECT_TABLE=0xe8cc0;    // e9558 LEA e8cc0(PC),A1 (op 08 callback LONG table, fixed ROM)
const std::uint32_t SO_CHILD_OPCODES=0xe941c;   // e93f2 JSR e941c(PC,D7.W)
const std::uint32_t SO_OPCODES=0xe9538;         // e9534 JMP e9538(PC,D0.W)
const std::uint32_t SO_SKIP=0xe9790;            // e978c JMP e9790(PC,D0.W)
// d16(A5) operands use the live A5 (negative displacements are written as their 16-bit two's complement).
bool so_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool so_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
bool so_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
// MOVE/CLR to d16(An) (CLR is modeled as a write like the other units).
bool so_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// ADDQ.B #1,<ea>: BYTE read-modify-write, carry out discarded.
bool so_increment(AnimationMachineContext& c,std::uint32_t address) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    return am_write(c,address,1,(value+1U)&255U);
}
// ADDQ.B #1,80(A6); BCC clear_pc (no carry out), otherwise set_pc (the MOVE.B #ff,80(A6) block).
bool so_saturate(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!so_get(c,c.s.a[6],0x80,1,value))return false;
    if(!so_put(c,c.s.a[6],0x80,1,(value+1U)&255U))return false;
    c.s.pc=(value&255U)==255U?set_pc:clear_pc;return true;
}
// Consumers of a C returned by 288c/289e or 2986: BCC clear_pc / BCS set_pc.
bool so_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"stage event ops caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEQ #0,Dn; MOVE.B (A0),Dn (the opcode BYTE; odd stream addresses are allowed for BYTE reads).
bool so_opcode(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t& value) {
    d=0;if(!am_read(c,c.s.a[0],1,value))return false;value&=255U;am_byte(d,value);return true;
}
// SUBQ.B #n,Dn; BCC ok_pc (no borrow), otherwise borrow_pc (a TRAP #f boundary).
void so_subtract(AnimationMachineState& r,std::uint32_t& d,std::uint32_t n,std::uint32_t ok_pc,std::uint32_t borrow_pc) {
    const std::uint32_t value=d&255U;am_byte(d,(value-n)&255U);r.pc=value>=n?ok_pc:borrow_pc;
}
// CMPA.L <ea>,A0; BCS less_pc; BEQ equal_pc; otherwise the TRAP #f boundary trap_pc (F3 main decision 3: the BEQ
// after the BCS consumes the Z of the same CMPA and is bundled into this block).
void so_bound(AnimationMachineState& r,std::uint32_t limit,std::uint32_t less_pc,std::uint32_t equal_pc,std::uint32_t trap_pc) {
    r.pc=r.a[0]<limit?less_pc:(r.a[0]==limit?equal_pc:trap_pc);
}
}
// Stage event F3b: the opcode 08..0f loop e94fe/e951c with the e9538 opcode table (eight BRA.W slots) and the handlers
// e9558..e9768 (08 object creation through U7 2986 with the e8cc0 callback table, 09 child thread creation through 28ae,
// 0a condition, 0b run of a section, 0c random choice within a section (candidate LONG array on A7, 49a84), 0d saturating
// counter, 0e 1a92c, 0f screen range with F3a e9298), the skip routine e9774 with the e9790 table (eight BRA.W slots and
// the e97b0..e97c6 tails), the child thread callbacks e9350 (initialisation, falls into e9362) and e9362 (every frame)
// with the e941c child opcode table (three BRA.W slots into the F3a opcode 05..07 handlers), and the helpers 288c, 1a92c and
// 49a84. Existing executors called: cleanup 43e08/43e22/43e34, input 289e (known C), buffer_cue 2986 (known C), fade_card
// 28ae (known C, not consumed by op 09: on failure A0 = sentinel 100e98 is written as in the original) and 2a00, stage area
// 49a58 (its RNG pointer guard applies), F3a e9298, e9768 and e97c8. The e97c8 evaluator returns to e9396/e939e/e96b0
// are evaluated by the F3a e98ea block (F3 main decision 3); here e939a/e93a2/e96b4/e96b8 are block starts. The BCS
// fall-through BEQs e96d0/e96fe are bundled into e96cc/e96f8 (F3 main decision 3 option A). The eight TRAP #15 sites
// (e93d8 e9528 e9530 e957a e96d4 e9702 e9780 e9788) are boundaries without an executor. The e941c, e9538 and e9790
// computed PCs are followed as is (bounded by the original on the natural path; a target that is not a block start is
// unsupported). Loops (op 08 copy with an odd or negative length, child stream opcodes 10..7f, op 0a/0b/0c chains) have
// no extra limit (block budget only); writes outside work RAM are checked errors. ROM data (streams, the e8cc0 table) is
// read through the live bus; all d16(A5) operands use the live A5.
bool animation_stage_event_ops_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // 288c: MOVEA.L c(A6),A0; CMPA.W #0,A0; BNE 289e (CMPA.W sign-extends: full 32-bit test).
    case 0x288c:if(!so_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;r.pc=value?0x289e:0x2898;return true;
    case 0x2898:r.carry=AnimationCarrySet;return am_return(c); // ORI.B #1,CCR; RTS.
    // 1a92c: MOVE.W D0,5444(A5); MOVE.W D1,5446(A5); MOVE.W D2,5448(A5); MOVE.W D3,544a(A5); RTS.
    case 0x1a92c:
        if(!so_write(c,0x5444,2,r.d[0]&65535U) || !so_write(c,0x5446,2,r.d[1]&65535U) || !so_write(c,0x5448,2,r.d[2]&65535U) ||
           !so_write(c,0x544a,2,r.d[3]&65535U))return false;
        return am_return(c);
    case 0x49a84:am_word(r.d[7],r.d[0]);return am_call(c,0x49a58,0x49a88); // MOVE.W D0,D7; BSR 49a58.
    // MULU.W D7,D0; SWAP D0; RTS.
    case 0x49a88:r.d[0]=(r.d[0]&65535U)*(r.d[7]&65535U);am_swap(r.d[0]);return am_return(c);

    // e9350 (child callback): CLR.W 7e(A6); CLR.B 80(A6); CLR.B 81(A6); MOVE.L #e9362,(A6) (then e9362).
    case 0xe9350:
        if(!so_put(c,r.a[6],0x7e,2,0) || !so_put(c,r.a[6],0x80,1,0) || !so_put(c,r.a[6],0x81,1,0) ||
           !am_write(c,r.a[6],4,SO_CHILD_FRAME))return false;
        r.pc=0xe9362;return true;
    case 0xe9362:return am_call(c,0x43e34,0xe9368); // JSR 43e34.L.
    case 0xe9368:return am_call(c,0x288c,0xe936e);  // JSR 288c.L.
    case 0xe936e:return so_carry(c,0xe9428,0xe9372); // BCC e9428.
    // BTST #7,61(A0); BNE e9428.
    case 0xe9372:if(!so_get(c,r.a[0],0x61,1,value))return false;r.pc=(value&0x80U)?0xe9428:0xe937c;return true;
    // MOVE.L 7a(A6),D7; BEQ e93a2.
    case 0xe937c:if(!so_get(c,r.a[6],0x7a,4,value))return false;r.d[7]=value;r.pc=value?0xe9384:0xe93a2;return true;
    // MOVEA.L D7,A0; MOVE.W (A0)+,D0; CMP.W 5418(A5),D0; BLS e9428 (unsigned).
    case 0xe9384:
        r.a[0]=r.d[7];if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[0],value);
        if(!so_read(c,0x5418,2,other))return false;r.pc=(value&65535U)<=(other&65535U)?0xe9428:0xe9390;return true;
    case 0xe9390:r.a[1]=r.a[0];return am_call(c,0xe97c8,0xe9396); // MOVEA.L A0,A1; BSR e97c8 (e9396 BEQ in e98ea).
    case 0xe939a:return am_call(c,0xe97c8,0xe939e);                // BSR e97c8 (e939e BEQ in e98ea).
    // MOVE.L 76(A6),D7; MOVEA.L D7,A0.
    case 0xe93a2:if(!so_get(c,r.a[6],0x76,4,value))return false;r.d[7]=value;r.a[0]=value;r.pc=0xe93a8;return true;
    // MOVEQ #0,D7; MOVE.B (A0),D7; BPL e93be.
    case 0xe93a8:if(!so_opcode(c,r.d[7],value))return false;r.pc=(value&0x80U)?0xe93b0:0xe93be;return true;
    // MOVEA.L c(A6),A0; BSET #7,62(A0); BRA e9428.
    case 0xe93b0:
        if(!so_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!so_get(c,r.a[0],0x62,1,value) || !so_put(c,r.a[0],0x62,1,(value|0x80U)&255U))return false;
        r.pc=0xe9428;return true;
    case 0xe93be:r.pc=(r.d[7]&255U)<8U?0xe93d2:0xe93c6;return true; // CMPI.B #8,D7; BCS e93d2.
    case 0xe93c6:return am_call(c,0xe94fe,0xe93ca);                 // BSR e94fe.
    // MOVE.L A0,D7; MOVE.L D7,76(A6); BRA e93a8.
    case 0xe93ca:r.d[7]=r.a[0];if(!so_put(c,r.a[6],0x76,4,r.d[7]))return false;r.pc=0xe93a8;return true;
    case 0xe93d2:so_subtract(r,r.d[7],5,0xe93f0,0xe93d8);return true; // SUBQ.B #5,D7; BCC e93f0 (else TRAP e93d8).
    // LSL.W #2,D7; JSR e941c(PC,D7.W) (computed PC; bounded by e93ac/e93be/e93d2 on the natural path).
    case 0xe93f0:am_word(r.d[7],(r.d[7]&65535U)<<2);return am_call(c,am_index(SO_CHILD_OPCODES,r.d[7]),0xe93f6);
    // BCLR #0,81(A6); BEQ e93a8 (the previous bit 0 was clear).
    case 0xe93f6:
        if(!so_get(c,r.a[6],0x81,1,value) || !so_put(c,r.a[6],0x81,1,value&0xfeU))return false;
        r.pc=(value&1U)?0xe93fe:0xe93a8;return true;
    // MOVE.L A0,D7; MOVE.L D7,76(A6); MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L; RTS.
    case 0xe93fe:r.d[7]=r.a[0];if(!so_put(c,r.a[6],0x76,4,r.d[7]) || !am_zero_bank(c))return false;return am_return(c);
    // e941c child opcode table: three BRA.W slots (opcodes 05..07, F3a handlers).
    case 0xe941c:r.pc=0xe94b8;return true;
    case 0xe9420:r.pc=0xe94d0;return true;
    case 0xe9424:r.pc=0xe94f6;return true;
    // MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L; JMP 2a00.L (child self delete).
    case 0xe9428:if(!am_zero_bank(c))return false;r.pc=0x2a00;return true;

    // e94fe: MOVEQ #0,D0; MOVE.B (A0),D0; CMPI.B #10,D0; BCS e950c.
    case 0xe94fe:if(!so_opcode(c,r.d[0],value))return false;r.pc=value<0x10U?0xe950c:0xe950a;return true;
    case 0xe950a:case 0xe9514:case 0xe9722:return am_return(c); // RTS.
    case 0xe950c:r.pc=(r.d[0]&255U)>=8U?0xe9516:0xe9514;return true; // CMPI.B #8,D0; BCC e9516.
    case 0xe9516:return am_call(c,0xe951c,0xe951a);                  // BSR e951c.
    case 0xe951a:r.pc=0xe94fe;return true;                           // BRA e94fe.
    // e951c: MOVEQ #0,D0; MOVE.B (A0),D0; CMPI.B #10,D0; BCS e952a (else TRAP e9528).
    case 0xe951c:if(!so_opcode(c,r.d[0],value))return false;r.pc=value<0x10U?0xe952a:0xe9528;return true;
    case 0xe952a:so_subtract(r,r.d[0],8,0xe9532,0xe9530);return true; // SUBQ.B #8,D0; BCC e9532 (else TRAP e9530).
    // LSL.W #2,D0; JMP e9538(PC,D0.W) (computed PC; bounded by e9520/e952a on the natural path).
    case 0xe9532:am_word(r.d[0],(r.d[0]&65535U)<<2);r.pc=am_index(SO_OPCODES,r.d[0]);return true;
    // e9538 opcode table: eight BRA.W slots (opcodes 08..0f).
    case 0xe9538:r.pc=0xe9558;return true;
    case 0xe953c:r.pc=0xe962a;return true;
    case 0xe9540:r.pc=0xe96a4;return true;
    case 0xe9544:r.pc=0xe96bc;return true;
    case 0xe9548:r.pc=0xe96da;return true;
    case 0xe954c:r.pc=0xe975a;return true;
    case 0xe9550:r.pc=0xe9724;return true;
    case 0xe9554:r.pc=0xe9742;return true;

    // e9558 (opcode 08): LEA e8cc0(PC),A1; MOVE.W 8(A0),D0; MOVE.L A0,-(A7); MOVEA.L (A1,D0.W),A0; MOVE.W #0,D0;
    // MOVEA.L #100bf4,A1; JSR 2986.L (no range check on the table index).
    case 0xe9558:
        r.a[1]=SO_OBJECT_TABLE;if(!so_get(c,r.a[0],8,2,value))return false;am_word(r.d[0],value);
        if(!am_push(c,4,r.a[0]) || !am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[0]=value;
        am_word(r.d[0],0);r.a[1]=SO_EVENT_NODE;return am_call(c,0x2986,0xe9576);
    case 0xe9576:return so_carry(c,0xe957a,0xe958e); // BCS e958e (else TRAP e957a).
    case 0xe958e:return so_saturate(c,0xe959c,0xe9596); // ADDQ.B #1,80(A6); BCC e959c.
    case 0xe9596:if(!so_put(c,r.a[6],0x80,1,0xff))return false;r.pc=0xe959c;return true; // MOVE.B #ff,80(A6).
    // MOVEA.L (A7),A1; MOVEQ #0,D0; MOVE.B 2(A1),D0; CMPI.B #c,D0; BCC e95b8.
    case 0xe959c:
        if(!am_read(c,r.a[7],4,value))return false;r.a[1]=value;r.d[0]=0;
        if(!so_get(c,r.a[1],2,1,value))return false;am_byte(r.d[0],value);r.pc=(value&255U)>=0xcU?0xe95b8:0xe95ac;return true;
    // LEA 5e30(A5),A2; ADDQ.B #1,(A2,D0.W); BRA e95ba.
    case 0xe95ac:r.a[2]=am_index(r.a[5],0x5e30);if(!so_increment(c,am_index(r.a[2],r.d[0])))return false;r.pc=0xe95ba;return true;
    case 0xe95b8:r.d[0]=0xffffffffU;r.pc=0xe95ba;return true; // MOVEQ #ff,D0.
    // MOVE.B D0,6b(A0); MOVEQ #0,D0; MOVEQ #0,D1; MOVE.W 4(A1),D0; MOVE.W 6(A1),D1; SWAP D0; SWAP D1; MOVE.B 3(A1),D4;
    // LSR.B #1,D4; BCC e95e0 (C = flag bit 0).
    case 0xe95ba:{
        if(!so_put(c,r.a[0],0x6b,1,r.d[0]&255U))return false;r.d[0]=0;r.d[1]=0;
        if(!so_get(c,r.a[1],4,2,value))return false;am_word(r.d[0],value);
        if(!so_get(c,r.a[1],6,2,value))return false;am_word(r.d[1],value);
        am_swap(r.d[0]);am_swap(r.d[1]);
        if(!so_get(c,r.a[1],3,1,value))return false;am_byte(r.d[4],value);
        const bool bit=(r.d[4]&1U)!=0U;am_byte(r.d[4],(r.d[4]&255U)>>1);r.pc=bit?0xe95d8:0xe95e0;return true;}
    // ADD.L 46(A6),D1; SUB.L 53a6(A5),D1.
    case 0xe95d8:
        if(!so_get(c,r.a[6],0x46,4,value) || !so_read(c,0x53a6,4,other))return false;
        r.d[1]=r.d[1]+value;r.d[1]=r.d[1]-other;r.pc=0xe95e0;return true;
    // LSR.B #1,D4; BCC e95ee (C = flag bit 1).
    case 0xe95e0:{const bool bit=(r.d[4]&1U)!=0U;am_byte(r.d[4],(r.d[4]&255U)>>1);r.pc=bit?0xe95e6:0xe95ee;return true;}
    // ADD.L 42(A6),D0; SUB.L 53a2(A5),D0.
    case 0xe95e6:
        if(!so_get(c,r.a[6],0x42,4,value) || !so_read(c,0x53a2,4,other))return false;
        r.d[0]=r.d[0]+value;r.d[0]=r.d[0]-other;r.pc=0xe95ee;return true;
    // MOVE.B D4,6a(A0); MOVE.B D4,6a(A6); LEA 538e(A5),A1; LEA 2e(A0),A0; JSR 43e22.L.
    case 0xe95ee:
        if(!so_put(c,r.a[0],0x6a,1,r.d[4]&255U) || !so_put(c,r.a[6],0x6a,1,r.d[4]&255U))return false;
        r.a[1]=am_index(r.a[5],0x538e);r.a[0]=am_index(r.a[0],0x2e);return am_call(c,0x43e22,0xe9604);
    // LEA 48(A0),A1; MOVEA.L (A7)+,A0; MOVE.L A0,4a(A1); MOVEQ #0,D0; MOVE.B 1(A0),D0; SUBI.W #a,D0; BEQ e9626.
    case 0xe9604:
        r.a[1]=am_index(r.a[0],0x48);if(!am_pop(c,4,value))return false;r.a[0]=value;
        if(!so_put(c,r.a[1],0x4a,4,r.a[0]))return false;r.d[0]=0;
        if(!so_get(c,r.a[0],1,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],(r.d[0]&65535U)-0xaU);
        r.pc=(r.d[0]&65535U)?0xe961c:0xe9626;return true;
    case 0xe961c:r.a[2]=am_index(r.a[0],0xa);r.pc=0xe9620;return true; // LEA a(A0),A2.
    // MOVE.W (A2)+,(A1)+; SUBQ.W #2,D0; BNE e9620 (one WORD per block; an odd or negative count runs on to the block
    // budget or to a checked write outside work RAM, F3 main decision 7).
    case 0xe9620:
        if(!am_read(c,r.a[2],2,value))return false;r.a[2]+=2U;if(!am_write(c,r.a[1],2,value&65535U))return false;r.a[1]+=2U;
        am_word(r.d[0],(r.d[0]&65535U)-2U);r.pc=(r.d[0]&65535U)?0xe9620:0xe9626;return true;
    case 0xe9626:case 0xe973e:case 0xe97b0:r.pc=0xe9768;return true; // BRA e9768.
    // e962a (opcode 09): ADDQ.B #1,80(A6); BCC e9638.
    case 0xe962a:return so_saturate(c,0xe9638,0xe9632);
    case 0xe9632:if(!so_put(c,r.a[6],0x80,1,0xff))return false;r.pc=0xe9638;return true; // MOVE.B #ff,80(A6).
    // MOVE.L A0,-(A7); MOVEA.L #e9350,A0; MOVE.W #0,D0; JSR 28ae.L (C not tested: a failure leaves A0 = 100e98).
    case 0xe9638:if(!am_push(c,4,r.a[0]))return false;r.a[0]=SO_CHILD_CALLBACK;am_word(r.d[0],0);return am_call(c,0x28ae,0xe964a);
    // LEA 2e(A6),A1; MOVEQ #0,D0; MOVEQ #0,D1; LEA 2e(A0),A0; JSR 43e08.L.
    case 0xe964a:r.a[1]=am_index(r.a[6],0x2e);r.d[0]=0;r.d[1]=0;r.a[0]=am_index(r.a[0],0x2e);return am_call(c,0x43e08,0xe965c);
    // LEA -2e(A0),A0; MOVEA.L (A7)+,A1; MOVEQ #0,D0; MOVE.B 1(A1),D0; LEA (A1,D0.W),A2; MOVE.L A2,D0; MOVE.L D0,76(A0);
    // LEA 6(A1),A2; MOVE.L A2,D0; MOVE.L D0,7a(A0); MOVE.W 4(A1),D0; CMPI.W #c,D0; BCC e9694 (unsigned WORD).
    case 0xe965c:
        r.a[0]=am_index(r.a[0],0xffd2);if(!am_pop(c,4,value))return false;r.a[1]=value;r.d[0]=0;
        if(!so_get(c,r.a[1],1,1,value))return false;am_byte(r.d[0],value);
        r.a[2]=am_index(r.a[1],r.d[0]);r.d[0]=r.a[2];if(!so_put(c,r.a[0],0x76,4,r.d[0]))return false;
        r.a[2]=am_index(r.a[1],6);r.d[0]=r.a[2];if(!so_put(c,r.a[0],0x7a,4,r.d[0]))return false;
        if(!so_get(c,r.a[1],4,2,value))return false;am_word(r.d[0],value);
        r.pc=(r.d[0]&65535U)>=0xcU?0xe9694:0xe9688;return true;
    // LEA 5e30(A5),A2; ADDQ.B #1,(A2,D0.W); BRA e9696.
    case 0xe9688:r.a[2]=am_index(r.a[5],0x5e30);if(!so_increment(c,am_index(r.a[2],r.d[0])))return false;r.pc=0xe9696;return true;
    case 0xe9694:r.d[0]=0xffffffffU;r.pc=0xe9696;return true; // MOVEQ #ff,D0.
    // MOVE.B D0,6b(A0); MOVE.W 2(A1),D0; LEA (A1,D0.W),A0; RTS.
    case 0xe9696:
        if(!so_put(c,r.a[0],0x6b,1,r.d[0]&255U) || !so_get(c,r.a[1],2,2,value))return false;am_word(r.d[0],value);
        r.a[0]=am_index(r.a[1],r.d[0]);return am_return(c);
    // e96a4 (opcode 0a): LEA 2(A0),A1; BSR e9768.
    case 0xe96a4:r.a[1]=am_index(r.a[0],2);return am_call(c,0xe9768,0xe96ac);
    case 0xe96ac:return am_call(c,0xe97c8,0xe96b0); // BSR e97c8 (e96b0 BEQ in e98ea).
    case 0xe96b4:r.pc=0xe951c;return true;          // BRA e951c (condition true: run the next opcode).
    case 0xe96b8:case 0xe97c6:r.pc=0xe9774;return true; // BRA e9774 (skip the next opcode).
    // e96bc (opcode 0b): MOVE.W 2(A0),D0; PEA (A0,D0.W); BSR e9768.
    case 0xe96bc:
        if(!so_get(c,r.a[0],2,2,value))return false;am_word(r.d[0],value);
        if(!am_push(c,4,am_index(r.a[0],r.d[0])))return false;return am_call(c,0xe9768,0xe96c8);
    case 0xe96c8:return am_call(c,0xe951c,0xe96cc); // BSR e951c.
    // CMPA.L (A7),A0; BCS e96c8; BEQ e96d6 (else TRAP e96d4).
    case 0xe96cc:if(!am_read(c,r.a[7],4,value))return false;so_bound(r,value,0xe96c8,0xe96d6,0xe96d4);return true;
    case 0xe96d6:if(!am_pop(c,4,value))return false;r.a[0]=value;return am_return(c); // MOVEA.L (A7)+,A0; RTS.
    // e96da (opcode 0c): MOVE.W 2(A0),D0; LEA (A0,D0.W),A1; BSR e9768.
    case 0xe96da:
        if(!so_get(c,r.a[0],2,2,value))return false;am_word(r.d[0],value);r.a[1]=am_index(r.a[0],r.d[0]);
        return am_call(c,0xe9768,0xe96e6);
    case 0xe96e6:r.pc=r.a[1]==r.a[0]?0xe9722:0xe96ec;return true; // CMPA.L A0,A1; BEQ e9722 (empty section).
    case 0xe96ec:if(!am_push(c,4,r.a[1]))return false;r.a[1]=r.a[7];r.pc=0xe96f0;return true; // MOVE.L A1,-(A7); MOVEA.L A7,A1.
    // MOVE.L A0,-(A7); MOVE.L A1,-(A7); BSR e9774 (one candidate LONG per opcode of the section).
    case 0xe96f0:if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.a[1]))return false;return am_call(c,0xe9774,0xe96f8);
    // MOVEA.L (A7)+,A1; CMPA.L (A1),A0; BCS e96f0; BEQ e9704 (else TRAP e9702).
    case 0xe96f8:
        if(!am_pop(c,4,value))return false;r.a[1]=value;if(!am_read(c,r.a[1],4,value))return false;
        so_bound(r,value,0xe96f0,0xe9704,0xe9702);return true;
    // MOVE.W A1,D0; SUB.W A7,D0; LSR.W #2,D0; MOVE.L A1,-(A7); JSR 49a84.L (candidate count from the WORD difference).
    case 0xe9704:
        am_word(r.d[0],r.a[1]);am_word(r.d[0],(r.d[0]&65535U)-(r.a[7]&65535U));am_word(r.d[0],(r.d[0]&65535U)>>2);
        if(!am_push(c,4,r.a[1]))return false;return am_call(c,0x49a84,0xe9712);
    // MOVEA.L (A7)+,A1; LSL.W #2,D0; MOVEA.L (A7,D0.W),A0; MOVEA.L A1,A7; BSR e951c.
    case 0xe9712:
        if(!am_pop(c,4,value))return false;r.a[1]=value;am_word(r.d[0],(r.d[0]&65535U)<<2);
        if(!am_read(c,am_index(r.a[7],r.d[0]),4,value))return false;r.a[0]=value;r.a[7]=r.a[1];return am_call(c,0xe951c,0xe9720);
    case 0xe9720:if(!am_pop(c,4,value))return false;r.a[0]=value;r.pc=0xe9722;return true; // MOVEA.L (A7)+,A0.
    // e9724 (opcode 0e): MOVE.W 2(A0),D0; MOVE.W 4(A0),D1; MOVEQ #0,D2; MOVEQ #0,D3; MOVE.B 6(A0),D2; MOVE.B 7(A0),D3;
    // JSR 1a92c.L.
    case 0xe9724:
        if(!so_get(c,r.a[0],2,2,value))return false;am_word(r.d[0],value);
        if(!so_get(c,r.a[0],4,2,value))return false;am_word(r.d[1],value);r.d[2]=0;r.d[3]=0;
        if(!so_get(c,r.a[0],6,1,value))return false;am_byte(r.d[2],value);
        if(!so_get(c,r.a[0],7,1,value))return false;am_byte(r.d[3],value);
        return am_call(c,0x1a92c,0xe973e);
    // e9742 (opcode 0f): MOVE.W 2(A0),5e46(A5); MOVE.W 4(A0),5e48(A5); MOVE.L A0,-(A7); BSR e9298.
    case 0xe9742:
        if(!so_get(c,r.a[0],2,2,value) || !so_write(c,0x5e46,2,value&65535U))return false;
        if(!so_get(c,r.a[0],4,2,value) || !so_write(c,0x5e48,2,value&65535U))return false;
        if(!am_push(c,4,r.a[0]))return false;return am_call(c,0xe9298,0xe9754);
    case 0xe9754:if(!am_pop(c,4,value))return false;r.a[0]=value;r.pc=0xe9768;return true; // MOVEA.L (A7)+,A0; BRA e9768.
    // e975a (opcode 0d): ADDQ.B #1,80(A6); BCC e9768.
    case 0xe975a:return so_saturate(c,0xe9768,0xe9762);
    case 0xe9762:if(!so_put(c,r.a[6],0x80,1,0xff))return false;r.pc=0xe9768;return true; // MOVE.B #ff,80(A6).

    // e9774 (skip): MOVEQ #0,D0; MOVE.B (A0),D0; CMPI.B #10,D0; BCS e9782 (else TRAP e9780).
    case 0xe9774:if(!so_opcode(c,r.d[0],value))return false;r.pc=value<0x10U?0xe9782:0xe9780;return true;
    case 0xe9782:so_subtract(r,r.d[0],8,0xe978a,0xe9788);return true; // SUBQ.B #8,D0; BCC e978a (else TRAP e9788).
    // LSL.W #2,D0; JMP e9790(PC,D0.W) (computed PC; bounded by e9778/e9782 on the natural path).
    case 0xe978a:am_word(r.d[0],(r.d[0]&65535U)<<2);r.pc=am_index(SO_SKIP,r.d[0]);return true;
    // e9790 skip table: eight BRA.W slots (opcodes 08..0f).
    case 0xe9790:case 0xe97a4:case 0xe97a8:case 0xe97ac:r.pc=0xe97b0;return true;
    case 0xe9794:r.pc=0xe97b2;return true;
    case 0xe9798:r.pc=0xe97c4;return true;
    case 0xe979c:r.pc=0xe97b8;return true;
    case 0xe97a0:r.pc=0xe97be;return true;
    // ADDA.W 2(A0),A0; RTS (opcodes 09, 0b, 0c: skip the section).
    case 0xe97b2:case 0xe97b8:case 0xe97be:if(!so_get(c,r.a[0],2,2,value))return false;r.a[0]=am_index(r.a[0],value);return am_return(c);
    case 0xe97c4:return am_call(c,0xe9768,0xe97c6); // BSR e9768 (opcode 0a: skip the condition, then the next opcode).
    default:return am_error(c,"unsupported animation stage event ops PC");
    }
}
}
