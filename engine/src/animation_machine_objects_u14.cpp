#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OU14_BANK_ANIMATION=0x200198;  // MOVE.L 200198.L,22(A6) (banked window LONG, live bus).
const std::uint32_t OU14_CHILD_TAIL=0x51702;       // MOVE.W D6,92(A6) (the shared tail of the child callbacks 5169e..516ec).
const std::uint32_t OU14_WAIT_PARENT=0x51752;      // MOVE.L #51758,(A6) (the parent wait of the child callbacks).
const std::uint32_t OU14_SIGNAL=0x5d2c;            // BYTE 5d2c(A5) (set by 51fcc, cleared by 50d46, tested by 52004).
const std::uint32_t OU14_HOLD=0x5d2d;              // BYTE 5d2d(A5) (cleared by 51fcc, tested by 50d50).
const std::uint32_t OU14_PARENT_LIST=0x100bf4;     // MOVEA.L #100bf4,A1 (the 2986 list argument).
bool ou14_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou14_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
std::uint32_t ou14_w(std::uint32_t value) {return value&65535U;}
// Two's complement value of a WORD (explicit, no implementation-defined conversion).
std::int32_t ou14_signed_word(std::uint32_t value) {
    return static_cast<std::int32_t>(value&0x7fffU)-((value&0x8000U)!=0U?32768:0);
}
// BSET.B/BCLR.B #bit,d16(A6) (BYTE read-modify-write; Z only).
bool ou14_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!ou14_get(c,c.s.a[6],displacement,1,value))return false;
    value=set?(value|(1U<<bit)):(value&~(1U<<bit));return ou14_put(c,c.s.a[6],displacement,1,value&255U);
}
// MOVE.L #callback,(A6) then continue at the installed callback.
bool ou14_install(AnimationMachineContext& c,std::uint32_t callback) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=callback;return true;
}
// MOVE.W #193,20(A6); MOVE.L 200198.L,22(A6).
bool ou14_animation_bank(AnimationMachineContext& c) {
    std::uint32_t value=0;
    return ou14_put(c,c.s.a[6],0x20,2,0x193) && am_read(c,OU14_BANK_ANIMATION,4,value) && ou14_put(c,c.s.a[6],0x22,4,value);
}
// MOVE.W #k,D0; MOVE.B #0,D1; JSR 8ebe.L.
bool ou14_palette(AnimationMachineContext& c,std::uint32_t k,std::uint32_t return_pc) {
    am_word(c.s.d[0],k);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// BSET.B #6,15(A6); MOVE.W #h,68(A6); MOVE.W #h,1e(A6).
bool ou14_height(AnimationMachineContext& c,std::uint32_t h) {
    return ou14_bit(c,0x15,6,true) && ou14_put(c,c.s.a[6],0x68,2,h) && ou14_put(c,c.s.a[6],0x1e,2,h);
}
// MOVEA.L (A7)+,A1; MOVE.W #100,D0; JSR 49f8c.L.
bool ou14_interpret(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.a[1]=value;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #0,D0; MOVE.W #d1,D1; MOVE.W #d6,D6; MOVE.W #d7,D7; MOVEA.L #a0,A0; BRA.W 51702 (child callback entry).
bool ou14_child(AnimationMachineContext& c,std::uint32_t d1,std::uint32_t d6,std::uint32_t d7,std::uint32_t a0) {
    AnimationMachineState& r=c.s;am_word(r.d[0],0);am_word(r.d[1],d1);am_word(r.d[6],d6);am_word(r.d[7],d7);r.a[0]=a0;
    r.pc=OU14_CHILD_TAIL;return true;
}
// MOVEA.L c(A6),A0; BTST.B #2,7e(A0) (true when the parent's bit 2 is set).
bool ou14_parent_bit(AnimationMachineContext& c,bool& set) {
    std::uint32_t value=0;if(!ou14_get(c,c.s.a[6],0xc,4,value))return false;c.s.a[0]=value;
    if(!ou14_get(c,c.s.a[0],0x7e,1,value))return false;set=(value&4U)!=0U;return true;
}
}
// Objects F4 U14 (78 block starts): the shared helpers 16ef0 (unsigned WORD compare into 15(A6) bit 2), 49260 (cleanup 43e08 around
// A0+2e) and 4a496 (8ebe with a BYTE stack save of 14(A6)); the callback 614d4 -> 50cca with the object builder 51482 (bank LONG
// 200198, palette 8ebe/8da2, interpreter 49f8c, five fade_card children, two U12 490ba picks) and the wait/grow chain 50d2c with the
// installed callbacks 50d3c 50d50 50d6a; the child callbacks 51634 5169e 516b8 516d2 516ec with the shared tail 51702 and the parent
// wait 51752 (installed 51758 5176e); the signal helpers 51fcc/51fda and the child callback 51ffa (installed 52004, random 49a84);
// the callback 7086a (U12 70418). Boundaries without an executor here: 51602 and 515fc (BSR.W helpers), the installed callback 50dae
// and the U13 dispatcher 70932. U14 has no carry consumer across blocks and no known-carry producer; it writes no port.
bool animation_objects_u14_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool flag=false;
    switch(r.pc) {
    // ---- 16ef0: MOVE.W d3e(A5),D0; CMP.W d46(A5),D0; BCC.W 16f06 (unsigned).
    case 0x16ef0:
        if(!ou14_get(c,r.a[5],0xd3e,2,value))return false;am_word(r.d[0],value);if(!ou14_get(c,r.a[5],0xd46,2,other))return false;
        r.pc=ou14_w(r.d[0])>=other?0x16f06:0x16efc;return true;
    case 0x16efc:if(!ou14_bit(c,0x15,2,false))return false;r.pc=0x16f0c;return true; // BCLR.B #2,15(A6); BRA.W 16f0c.
    case 0x16f06:if(!ou14_bit(c,0x15,2,true))return false;r.pc=0x16f0c;return true;  // BSET.B #2,15(A6).
    case 0x16f0c:case 0x50d44:case 0x50d58:case 0x50d94:case 0x50dac:case 0x51766:case 0x5179e:case 0x51ff2:case 0x5205c:
        return am_return(c);                                                       // RTS.
    // ---- 49260: LEA 2e(A0),A0; LEA 538e(A5),A1; JSR 43e08.L.
    case 0x49260:r.a[0]=am_index(r.a[0],0x2e);r.a[1]=am_index(r.a[5],0x538e);return am_call(c,0x43e08,0x4926e);
    case 0x4926e:r.a[0]=am_index(r.a[0],0xffd2);return am_return(c);             // SUBA.W #2e,A0; RTS.
    // ---- 4a496: MOVE.B 14(A6),-(A7); MOVEQ #0,D1; JSR 8ebe.L.
    case 0x4a496:
        if(!ou14_get(c,r.a[6],0x14,1,value) || !am_push(c,1,value))return false;r.d[1]=0;return am_call(c,0x8ebe,0x4a4a2);
    // MOVE.B 14(A6),16(A6); MOVE.B #0,17(A6); MOVE.B (A7)+,14(A6); RTS.
    case 0x4a4a2:
        if(!ou14_get(c,r.a[6],0x14,1,value) || !ou14_put(c,r.a[6],0x16,1,value) || !ou14_put(c,r.a[6],0x17,1,0) ||
           !am_pop(c,1,value) || !ou14_put(c,r.a[6],0x14,1,value&255U))return false;
        return am_return(c);

    // ---- 614d4 (callback): JMP 50cca.L.
    case 0x614d4:r.pc=0x50cca;return true;
    case 0x50cca:return am_call(c,0x51482,0x50cce);                             // BSR.W 51482.
    case 0x50cce:r.pc=0x50d2c;return true;                                      // BRA.W 50d2c.
    case 0x50d2c:return am_call(c,0x51fda,0x50d30);                             // BSR.W 51fda.
    // MOVE.B #78,8c(A6); MOVE.L #50d3c,(A6).
    case 0x50d30:if(!ou14_put(c,r.a[6],0x8c,1,0x78))return false;return ou14_install(c,0x50d3c);
    // 50d3c (installed callback): SUBQ.B #1,8c(A6); BEQ.W 50d46.
    case 0x50d3c:
        if(!ou14_get(c,r.a[6],0x8c,1,value))return false;value=(value-1U)&255U;if(!ou14_put(c,r.a[6],0x8c,1,value))return false;
        r.pc=value==0U?0x50d46:0x50d44;return true;
    // CLR.B 5d2c(A5); MOVE.L #50d50,(A6).
    case 0x50d46:if(!ou14_put(c,r.a[5],OU14_SIGNAL,1,0))return false;return ou14_install(c,0x50d50);
    // 50d50 (installed callback): TST.B 5d2d(A5); BEQ.W 50d5a.
    case 0x50d50:if(!ou14_get(c,r.a[5],OU14_HOLD,1,value))return false;r.pc=value==0U?0x50d5a:0x50d58;return true;
    // CLR.W 8c(A6); MOVE.W #40,8e(A6); MOVE.L #50d6a,(A6).
    case 0x50d5a:
        if(!ou14_put(c,r.a[6],0x8c,2,0) || !ou14_put(c,r.a[6],0x8e,2,0x40))return false;return ou14_install(c,0x50d6a);
    // 50d6a (installed callback): MOVE.W 8e(A6),D0; ADD.W D0,8c(A6); CMPI.W #2000,8c(A6); BCS.W 50d96 (unsigned).
    case 0x50d6a:
        if(!ou14_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[0],value);
        if(!ou14_get(c,r.a[6],0x8c,2,value))return false;value=(value+ou14_w(r.d[0]))&65535U;
        if(!ou14_put(c,r.a[6],0x8c,2,value))return false;r.pc=value<0x2000U?0x50d96:0x50d7c;return true;
    // MOVE.W #2000,8c(A6); MOVE.L #50dae,(A6); LEA 10d256.L,A0; JSR 1701a.L (50dae is an installed callback outside U14).
    case 0x50d7c:
        if(!ou14_put(c,r.a[6],0x8c,2,0x2000) || !am_write(c,r.a[6],4,0x50dae))return false;r.a[0]=0x10d256;
        return am_call(c,0x1701a,0x50d94);
    // MOVEQ #0,D2; MOVE.B 8c(A6),D2; BSR.W 51602 (boundary).
    case 0x50d96:if(!ou14_get(c,r.a[6],0x8c,1,value))return false;r.d[2]=value&255U;return am_call(c,0x51602,0x50da0);
    // MOVEQ #0,D2; MOVE.B 8c(A6),D2; LSR.W #1,D2; BSR.W 515fc (boundary).
    case 0x50da0:if(!ou14_get(c,r.a[6],0x8c,1,value))return false;r.d[2]=(value&255U)>>1;return am_call(c,0x515fc,0x50dac);

    // ---- 51482: MOVE.W #193,20(A6); MOVE.L 200198.L,22(A6); MOVE.W #d7d,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0x51482:if(!ou14_animation_bank(c))return false;return ou14_palette(c,0xd7d,0x5149e);
    case 0x5149e:return ou14_palette(c,0xd7c,0x514ac);                          // MOVE.W #d7c,D0; MOVE.B #0,D1; JSR 8ebe.L.
    // MOVE.B 19(A6),14(A6); MOVE.W #922,D0; JSR 4a496.L.
    case 0x514ac:
        if(!ou14_get(c,r.a[6],0x19,1,value) || !ou14_put(c,r.a[6],0x14,1,value))return false;am_word(r.d[0],0x922);
        return am_call(c,0x4a496,0x514bc);
    case 0x514bc:case 0x51668:case 0x51720:return am_call(c,0x16ef0,r.pc+6U);    // JSR 16ef0.L.
    // BSET.B #6,15(A6); MOVE.W #800,68(A6); MOVE.W #800,1e(A6); LEA 5162c(PC),A0; JSR 8da2.L.
    case 0x514c2:if(!ou14_height(c,0x800))return false;r.a[0]=0x5162c;return am_call(c,0x8da2,0x514de);
    // MOVEA.L #528c0,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x514de:r.a[1]=0x528c0;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x514ee);
    // MOVEA.L #child,A0; MOVE.W #a,D0; JSR 28ae.L (five fade_card children).
    case 0x514ee:r.a[0]=0x51634;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x514fe);
    case 0x514fe:r.a[0]=0x5169e;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x5150e);
    case 0x5150e:r.a[0]=0x516b8;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x5151e);
    case 0x5151e:r.a[0]=0x516d2;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x5152e);
    case 0x5152e:r.a[0]=0x516ec;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x5153e);
    // BCLR.B #2,7e(A6); MOVE.L #521cc,56(A6); LEA 52b82.L,A0; JSR 490ba.L.
    case 0x5153e:
        if(!ou14_bit(c,0x7e,2,false) || !ou14_put(c,r.a[6],0x56,4,0x521cc))return false;r.a[0]=0x52b82;return am_call(c,0x490ba,0x51558);
    // MOVE.W D0,54(A6); LEA 52bcc.L,A0; JSR 490ba.L.
    case 0x51558:if(!ou14_put(c,r.a[6],0x54,2,ou14_w(r.d[0])))return false;r.a[0]=0x52bcc;return am_call(c,0x490ba,0x51568);
    // MOVE.W D0,9a(A6); MOVE.B #0,a1(A6); RTS.
    case 0x51568:if(!ou14_put(c,r.a[6],0x9a,2,ou14_w(r.d[0])) || !ou14_put(c,r.a[6],0xa1,1,0))return false;return am_return(c);

    // ---- 51634 (child callback): MOVE.W #193,20(A6); MOVE.L 200198.L,22(A6); MOVE.W #0,D0; MOVE.W #80,D1; MOVE.W #ffd4,D6;
    // MOVE.W #8c,D7; MOVEA.L #528b6,A0; MOVE.W D6,92(A6); MOVE.W D7,94(A6); MOVE.L A0,-(A7); JSR 49290.L.
    case 0x51634:
        if(!ou14_animation_bank(c))return false;am_word(r.d[0],0);am_word(r.d[1],0x80);am_word(r.d[6],0xffd4);am_word(r.d[7],0x8c);
        r.a[0]=0x528b6;if(!ou14_put(c,r.a[6],0x92,2,ou14_w(r.d[6])) || !ou14_put(c,r.a[6],0x94,2,ou14_w(r.d[7])) || !am_push(c,4,r.a[0]))
            return false;
        return am_call(c,0x49290,0x51668);
    // BSET.B #6,15(A6); MOVE.W #2,68(A6); MOVE.W #2,1e(A6); MOVE.W #d7b,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0x5166e:if(!ou14_height(c,2))return false;return ou14_palette(c,0xd7b,0x5168e);
    case 0x5168e:return ou14_interpret(c,0x5169a);                             // MOVEA.L (A7)+,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x5169a:r.pc=OU14_WAIT_PARENT;return true;                             // BRA.W 51752.
    case 0x5169e:return ou14_child(c,0x80,0xff78,0x100,0x52838);                // (child callbacks) -> BRA.W 51702.
    case 0x516b8:return ou14_child(c,0xff80,0x58,0x208,0x52842);
    case 0x516d2:return ou14_child(c,0xfe80,0x148,0x318,0x5284c);
    case 0x516ec:return ou14_child(c,0xfdb0,0x254,0x398,0x52856);
    // MOVE.W D6,92(A6); MOVE.W D7,94(A6); MOVE.L A0,-(A7); MOVE.W #193,20(A6); MOVE.L 200198.L,22(A6); JSR 49290.L.
    case 0x51702:
        if(!ou14_put(c,r.a[6],0x92,2,ou14_w(r.d[6])) || !ou14_put(c,r.a[6],0x94,2,ou14_w(r.d[7])) || !am_push(c,4,r.a[0]) ||
           !ou14_animation_bank(c))return false;
        return am_call(c,0x49290,0x51720);
    // BSET.B #6,15(A6); MOVE.W #1,68(A6); MOVE.W #1,1e(A6); MOVE.W #d7a,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0x51726:if(!ou14_height(c,1))return false;return ou14_palette(c,0xd7a,0x51746);
    case 0x51746:return ou14_interpret(c,OU14_WAIT_PARENT);                     // MOVEA.L (A7)+,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x51752:return ou14_install(c,0x51758);                                // MOVE.L #51758,(A6).
    // 51758 (installed callback): MOVEA.L c(A6),A0; BTST.B #2,7e(A0); BNE.W 51768.
    case 0x51758:if(!ou14_parent_bit(c,flag))return false;r.pc=flag?0x51768:0x51766;return true;
    case 0x51768:return ou14_install(c,0x5176e);                                // MOVE.L #5176e,(A6).
    // 5176e (installed callback): MOVEA.L c(A6),A0; BTST.B #2,7e(A0); BEQ.B 51752.
    case 0x5176e:if(!ou14_parent_bit(c,flag))return false;r.pc=flag?0x5177a:OU14_WAIT_PARENT;return true;
    case 0x5177a:return am_call(c,0x43e34,0x51780);                             // JSR 43e34.L (cleanup).
    // MOVEA.L c(A6),A0; MOVE.W 32(A0),D0; CMP.W 92(A6),D0; BLT.W 5179e (signed).
    case 0x51780:
        if(!ou14_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ou14_get(c,r.a[0],0x32,2,value))return false;am_word(r.d[0],value);
        if(!ou14_get(c,r.a[6],0x92,2,other))return false;
        r.pc=ou14_signed_word(r.d[0])<ou14_signed_word(other)?0x5179e:0x51790;return true;
    // CMP.W 94(A6),D0; BGT.W 5179e (signed).
    case 0x51790:
        if(!ou14_get(c,r.a[6],0x94,2,other))return false;r.pc=ou14_signed_word(r.d[0])>ou14_signed_word(other)?0x5179e:0x51798;return true;
    case 0x51798:return am_call(c,0x49fc6,0x5179e);                             // JSR 49fc6.L.

    // ---- 51fcc: MOVE.B #ff,5d2c(A5); MOVE.B #0,5d2d(A5); RTS.
    case 0x51fcc:if(!ou14_put(c,r.a[5],OU14_SIGNAL,1,0xff) || !ou14_put(c,r.a[5],OU14_HOLD,1,0))return false;return am_return(c);
    case 0x51fda:return am_call(c,0x51fcc,0x51fdc);                             // BSR.B 51fcc.
    // MOVEA.L #51ffa,A0; MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.L.
    case 0x51fdc:r.a[0]=0x51ffa;am_word(r.d[0],0xa);r.a[1]=OU14_PARENT_LIST;return am_call(c,0x2986,0x51ff2);
    // 51ffa (child callback): CLR.W 8c(A6); MOVE.L #52004,(A6).
    case 0x51ffa:if(!ou14_put(c,r.a[6],0x8c,2,0))return false;return ou14_install(c,0x52004);
    // 52004 (installed callback): TST.B 5d2c(A5); BEQ.W 5205c.
    case 0x52004:if(!ou14_get(c,r.a[5],OU14_SIGNAL,1,value))return false;r.pc=value==0U?0x5205c:0x5200c;return true;
    case 0x5200c:if(!ou14_get(c,r.a[6],0x8c,2,value))return false;r.pc=value!=0U?0x52058:0x52014;return true; // TST.W 8c(A6); BNE.W.
    // MOVEA.L #5208a,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.L.
    case 0x52014:r.a[0]=0x5208a;am_word(r.d[0],0x14);r.a[1]=OU14_PARENT_LIST;return am_call(c,0x2986,0x5202a);
    case 0x5202a:r.d[0]=0;r.d[1]=0;return am_call(c,0x49260,0x52034);           // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49260.L.
    case 0x52034:am_word(r.d[0],2);return am_call(c,0x49a84,0x5203e);            // MOVE.W #2,D0; JSR 49a84.L.
    // MOVE.W D0,76(A0); MOVE.W #30,D0; JSR 49a84.L.
    case 0x5203e:if(!ou14_put(c,r.a[0],0x76,2,ou14_w(r.d[0])))return false;am_word(r.d[0],0x30);return am_call(c,0x49a84,0x5204c);
    // ADDI.W #20,D0; MOVE.W D0,8c(A6); BRA.W 5205c.
    case 0x5204c:am_word(r.d[0],r.d[0]+0x20U);if(!ou14_put(c,r.a[6],0x8c,2,ou14_w(r.d[0])))return false;r.pc=0x5205c;return true;
    // SUBQ.W #1,8c(A6).
    case 0x52058:
        if(!ou14_get(c,r.a[6],0x8c,2,value) || !ou14_put(c,r.a[6],0x8c,2,(value-1U)&65535U))return false;r.pc=0x5205c;return true;

    // ---- 7086a (callback): MOVE.W #0,9c(A6); JSR 70418(PC) (U12).
    case 0x7086a:if(!ou14_put(c,r.a[6],0x9c,2,0))return false;return am_call(c,0x70418,0x70874);
    case 0x70874:if(!ou14_put(c,r.a[6],0x87,1,2))return false;r.pc=0x70932;return true; // MOVE.B #2,87(A6); BRA.W 70932 (U13).
    default:return am_error(c,"unsupported animation objects u14 PC");
    }
}
}
