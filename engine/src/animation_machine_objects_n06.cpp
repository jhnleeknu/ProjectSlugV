#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t ON06_BANK_1D0=0x2001d0;       // MOVE.L 2001d0.L,22(A6) (b9e88 b9eb4; banked window LONG, live bus).
std::uint32_t on06_w(std::uint32_t v) {return v&65535U;}
std::int32_t on06_s(std::uint32_t v) {return static_cast<std::int32_t>(am_extend_word(v&65535U));}
bool on06_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on06_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool on06_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n06 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #callback,(A6) then continue at next_pc.
bool on06_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// TST.W/TST.B d16(An) (and other zero tests): branch to zero_pc when the value is 0.
bool on06_test(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!on06_get(c,base,displacement,size,value))return false;
    c.s.pc=value==0U?zero_pc:next_pc;return true;
}
// CMPI.W #k,76(A6); BNE: equal_pc when WORD 76 = k.
bool on06_mode(AnimationMachineContext& c,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!on06_get(c,c.s.a[6],0x76,2,value))return false;
    c.s.pc=value==k?equal_pc:other_pc;return true;
}
// LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1;
// JSR 49f8c.L (the bank LONG and the LONG at its value + d16 through the live bus).
bool on06_animation(AnimationMachineContext& c,std::uint32_t k,std::uint32_t bank,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!on06_put(c,r.a[6],0x20,2,k) || !am_read(c,bank,4,value) || !on06_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!on06_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!on06_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #73,D0; MOVE.W #d1,D1; MOVE.B #0,D2; JSR c6a96.L.
bool on06_palette(AnimationMachineContext& c,std::uint32_t d1,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;am_word(r.d[0],0x73);am_word(r.d[1],d1);am_byte(r.d[2],0);return am_call(c,0xc6a96,return_pc);
}
// MOVEA.L 84(A6),A0; CMPA.W #0,A0; BEQ (CMPA.W sign-extends 0: full 32-bit test).
bool on06_table(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!on06_get(c,c.s.a[6],0x84,4,value))return false;c.s.a[0]=value;
    c.s.pc=value==0U?zero_pc:next_pc;return true;
}
// ST.B d16(A6) (BYTE ff; the CCR is kept).
bool on06_set(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    if(!on06_put(c,c.s.a[6],displacement,1,0xff))return false;c.s.pc=next_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #d0,D0; JSR 28ae.L.
bool on06_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t d0,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],d0);return am_call(c,0x28ae,return_pc);
}
// MOVE.x d16(A6),d16(A0) (same displacement).
bool on06_copy(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size) {
    std::uint32_t value=0;return on06_get(c,c.s.a[6],displacement,size,value) && on06_put(c,c.s.a[0],displacement,size,value);
}
}
// Objects F4 N06 (123 block starts): the object callback b9dc6 (installed b9df0 b9e0c b9e16 b9de6) with its 28ae child b9e64
// (ba310; bank 2001d0 + 70/58, installed b9f70) and the shared tail ba1b8, the installed callback ba196, the 28ae child ba1cc (ba386;
// installed ba1e6), the check ba234 (ST.B a1/a2 from eb774 and the boundary 497f0 / U11 497b6), the WORD table walk ba2d6, the BYTE 15
// copy 491b6, the work RAM BYTE lookup e90d8, the wait callback d9bcc (installed d9bea) and eb774 (returns C: ORI/ANDI CCR).
// Consumers b9e46 (1aa7e), ba1ec (288c), ba23a (eb774), ba282 (boundary 497f0), ba29c (497b6), ba334 ba396 (28ae), eb77a (49370),
// eb786 eb79c (49392) and eb790 eb7a6 (boundary 49416). Producers eb7aa (Set) and eb7b0 (Clear). Boundaries without an executor:
// 49416 497f0 and the TRAP #15 sites ba338 ba364 ba39a; orphan install values b9f96 b9f9a and the 28ae child value 4841a.
bool animation_objects_n06_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,value2=0;
    switch(r.pc) {
    // ---- 491b6: MOVE.B 15(A6),D0; ANDI.B #3,D0; MOVE.B D0,15(A0); RTS.
    case 0x491b6:
        if(!on06_get(c,r.a[6],0x15,1,value))return false;am_byte(r.d[0],value&3U);
        if(!on06_put(c,r.a[0],0x15,1,r.d[0]&255U))return false;return am_return(c);

    // ---- b9dc6: TST.W 7e(A6); BNE.W b9dd4.
    case 0xb9dc6:return on06_test(c,r.a[6],0x7e,2,0xb9dce,0xb9dd4);
    case 0xb9dce:if(!on06_put(c,r.a[6],0x7e,2,0x70))return false;r.pc=0xb9dd4;return true;   // MOVE.W #70,7e(A6).
    case 0xb9dd4:return am_call(c,0xba310,0xb9dd8);                                      // JSR ba310(PC).
    // MOVE.B 6b(A6),D0; JSR e90d8.L.
    case 0xb9dd8:if(!on06_get(c,r.a[6],0x6b,1,value))return false;am_byte(r.d[0],value);return am_call(c,0xe90d8,0xb9de2);
    case 0xb9de2:if(!on06_put(c,r.a[6],0x9f,1,r.d[0]&255U))return false;r.pc=0xb9de6;return true; // MOVE.B D0,9f(A6).
    // (installed callback) CLR.B a1(A6); MOVE.L #b9df0,(A6).
    case 0xb9de6:if(!on06_put(c,r.a[6],0xa1,1,0))return false;return on06_install(c,0xb9df0,0xb9df0);
    case 0xb9df0:return am_call(c,0x43e34,0xb9df6);                                      // (installed callback) JSR 43e34.L.
    case 0xb9df6:return am_call(c,0xba234,0xb9dfa);                                      // JSR ba234(PC).
    case 0xb9dfa:return on06_test(c,r.a[6],0xa1,1,0xb9e08,0xb9e02);                      // TST.B a1(A6); BEQ.W b9e08.
    case 0xb9e02:return on06_install(c,0xb9e0c,0xb9e08);                                 // MOVE.L #b9e0c,(A6).
    case 0xb9e08:case 0xb9e2e:r.pc=0xb9e32;return true;                                  // BRA.W b9e32.
    // (installed callback) CLR.B a2(A6); MOVE.L #b9e16,(A6).
    case 0xb9e0c:if(!on06_put(c,r.a[6],0xa2,1,0))return false;return on06_install(c,0xb9e16,0xb9e16);
    case 0xb9e16:return am_call(c,0x43e34,0xb9e1c);                                      // (installed callback) JSR 43e34.L.
    case 0xb9e1c:return am_call(c,0xba234,0xb9e20);                                      // JSR ba234(PC).
    case 0xb9e20:return on06_test(c,r.a[6],0xa2,1,0xb9e2e,0xb9e28);                      // TST.B a2(A6); BEQ.W b9e2e.
    case 0xb9e28:return on06_install(c,0xb9de6,0xb9e2e);                                 // MOVE.L #b9de6,(A6).
    // MOVE.W 80(A6),D0; BNE.W b9e54.
    case 0xb9e32:if(!on06_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[0],value);r.pc=value==0U?0xb9e3a:0xb9e54;return true;
    case 0xb9e3a:r.a[0]=0xba3de;return am_call(c,0x1aa7e,0xb9e46);                       // MOVEA.L #ba3de,A0; JSR 1aa7e.L.
    case 0xb9e46:return on06_consume(c,false,0xb9e50,0xb9e4a);                           // BCC.W b9e50 (C returned by 1aa7e).
    case 0xb9e4a:case 0xb9e5c:r.pc=0x2a24;return true;                                   // JMP 2a24.L.
    case 0xb9e50:r.pc=0xb9e62;return true;                                               // BRA.W b9e62.
    // CMP.W 5418(A5),D0; BHI.W b9e62 (unsigned D0.W > WORD).
    case 0xb9e54:if(!on06_get(c,r.a[5],0x5418,2,value))return false;r.pc=on06_w(r.d[0])>value?0xb9e62:0xb9e5c;return true;
    // RTS (keeps C).
    case 0xb9e62:case 0xba1ca:case 0xba212:case 0xba2b4:case 0xba384:case 0xd9bf2:return am_return(c);

    // ---- b9e64 (28ae child of ba324): MOVEQ #0,D0; MOVE.W 78(A6),D1; JSR 49290.L.
    case 0xb9e64:r.d[0]=0;if(!on06_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[1],value);return am_call(c,0x49290,0xb9e70);
    case 0xb9e70:return am_call(c,0xba386,0xb9e74);                                      // JSR ba386(PC).
    // LEA ba3f6.L,A0; MOVE.L A0,84(A6); CMPI.W #2,76(A6); BNE.W b9eb4.
    case 0xb9e74:r.a[0]=0xba3f6;if(!on06_put(c,r.a[6],0x84,4,r.a[0]))return false;return on06_mode(c,2,0xb9e88,0xb9eb4);
    case 0xb9e88:return on06_animation(c,0x203,ON06_BANK_1D0,0x70,0xb9eb0);
    case 0xb9eb0:r.pc=0xb9edc;return true;                                               // BRA.W b9edc.
    case 0xb9eb4:return on06_animation(c,0x203,ON06_BANK_1D0,0x58,0xb9edc);
    // MOVE.W #801,68(A6); MOVE.W #801,1e(A6); CMPI.W #2,76(A6); BNE.W b9f08.
    case 0xb9edc:
        if(!on06_put(c,r.a[6],0x68,2,0x801) || !on06_put(c,r.a[6],0x1e,2,0x801))return false;return on06_mode(c,2,0xb9ef2,0xb9f08);
    case 0xb9ef2:return on06_palette(c,0x1c,0xb9f04);
    case 0xb9f04:r.pc=0xb9f1a;return true;                                               // BRA.W b9f1a.
    case 0xb9f08:return on06_palette(c,0x16,0xb9f1a);
    // MOVE.L #18000,3a(A6); TST.B 7a(A6); BNE.W b9f2e.
    case 0xb9f1a:if(!on06_put(c,r.a[6],0x3a,4,0x18000))return false;return on06_test(c,r.a[6],0x7a,1,0xb9f2a,0xb9f2e);
    // NEG.L 3a(A6).
    case 0xb9f2a:
        if(!on06_get(c,r.a[6],0x3a,4,value) || !on06_put(c,r.a[6],0x3a,4,(0U-value)&0xffffffffU))return false;r.pc=0xb9f2e;return true;
    case 0xb9f2e:r.pc=0xb9f62;return true;                                               // BRA.W b9f62.
    // MOVE.L #ba30e,8c(A6); MOVE.L #b9f70,(A6).
    case 0xb9f62:if(!on06_put(c,r.a[6],0x8c,4,0xba30e))return false;return on06_install(c,0xb9f70,0xb9f70);
    case 0xb9f70:return am_call(c,0xba2d6,0xb9f74);                                      // (installed callback) JSR ba2d6(PC).
    case 0xb9f74:return am_call(c,0x43e34,0xb9f7a);                                      // JSR 43e34.L.
    case 0xb9f7a:return am_call(c,0x49fc6,0xb9f80);                                      // JSR 49fc6.L.
    // MOVEA.L c(A6),A0; TST.B a1(A0); BEQ.W b9f92.
    case 0xb9f80:if(!on06_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;return on06_test(c,r.a[0],0xa1,1,0xb9f92,0xb9f8c);
    case 0xb9f8c:return on06_install(c,0xb9f9a,0xb9f92);                                 // MOVE.L #b9f9a,(A6) (orphan install value).
    case 0xb9f92:case 0xba1b4:r.pc=0xba1b8;return true;                                  // BRA.W ba1b8.

    // ---- ba196 (installed callback): JSR ba2d6(PC); JSR 43e34.L; JSR 49fc6.L.
    case 0xba196:return am_call(c,0xba2d6,0xba19a);
    case 0xba19a:return am_call(c,0x43e34,0xba1a0);
    case 0xba1a0:return am_call(c,0x49fc6,0xba1a6);
    // SUBQ.W #1,9c(A6); BGT.W ba1b4 (Z clear and N = V of the WORD subtraction).
    case 0xba1a6:{
        if(!on06_get(c,r.a[6],0x9c,2,value))return false;value2=(value-1U)&65535U;
        if(!on06_put(c,r.a[6],0x9c,2,value2))return false;
        const bool negative=(value2&0x8000U)!=0U,overflow=value==0x8000U;
        r.pc=(value2!=0U && negative==overflow)?0xba1b4:0xba1ae;return true;}
    case 0xba1ae:return on06_install(c,0xb9f96,0xba1b4);                                 // MOVE.L #b9f96,(A6) (orphan install value).
    case 0xba1b8:return on06_table(c,0xba1ca,0xba1c4);                                   // MOVEA.L 84(A6),A0; CMPA.W #0,A0; BEQ.W ba1ca.
    case 0xba1c4:return am_call(c,0x4706c,0xba1ca);                                      // JSR 4706c.L.
    // ---- ba1cc (28ae child of ba386): MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L.
    case 0xba1cc:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0xba1d6);
    // LEA ba432.L,A0; MOVE.L A0,84(A6); MOVE.L #ba1e6,(A6).
    case 0xba1d6:r.a[0]=0xba432;if(!on06_put(c,r.a[6],0x84,4,r.a[0]))return false;return on06_install(c,0xba1e6,0xba1e6);
    case 0xba1e6:return am_call(c,0x288c,0xba1ec);                                       // (installed callback) JSR 288c.L.
    case 0xba1ec:return on06_consume(c,true,0xba1f6,0xba1f0);                            // BCS.W ba1f6 (C returned by 288c).
    case 0xba1f0:case 0xd9bd8:case 0xd9c04:r.pc=0x2a00;return true;                      // JMP 2a00.L.
    case 0xba1f6:return am_call(c,0x43e34,0xba1fc);                                      // JSR 43e34.L.
    case 0xba1fc:return on06_table(c,0xba212,0xba208);                                   // MOVEA.L 84(A6),A0; CMPA.W #0,A0; BEQ.W ba212.
    case 0xba208:r.d[0]=0;r.d[1]=0xf;return am_call(c,0x47070,0xba212);                  // MOVEQ #0,D0; MOVEQ #f,D1; JSR 47070.L.

    // ---- ba234: JSR eb774.L; BCC.W ba2b0 (C returned by eb774).
    case 0xba234:return am_call(c,0xeb774,0xba23a);
    case 0xba23a:return on06_consume(c,false,0xba2b0,0xba23e);
    case 0xba23e:return on06_mode(c,2,0xba248,0xba260);                                  // CMPI.W #2,76(A6); BNE.W ba260.
    case 0xba248:return on06_test(c,r.a[6],0xa4,1,0xba250,0xba258);                      // TST.B a4(A6); BNE.W ba258.
    case 0xba250:r.a[1]=0xba224;r.pc=0xba25c;return true;                                // LEA ba224(PC),A1; BRA.W ba25c.
    case 0xba258:r.a[1]=0xba22c;r.pc=0xba25c;return true;                                // LEA ba22c(PC),A1.
    case 0xba25c:r.pc=0xba274;return true;                                               // BRA.W ba274.
    case 0xba260:return on06_test(c,r.a[6],0xa4,1,0xba268,0xba270);                      // TST.B a4(A6); BNE.W ba270.
    case 0xba268:r.a[1]=0xba214;r.pc=0xba274;return true;                                // LEA ba214(PC),A1; BRA.W ba274.
    case 0xba270:r.a[1]=0xba21c;r.pc=0xba274;return true;                                // LEA ba21c(PC),A1.
    case 0xba274:return on06_test(c,r.a[6],0xa4,1,0xba296,0xba27c);                      // TST.B a4(A6); BEQ.W ba296.
    case 0xba27c:return am_call(c,0x497f0,0xba282);                                      // JSR 497f0.L (boundary).
    case 0xba282:return on06_consume(c,false,0xba28e,0xba286);                           // BCC.W ba28e (C returned by 497f0).
    case 0xba286:return on06_set(c,0xa1,0xba292);                                        // ST.B a1(A6); BRA.W ba292.
    case 0xba28e:return on06_set(c,0xa2,0xba292);                                        // ST.B a2(A6).
    case 0xba292:r.pc=0xba2ac;return true;                                               // BRA.W ba2ac.
    case 0xba296:return am_call(c,0x497b6,0xba29c);                                      // JSR 497b6.L.
    case 0xba29c:return on06_consume(c,false,0xba2a8,0xba2a0);                           // BCC.W ba2a8 (C returned by 497b6).
    case 0xba2a0:return on06_set(c,0xa1,0xba2ac);                                        // ST.B a1(A6); BRA.W ba2ac.
    case 0xba2a8:return on06_set(c,0xa2,0xba2ac);                                        // ST.B a2(A6).
    case 0xba2ac:r.pc=0xba2b4;return true;                                               // BRA.W ba2b4.
    case 0xba2b0:return on06_set(c,0xa2,0xba2b4);                                        // ST.B a2(A6).

    // ---- ba2d6: MOVEA.L 8c(A6),A0; CMPI.W #80,(A0); BEQ.W ba2f0 (WORD through the live bus).
    case 0xba2d6:
        if(!on06_get(c,r.a[6],0x8c,4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0],2,value))return false;r.pc=value==0x80U?0xba2f0:0xba2e2;return true;
    // MOVE.W 32(A6),D0; ADD.W (A0)+,D0; MOVE.W D0,32(A6); MOVE.L A0,8c(A6).
    case 0xba2e2:
        if(!on06_get(c,r.a[6],0x32,2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[0],(r.d[0]+value)&65535U);
        if(!on06_put(c,r.a[6],0x32,2,r.d[0]&65535U) || !on06_put(c,r.a[6],0x8c,4,r.a[0]))return false;r.pc=0xba2f0;return true;
    // ANDI.L #ffff0000,32(A6); RTS.
    case 0xba2f0:
        if(!on06_get(c,r.a[6],0x32,4,value) || !on06_put(c,r.a[6],0x32,4,value&0xffff0000U))return false;return am_return(c);

    // ---- ba310: MOVE.W 7e(A6),94(A6); TST.W 76(A6); BEQ.W ba324.
    case 0xba310:
        if(!on06_get(c,r.a[6],0x7e,2,value) || !on06_put(c,r.a[6],0x94,2,value))return false;
        return on06_test(c,r.a[6],0x76,2,0xba324,0xba31e);
    // BSET.B #0,15(A6) (Z only).
    case 0xba31e:if(!on06_get(c,r.a[6],0x15,1,value) || !on06_put(c,r.a[6],0x15,1,(value|1U)&255U))return false;r.pc=0xba324;return true;
    case 0xba324:return on06_child(c,0xb9e64,0,0xba334);                                 // MOVEA.L #b9e64,A0; MOVE.W #0,D0; JSR 28ae.L.
    case 0xba334:return on06_consume(c,true,0xba346,0xba338);                            // BCS.W ba346 (else the TRAP #15 boundary ba338).
    // MOVE.W 76/78/94(A6),76/78/94(A0); MOVE.W 78(A0),D0; CMP.W 94(A0),D0; BLE.W ba372 (signed; else the TRAP #15 boundary ba364).
    case 0xba346:
        if(!on06_copy(c,0x76,2) || !on06_copy(c,0x78,2) || !on06_copy(c,0x94,2) || !on06_get(c,r.a[0],0x78,2,value))return false;
        am_word(r.d[0],value);if(!on06_get(c,r.a[0],0x94,2,value2))return false;
        r.pc=on06_s(r.d[0])<=on06_s(value2)?0xba372:0xba364;return true;
    // MOVE.B 7a(A6),7a(A0); MOVE.B 7b(A6),7b(A0); JSR 491b6.L.
    case 0xba372:if(!on06_copy(c,0x7a,1) || !on06_copy(c,0x7b,1))return false;return am_call(c,0x491b6,0xba384);
    case 0xba386:return on06_child(c,0xba1cc,0,0xba396);                                 // MOVEA.L #ba1cc,A0; MOVE.W #0,D0; JSR 28ae.L.
    case 0xba396:return on06_consume(c,true,0xba3a8,0xba39a);                            // BCS.W ba3a8 (else the TRAP #15 boundary ba39a).
    case 0xba3a8:return am_call(c,0x491b6,0xba3ae);                                      // JSR 491b6.L.
    case 0xba3ae:if(!on06_copy(c,0x76,2))return false;return am_return(c);               // MOVE.W 76(A6),76(A0); RTS.

    // ---- d9bcc: CMPI.B #1,100012.L; BEQ.W d9bde (work RAM BYTE).
    case 0xd9bcc:if(!am_read(c,0x100012,1,value))return false;r.pc=value==1U?0xd9bde:0xd9bd8;return true;
    // MOVE.W #294,76(A6); MOVE.L #d9bea,(A6).
    case 0xd9bde:if(!on06_put(c,r.a[6],0x76,2,0x294))return false;return on06_install(c,0xd9bea,0xd9bea);
    // (installed callback) SUBQ.W #1,76(A6); BCS.W d9bf4 (borrow when the WORD was 0).
    case 0xd9bea:
        if(!on06_get(c,r.a[6],0x76,2,value) || !on06_put(c,r.a[6],0x76,2,(value-1U)&65535U))return false;
        r.pc=value==0U?0xd9bf4:0xd9bf2;return true;
    case 0xd9bf4:return on06_child(c,0x4841a,0xa,0xd9c04);                               // MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L.

    // ---- e90d8: CMPI.B #c,D0; BCS.W e90e4 (unsigned BYTE).
    case 0xe90d8:r.pc=(r.d[0]&255U)<0xcU?0xe90e4:0xe90e0;return true;
    case 0xe90e0:r.d[0]=0;return am_return(c);                                          // MOVEQ #0,D0; RTS.
    // ANDI.W #ff,D0; LEA 5e30(A5),A0; MOVE.B (A0,D0.W),D0; RTS.
    case 0xe90e4:
        am_word(r.d[0],r.d[0]&0xffU);r.a[0]=am_index(r.a[5],0x5e30);
        if(!am_read(c,am_index(r.a[0],r.d[0]),1,value))return false;am_byte(r.d[0],value);return am_return(c);

    // ---- eb774: JSR 49370.L; BCS.W eb7b0; MOVEQ #0/#1,D0; JSR 49392.L; BCC; JSR 49416.L (boundary); BCS.
    case 0xeb774:return am_call(c,0x49370,0xeb77a);
    case 0xeb77a:case 0xeb790:case 0xeb7a6:
        return on06_consume(c,true,0xeb7b0,r.pc==0xeb77aU?0xeb77e:(r.pc==0xeb790U?0xeb794:0xeb7aa));
    case 0xeb77e:case 0xeb794:r.d[0]=r.pc==0xeb77eU?0U:1U;return am_call(c,0x49392,r.pc==0xeb77eU?0xeb786:0xeb79c);
    case 0xeb786:return on06_consume(c,false,0xeb794,0xeb78a);                           // BCC.W eb794 (C returned by 49392).
    case 0xeb79c:return on06_consume(c,false,0xeb7aa,0xeb7a0);                           // BCC.W eb7aa.
    case 0xeb78a:return am_call(c,0x49416,0xeb790);                                      // JSR 49416.L (boundary).
    case 0xeb7a0:return am_call(c,0x49416,0xeb7a6);
    case 0xeb7aa:r.carry=AnimationCarrySet;return am_return(c);                         // ORI.B #1,CCR; RTS.
    case 0xeb7b0:r.carry=AnimationCarryClear;return am_return(c);                       // ANDI.B #fe,CCR; RTS.
    default:return am_error(c,"unsupported animation objects n06 PC");
    }
}
}
