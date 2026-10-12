#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code.
const std::uint32_t OU20B_BANK_ANIMATION=0x2000e0;  // MOVE.L 2000e0.L,22(A6) (banked window LONG, live bus).
const std::uint32_t OU20B_PALETTE_TABLE=0x84976;    // LEA 84976(PC),A0: fixed ROM WORD table (live bus).
const std::uint32_t OU20B_RANGE_RECORD=0x84982;     // LEA 84982(PC),A0: two LONGs read by 1ab02.
const std::uint32_t OU20B_CHILD=0x85c6c;            // MOVEA.L #85c6c,A0 (28ae child callback; written only).
const std::uint32_t OU20B_TAIL=0x849f4;             // shared tail (BRA.W 849f4).
bool ou20b_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool ou20b_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Signed LONG / WORD order through the sign-flipped unsigned values.
bool ou20b_le(std::uint32_t a,std::uint32_t b) {return (a^0x80000000U)<=(b^0x80000000U);}
bool ou20b_ge(std::uint32_t a,std::uint32_t b) {return (a^0x80000000U)>=(b^0x80000000U);}
bool ou20b_word_ge(std::uint32_t a,std::uint32_t b) {return ((a&65535U)^0x8000U)>=((b&65535U)^0x8000U);}
// Bcc consuming the C returned by a callee: BCC taken when C is clear.
bool ou20b_bcc(AnimationMachineContext& c,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u20b caller requires known carry");
    r.pc=r.carry==AnimationCarryClear?taken_pc:next_pc;return true;
}
// MOVE.L #callback,(A6) then continue at next_pc.
bool ou20b_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// BTST.B #bit,15(A6): true when the bit is set.
bool ou20b_bit15(AnimationMachineContext& c,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ou20b_get(c,0x15,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// NEG.L d16(A6).
bool ou20b_neg(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ou20b_get(c,displacement,4,value) || !ou20b_put(c,displacement,4,(0U-value)&0xffffffffU))return false;
    c.s.pc=next_pc;return true;
}
// MOVE.L #value,d16(A6).
bool ou20b_long(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,std::uint32_t next_pc) {
    if(!ou20b_put(c,displacement,4,value))return false;c.s.pc=next_pc;return true;
}
// ADD.L D0,d16(A6).
bool ou20b_add_d0(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ou20b_get(c,displacement,4,value) || !ou20b_put(c,displacement,4,(value+c.s.d[0])&0xffffffffU))return false;
    c.s.pc=next_pc;return true;
}
// CMPI.L #limit,d16(A6); BLE.W (taken when the LONG <= limit, signed) / BGE.W (taken when >= limit, signed).
bool ou20b_limit(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t limit,bool less_equal,std::uint32_t taken_pc,
    std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ou20b_get(c,displacement,4,value))return false;
    c.s.pc=(less_equal?ou20b_le(value,limit):ou20b_ge(value,limit))?taken_pc:next_pc;return true;
}
// MOVE.W d16(A6),D0; CMP.W d16(A6),D0; BCC.W (taken when D0.W >= bound unsigned) / BCS.W (taken when D0.W < bound unsigned).
bool ou20b_bound(AnimationMachineContext& c,std::uint32_t position,std::uint32_t bound,bool carry_clear_taken,std::uint32_t taken_pc,
    std::uint32_t next_pc) {
    std::uint32_t value=0,limit=0;
    if(!ou20b_get(c,position,2,value) || !ou20b_get(c,bound,2,limit))return false;am_word(c.s.d[0],value);
    const bool below=value<limit;c.s.pc=(carry_clear_taken?!below:below)?taken_pc:next_pc;return true;
}
// MOVE.L d16(A6),D0; CMPI.L #0,D0; BGE.W taken_pc.
bool ou20b_speed(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t taken_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ou20b_get(c,displacement,4,value))return false;c.s.d[0]=value;
    c.s.pc=(value&0x80000000U)==0U?taken_pc:next_pc;return true;
}
// SUBQ.W #1,76(A6); BNE.W taken_pc.
bool ou20b_count(AnimationMachineContext& c,std::uint32_t taken_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ou20b_get(c,0x76,2,value))return false;value=(value-1U)&65535U;
    if(!ou20b_put(c,0x76,2,value))return false;c.s.pc=value!=0U?taken_pc:next_pc;return true;
}
// CMPI.W #a0,42(A6); BGE.W taken_pc (signed WORD).
bool ou20b_side(AnimationMachineContext& c,std::uint32_t taken_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ou20b_get(c,0x42,2,value))return false;c.s.pc=ou20b_word_ge(value,0xa0)?taken_pc:next_pc;return true;
}
// LEA 26(A6),A0; MOVE.W #23,20(A6); MOVE.L 2000e0.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1;
// JSR 49f8c.L.
bool ou20b_animation(AnimationMachineContext& c,std::uint32_t offset,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!ou20b_put(c,0x20,2,0x23) || !am_read(c,OU20B_BANK_ANIMATION,4,value) || !ou20b_put(c,0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!ou20b_get(c,0x22,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],offset),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// BTST.B #7,15(A6); BNE.W set_pc (otherwise next_pc).
bool ou20b_air(AnimationMachineContext& c,std::uint32_t set_pc,std::uint32_t next_pc) {
    bool set=false;if(!ou20b_bit15(c,7,set))return false;c.s.pc=set?set_pc:next_pc;return true;
}
}
// Objects F4 U20b (92 block starts, rescope N02): the node callback 858d8 (screen limits 7c/7e/80/82, U20a 497a6 for the palette
// index 7a, fixed WORD table 84976 for U02 8ebe, child 85c6c through fade_card 28ae when 78 is 0), its installed callbacks 859b2
// (bounded speeds 84/88 into 36/3a, U04 43ea4, interpreter 49fc6), 85aa4/85af8, 85b6c, 85b9e/85bcc (U20a 492d0 after the C
// returned by 49fc6), 85c04/85c48 (U18 4be2c, U11 4be06, U17 4bfa4), the banked animation LONG 2000e0 for the interpreter 49f8c,
// and the shared tail 849f4 (U05 1ab02 with the fixed record 84982; C clear: RTS, C set: BSET #7,61, CLR.W 54, fade_card 2a00).
// U20b writes no port, changes no bank and has no boundary without an executor; the child callback 85c6c is written only.
bool animation_objects_u20b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool flag=false;
    switch(r.pc) {
    // ---- 849f4 shared tail: LEA 84982(PC),A0; JSR 1ab02.L.
    case 0x849f4:r.a[0]=OU20B_RANGE_RECORD;return am_call(c,0x1ab02,0x849fe);
    case 0x849fe:return ou20b_bcc(c,0x84a12,0x84a02);                        // BCC.W 84a12 (C returned by 1ab02).
    // BSET.B #7,61(A6); CLR.W 54(A6); JMP 2a00.L.
    case 0x84a02:
        if(!ou20b_get(c,0x61,1,value) || !ou20b_put(c,0x61,1,(value|0x80U)&255U) || !ou20b_put(c,0x54,2,0))return false;r.pc=0x2a00;return true;
    case 0x84a12:return am_return(c);                                          // RTS.

    // ---- 858d8 (callback): CMPI.W #a0,42(A6); BGE.W 858f2.
    case 0x858d8:return ou20b_side(c,0x858f2,0x858e2);
    // MOVE.W #40,7e(A6); MOVE.W #ffc0,7c(A6); BRA.W 858fe.
    case 0x858e2:if(!ou20b_put(c,0x7e,2,0x40) || !ou20b_put(c,0x7c,2,0xffc0))return false;r.pc=0x858fe;return true;
    // MOVE.W #100,7c(A6); MOVE.W #100,7e(A6).
    case 0x858f2:if(!ou20b_put(c,0x7c,2,0x100) || !ou20b_put(c,0x7e,2,0x100))return false;r.pc=0x858fe;return true;
    // MOVE.W 46(A6),D0; MOVE.W D0,80(A6); MOVE.W 46(A6),D0; MOVE.W D0,82(A6); MOVE.L #ffff8000,84(A6); MOVE.L #ffff8000,88(A6);
    // TST.W 7a(A6); BNE.W 85936.
    case 0x858fe:
        if(!ou20b_get(c,0x46,2,value))return false;am_word(r.d[0],value);if(!ou20b_put(c,0x80,2,value))return false;
        if(!ou20b_get(c,0x46,2,value))return false;am_word(r.d[0],value);
        if(!ou20b_put(c,0x82,2,value) || !ou20b_put(c,0x84,4,0xffff8000U) || !ou20b_put(c,0x88,4,0xffff8000U) || !ou20b_get(c,0x7a,2,value))
            return false;
        r.pc=value!=0U?0x85936:0x85926;return true;
    case 0x85926:return am_call(c,0x497a6,0x8592c);                            // JSR 497a6.L.
    case 0x8592c:return ou20b_bcc(c,0x85936,0x85930);                         // BCC.W 85936 (C returned by 497a6).
    case 0x85930:if(!ou20b_put(c,0x7a,2,5))return false;r.pc=0x85936;return true; // MOVE.W #5,7a(A6).
    // MOVE.W 7a(A6),D0; LEA 84976(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0x85936:
        if(!ou20b_get(c,0x7a,2,value))return false;am_word(r.d[0],(value<<1)&65535U);r.a[0]=OU20B_PALETTE_TABLE;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x8594e);
    // BSET.B #6,15(A6); MOVE.W #8800,68(A6); MOVE.W #8800,1e(A6); TST.W 78(A6); BNE.W 85980.
    case 0x8594e:
        if(!ou20b_get(c,0x15,1,value) || !ou20b_put(c,0x15,1,(value|0x40U)&255U) || !ou20b_put(c,0x68,2,0x8800) || !ou20b_put(c,0x1e,2,0x8800) ||
           !ou20b_get(c,0x78,2,value))return false;
        r.pc=value!=0U?0x85980:0x85968;return true;
    // MOVEA.L #85c6c,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0x85968:r.a[0]=OU20B_CHILD;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x85978);
    case 0x85978:r.pc=0x85984;return true;                                    // BRA.W 85984.
    case 0x85980:r.pc=0x85b3e;return true;                                    // BRA.W 85b3e.
    case 0x85984:return ou20b_animation(c,0x5c,0x859ac);
    case 0x859ac:return ou20b_install(c,0x859b2,0x859b2);                     // MOVE.L #859b2,(A6).

    // ---- 859b2 (installed callback): MOVE.L 84(A6),D0; CMPI.L #0,D0; BGE.W 859f0.
    case 0x859b2:return ou20b_speed(c,0x84,0x859f0,0x859c0);
    case 0x859c0:return ou20b_limit(c,0x36,0xfffc0000U,true,0x859d4,0x859cc); // CMPI.L #fffc0000,36(A6); BLE.W 859d4.
    case 0x859cc:return ou20b_add_d0(c,0x36,0x859dc);                         // ADD.L D0,36(A6); BRA.W 859dc.
    case 0x859d4:return ou20b_long(c,0x36,0xfffc0000U,0x859dc);               // MOVE.L #fffc0000,36(A6).
    case 0x859dc:return ou20b_bound(c,0x42,0x7c,true,0x859ec,0x859e8);       // MOVE.W 42(A6),D0; CMP.W 7c(A6),D0; BCC.W 859ec.
    case 0x859e8:return ou20b_neg(c,0x84,0x859ec);                            // NEG.L 84(A6).
    case 0x859ec:r.pc=0x85a1c;return true;                                    // BRA.W 85a1c.
    case 0x859f0:return ou20b_limit(c,0x36,0x40000U,false,0x85a04,0x859fc);   // CMPI.L #40000,36(A6); BGE.W 85a04.
    case 0x859fc:return ou20b_add_d0(c,0x36,0x85a0c);                         // ADD.L D0,36(A6); BRA.W 85a0c.
    case 0x85a04:return ou20b_long(c,0x36,0x40000U,0x85a0c);                  // MOVE.L #40000,36(A6).
    case 0x85a0c:return ou20b_bound(c,0x42,0x7e,false,0x85a1c,0x85a18);      // MOVE.W 42(A6),D0; CMP.W 7e(A6),D0; BCS.W 85a1c.
    case 0x85a18:return ou20b_neg(c,0x84,0x85a1c);                            // NEG.L 84(A6).
    case 0x85a1c:return ou20b_speed(c,0x88,0x85a5a,0x85a2a);                  // MOVE.L 88(A6),D0; CMPI.L #0,D0; BGE.W 85a5a.
    case 0x85a2a:return ou20b_limit(c,0x3a,0xffff0000U,true,0x85a3e,0x85a36); // CMPI.L #ffff0000,3a(A6); BLE.W 85a3e.
    case 0x85a36:return ou20b_add_d0(c,0x3a,0x85a46);                         // ADD.L D0,3a(A6); BRA.W 85a46.
    case 0x85a3e:return ou20b_long(c,0x3a,0xffff0000U,0x85a46);               // MOVE.L #ffff0000,3a(A6).
    case 0x85a46:return ou20b_bound(c,0x46,0x82,true,0x85a56,0x85a52);       // MOVE.W 46(A6),D0; CMP.W 82(A6),D0; BCC.W 85a56.
    case 0x85a52:return ou20b_neg(c,0x88,0x85a56);                            // NEG.L 88(A6).
    case 0x85a56:r.pc=0x85a86;return true;                                    // BRA.W 85a86.
    case 0x85a5a:return ou20b_limit(c,0x3a,0x10000U,false,0x85a6e,0x85a66);   // CMPI.L #10000,3a(A6); BGE.W 85a6e.
    case 0x85a66:return ou20b_add_d0(c,0x3a,0x85a76);                         // ADD.L D0,3a(A6); BRA.W 85a76.
    case 0x85a6e:return ou20b_long(c,0x3a,0x10000U,0x85a76);                  // MOVE.L #10000,3a(A6).
    case 0x85a76:return ou20b_bound(c,0x46,0x80,false,0x85a86,0x85a82);      // MOVE.W 46(A6),D0; CMP.W 80(A6),D0; BCS.W 85a86.
    case 0x85a82:return ou20b_neg(c,0x88,0x85a86);                            // NEG.L 88(A6).
    case 0x85a86:return am_call(c,0x43ea4,0x85a8c);                           // JSR 43ea4.L.
    case 0x85a8c:return am_call(c,0x49fc6,0x85a92);                           // JSR 49fc6.L.
    case 0x85a92:return ou20b_count(c,0x85aa0,0x85a9a);                       // SUBQ.W #1,76(A6); BNE.W 85aa0.
    case 0x85a9a:return ou20b_install(c,0x85aa4,0x85aa0);                     // MOVE.L #85aa4,(A6).
    case 0x85aa0:case 0x85b3a:case 0x85b9a:case 0x85c00:case 0x85c68:r.pc=OU20B_TAIL;return true; // BRA.W 849f4.

    // ---- 85aa4 (installed callback): CMPI.W #a0,42(A6); BGE.W 85aba.
    case 0x85aa4:return ou20b_side(c,0x85aba,0x85aae);
    case 0x85aae:return ou20b_long(c,0x36,0xffffc000U,0x85ac2);               // MOVE.L #ffffc000,36(A6); BRA.W 85ac2.
    case 0x85aba:return ou20b_long(c,0x36,0x4000U,0x85ac2);                   // MOVE.L #4000,36(A6).
    case 0x85ac2:if(!ou20b_put(c,0x3a,4,0))return false;return ou20b_animation(c,0xc,0x85af2); // MOVE.L #0,3a(A6); animation c.
    case 0x85af2:return ou20b_install(c,0x85af8,0x85af8);                     // MOVE.L #85af8,(A6).
    // ---- 85af8 (installed callback): CMPI.W #0,36(A6); BGE.W 85b1a (signed upper WORD of LONG 36).
    case 0x85af8:if(!ou20b_get(c,0x36,2,value))return false;r.pc=(value&0x8000U)==0U?0x85b1a:0x85b02;return true;
    case 0x85b02:return ou20b_limit(c,0x36,0xfffc0000U,true,0x85b16,0x85b0e); // CMPI.L #fffc0000,36(A6); BLE.W 85b16.
    // SUBI.L #8000,36(A6).
    case 0x85b0e:if(!ou20b_get(c,0x36,4,value))return false;return ou20b_long(c,0x36,(value-0x8000U)&0xffffffffU,0x85b16);
    case 0x85b16:r.pc=0x85b2e;return true;                                    // BRA.W 85b2e.
    case 0x85b1a:return ou20b_limit(c,0x36,0x40000U,false,0x85b2e,0x85b26);   // CMPI.L #40000,36(A6); BGE.W 85b2e.
    // ADDI.L #8000,36(A6).
    case 0x85b26:if(!ou20b_get(c,0x36,4,value))return false;return ou20b_long(c,0x36,(value+0x8000U)&0xffffffffU,0x85b2e);
    case 0x85b2e:return am_call(c,0x43ea4,0x85b34);                           // JSR 43ea4.L.
    case 0x85b34:return am_call(c,0x49fc6,0x85b3a);                           // JSR 49fc6.L.

    // ---- 85b3e: animation c, then the installed callback 85b6c.
    case 0x85b3e:return ou20b_animation(c,0xc,0x85b66);
    case 0x85b66:return ou20b_install(c,0x85b6c,0x85b6c);                     // MOVE.L #85b6c,(A6).
    // ---- 85b6c / 85bcc / 85c48 (installed callbacks): BTST.B #7,15(A6); BNE.W.
    case 0x85b6c:return ou20b_air(c,0x85b80,0x85b76);
    case 0x85bcc:return ou20b_air(c,0x85be0,0x85bd6);
    case 0x85c48:return ou20b_air(c,0x85c5c,0x85c52);
    case 0x85b76:return am_call(c,0x4be2c,0x85b7c);                           // JSR 4be2c.L.
    case 0x85bd6:return am_call(c,0x4be2c,0x85bdc);
    case 0x85c52:return am_call(c,0x4be2c,0x85c58);
    case 0x85b7c:r.pc=0x85b86;return true;                                    // BRA.W 85b86.
    case 0x85bdc:r.pc=0x85be6;return true;                                    // BRA.W 85be6.
    case 0x85c58:r.pc=0x85c62;return true;                                    // BRA.W 85c62.
    case 0x85b80:return am_call(c,0x4be06,0x85b86);                           // JSR 4be06.L.
    case 0x85be0:return am_call(c,0x4be06,0x85be6);
    case 0x85c5c:return am_call(c,0x4bfa4,0x85c62);                           // JSR 4bfa4.L.
    case 0x85b86:return am_call(c,0x49fc6,0x85b8c);                           // JSR 49fc6.L.
    case 0x85be6:return am_call(c,0x49fc6,0x85bec);
    case 0x85c62:return am_call(c,0x49fc6,0x85c68);
    case 0x85b8c:return ou20b_count(c,0x85b9a,0x85b94);                       // SUBQ.W #1,76(A6); BNE.W 85b9a.
    case 0x85b94:return ou20b_install(c,0x85b9e,0x85b9a);                     // MOVE.L #85b9e,(A6).
    // ---- 85b9e (installed callback): animation 18, then 85bcc.
    case 0x85b9e:return ou20b_animation(c,0x18,0x85bc6);
    case 0x85bc6:return ou20b_install(c,0x85bcc,0x85bcc);                     // MOVE.L #85bcc,(A6).
    case 0x85bec:return ou20b_bcc(c,0x85c00,0x85bf0);                         // BCC.W 85c00 (C returned by 49fc6).
    case 0x85bf0:r.a[0]=am_index(r.a[6],0x26);return am_call(c,0x492d0,0x85bfa); // LEA 26(A6),A0; JSR 492d0.L.
    case 0x85bfa:return ou20b_install(c,0x85c04,0x85c00);                     // MOVE.L #85c04,(A6).
    // ---- 85c04 (installed callback): animation 4; MOVE.L #fffc0000,64(A6); BTST.B #0,15(A6); BEQ.W 85c42.
    case 0x85c04:return ou20b_animation(c,0x4,0x85c2c);
    case 0x85c2c:
        if(!ou20b_put(c,0x64,4,0xfffc0000U) || !ou20b_bit15(c,0,flag))return false;r.pc=flag?0x85c3e:0x85c42;return true;
    case 0x85c3e:return ou20b_neg(c,0x64,0x85c42);                            // NEG.L 64(A6).
    case 0x85c42:return ou20b_install(c,0x85c48,0x85c48);                     // MOVE.L #85c48,(A6).
    default:return am_error(c,"unsupported animation objects u20b PC");
    }
}
}
