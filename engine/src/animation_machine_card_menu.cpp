#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// MOVE.B (A0)+,Dn: one live BYTE read at the current A0, low BYTE replaced.
bool menu_next(AnimationMachineContext& c,unsigned int reg) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[0],1,value))return false;
    c.s.a[0]+=1U;am_byte(c.s.d[reg],value);return true;
}
// CMP.B mem,D0 then BLS: taken when the low BYTE of D0 <= mem BYTE (unsigned).
bool menu_bls_byte(AnimationMachineContext& c,std::uint32_t address,std::uint32_t low,std::uint32_t high) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    c.s.pc=(c.s.d[0]&255U)<=value?low:high;return true;
}
}
// Card menu push a29c -> a0a0 (frame stack at 107e0e..107f0e), text width 38e8/386e,
// and the card child renderer setup c2a8 -> a2b8 -> c2ba.
// 38c8/38e2 (TRAP #f) have no executor; 9b58 and a370 run in animation_machine_card_menu_open.cpp.
bool animation_card_menu_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // MOVE.L #3650,-ea(A5); MOVE.B #0,-e6(A5); MOVE.L #107f0e,107f0e; BRA a0a0. Live A5.
    case 0xa29c:
        if(!am_write(c,am_index(r.a[5],0xff16),4,0x3650) || !am_write(c,am_index(r.a[5],0xff1a),1,0) ||
           !am_write(c,0x107f0e,4,0x107f0e))return false;
        r.pc=0xa0a0;return true;
    // MOVE.L -ee(A5),-(A7) through the incoming A5, then LEA 108000,A5.
    // SUBA.L #10; CMPA.L #107e0e; BCC: unsigned 32-bit A2 >= 107e0e.
    case 0xa0a0:
        if(!am_read(c,am_index(r.a[5],0xff12),4,value) || !am_push(c,4,value))return false;r.a[5]=0x108000;
        if(!am_read(c,am_index(r.a[5],0xff0e),4,value))return false;r.a[2]=value;
        if(!am_write(c,am_index(r.a[5],0xff12),4,r.a[2]))return false;r.a[2]-=0x10U;
        r.pc=r.a[2]>=0x107e0eU?0xa0c4:0xa0c2;return true;
    // Overflow RTS pops the LONG pushed at a0a0 as the PC (original, uncorrected).
    case 0xa0c2:case 0x3878:case 0x38a4:case 0xa2bc:return am_return(c);
    // MOVEM.L D0-D1/A0,-(A7): predecrement stores A0 first, memory ascending D0,D1,A0.
    case 0xa0c4:
        if(!am_write(c,am_index(r.a[5],0xff0e),4,r.a[2]) ||
           !am_push(c,4,r.a[0]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]) ||
           !am_write(c,r.a[2]+9U,1,255) || !am_write(c,r.a[2]+0xaU,1,255) ||
           !am_write(c,r.a[2]+0xbU,1,0) || !am_write(c,r.a[2]+0xcU,1,0))return false;
        r.a[1]=0xa008;r.a[2]+=0x10U;r.pc=r.a[2]>=0x107f0eU?0xa104:0xa0f8;return true;
    // Nested menu: BSR 9b58 (card menu open executor) with return a100.
    case 0xa0f8:
        if(!am_write(c,am_index(r.a[5],0xff12),4,r.a[2]))return false;return am_call(c,0x9b58,0xa100);
    case 0xa104:
        if(!am_pop(c,4,r.d[0]) || !am_pop(c,4,r.d[1]) || !am_pop(c,4,r.a[0]) ||
           !am_read(c,am_index(r.a[5],0xff0e),4,value))return false;r.a[2]=value;
        if(!am_write(c,am_index(r.a[5],0xff12),4,r.a[2]) || !am_write(c,r.a[2],4,r.a[0]) ||
           !am_write(c,r.a[2]+9U,1,r.d[0]) || !am_write(c,r.a[2]+0xaU,1,r.d[1]) ||
           !am_write(c,r.a[2]+7U,1,0) || !am_write(c,r.a[2]+8U,1,0) || !am_write(c,r.a[2]+0xfU,1,0) ||
           !am_write(c,r.a[2]+0xdU,1,3) || !am_write(c,r.a[2]+0xeU,1,255))return false;
        if(!am_read(c,r.a[0]+4U,1,value) || !am_write(c,r.a[2]+0xbU,1,value) ||
           !am_read(c,r.a[0]+5U,1,value) || !am_write(c,r.a[2]+0xcU,1,value) ||
           !am_write(c,r.a[2]+6U,1,0))return false;
        r.a[3]=r.a[0];r.d[0]=0;
        if(!am_read(c,r.a[3],4,value))return false;r.a[0]=value;
        r.pc=r.a[0]==0?0xa15e:0xa158;return true; // CMPA.W #0 sign-extends: full 32-bit test.
    case 0xa158:return am_call(c,0x38e8,0xa15e);
    // MOVE.W D0,-(A7); ADDA.W #10,A3; MOVEA.L (A3),A0.
    case 0xa15e:
        if(!am_push(c,2,r.d[0]))return false;r.a[3]=am_index(r.a[3],0x10);
        if(!am_read(c,r.a[3],4,value))return false;r.a[0]=value;r.pc=0xa166;return true;
    // CMPA.W #ffff/#0/#fffe: sign-extended immediates against the whole A0.
    case 0xa166:
        if(r.a[0]==0xffffffffU)r.pc=0xa198;
        else if(r.a[0]==0 || r.a[0]==0xfffffffeU)r.pc=0xa18c;
        else r.pc=0xa17e;
        return true;
    case 0xa17e:return am_call(c,0x38e8,0xa184);
    // CMP.W (A7),D0; BLS: unsigned D0.W <= (A7).W keeps the stacked maximum.
    case 0xa184:
        if(!am_read(c,r.a[7],2,value))return false;r.pc=(r.d[0]&65535U)<=value?0xa18c:0xa18a;return true;
    case 0xa18a:
        if(!am_write(c,r.a[7],2,r.d[0]&65535U))return false;r.pc=0xa18c;return true;
    // ADDQ.B #1,6(A2) wraps in the BYTE; separators and null items are counted too.
    case 0xa18c:
        if(!am_read(c,r.a[2]+6U,1,value) || !am_write(c,r.a[2]+6U,1,(value+1U)&255U))return false;
        r.a[3]=am_index(r.a[3],0xa);
        if(!am_read(c,r.a[3],4,value))return false;r.a[0]=value;r.pc=0xa166;return true;
    // MOVEA.L (A2),A3; MOVE.W e(A3),D0; ANDI.W #e,D0; BNE.
    case 0xa198:
        if(!am_read(c,r.a[2],4,value))return false;r.a[3]=value;
        if(!am_read(c,r.a[3]+0xeU,2,value))return false;am_word(r.d[0],value&0xeU);
        r.pc=(r.d[0]&65535U)?0xa1ac:0xa1a6;return true;
    case 0xa1a6:r.d[0]=2;r.pc=0xa1ae;return true;
    case 0xa1ac:r.d[0]=0;r.pc=0xa1ae;return true;
    // ADDQ.W #2,D0; ADD.W (A7)+,D0; CMP.B b(A2),D0; BLS.
    case 0xa1ae:
        am_word(r.d[0],r.d[0]+2U);if(!am_pop(c,2,value))return false;am_word(r.d[0],r.d[0]+value);
        return menu_bls_byte(c,r.a[2]+0xbU,0xa1be,0xa1ba);
    case 0xa1ba:
        if(!am_write(c,r.a[2]+0xbU,1,r.d[0]))return false;r.pc=0xa1be;return true;
    // MOVE.B 6(A2),D0 replaces only the low BYTE; ADDQ.W #2 is a WORD add.
    case 0xa1be:
        if(!am_read(c,r.a[2]+6U,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]+2U);
        return menu_bls_byte(c,r.a[2]+0xcU,0xa1d0,0xa1cc);
    case 0xa1cc:
        if(!am_write(c,r.a[2]+0xcU,1,r.d[0]))return false;r.pc=0xa1d0;return true;
    // MOVE.B #0,4(A2); MOVE.B #1,-e5(A5); MOVE.L (A7)+,-ee(A5); RTS.
    case 0xa1d0:
        if(!am_write(c,r.a[2]+4U,1,0) || !am_write(c,am_index(r.a[5],0xff1b),1,1) ||
           !am_pop(c,4,value) || !am_write(c,am_index(r.a[5],0xff12),4,value))return false;
        return am_return(c);
    // MOVE.B (A0)+,D2; CMPI.B #5c,D2; BEQ.
    case 0x386e:
        if(!menu_next(c,2))return false;r.pc=(r.d[2]&255U)==0x5cU?0x387a:0x3878;return true;
    case 0x387a:
        if(!menu_next(c,2))return false;value=r.d[2]&255U;
        if(value==0x6eU)r.pc=0x38be;
        else if(value==0x72U)r.pc=0x38ca;
        else if(value==0x63U)r.pc=0x38b6;
        else if(value==0x70U)r.pc=0x38a6;
        else if(value==0x6cU)r.pc=0x38ce;
        else r.pc=0x38a4;
        return true;
    // \p: ANDI.W #ff,D1; MOVE.B (A0)+,D7; ANDI.B #f,D7; LSL.W #8,D7; OR.W D7,D1. D7 bits 16-31 kept.
    case 0x38a6:
        am_word(r.d[1],r.d[1]&0xffU);if(!menu_next(c,7))return false;
        am_byte(r.d[7],r.d[7]&0xfU);am_word(r.d[7],r.d[7]<<8);am_word(r.d[1],r.d[1]|r.d[7]);
        r.pc=0x386e;return true;
    // \c: ANDI.W #ff00,D1; MOVE.B (A0)+,D1.
    case 0x38b6:
        am_word(r.d[1],r.d[1]&0xff00U);if(!menu_next(c,1))return false;r.pc=0x386e;return true;
    // \n: ADDQ.W #1,D3; CMPI.W #7500,D3; BCS 38ca, else TRAP #f at 38c8.
    case 0x38be:
        am_word(r.d[3],r.d[3]+1U);r.pc=(r.d[3]&65535U)<0x7500U?0x38ca:0x38c8;return true;
    case 0x38ca:case 0x38e4:am_word(r.d[0],r.d[3]);r.pc=0x386e;return true;
    // \l: MOVEQ #0,D3; MOVE.B (A0)+,D3; LSL.W #5; ADD.B (A0)+ (BYTE); ADDI.W #7000; CMPI.W #7500; BCS.
    case 0x38ce:
        r.d[3]=0;if(!menu_next(c,3))return false;am_word(r.d[3],r.d[3]<<5);
        if(!am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;am_byte(r.d[3],r.d[3]+value);
        am_word(r.d[3],r.d[3]+0x7000U);r.pc=(r.d[3]&65535U)<0x7500U?0x38e4:0x38e2;return true;
    // MOVE.W #0,-(A7); BSR 386e.
    case 0x38e8:
        if(!am_push(c,2,0))return false;return am_call(c,0x386e,0x38ee);
    // TST.B D2 then BEQ 38fe (38fa reaches the same BEQ through BRA 38f0).
    case 0x38ee:case 0x38fa:r.pc=(r.d[2]&255U)?0x38f4:0x38fe;return true;
    // ADDQ.W #1,(A7); BSR 386e.
    case 0x38f4:
        if(!am_read(c,r.a[7],2,value) || !am_write(c,r.a[7],2,(value+1U)&65535U))return false;
        return am_call(c,0x386e,0x38fa);
    // MOVE.W (A7)+,D0; RTS.
    case 0x38fe:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);return am_return(c);
    case 0xc2a8:r.a[0]=0xe84c8;return am_call(c,0xa2b8,0xc2b4);
    // MOVE.L A0,-ea(A5) through the live A5.
    case 0xa2b8:
        if(!am_write(c,am_index(r.a[5],0xff16),4,r.a[0]))return false;r.pc=0xa2bc;return true;
    case 0xc2b4:
        if(!am_write(c,r.a[6],4,0xc2ba))return false;r.pc=0xc2ba;return true;
    // JSR a370 (menu frame, card menu open executor).
    case 0xc2ba:return am_call(c,0xa370,0xc2c0);
    default:return am_error(c,"unsupported animation card menu PC");
    }
}
}
