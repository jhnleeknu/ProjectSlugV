#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t ON01_BANK_B8=0x2000b8;        // MOVE.L 2000b8.L,22(A6) / MOVEA.L 2000b8.L,A1 (e5c74 family; banked window LONG, live bus).
const std::uint32_t ON01_BANK_C8=0x2000c8;        // MOVE.L 2000c8.L,22(A6) / MOVEA.L 2000c8.L,A1 (e5bb0 and e5d72/e5d86 families).
const std::uint32_t ON01_BANK_E0=0x2001e0;        // MOVE.L 2001e0.L,22(A6) (5208a).
const std::uint32_t ON01_RECORDS=0x5205e;         // LEA 5205e(PC,D0.W),A0 (fixed ROM records: WORD, WORD, LONG).
const std::uint32_t ON01_PALETTES=0x5206e;        // LEA 5206e(PC),A0 (fixed ROM WORD table, ffff ends).
const std::uint32_t ON01_PICK_D86=0xe5e80;        // LEA e5e80(PC),A0 (fixed ROM WORD table, stride 4).
const std::uint32_t ON01_PICK_D72=0xe5e90;        // LEA e5e90(PC),A0.
const std::uint32_t ON01_STREAM=0xe5fbe;          // LEA e5fbe(PC),A0 (fixed ROM WORD triples, negative WORD ends).
const std::uint32_t ON01_SPRITES=0xe60c6;         // LEA e60c6(PC),A0 (fixed ROM LONG table).
bool on01_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on01_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool on01_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n01 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #callback,(A6) then continue at next_pc.
bool on01_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// MOVE.W #v,68(A6); MOVE.W #v,1e(A6).
bool on01_height(AnimationMachineContext& c,std::uint32_t v) {
    return on01_put(c,c.s.a[6],0x68,2,v) && on01_put(c,c.s.a[6],0x1e,2,v);
}
// LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1;
// JSR 49f8c.L (the bank LONG and the LONG at its value + d16 through the live bus).
bool on01_animation(AnimationMachineContext& c,std::uint32_t k,std::uint32_t bank,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!on01_put(c,r.a[6],0x20,2,k) || !am_read(c,bank,4,value) || !on01_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!on01_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!on01_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); LEA 26(A6),A0; MOVE.W D0,D1 (from_8c: MOVE.W 8c(A6),D1); ADD.W D1,D1;
// ADD.W D1,D1; MOVEA.L bank.L,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.L (the bank LONG is read twice; WORD index
// sign-extended).
bool on01_index_animation(AnimationMachineContext& c,std::uint32_t k,std::uint32_t bank,bool from_8c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!on01_put(c,r.a[6],0x20,2,k) || !am_read(c,bank,4,value) || !on01_put(c,r.a[6],0x22,4,value))return false;
    r.a[0]=am_index(r.a[6],0x26);
    if(from_8c){if(!on01_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[1],value);}else am_word(r.d[1],r.d[0]);
    am_word(r.d[1],(r.d[1]<<2)&65535U);
    if(!am_read(c,bank,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;
    am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L c(A6),A0; TST.B 62(A0); BEQ.W zero_pc (parent node BYTE 62).
bool on01_parent_test(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!on01_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
    if(!on01_get(c,r.a[0],0x62,1,value))return false;r.pc=(value&255U)==0U?zero_pc:next_pc;return true;
}
// MOVEA.L c(A6),A0; ST.B d16(A0); JMP 2a00.L (ST keeps the CCR).
bool on01_parent_mark(AnimationMachineContext& c,std::uint32_t displacement) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!on01_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
    if(!on01_put(c,r.a[0],displacement,1,0xff))return false;r.pc=0x2a00;return true;
}
// LEA table(PC),A0; MOVE.W 8c(A6),D0; LSL.W #2,D0; MOVE.W (A0,D0.W),8c(A6); BRA.W e5d9a.
bool on01_pick(AnimationMachineContext& c,std::uint32_t table) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=table;if(!on01_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],(value<<2)&65535U);
    if(!am_read(c,am_index(r.a[0],r.d[0]),2,value) || !on01_put(c,r.a[6],0x8c,2,value))return false;r.pc=0xe5d9a;return true;
}
// MOVE.W (A0)+,d16(A6) (fixed ROM stream WORD); returns the WORD.
bool on01_stream(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t& value) {
    AnimationMachineState& r=c.s;
    if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;return on01_put(c,r.a[6],displacement,2,value);
}
// MOVE.W (A0)+,7e(A6); MOVE.W (A0)+,80(A6); MOVE.L A0,88(A6).
bool on01_stream_rest(AnimationMachineContext& c) {
    std::uint32_t value=0;
    return on01_stream(c,0x7e,value) && on01_stream(c,0x80,value) && on01_put(c,c.s.a[6],0x88,4,c.s.a[0]);
}
// ADDQ.B/SUBQ.B #1,5d2d(A5) (BYTE read-modify-write).
bool on01_count(AnimationMachineContext& c,std::uint32_t delta) {
    std::uint32_t value=0;if(!on01_get(c,c.s.a[5],0x5d2d,1,value))return false;return on01_put(c,c.s.a[5],0x5d2d,1,(value+delta)&255U);
}
// CMPI.W #lim,32(A6); BLE.W le_pc (signed WORD <=).
bool on01_bottom(AnimationMachineContext& c,std::uint32_t lim,std::uint32_t le_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!on01_get(c,c.s.a[6],0x32,2,value))return false;
    const std::int32_t y=static_cast<std::int32_t>(am_extend_word(value)),l=static_cast<std::int32_t>(am_extend_word(lim));
    c.s.pc=y<=l?le_pc:next_pc;return true;
}
}
// Objects F4 N01 (74 block starts): the debris object 5208a (bank 2001e0, fixed ROM records 5205e + 8 * 76, BYTE 5d2d(A5) count) with
// its installed callback 52100 (WORD palette table 5206e indexed by the upper BYTE of 8c, ffff ends), and the U07 children e5bb0 / e5c74 /
// e5d72 e5d86 / e5ea0 (banks 2000c8 2000b8 with the LONG at their value + d16 or + 4 * index; installed callbacks e5c06 e5cdc e5dfa e5eca
// e5f1a; WORD tables e5e80/e5e90; WORD triple stream e5fbe creating the 28ae child e5f32 with its LONG table e60c6 and installed callbacks
// e5f74 e5f9e). Consumers e5c12 e5e06 (C returned by 49fc6). No known-carry producer, no boundary, no port write.
bool animation_objects_n01_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 5208a: MOVE.W #223,20(A6); MOVE.L 2001e0.L,22(A6); MOVE.W #189f,D0; JSR 3af8.L.
    case 0x5208a:
        if(!on01_put(c,r.a[6],0x20,2,0x223) || !am_read(c,ON01_BANK_E0,4,value) || !on01_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[0],0x189f);return am_call(c,0x3af8,0x520a2);
    // MOVE.W 76(A6),D0; ADDQ.B #1,5d2d(A5); LSL.W #3,D0; LEA 5205e(PC,D0.W),A0; MOVE.W (A0)+,D0; MOVE.W (A0)+,D1; MOVE.L A0,-(A7);
    // MOVE.W D0,2e(A6); MOVE.W D1,32(A6); MOVEA.L (A7)+,A0; MOVEA.L (A0),A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x520a2:
        if(!on01_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);
        if(!on01_count(c,1U))return false;
        am_word(r.d[0],(r.d[0]<<3)&65535U);r.a[0]=am_index(ON01_RECORDS,r.d[0]);
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.a[0]+=2U;
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);r.a[0]+=2U;
        if(!am_push(c,4,r.a[0]) || !on01_put(c,r.a[6],0x2e,2,r.d[0]&65535U) || !on01_put(c,r.a[6],0x32,2,r.d[1]&65535U) ||
           !am_pop(c,4,value))return false;
        r.a[0]=value;if(!am_read(c,r.a[0],4,value))return false;r.a[1]=value;
        am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x520cc);
    case 0x520cc:if(!on01_height(c,0))return false;return am_call(c,0x16ef0,0x520de);   // MOVE.W #0,68(A6); MOVE.W #0,1e(A6); JSR 16ef0.L.
    case 0x520de:if(!on01_put(c,r.a[6],0x8c,2,0))return false;am_word(r.d[0],0x40);return am_call(c,0x49a84,0x520ec); // CLR.W 8c(A6); MOVE.W #40,D0; JSR 49a84.L.
    // ADDI.W #60,D0; MOVE.W D0,8e(A6); MOVE.W #ffff,90(A6); MOVE.L #52100,(A6).
    case 0x520ec:
        am_word(r.d[0],(r.d[0]+0x60U)&65535U);
        if(!on01_put(c,r.a[6],0x8e,2,r.d[0]&65535U) || !on01_put(c,r.a[6],0x90,2,0xffff))return false;return on01_install(c,0x52100,0x52100);
    // (installed callback) MOVEQ #0,D0; MOVE.B 8c(A6),D0; ADD.W D0,D0; LEA 5206e(PC),A0; MOVE.W (A0,D0.W),D0; CMPI.W #ffff,D0; BEQ.W 5214c.
    case 0x52100:
        if(!on01_get(c,r.a[6],0x8c,1,value))return false;r.d[0]=(value&255U)<<1;r.a[0]=ON01_PALETTES;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
        r.pc=(r.d[0]&65535U)==0xffffU?0x5214c:0x52118;return true;
    case 0x52118:if(!on01_get(c,r.a[6],0x90,2,value))return false;r.pc=(r.d[0]&65535U)==(value&65535U)?0x52136:0x52120;return true; // CMP.W 90(A6),D0; BEQ.W 52136.
    case 0x52120:if(!on01_put(c,r.a[6],0x90,2,r.d[0]&65535U))return false;return am_call(c,0x8ff4,0x5212a); // MOVE.W D0,90(A6); JSR 8ff4.L.
    case 0x5212a:if(!on01_get(c,r.a[6],0x90,2,value))return false;am_word(r.d[0],value);r.d[1]=0;return am_call(c,0x8ebe,0x52136); // MOVE.W 90(A6),D0; MOVEQ #0,D1; JSR 8ebe.L.
    case 0x52136:case 0xe5c06:case 0xe5cdc:case 0xe5dfa:return am_call(c,0x43e34,r.pc+6U);   // JSR 43e34.L.
    case 0x5213c:case 0xe5c0c:case 0xe5ce2:case 0xe5e00:return am_call(c,0x49fc6,r.pc+6U);   // JSR 49fc6.L.
    // MOVE.W 8e(A6),D0; ADD.W D0,8c(A6); RTS.
    case 0x52142:
        if(!on01_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[0],value);
        if(!on01_get(c,r.a[6],0x8c,2,value) || !on01_put(c,r.a[6],0x8c,2,(value+r.d[0])&65535U))return false;return am_return(c);
    case 0x5214c:if(!on01_count(c,0xffU))return false;r.pc=0x2a00;return true;              // SUBQ.B #1,5d2d(A5); JMP 2a00.L.

    // ---- e5bb0 (U07 child): MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L.
    case 0xe5bb0:case 0xe5d9a:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,r.pc+0xaU);
    // MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); MOVE.W #31,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xe5bba:if(!on01_height(c,0x8810))return false;am_word(r.d[0],0x31);am_word(r.d[1],1);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xe5bd8);
    case 0xe5bd8:return on01_animation(c,0x14a,ON01_BANK_C8,0x4,0xe5c00);   // animation 14a, bank LONG 2000c8, + 4.
    case 0xe5c00:return on01_install(c,0xe5c06,0xe5c06);                    // MOVE.L #e5c06,(A6).
    case 0xe5c12:return on01_consume(c,false,0xe5c3e,0xe5c16);              // BCC.W e5c3e (C returned by 49fc6).
    case 0xe5c16:return on01_animation(c,0x14a,ON01_BANK_C8,0x4,0xe5c3e);
    case 0xe5c3e:return on01_parent_test(c,0xe5c72,0xe5c4a);
    case 0xe5c4a:return on01_animation(c,0x14a,ON01_BANK_C8,0x8,0xe5c72);
    // RTS (keeps C).
    case 0xe5c72:case 0xe5d70:case 0xe5e7e:case 0xe5f18:case 0xe5f30:case 0xe5f96:case 0xe5fbc:return am_return(c);

    // ---- e5c74 (U07 child): MOVEQ #-c,D0; MOVEQ #1e,D1; JSR 49290.L.
    case 0xe5c74:r.d[0]=0xfffffff4U;r.d[1]=0x1e;return am_call(c,0x49290,0xe5c7e);
    // MOVE.W #8834,68(A6); MOVE.W #8834,1e(A6); MOVE.W #2d,D0; MOVE.W #0,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xe5c7e:if(!on01_height(c,0x8834))return false;am_word(r.d[0],0x2d);am_word(r.d[1],0);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xe5c9c);
    // MOVE.W #c,76(A6); MOVE.W #1,D0; animation 12a with bank 2000b8 and index D0 (MOVE.W D0,D1).
    case 0xe5c9c:
        if(!on01_put(c,r.a[6],0x76,2,0xc))return false;am_word(r.d[0],1);
        return on01_index_animation(c,0x12a,ON01_BANK_B8,false,0xe5cd6);
    case 0xe5cd6:return on01_install(c,0xe5cdc,0xe5cdc);                    // MOVE.L #e5cdc,(A6).
    // LEA 26(A6),A0; TST.W 4(A0); BNE.W e5d2c.
    case 0xe5ce8:r.a[0]=am_index(r.a[6],0x26);if(!on01_get(c,r.a[0],0x4,2,value))return false;r.pc=(value&65535U)!=0U?0xe5d2c:0xe5cf4;return true;
    // MOVE.W #1,D0; ADD.W 76(A6),D0; animation 12a with bank 2000b8 and index D0 (MOVE.W D0,D1).
    case 0xe5cf4:case 0xe5d38:
        if(!on01_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],(1U+value)&65535U);
        return on01_index_animation(c,0x12a,ON01_BANK_B8,false,r.pc==0xe5cf4U?0xe5d2cU:0xe5d70U);
    case 0xe5d2c:return on01_parent_test(c,0xe5d70,0xe5d38);

    // ---- e5d72 / e5d86 (U07 children): 8c = WORD table + 4 * 8c, then BRA.W e5d9a.
    case 0xe5d72:return on01_pick(c,ON01_PICK_D72);
    case 0xe5d86:return on01_pick(c,ON01_PICK_D86);
    // animation 14a with bank 2000c8 and index 8c (MOVE.W 8c(A6),D1 after the 20/22 writes).
    case 0xe5da4:case 0xe5e0a:return on01_index_animation(c,0x14a,ON01_BANK_C8,true,r.pc==0xe5da4U?0xe5dd6U:0xe5e3cU);
    // MOVE.W 8c(A6),D1; MOVE.W #31,D0; MOVE.B #0,D2; JSR c6a96.L.
    case 0xe5dd6:if(!on01_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[1],value);am_word(r.d[0],0x31);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xe5de8);
    case 0xe5de8:if(!on01_height(c,0x8834))return false;return on01_install(c,0xe5dfa,0xe5dfa); // MOVE.W #8834,68/1e(A6); MOVE.L #e5dfa,(A6).
    case 0xe5e06:return on01_consume(c,false,0xe5e3c,0xe5e0a);              // BCC.W e5e3c (C returned by 49fc6).
    case 0xe5e3c:return on01_parent_test(c,0xe5e7e,0xe5e48);
    // MOVE.W 8c(A6),D0; ADDQ.W #1,D0; animation 14a with bank 2000c8 and index D0 (MOVE.W D0,D1).
    case 0xe5e48:
        if(!on01_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],(value+1U)&65535U);
        return on01_index_animation(c,0x14a,ON01_BANK_C8,false,0xe5e7e);

    // ---- e5ea0 (U07 child): MOVE.W #0,76(A6); LEA e5fbe(PC),A0; MOVE.W (A0)+,7c(A6); BPL.W e5eb8.
    case 0xe5ea0:
        if(!on01_put(c,r.a[6],0x76,2,0))return false;r.a[0]=ON01_STREAM;
        if(!on01_stream(c,0x7c,value))return false;r.pc=(value&0x8000U)==0U?0xe5eb8:0xe5eb2;return true;
    case 0xe5eb2:case 0xe5f90:r.pc=0x2a00;return true;                      // JMP 2a00.L.
    case 0xe5eb8:if(!on01_stream_rest(c))return false;return on01_install(c,0xe5eca,0xe5eca); // ...; MOVE.L #e5eca,(A6).
    // (installed callback) MOVE.W 76(A6),D0; ADDQ.W #1,D0; MOVE.W D0,76(A6); CMP.W 7c(A6),D0; BLT.W e5f18 (signed WORD <).
    case 0xe5eca:
        if(!on01_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],(value+1U)&65535U);
        if(!on01_put(c,r.a[6],0x76,2,r.d[0]&65535U) || !on01_get(c,r.a[6],0x7c,2,value))return false;
        r.pc=static_cast<std::int32_t>(am_extend_word(r.d[0]))<static_cast<std::int32_t>(am_extend_word(value))?0xe5f18:0xe5edc;return true;
    case 0xe5edc:r.a[0]=0xe5f32;am_word(r.d[0],0xa);return am_call(c,0x28ae,0xe5eec);   // MOVEA.L #e5f32,A0; MOVE.W #a,D0; JSR 28ae.L.
    // MOVE.W 7e(A6),7e(A0); MOVE.W 80(A6),80(A0); MOVEA.L 88(A6),A0; MOVE.W (A0)+,7c(A6); BPL.W e5f0c.
    case 0xe5eec:
        if(!on01_get(c,r.a[6],0x7e,2,value) || !on01_put(c,r.a[0],0x7e,2,value) || !on01_get(c,r.a[6],0x80,2,value) ||
           !on01_put(c,r.a[0],0x80,2,value) || !on01_get(c,r.a[6],0x88,4,value))return false;
        r.a[0]=value;if(!on01_stream(c,0x7c,value))return false;r.pc=(value&0x8000U)==0U?0xe5f0c:0xe5f04;return true;
    case 0xe5f04:if(!am_write(c,r.a[6],4,0xe5f1a))return false;return am_return(c);       // MOVE.L #e5f1a,(A6); RTS.
    case 0xe5f0c:if(!on01_stream_rest(c))return false;r.pc=0xe5f18;return true;
    // (installed callback) TST.B 62(A6); BEQ.W e5f30.
    case 0xe5f1a:if(!on01_get(c,r.a[6],0x62,1,value))return false;r.pc=(value&255U)==0U?0xe5f30:0xe5f22;return true;
    case 0xe5f22:return on01_parent_mark(c,0x63);                           // MOVEA.L c(A6),A0; ST.B 63(A0); JMP 2a00.L.
    // (28ae child) MOVE.W #a0,2e(A6); MOVE.W #e0,32(A6); MOVE.L #8000,3a(A6); LEA e60c6(PC),A0; MOVE.W 7e(A6),D0; ADD.W D0,D0 (twice);
    // MOVE.L (A0,D0.W),84(A6); BNE.W e5f60.
    case 0xe5f32:
        if(!on01_put(c,r.a[6],0x2e,2,0xa0) || !on01_put(c,r.a[6],0x32,2,0xe0) || !on01_put(c,r.a[6],0x3a,4,0x8000) ||
           !on01_get(c,r.a[6],0x7e,2,value))return false;
        r.a[0]=ON01_SPRITES;am_word(r.d[0],(value<<2)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value) || !on01_put(c,r.a[6],0x84,4,value))return false;
        r.pc=value!=0U?0xe5f60:0xe5f5c;return true;
    case 0xe5f5c:r.pc=0xe5f98;return true;                                  // BRA.W e5f98.
    // MOVE.W 80(A6),D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xe5f60:if(!on01_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xe5f6e);
    case 0xe5f6e:return on01_install(c,0xe5f74,0xe5f74);                    // MOVE.L #e5f74,(A6).
    case 0xe5f74:case 0xe5f9e:return am_call(c,0x43ea4,r.pc+6U);            // (installed callback) JSR 43ea4.L.
    // MOVE.L 84(A6),D7; MOVEQ #0,D0; JSR 16ea4.L.
    case 0xe5f7a:if(!on01_get(c,r.a[6],0x84,4,value))return false;r.d[7]=value;r.d[0]=0;return am_call(c,0x16ea4,0xe5f86);
    case 0xe5f86:return on01_bottom(c,0x220,0xe5f96,0xe5f90);               // CMPI.W #220,32(A6); BLE.W e5f96.
    case 0xe5f98:return on01_install(c,0xe5f9e,0xe5f9e);                    // MOVE.L #e5f9e,(A6).
    case 0xe5fa4:return on01_bottom(c,0x200,0xe5fbc,0xe5fae);               // CMPI.W #200,32(A6); BLE.W e5fbc.
    case 0xe5fae:return on01_parent_mark(c,0x62);                           // MOVEA.L c(A6),A0; ST.B 62(A0); JMP 2a00.L.
    default:return am_error(c,"unsupported animation objects n01 PC");
    }
}
}
