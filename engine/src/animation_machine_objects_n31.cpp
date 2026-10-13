#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t on31_b(std::uint32_t value) {return value&255U;}
std::uint32_t on31_w(std::uint32_t value) {return value&65535U;}
bool on31_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on31_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BTST.B #bit,d16(A6): true when the bit is 1.
bool on31_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on31_get(c,c.s.a[6],displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,d16(A6) (read, then write the changed BYTE).
bool on31_change(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool on) {
    std::uint32_t value=0;if(!on31_get(c,c.s.a[6],displacement,1,value))return false;
    value=on?(value|(1U<<bit)):(value&~(1U<<bit));return on31_put(c,c.s.a[6],displacement,1,value&255U);
}
// MOVE.B from(A6),to(A6).
bool on31_copy(AnimationMachineContext& c,std::uint32_t from,std::uint32_t to) {
    std::uint32_t value=0;return on31_get(c,c.s.a[6],from,1,value) && on31_put(c,c.s.a[6],to,1,value);
}
// TST.B / TST.W / TST.L d16(A6): true when the value is zero.
bool on31_zero(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,bool& zero) {
    std::uint32_t value=0;if(!on31_get(c,c.s.a[6],displacement,size,value))return false;zero=value==0U;return true;
}
// SUBQ.B #1,d16(A6) (8-bit wrap).
bool on31_decrement(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t value=0;return on31_get(c,c.s.a[6],displacement,1,value) && on31_put(c,c.s.a[6],displacement,1,(value+255U)&255U);
}
// MOVE.L #value,(A6) (installed callback LONG).
bool on31_install(AnimationMachineContext& c,std::uint32_t value) {return on31_put(c,c.s.a[6],0,4,value);}
// Bcc.W on a C returned by a callee: clear -> clear_pc, set -> set_pc.
bool on31_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n31 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W 86(A6),D0.
bool on31_area(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!on31_get(c,c.s.a[6],0x86,2,value))return false;am_word(c.s.d[0],value);return true;
}
}
// Objects F4 N31 (96 block starts): the callback 38ba0 (installs 38bac), the installed callbacks 38bac (installs 38c36) and 38c36
// (installs the out-of-range value 38d56), the installed 38c8e chain (installs 38cc0 / 38cfa / 38d18 / 38bac), the code pointer 38d44
// (N23 4dbac JSR (A1); TST.B Clear / ORI Set, read by 4dbb2), the shared JMP 2a00 tail 3a2f4, the 28ae child callback 3a2fa (installs
// 3a334), the shared tail 3a34c / 3a350 / 3a41c (installs 38c8e and the out-of-range value 3a0dc) and the N30a live target 34750 (RTS).
// Boundaries without an executor: 3a4a4 3a5be 3a5d2 3b22a 3b26a 3b2b8 3b2ee 3b302 3b334 3b542 4d734 4d9ba. The 10 consumers read a
// known C returned by 1aa7e / 4d2d4 / 3a4a4 / 3b334 / 49fc6 / 4d766. No port, no bank access, no X / DIV, no computed jump.
bool animation_objects_n31_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool bit=false;
    switch(r.pc) {
    case 0x34750:case 0x38d54:case 0x3a34a:case 0x3a4a2:return am_return(c); // RTS.
    // ---- callback 38ba0: JSR 3b542(PC); MOVE.L #38bac,(A6); RTS.
    case 0x38ba0:return am_call(c,0x3b542,0x38ba4);
    case 0x38ba4:if(!on31_install(c,0x38bac))return false;return am_return(c);
    // ---- installed callback 38bac: MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); LEA 0.W,A0; JSR 4b82e.l.
    case 0x38bac:
        if(!on31_put(c,r.a[6],0x68,2,0x8810) || !on31_put(c,r.a[6],0x1e,2,0x8810))return false;r.a[0]=0;return am_call(c,0x4b82e,0x38bc2);
    // MOVE.W #0,88(A6); MOVEA.L #3b8a0,A0; JSR 3b302(PC) (boundary).
    case 0x38bc2:if(!on31_put(c,r.a[6],0x88,2,0))return false;r.a[0]=0x3b8a0;return am_call(c,0x3b302,0x38bd2);
    case 0x38bd2:return am_call(c,0x3a5d2,0x38bd6);                     // JSR 3a5d2(PC) (boundary).
    // CLR.B a4(A6); CLR.B 9c(A6); MOVE.B #40,a1(A6); BCLR.B #3,15(A6); JSR 3b22a(PC) (boundary).
    case 0x38bd6:
        if(!on31_put(c,r.a[6],0xa4,1,0) || !on31_put(c,r.a[6],0x9c,1,0) || !on31_put(c,r.a[6],0xa1,1,0x40) || !on31_change(c,0x15,3,false))return false;
        return am_call(c,0x3b22a,0x38bee);
    // MOVE.B 1b(A6),14(A6); MOVE.L #0,7e(A6); MOVE.L #0,56(A6); MOVEQ #2,D0; MOVEQ #24,D1; BTST.B #0,15(A6); BEQ.W 38c14.
    case 0x38bee:
        if(!on31_copy(c,0x1b,0x14) || !on31_put(c,r.a[6],0x7e,4,0) || !on31_put(c,r.a[6],0x56,4,0))return false;r.d[0]=2;r.d[1]=0x24;
        if(!on31_bit(c,0x15,0,bit))return false;r.pc=bit?0x38c12:0x38c14;return true;
    case 0x38c12:am_word(r.d[0],(65536U-on31_w(r.d[0]))&65535U);r.pc=0x38c14;return true; // NEG.W D0 (16-bit two's complement).
    case 0x38c14:r.a[0]=0x38d44;return am_call(c,0x4da50,0x38c1e);      // LEA 38d44(PC),A0; JSR 4da50.l (code pointer).
    case 0x38c1e:return am_call(c,0x496c2,0x38c24);                     // JSR 496c2.l.
    // MOVE.B #0,78(A6); MOVE.B #0,b5(A6); MOVE.L #38c36,(A6) (falls through into the installed 38c36).
    case 0x38c24:
        if(!on31_put(c,r.a[6],0x78,1,0) || !on31_put(c,r.a[6],0xb5,1,0) || !on31_install(c,0x38c36))return false;r.pc=0x38c36;return true;
    // ---- installed callback 38c36: LEA 3b736(PC),A0; JSR 1aa7e.l; BCS.W 3a2f4.
    case 0x38c36:case 0x38cce:case 0x38d18:r.a[0]=0x3b736;return am_call(c,0x1aa7e,r.pc==0x38c36?0x38c40U:(r.pc==0x38cce?0x38cd8U:0x38d22U));
    case 0x38c40:return on31_carry(c,0x38c44,0x3a2f4);                  // BCS.W 3a2f4 (C returned by 1aa7e).
    case 0x38cd8:return on31_carry(c,0x38cdc,0x3a2f4);
    case 0x38d22:return on31_carry(c,0x38d26,0x3a2f4);
    case 0x38c44:case 0x38cdc:case 0x38d26:return am_call(c,0x3b26a,r.pc+4U); // JSR 3b26a(PC) (boundary).
    case 0x38c48:r.a[0]=0x3b74e;return am_call(c,0x4d2d4,0x38c52);      // LEA 3b74e(PC),A0; JSR 4d2d4.l.
    case 0x38c52:return on31_carry(c,0x38c86,0x38c56);                  // BCC.W 38c86 (C returned by 4d2d4).
    case 0x38c56:if(!on31_put(c,r.a[6],0x86,2,on31_w(r.d[0])))return false;return am_call(c,0x3a4a4,0x38c5e); // MOVE.W D0,86(A6); JSR 3a4a4(PC).
    case 0x38c5e:return on31_carry(c,0x38c86,0x38c62);                  // BCC.W 38c86 (C returned by 3a4a4).
    // MOVE.W D0,88(A6); MOVE.W 86(A6),D0; MOVE.B #11,D1; MOVE.B ad(A6),D2; MOVE.B ae(A6),D3; MOVE.W 54(A6),D4; JSR 4d508.l.
    case 0x38c62:
        if(!on31_put(c,r.a[6],0x88,2,on31_w(r.d[0])) || !on31_area(c))return false;am_byte(r.d[1],0x11);
        if(!on31_get(c,r.a[6],0xad,1,value))return false;am_byte(r.d[2],value);
        if(!on31_get(c,r.a[6],0xae,1,value))return false;am_byte(r.d[3],value);
        if(!on31_get(c,r.a[6],0x54,2,value))return false;am_word(r.d[4],value);return am_call(c,0x4d508,0x38c80);
    case 0x38c80:if(!on31_install(c,0x38d56))return false;r.pc=0x38c86;return true; // MOVE.L #38d56,(A6) (out-of-range value).
    case 0x38c86:case 0x38ce0:case 0x38d2a:return am_call(c,0x3b334,r.pc+4U); // JSR 3b334(PC) (boundary).
    case 0x38c8a:r.pc=0x3a34c;return true;                               // BRA.W 3a34c.
    case 0x3a34c:r.pc=0x3a3e8;return true;                               // BRA.W 3a3e8.
    // ---- installed callback 38c8e (3a388): CMPI.B #11,9f(A6); BCC.W 38cfa.
    case 0x38c8e:if(!on31_get(c,r.a[6],0x9f,1,value))return false;r.pc=on31_b(value)>=0x11U?0x38cfa:0x38c98;return true;
    case 0x38c98:am_word(r.d[0],0x1a5f);return am_call(c,0x3af8,0x38ca2); // MOVE.W #1a5f,D0; JSR 3af8.l.
    case 0x38ca2:r.a[0]=0x3b8d6;return am_call(c,0x3b302,0x38cac);      // MOVEA.L #3b8d6,A0; JSR 3b302(PC) (boundary).
    case 0x38cac:case 0x38d0a:return am_call(c,0x3a5d2,r.pc+4U);        // JSR 3a5d2(PC) (boundary).
    // MOVE.B #4,95(A6); CLR.L 64(A6); MOVE.L #38cc0,(A6) (falls through into the installed 38cc0).
    case 0x38cb0:
        if(!on31_put(c,r.a[6],0x95,1,4) || !on31_put(c,r.a[6],0x64,4,0) || !on31_install(c,0x38cc0))return false;r.pc=0x38cc0;return true;
    // BSET.B #3,94(A6); MOVEA.L 82(A6),A0; JSR 3a5be(PC) (boundary).
    case 0x38cc0:
        if(!on31_change(c,0x94,3,true) || !on31_get(c,r.a[6],0x82,4,value))return false;r.a[0]=value;return am_call(c,0x3a5be,0x38cce);
    case 0x38ce4:return on31_carry(c,0x38cee,0x38ce8);                  // BCC.W 38cee (C returned by 3b334).
    case 0x38ce8:if(!on31_install(c,0x38cfa))return false;r.pc=0x38cee;return true; // MOVE.L #38cfa,(A6).
    case 0x38cee:case 0x38d38:if(!on31_put(c,r.a[6],0x56,4,0))return false;r.pc=0x3a34c;return true; // MOVE.L #0,56(A6); BRA.W 3a34c.
    // MOVE.B #11,9f(A6); MOVEA.L #3b8ac,A0; JSR 3b302(PC) (boundary).
    case 0x38cfa:if(!on31_put(c,r.a[6],0x9f,1,0x11))return false;r.a[0]=0x3b8ac;return am_call(c,0x3b302,0x38d0a);
    // CLR.L 64(A6); MOVE.L #38d18,(A6) (falls through into the installed 38d18).
    case 0x38d0e:if(!on31_put(c,r.a[6],0x64,4,0) || !on31_install(c,0x38d18))return false;r.pc=0x38d18;return true;
    case 0x38d2e:return on31_carry(c,0x38d38,0x38d32);                  // BCC.W 38d38 (C returned by 3b334).
    case 0x38d32:if(!on31_install(c,0x38bac))return false;r.pc=0x38d38;return true; // MOVE.L #38bac,(A6).
    // ---- code pointer 38d44 (N23 4dbac JSR (A1)): MOVEA.L c(A6),A0; TST.B b3(A0); BEQ.W 38d54 (C = 0) / ORI.B #1,CCR.
    case 0x38d44:
        if(!on31_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!on31_get(c,r.a[0],0xb3,1,value))return false;
        r.carry=AnimationCarryClear;r.pc=on31_b(value)==0U?0x38d54:0x38d50;return true;
    case 0x38d50:r.carry=AnimationCarrySet;r.pc=0x38d54;return true;
    case 0x3a2f4:case 0x3a344:r.pc=0x2a00;return true;                  // JMP 2a00.l.
    // ---- 28ae child callback 3a2fa (N33 3a2d4, 3a02a): MOVE.W #18de,D0; JSR 3af8.l.
    case 0x3a2fa:am_word(r.d[0],0x18de);return am_call(c,0x3af8,0x3a304);
    case 0x3a304:am_word(r.d[0],0x363);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3a312); // MOVE.W #363,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); MOVEA.L #6f536,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3a312:
        if(!on31_put(c,r.a[6],0x68,2,0x1001) || !on31_put(c,r.a[6],0x1e,2,0x1001))return false;r.a[1]=0x6f536;am_word(r.d[0],0x100);
        return am_call(c,0x49f8c,0x3a32e);
    case 0x3a32e:if(!on31_install(c,0x3a334))return false;r.pc=0x3a334;return true; // MOVE.L #3a334,(A6).
    case 0x3a334:return am_call(c,0x4be06,0x3a33a);                     // JSR 4be06.l.
    case 0x3a33a:return am_call(c,0x49fc6,0x3a340);                     // JSR 49fc6.l.
    case 0x3a340:return on31_carry(c,0x3a34a,0x3a344);                  // BCC.W 3a34a (C returned by 49fc6).
    // ---- shared tail 3a350 (N32, 38d56 chain): BTST.B #7,15(A6); BEQ.W 3a376.
    case 0x3a350:if(!on31_bit(c,0x15,7,bit))return false;r.pc=bit?0x3a35a:0x3a376;return true;
    // MOVEQ #0,D0; MOVE.B D0,a4(A6); MOVE.B #1,9c(A6); MOVE.B #40,a1(A6); BCLR.B #3,15(A6); BRA.W 3a380.
    case 0x3a35a:
        r.d[0]=0;if(!on31_put(c,r.a[6],0xa4,1,0) || !on31_put(c,r.a[6],0x9c,1,1) || !on31_put(c,r.a[6],0xa1,1,0x40) || !on31_change(c,0x15,3,false))
            return false;
        r.pc=0x3a380;return true;
    // ADDQ.B #1,ab(A6); SCS.B D0 (C of the 8-bit add); OR.B D0,ab(A6) (reads the BYTE again).
    case 0x3a376:
        if(!on31_get(c,r.a[6],0xab,1,value) || !on31_put(c,r.a[6],0xab,1,(value+1U)&255U))return false;am_byte(r.d[0],on31_b(value)==255U?0xffU:0U);
        if(!on31_get(c,r.a[6],0xab,1,value) || !on31_put(c,r.a[6],0xab,1,(value|r.d[0])&255U))return false;r.pc=0x3a380;return true;
    case 0x3a380:return am_call(c,0x3a4a4,0x3a384);                     // JSR 3a4a4(PC) (boundary).
    case 0x3a384:return on31_carry(c,0x3a388,0x3a392);                  // BCS.W 3a392 (C returned by 3a4a4).
    case 0x3a388:if(!on31_install(c,0x38c8e))return false;r.pc=0x3a3e8;return true; // MOVE.L #38c8e,(A6); BRA.W 3a3e8.
    case 0x3a392:if(!on31_area(c))return false;return am_call(c,0x4d7a6,0x3a39c); // MOVE.W 86(A6),D0; JSR 4d7a6.l.
    case 0x3a39c:r.pc=on31_b(r.d[0])!=0x11U?0x3a3ac:0x3a3a4;return true; // CMPI.B #11,D0; BNE.W 3a3ac.
    // MOVE.B D1,ad(A6); MOVE.B D2,ae(A6).
    case 0x3a3a4:if(!on31_put(c,r.a[6],0xad,1,on31_b(r.d[1])) || !on31_put(c,r.a[6],0xae,1,on31_b(r.d[2])))return false;r.pc=0x3a3ac;return true;
    case 0x3a3ac:if(!on31_area(c))return false;return am_call(c,0x4d734,0x3a3b6); // MOVE.W 86(A6),D0; JSR 4d734.l (boundary).
    // MOVE.W 86(A6),D0; MOVEA.L 56(A6),A1; JSR 4d9ba.l (boundary).
    case 0x3a3b6:if(!on31_area(c) || !on31_get(c,r.a[6],0x56,4,value))return false;r.a[1]=value;return am_call(c,0x4d9ba,0x3a3c4);
    case 0x3a3c4:if(!on31_zero(c,0x5e,1,bit))return false;r.pc=bit?0x3a3e8:0x3a3cc;return true; // TST.B 5e(A6); BEQ.W 3a3e8.
    case 0x3a3cc:if(!on31_bit(c,0x61,6,bit))return false;r.pc=bit?0x3a3e8:0x3a3d6;return true; // BTST.B #6,61(A6); BNE.W 3a3e8.
    case 0x3a3d6:am_word(r.d[0],0x1e);return am_call(c,0x3b2ee,0x3a3de); // MOVE.W #1e,D0; JSR 3b2ee(PC) (boundary).
    case 0x3a3de:am_word(r.d[0],0x1a59);return am_call(c,0x3af8,0x3a3e8); // MOVE.W #1a59,D0; JSR 3af8.l.
    case 0x3a3e8:return am_call(c,0x4b54e,0x3a3ee);                     // JSR 4b54e.l.
    // BTST.B #7,15(A6) (Z overwritten); TST.W 64(A6); BEQ.W 3a406.
    case 0x3a3ee:if(!on31_bit(c,0x15,7,bit) || !on31_zero(c,0x64,2,bit))return false;r.pc=bit?0x3a406:0x3a3fc;return true;
    case 0x3a3fc:r.a[0]=0x3b7ec;return am_call(c,0x4ae4a,0x3a406);      // LEA 3b7ec(PC),A0; JSR 4ae4a.l.
    // BTST.B #7,61(A6); SNE.B D0; BEQ.W 3a418.
    case 0x3a406:if(!on31_bit(c,0x61,7,bit))return false;am_byte(r.d[0],bit?0xffU:0U);r.pc=bit?0x3a412:0x3a418;return true;
    case 0x3a412:if(!on31_install(c,0x3a0dc))return false;r.pc=0x3a418;return true; // MOVE.L #3a0dc,(A6) (out-of-range value).
    // AND.B D0,5e(A6) (falls through into 3a41c).
    case 0x3a418:if(!on31_get(c,r.a[6],0x5e,1,value) || !on31_put(c,r.a[6],0x5e,1,value&r.d[0]&255U))return false;r.pc=0x3a41c;return true;
    // ---- shared tail 3a41c (N32, N33): BCLR.B #6,61(A6); TST.W 8a(A6); BEQ.W 3a434.
    case 0x3a41c:if(!on31_change(c,0x61,6,false) || !on31_zero(c,0x8a,2,bit))return false;r.pc=bit?0x3a434:0x3a42a;return true;
    // SUBQ.W #1,8a(A6); BSET.B #6,61(A6).
    case 0x3a42a:
        if(!on31_get(c,r.a[6],0x8a,2,value) || !on31_put(c,r.a[6],0x8a,2,(value+65535U)&65535U) || !on31_change(c,0x61,6,true))return false;
        r.pc=0x3a434;return true;
    case 0x3a434:return am_call(c,0x4d766,0x3a43a);                     // JSR 4d766.l.
    case 0x3a43a:return on31_carry(c,0x3a444,0x3a43e);                  // BCC.W 3a444 (C returned by 4d766).
    case 0x3a43e:if(!on31_change(c,0x61,6,true))return false;r.pc=0x3a444;return true; // BSET.B #6,61(A6).
    case 0x3a444:if(!on31_zero(c,0x7e,4,bit))return false;r.pc=bit?0x3a460:0x3a44c;return true; // TST.L 7e(A6); BEQ.W 3a460.
    case 0x3a44c:if(!on31_copy(c,0x1a,0x14))return false;return am_call(c,0x3b2b8,0x3a456); // MOVE.B 1a(A6),14(A6); JSR 3b2b8(PC).
    case 0x3a456:if(!on31_change(c,0x61,6,true))return false;r.pc=0x3a478;return true; // BSET.B #6,61(A6); BRA.W 3a478.
    // MOVE.B 1b(A6),14(A6); MOVE.W 8a(A6),D0; ANDI.W #1,D0; BEQ.W 3a478.
    case 0x3a460:
        if(!on31_copy(c,0x1b,0x14) || !on31_get(c,r.a[6],0x8a,2,value))return false;am_word(r.d[0],value&1U);
        r.pc=(value&1U)==0U?0x3a478:0x3a472;return true;
    case 0x3a472:if(!on31_copy(c,0x19,0x14))return false;r.pc=0x3a478;return true; // MOVE.B 19(A6),14(A6).
    // BCLR.B #3,94(A6); BCLR.B #2,94(A6); MOVE.B #ff,9e(A6); TST.B a3(A6); BEQ.W 3a496.
    case 0x3a478:
        if(!on31_change(c,0x94,3,false) || !on31_change(c,0x94,2,false) || !on31_put(c,r.a[6],0x9e,1,0xff) || !on31_zero(c,0xa3,1,bit))return false;
        r.pc=bit?0x3a496:0x3a492;return true;
    case 0x3a492:if(!on31_decrement(c,0xa3))return false;r.pc=0x3a496;return true; // SUBQ.B #1,a3(A6).
    case 0x3a496:if(!on31_zero(c,0xb2,1,bit))return false;r.pc=bit?0x3a4a2:0x3a49e;return true; // TST.B b2(A6); BEQ.W 3a4a2.
    case 0x3a49e:if(!on31_decrement(c,0xb2))return false;r.pc=0x3a4a2;return true; // SUBQ.B #1,b2(A6).
    default:return am_error(c,"unsupported animation objects n31 PC");
    }
}
}
