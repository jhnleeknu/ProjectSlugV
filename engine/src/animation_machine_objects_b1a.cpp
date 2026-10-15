#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONGs (live bus, current PVC bank): MOVE.L 2000d4.L,22(A6) (the 7839a family record), 2001a8.L / 2001ac.L (the U19 ground state records).
const std::uint32_t OB1A_BANK_RECORD=0x2000d4;
const std::uint32_t OB1A_BANK_1A8=0x2001a8;
const std::uint32_t OB1A_BANK_1AC=0x2001ac;
bool ob1a_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool ob1a_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Signed views of 68000 operands (two's complement, no implementation-defined conversion).
bool ob1a_less_word(std::uint32_t a,std::uint32_t b) {
    return ((a&65535U)^0x8000U)<((b&65535U)^0x8000U);
}
bool ob1a_less_byte(std::uint32_t a,std::uint32_t b) {
    return ((a&255U)^0x80U)<((b&255U)^0x80U);
}
// BTST.B #bit,d16(A6): true when the bit is set.
bool ob1a_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob1a_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// TST.B / TST.W d16(A6): true when the BYTE / WORD is zero.
bool ob1a_zero(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,bool& zero) {
    std::uint32_t value=0;if(!ob1a_get(c,displacement,size,value))return false;zero=value==0U;return true;
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool ob1a_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b1a caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ORI.B #1,CCR; RTS / ANDI.B #fe,CCR; RTS.
bool ob1a_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// MOVE.L #target,(A6) then continue at next_pc.
bool ob1a_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// N16b animation record: LEA 26(A6),A0; MOVE.W #b,20(A6); MOVE.L 2000d4.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1;
// MOVEA.L offset(A1),A1; JSR 49f8c.L.
bool ob1a_animation(AnimationMachineContext& c,std::uint32_t offset,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[6],0x26);
    if(!ob1a_put(c,0x20,2,0xb) || !am_read(c,OB1A_BANK_RECORD,4,value) || !ob1a_put(c,0x22,4,value))return false;am_word(r.d[0],0x100);
    if(!ob1a_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],offset),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// U19b animation record: LEA 26(A6),A0; MOVE.W #word,20(A6); MOVE.L bank,22(A6); MOVEA.L #table,A1; ADD.W D0,D0 twice; MOVE.L (A1,D0.W),D0;
// MOVEA.L bank,A1; ADD.W D0,D0 twice; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L (D0.W on entry is the node index 8e(A6) or the
// leading D0.W of the block; the upper word of D0 follows the loaded LONG).
bool ob1a_ground(AnimationMachineContext& c,std::uint32_t word,std::uint32_t bank,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[6],0x26);
    if(!ob1a_put(c,0x20,2,word) || !am_read(c,bank,4,value) || !ob1a_put(c,0x22,4,value))return false;
    r.a[1]=table;am_word(r.d[0],(r.d[0]*4U)&65535U);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.d[0]=value;
    if(!am_read(c,bank,4,value))return false;r.a[1]=value;am_word(r.d[0],(r.d[0]*4U)&65535U);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);
    return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W nonzero_pc (the fall-through is the 1b3 / 2001a8 variant).
