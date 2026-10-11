#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (MOVE.L #, LEA d16(PC), LEA xxx.L).
const std::uint32_t OU_ITEM_TABLE=0xb516c;   // b4fdc LEA b516c(PC),A0 (item record LONG table, fixed ROM)
const std::uint32_t OU_SLOT_TABLE=0x4a9e2;   // 4b646 LEA 4a9e2(PC),A1 (BYTE table, fixed ROM)
const std::uint32_t OU_DEBUG_FLAGS=0x10f000; // 4b69e BTST #6,10f000.L
const std::uint32_t OU_SCROLL_A=0x10b1d6;    // dd512 LEA 10b1d6.L,A1
const std::uint32_t OU_SCROLL_B=0x10d256;    // dd54c LEA 10d256.L,A1
bool ou_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Signed views of a WORD and a LONG (explicit two's complement, no implementation-defined conversion).
std::int32_t ou_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
std::int64_t ou_signed_long(std::uint32_t value) {
    return (value&0x80000000U)?static_cast<std::int64_t>(value)-0x100000000LL:static_cast<std::int64_t>(value);
}
// BSET/BCLR on a memory BYTE: read, change bit (n mod 8), write.
bool ou_bit(AnimationMachineContext& c,std::uint32_t address,std::uint32_t bit,bool set) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    return am_write(c,address,1,set?((value|mask)&255U):(value&~mask&255U));
}
// ADD.W src,Dn (WORD, upper half kept).
void ou_add_word(std::uint32_t& d,std::uint32_t src) {am_word(d,(d+src)&65535U);}
// ADD.W D1,D0; NEG.W D0.
void ou_add_negate(AnimationMachineState& r) {ou_add_word(r.d[0],r.d[1]);am_word(r.d[0],(0U-(r.d[0]&65535U))&65535U);}
// MOVE.W d16(A6),D2; CMP.W d16(A6),D2; BEQ equal_pc; BMI minus_pc (bundled: N of the same CMP), else plus_pc.
bool ou_range_compare(AnimationMachineContext& c,std::uint32_t own,std::uint32_t other,std::uint32_t equal_pc,
    std::uint32_t minus_pc,std::uint32_t plus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,limit=0;
    if(!ou_get(c,r.a[6],own,2,value) || !ou_get(c,r.a[6],other,2,limit))return false;
    am_word(r.d[2],value);
    const std::uint32_t difference=(value-limit)&65535U;
    r.pc=difference==0?equal_pc:((difference&0x8000U)?minus_pc:plus_pc);return true;
}
// Consumers of a known C (BCC clear_pc / BCS set_pc).
bool ou_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects u01 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ANDI.B #fe,CCR / ORI.B #1,CCR; RTS.
bool ou_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {c.s.carry=carry;return am_return(c);}
// SUB.W D6,Dn; BGE ge_pc (signed Dn >= D6 before the subtraction), else lt_pc.
void ou_subtract_ge(AnimationMachineState& r,std::uint32_t& d,std::uint32_t ge_pc,std::uint32_t lt_pc) {
    const bool ge=ou_signed_word(d)>=ou_signed_word(r.d[6]);am_word(d,(d-r.d[6])&65535U);r.pc=ge?ge_pc:lt_pc;
}
// BSET D4,(A1); LEA 8(A1),A1; DBRA D1,loop_pc.
bool ou_mark_column(AnimationMachineContext& c,std::uint32_t loop_pc,std::uint32_t done_pc) {
    AnimationMachineState& r=c.s;
    if(!ou_bit(c,r.a[1],r.d[4],true))return false;r.a[1]+=8U;
    am_word(r.d[1],(r.d[1]-1U)&65535U);r.pc=(r.d[1]&65535U)!=65535U?loop_pc:done_pc;return true;
}
// ASR.W #1,D0; BCC clear_pc (C = the bit shifted out), else set_pc.
void ou_shift_flag(AnimationMachineState& r,std::uint32_t clear_pc,std::uint32_t set_pc) {
    const std::uint32_t word=r.d[0]&65535U;am_word(r.d[0],(word>>1)|(word&0x8000U));r.pc=(word&1U)?set_pc:clear_pc;
}
// LEA d(A4),A1; BSET D4,(A1,D5.W).
bool ou_mark_flag(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;r.a[1]=am_index(r.a[4],displacement);
    if(!ou_bit(c,am_index(r.a[1],r.d[5]),r.d[4],true))return false;r.pc=next_pc;return true;
}
// LEA abs,A1; CMPI.L #limit,8(A1); BLE le_pc (signed), else gt_pc.
bool ou_scroll_check(AnimationMachineContext& c,std::uint32_t base,std::uint32_t limit,std::uint32_t le_pc,std::uint32_t gt_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[1]=base;
    if(!ou_get(c,r.a[1],8,4,value))return false;
    r.pc=ou_signed_long(value)<=ou_signed_long(limit)?le_pc:gt_pc;return true;
}
// SUBI.L #n,8(A1).
bool ou_scroll_step(AnimationMachineContext& c,std::uint32_t n,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ou_get(c,r.a[1],8,4,value) || !ou_put(c,r.a[1],8,4,value-n))return false;r.pc=next_pc;return true;
}
}
// Object callbacks F4 U01 (105 block starts): the C2 screen range test 1aa7e (C returned), 48296, the C4 contact entry
// 4b50c (C returned) and contact bitmap registration 4b54e (C returned: Clear when BYTE 5e(A6) = 0, else Set), the item node
// callback b4d7e with its installed callbacks b4df8/b4e1c/b4e34 and the item initialisation b4fd4, the stubs c6a90 and d6d22,
// and the node callback dd4d0 with its installed callbacks dd4e2/dd512. The BMI after the BEQ at 1aa9c/1aad8 consumes the N of
// the same CMP and is bundled into 1aa90/1aacc. 4b55c, b4e26 and b4e60 consume a known C (b4e26: from the b4e6c boundary).
// 1aaf6/4b548/4b6be produce Clear and 1aafc/4b532/4b6ca produce Set (4b6be: MOVE.B clears C). The TRAP #15 sites b4db0 and
// b4e46 with their strings, the callees b4e6c and 482c0 and the callback dd574 have no executor. Existing executors called:
// F3a 43e34, F3b 49a84 (F1c2 49a58 with its RNG pointer guard), U7 4b784, F1b 1c5b0, sound 3af8, fade_card 2a00. ROM data
// (b516c, 4a9e2, item records) is read through the live bus; d16(A5) operands use the live A5. The DBRA loops and the
// 4b6ae..4b6b8 loop have no extra limit (block budget only).
bool animation_objects_u01_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- 1aa7e: MOVE.L (A0)+,D0; MOVE.L (A0)+,D1; BTST #1,15(A6); BEQ 1aa90.
    case 0x1aa7e:
        if(!am_read(c,r.a[0],4,value))return false;r.d[0]=value;r.a[0]+=4U;
        if(!am_read(c,r.a[0],4,value))return false;r.d[1]=value;r.a[0]+=4U;
        if(!ou_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&2U)?0x1aa8c:0x1aa90;return true;
    case 0x1aa8c:ou_add_negate(r);r.pc=0x1aa90;return true;
    case 0x1aa90:return ou_range_compare(c,0x46,0x4e,0x1aaba,0x1aaae,0x1aaa0);
    // ADD.W D0,D2; CMP.W 53f8(A5),D2; BGT 1aafc.
    case 0x1aaa0:
        ou_add_word(r.d[2],r.d[0]);if(!ou_get(c,r.a[5],0x53f8,2,value))return false;
        r.pc=ou_signed_word(r.d[2])>ou_signed_word(value)?0x1aafc:0x1aaaa;return true;
    case 0x1aaaa:r.pc=0x1aaba;return true; // BRA 1aaba.
    // ADD.W D0,D2; ADD.W D1,D2; CMP.W 53f6(A5),D2; BLT 1aafc.
    case 0x1aaae:
        ou_add_word(r.d[2],r.d[0]);ou_add_word(r.d[2],r.d[1]);if(!ou_get(c,r.a[5],0x53f6,2,value))return false;
        r.pc=ou_signed_word(r.d[2])<ou_signed_word(value)?0x1aafc:0x1aaba;return true;
    // SWAP D0; SWAP D1; BTST #0,15(A6); BEQ 1aacc.
    case 0x1aaba:
        am_swap(r.d[0]);am_swap(r.d[1]);if(!ou_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&1U)?0x1aac8:0x1aacc;return true;
    case 0x1aac8:ou_add_negate(r);r.pc=0x1aacc;return true;
    case 0x1aacc:return ou_range_compare(c,0x42,0x4a,0x1aaf6,0x1aaea,0x1aadc);
    // ADD.W D0,D2; CMP.W 53f4(A5),D2; BGT 1aafc.
    case 0x1aadc:
        ou_add_word(r.d[2],r.d[0]);if(!ou_get(c,r.a[5],0x53f4,2,value))return false;
        r.pc=ou_signed_word(r.d[2])>ou_signed_word(value)?0x1aafc:0x1aae6;return true;
    case 0x1aae6:r.pc=0x1aaf6;return true; // BRA 1aaf6.
    // ADD.W D0,D2; ADD.W D1,D2; CMP.W 53f2(A5),D2; BLT 1aafc.
    case 0x1aaea:
        ou_add_word(r.d[2],r.d[0]);ou_add_word(r.d[2],r.d[1]);if(!ou_get(c,r.a[5],0x53f2,2,value))return false;
        r.pc=ou_signed_word(r.d[2])<ou_signed_word(value)?0x1aafc:0x1aaf6;return true;
    case 0x1aaf6:case 0x4b548:return ou_return_carry(c,AnimationCarryClear); // ANDI.B #fe,CCR; RTS.
    case 0x1aafc:return ou_return_carry(c,AnimationCarrySet);                // ORI.B #1,CCR; RTS.

    // ---- 48296: BCLR #5,5683(A5); BCLR #4,5683(A5); JSR 1c5b0.L.
    case 0x48296:
        if(!ou_bit(c,am_index(r.a[5],0x5683),5,false) || !ou_bit(c,am_index(r.a[5],0x5683),4,false))return false;
        return am_call(c,0x1c5b0,0x482a8);
    case 0x482a8:case 0x4b6e2:case 0xb4e6a:case 0xdd4ea:return am_return(c); // RTS.

    // ---- 4b50c: CMPI.W #1,a(A3); BEQ 4b548.
    case 0x4b50c:if(!ou_get(c,r.a[3],0xa,2,value))return false;r.pc=(value&65535U)==1U?0x4b548:0x4b516;return true;
    // TST.B 5b84(A5); BEQ 4b548.
    case 0x4b516:if(!ou_get(c,r.a[5],0x5b84,1,value))return false;r.pc=(value&255U)?0x4b51e:0x4b548;return true;
    // MOVEA.L c(A3),A4; CMPA.W #0,A4; BEQ 4b532 (full 32-bit test).
    case 0x4b51e:if(!ou_get(c,r.a[3],0xc,4,value))return false;r.a[4]=value;r.pc=value?0x4b52a:0x4b532;return true;
    // TST.W 32(A4); BEQ 4b548.
    case 0x4b52a:if(!ou_get(c,r.a[4],0x32,2,value))return false;r.pc=(value&65535U)?0x4b532:0x4b548;return true;
    // CLR.W 54(A6); BSET #7,61(A6); MOVE.B #19,5e(A6); ORI.B #1,CCR; RTS.
    case 0x4b532:
        if(!ou_put(c,r.a[6],0x54,2,0) || !ou_bit(c,am_index(r.a[6],0x61),7,true) || !ou_put(c,r.a[6],0x5e,1,0x19))return false;
        return ou_return_carry(c,AnimationCarrySet);

    // ---- 4b54e: MOVEA.L 56(A6),A3; CMPA.W #0,A3; BEQ 4b6be.
    case 0x4b54e:if(!ou_get(c,r.a[6],0x56,4,value))return false;r.a[3]=value;r.pc=value?0x4b55a:0x4b6be;return true;
    case 0x4b55a:return am_call(c,0x4b50c,0x4b55c); // BSR 4b50c.
    case 0x4b55c:return ou_carry(c,0x4b560,0x4b6be); // BCS 4b6be.
    // LEA 5a(A6),A2; LEA 5746(A5),A4; TST.B 5744(A5); BPL 4b576.
    case 0x4b560:
        r.a[2]=am_index(r.a[6],0x5a);r.a[4]=am_index(r.a[5],0x5746);if(!ou_get(c,r.a[5],0x5744,1,value))return false;
        r.pc=(value&0x80U)?0x4b570:0x4b576;return true;
    case 0x4b570:r.a[2]+=1U;r.a[4]=am_index(r.a[5],0x5918);r.pc=0x4b576;return true; // ADDQ.W #1,A2; LEA 5918(A5),A4.
    // MOVE.B #ff,(A2); MOVE.W 1d0(A4),D4; CMPI.W #40,D4; BCC 4b6be (unsigned).
    case 0x4b576:
        if(!am_write(c,r.a[2],1,0xff) || !ou_get(c,r.a[4],0x1d0,2,value))return false;am_word(r.d[4],value);
        r.pc=(value&65535U)>=0x40U?0x4b6be:0x4b586;return true;
    // MOVE.B D4,D5; LSR.W #3,D5; NOT.W D5; ANDI.W #7,D5; MOVE.L (A3)+,D0; MOVE.L (A3)+,D1; BTST #1,15(A6); BEQ 4b5a2.
    case 0x4b586:
        am_byte(r.d[5],r.d[4]&255U);am_word(r.d[5],(r.d[5]&65535U)>>3);am_word(r.d[5],(~r.d[5])&65535U);am_word(r.d[5],r.d[5]&7U);
        if(!am_read(c,r.a[3],4,value))return false;r.d[0]=value;r.a[3]+=4U;
        if(!am_read(c,r.a[3],4,value))return false;r.d[1]=value;r.a[3]+=4U;
        if(!ou_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&2U)?0x4b59e:0x4b5a2;return true;
    case 0x4b59e:ou_add_negate(r);r.pc=0x4b5a2;return true;
    // ADD.W 46(A6),D0; SWAP D0; SWAP D1; BTST #0,15(A6); BEQ 4b5b8.
    case 0x4b5a2:
        if(!ou_get(c,r.a[6],0x46,2,value))return false;ou_add_word(r.d[0],value);am_swap(r.d[0]);am_swap(r.d[1]);
        if(!ou_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&1U)?0x4b5b4:0x4b5b8;return true;
    case 0x4b5b4:ou_add_negate(r);r.pc=0x4b5b8;return true;
    // ADD.W 42(A6),D0; MOVE.W #ffe0,D6; MOVE.W #15f,D7; ADD.W D0,D1; CMP.W D7,D0; BGT 4b6be.
    case 0x4b5b8:
        if(!ou_get(c,r.a[6],0x42,2,value))return false;ou_add_word(r.d[0],value);am_word(r.d[6],0xffe0);am_word(r.d[7],0x15f);
        ou_add_word(r.d[1],r.d[0]);r.pc=ou_signed_word(r.d[0])>ou_signed_word(r.d[7])?0x4b6be:0x4b5cc;return true;
    case 0x4b5cc:case 0x4b5f8:r.pc=ou_signed_word(r.d[1])<ou_signed_word(r.d[6])?0x4b6be:r.pc+6U;return true; // CMP.W D6,D1; BLT 4b6be.
    case 0x4b5d2:ou_subtract_ge(r,r.d[0],0x4b5da,0x4b5d8);return true; // SUB.W D6,D0; BGE 4b5da.
    case 0x4b5fe:ou_subtract_ge(r,r.d[0],0x4b606,0x4b604);return true; // SUB.W D6,D0; BGE 4b606.
    case 0x4b5d8:case 0x4b604:am_word(r.d[0],0);r.pc+=2U;return true;  // CLR.W D0.
    case 0x4b5da:case 0x4b606:r.pc=ou_signed_word(r.d[1])<=ou_signed_word(r.d[7])?r.pc+8U:r.pc+6U;return true; // CMP.W D7,D1; BLE.
    case 0x4b5e0:case 0x4b60c:am_word(r.d[1],r.d[7]);r.pc+=2U;return true; // MOVE.W D7,D1.
    // SUB.W D6,D1; SWAP D0; SWAP D1; MOVE.W #100,D6; MOVE.W #1ff,D7; ADD.W D0,D1; CMP.W D7,D0; BGT 4b6be.
    case 0x4b5e2:
        am_word(r.d[1],(r.d[1]-r.d[6])&65535U);am_swap(r.d[0]);am_swap(r.d[1]);am_word(r.d[6],0x100);am_word(r.d[7],0x1ff);
        ou_add_word(r.d[1],r.d[0]);r.pc=ou_signed_word(r.d[0])>ou_signed_word(r.d[7])?0x4b6be:0x4b5f8;return true;
    // SUB.W D6,D1; LSR.L #5,D0; LSR.L #5,D1; MOVE.W #7ff,D6; AND.W D6,D0; AND.W D6,D1; SUB.L D0,D1; LSL.L #3,D0;
    // ADD.W D5,D0; LEA 60(A4,D0.W),A1.
    case 0x4b60e:
        am_word(r.d[1],(r.d[1]-r.d[6])&65535U);r.d[0]>>=5;r.d[1]>>=5;am_word(r.d[6],0x7ff);
        am_word(r.d[0],r.d[0]&0x7ffU);am_word(r.d[1],r.d[1]&0x7ffU);r.d[1]=r.d[1]-r.d[0];r.d[0]=r.d[0]<<3;
        ou_add_word(r.d[0],r.d[5]);r.a[1]=am_index(r.a[4],r.d[0])+0x60U;r.pc=0x4b626;return true;
    case 0x4b626:return ou_mark_column(c,0x4b626,0x4b630);
    // SWAP D0; SWAP D1; ADD.W D5,D0; LEA (A4,D0.W),A1.
    case 0x4b630:am_swap(r.d[0]);am_swap(r.d[1]);ou_add_word(r.d[0],r.d[5]);r.a[1]=am_index(r.a[4],r.d[0]);r.pc=0x4b63a;return true;
    case 0x4b63a:return ou_mark_column(c,0x4b63a,0x4b644);
    // MOVE.W (A3)+,D0; LEA 4a9e2(PC),A1; MOVE.B (A1,D0.W),D0; LSL.W #3,D0; ADD.W D5,D0; LEA a0(A4),A1; BSET D4,(A1,D0.W);
    // MOVE.W (A3)+,D0; ASR.W #1,D0; BCC 4b66a.
    case 0x4b644:
        if(!am_read(c,r.a[3],2,value))return false;am_word(r.d[0],value);r.a[3]+=2U;r.a[1]=OU_SLOT_TABLE;
        if(!am_read(c,am_index(r.a[1],r.d[0]),1,value))return false;am_byte(r.d[0],value);
        am_word(r.d[0],(r.d[0]<<3)&65535U);ou_add_word(r.d[0],r.d[5]);r.a[1]=am_index(r.a[4],0xa0);
        if(!ou_bit(c,am_index(r.a[1],r.d[0]),r.d[4],true))return false;
        if(!am_read(c,r.a[3],2,value))return false;am_word(r.d[0],value);r.a[3]+=2U;
        ou_shift_flag(r,0x4b66a,0x4b662);return true;
    case 0x4b662:return ou_mark_flag(c,0xb8,0x4b66a);
    case 0x4b66a:ou_shift_flag(r,0x4b678,0x4b670);return true;
    case 0x4b670:return ou_mark_flag(c,0xc0,0x4b678);
    case 0x4b678:ou_shift_flag(r,0x4b686,0x4b67e);return true;
    case 0x4b67e:return ou_mark_flag(c,0xc8,0x4b686);
    // MOVE.W 1d0(A4),D0; MOVE.B D0,(A2); MOVE.W D0,D7; LSL.W #2,D7; LEA d0(A4),A2; MOVE.L A6,(A2,D7.W); ADDQ.W #1,D0;
    // MOVE.W D0,1d0(A4); BTST #6,10f000.L; BEQ 4b6be.
    case 0x4b686:
        if(!ou_get(c,r.a[4],0x1d0,2,value))return false;am_word(r.d[0],value);
        if(!am_write(c,r.a[2],1,r.d[0]&255U))return false;am_word(r.d[7],r.d[0]);am_word(r.d[7],(r.d[7]<<2)&65535U);
        r.a[2]=am_index(r.a[4],0xd0);if(!am_write(c,am_index(r.a[2],r.d[7]),4,r.a[6]))return false;
        ou_add_word(r.d[0],1);if(!ou_put(c,r.a[4],0x1d0,2,r.d[0]&65535U))return false;
        if(!am_read(c,OU_DEBUG_FLAGS,1,value))return false;r.pc=(value&0x40U)?0x4b6aa:0x4b6be;return true;
    case 0x4b6aa:r.a[0]=am_index(r.a[3],6);r.pc=0x4b6ae;return true; // LEA 6(A3),A0.
    case 0x4b6ae:r.d[7]=0xa2b;return am_call(c,0x4b784,0x4b6b8); // MOVE.L #a2b,D7; JSR 4b784(PC).
    // CMPI.W #8000,(A0); BNE 4b6ae.
    case 0x4b6b8:if(!am_read(c,r.a[0],2,value))return false;r.pc=(value&65535U)!=0x8000U?0x4b6ae:0x4b6be;return true;
    // MOVEQ #0,D2; MOVEQ #0,D3; MOVE.B 5e(A6),D0; BEQ 4b6e2 (MOVE clears C: the known Clear returned by 4b54e).
    case 0x4b6be:
        r.d[2]=0;r.d[3]=0;if(!ou_get(c,r.a[6],0x5e,1,value))return false;am_byte(r.d[0],value);
        r.carry=AnimationCarryClear;r.pc=(value&255U)?0x4b6ca:0x4b6e2;return true;
    // MOVE.B 5c(A6),D2; ADD.W D2,D2; MOVE.B 5d(A6),D3; ADD.W D3,D3; SUB.W 42(A6),D2; SUB.W 46(A6),D3; ORI.B #1,CCR.
    case 0x4b6ca:
        if(!ou_get(c,r.a[6],0x5c,1,value))return false;am_byte(r.d[2],value);ou_add_word(r.d[2],r.d[2]);
        if(!ou_get(c,r.a[6],0x5d,1,value))return false;am_byte(r.d[3],value);ou_add_word(r.d[3],r.d[3]);
        if(!ou_get(c,r.a[6],0x42,2,value) || !ou_get(c,r.a[6],0x46,2,other))return false;
        am_word(r.d[2],(r.d[2]-value)&65535U);am_word(r.d[3],(r.d[3]-other)&65535U);
        r.carry=AnimationCarrySet;r.pc=0x4b6e2;return true;

    // ---- b4d7e (callback): MOVE.W #0,8c(A6); BRA b4da6.
    case 0xb4d7e:if(!ou_put(c,r.a[6],0x8c,2,0))return false;r.pc=0xb4da6;return true;
    // CMPI.W #4,76(A6); BCS b4dc2 (unsigned; otherwise the TRAP #15 boundary b4db0).
    case 0xb4da6:if(!ou_get(c,r.a[6],0x76,2,value))return false;r.pc=(value&65535U)<4U?0xb4dc2:0xb4db0;return true;
    case 0xb4dc2:return am_call(c,0xb4fd4,0xb4dc6); // JSR b4fd4(PC).
    case 0xb4dc6:case 0xb4e12:case 0xb4e30:r.pc=r.pc==0xb4dc6?0xb4df2:0xb4e3a;return true; // BRA.
    case 0xb4df2:if(!am_write(c,r.a[6],4,0xb4df8))return false;r.pc=0xb4df8;return true; // MOVE.L #b4df8,(A6).
    case 0xb4df8:return am_call(c,0x43e34,0xb4dfe); // JSR 43e34.L (callback entry).
    case 0xb4dfe:return am_call(c,0x4b54e,0xb4e04); // JSR 4b54e.L.
    // CLR.B 5e(A6); BTST #7,61(A6); BNE b4e16.
    case 0xb4e04:
        if(!ou_put(c,r.a[6],0x5e,1,0) || !ou_get(c,r.a[6],0x61,1,value))return false;r.pc=(value&0x80U)?0xb4e16:0xb4e12;return true;
    case 0xb4e16:if(!am_write(c,r.a[6],4,0xb4e1c))return false;r.pc=0xb4e1c;return true; // MOVE.L #b4e1c,(A6).
    case 0xb4e1c:return am_call(c,0x43e34,0xb4e22); // JSR 43e34.L (callback entry).
    case 0xb4e22:return am_call(c,0xb4e6c,0xb4e26); // JSR b4e6c(PC) (boundary without an executor).
    case 0xb4e26:return ou_carry(c,0xb4e30,0xb4e2a); // BCC b4e30.
    case 0xb4e2a:if(!am_write(c,r.a[6],4,0xb4e34))return false;r.pc=0xb4e30;return true; // MOVE.L #b4e34,(A6).
    case 0xb4e34:case 0xc6a90:r.pc=0x2a00;return true; // JMP 2a00.L (callback entry, self delete).
    // MOVEA.L 56(A6),A0; CMPA.W #0,A0; BNE b4e5a (otherwise the TRAP #15 boundary b4e46).
    case 0xb4e3a:if(!ou_get(c,r.a[6],0x56,4,value))return false;r.a[0]=value;r.pc=value?0xb4e5a:0xb4e46;return true;
    case 0xb4e5a:return am_call(c,0x1aa7e,0xb4e60); // JSR 1aa7e.L.
    case 0xb4e60:return ou_carry(c,0xb4e6a,0xb4e64); // BCC b4e6a.
    case 0xb4e64:if(!am_write(c,r.a[6],4,0xb4e34))return false;r.pc=0xb4e6a;return true; // MOVE.L #b4e34,(A6).

    // ---- b4fd4: MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; LEA b516c(PC),A0; MOVEA.L (A0,D0.W),A0; MOVE.L A0,56(A6);
    // ADDA.W #12,A0; MOVE.L (A0)+,8e(A6); MOVE.L (A0)+,92(A6); MOVE.W 7a(A6),54(A6); BNE b5004.
    case 0xb4fd4:
        if(!ou_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);
        am_word(r.d[0],(r.d[0]<<1)&65535U);am_word(r.d[0],(r.d[0]<<1)&65535U);r.a[0]=OU_ITEM_TABLE;
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;
        if(!ou_put(c,r.a[6],0x56,4,r.a[0]))return false;r.a[0]+=0x12U;
        if(!am_read(c,r.a[0],4,value) || !ou_put(c,r.a[6],0x8e,4,value))return false;r.a[0]+=4U;
        if(!am_read(c,r.a[0],4,value) || !ou_put(c,r.a[6],0x92,4,value))return false;r.a[0]+=4U;
        if(!ou_get(c,r.a[6],0x7a,2,value) || !ou_put(c,r.a[6],0x54,2,value&65535U))return false;
        r.pc=(value&65535U)?0xb5004:0xb4ffe;return true;
    case 0xb4ffe:if(!ou_bit(c,am_index(r.a[6],0x61),7,true))return false;r.pc=0xb5004;return true; // BSET #7,61(A6).
    // TST.W 78(A6); BNE b501c.
    case 0xb5004:if(!ou_get(c,r.a[6],0x78,2,value))return false;r.pc=(value&65535U)?0xb501c:0xb500c;return true;
    case 0xb500c:am_word(r.d[0],3);return am_call(c,0x49a84,0xb5016); // MOVE.W #3,D0; JSR 49a84.L.
    // ADDQ.W #1,D0; MOVE.W D0,78(A6).
    case 0xb5016:ou_add_word(r.d[0],1);if(!ou_put(c,r.a[6],0x78,2,r.d[0]&65535U))return false;r.pc=0xb501c;return true;
    // CLR.B 9c(A6); MOVE.W 82(A6),D0; MOVE.B 84(A6),D1; MOVE.B 85(A6),D2; EXT.L D0; LSL.L #8,D0; MOVE.L D0,88(A6);
    // MOVE.B D1,9a(A6); MOVE.B D2,9b(A6); RTS.
    case 0xb501c:
        if(!ou_put(c,r.a[6],0x9c,1,0) || !ou_get(c,r.a[6],0x82,2,value))return false;am_word(r.d[0],value);
        if(!ou_get(c,r.a[6],0x84,1,value))return false;am_byte(r.d[1],value);
        if(!ou_get(c,r.a[6],0x85,1,value))return false;am_byte(r.d[2],value);
        r.d[0]=am_extend_word(r.d[0])<<8;
        if(!ou_put(c,r.a[6],0x88,4,r.d[0]) || !ou_put(c,r.a[6],0x9a,1,r.d[1]&255U) || !ou_put(c,r.a[6],0x9b,1,r.d[2]&255U))return false;
        return am_return(c);

    // ---- d6d22 (callback): MOVEA.L c0(A6),A0; ADDA.L #a,A0; MOVE.L A0,5e2a(A5); JMP 2a00.L.
    case 0xd6d22:
        if(!ou_get(c,r.a[6],0xc0,4,value))return false;r.a[0]=value+0xaU;
        if(!ou_put(c,r.a[5],0x5e2a,4,r.a[0]))return false;r.pc=0x2a00;return true;

    // ---- dd4d0 (callback): JSR 48296.L.
    case 0xdd4d0:return am_call(c,0x48296,0xdd4d6);
    // MOVE.B #5a,18(A6); MOVE.L #dd4e2,(A6) (then the callback dd4e2).
    case 0xdd4d6:if(!ou_put(c,r.a[6],0x18,1,0x5a) || !am_write(c,r.a[6],4,0xdd4e2))return false;r.pc=0xdd4e2;return true;
    // SUBQ.B #1,18(A6); BMI dd4ec.
    case 0xdd4e2:
        if(!ou_get(c,r.a[6],0x18,1,value))return false;value=(value-1U)&255U;
        if(!ou_put(c,r.a[6],0x18,1,value))return false;r.pc=(value&0x80U)?0xdd4ec:0xdd4ea;return true;
    case 0xdd4ec:return am_call(c,0x482c0,0xdd4f2); // JSR 482c0.L (boundary without an executor).
    case 0xdd4f2:am_word(r.d[0],0x19d5);return am_call(c,0x3af8,0xdd4fc); // MOVE.W #19d5,D0; JSR 3af8.L.
    case 0xdd4fc:am_word(r.d[0],0x738);return am_call(c,0x3af8,0xdd506);  // MOVE.W #738,D0; JSR 3af8.L.
    // MOVE.W #1,5418(A5); MOVE.L #dd512,(A6) (then the callback dd512).
    case 0xdd506:if(!ou_put(c,r.a[5],0x5418,2,1) || !am_write(c,r.a[6],4,0xdd512))return false;r.pc=0xdd512;return true;
    case 0xdd512:return ou_scroll_check(c,OU_SCROLL_A,0xfffa0000U,0xdd52c,0xdd524); // LEA 10b1d6,A1; CMPI.L; BLE dd52c.
    case 0xdd524:return ou_scroll_step(c,0x4000,0xdd52c);                         // SUBI.L #4000,8(A1).
    // MOVE.L #0,c(A1); MOVE.L 76(A6),D0; SUB.L 8(A1),D0; CMPI.L #7b00000,D0; BCS dd54c (unsigned).
    case 0xdd52c:
        if(!ou_put(c,r.a[1],0xc,4,0) || !ou_get(c,r.a[6],0x76,4,value) || !ou_get(c,r.a[1],8,4,other))return false;
        r.d[0]=value-other;r.pc=r.d[0]<0x7b00000U?0xdd54c:0xdd546;return true;
    case 0xdd546:if(!am_write(c,r.a[6],4,0xdd574))return false;r.pc=0xdd54c;return true; // MOVE.L #dd574,(A6).
    // MOVE.L D0,76(A6); LEA 10d256,A1; CMPI.L #ffffa000,8(A1); BLE dd56a.
    case 0xdd54c:if(!ou_put(c,r.a[6],0x76,4,r.d[0]))return false;return ou_scroll_check(c,OU_SCROLL_B,0xffffa000U,0xdd56a,0xdd562);
    case 0xdd562:return ou_scroll_step(c,0x400,0xdd56a); // SUBI.L #400,8(A1).
    case 0xdd56a:if(!ou_put(c,r.a[1],0xc,4,0))return false;return am_return(c); // MOVE.L #0,c(A1); RTS.
    default:return am_error(c,"unsupported animation objects u01 PC");
    }
}
}
