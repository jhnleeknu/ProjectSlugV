#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool ofr12_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr12_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR / BCHG #bit,d16(An) (a memory operand: BYTE, bit modulo 8). op 0 tests, 1 sets, 2 clears, 3 changes; old is the bit before (the
// Z of the instruction is old = 0).
bool ofr12_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!ofr12_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    if(op==3U)return ofr12_put(c,base,displacement,1,value^mask);
    return ofr12_put(c,base,displacement,1,op==1U?(value|mask):(value&~mask));
}
// BTST #bit,d16(An); BEQ.W zero_pc (the bit clear) / BNE one_pc (the bit set).
bool ofr12_btst(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    bool old=false;if(!ofr12_bit(c,base,displacement,bit,0,old))return false;
    c.s.pc=old?one_pc:zero_pc;return true;
}
// TST.W d16(A6); BEQ.W zero_pc / other_pc.
bool ofr12_test(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr12_get(c,c.s.a[6],displacement,size,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// BCC / BCS on the known C returned to the block: clear -> clear_pc, set -> set_pc; Unknown is a checked error.
bool ofr12_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr12 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #value,(A6) followed by next_pc (the value is entered only when it is next_pc; otherwise it is written only).
bool ofr12_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr12_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// ASR.L #n (n = 1..31): arithmetic right shift of the LONG (the sign bit fills the vacated bits; no signed shift).
std::uint32_t ofr12_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t shifted=value>>n;return (value&0x80000000U)!=0U?(shifted|~(0xffffffffU>>n)):shifted;
}
// ASR.W #n (n = 1..8): the low WORD shifted right with its sign bit filling (the caller writes the WORD back with am_word).
std::uint32_t ofr12_asr_word(std::uint32_t value,unsigned int n) {
    const std::uint32_t word=value&0xffffU;const std::uint32_t shifted=word>>n;
    return (word&0x8000U)!=0U?((shifted|(0xffffU<<(16U-n)))&0xffffU):shifted;
}
// The signed value of the low WORD (CMPI .W followed by a signed Bcc: the exact signed comparison of the two WORDs).
std::int32_t ofr12_signed_word(std::uint32_t value) {
    return static_cast<std::int32_t>(value&0x7fffU)-static_cast<std::int32_t>(value&0x8000U);
}
// EXT.W Dn: the low BYTE sign-extended to the WORD (the caller writes it with am_word).
std::uint32_t ofr12_ext_byte(std::uint32_t value) {
    return (value&0x80U)!=0U?(0xff00U|(value&0xffU)):(value&0xffU);
}
// MULS.W <ea>,Dn: the signed low WORDs of both operands, the signed 32-bit product as the new LONG (|product| <= 2^30: no overflow in std::int32_t).
std::uint32_t ofr12_muls(std::uint32_t a,std::uint32_t b) {
    return static_cast<std::uint32_t>(ofr12_signed_word(a)*ofr12_signed_word(b));                       // modulo 2^32 (well defined).
}
// MULU.W #n,Dn: the unsigned low WORD times n, the unsigned 32-bit product as the new LONG (ffff x 10 < 2^32).
std::uint32_t ofr12_mulu(std::uint32_t value,std::uint32_t n) {
    return (value&0xffffU)*n;
}
// ADD.L Dn,d16(A6) (read, add modulo 2^32, write).
bool ofr12_add(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value) {
    std::uint32_t old=0;if(!ofr12_get(c,c.s.a[6],displacement,4,old))return false;return ofr12_put(c,c.s.a[6],displacement,4,old+value);
}
// ADD.W Dn,d16(A6) / SUB.W Dn,d16(A6) (the low WORD of the register; the WORD in memory modulo 2^16).
bool ofr12_add_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,bool subtract) {
    std::uint32_t old=0;if(!ofr12_get(c,c.s.a[6],displacement,2,old))return false;
    return ofr12_put(c,c.s.a[6],displacement,2,subtract?(old-value):(old+value));
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus; FR4 ofr4_bank_anim, FR10 ofr10_bank_anim, FR11 ofr11_bank_anim).
bool ofr12_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=r.a[6]+0x26U;
    if(!ofr12_put(c,r.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr12_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=r.a[6]+0x26U;
    if(!ofr12_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!ofr12_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVEA.L #table,A1; ADD.W D0,D0; ADD.W D0,D0; MOVE.L (A1,D0.W),D0;
// MOVEA.L window.l,A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l (the ROM LONG table b7fbc / b7fcc indexed by
// D0.W, then the bank-window LONG table indexed by that LONG's WORD; all reads through the live bus, WORD index arithmetic; FR11 ofr11_table_anim).
bool ofr12_table_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=r.a[6]+0x26U;
    if(!ofr12_put(c,r.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr12_put(c,r.a[6],0x22,4,value))return false;
    r.a[1]=table;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.d[0]=value;
    if(!am_read(c,window,4,value))return false;r.a[1]=value;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W d16(A6),D0 (8e); CMPI.W #0,D0; BNE.W other_pc (D0.W = 0 -> zero_pc).
bool ofr12_kind(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr12_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);
    c.s.pc=(c.s.d[0]&0xffffU)==0U?zero_pc:other_pc;return true;
}
// MOVE.L #low,96(A6); MOVE.L #high,98(A6) (the second LONG overwrites the low WORD of the first).
bool ofr12_offsets(AnimationMachineContext& c,std::uint32_t low,std::uint32_t high) {
    return ofr12_put(c,c.s.a[6],0x96,4,low) && ofr12_put(c,c.s.a[6],0x98,4,high);
}
// MOVE.L 36(A6) / 64(A6),D0; ASR.L #5,D0; SUB.W b4(A6),D0; ASR.W #1,D0; ADD.W D0,b4(A6) (c10e2 / c118a).
bool ofr12_steer(AnimationMachineContext& c,std::uint32_t displacement) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr12_get(c,r.a[6],displacement,4,value))return false;r.d[0]=ofr12_asr(value,5);
    if(!ofr12_get(c,r.a[6],0xb4,2,value))return false;am_word(r.d[0],r.d[0]-value);am_word(r.d[0],ofr12_asr_word(r.d[0],1));
    return ofr12_add_word(c,0xb4,r.d[0],false);
}
// MOVE.W b4(A6),D0; ADD.W b2(A6),D0; MOVE.W D0,b2(A6); BTST.B #0,15(A6); BEQ.W zero_pc / one_pc (c10f2 / c119a).
bool ofr12_angle(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t one_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr12_get(c,r.a[6],0xb4,2,value))return false;am_word(r.d[0],value);if(!ofr12_get(c,r.a[6],0xb2,2,value))return false;
    am_word(r.d[0],r.d[0]+value);if(!ofr12_put(c,r.a[6],0xb2,2,r.d[0]))return false;return ofr12_btst(c,r.a[6],0x15,0,zero_pc,one_pc);
}
// SUBI.W #4000,D0; NEG.W D0; ADDI.W #4000,D0 (c1108 / c11b0: the WORD mirrored about 4000).
void ofr12_mirror(AnimationMachineState& r,std::uint32_t next_pc) {
    am_word(r.d[0],r.d[0]-0x4000U);am_word(r.d[0],0U-r.d[0]);am_word(r.d[0],r.d[0]+0x4000U);r.pc=next_pc;
}
// MULU.W #10,D0; SWAP D0; MOVE.B D0,b6(A6) (c1112 / c11ba: BYTE b6 := the top four bits of the WORD).
bool ofr12_sector(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;r.d[0]=ofr12_mulu(r.d[0],0x10);am_swap(r.d[0]);return ofr12_put(c,r.a[6],0xb6,1,r.d[0]);
}
// CMPI.B #k,b6(A6); BEQ.W (the bundled BEQ c113a / c11ec, the same Z) equal_pc / other_pc.
bool ofr12_sector_is(AnimationMachineContext& c,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr12_get(c,c.s.a[6],0xb6,1,value))return false;c.s.pc=(value&0xffU)==k?equal_pc:other_pc;return true;
}
// MOVE.W #0,-(A7) (x 4); MOVE.W #21,-(A7); MOVE.W #0,-(A7) (x 2); MOVEA.L #b3dbc,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.l (the 2986 child
// b3dbc; c120c / c128a / c131a).
bool ofr12_spawn(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;
    if(!am_push(c,2,0) || !am_push(c,2,0) || !am_push(c,2,0) || !am_push(c,2,0) || !am_push(c,2,0x21) || !am_push(c,2,0) || !am_push(c,2,0))return false;
    r.a[0]=0xb3dbc;am_word(r.d[0],0x14);r.a[1]=0x100bf4;return am_call(c,0x2986,return_pc);
}
// MOVEM.W (A7)+,D0-D6 (each WORD sign-extended to the LONG, the lowest address to D0; flags unchanged); BCC.W clear_pc (C of 2986) / set_pc.  An
// Unknown C fails before the pops (FR10 b7a78, FR11 b7d8c).
bool ofr12_unpush(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects fr12 caller requires known carry");
    for(unsigned int i=0;i<7U;++i){if(!am_pop(c,2,value))return false;r.d[i]=am_extend_word(value);}
    r.pc=r.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W D2,76(A0); MOVE.W D3,78(A0); MOVE.W D4,7a(A0); MOVE.W D5,7c(A0); MOVE.W D6,7e(A0); JSR 49214.l (c1246 / c12d4 / c1364).
bool ofr12_child_fields(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;
    if(!ofr12_put(c,r.a[0],0x76,2,r.d[2]) || !ofr12_put(c,r.a[0],0x78,2,r.d[3]) || !ofr12_put(c,r.a[0],0x7a,2,r.d[4]) ||
       !ofr12_put(c,r.a[0],0x7c,2,r.d[5]) || !ofr12_put(c,r.a[0],0x7e,2,r.d[6]))return false;
    return am_call(c,0x49214,return_pc);
}
// EXT.L D0; LSL.L #8,D0; MOVE.L D0,d16(A0) (c127c c128a c130c c131a c139c c13aa: the child's LONG 36 / 3a).
bool ofr12_child_speed(AnimationMachineContext& c,std::uint32_t displacement) {
    AnimationMachineState& r=c.s;r.d[0]=am_extend_word(r.d[0])<<8;return ofr12_put(c,r.a[0],displacement,4,r.d[0]);
}
// ANDI.W #1ff,D0; ADDI.W #k,D0 (the random WORD of 49a58 limited to 0..1ff, then offset).
void ofr12_random_word(AnimationMachineState& r,std::uint32_t k) {
    am_word(r.d[0],r.d[0]&0x1ffU);am_word(r.d[0],r.d[0]+k);
}
}
// Objects FR12 (212 block starts, contract docs/analysis/animation-machine-frontier-fr12-contract.md, area C plan 10.5 FR12 row): the area-D code that
// the extended-input IO observation reaches after FR11 -- the FR10 later-unit successors 70f8e (MOVE.L #70c0c,(A6) -> FR10 70f94) and b6c58 (-> FR10
// b6c66), the FR4 table entry cc7c0 (-> FR10 cd7c6), the FR11 later-unit successors b41f2 (MULS rotation by the ROM WORD tables 4411e / 4419e, the
// c000 dead zone -> FR11 b427e), b6e5e (-> b6e6e 49392 -> b518c), c5612 (JMP 2a00), the FR11 table entry b42c4 (-> b42ea random D4 step), the item
// object handlers b42a2 / b4294 / c0924 (FR11 JMP (A0) b4034 targets) with b40f8 / b41b2 and b402a (MOVE.L A0,76(A6)), the callback c1036 (b4304:
// the C of the handler LONG 76 compare -> c1064; c106e random angle, c1cf2, c1094 .. c115a turn and sector by MULU.W #10, the three 2986 children
// b3dbc of c120c / c128a / c131a with MOVEM.W (A7)+,D0-D6, c1d06), the installs b6ed8 / b6fa4 / b7096 (the table anims b7fbc / b7fcc), 716ca (4d7a6,
// 4d84e: MULU.W #10 record 4cf64 -> C) / 71788 / 7179a (4945e C) / 717c8, 71e8c / 71f08 and 722da / 72352.  ROM data (live bus, no limit test): the
// WORD tables 4411e / 4419e, the records 4cf64 + 16k, the LONG tables b7fbc / b7fcc, the bank-window LONGs 2000d0 / 2000d4 / 2001a8 / 2001ac.
// MOVE.L #v,(A6) enters v only when v is the next PC; c0966 MOVE.L a2(A6),(A6) writes the RAM LONG only.  The 8 C consumers 716fa (4d84e), 717aa
// (BCS, 4945e), 71f1e (49fc6), b6e7c (49392), c1064 (b4304) and c123e c12cc c135c (MOVEM.W (A7)+,D0-D6; 2986) read a known C or fail; 4d84e
// (TST.W) / b4322 (ANDI) set Clear, 4d868 / b431c (ORI) Set, the RTS 4d86c passes the C of 4d84e / 4d868 to 716fa; c1260 c12ee c137e (ORI.B #1,CCR)
// set Set without a reader.  No Z / N crosses a block boundary (the bundled BEQ c113a / c11ec read the Z of their own block).
bool animation_objects_fr12_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool old=false;
    switch(r.pc) {
    case 0x4d86c:case 0xb42f6:case 0xc0984:case 0xc1158:case 0xc120a:case 0xc1d04:case 0xc1d2c:return am_return(c);   // RTS.
    // ---- 4d84e (716f4): ANDI.W #ff,D0 (x 2); MULU.W #10,D0; LEA 4cf64(PC),A2; ADDA.W D0,A2; TST.W a(A2); BNE.W 4d86c (C Clear) / ORI.B #1,CCR.
    case 0x4d84e:
        am_word(r.d[0],r.d[0]&0xffU);r.d[0]=ofr12_mulu(r.d[0],0x10);r.a[2]=am_index(0x4cf64,r.d[0]);if(!ofr12_get(c,r.a[2],0xa,2,value))return false;
        r.carry=AnimationCarryClear;r.pc=value!=0U?0x4d86c:0x4d868;return true;
    case 0x4d868:r.carry=AnimationCarrySet;r.pc=0x4d86c;return true;                                 // ORI.B #1,CCR (the RTS 4d86c passes it).
    // ---- 70f8e (FR10 70f8a BCS side): MOVE.L #70c0c,(A6) (written only) -> FR10 70f94.
    case 0x70f8e:return ofr12_install(c,0x70c0c,0x70f94);
    // ---- 71502: TST.W 9c(A6); BNE.W 71536; the bank anims 3 / 2000d0 / 70 and b / 2000d4 / a4 -> BRA.W 71682 (the later-unit stop).
    case 0x71502:return ofr12_test(c,0x9c,2,0x7150a,0x71536);
    case 0x7150a:return ofr12_bank_anim(c,3,0x2000d0,0x70,0x71532);
    case 0x71536:return ofr12_bank_anim(c,0xb,0x2000d4,0xa4,0x7155e);
    case 0x71532:r.pc=0x7155e;return true;                                                            // BRA.W 7155e.
    case 0x7155e:r.pc=0x71682;return true;                                                            // BRA.W 71682.
    // ---- 716ca: LEA -7348(A5),A0; MOVE.B 86(A6),D0; BEQ.W 716da / LEA -7258(A5),A0.
    case 0x716ca:
        r.a[0]=am_index(r.a[5],0x8cb8);if(!ofr12_get(c,r.a[6],0x86,1,value))return false;am_byte(r.d[0],value);
        r.pc=(value&0xffU)==0U?0x716da:0x716d6;return true;
    case 0x716d6:r.a[0]=am_index(r.a[5],0x8da8);r.pc=0x716da;return true;
    // MOVE.W 46(A6),D0; SUB.W 46(A6),D0; CMPI.W #30,D0; BGT.W 71502 (signed WORD; the same WORD twice).
    case 0x716da:
        if(!ofr12_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],value);if(!ofr12_get(c,r.a[6],0x46,2,value))return false;
        am_word(r.d[0],r.d[0]-value);r.pc=ofr12_signed_word(r.d[0])>0x30?0x71502:0x716ea;return true;
    case 0x716ea:if(!ofr12_get(c,r.a[6],0x86,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x4d7a6,0x716f4);   // MOVE.B 86(A6),D0; JSR 4d7a6.l.
    case 0x716f4:return am_call(c,0x4d84e,0x716fa);                                                   // JSR 4d84e.l.
    case 0x716fa:return ofr12_carry(c,0x71502,0x716fe);                                               // BCC.W 71502 (C of 4d84e).
    case 0x716fe:return ofr12_test(c,0x9c,2,0x71706,0x71732);                                         // TST.W 9c(A6); BNE.W 71732.
    case 0x71706:return ofr12_bank_anim(c,3,0x2000d0,4,0x7172e);
    case 0x71732:return ofr12_bank_anim(c,0xb,0x2000d4,4,0x7175a);
    case 0x7172e:r.pc=0x7175a;return true;                                                            // BRA.W 7175a.
    case 0x7175a:return ofr12_btst(c,r.a[6],0x82,0,0x71764,0x7176a);                                  // BTST.B #0,82(A6); BNE.W 7176a.
    case 0x71764:if(!ofr12_bit(c,r.a[6],0x15,0,3,old))return false;r.pc=0x7176a;return true;      // BCHG.B #0,15(A6).
    // MOVE.L #40000,D0; BTST.B #0,15(A6); BNE.W 7177c / the later-unit 7177a (NEG.L D0).
    case 0x7176a:r.d[0]=0x40000;return ofr12_btst(c,r.a[6],0x15,0,0x7177a,0x7177c);
    // MOVE.L D0,64(A6); TST.L D0; BPL.W 71788 / the later-unit 71786 (NEG.L D0).
    case 0x7177c:if(!ofr12_put(c,r.a[6],0x64,4,r.d[0]))return false;r.pc=(r.d[0]&0x80000000U)==0U?0x71788:0x71786;return true;
    // LSL.L #6,D0; SWAP D0; ADDI.W #80,D0; MOVE.W D0,2c(A6); MOVE.L #7179a,(A6) (next PC).
    case 0x71788:
        r.d[0]=r.d[0]<<6;am_swap(r.d[0]);am_word(r.d[0],r.d[0]+0x80U);if(!ofr12_put(c,r.a[6],0x2c,2,r.d[0]))return false;
        return ofr12_install(c,0x7179a,0x7179a);
    case 0x7179a:return ofr12_btst(c,r.a[6],0x15,7,0x71c90,0x717a4);                                  // BTST.B #7,15(A6); BEQ.W 71c90.
    case 0x717a4:return am_call(c,0x4945e,0x717aa);                                                   // JSR 4945e.l.
    case 0x717aa:return ofr12_carry(c,0x717ae,0x713d8);                                               // BCS.W 713d8 (C of 4945e).
    // MOVE.W 42(A0),D0; SUB.W 42(A6),D0; ADDI.W #40,D0; CMPI.W #80,D0; BCC.W 717c8 (unsigned WORD >= 80) / the later-unit 717c2.
    case 0x717ae:
        if(!ofr12_get(c,r.a[0],0x42,2,value))return false;am_word(r.d[0],value);if(!ofr12_get(c,r.a[6],0x42,2,value))return false;
        am_word(r.d[0],r.d[0]-value);am_word(r.d[0],r.d[0]+0x40U);r.pc=(r.d[0]&0xffffU)>=0x80U?0x717c8:0x717c2;return true;
    case 0x717c8:case 0x71f12:return am_call(c,0x4bfa4,r.pc+6U);                                    // JSR 4bfa4.l.
    case 0x717ce:case 0x71f18:case 0x72376:case 0xb6fa8:case 0xb70b2:return am_call(c,0x49fc6,r.pc+6U);   // JSR 49fc6.l.
    case 0x717d4:return ofr12_btst(c,r.a[6],0x61,0,0x717e4,0x717de);                                  // BTST.B #0,61(A6); BEQ.W 717e4.
    case 0x717de:return ofr12_install(c,0x71a80,0x717e4);                                             // MOVE.L #71a80,(A6) (written only).
    case 0x717e4:case 0x7238c:r.pc=0x72dd2;return true;                                             // BRA.W 72dd2.
    // ---- 71e8c (FR12 72386 / N15 71e82 installs): TST.W 9c(A6); BNE.W 71ec0; the bank anims 3 / 2000d0 / 24 and b / 2000d4 / 24; JSR 49a58.l.
    case 0x71e8c:return ofr12_test(c,0x9c,2,0x71e94,0x71ec0);
    case 0x71e94:return ofr12_bank_anim(c,3,0x2000d0,0x24,0x71ebc);
    case 0x71ec0:return ofr12_bank_anim(c,0xb,0x2000d4,0x24,0x71ee8);
    case 0x71ebc:r.pc=0x71ee8;return true;                                                            // BRA.W 71ee8.
    case 0x71ee8:case 0xb42ea:case 0xc1068:case 0xc1cf2:case 0xc1264:case 0xc12f2:case 0xc1382:return am_call(c,0x49a58,r.pc+6U);   // JSR 49a58.l.
    // ANDI.W #3f,D0; ADDI.W #10,D0; MOVE.W D0,88(A6); MOVE.L #0,64(A6); MOVE.L #71f08,(A6) (next PC).
    case 0x71eee:
        am_word(r.d[0],r.d[0]&0x3fU);am_word(r.d[0],r.d[0]+0x10U);if(!ofr12_put(c,r.a[6],0x88,2,r.d[0]) || !ofr12_put(c,r.a[6],0x64,4,0))return false;
        return ofr12_install(c,0x71f08,0x71f08);
    case 0x71f08:return ofr12_btst(c,r.a[6],0x15,7,0x722da,0x71f12);                                  // BTST.B #7,15(A6); BEQ.W 722da.
    case 0x71f1e:return ofr12_carry(c,0x71f28,0x71f22);                                               // BCC.W 71f28 (C of 49fc6).
    case 0x71f22:return ofr12_install(c,0x71f2c,0x71f28);                                             // MOVE.L #71f2c,(A6) (written only).
    case 0x71f28:r.pc=0x72d66;return true;                                                            // BRA.W 72d66.
    // ---- 722da (71f08): TST.W 9c(A6); BNE.W 7230e; the bank anims 3 / 2000d0 / 20 and b / 2000d4 / 20; MOVE.L 64(A6),36(A6); CLR 64 / 3a;
    // (A6) := 72352.
    case 0x722da:return ofr12_test(c,0x9c,2,0x722e2,0x7230e);
    case 0x722e2:return ofr12_bank_anim(c,3,0x2000d0,0x20,0x7230a);
    case 0x7230e:return ofr12_bank_anim(c,0xb,0x2000d4,0x20,0x72336);
    case 0x7230a:r.pc=0x72336;return true;                                                            // BRA.W 72336.
    case 0x72336:
        if(!ofr12_get(c,r.a[6],0x64,4,value) || !ofr12_put(c,r.a[6],0x36,4,value) || !ofr12_put(c,r.a[6],0x64,4,0) || !ofr12_put(c,r.a[6],0x3a,4,0))return false;
        return ofr12_install(c,0x72352,0x72352);
    // MOVE.L 64(A6),D0; SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6); MOVE.L #fff00000,D0; SUB.L 3a(A6),D0; ASR.L #5,D0; ADD.L D0,3a(A6);
    // JSR 4be34.l.
    case 0x72352:
        if(!ofr12_get(c,r.a[6],0x64,4,value) || !ofr12_get(c,r.a[6],0x36,4,other))return false;r.d[0]=ofr12_asr(value-other,5);
        if(!ofr12_add(c,0x36,r.d[0]) || !ofr12_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ofr12_asr(0xfff00000U-value,5);
        if(!ofr12_add(c,0x3a,r.d[0]))return false;return am_call(c,0x4be34,0x72376);
    case 0x7237c:return ofr12_btst(c,r.a[6],0x15,7,0x7238c,0x72386);                                  // BTST.B #7,15(A6); BEQ.W 7238c.
    case 0x72386:return ofr12_install(c,0x71e8c,0x7238c);                                             // MOVE.L #71e8c,(A6) (written only).
    // ---- b402a: MOVE.L A0,76(A6); RTS (the handler LONG of the FR11 JMP (A0) b4034).
    case 0xb402a:if(!ofr12_put(c,r.a[6],0x76,4,r.a[0]))return false;return am_return(c);
    // ---- b40f8 / b41b2 (b42a2 / b4294 with BYTE 15 bit 7): JSR 4be06.l / 4bfa4.l; MOVE.W D4,92(A6); RTS.
    case 0xb40f8:return am_call(c,0x4be06,0xb40fe);
    case 0xb41b2:return am_call(c,0x4bfa4,0xb41b8);
    case 0xb40fe:case 0xb41b8:if(!ofr12_put(c,r.a[6],0x92,2,r.d[4]))return false;return am_return(c);
    // ---- b41f2 (FR11 b41d8, WORD 8e != 0): ASR.L #8,D0; ASR.L #8,D1; MULS.W D7,D0; MULS.W D7,D1; CMPI.B #40,D4; BEQ.B b4208.
    case 0xb41f2:
        r.d[0]=ofr12_muls(ofr12_asr(r.d[0],8),r.d[7]);r.d[1]=ofr12_muls(ofr12_asr(r.d[1],8),r.d[7]);r.pc=(r.d[4]&0xffU)==0x40U?0xb4208:0xb4200;return true;
    case 0xb4200:r.pc=(r.d[4]&0xffU)==0xc0U?0xb4208:0xb4212;return true;                           // CMPI.B #c0,D4; BNE.W b4212.
    case 0xb4208:r.d[1]=0U-r.d[1];r.d[2]=r.d[0];r.d[3]=0;r.pc=0xb4250;return true;                // NEG.L D1; MOVE.L D0,D2; MOVEQ #0,D3; BRA.W b4250.
    // LEA 4411e.l,A0; LEA 4419e.l,A1; ANDI.W #ff,D4; ADD.W D4,D4; MOVE.L D0,D2; MOVE.L D1,D3; ASR.L #8 (D2, D3); MULS.W (A0,D4.W),D2;
    // MULS.W (A1,D4.W),D3; SUB.L D3,D2; ASR.L #8,D2; MOVE.L D2,D3; MULS.W (A0,D4.W),D2; MULS.W (A1,D4.W),D3; NEG.L D3; SUB.L D2,D0; SUB.L D3,D1;
    // NEG.L D0; NEG.L D1; ADD.L D2,D0; ADD.L D3,D1 (the ROM WORD tables read through the live bus, the index D4.W sign-extended).
    case 0xb4212:{
        r.a[0]=0x4411e;r.a[1]=0x4419e;am_word(r.d[4],r.d[4]&0xffU);am_word(r.d[4],r.d[4]+r.d[4]);
        r.d[2]=ofr12_asr(r.d[0],8);r.d[3]=ofr12_asr(r.d[1],8);
        std::uint32_t first=0;std::uint32_t second=0;
        if(!am_read(c,am_index(r.a[0],r.d[4]),2,first) || !am_read(c,am_index(r.a[1],r.d[4]),2,second))return false;
        r.d[2]=ofr12_muls(r.d[2],first);r.d[3]=ofr12_muls(r.d[3],second);r.d[2]=ofr12_asr(r.d[2]-r.d[3],8);r.d[3]=r.d[2];
        r.d[2]=ofr12_muls(r.d[2],first);r.d[3]=ofr12_muls(r.d[3],second);r.d[3]=0U-r.d[3];
        r.d[0]=r.d[0]-r.d[2];r.d[1]=r.d[1]-r.d[3];r.d[0]=0U-r.d[0];r.d[1]=0U-r.d[1];r.d[0]=r.d[0]+r.d[2];r.d[1]=r.d[1]+r.d[3];r.pc=0xb4250;return true;}
    // MOVE.L #c000,D7; MOVE.L D0,36(A6); BPL.W b4260 / NEG.L D0.
    case 0xb4250:r.d[7]=0xc000;if(!ofr12_put(c,r.a[6],0x36,4,r.d[0]))return false;r.pc=(r.d[0]&0x80000000U)==0U?0xb4260:0xb425e;return true;
    case 0xb425e:r.d[0]=0U-r.d[0];r.pc=0xb4260;return true;                                          // NEG.L D0.
    case 0xb4260:r.pc=r.d[7]<=r.d[0]?0xb426a:0xb4266;return true;                                    // CMP.L D0,D7; BLS.W b426a (unsigned D7 <= D0).
    case 0xb4266:if(!ofr12_put(c,r.a[6],0x36,4,0))return false;r.pc=0xb426a;return true;          // CLR.L 36(A6).
    case 0xb426a:if(!ofr12_put(c,r.a[6],0x3a,4,r.d[1]))return false;r.pc=(r.d[1]&0x80000000U)==0U?0xb4274:0xb4272;return true;   // MOVE.L D1,3a; BPL.
    case 0xb4272:r.d[1]=0U-r.d[1];r.pc=0xb4274;return true;                                          // NEG.L D1.
    case 0xb4274:r.pc=r.d[7]<=r.d[1]?0xb427e:0xb427a;return true;                                    // CMP.L D1,D7; BLS.W b427e (unsigned D7 <= D1).
    case 0xb427a:if(!ofr12_put(c,r.a[6],0x3a,4,0))return false;r.pc=0xb427e;return true;          // CLR.L 3a(A6) -> FR11 b427e.
    // ---- b4294 / b42a2 (handlers of the FR11 JMP (A0) b4034): BTST.B #7,15(A6); BNE.W b41b2 / b40f8; BRA.W b411c (FR11).
    case 0xb4294:return ofr12_btst(c,r.a[6],0x15,7,0xb429e,0xb41b2);
    case 0xb42a2:return ofr12_btst(c,r.a[6],0x15,7,0xb42ac,0xb40f8);
    case 0xb429e:case 0xb42ac:r.pc=0xb411c;return true;                                             // BRA.W b411c.
    // ---- b42c4 (the FR11 table b42b8 entry c): BRA.W b42ea; JSR 49a58.l / TST.B D0; BMI.W b42f8 / RTS.
    case 0xb42c4:r.pc=0xb42ea;return true;
    case 0xb42f0:r.pc=(r.d[0]&0x80U)!=0U?0xb42f8:0xb42f6;return true;
    // ANDI.B #1c,D0; SUBI.B #c,D0; ADD.B D0,D4; RTS.
    case 0xb42f8:am_byte(r.d[0],r.d[0]&0x1cU);am_byte(r.d[0],r.d[0]-0xcU);am_byte(r.d[4],r.d[4]+r.d[0]);return am_return(c);
    // ---- b4304 (c105e): MOVE.L 76(A6),D0; CMPI.L #b4036,D0; BEQ.W b4322 / CMPI.L #b403e,D0; BEQ.W b4322 / ORI.B #1,CCR; RTS / ANDI.B #fe,CCR; RTS.
    case 0xb4304:if(!ofr12_get(c,r.a[6],0x76,4,value))return false;r.d[0]=value;r.pc=value==0xb4036U?0xb4322:0xb4312;return true;
    case 0xb4312:r.pc=r.d[0]==0xb403eU?0xb4322:0xb431c;return true;
    case 0xb431c:r.carry=AnimationCarrySet;return am_return(c);
    case 0xb4322:r.carry=AnimationCarryClear;return am_return(c);
    // ---- b518c (b6e86 JMP): MOVE.L A0,7e(A6); MOVE.L #b5198,(A6) (written); RTS.
    case 0xb518c:if(!ofr12_put(c,r.a[6],0x7e,4,r.a[0]) || !ofr12_put(c,r.a[6],0,4,0xb5198))return false;return am_return(c);
    // ---- b6c58 (FR10 b6c42 BLE): BCLR.B #0,15(A6); MOVE.L #70000,64(A6) -> FR10 b6c66.
    case 0xb6c58:if(!ofr12_bit(c,r.a[6],0x15,0,2,old) || !ofr12_put(c,r.a[6],0x64,4,0x70000))return false;r.pc=0xb6c66;return true;
    // ---- b6e5e (FR11 b6e5a BCS side): MOVE.L #b6ed8,(A6) (written); CMPI.W #ffff,7c(A6); BNE.W b6e8c (FR11).
    case 0xb6e5e:
        if(!ofr12_put(c,r.a[6],0,4,0xb6ed8) || !ofr12_get(c,r.a[6],0x7c,2,value))return false;r.pc=(value&0xffffU)!=0xffffU?0xb6e8c:0xb6e6e;return true;
    // MOVE.B 9d(A6),D0; ANDI.W #ff,D0; JSR 49392.l.
    case 0xb6e6e:if(!ofr12_get(c,r.a[6],0x9d,1,value))return false;am_word(r.d[0],value&0xffU);return am_call(c,0x49392,0xb6e7c);
    case 0xb6e7c:return ofr12_carry(c,0xb6e8c,0xb6e80);                                               // BCC.W b6e8c (C of 49392).
    case 0xb6e80:if(!ofr12_put(c,r.a[6],0x7c,2,0))return false;r.pc=0xb518c;return true;          // MOVE.W #0,7c(A6); JMP b518c.l.
    // ---- b6ed8 (callback): BTST.B #1,9f(A6); BNE.W b6ff4; the anims by WORD 8e (b7fbc), the offsets, BYTE 15 bit 0 by WORD 82, LONG 64 = +-40000.
    case 0xb6ed8:return ofr12_btst(c,r.a[6],0x9f,1,0xb6ee2,0xb6ff4);
    case 0xb6ee2:return ofr12_kind(c,0x8e,0xb6eee,0xb6f2a);
    case 0xb6eee:return ofr12_table_anim(c,0x1b3,0x2001a8,0xb7fbc,0xb6f26);
    case 0xb6f2a:return ofr12_table_anim(c,0x1bb,0x2001ac,0xb7fbc,0xb6f62);
    case 0xb6f26:r.pc=0xb6f62;return true;                                                            // BRA.W b6f62.
    // MOVE.L #fffffff4,96(A6); MOVE.L #1e,98(A6); BCLR.B #0,15(A6); CMPI.W #1,82(A6); BNE.W b6f88 / BSET.B #0,15(A6).
    case 0xb6f62:
        if(!ofr12_offsets(c,0xfffffff4U,0x1e) || !ofr12_bit(c,r.a[6],0x15,0,2,old) || !ofr12_get(c,r.a[6],0x82,2,value))return false;
        r.pc=(value&0xffffU)!=1U?0xb6f88:0xb6f82;return true;
    case 0xb6f82:if(!ofr12_bit(c,r.a[6],0x15,0,1,old))return false;r.pc=0xb6f88;return true;
    // MOVE.L #40000,64(A6); BTST.B #0,15(A6); BNE.W b6f9e / NEG.L 64(A6).
    case 0xb6f88:if(!ofr12_put(c,r.a[6],0x64,4,0x40000))return false;return ofr12_btst(c,r.a[6],0x15,0,0xb6f9a,0xb6f9e);
    case 0xb6f9a:if(!ofr12_get(c,r.a[6],0x64,4,value) || !ofr12_put(c,r.a[6],0x64,4,0U-value))return false;r.pc=0xb6f9e;return true;
    case 0xb6f9e:return ofr12_install(c,0xb6fa4,0xb6fa4);                                             // MOVE.L #b6fa4,(A6) (next PC).
    case 0xb6fa4:return am_call(c,0xb7cfa,0xb6fa8);                                                   // JSR b7cfa(PC).
    case 0xb6fae:return ofr12_btst(c,r.a[6],0x61,0,0xb6fbe,0xb6fb8);                                  // BTST.B #0,61(A6); BEQ.W b6fbe.
    case 0xb6fb8:return ofr12_install(c,0xb6fc2,0xb6fbe);                                             // MOVE.L #b6fc2,(A6) (written only).
    case 0xb6fbe:case 0xb70fc:r.pc=0xb76d2;return true;                                             // BRA.W b76d2.
    // ---- b6ff4 (BYTE 9f bit 1): the anims by WORD 8e (b7fcc), the offsets, BCLR #3,61; BYTE 9c := 8; (A6) := b7096.
    case 0xb6ff4:return ofr12_kind(c,0x8e,0xb7000,0xb703c);
    case 0xb7000:return ofr12_table_anim(c,0x1b3,0x2001a8,0xb7fcc,0xb7038);
    case 0xb703c:return ofr12_table_anim(c,0x1bb,0x2001ac,0xb7fcc,0xb7074);
    case 0xb7038:r.pc=0xb7074;return true;                                                            // BRA.W b7074.
    case 0xb7074:
        if(!ofr12_offsets(c,0xfffffff6U,0x18) || !ofr12_bit(c,r.a[6],0x61,3,2,old) || !ofr12_put(c,r.a[6],0x9c,1,8))return false;
        return ofr12_install(c,0xb7096,0xb7096);
    // MOVE.L #fffe0000,D0; SUB.L 3a(A6),D0; ASR.L #3,D0; ADD.L D0,3a(A6); JSR 4be34.l.
    case 0xb7096:
        if(!ofr12_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ofr12_asr(0xfffe0000U-value,3);if(!ofr12_add(c,0x3a,r.d[0]))return false;
        return am_call(c,0x4be34,0xb70ac);
    case 0xb70ac:return am_call(c,0x492c8,0xb70b2);                                                   // JSR 492c8.l.
    // SUBQ.B #1,9c(A6); BNE.W b70ce (the new BYTE) / MOVE.B #8,9c(A6); MOVE.L #60000,3a(A6).
    case 0xb70b8:
        if(!ofr12_get(c,r.a[6],0x9c,1,value) || !ofr12_put(c,r.a[6],0x9c,1,value-1U))return false;r.pc=((value-1U)&0xffU)!=0U?0xb70ce:0xb70c0;return true;
    case 0xb70c0:if(!ofr12_put(c,r.a[6],0x9c,1,8) || !ofr12_put(c,r.a[6],0x3a,4,0x60000))return false;r.pc=0xb70ce;return true;
    case 0xb70ce:return ofr12_btst(c,r.a[6],0x61,1,0xb70e4,0xb70d8);                                  // BTST.B #1,61(A6); BEQ.W b70e4.
    case 0xb70d8:if(!ofr12_bit(c,r.a[6],0x61,3,1,old) || !ofr12_put(c,r.a[6],0x84,2,0x1e))return false;r.pc=0xb70e4;return true;   // BSET #3,61; WORD 84 := 1e.
    case 0xb70e4:return ofr12_btst(c,r.a[6],0x61,3,0xb70fc,0xb70ee);                                  // BTST.B #3,61(A6); BEQ.W b70fc.
    // SUBQ.W #1,84(A6); BPL.W b70fc (the sign of the new WORD) / MOVE.L #b7742,(A6) (written only).
    case 0xb70ee:
        if(!ofr12_get(c,r.a[6],0x84,2,value) || !ofr12_put(c,r.a[6],0x84,2,value-1U))return false;r.pc=((value-1U)&0x8000U)==0U?0xb70fc:0xb70f6;return true;
    case 0xb70f6:return ofr12_install(c,0xb7742,0xb70fc);
    // ---- c0924 (handler): TST.W 64(A6); SMI.B D0; ORI.B #1,D0; EXT.W D0; SWAP D0; CLR.W D0 (D0 = +-10000 by the sign of WORD 64); SUB.L 64(A6),D0;
    // ASR.L #1,D0; ADD.L D0,64(A6); JMP b4294.l.
    case 0xc0924:
        if(!ofr12_get(c,r.a[6],0x64,2,value))return false;am_byte(r.d[0],(value&0x8000U)!=0U?0xffU:0U);am_byte(r.d[0],r.d[0]|1U);
        am_word(r.d[0],ofr12_ext_byte(r.d[0]));am_swap(r.d[0]);am_word(r.d[0],0);
        if(!ofr12_get(c,r.a[6],0x64,4,value))return false;r.d[0]=ofr12_asr(r.d[0]-value,1);if(!ofr12_add(c,0x64,r.d[0]))return false;r.pc=0xb4294;return true;
    case 0xc0944:r.a[0]=0xb42a2;return am_call(c,0xb402a,0xc0950);                                  // LEA b42a2.l,A0; JSR b402a.l.
    case 0xc0950:return ofr12_install(c,0xc0956,0xc0956);                                             // MOVE.L #c0956,(A6) (next PC).
    case 0xc0956:case 0xc10a0:case 0xc1170:case 0xc1d0c:return am_call(c,0xb4030,r.pc+6U);          // JSR b4030.l.
    case 0xc095c:return ofr12_btst(c,r.a[6],0x15,7,0xc0966,0xc096a);                                  // BTST.B #7,15(A6); BNE.W c096a.
    case 0xc0966:if(!ofr12_get(c,r.a[6],0xa2,4,value) || !ofr12_put(c,r.a[6],0,4,value))return false;r.pc=0xc096a;return true;   // MOVE.L a2(A6),(A6).
    case 0xc096a:case 0xc113e:case 0xc11f0:case 0xc1d12:return am_call(c,0xb4958,r.pc+6U);          // JSR b4958.l.
    case 0xc0970:case 0xc1144:case 0xc11f6:case 0xc1d18:return am_call(c,0xb4ab0,r.pc+6U);          // JSR b4ab0.l (D0.B := BYTE 96).
    case 0xc0976:case 0xc114a:case 0xc11fc:case 0xc1d1e:r.pc=(r.d[0]&4U)!=0U?0xc1d2eU:r.pc+8U;return true;   // BTST #2,D0; BNE.W c1d2e.
    case 0xc097e:case 0xc1152:case 0xc1204:case 0xc1d26:return am_call(c,0xb4334,r.pc+6U);          // JSR b4334.l.
    // ---- c1036 (callback): MOVE.W #72,D0; MOVE.W #3,D1; MOVE.B #0,D2; JSR c6a96.l / MOVE.W #1fb,20(A6); MOVEA.L #c1e3a,A1; MOVE.W #100,D0;
    // JSR 49f8c.l / JSR b4304.l / BCC.W c1d06.
    case 0xc1036:am_word(r.d[0],0x72);am_word(r.d[1],3);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xc1048);
    case 0xc1048:if(!ofr12_put(c,r.a[6],0x20,2,0x1fb))return false;r.a[1]=0xc1e3a;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xc105e);
    case 0xc105e:return am_call(c,0xb4304,0xc1064);
    case 0xc1064:return ofr12_carry(c,0xc1d06,0xc1068);                                               // BCC.W c1d06 (C of b4304).
    // MOVE.W D0,b2(A6); ROR.W #8,D0; SMI.B D1; ANDI.W #3ff,D0; ADDI.W #800,D0; EXT.W D1; EOR.W D1,D0; SUB.W D1,D0 (negated when bit 7 of the random
    // WORD is set); MOVE.W D0,b4(A6); MOVE.L #c1094,a2(A6); JSR c1cf2(PC).
    case 0xc106e:
        if(!ofr12_put(c,r.a[6],0xb2,2,r.d[0]))return false;value=r.d[0]&0xffffU;am_word(r.d[0],((value<<8)|(value>>8))&0xffffU);
        am_byte(r.d[1],(r.d[0]&0x8000U)!=0U?0xffU:0U);am_word(r.d[0],r.d[0]&0x3ffU);am_word(r.d[0],r.d[0]+0x800U);
        am_word(r.d[1],ofr12_ext_byte(r.d[1]));am_word(r.d[0],r.d[0]^r.d[1]);am_word(r.d[0],r.d[0]-r.d[1]);
        if(!ofr12_put(c,r.a[6],0xb4,2,r.d[0]) || !ofr12_put(c,r.a[6],0xa2,4,0xc1094))return false;return am_call(c,0xc1cf2,0xc1094);
    // MOVE.W #f,b0(A6); MOVE.L #c10a0,(A6) (next PC).
    case 0xc1094:if(!ofr12_put(c,r.a[6],0xb0,2,0xf))return false;return ofr12_install(c,0xc10a0,0xc10a0);
    case 0xc10a6:return ofr12_btst(c,r.a[6],0x15,7,0xc10c6,0xc10b0);                                  // BTST.B #7,15(A6); BEQ.W c10c6.
    // MOVE.W b4(A6),D0; ASR.W #3,D0; EXT.L D0; LSL.L #8,D0; ASR.L #1,D0; ADD.L D0,36(A6); ASR.L #5,D0; SUB.W D0,b4(A6).
    case 0xc10b0:
        if(!ofr12_get(c,r.a[6],0xb4,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],ofr12_asr_word(r.d[0],3));
        r.d[0]=am_extend_word(r.d[0])<<8;r.d[0]=ofr12_asr(r.d[0],1);if(!ofr12_add(c,0x36,r.d[0]))return false;r.d[0]=ofr12_asr(r.d[0],5);
        if(!ofr12_add_word(c,0xb4,r.d[0],true))return false;r.pc=0xc10c6;return true;
    case 0xc10c6:return ofr12_btst(c,r.a[6],0x15,7,0xc10d8,0xc10d0);                                  // BTST.B #7,15(A6); BEQ.W c10d8.
    // LSR.W b0(A6) (the WORD shifted right by one); BEQ.W c115a (the new WORD zero).
    case 0xc10d0:if(!ofr12_get(c,r.a[6],0xb0,2,value) || !ofr12_put(c,r.a[6],0xb0,2,(value&0xffffU)>>1))return false;r.pc=((value&0xffffU)>>1)==0U?0xc115a:0xc10d8;return true;
    case 0xc10d8:return ofr12_btst(c,r.a[6],0x15,7,0xc10f2,0xc10e2);                                  // BTST.B #7,15(A6); BEQ.W c10f2.
    case 0xc10e2:if(!ofr12_steer(c,0x36))return false;r.pc=0xc10f2;return true;
    case 0xc10f2:return ofr12_angle(c,0xc1112,0xc1108);
    case 0xc1108:ofr12_mirror(r,0xc1112);return true;
    // MULU.W #10,D0; SWAP D0; MOVE.B D0,b6(A6); BTST.B #7,15(A6); BEQ.W c113e.
    case 0xc1112:if(!ofr12_sector(c))return false;return ofr12_btst(c,r.a[6],0x15,7,0xc113e,0xc1126);
    // CMPI.B #0,b6(A6); BEQ.W c113a (the bundled BEQ.W c120c, Z still set) / CMPI.B #2,b6(A6); BEQ.W c113a (-> c120c); BEQ.W c120c not taken -> c113e.
    case 0xc1126:return ofr12_sector_is(c,0,0xc120c,0xc1130);
    case 0xc1130:return ofr12_sector_is(c,2,0xc120c,0xc113e);
    // MOVE.L 36(A6),64(A6); LEA c0924(PC),A0; JSR b402a.l.
    case 0xc115a:if(!ofr12_get(c,r.a[6],0x36,4,value) || !ofr12_put(c,r.a[6],0x64,4,value))return false;r.a[0]=0xc0924;return am_call(c,0xb402a,0xc116a);
    case 0xc116a:return ofr12_install(c,0xc1170,0xc1170);                                             // MOVE.L #c1170,(A6) (next PC).
    case 0xc1176:return ofr12_btst(c,r.a[6],0x15,7,0xc1094,0xc1180);                                  // BTST.B #7,15(A6); BEQ.W c1094.
    case 0xc1180:return ofr12_btst(c,r.a[6],0x15,7,0xc119a,0xc118a);                                  // BTST.B #7,15(A6); BEQ.W c119a.
    case 0xc118a:if(!ofr12_steer(c,0x64))return false;r.pc=0xc119a;return true;
    case 0xc119a:return ofr12_angle(c,0xc11ba,0xc11b0);
    case 0xc11b0:ofr12_mirror(r,0xc11ba);return true;
    // MULU.W #10,D0; SWAP D0; MOVE.B D0,b6(A6); CMPI.B #0,b6(A6); BEQ.W c11ec (the bundled BEQ.W c0944) / c11ce.
    case 0xc11ba:if(!ofr12_sector(c))return false;return ofr12_sector_is(c,0,0xc0944,0xc11ce);
    case 0xc11ce:return ofr12_sector_is(c,1,0xc0944,0xc11d8);
    case 0xc11d8:return ofr12_sector_is(c,2,0xc0944,0xc11e2);
    case 0xc11e2:return ofr12_sector_is(c,3,0xc0944,0xc11f0);                                         // ...; BEQ.W c0944 not taken -> c11f0.
    // ---- the three 2986 children b3dbc (c120c / c128a / c131a), their MOVEM.W (A7)+,D0-D6, fields, random LONGs 36 / 3a of the child (A0).
    case 0xc120c:return ofr12_spawn(c,0xc123e);
    case 0xc123e:return ofr12_unpush(c,0xc1264,0xc1246);
    case 0xc12cc:return ofr12_unpush(c,0xc12f2,0xc12d4);
    case 0xc135c:return ofr12_unpush(c,0xc1382,0xc1364);
    case 0xc1246:return ofr12_child_fields(c,0xc1260);
    case 0xc12d4:return ofr12_child_fields(c,0xc12ee);
    case 0xc1364:return ofr12_child_fields(c,0xc137e);
    case 0xc1260:case 0xc12ee:case 0xc137e:r.carry=AnimationCarrySet;r.pc=r.pc+4U;return true;     // ORI.B #1,CCR (no reader).
    // ANDI.W #1ff,D0; ADDQ.W #1,D0 / ADDI.W #101,D0 / ADDI.W #fd01,D0; BTST.B #0,15(A6); BEQ.W (skip) / NEG.W D0.
    case 0xc126a:ofr12_random_word(r,1);return ofr12_btst(c,r.a[6],0x15,0,0xc127c,0xc127a);
    case 0xc12f8:ofr12_random_word(r,0x101);return ofr12_btst(c,r.a[6],0x15,0,0xc130c,0xc130a);
    case 0xc1388:ofr12_random_word(r,0xfd01);return ofr12_btst(c,r.a[6],0x15,0,0xc139c,0xc139a);
    case 0xc127a:case 0xc130a:case 0xc139a:am_word(r.d[0],0U-r.d[0]);r.pc=r.pc+2U;return true;      // NEG.W D0.
    // EXT.L D0; LSL.L #8,D0; MOVE.L D0,36(A0); JSR 49a58.l.
    case 0xc127c:case 0xc130c:case 0xc139c:if(!ofr12_child_speed(c,0x36))return false;return am_call(c,0x49a58,r.pc+0xeU);
    // ANDI.W #1ff,D0; ADDI.W #301 / #101,D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,3a(A0); the next 2986 child / JMP 2a00.l.
    case 0xc128a:ofr12_random_word(r,0x301);if(!ofr12_child_speed(c,0x3a))return false;return ofr12_spawn(c,0xc12cc);
    case 0xc131a:ofr12_random_word(r,0x101);if(!ofr12_child_speed(c,0x3a))return false;return ofr12_spawn(c,0xc135c);
    case 0xc13aa:ofr12_random_word(r,0x101);if(!ofr12_child_speed(c,0x3a))return false;r.pc=0x2a00;return true;
    // ---- c1cf2 (c1090 JSR): JSR 49a58.l / TST.B D0; BPL.W c1d04 / BCHG.B #0,15(A6) / RTS.
    case 0xc1cf8:r.pc=(r.d[0]&0x80U)==0U?0xc1d04:0xc1cfe;return true;
    case 0xc1cfe:if(!ofr12_bit(c,r.a[6],0x15,0,3,old))return false;r.pc=0xc1d04;return true;
    case 0xc1d06:return ofr12_install(c,0xc1d0c,0xc1d0c);                                             // MOVE.L #c1d0c,(A6) (next PC).
    // ---- c5612 (FR11 c560e BCS side): JMP 2a00.l.  cc7c0 (the FR4 table cc7a8 entry): BRA.W cd7c6 (FR10).
    case 0xc5612:r.pc=0x2a00;return true;
    case 0xcc7c0:r.pc=0xcd7c6;return true;
    default:return am_error(c,"unsupported animation objects fr12 PC");
    }
}
}
