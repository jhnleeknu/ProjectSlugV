#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute and PC relative data operands (read through the live bus).
const std::uint32_t OU6_SCRIPT=0xe7570;      // e7410 MOVE.L #e7570,76(A6) (script of duration/handler/argument WORDs, fixed ROM)
const std::uint32_t OU6_TEXT_TABLE_3=0xe7392;// e74da LEA e7392(PC),A1 (LONG table when BYTE -8000(A5) = 3, fixed ROM)
const std::uint32_t OU6_TEXT_TABLE=0xe73c2;  // e74ec LEA e73c2(PC),A1 (LONG table otherwise, fixed ROM)
const std::uint32_t OU6_SLOT_TABLE=0xe7752;  // e77ba LEA e7752(PC),A1 (16 LONGs, fixed ROM)
const std::uint32_t OU6_BANK_LIST=0xeba9e;   // eb7b8/eb7f2/eba08 LEA eba9e(PC),A0 (8-byte entries ended by a zero LONG, fixed ROM)
const std::uint32_t OU6_BANK_TABLE=0x200004; // eba6e LEA 200004.L,A1 (bank window, live bank_base)
bool ou6_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou6_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Consumers of a known C (BCC clear_pc, else set_pc).
bool ou6_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects u06 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W #id,D0; MOVE.B #0,D1; JSR 8ebe.L.
bool ou6_palette(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #ea,20(A6); MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.L.
bool ou6_animation(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    if(!ou6_put(c,c.s.a[6],0x20,2,0xea))return false;c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #mask,76(A6) (the e77f2/e7818 pairs write twice); MOVE.L #offset,78(A6).
bool ou6_select(AnimationMachineContext& c,std::uint32_t first,std::uint32_t mask,std::uint32_t offset) {
    if(first!=mask && !ou6_put(c,c.s.a[6],0x76,2,first))return false;
    return ou6_put(c,c.s.a[6],0x76,2,mask) && ou6_put(c,c.s.a[6],0x78,4,offset);
}
// MOVEQ #0,D0; MOVE.L 78(A6),D7; ADDI.W #ea,D7; JSR 16ea4.L.
bool ou6_place(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;AnimationMachineState& r=c.s;r.d[0]=0;if(!ou6_get(c,r.a[6],0x78,4,value))return false;
    r.d[7]=value;am_word(r.d[7],r.d[7]+0xeaU);return am_call(c,0x16ea4,return_pc);
}
// TST.W 76(A6); BNE other_pc (else zero_pc).
bool ou6_side(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ou6_get(c,c.s.a[6],0x76,2,value))return false;c.s.pc=(value&65535U)?other_pc:zero_pc;return true;
}
// BTST #bit,D0; BEQ clear_pc (else set_pc). Only Z changes.
void ou6_bit(AnimationMachineState& r,unsigned int bit,std::uint32_t set_pc,std::uint32_t clear_pc) {
    r.pc=((r.d[0]>>bit)&1U)?set_pc:clear_pc;
}
// ADDQ.W/SUBQ.W #1,d16(A6) (WORD wrap).
bool ou6_step(AnimationMachineContext& c,std::uint32_t displacement,bool up) {
    std::uint32_t value=0;if(!ou6_get(c,c.s.a[6],displacement,2,value))return false;
    return ou6_put(c,c.s.a[6],displacement,2,(up?value+1U:value-1U)&65535U);
}
// MOVE.W 84(A6),D0; ADD.W 88(A6),D0; MOVE.B #0,D1; JSR 8ebe.L.
bool ou6_show(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t base=0,index=0;AnimationMachineState& r=c.s;
    if(!ou6_get(c,r.a[6],0x84,2,base) || !ou6_get(c,r.a[6],0x88,2,index))return false;
    am_word(r.d[0],base+index);am_byte(r.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.B #value,D0; MOVE.B D0,8a(A6); JSR 101c.L (boundary without an executor).
bool ou6_mode(AnimationMachineContext& c,std::uint32_t value,std::uint32_t return_pc) {
    am_byte(c.s.d[0],value);if(!ou6_put(c,c.s.a[6],0x8a,1,value))return false;return am_call(c,0x101c,return_pc);
}
// MOVE.W #value,2ffff0/2ffff2 (the bank select words). Plain WORD write through the shared PVC model (am_write -> pvc_effects ->
// bus bank_base): any bank the MAME equation produces is accepted at write time; a banked read past the 8 MiB image is the shared
// program bus error (F4 main decision: guard removed, native evidence animation-machine-pvc-banks.md).
bool ou6_pvc(AnimationMachineContext& c,std::uint32_t address,std::uint32_t value) {
    return am_write(c,address,2,value&65535U);
}
}
// Objects F4 U06 (135 block starts): C3 49be0 (input slot pointer by D0.B), the script object callback e73f8 with its installed
// callback e7426 and the script handlers e74b6/e74da/e74f2/e7546 reached through e74ac JSR (A0,D0.W), the selection object
// callbacks e7792/e77ac, e77e4/e780a/e7830/e7850, e788c/e78a8 and e78d8/e78f4, and the bank list object callback eb7b6 with its
// installed callback eb81e and the list length eba3e. e742c consumes the C returned by the input executor 4836e, e7916 the C
// returned by the interpreter 49fc6; U06 produces no known C. The callees 3ed2, e7562, eb9ba, eb9e4 and 101c have no executor;
// e74ac dispatches the live A0+D0.W through the routing (e74f8/e7562 have no executor). eba3e selects the bank (80(A6) AND 7)+2:
// every PVC bank word write goes through the shared PVC model (any bank the equation produces), then the bank window
// LONG 200004+D2.W and its LONG list are read through the live bus with the new bank_base; a read past the 8 MiB image is
// the shared program bus error. The eb7bc/eba78 list walks and the
// e748a/e74b0 script loop have no extra limit (block budget only).
bool animation_objects_u06_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- 49be0: TST.B D0; BNE 49bec / LEA 5726(A5),A0; RTS / LEA 572c(A5),A0; RTS.
    case 0x49be0:r.pc=(r.d[0]&255U)?0x49bec:0x49be6;return true;
    case 0x49be6:r.a[0]=am_index(r.a[5],0x5726);return am_return(c);
    case 0x49bec:r.a[0]=am_index(r.a[5],0x572c);return am_return(c);

    // ---- e73f8 (callback): LEA e6ed2(PC),A0; JSR 8da2.L.
    case 0xe73f8:r.a[0]=0xe6ed2;return am_call(c,0x8da2,0xe7402);
    case 0xe7402:am_byte(r.d[0],0);r.a[0]=0xe73f2;return am_call(c,0x49c20,0xe7410); // MOVE.B #0,D0; LEA e73f2(PC),A0; JSR 49c20.L.
    // CLR.W 5e24(A5); MOVE.L #e7570,76(A6); CLR.W 7a(A6); MOVE.L #e7426,(A6) (then the callback e7426).
    case 0xe7410:
        if(!ou6_put(c,r.a[5],0x5e24,2,0) || !ou6_put(c,r.a[6],0x76,4,OU6_SCRIPT) || !ou6_put(c,r.a[6],0x7a,2,0) ||
            !am_write(c,r.a[6],4,0xe7426))return false;
        r.pc=0xe7426;return true;
    case 0xe7426:return am_call(c,0x4836e,0xe742c);     // JSR 4836e.L (callback entry).
    case 0xe742c:return ou6_carry(c,0xe7430,0xe748a);   // BCS e748a.
    // MOVEQ #-1,D0; TST.B 7d82(A5); BEQ e7440.
    case 0xe7430:r.d[0]=0xffffffffU;if(!ou6_get(c,r.a[5],0x7d82,1,value))return false;r.pc=value?0xe743a:0xe7440;return true;
    case 0xe743a:return am_call(c,0x3ed2,0xe7440);      // JSR 3ed2.L (boundary without an executor).
    case 0xe7440:r.d[7]=0;ou6_bit(r,0,0xe744a,0xe744e);return true; // MOVEQ #0,D7; BTST #0,D0; BEQ e744e.
    case 0xe744a:if(!ou6_get(c,r.a[5],0xccab,1,value))return false;am_byte(r.d[7],r.d[7]|value);r.pc=0xe744e;return true; // OR.B -3355(A5),D7.
    case 0xe744e:ou6_bit(r,1,0xe7456,0xe745a);return true; // BTST #1,D0; BEQ e745a.
    case 0xe7456:if(!ou6_get(c,r.a[5],0xccb1,1,value))return false;am_byte(r.d[7],r.d[7]|value);r.pc=0xe745a;return true; // OR.B -334f(A5),D7.
    case 0xe745a:am_byte(r.d[7],r.d[7]&0x30U);r.pc=(r.d[7]&255U)?0xe7462:0xe7466;return true; // ANDI.B #30,D7; BEQ e7466.
    case 0xe7462:return am_call(c,0xe7562,0xe7466);     // BSR e7562 (boundary).
    case 0xe7466:if(!ou6_get(c,r.a[5],0x7d82,1,value))return false;r.pc=value?0xe748a:0xe746e;return true; // TST.B 7d82(A5); BNE e748a.
    case 0xe746e:if(!ou6_get(c,r.a[5],0x7db6,1,value))return false;r.pc=value==1?0xe7478:0xe747c;return true; // CMPI.B #1,7db6(A5); BNE e747c.
    case 0xe7478:return am_call(c,0xe7562,0xe747c);     // BSR e7562 (boundary).
    case 0xe747c:if(!ou6_get(c,r.a[5],0x7db7,1,value))return false;r.pc=value==1?0xe7486:0xe748a;return true; // CMPI.B #1,7db7(A5); BNE e748a.
    case 0xe7486:return am_call(c,0xe7562,0xe748a);     // BSR e7562 (boundary).
    case 0xe748a:if(!ou6_get(c,r.a[6],0x7a,2,value))return false;r.pc=value?0xe7492:0xe74a2;return true; // TST.W 7a(A6); BEQ e74a2.
    case 0xe7492:if(!ou6_get(c,r.a[6],0x7a,2,value))return false;r.pc=value==0xffffU?0xe74a0:0xe749c;return true; // CMPI.W #ffff,7a(A6); BEQ e74a0.
    case 0xe749c:if(!ou6_step(c,0x7a,false))return false;r.pc=0xe74a0;return true; // SUBQ.W #1,7a(A6).
    case 0xe74a0:case 0xe74ea:case 0xe77e2:case 0xe78d6:case 0xe7944:case 0xeb9b8:return am_return(c); // RTS.
    // MOVEA.L 76(A6),A0; MOVE.W (A0)+,7a(A6); MOVE.W (A0)+,D0; JSR (A0,D0.W) (live target through the routing).
    case 0xe74a2:
        if(!ou6_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;if(!ou6_put(c,r.a[6],0x7a,2,value))return false;
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[0],value);
        return am_call(c,am_index(r.a[0],r.d[0]),0xe74b0);
    case 0xe74b0:if(!ou6_put(c,r.a[6],0x76,4,r.a[0]))return false;r.pc=0xe748a;return true; // MOVE.L A0,76(A6); BRA e748a.
    // MOVE.W (A0)+,D0; MOVE.L A0,-(A7); BSR e74da.
    case 0xe74b6:if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[0],value);
        if(!am_push(c,4,r.a[0]))return false;return am_call(c,0xe74da,0xe74be);
    // MOVEA.L (A1,D0.W),A0; LEA e84c8.L,A1; MOVE.W #70a6,D0; MOVE.W #800,D1; JSR 3918.L.
    case 0xe74be:if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[0]=value;r.a[1]=0xe84c8;
        am_word(r.d[0],0x70a6);am_word(r.d[1],0x800);return am_call(c,0x3918,0xe74d6);
    case 0xe74d6:case 0xe755e:if(!am_pop(c,4,value))return false;r.a[0]=value;return am_return(c); // MOVEA.L (A7)+,A0; RTS.
    // MOVE.B -8000(A5),D1; LEA e7392(PC),A1; CMPI.B #3,D1; BNE e74ec.
    case 0xe74da:if(!ou6_get(c,r.a[5],0x8000,1,value))return false;am_byte(r.d[1],value);r.a[1]=OU6_TEXT_TABLE_3;
        r.pc=value==3?0xe74ea:0xe74ec;return true;
    case 0xe74ec:r.a[1]=OU6_TEXT_TABLE;return am_return(c); // LEA e73c2(PC),A1; RTS.
    // MOVE.W (A0)+,5e24(A5); RTS.
    case 0xe74f2:if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;if(!ou6_put(c,r.a[5],0x5e24,2,value))return false;return am_return(c);
    // MOVE.L A0,-(A7); MOVE.W #70a5,D0; MOVE.W #320,D1; MOVE.W #1f,D2; MOVE.W #6,D3; JSR 35a2.L.
    case 0xe7546:if(!am_push(c,4,r.a[0]))return false;am_word(r.d[0],0x70a5);am_word(r.d[1],0x320);am_word(r.d[2],0x1f);
        am_word(r.d[3],6);return am_call(c,0x35a2,0xe755e);

    // ---- e7792 (callback): JSR 16ed2.L.
    case 0xe7792:return am_call(c,0x16ed2,0xe7798);
    case 0xe7798:return ou6_palette(c,0x2b1,0xe77a6);
    case 0xe77a6:if(!am_write(c,r.a[6],4,0xe77ac))return false;r.pc=0xe77ac;return true; // MOVE.L #e77ac,(A6).
    case 0xe77ac:case 0xe78ae:case 0xe78fa:case 0xe791a:  // MOVEQ #0,D0; JSR 49be0.L (e77ac is a callback entry).
        r.d[0]=0;return am_call(c,0x49be0,r.pc==0xe77ac?0xe77b4:r.pc==0xe78ae?0xe78b6:r.pc==0xe78fa?0xe7902:0xe7922);
    // MOVE.W (A0),D0; ANDI.W #f,D0; LEA e7752(PC),A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0xe77b4:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],(value&15U)*4U);r.a[1]=OU6_SLOT_TABLE;
        if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xe77d0);
    case 0xe77d0:if(!ou6_put(c,r.a[6],0x20,2,0xea))return false;return am_call(c,0x43e34,0xe77dc); // MOVE.W #ea,20(A6); JSR 43e34.L.
    case 0xe77dc:return am_call(c,0x49fc6,0xe77e2); // JSR 49fc6.L.
    case 0xe77e4:return ou6_palette(c,0x2ae,0xe77f2);
    case 0xe77f2:if(!ou6_select(c,0x90,0x10,0))return false;r.pc=0xe786c;return true;
    case 0xe780a:return ou6_palette(c,0x2af,0xe7818);
    case 0xe7818:if(!ou6_select(c,0xa0,0x20,0x800))return false;r.pc=0xe786c;return true;
    case 0xe7830:return ou6_palette(c,0x2b0,0xe783e);
    case 0xe783e:if(!ou6_select(c,0x40,0x40,0x1000))return false;r.pc=0xe786c;return true;
    case 0xe7850:return ou6_palette(c,0x2b2,0xe785e);
    case 0xe785e:if(!ou6_select(c,0x80,0x80,0x1800))return false;r.pc=0xe786c;return true;
    case 0xe786c:return am_call(c,0x16ed2,0xe7872); // JSR 16ed2.L.
    case 0xe7872:return ou6_animation(c,0xe7a70,0xe7888);
    case 0xe7888:r.pc=0xe78a2;return true;          // BRA e78a2.
    case 0xe788c:return ou6_animation(c,0xe7a5c,0xe78a2);
    case 0xe78a2:if(!am_write(c,r.a[6],4,0xe78a8))return false;r.pc=0xe78a8;return true; // MOVE.L #e78a8,(A6).
    case 0xe78a8:return am_call(c,0x43e34,0xe78ae); // JSR 43e34.L (callback entry).
    // MOVE.W (A0),D0; AND.W 76(A6),D0; BNE e78d8.
    case 0xe78b6:if(!am_read(c,r.a[0],2,value) || !ou6_get(c,r.a[6],0x76,2,other))return false;am_word(r.d[0],value&other);
        r.pc=(value&other&65535U)?0xe78d8:0xe78c0;return true;
    case 0xe78c0:return am_call(c,0x49fc6,0xe78c6); // JSR 49fc6.L.
    case 0xe78c6:return ou6_place(c,0xe78d6);
    case 0xe78d8:return ou6_animation(c,0xe7a46,0xe78ee);
    case 0xe78ee:if(!am_write(c,r.a[6],4,0xe78f4))return false;r.pc=0xe78f4;return true; // MOVE.L #e78f4,(A6).
    case 0xe78f4:return am_call(c,0x43e34,0xe78fa); // JSR 43e34.L (callback entry).
    // AND.W 76(A6),D0; BEQ e7910.
    case 0xe7902:if(!ou6_get(c,r.a[6],0x76,2,other))return false;am_word(r.d[0],r.d[0]&other);r.pc=(r.d[0]&65535U)?0xe790a:0xe7910;return true;
    case 0xe790a:if(!am_write(c,r.a[6],4,0xe78d8))return false;r.pc=0xe7910;return true; // MOVE.L #e78d8,(A6).
    case 0xe7910:return am_call(c,0x49fc6,0xe7916); // JSR 49fc6.L.
    case 0xe7916:return ou6_carry(c,0xe7934,0xe791a); // BCC e7934.
    // MOVE.W 2(A0),D0; AND.W 76(A6),D0; BNE e7934.
    case 0xe7922:if(!ou6_get(c,r.a[0],2,2,value) || !ou6_get(c,r.a[6],0x76,2,other))return false;am_word(r.d[0],value&other);
        r.pc=(value&other&65535U)?0xe7934:0xe792e;return true;
    case 0xe792e:if(!am_write(c,r.a[6],4,0xe788c))return false;r.pc=0xe7934;return true; // MOVE.L #e788c,(A6).
    case 0xe7934:return ou6_place(c,0xe7944);

    // ---- eb7b6 (callback): MOVEQ #0,D0; LEA eba9e(PC),A0.
    case 0xeb7b6:r.d[0]=0;r.a[0]=OU6_BANK_LIST;r.pc=0xeb7bc;return true;
    // ADDQ.W #1,D0; ADDQ.L #8,A0; TST.L (A0); BNE eb7bc.
    case 0xeb7bc:am_word(r.d[0],r.d[0]+1U);r.a[0]+=8U;if(!am_read(c,r.a[0],4,value))return false;r.pc=value?0xeb7bc:0xeb7c4;return true;
    // MOVE.W D0,78(A6); MOVE.W #0,7c/7e/88(A6); MOVE.B #2,8a(A6); MOVE.W #8,D0; MOVE.W #0,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xeb7c4:
        if(!ou6_put(c,r.a[6],0x78,2,r.d[0]) || !ou6_put(c,r.a[6],0x7c,2,0) || !ou6_put(c,r.a[6],0x7e,2,0) ||
            !ou6_put(c,r.a[6],0x88,2,0) || !ou6_put(c,r.a[6],0x8a,1,2))return false;
        am_word(r.d[0],8);am_word(r.d[1],0);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xeb7f2);
    // LEA eba9e(PC),A0; MOVE.L (A0),80(A6); MOVE.W 4(A0),84(A6); MOVE.W 6(A0),86(A6); JSR eba3e(PC).
    case 0xeb7f2:r.a[0]=OU6_BANK_LIST;
        if(!am_read(c,r.a[0],4,value) || !ou6_put(c,r.a[6],0x80,4,value))return false;
        if(!ou6_get(c,r.a[0],4,2,value) || !ou6_put(c,r.a[6],0x84,2,value))return false;
        if(!ou6_get(c,r.a[0],6,2,value) || !ou6_put(c,r.a[6],0x86,2,value))return false;return am_call(c,0xeba3e,0xeb80a);
    // MOVE.W 84(A6),D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xeb80a:if(!ou6_get(c,r.a[6],0x84,2,value))return false;return ou6_palette(c,value,0xeb818);
    case 0xeb818:if(!am_write(c,r.a[6],4,0xeb81e))return false;r.pc=0xeb81e;return true; // MOVE.L #eb81e,(A6).
    // MOVE.B #90,567e(A5); MOVE.B #ff,567f(A5); TST.W 76(A6); BNE eb83a (callback entry).
    case 0xeb81e:if(!ou6_put(c,r.a[5],0x567e,1,0x90) || !ou6_put(c,r.a[5],0x567f,1,0xff))return false;return ou6_side(c,0xeb832,0xeb83a);
    case 0xeb832:if(!ou6_get(c,r.a[5],0xccba,1,value))return false;am_byte(r.d[0],value);r.pc=0xeb83e;return true; // MOVE.B -3346(A5),D0; BRA eb83e.
    case 0xeb83a:if(!ou6_get(c,r.a[5],0xccc0,1,value))return false;am_byte(r.d[0],value);r.pc=0xeb83e;return true; // MOVE.B -3340(A5),D0.
    case 0xeb83e:ou6_bit(r,4,0xeb846,0xeb852);return true;
    case 0xeb846:if(!ou6_step(c,0x7e,true))return false;return am_call(c,0xeb9ba,0xeb84e); // ADDQ.W #1,7e(A6); JSR eb9ba(PC) (boundary).
    case 0xeb84e:case 0xeb862:case 0xeb87c:case 0xeb896:r.pc=0xeb89a;return true; // BRA eb89a.
    case 0xeb852:ou6_bit(r,5,0xeb85a,0xeb866);return true;
    case 0xeb85a:if(!ou6_step(c,0x7e,false))return false;return am_call(c,0xeb9ba,0xeb862); // SUBQ.W #1,7e(A6); JSR eb9ba(PC) (boundary).
    case 0xeb866:ou6_bit(r,6,0xeb86e,0xeb880);return true;
    // MOVE.W #0,7e(A6); ADDQ.W/SUBQ.W #1,7c(A6); JSR eb9e4(PC) (boundary).
    case 0xeb86e:if(!ou6_put(c,r.a[6],0x7e,2,0) || !ou6_step(c,0x7c,true))return false;return am_call(c,0xeb9e4,0xeb87c);
    case 0xeb880:ou6_bit(r,7,0xeb888,0xeb89a);return true;
    case 0xeb888:if(!ou6_put(c,r.a[6],0x7e,2,0) || !ou6_step(c,0x7c,false))return false;return am_call(c,0xeb9e4,0xeb896);
    case 0xeb89a:return ou6_side(c,0xeb8a2,0xeb8aa);
    case 0xeb8a2:if(!ou6_get(c,r.a[5],0xccbe,1,value))return false;am_byte(r.d[0],value);r.pc=0xeb8ae;return true; // MOVE.B -3342(A5),D0; BRA eb8ae.
    case 0xeb8aa:if(!ou6_get(c,r.a[5],0xccb8,1,value))return false;am_byte(r.d[0],value);r.pc=0xeb8ae;return true; // MOVE.B -3348(A5),D0.
    case 0xeb8ae:ou6_bit(r,0,0xeb8b6,0xeb8ba);return true;
    case 0xeb8b6:if(!ou6_step(c,0x46,true))return false;r.pc=0xeb8ba;return true;
    case 0xeb8ba:ou6_bit(r,1,0xeb8c2,0xeb8c6);return true;
    case 0xeb8c2:if(!ou6_step(c,0x46,false))return false;r.pc=0xeb8c6;return true;
    case 0xeb8c6:ou6_bit(r,3,0xeb8ce,0xeb8d2);return true;
    case 0xeb8ce:if(!ou6_step(c,0x42,true))return false;r.pc=0xeb8d2;return true;
    case 0xeb8d2:ou6_bit(r,2,0xeb8da,0xeb8de);return true;
    case 0xeb8da:if(!ou6_step(c,0x42,false))return false;r.pc=0xeb8de;return true;
    case 0xeb8de:return ou6_side(c,0xeb8e6,0xeb8ee);
    case 0xeb8e6:if(!ou6_get(c,r.a[5],0xccc0,1,value))return false;am_byte(r.d[0],value);r.pc=0xeb8f2;return true; // MOVE.B -3340(A5),D0; BRA eb8f2.
    case 0xeb8ee:if(!ou6_get(c,r.a[5],0xccba,1,value))return false;am_byte(r.d[0],value);r.pc=0xeb8f2;return true; // MOVE.B -3346(A5),D0.
    case 0xeb8f2:ou6_bit(r,4,0xeb8fa,0xeb92c);return true;
    // ADDQ.W #1,88(A6); MOVE.W 86(A6),D0; CMP.W 88(A6),D0; BCC eb910 (no borrow: D0.W >= 88(A6) unsigned).
    case 0xeb8fa:if(!ou6_step(c,0x88,true) || !ou6_get(c,r.a[6],0x86,2,value) || !ou6_get(c,r.a[6],0x88,2,other))return false;
        am_word(r.d[0],value);r.pc=value>=other?0xeb910:0xeb90a;return true;
    case 0xeb90a:if(!ou6_put(c,r.a[6],0x88,2,0))return false;r.pc=0xeb910;return true; // MOVE.W #0,88(A6).
    case 0xeb910:return am_call(c,0x8ff4,0xeb916); // JSR 8ff4.L.
    case 0xeb916:return ou6_show(c,0xeb928);
    case 0xeb928:r.pc=0xeb95a;return true;          // BRA eb95a.
    case 0xeb92c:ou6_bit(r,5,0xeb934,0xeb95a);return true;
    // SUBQ.W #1,88(A6); BCC eb942 (borrow only from 0).
    case 0xeb934:if(!ou6_get(c,r.a[6],0x88,2,value) || !ou6_put(c,r.a[6],0x88,2,(value-1U)&65535U))return false;
        r.pc=value?0xeb942:0xeb93c;return true;
    case 0xeb93c:if(!ou6_get(c,r.a[6],0x86,2,value) || !ou6_put(c,r.a[6],0x88,2,value))return false;r.pc=0xeb942;return true; // MOVE.W 86(A6),88(A6).
    case 0xeb942:return am_call(c,0x8ff4,0xeb948); // JSR 8ff4.L.
    case 0xeb948:return ou6_show(c,0xeb95a);
    case 0xeb95a:return ou6_side(c,0xeb962,0xeb96a);
    case 0xeb962:if(!ou6_get(c,r.a[5],0xccbf,1,value))return false;am_byte(r.d[0],value);r.pc=0xeb96e;return true; // MOVE.B -3341(A5),D0; BRA eb96e.
    case 0xeb96a:if(!ou6_get(c,r.a[5],0xccb9,1,value))return false;am_byte(r.d[0],value);r.pc=0xeb96e;return true; // MOVE.B -3347(A5),D0.
    case 0xeb96e:ou6_bit(r,6,0xeb976,0xeb9a0);return true;
    case 0xeb976:if(!ou6_get(c,r.a[6],0x8a,1,value))return false;r.pc=value==1?0xeb980:0xeb992;return true; // CMPI.B #1,8a(A6); BNE eb992.
    case 0xeb980:return ou6_mode(c,2,0xeb98e);
    case 0xeb98e:r.pc=0xeb9a0;return true;          // BRA eb9a0.
    case 0xeb992:return ou6_mode(c,1,0xeb9a0);
    // MOVEQ #0,D0; MOVE.L 80(A6),D7; MOVE.W 7e(A6),D0; LSL.L #8,D0; LSL.L #3,D0; ADD.L D0,D7; MOVEQ #0,D0; JSR 16ea4.L.
    case 0xeb9a0:if(!ou6_get(c,r.a[6],0x80,4,value) || !ou6_get(c,r.a[6],0x7e,2,other))return false;
        r.d[7]=value+((other&65535U)<<11);r.d[0]=0;return am_call(c,0x16ea4,0xeb9b8);

    // ---- eba3e: MOVE.L 80(A6),D1; MOVE.L D1,D2; ANDI.W #7,D1; LSR.W #3,D2; LSL.W #2,D2; MOVEQ #0,D3; MOVE.W D0,-(A7);
    // MOVE.W D1,D0; MOVE.W D1,-7ff0(A5); ADDQ.W #1,D1; LSL.W #8,D1; LSL.W #4,D1; MOVE.W D1,2ffff2.L; MOVE.W #0,2ffff0.L;
    // MOVE.W D0,D1; MOVE.W (A7)+,D0; LEA 200004.L,A1; MOVEA.L (A1,D2.W),A1.
    case 0xeba3e:
        if(!ou6_get(c,r.a[6],0x80,4,value))return false;
        r.d[1]=value;r.d[2]=value;am_word(r.d[1],value&7U);am_word(r.d[2],((value&65535U)>>3)<<2);r.d[3]=0;
        if(!am_push(c,2,r.d[0]&65535U))return false;am_word(r.d[0],r.d[1]);
        if(!ou6_put(c,r.a[5],0x8010,2,r.d[1]))return false;am_word(r.d[1],((r.d[1]+1U)<<12)&65535U);
        if(!ou6_pvc(c,0x2ffff2,r.d[1]) || !ou6_pvc(c,0x2ffff0,0))return false;
        am_word(r.d[1],r.d[0]);if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        r.a[1]=OU6_BANK_TABLE;if(!am_read(c,am_index(r.a[1],r.d[2]),4,value))return false;r.a[1]=value;r.pc=0xeba78;return true;
    // ADDQ.W #1,D3; ADDQ.L #4,A1; TST.L (A1); BNE eba78.
    case 0xeba78:am_word(r.d[3],r.d[3]+1U);r.a[1]+=4U;if(!am_read(c,r.a[1],4,value))return false;r.pc=value?0xeba78:0xeba80;return true;
    // SUBQ.W #1,D3; MOVE.W D3,7a(A6); MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L; RTS.
    case 0xeba80:
        am_word(r.d[3],r.d[3]-1U);
        if(!ou6_put(c,r.a[6],0x7a,2,r.d[3]) || !ou6_put(c,r.a[5],0x8010,2,0) || !ou6_pvc(c,0x2ffff2,0x1000) || !ou6_pvc(c,0x2ffff0,0))return false;
        return am_return(c);
    default:return am_error(c,"unsupported animation objects u06 PC");
    }
}
}