bool ob1a_select(AnimationMachineContext& c,std::uint32_t nonzero_pc,std::uint32_t zero_pc) {
    std::uint32_t value=0;if(!ob1a_get(c,0x8e,2,value))return false;am_word(c.s.d[0],value);
    c.s.pc=(value&65535U)!=0U?nonzero_pc:zero_pc;return true;
}
// The two variants of one ground animation: index zero uses 2001a8 / 1b3, any other index 2001ac / 1bb.
bool ob1a_ground_a(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    return ob1a_ground(c,0x1b3,OB1A_BANK_1A8,table,return_pc);
}
bool ob1a_ground_b(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    return ob1a_ground(c,0x1bb,OB1A_BANK_1AC,table,return_pc);
}
// MOVE.B 9e(A6),D0; JSR 6f1c2.L (ground probe).
bool ob1a_probe(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!ob1a_get(c,0x9e,1,value))return false;am_byte(c.s.d[0],value);return am_call(c,0x6f1c2,return_pc);
}
// NEG.L / NEG.W.
std::uint32_t ob1a_neg_long(std::uint32_t value) {
    return (0U-value);
}
}
// Objects deferred B1a (215 block starts): the N16b part of the 7839a object (107: the state branches 783ea / 785f2 with their installed
// states 7840c 78462 78496 784bc 784fa 7855a 785b4 78628, the tail 78cc4 with its installed 78d0a / 78d3a and the helpers 7919a 79222 7962a),
// the U19b part (86: the ground states b7100 / b749c with their installed states b718c b71ae b723c b72f2 b7386 b73a0 b7444 b7474 b7528
// b754e b75dc b7618) and the 22 leaf helper blocks 7930a 796e6 7970e 79722 b7d2e b7d3c (none of them is routed by another unit). Boundaries
// without an executor: the state chains 78660 78716 78776, the tail jump cc8b4, the callees 4929e 4be06 4be2c 4be34 4bfa4 4b54e 49f8c 49fc6
// 496c2 4970a 1ab02 28ae 6f1c2 43e34 4945e, and the targets of other units 791ea 791fa 7967e 796cc 78c22 77556 b76bc b76a4 b68be b6a2a.
// Known C: Set 79240 79648 79740 78d2a (ORI CCR), Clear 79250 7931a 7964e 7973a (ANDI CCR). The BCC/BCS consumers 78408 78454 784ae 7854c
// 78652 (C returned by 791fa), 784a0 785dc b71a0 b726a b7392 b7538 b75ee (49fc6), 7853e (79222), 78636 (7962a), 78644 (7930a), 78cfe
// (1ab02), 78d1a (28ae), 79630 (4945e) and 79638 (79722) read the C of their callee and fail on an Unknown C. The U19 ground selectors
// (MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE) pick the 2001a8 / 1b3 variant for index 0 and the 2001ac / 1bb variant otherwise; the two table
// lookups use ADD.W D0,D0 twice and the sign extended (A1,D0.W) index of the 68000.
bool animation_objects_b1a_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool flag=false,zero=false;
    switch(r.pc) {
    // ---- N16b: 783ea: TST.B 8a(A6); BEQ.W 783fe.
    case 0x783ea:if(!ob1a_zero(c,0x8a,1,zero))return false;r.pc=zero?0x783fe:0x783f2;return true;
    // MOVE.B 8a(A6),D0; ANDI.W #ff,D0; MOVE.W D0,84(A6).
    case 0x783f2:
        if(!ob1a_get(c,0x8a,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]&255U);
        if(!ob1a_put(c,0x84,2,r.d[0]&65535U))return false;r.pc=0x783fe;return true;
    case 0x783fe:return am_call(c,0x4be06,0x78404);                      // JSR 4be06.L.
    case 0x78404:case 0x78450:case 0x784aa:case 0x78548:case 0x7864e:return am_call(c,0x791fa,r.pc+4U); // JSR 791fa(PC).
    case 0x78408:return ob1a_carry(c,0x784bc,0x7840c);                    // BCC.W 784bc (C returned by 791fa).
    // MOVE.L 36(A6),D0; ASR.L #1,D0; MOVE.L D0,36(A6); animation record + 20 (49f8c).
    case 0x7840c:
        if(!ob1a_get(c,0x36,4,value))return false;r.d[0]=(value>>1)|(value&0x80000000U);if(!ob1a_put(c,0x36,4,r.d[0]))return false;
        return ob1a_animation(c,0x20,0x7843e);
    case 0x7843e:return ob1a_install(c,0x78444,0x78444);                  // MOVE.L #78444,(A6).
    case 0x78444:return am_call(c,0x4be2c,0x7844a);                       // JSR 4be2c.L.
    case 0x7844a:case 0x7849a:case 0x784fe:case 0x7862c:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.L.
    case 0x78454:return ob1a_carry(c,0x78458,0x7845e);                    // BCS.W 7845e (C returned by 791fa).
    case 0x78458:return ob1a_install(c,0x78462,0x7845e);
    case 0x7845e:case 0x784b8:case 0x78556:case 0x785ee:r.pc=0x78c22;return true; // BRA.W 78c22.
    case 0x78462:return am_call(c,0x496c2,0x78468);                       // JSR 496c2.L.
    case 0x78468:return ob1a_animation(c,0x24,0x78490);
    case 0x78490:return ob1a_install(c,0x78496,0x78496);
    case 0x78496:return am_call(c,0x791ea,0x7849a);                       // JSR 791ea(PC).
    case 0x784a0:return ob1a_carry(c,0x784aa,0x784a4);                    // BCC.W 784aa (C returned by 49fc6).
    case 0x784a4:return ob1a_install(c,0x784bc,0x784aa);
    case 0x784ae:return ob1a_carry(c,0x784b8,0x784b2);                    // BCC.W 784b8 (C returned by 791fa).
    case 0x784b2:case 0x78550:case 0x78656:return ob1a_install(c,0x7840c,r.pc+6U); // MOVE.L #7840c,(A6).
    case 0x784bc:return am_call(c,0x796cc,0x784c0);                       // JSR 796cc(PC).
    // MOVE.L #40000,64(A6); JSR 796e6(PC).
    case 0x784c0:if(!ob1a_put(c,0x64,4,0x40000))return false;return am_call(c,0x796e6,0x784cc);
    case 0x784cc:return ob1a_animation(c,0xb8,0x784f4);
    case 0x784f4:return ob1a_install(c,0x784fa,0x784fa);
    case 0x784fa:return am_call(c,0x7919a,0x784fe);                       // JSR 7919a(PC).
    // MOVE.W 88(A6),D0; CLR.W D1; JSR 4929e.L.
    case 0x78504:
        if(!ob1a_get(c,0x88,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],0);return am_call(c,0x4929e,0x78510);
    case 0x78510:if(!ob1a_bit(c,0x15,0,flag))return false;r.pc=flag?0x7852c:0x7851a;return true; // BTST.B #0,15(A6); BNE.W 7852c.
    // CMP.W 42(A6),D0; BLT.W 78528 (D0.W < WORD, signed).
    case 0x7851a:if(!ob1a_get(c,0x42,2,value))return false;r.pc=ob1a_less_word(r.d[0],value)?0x78528:0x78522;return true;
    case 0x78522:case 0x78534:case 0x78542:return ob1a_install(c,0x7855a,r.pc==0x78522U?0x78528U:r.pc==0x78534U?0x7853aU:0x78548U);
    case 0x78528:r.pc=0x7853a;return true;                                 // BRA.W 7853a.
    // CMP.W 42(A6),D0; BGT.W 7853a (D0.W > WORD, signed).
    case 0x7852c:if(!ob1a_get(c,0x42,2,value))return false;r.pc=ob1a_less_word(value,r.d[0])?0x7853a:0x78534;return true;
    case 0x7853a:return am_call(c,0x79222,0x7853e);                       // JSR 79222(PC).
    case 0x7853e:return ob1a_carry(c,0x78548,0x78542);                    // BCC.W 78548 (C returned by 79222).
    case 0x7854c:return ob1a_carry(c,0x78556,0x78550);                    // BCC.W 78556 (C returned by 791fa).
    case 0x7855a:if(!ob1a_bit(c,0x9b,5,flag))return false;r.pc=flag?0x77556:0x78564;return true; // BTST.B #5,9b(A6); BNE.W 77556.
    case 0x78564:if(!ob1a_bit(c,0x9b,2,flag))return false;r.pc=flag?0x7856e:0x78776;return true; // BTST.B #2,9b(A6); BEQ.W 78776.
    // MOVE.L #ccccc,3a(A6); MOVE.L #fffae148,7e(A6); MOVE.L #fff9999a,36(A6); animation record + 10 (49f8c).
    case 0x7856e:
        if(!ob1a_put(c,0x3a,4,0xccccc) || !ob1a_put(c,0x7e,4,0xfffae148U) || !ob1a_put(c,0x36,4,0xfff9999aU))return false;
        return ob1a_animation(c,0x10,0x785ae);
    case 0x785ae:return ob1a_install(c,0x785b4,0x785b4);
    case 0x785b4:return am_call(c,0x4be34,0x785ba);                       // JSR 4be34.L.
    case 0x785ba:if(!ob1a_bit(c,0x15,7,flag))return false;r.pc=flag?0x785d0:0x785c4;return true; // BTST.B #7,15(A6); BNE.W 785d0.
    // MOVE.L 7e(A6),D0; ADD.L D0,3a(A6); BRA.W 785d6.
    case 0x785c4:
        if(!ob1a_get(c,0x7e,4,value))return false;r.d[0]=value;if(!ob1a_get(c,0x3a,4,value) || !ob1a_put(c,0x3a,4,value+r.d[0]))return false;
        r.pc=0x785d6;return true;
    case 0x785d0:return am_call(c,0x496c2,0x785d6);                       // JSR 496c2.L.
    case 0x785d6:return am_call(c,0x49fc6,0x785dc);                       // JSR 49fc6.L.
    case 0x785dc:return ob1a_carry(c,0x785ee,0x785e0);                    // BCC.W 785ee (C returned by 49fc6).
    case 0x785e0:if(!ob1a_get(c,0x36,2,value))return false;r.pc=(value&65535U)!=0U?0x785ee:0x785e8;return true; // TST.W 36(A6); BNE.W 785ee.
    case 0x785e8:return ob1a_install(c,0x785f2,0x785ee);
    // CLR.L 36(A6); CLR.L 3a(A6); animation record + 14 (49f8c).
    case 0x785f2:if(!ob1a_put(c,0x36,4,0) || !ob1a_put(c,0x3a,4,0))return false;return ob1a_animation(c,0x14,0x78622);
    case 0x78622:return ob1a_install(c,0x78628,0x78628);
    case 0x78628:return am_call(c,0x791ea,0x7862c);                       // JSR 791ea(PC).
    case 0x78632:return am_call(c,0x7962a,0x78636);                       // JSR 7962a(PC).
    case 0x78636:return ob1a_carry(c,0x78640,0x7863a);                    // BCC.W 78640 (C returned by 7962a).
    case 0x7863a:return ob1a_install(c,0x78716,0x78640);
    case 0x78640:return am_call(c,0x7930a,0x78644);                       // JSR 7930a(PC).
    case 0x78644:return ob1a_carry(c,0x7864e,0x78648);                    // BCC.W 7864e (C returned by 7930a).
    case 0x78648:return ob1a_install(c,0x78660,0x7864e);
    case 0x78652:return ob1a_carry(c,0x7865c,0x78656);                    // BCC.W 7865c (C returned by 791fa).
    case 0x7865c:r.pc=0x78cc4;return true;                                 // BRA.W 78cc4.
    // ---- 78cc4 (tail): JSR 7967e(PC); SUBQ.W #1,84(A6); BPL.W 78cd6.
    case 0x78cc4:return am_call(c,0x7967e,0x78cc8);
    case 0x78cc8:
        if(!ob1a_get(c,0x84,2,value))return false;value=(value-1U)&65535U;if(!ob1a_put(c,0x84,2,value))return false;
        r.pc=(value&0x8000U)==0U?0x78cd6:0x78cd0;return true;
    case 0x78cd0:if(!ob1a_put(c,0x84,2,0))return false;r.pc=0x78cd6;return true; // MOVE.W #0,84(A6).
    case 0x78cd6:return am_call(c,0x4b54e,0x78cdc);                       // JSR 4b54e.L.
    case 0x78cdc:if(!ob1a_bit(c,0x61,7,flag))return false;r.pc=flag?0x78ce6:0x78cf0;return true; // BTST.B #7,61(A6); BEQ.W 78cf0.
    case 0x78ce6:return ob1a_install(c,0x78d0a,0x78cf4);                  // MOVE.L #78d0a,(A6); BRA.B 78cf4.
    case 0x78cf0:if(!ob1a_put(c,0x5e,1,0))return false;r.pc=0x78cf4;return true; // CLR.B 5e(A6).
    case 0x78cf4:r.a[0]=0x798ca;return am_call(c,0x1ab02,0x78cfe);       // LEA 798ca(PC),A0; JSR 1ab02.L.
    case 0x78cfe:return ob1a_carry(c,0x78d08,0x78d02);                    // BCC.W 78d08 (C returned by 1ab02).
    case 0x78d02:return ob1a_install(c,0x78de6,0x78d08);
    case 0x78d08:case 0x791be:case 0x79318:case 0x79720:case 0xb7d3a:case 0xb7d48:return am_return(c); // RTS.
    // MOVEA.L #78e0e,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0x78d0a:r.a[0]=0x78e0e;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x78d1a);
    case 0x78d1a:return ob1a_carry(c,0x78d2e,0x78d1e);                    // BCC.W 78d2e (C returned by 28ae).
    case 0x78d1e:am_word(r.d[0],0);am_word(r.d[1],0x10);return am_call(c,0x4970a,0x78d2a); // CLR.W D0; MOVE.W #10,D1; JSR 4970a.L.
    case 0x78d2a:r.carry=AnimationCarrySet;r.pc=0x78d2e;return true;       // ORI.B #1,CCR (Set).
    // MOVE.B 5f(A6),5f(A0); MOVE.L #78d3a,(A6).
    case 0x78d2e:
        if(!ob1a_get(c,0x5f,1,value) || !am_write(c,am_index(r.a[0],0x5f),1,value))return false;return ob1a_install(c,0x78d3a,0x78d3a);
    // MOVE.B #ff,17(A6); LEA cdef8.L,A0; MOVEA.L 2000d4.L,A1; MOVE.W #b,D1; MOVE.W #1,D2; JMP cc8b4.L (boundary).
    case 0x78d3a:
        if(!ob1a_put(c,0x17,1,0xff))return false;r.a[0]=0xcdef8;if(!am_read(c,OB1A_BANK_RECORD,4,value))return false;r.a[1]=value;
        am_word(r.d[1],0xb);am_word(r.d[2],1);r.pc=0xcc8b4;return true;
    // ---- 7919a (helper): JSR 4be06.L; BTST.B #7,15(A6); BEQ.B 791c0.
    case 0x7919a:return am_call(c,0x4be06,0x791a0);
    case 0x791a0:if(!ob1a_bit(c,0x15,7,flag))return false;r.pc=flag?0x791aa:0x791c0;return true;
    case 0x791aa:return am_call(c,0x4bfa4,0x791b0);                       // JSR 4bfa4.L.
    case 0x791b0:if(!ob1a_get(c,0x36,4,value))return false;r.pc=value!=0U?0x791be:0x791b8;return true; // TST.L 36(A6); BNE.W 791be.
    case 0x791b8:{                                                         // BSET.B #0,61(A6).
        if(!ob1a_get(c,0x61,1,value) || !ob1a_put(c,0x61,1,(value|1U)&255U))return false;r.pc=0x791be;return true;}
    // ---- 79222 (C returned): BTST.B #0,61(A6); BEQ.W 7924c.
    case 0x79222:if(!ob1a_bit(c,0x61,0,flag))return false;r.pc=flag?0x7922c:0x7924c;return true;
    // MOVE.B #1e,99(A6); ADDQ.B #1,98(A6); CMPI.B #f,98(A6); BLT.W 79250.
    case 0x7922c:
        if(!ob1a_put(c,0x99,1,0x1e) || !ob1a_get(c,0x98,1,value))return false;value=(value+1U)&255U;if(!ob1a_put(c,0x98,1,value))return false;
        r.pc=ob1a_less_byte(value,0xfU)?0x79250:0x79240;return true;
    case 0x79240:if(!ob1a_put(c,0x98,1,0xf))return false;return ob1a_return_carry(c,AnimationCarrySet); // MOVE.B #f,98(A6); ORI.B #1,CCR; RTS.
    case 0x7924c:if(!ob1a_put(c,0x98,1,0))return false;r.pc=0x79250;return true; // CLR.B 98(A6).
    case 0x79250:case 0x7931a:case 0x7973a:case 0x7964e:return ob1a_return_carry(c,AnimationCarryClear); // ANDI.B #fe,CCR; RTS.
    // ---- 7962a (C returned): JSR 4945e.L; BCS.W 7964e; JSR 79722(PC); BCS.W 7964e; JSR 7970e(PC); CMPI.W #30,D0; BGT.W 7964e.
    case 0x7962a:return am_call(c,0x4945e,0x79630);
    case 0x79630:return ob1a_carry(c,0x79634,0x7964e);                    // BCS.W 7964e (C returned by 4945e).
    case 0x79634:return am_call(c,0x79722,0x79638);                       // JSR 79722(PC).
    case 0x79638:return ob1a_carry(c,0x7963c,0x7964e);                    // BCS.W 7964e (C returned by 79722).
    case 0x7963c:return am_call(c,0x7970e,0x79640);                       // JSR 7970e(PC).
    case 0x79640:r.pc=ob1a_less_word(0x30U,r.d[0])?0x7964e:0x79648;return true; // CMPI.W #30,D0; BGT.W 7964e.
    case 0x79648:case 0x79740:return ob1a_return_carry(c,AnimationCarrySet); // ORI.B #1,CCR; RTS.
    // ---- leaf helper 7930a: CMPI.W #0,84(A6); BGT.W 7931a; JSR 79292(PC); RTS (the C of 79292).
    case 0x7930a:if(!ob1a_get(c,0x84,2,value))return false;r.pc=(value&0x8000U)==0U && (value&65535U)!=0U?0x7931a:0x79314;return true;
    case 0x79314:return am_call(c,0x79292,0x79318);
    // ---- leaf helper 796e6: MOVE.L 64(A6),D0; BTST.B #0,9b(A6); BNE.W 79700; (TST.L D0; BPL.W 796fc; NEG.L D0) / (TST.L D0; BMI.W 79708; NEG.L D0).
    case 0x796e6:
        if(!ob1a_get(c,0x64,4,value))return false;r.d[0]=value;if(!ob1a_bit(c,0x9b,0,flag))return false;r.pc=flag?0x79700:0x796f4;return true;
    case 0x796f4:r.pc=(r.d[0]&0x80000000U)==0U?0x796fc:0x796fa;return true;
    case 0x796fa:case 0x79706:r.d[0]=ob1a_neg_long(r.d[0]);r.pc=r.pc==0x796faU?0x796fcU:0x79708U;return true; // NEG.L D0.
    case 0x796fc:r.pc=0x79708;return true;                                 // BRA.W 79708.
    case 0x79700:r.pc=(r.d[0]&0x80000000U)!=0U?0x79708:0x79706;return true;
    case 0x79708:if(!ob1a_put(c,0x64,4,r.d[0]))return false;return am_return(c); // MOVE.L D0,64(A6); RTS.
    // ---- leaf helper 7970e: MOVE.W 42(A6),D0; SUB.W 42(A0),D0; CMPI.W #0,D0; BGE.W 79720; NEG.W D0; RTS.
    case 0x7970e:
        if(!ob1a_get(c,0x42,2,value) || !am_read(c,am_index(r.a[0],0x42),2,other))return false;am_word(r.d[0],value-other);
        r.pc=(r.d[0]&0x8000U)==0U?0x79720:0x7971e;return true;
    case 0x7971e:am_word(r.d[0],(0x10000U-(r.d[0]&65535U))&65535U);r.pc=0x79720;return true; // NEG.W D0.
    // ---- leaf helper 79722 (C returned): MOVE.W 46(A0),D0; SUB.W 46(A6),D0; CMPI.W #30,D0; BGT.W 79740; CMPI.W #fff0,D0; BLT.W 79740.
    case 0x79722:
        if(!am_read(c,am_index(r.a[0],0x46),2,value) || !ob1a_get(c,0x46,2,other))return false;am_word(r.d[0],value-other);
        r.pc=ob1a_less_word(0x30U,r.d[0])?0x79740:0x79732;return true;
    case 0x79732:r.pc=ob1a_less_word(r.d[0],0xfff0U)?0x79740:0x7973a;return true;
    // ---- leaf helper b7d2e / b7d3c: ADDI.W / SUBI.W #24,32(A6); JSR 43e34.L; RTS.
    case 0xb7d2e:case 0xb7d3c:
        if(!ob1a_get(c,0x32,2,value))return false;
        if(!ob1a_put(c,0x32,2,r.pc==0xb7d2eU?(value+0x24U)&65535U:(value-0x24U)&65535U))return false;
        return am_call(c,0x43e34,r.pc+0xcU);
    // ---- U19b: b7100: JSR 496c2.L; MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b714e.
    case 0xb7100:case 0xb72f2:case 0xb749c:case 0xb7618:return am_call(c,0x496c2,r.pc+6U);
    case 0xb7106:return ob1a_select(c,0xb714e,0xb7112);
    case 0xb7112:return ob1a_ground_a(c,0xb7f84,0xb714a);
    case 0xb714a:r.pc=0xb7186;return true;                                 // BRA.W b7186.
    case 0xb714e:return ob1a_ground_b(c,0xb7f84,0xb7186);
    case 0xb7186:return ob1a_install(c,0xb718c,0xb718c);
    // CLR.W 3a(A6); MOVE.B 9e(A6),D0; JSR 6f1c2.L.
    case 0xb718c:if(!ob1a_put(c,0x3a,2,0))return false;return ob1a_probe(c,0xb719a);
    case 0xb719a:case 0xb7264:case 0xb738c:case 0xb7482:case 0xb7532:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.L.
    case 0xb71a0:return ob1a_carry(c,0xb71aa,0xb71a4);                    // BCC.W b71aa (C returned by 49fc6).
    case 0xb71a4:return ob1a_install(c,0xb71ae,0xb71aa);
    case 0xb71aa:case 0xb72ee:case 0xb739c:case 0xb7498:case 0xb754a:case 0xb7614:r.pc=0xb76bc;return true; // BRA.W b76bc.
    case 0xb71ae:return ob1a_select(c,0xb71f6,0xb71ba);
    case 0xb726e:return ob1a_select(c,0xb72b6,0xb727a);
    case 0xb754e:return ob1a_select(c,0xb7596,0xb755a);
    case 0xb71ba:return ob1a_ground_a(c,0xb7f8c,0xb71f2);
    case 0xb71f2:r.pc=0xb722e;return true;                                 // BRA.W b722e.
    case 0xb71f6:return ob1a_ground_b(c,0xb7f8c,0xb722e);
    // MOVE.L #15500,3a(A6); MOVE.L #b723c,(A6).
    case 0xb722e:if(!ob1a_put(c,0x3a,4,0x15500))return false;return ob1a_install(c,0xb723c,0xb723c);
    case 0xb723c:case 0xb7528:case 0xb75dc:return ob1a_probe(c,r.pc==0xb723cU?0xb7246U:r.pc==0xb7528U?0xb7532U:0xb75e6U);
    case 0xb7246:r.pc=(r.d[0]&0x8000U)==0U?0xb7256:0xb724c;return true;   // TST.W D0; BPL.W b7256.
    case 0xb724c:return ob1a_install(c,0xb68be,0xb7264);                  // MOVE.L #b68be,(A6); BRA.W b7264.
    // SUBI.W #24,D0; BCC.W b7264 (the borrow is set when D0.W < 24).
    case 0xb7256:
        value=r.d[0]&65535U;am_word(r.d[0],value-0x24U);r.pc=value>=0x24U?0xb7264:0xb725e;return true;
    case 0xb725e:return ob1a_install(c,0xb72f2,0xb7264);
    case 0xb726a:return ob1a_carry(c,0xb72ee,0xb726e);                    // BCC.W b72ee (C returned by 49fc6).
    case 0xb727a:return ob1a_ground_a(c,0xb7f8c,0xb72b2);
    case 0xb72b2:r.pc=0xb72ee;return true;                                 // BRA.W b72ee.
    case 0xb72b6:return ob1a_ground_b(c,0xb7f8c,0xb72ee);
    case 0xb72f8:return ob1a_select(c,0xb7340,0xb7304);
    case 0xb7304:return ob1a_ground_a(c,0xb7f94,0xb733c);
    case 0xb733c:r.pc=0xb7378;return true;                                 // BRA.W b7378.
    case 0xb7340:return ob1a_ground_b(c,0xb7f94,0xb7378);
    case 0xb7378:r.a[0]=am_index(r.a[6],0x26);return am_call(c,0xb7d2e,0xb7380); // LEA 26(A6),A0; JSR b7d2e(PC).
    case 0xb7380:return ob1a_install(c,0xb7386,0xb7386);
    case 0xb7386:return am_call(c,0x4be34,0xb738c);                       // JSR 4be34.L.
    case 0xb7392:return ob1a_carry(c,0xb739c,0xb7396);                    // BCC.W b739c (C returned by 49fc6).
    case 0xb7396:return ob1a_install(c,0xb73a0,0xb739c);
    // MOVE.B #c,9c(A6); MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b73ee.
    case 0xb73a0:if(!ob1a_put(c,0x9c,1,0xc))return false;return ob1a_select(c,0xb73ee,0xb73b2);
    case 0xb73b2:return ob1a_ground_a(c,0xb7f9c,0xb73ea);
    case 0xb73ea:r.pc=0xb7426;return true;                                 // BRA.W b7426.
    case 0xb73ee:return ob1a_ground_b(c,0xb7f9c,0xb7426);
    // MOVE.L #4cccc,3a(A6); MOVE.L #ffff0a3e,88(A6); MOVE.L #fffe6667,36(A6); MOVE.L #b7444,(A6).
    case 0xb7426:
        if(!ob1a_put(c,0x3a,4,0x4cccc) || !ob1a_put(c,0x88,4,0xffff0a3eU) || !ob1a_put(c,0x36,4,0xfffe6667U))return false;
        return ob1a_install(c,0xb7444,0xb7444);
    // MOVE.L 36(A6),D0; BEQ.W b745c.
    case 0xb7444:if(!ob1a_get(c,0x36,4,value))return false;r.d[0]=value;r.pc=value==0U?0xb745c:0xb744c;return true;
    // ASR.L #4,D0; SEQ.B D1; EXT.W D1; EXT.L D1; EOR.L D1,D0; SUB.L D1,D0; SUB.L D0,36(A6).
    case 0xb744c:
        r.d[0]=(r.d[0]>>4)|((r.d[0]&0x80000000U)!=0U?0xf0000000U:0U);r.d[1]=r.d[0]==0U?0xffffffffU:0U;
        r.d[0]=(r.d[0]^r.d[1])-r.d[1];if(!ob1a_get(c,0x36,4,value) || !ob1a_put(c,0x36,4,value-r.d[0]))return false;
        r.pc=0xb745c;return true;
    // SUBQ.B #1,9c(A6); CMPI.B #0,9c(A6); BGT.W b7474.
    case 0xb745c:
        if(!ob1a_get(c,0x9c,1,value))return false;value=(value-1U)&255U;if(!ob1a_put(c,0x9c,1,value))return false;
        r.pc=(value&0x80U)==0U && value!=0U?0xb7474:0xb746a;return true;
    case 0xb746a:if(!ob1a_put(c,0x36,4,0))return false;return ob1a_install(c,0xb7474,0xb7474); // CLR.L 36(A6); MOVE.L #b7474,(A6).
    // MOVE.L 88(A6),D0; ADD.L D0,3a(A6); JSR 4be34.L.
    case 0xb7474:
        if(!ob1a_get(c,0x88,4,value))return false;r.d[0]=value;if(!ob1a_get(c,0x3a,4,value) || !ob1a_put(c,0x3a,4,value+r.d[0]))return false;
        return am_call(c,0x4be34,0xb7482);
    case 0xb7488:if(!ob1a_bit(c,0x15,7,flag))return false;r.pc=flag?0xb7492:0xb7498;return true; // BTST.B #7,15(A6); BEQ.W b7498.
    case 0xb7492:return ob1a_install(c,0xb68be,0xb7498);
    case 0xb74a2:return ob1a_select(c,0xb74ea,0xb74ae);
    case 0xb74ae:return ob1a_ground_a(c,0xb7fa4,0xb74e6);
    case 0xb74e6:r.pc=0xb7522;return true;                                 // BRA.W b7522.
    case 0xb74ea:return ob1a_ground_b(c,0xb7fa4,0xb7522);
    case 0xb7522:return ob1a_install(c,0xb7528,0xb7528);
    case 0xb7538:return ob1a_carry(c,0xb754a,0xb753c);                    // BCC.W b754a (C returned by 49fc6).
    case 0xb753c:r.a[0]=am_index(r.a[6],0x26);return am_call(c,0xb7d3c,0xb7544); // LEA 26(A6),A0; JSR b7d3c(PC).
    case 0xb7544:return ob1a_install(c,0xb754e,0xb754a);
    case 0xb755a:return ob1a_ground_a(c,0xb7fac,0xb7592);
    case 0xb7592:r.pc=0xb75ce;return true;                                 // BRA.W b75ce.
    case 0xb7596:return ob1a_ground_b(c,0xb7fac,0xb75ce);
    // MOVE.L #fffeab00,3a(A6); MOVE.L #b75dc,(A6).
    case 0xb75ce:if(!ob1a_put(c,0x3a,4,0xfffeab00U))return false;return ob1a_install(c,0xb75dc,0xb75dc);
    case 0xb75e6:if(!am_push(c,2,r.d[0]&65535U))return false;return am_call(c,0x49fc6,0xb75ee); // MOVE.W D0,-(A7); JSR 49fc6.L.
    case 0xb75ee:return ob1a_carry(c,0xb75f8,0xb75f2);                    // BCC.W b75f8 (C returned by 49fc6).
    case 0xb75f2:return ob1a_install(c,0xb754e,0xb75f8);
    // MOVE.W (A7)+,D0; BPL.W b7604.
    case 0xb75f8:if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.pc=(value&0x8000U)==0U?0xb7604:0xb75fe;return true;
    case 0xb75fe:return ob1a_install(c,0xb6a2a,0xb7604);
    case 0xb7604:if(!ob1a_bit(c,0x15,7,flag))return false;r.pc=flag?0xb7614:0xb760e;return true; // BTST.B #7,15(A6); BNE.W b7614.
    case 0xb760e:return ob1a_install(c,0xb7618,0xb7614);
    case 0xb761e:return ob1a_select(c,0xb7666,0xb762a);
    case 0xb762a:return ob1a_ground_a(c,0xb7fb4,0xb7662);
    case 0xb7662:r.pc=0xb769e;return true;                                 // BRA.W b769e.
    case 0xb7666:return ob1a_ground_b(c,0xb7fb4,0xb769e);
    case 0xb769e:return ob1a_install(c,0xb76a4,0xb76a4);
    default:return am_error(c,"unsupported animation objects b1a PC");
    }
}
}
