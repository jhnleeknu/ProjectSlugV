#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (MOVEA.L #, MOVE.L #, LEA xxx.L, MOVE.B #,xxx.L, LEA d16(PC)).
const std::uint32_t AC_PLAYER1=0x100cb8,AC_PLAYER2=0x100da8;   // 1c5b0/1c5cc LEA xxx.L
const std::uint32_t AC_INPUT_SLOT=0x1bec0;                      // 1bee4 LEA 1bec0(PC),A0 (address only)
const std::uint32_t AC_PALETTE_SET=0x107def;                    // 9056 MOVE.B #ff,xxx.L
const std::uint32_t AC_CHILD_FADE=0xe4234,AC_CHILD_SOUND=0xd72fe; // 47dfa/47e30 MOVEA.L # (callbacks)
// d16(A5) operands use the live A5 (negative displacements are written as their 16-bit two's complement).
bool ac_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool ac_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// BSET/BCLR #n,d16(An): memory BYTE read-modify-write, bit number mod 8 (Z not consumed).
bool ac_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t bit,bool set) {
    const std::uint32_t address=am_index(base,displacement);std::uint32_t value=0;
    if(!am_read(c,address,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    return am_write(c,address,1,(set?(value|mask):(value&~mask))&255U);
}
// MOVE.W #count,7a(A6); MOVE.L #callback,(A6); fall through into the callback.
bool ac_timer(AnimationMachineContext& c,std::uint32_t count,std::uint32_t callback) {
    AnimationMachineState& r=c.s;
    if(!am_write(c,am_index(r.a[6],0x7a),2,count) || !am_write(c,r.a[6],4,callback))return false;
    r.pc=callback;return true;
}
// Dispatcher callback: SUBQ.W #1,7a(A6); BNE.W 480bc (Z of the WORD result; 0 -> ffff keeps waiting).
bool ac_count(AnimationMachineContext& c,std::uint32_t done_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;const std::uint32_t address=am_index(r.a[6],0x7a);
    if(!am_read(c,address,2,value))return false;
    const std::uint32_t next=(value-1U)&65535U;
    if(!am_write(c,address,2,next))return false;
    r.pc=next?0x480bc:done_pc;return true;
}
// Consumers of a C returned by 289e: BCC clear_pc, otherwise set_pc.
bool ac_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"area clear caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEQ #0,D0; MOVE.B 7c(A6),D0 (LONG zero, then the BYTE).
bool ac_level(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[0]=0;
    if(!am_read(c,am_index(r.a[6],0x7c),1,value))return false;am_byte(r.d[0],value);return true;
}
}
// Stage controller F1b: area clear 47da4..47eac (first-frame preparation 4b6e4 4b6ec 2a48 1c5b0 1bee4 ca48, the
// dispatcher callbacks 47de4 47e22 47e62 47e70 47e92, the 10d68e player branch with the e4234/d72fe children and the
// 19db sound, the 8c16 fade and the next-area hand-off BRA 477ee) with 9056. Existing executors called: cleanup 2a48,
// readiness 289e (known C), U6 49c20, fade_card 28ae (known C at 47e0a; 47e3a ignores C as the original: a failed 28ae
// leaves A0=100e98 and 47e48 writes WORD 100f0e), F1a 9060, sound 3af8, exit 8c16 and U1 480bc for every frame wait.
// No Waiting: a frame ends when 480f0 RTS returns to the dispatcher (stop 2ac2); the next frame is a declared direct
// entry at the callback LONG (A6) (main decision 2). Child completion 62(A6), 10dd44, 10d68e and 10d683 are changed
// only by declared host writes between frames. 477ee (F1c) is a boundary without an executor. All d16(A5) operands use
// the live A5 (28ae rewrites A5=108000). No loop, TRAP, ROM data read or PVC bank write inside F1b.
bool animation_area_clear_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x47da4:return am_call(c,0x4b6e4,0x47daa); // JSR 4b6e4.L.
    case 0x47daa:return am_call(c,0x4b6ec,0x47db0); // JSR 4b6ec.L.
    case 0x47db0:r.a[0]=am_index(r.a[5],0x8bf4);return am_call(c,0x2a48,0x47dba); // LEA -740c(A5),A0; JSR 2a48.L.
    case 0x47dba:return am_call(c,0x1c5b0,0x47dc0); // JSR 1c5b0.L.
    case 0x47dc0:return am_call(c,0x1bee4,0x47dc6); // JSR 1bee4.L.
    // BCLR #5,5683(A5); BCLR #1,5683(A5); JSR ca48.L.
    case 0x47dc6:
        if(!ac_bit(c,r.a[5],0x5683,5,false) || !ac_bit(c,r.a[5],0x5683,1,false))return false;
        return am_call(c,0xca48,0x47dd8);
    case 0x47dd8:return ac_timer(c,0x1e,0x47de4); // MOVE.W #1e,7a(A6); MOVE.L #47de4,(A6).
    // 47de4 (dispatcher callback): SUBQ.W #1,7a(A6); BNE 480bc.
    case 0x47de4:return ac_count(c,0x47dec);
    // TST.B 568e(A5); BEQ 47e30.
    case 0x47dec:if(!ac_read(c,0x568e,1,value))return false;r.pc=(value&255U)?0x47df4:0x47e30;return true;
    case 0x47df4:return am_call(c,0x9056,0x47dfa); // JSR 9056.L.
    // MOVEA.L #e4234,A0; MOVE.W #0,D0; JSR 28ae.L (known C).
    case 0x47dfa:r.a[0]=AC_CHILD_FADE;am_word(r.d[0],0);return am_call(c,0x28ae,0x47e0a);
    // SCC.B 62(A6) (C clear: ff, C set: 00; flags unchanged); BCC 47e1c. The known C is checked before the write.
    case 0x47e0a:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"area clear caller requires known carry");
        if(!am_write(c,am_index(r.a[6],0x62),1,r.carry==AnimationCarryClear?0xffU:0U))return false;
        r.pc=r.carry==AnimationCarryClear?0x47e1c:0x47e12;return true;
    // MOVEQ #0,D0; MOVE.B 7c(A6),D0; MOVE.W D0,76(A0) (A0 = the new child).
    case 0x47e12:
        if(!ac_level(c) || !am_write(c,am_index(r.a[0],0x76),2,r.d[0]&65535U))return false;r.pc=0x47e1c;return true;
    case 0x47e1c:if(!am_write(c,r.a[6],4,0x47e22))return false;r.pc=0x47e22;return true; // MOVE.L #47e22,(A6).
    // 47e22 (dispatcher callback): TST.B 62(A6); BEQ 480bc.
    case 0x47e22:if(!am_read(c,am_index(r.a[6],0x62),1,value))return false;r.pc=(value&255U)?0x47e2a:0x480bc;return true;
    case 0x47e2a:return am_call(c,0x9060,0x47e30); // JSR 9060.L.
    // MOVEA.L #d72fe,A0; MOVE.W #14,D0; JSR 28ae.L (C not checked by 47e40).
    case 0x47e30:r.a[0]=AC_CHILD_SOUND;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x47e40);
    // MOVEQ #0,D0; MOVE.B 7c(A6),D0; ADDQ.W #1,D0; MOVE.W D0,76(A0); MOVE.W #19db,D0; JSR 3af8.L.
    case 0x47e40:
        if(!ac_level(c))return false;am_word(r.d[0],r.d[0]+1U);
        if(!am_write(c,am_index(r.a[0],0x76),2,r.d[0]&65535U))return false;
        am_word(r.d[0],0x19db);return am_call(c,0x3af8,0x47e56);
    case 0x47e56:return ac_timer(c,0xa0,0x47e62); // MOVE.W #a0,7a(A6); MOVE.L #47e62,(A6).
    // 47e62 (dispatcher callback): SUBQ.W #1,7a(A6); BNE 480bc.
    case 0x47e62:return ac_count(c,0x47e6a);
    case 0x47e6a:if(!am_write(c,r.a[6],4,0x47e70))return false;r.pc=0x47e70;return true; // MOVE.L #47e70,(A6).
    // 47e70 (dispatcher callback): TST.B 5d44(A5); BEQ 480bc.
    case 0x47e70:if(!ac_read(c,0x5d44,1,value))return false;r.pc=(value&255U)?0x47e78:0x480bc;return true;
    // MOVEQ #e1,D0; MOVEQ #e1,D1; MOVEQ #e1,D2; MOVEQ #30,D3; JSR 8c16.L.
    case 0x47e78:r.d[0]=0xffffffe1U;r.d[1]=0xffffffe1U;r.d[2]=0xffffffe1U;r.d[3]=0x30;return am_call(c,0x8c16,0x47e86);
    case 0x47e86:return ac_timer(c,0x30,0x47e92); // MOVE.W #30,7a(A6); MOVE.L #47e92,(A6).
    // 47e92 (dispatcher callback): SUBQ.W #1,7a(A6); BNE 480bc.
    case 0x47e92:return ac_count(c,0x47e9a);
    // ADDQ.B #1,7c(A6); MOVE.B 7c(A6),5680(A5); CLR.B 5681(A5); BRA 477ee (F1c boundary).
    case 0x47e9a:
        if(!am_read(c,am_index(r.a[6],0x7c),1,value) || !am_write(c,am_index(r.a[6],0x7c),1,(value+1U)&255U))return false;
        if(!am_read(c,am_index(r.a[6],0x7c),1,value) || !ac_write(c,0x5680,1,value&255U) || !ac_write(c,0x5681,1,0))return false;
        r.pc=0x477ee;return true;

    case 0x4b6e4:if(!ac_write(c,0x5b85,1,0xff))return false;return am_return(c); // MOVE.B #ff,5b85(A5); RTS.
    case 0x4b6ec:if(!ac_write(c,0x5b87,1,0xff))return false;return am_return(c); // MOVE.B #ff,5b87(A5); RTS.

    // 1c5b0: LEA 100cb8.L,A0; JSR 289e.L. 1c5bc: BCC 1c5cc. 1c5c0: BSET #6,61(A0); BSET #0,a8(A0).
    case 0x1c5b0:r.a[0]=AC_PLAYER1;return am_call(c,0x289e,0x1c5bc);
    case 0x1c5bc:return ac_carry(c,0x1c5cc,0x1c5c0);
    case 0x1c5c0:case 0x1c5dc:
        if(!ac_bit(c,r.a[0],0x61,6,true) || !ac_bit(c,r.a[0],0xa8,0,true))return false;
        r.pc=r.pc==0x1c5c0?0x1c5cc:0x1c5e8;return true;
    case 0x1c5cc:r.a[0]=AC_PLAYER2;return am_call(c,0x289e,0x1c5d8); // LEA 100da8.L,A0; JSR 289e.L.
    case 0x1c5d8:return ac_carry(c,0x1c5e8,0x1c5dc); // BCC 1c5e8.
    case 0x1c5e8:return am_return(c); // RTS.

    // 1bee4: LEA 1bec0(PC),A0; MOVEQ #0,D0; JSR 49c20.L. 1bef0: MOVEQ #1,D0; JMP 49c20.L (its RTS returns to 47dc6).
    case 0x1bee4:r.a[0]=AC_INPUT_SLOT;r.d[0]=0;return am_call(c,0x49c20,0x1bef0);
    case 0x1bef0:r.d[0]=1;r.pc=0x49c20;return true;

    case 0xca48:if(!ac_write(c,0x8967,1,0xff))return false;return am_return(c); // MOVE.B #ff,-7699(A5); RTS.
    case 0x9056:if(!am_write(c,AC_PALETTE_SET,1,0xff))return false;return am_return(c); // MOVE.B #ff,107def.L; RTS.
    default:return am_error(c,"unsupported animation area clear PC");
    }
}
}
