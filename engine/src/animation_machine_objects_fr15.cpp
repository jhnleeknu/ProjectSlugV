#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool ofr15_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr15_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR #bit,d16(An) or Dn,d16(An) (a memory operand: BYTE, bit modulo 8). op 0 tests, 1 sets, 2 clears; old is the bit before (the Z of
// the instruction is old = 0).
bool ofr15_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!ofr15_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return ofr15_put(c,base,displacement,1,op==1U?(value|mask):(value&~mask));
}
// BTST #bit,d16(A6); BEQ.W zero_pc (the bit clear) / one_pc (the bit set).
bool ofr15_btst(AnimationMachineContext& c,unsigned int displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    bool old=false;if(!ofr15_bit(c,c.s.a[6],displacement,bit,0,old))return false;
    c.s.pc=old?one_pc:zero_pc;return true;
}
// BSET #6,61(A6) followed by next_pc.
bool ofr15_bset61(AnimationMachineContext& c,std::uint32_t next_pc) {
    bool old=false;if(!ofr15_bit(c,c.s.a[6],0x61,6,1,old))return false;c.s.pc=next_pc;return true;
}
// BCC / BCS on the known C returned to the block: clear -> clear_pc, set -> set_pc; Unknown is a checked error.  The C is kept (the dispatcher keeps
// it only into the pass block 40b7a).
bool ofr15_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr15 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #value,(A6) followed by next_pc (the value is entered only when it is next_pc; otherwise it is written only).
bool ofr15_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr15_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.W d16(A6),Dn (bits 16..31 kept).
bool ofr15_field_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t& reg) {
    std::uint32_t value=0;if(!ofr15_get(c,c.s.a[6],displacement,2,value))return false;am_word(reg,value);return true;
}
// The low WORD as a signed value (no signed conversion of an out-of-range unsigned).
std::int32_t ofr15_signed_word(std::uint32_t value) {
    return static_cast<std::int32_t>(value&0x7fffU)-static_cast<std::int32_t>(value&0x8000U);
}
// ASR.L #n (n = 1..8): the LONG shifted right with its sign bit filling.
std::uint32_t ofr15_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t shifted=value>>n;return (value&0x80000000U)!=0U?(shifted|~(0xffffffffU>>n)):shifted;
}
// ASR.W #n (n = 1..8): the low WORD shifted right with its sign bit filling (16-bit result; the caller writes it with am_word).
std::uint32_t ofr15_asr_word(std::uint32_t value,unsigned int n) {
    const std::uint32_t word=value&0xffffU;const std::uint32_t shifted=word>>n;
    return (word&0x8000U)!=0U?((shifted|(0xffffU<<(16U-n)))&0xffffU):shifted;
}
// SUB.W Dn,d16(A6) / ADD.W Dn,d16(A6) (the WORD field only).
bool ofr15_add_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,bool subtract) {
    std::uint32_t old=0;if(!ofr15_get(c,c.s.a[6],displacement,2,old))return false;
    return ofr15_put(c,c.s.a[6],displacement,2,subtract?(old-value):(old+value));
}
// ASR.W #1,D0; SUB.W D0,d16(A6) followed by next_pc (e9c16 e9c2a e9c40 e9c52).
bool ofr15_half_sub(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;am_word(r.d[0],ofr15_asr_word(r.d[0],1));if(!ofr15_add_word(c,displacement,r.d[0],true))return false;
    r.pc=next_pc;return true;
}
// MOVE.L 36(A6) / 64(A6),D0; ASR.L #5,D0; SUB.W b4(A6),D0; ASR.W #1,D0; ADD.W D0,b4(A6) (c146c / c14f2; FR12 c10e2 / c118a).
bool ofr15_steer(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr15_get(c,r.a[6],displacement,4,value))return false;r.d[0]=ofr15_asr(value,5);
    if(!ofr15_get(c,r.a[6],0xb4,2,value))return false;am_word(r.d[0],r.d[0]-value);am_word(r.d[0],ofr15_asr_word(r.d[0],1));
    if(!ofr15_add_word(c,0xb4,r.d[0],false))return false;r.pc=next_pc;return true;
}
// MOVE.W b4(A6),D0; ADD.W b2(A6),D0; MOVE.W D0,b2(A6); BTST.B #0,15(A6); BEQ.W zero_pc / one_pc (c147c / c1502).
bool ofr15_angle(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t one_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr15_get(c,r.a[6],0xb4,2,value))return false;am_word(r.d[0],value);if(!ofr15_get(c,r.a[6],0xb2,2,value))return false;
    am_word(r.d[0],r.d[0]+value);if(!ofr15_put(c,r.a[6],0xb2,2,r.d[0]))return false;return ofr15_btst(c,0x15,0,zero_pc,one_pc);
}
// SUBI.W #4000,D0; NEG.W D0; ADDI.W #4000,D0 (c1492 / c1518: the WORD mirrored about 4000).
void ofr15_mirror(AnimationMachineState& r,std::uint32_t next_pc) {
    am_word(r.d[0],r.d[0]-0x4000U);am_word(r.d[0],0U-r.d[0]);am_word(r.d[0],r.d[0]+0x4000U);r.pc=next_pc;
}
// MULU.W #8,D0 (D0.L := unsigned D0.W x 8); SWAP D0; MOVE.B D0,b6(A6) (c149c / c1522: BYTE b6 := the top three bits of the WORD).
bool ofr15_sector(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;r.d[0]=(r.d[0]&0xffffU)*8U;am_swap(r.d[0]);return ofr15_put(c,r.a[6],0xb6,1,r.d[0]);
}
// CMPI.B #k,b6(A6); BEQ.W c1540 (the bundled BEQ.W c0944, Z still set) / other_pc (c1522 / c1536).
bool ofr15_sector_is(AnimationMachineContext& c,std::uint32_t k,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr15_get(c,c.s.a[6],0xb6,1,value))return false;c.s.pc=(value&0xffU)==k?0xc0944U:other_pc;return true;
}
// BTST #2,D0 (register: bit 2 of the LONG); BNE.W c1d2e / next_pc (c14b2 / c1550).
void ofr15_bit2(AnimationMachineState& r,std::uint32_t next_pc) {
    r.pc=(r.d[0]&4U)!=0U?0xc1d2eU:next_pc;
}
// MOVE.W #11a,20(A6); MOVE.L 2000b0.l,22(A6) (the bank-window LONG read through the live bus; 40896 / 40a5a).
bool ofr15_bank(AnimationMachineContext& c) {
    std::uint32_t value=0;
    return ofr15_put(c,c.s.a[6],0x20,2,0x11a) && am_read(c,0x2000b0,4,value) && ofr15_put(c,c.s.a[6],0x22,4,value);
}
// MOVE.W #sound,D0; MOVE.B #1,D1; JSR 8ebe.l (40a5a .. 40a84).
bool ofr15_sound(AnimationMachineContext& c,std::uint32_t sound,std::uint32_t return_pc) {
    am_word(c.s.d[0],sound);am_byte(c.s.d[1],1);return am_call(c,0x8ebe,return_pc);
}
// MOVEQ #0,D2; MOVE.B 76(A6,D1.W),D2; ADD.W D2,D2; MOVEA.L 7e(A6),A0 (ea2fe / ea314 / ea334: the per-index BYTE and the record pointer LONG 7e).
bool ofr15_record(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,am_index(r.a[6]+0x76U,r.d[1]),1,value))return false;r.d[2]=value&0xffU;am_word(r.d[2],r.d[2]+r.d[2]);
    if(!ofr15_get(c,r.a[6],0x7e,4,value))return false;r.a[0]=value;return true;
}
// ... ; MOVE.W 4(A0,D2.W),D2; ADD.W D2,86(A6); RTS (ea2fe / ea334).
bool ofr15_width(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr15_record(c) || !am_read(c,am_index(r.a[0]+4U,r.d[2]),2,value))return false;am_word(r.d[2],value);
    if(!ofr15_add_word(c,0x86,r.d[2],false))return false;return am_return(c);
}
// MOVE.L D3,3c0000.l (the VRAM address / data port LONG).
void ofr15_port(AnimationMachineContext& c,std::uint32_t value) {
    VideoPortWrite port;port.address=0x3c0000;port.size=4;port.value=value;c.ports.push_back(port);
}
// NEG.W Dn; BSR.W 4fe50 (the circle octants 4fe0e .. 4fe32).
bool ofr15_octant(AnimationMachineContext& c,std::uint32_t& reg,std::uint32_t return_pc) {
    am_word(reg,0U-reg);return am_call(c,0x4fe50,return_pc);
}
// EXG.L D4,D5.
void ofr15_exg45(AnimationMachineState& r) {
    const std::uint32_t t=r.d[4];r.d[4]=r.d[5];r.d[5]=t;
}
}
// Objects FR15 (192 block starts, contract docs/analysis/animation-machine-objects-fr15-contract.md, area C plan 11.5 D-1 row, third IO observation): the
// area-D code the other stages and the continue path reach after C11 -- the 2986 callback 3ff14 (49f8c, 496c2, the install 3ff4c: 40964 / 40a1c, the
// player node of WORD 8a (A5 - 7348 / A5 - 7258), the signed WORD 2e compare, 40b60 (4d418 C; 40b72 ORI Set; the RTS 40b7a passes the C), 4d508,
// 4002c written) -> 4076a / 40812 (4b54e, BYTE 61 bits 7 / 6, 405e2 written, 4d766 C, 409e6 the script WORD list of LONG 76 (40a0a ADDA.W), 8d34),
// the 28ae children 40896 (bank anim 11a / 2000b0, 49290, the install 408c0: 288c C, 491c4) and 40a5a (three 8ebe sounds, 4d81c, 496c2, the 28ae
// children 41fe6 (fields only) and 40896), the script callbacks 40bc8 / 6f282 / 6f352 (49a58), 4c2c4 (4bce0, BRA.W 4c2d0), the 2986 child b3dfc
// (1aa3a, b42a2 / b403e, b3ea2), the circle plotter 4fdfc / 4fe50 (the VRAM port LONG 3c0000) with 4fea4 (the WORD table 4fe8a) / 4fec6 and the
// callback 4ff4c -> 4ff5c, the FR1 kind-record handler c13c0 (c6a96, b4304 C, 49a58, c1cf2, the installs c142a / c14d8: b4030, the steer / angle /
// mirror of FR12 c1036, MULU.W #8 sectors with the bundled BEQ c1540 -> c0944, b4958 / b4ab0 / b4334, c1d2e / c1d06), and the 2986 child e9b8a ->
// e9b9a (ea2c6, the LONG tables ea3c4 / ea3ac, two 8ebe sounds, the BYTE 8f loop of the WORD widths, the 2e / 32 clamps, 43e34, 496c2, the computed
// JMP e9c72(PC,D0.W) entry 3 e9c7e) -> ea132 / ea13c (the install ea14c: ea2ca C, ea2e0, the BYTE 8f loop of ea2fe / ea314 (16ea4) / ea334 with the
// WORD table ea37c and BSET / BTST D1 on BYTEs 93 / 92).  ROM data (live bus, no limit test): the bank-window LONG 2000b0, the WORD table 4fe8a, the
// LONG tables ea3c4 / ea3ac and the records they point to, the WORD table ea37c, the script data of LONG 76; 40da0 c1ec0 b42a2 b403e c0924 41fe6 are
// only passed on.  MOVE.L #v,(A6) enters v only when v is the next PC.  The 8 C consumers 3ff78 (40b60), 4084c (4d766), 408c6 (288c), 40ac8 40b06
// (28ae), 40b6e (4d418), c13ee (b4304), ea150 (ea2ca) read a known C or fail; ea2ca (CMP.W) and 40b72 (ORI) produce it, 40b7a passes it; 40acc
// (ORI) sets Set without a reader.  No Z / N crosses an FR15 block boundary (the bundled BEQ c1540 reads the Z of its own block).
bool animation_objects_fr15_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool old=false;
    switch(r.pc) {
    case 0x4088e:case 0x408d8:case 0x40a2c:case 0x4fe4e:case 0x4fec4:case 0x6f35e:case 0xc14c0:case 0xc155e:case 0xea2be:case 0xea332:
        return am_return(c);                                                                        // RTS.
    case 0x40b7a:return am_return(c);                                                               // RTS (passes the C of 40b6e / 40b72).
    case 0x4095e:r.pc=0x2a00;return true;                                                           // JMP 2a00.l.
    // ---- 3ff14 (the 2986 callback written by C11 3fef4): MOVEA.L #40da0,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3ff14:r.a[1]=0x40da0;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3ff24);
    // MOVE.B #ff,92(A6); MOVE.B 1b(A6),14(A6); MOVE.L #0,76(A6); MOVE.L #0,56(A6); JSR 496c2.l.
    case 0x3ff24:
        if(!ofr15_put(c,r.a[6],0x92,1,0xff) || !ofr15_get(c,r.a[6],0x1b,1,value) || !ofr15_put(c,r.a[6],0x14,1,value) ||
           !ofr15_put(c,r.a[6],0x76,4,0) || !ofr15_put(c,r.a[6],0x56,4,0))return false;
        return am_call(c,0x496c2,0x3ff46);
    case 0x3ff46:return ofr15_install(c,0x3ff4c,0x3ff4c);                                          // MOVE.L #3ff4c,(A6) (next PC).
    case 0x3ff4c:return am_call(c,0x40964,0x3ff50);                                                 // BSR.W 40964.
    case 0x3ff50:return am_call(c,0x40a1c,0x3ff54);                                                 // BSR.W 40a1c.
    case 0x3ff54:if(!ofr15_get(c,r.a[6],0x8a,2,value))return false;r.pc=(value&0xffffU)!=0U?0x3ff64:0x3ff5c;return true;   // TST.W 8a(A6); BNE.W.
    case 0x3ff5c:r.a[0]=am_index(r.a[5],0x8cb8);r.pc=0x3ff68;return true;                          // LEA -7348(A5),A0; BRA.W 3ff68.
    case 0x3ff64:r.a[0]=am_index(r.a[5],0x8da8);r.pc=0x3ff68;return true;                          // LEA -7258(A5),A0.
    // MOVE.W 2e(A0),D0; CMP.W 2e(A6),D0; BLT.W 3ff9c (signed WORDs: D0.W < WORD 2e(A6)).
    case 0x3ff68:
        if(!ofr15_get(c,r.a[0],0x2e,2,value) || !ofr15_get(c,r.a[6],0x2e,2,other))return false;am_word(r.d[0],value);
        r.pc=ofr15_signed_word(value)<ofr15_signed_word(other)?0x3ff9c:0x3ff74;return true;
    case 0x3ff74:return am_call(c,0x40b60,0x3ff78);                                                 // BSR.W 40b60.
    case 0x3ff78:return ofr15_carry(c,0x3ff9c,0x3ff7c);                                            // BCC.W 3ff9c (C of 40b60).
    // MOVE.W 8a(A6),D0; MOVE.B #13,D1; MOVE.B 97(A6),D2; MOVE.B 98(A6),D3; MOVE.W 54(A6),D4; JSR 4d508.l.
    case 0x3ff7c:
        if(!ofr15_field_word(c,0x8a,r.d[0]))return false;am_byte(r.d[1],0x13);
        if(!ofr15_get(c,r.a[6],0x97,1,value))return false;am_byte(r.d[2],value);
        if(!ofr15_get(c,r.a[6],0x98,1,value))return false;am_byte(r.d[3],value);
        if(!ofr15_field_word(c,0x54,r.d[4]))return false;return am_call(c,0x4d508,0x3ff96);
    case 0x3ff96:return ofr15_install(c,0x4002c,0x3ff9c);                                          // MOVE.L #4002c,(A6) (written only).
    case 0x3ff9c:r.pc=0x4076a;return true;                                                          // BRA.W 4076a.
    case 0x4076a:r.pc=0x40812;return true;                                                          // BRA.W 40812.
    case 0x40812:return am_call(c,0x4b54e,0x40818);                                                 // JSR 4b54e.l.
    // BTST #7,61(A6); SNE.B D0; BEQ.W 4082a / 40824.
    case 0x40818:
        if(!ofr15_bit(c,r.a[6],0x61,7,0,old))return false;am_byte(r.d[0],old?0xffU:0U);r.pc=old?0x40824:0x4082a;return true;
    case 0x40824:return ofr15_install(c,0x405e2,0x4082a);                                          // MOVE.L #405e2,(A6) (written only).
    // AND.B D0,5e(A6); BCLR #6,61(A6); TST.W 84(A6); BEQ.W 40846 / 4083c.
    case 0x4082a:
        if(!ofr15_get(c,r.a[6],0x5e,1,value) || !ofr15_put(c,r.a[6],0x5e,1,value&r.d[0]) || !ofr15_bit(c,r.a[6],0x61,6,2,old) ||
           !ofr15_get(c,r.a[6],0x84,2,value))return false;
        r.pc=(value&0xffffU)==0U?0x40846:0x4083c;return true;
    case 0x40846:return am_call(c,0x4d766,0x4084c);                                                 // JSR 4d766.l.
    case 0x4084c:return ofr15_carry(c,0x40856,0x40850);                                            // BCC.W 40856 (C of 4d766).
    case 0x40850:return ofr15_bset61(c,0x40856);                                                    // BSET #6,61(A6).
    case 0x40856:if(!ofr15_get(c,r.a[6],0x76,4,value))return false;r.pc=value==0U?0x40872:0x4085e;return true;   // TST.L 76(A6); BEQ.W 40872.
    // MOVE.B 1a(A6),14(A6); JSR 409e6(PC).
    case 0x4085e:if(!ofr15_get(c,r.a[6],0x1a,1,value) || !ofr15_put(c,r.a[6],0x14,1,value))return false;return am_call(c,0x409e6,0x40868);
    case 0x40868:return ofr15_bset61(c,0x4088e);                                                    // BSET #6,61(A6); BRA.W 4088e.
    // MOVE.B 1b(A6),14(A6); MOVE.W 84(A6),D0; ANDI.W #1,D0; BEQ.W 4088e / 40884.
    case 0x40872:
        if(!ofr15_get(c,r.a[6],0x1b,1,value) || !ofr15_put(c,r.a[6],0x14,1,value) || !ofr15_field_word(c,0x84,r.d[0]))return false;
        am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&1U)==0U?0x4088e:0x40884;return true;
    // ---- 40896 (the 28ae child of 40af6): bank anim 11a / 2000b0; MOVE.B #ff,92(A6); MOVE.W #ffff,8c(A6); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0x40896:
        if(!ofr15_bank(c) || !ofr15_put(c,r.a[6],0x92,1,0xff) || !ofr15_put(c,r.a[6],0x8c,2,0xffff))return false;r.d[0]=0;r.d[1]=0;
        return am_call(c,0x49290,0x408ba);
    case 0x408ba:return ofr15_install(c,0x408c0,0x408c0);                                          // MOVE.L #408c0,(A6) (next PC).
    case 0x408c0:return am_call(c,0x288c,0x408c6);                                                  // JSR 288c.l.
    case 0x408c6:return ofr15_carry(c,0x4095e,0x408ca);                                            // BCC.W 4095e (C of 288c).
    case 0x408ca:return am_call(c,0x491c4,0x408d0);                                                 // JSR 491c4.l.
    case 0x408d0:if(!ofr15_get(c,r.a[0],0x92,1,value))return false;r.pc=(value&0x80U)!=0U?0x408d8:0x408da;return true;   // TST.B 92(A0); BPL.W 408da.
    // CLR.B 9b(A6); BTST #7,15(A6); BEQ.W 40978 / 40972: JMP 4bfb4.l.
    case 0x40964:if(!ofr15_put(c,r.a[6],0x9b,1,0))return false;return ofr15_btst(c,0x15,7,0x40978,0x40972);
    case 0x40972:r.pc=0x4bfb4;return true;
    // MOVEA.L 76(A6),A0; MOVE.W (A0)+,D1; BPL.W 40a0e / 409f0.
    case 0x409e6:
        if(!ofr15_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);r.a[0]+=2U;
        r.pc=(value&0x8000U)!=0U?0x409f0:0x40a0e;return true;
    case 0x409f0:am_word(r.d[1],0U-r.d[1]);r.pc=(r.d[1]&0xffffU)>=4U?0x40a0a:0x409fa;return true;  // NEG.W D1; CMPI.W #4,D1; BCC.W 40a0a.
    // MOVE.B 19(A6,D1.W),14(A6); MOVE.L A0,76(A6); RTS.
    case 0x409fa:
        if(!am_read(c,am_index(r.a[6]+0x19U,r.d[1]),1,value) || !ofr15_put(c,r.a[6],0x14,1,value) || !ofr15_put(c,r.a[6],0x76,4,r.a[0]))return false;
        return am_return(c);
    case 0x40a0a:   // ADDA.W (A0),A0; MOVE.W (A0)+,D1 (falls to 40a0e).
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]=am_index(r.a[0],value);if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);
        r.a[0]+=2U;r.pc=0x40a0e;return true;
    // MOVE.L A0,76(A6); MOVE.B 14(A6),D0; JMP 8d34.l.
    case 0x40a0e:
        if(!ofr15_put(c,r.a[6],0x76,4,r.a[0]) || !ofr15_get(c,r.a[6],0x14,1,value))return false;am_byte(r.d[0],value);r.pc=0x8d34;return true;
    case 0x40a1c:if(!ofr15_field_word(c,0x1e,r.d[0]))return false;return am_call(c,0xce02,0x40a26);  // MOVE.W 1e(A6),D0; JSR ce02.l.
    case 0x40a26:return am_call(c,0x49fc6,0x40a2c);                                                 // JSR 49fc6.l.
    // ---- 40a5a (C11 3fee2 BSR.W): bank anim 11a / 2000b0; the sounds dad / dac / da6 (8ebe, D1.B 1).
    case 0x40a5a:if(!ofr15_bank(c))return false;return ofr15_sound(c,0xdad,0x40a76);
    case 0x40a76:return ofr15_sound(c,0xdac,0x40a84);
    case 0x40a84:return ofr15_sound(c,0xda6,0x40a92);
    // MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); MOVEQ #13,D1; JSR 4d81c.l.
    case 0x40a92:
        if(!ofr15_put(c,r.a[6],0x68,2,0x8810) || !ofr15_put(c,r.a[6],0x1e,2,0x8810))return false;r.d[1]=0x13;return am_call(c,0x4d81c,0x40aa6);
    // MOVE.B D1,97(A6); MOVE.B D2,98(A6); MOVE.W D3,54(A6); JSR 496c2.l.
    case 0x40aa6:
        if(!ofr15_put(c,r.a[6],0x97,1,r.d[1]) || !ofr15_put(c,r.a[6],0x98,1,r.d[2]) || !ofr15_put(c,r.a[6],0x54,2,r.d[3]))return false;
        return am_call(c,0x496c2,0x40ab8);
    case 0x40ab8:r.a[0]=0x41fe6;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x40ac8);           // MOVEA.L #41fe6,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x40ac8:return ofr15_carry(c,0x40af6,0x40acc);                                            // BCC.W 40af6 (C of 28ae).
    // LEA 86(A6),A1; MOVE.L A1,76(A0); MOVE.B #14,7a(A0); MOVE.B #0,7b(A0) .. 7e(A0); ORI.B #1,CCR (no reader).
    case 0x40acc:
        r.a[1]=r.a[6]+0x86U;
        if(!ofr15_put(c,r.a[0],0x76,4,r.a[1]) || !ofr15_put(c,r.a[0],0x7a,1,0x14) || !ofr15_put(c,r.a[0],0x7b,1,0) || !ofr15_put(c,r.a[0],0x7c,1,0) ||
           !ofr15_put(c,r.a[0],0x7d,1,0) || !ofr15_put(c,r.a[0],0x7e,1,0))return false;
        r.carry=AnimationCarrySet;r.pc=0x40af6;return true;
    case 0x40af6:r.a[0]=0x40896;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x40b06);           // MOVEA.L #40896,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x40b06:return ofr15_carry(c,0x40890,0x40b0a);                                            // BCC.W 40890 (C of 28ae).
    case 0x40b0a:if(!ofr15_put(c,r.a[6],0x92,1,0xff))return false;return am_return(c);            // MOVE.B #ff,92(A6); RTS.
    // ---- 40b60: MOVE.W 8a(A6),D0; MOVEQ #0,D2; MOVEQ #8,D3; JSR 4d418.l.
    case 0x40b60:if(!ofr15_field_word(c,0x8a,r.d[0]))return false;r.d[2]=0;r.d[3]=8;return am_call(c,0x4d418,0x40b6e);
    case 0x40b6e:return ofr15_carry(c,0x40b7a,0x40b72);                                            // BCC.W 40b7a (C of 4d418, kept into 40b7a).
    // MOVE.W D0,8c(A6); ORI.B #1,CCR (C Set into the pass block 40b7a).
    case 0x40b72:if(!ofr15_put(c,r.a[6],0x8c,2,r.d[0]))return false;r.carry=AnimationCarrySet;r.pc=0x40b7a;return true;
    // ---- 40bc8 (script callback, interpreter table 4a500 + bc): MOVE.W (A0),86(A6); RTS.
    case 0x40bc8:if(!am_read(c,r.a[0],2,value) || !ofr15_put(c,r.a[6],0x86,2,value))return false;return am_return(c);
    // ---- 4c2c4: JSR 4bce0(PC); 4c2c8: BRA.W 4c2d0.
    case 0x4c2c4:return am_call(c,0x4bce0,0x4c2c8);
    case 0x4c2c8:r.pc=0x4c2d0;return true;
    // ---- 4fdfc (the circle of radius D2.W around the fix cell D0.W / D1.W, cell code D3.W): MOVEQ #0,D4; MOVE.W D2,D5; MOVE.W D2,D6; LSR.W #2,D6.
    case 0x4fdfc:r.d[4]=0;am_word(r.d[5],r.d[2]);am_word(r.d[6],(r.d[2]&0xffffU)>>2);r.pc=0x4fe04;return true;
    case 0x4fe04:r.pc=(r.d[5]&0xffffU)<(r.d[4]&0xffffU)?0x4fe4e:0x4fe0a;return true;              // CMP.W D4,D5; BCS.W 4fe4e (unsigned).
    case 0x4fe0a:return am_call(c,0x4fe50,0x4fe0e);                                                 // BSR.W 4fe50.
    case 0x4fe0e:return ofr15_octant(c,r.d[4],0x4fe14);                                            // NEG.W D4; BSR.W 4fe50.
    case 0x4fe14:return ofr15_octant(c,r.d[5],0x4fe1a);                                            // NEG.W D5; BSR.W 4fe50.
    case 0x4fe1a:return ofr15_octant(c,r.d[4],0x4fe20);                                            // NEG.W D4; BSR.W 4fe50.
    case 0x4fe20:ofr15_exg45(r);return am_call(c,0x4fe50,0x4fe26);                                 // EXG.L D4,D5; BSR.W 4fe50.
    case 0x4fe26:return ofr15_octant(c,r.d[5],0x4fe2c);                                            // NEG.W D5; BSR.W 4fe50.
    case 0x4fe2c:return ofr15_octant(c,r.d[4],0x4fe32);                                            // NEG.W D4; BSR.W 4fe50.
    case 0x4fe32:return ofr15_octant(c,r.d[5],0x4fe38);                                            // NEG.W D5; BSR.W 4fe50.
    case 0x4fe38:ofr15_exg45(r);r.pc=(r.d[6]&0x8000U)!=0U?0x4fe48:0x4fe40;return true;           // EXG.L D4,D5; TST.W D6; BMI.W 4fe48.
    case 0x4fe40:am_word(r.d[4],r.d[4]+1U);am_word(r.d[6],r.d[6]-r.d[4]);r.pc=0x4fe4c;return true; // ADDQ.W #1,D4; SUB.W D4,D6; BRA.W 4fe4c.
    case 0x4fe48:am_word(r.d[5],r.d[5]-1U);am_word(r.d[6],r.d[6]+r.d[5]);r.pc=0x4fe4c;return true; // SUBQ.W #1,D5; ADD.W D5,D6.
    case 0x4fe4c:r.pc=0x4fe04;return true;                                                          // BRA.B 4fe04.
    // SWAP D3; MOVE.W D0,D7; ADD.W D4,D7; SUBQ.W #1,D7; CMPI.W #26,D7; BCC.W 4fe86 (unsigned: the column outside 0..25).
    case 0x4fe50:am_swap(r.d[3]);am_word(r.d[7],r.d[0]);am_word(r.d[7],r.d[7]+r.d[4]);am_word(r.d[7],r.d[7]-1U);
        r.pc=(r.d[7]&0xffffU)>=0x26U?0x4fe86:0x4fe60;return true;
    // ADDQ.W #1,D7; LSL.W #5,D7; MOVE.W D7,D3; MOVE.W D1,D7; ADD.W D5,D7; SUBQ.W #1,D7; CMPI.W #1e,D7; BCC.W 4fe86 (the row outside 0..1d).
    case 0x4fe60:am_word(r.d[7],r.d[7]+1U);am_word(r.d[7],(r.d[7]&0xffffU)<<5);am_word(r.d[3],r.d[7]);am_word(r.d[7],r.d[1]);am_word(r.d[7],r.d[7]+r.d[5]);
        am_word(r.d[7],r.d[7]-1U);r.pc=(r.d[7]&0xffffU)>=0x1eU?0x4fe86:0x4fe74;return true;
    // ADDQ.W #1,D7; ADD.W D7,D3; ADDI.W #7000,D3; SWAP D3; MOVE.L D3,3c0000.l; RTS.
    case 0x4fe74:am_word(r.d[7],r.d[7]+1U);am_word(r.d[3],r.d[3]+r.d[7]);am_word(r.d[3],r.d[3]+0x7000U);am_swap(r.d[3]);ofr15_port(c,r.d[3]);
        return am_return(c);
    case 0x4fe86:am_swap(r.d[3]);return am_return(c);                                               // SWAP D3; RTS.
    // ---- 4fea4 (13 circles, cell codes from the ROM WORD table 4fe8a): LEA 4fe8a(PC),A0; MOVE.W #d,D4; SUB.W D4,D2.
    case 0x4fea4:r.a[0]=0x4fe8a;am_word(r.d[4],0xd);am_word(r.d[2],r.d[2]-r.d[4]);r.pc=0x4feae;return true;
    // MOVE.W D4,-(A7); ADDQ.W #1,D2; BMI.W 4febc / 4feb6.
    case 0x4feae:if(!am_push(c,2,r.d[4]&0xffffU))return false;am_word(r.d[2],r.d[2]+1U);r.pc=(r.d[2]&0x8000U)!=0U?0x4febc:0x4feb6;return true;
    case 0x4feb6:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[3],value);return am_call(c,0x4fdfc,0x4febc);   // MOVE.W (A0),D3; BSR.W 4fdfc.
    // ADDQ.W #2,A0; MOVE.W (A7)+,D4; SUBQ.W #1,D4; BNE.B 4feae / 4fec4.
    case 0x4febc:r.a[0]+=2U;if(!am_pop(c,2,value))return false;am_word(r.d[4],value-1U);r.pc=(r.d[4]&0xffffU)!=0U?0x4feae:0x4fec4;return true;
    // ---- 4fec6: WORD 76 := WORD 76 ASR 3; WORD 78 := (1ff - WORD 78) ASR 3; D0.W - 14 / D1.W - 10 (BPL / NEG: absolute values).
    case 0x4fec6:
        if(!ofr15_field_word(c,0x76,r.d[0]))return false;am_word(r.d[0],ofr15_asr_word(r.d[0],3));if(!ofr15_put(c,r.a[6],0x76,2,r.d[0]))return false;
        if(!ofr15_field_word(c,0x78,r.d[1]))return false;am_word(r.d[1],r.d[1]-0x1ffU);am_word(r.d[1],0U-r.d[1]);am_word(r.d[1],ofr15_asr_word(r.d[1],3));
        if(!ofr15_put(c,r.a[6],0x78,2,r.d[1]))return false;am_word(r.d[0],r.d[0]-0x14U);r.pc=(r.d[0]&0x8000U)!=0U?0x4fee8:0x4feea;return true;
    case 0x4fee8:am_word(r.d[0],0U-r.d[0]);r.pc=0x4feea;return true;                              // NEG.W D0.
    // ADDI.W #14,D0; SUBI.W #10,D1; BPL.W 4fef8 / 4fef6.
    case 0x4feea:am_word(r.d[0],r.d[0]+0x14U);am_word(r.d[1],r.d[1]-0x10U);r.pc=(r.d[1]&0x8000U)!=0U?0x4fef6:0x4fef8;return true;
    case 0x4fef6:am_word(r.d[1],0U-r.d[1]);r.pc=0x4fef8;return true;                              // NEG.W D1.
    // ADDI.W #10,D1; CMP.W D0,D1; BCC.W 4ff04 (unsigned D1.W >= D0.W) / 4ff02.
    case 0x4fef8:am_word(r.d[1],r.d[1]+0x10U);r.pc=(r.d[1]&0xffffU)>=(r.d[0]&0xffffU)?0x4ff04:0x4ff02;return true;
    case 0x4ff02:value=r.d[0];r.d[0]=r.d[1];r.d[1]=value;r.pc=0x4ff04;return true;                // EXG.L D0,D1.
    // LSR.W #1,D0; ADD.W D1,D0; ADDI.W #d,D0; MOVE.B D0,7c(A6); RTS.
    case 0x4ff04:am_word(r.d[0],(r.d[0]&0xffffU)>>1);am_word(r.d[0],r.d[0]+r.d[1]);am_word(r.d[0],r.d[0]+0xdU);
        if(!ofr15_put(c,r.a[6],0x7c,1,r.d[0]))return false;return am_return(c);
    // ---- 4ff4c (the 28ae child of stage catalog 47964): BSR.W 4fec6; MOVE.B 7c(A6),7a(A6); MOVE.L #4ff5c,(A6) (next PC).
    case 0x4ff4c:return am_call(c,0x4fec6,0x4ff50);
    case 0x4ff50:if(!ofr15_get(c,r.a[6],0x7c,1,value) || !ofr15_put(c,r.a[6],0x7a,1,value))return false;return ofr15_install(c,0x4ff5c,0x4ff5c);
    case 0x4ff5c:if(!ofr15_get(c,r.a[6],0x7a,2,value))return false;r.pc=(value&0xffffU)!=0U?0x4ff74:0x4ff64;return true;   // TST.W 7a(A6); BNE.W.
    // MOVEA.L c(A6),A0; MOVE.B #ff,62(A0); JMP 2a00.l.
    case 0x4ff64:if(!ofr15_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr15_put(c,r.a[0],0x62,1,0xff))return false;r.pc=0x2a00;return true;
    // SUBI.W #200,7a(A6); BCC.W 4ff84 (no borrow) / 4ff7e: MOVE.W #0,7a(A6).
    case 0x4ff74:
        if(!ofr15_get(c,r.a[6],0x7a,2,value) || !ofr15_put(c,r.a[6],0x7a,2,value-0x200U))return false;r.pc=(value&0xffffU)<0x200U?0x4ff7e:0x4ff84;return true;
    case 0x4ff7e:if(!ofr15_put(c,r.a[6],0x7a,2,0))return false;r.pc=0x4ff84;return true;
    // MOVE.W 76(A6),D0; MOVE.W 78(A6),D1; MOVEQ #0,D2; MOVE.B 7a(A6),D2; BRA.W 4fea4.
    case 0x4ff84:
        if(!ofr15_field_word(c,0x76,r.d[0]) || !ofr15_field_word(c,0x78,r.d[1]) || !ofr15_get(c,r.a[6],0x7a,1,value))return false;r.d[2]=value&0xffU;
        r.pc=0x4fea4;return true;
    // ---- 6f282 (script callback, table 4a500 + 20): MOVE.W (A0)+,D0; D0.W := 6 x D0.W (ADD.W x 3); ADD.B 7c(A6),D0; MOVE.B D0,7f(A6); RTS.
    case 0x6f282:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[0],value);am_word(r.d[1],r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        am_word(r.d[0],r.d[0]+r.d[1]);am_word(r.d[0],r.d[0]+r.d[0]);if(!ofr15_get(c,r.a[6],0x7c,1,value))return false;am_byte(r.d[0],r.d[0]+value);
        if(!ofr15_put(c,r.a[6],0x7f,1,r.d[0]))return false;return am_return(c);
    // ---- 6f352 (script callback, table 4a500 + 38): JSR 49a58.l; 6f358: CMP.W (A0)+,D0; BCS.W 6f360 (unsigned D0.W < WORD) / RTS.
    case 0x6f352:return am_call(c,0x49a58,0x6f358);
    case 0x6f358:if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;r.pc=(r.d[0]&0xffffU)<(value&0xffffU)?0x6f360:0x6f35e;return true;
    // ---- b3dfc (the 2986 child written by C11 e8c66): MOVE.W #1,7c(A6); JSR 1aa3a.l.
    case 0xb3dfc:if(!ofr15_put(c,r.a[6],0x7c,2,1))return false;return am_call(c,0x1aa3a,0xb3e08);
    // LEA b42a2(PC),A0; ANDI.B #c0,D0; BEQ.W b3e18 / b3e14: LEA b403e(PC),A0; b3e18: BRA.W b3ea2.
    case 0xb3e08:r.a[0]=0xb42a2;am_byte(r.d[0],r.d[0]&0xc0U);r.pc=(r.d[0]&0xc0U)==0U?0xb3e18:0xb3e14;return true;
    case 0xb3e14:r.a[0]=0xb403e;r.pc=0xb3e18;return true;
    case 0xb3e18:r.pc=0xb3ea2;return true;
    // ---- c13c0 (the FR1 kind-record handler, record b35ce): MOVE.W #1fb,20(A6); MOVEA.L #c1ec0,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xc13c0:if(!ofr15_put(c,r.a[6],0x20,2,0x1fb))return false;r.a[1]=0xc1ec0;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xc13d6);
    case 0xc13d6:am_word(r.d[0],0x72);am_word(r.d[1],3);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xc13e8);   // MOVE.W #72,D0; MOVE.W #3,D1; MOVE.B #0,D2.
    case 0xc13e8:return am_call(c,0xb4304,0xc13ee);                                                 // JSR b4304.l.
    case 0xc13ee:return ofr15_carry(c,0xc1d06,0xc13f2);                                            // BCC.W c1d06 (C of b4304).
    case 0xc13f2:return am_call(c,0x49a58,0xc13f8);                                                 // JSR 49a58.l.
    // MOVE.W D0,b2(A6); ROR.W #8,D0; SMI.B D1; ANDI.W #3ff,D0; ADDI.W #800,D0; EXT.W D1; EOR.W D1,D0; SUB.W D1,D0; MOVE.W D0,b4(A6);
    // MOVE.L #c141e,a2(A6); JSR c1cf2(PC) (FR12 c106e).
    case 0xc13f8:
        if(!ofr15_put(c,r.a[6],0xb2,2,r.d[0]))return false;value=r.d[0]&0xffffU;am_word(r.d[0],((value<<8)|(value>>8))&0xffffU);
        am_byte(r.d[1],(r.d[0]&0x8000U)!=0U?0xffU:0U);am_word(r.d[0],r.d[0]&0x3ffU);am_word(r.d[0],r.d[0]+0x800U);
        am_word(r.d[1],(r.d[1]&0x80U)!=0U?0xffffU:0U);am_word(r.d[0],r.d[0]^r.d[1]);am_word(r.d[0],r.d[0]-r.d[1]);
        if(!ofr15_put(c,r.a[6],0xb4,2,r.d[0]) || !ofr15_put(c,r.a[6],0xa2,4,0xc141e))return false;return am_call(c,0xc1cf2,0xc141e);
    // MOVE.W #7,b0(A6); MOVE.L #c142a,(A6) (next PC).
    case 0xc141e:if(!ofr15_put(c,r.a[6],0xb0,2,7))return false;return ofr15_install(c,0xc142a,0xc142a);
    case 0xc142a:return am_call(c,0xb4030,0xc1430);                                                 // JSR b4030.l.
    case 0xc1430:return ofr15_btst(c,0x15,7,0xc1450,0xc143a);                                       // BTST.B #7,15(A6); BEQ.W c1450.
    // MOVE.W b4(A6),D0; ASR.W #3,D0; EXT.L D0; LSL.L #8,D0; ASR.L #1,D0; ADD.L D0,36(A6); ASR.L #5,D0; SUB.W D0,b4(A6) (FR12 c10b0).
    case 0xc143a:
        if(!ofr15_field_word(c,0xb4,r.d[0]))return false;am_word(r.d[0],ofr15_asr_word(r.d[0],3));r.d[0]=am_extend_word(r.d[0])<<8;
        r.d[0]=ofr15_asr(r.d[0],1);if(!ofr15_get(c,r.a[6],0x36,4,value) || !ofr15_put(c,r.a[6],0x36,4,value+r.d[0]))return false;
        r.d[0]=ofr15_asr(r.d[0],5);if(!ofr15_add_word(c,0xb4,r.d[0],true))return false;r.pc=0xc1450;return true;
    case 0xc1450:return ofr15_btst(c,0x15,7,0xc1462,0xc145a);                                       // BTST.B #7,15(A6); BEQ.W c1462.
    // LSR.W b0(A6) (the WORD shifted right by one); BEQ.W c14c2 (the new WORD zero) / c1462.
    case 0xc145a:
        if(!ofr15_get(c,r.a[6],0xb0,2,value) || !ofr15_put(c,r.a[6],0xb0,2,(value&0xffffU)>>1))return false;
        r.pc=((value&0xffffU)>>1)==0U?0xc14c2:0xc1462;return true;
    case 0xc1462:return ofr15_btst(c,0x15,7,0xc147c,0xc146c);                                       // BTST.B #7,15(A6); BEQ.W c147c.
    case 0xc146c:return ofr15_steer(c,0x36,0xc147c);
    case 0xc147c:return ofr15_angle(c,0xc149c,0xc1492);
    case 0xc1492:ofr15_mirror(r,0xc149c);return true;
    case 0xc149c:if(!ofr15_sector(c))return false;return am_call(c,0xb4958,0xc14ac);                // MULU.W #8,D0; SWAP D0; MOVE.B D0,b6(A6); JSR b4958.l.
    case 0xc14ac:return am_call(c,0xb4ab0,0xc14b2);                                                 // JSR b4ab0.l.
    case 0xc14b2:ofr15_bit2(r,0xc14ba);return true;                                                 // BTST #2,D0; BNE.W c1d2e.
    case 0xc14ba:return am_call(c,0xb4334,0xc14c0);                                                 // JSR b4334.l.
    // MOVE.L 36(A6),64(A6); LEA c0924(PC),A0; JSR b402a.l.
    case 0xc14c2:if(!ofr15_get(c,r.a[6],0x36,4,value) || !ofr15_put(c,r.a[6],0x64,4,value))return false;r.a[0]=0xc0924;return am_call(c,0xb402a,0xc14d2);
    case 0xc14d2:return ofr15_install(c,0xc14d8,0xc14d8);                                          // MOVE.L #c14d8,(A6) (next PC).
    case 0xc14d8:return am_call(c,0xb4030,0xc14de);                                                 // JSR b4030.l.
    case 0xc14de:return ofr15_btst(c,0x15,7,0xc141e,0xc14e8);                                       // BTST.B #7,15(A6); BEQ.W c141e.
    case 0xc14e8:return ofr15_btst(c,0x15,7,0xc1502,0xc14f2);                                       // BTST.B #7,15(A6); BEQ.W c1502.
    case 0xc14f2:return ofr15_steer(c,0x64,0xc1502);
    case 0xc1502:return ofr15_angle(c,0xc1522,0xc1518);
    case 0xc1518:ofr15_mirror(r,0xc1522);return true;
    // MULU.W #8,D0; SWAP D0; MOVE.B D0,b6(A6); CMPI.B #0,b6(A6); BEQ.W c1540 (the bundled BEQ.W c0944, Z still set) / c1536.
    case 0xc1522:if(!ofr15_sector(c))return false;return ofr15_sector_is(c,0,0xc1536);
    // CMPI.B #1,b6(A6); BEQ.W c1540 (-> c0944); BEQ.W c0944 not taken -> c1544.
    case 0xc1536:return ofr15_sector_is(c,1,0xc1544);
    case 0xc1544:return am_call(c,0xb4958,0xc154a);                                                 // JSR b4958.l.
    case 0xc154a:return am_call(c,0xb4ab0,0xc1550);                                                 // JSR b4ab0.l.
    case 0xc1550:ofr15_bit2(r,0xc1558);return true;                                                 // BTST #2,D0; BNE.W c1d2e.
    case 0xc1558:return am_call(c,0xb4334,0xc155e);                                                 // JSR b4334.l.
    // ---- e9b8a (the 2986 child written by FR2 e9b5c): MOVE.W #3,D0; BRA.W e9b9a.
    case 0xe9b8a:am_word(r.d[0],3);r.pc=0xe9b9a;return true;
    // MOVE.B D0,90(A6); MOVE.W #ffff,68(A6); MOVE.W #ffff,1e(A6); JSR ea2c6(PC).
    case 0xe9b9a:
        if(!ofr15_put(c,r.a[6],0x90,1,r.d[0]) || !ofr15_put(c,r.a[6],0x68,2,0xffff) || !ofr15_put(c,r.a[6],0x1e,2,0xffff))return false;
        return am_call(c,0xea2c6,0xe9bae);
    // ADD.W D0,D0 (x 2); LEA ea3c4.l,A0; MOVE.L (A0,D0.W),7e(A6); MOVE.W 88(A6),D0; ADD.W D0,D0 (x 2); LEA ea3ac.l,A0; MOVEA.L (A0,D0.W),A0;
    // MOVE.W (A0)+,D0; MOVE.W (A0),-(A7); MOVEQ #0,D1; JSR 8ebe.l.
    case 0xe9bae:
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);r.a[0]=0xea3c4;
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value) || !ofr15_put(c,r.a[6],0x7e,4,value) || !ofr15_field_word(c,0x88,r.d[0]))return false;
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);r.a[0]=0xea3ac;
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.a[0]+=2U;
        if(!am_read(c,r.a[0],2,value) || !am_push(c,2,value&0xffffU))return false;r.d[1]=0;return am_call(c,0x8ebe,0xe9bdc);
    case 0xe9bdc:if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.d[1]=0;return am_call(c,0x8ebe,0xe9be6);   // MOVE.W (A7)+,D0; MOVEQ #0,D1.
    // MOVEQ #0,D0; MOVEQ #0,D7; LEA 76(A6),A0; MOVEA.L 7e(A6),A1.
    case 0xe9be6:r.d[0]=0;r.d[7]=0;r.a[0]=r.a[6]+0x76U;if(!ofr15_get(c,r.a[6],0x7e,4,value))return false;r.a[1]=value;r.pc=0xe9bf2;return true;
    // CMP.B 8f(A6),D0; BCC.W e9c0a (unsigned D0.B >= BYTE 8f) / e9bfa.
    case 0xe9bf2:if(!ofr15_get(c,r.a[6],0x8f,1,value))return false;r.pc=(r.d[0]&0xffU)>=(value&0xffU)?0xe9c0a:0xe9bfa;return true;
    // MOVEQ #0,D2; MOVE.B (A0,D0.W),D2; ADD.W D2,D2; ADD.W 4(A1,D2.W),D7; ADDQ.W #1,D0; BRA.B e9bf2.
    case 0xe9bfa:
        if(!am_read(c,am_index(r.a[0],r.d[0]),1,value))return false;r.d[2]=value&0xffU;am_word(r.d[2],r.d[2]+r.d[2]);
        if(!am_read(c,am_index(r.a[1]+4U,r.d[2]),2,value))return false;am_word(r.d[7],r.d[7]+value);am_word(r.d[0],r.d[0]+1U);r.pc=0xe9bf2;return true;
    // MOVE.W 42(A6),D0; SUB.W D7,D0; SUBQ.W #8,D0; BPL.W e9c1c / e9c16.
    case 0xe9c0a:if(!ofr15_field_word(c,0x42,r.d[0]))return false;am_word(r.d[0],r.d[0]-r.d[7]-8U);r.pc=(r.d[0]&0x8000U)!=0U?0xe9c16:0xe9c1c;return true;
    case 0xe9c16:return ofr15_half_sub(c,0x2e,0xe9c1c);                                            // ASR.W #1,D0; SUB.W D0,2e(A6).
    // MOVE.W 42(A6),D0; ADD.W D7,D0; SUBI.W #138,D0; BMI.W e9c30 / e9c2a.
    case 0xe9c1c:if(!ofr15_field_word(c,0x42,r.d[0]))return false;am_word(r.d[0],r.d[0]+r.d[7]-0x138U);r.pc=(r.d[0]&0x8000U)!=0U?0xe9c30:0xe9c2a;return true;
    case 0xe9c2a:return ofr15_half_sub(c,0x2e,0xe9c30);
    // SUB.W D7,2e(A6); MOVE.W 46(A6),D0; SUBI.W #108,D0; BPL.W e9c46 / e9c40.
    case 0xe9c30:
        if(!ofr15_add_word(c,0x2e,r.d[7],true) || !ofr15_field_word(c,0x46,r.d[0]))return false;am_word(r.d[0],r.d[0]-0x108U);
        r.pc=(r.d[0]&0x8000U)!=0U?0xe9c40:0xe9c46;return true;
    case 0xe9c40:return ofr15_half_sub(c,0x32,0xe9c46);
    // MOVE.W 46(A6),D0; SUBI.W #1e0,D0; BMI.W e9c58 / e9c52.
    case 0xe9c46:if(!ofr15_field_word(c,0x46,r.d[0]))return false;am_word(r.d[0],r.d[0]-0x1e0U);r.pc=(r.d[0]&0x8000U)!=0U?0xe9c58:0xe9c52;return true;
    case 0xe9c52:return ofr15_half_sub(c,0x32,0xe9c58);
    case 0xe9c58:return am_call(c,0x43e34,0xe9c5e);                                                 // JSR 43e34.l.
    case 0xe9c5e:return am_call(c,0x496c2,0xe9c64);                                                 // JSR 496c2.l.
    // MOVEQ #0,D0; MOVE.B 90(A6),D0; ADD.W D0,D0 (x 2); JMP e9c72(PC,D0.W): only the executed entry 3 (e9c7e: BRA.W ea132, BYTE 90 = 3 written by
    // e9b8a) is transcribed; any other index is a checked jump-target error.
    case 0xe9c64:
        if(!ofr15_get(c,r.a[6],0x90,1,value))return false;r.d[0]=value&0xffU;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        if(am_index(0xe9c72,r.d[0])!=0xe9c7eU)return am_error(c,"unsupported animation objects fr15 jump target");r.pc=0xe9c7e;return true;
    case 0xe9c7e:r.pc=0xea132;return true;                                                          // BRA.W ea132.
    case 0xea132:if(!ofr15_put(c,r.a[6],0xa4,2,2))return false;r.pc=0xea13c;return true;         // MOVE.W #2,a4(A6); BRA.W ea13c.
    // ST.B 92(A6); MOVE.W a4(A6),8c(A6); MOVE.L #ea14c,(A6) (next PC).
    case 0xea13c:
        if(!ofr15_put(c,r.a[6],0x92,1,0xff) || !ofr15_get(c,r.a[6],0xa4,2,value) || !ofr15_put(c,r.a[6],0x8c,2,value))return false;
        return ofr15_install(c,0xea14c,0xea14c);
    case 0xea14c:return am_call(c,0xea2ca,0xea150);                                                 // JSR ea2ca(PC).
    case 0xea150:return ofr15_carry(c,0xea154,0xea2c0);                                            // BCS.W ea2c0 (C of ea2ca).
    case 0xea154:return am_call(c,0xea2e0,0xea158);                                                 // JSR ea2e0(PC).
    // CLR.B 93(A6); MOVE.W 8c(A6),-(A7); MOVEQ #0,D1.
    case 0xea158:
        if(!ofr15_put(c,r.a[6],0x93,1,0) || !ofr15_get(c,r.a[6],0x8c,2,value) || !am_push(c,2,value&0xffffU))return false;r.d[1]=0;r.pc=0xea162;return true;
    case 0xea162:return am_call(c,0xea2fe,0xea166);                                                 // JSR ea2fe(PC).
    // MOVE.W (A7),D6; SUB.W a4(A6),D6; MOVE.W D6,(A7); BMI.W ea1b0 / ea172.
    case 0xea166:
        if(!am_read(c,r.a[7],2,value) || !ofr15_get(c,r.a[6],0xa4,2,other))return false;am_word(r.d[6],value-other);
        if(!am_write(c,r.a[7],2,r.d[6]&0xffffU))return false;r.pc=(r.d[6]&0x8000U)!=0U?0xea1b0:0xea172;return true;
    // LEA 94(A6),A0; ADDA.W D1,A0 (x 2); CMPI.W #14,D6; BCC.W ea192 (unsigned D6.W >= 14) / ea182.
    case 0xea172:r.a[0]=am_index(am_index(r.a[6]+0x94U,r.d[1]),r.d[1]);r.pc=(r.d[6]&0xffffU)>=0x14U?0xea192:0xea182;return true;
    // LEA ea37c.l,A1; ADD.W D6,D6; MOVE.W (A1,D6.W),(A0); BSET D1,93(A6) (bit D1 mod 8).
    case 0xea182:
        r.a[1]=0xea37c;am_word(r.d[6],r.d[6]+r.d[6]);if(!am_read(c,am_index(r.a[1],r.d[6]),2,value) || !am_write(c,r.a[0],2,value&0xffffU) ||
           !ofr15_bit(c,r.a[6],0x93,r.d[1],1,old))return false;
        r.pc=0xea192;return true;
    // MOVE.W (A0),84(A6); BTST D1,92(A6) (bit D1 mod 8); BEQ.W ea1b0 / ea19e.
    case 0xea192:
        if(!am_read(c,r.a[0],2,value) || !ofr15_put(c,r.a[6],0x84,2,value) || !ofr15_bit(c,r.a[6],0x92,r.d[1],0,old))return false;
        r.pc=old?0xea19e:0xea1b0;return true;
    // MOVE.W 82(A6),D0; ADD.W 86(A6),D0; SWAP D0; MOVE.W 84(A6),D0; JSR ea314(PC).
    case 0xea19e:
        if(!ofr15_field_word(c,0x82,r.d[0]) || !ofr15_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],r.d[0]+value);am_swap(r.d[0]);
        if(!ofr15_field_word(c,0x84,r.d[0]))return false;return am_call(c,0xea314,0xea1b0);
    case 0xea1b0:return am_call(c,0xea334,0xea1b4);                                                 // JSR ea334(PC).
    // ADDQ.W #1,D1; CMP.B 8f(A6),D1; BCS.B ea162 (unsigned D1.B < BYTE 8f) / ea1bc.
    case 0xea1b4:am_word(r.d[1],r.d[1]+1U);if(!ofr15_get(c,r.a[6],0x8f,1,value))return false;r.pc=(r.d[1]&0xffU)<(value&0xffU)?0xea162:0xea1bc;return true;
    case 0xea1bc:if(!am_pop(c,2,value))return false;am_word(r.d[6],value);r.pc=(value&0x8000U)!=0U?0xea1d0:0xea1c2;return true;   // MOVE.W (A7)+,D6; BMI.W.
    case 0xea1c2:if(!ofr15_get(c,r.a[6],0x93,1,value))return false;r.pc=(value&0xffU)!=0U?0xea1d0:0xea1ca;return true;   // TST.B 93(A6); BNE.W ea1d0.
    case 0xea1d0:if(!ofr15_add_word(c,0x8c,1,false))return false;r.pc=0xea2be;return true;      // ADDQ.W #1,8c(A6); BRA.W ea2be.
    case 0xea2c6:r.d[0]=0;return am_return(c);                                                      // MOVEQ #0,D0; RTS.
    // MOVE.W 8a(A6),D0; ADDQ.W #4,D0; MOVE.W 88(A6),D1; ADD.W D1,D1; LEA 5e4a(A5),A0; CMP.W (A0,D1.W),D0; RTS (C: unsigned D0.W < the WORD).
    case 0xea2ca:
        if(!ofr15_field_word(c,0x8a,r.d[0]))return false;am_word(r.d[0],r.d[0]+4U);if(!ofr15_field_word(c,0x88,r.d[1]))return false;
        am_word(r.d[1],r.d[1]+r.d[1]);r.a[0]=r.a[5]+0x5e4aU;if(!am_read(c,am_index(r.a[0],r.d[1]),2,value))return false;
        r.carry=(r.d[0]&0xffffU)<(value&0xffffU)?AnimationCarrySet:AnimationCarryClear;return am_return(c);
    case 0xea2e0:return am_call(c,0x43e34,0xea2e6);                                                 // JSR 43e34.l.
    // ADDQ.B #1,8e(A6); MOVE.B 8e(A6),D0; ANDI.W #1,D0; MOVE.B 19(A6,D0.W),14(A6); CLR.W 86(A6); RTS.
    case 0xea2e6:
        if(!ofr15_get(c,r.a[6],0x8e,1,value) || !ofr15_put(c,r.a[6],0x8e,1,value+1U))return false;am_byte(r.d[0],value+1U);am_word(r.d[0],r.d[0]&1U);
        if(!am_read(c,am_index(r.a[6]+0x19U,r.d[0]),1,value) || !ofr15_put(c,r.a[6],0x14,1,value) || !ofr15_put(c,r.a[6],0x86,2,0))return false;
        return am_return(c);
    case 0xea2fe:case 0xea334:return ofr15_width(c);
    // MOVEQ #0,D2; MOVE.B 76(A6,D1.W),D2; ADD.W D2,D2; MOVEA.L 7e(A6),A0; MOVE.L (A0,D2.W),D7; BEQ.W ea332 / ea328.
    case 0xea314:if(!ofr15_record(c) || !am_read(c,am_index(r.a[0],r.d[2]),4,value))return false;r.d[7]=value;r.pc=value==0U?0xea332:0xea328;return true;
    case 0xea328:if(!am_push(c,2,r.d[1]&0xffffU))return false;return am_call(c,0x16ea4,0xea330);   // MOVE.W D1,-(A7); JSR 16ea4.l.
    case 0xea330:if(!am_pop(c,2,value))return false;am_word(r.d[1],value);r.pc=0xea332;return true;   // MOVE.W (A7)+,D1.
    default:return am_error(c,"unsupported animation objects fr15 PC");
    }
}
}
