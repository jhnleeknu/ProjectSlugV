#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONGs (live bus, current PVC bank).
const std::uint32_t ON14_BANK_RECORD=0x200134;      // MOVE.L 200134.L,22(A6) / -4(A0): animation record of the a5e80 family.
const std::uint32_t ON14_BANK_RECORD_BE=0x2001dc;   // MOVE.L 2001dc.L,22(A6) (be0d6).
bool on14_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on14_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Two's complement values of 68000 operands, compared as 64-bit signed numbers (no signed overflow in C++).
std::int64_t on14_signed_long(std::uint32_t value) {
    return (value&0x80000000U)?static_cast<std::int64_t>(value)-0x100000000LL:static_cast<std::int64_t>(value);
}
std::int64_t on14_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int64_t>(value)-65536:static_cast<std::int64_t>(value);
}
// ASR.L #n with the sign bit copied in (0 < n < 32).
std::uint32_t on14_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t fill=(value&0x80000000U)?~(0xffffffffU>>n):0U;return (value>>n)|fill;
}
// EXT.L Dn: sign-extend the low WORD.
std::uint32_t on14_ext(std::uint32_t value) {
    return (value&0x8000U)?(value|0xffff0000U):(value&65535U);
}
// Bcc on a C returned by a callee or set by ORI CCR: BCC goes to clear_pc, otherwise set_pc.
bool on14_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n14 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,(A6) then continue at next_pc.
bool on14_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// MOVEA.L #target,A0; MOVE.W #count,D0; JSR 28ae.L.
bool on14_child(AnimationMachineContext& c,std::uint32_t target,std::uint32_t count,std::uint32_t return_pc) {
    c.s.a[0]=target;am_word(c.s.d[0],count);return am_call(c,0x28ae,return_pc);
}
// CLR.W D0 / MOVE.W #0,D0; CLR.W D1 / MOVE.W #y,D1; JSR 4970a.L.
bool on14_place(AnimationMachineContext& c,std::uint32_t y,std::uint32_t return_pc) {
    am_word(c.s.d[0],0);am_word(c.s.d[1],y);return am_call(c,0x4970a,return_pc);
}
// MOVE.W #id,D0; MOVE.B #0,D1; JSR 8ebe.L.
bool on14_sound(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// BTST.B #bit,displacement(An): true when the bit is set.
bool on14_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!am_read(c,am_index(base,displacement),1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B #bit,displacement(An).
bool on14_bset(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit) {
    const std::uint32_t address=am_index(base,displacement);std::uint32_t value=0;
    if(!am_read(c,address,1,value))return false;return am_write(c,address,1,(value|(1U<<bit))&255U);
}
// NEG.L displacement(A6).
bool on14_neg_long(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t value=0;if(!on14_get(c,displacement,4,value))return false;return on14_put(c,displacement,4,0U-value);
}
// ASR.L #3,D0; ADD.L D0,displacement(A6).
bool on14_ease(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[0]=on14_asr(r.d[0],3);
    if(!on14_get(c,displacement,4,value) || !on14_put(c,displacement,4,value+r.d[0]))return false;r.pc=next_pc;return true;
}
// [LEA 26(A6),A0;] MOVE.W #head,20(A6); MOVE.L bank,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L offset(A1),A1;
// JSR 49f8c.L.
bool on14_animation(AnimationMachineContext& c,std::uint32_t head,std::uint32_t bank,std::uint32_t offset,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[6],0x26);
    if(!on14_put(c,0x20,2,head) || !am_read(c,bank,4,value) || !on14_put(c,0x22,4,value))return false;am_word(r.d[0],0x100);
    if(!on14_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],offset),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L a4(A6),A4; LEA 26(A4),A0; MOVE.W #cb,-6(A0); MOVE.L 200134.L,-4(A0); MOVE.W #100,D0; LEA 26(A4),A0; MOVEA.L 22(A6),A1;
// MOVEA.L offset(A1),A1; JSR 49f96.L.
bool on14_part_animation(AnimationMachineContext& c,std::uint32_t offset,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!on14_get(c,0xa4,4,value))return false;r.a[4]=value;r.a[0]=am_index(r.a[4],0x26);
    if(!am_write(c,am_index(r.a[0],0xfffa),2,0xcb) || !am_read(c,ON14_BANK_RECORD,4,value) || !am_write(c,am_index(r.a[0],0xfffc),4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[4],0x26);
    if(!on14_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],offset),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f96,return_pc);
}
// MOVE.W #w76,76(A0); ... MOVE.W #w7e,7e(A0) on the 28ae child.
bool on14_child_words(AnimationMachineContext& c,std::uint32_t w76,std::uint32_t w78,std::uint32_t w7a,std::uint32_t w7c,std::uint32_t w7e) {
    const std::uint32_t a0=c.s.a[0];
    return am_write(c,am_index(a0,0x76),2,w76) && am_write(c,am_index(a0,0x78),2,w78) && am_write(c,am_index(a0,0x7a),2,w7a) &&
        am_write(c,am_index(a0,0x7c),2,w7c) && am_write(c,am_index(a0,0x7e),2,w7e);
}
// CMPI.W #value,78(A6): true when equal.
bool on14_kind(AnimationMachineContext& c,std::uint32_t value,bool& equal) {
    std::uint32_t got=0;if(!on14_get(c,0x78,2,got))return false;equal=(got&65535U)==value;return true;
}
}
// Objects F4 N14 (old U29 + U28 part; 196 block starts): the stage event callbacks a5e62 a5e6c a5e76 a5e80 (shared body a5e86 with
// the installed states a60c8, a6a0c via a6914, the shared tail a5cf6 and the destruction path a5d18 with the installed a5e20), the 28ae
// child a6dd4 with the installed a6e7e and the tail a7256, the callback be0c4 with the installed be110, and the shared helpers 4970a
// (4972c, then N05 49214) and 4b702. Every callee is routed elsewhere; there is no boundary without an executor. Known C: the five
// ORI.B #1,CCR blocks a5d64 a5d9c a5de8 a5e54 a5faa set C; the 15 BCC/BCS consumers read the C of 1ab02 28ae 497a6 4b54e 288c or of
// those ORI blocks. N14 writes no port and changes no bank.
bool animation_objects_n14_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool flag=false;
    switch(r.pc) {
    // ---- 4970a (helper): JSR 4972c(PC); BTST.B #0,15(A0); BEQ.W 4971a; NEG.W D0; BTST.B #1,15(A0); BEQ.W 49726; NEG.W D1;
    // JSR 49214(PC); RTS.
    case 0x4970a:return am_call(c,0x4972c,0x4970e);
    case 0x4970e:if(!on14_bit(c,r.a[0],0x15,0,flag))return false;r.pc=flag?0x49718:0x4971a;return true;
    case 0x49718:am_word(r.d[0],0U-r.d[0]);r.pc=0x4971a;return true;
    case 0x4971a:if(!on14_bit(c,r.a[0],0x15,1,flag))return false;r.pc=flag?0x49724:0x49726;return true;
    case 0x49724:am_word(r.d[1],0U-r.d[1]);r.pc=0x49726;return true;
    case 0x49726:return am_call(c,0x49214,0x4972a);
    case 0x4972a:case 0x4976c:case 0xa5d16:case 0xa6ed6:case 0xa6ee8:case 0xbe13a:return am_return(c); // RTS.
    // ---- 4972c (helper): MOVE.W 1e(A6),D2; MOVE.W D2,1e(A0); MOVE.W 68(A6),D2; MOVE.W D2,68(A0); BTST.B #0,15(A6); BEQ.W 4974c.
    case 0x4972c:
        if(!on14_get(c,0x1e,2,value))return false;am_word(r.d[2],value);if(!am_write(c,am_index(r.a[0],0x1e),2,r.d[2]&65535U))return false;
        if(!on14_get(c,0x68,2,value))return false;am_word(r.d[2],value);if(!am_write(c,am_index(r.a[0],0x68),2,r.d[2]&65535U))return false;
        if(!on14_bit(c,r.a[6],0x15,0,flag))return false;r.pc=flag?0x49746:0x4974c;return true;
    case 0x49746:if(!on14_bset(c,r.a[0],0x15,0))return false;r.pc=0x4974c;return true; // BSET.B #0,15(A0).
    case 0x4974c:if(!on14_bit(c,r.a[6],0x15,1,flag))return false;r.pc=flag?0x49756:0x4975c;return true;
    case 0x49756:if(!on14_bset(c,r.a[0],0x15,1))return false;r.pc=0x4975c;return true;
    case 0x4975c:if(!on14_bit(c,r.a[6],0x15,2,flag))return false;r.pc=flag?0x49766:0x4976c;return true;
    case 0x49766:if(!on14_bset(c,r.a[0],0x15,2))return false;r.pc=0x4976c;return true;
    // ---- 4b702 (helper): ORI.B #80,60(A6); RTS.
    case 0x4b702:if(!on14_get(c,0x60,1,value) || !on14_put(c,0x60,1,(value|0x80U)&255U))return false;return am_return(c);
    // ---- a5cf6 (shared tail): TST.W 90(A6); BEQ.W a5d02; SUBQ.W #1,90(A6); LEA a5cea(PC),A0; JSR 1ab02.L; BCC.W a5d16; JMP 2a00.L.
    case 0xa5cf6:if(!on14_get(c,0x90,2,value))return false;r.pc=(value&65535U)==0U?0xa5d02:0xa5cfe;return true;
    case 0xa5cfe:if(!on14_get(c,0x90,2,value) || !on14_put(c,0x90,2,(value-1U)&65535U))return false;r.pc=0xa5d02;return true;
    case 0xa5d02:r.a[0]=0xa5cea;return am_call(c,0x1ab02,0xa5d0c);
    case 0xa5d0c:return on14_carry(c,0xa5d16,0xa5d10);                        // BCC.W a5d16 (C returned by 1ab02).
    case 0xa5d10:case 0xa5e58:case 0xa5fb2:case 0xa6ee2:case 0xa7256:case 0xbe134:r.pc=0x2a00;return true; // JMP 2a00.L.
    // ---- a5d18 (destruction): BSET.B #3,15(A6); animation record + a4 (49f8c).
    case 0xa5d18:if(!on14_bset(c,r.a[6],0x15,3))return false;return on14_animation(c,0xcb,ON14_BANK_RECORD,0xa4,0xa5d46);
    case 0xa5d46:return on14_child(c,0xd1d38,0x1e,0xa5d56);
    case 0xa5d56:return on14_carry(c,0xa5d68,0xa5d5a);                        // BCC.W a5d68 (C returned by 28ae).
    case 0xa5d5a:return on14_place(c,0,0xa5d64);
    case 0xa5d64:case 0xa5d9c:case 0xa5de8:case 0xa5e54:case 0xa5faa:       // ORI.B #1,CCR (Set).
        r.carry=AnimationCarrySet;
        r.pc=r.pc==0xa5d64?0xa5d68:r.pc==0xa5d9c?0xa5da0:r.pc==0xa5de8?0xa5dec:r.pc==0xa5e54?0xa5e58:0xa5fae;return true;
    // CMPI.B #1,9a(A6); BNE.W a5e0e.
    case 0xa5d68:if(!on14_get(c,0x9a,1,value))return false;r.pc=(value&255U)!=1U?0xa5e0e:0xa5d72;return true;
    case 0xa5d72:if(!on14_get(c,0x7e,2,value))return false;r.pc=(value&65535U)!=0U?0xa5dc6:0xa5d7a;return true; // TST.W 7e(A6); BNE.
    case 0xa5d7a:return on14_child(c,0x7086a,0x14,0xa5d8a);
    case 0xa5dc6:return on14_child(c,0x7487a,0x14,0xa5dd6);
    case 0xa5d8a:return on14_carry(c,0xa5da0,0xa5d8e);
    case 0xa5dd6:return on14_carry(c,0xa5dec,0xa5dda);
    case 0xa5d8e:return on14_place(c,0x20,0xa5d9c);
    case 0xa5dda:return on14_place(c,0x20,0xa5de8);
    case 0xa5da0:return on14_carry(c,0xa5dc2,0xa5da4);
    case 0xa5dec:return on14_carry(c,0xa5e0e,0xa5df0);
    case 0xa5da4:if(!on14_child_words(c,0,0x78,0xb4,0,0))return false;r.pc=0xa5dc2;return true;
    case 0xa5df0:if(!on14_child_words(c,0,0,0,0,1))return false;r.pc=0xa5e0e;return true;
    case 0xa5dc2:r.pc=0xa5e0e;return true;                                   // BRA.W a5e0e.
    // MOVE.B #0,9a(A6); MOVE.B #2,9b(A6); MOVE.L #a5e20,(A6).
    case 0xa5e0e:if(!on14_put(c,0x9a,1,0) || !on14_put(c,0x9b,1,2))return false;return on14_install(c,0xa5e20,0xa5e20);
    case 0xa5e20:return am_call(c,0x4be2c,0xa5e26);
    case 0xa5e26:case 0xa6114:case 0xa6ea0:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.L.
    case 0xa5e2c:if(!on14_bit(c,r.a[6],0x15,7,flag))return false;r.pc=flag?0xa5e36:0xa5e5e;return true; // BTST.B #7,15(A6); BEQ.
    case 0xa5e36:return on14_child(c,0xd1d38,0x1e,0xa5e46);
    case 0xa5e46:return on14_carry(c,0xa5e58,0xa5e4a);
    case 0xa5e4a:return on14_place(c,0,0xa5e54);
    case 0xa5e5e:case 0xa616e:case 0xa6ac2:r.pc=0xa5cf6;return true;       // BRA.W a5cf6.
    // ---- a5e62 a5e6c a5e76 a5e80 (stage event callbacks): MOVE.B #1/#2,9a(A6); BRA.W a5e86 (a5e80 falls through).
    case 0xa5e62:case 0xa5e6c:case 0xa5e76:case 0xa5e80:
        if(!on14_put(c,0x9a,1,(r.pc==0xa5e62 || r.pc==0xa5e76)?1U:2U))return false;r.pc=0xa5e86;return true;
    case 0xa5e86:if(!on14_get(c,0x9a,1,value))return false;r.pc=(value&255U)!=1U?0xa5ed2:0xa5e90;return true; // CMPI.B #1,9a(A6); BNE.
    case 0xa5e90:return on14_sound(c,0xc7f,0xa5e9e);
    case 0xa5ed2:return on14_sound(c,0xc7f,0xa5ee0);
    case 0xa5e9e:return am_call(c,0x497a6,0xa5ea4);
    case 0xa5ee0:return am_call(c,0x497a6,0xa5ee6);
    case 0xa5ea4:return on14_carry(c,0xa5eba,0xa5ea8);                        // BCC (C returned by 497a6).
    case 0xa5ee6:return on14_carry(c,0xa5efc,0xa5eea);
    case 0xa5ea8:return on14_sound(c,0xc4d,0xa5eb6);
    case 0xa5eba:return on14_sound(c,0xc49,0xa5ec8);
    case 0xa5eea:return on14_sound(c,0xc54,0xa5ef8);
    case 0xa5efc:return on14_sound(c,0xc4e,0xa5f0a);
    case 0xa5eb6:r.pc=0xa5ec8;return true;                                   // BRA.W a5ec8.
    case 0xa5ef8:r.pc=0xa5f0a;return true;                                   // BRA.W a5f0a.
    // MOVE.B 19(A6),14(A6) (a5ec8 then BRA.W a5f10).
    case 0xa5ec8:case 0xa5f0a:if(!on14_get(c,0x19,1,value) || !on14_put(c,0x14,1,value))return false;r.pc=0xa5f10;return true;
    case 0xa5f10:am_word(r.d[0],0xc83);return am_call(c,0x4a496,0xa5f1a);  // MOVE.W #c83,D0; JSR 4a496.L.
    // BSET.B #6,15(A6); MOVE.W #8800,68/1e(A6); MOVE.W #32,54(A6); MOVE.W 7c(A6),8e(A6); CMPI.W #3,78(A6); BNE.W a5f4c.
    case 0xa5f1a:
        if(!on14_bset(c,r.a[6],0x15,6) || !on14_put(c,0x68,2,0x8800) || !on14_put(c,0x1e,2,0x8800) || !on14_put(c,0x54,2,0x32) ||
            !on14_get(c,0x7c,2,value) || !on14_put(c,0x8e,2,value) || !on14_kind(c,3,flag))return false;
        r.pc=flag?0xa5f42:0xa5f4c;return true;
    case 0xa5f42:if(!on14_put(c,0x90,2,0x5a))return false;r.pc=0xa5f52;return true; // MOVE.W #5a,90(A6); BRA.W a5f52.
    case 0xa5f4c:if(!on14_put(c,0x90,2,0x32))return false;r.pc=0xa5f52;return true;
    // MOVE.L #0,36(A6); MOVE.L #0,3a(A6); MOVE.W 80(A6),D0; BNE.W a5f76.
    case 0xa5f52:
        if(!on14_put(c,0x36,4,0) || !on14_put(c,0x3a,4,0) || !on14_get(c,0x80,2,value))return false;am_word(r.d[0],value);
        r.pc=(value&65535U)!=0U?0xa5f76:0xa5f6a;return true;
    case 0xa5f6a:if(!on14_put(c,0x9c,4,0x30000))return false;r.pc=0xa5f7e;return true; // MOVE.L #30000,9c(A6); BRA.W a5f7e.
    case 0xa5f76:r.d[0]=on14_ext(r.d[0])<<8;if(!on14_put(c,0x9c,4,r.d[0]))return false;r.pc=0xa5f7e;return true; // EXT.L; LSL.L #8.
    case 0xa5f7e:if(!on14_get(c,0x76,2,value))return false;r.pc=(value&65535U)!=0U?0xa5f8c:0xa5f86;return true; // TST.W 76(A6); BNE.
    case 0xa5f86:if(!on14_bset(c,r.a[6],0x15,0))return false;r.pc=0xa5f8c;return true;
    case 0xa5f8c:return on14_child(c,0xa6dd4,0xa,0xa5f9c);
    case 0xa5f9c:return on14_carry(c,0xa5fae,0xa5fa0);
    case 0xa5fa0:return on14_place(c,0,0xa5faa);
    case 0xa5fae:return on14_carry(c,0xa5fb2,0xa5fb8);                        // BCS.W a5fb8.
    // MOVE.L A0,a4(A6); MOVE.B #1,9b(A6); TST.W 76(A6); BEQ.W a5fce.
    case 0xa5fb8:
        if(!on14_put(c,0xa4,4,r.a[0]) || !on14_put(c,0x9b,1,1) || !on14_get(c,0x76,2,value))return false;
        r.pc=(value&65535U)==0U?0xa5fce:0xa5fca;return true;
    case 0xa5fca:if(!on14_neg_long(c,0x9c))return false;r.pc=0xa5fce;return true; // NEG.L 9c(A6).
    case 0xa5fce:if(!on14_kind(c,4,flag))return false;r.pc=flag?0xa5fd8:0xa5fdc;return true; // CMPI.W #4,78(A6); BNE.W a5fdc.
    case 0xa5fd8:r.pc=0xa6914;return true;                                   // BRA.W a6914.
    // MOVE.L #4000,36(A6); BTST.B #0,15(A6); BNE.W a5ff2; NEG.L 36(A6) (a5fee).
    case 0xa5fdc:if(!on14_put(c,0x36,4,0x4000) || !on14_bit(c,r.a[6],0x15,0,flag))return false;r.pc=flag?0xa5ff2:0xa5fee;return true;
    case 0xa5fee:if(!on14_neg_long(c,0x36))return false;r.pc=0xa5ff2;return true;
    // MOVE.W #0,98(A6); MOVE.W #6,94(A6); MOVE.B 9a(A6),D0; BNE.W a6032.
    case 0xa5ff2:
        if(!on14_put(c,0x98,2,0) || !on14_put(c,0x94,2,6) || !on14_get(c,0x9a,1,value))return false;am_byte(r.d[0],value);
        r.pc=(value&255U)!=0U?0xa6032:0xa6006;return true;
    // ---- a6914 (78 = 4): MOVE.B 9a(A6),D0; BNE.W a6948.
    case 0xa6914:if(!on14_get(c,0x9a,1,value))return false;am_byte(r.d[0],value);r.pc=(value&255U)!=0U?0xa6948:0xa691c;return true;
    case 0xa6032:case 0xa6948:                                              // CMPI.B #1,D0; BNE.W a6066 / a697c.
        r.pc=(r.d[0]&255U)!=1U?(r.pc==0xa6032?0xa6066:0xa697c):(r.pc==0xa6032?0xa603a:0xa6950);return true;
    case 0xa6006:return on14_animation(c,0xcb,ON14_BANK_RECORD,0x4,0xa602e);
    case 0xa603a:return on14_animation(c,0xcb,ON14_BANK_RECORD,0x54,0xa6062);
    case 0xa6066:return on14_animation(c,0xcb,ON14_BANK_RECORD,0x2c,0xa608e);
    case 0xa691c:return on14_animation(c,0xcb,ON14_BANK_RECORD,0x20,0xa6944);
    case 0xa6950:return on14_animation(c,0xcb,ON14_BANK_RECORD,0x70,0xa6978);
    case 0xa697c:return on14_animation(c,0xcb,ON14_BANK_RECORD,0x48,0xa69a4);
    case 0xa602e:case 0xa6062:r.pc=0xa608e;return true;                     // BRA.W a608e.
    case 0xa6944:case 0xa6978:r.pc=0xa69a4;return true;                     // BRA.W a69a4.
    // TST.B 9b(A6); BEQ.W a60c2 / a69d8.
    case 0xa608e:case 0xa69a4:
        if(!on14_get(c,0x9b,1,value))return false;
        r.pc=(value&255U)==0U?(r.pc==0xa608e?0xa60c2:0xa69d8):(r.pc==0xa608e?0xa6096:0xa69ac);return true;
    case 0xa6096:return on14_part_animation(c,0x7c,0xa60c2);
    case 0xa69ac:return on14_part_animation(c,0x98,0xa69d8);
    case 0xa60c2:return on14_install(c,0xa60c8,0xa60c8);
    // ---- a60c8 / a6a0c (installed): JSR 4b54e.L; BCC; CLR.B 5e(A6); BTST.B #7,61(A6); BNE.W a5d18.
    case 0xa60c8:return am_call(c,0x4b54e,0xa60ce);
    case 0xa6a0c:return am_call(c,0x4b54e,0xa6a12);
    case 0xa60ce:return on14_carry(c,0xa60d6,0xa60d2);                        // BCC (C returned by 4b54e).
    case 0xa6a12:return on14_carry(c,0xa6a1a,0xa6a16);
    case 0xa60d2:case 0xa6a16:if(!on14_put(c,0x5e,1,0))return false;r.pc=r.pc+4U;return true; // CLR.B 5e(A6).
    case 0xa60d6:case 0xa6a1a:
        if(!on14_bit(c,r.a[6],0x61,7,flag))return false;r.pc=flag?0xa5d18:(r.pc==0xa60d6?0xa60e0:0xa6a24);return true;
    // MOVE.L 36(A6),D0; BTST.B #0,15(A6); BNE.W a6100.
    case 0xa60e0:if(!on14_get(c,0x36,4,value))return false;r.d[0]=value;if(!on14_bit(c,r.a[6],0x15,0,flag))return false;
        r.pc=flag?0xa6100:0xa60ee;return true;
    // CMP.L 9c(A6),D0; BLE.W a60fc (signed D0 <= 9c) / BGE.W a610e (signed D0 >= 9c).
    case 0xa60ee:if(!on14_get(c,0x9c,4,value))return false;r.pc=on14_signed_long(r.d[0])<=on14_signed_long(value)?0xa60fc:0xa60f6;return true;
    case 0xa6100:if(!on14_get(c,0x9c,4,value))return false;r.pc=on14_signed_long(r.d[0])>=on14_signed_long(value)?0xa610e:0xa6108;return true;
    case 0xa60f6:return on14_ease(c,0x36,0xa60fc);                           // ASR.L #3,D0; ADD.L D0,36(A6).
    case 0xa6108:return on14_ease(c,0x36,0xa610e);
    case 0xa60fc:r.pc=0xa610e;return true;                                   // BRA.W a610e.
    case 0xa610e:case 0xa6a9c:return am_call(c,0x43ea4,r.pc+6U);           // JSR 43ea4.L.
    case 0xa611a:if(!on14_get(c,0x8e,2,value))return false;r.pc=(value&65535U)==0U?0xa6136:0xa6122;return true; // TST.W 8e(A6); BEQ.
    // SUBQ.W #1,8e(A6); BNE.W a6136.
    case 0xa6122:if(!on14_get(c,0x8e,2,value))return false;value=(value-1U)&65535U;if(!on14_put(c,0x8e,2,value))return false;
        r.pc=value!=0U?0xa6136:0xa612a;return true;
    case 0xa612a:if(!on14_put(c,0x9b,1,0) || !on14_put(c,0x90,2,0))return false;r.pc=0xa6136;return true; // MOVE.B #0,9b; MOVE.W #0,90.
    case 0xa6136:if(!on14_get(c,0x90,2,value))return false;r.pc=(value&65535U)!=0U?0xa616e:0xa613e;return true; // TST.W 90(A6); BNE.
    // CMPI.W #0/#1/#3,78(A6); BNE; MOVE.L #a6172/#a62cc/#a658e,(A6) (installed values outside the unit).
    case 0xa613e:if(!on14_kind(c,0,flag))return false;r.pc=flag?0xa6148:0xa614e;return true;
    case 0xa614e:if(!on14_kind(c,1,flag))return false;r.pc=flag?0xa6158:0xa615e;return true;
    case 0xa615e:if(!on14_kind(c,3,flag))return false;r.pc=flag?0xa6168:0xa616e;return true;
    case 0xa6148:return on14_install(c,0xa6172,0xa614e);
    case 0xa6158:return on14_install(c,0xa62cc,0xa615e);
    case 0xa6168:return on14_install(c,0xa658e,0xa616e);
    // ---- a69d8: CLR.L 36(A6); MOVE.L #fffff000,3a(A6); MOVE.L 9c(A6),a0(A6); MOVE.L #1000,36(A6); TST.L 9c(A6); BPL.W a6a02.
    case 0xa69d8:
        if(!on14_put(c,0x36,4,0) || !on14_put(c,0x3a,4,0xfffff000U) || !on14_get(c,0x9c,4,value) || !on14_put(c,0xa0,4,value) ||
            !on14_put(c,0x36,4,0x1000) || !on14_get(c,0x9c,4,value))return false;
        r.pc=(value&0x80000000U)?0xa69fa:0xa6a02;return true;
    case 0xa69fa:if(!on14_neg_long(c,0x36))return false;r.pc=0xa6a06;return true; // NEG.L 36(A6); BRA.W a6a06.
    case 0xa6a02:if(!on14_neg_long(c,0xa0))return false;r.pc=0xa6a06;return true; // NEG.L a0(A6).
    case 0xa6a06:return on14_install(c,0xa6a0c,0xa6a0c);
    // ---- a6a24: MOVE.L 3a(A6),D0; CMP.L a0(A6),D0; BLE.W a6a36; ASR.L #3,D0; ADD.L D0,3a(A6) (a6a30).
    case 0xa6a24:if(!on14_get(c,0x3a,4,value))return false;r.d[0]=value;if(!on14_get(c,0xa0,4,other))return false;
        r.pc=on14_signed_long(r.d[0])<=on14_signed_long(other)?0xa6a36:0xa6a30;return true;
    case 0xa6a30:return on14_ease(c,0x3a,0xa6a36);
    // CLR.B D2; MOVE.W 42(A6),D0; CMP.W 84(A6),D0; BEQ.W a6a60; BLE.W a6a56 (signed WORD).
    case 0xa6a36:
        am_byte(r.d[2],0);if(!on14_get(c,0x42,2,value))return false;am_word(r.d[0],value);if(!on14_get(c,0x84,2,other))return false;
        r.pc=(value&65535U)==(other&65535U)?0xa6a60:on14_signed_word(value)<=on14_signed_word(other)?0xa6a56:0xa6a48;return true;
    // TST.L 9c(A6); BPL.W a6a52 / BMI.W a6a60.
    case 0xa6a48:if(!on14_get(c,0x9c,4,value))return false;r.pc=(value&0x80000000U)?0xa6a50:0xa6a52;return true;
    case 0xa6a56:if(!on14_get(c,0x9c,4,value))return false;r.pc=(value&0x80000000U)?0xa6a60:0xa6a5e;return true;
    case 0xa6a50:case 0xa6a5e:am_byte(r.d[2],0xff);r.pc=r.pc+2U;return true; // ST.B D2.
    case 0xa6a52:r.pc=0xa6a60;return true;                                   // BRA.W a6a60.
    case 0xa6a60:r.pc=(r.d[2]&255U)!=0U?0xa6a74:0xa6a66;return true;       // TST.B D2; BNE.W a6a74.
    // MOVE.L 36(A6),D0; ASR.L #2,D0; SUB.L D0,36(A6); BRA.W a6a9c.
    case 0xa6a66:if(!on14_get(c,0x36,4,value))return false;r.d[0]=on14_asr(value,2);
        if(!on14_get(c,0x36,4,value) || !on14_put(c,0x36,4,value-r.d[0]))return false;r.pc=0xa6a9c;return true;
    // MOVE.L 36(A6),D0; MOVE.L 9c(A6),D1; BPL.W a6a90.
    case 0xa6a74:if(!on14_get(c,0x36,4,value))return false;r.d[0]=value;if(!on14_get(c,0x9c,4,value))return false;r.d[1]=value;
        r.pc=(value&0x80000000U)?0xa6a80:0xa6a90;return true;
    // CMP.L D1,D0; BLE.W a6a8c / BGE.W a6a9c.
    case 0xa6a80:r.pc=on14_signed_long(r.d[0])<=on14_signed_long(r.d[1])?0xa6a8c:0xa6a86;return true;
    case 0xa6a90:r.pc=on14_signed_long(r.d[0])>=on14_signed_long(r.d[1])?0xa6a9c:0xa6a96;return true;
    case 0xa6a86:return on14_ease(c,0x36,0xa6a8c);
    case 0xa6a96:return on14_ease(c,0x36,0xa6a9c);
    case 0xa6a8c:r.pc=0xa6a9c;return true;                                   // BRA.W a6a9c.
    // MOVE.W 46(A6),D0; SUBI.W #100,D0; CMP.W 82(A6),D0; BGE.W a6ab8 (signed WORD).
    case 0xa6aa2:if(!on14_get(c,0x46,2,value))return false;am_word(r.d[0],value-0x100U);if(!on14_get(c,0x82,2,other))return false;
        r.pc=on14_signed_word(r.d[0])>=on14_signed_word(other)?0xa6ab8:0xa6ab2;return true;
    case 0xa6ab2:return on14_install(c,0xa6ac6,0xa6ab8);                     // MOVE.L #a6ac6,(A6) (installed value outside the unit).
    case 0xa6ab8:if(!on14_get(c,0x84,2,value))return false;return am_call(c,0x49fc6,0xa6ac2); // CMP.W 84(A6),D0 (flags unused); JSR 49fc6.L.
    // ---- a6dd4 (28ae child): BSET.B #6,15(A6); MOVE.W #e001,68/1e(A6); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L.
    case 0xa6dd4:
        if(!on14_bset(c,r.a[6],0x15,6) || !on14_put(c,0x68,2,0xe001) || !on14_put(c,0x1e,2,0xe001))return false;r.d[0]=0;r.d[1]=0;
        return am_call(c,0x49290,0xa6df0);
    // MOVE.W #x,D0; MOVE.W #y,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xa6df0:am_word(r.d[0],0x4c);am_word(r.d[1],0x1f);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xa6e02);
    case 0xbe0c4:am_word(r.d[0],0x76);am_word(r.d[1],0x1b);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xbe0d6);
    // BSET.B #3,15(A6); LEA cad88.L,A0; JSR 490ba.L.
    case 0xa6e02:if(!on14_bset(c,r.a[6],0x15,3))return false;r.a[0]=0xcad88;return am_call(c,0x490ba,0xa6e14);
    case 0xa6e14:if(!on14_put(c,0x54,2,r.d[0]&65535U))return false;r.a[0]=0xcadea;return am_call(c,0x490ba,0xa6e24);
    // MOVE.W D0,D0; EXT.L D0; LSL.L #8,D0; BTST.B #0,15(A6); BNE.W a6e36; NEG.L D0 (a6e34).
    case 0xa6e24:r.d[0]=on14_ext(r.d[0])<<8;if(!on14_bit(c,r.a[6],0x15,0,flag))return false;r.pc=flag?0xa6e36:0xa6e34;return true;
    case 0xa6e34:case 0xa6e44:r.d[0]=0U-r.d[0];r.pc=r.pc+2U;return true;  // NEG.L D0.
    // MOVEA.L c(A6),A0; CMPI.W #4,78(A0); BNE.W a6e46.
    case 0xa6e36:if(!on14_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x78),2,value))return false;
        r.pc=(value&65535U)!=4U?0xa6e46:0xa6e44;return true;
    // MOVE.L D0,64(A6); MOVEQ #0,D0; MOVE.L D0,36(A6); MOVE.L D0,3a(A6); JSR 4b702.L.
    case 0xa6e46:if(!on14_put(c,0x64,4,r.d[0]))return false;r.d[0]=0;if(!on14_put(c,0x36,4,0) || !on14_put(c,0x3a,4,0))return false;
        return am_call(c,0x4b702,0xa6e5a);
    // MOVEA.L c(A6),A0; MOVE.W 7a(A0),D0; ADDI.W #100,D0; MOVE.W D0,82(A6); MOVE.W #cb,20(A6); MOVE.L 200134.L,22(A6); MOVE.L #a6e7e,(A6).
    case 0xa6e5a:
        if(!on14_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x7a),2,value))return false;
        am_word(r.d[0],value+0x100U);if(!on14_put(c,0x82,2,r.d[0]&65535U) || !on14_put(c,0x20,2,0xcb) || !am_read(c,ON14_BANK_RECORD,4,value) ||
            !on14_put(c,0x22,4,value))return false;
        return on14_install(c,0xa6e7e,0xa6e7e);
    // ---- a6e7e (installed): JSR 288c.L; BCC.W a7256.
    case 0xa6e7e:return am_call(c,0x288c,0xa6e84);
    case 0xa6e84:return on14_carry(c,0xa7256,0xa6e88);                        // BCC.W a7256 (C returned by 288c).
    case 0xa6e88:return am_call(c,0x491c4,0xa6e8e);
    // MOVE.B a8(A0),a8(A6); JSR 43e34.L.
    case 0xa6e8e:if(!am_read(c,am_index(r.a[0],0xa8),1,value) || !on14_put(c,0xa8,1,value))return false;return am_call(c,0x43e34,0xa6e9a);
    case 0xa6e9a:return am_call(c,0x492c8,0xa6ea0);
    // MOVEA.L c(A6),A0; TST.B 9b(A0); BNE.W a6ed8.
    case 0xa6ea6:if(!on14_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x9b),1,value))return false;
        r.pc=(value&255U)!=0U?0xa6ed8:0xa6eb2;return true;
    case 0xa6eb2:am_word(r.d[0],0x182a);return am_call(c,0x3af8,0xa6ebc);  // MOVE.W #182a,D0; JSR 3af8.L.
    // MOVE.L #a7036,(A6) (installed value outside the unit); MOVE.W #0,D0; MOVE.W #ffe0,D1; JSR 49290.L.
    case 0xa6ebc:if(!am_write(c,r.a[6],4,0xa7036))return false;am_word(r.d[0],0);am_word(r.d[1],0xffe0);return am_call(c,0x49290,0xa6ed0);
    case 0xa6ed0:return am_call(c,0x49274,0xa6ed6);
    // CMPI.B #2,9b(A0); BNE.W a6ee8.
    case 0xa6ed8:if(!am_read(c,am_index(r.a[0],0x9b),1,value))return false;r.pc=(value&255U)!=2U?0xa6ee8:0xa6ee2;return true;
    // ---- be0c4 (callback): MOVE.W #8838,68/1e(A6); LEA 26(A6),A0; MOVE.W #21b,20(A6); MOVE.L 2001dc.L,22(A6); ... record + 6c (49f8c).
    case 0xbe0d6:
        if(!on14_put(c,0x68,2,0x8838) || !on14_put(c,0x1e,2,0x8838))return false;
        return on14_animation(c,0x21b,ON14_BANK_RECORD_BE,0x6c,0xbe10a);
    case 0xbe10a:return on14_install(c,0xbe110,0xbe110);
    case 0xbe110:return am_call(c,0x43e34,0xbe116);
    // LEA 26(A6),A0; MOVE.W #80,6(A0); JSR 49fc6.L.
    case 0xbe116:r.a[0]=am_index(r.a[6],0x26);if(!am_write(c,am_index(r.a[0],6),2,0x80))return false;return am_call(c,0x49fc6,0xbe126);
    case 0xbe126:r.a[0]=0xbe0bc;return am_call(c,0x1ab02,0xbe130);          // LEA be0bc(PC),A0; JSR 1ab02.L.
    case 0xbe130:return on14_carry(c,0xbe13a,0xbe134);                        // BCC.W be13a (C returned by 1ab02).
    default:return am_error(c,"unsupported animation objects n14 PC");
    }
}
}
