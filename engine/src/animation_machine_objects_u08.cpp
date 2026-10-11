#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// 4483a JMP 4483e(PC,D7.W): the 96 BRA.W entries 4483e+4k (k = 0..5f) transcribed from the original code (decision 4).
// The D7 producer 447be returns D7.W = 4k (k < 60) or 160; the jump itself moves to the computed PC (F1 decision 3).
const std::uint32_t OU8_TABLE=0x4483e;
const unsigned int OU8_TABLE_ENTRIES=96;
const std::uint32_t OU8_TARGETS[OU8_TABLE_ENTRIES]={
    0x44aae,0x44aba,0x44ac6,0x44ad2,0x44aae,0x44aba,0x44ac6,0x44ad2,0x44aae,0x44aba,0x44ac6,0x44ad2,0x44aae,0x44aba,0x44ac6,0x44ad2,
    0x44aae,0x44aba,0x44ac6,0x44ad2,0x44aae,0x44aba,0x44ac6,0x44ad2,0x44aae,0x44aba,0x44ac6,0x44ad2,0x44aae,0x44aba,0x44ac6,0x44ad2,
    0x449d2,0x449d8,0x449d2,0x449d8,0x449de,0x449e8,0x449f2,0x449fc,0x449de,0x449e8,0x449f2,0x449fc,0x449de,0x449e8,0x449f2,0x449fc,
    0x449de,0x449e8,0x449f2,0x449fc,0x44a06,0x44a10,0x44a1a,0x44a24,0x44a06,0x44a10,0x44a1a,0x44a24,0x44a2e,0x44a34,0x44a3c,0x44a46,
    0x44a4e,0x44a5a,0x44a66,0x44a72,0x44a4e,0x44a5a,0x44a66,0x44a72,0x44a7e,0x44a8a,0x44a96,0x44aa2,0x44a7e,0x44a8a,0x44a96,0x44aa2,
    0x44a7e,0x44a8a,0x44a96,0x44aa2,0x44a7e,0x44a8a,0x44a96,0x44aa2,0x449c4,0x449c6,0x449cc,0x449c6,0x449c6,0x449c4,0x449c4,0x449c4};
