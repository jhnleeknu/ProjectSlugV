#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONGs (live bus, current PVC bank): animation records of the 8664c family (id e3), the b630e generator and its b780c
// children (id 1b3 / 1bb).
const std::uint32_t ON18_BANK_E3=0x200140;
const std::uint32_t ON18_BANK_1B3=0x2001a8;
const std::uint32_t ON18_BANK_1BB=0x2001ac;
// -7348(A5) / -7258(A5): the two player nodes (100cb8 / 100da8 with A5 = 108000).
const std::uint32_t ON18_PLAYER1=0x8cb8;
const std::uint32_t ON18_PLAYER2=0x8da8;
bool on18_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on18_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Two's complement WORD as a signed number (no signed overflow in C++).
int on18_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<int>(value)-65536:static_cast<int>(value);
}
// ASR.L #5 with the sign bit copied in.
std::uint32_t on18_asr5(std::uint32_t value) {
    return (value&0x80000000U)?((value>>5)|0xf8000000U):(value>>5);
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on18_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n18 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,(A6) then continue at next_pc.
bool on18_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// BTST.B #bit,displacement(A6): true when the bit is set.
bool on18_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on18_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,displacement(A6) (set: true sets, false clears).
bool on18_bitop(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!on18_get(c,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;value=set?(value|mask):(value&~mask);return on18_put(c,displacement,1,value&255U);
}
// MOVE.L #value,displacement(A6) / MOVE.W #value,displacement(A6).
bool on18_set_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value) {
    return on18_put(c,displacement,2,value&65535U);
}
// LEA 26(A6),A0; MOVE.W #id,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L offset(A1),A1;
// JSR 49f8c.L.
bool on18_animation(AnimationMachineContext& c,std::uint32_t bank,std::uint32_t id,std::uint32_t offset,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[6],0x26);
    if(!on18_set_word(c,0x20,id) || !am_read(c,bank,4,value) || !on18_put(c,0x22,4,value))return false;am_word(r.d[0],0x100);
    if(!on18_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],offset),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// b6566 / b65a2: LEA 26(A6),A0; MOVE.W #id,20(A6); MOVE.L bank.L,22(A6); MOVEA.L #b7f2c,A1; ADD.W D0,D0; ADD.W D0,D0;
// MOVE.L (A1,D0.W),D0; MOVEA.L bank.L,A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
bool on18_indexed_animation(AnimationMachineContext& c,std::uint32_t bank,std::uint32_t id,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[6],0x26);
    if(!on18_set_word(c,0x20,id) || !am_read(c,bank,4,value) || !on18_put(c,0x22,4,value))return false;
    r.a[1]=0xb7f2c;am_word(r.d[0],(r.d[0]*4U)&65535U);if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.d[0]=value;
    if(!am_read(c,bank,4,value))return false;r.a[1]=value;am_word(r.d[0],(r.d[0]*4U)&65535U);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);
    return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 42(A0),D0; SUB.W 42(A6),D0 (D0.W, BPL/NEG follow in the next blocks): returns true when the difference is >= 0 (N clear).
