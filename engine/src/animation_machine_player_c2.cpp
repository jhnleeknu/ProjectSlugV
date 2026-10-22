#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc2_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc2_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR #bit,d16(A6) (a memory operand: BYTE, bit = the immediate modulo 8). op 0 tests, 1 sets, 2 clears; old is the bit before
// (the Z of the instruction is old = 0).
bool pc2_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!pc2_get(c,c.s.a[6],displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return pc2_put(c,c.s.a[6],displacement,1,op==1U?(value|mask):(value&~mask));
}
// TST.B / CMPI.B d16(A6) against k; BNE.W / BEQ.W: equal_pc when BYTE = k, else other_pc.
bool pc2_byte_is(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc2_get(c,c.s.a[6],displacement,1,value))return false;
    c.s.pc=value==k?equal_pc:other_pc;return true;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc2_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c2 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #v,(A6) followed by v: the next PC is v (installed value entered at once).
bool pc2_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!pc2_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVEQ #0,D7; MOVE.B 9f(A6),D7; ADD.W D7,D7; MOVE.W (A0,D7.W),D7 (1cac2 / 1cb08: the WORD of the record table A0 for the state BYTE 9f).
bool pc2_state_word(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[7]=0;
    if(!pc2_get(c,r.a[6],0x9f,1,value))return false;am_byte(r.d[7],value);am_word(r.d[7],r.d[7]+r.d[7]);
    if(!am_read(c,am_index(r.a[0],r.d[7]&0xffffU),2,value))return false;am_word(r.d[7],value);return true;
}
// MOVE.W #mask,D1; AND.W D0,D1; BNE.W set_pc (fall through to clear_pc).  D1 bits 16..31 kept.
void pc2_mask(AnimationMachineContext& c,std::uint32_t mask,std::uint32_t clear_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;am_word(r.d[1],mask);am_word(r.d[1],r.d[1]&r.d[0]);
    r.pc=(r.d[1]&0xffffU)!=0U?set_pc:clear_pc;
}
// MOVE.W 1e(A6),D0; JSR ce02.l (D0 bits 16..31 kept).
bool pc2_shape(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc2_get(c,c.s.a[6],0x1e,2,value))return false;am_word(c.s.d[0],value);return am_call(c,0xce02,return_pc);
}
// ASR.W #4,Dn (the low WORD shifted right by 4 with its sign copied in; Dn bits 16..31 kept).
void pc2_asr4(std::uint32_t& r) {
    const std::uint32_t w=r&0xffffU;am_word(r,(w&0x8000U)!=0U?((w>>4)|0xf000U):(w>>4));
}
// ASR.L #5,Dn (LONG, sign copied into bits 27..31).
std::uint32_t pc2_asr5(std::uint32_t v) {
    return (v&0x80000000U)!=0U?((v>>5)|0xf8000000U):(v>>5);
}
// ADD.L Dn,d16(A6) (LONG read, modulo 2^32 sum, LONG write).
bool pc2_add_long(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t addend) {
    std::uint32_t value=0;if(!pc2_get(c,c.s.a[6],displacement,4,value))return false;return pc2_put(c,c.s.a[6],displacement,4,value+addend);
}
// MOVE.L #21602,84(A6); MOVE.B #0,9c(A6); MOVE.B #1,aa(A6); CLR.W 7a(A6) (the second callback slot of the node: 21602 is unit C3).
bool pc2_slot84(AnimationMachineContext& c) {
    return pc2_put(c,c.s.a[6],0x84,4,0x21602) && pc2_put(c,c.s.a[6],0x9c,1,0) && pc2_put(c,c.s.a[6],0xaa,1,1) && pc2_put(c,c.s.a[6],0x7a,2,0);
}
// The 23 field writes of 1d22a after BCLR.B #7,61(A6) / BSET.B #6,15(A6) (original order).
bool pc2_reset(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;const std::uint32_t a6=r.a[6];
    if(!pc2_put(c,a6,0x68,2,0x8834) || !pc2_put(c,a6,0x1e,2,0x8834) || !pc2_put(c,a6,0x56,4,0) || !pc2_slot84(c) ||
       !pc2_put(c,a6,0x36,4,0) || !pc2_put(c,a6,0x3a,4,0) || !pc2_put(c,a6,0x64,4,0) || !pc2_put(c,a6,0x84,4,0x21602) ||
       !pc2_put(c,a6,0x9c,1,0) || !pc2_put(c,a6,0xa9,1,0) || !pc2_put(c,a6,0xaa,1,1) || !pc2_put(c,a6,0x92,2,0))return false;
    const std::uint32_t bytes[11]={0x9d,0xa4,0xa5,0xa2,0xa3,0xab,0xac,0xad,0xa7,0xa8,0xa6};
    for(unsigned int i=0;i<11U;++i)if(!pc2_put(c,a6,bytes[i],1,0))return false;
    return pc2_put(c,a6,0xb6,2,0xffff) && pc2_put(c,a6,0xb8,1,0) && pc2_put(c,a6,0xb9,1,0) && pc2_put(c,a6,0xb2,4,0);
}
}
// Player C2 (196 block starts, contract docs/analysis/animation-machine-player-c2-contract.md; area C plan unit C2): the player object main state
// 1d222 (BCS of the C1 block 1d21c: reset of the node, 1d2d4..1d390 the start pose from 1aa3a, the input 1d15a / 1d0c2 lights, the record e8b5a (C3) /
// ea5f0 / 2986 child 6f1c4) and its later states 1ddd0..1de38, 1ed78 / 1edb0 (the state machine head; 1edb0 is the installed callback of the IO run),
// 1f1d8..1f2a0, 1f7a4..1f80c, 1fa3c..1fafc, the helpers 1a9e8 (the live JMP (A1) 1aa38, contract decision 2), 1c1e2, 1cab6 / 1cabe (record table to
// the interpreter 49f96), 1cb08, 1cd12, 1cd98 (input summary into D0), 1d0c2, 1d1d0, 1d582, 1dbd8, 1dfe6 and 1ed34.  C: the consumers 1d1d6 (48384 of
// C3), 1d58e (4836e), 1d59c (49c38), 1ed80 / 1fa44 (1cb08), 1f296 / 1f802 / 1fac0 (49fc6) read a known C or fail; 1cb08 ends with C Clear (MOVE.W),
// 1dff0 / 1ed54 (ANDI.B #fe,CCR; RTS) return Clear, 1e016 (SUB.W D1,D0; RTS) returns the borrow, 1edf6 (AND.W) leaves Clear; the RTS 1cb18 1ed3c 1ed48
// and the BTST blocks 1ed34 1ed3e keep the incoming C (dispatcher carry list).  MOVE.L #v,(A6) enters v at once when v follows (1d466 1edb0 1f224 1f7da
// 1faaa); 1f29a 1f806 1fac8 write the callback LONG only.
bool animation_player_c2_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool old=false;
    switch(r.pc) {
    // ---- 1a9e8 (JSR from 201a8, C3): CMPI.B #6,6e(A6); BNE.W 1aa2a.
    case 0x1a9e8:return pc2_byte_is(c,0x6e,6,0x1a9f2,0x1aa2a);
    // MOVEA.L 5434(A5),A1; CMPA.W #0,A1; BEQ.W 1aa2a (CMPA.W compares the whole A1 with the sign-extended 0).
    case 0x1a9f2:if(!pc2_get(c,r.a[5],0x5434,4,r.a[1]))return false;r.pc=r.a[1]==0U?0x1aa2a:0x1a9fe;return true;
    // MOVEA.L 3e(A6),A0; CMPA.L #109156,A0; BEQ.W 1aa2c / the three other map buffers.
    case 0x1a9fe:if(!pc2_get(c,r.a[6],0x3e,4,r.a[0]))return false;r.pc=r.a[0]==0x109156U?0x1aa2c:0x1aa0c;return true;
    case 0x1aa0c:r.pc=r.a[0]==0x10b1d6U?0x1aa2c:0x1aa16;return true;
    case 0x1aa16:r.pc=r.a[0]==0x10d256U?0x1aa2c:0x1aa20;return true;
    case 0x1aa20:r.pc=r.a[0]==0x10d2d6U?0x1aa2c:0x1aa2a;return true;
    // MOVE.W 2e(A6),D4; MOVE.W 32(A6),D5; ASR.W #4,D4; ASR.W #4,D5; JMP (A1): PC := A1 (32 bit, live target, contract decision 2).
    case 0x1aa2c:
        if(!pc2_get(c,r.a[6],0x2e,2,value))return false;am_word(r.d[4],value);
        if(!pc2_get(c,r.a[6],0x32,2,value))return false;am_word(r.d[5],value);
        pc2_asr4(r.d[4]);pc2_asr4(r.d[5]);r.pc=r.a[1];return true;
    // ---- 1c1e2: MOVEQ #0,D0; MOVE.B a0(A6),D0; MOVE.B D0,9f(A6); MOVE.B 1c1d8(PC,D0.W),9e(A6); RTS (fixed ROM BYTE table 1c1d8 + D0.W).
    case 0x1c1e2:
        r.d[0]=0;if(!pc2_get(c,r.a[6],0xa0,1,value))return false;am_byte(r.d[0],value);
        if(!pc2_put(c,r.a[6],0x9f,1,r.d[0]) || !am_read(c,am_index(0x1c1d8,r.d[0]&0xffffU),1,value) || !pc2_put(c,r.a[6],0x9e,1,value))return false;
        return am_return(c);
    // ---- 1cab6 / 1cabe: LEA 26(A6),A1 (BRA.W 1cac2) / LEA 94(A6),A1.
    case 0x1cab6:r.a[1]=am_index(r.a[6],0x26);r.pc=0x1cac2;return true;
    case 0x1cabe:r.a[1]=am_index(r.a[6],0x94);r.pc=0x1cac2;return true;
    // 1cac2: the WORD of the record table A0 for BYTE 9f; BNE.W 1cad4 / MOVE.W (A0),D7 (entry 0 is the default).
    case 0x1cac2:if(!pc2_state_word(c))return false;r.pc=(r.d[7]&0xffffU)!=0U?0x1cad4:0x1cad2;return true;
    case 0x1cad2:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[7],value);r.pc=0x1cad4;return true;
    // LEA (A0,D7.W),A0; MOVE.W (A0),D7; ADD.W D7,D7 twice; MOVEA.L 22(A6),A0; MOVE.L (A0,D7.W),D7; BNE.W 1caf0.
    case 0x1cad4:
        r.a[0]=am_index(r.a[0],r.d[7]&0xffffU);if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[7],value);
        am_word(r.d[7],r.d[7]+r.d[7]);am_word(r.d[7],r.d[7]+r.d[7]);
        if(!pc2_get(c,r.a[6],0x22,4,r.a[0]) || !am_read(c,am_index(r.a[0],r.d[7]&0xffffU),4,value))return false;
        r.d[7]=value;r.pc=value!=0U?0x1caf0:0x1caea;return true;
    case 0x1caea:r.d[7]=0x1cafe;r.pc=0x1caf0;return true;                                                   // MOVE.L #1cafe,D7 (default script).
    // MOVEA.L D7,A0; EXG A0,A1; MOVE.W #100,D0; JMP 49f96.l (the interpreter: A1 = script, A0 = 26(A6) / 94(A6)).
    case 0x1caf0:r.a[0]=r.a[1];r.a[1]=r.d[7];am_word(r.d[0],0x100);r.pc=0x49f96;return true;
    // ---- 1cb08: the WORD of the record table A0 for BYTE 9f; BNE.W 1cb1a (unit C5).  The MOVE.W leaves C Clear for both sides (1ed80 / 1fa44 read it
    // through the RTS 1cb18).
    case 0x1cb08:if(!pc2_state_word(c))return false;r.carry=AnimationCarryClear;r.pc=(r.d[7]&0xffffU)!=0U?0x1cb1a:0x1cb18;return true;
    // ---- RTS blocks (1cb18 1ed3c 1ed48 keep the incoming C: dispatcher carry list).
    case 0x1aa2a:case 0x1cb18:case 0x1cd1a:case 0x1cd28:case 0x1cd4e:case 0x1cd56:case 0x1cec0:case 0x1cef8:case 0x1d1f2:case 0x1d466:case 0x1d5aa:
    case 0x1dbee:case 0x1ed3c:case 0x1ed48:return am_return(c);
    // ---- 1cd12: TST.W a(A4); BNE.W 1cd1c / RTS.
    case 0x1cd12:if(!pc2_get(c,r.a[4],0xa,2,value))return false;r.pc=value!=0U?0x1cd1c:0x1cd1a;return true;
    // MOVEA.L 5474(A5),A0; CMPA.W #0,A0; BNE.W 1cd2a / RTS.
    case 0x1cd1c:if(!pc2_get(c,r.a[5],0x5474,4,r.a[0]))return false;r.pc=r.a[0]!=0U?0x1cd2a:0x1cd28;return true;
    // MOVE.W 42(A6),D2; MOVE.W 46(A6),D3; SUB.W 53a2(A5),D2; SUB.W 53a6(A5),D3; SUB.W 5470(A5),D2; SMI.B D7; SUB.W 5472(A5),D3; SUB.W (A0)+,D2;
    // SUB.W (A0)+,D3; CMP.W (A0)+,D2; BCS.W 1cd50 / RTS (unsigned WORD compare; D2 / D3 / D7 bits above the WORD / BYTE kept).
    case 0x1cd2a: {
        std::uint32_t v42=0,v46=0,w=0;
        if(!pc2_get(c,r.a[6],0x42,2,v42) || !pc2_get(c,r.a[6],0x46,2,v46))return false;am_word(r.d[2],v42);am_word(r.d[3],v46);
        if(!pc2_get(c,r.a[5],0x53a2,2,w))return false;am_word(r.d[2],r.d[2]-w);
        if(!pc2_get(c,r.a[5],0x53a6,2,w))return false;am_word(r.d[3],r.d[3]-w);
        if(!pc2_get(c,r.a[5],0x5470,2,w))return false;am_word(r.d[2],r.d[2]-w);am_byte(r.d[7],(r.d[2]&0x8000U)!=0U?0xffU:0U);
        if(!pc2_get(c,r.a[5],0x5472,2,w))return false;am_word(r.d[3],r.d[3]-w);
        if(!am_read(c,r.a[0],2,w))return false;r.a[0]+=2U;am_word(r.d[2],r.d[2]-w);
        if(!am_read(c,r.a[0],2,w))return false;r.a[0]+=2U;am_word(r.d[3],r.d[3]-w);
        if(!am_read(c,r.a[0],2,w))return false;r.a[0]+=2U;
        r.pc=(r.d[2]&0xffffU)<w?0x1cd50:0x1cd4e;return true;
    }
    case 0x1cd50:if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;r.pc=(r.d[3]&0xffffU)<value?0x1cd58:0x1cd56;return true;  // CMP.W (A0)+,D3; BCS.W.
    // ANDI.W #3,D0; BTST.B #0,15(A6); SEQ.B D6; EOR.B D6,D7; BEQ.W 1cd7c.
    case 0x1cd58:
        am_word(r.d[0],r.d[0]&3U);if(!pc2_bit(c,0x15,0,0,old))return false;am_byte(r.d[6],old?0U:0xffU);am_byte(r.d[7],r.d[7]^r.d[6]);
        r.pc=(r.d[7]&0xffU)==0U?0x1cd7c:0x1cd6a;return true;
    case 0x1cd6a:r.pc=(r.d[6]&0xffU)==0U?0x1cd78:0x1cd70;return true;                                     // TST.B D6; BEQ.W 1cd78.
    case 0x1cd70:am_word(r.d[0],r.d[0]|4U);r.pc=0x1cd7c;return true;                                      // ORI.W #4,D0; BRA.W 1cd7c.
    case 0x1cd78:am_word(r.d[0],r.d[0]|8U);r.pc=0x1cd7c;return true;                                      // ORI.W #8,D0.
    // ORI.W #40,D0; BSET.B #5,a8(A6); MOVE.W #12,90(A6); MOVE.B #6,ac(A6); RTS.
    case 0x1cd7c:
        am_word(r.d[0],r.d[0]|0x40U);
        if(!pc2_bit(c,0xa8,5,1,old) || !pc2_put(c,r.a[6],0x90,2,0x12) || !pc2_put(c,r.a[6],0xac,1,6))return false;return am_return(c);
    // ---- 1cd98: MOVEA.L 8c(A6),A4; BSET.B #7,a8(A6); BEQ.W 1cdb0 (old bit clear).
    case 0x1cd98:if(!pc2_get(c,r.a[6],0x8c,4,r.a[4]) || !pc2_bit(c,0xa8,7,1,old))return false;r.pc=old?0x1cda6:0x1cdb0;return true;
    case 0x1cda6:r.d[0]=0;if(!pc2_get(c,r.a[6],0xad,1,value))return false;am_byte(r.d[0],value);r.pc=0x1ce80;return true;  // MOVEQ #0; MOVE.B ad; BRA.
    case 0x1cdb0:if(!pc2_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49be0,0x1cdba);     // JSR 49be0.l.
    // MOVE.W (A0),D0; ANDI.W #ff7f,D0; BTST.B #0,D0 (register: bit 0); BEQ.W 1cdd2.
    case 0x1cdba:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value&0xff7fU);r.pc=(r.d[0]&1U)==0U?0x1cdd2:0x1cdc8;return true;
    case 0x1cdc8:if(!pc2_bit(c,0x61,5,1,old))return false;r.pc=0x1cdd8;return true;                    // BSET.B #5,61(A6); BRA.W 1cdd8.
    case 0x1cdd2:if(!pc2_bit(c,0x61,5,2,old))return false;r.pc=0x1cdd8;return true;                    // BCLR.B #5,61(A6).
    case 0x1cdd8:r.pc=(r.d[0]&2U)==0U?0x1cdea:0x1cde0;return true;                                       // BTST.B #1,D0; BEQ.W 1cdea (1cde0 is C7).
    case 0x1cdea:if(!pc2_bit(c,0x61,4,2,old))return false;r.pc=0x1cdf0;return true;                    // BCLR.B #4,61(A6) (1cdf0 is C7).
    // 1cdfe (BCS from 1cdf6, C7): BTST.B #0,a7(A6); BNE.W 1ce2a.
    case 0x1cdfe:if(!pc2_bit(c,0xa7,0,0,old))return false;r.pc=old?0x1ce2a:0x1ce08;return true;
    // MOVEQ #0,D1; MOVE.B 4(A4),D1; LEA 22642(PC),A3; TST.B (A3,D1.W); BNE.W 1ce2a (fixed ROM BYTE table 22642 + D1.W).
    case 0x1ce08:
        r.d[1]=0;if(!pc2_get(c,r.a[4],4,1,value))return false;am_byte(r.d[1],value);r.a[3]=0x22642;
        if(!am_read(c,am_index(r.a[3],r.d[1]&0xffffU),1,value))return false;r.pc=value!=0U?0x1ce2a:0x1ce1a;return true;
    // MOVE.B 2(A4),D2; CMP.B 3(A4),D2; BCS.W 1ce2a (unsigned BYTE) / ANDI.W #ffef,D0.
    case 0x1ce1a:
        if(!pc2_get(c,r.a[4],2,1,value))return false;am_byte(r.d[2],value);if(!pc2_get(c,r.a[4],3,1,value))return false;
        r.pc=(r.d[2]&0xffU)<value?0x1ce2a:0x1ce26;return true;
    case 0x1ce26:am_word(r.d[0],r.d[0]&0xffefU);r.pc=0x1ce2a;return true;
    case 0x1ce2a:return pc2_byte_is(c,0x6e,7,0x1ce34,0x1ce50);                                           // CMPI.B #7,6e(A6); BNE.W 1ce50.
    // BCLR.B #2,a8(A6); ORI.W #2,D0; CMPI.B #1,9e(A6); BNE.W 1ce4c.
    case 0x1ce34:if(!pc2_bit(c,0xa8,2,2,old))return false;am_word(r.d[0],r.d[0]|2U);return pc2_byte_is(c,0x9e,1,0x1ce48,0x1ce4c);
    case 0x1ce48:am_word(r.d[0],r.d[0]&0xffdfU);r.pc=0x1ce4c;return true;                                // ANDI.W #ffdf,D0.
    case 0x1ce4c:r.pc=0x1ce5e;return true;                                                                 // BRA.W 1ce5e.
    case 0x1ce50:if(!pc2_bit(c,0xa8,2,2,old))return false;r.pc=old?0x1ce5a:0x1ce5e;return true;          // BCLR.B #2,a8(A6); BEQ.W 1ce5e.
    case 0x1ce5a:am_word(r.d[0],r.d[0]&0xfffdU);r.pc=0x1ce5e;return true;                                // ANDI.W #fffd,D0.
    case 0x1ce5e:return am_call(c,0x1cd12,0x1ce62);                                                       // BSR.W 1cd12.
    case 0x1ce62:return pc2_byte_is(c,0xab,0,0x1ce6e,0x1ce6a);                                           // TST.B ab(A6); BEQ.W 1ce6e.
    case 0x1ce6a:am_word(r.d[0],r.d[0]&0xffbfU);r.pc=0x1ce6e;return true;                                // ANDI.W #ffbf,D0.
    // MOVEQ #0,D1; MOVE.B 9e(A6),D1; LEA 1cd94(PC),A0; AND.B (A0,D1.W),D0; MOVE.B D0,ad(A6) (fixed ROM BYTE table 1cd94 + D1.W).
    case 0x1ce6e:
        r.d[1]=0;if(!pc2_get(c,r.a[6],0x9e,1,value))return false;am_byte(r.d[1],value);r.a[0]=0x1cd94;
        if(!am_read(c,am_index(r.a[0],r.d[1]&0xffffU),1,value))return false;am_byte(r.d[0],r.d[0]&value);
        if(!pc2_put(c,r.a[6],0xad,1,r.d[0]))return false;r.pc=0x1ce80;return true;
    // MOVE.B a6(A6),D1; AND.B D0,D1; OR.B D1,a5(A6); BCLR.B #3,a7(A6); BTST.B #2,D0; BEQ.W 1cea8 (1ce98 is C8).
    case 0x1ce80:
        if(!pc2_get(c,r.a[6],0xa6,1,value))return false;am_byte(r.d[1],value&r.d[0]);
        if(!pc2_get(c,r.a[6],0xa5,1,value) || !pc2_put(c,r.a[6],0xa5,1,value|(r.d[1]&0xffU)) || !pc2_bit(c,0xa7,3,2,old))return false;
        r.pc=(r.d[0]&4U)==0U?0x1cea8:0x1ce98;return true;
    case 0x1cea8:r.pc=(r.d[0]&8U)==0U?0x1cec0:0x1ceb0;return true;                                      // BTST.B #3,D0; BEQ.W 1cec0 (1ceb0 is C4).
    // ---- 1d0c2: MOVE.L A0,-(A7); JSR 8ff4.l.
    case 0x1d0c2:if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x8ff4,0x1d0ca);
    // MOVEA.L (A7),A0 / MOVEA.L (A7)+,A0; MOVE.W 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0 / #1,D1; JSR 8ebe.l.
    case 0x1d0ca:case 0x1d0e0:
        if(r.pc==0x1d0ca) {if(!am_read(c,r.a[7],4,r.a[0]))return false;}
        else if(!am_pop(c,4,r.a[0]))return false;
        if(!pc2_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);
        if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),2,value))return false;am_word(r.d[0],value);
        am_byte(r.d[1],r.pc==0x1d0ca?0U:1U);return am_call(c,0x8ebe,r.pc==0x1d0ca?0x1d0e0U:0x1d0f6U);
    // MOVEQ #0,D0; MOVE.B 1a(A6),D0; MOVE.W #0,D1; MOVE.W #8,D2; JSR 8cda.l.
    case 0x1d0f6:
        r.d[0]=0;if(!pc2_get(c,r.a[6],0x1a,1,value))return false;am_byte(r.d[0],value);am_word(r.d[1],0);am_word(r.d[2],8);
        return am_call(c,0x8cda,0x1d10a);
    case 0x1d10a:if(!pc2_get(c,r.a[6],0x19,1,value) || !pc2_put(c,r.a[6],0x14,1,value))return false;return am_return(c);  // MOVE.B 19,14; RTS.
    // ---- 1d15a: JSR 1aa3a.l / LEA 1d112(PC),A0; BTST.B #3,D0; BEQ.W 1d170 / LEA 1d136(PC),A0.
    case 0x1d15a:return am_call(c,0x1aa3a,0x1d160);
    case 0x1d160:r.a[0]=0x1d112;r.pc=(r.d[0]&8U)==0U?0x1d170:0x1d16c;return true;
    case 0x1d16c:r.a[0]=0x1d136;r.pc=0x1d170;return true;
    // MOVEQ #0,D0; MOVE.B 9f(A6),D0; ADD.W D0,D0 twice; MOVEA.L (A0,D0.W),A0; BRA.W 1d0c2 (fixed ROM LONG table).
    case 0x1d170:
        r.d[0]=0;if(!pc2_get(c,r.a[6],0x9f,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),4,r.a[0]))return false;r.pc=0x1d0c2;return true;
    // ---- 1d1d0: JSR 48384.l (unit C3) / BCS.W 1d1f2 (C of 48384) / TST.W 90(A6); BEQ.W 1d1f2 / MOVEA.L #361e4,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x1d1d0:return am_call(c,0x48384,0x1d1d6);
    case 0x1d1d6:return pc2_carry(c,0x1d1da,0x1d1f2);
    case 0x1d1da:if(!pc2_get(c,r.a[6],0x90,2,value))return false;r.pc=value==0U?0x1d1f2:0x1d1e2;return true;
    case 0x1d1e2:r.a[0]=0x361e4;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x1d1f2);
    // ---- 1d222 (BCS of C1 1d21c, BRA from 1eb94): MOVE.W 76(A6),D0; BSR.W 1d198.
    case 0x1d222:if(!pc2_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);return am_call(c,0x1d198,0x1d22a);
    // BCLR.B #7,61(A6); BSET.B #6,15(A6); the node reset (pc2_reset); MOVE.W 78(A6),D0; BSET.B D0,60(A6) (bit D0 modulo 8); JSR 1aa3a.l.
    case 0x1d22a: {
        if(!pc2_bit(c,0x61,7,2,old) || !pc2_bit(c,0x15,6,1,old) || !pc2_reset(c) || !pc2_get(c,r.a[6],0x78,2,value))return false;
        am_word(r.d[0],value);if(!pc2_bit(c,0x60,r.d[0]&7U,1,old))return false;return am_call(c,0x1aa3a,0x1d2d4);
    }
    case 0x1d2d4:am_word(r.d[1],r.d[0]);r.pc=(r.d[1]&0x20U)!=0U?0x1d2e6:0x1d2de;return true;             // MOVE.W D0,D1; BTST.B #5,D1; BNE.W 1d2e6.
    case 0x1d2de:if(!pc2_get(c,r.a[6],0x8c,4,r.a[4]) || !pc2_put(c,r.a[4],8,2,0))return false;r.pc=0x1d2e6;return true;  // MOVEA.L 8c; CLR.W 8(A4).
    case 0x1d2e6:r.d[0]=5;r.pc=(r.d[1]&8U)==0U?0x1d2f2:0x1d2f0;return true;                              // MOVEQ #5,D0; BTST.B #3,D1; BEQ.W 1d2f2.
    case 0x1d2f0:r.d[0]=3;r.pc=0x1d2f2;return true;                                                       // MOVEQ #3,D0.
    case 0x1d2f2:r.pc=(r.d[1]&0x40U)==0U?0x1d2fc:0x1d2fa;return true;                                   // BTST.B #6,D1; BEQ.W 1d2fc.
    case 0x1d2fa:r.d[0]=4;r.pc=0x1d2fc;return true;                                                       // MOVEQ #4,D0.
    case 0x1d2fc:r.pc=(r.d[1]&0x400U)==0U?0x1d306:0x1d304;return true;                                  // BTST.B #a,D1 (register: bit 10); BEQ.W 1d306.
    case 0x1d304:r.d[0]=7;r.pc=0x1d306;return true;                                                       // MOVEQ #7,D0.
    case 0x1d306:r.a[0]=r.a[6];return am_call(c,0x1c1f4,0x1d30c);                                         // MOVEA.L A6,A0; BSR.W 1c1f4.
    case 0x1d30c:return am_call(c,0x1c1e2,0x1d310);                                                       // BSR.W 1c1e2.
    case 0x1d310:return am_call(c,0x1d15a,0x1d314);                                                       // BSR.W 1d15a.
    case 0x1d314:if(!pc2_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);return am_call(c,0xe8b5a,0x1d31e);  // JSR e8b5a.l (C3).
    case 0x1d31e:r.pc=(r.d[7]&0xffffU)==0U?0x1d45a:0x1d326;return true;                                 // CMPI.W #0,D7; BEQ.W 1d45a.
    case 0x1d326:if(!am_push(c,2,r.d[7]&0xffffU))return false;return am_call(c,0xea5f0,0x1d32e);        // MOVE.W D7,-(A7); JSR ea5f0.l.
    // MOVEA.L 8c(A6),A4; MOVE.B 4(A4),D0; MOVE.L #6f1c4,D7; CMPI.B #10,D0; BEQ.W 1d352.
    case 0x1d32e:
        if(!pc2_get(c,r.a[6],0x8c,4,r.a[4]) || !pc2_get(c,r.a[4],4,1,value))return false;am_byte(r.d[0],value);r.d[7]=0x6f1c4;
        r.pc=(r.d[0]&0xffU)==0x10U?0x1d352:0x1d344;return true;
    case 0x1d344:r.d[7]=0x6f1c4;r.pc=(r.d[0]&0xffU)==0x11U?0x1d352:0x1d380;return true;                 // MOVE.L #6f1c4,D7; CMPI.B #11,D0; BNE.W 1d380.
    case 0x1d352:r.a[0]=r.d[7];am_word(r.d[0],0xa);r.a[1]=0x100bf4;return am_call(c,0x2986,0x1d364);    // MOVEA.L D7,A0; MOVE.W #a,D0; JSR 2986.l.
    // MOVE.W 78(A6),76(A0); MOVE.W 42(A6),D0; MOVE.W #200,D1; MOVEA.W #0,A1; LEA 2e(A0),A0; JSR 43e08.l.
    case 0x1d364:
        if(!pc2_get(c,r.a[6],0x78,2,value) || !pc2_put(c,r.a[0],0x76,2,value) || !pc2_get(c,r.a[6],0x42,2,value))return false;
        am_word(r.d[0],value);am_word(r.d[1],0x200);r.a[1]=0;r.a[0]=am_index(r.a[0],0x2e);return am_call(c,0x43e08,0x1d380);
    // MOVE.W #78,90(A6); MOVE.W (A7)+,D7; CMPI.W #1,D7; BEQ.W 1de3c (C9) / CMPI.W #4,D7; BEQ.W 1ddd0 (1d398 is C6).
    case 0x1d380:if(!pc2_put(c,r.a[6],0x90,2,0x78) || !am_pop(c,2,value))return false;am_word(r.d[7],value);
        r.pc=(r.d[7]&0xffffU)==1U?0x1de3c:0x1d390;return true;
    case 0x1d390:r.pc=(r.d[7]&0xffffU)==4U?0x1ddd0:0x1d398;return true;
    case 0x1d45a:if(!pc2_bit(c,0xa8,4,1,old))return false;return pc2_install(c,0x1d466);                // BSET.B #4,a8(A6); MOVE.L #1d466,(A6).
    // ---- 1d582: JSR 43e34.l / JSR 4836e.l / BCC.W 1d5aa / MOVE.W 78(A6),D0; JSR 49c38.l / BCS.W 1d5aa / LEA 1d5ac(PC),A0; JSR 49c20.l / RTS.
    case 0x1d582:return am_call(c,0x43e34,0x1d588);
    case 0x1d588:return am_call(c,0x4836e,0x1d58e);
    case 0x1d58e:return pc2_carry(c,0x1d5aa,0x1d592);
    case 0x1d592:if(!pc2_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49c38,0x1d59c);
    case 0x1d59c:return pc2_carry(c,0x1d5a0,0x1d5aa);
    case 0x1d5a0:r.a[0]=0x1d5ac;return am_call(c,0x49c20,0x1d5aa);
    // ---- 1dbd8: JSR 1aa3a.l / MOVE.W #c8,D1; AND.W D0,D1; BNE.W 1dbee / JSR 4c0ea.l / RTS.
    case 0x1dbd8:return am_call(c,0x1aa3a,0x1dbde);
    case 0x1dbde:pc2_mask(c,0xc8,0x1dbe8,0x1dbee);return true;
    case 0x1dbe8:return am_call(c,0x4c0ea,0x1dbee);
    // ---- 1ddd0: BSR.W 1dbd8 / BRA.W 1ddfc / BSR.W 1d582 / BSET.B #2,a7(A6) / BSR.W 1d1d0.
    case 0x1ddd0:return am_call(c,0x1dbd8,0x1ddd4);
    case 0x1ddd4:r.pc=0x1ddfc;return true;
    case 0x1ddfc:return am_call(c,0x1d582,0x1de00);
    case 0x1de00:if(!pc2_bit(c,0xa7,2,1,old))return false;r.pc=0x1de06;return true;
    case 0x1de06:return am_call(c,0x1d1d0,0x1de0a);
    // MOVE.B #ff,82(A6); MOVE.B #ff,81(A6); MOVE.W #8834,68(A6); MOVE.W #8834,1e(A6); JSR 1aa3a.l.
    case 0x1de0a:
        if(!pc2_put(c,r.a[6],0x82,1,0xff) || !pc2_put(c,r.a[6],0x81,1,0xff) || !pc2_put(c,r.a[6],0x68,2,0x8834) || !pc2_put(c,r.a[6],0x1e,2,0x8834))return false;
        return am_call(c,0x1aa3a,0x1de28);
    case 0x1de28:r.pc=(r.d[0]&8U)!=0U?0x1e21c:0x1de30;return true;                                      // BTST.B #3,D0; BNE.W 1e21c (C10).
    case 0x1de30:r.pc=(r.d[0]&0x40U)!=0U?0x1e8de:0x1de38;return true;                                   // BTST.B #6,D0; BNE.W 1e8de (C10).
    case 0x1de38:r.pc=0x1ed78;return true;                                                                 // BRA.W 1ed78.
    // ---- 1dfe6: BTST.B #5,a7(A6); BNE.W 1dff6 / ANDI.B #fe,CCR; RTS (returns C Clear).
    case 0x1dfe6:if(!pc2_bit(c,0xa7,5,0,old))return false;r.pc=old?0x1dff6:0x1dff0;return true;
    case 0x1dff0:case 0x1ed54:r.carry=AnimationCarryClear;return am_return(c);
    // ADDQ.B #1,a2(A6); SCS.B D0; OR.B D0,a2(A6) (ff stays ff); JSR 49a58.l.
    case 0x1dff6: {
        if(!pc2_get(c,r.a[6],0xa2,1,value))return false;const bool carry=value==0xffU;
        if(!pc2_put(c,r.a[6],0xa2,1,value+1U))return false;am_byte(r.d[0],carry?0xffU:0U);
        if(!pc2_get(c,r.a[6],0xa2,1,value) || !pc2_put(c,r.a[6],0xa2,1,value|(r.d[0]&0xffU)))return false;return am_call(c,0x49a58,0x1e006);
    }
    // MOVEQ #0,D1; MOVE.B a2(A6),D1; SUBI.W #1e,D1; BCC.W 1e016 (no borrow) / MOVEQ #0,D1.
    case 0x1e006:
        r.d[1]=0;if(!pc2_get(c,r.a[6],0xa2,1,value))return false;am_byte(r.d[1],value);
        r.pc=(r.d[1]&0xffffU)>=0x1eU?0x1e016:0x1e014;am_word(r.d[1],r.d[1]-0x1eU);return true;
    case 0x1e014:r.d[1]=0;r.pc=0x1e016;return true;
    // SUB.W D1,D0; RTS: C := the borrow (unsigned D0.W < D1.W), returned to the caller.
    case 0x1e016:
        r.carry=(r.d[0]&0xffffU)<(r.d[1]&0xffffU)?AnimationCarrySet:AnimationCarryClear;am_word(r.d[0],r.d[0]-r.d[1]);return am_return(c);
    // ---- 1ed34 (BSR from 1ee00 / 1efb0): BTST.B #4,D0; BNE.W 1ed3e / RTS.  1ed3e: BTST.B #0,a7(A6); BNE.W 1ed4a / RTS.  BTST changes only Z: the
    // incoming C goes back to the caller (dispatcher carry list: 1ed34 1ed3c 1ed3e 1ed48).
    case 0x1ed34:r.pc=(r.d[0]&0x10U)!=0U?0x1ed3e:0x1ed3c;return true;
    case 0x1ed3e:if(!pc2_bit(c,0xa7,0,0,old))return false;r.pc=old?0x1ed4a:0x1ed48;return true;
    case 0x1ed4a:return pc2_byte_is(c,0x6e,5,0x1ed5a,0x1ed54);                                           // CMPI.B #5,6e(A6); BEQ.W 1ed5a.
    // LEA 1ed70(PC),A0; BTST.B #1,a7(A6); BEQ.W 1ed6a / ADDQ.W #4,A0 / MOVEA.L (A0),A0; BRA.W 1cb08 (fixed ROM LONG 1ed70 / 1ed74).
    case 0x1ed5a:r.a[0]=0x1ed70;if(!pc2_bit(c,0xa7,1,0,old))return false;r.pc=old?0x1ed68:0x1ed6a;return true;
    case 0x1ed68:r.a[0]+=4U;r.pc=0x1ed6a;return true;
    case 0x1ed6a:if(!am_read(c,r.a[0],4,r.a[0]))return false;r.pc=0x1cb08;return true;
    // ---- 1ed78: LEA 1b230(PC),A0; BSR.W 1cb08 / BCC.W 1ed8e (C of 1cb08) / CMPI.B #78,92(A6); BCC.W 1eee0 (unsigned BYTE >= 78).
    case 0x1ed78:r.a[0]=0x1b230;return am_call(c,0x1cb08,0x1ed80);
    case 0x1ed80:return pc2_carry(c,0x1ed8e,0x1ed84);
    case 0x1ed84:if(!pc2_get(c,r.a[6],0x92,1,value))return false;r.pc=value>=0x78U?0x1eee0:0x1ed8e;return true;
    case 0x1ed8e:r.a[0]=0x1b6c4;return am_call(c,0x1cab6,0x1ed96);                                        // LEA 1b6c4(PC),A0; BSR.W 1cab6.
    // CLR.B a2(A6); CLR.L 64(A6); MOVE.B #1,a9(A6); MOVE.B #1,9c(A6); MOVE.L #1edb0,(A6).
    case 0x1ed96:
        if(!pc2_put(c,r.a[6],0xa2,1,0) || !pc2_put(c,r.a[6],0x64,4,0) || !pc2_put(c,r.a[6],0xa9,1,1) || !pc2_put(c,r.a[6],0x9c,1,1))return false;
        return pc2_install(c,0x1edb0);
    case 0x1edb0:case 0x1f224:case 0x1f7da:return am_call(c,0x1cd98,r.pc+4U);                            // BSR.W 1cd98 (installed callbacks).
    case 0x1edb4:if(!pc2_bit(c,0x15,7,0,old))return false;r.pc=old?0x1edbe:0x1fae8;return true;          // BTST.B #7,15(A6); BEQ.W 1fae8.
    case 0x1edbe:r.pc=(r.d[0]&0x20U)==0U?0x1ede6:0x1edc6;return true;                                   // BTST.B #5,D0; BEQ.W 1ede6.
    case 0x1edc6:return pc2_byte_is(c,0x9e,0,0x1edd0,0x1edd8);                                           // CMPI.B #0,9e(A6); BNE.W 1edd8.
    case 0x1edd0:r.pc=(r.d[0]&2U)!=0U?0x1f7a4:0x1edd8;return true;                                      // BTST.B #1,D0; BNE.W 1f7a4.
    case 0x1edd8:pc2_mask(c,0xc,0x1ede2,0x1fa68);return true;                                            // MOVE.W #c,D1; AND.W D0,D1; BNE.W 1fa68 (C8).
    case 0x1ede2:r.pc=0x1fa3c;return true;                                                                 // BRA.W 1fa3c.
    case 0x1ede6:r.pc=(r.d[0]&2U)!=0U?0x1f2a4:0x1edee;return true;                                      // BTST.B #1,D0; BNE.W 1f2a4 (C7).
    case 0x1edee:r.pc=(r.d[0]&0x80U)!=0U?0x1f1d8:0x1edf6;return true;                                   // BTST.B #7,D0; BNE.W 1f1d8.
    // MOVE.W #c,D1; AND.W D0,D1; BNE.W 1eeea (C4); 1ee00 (C3) is the fall-through.  AND leaves C Clear (read by the C3 BSR 1ee00 -> 1ed34 -> RTS).
    case 0x1edf6:pc2_mask(c,0xc,0x1ee00,0x1eeea);r.carry=AnimationCarryClear;return true;
    case 0x1eee0:if(!pc2_bit(c,0xa7,5,2,old))return false;r.pc=0x1ebbe;return true;                    // BCLR.B #5,a7(A6); BRA.W 1ebbe (C6).
    // ---- 1f1d8: LEA 1bcc2(PC),A0; BTST.B #2,10f001.l; BNE.W 1f1f8 / MOVEA.L 8c(A6),A4; TST.B 7(A4); BNE.W 1f1f8 / LEA 1bcc4(PC),A0 / BSR.W 1cb38.
    case 0x1f1d8:r.a[0]=0x1bcc2;if(!am_read(c,0x10f001,1,value))return false;r.pc=(value&4U)!=0U?0x1f1f8:0x1f1e8;return true;
    case 0x1f1e8:if(!pc2_get(c,r.a[6],0x8c,4,r.a[4]) || !pc2_get(c,r.a[4],7,1,value))return false;r.pc=value!=0U?0x1f1f8:0x1f1f4;return true;
    case 0x1f1f4:r.a[0]=0x1bcc4;r.pc=0x1f1f8;return true;
    case 0x1f1f8:return am_call(c,0x1cb38,0x1f1fc);                                                       // BSR.W 1cb38 (C5).
    // CLR.B 7e(A6); MOVE.B #1,a9(A6); the slot 84 block; MOVE.L #1f224,(A6).
    case 0x1f1fc:
        if(!pc2_put(c,r.a[6],0x7e,1,0) || !pc2_put(c,r.a[6],0xa9,1,1) || !pc2_slot84(c))return false;return pc2_install(c,0x1f224);
    case 0x1f228:if(!pc2_get(c,r.a[6],0x7e,1,value))return false;r.pc=value==0U?0x1f23a:0x1f230;return true;  // TST.B 7e(A6); BEQ.W 1f23a.
    case 0x1f230:pc2_mask(c,0x1c,0x1f23a,0x1ed78);return true;                                           // MOVE.W #1c,D1; AND.W D0,D1; BNE.W 1ed78.
    case 0x1f23a:if(!pc2_bit(c,0x15,7,0,old))return false;r.pc=old?0x1f278:0x1f244;return true;          // BTST.B #7,15(A6); BNE.W 1f278.
    // MOVEQ #0,D2; MOVE.L #ffea0000,D3; SUB.L 36(A6),D2; BMI.W 1f25a / ADDI.L #1f,D2.
    case 0x1f244:
        r.d[2]=0;r.d[3]=0xffea0000U;if(!pc2_get(c,r.a[6],0x36,4,value))return false;r.d[2]=0U-value;
        r.pc=(r.d[2]&0x80000000U)!=0U?0x1f25a:0x1f254;return true;
    case 0x1f254:r.d[2]+=0x1fU;r.pc=0x1f25a;return true;
    // ASR.L #5,D2; ADD.L D2,36(A6); SUB.L 3a(A6),D3; BMI.W 1f26e / ADDI.L #1f,D3.
    case 0x1f25a:
        r.d[2]=pc2_asr5(r.d[2]);if(!pc2_add_long(c,0x36,r.d[2]) || !pc2_get(c,r.a[6],0x3a,4,value))return false;r.d[3]-=value;
        r.pc=(r.d[3]&0x80000000U)!=0U?0x1f26e:0x1f268;return true;
    case 0x1f268:r.d[3]+=0x1fU;r.pc=0x1f26e;return true;
    case 0x1f26e:r.d[3]=pc2_asr5(r.d[3]);if(!pc2_add_long(c,0x3a,r.d[3]))return false;r.pc=0x1f280;return true;  // ASR.L #5,D3; ADD.L D3,3a(A6); BRA.
    case 0x1f278:if(!pc2_put(c,r.a[6],0x36,4,0) || !pc2_put(c,r.a[6],0x3a,4,0))return false;r.pc=0x1f280;return true;  // CLR.L 36 / 3a.
    case 0x1f280:return am_call(c,0x4be82,0x1f286);                                         // JSR 4be82.l.
    case 0x1f286:case 0x1f7f2:case 0x1fab0:return pc2_shape(c,r.pc+0xaU);                               // MOVE.W 1e(A6),D0; JSR ce02.l.
    case 0x1f290:case 0x1f7fc:case 0x1faba:return am_call(c,0x49fc6,r.pc+6U);                           // JSR 49fc6.l.
    case 0x1f296:return pc2_carry(c,0x1f2a0,0x1f29a);                                                     // BCC.W 1f2a0 (C of 49fc6).
    case 0x1f29a:if(!pc2_put(c,r.a[6],0,4,0x1ed78))return false;r.pc=0x1f2a0;return true;              // MOVE.L #1ed78,(A6) (written only).
    case 0x1f2a0:case 0x1f80c:case 0x1face:r.pc=0x201a2;return true;                                     // BRA.W 201a2 (C3).
    // ---- 1f7a4: LEA 1b34a(PC),A0; BSR.W 1cab6 / the slot 84 block; MOVE.B #2,a9(A6); MOVE.B #2,aa(A6); CLR.L 64(A6); MOVE.L #1f7da,(A6).
    case 0x1f7a4:r.a[0]=0x1b34a;return am_call(c,0x1cab6,0x1f7ac);
    case 0x1f7ac:
        if(!pc2_slot84(c) || !pc2_put(c,r.a[6],0xa9,1,2) || !pc2_put(c,r.a[6],0xaa,1,2) || !pc2_put(c,r.a[6],0x64,4,0))return false;
        return pc2_install(c,0x1f7da);
    case 0x1f7de:return am_call(c,0x1cec2,0x1f7e2);                                                       // BSR.W 1cec2 (C4).
    case 0x1f7e2:if(!pc2_bit(c,0x15,7,0,old))return false;r.pc=old?0x1f7ec:0x1fad2;return true;          // BTST.B #7,15(A6); BEQ.W 1fad2.
    case 0x1f7ec:case 0x1faaa:return am_call(c,0x4bfc0,r.pc+6U);                                         // JSR 4bfc0.l.
    case 0x1f802:return pc2_carry(c,0x1f80c,0x1f806);                                                     // BCC.W 1f80c (C of 49fc6).
    case 0x1f806:if(!pc2_put(c,r.a[6],0,4,0x1f810))return false;r.pc=0x1f80c;return true;              // MOVE.L #1f810,(A6) (written only).
    // ---- 1fa3c: LEA 1b716(PC),A0; BSR.W 1cb08 / BCS.W 1fa90 / CLR.L 36(A6); BSR.W 1cfde (C8) / LEA 1b72e(PC),A0; BSR.W 1cab6 /
    // MOVE.B #3,9c(A6); MOVE.B #1,a9(A6); BRA.W 1fafc (C8).
    case 0x1fa3c:r.a[0]=0x1b716;return am_call(c,0x1cb08,0x1fa44);
    case 0x1fa44:return pc2_carry(c,0x1fa48,0x1fa90);
    case 0x1fa48:if(!pc2_put(c,r.a[6],0x36,4,0))return false;return am_call(c,0x1cfde,0x1fa50);
    case 0x1fa50:r.a[0]=0x1b72e;return am_call(c,0x1cab6,0x1fa58);
    case 0x1fa58:if(!pc2_put(c,r.a[6],0x9c,1,3) || !pc2_put(c,r.a[6],0xa9,1,1))return false;r.pc=0x1fafc;return true;
    // 1fa90: BSR.W 1cab6 / MOVE.B #1,a9(A6); MOVE.B #3,9c(A6) / CLR.L 64(A6); MOVE.L #1faaa,(A6).
    case 0x1fa90:return am_call(c,0x1cab6,0x1fa94);
    case 0x1fa94:if(!pc2_put(c,r.a[6],0xa9,1,1) || !pc2_put(c,r.a[6],0x9c,1,3))return false;r.pc=0x1faa0;return true;
    case 0x1faa0:if(!pc2_put(c,r.a[6],0x64,4,0))return false;return pc2_install(c,0x1faaa);
    case 0x1fac0:return pc2_carry(c,0x1face,0x1fac4);                                                     // BCC.W 1face (C of 49fc6).
    case 0x1fac4:return am_call(c,0x1cfde,0x1fac8);                                                       // BSR.W 1cfde (C8).
    case 0x1fac8:if(!pc2_put(c,r.a[6],0,4,0x1fae8))return false;r.pc=0x1face;return true;              // MOVE.L #1fae8,(A6) (written only).
    // MOVE.L #fff00000,3a(A6); JSR 4be82.l / MOVE.L #0,3a(A6) / MOVE.B #3,9c(A6); MOVE.B #1,a9(A6); LEA 1b72e(PC),A0; BSR.W 1cab6.
    case 0x1fad2:if(!pc2_put(c,r.a[6],0x3a,4,0xfff00000U))return false;return am_call(c,0x4be82,0x1fae0);
    case 0x1fae0:if(!pc2_put(c,r.a[6],0x3a,4,0))return false;r.pc=0x1fae8;return true;
    case 0x1fae8:if(!pc2_put(c,r.a[6],0x9c,1,3) || !pc2_put(c,r.a[6],0xa9,1,1))return false;r.a[0]=0x1b72e;return am_call(c,0x1cab6,0x1fafc);
    default:return am_error(c,"unsupported animation player c2 PC");
    }
}
}
