#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OU16_BANK_ANIMATION=0x2001d8;  // MOVE.L 2001d8.L,22(A6) (banked window LONG, live bus).
const std::uint32_t OU16_TAIL_RETURN=0xb014e;     // RTS of b0106 (keeps the C set by b011a or b0144).
const std::uint32_t OU16_PICK_RETURN=0xb0226;     // RTS of b0206 (keeps the C set by b0210 or b021c).
const std::uint32_t OU16_DIRECTION_ROUND=0xb02e6; // ADDQ.B #8,D0; LSR.B #4,D0; RTS.
const std::uint32_t OU16_OBJECT_RETURN=0xbbf02;   // RTS of the bbe74 callback.
const std::uint32_t OU16_PARENT_LIST=0x100bf4;    // MOVEA.L #100bf4,A1 (the 2986 list argument).
bool ou16_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou16_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool ou16_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u16 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #callback,(A6) then continue at the installed callback.
bool ou16_install(AnimationMachineContext& c,std::uint32_t callback) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=callback;return true;
}
// MOVEA.L #child,A0; MOVE.W #k,D0; MOVEA.L #100bf4,A1; JSR 2986.L (buffer_cue child).
bool ou16_cue(AnimationMachineContext& c,std::uint32_t child,std::uint32_t k,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],k);c.s.a[1]=OU16_PARENT_LIST;return am_call(c,0x2986,return_pc);
}
// MOVE.W #0,D0; MOVEQ #k,D1; JSR 49214.L (boundary).
bool ou16_effect(AnimationMachineContext& c,std::uint32_t k,std::uint32_t return_pc) {
    am_word(c.s.d[0],0);c.s.d[1]=k;return am_call(c,0x49214,return_pc);
}
}
// Objects F4 U16 (39 block starts): the terrain helpers b0106 (U15 4c29a, then U08 43eb8 and U08b 4be34 when D6 bit 3 is set; returns
// C set by ORI CCR or C clear by ANDI.W) and b0206 (U15 4950e; consumes its C and returns the opposite known C with LONG 76(A6)); the
// direction helper b02c8 (ASR/NEG/LSR on D0); the object callback bbe12 (U12 4c0ac, U05 c6a96, the bank LONG 2001d8 and the LONG at its
// value + 80 for the interpreter 49f8c, U14 4a496) with the installed callback bbe74 (cleanup 43e34, interpreter 49fc6, U01 4b54e whose
// C is consumed, sound 3af8, buffer_cue 2986 children d1d38/38ba0, fade_card 2a00); the countdown callback f1a0e (installed f1a1a,
// fade_card 28ae child 4841a). Boundaries without an executor here: 49214 and d3802, and the U15 callees 4c29a and 4950e. U16 writes
// no port.
bool animation_objects_u16_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- b0106: MOVEQ #0,D0; MOVEQ #0,D1; MOVEQ #0,D2; MOVE.W #200,D3; SUB.W 46(A6),D3; JSR 4c29a.L (U15 boundary).
    case 0xb0106:
        r.d[0]=0;r.d[1]=0;r.d[2]=0;if(!ou16_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[3],(0x200U-value)&65535U);
        return am_call(c,0x4c29a,0xb011a);
    // ANDI.W #8,D6 (C clear); BEQ.W b014e.
    case 0xb011a:am_word(r.d[6],r.d[6]&8U);r.carry=AnimationCarryClear;r.pc=(r.d[6]&65535U)==0U?OU16_TAIL_RETURN:0xb0122;return true;
    // MOVEA.L 3e(A6),A1; JSR 43eb8.L.
    case 0xb0122:if(!ou16_get(c,r.a[6],0x3e,4,value))return false;r.a[1]=value;return am_call(c,0x43eb8,0xb012c);
    // SUB.L 32(A6),D1; ADDI.L #80000,D1; MOVE.L D1,3a(A6); CLR.L 36(A6); JSR 4be34.L.
    case 0xb012c:
        if(!ou16_get(c,r.a[6],0x32,4,value))return false;r.d[1]=(r.d[1]-value+0x80000U)&0xffffffffU;
        if(!ou16_put(c,r.a[6],0x3a,4,r.d[1]) || !ou16_put(c,r.a[6],0x36,4,0))return false;return am_call(c,0x4be34,0xb0144);
    // LSR.W #8,D4; MOVE.B D4,9e(A6); ORI.B #1,CCR (C set).
    case 0xb0144:
        am_word(r.d[4],(r.d[4]&65535U)>>8);if(!ou16_put(c,r.a[6],0x9e,1,r.d[4]&255U))return false;
        r.carry=AnimationCarrySet;r.pc=OU16_TAIL_RETURN;return true;
    case 0xb014e:case 0xb0226:case 0xbbf02:case 0xf1a22:return am_return(c); // RTS (keeps C).
    // ---- b0206: JSR 4950e.L (U15 boundary).
    case 0xb0206:return am_call(c,0x4950e,0xb020c);
    case 0xb020c:return ou16_consume(c,true,0xb021c,0xb0210);                // BCS.W b021c (C returned by 4950e).
    // MOVE.L A0,76(A6); ORI.B #1,CCR (C set); BRA.W b0226.
    case 0xb0210:if(!ou16_put(c,r.a[6],0x76,4,r.a[0]))return false;r.carry=AnimationCarrySet;r.pc=OU16_PICK_RETURN;return true;
    // MOVEQ #0,D0; MOVE.L D0,76(A6); ANDI.B #fe,CCR (C clear).
    case 0xb021c:r.d[0]=0;if(!ou16_put(c,r.a[6],0x76,4,0))return false;r.carry=AnimationCarryClear;r.pc=OU16_PICK_RETURN;return true;
    // ---- b02c8: ASR.W #8,D0; BTST.B #0,15(A6); BEQ.W b02de.
    case 0xb02c8:
        value=r.d[0]&65535U;value=(value>>8)|((value&0x8000U)!=0U?0xff00U:0U);am_word(r.d[0],value);
        if(!ou16_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&1U)==0U?0xb02de:0xb02d4;return true;
    // SUBI.B #40,D0; NEG.B D0; ADDI.B #40,D0 (D0.B = 80 - D0.B).
    case 0xb02d4:am_byte(r.d[0],(0x80U-(r.d[0]&255U))&255U);r.pc=0xb02de;return true;
    case 0xb02de:r.pc=(r.d[0]&0x80U)!=0U?0xb02e4:OU16_DIRECTION_ROUND;return true; // TST.B D0; BPL.W b02e6.
    case 0xb02e4:am_byte(r.d[0],(0U-(r.d[0]&255U))&255U);r.pc=OU16_DIRECTION_ROUND;return true; // NEG.B D0.
    // ADDQ.B #8,D0; LSR.B #4,D0; RTS.
    case 0xb02e6:am_byte(r.d[0],((r.d[0]+8U)&255U)>>4);return am_return(c);

    // ---- bbe12 (callback): JSR 4c0ac.L.
    case 0xbbe12:return am_call(c,0x4c0ac,0xbbe18);
    // MOVE.W #1,68(A6); MOVE.W #1,1e(A6); MOVE.W #c8,54(A6); MOVE.W #75,D0; MOVE.W #20,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xbbe18:
        if(!ou16_put(c,r.a[6],0x68,2,1) || !ou16_put(c,r.a[6],0x1e,2,1) || !ou16_put(c,r.a[6],0x54,2,0xc8))return false;
        am_word(r.d[0],0x75);am_word(r.d[1],0x20);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xbbe3c);
    // LEA 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 80(A1),A1;
    // JSR 49f8c.L.
    case 0xbbe3c:
        r.a[0]=am_index(r.a[6],0x26);
        if(!ou16_put(c,r.a[6],0x20,2,0x213) || !am_read(c,OU16_BANK_ANIMATION,4,value) || !ou16_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
        if(!ou16_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
        if(!ou16_get(c,r.a[1],0x80,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,0xbbe64);
    case 0xbbe64:am_word(r.d[0],0xe5d);return am_call(c,0x4a496,0xbbe6e);   // MOVE.W #e5d,D0; JSR 4a496.L.
    case 0xbbe6e:return ou16_install(c,0xbbe74);                              // MOVE.L #bbe74,(A6).
    case 0xbbe74:return am_call(c,0x43e34,0xbbe7a);                           // (installed callback) JSR 43e34.L.
    case 0xbbe7a:return am_call(c,0x49fc6,0xbbe80);                           // JSR 49fc6.L.
    case 0xbbe80:return am_call(c,0x4b54e,0xbbe86);                           // JSR 4b54e.L.
    case 0xbbe86:return ou16_consume(c,false,OU16_OBJECT_RETURN,0xbbe8a);     // BCC.W bbf02 (C returned by 4b54e).
    // CLR.B 5e(A6); BTST.B #7,61(A6); BEQ.W bbf02.
    case 0xbbe8a:
        if(!ou16_put(c,r.a[6],0x5e,1,0) || !ou16_get(c,r.a[6],0x61,1,value))return false;
        r.pc=(value&0x80U)==0U?OU16_OBJECT_RETURN:0xbbe98;return true;
    case 0xbbe98:am_word(r.d[0],0x1a2a);return am_call(c,0x3af8,0xbbea2);    // MOVE.W #1a2a,D0; JSR 3af8.L.
    case 0xbbea2:return ou16_cue(c,0xd1d38,0x14,0xbbeb8);                     // MOVEA.L #d1d38,A0; MOVE.W #14,D0; ...; JSR 2986.L.
    case 0xbbeb8:return ou16_effect(c,0x10,0xbbec4);                          // MOVE.W #0,D0; MOVEQ #10,D1; JSR 49214.L (boundary).
    // MOVE.W #e0ed,68(A0); MOVE.W #e0ed,1e(A0); MOVEA.L #38ba0,A0; MOVE.W #0,D0; MOVEA.L #100bf4,A1; JSR 2986.L.
    case 0xbbec4:
        if(!ou16_put(c,r.a[0],0x68,2,0xe0ed) || !ou16_put(c,r.a[0],0x1e,2,0xe0ed))return false;return ou16_cue(c,0x38ba0,0,0xbbee6);
    case 0xbbee6:return ou16_effect(c,0x40,0xbbef2);                          // MOVE.W #0,D0; MOVEQ #40,D1; JSR 49214.L (boundary).
    case 0xbbef2:r.a[1]=0xbbf04;return am_call(c,0xd3802,0xbbefc);           // LEA bbf04(PC),A1; JSR d3802.L (boundary).
    case 0xbbefc:case 0xf1a34:r.pc=0x2a00;return true;                       // JMP 2a00.L.

    // ---- f1a0e (callback): MOVE.W #294,76(A6); MOVE.L #f1a1a,(A6).
    case 0xf1a0e:if(!ou16_put(c,r.a[6],0x76,2,0x294))return false;return ou16_install(c,0xf1a1a);
    // f1a1a (installed callback): SUBQ.W #1,76(A6); BCS.W f1a24 (borrow: the WORD was 0).
    case 0xf1a1a:
        if(!ou16_get(c,r.a[6],0x76,2,value) || !ou16_put(c,r.a[6],0x76,2,(value-1U)&65535U))return false;
        r.pc=value==0U?0xf1a24:0xf1a22;return true;
    // MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0xf1a24:r.a[0]=0x4841a;am_word(r.d[0],0xa);return am_call(c,0x28ae,0xf1a34);
    default:return am_error(c,"unsupported animation objects u16 PC");
    }
}
}
