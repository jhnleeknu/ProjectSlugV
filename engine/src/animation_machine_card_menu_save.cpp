#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// SUBQ.W #1,D7 then BCS: the borrow is taken only when D7.W was 0 (D7 bits 16-31 kept).
void save_count(AnimationMachineState& r,std::uint32_t borrow_pc,std::uint32_t other_pc) {
    const std::uint32_t old=r.d[7]&65535U;am_word(r.d[7],old-1U);r.pc=old==0?borrow_pc:other_pc;
}
// MOVE.B (An),Dn: one live BYTE read, low BYTE replaced.
bool save_byte(AnimationMachineContext& c,std::uint32_t address,std::uint32_t& reg) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;am_byte(reg,value);return true;
}
}
// Card menu YES (c1c4 event 3 -> c1e6 BSR bd26): card save bd26 with the name copy bbb8
// ("METAL SLUG V3" from bb8e into -e4(A5)), the WORD checksum bb74 into -ce(A5) and three
// BIOS calls (c00468 twice, c0046e) that have no executor: a stop at the BIOS PC keeps the
// return LONG pushed by the JSR (bd60/bd90/be1c) above the saved A6; any other stop is
// "unsupported animation machine PC". be2e/be34 return a known C (ORI/ANDI CCR) to c1ea
// (animation_machine_card_menu_open.cpp); 9f36 computes the result menu row/column and
// a71a pushes the c214/c232 result descriptor through a0a0 and queues sound 1adb.
// Card write and BIOS register effects (10fdc2..10fdd0, 10fdc6) are not modeled.
bool animation_card_menu_save_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // MOVEA.L -ee(A5),A2; MOVEA.L (A2),A3; MOVE.W e(A3),D0; ANDI.W #e,D0; BNE 9f4e.
    case 0x9f36:
        if(!am_read(c,am_index(r.a[5],0xff12),4,value))return false;r.a[2]=value;
        if(!am_read(c,r.a[2],4,value))return false;r.a[3]=value;
        if(!am_read(c,r.a[3]+0xeU,2,value))return false;am_word(r.d[0],value&0xeU);
        r.pc=(r.d[0]&65535U)?0x9f4e:0x9f48;return true;
    // MOVEQ #2,D0; BRA 9f50.
    case 0x9f48:r.d[0]=2;r.pc=0x9f50;return true;
    // MOVEQ #0,D0.
    case 0x9f4e:r.d[0]=0;r.pc=0x9f50;return true;
    // MOVEQ #0,D1; MOVEQ #0,D2; ADD.B 9(A2),D0; MOVE.B a(A2),D1; ADDQ.B #1,D0; ADDQ.B #1,D1;
    // MOVE.B 8(A2),D2; ADD.B D2,D1 (all BYTE); MOVEA.L (A2),A0; LEA 10(A0),A0; MOVE.W D2,D7;
    // MULU.W #a,D7 (32-bit product); MOVEA.L (A0,D7.W),A0 (sign-extended WORD index); RTS.
    case 0x9f50:
        r.d[1]=0;r.d[2]=0;
        if(!am_read(c,r.a[2]+9U,1,value))return false;am_byte(r.d[0],r.d[0]+value);
        if(!save_byte(c,r.a[2]+0xaU,r.d[1]))return false;
        am_byte(r.d[0],r.d[0]+1U);am_byte(r.d[1],r.d[1]+1U);
        if(!save_byte(c,r.a[2]+8U,r.d[2]))return false;am_byte(r.d[1],r.d[1]+r.d[2]);
        if(!am_read(c,r.a[2],4,value))return false;r.a[0]=am_index(value,0x10);
        am_word(r.d[7],r.d[2]);r.d[7]=(r.d[7]&65535U)*10U;
        if(!am_read(c,am_index(r.a[0],r.d[7]&65535U),4,value))return false;r.a[0]=value;
        return am_return(c);
    // JSR a0a0 (card menu push executor; nested frame when -f2 already holds a menu).
    case 0xa71a:return am_call(c,0xa0a0,0xa720);
    // MOVE.W #1adb,D0 (high WORD kept); JSR 3af8.
    case 0xa720:am_word(r.d[0],0x1adb);return am_call(c,0x3af8,0xa72a);
    case 0xa72a:case 0xbb8c:return am_return(c);
    // MOVEQ #0,D0.
    case 0xbb74:r.d[0]=0;r.pc=0xbb76;return true;
    // MOVE.B (A0)+,D1; EXT.W D1; ADD.W D1,D0; ADD.W D0,D0; BCC bb84 (C = WORD carry of the doubling).
    case 0xbb76:
        if(!save_byte(c,r.a[0],r.d[1]))return false;r.a[0]+=1U;
        value=r.d[1]&255U;am_word(r.d[1],(value&0x80U)?(value|0xff00U):value);
        am_word(r.d[0],r.d[0]+r.d[1]);value=r.d[0]&65535U;am_word(r.d[0],value<<1);
        r.pc=(value&0x8000U)?0xbb82:0xbb84;return true;
    // NOT.W D0.
    case 0xbb82:am_word(r.d[0],~r.d[0]);r.pc=0xbb84;return true;
    // ADDI.W #3c5b,D0; SUBQ.W #1,D7; BNE bb76 (Z of the WORD result).
    case 0xbb84:
        am_word(r.d[0],r.d[0]+0x3c5bU);am_word(r.d[7],r.d[7]-1U);r.pc=(r.d[7]&65535U)?0xbb76:0xbb8c;return true;
    // MOVE.L A0,-(A7).
    case 0xbbb8:if(!am_push(c,4,r.a[0]))return false;r.pc=0xbbba;return true;
    // SUBQ.W #1,D7; BCS bbd0.
    case 0xbbba:save_count(r,0xbbd0,0xbbc0);return true;
    // MOVE.B (A1)+,(A0)+ (read, then write; Z = the moved BYTE); BNE bbba.
    case 0xbbc0:
        if(!am_read(c,r.a[1],1,value))return false;r.a[1]+=1U;
        if(!am_write(c,r.a[0],1,value))return false;r.a[0]+=1U;r.pc=value?0xbbba:0xbbc4;return true;
    // SUBQ.W #1,D7; BCS bbd0.
    case 0xbbc4:save_count(r,0xbbd0,0xbbca);return true;
    // MOVE.B #0,(A0)+; BRA bbc4.
    case 0xbbca:if(!am_write(c,r.a[0],1,0))return false;r.a[0]+=1U;r.pc=0xbbc4;return true;
    // MOVEA.L (A7)+,A0; RTS.
    case 0xbbd0:if(!am_pop(c,4,r.a[0]))return false;return am_return(c);
    // LEA -e4(A5),A0 (live A5); LEA bb8e(PC),A1; MOVEQ #14,D7; BSR bbb8.
    case 0xbd26:r.a[0]=am_index(r.a[5],0xff1c);r.a[1]=0xbb8e;r.d[7]=0x14;return am_call(c,0xbbb8,0xbd34);
    // MOVE.W #16,D7 (high WORD kept); BSR bb74.
    case 0xbd34:am_word(r.d[7],0x16);return am_call(c,0xbb74,0xbd3c);
    // MOVE.W D0,-ce(A5); MOVE.L A6,-(A7); MOVE.B #4,10fdc4; MOVE.W #268,10fdce; MOVE.B #0,10fdd0;
    // JSR c00468 (BIOS boundary 1, no executor).
    case 0xbd3c:
        if(!am_write(c,am_index(r.a[5],0xff32),2,r.d[0]&65535U) || !am_push(c,4,r.a[6]) ||
           !am_write(c,0x10fdc4,1,4) || !am_write(c,0x10fdce,2,0x268) || !am_write(c,0x10fdd0,1,0))return false;
        return am_call(c,0xc00468,0xbd60);
    // MOVE.B #3,10fdc4; MOVE.W #268,10fdce; MOVE.B #0,10fdd0; MOVE.L #107f1c,10fdc8;
    // MOVE.W #18,10fdcc; JSR c00468 (BIOS boundary 2).
    case 0xbd60:
        if(!am_write(c,0x10fdc4,1,3) || !am_write(c,0x10fdce,2,0x268) || !am_write(c,0x10fdd0,1,0) ||
           !am_write(c,0x10fdc8,4,0x107f1c) || !am_write(c,0x10fdcc,2,0x18))return false;
        return am_call(c,0xc00468,0xbd90);
    // MOVEA.L (A7)+,A6; BRA be0c.
    case 0xbd90:if(!am_pop(c,4,r.a[6]))return false;r.pc=0xbe0c;return true;
    // MOVE.L A6,-(A7); MOVE.B #0,10fdc2; JSR c0046e (BIOS boundary 3).
    case 0xbe0c:
        if(!am_push(c,4,r.a[6]) || !am_write(c,0x10fdc2,1,0))return false;return am_call(c,0xc0046e,0xbe1c);
    // MOVEA.L (A7)+,A6; LEA 108000,A5; TST.B 10fdc6; BNE be34.
    case 0xbe1c:
        if(!am_pop(c,4,r.a[6]))return false;r.a[5]=0x108000;
        if(!am_read(c,0x10fdc6,1,value))return false;r.pc=value?0xbe34:0xbe2e;return true;
    case 0xbe2e:r.carry=AnimationCarrySet;return am_return(c);   // ORI #1,CCR; RTS
    case 0xbe34:r.carry=AnimationCarryClear;return am_return(c); // ANDI #fe,CCR; RTS
    default:return am_error(c,"unsupported animation card menu save PC");
    }
}
}
