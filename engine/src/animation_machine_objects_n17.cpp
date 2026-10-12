#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONG (live bus, current PVC bank): MOVE.L 2000d4.L,22(A6) / MOVEA.L 2000d4.L,A1 (animation record of the 7a53c family).
const std::uint32_t ON17_BANK_RECORD=0x2000d4;
bool on17_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on17_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Two's complement values of 68000 operands, compared as signed numbers (no signed overflow in C++).
int on17_signed_byte(std::uint32_t value) {
    value&=255U;return (value&0x80U)?static_cast<int>(value)-256:static_cast<int>(value);
}
int on17_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<int>(value)-65536:static_cast<int>(value);
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on17_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n17 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,displacement(A6) then continue at next_pc.
bool on17_install(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t next_pc) {
    if(!on17_put(c,displacement,4,target))return false;c.s.pc=next_pc;return true;
}
// BTST.B #bit,displacement(base): true when the bit is set.
bool on17_bit_at(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!am_read(c,am_index(base,displacement),1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
bool on17_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    return on17_bit_at(c,c.s.a[6],displacement,bit,set);
}
// BSET.B / BCLR.B #bit,displacement(A6) (set true: BSET, false: BCLR).
bool on17_bitop(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!on17_get(c,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;value=set?(value|mask):(value&~mask);return on17_put(c,displacement,1,value&255U);
}
// MOVE.W #number,D0; MOVE.B #0,D1; JSR 8ebe.L.
bool on17_sound(AnimationMachineContext& c,std::uint32_t number,std::uint32_t return_pc) {
    am_word(c.s.d[0],number);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.L.
bool on17_list(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.B #ff,17(A6) ... LEA cdef8.L,A0; MOVEA.L 2000d4.L,A1; MOVE.W #b,D1; MOVE.W #1,D2; JMP cc778.L (after the node writes).
bool on17_debris(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=0xcdef8;if(!am_read(c,ON17_BANK_RECORD,4,value))return false;r.a[1]=value;
    am_word(r.d[1],0xb);am_word(r.d[2],1);r.pc=0xcc778;return true;
}
// MOVE.L #0,56(A6); MOVE.L #7abc2,(A6) (installed value outside the unit).
bool on17_release(AnimationMachineContext& c,std::uint32_t next_pc) {
    if(!on17_put(c,0x56,4,0) || !on17_put(c,0,4,0x7abc2))return false;c.s.pc=next_pc;return true;
}
// CLR.L 36(A6); CLR.L 3a(A6).
bool on17_stop_motion(AnimationMachineContext& c) {
    return on17_put(c,0x36,4,0) && on17_put(c,0x3a,4,0);
}
}
// Objects F4 N17 (190 block starts): the stage event callback 7a53c (helpers 7afa6 7b018 7b1a2, the 28ae child 7aa6e with the installed
// 7aae6), the shared step 7a388 (7b200 7b7ae), the installed 7a674 (7b23a 7b268 7b140 7b570), 7a48e 7a4e0 (28ae child 7a516), the
// deletions 7aa5e 7aa66, the parent-installed 7a3b2 with 7a40a 7a426 (7b17c, the DBRA clear 7a45a) and the interpreter table callbacks
// 7b740 7b74a 7b754 7b786 7b790. Boundaries without an executor: 7a558 7b8a8 72f40 7b834 7b28e cc778. Known C: Set 7a502 7b0f4 7b21c
// 7b22e 7b250 7b588 7b7ce, Clear 7b214 7b25c 7b596 7b59e; the 11 BCC/BCS consumers read the C of 7b200 7b7ae 7b570 (N17 helpers),
// 49fc6 28ae 4b54e 288c 497a6. N17 writes no port and changes no bank.
bool animation_objects_n17_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool flag=false;
    switch(r.pc) {
    // ---- 7a388 (shared step): SUBQ.W #1,82(A6); JSR 7b200(PC); BCC.W 7a398; CLR.B 5e(A6).
    case 0x7a388:if(!on17_get(c,0x82,2,value) || !on17_put(c,0x82,2,(value-1U)&65535U))return false;return am_call(c,0x7b200,0x7a390);
    case 0x7a390:return on17_carry(c,0x7a398,0x7a394);                    // BCC.W 7a398 (C returned by 7b200).
    case 0x7a394:if(!on17_put(c,0x5e,1,0))return false;r.pc=0x7a398;return true;
    case 0x7a398:if(!on17_bit(c,0x61,7,flag))return false;r.pc=flag?0x7a476:0x7a3a2;return true; // BTST.B #7,61(A6); BNE.W 7a476.
    case 0x7a3a2:case 0x7a506:return am_call(c,0x7b7ae,r.pc+4U);          // JSR 7b7ae(PC).
    case 0x7a3a6:return on17_carry(c,0x7a3b0,0x7a3aa);                    // BCC.W 7a3b0 (C returned by 7b7ae).
    case 0x7a3aa:return on17_install(c,0,0x7aa5e,0x7a3b0);               // MOVE.L #7aa5e,(A6).
    case 0x7a3b0:case 0x7a4de:case 0x7a514:case 0x7abc0:case 0x7b118:case 0x7b17a:case 0x7b238:case 0x7b28c:case 0x7b5a6:case 0x7b7cc:
        return am_return(c);                                               // RTS.
    // ---- 7a3b2 (installed into the parent node by 7ab80): JSR 496c2.L; JSR 46ef4.L.
    case 0x7a3b2:return am_call(c,0x496c2,0x7a3b8);
    case 0x7a3b8:case 0x7a480:return am_call(c,0x46ef4,r.pc+6U);           // JSR 46ef4.L.
    // MOVE.W #100,2c(A6); BTST.B #6,98(A6); BEQ.W 7a3d2.
    case 0x7a3be:if(!on17_put(c,0x2c,2,0x100) || !on17_bit(c,0x98,6,flag))return false;r.pc=flag?0x7a3ce:0x7a3d2;return true;
    case 0x7a3ce:return am_call(c,0x7b8a8,0x7a3d2);                       // JSR 7b8a8(PC) (boundary).
    // LEA 26(A6),A0; MOVE.W #b,20(A6); MOVE.L 2000d4.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 2c(A1),A1;
    // JSR 49f8c.L.
    case 0x7a3d2:
        r.a[0]=am_index(r.a[6],0x26);
        if(!on17_put(c,0x20,2,0xb) || !am_read(c,ON17_BANK_RECORD,4,value) || !on17_put(c,0x22,4,value))return false;am_word(r.d[0],0x100);
        if(!on17_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],0x2c),4,value))return false;r.a[1]=value;
        return am_call(c,0x49f8c,0x7a3fa);
    case 0x7a3fa:case 0x7a476:r.a[0]=0;return am_call(c,0x4b82e,r.pc+0xaU); // LEA 0.W,A0; JSR 4b82e.L.
    case 0x7a404:return on17_install(c,0,0x7a40a,0x7a40a);               // MOVE.L #7a40a,(A6).
    case 0x7a40a:return am_call(c,0x7b17c,0x7a40e);
    case 0x7a40e:case 0x7a680:case 0x7ab44:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.L.
    case 0x7a414:return on17_carry(c,0x7a41e,0x7a418);                    // BCC.W 7a41e (C returned by 49fc6).
    case 0x7a418:return on17_install(c,0,0x7a426,0x7a41e);
    case 0x7a41e:if(!on17_put(c,0x56,4,0))return false;r.pc=0x7a388;return true; // CLR.L 56(A6); BRA.W 7a388.
    // ---- 7a426 (installed): MOVE.W #b,20(A6); BCLR.B #7,61(A6); CLR.B 5e(A6); MOVE.B #ff,17(A6); LEA 0.W,A0; JSR 4b82e.L.
    case 0x7a426:
        if(!on17_put(c,0x20,2,0xb) || !on17_bitop(c,0x61,7,false) || !on17_put(c,0x5e,1,0) || !on17_put(c,0x17,1,0xff))return false;
        r.a[0]=0;return am_call(c,0x4b82e,0x7a446);
    // LEA 76(A6),A0; LEA 99(A6),A1; MOVE.L A0,D0; MOVE.L A1,D1; SUB.L D0,D1; MOVE.W D1,D0; LSR.W #1,D1; MOVEQ #0,D2.
    case 0x7a446:
        r.a[0]=am_index(r.a[6],0x76);r.a[1]=am_index(r.a[6],0x99);r.d[0]=r.a[0];r.d[1]=r.a[1]-r.d[0];am_word(r.d[0],r.d[1]);
        am_word(r.d[1],(r.d[1]&65535U)>>1);r.d[2]=0;r.pc=0x7a45a;return true;
    // MOVE.W D2,(A0)+; DBRA D1,7a45a (one iteration per block).
    case 0x7a45a:
        if(!am_write(c,r.a[0],2,r.d[2]&65535U))return false;r.a[0]+=2U;am_word(r.d[1],(r.d[1]-1U)&65535U);
        r.pc=(r.d[1]&65535U)!=65535U?0x7a45a:0x7a460;return true;
    case 0x7a460:r.pc=(r.d[0]&1U)==0U?0x7a46a:0x7a468;return true;         // BTST.B #0,D0; BEQ.W 7a46a.
    case 0x7a468:if(!am_write(c,r.a[0],1,r.d[2]&255U))return false;r.a[0]+=1U;r.pc=0x7a46a;return true; // MOVE.B D2,(A0)+.
    case 0x7a46a:if(!on17_put(c,0x70,2,1))return false;r.pc=0x72f40;return true; // MOVE.W #1,70(A6); JMP 72f40.L (boundary).
    // ---- 7a476 (destroyed): LEA 0.W,A0; JSR 4b82e.L (above); JSR 46ef4.L (above); MOVE.L #7a48e,(A6); RTS.
    case 0x7a486:if(!on17_put(c,0,4,0x7a48e))return false;return am_return(c);
    // ---- 7a48e (installed): BTST.B #6,98(A6); BEQ.W 7a4aa; JSR 7b834(PC); JSR 7b28e(PC); MOVE.L #7a4e0,(A6); BRA.W 7a4de.
    case 0x7a48e:if(!on17_bit(c,0x98,6,flag))return false;r.pc=flag?0x7a498:0x7a4aa;return true;
    case 0x7a498:return am_call(c,0x7b834,0x7a49c);                       // boundary.
    case 0x7a49c:return am_call(c,0x7b28e,0x7a4a0);                       // boundary.
    case 0x7a4a0:return on17_install(c,0,0x7a4e0,0x7a4de);
    // MOVE.B #ff,17(A6); MOVE.B 8e(A6),5e(A6); MOVE.W #b,20(A6); MOVE.B #ff,17(A6); LEA cdef8.L,A0; MOVEA.L 2000d4.L,A1; MOVE.W #b,D1;
    // MOVE.W #1,D2; JMP cc778.L.
    case 0x7a4aa:
        if(!on17_put(c,0x17,1,0xff) || !on17_get(c,0x8e,1,value) || !on17_put(c,0x5e,1,value) || !on17_put(c,0x20,2,0xb) ||
            !on17_put(c,0x17,1,0xff))return false;
        return on17_debris(c);
    // ---- 7a4e0 (installed): MOVEA.L #7a516,A0; MOVE.W #14,D0; JSR 28ae.L; BCC.W 7a506.
    case 0x7a4e0:r.a[0]=0x7a516;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x7a4f0);
    case 0x7a4f0:return on17_carry(c,0x7a506,0x7a4f4);                    // BCC.W 7a506 (C returned by 28ae).
    case 0x7a4f4:am_word(r.d[0],0);am_word(r.d[1],0x18);return am_call(c,0x4970a,0x7a502); // MOVE.W #0,D0; MOVE.W #18,D1; JSR 4970a.L.
    case 0x7a502:r.carry=AnimationCarrySet;r.pc=0x7a506;return true;       // ORI.B #1,CCR (Set).
    case 0x7a50a:return on17_carry(c,0x7a514,0x7a50e);                    // BCC.W 7a514 (C returned by 7b7ae).
    case 0x7a50e:return on17_install(c,0,0x7aa5e,0x7a514);
    // ---- 7a516 (28ae child callback): MOVE.W #d2,20(A6); MOVE.W #20d,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0x7a516:if(!on17_put(c,0x20,2,0xd2))return false;return on17_sound(c,0x20d,0x7a52a);
    case 0x7a52a:return on17_list(c,0x7c6b6,0x7a53a);                     // MOVEA.L #7c6b6,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x7a53a:r.pc=0x7a506;return true;                                 // BRA.B 7a506.
    // ---- 7a53c (stage event callback): MOVE.W #16b,20(A6); JSR 7afa6(PC); JSR 7b018(PC); BTST.B #0,98(A6); BNE.W 7a65a; BRA.W 7a558.
    case 0x7a53c:if(!on17_put(c,0x20,2,0x16b))return false;return am_call(c,0x7afa6,0x7a546);
    case 0x7a546:return am_call(c,0x7b018,0x7a54a);
    case 0x7a54a:if(!on17_bit(c,0x98,0,flag))return false;r.pc=flag?0x7a65a:0x7a554;return true;
    case 0x7a554:r.pc=0x7a558;return true;                                 // BRA.W 7a558 (boundary).
    // ---- 7a65a: JSR 7b1a2(PC); MOVEA.L #7bd7c,A1; MOVE.W #100,D0; JSR 49f8c.L; MOVE.L #7a674,(A6).
    case 0x7a65a:return am_call(c,0x7b1a2,0x7a65e);
    case 0x7a65e:return on17_list(c,0x7bd7c,0x7a66e);
    case 0x7a66e:return on17_install(c,0,0x7a674,0x7a674);
    // ---- 7a674 (installed): JSR 7b23a(PC); JSR 7b268(PC); JSR 7b140(PC); JSR 49fc6.L (above).
    case 0x7a674:return am_call(c,0x7b23a,0x7a678);
    case 0x7a678:return am_call(c,0x7b268,0x7a67c);
    case 0x7a67c:return am_call(c,0x7b140,0x7a680);
    // MOVE.W 86(A6),D0; CLR.W D1; JSR 4929e.L.
    case 0x7a686:if(!on17_get(c,0x86,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],0);return am_call(c,0x4929e,0x7a692);
    case 0x7a692:if(!on17_bit(c,0x15,0,flag))return false;r.pc=flag?0x7a6ae:0x7a69c;return true; // BTST.B #0,15(A6); BNE.W 7a6ae.
    // CMP.W 42(A6),D0; BLT.W 7a6aa (signed D0.W < 42.W) / BGT.W 7a6bc (signed D0.W > 42.W).
    case 0x7a69c:
        if(!on17_get(c,0x42,2,value))return false;r.pc=on17_signed_word(r.d[0])<on17_signed_word(value)?0x7a6aa:0x7a6a4;return true;
    case 0x7a6ae:
        if(!on17_get(c,0x42,2,value))return false;r.pc=on17_signed_word(r.d[0])>on17_signed_word(value)?0x7a6bc:0x7a6b6;return true;
    case 0x7a6a4:return on17_install(c,0,0x7a6ce,0x7a6aa);               // MOVE.L #7a6ce,(A6) (installed value outside the unit).
    case 0x7a6b6:return on17_install(c,0,0x7a6ce,0x7a6bc);
    case 0x7a6aa:r.pc=0x7a6bc;return true;                                 // BRA.W 7a6bc.
    case 0x7a6bc:return am_call(c,0x7b570,0x7a6c0);
    case 0x7a6c0:return on17_carry(c,0x7a6ca,0x7a6c4);                    // BCC.W 7a6ca (C returned by 7b570).
    case 0x7a6c4:return on17_install(c,0,0x7a964,0x7a6ca);               // MOVE.L #7a964,(A6) (installed value outside the unit).
    case 0x7a6ca:r.pc=0x7a388;return true;                                 // BRA.W 7a388.
    // ---- 7aa5e / 7aa66 (installed deletions): JMP 2a00.L / JMP 2a24.L.
    case 0x7aa5e:r.pc=0x2a00;return true;
    case 0x7aa66:r.pc=0x2a24;return true;
    // ---- 7aa6e (28ae child callback): MOVE.W #16b,20(A6); BTST.B #6,98(A6); BNE.W 7aa9a.
    case 0x7aa6e:if(!on17_put(c,0x20,2,0x16b) || !on17_bit(c,0x98,6,flag))return false;r.pc=flag?0x7aa9a:0x7aa7e;return true;
    case 0x7aa7e:case 0x7b06e:case 0x7b09e:return on17_sound(c,0xc48,r.pc+0xeU); // MOVE.W #c48,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0x7aa8c:am_word(r.d[0],0x38c);return am_call(c,0x4a496,0x7aa96); // MOVE.W #38c,D0; JSR 4a496.L.
    case 0x7aa96:r.pc=0x7aab2;return true;                                 // BRA.W 7aab2.
    case 0x7aa9a:case 0x7b090:return on17_sound(c,0x3c7,r.pc+0xeU);       // MOVE.W #3c7,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0x7aaa8:am_word(r.d[0],0x171);return am_call(c,0x4a496,0x7aab2); // MOVE.W #171,D0; JSR 4a496.L.
    case 0x7aab2:r.a[0]=0xcb5ee;return am_call(c,0x490ba,0x7aabe);       // LEA cb5ee.L,A0; JSR 490ba.L.
    case 0x7aabe:if(!on17_put(c,0x54,2,r.d[0]&65535U))return false;return am_call(c,0x7b786,0x7aac6); // MOVE.W D0,54(A6); JSR 7b786(PC).
    case 0x7aac6:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x49290,0x7aad0); // CLR.W D0; CLR.W D1; JSR 49290.L.
    case 0x7aad0:return on17_list(c,0x7c668,0x7aae0);
    case 0x7aae0:return on17_install(c,0,0x7aae6,0x7aae6);
    // ---- 7aae6 (installed): MOVEA.L c(A6),A0; MOVE.B 95(A0),D0; CMP.B 95(A6),D0; BEQ.W 7ab14.
    case 0x7aae6:
        if(!on17_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x95),1,value))return false;am_byte(r.d[0],value);
        if(!on17_get(c,0x95,1,other))return false;r.pc=(value&255U)==(other&255U)?0x7ab14:0x7aaf6;return true;
    // MOVE.B D0,95(A6); ANDI.W #f,D0; LEA 7bce0(PC),A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x7aaf6:
        if(!on17_put(c,0x95,1,r.d[0]&255U))return false;am_word(r.d[0],r.d[0]&15U);r.a[1]=0x7bce0;am_word(r.d[0],(r.d[0]*4U)&65535U);
        if(!am_read(c,am_index(r.a[1],r.d[0]&65535U),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);
        return am_call(c,0x49f8c,0x7ab14);
    case 0x7ab14:return am_call(c,0x43e34,0x7ab1a);                       // JSR 43e34.L.
    // MOVEA.L c(A6),A0; MOVE.B 98(A0),98(A6); MOVE.W 2c(A0),2c(A6); BTST.B #0,15(A0); BNE.W 7ab3e.
    case 0x7ab1a:
        if(!on17_get(c,0xc,4,value))return false;r.a[0]=value;
        if(!am_read(c,am_index(r.a[0],0x98),1,value) || !on17_put(c,0x98,1,value))return false;
        if(!am_read(c,am_index(r.a[0],0x2c),2,value) || !on17_put(c,0x2c,2,value))return false;
        if(!on17_bit_at(c,r.a[0],0x15,0,flag))return false;r.pc=flag?0x7ab3e:0x7ab34;return true;
    case 0x7ab34:if(!on17_bitop(c,0x15,0,false))return false;r.pc=0x7ab44;return true; // BCLR.B #0,15(A6); BRA.W 7ab44.
    case 0x7ab3e:if(!on17_bitop(c,0x15,0,true))return false;r.pc=0x7ab44;return true;  // BSET.B #0,15(A6).
    // MOVEA.L c(A6),A0; BTST.B #7,61(A0); BNE.W 7aba2.
    case 0x7ab4a:
        if(!on17_get(c,0xc,4,value))return false;r.a[0]=value;if(!on17_bit_at(c,r.a[0],0x61,7,flag))return false;
        r.pc=flag?0x7aba2:0x7ab58;return true;
    case 0x7ab58:case 0x7b200:return am_call(c,0x4b54e,r.pc+6U);           // JSR 4b54e.L.
    case 0x7ab5e:return on17_carry(c,0x7ab70,0x7ab62);                    // BCC.W 7ab70 (C returned by 4b54e).
    // CLR.B 5e(A6); BSET.B #1,98(A6); BRA.W 7ab76 / BCLR.B #1,98(A6).
    case 0x7ab62:if(!on17_put(c,0x5e,1,0) || !on17_bitop(c,0x98,1,true))return false;r.pc=0x7ab76;return true;
    case 0x7ab70:if(!on17_bitop(c,0x98,1,false))return false;r.pc=0x7ab76;return true;
    case 0x7ab76:if(!on17_bit(c,0x61,7,flag))return false;r.pc=flag?0x7ab80:0x7ab9e;return true; // BTST.B #7,61(A6); BEQ.W 7ab9e.
    // MOVEA.L c(A6),A0; MOVE.L #7a3b2,(A0) (installed into the parent node); JSR 49274.L.
    case 0x7ab80:
        if(!on17_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_write(c,r.a[0],4,0x7a3b2))return false;return am_call(c,0x49274,0x7ab90);
    case 0x7ab90:return on17_release(c,0x7ab9e);
    case 0x7ab9e:r.pc=0x7abb0;return true;                                 // BRA.W 7abb0.
    case 0x7aba2:return on17_release(c,0x7abb0);
    case 0x7abb0:return am_call(c,0x288c,0x7abb6);                        // JSR 288c.L.
    case 0x7abb6:return on17_carry(c,0x7abba,0x7abc0);                    // BCS.W 7abc0 (C returned by 288c).
    case 0x7abba:return on17_install(c,0,0x7aa66,0x7abc0);
    // ---- 7afa6 (helper): CLR.B 98(A6); MOVE.W 76(A6),D0; CMPI.W #2,D0; BLT.W 7afbc.
    case 0x7afa6:
        if(!on17_put(c,0x98,1,0) || !on17_get(c,0x76,2,value))return false;am_word(r.d[0],value);
        r.pc=on17_signed_word(value)<2?0x7afbc:0x7afb6;return true;
    case 0x7afb6:return am_call(c,0x49a58,0x7afbc);                       // JSR 49a58.L.
    case 0x7afbc:am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&65535U)!=0U?0x7afce:0x7afc4;return true; // ANDI.W #1,D0; BNE.W 7afce.
    case 0x7afc4:if(!on17_bitop(c,0x98,5,false))return false;r.pc=0x7afd4;return true; // BCLR.B #5,98(A6); BRA.W 7afd4.
    case 0x7afce:if(!on17_bitop(c,0x98,5,true))return false;r.pc=0x7afd4;return true;  // BSET.B #5,98(A6).
    // MOVE.W 78(A6),86(A6); TST.W 78(A6); BEQ.W 7afe8.
    case 0x7afd4:
        if(!on17_get(c,0x78,2,value) || !on17_put(c,0x86,2,value) || !on17_get(c,0x78,2,value))return false;
        r.pc=(value&65535U)==0U?0x7afe8:0x7afe2;return true;
    case 0x7afe2:if(!on17_bitop(c,0x98,0,true))return false;r.pc=0x7afe8;return true; // BSET.B #0,98(A6).
    // MOVE.W 7a(A6),D0; CMPI.W #0,D0; BEQ.W 7b004.
    case 0x7afe8:if(!on17_get(c,0x7a,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)==0U?0x7b004:0x7aff4;return true;
    // MOVE.W D0,88(A6); MOVE.W 7c(A6),8a(A6); BSET.B #6,98(A6).
    case 0x7aff4:
        if(!on17_put(c,0x88,2,r.d[0]&65535U) || !on17_get(c,0x7c,2,value) || !on17_put(c,0x8a,2,value) || !on17_bitop(c,0x98,6,true))return false;
        r.pc=0x7b004;return true;
    // CLR.W D0; MOVE.W D0,76/78/7a/7c(A6); RTS.
    case 0x7b004:
        am_word(r.d[0],0);
        for(std::uint32_t displacement=0x76;displacement<=0x7c;displacement+=2)if(!on17_put(c,displacement,2,0))return false;
        return am_return(c);
    // ---- 7b018 (helper): JSR 4c0ac.L; JSR 496c2.L; JSR 4be06.L; CMPI.W #100,42(A6); BGE.W 7b03a; BSET.B #0,15(A6).
    case 0x7b018:return am_call(c,0x4c0ac,0x7b01e);
    case 0x7b01e:return am_call(c,0x496c2,0x7b024);
    case 0x7b024:return am_call(c,0x4be06,0x7b02a);
    case 0x7b02a:if(!on17_get(c,0x42,2,value))return false;r.pc=on17_signed_word(value)>=0x100?0x7b03a:0x7b034;return true;
    case 0x7b034:if(!on17_bitop(c,0x15,0,true))return false;r.pc=0x7b03a;return true;
    case 0x7b03a:if(!on17_bit(c,0x98,6,flag))return false;r.pc=flag?0x7b090:0x7b044;return true; // BTST.B #6,98(A6); BNE.W 7b090.
    case 0x7b044:return am_call(c,0x497a6,0x7b04a);                       // JSR 497a6.L.
    case 0x7b04a:return on17_carry(c,0x7b04e,0x7b060);                    // BCS.W 7b060 (C returned by 497a6).
    case 0x7b04e:return on17_sound(c,0xc46,0x7b05c);
    case 0x7b05c:r.pc=0x7b06e;return true;                                 // BRA.W 7b06e.
    case 0x7b060:return on17_sound(c,0xc54,0x7b06e);
    // MOVE.B 19(A6),14(A6); MOVE.W #38c,D0 / #171,D0; JSR 4a496.L.
    case 0x7b07c:case 0x7b0ac:
        if(!on17_get(c,0x19,1,value) || !on17_put(c,0x14,1,value))return false;am_word(r.d[0],r.pc==0x7b07c?0x38cU:0x171U);
        return am_call(c,0x4a496,r.pc+0x10U);
    case 0x7b08c:r.pc=0x7b0bc;return true;                                 // BRA.W 7b0bc.
    // MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); CLR.B 96(A6); MOVE.W #1,54(A6); JSR 7b740(PC).
    case 0x7b0bc:
        if(!on17_put(c,0x68,2,0x8820) || !on17_put(c,0x1e,2,0x8820) || !on17_put(c,0x96,1,0) || !on17_put(c,0x54,2,1))return false;
        return am_call(c,0x7b740,0x7b0d6);
    case 0x7b0d6:r.a[0]=0x7aa6e;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x7b0e6); // MOVEA.L #7aa6e,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0x7b0e6:return on17_carry(c,0x7b0f8,0x7b0ea);                    // BCC.W 7b0f8 (C returned by 28ae).
    case 0x7b0ea:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0x7b0f4); // CLR.W D0; CLR.W D1; JSR 4970a.L.
    case 0x7b0f4:r.carry=AnimationCarrySet;r.pc=0x7b0f8;return true;       // ORI.B #1,CCR (Set).
    // MOVE.B 98(A6),98(A0); MOVE.L A0,7a(A6); LEA cb848.L,A0; JSR 490ba.L.
    case 0x7b0f8:
        if(!on17_get(c,0x98,1,value) || !am_write(c,am_index(r.a[0],0x98),1,value) || !on17_put(c,0x7a,4,r.a[0]))return false;
        r.a[0]=0xcb848;return am_call(c,0x490ba,0x7b10e);
    case 0x7b10e:if(!on17_put(c,0x82,2,r.d[0]&65535U))return false;return am_call(c,0xea5f0,0x7b118); // MOVE.W D0,82(A6); JSR ea5f0.L.
    // ---- 7b140 (helper): CLR.L 36(A6); CLR.L 3a(A6); JSR 4be34.L; BTST.B #7,15(A6); BEQ.W 7b162; JSR 4bfa4.L; BRA.W 7b17a.
    case 0x7b140:if(!on17_stop_motion(c))return false;return am_call(c,0x4be34,0x7b14e);
    case 0x7b14e:if(!on17_bit(c,0x15,7,flag))return false;r.pc=flag?0x7b158:0x7b162;return true;
    case 0x7b158:return am_call(c,0x4bfa4,0x7b15e);
    case 0x7b15e:r.pc=0x7b17a;return true;
    case 0x7b162:return am_call(c,0x4be2c,0x7b168);
    case 0x7b168:if(!on17_bit(c,0x15,7,flag))return false;r.pc=flag?0x7b172:0x7b17a;return true;
    case 0x7b172:if(!on17_stop_motion(c))return false;r.pc=0x7b17a;return true;
    // ---- 7b17c (helper): JSR 4be34.L; BTST.B #7,15(A6); BEQ.W 7b194; CLR.L 3a(A6); BRA.W 7b19c / ADDI.L #ffffb000,3a(A6); CLR.L 36(A6); RTS.
    case 0x7b17c:return am_call(c,0x4be34,0x7b182);
    case 0x7b182:if(!on17_bit(c,0x15,7,flag))return false;r.pc=flag?0x7b18c:0x7b194;return true;
    case 0x7b18c:if(!on17_put(c,0x3a,4,0))return false;r.pc=0x7b19c;return true;
    case 0x7b194:if(!on17_get(c,0x3a,4,value) || !on17_put(c,0x3a,4,value+0xffffb000U))return false;r.pc=0x7b19c;return true;
    case 0x7b19c:if(!on17_put(c,0x36,4,0))return false;return am_return(c);
    // ---- 7b1a2 (helper): LEA cb650.L,A0; JSR 490ba.L.
    case 0x7b1a2:r.a[0]=0xcb650;return am_call(c,0x490ba,0x7b1ae);
    // MOVE.W D0,D1; EXT.L D0; BTST.B #0,15(A6); BNE.W 7b1be; NEG.L D0.
    case 0x7b1ae:am_word(r.d[1],r.d[0]);r.d[0]=am_extend_word(r.d[0]);if(!on17_bit(c,0x15,0,flag))return false;r.pc=flag?0x7b1be:0x7b1bc;return true;
    case 0x7b1bc:r.d[0]=(0U-r.d[0])&0xffffffffU;r.pc=0x7b1be;return true;
    // LSL.L #8,D0; MOVE.L D0,64(A6); ANDI.W #700,D1; LSR.W #1,D1; TST.W D1; BNE.W 7b1d4; MOVE.W #80,D1.
    case 0x7b1be:
        r.d[0]=(r.d[0]<<8)&0xffffffffU;if(!on17_put(c,0x64,4,r.d[0]))return false;am_word(r.d[1],r.d[1]&0x700U);
        am_word(r.d[1],(r.d[1]&65535U)>>1);r.pc=(r.d[1]&65535U)!=0U?0x7b1d4:0x7b1d0;return true;
    case 0x7b1d0:am_word(r.d[1],0x80);r.pc=0x7b1d4;return true;
    case 0x7b1d4:if(!on17_put(c,0x2c,2,r.d[1]&65535U))return false;return am_return(c); // MOVE.W D1,2c(A6); RTS.
    // ---- 7b200 (C returned): JSR 4b54e.L (above); BCS.W 7b22e; BTST.B #1,98(A6); BNE.W 7b21c; ANDI.B #fe,CCR; BRA.W 7b22a.
    case 0x7b206:return on17_carry(c,0x7b20a,0x7b22e);                    // BCS.W 7b22e (C returned by 4b54e).
    case 0x7b20a:if(!on17_bit(c,0x98,1,flag))return false;r.pc=flag?0x7b21c:0x7b214;return true;
    case 0x7b214:r.carry=AnimationCarryClear;r.pc=0x7b22a;return true;
    // MOVEA.L 7a(A6),A0; MOVE.B 17(A0),17(A6); ORI.B #1,CCR.
    case 0x7b21c:
        if(!on17_get(c,0x7a,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x17),1,value) || !on17_put(c,0x17,1,value))return false;
        r.carry=AnimationCarrySet;r.pc=0x7b22a;return true;
    case 0x7b22a:r.pc=0x7b238;return true;                                 // BRA.W 7b238.
    // MOVE.B 5e(A6),8e(A6); ORI.B #1,CCR.
    case 0x7b22e:if(!on17_get(c,0x5e,1,value) || !on17_put(c,0x8e,1,value))return false;r.carry=AnimationCarrySet;r.pc=0x7b238;return true;
    // ---- 7b23a (C returned): TST.B 96(A6); BNE.W 7b25c; MOVEA.L 7a(A6),A0; BTST.B #1,98(A0); BEQ.W 7b25c.
    case 0x7b23a:if(!on17_get(c,0x96,1,value))return false;r.pc=(value&255U)!=0U?0x7b25c:0x7b242;return true;
    case 0x7b242:
        if(!on17_get(c,0x7a,4,value))return false;r.a[0]=value;if(!on17_bit_at(c,r.a[0],0x98,1,flag))return false;
        r.pc=flag?0x7b250:0x7b25c;return true;
    // ORI.B #1,CCR; BSET.B #1,98(A6); RTS / ANDI.B #fe,CCR; BCLR.B #1,98(A6); RTS.
    case 0x7b250:case 0x7b25c:
        if(!on17_bitop(c,0x98,1,r.pc==0x7b250))return false;r.carry=r.pc==0x7b250?AnimationCarrySet:AnimationCarryClear;return am_return(c);
    // ---- 7b268: MOVEA.L 7a(A6),A0; TST.L 56(A0); BEQ.W 7b282; LEA 7bc6c(PC),A0; JSR 4b82e.L; BRA.W 7b28c / LEA 0.W,A0; JSR 4b82e.L.
    case 0x7b268:
        if(!on17_get(c,0x7a,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x56),4,value))return false;
        r.pc=value==0U?0x7b282:0x7b274;return true;
    case 0x7b274:r.a[0]=0x7bc6c;return am_call(c,0x4b82e,0x7b27e);
    case 0x7b27e:r.pc=0x7b28c;return true;
    case 0x7b282:r.a[0]=0;return am_call(c,0x4b82e,0x7b28c);
    // ---- 7b570 (C returned): BTST.B #7,15(A6); BNE.W 7b59e; ADDQ.B #1,90(A6); CMPI.B #6,90(A6); BLE.W 7b596.
    case 0x7b570:if(!on17_bit(c,0x15,7,flag))return false;r.pc=flag?0x7b59e:0x7b57a;return true;
    case 0x7b57a:
        if(!on17_get(c,0x90,1,value) || !on17_put(c,0x90,1,(value+1U)&255U) || !on17_get(c,0x90,1,value))return false;
        r.pc=on17_signed_byte(value)<=6?0x7b596:0x7b588;return true;
    // MOVE.B #6,90(A6); ORI.B #1,CCR; BRA.W 7b59a.
    case 0x7b588:if(!on17_put(c,0x90,1,6))return false;r.carry=AnimationCarrySet;r.pc=0x7b59a;return true;
    case 0x7b596:r.carry=AnimationCarryClear;r.pc=0x7b59a;return true;     // ANDI.B #fe,CCR.
    case 0x7b59a:r.pc=0x7b5a6;return true;                                 // BRA.W 7b5a6.
    case 0x7b59e:if(!on17_put(c,0x90,1,0))return false;r.carry=AnimationCarryClear;r.pc=0x7b5a6;return true; // CLR.B 90(A6); ANDI.B #fe,CCR.
    // ---- 7b740 7b74a 7b754 7b786 7b790 (interpreter table callbacks / helpers): MOVE.L #animation,56(A6); RTS.
    case 0x7b740:case 0x7b74a:case 0x7b754:case 0x7b786:case 0x7b790:
        value=r.pc==0x7b740?0x7b924U:r.pc==0x7b74a?0x7b99cU:r.pc==0x7b754?0x7ba14U:r.pc==0x7b786?0x7b960U:0x7b9d8U;
        if(!on17_put(c,0x56,4,value))return false;return am_return(c);
    // ---- 7b7ae (C returned): CMPI.W #ffc0,42(A6); BLT.W 7b7ce; CMPI.W #1c0,42(A6); BGT.W 7b7ce; LEA 7bca0(PC),A0; JSR 1ab02.L; RTS.
    case 0x7b7ae:if(!on17_get(c,0x42,2,value))return false;r.pc=on17_signed_word(value)<-0x40?0x7b7ce:0x7b7b8;return true;
    case 0x7b7b8:if(!on17_get(c,0x42,2,value))return false;r.pc=on17_signed_word(value)>0x1c0?0x7b7ce:0x7b7c2;return true;
    case 0x7b7c2:r.a[0]=0x7bca0;return am_call(c,0x1ab02,0x7b7cc);
    case 0x7b7ce:r.carry=AnimationCarrySet;return am_return(c);            // ORI.B #1,CCR; RTS.
    default:return am_error(c,"unsupported animation objects n17 PC");
    }
}
}
