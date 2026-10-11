#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// 45176 JMP 4517a(PC,D7.W): the 96 BRA.W entries 4517a+4k (k = 0..5f) transcribed from the original code (decision 4).
// The callers' D7.W is the 447be result 4k (k < 60) or 160; the jump itself moves to the computed PC (F1 decision 3).
const std::uint32_t OU11_TABLE=0x4517a;
const unsigned int OU11_TABLE_ENTRIES=96;
const std::uint32_t OU11_TARGETS[OU11_TABLE_ENTRIES]={
    0x4560e,0x45772,0x456ca,0x456b2,0x45622,0x4575a,0x456e2,0x4569a,0x4563a,0x45742,0x456fa,0x45682,0x45652,0x4572a,0x45712,0x4566a,
    0x4566a,0x45712,0x4572a,0x45652,0x45682,0x456fa,0x45742,0x4563a,0x4569a,0x456e2,0x4575a,0x45622,0x456b2,0x456ca,0x45772,0x4560e,
    0x452fa,0x452fa,0x452fa,0x452fa,0x453a2,0x45426,0x453c0,0x4533a,0x4537e,0x45404,0x453e2,0x4535c,0x4535c,0x453e2,0x45404,0x4537e,
    0x4533a,0x453c0,0x45426,0x453a2,0x4546c,0x454ac,0x4548a,0x45448,0x45448,0x4548a,0x454ac,0x4546c,0x454ce,0x454e0,0x454e0,0x454ce,
    0x454f6,0x4553a,0x45522,0x4550a,0x4550a,0x45522,0x4553a,0x454f6,0x45552,0x455f6,0x455ae,0x45596,0x45566,0x455de,0x455c6,0x4557e,
    0x4557e,0x455c6,0x455de,0x45566,0x45596,0x455ae,0x455f6,0x45552,0x452fa,0x45330,0x45310,0x45320,0x45310,0x45302,0x452fa,0x452fa};
