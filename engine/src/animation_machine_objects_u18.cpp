#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code.
const std::uint32_t OU18_SLOT_ONE=0x109156;       // LEA 109156.L,A1 (46c68): fixed RAM slot, LONG 2e = target node.
const std::uint32_t OU18_SLOT_TWO=0x10b1d6;       // LEA 10b1d6.L,A1 (46cbe).
const std::uint32_t OU18_BANK_LEFT=0x2001a8;      // MOVE.L 2001a8.L,22(A6) / MOVEA.L 2001a8.L,A1 (b66d4; banked window, live bus).
const std::uint32_t OU18_BANK_RIGHT=0x2001ac;     // MOVE.L 2001ac.L,22(A6) / MOVEA.L 2001ac.L,A1 (b6710).
const std::uint32_t OU18_ANIMATION_INDEX=0xb7f54; // MOVEA.L #b7f54,A1: fixed ROM LONG table (live bus).
const std::uint32_t OU18_PALETTE_TABLE=0xb7f14;   // LEA b7f14(PC),A0: fixed ROM WORD table (live bus).
const std::uint32_t OU18_STATE_TABLE=0xea742;     // LEA ea742(PC),A1: fixed ROM LONG table (live bus).
const std::uint32_t OU18_TURN_TABLE=0xea752;      // LEA ea752(PC),A1: fixed ROM LONG table (live bus).
const std::uint32_t OU18_SEARCH_ENTRY=0x46c68;    // JSR 46c68.L (ea63c, ea668).
const std::uint32_t OU18_SEARCH_FOUND=0x46d12;    // ADDA.W #c,A7; ORI.B #1,CCR; RTS.
const std::uint32_t OU18_SEARCH_MISS=0x46d08;     // MOVEM.L (A7)+,D0-D1/A0; ANDI.B #fe,CCR; RTS.
const std::uint32_t OU18_TAIL=0xb76d2;            // shared tail (BRA.W b76d2 from b67ae, entered by b76c4 BCC).
const std::uint32_t OU18_CHILD_RETURN=0xea7f2;    // RTS of ea762.
const std::uint32_t OU18_DELETE=0xeaa54;          // JMP 2a00.L.
bool ou18_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou18_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool ou18_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u18 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #callback,(A6) then continue at next_pc.
bool ou18_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// BTST.B #bit,d16(base): true when the bit is set.
bool ou18_btst(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ou18_get(c,base,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET/BCLR #bit,d16(base) (BYTE read-modify-write; Z only); was_set receives the tested bit.
bool ou18_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool set_bit,bool& was_set) {
    std::uint32_t value=0;if(!ou18_get(c,base,displacement,1,value))return false;was_set=((value>>bit)&1U)!=0U;
    const std::uint32_t mask=1U<<bit;
    return ou18_put(c,base,displacement,1,(set_bit?(value|mask):(value&~mask))&255U);
}
// CMPI.W #k,d16(A6); BNE: true when the WORD differs.
bool ou18_word_differs(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t k,bool& differs) {
    std::uint32_t value=0;if(!ou18_get(c,c.s.a[6],displacement,2,value))return false;differs=value!=k;return true;
}
// 46c9e/46ce8: SUB.L 14(A1),D0; SUB.L 18(A1),D1; MOVEA.L A1,A0; SWAP D0; SWAP D1; BSR.W 447be.
bool ou18_offset(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t x=0,y=0;
    if(!ou18_get(c,r.a[1],0x14,4,x) || !ou18_get(c,r.a[1],0x18,4,y))return false;
    r.d[0]=(r.d[0]-x)&0xffffffffU;r.d[1]=(r.d[1]-y)&0xffffffffU;r.a[0]=r.a[1];am_swap(r.d[0]);am_swap(r.d[1]);
    return am_call(c,0x447be,return_pc);
}
// 46cb0/46cfa: SWAP D1; SWAP D0; SWAP D7; CMP.W 54d8(A5),D7; BEQ.W 46d12.
bool ou18_compare(AnimationMachineContext& c,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    am_swap(r.d[1]);am_swap(r.d[0]);am_swap(r.d[7]);if(!ou18_get(c,r.a[5],0x54d8,2,value))return false;
    r.pc=(r.d[7]&65535U)==value?OU18_SEARCH_FOUND:next_pc;return true;
}
// 46c68/46cbe tail: LEA slot,A1; MOVEA.L 2e(A1),A2; CMPA.W #0,A2; BEQ.W miss_pc.
bool ou18_slot(AnimationMachineContext& c,std::uint32_t slot,std::uint32_t miss_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[1]=slot;if(!ou18_get(c,r.a[1],0x2e,4,value))return false;r.a[2]=value;r.pc=value==0U?miss_pc:next_pc;return true;
}
// 46c96/46ce0: ADD.L 14(A0),D0; ADD.L 18(A0),D1.
bool ou18_add_origin(AnimationMachineContext& c,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t x=0,y=0;
    if(!ou18_get(c,r.a[0],0x14,4,x) || !ou18_get(c,r.a[0],0x18,4,y))return false;
    r.d[0]=(r.d[0]+x)&0xffffffffU;r.d[1]=(r.d[1]+y)&0xffffffffU;r.pc=next_pc;return true;
}
// b66d4/b6710: LEA 26(A6),A0; MOVE.W #anim,20(A6); MOVE.L bank.L,22(A6); MOVEA.L #b7f54,A1; ADD.W D0,D0; ADD.W D0,D0;
// MOVE.L (A1,D0.W),D0; MOVEA.L bank.L,A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
bool ou18_animation(AnimationMachineContext& c,std::uint32_t animation,std::uint32_t bank,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!ou18_put(c,r.a[6],0x20,2,animation) || !am_read(c,bank,4,value) || !ou18_put(c,r.a[6],0x22,4,value))return false;
    r.a[1]=OU18_ANIMATION_INDEX;am_word(r.d[0],(r.d[0]<<2)&65535U);
    if(!am_read(c,am_index(r.a[1],r.d[0]&65535U),4,value))return false;r.d[0]=value;
    if(!am_read(c,bank,4,value))return false;r.a[1]=value;am_word(r.d[0],(r.d[0]<<2)&65535U);
    if(!am_read(c,am_index(r.a[1],r.d[0]&65535U),4,value))return false;r.a[1]=value;
    am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// LEA table(PC),A1; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
bool ou18_state_animation(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[1]=table;if(!ou18_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],(value<<2)&65535U);
    if(!am_read(c,am_index(r.a[1],r.d[0]&65535U),4,value))return false;r.a[1]=value;
    am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #k,D0; MOVE.B #b,D1; JSR 8ebe.L.
bool ou18_palette(AnimationMachineContext& c,std::uint32_t k,std::uint32_t b,std::uint32_t return_pc) {
    am_word(c.s.d[0],k);am_byte(c.s.d[1],b);return am_call(c,0x8ebe,return_pc);
}
}
// Objects F4 U18 (158 block starts): the distance search 46c68 (two fixed slots 109156/10b1d6, U08 447be; returns C clear after
// MOVEM restore or C set after dropping the 12 saved bytes), 4be2c (ADDI.L into 3a(A6), then U08b 4be34), the object b631c family
// (b7bc2 setup, bank LONGs 2001a8/2001ac with the fixed table b7f54 for the interpreter 49f8c, installed callback b6764) with the
// shared tail b76a4/b76d2 (b7b4c, b7dd6 boundaries, hud 8cda, U01 1aa7e), the setup b7bc2/b7c42 (stage_event_ops 49a84, U08 1aa3a,
// U11 4be06, ea5e0, cleanup 8ff4, U02 8ebe with the fixed WORD table b7f14), the motion helpers b7cfa (U17 4bfa4 boundary, 4be2c,
// U12 492c8), b7e06 (fade_card 28ae child d1f68, 4970a boundary) and b7e5c (U01 4b54e tail), the child creation ea5e0 (U12 1abda,
// U13 ea60c/ea624), the search loop ea636/ea63c/ea65a (MOVEM.W D7 around 46c68, DBCS), ea762 (readiness 289e, cleanup 43e22) and
// the child callback ea7f4 with the installed callbacks ea824/ea82a/ea940 (stage_event_ops 288c, fixed tables ea742/ea752, stage
// area 49a58, interpreter 49fc6, fade_card 2a00). Boundaries without an executor here: 4970a, b7b4c, b7dd6 and the U17 callee 4bfa4.
// U18 writes no port and changes no bank.
bool animation_objects_u18_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool flag=false;
    switch(r.pc) {
    // ---- 46c68: MOVE.W D7,54d8(A5); MOVEM.L D0-D1/A0,-(A7); MOVEQ #0,D2; MOVEQ #0,D3; LEA 109156.L,A1; MOVEA.L 2e(A1),A2;
    // CMPA.W #0,A2; BEQ.W 46cbe.
    case 0x46c68:
        if(!ou18_put(c,r.a[5],0x54d8,2,r.d[7]&65535U) || !am_push(c,4,r.a[0]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;
        r.d[2]=0;r.d[3]=0;return ou18_slot(c,OU18_SLOT_ONE,0x46cbe,0x46c86);
    // TST.W 2(A2); BEQ.W 46cbe / 46d08.
    case 0x46c86:case 0x46cd0:
        if(!ou18_get(c,r.a[2],2,2,value))return false;
        r.pc=value==0U?(r.pc==0x46c86?0x46cbe:OU18_SEARCH_MISS):(r.pc==0x46c86?0x46c8e:0x46cd8);return true;
    // CMPA.W #0,A0; BEQ.W 46c9e / 46ce8.
    case 0x46c8e:r.pc=r.a[0]==0U?0x46c9e:0x46c96;return true;
    case 0x46cd8:r.pc=r.a[0]==0U?0x46ce8:0x46ce0;return true;
    case 0x46c96:return ou18_add_origin(c,0x46c9e);
    case 0x46ce0:return ou18_add_origin(c,0x46ce8);
    case 0x46c9e:return ou18_offset(c,0x46cb0);
    case 0x46ce8:return ou18_offset(c,0x46cfa);
    case 0x46cb0:return ou18_compare(c,0x46cbe);
    case 0x46cfa:return ou18_compare(c,OU18_SEARCH_MISS);
    // LEA 10b1d6.L,A1; MOVEA.L 2e(A1),A2; CMPA.W #0,A2; BEQ.W 46d08.
    case 0x46cbe:return ou18_slot(c,OU18_SLOT_TWO,OU18_SEARCH_MISS,0x46cd0);
    // MOVEM.L (A7)+,D0-D1/A0; ANDI.B #fe,CCR (C clear); RTS.
    case 0x46d08:
        if(!am_pop(c,4,r.d[0]) || !am_pop(c,4,r.d[1]) || !am_pop(c,4,r.a[0]))return false;
        r.carry=AnimationCarryClear;return am_return(c);
    // ADDA.W #c,A7; ORI.B #1,CCR (C set); RTS.
    case 0x46d12:r.a[7]=(r.a[7]+12U)&0xffffffffU;r.carry=AnimationCarrySet;return am_return(c);

    // ---- 4be2c: ADDI.L #ffffb000,3a(A6) (then U08b 4be34).
    case 0x4be2c:
        if(!ou18_get(c,r.a[6],0x3a,4,value) || !ou18_put(c,r.a[6],0x3a,4,(value+0xffffb000U)&0xffffffffU))return false;
        r.pc=0x4be34;return true;

    // ---- b631c (callback): MOVE.W #0,8e(A6); BSR.W b7bc2.
    case 0xb631c:if(!ou18_put(c,r.a[6],0x8e,2,0))return false;return am_call(c,0xb7bc2,0xb6326);
    case 0xb6326:r.pc=0xb66c8;return true;                                   // BRA.W b66c8.
    // MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b6710.
    case 0xb66c8:if(!ou18_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[0],value);r.pc=value!=0U?0xb6710:0xb66d4;return true;
    case 0xb66d4:return ou18_animation(c,0x1b3,OU18_BANK_LEFT,0xb670c);
    case 0xb670c:r.pc=0xb6748;return true;                                   // BRA.W b6748.
    case 0xb6710:return ou18_animation(c,0x1bb,OU18_BANK_RIGHT,0xb6748);
    // MOVE.L #fffffff2,96(A6); MOVE.L #1e,98(A6); MOVE.B #5,9c(A6); MOVE.L #b6764,(A6).
    case 0xb6748:
        if(!ou18_put(c,r.a[6],0x96,4,0xfffffff2U) || !ou18_put(c,r.a[6],0x98,4,0x1e) || !ou18_put(c,r.a[6],0x9c,1,5))return false;
        return ou18_install(c,0xb6764,0xb6764);
    case 0xb6764:return am_call(c,0xb7cfa,0xb6768);                          // (installed callback) JSR b7cfa(PC).
    case 0xb6768:return am_call(c,0x49fc6,0xb676e);                          // JSR 49fc6.L.
    // LEA 26(A6),A0; TST.W 4(A0); BNE.W b67a0.
    case 0xb676e:
        r.a[0]=am_index(r.a[6],0x26);if(!ou18_get(c,r.a[0],4,2,value))return false;r.pc=value!=0U?0xb67a0:0xb677a;return true;
    // SUBQ.B #1,9c(A6); BNE.W b67a0.
    case 0xb677a:
        if(!ou18_get(c,r.a[6],0x9c,1,value))return false;value=(value-1U)&255U;if(!ou18_put(c,r.a[6],0x9c,1,value))return false;
        r.pc=value!=0U?0xb67a0:0xb6782;return true;
    // MOVE.L #fffffff6,96(A6); MOVE.L #1c,98(A6); LEA 26(A6),A0; JSR b7e06(PC).
    case 0xb6782:
        if(!ou18_put(c,r.a[6],0x96,4,0xfffffff6U) || !ou18_put(c,r.a[6],0x98,4,0x1c))return false;
        r.a[0]=am_index(r.a[6],0x26);return am_call(c,0xb7e06,0xb679a);
    case 0xb679a:if(!ou18_put(c,r.a[6],0x9c,1,0xf))return false;r.pc=0xb67a0;return true; // MOVE.B #f,9c(A6).
    case 0xb67a0:return am_call(c,0xb7e5c,0xb67a4);                          // JSR b7e5c(PC).
    case 0xb67a4:return ou18_consume(c,false,0xb67ae,0xb67a8);               // BCC.W b67ae (C returned by b7e5c).
    case 0xb67a8:return ou18_install(c,0xb67b2,0xb67ae);                     // MOVE.L #b67b2,(A6).
    case 0xb67ae:r.pc=OU18_TAIL;return true;                                 // BRA.W b76d2.

    // ---- b76a4 (installed callback): BSR.W b7cfa.
    case 0xb76a4:return am_call(c,0xb7cfa,0xb76a8);
    case 0xb76a8:return am_call(c,0x49fc6,0xb76ae);                          // JSR 49fc6.L.
    case 0xb76ae:return ou18_consume(c,false,0xb76b8,0xb76b2);               // BCC.W b76b8 (C returned by 49fc6).
    case 0xb76b2:return ou18_install(c,0xb68be,0xb76b8);                     // MOVE.L #b68be,(A6).
    case 0xb76b8:r.pc=0xb76bc;return true;                                   // BRA.W b76bc.
    case 0xb76bc:r.a[1]=0xb7efc;return am_call(c,0xb7b4c,0xb76c4);           // LEA b7efc(PC),A1; BSR.W b7b4c (boundary).
    case 0xb76c4:return ou18_consume(c,false,OU18_TAIL,0xb76c8);             // BCC.W b76d2 (C returned by b7b4c).
    // MOVE.B D0,9d(A6); MOVE.L #b6ba0,(A6).
    case 0xb76c8:if(!ou18_put(c,r.a[6],0x9d,1,r.d[0]&255U))return false;return ou18_install(c,0xb6ba0,OU18_TAIL);
    // BTST.B #1,9f(A6); BEQ.W b76e0.
    case 0xb76d2:if(!ou18_btst(c,r.a[6],0x9f,1,flag))return false;r.pc=flag?0xb76dc:0xb76e0;return true;
    case 0xb76dc:return am_call(c,0xb7dd6,0xb76e0);                          // JSR b7dd6(PC) (boundary).
    // BTST.B #0,9f(A6); BEQ.W b772c.
    case 0xb76e0:if(!ou18_btst(c,r.a[6],0x9f,0,flag))return false;r.pc=flag?0xb76ea:0xb772c;return true;
    // MOVE.W 92(A6),D0; ADD.W D0,94(A6); TST.W D0; BMI.W b770c.
    case 0xb76ea:
        if(!ou18_get(c,r.a[6],0x92,2,value))return false;am_word(r.d[0],value);
        if(!ou18_get(c,r.a[6],0x94,2,other) || !ou18_put(c,r.a[6],0x94,2,(other+value)&65535U))return false;
        r.pc=(value&0x8000U)!=0U?0xb770c:0xb76f8;return true;
    // CMPI.W #2000,94(A6); BCS.W b7708.
    case 0xb76f8:if(!ou18_get(c,r.a[6],0x94,2,value))return false;r.pc=value<0x2000U?0xb7708:0xb7702;return true;
    case 0xb7702:if(!ou18_put(c,r.a[6],0x94,2,0x2000))return false;r.pc=0xb7708;return true; // MOVE.W #2000,94(A6).
    case 0xb7708:r.pc=0xb771a;return true;                                   // BRA.W b771a.
    // TST.W 94(A6); BPL.W b771a.
    case 0xb770c:if(!ou18_get(c,r.a[6],0x94,2,value))return false;r.pc=(value&0x8000U)==0U?0xb771a:0xb7714;return true;
    case 0xb7714:if(!ou18_put(c,r.a[6],0x94,2,0))return false;r.pc=0xb771a;return true; // MOVE.W #0,94(A6).
    // MOVE.B 19(A6),D0; MOVE.W 90(A6),D1; MOVE.B 94(A6),D2; JSR 8cda.L.
    case 0xb771a:
        if(!ou18_get(c,r.a[6],0x19,1,value))return false;am_byte(r.d[0],value);
        if(!ou18_get(c,r.a[6],0x90,2,value))return false;am_word(r.d[1],value);
        if(!ou18_get(c,r.a[6],0x94,1,value))return false;am_byte(r.d[2],value);return am_call(c,0x8cda,0xb772c);
    case 0xb772c:r.a[0]=0xb7eec;return am_call(c,0x1aa7e,0xb7736);           // LEA b7eec(PC),A0; JSR 1aa7e.L.
    case 0xb7736:return ou18_consume(c,false,0xb7740,0xb773a);               // BCC.W b7740 (C returned by 1aa7e).
    case 0xb773a:return ou18_install(c,0xb7742,0xb7740);                     // MOVE.L #b7742,(A6).
    case 0xb7740:case 0xb7c40:case 0xb7d2c:case 0xea658:case 0xea660:case 0xea7f2:case 0xea9fe:return am_return(c); // RTS (keeps C).

    // ---- b7bc2: CMPI.W #0,7a(A6); BNE.W b7bd2.
    case 0xb7bc2:if(!ou18_word_differs(c,0x7a,0,flag))return false;r.pc=flag?0xb7bd2:0xb7bcc;return true;
    case 0xb7bcc:if(!ou18_bit(c,r.a[6],0x15,0,true,flag))return false;r.pc=0xb7bd2;return true;  // BSET.B #0,15(A6).
    // CMPI.W #3,76(A6); BNE.W b7bea.
    case 0xb7bd2:if(!ou18_word_differs(c,0x76,3,flag))return false;r.pc=flag?0xb7bea:0xb7bdc;return true;
    case 0xb7bdc:am_word(r.d[0],3);return am_call(c,0x49a84,0xb7be6);        // MOVE.W #3,D0; JSR 49a84.L.
    case 0xb7be6:if(!ou18_put(c,r.a[6],0x76,2,r.d[0]&65535U))return false;r.pc=0xb7bea;return true; // MOVE.W D0,76(A6).
    // CMPI.W #1,80(A6); BNE.W b7bfa.
    case 0xb7bea:if(!ou18_word_differs(c,0x80,1,flag))return false;r.pc=flag?0xb7bfa:0xb7bf4;return true;
    case 0xb7bf4:if(!ou18_bit(c,r.a[6],0x15,3,true,flag))return false;r.pc=0xb7bfa;return true;  // BSET.B #3,15(A6).
    // MOVE.W #2,8c(A6); CMPI.W #0,8e(A6); BNE.W b7c1e.
    case 0xb7bfa:
        if(!ou18_put(c,r.a[6],0x8c,2,2) || !ou18_word_differs(c,0x8e,0,flag))return false;r.pc=flag?0xb7c1e:0xb7c0a;return true;
    case 0xb7c0a:return am_call(c,0x1aa3a,0xb7c10);                          // JSR 1aa3a.L.
    case 0xb7c10:r.pc=((r.d[0]>>3)&1U)!=0U?0xb7c18:0xb7c1e;return true;    // BTST.B #3,D0; BEQ.W b7c1e.
    case 0xb7c18:if(!ou18_bit(c,r.a[6],0x9f,1,true,flag))return false;r.pc=0xb7c1e;return true;  // BSET.B #1,9f(A6).
    case 0xb7c1e:return am_call(c,0x4be06,0xb7c24);                          // JSR 4be06.L.
    // MOVE.W #40,92(A6); MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); JSR ea5e0.L.
    case 0xb7c24:
        if(!ou18_put(c,r.a[6],0x92,2,0x40) || !ou18_put(c,r.a[6],0x68,2,0x8820) || !ou18_put(c,r.a[6],0x1e,2,0x8820))return false;
        return am_call(c,0xea5e0,0xb7c3c);
    case 0xb7c3c:return am_call(c,0xb7c42,0xb7c40);                          // JSR b7c42(PC).
    case 0xb7c42:return am_call(c,0x8ff4,0xb7c48);                           // JSR 8ff4.L.
    // BTST.B #1,9f(A6); BNE.W b7c6e.
    case 0xb7c48:if(!ou18_btst(c,r.a[6],0x9f,1,flag))return false;r.pc=flag?0xb7c6e:0xb7c52;return true;
    // MOVE.W 8e(A6),D0; LEA b7f14(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xb7c52:
        if(!ou18_get(c,r.a[6],0x8e,2,value))return false;r.a[0]=OU18_PALETTE_TABLE;am_word(r.d[0],(value<<1)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[0]&65535U),2,value))return false;return ou18_palette(c,value,0,0xb7c6a);
    case 0xb7c6a:r.pc=0xb7c88;return true;                                   // BRA.W b7c88.
    case 0xb7c6e:return ou18_palette(c,0xac3,1,0xb7c7c);                     // MOVE.W #ac3,D0; MOVE.B #1,D1; JSR 8ebe.L.
    // MOVE.W #ac4,90(A6); BSET.B #0,9f(A6).
    case 0xb7c7c:
        if(!ou18_put(c,r.a[6],0x90,2,0xac4) || !ou18_bit(c,r.a[6],0x9f,0,true,flag))return false;r.pc=0xb7c88;return true;
    case 0xb7c88:return ou18_palette(c,0xd88,0,0xb7c96);                     // MOVE.W #d88,D0; MOVE.B #0,D1; JSR 8ebe.L.
    // MOVE.B 19(A6),14(A6); RTS.
    case 0xb7c96:if(!ou18_get(c,r.a[6],0x19,1,value) || !ou18_put(c,r.a[6],0x14,1,value))return false;return am_return(c);

    // ---- b7cfa: BTST.B #7,15(A6); BEQ.W b7d0e.
    case 0xb7cfa:if(!ou18_btst(c,r.a[6],0x15,7,flag))return false;r.pc=flag?0xb7d04:0xb7d0e;return true;
    case 0xb7d04:return am_call(c,0x4bfa4,0xb7d0a);                          // JSR 4bfa4.L (U17 boundary).
    case 0xb7d0a:r.pc=0xb7d2c;return true;                                   // BRA.W b7d2c.
    case 0xb7d0e:return am_call(c,0x4be2c,0xb7d14);                          // JSR 4be2c.L.
    case 0xb7d14:return am_call(c,0x492c8,0xb7d1a);                          // JSR 492c8.L.
    // BTST.B #7,15(A6); BEQ.W b7d2c.
    case 0xb7d1a:if(!ou18_btst(c,r.a[6],0x15,7,flag))return false;r.pc=flag?0xb7d24:0xb7d2c;return true;
    // CLR.L 36(A6); CLR.L 3a(A6).
    case 0xb7d24:if(!ou18_put(c,r.a[6],0x36,4,0) || !ou18_put(c,r.a[6],0x3a,4,0))return false;r.pc=0xb7d2c;return true;

    // ---- b7e06: BTST.B #1,9f(A6); BEQ.W b7e56.
    case 0xb7e06:if(!ou18_btst(c,r.a[6],0x9f,1,flag))return false;r.pc=flag?0xb7e10:0xb7e56;return true;
    // MOVEA.L #d1f68,A0; MOVE.W #1e,D0; JSR 28ae.L.
    case 0xb7e10:r.a[0]=0xd1f68;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0xb7e20);
    case 0xb7e20:return ou18_consume(c,false,0xb7e32,0xb7e24);               // BCC.W b7e32 (C returned by 28ae).
    case 0xb7e24:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0xb7e2e); // CLR.W D0; CLR.W D1; JSR 4970a.L (boundary).
    case 0xb7e2e:r.pc=0xb7e32;return true;  // ORI.B #1,CCR (overwritten by the b7e32 MOVE.W before any consumer: Unknown).
    // MOVE.W 96(A6),D0; MOVE.W 98(A6),D1; BTST.B #0,15(A6); BEQ.W b7e46.
    case 0xb7e32:
        if(!ou18_get(c,r.a[6],0x96,2,value))return false;am_word(r.d[0],value);
        if(!ou18_get(c,r.a[6],0x98,2,value))return false;am_word(r.d[1],value);
        if(!ou18_btst(c,r.a[6],0x15,0,flag))return false;r.pc=flag?0xb7e44:0xb7e46;return true;
    case 0xb7e44:am_word(r.d[0],(0U-(r.d[0]&65535U))&65535U);r.pc=0xb7e46;return true; // NEG.W D0.
    // ADD.W D0,2e(A0); ADD.W D1,32(A0); MOVE.W #0,9a(A6); RTS.
    case 0xb7e46:
        if(!ou18_get(c,r.a[0],0x2e,2,value) || !ou18_put(c,r.a[0],0x2e,2,(value+r.d[0])&65535U))return false;
        if(!ou18_get(c,r.a[0],0x32,2,value) || !ou18_put(c,r.a[0],0x32,2,(value+r.d[1])&65535U))return false;
        if(!ou18_put(c,r.a[6],0x9a,2,0))return false;return am_return(c);
    case 0xb7e56:return am_return(c);  // ANDI.B #fe,CCR; RTS (no caller consumes this C: Unknown).
    // TST.W 8c(A6); BEQ.W b7e6e.
    case 0xb7e5c:if(!ou18_get(c,r.a[6],0x8c,2,value))return false;r.pc=value==0U?0xb7e6e:0xb7e64;return true;
    // SUBQ.W #1,8c(A6); ANDI.B #fe,CCR (C clear); RTS.
    case 0xb7e64:
        if(!ou18_get(c,r.a[6],0x8c,2,value) || !ou18_put(c,r.a[6],0x8c,2,(value-1U)&65535U))return false;
        r.carry=AnimationCarryClear;return am_return(c);
    case 0xb7e6e:r.pc=0x4b54e;return true;                                   // JMP 4b54e.L.

    // ---- ea5e0: JSR 1abda.L.
    case 0xea5e0:return am_call(c,0x1abda,0xea5e6);
    case 0xea5e6:return ou18_consume(c,false,0xea624,0xea5ea);               // BCC.W ea624 (C returned by 1abda).
    case 0xea5ea:r.d[2]=1;r.pc=0xea60c;return true;                          // MOVEQ #1,D2; BRA.W ea60c.

    // ---- ea636: SUBI.L #90000,D1.
    case 0xea636:r.d[1]=(r.d[1]-0x90000U)&0xffffffffU;r.pc=0xea63c;return true;
    // MOVEM.W D7,-(A7); ADDI.L #80000,D1; MOVE.W #4,D7; JSR 46c68.L.
    case 0xea63c:
        if(!am_push(c,2,r.d[7]&65535U))return false;r.d[1]=(r.d[1]+0x80000U)&0xffffffffU;am_word(r.d[7],4);
        return am_call(c,OU18_SEARCH_ENTRY,0xea650);
    // MOVEM.W (A7)+,D7 (sign-extended to the LONG); DBCS D7,ea63c (C returned by 46c68).
    case 0xea650:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u18 caller requires known carry");
        if(!am_pop(c,2,value))return false;r.d[7]=am_extend_word(value);
        if(r.carry==AnimationCarrySet){r.pc=0xea658;return true;}
        am_word(r.d[7],(r.d[7]-1U)&65535U);r.pc=(r.d[7]&65535U)!=65535U?0xea63c:0xea658;return true;
    case 0xea65a:return am_call(c,0xea636,0xea65c);                          // BSR.B ea636.
    case 0xea65c:return ou18_consume(c,true,0xea662,0xea660);                // BCS.W ea662 (C returned by ea636).
    case 0xea662:r.d[1]&=0xfff80000U;r.pc=0xea668;return true;              // ANDI.L #fff80000,D1.
    // ADDI.L #80000,D1; MOVE.W #4,D7; JSR 46c68.L.
    case 0xea668:r.d[1]=(r.d[1]+0x80000U)&0xffffffffU;am_word(r.d[7],4);return am_call(c,OU18_SEARCH_ENTRY,0xea678);
    case 0xea678:return ou18_consume(c,true,0xea668,0xea67a);                // BCS.B ea668 (C returned by 46c68).
    case 0xea67a:r.carry=AnimationCarrySet;return am_return(c);             // ORI.B #1,CCR (C set); RTS.

    // ---- ea762: CLR.B 78(A6); MOVEA.L c(A6),A0; JSR 289e.L.
    case 0xea762:
        if(!ou18_put(c,r.a[6],0x78,1,0) || !ou18_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;return am_call(c,0x289e,0xea770);
    case 0xea770:return ou18_consume(c,false,OU18_CHILD_RETURN,0xea774);     // BCC.W ea7f2 (C returned by 289e).
    // MOVE.W 1e(A0),1e(A6); MOVE.L 42(A0),D0; MOVE.L 46(A0),D1; LEA 538e(A5),A0; SUB.L 14(A0),D0; SUB.L 18(A0),D1; BSR.W ea65a.
    case 0xea774:
        if(!ou18_get(c,r.a[0],0x1e,2,value) || !ou18_put(c,r.a[6],0x1e,2,value))return false;
        if(!ou18_get(c,r.a[0],0x42,4,r.d[0]) || !ou18_get(c,r.a[0],0x46,4,r.d[1]))return false;
        r.a[0]=am_index(r.a[5],0x538e);if(!ou18_get(c,r.a[0],0x14,4,value) || !ou18_get(c,r.a[0],0x18,4,other))return false;
        r.d[0]=(r.d[0]-value)&0xffffffffU;r.d[1]=(r.d[1]-other)&0xffffffffU;return am_call(c,0xea65a,0xea792);
    // SCS.B 78(A6); BCS.W ea7aa (C returned by ea65a).
    case 0xea792:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u18 caller requires known carry");
        if(!ou18_put(c,r.a[6],0x78,1,r.carry==AnimationCarrySet?0xffU:0U))return false;
        r.pc=r.carry==AnimationCarrySet?0xea7aa:0xea79a;return true;
    // MOVE.L 42(A6),D0; MOVE.L 46(A6),D1; SUB.L 14(A0),D0; SUB.L 18(A0),D1.
    case 0xea79a:
        if(!ou18_get(c,r.a[6],0x42,4,r.d[0]) || !ou18_get(c,r.a[6],0x46,4,r.d[1]))return false;
        if(!ou18_get(c,r.a[0],0x14,4,value) || !ou18_get(c,r.a[0],0x18,4,other))return false;
        r.d[0]=(r.d[0]-value)&0xffffffffU;r.d[1]=(r.d[1]-other)&0xffffffffU;r.pc=0xea7aa;return true;
    case 0xea7aa:r.a[1]=r.a[0];r.a[0]=am_index(r.a[6],0x2e);return am_call(c,0x43e22,0xea7b6); // MOVEA.L A0,A1; LEA 2e(A6),A0; JSR 43e22.L.
    // MOVE.B #ff,D1; MOVEA.L c(A6),A0; BTST.B #7,15(A0); BEQ.W ea7ee.
    case 0xea7b6:
        am_byte(r.d[1],0xff);if(!ou18_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ou18_btst(c,r.a[0],0x15,7,flag))return false;r.pc=flag?0xea7c8:0xea7ee;return true;
    // MOVE.L 46(A6),D0; SUB.L 46(A0),D0; BLE.W ea7ee (signed LONG 46(A6) <= 46(A0)).
    case 0xea7c8:
        if(!ou18_get(c,r.a[6],0x46,4,value) || !ou18_get(c,r.a[0],0x46,4,other))return false;
        r.d[0]=(value-other)&0xffffffffU;r.pc=(value^0x80000000U)<=(other^0x80000000U)?0xea7ee:0xea7d4;return true;
    // ADDI.L #20000,D0; SUBI.L #a0000,D0; BCC.W ea7ee (no borrow).
    case 0xea7d4:
        value=(r.d[0]+0x20000U)&0xffffffffU;r.d[0]=(value-0xa0000U)&0xffffffffU;r.pc=value>=0xa0000U?0xea7ee:0xea7e4;return true;
    // LSL.L #4,D0; SWAP D0; MOVE.W D0,D1; ADDI.W #100,D0.
    case 0xea7e4:
        r.d[0]=(r.d[0]<<4)&0xffffffffU;am_swap(r.d[0]);am_word(r.d[1],r.d[0]);am_word(r.d[0],(r.d[0]+0x100U)&65535U);r.pc=0xea7ee;return true;
    case 0xea7ee:if(!ou18_put(c,r.a[6],0x12,1,r.d[1]&255U))return false;r.pc=OU18_CHILD_RETURN;return true; // MOVE.B D1,12(A6).

    // ---- ea7f4 (child callback): MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); JSR 288c.L.
    case 0xea7f4:
        if(!ou18_put(c,r.a[6],0x68,2,0x1001) || !ou18_put(c,r.a[6],0x1e,2,0x1001))return false;return am_call(c,0x288c,0xea806);
    case 0xea806:return ou18_consume(c,false,OU18_DELETE,0xea80a);           // BCC.W eaa54 (C returned by 288c).
    // MOVE.W #e2,20(A6); BCLR.B #1,15(A6); MOVEQ #2,D7; BSR.W ea762.
    case 0xea80a:
        if(!ou18_put(c,r.a[6],0x20,2,0xe2) || !ou18_bit(c,r.a[6],0x15,1,false,flag))return false;r.d[7]=2;return am_call(c,0xea762,0xea81c);
    // TST.B 78(A6); BNE.W ea908.
    case 0xea81c:if(!ou18_get(c,r.a[6],0x78,1,value))return false;r.pc=value!=0U?0xea908:0xea824;return true;
    case 0xea824:return ou18_install(c,0xea82a,0xea82a);                     // MOVE.L #ea82a,(A6).
    case 0xea82a:case 0xea940:return am_call(c,0x288c,r.pc==0xea82a?0xea830:0xea946); // (installed callback) JSR 288c.L.
    case 0xea830:return ou18_consume(c,false,OU18_DELETE,0xea834);           // BCC.W eaa54 (C returned by 288c).
    case 0xea834:r.d[7]=2;return am_call(c,0xea762,0xea83a);                 // MOVEQ #2,D7; BSR.W ea762.
    // BCLR.B #7,5e51(A5); BNE.W ea852.
    case 0xea83a:if(!ou18_bit(c,r.a[5],0x5e51,7,false,flag))return false;r.pc=flag?0xea852:0xea844;return true;
    // TST.B 78(A6); BEQ.W ea852.
    case 0xea844:if(!ou18_get(c,r.a[6],0x78,1,value))return false;r.pc=value==0U?0xea852:0xea84c;return true;
    case 0xea84c:return ou18_install(c,0xea85a,0xea852);                     // MOVE.L #ea85a,(A6).
    case 0xea852:if(!ou18_bit(c,r.a[5],0x5e50,7,false,flag))return false;return am_return(c); // BCLR.B #7,5e50(A5); RTS.

    // ---- ea908: JSR 8ff4.L; JSR 1abda.L; MOVEQ #0,D1; JSR 8ebe.L.
    case 0xea908:return am_call(c,0x8ff4,0xea90e);
    case 0xea90e:return am_call(c,0x1abda,0xea914);
    case 0xea914:r.d[1]=0;return am_call(c,0x8ebe,0xea91c);
    // CLR.L 36(A6); LEA ea742(PC),A1; ... JSR 49f8c.L.
    case 0xea91c:if(!ou18_put(c,r.a[6],0x36,4,0))return false;return ou18_state_animation(c,OU18_STATE_TABLE,0xea93a);
    case 0xea93a:return ou18_install(c,0xea940,0xea940);                     // MOVE.L #ea940,(A6).
    case 0xea946:return ou18_consume(c,false,OU18_DELETE,0xea94a);           // BCC.W eaa54 (C returned by 288c).
    // BCLR.B #7,5e51(A5); BNE.W ea824.
    case 0xea94a:if(!ou18_bit(c,r.a[5],0x5e51,7,false,flag))return false;r.pc=flag?0xea824:0xea954;return true;
    case 0xea954:r.d[7]=8;return am_call(c,0xea762,0xea95a);                 // MOVEQ #8,D7; BSR.W ea762.
    // MOVEA.L c(A6),A0; TST.L 36(A6); SNE.B D0; EXT.W D0; MOVE.L 36(A0),36(A6); SNE.B D0; CMPI.W #ff,D0; BNE.W ea9a8.
    case 0xea95a:
        if(!ou18_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ou18_get(c,r.a[6],0x36,4,value))return false;am_word(r.d[0],value!=0U?0xffffU:0U);
        if(!ou18_get(c,r.a[0],0x36,4,value) || !ou18_put(c,r.a[6],0x36,4,value))return false;am_byte(r.d[0],value!=0U?0xffU:0U);
        r.pc=(r.d[0]&65535U)!=0xffU?0xea9a8:0xea976;return true;
    case 0xea976:return ou18_state_animation(c,OU18_TURN_TABLE,0xea990);
    // BCLR.B #0,15(A6); TST.L 36(A6); BPL.W ea9a4.
    case 0xea990:
        if(!ou18_bit(c,r.a[6],0x15,0,false,flag) || !ou18_get(c,r.a[6],0x36,4,value))return false;
        r.pc=(value&0x80000000U)==0U?0xea9a4:0xea99e;return true;
    case 0xea99e:if(!ou18_bit(c,r.a[6],0x15,0,true,flag))return false;r.pc=0xea9a4;return true;  // BSET.B #0,15(A6).
    case 0xea9a4:r.pc=0xea9ca;return true;                                   // BRA.W ea9ca.
    case 0xea9a8:r.pc=(r.d[0]&65535U)!=0xff00U?0xea9ca:0xea9b0;return true; // CMPI.W #ff00,D0; BNE.W ea9ca.
    case 0xea9b0:return ou18_state_animation(c,OU18_STATE_TABLE,0xea9ca);
    case 0xea9ca:return am_call(c,0x49a58,0xea9d0);                          // JSR 49a58.L.
    // ANDI.W #7f,D0; ADDI.W #40,D0; MOVE.W D0,2c(A6); TST.B 78(A6); BNE.W ea9ea.
    case 0xea9d0:
        am_word(r.d[0],((r.d[0]&0x7fU)+0x40U)&65535U);if(!ou18_put(c,r.a[6],0x2c,2,r.d[0]&65535U) || !ou18_get(c,r.a[6],0x78,1,value))return false;
        r.pc=value!=0U?0xea9ea:0xea9e4;return true;
    case 0xea9e4:return ou18_install(c,0xeaa00,0xea9ea);                     // MOVE.L #eaa00,(A6).
    // ANDI.B #fe,CCR (no consumer: Unknown); BCLR.B #7,5e50(A5); BNE.W ea9fe.
    case 0xea9ea:if(!ou18_bit(c,r.a[5],0x5e50,7,false,flag))return false;r.pc=flag?0xea9fe:0xea9f8;return true;
    case 0xea9f8:return am_call(c,0x49fc6,0xea9fe);                          // JSR 49fc6.L.
    case 0xeaa54:r.pc=0x2a00;return true;                                    // JMP 2a00.L.
    default:return am_error(c,"unsupported animation objects u18 PC");
    }
}
}
