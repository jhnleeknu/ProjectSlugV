#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (LEA xxx.L, LEA d16(PC), MOVEA.L #, MOVE.L # callback/child entries).
const std::uint32_t OV_TEXT_STATE=0x104cd6;   // 3a70 LEA 104cd6.L,A3 (text cursor record)
const std::uint32_t OV_TEXT_CODE=0x3650;      // 3a62 LEA 3650(PC),A0
const std::uint32_t OV_WORK_BASE=0x108000;    // 8ecc LEA 108000.L,A5
const std::uint32_t OV_PALETTE_TEXT=0x8f6c;   // 8f44 LEA 8f6c(PC),A0 (debug string, fixed ROM)
const std::uint32_t OV_DEBUG_FLAGS=0x10f000;  // 8f28 BTST #2,10f000.L
const std::uint32_t OV_SINE=0x4419e;          // 443dc LEA 4419e(PC),A0 (WORD table, fixed ROM)
const std::uint32_t OV_SLOT_FLAGS=0x10fdb6;   // e5090/e50e4 LEA 10fdb6.L
const std::uint32_t OV_SCORE_A=0x10de14;      // e50a0/e50ba/e5216 LEA/MOVE.L 10de14.L
const std::uint32_t OV_SCORE_B=0x10de1c;      // e50a6/e50b4/e521c LEA/CMP.L 10de1c.L
const std::uint32_t OV_RESULT_TEXT=0x10ddfa;  // e568e/e56a0 LEA 10ddfa.L,A3
const std::uint32_t OV_PRINT_TARGET=0xe84c8;  // e5638/e565a/e5688 LEA e84c8.L,A1
const std::uint32_t OV_SEGMENT_TABLE=0xe583c; // e57ae LEA e583c(PC),A1 (LONG table, fixed ROM)
bool ov_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ov_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
std::int32_t ov_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
// MULS.W: signed 16 x 16 -> 32 (two's complement LONG without implementation-defined conversion).
std::uint32_t ov_muls(std::uint32_t a,std::uint32_t b) {
    std::int64_t product=static_cast<std::int64_t>(ov_signed_word(a))*static_cast<std::int64_t>(ov_signed_word(b));
    if(product<0)product+=0x100000000LL;
    return static_cast<std::uint32_t>(product);
}
// ASR.L #8.
std::uint32_t ov_asr8(std::uint32_t value) {return (value&0x80000000U)?((value>>8)|0xff000000U):(value>>8);}
// BSET #n on a memory BYTE.
bool ov_bset(AnimationMachineContext& c,std::uint32_t address,std::uint32_t bit) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    return am_write(c,address,1,(value|(1U<<(bit&7U)))&255U);
}
// Consumers of a known C (BCC clear_pc / else set_pc).
bool ov_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects u02 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// SUBQ.W #1,7a(A6); BEQ zero_pc, else the RTS at rts_pc.
bool ov_count_down(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t rts_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ov_get(c,r.a[6],0x7a,2,value))return false;value=(value-1U)&65535U;
    if(!ov_put(c,r.a[6],0x7a,2,value))return false;r.pc=value?rts_pc:zero_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #0,D0; JSR 28ae.L (fade_card child creation).
