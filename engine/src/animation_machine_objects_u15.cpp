#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OU15_FRAME_HEIGHT=0x54b2;   // WORD 54b2(A5): the 447be height D6.W.
const std::uint32_t OU15_LAST_CODE=0x54ae;      // WORD 54ae(A5): the previous 447be terrain code.
const std::uint32_t OU15_CODE=0x54b0;           // WORD 54b0(A5): the stored terrain code.
const std::uint32_t OU15_STATE=0x54aa;          // WORD 54aa(A5): terrain state bits (ORI.W #40 / #400).
const std::uint32_t OU15_GROUND=0x54b4;         // BYTE 54b4(A5): ground flag (ff / 0).
const std::uint32_t OU15_FRACTION=0x7ffff;      // ANDI.L #7ffff (the fraction mask of the terrain coordinate).
bool ou15_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou15_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Signed LONG a <= b (CMP.L b,a; BLE) without a signed conversion.
bool ou15_long_le(std::uint32_t a,std::uint32_t b) {return (a^0x80000000U)<=(b^0x80000000U);}
// Signed WORD a >= b (CMP.W b,a; BGE) and a <= b (BLE) of the low WORDs.
bool ou15_word_ge(std::uint32_t a,std::uint32_t b) {return ((a^0x8000U)&65535U)>=((b^0x8000U)&65535U);}
bool ou15_word_le(std::uint32_t a,std::uint32_t b) {return ((a^0x8000U)&65535U)<=((b^0x8000U)&65535U);}
// V of the LONG addition a+b=r and of the LONG subtraction a-b=r.
bool ou15_add_overflow(std::uint32_t a,std::uint32_t b,std::uint32_t r) {return ((~(a^b))&(a^r)&0x80000000U)!=0;}
bool ou15_sub_overflow(std::uint32_t a,std::uint32_t b,std::uint32_t r) {return ((a^b)&(a^r)&0x80000000U)!=0;}
// BSET.B #bit,d(A6) (only Z, not modeled further).
bool ou15_bset(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;if(!ou15_get(c,c.s.a[6],displacement,1,value))return false;
    return ou15_put(c,c.s.a[6],displacement,1,value|(1U<<bit));
}
// ORI.W #bits,54aa(A5).
bool ou15_state_or(AnimationMachineContext& c,std::uint32_t bits) {
    std::uint32_t value=0;if(!ou15_get(c,c.s.a[5],OU15_STATE,2,value))return false;
    return ou15_put(c,c.s.a[5],OU15_STATE,2,value|bits);
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool ou15_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u15 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// ANDI.B #fe,CCR / ORI.B #1,CCR; RTS (known C returned to the caller).
bool ou15_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {c.s.carry=carry;return am_return(c);}
// MOVEA.L c(A6),A0; SUBQ.B #1,62(A0); JMP 2a00.L (parent count decrement, fade_card self-delete).
bool ou15_release(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ou15_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
    if(!ou15_get(c,r.a[0],0x62,1,value) || !ou15_put(c,r.a[0],0x62,1,(value-1U)&255U))return false;
    r.pc=0x2a00;return true;
}
// MOVE.L #callback,(A6); RTS.
bool ou15_install_return(AnimationMachineContext& c,std::uint32_t callback) {
    if(!am_write(c,c.s.a[6],4,callback))return false;return am_return(c);
}
// MOVE.W D0,d(A6); LEA table.L,A0; JSR 490ba.L.
bool ou15_store_math(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t table,std::uint32_t return_pc) {
    if(!ou15_put(c,c.s.a[6],displacement,2,c.s.d[0]&65535U))return false;c.s.a[0]=table;return am_call(c,0x490ba,return_pc);
}
// MOVE.B D0,a1(A6); MOVE.B D0,a0(A6); JSR b0206(PC).
bool ou15_side_check(AnimationMachineContext& c,std::uint32_t return_pc) {
    const std::uint32_t v=c.s.d[0]&255U;
    if(!ou15_put(c,c.s.a[6],0xa1,1,v) || !ou15_put(c,c.s.a[6],0xa0,1,v))return false;return am_call(c,0xb0206,return_pc);
}
// MOVEA.L #child,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.L (child created under the node 100bf4).
bool ou15_spawn_under(AnimationMachineContext& c,std::uint32_t child,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],0x14);c.s.a[1]=0x100bf4;return am_call(c,0x2986,return_pc);
}
// MOVE.W D6,54b2(A5); MOVE.W 54ae(A5),D4; MOVE.W D7,54ae(A5); CMPI.W #174,D4; BNE.W next.
bool ou15_land_store(AnimationMachineContext& c,std::uint32_t ne_pc,std::uint32_t eq_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ou15_put(c,r.a[5],OU15_FRAME_HEIGHT,2,r.d[6]&65535U) || !ou15_get(c,r.a[5],OU15_LAST_CODE,2,value))return false;
    am_word(r.d[4],value);if(!ou15_put(c,r.a[5],OU15_LAST_CODE,2,r.d[7]&65535U))return false;
    r.pc=(r.d[4]&65535U)!=0x174U?ne_pc:eq_pc;return true;
}
// MOVE.W #160,D7; ORI.W #400,54aa(A5).
bool ou15_land_reset(AnimationMachineContext& c,std::uint32_t next_pc) {
    am_word(c.s.d[7],0x160);if(!ou15_state_or(c,0x400))return false;c.s.pc=next_pc;return true;
}
// MOVE.W D7,54b0(A5); SWAP D0; SWAP D1; MOVEQ #0,D4.
bool ou15_land_save(AnimationMachineContext& c,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;if(!ou15_put(c,r.a[5],OU15_CODE,2,r.d[7]&65535U))return false;
    am_swap(r.d[0]);am_swap(r.d[1]);r.d[4]=0;r.pc=next_pc;return true;
}
// MOVE.L D1,D4; ANDI.L #7ffff,D4; SUB.L D6,D1; SUB.L D6,D4; SWAP D4; SUBQ.W #8,D4; BCS.W below.
void ou15_rise(AnimationMachineState& r,std::uint32_t below_pc,std::uint32_t next_pc) {
    r.d[4]=r.d[1]&OU15_FRACTION;r.d[1]-=r.d[6];r.d[4]-=r.d[6];am_swap(r.d[4]);
    const std::uint32_t w=r.d[4]&65535U;am_word(r.d[4],w-8U);r.pc=w<8U?below_pc:next_pc;
}
}
// Objects F4 U15a (175 block starts; U15b 4578a/45798 table and U15c 45b1a/45b28 table are separate units): the terrain driver
// 4662e (U11 45176, U08a 4483a/447be; the U15b 45afe and U15c 45b1a calls are boundaries), C3 4950e (U11 49370, 49a58) with its C,
// C4 4c1de (U08b 4bc44, U09 469d8 in 8-unit steps) with its C and 4c29a, the callbacks af078/af146 with the installed callback af1e4,
// the child callbacks af3de af3f8 af3fe and the shared tail b05be, b0062/b00da. Calls into existing executors: U05 c6a96/1ab02, U12
// 490ba/4c0ac, interpreter 49f8c/49fc6, U08a 49274, cleanup 43e34/287e, fade_card 2986/28ae/2a00, U01 4b54e, U02 8ebe. Boundaries:
// U16 b0106 b0206 b02c8, 491fe 49214 4b702 d3c2a. af150 af27a af2e6 af42a af452 af4c4 b05ca consume a callee C; 49542 4c260 return
// C Clear and 49548 4c25a C Set. U15a reads/writes work RAM only (no table, no bank data, no port).
bool animation_objects_u15_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 4662e: TST.L D3; BNE.W 46638.
    case 0x4662e:r.pc=r.d[3]!=0U?0x46638:0x46634;return true;
    case 0x46634:r.d[6]=0;return am_return(c);                                      // MOVEQ #0,D6; RTS.
    // SUB.L D6,D3; ORI.W #40,54aa(A5); CLR.B 54b4(A5); MOVEQ #0,D6; RTS.
    case 0x46822:
        r.d[3]-=r.d[6];if(!ou15_state_or(c,0x40) || !ou15_put(c,r.a[5],OU15_GROUND,1,0))return false;r.d[6]=0;return am_return(c);
    // SUB.L D5,D3; CLR.B 54b4(A5); MOVEQ #0,D6; RTS.
    case 0x46832:r.d[3]-=r.d[5];if(!ou15_put(c,r.a[5],OU15_GROUND,1,0))return false;r.d[6]=0;return am_return(c);
    case 0x46638:r.pc=(r.d[7]&65535U)==0x160U?0x46694:0x46640;return true;          // CMPI.W #160,D7; BEQ.W 46694.
    case 0x46640:return am_call(c,0x45176,0x46644);                                 // BSR.W 45176.
    case 0x46644:r.d[6]-=0x80000000U;r.pc=r.d[6]==0U?0x46694:0x4664e;return true;   // SUBI.L #80000000,D6; BEQ.W 46694.
    // ADD.L D3,D6; BVC.W 46694.
    case 0x4664e:{const std::uint32_t a=r.d[6];r.d[6]=a+r.d[3];r.pc=ou15_add_overflow(a,r.d[3],r.d[6])?0x46654:0x46694;return true;}
    // ADDI.L #80000000,D6 (X = carry out); SUBX.L D4,D4; SUB.L D4,D6; SUB.L D6,D3; EXG.L D3,D6; ADD.L D6,D1; BSR.W 4483a.
    case 0x46654:{
        const bool x=(r.d[6]&0x80000000U)!=0;r.d[6]+=0x80000000U;r.d[4]=x?0xffffffffU:0U;r.d[6]-=r.d[4];r.d[3]-=r.d[6];
        const std::uint32_t t=r.d[3];r.d[3]=r.d[6];r.d[6]=t;r.d[1]+=r.d[6];return am_call(c,0x4483a,0x46668);}
    case 0x46668:r.pc=(r.d[7]&65535U)==0x160U?0x4667c:0x46670;return true;          // CMPI.W #160,D7; BEQ.W 4667c.
    case 0x46670:return am_call(c,0x45b1a,0x46674);                                 // BSR.W 45b1a (boundary U15c).
    case 0x46674:return am_call(c,0x45afe,0x46678);                                 // BSR.W 45afe (boundary U15b).
    case 0x46678:case 0x467ae:r.d[6]=0xffffffffU;return am_return(c);               // MOVEQ #ff,D6; RTS.
    // TST.B 54b4(A5); BNE.W 46694 / 46822.
    case 0x4667c:case 0x467b2:
        if(!ou15_get(c,r.a[5],OU15_GROUND,1,value))return false;
        r.pc=value?(r.pc==0x4667c?0x46694:0x46822):(r.pc==0x4667c?0x46684:0x467ba);return true;
    // ORI.W #40,54aa(A5); MOVE.B #ff,54b4(A5); MOVEQ #ff,D6; RTS.
    case 0x46684:if(!ou15_state_or(c,0x40) || !ou15_put(c,r.a[5],OU15_GROUND,1,0xff))return false;r.d[6]=0xffffffffU;return am_return(c);
    // MOVEQ #8,D4; SWAP D4; MOVE.L D3,D5; CMP.L D4,D5; BLE.W 466a2.
    case 0x46694:r.d[4]=0x80000U;r.d[5]=r.d[3];r.pc=ou15_long_le(r.d[5],r.d[4])?0x466a2:0x466a0;return true;
    case 0x466a0:r.d[5]=r.d[4];r.pc=0x466a2;return true;                            // MOVE.L D4,D5.
    // ADD.L D5,D4; BGE.W 466aa (N = V).
    case 0x466a2:{const std::uint32_t a=r.d[4];r.d[4]=a+r.d[5];
        r.pc=((r.d[4]&0x80000000U)!=0)==ou15_add_overflow(a,r.d[5],r.d[4])?0x466aa:0x466a8;return true;}
    case 0x466a8:r.d[5]-=r.d[4];r.pc=0x466aa;return true;                           // SUB.L D4,D5.
    // MOVE.L D5,-(A7); MOVE.L D1,D4; ANDI.L #7ffff,D4; ADD.L D5,D1; ADD.L D5,D4; SWAP D4; SUBQ.W #8,D4; BCS.W 4670a.
    case 0x466aa:{
        if(!am_push(c,4,r.d[5]))return false;r.d[4]=(r.d[1]&OU15_FRACTION)+r.d[5];r.d[1]+=r.d[5];am_swap(r.d[4]);
        const std::uint32_t w=r.d[4]&65535U;am_word(r.d[4],w-8U);r.pc=w<8U?0x4670a:0x466c0;return true;}
    // SWAP D0; SWAP D1; BSR.W 447be.
    case 0x466c0:case 0x46764:case 0x467ce:am_swap(r.d[0]);am_swap(r.d[1]);return am_call(c,0x447be,r.pc+8U);
    case 0x466c8:return ou15_land_store(c,0x466e8,0x466dc);
    case 0x4676c:return ou15_land_store(c,0x4678c,0x46780);
    case 0x467d6:return ou15_land_store(c,0x467f6,0x467ea);
    // CMPI.W #174,D7; BNE.W n1.
    case 0x466dc:r.pc=(r.d[7]&65535U)!=0x174U?0x466e8:0x466e4;return true;
    case 0x46780:r.pc=(r.d[7]&65535U)!=0x174U?0x4678c:0x46788;return true;
    case 0x467ea:r.pc=(r.d[7]&65535U)!=0x174U?0x467f6:0x467f2;return true;
    case 0x466e4:case 0x46788:case 0x467f2:am_word(r.d[7],0x160);r.pc+=4U;return true; // MOVE.W #160,D7.
    // CMPI.W #178,D7; BEQ.B n2.
    case 0x466e8:case 0x4678c:case 0x467f6:r.pc=(r.d[7]&65535U)==0x178U?r.pc+0xeU:r.pc+6U;return true;
    // CMPI.W #17c,D7; BNE.W n3.
    case 0x466ee:case 0x46792:case 0x467fc:r.pc=(r.d[7]&65535U)!=0x17cU?r.pc+0x12U:r.pc+8U;return true;
    case 0x466f6:case 0x4679a:case 0x46804:return ou15_land_reset(c,r.pc+0xaU);
    case 0x46700:case 0x467a4:case 0x4680e:return ou15_land_save(c,r.pc+0xaU);
    // MOVE.L (A7)+,D5; TST.W D4; BNE.W 46832.
    case 0x4670a:if(!am_pop(c,4,value))return false;r.d[5]=value;r.pc=(r.d[4]&65535U)!=0U?0x46832:0x46712;return true;
    case 0x46712:r.pc=(r.d[7]&65535U)==0x160U?0x46832:0x4671a;return true;          // CMPI.W #160,D7; BEQ.W 46832.
    case 0x4671a:return am_call(c,0x45176,0x4671e);                                 // BSR.W 45176.
    case 0x4671e:r.d[6]-=0x80000000U;r.pc=r.d[6]==0U?0x46832:0x46728;return true;   // SUBI.L #80000000,D6; BEQ.W 46832.
    // CMP.L D5,D6; BVC.W 46832.
    case 0x46728:r.pc=ou15_sub_overflow(r.d[6],r.d[5],r.d[6]-r.d[5])?0x4672e:0x46832;return true;
    // ADDI.L #80000000,D6; SUBX.L D4,D4; SUB.L D4,D6; SUB.L D5,D3; ADD.L D6,D3; BSR.W 4483a.
    case 0x4672e:{
        const bool x=(r.d[6]&0x80000000U)!=0;r.d[6]+=0x80000000U;r.d[4]=x?0xffffffffU:0U;r.d[6]-=r.d[4];r.d[3]-=r.d[5];r.d[3]+=r.d[6];
        return am_call(c,0x4483a,0x46740);}
    case 0x46740:r.pc=(r.d[7]&65535U)==0x160U?0x467b2:0x46748;return true;          // CMPI.W #160,D7; BEQ.W 467b2.
    case 0x46748:return am_call(c,0x45b1a,0x4674c);                                 // BSR.W 45b1a (boundary U15c).
    case 0x4674c:return am_call(c,0x45afe,0x46750);                                 // BSR.W 45afe (boundary U15b).
    case 0x46750:ou15_rise(r,0x467ae,0x46764);return true;
    case 0x467ba:ou15_rise(r,0x46818,0x467ce);return true;
    // MOVE.B #ff,54b4(A5); MOVEQ #ff,D6; RTS.
    case 0x46818:if(!ou15_put(c,r.a[5],OU15_GROUND,1,0xff))return false;r.d[6]=0xffffffffU;return am_return(c);

    // ---- 4950e: JSR 49370(PC).
    case 0x4950e:return am_call(c,0x49370,0x49512);
    case 0x49512:r.pc=(r.d[0]&65535U)<3U?0x49526:0x4951a;return true;               // CMPI.W #3,D0; BCS.W 49526.
    case 0x4951a:return am_call(c,0x49a58,0x49520);                                 // JSR 49a58.L.
    case 0x49520:am_word(r.d[0],(r.d[0]&1U)+1U);r.pc=0x49526;return true;          // ANDI.W #1,D0; ADDQ.W #1,D0.
    // LEA 100cb8.L,A0; CMPI.W #2,D0; BNE.W 4953a.
    case 0x49526:r.a[0]=0x100cb8;r.pc=(r.d[0]&65535U)!=2U?0x4953a:0x49534;return true;
    case 0x49534:r.a[0]=0x100da8;r.pc=0x4953a;return true;                          // LEA 100da8.L,A0.
    case 0x4953a:r.pc=(r.d[0]&65535U)==0U?0x49548:0x49542;return true;              // CMPI.W #0,D0; BEQ.W 49548.
    case 0x49542:case 0x4c260:return ou15_return_carry(c,AnimationCarryClear);     // ANDI.B #fe,CCR; RTS.
    case 0x49548:case 0x4c25a:return ou15_return_carry(c,AnimationCarrySet);       // ORI.B #1,CCR; RTS.

    // ---- 4c1de: TST.W D0; BMI.W 4c1f2.
    case 0x4c1de:r.pc=(r.d[0]&0x8000U)?0x4c1f2:0x4c1e4;return true;
    case 0x4c1e4:r.d[1]=8;r.pc=ou15_word_ge(r.d[0],8)?0x4c1ee:0x4c1ec;return true; // MOVEQ #8,D1; CMP.W D1,D0; BGE.W 4c1ee.
    case 0x4c1ec:case 0x4c1fa:am_word(r.d[1],r.d[0]);r.pc+=2U;return true;         // MOVE.W D0,D1 (falls to 4c1ee / 4c1fc).
    case 0x4c1ee:r.pc=0x4c1fc;return true;                                          // BRA.W 4c1fc.
    // MOVEQ #f8,D1; CMP.W D1,D0; BLE.W 4c1fc.
    case 0x4c1f2:r.d[1]=0xfffffff8U;r.pc=ou15_word_le(r.d[0],0xfff8U)?0x4c1fc:0x4c1fa;return true;
    // SUB.W D1,D0; MOVE.W D0,-(A7); MOVE.W D1,-(A7); JSR 4bc44(PC).
    case 0x4c1fc:
        am_word(r.d[0],r.d[0]-r.d[1]);if(!am_push(c,2,r.d[0]&65535U) || !am_push(c,2,r.d[1]&65535U))return false;
        return am_call(c,0x4bc44,0x4c206);
    // MOVE.B #ff,549d(A5); MOVEM.L 2e(A6),D0-D1; MOVEA.L 3e(A6),A0.
    case 0x4c206:
        if(!ou15_put(c,r.a[5],0x549d,1,0xff) || !ou15_get(c,r.a[6],0x2e,4,value))return false;r.d[0]=value;
        if(!ou15_get(c,r.a[6],0x32,4,value))return false;r.d[1]=value;if(!ou15_get(c,r.a[6],0x3e,4,value))return false;r.a[0]=value;
        r.pc=0x4c216;return true;
    // MOVEQ #0,D2; MOVEQ #0,D3; MOVE.W (A7),D2; SWAP D2; JSR 469d8.L.
    case 0x4c216:if(!am_read(c,r.a[7],2,value))return false;r.d[3]=0;r.d[2]=value<<16;return am_call(c,0x469d8,0x4c224);
    // MOVE.W (A7)+,D4; MOVE.W (A7)+,D5; BTST.B #0,D6; BEQ.W 4c260.
    case 0x4c224:
        if(!am_pop(c,2,value))return false;am_word(r.d[4],value);if(!am_pop(c,2,value))return false;am_word(r.d[5],value);
        r.pc=(r.d[6]&1U)==0U?0x4c260:0x4c230;return true;
    // TST.W D5; BEQ.W 4c25a; BMI.W 4c248.
    case 0x4c230:r.pc=(r.d[5]&65535U)==0U?0x4c25a:((r.d[5]&0x8000U)?0x4c248:0x4c23a);return true;
    case 0x4c23a:r.d[4]=8;r.pc=ou15_word_ge(r.d[5],8)?0x4c244:0x4c242;return true; // MOVEQ #8,D4; CMP.W D4,D5; BGE.W 4c244.
    case 0x4c242:case 0x4c250:am_word(r.d[4],r.d[5]);r.pc+=2U;return true;         // MOVE.W D5,D4 (falls to 4c244 / 4c252).
    case 0x4c244:r.pc=0x4c252;return true;                                          // BRA.W 4c252.
    // MOVEQ #f8,D4; CMP.W D4,D5; BLE.W 4c252.
    case 0x4c248:r.d[4]=0xfffffff8U;r.pc=ou15_word_le(r.d[5],0xfff8U)?0x4c252:0x4c250;return true;
    // SUB.W D4,D5; MOVE.W D5,-(A7); MOVE.W D4,-(A7); BRA.B 4c216.
    case 0x4c252:
        am_word(r.d[5],r.d[5]-r.d[4]);if(!am_push(c,2,r.d[5]&65535U) || !am_push(c,2,r.d[4]&65535U))return false;
        r.pc=0x4c216;return true;
    // ---- 4c29a: JSR 4bc44(PC).
    case 0x4c29a:return am_call(c,0x4bc44,0x4c29e);
    // SUB.W D0,D2; SUB.W D1,D3; SWAP D2; SWAP D3; CLR.W D2; CLR.W D3; SWAP D0; SWAP D1; CLR.W D0; CLR.W D1; ADD.L 2e(A6),D0;
    // ADD.L 32(A6),D1; MOVEA.L 3e(A6),A0; JMP 469d8.L.
    case 0x4c29e:
        am_word(r.d[2],r.d[2]-r.d[0]);am_word(r.d[3],r.d[3]-r.d[1]);
        r.d[2]=r.d[2]<<16;r.d[3]=r.d[3]<<16;r.d[0]=r.d[0]<<16;r.d[1]=r.d[1]<<16;
        if(!ou15_get(c,r.a[6],0x2e,4,value))return false;r.d[0]+=value;if(!ou15_get(c,r.a[6],0x32,4,value))return false;r.d[1]+=value;
        if(!ou15_get(c,r.a[6],0x3e,4,value))return false;r.a[0]=value;r.pc=0x469d8;return true;

    // ---- af078 (callback): BSET.B #3,15(A6); MOVE.W 46(A6),D0; CMPI.W #200,D0; BGE.W af3fe.
    case 0xaf078:
        if(!ou15_bset(c,0x15,3) || !ou15_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],value);
        r.pc=ou15_word_ge(r.d[0],0x200)?0xaf3fe:0xaf08a;return true;
    case 0xaf08a:if(!ou15_get(c,r.a[6],0x7c,2,value))return false;r.pc=value?0xaf41e:0xaf092;return true; // TST.W 7c(A6); BNE.W af41e.
    case 0xaf092:r.pc=0xaf488;return true;                                          // BRA.W af488.
    // ---- af146 (callback): BSET.B #3,15(A6); JSR b0106(PC) (boundary U16).
    case 0xaf146:if(!ou15_bset(c,0x15,3))return false;return am_call(c,0xb0106,0xaf150);
    case 0xaf150:return ou15_consume(c,true,0xaf162,0xaf154);                      // BCS.W af162 (C returned by b0106).
    case 0xaf154:case 0xaf42e:case 0xaf49c:case 0xb05ce:return ou15_release(c);
    // MOVE.W #5f,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xaf162:am_word(r.d[0],0x5f);am_word(r.d[1],1);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xaf174);
    // MOVE.W #8899,68(A6); MOVE.W #8899,1e(A6); MOVE.L #b060c,56(A6); MOVE.W 76(A6),D0; MOVE.W 78(A6),D1; MOVE.W D0,90(A6);
    // MOVE.B D1,9a(A6); MOVEQ #0,D0; MOVE.W D0,76(A6); MOVE.W D0,78(A6); LEA cac22.L,A0; JSR 490ba.L.
    case 0xaf174:
        if(!ou15_put(c,r.a[6],0x68,2,0x8899) || !ou15_put(c,r.a[6],0x1e,2,0x8899) || !ou15_put(c,r.a[6],0x56,4,0xb060c) ||
           !ou15_get(c,r.a[6],0x76,2,value))return false;
        am_word(r.d[0],value);if(!ou15_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[1],value);
        if(!ou15_put(c,r.a[6],0x90,2,r.d[0]&65535U) || !ou15_put(c,r.a[6],0x9a,1,r.d[1]&255U))return false;r.d[0]=0;
        if(!ou15_put(c,r.a[6],0x76,2,0) || !ou15_put(c,r.a[6],0x78,2,0))return false;r.a[0]=0xcac22;return am_call(c,0x490ba,0xaf1ae);
    // MOVE.W D0,54(A6); MOVE.W #163,20(A6); MOVEA.L #b0c4a,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0xaf1ae:
        if(!ou15_put(c,r.a[6],0x54,2,r.d[0]&65535U) || !ou15_put(c,r.a[6],0x20,2,0x163))return false;
        r.a[1]=0xb0c4a;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xaf1c8);
    case 0xaf1c8:case 0xaf1f8:r.a[0]=0xcac3c;return am_call(c,0x490ba,r.pc+0xcU);  // LEA cac3c.L,A0; JSR 490ba.L.
    // MOVE.W D0,96(A6); JSR 49274.L.
    case 0xaf1d4:if(!ou15_put(c,r.a[6],0x96,2,r.d[0]&65535U))return false;return am_call(c,0x49274,0xaf1de);
    case 0xaf1de:if(!am_write(c,r.a[6],4,0xaf1e4))return false;r.pc=0xaf1e4;return true; // MOVE.L #af1e4,(A6).
    case 0xaf1e4:return am_call(c,0x43e34,0xaf1ea);                                 // (installed callback) JSR 43e34.L.
    case 0xaf1ea:return am_call(c,0x49fc6,0xaf1f0);                                 // JSR 49fc6.L.
    // SUBQ.W #1,96(A6); BPL.W af26c.
    case 0xaf1f0:
        if(!ou15_get(c,r.a[6],0x96,2,value))return false;value=(value-1U)&65535U;if(!ou15_put(c,r.a[6],0x96,2,value))return false;
        r.pc=(value&0x8000U)?0xaf1f8:0xaf26c;return true;
    // MOVE.W D0,96(A6); TST.W 90(A6); BEQ.W af26c; BPL.W af22e.
    case 0xaf204:
        if(!ou15_put(c,r.a[6],0x96,2,r.d[0]&65535U) || !ou15_get(c,r.a[6],0x90,2,value))return false;
        r.pc=value==0U?0xaf26c:((value&0x8000U)?0xaf214:0xaf22e);return true;
    case 0xaf214:return ou15_spawn_under(c,0xaf3f8,0xaf22a);
    case 0xaf22a:r.pc=0xaf244;return true;                                          // BRA.W af244.
    case 0xaf22e:return ou15_spawn_under(c,0xaf3fe,0xaf244);
    // MOVE.B 6a(A6),6a(A0); MOVEQ #0,D0; MOVE.W D0,76(A0); MOVE.W D0,78(A0); MOVE.W D0,7a(A0); MOVEQ #fc,D1; JSR 49214.L (boundary).
    case 0xaf244:
        if(!ou15_get(c,r.a[6],0x6a,1,value) || !ou15_put(c,r.a[0],0x6a,1,value))return false;r.d[0]=0;
        if(!ou15_put(c,r.a[0],0x76,2,0) || !ou15_put(c,r.a[0],0x78,2,0) || !ou15_put(c,r.a[0],0x7a,2,0))return false;
        r.d[1]=0xfffffffcU;return am_call(c,0x49214,0xaf260);
    // SUBQ.W #1,90(A6); SMI.B D0; EXT.W D0; SUB.W D0,90(A6).
    case 0xaf260:{
        if(!ou15_get(c,r.a[6],0x90,2,value))return false;value=(value-1U)&65535U;if(!ou15_put(c,r.a[6],0x90,2,value))return false;
        const std::uint32_t m=(value&0x8000U)?0xffffU:0U;am_word(r.d[0],m);
        if(!ou15_get(c,r.a[6],0x90,2,value) || !ou15_put(c,r.a[6],0x90,2,(value-m)&65535U))return false;r.pc=0xaf26c;return true;}
    case 0xaf26c:if(!ou15_get(c,r.a[6],0x9a,1,value))return false;r.pc=value?0xaf274:0xaf2dc;return true; // TST.B 9a(A6); BEQ.W af2dc.
    case 0xaf274:return am_call(c,0x287e,0xaf27a);                                  // JSR 287e.L.
    case 0xaf27a:return ou15_consume(c,true,0xaf2dc,0xaf27e);                      // BCS.W af2dc (C returned by 287e).
    case 0xaf27e:r.a[0]=0xaf3de;am_word(r.d[0],0x14);return am_call(c,0x28ae,0xaf28e); // MOVEA.L #af3de,A0; MOVE.W #14,D0; JSR 28ae.L.
    // MOVE.B 6a(A6),6a(A0); MOVE.B a3(A6),a3(A0); MOVE.W #ffff,76(A0); MOVE.W #0,78(A0); MOVE.W #0,7a(A0); MOVE.B 9a(A6),D0;
    // CMPI.B #3,D0; BNE.W af2be.
    case 0xaf28e:
        if(!ou15_get(c,r.a[6],0x6a,1,value) || !ou15_put(c,r.a[0],0x6a,1,value) || !ou15_get(c,r.a[6],0xa3,1,value) ||
           !ou15_put(c,r.a[0],0xa3,1,value) || !ou15_put(c,r.a[0],0x76,2,0xffff) || !ou15_put(c,r.a[0],0x78,2,0) ||
           !ou15_put(c,r.a[0],0x7a,2,0) || !ou15_get(c,r.a[6],0x9a,1,value))return false;
        am_byte(r.d[0],value);r.pc=value!=3U?0xaf2be:0xaf2b8;return true;
    case 0xaf2b8:case 0xaf408:return am_call(c,0x49a58,r.pc+6U);                  // JSR 49a58.L.
    case 0xaf2be:r.pc=(r.d[0]&1U)==0U?0xaf2ce:0xaf2c6;return true;                 // BTST.B #0,D0; BEQ.W af2ce.
    case 0xaf2c6:am_word(r.d[0],0x158);r.pc=0xaf2d2;return true;                   // MOVE.W #158,D0; BRA.W af2d2.
    case 0xaf2ce:am_word(r.d[0],0xffe8);r.pc=0xaf2d2;return true;                  // MOVE.W #ffe8,D0.
    case 0xaf2d2:am_word(r.d[1],0x1a0);return am_call(c,0x491fe,0xaf2dc);          // MOVE.W #1a0,D1; JSR 491fe.L (boundary).
    case 0xaf2dc:r.pc=0xaf2e0;return true;                                          // BRA.W af2e0.
    case 0xaf2e0:return am_call(c,0x4b54e,0xaf2e6);                                 // JSR 4b54e.L.
    case 0xaf2e6:return ou15_consume(c,false,0xaf2ee,0xaf2ea);                     // BCC.W af2ee (C returned by 4b54e).
    case 0xaf2ea:if(!ou15_put(c,r.a[6],0x5e,1,0))return false;r.pc=0xaf2ee;return true; // CLR.B 5e(A6).
    case 0xaf2ee:if(!ou15_get(c,r.a[6],0x61,1,value))return false;r.pc=(value&0x80U)?0xaf2f8:0xaf2fe;return true; // BTST #7; BEQ af2fe.
    case 0xaf2f8:if(!am_write(c,r.a[6],4,0xaf302))return false;r.pc=0xaf2fe;return true; // MOVE.L #af302,(A6).
    case 0xaf2fe:r.pc=0xb05be;return true;                                          // BRA.W b05be.
    // ---- af3de (child callback): BSET.B #3,15(A6); JSR 49274.L.
    case 0xaf3de:if(!ou15_bset(c,0x15,3))return false;return am_call(c,0x49274,0xaf3ea);
    case 0xaf3ea:case 0xaf3f8:return am_call(c,0x4b702,r.pc+6U);                  // JSR 4b702.L (boundary).
    case 0xaf3f0:if(!ou15_put(c,r.a[6],0x9a,1,0xff))return false;r.pc=0xaf422;return true; // ST.B 9a(A6); BRA.W af422.
    case 0xaf3fe:case 0xaf422:case 0xaf488:return am_call(c,0xb0062,r.pc+4U);     // JSR b0062(PC).
    case 0xaf402:return am_call(c,0xd3c2a,0xaf408);                                 // JSR d3c2a.L (boundary).
    // ANDI.B #7,D0; MOVE.B D0,a1(A6); MOVE.L #af4ee,(A6); RTS.
    case 0xaf40e:am_byte(r.d[0],r.d[0]&7U);if(!ou15_put(c,r.a[6],0xa1,1,r.d[0]&255U))return false;return ou15_install_return(c,0xaf4ee);
    case 0xaf41e:if(!ou15_put(c,r.a[6],0x9a,1,0))return false;r.pc=0xaf422;return true; // SF.B 9a(A6).
    case 0xaf426:return am_call(c,0xb0106,0xaf42a);                                 // JSR b0106(PC) (boundary U16).
    case 0xaf42a:return ou15_consume(c,true,0xaf43c,0xaf42e);                      // BCS.W af43c (C returned by b0106).
    // MOVE.B 9e(A6),D0; LSL.W #8,D0; BSR.W b02c8 (boundary U16).
    case 0xaf43c:
        if(!ou15_get(c,r.a[6],0x9e,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],(r.d[0]&65535U)<<8);
        return am_call(c,0xb02c8,0xaf446);
    case 0xaf446:return ou15_side_check(c,0xaf452);
    case 0xaf452:return ou15_consume(c,false,0xaf470,0xaf456);                     // BCC.W af470 (C returned by b0206).
    // MOVEA.L 76(A6),A0; MOVE.W 42(A0),D0; CMP.W 42(A6),D0; BLE.W af46c.
    case 0xaf456:
        if(!ou15_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;if(!ou15_get(c,r.a[0],0x42,2,value))return false;
        am_word(r.d[0],value);if(!ou15_get(c,r.a[6],0x42,2,value))return false;r.pc=ou15_word_le(r.d[0],value)?0xaf46c:0xaf466;return true;
    case 0xaf466:case 0xaf47a:case 0xaf4e0:if(!ou15_bset(c,0x15,0))return false;r.pc+=6U;return true; // BSET.B #0,15(A6).
    case 0xaf46c:r.pc=0xaf480;return true;                                          // BRA.W af480.
    // CMPI.W #a0,42(A6); BGT.W af480.
    case 0xaf470:if(!ou15_get(c,r.a[6],0x42,2,value))return false;r.pc=ou15_word_le(value,0xa0)?0xaf47a:0xaf480;return true;
    case 0xaf480:return ou15_install_return(c,0xaf6ec);                            // MOVE.L #af6ec,(A6); RTS.
    case 0xaf48c:return am_call(c,0x4c0ac,0xaf492);                                 // JSR 4c0ac.L.
    case 0xaf492:if(!ou15_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&0x80U)?0xaf4aa:0xaf49c;return true; // BTST #7; BNE af4aa.
    case 0xaf4aa:r.d[0]=0;return am_call(c,0x4c1de,0xaf4b2);                       // MOVEQ #0,D0; JSR 4c1de.L.
    case 0xaf4b2:am_word(r.d[0],r.d[7]);return am_call(c,0xb02c8,0xaf4b8);          // MOVE.W D7,D0; BSR.W b02c8 (boundary U16).
    case 0xaf4b8:return ou15_side_check(c,0xaf4c4);
    case 0xaf4c4:return ou15_consume(c,false,0xaf4d4,0xaf4c8);                     // BCC.W af4d4 (C returned by b0206).
    // MOVEA.L 76(A6),A0; MOVE.W 42(A0),D0; BRA.W af4d8.
    case 0xaf4c8:
        if(!ou15_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;if(!ou15_get(c,r.a[0],0x42,2,value))return false;
        am_word(r.d[0],value);r.pc=0xaf4d8;return true;
    case 0xaf4d4:am_word(r.d[0],0xa0);r.pc=0xaf4d8;return true;                    // MOVE.W #a0,D0.
    // CMP.W 42(A6),D0; BLE.W af4e6.
    case 0xaf4d8:if(!ou15_get(c,r.a[6],0x42,2,value))return false;r.pc=ou15_word_le(r.d[0],value)?0xaf4e6:0xaf4e0;return true;
    case 0xaf4e6:return ou15_install_return(c,0xaf6de);                            // MOVE.L #af6de,(A6); RTS.

    // ---- b0062: BSR.W b00da.
    case 0xb0062:return am_call(c,0xb00da,0xb0066);
    case 0xb0066:am_word(r.d[0],0xc45);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xb0074); // MOVE.W #c45,D0; MOVE.B #0,D1; JSR 8ebe.L.
    // MOVE.W #8898,68(A6); MOVE.W #8898,1e(A6); MOVE.L #b05ee,56(A6); LEA caadc.L,A0; JSR 490ba.L.
    case 0xb0074:
        if(!ou15_put(c,r.a[6],0x68,2,0x8898) || !ou15_put(c,r.a[6],0x1e,2,0x8898) || !ou15_put(c,r.a[6],0x56,4,0xb05ee))return false;
        r.a[0]=0xcaadc;return am_call(c,0x490ba,0xb0094);
    case 0xb0094:return ou15_store_math(c,0x54,0xcabba,0xb00a4);
    case 0xb00a4:return ou15_store_math(c,0x82,0xcabd4,0xb00b4);
    case 0xb00b4:return ou15_store_math(c,0x84,0xcabee,0xb00c4);
    case 0xb00c4:return ou15_store_math(c,0x86,0xcac08,0xb00d4);
    case 0xb00d4:if(!ou15_put(c,r.a[6],0x88,2,r.d[0]&65535U))return false;return am_return(c); // MOVE.W D0,88(A6); RTS.
    // ---- b00da: MOVE.W 76/78/7a(A6),D0/D1/D2; MOVEQ #0,D7; MOVE.W D7,76/78/7a/7c(A6); MOVE.W D0/D1/D2,8a/92/94(A6); RTS.
    case 0xb00da:
        if(!ou15_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);if(!ou15_get(c,r.a[6],0x78,2,value))return false;
        am_word(r.d[1],value);if(!ou15_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[2],value);r.d[7]=0;
        if(!ou15_put(c,r.a[6],0x76,2,0) || !ou15_put(c,r.a[6],0x78,2,0) || !ou15_put(c,r.a[6],0x7a,2,0) || !ou15_put(c,r.a[6],0x7c,2,0) ||
           !ou15_put(c,r.a[6],0x8a,2,r.d[0]&65535U) || !ou15_put(c,r.a[6],0x92,2,r.d[1]&65535U) || !ou15_put(c,r.a[6],0x94,2,r.d[2]&65535U))
            return false;
        return am_return(c);
    // ---- b05be (shared tail): LEA b05e6.L,A0; JSR 1ab02.L.
    case 0xb05be:r.a[0]=0xb05e6;return am_call(c,0x1ab02,0xb05ca);
    case 0xb05ca:return ou15_consume(c,false,0xb05dc,0xb05ce);                     // BCC.W b05dc (C returned by 1ab02).
    case 0xb05dc:return am_return(c);                                               // RTS.
    default:return am_error(c,"unsupported animation objects u15 PC");
    }
}
}
