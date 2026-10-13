#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONG (live bus, current PVC bank): the animation record of 33b12 / 345c2 / 3471a (id 102).
const std::uint32_t ON30_BANK_102=0x2000a4;
// Fixed ROM tables (live bus, no index check as in the original): the 346c0 BYTE offsets (3467e), the 346fc BYTE transition matrix
// (346d0), the 34708 LONG continuation table (346ea) and the 348a2 LONG continuation table (3488a).
const std::uint32_t ON30_OFFSETS=0x346c0;
const std::uint32_t ON30_MATRIX=0x346fc;
const std::uint32_t ON30_TARGETS=0x34708;
const std::uint32_t ON30_STATES=0x348a2;
std::uint32_t on30_b(std::uint32_t value) {return value&255U;}
std::uint32_t on30_w(std::uint32_t value) {return value&65535U;}
// EXT.W: the BYTE sign bit refills the upper byte of the WORD (explicit, no signed conversion).
std::uint32_t on30_ext(std::uint32_t value) {const std::uint32_t u=value&255U;return (u&0x80U)?(u|0xff00U):u;}
bool on30_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on30_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BTST.B #bit,d16(A6): true when the bit is 1.
bool on30_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on30_get(c,c.s.a[6],displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,d16(A6) (read, then write the changed BYTE).
bool on30_change(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool on) {
    std::uint32_t value=0;if(!on30_get(c,c.s.a[6],displacement,1,value))return false;
    value=on?(value|(1U<<bit)):(value&~(1U<<bit));return on30_put(c,c.s.a[6],displacement,1,value&255U);
}
// MOVE.B from(src),to(A6).
bool on30_copy(AnimationMachineContext& c,std::uint32_t src,std::uint32_t from,std::uint32_t to,unsigned int size) {
    std::uint32_t value=0;return on30_get(c,src,from,size,value) && on30_put(c,c.s.a[6],to,size,value);
}
// MOVE.L #value,(A6) (installed callback LONG).
bool on30_install(AnimationMachineContext& c,std::uint32_t value) {return on30_put(c,c.s.a[6],0,4,value);}
// BCC.W on a C returned by a callee: clear -> clear_pc, set -> set_pc.
bool on30_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n30 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.l.
bool on30_animation(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #102,20(A6); MOVE.L 2000a4.l,22(A6).
bool on30_record(AnimationMachineContext& c) {
    std::uint32_t value=0;
    return on30_put(c,c.s.a[6],0x20,2,0x102) && am_read(c,ON30_BANK_102,4,value) && on30_put(c,c.s.a[6],0x22,4,value);
}
// ADDI.L #ffffb000,3a(A6) (32-bit wrap).
bool on30_lift(AnimationMachineContext& c) {
    std::uint32_t value=0;return on30_get(c,c.s.a[6],0x3a,4,value) && on30_put(c,c.s.a[6],0x3a,4,(value+0xffffb000U)&0xffffffffU);
}
// ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L table(PC,D0.W),A1.
bool on30_target(AnimationMachineContext& c,std::uint32_t table) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;am_word(r.d[0],r.d[0]&255U);am_word(r.d[0],(r.d[0]*4U)&65535U);
    if(!am_read(c,am_index(table,r.d[0]),4,value))return false;r.a[1]=value;return true;
}
}
// Objects F4 N30a (166 block starts): the stage event callback 33132 (installs 33180 / 33b0c, 331d8 / 33b0c / 3323e), the installed
// callback 336d2 with the 27-slot BRA.W table 336e6 and its installed 337a8 (installs 3383c), the shared tail 33958 / 33a88 (installs
// 336d2), the setup 33b12 (28ae children 41fe6 / 345c2 / 3471a), the helpers 33be0 33c0e 33c2a 33c54, the interpreter table entry
// 33f4c, the 28ae child callbacks 345c2 and 3471a with the LONG table targets 345f2 34616 34644, the helper 3465a and the two selectors
// 346c6 / 34874 whose JMP (A1) is a live target (continuations 34610 34634 34658, N31 34750). The install chain 3323e (N30b) is not
// routed. Boundaries without an executor: 33846 33940 33f1a 34490 3453a 4be6c 4bfb4 4bfc0 4d418 4d8d8 4db18 (and the live target
// 34750). 3382e (BNE after TST.B or SUBQ.B) is folded into 3381c / 3382a. The 10 consumers read a known C returned by 1aa7e / 4d2d4 /
// 4d418 / 4d766 / 28ae / 3465a (= 49fc6) / 288c; ORI CCR (33b90) sets it. No port, no bank change, no X / DIV.
bool animation_objects_n30_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool bit=false;
    switch(r.pc) {
    // ---- stage event callback 33132 (N29 33124 / N30b 33a0c install, N30b 33546 BRA.W): animation 34c80.
    case 0x33132:
        if(!on30_put(c,r.a[6],0x9a,1,1) || !on30_put(c,r.a[6],0x9b,1,0) || !on30_put(c,r.a[6],0x76,4,0) || !on30_put(c,r.a[6],0x56,4,0))return false;
        return on30_animation(c,0x34c80,0x3315e);
    case 0x3315e:if(!on30_copy(c,r.a[6],0x1b,0x14,1))return false;return am_call(c,0x46ef4,0x3316a); // MOVE.B 1b(A6),14(A6); JSR 46ef4.l.
    case 0x3316a:return am_call(c,0x496c2,0x33170);                     // JSR 496c2.l.
    case 0x33170:if(!on30_bit(c,0x15,7,bit))return false;r.pc=bit?0x331ac:0x3317a;return true; // BTST.B #7,15(A6); BNE.W 331ac.
    case 0x3317a:if(!on30_install(c,0x33180))return false;r.pc=0x33180;return true; // MOVE.L #33180,(A6).
    case 0x33180:return am_call(c,0x33c54,0x33184);                     // JSR 33c54(PC).
    case 0x33184:r.a[0]=0x349ce;return am_call(c,0x1aa7e,0x3318e);      // LEA 349ce(PC),A0; JSR 1aa7e.l.
    case 0x3318e:return on30_carry(c,0x33198,0x33192);                  // BCC.W 33198 (C returned by 1aa7e).
    case 0x33192:if(!on30_install(c,0x33b0c))return false;r.pc=0x33198;return true; // MOVE.L #33b0c,(A6).
    case 0x33198:if(!on30_bit(c,0x15,7,bit))return false;r.pc=bit?0x331ac:0x331a2;return true; // BTST.B #7,15(A6); BNE.W 331ac.
    case 0x331a2:return am_call(c,0x49fc6,0x331a8);                     // JSR 49fc6.l.
    case 0x331a8:case 0x3323a:r.pc=0x33958;return true;                 // BRA.W 33958.
    // ---- 331ac (BNE.W from 33170 / 33198): animation 34c80, install 331d8.
    case 0x331ac:if(!on30_put(c,r.a[6],0x9b,1,0))return false;return on30_animation(c,0x34c80,0x331c2);
    case 0x331c2:return am_call(c,0x496c2,0x331c8);                     // JSR 496c2.l.
    case 0x331c8:r.d[0]=0x10;r.d[1]=0x30;return am_call(c,0x4da4a,0x331d2); // MOVEQ #10,D0; MOVEQ #30,D1; JSR 4da4a.l.
    case 0x331d2:if(!on30_install(c,0x331d8))return false;r.pc=0x331d8;return true; // MOVE.L #331d8,(A6).
    case 0x331d8:return am_call(c,0x33c54,0x331dc);                     // (installed) JSR 33c54(PC).
    case 0x331dc:return am_call(c,0x49fc6,0x331e2);                     // JSR 49fc6.l.
    case 0x331e2:r.a[0]=0x349ce;return am_call(c,0x1aa7e,0x331ec);      // LEA 349ce(PC),A0; JSR 1aa7e.l.
    case 0x331ec:return on30_carry(c,0x331f6,0x331f0);                  // BCC.W 331f6 (C returned by 1aa7e).
    case 0x331f0:if(!on30_install(c,0x33b0c))return false;r.pc=0x331f6;return true; // MOVE.L #33b0c,(A6).
    case 0x331f6:r.a[0]=0x349e6;return am_call(c,0x4d2d4,0x33200);      // LEA 349e6(PC),A0; JSR 4d2d4.l.
    case 0x33200:return on30_carry(c,0x3323a,0x33204);                  // BCC.W 3323a (C returned by 4d2d4).
    // MOVE.W D0,7a(A6); MOVEQ #c,D2; MOVEQ #18,D3; JSR 4d418.l (boundary).
    case 0x33204:if(!on30_put(c,r.a[6],0x7a,2,on30_w(r.d[0])))return false;r.d[2]=0xc;r.d[3]=0x18;return am_call(c,0x4d418,0x33212);
    case 0x33212:return on30_carry(c,0x3323a,0x33216);                  // BCC.W 3323a (C returned by 4d418).
    // MOVE.W D0,7c(A6); MOVE.W 7a(A6),D0; MOVE.B #4,D1; MOVE.B 93(A6),D2; MOVE.B 94(A6),D3; MOVE.W 54(A6),D4; JSR 4d508.l.
    case 0x33216:
        if(!on30_put(c,r.a[6],0x7c,2,on30_w(r.d[0])) || !on30_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],4);
        if(!on30_get(c,r.a[6],0x93,1,value))return false;am_byte(r.d[2],value);
        if(!on30_get(c,r.a[6],0x94,1,value))return false;am_byte(r.d[3],value);
        if(!on30_get(c,r.a[6],0x54,2,value))return false;am_word(r.d[4],value);return am_call(c,0x4d508,0x33234);
    case 0x33234:if(!on30_install(c,0x3323e))return false;r.pc=0x3323a;return true; // MOVE.L #3323e,(A6) (N30b value).
    // ---- installed callback 336d2 (33a9a): MOVE.B 5e(A6),D0; CMPI.B #1b,D0; BCC.W 33756.
    case 0x336d2:if(!on30_get(c,r.a[6],0x5e,1,value))return false;am_byte(r.d[0],value);r.pc=on30_b(value)>=0x1bU?0x33756:0x336de;return true;
    // ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; JMP 336ea(PC,D0.W) (F1 decision 3: no bound check here; 336d2 bounds the index to 0..26).
    case 0x336de:am_word(r.d[0],r.d[0]&255U);am_word(r.d[0],(r.d[0]*4U)&65535U);r.pc=am_index(0x336ea,r.d[0]);return true;
    // The 27 BRA.W slots of 336ea: k = 24 -> 33846 (boundary), every other k -> 33756.
    case 0x3374a:r.pc=0x33846;return true;
    case 0x336ea:case 0x336ee:case 0x336f2:case 0x336f6:case 0x336fa:case 0x336fe:case 0x33702:case 0x33706:case 0x3370a:case 0x3370e:
    case 0x33712:case 0x33716:case 0x3371a:case 0x3371e:case 0x33722:case 0x33726:case 0x3372a:case 0x3372e:case 0x33732:case 0x33736:
    case 0x3373a:case 0x3373e:case 0x33742:case 0x33746:case 0x3374e:case 0x33752:r.pc=0x33756;return true;
    case 0x33756:return on30_animation(c,0x34bec,0x33766);
    // MOVE.B #4,9b(A6); MOVE.B #1,9a(A6); MOVE.W #1ac8,D0; JSR 3af8.l.
    case 0x33766:if(!on30_put(c,r.a[6],0x9b,1,4) || !on30_put(c,r.a[6],0x9a,1,1))return false;am_word(r.d[0],0x1ac8);return am_call(c,0x3af8,0x3377c);
    case 0x3377c:return am_call(c,0x496c2,0x33782);                     // JSR 496c2.l.
    case 0x33782:return am_call(c,0x46ef4,0x33788);                     // JSR 46ef4.l.
    // MOVE.L #34906,76(A6); MOVEQ #10,D0; MOVE.W #2c,D1; JSR 4db18.l (boundary).
    case 0x33788:if(!on30_put(c,r.a[6],0x76,4,0x34906))return false;r.d[0]=0x10;am_word(r.d[1],0x2c);return am_call(c,0x4db18,0x3379c);
    // MOVE.B #60,92(A6); MOVE.L #337a8,(A6) (falls through into the installed 337a8).
    case 0x3379c:if(!on30_put(c,r.a[6],0x92,1,0x60) || !on30_install(c,0x337a8))return false;r.pc=0x337a8;return true;
    case 0x337a8:return am_call(c,0x4d8d8,0x337ae);                     // JSR 4d8d8.l (boundary).
    case 0x337ae:r.pc=(r.d[0]&0x80U)!=0U?0x337de:0x337b4;return true;   // TST.B D0; BMI.W 337de.
    case 0x337b4:return am_call(c,0x33c2a,0x337b8);                     // JSR 33c2a(PC).
    case 0x337b8:return am_call(c,0x33c0e,0x337bc);                     // JSR 33c0e(PC).
    case 0x337bc:r.pc=((r.d[0]>>5)&1U)!=0U?0x337c4:0x337cc;return true;  // BTST.B #5,D0; BEQ.W 337cc.
    case 0x337c4:am_byte(r.d[1],4);return am_call(c,0x33940,0x337cc);   // MOVE.B #4,D1; JSR 33940(PC) (boundary).
    // MOVE.W 7a(A6),D0; MOVEQ #c,D2; MOVEQ #18,D3; JSR 4d418.l (boundary).
    case 0x337cc:if(!on30_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);r.d[2]=0xc;r.d[3]=0x18;return am_call(c,0x4d418,0x337da);
    case 0x337da:r.pc=0x337e2;return true;                               // BRA.W 337e2.
    case 0x337de:return am_call(c,0x33c54,0x337e2);                     // JSR 33c54(PC).
    case 0x337e2:return am_call(c,0x4d8d8,0x337e8);                     // JSR 4d8d8.l (boundary).
    case 0x337e8:r.pc=(r.d[0]&0x80U)==0U?0x33816:0x337ee;return true;   // TST.B D0; BPL.W 33816.
    case 0x337ee:if(!on30_get(c,r.a[6],0x9b,1,value))return false;r.pc=on30_b(value)==0U?0x33816:0x337f8;return true; // CMPI.B #0,9b(A6); BEQ.W.
    case 0x337f8:if(!on30_put(c,r.a[6],0x9b,1,0))return false;return on30_animation(c,0x34cf6,0x3380e); // MOVE.B #0,9b(A6); animation 34cf6.
    case 0x3380e:return am_call(c,0x34490,0x33812);                     // JSR 34490(PC) (boundary).
    case 0x33812:return am_call(c,0x3453a,0x33816);                     // JSR 3453a(PC) (boundary).
    case 0x33816:return am_call(c,0x49fc6,0x3381c);                     // JSR 49fc6.l.
    // MOVE.W #8000,8a(A6); TST.B 92(A6); BEQ.W 3382e (folded: Z = 1 there, so the BNE.W 33838 at 3382e falls through to 33832).
    case 0x3381c:
        if(!on30_put(c,r.a[6],0x8a,2,0x8000) || !on30_get(c,r.a[6],0x92,1,value))return false;r.pc=on30_b(value)==0U?0x33832:0x3382a;return true;
    // SUBQ.B #1,92(A6); BNE.W 33838 (3382e folded).
    case 0x3382a:
        if(!on30_get(c,r.a[6],0x92,1,value))return false;value=(value+255U)&255U;if(!on30_put(c,r.a[6],0x92,1,value))return false;
        r.pc=value!=0U?0x33838:0x33832;return true;
    case 0x33832:if(!on30_install(c,0x3383c))return false;r.pc=0x33838;return true; // MOVE.L #3383c,(A6) (value outside the unit).
    case 0x33838:r.pc=0x33aa4;return true;                               // BRA.W 33aa4.
    // ---- shared tail 33958 (BRA.W 33a88) / 33a88.
    case 0x33958:r.pc=0x33a88;return true;
    case 0x33a88:return am_call(c,0x4b54e,0x33a8e);                     // JSR 4b54e.l.
    // BTST.B #7,61(A6); SNE.B D0; BEQ.W 33aa0.
    case 0x33a8e:if(!on30_bit(c,0x61,7,bit))return false;am_byte(r.d[0],bit?0xffU:0U);r.pc=bit?0x33a9a:0x33aa0;return true;
    case 0x33a9a:if(!on30_install(c,0x336d2))return false;r.pc=0x33aa0;return true; // MOVE.L #336d2,(A6).
    // AND.B D0,5e(A6).
    case 0x33aa0:if(!on30_get(c,r.a[6],0x5e,1,value) || !on30_put(c,r.a[6],0x5e,1,(value&r.d[0])&255U))return false;r.pc=0x33aa4;return true;
    // BCLR.B #6,61(A6); TST.W 7e(A6); BEQ.W 33abc.
    case 0x33aa4:if(!on30_change(c,0x61,6,false) || !on30_get(c,r.a[6],0x7e,2,value))return false;r.pc=on30_w(value)==0U?0x33abc:0x33ab2;return true;
    // SUBQ.W #1,7e(A6); BSET.B #6,61(A6).
    case 0x33ab2:
        if(!on30_get(c,r.a[6],0x7e,2,value) || !on30_put(c,r.a[6],0x7e,2,(value+65535U)&65535U) || !on30_change(c,0x61,6,true))return false;
        r.pc=0x33abc;return true;
    case 0x33abc:return am_call(c,0x4d766,0x33ac2);                     // JSR 4d766.l.
    case 0x33ac2:return on30_carry(c,0x33acc,0x33ac6);                  // BCC.W 33acc (C returned by 4d766).
    case 0x33ac6:if(!on30_change(c,0x61,6,true))return false;r.pc=0x33acc;return true; // BSET.B #6,61(A6).
    case 0x33acc:if(!on30_get(c,r.a[6],0x76,4,value))return false;r.pc=value==0U?0x33ae8:0x33ad4;return true; // TST.L 76(A6); BEQ.W 33ae8.
    case 0x33ad4:if(!on30_copy(c,r.a[6],0x1a,0x14,1))return false;return am_call(c,0x33f1a,0x33ade); // MOVE.B 1a(A6),14(A6); JSR 33f1a(PC).
    case 0x33ade:if(!on30_change(c,0x61,6,true))return false;r.pc=0x33b04;return true; // BSET.B #6,61(A6); BRA.W 33b04.
    // MOVE.B 1b(A6),14(A6); MOVE.W 7e(A6),D0; ANDI.W #1,D0; BEQ.W 33b04.
    case 0x33ae8:
        if(!on30_copy(c,r.a[6],0x1b,0x14,1) || !on30_get(c,r.a[6],0x7e,2,value))return false;am_word(r.d[0],value&1U);
        r.pc=on30_w(r.d[0])==0U?0x33b04:0x33afa;return true;
    // MOVE.B 19(A6),14(A6); ST.B 8c(A6).
    case 0x33afa:if(!on30_copy(c,r.a[6],0x19,0x14,1) || !on30_put(c,r.a[6],0x8c,1,0xff))return false;r.pc=0x33b04;return true;
    case 0x33b04:if(!on30_put(c,r.a[6],0x95,1,2))return false;return am_return(c); // MOVE.B #2,95(A6); RTS.
    case 0x33b0c:case 0x34714:case 0x3489c:r.pc=0x2a00;return true;      // JMP 2a00.l.
    // ---- setup 33b12 (N29 3311c JSR): id 102, 8ebe x3, 4d81c, 28ae children 41fe6 / 345c2 / 3471a.
    case 0x33b12:if(!on30_record(c))return false;am_word(r.d[0],0xce);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x33b2e);
    case 0x33b2e:am_word(r.d[0],0xce);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x33b3c);  // MOVE.W #ce,D0; MOVE.B #1,D1; JSR 8ebe.l.
    case 0x33b3c:am_word(r.d[0],0xd);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x33b4a);   // MOVE.W #d,D0; MOVE.B #1,D1; JSR 8ebe.l.
    // MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); MOVEQ #4,D1; JSR 4d81c.l.
    case 0x33b4a:if(!on30_put(c,r.a[6],0x68,2,0x8810) || !on30_put(c,r.a[6],0x1e,2,0x8810))return false;r.d[1]=4;return am_call(c,0x4d81c,0x33b5e);
    // MOVE.B D1,93(A6); MOVE.B D2,94(A6); MOVE.W D3,54(A6); MOVE.B #2,9a(A6); MOVE.B #0,9b(A6); MOVE.B #5,8e(A6); MOVEA.L #41fe6,A0;
    // MOVE.W #a,D0; JSR 28ae.l.
    case 0x33b5e:
        if(!on30_put(c,r.a[6],0x93,1,on30_b(r.d[1])) || !on30_put(c,r.a[6],0x94,1,on30_b(r.d[2])) || !on30_put(c,r.a[6],0x54,2,on30_w(r.d[3])) ||
           !on30_put(c,r.a[6],0x9a,1,2) || !on30_put(c,r.a[6],0x9b,1,0) || !on30_put(c,r.a[6],0x8e,1,5))return false;
        r.a[0]=0x41fe6;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x33b8c);
    case 0x33b8c:return on30_carry(c,0x33bba,0x33b90);                  // BCC.W 33bba (C returned by 28ae).
    // LEA 8a(A6),A1; MOVE.L A1,76(A0); MOVE.B #1,7a(A0); MOVE.B #0,7b(A0) .. 7e(A0); ORI.B #1,CCR.
    case 0x33b90:
        r.a[1]=am_index(r.a[6],0x8a);
        if(!on30_put(c,r.a[0],0x76,4,r.a[1]) || !on30_put(c,r.a[0],0x7a,1,1) || !on30_put(c,r.a[0],0x7b,1,0) || !on30_put(c,r.a[0],0x7c,1,0) ||
           !on30_put(c,r.a[0],0x7d,1,0) || !on30_put(c,r.a[0],0x7e,1,0))return false;
        r.carry=AnimationCarrySet;r.pc=0x33bba;return true;
    case 0x33bba:r.a[0]=0x345c2;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x33bca); // MOVEA.L #345c2,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x33bca:r.a[0]=0x3471a;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x33bda); // MOVEA.L #3471a,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x33bda:return on30_carry(c,0x33b0c,0x33bde);                  // BCC.W 33b0c (C returned by 28ae).
    case 0x33bde:case 0x33c28:case 0x34614:case 0x34642:case 0x34658:case 0x346be:return am_return(c); // RTS.
    // ---- helper 33be0: MOVEQ #0,D0; 5e = 90 = 91 = 0; 7e.W = 1e; LONG 76 = 0; 95 = 2; 96 = ff; LONG 56 = 34b66; RTS.
    case 0x33be0:
        r.d[0]=0;
        if(!on30_put(c,r.a[6],0x5e,1,0) || !on30_put(c,r.a[6],0x90,1,0) || !on30_put(c,r.a[6],0x91,1,0) || !on30_put(c,r.a[6],0x7e,2,0x1e) ||
           !on30_put(c,r.a[6],0x76,4,0) || !on30_put(c,r.a[6],0x95,1,2) || !on30_put(c,r.a[6],0x96,1,0xff) || !on30_put(c,r.a[6],0x56,4,0x34b66))return false;
        return am_return(c);
    // ---- helper 33c0e: MOVE.W 7a(A6),D0; JSR 49be0.l.
    case 0x33c0e:if(!on30_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49be0,0x33c18);
    // MOVE.W (A0),D0; BTST.B #6,D0; BEQ.W 33c28.
    case 0x33c18:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.pc=((r.d[0]>>6)&1U)==0U?0x33c28:0x33c22;return true;
    case 0x33c22:if(!on30_put(c,r.a[6],0x90,1,0xf))return false;r.pc=0x33c28;return true; // MOVE.B #f,90(A6).
    // ---- helpers 33c2a / 33c54: BTST.B #7,15(A6); BEQ.W 33c3a / 33c64.
    case 0x33c2a:if(!on30_bit(c,0x15,7,bit))return false;r.pc=bit?0x33c34:0x33c3a;return true;
    case 0x33c34:r.pc=0x4bfc0;return true;                               // JMP 4bfc0.l (boundary).
    // MOVE.L 64(A6),36(A6); ADDI.L #ffffb000,3a(A6) (falls through into 33c48).
    case 0x33c3a:if(!on30_copy(c,r.a[6],0x64,0x36,4) || !on30_lift(c))return false;r.pc=0x33c48;return true;
    case 0x33c48:return am_call(c,0x4be82,0x33c4e);                     // JSR 4be82.l.
    case 0x33c4e:case 0x33c72:r.pc=0x492c8;return true;                 // JMP 492c8.l.
    case 0x33c54:if(!on30_bit(c,0x15,7,bit))return false;r.pc=bit?0x33c5e:0x33c64;return true;
    case 0x33c5e:r.pc=0x4bfb4;return true;                               // JMP 4bfb4.l (boundary).
    case 0x33c64:if(!on30_lift(c))return false;r.pc=0x33c6c;return true; // ADDI.L #ffffb000,3a(A6) (falls through into 33c6c).
    case 0x33c6c:return am_call(c,0x4be6c,0x33c72);                     // JSR 4be6c.l (boundary).
    // ---- interpreter table entry 33f4c (LONG 4a5b4): MOVEA.L (A0),A0; MOVE.W (A0),8a(A6); MOVE.W (A0),88(A6); RTS.
    case 0x33f4c:
        if(!am_read(c,r.a[0],4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0],2,value) || !on30_put(c,r.a[6],0x8a,2,value) || !am_read(c,r.a[0],2,value) || !on30_put(c,r.a[6],0x88,2,value))return false;
        return am_return(c);
    // ---- 28ae child callback 345c2 (33bba): id 102, JSR 8ebe.l (f, 0).
    case 0x345c2:if(!on30_record(c))return false;am_word(r.d[0],0xf);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x345de);
    case 0x345de:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x345e8);   // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0x345e8:if(!on30_put(c,r.a[6],0x9a,1,2))return false;r.pc=0x34644;return true; // MOVE.B #2,9a(A6); BRA.W 34644.
    // ---- LONG table 34708 targets 345f2 (k = 0) / 34616 (k = 1): animation 354f2 / 35650, install 34608 / 3462c.
    case 0x345f2:return on30_animation(c,0x354f2,0x34602);
    case 0x34602:if(!on30_install(c,0x34608))return false;r.pc=0x34608;return true; // MOVE.L #34608,(A6).
    case 0x34608:r.a[1]=0x34610;r.pc=0x346c6;return true;               // LEA 34610(PC),A1; BRA.W 346c6.
    case 0x34610:return am_call(c,0x3465a,0x34614);                     // JSR 3465a(PC).
    case 0x34616:return on30_animation(c,0x35650,0x34626);
    case 0x34626:if(!on30_install(c,0x3462c))return false;r.pc=0x3462c;return true; // MOVE.L #3462c,(A6).
    case 0x3462c:r.a[1]=0x34634;r.pc=0x346c6;return true;               // LEA 34634(PC),A1; BRA.W 346c6.
    case 0x34634:return am_call(c,0x3465a,0x34638);                     // JSR 3465a(PC).
    case 0x34638:return on30_carry(c,0x34642,0x3463c);                  // BCC.W 34642 (C returned by 3465a = 49fc6).
    case 0x3463c:if(!on30_install(c,0x34644))return false;r.pc=0x34642;return true; // MOVE.L #34644,(A6).
    // ---- 34644 (k = 2, 345e8 BRA.W, install 3463c): MOVE.B #2,9a(A6); MOVE.L #34650,(A6) (falls through into 34650).
    case 0x34644:if(!on30_put(c,r.a[6],0x9a,1,2) || !on30_install(c,0x34650))return false;r.pc=0x34650;return true;
    case 0x34650:r.a[1]=0x34658;r.pc=0x346c6;return true;               // LEA 34658(PC),A1; BRA.W 346c6.
    // ---- helper 3465a: MOVEA.L c(A6),A0; MOVE.W 1e(A0),1e(A6); MOVE.B 88(A0),D0; MOVE.B 89(A0),D1; EXT.W D0; EXT.W D1;
    // MOVE.W D0,2e(A6); MOVE.W D1,32(A6); JSR 43e34.l.
    case 0x3465a:
        if(!on30_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!on30_copy(c,r.a[0],0x1e,0x1e,2) || !on30_get(c,r.a[0],0x88,1,value) || !on30_get(c,r.a[0],0x89,1,other))return false;
        am_byte(r.d[0],value);am_byte(r.d[1],other);am_word(r.d[0],on30_ext(r.d[0]));am_word(r.d[1],on30_ext(r.d[1]));
        if(!on30_put(c,r.a[6],0x2e,2,on30_w(r.d[0])) || !on30_put(c,r.a[6],0x32,2,on30_w(r.d[1])))return false;return am_call(c,0x43e34,0x3467e);
    // MOVEA.L c(A6),A0; MOVE.B 84(A0),8f(A6); MOVE.B 85(A0),D0; ANDI.W #ff,D0; MOVE.B 346c0(PC,D0.W),D0; EXT.W D0; MOVE.W D0,-(A7);
    // ADD.W D0,46(A6); JSR 49fc6.l.
    case 0x3467e:
        if(!on30_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!on30_copy(c,r.a[0],0x84,0x8f,1) || !on30_get(c,r.a[0],0x85,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]&255U);
        if(!am_read(c,am_index(ON30_OFFSETS,r.d[0]),1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],on30_ext(r.d[0]));
        if(!am_push(c,2,on30_w(r.d[0])) || !on30_get(c,r.a[6],0x46,2,value) || !on30_put(c,r.a[6],0x46,2,(value+r.d[0])&65535U))return false;
        return am_call(c,0x49fc6,0x346a2);
    case 0x346a2:return am_call(c,0x43e34,0x346a8);                     // JSR 43e34.l.
    // MOVE.W (A7)+,D0; NEG.W D0; ADD.W D0,46(A6); ADDQ.W #6,42(A6); SUBQ.W #1,1e(A6); JSR 49fc6.l.
    case 0x346a8:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],(65536U-on30_w(r.d[0]))&65535U);
        if(!on30_get(c,r.a[6],0x46,2,value) || !on30_put(c,r.a[6],0x46,2,(value+r.d[0])&65535U) ||
           !on30_get(c,r.a[6],0x42,2,value) || !on30_put(c,r.a[6],0x42,2,(value+6U)&65535U) ||
           !on30_get(c,r.a[6],0x1e,2,value) || !on30_put(c,r.a[6],0x1e,2,(value+65535U)&65535U))return false;
        return am_call(c,0x49fc6,0x346be);
    // ---- selectors 346c6 / 34874: JSR 288c.l; BCC.W 34714 / 3489c (C returned by 288c; A0 = the parent).
    case 0x346c6:return am_call(c,0x288c,0x346cc);
    case 0x346cc:return on30_carry(c,0x34714,0x346d0);
    // MOVE.B 9a(A0),D0; MOVE.B 9a(A6),D7; ADD.B D7,D7 (twice); ADD.B D0,D7; ANDI.W #ff,D7; MOVE.B 346fc(PC,D7.W),D7; BEQ.W 346fa.
    case 0x346d0:
        if(!on30_get(c,r.a[0],0x9a,1,value))return false;am_byte(r.d[0],value);if(!on30_get(c,r.a[6],0x9a,1,value))return false;am_byte(r.d[7],value);
        am_byte(r.d[7],r.d[7]*4U);am_byte(r.d[7],r.d[7]+on30_b(r.d[0]));am_word(r.d[7],r.d[7]&255U);
        if(!am_read(c,am_index(ON30_MATRIX,r.d[7]),1,value))return false;am_byte(r.d[7],value);r.pc=on30_b(value)==0U?0x346fa:0x346ea;return true;
    // MOVE.B D0,9a(A6); ANDI.W #ff,D0; ADD.W D0,D0 (twice); MOVEA.L 34708(PC,D0.W),A1 (falls through into 346fa).
    case 0x346ea:if(!on30_put(c,r.a[6],0x9a,1,on30_b(r.d[0])) || !on30_target(c,ON30_TARGETS))return false;r.pc=0x346fa;return true;
    case 0x346fa:case 0x3489a:r.pc=r.a[1];return true;                  // JMP (A1) (live target).
    // ---- 28ae child callback 3471a (33bca): id 102; MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0x3471a:if(!on30_record(c))return false;r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x34732);
    // MOVE.W #ffff,7c(A6); MOVE.B #ff,9b(A6); BRA.W 34742.
    case 0x34732:if(!on30_put(c,r.a[6],0x7c,2,0xffff) || !on30_put(c,r.a[6],0x9b,1,0xff))return false;r.pc=0x34742;return true;
    case 0x34742:if(!on30_install(c,0x34748))return false;r.pc=0x34748;return true; // MOVE.L #34748,(A6).
    case 0x34748:r.a[1]=0x34750;r.pc=0x34874;return true;               // LEA 34750(PC),A1; BRA.W 34874.
    case 0x34874:return am_call(c,0x288c,0x3487a);
    case 0x3487a:return on30_carry(c,0x3489c,0x3487e);
    // MOVE.B 9b(A0),D0; CMP.B 9b(A6),D0; BEQ.W 3489a.
    case 0x3487e:
        if(!on30_get(c,r.a[0],0x9b,1,value))return false;am_byte(r.d[0],value);if(!on30_get(c,r.a[6],0x9b,1,other))return false;
        r.pc=on30_b(r.d[0])==on30_b(other)?0x3489a:0x3488a;return true;
    // MOVE.B D0,9b(A6); ANDI.W #ff,D0; ADD.W D0,D0 (twice); MOVEA.L 348a2(PC,D0.W),A1 (falls through into 3489a).
    case 0x3488a:if(!on30_put(c,r.a[6],0x9b,1,on30_b(r.d[0])) || !on30_target(c,ON30_STATES))return false;r.pc=0x3489a;return true;
    default:return am_error(c,"unsupported animation objects n30 PC");
    }
}
}
