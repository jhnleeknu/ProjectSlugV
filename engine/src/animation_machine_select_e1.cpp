#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool se1_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool se1_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// The signed value of the low WORD / BYTE (BLT / BGT / BGE after CMPI / CMP compare the signed operands; no C++ signed overflow).
std::int32_t se1_signed_word(std::uint32_t value) {
    const std::uint32_t w=value&0xffffU;
    return (w&0x8000U)!=0U?static_cast<std::int32_t>(w)-0x10000:static_cast<std::int32_t>(w);
}
std::int32_t se1_signed_byte(std::uint32_t value) {
    const std::uint32_t b=value&0xffU;
    return (b&0x80U)!=0U?static_cast<std::int32_t>(b)-0x100:static_cast<std::int32_t>(b);
}
// ASR.W #4,Dn: the low WORD shifted right by 4 with its sign bit copied in (Dn bits 16..31 kept).
void se1_asr4(std::uint32_t& r) {
    const std::uint32_t w=r&0xffffU;am_word(r,(w&0x8000U)!=0U?((w>>4)|0xf000U):(w>>4));
}
// MOVE.W #v,68(A6); MOVE.W #v,1e(A6); JSR 8ff4.l.
bool se1_shape(AnimationMachineContext& c,std::uint32_t value,std::uint32_t return_pc) {
    if(!se1_put(c,c.s.a[6],0x68,2,value) || !se1_put(c,c.s.a[6],0x1e,2,value))return false;return am_call(c,0x8ff4,return_pc);
}
// MOVE.W #id,D0; MOVE.B #k,D1; JSR 8ebe.l.
bool se1_light(AnimationMachineContext& c,std::uint32_t id,std::uint32_t k,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);am_byte(c.s.d[1],k);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W 7a(A6),D0; LSL.W #2,D0 (or ADD.W D0,D0 twice when shift = 2, once when shift = 1; D0 bits 16..31 kept).
bool se1_index(AnimationMachineContext& c,unsigned int shift) {
    std::uint32_t value=0;if(!se1_get(c,c.s.a[6],0x7a,2,value))return false;am_word(c.s.d[0],value<<shift);return true;
}
// MOVE.L 2000c0.l,22(A6) (the bank-window LONG, live bus).
bool se1_window(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!am_read(c,0x2000c0,4,value))return false;return se1_put(c,c.s.a[6],0x22,4,value);
}
// MOVEA.L (A0,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l (the animation interpreter with the script pointer A1).
bool se1_script_a0(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;
    if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),4,r.a[1]))return false;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// LEA table,A0; MOVE.W 7a(A6),D0; LSL.W #2,D0; MOVEA.L (A0,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
