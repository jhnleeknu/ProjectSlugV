#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool ofr14_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr14_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR #bit,d16(An) (a memory operand: BYTE, bit modulo 8). op 0 tests, 1 sets, 2 clears; old is the bit before (the Z of the
// instruction is old = 0).
bool ofr14_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!ofr14_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return ofr14_put(c,base,displacement,1,op==1U?(value|mask):(value&~mask));
}
// BTST #bit,d16(A6); BEQ.W zero_pc (the bit clear) / BNE one_pc (the bit set).
bool ofr14_btst(AnimationMachineContext& c,unsigned int displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    bool old=false;if(!ofr14_bit(c,c.s.a[6],displacement,bit,0,old))return false;
    c.s.pc=old?one_pc:zero_pc;return true;
}
// BSET #3,61(A6); BEQ.W zero_pc (the bit was clear) / one_pc (it was set already).
bool ofr14_bset(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t one_pc) {
    bool old=false;if(!ofr14_bit(c,c.s.a[6],0x61,3,1,old))return false;
    c.s.pc=old?one_pc:zero_pc;return true;
}
// BCC / BCS on the known C returned to the block: clear -> clear_pc, set -> set_pc; Unknown is a checked error.
bool ofr14_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr14 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #value,(A6) followed by next_pc (the value is entered only when it is next_pc; otherwise it is written only).
bool ofr14_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr14_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// ASR.L #4: arithmetic right shift of the LONG by 4 (the sign bit fills the vacated bits; no signed shift).
std::uint32_t ofr14_asr4(std::uint32_t value) {
    const std::uint32_t shifted=value>>4;return (value&0x80000000U)!=0U?(shifted|0xf0000000U):shifted;
}
// The signed value of the low WORD (CMPI.W followed by BGE).
std::int32_t ofr14_signed_word(std::uint32_t value) {
    return static_cast<std::int32_t>(value&0x7fffU)-static_cast<std::int32_t>(value&0x8000U);
}
// ADD.W D0,d16(A6) (the WORD field only).
bool ofr14_add_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t addend) {
    std::uint32_t value=0;if(!ofr14_get(c,c.s.a[6],displacement,2,value))return false;return ofr14_put(c,c.s.a[6],displacement,2,value+addend);
}
// ADD.L Dn,d16(A6) (the LONG field, modulo 2^32).
bool ofr14_add_long(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t addend) {
    std::uint32_t value=0;if(!ofr14_get(c,c.s.a[6],displacement,4,value))return false;return ofr14_put(c,c.s.a[6],displacement,4,value+addend);
}
// Dn := Dn - LONG d16(A6) (SUB.L d16(A6),Dn); BMI.W minus_pc (bit 31 of the LONG difference) / plus_pc.
bool ofr14_sub_long(AnimationMachineContext& c,std::uint32_t& reg,std::uint32_t displacement,std::uint32_t minus_pc,std::uint32_t plus_pc) {
    std::uint32_t value=0;if(!ofr14_get(c,c.s.a[6],displacement,4,value))return false;reg-=value;
    c.s.pc=(reg&0x80000000U)!=0U?minus_pc:plus_pc;return true;
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus; FR4 ofr4_bank_anim, FR12 / FR13 bank anim).
bool ofr14_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=r.a[6]+0x26U;
    if(!ofr14_put(c,r.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr14_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=r.a[6]+0x26U;
    if(!ofr14_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!ofr14_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 8a(A6),20(A6); MOVEA.L #anim,A1; MOVE.W #100,D0; JSR 49f8c.l (cd118 .. cd34a: the anim pointer is a ROM constant).
bool ofr14_anim(AnimationMachineContext& c,std::uint32_t anim,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr14_get(c,r.a[6],0x8a,2,value) || !ofr14_put(c,r.a[6],0x20,2,value))return false;
    r.a[1]=anim;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// LEA table(PC),A1; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l (3645a / 36532: the fixed ROM
// LONG table 363ae / 36522 read through the live bus at table + sext(4 x WORD 76), no limit test).
bool ofr14_table_anim(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[1]=table;
    if(!ofr14_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 76(A6),D0; LEA 363be(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.l (36474 / 3654c: the sound WORD of the fixed ROM
// table 363be at sext(2 x WORD 76), no limit test).
bool ofr14_table_sound(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr14_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.a[0]=0x363be;am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #4,D0; ADD.W D0,3a(A6); BTST #0,15(A6); BEQ.W plus_pc / minus_pc (3648c / 36564).
bool ofr14_step(AnimationMachineContext& c,std::uint32_t plus_pc,std::uint32_t minus_pc) {
    am_word(c.s.d[0],4);if(!ofr14_add_word(c,0x3a,c.s.d[0]))return false;return ofr14_btst(c,0x15,0,plus_pc,minus_pc);
}
}
// Objects FR14 (200 block starts, contract docs/analysis/animation-machine-frontier-fr14-contract.md, area C plan 10.5 FR14 row): the last area-D
// code that the extended-input IO observation reaches -- the C5 2986 child 3643e (table 1cc04 entry 1: 1aa3a bit 3 -> the WORD 76 anim tables 363ae /
// 36522 and the sound table 363be, the 1/16 approach 364aa / 36588 of LONG 36 / 3a toward 0 / fff00000 / fffc0000 with ASR.L #4, BSET #3,61, the
// 1ab80 screen test of the record 363a6; 3657c is the BRA.W target of the unrouted 2986 child 365fc), the FR12 / FR13 later-unit fall-throughs
// 7177a / 71786 / 71874 (NEG.L D0) and d1632 (NEG.W D0; NEG.L D1), the stage-event op 08 child b5c34 (b5c60 .. b5d56: 4c0ac, 490ba, the bank anim
// 1b3 / 2001a8 / 94, the install b5cec with the helpers b6056 / b6084 / b60c4, the LONG table b6280 by BYTE 8a, the 4b54e / b60da / 1aa7e C tests,
// the player tests b60da (49392 / 4941e) with the counters b7ae4 / b7af0 (MOVEM.L D0/A2-A3)), the FR1 kind-record handler c0d68 (the signed
// WORD 42 test, c6a96, the bank anim 1eb / 2001c4 / 44, the install c0dc8 with b4958 / b4ab0 / b4334), the FR4 table cc7ac entry 3 cc7b8 (-> cd0fe:
// the BYTE 5f / BYTE 15 bit 0 sign test, BYTE 7a, the WORD 8c anim selection, LONG 3a := 20000, cdd2e written), the FR13 later-unit stop d177e
// (4ae4a, 8ff4, the bank anim d2 / 20008c / 10, the install d17e0).  ROM data: the bank-window LONGs 200034 / 2001a8 / 2001c4 / 20008c and the
// LONGs they point to, the tables 363ae / 36522 / 363be / b6280 (live bus, no limit test); the records 363a6 (1ab80) / b6270 (1aa7e) / b6278
// (4941e) / c8544 (490ba) / d1cba (4ae4a) and the anim constants of cd0fe are only passed on.  MOVE.L #v,(A6) enters v only when v is the next PC.
// The 12 C consumers 36516 365f0 (1ab80), b5d30 (4b54e), b5d3e (b60da: b6128 Clear / b6146 Set), b6042 (1aa7e), b60ec b610e (49392), b60fa b611c
// (4941e), b7b02 (49392, across MOVEM.L), c0dfc (b4334), d17ec (49fc6) read a known C or fail; b6128 / b6146 set their own C.
bool animation_objects_fr14_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool old=false;
    switch(r.pc) {
    case 0x36520:case 0x365fa:case 0xb604c:case 0xb6082:case 0xb60c2:case 0xb7b2e:case 0xc0e28:case 0xd17f6:return am_return(c);   // RTS.
    case 0x364fa:case 0x3651a:case 0x365ca:case 0x365f4:case 0xd17f0:r.pc=0x2a00;return true;            // JMP 2a00.l.
    // ---- 3643e (the C5 2986 child of 1cc38, table 1cc04 entry 1): MOVE.W #22,20(A6); MOVE.L 200034.l,22(A6); JSR 1aa3a.l.
    case 0x3643e:
        if(!ofr14_put(c,r.a[6],0x20,2,0x22) || !am_read(c,0x200034,4,value) || !ofr14_put(c,r.a[6],0x22,4,value))return false;
        return am_call(c,0x1aa3a,0x36452);
    case 0x36452:r.pc=(r.d[0]&8U)!=0U?0x36532:0x3645a;return true;                                     // BTST.B #3,D0; BNE.W 36532.
    case 0x3645a:return ofr14_table_anim(c,0x363ae,0x36474);
    case 0x36474:return ofr14_table_sound(c,0x3648c);
    case 0x3648c:return ofr14_step(c,0x364a0,0x3649e);
    case 0x36564:return ofr14_step(c,0x36578,0x36576);
    case 0x3649e:case 0x36576:am_word(r.d[0],0U-r.d[0]);r.pc=r.pc+2U;return true;                  // NEG.W D0.
    // ADD.W D0,36(A6); MOVE.L #364aa,(A6) (next PC).
    case 0x364a0:if(!ofr14_add_word(c,0x36,r.d[0]))return false;return ofr14_install(c,0x364aa,0x364aa);
    // MOVEQ #0,D2; MOVE.L #fff00000 / #fffc0000,D3; SUB.L 36(A6),D2; BMI.W (bit 31 of the LONG difference).
    case 0x364aa:r.d[2]=0;r.d[3]=0xfff00000U;return ofr14_sub_long(c,r.d[2],0x36,0x364c0,0x364ba);
    case 0x36588:r.d[2]=0;r.d[3]=0xfffc0000U;return ofr14_sub_long(c,r.d[2],0x36,0x3659e,0x36598);
    case 0x364ba:case 0x36598:r.d[2]+=0xfU;r.pc=r.pc+6U;return true;                                  // ADDI.L #f,D2.
    case 0x364ce:case 0x365ac:r.d[3]+=0xfU;r.pc=r.pc+6U;return true;                                  // ADDI.L #f,D3.
    // ASR.L #4,D2; ADD.L D2,36(A6); SUB.L 3a(A6),D3; BMI.W (bit 31 of the LONG difference).
    case 0x364c0:r.d[2]=ofr14_asr4(r.d[2]);if(!ofr14_add_long(c,0x36,r.d[2]))return false;return ofr14_sub_long(c,r.d[3],0x3a,0x364d4,0x364ce);
    case 0x3659e:r.d[2]=ofr14_asr4(r.d[2]);if(!ofr14_add_long(c,0x36,r.d[2]))return false;return ofr14_sub_long(c,r.d[3],0x3a,0x365b2,0x365ac);
    // ASR.L #4,D3; ADD.L D3,3a(A6); MOVE.L 3a(A6),-(A7); JSR 4be34.l.
    case 0x364d4:
        r.d[3]=ofr14_asr4(r.d[3]);if(!ofr14_add_long(c,0x3a,r.d[3]) || !ofr14_get(c,r.a[6],0x3a,4,value) || !am_push(c,4,value))return false;
        return am_call(c,0x4be34,0x364e4);
    // MOVE.L (A7)+,D0; BTST #7,15(A6); BEQ.W 36502 / 364f0.
    case 0x364e4:if(!am_pop(c,4,value))return false;r.d[0]=value;return ofr14_btst(c,0x15,7,0x36502,0x364f0);
    case 0x364f0:case 0x365c0:return ofr14_bset(c,r.pc==0x364f0U?0x36500U:0x365d4U,r.pc+10U);           // BSET #3,61(A6); BEQ.W (the bit was clear).
    case 0x36500:r.d[0]=0U-r.d[0];r.pc=0x36502;return true;                                          // NEG.L D0.
    case 0x36502:if(!ofr14_put(c,r.a[6],0x3a,4,r.d[0]))return false;return am_call(c,0x49fc6,0x3650c);   // MOVE.L D0,3a(A6); JSR 49fc6.l.
    case 0x3650c:case 0x365e6:r.a[0]=0x363a6;return am_call(c,0x1ab80,r.pc+10U);                    // LEA 363a6(PC),A0; JSR 1ab80.l.
    case 0x36516:return ofr14_carry(c,0x36520,0x3651a);                                               // BCC.W 36520 (C of 1ab80).
    case 0x365f0:return ofr14_carry(c,0x365fa,0x365f4);                                               // BCC.W 365fa (C of 1ab80).
    // ---- 36532 (36452 BNE): the anim table 36522, the sound table 363be.
    case 0x36532:return ofr14_table_anim(c,0x36522,0x3654c);
    case 0x3654c:return ofr14_table_sound(c,0x36564);
    case 0x36578:if(!ofr14_add_word(c,0x36,r.d[0]))return false;r.pc=0x3657c;return true;            // ADD.W D0,36(A6).
    // MOVE.B #1e,7f(A6); MOVE.L #36588,(A6) (next PC; 3657c is also the BRA.W target of the unrouted 2986 child 365fc).
    case 0x3657c:if(!ofr14_put(c,r.a[6],0x7f,1,0x1e))return false;return ofr14_install(c,0x36588,0x36588);
    // ASR.L #4,D3; ADD.L D3,3a(A6); SUBQ.B #1,7f(A6); BCC.W 365da (no borrow: the old BYTE was not 0) / 365c0.
    case 0x365b2:
        r.d[3]=ofr14_asr4(r.d[3]);if(!ofr14_add_long(c,0x3a,r.d[3]) || !ofr14_get(c,r.a[6],0x7f,1,value) || !ofr14_put(c,r.a[6],0x7f,1,value-1U))return false;
        r.pc=value!=0U?0x365da:0x365c0;return true;
    case 0x365d4:if(!ofr14_put(c,r.a[6],0x7f,1,0x1e))return false;r.pc=0x365da;return true;          // MOVE.B #1e,7f(A6).
    case 0x365da:return am_call(c,0x4be34,0x365e0);                                                   // JSR 4be34.l.
    case 0x365e0:case 0xb5cf0:case 0xd17e6:return am_call(c,0x49fc6,r.pc+6U);                        // JSR 49fc6.l.
    // ---- 7177a / 71786 / 71874 (the FR12 / FR13 later-unit fall-throughs): NEG.L D0 -> FR12 7177c / 71788, FR13 71876.
    case 0x7177a:case 0x71786:case 0x71874:r.d[0]=0U-r.d[0];r.pc=r.pc+2U;return true;
    // ---- d1632 (FR13 d161a BTST fall-through): NEG.W D0; NEG.L D1 -> FR13 d1636.
    case 0xd1632:am_word(r.d[0],0U-r.d[0]);r.d[1]=0U-r.d[1];r.pc=0xd1636;return true;
    // ---- b5c34 (the stage-event op 08 child, table e8cc0 entry 8f): MOVE.B #0,8b(A6); MOVE.W #9b,D0; MOVE.B #0,D1; JSR 8ebe.l; BRA.W b5c60.
    case 0xb5c34:if(!ofr14_put(c,r.a[6],0x8b,1,0))return false;am_word(r.d[0],0x9b);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xb5c48);
    case 0xb5c48:r.pc=0xb5c60;return true;
    case 0xb5c60:if(!ofr14_get(c,r.a[6],0x76,2,value))return false;r.pc=value==0U?0xb5c78:0xb5c68;return true;   // TST.W 76(A6); BEQ.W b5c78.
    // BSET #0,15(A6); MOVE.L #ffff8000,D0; BRA.W b5c84.
    case 0xb5c68:if(!ofr14_bit(c,r.a[6],0x15,0,1,old))return false;r.d[0]=0xffff8000U;r.pc=0xb5c84;return true;
    // BCLR #0,15(A6); MOVE.L #8000,D0.
    case 0xb5c78:if(!ofr14_bit(c,r.a[6],0x15,0,2,old))return false;r.d[0]=0x8000U;r.pc=0xb5c84;return true;
    // MOVE.L D0,64(A6); CLR.L D0; MOVE.W 7c(A6),D0; SWAP D0; MOVE.L D0,80(A6); JSR 4c0ac.l.
    case 0xb5c84:
        if(!ofr14_put(c,r.a[6],0x64,4,r.d[0]) || !ofr14_get(c,r.a[6],0x7c,2,value))return false;r.d[0]=value<<16;
        if(!ofr14_put(c,r.a[6],0x80,4,r.d[0]))return false;return am_call(c,0x4c0ac,0xb5c9a);
    // MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); LEA c8544.l,A0; JSR 490ba.l.
    case 0xb5c9a:
        if(!ofr14_put(c,r.a[6],0x68,2,0x8820) || !ofr14_put(c,r.a[6],0x1e,2,0x8820))return false;r.a[0]=0xc8544;return am_call(c,0x490ba,0xb5cb2);
    // MOVE.W D0,86(A6); CLR.L 64(A6); CLR.B 8a(A6); the bank anim 1b3 / 2001a8 / 94.
    case 0xb5cb2:
        if(!ofr14_put(c,r.a[6],0x86,2,r.d[0]) || !ofr14_put(c,r.a[6],0x64,4,0) || !ofr14_put(c,r.a[6],0x8a,1,0))return false;
        return ofr14_bank_anim(c,0x1b3,0x2001a8,0x94,0xb5ce6);
    case 0xb5ce6:return ofr14_install(c,0xb5cec,0xb5cec);                                              // MOVE.L #b5cec,(A6) (next PC).
    case 0xb5cec:return am_call(c,0xb6056,0xb5cf0);                                                   // JSR b6056(PC).
    // LEA 26(A6),A0; TST.W 4(A0); BNE.W b5d2a.
    case 0xb5cf6:r.a[0]=r.a[6]+0x26U;if(!ofr14_get(c,r.a[0],4,2,value))return false;r.pc=value!=0U?0xb5d2a:0xb5d02;return true;
    // MOVEQ #0,D0; MOVE.B 8a(A6),D0; ADDQ.B #1,D0; ANDI.B #f,D0; MOVE.B D0,8a(A6); LEA b6280(PC),A0; ADD.W D0,D0 twice; MOVE.L (A0,D0.W),D1;
    // MOVE.L D1,64(A6); LEA 26(A6),A0; JSR b6084(PC).
    case 0xb5d02:
        r.d[0]=0;if(!ofr14_get(c,r.a[6],0x8a,1,value))return false;am_byte(r.d[0],(value+1U)&0xfU);if(!ofr14_put(c,r.a[6],0x8a,1,r.d[0]))return false;
        r.a[0]=0xb6280;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;
        r.d[1]=value;if(!ofr14_put(c,r.a[6],0x64,4,r.d[1]))return false;r.a[0]=r.a[6]+0x26U;return am_call(c,0xb6084,0xb5d2a);
    case 0xb5d2a:return am_call(c,0x4b54e,0xb5d30);                                                   // JSR 4b54e.l.
    case 0xb5d30:return ofr14_carry(c,0xb5d3a,0xb5d34);                                               // BCC.W b5d3a (C of 4b54e).
    case 0xb5d34:return ofr14_install(c,0xb5d5a,0xb5d3a);                                              // MOVE.L #b5d5a,(A6) (written only).
    case 0xb5d3a:return am_call(c,0xb60da,0xb5d3e);                                                   // JSR b60da(PC).
    case 0xb5d3e:return ofr14_carry(c,0xb5d48,0xb5d42);                                               // BCC.W b5d48 (C of b60da).
    case 0xb5d42:return ofr14_install(c,0xb5e46,0xb5d48);                                              // MOVE.L #b5e46,(A6) (written only).
    // TST.L 80(A6); BNE.W b5d56 / MOVE.L #b5f00,(A6) (written only).
    case 0xb5d48:if(!ofr14_get(c,r.a[6],0x80,4,value))return false;r.pc=value!=0U?0xb5d56:0xb5d50;return true;
    case 0xb5d50:return ofr14_install(c,0xb5f00,0xb5d56);
    case 0xb5d56:r.pc=0xb6038;return true;                                                            // BRA.W b6038.
    // ---- b6038: LEA b6270(PC),A0; JSR 1aa7e.l; BCC.W b604c (RTS) / MOVE.L #b604e,(A6) (written only).
    case 0xb6038:r.a[0]=0xb6270;return am_call(c,0x1aa7e,0xb6042);
    case 0xb6042:return ofr14_carry(c,0xb604c,0xb6046);                                               // BCC.W b604c (C of 1aa7e).
    case 0xb6046:return ofr14_install(c,0xb604e,0xb604c);
    // ---- b6056: BTST #7,15(A6); BEQ.W b606a / JSR 4bfa4.l; BRA.W b6082 / JSR 4be2c.l; BTST #7,15(A6); BEQ.W b6082 / CLR.L 36 / 3a(A6); RTS.
    case 0xb6056:return ofr14_btst(c,0x15,7,0xb606a,0xb6060);
    case 0xb6060:case 0xb6092:case 0xc0ddc:return am_call(c,0x4bfa4,r.pc+6U);                        // JSR 4bfa4.l.
    case 0xb6066:r.pc=0xb6082;return true;                                                            // BRA.W b6082.
    case 0xb606a:case 0xc0dd2:return am_call(c,0x4be2c,r.pc+6U);                                      // JSR 4be2c.l.
    case 0xb6070:return ofr14_btst(c,0x15,7,0xb6082,0xb607a);
    case 0xb607a:if(!ofr14_put(c,r.a[6],0x36,4,0) || !ofr14_put(c,r.a[6],0x3a,4,0))return false;r.pc=0xb6082;return true;
    // ---- b6084: BTST #7,15(A6); BEQ.W b60c2 (RTS) / JSR b60c4(PC); JSR 4bfa4.l.
    case 0xb6084:return ofr14_btst(c,0x15,7,0xb60c2,0xb608e);
    case 0xb608e:return am_call(c,0xb60c4,0xb6092);
    // MOVE.L 64(A6),D0; TST.L D0; BPL.W b60a4 / NEG.L D0.
    case 0xb6098:if(!ofr14_get(c,r.a[6],0x64,4,value))return false;r.d[0]=value;r.pc=(value&0x80000000U)!=0U?0xb60a2:0xb60a4;return true;
    case 0xb60a2:case 0xb60d2:r.d[0]=0U-r.d[0];r.pc=r.pc+2U;return true;                               // NEG.L D0.
    // SUB.L D0,80(A6); TST.L 80(A6); BPL.W b60b4 / CLR.L 80(A6).
    case 0xb60a4:
        if(!ofr14_get(c,r.a[6],0x80,4,value) || !ofr14_put(c,r.a[6],0x80,4,value-r.d[0]))return false;r.pc=((value-r.d[0])&0x80000000U)!=0U?0xb60b0:0xb60b4;
        return true;
    case 0xb60b0:if(!ofr14_put(c,r.a[6],0x80,4,0))return false;r.pc=0xb60b4;return true;
    // CLR.L D0; MOVE.L D0,64 / 36 / 3a(A6).
    case 0xb60b4:
        r.d[0]=0;if(!ofr14_put(c,r.a[6],0x64,4,0) || !ofr14_put(c,r.a[6],0x36,4,0) || !ofr14_put(c,r.a[6],0x3a,4,0))return false;r.pc=0xb60c2;return true;
    // ---- b60c4: MOVE.L 64(A6),D0; BTST #0,15(A6); BEQ.W b60d4 / NEG.L D0; MOVE.L D0,64(A6); RTS.
    case 0xb60c4:if(!ofr14_get(c,r.a[6],0x64,4,value))return false;r.d[0]=value;return ofr14_btst(c,0x15,0,0xb60d4,0xb60d2);
    case 0xb60d4:if(!ofr14_put(c,r.a[6],0x64,4,r.d[0]))return false;return am_return(c);
    // ---- b60da: BTST #0,61(A6); BNE.W b6146 (Set) / CLR.W D0; JSR 49392.l.
    case 0xb60da:return ofr14_btst(c,0x61,0,0xb60e4,0xb6146);
    case 0xb60e4:am_word(r.d[0],0);return am_call(c,0x49392,0xb60ec);
    case 0xb60ec:return ofr14_carry(c,0xb6104,0xb60f0);                                               // BCC.W b6104 (C of 49392).
    case 0xb60f0:case 0xb6112:r.a[1]=0xb6278;return am_call(c,0x4941e,r.pc+10U);                    // LEA b6278(PC),A1; JSR 4941e.l.
    case 0xb60fa:return ofr14_carry(c,0xb60fe,0xb6104);                                               // BCS.W b6104 (C of 4941e).
    case 0xb60fe:am_word(r.d[0],0);r.pc=0xb612e;return true;                                        // CLR.W D0; BRA.W b612e.
    case 0xb6104:am_word(r.d[0],1);return am_call(c,0x49392,0xb610e);                               // MOVE.W #1,D0; JSR 49392.l.
    case 0xb610e:return ofr14_carry(c,0xb6128,0xb6112);                                               // BCC.W b6128 (C of 49392).
    case 0xb611c:return ofr14_carry(c,0xb6120,0xb6128);                                               // BCS.W b6128 (C of 4941e).
    case 0xb6120:am_word(r.d[0],1);r.pc=0xb612e;return true;                                        // MOVE.W #1,D0; BRA.W b612e.
    case 0xb6128:r.carry=AnimationCarryClear;return am_return(c);                                    // ANDI.B #fe,CCR; RTS.
    // TST.B 8b(A6); BNE.W b6140 / JSR b7af0.l; BRA.W b6146 / JSR b7ae4.l; ORI.B #1,CCR; RTS.
    case 0xb612e:if(!ofr14_get(c,r.a[6],0x8b,1,value))return false;r.pc=value!=0U?0xb6140:0xb6136;return true;
    case 0xb6136:return am_call(c,0xb7af0,0xb613c);
    case 0xb613c:r.pc=0xb6146;return true;
    case 0xb6140:return am_call(c,0xb7ae4,0xb6146);
    case 0xb6146:r.carry=AnimationCarrySet;return am_return(c);
    // ---- b7ae4 / b7af0: LEA 5ddf / 5dde(A5),A2; LEA 5de7 / 5de6(A5),A3 -> b7af8: MOVEM.L D0/A2-A3,-(A7) (A3 at the highest LONG, D0 at the
    // lowest); JSR 49392.l.
    case 0xb7ae4:r.a[2]=am_index(r.a[5],0x5ddf);r.a[3]=am_index(r.a[5],0x5de7);r.pc=0xb7af8;return true;
    case 0xb7af0:r.a[2]=am_index(r.a[5],0x5dde);r.a[3]=am_index(r.a[5],0x5de6);r.pc=0xb7af8;return true;
    case 0xb7af8:if(!am_push(c,4,r.a[3]) || !am_push(c,4,r.a[2]) || !am_push(c,4,r.d[0]))return false;return am_call(c,0x49392,0xb7b02);
    // MOVEM.L (A7)+,D0/A2-A3 (the flags stay: the C of 49392); BCC.W b7b2e.
    case 0xb7b02:
        if(!am_pop(c,4,r.d[0]) || !am_pop(c,4,r.a[2]) || !am_pop(c,4,r.a[3]))return false;return ofr14_carry(c,0xb7b2e,0xb7b0a);
    case 0xb7b0a:r.pc=(r.d[0]&0xffU)!=0U?0xb7b18:0xb7b10;return true;                                // TST.B D0; BNE.W b7b18.
    case 0xb7b10:r.a[1]=am_index(r.a[5],0x5ddc);r.pc=0xb7b1e;return true;                           // LEA 5ddc(A5),A1; BRA.W b7b1e.
    case 0xb7b18:r.a[1]=am_index(r.a[5],0x5de4);r.a[2]=r.a[3];r.pc=0xb7b1e;return true;             // LEA 5de4(A5),A1; MOVEA.L A3,A2.
    // ADDQ.W #1,(A1); CMPI.W #64,(A1); BCS.W b7b2c (unsigned WORD below 64) / MOVE.W #63,(A1).
    case 0xb7b1e:
        if(!am_read(c,r.a[1],2,value) || !am_write(c,r.a[1],2,(value+1U)&0xffffU) || !am_read(c,r.a[1],2,value))return false;
        r.pc=value<0x64U?0xb7b2c:0xb7b28;return true;
    case 0xb7b28:if(!am_write(c,r.a[1],2,0x63))return false;r.pc=0xb7b2c;return true;
    case 0xb7b2c:if(!am_read(c,r.a[2],1,value) || !am_write(c,r.a[2],1,(value+1U)&0xffU))return false;r.pc=0xb7b2e;return true;   // ADDQ.B #1,(A2).
    // ---- c0d68 (the FR1 kind-record handler, b3484 record 61 LONG 6; FR1 b3f3a / b3fb2 JMP (A0)): MOVE.L #a000,64(A6); CMPI.W #a0,42(A6); BGE.W
    // c0d82 (signed WORD) / NEG.L 64(A6); BRA.W c0d88 / BSET #0,15(A6).
    case 0xc0d68:
        if(!ofr14_put(c,r.a[6],0x64,4,0xa000) || !ofr14_get(c,r.a[6],0x42,2,value))return false;r.pc=ofr14_signed_word(value)>=0xa0?0xc0d82:0xc0d7a;return true;
    case 0xc0d7a:if(!ofr14_get(c,r.a[6],0x64,4,value) || !ofr14_put(c,r.a[6],0x64,4,0U-value))return false;r.pc=0xc0d88;return true;
    case 0xc0d82:if(!ofr14_bit(c,r.a[6],0x15,0,1,old))return false;r.pc=0xc0d88;return true;
    // MOVE.W #70,D0; MOVE.W #11,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xc0d88:am_word(r.d[0],0x70);am_word(r.d[1],0x11);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xc0d9a);
    case 0xc0d9a:return ofr14_bank_anim(c,0x1eb,0x2001c4,0x44,0xc0dc2);
    case 0xc0e00:return ofr14_bank_anim(c,0x1eb,0x2001c4,0x44,0xc0e28);
    case 0xc0dc2:return ofr14_install(c,0xc0dc8,0xc0dc8);                                              // MOVE.L #c0dc8,(A6) (next PC).
    case 0xc0dc8:return ofr14_btst(c,0x15,7,0xc0dd2,0xc0ddc);                                         // BTST.B #7,15(A6); BNE.W c0ddc.
    case 0xc0dd8:r.pc=0xc0de2;return true;                                                            // BRA.W c0de2.
    case 0xc0de2:return am_call(c,0xb4958,0xc0de8);                                                   // JSR b4958.l.
    case 0xc0de8:return am_call(c,0xb4ab0,0xc0dee);                                                   // JSR b4ab0.l.
    case 0xc0dee:r.pc=(r.d[0]&4U)!=0U?0xc1d2e:0xc0df6;return true;                                     // BTST.B #2,D0; BNE.W c1d2e.
    case 0xc0df6:return am_call(c,0xb4334,0xc0dfc);                                                   // JSR b4334.l.
    case 0xc0dfc:return ofr14_carry(c,0xc0e28,0xc0e00);                                               // BCC.W c0e28 (C of b4334).
    // ---- cc7b8 (the FR4 table cc7ac entry 3): BRA.W cd0fe.
    case 0xcc7b8:r.pc=0xcd0fe;return true;
    // ---- cd0fe: MOVE.B 5f(A6),D0; BTST #0,15(A6); SNE.B D1; EOR.B D0,D1; BMI.W cd1d4 (bit 7 of the BYTE) / cd110.
    case 0xcd0fe:
        if(!ofr14_get(c,r.a[6],0x5f,1,value))return false;am_byte(r.d[0],value);if(!ofr14_bit(c,r.a[6],0x15,0,0,old))return false;
        am_byte(r.d[1],old?0xffU:0U);am_byte(r.d[1],r.d[1]^r.d[0]);r.pc=(r.d[1]&0x80U)!=0U?0xcd1d4:0xcd110;return true;
    // MOVE.W 8c(A6),D0; BNE.W (the WORD 8c anim selection: CMPI.W #1 .. #4).
    case 0xcd110:case 0xcd1dc:case 0xcd2a0:
        if(!ofr14_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],value);r.pc=value!=0U?r.pc+0x22U:r.pc+8U;return true;
    case 0xcd132:case 0xcd1fe:case 0xcd2c2:r.pc=(r.d[0]&0xffffU)!=1U?r.pc+0x22U:r.pc+8U;return true;   // CMPI.W #1,D0; BNE.W.
    case 0xcd154:case 0xcd220:case 0xcd2e4:r.pc=(r.d[0]&0xffffU)!=2U?r.pc+0x22U:r.pc+8U;return true;   // CMPI.W #2,D0; BNE.W.
    case 0xcd176:case 0xcd242:case 0xcd306:r.pc=(r.d[0]&0xffffU)!=3U?r.pc+0x22U:r.pc+8U;return true;   // CMPI.W #3,D0; BNE.W.
    case 0xcd198:case 0xcd264:case 0xcd328:r.pc=(r.d[0]&0xffffU)!=4U?r.pc+0x22U:r.pc+8U;return true;   // CMPI.W #4,D0; BNE.W.
    // TST.B 7a(A6); BEQ.W cd2a0.
    case 0xcd1d4:if(!ofr14_get(c,r.a[6],0x7a,1,value))return false;r.pc=value==0U?0xcd2a0:0xcd1dc;return true;
    // the anims of WORD 8c (BYTE 5f / bit 0 sign clear: ce48c cecde cfde4 cf636 d05be d0d26; set with BYTE 7a: ce48c ced72 cfde4 cf636 d05be d0d26;
    // set without: cdf86 ce7c4 cf870 cf126 d00e0 d07f8).
    case 0xcd118:return ofr14_anim(c,0xce48c,0xcd12e);
    case 0xcd13a:return ofr14_anim(c,0xcecde,0xcd150);
    case 0xcd15c:return ofr14_anim(c,0xcfde4,0xcd172);
    case 0xcd17e:return ofr14_anim(c,0xcf636,0xcd194);
    case 0xcd1a0:return ofr14_anim(c,0xd05be,0xcd1b6);
    case 0xcd1ba:return ofr14_anim(c,0xd0d26,0xcd1d0);
    case 0xcd1e4:return ofr14_anim(c,0xce48c,0xcd1fa);
    case 0xcd206:return ofr14_anim(c,0xced72,0xcd21c);
    case 0xcd228:return ofr14_anim(c,0xcfde4,0xcd23e);
    case 0xcd24a:return ofr14_anim(c,0xcf636,0xcd260);
    case 0xcd26c:return ofr14_anim(c,0xd05be,0xcd282);
    case 0xcd286:return ofr14_anim(c,0xd0d26,0xcd29c);
    case 0xcd2a8:return ofr14_anim(c,0xcdf86,0xcd2be);
    case 0xcd2ca:return ofr14_anim(c,0xce7c4,0xcd2e0);
    case 0xcd2ec:return ofr14_anim(c,0xcf870,0xcd302);
    case 0xcd30e:return ofr14_anim(c,0xcf126,0xcd324);
    case 0xcd330:return ofr14_anim(c,0xd00e0,0xcd346);
    case 0xcd34a:return ofr14_anim(c,0xd07f8,0xcd360);
    case 0xcd12e:case 0xcd150:case 0xcd172:case 0xcd194:case 0xcd1b6:r.pc=0xcd1d0;return true;       // BRA.W cd1d0.
    case 0xcd1fa:case 0xcd21c:case 0xcd23e:case 0xcd260:case 0xcd282:r.pc=0xcd29c;return true;       // BRA.W cd29c.
    case 0xcd1d0:case 0xcd29c:case 0xcd2be:case 0xcd2e0:case 0xcd302:case 0xcd324:case 0xcd346:r.pc=0xcd360;return true;   // BRA.W cd360.
    // MOVE.L #20000,3a(A6); MOVE.L #cdd2e,(A6) (written only); RTS.
    case 0xcd360:if(!ofr14_put(c,r.a[6],0x3a,4,0x20000) || !ofr14_put(c,r.a[6],0,4,0xcdd2e))return false;return am_return(c);
    // ---- d177e (the FR13 later-unit stop, d177a BCC Set side): LEA d1cba.l,A0; MOVE.L A0,D0; BEQ.W d1792 / MOVEA.L D0,A0; JSR 4ae4a.l.
    case 0xd177e:r.a[0]=0xd1cba;r.d[0]=r.a[0];r.pc=r.d[0]==0U?0xd1792:0xd178a;return true;
    case 0xd178a:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0xd1792);
    case 0xd1792:return am_call(c,0x8ff4,0xd1798);                                                    // JSR 8ff4.l.
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); the bank anim d2 / 20008c / 10.
    case 0xd1798:
        if(!ofr14_put(c,r.a[6],0x68,2,0x1001) || !ofr14_put(c,r.a[6],0x1e,2,0x1001))return false;return ofr14_bank_anim(c,0xd2,0x20008c,0x10,0xd17cc);
    case 0xd17cc:am_word(r.d[0],0x36b);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xd17da);          // MOVE.W #36b,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0xd17da:return ofr14_install(c,0xd17e0,0xd17e0);                                              // MOVE.L #d17e0,(A6) (next PC).
    case 0xd17e0:return am_call(c,0x43e34,0xd17e6);                                                   // JSR 43e34.l.
    case 0xd17ec:return ofr14_carry(c,0xd17f6,0xd17f0);                                               // BCC.W d17f6 (C of 49fc6).
    default:return am_error(c,"unsupported animation objects fr14 PC");
    }
}
}
