#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code.
const std::uint32_t OU12_BIT_COUNT=0x48f98;     // LEA 48f98(PC),A1 (490be): 256 BYTEs, fixed ROM, read through the live bus
const std::uint32_t OU12_TABLE_GAP=0xc8750;     // LEA c8750.L,A0 (7011a, passed to 490ba)
const std::uint32_t OU12_TABLE_TIMER=0xc868e;   // LEA c868e.L,A0 (7041e, passed to 490ba)
const std::uint32_t OU12_TABLE_DELAY=0xc85cc;   // LEA c85cc.L,A0 (70434, passed to 490ba)
const std::uint32_t OU12_PLAYER_ONE=0x8cb8;     // -7348(A5) (player node 1, d16 WORD)
const std::uint32_t OU12_PLAYER_TWO=0x8da8;     // -7258(A5) (player node 2, d16 WORD)
bool ou12_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou12_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
std::uint32_t ou12_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ou12_b(std::uint32_t value) {return value&255U;}
// Two's complement view of a WORD (explicit, no implementation-defined conversion).
bool ou12_word_negative(std::uint32_t value) {return (value&0x8000U)!=0;}
// BSET/BCLR #bit,d16(A6) (BYTE read-modify-write; Z only).
bool ou12_bset(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;
    return ou12_get(c,c.s.a[6],displacement,1,value) && ou12_put(c,c.s.a[6],displacement,1,(value|(1U<<bit))&255U);
}
bool ou12_bclr(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;
    return ou12_get(c,c.s.a[6],displacement,1,value) && ou12_put(c,c.s.a[6],displacement,1,value&~(1U<<bit)&255U);
}
// BTST.B #bit,d16(A6): true when the bit is set.
bool ou12_btst(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ou12_get(c,c.s.a[6],displacement,1,value))return false;set=((value>>bit)&1U)!=0;return true;
}
// ORI.W #bits,54aa(A5).
bool ou12_ori_54aa(AnimationMachineContext& c,std::uint32_t bits) {
    std::uint32_t value=0;
    return ou12_get(c,c.s.a[5],0x54aa,2,value) && ou12_put(c,c.s.a[5],0x54aa,2,(value|bits)&65535U);
}
// MOVE.W #160,D7; ORI.W #400,54aa(A5).
bool ou12_terrain_160(AnimationMachineContext& c,std::uint32_t next_pc) {
    am_word(c.s.d[7],0x160);if(!ou12_ori_54aa(c,0x400))return false;c.s.pc=next_pc;return true;
}
// SUB.L 14(A0),D0; SUB.L 18(A0),D1 (relative position to the node A0).
bool ou12_relative(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ou12_get(c,r.a[0],0x14,4,value))return false;r.d[0]-=value;
    if(!ou12_get(c,r.a[0],0x18,4,value))return false;r.d[1]-=value;return true;
}
// Bcc / Scc consuming the C returned by the previous callee.
bool ou12_known(AnimationMachineContext& c,bool& set) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects u12 caller requires known carry");
    set=c.s.carry==AnimationCarrySet;return true;
}
bool ou12_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    bool set=false;if(!ou12_known(c,set))return false;c.s.pc=set?set_pc:clear_pc;return true;
}
// N of the 49a58 tail SUB.W D0,(A3) (the only predecessor; A3 and that WORD are unchanged by its RTS): bit 15 of WORD (A3).
bool ou12_random_negative(AnimationMachineContext& c,bool& negative) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[3],2,value))return false;negative=ou12_word_negative(value);return true;
}
// MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L; RTS.
bool ou12_bank_return(AnimationMachineContext& c) {return am_zero_bank(c) && am_return(c);}
}
// Objects F4 U12 (162 block starts): the shared-core pieces 1abda (C returned), the terrain search 46d72 (C returned), the math
// helpers 49098 (two 289e C reads), 490ba (difficulty table pick with the BYTE table 48f98 and RNG 49a58, then the bank 0 reset),
// 492ae/492c8, the motion step 4c0ac, and 70418 with its tail 70054. The callees 45176 and 49370 (U11), 4bc04, 4c1de, 4c29a, 4c2cc
// (C returned), 6feb4, 70036 and ea5f0, and the TRAP #15 sites 4910c, 4913e and 49174 are boundaries without an executor here.
// 1abda/1abec and 46eda/46ee6 produce the returned C; 490a4/490b0 (SCS) consume the 289e C and 4c0c6/70502 (BCC) the 46d72/4c2cc C.
// 70198 (BPL) and 701cc (SMI) recompute the N of the 49a58 SUB.W D0,(A3) from the live A3 WORD. 49140/49196 write the three bank
// reset WORDs (port writes through am_write).
bool animation_objects_u12_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool flag=false;
    switch(r.pc) {
    // ---- 1abda: MOVE.W 542e(A5),D0; MOVE.W 5430(A5),D1; CMPI.W #ffff,D1; BEQ 1abec (C of the CMPI: D1.W <u ffff).
    case 0x1abda:
        if(!ou12_get(c,r.a[5],0x542e,2,value))return false;am_word(r.d[0],value);
        if(!ou12_get(c,r.a[5],0x5430,2,value))return false;am_word(r.d[1],value);
        r.carry=ou12_w(r.d[1])!=0xffffU?AnimationCarrySet:AnimationCarryClear;r.pc=ou12_w(r.d[1])==0xffffU?0x1abec:0x1abea;return true;
    case 0x1abea:case 0x46eea:case 0x492c6:case 0x4c0e8:case 0x7028c:return am_return(c); // RTS.
    // MOVE.W #210,D0; MOVE.W #20c,D1; ANDI.B #fe,CCR; RTS.
    case 0x1abec:am_word(r.d[0],0x210);am_word(r.d[1],0x20c);r.carry=AnimationCarryClear;return am_return(c);

    // ---- 46d72: MOVEM.L A0,54d4(A5); MOVE.L #160,54d8(A5); MOVEQ #0,D2; CMPA.W #0,A0; BSR 469a0.
    case 0x46d72:
        if(!ou12_put(c,r.a[5],0x54d4,4,r.a[0]) || !ou12_put(c,r.a[5],0x54d8,4,0x160))return false;r.d[2]=0;return am_call(c,0x469a0,0x46d8a);
    // NEG.L D3; MOVE.L D3,54d0(A5); MOVE.W #0,54aa(A5); MOVE.L #fff80000,D3; CMPA.W #0,A0; BEQ 46dac.
    case 0x46d8a:
        r.d[3]=(0U-r.d[3])&0xffffffffU;if(!ou12_put(c,r.a[5],0x54d0,4,r.d[3]) || !ou12_put(c,r.a[5],0x54aa,2,0))return false;
        r.d[3]=0xfff80000U;r.pc=r.a[0]==0U?0x46dac:0x46da4;return true;
    // ADD.L 14(A0),D0; ADD.L 18(A0),D1.
    case 0x46da4:
        if(!ou12_get(c,r.a[0],0x14,4,value))return false;r.d[0]+=value;
        if(!ou12_get(c,r.a[0],0x18,4,value))return false;r.d[1]+=value;r.pc=0x46dac;return true;
    // MOVEM.L D0-D1,54ba(A5); BSR 469ae.
    case 0x46dac:
        if(!ou12_put(c,r.a[5],0x54ba,4,r.d[0]) || !ou12_put(c,r.a[5],0x54be,4,r.d[1]))return false;return am_call(c,0x469ae,0x46db6);
    // SUBQ.W #4,A7; CMPA.W #0,A1; BEQ 46eba.
    case 0x46db6:r.a[7]-=4U;r.pc=r.a[1]==0U?0x46eba:0x46dc0;return true;
    // MOVEA.L A1,A0; SUB.L 14(A0),D0; SUB.L 18(A0),D1; MOVE.L #0,(A7); SWAP D0; SWAP D1; BSR 447be.
    case 0x46dc0:
        r.a[0]=r.a[1];if(!ou12_relative(c) || !am_write(c,r.a[7],4,0))return false;am_swap(r.d[0]);am_swap(r.d[1]);
        return am_call(c,0x447be,0x46dd8);
    // MOVE.W D7,54ae(A5); CMPI.W #178,D7; BEQ 46dea.
    case 0x46dd8:if(!ou12_put(c,r.a[5],0x54ae,2,ou12_w(r.d[7])))return false;r.pc=ou12_w(r.d[7])==0x178U?0x46dea:0x46de2;return true;
    case 0x46de2:r.pc=ou12_w(r.d[7])!=0x17cU?0x46df4:0x46dea;return true; // CMPI.W #17c,D7; BNE 46df4.
    case 0x46dea:return ou12_terrain_160(c,0x46df4);                   // MOVE.W #160,D7; ORI.W #400,54aa(A5).
    // MOVE.W D7,54b0(A5); MOVE.W D6,54b2(A5); CLR.B 54b4(A5); SWAP D0; SWAP D1; BSR 4483a.
    case 0x46df4:
        if(!ou12_put(c,r.a[5],0x54b0,2,ou12_w(r.d[7])) || !ou12_put(c,r.a[5],0x54b2,2,ou12_w(r.d[6])) || !ou12_put(c,r.a[5],0x54b4,1,0))
            return false;
        am_swap(r.d[0]);am_swap(r.d[1]);return am_call(c,0x4483a,0x46e08);
    case 0x46e08:case 0x46e6a:return am_call(c,0x45176,r.pc+4U);        // BSR 45176 (U11 boundary).
    case 0x46e0c:r.pc=(r.d[6]&0x80000000U)==0U?0x46e84:0x46e12;return true; // TST.L D6; BPL 46e84.
    // SUB.L D3,(A7); SWAP D0; SWAP D1; SUBQ.W #8,D1; BSR 447be.
    case 0x46e12:
        if(!am_read(c,r.a[7],4,value) || !am_write(c,r.a[7],4,(value-r.d[3])&0xffffffffU))return false;
        am_swap(r.d[0]);am_swap(r.d[1]);am_word(r.d[1],r.d[1]-8U);return am_call(c,0x447be,0x46e1e);
    // MOVE.W D6,54b2(A5); MOVE.W 54ae(A5),D4; MOVE.W D7,54ae(A5); CMPI.W #174,D4; BNE 46e3e.
    case 0x46e1e:
        if(!ou12_put(c,r.a[5],0x54b2,2,ou12_w(r.d[6])) || !ou12_get(c,r.a[5],0x54ae,2,value))return false;am_word(r.d[4],value);
        if(!ou12_put(c,r.a[5],0x54ae,2,ou12_w(r.d[7])))return false;r.pc=ou12_w(r.d[4])!=0x174U?0x46e3e:0x46e32;return true;
    case 0x46e32:r.pc=ou12_w(r.d[7])!=0x174U?0x46e3e:0x46e3a;return true; // CMPI.W #174,D7; BNE 46e3e.
    case 0x46e3a:am_word(r.d[7],0x160);r.pc=0x46e3e;return true;          // MOVE.W #160,D7.
    case 0x46e3e:r.pc=ou12_w(r.d[7])==0x178U?0x46e4c:0x46e44;return true; // CMPI.W #178,D7; BEQ 46e4c.
    case 0x46e44:r.pc=ou12_w(r.d[7])!=0x17cU?0x46e56:0x46e4c;return true; // CMPI.W #17c,D7; BNE 46e56.
    case 0x46e4c:return ou12_terrain_160(c,0x46e56);                   // MOVE.W #160,D7; ORI.W #400,54aa(A5).
    // MOVE.W D7,54b0(A5); SWAP D0; SWAP D1; CMPI.W #160,D7; BEQ 46e78.
    case 0x46e56:
        if(!ou12_put(c,r.a[5],0x54b0,2,ou12_w(r.d[7])))return false;am_swap(r.d[0]);am_swap(r.d[1]);
        r.pc=ou12_w(r.d[7])==0x160U?0x46e78:0x46e66;return true;
    case 0x46e66:return am_call(c,0x4483a,0x46e6a);                     // BSR 4483a (U08a table).
    case 0x46e6e:r.pc=r.d[6]!=0x80000000U?0x46e84:0x46e78;return true;  // CMPI.L #80000000,D6; BNE 46e84.
    // MOVE.L (A7),D4; CMP.L 54d0(A5),D4; BCS 46e12 (unsigned).
    case 0x46e78:
        if(!am_read(c,r.a[7],4,value))return false;r.d[4]=value;if(!ou12_get(c,r.a[5],0x54d0,4,value))return false;
        r.pc=r.d[4]<value?0x46e12:0x46e80;return true;
    case 0x46e80:r.pc=0x46ea8;return true;                              // BRA 46ea8.
    // ADD.L (A7),D6; CMP.L 54d0(A5),D6; BCC 46ea8 (unsigned).
    case 0x46e84:
        if(!am_read(c,r.a[7],4,value))return false;r.d[6]+=value;if(!ou12_get(c,r.a[5],0x54d0,4,value))return false;
        r.pc=r.d[6]>=value?0x46ea8:0x46e8e;return true;
    // ORI.W #1,54aa(A5); MOVE.L D6,54d0(A5); MOVE.L D7,54d8(A5); MOVEM.L A0,54d4(A5); MOVE.W 54b2(A5),54dc(A5).
    case 0x46e8e:
        if(!ou12_ori_54aa(c,1) || !ou12_put(c,r.a[5],0x54d0,4,r.d[6]) || !ou12_put(c,r.a[5],0x54d8,4,r.d[7]) ||
           !ou12_put(c,r.a[5],0x54d4,4,r.a[0]) || !ou12_get(c,r.a[5],0x54b2,2,value) || !ou12_put(c,r.a[5],0x54dc,2,value))return false;
        r.pc=0x46ea8;return true;
    // MOVEM.L 54ba(A5),D0-D1; BSR 469ae.
    case 0x46ea8:{
        std::uint32_t d1=0;if(!ou12_get(c,r.a[5],0x54ba,4,value) || !ou12_get(c,r.a[5],0x54be,4,d1))return false;
        r.d[0]=value;r.d[1]=d1;return am_call(c,0x469ae,0x46eb2);}
    case 0x46eb2:r.pc=r.a[1]!=0U?0x46dc0:0x46eba;return true;          // CMPA.W #0,A1; BNE 46dc0.
    // ADDQ.W #4,A7; MOVEA.L 54d4(A5),A0; CMPA.W #0,A0; BEQ 46ed0.
    case 0x46eba:
        r.a[7]+=4U;if(!ou12_get(c,r.a[5],0x54d4,4,value))return false;r.a[0]=value;r.pc=value==0U?0x46ed0:0x46ec8;return true;
    case 0x46ec8:if(!ou12_relative(c))return false;r.pc=0x46ed0;return true; // SUB.L 14(A0),D0; SUB.L 18(A0),D1.
    // MOVE.L 54d8(A5),D7; MOVE.W D7,D5; BSR 461ec.
    case 0x46ed0:
        if(!ou12_get(c,r.a[5],0x54d8,4,value))return false;r.d[7]=value;am_word(r.d[5],value);return am_call(c,0x461ec,0x46eda);
    // MOVE.L 54d0(A5),D6; MOVE.W 54aa(A5),D5; BEQ 46eea (MOVE clears C).
    case 0x46eda:
        if(!ou12_get(c,r.a[5],0x54d0,4,value))return false;r.d[6]=value;if(!ou12_get(c,r.a[5],0x54aa,2,value))return false;
        am_word(r.d[5],value);r.carry=AnimationCarryClear;r.pc=value==0U?0x46eea:0x46ee6;return true;
    case 0x46ee6:r.carry=AnimationCarrySet;r.pc=0x46eea;return true;    // ORI.B #1,CCR.

    // ---- 49098: MOVEQ #0,D7; LEA -7348(A5),A0; JSR 289e.L.
    case 0x49098:r.d[7]=0;r.a[0]=am_index(r.a[5],OU12_PLAYER_ONE);return am_call(c,0x289e,0x490a4);
    // SCS.B D0; LEA -7258(A5),A0; JSR 289e.L (C returned by 289e).
    case 0x490a4:
        if(!ou12_known(c,flag))return false;am_byte(r.d[0],flag?0xffU:0U);r.a[0]=am_index(r.a[5],OU12_PLAYER_TWO);
        return am_call(c,0x289e,0x490b0);
    // SCS.B D1; AND.B D0,D1; NEG.B D1; ADD.B D1,D7; RTS (C returned by 289e; the ADD.B leaves the C Unknown).
    case 0x490b0:
        if(!ou12_known(c,flag))return false;am_byte(r.d[1],flag?0xffU:0U);am_byte(r.d[1],r.d[1]&r.d[0]);am_byte(r.d[1],0U-ou12_b(r.d[1]));
        am_byte(r.d[7],r.d[7]+ou12_b(r.d[1]));r.carry=AnimationCarryUnknown;return am_return(c);
    // ---- 490ba: MOVE.L A0,-(A7); BSR 49098.
    case 0x490ba:if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x49098,0x490be);
    // MOVE.L (A7)+,D6; MOVEA.L D6,A0; LEA 48f98(PC),A1; MOVE.B (A0)+,D6; MOVEQ #0,D5; MOVE.B (A0)+,D5; MOVE.B 7d8b(A5),D1;
    // CMPI.B #2,-7fee(A5); BEQ 490dc.
    case 0x490be:
        if(!am_pop(c,4,value))return false;r.d[6]=value;r.a[0]=value;r.a[1]=OU12_BIT_COUNT;
        if(!am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;am_byte(r.d[6],value);
        r.d[5]=0;if(!am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;am_byte(r.d[5],value);
        if(!ou12_get(c,r.a[5],0x7d8b,1,value))return false;am_byte(r.d[1],value);
        if(!ou12_get(c,r.a[5],0x8012,1,value))return false;r.pc=value==2U?0x490dc:0x490da;return true;
    case 0x490da:r.d[1]=3;r.pc=0x490dc;return true;                     // MOVEQ #3,D1.
    case 0x490dc:r.pc=ou12_b(r.d[1])<7U?0x490f0:0x490e4;return true;     // CMPI.B #7,D1; BCS 490f0.
    case 0x490e4:r.pc=ou12_w(r.d[7])<2U?0x490f0:0x490ec;return true;     // CMPI.W #2,D7; BCS 490f0.
    case 0x490ec:am_byte(r.d[7],1);r.pc=0x490f0;return true;             // MOVE.B #1,D7.
    // MOVEQ #0,D2; ANDI.B #7,D1; ADDQ.B #1,D1; BSET.B D1,D2; SUBQ.W #1,D2; MOVE.W D5,D0; AND.W D2,D0; MOVE.B (A1,D0.W),D0;
    // CMPI.B #1,D0; BCC 4911a (unsigned; otherwise the TRAP #15 boundary 4910c).
    case 0x490f0:
        r.d[2]=0;am_byte(r.d[1],r.d[1]&7U);am_byte(r.d[1],r.d[1]+1U);r.d[2]|=1U<<(r.d[1]&31U);am_word(r.d[2],r.d[2]-1U);
        am_word(r.d[0],r.d[5]);am_word(r.d[0],r.d[0]&r.d[2]);if(!am_read(c,am_index(r.a[1],r.d[0]),1,value))return false;
        am_byte(r.d[0],value);r.pc=ou12_b(r.d[0])>=1U?0x4911a:0x4910c;return true;
    // SUBQ.B #1,D0; ADD.W D0,D0; ADD.W D7,D0; CMPI.B #2,D6; BEQ 49160.
    case 0x4911a:
        am_byte(r.d[0],r.d[0]-1U);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[7]);
        r.pc=ou12_b(r.d[6])==2U?0x49160:0x49128;return true;
    // ADD.W D0,D0; ADD.W D0,D0; MOVE.W D0,D1; ADD.W D0,D0; ADD.W D1,D0; MOVE.B 6a(A6),D1; CMPI.W #c,D1; BCS 49140
    // (unsigned; otherwise the TRAP #15 boundary 4913e).
    case 0x49128:
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[1],r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        am_word(r.d[0],r.d[0]+r.d[1]);if(!ou12_get(c,r.a[6],0x6a,1,value))return false;am_byte(r.d[1],value);
        r.pc=ou12_w(r.d[1])<0xcU?0x49140:0x4913e;return true;
    // ADD.W D1,D1; ADD.W D1,D0; ADDA.W D0,A0; MOVE.W (A0),D0; bank reset; RTS.
    case 0x49140:
        am_word(r.d[1],r.d[1]+r.d[1]);am_word(r.d[0],r.d[0]+r.d[1]);r.a[0]=am_index(r.a[0],r.d[0]);
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);return ou12_bank_return(c);
    // ADD.W D0,D0; MOVE.W D0,D1; ADD.W D0,D0; ADD.W D1,D0; MOVE.B 6a(A6),D1; CMPI.W #c,D1; BCS 49176
    // (unsigned; otherwise the TRAP #15 boundary 49174).
    case 0x49160:
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[1],r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[1]);
        if(!ou12_get(c,r.a[6],0x6a,1,value))return false;am_byte(r.d[1],value);r.pc=ou12_w(r.d[1])<0xcU?0x49176:0x49174;return true;
    // ADD.W D1,D0; MOVE.B (A0,D0.W),D0; LSL.W #4,D0; MOVE.B (A1,D5.W),D5; ADD.W D5,D5; MOVE.W D5,D1; ADD.W D5,D5; ADD.W D1,D5;
    // ADD.W D5,D5; ADD.W D5,D0; ADDA.W D0,A0; JSR 49a58.L.
    case 0x49176:
        am_word(r.d[0],r.d[0]+r.d[1]);if(!am_read(c,am_index(r.a[0],r.d[0]),1,value))return false;am_byte(r.d[0],value);
        am_word(r.d[0],r.d[0]<<4);if(!am_read(c,am_index(r.a[1],r.d[5]),1,value))return false;am_byte(r.d[5],value);
        am_word(r.d[5],r.d[5]+r.d[5]);am_word(r.d[1],r.d[5]);am_word(r.d[5],r.d[5]+r.d[5]);am_word(r.d[5],r.d[5]+r.d[1]);
        am_word(r.d[5],r.d[5]+r.d[5]);am_word(r.d[0],r.d[0]+r.d[5]);r.a[0]=am_index(r.a[0],r.d[0]);return am_call(c,0x49a58,0x49196);
    // ANDI.W #e,D0; MOVE.W (A0,D0.W),D0; bank reset; RTS.
    case 0x49196:
        am_word(r.d[0],r.d[0]&0xeU);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
        return ou12_bank_return(c);

    // ---- 492ae: MOVE.W 68(A6),D0; MOVE.W D0,D7; ANDI.W #f000,D7; CMPI.W #8000,D7; BNE 492c6.
    case 0x492ae:
        if(!ou12_get(c,r.a[6],0x68,2,value))return false;am_word(r.d[0],value);am_word(r.d[7],value&0xf000U);
        r.pc=ou12_w(r.d[7])!=0x8000U?0x492c6:0x492c0;return true;
    // MOVE.W 46(A6),D1; SUB.W D1,D0.
    case 0x492c0:
        if(!ou12_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],value);am_word(r.d[0],r.d[0]-r.d[1]);r.pc=0x492c6;return true;
    case 0x492c8:return am_call(c,0x492ae,0x492ca);                     // BSR 492ae.
    case 0x492ca:if(!ou12_put(c,r.a[6],0x1e,2,ou12_w(r.d[0])))return false;return am_return(c); // MOVE.W D0,1e(A6); RTS.

    // ---- 4c0ac: JSR 4bc44(PC) (U08b).
    case 0x4c0ac:return am_call(c,0x4bc44,0x4c0b0);
    // MOVEM.L 2e(A6),D0-D1; MOVEA.L 3e(A6),A0; MOVE.L #ff000000,D3; JSR 46d72.L.
    case 0x4c0b0:{
        std::uint32_t d1=0;if(!ou12_get(c,r.a[6],0x2e,4,value) || !ou12_get(c,r.a[6],0x32,4,d1))return false;r.d[0]=value;r.d[1]=d1;
        if(!ou12_get(c,r.a[6],0x3e,4,value))return false;r.a[0]=value;r.d[3]=0xff000000U;return am_call(c,0x46d72,0x4c0c6);}
    case 0x4c0c6:return ou12_carry(c,0x4c0d2,0x4c0ca);                  // BCC 4c0d2 (C returned by 46d72).
    // SUB.L D6,D1; BSET.B #7,15(A6).
    case 0x4c0ca:r.d[1]-=r.d[6];if(!ou12_bset(c,0x15,7))return false;r.pc=0x4c0d2;return true;
    // LSR.L #8,D7; MOVE.W D7,6e(A6); MOVEQ #0,D2; MOVEQ #0,D3; MOVEM.L D0-D3/A0,2e(A6); JSR 43e34.L.
    case 0x4c0d2:
        r.d[7]>>=8;if(!ou12_put(c,r.a[6],0x6e,2,ou12_w(r.d[7])))return false;r.d[2]=0;r.d[3]=0;
        for(unsigned int i=0;i<4;++i)if(!ou12_put(c,r.a[6],0x2eU+4U*i,4,r.d[i]))return false;
        if(!ou12_put(c,r.a[6],0x3e,4,r.a[0]))return false;return am_call(c,0x43e34,0x4c0e8);

    // ---- 70054: JSR 49370.L (U11 boundary).
    case 0x70054:return am_call(c,0x49370,0x7005a);
    case 0x7005a:r.pc=ou12_b(r.d[0])!=0U?0x7006e:0x70060;return true;   // TST.B D0; BNE 7006e.
    // MOVE.B #ff,86(A6); MOVEA.W #0,A0; BRA 7010c.
    case 0x70060:if(!ou12_put(c,r.a[6],0x86,1,0xff))return false;r.a[0]=0;r.pc=0x7010c;return true;
    case 0x7006e:r.pc=ou12_b(r.d[0])!=1U?0x70084:0x70076;return true;   // CMPI.B #1,D0; BNE 70084.
    // MOVE.B #0,86(A6); LEA -7348(A5),A0; BRA 700ea.
    case 0x70076:if(!ou12_put(c,r.a[6],0x86,1,0))return false;r.a[0]=am_index(r.a[5],OU12_PLAYER_ONE);r.pc=0x700ea;return true;
    case 0x70084:r.pc=ou12_b(r.d[0])!=2U?0x7009a:0x7008c;return true;   // CMPI.B #2,D0; BNE 7009a.
    // MOVE.B #1,86(A6); LEA -7258(A5),A0; BRA 700ea.
    case 0x7008c:if(!ou12_put(c,r.a[6],0x86,1,1))return false;r.a[0]=am_index(r.a[5],OU12_PLAYER_TWO);r.pc=0x700ea;return true;
    // LEA -7348(A5),A0; LEA -7258(A5),A1; MOVE.W 42(A0),D0; MOVE.W 42(A1),D1; MOVE.W 42(A6),D2; SUB.W D2,D0; BPL 700b6.
    case 0x7009a:
        r.a[0]=am_index(r.a[5],OU12_PLAYER_ONE);r.a[1]=am_index(r.a[5],OU12_PLAYER_TWO);
        if(!ou12_get(c,r.a[0],0x42,2,value))return false;am_word(r.d[0],value);
        if(!ou12_get(c,r.a[1],0x42,2,value))return false;am_word(r.d[1],value);
        if(!ou12_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[2],value);
        am_word(r.d[0],r.d[0]-r.d[2]);r.pc=ou12_word_negative(r.d[0])?0x700b4:0x700b6;return true;
    case 0x700b4:am_word(r.d[0],0U-ou12_w(r.d[0]));r.pc=0x700b6;return true; // NEG.W D0.
    case 0x700b6:am_word(r.d[1],r.d[1]-r.d[2]);r.pc=ou12_word_negative(r.d[1])?0x700bc:0x700be;return true; // SUB.W D2,D1; BPL 700be.
    case 0x700bc:am_word(r.d[1],0U-ou12_w(r.d[1]));r.pc=0x700be;return true; // NEG.W D1.
    case 0x700be:if(!ou12_get(c,r.a[6],0x86,1,value))return false;r.pc=value!=0U?0x700ce:0x700c6;return true; // TST.B 86(A6); BNE 700ce.
    // LSR.W #2,D0; LSL.W #4,D1; BRA 700d2.
    case 0x700c6:am_word(r.d[0],ou12_w(r.d[0])>>2);am_word(r.d[1],r.d[1]<<4);r.pc=0x700d2;return true;
    // LSL.W #4,D0; LSR.W #2,D1.
    case 0x700ce:am_word(r.d[0],r.d[0]<<4);am_word(r.d[1],ou12_w(r.d[1])>>2);r.pc=0x700d2;return true;
    case 0x700d2:am_word(r.d[0],r.d[0]+r.d[1]);return am_call(c,0x49a84,0x700da); // ADD.W D1,D0; JSR 49a84.L.
    // MOVEQ #0,D7; CMP.W D0,D1; BCC 700e6 (unsigned D1.W >= D0.W).
    case 0x700da:r.d[7]=0;r.pc=ou12_w(r.d[1])>=ou12_w(r.d[0])?0x700e6:0x700e2;return true;
    case 0x700e2:r.a[0]=r.a[1];r.d[7]=1;r.pc=0x700e6;return true;       // MOVEA.L A1,A0; MOVEQ #1,D7.
    case 0x700e6:if(!ou12_put(c,r.a[6],0x86,1,ou12_b(r.d[7])))return false;r.pc=0x700ea;return true; // MOVE.B D7,86(A6).
    // CLR.B 82(A6); MOVE.W 42(A0),D0; CMP.W 42(A6),D0; SPL.B D0; BTST.B #0,15(A6); SNE.B D1; EOR.B D0,D1; BMI 7010c.
    case 0x700ea:
        if(!ou12_put(c,r.a[6],0x82,1,0) || !ou12_get(c,r.a[0],0x42,2,value))return false;am_word(r.d[0],value);
        if(!ou12_get(c,r.a[6],0x42,2,value))return false;am_byte(r.d[0],ou12_word_negative(r.d[0]-value)?0U:0xffU);
        if(!ou12_btst(c,0x15,0,flag))return false;am_byte(r.d[1],flag?0xffU:0U);am_byte(r.d[1],r.d[1]^r.d[0]);
        r.pc=(r.d[1]&0x80U)!=0U?0x7010c:0x70106;return true;
    case 0x70106:if(!ou12_bset(c,0x82,0))return false;r.pc=0x7010c;return true; // BSET.B #0,82(A6).
    case 0x7010c:if(!ou12_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);r.pc=value==0U?0x7011a:0x70114;return true;
    // SUBQ.W #1,D0; MOVE.W D0,78(A6).
    case 0x70114:am_word(r.d[0],r.d[0]-1U);if(!ou12_put(c,r.a[6],0x78,2,ou12_w(r.d[0])))return false;r.pc=0x7011a;return true;
    case 0x7011a:r.a[0]=OU12_TABLE_GAP;return am_call(c,0x490ba,0x70126); // LEA c8750.L,A0; JSR 490ba.L.
    case 0x70126:am_word(r.d[1],r.d[0]);return am_call(c,0x49a58,0x7012e); // MOVE.W D0,D1; JSR 49a58.L.
    // MOVE.W D0,D7; ANDI.W #ff,D0; CMP.W D1,D0; BCC 70172 (unsigned).
    case 0x7012e:am_word(r.d[7],r.d[0]);am_word(r.d[0],r.d[0]&0xffU);r.pc=ou12_w(r.d[0])>=ou12_w(r.d[1])?0x70172:0x7013a;return true;
    // LSR.W #8,D7; CMP.W D1,D7; BCC 70172 (unsigned).
    case 0x7013a:am_word(r.d[7],ou12_w(r.d[7])>>8);r.pc=ou12_w(r.d[7])>=ou12_w(r.d[1])?0x70172:0x70142;return true;
    // BSET.B #1,82(A6); MOVE.W #30,D0; BTST.B #0,15(A6); BNE 70158.
    case 0x70142:
        if(!ou12_bset(c,0x82,1))return false;am_word(r.d[0],0x30);if(!ou12_btst(c,0x15,0,flag))return false;
        r.pc=flag?0x70158:0x70156;return true;
    case 0x70156:case 0x70268:am_word(r.d[0],0U-ou12_w(r.d[0]));r.pc=r.pc+2U;return true; // NEG.W D0.
    // ADD.W 42(A6),D0; MOVE.W 46(A6),D1; MOVE.W D0,-(A7); MOVE.W D1,-(A7); JSR 4bc04.L (boundary).
    case 0x70158:
        if(!ou12_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!ou12_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],value);
        if(!am_push(c,2,ou12_w(r.d[0])) || !am_push(c,2,ou12_w(r.d[1])))return false;return am_call(c,0x4bc04,0x7016a);
    // MOVE.W (A7)+,D3; MOVE.W (A7)+,D2; BSR 70036 (boundary).
    case 0x7016a:
        if(!am_pop(c,2,value))return false;am_word(r.d[3],value);if(!am_pop(c,2,value))return false;am_word(r.d[2],value);
        return am_call(c,0x70036,0x70172);
    case 0x70172:if(!ou12_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.pc=value==0U?0x701b8:0x7017a;return true;
    case 0x7017a:r.pc=ou12_w(r.d[0])!=1U?0x70192:0x70182;return true;   // CMPI.W #1,D0; BNE 70192.
    // BSET.B #4,61(A6); BSET.B #5,61(A6); BRA 701b8.
    case 0x70182:if(!ou12_bset(c,0x61,4) || !ou12_bset(c,0x61,5))return false;r.pc=0x701b8;return true;
    case 0x70192:case 0x701c6:return am_call(c,0x49a58,r.pc+6U); // JSR 49a58.L.
    // BPL 701ac (N of the 49a58 SUB.W D0,(A3), recomputed from the live A3 WORD).
    case 0x70198:if(!ou12_random_negative(c,flag))return false;r.pc=flag?0x7019c:0x701ac;return true;
    // BCLR.B #5,61(A6); BSET.B #4,61(A6); BRA 701b8.
    case 0x7019c:if(!ou12_bclr(c,0x61,5) || !ou12_bset(c,0x61,4))return false;r.pc=0x701b8;return true;
    // BSET.B #5,61(A6); BCLR.B #4,61(A6).
    case 0x701ac:if(!ou12_bset(c,0x61,5) || !ou12_bclr(c,0x61,4))return false;r.pc=0x701b8;return true;
    case 0x701b8:if(!ou12_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[0],value);r.pc=value==0U?0x701c6:0x701c0;return true;
    // SUBQ.W #1,D0; MOVE.W D0,7c(A6).
    case 0x701c0:am_word(r.d[0],r.d[0]-1U);if(!ou12_put(c,r.a[6],0x7c,2,ou12_w(r.d[0])))return false;r.pc=0x701c6;return true;
    // SMI.B 83(A6) (N of the 49a58 SUB.W D0,(A3), recomputed from the live A3 WORD); BCLR.B #3,82(A6); MOVE.W 42(A6),D0;
    // SUBI.W #20,D0; CMPI.W #100,D0; BCC 701f8 (unsigned).
    case 0x701cc:
        if(!ou12_random_negative(c,flag) || !ou12_put(c,r.a[6],0x83,1,flag?0xffU:0U) || !ou12_bclr(c,0x82,3) ||
           !ou12_get(c,r.a[6],0x42,2,value))return false;
        am_word(r.d[0],value-0x20U);r.pc=ou12_w(r.d[0])>=0x100U?0x701f8:0x701e6;return true;
    // MOVE.W 46(A6),D0; SUBI.W #20,D0; CMPI.W #c0,D0 (result unused); BSET.B #3,82(A6).
    case 0x701e6:
        if(!ou12_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],value-0x20U);if(!ou12_bset(c,0x82,3))return false;
        r.pc=0x701f8;return true;
    case 0x701f8:if(!ou12_get(c,r.a[6],0x9a,2,value))return false;am_word(r.d[7],value);r.pc=value==0U?0x7020c:0x70200;return true;
    // ASR.W #6,D7; BNE 70208 (sign fill of the WORD).
    case 0x70200:
        value=ou12_w(r.d[7]);value=(value>>6)|(ou12_word_negative(value)?0xfc00U:0U);am_word(r.d[7],value);
        r.pc=value!=0U?0x70208:0x70206;return true;
    case 0x70206:r.d[7]=1;r.pc=0x70208;return true;                     // MOVEQ #1,D7.
    case 0x70208:                                                       // SUB.W D7,9a(A6).
        if(!ou12_get(c,r.a[6],0x9a,2,value) || !ou12_put(c,r.a[6],0x9a,2,(value-r.d[7])&65535U))return false;r.pc=0x7020c;return true;
    // MOVEQ #0,D0; MOVE.W #20,D1; MOVE.W #10,D2; MOVE.W #24,D3; BTST.B #0,15(A6); BNE 70226.
    case 0x7020c:
        r.d[0]=0;am_word(r.d[1],0x20);am_word(r.d[2],0x10);am_word(r.d[3],0x24);if(!ou12_btst(c,0x15,0,flag))return false;
        r.pc=flag?0x70226:0x70224;return true;
    case 0x70224:am_word(r.d[2],0U-ou12_w(r.d[2]));r.pc=0x70226;return true; // NEG.W D2.
    case 0x70226:return am_call(c,0x4c29a,0x7022c);                     // JSR 4c29a.L (boundary).
    case 0x7022c:r.pc=(r.d[6]&8U)==0U?0x7023e:0x70234;return true;      // BTST.B #3,D6; BEQ 7023e.
    case 0x70234:if(!ou12_bset(c,0x82,1))return false;r.pc=0x7025a;return true; // BSET.B #1,82(A6); BRA 7025a.
    case 0x7023e:r.pc=(r.d[6]&0x40U)==0U?0x7024c:0x70246;return true;   // BTST.B #6,D6; BEQ 7024c.
    case 0x70246:if(!ou12_bset(c,0x82,4))return false;r.pc=0x7024c;return true; // BSET.B #4,82(A6).
    case 0x7024c:r.pc=(r.d[6]&4U)==0U?0x7025a:0x70254;return true;      // BTST.B #2,D6; BEQ 7025a.
    case 0x70254:if(!ou12_bset(c,0x82,5))return false;r.pc=0x7025a;return true; // BSET.B #5,82(A6).
    // MOVE.W #8,D0; BTST.B #0,15(A6); BNE 7026a.
    case 0x7025a:am_word(r.d[0],8);if(!ou12_btst(c,0x15,0,flag))return false;r.pc=flag?0x7026a:0x70268;return true;
    case 0x7026a:return am_call(c,0x4c1de,0x70270);                     // JSR 4c1de.L (boundary).
    case 0x70270:r.pc=(r.d[6]&4U)==0U?0x7027e:0x70278;return true;      // BTST.B #2,D6; BEQ 7027e.
    case 0x70278:if(!ou12_bset(c,0x82,2))return false;r.pc=0x7027e;return true; // BSET.B #2,82(A6).
    case 0x7027e:r.pc=(r.d[6]&1U)!=0U?0x7028c:0x70286;return true;      // BTST.B #0,D6; BNE 7028c.
    case 0x70286:if(!ou12_bset(c,0x82,7))return false;r.pc=0x7028c;return true; // BSET.B #7,82(A6).

    // ---- 70418: JSR ea5f0.L (boundary).
    case 0x70418:return am_call(c,0xea5f0,0x7041e);
    case 0x7041e:r.a[0]=OU12_TABLE_TIMER;return am_call(c,0x490ba,0x7042a); // LEA c868e.L,A0; JSR 490ba.L.
    case 0x7042a:if(!ou12_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[1],value);r.pc=value==0U?0x70434:0x70432;return true;
    case 0x70432:r.d[0]=ou12_w(r.d[0])*ou12_w(r.d[1]);r.pc=0x70434;return true; // MULU.W D1,D0.
    // LSR.L #8,D0; MOVE.W D0,78(A6); LEA c85cc.L,A0; JSR 490ba.L.
    case 0x70434:
        r.d[0]>>=8;if(!ou12_put(c,r.a[6],0x78,2,ou12_w(r.d[0])))return false;r.a[0]=OU12_TABLE_DELAY;return am_call(c,0x490ba,0x70446);
    case 0x70446:if(!ou12_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[1],value);r.pc=value!=0U?0x70452:0x7044e;return true;
    case 0x7044e:am_word(r.d[1],0x1e);r.pc=0x70452;return true;          // MOVE.W #1e,D1.
    // MULU.W D1,D0; LSR.L #8,D0; MOVE.W D0,7a(A6); JSR 49a58.L.
    case 0x70452:
        r.d[0]=ou12_w(r.d[0])*ou12_w(r.d[1]);r.d[0]>>=8;if(!ou12_put(c,r.a[6],0x7a,2,ou12_w(r.d[0])))return false;
        return am_call(c,0x49a58,0x70460);
    // ANDI.W #7,D0; ADD.W D0,7a(A6); TST.W 7c(A6); BNE 70476.
    case 0x70460:
        am_word(r.d[0],r.d[0]&7U);if(!ou12_get(c,r.a[6],0x7a,2,value) || !ou12_put(c,r.a[6],0x7a,2,(value+r.d[0])&65535U) ||
           !ou12_get(c,r.a[6],0x7c,2,value))return false;
        r.pc=value!=0U?0x70476:0x70470;return true;
    case 0x70470:if(!ou12_put(c,r.a[6],0x7c,2,0x5a))return false;r.pc=0x70476;return true; // MOVE.W #5a,7c(A6).
    case 0x70476:return am_call(c,0x8ff4,0x7047c);                      // JSR 8ff4.L (cleanup).
    case 0x7047c:if(!ou12_get(c,r.a[6],0x9c,2,value))return false;r.pc=value!=0U?0x7049a:0x70484;return true; // TST.W 9c(A6); BNE.
    // MOVE.W #33/#34,D0; MOVE.W #3,D1; MOVE.B #0,D2; JSR c6a96.L (U05).
    case 0x70484:am_word(r.d[0],0x33);am_word(r.d[1],3);am_byte(r.d[2],0);return am_call(c,0xc6a96,0x70496);
    case 0x7049a:am_word(r.d[0],0x34);am_word(r.d[1],3);am_byte(r.d[2],0);return am_call(c,0xc6a96,0x704ac);
    case 0x70496:r.pc=0x704ac;return true;                              // BRA 704ac.
    // MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVE.W 7e(A6),D0; BEQ 704fa.
    case 0x704ac:
        if(!ou12_put(c,r.a[6],0x68,2,0x8820) || !ou12_put(c,r.a[6],0x1e,2,0x8820) || !ou12_get(c,r.a[6],0x7e,2,value))return false;
        am_word(r.d[0],value);r.pc=value==0U?0x704fa:0x704c0;return true;
    case 0x704c0:r.pc=ou12_w(r.d[0])==0xeU?0x704fa:0x704c8;return true; // CMPI.W #e,D0; BEQ 704fa.
    case 0x704c8:r.pc=ou12_w(r.d[0])==0xfU?0x704fa:0x704d0;return true; // CMPI.W #f,D0; BEQ 704fa.
    case 0x704d0:r.pc=ou12_w(r.d[0])==3U?0x704fa:0x704d8;return true;   // CMPI.W #3,D0; BEQ 704fa.
    case 0x704d8:r.pc=ou12_w(r.d[0])==6U?0x704fa:0x704e0;return true;   // CMPI.W #6,D0; BEQ 704fa.
    case 0x704e0:r.pc=ou12_w(r.d[0])==8U?0x704fa:0x704e8;return true;   // CMPI.W #8,D0; BEQ 704fa.
    case 0x704e8:r.pc=ou12_w(r.d[0])==0xaU?0x704fa:0x704f0;return true; // CMPI.W #a,D0; BEQ 704fa.
    case 0x704f0:return am_call(c,0x4c0ac,0x704f6);                     // JSR 4c0ac.L.
    case 0x704f6:r.pc=0x70512;return true;                              // BRA 70512.
    case 0x704fa:r.d[0]=0xffffffffU;return am_call(c,0x4c2cc,0x70502);  // MOVEQ #ff,D0; JSR 4c2cc.L (boundary, C returned).
    case 0x70502:return ou12_carry(c,0x7050c,0x70506);                  // BCC 7050c (C returned by 4c2cc).
    case 0x70506:if(!ou12_bset(c,0x15,7))return false;r.pc=0x7050c;return true; // BSET.B #7,15(A6).
    case 0x7050c:am_swap(r.d[7]);if(!ou12_put(c,r.a[6],0x6e,1,ou12_b(r.d[7])))return false;r.pc=0x70512;return true; // SWAP D7; MOVE.B D7,6e(A6).
    case 0x70512:return am_call(c,0x43e34,0x70518);                     // JSR 43e34.L (cleanup).
    // CMPI.W #a0,42(A6); BPL 70528 (sign of WORD 42 - a0).
    case 0x70518:if(!ou12_get(c,r.a[6],0x42,2,value))return false;r.pc=ou12_word_negative(value-0xa0U)?0x70522:0x70528;return true;
    case 0x70522:if(!ou12_bset(c,0x15,0))return false;r.pc=0x70528;return true; // BSET.B #0,15(A6).
    // MOVE.W 42(A6),D0; SUBI.W #a0,D0; ASR.W #2,D0; ADDI.W #a0,D0; MOVE.W D0,8e(A6); JSR 49a58.L.
    case 0x70528:
        if(!ou12_get(c,r.a[6],0x42,2,value))return false;value=(value-0xa0U)&65535U;value=(value>>2)|(ou12_word_negative(value)?0xc000U:0U);
        am_word(r.d[0],value+0xa0U);if(!ou12_put(c,r.a[6],0x8e,2,ou12_w(r.d[0])))return false;return am_call(c,0x49a58,0x70540);
    // MOVE.W D0,90(A6); BSR 6feb4 (boundary).
    case 0x70540:if(!ou12_put(c,r.a[6],0x90,2,ou12_w(r.d[0])))return false;return am_call(c,0x6feb4,0x70548);
    case 0x70548:r.pc=0x70054;return true;                              // BRA 70054.
    default:return am_error(c,"unsupported animation objects u12 PC");
    }
}
}
