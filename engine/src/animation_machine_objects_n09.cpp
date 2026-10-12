#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code (addresses passed on, never read here).
const std::uint32_t ON09_WALK_LIST=0xb0d88;     // MOVEA.L #b0d88,A1: animation list for 49f8c.
const std::uint32_t ON09_TURN_LIST=0xb0cdc;     // MOVEA.L #b0cdc,A1.
const std::uint32_t ON09_STAND_LIST=0xb06c8;    // MOVEA.L #b06c8,A1.
const std::uint32_t ON09_SEARCH_A=0xb0660;      // LEA b0660.L,A0: argument of the boundary 4ae4a.
const std::uint32_t ON09_SEARCH_B=0xb067e;      // LEA b067e.L,A0.
const std::uint32_t ON09_PACE=0xcab3e;          // LEA cab3e.L,A0: table for 490ba.
const std::uint32_t ON09_BOX[4]={0xcabba,0xcabd4,0xcabee,0xcac08}; // the four 490ba tables of b0378..b03a2.
const std::uint32_t ON09_RECT=0xb05de;          // LEA b05de.L,A0: rectangle for 1ab02 / 1ab80.
const std::uint32_t ON09_LINK=0xaf80a;          // LEA af80a(PC),A1: data for the boundary 4941e.
const std::uint32_t ON09_PLAYER1=0x100cb8;      // LEA 100cb8.L,A0 (work RAM object).
const std::uint32_t ON09_PLAYER2=0x100da8;      // LEA 100da8.L,A0.
const std::uint32_t ON09_SCROLL=0x5404;         // TST.W 5404(A5).
bool on09_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on09_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
std::int32_t on09_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
bool on09_negative_word(std::uint32_t value) {return (value&0x8000U)!=0U;}
bool on09_negative_long(std::uint32_t value) {return (value&0x80000000U)!=0U;}
// ASR.L #n (n = 1 or 2) with the sign bit copied in.
std::uint32_t on09_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t fill=on09_negative_long(value)?~(0xffffffffU>>n):0U;return (value>>n)|fill;
}
// Bcc on a C returned by a callee: taken_when_clear for BCC, the other target otherwise.
bool on09_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n09 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,(A6) then continue at next_pc.
bool on09_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// MOVE.W #163,20(A6); MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.L.
bool on09_animation(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    if(!on09_put(c,0x20,2,0x163))return false;c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L c(A6),A0; SUBQ.B #1,62(A0); JMP 2a00.L.
bool on09_release(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on09_get(c,0xc,4,value))return false;r.a[0]=value;
    const std::uint32_t address=am_index(r.a[0],0x62);
    if(!am_read(c,address,1,value) || !am_write(c,address,1,(value-1U)&255U))return false;r.pc=0x2a00;return true;
}
// BTST.B #bit,displacement(A6): true when the bit is set.
bool on09_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on09_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET/BCLR/BCHG.B #bit,displacement(A6) (op 0 clear, 1 set, 2 change).
bool on09_bit_op(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,unsigned int op) {
    std::uint32_t value=0;if(!on09_get(c,displacement,1,value))return false;const std::uint32_t mask=1U<<bit;
    value=op==0?(value&~mask):op==1?(value|mask):(value^mask);return on09_put(c,displacement,1,value&255U);
}
// TST.B / TST.W displacement(A6): true when non-zero.
bool on09_nonzero(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,bool& nonzero) {
    std::uint32_t value=0;if(!on09_get(c,displacement,size,value))return false;nonzero=value!=0U;return true;
}
// DIVU.W #divisor,Dn (68000): divisor is a non-zero constant here; quotient > ffff sets V and leaves Dn unchanged.
void on09_divu(std::uint32_t& d,std::uint32_t divisor) {
    const std::uint32_t quotient=d/divisor;if(quotient>0xffffU)return;d=((d%divisor)<<16)|quotient;
}
}
// Objects F4 N09 (old R09/R10; 225 block starts): the node callbacks af4ee af582 af6de af6ec af71a with the installed af630 af676
// af698 (in range) and af92c afc16 (installed out of range), the shared tails af96a b057e b005e/b059e and the helpers b0150 b01e4 b0228
// b0260 b02ec b0326 b0352/b0406 b041c b0468. Boundaries without an executor: 493bc, 4941e and the N08 entries 4945e 4983e 4ae4a.
// Known C: Clear b01c8 b01fa b0320 b042e b0358 b03d8 b041c b0468 b047e, Set b01d6 b01ee b031a b04b6, computed b0406 b0412 b0434
// b0462 (unsigned borrow of CMP/CMPI). The BNE af7b0 is folded into its two predecessors af7a0 and af7aa. N09 writes no port and
// changes no bank.
bool animation_objects_n09_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool flag=false;
    switch(r.pc) {
    // ---- af4ee (callback): MOVE.B a1(A6),D0; LSL.B #1,D0; BTST.B #1,15(A6); BEQ.W af522.
    case 0xaf4ee:
        if(!on09_get(c,0xa1,1,value))return false;am_byte(r.d[0],value<<1);if(!on09_bit(c,0x15,1,flag))return false;
        r.pc=flag?0xaf4fe:0xaf522;return true;
    // ADDI.B #10,D0; BCHG.B #0,15(A6); MOVE.B D0,-(A7); MOVEQ #0,D0; MOVE.L D0,36(A6); MOVE.W #fff8,D0; SWAP D0; MOVE.L D0,3a(A6);
    // JSR 4be34.L.
    case 0xaf4fe:
        am_byte(r.d[0],r.d[0]+0x10U);if(!on09_bit_op(c,0x15,0,2) || !am_push(c,1,r.d[0]&255U))return false;r.d[0]=0;
        if(!on09_put(c,0x36,4,0))return false;r.d[0]=0xfff80000U;if(!on09_put(c,0x3a,4,r.d[0]))return false;return am_call(c,0x4be34,0xaf520);
    case 0xaf520:if(!am_pop(c,1,value))return false;am_byte(r.d[0],value);r.pc=0xaf522;return true; // MOVE.B (A7)+,D0.
    // MOVE.B D0,8c(A6); CLR.B 8d(A6); MOVEQ #0,D0; MOVE.L D0,36/3a(A6); MOVE.L #ffffb000,7e(A6); animation b0d88.
    case 0xaf522:
        if(!on09_put(c,0x8c,1,r.d[0]&255U) || !on09_put(c,0x8d,1,0))return false;r.d[0]=0;
        if(!on09_put(c,0x36,4,0) || !on09_put(c,0x3a,4,0) || !on09_put(c,0x7e,4,0xffffb000U))return false;
        return on09_animation(c,ON09_WALK_LIST,0xaf552);
    case 0xaf552:return am_call(c,0x49a58,0xaf558);                          // JSR 49a58.L.
    case 0xaf5be:return am_call(c,0x49a58,0xaf5c4);
    case 0xaf7c6:return am_call(c,0x49a58,0xaf7cc);
    case 0xafc3a:return am_call(c,0x49a58,0xafc40);
    case 0xb0352:return am_call(c,0x49a58,0xb0358);
    // MOVE.W D0,D1; BEQ.W af56e.
    case 0xaf558:am_word(r.d[1],r.d[0]);r.pc=(r.d[0]&65535U)==0U?0xaf56e:0xaf55e;return true;
    // ANDI.W #ff,D0; ADDI.W #100,D0; TST.W D1; BPL.W af56e; NEG.W D0 (af56c).
    case 0xaf55e:am_word(r.d[0],(r.d[0]&255U)+0x100U);r.pc=on09_negative_word(r.d[1])?0xaf56c:0xaf56e;return true;
    case 0xaf56c:case 0xaf6b4:case 0xb0276:case 0xb0460:case 0xafc50:am_word(r.d[0],0U-(r.d[0]&65535U)); // NEG.W D0.
        r.pc=r.pc==0xaf56c?0xaf56e:r.pc==0xaf6b4?0xaf6b6:r.pc==0xb0276?0xb0278:r.pc==0xb0460?0xb0462:0xafc52;return true;
    // MOVE.W D0,8e(A6); BCLR.B #1,15(A6); ST.B 9b(A6); MOVE.L #af582,(A6).
    case 0xaf56e:
        if(!on09_put(c,0x8e,2,r.d[0]&65535U) || !on09_bit_op(c,0x15,1,0) || !on09_put(c,0x9b,1,0xff))return false;
        return on09_install(c,0xaf582,0xaf582);
    // ---- af582 (installed): MOVE.W 8e(A6),D0; ADD.W D0,8c(A6); ANDI.B #1f,8c(A6); MOVE.L 7e(A6),D0; ADD.L D0,3a(A6); JSR 4be34.L.
    case 0xaf582:
        if(!on09_get(c,0x8e,2,value))return false;am_word(r.d[0],value);
        if(!on09_get(c,0x8c,2,value) || !on09_put(c,0x8c,2,(value+r.d[0])&65535U))return false;
        if(!on09_get(c,0x8c,1,value) || !on09_put(c,0x8c,1,value&0x1fU))return false;
        if(!on09_get(c,0x7e,4,value))return false;r.d[0]=value;
        if(!on09_get(c,0x3a,4,value) || !on09_put(c,0x3a,4,value+r.d[0]))return false;return am_call(c,0x4be34,0xaf59e);
    case 0xaf59e:return am_call(c,0x49fc6,0xaf5a4);                          // JSR 49fc6.L.
    case 0xaf69e:return am_call(c,0x49fc6,0xaf6a4);
    case 0xaf932:return am_call(c,0x49fc6,0xaf938);
    case 0xafc8c:return am_call(c,0x49fc6,0xafc92);
    // TST.B 9b(A6); BEQ.W af5b4; JSR b0468(PC); SCC.B 9b(A6).
    case 0xaf5a4:if(!on09_nonzero(c,0x9b,1,flag))return false;r.pc=flag?0xaf5ac:0xaf5b4;return true;
    case 0xaf5ac:return am_call(c,0xb0468,0xaf5b0);
    case 0xaf5b0:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n09 caller requires known carry");
        if(!on09_put(c,0x9b,1,r.carry==AnimationCarryClear?0xffU:0U))return false;r.pc=0xaf5b4;return true;
    // BTST.B #7,15(A6); BEQ.W af62c.
    case 0xaf5b4:if(!on09_bit(c,0x15,7,flag))return false;r.pc=flag?0xaf5be:0xaf62c;return true;
    // MOVE.W D0,D1; ANDI.W #1000,D1; SEQ.B D1; AND.B 9b(A6),D1; BEQ.W af608.
    case 0xaf5c4:
        am_word(r.d[1],r.d[0]&0x1000U);am_byte(r.d[1],(r.d[1]&65535U)==0U?0xffU:0U);
        if(!on09_get(c,0x9b,1,value))return false;am_byte(r.d[1],r.d[1]&value);r.pc=(r.d[1]&255U)==0U?0xaf608:0xaf5d4;return true;
    // ANDI.W #1f0,D0; SUBI.W #100,D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,36(A6); MOVE.L 3a(A6),D0; ASR.L #2,D0; NEG.L D0;
    // CMPI.L #20000,D0; BCC.W af5fc (unsigned).
    case 0xaf5d4:
        am_word(r.d[0],(r.d[0]&0x1f0U)-0x100U);r.d[0]=am_extend_word(r.d[0])<<8;if(!on09_put(c,0x36,4,r.d[0]))return false;
        if(!on09_get(c,0x3a,4,value))return false;r.d[0]=0U-on09_asr(value,2);r.pc=r.d[0]>=0x20000U?0xaf5fc:0xaf5f6;return true;
    case 0xaf5f6:r.d[0]=0x20000;r.pc=0xaf5fc;return true;                    // MOVE.L #20000,D0.
    // MOVE.L D0,3a(A6); SF.B 9b(A6); BRA.W af62c.
    case 0xaf5fc:if(!on09_put(c,0x3a,4,r.d[0]) || !on09_put(c,0x9b,1,0))return false;r.pc=0xaf62c;return true;
    // TST.W D0; BPL.W af614; BCHG.B #0,15(A6).
    case 0xaf608:r.pc=on09_negative_word(r.d[0])?0xaf60e:0xaf614;return true;
    case 0xaf60e:if(!on09_bit_op(c,0x15,0,2))return false;r.pc=0xaf614;return true;
    // ANDI.B #3,D0; BEQ.W af626.
    case 0xaf614:am_byte(r.d[0],r.d[0]&3U);r.pc=(r.d[0]&255U)==0U?0xaf626:0xaf61c;return true;
    case 0xaf61c:return on09_install(c,0xaf630,0xaf62c);                     // MOVE.L #af630,(A6); BRA.W af62c.
    case 0xaf626:return on09_install(c,0xafbbe,0xaf62c);                     // MOVE.L #afbbe,(A6).
    case 0xaf62c:case 0xaf6da:case 0xaf806:case 0xaf966:r.pc=0xaf96a;return true; // BRA.W af96a.

    // ---- af630 (installed): MOVEQ #0,D0; JSR 4c1de.L; MOVE.W D7,D0; BSR.W b02c8.
    case 0xaf630:r.d[0]=0;return am_call(c,0x4c1de,0xaf638);
    case 0xaf638:am_word(r.d[0],r.d[7]);return am_call(c,0xb02c8,0xaf63e);
    // MOVE.B D0,a1(A6); MOVE.B D0,a0(A6); JSR b0206(PC).
    case 0xaf63e:if(!on09_put(c,0xa1,1,r.d[0]&255U) || !on09_put(c,0xa0,1,r.d[0]&255U))return false;return am_call(c,0xb0206,0xaf64a);
    case 0xaf64a:return on09_carry(c,0xaf65a,0xaf64e);                        // BCC.W af65a (C returned by b0206).
    // MOVEA.L 76(A6),A0; MOVE.W 42(A0),D0; BRA.W af65e.
    case 0xaf64e:
        if(!on09_get(c,0x76,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x42),2,value))return false;
        am_word(r.d[0],value);r.pc=0xaf65e;return true;
    case 0xaf65a:am_word(r.d[0],0xa0);r.pc=0xaf65e;return true;             // MOVE.W #a0,D0.
    // CMP.W 42(A6),D0; SGT.B D0; BTST.B #0,15(A6); SNE.B D1; EOR.B D0,D1; BNE.W af676.
    case 0xaf65e:
        if(!on09_get(c,0x42,2,value))return false;am_byte(r.d[0],on09_signed_word(r.d[0])>on09_signed_word(value)?0xffU:0U);
        if(!on09_bit(c,0x15,0,flag))return false;am_byte(r.d[1],flag?0xffU:0U);am_byte(r.d[1],r.d[1]^r.d[0]);
        r.pc=(r.d[1]&255U)!=0U?0xaf676:0xaf672;return true;
    case 0xaf672:r.pc=0xaf6de;return true;                                   // BRA.W af6de.
    case 0xaf676:return am_call(c,0x496c2,0xaf67c);                          // JSR 496c2.L.
    case 0xaf67c:return on09_animation(c,ON09_TURN_LIST,0xaf692);
    case 0xaf692:return on09_install(c,0xaf698,0xaf698);                     // MOVE.L #af698,(A6).
    // ---- af698 (installed): JSR 4be2c.L; JSR 49fc6.L; BCC.W af6da.
    case 0xaf698:return am_call(c,0x4be2c,0xaf69e);
    case 0xaf6a4:return on09_carry(c,0xaf6da,0xaf6a8);
    // MOVEQ #5,D0; BTST.B #0,15(A6); BEQ.W af6b6; NEG.W D0 (af6b4, above).
    case 0xaf6a8:r.d[0]=5;if(!on09_bit(c,0x15,0,flag))return false;r.pc=flag?0xaf6b4:0xaf6b6;return true;
    // SWAP D0; MOVE.L D0,64(A6); JSR 4bfa4.L.
    case 0xaf6b6:am_swap(r.d[0]);if(!on09_put(c,0x64,4,r.d[0]))return false;return am_call(c,0x4bfa4,0xaf6c2);
    case 0xaf6c2:return am_call(c,0x492d0,0xaf6c8);                          // JSR 492d0.L.
    // MOVE.B #4,a1(A6); MOVE.B #4,a0(A6); MOVE.L #af6de,(A6).
    case 0xaf6c8:if(!on09_put(c,0xa1,1,4) || !on09_put(c,0xa0,1,4))return false;return on09_install(c,0xaf6de,0xaf6da);

    // ---- af6de (callback): BCLR.B #1,15(A6); SF.B 9f(A6); BRA.W af6f6. af6ec (callback): BSET.B #1,15(A6); ST.B 9f(A6).
    case 0xaf6de:if(!on09_bit_op(c,0x15,1,0) || !on09_put(c,0x9f,1,0))return false;r.pc=0xaf6f6;return true;
    case 0xaf6ec:if(!on09_bit_op(c,0x15,1,1) || !on09_put(c,0x9f,1,0xff))return false;r.pc=0xaf6f6;return true;
    case 0xaf6f6:return on09_animation(c,ON09_STAND_LIST,0xaf70c);
    case 0xaf70c:return am_call(c,0xb0326,0xaf710);                          // JSR b0326(PC).
    // ST.B 9d(A6); MOVE.L #af71a,(A6).
    case 0xaf710:if(!on09_put(c,0x9d,1,0xff))return false;return on09_install(c,0xaf71a,0xaf71a);
    // ---- af71a (installed): MOVE.B 61(A6),-(A7); JSR 4be06.L.
    case 0xaf71a:if(!on09_get(c,0x61,1,value) || !am_push(c,1,value))return false;return am_call(c,0x4be06,0xaf724);
    // MOVE.B (A7)+,D0; ANDI.B #2,D0; OR.B D0,61(A6); JSR 49fc6.L.
    case 0xaf724:
        if(!am_pop(c,1,value))return false;am_byte(r.d[0],value&2U);
        if(!on09_get(c,0x61,1,value) || !on09_put(c,0x61,1,(value|r.d[0])&255U))return false;return am_call(c,0x49fc6,0xaf734);
    case 0xaf734:return am_call(c,0xb02ec,0xaf738);
    case 0xaf738:return on09_carry(c,0xaf742,0xaf73c);                        // BCC.W af742 (C returned by b02ec).
    case 0xaf73c:return on09_install(c,0xaf812,0xaf742);                     // MOVE.L #af812,(A6) (out-of-range target).
    // TST.B a3(A6); BNE.W af758.
    case 0xaf742:if(!on09_nonzero(c,0xa3,1,flag))return false;r.pc=flag?0xaf758:0xaf74a;return true;
    case 0xaf74a:return am_call(c,0xb041c,0xaf74e);
    case 0xaf74e:return on09_carry(c,0xaf758,0xaf752);                        // BCC.W af758 (C returned by b041c).
    case 0xaf752:return on09_install(c,0xaf4ee,0xaf758);
    // TST.B 9f(A6); BNE.W af76e.
    case 0xaf758:if(!on09_nonzero(c,0x9f,1,flag))return false;r.pc=flag?0xaf76e:0xaf760;return true;
    case 0xaf760:return am_call(c,0xb0352,0xaf764);
    case 0xaf764:return on09_carry(c,0xaf76e,0xaf768);                        // BCC.W af76e (C returned by b0352).
    case 0xaf768:return on09_install(c,0xaf8cc,0xaf76e);                     // MOVE.L #af8cc,(A6) (out-of-range target).
    // BTST.B #0,61(A6); BEQ.W af790.
    case 0xaf76e:if(!on09_bit(c,0x61,0,flag))return false;r.pc=flag?0xaf778:0xaf790;return true;
    // TST.B 9f(A6); BNE.W af78a; MOVE.L #af676,(A6); BRA.W af790 / MOVE.L #af4ee,(A6).
    case 0xaf778:if(!on09_nonzero(c,0x9f,1,flag))return false;r.pc=flag?0xaf78a:0xaf780;return true;
    case 0xaf780:return on09_install(c,0xaf676,0xaf790);
    case 0xaf78a:return on09_install(c,0xaf4ee,0xaf790);
    // TST.B a3(A6); BNE.W af7be; TST.B 9f(A6); BNE.W af7aa.
    case 0xaf790:if(!on09_nonzero(c,0xa3,1,flag))return false;r.pc=flag?0xaf7be:0xaf798;return true;
    case 0xaf798:if(!on09_nonzero(c,0x9f,1,flag))return false;r.pc=flag?0xaf7aa:0xaf7a0;return true;
    // BTST.B #7,15(A6); BRA.W af7b0; BNE.W af7ba (folded) / BTST.B #1,61(A6); BNE.W af7ba.
    case 0xaf7a0:if(!on09_bit(c,0x15,7,flag))return false;r.pc=flag?0xaf7ba:0xaf7b4;return true;
    case 0xaf7aa:if(!on09_bit(c,0x61,1,flag))return false;r.pc=flag?0xaf7ba:0xaf7b4;return true;
    case 0xaf7b4:return on09_install(c,0xaf4ee,0xaf7ba);
    case 0xaf7ba:r.pc=0xaf7da;return true;                                   // BRA.W af7da.
    // TST.W 5404(A5); BEQ.W af7da.
    case 0xaf7be:if(!am_read(c,am_index(r.a[5],ON09_SCROLL),2,value))return false;r.pc=value!=0U?0xaf7c6:0xaf7da;return true;
    // ANDI.W #f,D0; BNE.W af7da.
    case 0xaf7cc:am_word(r.d[0],r.d[0]&15U);r.pc=(r.d[0]&65535U)!=0U?0xaf7da:0xaf7d4;return true;
    case 0xaf7d4:return on09_install(c,0xaf4ee,0xaf7da);
    // MOVE.B 9a(A6),D0; AND.B 9f(A6),D0; BEQ.W af806.
    case 0xaf7da:
        if(!on09_get(c,0x9a,1,value) || !on09_get(c,0x9f,1,other))return false;am_byte(r.d[0],value&other);
        r.pc=(r.d[0]&255U)==0U?0xaf806:0xaf7e6;return true;
    // MOVEA.L c(A6),A0; LEA af80a(PC),A1; JSR 4941e.L (boundary).
    case 0xaf7e6:if(!on09_get(c,0xc,4,value))return false;r.a[0]=value;r.a[1]=ON09_LINK;return am_call(c,0x4941e,0xaf7f4);
    case 0xaf7f4:return on09_carry(c,0xaf7f8,0xaf806);                        // BCS.W af806.
    case 0xaf7f8:case 0xaf93c:case 0xb058e:case 0xb05ae:return on09_release(c);

    // ---- af92c (installed by af926): JSR 4be06.L; JSR 49fc6.L; BCC.W af94a.
    case 0xaf92c:return am_call(c,0x4be06,0xaf932);
    case 0xaf938:return on09_carry(c,0xaf94a,0xaf93c);
    // TST.B 9c(A6); BEQ.W af966; LEA b0660.L,A0; JSR 4ae4a.L (boundary, N08); CMPI.W #0,D0; SEQ.B 9c(A6).
    case 0xaf94a:if(!on09_nonzero(c,0x9c,1,flag))return false;r.pc=flag?0xaf952:0xaf966;return true;
    case 0xaf952:r.a[0]=ON09_SEARCH_A;return am_call(c,0x4ae4a,0xaf95e);
    case 0xaf95e:if(!on09_put(c,0x9c,1,(r.d[0]&65535U)==0U?0xffU:0U))return false;r.pc=0xaf966;return true;
    // ---- af96a (shared tail): JSR 4b54e.L; BCC.W af98c; BTST.B #7,61(A6); BEQ.W af988; MOVE.L #af990,(A6) / CLR.B 5e(A6).
    case 0xaf96a:return am_call(c,0x4b54e,0xaf970);
    case 0xaf970:return on09_carry(c,0xaf98c,0xaf974);
    case 0xaf974:if(!on09_bit(c,0x61,7,flag))return false;r.pc=flag?0xaf97e:0xaf988;return true;
    case 0xaf97e:return on09_install(c,0xaf990,0xaf98c);                     // out-of-range target; BRA.W af98c.
    case 0xaf988:if(!on09_put(c,0x5e,1,0))return false;r.pc=0xaf98c;return true;
    case 0xaf98c:r.pc=0xb057e;return true;                                   // BRA.W b057e.

    // ---- afc16 (installed by afc10): BTST.B #7,61(A6); BEQ.W afc32; TST.B 63(A6); BNE.W afc32; JSR 8ff4.L; ST.B 63(A6).
    case 0xafc16:if(!on09_bit(c,0x61,7,flag))return false;r.pc=flag?0xafc20:0xafc32;return true;
    case 0xafc20:if(!on09_nonzero(c,0x63,1,flag))return false;r.pc=flag?0xafc32:0xafc28;return true;
    case 0xafc28:return am_call(c,0x8ff4,0xafc2e);
    case 0xafc2e:if(!on09_put(c,0x63,1,0xff))return false;r.pc=0xafc32;return true;
    // SUBQ.W #1,96(A6); BPL.W afc6c.
    case 0xafc32:
        if(!on09_get(c,0x96,2,value))return false;value=(value-1U)&65535U;if(!on09_put(c,0x96,2,value))return false;
        r.pc=on09_negative_word(value)?0xafc3a:0xafc6c;return true;
    // MOVE.W D0,D1; ANDI.W #ff,D0; ADDI.W #20,D0; TST.W D1; BPL.W afc52; NEG.W D0 (afc50, above).
    case 0xafc40:am_word(r.d[1],r.d[0]);am_word(r.d[0],(r.d[0]&255U)+0x20U);r.pc=on09_negative_word(r.d[1])?0xafc50:0xafc52;return true;
    // EXT.L D0; LSL.L #8,D0; MOVE.L D0,64(A6); JSR 49a58.L.
    case 0xafc52:r.d[0]=am_extend_word(r.d[0])<<8;if(!on09_put(c,0x64,4,r.d[0]))return false;return am_call(c,0x49a58,0xafc60);
    // ANDI.W #1f,D0; ADDI.W #a,D0; MOVE.W D0,96(A6).
    case 0xafc60:am_word(r.d[0],(r.d[0]&0x1fU)+0xaU);if(!on09_put(c,0x96,2,r.d[0]&65535U))return false;r.pc=0xafc6c;return true;
    // MOVE.W 64(A6),D0; ASL.W #1,D0; JSR 4c1de.L.
    case 0xafc6c:if(!on09_get(c,0x64,2,value))return false;am_word(r.d[0],value<<1);return am_call(c,0x4c1de,0xafc78);
    case 0xafc78:return on09_carry(c,0xafc86,0xafc7c);                        // BCC.W afc86 (C returned by 4c1de).
    case 0xafc7c:return am_call(c,0x4bfa4,0xafc82);
    case 0xafc82:r.pc=0xafc8c;return true;                                   // BRA.W afc8c.
    case 0xafc86:return am_call(c,0x4be06,0xafc8c);
    case 0xafc92:return on09_carry(c,0xafcb0,0xafc96);
    case 0xafc96:if(!on09_bit(c,0x61,7,flag))return false;r.pc=flag?0xafca0:0xafcaa;return true;
    case 0xafca0:return on09_install(c,0xafed8,0xafcb0);                     // out-of-range targets afed8 / afcbe.
    case 0xafcaa:return on09_install(c,0xafcbe,0xafcb0);
    case 0xafcb0:if(!on09_bit(c,0x61,7,flag))return false;r.pc=flag?0xafcba:0xaf96a;return true;
    case 0xafcba:r.pc=0xb005e;return true;                                   // BRA.W b005e.
    case 0xb005e:r.pc=0xb059e;return true;                                   // BRA.W b059e.

    // ---- b0150 (helper): MOVE.L 3e/32/2e(A6),-(A7); MOVE.L 7a(A6),D0; MOVE.B 9e(A6),D1; JSR 443d2.L.
    case 0xb0150:
        if(!on09_get(c,0x3e,4,value) || !am_push(c,4,value) || !on09_get(c,0x32,4,value) || !am_push(c,4,value) ||
            !on09_get(c,0x2e,4,value) || !am_push(c,4,value) || !on09_get(c,0x7a,4,value))return false;
        r.d[0]=value;if(!on09_get(c,0x9e,1,value))return false;am_byte(r.d[1],value);return am_call(c,0x443d2,0xb016a);
    // NEG.L D1; MOVE.L D1,36(A6); MOVE.L D0,3a(A6); JSR 4be34.L.
    case 0xb016a:r.d[1]=0U-r.d[1];if(!on09_put(c,0x36,4,r.d[1]) || !on09_put(c,0x3a,4,r.d[0]))return false;return am_call(c,0x4be34,0xb017a);
    // BTST.B #1,61(A6); BNE.W b01aa.
    case 0xb017a:if(!on09_bit(c,0x61,1,flag))return false;r.pc=flag?0xb01aa:0xb0184;return true;
    // MOVE.L 7a(A6),D0; BPL.W b018e; NEG.L D0.
    case 0xb0184:if(!on09_get(c,0x7a,4,value))return false;r.d[0]=value;r.pc=on09_negative_long(value)?0xb018c:0xb018e;return true;
    case 0xb018c:case 0xb0494:r.d[0]=0U-r.d[0];r.pc=r.pc==0xb018c?0xb018e:0xb0496;return true;
    // MOVE.B 9e(A6),D1; JSR 443d2.L.
    case 0xb018e:if(!on09_get(c,0x9e,1,value))return false;am_byte(r.d[1],value);return am_call(c,0x443d2,0xb0198);
    // NEG.L D0; NEG.L D1; MOVE.L D0,36(A6); MOVE.L D1,3a(A6); JSR 4be34.L.
    case 0xb0198:
        r.d[0]=0U-r.d[0];r.d[1]=0U-r.d[1];if(!on09_put(c,0x36,4,r.d[0]) || !on09_put(c,0x3a,4,r.d[1]))return false;
        return am_call(c,0x4be34,0xb01aa);
    // MOVEM.L (A7)+,D0-D2; BTST.B #1,61(A6); BNE.W b01d6.
    case 0xb01aa:
        for(unsigned int i=0;i<3;++i)if(!am_pop(c,4,r.d[i]))return false;
        if(!on09_bit(c,0x61,1,flag))return false;r.pc=flag?0xb01d6:0xb01b8;return true;
    // MOVEM.L D0-D1,2e(A6); MOVE.L D2,3e(A6); JSR 4be06.L.
    case 0xb01b8:
        if(!on09_put(c,0x2e,4,r.d[0]) || !on09_put(c,0x32,4,r.d[1]) || !on09_put(c,0x3e,4,r.d[2]))return false;
        return am_call(c,0x4be06,0xb01c8);
    // BCLR.B #1,61(A6); ANDI.B #fe,CCR; BRA.W b01e2.
    case 0xb01c8:if(!on09_bit_op(c,0x61,1,0))return false;r.carry=AnimationCarryClear;r.pc=0xb01e2;return true;
    // MOVE.W D4,D0; LSR.W #8,D0; MOVE.B D0,9e(A6); ORI.B #1,CCR.
    case 0xb01d6:
        am_word(r.d[0],(r.d[4]&65535U)>>8);if(!on09_put(c,0x9e,1,r.d[0]&255U))return false;r.carry=AnimationCarrySet;r.pc=0xb01e2;return true;
    case 0xb01e2:case 0xb0204:case 0xb023c:case 0xb0268:case 0xb029c:case 0xb02b4:case 0xb0360:case 0xb0370:case 0xb03f4:
    case 0xb03fe:case 0xb041a:case 0xb0424:case 0xb0444:case 0xb044e:case 0xb0470:case 0xb04ca:case 0xb059c:case 0xb05bc:
        return am_return(c);                                                 // RTS.
    // ---- b01e4: JSR 4945e.L (boundary, N08); BCS.W b01fa; MOVE.L A0,76(A6); ORI.B #1,CCR; BRA.W b0204 / MOVEQ #0,D0;
    // MOVE.L D0,76(A6); ANDI.B #fe,CCR.
    case 0xb01e4:return am_call(c,0x4945e,0xb01ea);
    case 0xb0486:return am_call(c,0x4945e,0xb048c);
    case 0xb01ea:return on09_carry(c,0xb01ee,0xb01fa);
    case 0xb01ee:if(!on09_put(c,0x76,4,r.a[0]))return false;r.carry=AnimationCarrySet;r.pc=0xb0204;return true;
    case 0xb01fa:r.d[0]=0;if(!on09_put(c,0x76,4,0))return false;r.carry=AnimationCarryClear;r.pc=0xb0204;return true;
    // ---- b0228 (helper): MOVE.L 76(A6),D0; BEQ.W b023e; MOVEA.L D0,A0; JSR 493bc.L (boundary); BCC.W b023e; RTS.
    case 0xb0228:if(!on09_get(c,0x76,4,value))return false;r.d[0]=value;r.pc=value==0U?0xb023e:0xb0230;return true;
    case 0xb0230:r.a[0]=r.d[0];return am_call(c,0x493bc,0xb0238);
    case 0xb0238:return on09_carry(c,0xb023e,0xb023c);
    case 0xb023e:r.pc=0xb01e4;return true;                                   // BRA.B b01e4.

    // ---- b0260 (LONG 4a704): TST.B 9d(A6); BNE.W b026a; RTS.
    case 0xb0260:if(!on09_nonzero(c,0x9d,1,flag))return false;r.pc=flag?0xb026a:0xb0268;return true;
    // MOVE.W (A0),D0; BTST.B #0,15(A6); BNE.W b0278; NEG.W D0 (b0276, above).
    case 0xb026a:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);if(!on09_bit(c,0x15,0,flag))return false;
        r.pc=flag?0xb0278:0xb0276;return true;
    // SWAP D0; CLR.W D0; TST.B 9f(A6); BNE.W b02a4.
    case 0xb0278:am_swap(r.d[0]);am_word(r.d[0],0);if(!on09_nonzero(c,0x9f,1,flag))return false;r.pc=flag?0xb02a4:0xb0284;return true;
    // MOVE.L D0,64(A6); MOVE.L D0,36(A6); JSR 4bfa4.L.
    case 0xb0284:if(!on09_put(c,0x64,4,r.d[0]) || !on09_put(c,0x36,4,r.d[0]))return false;return am_call(c,0x4bfa4,0xb0292);
    // BTST.B #7,15(A6); BNE.W b029e; RTS.
    case 0xb0292:if(!on09_bit(c,0x15,7,flag))return false;r.pc=flag?0xb029e:0xb029c;return true;
    case 0xb029e:am_word(r.d[0],r.d[7]);r.pc=0xb02b8;return true;           // MOVE.W D7,D0; BRA.W b02b8.
    // MOVE.L D0,7a(A6); MOVE.L D0,36(A6); JSR b0150(PC).
    case 0xb02a4:if(!on09_put(c,0x7a,4,r.d[0]) || !on09_put(c,0x36,4,r.d[0]))return false;return am_call(c,0xb0150,0xb02b0);
    case 0xb02b0:return on09_carry(c,0xb02b4,0xb02b6);                        // BCS.W b02b6.
    case 0xb02b6:am_word(r.d[0],r.d[4]);r.pc=0xb02b8;return true;           // MOVE.W D4,D0.
    case 0xb02b8:return am_call(c,0xb02c8,0xb02bc);                          // BSR.W b02c8 (U16).
    // MOVE.B a0(A6),a1(A6); MOVE.B D0,a0(A6); RTS.
    case 0xb02bc:
        if(!on09_get(c,0xa0,1,value) || !on09_put(c,0xa1,1,value) || !on09_put(c,0xa0,1,r.d[0]&255U))return false;return am_return(c);

    // ---- b02ec (helper): MOVE.B a0(A6),D0; MOVE.B a1(A6),D1; CMP.B D0,D1; BEQ.W b0320.
    case 0xb02ec:
        if(!on09_get(c,0xa0,1,value) || !on09_get(c,0xa1,1,other))return false;am_byte(r.d[0],value);am_byte(r.d[1],other);
        r.pc=(r.d[0]&255U)==(r.d[1]&255U)?0xb0320:0xb02fa;return true;
    case 0xb02fa:r.pc=(r.d[0]&255U)>2U?0xb030a:0xb0302;return true;         // CMPI.B #2,D0; BHI.W b030a.
    case 0xb0302:r.pc=(r.d[1]&255U)<=2U?0xb0320:0xb030a;return true;        // CMPI.B #2,D1; BLS.W b0320.
    case 0xb030a:r.pc=(r.d[0]&255U)<6U?0xb031a:0xb0312;return true;         // CMPI.B #6,D0; BCS.W b031a.
    case 0xb0312:r.pc=(r.d[1]&255U)>=6U?0xb0320:0xb031a;return true;        // CMPI.B #6,D1; BCC.W b0320.
    case 0xb031a:r.carry=AnimationCarrySet;return am_return(c);             // ORI.B #1,CCR; RTS.
    case 0xb0320:case 0xb042e:r.carry=AnimationCarryClear;return am_return(c); // ANDI.B #fe,CCR; RTS.
    // ---- b0326 (helper): LEA cab3e.L,A0; JSR 490ba.L.
    case 0xb0326:r.a[0]=ON09_PACE;return am_call(c,0x490ba,0xb0332);
    // EXT.L D0; LSL.L #8,D0; DIVU.W #50,D0; MOVE.W D0,2c(A6); JSR 49a58.L.
    case 0xb0332:
        r.d[0]=am_extend_word(r.d[0])<<8;on09_divu(r.d[0],0x50);if(!on09_put(c,0x2c,2,r.d[0]&65535U))return false;
        return am_call(c,0x49a58,0xb0344);
    // ANDI.W #3f,D0; SUBI.W #20,D0; ADD.W D0,2c(A6); RTS.
    case 0xb0344:
        am_word(r.d[0],(r.d[0]&0x3fU)-0x20U);if(!on09_get(c,0x2c,2,value) || !on09_put(c,0x2c,2,(value+r.d[0])&65535U))return false;
        return am_return(c);
    // ---- b0352 (helper, JSR 49a58 above): ANDI.B #7,D0; BEQ.W b0362; RTS (C clear).
    case 0xb0358:am_byte(r.d[0],r.d[0]&7U);r.carry=AnimationCarryClear;r.pc=(r.d[0]&255U)==0U?0xb0362:0xb0360;return true;
    // MOVEQ #0,D0; MOVEQ #0,D1; JSR 4983e.L (boundary, N08); BCS.W b0372; RTS.
    case 0xb0362:r.d[0]=0;r.d[1]=0;return am_call(c,0x4983e,0xb036c);
    case 0xb036c:return on09_carry(c,0xb0370,0xb0372);
    case 0xb0372:return am_call(c,0x49370,0xb0378);                          // JSR 49370.L.
    // MOVE.B D0,-(A7) / MOVE.W D0,-(A7); LEA table.L,A0; JSR 490ba.L.
    case 0xb0378:if(!am_push(c,1,r.d[0]&255U))return false;r.a[0]=ON09_BOX[0];return am_call(c,0x490ba,0xb0386);
    case 0xb0386:if(!am_push(c,2,r.d[0]&65535U))return false;r.a[0]=ON09_BOX[1];return am_call(c,0x490ba,0xb0394);
    case 0xb0394:if(!am_push(c,2,r.d[0]&65535U))return false;r.a[0]=ON09_BOX[2];return am_call(c,0x490ba,0xb03a2);
    case 0xb03a2:if(!am_push(c,2,r.d[0]&65535U))return false;r.a[0]=ON09_BOX[3];return am_call(c,0x490ba,0xb03b0);
    // MOVE.W D0,D3; MOVE.W (A7)+,D2; MOVE.W (A7)+,D1; MOVE.W (A7)+,D0; BTST.B #0,15(A6); BEQ.W b03c6.
    case 0xb03b0:
        am_word(r.d[3],r.d[0]);if(!am_pop(c,2,value))return false;am_word(r.d[2],value);if(!am_pop(c,2,value))return false;
        am_word(r.d[1],value);if(!am_pop(c,2,value))return false;am_word(r.d[0],value);if(!on09_bit(c,0x15,0,flag))return false;
        r.pc=flag?0xb03c2:0xb03c6;return true;
    case 0xb03c2:am_word(r.d[0],0U-((r.d[0]+r.d[1])&65535U));r.pc=0xb03c6;return true; // ADD.W D1,D0; NEG.W D0.
    // ADD.W 42(A6),D0; BTST.B #1,15(A6); BEQ.W b03d8.
    case 0xb03c6:
        if(!on09_get(c,0x42,2,value))return false;am_word(r.d[0],r.d[0]+value);if(!on09_bit(c,0x15,1,flag))return false;
        r.pc=flag?0xb03d4:0xb03d8;return true;
    case 0xb03d4:am_word(r.d[2],0U-((r.d[2]+r.d[3])&65535U));r.pc=0xb03d8;return true; // ADD.W D3,D2; NEG.W D2.
    // ADD.W 46(A6),D2; MOVE.B (A7)+,D7 (C clear); BTST.B #0,D7; BEQ.W b03f6.
    case 0xb03d8:
        if(!on09_get(c,0x46,2,value))return false;am_word(r.d[2],r.d[2]+value);if(!am_pop(c,1,value))return false;am_byte(r.d[7],value);
        r.carry=AnimationCarryClear;r.pc=(r.d[7]&1U)!=0U?0xb03e6:0xb03f6;return true;
    case 0xb03e6:r.a[0]=ON09_PLAYER1;return am_call(c,0xb0406,0xb03f0);    // LEA 100cb8.L,A0; BSR.W b0406.
    case 0xb03f0:return on09_carry(c,0xb03f6,0xb03f4);                        // BCC.W b03f6 (C returned by b0406).
    case 0xb03f6:r.pc=(r.d[7]&2U)!=0U?0xb0400:0xb03fe;return true;          // BTST.B #1,D7; BNE.W b0400.
    case 0xb0400:r.a[0]=ON09_PLAYER2;r.pc=0xb0406;return true;              // LEA 100da8.L,A0.
    // ---- b0406: MOVE.W 42(A0),D4; SUB.W D0,D4; CMP.W D1,D4; BCC.W b041a.
    case 0xb0406:
        if(!am_read(c,am_index(r.a[0],0x42),2,value))return false;am_word(r.d[4],value-r.d[0]);
        flag=(r.d[4]&65535U)<(r.d[1]&65535U);r.carry=flag?AnimationCarrySet:AnimationCarryClear;r.pc=flag?0xb0412:0xb041a;return true;
    // MOVE.W 46(A0),D4; SUB.W D2,D4; CMP.W D3,D4.
    case 0xb0412:
        if(!am_read(c,am_index(r.a[0],0x46),2,value))return false;am_word(r.d[4],value-r.d[2]);
        r.carry=(r.d[4]&65535U)<(r.d[3]&65535U)?AnimationCarrySet:AnimationCarryClear;r.pc=0xb041a;return true;
    // ---- b041c (helper): TST.B 9f(A6); BNE.W b0426; RTS (C clear).
    case 0xb041c:if(!on09_nonzero(c,0x9f,1,flag))return false;r.carry=AnimationCarryClear;r.pc=flag?0xb0426:0xb0424;return true;
    // TST.W 8a(A6); BPL.W b0434; ANDI.B #fe,CCR; RTS (b042e, above).
    case 0xb0426:if(!on09_get(c,0x8a,2,value))return false;r.pc=on09_negative_word(value)?0xb042e:0xb0434;return true;
    // MOVE.W 42(A6),D0; SUBI.W #20,D0; CMPI.W #120,D0; BCS.W b0446; RTS.
    case 0xb0434:
        if(!on09_get(c,0x42,2,value))return false;am_word(r.d[0],value-0x20U);flag=(r.d[0]&65535U)<0x120U;
        r.carry=flag?AnimationCarrySet:AnimationCarryClear;r.pc=flag?0xb0446:0xb0444;return true;
    case 0xb0446:return am_call(c,0xb0228,0xb044a);                          // BSR.W b0228.
    case 0xb044a:return on09_carry(c,0xb044e,0xb0450);                        // BCS.W b0450.
    // MOVEA.L 76(A6),A0; MOVE.W 42(A0),D0; SUB.W 42(A6),D0; BPL.W b0462; NEG.W D0 (b0460, above).
    case 0xb0450:
        if(!on09_get(c,0x76,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x42),2,value) ||
            !on09_get(c,0x42,2,other))return false;am_word(r.d[0],value-other);r.pc=on09_negative_word(r.d[0])?0xb0460:0xb0462;return true;
    // CMP.W 8a(A6),D0; RTS.
    case 0xb0462:
        if(!on09_get(c,0x8a,2,value))return false;r.carry=(r.d[0]&65535U)<(value&65535U)?AnimationCarrySet:AnimationCarryClear;
        return am_return(c);
    // ---- b0468 (helper): TST.W 3a(A6); BMI.W b0472; RTS (C clear).
    case 0xb0468:if(!on09_get(c,0x3a,2,value))return false;r.carry=AnimationCarryClear;r.pc=on09_negative_word(value)?0xb0472:0xb0470;return true;
    case 0xb0472:r.a[0]=ON09_SEARCH_B;return am_call(c,0x4ae4a,0xb047e);   // LEA b067e.L,A0; JSR 4ae4a.L (boundary, N08).
    // CMPI.W #0,D0 (C clear); BEQ.W b04ca.
    case 0xb047e:r.carry=AnimationCarryClear;r.pc=(r.d[0]&65535U)==0U?0xb04ca:0xb0486;return true;
    // MOVE.L 36(A6),D0; BPL.W b0496; NEG.L D0 (b0494, above).
    case 0xb048c:if(!on09_get(c,0x36,4,value))return false;r.d[0]=value;r.pc=on09_negative_long(value)?0xb0494:0xb0496;return true;
    // LSR.L #1,D0; CMPI.L #18000,D0; BCC.W b04a8; MOVE.L #18000,D0.
    case 0xb0496:r.d[0]>>=1;r.pc=r.d[0]>=0x18000U?0xb04a8:0xb04a2;return true;
    case 0xb04a2:r.d[0]=0x18000;r.pc=0xb04a8;return true;
    // MOVE.W 42(A6),D1; CMP.W 42(A0),D1; BGE.W b04b6; NEG.L D0.
    case 0xb04a8:
        if(!on09_get(c,0x42,2,value) || !am_read(c,am_index(r.a[0],0x42),2,other))return false;am_word(r.d[1],value);
        r.pc=on09_signed_word(value)>=on09_signed_word(other)?0xb04b6:0xb04b4;return true;
    case 0xb04b4:r.d[0]=0U-r.d[0];r.pc=0xb04b6;return true;
    // MOVE.L 3a(A6),D1; ASR.L #1,D1; NEG.L D1; MOVE.L D0,36(A6); MOVE.L D1,3a(A6); ORI.B #1,CCR.
    case 0xb04b6:
        if(!on09_get(c,0x3a,4,value))return false;r.d[1]=0U-on09_asr(value,1);
        if(!on09_put(c,0x36,4,r.d[0]) || !on09_put(c,0x3a,4,r.d[1]))return false;r.carry=AnimationCarrySet;r.pc=0xb04ca;return true;
    // ---- b057e / b059e (tails): LEA b05de.L,A0; JSR 1ab02.L / 1ab80.L; BCC.W RTS, else parent 62 - 1 and JMP 2a00.
    case 0xb057e:r.a[0]=ON09_RECT;return am_call(c,0x1ab02,0xb058a);
    case 0xb059e:r.a[0]=ON09_RECT;return am_call(c,0x1ab80,0xb05aa);
    case 0xb058a:return on09_carry(c,0xb059c,0xb058e);
    case 0xb05aa:return on09_carry(c,0xb05bc,0xb05ae);
    default:return am_error(c,"unsupported animation objects n09 PC");
    }
}
}
