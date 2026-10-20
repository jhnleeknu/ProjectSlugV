#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OB2E_ANGLE_TABLE=0x44502;  // 4462a: LEA 44502(PC),A0 (BYTE table, fixed ROM, live bus).
const std::uint32_t OB2E_RANK_TEXT=0xe637a;    // e6792: LEA e637a(PC),A0; MOVEA.L (A0,D0.W),A0 (LONG pointers of the rank labels).
const std::uint32_t OB2E_CHILD_SCRIPT=0xe63e4; // e68d4: LEA e63e4(PC),A4; MOVEA.L (A4,D0.W),A1 (two LONG script pointers).
const std::uint32_t OB2E_RECORDS=0x10f02e;     // e67d6 / e6804 / e685a / e6864: LEA 10f02e.l (8-byte ranking records, work RAM).
const std::uint32_t OB2E_BANK_98=0x200098;     // 4dbe2: MOVE.L 200098.l,22(A6) (banked LONG through the live bus).
const std::uint32_t OB2E_2986_PARENT=0x100bf4; // 3ac38 / 3ac6a: MOVEA.L #100bf4,A1 (2986 parent node).
std::uint32_t ob2e_w(std::uint32_t value) {return value&65535U;}
// ASR.L #n (1 <= n <= 8): the sign bit refills the vacated bits (explicit, no signed shift).
std::uint32_t ob2e_asr_l(std::uint32_t value,unsigned int n) {
    const std::uint32_t fill=(value&0x80000000U)!=0U?~(0xffffffffU>>n):0U;return (value>>n)|fill;
}
bool ob2e_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob2e_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// ADDQ/SUBQ #delta,d16(A6) on a BYTE or WORD field (modular; the flags are consumed by the caller of this helper only through `old`).
bool ob2e_add(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t delta,std::uint32_t& old) {
    return ob2e_get(c,c.s.a[6],displacement,size,old) && ob2e_put(c,c.s.a[6],displacement,size,old+delta);
}
// BTST.B #bit,d16(A6): true when the bit is 1.
bool ob2e_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob2e_get(c,c.s.a[6],displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// ANDI.B / AND.B mask into d16(A6).
bool ob2e_and(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t mask) {
    std::uint32_t value=0;return ob2e_get(c,c.s.a[6],displacement,1,value) && ob2e_put(c,c.s.a[6],displacement,1,value&mask);
}
// Bcc on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob2e_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b2e caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.B (A0)+,D2; JSR e84c8.l (one rank-row character).
bool ob2e_char(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[0],1,value))return false;am_byte(c.s.d[2],value);c.s.a[0]+=1U;return am_call(c,0xe84c8,return_pc);
}
// MOVE.W (A7),D0; MULU.W #scale,D0 (WORD x constant, 32-bit result).
bool ob2e_row_scaled(AnimationMachineContext& c,std::uint32_t scale) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[7],2,value))return false;am_word(c.s.d[0],value);c.s.d[0]=ob2e_w(c.s.d[0])*scale;return true;
}
// Signed WORD compare D <= / < limit (CMPI.W #limit,Dn; BLE / BLT) for a small positive limit.
bool ob2e_word_le(std::uint32_t reg,std::uint32_t limit) {const std::uint32_t w=ob2e_w(reg);return (w&0x8000U)!=0U || w<=limit;}
bool ob2e_word_lt(std::uint32_t reg,std::uint32_t limit) {const std::uint32_t w=ob2e_w(reg);return (w&0x8000U)!=0U || w<limit;}
// 44602 / 4461c / 4460a: ASR.W #1,Dv; SMI.B Ds; EOR.B Ds,Dv; SUB.B Ds,Dv (the BYTE magnitude of the halved WORD; Ds.B = ff when negative).
void ob2e_half_abs(std::uint32_t& v,std::uint32_t& s) {
    const std::uint32_t w=ob2e_w(v);const std::uint32_t half=(w>>1)|(w&0x8000U);am_word(v,half);
    am_byte(s,(half&0x8000U)!=0U?0xffU:0U);am_byte(v,(v^s)&255U);am_byte(v,(v-s)&255U);
}
}
// Objects B2e (109 block starts): the script callbacks of table 4a500 (index 23 3abee 19, 24 3b656 5, 25 3b458 2, 26 3b648 1, 27 3b62a 4), the shared angle
// leaf 44602 (6), the child-spawn helper 4db18 (2) with its 28ae child 4dbdc (16), and the demo-end ranking child e66aa (34 + 8 + 11 with its 28ae child e68c6)
// with the shared text leaf e89da (1). TRAP #f at e6836 / e6896 stays unrouted (checked boundary); e6890 MOVE.W #1,1.w is an odd WORD write (checked error).
// The indirect JSR (A1) of 4dc40 goes to the live LONG 7a(A6). Data reads (44502 angle bytes, e637a rank text pointers, e63e4 child scripts, 10f02e records,
// banked 200098) go through the live bus without a bound check. Known C: the five consumers 3ac76 (2986), 3b666 (28ae), 4dc34 (49fc6), 4dc46 (the live
// JSR (A1) callee) and 4dc50 (288c); no block produces a known C for another block. Callees 2986 28ae 288c 3b288 3b48c 4970a 43e34 49290 49f8c 49fc6 4d900
// 8ebe 8e82 e7c36 1a5a4 47570 8c16 e84c8 3670 49260 49a58 3918 and the exits 4c2fa 2a00 are routed elsewhere. No X / port / bank change.
bool animation_objects_b2e_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool bit=false;
    switch(r.pc) {
    // ---- 3abee (callback 23): TST.B a6(A6); BNE.W 3ac12.
    case 0x3abee:if(!ob2e_get(c,r.a[6],0xa6,1,value))return false;r.pc=value!=0U?0x3ac12:0x3abf6;return true;
    case 0x3abf6:if(!ob2e_bit(c,0x9d,4,bit))return false;r.pc=bit?0x3ac00:0x3ac12;return true;      // BTST.B #4,9d(A6); BEQ.W 3ac12.
    // ANDI.B #ef,9d(A6); ANDI.B #ef,9e(A6); MOVE.B #5,a6(A6).
    case 0x3ac00:if(!ob2e_and(c,0x9d,0xef) || !ob2e_and(c,0x9e,0xef) || !ob2e_put(c,r.a[6],0xa6,1,5))return false;r.pc=0x3ac12;return true;
    case 0x3ac12:if(!ob2e_get(c,r.a[6],0xa6,1,value))return false;r.pc=value!=0U?0x3ac1c:0x3ac1a;return true;   // TST.B a6(A6); BNE.W 3ac1c.
    case 0x3ac1a:case 0x3acd4:case 0x4dc5e:case 0xe6746:case 0xe6782:case 0xe6882:case 0xe6938:return am_return(c);   // RTS.
    // SUBQ.B #1,a6(A6); MOVE.B a8(A6),D7; ANDI.B #3,D7; BNE.W 3ac58.
    case 0x3ac1c:
        if(!ob2e_add(c,0xa6,1,0xffU,value) || !ob2e_get(c,r.a[6],0xa8,1,value))return false;
        am_byte(r.d[7],value&3U);r.pc=(value&3U)!=0U?0x3ac58:0x3ac2c;return true;
    // MOVE.L A0,-(A7); MOVEA.L #3ad48,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l (child 3ad48 is data).
    case 0x3ac2c:if(!am_push(c,4,r.a[0]))return false;r.a[0]=0x3ad48;am_word(r.d[0],0x1e);r.a[1]=OB2E_2986_PARENT;return am_call(c,0x2986,0x3ac44);
    case 0x3ac44:return am_call(c,0x3b48c,0x3ac48);                                  // JSR 3b48c(PC).
    case 0x3ac48:am_word(r.d[0],0xfff0);am_word(r.d[1],r.d[1]+0x20U);return am_call(c,0x4970a,0x3ac56);   // MOVE.W #fff0,D0; ADDI.W #20,D1; JSR 4970a.l.
    case 0x3ac56:if(!am_pop(c,4,value))return false;r.a[0]=value;r.pc=0x3ac58;return true;              // MOVEA.L (A7)+,A0.
    // MOVE.B #6,a3(A6); MOVE.L A0,-(A7); MOVEA.L #42d9c,A0; MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.l (child 42d9c is data).
    case 0x3ac58:
        if(!ob2e_put(c,r.a[6],0xa3,1,6) || !am_push(c,4,r.a[0]))return false;
        r.a[0]=0x42d9c;am_word(r.d[0],0xa);r.a[1]=OB2E_2986_PARENT;return am_call(c,0x2986,0x3ac76);
    // MOVEA.L (A7)+,A1; BCC.W 3acd4 (C returned by 2986; MOVEA keeps it).
    case 0x3ac76:
        if(!am_pop(c,4,value))return false;r.a[1]=value;return ob2e_carry(c,0x3acd4,0x3ac7c);
    // ADDQ.B #1,a8(A6); MOVE.W (A1)+,D7; MOVE.W (A1)+,D2; MOVE.W (A1)+,D3; BSR.W 3b48c.
    case 0x3ac7c:
        if(!ob2e_add(c,0xa8,1,1,value))return false;
        if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[7],value);r.a[1]+=2U;
        if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[2],value);r.a[1]+=2U;
        if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[3],value);r.a[1]+=2U;
        return am_call(c,0x3b48c,0x3ac8a);
    // ADD.W D0,D2; ADD.W D1,D3; BTST.B #0,15(A6); BEQ.W 3aca0.
    case 0x3ac8a:am_word(r.d[2],r.d[2]+r.d[0]);am_word(r.d[3],r.d[3]+r.d[1]);if(!ob2e_bit(c,0x15,0,bit))return false;r.pc=bit?0x3ac98:0x3aca0;return true;
    // NEG.B D7; ADDI.B #80,D7; NEG.W D2.
    case 0x3ac98:am_byte(r.d[7],0x100U-(r.d[7]&255U));am_byte(r.d[7],r.d[7]+0x80U);am_word(r.d[2],0x10000U-ob2e_w(r.d[2]));r.pc=0x3aca0;return true;
    // MOVE.B D7,76(A0); MOVEQ #2,D7; MOVE.B 76(A0),D0; ANDI.B #3f,D0; BNE.W 3acc6.
    case 0x3aca0:
        if(!ob2e_put(c,r.a[0],0x76,1,r.d[7]))return false;r.d[7]=2;
        if(!ob2e_get(c,r.a[0],0x76,1,value))return false;am_byte(r.d[0],value&0x3fU);r.pc=(value&0x3fU)!=0U?0x3acc6:0x3acb2;return true;
    // MOVEQ #0,D0; MOVE.B a8(A6),D0; DIVU.W #3,D0; SWAP D0; SUBQ.W #1,D0; MULS.W D7,D0; ADD.B D0,76(A0).
    case 0x3acb2: {
        if(!ob2e_get(c,r.a[6],0xa8,1,value))return false;
        // The dividend is the BYTE 0..ff: the quotient <= 55 fits the WORD (no DIVU overflow), the divisor is the constant 3.
        const std::uint32_t quotient=value/3U,remainder=value%3U;r.d[0]=(remainder<<16)|quotient;am_swap(r.d[0]);
        am_word(r.d[0],r.d[0]-1U);
        r.d[0]=am_extend_word(ob2e_w(r.d[0]))*am_extend_word(ob2e_w(r.d[7]));   // MULS.W: low 32 bits of the signed product (modular unsigned multiply).
        if(!ob2e_get(c,r.a[0],0x76,1,value) || !ob2e_put(c,r.a[0],0x76,1,value+r.d[0]))return false;r.pc=0x3acc6;return true;
    }
    // MOVE.B 60(A6),60(A0); MOVEQ #2,D0; JMP 4c2fa.l.
    case 0x3acc6:if(!ob2e_get(c,r.a[6],0x60,1,value) || !ob2e_put(c,r.a[0],0x60,1,value))return false;r.d[0]=2;r.pc=0x4c2fa;return true;
    // ---- 3b458 (callback 25): MOVEM.L 36(A6),D0-D1; ASR.L #8,D0; ASR.L #8,D1; ASR.L #1,D0; ASR.L #4,D1; JSR 44602.l.
    case 0x3b458:
        if(!ob2e_get(c,r.a[6],0x36,4,r.d[0]) || !ob2e_get(c,r.a[6],0x3a,4,r.d[1]))return false;
        r.d[0]=ob2e_asr_l(ob2e_asr_l(r.d[0],8),1);r.d[1]=ob2e_asr_l(ob2e_asr_l(r.d[1],8),4);return am_call(c,0x44602,0x3b46c);
    // ANDI.B #7f,D0; SUB.B a1(A6),D0; ASR.B #3,D0; MOVE.B a1(A6),D1; ADD.B D0,D1; MOVE.B D1,a1(A6); LSR.B #3,D1; MOVE.B D1,98(A6); MOVE.B D1,a2(A6); RTS.
    case 0x3b46c: {
        if(!ob2e_get(c,r.a[6],0xa1,1,value))return false;
        am_byte(r.d[0],r.d[0]&0x7fU);am_byte(r.d[0],r.d[0]-value);
        const std::uint32_t b=r.d[0]&255U;am_byte(r.d[0],(b>>3)|((b&0x80U)!=0U?0xe0U:0U));
        am_byte(r.d[1],value);am_byte(r.d[1],r.d[1]+r.d[0]);if(!ob2e_put(c,r.a[6],0xa1,1,r.d[1]))return false;
        am_byte(r.d[1],(r.d[1]&255U)>>3);
        if(!ob2e_put(c,r.a[6],0x98,1,r.d[1]) || !ob2e_put(c,r.a[6],0xa2,1,r.d[1]))return false;return am_return(c);
    }
    // ---- 3b62a (callback 27): MOVE.L (A0),D0; CLR.W D0; BTST.B #0,15(A6); BEQ.W 3b63a / NEG.L D0.
    case 0x3b62a:
        if(!am_read(c,r.a[0],4,value))return false;r.d[0]=value&0xffff0000U;if(!ob2e_bit(c,0x15,0,bit))return false;r.pc=bit?0x3b638:0x3b63a;return true;
    case 0x3b638:r.d[0]=0U-r.d[0];r.pc=0x3b63a;return true;
    case 0x3b63a:if(!ob2e_put(c,r.a[6],0x64,4,r.d[0]))return false;return am_call(c,0x3b288,0x3b642);   // MOVE.L D0,64(A6); JSR 3b288(PC).
    case 0x3b642:if(!ob2e_put(c,r.a[6],0x64,4,0))return false;return am_return(c);                     // CLR.L 64(A6); RTS.
    // ---- 3b648 (callback 26): MOVE.W (A0),D0; NOT.W D0; AND.B D0,9d(A6); AND.B D0,9e(A6); RTS.
    case 0x3b648:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],~value);
        if(!ob2e_and(c,0x9d,r.d[0]&255U) || !ob2e_and(c,0x9e,r.d[0]&255U))return false;return am_return(c);
    // ---- 3b656 (callback 24): MOVEA.L #d3c9e,A0; MOVE.W #1e,D0; JSR 28ae.l (child d3c9e is data).
    case 0x3b656:r.a[0]=0xd3c9e;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0x3b666);
    case 0x3b666:return ob2e_carry(c,0x3b67c,0x3b66a);                              // BCC.W 3b67c (C returned by 28ae).
    case 0x3b66a:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0x3b678);   // MOVE.W #0,D0; MOVE.W #0,D1; JSR 4970a.l.
    case 0x3b678:r.pc=0x3b67c;return true;   // ORI.B #1,CCR: the C is overwritten by the MOVE.W of 3b67c (no consumer; stays Unknown).
    // MOVE.W #1001,68(A0); MOVE.W #1001,1e(A0); RTS.
    case 0x3b67c:if(!ob2e_put(c,r.a[0],0x68,2,0x1001) || !ob2e_put(c,r.a[0],0x1e,2,0x1001))return false;return am_return(c);
    // ---- 44602: ASR.W #1,D0; SMI.B D2; EOR.B D2,D0; SUB.B D2,D0; (same D1 / D3); MOVE.W #ff,D4; AND.W D4,D1; BNE.W 44620.
    case 0x44602:
        ob2e_half_abs(r.d[0],r.d[2]);ob2e_half_abs(r.d[1],r.d[3]);am_word(r.d[4],0xff);am_word(r.d[1],r.d[1]&r.d[4]);
        r.pc=ob2e_w(r.d[1])!=0U?0x44620:0x4461c;return true;
    case 0x4461c:r.d[0]=0;r.pc=0x4463c;return true;                                // MOVEQ #0,D0; BRA.B 4463c.
    case 0x44620:am_word(r.d[0],r.d[0]&r.d[4]);r.pc=ob2e_w(r.d[0])!=0U?0x4462a:0x44626;return true;   // AND.W D4,D0; BNE.W 4462a.
    case 0x44626:r.d[0]=0x40;r.pc=0x4463c;return true;                             // MOVEQ #40,D0; BRA.B 4463c.
    // LEA 44502(PC),A0; MOVE.B (A0,D0.W),D0; MOVE.B (A0,D1.W),D1; SUB.W D0,D1; MOVE.B -80(A0,D1.W),D0 (live bus, no bound check).
    case 0x4462a:
        r.a[0]=OB2E_ANGLE_TABLE;
        if(!am_read(c,am_index(r.a[0],r.d[0]),1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,am_index(r.a[0],r.d[1]),1,value))return false;am_byte(r.d[1],value);
        am_word(r.d[1],r.d[1]-r.d[0]);
        if(!am_read(c,am_index(r.a[0]-0x80U,r.d[1]),1,value))return false;am_byte(r.d[0],value);r.pc=0x4463c;return true;
    // EOR.B D2,D3; EOR.B D3,D0; SUB.B D3,D0; ANDI.B #80,D2; ADD.B D2,D0; RTS.
    case 0x4463c:
        am_byte(r.d[3],r.d[3]^r.d[2]);am_byte(r.d[0],r.d[0]^r.d[3]);am_byte(r.d[0],r.d[0]-r.d[3]);am_byte(r.d[2],r.d[2]&0x80U);am_byte(r.d[0],r.d[0]+r.d[2]);
        return am_return(c);
    // ---- 4db18: MOVEA.L #0,A0; MOVE.L A0,-(A7); MOVEM.W D0-D1,-(A7) (D0.W at the lower address); MOVEA.L #4dbdc,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x4db18:
        r.a[0]=0;if(!am_push(c,4,0) || !am_push(c,2,ob2e_w(r.d[1])) || !am_push(c,2,ob2e_w(r.d[0])))return false;
        r.a[0]=0x4dbdc;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x4db34);
    // MOVE.W (A7)+,76(A0); MOVE.W (A7)+,78(A0); MOVE.L (A7)+,7a(A0); RTS.
    case 0x4db34:
        if(!am_pop(c,2,value) || !ob2e_put(c,r.a[0],0x76,2,value) || !am_pop(c,2,value) || !ob2e_put(c,r.a[0],0x78,2,value) ||
            !am_pop(c,4,value) || !ob2e_put(c,r.a[0],0x7a,4,value))return false;
        return am_return(c);
    // ---- 4dbdc (28ae child): MOVE.W #ea,20(A6); MOVE.L 200098.l,22(A6); MOVEA.L #4dd1a,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x4dbdc:
        if(!ob2e_put(c,r.a[6],0x20,2,0xea) || !am_read(c,OB2E_BANK_98,4,value) || !ob2e_put(c,r.a[6],0x22,4,value))return false;
        r.a[1]=0x4dd1a;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x4dbfa);
    case 0x4dbfa:am_word(r.d[0],0x3b0);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x4dc08);   // MOVE.W #3b0,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVE.W #fff1,68(A6); MOVE.W #fff1,1e(A6); MOVE.W 76(A6),D0; MOVE.W 78(A6),D1; JSR 49290.l.
    case 0x4dc08:
        if(!ob2e_put(c,r.a[6],0x68,2,0xfff1) || !ob2e_put(c,r.a[6],0x1e,2,0xfff1))return false;
        if(!ob2e_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);
        if(!ob2e_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[1],value);return am_call(c,0x49290,0x4dc22);
    case 0x4dc22:if(!ob2e_put(c,r.a[6],0,4,0x4dc28))return false;r.pc=0x4dc28;return true;   // MOVE.L #4dc28,(A6).
    case 0x4dc28:return am_call(c,0x43e34,0x4dc2e);                                // JSR 43e34.l.
    case 0x4dc2e:return am_call(c,0x49fc6,0x4dc34);                                // JSR 49fc6.l.
    case 0x4dc34:case 0x4dc46:return ob2e_carry(c,r.pc+4U,0x4dc60);              // BCS.W 4dc60 (C of 49fc6 / of the live JSR (A1) callee).
    case 0x4dc38:if(!ob2e_get(c,r.a[6],0x7a,4,value))return false;r.pc=value==0U?0x4dc4a:0x4dc40;return true;   // TST.L 7a(A6); BEQ.W 4dc4a.
    case 0x4dc40:if(!ob2e_get(c,r.a[6],0x7a,4,value))return false;r.a[1]=value;return am_call(c,r.a[1],0x4dc46);   // MOVEA.L 7a(A6),A1; JSR (A1) (live).
    case 0x4dc4a:return am_call(c,0x288c,0x4dc50);                                 // JSR 288c.l.
    case 0x4dc50:return ob2e_carry(c,0x4dc60,0x4dc54);                             // BCC.W 4dc60 (C of 288c).
    case 0x4dc54:return am_call(c,0x4d900,0x4dc58);                                // JSR 4d900(PC).
    case 0x4dc58:r.pc=(r.d[0]&0x80U)!=0U?0x4dc60:0x4dc5e;return true;            // TST.B D0; BMI.W 4dc60.
    case 0x4dc60:r.pc=0x2a00;return true;                                         // JMP 2a00.l.
    // ---- e66aa (28ae child of C2 c6a6 / c926): JSR e6756(PC).
    case 0xe66aa:return am_call(c,0xe6756,0xe66ae);
    case 0xe66ae:r.a[0]=0xe68c6;am_word(r.d[0],0x14);return am_call(c,0x28ae,0xe66be);   // MOVEA.L #e68c6,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0xe66be:am_word(r.d[0],0xa0);am_word(r.d[1],0x80);return am_call(c,0x49260,0xe66cc);   // MOVE.W #a0,D0; MOVE.W #80,D1; JSR 49260.l.
    // MOVE.W #5a,76(A6); CLR.W 7e(A6); CLR.W 78(A6); CLR.W 7a(A6); CLR.B 80(A6); MOVE.W #1,7c(A6); MOVE.L #e66ee,(A6).
    case 0xe66cc:
        if(!ob2e_put(c,r.a[6],0x76,2,0x5a) || !ob2e_put(c,r.a[6],0x7e,2,0) || !ob2e_put(c,r.a[6],0x78,2,0) || !ob2e_put(c,r.a[6],0x7a,2,0) ||
            !ob2e_put(c,r.a[6],0x80,1,0) || !ob2e_put(c,r.a[6],0x7c,2,1) || !ob2e_put(c,r.a[6],0,4,0xe66ee))return false;
        r.pc=0xe66ee;return true;
    case 0xe66ee:if(!ob2e_get(c,r.a[6],0x80,1,value))return false;r.pc=value==0U?0xe6746:0xe66f6;return true;   // TST.B 80(A6); BEQ.W e6746.
    case 0xe66f6:return am_call(c,0xe6898,0xe66fa);                                // JSR e6898(PC).
    case 0xe66fa:if(!ob2e_add(c,0x7c,2,0xffffU,value))return false;r.pc=ob2e_w(value)==0U?0xe6702:0xe6746;return true;   // SUBQ.W #1,7c(A6); BCC.W e6746.
    // CLR.W 7c(A6); ADDQ.W #1,7a(A6); CMPI.W #1,7a(A6); BLS.W e6726 (unsigned <= 1).
    case 0xe6702:
        if(!ob2e_put(c,r.a[6],0x7c,2,0) || !ob2e_add(c,0x7a,2,1,value))return false;r.pc=ob2e_w(value+1U)<=1U?0xe6726:0xe6714;return true;
    case 0xe6714:if(!ob2e_get(c,r.a[6],0x78,2,value))return false;r.pc=ob2e_w(value)==9U?0xe6722:0xe671e;return true;   // CMPI.W #9,78(A6); BEQ.W e6722.
    case 0xe671e:if(!ob2e_add(c,0x78,2,1,value))return false;r.pc=0xe6722;return true;   // ADDQ.W #1,78(A6).
    case 0xe6722:if(!ob2e_put(c,r.a[6],0x7a,2,0))return false;r.pc=0xe6726;return true;  // CLR.W 7a(A6).
    case 0xe6726:if(!ob2e_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);return am_call(c,0xe6784,0xe672e);   // MOVE.W 78(A6),D0; JSR e6784(PC).
    case 0xe672e:if(!ob2e_get(c,r.a[6],0x78,2,value))return false;r.pc=ob2e_w(value)!=9U?0xe673e:0xe6738;return true;   // CMPI.W #9,78(A6); BNE.W e673e.
    case 0xe6738:if(!ob2e_put(c,r.a[6],0,4,0xe673e))return false;r.pc=0xe673e;return true;   // MOVE.L #e673e,(A6).
    case 0xe673e:if(!ob2e_add(c,0x76,2,0xffffU,value))return false;r.pc=ob2e_w(value-1U)==0U?0xe6748:0xe6746;return true;   // SUBQ.W #1,76(A6); BEQ.W e6748.
    // MOVEA.L c(A6),A0; ST.B 62(A0) (the controller's end request); JMP 2a00.l (self delete).
    case 0xe6748:if(!ob2e_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ob2e_put(c,r.a[0],0x62,1,0xff))return false;r.pc=0x2a00;return true;
    // ---- e6756 (screen preparation): JSR 8e82.l / JSR e7c36.l / LEA e631a(PC),A0; MOVEQ #0,D0; JSR 1a5a4.l / JSR 47570.l /
    // MOVEQ #0,D0; MOVEQ #0,D1; MOVEQ #0,D2; MOVEQ #8,D3; JSR 8c16.l / RTS.
    case 0xe6756:return am_call(c,0x8e82,0xe675c);
    case 0xe675c:return am_call(c,0xe7c36,0xe6762);
    case 0xe6762:r.a[0]=0xe631a;r.d[0]=0;return am_call(c,0x1a5a4,0xe676e);
    case 0xe676e:return am_call(c,0x47570,0xe6774);
    case 0xe6774:r.d[0]=0;r.d[1]=0;r.d[2]=0;r.d[3]=8;return am_call(c,0x8c16,0xe6782);
    // ---- e6784 (rank row k = D0.W): MOVE.W D0,-(A7); MOVE.W (A7),D7; JSR e682e(PC).
    case 0xe6784:if(!am_push(c,2,ob2e_w(r.d[0])) || !am_read(c,r.a[7],2,value))return false;am_word(r.d[7],value);return am_call(c,0xe682e,0xe678c);
    // SUBQ.W #1,D0; ADD.W D0,D0 (x2); LEA e637a(PC),A0; MOVEA.L (A0,D0.W),A0; MOVE.W (A7),D0; MULU.W #2,D0; ADDI.W #70a8,D0; MOVE.W #441,D1;
    // MOVE.B (A0)+,D2; JSR e84c8.l (no bound check on the rank index: live bus).
    case 0xe678c:
        am_word(r.d[0],r.d[0]-1U);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);r.a[0]=OB2E_RANK_TEXT;
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;
        if(!ob2e_row_scaled(c,2))return false;am_word(r.d[0],r.d[0]+0x70a8U);am_word(r.d[1],0x441);return ob2e_char(c,0xe67b0);
    case 0xe67b0:am_word(r.d[1],3);am_word(r.d[0],r.d[0]+1U);return ob2e_char(c,0xe67c0);   // MOVE.W #3,D1; ADDI.W #1,D0; MOVE.B (A0)+,D2; JSR e84c8.l.
    case 0xe67c0:return ob2e_char(c,0xe67c8);
    case 0xe67c8:return ob2e_char(c,0xe67d0);
    // MOVE.W (A7),D0; MULU.W #8,D0; LEA 10f02e.l,A1; LEA (A1,D0.W),A0; MOVE.W (A7),D0; MULU.W #2,D0; ADDI.W #7168,D0; MOVE.W #441,D1; MOVEQ #8,D4;
    // LEA e84c8.l,A1; MOVEQ #0,D3; JSR 3670.l (the score digits).
    case 0xe67d0:
        if(!ob2e_row_scaled(c,8))return false;r.a[1]=OB2E_RECORDS;r.a[0]=am_index(r.a[1],r.d[0]);
        if(!ob2e_row_scaled(c,2))return false;am_word(r.d[0],r.d[0]+0x7168U);am_word(r.d[1],0x441);r.d[4]=8;r.a[1]=0xe84c8;r.d[3]=0;
        return am_call(c,0x3670,0xe67fe);
    // MOVE.W (A7),D0; MULU.W #8,D0; LEA 10f02e.l,A1; LEA 4(A1,D0.W),A0; MOVE.W (A7),D0; MULU.W #2,D0; ADDI.W #73a8,D0; MOVE.W #441,D1; MOVEQ #2,D7.
    case 0xe67fe:
        if(!ob2e_row_scaled(c,8))return false;r.a[1]=OB2E_RECORDS;r.a[0]=am_index(r.a[1],r.d[0])+4U;
        if(!ob2e_row_scaled(c,2))return false;am_word(r.d[0],r.d[0]+0x73a8U);am_word(r.d[1],0x441);r.d[7]=2;r.pc=0xe681e;return true;
    case 0xe681e:return ob2e_char(c,0xe6826);                                      // MOVE.B (A0)+,D2; JSR e84c8.l (the name letters).
    case 0xe6826:am_word(r.d[7],r.d[7]-1U);r.pc=ob2e_w(r.d[7])!=0xffffU?0xe681e:0xe682a;return true;   // DBRA D7,e681e.
    case 0xe682a:if(!am_pop(c,2,value))return false;am_word(r.d[0],value);return am_return(c);         // MOVE.W (A7)+,D0; RTS.
    // ---- e682e (rank of record D7.W): CMPI.W #a,D7; BLT.W e6854 (signed); else the TRAP #f at e6836 ("RANK_IN Record Number Error", boundary).
    case 0xe682e:r.pc=ob2e_word_lt(r.d[7],10)?0xe6854:0xe6836;return true;
    // MOVE.W D7,D0; MULU.W #8,D0; LEA 10f02e.l,A0; ADDA.W D0,A0; ADDQ.W #1,D7; LEA 10f02e.l,A1; MOVEQ #1,D0; MOVEQ #1,D1; MOVE.L (A0),D3.
    case 0xe6854:
        am_word(r.d[0],r.d[7]);r.d[0]=ob2e_w(r.d[0])*8U;r.a[0]=am_index(OB2E_RECORDS,r.d[0]);am_word(r.d[7],r.d[7]+1U);r.a[1]=OB2E_RECORDS;
        r.d[0]=1;r.d[1]=1;if(!am_read(c,r.a[0],4,value))return false;r.d[3]=value;r.pc=0xe6870;return true;
    case 0xe6870:if(!am_read(c,r.a[1],4,value))return false;r.d[4]=value;r.pc=r.d[3]>=r.d[4]?0xe687c:0xe6878;return true;   // MOVE.L (A1),D4; CMP.L D4,D3; BCC.W e687c.
    case 0xe6878:am_word(r.d[0],r.d[1]);am_word(r.d[0],r.d[0]+1U);r.pc=0xe687c;return true;   // MOVE.W D1,D0; ADDQ.W #1,D0.
    case 0xe687c:r.pc=ob2e_w(r.d[1])!=ob2e_w(r.d[7])?0xe6884:0xe6882;return true;   // CMP.W D7,D1; BNE.W e6884.
    // ADDA.W #8,A1; ADDQ.W #1,D1; CMPI.W #a,D1; BLE.B e6870 (signed).
    case 0xe6884:r.a[1]+=8U;am_word(r.d[1],r.d[1]+1U);r.pc=ob2e_word_le(r.d[1],10)?0xe6870:0xe6890;return true;
    // MOVE.W #1,1.w: an odd WORD write (address error on the 68000) -> the checked alignment error; then the TRAP #f at e6896 (boundary).
    case 0xe6890:if(!am_write(c,0x1,2,1))return false;r.pc=0xe6896;return true;
    // ---- e6898 (title): MOVE.W #7085,D0; MOVE.W #441,D1; LEA e63d2(PC),A0; JSR e89da.l / MOVE.W #71a5,D0; LEA e63d7(PC),A0; JSR e89da.l /
    // MOVE.W #72c5,D0; LEA e63dc(PC),A0; JMP e89da.l.
    case 0xe6898:am_word(r.d[0],0x7085);am_word(r.d[1],0x441);r.a[0]=0xe63d2;return am_call(c,0xe89da,0xe68aa);
    case 0xe68aa:am_word(r.d[0],0x71a5);r.a[0]=0xe63d7;return am_call(c,0xe89da,0xe68b8);
    case 0xe68b8:am_word(r.d[0],0x72c5);r.a[0]=0xe63dc;r.pc=0xe89da;return true;
    case 0xe89da:r.a[1]=0xe84c8;r.pc=0x3918;return true;                          // LEA e84c8(PC),A1; JMP 3918.l.
    // ---- e68c6 (28ae child of e66aa): JSR 49a58.l.
    case 0xe68c6:return am_call(c,0x49a58,0xe68cc);
    // ANDI.W #1,D0; ADD.W D0,D0 (x2); LEA e63e4(PC),A4; MOVE.W #152,20(A6); MOVEA.L (A4,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xe68cc:
        am_word(r.d[0],r.d[0]&1U);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);r.a[4]=OB2E_CHILD_SCRIPT;
        if(!ob2e_put(c,r.a[6],0x20,2,0x152) || !am_read(c,am_index(r.a[4],r.d[0]),4,value))return false;r.a[1]=value;
        am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xe68ec);
    case 0xe68ec:am_word(r.d[0],0xe95);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xe68fa);   // MOVE.W #e95,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVE.W #0,68(A6); MOVE.W #0,1e(A6); CLR.B 12(A6); JSR 43e34.l.
    case 0xe68fa:
        if(!ob2e_put(c,r.a[6],0x68,2,0) || !ob2e_put(c,r.a[6],0x1e,2,0) || !ob2e_put(c,r.a[6],0x12,1,0))return false;return am_call(c,0x43e34,0xe6910);
    case 0xe6910:if(!ob2e_put(c,r.a[6],0,4,0xe6916))return false;r.pc=0xe6916;return true;   // MOVE.L #e6916,(A6).
    case 0xe6916:if(!ob2e_add(c,0x12,1,0x10,value))return false;r.pc=(value&255U)+0x10U>0xffU?0xe6920:0xe6932;return true;   // ADDI.B #10,12(A6); BCC.W e6932.
    // ST.B 12(A6); MOVEA.L c(A6),A0; ST.B 80(A0) (the parent starts the display); MOVE.L #e6932,(A6).
    case 0xe6920:
        if(!ob2e_put(c,r.a[6],0x12,1,0xff) || !ob2e_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob2e_put(c,r.a[0],0x80,1,0xff) || !ob2e_put(c,r.a[6],0,4,0xe6932))return false;r.pc=0xe6932;return true;
    case 0xe6932:return am_call(c,0x49fc6,0xe6938);                                // JSR 49fc6.l (its C is not read).
    default:return am_error(c,"unsupported animation objects b2e PC");
    }
}
}
