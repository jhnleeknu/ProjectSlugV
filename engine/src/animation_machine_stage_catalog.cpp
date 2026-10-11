#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (LEA d16(PC), MOVEA.L #, MOVE.L #).
const std::uint32_t SC_GROUPS=0x474f4;                             // 474ee MOVEA.L 474f4(PC,D0.W),A0 (read through the live bus)
const std::uint32_t SC_TABLE=0x478ac;                              // 478a8 JMP 478ac(PC,D0.W)
const std::uint32_t SC_CHILD1=0x4fcb8,SC_CHILD2=0x4fd0a,SC_CHILD3=0x4ff4c; // 47934/4794c/47964 MOVEA.L # (callbacks)
// d16(A5) operands use the live A5 (negative displacements are written as their 16-bit two's complement).
bool sc_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool sc_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// BCLR #n,d16(A5): memory BYTE read-modify-write, bit number mod 8 (Z not consumed).
bool sc_bclr(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t bit) {
    std::uint32_t value=0;if(!sc_read(c,displacement,1,value))return false;
    return sc_write(c,displacement,1,value&~(1U<<(bit&7U))&255U);
}
// Consumers of a C returned by 28ae: BCC clear_pc, otherwise set_pc.
bool sc_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"stage catalog caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEQ #e1,D0; MOVEQ #e1,D1; MOVEQ #e1,D2; MOVE.W #level,D3 (low WORD only).
void sc_fade(AnimationMachineState& r,std::uint32_t level) {
    r.d[0]=0xffffffe1U;r.d[1]=0xffffffe1U;r.d[2]=0xffffffe1U;am_word(r.d[3],level);
}
// MOVEA.L #child,A0; MOVE.W #0,D0; JSR 28ae.L (known C).
bool sc_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],0);return am_call(c,0x28ae,return_pc);
}
// MOVE.L #callback,(A6).
bool sc_install(AnimationMachineContext& c,std::uint32_t callback) {return am_write(c,c.s.a[6],4,callback);}
}
// Stage controller F1c1: catalog selection, music and entry effect 477e4..479b0 (the node callback 477e4 through F1a
// 1a5a4, the 477ee stage/area copy, the 474e2 group table and the 47540 record walk, the 47842 BCLR chain and the
// 10d686 music comparison with 3d58/3d6a/3d6e and 4814e, the 478a8 entry effect table with its six BRA.W slots and the
// dispatcher callbacks 478de 4790a 4798e) and ca8a. Existing executors called: F1a 1a5a4 and 72f0 (known C), F1b ca48
// 1c5b0 9056, exit ca7e 4e24e 8c16, sound 3ac8, screen ca9e caf0, transition 35a2, fade_card 28ae (known C) and U1
// 480bc for every frame wait. 478e4 with C clear leaves PC 478de and returns Waiting (F1 main decision 2): the IRQ that
// clears 107ded bit7 is a declared host change before the resume. A frame ends when 480f0 RTS returns to the dispatcher
// (stop 2ac2); the next frame is a declared direct entry at the callback LONG (A6). Child completion 62(A6) changes only
// through a declared host write between frames. The 478a8 JMP index is the computed PC 478ac+D0.W (F1 main decision 3:
// odd targets fail as unaligned, non-start targets as unsupported); 478a6 (TRAP #f, record +0 >= 18) is a boundary
// without an executor. 3d58 MOVE.B D0,-(A7) and 3d6e MOVE.B (A7)+,D0 move A7 by 2 and touch one BYTE. The callback
// 479b0 (F1c2) is a boundary without an executor. ROM data (474f4 group table, group lists and records) is read through
// the live bus; 47842 and 47896 re-read LONG 76(A6) live. All d16(A5) operands use the live A5. The 47544 walk and the
// empty-group retry 4781a have no extra limit (block budget only).
bool animation_stage_catalog_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x477e4:r.d[0]=0;r.a[0]=r.d[0];return am_call(c,0x1a5a4,0x477ee); // MOVEQ #0,D0; MOVEA.L D0,A0; JSR 1a5a4.L.
    // MOVE.B 5680(A5),7c(A6); MOVE.B 5681(A5),7d(A6).
    case 0x477ee:
        if(!sc_read(c,0x5680,1,value) || !am_write(c,am_index(r.a[6],0x7c),1,value&255U))return false;
        if(!sc_read(c,0x5681,1,value) || !am_write(c,am_index(r.a[6],0x7d),1,value&255U))return false;
        r.pc=0x477fa;return true;
    // MOVEQ #0,D0; MOVE.B 7c(A6),D0; BSR 474e2.
    case 0x477fa:
        r.d[0]=0;if(!am_read(c,am_index(r.a[6],0x7c),1,value))return false;am_byte(r.d[0],value);
        return am_call(c,0x474e2,0x47804);
    // MOVE.B (A0),5684(A5); MOVEQ #0,D1; MOVE.B 7d(A6),D1; BSR 47540.
    case 0x47804:
        if(!am_read(c,r.a[0],1,value) || !sc_write(c,0x5684,1,value&255U))return false;
        r.d[1]=0;if(!am_read(c,am_index(r.a[6],0x7d),1,value))return false;am_byte(r.d[1],value);
        return am_call(c,0x47540,0x47812);
    case 0x47812:r.pc=r.a[0]?0x47820:0x4781a;return true; // CMPA.W #0,A0 (whole LONG); BNE 47820.
    case 0x4781a:if(!am_write(c,am_index(r.a[6],0x7d),1,0))return false;r.pc=0x477fa;return true; // CLR.B 7d(A6); BRA 477fa.
    case 0x47820:if(!am_write(c,am_index(r.a[6],0x76),4,r.a[0]))return false;return am_call(c,0xca48,0x4782a); // MOVE.L A0,76(A6); JSR ca48.L.
    case 0x4782a:return am_call(c,0x1c5b0,0x47830); // JSR 1c5b0.L.
    case 0x47830:return am_call(c,0xca7e,0x47836);  // JSR ca7e.L.
    case 0x47836:return am_call(c,0x4e24e,0x4783c); // JSR 4e24e.L.
    case 0x4783c:return am_call(c,0x9056,0x47842);  // JSR 9056.L.
    // BCLR #0/#4/#2/#1/#5,5683(A5); MOVEA.L 76(A6),A0; MOVE.W 10(A0),D0; MOVE.W 5686(A5),D1; CMP.W D0,D1; BEQ 47890.
    case 0x47842:
        if(!sc_bclr(c,0x5683,0) || !sc_bclr(c,0x5683,4) || !sc_bclr(c,0x5683,2) || !sc_bclr(c,0x5683,1) ||
           !sc_bclr(c,0x5683,5))return false;
        if(!am_read(c,am_index(r.a[6],0x76),4,value))return false;r.a[0]=value;
        if(!am_read(c,am_index(r.a[0],0x10),2,value))return false;am_word(r.d[0],value);
        if(!sc_read(c,0x5686,2,value))return false;am_word(r.d[1],value);
        r.pc=(r.d[0]&65535U)==(r.d[1]&65535U)?0x47890:0x47872;return true;
    case 0x47872:r.pc=(r.d[0]&65535U)==0x19c1U?0x4787a:0x47882;return true; // CMPI.W #19c1,D0; BNE 47882.
    case 0x4787a:am_word(r.d[0],0x38);r.pc=0x47886;return true; // MOVE.W #38,D0; BRA 47886.
    case 0x47882:am_word(r.d[0],0x80);r.pc=0x47886;return true; // MOVE.W #80,D0.
    case 0x47886:return am_call(c,0x3d58,0x4788c);  // JSR 3d58.L.
    case 0x4788c:return am_call(c,0x4814e,0x47890); // JSR 4814e(PC).
    case 0x47890:return am_call(c,0xca9e,0x47896);  // JSR ca9e.L.
    // MOVEA.L 76(A6),A0; MOVEQ #0,D0; MOVE.B (A0),D0; CMPI.W #18,D0; BCS 478a8 (else 478a6 TRAP #f boundary).
    case 0x47896:
        if(!am_read(c,am_index(r.a[6],0x76),4,value))return false;r.a[0]=value;
        r.d[0]=0;if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[0],value);
        r.pc=(r.d[0]&65535U)<0x18U?0x478a8:0x478a6;return true;
    case 0x478a8:r.pc=am_index(SC_TABLE,r.d[0]);return true; // JMP 478ac(PC,D0.W) (computed PC, no range check).
    // Table slots (BRA.W).
    case 0x478ac:r.pc=0x478c4;return true;
    case 0x478b0:r.pc=0x478f0;return true;
    case 0x478b4:r.pc=0x4791c;return true;
    case 0x478b8:r.pc=0x47934;return true;
    case 0x478bc:r.pc=0x4794c;return true;
    case 0x478c0:r.pc=0x47964;return true;
    case 0x478c4:sc_fade(r,0);return am_call(c,0x8c16,0x478d4); // MOVEQ #e1,D0..D2; MOVE.W #0,D3; JSR 8c16.L.
    case 0x478d4:if(!sc_install(c,0x478de))return false;r.pc=0x480bc;return true; // MOVE.L #478de,(A6); BRA 480bc.
    // 478de (dispatcher callback): JSR 72f0.L. 478e4: BCC 478de (C clear: wait at 478de, F1 main decision 2).
    case 0x478de:return am_call(c,0x72f0,0x478e4);
    case 0x478e4:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"stage catalog caller requires known carry");
        if(r.carry==AnimationCarryClear) {r.pc=0x478de;c.waiting=true;return true;}
        r.pc=0x478e6;return true;
    case 0x478e6:return am_call(c,0xca8a,0x478ec); // JSR ca8a.L.
    case 0x478ec:case 0x47918:r.pc=0x479b0;return true; // BRA 479b0 (F1c2 boundary).
    // MOVEQ #e1,D0..D2; MOVE.W #10,D3; MOVE.W D3,7a(A6).
    case 0x478f0:
        sc_fade(r,0x10);if(!am_write(c,am_index(r.a[6],0x7a),2,r.d[3]&65535U))return false;r.pc=0x478fe;return true;
    case 0x478fe:return am_call(c,0x8c16,0x47904); // JSR 8c16.L.
    case 0x47904:if(!sc_install(c,0x4790a))return false;r.pc=0x4790a;return true; // MOVE.L #4790a,(A6).
    // 4790a (dispatcher callback): SUBQ.W #1,7a(A6); BCC 480bc (C = borrow, 0 -> ffff falls through).
    case 0x4790a:
        if(!am_read(c,am_index(r.a[6],0x7a),2,value))return false;
        if(!am_write(c,am_index(r.a[6],0x7a),2,(value-1U)&65535U))return false;
        r.pc=(value&65535U)==0U?0x47912:0x480bc;return true;
    case 0x47912:return am_call(c,0xca8a,0x47918); // JSR ca8a.L.
    case 0x4791c:return am_call(c,0xcaf0,0x47922); // JSR caf0.L.
    // MOVE.W #3c,7a(A6); MOVEQ #1f,D0..D2; MOVE.W #1e,D3; BRA 478fe.
    case 0x47922:
        if(!am_write(c,am_index(r.a[6],0x7a),2,0x3c))return false;
        r.d[0]=0x1f;r.d[1]=0x1f;r.d[2]=0x1f;am_word(r.d[3],0x1e);r.pc=0x478fe;return true;
    case 0x47934:return sc_child(c,SC_CHILD1,0x47944);
    case 0x47944:return sc_carry(c,0x478c4,0x47948); // BCC 478c4.
    case 0x47948:case 0x47960:r.pc=0x47984;return true; // BRA 47984.
    case 0x4794c:return sc_child(c,SC_CHILD2,0x4795c);
    case 0x4795c:return sc_carry(c,0x478c4,0x47960); // BCC 478c4.
    case 0x47964:return sc_child(c,SC_CHILD3,0x47974);
    case 0x47974:return sc_carry(c,0x478c4,0x47978); // BCC 478c4.
    // MOVE.W 5690(A5),76(A0); MOVE.W 5692(A5),78(A0) (A0 = the new object).
    case 0x47978:
        if(!sc_read(c,0x5690,2,value) || !am_write(c,am_index(r.a[0],0x76),2,value&65535U))return false;
        if(!sc_read(c,0x5692,2,value) || !am_write(c,am_index(r.a[0],0x78),2,value&65535U))return false;
        r.pc=0x47984;return true;
    // CLR.B 62(A6); MOVE.L #4798e,(A6).
    case 0x47984:
        if(!am_write(c,am_index(r.a[6],0x62),1,0) || !sc_install(c,0x4798e))return false;r.pc=0x4798e;return true;
    // 4798e (dispatcher callback): TST.B 62(A6); BEQ 480bc.
    case 0x4798e:if(!am_read(c,am_index(r.a[6],0x62),1,value))return false;r.pc=(value&255U)?0x47996:0x480bc;return true;
    case 0x47996:sc_fade(r,0);return am_call(c,0x8c16,0x479a6); // MOVEQ #e1,D0..D2; MOVE.W #0,D3; JSR 8c16.L.
    case 0x479a6:if(!sc_install(c,0x479b0))return false;r.pc=0x480bc;return true; // MOVE.L #479b0,(A6); BRA 480bc.

    // 474e2: CMPI.W #13,D0; BCS 474ec. 474ea: MOVEQ #0,D0.
    case 0x474e2:r.pc=(r.d[0]&65535U)<0x13U?0x474ec:0x474ea;return true;
    case 0x474ea:r.d[0]=0;r.pc=0x474ec;return true;
    // LSL.W #2,D0; MOVEA.L 474f4(PC,D0.W),A0; RTS.
    case 0x474ec:
        am_word(r.d[0],(r.d[0]&65535U)<<2);
        if(!am_read(c,am_index(SC_GROUPS,r.d[0]),4,value))return false;r.a[0]=value;return am_return(c);
    case 0x47540:r.a[0]=am_index(r.a[0],2);r.pc=0x47544;return true; // LEA 2(A0),A0.
    // MOVE.W (A0)+,D0; BNE 47550.
    case 0x47544:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[0],value);
        r.pc=(value&65535U)?0x47550:0x4754a;return true;
    case 0x4754a:r.a[0]=0;return am_return(c); // MOVEA.W #0,A0; RTS.
    // SUBQ.W #1,D1; BCC 47558 (C = borrow: D1.W was 0).
    case 0x47550:value=r.d[1]&65535U;am_word(r.d[1],value-1U);r.pc=value==0U?0x47556:0x47558;return true;
    case 0x47556:return am_return(c); // RTS.
    case 0x47558:r.a[0]=am_index(r.a[0],r.d[0]);r.pc=0x47544;return true; // LEA (A0,D0.W),A0; BRA 47544.

    // 3d58: MOVE.B D0,-(A7) (A7-2, one BYTE); MOVE.B #a,D0; BRA 3d6a.
    case 0x3d58:if(!am_push(c,1,r.d[0]&255U))return false;am_byte(r.d[0],0xa);r.pc=0x3d6a;return true;
    case 0x3d6a:return am_call(c,0x3ac8,0x3d6e); // BSR 3ac8.
    // MOVE.B (A7)+,D0 (one BYTE, A7+2); ADDI.B #20,D0; SCS.B D1 (C = BYTE carry); OR.W D1,D0; BRA 3ac8 (tail).
    case 0x3d6e:{
        if(!am_pop(c,1,value))return false;am_byte(r.d[0],value);
        const std::uint32_t sum=(r.d[0]&255U)+0x20U;am_byte(r.d[0],sum);am_byte(r.d[1],sum>255U?0xffU:0U);
        am_word(r.d[0],(r.d[0]|r.d[1])&65535U);r.pc=0x3ac8;return true;}
    // ca8a: MOVE.W #7000,D0; MOVE.W #28,D2; MOVEQ #20,D3; MOVE.W #7000,D1; JMP 35a2.L (tail call).
    case 0xca8a:am_word(r.d[0],0x7000);am_word(r.d[2],0x28);r.d[3]=0x20;am_word(r.d[1],0x7000);r.pc=0x35a2;return true;
    case 0x4814e:if(!sc_write(c,0x568c,2,1))return false;return am_return(c); // MOVE.W #1,568c(A5); RTS.
    default:return am_error(c,"unsupported animation stage catalog PC");
    }
}
}
