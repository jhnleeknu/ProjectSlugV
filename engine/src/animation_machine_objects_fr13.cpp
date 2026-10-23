#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool ofr13_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr13_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR #bit,d16(An) (a memory operand: BYTE, bit modulo 8). op 0 tests, 1 sets, 2 clears; old is the bit before (the Z of the
// instruction is old = 0).
bool ofr13_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!ofr13_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return ofr13_put(c,base,displacement,1,op==1U?(value|mask):(value&~mask));
}
// BTST #bit,d16(A6); BEQ.W zero_pc (the bit clear) / BNE one_pc (the bit set).
bool ofr13_btst(AnimationMachineContext& c,unsigned int displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    bool old=false;if(!ofr13_bit(c,c.s.a[6],displacement,bit,0,old))return false;
    c.s.pc=old?one_pc:zero_pc;return true;
}
// TST.W d16(A6); BNE.W other_pc (the WORD 0 -> zero_pc).
bool ofr13_test(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr13_get(c,c.s.a[6],displacement,2,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// BCC / BCS on the known C returned to the block: clear -> clear_pc, set -> set_pc; Unknown is a checked error.
bool ofr13_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr13 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #value,(A6) followed by next_pc (the value is entered only when it is next_pc; otherwise it is written only).
bool ofr13_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr13_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// ASR.L #n (n = 1..31): arithmetic right shift of the LONG (the sign bit fills the vacated bits; no signed shift).
std::uint32_t ofr13_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t shifted=value>>n;return (value&0x80000000U)!=0U?(shifted|~(0xffffffffU>>n)):shifted;
}
// The signed value of a LONG (CMPI.L followed by a signed Bcc: the exact signed comparison of the two LONGs; no conversion of an out-of-range value).
std::int64_t ofr13_signed_long(std::uint32_t value) {
    return static_cast<std::int64_t>(value&0x7fffffffU)-static_cast<std::int64_t>(value&0x80000000U);
}
// The signed value of the low WORD (CMP.W followed by a signed Bcc).
std::int32_t ofr13_signed_word(std::uint32_t value) {
    return static_cast<std::int32_t>(value&0x7fffU)-static_cast<std::int32_t>(value&0x8000U);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus; FR4 ofr4_bank_anim, FR12 ofr12_bank_anim).
bool ofr13_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=r.a[6]+0x26U;
    if(!ofr13_put(c,r.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr13_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=r.a[6]+0x26U;
    if(!ofr13_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!ofr13_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 8a(A6),20(A6); MOVEA.L #anim,A1; MOVE.W #100,D0; JSR 49f8c.l (ccbc8 .. ccc6a: the anim pointer is a ROM constant).
bool ofr13_anim(AnimationMachineContext& c,std::uint32_t anim,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr13_get(c,r.a[6],0x8a,2,value) || !ofr13_put(c,r.a[6],0x20,2,value))return false;
    r.a[1]=anim;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.L #target,D0; SUB.L 3a(A6),D0; ASR.L #5,D0; ADD.L D0,3a(A6); JSR 4be34.l (d1654 / d170e: LONG 3a eased toward target by 1/32).
bool ofr13_ease(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr13_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ofr13_asr(target-value,5);
    if(!ofr13_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;return am_call(c,0x4be34,return_pc);
}
// MOVEA.L #child,A0; MOVE.W #n,D0; MOVEA.L #100bf4,A1; JSR 2986.l (bfcfa / d159e: the 2986 children bfd48 / d15c4).
bool ofr13_spawn(AnimationMachineContext& c,std::uint32_t child,std::uint32_t n,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;r.a[0]=child;am_word(r.d[0],n);r.a[1]=0x100bf4;return am_call(c,0x2986,return_pc);
}
}
// Objects FR13 (207 block starts, contract docs/analysis/animation-machine-frontier-fr13-contract.md, area C plan 10.5 FR13 row): the area-D code that
// the extended-input IO observation reaches after FR12 -- the FR10 later-unit successors 70f60 (facing test -> BYTE 63), 70fcc / 71028 (installs
// written only), 70ff8 (MOVE.L A0,(A6): the LONG of the table 70d72 written as the next callback), the FR12 later-unit successors 71682 / 717c2, the
// table 70d72 callback 71622, the installs 717e8 (49a58 twice -> LONG 64 / 36) / 71884, 719f8, 71f2c .. 72114 (705ca C, 70302 -> 71fe2 TST.B D0 /
// 71fe4 BEQ with the Z recomputed from D0.B, the signed LONG clamp 7209c .. 720c0, the EOR.W sign test 720e0), 7224c, the FR11 later-unit successors
// b6d90 (signed WORD 42 compare -> BYTE 15 bit 0) / bfcfa (2986 child bfd48), the FR11 table c54b2 entries c54ba / c54d6 -> c5520, c554c, the item
// handler b44ac (MOVEQ #5,D1; JSR 1c356; the RTS b450c passes the C of 1c356 to the FR2 consumer b46ac), the FR4 table cc82e entry cc852 (-> FR4
// cdc1c), the animation tail cc8b4 (JSR cca76, the guard CMPI.B #1b and the computed jump JMP cc8de(PC,D0.W): the 27-entry BRA.W table, only the
// executed entry cc8f6 transcribed -> ccbc0 anim select by WORD 8c), the interpreter callbacks cca5a / d159e (2986 child d15c4: d1636 .. d177a).
// ROM data: the bank-window LONGs 2000d0 / 2000d4 / 2001c0 / 200080 / 200090 and the LONGs they point to (live bus, no limit test); the anim
// constants of ccbc0 (ce758 ce7c4 d0060 cf126 d00e0 d07f8), 6fe78 (4ae4a) and d13a4 (1ab80) are only passed on.  MOVE.L #v,(A6) enters v only when v
// is the next PC.  The 10 C consumers 716bc 71a6e 72102 722cc bfd94 c5586 d172a d177a (49fc6), 71f30 (705ca), d16a2 (1ab80) read a known C or fail;
// the RTS b450c passes the C of 1c356 (FR2 b46ac reads it).  71fe4 recomputes the Z of the TST.B D0 of 71fe2 (the only path into it).
bool animation_objects_fr13_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool old=false;
    switch(r.pc) {
    case 0xb450c:case 0xbfd40:case 0xbfd9e:case 0xc5590:case 0xcc94a:case 0xd16ac:return am_return(c);   // RTS.
    case 0xbfd42:case 0xbfd98:case 0xc558a:case 0xd16a6:r.pc=0x2a00;return true;                        // JMP 2a00.l.
    // ---- 70f60 (FR10 70f4e): SUBI.W #1800,D7; BTST #0,15(A6); SEQ.B D0; EXT.W D0; EOR.W D7,D0; BMI.W 70f7e (bit 15 of the WORD) / 70f74.
    case 0x70f60:
        am_word(r.d[7],r.d[7]-0x1800U);if(!ofr13_bit(c,r.a[6],0x15,0,0,old))return false;am_byte(r.d[0],old?0U:0xffU);
        am_word(r.d[0],(r.d[0]&0x80U)!=0U?(0xff00U|(r.d[0]&0xffU)):(r.d[0]&0xffU));am_word(r.d[0],r.d[0]^r.d[7]);
        r.pc=(r.d[0]&0x8000U)!=0U?0x70f7e:0x70f74;return true;
    case 0x70f74:if(!ofr13_put(c,r.a[6],0x63,1,1))return false;r.pc=0x70f84;return true;             // MOVE.B #1,63(A6); BRA.W 70f84.
    case 0x70f7e:if(!ofr13_put(c,r.a[6],0x63,1,2))return false;r.pc=0x70f84;return true;             // MOVE.B #2,63(A6) -> FR10 70f84.
    case 0x70fcc:return ofr13_install(c,0x71468,0x70fd2);                                              // MOVE.L #71468,(A6) (written only).
    case 0x70ff8:if(!ofr13_put(c,r.a[6],0,4,r.a[0]))return false;r.pc=0x70ffa;return true;          // MOVE.L A0,(A6) (written only).
    case 0x71028:return ofr13_install(c,0x72f8a,0x7102e);                                              // MOVE.L #72f8a,(A6) (written only).
    // ---- 71622 (the table 70d72 entry 4): TST.W 9c(A6); BNE.W 71656; the bank anims 3 / 2000d0 / 88 and b / 2000d4 / a4 -> 71682.
    case 0x71622:return ofr13_test(c,0x9c,0x7162a,0x71656);
    case 0x7162a:return ofr13_bank_anim(c,3,0x2000d0,0x88,0x71652);
    case 0x71656:return ofr13_bank_anim(c,0xb,0x2000d4,0xa4,0x7167e);
    case 0x71652:r.pc=0x7167e;return true;                                                            // BRA.W 7167e.
    case 0x7167e:r.pc=0x71682;return true;                                                            // BRA.W 71682.
    // MOVE.W 7a(A6),78(A6); MOVE.L #0,64(A6); MOVE.L #71696,(A6) (next PC).
    case 0x71682:
        if(!ofr13_get(c,r.a[6],0x7a,2,value) || !ofr13_put(c,r.a[6],0x78,2,value) || !ofr13_put(c,r.a[6],0x64,4,0))return false;
        return ofr13_install(c,0x71696,0x71696);
    case 0x71696:return am_call(c,0x4be06,0x7169c);                                                   // JSR 4be06.l.
    case 0x7169c:return ofr13_btst(c,0x15,7,0x716b0,0x716a6);                                         // BTST.B #7,15(A6); BEQ.W 716b0.
    case 0x716a6:case 0x71a62:case 0x71fb6:case 0x720f6:case 0x722c0:case 0xd1704:return am_call(c,0x4bfa4,r.pc+6U);   // JSR 4bfa4.l.
    case 0x716ac:r.pc=0x716b6;return true;                                                            // BRA.W 716b6.
    case 0x716b0:return am_call(c,0x4be2c,0x716b6);                                                   // JSR 4be2c.l.
    case 0x716b6:case 0x71888:case 0x71a68:case 0x71fbc:case 0x720fc:case 0x722c6:case 0xbfd8e:case 0xc5580:case 0xd166a:case 0xd1724:
    case 0xd1774:return am_call(c,0x49fc6,r.pc+6U);                                                   // JSR 49fc6.l.
    case 0x716bc:return ofr13_carry(c,0x716c6,0x716c0);                                               // BCC.W 716c6 (C of 49fc6).
    case 0x716c0:case 0x71a72:case 0x722d0:return ofr13_install(c,0x70c0c,r.pc+6U);                 // MOVE.L #70c0c,(A6) (written only).
    case 0x716c6:case 0x718c4:case 0x71a7c:case 0x722d6:r.pc=0x72dd2;return true;                    // BRA.W 72dd2.
    // ---- 717c2 (FR12 717ae BCC fall-through): MOVE.L #717e8,(A6) (written only) -> FR12 717c8.
    case 0x717c2:return ofr13_install(c,0x717e8,0x717c8);
    // ---- 717e8: TST.W 9c(A6); BNE.W 7181c; the bank anims 3 / 2000d0 / 180 and b / 2000d4 / 1cc.
    case 0x717e8:return ofr13_test(c,0x9c,0x717f0,0x7181c);
    case 0x717f0:return ofr13_bank_anim(c,3,0x2000d0,0x180,0x71818);
    case 0x7181c:return ofr13_bank_anim(c,0xb,0x2000d4,0x1cc,0x71844);
    case 0x71818:r.pc=0x71844;return true;                                                            // BRA.W 71844.
    // MOVE.L 64(A6),36(A6); MOVE.L #8a000,3a(A6); JSR 49a58.l.
    case 0x71844:
        if(!ofr13_get(c,r.a[6],0x64,4,value) || !ofr13_put(c,r.a[6],0x36,4,value) || !ofr13_put(c,r.a[6],0x3a,4,0x8a000))return false;
        return am_call(c,0x49a58,0x71858);
    case 0x71858:am_word(r.d[1],r.d[0]);return am_call(c,0x49a58,0x71860);                           // MOVE.W D0,D1; JSR 49a58.l.
    // ADD.W D1,D0; EXT.L D0; ADDI.L #28000,D0; BTST #0,15(A6); BNE.W 71876 / 71874 (FR14).
    case 0x71860:
        am_word(r.d[0],r.d[0]+r.d[1]);r.d[0]=am_extend_word(r.d[0])+0x28000U;return ofr13_btst(c,0x15,0,0x71874,0x71876);
    // MOVE.L D0,64(A6); MOVE.L D0,36(A6); MOVE.L #71884,(A6) (next PC).
    case 0x71876:if(!ofr13_put(c,r.a[6],0x64,4,r.d[0]) || !ofr13_put(c,r.a[6],0x36,4,r.d[0]))return false;return ofr13_install(c,0x71884,0x71884);
    case 0x71884:return am_call(c,0x702cc,0x71888);                                                   // BSR.W 702cc.
    // TST.W 3a(A6); BPL.W 718ae (bit 15 of the WORD).
    case 0x7188e:if(!ofr13_get(c,r.a[6],0x3a,2,value))return false;r.pc=(value&0x8000U)!=0U?0x71896:0x718ae;return true;
    case 0x71896:r.a[0]=0x6fe78;return am_call(c,0x4ae4a,0x718a0);                                  // LEA 6fe78(PC),A0; JSR 4ae4a.l.
    case 0x718a0:r.pc=(r.d[0]&0xffU)==6U?0x718a8:0x718ae;return true;                                // CMPI.B #6,D0; BNE.W 718ae.
    case 0x718a8:return ofr13_install(c,0x718ec,0x718ae);                                              // MOVE.L #718ec,(A6) (written only).
    case 0x718ae:return ofr13_btst(c,0x15,7,0x718c4,0x718b8);                                         // BTST.B #7,15(A6); BEQ.W 718c4.
    // BCLR #3,15(A6); MOVE.L #719f8,(A6) (written only).
    case 0x718b8:if(!ofr13_bit(c,r.a[6],0x15,3,2,old))return false;return ofr13_install(c,0x719f8,0x718c4);
    // ---- 719f8: TST.W 9c(A6); BNE.W 71a2c; the bank anims 3 / 2000d0 / 188 and b / 2000d4 / 1d4.
    case 0x719f8:return ofr13_test(c,0x9c,0x71a00,0x71a2c);
    case 0x71a00:return ofr13_bank_anim(c,3,0x2000d0,0x188,0x71a28);
    case 0x71a2c:return ofr13_bank_anim(c,0xb,0x2000d4,0x1d4,0x71a54);
    case 0x71a28:r.pc=0x71a54;return true;                                                            // BRA.W 71a54.
    case 0x71a54:if(!ofr13_put(c,r.a[6],0x64,4,0))return false;return ofr13_install(c,0x71a62,0x71a62);   // MOVE.L #0,64(A6); MOVE.L #71a62,(A6).
    case 0x71a6e:return ofr13_carry(c,0x71a78,0x71a72);                                               // BCC.W 71a78 (C of 49fc6).
    case 0x71a78:return am_call(c,0x703f6,0x71a7c);                                                   // JSR 703f6(PC).
    // ---- 71f2c: BSR.W 705ca; BCC.W 71f42 (C of 705ca) / JSR 49a58.l; ANDI.W #1f,D0; ADD.W D0,88(A6).
    case 0x71f2c:return am_call(c,0x705ca,0x71f30);
    case 0x71f30:return ofr13_carry(c,0x71f42,0x71f34);
    case 0x71f34:return am_call(c,0x49a58,0x71f3a);                                                   // JSR 49a58.l.
    case 0x71f3a:
        am_word(r.d[0],r.d[0]&0x1fU);if(!ofr13_get(c,r.a[6],0x88,2,value) || !ofr13_put(c,r.a[6],0x88,2,value+r.d[0]))return false;
        r.pc=0x71f42;return true;
    // TST.W 9c(A6); BNE.W 71f76; the bank anims 3 / 2000d0 / 104 and b / 2000d4 / 4.
    case 0x71f42:return ofr13_test(c,0x9c,0x71f4a,0x71f76);
    case 0x71f4a:return ofr13_bank_anim(c,3,0x2000d0,0x104,0x71f72);
    case 0x71f76:return ofr13_bank_anim(c,0xb,0x2000d4,0x4,0x71f9e);
    case 0x71f72:r.pc=0x71f9e;return true;                                                            // BRA.W 71f9e.
    case 0x71f9e:if(!ofr13_put(c,r.a[6],0x64,4,0))return false;return ofr13_install(c,0x71fac,0x71fac);   // MOVE.L #0,64(A6); MOVE.L #71fac,(A6).
    case 0x71fac:return ofr13_btst(c,0x15,7,0x722da,0x71fb6);                                         // BTST.B #7,15(A6); BEQ.W 722da (FR12).
    // MOVE.W 8e(A6),D0; SUB.W 42(A6),D0; BPL.W 71fd0 (bit 15 of the WORD difference) / NEG.W D0.
    case 0x71fc2:
        if(!ofr13_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[0],value);if(!ofr13_get(c,r.a[6],0x42,2,value))return false;
        am_word(r.d[0],r.d[0]-value);r.pc=(r.d[0]&0x8000U)!=0U?0x71fce:0x71fd0;return true;
    case 0x71fce:am_word(r.d[0],0U-r.d[0]);r.pc=0x71fd0;return true;                                // NEG.W D0.
    case 0x71fd0:r.pc=(r.d[0]&0xffffU)<0x10U?0x71fde:0x71fd8;return true;                            // CMPI.W #10,D0; BCS.W 71fde (unsigned WORD).
    case 0x71fd8:return ofr13_install(c,0x72040,0x71fde);                                              // MOVE.L #72040,(A6) (written only).
    case 0x71fde:return am_call(c,0x70302,0x71fe2);                                                   // BSR.W 70302.
    case 0x71fe2:r.pc=0x71fe4;return true;                                                            // TST.B D0 (flags only).
    case 0x71fe4:r.pc=(r.d[0]&0xffU)==0U?0x72000:0x71fe8;return true;   // BEQ.W 72000: the Z of TST.B D0 (71fe2) recomputed from D0.B (decision 4).
    case 0x71fe8:r.pc=(r.d[0]&0xffU)==1U?0x71ff0:0x71ffa;return true;                                // CMPI.B #1,D0; BNE.W 71ffa.
    case 0x71ff0:return ofr13_install(c,0x721b8,0x72000);                                              // MOVE.L #721b8,(A6); BRA.W 72000 (written only).
    case 0x71ffa:case 0x72008:return ofr13_install(c,0x7224c,r.pc+6U);                               // MOVE.L #7224c,(A6) (written only).
    // SUBQ.W #1,88(A6); BPL.W 7200e (bit 15 of the new WORD).
    case 0x72000:
        if(!ofr13_get(c,r.a[6],0x88,2,value) || !ofr13_put(c,r.a[6],0x88,2,value-1U))return false;r.pc=((value-1U)&0x8000U)!=0U?0x72008:0x7200e;return true;
    case 0x7200e:return ofr13_btst(c,0x82,0,0x72018,0x7201e);                                         // BTST.B #0,82(A6); BNE.W 7201e.
    case 0x72018:return ofr13_install(c,0x72118,0x7201e);                                              // MOVE.L #72118,(A6) (written only).
    case 0x7201e:return ofr13_test(c,0x7c,0x72026,0x7202c);                                           // TST.W 7c(A6); BNE.W 7202c.
    case 0x72026:return ofr13_install(c,0x73192,0x7202c);                                              // MOVE.L #73192,(A6) (written only).
    // CMPI.B #40,6f(A6); BEQ.W 7203c / MOVE.L #7224c,(A6) (written only).
    case 0x7202c:if(!ofr13_get(c,r.a[6],0x6f,1,value))return false;r.pc=value==0x40U?0x7203c:0x72036;return true;
    case 0x72036:return ofr13_install(c,0x7224c,0x7203c);
    case 0x7203c:r.pc=0x72d66;return true;                                                            // BRA.W 72d66.
    // ---- 72040: TST.W 9c(A6); BNE.W 72074; the bank anims 3 / 2000d0 / 64 and b / 2000d4 / 4.
    case 0x72040:return ofr13_test(c,0x9c,0x72048,0x72074);
    case 0x72048:return ofr13_bank_anim(c,3,0x2000d0,0x64,0x72070);
    case 0x72074:return ofr13_bank_anim(c,0xb,0x2000d4,0x4,0x7209c);
    case 0x72070:r.pc=0x7209c;return true;                                                            // BRA.W 7209c.
    // MOVE.L 8e(A6),D0; SUB.L 42(A6),D0; ASR.L #5,D0; CMPI.L #18000,D0; BLE.W 720b6 (signed LONG) / MOVE.L #18000,D0.
    case 0x7209c:
        if(!ofr13_get(c,r.a[6],0x8e,4,value))return false;r.d[0]=value;if(!ofr13_get(c,r.a[6],0x42,4,value))return false;
        r.d[0]=ofr13_asr(r.d[0]-value,5);r.pc=ofr13_signed_long(r.d[0])<=0x18000?0x720b6:0x720b0;return true;
    case 0x720b0:r.d[0]=0x18000;r.pc=0x720b6;return true;
    // CMPI.L #fffe8000,D0; BGE.W 720c6 (signed LONG) / MOVE.L #fffe8000,D0.
    case 0x720b6:r.pc=ofr13_signed_long(r.d[0])>=-0x18000?0x720c6:0x720c0;return true;
    case 0x720c0:r.d[0]=0xfffe8000U;r.pc=0x720c6;return true;
    // MOVE.L D0,64(A6); MOVE.W #18,8a(A6); MOVE.L #720d6,(A6) (next PC).
    case 0x720c6:if(!ofr13_put(c,r.a[6],0x64,4,r.d[0]) || !ofr13_put(c,r.a[6],0x8a,2,0x18))return false;return ofr13_install(c,0x720d6,0x720d6);
    case 0x720d6:return ofr13_btst(c,0x82,7,0x720f6,0x720e0);                                         // BTST.B #7,82(A6); BEQ.W 720f6.
    // BTST #0,15(A6); SNE.B D0; MOVE.B 64(A6),D1; EOR.W D0,D1; BPL.W 720f6 (bit 15 of the WORD: bits 8..15 of D0 / D1 as before) / NEG.L 64(A6).
    case 0x720e0:
        if(!ofr13_bit(c,r.a[6],0x15,0,0,old))return false;am_byte(r.d[0],old?0xffU:0U);if(!ofr13_get(c,r.a[6],0x64,1,value))return false;
        am_byte(r.d[1],value);am_word(r.d[1],r.d[1]^r.d[0]);r.pc=(r.d[1]&0x8000U)!=0U?0x720f2:0x720f6;return true;
    case 0x720f2:if(!ofr13_get(c,r.a[6],0x64,4,value) || !ofr13_put(c,r.a[6],0x64,4,0U-value))return false;r.pc=0x720f6;return true;   // NEG.L 64(A6).
    case 0x72102:return ofr13_carry(c,0x7210c,0x72106);                                               // BCC.W 7210c (C of 49fc6).
    case 0x72106:return ofr13_install(c,0x71f2c,0x7210c);                                              // MOVE.L #71f2c,(A6) (written only).
    // SUBQ.W #1,8a(A6); BEQ.W 71f2c (the new WORD 0) / BRA.W 71fde.
    case 0x7210c:
        if(!ofr13_get(c,r.a[6],0x8a,2,value) || !ofr13_put(c,r.a[6],0x8a,2,value-1U))return false;r.pc=((value-1U)&0xffffU)==0U?0x71f2c:0x72114;return true;
    case 0x72114:r.pc=0x71fde;return true;                                                            // BRA.W 71fde.
    // ---- 7224c: TST.W 9c(A6); BNE.W 72280; the bank anims 3 / 2000d0 / 68 and b / 2000d4 / 10.
    case 0x7224c:return ofr13_test(c,0x9c,0x72254,0x72280);
    case 0x72254:return ofr13_bank_anim(c,3,0x2000d0,0x68,0x7227c);
    case 0x72280:return ofr13_bank_anim(c,0xb,0x2000d4,0x10,0x722a8);
    case 0x7227c:r.pc=0x722a8;return true;                                                            // BRA.W 722a8.
    case 0x722a8:if(!ofr13_put(c,r.a[6],0x64,4,0))return false;return ofr13_install(c,0x722b6,0x722b6);   // MOVE.L #0,64(A6); MOVE.L #722b6,(A6).
    case 0x722b6:return ofr13_btst(c,0x15,7,0x722da,0x722c0);                                         // BTST.B #7,15(A6); BEQ.W 722da (FR12).
    case 0x722cc:return ofr13_carry(c,0x722d6,0x722d0);                                               // BCC.W 722d6 (C of 49fc6).
    // ---- b44ac (item record handler, FR2 b46aa JSR (A1)): MOVEQ #5,D1; BRA.W b4506 / JSR 1c356.l / RTS (b450c passes the C of 1c356).
    case 0xb44ac:r.d[1]=5;r.pc=0xb4506;return true;
    case 0xb4506:return am_call(c,0x1c356,0xb450c);
    // ---- b6d90 (FR11 later-unit stop): MOVE.W 42(A6),D0; CMP.W 42(A0),D0; BLE.W b6da6 (signed WORD) / BCLR #0,15(A6); BRA.W b6dac.
    case 0xb6d90:
        if(!ofr13_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value);if(!ofr13_get(c,r.a[0],0x42,2,value))return false;
        r.pc=ofr13_signed_word(r.d[0])<=ofr13_signed_word(value)?0xb6da6:0xb6d9c;return true;
    case 0xb6d9c:if(!ofr13_bit(c,r.a[6],0x15,0,2,old))return false;r.pc=0xb6dac;return true;
    case 0xb6da6:if(!ofr13_bit(c,r.a[6],0x15,0,1,old))return false;r.pc=0xb6dac;return true;     // BSET #0,15(A6) -> FR11 b6dac.
    // ---- bfcfa (FR11 bfcee BNE): the 2986 child bfd48 (D0 = 1e); MOVEQ #0,D0; MOVEQ #0,D1; JSR 4970a.l; MOVE.B 1a(A6),14(A6); MOVE.W #2,a4(A6);
    // MOVE.L #bfd2c,(A6) (next PC); SUBQ.W #1,a4(A6); BMI.W bfd42 / JSR b4030.l; JSR b4334.l; RTS.
    case 0xbfcfa:return ofr13_spawn(c,0xbfd48,0x1e,0xbfd10);
    case 0xbfd10:case 0xd15b4:r.d[0]=0;r.d[1]=0;return am_call(c,r.pc==0xbfd10U?0x4970aU:0x49214U,r.pc+10U);
    case 0xbfd1a:
        if(!ofr13_get(c,r.a[6],0x1a,1,value) || !ofr13_put(c,r.a[6],0x14,1,value) || !ofr13_put(c,r.a[6],0xa4,2,2))return false;
        return ofr13_install(c,0xbfd2c,0xbfd2c);
    case 0xbfd2c:
        if(!ofr13_get(c,r.a[6],0xa4,2,value) || !ofr13_put(c,r.a[6],0xa4,2,value-1U))return false;r.pc=((value-1U)&0x8000U)!=0U?0xbfd42:0xbfd34;return true;
    case 0xbfd34:return am_call(c,0xb4030,0xbfd3a);                                                   // JSR b4030.l.
    case 0xbfd3a:return am_call(c,0xb4334,0xbfd40);                                                   // JSR b4334.l.
    // ---- bfd48 (the 2986 child of bfcfa): the bank anim 1e3 / 2001c0 / c; MOVE.W #6f,D0; MOVE.W #3,D1; MOVE.B #0,D2; JSR c6a96.l; MOVE.L #bfd88,(A6);
    // JSR 43e34.l; JSR 49fc6.l; BCC.W bfd9e (RTS) / JMP 2a00.l.
    case 0xbfd48:return ofr13_bank_anim(c,0x1e3,0x2001c0,0xc,0xbfd70);
    case 0xbfd70:am_word(r.d[0],0x6f);am_word(r.d[1],3);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xbfd82);
    case 0xbfd82:return ofr13_install(c,0xbfd88,0xbfd88);
    case 0xbfd88:case 0xd176e:return am_call(c,0x43e34,r.pc+6U);                                     // JSR 43e34.l.
    case 0xbfd94:return ofr13_carry(c,0xbfd9e,0xbfd98);                                               // BCC.W bfd9e (C of 49fc6).
    // ---- c54ba / c54d6 (the FR11 table c54b2 entries 2 / 9): BRA.W c5520.  c5520: CLR.B 5e(A6); MOVE.L #c5432,(A6) (written only); BTST #7,61(A6);
    // BEQ.W c553a / MOVE.L #c554c,(A6) (written only); c553a: CLR.B 5e(A6); RTS.
    case 0xc54ba:case 0xc54d6:r.pc=0xc5520;return true;
    case 0xc5520:if(!ofr13_put(c,r.a[6],0x5e,1,0) || !ofr13_put(c,r.a[6],0,4,0xc5432))return false;return ofr13_btst(c,0x61,7,0xc553a,0xc5534);
    case 0xc5534:return ofr13_install(c,0xc554c,0xc553a);
    case 0xc553a:if(!ofr13_put(c,r.a[6],0x5e,1,0))return false;return am_return(c);
    // ---- c554c: the bank anim ba / 200080 / 148; MOVE.L #c557a,(A6) (next PC); JSR 4be06.l; JSR 49fc6.l; BCC.W c5590 (RTS) / JMP 2a00.l.
    case 0xc554c:return ofr13_bank_anim(c,0xba,0x200080,0x148,0xc5574);
    case 0xc5574:return ofr13_install(c,0xc557a,0xc557a);
    case 0xc557a:return am_call(c,0x4be06,0xc5580);
    case 0xc5586:return ofr13_carry(c,0xc5590,0xc558a);                                               // BCC.W c5590 (C of 49fc6).
    // ---- cc852 (the FR4 table cc82e entry 9): BRA.W cdc1c (FR4).  cc8f6 (the table cc8de entry 6): BRA.W ccbc0.
    case 0xcc852:r.pc=0xcdc1c;return true;
    case 0xcc8f6:r.pc=0xccbc0;return true;
    // ---- cc8b4 (JMP from N15 72da0 / 72dc6, B1a 78d54): MOVE.B 5e(A6),D0; BEQ.W cc94a (RTS) / JSR cca76(PC).
    case 0xcc8b4:if(!ofr13_get(c,r.a[6],0x5e,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0xcc94a:0xcc8bc;return true;
    case 0xcc8bc:return am_call(c,0xcca76,0xcc8c0);
    // MOVE.B 5e(A6),D0; MOVE.W #0,5e(A6) (the WORD 5e / 5f); CMPI.B #1b,D0; BCC.W ccbc0 (unsigned BYTE >= 1b).
    case 0xcc8c0:
        if(!ofr13_get(c,r.a[6],0x5e,1,value) || !ofr13_put(c,r.a[6],0x5e,2,0))return false;am_byte(r.d[0],value);
        r.pc=value>=0x1bU?0xccbc0:0xcc8d2;return true;
    // ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; JMP cc8de(PC,D0.W) (decision 2: the 27-entry BRA.W table cc8de..cc94a; the guard of cc8c0 keeps the index
    // 0..1a; the routing decides the entry: cc8f6 (entry 6) is the executed FR13 block, the others unrouted; a larger index is a checked error).
    case 0xcc8d2:
        am_word(r.d[0],r.d[0]&0xffU);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);value=r.d[0]&0xffffU;
        if(value>0x68U)return am_error(c,"unsupported animation objects fr13 jump target");r.pc=0xcc8deU+value;return true;
    // ---- cca5a (the interpreter callback of the script table 4a500 + 23c): MOVEQ #0,D0; MOVE.W (A0),D0; SWAP D0; BTST #0,15(A6); BNE.W cca6c /
    // NEG.L D0; MOVE.L D0,36(A6); MOVE.L D0,64(A6); RTS.
    case 0xcca5a:if(!ofr13_get(c,r.a[0],0,2,value))return false;r.d[0]=value<<16;return ofr13_btst(c,0x15,0,0xcca6a,0xcca6c);
    case 0xcca6a:r.d[0]=0U-r.d[0];r.pc=0xcca6c;return true;
    case 0xcca6c:if(!ofr13_put(c,r.a[6],0x36,4,r.d[0]) || !ofr13_put(c,r.a[6],0x64,4,r.d[0]))return false;return am_return(c);
    // ---- ccbc0: MOVE.W 8c(A6),D0; the anim of WORD 8c (0 ce758, 1 ce7c4, 2 d0060, 3 cf126, 4 d00e0, other d07f8); MOVE.L #cdd2e,(A6); RTS.
    case 0xccbc0:if(!ofr13_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],value);r.pc=value==0U?0xccbc8:0xccbe2;return true;
    case 0xccbe2:r.pc=(r.d[0]&0xffffU)==1U?0xccbea:0xccc04;return true;
    case 0xccc04:r.pc=(r.d[0]&0xffffU)==2U?0xccc0c:0xccc26;return true;
    case 0xccc26:r.pc=(r.d[0]&0xffffU)==3U?0xccc2e:0xccc48;return true;
    case 0xccc48:r.pc=(r.d[0]&0xffffU)==4U?0xccc50:0xccc6a;return true;
    case 0xccbc8:return ofr13_anim(c,0xce758,0xccbde);
    case 0xccbea:return ofr13_anim(c,0xce7c4,0xccc00);
    case 0xccc0c:return ofr13_anim(c,0xd0060,0xccc22);
    case 0xccc2e:return ofr13_anim(c,0xcf126,0xccc44);
    case 0xccc50:return ofr13_anim(c,0xd00e0,0xccc66);
    case 0xccc6a:return ofr13_anim(c,0xd07f8,0xccc80);
    case 0xccbde:case 0xccc00:case 0xccc22:case 0xccc44:case 0xccc66:r.pc=0xccc80;return true;      // BRA.W ccc80.
    case 0xccc80:if(!ofr13_put(c,r.a[6],0,4,0xcdd2e))return false;return am_return(c);               // MOVE.L #cdd2e,(A6) (written only); RTS.
    // ---- d159e (the interpreter callback of the script table 4a500 + 19c): the 2986 child d15c4 (D0 = 14); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.l;
    // JMP 491b6.l.
    case 0xd159e:return ofr13_spawn(c,0xd15c4,0x14,0xd15b4);
    case 0xd15be:r.pc=0x491b6;return true;
    // ---- d15c4 (the 2986 child of d159e): BSET #4,15(A6); MOVE.W #e0ef,68(A6); MOVE.W #e0ef,1e(A6); the bank anim da / 200090 / 8.
    case 0xd15c4:
        if(!ofr13_bit(c,r.a[6],0x15,4,1,old) || !ofr13_put(c,r.a[6],0x68,2,0xe0ef) || !ofr13_put(c,r.a[6],0x1e,2,0xe0ef))return false;
        return ofr13_bank_anim(c,0xda,0x200090,0x8,0xd15fe);
    case 0xd15fe:case 0xd160c:am_word(r.d[0],r.pc==0xd15feU?0x212U:0x213U);am_byte(r.d[1],0);return am_call(c,0x8ebe,r.pc+14U);   // MOVE.W #n,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVEQ #18,D0; ADDI.W #18,32(A6); MOVE.L #18000,D1; BTST #0,15(A6); BNE.W d1636 / d1632 (FR14).
    case 0xd161a:
        r.d[0]=0x18;if(!ofr13_get(c,r.a[6],0x32,2,value) || !ofr13_put(c,r.a[6],0x32,2,value+0x18U))return false;r.d[1]=0x18000;
        return ofr13_btst(c,0x15,0,0xd1632,0xd1636);
    // ADD.W D0,2e(A6); MOVE.L D1,36(A6); MOVE.L #d1644,(A6) (next PC).
    case 0xd1636:
        if(!ofr13_get(c,r.a[6],0x2e,2,value) || !ofr13_put(c,r.a[6],0x2e,2,value+r.d[0]) || !ofr13_put(c,r.a[6],0x36,4,r.d[1]))return false;
        return ofr13_install(c,0xd1644,0xd1644);
    case 0xd1644:return ofr13_btst(c,0x15,7,0xd1654,0xd164e);                                         // BTST.B #7,15(A6); BEQ.W d1654.
    case 0xd164e:return ofr13_install(c,0xd16ae,0xd1654);                                              // MOVE.L #d16ae,(A6) (written only).
    case 0xd1654:return ofr13_ease(c,0xfff00000U,0xd166a);
    // MOVE.W -7ff2(A5),D0; ANDI.W #3,D0; BNE.W d1698.
    case 0xd1670:if(!ofr13_get(c,r.a[5],0x800e,2,value))return false;am_word(r.d[0],value&3U);r.pc=(value&3U)!=0U?0xd1698:0xd167c;return true;
    // MOVE.B 14(A6),D0; CMP.B 19(A6),D0; BEQ.W d1692 (the BYTEs equal).
    case 0xd167c:
        if(!ofr13_get(c,r.a[6],0x14,1,value))return false;am_byte(r.d[0],value);if(!ofr13_get(c,r.a[6],0x19,1,value))return false;
        r.pc=(r.d[0]&0xffU)==value?0xd1692:0xd1688;return true;
    case 0xd1688:if(!ofr13_get(c,r.a[6],0x19,1,value) || !ofr13_put(c,r.a[6],0x14,1,value))return false;r.pc=0xd1698;return true;   // MOVE.B 19,14; BRA.W.
    case 0xd1692:if(!ofr13_get(c,r.a[6],0x1a,1,value) || !ofr13_put(c,r.a[6],0x14,1,value))return false;r.pc=0xd1698;return true;   // MOVE.B 1a,14.
    case 0xd1698:r.a[0]=0xd13a4;return am_call(c,0x1ab80,0xd16a2);                                  // LEA d13a4(PC),A0; JSR 1ab80.l.
    case 0xd16a2:return ofr13_carry(c,0xd16ac,0xd16a6);                                               // BCC.W d16ac (C of 1ab80).
    // ---- d16ae: the bank anim da / 200090 / 4; MOVE.L #0,36 / 3a / 64(A6); MOVE.W #78,76(A6); MOVE.L #d16fa,(A6) (next PC).
    case 0xd16ae:return ofr13_bank_anim(c,0xda,0x200090,0x4,0xd16d6);
    case 0xd16d6:
        if(!ofr13_put(c,r.a[6],0x36,4,0) || !ofr13_put(c,r.a[6],0x3a,4,0) || !ofr13_put(c,r.a[6],0x64,4,0) || !ofr13_put(c,r.a[6],0x76,2,0x78))return false;
        return ofr13_install(c,0xd16fa,0xd16fa);
    case 0xd16fa:return ofr13_btst(c,0x15,7,0xd170e,0xd1704);                                         // BTST.B #7,15(A6); BEQ.W d170e.
    case 0xd170a:r.pc=0xd1724;return true;                                                            // BRA.W d1724.
    case 0xd170e:return ofr13_ease(c,0xfff40000U,0xd1724);
    case 0xd172a:return ofr13_carry(c,0xd173c,0xd172e);                                               // BCC.W d173c (C of 49fc6).
    // SUBQ.W #1,76(A6); BCC.W d173c (no borrow: the old WORD was not 0) / MOVE.L #d1740,(A6) (written only).
    case 0xd172e:if(!ofr13_get(c,r.a[6],0x76,2,value) || !ofr13_put(c,r.a[6],0x76,2,value-1U))return false;r.pc=value!=0U?0xd173c:0xd1736;return true;
    case 0xd1736:return ofr13_install(c,0xd1740,0xd173c);
    case 0xd173c:r.pc=0xd1670;return true;                                                            // BRA.W d1670.
    // ---- d1740: the bank anim da / 200090 / c; MOVE.L #d176e,(A6) (next PC); JSR 43e34.l; JSR 49fc6.l; BCC.W d1670 / d177e (FR14).
    case 0xd1740:return ofr13_bank_anim(c,0xda,0x200090,0xc,0xd1768);
    case 0xd1768:return ofr13_install(c,0xd176e,0xd176e);
    case 0xd177a:return ofr13_carry(c,0xd1670,0xd177e);
    default:return am_error(c,"unsupported animation objects fr13 PC");
    }
}
}