const std::uint32_t OU11_NONE=0x452fa;      // MOVE.L #80000000,D6; RTS (the out-of-range branch of the range targets).
const std::uint32_t OU11_FRACTION=0x7ffff;  // MOVE.L #7ffff,D6 (the fraction mask of the targets).
const std::uint32_t OU11_CHILD=0xbead4;     // MOVEA.L #bead4,A0 (the child callback of be8a4).
const std::uint32_t OU11_BANK_TABLE=0x2001e0; // MOVE.L/MOVEA.L 2001e0.L (banked window LONG, live bus).
bool ou11_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou11_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// ASR.L #shift (shift 1..3): sign fill written out (no signed shift of C++).
std::uint32_t ou11_asr_long(std::uint32_t value,unsigned int shift) {
    const std::uint32_t fill=(value&0x80000000U)?~(0xffffffffU>>shift):0U;return (value>>shift)|fill;
}
// ASR.W #3 of the low WORD (high WORD kept).
void ou11_asr_word3(std::uint32_t& r) {
    const std::uint32_t w=r&65535U;const std::uint32_t fill=(w&0x8000U)?0xe000U:0U;am_word(r,(w>>3)|fill);
}
// Range target head: MOVE.L #7ffff,D6; MOVE.L D0,D4; AND.L D6,D4; [ADDI.L #add,D4;] CMPI.L #bound,D4; BCC/BCS 452fa.
// below_out: BCS (out of range when D4 <u bound), otherwise BCC (out of range when D4 >=u bound).
void ou11_range_head(AnimationMachineState& r,std::uint32_t add,std::uint32_t bound,bool below_out,std::uint32_t fall_pc) {
    r.d[6]=OU11_FRACTION;r.d[4]=(r.d[0]&r.d[6])+add;
    const bool below=r.d[4]<bound;r.pc=(below==below_out)?OU11_NONE:fall_pc;
}
// Target tail: AND.L D1,D6; SUB.L D4,D6 or ADD.L D4,D6; RTS.
bool ou11_finish(AnimationMachineContext& c,bool subtract) {
    AnimationMachineState& r=c.s;r.d[6]&=r.d[1];r.d[6]=subtract?r.d[6]-r.d[4]:r.d[6]+r.d[4];return am_return(c);
}
// Range target tail: [ADDQ.L #1,D4;] LSL.L #shift,D4; AND.L D1,D6; SUB.L/ADD.L D4,D6; RTS.
bool ou11_range_tail(AnimationMachineContext& c,bool add_one,unsigned int shift,bool subtract) {
    AnimationMachineState& r=c.s;if(add_one)r.d[4]+=1U;r.d[4]<<=shift;return ou11_finish(c,subtract);
}
// Straight target: MOVE.L #7ffff,D6; MOVE.L D0,D4; AND.L D6,D4; [ASR.L #shift,D4;] ADDQ.L #1/ADDI.L #add,D4; AND.L D1,D6;
// SUB.L/ADD.L D4,D6; RTS (shift 0: no ASR).
bool ou11_straight(AnimationMachineContext& c,unsigned int shift,std::uint32_t add,bool subtract) {
    AnimationMachineState& r=c.s;r.d[6]=OU11_FRACTION;r.d[4]=r.d[0]&r.d[6];
    if(shift)r.d[4]=ou11_asr_long(r.d[4],shift);r.d[4]+=add;return ou11_finish(c,subtract);
}
// MOVE.L D1,D6; ANDI.L #7ffff,D6; [SUBI.L #sub,D6;] RTS.
bool ou11_column(AnimationMachineContext& c,std::uint32_t sub) {
    AnimationMachineState& r=c.s;r.d[6]=(r.d[1]&OU11_FRACTION)-sub;return am_return(c);
}
// ORI.B #1,CCR / ANDI.B #fe,CCR; RTS (known C returned to the caller).
bool ou11_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {c.s.carry=carry;return am_return(c);}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool ou11_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u11 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVEA.L #bead4,A0; MOVE.W #a,D0; JSR 28ae.L (fade_card object creation of the child bead4).
bool ou11_spawn(AnimationMachineContext& c,std::uint32_t return_pc) {
    c.s.a[0]=OU11_CHILD;am_word(c.s.d[0],0xa);return am_call(c,0x28ae,return_pc);
}
// MOVE.W #k,76(A0) of the created child.
bool ou11_child_index(AnimationMachineContext& c,std::uint32_t k) {return ou11_put(c,c.s.a[0],0x76,2,k);}
// LEA table(PC),A0; MOVE.W 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),Dn (WORD table indexed by the node WORD 76).
bool ou11_node_word(AnimationMachineContext& c,std::uint32_t table,std::uint32_t& out) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=table;
    if(!ou11_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]<<1);
    return am_read(c,am_index(r.a[0],r.d[0]),2,out);
}
}
// Objects F4 U11 (215 block starts): the terrain height table 45176 (JMP 4517a(PC,D7.W), all 96 BRA.W entries 4517a..452f6 and
// the target bodies 452fa..45788; the BNE 44c62 of 45302 is a boundary), the terrain rectangle 47288, C3 49370 (TRAP 4937c is a
// boundary), 496c2 and 497b6 (frame_helpers 49392, boundary 4941e), C4 4be06 (U08b 4bc44/4bf16, U09 469d8) and the object family
// be888/be8a4 with the installed callbacks beac0 and beb52 and the child callback bead4 (U05 1ab02/c6a96, cleanup 46ef4/2a24/43e34,
// fade_card 28ae/2a00, U08a 49290, interpreter 49f8c/49fc6, U09 4706c). 45176 moves to the computed PC 4517a+D7.W through the
// routing. 49386/497e4 return C Set and 4938c/497ea C Clear; 497ba 497c4 497cc 497d8 497e0 be892 consume a callee C. U11 reads
// work RAM, fixed ROM tables and the banked window LONG 2001e0 and writes no port.
bool animation_objects_u11_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 45176: JMP 4517a(PC,D7.W) (computed PC through the routing).
    case 0x45176:r.pc=am_index(OU11_TABLE,r.d[7]);return true;
    case 0x452fa:r.d[6]=0x80000000U;return am_return(c);                // MOVE.L #80000000,D6; RTS.
    // TST.B 549e(A5); BNE.W 44c62 (boundary).
    case 0x45302:if(!ou11_get(c,r.a[5],0x549e,1,value))return false;r.pc=value?0x44c62:0x4530a;return true;
    // TST.L D3; BGT.W 45330 (signed LONG D3 > 0).
    case 0x4530a:r.pc=(r.d[3]!=0U && (r.d[3]&0x80000000U)==0U)?0x45330:0x45310;return true;
    case 0x45310:return ou11_column(c,0x80000);
    case 0x45320:return ou11_column(c,0x40000);
    case 0x45330:return ou11_column(c,0);
    // Range heads (CMPI.L #20000/BCC, #fffe0000/BCS, #40000/BCC, #fffc0000/BCS) and their tails.
    case 0x4533a:ou11_range_head(r,0xfffa0000U,0x20000,false,0x45352);return true;
    case 0x4535c:ou11_range_head(r,0xfffc0000U,0x20000,false,0x45374);return true;
    case 0x4537e:ou11_range_head(r,0xfffe0000U,0x20000,false,0x45398);return true;
    case 0x453a2:ou11_range_head(r,0,0x20000,false,0x453b6);return true;
    case 0x45352:case 0x45374:case 0x45398:case 0x453b6:return ou11_range_tail(c,true,2,true);
    case 0x453c0:ou11_range_head(r,0xfffe0000U,0xfffe0000U,true,0x453da);return true;
    case 0x453e2:ou11_range_head(r,0xfffc0000U,0xfffe0000U,true,0x453fc);return true;
    case 0x45404:ou11_range_head(r,0xfffa0000U,0xfffe0000U,true,0x4541e);return true;
    case 0x45426:ou11_range_head(r,0xfff80000U,0xfffe0000U,true,0x45440);return true;
    case 0x453da:case 0x453fc:case 0x4541e:case 0x45440:return ou11_range_tail(c,false,2,false);
    case 0x45448:ou11_range_head(r,0xfffc0000U,0x40000,false,0x45462);return true;
    case 0x4546c:ou11_range_head(r,0,0x40000,false,0x45480);return true;
    case 0x45462:case 0x45480:return ou11_range_tail(c,true,1,true);
    case 0x4548a:ou11_range_head(r,0xfffc0000U,0xfffc0000U,true,0x454a4);return true;
    case 0x454ac:ou11_range_head(r,0xfff80000U,0xfffc0000U,true,0x454c6);return true;
    case 0x454a4:case 0x454c6:return ou11_range_tail(c,false,1,false);
    // Straight targets (no range check).
    case 0x454ce:return ou11_straight(c,0,1,true);
    case 0x454e0:return ou11_straight(c,0,0xfff80000U,false);
    case 0x454f6:return ou11_straight(c,1,1,true);
    case 0x4550a:return ou11_straight(c,1,0x40001,true);
    case 0x45522:return ou11_straight(c,1,0xfff80000U,false);
    case 0x4553a:return ou11_straight(c,1,0xfffc0000U,false);
    case 0x45552:return ou11_straight(c,2,1,true);
    case 0x45566:return ou11_straight(c,2,0x20001,true);
    case 0x4557e:return ou11_straight(c,2,0x40001,true);
    case 0x45596:return ou11_straight(c,2,0x60001,true);
    case 0x455ae:return ou11_straight(c,2,0xfff80000U,false);
    case 0x455c6:return ou11_straight(c,2,0xfffa0000U,false);
    case 0x455de:return ou11_straight(c,2,0xfffc0000U,false);
    case 0x455f6:return ou11_straight(c,2,0xfffe0000U,false);
    case 0x4560e:return ou11_straight(c,3,1,true);
    case 0x45622:return ou11_straight(c,3,0x10001,true);
    case 0x4563a:return ou11_straight(c,3,0x20001,true);
    case 0x45652:return ou11_straight(c,3,0x30001,true);
    case 0x4566a:return ou11_straight(c,3,0x40001,true);
    case 0x45682:return ou11_straight(c,3,0x50001,true);
    case 0x4569a:return ou11_straight(c,3,0x60001,true);
    case 0x456b2:return ou11_straight(c,3,0x70001,true);
    case 0x456ca:return ou11_straight(c,3,0xfff80000U,false);
    case 0x456e2:return ou11_straight(c,3,0xfff90000U,false);
    case 0x456fa:return ou11_straight(c,3,0xfffa0000U,false);
    case 0x45712:return ou11_straight(c,3,0xfffb0000U,false);
    case 0x4572a:return ou11_straight(c,3,0xfffc0000U,false);
    case 0x45742:return ou11_straight(c,3,0xfffd0000U,false);
    case 0x4575a:return ou11_straight(c,3,0xfffe0000U,false);
    case 0x45772:return ou11_straight(c,3,0xffff0000U,false);

    // ---- 47288: MOVE.W D0,D4; MOVE.W D1,D5; ASR.W #3,D4; ASR.W #3,D5; MOVEA.L 26(A0),A4; SUB.W (A4)+,D4; SUB.W (A4)+,D5;
    // MOVE.W (A4)+,D6; CMP.W D6,D4; BCC.W 472b8 (unsigned WORD D4 >= D6).
    case 0x47288:
        am_word(r.d[4],r.d[0]);am_word(r.d[5],r.d[1]);ou11_asr_word3(r.d[4]);ou11_asr_word3(r.d[5]);
        if(!ou11_get(c,r.a[0],0x26,4,value))return false;r.a[4]=value;
        if(!am_read(c,r.a[4],2,value))return false;r.a[4]+=2U;am_word(r.d[4],r.d[4]-value);
        if(!am_read(c,r.a[4],2,value))return false;r.a[4]+=2U;am_word(r.d[5],r.d[5]-value);
        if(!am_read(c,r.a[4],2,value))return false;r.a[4]+=2U;am_word(r.d[6],value);
        r.pc=(r.d[4]&65535U)>=(r.d[6]&65535U)?0x472b8:0x472a0;return true;
    // MOVE.W (A4)+,D7; CMP.W D7,D5; BCC.W 472b8.
    case 0x472a0:
        if(!am_read(c,r.a[4],2,value))return false;r.a[4]+=2U;am_word(r.d[7],value);
        r.pc=(r.d[5]&65535U)>=(r.d[7]&65535U)?0x472b8:0x472a8;return true;
    // MOVE.W (A4)+,D7; ADD.W D5,D5; MOVE.W (A4,D5.W),D5; ADD.W D4,D5; ADDA.W D5,A4; MOVE.B (A4),D7; RTS.
    case 0x472a8:
        if(!am_read(c,r.a[4],2,value))return false;r.a[4]+=2U;am_word(r.d[7],value);am_word(r.d[5],r.d[5]<<1);
        if(!am_read(c,am_index(r.a[4],r.d[5]),2,value))return false;am_word(r.d[5],value);am_word(r.d[5],r.d[5]+r.d[4]);
        r.a[4]=am_index(r.a[4],r.d[5]);if(!am_read(c,r.a[4],1,value))return false;am_byte(r.d[7],value);return am_return(c);
    case 0x472b8:r.d[6]=0;r.d[7]=0x58;return am_return(c);              // MOVEQ #0,D6; MOVEQ #58,D7; RTS.

    // ---- 49370: MOVEQ #0,D0; CMPA.L #108000,A5; BEQ.W 4937e (otherwise the TRAP 4937c boundary).
    case 0x49370:r.d[0]=0;r.pc=r.a[5]==0x108000U?0x4937e:0x4937c;return true;
    // MOVE.B 568e(A5),D0; BNE.W 4938c.
    case 0x4937e:if(!ou11_get(c,r.a[5],0x568e,1,value))return false;am_byte(r.d[0],value);r.pc=value?0x4938c:0x49386;return true;
    case 0x49386:case 0x497e4:return ou11_return_carry(c,AnimationCarrySet);   // ORI.B #1,CCR; RTS.
    case 0x4938c:case 0x497ea:return ou11_return_carry(c,AnimationCarryClear); // ANDI.B #fe,CCR; RTS.

    // ---- 496c2: EOR.L D0,D0; MOVE.L D0,36(A6); MOVE.L D0,3a(A6); MOVE.L D0,64(A6); RTS.
    case 0x496c2:
        r.d[0]=0;if(!ou11_put(c,r.a[6],0x36,4,0) || !ou11_put(c,r.a[6],0x3a,4,0) || !ou11_put(c,r.a[6],0x64,4,0))return false;
        return am_return(c);

    // ---- 497b6: JSR 49370(PC).
    case 0x497b6:return am_call(c,0x49370,0x497ba);
    case 0x497ba:return ou11_consume(c,true,0x497ea,0x497be);           // BCS.W 497ea (C returned by 49370).
    case 0x497be:am_word(r.d[0],0);return am_call(c,0x49392,0x497c4);   // CLR.W D0; JSR 49392(PC).
    case 0x497c4:return ou11_consume(c,false,0x497d0,0x497c8);          // BCC.W 497d0 (C returned by 49392).
    case 0x497c8:return am_call(c,0x4941e,0x497cc);                     // JSR 4941e(PC) (boundary).
    case 0x497cc:return ou11_consume(c,true,0x497ea,0x497d0);           // BCS.W 497ea (C returned by 4941e).
    case 0x497d0:am_word(r.d[0],1);return am_call(c,0x49392,0x497d8);   // MOVE.W #1,D0; JSR 49392(PC).
    case 0x497d8:return ou11_consume(c,false,0x497e4,0x497dc);          // BCC.W 497e4.
    case 0x497dc:return am_call(c,0x4941e,0x497e0);                     // JSR 4941e(PC) (boundary).
    case 0x497e0:return ou11_consume(c,true,0x497ea,0x497e4);           // BCS.W 497ea.

    // ---- 4be06: JSR 4bc44(PC).
    case 0x4be06:return am_call(c,0x4bc44,0x4be0a);
    // MOVEM.L 2e(A6),D0-D1; MOVEA.L 3e(A6),A0; MOVEQ #0,D2; MOVEQ #0,D3; JSR 469d8.L.
    case 0x4be0a:
        if(!ou11_get(c,r.a[6],0x2e,4,value))return false;r.d[0]=value;if(!ou11_get(c,r.a[6],0x32,4,value))return false;r.d[1]=value;
        if(!ou11_get(c,r.a[6],0x3e,4,value))return false;r.a[0]=value;r.d[2]=0;r.d[3]=0;return am_call(c,0x469d8,0x4be1e);
    // MOVEM.L D0-D1,2e(A6); MOVE.L A0,3e(A6); BRA.W 4bf16.
    case 0x4be1e:
        if(!ou11_put(c,r.a[6],0x2e,4,r.d[0]) || !ou11_put(c,r.a[6],0x32,4,r.d[1]) || !ou11_put(c,r.a[6],0x3e,4,r.a[0]))return false;
        r.pc=0x4bf16;return true;

    // ---- be888: LEA be3e4(PC),A0; JSR 1ab02.L.
    case 0xbe888:r.a[0]=0xbe3e4;return am_call(c,0x1ab02,0xbe892);
    case 0xbe892:return ou11_consume(c,false,0xbe8a2,0xbe896);          // BCC.W be8a2 (C returned by 1ab02).
    case 0xbe896:return am_call(c,0x46ef4,0xbe89c);                     // JSR 46ef4.L.
    case 0xbe89c:r.pc=0x2a24;return true;                               // JMP 2a24.L.
    case 0xbe8a2:case 0xbeb78:return am_return(c);                      // RTS.
    // ---- be8a4 (callback): MOVE.W 76(A6),D0; LEA be874(PC),A0; ADD.W D0,D0; ADD.W D0,D0; MOVE.W (A0,D0.W),8a(A6);
    // TST.W 7a(A6); BNE.W be8c8.
    case 0xbe8a4:
        if(!ou11_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.a[0]=0xbe874;am_word(r.d[0],r.d[0]<<2);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value) || !ou11_put(c,r.a[6],0x8a,2,value) || !ou11_get(c,r.a[6],0x7a,2,value))
            return false;
        r.pc=value?0xbe8c8:0xbe8be;return true;
    // MOVE.W 2(A0,D0.W),8c(A6); BRA.W be8ce.
    case 0xbe8be:
        if(!am_read(c,am_index(r.a[0]+2U,r.d[0]),2,value) || !ou11_put(c,r.a[6],0x8c,2,value))return false;r.pc=0xbe8ce;return true;
    case 0xbe8c8:if(!ou11_put(c,r.a[6],0x8c,2,0xffe8))return false;r.pc=0xbe8ce;return true; // MOVE.W #ffe8,8c(A6).
    // MOVE.W 76(A6),D2; ADD.W D2,D2; ADD.W D2,D2; LEA be808(PC),A0; MOVE.L (A0,D2.W),86(A6); MOVE.W 76(A6),D0; BNE.W be918.
    case 0xbe8ce:
        if(!ou11_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[2],value);am_word(r.d[2],r.d[2]<<2);r.a[0]=0xbe808;
        if(!am_read(c,am_index(r.a[0],r.d[2]),4,value) || !ou11_put(c,r.a[6],0x86,4,value) || !ou11_get(c,r.a[6],0x76,2,value))
            return false;
        am_word(r.d[0],value);r.pc=value?0xbe918:0xbe8e8;return true;
    case 0xbe8e8:case 0xbe920:case 0xbe958:return ou11_spawn(c,r.pc+0x10U); // MOVEA.L #bead4,A0; MOVE.W #a,D0; JSR 28ae.L.
    // MOVE.W #k,76(A0); MOVEA.L #bead4,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0xbe8f8:if(!ou11_child_index(c,0))return false;return ou11_spawn(c,0xbe90e);
    case 0xbe930:if(!ou11_child_index(c,2))return false;return ou11_spawn(c,0xbe946);
    case 0xbe968:if(!ou11_child_index(c,4))return false;return ou11_spawn(c,0xbe97e);
    // MOVE.W #k,76(A0); BRA.W be98e.
    case 0xbe90e:if(!ou11_child_index(c,1))return false;r.pc=0xbe98e;return true;
    case 0xbe946:if(!ou11_child_index(c,3))return false;r.pc=0xbe98e;return true;
    case 0xbe97e:if(!ou11_child_index(c,5))return false;r.pc=0xbe98e;return true;
    case 0xbe918:r.pc=(r.d[0]&65535U)!=1U?0xbe950:0xbe920;return true; // CMPI.W #1,D0; BNE.W be950.
    case 0xbe950:r.pc=(r.d[0]&65535U)!=2U?0xbe988:0xbe958;return true; // CMPI.W #2,D0; BNE.W be988.
    case 0xbe988:r.pc=0x2a00;return true;                               // JMP 2a00.L.
    case 0xbe98e:r.pc=0xbeab4;return true;                              // BRA.W beab4.
    case 0xbeab4:return am_call(c,0x496c2,0xbeaba);                     // JSR 496c2.L.
    case 0xbeaba:if(!am_write(c,r.a[6],4,0xbeac0))return false;r.pc=0xbeac0;return true; // MOVE.L #beac0,(A6).
    case 0xbeac0:return am_call(c,0x4be06,0xbeac6);                     // (callback) JSR 4be06.L.
    // MOVEA.L 86(A6),A0; JSR 4706c.L.
    case 0xbeac6:if(!ou11_get(c,r.a[6],0x86,4,value))return false;r.a[0]=value;return am_call(c,0x4706c,0xbead0);
    case 0xbead0:r.pc=0xbe888;return true;                              // BRA.W be888.
    // ---- bead4 (child callback): LEA beb7a(PC),A0; MOVE.W 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.W #0,D1;
    // JSR 49290.L.
    case 0xbead4:if(!ou11_node_word(c,0xbeb7a,value))return false;am_word(r.d[0],value);am_word(r.d[1],0);return am_call(c,0x49290,0xbeaec);
    // MOVE.W #77,D0; MOVE.W #14,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xbeaec:am_word(r.d[0],0x77);am_word(r.d[1],0x14);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xbeafe);
    // MOVE.W 76(A6),D0; ADDI.W #14,D0; LEA 26(A6),A0; MOVE.W #223,20(A6); MOVE.L 2001e0.L,22(A6); LEA 26(A6),A0; MOVE.W D0,D1;
    // ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 2001e0.L,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0xbeafe:
        if(!ou11_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]+0x14U);
        r.a[0]=am_index(r.a[6],0x26);if(!ou11_put(c,r.a[6],0x20,2,0x223) || !am_read(c,OU11_BANK_TABLE,4,value) ||
           !ou11_put(c,r.a[6],0x22,4,value))return false;
        r.a[0]=am_index(r.a[6],0x26);am_word(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]<<2);
        if(!am_read(c,OU11_BANK_TABLE,4,value))return false;r.a[1]=value;
        if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xbeb36);
    // LEA beb86(PC),A0; MOVE.W 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D1; MOVE.W D1,68(A6); MOVE.W D1,1e(A6); MOVE.L #beb52,(A6).
    case 0xbeb36:
        if(!ou11_node_word(c,0xbeb86,value))return false;am_word(r.d[1],value);
        if(!ou11_put(c,r.a[6],0x68,2,value) || !ou11_put(c,r.a[6],0x1e,2,value) || !am_write(c,r.a[6],4,0xbeb52))return false;
        r.pc=0xbeb52;return true;
    case 0xbeb52:return am_call(c,0x43e34,0xbeb58);                     // (callback) JSR 43e34.L.
    // LEA beb86(PC),A0; MOVE.W 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D1; ADD.W 46(A6),D1; MOVE.W D1,68(A6); MOVE.W D1,1e(A6);
    // JSR 49fc6.L.
    case 0xbeb58:
        if(!ou11_node_word(c,0xbeb86,value))return false;am_word(r.d[1],value);if(!ou11_get(c,r.a[6],0x46,2,value))return false;
        am_word(r.d[1],r.d[1]+value);
        if(!ou11_put(c,r.a[6],0x68,2,r.d[1]&65535U) || !ou11_put(c,r.a[6],0x1e,2,r.d[1]&65535U))return false;
        return am_call(c,0x49fc6,0xbeb78);
    default:
        // Table entries 4517a+4k: BRA.W to the transcribed target. The displacement WORDs are interior PCs.
        if(r.pc>=OU11_TABLE && r.pc<OU11_TABLE+4U*OU11_TABLE_ENTRIES && ((r.pc-OU11_TABLE)&3U)==0){
            r.pc=OU11_TARGETS[(r.pc-OU11_TABLE)>>2];return true;
        }
        return am_error(c,"unsupported animation objects u11 PC");
    }
}
}
