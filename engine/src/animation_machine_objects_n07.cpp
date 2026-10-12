#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code.
const std::uint32_t ON07_RECT=0x9ac86;          // LEA 9ac86(PC),A0: rectangle read by 1ab02.
const std::uint32_t ON07_FLYER_BANK=0x200128;   // MOVE.L 200128.L,22(A6): banked window LONG (live bus).
const std::uint32_t ON07_STILL_BANK=0x2001d8;   // MOVE.L 2001d8.L,22(A6).
const std::uint32_t ON07_FLYER_LIST=0x9c0bc;    // MOVEA.L #9c0bc,A1: fixed animation list for 49f8c (address only).
const std::uint32_t ON07_INTERVALS=0xcc22c;     // LEA cc22c.L,A0: table for 490ba (address only).
const std::uint32_t ON07_SPLASH=0xbbdc0;        // LEA bbdc0(PC),A1: data for the boundary d3802 (address only).
// A5 displacement (sign-extended WORD).
const std::uint32_t ON07_PROGRESS=0x5418;       // WORD 5418(A5) compared with 7c(A6).
bool on07_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on07_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Signed view of a WORD (explicit two's complement).
std::int32_t on07_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
// Signed LONG a >= b without signed overflow: flip the sign bits and compare unsigned.
bool on07_long_ge(std::uint32_t a,std::uint32_t b) {return (a^0x80000000U)>=(b^0x80000000U);}
bool on07_negative_long(std::uint32_t value) {return (value&0x80000000U)!=0U;}
// ASR.L #3.
std::uint32_t on07_asr3(std::uint32_t value) {return (value>>3)|(on07_negative_long(value)?0xe0000000U:0U);}
// Consumers of a known C: BCC (taken when clear).
bool on07_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n07 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W #d0,D0; MOVE.W #d1,D1; MOVE.B #0,D2; JSR c6a96.L.
bool on07_palette_object(AnimationMachineContext& c,std::uint32_t d0,std::uint32_t d1,std::uint32_t return_pc) {
    am_word(c.s.d[0],d0);am_word(c.s.d[1],d1);am_byte(c.s.d[2],0);return am_call(c,0xc6a96,return_pc);
}
// LEA 26(A6),A0; MOVE.W #id,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1;
// MOVEA.L entry(A1),A1; JSR 49f8c.L.
bool on07_animation(AnimationMachineContext& c,std::uint32_t id,std::uint32_t bank,std::uint32_t entry,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!on07_put(c,0x20,2,id) || !am_read(c,bank,4,value) || !on07_put(c,0x22,4,value))return false;
    am_word(r.d[0],0x100);if(!on07_get(c,0x22,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],entry),4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.L speed(A6),D0; MOVE.L D0,D1; BPL.W abs_pc (else NEG.L D1 at neg_pc).
bool on07_speed(AnimationMachineContext& c,std::uint32_t speed,std::uint32_t abs_pc,std::uint32_t neg_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on07_get(c,speed,4,value))return false;
    r.d[0]=value;r.d[1]=value;r.pc=on07_negative_long(value)?neg_pc:abs_pc;return true;
}
// CMP.L limit(A6),D1; BGE.W skip_pc (signed LONG), else grow_pc.
bool on07_limit(AnimationMachineContext& c,std::uint32_t limit,std::uint32_t skip_pc,std::uint32_t grow_pc) {
    std::uint32_t value=0;if(!on07_get(c,limit,4,value))return false;c.s.pc=on07_long_ge(c.s.d[1],value)?skip_pc:grow_pc;return true;
}
// ASR.L #3,D0; ADD.L D0,speed(A6).
bool on07_grow(AnimationMachineContext& c,std::uint32_t speed,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[0]=on07_asr3(r.d[0]);
    if(!on07_get(c,speed,4,value) || !on07_put(c,speed,4,value+r.d[0]))return false;r.pc=next_pc;return true;
}
// MOVE.W speed(A6),D0; CMPI.B #3,D0; BPL.W keep_pc (N = bit 7 of the BYTE difference), else NEG.W D0 at neg_pc.
bool on07_tilt(AnimationMachineContext& c,std::uint32_t speed,std::uint32_t keep_pc,std::uint32_t neg_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on07_get(c,speed,2,value))return false;
    am_word(r.d[0],value);r.pc=((r.d[0]-3U)&0x80U)==0U?keep_pc:neg_pc;return true;
}
// MOVE.B #3,D0; BLE.W skip_pc: MOVE leaves N=Z=V=0, so BLE is never taken.
bool on07_clamp(AnimationMachineState& r,std::uint32_t skip_pc,std::uint32_t next_pc) {
    am_byte(r.d[0],3);const bool z=false,n=false,v=false;r.pc=(z || n!=v)?skip_pc:next_pc;return true;
}
// SUBQ.W #1,displacement(A6).
bool on07_decrement(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t& old) {
    return on07_get(c,displacement,2,old) && on07_put(c,displacement,2,(old-1U)&65535U);
}
}
// Objects F4 N07 (old U24; 125 block starts): the node callbacks 9baf2 (U05 c6a96, U14 4a496, banked animation 200128 for the
// interpreter 49f8c, cleanup 43e34, U12 4c0ac, installed 9bbf8 easing 3a toward 7a, the progress test 5418(A5) >= 7c installing
// the out-of-range 9bc74 or entering 9bf6c: sound 188e, fixed list 9c0bc, U11 490ba intervals cc22c, installed 9bfba with the 28ae
// children 9b370 / 9b164, the boundaries 4970a and N06 491b6) and bbb9e (palette and banked animation 2001d8 chosen by 76, installed
// bbd3c, U01 4b54e contact, sound 1a31, stage area 49a58, N05 1a3ae, the boundaries d3802 and 1aa40, U09 4706c), the installed 9bf1e
// (out-of-range installer 9bf18) and the shared tail 9ad06 (counters 96/92, U05 1ab02 with the fixed rectangle 9ac86). 9c04c/9c07a
// (ORI CCR) set C. The BLE after MOVE.B #3,D0 (9bf52 9bfee) is never taken. N07 writes no port and changes no bank.
bool animation_objects_n07_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    // ---- 9ad06 (shared tail): TST.W 96(A6); BEQ.W 9ad12; SUBQ.W #1,96(A6); TST.W 92(A6); BEQ.W 9ad1e; SUBQ.W #1,92(A6).
    case 0x9ad06:if(!on07_get(c,0x96,2,value))return false;r.pc=(value&65535U)==0U?0x9ad12:0x9ad0e;return true;
    case 0x9ad0e:if(!on07_decrement(c,0x96,value))return false;r.pc=0x9ad12;return true;
    case 0x9ad12:if(!on07_get(c,0x92,2,value))return false;r.pc=(value&65535U)==0U?0x9ad1e:0x9ad1a;return true;
    case 0x9ad1a:if(!on07_decrement(c,0x92,value))return false;r.pc=0x9ad1e;return true;
    case 0x9ad1e:r.a[0]=ON07_RECT;return am_call(c,0x1ab02,0x9ad28);          // LEA 9ac86(PC),A0; JSR 1ab02.L.
    case 0x9ad28:return on07_carry(c,0x9ad32,0x9ad2c);                        // BCC.W 9ad32 (C returned by 1ab02).
    case 0x9ad2c:case 0xbbda8:r.pc=0x2a00;return true;                       // JMP 2a00.L.
    case 0x9ad32:case 0xbbdbe:return am_return(c);                           // RTS.

    // ---- 9baf2 (callback): c6a96 (49, 4); MOVE.W #c7d,D0; JSR 4a496.L.
    case 0x9baf2:return on07_palette_object(c,0x49,0x4,0x9bb04);
    case 0x9bb04:am_word(r.d[0],0xc7d);return am_call(c,0x4a496,0x9bb0e);
    // MOVE.W #800,68(A6); MOVE.W #800,1e(A6); MOVE.W #a0,54(A6); MOVE.W 7a/7c/7e(A6),94/92/90(A6); MOVE.W 80(A6),D0; BNE.W 9bb4e.
    case 0x9bb0e:
        if(!on07_put(c,0x68,2,0x800) || !on07_put(c,0x1e,2,0x800) || !on07_put(c,0x54,2,0xa0))return false;
        if(!on07_get(c,0x7a,2,value) || !on07_put(c,0x94,2,value) || !on07_get(c,0x7c,2,value) || !on07_put(c,0x92,2,value) ||
            !on07_get(c,0x7e,2,value) || !on07_put(c,0x90,2,value) || !on07_get(c,0x80,2,value))return false;
        am_word(r.d[0],value);r.pc=(value&65535U)!=0U?0x9bb4e:0x9bb3a;return true;
    // MOVE.L #30000,82(A6); MOVE.L #30000,86(A6); BRA.W 9bb5a.
    case 0x9bb3a:if(!on07_put(c,0x82,4,0x30000) || !on07_put(c,0x86,4,0x30000))return false;r.pc=0x9bb5a;return true;
    // EXT.L D0; LSL.L #8,D0; MOVE.L D0,86(A6); MOVE.L D0,82(A6).
    case 0x9bb4e:r.d[0]=am_extend_word(r.d[0])<<8;if(!on07_put(c,0x86,4,r.d[0]) || !on07_put(c,0x82,4,r.d[0]))return false;r.pc=0x9bb5a;return true;
    // TST.W 76(A6); BNE.W 9bb68; BSET.B #0,15(A6).
    case 0x9bb5a:if(!on07_get(c,0x76,2,value))return false;r.pc=(value&65535U)!=0U?0x9bb68:0x9bb62;return true;
    case 0x9bb62:if(!on07_get(c,0x15,1,value) || !on07_put(c,0x15,1,value|1U))return false;r.pc=0x9bb68;return true;
    // CMPI.W #0,78(A6); BNE.W 9bb7e; JSR 43e34.L; MOVE.W 46(A6),7a(A6).
    case 0x9bb68:if(!on07_get(c,0x78,2,value))return false;r.pc=(value&65535U)!=0U?0x9bb7e:0x9bb72;return true;
    case 0x9bb72:case 0xbbd3c:return am_call(c,0x43e34,r.pc==0x9bb72?0x9bb78:0xbbd42); // JSR 43e34.L.
    case 0x9bb78:if(!on07_get(c,0x46,2,value) || !on07_put(c,0x7a,2,value))return false;r.pc=0x9bb7e;return true;
    // CMPI.W #1,78(A6); BNE.W 9bb8e; JSR 4c0ac.L.
    case 0x9bb7e:if(!on07_get(c,0x78,2,value))return false;r.pc=(value&65535U)!=1U?0x9bb8e:0x9bb88;return true;
    case 0x9bb88:return am_call(c,0x4c0ac,0x9bb8e);
    // TST.W 78(A6); BEQ.W 9bbc2; banked animation 200128 + 48 / + 10.
    case 0x9bb8e:if(!on07_get(c,0x78,2,value))return false;r.pc=(value&65535U)==0U?0x9bbc2:0x9bb96;return true;
    case 0x9bb96:return on07_animation(c,0xb3,ON07_FLYER_BANK,0x48,0x9bbbe);
    case 0x9bbc2:return on07_animation(c,0xb3,ON07_FLYER_BANK,0x10,0x9bbea);
    case 0x9bbbe:r.pc=0x9bbf2;return true;                                   // BRA.W 9bbf2.
    case 0x9bbea:if(!on07_put(c,0x3a,4,0xffffc000U))return false;r.pc=0x9bbf2;return true; // MOVE.L #ffffc000,3a(A6).
    case 0x9bbf2:if(!am_write(c,r.a[6],4,0x9bbf8))return false;r.pc=0x9bbf8;return true; // MOVE.L #9bbf8,(A6).
    // ---- 9bbf8 (installed): TST.W 78(A6); BNE.W 9bc3e.
    case 0x9bbf8:if(!on07_get(c,0x78,2,value))return false;r.pc=(value&65535U)!=0U?0x9bc3e:0x9bc00;return true;
    // MOVE.L 3a(A6),D0; ASR.L #3,D0; SUB.L D0,3a(A6); MOVE.W 46(A6),D0; SUBI.W #100,D0; CMP.W 7a(A6),D0; BLE.W 9bc2e.
    case 0x9bc00:
        if(!on07_get(c,0x3a,4,value))return false;r.d[0]=on07_asr3(value);if(!on07_put(c,0x3a,4,value-r.d[0]))return false;
        if(!on07_get(c,0x46,2,value))return false;am_word(r.d[0],value-0x100U);if(!on07_get(c,0x7a,2,other))return false;
        r.pc=on07_signed_word(r.d[0])<=on07_signed_word(other)?0x9bc2e:0x9bc1a;return true;
    // TST.L 3a(A6); BMI.W 9bc2a; SUBI.L #8000,3a(A6).
    case 0x9bc1a:if(!on07_get(c,0x3a,4,value))return false;r.pc=on07_negative_long(value)?0x9bc2a:0x9bc22;return true;
    case 0x9bc22:if(!on07_get(c,0x3a,4,value) || !on07_put(c,0x3a,4,value-0x8000U))return false;r.pc=0x9bc2a;return true;
    case 0x9bc2a:r.pc=0x9bc3e;return true;                                   // BRA.W 9bc3e.
    // TST.L 3a(A6); BPL.W 9bc3e; ADDI.L #8000,3a(A6).
    case 0x9bc2e:if(!on07_get(c,0x3a,4,value))return false;r.pc=on07_negative_long(value)?0x9bc36:0x9bc3e;return true;
    case 0x9bc36:if(!on07_get(c,0x3a,4,value) || !on07_put(c,0x3a,4,value+0x8000U))return false;r.pc=0x9bc3e;return true;
    case 0x9bc3e:return am_call(c,0x43ea4,0x9bc44);                          // JSR 43ea4.L.
    case 0x9bf38:return am_call(c,0x43ea4,0x9bf3e);
    case 0x9bfd4:return am_call(c,0x43ea4,0x9bfda);
    case 0x9bc44:return am_call(c,0x492c8,0x9bc4a);                          // JSR 492c8.L.
    case 0x9bf3e:return am_call(c,0x492c8,0x9bf44);
    case 0x9bfda:return am_call(c,0x492c8,0x9bfe0);
    case 0x9bc4a:return am_call(c,0x49fc6,0x9bc50);                          // JSR 49fc6.L.
    // MOVE.W 5418(A5),D0; CMP.W 7c(A6),D0; BLT.W 9bc70.
    case 0x9bc50:
        if(!am_read(c,am_index(r.a[5],ON07_PROGRESS),2,value))return false;am_word(r.d[0],value);if(!on07_get(c,0x7c,2,other))return false;
        r.pc=on07_signed_word(r.d[0])<on07_signed_word(other)?0x9bc70:0x9bc5c;return true;
    // MOVE.L #9bc74,(A6); CMPI.W #2,78(A6); BNE.W 9bc70.
    case 0x9bc5c:if(!am_write(c,r.a[6],4,0x9bc74) || !on07_get(c,0x78,2,value))return false;r.pc=(value&65535U)!=2U?0x9bc70:0x9bc6c;return true;
    case 0x9bc6c:r.pc=0x9bf6c;return true;                                   // BRA.W 9bf6c.
    case 0x9bc70:case 0x9bf68:case 0x9c0b2:r.pc=0x9ad06;return true;         // BRA.W 9ad06.

    // ---- 9bf1e (installed by 9bf18) and 9bfba (installed): speed 3a / 36 grows by ASR 3 until |speed| >= 86 / 82.
    case 0x9bf1e:return on07_speed(c,0x3a,0x9bf2a,0x9bf28);
    case 0x9bfba:return on07_speed(c,0x36,0x9bfc6,0x9bfc4);
    case 0x9bf28:r.d[1]=0U-r.d[1];r.pc=0x9bf2a;return true;                  // NEG.L D1.
    case 0x9bfc4:r.d[1]=0U-r.d[1];r.pc=0x9bfc6;return true;
    case 0x9bf2a:return on07_limit(c,0x86,0x9bf38,0x9bf32);
    case 0x9bfc6:return on07_limit(c,0x82,0x9bfd4,0x9bfce);
    case 0x9bf32:return on07_grow(c,0x3a,0x9bf38);
    case 0x9bfce:return on07_grow(c,0x36,0x9bfd4);
    case 0x9bf44:return on07_tilt(c,0x3a,0x9bf52,0x9bf50);
    case 0x9bfe0:return on07_tilt(c,0x36,0x9bfee,0x9bfec);
    case 0x9bf50:am_word(r.d[0],0U-(r.d[0]&65535U));r.pc=0x9bf52;return true; // NEG.W D0.
    case 0x9bfec:am_word(r.d[0],0U-(r.d[0]&65535U));r.pc=0x9bfee;return true;
    case 0x9bf52:return on07_clamp(r,0x9bf5e,0x9bf5a);
    case 0x9bfee:return on07_clamp(r,0x9bffa,0x9bff6);
    case 0x9bf5a:am_byte(r.d[0],3);r.pc=0x9bf5e;return true;                 // MOVE.B #3,D0.
    case 0x9bff6:am_byte(r.d[0],3);r.pc=0x9bffa;return true;
    // MOVE.B D0,9e(A6); JSR 49fc6.L.
    case 0x9bf5e:if(!on07_put(c,0x9e,1,r.d[0]&255U))return false;return am_call(c,0x49fc6,0x9bf68);
    case 0x9bffa:if(!on07_put(c,0x9e,1,r.d[0]&255U))return false;return am_call(c,0x49fc6,0x9c004);

    // ---- 9bf6c: MOVE.W #188e,D0; JSR 3af8.L.
    case 0x9bf6c:am_word(r.d[0],0x188e);return am_call(c,0x3af8,0x9bf76);
    // MOVE.L #4000,36(A6); BTST.B #0,15(A6); BNE.W 9bf8c; NEG.L 36(A6).
    case 0x9bf76:if(!on07_put(c,0x36,4,0x4000) || !on07_get(c,0x15,1,value))return false;r.pc=(value&1U)!=0U?0x9bf8c:0x9bf88;return true;
    case 0x9bf88:if(!on07_get(c,0x36,4,value) || !on07_put(c,0x36,4,0U-value))return false;r.pc=0x9bf8c;return true;
    // MOVE.W #b3,20(A6); MOVEA.L #9c0bc,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x9bf8c:if(!on07_put(c,0x20,2,0xb3))return false;r.a[1]=ON07_FLYER_LIST;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x9bfa2);
    case 0x9bfa2:r.a[0]=ON07_INTERVALS;return am_call(c,0x490ba,0x9bfae);   // LEA cc22c.L,A0; JSR 490ba.L.
    // MOVE.W D0,D0; MOVE.W D0,9a(A6); MOVE.L #9bfba,(A6).
    case 0x9bfae:if(!on07_put(c,0x9a,2,r.d[0]&65535U) || !am_write(c,r.a[6],4,0x9bfba))return false;r.pc=0x9bfba;return true;
    // TST.W 90(A6); BEQ.W 9c0b2; SUBQ.W #1,9a(A6); BCC.W 9c0b2 (borrow only from 0).
    case 0x9c004:if(!on07_get(c,0x90,2,value))return false;r.pc=(value&65535U)==0U?0x9c0b2:0x9c00c;return true;
    case 0x9c00c:if(!on07_decrement(c,0x9a,value))return false;r.pc=(value&65535U)!=0U?0x9c0b2:0x9c014;return true;
    // SUBQ.W #1,90(A6); LEA cc22c.L,A0; JSR 490ba.L.
    case 0x9c014:if(!on07_decrement(c,0x90,value))return false;r.a[0]=ON07_INTERVALS;return am_call(c,0x490ba,0x9c024);
    // MOVE.W D0,D0; MOVE.W D0,9a(A6); MOVEA.L #9b370,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0x9c024:if(!on07_put(c,0x9a,2,r.d[0]&65535U))return false;r.a[0]=0x9b370;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x9c03a);
    case 0x9c03a:return on07_carry(c,0x9c050,0x9c03e);                        // BCC.W 9c050 (C returned by 28ae).
    case 0x9c06c:return on07_carry(c,0x9c07e,0x9c070);                        // BCC.W 9c07e (C returned by 28ae).
    // MOVE.W #0,D0; MOVE.W #0,D1 (CLR.W D0; CLR.W D1); JSR 4970a.L (boundary).
    case 0x9c03e:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0x9c04c);
    case 0x9c070:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0x9c07a);
    case 0x9c04c:r.carry=AnimationCarrySet;r.pc=0x9c050;return true;         // ORI.B #1,CCR.
    case 0x9c07a:r.carry=AnimationCarrySet;r.pc=0x9c07e;return true;
    // MOVE.W #0,9a(A0); JSR 491b6.L (boundary, N06).
    case 0x9c050:if(!am_write(c,am_index(r.a[0],0x9a),2,0))return false;return am_call(c,0x491b6,0x9c05c);
    // MOVEA.L #9b164,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0x9c05c:r.a[0]=0x9b164;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x9c06c);
    // MOVE.W #1,a0(A0); MOVE.W #0,D0; BTST.B #0,15(A6); BNE.W 9c09e.
    case 0x9c07e:
        if(!am_write(c,am_index(r.a[0],0xa0),2,1))return false;am_word(r.d[0],0);if(!on07_get(c,0x15,1,value))return false;
        r.pc=(value&1U)!=0U?0x9c09e:0x9c092;return true;
    // SUBI.W #40,D0; ADD.W D0,2e(A0) (9c092, then BRA.W 9c0a6) / SUB.W D0,2e(A0) (9c09e).
    case 0x9c092:case 0x9c09e:{
        const std::uint32_t address=am_index(r.a[0],0x2e);am_word(r.d[0],r.d[0]-0x40U);if(!am_read(c,address,2,value))return false;
        if(!am_write(c,address,2,(r.pc==0x9c092?value+r.d[0]:value-r.d[0])&65535U))return false;r.pc=0x9c0a6;return true;}
    // MOVE.W 32(A6),D0; SUB.W 7a(A6),D0; MOVE.W D0,32(A0).
    case 0x9c0a6:
        if(!on07_get(c,0x32,2,value) || !on07_get(c,0x7a,2,other))return false;am_word(r.d[0],value-other);
        if(!am_write(c,am_index(r.a[0],0x32),2,r.d[0]&65535U))return false;r.pc=0x9c0b2;return true;

    // ---- bbb9e (callback): MOVE.W 78(A6),68(A6); MOVE.W 78(A6),1e(A6); MOVE.W #e5c,D0; JSR 4a496.L.
    case 0xbbb9e:
        if(!on07_get(c,0x78,2,value) || !on07_put(c,0x68,2,value) || !on07_get(c,0x78,2,value) || !on07_put(c,0x1e,2,value))return false;
        am_word(r.d[0],0xe5c);return am_call(c,0x4a496,0xbbbb4);
    // MOVE.L #0,7a(A6); MOVE.W 76(A6),D0; BNE.W bbc10.
    case 0xbbbb4:if(!on07_put(c,0x7a,4,0) || !on07_get(c,0x76,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)!=0U?0xbbc10:0xbbbc4;return true;
    // MOVE.L #bba7e / #bbb3e,7a(A6); MOVE.W #12c,54(A6); c6a96 (75, 22 / 23).
    case 0xbbbc4:if(!on07_put(c,0x7a,4,0xbba7e) || !on07_put(c,0x54,2,0x12c))return false;return on07_palette_object(c,0x75,0x22,0xbbbe4);
    case 0xbbc18:if(!on07_put(c,0x7a,4,0xbbb3e) || !on07_put(c,0x54,2,0x12c))return false;return on07_palette_object(c,0x75,0x23,0xbbc38);
    case 0xbbc6c:return on07_palette_object(c,0x75,0x24,0xbbc7e);
    case 0xbbcb2:return on07_palette_object(c,0x75,0x25,0xbbcc4);
    case 0xbbcf8:return on07_palette_object(c,0x75,0x26,0xbbd0a);
    case 0xbbbe4:return on07_animation(c,0x213,ON07_STILL_BANK,0x88,0xbbc0c);
    case 0xbbc38:return on07_animation(c,0x213,ON07_STILL_BANK,0x8c,0xbbc60);
    case 0xbbc7e:return on07_animation(c,0x213,ON07_STILL_BANK,0x90,0xbbca6);
    case 0xbbcc4:return on07_animation(c,0x213,ON07_STILL_BANK,0x94,0xbbcec);
    case 0xbbd0a:return on07_animation(c,0x213,ON07_STILL_BANK,0x98,0xbbd32);
    case 0xbbc0c:case 0xbbc60:case 0xbbca6:case 0xbbcec:case 0xbbd32:r.pc=0xbbd36;return true; // BRA.W bbd36.
    // CMPI.W #1..#4,D0; BNE.W next test.
    case 0xbbc10:r.pc=(r.d[0]&65535U)!=1U?0xbbc64:0xbbc18;return true;
    case 0xbbc64:r.pc=(r.d[0]&65535U)!=2U?0xbbcaa:0xbbc6c;return true;
    case 0xbbcaa:r.pc=(r.d[0]&65535U)!=3U?0xbbcf0:0xbbcb2;return true;
    case 0xbbcf0:r.pc=(r.d[0]&65535U)!=4U?0xbbd36:0xbbcf8;return true;
    case 0xbbd36:if(!am_write(c,r.a[6],4,0xbbd3c))return false;r.pc=0xbbd3c;return true; // MOVE.L #bbd3c,(A6).
    // ---- bbd3c (installed): JSR 43e34.L (above); JSR 49fc6.L; CMPI.W #1,76(A6); BGT.W bbdae.
    case 0xbbd42:return am_call(c,0x49fc6,0xbbd48);
    case 0xbbd48:if(!on07_get(c,0x76,2,value))return false;r.pc=on07_signed_word(value)>1?0xbbdae:0xbbd52;return true;
    case 0xbbd52:return am_call(c,0x4b54e,0xbbd58);                          // JSR 4b54e.L.
    case 0xbbd58:return on07_carry(c,0xbbd60,0xbbd5c);                        // BCC.W bbd60 (C returned by 4b54e).
    case 0xbbd5c:if(!on07_put(c,0x5e,1,0))return false;r.pc=0xbbd60;return true; // CLR.B 5e(A6).
    // BTST.B #7,61(A6); BEQ.W bbdae.
    case 0xbbd60:if(!on07_get(c,0x61,1,value))return false;r.pc=(value&0x80U)==0U?0xbbdae:0xbbd6a;return true;
    case 0xbbd6a:am_word(r.d[0],0x1a31);return am_call(c,0x3af8,0xbbd74);    // MOVE.W #1a31,D0; JSR 3af8.L.
    case 0xbbd74:return am_call(c,0x49a58,0xbbd7a);                          // JSR 49a58.L.
    // ANDI.W #3,D0; ADDQ.W #2,D0; JSR 1a3ae.L.
    case 0xbbd7a:am_word(r.d[0],(r.d[0]&3U)+2U);return am_call(c,0x1a3ae,0xbbd86);
    case 0xbbd86:r.a[1]=ON07_SPLASH;return am_call(c,0xd3802,0xbbd90);      // LEA bbdc0(PC),A1; JSR d3802.L (boundary).
    case 0xbbd90:return am_call(c,0x46ef4,0xbbd96);                          // JSR 46ef4.L.
    // MOVE.L #18000,D0; MOVE.L #fffe8000,D1; JSR 1aa40.L (boundary).
    case 0xbbd96:r.d[0]=0x18000;r.d[1]=0xfffe8000U;return am_call(c,0x1aa40,0xbbda8);
    // MOVE.L 7a(A6),D0; BEQ.W bbdbe; MOVEA.L D0,A0; JSR 4706c.L.
    case 0xbbdae:if(!on07_get(c,0x7a,4,value))return false;r.d[0]=value;r.pc=value==0U?0xbbdbe:0xbbdb6;return true;
    case 0xbbdb6:r.a[0]=r.d[0];return am_call(c,0x4706c,0xbbdbe);
    default:return am_error(c,"unsupported animation objects n07 PC");
    }
}
}
