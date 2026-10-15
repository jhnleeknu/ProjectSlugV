#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Fixed ROM WORD table (live bus, no index check as in the original): the 3343c / 33450 sine-like table 4411e read through (A0,Dn.W).
const std::uint32_t OB1C_TABLE=0x4411e;
std::uint32_t ob1c_b(std::uint32_t value) {return value&255U;}
std::uint32_t ob1c_w(std::uint32_t value) {return value&65535U;}
// A WORD as a signed value (BLT / BGT after CMPI.W / TST.W), converted explicitly.
std::int32_t ob1c_signed_w(std::uint32_t value) {
    const std::uint32_t u=value&65535U;return (u&0x8000U)?static_cast<std::int32_t>(u)-65536:static_cast<std::int32_t>(u);
}
// A LONG as a signed value (BLT / BGT after CMPI.L), converted explicitly.
std::int64_t ob1c_signed_l(std::uint32_t value) {
    return (value&0x80000000U)?static_cast<std::int64_t>(value)-4294967296LL:static_cast<std::int64_t>(value);
}
// Arithmetic shift right of a LONG (sign bit refilled explicitly; the count is the original 0..63 register count).
std::uint32_t ob1c_asr_l(std::uint32_t value,unsigned int count) {
    std::uint32_t u=value;for(unsigned int i=0;i<count;++i)u=(u>>1)|(u&0x80000000U);return u;
}
bool ob1c_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob1c_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BTST.B #bit,d16(A6): true when the bit is 1.
bool ob1c_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob1c_get(c,c.s.a[6],displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// MOVE.L #value,(A6) (installed callback LONG).
bool ob1c_install(AnimationMachineContext& c,std::uint32_t value) {return ob1c_put(c,c.s.a[6],0,4,value);}
// BCC.W / BCS.W on a C returned by a callee: clear -> clear_pc, set -> set_pc (BCS: the caller passes the targets swapped).
bool ob1c_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b1c caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.l.
bool ob1c_animation(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.L #l36,36(A0); MOVE.L #l3a,3a(A0); MOVE.W #w54,54(A0) (the d3d7c node).
bool ob1c_spark(AnimationMachineContext& c,std::uint32_t l36,std::uint32_t l3a,std::uint32_t w54) {
    AnimationMachineState& r=c.s;return ob1c_put(c,r.a[0],0x36,4,l36) && ob1c_put(c,r.a[0],0x3a,4,l3a) && ob1c_put(c,r.a[0],0x54,2,w54);
}
// TST.B d(A6); BEQ.W skip_pc (else dec_pc).
bool ob1c_timer(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t dec_pc,std::uint32_t skip_pc) {
    std::uint32_t value=0;if(!ob1c_get(c,c.s.a[6],displacement,1,value))return false;
    c.s.pc=ob1c_b(value)==0U?skip_pc:dec_pc;return true;
}
// SUBQ.B #1,d(A6) (read, wrap, write).
bool ob1c_count(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ob1c_get(c,c.s.a[6],displacement,1,value) || !ob1c_put(c,c.s.a[6],displacement,1,(value+255U)&255U))return false;
    c.s.pc=next_pc;return true;
}
// MOVE.L #imm,d16(A6) written as old + delta (ADD.L / SUB.L / ADDI.L Dn|#imm,d16(A6), 32-bit wrap).
bool ob1c_add_l(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t delta) {
    std::uint32_t value=0;return ob1c_get(c,c.s.a[6],displacement,4,value) && ob1c_put(c,c.s.a[6],displacement,4,(value+delta)&0xffffffffU);
}
// MOVE.L #start,Dn; SUB.L d16(A6),Dn; ASR.L #count,Dn; ADD.L Dn,d16(A6): the easing step of 33394 / 3359c (result in D0).
bool ob1c_ease(AnimationMachineContext& c,std::uint32_t start,std::uint32_t displacement,unsigned int count) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ob1c_get(c,r.a[6],displacement,4,value))return false;r.d[0]=ob1c_asr_l((start-value)&0xffffffffU,count);
    return ob1c_put(c,r.a[6],displacement,4,(value+r.d[0])&0xffffffffU);
}
}
// Objects F4 B1c (224 block starts; contract B1c): N29b = the install 30b6c (N28 30f96) with the 27-slot BRA.W table 30b84 and the
// installed 30c4c / 30cb8 chains, N30b = the install 3323e (N30a 33234) with the state machine 33250, the installs 33280 3329c 332d6
// 33364 333f2 3341a 3349e 33500 3353a 3359c, the 9-slot BRA.W table 335fe and the shared tail 3395c (ends in the N30a block 33a88).
// Boundaries without an executor (callees outside the contract): 317b8 33940 33c78 33d2c 33dce 33e48 343e0 34470 34490 3453a 4c2c4 4d418
// 4d734 4d98a 4d9ba 4db18 4ff96 d3d7c (and every other PC outside the routed ranges: unsupported animation machine PC). 30cb4 BRA.W 30fa0 enters the N28 block 30f9c
// at its second instruction. The 6 consumers read a known C returned by 319f6 (30c7c) / 49fc6 (3328e 3352c) / 4c2c4 (33390 335b4) /
// 4d418 (33a08). B1c has no known-C producer: every MOVE / MOVEQ / TST / CMP / SUB / ADD / AND / ASR / LSL block ends Unknown. No port,
// no bank change, no X / DIV.
bool animation_objects_b1c_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool bit=false;
    switch(r.pc) {
    // ======== N29b: install 30b6c (N28 30f96): BYTE 5e selects the BRA.W table 30b84 (27 slots).
    // MOVE.B 5e(A6),D0; CMPI.B #1b,D0; BCC.W 30bf0.
    case 0x30b6c:if(!ob1c_get(c,r.a[6],0x5e,1,value))return false;am_byte(r.d[0],value);r.pc=ob1c_b(value)>=0x1bU?0x30bf0:0x30b78;return true;
    // ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; JMP 30b84(PC,D0.W) (F1 decision 3: no bound check here; 30b6c bounds the natural index to 0..26).
    case 0x30b78:am_word(r.d[0],r.d[0]&255U);am_word(r.d[0],(r.d[0]*4U)&65535U);r.pc=am_index(0x30b84,r.d[0]);return true;
    // The 27 BRA.W slots of 30b84: k = 24 -> 30cc4, every other k -> 30bf0.
    case 0x30be4:r.pc=0x30cc4;return true;
    case 0x30b84:case 0x30b88:case 0x30b8c:case 0x30b90:case 0x30b94:case 0x30b98:case 0x30b9c:case 0x30ba0:case 0x30ba4:case 0x30ba8:
    case 0x30bac:case 0x30bb0:case 0x30bb4:case 0x30bb8:case 0x30bbc:case 0x30bc0:case 0x30bc4:case 0x30bc8:case 0x30bcc:case 0x30bd0:
    case 0x30bd4:case 0x30bd8:case 0x30bdc:case 0x30be0:case 0x30be8:case 0x30bec:r.pc=0x30bf0;return true;
    case 0x30bf0:return ob1c_animation(c,0x32006,0x30c00);               // animation 32006.
    case 0x30c00:return am_call(c,0x4d8d8,0x30c06);                      // JSR 4d8d8.l.
    case 0x30c06:r.pc=(r.d[0]&0x8000U)!=0U?0x30c16:0x30c0c;return true;   // TST.W D0; BMI.W 30c16.
    case 0x30c0c:if(!ob1c_put(c,r.a[6],0x94,1,1))return false;r.pc=0x30c1c;return true; // MOVE.B #1,94(A6); BRA.W 30c1c.
    case 0x30c16:if(!ob1c_put(c,r.a[6],0x94,1,0xff))return false;r.pc=0x30c1c;return true; // MOVE.B #ff,94(A6) (falls into 30c1c).
    // MOVE.B #60,98(A6); LONG 56 = 0; LONG 76 = 31c92; MOVEQ #0,D0; MOVEQ #40,D1; JSR 4db18.l (boundary).
    case 0x30c1c:
        if(!ob1c_put(c,r.a[6],0x98,1,0x60) || !ob1c_put(c,r.a[6],0x56,4,0) || !ob1c_put(c,r.a[6],0x76,4,0x31c92))return false;
        r.d[0]=0;r.d[1]=0x40;return am_call(c,0x4db18,0x30c3c);
    case 0x30c3c:am_word(r.d[0],0x1ac8);return am_call(c,0x3af8,0x30c46); // MOVE.W #1ac8,D0; JSR 3af8.l.
    case 0x30c46:if(!ob1c_install(c,0x30c4c))return false;r.pc=0x30c4c;return true; // MOVE.L #30c4c,(A6) (falls into the installed 30c4c).
    case 0x30c4c:r.d[0]=0;return am_call(c,0x317b8,0x30c52);              // MOVEQ #0,D0; JSR 317b8(PC) (boundary).
    case 0x30c52:if(!ob1c_put(c,r.a[6],0x88,1,0xff))return false;return am_call(c,0x4d8d8,0x30c5e); // MOVE.B #ff,88(A6); JSR 4d8d8.l.
    case 0x30c5e:r.pc=(r.d[0]&0x80U)!=0U?0x30c8e:0x30c64;return true;     // TST.B D0; BMI.W 30c8e.
    case 0x30c64:return am_call(c,0x3166c,0x30c68);                      // JSR 3166c(PC).
    case 0x30c68:r.pc=((r.d[0]>>5)&1U)==0U?0x30c78:0x30c70;return true;   // BTST.B #5,D0; BEQ.W 30c78.
    case 0x30c70:am_byte(r.d[1],1);return am_call(c,0x31a12,0x30c78);     // MOVE.B #1,D1; JSR 31a12(PC).
    case 0x30c78:return am_call(c,0x319f6,0x30c7c);                      // JSR 319f6(PC).
    case 0x30c7c:return ob1c_carry(c,0x30c80,0x30c86);                   // BCS.W 30c86 (C returned by 319f6).
    case 0x30c80:if(!ob1c_put(c,r.a[6],0x94,1,0xff))return false;r.pc=0x30c86;return true; // MOVE.B #ff,94(A6).
    case 0x30c86:return am_call(c,0x31696,0x30c8a);                      // JSR 31696(PC).
    case 0x30c8a:r.pc=0x30c92;return true;                                // BRA.W 30c92.
    case 0x30c8e:return am_call(c,0x316ac,0x30c92);                      // JSR 316ac(PC).
    case 0x30c92:return am_call(c,0x3165e,0x30c96);                      // JSR 3165e(PC).
    // MOVE.W #8000,8a(A6); MOVE.B 98(A6),D0; BEQ.W 30cae.
    case 0x30c96:
        if(!ob1c_put(c,r.a[6],0x8a,2,0x8000) || !ob1c_get(c,r.a[6],0x98,1,value))return false;am_byte(r.d[0],value);
        r.pc=ob1c_b(value)==0U?0x30cae:0x30ca4;return true;
    // SUBQ.B #1,D0; MOVE.B D0,98(A6); BRA.W 30cb4.
    case 0x30ca4:am_byte(r.d[0],r.d[0]+255U);if(!ob1c_put(c,r.a[6],0x98,1,ob1c_b(r.d[0])))return false;r.pc=0x30cb4;return true;
    case 0x30cae:if(!ob1c_install(c,0x30cb8))return false;r.pc=0x30cb4;return true; // MOVE.L #30cb8,(A6).
    case 0x30cb4:r.pc=0x30fa0;return true;                                // BRA.W 30fa0 (N28 block 30f9c, second instruction).
    case 0x30cb8:r.a[0]=0x31c0c;return am_call(c,0x4ae4a,0x30cc4);       // LEA 31c0c.l,A0; JSR 4ae4a.l.
    case 0x30cc4:am_byte(r.d[1],0);return am_call(c,0x31a12,0x30ccc);     // MOVE.B #0,D1; JSR 31a12(PC).
    case 0x30ccc:r.d[0]=1;r.d[1]=0;return am_call(c,0x4ff96,0x30cd6);    // MOVEQ #1,D0; MOVEQ #0,D1; JSR 4ff96.l (boundary).
    case 0x30cd6:return am_call(c,0xd3d7c,0x30cdc);                      // JSR d3d7c.l (boundary).
    case 0x30cdc:if(!ob1c_spark(c,0xffee0000U,0x240000,0xa))return false;return am_call(c,0xd3d7c,0x30cf8);
    case 0x30cf8:if(!ob1c_spark(c,0xe0000,0x200000,7))return false;return am_call(c,0xd3d7c,0x30d14);
    case 0x30d14:if(!ob1c_spark(c,0xfff40000U,0x10000,7))return false;return am_call(c,0xd3d7c,0x30d30);
    // ... MOVEA.L #30d6c,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0x30d30:
        if(!ob1c_spark(c,0xa0000,0xfffc0000U,5))return false;r.a[0]=0x30d6c;am_word(r.d[0],0x1e);r.a[1]=0x100bf4;return am_call(c,0x2986,0x30d5c);
    case 0x30d5c:r.d[0]=0;r.d[1]=0x10;return am_call(c,0x49214,0x30d66); // MOVEQ #0,D0; MOVEQ #10,D1; JSR 49214.l.
    case 0x30d66:r.pc=0x2a00;return true;                                 // JMP 2a00.l.
    // ======== N30b: install 3323e (N30a 33234): MOVE.W #1a60,D0; JSR 3af8.l; JSR 33be0(PC); BRA.W 33250.
    case 0x3323e:am_word(r.d[0],0x1a60);return am_call(c,0x3af8,0x33248);
    case 0x33248:return am_call(c,0x33be0,0x3324c);                      // JSR 33be0(PC).
    case 0x3324c:r.pc=0x33250;return true;                                // BRA.W 33250.
    // ---- 33250: BYTE 9a = 0, 9b = 1; TST.B 8e(A6); BEQ.W 3329c.
    case 0x33250:
        if(!ob1c_put(c,r.a[6],0x9a,1,0) || !ob1c_put(c,r.a[6],0x9b,1,1) || !ob1c_get(c,r.a[6],0x8e,1,value))return false;
        r.pc=ob1c_b(value)==0U?0x3329c:0x33264;return true;
    case 0x33264:return ob1c_animation(c,0x34bec,0x33274);               // animation 34bec.
    case 0x33274:return am_call(c,0x496c2,0x3327a);                      // JSR 496c2.l.
    case 0x3327a:if(!ob1c_install(c,0x33280))return false;r.pc=0x33280;return true; // MOVE.L #33280,(A6) (falls into 33280).
    case 0x33280:return am_call(c,0x33c0e,0x33284);                      // JSR 33c0e(PC).
    case 0x33284:return am_call(c,0x33c2a,0x33288);                      // JSR 33c2a(PC).
    case 0x33288:return am_call(c,0x49fc6,0x3328e);                      // JSR 49fc6.l.
    case 0x3328e:return ob1c_carry(c,0x33298,0x33292);                   // BCC.W 33298 (C returned by 49fc6).
    case 0x33292:if(!ob1c_install(c,0x3329c))return false;r.pc=0x33298;return true; // MOVE.L #3329c,(A6).
    case 0x33298:r.pc=0x3395c;return true;                                // BRA.W 3395c.
    // ---- 3329c: MOVE.W #1aa8,D0; JSR 3af8.l.
    case 0x3329c:am_word(r.d[0],0x1aa8);return am_call(c,0x3af8,0x332a6);
    case 0x332a6:if(!ob1c_put(c,r.a[6],0x9b,1,2))return false;return ob1c_animation(c,0x34d7c,0x332bc); // BYTE 9b = 2; animation 34d7c.
    // CLR.W 80(A6); CLR.W 82(A6); MOVE.L #80000,3a(A6); JSR 34470(PC) (boundary).
    case 0x332bc:
        if(!ob1c_put(c,r.a[6],0x80,2,0) || !ob1c_put(c,r.a[6],0x82,2,0) || !ob1c_put(c,r.a[6],0x3a,4,0x80000))return false;
        return am_call(c,0x34470,0x332d0);
    case 0x332d0:if(!ob1c_install(c,0x332d6))return false;r.pc=0x332d6;return true; // MOVE.L #332d6,(A6) (falls into 332d6).
    case 0x332d6:return am_call(c,0x33c0e,0x332da);                      // JSR 33c0e(PC).
    // ANDI.B #fc,D0; MOVEQ #0,D1; MOVEQ #1,D2; BTST.B #3,D0; BEQ.W 332f0.
    case 0x332da:
        am_byte(r.d[0],r.d[0]&0xfcU);r.d[1]=0;r.d[2]=1;r.pc=((r.d[0]>>3)&1U)==0U?0x332f0:0x332ea;return true;
    case 0x332ea:r.d[1]=0x40000;r.pc=0x332f0;return true;                 // MOVE.L #40000,D1.
    case 0x332f0:r.pc=((r.d[0]>>2)&1U)==0U?0x332fe:0x332f8;return true;   // BTST.B #2,D0; BEQ.W 332fe.
    case 0x332f8:r.d[1]=0xfffc0000U;r.pc=0x332fe;return true;             // MOVE.L #fffc0000,D1.
    // SUB.L 36(A6),D1; ASR.L D2,D1; ADD.L D1,36(A6); MOVEQ #0,D1; MOVEQ #3,D2; SUB.L 3a(A6),D1; ASR.L D2,D1; ADD.L D1,3a(A6);
    // CMPI.W #2,3a(A6); BLT.W 33336 (signed WORD, the high WORD of the LONG 3a).
    case 0x332fe:
        if(!ob1c_get(c,r.a[6],0x36,4,value))return false;r.d[1]=ob1c_asr_l((r.d[1]-value)&0xffffffffU,r.d[2]&63U);
        if(!ob1c_put(c,r.a[6],0x36,4,(value+r.d[1])&0xffffffffU))return false;
        r.d[1]=0;r.d[2]=3;
        if(!ob1c_get(c,r.a[6],0x3a,4,value))return false;r.d[1]=ob1c_asr_l((r.d[1]-value)&0xffffffffU,3);
        if(!ob1c_put(c,r.a[6],0x3a,4,(value+r.d[1])&0xffffffffU) || !ob1c_get(c,r.a[6],0x3a,2,value))return false;
        r.pc=ob1c_signed_w(value)<2?0x33336:0x33320;return true;
    case 0x33320:return am_call(c,0x33c48,0x33324);                      // JSR 33c48(PC).
    case 0x33324:return am_call(c,0x33d2c,0x33328);                      // JSR 33d2c(PC) (boundary).
    case 0x33328:return am_call(c,0x33dce,0x3332c);                      // JSR 33dce(PC) (boundary).
    case 0x3332c:return am_call(c,0x49fc6,0x33332);                      // JSR 49fc6.l.
    case 0x33332:r.pc=0x3395c;return true;                                // BRA.W 3395c.
    // ---- 33336 (BLT.W from 332fe, BNE.W 3341a, BEQ.W 334dc, BRA.W 3353a): BYTE 8e = 9a = 0, 9b = 2; animation 34d7c.
    case 0x33336:
        if(!ob1c_put(c,r.a[6],0x8e,1,0) || !ob1c_put(c,r.a[6],0x9a,1,0) || !ob1c_put(c,r.a[6],0x9b,1,2))return false;
        return ob1c_animation(c,0x34d7c,0x33358);
    case 0x33358:if(!ob1c_put(c,r.a[6],0x86,2,2) || !ob1c_install(c,0x33364))return false;r.pc=0x33364;return true; // WORD 86 = 2; install (falls into 33364).
    case 0x33364:return am_call(c,0x33c0e,0x33368);                      // JSR 33c0e(PC).
    case 0x33368:r.pc=((r.d[0]>>1)&1U)==0U?0x3337e:0x33370;return true;   // BTST.B #1,D0; BEQ.W 3337e.
    case 0x33370:if(!ob1c_bit(c,0x15,7,bit))return false;r.pc=bit?0x33482:0x3337a;return true; // BTST.B #7,15(A6); BNE.W 33482.
    case 0x3337a:r.pc=0x333ac;return true;                                // BRA.W 333ac.
    case 0x3337e:if(!ob1c_get(c,r.a[6],0x3a,2,value))return false;r.pc=ob1c_signed_w(value)>0?0x333ac:0x33386;return true; // TST.W 3a(A6); BGT.W 333ac.
    // MOVE.W D0,-(A7); MOVEQ #f8,D0; JSR 4c2c4.l (boundary).
    case 0x33386:if(!am_push(c,2,ob1c_w(r.d[0])))return false;r.d[0]=0xfffffff8U;return am_call(c,0x4c2c4,0x33390);
    case 0x33390:return ob1c_carry(c,0x333aa,0x33394);                   // BCC.W 333aa (C returned by 4c2c4).
    // MOVE.L #20000,D0; SUB.L 3a(A6),D0; ASR.L #3,D0; ADD.L D0,3a(A6); MOVE.W #2,86(A6).
    case 0x33394:if(!ob1c_ease(c,0x20000,0x3a,3) || !ob1c_put(c,r.a[6],0x86,2,2))return false;r.pc=0x333aa;return true;
    case 0x333aa:if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.pc=0x333ac;return true; // MOVE.W (A7)+,D0.
    case 0x333ac:r.pc=((r.d[0]>>7)&1U)!=0U?0x3354a:0x333b4;return true;   // BTST.B #7,D0; BNE.W 3354a.
    case 0x333b4:return am_call(c,0x33c78,0x333b8);                      // JSR 33c78(PC) (boundary).
    case 0x333b8:return am_call(c,0x33c48,0x333bc);                      // JSR 33c48(PC).
    case 0x333bc:return am_call(c,0x33d2c,0x333c0);                      // JSR 33d2c(PC) (boundary).
    case 0x333c0:return am_call(c,0x33dce,0x333c4);                      // JSR 33dce(PC) (boundary).
    case 0x333c4:if(!ob1c_get(c,r.a[6],0x8f,1,value))return false;r.pc=ob1c_b(value)==0xcU?0x333d4:0x333ce;return true; // CMPI.B #c,8f(A6); BEQ.W 333d4.
    case 0x333ce:if(!ob1c_put(c,r.a[6],0x86,2,2))return false;r.pc=0x333d4;return true; // MOVE.W #2,86(A6).
    // SUBQ.W #1,86(A6); BPL.W 333e2.
    case 0x333d4:
        if(!ob1c_get(c,r.a[6],0x86,2,value))return false;value=(value+65535U)&65535U;if(!ob1c_put(c,r.a[6],0x86,2,value))return false;
        r.pc=(value&0x8000U)==0U?0x333e2:0x333dc;return true;
    case 0x333dc:if(!ob1c_install(c,0x333f2))return false;r.pc=0x333e2;return true; // MOVE.L #333f2,(A6).
    case 0x333e2:return am_call(c,0x49fc6,0x333e8);                      // JSR 49fc6.l.
    case 0x333e8:if(!ob1c_put(c,r.a[6],0x95,1,1))return false;r.pc=0x3395c;return true; // MOVE.B #1,95(A6); BRA.W 3395c.
    // ---- 333f2 (installed): BYTE 9b = 3; animation 34e56.
    case 0x333f2:if(!ob1c_put(c,r.a[6],0x9b,1,3))return false;return ob1c_animation(c,0x34e56,0x33408);
    case 0x33408:if(!ob1c_put(c,r.a[6],0x86,2,0))return false;return am_call(c,0x496c2,0x33414); // MOVE.W #0,86(A6); JSR 496c2.l.
    case 0x33414:if(!ob1c_install(c,0x3341a))return false;r.pc=0x3341a;return true; // MOVE.L #3341a,(A6) (falls into 3341a).
    case 0x3341a:return am_call(c,0x33c0e,0x3341e);                      // JSR 33c0e(PC).
    // MOVE.B D0,D1; ANDI.B #f,D1; BNE.W 33336.
    case 0x3341e:am_byte(r.d[1],r.d[0]&15U);r.pc=ob1c_b(r.d[1])!=0U?0x33336:0x33428;return true;
    case 0x33428:r.pc=((r.d[0]>>7)&1U)!=0U?0x3354a:0x33430;return true;   // BTST.B #7,D0; BNE.W 3354a.
    case 0x33430:return am_call(c,0x33c78,0x33434);                      // JSR 33c78(PC) (boundary).
    // D0.W = 86(A6); D1.W = table[2 * D0.W]; D0.B += 3; 86(A6) = D0.W; D2.W = table[2 * D0.W] - D1.W; 3a(A6) += (D2.W << 16) >> 8; JSR 33c48(PC).
    case 0x33434:
        if(!ob1c_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]+r.d[1]);
        r.a[0]=OB1C_TABLE;if(!am_read(c,am_index(r.a[0],r.d[1]),2,value))return false;am_word(r.d[1],value);
        am_byte(r.d[0],r.d[0]+3U);if(!ob1c_put(c,r.a[6],0x86,2,ob1c_w(r.d[0])))return false;
        am_word(r.d[2],r.d[0]);am_word(r.d[2],r.d[2]+r.d[2]);
        r.a[0]=OB1C_TABLE;if(!am_read(c,am_index(r.a[0],r.d[2]),2,value))return false;am_word(r.d[2],value);
        am_word(r.d[2],r.d[2]-r.d[1]);am_swap(r.d[2]);am_word(r.d[2],0);r.d[2]=ob1c_asr_l(r.d[2],8);
        if(!ob1c_add_l(c,0x3a,r.d[2]))return false;return am_call(c,0x33c48,0x3346a);
    case 0x3346a:return am_call(c,0x33d2c,0x3346e);                      // JSR 33d2c(PC) (boundary).
    case 0x3346e:return am_call(c,0x33dce,0x33472);                      // JSR 33dce(PC) (boundary).
    case 0x33472:return am_call(c,0x49fc6,0x33478);                      // JSR 49fc6.l.
    case 0x33478:if(!ob1c_put(c,r.a[6],0x95,1,1))return false;r.pc=0x3395c;return true; // MOVE.B #1,95(A6); BRA.W 3395c.
    // ---- 33482 (BNE.W from 33370 / 33512): BYTE 9b = 4; animation 34c80.
    case 0x33482:if(!ob1c_put(c,r.a[6],0x9b,1,4))return false;return ob1c_animation(c,0x34c80,0x33498);
    case 0x33498:if(!ob1c_install(c,0x3349e))return false;r.pc=0x3349e;return true; // MOVE.L #3349e,(A6) (falls into 3349e).
    case 0x3349e:if(!ob1c_bit(c,0x15,7,bit))return false;r.pc=bit?0x334a8:0x334dc;return true; // BTST.B #7,15(A6); BEQ.W 334dc.
    case 0x334a8:return am_call(c,0x33c0e,0x334ac);                      // JSR 33c0e(PC).
    case 0x334ac:r.pc=((r.d[0]>>5)&1U)!=0U?0x33546:0x334b4;return true;   // BTST.B #5,D0; BNE.W 33546.
    case 0x334b4:r.pc=((r.d[0]>>1)&1U)==0U?0x334dc:0x334bc;return true;   // BTST.B #1,D0; BEQ.W 334dc.
    case 0x334bc:return am_call(c,0x33c78,0x334c0);                      // JSR 33c78(PC) (boundary).
    case 0x334c0:return am_call(c,0x33c48,0x334c4);                      // JSR 33c48(PC).
    case 0x334c4:return am_call(c,0x33d2c,0x334c8);                      // JSR 33d2c(PC) (boundary).
    case 0x334c8:return am_call(c,0x33dce,0x334cc);                      // JSR 33dce(PC) (boundary).
    case 0x334cc:return am_call(c,0x49fc6,0x334d2);                      // JSR 49fc6.l.
    case 0x334d2:if(!ob1c_put(c,r.a[6],0x95,1,0))return false;r.pc=0x3395c;return true; // MOVE.B #0,95(A6); BRA.W 3395c.
    // BYTE 9b = 4; TST.B 8e(A6); BEQ.W 33336.
    case 0x334dc:if(!ob1c_put(c,r.a[6],0x9b,1,4))return false;return ob1c_timer(c,0x8e,0x334ea,0x33336);
    case 0x334ea:return ob1c_animation(c,0x34bec,0x334fa);               // animation 34bec.
    case 0x334fa:if(!ob1c_install(c,0x33500))return false;r.pc=0x33500;return true; // MOVE.L #33500,(A6) (falls into 33500).
    case 0x33500:return am_call(c,0x33c0e,0x33504);                      // JSR 33c0e(PC).
    case 0x33504:r.pc=((r.d[0]>>1)&1U)==0U?0x33516:0x3350c;return true;   // BTST.B #1,D0; BEQ.W 33516.
    case 0x3350c:if(!ob1c_bit(c,0x15,7,bit))return false;r.pc=bit?0x33482:0x33516;return true; // BTST.B #7,15(A6); BNE.W 33482.
    case 0x33516:return am_call(c,0x33c78,0x3351a);                      // JSR 33c78(PC) (boundary).
    case 0x3351a:return am_call(c,0x33c48,0x3351e);                      // JSR 33c48(PC).
    case 0x3351e:return am_call(c,0x33d2c,0x33522);                      // JSR 33d2c(PC) (boundary).
    case 0x33522:return am_call(c,0x33dce,0x33526);                      // JSR 33dce(PC) (boundary).
    case 0x33526:return am_call(c,0x49fc6,0x3352c);                      // JSR 49fc6.l.
    case 0x3352c:return ob1c_carry(c,0x33536,0x33530);                   // BCC.W 33536 (C returned by 49fc6).
    case 0x33530:if(!ob1c_install(c,0x3353a))return false;r.pc=0x33536;return true; // MOVE.L #3353a,(A6).
    case 0x33536:r.pc=0x3395c;return true;                                // BRA.W 3395c.
    case 0x3353a:if(!ob1c_put(c,r.a[6],0x3a,4,0x40000))return false;r.pc=0x33336;return true; // MOVE.L #40000,3a(A6); BRA.W 33336.
    case 0x33546:r.pc=0x33132;return true;                                // BRA.W 33132 (N30a).
    // ---- 3354a (BNE.W from 333ac / 33428): JSR 496c2.l; MOVE.W #1ac8,D0; JSR 3af8.l.
    case 0x3354a:return am_call(c,0x496c2,0x33550);
    case 0x33550:am_word(r.d[0],0x1ac8);return am_call(c,0x3af8,0x3355a);
    case 0x3355a:am_byte(r.d[1],4);return am_call(c,0x33940,0x33562);     // MOVE.B #4,D1; JSR 33940(PC) (boundary).
    // BYTE 9b = 0; LONG 76 = 34966; animation 34cf6 with D0.W = 300.
    case 0x33562:
        if(!ob1c_put(c,r.a[6],0x9b,1,0) || !ob1c_put(c,r.a[6],0x76,4,0x34966))return false;
        r.a[1]=0x34cf6;am_word(r.d[0],0x300);return am_call(c,0x49f8c,0x33580);
    case 0x33580:return am_call(c,0x34490,0x33584);                      // JSR 34490(PC) (boundary).
    case 0x33584:return am_call(c,0x3453a,0x33588);                      // JSR 3453a(PC) (boundary).
    case 0x33588:return am_call(c,0x46ef4,0x3358e);                      // JSR 46ef4.l.
    case 0x3358e:if(!ob1c_put(c,r.a[6],0x56,4,0) || !ob1c_install(c,0x3359c))return false;r.pc=0x3359c;return true; // LONG 56 = 0; install (falls into 3359c).
    // MOVE.L #100000,D0; SUB.L 36(A6),D0; ASR.L #3,D0; ADD.L D0,36(A6); MOVEQ #f0,D0; JSR 4c2c4.l (boundary).
    case 0x3359c:if(!ob1c_ease(c,0x100000,0x36,3))return false;r.d[0]=0xfffffff0U;return am_call(c,0x4c2c4,0x335b4);
    case 0x335b4:return ob1c_carry(c,0x335b8,0x335c4);                   // BCS.W 335c4 (C returned by 4c2c4).
    case 0x335b8:if(!ob1c_add_l(c,0x3a,0xfffff800U))return false;r.pc=0x335cc;return true; // ADDI.L #fffff800,3a(A6); BRA.W 335cc.
    case 0x335c4:if(!ob1c_add_l(c,0x3a,0x800))return false;r.pc=0x335cc;return true;       // SUBI.L #fffff800,3a(A6) (+ 800).
    case 0x335cc:return am_call(c,0x33c6c,0x335d0);                      // JSR 33c6c(PC).
    case 0x335d0:return am_call(c,0x33d2c,0x335d4);                      // JSR 33d2c(PC) (boundary).
    case 0x335d4:return am_call(c,0x33dce,0x335d8);                      // JSR 33dce(PC) (boundary).
    case 0x335d8:return am_call(c,0x49fc6,0x335de);                      // JSR 49fc6.l.
    // MOVE.W #8000,8a(A6); LEA 34a2a(PC),A0; JSR 4ae4a.l.
    case 0x335de:if(!ob1c_put(c,r.a[6],0x8a,2,0x8000))return false;r.a[0]=0x34a2a;return am_call(c,0x4ae4a,0x335ee);
    case 0x335ee:r.pc=ob1c_w(r.d[0])>=9U?0x33622:0x335f6;return true;     // CMPI.W #9,D0; BCC.W 33622.
    // ADD.W D0,D0; ADD.W D0,D0; JMP 335fe(PC,D0.W) (F1 decision 3: no bound check here; 335ee bounds the natural index to 0..8).
    case 0x335f6:am_word(r.d[0],(r.d[0]*4U)&65535U);r.pc=am_index(0x335fe,r.d[0]);return true;
    // The 9 BRA.W slots of 335fe: k = 1 2 -> 3363a, every other k -> 33622.
    case 0x33602:case 0x33606:r.pc=0x3363a;return true;
    case 0x335fe:case 0x3360a:case 0x3360e:case 0x33612:case 0x33616:case 0x3361a:case 0x3361e:r.pc=0x33622;return true;
    // CMPI.W #110,42(A6); BGT.W 3363a (signed).
    case 0x33622:if(!ob1c_get(c,r.a[6],0x42,2,value))return false;r.pc=ob1c_signed_w(value)>0x110?0x3363a:0x3362c;return true;
    case 0x3362c:if(!ob1c_bit(c,0x61,0,bit))return false;r.pc=bit?0x3363a:0x33636;return true; // BTST.B #0,61(A6); BNE.W 3363a.
    case 0x33636:r.pc=0x33aa4;return true;                                // BRA.W 33aa4 (N30a).
    // ---- 3363a (break-up): LEA 34a48(PC),A0; JSR 4ae4a.l.
    case 0x3363a:r.a[0]=0x34a48;return am_call(c,0x4ae4a,0x33644);
    case 0x33644:r.d[0]=1;r.d[1]=0;return am_call(c,0x4ff96,0x3364e);    // MOVEQ #1,D0; MOVEQ #0,D1; JSR 4ff96.l (boundary).
    case 0x3364e:return am_call(c,0xd3d7c,0x33654);                      // JSR d3d7c.l (boundary).
    case 0x33654:if(!ob1c_spark(c,0xfff30000U,0x180000,0xa))return false;return am_call(c,0xd3d7c,0x33670);
    case 0x33670:if(!ob1c_spark(c,0xb0000,0x150000,7))return false;return am_call(c,0xd3d7c,0x3368c);
    // ... MOVEA.L #338f8,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0x3368c:
        if(!ob1c_spark(c,0x80000,0xfffc0000U,5))return false;r.a[0]=0x338f8;am_word(r.d[0],0x1e);r.a[1]=0x100bf4;return am_call(c,0x2986,0x336b8);
    case 0x336b8:r.d[0]=0;r.d[1]=0x10;return am_call(c,0x49214,0x336c2); // MOVEQ #0,D0; MOVEQ #10,D1; JSR 49214.l.
    case 0x336c2:am_word(r.d[0],0x18de);return am_call(c,0x3af8,0x336cc); // MOVE.W #18de,D0; JSR 3af8.l.
    case 0x336cc:r.pc=0x2a00;return true;                                 // JMP 2a00.l.
    // ---- shared tail 3395c: BYTE timers 90 / 91 (SUBQ.B #1 while non-zero).
    case 0x3395c:return ob1c_timer(c,0x90,0x33964,0x33968);              // TST.B 90(A6); BEQ.W 33968.
    case 0x33964:return ob1c_count(c,0x90,0x33968);                      // SUBQ.B #1,90(A6).
    case 0x33968:return ob1c_timer(c,0x91,0x33970,0x33974);              // TST.B 91(A6); BEQ.W 33974.
    case 0x33970:return ob1c_count(c,0x91,0x33974);                      // SUBQ.B #1,91(A6).
    // MOVE.B 95(A6),D7; CMP.B 96(A6),D7; BEQ.W 33990.
    case 0x33974:
        if(!ob1c_get(c,r.a[6],0x95,1,value) || !ob1c_get(c,r.a[6],0x96,1,other))return false;am_byte(r.d[7],value);
        r.pc=ob1c_b(value)==ob1c_b(other)?0x33990:0x33980;return true;
    // MOVE.B D7,96(A6); MOVE.B #0,90(A6); MOVE.B #0,91(A6).
    case 0x33980:
        if(!ob1c_put(c,r.a[6],0x96,1,ob1c_b(r.d[7])) || !ob1c_put(c,r.a[6],0x90,1,0) || !ob1c_put(c,r.a[6],0x91,1,0))return false;
        r.pc=0x33990;return true;
    case 0x33990:return am_call(c,0x33e48,0x33994);                      // JSR 33e48(PC) (boundary).
    // MOVE.W 7a(A6),D0; MOVE.B 95(A6),D7; CMPI.B #2,D7; BNE.W 339aa.
    case 0x33994:
        if(!ob1c_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);
        if(!ob1c_get(c,r.a[6],0x95,1,value))return false;am_byte(r.d[7],value);
        r.pc=ob1c_b(value)!=2U?0x339aa:0x339a4;return true;
    case 0x339a4:if(!ob1c_put(c,r.a[6],0x95,1,1))return false;r.pc=0x339aa;return true; // MOVE.B #1,95(A6).
    case 0x339aa:return am_call(c,0x4d98a,0x339b0);                      // JSR 4d98a.l (boundary).
    // CMPI.L #fffe0000,3a(A6); BGT.W 339c6 (signed).
    case 0x339b0:if(!ob1c_get(c,r.a[6],0x3a,4,value))return false;r.pc=ob1c_signed_l(value)>-131072LL?0x339c6:0x339bc;return true;
    case 0x339bc:r.a[0]=0x34b0c;return am_call(c,0x4ae4a,0x339c6);       // LEA 34b0c(PC),A0; JSR 4ae4a.l.
    // CMPI.L #20000,36(A6); BLT.W 339e0 (signed).
    case 0x339c6:if(!ob1c_get(c,r.a[6],0x36,4,value))return false;r.pc=ob1c_signed_l(value)<131072LL?0x339e0:0x339d2;return true;
    case 0x339d2:r.a[0]=0x34b48;return am_call(c,0x4ae4a,0x339dc);       // LEA 34b48(PC),A0; JSR 4ae4a.l.
    case 0x339dc:r.pc=0x339f6;return true;                                // BRA.W 339f6.
    // CMPI.L #fffe0000,36(A6); BGT.W 339f6 (signed).
    case 0x339e0:if(!ob1c_get(c,r.a[6],0x36,4,value))return false;r.pc=ob1c_signed_l(value)>-131072LL?0x339f6:0x339ec;return true;
    case 0x339ec:r.a[0]=0x34b2a;return am_call(c,0x4ae4a,0x339f6);       // LEA 34b2a(PC),A0; JSR 4ae4a.l.
    case 0x339f6:return am_call(c,0x343e0,0x339fa);                      // JSR 343e0(PC) (boundary).
    // MOVE.W 7a(A6),D0; MOVEQ #c,D2; MOVEQ #18,D3; JSR 4d418.l (boundary).
    case 0x339fa:
        if(!ob1c_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);r.d[2]=0xc;r.d[3]=0x18;return am_call(c,0x4d418,0x33a08);
    case 0x33a08:return ob1c_carry(c,0x33a0c,0x33a16);                   // BCS.W 33a16 (C returned by 4d418).
    case 0x33a0c:if(!ob1c_install(c,0x33132))return false;r.pc=0x33a88;return true; // MOVE.L #33132,(A6); BRA.W 33a88 (N30a).
    // MOVE.W 7a(A6),D0; JSR 4d7a6.l.
    case 0x33a16:if(!ob1c_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4d7a6,0x33a20);
    case 0x33a20:r.pc=ob1c_b(r.d[0])!=4U?0x33a30:0x33a28;return true;     // CMPI.B #4,D0; BNE.W 33a30.
    case 0x33a28:if(!ob1c_put(c,r.a[6],0x93,1,ob1c_b(r.d[1])) || !ob1c_put(c,r.a[6],0x94,1,ob1c_b(r.d[2])))return false;r.pc=0x33a30;return true; // MOVE.B D1,93(A6); MOVE.B D2,94(A6).
    case 0x33a30:if(!ob1c_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4d734,0x33a3a); // JSR 4d734.l (boundary).
    // MOVE.W 7a(A6),D0; MOVEA.L 56(A6),A1; JSR 4d9ba.l (boundary).
    case 0x33a3a:
        if(!ob1c_get(c,r.a[6],0x7a,2,value) || !ob1c_get(c,r.a[6],0x56,4,other))return false;am_word(r.d[0],value);r.a[1]=other;
        return am_call(c,0x4d9ba,0x33a48);
    case 0x33a48:if(!ob1c_get(c,r.a[6],0x5e,1,value))return false;r.pc=ob1c_b(value)==0U?0x33a88:0x33a50;return true; // TST.B 5e(A6); BEQ.W 33a88.
    case 0x33a50:if(!ob1c_bit(c,0x61,6,bit))return false;r.pc=bit?0x33a88:0x33a5a;return true; // BTST.B #6,61(A6); BNE.W 33a88.
    // MOVE.W #1e,7e(A6); D1.B = (5f(A6) & f) << 4; MOVE.L #80000,D0; JSR 443d2.l.
    case 0x33a5a:
        if(!ob1c_put(c,r.a[6],0x7e,2,0x1e) || !ob1c_get(c,r.a[6],0x5f,1,value))return false;
        am_byte(r.d[1],((value&15U)<<4)&255U);r.d[0]=0x80000;return am_call(c,0x443d2,0x33a76);
    // ADD.L D0,36(A6); ADD.L D1,3a(A6); MOVE.W #1a59,D0; JSR 3af8.l.
    case 0x33a76:if(!ob1c_add_l(c,0x36,r.d[0]) || !ob1c_add_l(c,0x3a,r.d[1]))return false;am_word(r.d[0],0x1a59);return am_call(c,0x3af8,0x33a88);
    default:return am_error(c,"unsupported animation objects b1c PC");
    }
}
}