const std::uint32_t OU8_FAIL=0x449be;  // MOVE.W #160,D7; RTS (the true branch of every target predicate).
bool ou8_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou8_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// LONG flags of ADD.L s,d (r = d+s) and CMP.L s,d (r = d-s): N, Z and V of the 68000.
struct Ou8Flags {bool n,z,v;};
Ou8Flags ou8_add(std::uint32_t d,std::uint32_t s) {
    const std::uint32_t r=d+s;Ou8Flags f;f.n=(r>>31)!=0;f.z=r==0;f.v=((~(s^d)&(d^r))>>31)!=0;return f;
}
Ou8Flags ou8_cmp(std::uint32_t d,std::uint32_t s) {
    const std::uint32_t r=d-s;Ou8Flags f;f.n=(r>>31)!=0;f.z=r==0;f.v=(((s^d)&(d^r))>>31)!=0;return f;
}
Ou8Flags ou8_tst(std::uint32_t d) {Ou8Flags f;f.n=(d>>31)!=0;f.z=d==0;f.v=false;return f;}
bool ou8_gt(const Ou8Flags& f) {return !f.z && f.n==f.v;}  // BGT
bool ou8_lt(const Ou8Flags& f) {return f.n!=f.v;}           // BLT
// Target predicate: the true branch goes to 449be (D7.W = 160), otherwise the next block (an RTS).
void ou8_branch(AnimationMachineState& r,bool taken,std::uint32_t rts_pc) {r.pc=taken?OU8_FAIL:rts_pc;}
// MOVE.L Dsrc,D4; LSL.L #shift,D4 (shift 0: no LSL).
std::uint32_t ou8_scaled(std::uint32_t value,unsigned int shift) {return value<<shift;}
}
// Objects F4 U08a (181 block starts, the first part of the proposed U08 split): the terrain map WORD 18be8, C2 1aa3a, the relative
// position helper 43eb8, the terrain code 447be with the jump table 4483a (all 96 BRA.W entries 4483e..449ba) and its slope
// predicates 449be..44adc, and C3 49274 (-> 43e34) / 49290 (-> 43e04). 4483a moves to the computed PC 4483e+D7.W through the
// routing (entries and 449be are block starts; other values reach the routing errors like the original jump). U08a has no carry
// consumer and no known-carry producer. The callee 47288 has no executor.
bool animation_objects_u08_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 18be8: MOVE.W D0,D6; MOVE.W D1,D7; NOT.W D7; ANDI.W #1f8,D6; ANDI.W #1f8,D7; LSR.W #2,D7; LSL.W #4,D6; OR.W D6,D7;
    // ADDI.W #80,D7; MOVE.W (A0,D7.W),D7; RTS.
    case 0x18be8: {
        const std::uint32_t d6=(r.d[0]&0x1f8U)<<4;const std::uint32_t d7=((~r.d[1]&0x1f8U)>>2|d6)+0x80U;
        am_word(r.d[6],d6);am_word(r.d[7],d7);
        if(!am_read(c,am_index(r.a[0],r.d[7]),2,value))return false;am_word(r.d[7],value);return am_return(c);
    }
    // ---- 1aa3a: MOVE.W 543c(A5),D0; RTS.
    case 0x1aa3a:if(!ou8_get(c,r.a[5],0x543c,2,value))return false;am_word(r.d[0],value);return am_return(c);

    // ---- 43eb8: CMPA.L A1,A0; BNE 43ec0.
    case 0x43eb8:r.pc=r.a[0]!=r.a[1]?0x43ec0:0x43ebe;return true;
    case 0x43ebe:return am_return(c); // RTS.
    // ADD.L D0,D2; ADD.L D1,D3; CMPA.W #0,A0; BEQ 43edc.
    case 0x43ec0:r.d[2]+=r.d[0];r.d[3]+=r.d[1];r.pc=r.a[0]==0?0x43edc:0x43ecc;return true;
    // ADD.L 1c(A0),D0; ADD.L 20(A0),D1; ADD.L 14(A0),D2; ADD.L 18(A0),D3.
    case 0x43ecc:
        if(!ou8_get(c,r.a[0],0x1c,4,value))return false;r.d[0]+=value;if(!ou8_get(c,r.a[0],0x20,4,value))return false;r.d[1]+=value;
        if(!ou8_get(c,r.a[0],0x14,4,value))return false;r.d[2]+=value;if(!ou8_get(c,r.a[0],0x18,4,value))return false;r.d[3]+=value;
        r.pc=0x43edc;return true;
    case 0x43edc:r.pc=r.a[1]==0?0x43ef4:0x43ee4;return true; // CMPA.W #0,A1; BEQ 43ef4.
    // SUB.L 1c(A1),D0; SUB.L 20(A1),D1; SUB.L 14(A1),D2; SUB.L 18(A1),D3.
    case 0x43ee4:
        if(!ou8_get(c,r.a[1],0x1c,4,value))return false;r.d[0]-=value;if(!ou8_get(c,r.a[1],0x20,4,value))return false;r.d[1]-=value;
        if(!ou8_get(c,r.a[1],0x14,4,value))return false;r.d[2]-=value;if(!ou8_get(c,r.a[1],0x18,4,value))return false;r.d[3]-=value;
        r.pc=0x43ef4;return true;
    case 0x43ef4:r.d[2]-=r.d[0];r.d[3]-=r.d[1];return am_return(c); // SUB.L D0,D2; SUB.L D1,D3; RTS.

    // ---- 447be: CMPA.W #0,A0; BEQ 4482e / CMPA.L #109156,A0; BEQ 447e4 / CMPA.L #10b1d6,A0; BEQ 447e4.
    case 0x447be:r.pc=r.a[0]==0?0x4482e:0x447c6;return true;
    case 0x447c6:r.pc=r.a[0]==0x109156U?0x447e4:0x447d0;return true;
    case 0x447d0:r.pc=r.a[0]==0x10b1d6U?0x447e4:0x447da;return true;
    case 0x447da:return am_call(c,0x47288,0x447e0);       // JSR 47288.L (boundary without an executor).
    case 0x447e0:r.pc=0x447ee;return true;                // BRA 447ee.
    case 0x447e4:return am_call(c,0x18be8,0x447ea);       // JSR 18be8.L.
    case 0x447ea:am_byte(r.d[7],r.d[7]+0x58U);r.pc=0x447ee;return true; // ADDI.B #58,D7.
    // MOVEQ #0,D6; MOVE.W D7,-(A7); MOVE.B (A7)+,D6 (the high BYTE of D7.W; A7 BYTE steps are 2); ANDI.W #1f,D6; CMPI.W #1,D6;
    // BNE 4480c.
    case 0x447ee:
        r.d[6]=0;if(!am_push(c,2,r.d[7]&65535U))return false;if(!am_read(c,r.a[7],1,value))return false;r.a[7]+=2U;
        r.d[6]=value&0x1fU;r.pc=r.d[6]==1U?0x44800:0x4480c;return true;
    case 0x44800:if(!ou8_get(c,r.a[5],0x549f,1,value))return false;r.pc=value?0x44808:0x4480c;return true; // TST.B 549f(A5); BEQ 4480c.
    case 0x44808:am_byte(r.d[7],0x58);r.pc=0x4480c;return true; // MOVE.B #58,D7.
    // SWAP D6; MOVE.B D7,D6; ROL.W #2,D7; ANDI.W #3,D7; EXG D6,D7; CMP.B 549c(A5),D6; BHI 4482e (D6.B > BYTE unsigned).
    case 0x4480c: {
        am_swap(r.d[6]);am_byte(r.d[6],r.d[7]);
        const std::uint32_t w=r.d[7]&65535U;am_word(r.d[7],((w<<2)|(w>>14))&3U);
        const std::uint32_t t=r.d[6];r.d[6]=r.d[7];r.d[7]=t;
        if(!ou8_get(c,r.a[5],0x549c,1,value))return false;r.pc=(r.d[6]&255U)>(value&255U)?0x4482e:0x44820;return true;
    }
    case 0x44820:r.pc=(r.d[7]&255U)>=0x60U?0x4482e:0x44828;return true; // CMPI.B #60,D7; BCC 4482e.
    case 0x44828:am_word(r.d[7],r.d[7]<<2);return am_return(c);         // ADD.W D7,D7; ADD.W D7,D7; RTS.
    // ORI.W #200,54aa(A5); MOVE.W #160,D7; RTS.
    case 0x4482e:if(!ou8_get(c,r.a[5],0x54aa,2,value) || !ou8_put(c,r.a[5],0x54aa,2,(value|0x200U)&65535U))return false;
        am_word(r.d[7],0x160);return am_return(c);
    // ---- 4483a: JMP 4483e(PC,D7.W) (computed PC through the routing).
    case 0x4483a:r.pc=am_index(OU8_TABLE,r.d[7]);return true;

    // ---- Table targets (D2/D3 slope predicates); 449be is the shared true branch.
    case 0x449be:am_word(r.d[7],0x160);return am_return(c); // MOVE.W #160,D7; RTS.
    case 0x449c4:case 0x449ca:case 0x449d0:case 0x449d6:case 0x449dc:case 0x449e6:case 0x449f0:case 0x449fa:case 0x44a04:case 0x44a0e:
    case 0x44a18:case 0x44a22:case 0x44a2c:case 0x44a32:case 0x44a3a:case 0x44a44:case 0x44a4c:case 0x44a58:case 0x44a64:case 0x44a70:
    case 0x44a7c:case 0x44a88:case 0x44a94:case 0x44aa0:case 0x44aac:case 0x44ab8:case 0x44ac4:case 0x44ad0:case 0x44adc:
        return am_return(c); // RTS.
    case 0x449c6:ou8_branch(r,ou8_gt(ou8_tst(r.d[3])),0x449ca);return true; // TST.L D3; BGT 449be.
    case 0x449cc:ou8_branch(r,ou8_lt(ou8_tst(r.d[3])),0x449d0);return true; // TST.L D3; BLT 449be.
    case 0x449d2:ou8_branch(r,ou8_lt(ou8_tst(r.d[2])),0x449d6);return true; // TST.L D2; BLT 449be.
    case 0x449d8:ou8_branch(r,ou8_gt(ou8_tst(r.d[2])),0x449dc);return true; // TST.L D2; BGT 449be.
    // MOVE.L D2,D4; LSL.L #n,D4; CMP.L D4,D3 / ADD.L D3,D4; BGT/BLT 449be.
    case 0x449de:r.d[4]=ou8_scaled(r.d[2],2);ou8_branch(r,ou8_gt(ou8_cmp(r.d[3],r.d[4])),0x449e6);return true;
    case 0x449e8:r.d[4]=ou8_scaled(r.d[2],2);{const Ou8Flags f=ou8_add(r.d[4],r.d[3]);r.d[4]+=r.d[3];ou8_branch(r,ou8_gt(f),0x449f0);}return true;
    case 0x449f2:r.d[4]=ou8_scaled(r.d[2],2);{const Ou8Flags f=ou8_add(r.d[4],r.d[3]);r.d[4]+=r.d[3];ou8_branch(r,ou8_lt(f),0x449fa);}return true;
    case 0x449fc:r.d[4]=ou8_scaled(r.d[2],2);ou8_branch(r,ou8_lt(ou8_cmp(r.d[3],r.d[4])),0x44a04);return true;
    case 0x44a06:r.d[4]=ou8_scaled(r.d[2],1);ou8_branch(r,ou8_gt(ou8_cmp(r.d[3],r.d[4])),0x44a0e);return true;
    case 0x44a10:r.d[4]=ou8_scaled(r.d[2],1);{const Ou8Flags f=ou8_add(r.d[4],r.d[3]);r.d[4]+=r.d[3];ou8_branch(r,ou8_gt(f),0x44a18);}return true;
    case 0x44a1a:r.d[4]=ou8_scaled(r.d[2],1);{const Ou8Flags f=ou8_add(r.d[4],r.d[3]);r.d[4]+=r.d[3];ou8_branch(r,ou8_lt(f),0x44a22);}return true;
    case 0x44a24:r.d[4]=ou8_scaled(r.d[2],1);ou8_branch(r,ou8_lt(ou8_cmp(r.d[3],r.d[4])),0x44a2c);return true;
    case 0x44a2e:ou8_branch(r,ou8_gt(ou8_cmp(r.d[3],r.d[2])),0x44a32);return true; // CMP.L D2,D3; BGT 449be.
    case 0x44a34:r.d[4]=r.d[2];{const Ou8Flags f=ou8_add(r.d[4],r.d[3]);r.d[4]+=r.d[3];ou8_branch(r,ou8_gt(f),0x44a3a);}return true;
    case 0x44a3c:r.d[4]=r.d[2];{const Ou8Flags f=ou8_add(r.d[4],r.d[3]);r.d[4]+=r.d[3];ou8_branch(r,ou8_lt(f),0x44a44);}return true;
    case 0x44a46:ou8_branch(r,ou8_lt(ou8_cmp(r.d[3],r.d[2])),0x44a4c);return true; // CMP.L D2,D3; BLT 449be.
    // MOVE.L D3,D4; LSL.L #n,D4; CMP.L D2,D4 / ADD.L D2,D4; BGT/BLT 449be.
    case 0x44a4e:r.d[4]=ou8_scaled(r.d[3],1);ou8_branch(r,ou8_gt(ou8_cmp(r.d[4],r.d[2])),0x44a58);return true;
    case 0x44a5a:r.d[4]=ou8_scaled(r.d[3],1);{const Ou8Flags f=ou8_add(r.d[4],r.d[2]);r.d[4]+=r.d[2];ou8_branch(r,ou8_gt(f),0x44a64);}return true;
    case 0x44a66:r.d[4]=ou8_scaled(r.d[3],1);{const Ou8Flags f=ou8_add(r.d[4],r.d[2]);r.d[4]+=r.d[2];ou8_branch(r,ou8_lt(f),0x44a70);}return true;
    case 0x44a72:r.d[4]=ou8_scaled(r.d[3],1);ou8_branch(r,ou8_lt(ou8_cmp(r.d[4],r.d[2])),0x44a7c);return true;
    case 0x44a7e:r.d[4]=ou8_scaled(r.d[3],2);ou8_branch(r,ou8_gt(ou8_cmp(r.d[4],r.d[2])),0x44a88);return true;
    case 0x44a8a:r.d[4]=ou8_scaled(r.d[3],2);{const Ou8Flags f=ou8_add(r.d[4],r.d[2]);r.d[4]+=r.d[2];ou8_branch(r,ou8_gt(f),0x44a94);}return true;
    case 0x44a96:r.d[4]=ou8_scaled(r.d[3],2);{const Ou8Flags f=ou8_add(r.d[4],r.d[2]);r.d[4]+=r.d[2];ou8_branch(r,ou8_lt(f),0x44aa0);}return true;
    case 0x44aa2:r.d[4]=ou8_scaled(r.d[3],2);ou8_branch(r,ou8_lt(ou8_cmp(r.d[4],r.d[2])),0x44aac);return true;
    case 0x44aae:r.d[4]=ou8_scaled(r.d[3],3);ou8_branch(r,ou8_gt(ou8_cmp(r.d[4],r.d[2])),0x44ab8);return true;
    case 0x44aba:r.d[4]=ou8_scaled(r.d[3],3);{const Ou8Flags f=ou8_add(r.d[4],r.d[2]);r.d[4]+=r.d[2];ou8_branch(r,ou8_gt(f),0x44ac4);}return true;
    case 0x44ac6:r.d[4]=ou8_scaled(r.d[3],3);{const Ou8Flags f=ou8_add(r.d[4],r.d[2]);r.d[4]+=r.d[2];ou8_branch(r,ou8_lt(f),0x44ad0);}return true;
    case 0x44ad2:r.d[4]=ou8_scaled(r.d[3],3);ou8_branch(r,ou8_lt(ou8_cmp(r.d[4],r.d[2])),0x44adc);return true;

    // ---- 49274: MOVEM.L 2e(A6),D0-D3/A0; LEA 538e(A5),A1; JSR 43eb8.L.
    case 0x49274:
        for(unsigned int i=0;i<4;++i){if(!ou8_get(c,r.a[6],0x2eU+4U*i,4,value))return false;r.d[i]=value;}
        if(!ou8_get(c,r.a[6],0x3e,4,value))return false;r.a[0]=value;r.a[1]=am_index(r.a[5],0x538e);return am_call(c,0x43eb8,0x49284);
    // MOVEM.L D0-D3/A1,2e(A6); JMP 43e34.L.
    case 0x49284:
        for(unsigned int i=0;i<4;++i)if(!ou8_put(c,r.a[6],0x2eU+4U*i,4,r.d[i]))return false;
        if(!ou8_put(c,r.a[6],0x3e,4,r.a[1]))return false;r.pc=0x43e34;return true;
    // ---- 49290: MOVEA.L c(A6),A1; LEA 2e(A1),A1; JMP 43e04.L.
    case 0x49290:if(!ou8_get(c,r.a[6],0xc,4,value))return false;r.a[1]=value+0x2eU;r.pc=0x43e04;return true;
    default:
        // Table entries 4483e+4k: BRA.W to the transcribed target. The displacement WORDs are interior PCs.
        if(r.pc>=OU8_TABLE && r.pc<OU8_TABLE+4U*OU8_TABLE_ENTRIES && ((r.pc-OU8_TABLE)&3U)==0){
            r.pc=OU8_TARGETS[(r.pc-OU8_TABLE)>>2];return true;
        }
        return am_error(c,"unsupported animation objects u08 PC");
    }
}
}
