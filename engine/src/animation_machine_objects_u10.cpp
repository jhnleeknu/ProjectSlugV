#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code.
const std::uint32_t OU10_BANK_POINTER=0x2001d8; // MOVE.L 2001d8.L,22(A6) (bank window LONG, live bus and live bank_base)
const std::uint32_t OU10_RANGE_RECORD=0xbcb22;  // LEA bcb22.L,A0 (range record passed to 1ab02)
const std::uint32_t OU10_SLOPE_LIST=0xbcb2a;    // LEA bcb2a.L,A1 (passed to the 497b6 boundary)
const std::uint32_t OU10_RECT_IDLE=0xbb598;     // LEA bb598(PC),A0 (passed to 4706c when 7a(A6) = 0)
const std::uint32_t OU10_RECT_BUSY=0xbb5c0;     // LEA bb5c0(PC),A0 (passed to 4706c otherwise)
const std::uint32_t OU10_RECT_CHILD=0xbb55a;    // LEA bb55a(PC),A0 (bb54c)
const std::uint32_t OU10_MARKER=0x10ddec;       // LEA 10ddec.L,A0 (d7834)
bool ou10_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou10_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Two's complement views (explicit, no implementation-defined conversion).
std::int32_t ou10_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
bool ou10_signed_long_le(std::uint32_t a,std::uint32_t b) {
    const std::uint32_t sa=a^0x80000000U,sb=b^0x80000000U;return sa<=sb;
}
// ASR.L #3 (sign fill).
std::uint32_t ou10_asr3(std::uint32_t value) {
    return (value>>3)|((value&0x80000000U)?0xe0000000U:0U);
}
// MOVE.L #callback,(A6), then the installed callback (fall-through).
bool ou10_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// LEA 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1;
// MOVEA.L k(A1),A1; JSR 49f8c.L (banked animation list, two banked LONG reads through the live bus).
bool ou10_animation(AnimationMachineContext& c,std::uint32_t k,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);if(!ou10_put(c,r.a[6],0x20,2,0x213) || !am_read(c,OU10_BANK_POINTER,4,value) ||
       !ou10_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!ou10_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!ou10_get(c,r.a[1],k,4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// ANDI.W #1f,D0; ADDI.W #5a,D0; MOVE.W D0,94(A6) (RNG delay after 49a58).
bool ou10_delay(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;am_word(r.d[0],(r.d[0]&0x1fU)+0x5aU);return ou10_put(c,r.a[6],0x94,2,r.d[0]&65535U);
}
// MOVEA.L #object,A0; MOVE.W #a,D0; JSR 28ae.L (fade_card child creation).
bool ou10_spawn(AnimationMachineContext& c,std::uint32_t object,std::uint32_t return_pc) {
    c.s.a[0]=object;am_word(c.s.d[0],0xa);return am_call(c,0x28ae,return_pc);
}
// MOVE.W #75,D0; MOVE.W #k,D1; MOVE.B #0,D2; JSR c6a96.L (U05 palette reference).
bool ou10_palette(AnimationMachineContext& c,std::uint32_t k,std::uint32_t return_pc) {
    am_word(c.s.d[0],0x75);am_word(c.s.d[1],k);am_byte(c.s.d[2],0);return am_call(c,0xc6a96,return_pc);
}
// TST.W 7a(A6); BNE busy_pc (else idle_pc).
bool ou10_test_7a(AnimationMachineContext& c,std::uint32_t idle_pc,std::uint32_t busy_pc) {
    std::uint32_t value=0;if(!ou10_get(c,c.s.a[6],0x7a,2,value))return false;c.s.pc=value?busy_pc:idle_pc;return true;
}
// Bcc consuming the C returned by the previous callee.
bool ou10_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects u10 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L 36/3a(A6),D3; ASR.L #3,D3; SUB.L D3,36/3a(A6) (velocity decay).
bool ou10_decay(AnimationMachineContext& c,std::uint32_t displacement) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ou10_get(c,r.a[6],displacement,4,value))return false;r.d[3]=ou10_asr3(value);
    if(!ou10_get(c,r.a[6],displacement,4,value))return false;return ou10_put(c,r.a[6],displacement,4,(value-r.d[3])&0xffffffffU);
}
// MOVE.W off(A6),D0; BEQ zero_pc (else next_pc).
bool ou10_word_d0(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ou10_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);
    c.s.pc=value==0U?zero_pc:next_pc;return true;
}
// CMP.W 5418(A5),D0; BCC ge_pc (unsigned D0.W >= WORD; else lt_pc).
bool ou10_cmp_5418(AnimationMachineContext& c,std::uint32_t ge_pc,std::uint32_t lt_pc) {
    std::uint32_t value=0;if(!ou10_get(c,c.s.a[5],0x5418,2,value))return false;
    c.s.pc=(c.s.d[0]&65535U)>=value?ge_pc:lt_pc;return true;
}
// CMPI.W #k,5418(A5); BGE/BLT (signed WORD 5418 >= k -> ge_pc, else lt_pc).
bool ou10_scroll_ge(AnimationMachineContext& c,std::uint32_t k,std::uint32_t ge_pc,std::uint32_t lt_pc) {
    std::uint32_t value=0;if(!ou10_get(c,c.s.a[5],0x5418,2,value))return false;
    c.s.pc=ou10_signed_word(value)>=ou10_signed_word(k)?ge_pc:lt_pc;return true;
}
// MOVE.W #0,off(A6); MOVE.W #mode,86(A6); MOVE.W 46(A6),D0; ADD.W/SUB.W 7e(A6),D0; MOVE.W D0,84(A6).
bool ou10_target(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t mode,bool add) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ou10_put(c,r.a[6],displacement,2,0) || !ou10_put(c,r.a[6],0x86,2,mode) || !ou10_get(c,r.a[6],0x46,2,value))return false;
    am_word(r.d[0],value);if(!ou10_get(c,r.a[6],0x7e,2,value))return false;
    am_word(r.d[0],add?r.d[0]+value:r.d[0]-value);return ou10_put(c,r.a[6],0x84,2,r.d[0]&65535U);
}
// MOVEA.L c(A6),A0; TST.W/CMPI.W of the parent node.
bool ou10_parent(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!ou10_get(c,c.s.a[6],0xc,4,value))return false;c.s.a[0]=value;return true;
}
}
// Objects F4 U10 (223 block starts): the creator callback babb4 (children bb188, bafe6, bb536 through fade_card 28ae) with its
// installed callbacks bac5c/bacbe/bacf2/baec0/baf0e/baf4a, the common tail bafd4 (288c, then 2a00 or RTS), the child callbacks
// bafe6/bb0e4, bb188 (RNG 49a58) with bb1f0/bb2b2/bb2d2/bb300/bb370/bb3fe/bb41e/bb45e/bb520 and bb536/bb546, the callback d7828
// and the sound callback dbdb6 with dbdc6/dbde6/dbe06 and the bare RTS dbe1e. 4be06, 497b6, eb774, 4c266, 1aa40, 492c8 and the
// U08b 4be34 are boundaries without an executor here. 18 blocks read the bank window LONG 2001d8 and the LONG at its value + k
// through the live bus. The 15 lone BCC/BCS blocks consume the C returned by their callee (1ab02, 49fc6, 288c or a boundary).
// U10 writes no port and changes no bank.
bool animation_objects_u10_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- babb4 (callback): three children through 28ae.
    case 0xbabb4:return ou10_spawn(c,0xbb188,0xbabc4);
    case 0xbabc4:return ou10_spawn(c,0xbafe6,0xbabd4);
    case 0xbabd4:return ou10_spawn(c,0xbb536,0xbabe4);
    // MOVE.W 76(A6),D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,88(A6); MOVE.W 7c(A6),D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,8c(A6);
    // MOVE.W #75,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xbabe4:
        if(!ou10_get(c,r.a[6],0x76,2,value))return false;r.d[0]=(am_extend_word(value)<<8)&0xffffffffU;
        if(!ou10_put(c,r.a[6],0x88,4,r.d[0]) || !ou10_get(c,r.a[6],0x7c,2,value))return false;r.d[0]=(am_extend_word(value)<<8)&0xffffffffU;
        if(!ou10_put(c,r.a[6],0x8c,4,r.d[0]))return false;return ou10_palette(c,1,0xbac0e);
    // MOVE.W #0,68(A6); MOVE.W #0,1e(A6); CMPI.W #100,5418(A5); BGE bac28.
    case 0xbac0e:
        if(!ou10_put(c,r.a[6],0x68,2,0) || !ou10_put(c,r.a[6],0x1e,2,0))return false;return ou10_scroll_ge(c,0x100,0xbac28,0xbac24);
    case 0xbac24:case 0xbac7c:r.pc=0xbacbe;return true;                 // BRA bacbe.
    case 0xbac28:return ou10_animation(c,4,0xbac50);
    case 0xbac50:if(!ou10_put(c,r.a[6],0x86,2,0))return false;return ou10_install(c,0xbac5c,0xbac5c); // MOVE.W #0,86(A6); MOVE.L #bac5c,(A6).
    case 0xbac5c:return am_call(c,0x4be06,0xbac62);                     // (callback) JSR 4be06.L (boundary).
    case 0xbac62:r.a[1]=OU10_SLOPE_LIST;return am_call(c,0x497b6,0xbac6e); // LEA bcb2a.L,A1; JSR 497b6.L (boundary).
    case 0xbac6e:return ou10_carry(c,0xbac80,0xbac72);                  // BCC bac80 (C returned by 497b6).
    case 0xbac72:return am_call(c,0xeb774,0xbac78);                     // JSR eb774.L (boundary).
    case 0xbac78:return ou10_carry(c,0xbac80,0xbac7c);                  // BCC bac80 (C returned by eb774).
    case 0xbac80:return am_call(c,0x49fc6,0xbac86);                     // JSR 49fc6.L.
    case 0xbac86:case 0xbae2c:case 0xbaed6:case 0xbaf82:                // LEA bcb22.L,A0; JSR 1ab02.L.
        r.a[0]=OU10_RANGE_RECORD;return am_call(c,0x1ab02,r.pc+12U);
    case 0xbac92:return ou10_carry(c,0xbaca2,0xbac96);                  // BCC baca2 (C returned by 1ab02).
    case 0xbac96:case 0xbae3c:case 0xbaee6:case 0xbaf92:return am_call(c,0x46ef4,r.pc+6U); // JSR 46ef4.L.
    case 0xbac9c:case 0xbae42:case 0xbaeec:case 0xbaf98:case 0xbafde:case 0xdbe16:r.pc=0x2a00;return true; // JMP 2a00.L.
    case 0xbaca2:return ou10_test_7a(c,0xbacaa,0xbacb2);                // TST.W 7a(A6); BNE bacb2.
    case 0xbacaa:r.a[0]=OU10_RECT_IDLE;r.pc=0xbacb6;return true;        // LEA bb598(PC),A0; BRA bacb6.
    case 0xbacb2:r.a[0]=OU10_RECT_BUSY;r.pc=0xbacb6;return true;        // LEA bb5c0(PC),A0.
    case 0xbacb6:case 0xbae68:case 0xbaf06:case 0xbafcc:return am_call(c,0x4706c,r.pc+6U); // JSR 4706c.L (U09).
    case 0xbacbc:case 0xbae6e:case 0xbaf0c:case 0xbafd2:case 0xbafe4:case 0xdbdd4:case 0xdbdf4:case 0xdbe14:case 0xdbe1e:
        return am_return(c);                                            // RTS.

    // ---- bacbe (installed callback): banked animation 4, then MOVE.W #1,86(A6); MOVE.L #bacf2,(A6).
    case 0xbacbe:return ou10_animation(c,4,0xbace6);
    case 0xbace6:if(!ou10_put(c,r.a[6],0x86,2,1))return false;return ou10_install(c,0xbacf2,0xbacf2);
    // (callback) MOVE.W 42(A6),D0; MOVE.L 88(A6),D1; MOVE.W 78(A6),D2; CMP.W D2,D0; BNE bad10.
    case 0xbacf2:
        if(!ou10_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value);
        if(!ou10_get(c,r.a[6],0x88,4,value))return false;r.d[1]=value;
        if(!ou10_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[2],value);
        r.pc=(r.d[0]&65535U)!=(r.d[2]&65535U)?0xbad10:0xbad04;return true;
    case 0xbad04:if(!ou10_put(c,r.a[6],0x36,4,0))return false;r.pc=0xbad2a;return true; // MOVE.L #0,36(A6); BRA bad2a.
    // ADDI.W #fff0,D2; CMP.W D2,D0; BGE bad2a.
    case 0xbad10:
        am_word(r.d[2],r.d[2]+0xfff0U);r.pc=ou10_signed_word(r.d[0])>=ou10_signed_word(r.d[2])?0xbad2a:0xbad1a;return true;
    // CMP.L 36(A6),D1; BLE bad2a (signed LONG D1 <= 36(A6)).
    case 0xbad1a:if(!ou10_get(c,r.a[6],0x36,4,value))return false;r.pc=ou10_signed_long_le(r.d[1],value)?0xbad2a:0xbad22;return true;
    case 0xbad22:                                                        // ADDI.L #18000,36(A6).
        if(!ou10_get(c,r.a[6],0x36,4,value) || !ou10_put(c,r.a[6],0x36,4,(value+0x18000U)&0xffffffffU))return false;r.pc=0xbad2a;return true;
    // MOVE.L 36(A6),D3; ASR.L #3,D3; SUB.L D3,36(A6); CMPI.W #1,86(A6); BEQ bad92.
    case 0xbad2a:
        if(!ou10_decay(c,0x36) || !ou10_get(c,r.a[6],0x86,2,value))return false;r.pc=value==1U?0xbad92:0xbad3e;return true;
    // MOVE.W 46(A6),D0; MOVE.L 8c(A6),D1; MOVE.W 84(A6),D2; CMP.W D2,D0; BNE bad62.
    case 0xbad3e:
        if(!ou10_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],value);
        if(!ou10_get(c,r.a[6],0x8c,4,value))return false;r.d[1]=value;
        if(!ou10_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[2],value);
        r.pc=(r.d[0]&65535U)!=(r.d[2]&65535U)?0xbad62:0xbad50;return true;
    // MOVE.L #0,3a(A6); MOVE.W #1,86(A6); BRA bad6c.
    case 0xbad50:if(!ou10_put(c,r.a[6],0x3a,4,0) || !ou10_put(c,r.a[6],0x86,2,1))return false;r.pc=0xbad6c;return true;
    case 0xbad62:if(!ou10_decay(c,0x3a))return false;r.pc=0xbad6c;return true;
    // MOVE.W 84(A6),D2; ADDI.W #fff0,D2; CMP.W D2,D0; BGE bad7e.
    case 0xbad6c:
        if(!ou10_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[2],value+0xfff0U);
        r.pc=ou10_signed_word(r.d[0])>=ou10_signed_word(r.d[2])?0xbad7e:0xbad7a;return true;
    case 0xbad7a:if(!ou10_put(c,r.a[6],0x3a,4,r.d[1]))return false;r.pc=0xbad7e;return true; // MOVE.L D1,3a(A6).
    // MOVE.W 84(A6),D2; ADDI.W #10,D2; CMP.W D2,D0; BLE bad92.
    case 0xbad7e:
        if(!ou10_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[2],value+0x10U);
        r.pc=ou10_signed_word(r.d[0])<=ou10_signed_word(r.d[2])?0xbad92:0xbad8c;return true;
    case 0xbad8c:r.d[1]=(0U-r.d[1])&0xffffffffU;if(!ou10_put(c,r.a[6],0x3a,4,r.d[1]))return false;r.pc=0xbad92;return true; // NEG.L; MOVE.L.
    case 0xbad92:return am_call(c,0x4be34,0xbad98);                     // JSR 4be34.L (U08b boundary).
    case 0xbad98:return ou10_word_d0(c,0x7a,0xbadb0,0xbada0);          // MOVE.W 7a(A6),D0; BEQ badb0.
    case 0xbada0:return ou10_cmp_5418(c,0xbadac,0xbada8);              // CMP.W 5418(A5),D0; BCC badac.
    case 0xbada8:case 0xbadc2:r.pc=0xbae70;return true;                 // BRA bae70.
    case 0xbadac:r.pc=0xbadc6;return true;                              // BRA badc6.
    case 0xbadb0:am_word(r.d[0],0x70);am_word(r.d[1],0x20);return am_call(c,0x4c266,0xbadbe); // MOVE.W #70,D0; MOVE.W #20,D1; JSR 4c266.L.
    case 0xbadbe:return ou10_carry(c,0xbadc6,0xbadc2);                  // BCC badc6 (C returned by 4c266).
    case 0xbadc6:return ou10_word_d0(c,0x80,0xbadee,0xbadce);          // MOVE.W 80(A6),D0; BEQ badee.
    case 0xbadce:return ou10_cmp_5418(c,0xbadee,0xbadd6);              // CMP.W 5418(A5),D0; BCC badee.
    case 0xbadd6:if(!ou10_target(c,0x80,4,true))return false;r.pc=0xbadee;return true;
    case 0xbadee:return ou10_word_d0(c,0x82,0xbae16,0xbadf6);          // MOVE.W 82(A6),D0; BEQ bae16.
    case 0xbadf6:return ou10_cmp_5418(c,0xbae16,0xbadfe);              // CMP.W 5418(A5),D0; BCC bae16.
    case 0xbadfe:if(!ou10_target(c,0x82,5,false))return false;r.pc=0xbae16;return true;
    case 0xbae16:return ou10_scroll_ge(c,0x1130,0xbae20,0xbae26);      // CMPI.W #1130,5418(A5); BLT bae26.
    case 0xbae20:if(!ou10_put(c,r.a[6],0x78,2,0x140))return false;r.pc=0xbae26;return true; // MOVE.W #140,78(A6).
    case 0xbae26:case 0xbaec6:case 0xbaf50:case 0xbb0ea:case 0xbb20c:case 0xbb2be:case 0xbb338:case 0xbb39a:case 0xbb40a:
    case 0xbb47a:case 0xbb52c:return am_call(c,0x49fc6,r.pc+6U);       // JSR 49fc6.L.
    case 0xbae38:return ou10_carry(c,0xbae48,0xbae3c);                  // BCC bae48 (C returned by 1ab02).
    // MOVE.W 46(A6),D0; SUBI.W #140,D0; MOVE.W D0,5432(A5); TST.W 7a(A6); BNE bae64.
    case 0xbae48:
        if(!ou10_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],value-0x140U);
        if(!ou10_put(c,r.a[5],0x5432,2,r.d[0]&65535U))return false;return ou10_test_7a(c,0xbae5c,0xbae64);
    case 0xbae5c:r.a[0]=OU10_RECT_IDLE;r.pc=0xbae68;return true;        // LEA bb598(PC),A0; BRA bae68.
    case 0xbae64:r.a[0]=OU10_RECT_BUSY;r.pc=0xbae68;return true;        // LEA bb5c0(PC),A0.

    // ---- bae70: TST.W 7a(A6); BNE bae86.
    case 0xbae70:return ou10_test_7a(c,0xbae78,0xbae86);
    case 0xbae78:r.d[0]=0;r.d[1]=0;return am_call(c,0x1aa40,0xbae82);  // CLR.L D0; CLR.L D1; JSR 1aa40.L (boundary).
    case 0xbae82:r.pc=0xbae8c;return true;                              // BRA bae8c.
    case 0xbae86:if(!ou10_put(c,r.a[5],0x5432,2,0xfff0))return false;r.pc=0xbae8c;return true; // MOVE.W #fff0,5432(A5).
    case 0xbae8c:if(!ou10_put(c,r.a[6],0x86,2,2))return false;return ou10_animation(c,0xc,0xbaeba); // MOVE.W #2,86(A6); (animation c).
    case 0xbaeba:return ou10_install(c,0xbaec0,0xbaec0);                // MOVE.L #baec0,(A6).
    case 0xbaec0:case 0xbaf4a:return am_call(c,0x4be06,r.pc+6U);       // (callback) JSR 4be06.L (boundary).
    case 0xbaecc:return ou10_carry(c,0xbaed6,0xbaed0);                  // BCC baed6 (C returned by 49fc6).
    case 0xbaed0:return ou10_install(c,0xbaf0e,0xbaed6);                // MOVE.L #baf0e,(A6).
    case 0xbaee2:return ou10_carry(c,0xbaef2,0xbaee6);                  // BCC baef2 (C returned by 1ab02).
    case 0xbaef2:return ou10_test_7a(c,0xbaefa,0xbaf02);                // TST.W 7a(A6); BNE baf02.
    case 0xbaefa:r.a[0]=OU10_RECT_IDLE;r.pc=0xbaf06;return true;        // LEA bb598(PC),A0; BRA baf06.
    case 0xbaf02:r.a[0]=OU10_RECT_BUSY;r.pc=0xbaf06;return true;        // LEA bb5c0(PC),A0.

    // ---- baf0e (installed callback): banked animation 10; MOVE.W 5418(A5),94(A6); CLR.L 36(A6); CLR.L 3a(A6); MOVE.L #baf4a,(A6).
    case 0xbaf0e:return ou10_animation(c,0x10,0xbaf36);
    case 0xbaf36:
        if(!ou10_get(c,r.a[5],0x5418,2,value) || !ou10_put(c,r.a[6],0x94,2,value) || !ou10_put(c,r.a[6],0x36,4,0) ||
           !ou10_put(c,r.a[6],0x3a,4,0))return false;
        return ou10_install(c,0xbaf4a,0xbaf4a);
    case 0xbaf56:return ou10_carry(c,0xbaf82,0xbaf5a);                  // BCC baf82 (C returned by 49fc6).
    case 0xbaf5a:return ou10_animation(c,4,0xbaf82);
    case 0xbaf8e:return ou10_carry(c,0xbaf9e,0xbaf92);                  // BCC baf9e (C returned by 1ab02).
    case 0xbaf9e:return ou10_test_7a(c,0xbafa6,0xbafb8);                // TST.W 7a(A6); BNE bafb8.
    // MOVE.W 94(A6),D0; CMP.W 5418(A5),D0; BEQ bafb8.
    case 0xbafa6:
        if(!ou10_get(c,r.a[6],0x94,2,value))return false;am_word(r.d[0],value);
        if(!ou10_get(c,r.a[5],0x5418,2,value))return false;r.pc=(r.d[0]&65535U)==value?0xbafb8:0xbafb2;return true;
    case 0xbafb2:return ou10_install(c,0xbacbe,0xbafb8);                // MOVE.L #bacbe,(A6).
    case 0xbafb8:return ou10_test_7a(c,0xbafc0,0xbafc8);                // TST.W 7a(A6); BNE bafc8.
    case 0xbafc0:r.a[0]=OU10_RECT_IDLE;r.pc=0xbafcc;return true;        // LEA bb598(PC),A0; BRA bafcc.
    case 0xbafc8:r.a[0]=OU10_RECT_BUSY;r.pc=0xbafcc;return true;        // LEA bb5c0(PC),A0.

    // ---- bafd4 (common tail): JSR 288c.L; BCS bafe4; JMP 2a00.L; RTS.
    case 0xbafd4:return am_call(c,0x288c,0xbafda);
    case 0xbafda:return ou10_carry(c,0xbafde,0xbafe4);                  // BCS bafe4 (C returned by 288c).

    // ---- bafe6 (callback): MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L.
    case 0xbafe6:case 0xbb536:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,r.pc+10U);
    // MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.W #75,D0; MOVE.W #6,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xbaff0:if(!ou10_put(c,r.a[6],0x68,2,0) || !ou10_put(c,r.a[6],0x1e,2,0))return false;return ou10_palette(c,6,0xbb00e);
    case 0xbb00e:r.pc=0xbb0b6;return true;                              // BRA bb0b6.
    case 0xbb0b6:return ou10_animation(c,0x18,0xbb0de);
    case 0xbb0de:return ou10_install(c,0xbb0e4,0xbb0e4);                // MOVE.L #bb0e4,(A6).
    case 0xbb0e4:case 0xbb200:case 0xbb2b2:case 0xbb32c:case 0xbb38e:case 0xbb3fe:case 0xbb46e:case 0xbb520:case 0xbb546:
        return am_call(c,0x43e34,r.pc+6U);                              // (callbacks) JSR 43e34.L.
    case 0xbb0f0:case 0xbb280:case 0xbb2ce:case 0xbb33e:case 0xbb3cc:case 0xbb41a:case 0xbb4ee:case 0xbb532:case 0xbb556:
        r.pc=0xbafd4;return true;                                       // BRA bafd4.

    // ---- bb188 (callback): MOVE.W #75,D0; MOVE.W #19,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xbb188:return ou10_palette(c,0x19,0xbb19a);
    // MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L.
    case 0xbb19a:
        if(!ou10_put(c,r.a[6],0x68,2,0x8820) || !ou10_put(c,r.a[6],0x1e,2,0x8820))return false;r.d[0]=0;r.d[1]=0;
        return am_call(c,0x49290,0xbb1b0);
    case 0xbb1b0:return ou10_animation(c,0x64,0xbb1d8);
    case 0xbb1d8:case 0xbb246:case 0xbb446:case 0xbb4b4:return am_call(c,0x49a58,r.pc+6U); // JSR 49a58.L (RNG).
    case 0xbb1de:if(!ou10_delay(c))return false;return ou10_install(c,0xbb1f0,0xbb1f0);  // (delay); MOVE.L #bb1f0,(A6).
    case 0xbb44c:if(!ou10_delay(c))return false;return ou10_install(c,0xbb45e,0xbb45e);  // (delay); MOVE.L #bb45e,(A6).
    // (callbacks bb1f0/bb45e) MOVEA.L c(A6),A0; TST.W 36(A0); BEQ bb200/bb46e.
    case 0xbb1f0:case 0xbb45e:
        if(!ou10_parent(c) || !ou10_get(c,r.a[0],0x36,2,value))return false;
        r.pc=value==0U?(r.pc==0xbb1f0?0xbb200:0xbb46e):(r.pc==0xbb1f0?0xbb1fc:0xbb46a);return true;
    case 0xbb1fc:case 0xbb46a:r.pc=0xbb284;return true;                 // BRA bb284.
    case 0xbb206:case 0xbb2b8:case 0xbb332:case 0xbb394:case 0xbb404:case 0xbb474:case 0xbb526:return am_call(c,0x492c8,r.pc+6U); // JSR 492c8.L (boundary).
    case 0xbb212:return ou10_carry(c,0xbb23e,0xbb216);                  // BCC bb23e (C returned by 49fc6).
    case 0xbb216:case 0xbb484:return ou10_animation(c,0x64,r.pc==0xbb216?0xbb23e:0xbb4ac);
    // SUBQ.W #1,94(A6); BGE bb280/bb4ee (signed WORD before the decrement >= 1).
    case 0xbb23e:case 0xbb4ac:
        if(!ou10_get(c,r.a[6],0x94,2,value) || !ou10_put(c,r.a[6],0x94,2,(value-1U)&65535U))return false;
        r.pc=ou10_signed_word(value)>=1?(r.pc==0xbb23e?0xbb280:0xbb4ee):(r.pc==0xbb23e?0xbb246:0xbb4b4);return true;
    case 0xbb24c:case 0xbb4ba:if(!ou10_delay(c))return false;return ou10_animation(c,0x68,r.pc==0xbb24c?0xbb280:0xbb4ee);
    case 0xbb284:return ou10_animation(c,0x6c,0xbb2ac);
    case 0xbb2ac:return ou10_install(c,0xbb2b2,0xbb2b2);                // MOVE.L #bb2b2,(A6).
    case 0xbb2c4:return ou10_carry(c,0xbb2ce,0xbb2c8);                  // BCC bb2ce (C returned by 49fc6).
    case 0xbb2c8:return ou10_install(c,0xbb2d2,0xbb2ce);                // MOVE.L #bb2d2,(A6).
    case 0xbb2d2:return ou10_animation(c,0x54,0xbb2fa);
    case 0xbb2fa:return ou10_install(c,0xbb300,0xbb300);                // MOVE.L #bb300,(A6).
    // (callbacks bb300/bb370) MOVEA.L c(A6),A0; CMPI.W #2,86(A0); BNE bb312/bb382.
    case 0xbb300:case 0xbb370:
        if(!ou10_parent(c) || !ou10_get(c,r.a[0],0x86,2,value))return false;
        r.pc=value!=2U?(r.pc==0xbb300?0xbb312:0xbb382):(r.pc==0xbb300?0xbb30e:0xbb37e);return true;
    case 0xbb30e:case 0xbb37e:r.pc=0xbb3d0;return true;                 // BRA bb3d0.
    case 0xbb312:if(!ou10_get(c,r.a[0],0x3a,2,value))return false;r.pc=value==0U?0xbb31e:0xbb31a;return true; // TST.W 3a(A0); BEQ bb31e.
    case 0xbb31a:r.pc=0xbb342;return true;                              // BRA bb342.
    case 0xbb31e:return ou10_scroll_ge(c,0x1120,0xbb328,0xbb32c);      // CMPI.W #1120,5418(A5); BLT bb32c.
    case 0xbb328:r.pc=0xbb4f2;return true;                              // BRA bb4f2.
    case 0xbb342:return ou10_animation(c,0x5c,0xbb36a);
    case 0xbb36a:return ou10_install(c,0xbb370,0xbb370);                // MOVE.L #bb370,(A6).
    case 0xbb382:if(!ou10_get(c,r.a[0],0x3a,2,value))return false;r.pc=value!=0U?0xbb38e:0xbb38a;return true; // TST.W 3a(A0); BNE bb38e.
    case 0xbb38a:r.pc=0xbb2d2;return true;                              // BRA bb2d2.
    case 0xbb3a0:return ou10_carry(c,0xbb3cc,0xbb3a4);                  // BCC bb3cc (C returned by 49fc6).
    case 0xbb3a4:return ou10_animation(c,0x5c,0xbb3cc);
    case 0xbb3d0:return ou10_animation(c,0x60,0xbb3f8);
    case 0xbb3f8:return ou10_install(c,0xbb3fe,0xbb3fe);                // MOVE.L #bb3fe,(A6).
    case 0xbb410:return ou10_carry(c,0xbb41a,0xbb414);                  // BCC bb41a (C returned by 49fc6).
    case 0xbb414:return ou10_install(c,0xbb41e,0xbb41a);                // MOVE.L #bb41e,(A6).
    case 0xbb41e:return ou10_animation(c,0x64,0xbb446);
    case 0xbb480:return ou10_carry(c,0xbb4ac,0xbb484);                  // BCC bb4ac (C returned by 49fc6).
    case 0xbb4f2:return ou10_animation(c,0x58,0xbb51a);
    case 0xbb51a:return ou10_install(c,0xbb520,0xbb520);                // MOVE.L #bb520,(A6).

    // ---- bb536 (callback, MOVEQ/MOVEQ/JSR 49290 above); MOVE.L #bb546,(A6).
    case 0xbb540:return ou10_install(c,0xbb546,0xbb546);
    case 0xbb54c:r.a[0]=OU10_RECT_CHILD;return am_call(c,0x4706c,0xbb556); // LEA bb55a(PC),A0; JSR 4706c.L.

    // ---- d7828 (callback): TST.B 78(A6); BEQ d7834.
    case 0xd7828:if(!ou10_get(c,r.a[6],0x78,1,value))return false;r.pc=value==0U?0xd7834:0xd7830;return true;
    case 0xd7830:if(!ou10_put(c,r.a[5],0x5df8,2,0))return false;r.pc=0xd7834;return true; // CLR.W 5df8(A5).
    // LEA 10ddec.L,A0; MOVE.B 76(A6),D0; BEQ d7846.
    case 0xd7834:
        r.a[0]=OU10_MARKER;if(!ou10_get(c,r.a[6],0x76,1,value))return false;am_byte(r.d[0],value);
        r.pc=value==0U?0xd7846:0xd7842;return true;
    case 0xd7842:r.a[0]=am_index(r.a[0],6);r.pc=0xd7846;return true;   // ADDA.W #6,A0.
    // MOVEQ #0,D0; MOVE.B 77(A6),D0; CMPI.W #f,D0; BCS d7856.
    case 0xd7846:r.d[0]=0;if(!ou10_get(c,r.a[6],0x77,1,value))return false;am_byte(r.d[0],value);r.pc=value<0xfU?0xd7856:0xd7854;return true;
    case 0xd7854:r.d[0]=0;r.pc=0xd7856;return true;                     // MOVEQ #0,D0.
    // MOVE.W D0,(A0); MOVE.W 42(A6),D0; CMPI.W #140,D0; BCS d7868.
    case 0xd7856:
        if(!am_write(c,r.a[0],2,r.d[0]&65535U) || !ou10_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value);
        r.pc=value<0x140U?0xd7868:0xd7864;return true;
    case 0xd7864:am_word(r.d[0],0x108);r.pc=0xd7868;return true;        // MOVE.W #108,D0.
    // MOVE.W D0,2(A0); MOVE.W 46(A6),D0; MOVE.W D0,D1; SUBI.W #100,D1; CMPI.W #100,D1; BCS d7882.
    case 0xd7868:
        if(!ou10_put(c,r.a[0],2,2,r.d[0]&65535U) || !ou10_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],value);
        am_word(r.d[1],value-0x100U);r.pc=(r.d[1]&65535U)<0x100U?0xd7882:0xd787e;return true;
    case 0xd787e:am_word(r.d[0],0x1a0);r.pc=0xd7882;return true;        // MOVE.W #1a0,D0.
    case 0xd7882:if(!ou10_put(c,r.a[0],4,2,r.d[0]&65535U))return false;r.pc=0x2a00;return true; // MOVE.W D0,4(A0); JMP 2a00.L.

    // ---- dbdb6 (callback): MOVE.W #730,D0; JSR 3af8.L; MOVE.L #dbdc6,(A6); (callbacks dbdc6/dbde6/dbe06) JSR dbe1e(PC);
    // CMPI.W #k,5418(A5); BGE next stage (else RTS).
    case 0xdbdb6:case 0xdbdf6:am_word(r.d[0],0x730);return am_call(c,0x3af8,r.pc+10U);
    case 0xdbdd6:am_word(r.d[0],0x742);return am_call(c,0x3af8,0xdbde0);
    case 0xdbdc0:return ou10_install(c,0xdbdc6,0xdbdc6);
    case 0xdbde0:return ou10_install(c,0xdbde6,0xdbde6);
    case 0xdbe00:return ou10_install(c,0xdbe06,0xdbe06);
    case 0xdbdc6:case 0xdbde6:case 0xdbe06:return am_call(c,0xdbe1e,r.pc+4U);
    case 0xdbdca:return ou10_scroll_ge(c,0x850,0xdbdd6,0xdbdd4);
    case 0xdbdea:return ou10_scroll_ge(c,0xa00,0xdbdf6,0xdbdf4);
    case 0xdbe0a:return ou10_scroll_ge(c,0x1100,0xdbe16,0xdbe14);
    default:return am_error(c,"unsupported animation objects u10 PC");
    }
}
}