bool se1_script(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    c.s.a[0]=table;if(!se1_index(c,2))return false;return se1_script_a0(c,return_pc);
}
// MOVE.W 2(A0,D0.W),D1; MOVE.W (A0,D0.W),D0; MOVEA.L #0,A1; JSR 43e04.l (the WORD pair of the table entry; A0 and D0.W already set).
bool se1_place_a0(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;const std::uint32_t at=am_index(r.a[0],r.d[0]&0xffffU);
    if(!am_read(c,at+2U,2,value))return false;am_word(r.d[1],value);
    if(!am_read(c,at,2,value))return false;am_word(r.d[0],value);r.a[1]=0;return am_call(c,0x43e04,return_pc);
}
// LEA table(PC),A0; MOVE.W 7a(A6),D0; LSL.W #2,D0; then se1_place_a0.
bool se1_place(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    c.s.a[0]=table;if(!se1_index(c,2))return false;return se1_place_a0(c,return_pc);
}
// MOVE.L #v,(A6) and the next PC (v itself when the install falls through into v).
bool se1_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!se1_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #v,(A6); RTS.
bool se1_install_return(AnimationMachineContext& c,std::uint32_t value) {
    if(!se1_put(c,c.s.a[6],0,4,value))return false;return am_return(c);
}
// TST.W / TST.B d(A6); BEQ / BNE: zero_pc when the field is 0, else other_pc.
bool se1_zero(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!se1_get(c,c.s.a[6],displacement,size,value))return false;c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// SUBQ.W #1,d(A6); BNE.W: zero_pc when the new WORD is 0, else other_pc.
bool se1_count(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!se1_get(c,c.s.a[6],displacement,2,value) || !se1_put(c,c.s.a[6],displacement,2,value-1U))return false;
    c.s.pc=((value-1U)&0xffffU)==0U?zero_pc:other_pc;return true;
}
// MOVE.B #v,d(A6) and the next PC.
bool se1_mark(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,std::uint32_t next_pc) {
    if(!se1_put(c,c.s.a[6],displacement,1,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.W #k,D0; JSR 4e186.l (the player slot query: D1 / D2 out).
bool se1_query(AnimationMachineContext& c,std::uint32_t k,std::uint32_t return_pc) {
    am_word(c.s.d[0],k);return am_call(c,0x4e186,return_pc);
}
// CMP.W 7a(A6),D2; BNE.W other_pc (fall through to equal_pc).
bool se1_same_slot(AnimationMachineContext& c,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!se1_get(c,c.s.a[6],0x7a,2,value))return false;
    c.s.pc=(c.s.d[2]&0xffffU)==value?equal_pc:other_pc;return true;
}
// MOVE.W 78(A6),D0; LEA e84c8.l,A1; JSR 3918.l (the text of the slot with A0 already set).
bool se1_text(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!se1_get(c,c.s.a[6],0x78,2,value))return false;am_word(c.s.d[0],value);c.s.a[1]=0xe84c8;
    return am_call(c,0x3918,return_pc);
}
// Z of the TST.B -7699(A5) that ended ca50 (RTS ca54), recomputed from that BYTE (contract decision 3, the player C1 rule): RTS reads only the stack
// and A5 is unchanged.  The address must be work RAM (100000..1fffff, 24-bit): a second read of a device would not be the original.
bool se1_flag_ca50(AnimationMachineContext& c,bool& zero) {
    const std::uint32_t address=am_index(c.s.a[5],0x8967U);
    if((address&0xffffffU)<0x100000U || (address&0xffffffU)>=0x200000U)return am_error(c,"unsupported animation select e1 flag source");
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    zero=value==0U;return true;
}
// Z of the TST.B (A0) that ended 4a974 (4a9b0 / 4a9c6 + RTS), recomputed from BYTE (A0) (contract decision 3, the controller C1 / C2 rule): A0 must be
// one of the four work RAM BYTEs 4a974 points at (10fdb0 / 10fdb1 = 7db0(A5) + slot with A5 = 108000, 100004 / 100005).
bool se1_flag_credit(AnimationMachineContext& c,bool& zero) {
    const std::uint32_t a0=c.s.a[0];
    if(a0!=0x10fdb0U && a0!=0x10fdb1U && a0!=0x100004U && a0!=0x100005U)return am_error(c,"unsupported animation select e1 flag source");
    std::uint32_t value=0;if(!am_read(c,a0,1,value))return false;
    zero=value==0U;return true;
}
// LEA table(PC),A0; MOVE.W 7a(A6),D0; LSL.W #2,D0; MOVEA.L (A0,D0.W),A0; MOVEQ #0,D0; MOVE.B 19(A6),D0; MOVE.W (A0),D1 (df272, the first of the
// three digit marks).
bool se1_digits(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=0xde598;if(!se1_index(c,2))return false;
    if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),4,r.a[0]))return false;
    r.d[0]=0;if(!se1_get(c,r.a[6],0x19,1,value))return false;am_byte(r.d[0],value);
    if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);return true;
}
// MOVEM.L D2/A0,-(A7) (A0 at the higher LONG, D2 at the lower) / MOVEM.L (A7)+,D2/A0.
bool se1_save(AnimationMachineContext& c) {return am_push(c,4,c.s.a[0]) && am_push(c,4,c.s.d[2]);}
bool se1_restore(AnimationMachineContext& c) {return am_pop(c,4,c.s.d[2]) && am_pop(c,4,c.s.a[0]);}
// MOVEM.L (A7)+,D2/A0; MOVEQ #0,D0; MOVE.B field(A6),D0; MOVE.W k(A0),D1.
bool se1_next_digit(AnimationMachineContext& c,std::uint32_t field,std::uint32_t k) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!se1_restore(c))return false;r.d[0]=0;if(!se1_get(c,r.a[6],field,1,value))return false;am_byte(r.d[0],value);
    if(!se1_get(c,r.a[0],k,2,value))return false;am_word(r.d[1],value);return true;
}
// The four character-portrait scripts of dee5e: CMPI.W #k,D0; BNE.W next / LSL.W #2,D0; MOVE.W #v,20(A6); MOVEA.L (A0,D0.W),A1; MOVE.W #100,D0;
// JSR 49f8c.l.
bool se1_portrait(AnimationMachineContext& c,std::uint32_t v,std::uint32_t return_pc) {
    am_word(c.s.d[0],c.s.d[0]<<2);if(!se1_put(c,c.s.a[6],0x20,2,v))return false;return se1_script_a0(c,return_pc);
}
}
// Select E1 (222 block starts, contract docs/analysis/animation-machine-select-e1-contract.md; area C/E plan unit E1): the character select nodes of
// de8bc..df2c0 (the creation callbacks de8ca de97e de9e8 deb1a deba4 and the 28ae children defdc dedb6 dee36 with their installed states), the shared
// tail de8bc (JSR 43e34; JSR 49fc6; RTS), the digit marks df272 / df2c0, the map-clip helper 18364 (falls through into the routed map-transfer block
// 183c6) and the boot input check 2634 (BYTE 300000 through the declared external-read queue).  No C consumer, no C producer: every block leaves C
// Unknown.  Z: de8f4 (BEQ after JSR ca50) recomputes the Z from BYTE -7699(A5) (work RAM only) and de938 (BEQ after JSR 4a974) from BYTE (A0)
// (the four credit BYTEs only), contract decision 3.  MOVE.L #v,(A6) writes the next callback; it is entered at once only when v is the next PC.
bool animation_select_e1_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool zero=false;
    switch(r.pc) {
    // ---- boot input check 2634 (from 262a): MOVE.B 300000.l,D0; ANDI.B #70,D0; BNE.W 2648 / MOVE.B #ff,7002(A5); RTS.
    case 0x2634:if(!am_read(c,0x300000,1,value))return false;am_byte(r.d[0],value&0x70U);r.pc=(r.d[0]&0x70U)!=0U?0x2648:0x2642;return true;
    case 0x2642:if(!se1_put(c,r.a[5],0x7002,1,0xff))return false;r.pc=0x2648;return true;
    // ---- map-clip helper 18364 (JSR from ded4a; falls through into the routed map-transfer block 183c6, the clip-out exit 185f4).
    // MOVE.W 14(A0),D6; ASR.W #4,D6; SUBI.W #fffa,D6; ADD.W D6,D4; MOVEQ #20,D7; ADD.W D2,D4; ADD.W D2,D7; CMP.W D7,D4; BCC.W 185f4.
    case 0x18364:
        if(!se1_get(c,r.a[0],0x14,2,value))return false;am_word(r.d[6],value);se1_asr4(r.d[6]);am_word(r.d[6],r.d[6]-0xfffaU);
        am_word(r.d[4],r.d[4]+r.d[6]);r.d[7]=0x20;am_word(r.d[4],r.d[4]+r.d[2]);am_word(r.d[7],r.d[7]+r.d[2]);
        r.pc=(r.d[4]&0xffffU)>=(r.d[7]&0xffffU)?0x185f4:0x1837c;return true;
    // SUB.W D2,D7; SUB.W D2,D4; BCC.W 1838a (no borrow of D4.W - D2.W).
    case 0x1837c:
        am_word(r.d[7],r.d[7]-r.d[2]);other=r.d[4]&0xffffU;am_word(r.d[4],r.d[4]-r.d[2]);r.pc=other>=(r.d[2]&0xffffU)?0x1838a:0x18384;return true;
    case 0x18384:am_word(r.d[0],r.d[0]-r.d[4]);am_word(r.d[2],r.d[2]+r.d[4]);r.d[4]=0;r.pc=0x1838a;return true;   // SUB.W D4,D0; ADD.W D4,D2; MOVEQ #0,D4.
    case 0x1838a:other=r.d[7]&0xffffU;am_word(r.d[7],r.d[7]-r.d[2]);r.pc=other>=(r.d[2]&0xffffU)?0x18392:0x18390;return true; // SUB.W D2,D7; BCC.
    case 0x18390:am_word(r.d[2],r.d[2]+r.d[7]);r.pc=0x18392;return true;                                  // ADD.W D7,D2.
    // SUB.W D6,D4; MOVE.W #80,D6; SUB.W 18(A0),D6; ASR.W #4,D6; SUB.W D6,D5; MOVEQ #1f,D7; ADD.W D3,D7; CMP.W D7,D5; BCC.W 185f4.
    case 0x18392:
        am_word(r.d[4],r.d[4]-r.d[6]);am_word(r.d[6],0x80);if(!se1_get(c,r.a[0],0x18,2,value))return false;am_word(r.d[6],r.d[6]-value);
        se1_asr4(r.d[6]);am_word(r.d[5],r.d[5]-r.d[6]);r.d[7]=0x1f;am_word(r.d[7],r.d[7]+r.d[3]);
        r.pc=(r.d[5]&0xffffU)>=(r.d[7]&0xffffU)?0x185f4:0x183aa;return true;
    // SUB.W D3,D7; SUB.W D7,D5; BCS.W 183b8 (borrow of D5.W - D7.W).
    case 0x183aa:
        am_word(r.d[7],r.d[7]-r.d[3]);other=r.d[5]&0xffffU;am_word(r.d[5],r.d[5]-r.d[7]);r.pc=other<(r.d[7]&0xffffU)?0x183b8:0x183b2;return true;
    case 0x183b2:am_word(r.d[1],r.d[1]+r.d[5]);am_word(r.d[3],r.d[3]-r.d[5]);r.d[5]=0;r.pc=0x183b8;return true;   // ADD.W D5,D1; SUB.W D5,D3; MOVEQ #0,D5.
    case 0x183b8:am_word(r.d[5],r.d[5]+r.d[7]);r.pc=(r.d[5]&0xffffU)>=(r.d[3]&0xffffU)?0x183c4:0x183c0;return true; // ADD.W D7,D5; CMP.W D3,D5; BCC.
    case 0x183c0:am_word(r.d[3],r.d[5]);am_word(r.d[3],r.d[3]+1U);r.pc=0x183c4;return true;              // MOVE.W D5,D3; ADDQ.W #1,D3.
    case 0x183c4:am_word(r.d[5],r.d[5]+r.d[6]);r.pc=0x183c6;return true;                                 // ADD.W D6,D5 (into the routed 183c6).
    // ---- shared tail de8bc: JSR 43e34.l; JSR 49fc6.l; RTS (also dee28 / def8c / defc0 with their own entries).
    case 0xde8bc:case 0xded00:case 0xded9e:case 0xdee28:case 0xdec10:case 0xdef8c:
        return am_call(c,0x43e34,r.pc==0xde8bc?0xde8c2:(r.pc==0xded00?0xded06:(r.pc==0xded9e?0xdeda4:(r.pc==0xdee28?0xdee2e:(r.pc==0xdec10?0xdec16:0xdef92)))));
    case 0xde8c2:case 0xdee2e:case 0xdef50:case 0xdef92:case 0xdefce:
        return am_call(c,0x49fc6,r.pc==0xde8c2?0xde8c8:(r.pc==0xdee2e?0xdee34:(r.pc==0xdef50?0xdef56:(r.pc==0xdef92?0xdef98:0xdefd4))));
    case 0xde8c8:case 0xdeb18:case 0xdec6c:case 0xdec76:case 0xdecfe:case 0xded9c:case 0xdedb4:case 0xdee34:case 0xdef56:case 0xdefda:
    case 0xdf0f0:case 0xdf126:case 0xdf15c:case 0xdf22e:case 0xdf270:case 0xdf2be:case 0xdf2ce:case 0x2648:
        return am_return(c);                                                                                 // RTS.
    // ---- de8ca (creation callback, text node): TST.W 7a(A6); BNE.W de8da / MOVE.W #709b,D0 / #735b,D0; MOVE.W D0,78(A6); MOVE.W #0,76(A6);
    // MOVE.L #de8ee,(A6) (enters de8ee).
    case 0xde8ca:return se1_zero(c,0x7a,2,0xde8d2,0xde8da);
    case 0xde8d2:am_word(r.d[0],0x709b);r.pc=0xde8de;return true;
    case 0xde8da:am_word(r.d[0],0x735b);r.pc=0xde8de;return true;
    case 0xde8de:
        if(!se1_put(c,r.a[6],0x78,2,r.d[0]) || !se1_put(c,r.a[6],0x76,2,0))return false;return se1_install(c,0xde8ee,0xde8ee);
    case 0xde8ee:return am_call(c,0xca50,0xde8f4);                                                       // JSR ca50.l.
    case 0xde8f4:if(!se1_flag_ca50(c,zero))return false;r.pc=zero?0xde910:0xde8f8;return true;          // BEQ.W de910 (Z of ca50).
    case 0xde8f8:r.a[0]=0xde49e;return se1_text(c,0xde90c);                                              // LEA de49e(PC),A0; text; JSR 3918.l.
    case 0xde90c:case 0xde960:r.pc=0xde978;return true;                                                  // BRA.W de978.
    case 0xde910:if(!se1_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4e186,0xde91a); // MOVE.W 7a(A6),D0.
    case 0xde91a:r.pc=(r.d[1]&0xffffU)!=0xffffU?0xde964:0xde922;return true;                             // CMPI.W #ffff,D1; BNE.W de964.
    // MOVE.W 76(A6),D0; ANDI.W #10,D0; BNE.W de94c.
    case 0xde922:if(!se1_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value&0x10U);r.pc=(r.d[0]&0xffffU)!=0U?0xde94c:0xde92e;return true;
    case 0xde92e:if(!se1_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4a974,0xde938); // MOVE.W 7a(A6),D0.
    case 0xde938:if(!se1_flag_credit(c,zero))return false;r.pc=zero?0xde944:0xde93c;return true;        // BEQ.W de944 (Z of 4a974).
    case 0xde93c:r.a[0]=0xde4b0;r.pc=0xde948;return true;                                                // LEA de4b0(PC),A0; BRA.W de948.
    case 0xde944:r.a[0]=0xde48c;r.pc=0xde948;return true;                                                // LEA de48c(PC),A0.
    case 0xde948:r.pc=0xde950;return true;                                                               // BRA.W de950.
    case 0xde94c:r.a[0]=0xde4c2;r.pc=0xde950;return true;                                                // LEA de4c2(PC),A0.
    case 0xde950:return se1_text(c,0xde960);
    case 0xde964:r.a[0]=0xde4c2;return se1_text(c,0xde978);
    case 0xde978:if(!se1_get(c,r.a[6],0x76,2,value) || !se1_put(c,r.a[6],0x76,2,value+1U))return false;return am_return(c); // ADDQ.W #1,76(A6); RTS.
    // ---- de97e (creation callback): shape c0, light ddc, BSET #2 of BYTE 15, 43e04 (a0, 1d8), the interpreter on the bank-window script 4(LONG 22).
    case 0xde97e:return se1_shape(c,0xc0,0xde990);
    case 0xde990:return se1_light(c,0xddc,0,0xde99e);
    // BSET.B #2,15(A6); MOVE.W #a0,D0; MOVE.W #1d8,D1; MOVEA.L #0,A1; JSR 43e04.l.
    case 0xde99e:
        if(!se1_get(c,r.a[6],0x15,1,value) || !se1_put(c,r.a[6],0x15,1,value|4U))return false;
        am_word(r.d[0],0xa0);am_word(r.d[1],0x1d8);r.a[1]=0;return am_call(c,0x43e04,0xde9b8);
    // LEA 26(A6),A0; MOVE.W #13a,20(A6); MOVE.L 2000c0.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 4(A1),A1; JSR 49f8c.l.
    case 0xde9b8:case 0xdedf4:
        if(r.pc==0xdedf4 && !se1_put(c,r.a[6],0x76,2,5))return false;                                   // (dedf4: MOVE.W #5,76(A6) first)
        r.a[0]=am_index(r.a[6],0x26);if(!se1_put(c,r.a[6],0x20,2,0x13a) || !se1_window(c))return false;am_word(r.d[0],0x100);
        if(!se1_get(c,r.a[6],0x22,4,r.a[1]))return false;
        if(!se1_get(c,r.a[1],r.pc==0xde9b8?4U:0xdcU,4,r.a[1]))return false;return am_call(c,0x49f8c,r.pc==0xde9b8?0xde9e0:0xdee22);
    case 0xde9e0:case 0xdeb9c:return se1_install_return(c,0xde8bc);                                    // MOVE.L #de8bc,(A6); RTS.
    // ---- de9e8 (creation callback, cursor node): shape 60, lights deb / dec, 43e04 (a0, 1a0), the blink state dea50.
    case 0xde9e8:return se1_shape(c,0x60,0xde9fa);
    case 0xde9fa:return se1_light(c,0xdeb,0,0xdea08);
    case 0xdea08:return se1_light(c,0xdec,0,0xdea16);
    case 0xdea16:am_word(r.d[0],0xa0);am_word(r.d[1],0x1a0);r.a[1]=0;return am_call(c,0x43e04,0xdea2a);
    // BSET.B #2,15(A6); MOVE.W #4,76(A6); MOVE.B #0,62(A6); MOVE.W #ffff,82(A6); MOVE.B #ff,84(A6); MOVE.L #dea50,(A6); RTS.
    case 0xdea2a:
        if(!se1_get(c,r.a[6],0x15,1,value) || !se1_put(c,r.a[6],0x15,1,value|4U) || !se1_put(c,r.a[6],0x76,2,4) || !se1_put(c,r.a[6],0x62,1,0) ||
           !se1_put(c,r.a[6],0x82,2,0xffff) || !se1_put(c,r.a[6],0x84,1,0xff))return false;
        return se1_install_return(c,0xdea50);
    case 0xdea50:return se1_count(c,0x76,0xdea58,0xdea62);                                               // SUBQ.W #1,76(A6); BNE.W dea62.
    // MOVE.W #4,76(A6); ADDQ.B #1,62(A6).
    case 0xdea58:
        if(!se1_put(c,r.a[6],0x76,2,4) || !se1_get(c,r.a[6],0x62,1,value) || !se1_put(c,r.a[6],0x62,1,value+1U))return false;r.pc=0xdea62;return true;
    // BTST.B #0,62(A6); BNE.W dea76.
    case 0xdea62:if(!se1_get(c,r.a[6],0x62,1,value))return false;r.pc=(value&1U)!=0U?0xdea76:0xdea6c;return true;
    case 0xdea6c:case 0xdea76:                                                                           // MOVE.B 19(A6) / 1a(A6),14(A6).
        if(!se1_get(c,r.a[6],r.pc==0xdea6c?0x19U:0x1aU,1,value) || !se1_put(c,r.a[6],0x14,1,value))return false;r.pc=0xdea7c;return true;
    case 0xdea7c:if(!se1_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4e186,0xdea86); // MOVE.W 7a(A6),D0.
    case 0xdea86:r.pc=(r.d[1]&0xffffU)==0xffffU?0xdeb18:0xdea8e;return true;                             // CMPI.W #ffff,D1; BEQ.W deb18.
    // MOVE.W D2,-(A7); TST.B 84(A6); BNE.W deab2.
    case 0xdea8e:if(!am_push(c,2,r.d[2]&0xffffU))return false;return se1_zero(c,0x84,1,0xdea98,0xdeab2);
    case 0xdea98:if(!se1_get(c,r.a[6],0x82,2,value))return false;r.pc=(r.d[2]&0xffffU)==value?0xdeaae:0xdeaa0;return true; // CMP.W 82(A6),D2.
    // MOVE.W D2,82(A6); MOVE.W #1ac2,D0; JSR 3af8.l.
    case 0xdeaa0:if(!se1_put(c,r.a[6],0x82,2,r.d[2]))return false;am_word(r.d[0],0x1ac2);return am_call(c,0x3af8,0xdeaae);
    case 0xdeaae:r.pc=0xdeaba;return true;                                                               // BRA.W deaba.
    case 0xdeab2:if(!se1_put(c,r.a[6],0x84,1,0) || !se1_put(c,r.a[6],0x82,2,r.d[2]))return false;r.pc=0xdeaba;return true; // CLR.B 84; MOVE.W D2,82.
    // MOVE.W (A7)+,D2; LEA de600(PC),A0; MOVE.W 7a(A6),D0; LSL.W #2,D0; MOVEA.L (A0,D0.W),A0; LSL.W #2,D2; MOVE.W D2,-(A7); MOVE.L (A0,D2.W),D2;
    // LEA 26(A6),A0; MOVE.W #13a,20(A6); MOVE.L 2000c0.l,22(A6); LEA 26(A6),A0; MOVE.W D2,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 2000c0.l,A1;
    // MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xdeaba:
        if(!am_pop(c,2,value))return false;am_word(r.d[2],value);r.a[0]=0xde600;if(!se1_index(c,2))return false;
        if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),4,r.a[0]))return false;am_word(r.d[2],r.d[2]<<2);
        if(!am_push(c,2,r.d[2]&0xffffU) || !am_read(c,am_index(r.a[0],r.d[2]&0xffffU),4,r.d[2]))return false;
        r.a[0]=am_index(r.a[6],0x26);if(!se1_put(c,r.a[6],0x20,2,0x13a) || !se1_window(c))return false;
        am_word(r.d[1],r.d[2]<<2);if(!am_read(c,0x2000c0,4,r.a[1]) || !am_read(c,am_index(r.a[1],r.d[1]&0xffffU),4,r.a[1]))return false;
        am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xdeb02);
    // MOVE.W (A7)+,D2; LEA de630(PC),A0; MOVE.W 2(A0,D2.W),32(A6); MOVE.W (A0,D2.W),2e(A6); JSR de8bc(PC).
    case 0xdeb02:
        if(!am_pop(c,2,value))return false;am_word(r.d[2],value);r.a[0]=0xde630;
        if(!am_read(c,am_index(r.a[0],r.d[2]&0xffffU)+2U,2,value) || !se1_put(c,r.a[6],0x32,2,value))return false;
        if(!am_read(c,am_index(r.a[0],r.d[2]&0xffffU),2,value) || !se1_put(c,r.a[6],0x2e,2,value))return false;return am_call(c,0xde8bc,0xdeb18);
    // ---- deb1a (creation callback, portrait frame): shape c0, light ddd, BSET #2 of BYTE 15, 43e04 from the WORD pair de640 + 4 x 7a, the script
    // LONG [2000c0] + 4 x LONG (de5f0 + 4 x 7a).
    case 0xdeb1a:return se1_shape(c,0xc0,0xdeb2c);
    case 0xdeb2c:return se1_light(c,0xddd,0,0xdeb3a);
    // BSET.B #2,15(A6); MOVE.W 7a(A6),D2; LSL.W #2,D2; LEA de640(PC),A0; MOVE.W (A0,D2.W),D0; MOVE.W 2(A0,D2.W),D1; MOVEA.L #0,A1; JSR 43e04.l.
    case 0xdeb3a:
        if(!se1_get(c,r.a[6],0x15,1,value) || !se1_put(c,r.a[6],0x15,1,value|4U) || !se1_get(c,r.a[6],0x7a,2,value))return false;
        am_word(r.d[2],value<<2);r.a[0]=0xde640;
        if(!am_read(c,am_index(r.a[0],r.d[2]&0xffffU),2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,am_index(r.a[0],r.d[2]&0xffffU)+2U,2,value))return false;am_word(r.d[1],value);r.a[1]=0;return am_call(c,0x43e04,0xdeb5e);
    // MOVE.W 7a(A6),D0; MOVE.W D0,D0; LEA 26(A6),A0; MOVE.W #13a,20(A6); MOVE.L 2000c0.l,22(A6); MOVEA.L #de5f0,A1; ADD.W D0,D0; ADD.W D0,D0;
    // MOVE.L (A1,D0.W),D0; MOVEA.L 2000c0.l,A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xdeb5e:
        if(!se1_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);r.a[0]=am_index(r.a[6],0x26);
        if(!se1_put(c,r.a[6],0x20,2,0x13a) || !se1_window(c))return false;r.a[1]=0xde5f0;am_word(r.d[0],r.d[0]<<2);
        if(!am_read(c,am_index(r.a[1],r.d[0]&0xffffU),4,r.d[0]) || !am_read(c,0x2000c0,4,r.a[1]))return false;am_word(r.d[0],r.d[0]<<2);
        if(!am_read(c,am_index(r.a[1],r.d[0]&0xffffU),4,r.a[1]))return false;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xdeb9c);
    // ---- deba4 (creation callback, portrait slide): shape 80 (no 8ff4: MOVE.W #80,68 / 1e), 43e04 from de588, the 28ae child defdc, the timer.
    case 0xdeba4:
        if(!se1_put(c,r.a[6],0x68,2,0x80) || !se1_put(c,r.a[6],0x1e,2,0x80))return false;return se1_place(c,0xde588,0xdebce);
    case 0xdebce:r.a[0]=0xdefdc;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0xdebde);                  // MOVEA.L #defdc,A0; MOVE.W #1e,D0; JSR 28ae.l.
    // MOVE.W 7a(A6),7a(A0); MOVE.W #a,D0; JSR 49a84.l (D0.W := random 0..9 [I]).
    case 0xdebde:
        if(!se1_get(c,r.a[6],0x7a,2,value) || !se1_put(c,r.a[0],0x7a,2,value))return false;am_word(r.d[0],0xa);return am_call(c,0x49a84,0xdebee);
    // ADDI.W #14,D0; MOVE.W D0,76(A6); MOVE.W #0,78(A6); MOVE.B #0,63(A6); MOVE.B #0,62(A6); MOVE.L #dec10,(A6); RTS.
    case 0xdebee:
        am_word(r.d[0],r.d[0]+0x14U);
        if(!se1_put(c,r.a[6],0x76,2,r.d[0]) || !se1_put(c,r.a[6],0x78,2,0) || !se1_put(c,r.a[6],0x63,1,0) || !se1_put(c,r.a[6],0x62,1,0))return false;
        return se1_install_return(c,0xdec10);
    case 0xdec16:return se1_zero(c,0x63,1,0xdec1e,0xdec30);                                              // TST.B 63(A6); BNE.W dec30.
    case 0xdec1e:return se1_count(c,0x76,0xdec26,0xdec2c);                                               // SUBQ.W #1,76(A6); BNE.W dec2c.
    case 0xdec26:return se1_mark(c,0x63,1,0xdec2c);                                                      // MOVE.B #1,63(A6).
    case 0xdec2c:r.pc=0xdec6c;return true;                                                               // BRA.W dec6c.
    case 0xdec30:return se1_zero(c,0x78,2,0xdec38,0xdec46);                                              // TST.W 78(A6); BNE.W dec46.
    // SUBQ.W #2,32(A6); MOVE.W #ffff,78(A6); BRA.W dec6c.
    case 0xdec38:
        if(!se1_get(c,r.a[6],0x32,2,value) || !se1_put(c,r.a[6],0x32,2,value-2U) || !se1_put(c,r.a[6],0x78,2,0xffff))return false;r.pc=0xdec6c;return true;
    // ADDI.W #a,32(A6); CMPI.W #170,32(A6); BLT.W dec5c (signed).
    case 0xdec46:
        if(!se1_get(c,r.a[6],0x32,2,value) || !se1_put(c,r.a[6],0x32,2,value+0xaU))return false;
        r.pc=se1_signed_word(value+0xaU)<0x170?0xdec5c:0xdec56;return true;
    case 0xdec56:return se1_mark(c,0x63,2,0xdec5c);                                                      // MOVE.B #2,63(A6).
    case 0xdec5c:if(!se1_get(c,r.a[6],0x32,2,value))return false;r.pc=se1_signed_word(value)<0x1b0?0xdec6c:0xdec66;return true; // CMPI.W #1b0; BLT.
    case 0xdec66:return se1_install(c,0xdec6e,0xdec6c);                                                  // MOVE.L #dec6e,(A6) (then RTS dec6c).
    case 0xdec6e:return se1_zero(c,0x62,1,0xdec76,0xdec78);                                              // TST.B 62(A6); BNE.W dec78.
    // MOVEA.L c(A6),A0; ADDQ.B #1,62(A0); MOVE.B #3,63(A6); MOVE.L #dec8c,(A6) (enters dec8c).
    case 0xdec78:
        if(!se1_get(c,r.a[6],0xc,4,r.a[0]) || !se1_get(c,r.a[0],0x62,1,value) || !se1_put(c,r.a[0],0x62,1,value+1U) || !se1_put(c,r.a[6],0x63,1,3))return false;
        return se1_install(c,0xdec8c,0xdec8c);
    case 0xdec8c:if(!se1_put(c,r.a[6],0x63,1,0))return false;return se1_query(c,0,0xdec9c);             // MOVE.B #0,63(A6); query 0.
    case 0xdec9c:r.pc=(r.d[1]&0xffffU)!=1U?0xdecb2:0xdeca4;return true;                                   // CMPI.W #1,D1; BNE.W decb2.
    case 0xdeca4:return se1_same_slot(c,0xdecac,0xdecb2);
    case 0xdecac:return se1_mark(c,0x63,1,0xdecb2);
    case 0xdecb2:return se1_query(c,1,0xdecbc);
    case 0xdecbc:r.pc=(r.d[1]&0xffffU)!=1U?0xdecd2:0xdecc4;return true;
    case 0xdecc4:return se1_same_slot(c,0xdeccc,0xdecd2);
    case 0xdeccc:return se1_mark(c,0x63,1,0xdecd2);
    case 0xdecd2:return se1_zero(c,0x63,1,0xdecfe,0xdecda);                                              // TST.B 63(A6); BEQ.W decfe.
    // LEA de628(PC),A0; MOVE.W 7a(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; JSR 3af8.l (the selection sound [I]).
    case 0xdecda:
        r.a[0]=0xde628;if(!se1_index(c,1) || !am_read(c,am_index(r.a[0],r.d[0]&0xffffU),2,value))return false;am_word(r.d[0],value);
        return am_call(c,0x3af8,0xdecee);
    // MOVE.W #1e,76(A6); CLR.B 84(A6); MOVE.L #ded00,(A6) (then RTS decfe).
    case 0xdecee:if(!se1_put(c,r.a[6],0x76,2,0x1e) || !se1_put(c,r.a[6],0x84,1,0))return false;return se1_install(c,0xded00,0xdecfe);
    case 0xded06:return se1_zero(c,0x76,2,0xded0e,0xded98);                                              // TST.W 76(A6); BNE.W ded98.
    // SUBI.W #10,32(A6); CMPI.W #12c,32(A6); BGT.W ded94 (signed).
    case 0xded0e:
        if(!se1_get(c,r.a[6],0x32,2,value) || !se1_put(c,r.a[6],0x32,2,value-0x10U))return false;
        r.pc=se1_signed_word(value-0x10U)>0x12c?0xded94:0xded1e;return true;
    case 0xded1e:am_word(r.d[0],4);return am_call(c,0x3d7e,0xded28);                                    // MOVE.W #4,D0; JSR 3d7e.l.
    // LEA 109156.l,A0; LEA df2d0(PC),A1; MOVE.W #0,D0; MOVE.W #0,D1; MOVE.W #16,D2; MOVE.W #10,D3; MOVE.W #0,D4; MOVE.W #10,D5; JSR 18364.l.
    case 0xded28:
        r.a[0]=0x109156;r.a[1]=0xdf2d0;am_word(r.d[0],0);am_word(r.d[1],0);am_word(r.d[2],0x16);am_word(r.d[3],0x10);am_word(r.d[4],0);am_word(r.d[5],0x10);
        return am_call(c,0x18364,0xded50);
    // MOVE.W #0,78(A6); MOVE.W #12c,32(A6); MOVE.W 32(A6),80(A6); MOVEA.L #dedb6,A0; MOVE.W #1e,D0; JSR 28ae.l.
    case 0xded50:
        if(!se1_put(c,r.a[6],0x78,2,0) || !se1_put(c,r.a[6],0x32,2,0x12c) || !se1_get(c,r.a[6],0x32,2,value) || !se1_put(c,r.a[6],0x80,2,value))return false;
        r.a[0]=0xdedb6;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0xded72);
    // MOVE.W 7a(A6),7a(A0); MOVEA.L #dee36,A0; MOVE.W #1e,D0; JSR 28ae.l.
    case 0xded72:
        if(!se1_get(c,r.a[6],0x7a,2,value) || !se1_put(c,r.a[0],0x7a,2,value))return false;r.a[0]=0xdee36;am_word(r.d[0],0x1e);
        return am_call(c,0x28ae,0xded88);
    // MOVE.W 7a(A6),7a(A0); MOVE.L #ded9e,(A6) (then BRA ded94 -> RTS).
    case 0xded88:if(!se1_get(c,r.a[6],0x7a,2,value) || !se1_put(c,r.a[0],0x7a,2,value))return false;return se1_install(c,0xded9e,0xded94);
    case 0xded94:r.pc=0xded9c;return true;                                                               // BRA.W ded9c.
    case 0xded98:return se1_count(c,0x76,0xded9c,0xded9c);                                               // SUBQ.W #1,76(A6) (both sides ded9c).
    // CMPI.W #10,78(A6); BGE.W dedb4 (signed) / MOVE.W 80(A6),32(A6).
    case 0xdeda4:if(!se1_get(c,r.a[6],0x78,2,value))return false;r.pc=se1_signed_word(value)>=0x10?0xdedb4:0xdedae;return true;
    case 0xdedae:if(!se1_get(c,r.a[6],0x80,2,value) || !se1_put(c,r.a[6],0x32,2,value))return false;r.pc=0xdedb4;return true;
    // ---- 28ae child dedb6 (name plate): shape 80, light ded, 43e04 from de650, the bank-window script dc(LONG 22) (dedf4 above), state dee28.
    case 0xdedb6:return se1_shape(c,0x80,0xdedc8);
    case 0xdedc8:return se1_light(c,0xded,0,0xdedd6);
    case 0xdedd6:return se1_place(c,0xde650,0xdedf4);
    case 0xdee22:return se1_install(c,0xdee28,0xdee28);                                                  // MOVE.L #dee28,(A6) (enters dee28).
    // ---- 28ae child dee36 (portrait): shape a0, light WORD de580 + 2 x 7a with D1.W := 0, the portrait script dfbc0 + 4 x 7a (7a = 0..3).
    case 0xdee36:return se1_shape(c,0xa0,0xdee48);
    // LEA de580(PC),A0; MOVE.W 7a(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; CLR.W D1; JSR 8ebe.l.
    case 0xdee48:
        r.a[0]=0xde580;if(!se1_index(c,1) || !am_read(c,am_index(r.a[0],r.d[0]&0xffffU),2,value))return false;am_word(r.d[0],value);am_word(r.d[1],0);
        return am_call(c,0x8ebe,0xdee5e);
    // LEA dfbc0.l,A0; MOVE.W 7a(A6),D0; CMPI.W #0,D0; BNE.W dee8a.
    case 0xdee5e:r.a[0]=0xdfbc0;if(!se1_index(c,0))return false;r.pc=(r.d[0]&0xffffU)!=0U?0xdee8a:0xdee70;return true;
    case 0xdee8a:r.pc=(r.d[0]&0xffffU)!=1U?0xdeeac:0xdee92;return true;                                   // CMPI.W #1,D0; BNE.W deeac.
    case 0xdeeac:r.pc=(r.d[0]&0xffffU)!=2U?0xdeece:0xdeeb4;return true;                                   // CMPI.W #2,D0; BNE.W deece.
    case 0xdeece:r.pc=(r.d[0]&0xffffU)!=3U?0xdeef0:0xdeed6;return true;                                   // CMPI.W #3,D0; BNE.W deef0.
    case 0xdee70:return se1_portrait(c,2,0xdee86);
    case 0xdee92:return se1_portrait(c,0xa,0xdeea8);
    case 0xdeeb4:return se1_portrait(c,0x12,0xdeeca);
    case 0xdeed6:return se1_portrait(c,0x1a,0xdeeec);
    case 0xdee86:case 0xdeea8:case 0xdeeca:case 0xdeeec:r.pc=0xdeef0;return true;                        // BRA.W deef0.
    // MOVEA.L c(A6),A0; MOVE.W 2e(A0),2e(A6); MOVE.W #188,32(A6); SUBI.W #8,32(A6); MOVE.L #0,36(A6); MOVE.L #0,3a(A6); MOVE.W #73c,D0; JSR 3c44.l.
    case 0xdeef0:
        if(!se1_get(c,r.a[6],0xc,4,r.a[0]) || !se1_get(c,r.a[0],0x2e,2,value) || !se1_put(c,r.a[6],0x2e,2,value) || !se1_put(c,r.a[6],0x32,2,0x188) ||
           !se1_get(c,r.a[6],0x32,2,value) || !se1_put(c,r.a[6],0x32,2,value-8U) || !se1_put(c,r.a[6],0x36,4,0) || !se1_put(c,r.a[6],0x3a,4,0))return false;
        am_word(r.d[0],0x73c);return am_call(c,0x3c44,0xdef20);
    case 0xdef20:am_word(r.d[0],0x73e);return am_call(c,0x3af8,0xdef2a);                                // MOVE.W #73e,D0; JSR 3af8.l.
    case 0xdef2a:return se1_install_return(c,0xdef32);                                                  // MOVE.L #def32,(A6); RTS.
    // ADDI.L #ffffb000,3a(A6); JSR 43ea4.l.
    case 0xdef32:if(!se1_get(c,r.a[6],0x3a,4,value) || !se1_put(c,r.a[6],0x3a,4,value+0xffffb000U))return false;return am_call(c,0x43ea4,0xdef40);
    // CMPI.W #148,32(A6); BCC.W def50 (unsigned) / MOVE.L #def58,(A6).
    case 0xdef40:if(!se1_get(c,r.a[6],0x32,2,value))return false;r.pc=value>=0x148U?0xdef50:0xdef4a;return true;
    case 0xdef4a:return se1_install(c,0xdef58,0xdef50);
    // MOVE.L #0,3a(A6); MOVE.W #148,32(A6); script dfbd0.
    case 0xdef58:if(!se1_put(c,r.a[6],0x3a,4,0) || !se1_put(c,r.a[6],0x32,2,0x148))return false;return se1_script(c,0xdfbd0,0xdef80);
    case 0xdef80:if(!se1_put(c,r.a[6],0x76,2,4))return false;return se1_install(c,0xdef8c,0xdef8c);     // MOVE.W #4,76(A6); MOVE.L #def8c,(A6).
    case 0xdef98:return se1_count(c,0x76,0xdefa0,0xdefda);                                               // SUBQ.W #1,76(A6); BNE.W defda.
    case 0xdefa0:return se1_script(c,0xdfbb0,0xdefba);
    case 0xdefba:return se1_install(c,0xdefc0,0xdefc0);                                                  // MOVE.L #defc0,(A6) (enters defc0).
    case 0xdefc0:if(!se1_put(c,r.a[6],0x36,4,0x30000))return false;return am_call(c,0x43e34,0xdefce);   // MOVE.L #30000,36(A6); JSR 43e34.l.
    case 0xdefd4:return am_call(c,0x43ea4,0xdefda);                                                      // JSR 43ea4.l.
    // ---- 28ae child defdc (selection cursor): shape 40, 43e04 from de588 with the index LONG kept on the stack, three lights b00, the script de5e0.
    case 0xdefdc:return se1_shape(c,0x40,0xdefee);
    // LEA de588(PC),A0; MOVE.W 7a(A6),D0; LSL.W #2,D0; MOVE.L D0,-(A7); MOVE.W 2(A0,D0.W),D1; MOVE.W (A0,D0.W),D0; MOVEA.L #0,A1; JSR 43e04.l.
    case 0xdefee:r.a[0]=0xde588;if(!se1_index(c,2) || !am_push(c,4,r.d[0]))return false;return se1_place_a0(c,0xdf00e);
    case 0xdf00e:return se1_light(c,0xb00,1,0xdf01c);
    case 0xdf01c:return se1_light(c,0xb00,1,0xdf02a);
    case 0xdf02a:return se1_light(c,0xb00,1,0xdf038);
    // MOVE.L (A7)+,D0; LEA de5e0(PC),A0; MOVE.W #13a,20(A6); MOVEA.L (A0,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xdf038:if(!am_pop(c,4,r.d[0]))return false;r.a[0]=0xde5e0;if(!se1_put(c,r.a[6],0x20,2,0x13a))return false;return se1_script_a0(c,0xdf052);
    // MOVE.B #0,63(A6); MOVE.B #0,62(A6); MOVE.W #0,7c(A6); MOVE.L #df06c,(A6); RTS.
    case 0xdf052:
        if(!se1_put(c,r.a[6],0x63,1,0) || !se1_put(c,r.a[6],0x62,1,0) || !se1_put(c,r.a[6],0x7c,2,0))return false;return se1_install_return(c,0xdf06c);
    case 0xdf06c:return se1_query(c,0,0xdf076);
    case 0xdf076:r.pc=(r.d[1]&0xffffU)==0xffffU?0xdf08c:0xdf07e;return true;                             // CMPI.W #ffff,D1; BEQ.W df08c.
    case 0xdf07e:return se1_same_slot(c,0xdf086,0xdf08c);
    case 0xdf086:return se1_mark(c,0x62,1,0xdf08c);
    case 0xdf08c:return se1_query(c,1,0xdf096);
    case 0xdf096:r.pc=(r.d[1]&0xffffU)==0xffffU?0xdf0ac:0xdf09e;return true;
    case 0xdf09e:return se1_same_slot(c,0xdf0a6,0xdf0ac);
    case 0xdf0a6:return se1_mark(c,0x62,1,0xdf0ac);
    case 0xdf0ac:return am_call(c,0xde8bc,0xdf0b0);                                                      // JSR de8bc(PC).
    // MOVEA.L c(A6),A0; CMPI.B #2,63(A0); BLT.W df0f0 (signed).
    case 0xdf0b0:
        if(!se1_get(c,r.a[6],0xc,4,r.a[0]) || !se1_get(c,r.a[0],0x63,1,value))return false;r.pc=se1_signed_byte(value)<2?0xdf0f0:0xdf0be;return true;
    // MOVE.W #0,78(A6); MOVE.L #df128,(A6); TST.B 62(A6); BEQ.W df0f0.
    case 0xdf0be:if(!se1_put(c,r.a[6],0x78,2,0) || !se1_put(c,r.a[6],0,4,0xdf128))return false;return se1_zero(c,0x62,1,0xdf0f0,0xdf0d2);
    case 0xdf0d2:return se1_script(c,0xde5c0,0xdf0ea);
    case 0xdf0ea:return se1_install(c,0xdf0f2,0xdf0f0);                                                  // MOVE.L #df0f2,(A6) (then RTS df0f0).
    // CMPI.W #20,78(A6); BLT.W df116 / df14c (signed).
    case 0xdf0f2:case 0xdf128:
        if(!se1_get(c,r.a[6],0x78,2,value))return false;
        r.pc=se1_signed_word(value)<0x20?(r.pc==0xdf0f2?0xdf116:0xdf14c):(r.pc==0xdf0f2?0xdf0fc:0xdf132);return true;
    // MOVEA.L c(A6),A0; MOVE.B #ff,62(A0); MOVE.B #1 / #0,85(A6); MOVE.L #df15e,(A6); BRA.W df122 / df158.
    case 0xdf0fc:case 0xdf132:
        if(!se1_get(c,r.a[6],0xc,4,r.a[0]) || !se1_put(c,r.a[0],0x62,1,0xff) || !se1_put(c,r.a[6],0x85,1,r.pc==0xdf0fc?1U:0U))return false;
        return se1_install(c,0xdf15e,r.pc==0xdf0fc?0xdf122:0xdf158);
    // MOVE.W 78(A6),D2; JSR df272(PC) / df2c0(PC).
    case 0xdf116:case 0xdf14c:
        if(!se1_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[2],value);return am_call(c,r.pc==0xdf116?0xdf272:0xdf2c0,r.pc==0xdf116?0xdf11e:0xdf154);
    // ADDQ.W #1,78(A6).
    case 0xdf11e:case 0xdf154:
        if(!se1_get(c,r.a[6],0x78,2,value) || !se1_put(c,r.a[6],0x78,2,value+1U))return false;r.pc=r.pc==0xdf11e?0xdf122:0xdf158;return true;
    case 0xdf122:case 0xdf158:case 0xdf22a:case 0xdf26c:                                                 // JSR de8bc(PC).
        return am_call(c,0xde8bc,r.pc==0xdf122?0xdf126:(r.pc==0xdf158?0xdf15c:(r.pc==0xdf22a?0xdf22e:0xdf270)));
    case 0xdf15e:if(!se1_put(c,r.a[6],0x62,1,0))return false;return se1_query(c,0,0xdf16e);              // MOVE.B #0,62(A6); query 0.
    case 0xdf16e:return se1_same_slot(c,0xdf176,0xdf192);                                              // CMP.W 7a(A6),D2; BNE.W df192.
    case 0xdf176:r.pc=(r.d[1]&0xffffU)==0xffffU?0xdf192:0xdf17e;return true;                             // CMPI.W #ffff,D1; BEQ.W df192.
    case 0xdf17e:if(!se1_put(c,r.a[6],0x62,1,1))return false;r.pc=(r.d[1]&0xffffU)!=1U?0xdf192:0xdf18c;return true; // MOVE.B #1,62; CMPI.W #1,D1.
    case 0xdf18c:return se1_mark(c,0x62,2,0xdf192);
    case 0xdf192:return se1_query(c,1,0xdf19c);
    case 0xdf19c:return se1_same_slot(c,0xdf1a4,0xdf1c0);
    case 0xdf1a4:r.pc=(r.d[1]&0xffffU)==0xffffU?0xdf1c0:0xdf1ac;return true;
    case 0xdf1ac:if(!se1_put(c,r.a[6],0x62,1,1))return false;r.pc=(r.d[1]&0xffffU)!=1U?0xdf1c0:0xdf1ba;return true;
    case 0xdf1ba:return se1_mark(c,0x62,2,0xdf1c0);
    // MOVE.B 62(A6),D0; CMP.B 85(A6),D0; BEQ.W df22a.
    case 0xdf1c0:
        if(!se1_get(c,r.a[6],0x62,1,value))return false;am_byte(r.d[0],value);if(!se1_get(c,r.a[6],0x85,1,value))return false;
        r.pc=(r.d[0]&0xffU)==value?0xdf22a:0xdf1cc;return true;
    case 0xdf1cc:if(!se1_put(c,r.a[6],0x85,1,r.d[0]))return false;r.pc=(r.d[0]&0xffU)!=0U?0xdf1fa:0xdf1d6;return true; // MOVE.B D0,85; TST.B D0.
    case 0xdf1d6:am_byte(r.d[2],0x20);return am_call(c,0xdf2c0,0xdf1de);                                // MOVE.B #20,D2; JSR df2c0(PC).
    case 0xdf1de:return se1_script(c,0xde5e0,0xdf1f6);
    case 0xdf1f6:r.pc=0xdf22a;return true;                                                               // BRA.W df22a.
    case 0xdf1fa:case 0xdf264:am_byte(r.d[2],0x20);return am_call(c,0xdf272,r.pc==0xdf1fa?0xdf202:0xdf26c); // MOVE.B #20,D2; JSR df272(PC).
    case 0xdf202:return se1_script(c,0xde5c0,0xdf21a);
    case 0xdf21a:if(!se1_get(c,r.a[6],0x62,1,value))return false;r.pc=value!=2U?0xdf22a:0xdf224;return true; // CMPI.B #2,62(A6); BNE.W df22a.
    case 0xdf224:return se1_install(c,0xdf230,0xdf22a);                                                  // MOVE.L #df230,(A6).
    case 0xdf230:return se1_script(c,0xde5d0,0xdf248);
    case 0xdf248:if(!se1_put(c,r.a[6],0x76,2,2))return false;return se1_install(c,0xdf254,0xdf254);     // MOVE.W #2,76(A6); MOVE.L #df254,(A6).
    case 0xdf254:return se1_zero(c,0x76,2,0xdf26c,0xdf25c);                                              // TST.W 76(A6); BEQ.W df26c.
    case 0xdf25c:return se1_count(c,0x76,0xdf264,0xdf26c);                                               // SUBQ.W #1,76(A6); BNE.W df26c.
    // ---- digit marks df272 (three digits of the WORD triple at LONG (de598 + 4 x 7a), MOVEM-saved D2 / A0) and df2c0 (one mark dea).
    case 0xdf272:if(!se1_digits(c) || !se1_save(c))return false;return am_call(c,0x8cda,0xdf292);
    case 0xdf292:if(!se1_next_digit(c,0x1a,2) || !se1_save(c))return false;return am_call(c,0x8cda,0xdf2aa);
    case 0xdf2aa:if(!se1_next_digit(c,0x1b,4))return false;return am_call(c,0x8cda,0xdf2be);
    // MOVE.B 19(A6),D0; MOVE.W #dea,D1; JSR 8cda.l.
    case 0xdf2c0:if(!se1_get(c,r.a[6],0x19,1,value))return false;am_byte(r.d[0],value);am_word(r.d[1],0xdea);return am_call(c,0x8cda,0xdf2ce);
    default:
        return am_error(c,"unsupported animation select e1 PC");
    }
}
}
