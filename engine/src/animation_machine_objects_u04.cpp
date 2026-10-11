#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (LEA d16(PC), MOVE.L #, MOVEA.L #, LEA xxx.L, JSR/JMP xxx.L).
const std::uint32_t OV_TABLE_A=0xd727a;    // d72f6 LEA d727a(PC),A0 (5 records of 12 bytes, fixed ROM)
const std::uint32_t OV_TABLE_B=0xd72b6;    // d72fe LEA d72b6(PC),A0 (5 records of 12 bytes, fixed ROM)
const std::uint32_t OV_CHILD=0xd73de;      // d7352 MOVEA.L #d73de,A0 (child callback for 28ae)
const std::uint32_t OV_COSINE=0x4419e;     // d7506 LEA 4419e.L,A0 (256 WORDs, fixed ROM)
const std::uint32_t OV_SORT=0xce02;        // d73d8 JMP ce02.L
const std::uint32_t OV_DELETE=0x2a00;      // JMP 2a00.L (self delete)
bool ov_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ov_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BSET/BCLR #bit,d16(A6): BYTE read-modify-write.
bool ov_bit(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t bit,bool set) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ov_get(c,r.a[6],displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    return ov_put(c,r.a[6],displacement,1,set?((value|mask)&255U):(value&~mask&255U));
}
// ASR.L #n (arithmetic, n = 1..8) and ASR.W #n on the low WORD.
std::uint32_t ov_asr_long(std::uint32_t value,unsigned int n) {
    const std::uint32_t fill=(value&0x80000000U)?~(0xffffffffU>>n):0U;return (value>>n)|fill;
}
std::uint32_t ov_asr_word(std::uint32_t value,unsigned int n) {
    value&=65535U;const std::uint32_t fill=(value&0x8000U)?((~(0xffffU>>n))&65535U):0U;return ((value>>n)|fill)&65535U;
}
// Signed view of a WORD (explicit two's complement).
std::int32_t ov_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
// MULS.W: 16 x 16 signed -> 32 (|product| <= 2^30, kept in 64 bits, then the two's complement LONG).
std::uint32_t ov_muls(std::uint32_t a,std::uint32_t b) {
    const std::int64_t p=static_cast<std::int64_t>(ov_signed_word(a))*static_cast<std::int64_t>(ov_signed_word(b));
    return static_cast<std::uint32_t>(static_cast<std::uint64_t>(p)&0xffffffffULL);
}
// MULU.W: 16 x 16 unsigned -> 32 (at most fffe0001).
std::uint32_t ov_mulu(std::uint32_t a,std::uint32_t b) {return (a&65535U)*(b&65535U);}
// SUBQ.W #1,d16(A6); write; returns the WORD before the subtraction.
bool ov_decrement(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t& before) {
    AnimationMachineState& r=c.s;
    if(!ov_get(c,r.a[6],displacement,2,before))return false;before&=65535U;
    return ov_put(c,r.a[6],displacement,2,(before-1U)&65535U);
}
// MOVE.L #callback,(A6), then the callback entry (fall-through).
bool ov_install(AnimationMachineContext& c,std::uint32_t callback) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=callback;return true;
}
// ASR.L #1,Dn; ADD.L Dn,d16(A6).
bool ov_half_add(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t displacement) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;d=ov_asr_long(d,1);
    if(!ov_get(c,r.a[6],displacement,4,value))return false;return ov_put(c,r.a[6],displacement,4,value+d);
}
// SUB.W d16(A6),Dn (upper WORD zero from MOVEQ #0); SWAP Dn; ASR.L #3,Dn; SUB.L d16(A6),Dn; BMI minus_pc else plus_pc.
bool ov_steer(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t position,std::uint32_t velocity,
    std::uint32_t minus_pc,std::uint32_t plus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ov_get(c,r.a[6],position,2,value))return false;am_word(d,(d-value)&65535U);
    am_swap(d);d=ov_asr_long(d,3);
    if(!ov_get(c,r.a[6],velocity,4,value))return false;d=d-value;
    r.pc=(d&0x80000000U)?minus_pc:plus_pc;return true;
}
}
// Object callbacks F4 U04 (69 block starts): the delayed sprite queue sort ce02 (D0.W = new tag), the C5 entry 43ea4 (LEA
// 2e(A6),A0, then the scene update block 43ea8), and the node callback d72f2/d72fe with its installed callbacks d7346/d7396/
// d73b0/d73c4 and the child callback d73de with its installed callback d7424. Every C consumer is a BCC/BCS inside the block of
// its SUBQ/CMPI/CMP; no block produces a known C. d73ca branches on the Z of the 287e CMP.W 10(A0),D0: A0, D0 and the WORD
// 10(A0) are unchanged by the 287e RTS, so the Z is recomputed from the live registers (contract decision 2). The tail
// 16ede..16eee of 16ed2 stays inside the sprite executor (decision 1). Existing executors called: sound 3af8, fade_card 28ae
// (child) and 2a00 (self delete), cleanup 287e, sprite 16ed2/16ea4, hud 8cda, scene update 43ea8 (then cleanup 43e38); 8ebe
// is U02 (no executor in a tree without U02). ROM data (d727a/d72b6 records, item lists, the 4419e WORD table) is read through
// the live bus; d16(A5) operands use the live A5. The ce22..ce46 sort loop has no extra limit (block budget only).
bool animation_objects_u04_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- ce02: MOVE.W 1150(A5),D7; MOVE.W D0,1150(A5); MOVE.W 114e(A5),D6; BEQ ce60.
    case 0xce02:
        if(!ov_get(c,r.a[5],0x1150,2,value))return false;am_word(r.d[7],value);
        if(!ov_put(c,r.a[5],0x1150,2,r.d[0]&65535U) || !ov_get(c,r.a[5],0x114e,2,value))return false;am_word(r.d[6],value);
        r.pc=(value&65535U)?0xce12:0xce60;return true;
    // LEA -cc(A5),A0; LEA b34(A5),A1; MOVE.W d38(A5),D5; LEA f4e(A5),A2.
    case 0xce12:
        r.a[0]=am_index(r.a[5],0xff34);r.a[1]=am_index(r.a[5],0xb34);
        if(!ov_get(c,r.a[5],0xd38,2,value))return false;am_word(r.d[5],value);r.a[2]=am_index(r.a[5],0xf4e);r.pc=0xce22;return true;
    // LEA (A2,D6.W),A3; MOVE.W -(A3),D0; MOVE.W (A0,D0.W),D1.
    case 0xce22:
        r.a[3]=am_index(r.a[2],r.d[6])-2U;if(!am_read(c,r.a[3],2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[1],value);r.pc=0xce2c;return true;
    case 0xce2c:r.pc=r.a[3]==r.a[2]?0xce46:0xce32;return true; // CMPA.L A3,A2; BEQ ce46.
    // MOVE.W -(A3),D2; MOVE.W (A0,D2.W),D3; CMP.W D3,D1; BCS ce44 (unsigned D1.W < D3.W).
    case 0xce32:
        r.a[3]-=2U;if(!am_read(c,r.a[3],2,value))return false;am_word(r.d[2],value);
        if(!am_read(c,am_index(r.a[0],r.d[2]),2,value))return false;am_word(r.d[3],value);
        r.pc=(r.d[1]&65535U)<(r.d[3]&65535U)?0xce44:0xce3e;return true;
    // MOVE.W D3,D1; MOVE.W D0,(A3); MOVE.W D2,D0.
    case 0xce3e:am_word(r.d[1],r.d[3]);if(!am_write(c,r.a[3],2,r.d[0]&65535U))return false;am_word(r.d[0],r.d[2]);r.pc=0xce44;return true;
    case 0xce44:r.pc=0xce2c;return true; // BRA.B ce2c.
    // MOVE.W D7,(A0,D0.W); MOVE.W D0,(A1,D5.W); ADDQ.W #2,D5; ANDI.W #1fe,D5; SUBQ.W #2,D6; BNE ce22.
    case 0xce46:
        if(!am_write(c,am_index(r.a[0],r.d[0]),2,r.d[7]&65535U) || !am_write(c,am_index(r.a[1],r.d[5]),2,r.d[0]&65535U))return false;
        am_word(r.d[5],(r.d[5]+2U)&0x1feU);am_word(r.d[6],(r.d[6]-2U)&65535U);r.pc=(r.d[6]&65535U)?0xce22:0xce58;return true;
    // MOVE.W D5,d38(A5); MOVE.W D6,114e(A5).
    case 0xce58:
        if(!ov_put(c,r.a[5],0xd38,2,r.d[5]&65535U) || !ov_put(c,r.a[5],0x114e,2,r.d[6]&65535U))return false;r.pc=0xce60;return true;
    case 0xce60:case 0xd7504:case 0xd75cc:return am_return(c); // RTS.

    // ---- 43ea4: LEA 2e(A6),A0 (then the scene update block 43ea8).
    case 0x43ea4:r.a[0]=am_index(r.a[6],0x2e);r.pc=0x43ea8;return true;

    // ---- d72f2 (callback): CLR.W 1e(A6); LEA d727a(PC),A0; BRA d7302.
    case 0xd72f2:if(!ov_put(c,r.a[6],0x1e,2,0))return false;r.a[0]=OV_TABLE_A;r.pc=0xd7302;return true;
    case 0xd72fe:r.a[0]=OV_TABLE_B;r.pc=0xd7302;return true; // LEA d72b6(PC),A0 (callback).
    // SUBQ.W #1,76(A6); BCC d7310 (C = borrow: the WORD was 0).
    case 0xd7302:if(!ov_decrement(c,0x76,value))return false;r.pc=value?0xd7310:0xd730a;return true;
    case 0xd730a:case 0xd731a:case 0xd73ce:case 0xd748c:case 0xd74a2:r.pc=OV_DELETE;return true; // JMP 2a00.L.
    // CMPI.W #5,76(A6); BCS d7320 (unsigned).
    case 0xd7310:if(!ov_get(c,r.a[6],0x76,2,value))return false;r.pc=(value&65535U)<5U?0xd7320:0xd731a;return true;
    // MOVE.W 76(A6),D0; MULS.W #c,D0; LEA (A0,D0.W),A0; MOVE.L (A0)+,7e(A6); MOVE.L (A0)+,78(A6); MOVE.L (A0)+,D0; JSR 3af8.L.
    case 0xd7320:
        if(!ov_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.d[0]=ov_muls(r.d[0],0xc);
        r.a[0]=am_index(r.a[0],r.d[0]);
        if(!am_read(c,r.a[0],4,value) || !ov_put(c,r.a[6],0x7e,4,value))return false;r.a[0]+=4U;
        if(!am_read(c,r.a[0],4,value) || !ov_put(c,r.a[6],0x78,4,value))return false;r.a[0]+=4U;
        if(!am_read(c,r.a[0],4,value))return false;r.d[0]=value;r.a[0]+=4U;
        return am_call(c,0x3af8,0xd733c);
    // CLR.W 7c(A6); MOVE.L #d7346,(A6).
    case 0xd733c:if(!ov_put(c,r.a[6],0x7c,2,0))return false;return ov_install(c,0xd7346);
    // SUBQ.W #1,7c(A6); BCC d73d4 (callback; no borrow when the WORD was not 0).
    case 0xd7346:if(!ov_decrement(c,0x7c,value))return false;r.pc=value?0xd73d4:0xd734e;return true;
    // ADDQ.W #2,7c(A6); MOVEA.L #d73de,A0; MOVE.W #0,D0; JSR 28ae.L.
    case 0xd734e:
        if(!ov_get(c,r.a[6],0x7c,2,value) || !ov_put(c,r.a[6],0x7c,2,(value+2U)&65535U))return false;
        r.a[0]=OV_CHILD;am_word(r.d[0],0);return am_call(c,0x28ae,0xd7362);
    // MOVE.W 1e(A6),1e(A0); MOVE.L 78(A6),78(A0); MOVE.L 7e(A6),7e(A0); ADDQ.W #1,1e(A6); MOVEA.L 78(A6),A0; LEA a(A0),A0;
    // MOVE.L A0,78(A6); TST.W (A0); BPL d73d4.
    case 0xd7362:
        if(!ov_get(c,r.a[6],0x1e,2,value) || !ov_put(c,r.a[0],0x1e,2,value&65535U))return false;
        if(!ov_get(c,r.a[6],0x78,4,value) || !ov_put(c,r.a[0],0x78,4,value))return false;
        if(!ov_get(c,r.a[6],0x7e,4,value) || !ov_put(c,r.a[0],0x7e,4,value))return false;
        if(!ov_get(c,r.a[6],0x1e,2,value) || !ov_put(c,r.a[6],0x1e,2,(value+1U)&65535U))return false;
        if(!ov_get(c,r.a[6],0x78,4,value))return false;r.a[0]=value+0xaU;
        if(!ov_put(c,r.a[6],0x78,4,r.a[0]) || !am_read(c,r.a[0],2,value))return false;
        r.pc=(value&0x8000U)?0xd738a:0xd73d4;return true;
    // MOVE.W #30,7c(A6); MOVE.L #d7396,(A6).
    case 0xd738a:if(!ov_put(c,r.a[6],0x7c,2,0x30))return false;return ov_install(c,0xd7396);
    // SUBQ.W #1,7c(A6); BNE d73d4 (callbacks d7396/d73b0).
    case 0xd7396:case 0xd73b0:
        if(!ov_decrement(c,0x7c,value))return false;r.pc=((value-1U)&65535U)?0xd73d4:r.pc+8U;return true;
    // MOVE.B #1,63(A6); MOVE.W #20,7c(A6); MOVE.L #d73b0,(A6).
    case 0xd739e:if(!ov_put(c,r.a[6],0x63,1,1) || !ov_put(c,r.a[6],0x7c,2,0x20))return false;return ov_install(c,0xd73b0);
    // MOVE.B #2,63(A6); MOVE.L #d73c4,(A6).
    case 0xd73b8:if(!ov_put(c,r.a[6],0x63,1,2))return false;return ov_install(c,0xd73c4);
    case 0xd73c4:return am_call(c,0x287e,0xd73ca); // JSR 287e.L (callback).
    // BNE d73d4: Z of the 287e CMP.W 10(A0),D0, recomputed from the live A0/D0.W (contract decision 2).
    case 0xd73ca:if(!ov_get(c,r.a[0],0x10,2,value))return false;r.pc=(value&65535U)!=(r.d[0]&65535U)?0xd73d4:0xd73ce;return true;
    case 0xd73d4:am_word(r.d[0],0xffff);r.pc=OV_SORT;return true; // MOVE.W #ffff,D0; JMP ce02.L.

    // ---- d73de (child callback): MOVE.W #3aa,D0; MOVE.B #1,D1; JSR 8ebe.L.
    case 0xd73de:am_word(r.d[0],0x3aa);am_byte(r.d[1],1);return am_call(c,0x8ebe,0xd73ec);
    case 0xd73ec:am_word(r.d[0],0x3be);am_byte(r.d[1],1);return am_call(c,0x8ebe,0xd73fa); // MOVE.W #3be,D0; MOVE.B #1,D1; JSR 8ebe.L.
    // BSET #6,15(A6); MOVE.W #0,2e(A6); MOVE.W #210,32(A6); MOVE.W #0,36(A6); MOVE.W #fff0,3a(A6); MOVE.W #1,82(A6);
    // MOVE.L #d7424,(A6).
    case 0xd73fa:
        if(!ov_bit(c,0x15,6,true) || !ov_put(c,r.a[6],0x2e,2,0) || !ov_put(c,r.a[6],0x32,2,0x210) || !ov_put(c,r.a[6],0x36,2,0) ||
           !ov_put(c,r.a[6],0x3a,2,0xfff0) || !ov_put(c,r.a[6],0x82,2,1))return false;
        return ov_install(c,0xd7424);
    case 0xd7424:return am_call(c,0x16ed2,0xd742a); // JSR 16ed2.L (callback).
    // MOVEA.L c(A6),A0; CMPI.B #2,63(A0); BEQ d747c.
    case 0xd742a:
        if(!ov_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ov_get(c,r.a[0],0x63,1,value))return false;
        r.pc=(value&255U)==2U?0xd747c:0xd7438;return true;
    // MOVEA.L 78(A6),A0; MOVEQ #0,D0; MOVEQ #0,D1; MOVE.W 6(A0),D0; MOVE.W 8(A0),D1; SUB.W 2e(A6),D0; SWAP D0; ASR.L #3,D0;
    // SUB.L 36(A6),D0; BMI d745a.
    case 0xd7438:
        if(!ov_get(c,r.a[6],0x78,4,value))return false;r.a[0]=value;r.d[0]=0;r.d[1]=0;
        if(!ov_get(c,r.a[0],6,2,value))return false;am_word(r.d[0],value);
        if(!ov_get(c,r.a[0],8,2,value))return false;am_word(r.d[1],value);
        return ov_steer(c,r.d[0],0x2e,0x36,0xd745a,0xd7458);
    case 0xd7458:r.d[0]+=1U;r.pc=0xd745a;return true; // ADDQ.L #1,D0.
    // ASR.L #1,D0; ADD.L D0,36(A6); SUB.W 32(A6),D1; SWAP D1; ASR.L #3,D1; SUB.L 3a(A6),D1; BMI d7472.
    case 0xd745a:if(!ov_half_add(c,r.d[0],0x36))return false;return ov_steer(c,r.d[1],0x32,0x3a,0xd7472,0xd7470);
    case 0xd7470:r.d[1]+=1U;r.pc=0xd7472;return true; // ADDQ.L #1,D1.
    case 0xd7472:if(!ov_half_add(c,r.d[1],0x3a))return false;r.pc=0xd74d6;return true; // ASR.L #1,D1; ADD.L D1,3a(A6); BRA d74d6.
    // MOVE.W 2e(A6),D0; ADDI.W #20,D0; CMPI.W #180,D0; BCS d7492 (unsigned).
    case 0xd747c:
        if(!ov_get(c,r.a[6],0x2e,2,value))return false;am_word(r.d[0],(value+0x20U)&65535U);
        r.pc=(r.d[0]&65535U)<0x180U?0xd7492:0xd748c;return true;
    // MOVE.W 32(A6),D0; SUBI.W #e0,D0; CMPI.W #140,D0; BCS d74a8 (unsigned).
    case 0xd7492:
        if(!ov_get(c,r.a[6],0x32,2,value))return false;am_word(r.d[0],(value-0xe0U)&65535U);
        r.pc=(r.d[0]&65535U)<0x140U?0xd74a8:0xd74a2;return true;
    // MOVE.L 2e(A6),D0; SUBI.L #a00000,D0; ASR.L #3,D0; MOVE.L D0,36(A6); MOVE.L #20000,D1; MOVE.L 32(A6),D0;
    // SUBI.L #1800000,D0; ASR.L #3,D0; BPL d74d0.
    case 0xd74a8:
        if(!ov_get(c,r.a[6],0x2e,4,value))return false;r.d[0]=ov_asr_long(value-0xa00000U,3);
        if(!ov_put(c,r.a[6],0x36,4,r.d[0]))return false;r.d[1]=0x20000;
        if(!ov_get(c,r.a[6],0x32,4,value))return false;r.d[0]=ov_asr_long(value-0x1800000U,3);
        r.pc=(r.d[0]&0x80000000U)?0xd74ce:0xd74d0;return true;
    case 0xd74ce:r.d[1]=0U-r.d[1];r.pc=0xd74d0;return true; // NEG.L D1.
    case 0xd74d0:r.d[0]+=r.d[1];if(!ov_put(c,r.a[6],0x3a,4,r.d[0]))return false;r.pc=0xd74d6;return true; // ADD.L D1,D0; MOVE.L D0,3a(A6).
    case 0xd74d6:return am_call(c,0x43ea4,0xd74dc); // JSR 43ea4.L.
    // MOVEQ #0,D0; SUB.L 82(A6),D0; ASR.L #3,D0; ADD.L D0,82(A6); MOVEA.L c(A6),A0; CMPI.B #1,63(A0); BNE d7506.
    case 0xd74dc:
        if(!ov_get(c,r.a[6],0x82,4,value))return false;r.d[0]=ov_asr_long(0U-value,3);
        if(!ov_put(c,r.a[6],0x82,4,value+r.d[0]) || !ov_get(c,r.a[6],0xc,4,other))return false;r.a[0]=other;
        if(!ov_get(c,r.a[0],0x63,1,value))return false;r.pc=(value&255U)!=1U?0xd7506:0xd74f6;return true;
    // MOVE.W 7c(A0),D0; NOT.W D0; ANDI.W #c,D0; BNE d7506.
    case 0xd74f6:
        if(!ov_get(c,r.a[0],0x7c,2,value))return false;am_word(r.d[0],(~value)&0xcU);r.pc=(r.d[0]&65535U)?0xd7506:0xd7504;return true;
    // LEA 4419e.L,A0; MOVEQ #0,D0; MOVE.B 84(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; BLE d7520 (signed WORD <= 0).
    case 0xd7506:
        r.a[0]=OV_COSINE;if(!ov_get(c,r.a[6],0x84,1,value))return false;r.d[0]=(value&255U)<<1;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
        r.pc=((value&65535U)==0U || (value&0x8000U))?0xd7520:0xd751c;return true;
    case 0xd751c:am_word(r.d[0],0U-((r.d[0]-1U)&65535U));r.pc=0xd7520;return true; // SUBQ.W #1,D0; NEG.W D0.
    // NEG.W D0; MOVE.B D0,12(A6); MOVE.B 84(A6),D0; ADDI.B #40,D0; BPL d7542.
    case 0xd7520:
        am_word(r.d[0],0U-(r.d[0]&65535U));if(!ov_put(c,r.a[6],0x12,1,r.d[0]&255U) || !ov_get(c,r.a[6],0x84,1,value))return false;
        am_byte(r.d[0],(value+0x40U)&255U);r.pc=(r.d[0]&0x80U)?0xd7532:0xd7542;return true;
    // MOVE.B 1a(A6),14(A6); BSET #0,15(A6); BRA d754e.
    case 0xd7532:
        if(!ov_get(c,r.a[6],0x1a,1,value) || !ov_put(c,r.a[6],0x14,1,value&255U) || !ov_bit(c,0x15,0,true))return false;
        r.pc=0xd754e;return true;
    // MOVE.B 19(A6),14(A6); BCLR #0,15(A6).
    case 0xd7542:
        if(!ov_get(c,r.a[6],0x19,1,value) || !ov_put(c,r.a[6],0x14,1,value&255U) || !ov_bit(c,0x15,0,false))return false;
        r.pc=0xd754e;return true;
    // MOVEQ #0,D0; MOVE.B 84(A6),D0; SUBI.B #20,D0; ADD.B D0,D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; ASR.W #4,D0;
    // BTST #0,15(A6); BEQ d7570.
    case 0xd754e:
        if(!ov_get(c,r.a[6],0x84,1,value))return false;r.d[0]=(((value-0x20U)&255U)<<1)&255U;r.d[0]<<=1;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],ov_asr_word(value,4));
        if(!ov_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&1U)?0xd756c:0xd7570;return true;
    case 0xd756c:am_word(r.d[0],(r.d[0]-0x10U)&65535U);r.pc=0xd7570;return true; // SUBI.W #10,D0.
    // MOVEQ #0,D2; BTST #0,15(A6); BNE d7598.
    case 0xd7570:r.d[2]=0;if(!ov_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&1U)?0xd7598:0xd757c;return true;
    // MOVE.B 84(A6),D2; SUBI.B #18,D2; ANDI.W #7f,D2; SUBI.W #40,D2; MULS.W D2,D2; MULU.W D2,D2; SWAP D2; MULU.W D2,D2;
    // LSL.L #4,D2; SWAP D2.
    case 0xd757c:
        if(!ov_get(c,r.a[6],0x84,1,value))return false;am_byte(r.d[2],(value-0x18U)&255U);am_word(r.d[2],r.d[2]&0x7fU);
        am_word(r.d[2],(r.d[2]-0x40U)&65535U);r.d[2]=ov_muls(r.d[2],r.d[2]);r.d[2]=ov_mulu(r.d[2],r.d[2]);am_swap(r.d[2]);
        r.d[2]=ov_mulu(r.d[2],r.d[2]);r.d[2]<<=4;am_swap(r.d[2]);r.pc=0xd7598;return true;
    // ADD.W D0,D2; BMI d75a6.
    case 0xd7598:am_word(r.d[2],(r.d[2]+r.d[0])&65535U);r.pc=(r.d[2]&0x8000U)?0xd75a6:0xd759e;return true;
    case 0xd759e:am_word(r.d[1],0x200);r.pc=0xd75ac;return true; // MOVE.W #200,D1; BRA d75ac.
    case 0xd75a6:am_word(r.d[2],0U-(r.d[2]&65535U));am_word(r.d[1],0x201);r.pc=0xd75ac;return true; // NEG.W D2; MOVE.W #201,D1.
    // MOVE.B 14(A6),D0; JSR 8cda.L.
    case 0xd75ac:if(!ov_get(c,r.a[6],0x14,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x8cda,0xd75b6);
    // MOVEA.L 78(A6),A0; MOVE.L (A0),D7; BNE d75c4.
    case 0xd75b6:
        if(!ov_get(c,r.a[6],0x78,4,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],4,value))return false;r.d[7]=value;
        r.pc=value?0xd75c4:0xd75c0;return true;
    case 0xd75c0:if(!ov_get(c,r.a[6],0x7e,4,value))return false;r.d[7]=value;r.pc=0xd75c4;return true; // MOVE.L 7e(A6),D7.
    case 0xd75c4:r.d[0]=0;return am_call(c,0x16ea4,0xd75cc); // MOVEQ #0,D0; JSR 16ea4.L.
    default:return am_error(c,"unsupported animation objects u04 PC");
    }
}
}
