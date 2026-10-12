#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONG (live bus, current PVC bank): MOVE.L 2000d4.L,22(A6) / MOVEA.L 2000d4.L,A1 (animation record of the 7839a family).
const std::uint32_t ON16_BANK_RECORD=0x2000d4;
bool on16_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on16_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Two's complement values of 68000 operands, compared as signed numbers (no signed overflow in C++).
int on16_signed_byte(std::uint32_t value) {
    value&=255U;return (value&0x80U)?static_cast<int>(value)-256:static_cast<int>(value);
}
int on16_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<int>(value)-65536:static_cast<int>(value);
}
// ASR.L #1 with the sign bit copied in.
std::uint32_t on16_asr1(std::uint32_t value) {
    return (value>>1)|(value&0x80000000U);
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on16_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n16 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// EORI.B #1,CCR; RTS: the callee's C inverted.
bool on16_flip(AnimationMachineContext& c) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n16 caller requires known carry");
    c.s.carry=c.s.carry==AnimationCarryClear?AnimationCarrySet:AnimationCarryClear;return am_return(c);
}
// ORI.B #1,CCR; RTS / ANDI.B #fe,CCR; RTS.
bool on16_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// MOVE.L #target,(A6) then continue at next_pc.
bool on16_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// BTST.B #bit,displacement(A6): true when the bit is set.
bool on16_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on16_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B / BCHG.B #bit,displacement(A6) (0 set, 1 clear, 2 change).
bool on16_bitop(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,unsigned int op) {
    std::uint32_t value=0;if(!on16_get(c,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;value=op==0?(value|mask):op==1?(value&~mask):(value^mask);return on16_put(c,displacement,1,value&255U);
}
// LEA 26(A6),A0; MOVE.W #b,20(A6); MOVE.L 2000d4.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L offset(A1),A1;
// JSR 49f8c.L.
bool on16_animation(AnimationMachineContext& c,std::uint32_t offset,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[6],0x26);
    if(!on16_put(c,0x20,2,0xb) || !am_read(c,ON16_BANK_RECORD,4,value) || !on16_put(c,0x22,4,value))return false;am_word(r.d[0],0x100);
    if(!on16_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],offset),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L 76(A6),A0; JSR target.
bool on16_target_call(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!on16_get(c,0x76,4,value))return false;c.s.a[0]=value;return am_call(c,target,return_pc);
}
}
// Objects F4 N16 (N16a, 163 block starts): the stage event callback 7839a (79114, the state dispatch 783c0 with the N16b boundaries
// 783ea / 785f2 and the boundary 787d2), the initialisation 77556 with the installed state 77596, the installed 77d38 / 77d70, the shared
// tail 78c22 (installed 78de6, the destruction path 78c76 to the boundary cc778) and the helpers 79054 790be 790d4 79114 791c0 791ea
// 791fa 79256 79292 792b8 79566 (second entry 7957a) 7960a 7967e 796cc. Boundaries without an executor: 493bc (N15) 494c0 4954e 79400
// 7942e 79454 79478 7949c 794e2 79722 787d2 cc778 783ea 785f2. Known C: Set 79212 792fe 795ac 78c96, Clear 7921c 792b2 79304 795b2
// 79624, inverted 792ac 7961e (EORI CCR consumers); the 23 BCC/BCS consumers read the C of 493bc 4945e 1ab02 28ae, the N16 helpers or
// the boundary helpers. N16 writes no port and changes no bank.
bool animation_objects_n16_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool flag=false;
    switch(r.pc) {
    // ---- 77556 (initialisation): CLR.L 36(A6); CLR.L 3a(A6); JSR 796cc(PC).
    case 0x77556:if(!on16_put(c,0x36,4,0) || !on16_put(c,0x3a,4,0))return false;return am_call(c,0x796cc,0x77562);
    // BCHG.B #0,9b(A6); animation record + c0 (49f8c).
    case 0x77562:if(!on16_bitop(c,0x9b,0,2))return false;return on16_animation(c,0xc0,0x77590);
    case 0x77590:return on16_install(c,0x77596,0x77596);                   // MOVE.L #77596,(A6).
    // ---- 77596 (installed): JSR 791ea(PC); JSR 49fc6.L; BTST.B #4,9b(A6); BEQ.W 77660.
    case 0x77596:return am_call(c,0x791ea,0x7759a);
    case 0x7759a:return am_call(c,0x49fc6,0x775a0);
    case 0x775a0:if(!on16_bit(c,0x9b,4,flag))return false;r.pc=flag?0x775aa:0x77660;return true;
    case 0x775aa:if(!on16_get(c,0x99,1,value))return false;r.pc=(value&255U)!=0U?0x7764a:0x775b2;return true; // TST.B 99(A6); BNE.W.
    case 0x775b2:return on16_target_call(c,0x493bc,0x775bc);              // MOVEA.L 76(A6),A0; JSR 493bc.L.
    case 0x775bc:return on16_carry(c,0x7763c,0x775c0);                    // BCC.W 7763c (C returned by 493bc).
    case 0x775c0:return am_call(c,0x4d7a6,0x775c6);
    case 0x775c6:r.pc=(r.d[0]&255U)==4U?0x775f2:0x775ce;return true;       // CMPI.B #4,D0; BEQ.W 775f2.
    case 0x775ce:return am_call(c,0x79256,0x775d2);
    case 0x775d2:r.pc=(r.d[0]&65535U)!=1U?0x775e4:0x775da;return true;     // CMPI.W #1,D0; BNE.W 775e4.
    case 0x775da:return on16_install(c,0x7777a,0x775f2);                  // MOVE.L #7777a,(A6); BRA.W 775f2.
    case 0x775e4:r.pc=(r.d[0]&65535U)!=2U?0x775f2:0x775ec;return true;     // CMPI.W #2,D0; BNE.W 775f2.
    case 0x775ec:return on16_install(c,0x7783e,0x775f2);
    case 0x775f2:return am_call(c,0x79454,0x775f6);
    case 0x775f6:return on16_carry(c,0x77600,0x775fa);                    // BCC.W 77600 (C returned by 79454).
    case 0x775fa:return on16_install(c,0x776da,0x77600);
    case 0x77600:return am_call(c,0x7960a,0x77604);
    case 0x77604:return on16_carry(c,0x7760e,0x77608);                    // BCC.W 7760e (C returned by 7960a).
    case 0x77608:return on16_install(c,0x77a70,0x7760e);
    case 0x7760e:case 0x77660:return am_call(c,0x79566,r.pc+4U);           // JSR 79566(PC).
    case 0x77612:return on16_carry(c,0x7761c,0x77616);                    // BCC.W 7761c (C returned by 79566).
    case 0x77616:return on16_install(c,0x77c68,0x7761c);
    case 0x7761c:return am_call(c,0x7949c,0x77620);
    case 0x77620:return on16_carry(c,0x7762a,0x77624);                    // BCC.W 7762a (C returned by 7949c).
    case 0x77624:return on16_install(c,0x778fa,0x7762a);
    case 0x7762a:return am_call(c,0x794e2,0x7762e);
    case 0x7762e:return on16_carry(c,0x77638,0x77632);                    // BCC.W 77638 (C returned by 794e2).
    case 0x77632:return on16_install(c,0x77af4,0x77638);
    case 0x77638:r.pc=0x77646;return true;                                 // BRA.W 77646.
    case 0x7763c:return am_call(c,0x4950e,0x77642);
    case 0x77642:case 0x79692:                                             // MOVE.L A0,76(A6).
        if(!on16_put(c,0x76,4,r.a[0]))return false;r.pc=r.pc==0x77642?0x77646:0x79696;return true;
    case 0x77646:r.pc=0x7765c;return true;                                 // BRA.W 7765c.
    // SUBQ.B #1,99(A6); JSR 79566(PC).
    case 0x7764a:if(!on16_get(c,0x99,1,value) || !on16_put(c,0x99,1,(value-1U)&255U))return false;return am_call(c,0x79566,0x77652);
    case 0x77652:return on16_carry(c,0x7765c,0x77656);
    case 0x77656:return on16_install(c,0x77c68,0x7765c);
    case 0x7765c:r.pc=0x7766e;return true;                                 // BRA.W 7766e.
    case 0x77664:return on16_carry(c,0x7766e,0x77668);
    case 0x77668:return on16_install(c,0x77c68,0x7766e);
    case 0x7766e:return am_call(c,0x792b8,0x77672);
    case 0x77672:return on16_carry(c,0x7767c,0x77676);                    // BCC.W 7767c (C returned by 792b8).
    case 0x77676:return on16_install(c,0x77de8,0x7767c);
    case 0x7767c:return am_call(c,0x791fa,0x77680);
    case 0x77680:return on16_carry(c,0x7768a,0x77684);                    // BCC.W 7768a (C returned by 791fa).
    case 0x77684:return on16_install(c,0x77d38,0x7768a);
    case 0x7768a:case 0x77d8a:r.pc=0x78c22;return true;                    // BRA.W 78c22.
    // ---- 77d38 (installed): MOVE.L 36(A6),D0; ASR.L #1,D0; MOVE.L D0,36(A6); animation record + 20 (49f8c).
    case 0x77d38:
        if(!on16_get(c,0x36,4,value))return false;r.d[0]=on16_asr1(value);if(!on16_put(c,0x36,4,r.d[0]))return false;
        return on16_animation(c,0x20,0x77d6a);
    case 0x77d6a:return on16_install(c,0x77d70,0x77d70);
    case 0x77d70:return am_call(c,0x4be2c,0x77d76);
    case 0x77d76:return am_call(c,0x49fc6,0x77d7c);
    case 0x77d7c:return am_call(c,0x791fa,0x77d80);
    case 0x77d80:return on16_carry(c,0x77d84,0x77d8a);                    // BCS.W 77d8a (C returned by 791fa).
    case 0x77d84:return on16_install(c,0x77d8e,0x77d8a);                  // MOVE.L #77d8e,(A6) (installed value outside the unit).
    // ---- 7839a (stage event callback): JSR 79114(PC); MOVE.B #f0,94(A6); MOVE.B #8,93(A6); BRA.W 783c0.
    case 0x7839a:return am_call(c,0x79114,0x7839e);
    case 0x7839e:if(!on16_put(c,0x94,1,0xf0) || !on16_put(c,0x93,1,8))return false;r.pc=0x783c0;return true;
    case 0x783c0:return am_call(c,0x4c0ac,0x783c6);
    case 0x783c6:return am_call(c,0x79054,0x783ca);
    case 0x783ca:if(!on16_get(c,0x88,2,value))return false;r.pc=(value&65535U)!=0U?0x783ea:0x783d2;return true; // TST.W 88(A6); BNE.W.
    case 0x783d2:if(!on16_bit(c,0x9b,5,flag))return false;r.pc=flag?0x77556:0x783dc;return true; // BTST.B #5,9b(A6); BNE.W 77556.
    case 0x783dc:if(!on16_bit(c,0x9b,2,flag))return false;r.pc=flag?0x785f2:0x783e6;return true; // BTST.B #2,9b(A6); BNE.W 785f2.
    case 0x783e6:r.pc=0x787d2;return true;                                 // BRA.W 787d2.
    // ---- 78c22 (shared tail): JSR 7967e(PC); SUBQ.W #1,84(A6); BPL.W 78c34.
    case 0x78c22:return am_call(c,0x7967e,0x78c26);
    case 0x78c26:
        if(!on16_get(c,0x84,2,value))return false;value=(value-1U)&65535U;if(!on16_put(c,0x84,2,value))return false;
        r.pc=(value&0x8000U)==0U?0x78c34:0x78c2e;return true;
    case 0x78c2e:if(!on16_put(c,0x84,2,0))return false;r.pc=0x78c34;return true; // MOVE.W #0,84(A6).
    case 0x78c34:if(!on16_bit(c,0x61,0,flag))return false;r.pc=flag?0x78c3e:0x78c44;return true; // BTST.B #0,61(A6); BEQ.W 78c44.
    case 0x78c3e:if(!on16_put(c,0x99,1,0x1e))return false;r.pc=0x78c44;return true; // MOVE.B #1e,99(A6).
    case 0x78c44:return am_call(c,0x4b54e,0x78c4a);
    case 0x78c4a:if(!on16_bit(c,0x61,7,flag))return false;r.pc=flag?0x78c54:0x78c5c;return true; // BTST.B #7,61(A6); BEQ.W 78c5c.
    case 0x78c54:r.pc=0x78c76;return true;                                 // BRA.W 78c76.
    // CLR.B 5e(A6); LEA 798ca(PC),A0; JSR 1ab02.L.
    case 0x78c5c:if(!on16_put(c,0x5e,1,0))return false;r.a[0]=0x798ca;return am_call(c,0x1ab02,0x78c6a);
    case 0x78c6a:return on16_carry(c,0x78c74,0x78c6e);                    // BCC.W 78c74 (C returned by 1ab02).
    case 0x78c6e:return on16_install(c,0x78de6,0x78c74);
    case 0x78c74:case 0x790a4:case 0x791e8:case 0x791f8:case 0x795aa:case 0x79696:return am_return(c); // RTS.
    // MOVEA.L #78e0e,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0x78c76:r.a[0]=0x78e0e;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x78c86);
    case 0x78c86:return on16_carry(c,0x78c9a,0x78c8a);                    // BCC.W 78c9a (C returned by 28ae).
    case 0x78c8a:am_word(r.d[0],0);am_word(r.d[1],0x18);return am_call(c,0x4970a,0x78c96); // CLR.W D0; MOVE.W #18,D1; JSR 4970a.L.
    case 0x78c96:r.carry=AnimationCarrySet;r.pc=0x78c9a;return true;       // ORI.B #1,CCR (Set).
    // MOVE.B 5f(A6),5f(A0); MOVE.B #ff,17(A6); LEA cdef8.L,A0; MOVEA.L 2000d4.L,A1; MOVE.W #b,D1; MOVE.W #1,D2; JMP cc778.L.
    case 0x78c9a:
        if(!on16_get(c,0x5f,1,value) || !am_write(c,am_index(r.a[0],0x5f),1,value) || !on16_put(c,0x17,1,0xff))return false;
        r.a[0]=0xcdef8;if(!am_read(c,ON16_BANK_RECORD,4,value))return false;r.a[1]=value;am_word(r.d[1],0xb);am_word(r.d[2],1);
        r.pc=0xcc778;return true;
    case 0x78de6:r.pc=0x2a00;return true;                                  // JMP 2a00.L.
    // ---- 79054 (helper): CMPI.W #a0,42(A6); BGT.W 79064.
    case 0x79054:if(!on16_get(c,0x42,2,value))return false;r.pc=on16_signed_word(value)>0xa0?0x79064:0x7905e;return true;
    case 0x7905e:if(!on16_bitop(c,0x15,0,2))return false;r.pc=0x79064;return true; // BCHG.B #0,15(A6).
    case 0x79064:return am_call(c,0x496c2,0x7906a);
    // MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVE.W #34,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0x7906a:
        if(!on16_put(c,0x68,2,0x8820) || !on16_put(c,0x1e,2,0x8820))return false;am_word(r.d[0],0x34);am_word(r.d[1],1);am_byte(r.d[2],0);
        return am_call(c,0xc6a96,0x79088);
    // MOVE.W #1,54(A6); LEA cb3e4.L,A0; JSR 490ba.L.
    case 0x79088:if(!on16_put(c,0x54,2,1))return false;r.a[0]=0xcb3e4;return am_call(c,0x490ba,0x7909a);
    case 0x7909a:if(!on16_put(c,0x84,2,r.d[0]&65535U))return false;return am_call(c,0xea5f0,0x790a4); // MOVE.W D0,84(A6); JSR ea5f0.L.
    // ---- 790be: BSET.B #7,9b(A6); MOVE.W 78(A6),D0; MOVE.W 7a(A6),D1; MOVE.B D0,8d(A6); MOVE.B D1,8c(A6).
    case 0x790be:
        if(!on16_bitop(c,0x9b,7,0) || !on16_get(c,0x78,2,value))return false;am_word(r.d[0],value);
        if(!on16_get(c,0x7a,2,value))return false;am_word(r.d[1],value);
        if(!on16_put(c,0x8d,1,r.d[0]&255U) || !on16_put(c,0x8c,1,r.d[1]&255U))return false;r.pc=0x790d4;return true;
    // EOR.W D0,D0; MOVE.W D0,76/78/7a/7c/7e/80(A6); JSR 4945e.L.
    case 0x790d4:
        am_word(r.d[0],0);
        for(std::uint32_t displacement=0x76;displacement<=0x80;displacement+=2)if(!on16_put(c,displacement,2,0))return false;
        return am_call(c,0x4945e,0x790f4);
    case 0x790f4:if(!on16_put(c,0x76,4,r.a[0]))return false;return am_return(c); // MOVE.L A0,76(A6); RTS.
    case 0x790fa:r.pc=0x790d4;return true;                                 // BRA.B 790d4.
    case 0x79114:if(!on16_bit(c,0x9b,7,flag))return false;r.pc=flag?0x790fa:0x7911c;return true; // BTST.B #7,9b(A6); BNE.B 790fa.
    // BSET.B #5,9b(A6); BCLR.B #4,9b(A6); MOVE.W 76(A6),88(A6); BRA.B 790be.
    case 0x7911c:
        if(!on16_bitop(c,0x9b,5,0) || !on16_bitop(c,0x9b,4,1) || !on16_get(c,0x76,2,value) || !on16_put(c,0x88,2,value))return false;
        r.pc=0x790be;return true;
    // ---- 791c0: TST.W 3a(A6); BMI.W 791d0.
    case 0x791c0:if(!on16_get(c,0x3a,2,value))return false;r.pc=(value&0x8000U)?0x791d0:0x791c8;return true;
    case 0x791c8:if(!on16_put(c,0x3a,4,0xffff0000U))return false;r.pc=0x791d0;return true; // MOVE.L #ffff0000,3a(A6).
    case 0x791d0:return am_call(c,0x4be2c,0x791d6);
    case 0x791d6:if(!on16_bit(c,0x15,7,flag))return false;r.pc=flag?0x791e0:0x791e8;return true; // BTST.B #7,15(A6); BEQ.W 791e8.
    case 0x791e0:if(!on16_put(c,0x36,4,0) || !on16_put(c,0x3a,4,0))return false;r.pc=0x791e8;return true; // CLR.L 36/3a(A6).
    // ---- 791ea: JSR 4be06.L; BTST.B #7,15(A6); BEQ.B 791c0.
    case 0x791ea:return am_call(c,0x4be06,0x791f0);
    case 0x791f0:if(!on16_bit(c,0x15,7,flag))return false;r.pc=flag?0x791f8:0x791c0;return true;
    // ---- 791fa (C returned): BTST.B #7,15(A6); BNE.W 79218.
    case 0x791fa:if(!on16_bit(c,0x15,7,flag))return false;r.pc=flag?0x79218:0x79204;return true;
    // ADDQ.B #1,97(A6); CMPI.B #6,97(A6); BLT.W 7921c.
    case 0x79204:
        if(!on16_get(c,0x97,1,value) || !on16_put(c,0x97,1,(value+1U)&255U) || !on16_get(c,0x97,1,value))return false;
        r.pc=on16_signed_byte(value)<6?0x7921c:0x79212;return true;
    case 0x79212:case 0x792fe:case 0x795ac:return on16_return_carry(c,AnimationCarrySet);     // ORI.B #1,CCR; RTS.
    case 0x79218:if(!on16_put(c,0x97,1,0))return false;r.pc=0x7921c;return true;             // CLR.B 97(A6).
    case 0x7921c:case 0x792b2:case 0x79304:case 0x795b2:case 0x79624:return on16_return_carry(c,AnimationCarryClear); // ANDI.B #fe,CCR; RTS.
    // ---- 79256 (D0.W = 0/1/2): JSR 79400(PC); BCS.W 79282.
    case 0x79256:return am_call(c,0x79400,0x7925a);
    case 0x7925a:return on16_carry(c,0x7925e,0x79282);                    // BCS.W 79282 (C returned by 79400).
    case 0x7925e:if(!on16_get(c,0x94,1,value))return false;r.pc=(value&255U)==0xc0U?0x79286:0x79268;return true; // CMPI.B #c0,94(A6).
    case 0x79268:return am_call(c,0x79478,0x7926c);
    case 0x7926c:return on16_carry(c,0x79286,0x79270);                    // BCC.W 79286 (C returned by 79478).
    case 0x79270:return am_call(c,0x49a58,0x79276);
    case 0x79276:am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&65535U)==0U?0x79286:0x7927e;return true; // ANDI.W #1,D0; BEQ.W 79286.
    case 0x7927e:r.pc=0x7928c;return true;                                 // BRA.W 7928c.
    case 0x79282:am_word(r.d[0],0);return am_return(c);                    // CLR.W D0; RTS.
    case 0x79286:am_word(r.d[0],1);return am_return(c);                    // MOVE.W #1,D0; RTS.
    case 0x7928c:am_word(r.d[0],2);return am_return(c);                    // MOVE.W #2,D0; RTS.
    // ---- 79292 (C returned): MOVE.W 42(A6),D0; CMPI.W #18,D0; BLT.W 792b2.
    case 0x79292:if(!on16_get(c,0x42,2,value))return false;am_word(r.d[0],value);r.pc=on16_signed_word(value)<0x18?0x792b2:0x7929e;return true;
    case 0x7929e:r.pc=on16_signed_word(r.d[0])>0x128?0x792b2:0x792a6;return true; // CMPI.W #128,D0; BGT.W 792b2.
    case 0x792a6:case 0x7957a:return am_call(c,0x4945e,r.pc+6U);           // JSR 4945e.L.
    case 0x792ac:case 0x7961e:return on16_flip(c);                         // EORI.B #1,CCR; RTS (C returned by 4945e / 494c0).
    // ---- 792b8 (C returned): JSR 79292(PC); BCC.W 79304.
    case 0x792b8:return am_call(c,0x79292,0x792bc);
    case 0x792bc:return on16_carry(c,0x79304,0x792c0);
    // MOVEA.L 76(A6),A0; CMPI.B #5,95(A6); BGT.W 792e4.
    case 0x792c0:
        if(!on16_get(c,0x76,4,value))return false;r.a[0]=value;if(!on16_get(c,0x95,1,value))return false;
        r.pc=on16_signed_byte(value)>5?0x792e4:0x792ce;return true;
    case 0x792ce:if(!on16_get(c,0x84,2,value))return false;r.pc=on16_signed_word(value)>0?0x79304:0x792d8;return true; // CMPI.W #0,84(A6).
    case 0x792d8:if(!on16_put(c,0x84,2,0))return false;return am_call(c,0x79478,0x792e0); // CLR.W 84(A6); JSR 79478(PC).
    case 0x792e0:return on16_carry(c,0x79304,0x792e4);                    // BCC.W 79304 (C returned by 79478).
    case 0x792e4:if(!on16_bit(c,0x9b,4,flag))return false;r.pc=flag?0x792ee:0x792fe;return true; // BTST.B #4,9b(A6); BEQ.W 792fe.
    case 0x792ee:return am_call(c,0x79722,0x792f2);
    case 0x792f2:return on16_carry(c,0x792fe,0x792f6);                    // BCC.W 792fe (C returned by 79722).
    case 0x792f6:return am_call(c,0x7942e,0x792fa);
    case 0x792fa:return on16_carry(c,0x79304,0x792fe);                    // BCC.W 79304 (C returned by 7942e).
    // ---- 79566 (C returned): ADDQ.B #1,96(A6); CMPI.B #1e,96(A6); BLT.W 795b2.
    case 0x79566:
        if(!on16_get(c,0x96,1,value) || !on16_put(c,0x96,1,(value+1U)&255U) || !on16_get(c,0x96,1,value))return false;
        r.pc=on16_signed_byte(value)<0x1e?0x795b2:0x79574;return true;
    case 0x79574:if(!on16_put(c,0x96,1,0x1e))return false;r.pc=0x7957a;return true; // MOVE.B #1e,96(A6).
    case 0x79580:return on16_carry(c,0x79584,0x795b2);                    // BCS.W 795b2 (C returned by 4945e).
    case 0x79584:r.a[0]=0x798aa;return am_call(c,0x494c0,0x7958e);       // LEA 798aa(PC),A0; JSR 494c0.L.
    case 0x7958e:return on16_carry(c,0x795b2,0x79592);                    // BCC.W 795b2 (C returned by 494c0).
    case 0x79592:r.a[0]=0x798b2;return am_call(c,0x494c0,0x7959c);
    case 0x7959c:return on16_carry(c,0x795ac,0x795a0);                    // BCC.W 795ac (C returned by 494c0).
    case 0x795a0:return on16_target_call(c,0x4954e,0x795aa);              // MOVEA.L 76(A6),A0; JSR 4954e.L.
    // ---- 7960a (C returned): BTST.B #3,9b(A6); BEQ.W 79624.
    case 0x7960a:if(!on16_bit(c,0x9b,3,flag))return false;r.pc=flag?0x79614:0x79624;return true;
    case 0x79614:r.a[0]=0x798c2;return am_call(c,0x494c0,0x7961e);
    // ---- 7967e: MOVEA.L 76(A6),A0; JSR 493bc.L; BCS.W 79696; JSR 4950e.L; MOVE.L A0,76(A6); RTS.
    case 0x7967e:return on16_target_call(c,0x493bc,0x79688);
    case 0x79688:return on16_carry(c,0x7968c,0x79696);                    // BCS.W 79696 (C returned by 493bc).
    case 0x7968c:return am_call(c,0x4950e,0x79692);
    // ---- 796cc: BTST.B #0,15(A6); BEQ.W 796de; BCLR.B #0,9b(A6); RTS / BSET.B #0,9b(A6); RTS.
    case 0x796cc:if(!on16_bit(c,0x15,0,flag))return false;r.pc=flag?0x796d6:0x796de;return true;
    case 0x796d6:if(!on16_bitop(c,0x9b,0,1))return false;return am_return(c);
    case 0x796de:if(!on16_bitop(c,0x9b,0,0))return false;return am_return(c);
    default:return am_error(c,"unsupported animation objects n16 PC");
    }
}
}
