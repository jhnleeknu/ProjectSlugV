#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t CORE_SIGN=0x80000000U;
// BCC/BCS right after a call: consumes the C returned by 1a2b4, a condition handler, 1a34c or 289e.
bool core_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"scene core caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// Two's-complement WORD/LONG values for signed compares, without implementation-defined casts.
std::int32_t core_signed(std::uint32_t value) {
    const std::int32_t low=static_cast<std::int32_t>(value&0x7fffU);
    return (value&0x8000U)?low-0x8000:low;
}
std::int64_t core_signed_long(std::uint32_t value) {
    const std::int64_t low=static_cast<std::int64_t>(value&0x7fffffffU);
    return (value&CORE_SIGN)?low-static_cast<std::int64_t>(0x80000000LL):low;
}
// ASR.W/ASR.L: arithmetic shift (sign bits shifted in), counts below the operand width.
std::uint32_t core_asr_word(std::uint32_t value,unsigned int count) {
    const std::uint32_t word=value&65535U;
    const std::uint32_t fill=(word&0x8000U)?((65535U<<(16U-count))&65535U):0U;
    return (word>>count)|fill;
}
std::uint32_t core_asr_long(std::uint32_t value,unsigned int count) {
    const std::uint32_t fill=(value&CORE_SIGN)?(0xffffffffU<<(32U-count)):0U;
    return (value>>count)|fill;
}
// ADD.W src,dst: 16-bit signed overflow (V) of the exact operation.
bool core_add_overflow_word(std::uint32_t dst,std::uint32_t src) {
    const std::uint32_t result=(dst+src)&65535U;
    return (~(dst^src)&(dst^result)&0x8000U)!=0U;
}
// ADD.L src,dst then BGE: N xor V of the 32-bit result.
bool core_add_ge_long(std::uint32_t dst,std::uint32_t src) {
    const std::uint32_t result=dst+src;
    const bool n=(result&CORE_SIGN)!=0U;
    const bool v=(~(dst^src)&(dst^result)&CORE_SIGN)!=0U;
    return n==v;
}
// d16(A5) operands use the live A5.
bool core_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool core_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// MOVE.W d16(A5),Dn: one live WORD read, only the low WORD replaced.
bool core_load(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t& reg) {
    std::uint32_t value=0;if(!core_read(c,displacement,2,value))return false;am_word(reg,value);return true;
}
// SUB.W Dn,d16(A5) / ADD.W Dn,d16(A5): WORD read-modify-write.
bool core_sub_memory(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t reg) {
    std::uint32_t value=0;if(!core_read(c,displacement,2,value))return false;
    return core_write(c,displacement,2,(value-reg)&65535U);
}
bool core_add_memory(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t reg,unsigned int size) {
    std::uint32_t value=0;if(!core_read(c,displacement,size,value))return false;
    return core_write(c,displacement,size,size==2?((value+reg)&65535U):value+reg);
}
// 1a73c..1a7a8 MOVE.W #bank,-7ff0(A5) and the two PVC bank WORD writes through the device path.
bool core_bank(AnimationMachineContext& c,std::uint32_t flag,std::uint32_t bank) {
    return am_write(c,am_index(c.s.a[5],0x8010),2,flag) && am_write(c,0x2ffff2,2,bank) && am_write(c,0x2ffff0,2,0);
}
// MOVE.L 53bc(A5),D0; MOVE.L 53c0(A5),D1; BSR 19802 (1a76a, 19bbe and the tail of 19d08).
bool core_motion(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;
    if(!core_read(c,0x53bc,4,value))return false;c.s.d[0]=value;
    if(!core_read(c,0x53c0,4,value))return false;c.s.d[1]=value;
    return am_call(c,0x19802,return_pc);
}
// MOVE.W target(A5),D1; SUB.W current(A5),D1; BEQ; BMI (Z and N of the WORD difference, one block).
bool core_delta(AnimationMachineContext& c,std::uint32_t target,std::uint32_t current,
    std::uint32_t zero_pc,std::uint32_t minus_pc,std::uint32_t plus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!core_load(c,target,r.d[1]) || !core_read(c,current,2,value))return false;
    am_word(r.d[1],r.d[1]-value);
    r.pc=!(r.d[1]&65535U)?zero_pc:((r.d[1]&0x8000U)?minus_pc:plus_pc);return true;
}
// 19a40 (X) and 19ac8 (Y) share one body with different fields and margins.
struct CoreAxis {
    std::uint32_t low,high,center,half,margin_low,margin_high,limit,smooth;
};
const CoreAxis CORE_X={0x53ce,0x53d2,0x53d6,0x53da,0x2c,0x114,0x53e6,0x53de};
const CoreAxis CORE_Y={0x53d0,0x53d4,0x53d8,0x53dc,0x18,0xb8,0x53ea,0x53e2};
// MOVE.W low,D0; MOVE.W high,D1; MOVEQ #0,D7; MOVE.W D0,D7; ADD.W D1,D7; ASR.W #1,D7 (of the wrapped
// WORD sum); SUB.W center,D7; MOVE.W D7,D6; MOVE.W half,D5; ADD.W D5,D6; BMI (N of the WORD sum).
bool core_axis_start(AnimationMachineContext& c,const CoreAxis& a,std::uint32_t minus_pc,std::uint32_t other_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!core_load(c,a.low,r.d[0]) || !core_load(c,a.high,r.d[1]))return false;
    r.d[7]=0;am_word(r.d[7],r.d[0]);am_word(r.d[7],r.d[7]+r.d[1]);am_word(r.d[7],core_asr_word(r.d[7],1));
    if(!core_read(c,a.center,2,value))return false;am_word(r.d[7],r.d[7]-value);
    am_word(r.d[6],r.d[7]);
    if(!core_load(c,a.half,r.d[5]))return false;am_word(r.d[6],r.d[6]+r.d[5]);
    r.pc=(r.d[6]&0x8000U)?minus_pc:other_pc;return true;
}
// ASR.L #3,D7; MOVE.L limit,D0; CMP.L D0,D7; BLE (signed LONG).
bool core_axis_limit(AnimationMachineContext& c,const CoreAxis& a,std::uint32_t le_pc,std::uint32_t other_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.d[7]=core_asr_long(r.d[7],3);if(!core_read(c,a.limit,4,value))return false;r.d[0]=value;
    r.pc=core_signed_long(r.d[7])<=core_signed_long(r.d[0])?le_pc:other_pc;return true;
}
}
// 480bc frame helper U2: scene core 1a73c and its callees 1a2b4 (condition table 1a2d4: 1a2e0 1a334
// 1a2f2, rect test 1a34c -> 289e), 1a29e/197da, 1a26a, 1a526, 19b96 (19a40 19ac8 19978 19832 19802),
// 19d08 (19d98 198ee), 1a3d6 and 1a442. Existing executor: 289e (readiness, known C).
// Boundaries without an executor: 1a0b6 1a470 1a7a8 and the non-null motion branch targets
// 19812 19844 19910. All A5-relative operands use the live A5.
bool animation_scene_core_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    // 1a73c: MOVE.W #1,-7ff0(A5); MOVE.W #2000,2ffff2; MOVE.W #0,2ffff0; BSR 1a2b4.
    case 0x1a73c:if(!core_bank(c,1,0x2000))return false;return am_call(c,0x1a2b4,0x1a756);
    case 0x1a756:return core_carry(c,0x1a75e,0x1a75a); // BCC 1a75e
    case 0x1a75a:return am_call(c,0x1a26a,0x1a75e);
    case 0x1a75e:return am_call(c,0x1a526,0x1a762);
    case 0x1a762:return am_call(c,0x19b96,0x1a766);
    case 0x1a766:return am_call(c,0x19d08,0x1a76a);
    case 0x1a76a:return core_motion(c,0x1a776);
    // SWAP D7; CMP.W 5418(A5),D7; BCS 1a784 (unsigned).
    case 0x1a776:
        am_swap(r.d[7]);if(!core_read(c,0x5418,2,value))return false;
        r.pc=(r.d[7]&65535U)<value?0x1a784:0x1a780;return true;
    case 0x1a780:if(!core_write(c,0x5418,2,r.d[7]&65535U))return false;r.pc=0x1a784;return true;
    case 0x1a784:return am_call(c,0x1a3d6,0x1a788);
    case 0x1a788:return am_call(c,0x1a7a8,0x1a78c);
    case 0x1a78c:return am_call(c,0x1a442,0x1a790);
    // MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2; MOVE.W #0,2ffff0; RTS.
    case 0x1a790:if(!core_bank(c,0,0x1000))return false;return am_return(c);

    // 1a2b4: MOVEA.L 5422(A5),A1; CMPA.W #0,A1 (whole A1); BEQ 1a2cc.
    case 0x1a2b4:if(!core_read(c,0x5422,4,value))return false;r.a[1]=value;r.pc=value?0x1a2c0:0x1a2cc;return true;
    // MOVE.W (A1)+,D0; JSR 1a2d4(PC,D0.W): no range check, the computed PC is executed as is.
    case 0x1a2c0:
        if(!am_read(c,r.a[1],2,value))return false;r.a[1]+=2U;am_word(r.d[0],value);
        return am_call(c,0x1a2d4U+am_extend_word(r.d[0]),0x1a2c6);
    case 0x1a2c6:return core_carry(c,0x1a2d2,0x1a2ca); // BCC 1a2d2 (handler C)
    case 0x1a2ca:return am_call(c,0x1a29e,0x1a2cc);
    case 0x1a2cc:r.carry=AnimationCarrySet;return am_return(c); // ORI #1,CCR; RTS
    case 0x1a2d2:case 0x1a312:case 0x1a330:case 0x1a332:case 0x1a276:case 0x1a29c:
    case 0x1a44e:case 0x1a45a:case 0x1a464:case 0x199d2:case 0x19dec:return am_return(c);
    case 0x1a2d4:r.pc=0x1a2e0;return true;
    case 0x1a2d8:r.pc=0x1a334;return true;
    case 0x1a2dc:r.pc=0x1a2f2;return true;
    // Index 0: MOVE.W (A1)+,543e(A5); MOVE.W 5418(A5),D0; CMP.W 541e(A5),D0; EORI #1,CCR; RTS.
    case 0x1a2e0:
        if(!am_read(c,r.a[1],2,value))return false;r.a[1]+=2U;
        if(!core_write(c,0x543e,2,value) || !core_load(c,0x5418,r.d[0]) || !core_read(c,0x541e,2,value))return false;
        // CMP borrow (D0.W < mem, unsigned), then inverted by EORI.
        r.carry=(r.d[0]&65535U)<value?AnimationCarryClear:AnimationCarrySet;return am_return(c);
    // Index 8: TST.B 568e(A5); BEQ 1a3a0; both players in rect 1, else both in rect 2 (A1+8).
    case 0x1a2f2:case 0x1a334:
        if(!core_read(c,0x568e,1,value))return false;r.pc=value?r.pc+8U:0x1a3a0;return true;
    case 0x1a2fa:r.a[0]=am_index(r.a[5],0x8cb8);return am_call(c,0x1a34c,0x1a302);
    case 0x1a302:return core_carry(c,0x1a314,0x1a306);
    case 0x1a306:r.a[0]=am_index(r.a[5],0x8da8);return am_call(c,0x1a34c,0x1a30e);
    case 0x1a30e:return core_carry(c,0x1a314,0x1a312);
    // LEA 8(A1),A1; LEA -7348(A5),A0; BSR 1a34c.
    case 0x1a314:r.a[1]=am_index(r.a[1],8);r.a[0]=am_index(r.a[5],0x8cb8);return am_call(c,0x1a34c,0x1a320);
    case 0x1a320:return core_carry(c,0x1a332,0x1a324);
    case 0x1a324:r.a[0]=am_index(r.a[5],0x8da8);return am_call(c,0x1a34c,0x1a32c);
    case 0x1a32c:return core_carry(c,0x1a332,0x1a330);
    // Index 4: 1a33c BSR 1a34c for player 1, then 1a348 falls through into 1a34c for player 2.
    case 0x1a33c:r.a[0]=am_index(r.a[5],0x8cb8);return am_call(c,0x1a34c,0x1a344);
    case 0x1a344:return core_carry(c,0x1a3a0,0x1a348);
    case 0x1a348:r.a[0]=am_index(r.a[5],0x8da8);r.pc=0x1a34c;return true;
    case 0x1a34c:return am_call(c,0x289e,0x1a352); // JSR 289e.l
    case 0x1a352:return core_carry(c,0x1a356,0x1a35c); // BCS 1a35c
    case 0x1a356:case 0x1a39a:r.carry=AnimationCarrySet;return am_return(c); // ORI #1,CCR; RTS
    case 0x1a3a0:r.carry=AnimationCarryClear;return am_return(c); // ANDI #fe,CCR; RTS
    // BTST #7,15(A0) (memory BYTE); BEQ 1a3a0.
    case 0x1a35c:if(!am_read(c,am_index(r.a[0],0x15),1,value))return false;r.pc=(value&0x80U)?0x1a366:0x1a3a0;return true;
    // MOVE.L (A1),D4; MOVE.L 4(A1),D5; ADD.L D4,D5 (LONG: the low WORD carry reaches the high WORD);
    // MOVE.W 42(A0),D0; MOVE.W 46(A0),D1; SUB.W 53a2(A5),D0; SUB.W 53a6(A5),D1; CMP.W D4,D1; BLT 1a3a0.
    case 0x1a366:
        if(!am_read(c,r.a[1],4,value))return false;r.d[4]=value;
        if(!am_read(c,am_index(r.a[1],4),4,value))return false;r.d[5]=value+r.d[4];
        if(!am_read(c,am_index(r.a[0],0x42),2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,am_index(r.a[0],0x46),2,value))return false;am_word(r.d[1],value);
        if(!core_read(c,0x53a2,2,value))return false;am_word(r.d[0],r.d[0]-value);
        if(!core_read(c,0x53a6,2,value))return false;am_word(r.d[1],r.d[1]-value);
        r.pc=core_signed(r.d[1])<core_signed(r.d[4])?0x1a3a0:0x1a384;return true;
    case 0x1a384:r.pc=core_signed(r.d[1])>=core_signed(r.d[5])?0x1a3a0:0x1a38a;return true; // CMP.W D5,D1; BGE
    case 0x1a38a: // SWAP D4; SWAP D5; CMP.W D4,D0; BLT 1a3a0.
        am_swap(r.d[4]);am_swap(r.d[5]);r.pc=core_signed(r.d[0])<core_signed(r.d[4])?0x1a3a0:0x1a394;return true;
    case 0x1a394:r.pc=core_signed(r.d[0])>=core_signed(r.d[5])?0x1a3a0:0x1a39a;return true; // CMP.W D5,D0; BGE

    // 1a29e: CLR.L 5422(A5); JSR 197da(PC).
    case 0x1a29e:if(!core_write(c,0x5422,4,0))return false;return am_call(c,0x197da,0x1a2a6);
    // MOVE.W D7,541e(A5); MOVE.W D7,5420(A5); CLR.W 543e(A5); RTS.
    case 0x1a2a6:
        if(!core_write(c,0x541e,2,r.d[7]&65535U) || !core_write(c,0x5420,2,r.d[7]&65535U) ||
           !core_write(c,0x543e,2,0))return false;
        return am_return(c);
    // 197da: MOVEA.L 53b4(A5),A1; CMPA.W #0,A1; BNE 197ec.
    case 0x197da:if(!core_read(c,0x53b4,4,value))return false;r.a[1]=value;r.pc=value?0x197ec:0x197e6;return true;
    case 0x197e6:am_word(r.d[7],0x7fff);return am_return(c);
    // CMPI.W #ffff,2(A1); BEQ 197fc / ADDA.W #a,A1; BRA 197ec (no iteration limit in the original).
    case 0x197ec:if(!am_read(c,am_index(r.a[1],2),2,value))return false;r.pc=value==0xffffU?0x197fc:0x197f6;return true;
    case 0x197f6:r.a[1]=am_index(r.a[1],0xa);r.pc=0x197ec;return true;
    // MOVE.W (A1),D7; SUBQ.W #1,D7; RTS.
    case 0x197fc:if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[7],value-1U);return am_return(c);
    // 19802/19832/198ee: MOVEA.L 53b4(A5),A1; CMPA.W #0,A1; BNE to the non-null boundary.
    case 0x19802:case 0x19832:case 0x198ee:
        if(!core_read(c,0x53b4,4,value))return false;r.a[1]=value;
        if(r.pc==0x19802)r.pc=value?0x19812:0x1980e;
        else if(r.pc==0x19832)r.pc=value?0x19844:0x1983e;
        else r.pc=value?0x19910:0x198fa;
        return true;
    case 0x1980e:r.d[7]=0;return am_return(c);
    case 0x1983e:r.d[6]=0;r.d[7]=0;return am_return(c);
    // MOVEQ #0,D0/D1; MOVE.W 53b8/53ba(A5),D0/D1; SWAP D0/D1; MOVEQ #0,D2/D3; RTS.
    case 0x198fa:
        r.d[0]=0;r.d[1]=0;if(!core_load(c,0x53b8,r.d[0]) || !core_load(c,0x53ba,r.d[1]))return false;
        am_swap(r.d[0]);am_swap(r.d[1]);r.d[2]=0;r.d[3]=0;return am_return(c);

    // 1a26a: MOVEA.L 5412(A5),A1; CMPA.W #0,A1; BNE 1a278.
    case 0x1a26a:if(!core_read(c,0x5412,4,value))return false;r.a[1]=value;r.pc=value?0x1a278:0x1a276;return true;
    // MOVE.W 5418(A5),D0; CMP.W 5416(A5),D0; BCS 1a29c (unsigned).
    case 0x1a278:
        if(!core_load(c,0x5418,r.d[0]) || !core_read(c,0x5416,2,value))return false;
        r.pc=(r.d[0]&65535U)<value?0x1a29c:0x1a284;return true;
    case 0x1a284:if(!am_read(c,r.a[1],2,value))return false;r.pc=(value&0x8000U)?0x1a28a:0x1a292;return true; // TST.W (A1); BPL
    case 0x1a28a:if(!core_write(c,0x5416,2,0xffff))return false;return am_return(c);
    case 0x1a292:return am_call(c,0x1a0b6,0x1a296);
    case 0x1a296:if(!core_write(c,0x5412,4,r.a[1]))return false;r.pc=0x1a278;return true; // MOVE.L A1; BRA 1a278

    // 1a526: D0/D1 = min(541e,5440)/min(5420,5442) (CMP.W; BCS unsigned).
    case 0x1a526:
        if(!core_load(c,0x541e,r.d[0]) || !core_load(c,0x5420,r.d[1]) || !core_load(c,0x5440,r.d[2]))return false;
        r.pc=(r.d[0]&65535U)<(r.d[2]&65535U)?0x1a53a:0x1a538;return true;
    case 0x1a538:am_word(r.d[0],r.d[2]);r.pc=0x1a53a;return true;
    case 0x1a53a:if(!core_load(c,0x5442,r.d[2]))return false;r.pc=(r.d[1]&65535U)<(r.d[2]&65535U)?0x1a546:0x1a544;return true;
    case 0x1a544:am_word(r.d[1],r.d[2]);r.pc=0x1a546;return true;
    // MOVE.W D0/D1 to 53ee/53f0; MOVE.W 5444/5448 to D0/D1; CMPI.W #8000,D0; BNE 1a566.
    case 0x1a546:
        if(!core_write(c,0x53ee,2,r.d[0]&65535U) || !core_write(c,0x53f0,2,r.d[1]&65535U) ||
           !core_load(c,0x5444,r.d[0]) || !core_load(c,0x5448,r.d[1]))return false;
        r.pc=(r.d[0]&65535U)!=0x8000U?0x1a566:0x1a55e;return true;
    case 0x1a55e:if(!core_load(c,0x5426,r.d[0]) || !core_load(c,0x542a,r.d[1]))return false;r.pc=0x1a566;return true;
    case 0x1a566:
        if(!core_write(c,0x53d6,2,r.d[0]&65535U) || !core_write(c,0x53da,2,r.d[1]&65535U) ||
           !core_load(c,0x5446,r.d[0]) || !core_load(c,0x544a,r.d[1]))return false;
        r.pc=(r.d[0]&65535U)!=0x8000U?0x1a586:0x1a57e;return true;
    case 0x1a57e:if(!core_load(c,0x5428,r.d[0]) || !core_load(c,0x542c,r.d[1]))return false;r.pc=0x1a586;return true;
    // MOVE.W D0/D1 to 53d8/53dc; MOVE.W 543e(A5),D0; CMP.W 544c(A5),D0; BCC 1a59e (unsigned max).
    case 0x1a586:
        if(!core_write(c,0x53d8,2,r.d[0]&65535U) || !core_write(c,0x53dc,2,r.d[1]&65535U) ||
           !core_load(c,0x543e,r.d[0]) || !core_read(c,0x544c,2,value))return false;
        r.pc=(r.d[0]&65535U)>=value?0x1a59e:0x1a59a;return true;
    case 0x1a59a:if(!core_load(c,0x544c,r.d[0]))return false;r.pc=0x1a59e;return true;
    case 0x1a59e:if(!core_write(c,0x53fa,2,r.d[0]&65535U))return false;return am_return(c);

    // 19b96: MOVE.W 53bc/53c0(A5),D4/D5 (high WORDs); ADD.W 53a2/53a6(A5); SUB.W D4/D5 from 53ce 53d0
    // 53d2 53d4 (memory WORDs); TST.W 53fa(A5); BEQ 19bda.
    case 0x19b96:
        if(!core_load(c,0x53bc,r.d[4]) || !core_load(c,0x53c0,r.d[5]))return false;
        if(!core_read(c,0x53a2,2,value))return false;am_word(r.d[4],r.d[4]+value);
        if(!core_read(c,0x53a6,2,value))return false;am_word(r.d[5],r.d[5]+value);
        if(!core_sub_memory(c,0x53ce,r.d[4]) || !core_sub_memory(c,0x53d0,r.d[5]) ||
           !core_sub_memory(c,0x53d2,r.d[4]) || !core_sub_memory(c,0x53d4,r.d[5]) ||
           !core_read(c,0x53fa,2,value))return false;
        r.pc=value?0x19bbe:0x19bda;return true;
    case 0x19bbe:return core_motion(c,0x19bca);
    // MOVE.L D7,D6; MOVEQ #0,D7; MOVE.W 53fa(A5),D7; LSL.L #8,D7; ADD.L D6,D7; BRA 19c28.
    case 0x19bca:
        r.d[6]=r.d[7];r.d[7]=0;if(!core_load(c,0x53fa,r.d[7]))return false;
        r.d[7]=(r.d[7]<<8)+r.d[6];r.pc=0x19c28;return true;
    // BTST #0,53cc(A5); BNE 19bf0.
    case 0x19bda:if(!core_read(c,0x53cc,1,value))return false;r.pc=(value&1U)?0x19bf0:0x19be4;return true;
    case 0x19be4:
        if(!core_read(c,0x53fc,4,value))return false;r.d[7]=value;
        if(!core_write(c,0x53de,4,r.d[7]))return false;r.pc=0x19bf4;return true;
    case 0x19bf0:return am_call(c,0x19a40,0x19bf4);
    // ADD.L 53bc(A5),D7; MOVE.L D7,53c4(A5); BTST #1,53cc(A5); BNE 19c12.
    case 0x19bf4:
        if(!core_read(c,0x53bc,4,value))return false;r.d[7]+=value;
        if(!core_write(c,0x53c4,4,r.d[7]) || !core_read(c,0x53cc,1,value))return false;
        r.pc=(value&2U)?0x19c12:0x19c06;return true;
    case 0x19c06:
        if(!core_read(c,0x5400,4,value))return false;r.d[7]=value;
        if(!core_write(c,0x53e2,4,r.d[7]))return false;r.pc=0x19c16;return true;
    case 0x19c12:return am_call(c,0x19ac8,0x19c16);
    case 0x19c16:
        if(!core_read(c,0x53c0,4,value))return false;r.d[7]+=value;
        if(!core_write(c,0x53c8,4,r.d[7]))return false;return am_call(c,0x19832,0x19c22);
    case 0x19c22:r.pc=r.d[7]<r.d[6]?0x19c44:0x19c28;return true; // CMP.L D6,D7; BCS (unsigned LONG)
    // MOVEQ #0,D5; MOVE.W 53ee(A5),D5; SWAP D5; CMP.L D5,D7; BCS 19c40.
    case 0x19c28:
        r.d[5]=0;if(!core_load(c,0x53ee,r.d[5]))return false;am_swap(r.d[5]);
        r.pc=r.d[7]<r.d[5]?0x19c40:0x19c36;return true;
    case 0x19c36:r.pc=r.d[6]<r.d[5]?0x19c3e:0x19c3c;return true; // CMP.L D5,D6; BCS
    case 0x19c3c:case 0x19c58:r.d[5]=r.d[6];r.pc+=2U;return true; // MOVE.L D6,D5
    case 0x19c3e:r.d[7]=r.d[5];r.pc=0x19c40;return true;
    case 0x19c40:r.pc=0x19c5c;return true;
    case 0x19c44:
        r.d[5]=0;if(!core_load(c,0x53f0,r.d[5]))return false;am_swap(r.d[5]);
        r.pc=r.d[7]>=r.d[5]?0x19c5c:0x19c52;return true; // BCC 19c5c
    case 0x19c52:r.pc=r.d[6]>=r.d[5]?0x19c5a:0x19c58;return true;
    case 0x19c5a:r.d[7]=r.d[5];r.pc=0x19c5c;return true;
    case 0x19c5c:return am_call(c,0x19978,0x19c60);
    case 0x19c60:if(!core_read(c,0x53fa,2,value))return false;r.pc=value?0x19cd6:0x19c68;return true; // TST.W; BNE
    case 0x19c68:if(!core_read(c,0x53cc,1,value))return false;r.pc=(value&1U)?0x19c72:0x19ca0;return true;
    // MOVE.W 53c4(A5),D1; SUB.W 53bc(A5),D1; BEQ 19ca0; BMI 19c92 (N of the WORD difference).
    case 0x19c72:return core_delta(c,0x53c4,0x53bc,0x19ca0,0x19c92,0x19c82);
    // MOVE.W 53c8(A5),D1; SUB.W 53c0(A5),D1; BEQ 19cd6; BMI 19cca.
    case 0x19caa:return core_delta(c,0x53c8,0x53c0,0x19cd6,0x19cca,0x19cba);
    // MOVE.W 53ce(A5),D0; SUBI.W #2c,D0; BMI 19ce6.
    case 0x19c82:if(!core_load(c,0x53ce,r.d[0]))return false;am_word(r.d[0],r.d[0]-0x2cU);r.pc=(r.d[0]&0x8000U)?0x19ce6:0x19c8e;return true;
    case 0x19c8e:r.pc=0x19ca0;return true;
    // MOVE.W 53d2(A5),D0; SUBI.W #114,D0; ADD.W D1,D0; BPL 19ce6.
    case 0x19c92:
        if(!core_load(c,0x53d2,r.d[0]))return false;am_word(r.d[0],r.d[0]-0x114U);am_word(r.d[0],r.d[0]+r.d[1]);
        r.pc=(r.d[0]&0x8000U)?0x19ca0:0x19ce6;return true;
    case 0x19ca0:if(!core_read(c,0x53cc,1,value))return false;r.pc=(value&2U)?0x19caa:0x19cd6;return true;
    case 0x19cba:if(!core_load(c,0x53d0,r.d[0]))return false;am_word(r.d[0],r.d[0]-0x18U);r.pc=(r.d[0]&0x8000U)?0x19ce6:0x19cc6;return true;
    case 0x19cc6:r.pc=0x19cd6;return true;
    // MOVE.W 53d4(A5),D0; SUBI.W #b8,D0; BPL 19ce6 (D1 is not added on this axis).
    case 0x19cca:if(!core_load(c,0x53d4,r.d[0]))return false;am_word(r.d[0],r.d[0]-0xb8U);r.pc=(r.d[0]&0x8000U)?0x19cd6:0x19ce6;return true;
    // MOVE.L 53c4(A5),53bc(A5); MOVE.L 53c8(A5),53c0(A5); BRA 19cee.
    case 0x19cd6:
        if(!core_read(c,0x53c4,4,value) || !core_write(c,0x53bc,4,value) ||
           !core_read(c,0x53c8,4,value) || !core_write(c,0x53c0,4,value))return false;
        r.pc=0x19cee;return true;
    case 0x19ce6:if(!core_write(c,0x53de,4,0) || !core_write(c,0x53e2,4,0))return false;r.pc=0x19cee;return true;
    case 0x19cee:
        if(!core_write(c,0x53ce,2,0x7fff) || !core_write(c,0x53d2,2,0x8000) ||
           !core_write(c,0x53d0,2,0x7fff) || !core_write(c,0x53d4,2,0x8000))return false;
        return am_return(c);

    // 19a40 (X) / 19ac8 (Y) bodies.
    case 0x19a40:return core_axis_start(c,CORE_X,0x19a62,0x19a60);
    case 0x19ac8:return core_axis_start(c,CORE_Y,0x19aea,0x19ae8);
    case 0x19a60:r.d[6]=0;r.pc=0x19a62;return true;
    case 0x19ae8:r.d[6]=0;r.pc=0x19aea;return true;
    // SUB.W D5,D7; BPL.
    case 0x19a62:am_word(r.d[7],r.d[7]-r.d[5]);r.pc=(r.d[7]&0x8000U)?0x19a68:0x19a6a;return true;
    case 0x19aea:am_word(r.d[7],r.d[7]-r.d[5]);r.pc=(r.d[7]&0x8000U)?0x19af0:0x19af2;return true;
    case 0x19a68:r.d[7]=0;r.pc=0x19a6a;return true;
    case 0x19af0:r.d[7]=0;r.pc=0x19af2;return true;
    // ADD.W D6,D7; SUBI.W #margin,D0; BPL.
    case 0x19a6a:
        am_word(r.d[7],r.d[7]+r.d[6]);am_word(r.d[0],r.d[0]-CORE_X.margin_low);
        r.pc=(r.d[0]&0x8000U)?0x19a74:0x19a76;return true;
    case 0x19af2:
        am_word(r.d[7],r.d[7]+r.d[6]);am_word(r.d[0],r.d[0]-CORE_Y.margin_low);
        r.pc=(r.d[0]&0x8000U)?0x19afc:0x19afe;return true;
    case 0x19a74:r.d[0]=0;r.pc=0x19a76;return true;
    case 0x19afc:r.d[0]=0;r.pc=0x19afe;return true;
    // CMP.W D0,D7; BLE (signed WORD).
    case 0x19a76:r.pc=core_signed(r.d[7])<=core_signed(r.d[0])?0x19a7e:0x19a7c;return true;
    case 0x19afe:r.pc=core_signed(r.d[7])<=core_signed(r.d[0])?0x19b06:0x19b04;return true;
    case 0x19a7c:am_word(r.d[7],r.d[0]);r.pc=0x19a7e;return true;
    case 0x19b04:am_word(r.d[7],r.d[0]);r.pc=0x19b06;return true;
    // SUBI.W #margin,D1; BMI.
    case 0x19a7e:am_word(r.d[1],r.d[1]-CORE_X.margin_high);r.pc=(r.d[1]&0x8000U)?0x19a88:0x19a86;return true;
    case 0x19b06:am_word(r.d[1],r.d[1]-CORE_Y.margin_high);r.pc=(r.d[1]&0x8000U)?0x19b10:0x19b0e;return true;
    case 0x19a86:r.d[1]=0;r.pc=0x19a88;return true;
    case 0x19b0e:r.d[1]=0;r.pc=0x19b10;return true;
    // CMP.W D1,D7; BGE (signed WORD).
    case 0x19a88:r.pc=core_signed(r.d[7])>=core_signed(r.d[1])?0x19a90:0x19a8e;return true;
    case 0x19b10:r.pc=core_signed(r.d[7])>=core_signed(r.d[1])?0x19b18:0x19b16;return true;
    case 0x19a8e:am_word(r.d[7],r.d[1]);r.pc=0x19a90;return true;
    case 0x19b16:am_word(r.d[7],r.d[1]);r.pc=0x19b18;return true;
    // SWAP D7; TST.L D7; BMI (no +7 for negative values).
    case 0x19a90:am_swap(r.d[7]);r.pc=(r.d[7]&CORE_SIGN)?0x19a9a:0x19a98;return true;
    case 0x19b18:am_swap(r.d[7]);r.pc=(r.d[7]&CORE_SIGN)?0x19b22:0x19b20;return true;
    case 0x19a98:r.d[7]+=7U;r.pc=0x19a9a;return true;
    case 0x19b20:r.d[7]+=7U;r.pc=0x19b22;return true;
    case 0x19a9a:return core_axis_limit(c,CORE_X,0x19aa8,0x19aa6);
    case 0x19b22:return core_axis_limit(c,CORE_Y,0x19b30,0x19b2e);
    case 0x19aa6:r.d[7]=r.d[0];r.pc=0x19aa8;return true;
    case 0x19b2e:r.d[7]=r.d[0];r.pc=0x19b30;return true;
    // ADD.L D7,D0; BGE (N xor V of the LONG sum).
    case 0x19aa8:other=r.d[0];r.d[0]=other+r.d[7];r.pc=core_add_ge_long(other,r.d[7])?0x19ab0:0x19aae;return true;
    case 0x19b30:other=r.d[0];r.d[0]=other+r.d[7];r.pc=core_add_ge_long(other,r.d[7])?0x19b38:0x19b36;return true;
    case 0x19aae:r.d[7]-=r.d[0];r.pc=0x19ab0;return true; // SUB.L D0,D7
    case 0x19b36:r.d[7]-=r.d[0];r.pc=0x19b38;return true;
    // X: SUB.L 53de(A5),D7; TST.L D7; BMI 19abc.
    case 0x19ab0:if(!core_read(c,0x53de,4,value))return false;r.d[7]-=value;r.pc=(r.d[7]&CORE_SIGN)?0x19abc:0x19aba;return true;
    // Y: MOVE.L D7,53e2(A5); SUB.L 53e2(A5),D7 (live read of the stored LONG); TST.L D7; BMI 19b48.
    case 0x19b38:
        if(!core_write(c,0x53e2,4,r.d[7]) || !core_read(c,0x53e2,4,value))return false;
        r.d[7]-=value;r.pc=(r.d[7]&CORE_SIGN)?0x19b48:0x19b46;return true;
    case 0x19aba:r.d[7]+=1U;r.pc=0x19abc;return true;
    case 0x19b46:r.d[7]+=1U;r.pc=0x19b48;return true;
    // ASR.L #1,D7; ADD.L 53de(A5),D7; MOVE.L D7,53de(A5); RTS.
    case 0x19abc:
        r.d[7]=core_asr_long(r.d[7],1);if(!core_read(c,0x53de,4,value))return false;r.d[7]+=value;
        if(!core_write(c,0x53de,4,r.d[7]))return false;return am_return(c);
    // ASR.L #1,D7; ADD.L 53e2(A5),D7; RTS (no store).
    case 0x19b48:r.d[7]=core_asr_long(r.d[7],1);if(!core_read(c,0x53e2,4,value))return false;r.d[7]+=value;return am_return(c);

    // 19978: BSR 198ee; CMPA.W #0,A1; BNE 1998e / MOVE.L D0,53c4; MOVE.L D1,53c8; RTS.
    case 0x19978:return am_call(c,0x198ee,0x1997c);
    case 0x1997c:r.pc=r.a[1]?0x1998e:0x19984;return true;
    case 0x19984:if(!core_write(c,0x53c4,4,r.d[0]) || !core_write(c,0x53c8,4,r.d[1]))return false;return am_return(c);
    // ADD.L D1,D3; CMP.L D1,D3; BPL 19998 (N only).
    case 0x1998e:r.d[3]+=r.d[1];r.pc=((r.d[3]-r.d[1])&CORE_SIGN)?0x19996:0x19998;return true;
    case 0x19996:value=r.d[1];r.d[1]=r.d[3];r.d[3]=value;r.pc=0x19998;return true; // EXG.L D1,D3
    // SUB.L 53c8(A5),D1; BMI 199a4 / ADD.L D1,53c8(A5).
    case 0x19998:if(!core_read(c,0x53c8,4,value))return false;r.d[1]-=value;r.pc=(r.d[1]&CORE_SIGN)?0x199a4:0x199a0;return true;
    case 0x199a0:if(!core_add_memory(c,0x53c8,r.d[1],4))return false;r.pc=0x199a4;return true;
    // SUB.L 53c8(A5),D3 (the updated LONG); BPL 199b0 / ADD.L D3,53c8(A5).
    case 0x199a4:if(!core_read(c,0x53c8,4,value))return false;r.d[3]-=value;r.pc=(r.d[3]&CORE_SIGN)?0x199ac:0x199b0;return true;
    case 0x199ac:if(!core_add_memory(c,0x53c8,r.d[3],4))return false;r.pc=0x199b0;return true;
    case 0x199b0:r.d[2]+=r.d[0];r.pc=((r.d[2]-r.d[0])&CORE_SIGN)?0x199b8:0x199ba;return true;
    case 0x199b8:value=r.d[0];r.d[0]=r.d[2];r.d[2]=value;r.pc=0x199ba;return true; // EXG.L D0,D2
    case 0x199ba:if(!core_read(c,0x53c4,4,value))return false;r.d[0]-=value;r.pc=(r.d[0]&CORE_SIGN)?0x199c6:0x199c2;return true;
    case 0x199c2:if(!core_add_memory(c,0x53c4,r.d[0],4))return false;r.pc=0x199c6;return true;
    case 0x199c6:if(!core_read(c,0x53c4,4,value))return false;r.d[2]-=value;r.pc=(r.d[2]&CORE_SIGN)?0x199ce:0x199d2;return true;
    case 0x199ce:if(!core_add_memory(c,0x53c4,r.d[2],4))return false;r.pc=0x199d2;return true;

    // 19d08: MOVE.W #7fff,53f2/53f6; MOVE.W #8000,53f4/53f8; then 19d20 loads D0/D1 and BSR 19802.
    case 0x19d08:
        if(!core_write(c,0x53f2,2,0x7fff) || !core_write(c,0x53f6,2,0x7fff) ||
           !core_write(c,0x53f4,2,0x8000) || !core_write(c,0x53f8,2,0x8000))return false;
        return core_motion(c,0x19d2c);
    // SWAP D7; MOVE.W D7,-(A7); MOVE.W 5418(A5),D6; CMP.W 53ee(A5),D6; BCS 19d40.
    case 0x19d2c:
        am_swap(r.d[7]);if(!am_push(c,2,r.d[7]&65535U) || !core_load(c,0x5418,r.d[6]) || !core_read(c,0x53ee,2,value))return false;
        r.pc=(r.d[6]&65535U)<value?0x19d40:0x19d3c;return true;
    case 0x19d3c:if(!core_load(c,0x53ee,r.d[6]))return false;r.pc=0x19d40;return true;
    case 0x19d40:r.pc=(r.d[7]&65535U)>=(r.d[6]&65535U)?0x19d48:0x19d46;return true; // CMP.W D6,D7; BCC
    case 0x19d46:am_word(r.d[7],r.d[6]);r.pc=0x19d48;return true;
    case 0x19d48:return am_call(c,0x19d98,0x19d4c);
    // MOVE.W (A7)+,D7; CMP.W 53f0(A5),D7; BCS 19d5a.
    case 0x19d4c:
        if(!am_pop(c,2,value))return false;am_word(r.d[7],value);if(!core_read(c,0x53f0,2,value))return false;
        r.pc=(r.d[7]&65535U)<value?0x19d5a:0x19d56;return true;
    case 0x19d56:if(!core_load(c,0x53f0,r.d[7]))return false;r.pc=0x19d5a;return true;
    case 0x19d5a:return am_call(c,0x19d98,0x19d5e);
    // MOVE.W 53a2(A5),D0; ADD.W D0,53f2(A5); ADDI.W #140,D0; ADD.W 53f4(A5),D0; BVC 19d76.
    case 0x19d5e:
        if(!core_load(c,0x53a2,r.d[0]) || !core_add_memory(c,0x53f2,r.d[0]&65535U,2))return false;
        am_word(r.d[0],r.d[0]+0x140U);if(!core_read(c,0x53f4,2,value))return false;
        other=r.d[0]&65535U;am_word(r.d[0],other+value);
        r.pc=core_add_overflow_word(other,value)?0x19d72:0x19d76;return true;
    case 0x19d72:am_word(r.d[0],0x7fff);r.pc=0x19d76;return true;
    case 0x19d76:
        if(!core_write(c,0x53f4,2,r.d[0]&65535U) || !core_load(c,0x53a6,r.d[1]) ||
           !core_add_memory(c,0x53f6,r.d[1]&65535U,2))return false;
        am_word(r.d[1],r.d[1]+0x100U);if(!core_read(c,0x53f8,2,value))return false;
        other=r.d[1]&65535U;am_word(r.d[1],other+value);
        r.pc=core_add_overflow_word(other,value)?0x19d8e:0x19d92;return true;
    case 0x19d8e:am_word(r.d[1],0x7fff);r.pc=0x19d92;return true;
    case 0x19d92:if(!core_write(c,0x53f8,2,r.d[1]&65535U))return false;return am_return(c);
    // 19d98: SWAP D7; CLR.W D7; BSR 198ee.
    case 0x19d98:am_swap(r.d[7]);am_word(r.d[7],0);return am_call(c,0x198ee,0x19da0);
    // SWAP D0-D3; ADD.W D0,D2; ADD.W D1,D3; CMP.W D0,D2; BGE 19db4 (signed WORD).
    case 0x19da0:
        am_swap(r.d[0]);am_swap(r.d[1]);am_swap(r.d[2]);am_swap(r.d[3]);
        am_word(r.d[2],r.d[2]+r.d[0]);am_word(r.d[3],r.d[3]+r.d[1]);
        r.pc=core_signed(r.d[2])>=core_signed(r.d[0])?0x19db4:0x19db2;return true;
    case 0x19db2:value=r.d[0];r.d[0]=r.d[2];r.d[2]=value;r.pc=0x19db4;return true; // EXG.L D0,D2
    case 0x19db4:r.pc=core_signed(r.d[3])>=core_signed(r.d[1])?0x19dbc:0x19dba;return true;
    case 0x19dba:value=r.d[1];r.d[1]=r.d[3];r.d[3]=value;r.pc=0x19dbc;return true; // EXG.L D1,D3
    // CMP.W mem,Dn; BGE/BLE (signed WORD); MOVE.W Dn,mem.
    case 0x19dbc:if(!core_read(c,0x53f2,2,value))return false;r.pc=core_signed(r.d[0])>=core_signed(value)?0x19dc8:0x19dc4;return true;
    case 0x19dc4:if(!core_write(c,0x53f2,2,r.d[0]&65535U))return false;r.pc=0x19dc8;return true;
    case 0x19dc8:if(!core_read(c,0x53f6,2,value))return false;r.pc=core_signed(r.d[1])>=core_signed(value)?0x19dd4:0x19dd0;return true;
    case 0x19dd0:if(!core_write(c,0x53f6,2,r.d[1]&65535U))return false;r.pc=0x19dd4;return true;
    case 0x19dd4:if(!core_read(c,0x53f4,2,value))return false;r.pc=core_signed(r.d[2])<=core_signed(value)?0x19de0:0x19ddc;return true;
    case 0x19ddc:if(!core_write(c,0x53f4,2,r.d[2]&65535U))return false;r.pc=0x19de0;return true;
    case 0x19de0:if(!core_read(c,0x53f8,2,value))return false;r.pc=core_signed(r.d[3])<=core_signed(value)?0x19dec:0x19de8;return true;
    case 0x19de8:if(!core_write(c,0x53f8,2,r.d[3]&65535U))return false;r.pc=0x19dec;return true;

    // 1a3d6: MOVE.L 5408(A5),D0; MOVE.L D0,D1; ASR.L #4,D1; NEG.L D0; ADD.L D1,D0; MOVE.L D0,5408(A5);
    // ADDI.L #8000,D0; SWAP D0; CMPI.W #8,D0; BLE 1a3f8 (signed WORD).
    case 0x1a3d6:
        if(!core_read(c,0x5408,4,value))return false;r.d[0]=value;r.d[1]=core_asr_long(r.d[0],4);
        r.d[0]=(0U-r.d[0])+r.d[1];if(!core_write(c,0x5408,4,r.d[0]))return false;
        r.d[0]+=0x8000U;am_swap(r.d[0]);r.pc=core_signed(r.d[0])<=8?0x1a3f8:0x1a3f6;return true;
    case 0x1a3f6:r.d[0]=8;r.pc=0x1a3f8;return true;
    case 0x1a3f8:r.pc=core_signed(r.d[0])>=-8?0x1a402:0x1a400;return true; // CMPI.W #fff8,D0; BGE
    case 0x1a400:r.d[0]=0xfffffff8U;r.pc=0x1a402;return true; // MOVEQ #-8,D0
    // MOVE.W 5404(A5),5406(A5); MOVE.W D0,5404(A5); RTS.
    case 0x1a402:
        if(!core_read(c,0x5404,2,value) || !core_write(c,0x5406,2,value) || !core_write(c,0x5404,2,r.d[0]&65535U))return false;
        return am_return(c);

    // 1a442: MOVEA.L 540e(A5),A0; CMPA.W #0,A0; BNE 1a450.
    case 0x1a442:if(!core_read(c,0x540e,4,value))return false;r.a[0]=value;r.pc=value?0x1a450:0x1a44e;return true;
    // MOVE.W (A0),D7; CMPI.W #ffff,D7; BNE 1a45c.
    case 0x1a450:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[7],value);r.pc=value!=0xffffU?0x1a45c:0x1a45a;return true;
    // CMP.W 5418(A5),D7; BLS 1a466 (D7.W <= phase, unsigned).
    case 0x1a45c:if(!core_read(c,0x5418,2,value))return false;r.pc=(r.d[7]&65535U)<=value?0x1a466:0x1a464;return true;
    case 0x1a466:return am_call(c,0x1a470,0x1a46a);
    case 0x1a46a:if(!core_write(c,0x540e,4,r.a[0]))return false;return am_return(c);
    default:return am_error(c,"unsupported animation scene core PC");
    }
}
}
