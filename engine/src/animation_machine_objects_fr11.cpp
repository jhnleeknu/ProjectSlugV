#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool ofr11_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr11_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR #bit,d16(An) (a memory operand: BYTE, bit modulo 8). op 0 tests, 1 sets, 2 clears; old is the bit before (the Z of the
// instruction is old = 0).
bool ofr11_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!ofr11_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return ofr11_put(c,base,displacement,1,op==1U?(value|mask):(value&~mask));
}
// BTST #bit,d16(An); BEQ.W zero_pc (the bit clear) / BNE one_pc (the bit set).
bool ofr11_btst(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    bool old=false;if(!ofr11_bit(c,base,displacement,bit,0,old))return false;
    c.s.pc=old?one_pc:zero_pc;return true;
}
// TST.B / TST.W d16(A6); BEQ.W zero_pc / other_pc.
bool ofr11_test(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr11_get(c,c.s.a[6],displacement,size,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// BCC on the known C returned to the block: clear -> clear_pc, set -> set_pc; Unknown is a checked error.
bool ofr11_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr11 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #value,(A6) followed by next_pc (the value is entered only when it is next_pc; otherwise it is written only).
bool ofr11_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr11_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// ASR.L #n (n = 1..31): arithmetic right shift of the LONG (the sign bit fills the vacated bits; no signed shift).
std::uint32_t ofr11_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t shifted=value>>n;return (value&0x80000000U)!=0U?(shifted|~(0xffffffffU>>n)):shifted;
}
// ASR.W #1: the low WORD shifted right by one with its sign bit kept (the caller writes the WORD back with am_word).
std::uint32_t ofr11_asr_word(std::uint32_t value) {
    return ((value&0xffffU)>>1)|(value&0x8000U);
}
// The signed value of the low WORD (CMP / CMPI .W and TST.W followed by a signed Bcc: the exact signed comparison of the two WORDs).
std::int32_t ofr11_signed_word(std::uint32_t value) {
    return static_cast<std::int32_t>(value&0x7fffU)-static_cast<std::int32_t>(value&0x8000U);
}
// MULS.W <ea>,Dn: the signed low WORDs of both operands, the signed 32-bit product as the new LONG (|product| <= 2^30: no overflow in std::int32_t).
std::uint32_t ofr11_muls(std::uint32_t a,std::uint32_t b) {
    return static_cast<std::uint32_t>(ofr11_signed_word(a)*ofr11_signed_word(b));                       // modulo 2^32 (well defined).
}
// ADD.L Dn,d16(A6) (read, add modulo 2^32, write).
bool ofr11_add(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value) {
    std::uint32_t old=0;if(!ofr11_get(c,c.s.a[6],displacement,4,old))return false;return ofr11_put(c,c.s.a[6],displacement,4,old+value);
}
// NEG.L d16(A6).
bool ofr11_neg(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t old=0;if(!ofr11_get(c,c.s.a[6],displacement,4,old))return false;return ofr11_put(c,c.s.a[6],displacement,4,0U-old);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus; FR4 ofr4_bank_anim, FR10 ofr10_bank_anim).
bool ofr11_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=r.a[6]+0x26U;
    if(!ofr11_put(c,r.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr11_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=r.a[6]+0x26U;
    if(!ofr11_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!ofr11_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVEA.L #table,A1; ADD.W D0,D0; ADD.W D0,D0; MOVE.L (A1,D0.W),D0;
// MOVEA.L window.l,A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l (the ROM LONG table b7f5c / b7f64 / b7f7c /
// b7fc4 indexed by D0.W, then the bank-window LONG table indexed by that LONG's WORD; all reads through the live bus, WORD index arithmetic; FR10
// ofr10_table_anim with the table as a parameter).
bool ofr11_table_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=r.a[6]+0x26U;
    if(!ofr11_put(c,r.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr11_put(c,r.a[6],0x22,4,value))return false;
    r.a[1]=table;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.d[0]=value;
    if(!am_read(c,window,4,value))return false;r.a[1]=value;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 8a(A6),20(A6); MOVEA.L #anim,A1; MOVE.W #100,D0; JSR 49f8c.l.
bool ofr11_anim(AnimationMachineContext& c,std::uint32_t anim,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr11_get(c,r.a[6],0x8a,2,value) || !ofr11_put(c,r.a[6],0x20,2,value))return false;r.a[1]=anim;am_word(r.d[0],0x100);
    return am_call(c,0x49f8c,return_pc);
}
// MOVE.W d16(A6),D0 (8e / 8c); [CMPI.W #0,D0;] BNE.W other_pc (D0.W = 0 -> zero_pc).
bool ofr11_kind(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr11_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);
    c.s.pc=(c.s.d[0]&0xffffU)==0U?zero_pc:other_pc;return true;
}
// CMPI.W #k,D0; BNE.W other_pc (D0.W = k -> equal_pc).
void ofr11_select(AnimationMachineState& r,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    r.pc=(r.d[0]&0xffffU)==k?equal_pc:other_pc;
}
// MOVE.L #low,96(A6); MOVE.L #high,98(A6) (the second LONG overwrites the low WORD of the first); [LEA 26(A6),A0; JSR b7e06(PC)].
bool ofr11_offsets(AnimationMachineContext& c,std::uint32_t low,std::uint32_t high) {
    return ofr11_put(c,c.s.a[6],0x96,4,low) && ofr11_put(c,c.s.a[6],0x98,4,high);
}
bool ofr11_offsets_call(AnimationMachineContext& c,std::uint32_t low,std::uint32_t high,std::uint32_t return_pc) {
    if(!ofr11_offsets(c,low,high))return false;c.s.a[0]=c.s.a[6]+0x26U;return am_call(c,0xb7e06,return_pc);
}
// JMP (A0) b4034 with A0 = LONG 76(A6) (contract decision 2): only the handlers that the ROM writers of LONG 76 produce -- b3f02 MOVE.L A0,76(A6)
// with A0 from the FR1 table b3dcc (b41be b4036 b42a2 b403e; b3e1c passes the same LONG 7a), b402a MOVE.L A0,76(A6) after LEA b42a2 / c0924 / b4294
// (c0944 c0fa8 .. c1a40 c1bb0) -- are targets (the routing decides: b41be / b403e are FR11 blocks, the others unrouted stops); any other A0 is a
// checked error.
bool ofr11_handler(AnimationMachineContext& c,std::uint32_t target) {
    const std::uint32_t allowed[]={0xb41be,0xb4036,0xb42a2,0xb403e,0xc0924,0xb4294};
    for(unsigned int i=0;i<sizeof(allowed)/sizeof(allowed[0]);++i)if(target==allowed[i]){c.s.pc=target;return true;}
    return am_error(c,"unsupported animation objects fr11 jump target");
}
}
// Objects FR11 (192 block starts, contract docs/analysis/animation-machine-frontier-fr11-contract.md, area C plan 10.5 FR11 row): the area-D code that
// the extended-input IO observation reaches after C10 -- the FR10 later-unit successors 70e42 (bank anims -> FR10 70efe), 70fac (|D0| < 30), cd7e2
// (NEG.L), cd92e, cd96c (anim by WORD 8c -> cdafc), the FR4 table entries cc836 / cc842, the item object handlers of the FR1 2986 child b3dbc: b4030
// (JMP (A0) on LONG 76, decision 2) -> b403e (spring to 40000, bounds of the b4aca record) / b41be -> b411c (input 1aa3a, MULS rotation by the ROM WORD
// tables 4411e / 4419e) -> b4104 / b41cc -> b42b0 (JMP b42b8(PC,D0.W), decision 2) / b427e, the kind handler bfb5a -> bfc2a (MULU.W #8, ROM table
// bfdee, the bank-window LONG 2001c0) -> bfcaa (sine table 4411e) -> bfcd8 / bfdb2 -> b3e1c (TRAP #15 b3e58 when LONG 7a = 0: a boundary outside the
// unit), the U18 install b67b2 -> b686e (the 28ae child b774a), the FR10 installs b6ca2 -> b6d6a / b6d82 -> b6e50 -> b6e8c, the 28ae child b774a ->
// b77f4, the script callback b7d4a (2986 child b3dbc with seven pushed WORDs, MOVEM.W (A7)+,D0-D6), the FR3 install c5432 -> c5470 -> c5486 ->
// c5496 -> c54a6 (JMP c54b2(PC,D0.W), decision 2) / c5540, and the 28ae child c5592 -> c5602.  ROM data (live bus, no limit test): the LONG tables
// b7f5c / b7f64 / b7f7c / b7fc4, the WORD tables b7f14 / bfdd0 / 4411e / 4419e, the LONG records bfdee + 8k, the bank-window LONGs 2000d0 / 2000d4 /
// 200080 / 200094 / 2001a8 / 2001ac / 2001c0.  MOVE.L #v,(A6) enters v only when v is the next PC.  The 11 C consumers b687a b6d74 b6e5a b7800
// c547c c560e (49fc6), b688e (28ae), b6cac b6d8c (49392), c5492 (4b54e) and b7d8c (MOVEM.W (A7)+,D0-D6; 2986) read a known C or fail; b689c /
// b7dae (ORI.B #1,CCR) set C before a MOVE that clears it (no reader).  No Z / N crosses a block boundary.
bool animation_objects_fr11_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool old=false;
    switch(r.pc) {
    case 0xb40f6:case 0xb4292:case 0xb42c8:case 0xb780a:case 0xb7dd4:case 0xbfcf8:case 0xc551e:case 0xc5618:return am_return(c);   // RTS.
    // ---- 70e42 (FR10 70e2a BPL fall-through): TST.W 9c(A6); BNE.W 70e76; the bank anims 3 / 2000d0 / 110 and b / 2000d4 / 188 -> BRA.W 70efe.
    case 0x70e42:return ofr11_test(c,0x9c,2,0x70e4a,0x70e76);
    case 0x70e4a:return ofr11_bank_anim(c,3,0x2000d0,0x110,0x70e72);
    case 0x70e76:return ofr11_bank_anim(c,0xb,0x2000d4,0x188,0x70e9e);
    case 0x70e72:r.pc=0x70e9e;return true;                                                            // BRA.W 70e9e.
    case 0x70e9e:r.pc=0x70efe;return true;                                                            // BRA.W 70efe.
    // ---- 70fac (FR10 70f94): TST.W D0; BPL.W 70fb4 / NEG.W D0 / CMPI.W #30,D0; BCS.W 70fc2 (unsigned WORD) / MOVE.L #71468,(A6) (written only).
    case 0x70fac:r.pc=(r.d[0]&0x8000U)==0U?0x70fb4:0x70fb2;return true;
    case 0x70fb2:am_word(r.d[0],0U-r.d[0]);r.pc=0x70fb4;return true;
    case 0x70fb4:r.pc=(r.d[0]&0xffffU)<0x30U?0x70fc2:0x70fbc;return true;
    case 0x70fbc:return ofr11_install(c,0x71468,0x70fc2);
    // ---- b3e1c (bfdca JMP): MOVE.L 7a(A6),-(A7); LEA 76(A6),A0; CLR.L (A0)+ (x 10: 76..9d); MOVE.W D0,76(A6); MOVE.W D1,78(A6); JSR 8ff4.l.
    case 0xb3e1c:
        if(!ofr11_get(c,r.a[6],0x7a,4,value) || !am_push(c,4,value))return false;r.a[0]=r.a[6]+0x76U;
        for(unsigned int i=0;i<10U;++i){if(!am_write(c,r.a[0],4,0))return false;r.a[0]+=4U;}
        if(!ofr11_put(c,r.a[6],0x76,2,r.d[0]) || !ofr11_put(c,r.a[6],0x78,2,r.d[1]))return false;return am_call(c,0x8ff4,0xb3e46);
    // BSET.B #2,95(A6); MOVEA.L (A7)+,A0; CMPA.L #0,A0; BNE.W b3e70; otherwise the TRAP #15 b3e58 (a boundary outside the unit, decision 3).
    case 0xb3e46:
        if(!ofr11_bit(c,r.a[6],0x95,2,1,old) || !am_pop(c,4,value))return false;r.a[0]=value;r.pc=value!=0U?0xb3e70:0xb3e58;return true;
    case 0xb3e70:r.pc=0xb3ea2;return true;                                                            // BRA.W b3ea2.
    // ---- b4030 (bfcd8): MOVEA.L 76(A6),A0; JMP (A0) (decision 2).
    case 0xb4030:if(!ofr11_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;return ofr11_handler(c,value);
    // ---- b403e (handler): BSET.B #4,95(A6); MOVE.L #40000,D0; MOVE.L #40000,D1; TST.W 36(A6); BGE.W b405a (N clear) / NEG.L D0.
    case 0xb403e:
        if(!ofr11_bit(c,r.a[6],0x95,4,1,old) || !ofr11_get(c,r.a[6],0x36,2,value))return false;
        r.d[0]=0x40000;r.d[1]=0x40000;r.pc=(value&0x8000U)==0U?0xb405a:0xb4058;return true;
    case 0xb4058:r.d[0]=0U-r.d[0];r.pc=0xb405a;return true;                                          // NEG.L D0.
    // TST.W 3a(A6); BGT.W b4064 (signed WORD > 0) / NEG.L D1.
    case 0xb405a:if(!ofr11_get(c,r.a[6],0x3a,2,value))return false;r.pc=ofr11_signed_word(value)>0?0xb4064:0xb4062;return true;
    case 0xb4062:r.d[1]=0U-r.d[1];r.pc=0xb4064;return true;                                          // NEG.L D1.
    // SUB.L 36(A6),D0; SUB.L 3a(A6),D1; ASR.L #3,D0; ASR.L #3,D1; ADD.L D0,36(A6); ADD.L D1,3a(A6); TST.W 8c(A6); BEQ.W b40f0.
    case 0xb4064:
        if(!ofr11_get(c,r.a[6],0x36,4,value) || !ofr11_get(c,r.a[6],0x3a,4,other))return false;
        r.d[0]=ofr11_asr(r.d[0]-value,3);r.d[1]=ofr11_asr(r.d[1]-other,3);
        if(!ofr11_add(c,0x36,r.d[0]) || !ofr11_add(c,0x3a,r.d[1]))return false;return ofr11_test(c,0x8c,2,0xb40f0,0xb4080);
    case 0xb4080:return am_call(c,0xb4aca,0xb4084);                                                   // JSR b4aca(PC) (A0 := the bounds record).
    case 0xb4084:if(!ofr11_get(c,r.a[6],0x36,2,value))return false;r.pc=(value&0x8000U)!=0U?0xb40a6:0xb408c;return true;   // TST.W 36; BMI.
    // MOVE.W (A0),D0; ADD.W 4(A0),D0; ADD.W 42(A6),D0; CMPI.W #130,D0; BLE.W b40a2 (signed) / NEG.L 36(A6).
    case 0xb408c:
        if(!ofr11_get(c,r.a[0],0,2,value) || !ofr11_get(c,r.a[0],4,2,other))return false;am_word(r.d[0],value+other);
        if(!ofr11_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],r.d[0]+value);r.pc=ofr11_signed_word(r.d[0])<=0x130?0xb40a2:0xb409e;return true;
    case 0xb409e:case 0xb40b4:if(!ofr11_neg(c,0x36))return false;r.pc=r.pc==0xb409eU?0xb40a2:0xb40b8;return true;   // NEG.L 36(A6).
    case 0xb40a2:r.pc=0xb40b8;return true;                                                            // BRA.W b40b8.
    // MOVE.W (A0),D0; ADD.W 42(A6),D0; CMPI.W #10,D0; BGE.W b40b8 (signed) / NEG.L 36(A6).
    case 0xb40a6:
        if(!ofr11_get(c,r.a[0],0,2,value))return false;am_word(r.d[0],value);if(!ofr11_get(c,r.a[6],0x42,2,value))return false;
        am_word(r.d[0],r.d[0]+value);r.pc=ofr11_signed_word(r.d[0])>=0x10?0xb40b8:0xb40b4;return true;
    case 0xb40b8:if(!ofr11_get(c,r.a[6],0x3a,2,value))return false;r.pc=(value&0x8000U)!=0U?0xb40dc:0xb40c0;return true;   // TST.W 3a; BMI.
    // MOVE.W 2(A0),D0; ADD.W 6(A0),D0; ADD.W 46(A6),D0; CMPI.W #1f0,D0; BLE.W b40d8 (signed) / NEG.L 3a(A6).
    case 0xb40c0:
        if(!ofr11_get(c,r.a[0],2,2,value) || !ofr11_get(c,r.a[0],6,2,other))return false;am_word(r.d[0],value+other);
        if(!ofr11_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],r.d[0]+value);r.pc=ofr11_signed_word(r.d[0])<=0x1f0?0xb40d8:0xb40d4;return true;
    case 0xb40d4:case 0xb40ec:if(!ofr11_neg(c,0x3a))return false;r.pc=r.pc==0xb40d4U?0xb40d8:0xb40f0;return true;   // NEG.L 3a(A6).
    case 0xb40d8:r.pc=0xb40f0;return true;                                                            // BRA.W b40f0.
    // MOVE.W 2(A0),D0; ADD.W 46(A6),D0; CMPI.W #130,D0; BGE.W b40f0 (signed) / NEG.L 3a(A6).
    case 0xb40dc:
        if(!ofr11_get(c,r.a[0],2,2,value))return false;am_word(r.d[0],value);if(!ofr11_get(c,r.a[6],0x46,2,value))return false;
        am_word(r.d[0],r.d[0]+value);r.pc=ofr11_signed_word(r.d[0])>=0x130?0xb40f0:0xb40ec;return true;
    case 0xb40f0:return am_call(c,0x43ea4,0xb40f6);                                                   // JSR 43ea4.l.
    // ---- b4104: MOVE.L 36(A6),82(A6); MOVE.L 3a(A6),86(A6); JSR 4be34.l / MOVE.W D4,92(A6); RTS.
    case 0xb4104:
        if(!ofr11_get(c,r.a[6],0x36,4,value) || !ofr11_put(c,r.a[6],0x82,4,value) || !ofr11_get(c,r.a[6],0x3a,4,value) ||
           !ofr11_put(c,r.a[6],0x86,4,value))return false;
        return am_call(c,0x4be34,0xb4116);
    case 0xb4116:if(!ofr11_put(c,r.a[6],0x92,2,r.d[4]))return false;return am_return(c);
    // ---- b411c (b41be): BCLR.B #4,95(A6); BTST.B #7,15(A6); BNE.W b41ae / JSR 1aa3a.l; ANDI.B #8,D0; BEQ.W b4198.
    case 0xb411c:if(!ofr11_bit(c,r.a[6],0x95,4,2,old))return false;return ofr11_btst(c,r.a[6],0x15,7,0xb412c,0xb41ae);
    case 0xb412c:case 0xb4198:return am_call(c,0x1aa3a,r.pc+6U);                                    // JSR 1aa3a.l.
    case 0xb4132:am_byte(r.d[0],r.d[0]&8U);r.pc=(r.d[0]&0xffU)==0U?0xb4198:0xb413a;return true;
    // MOVE.L 7e(A6),D0; ASR.L #1,D0; ADD.L D0,3a(A6); MOVEQ #0,D7; ADDI.W #800,98(A6); MOVE.B 98(A6),D7; BPL.W b4156 / NEG.B D7.
    case 0xb413a:
        if(!ofr11_get(c,r.a[6],0x7e,4,value))return false;r.d[0]=ofr11_asr(value,1);if(!ofr11_add(c,0x3a,r.d[0]))return false;r.d[7]=0;
        if(!ofr11_get(c,r.a[6],0x98,2,value) || !ofr11_put(c,r.a[6],0x98,2,value+0x800U) || !ofr11_get(c,r.a[6],0x98,1,value))return false;
        am_byte(r.d[7],value);r.pc=(value&0x80U)==0U?0xb4156:0xb4154;return true;
    case 0xb4154:am_byte(r.d[7],0U-r.d[7]);r.pc=0xb4156;return true;                                 // NEG.B D7.
    // ADD.W D7,D7; MOVEM.L 36(A6),D0-D1; ASR.L #8 (D0, D1); ASR.W #1 (D0, D1); NEG.W (D0, D1); LEA 4411e.l,A0; LEA 4419e.l,A1;
    // MULS.W (A1,D7.W),D0; MULS.W (A0,D7.W),D1; ADD.L D1,D0; ASR.L #8,D0; MOVE.W D0,D1; MULS.W (A1,D7.W),D0; MULS.W (A0,D7.W),D1;
    // ADD.L D0,36(A6); ADD.L D1,3a(A6); BRA.W b4104 (the ROM WORD tables read through the live bus, the index D7.W sign-extended).
    case 0xb4156:{
        am_word(r.d[7],r.d[7]+r.d[7]);
        if(!ofr11_get(c,r.a[6],0x36,4,value) || !ofr11_get(c,r.a[6],0x3a,4,other))return false;
        r.d[0]=ofr11_asr(value,8);r.d[1]=ofr11_asr(other,8);am_word(r.d[0],ofr11_asr_word(r.d[0]));am_word(r.d[1],ofr11_asr_word(r.d[1]));
        am_word(r.d[0],0U-r.d[0]);am_word(r.d[1],0U-r.d[1]);r.a[0]=0x4411e;r.a[1]=0x4419e;
        std::uint32_t first=0;std::uint32_t second=0;
        if(!am_read(c,am_index(r.a[1],r.d[7]),2,first) || !am_read(c,am_index(r.a[0],r.d[7]),2,second))return false;
        r.d[0]=ofr11_muls(r.d[0],first);r.d[1]=ofr11_muls(r.d[1],second);r.d[0]=ofr11_asr(r.d[0]+r.d[1],8);am_word(r.d[1],r.d[0]);
        if(!am_read(c,am_index(r.a[1],r.d[7]),2,first) || !am_read(c,am_index(r.a[0],r.d[7]),2,second))return false;
        r.d[0]=ofr11_muls(r.d[0],first);r.d[1]=ofr11_muls(r.d[1],second);
        if(!ofr11_add(c,0x36,r.d[0]) || !ofr11_add(c,0x3a,r.d[1]))return false;r.pc=0xb4104;return true;}
    case 0xb419e:am_byte(r.d[0],r.d[0]&0x80U);r.pc=(r.d[0]&0xffU)!=0U?0xb403e:0xb41a6;return true;   // ANDI.B #80,D0; BNE.W b403e.
    // MOVE.L 7e(A6),D0; ADD.L D0,3a(A6) / BRA.W b4104.
    case 0xb41a6:if(!ofr11_get(c,r.a[6],0x7e,4,value))return false;r.d[0]=value;if(!ofr11_add(c,0x3a,r.d[0]))return false;r.pc=0xb41ae;return true;
    case 0xb41ae:r.pc=0xb4104;return true;
    // ---- b41be (handler): JSR b411c(PC); BTST.B #5,15(A6); BEQ.W b427e / MOVE.B 92(A6),D4; MOVE.B 97(A6),D0; JSR b42b0(PC).
    case 0xb41be:return am_call(c,0xb411c,0xb41c2);
    case 0xb41c2:return ofr11_btst(c,r.a[6],0x15,5,0xb427e,0xb41cc);
    case 0xb41cc:
        if(!ofr11_get(c,r.a[6],0x92,1,value))return false;am_byte(r.d[4],value);if(!ofr11_get(c,r.a[6],0x97,1,value))return false;am_byte(r.d[0],value);
        return am_call(c,0xb42b0,0xb41d8);
    // MOVEM.L 82(A6),D0-D1; MOVE.W 8e(A6),D7; BNE.W b41f2 (the later-unit PC) / CLR.L 36(A6); CLR.L 3a(A6); BRA.W b427e.
    case 0xb41d8:
        if(!ofr11_get(c,r.a[6],0x82,4,value) || !ofr11_get(c,r.a[6],0x86,4,other))return false;r.d[0]=value;r.d[1]=other;
        if(!ofr11_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[7],value);r.pc=(value&0xffffU)!=0U?0xb41f2:0xb41e6;return true;
    case 0xb41e6:if(!ofr11_put(c,r.a[6],0x36,4,0) || !ofr11_put(c,r.a[6],0x3a,4,0))return false;r.pc=0xb427e;return true;
    case 0xb427e:return ofr11_btst(c,r.a[6],0x15,7,0xb4292,0xb4288);                                  // BTST.B #7,15(A6); BEQ.W b4292.
    // MOVE.L 36(A6),D0; ASR.L #3,D0; SUB.L D0,36(A6).
    case 0xb4288:if(!ofr11_get(c,r.a[6],0x36,4,value))return false;r.d[0]=ofr11_asr(value,3);if(!ofr11_put(c,r.a[6],0x36,4,value-r.d[0]))return false;
        r.pc=0xb4292;return true;
    // ---- b42b0 (b41cc): ANDI.W #ff,D0; JMP b42b8(PC,D0.W) (decision 2: the BRA.W table b42b8..b42c8; the ROM writer of BYTE 97(A6) -- b3f68 from the
    // kind records b3484 -- produces 0 / 4 / c only; the routing decides the entry: b42b8 is the executed FR11 block, b42bc / b42c4 are stops).
    case 0xb42b0:
        am_word(r.d[0],r.d[0]&0xffU);value=r.d[0]&0xffffU;
        if(value!=0U && value!=4U && value!=0xcU)return am_error(c,"unsupported animation objects fr11 jump target");r.pc=0xb42b8+value;return true;
    case 0xb42b8:r.pc=0xb42c8;return true;                                                            // BRA.W b42c8 (table entry 0).
    // ---- b4abc / b4ac2: MOVE.W 8c(A6),D1; RTS / BSET.B #3,95(A6); RTS.
    case 0xb4abc:if(!ofr11_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[1],value);return am_return(c);
    case 0xb4ac2:if(!ofr11_bit(c,r.a[6],0x95,3,1,old))return false;return am_return(c);
    // ---- b67b2 (U18 b67a8 install): JSR 496c2.l; the anims by WORD 8e (b7f5c), the offsets, (A6) := b686e.
    case 0xb67b2:return am_call(c,0x496c2,0xb67b8);
    case 0xb67b8:return ofr11_kind(c,0x8e,0xb67c4,0xb6800);
    case 0xb67c4:return ofr11_table_anim(c,0x1b3,0x2001a8,0xb7f5c,0xb67fc);
    case 0xb6800:return ofr11_table_anim(c,0x1bb,0x2001ac,0xb7f5c,0xb6838);
    case 0xb67fc:r.pc=0xb6838;return true;                                                            // BRA.W b6838.
    case 0xb6838:return ofr11_offsets_call(c,0xfffffff4U,0x14,0xb6850);
    case 0xb6850:return ofr11_offsets_call(c,0xfffffff0U,0x1c,0xb6868);
    case 0xb6868:return ofr11_install(c,0xb686e,0xb686e);                                             // MOVE.L #b686e,(A6) (next PC).
    case 0xb686e:return am_call(c,0x4be34,0xb6874);                                                   // JSR 4be34.l.
    case 0xb6874:case 0xb6d6e:case 0xb6e54:case 0xb77fa:case 0xc5476:case 0xc5608:return am_call(c,0x49fc6,r.pc+6U);   // JSR 49fc6.l.
    case 0xb687a:return ofr11_carry(c,0xb68b6,0xb687e);                                               // BCC.W b68b6 (C of 49fc6).
    case 0xb687e:r.a[0]=0xb774a;am_word(r.d[0],0x14);return am_call(c,0x28ae,0xb688e);              // MOVEA.L #b774a,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0xb688e:return ofr11_carry(c,0xb68a0,0xb6892);                                               // BCC.W b68a0 (C of 28ae).
    case 0xb6892:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0xb689c);           // CLR.W D0; CLR.W D1; JSR 4970a.l.
    case 0xb689c:r.carry=AnimationCarrySet;r.pc=0xb68a0;return true;                                 // ORI.B #1,CCR (the next MOVE clears it).
    // MOVE.W 8e(A6),8e(A0); MOVE.L #b68ba,(A6) (written only); CMPI.W #1,8e(A6); BNE.W b68b6 (both outcomes b68b6).
    case 0xb68a0:
        if(!ofr11_get(c,r.a[6],0x8e,2,value) || !ofr11_put(c,r.a[0],0x8e,2,value) || !ofr11_put(c,r.a[6],0,4,0xb68ba) ||
           !ofr11_get(c,r.a[6],0x8e,2,value))return false;
        r.pc=0xb68b6;return true;
    case 0xb68b6:case 0xb6d7e:case 0xb6ec4:r.pc=0xb76d2;return true;                               // BRA.W b76d2.
    // ---- b6ca2 / b6d82 (FR10 b6c8a / b6c98 installs): MOVE.B 9d(A6),D0; JSR 49392.l.
    case 0xb6ca2:case 0xb6d82:if(!ofr11_get(c,r.a[6],0x9d,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x49392,r.pc+0xaU);
    case 0xb6cac:return ofr11_carry(c,0xb6ccc,0xb6cb0);                                               // BCC.W b6ccc (C of 49392).
    // MOVE.W 42(A6),D0; CMP.W 42(A0),D0; BLE.W b6cc6 (signed) / BCLR.B #0,15(A6); BRA.W b6ccc.
    case 0xb6cb0:
        if(!ofr11_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value);if(!ofr11_get(c,r.a[0],0x42,2,other))return false;
        r.pc=ofr11_signed_word(value)<=ofr11_signed_word(other)?0xb6cc6:0xb6cbc;return true;
    case 0xb6cbc:if(!ofr11_bit(c,r.a[6],0x15,0,2,old))return false;r.pc=0xb6ccc;return true;
    case 0xb6cc6:if(!ofr11_bit(c,r.a[6],0x15,0,1,old))return false;r.pc=0xb6ccc;return true;      // BSET.B #0,15(A6).
    case 0xb6ccc:return ofr11_kind(c,0x8e,0xb6cd8,0xb6d14);
    case 0xb6cd8:return ofr11_table_anim(c,0x1b3,0x2001a8,0xb7f7c,0xb6d10);
    case 0xb6d14:return ofr11_table_anim(c,0x1bb,0x2001ac,0xb7f7c,0xb6d4c);
    case 0xb6d10:r.pc=0xb6d4c;return true;                                                            // BRA.W b6d4c.
    // MOVE.L #fffffffc,96(A6); MOVE.L #1a,98(A6); CLR.L 36(A6); CLR.L 64(A6); MOVE.L #b6d6a,(A6) (next PC).
    case 0xb6d4c:
        if(!ofr11_offsets(c,0xfffffffcU,0x1a) || !ofr11_put(c,r.a[6],0x36,4,0) || !ofr11_put(c,r.a[6],0x64,4,0))return false;
        return ofr11_install(c,0xb6d6a,0xb6d6a);
    case 0xb6d6a:case 0xb6e50:return am_call(c,0xb7cfa,r.pc+4U);                                    // BSR.W b7cfa.
    case 0xb6d74:return ofr11_carry(c,0xb6d7e,0xb6d78);                                               // BCC.W b6d7e (C of 49fc6).
    case 0xb6d78:return ofr11_install(c,0xb6d82,0xb6d7e);                                             // MOVE.L #b6d82,(A6) (written only).
    case 0xb6d8c:return ofr11_carry(c,0xb6dac,0xb6d90);                                               // BCC.W b6dac (C of 49392); else the later-unit b6d90.
    case 0xb6dac:return ofr11_kind(c,0x8e,0xb6db8,0xb6df4);
    case 0xb6db8:return ofr11_table_anim(c,0x1b3,0x2001a8,0xb7fc4,0xb6df0);
    case 0xb6df4:return ofr11_table_anim(c,0x1bb,0x2001ac,0xb7fc4,0xb6e2c);
    case 0xb6df0:r.pc=0xb6e2c;return true;                                                            // BRA.W b6e2c.
    // MOVE.L #fffffffe,96(A6); MOVE.L #18,98(A6); CLR.L 64(A6); CLR.L 36(A6); MOVE.B #8,9c(A6); MOVE.L #b6e50,(A6) (next PC).
    case 0xb6e2c:
        if(!ofr11_offsets(c,0xfffffffeU,0x18) || !ofr11_put(c,r.a[6],0x64,4,0) || !ofr11_put(c,r.a[6],0x36,4,0) || !ofr11_put(c,r.a[6],0x9c,1,8))return false;
        return ofr11_install(c,0xb6e50,0xb6e50);
    case 0xb6e5a:return ofr11_carry(c,0xb6e8c,0xb6e5e);                                               // BCC.W b6e8c (C of 49fc6); else the later-unit b6e5e.
    case 0xb6e8c:return ofr11_test(c,0x9c,1,0xb6ec4,0xb6e94);                                         // TST.B 9c(A6); BEQ.W b6ec4.
    // SUBQ.B #1,9c(A6); BNE.W b6ec4 (the new BYTE).
    case 0xb6e94:
        if(!ofr11_get(c,r.a[6],0x9c,1,value) || !ofr11_put(c,r.a[6],0x9c,1,value-1U))return false;r.pc=((value-1U)&0xffU)!=0U?0xb6ec4:0xb6e9c;return true;
    case 0xb6e9c:return ofr11_offsets_call(c,0xfffffff8U,0x20,0xb6eb4);
    case 0xb6eb4:if(!ofr11_offsets(c,0xfffffffeU,0x18))return false;r.pc=0xb6ec4;return true;
    // ---- b774a (the 28ae child of b687e): MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); MOVE.W 8e(A6),D0; LEA b7f14(PC),A0; ADD.W D0,D0;
    // MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0xb774a:
        if(!ofr11_put(c,r.a[6],0x68,2,0x1001) || !ofr11_put(c,r.a[6],0x1e,2,0x1001) || !ofr11_get(c,r.a[6],0x8e,2,value))return false;
        am_word(r.d[0],value);r.a[0]=0xb7f14;am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;
        am_word(r.d[0],value);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xb776e);
    case 0xb776e:return ofr11_kind(c,0x8e,0xb777a,0xb77b6);
    case 0xb777a:return ofr11_table_anim(c,0x1b3,0x2001a8,0xb7f64,0xb77b2);
    case 0xb77b6:return ofr11_table_anim(c,0x1bb,0x2001ac,0xb7f64,0xb77ee);
    case 0xb77b2:r.pc=0xb77ee;return true;                                                            // BRA.W b77ee.
    case 0xb77ee:return ofr11_install(c,0xb77f4,0xb77f4);                                             // MOVE.L #b77f4,(A6) (next PC).
    case 0xb77f4:return am_call(c,0x43e34,0xb77fa);                                                   // JSR 43e34.l.
    case 0xb7800:return ofr11_carry(c,0xb780a,0xb7804);                                               // BCC.W b780a (C of 49fc6).
    case 0xb7804:return ofr11_install(c,0xb7742,0xb780a);                                             // MOVE.L #b7742,(A6) (written only).
    // ---- b7d4a (script callback, interpreter table 4a500 + 1cc): LEA 26(A6),A0; JSR b7e06(PC) / TST.W 7c(A6); BLE.W b7dd4 (signed).
    case 0xb7d4a:r.a[0]=r.a[6]+0x26U;return am_call(c,0xb7e06,0xb7d52);
    case 0xb7d52:if(!ofr11_get(c,r.a[6],0x7c,2,value))return false;r.pc=ofr11_signed_word(value)<=0?0xb7dd4:0xb7d5a;return true;
    // MOVE.W #0,-(A7) (x 3); MOVE.W 7e(A6),-(A7); MOVE.W 7c(A6),-(A7); MOVE.W #0,-(A7) (x 2); MOVEA.L #b3dbc,A0; MOVE.W #14,D0;
    // MOVEA.L #100bf4,A1; JSR 2986.l (the 2986 child b3dbc).
    case 0xb7d5a:
        if(!am_push(c,2,0) || !am_push(c,2,0) || !am_push(c,2,0) || !ofr11_get(c,r.a[6],0x7e,2,value) || !am_push(c,2,value) ||
           !ofr11_get(c,r.a[6],0x7c,2,value) || !am_push(c,2,value) || !am_push(c,2,0) || !am_push(c,2,0))return false;
        r.a[0]=0xb3dbc;am_word(r.d[0],0x14);r.a[1]=0x100bf4;return am_call(c,0x2986,0xb7d8c);
    // MOVEM.W (A7)+,D0-D6 (each WORD sign-extended to the LONG, the lowest address to D0; flags unchanged); BCC.W b7db2 (C of 2986).
    case 0xb7d8c:
        if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr11 caller requires known carry");
        for(unsigned int i=0;i<7U;++i){if(!am_pop(c,2,value))return false;r.d[i]=am_extend_word(value);}
        r.pc=c.s.carry==AnimationCarryClear?0xb7db2:0xb7d94;return true;
    // MOVE.W D2,76(A0); MOVE.W D3,78(A0); MOVE.W D4,7a(A0); MOVE.W D5,7c(A0); MOVE.W D6,7e(A0); JSR 49214.l.
    case 0xb7d94:
        if(!ofr11_put(c,r.a[0],0x76,2,r.d[2]) || !ofr11_put(c,r.a[0],0x78,2,r.d[3]) || !ofr11_put(c,r.a[0],0x7a,2,r.d[4]) ||
           !ofr11_put(c,r.a[0],0x7c,2,r.d[5]) || !ofr11_put(c,r.a[0],0x7e,2,r.d[6]))return false;
        return am_call(c,0x49214,0xb7dae);
    case 0xb7dae:r.carry=AnimationCarrySet;r.pc=0xb7db2;return true;                                 // ORI.B #1,CCR (the next MOVEQ clears it).
    // MOVEQ #0,D0; MOVE.W #10,D2; MOVE.W #8,D3; BTST.B #0,15(A6); BNE.W b7dc8 / NEG.W D2.
    case 0xb7db2:r.d[0]=0;am_word(r.d[2],0x10);am_word(r.d[3],8);return ofr11_btst(c,r.a[6],0x15,0,0xb7dc6,0xb7dc8);
    case 0xb7dc6:am_word(r.d[2],0U-r.d[2]);r.pc=0xb7dc8;return true;                                 // NEG.W D2.
    case 0xb7dc8:return am_call(c,0x4c2fa,0xb7dce);                                                   // JSR 4c2fa.l.
    case 0xb7dce:if(!ofr11_put(c,r.a[6],0x7c,2,0))return false;r.pc=0xb7dd4;return true;           // MOVE.W #0,7c(A6).
    // ---- bfb5a (kind handler, kind record b3484 + a): MOVE.W #0,D0; BRA.W bfc2a.
    case 0xbfb5a:am_word(r.d[0],0);r.pc=0xbfc2a;return true;
    // MOVE.W D0,a2(A6); MULU.W #8,D0; LEA bfdee(PC),A0; LEA (A0,D0.W),A0; MOVE.L A0,9e(A6); MOVE.L (A0),D0; LEA 26(A6),A0; MOVE.W #1e3,20(A6);
    // MOVE.L 2001c0.l,22(A6); LEA 26(A6),A0; MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 2001c0.l,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0;
    // JSR 49f8c.l (MULU.W: the unsigned low WORD x 8, the 32-bit product; the record index D0.W sign-extended).
    case 0xbfc2a:
        if(!ofr11_put(c,r.a[6],0xa2,2,r.d[0]))return false;r.d[0]=(r.d[0]&0xffffU)*8U;r.a[0]=am_index(0xbfdee,r.d[0]);
        if(!ofr11_put(c,r.a[6],0x9e,4,r.a[0]) || !am_read(c,r.a[0],4,value))return false;r.d[0]=value;r.a[0]=r.a[6]+0x26U;
        if(!ofr11_put(c,r.a[6],0x20,2,0x1e3) || !am_read(c,0x2001c0,4,value) || !ofr11_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]+r.d[1]);am_word(r.d[1],r.d[1]+r.d[1]);
        if(!am_read(c,0x2001c0,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;
        am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xbfc70);
    // MOVEA.L 9e(A6),A0; MOVE.W 4(A0) / 6(A0),D0; MOVEQ #0,D1; JSR 8ebe.l.
    case 0xbfc70:case 0xbfc80:
        if(!ofr11_get(c,r.a[6],0x9e,4,value))return false;r.a[0]=value;if(!ofr11_get(c,r.a[0],r.pc==0xbfc70U?4U:6U,2,value))return false;
        am_word(r.d[0],value);r.d[1]=0;return am_call(c,0x8ebe,r.pc+0x10U);
    // MOVE.B 19(A6),14(A6); TST.B a8(A6); BEQ.W bfca4 / JSR b4ac2.l.
    case 0xbfc90:if(!ofr11_get(c,r.a[6],0x19,1,value) || !ofr11_put(c,r.a[6],0x14,1,value))return false;return ofr11_test(c,0xa8,1,0xbfca4,0xbfc9e);
    case 0xbfc9e:return am_call(c,0xb4ac2,0xbfca4);
    case 0xbfca4:return ofr11_install(c,0xbfcaa,0xbfcaa);                                             // MOVE.L #bfcaa,(A6) (next PC).
    case 0xbfcaa:return ofr11_test(c,0xa8,1,0xbfcd8,0xbfcb2);                                         // TST.B a8(A6); BEQ.W bfcd8.
    // ADDQ.W #8,a6(A6); MOVE.W a6(A6),D0; ANDI.W #7f,D0; ADD.W D0,D0; LEA 4411e.l,A0; MOVE.W (A0,D0.W),D0; BEQ.W bfcd0 / SUBQ.W #1,D0.
    case 0xbfcb2:
        if(!ofr11_get(c,r.a[6],0xa6,2,value) || !ofr11_put(c,r.a[6],0xa6,2,value+8U) || !ofr11_get(c,r.a[6],0xa6,2,value))return false;
        am_word(r.d[0],value&0x7fU);am_word(r.d[0],r.d[0]+r.d[0]);r.a[0]=0x4411e;if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;
        am_word(r.d[0],value);r.pc=(value&0xffffU)==0U?0xbfcd0:0xbfcce;return true;
    case 0xbfcce:am_word(r.d[0],r.d[0]-1U);r.pc=0xbfcd0;return true;                                // SUBQ.W #1,D0.
    // MOVE.B D0,12(A6); BEQ.W bfdb2 (the Z of the BYTE D0.B).
    case 0xbfcd0:if(!ofr11_put(c,r.a[6],0x12,1,r.d[0]))return false;r.pc=(r.d[0]&0xffU)==0U?0xbfdb2:0xbfcd8;return true;
    case 0xbfcd8:return am_call(c,0xb4030,0xbfcde);                                                   // JSR b4030.l.
    case 0xbfcde:return am_call(c,0xb4958,0xbfce4);                                                   // JSR b4958.l.
    case 0xbfce4:return am_call(c,0xb4ab0,0xbfcea);                                                   // JSR b4ab0.l (D0.B := BYTE 96).
    case 0xbfcea:r.pc=(r.d[0]&4U)!=0U?0xbfcfa:0xbfcf2;return true;                                  // BTST #2,D0; BNE.W bfcfa (the later-unit PC).
    case 0xbfcf2:return am_call(c,0xb4334,0xbfcf8);                                                   // JSR b4334.l.
    // ST.B a8(A6); MOVEQ #f,D0; JSR 49a84.l / ADD.W D0,D0; MOVE.W bfdd0(PC,D0.W),D0; JSR b4abc.l / JMP b3e1c.l.
    case 0xbfdb2:if(!ofr11_put(c,r.a[6],0xa8,1,0xff))return false;r.d[0]=0xf;return am_call(c,0x49a84,0xbfdbe);
    case 0xbfdbe:
        am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(0xbfdd0,r.d[0]),2,value))return false;am_word(r.d[0],value);return am_call(c,0xb4abc,0xbfdca);
    case 0xbfdca:r.pc=0xb3e1c;return true;
    // ---- c5432 (FR3 c541a install): MOVEA.L #c5592,A0; MOVE.W #a,D0; JSR 28ae.l (the 28ae child c5592; its C is not read); the bank anim ba /
    // 200080 / 144; (A6) := c5470.
    case 0xc5432:r.a[0]=0xc5592;am_word(r.d[0],0xa);return am_call(c,0x28ae,0xc5442);
    case 0xc5442:return ofr11_bank_anim(c,0xba,0x200080,0x144,0xc546a);
    case 0xc546a:return ofr11_install(c,0xc5470,0xc5470);                                             // MOVE.L #c5470,(A6) (next PC).
    case 0xc5470:return am_call(c,0x4be06,0xc5476);                                                   // JSR 4be06.l.
    case 0xc547c:return ofr11_carry(c,0xc5486,0xc5480);                                               // BCC.W c5486 (C of 49fc6).
    case 0xc5480:return ofr11_install(c,0xc53be,0xc5486);                                             // MOVE.L #c53be,(A6) (written only).
    case 0xc5486:if(!ofr11_get(c,r.a[6],0x54,2,value) || !ofr11_put(c,r.a[6],0x80,2,value))return false;return am_call(c,0x4b54e,0xc5492);
    case 0xc5492:return ofr11_carry(c,0xc551e,0xc5496);                                               // BCC.W c551e (C of 4b54e).
    // MOVE.B 5e(A6),D0; CLR.B 5e(A6); CMPI.B #1b,D0; BCC.W c5540 (unsigned BYTE >= 1b).
    case 0xc5496:
        if(!ofr11_get(c,r.a[6],0x5e,1,value) || !ofr11_put(c,r.a[6],0x5e,1,0))return false;am_byte(r.d[0],value);
        r.pc=(value&0xffU)>=0x1bU?0xc5540:0xc54a6;return true;
    // ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; JMP c54b2(PC,D0.W) (decision 2: the 27-entry BRA.W table c54b2..c551e; the guard of c5496 keeps the index
    // 0..1a; the routing decides the entry: c54ca is the executed FR11 block, c54ba / c54d6 FR13 stops, the others unrouted; a larger index is a checked
    // error).
    case 0xc54a6:
        am_word(r.d[0],r.d[0]&0xffU);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);value=r.d[0]&0xffffU;
        if(value>0x68U)return am_error(c,"unsupported animation objects fr11 jump target");r.pc=0xc54b2+value;return true;
    case 0xc54ca:r.pc=0xc5540;return true;                                                            // BRA.W c5540 (table entry 6).
    // MOVE.W 80(A6),54(A6); CLR.B 5e(A6); RTS.
    case 0xc5540:if(!ofr11_get(c,r.a[6],0x80,2,value) || !ofr11_put(c,r.a[6],0x54,2,value) || !ofr11_put(c,r.a[6],0x5e,1,0))return false;return am_return(c);
    // ---- c5592 (the 28ae child of c5432): JSR 49a58.l / ANDI.W #1f,D0; SUBI.W #ffe1,D0; MOVEQ #0,D1; JSR 49290.l / JSR 491c4.l / MOVE.W #24,D0;
    // MOVE.W #8,D1; MOVE.B #0,D2; JSR c6a96.l / MOVE.W #e0ed,68(A6); MOVE.W #e0ed,1e(A6); the bank anim e2 / 200094 / 20 / MOVE.L #40000,3a(A6);
    // (A6) := c5602.
    case 0xc5592:return am_call(c,0x49a58,0xc5598);
    case 0xc5598:am_word(r.d[0],r.d[0]&0x1fU);am_word(r.d[0],r.d[0]-0xffe1U);r.d[1]=0;return am_call(c,0x49290,0xc55a8);
    case 0xc55a8:return am_call(c,0x491c4,0xc55ae);
    case 0xc55ae:am_word(r.d[0],0x24);am_word(r.d[1],8);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xc55c0);
    case 0xc55c0:
        if(!ofr11_put(c,r.a[6],0x68,2,0xe0ed) || !ofr11_put(c,r.a[6],0x1e,2,0xe0ed))return false;return ofr11_bank_anim(c,0xe2,0x200094,0x20,0xc55f4);
    case 0xc55f4:if(!ofr11_put(c,r.a[6],0x3a,4,0x40000))return false;return ofr11_install(c,0xc5602,0xc5602);
    case 0xc5602:return am_call(c,0x4be2c,0xc5608);                                                   // JSR 4be2c.l.
    case 0xc560e:return ofr11_carry(c,0xc5618,0xc5612);                                               // BCC.W c5618 (C of 49fc6); else the later-unit c5612.
    // ---- the FR4 BRA.W table entries (cc82a): cc836 (entry 2) -> cdc1c, cc842 (entry 5) -> cd7c6.
    case 0xcc836:r.pc=0xcdc1c;return true;
    case 0xcc842:r.pc=0xcd7c6;return true;
    // ---- cd7e2 (FR10 cd7cc BPL fall-through): NEG.L D0 -> FR10 cd7e4.
    case 0xcd7e2:r.d[0]=0U-r.d[0];r.pc=0xcd7e4;return true;
    // ---- cd92e (FR10 cd8ee BNE): MOVE.L #0,7e(A6); MOVE.W #100,2c(A6) -> FR10 cd93c.
    case 0xcd92e:if(!ofr11_put(c,r.a[6],0x7e,4,0) || !ofr11_put(c,r.a[6],0x2c,2,0x100))return false;r.pc=0xcd93c;return true;
    // ---- cd96c (FR10 cd95a BPL fall-through): the anim by WORD 8c(A6) 0..4 / other; (A6) := cdafc; RTS.
    case 0xcd96c:return ofr11_kind(c,0x8c,0xcd974,0xcd98e);
    case 0xcd974:return ofr11_anim(c,0xce148,0xcd98a);
    case 0xcd98e:ofr11_select(r,1,0xcd996,0xcd9b0);return true;
    case 0xcd996:return ofr11_anim(c,0xce99a,0xcd9ac);
    case 0xcd9b0:ofr11_select(r,2,0xcd9b8,0xcd9d2);return true;
    case 0xcd9b8:return ofr11_anim(c,0xcfa46,0xcd9ce);
    case 0xcd9d2:ofr11_select(r,3,0xcd9da,0xcd9f4);return true;
    case 0xcd9da:return ofr11_anim(c,0xcf2f2,0xcd9f0);
    case 0xcd9f4:ofr11_select(r,4,0xcd9fc,0xcda16);return true;
    case 0xcd9fc:return ofr11_anim(c,0xd02a2,0xcda12);
    case 0xcda16:return ofr11_anim(c,0xd09ba,0xcda2c);
    case 0xcd98a:case 0xcd9ac:case 0xcd9ce:case 0xcd9f0:case 0xcda12:r.pc=0xcda2c;return true;   // BRA.W cda2c.
    case 0xcda2c:if(!ofr11_put(c,r.a[6],0,4,0xcdafc))return false;return am_return(c);            // MOVE.L #cdafc,(A6) (written); RTS.
    default:return am_error(c,"unsupported animation objects fr11 PC");
    }
}
}
