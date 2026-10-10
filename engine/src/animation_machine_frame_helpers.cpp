#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// BCC after JSR 289e / JSR 49392: consumes the C those routines return (known only when modeled).
bool helper_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"frame helper caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// Two's-complement WORD value for signed compares (BLE/BGT/BLT/BGE), without implementation-defined casts.
std::int32_t helper_signed(std::uint32_t value) {
    const std::int32_t low=static_cast<std::int32_t>(value&0x7fffU);
    return (value&0x8000U)?low-0x8000:low;
}
// MOVE.B/MOVE.W mem,Dn: one live read, only the low BYTE/WORD replaced.
bool helper_load(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t& reg) {
    std::uint32_t value=0;if(!am_read(c,address,size,value))return false;
    if(size==1)am_byte(reg,value);else am_word(reg,value);return true;
}
// BSET Dn,<memory>: BYTE operand, bit number taken modulo 8.
bool helper_bset(AnimationMachineContext& c,std::uint32_t address,std::uint32_t bit) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    return am_write(c,address,1,value|(1U<<(bit&7U)));
}
// DBRA Dn: WORD decrement, loop until the WORD becomes ffff (upper WORD untouched).
void helper_dbra(AnimationMachineContext& c,std::uint32_t& reg,std::uint32_t loop_pc,std::uint32_t exit_pc) {
    am_word(reg,reg-1U);c.s.pc=(reg&65535U)!=0xffffU?loop_pc:exit_pc;
}
// SUB.W src,Dn then BLT/BGE: N xor V is the exact signed comparison of the old WORDs.
bool helper_sub_less(std::uint32_t& reg,std::uint32_t src) {
    const bool less=helper_signed(reg)<helper_signed(src);am_word(reg,reg-src);return less;
}
// MOVEM.W (A1),D0-D3; ADD.W 42(A0),D0; ADD.W 46(A0),D1; MOVEM.W D0-D3,d16(A5).
// WORD loads sign-extend into the whole LONG; stores are ascending D0..D3 WORDs.
bool helper_region(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    for(unsigned int i=0;i<4;++i) {
        if(!am_read(c,r.a[1]+2U*i,2,value))return false;r.d[i]=am_extend_word(value);
    }
    if(!am_read(c,am_index(r.a[0],0x42),2,value))return false;am_word(r.d[0],r.d[0]+value);
    if(!am_read(c,am_index(r.a[0],0x46),2,value))return false;am_word(r.d[1],r.d[1]+value);
    const std::uint32_t base=am_index(r.a[5],displacement);
    for(unsigned int i=0;i<4;++i)if(!am_write(c,base+2U*i,2,r.d[i]&65535U))return false;
    r.pc=next;return true;
}
// TST.B (A0); BEQ: then SUBQ.B #1,(A0) runs in the following block.
bool helper_counter(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[0],1,value))return false;
    c.s.pc=value?other_pc:zero_pc;return true;
}
bool helper_decrement(AnimationMachineContext& c,std::uint32_t next) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[0],1,value) || !am_write(c,c.s.a[0],1,(value-1U)&255U))return false;
    c.s.pc=next;return true;
}
}
// 480bc frame helper shell (U1): 47642/47656 player flags, 6f1c2, b4a2a region boxes (49392, 1c028,
// 4d9d6, b481e), 4701e/46f52 spatial bins, 2efa6/3c44 loop sound. Existing executors: 289e (readiness,
// known C), 43e38 (cleanup), 3af8/3ac8 (sound). Called units: 1a73c (U2), 49b0c (U6); boundaries without an executor: 4aa88
// e8a48 and 4939c (TRAP #f when A5 != 108000). All A5-relative operands use the live A5.
bool animation_frame_helpers_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // 480bc: JSR 47642(PC), then JSR.L to each helper; 480f0 RTS to the dispatcher.
    case 0x480bc:return am_call(c,0x47642,0x480c0);
    case 0x480c0:return am_call(c,0x1a73c,0x480c6);
    case 0x480c6:return am_call(c,0x49b0c,0x480cc);
    case 0x480cc:return am_call(c,0x4aa88,0x480d2);
    case 0x480d2:return am_call(c,0xb4a2a,0x480d8);
    case 0x480d8:return am_call(c,0x6f1c2,0x480de);
    case 0x480de:return am_call(c,0x4701e,0x480e4);
    case 0x480e4:return am_call(c,0xe8a48,0x480ea);
    case 0x480ea:return am_call(c,0x2efa6,0x480f0);
    // CLR.B 568e(A5); LEA -7348(A5),A0; MOVEQ #0,D0; BSR 47656.
    case 0x47642:
        if(!am_write(c,am_index(r.a[5],0x568e),1,0))return false;
        r.a[0]=am_index(r.a[5],0x8cb8);r.d[0]=0;return am_call(c,0x47656,0x47650);
    // LEA -7258(A5),A0; MOVEQ #1,D0; fall through into the same 47656 body.
    case 0x47650:r.a[0]=am_index(r.a[5],0x8da8);r.d[0]=1;r.pc=0x47656;return true;
    case 0x47656:return am_call(c,0x289e,0x4765c);
    // BCC 47670: consumes the C returned by 289e (CMPI.L equal Clear / ORI CCR Set).
    case 0x4765c:return helper_carry(c,0x47670,0x47660);
    // BTST #7,61(A0); BNE 47670.
    case 0x47660:
        if(!am_read(c,am_index(r.a[0],0x61),1,value))return false;
        r.pc=(value&0x80U)?0x47670:0x4766a;return true;
    // BSET D0,568e(A5) (memory: bit mod 8); RTS.
    case 0x4766a:
        if(!helper_bset(c,am_index(r.a[5],0x568e),r.d[0]))return false;return am_return(c);
    case 0x47670:case 0x480f0:case 0x6f1c2:case 0x2efc8:case 0x2efda:case 0x493ba:case 0x1c03a:
    case 0xb484e:case 0xb4aae:case 0x4701c:case 0x4706a:return am_return(c);
    // MOVE.B 5491(A5),D1; TST.B 5490(A5); SNE D0; MOVE.B D0,5491(A5); BEQ (Z of the MOVE.B result).
    case 0x2efa6:
        if(!helper_load(c,am_index(r.a[5],0x5491),1,r.d[1]) || !am_read(c,am_index(r.a[5],0x5490),1,value))return false;
        am_byte(r.d[0],value?0xffU:0U);
        if(!am_write(c,am_index(r.a[5],0x5491),1,r.d[0]&255U))return false;
        r.pc=(r.d[0]&255U)?0x2efb8:0x2efca;return true;
    case 0x2efb8:r.pc=(r.d[1]&255U)?0x2efc8:0x2efbe;return true;
    case 0x2efbe:am_word(r.d[0],0x1d28);return am_call(c,0x3af8,0x2efc8);
    case 0x2efca:r.pc=(r.d[1]&255U)?0x2efd0:0x2efda;return true;
    case 0x2efd0:am_word(r.d[0],0x1d28);return am_call(c,0x3c44,0x2efda);
    // MOVE.W D0,-(A7); LEA -327e(A5),A0; MOVE.W -3276(A5),D1.
    case 0x3c44:
        if(!am_push(c,2,r.d[0]&65535U))return false;
        r.a[0]=am_index(r.a[5],0xcd82);
        if(!helper_load(c,am_index(r.a[5],0xcd8a),2,r.d[1]))return false;r.pc=0x3c4e;return true;
    // CMP.W -3274(A5),D1; BEQ 3c6a.
    case 0x3c4e:
        if(!am_read(c,am_index(r.a[5],0xcd8c),2,value))return false;
        r.pc=(r.d[1]&65535U)==value?0x3c6a:0x3c56;return true;
    // LEA (A0,D1.W),A1; ADDQ.W #2,D1; ANDI.W #6,D1; CMP.W (A1),D0; BNE 3c68.
    case 0x3c56:
        r.a[1]=am_index(r.a[0],r.d[1]);am_word(r.d[1],r.d[1]+2U);am_word(r.d[1],r.d[1]&6U);
        if(!am_read(c,r.a[1],2,value))return false;r.pc=(r.d[0]&65535U)!=value?0x3c68:0x3c66;return true;
    case 0x3c66:if(!am_write(c,r.a[1],2,0))return false;r.pc=0x3c68;return true;
    case 0x3c68:r.pc=0x3c4e;return true;
    case 0x3c6a:r.d[0]=0x14;return am_call(c,0x3ac8,0x3c70);
    // MOVE.B (A7),D0: live stack BYTE (upper BYTE of the pushed WORD); BSR 3ac8.
    case 0x3c70:
        if(!helper_load(c,r.a[7],1,r.d[0]))return false;return am_call(c,0x3ac8,0x3c76);
    // MOVE.W (A7)+,D0; BRA 3ac8 (its RTS returns to the 3c44 caller).
    case 0x3c76:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.pc=0x3ac8;return true;
    // MOVE.W #8000,5d48(A5); MOVEQ #0,D0; JSR 49392.
    case 0xb4a2a:
        if(!am_write(c,am_index(r.a[5],0x5d48),2,0x8000))return false;r.d[0]=0;return am_call(c,0x49392,0xb4a38);
    case 0xb4a38:return helper_carry(c,0xb4a5e,0xb4a3c);
    case 0xb4a3c:r.d[0]=0;return am_call(c,0x1c028,0xb4a44);
    // CMPA.W #0,A1: sign-extended 0 against the whole A1.
    case 0xb4a44:r.pc=r.a[1]?0xb4a4c:0xb4a5e;return true;
    case 0xb4a4c:return helper_region(c,0x5d48,0xb4a5e);
    case 0xb4a5e:
        if(!am_write(c,am_index(r.a[5],0x5d50),2,0x8000))return false;r.d[0]=1;return am_call(c,0x49392,0xb4a6c);
    case 0xb4a6c:return helper_carry(c,0xb4a92,0xb4a70);
    case 0xb4a70:r.d[0]=1;return am_call(c,0x1c028,0xb4a78);
    case 0xb4a78:r.pc=r.a[1]?0xb4a80:0xb4a92;return true;
    case 0xb4a80:return helper_region(c,0x5d50,0xb4a92);
    // LEA 5d58(A5),A0; TST.B (A0); BEQ / SUBQ.B #1,(A0); ADDQ.W #2,A0 (whole An) twice; JSR b481e(PC).
    case 0xb4a92:r.a[0]=am_index(r.a[5],0x5d58);return helper_counter(c,0xb4a9e,0xb4a9c);
    case 0xb4a9c:return helper_decrement(c,0xb4a9e);
    case 0xb4a9e:r.a[0]+=2U;return helper_counter(c,0xb4aa8,0xb4aa6);
    case 0xb4aa6:return helper_decrement(c,0xb4aa8);
    case 0xb4aa8:r.a[0]+=2U;return am_call(c,0xb481e,0xb4aae);
    // CMPA.L #108000,A5; BEQ 4939e; otherwise 4939c TRAP #f (boundary).
    case 0x49392:r.pc=r.a[5]==0x108000U?0x4939e:0x4939c;return true;
    // LEA -7348(A5),A0; ANDI.W #1,D0 (clears C); BEQ 493ae.
    case 0x4939e:
        r.a[0]=am_index(r.a[5],0x8cb8);am_word(r.d[0],r.d[0]&1U);r.carry=AnimationCarryClear;
        r.pc=(r.d[0]&65535U)?0x493aa:0x493ae;return true;
    case 0x493aa:r.a[0]=am_index(r.a[5],0x8da8);r.pc=0x493ae;return true;
    // BTST D0,568e(A5) (memory: bit mod 8, C unchanged); BEQ 493ba.
    case 0x493ae:
        if(!am_read(c,am_index(r.a[5],0x568e),1,value))return false;
        r.pc=(value&(1U<<(r.d[0]&7U)))?0x493b6:0x493ba;return true;
    case 0x493b6:r.carry=AnimationCarrySet;r.pc=0x493ba;return true; // ORI #1,CCR
    // MOVE.W D0,-(A7); JSR 4d9d6.
    case 0x1c028:if(!am_push(c,2,r.d[0]&65535U))return false;return am_call(c,0x4d9d6,0x1c030);
    // MOVE.W (A7)+,D0; CMPA.W #0,A0 (whole A0); BEQ 1c03c.
    case 0x1c030:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.pc=r.a[0]?0x1c03a:0x1c03c;return true;
    case 0x1c03c:
        r.a[0]=am_index(r.a[5],0x8cb8);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&65535U)?0x1c048:0x1c04c;return true;
    case 0x1c048:r.a[0]=am_index(r.a[5],0x8da8);r.pc=0x1c04c;return true;
    case 0x1c04c:if(!am_read(c,am_index(r.a[0],0x56),4,value))return false;r.a[1]=value;return am_return(c);
    // LEA 5cba(A5),A4; TST.B D0; BEQ 4d9e4 / LEA 5ce6(A5),A4.
    case 0x4d9d6:r.a[4]=am_index(r.a[5],0x5cba);r.pc=(r.d[0]&255U)?0x4d9e0:0x4d9e4;return true;
    case 0x4d9e0:r.a[4]=am_index(r.a[5],0x5ce6);r.pc=0x4d9e4;return true;
    case 0x4d9e4:if(!am_read(c,r.a[4],2,value))return false;r.pc=value?0x4d9f2:0x4d9ea;return true;
    case 0x4d9ea:r.a[0]=0;return am_return(c);
    // MOVE.L A6,D0; MOVE.W 6(A4),D0; BNE 4da00.
    case 0x4d9f2:
        r.d[0]=r.a[6];if(!helper_load(c,am_index(r.a[4],6),2,r.d[0]))return false;
        r.pc=(r.d[0]&65535U)?0x4da00:0x4d9fc;return true;
    case 0x4d9fc:r.a[0]=am_extend_word(r.d[0]);return am_return(c); // MOVEA.W D0,A0
    case 0x4da00:
        r.a[0]=r.d[0];if(!am_read(c,am_index(r.a[4],8),4,value))return false;r.a[1]=value;return am_return(c);
    // MOVE.W -7ff2(A5),D0; ANDI.W #1,D0; BNE b4836.
    case 0xb481e:
        if(!helper_load(c,am_index(r.a[5],0x800e),2,r.d[0]))return false;am_word(r.d[0],r.d[0]&1U);
        r.pc=(r.d[0]&65535U)?0xb4836:0xb482a;return true;
    case 0xb482a:r.a[1]=am_index(r.a[5],0x5d5c);r.a[2]=am_index(r.a[5],0x5d98);r.pc=0xb483e;return true;
    case 0xb4836:r.a[1]=am_index(r.a[5],0x5d98);r.a[2]=am_index(r.a[5],0x5dd4);r.pc=0xb483e;return true;
    case 0xb483e:r.d[0]=0;r.pc=0xb4840;return true;
    case 0xb4840:r.pc=r.a[1]==r.a[2]?0xb484e:0xb4846;return true; // CMPA.L A1,A2; BEQ
    // MOVE.W D0,(A1); ADDA.W #a,A1; BRA b4840.
    case 0xb4846:
        if(!am_write(c,r.a[1],2,r.d[0]&65535U))return false;r.a[1]=am_index(r.a[1],0xa);r.pc=0xb4840;return true;
    // LEA 5646(A5),A0; MOVEQ #0,D0; 9 x MOVE.L D0,(A0)+; MOVE.W #7,567c(A5); LEA 561a(A5),A0.
    case 0x4701e:
        r.a[0]=am_index(r.a[5],0x5646);r.d[0]=0;
        for(unsigned int i=0;i<9;++i){if(!am_write(c,r.a[0],4,0))return false;r.a[0]+=4U;}
        if(!am_write(c,am_index(r.a[5],0x567c),2,7))return false;r.a[0]=am_index(r.a[5],0x561a);r.pc=0x47040;return true;
    case 0x47040:
        if(!helper_load(c,am_index(r.a[0],0x2a),2,r.d[0]))return false;r.pc=(r.d[0]&65535U)?0x47048:0x47054;return true;
    // SUBQ.W #1,D0; MOVE.W D0,2a(A0); JSR 43e38.
    case 0x47048:
        am_word(r.d[0],r.d[0]-1U);if(!am_write(c,am_index(r.a[0],0x2a),2,r.d[0]&65535U))return false;
        return am_call(c,0x43e38,0x47054);
    // TST.W 26(A0); BMI 47060.
    case 0x47054:
        if(!am_read(c,am_index(r.a[0],0x26),2,value))return false;r.pc=(value&0x8000U)?0x47060:0x4705c;return true;
    case 0x4705c:return am_call(c,0x46f52,0x47060);
    // LEA -2c(A0),A0; SUBQ.W #1,567c(A5); BCC 47040 (no borrow: the old WORD was nonzero).
    case 0x47060:
        r.a[0]=am_index(r.a[0],0xffd4);
        if(!am_read(c,am_index(r.a[5],0x567c),2,value) || !am_write(c,am_index(r.a[5],0x567c),2,(value-1U)&65535U))return false;
        r.pc=value?0x47040:0x4706a;return true;
    // MOVEA.L 26(A0),A1; MOVE.W 1c/20/14/18(A0),D0/D1/D2/D3; CMP.W D2,D0; BLE 46f6e.
    case 0x46f52:
        if(!am_read(c,am_index(r.a[0],0x26),4,value))return false;r.a[1]=value;
        if(!helper_load(c,am_index(r.a[0],0x1c),2,r.d[0]) || !helper_load(c,am_index(r.a[0],0x20),2,r.d[1]) ||
           !helper_load(c,am_index(r.a[0],0x14),2,r.d[2]) || !helper_load(c,am_index(r.a[0],0x18),2,r.d[3]))return false;
        r.pc=helper_signed(r.d[0])<=helper_signed(r.d[2])?0x46f6e:0x46f6c;return true;
    case 0x46f6c:value=r.d[2];r.d[2]=r.d[0];r.d[0]=value;r.pc=0x46f6e;return true; // EXG.L D2,D0
    case 0x46f6e:r.pc=helper_signed(r.d[1])<=helper_signed(r.d[3])?0x46f76:0x46f74;return true;
    case 0x46f74:value=r.d[3];r.d[3]=r.d[1];r.d[1]=value;r.pc=0x46f76;return true; // EXG.L D3,D1
    // MOVEM.W (A1)+,D4-D7 (sign-extended); ADDQ.W #1,D7; LSL.W #3 D4-D7; D6+=D4; D7+=D5; D0+=D4;
    // D1+=D5; D2+=D6; D3+=D7 (WORD); MOVE.W 567c(A5),D7; MOVEQ #0,D6; MOVE.B (A1),D6; ROL.B #2,D6;
    // ANDI.B #3,D6; SUBQ.W #3,D6; BCC 46fb0 (no WORD borrow).
    case 0x46f76:
        for(unsigned int i=4;i<8;++i){if(!am_read(c,r.a[1],2,value))return false;r.d[i]=am_extend_word(value);r.a[1]+=2U;}
        am_word(r.d[7],r.d[7]+1U);
        for(unsigned int i=4;i<8;++i)am_word(r.d[i],(r.d[i]&65535U)<<3);
        am_word(r.d[6],r.d[6]+r.d[4]);am_word(r.d[7],r.d[7]+r.d[5]);
        am_word(r.d[0],r.d[0]+r.d[4]);am_word(r.d[1],r.d[1]+r.d[5]);
        am_word(r.d[2],r.d[2]+r.d[6]);am_word(r.d[3],r.d[3]+r.d[7]);
        if(!helper_load(c,am_index(r.a[5],0x567c),2,r.d[7]))return false;
        r.d[6]=0;if(!helper_load(c,r.a[1],1,r.d[6]))return false;
        value=r.d[6]&255U;am_byte(r.d[6],(value<<2)|(value>>6));am_byte(r.d[6],r.d[6]&3U);
        value=r.d[6]&65535U;am_word(r.d[6],value-3U);r.pc=value>=3U?0x46fb0:0x46fa4;return true;
    case 0x46fa4:am_word(r.d[6],~r.d[6]);r.a[1]=am_index(r.a[5],0x5669);r.pc=0x46faa;return true; // NOT.W D6
    // BSET D7,-(A1); DBRA D6,46faa.
    case 0x46faa:
        r.a[1]-=1U;if(!helper_bset(c,r.a[1],r.d[7]))return false;helper_dbra(c,r.d[6],0x46faa,0x46fb0);return true;
    // MOVE.W #ffa0,D4; MOVE.W #1ff,D5; CMP.W D5,D0; BGT 4701c.
    case 0x46fb0:
        am_word(r.d[4],0xffa0);am_word(r.d[5],0x01ff);
        r.pc=helper_signed(r.d[0])>helper_signed(r.d[5])?0x4701c:0x46fbe;return true;
    case 0x46fbe:r.pc=helper_sub_less(r.d[2],r.d[4])?0x4701c:0x46fc4;return true; // SUB.W D4,D2; BLT
    case 0x46fc4:r.pc=helper_sub_less(r.d[0],r.d[4])?0x46fca:0x46fcc;return true; // SUB.W D4,D0; BGE
    case 0x46fca:r.d[0]=0;r.pc=0x46fcc;return true;
    // CMP.W D5,D1; BLE 46fd4 / MOVE.W D5,D1 (the original clamps D1 here, not D2).
    case 0x46fcc:r.pc=helper_signed(r.d[1])<=helper_signed(r.d[5])?0x46fd4:0x46fd2;return true;
    case 0x46fd2:am_word(r.d[1],r.d[5]);r.pc=0x46fd4;return true;
    case 0x46fd4:
        am_word(r.d[4],0x0080);am_word(r.d[5],0x01ff);
        r.pc=helper_signed(r.d[1])>helper_signed(r.d[5])?0x4701c:0x46fe2;return true;
    case 0x46fe2:r.pc=helper_sub_less(r.d[3],r.d[4])?0x4701c:0x46fe8;return true; // SUB.W D4,D3; BLT
    case 0x46fe8:r.pc=helper_sub_less(r.d[1],r.d[4])?0x46fee:0x46ff0;return true; // SUB.W D4,D1; BGE
    case 0x46fee:r.d[1]=0;r.pc=0x46ff0;return true;
    case 0x46ff0:r.pc=helper_signed(r.d[3])<=helper_signed(r.d[5])?0x46ff8:0x46ff6;return true;
    case 0x46ff6:am_word(r.d[3],r.d[5]);r.pc=0x46ff8;return true;
    // LSR.W #5 D0/D2; SUB.W D0,D2; LSR.W #5 D1/D3; SUB.W D1,D3; LEA 5646(A5),A1; ADDA.W D0,A1.
    case 0x46ff8:
        am_word(r.d[0],(r.d[0]&65535U)>>5);am_word(r.d[2],(r.d[2]&65535U)>>5);am_word(r.d[2],r.d[2]-r.d[0]);
        am_word(r.d[1],(r.d[1]&65535U)>>5);am_word(r.d[3],(r.d[3]&65535U)>>5);am_word(r.d[3],r.d[3]-r.d[1]);
        r.a[1]=am_index(am_index(r.a[5],0x5646),r.d[0]);r.pc=0x4700a;return true;
    // BSET D7,(A1)+; DBRA D2,4700a.
    case 0x4700a:
        if(!helper_bset(c,r.a[1],r.d[7]))return false;r.a[1]+=1U;helper_dbra(c,r.d[2],0x4700a,0x47010);return true;
    case 0x47010:r.a[1]=am_index(am_index(r.a[5],0x5656),r.d[1]);r.pc=0x47016;return true;
    case 0x47016:
        if(!helper_bset(c,r.a[1],r.d[7]))return false;r.a[1]+=1U;helper_dbra(c,r.d[3],0x47016,0x4701c);return true;
    default:return am_error(c,"unsupported animation frame helper PC");
    }
}
}
