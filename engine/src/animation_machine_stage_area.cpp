#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (LEA d16(PC), LEA abs.L, MOVEA.L #, CMPA.L #).
const std::uint32_t SA_PLAYER_TABLE=0x476d0;                        // 476f2 LEA 476d0(PC),A0 (LONG pointers, live bus)
const std::uint32_t SA_RECORDS=0x4cf64;                             // 4d830 LEA 4cf64(PC),A0 (16-byte records, live bus)
const std::uint32_t SA_LOOKUP=0x4e4d2;                              // 4e67c LEA 4e4d2(PC),A1 (BYTE lookup, live bus)
const std::uint32_t SA_PLAYER1=0x100cb8,SA_PLAYER2=0x100da8;        // player nodes
const std::uint32_t SA_CHECK1=0x1009a8,SA_CHECK2=0x100a6c;          // nodes only tested through 289e
const std::uint32_t SA_PLAYER_CALLBACK=0x1d1f4;                     // 47772 LEA 1d1f4.L,A1; 1bd9c MOVE.L #1d1f4,(A0)
const std::uint32_t SA_CHILD=0xd764a;                               // d7638 MOVEA.L #d764a,A0 (28ae callback)
// d16(A5) operands use the live A5 (49a58 overwrites A5 with 108000).
bool sa_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool sa_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// MOVE/CLR to d16(An) (CLR is modeled as a write of 0 like the other units).
bool sa_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BSET/BCLR on a memory BYTE: read-modify-write, bit number mod 8 (Z not consumed).
bool sa_bit(AnimationMachineContext& c,std::uint32_t address,std::uint32_t bit,bool set) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    return am_write(c,address,1,(set?(value|mask):(value&~mask))&255U);
}
// Consumers of a C returned by 289e: BCS set_pc, otherwise clear_pc.
bool sa_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"stage area caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarrySet?set_pc:clear_pc;return true;
}
// 48198/481f6: MOVEA.L (A7)+,A0; MOVE.B D0,(A0); MOVE.B D1,3(A0); MOVE.B D2,2(A0); MOVE.W D3,4(A0); MOVE.W D5,6(A0);
// MOVE.B D6,1(A0); RTS.
bool sa_store_record(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_pop(c,4,value))return false;r.a[0]=value;
    if(!am_write(c,r.a[0],1,r.d[0]&255U) || !sa_put(c,r.a[0],3,1,r.d[1]&255U) || !sa_put(c,r.a[0],2,1,r.d[2]&255U) ||
       !sa_put(c,r.a[0],4,2,r.d[3]&65535U) || !sa_put(c,r.a[0],6,2,r.d[5]&65535U) || !sa_put(c,r.a[0],1,1,r.d[6]&255U))return false;
    return am_return(c);
}
// 48180/481de: LEA 5694(A5),A0; ANDI.W #1,D0; BEQ (else LEA 569c(A5),A0).
void sa_record_select(AnimationMachineState& r,std::uint32_t one_pc,std::uint32_t zero_pc) {
    r.a[0]=am_index(r.a[5],0x5694);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&65535U)?one_pc:zero_pc;
}
}
// Stage controller F1c2: area and player initialisation and music update from the dispatcher callback 479b0 to the F1a
// body 47a94 (479b0..47a94 without the dead 47a54..47a64), the player placement 476dc/47742, the first-area
// initialisation 47594 with its 475ca tail, and their helpers 3d3a, 1bcfe/1bd12/1bd2e/1bd90/1be84, 2ef90/2efdc, 46f2e,
// 48180/481de with 4d81c, 49a58, 49a8e, 4aa30, 4d126/4d13c, 4ddb6, 4e666, b4806/b4a24, b7a20 and d760a. Existing
// executors called: palette_bind e7c36, cleanup 477c2 2a28 2a48 3dce 43dda, readiness 289e (known C), sound 3af8, exit
// 3c84 3d44, U5 e89fa, U1 6f1c2 b483e, U6 4d7a6 49c32, U7 4ab88, fade_card 28ae; the run ends at the F1a body 47a94 (or
// at the dispatcher return 2ac2 of a later F1a frame). 4d824 (TRAP #f, D1.W >= 14) is a boundary without an executor.
// 49a58 LEA 108000.L,A5 overwrites the live A5 as the original does; its ring pointer LONG (A4) must address work RAM
// (24-bit 100000..1fffff), otherwise the run fails as a checked error before any ring access (the original would read
// and write outside work RAM; F1c contract decision 9). ROM data (476d0 pointers and the WORD pairs they address,
// 4cf64 records, 4e4d2 lookup) is read through the live bus. 3d58/3d6e (F1c1) own the only BYTE stack accesses; the
// LONG/WORD pushes here use the normal stack rules. The 46f32, 4aa50 and 4aa6e loops are bounded by the original.
bool animation_stage_area_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // 479b0 (dispatcher callback): JSR e7c36.L. 479b6: BSR 477c2.
    case 0x479b0:return am_call(c,0xe7c36,0x479b6);
    case 0x479b6:return am_call(c,0x477c2,0x479ba);
    // MOVE.B #ff,5681(A5); MOVE.B #3,D0; AND.B 5684(A5),D0; BEQ 479d0.
    case 0x479ba:
        if(!sa_write(c,0x5681,1,0xff) || !sa_read(c,0x5684,1,value))return false;
        am_byte(r.d[0],3U&value);r.pc=(r.d[0]&255U)?0x479cc:0x479d0;return true;
    case 0x479cc:return am_call(c,0x476dc,0x479d0); // BSR 476dc.
    case 0x479d0:if(!am_read(c,am_index(r.a[6],0x7d),1,value))return false;r.pc=(value&255U)?0x479ee:0x479d8;return true; // TST.B 7d(A6); BNE 479ee.
    case 0x479d8:return am_call(c,0x47594,0x479dc); // BSR 47594.
    case 0x479dc:if(!sa_read(c,0x5684,1,value))return false;r.pc=(value&255U)?0x479ea:0x479e4;return true; // TST.B 5684(A5); BNE 479ea.
    case 0x479e4:return am_call(c,0x4e666,0x479ea); // JSR 4e666.L.
    case 0x479ea:r.pc=0x479fe;return true;           // BRA 479fe.
    case 0x479ee:r.d[0]=0;return am_call(c,0x48180,0x479f4); // MOVEQ #0,D0; BSR 48180.
    case 0x479f4:r.d[0]=1;return am_call(c,0x48180,0x479fa); // MOVEQ #1,D0; BSR 48180.
    case 0x479fa:return am_call(c,0x475ca,0x479fe);          // BSR 475ca.
    case 0x479fe:if(!sa_read(c,0x5684,1,value))return false;r.pc=(value&255U)?0x47a0c:0x47a06;return true; // TST.B 5684(A5); BNE 47a0c.
    case 0x47a06:return am_call(c,0xd760a,0x47a0c); // JSR d760a.L.
    case 0x47a0c:r.d[0]=0;return am_call(c,0x49c32,0x47a14); // MOVEQ #0,D0; JSR 49c32.L.
    case 0x47a14:r.d[0]=1;return am_call(c,0x49c32,0x47a1c); // MOVEQ #1,D0; JSR 49c32.L.
    // MOVEA.L 76(A6),A0; MOVE.W 10(A0),D0; MOVE.W 5686(A5),D1; MOVE.W D0,5686(A5); CMP.W D0,D1; BEQ 47a6a.
    case 0x47a1c:
        if(!am_read(c,am_index(r.a[6],0x76),4,value))return false;r.a[0]=value;
        if(!am_read(c,am_index(r.a[0],0x10),2,value))return false;am_word(r.d[0],value);
        if(!sa_read(c,0x5686,2,value))return false;am_word(r.d[1],value);
        if(!sa_write(c,0x5686,2,r.d[0]&65535U))return false;
        r.pc=(r.d[0]&65535U)==(r.d[1]&65535U)?0x47a6a:0x47a32;return true;
    case 0x47a32:r.pc=(r.d[0]&65535U)==0x10feU?0x47a6a:0x47a3a;return true; // CMPI.W #10fe,D0; BEQ 47a6a.
    case 0x47a3a:r.pc=(r.d[0]&65535U)==0x19c1U?0x47a6a:0x47a42;return true; // CMPI.W #19c1,D0; BEQ 47a6a.
    case 0x47a42:r.pc=(r.d[0]&65535U)==0x19c0U?0x47a64:0x47a4a;return true; // CMPI.W #19c0,D0; BEQ 47a64.
    case 0x47a4a:return am_call(c,0x3af8,0x47a50); // JSR 3af8.L.
    case 0x47a50:r.pc=0x47a6a;return true;          // BRA 47a6a.
    case 0x47a64:return am_call(c,0x3d44,0x47a6a); // JSR 3d44.L.
    case 0x47a6a:am_word(r.d[0],0x1890);return am_call(c,0x3af8,0x47a74); // MOVE.W #1890,D0; JSR 3af8.L.
    case 0x47a74:am_word(r.d[0],0x1891);return am_call(c,0x3af8,0x47a7e); // MOVE.W #1891,D0; JSR 3af8.L.
    case 0x47a7e:am_word(r.d[0],0x1892);return am_call(c,0x3af8,0x47a88); // MOVE.W #1892,D0; JSR 3af8.L.
    case 0x47a88:return am_call(c,0x3c84,0x47a8e); // JSR 3c84.L.
    case 0x47a8e:return am_call(c,0x3d44,0x47a94); // JSR 3d44.L (returns to the F1a body 47a94).

    // 476dc: MOVEQ #0,D0; MOVE.B 7c(A6),D0; SUBQ.W #6,D0; CMPI.W #3,D0; BCS 476ee. 476ec: MOVEQ #0,D0.
    case 0x476dc:
        r.d[0]=0;if(!am_read(c,am_index(r.a[6],0x7c),1,value))return false;am_byte(r.d[0],value);
        am_word(r.d[0],(r.d[0]&65535U)-6U);r.pc=(r.d[0]&65535U)<3U?0x476ee:0x476ec;return true;
    case 0x476ec:r.d[0]=0;r.pc=0x476ee;return true;
    // ADD.W D0,D0 (twice); LEA 476d0(PC),A0; MOVEA.L (A0,D0.W),A0; MOVEQ #0,D0; MOVE.B 7d(A6),D0; ADD.W D0,D0 (twice);
    // LEA (A0,D0.W),A1; MOVE.W (A1)+,D1; LEA 1009a8.L,A0; JSR 289e.L.
    case 0x476ee:
        am_word(r.d[0],(r.d[0]&65535U)<<2);
        if(!am_read(c,am_index(SA_PLAYER_TABLE,r.d[0]),4,value))return false;r.a[0]=value;
        r.d[0]=0;if(!am_read(c,am_index(r.a[6],0x7d),1,value))return false;am_byte(r.d[0],value);
        am_word(r.d[0],(r.d[0]&65535U)<<2);r.a[1]=am_index(r.a[0],r.d[0]);
        if(!am_read(c,r.a[1],2,value))return false;r.a[1]+=2U;am_word(r.d[1],value);
        r.a[0]=SA_CHECK1;return am_call(c,0x289e,0x47716);
    case 0x47716:return sa_carry(c,0x4771a,0x47724); // BCS 47724.
    case 0x4771a:if(!am_push(c,4,r.a[1]))return false;r.d[0]=0;return am_call(c,0x47742,0x47722); // MOVE.L A1,-(A7); MOVEQ #0,D0; BSR 47742.
    case 0x47722:if(!am_pop(c,4,value))return false;r.a[1]=value;r.pc=0x47724;return true; // MOVEA.L (A7)+,A1.
    // MOVE.W (A1)+,D1; LEA 100a6c.L,A0; JSR 289e.L.
    case 0x47724:
        if(!am_read(c,r.a[1],2,value))return false;r.a[1]+=2U;am_word(r.d[1],value);
        r.a[0]=SA_CHECK2;return am_call(c,0x289e,0x47732);
    case 0x47732:return sa_carry(c,0x47736,0x47740); // BCS 47740.
    case 0x47736:if(!am_push(c,4,r.a[1]))return false;r.d[0]=1;return am_call(c,0x47742,0x4773e); // MOVE.L A1,-(A7); MOVEQ #1,D0; BSR 47742.
    case 0x4773e:if(!am_pop(c,4,value))return false;r.a[1]=value;r.pc=0x47740;return true; // MOVEA.L (A7)+,A1.
    case 0x47740:return am_return(c); // RTS.
    // 47742: LEA 100cb8.L,A0; TST.W D0; BEQ 47754. 4774e: LEA 100da8.L,A0.
    case 0x47742:r.a[0]=SA_PLAYER1;r.pc=(r.d[0]&65535U)?0x4774e:0x47754;return true;
    case 0x4774e:r.a[0]=SA_PLAYER2;r.pc=0x47754;return true;
    case 0x47754:r.pc=(r.d[1]&0x8000U)?0x4775a:0x47764;return true; // TST.W D1; BPL 47764.
    case 0x4775a:return am_call(c,0x2a48,0x47760); // JSR 2a48.L.
    case 0x47760:r.pc=0x477a0;return true;          // BRA 477a0.
    case 0x47764:if(!am_push(c,2,r.d[1]&65535U))return false;return am_call(c,0x289e,0x4776c); // MOVE.W D1,-(A7); JSR 289e.L.
    case 0x4776c:return sa_carry(c,0x47770,0x47788); // BCS 47788.
    // MOVE.W D0,-(A7); LEA 1d1f4.L,A1; JSR 2a28.L.
    case 0x47770:if(!am_push(c,2,r.d[0]&65535U))return false;r.a[1]=SA_PLAYER_CALLBACK;return am_call(c,0x2a28,0x4777e);
    // MOVE.W (A7)+,78(A0); JSR 1bd2e.L.
    case 0x4777e:
        if(!am_pop(c,2,value) || !sa_put(c,r.a[0],0x78,2,value&65535U))return false;return am_call(c,0x1bd2e,0x47788);
    // MOVE.W (A7)+,D0; CMPI.W #4,D0; BCS 4779c.
    case 0x47788:if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.pc=(r.d[0]&65535U)<4U?0x4779c:0x47792;return true;
    case 0x47792:return am_call(c,0x49a58,0x47798); // JSR 49a58.L.
    case 0x47798:am_word(r.d[0],r.d[0]&3U);r.pc=0x4779c;return true; // ANDI.W #3,D0.
    case 0x4779c:if(!sa_put(c,r.a[0],0x76,2,r.d[0]&65535U))return false;r.pc=0x477a0;return true; // MOVE.W D0,76(A0).
    case 0x477a0:return am_return(c); // RTS.

    // 47594: MOVE.W #720,D0; JSR 3af8.L. Then JSR 3d3a, CLR.W 5686(A5); JSR b7a20, JSR 4d126, JSR 1bcfe.
    case 0x47594:am_word(r.d[0],0x720);return am_call(c,0x3af8,0x4759e);
    case 0x4759e:return am_call(c,0x3d3a,0x475a4);
    case 0x475a4:if(!sa_write(c,0x5686,2,0))return false;return am_call(c,0xb7a20,0x475ae);
    case 0x475ae:return am_call(c,0x4d126,0x475b4);
    case 0x475b4:return am_call(c,0x1bcfe,0x475ba);
    case 0x475ba:r.d[0]=0;r.d[1]=0;return am_call(c,0x481de,0x475c2); // MOVEQ #0,D0; MOVEQ #0,D1; JSR 481de(PC).
    case 0x475c2:r.d[0]=1;r.d[1]=0;return am_call(c,0x481de,0x475ca); // MOVEQ #1,D0; MOVEQ #0,D1; JSR 481de(PC).
    // 475ca (also the entry for a later area): CLR.B 5682(A5); JSR 1bd12.L. Then MOVEA.L #0,A0; JSR e89fa.L and the
    // JSR chain 3d42 3dce 49a8e 4aa30 b4a24 2ef90 6f1c2 46f2e 4d13c 4ddb6.
    case 0x475ca:if(!sa_write(c,0x5682,1,0))return false;return am_call(c,0x1bd12,0x475d4);
    case 0x475d4:r.a[0]=0;return am_call(c,0xe89fa,0x475e0);
    case 0x475e0:return am_call(c,0x3d42,0x475e6);
    case 0x475e6:return am_call(c,0x3dce,0x475ec);
    case 0x475ec:return am_call(c,0x49a8e,0x475f2);
    case 0x475f2:return am_call(c,0x4aa30,0x475f8);
    case 0x475f8:return am_call(c,0xb4a24,0x475fe);
    case 0x475fe:return am_call(c,0x2ef90,0x47604);
    case 0x47604:return am_call(c,0x6f1c2,0x4760a);
    case 0x4760a:return am_call(c,0x46f2e,0x47610);
    case 0x47610:return am_call(c,0x4d13c,0x47616);
    case 0x47616:return am_call(c,0x4ddb6,0x4761c);
    // CLR.B 5c8c(A5); CLR.B 5c8d(A5); MOVE.W #a0,5690(A5); MOVE.W #180,5692(A5); CLR.B 568e(A5); CLR.W 5688(A5);
    // CLR.W 568a(A5); CLR.W 568c(A5); RTS.
    case 0x4761c:
        if(!sa_write(c,0x5c8c,1,0) || !sa_write(c,0x5c8d,1,0) || !sa_write(c,0x5690,2,0xa0) || !sa_write(c,0x5692,2,0x180) ||
           !sa_write(c,0x568e,1,0) || !sa_write(c,0x5688,2,0) || !sa_write(c,0x568a,2,0) || !sa_write(c,0x568c,2,0))return false;
        return am_return(c);

    // 3d3a: BSR 3c84; BSR 3d44; RTS.
    case 0x3d3a:return am_call(c,0x3c84,0x3d3e);
    case 0x3d3e:return am_call(c,0x3d44,0x3d42);
    case 0x3d42:return am_return(c);

    // 1bcfe: LEA 100cb8.L,A0; BSR 1bd2e; LEA 100da8.L,A0; BSR 1bd2e.
    case 0x1bcfe:r.a[0]=SA_PLAYER1;return am_call(c,0x1bd2e,0x1bd08);
    case 0x1bd08:r.a[0]=SA_PLAYER2;return am_call(c,0x1bd2e,0x1bd12);
    // 1bd12: CLR.W 5478(A5); CLR.L 5474(A5); LEA 100cb8.L,A0; BSR 1bd90. 1bd24: LEA 100da8.L,A0; BRA 1bd90.
    case 0x1bd12:
        if(!sa_write(c,0x5478,2,0) || !sa_write(c,0x5474,4,0))return false;r.a[0]=SA_PLAYER1;return am_call(c,0x1bd90,0x1bd24);
    case 0x1bd24:r.a[0]=SA_PLAYER2;r.pc=0x1bd90;return true;
    case 0x1bd2e:return am_call(c,0x289e,0x1bd34);  // JSR 289e.L.
    case 0x1bd34:return sa_carry(c,0x1bd38,0x1bd3a); // BCS 1bd3a.
    case 0x1bd38:return am_return(c);                // RTS.
    // MOVE.B #0,9e(A0); MOVE.B #0,a0(A0); MOVE.B #0,9f(A0); CLR.B a1(A0); LEA 5450(A5),A4; MOVE.W 78(A0),D0; BEQ 1bd60.
    case 0x1bd3a:
        if(!sa_put(c,r.a[0],0x9e,1,0) || !sa_put(c,r.a[0],0xa0,1,0) || !sa_put(c,r.a[0],0x9f,1,0) || !sa_put(c,r.a[0],0xa1,1,0))return false;
        r.a[4]=am_index(r.a[5],0x5450);if(!am_read(c,am_index(r.a[0],0x78),2,value))return false;am_word(r.d[0],value);
        r.pc=(value&65535U)?0x1bd5c:0x1bd60;return true;
    case 0x1bd5c:r.a[4]=am_index(r.a[5],0x5460);r.pc=0x1bd60;return true; // LEA 5460(A5),A4.
    // MOVE.L A4,8c(A0); MOVE.B #1,6(A4); MOVE.B #a,7(A4); MOVE.B #0,4(A4); MOVE.B #0,5(A4); MOVE.W #ffff,c(A4);
    // MOVE.B #ff,3(A4); JSR 1be84(PC).
    case 0x1bd60:
        if(!sa_put(c,r.a[0],0x8c,4,r.a[4]) || !sa_put(c,r.a[4],6,1,1) || !sa_put(c,r.a[4],7,1,0xa) || !sa_put(c,r.a[4],4,1,0) ||
           !sa_put(c,r.a[4],5,1,0) || !sa_put(c,r.a[4],0xc,2,0xffff) || !sa_put(c,r.a[4],3,1,0xff))return false;
        return am_call(c,0x1be84,0x1bd8c);
    case 0x1bd8c:if(!sa_put(c,r.a[4],8,2,0))return false;r.pc=0x1bd90;return true; // CLR.W 8(A4).
    case 0x1bd90:return am_call(c,0x289e,0x1bd96);  // JSR 289e.L.
    case 0x1bd96:return sa_carry(c,0x1bd9a,0x1bd9c); // BCS 1bd9c.
    case 0x1bd9a:return am_return(c);                // RTS.
    // MOVE.L #1d1f4,(A0); CLR.B 15(A0); CLR.B 61(A0); BSET #7,61(A0); BSET #4,a8(A0); MOVE.B #0,81(A0);
    // MOVE.B #0,82(A0); MOVE.W 78(A0),D0; JSR 2efdc.L.
    case 0x1bd9c:
        if(!am_write(c,r.a[0],4,SA_PLAYER_CALLBACK) || !sa_put(c,r.a[0],0x15,1,0) || !sa_put(c,r.a[0],0x61,1,0) ||
           !sa_bit(c,am_index(r.a[0],0x61),7,true) || !sa_bit(c,am_index(r.a[0],0xa8),4,true) ||
           !sa_put(c,r.a[0],0x81,1,0) || !sa_put(c,r.a[0],0x82,1,0))return false;
        if(!am_read(c,am_index(r.a[0],0x78),2,value))return false;am_word(r.d[0],value);return am_call(c,0x2efdc,0x1bdcc);
    // MOVEA.L 8c(A0),A4; CLR.B 2(A4); CLR.B 1(A4); CLR.W a(A4); RTS.
    case 0x1bdcc:
        if(!am_read(c,am_index(r.a[0],0x8c),4,value))return false;r.a[4]=value;
        if(!sa_put(c,r.a[4],2,1,0) || !sa_put(c,r.a[4],1,1,0) || !sa_put(c,r.a[4],0xa,2,0))return false;return am_return(c);
    // 1be84: LEA 5450(A5),A4; ANDI.W #1,D0; BEQ 1be94. 1be90: LEA 5460(A5),A4. 1be94: CLR.B (A4); RTS.
    case 0x1be84:r.a[4]=am_index(r.a[5],0x5450);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&65535U)?0x1be90:0x1be94;return true;
    case 0x1be90:r.a[4]=am_index(r.a[5],0x5460);r.pc=0x1be94;return true;
    case 0x1be94:if(!am_write(c,r.a[4],1,0))return false;return am_return(c);

    // 2ef90: MOVEQ #0,D0; JSR 2efdc(PC); MOVEQ #1,D0; JSR 2efdc(PC); CLR.B 5490(A5); CLR.B 5491(A5); RTS.
    case 0x2ef90:r.d[0]=0;return am_call(c,0x2efdc,0x2ef96);
    case 0x2ef96:r.d[0]=1;return am_call(c,0x2efdc,0x2ef9c);
    case 0x2ef9c:if(!sa_write(c,0x5490,1,0) || !sa_write(c,0x5491,1,0))return false;return am_return(c);
    // 2efdc: LEA 10d480.L,A1; TST.W D0; BEQ 2efee. 2efe8: LEA 10d488.L,A1. 2efee: CLR.B 7(A1); RTS.
    case 0x2efdc:r.a[1]=0x10d480;r.pc=(r.d[0]&65535U)?0x2efe8:0x2efee;return true;
    case 0x2efe8:r.a[1]=0x10d488;r.pc=0x2efee;return true;
    case 0x2efee:if(!sa_put(c,r.a[1],7,1,0))return false;return am_return(c);

    // 46f2e: LEA 54e6(A5),A0. 46f32: MOVE.W #ffff,26(A0); MOVE.W #0,2a(A0); JSR 43dda.L.
    case 0x46f2e:r.a[0]=am_index(r.a[5],0x54e6);r.pc=0x46f32;return true;
    case 0x46f32:if(!sa_put(c,r.a[0],0x26,2,0xffff) || !sa_put(c,r.a[0],0x2a,2,0))return false;return am_call(c,0x43dda,0x46f44);
    // LEA 2c(A0),A0; CMPA.L #10d646,A0; BCS 46f32 (unsigned LONG compare).
    case 0x46f44:r.a[0]=am_index(r.a[0],0x2c);r.pc=r.a[0]<0x10d646U?0x46f32:0x46f50;return true;
    case 0x46f50:return am_return(c); // RTS.

    // 48180/481de: LEA 5694(A5),A0; ANDI.W #1,D0; BEQ; LEA 569c(A5),A0; MOVE.L A0,-(A7); JSR 4d7a6.L / 4d81c.L.
    case 0x48180:sa_record_select(r,0x4818c,0x48190);return true;
    case 0x4818c:r.a[0]=am_index(r.a[5],0x569c);r.pc=0x48190;return true;
    case 0x48190:if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x4d7a6,0x48198);
    case 0x48198:return sa_store_record(c);
    case 0x481de:sa_record_select(r,0x481ea,0x481ee);return true;
    case 0x481ea:r.a[0]=am_index(r.a[5],0x569c);r.pc=0x481ee;return true;
    case 0x481ee:if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x4d81c,0x481f6);
    case 0x481f6:return sa_store_record(c);
    // 4d81c: CMPI.W #14,D1; BCS 4d826 (else 4d824 TRAP #f boundary).
    case 0x4d81c:r.pc=(r.d[1]&65535U)<0x14U?0x4d826:0x4d824;return true;
    // MOVE.W D1,D0; ANDI.W #ff,D1; MULU.W #10,D1 (LONG result); LEA 4cf64(PC),A0; ADDA.W D1,A0; MOVE.W c(A0),D1;
    // MOVE.B 1(A0),D2; MOVE.W a(A0),D3; MOVE.W D3,D4; MOVE.W e(A0),D5; MOVE.B 2(A0),D6; RTS.
    case 0x4d826:
        am_word(r.d[0],r.d[1]);am_word(r.d[1],r.d[1]&255U);r.d[1]=(r.d[1]&65535U)*0x10U;r.a[0]=am_index(SA_RECORDS,r.d[1]);
        if(!am_read(c,am_index(r.a[0],0xc),2,value))return false;am_word(r.d[1],value);
        if(!am_read(c,am_index(r.a[0],1),1,value))return false;am_byte(r.d[2],value);
        if(!am_read(c,am_index(r.a[0],0xa),2,value))return false;am_word(r.d[3],value);am_word(r.d[4],value);
        if(!am_read(c,am_index(r.a[0],0xe),2,value))return false;am_word(r.d[5],value);
        if(!am_read(c,am_index(r.a[0],2),1,value))return false;am_byte(r.d[6],value);
        return am_return(c);

    // 49a58: LEA 108000.L,A5; LEA 5722(A5),A4; MOVEA.L (A4),A3; MOVE.W (A3)+,D0; CMPA.L A4,A3; BCS 49a70.
    case 0x49a58:
        r.a[5]=0x108000;r.a[4]=am_index(r.a[5],0x5722);if(!am_read(c,r.a[4],4,value))return false;r.a[3]=value;
        if((r.a[3]&0xffffffU)<0x100000U || (r.a[3]&0xffffffU)>=0x200000U)return am_error(c,"stage area RNG pointer outside work RAM");
        if(!am_read(c,r.a[3],2,value))return false;r.a[3]+=2U;am_word(r.d[0],value);
        r.pc=r.a[3]<r.a[4]?0x49a70:0x49a6c;return true;
    case 0x49a6c:r.a[3]-=0x6eU;r.pc=0x49a70;return true; // SUBA.W #6e,A3.
    // MOVE.L A3,(A4); ADDA.W #2e,A3; CMPA.L A4,A3; BCS 49a80.
    case 0x49a70:if(!am_write(c,r.a[4],4,r.a[3]))return false;r.a[3]+=0x2eU;r.pc=r.a[3]<r.a[4]?0x49a80:0x49a7c;return true;
    case 0x49a7c:r.a[3]-=0x6eU;r.pc=0x49a80;return true; // SUBA.W #6e,A3.
    // SUB.W D0,(A3); RTS.
    case 0x49a80:
        if(!am_read(c,r.a[3],2,value) || !am_write(c,r.a[3],2,(value-r.d[0])&65535U))return false;return am_return(c);
    // CLR.W 5726/5728/572a(A5); CLR.L 5734(A5); CLR.W 572c/572e/5730(A5); CLR.L 5738(A5); RTS.
    case 0x49a8e:
        if(!sa_write(c,0x5726,2,0) || !sa_write(c,0x5728,2,0) || !sa_write(c,0x572a,2,0) || !sa_write(c,0x5734,4,0) ||
           !sa_write(c,0x572c,2,0) || !sa_write(c,0x572e,2,0) || !sa_write(c,0x5730,2,0) || !sa_write(c,0x5738,4,0))return false;
        return am_return(c);

    // 4aa30: MOVE.B #0,5b84..5b87(A5); MOVEQ #0,D7; LEA 10daf8.L,A4.
    case 0x4aa30:
        if(!sa_write(c,0x5b84,1,0) || !sa_write(c,0x5b85,1,0) || !sa_write(c,0x5b86,1,0) || !sa_write(c,0x5b87,1,0))return false;
        r.d[7]=0;r.a[4]=0x10daf8;r.pc=0x4aa50;return true;
    // MOVE.L D7,(A4); MOVE.L D7,4(A4); LEA 8(A4),A4; CMPA.L #10db78,A4; BCS 4aa50.
    case 0x4aa50:
        if(!am_write(c,r.a[4],4,r.d[7]) || !sa_put(c,r.a[4],4,4,r.d[7]))return false;
        r.a[4]=am_index(r.a[4],8);r.pc=r.a[4]<0x10db78U?0x4aa50:0x4aa62;return true;
    // MOVE.W #ff,D7; LEA 5b88(A5),A0; MOVE.L A0,5c88(A5).
    case 0x4aa62:am_word(r.d[7],0xff);r.a[0]=am_index(r.a[5],0x5b88);if(!sa_write(c,0x5c88,4,r.a[0]))return false;r.pc=0x4aa6e;return true;
    // MOVE.B #0,(A0)+; DBRA D7,4aa6e.
    case 0x4aa6e:
        if(!am_write(c,r.a[0],1,0))return false;r.a[0]+=1U;
        am_word(r.d[7],(r.d[7]&65535U)-1U);r.pc=(r.d[7]&65535U)!=0xffffU?0x4aa6e:0x4aa76;return true;
    case 0x4aa76:r.a[4]=am_index(r.a[5],0x5746);return am_call(c,0x4ab88,0x4aa7e); // LEA 5746(A5),A4; BSR 4ab88.
    case 0x4aa7e:r.a[4]=am_index(r.a[5],0x5918);r.pc=0x4ab88;return true;          // LEA 5918(A5),A4; BRA 4ab88.

    // 4d126/4d13c: LEA 10dcba.L,A4; BSR 4d152/4d17c; LEA 10dce6.L,A4; BSR 4d152/4d17c; RTS.
    case 0x4d126:r.a[4]=0x10dcba;return am_call(c,0x4d152,0x4d130);
    case 0x4d130:r.a[4]=0x10dce6;return am_call(c,0x4d152,0x4d13a);
    case 0x4d13a:return am_return(c);
    case 0x4d13c:r.a[4]=0x10dcba;return am_call(c,0x4d17c,0x4d146);
    case 0x4d146:r.a[4]=0x10dce6;return am_call(c,0x4d17c,0x4d150);
    case 0x4d150:return am_return(c);
    // MOVE.B #0,25(A4); MOVE.B #4,26(A4); MOVE.B #0,27(A4); MOVE.W #0,1c(A4); MOVE.W #0,1a(A4); MOVE.W #ffff,20(A4);
    // MOVE.B #0,2a(A4) (then 4d17c).
    case 0x4d152:
        if(!sa_put(c,r.a[4],0x25,1,0) || !sa_put(c,r.a[4],0x26,1,4) || !sa_put(c,r.a[4],0x27,1,0) || !sa_put(c,r.a[4],0x1c,2,0) ||
           !sa_put(c,r.a[4],0x1a,2,0) || !sa_put(c,r.a[4],0x20,2,0xffff) || !sa_put(c,r.a[4],0x2a,1,0))return false;
        r.pc=0x4d17c;return true;
    // MOVE.W #0,(A4); MOVE.B #0,22(A4); MOVE.W #0,6(A4); MOVE.L #0,8(A4); RTS.
    case 0x4d17c:
        if(!am_write(c,r.a[4],2,0) || !sa_put(c,r.a[4],0x22,1,0) || !sa_put(c,r.a[4],6,2,0) || !sa_put(c,r.a[4],8,4,0))return false;
        return am_return(c);

    // 4ddb6: LEA 5d12(A5),A0; BSR 4ddc2. 4ddbe: LEA 5d18(A5),A0 (then 4ddc2).
    case 0x4ddb6:r.a[0]=am_index(r.a[5],0x5d12);return am_call(c,0x4ddc2,0x4ddbe);
    case 0x4ddbe:r.a[0]=am_index(r.a[5],0x5d18);r.pc=0x4ddc2;return true;
    // MOVE.B #1,(A0); MOVE.W #ffff,4(A0); MOVE.B #0,1(A0); MOVE.B #0,2(A0); CLR.B 3(A0); RTS.
    case 0x4ddc2:
        if(!am_write(c,r.a[0],1,1) || !sa_put(c,r.a[0],4,2,0xffff) || !sa_put(c,r.a[0],1,1,0) || !sa_put(c,r.a[0],2,1,0) ||
           !sa_put(c,r.a[0],3,1,0))return false;
        return am_return(c);

    // 4e666: LEA 5d2a(A5),A0; BSR 4e672. 4e66e: LEA 5d2b(A5),A0 (then 4e672).
    case 0x4e666:r.a[0]=am_index(r.a[5],0x5d2a);return am_call(c,0x4e672,0x4e66e);
    case 0x4e66e:r.a[0]=am_index(r.a[5],0x5d2b);r.pc=0x4e672;return true;
    // MOVE.B #0,D0; MOVE.B (A0),D0; BMI 4e68c (only the low BYTE of D0 is written).
    case 0x4e672:am_byte(r.d[0],0);if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[0],value);r.pc=(value&0x80U)?0x4e68c:0x4e67c;return true;
    // LEA 4e4d2(PC),A1; MOVE.B (A1,D0.W),D0 (sign-extended WORD index, upper BYTE from the caller); BCLR D0,5d1e(A5)
    // (bit mod 8); MOVE.B #ff,(A0) (then the 4e68c RTS).
    case 0x4e67c:
        r.a[1]=SA_LOOKUP;if(!am_read(c,am_index(r.a[1],r.d[0]),1,value))return false;am_byte(r.d[0],value);
        if(!sa_bit(c,am_index(r.a[5],0x5d1e),r.d[0],false) || !am_write(c,r.a[0],1,0xff))return false;r.pc=0x4e68c;return true;
    case 0x4e68c:return am_return(c); // RTS.

    // b4806: LEA 5d5c(A5),A1; LEA 5d98(A5),A2; JSR b483e(PC). b4812: LEA 5d98(A5),A1; LEA 5dd4(A5),A2; JMP b483e(PC).
    case 0xb4806:r.a[1]=am_index(r.a[5],0x5d5c);r.a[2]=am_index(r.a[5],0x5d98);return am_call(c,0xb483e,0xb4812);
    case 0xb4812:r.a[1]=am_index(r.a[5],0x5d98);r.a[2]=am_index(r.a[5],0x5dd4);r.pc=0xb483e;return true;
    case 0xb4a24:return am_call(c,0xb4806,0xb4a28); // JSR b4806(PC).
    case 0xb4a28:return am_return(c);                // RTS.
    case 0xb7a20:return am_call(c,0xb7a2e,0xb7a24); // JSR b7a2e(PC).
    case 0xb7a24:r.pc=0xb7a48;return true;           // BRA b7a48.
    // CLR.W 5ddc(A5); CLR.B 5dde..5de2(A5); RTS.
    case 0xb7a2e:
        if(!sa_write(c,0x5ddc,2,0) || !sa_write(c,0x5dde,1,0) || !sa_write(c,0x5ddf,1,0) || !sa_write(c,0x5de0,1,0) ||
           !sa_write(c,0x5de1,1,0) || !sa_write(c,0x5de2,1,0))return false;
        return am_return(c);
    // CLR.W 5de4(A5); CLR.B 5de6..5dea(A5); RTS.
    case 0xb7a48:
        if(!sa_write(c,0x5de4,2,0) || !sa_write(c,0x5de6,1,0) || !sa_write(c,0x5de7,1,0) || !sa_write(c,0x5de8,1,0) ||
           !sa_write(c,0x5de9,1,0) || !sa_write(c,0x5dea,1,0))return false;
        return am_return(c);
    // d760a: LEA 10ddec.L,A0; MOVE.W #1,(A0); MOVE.W #108,2(A0); MOVE.W #1a0,4(A0); ADDQ.W #6,A0 (LONG); MOVE.W #0,(A0);
    // MOVE.W #108,2(A0); MOVE.W #1a0,4(A0); MOVE.W #96,5df8(A5); MOVEA.L #d764a,A0; MOVE.W #0,D0; JSR 28ae.L.
    case 0xd760a:
        r.a[0]=0x10ddec;
        if(!am_write(c,r.a[0],2,1) || !sa_put(c,r.a[0],2,2,0x108) || !sa_put(c,r.a[0],4,2,0x1a0))return false;
        r.a[0]+=6U;
        if(!am_write(c,r.a[0],2,0) || !sa_put(c,r.a[0],2,2,0x108) || !sa_put(c,r.a[0],4,2,0x1a0) || !sa_write(c,0x5df8,2,0x96))return false;
        r.a[0]=SA_CHILD;am_word(r.d[0],0);return am_call(c,0x28ae,0xd7648);
    case 0xd7648:return am_return(c); // RTS (the 28ae C is not consumed).
    default:return am_error(c,"unsupported animation stage area PC");
    }
}
}