bool on18_distance(AnimationMachineContext& c,bool& positive) {
    AnimationMachineState& r=c.s;std::uint32_t a=0,b=0;
    if(!am_read(c,am_index(r.a[0],0x42),2,a) || !on18_get(c,0x42,2,b))return false;
    am_word(r.d[0],(a-b)&65535U);positive=(r.d[0]&0x8000U)==0U;return true;
}
// NEG.W Dn.
void on18_neg_word(std::uint32_t& reg) {
    am_word(reg,(0U-reg)&65535U);
}
}
// Objects F4 N18 (196 block starts): the 8664c family (initial entries 86642 8664c 8665a 86664 with the shared initialisation 8666e,
// the installed callbacks 86700 8684e 86f1c 86f88 8715e 871c4, the shared tail 8625a with the 27-slot table 862a0 and the helper
// 864b6), the stage event callback b630e with the b6506 child generator (installed b65f0, 28ae child b780c with the installed b7874)
// and the stage event callback dbe98 (installed dbebe). Boundaries without an executor: cc778 868ea 86c70 and 86742 (N19). The seven
// BCC/BCS consumers read the C of 4b54e 1ab02 49fc6 28ae b7e5c 288c 1aa7e; b6544 (ORI CCR) sets a known C. The table JMP 862a4(PC,D0.W)
// is the computed PC 862a4+D0.W (F1 main decision 3, no range check). N18 writes no port and changes no bank.
bool animation_objects_n18_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool flag=false;
    switch(r.pc) {
    // ---- 8625a (shared tail): JSR 4b54e.L; BCC.W 86352.
    case 0x8625a:return am_call(c,0x4b54e,0x86260);
    case 0x86260:return on18_carry(c,0x86352,0x86264);                    // BCC.W 86352 (C returned by 4b54e).
    case 0x86264:if(!on18_get(c,0x94,1,value))return false;r.pc=(value&255U)==0U?0x8631a:0x8626c;return true; // TST.B 94(A6); BEQ.W.
    case 0x8626c:if(!on18_get(c,0x5f,1,value))return false;r.pc=(value&0x80U)?0x86282:0x86274;return true; // TST.B 5f(A6); BMI.W.
    case 0x86274:if(!on18_bit(c,0x15,0,flag))return false;r.pc=flag?0x8631a:0x8627e;return true; // BTST.B #0,15(A6); BNE.W 8631a.
    case 0x8627e:r.pc=0x8628c;return true;                                 // BRA.W 8628c.
    case 0x86282:if(!on18_bit(c,0x15,0,flag))return false;r.pc=flag?0x8628c:0x8631a;return true; // BTST.B #0,15(A6); BEQ.W 8631a.
    // MOVE.B 5e(A6),D0; CMPI.B #1b,D0; BCC.W 8631a (unsigned).
    case 0x8628c:if(!on18_get(c,0x5e,1,value))return false;am_byte(r.d[0],value);r.pc=(value&255U)>=0x1bU?0x8631a:0x86298;return true;
    // ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; JMP 862a4(PC,D0.W) (computed PC, no range check).
    case 0x86298:am_word(r.d[0],((r.d[0]&255U)*4U)&65535U);r.pc=am_index(0x862a4,r.d[0]);return true;
    // The 27 table slots (BRA.W): k = 2 3 6 15 -> 86310, the others -> 8631a.
    case 0x862ac:case 0x862b0:case 0x862bc:case 0x862e0:r.pc=0x86310;return true;
    case 0x862a4:case 0x862a8:case 0x862b4:case 0x862b8:case 0x862c0:case 0x862c4:case 0x862c8:case 0x862cc:case 0x862d0:case 0x862d4:
    case 0x862d8:case 0x862dc:case 0x862e4:case 0x862e8:case 0x862ec:case 0x862f0:case 0x862f4:case 0x862f8:case 0x862fc:case 0x86300:
    case 0x86304:case 0x86308:case 0x8630c:r.pc=0x8631a;return true;
    case 0x86310:if(!on18_put(c,0x5e,1,0) || !on18_bitop(c,0x61,7,false))return false;r.pc=0x8631a;return true; // CLR.B 5e; BCLR #7,61.
    case 0x8631a:if(!on18_bit(c,0x61,7,flag))return false;r.pc=flag?0x86324:0x8634e;return true; // BTST.B #7,61(A6); BEQ.W 8634e.
    // CLR.B 17(A6); MOVE.B #ff,17(A6); LEA cdf30.L,A0; MOVEA.L 200140.L,A1; MOVE.W #e3,D1; MOVE.W #5,D2; JMP cc778.L.
    case 0x86324:
        if(!on18_put(c,0x17,1,0) || !on18_put(c,0x17,1,0xff))return false;r.a[0]=0xcdf30;
        if(!am_read(c,ON18_BANK_E3,4,value))return false;r.a[1]=value;am_word(r.d[1],0xe3);am_word(r.d[2],5);r.pc=0xcc778;return true;
    case 0x8634e:if(!on18_put(c,0x5e,1,0))return false;r.pc=0x86352;return true; // CLR.B 5e(A6).
    case 0x86352:r.a[0]=0x86252;return am_call(c,0x1ab02,0x8635c);       // LEA 86252(PC),A0; JSR 1ab02.L.
    case 0x8635c:return on18_carry(c,0x86370,0x86360);                    // BCC.W 86370 (C returned by 1ab02).
    // BSET.B #7,61(A6); CLR.W 54(A6); JMP 2a00.L.
    case 0x86360:if(!on18_bitop(c,0x61,7,true) || !on18_set_word(c,0x54,0))return false;r.pc=0x2a00;return true;
    case 0x86370:case 0x86640:case 0xb78b6:case 0xdbea2:case 0xdbeea:return am_return(c); // RTS.
    // ---- 864b6 (helper): JSR 49370.L; TST.B D0 and CMPI.B #1/#2,D0 select the target player.
    case 0x864b6:return am_call(c,0x49370,0x864bc);
    case 0x864bc:r.pc=(r.d[0]&255U)!=0U?0x864d0:0x864c2;return true;       // TST.B D0; BNE.W 864d0.
    case 0x864c2:case 0x86552:                                             // MOVE.B #ff,85(A6); MOVEA.W #0,A0; BRA.W 8658a.
        if(!on18_put(c,0x85,1,0xff))return false;r.a[0]=0;r.pc=0x8658a;return true;
    case 0x864d0:r.pc=(r.d[0]&255U)!=1U?0x864e6:0x864d8;return true;       // CMPI.B #1,D0; BNE.W 864e6.
    case 0x864d8:if(!on18_put(c,0x85,1,0))return false;r.a[0]=am_index(r.a[5],ON18_PLAYER1);r.pc=0x86568;return true;
    case 0x864e6:r.pc=(r.d[0]&255U)!=2U?0x864fc:0x864ee;return true;       // CMPI.B #2,D0; BNE.W 864fc.
    case 0x864ee:if(!on18_put(c,0x85,1,1))return false;r.a[0]=am_index(r.a[5],ON18_PLAYER2);r.pc=0x86568;return true;
    // LEA -7348(A5),A0; LEA -7258(A5),A1; MOVE.W 42(A0),D0; MOVE.W 42(A1),D1; MOVE.W 42(A6),D2; SUB.W D2,D0; BPL.W 86518.
    case 0x864fc:
        r.a[0]=am_index(r.a[5],ON18_PLAYER1);r.a[1]=am_index(r.a[5],ON18_PLAYER2);
        if(!am_read(c,am_index(r.a[0],0x42),2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,am_index(r.a[1],0x42),2,value))return false;am_word(r.d[1],value);
        if(!on18_get(c,0x42,2,value))return false;am_word(r.d[2],value);
        am_word(r.d[0],(r.d[0]-r.d[2])&65535U);r.pc=(r.d[0]&0x8000U)?0x86516:0x86518;return true;
    case 0x86516:case 0x868b2:on18_neg_word(r.d[0]);r.pc=r.pc==0x86516?0x86518:0x868b4;return true; // NEG.W D0.
    case 0x86518:am_word(r.d[1],(r.d[1]-r.d[2])&65535U);r.pc=(r.d[1]&0x8000U)?0x8651e:0x86520;return true; // SUB.W D2,D1; BPL.W.
    case 0x8651e:on18_neg_word(r.d[1]);r.pc=0x86520;return true;           // NEG.W D1.
    case 0x86520:if(!on18_get(c,0x85,1,value))return false;r.pc=(value&255U)!=0U?0x86530:0x86528;return true; // TST.B 85(A6); BNE.W.
    case 0x86528:am_word(r.d[0],(r.d[0]&65535U)>>2);am_word(r.d[1],(r.d[1]<<4)&65535U);r.pc=0x86534;return true; // LSR.W #2,D0; LSL.W #4,D1.
    case 0x86530:am_word(r.d[0],(r.d[0]<<4)&65535U);am_word(r.d[1],(r.d[1]&65535U)>>2);r.pc=0x86534;return true; // LSL.W #4,D0; LSR.W #2,D1.
    case 0x86534:am_word(r.d[0],(r.d[0]+r.d[1])&65535U);return am_call(c,0x49a84,0x8653c); // ADD.W D1,D0; JSR 49a84.L.
    // MOVEQ #0,D7; CMP.W D0,D1; BCC.W 8654a (unsigned D1.W >= D0.W).
    case 0x8653c:r.d[7]=0;r.pc=(r.d[1]&65535U)>=(r.d[0]&65535U)?0x8654a:0x86544;return true;
    case 0x86544:r.a[0]=r.a[1];r.d[7]=1;am_word(r.d[0],r.d[1]);r.pc=0x8654a;return true; // MOVEA.L A1,A0; MOVEQ #1,D7; MOVE.W D1,D0.
    // CMP.W 8a(A6),D0; BLE.W 86564 (signed D0.W <= 8a.W).
    case 0x8654a:if(!on18_get(c,0x8a,2,value))return false;r.pc=on18_signed_word(r.d[0])<=on18_signed_word(value)?0x86564:0x86552;return true;
    case 0x86564:if(!on18_put(c,0x85,1,r.d[7]&255U))return false;r.pc=0x86568;return true; // MOVE.B D7,85(A6).
    // CLR.B 84(A6); MOVE.W 42(A0),D0; CMP.W 42(A6),D0; SPL.B D0; BTST.B #0,15(A6); SNE.B D1; EOR.B D0,D1; BMI.W 8658a.
    case 0x86568:
        if(!on18_put(c,0x84,1,0) || !am_read(c,am_index(r.a[0],0x42),2,value))return false;am_word(r.d[0],value);
        if(!on18_get(c,0x42,2,other))return false;am_byte(r.d[0],(((value-other)&0x8000U)==0U)?0xffU:0U);
        if(!on18_bit(c,0x15,0,flag))return false;am_byte(r.d[1],flag?0xffU:0U);am_byte(r.d[1],(r.d[1]^r.d[0])&255U);
        r.pc=(r.d[1]&0x80U)?0x8658a:0x86584;return true;
    case 0x86584:if(!on18_bitop(c,0x84,0,true))return false;r.pc=0x8658a;return true; // BSET.B #0,84(A6).
    case 0x8658a:if(!on18_get(c,0x8e,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)==0U?0x86598:0x86592;return true;
    case 0x86592:am_word(r.d[0],(r.d[0]-1U)&65535U);if(!on18_set_word(c,0x8e,r.d[0]))return false;r.pc=0x86598;return true; // SUBQ.W #1,D0; MOVE.W D0,8e(A6).
    // BCLR.B #3,84(A6); MOVE.W 42(A6),D0; SUBI.W #20,D0; CMPI.W #100,D0; BCC.W 865c0 (unsigned).
    case 0x86598:
        if(!on18_bitop(c,0x84,3,false) || !on18_get(c,0x42,2,value))return false;am_word(r.d[0],(value-0x20U)&65535U);
        r.pc=(r.d[0]&65535U)>=0x100U?0x865c0:0x865ae;return true;
    // MOVE.W 46(A6),D0; SUBI.W #20,D0; CMPI.W #c0,D0; BSET.B #3,84(A6) (no branch after the compare in the original).
    case 0x865ae:if(!on18_get(c,0x46,2,value))return false;am_word(r.d[0],(value-0x20U)&65535U);if(!on18_bitop(c,0x84,3,true))return false;r.pc=0x865c0;return true;
    // MOVEQ #0,D0; MOVE.W #20,D1; MOVE.W #10,D2; MOVE.W #24,D3; BTST.B #0,15(A6); BNE.W 865da.
    case 0x865c0:
        r.d[0]=0;am_word(r.d[1],0x20);am_word(r.d[2],0x10);am_word(r.d[3],0x24);if(!on18_bit(c,0x15,0,flag))return false;
        r.pc=flag?0x865da:0x865d8;return true;
    case 0x865d8:on18_neg_word(r.d[2]);r.pc=0x865da;return true;           // NEG.W D2.
    case 0x865da:return am_call(c,0x4c29a,0x865e0);
    case 0x865e0:r.pc=((r.d[6]>>3)&1U)?0x865e8:0x865f2;return true;        // BTST.B #3,D6; BEQ.W 865f2.
    case 0x865e8:if(!on18_bitop(c,0x84,1,true))return false;r.pc=0x8660e;return true; // BSET.B #1,84(A6); BRA.W 8660e.
    case 0x865f2:r.pc=((r.d[6]>>6)&1U)?0x865fa:0x86600;return true;        // BTST.B #6,D6; BEQ.W 86600.
    case 0x865fa:if(!on18_bitop(c,0x84,4,true))return false;r.pc=0x86600;return true; // BSET.B #4,84(A6).
    case 0x86600:r.pc=((r.d[6]>>2)&1U)?0x86608:0x8660e;return true;        // BTST.B #2,D6; BEQ.W 8660e.
    case 0x86608:if(!on18_bitop(c,0x84,5,true))return false;r.pc=0x8660e;return true; // BSET.B #5,84(A6).
    // MOVE.W #8,D0; BTST.B #0,15(A6); BNE.W 8661e.
    case 0x8660e:am_word(r.d[0],8);if(!on18_bit(c,0x15,0,flag))return false;r.pc=flag?0x8661e:0x8661c;return true;
    case 0x8661c:on18_neg_word(r.d[0]);r.pc=0x8661e;return true;           // NEG.W D0.
    case 0x8661e:return am_call(c,0x4c1de,0x86624);
    case 0x86624:r.pc=((r.d[6]>>2)&1U)?0x8662c:0x86632;return true;        // BTST.B #2,D6; BEQ.W 86632.
    case 0x8662c:if(!on18_bitop(c,0x84,2,true))return false;r.pc=0x86632;return true; // BSET.B #2,84(A6).
    case 0x86632:r.pc=(r.d[6]&1U)?0x86640:0x8663a;return true;             // BTST.B #0,D6; BNE.W 86640.
    case 0x8663a:if(!on18_bitop(c,0x84,7,true))return false;r.pc=0x86640;return true; // BSET.B #7,84(A6).
    // ---- Initial entries: MOVE.W #4/#0/#1/#2,92(A6) (8664c also ST.B 94(A6)); BRA.W 8666e.
    case 0x86642:if(!on18_set_word(c,0x92,4))return false;r.pc=0x8666e;return true;
    case 0x8664c:if(!on18_put(c,0x94,1,0xff) || !on18_set_word(c,0x92,0))return false;r.pc=0x8666e;return true;
    case 0x8665a:if(!on18_set_word(c,0x92,1))return false;r.pc=0x8666e;return true;
    case 0x86664:if(!on18_set_word(c,0x92,2))return false;r.pc=0x8666e;return true;
    // MOVE.L #28000,86(A6); 8a/90/8e/8c = 78/7a/7c/7e (WORD); MOVE.W #4f,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0x8666e:
        if(!on18_put(c,0x86,4,0x28000))return false;
        if(!on18_get(c,0x78,2,value) || !on18_put(c,0x8a,2,value) || !on18_get(c,0x7a,2,value) || !on18_put(c,0x90,2,value))return false;
        if(!on18_get(c,0x7c,2,value) || !on18_put(c,0x8e,2,value) || !on18_get(c,0x7e,2,value) || !on18_put(c,0x8c,2,value))return false;
        am_word(r.d[0],0x4f);am_word(r.d[1],1);am_byte(r.d[2],0);return am_call(c,0xc6a96,0x866a0);
    case 0x866a0:am_word(r.d[0],0xc8e);return am_call(c,0x4a496,0x866aa);  // MOVE.W #c8e,D0; JSR 4a496.L.
    // MOVE.B 19(A6),14(A6); MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVE.W #28,54(A6); TST.W 76(A6); BNE.W 866d0.
    case 0x866aa:
        if(!on18_get(c,0x19,1,value) || !on18_put(c,0x14,1,value) || !on18_set_word(c,0x68,0x8820) || !on18_set_word(c,0x1e,0x8820) ||
            !on18_set_word(c,0x54,0x28) || !on18_get(c,0x76,2,value))return false;
        r.pc=(value&65535U)!=0U?0x866d0:0x866ca;return true;
    case 0x866ca:if(!on18_bitop(c,0x15,0,true))return false;r.pc=0x866d0;return true; // BSET.B #0,15(A6).
    case 0x866d0:return am_call(c,0x864b6,0x866d4);                       // JSR 864b6(PC).
    case 0x866d4:if(!on18_get(c,0x92,2,value))return false;r.pc=(value&65535U)!=4U?0x866ee:0x866de;return true; // CMPI.W #4,92(A6); BNE.W.
    // MOVE.W #1,92(A6); MOVE.L #86c70,(A6); BRA.W 86c70 (boundary).
    case 0x866de:if(!on18_set_word(c,0x92,1))return false;return on18_install(c,0x86c70,0x86c70);
    case 0x866ee:if(!on18_get(c,0x80,2,value))return false;r.pc=(value&65535U)==0U?0x86700:0x866f6;return true; // TST.W 80(A6); BEQ.W.
    case 0x866f6:return on18_install(c,0x868ea,0x868ea);                  // MOVE.L #868ea,(A6); BRA.W 868ea (boundary).
    // ---- 86700 (installed): TST.W 92(A6); BNE.W 8670c.
    case 0x86700:if(!on18_get(c,0x92,2,value))return false;r.pc=(value&65535U)!=0U?0x8670c:0x86708;return true;
    case 0x86708:r.pc=0x86814;return true;                                 // BRA.W 86814.
    case 0x8670c:return on18_animation(c,ON18_BANK_E3,0xe3,0x4,0x86734);  // animation record + 4.
    // MOVE.L #0,64(A6); MOVE.L #86742,(A6) (fall-through into 86742, N19).
    case 0x86734:if(!on18_put(c,0x64,4,0))return false;return on18_install(c,0x86742,0x86742);
    // MOVE.L #0,64(A6); ST.B 94(A6); animation record + 40.
    case 0x86814:if(!on18_put(c,0x64,4,0) || !on18_put(c,0x94,1,0xff))return false;return on18_animation(c,ON18_BANK_E3,0xe3,0x40,0x86848);
    case 0x86848:return on18_install(c,0x8684e,0x8684e);                  // MOVE.L #8684e,(A6).
    // ---- 8684e (installed): JSR 864b6(PC); JSR 4be06.L; JSR 49fc6.L; TST.B 85(A6); BMI.W 868d6.
    case 0x8684e:return am_call(c,0x864b6,0x86852);
    case 0x86852:return am_call(c,0x4be06,0x86858);
    case 0x86858:return am_call(c,0x49fc6,0x8685e);
    case 0x8685e:if(!on18_get(c,0x85,1,value))return false;r.pc=(value&0x80U)?0x868d6:0x86866;return true;
    case 0x86866:if(!on18_bit(c,0x84,0,flag))return false;r.pc=flag?0x8687a:0x86870;return true; // BTST.B #0,84(A6); BNE.W 8687a.
    case 0x86870:return on18_install(c,0x86e76,0x868d6);                  // MOVE.L #86e76,(A6); BRA.W 868d6.
    case 0x8687a:if(!on18_get(c,0x8e,2,value))return false;r.pc=(value&65535U)!=0U?0x86892:0x86882;return true; // TST.W 8e(A6); BNE.W.
    case 0x86882:if(!on18_bit(c,0x84,3,flag))return false;r.pc=flag?0x8688c:0x86892;return true; // BTST.B #3,84(A6); BEQ.W 86892.
    case 0x8688c:return on18_install(c,0x871ee,0x86892);
    case 0x86892:if(!on18_get(c,0x85,1,value))return false;r.pc=(value&255U)!=0U?0x868a2:0x8689a;return true; // TST.B 85(A6); BNE.W.
    case 0x8689a:r.a[0]=am_index(r.a[5],ON18_PLAYER1);r.pc=0x868a6;return true; // LEA -7348(A5),A0; BRA.W 868a6.
    case 0x868a2:r.a[0]=am_index(r.a[5],ON18_PLAYER2);r.pc=0x868a6;return true; // LEA -7258(A5),A0.
    case 0x868a6:if(!on18_distance(c,flag))return false;r.pc=flag?0x868b4:0x868b2;return true; // MOVE.W 42(A0),D0; SUB.W 42(A6),D0; BPL.W.
    // CMP.W 8c(A6),D0; BLE.W 868d6 (signed D0.W <= 8c.W).
    case 0x868b4:if(!on18_get(c,0x8c,2,value))return false;r.pc=on18_signed_word(r.d[0])<=on18_signed_word(value)?0x868d6:0x868bc;return true;
    case 0x868bc:if(!on18_bit(c,0x84,7,flag))return false;r.pc=flag?0x868c6:0x868d0;return true; // BTST.B #7,84(A6); BEQ.W 868d0.
    case 0x868c6:return on18_install(c,0x86fca,0x868d6);                  // MOVE.L #86fca,(A6); BRA.W 868d6.
    case 0x868d0:return on18_install(c,0x8698c,0x868d6);
    case 0x868d6:case 0x871da:                                             // BTST.B #7,15(A6); BNE.W 868e6 / 871ea.
        if(!on18_bit(c,0x15,7,flag))return false;
        r.pc=r.pc==0x868d6?(flag?0x868e6:0x868e0):(flag?0x871ea:0x871e4);return true;
    case 0x868e0:return on18_install(c,0x86f1c,0x868e6);
    case 0x868e6:case 0x86fc6:case 0x871ea:r.pc=0x8625a;return true;      // BRA.W 8625a.
    // ---- 86f1c / 8715e (installed): CLR.B 94(A6); MOVE.W 92(A6),D0; BNE.W.
    case 0x86f1c:case 0x8715e:
        if(!on18_put(c,0x94,1,0) || !on18_get(c,0x92,2,value))return false;am_word(r.d[0],value);
        r.pc=(value&65535U)!=0U?(r.pc==0x86f1c?0x86f54:0x87196):(r.pc==0x86f1c?0x86f28:0x8716a);return true;
    case 0x86f28:return on18_animation(c,ON18_BANK_E3,0xe3,0xa8,0x86f50);
    case 0x86f50:r.pc=0x86f7c;return true;                                 // BRA.W 86f7c.
    case 0x86f54:return on18_animation(c,ON18_BANK_E3,0xe3,0x10,0x86f7c);
    // MOVE.L 64(A6),36(A6); MOVE.L #86f88,(A6).
    case 0x86f7c:if(!on18_get(c,0x64,4,value) || !on18_put(c,0x36,4,value))return false;return on18_install(c,0x86f88,0x86f88);
    case 0x86f88:return am_call(c,0x864b6,0x86f8c);
    // MOVE.L 64(A6),D0; SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6); MOVE.L #fff00000,D0; SUB.L 3a(A6),D0; ASR.L #5,D0;
    // ADD.L D0,3a(A6); JSR 4be34.L.
    case 0x86f8c:
        if(!on18_get(c,0x64,4,value) || !on18_get(c,0x36,4,other))return false;r.d[0]=on18_asr5(value-other);
        if(!on18_get(c,0x36,4,value) || !on18_put(c,0x36,4,value+r.d[0]))return false;
        if(!on18_get(c,0x3a,4,other))return false;r.d[0]=on18_asr5(0xfff00000U-other);
        if(!on18_get(c,0x3a,4,value) || !on18_put(c,0x3a,4,value+r.d[0]))return false;
        return am_call(c,0x4be34,0x86fb0);
    case 0x86fb0:return am_call(c,0x49fc6,0x86fb6);
    case 0x86fb6:if(!on18_bit(c,0x15,7,flag))return false;r.pc=flag?0x86fc0:0x86fc6;return true; // BTST.B #7,15(A6); BEQ.W 86fc6.
    case 0x86fc0:return on18_install(c,0x8715e,0x86fc6);
    case 0x8716a:return on18_animation(c,ON18_BANK_E3,0xe3,0xac,0x87192);
    case 0x87192:r.pc=0x871be;return true;                                 // BRA.W 871be.
    case 0x87196:return on18_animation(c,ON18_BANK_E3,0xe3,0x14,0x871be);
    case 0x871be:return on18_install(c,0x871c4,0x871c4);
    // ---- 871c4 (installed): JSR 4be06.L; JSR 49fc6.L; BCC.W 871da.
    case 0x871c4:return am_call(c,0x4be06,0x871ca);
    case 0x871ca:return am_call(c,0x49fc6,0x871d0);
    case 0x871d0:return on18_carry(c,0x871da,0x871d4);                    // BCC.W 871da (C returned by 49fc6).
    case 0x871d4:return on18_install(c,0x86700,0x871da);
    case 0x871e4:return on18_install(c,0x86f1c,0x871ea);
    // ---- b630e (stage event callback): MOVE.W #0,8e(A6); BSR.W b7bc2; BRA.W b6506.
    case 0xb630e:if(!on18_set_word(c,0x8e,0))return false;return am_call(c,0xb7bc2,0xb6318);
    case 0xb6318:r.pc=0xb6506;return true;
    // MOVE.W 78(A6),D0; CMPI.W #4,D0; BCS.W b6516 (unsigned).
    case 0xb6506:if(!on18_get(c,0x78,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)<4U?0xb6516:0xb6512;return true;
    case 0xb6512:am_word(r.d[0],3);r.pc=0xb6516;return true;               // MOVE.W #3,D0.
    // MOVE.W D0,78(A6); LEA b7f04(PC),A0; LSL.W #2,D0; MOVE.L (A0,D0.W),56(A6).
    case 0xb6516:
        if(!on18_set_word(c,0x78,r.d[0]))return false;r.a[0]=0xb7f04;am_word(r.d[0],(r.d[0]<<2)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value) || !on18_put(c,0x56,4,value))return false;r.pc=0xb6526;return true;
    case 0xb6526:r.a[0]=0xb780c;am_word(r.d[0],0x14);return am_call(c,0x28ae,0xb6536); // MOVEA.L #b780c,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0xb6536:return on18_carry(c,0xb6548,0xb653a);                    // BCC.W b6548 (C returned by 28ae).
    case 0xb653a:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0xb6544); // CLR.W D0; CLR.W D1; JSR 4970a.L.
    case 0xb6544:r.carry=AnimationCarrySet;r.pc=0xb6548;return true;       // ORI.B #1,CCR.
    // MOVE.W 8e(A6),8e(A0); MOVE.W 78(A6),78(A0); SUBQ.W #1,78(A6); BCC.B b6526 (no borrow).
    case 0xb6548:
        if(!on18_get(c,0x8e,2,value) || !am_write(c,am_index(r.a[0],0x8e),2,value))return false;
        if(!on18_get(c,0x78,2,value) || !am_write(c,am_index(r.a[0],0x78),2,value))return false;
        if(!on18_get(c,0x78,2,value) || !on18_set_word(c,0x78,value-1U))return false;
        r.pc=(value&65535U)!=0U?0xb6526:0xb655a;return true;
    case 0xb655a:if(!on18_get(c,0x8e,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)!=0U?0xb65a2:0xb6566;return true;
    case 0xb6566:return on18_indexed_animation(c,ON18_BANK_1B3,0x1b3,0xb659e);
    case 0xb659e:r.pc=0xb65da;return true;                                 // BRA.W b65da.
    case 0xb65a2:return on18_indexed_animation(c,ON18_BANK_1BB,0x1bb,0xb65da);
    // MOVE.L #0,96(A6); MOVE.L #18,98(A6); MOVE.L #b65f0,(A6).
    case 0xb65da:if(!on18_put(c,0x96,4,0) || !on18_put(c,0x98,4,0x18))return false;return on18_install(c,0xb65f0,0xb65f0);
    // ---- b65f0 (installed): JSR 43e34.L; JSR 49fc6.L; JSR b7e5c(PC); BCC.W b660a; MOVE.L #b660e,(A6); BRA.W b76d2.
    case 0xb65f0:return am_call(c,0x43e34,0xb65f6);
    case 0xb65f6:return am_call(c,0x49fc6,0xb65fc);
    case 0xb65fc:return am_call(c,0xb7e5c,0xb6600);
    case 0xb6600:return on18_carry(c,0xb660a,0xb6604);                    // BCC.W b660a (C returned by b7e5c).
    case 0xb6604:return on18_install(c,0xb660e,0xb660a);
    case 0xb660a:r.pc=0xb76d2;return true;                                 // BRA.W b76d2.
    // ---- b780c (28ae child): MOVE.W 8e(A6),D0; LEA b7f14(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xb780c:
        if(!on18_get(c,0x8e,2,value))return false;am_word(r.d[0],value);r.a[0]=0xb7f14;am_word(r.d[0],(r.d[0]*2U)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xb7824);
    // SUBQ.W #1,1e(A6); MOVEA.L c(A6),A0; MOVE.W 12(A0),12(A6); MOVE.W 78(A6),D0; LSL.W #4,D0; MOVE.W D0,D1; ADD.W D1,D0; ADD.W D0,D1;
    // CLR.W D0; JSR 49290.L.
    case 0xb7824:
        if(!on18_get(c,0x1e,2,value) || !on18_set_word(c,0x1e,value-1U) || !on18_get(c,0x0c,4,value))return false;r.a[0]=value;
        if(!am_read(c,am_index(r.a[0],0x12),2,value) || !on18_set_word(c,0x12,value) || !on18_get(c,0x78,2,value))return false;
        am_word(r.d[0],(value<<4)&65535U);am_word(r.d[1],r.d[0]);am_word(r.d[0],(r.d[0]+r.d[1])&65535U);am_word(r.d[1],(r.d[1]+r.d[0])&65535U);
        am_word(r.d[0],0);return am_call(c,0x49290,0xb7846);
    case 0xb7846:return on18_animation(c,ON18_BANK_1B3,0x1b3,0xc,0xb786e);
    case 0xb786e:return on18_install(c,0xb7874,0xb7874);
    // ---- b7874 (installed): JSR 43e34.L; JSR 49fc6.L; MOVEA.L c(A6),A0; TST.B 5e(A0); BEQ.W b7892.
    case 0xb7874:return am_call(c,0x43e34,0xb787a);
    case 0xb787a:return am_call(c,0x49fc6,0xb7880);
    case 0xb7880:
        if(!on18_get(c,0x0c,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x5e),1,value))return false;
        r.pc=(value&255U)==0U?0xb7892:0xb788c;return true;
    case 0xb788c:return on18_install(c,0xb78b8,0xb7892);
    case 0xb7892:return am_call(c,0x288c,0xb7898);
    case 0xb7898:return on18_carry(c,0xb789c,0xb78a2);                    // BCS.W b78a2 (C returned by 288c).
    case 0xb789c:return on18_install(c,0xb7742,0xb78a2);
    case 0xb78a2:r.a[0]=0xb7ef4;return am_call(c,0x1aa7e,0xb78ac);       // LEA b7ef4(PC),A0; JSR 1aa7e.L.
    case 0xb78ac:return on18_carry(c,0xb78b6,0xb78b0);                    // BCC.W b78b6 (C returned by 1aa7e).
    case 0xb78b0:return on18_install(c,0xb7742,0xb78b6);
    // ---- dbe98 (stage event callback): CMPI.W #280,5418(A5); BGE.W dbea4 (signed).
    case 0xdbe98:
        if(!am_read(c,am_index(r.a[5],0x5418),2,value))return false;r.pc=on18_signed_word(value)>=0x280?0xdbea4:0xdbea2;return true;
    case 0xdbea4:return am_call(c,0x4814e,0xdbeaa);
    // MOVE.L #dbe6c,76(A6); MOVE.W #3c,7a(A6); MOVE.L #dbebe,(A6).
    case 0xdbeaa:if(!on18_put(c,0x76,4,0xdbe6c) || !on18_set_word(c,0x7a,0x3c))return false;return on18_install(c,0xdbebe,0xdbebe);
    // ---- dbebe (installed): SUBQ.W #1,7a(A6); BCC.W dbeea (no borrow).
    case 0xdbebe:if(!on18_get(c,0x7a,2,value) || !on18_set_word(c,0x7a,value-1U))return false;r.pc=(value&65535U)!=0U?0xdbeea:0xdbec6;return true;
    // MOVEA.L 76(A6),A0; MOVE.W (A0),D0; JSR 3af8.L.
    case 0xdbec6:
        if(!on18_get(c,0x76,4,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);
        return am_call(c,0x3af8,0xdbed2);
    // MOVEA.L 76(A6),A0; MOVE.W 2(A0),7a(A6); BNE.W dbee6.
    case 0xdbed2:
        if(!on18_get(c,0x76,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],2),2,value) || !on18_set_word(c,0x7a,value))return false;
        r.pc=(value&65535U)!=0U?0xdbee6:0xdbee0;return true;
    case 0xdbee0:r.pc=0x2a00;return true;                                  // JMP 2a00.L.
    case 0xdbee6:if(!on18_get(c,0x76,4,value) || !on18_put(c,0x76,4,value+4U))return false;r.pc=0xdbeea;return true; // ADDQ.L #4,76(A6).
    default:return am_error(c,"unsupported animation objects n18 PC");
    }
}
}
