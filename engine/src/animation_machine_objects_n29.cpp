#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONGs (live bus, current PVC bank): animation records of 30e14 / 30e8a (id e2) and 31008 / 318d8 (id 112).
const std::uint32_t ON29_BANK_E2=0x200094;
const std::uint32_t ON29_BANK_112=0x2000ac;
// Fixed ROM tables: 8ebe sound id WORDs by 86.W (31078) and the animation LONGs by (4 * 94.B + 86.W) (310a2).
const std::uint32_t ON29_SOUND_IDS=0x31c84;
const std::uint32_t ON29_ANIMATIONS=0x31d3e;
std::uint32_t on29_b(std::uint32_t value) {return value&255U;}
std::uint32_t on29_w(std::uint32_t value) {return value&65535U;}
// A LONG as a signed value (BLE after CMPI.L), converted explicitly.
std::int64_t on29_signed_l(std::uint32_t value) {
    return (value&0x80000000U)?static_cast<std::int64_t>(value)-4294967296LL:static_cast<std::int64_t>(value);
}
// A WORD as a signed value (BGT after CMPI.W), converted explicitly.
std::int32_t on29_signed_w(std::uint32_t value) {
    const std::uint32_t u=value&65535U;return (u&0x8000U)?static_cast<std::int32_t>(u)-65536:static_cast<std::int32_t>(u);
}
// Arithmetic shift right of a LONG (sign bit refilled explicitly).
std::uint32_t on29_asr_l(std::uint32_t value,unsigned int count) {
    std::uint32_t u=value;for(unsigned int i=0;i<count;++i)u=(u>>1)|(u&0x80000000U);return u;
}
bool on29_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on29_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BYTE bit of the memory operand d16(A6) (BTST.B #bit,<ea>): true when the bit is 1.
bool on29_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on29_get(c,c.s.a[6],displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// MOVE.B / MOVE.W <src d16(from)>,<dst d16(A6)>.
bool on29_copy(AnimationMachineContext& c,std::uint32_t from_base,std::uint32_t from,std::uint32_t to,unsigned int size) {
    std::uint32_t value=0;return on29_get(c,from_base,from,size,value) && on29_put(c,c.s.a[6],to,size,value);
}
// MOVE.L #value,(A6) (installed callback LONG).
bool on29_install(AnimationMachineContext& c,std::uint32_t value) {return on29_put(c,c.s.a[6],0,4,value);}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on29_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n29 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.l.
bool on29_animation(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #id,20(A6); MOVE.L <banked LONG>,22(A6).
bool on29_record(AnimationMachineContext& c,std::uint32_t id,std::uint32_t banked) {
    std::uint32_t value=0;
    return on29_put(c,c.s.a[6],0x20,2,id) && am_read(c,banked,4,value) && on29_put(c,c.s.a[6],0x22,4,value);
}
// MOVE.L #l36,36(A0); MOVE.L #l3a,3a(A0); MOVE.W #w54,54(A0) (the d3d7c node).
bool on29_spark(AnimationMachineContext& c,std::uint32_t l36,std::uint32_t l3a,std::uint32_t w54) {
    AnimationMachineState& r=c.s;return on29_put(c,r.a[0],0x36,4,l36) && on29_put(c,r.a[0],0x3a,4,l3a) && on29_put(c,r.a[0],0x54,2,w54);
}
// MOVE.L D1,D3; ADD.L 18(A0),D3; SUB.L 46(A6),D3; CMPI.L #300000,D3; BLE.W near_pc (else far_pc).
bool on29_distance(AnimationMachineContext& c,std::uint32_t near_pc,std::uint32_t far_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[3]=r.d[1];
    if(!on29_get(c,r.a[0],0x18,4,value))return false;r.d[3]=(r.d[3]+value)&0xffffffffU;
    if(!on29_get(c,r.a[6],0x46,4,value))return false;r.d[3]=(r.d[3]-value)&0xffffffffU;
    r.pc=on29_signed_l(r.d[3])<=0x300000LL?near_pc:far_pc;return true;
}
// MOVE.B d(A6),D0; BEQ.W skip_pc (else dec_pc).
bool on29_timer(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t dec_pc,std::uint32_t skip_pc) {
    std::uint32_t value=0;if(!on29_get(c,c.s.a[6],displacement,1,value))return false;am_byte(c.s.d[0],value);
    c.s.pc=on29_b(value)==0U?skip_pc:dec_pc;return true;
}
// SUBQ.B #1,D0; MOVE.B D0,d(A6).
bool on29_count(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    am_byte(c.s.d[0],c.s.d[0]+255U);if(!on29_put(c,c.s.a[6],displacement,1,on29_b(c.s.d[0])))return false;c.s.pc=next_pc;return true;
}
}
// Objects F4 N29a (192 block starts): the 28ae child callbacks 30dbe (installs 30de4 30e38 30e8a 30eae 30dd4) and 31008 (installs
// 31032), the stage event setup 318d8 (spawns 41fe6 / 31008 / 30dbe), the installed chain 306b4 / 308e2 / 309b4 / 309f2 with the 9-slot
// BRA.W table 30a76 and the 30ac0 break-up, the shared tail 30ed6 (handed over by N28; ends in N28 30f84), the helpers 3164a (C), 3165e,
// 3166c, 31696 / 316ac / 316b2 (JMP 4be82 / 4be6c), 319f6 (C), 31a12, the interpreter table entries 31a2a / 31a44 and the stage event
// callback 3310c. Boundaries without an executor: 316c2 316f0 31768 317b8 31832 3185a 33b12 49c38 4be6c 4c0ea 4d418 4d4b4 4d734 4d8d8
// 4d9ba 4ff96 d3d7c ea680. 30abc BRA.W 30fa0 enters the N28 block 30f9c at its second instruction (contract decision 3). The 15
// consumers read a known C returned by 1aa7e / 3165e / 3164a / 288c / ea680 / 49fc6 / 319f6 / 28ae / 4d418 / 49c38; ANDI.W #8 (31650)
// clears and ORI CCR (31658 31960 31a08) sets it. Every other flag test stays inside its block. No port, no bank change, no X / DIV.
bool animation_objects_n29_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool bit=false;
    switch(r.pc) {
    // ---- 306b4 (BNE.W from 30918 / 30978): animation 31e3a.
    case 0x306b4:return on29_animation(c,0x31e3a,0x306c4);
    // MOVE.B 1b(A6),14(A6); MOVE.L #0,76(A6); MOVE.L #0,56(A6); JSR 496c2.l.
    case 0x306c4:
        if(!on29_copy(c,r.a[6],0x1b,0x14,1) || !on29_put(c,r.a[6],0x76,4,0) || !on29_put(c,r.a[6],0x56,4,0))return false;
        return am_call(c,0x496c2,0x306e0);
    // MOVE.B #ff,94(A6); MOVE.L #306ec,(A6) (falls through into the installed 306ec).
    case 0x306e0:if(!on29_put(c,r.a[6],0x94,1,0xff) || !on29_install(c,0x306ec))return false;r.pc=0x306ec;return true;
    case 0x306ec:return am_call(c,0x316b2,0x306f0);                     // JSR 316b2(PC).
    case 0x306f0:r.a[0]=0x31ad4;return am_call(c,0x1aa7e,0x306fc);      // LEA 31ad4.l,A0; JSR 1aa7e.l.
    case 0x306fc:return on29_carry(c,0x30706,0x30700);                  // BCC.W 30706 (C returned by 1aa7e).
    case 0x30700:if(!on29_install(c,0x31002))return false;r.pc=0x30706;return true; // MOVE.L #31002,(A6).
    case 0x30706:return am_call(c,0x3165e,0x3070a);                     // JSR 3165e(PC).
    case 0x3070a:return on29_carry(c,0x30714,0x3070e);                  // BCC.W 30714 (C returned by 3165e = 49fc6).
    case 0x3070e:if(!on29_install(c,0x30718))return false;r.pc=0x30714;return true; // MOVE.L #30718,(A6).
    case 0x30714:r.pc=0x30ed2;return true;                               // BRA.W 30ed2 (N28).
    // ---- 308e2 (outside BMI.W 3086e / install 306a0, 30982 BNE.W, install 309e8): animation 31f0c.
    case 0x308e2:return on29_animation(c,0x31f0c,0x308f2);
    case 0x308f2:if(!on29_put(c,r.a[6],0x94,1,1) || !on29_install(c,0x308fe))return false;r.pc=0x308fe;return true; // MOVE.B #1,94(A6); install.
    case 0x308fe:return am_call(c,0x3166c,0x30902);                     // JSR 3166c(PC).
    case 0x30902:r.pc=((r.d[0]>>7)&1U)!=0U?0x309f2:0x3090a;return true;  // BTST.B #7,D0; BNE.W 309f2.
    case 0x3090a:if(!on29_bit(c,0x15,7,bit))return false;r.pc=bit?0x30914:0x3091c;return true; // BTST.B #7,15(A6); BEQ.W 3091c.
    case 0x30914:r.pc=((r.d[0]>>5)&1U)!=0U?0x306b4:0x3091c;return true;  // BTST.B #5,D0; BNE.W 306b4.
    // MOVE.W D0,D1; ANDI.W #f,D1; BEQ.W 30942.
    case 0x3091c:am_word(r.d[1],r.d[0]&15U);r.pc=on29_w(r.d[1])==0U?0x30942:0x30926;return true;
    case 0x30926:return am_call(c,0x316f0,0x3092a);                     // JSR 316f0(PC) (boundary).
    case 0x3092a:return am_call(c,0x317b8,0x3092e);                     // JSR 317b8(PC) (boundary).
    case 0x3092e:return am_call(c,0x31832,0x30932);                     // JSR 31832(PC) (boundary).
    case 0x30932:return am_call(c,0x31696,0x30936);                     // JSR 31696(PC).
    case 0x30936:return am_call(c,0x3165e,0x3093a);                     // JSR 3165e(PC).
    case 0x3093a:return am_call(c,0x3185a,0x3093e);                     // JSR 3185a(PC) (boundary).
    case 0x3093e:r.pc=0x30ed6;return true;                               // BRA.W 30ed6.
    // ---- 30942 (BEQ.W from 3091c): animation 31f0c, install 3095e.
    case 0x30942:return on29_animation(c,0x31f0c,0x30952);
    case 0x30952:if(!on29_put(c,r.a[6],0x94,1,1) || !on29_install(c,0x3095e))return false;r.pc=0x3095e;return true;
    case 0x3095e:return am_call(c,0x3166c,0x30962);                     // JSR 3166c(PC).
    case 0x30962:r.pc=((r.d[0]>>7)&1U)!=0U?0x309f2:0x3096a;return true;  // BTST.B #7,D0; BNE.W 309f2.
    case 0x3096a:if(!on29_bit(c,0x15,7,bit))return false;r.pc=bit?0x30974:0x3097c;return true; // BTST.B #7,15(A6); BEQ.W 3097c.
    case 0x30974:r.pc=((r.d[0]>>5)&1U)!=0U?0x306b4:0x3097c;return true;  // BTST.B #5,D0; BNE.W 306b4.
    // MOVE.W D0,D1; ANDI.W #f,D1; BNE.W 308e2.
    case 0x3097c:am_word(r.d[1],r.d[0]&15U);r.pc=on29_w(r.d[1])!=0U?0x308e2:0x30986;return true;
    case 0x30986:return am_call(c,0x317b8,0x3098a);                     // JSR 317b8(PC) (boundary).
    case 0x3098a:return am_call(c,0x31832,0x3098e);                     // JSR 31832(PC) (boundary).
    // MOVE.L 3a(A6),-(A7); JSR 316c2(PC) (boundary).
    case 0x3098e:if(!on29_get(c,r.a[6],0x3a,4,value) || !am_push(c,4,value))return false;return am_call(c,0x316c2,0x30996);
    // SWAP D0; CLR.W D0; ASR.L #6,D0; ADD.L D0,3a(A6); JSR 31696(PC).
    case 0x30996:
        am_swap(r.d[0]);am_word(r.d[0],0);r.d[0]=on29_asr_l(r.d[0],6);
        if(!on29_get(c,r.a[6],0x3a,4,value) || !on29_put(c,r.a[6],0x3a,4,(value+r.d[0])&0xffffffffU))return false;
        return am_call(c,0x31696,0x309a4);
    // MOVE.L (A7)+,3a(A6); JSR 3165e(PC).
    case 0x309a4:if(!am_pop(c,4,value) || !on29_put(c,r.a[6],0x3a,4,value))return false;return am_call(c,0x3165e,0x309ac);
    case 0x309ac:return am_call(c,0x3185a,0x309b0);                     // JSR 3185a(PC) (boundary).
    case 0x309b0:r.pc=0x30ed6;return true;                               // BRA.W 30ed6.
    // ---- installed callback 309b4 (30f66): animation 32084, install 309d0.
    case 0x309b4:return on29_animation(c,0x32084,0x309c4);
    case 0x309c4:if(!on29_put(c,r.a[6],0x94,1,2) || !on29_install(c,0x309d0))return false;r.pc=0x309d0;return true;
    case 0x309d0:return am_call(c,0x3166c,0x309d4);                     // JSR 3166c(PC).
    case 0x309d4:return am_call(c,0x317b8,0x309d8);                     // JSR 317b8(PC) (boundary).
    case 0x309d8:return am_call(c,0x31832,0x309dc);                     // JSR 31832(PC) (boundary).
    case 0x309dc:return am_call(c,0x31696,0x309e0);                     // JSR 31696(PC).
    case 0x309e0:return am_call(c,0x3165e,0x309e4);                     // JSR 3165e(PC).
    case 0x309e4:return on29_carry(c,0x309ee,0x309e8);                  // BCC.W 309ee (C returned by 3165e = 49fc6).
    case 0x309e8:if(!on29_install(c,0x308e2))return false;r.pc=0x309ee;return true; // MOVE.L #308e2,(A6).
    case 0x309ee:r.pc=0x30ed6;return true;                               // BRA.W 30ed6.
    // ---- 309f2 (BNE.W from 30902 / 30962): animation 31f0c.
    case 0x309f2:return on29_animation(c,0x31f0c,0x30a02);
    // MOVE.B #ff,94(A6); MOVE.B #1,D1; JSR 31a12(PC).
    case 0x30a02:if(!on29_put(c,r.a[6],0x94,1,0xff))return false;am_byte(r.d[1],1);return am_call(c,0x31a12,0x30a10);
    // MOVE.L #0,56(A6); MOVE.L #31c92,76(A6); MOVE.W #1ac8,D0; JSR 3af8.l.
    case 0x30a10:
        if(!on29_put(c,r.a[6],0x56,4,0) || !on29_put(c,r.a[6],0x76,4,0x31c92))return false;am_word(r.d[0],0x1ac8);return am_call(c,0x3af8,0x30a2a);
    case 0x30a2a:if(!on29_install(c,0x30a30))return false;r.pc=0x30a30;return true; // MOVE.L #30a30,(A6).
    // MOVE.L #100000,D0; SUB.L 36(A6),D0; ASR.L #3,D0; ADD.L D0,36(A6); MOVE.L 3a(A6),D0; ASR.L #4,D0; SUB.L D0,3a(A6); MOVEQ #0,D0;
    // JSR 31832(PC) (boundary).
    case 0x30a30:
        if(!on29_get(c,r.a[6],0x36,4,value))return false;r.d[0]=on29_asr_l((0x100000U-value)&0xffffffffU,3);
        if(!on29_get(c,r.a[6],0x36,4,value) || !on29_put(c,r.a[6],0x36,4,(value+r.d[0])&0xffffffffU))return false;
        if(!on29_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=on29_asr_l(value,4);
        if(!on29_get(c,r.a[6],0x3a,4,value) || !on29_put(c,r.a[6],0x3a,4,(value-r.d[0])&0xffffffffU))return false;
        r.d[0]=0;return am_call(c,0x31832,0x30a50);
    case 0x30a50:return am_call(c,0x316ac,0x30a54);                     // JSR 316ac(PC).
    case 0x30a54:return am_call(c,0x3165e,0x30a58);                     // JSR 3165e(PC).
    // MOVE.W #8000,8a(A6); LEA 31c2a.l,A0; JSR 4ae4a.l.
    case 0x30a58:if(!on29_put(c,r.a[6],0x8a,2,0x8000))return false;r.a[0]=0x31c2a;return am_call(c,0x4ae4a,0x30a6a);
    case 0x30a6a:r.pc=on29_w(r.d[0])>=9U?0x30a9e:0x30a72;return true;    // CMPI.W #9,D0; BCC.W 30a9e.
    // ADD.W D0,D0; ADD.W D0,D0; JMP 30a7a(PC,D0.W) (F1 decision 3: no bound check here; 30a6a bounds the natural index to 0..8).
    case 0x30a72:am_word(r.d[0],(r.d[0]*4U)&65535U);r.pc=am_index(0x30a7a,r.d[0]);return true;
    // The 9 BRA.W slots of 30a7a: k = 1 2 3 -> 30ac0, k = 0 4 5 6 7 8 -> 30a9e.
    case 0x30a7e:case 0x30a82:case 0x30a86:r.pc=0x30ac0;return true;
    case 0x30a7a:case 0x30a8a:case 0x30a8e:case 0x30a92:case 0x30a96:case 0x30a9a:r.pc=0x30a9e;return true;
    // CMPI.W #110,42(A6); BGT.W 30ac0 (signed).
    case 0x30a9e:if(!on29_get(c,r.a[6],0x42,2,value))return false;r.pc=on29_signed_w(value)>0x110?0x30ac0:0x30aa8;return true;
    case 0x30aa8:if(!on29_bit(c,0x15,5,bit))return false;r.pc=bit?0x30ac0:0x30ab2;return true; // BTST.B #5,15(A6); BNE.W 30ac0.
    case 0x30ab2:if(!on29_bit(c,0x61,0,bit))return false;r.pc=bit?0x30ac0:0x30abc;return true; // BTST.B #0,61(A6); BNE.W 30ac0.
    case 0x30abc:r.pc=0x30fa0;return true;                               // BRA.W 30fa0 (N28 block 30f9c, second instruction).
    // ---- 30ac0: LEA 31c48.l,A0; JSR 4ae4a.l.
    case 0x30ac0:r.a[0]=0x31c48;return am_call(c,0x4ae4a,0x30acc);
    case 0x30acc:r.d[0]=1;r.d[1]=0;return am_call(c,0x4ff96,0x30ad6);    // MOVEQ #1,D0; MOVEQ #0,D1; JSR 4ff96.l (boundary).
    case 0x30ad6:return am_call(c,0xd3d7c,0x30adc);                     // JSR d3d7c.l (boundary).
    case 0x30adc:if(!on29_spark(c,0xffee0000U,0x240000,0xa))return false;return am_call(c,0xd3d7c,0x30af8);
    case 0x30af8:if(!on29_spark(c,0xe0000,0x200000,7))return false;return am_call(c,0xd3d7c,0x30b14);
    case 0x30b14:if(!on29_spark(c,0xfff40000U,0x10000,7))return false;return am_call(c,0xd3d7c,0x30b30);
    // ... MOVEA.L #30d6c,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0x30b30:
        if(!on29_spark(c,0xa0000,0xfffc0000U,5))return false;r.a[0]=0x30d6c;am_word(r.d[0],0x1e);r.a[1]=0x100bf4;return am_call(c,0x2986,0x30b5c);
    case 0x30b5c:r.d[0]=0;r.d[1]=0x10;return am_call(c,0x49214,0x30b66); // MOVEQ #0,D0; MOVEQ #10,D1; JSR 49214.l.
    case 0x30b66:r.pc=0x2a00;return true;                                // JMP 2a00.l.
    // ---- 28ae child callback 30dbe (319a4): JSR 3164a(PC); BCS.W 30ecc.
    case 0x30dbe:return am_call(c,0x3164a,0x30dc2);
    case 0x30dc2:return on29_carry(c,0x30dc6,0x30ecc);                  // BCS.W 30ecc (C returned by 3164a).
    case 0x30dc6:return am_call(c,0x1abda,0x30dcc);                     // JSR 1abda.l.
    case 0x30dcc:r.d[1]=0;return am_call(c,0x8ebe,0x30dd4);             // MOVEQ #0,D1; JSR 8ebe.l.
    case 0x30dd4:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x30dde);    // (installed by 30ec4) MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0x30dde:if(!on29_install(c,0x30de4))return false;r.pc=0x30de4;return true; // MOVE.L #30de4,(A6).
    case 0x30de4:return am_call(c,0x288c,0x30dea);                      // JSR 288c.l.
    case 0x30dea:return on29_carry(c,0x30ecc,0x30dee);                  // BCC.W 30ecc (C returned by 288c).
    case 0x30dee:return am_call(c,0x43e34,0x30df4);                     // JSR 43e34.l.
    case 0x30df4:return am_call(c,0xea680,0x30dfa);                     // JSR ea680.l (boundary).
    case 0x30dfa:return on29_carry(c,0x30e12,0x30dfe);                  // BCC.W 30e12 (C returned by ea680).
    case 0x30dfe:return on29_distance(c,0x30e14,0x30e12);               // D3 = D1 + 18(A0) - 46(A6); BLE.W 30e14 (signed).
    case 0x30e12:case 0x30e88:case 0x30eca:case 0x3104a:case 0x310d6:case 0x3165c:case 0x3166a:case 0x31694:case 0x319b4:case 0x31a10:
    case 0x31a22:return am_return(c);                                      // RTS.
    // MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); animation 32f16.
    case 0x30e14:if(!on29_record(c,0xe2,ON29_BANK_E2))return false;return on29_animation(c,0x32f16,0x30e32);
    case 0x30e32:if(!on29_install(c,0x30e38))return false;r.pc=0x30e38;return true; // MOVE.L #30e38,(A6).
    case 0x30e38:return am_call(c,0x288c,0x30e3e);                      // JSR 288c.l.
    case 0x30e3e:return on29_carry(c,0x30ecc,0x30e42);                  // BCC.W 30ecc (C returned by 288c).
    case 0x30e42:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x30e4c);    // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0x30e4c:return am_call(c,0xea680,0x30e52);                     // JSR ea680.l (boundary).
    case 0x30e52:return on29_carry(c,0x30e8a,0x30e56);                  // BCC.W 30e8a (C returned by ea680).
    case 0x30e56:return on29_distance(c,0x30e70,0x30e6a);               // D3 = D1 + 18(A0) - 46(A6); BLE.W 30e70 (signed).
    case 0x30e6a:if(!on29_install(c,0x30e8a))return false;r.pc=0x30e70;return true; // MOVE.L #30e8a,(A6).
    case 0x30e70:r.a[1]=r.a[0];r.a[0]=am_index(r.a[6],0x2e);return am_call(c,0x43e22,0x30e7c); // MOVEA.L A0,A1; LEA 2e(A6),A0; JSR 43e22.l.
    case 0x30e7c:return am_call(c,0x16ed2,0x30e82);                     // JSR 16ed2.l.
    case 0x30e82:return am_call(c,0x49fc6,0x30e88);                     // JSR 49fc6.l.
    // MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); animation 32ec4.
    case 0x30e8a:if(!on29_record(c,0xe2,ON29_BANK_E2))return false;return on29_animation(c,0x32ec4,0x30ea8);
    case 0x30ea8:if(!on29_install(c,0x30eae))return false;r.pc=0x30eae;return true; // MOVE.L #30eae,(A6).
    case 0x30eae:return am_call(c,0x43e34,0x30eb4);                     // JSR 43e34.l.
    case 0x30eb4:return am_call(c,0x16ed2,0x30eba);                     // JSR 16ed2.l.
    case 0x30eba:return am_call(c,0x49fc6,0x30ec0);                     // JSR 49fc6.l.
    case 0x30ec0:return on29_carry(c,0x30eca,0x30ec4);                  // BCC.W 30eca (C returned by 49fc6).
    case 0x30ec4:if(!on29_install(c,0x30dd4))return false;r.pc=0x30eca;return true; // MOVE.L #30dd4,(A6).
    case 0x30ecc:case 0x310d8:r.pc=0x2a00;return true;                   // JMP 2a00.l.
    // ---- shared tail 30ed6 (N28 decision 1): JSR 31768(PC) (boundary); BYTE timers 97 / 98.
    case 0x30ed6:return am_call(c,0x31768,0x30eda);
    case 0x30eda:return on29_timer(c,0x97,0x30ee2,0x30ee8);             // MOVE.B 97(A6),D0; BEQ.W 30ee8.
    case 0x30ee2:return on29_count(c,0x97,0x30ee8);                     // SUBQ.B #1,D0; MOVE.B D0,97(A6).
    case 0x30ee8:return on29_timer(c,0x98,0x30ef0,0x30ef6);             // MOVE.B 98(A6),D0; BEQ.W 30ef6.
    case 0x30ef0:return on29_count(c,0x98,0x30ef6);                     // SUBQ.B #1,D0; MOVE.B D0,98(A6).
    case 0x30ef6:return am_call(c,0x319f6,0x30efa);                     // JSR 319f6(PC).
    case 0x30efa:return on29_carry(c,0x30efe,0x30f08);                  // BCS.W 30f08 (C returned by 319f6).
    case 0x30efe:if(!on29_install(c,0x30718))return false;r.pc=0x30f84;return true; // MOVE.L #30718,(A6); BRA.W 30f84 (N28).
    case 0x30f08:if(!on29_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4d7a6,0x30f12); // MOVE.W 84(A6),D0; JSR 4d7a6.l.
    case 0x30f12:r.pc=on29_b(r.d[0])!=9U?0x30f22:0x30f1a;return true;    // CMPI.B #9,D0; BNE.W 30f22.
    // MOVE.B D1,99(A6); MOVE.B D2,9a(A6).
    case 0x30f1a:if(!on29_put(c,r.a[6],0x99,1,on29_b(r.d[1])) || !on29_put(c,r.a[6],0x9a,1,on29_b(r.d[2])))return false;r.pc=0x30f22;return true;
    case 0x30f22:if(!on29_get(c,r.a[6],0x5e,1,value))return false;r.pc=on29_b(value)==0U?0x30f6c:0x30f2a;return true; // TST.B 5e(A6); BEQ.W 30f6c.
    case 0x30f2a:if(!on29_bit(c,0x61,6,bit))return false;r.pc=bit?0x30f6c:0x30f34;return true; // BTST.B #6,61(A6); BNE.W 30f6c.
    // MOVE.W #2d,88(A6); ST.B 8c(A6); MOVE.B 5f(A6),D1; ANDI.B #f,D1; LSL.B #4,D1; MOVE.L #60000,D0; JSR 443d2.l.
    case 0x30f34:
        if(!on29_put(c,r.a[6],0x88,2,0x2d) || !on29_put(c,r.a[6],0x8c,1,0xff) || !on29_get(c,r.a[6],0x5f,1,value))return false;
        am_byte(r.d[1],((value&15U)<<4)&255U);r.d[0]=0x60000;return am_call(c,0x443d2,0x30f54);
    // ADD.L D0,36(A6); ADD.L D1,3a(A6); MOVE.W #1a59,D0; JSR 3af8.l.
    case 0x30f54:
        if(!on29_get(c,r.a[6],0x36,4,value) || !on29_put(c,r.a[6],0x36,4,(value+r.d[0])&0xffffffffU) ||
           !on29_get(c,r.a[6],0x3a,4,value) || !on29_put(c,r.a[6],0x3a,4,(value+r.d[1])&0xffffffffU))return false;
        am_word(r.d[0],0x1a59);return am_call(c,0x3af8,0x30f66);
    case 0x30f66:if(!on29_install(c,0x309b4))return false;r.pc=0x30f6c;return true; // MOVE.L #309b4,(A6).
    case 0x30f6c:if(!on29_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4d734,0x30f76); // JSR 4d734.l (boundary).
    // MOVE.W 84(A6),D0; MOVEA.L 56(A6),A1; JSR 4d9ba.l (boundary; returns into N28 30f84).
    case 0x30f76:
        if(!on29_get(c,r.a[6],0x84,2,value) || !on29_get(c,r.a[6],0x56,4,other))return false;am_word(r.d[0],value);r.a[1]=other;
        return am_call(c,0x4d9ba,0x30f84);
    // ---- 31002 (installed by 30700 / N28 3076e, 3199a BCC.W): JMP 2a24.l.
    case 0x31002:r.pc=0x2a24;return true;
    // ---- 28ae child callback 31008 (3198a): id 112, BYTE 94 = ff, WORD 86 = ffff, JSR 49290.l.
    case 0x31008:
        if(!on29_record(c,0x112,ON29_BANK_112) || !on29_put(c,r.a[6],0x94,1,0xff) || !on29_put(c,r.a[6],0x86,2,0xffff))return false;
        r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x3102c);
    case 0x3102c:if(!on29_install(c,0x31032))return false;r.pc=0x31032;return true; // MOVE.L #31032,(A6).
    case 0x31032:return am_call(c,0x288c,0x31038);                      // JSR 288c.l.
    case 0x31038:return on29_carry(c,0x310d8,0x3103c);                  // BCC.W 310d8 (C returned by 288c).
    case 0x3103c:return am_call(c,0x491c4,0x31042);                     // JSR 491c4.l.
    case 0x31042:if(!on29_get(c,r.a[0],0x94,1,value))return false;r.pc=(value&0x80U)==0U?0x3104c:0x3104a;return true; // TST.B 94(A0); BPL.W 3104c.
    // MOVE.W 1e(A0),1e(A6); MOVE.W 84(A0),84(A6); MOVE.B 90(A0),90(A6); MOVEA.L c(A6),A0; MOVE.W 86(A0),D0; CMP.W 86(A6),D0; BEQ.W 31092.
    case 0x3104c:
        if(!on29_copy(c,r.a[0],0x1e,0x1e,2) || !on29_copy(c,r.a[0],0x84,0x84,2) || !on29_copy(c,r.a[0],0x90,0x90,1) ||
           !on29_get(c,r.a[6],0xc,4,value))return false;
        r.a[0]=value;if(!on29_get(c,r.a[0],0x86,2,value))return false;am_word(r.d[0],value);
        if(!on29_get(c,r.a[6],0x86,2,value))return false;r.pc=on29_w(r.d[0])==on29_w(value)?0x31092:0x3106e;return true;
    case 0x3106e:if(!on29_put(c,r.a[6],0x86,2,on29_w(r.d[0])))return false;return am_call(c,0x8ff4,0x31078); // MOVE.W D0,86(A6); JSR 8ff4.l.
    // MOVE.W 86(A6),D0; LEA 31c84.l,A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #1,D1; JSR 8ebe.l.
    case 0x31078:
        if(!on29_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],value);r.a[0]=ON29_SOUND_IDS;am_word(r.d[0],(r.d[0]*2U)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x31092);
    // MOVEA.L c(A6),A0; MOVE.B 94(A0),D0; CMP.B 94(A6),D0; BEQ.W 310ca.
    case 0x31092:
        if(!on29_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!on29_get(c,r.a[0],0x94,1,value))return false;am_byte(r.d[0],value);
        if(!on29_get(c,r.a[6],0x94,1,value))return false;r.pc=on29_b(r.d[0])==on29_b(value)?0x310ca:0x310a2;return true;
    // MOVE.B D0,94(A6); ANDI.W #ff,D0; ADD.W D0,D0 (twice); ADD.W 86(A6),D0; ADD.W D0,D0 (twice); LEA 31d3e.l,A0;
    // MOVEA.L (A0,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x310a2:
        if(!on29_put(c,r.a[6],0x94,1,on29_b(r.d[0])))return false;am_word(r.d[0],(on29_b(r.d[0])*4U)&65535U);
        if(!on29_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],r.d[0]+value);am_word(r.d[0],(r.d[0]*4U)&65535U);
        r.a[0]=ON29_ANIMATIONS;if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;
        return on29_animation(c,value,0x310ca);
    case 0x310ca:return am_call(c,0x43e34,0x310d0);                     // JSR 43e34.l.
    case 0x310d0:return am_call(c,0x49fc6,0x310d6);                     // JSR 49fc6.l.
    // ---- helper 3164a (C: BYTE bit 3 of the 1aa3a result): JSR 1aa3a.l.
    case 0x3164a:return am_call(c,0x1aa3a,0x31650);
    // ANDI.W #8,D0 (C = 0); BEQ.W 3165c.
    case 0x31650:am_word(r.d[0],r.d[0]&8U);r.carry=AnimationCarryClear;r.pc=on29_w(r.d[0])==0U?0x3165c:0x31658;return true;
    case 0x31658:r.carry=AnimationCarrySet;r.pc=0x3165c;return true;     // ORI.B #1,CCR.
    // ---- helper 3165e: JSR 492c8.l; JSR 49fc6.l; RTS (C of 49fc6).
    case 0x3165e:return am_call(c,0x492c8,0x31664);
    case 0x31664:return am_call(c,0x49fc6,0x3166a);
    // ---- helper 3166c: MOVE.W 84(A6),D0; JSR 49c38.l (boundary).
    case 0x3166c:if(!on29_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49c38,0x31676);
    // SCS.B a0(A6) (C returned by 49c38); MOVE.W 84(A6),D0; JSR 49be0.l (the block ends with an Unknown C).
    case 0x31676:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n29 caller requires known carry");
        if(!on29_put(c,r.a[6],0xa0,1,r.carry==AnimationCarrySet?0xffU:0U) || !on29_get(c,r.a[6],0x84,2,value))return false;
        am_word(r.d[0],value);r.carry=AnimationCarryUnknown;return am_call(c,0x49be0,0x31684);
    // MOVE.W (A0),D0; BTST.B #6,D0; BEQ.W 31694.
    case 0x31684:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.pc=((r.d[0]>>6)&1U)==0U?0x31694:0x3168e;return true;
    case 0x3168e:if(!on29_put(c,r.a[6],0x97,1,0xf))return false;r.pc=0x31694;return true; // MOVE.B #f,97(A6).
    case 0x31696:r.pc=0x4be82;return true;                               // JMP 4be82.l.
    case 0x316ac:r.pc=0x4be6c;return true;                               // JMP 4be6c.l (boundary).
    // MOVEQ #0,D0; MOVE.L D0,36(A6); MOVE.L D0,3a(A6); JMP 4be6c.l (boundary).
    case 0x316b2:r.d[0]=0;if(!on29_put(c,r.a[6],0x36,4,0) || !on29_put(c,r.a[6],0x3a,4,0))return false;r.pc=0x4be6c;return true;
    // ---- 318d8 (N28 306a8 and outside JSR): id 112; JSR 8ebe.l (1f4, 1).
    case 0x318d8:if(!on29_record(c,0x112,ON29_BANK_112))return false;am_word(r.d[0],0x1f4);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x318f4);
    case 0x318f4:am_word(r.d[0],0x1f4);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x31902);  // MOVE.W #1f4,D0; MOVE.B #1,D1; JSR 8ebe.l.
    case 0x31902:am_word(r.d[0],0x1d9);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x31910);  // MOVE.W #1d9,D0; MOVE.B #1,D1; JSR 8ebe.l.
    // MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); MOVEQ #9,D1; JSR 4d81c.l.
    case 0x31910:if(!on29_put(c,r.a[6],0x68,2,0x8810) || !on29_put(c,r.a[6],0x1e,2,0x8810))return false;r.d[1]=9;return am_call(c,0x4d81c,0x31924);
    // MOVE.B D1,99(A6); MOVE.B D2,9a(A6); MOVE.W D3,54(A6); MOVE.W #ffff,92(A6); MOVE.W #e80,90(A6); MOVEQ #0,D0; MOVE.B D0,97(A6);
    // MOVE.B D0,98(A6); JSR 496c2.l.
    case 0x31924:
        if(!on29_put(c,r.a[6],0x99,1,on29_b(r.d[1])) || !on29_put(c,r.a[6],0x9a,1,on29_b(r.d[2])) || !on29_put(c,r.a[6],0x54,2,on29_w(r.d[3])) ||
           !on29_put(c,r.a[6],0x92,2,0xffff) || !on29_put(c,r.a[6],0x90,2,0xe80))return false;
        r.d[0]=0;if(!on29_put(c,r.a[6],0x97,1,0) || !on29_put(c,r.a[6],0x98,1,0))return false;return am_call(c,0x496c2,0x3194c);
    case 0x3194c:r.a[0]=0x41fe6;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x3195c); // MOVEA.L #41fe6,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x3195c:return on29_carry(c,0x3198a,0x31960);                  // BCC.W 3198a (C returned by 28ae).
    // LEA 8a(A6),A1; MOVE.L A1,76(A0); MOVE.B #9,7a(A0); MOVE.B #4,7b(A0); MOVE.B #0,7c(A0); MOVE.B #3,7d(A0); MOVE.B #0,7e(A0);
    // ORI.B #1,CCR.
    case 0x31960:
        r.a[1]=am_index(r.a[6],0x8a);
        if(!on29_put(c,r.a[0],0x76,4,r.a[1]) || !on29_put(c,r.a[0],0x7a,1,9) || !on29_put(c,r.a[0],0x7b,1,4) || !on29_put(c,r.a[0],0x7c,1,0) ||
           !on29_put(c,r.a[0],0x7d,1,3) || !on29_put(c,r.a[0],0x7e,1,0))return false;
        r.carry=AnimationCarrySet;r.pc=0x3198a;return true;
    case 0x3198a:r.a[0]=0x31008;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x3199a); // MOVEA.L #31008,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x3199a:return on29_carry(c,0x31002,0x3199e);                  // BCC.W 31002 (C returned by 28ae).
    // MOVE.B #ff,94(A6); MOVEA.L #30dbe,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x3199e:if(!on29_put(c,r.a[6],0x94,1,0xff))return false;r.a[0]=0x30dbe;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x319b4);
    // ---- helper 319f6 (C): MOVE.W 84(A6),D0; MOVEQ #0,D2; MOVEQ #18,D3; JSR 4d418.l (boundary).
    case 0x319f6:if(!on29_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[0],value);r.d[2]=0;r.d[3]=0x18;return am_call(c,0x4d418,0x31a04);
    case 0x31a04:return on29_carry(c,0x31a10,0x31a08);                  // BCC.W 31a10 (C returned by 4d418).
    case 0x31a08:if(!on29_put(c,r.a[6],0x86,2,on29_w(r.d[0])))return false;r.carry=AnimationCarrySet;r.pc=0x31a10;return true; // MOVE.W D0,86(A6); ORI.
    // ---- helper 31a12: MOVE.B D1,-(A7) (BYTE, A7 - 2); JSR 4d8d8.l (boundary).
    case 0x31a12:if(!am_push(c,1,on29_b(r.d[1])))return false;return am_call(c,0x4d8d8,0x31a1a);
    // MOVE.B (A7)+,D1; TST.B D0; BPL.W 31a24.
    case 0x31a1a:if(!am_pop(c,1,value))return false;am_byte(r.d[1],value);r.pc=(r.d[0]&0x80U)==0U?0x31a24:0x31a22;return true;
    case 0x31a24:r.pc=0x4d4b4;return true;                               // JMP 4d4b4.l (boundary).
    // ---- interpreter table entry 31a2a (LONG 4a5a4): MOVE.L (A0),D0; MOVE.B (A0),D1; ANDI.L #ffffff,D0; MOVEA.L D0,A0; ANDI.W #ff,D1;
    // MOVE.B (A6,D1.W),D1; ADD.W D1,D1 (twice); ADDA.W D1,A0 (falls through into 31a44).
    case 0x31a2a:
        if(!am_read(c,r.a[0],4,value) || !am_read(c,r.a[0],1,other))return false;
        r.d[0]=value&0xffffffU;am_byte(r.d[1],other);r.a[0]=r.d[0];am_word(r.d[1],r.d[1]&255U);
        if(!am_read(c,am_index(r.a[6],r.d[1]),1,value))return false;am_byte(r.d[1],value);am_word(r.d[1],(r.d[1]*4U)&65535U);
        r.a[0]=am_index(r.a[0],r.d[1]);r.pc=0x31a44;return true;
    // ---- interpreter table entry 31a44 (LONG 4a5a8): MOVEA.L (A0),A0; MOVE.W (A0)+,8a(A6); MOVE.W (A0)+,9c(A6); MOVE.W (A0)+,9e(A6); RTS.
    case 0x31a44:
        if(!am_read(c,r.a[0],4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0],2,value) || !on29_put(c,r.a[6],0x8a,2,value))return false;r.a[0]+=2U;
        if(!am_read(c,r.a[0],2,value) || !on29_put(c,r.a[6],0x9c,2,value))return false;r.a[0]+=2U;
        if(!am_read(c,r.a[0],2,value) || !on29_put(c,r.a[6],0x9e,2,value))return false;r.a[0]+=2U;
        return am_return(c);
    // ---- stage event callback 3310c (LONG e8cd0): CMPI.W #0,76(A6); BNE.W 3311c.
    case 0x3310c:if(!on29_get(c,r.a[6],0x76,2,value))return false;r.pc=on29_w(value)!=0U?0x3311c:0x33116;return true;
    case 0x33116:return am_call(c,0x4c0ea,0x3311c);                     // JSR 4c0ea.l (boundary).
    case 0x3311c:if(!on29_put(c,r.a[6],0x76,2,0))return false;return am_call(c,0x33b12,0x33124); // CLR.W 76(A6); JSR 33b12(PC) (boundary).
    case 0x33124:if(!on29_install(c,0x33132))return false;return am_return(c); // MOVE.L #33132,(A6); RTS.
    default:return am_error(c,"unsupported animation objects n29 PC");
    }
}
}
