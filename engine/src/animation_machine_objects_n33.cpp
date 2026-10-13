#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t on33_b(std::uint32_t value) {return value&255U;}
std::uint32_t on33_w(std::uint32_t value) {return value&65535U;}
// N of a 32-bit CMP.L / TST.L result (BMI / BPL read only N).
bool on33_minus(std::uint32_t value) {return (value&0x80000000U)!=0U;}
bool on33_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on33_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BTST.B #bit,d16(An): true when the bit is 1.
bool on33_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on33_get(c,base,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,d16(A6) (read, then write the changed BYTE).
bool on33_change(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool on) {
    std::uint32_t value=0;if(!on33_get(c,c.s.a[6],displacement,1,value))return false;
    value=on?(value|(1U<<bit)):(value&~(1U<<bit));return on33_put(c,c.s.a[6],displacement,1,value&255U);
}
// ORI.B #mask,d16(An) / ANDI.B #mask,d16(An) (read, then write the BYTE).
bool on33_or(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t mask) {
    std::uint32_t value=0;return on33_get(c,base,displacement,1,value) && on33_put(c,base,displacement,1,(value|mask)&255U);
}
bool on33_and(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t mask) {
    std::uint32_t value=0;return on33_get(c,base,displacement,1,value) && on33_put(c,base,displacement,1,value&mask&255U);
}
// MOVE.B from(An),to(An) (same base).
bool on33_copy(AnimationMachineContext& c,std::uint32_t base,std::uint32_t from,std::uint32_t to) {
    std::uint32_t value=0;return on33_get(c,base,from,1,value) && on33_put(c,base,to,1,value);
}
// TST.x d16(A6): true when the value is zero.
bool on33_zero(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,bool& zero) {
    std::uint32_t value=0;if(!on33_get(c,c.s.a[6],displacement,size,value))return false;zero=value==0U;return true;
}
// LONG d16(An) read used as an operand of ADD.L / SUB.L.
bool on33_long(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t& value) {
    return on33_get(c,base,displacement,4,value);
}
// MOVE.L #value,(A6) (installed callback LONG).
bool on33_install(AnimationMachineContext& c,std::uint32_t value) {return on33_put(c,c.s.a[6],0,4,value);}
// Bcc / Scc on a C returned by a callee: clear -> clear_pc, set -> set_pc.
bool on33_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n33 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// SCS.B -(A7): the BYTE ff (C set) or 00 (C clear) at A7 - 2.
bool on33_push_carry(AnimationMachineContext& c) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n33 caller requires known carry");
    return am_push(c,1,c.s.carry==AnimationCarrySet?0xffU:0U);
}
// MOVE.W #122,20(A6); MOVE.L 2000b4.l,22(A6) (banked LONG through the live bus).
bool on33_banked(AnimationMachineContext& c) {
    std::uint32_t value=0;
    return on33_put(c,c.s.a[6],0x20,2,0x122) && am_read(c,0x2000b4U,4,value) && on33_put(c,c.s.a[6],0x22,4,value);
}
// SWAP Dn; op.W; SWAP Dn: add (or subtract) a WORD to the high WORD of a register.
std::uint32_t on33_high_add(std::uint32_t r,std::uint32_t word) {return ((((r>>16)+word)&65535U)<<16)|(r&65535U);}
std::uint32_t on33_high_sub(std::uint32_t r,std::uint32_t word) {return ((((r>>16)+65536U-(word&65535U))&65535U)<<16)|(r&65535U);}
// MOVE.L d0-d3/a0 from 2e(A6) (MOVEM.L 2e(A6),D0-D3/A0, read in register order).
bool on33_restore(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t v[5]={0,0,0,0,0};
    for(unsigned int i=0;i<5;++i)if(!on33_long(c,r.a[6],0x2eU+4U*i,v[i]))return false;
    r.d[0]=v[0];r.d[1]=v[1];r.d[2]=v[2];r.d[3]=v[3];r.a[0]=v[4];return true;
}
// MOVE.W 4(A2)/8(A2)/... sized helpers of the 4b8e8 overlap test.
bool on33_word(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t& value) {
    return on33_get(c,base,displacement,2,value);
}
// d -= L a(A3); d += L b(A3) (SUB.L then ADD.L, in that order).
bool on33_swap_rect(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t sub,std::uint32_t add) {
    std::uint32_t x=0,y=0;if(!on33_long(c,c.s.a[3],sub,x))return false;d-=x;if(!on33_long(c,c.s.a[3],add,y))return false;d+=y;return true;
}
// SUB.L 1c(A0),Dn; ADD.L 14(A0),Dn.
bool on33_frame_x(AnimationMachineContext& c,std::uint32_t& d) {
    std::uint32_t x=0,y=0;if(!on33_long(c,c.s.a[0],0x1c,x))return false;d-=x;if(!on33_long(c,c.s.a[0],0x14,y))return false;d+=y;return true;
}
}
// Objects F4 N33 (201 block starts): 3b542 (N31 38ba0) with the 28ae child callback 3b118 (installs 3b166), the 28ae child callback
// 3b1ae (N32b 39c80; installs 3b202), the installed callback 3a1e0 (installs 3a242; 3a24c), the helpers 3a5d2 3b22a 3b26a 3b282
// 3b288 3b2a0 3b2a6 3b2b8 3b2ee 3b302 3b334 3b398 3b3b4, the C producer 482aa, the overlap test 4b8e8 / 4b8e4, the input test 4bce0
// and the fragments 46bfc 4be50 4be6c 4bfb4 4c0ea 4c37c / 4c7a4. Boundaries without an executor: 19a00 3a4a4 3a4be 3a5be 3b424
// 4bfc0 4d8d8 4ff96 8d34 d3d7c. 4bdfe leaves through BRA.W 4bc58 (inside the u08b block 4bc44; contract decision 5). The 8
// consumers read a known C returned by 288c / 49fc6 / 49fca / 28ae / 482aa. One banked LONG read (2000b4); no port, no X / DIV.
bool animation_objects_n33_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool bit=false;
    switch(r.pc) {
    case 0x3b178:case 0x3b1a6:case 0x3b228:case 0x3b268:case 0x3b332:case 0x3b5a4:return am_return(c); // RTS.
    case 0x3a2ee:case 0x3b1a8:case 0x3b20c:case 0x3b222:r.pc=0x2a00;return true; // JMP 2a00.l.
    // ---- installed callback 3a1e0: MOVEA.L 82(A6),A0; JSR 3a5be(PC) (boundary).
    case 0x3a1e0:if(!on33_long(c,r.a[6],0x82,value))return false;r.a[0]=value;return am_call(c,0x3a5be,0x3a1e8);
    // CLR.L 64(A6); MOVE.B #ff,8a(A6); JSR 4d8d8.l (boundary).
    case 0x3a1e8:if(!on33_put(c,r.a[6],0x64,4,0) || !on33_put(c,r.a[6],0x8a,1,0xff))return false;return am_call(c,0x4d8d8,0x3a1f8);
    case 0x3a1f8:r.pc=(r.d[0]&0x80U)!=0U?0x3a21e:0x3a1fe;return true;  // TST.B D0; BMI.W 3a21e.
    case 0x3a1fe:return am_call(c,0x3b424,0x3a202);                     // JSR 3b424(PC) (boundary).
    case 0x3a202:r.pc=((r.d[0]>>5)&1U)!=0U?0x3a20a:0x3a212;return true; // BTST.B #5,D0; BEQ.W 3a212.
    case 0x3a20a:am_byte(r.d[1],1);return am_call(c,0x3a4be,0x3a212);   // MOVE.B #1,D1; JSR 3a4be(PC) (boundary).
    case 0x3a212:return am_call(c,0x3a4a4,0x3a216);                     // JSR 3a4a4(PC) (boundary).
    case 0x3a216:return am_call(c,0x3b288,0x3a21a);                     // JSR 3b288(PC).
    case 0x3a21a:r.pc=0x3a222;return true;                               // BRA.W 3a222.
    case 0x3a21e:return am_call(c,0x3b26a,0x3a222);                     // JSR 3b26a(PC).
    case 0x3a222:return am_call(c,0x3b334,0x3a226);                     // JSR 3b334(PC).
    case 0x3a226:if(!on33_get(c,r.a[6],0xa7,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x3a238:0x3a22e;return true; // MOVE.B a7(A6),D0; BEQ.W.
    // SUBQ.B #1,D0; MOVE.B D0,a7(A6); BRA.W 3a23e.
    case 0x3a22e:am_byte(r.d[0],(r.d[0]+255U)&255U);if(!on33_put(c,r.a[6],0xa7,1,on33_b(r.d[0])))return false;r.pc=0x3a23e;return true;
    case 0x3a238:if(!on33_install(c,0x3a242))return false;r.pc=0x3a23e;return true; // MOVE.L #3a242,(A6).
    case 0x3a23e:r.pc=0x3a41c;return true;                               // BRA.W 3a41c (N31).
    case 0x3a242:r.a[0]=0x3b846;return am_call(c,0x4ae4a,0x3a24c);      // LEA 3b846(PC),A0; JSR 4ae4a.l.
    case 0x3a24c:am_byte(r.d[1],0);return am_call(c,0x3a4be,0x3a254);   // MOVE.B #0,D1; JSR 3a4be(PC) (boundary).
    case 0x3a254:r.d[0]=1;r.d[1]=0;return am_call(c,0x4ff96,0x3a25e);   // MOVEQ #1,D0; MOVEQ #0,D1; JSR 4ff96.l (boundary).
    case 0x3a25e:return am_call(c,0x49274,0x3a264);                     // JSR 49274.l.
    case 0x3a264:return am_call(c,0xd3d7c,0x3a26a);                     // JSR d3d7c.l (boundary).
    // MOVE.L #x,36(A0); MOVE.L #y,3a(A0); MOVE.W #n,54(A0); JSR d3d7c.l (boundary) - three rows.
    case 0x3a26a:
        if(!on33_put(c,r.a[0],0x36,4,0xfff20000U) || !on33_put(c,r.a[0],0x3a,4,0x280000U) || !on33_put(c,r.a[0],0x54,2,0xa))return false;
        return am_call(c,0xd3d7c,0x3a286);
    case 0x3a286:
        if(!on33_put(c,r.a[0],0x36,4,0xa0000U) || !on33_put(c,r.a[0],0x3a,4,0xfff00000U) || !on33_put(c,r.a[0],0x54,2,7))return false;
        return am_call(c,0xd3d7c,0x3a2a2);
    case 0x3a2a2:
        if(!on33_put(c,r.a[0],0x36,4,0x90000U) || !on33_put(c,r.a[0],0x3a,4,0x250000U) || !on33_put(c,r.a[0],0x54,2,7))return false;
        return am_call(c,0xd3d7c,0x3a2be);
    // Last row, then MOVEA.L #3a2fa,A0; MOVE.W #1e,D0; JSR 28ae.l (child 3a2fa, N31).
    case 0x3a2be:
        if(!on33_put(c,r.a[0],0x36,4,0xfff90000U) || !on33_put(c,r.a[0],0x3a,4,0xfffc0000U) || !on33_put(c,r.a[0],0x54,2,5))return false;
        r.a[0]=0x3a2fa;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0x3a2e4);
    case 0x3a2e4:r.d[0]=0;r.d[1]=8;return am_call(c,0x49214,0x3a2ee);  // MOVEQ #0,D0; MOVEQ #8,D1; JSR 49214.l.
    // ---- 3a5d2: MOVE.L #3a60a,82(A6); MOVE.B #ff,96(A6); MOVE.B #ff,95(A6); MOVE.B #0,99(A6); MOVE.B #0,9a(A6); MOVEA.L #0,A1;
    // JSR 3b398(PC).
    case 0x3a5d2:
        if(!on33_put(c,r.a[6],0x82,4,0x3a60a) || !on33_put(c,r.a[6],0x96,1,0xff) || !on33_put(c,r.a[6],0x95,1,0xff) ||
            !on33_put(c,r.a[6],0x99,1,0) || !on33_put(c,r.a[6],0x9a,1,0))return false;
        r.a[1]=0;return am_call(c,0x3b398,0x3a5fc);
    // ANDI.B #ef,9d(A6); ANDI.B #ef,9e(A6); RTS.
    case 0x3a5fc:if(!on33_and(c,r.a[6],0x9d,0xef) || !on33_and(c,r.a[6],0x9e,0xef))return false;return am_return(c);
    // ---- 28ae child callback 3b118: MOVE.W #122,20(A6); MOVE.L 2000b4.l,22(A6); BSET.B #6,15(A6); MOVE.W #0,68(A6);
    // MOVE.W #0,1e(A6); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0x3b118:
        if(!on33_banked(c) || !on33_change(c,0x15,6,true) || !on33_put(c,r.a[6],0x68,2,0) || !on33_put(c,r.a[6],0x1e,2,0))return false;
        r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x3b142);
    case 0x3b142:am_word(r.d[0],0x1e1);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3b150); // MOVE.W #1e1,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x3b150:r.a[1]=0x3ceb8;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3b160); // MOVEA.L #3ceb8,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3b160:if(!on33_install(c,0x3b166))return false;r.pc=0x3b166;return true; // MOVE.L #3b166,(A6).
    case 0x3b166:case 0x3b202:return am_call(c,0x288c,r.pc+6U);         // JSR 288c.l (parent check).
    case 0x3b16c:return on33_carry(c,0x3b1a8,0x3b170);                  // BCC.W 3b1a8 (C returned by 288c).
    case 0x3b170:if(!on33_get(c,r.a[0],0xa4,1,value))return false;r.pc=value!=0U?0x3b17a:0x3b178;return true; // TST.B a4(A0); BNE.W.
    case 0x3b17a:return am_call(c,0x491c4,0x3b180);                     // JSR 491c4.l.
    // MOVE.W 1e(A0),1e(A6); SUBQ.W #1,1e(A6); MOVE.B a2(A0),a2(A6); CMPI.B #10,a2(A6); BCC.W 3b1a6.
    case 0x3b180:
        if(!on33_get(c,r.a[0],0x1e,2,value) || !on33_put(c,r.a[6],0x1e,2,value) || !on33_get(c,r.a[6],0x1e,2,value) ||
            !on33_put(c,r.a[6],0x1e,2,(value+65535U)&65535U) || !on33_get(c,r.a[0],0xa2,1,value) || !on33_put(c,r.a[6],0xa2,1,value) ||
            !on33_get(c,r.a[6],0xa2,1,value))return false;
        r.pc=value>=0x10U?0x3b1a6:0x3b19a;return true;
    case 0x3b19a:case 0x3b212:return am_call(c,0x43e34,r.pc+6U);        // JSR 43e34.l.
    case 0x3b1a0:case 0x3b218:return am_call(c,0x49fc6,r.pc+6U);        // JSR 49fc6.l.
    // ---- 28ae child callback 3b1ae: MOVE.W #122,20(A6); MOVE.L 2000b4.l,22(A6); MOVE.W #1a4b,D0; JSR 3af8.l.
    case 0x3b1ae:if(!on33_banked(c))return false;am_word(r.d[0],0x1a4b);return am_call(c,0x3af8,0x3b1c6);
    // BSET.B #6,15(A6); MOVE.W #e000,68(A6); MOVE.W #e000,1e(A6); MOVEA.L #3ce70,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3b1c6:
        if(!on33_change(c,0x15,6,true) || !on33_put(c,r.a[6],0x68,2,0xe000) || !on33_put(c,r.a[6],0x1e,2,0xe000))return false;
        r.a[1]=0x3ce70;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3b1e8);
    case 0x3b1e8:am_word(r.d[0],0x8cd);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3b1f6); // MOVE.W #8cd,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x3b1f6:return am_call(c,0x49274,0x3b1fc);                     // JSR 49274.l.
    case 0x3b1fc:if(!on33_install(c,0x3b202))return false;r.pc=0x3b202;return true; // MOVE.L #3b202,(A6).
    case 0x3b208:return on33_carry(c,0x3b20c,0x3b212);                  // BCS.W 3b212 (C returned by 288c).
    case 0x3b21e:return on33_carry(c,0x3b228,0x3b222);                  // BCC.W 3b228 (C returned by 49fc6).
    // ---- 3b22a: JSR 8ff4.l; MOVE.W #8ce,D0 / #db2,D0 (three times); MOVE.B #1,D1; JSR 8ebe.l; RTS.
    case 0x3b22a:return am_call(c,0x8ff4,0x3b230);
    case 0x3b230:am_word(r.d[0],0x8ce);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x3b23e);
    case 0x3b23e:case 0x3b24c:case 0x3b25a:am_word(r.d[0],0xdb2);am_byte(r.d[1],1);return am_call(c,0x8ebe,r.pc+14U);
    // ---- 3b26a / 3b288: BTST.B #7,15(A6); BEQ.W (+ ADDI.L #ffff6000,3a(A6)); JMP 4bfb4 / 4be6c / 4bfc0 (boundary) / 4be82.
    case 0x3b26a:case 0x3b288:
        if(!on33_bit(c,r.a[6],0x15,7,bit))return false;r.pc=bit?(r.pc==0x3b26aU?0x3b274U:0x3b292U):(r.pc==0x3b26aU?0x3b27aU:0x3b298U);return true;
    case 0x3b274:r.pc=0x4bfb4;return true;                               // JMP 4bfb4.l.
    case 0x3b27a:case 0x3b298:
        if(!on33_long(c,r.a[6],0x3a,value) || !on33_put(c,r.a[6],0x3a,4,value+0xffff6000U))return false;r.pc+=8U;return true;
    case 0x3b282:r.pc=0x4be6c;return true;                               // JMP 4be6c.l.
    case 0x3b292:r.pc=0x4bfc0;return true;                               // JMP 4bfc0.l (boundary).
    case 0x3b2a0:r.pc=0x4be82;return true;                               // JMP 4be82.l (u08b).
    // ---- 3b2a6: MOVE.L 64(A6),-(A7); CLR.L 64(A6); JSR 3b288(PC) / MOVE.L (A7)+,64(A6); RTS.
    case 0x3b2a6:
        if(!on33_long(c,r.a[6],0x64,value) || !am_push(c,4,value) || !on33_put(c,r.a[6],0x64,4,0))return false;return am_call(c,0x3b288,0x3b2b2);
    case 0x3b2b2:if(!am_pop(c,4,value) || !on33_put(c,r.a[6],0x64,4,value))return false;return am_return(c);
    // ---- 3b2b8: MOVEA.L 7e(A6),A0; MOVE.W (A0)+,D1; BPL.W 3b2e0.
    case 0x3b2b8:
        if(!on33_long(c,r.a[6],0x7e,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[1],value);
        r.pc=(value&0x8000U)!=0U?0x3b2c2:0x3b2e0;return true;
    // NEG.W D1; CMPI.W #4,D1; BCC.W 3b2dc (unsigned).
    case 0x3b2c2:am_word(r.d[1],(65536U-on33_w(r.d[1]))&65535U);r.pc=on33_w(r.d[1])>=4U?0x3b2dc:0x3b2cc;return true;
    // MOVE.B 19(A6,D1.W),14(A6); MOVE.L A0,7e(A6); RTS.
    case 0x3b2cc:
        if(!am_read(c,am_index(r.a[6]+0x19U,r.d[1]),1,value) || !on33_put(c,r.a[6],0x14,1,value) || !on33_put(c,r.a[6],0x7e,4,r.a[0]))return false;
        return am_return(c);
    // ADDA.W (A0),A0; MOVE.W (A0)+,D1.
    case 0x3b2dc:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]=am_index(r.a[0],value);if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;
        am_word(r.d[1],value);r.pc=0x3b2e0;return true;
    // MOVE.L A0,7e(A6); MOVE.B 14(A6),D0; JMP 8d34.l (boundary).
    case 0x3b2e0:
        if(!on33_put(c,r.a[6],0x7e,4,r.a[0]) || !on33_get(c,r.a[6],0x14,1,value))return false;am_byte(r.d[0],value);r.pc=0x8d34;return true;
    // ---- 3b2ee: ANDI.W #fffe,D0; MOVE.W 8a(A6),D1; ANDI.W #1,D1; OR.W D1,D0; MOVE.W D0,8a(A6); RTS.
    case 0x3b2ee:
        am_word(r.d[0],r.d[0]&0xfffeU);if(!on33_get(c,r.a[6],0x8a,2,value))return false;am_word(r.d[1],value&1U);
        am_word(r.d[0],(r.d[0]|on33_w(r.d[1]))&65535U);if(!on33_put(c,r.a[6],0x8a,2,on33_w(r.d[0])))return false;return am_return(c);
    // ---- 3b302: BCLR.B #4,94(A6); MOVE.B (A0)+,D0; BEQ.W 3b314 / BSET.B #4,94(A6) / BCLR.B #1,94(A6); MOVE.B (A0)+,D0; BEQ.W 3b326.
    case 0x3b302:case 0x3b314:
        if(!on33_change(c,0x94,r.pc==0x3b302U?4U:1U,false) || !am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;am_byte(r.d[0],value);
        r.pc=value==0U?(r.pc==0x3b302U?0x3b314U:0x3b326U):(r.pc==0x3b302U?0x3b30eU:0x3b320U);return true;
    case 0x3b30e:if(!on33_change(c,0x94,4,true))return false;r.pc=0x3b314;return true; // BSET.B #4,94(A6).
    case 0x3b320:if(!on33_change(c,0x94,1,true))return false;r.pc=0x3b326;return true; // BSET.B #1,94(A6).
    // MOVEA.L (A0),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3b326:if(!am_read(c,r.a[0],4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3b332);
    // ---- 3b334: TST.L 56(A6); BEQ.W 3b35a / CMPI.B #8,9f(A6); BCC.W 3b350 / MOVE.L #3b864|#3b882,D0 / MOVE.L D0,56(A6).
    case 0x3b334:if(!on33_zero(c,0x56,4,bit))return false;r.pc=bit?0x3b35a:0x3b33c;return true;
    case 0x3b33c:if(!on33_get(c,r.a[6],0x9f,1,value))return false;r.pc=value>=8U?0x3b350:0x3b346;return true;
    case 0x3b346:r.d[0]=0x3b864;r.pc=0x3b356;return true;
    case 0x3b350:r.d[0]=0x3b882;r.pc=0x3b356;return true;
    case 0x3b356:if(!on33_put(c,r.a[6],0x56,4,r.d[0]))return false;r.pc=0x3b35a;return true;
    // TST.L 36(A6); SNE.B b1(A6); MOVE.W 1e(A6),D0; JSR ce02.l.
    case 0x3b35a:
        if(!on33_long(c,r.a[6],0x36,value) || !on33_put(c,r.a[6],0xb1,1,value!=0U?0xffU:0U) || !on33_get(c,r.a[6],0x1e,2,value))return false;
        am_word(r.d[0],value);return am_call(c,0xce02,0x3b36c);
    case 0x3b36c:if(!on33_bit(c,r.a[6],0x94,1,bit))return false;r.pc=bit?0x3b386:0x3b376;return true; // BTST.B #1,94(A6); BNE.W.
    case 0x3b376:return am_call(c,0x3b3b4,0x3b37a);                     // JSR 3b3b4(PC).
    case 0x3b37a:case 0x3b386:return am_call(c,0x49fc6,r.pc+6U);        // JSR 49fc6.l.
    case 0x3b380:if(!on33_push_carry(c))return false;r.pc=0x3b392;return true; // SCS.B -(A7) (C of 49fc6); BRA.W 3b392.
    case 0x3b38c:if(!on33_push_carry(c))return false;return am_call(c,0x3b3b4,0x3b392); // SCS.B -(A7); JSR 3b3b4(PC).
    // MOVE.B (A7)+,D0; LSR.B #1,D0; RTS (C = bit 0 of the popped BYTE).
    case 0x3b392:
        if(!am_pop(c,1,value))return false;am_byte(r.d[0],(value&255U)>>1);r.carry=(value&1U)!=0U?AnimationCarrySet:AnimationCarryClear;
        return am_return(c);
    // ---- 3b398: CLR.B a9(A6); CLR.B aa(A6); BCLR.B #0,94(A6); LEA 8c(A6),A0; MOVE.W #100,D0; JMP 49f96.l.
    case 0x3b398:
        if(!on33_put(c,r.a[6],0xa9,1,0) || !on33_put(c,r.a[6],0xaa,1,0) || !on33_change(c,0x94,0,false))return false;
        r.a[0]=am_index(r.a[6],0x8c);am_word(r.d[0],0x100);r.pc=0x49f96;return true;
    // ---- 3b3b4: MOVE.W 1e(A6),-(A7); MOVE.B 14(A6),-(A7); MOVE.B a9(A6),D1; EXT.W D1; ADD.W D1,42(A6); CLR.B a9(A6);
    // MOVE.B aa(A6),D1; EXT.W D1; ADD.W D1,46(A6); CLR.B aa(A6); MOVE.B 14(A6),D0; CMP.B 1b(A6),D0; BNE.W 3b3ea.
    case 0x3b3b4:
        if(!on33_get(c,r.a[6],0x1e,2,value) || !am_push(c,2,value) || !on33_get(c,r.a[6],0x14,1,value) || !am_push(c,1,value))return false;
        if(!on33_get(c,r.a[6],0xa9,1,value))return false;am_word(r.d[1],(value&0x80U)!=0U?(value|0xff00U):value);
        if(!on33_get(c,r.a[6],0x42,2,value) || !on33_put(c,r.a[6],0x42,2,(value+r.d[1])&65535U) || !on33_put(c,r.a[6],0xa9,1,0))return false;
        if(!on33_get(c,r.a[6],0xaa,1,value))return false;am_word(r.d[1],(value&0x80U)!=0U?(value|0xff00U):value);
        if(!on33_get(c,r.a[6],0x46,2,value) || !on33_put(c,r.a[6],0x46,2,(value+r.d[1])&65535U) || !on33_put(c,r.a[6],0xaa,1,0))return false;
        if(!on33_get(c,r.a[6],0x14,1,value))return false;am_byte(r.d[0],value);if(!on33_get(c,r.a[6],0x1b,1,other))return false;
        r.pc=on33_b(r.d[0])!=on33_b(other)?0x3b3ea:0x3b3e4;return true;
    case 0x3b3e4:if(!on33_copy(c,r.a[6],0x1c,0x14))return false;r.pc=0x3b3ea;return true; // MOVE.B 1c(A6),14(A6).
    // MOVE.W #1,1e(A6); BCLR.B #0,94(A6); LEA 8c(A6),A0; JSR 49fca.l.
    case 0x3b3ea:
        if(!on33_put(c,r.a[6],0x1e,2,1) || !on33_change(c,0x94,0,false))return false;r.a[0]=am_index(r.a[6],0x8c);return am_call(c,0x49fca,0x3b400);
    case 0x3b400:return on33_carry(c,0x3b40a,0x3b404);                  // BCC.W 3b40a (C returned by 49fca).
    case 0x3b404:if(!on33_change(c,0x94,0,true))return false;r.pc=0x3b40a;return true; // BSET.B #0,94(A6).
    case 0x3b40a:return am_call(c,0x43e34,0x3b410);                     // JSR 43e34.l.
    // MOVE.B (A7)+,14(A6); MOVE.W (A7)+,1e(A6); BTST.B #0,94(A6); SNE.B D0; LSR.B #1,D0; RTS (C = BYTE 94 bit 0).
    case 0x3b410:
        if(!am_pop(c,1,value) || !on33_put(c,r.a[6],0x14,1,value) || !am_pop(c,2,value) || !on33_put(c,r.a[6],0x1e,2,value) ||
            !on33_bit(c,r.a[6],0x94,0,bit))return false;
        am_byte(r.d[0],bit?0x7fU:0U);r.carry=bit?AnimationCarrySet:AnimationCarryClear;return am_return(c);
    // ---- 3b542: MOVE.W #122,20(A6); MOVE.L 2000b4.l,22(A6); CMPI.B #1,79(A6); BNE.W 3b560.
    case 0x3b542:if(!on33_banked(c) || !on33_get(c,r.a[6],0x79,1,value))return false;r.pc=value==1U?0x3b55a:0x3b560;return true;
    case 0x3b55a:if(!on33_change(c,0x15,0,true))return false;r.pc=0x3b560;return true; // BSET.B #0,15(A6).
    case 0x3b560:return am_call(c,0x3b22a,0x3b564);                     // JSR 3b22a(PC).
    // MOVE.B 1b(A6),14(A6); BSET.B #6,15(A6); MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); MOVEQ #11,D1; JSR 4d81c.l.
    case 0x3b564:
        if(!on33_copy(c,r.a[6],0x1b,0x14) || !on33_change(c,0x15,6,true) || !on33_put(c,r.a[6],0x68,2,0x8810) || !on33_put(c,r.a[6],0x1e,2,0x8810))
            return false;
        r.d[1]=0x11;return am_call(c,0x4d81c,0x3b584);
    // MOVE.B D1,ad(A6); MOVE.B D2,ae(A6); MOVE.W D3,54(A6); MOVEA.L #3b118,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x3b584:
        if(!on33_put(c,r.a[6],0xad,1,on33_b(r.d[1])) || !on33_put(c,r.a[6],0xae,1,on33_b(r.d[2])) || !on33_put(c,r.a[6],0x54,2,on33_w(r.d[3])))
            return false;
        r.a[0]=0x3b118;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x3b5a0);
    case 0x3b5a0:return on33_carry(c,0x3a2f4,0x3b5a4);                  // BCC.W 3a2f4 (C returned by 28ae).
    // ---- leaf 46bfc: MOVEA.L 54c2(A5),A1; RTS.
    case 0x46bfc:if(!on33_long(c,r.a[5],0x54c2,value))return false;r.a[1]=value;return am_return(c);
    // ---- C producer 482aa: BTST.B #4,5683(A5); BEQ.W 482ba / ANDI.B #fe,CCR; RTS (Clear) / ORI.B #1,CCR; RTS (Set).
    case 0x482aa:if(!on33_bit(c,r.a[5],0x5683,4,bit))return false;r.pc=bit?0x482b4:0x482ba;return true;
    case 0x482b4:r.carry=AnimationCarryClear;return am_return(c);
    case 0x482ba:r.carry=AnimationCarrySet;return am_return(c);
    // ---- overlap test 4b8e8: MOVEQ #0,D7; RTS (4b8e4) / JSR 482aa.l / BCS.B 4b8e4 / BTST.B #7,61(A6); BNE.B 4b8e4.
    case 0x4b8e4:r.d[7]=0;return am_return(c);
    case 0x4b8e8:return am_call(c,0x482aa,0x4b8ee);
    case 0x4b8ee:return on33_carry(c,0x4b8f0,0x4b8e4);                  // BCS.B 4b8e4 (C returned by 482aa).
    case 0x4b8f0:if(!on33_bit(c,r.a[6],0x61,7,bit))return false;r.pc=bit?0x4b8e4:0x4b8f8;return true;
    case 0x4b8f8:r.d[2]+=r.d[0];r.d[3]+=r.d[1];r.pc=r.a[0]==0U?0x4b914:0x4b904;return true; // ADD.L D0,D2; ADD.L D1,D3; CMPA.W #0,A0; BEQ.W.
    // ADD.L 1c(A0),D0; ADD.L 20(A0),D1; ADD.L 14(A0),D2; ADD.L 18(A0),D3.
    case 0x4b904:
        if(!on33_long(c,r.a[0],0x1c,value))return false;r.d[0]+=value;if(!on33_long(c,r.a[0],0x20,value))return false;r.d[1]+=value;
        if(!on33_long(c,r.a[0],0x14,value))return false;r.d[2]+=value;if(!on33_long(c,r.a[0],0x18,value))return false;r.d[3]+=value;
        r.pc=0x4b914;return true;
    case 0x4b914:r.a[4]=0x10daf8;r.d[6]=0;r.d[7]=0;r.pc=0x4b91e;return true; // LEA 10daf8.l,A4; MOVEQ #0,D6; MOVEQ #0,D7.
    // MOVE.W D6,-(A7); MOVEA.L (A4)+,A3; MOVEA.L (A4)+,A2; CMPA.W #0,A2; BEQ.W 4baee.
    case 0x4b91e:
        if(!am_push(c,2,on33_w(r.d[6])) || !am_read(c,r.a[4],4,value))return false;r.a[3]=value;r.a[4]+=4U;
        if(!am_read(c,r.a[4],4,value))return false;r.a[2]=value;r.a[4]+=4U;r.pc=r.a[2]==0U?0x4baee:0x4b92c;return true;
    // MOVE.B 6d(A3),D4; ANDI.B #f,D4; CMP.B D6,D4; BNE.W 4baee.
    case 0x4b92c:if(!on33_get(c,r.a[3],0x6d,1,value))return false;am_byte(r.d[4],value&15U);r.pc=on33_b(r.d[4])!=on33_b(r.d[6])?0x4baee:0x4b93a;return true;
    // MOVEQ #0,D4; MOVE.W 4(A2),D4; MOVE.W 8(A2),D5; BTST.B #0,15(A3); BEQ.W 4b952.
    case 0x4b93a:
        r.d[4]=0;if(!on33_word(c,r.a[2],4,value))return false;am_word(r.d[4],value);if(!on33_word(c,r.a[2],8,value))return false;am_word(r.d[5],value);
        if(!on33_bit(c,r.a[3],0x15,0,bit))return false;r.pc=bit?0x4b94e:0x4b952;return true;
    case 0x4b94e:am_word(r.d[4],(r.d[4]+r.d[5])&65535U);am_word(r.d[4],(65536U-on33_w(r.d[4]))&65535U);r.pc=0x4b952;return true; // ADD.W D5,D4; NEG.W D4.
    // SWAP D4; ADD.L 42(A3),D4; CMP.L D4,D2; BMI.W 4baee.
    case 0x4b952:am_swap(r.d[4]);if(!on33_long(c,r.a[3],0x42,value))return false;r.d[4]+=value;r.pc=on33_minus(r.d[2]-r.d[4])?0x4baee:0x4b95e;return true;
    // SWAP D4; ADD.W D5,D4; SWAP D4; CMP.L D4,D2; BPL.W 4baee.
    case 0x4b95e:r.d[4]=on33_high_add(r.d[4],r.d[5]&65535U);r.pc=on33_minus(r.d[2]-r.d[4])?0x4b96a:0x4baee;return true;
    // MOVEQ #0,D5; MOVE.W 6(A2),D5; SWAP D5; ADD.L 46(A3),D5; CMP.L D5,D3; BPL.W 4b992.
    case 0x4b96a:
        r.d[5]=0;if(!on33_word(c,r.a[2],6,value))return false;am_word(r.d[5],value);am_swap(r.d[5]);if(!on33_long(c,r.a[3],0x46,value))return false;
        r.d[5]+=value;r.pc=on33_minus(r.d[3]-r.d[5])?0x4b97c:0x4b992;return true;
    // SUB.L 46(A3),D5; ADD.L 4e(A3),D5; CMP.L D5,D1; BMI.W 4baee.
    case 0x4b97c:if(!on33_swap_rect(c,r.d[5],0x46,0x4e))return false;r.pc=on33_minus(r.d[1]-r.d[5])?0x4baee:0x4b98a;return true;
    // SUB.L 4e(A3),D5; ADD.L 46(A3),D5 (-> 4b992 / 4b9b6).
    case 0x4b98a:case 0x4b9ae:if(!on33_swap_rect(c,r.d[5],0x4e,0x46))return false;r.pc=r.pc==0x4b98aU?0x4b992U:0x4b9b6U;return true;
    // SWAP D5; ADD.W a(A2),D5; SWAP D5; CMP.L D5,D3; BMI.W 4b9b6.
    case 0x4b992:if(!on33_word(c,r.a[2],0xa,value))return false;r.d[5]=on33_high_add(r.d[5],value);r.pc=on33_minus(r.d[3]-r.d[5])?0x4b9b6:0x4b9a0;return true;
    // SUB.L 46(A3),D5; ADD.L 4e(A3),D5; CMP.L D5,D1; BPL.W 4baee.
    case 0x4b9a0:if(!on33_swap_rect(c,r.d[5],0x46,0x4e))return false;r.pc=on33_minus(r.d[1]-r.d[5])?0x4b9ae:0x4baee;return true;
    // MOVE.W (A2),D6; CMPI.W #2,D6; BEQ.W 4b9fc / CMPI.W #1,D6; BEQ.W 4b9cc / BRA.W 4ba38.
    case 0x4b9b6:if(!on33_word(c,r.a[2],0,value))return false;am_word(r.d[6],value);r.pc=value==2U?0x4b9fc:0x4b9c0;return true;
    case 0x4b9c0:r.pc=on33_w(r.d[6])==1U?0x4b9cc:0x4b9c8;return true;
    case 0x4b9c8:case 0x4babc:r.pc=r.pc==0x4b9c8U?0x4ba38U:0x4baeeU;return true; // BRA.W.
    // MOVE.L D5,D6; SUB.L 46(A3),D6; ADD.L 4e(A3),D6; CMP.L D6,D1; BMI.W 4ba38 / 4ba16.
    case 0x4b9cc:case 0x4b9fc:
        r.d[6]=r.d[5];if(!on33_swap_rect(c,r.d[6],0x46,0x4e))return false;
        r.pc=on33_minus(r.d[1]-r.d[6])?(r.pc==0x4b9ccU?0x4ba38U:0x4ba16U):(r.pc==0x4b9ccU?0x4b9dcU:0x4ba0cU);return true;
    // MOVE.L D4,D6; SWAP D6; SUB.W 2(A2),D6; SWAP D6; CMP.L D6,D2; BMI.W 4b9f4.
    case 0x4b9dc:if(!on33_word(c,r.a[2],2,value))return false;r.d[6]=on33_high_sub(r.d[4],value);r.pc=on33_minus(r.d[2]-r.d[6])?0x4b9f4:0x4b9ec;return true;
    case 0x4b9ec:r.d[7]|=0x40U;r.pc=0x4baee;return true;               // ORI.B #40,D7; BRA.W 4baee.
    case 0x4b9f4:r.d[7]|=0x20U;r.pc=0x4baee;return true;               // ORI.B #20,D7; BRA.W 4baee.
    case 0x4ba0c:r.d[3]=r.d[5];r.d[7]|=0x80U;r.pc=0x4baee;return true; // MOVE.L D5,D3; ORI.B #80,D7; BRA.W 4baee.
    // SWAP D6; SUB.W a(A2),D6; SWAP D6; CMP.L D6,D1; BPL.W 4ba38.
    case 0x4ba16:if(!on33_word(c,r.a[2],0xa,value))return false;r.d[6]=on33_high_sub(r.d[6],value);r.pc=on33_minus(r.d[1]-r.d[6])?0x4ba24:0x4ba38;return true;
    // SWAP D5; SUB.W a(A2),D5; SWAP D5; SUBQ.L #1,D5; MOVE.L D5,D3; ORI.B #80,D7; BRA.W 4baee.
    case 0x4ba24:if(!on33_word(c,r.a[2],0xa,value))return false;r.d[5]=on33_high_sub(r.d[5],value)-1U;r.d[3]=r.d[5];r.d[7]|=0x80U;r.pc=0x4baee;return true;
    // MOVE.L D4,D6; SUB.L 42(A3),D6; ADD.L 4a(A3),D6; CMP.L D6,D0; BMI.W 4ba58.
    case 0x4ba38:r.d[6]=r.d[4];if(!on33_swap_rect(c,r.d[6],0x42,0x4a))return false;r.pc=on33_minus(r.d[0]-r.d[6])?0x4ba58:0x4ba48;return true;
    // ORI.B #20,6d(A3); MOVE.L D4,D2; ORI.B #80,D7; BRA.W 4baee.
    case 0x4ba48:if(!on33_or(c,r.a[3],0x6d,0x20))return false;r.d[2]=r.d[4];r.d[7]|=0x80U;r.pc=0x4baee;return true;
    // SWAP D6; SUB.W 8(A2),D6; SWAP D6; CMP.L D6,D0; BPL.W 4ba80.
    case 0x4ba58:if(!on33_word(c,r.a[2],8,value))return false;r.d[6]=on33_high_sub(r.d[6],value);r.pc=on33_minus(r.d[0]-r.d[6])?0x4ba66:0x4ba80;return true;
    // ORI.B #10,6d(A3); SWAP D4; SUB.W 8(A2),D4; SWAP D4; SUBQ.L #1,D4; MOVE.L D4,D2; ORI.B #80,D7; BRA.W 4baee.
    case 0x4ba66:
        if(!on33_or(c,r.a[3],0x6d,0x10) || !on33_word(c,r.a[2],8,value))return false;r.d[4]=on33_high_sub(r.d[4],value)-1U;r.d[2]=r.d[4];
        r.d[7]|=0x80U;r.pc=0x4baee;return true;
    // SWAP D6; ADD.W 2(A2),D6; SWAP D6; CMP.L D6,D0; BMI.W 4bac0.
    case 0x4ba80:if(!on33_word(c,r.a[2],2,value))return false;r.d[6]=on33_high_add(r.d[6],value);r.pc=on33_minus(r.d[0]-r.d[6])?0x4bac0:0x4ba8e;return true;
    // ORI.B #20|#10,6d(A3); MOVE.L D2,D6; SUB.L D0,D6; SUB.L 42(A3),D6; ADD.L 4a(A3),D6; TST.L D6; BGE.W 4babc / BLE.W 4baee.
    case 0x4ba8e:case 0x4bac0:
        if(!on33_or(c,r.a[3],0x6d,r.pc==0x4ba8eU?0x20U:0x10U))return false;r.d[6]=r.d[2]-r.d[0];if(!on33_swap_rect(c,r.d[6],0x42,0x4a))return false;
        if(r.pc==0x4ba8eU)r.pc=on33_minus(r.d[6])?0x4baa6:0x4babc;else r.pc=(on33_minus(r.d[6]) || r.d[6]==0U)?0x4baee:0x4bad8;return true;
    // MOVE.L D0,D2; CMPA.W #0,A0; BEQ.W 4bab8 / 4baea.
    case 0x4baa6:case 0x4bad8:
        r.d[2]=r.d[0];if(r.pc==0x4baa6U)r.pc=r.a[0]==0U?0x4bab8:0x4bab0;else r.pc=r.a[0]==0U?0x4baea:0x4bae2;return true;
    // SUB.L 1c(A0),D2; ADD.L 14(A0),D2.
    case 0x4bab0:case 0x4bae2:if(!on33_frame_x(c,r.d[2]))return false;r.pc+=8U;return true;
    case 0x4bab8:case 0x4baea:r.d[7]|=0x80U;r.pc=r.pc==0x4bab8U?0x4babcU:0x4baeeU;return true; // ORI.B #80,D7.
    // MOVE.W (A7)+,D6; ADDQ.W #1,D6; CMPA.L #10db78,A4; BCS.W 4b91e.
    case 0x4baee:if(!am_pop(c,2,value))return false;am_word(r.d[6],(value+1U)&65535U);r.pc=r.a[4]<0x10db78U?0x4b91e:0x4bafc;return true;
    case 0x4bafc:r.pc=r.a[0]==0U?0x4bb14:0x4bb04;return true;           // CMPA.W #0,A0; BEQ.W 4bb14.
    // SUB.L 1c(A0),D0; SUB.L 20(A0),D1; SUB.L 14(A0),D2; SUB.L 18(A0),D3.
    case 0x4bb04:
        if(!on33_long(c,r.a[0],0x1c,value))return false;r.d[0]-=value;if(!on33_long(c,r.a[0],0x20,value))return false;r.d[1]-=value;
        if(!on33_long(c,r.a[0],0x14,value))return false;r.d[2]-=value;if(!on33_long(c,r.a[0],0x18,value))return false;r.d[3]-=value;
        r.pc=0x4bb14;return true;
    case 0x4bb14:r.d[2]-=r.d[0];r.d[3]-=r.d[1];return am_return(c);    // SUB.L D0,D2; SUB.L D1,D3; RTS.
    // ---- input test 4bce0: MOVE.B #ff,549f(A5); CLR.B 54a0(A5); MOVEM.L D0-D7,-(A7); CMPA.L #100cb8,A6; BEQ.W 4bd6e.
    case 0x4bce0:
        if(!on33_put(c,r.a[5],0x549f,1,0xff) || !on33_put(c,r.a[5],0x54a0,1,0))return false;
        for(unsigned int i=8;i>0;--i)if(!am_push(c,4,r.d[i-1U]))return false;
        r.pc=r.a[6]==0x100cb8U?0x4bd6e:0x4bcf8;return true;
    case 0x4bcf8:r.pc=r.a[6]==0x100da8U?0x4bd6e:0x4bd02;return true;  // CMPA.L #100da8,A6; BEQ.W 4bd6e.
    case 0x4bd02:return am_call(c,0x4d8d8,0x4bd08);                     // JSR 4d8d8.l (boundary).
    case 0x4bd08:r.pc=(r.d[0]&0x80U)!=0U?0x4bd0e:0x4bd1e;return true;  // TST.B D0; BPL.W 4bd1e.
    // MOVE.B #ff,54a2(A5); MOVE.B #ff,54a3(A5); BRA.W 4bdfe.
    case 0x4bd0e:if(!on33_put(c,r.a[5],0x54a2,1,0xff) || !on33_put(c,r.a[5],0x54a3,1,0xff))return false;r.pc=0x4bdfe;return true;
    // MOVE.W D1,-(A7); MOVE.W 42(A6),D0; MOVE.W 46(A6),D1; MOVEQ #ff,D7; JSR 19a00.l (boundary).
    case 0x4bd1e:
        if(!am_push(c,2,on33_w(r.d[1])) || !on33_word(c,r.a[6],0x42,value))return false;am_word(r.d[0],value);
        if(!on33_word(c,r.a[6],0x46,value))return false;am_word(r.d[1],value);r.d[7]=0xffffffffU;return am_call(c,0x19a00,0x4bd30);
    // MOVE.W (A7)+,D1; MOVE.L #4bca8,D7; CMPI.B #4,D1; BEQ.W 4bdd6.
    case 0x4bd30:if(!am_pop(c,2,value))return false;am_word(r.d[1],value);r.d[7]=0x4bca8;r.pc=on33_b(r.d[1])==4U?0x4bdd6:0x4bd40;return true;
    case 0x4bd40:r.pc=on33_b(r.d[1])==8U?0x4bdd6:0x4bd48;return true;  // CMPI.B #8,D1; BEQ.W 4bdd6.
    case 0x4bd48:r.d[7]=0x4bcb0;r.pc=on33_b(r.d[1])==9U?0x4bdd6:0x4bd56;return true; // MOVE.L #4bcb0,D7; CMPI.B #9,D1; BEQ.W.
    case 0x4bd56:r.d[7]=0x4bcb8;r.pc=on33_b(r.d[1])==5U?0x4bdd6:0x4bd64;return true; // MOVE.L #4bcb8,D7; CMPI.B #5,D1; BEQ.W.
    case 0x4bd64:case 0x4bdd0:r.d[7]=0x4bca0;r.pc=0x4bdd6;return true; // MOVE.L #4bca0,D7 (+ BRA.W 4bdd6).
    // MOVE.B 81(A6),D7; SNE.B D7; EXT.W D7; MOVE.B 82(A6),D7; MOVE.W 42(A6),D0; MOVE.W 46(A6),D1; JSR 19a00.l (boundary).
    case 0x4bd6e:
        if(!on33_get(c,r.a[6],0x81,1,value))return false;am_word(r.d[7],value!=0U?0xffffU:0U);if(!on33_get(c,r.a[6],0x82,1,value))return false;
        am_byte(r.d[7],value);if(!on33_word(c,r.a[6],0x42,value))return false;am_word(r.d[0],value);
        if(!on33_word(c,r.a[6],0x46,value))return false;am_word(r.d[1],value);return am_call(c,0x19a00,0x4bd88);
    case 0x4bd88:return am_call(c,0x1aa3a,0x4bd8e);                     // JSR 1aa3a.l.
    case 0x4bd8e:r.d[7]=0x4bcc0;r.pc=((r.d[0]>>3)&1U)!=0U?0x4bdd6:0x4bd9c;return true; // MOVE.L #4bcc0,D7; BTST #3,D0; BNE.W.
    case 0x4bd9c:r.d[7]=0x4bcc8;r.pc=((r.d[0]>>14)&1U)!=0U?0x4bdd6:0x4bdaa;return true; // MOVE.L #4bcc8,D7; BTST #e,D0 (bit 14); BNE.W.
    case 0x4bdaa:if(!on33_bit(c,r.a[6],0x61,7,bit))return false;r.pc=bit?0x4bdd0:0x4bdb4;return true; // BTST.B #7,61(A6); BNE.W 4bdd0.
    case 0x4bdb4:r.d[7]=0x4bcd0;r.pc=((r.d[0]>>6)&1U)!=0U?0x4bdd6:0x4bdc2;return true; // MOVE.L #4bcd0,D7; BTST #6,D0; BNE.W.
    case 0x4bdc2:r.d[7]=0x4bcd8;r.pc=((r.d[0]>>7)&1U)!=0U?0x4bdd6:0x4bdd0;return true; // MOVE.L #4bcd8,D7; BTST #7,D0; BNE.W.
    // MOVE.L D7,54a6(A5); MOVE.B 5c8c(A5),54a2(A5); MOVE.B 5c8d(A5),54a3(A5); JSR 1aa3a.l.
    case 0x4bdd6:
        if(!on33_put(c,r.a[5],0x54a6,4,r.d[7]) || !on33_copy(c,r.a[5],0x5c8c,0x54a2) || !on33_copy(c,r.a[5],0x5c8d,0x54a3))return false;
        return am_call(c,0x1aa3a,0x4bdec);
    case 0x4bdec:r.pc=((r.d[0]>>6)&1U)!=0U?0x4bdf8:0x4bdf4;return true; // BTST #6,D0; BNE.W 4bdf8.
    case 0x4bdf4:r.pc=0x4bdfe;return true;                               // BRA.W 4bdfe.
    case 0x4bdf8:if(!on33_put(c,r.a[5],0x54a0,1,1))return false;r.pc=0x4bdfe;return true; // MOVE.B #1,54a0(A5).
    // MOVEM.L (A7)+,D0-D7; BRA.W 4bc58 (u08b block 4bc44, contract decision 5).
    case 0x4bdfe:for(unsigned int i=0;i<8;++i)if(!am_pop(c,4,r.d[i]))return false;r.pc=0x4bc58;return true;
    // ---- 4be50: JSR 4bc44(PC) / MOVE.B #ff,549e(A5); MOVE.B #0,10d49d.l; MOVEM.L 2e(A6),D0-D3/A0; BRA.W 4bf0a.
    case 0x4be50:return am_call(c,0x4bc44,0x4be54);
    case 0x4be54:if(!on33_put(c,r.a[5],0x549e,1,0xff) || !am_write(c,0x10d49d,1,0) || !on33_restore(c))return false;r.pc=0x4bf0a;return true;
    // ---- 4be6c: BSR.W 4bce0 / MOVE.B #0,10d49d.l; MOVEM.L 2e(A6),D0-D3/A0; BRA.W 4bf0a.
    case 0x4be6c:return am_call(c,0x4bce0,0x4be70);
    case 0x4be70:if(!am_write(c,0x10d49d,1,0) || !on33_restore(c))return false;r.pc=0x4bf0a;return true;
    // ---- 4bfb4: BSR.W 4bce0 / BSR.W 4c020 / BRA.W 4bf0a.
    case 0x4bfb4:return am_call(c,0x4bce0,0x4bfb8);
    case 0x4bfb8:return am_call(c,0x4c020,0x4bfbc);
    case 0x4bfbc:r.pc=0x4bf0a;return true;
    // ---- 4c0ea: JSR 4bce0(PC) / BRA.B 4c0b0 (U12).
    case 0x4c0ea:return am_call(c,0x4bce0,0x4c0ee);
    case 0x4c0ee:r.pc=0x4c0b0;return true;
    // ---- 4c37c: MOVEA.L #4cf52,A0; MOVE.W #0,D0; JSR 28ae.l (child 4cf52, N35) / BRA.W 4c7a4.
    case 0x4c37c:r.a[0]=0x4cf52;am_word(r.d[0],0);return am_call(c,0x28ae,0x4c38c);
    case 0x4c38c:r.pc=0x4c7a4;return true;
    // ---- 4c7a4: CLR.W 76(A0); MOVE.W #80,78(A0); CLR.W 7c 7a 7e 80 82 96(A0); CLR.B 9b 98 99(A0); MOVEA.L 3e(A6),A1;
    // MOVE.L 2e(A6),D0; MOVE.L 32(A6),D1; CMPA.W #0,A1; BEQ.W 4c7ee.
    case 0x4c7a4:{
        static const std::uint32_t words[6]={0x7c,0x7a,0x7e,0x80,0x82,0x96};
        static const std::uint32_t bytes[3]={0x9b,0x98,0x99};
        if(!on33_put(c,r.a[0],0x76,2,0) || !on33_put(c,r.a[0],0x78,2,0x80))return false;
        for(unsigned int i=0;i<6;++i)if(!on33_put(c,r.a[0],words[i],2,0))return false;
        for(unsigned int i=0;i<3;++i)if(!on33_put(c,r.a[0],bytes[i],1,0))return false;
        if(!on33_long(c,r.a[6],0x3e,value))return false;r.a[1]=value;if(!on33_long(c,r.a[6],0x2e,value))return false;r.d[0]=value;
        if(!on33_long(c,r.a[6],0x32,value))return false;r.d[1]=value;r.pc=r.a[1]==0U?0x4c7ee:0x4c7e6;return true;}
    // ADD.L 14(A1),D0; ADD.L 18(A1),D1.
    case 0x4c7e6:if(!on33_long(c,r.a[1],0x14,value))return false;r.d[0]+=value;if(!on33_long(c,r.a[1],0x18,value))return false;r.d[1]+=value;r.pc=0x4c7ee;return true;
    // LEA 538e(A5),A1; SUB.L 14(A1),D0; SUB.L 18(A1),D1; MOVE.L D0,86(A0); MOVE.L D1,8a(A0); MOVE.L D0,8e(A0); MOVE.L D1,92(A0);
    // MOVE.L A1,3e(A0); RTS.
    case 0x4c7ee:
        r.a[1]=am_index(r.a[5],0x538e);if(!on33_long(c,r.a[1],0x14,value))return false;r.d[0]-=value;if(!on33_long(c,r.a[1],0x18,value))return false;
        r.d[1]-=value;
        if(!on33_put(c,r.a[0],0x86,4,r.d[0]) || !on33_put(c,r.a[0],0x8a,4,r.d[1]) || !on33_put(c,r.a[0],0x8e,4,r.d[0]) ||
            !on33_put(c,r.a[0],0x92,4,r.d[1]) || !on33_put(c,r.a[0],0x3e,4,r.a[1]))return false;
        return am_return(c);
    default:return am_error(c,"unsupported animation objects n33 PC");
    }
}
}