bool ov_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],0);return am_call(c,0x28ae,return_pc);
}
// TST.B 62(A6); BNE set_pc, else the RTS at rts_pc.
bool ov_wait_flag(AnimationMachineContext& c,std::uint32_t set_pc,std::uint32_t rts_pc) {
    std::uint32_t value=0;if(!ov_get(c,c.s.a[6],0x62,1,value))return false;c.s.pc=(value&255U)?set_pc:rts_pc;return true;
}
// MOVE.W #n,7a(A6); MOVE.L #callback,(A6) (then the callback).
bool ov_install_count(AnimationMachineContext& c,std::uint32_t count,std::uint32_t callback) {
    if(!ov_put(c,c.s.a[6],0x7a,2,count) || !am_write(c,c.s.a[6],4,callback))return false;c.s.pc=callback;return true;
}
// CLR.B 62(A6); MOVE.L #callback,(A6) (then the callback).
bool ov_install_wait(AnimationMachineContext& c,std::uint32_t callback) {
    if(!ov_put(c,c.s.a[6],0x62,1,0) || !am_write(c,c.s.a[6],4,callback))return false;c.s.pc=callback;return true;
}
// MOVEA.L c(A6),A0; ST.B 62(A0); JMP 2a00.L.
bool ov_signal_parent(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ov_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
    if(!ov_put(c,r.a[0],0x62,1,0xff))return false;r.pc=0x2a00;return true;
}
// MOVE.W 2e(A6),D0; LSL.W #5,D0; ADD.W 32(A6),D0; ADDI.W #7000,D0; LEA text(PC),A0; LEA e84c8.L,A1; JSR 3a70.L.
bool ov_print_row(AnimationMachineContext& c,std::uint32_t text,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t row=0,column=0;
    if(!ov_get(c,r.a[6],0x2e,2,row) || !ov_get(c,r.a[6],0x32,2,column))return false;
    am_word(r.d[0],((row<<5)+column+0x7000U)&65535U);r.a[0]=text;r.a[1]=OV_PRINT_TARGET;return am_call(c,0x3a70,return_pc);
}
// BSET #0,15(A0); MOVE.W #angle,7e(A0); MOVEA.L #child,A0; MOVE.W #0,D0; JSR 28ae.L.
bool ov_mark_child(AnimationMachineContext& c,std::uint32_t angle,std::uint32_t child,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;
    if(!ov_bset(c,am_index(r.a[0],0x15),0) || !ov_put(c,r.a[0],0x7e,2,angle))return false;return ov_child(c,child,return_pc);
}
}
// Object callbacks F4 U02 (133 block starts): the text cursor routines 3950 (record set), 396e (one step, C returned: Set at the
// end of the text, else Clear) and 3a70 (whole text through 396e), the C1 palette slot reference 8ebe (A5 := 108000), the C5 sine
// product 443d2, the result comparison e5086, and the result node callback e5120 with its installed callbacks e5168 e5196 e51ac
// e51d0 e51e6 e523c e525a and its children e5614 (+e5626), e5680 (+e56a0), e5724 (+e5794), e579c/e57a4 (+e57f0). The BNE after the
// BCS at e50fc consumes the flags of the same CMP.L and is bundled into e50f4. 3a7e and e56ac consume the C returned by 396e
// (398c Set; 3a12/3a4c/3a68 Clear, all ANDI/ORI CCR). JSR (A1) at 3a10/3a36/3a66 is a computed call: the target is the live A1
// (static ROM callers load e84c8 or 3650) and is dispatched by the routing (odd: unaligned PC; no executor: unsupported PC).
// The TRAP #15 sites 39c6/3a0c/8ec8, the RTS 8eca after 8ec8, the debug string 8f6c..8f84 and the callees 36ba 37e2 383e 3902
// 48256 e6496 have no executor. Existing executors called: card_menu 386e, card_menu_open 3650/e84c8, palette_bind 8da2, U01
// 48296, fade_card 28ae/2a00, sound 3af8, interpreter 49f8c/49fc6, F3a 43e34. Fixed ROM data (4419e table, e583c table, texts) is
// read through the live bus. The 8ef2..8f08 list walk and the 3976 text loop have no extra limit (block budget only).
bool animation_objects_u02_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- 3950: MOVE.L A0,6(A3); MOVE.L A1,a(A3); MOVE.L A2,e(A3); MOVE.W D0,(A3); MOVE.W D0,2(A3); MOVE.W D1,4(A3);
    // MOVE.W #0,16(A3); RTS.
    case 0x3950:
        if(!ov_put(c,r.a[3],6,4,r.a[0]) || !ov_put(c,r.a[3],0xa,4,r.a[1]) || !ov_put(c,r.a[3],0xe,4,r.a[2]) ||
            !am_write(c,r.a[3],2,r.d[0]&65535U) || !ov_put(c,r.a[3],2,2,r.d[0]&65535U) || !ov_put(c,r.a[3],4,2,r.d[1]&65535U) ||
            !ov_put(c,r.a[3],0x16,2,0))return false;
        return am_return(c);
    // ---- 396e: MOVEA.L 6(A3),A0; MOVEA.L a(A3),A1.
    case 0x396e:
        if(!ov_get(c,r.a[3],6,4,value) || !ov_get(c,r.a[3],0xa,4,other))return false;r.a[0]=value;r.a[1]=other;r.pc=0x3976;return true;
    // MOVE.W (A3),D0; MOVE.W 4(A3),D1; MOVE.W 2(A3),D3; BSR 386e.
    case 0x3976:
        if(!am_read(c,r.a[3],2,value))return false;am_word(r.d[0],value);
        if(!ov_get(c,r.a[3],4,2,value))return false;am_word(r.d[1],value);
        if(!ov_get(c,r.a[3],2,2,value))return false;am_word(r.d[3],value);
        return am_call(c,0x386e,0x3984);
    case 0x3984:r.pc=(r.d[2]&255U)?0x3992:0x398c;return true;      // CMPI.B #0,D2; BNE 3992.
    case 0x398c:r.carry=AnimationCarrySet;return am_return(c);       // ORI.B #1,CCR; RTS (end of text).
    // MOVE.W D3,2(A3); MOVE.W D1,4(A3); MOVE.W D0,(A3); CMPI.B #25,D2; BNE 3a0e.
    case 0x3992:
        if(!ov_put(c,r.a[3],2,2,r.d[3]&65535U) || !ov_put(c,r.a[3],4,2,r.d[1]&65535U) || !am_write(c,r.a[3],2,r.d[0]&65535U))return false;
        r.pc=(r.d[2]&255U)!=0x25U?0x3a0e:0x39a4;return true;
    // MOVE.B (A0),D2; CMPI.B #25,D2; BNE 39b4.
    case 0x39a4:if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[2],value);r.pc=(value&255U)!=0x25U?0x39b4:0x39ae;return true;
    case 0x39ae:r.a[0]+=1U;r.pc=0x3a0e;return true; // ADDQ.W #1,A0; BRA 3a0e.
    // CMPI.B #30,D2; SEQ D3; BSR 383e (boundary without an executor).
    case 0x39b4:am_byte(r.d[3],(r.d[2]&255U)==0x30U?0xffU:0U);return am_call(c,0x383e,0x39be);
    case 0x39be:r.pc=(r.d[7]&65535U)?0x39c8:0x39c6;return true; // CMPI.W #0,D7; BNE 39c8 (otherwise the TRAP #15 boundary 39c6).
    // MOVE.B (A0)+,D2; MOVEA.L e(A3),A2; MOVE.W 16(A3),D6; CMP.W D6,D7; BNE 39e4.
    case 0x39c8:
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[2],value);r.a[0]+=1U;
        if(!ov_get(c,r.a[3],0xe,4,value))return false;r.a[2]=value;
        if(!ov_get(c,r.a[3],0x16,2,value))return false;am_word(r.d[6],value);
        r.pc=(r.d[7]&65535U)!=(r.d[6]&65535U)?0x39e4:0x39d8;return true;
    // MOVE.W #0,16(A3); MOVE.L A0,6(A3); BRA 3976.
    case 0x39d8:if(!ov_put(c,r.a[3],0x16,2,0) || !ov_put(c,r.a[3],6,4,r.a[0]))return false;r.pc=0x3976;return true;
    case 0x39e4:r.pc=(r.d[6]&255U)?0x39f8:0x39ea;return true; // TST.B D6; BNE 39f8.
    // MOVEA.L (A2)+,A0; MOVE.L A2,e(A3); MOVE.L A0,12(A3); BRA 39fc.
    case 0x39ea:
        if(!am_read(c,r.a[2],4,value))return false;r.a[0]=value;r.a[2]+=4U;
        if(!ov_put(c,r.a[3],0xe,4,r.a[2]) || !ov_put(c,r.a[3],0x12,4,r.a[0]))return false;r.pc=0x39fc;return true;
    case 0x39f8:if(!ov_get(c,r.a[3],0x12,4,value))return false;r.a[0]=value;r.pc=0x39fc;return true; // MOVEA.L 12(A3),A0.
    case 0x39fc:r.pc=(r.d[2]&255U)==0x73U?0x3a1e:0x3a04;return true; // CMPI.B #73,D2; BEQ 3a1e.
    case 0x3a04:r.pc=(r.d[2]&255U)==0x78U?0x3a52:0x3a0c;return true; // CMPI.B #78,D2; BEQ 3a52 (otherwise the TRAP #15 boundary 3a0c).
    // MOVE.W (A3),D0; JSR (A1) (computed call).
    case 0x3a0e:if(!am_read(c,r.a[3],2,value))return false;am_word(r.d[0],value);return am_call(c,r.a[1],0x3a12);
    // MOVE.W D0,(A3); MOVE.L A0,6(A3); ANDI.B #fe,CCR; RTS.
    case 0x3a12:
        if(!am_write(c,r.a[3],2,r.d[0]&65535U) || !ov_put(c,r.a[3],6,4,r.a[0]))return false;r.carry=AnimationCarryClear;return am_return(c);
    // ADDQ.W #1,16(A3); MOVE.W (A3),D0; MOVE.W 2(A3),D2; MOVE.W D7,-(A7); BSR 386e.
    case 0x3a1e:
        if(!ov_get(c,r.a[3],0x16,2,value) || !ov_put(c,r.a[3],0x16,2,(value+1U)&65535U))return false;
        if(!am_read(c,r.a[3],2,value))return false;am_word(r.d[0],value);
        if(!ov_get(c,r.a[3],2,2,value))return false;am_word(r.d[2],value);
        if(!am_push(c,2,r.d[7]&65535U))return false;return am_call(c,0x386e,0x3a2e);
    // MOVE.W D1,4(A3); MOVE.W D3,2(A3); JSR (A1) (computed call).
    case 0x3a2e:
        if(!ov_put(c,r.a[3],4,2,r.d[1]&65535U) || !ov_put(c,r.a[3],2,2,r.d[3]&65535U))return false;return am_call(c,r.a[1],0x3a38);
    // MOVE.W (A7)+,D7; MOVE.L A0,12(A3); MOVE.W D0,(A3); CMPI.B #0,(A0); BNE 3a4c.
    case 0x3a38:
        if(!am_pop(c,2,value))return false;am_word(r.d[7],value);
        if(!ov_put(c,r.a[3],0x12,4,r.a[0]) || !am_write(c,r.a[3],2,r.d[0]&65535U) || !am_read(c,r.a[0],1,value))return false;
        r.pc=(value&255U)?0x3a4c:0x3a48;return true;
    case 0x3a48:if(!ov_put(c,r.a[3],0x16,2,r.d[7]&65535U))return false;r.pc=0x3a4c;return true; // MOVE.W D7,16(A3).
    case 0x3a4c:r.carry=AnimationCarryClear;return am_return(c); // ANDI.B #fe,CCR; RTS.
    // MOVE.W 16(A3),D4; ADDQ.W #1,D4; MOVE.W D4,16(A3); BSR 37e2 (boundary without an executor).
    case 0x3a52:
        if(!ov_get(c,r.a[3],0x16,2,value))return false;am_word(r.d[4],(value+1U)&65535U);
        if(!ov_put(c,r.a[3],0x16,2,r.d[4]&65535U))return false;return am_call(c,0x37e2,0x3a60);
    // MOVE.W (A3),D0; LEA 3650(PC),A0; JSR (A1) (computed call).
    case 0x3a60:if(!am_read(c,r.a[3],2,value))return false;am_word(r.d[0],value);r.a[0]=OV_TEXT_CODE;return am_call(c,r.a[1],0x3a68);
    // MOVE.W D0,(A3); ANDI.B #fe,CCR; RTS.
    case 0x3a68:if(!am_write(c,r.a[3],2,r.d[0]&65535U))return false;r.carry=AnimationCarryClear;return am_return(c);
    case 0x3a70:r.a[3]=OV_TEXT_STATE;return am_call(c,0x3950,0x3a7a); // LEA 104cd6.L,A3; BSR 3950.
    case 0x3a7a:return am_call(c,0x396e,0x3a7e);                      // BSR 396e.
    case 0x3a7e:return ov_carry(c,0x3a7a,0x3a80);                     // BCC 3a7a (carry consumer).
    case 0x3a80:case 0x8f6a:case 0xe511e:case 0xe5170:case 0xe519e:case 0xe51b4:case 0xe51d8:case 0xe51ee:case 0xe5246:
    case 0xe527a:case 0xe567e:case 0xe56be:case 0xe583a:return am_return(c); // RTS.

    // ---- 8ebe: CMPI.B #4,1d(A6); BCS 8ecc (unsigned; otherwise the TRAP #15 boundary 8ec8).
    case 0x8ebe:if(!ov_get(c,r.a[6],0x1d,1,value))return false;r.pc=(value&255U)<4U?0x8ecc:0x8ec8;return true;
    // LEA 108000.L,A5; LEA -326e(A5),A1; BTST #0,D1; BNE 8f10.
    case 0x8ecc:r.a[5]=OV_WORK_BASE;r.a[1]=am_index(r.a[5],0xcd92);r.pc=(r.d[1]&1U)?0x8f10:0x8ede;return true;
    // MOVE.W D0,D7; ANDI.W #ff,D7; LSL.W #4,D7; ADDQ.W #4,D7; MOVE.W 2(A1,D7.W),D6; CMP.W D7,D6; BEQ 8f10.
    case 0x8ede:
        am_word(r.d[7],((r.d[0]&255U)<<4)+4U);if(!am_read(c,am_index(r.a[1],r.d[7])+2U,2,value))return false;am_word(r.d[6],value);
        r.pc=(r.d[6]&65535U)==(r.d[7]&65535U)?0x8f10:0x8ef2;return true;
    // LEA (A1,D6.W),A2; CMP.W a(A2),D0; BNE 8f08.
    case 0x8ef2:
        r.a[2]=am_index(r.a[1],r.d[6]);if(!ov_get(c,r.a[2],0xa,2,value))return false;
        r.pc=(r.d[0]&65535U)!=(value&65535U)?0x8f08:0x8efe;return true;
    // BTST #0,f(A2); BEQ 8f94.
    case 0x8efe:if(!ov_get(c,r.a[2],0xf,1,value))return false;r.pc=(value&1U)?0x8f08:0x8f94;return true;
    // MOVE.W 2(A2),D6; CMP.W D7,D6; BNE 8ef2.
    case 0x8f08:
        if(!ov_get(c,r.a[2],2,2,value))return false;am_word(r.d[6],value);
        r.pc=(r.d[6]&65535U)!=(r.d[7]&65535U)?0x8ef2:0x8f10;return true;
    // MOVE.W #1000,D7; MOVE.W 2(A1,D7.W),D6; LEA (A1,D6.W),A2; CMP.W D7,D6; BNE 8f84.
    case 0x8f10:
        am_word(r.d[7],0x1000);if(!am_read(c,am_index(r.a[1],0x1000)+2U,2,value))return false;am_word(r.d[6],value);
        r.a[2]=am_index(r.a[1],r.d[6]);r.pc=(value&65535U)!=0x1000U?0x8f84:0x8f22;return true;
    // MOVE.B #ff,14(A6); BTST #2,10f000.L; BEQ 8f6a.
    case 0x8f22:
        if(!ov_put(c,r.a[6],0x14,1,0xff) || !am_read(c,OV_DEBUG_FLAGS,1,value))return false;r.pc=(value&4U)?0x8f34:0x8f6a;return true;
    // MOVE.W D0,D1; ANDI.W #1ff,D1; MOVE.W D1,-(A7); LSR.W #1,D0; ADDI.W #100,D0; MOVE.W D0,-(A7); LEA 8f6c(PC),A0;
    // JSR 3902.L (boundary without an executor).
    case 0x8f34:
        am_word(r.d[1],r.d[0]&0x1ffU);if(!am_push(c,2,r.d[1]&65535U))return false;
        am_word(r.d[0],(((r.d[0]&65535U)>>1)+0x100U)&65535U);if(!am_push(c,2,r.d[0]&65535U))return false;
        r.a[0]=OV_PALETTE_TEXT;return am_call(c,0x3902,0x8f4e);
    case 0x8f4e:r.a[0]=r.a[7];r.d[3]=0xffffffffU;r.d[4]=2;return am_call(c,0x36ba,0x8f5a); // MOVEA.L A7,A0; MOVEQ #-1,D3; MOVEQ #2,D4; JSR 36ba.L.
    case 0x8f5a:r.a[7]+=2U;r.a[0]=r.a[7];r.d[3]=0xffffffffU;r.d[4]=3;return am_call(c,0x36ba,0x8f68); // ADDQ.W #2,A7; ...; JSR 36ba.L.
    case 0x8f68:r.a[7]+=2U;r.pc=0x8f6a;return true; // ADDQ.W #2,A7.
    // MOVE.W D0,a(A2); MOVE.W D0,c(A2); BSET #7,D1; MOVE.B D1,f(A2).
    case 0x8f84:
        r.d[1]|=0x80U;
        if(!ov_put(c,r.a[2],0xa,2,r.d[0]&65535U) || !ov_put(c,r.a[2],0xc,2,r.d[0]&65535U) || !ov_put(c,r.a[2],0xf,1,r.d[1]&255U))return false;
        r.pc=0x8f94;return true;
    // CMPI.W #ffff,8(A2); BEQ 8fa2.
    case 0x8f94:if(!ov_get(c,r.a[2],8,2,value))return false;r.pc=(value&65535U)==65535U?0x8fa2:0x8f9e;return true;
    case 0x8f9e:if(!ov_get(c,r.a[2],8,2,value) || !ov_put(c,r.a[2],8,2,(value+1U)&65535U))return false;r.pc=0x8fa2;return true; // ADDQ.W #1,8(A2).
    // MOVE.W D0,D1; MOVE.W D6,D0; MOVE.W D1,D4; ANDI.W #ff,D4; LSL.W #4,D4; ADDQ.W #4,D4; LEA (A1,D4.W),A4; CMP.W 2(A4),D0;
    // BEQ 8fdc.
    case 0x8fa2:
        am_word(r.d[1],r.d[0]);am_word(r.d[0],r.d[6]);am_word(r.d[4],((r.d[1]&255U)<<4)+4U);r.a[4]=am_index(r.a[1],r.d[4]);
        if(!ov_get(c,r.a[4],2,2,value))return false;r.pc=(r.d[0]&65535U)==(value&65535U)?0x8fdc:0x8fbc;return true;
    // MOVE.W (A2),D2; MOVE.W 2(A2),D3; MOVE.W D2,(A1,D3.W); MOVE.W D3,2(A1,D2.W); MOVE.W 2(A4),D3; MOVE.W D0,(A1,D3.W);
    // MOVE.W D3,2(A2); MOVE.W D4,(A2); MOVE.W D0,2(A4) (unlink the slot, then insert it after the list head A4).
    case 0x8fbc:
        if(!am_read(c,r.a[2],2,value))return false;am_word(r.d[2],value);
        if(!ov_get(c,r.a[2],2,2,value))return false;am_word(r.d[3],value);
        if(!am_write(c,am_index(r.a[1],r.d[3]),2,r.d[2]&65535U) || !am_write(c,am_index(r.a[1],r.d[2])+2U,2,r.d[3]&65535U))return false;
        if(!ov_get(c,r.a[4],2,2,value))return false;am_word(r.d[3],value);
        if(!am_write(c,am_index(r.a[1],r.d[3]),2,r.d[0]&65535U) || !ov_put(c,r.a[2],2,2,r.d[3]&65535U) ||
            !am_write(c,r.a[2],2,r.d[4]&65535U) || !ov_put(c,r.a[4],2,2,r.d[0]&65535U))return false;
        r.pc=0x8fdc;return true;
    // LSR.W #4,D0; MOVEQ #0,D2; MOVE.B 1d(A6),D2; MOVE.B D0,19(A6,D2.W); MOVE.B D0,14(A6); ADDQ.B #1,D2; MOVE.B D2,1d(A6); RTS.
    case 0x8fdc:
        am_word(r.d[0],(r.d[0]&65535U)>>4);r.d[2]=0;if(!ov_get(c,r.a[6],0x1d,1,value))return false;r.d[2]=value&255U;
        if(!am_write(c,am_index(r.a[6],r.d[2])+0x19U,1,r.d[0]&255U) || !ov_put(c,r.a[6],0x14,1,r.d[0]&255U))return false;
        am_byte(r.d[2],r.d[2]+1U);if(!ov_put(c,r.a[6],0x1d,1,r.d[2]&255U))return false;return am_return(c);

    // ---- 443d2: MOVEQ #0,D2; MOVE.B D1,D2; ASR.L #8,D0; MOVE.L D0,D1; ADD.W D2,D2; LEA 4419e(PC),A0; MULS.W (A0,D2.W),D0;
    // MULS.W -80(A0,D2.W),D1; RTS.
    case 0x443d2:
        r.d[2]=r.d[1]&255U;r.d[0]=ov_asr8(r.d[0]);r.d[1]=r.d[0];am_word(r.d[2],r.d[2]<<1);r.a[0]=OV_SINE;
        if(!am_read(c,am_index(r.a[0],r.d[2]),2,value) || !am_read(c,am_index(r.a[0],r.d[2])-0x80U,2,other))return false;
        r.d[0]=ov_muls(r.d[0],value);r.d[1]=ov_muls(r.d[1],other);return am_return(c);

    // ---- e5086: MOVE.W #ffff,D0; MOVE.W D0,D1; MOVE.W 7c(A6),D2; LEA 10fdb6.L,A0; CMPI.B #0,(A0,D2.W); BEQ e5112.
    case 0xe5086:
        am_word(r.d[0],0xffff);am_word(r.d[1],0xffff);if(!ov_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[2],value);
        r.a[0]=OV_SLOT_FLAGS;if(!am_read(c,am_index(r.a[0],r.d[2]),1,value))return false;r.pc=(value&255U)?0xe50a0:0xe5112;return true;
    // LEA 10de14.L,A0; LEA 10de1c.L,A1; TST.W 7c(A6); BEQ e50c0.
    case 0xe50a0:
        r.a[0]=OV_SCORE_A;r.a[1]=OV_SCORE_B;if(!ov_get(c,r.a[6],0x7c,2,value))return false;r.pc=(value&65535U)?0xe50b4:0xe50c0;return true;
    case 0xe50b4:r.a[0]=OV_SCORE_B;r.a[1]=OV_SCORE_A;r.pc=0xe50c0;return true; // LEA 10de1c.L,A0; LEA 10de14.L,A1.
    // MOVEM.L A0-A1,-(A7); JSR e6496.L (boundary without an executor).
    case 0xe50c0:if(!am_push(c,4,r.a[1]) || !am_push(c,4,r.a[0]))return false;return am_call(c,0xe6496,0xe50ca);
    // SUBQ.W #1,D0; MOVEM.L (A7)+,A0-A1; CMPI.W #a,D1; BCC e5112 (unsigned).
    case 0xe50ca:
        am_word(r.d[0],r.d[0]-1U);if(!am_pop(c,4,value) || !am_pop(c,4,other))return false;r.a[0]=value;r.a[1]=other;
        r.pc=(r.d[1]&65535U)>=10U?0xe5112:0xe50d8;return true;
    // MOVEQ #1,D2; TST.W 7c(A6); BEQ e50e4.
    case 0xe50d8:r.d[2]=1;if(!ov_get(c,r.a[6],0x7c,2,value))return false;r.pc=(value&65535U)?0xe50e2:0xe50e4;return true;
    case 0xe50e2:r.d[2]=0;r.pc=0xe50e4;return true; // MOVEQ #0,D2.
    // LEA 10fdb6.L,A2; CMPI.B #0,(A2,D2.W); BEQ e5112.
    case 0xe50e4:r.a[2]=OV_SLOT_FLAGS;if(!am_read(c,am_index(r.a[2],r.d[2]),1,value))return false;r.pc=(value&255U)?0xe50f4:0xe5112;return true;
    // MOVE.L (A1),D2; CMP.L (A0),D2; BCS e5112; BNE e510e (bundled: the same CMP.L, unsigned).
    case 0xe50f4:
        if(!am_read(c,r.a[1],4,value) || !am_read(c,r.a[0],4,other))return false;r.d[2]=value;
        r.pc=value<other?0xe5112:(value!=other?0xe510e:0xe5100);return true;
    case 0xe5100:if(!ov_get(c,r.a[6],0x7c,2,value))return false;r.pc=(value&65535U)?0xe5108:0xe5112;return true; // TST.W 7c(A6); BEQ e5112.
    case 0xe5108:am_word(r.d[1],r.d[1]+1U);r.pc=0xe5112;return true;                         // ADDQ.W #1,D1; BRA e5112.
    case 0xe510e:am_word(r.d[0],r.d[0]+1U);am_word(r.d[1],r.d[1]+1U);r.pc=0xe5112;return true; // ADDQ.W #1,D0; ADDQ.W #1,D1.
    case 0xe5112:r.pc=(r.d[1]&65535U)<10U?0xe511e:0xe511a;return true;                       // CMPI.W #a,D1; BCS e511e (unsigned).
    case 0xe511a:am_word(r.d[0],0x3e7);r.pc=0xe511e;return true;                              // MOVE.W #3e7,D0.

    // ---- e5120 (callback): LEA e4f9e(PC),A0; JSR 8da2.L.
    case 0xe5120:r.a[0]=0xe4f9e;return am_call(c,0x8da2,0xe512a);
    case 0xe512a:return am_call(c,0x48296,0xe5130);  // JSR 48296.L.
    case 0xe5130:return ov_child(c,0xe5724,0xe5140); // MOVEA.L #e5724,A0; MOVE.W #0,D0; JSR 28ae.L.
    case 0xe5140:if(!ov_put(c,r.a[6],0x7c,2,1))return false;return am_call(c,0xe5086,0xe514a); // MOVE.W #1,7c(A6); BSR e5086.
    // MOVE.W D0,84(A6); MOVE.W #0,7c(A6); BSR e5086.
    case 0xe514a:if(!ov_put(c,r.a[6],0x84,2,r.d[0]&65535U) || !ov_put(c,r.a[6],0x7c,2,0))return false;return am_call(c,0xe5086,0xe5158);
    // MOVE.W D0,82(A6); MOVE.W #1e,7a(A6); MOVE.L #e5168,(A6) (then the callback e5168).
    case 0xe5158:if(!ov_put(c,r.a[6],0x82,2,r.d[0]&65535U))return false;return ov_install_count(c,0x1e,0xe5168);
    case 0xe5168:return ov_count_down(c,0xe5172,0xe5170); // SUBQ.W #1,7a(A6); BEQ e5172.
    case 0xe5172:am_word(r.d[0],0x1a8c);return am_call(c,0x3af8,0xe517c); // MOVE.W #1a8c,D0; JSR 3af8.L.
    case 0xe517c:return ov_child(c,0xe5680,0xe518c);  // MOVEA.L #e5680,A0; MOVE.W #0,D0; JSR 28ae.L.
    case 0xe518c:return ov_install_wait(c,0xe5196);   // CLR.B 62(A6); MOVE.L #e5196,(A6).
    case 0xe5196:return ov_wait_flag(c,0xe51a0,0xe519e); // TST.B 62(A6); BNE e51a0.
    case 0xe51a0:return ov_install_count(c,0x1e,0xe51ac); // MOVE.W #1e,7a(A6); MOVE.L #e51ac,(A6).
    case 0xe51ac:return ov_count_down(c,0xe51b6,0xe51b4);
    case 0xe51b6:return ov_child(c,0xe5614,0xe51c6);  // MOVEA.L #e5614,A0; MOVE.W #0,D0; JSR 28ae.L.
    case 0xe51c6:return ov_install_wait(c,0xe51d0);
    case 0xe51d0:return ov_wait_flag(c,0xe51da,0xe51d8);
    case 0xe51da:return ov_install_count(c,0xf,0xe51e6); // MOVE.W #f,7a(A6); MOVE.L #e51e6,(A6).
    case 0xe51e6:return ov_count_down(c,0xe51f0,0xe51ee);
    case 0xe51f0:return ov_child(c,0xe5324,0xe5200);  // MOVEA.L #e5324,A0; MOVE.W #0,D0; JSR 28ae.L.
    case 0xe5200:if(!am_push(c,4,r.a[0]))return false;return ov_child(c,0xe5324,0xe5212); // MOVE.L A0,-(A7); (second child).
    // MOVEQ #0,D0; MOVEQ #1,D1; MOVE.L 10de14.L,D2; CMP.L 10de1c.L,D2; BCC e5228 (unsigned).
    case 0xe5212:
        r.d[0]=0;r.d[1]=1;if(!am_read(c,OV_SCORE_A,4,value) || !am_read(c,OV_SCORE_B,4,other))return false;r.d[2]=value;
        r.pc=value>=other?0xe5228:0xe5226;return true;
    case 0xe5226:value=r.d[0];r.d[0]=r.d[1];r.d[1]=value;r.pc=0xe5228;return true; // EXG D0,D1.
    // MOVE.W D0,7c(A0); MOVEA.L (A7)+,A1; MOVE.W D1,7c(A1); CLR.B 62(A6); MOVE.L #e523c,(A6) (then the callback e523c).
    case 0xe5228:
        if(!ov_put(c,r.a[0],0x7c,2,r.d[0]&65535U) || !am_pop(c,4,value))return false;r.a[1]=value;
        if(!ov_put(c,r.a[1],0x7c,2,r.d[1]&65535U))return false;return ov_install_wait(c,0xe523c);
    // CMPI.B #2,62(A6); BEQ e5248.
    case 0xe523c:if(!ov_get(c,r.a[6],0x62,1,value))return false;r.pc=(value&255U)==2U?0xe5248:0xe5246;return true;
    // MOVE.W #14,7a(A6); MOVE.W #19c0,86(A6); MOVE.L #e525a,(A6) (then the callback e525a).
    case 0xe5248:
        if(!ov_put(c,r.a[6],0x7a,2,0x14) || !ov_put(c,r.a[6],0x86,2,0x19c0) || !am_write(c,r.a[6],4,0xe525a))return false;
        r.pc=0xe525a;return true;
    // CMPI.W #19cf,86(A6); BGE e5272 (signed).
    case 0xe525a:if(!ov_get(c,r.a[6],0x86,2,value))return false;r.pc=ov_signed_word(value)>=0x19cf?0xe5272:0xe5264;return true;
    // ADDQ.W #1,86(A6); MOVE.W 86(A6),D0; JSR 3af8.L.
    case 0xe5264:
        if(!ov_get(c,r.a[6],0x86,2,value) || !ov_put(c,r.a[6],0x86,2,(value+1U)&65535U))return false;am_word(r.d[0],value+1U);
        return am_call(c,0x3af8,0xe5272);
    case 0xe5272:return ov_count_down(c,0xe527c,0xe527a);
    case 0xe527c:am_word(r.d[0],0x19c0);return am_call(c,0x3af8,0xe5286); // MOVE.W #19c0,D0; JSR 3af8.L.
    case 0xe5286:return am_call(c,0x48256,0xe528c);                        // JSR 48256.L (boundary without an executor).
    case 0xe528c:r.pc=0x2a00;return true;                            // JMP 2a00.L (self delete).
    case 0xe5670:case 0xe56b0:return ov_signal_parent(c);          // MOVEA.L c(A6),A0; ST.B 62(A0); JMP 2a00.L.

    // ---- e5614 (child callback): MOVE.W #4,2e(A6); MOVE.W #f,32(A6); MOVE.L #e5626,(A6) (then the callback e5626).
    case 0xe5614:
        if(!ov_put(c,r.a[6],0x2e,2,4) || !ov_put(c,r.a[6],0x32,2,0xf) || !am_write(c,r.a[6],4,0xe5626))return false;r.pc=0xe5626;return true;
    case 0xe5626:return ov_print_row(c,0xe4ffc,0xe5644); // ...; LEA e4ffc(PC),A0; LEA e84c8.L,A1; JSR 3a70.L.
    // SUBQ.W #1,32(A6); ...; LEA e4fd8(PC),A0; LEA e84c8.L,A1; JSR 3a70.L.
    case 0xe5644:
        if(!ov_get(c,r.a[6],0x32,2,value) || !ov_put(c,r.a[6],0x32,2,(value-1U)&65535U))return false;return ov_print_row(c,0xe4fd8,0xe5666);
    // CMPI.W #5,32(A6); BNE e567e.
    case 0xe5666:if(!ov_get(c,r.a[6],0x32,2,value))return false;r.pc=(value&65535U)!=5U?0xe567e:0xe5670;return true;

    // ---- e5680 (child callback): MOVE.W #708f,D0; LEA e4fd8(PC),A0; LEA e84c8.L,A1; LEA 10ddfa.L,A3; JSR 3950.L.
    case 0xe5680:am_word(r.d[0],0x708f);r.a[0]=0xe4fd8;r.a[1]=OV_PRINT_TARGET;r.a[3]=OV_RESULT_TEXT;return am_call(c,0x3950,0xe569a);
    case 0xe569a:if(!am_write(c,r.a[6],4,0xe56a0))return false;r.pc=0xe56a0;return true; // MOVE.L #e56a0,(A6).
    case 0xe56a0:r.a[3]=OV_RESULT_TEXT;return am_call(c,0x396e,0xe56ac); // (callback) LEA 10ddfa.L,A3; JSR 396e.L.
    case 0xe56ac:return ov_carry(c,0xe56be,0xe56b0);                     // BCC e56be (carry consumer).

    // ---- e5724 (child callback): four children e579c/e57a4 with angles 0/4000/8000/c000.
    case 0xe5724:return ov_child(c,0xe579c,0xe5734);
    case 0xe5734:if(!ov_put(c,r.a[0],0x7e,2,0))return false;return ov_child(c,0xe57a4,0xe574a); // MOVE.W #0,7e(A0); ...
    case 0xe574a:return ov_mark_child(c,0x4000,0xe579c,0xe5766);
    case 0xe5766:return ov_mark_child(c,0x8000,0xe57a4,0xe5782);
    // MOVE.W #c000,7e(A0); MOVE.W #4000,7e(A6); MOVE.L #e5794,(A6) (then the callback e5794).
    case 0xe5782:
        if(!ov_put(c,r.a[0],0x7e,2,0xc000) || !ov_put(c,r.a[6],0x7e,2,0x4000) || !am_write(c,r.a[6],4,0xe5794))return false;
        r.pc=0xe5794;return true;
    // SUBI.W #100,7e(A6); RTS.
    case 0xe5794:if(!ov_get(c,r.a[6],0x7e,2,value) || !ov_put(c,r.a[6],0x7e,2,(value-0x100U)&65535U))return false;return am_return(c);
    case 0xe579c:am_word(r.d[0],0);r.pc=0xe57a8;return true; // (child callback) MOVE.W #0,D0; BRA e57a8.
    case 0xe57a4:am_word(r.d[0],1);r.pc=0xe57a8;return true; // (child callback) MOVE.W #1,D0.
    // MOVE.W #22b,20(A6); LEA e583c(PC),A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0xe57a8:
        if(!ov_put(c,r.a[6],0x20,2,0x22b))return false;r.a[1]=OV_SEGMENT_TABLE;am_word(r.d[0],(r.d[0]<<2)&65535U);
        if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xe57c4);
    case 0xe57c4:am_word(r.d[0],0x35f);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xe57d2); // MOVE.W #35f,D0; MOVE.B #0,D1; JSR 8ebe.L.
    // CLR.L 2e(A6); MOVE.L #1800000,32(A6); MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.L #e57f0,(A6) (then the callback e57f0).
    case 0xe57d2:
        if(!ov_put(c,r.a[6],0x2e,4,0) || !ov_put(c,r.a[6],0x32,4,0x1800000) || !ov_put(c,r.a[6],0x68,2,0) ||
            !ov_put(c,r.a[6],0x1e,2,0) || !am_write(c,r.a[6],4,0xe57f0))return false;
        r.pc=0xe57f0;return true;
    case 0xe57f0:return am_call(c,0x43e34,0xe57f6); // JSR 43e34.L.
    // MOVEA.L c(A6),A0; MOVE.W 7e(A0),D1; ADD.W 7e(A6),D1; BMI e583a (N = bit 15 of the WORD sum).
    case 0xe57f6:
        if(!ov_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ov_get(c,r.a[0],0x7e,2,value) || !ov_get(c,r.a[6],0x7e,2,other))return false;am_word(r.d[1],value+other);
        r.pc=(r.d[1]&0x8000U)?0xe583a:0xe5806;return true;
    // LSR.W #8,D1; MOVE.W D1,-(A7); MOVE.L #ffff,D0; JSR 443d2.L.
    case 0xe5806:am_word(r.d[1],(r.d[1]&65535U)>>8);if(!am_push(c,2,r.d[1]&65535U))return false;r.d[0]=0xffff;return am_call(c,0x443d2,0xe5816);
    // LSR.W #8,D1; MOVE.B D1,12(A6); MOVE.W (A7)+,D1; MOVE.L #8800,D0; JSR 443d2.L.
    case 0xe5816:
        am_word(r.d[1],(r.d[1]&65535U)>>8);if(!ov_put(c,r.a[6],0x12,1,r.d[1]&255U) || !am_pop(c,2,value))return false;
        am_word(r.d[1],value);r.d[0]=0x8800;return am_call(c,0x443d2,0xe582a);
    // LSR.L #8,D0; ADDI.W #a0,D0; MOVE.W D0,2e(A6); JSR 49fc6.L.
    case 0xe582a:
        r.d[0]>>=8;am_word(r.d[0],r.d[0]+0xa0U);if(!ov_put(c,r.a[6],0x2e,2,r.d[0]&65535U))return false;return am_call(c,0x49fc6,0xe583a);
    default:return am_error(c,"unsupported animation objects u02 PC");
    }
}
}
