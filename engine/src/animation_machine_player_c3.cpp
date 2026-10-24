#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc3_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc3_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR / BCHG #bit,d16(A6) (a memory operand: BYTE, bit = the immediate modulo 8). op 0 tests, 1 sets, 2 clears, 3 changes; old is the
// bit before (the Z of the instruction is old = 0).
bool pc3_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!pc3_get(c,c.s.a[6],displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return pc3_put(c,c.s.a[6],displacement,1,op==1U?(value|mask):(op==2U?(value&~mask):(value^mask)));
}
// TST.B / CMPI.B d16(base) against k; BNE.W / BEQ.W: equal_pc when BYTE = k, else other_pc.
bool pc3_byte_is(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc3_get(c,base,displacement,1,value))return false;
    c.s.pc=value==k?equal_pc:other_pc;return true;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc3_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c3 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ANDI.B #fe,CCR / ORI.B #1,CCR; RTS: the C returned to the caller.
bool pc3_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// MOVE.L #v,(A6) followed by v: the next PC is v (installed value entered at once); write_only: MOVE.L #v,(A6) then next_pc.
bool pc3_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc3_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #v,84(A6) (the second callback slot of the player node) followed by next_pc.
bool pc3_slot84(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc3_put(c,c.s.a[6],0x84,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.W #mask,D1; AND.W D0,D1; BNE.W set_pc (fall through to clear_pc).  D1 bits 16..31 kept.
void pc3_mask(AnimationMachineContext& c,std::uint32_t mask,std::uint32_t clear_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;am_word(r.d[1],mask);am_word(r.d[1],r.d[1]&r.d[0]);
    r.pc=(r.d[1]&0xffffU)!=0U?set_pc:clear_pc;
}
// MOVE.W 1e(A6),D0; JSR ce02.l (D0 bits 16..31 kept).
bool pc3_shape(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc3_get(c,c.s.a[6],0x1e,2,value))return false;am_word(c.s.d[0],value);return am_call(c,0xce02,return_pc);
}
// MOVE.W 78(A6),D0 (D0 bits 16..31 kept); JSR target.l.
bool pc3_index_call(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc3_get(c,c.s.a[6],0x78,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// ADD.W / SUB.W Dn,d16(A6) (WORD read, modulo 2^16, WORD write).
bool pc3_add_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t addend) {
    std::uint32_t value=0;if(!pc3_get(c,c.s.a[6],displacement,2,value))return false;return pc3_put(c,c.s.a[6],displacement,2,value+addend);
}
// The computed-jump targets (contract decision 2), transcribed from the ROM writers:
//   201a6 JSR (A4) (A4 = LONG 84(A6)): the 34 immediate values written to LONG 84(A6) by the player code 1b000..24000 (MOVE.L #v,84(A6));
//   21620 JMP (A1): the handler LONGs of the (handler LONG, key WORD) list 21622 that 215e6 matched;  221de JMP (A1): the handler of the list 216c8.
// Every other target is the checked error "unsupported animation player c3 jump target"; a listed target that is not routed yet fails at the next
// dispatch ("unsupported animation machine PC", a later unit).
const std::uint32_t PC3_SLOT84[34]={0x21602,0x21610,0x21664,0x2173c,0x21770,0x217b2,0x217e0,0x217f6,0x218b2,0x2190e,0x21960,0x2199a,0x219d8,
    0x21a76,0x21acc,0x21c66,0x21cd8,0x21d2a,0x21d92,0x21e04,0x21e6a,0x21eb0,0x21f02,0x21f70,0x21fc6,0x21ffc,0x2210c,0x22128,0x221d2,0x22240,
    0x2228e,0x22360,0x2241c,0x22452};
const std::uint32_t PC3_LIST_21622[10]={0x21c22,0x21d60,0x21e48,0x21e3a,0x21720,0x217e0,0x2178e,0x2175a,0x21950,0x219c8};
bool pc3_listed(const std::uint32_t* list,unsigned int count,std::uint32_t target) {
    for(unsigned int i=0;i<count;++i)if(list[i]==target)return true;
    return false;
}
}
// Player C3 (230 block starts, contract docs/analysis/animation-machine-player-c3-contract.md; area C plan unit C3): the second half of the player
// object's IO-run frame (+190): the state 1ee00 (the fall-through of the C2 block 1edf6; 1ed22 record test) and its turn state 1f126 / 1f166, the
// common state tail 201a2 (the second callback slot JSR (A4) 201a6 = LONG 84(A6), 1a9e8, 4d0a4 / 4de9c, the BRA.W table jump 2031c, 20516 lights,
// 20626 / 206a4), the slot-84 states 21602 / 21610 (handler list lookup 215e6 and JMP (A1) 21620), 21c22 / 21c66 (21baa 21bc6 21be6 21c1c), 21f30 /
// 21f40 / 21f58 / 21f70, 21ffc / 221ca / 221d2 (JMP (A1) 221de), the move helper 2156a (MOVEM.W save / restore around 49fca), the 28ae child 361e4,
// the C helpers 48350 (the Set side of the C1 block 48346) 48384 484ca 4d0a4 4de9c, the record helper e8b5a and the straight-line continuations 1cde0 /
// 1cdf0 / 1cdfa (after C2 1cdd8 / 1cdea) and 202a0 (after 20290) that the IO runs execute inside the same TB (contract decision 10).  C: the 22 consumers read a known C or
// fail; 1ee00 (BSR) and the RTS 1ed32 215f6 21c1a keep the incoming C (dispatcher carry list); 215ec (CMPA) 21bc0 21be0 21bfa 21c1c 48392 4d100
// 4debc 4ded4 leave Clear, 215fc 21bda 48362 4deca Set, 1ed30 21bb2 21c06 the compare borrow.  Z: 1ee56 BNE recomputes the Z of the 1cb08 MOVE.W and,
// for a WORD that is not 0, of the C5 1cb1a TST.L from memory (contract decision 3, widened by player C5).
bool animation_player_c3_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool old=false;
    switch(r.pc) {
    // ---- 1cb40 (BSR from 21f30 and later units): LEA 94(A6),A1 (falls into 1cb44, unit C5).
    case 0x1cb40:r.a[1]=am_index(r.a[6],0x94);r.pc=0x1cb44;return true;
    // ---- 1cde0 / 1cdf0 / 1cdfa (the straight-line continuations of the C2 blocks 1cdd8 / 1cdea, contract decision 10): BSET.B #4,61(A6); BRA.W 1cdf0 /
    // CMPI.B #2,1(A4); BCS.W 1cdfe (unsigned BYTE < 2) / ANDI.W #ffbf,D0 (falls into the C2 block 1cdfe).
    case 0x1cde0:if(!pc3_bit(c,0x61,4,1,old))return false;r.pc=0x1cdf0;return true;
    case 0x1cdf0:if(!pc3_get(c,r.a[4],1,1,value))return false;r.pc=value<2U?0x1cdfe:0x1cdfa;return true;
    case 0x1cdfa:am_word(r.d[0],r.d[0]&0xffbfU);r.pc=0x1cdfe;return true;
    // ---- 1ed22: BSR.W 1cb08 / BCC.W 1ed32 (C of 1cb08) / JSR 49a58.l / CMP.W D1,D0 (C := unsigned D0.W < D1.W) / RTS (keeps the C).
    case 0x1ed22:return am_call(c,0x1cb08,0x1ed26);
    case 0x1ed26:return pc3_carry(c,0x1ed32,0x1ed2a);
    case 0x1ed2a:return am_call(c,0x49a58,0x1ed30);
    case 0x1ed30:r.carry=(r.d[0]&0xffffU)<(r.d[1]&0xffffU)?AnimationCarrySet:AnimationCarryClear;r.pc=0x1ed32;return true;
    // ---- 1ee00 (fall-through of C2 1edf6, C Clear): BSR.W 1ed34 (the BSR keeps the C; 1ed34 returns it) / BCS.W 1f126.
    case 0x1ee00:return am_call(c,0x1ed34,0x1ee04);
    case 0x1ee04:return pc3_carry(c,0x1ee08,0x1f126);
    case 0x1ee08:if(!pc3_bit(c,0xa7,5,0,old))return false;r.pc=old?0x1ee12:0x1eec6;return true;           // BTST.B #5,a7(A6); BEQ.W 1eec6.
    case 0x1ee12:return am_call(c,0x1dfe6,0x1ee16);                                                       // BSR.W 1dfe6.
    case 0x1ee16:return pc3_carry(c,0x1ee36,0x1ee1a);                                                     // BCC.W 1ee36.
    case 0x1ee1a:am_word(r.d[1],0x4000);r.a[0]=0x1b55e;return am_call(c,0x1ed22,0x1ee26);                // MOVE.W #4000,D1; LEA 1b55e(PC),A0; BSR.W 1ed22.
    case 0x1ee26:case 0x1ee86:case 0x1eea4:case 0x1eec2:return pc3_carry(c,r.pc+4U,0x1eee0);           // BCS.W 1eee0 (C2).
    case 0x1ee2a:r.a[0]=0x1b542;return am_call(c,0x1cb08,0x1ee32);                                        // LEA 1b542(PC),A0; BSR.W 1cb08.
    case 0x1ee32:return pc3_carry(c,0x1ee36,0x1eee0);                                                     // BCS.W 1eee0.
    case 0x1ee36:return am_call(c,0x484e2,0x1ee3c);                                                       // JSR 484e2.l.
    case 0x1ee3c:return pc3_carry(c,0x1ee5a,0x1ee40);                                                     // BCC.W 1ee5a.
    case 0x1ee40:return am_call(c,0x484ca,0x1ee46);                                                       // JSR 484ca.l.
    // AND.B 60(A6),D0; BEQ.W 1ee5a (D0 bits 8..31 kept).
    case 0x1ee46:if(!pc3_get(c,r.a[6],0x60,1,value))return false;am_byte(r.d[0],r.d[0]&value);r.pc=(r.d[0]&0xffU)==0U?0x1ee5a:0x1ee4e;return true;
    case 0x1ee4e:r.a[0]=0x1b5f2;return am_call(c,0x1cb08,0x1ee56);                                        // LEA 1b5f2(PC),A0; BSR.W 1cb08.
    // BNE.W 1eee0 on the Z that 1cb08 leaves at its return (contract decision 3, widened by player C5 decision 3): A0, BYTE 9f and LONG 22(A6) are
    // unchanged by 1cb08 / 1cb18 and by the C5 path 1cb1a / 1cb30 / 1cb32, so the sources are read again.  The WORD W = (A0 + sext(2 x BYTE 9f)) (the
    // Z of the 1cb08 MOVE.W): 0 is the return 1cb18 (Z = 1) -> 1ee5a.  W not 0 is the C5 path 1cb1a, whose Z is the TST.L of LONG (LONG 22(A6) +
    // sext(4 x WORD (A0 + sext(W)))): 0 returns through 1cb30 (Z = 1) -> 1ee5a, else through 1cb32 (ORI keeps Z = 0) -> 1eee0.  A source outside fixed
    // ROM / work RAM (a second device read) is the checked flag-source error.  (Before C5: W not 0 was that error too.)
    case 0x1ee56: {
        if(!pc3_get(c,r.a[6],0x9f,1,value))return false;
        std::uint32_t at=am_index(r.a[0],(value+value)&0xffffU);
        if((at&0xffffffU)>=0x200000U)return am_error(c,"unsupported animation player c3 flag source");
        if(!am_read(c,at,2,value))return false;
        if(value==0U){r.pc=0x1ee5a;return true;}
        at=am_index(r.a[0],value);
        if((at&0xffffffU)>=0x200000U)return am_error(c,"unsupported animation player c3 flag source");
        if(!am_read(c,at,2,value))return false;
        std::uint32_t base=0;if(!pc3_get(c,r.a[6],0x22,4,base))return false;
        at=am_index(base,(value<<2)&0xffffU);
        if((at&0xffffffU)>=0x200000U)return am_error(c,"unsupported animation player c3 flag source");
        if(!am_read(c,at,4,value))return false;
        r.pc=value==0U?0x1ee5a:0x1eee0;return true;
    }
    case 0x1ee5a:return pc3_byte_is(c,r.a[6],0x6e,2,0x1ee64,0x1ee8a);                                    // CMPI.B #2,6e(A6); BNE.W 1ee8a.
    // MOVE.W #10,D0; BTST.B #0,15(A6); BEQ.W 1ee74 / NEG.W D0.
    case 0x1ee64:am_word(r.d[0],0x10);if(!pc3_bit(c,0x15,0,0,old))return false;r.pc=old?0x1ee72:0x1ee74;return true;
    case 0x1ee72:am_word(r.d[0],0U-r.d[0]);r.pc=0x1ee74;return true;
    case 0x1ee74:return am_call(c,0x4c1de,0x1ee7a);                                                       // JSR 4c1de.l.
    case 0x1ee7a:return pc3_carry(c,0x1ee7e,0x1ee8a);                                                     // BCS.W 1ee8a.
    case 0x1ee7e:r.a[0]=0x1b5b6;return am_call(c,0x1cb08,0x1ee86);                                        // LEA 1b5b6(PC),A0; BSR.W 1cb08.
    case 0x1ee8a:case 0x1eea8:case 0x36256:case 0x202e6:return am_call(c,0x1aa3a,r.pc+6U);               // JSR 1aa3a.l.
    case 0x1ee90:r.pc=(r.d[0]&1U)==0U?0x1eea8:0x1ee98;return true;                                       // BTST.B #0,D0; BEQ.W 1eea8.
    case 0x1ee98:am_word(r.d[1],0x100);r.a[0]=0x1b57c;return am_call(c,0x1ed22,0x1eea4);                 // MOVE.W #100,D1; LEA 1b57c(PC),A0; BSR.W 1ed22.
    case 0x1eeae:r.pc=(r.d[0]&2U)==0U?0x1eec6:0x1eeb6;return true;                                       // BTST.B #1,D0; BEQ.W 1eec6.
    case 0x1eeb6:am_word(r.d[1],0x100);r.a[0]=0x1b598;return am_call(c,0x1ed22,0x1eec2);                 // MOVE.W #100,D1; LEA 1b598(PC),A0; BSR.W 1ed22.
    case 0x1eec6:case 0x1f1b4:return am_call(c,0x4bfc0,r.pc+6U);                                         // JSR 4bfc0.l.
    case 0x1eecc:case 0x1f1ba:return pc3_shape(c,r.pc+0xaU);                                             // MOVE.W 1e(A6),D0; JSR ce02.l.
    case 0x1eed6:case 0x1f1c4:return am_call(c,0x49fc6,r.pc+6U);                                         // JSR 49fc6.l.
    case 0x1eedc:case 0x1f1d4:r.pc=0x201a2;return true;                                                  // BRA.W 201a2.
    // ---- 1f126 (BCS of 1ee04 / 1efb4): BSR.W 1cab6 / BCHG.B #1,a7(A6); MOVE.B #0,aa(A6); CLR.B 9d(A6); CLR.B 7e(A6); CLR.L 64(A6);
    // MOVE.B #1,a9(A6); MOVE.L #21602,84(A6); MOVE.B #0,9c(A6); MOVE.B #1,aa(A6); CLR.W 7a(A6); MOVE.L #1f166,(A6) (entered at once).
    case 0x1f126:return am_call(c,0x1cab6,0x1f12a);
    case 0x1f12a:
        if(!pc3_bit(c,0xa7,1,3,old) || !pc3_put(c,r.a[6],0xaa,1,0) || !pc3_put(c,r.a[6],0x9d,1,0) || !pc3_put(c,r.a[6],0x7e,1,0) ||
           !pc3_put(c,r.a[6],0x64,4,0) || !pc3_put(c,r.a[6],0xa9,1,1) || !pc3_put(c,r.a[6],0x84,4,0x21602) || !pc3_put(c,r.a[6],0x9c,1,0) ||
           !pc3_put(c,r.a[6],0xaa,1,1) || !pc3_put(c,r.a[6],0x7a,2,0))return false;
        return pc3_install(c,0x1f166,0x1f166);
    case 0x1f166:return am_call(c,0x1cd98,0x1f16a);                                                       // BSR.W 1cd98.
    case 0x1f16a:if(!pc3_bit(c,0x15,7,0,old))return false;r.pc=old?0x1f174:0x1fae8;return true;          // BTST.B #7,15(A6); BEQ.W 1fae8.
    case 0x1f174:r.pc=(r.d[0]&0x20U)==0U?0x1f19c:0x1f17c;return true;                                   // BTST.B #5,D0; BEQ.W 1f19c.
    case 0x1f17c:return pc3_byte_is(c,r.a[6],0x9e,0,0x1f186,0x1f18e);                                    // CMPI.B #0,9e(A6); BNE.W 1f18e.
    case 0x1f186:r.pc=(r.d[0]&2U)!=0U?0x1f7a4:0x1f18e;return true;                                      // BTST.B #1,D0; BNE.W 1f7a4.
    case 0x1f18e:pc3_mask(c,0xc,0x1f198,0x1fa68);return true;                                            // MOVE.W #c,D1; AND.W D0,D1; BNE.W 1fa68 (C8).
    case 0x1f198:r.pc=0x1fa3c;return true;                                                                 // BRA.W 1fa3c.
    case 0x1f19c:return pc3_byte_is(c,r.a[6],0x7e,0,0x1f1b4,0x1f1a4);                                    // TST.B 7e(A6); BEQ.W 1f1b4.
    // MOVE.B #1,aa(A6); MOVE.W #5e,D1; AND.W D0,D1; BNE.W 1ed78.
    case 0x1f1a4:if(!pc3_put(c,r.a[6],0xaa,1,1))return false;pc3_mask(c,0x5e,0x1f1b4,0x1ed78);return true;
    case 0x1f1ca:return pc3_carry(c,0x1f1d4,0x1f1ce);                                                     // BCC.W 1f1d4 (C of 49fc6).
    case 0x1f1ce:return pc3_install(c,0x1ed78,0x1f1d4);                                                   // MOVE.L #1ed78,(A6) (written only).
    // ---- 201a2 (the common tail; BRA from the states): MOVEA.L 84(A6),A4; JSR (A4) (contract decision 2: a listed slot-84 value, else checked).
    case 0x201a2:
        if(!pc3_get(c,r.a[6],0x84,4,r.a[4]))return false;
        if(!pc3_listed(PC3_SLOT84,34U,r.a[4]))return am_error(c,"unsupported animation player c3 jump target");
        return am_call(c,r.a[4],0x201a8);
    case 0x201a8:return am_call(c,0x1a9e8,0x201ae);                                                       // JSR 1a9e8.l.
    case 0x201ae:return pc3_index_call(c,0x4d0a4,0x201b8);                                                // MOVE.W 78(A6),D0; JSR 4d0a4.l.
    case 0x201b8:return pc3_carry(c,0x201d0,0x201bc);                                                     // BCC.W 201d0 (201bc is C8).
    case 0x201d0:if(!pc3_bit(c,0xa7,7,2,old))return false;r.pc=old?0x1fd50:0x201da;return true;          // BCLR.B #7,a7(A6); BNE.W 1fd50 (C11).
    case 0x201da:return pc3_index_call(c,0x4de9c,0x201e4);                                                // MOVE.W 78(A6),D0; JSR 4de9c.l.
    case 0x201e4:return pc3_carry(c,0x201fc,0x201e8);                                                     // BCC.W 201fc.
    case 0x201e8:if(!pc3_bit(c,0xa7,6,1,old))return false;r.pc=old?0x201f8:0x201f2;return true;          // BSET.B #6,a7(A6); BNE.W 201f8.
    case 0x201f2:return pc3_install(c,0x1fc38,0x201f8);                                                   // MOVE.L #1fc38,(A6) (written only).
    case 0x201f8:r.pc=0x20206;return true;                                                                 // BRA.W 20206.
    case 0x201fc:if(!pc3_bit(c,0xa7,6,2,old))return false;r.pc=old?0x1fc96:0x20206;return true;          // BCLR.B #6,a7(A6); BNE.W 1fc96 (C11).
    case 0x20206:return pc3_byte_is(c,r.a[6],0x5e,0x18,0x20210,0x20216);                                 // CMPI.B #18,5e(A6); BNE.W 20216.
    case 0x20210:if(!pc3_bit(c,0xa8,1,1,old))return false;r.pc=0x20216;return true;                    // BSET.B #1,a8(A6).
    case 0x20216:return am_call(c,0x4b54e,0x2021c);                                                       // JSR 4b54e.l.
    case 0x2021c:if(!pc3_bit(c,0x61,6,2,old))return false;r.pc=old?0x20226:0x2022a;return true;          // BCLR.B #6,61(A6); BEQ.W 2022a.
    case 0x20226:if(!pc3_put(c,r.a[6],0x5e,1,0))return false;r.pc=0x2022a;return true;                 // CLR.B 5e(A6).
    // MOVE.B 19(A6),14(A6); TST.W 90(A6); BEQ.W 20268 (C5).
    case 0x2022a:
        if(!pc3_get(c,r.a[6],0x19,1,value) || !pc3_put(c,r.a[6],0x14,1,value) || !pc3_get(c,r.a[6],0x90,2,value))return false;
        r.pc=value==0U?0x20268:0x20238;return true;
    // SUBQ.W #1,90(A6); BNE.W 2024a (20240 is C5).
    case 0x20238:if(!pc3_get(c,r.a[6],0x90,2,value) || !pc3_put(c,r.a[6],0x90,2,value-1U))return false;r.pc=((value-1U)&0xffffU)!=0U?0x2024a:0x20240;return true;
    case 0x2024a:if(!pc3_bit(c,0xa7,2,0,old))return false;r.pc=old?0x20254:0x20264;return true;          // BTST.B #2,a7(A6); BEQ.W 20264.
    case 0x20254:if(!pc3_bit(c,0xa8,6,3,old))return false;r.pc=old?0x2025e:0x20264;return true;          // BCHG.B #6,a8(A6); BEQ.W 20264.
    case 0x2025e:if(!pc3_get(c,r.a[6],0x1a,1,value) || !pc3_put(c,r.a[6],0x14,1,value))return false;r.pc=0x20264;return true;  // MOVE.B 1a,14.
    case 0x20264:r.pc=0x20290;return true;                                                                 // BRA.W 20290.
    // BSET.B #6,61(A6); BCLR.B #7,61(A6); CLR.B 5e(A6) (falls into 202a0).
    case 0x20290:if(!pc3_bit(c,0x61,6,1,old) || !pc3_bit(c,0x61,7,2,old) || !pc3_put(c,r.a[6],0x5e,1,0))return false;r.pc=0x202a0;return true;
    // 202a0 (decision 10): MOVEA.L 8c(A6),A4; TST.W c(A4); BNE.W 202b6 (202ac is C5).
    case 0x202a0:if(!pc3_get(c,r.a[6],0x8c,4,r.a[4]) || !pc3_get(c,r.a[4],0xc,2,value))return false;r.pc=value!=0U?0x202b6:0x202ac;return true;
    // ---- 202b6 (BNE from 202a8, C5): MOVEA.L 8c(A6),A4; SUBQ.W #1,8(A4); BCC.W 202e6 (the borrow: WORD 0 before).
    case 0x202b6:
        if(!pc3_get(c,r.a[6],0x8c,4,r.a[4]) || !pc3_get(c,r.a[4],8,2,value) || !pc3_put(c,r.a[4],8,2,value-1U))return false;
        r.pc=value==0U?0x202c2:0x202e6;return true;
    // CLR.W 8(A4); CMPI.B #1,9e(A6); BNE.W 202e6.
    case 0x202c2:if(!pc3_put(c,r.a[4],8,2,0))return false;return pc3_byte_is(c,r.a[6],0x9e,1,0x202d0,0x202e6);
    case 0x202d0:return pc3_index_call(c,0x49c38,0x202da);                                                // MOVE.W 78(A6),D0; JSR 49c38.l.
    case 0x202da:return pc3_carry(c,0x202de,0x202e6);                                                     // BCS.W 202e6.
    case 0x202de:r.d[0]=2;r.a[0]=r.a[6];return am_call(c,0x1c1f4,0x202e6);                               // MOVEQ #2,D0; MOVEA.L A6,A0; BSR.W 1c1f4.
    case 0x202ec:r.pc=(r.d[0]&0x20U)!=0U?0x202fc:0x202f4;return true;                                   // BTST.B #5,D0; BNE.W 202fc.
    case 0x202f4:if(!pc3_get(c,r.a[6],0x8c,4,r.a[4]) || !pc3_put(c,r.a[4],8,2,0))return false;r.pc=0x202fc;return true;  // MOVEA.L 8c; CLR.W 8(A4).
    case 0x202fc:return am_call(c,0x1cef8,0x20300);                                                       // BSR.W 1cef8.
    case 0x20300:if(!pc3_bit(c,0xa8,3,2,old))return false;r.pc=old?0x20516:0x2030a;return true;          // BCLR.B #3,a8(A6); BNE.W 20516.
    // MOVEQ #0,D0; MOVE.B a0(A6),D0; CMP.B 9f(A6),D0; BEQ.W 20516.
    case 0x2030a:
        r.d[0]=0;if(!pc3_get(c,r.a[6],0xa0,1,value))return false;am_byte(r.d[0],value);if(!pc3_get(c,r.a[6],0x9f,1,value))return false;
        r.pc=(r.d[0]&0xffU)==value?0x20516:0x20318;return true;
    // ADD.W D0,D0 twice; JMP 20320(PC,D0.W) (contract decision 2: the 9 BRA.W entries 20320..20340 only; a displacement beyond the table is the
    // checked error).  The entry is decided by the routing: since player C10 the executed entry 20324 (BRA.W 203a0) is a C10 block (C10 contract
    // decision 2; was: no entry transcribed), the other entries are later-unit stops.
    case 0x20318: {
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        const std::uint32_t displacement=r.d[0]&0xffffU;
        if(displacement>0x20U)return am_error(c,"unsupported animation player c3 jump target");
        r.pc=am_index(0x20320,displacement);return true;
    }
    // ---- 20516: MOVE.B a4(A6),D0; BEQ.W 2053c / SUBQ.B #1,D0; MOVE.B D0,a4(A6); ANDI.W #1,D0; BNE.W 20534 / BSR.W 1d15a; BRA.W 2053c /
    // LEA 1b188(PC),A0; BSR.W 1d0c2.
    case 0x20516:if(!pc3_get(c,r.a[6],0xa4,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x2053c:0x2051e;return true;
    case 0x2051e:
        am_byte(r.d[0],r.d[0]-1U);if(!pc3_put(c,r.a[6],0xa4,1,r.d[0]))return false;am_word(r.d[0],r.d[0]&1U);
        r.pc=(r.d[0]&0xffffU)!=0U?0x20534:0x2052c;return true;
    case 0x2052c:return am_call(c,0x1d15a,0x20530);
    case 0x20530:r.pc=0x2053c;return true;
    case 0x20534:r.a[0]=0x1b188;return am_call(c,0x1d0c2,0x2053c);
    case 0x2053c:return pc3_byte_is(c,r.a[6],0x5e,0,0x20626,0x20544);                                    // TST.B 5e(A6); BEQ.W 20626 (20544 is C5).
    // ---- 20626: TST.B 5c8d(A5); BNE.W 20654 / MOVE.L 46(A6),D0; SUB.L 4e(A6),D0; BGT.W 20654 (signed LONG) / JSR 1a988.l /
    // SUB.W 46(A6),D0; BLE.W 20654 (signed WORD) / BSET.B #7,61(A6); MOVE.L #20720,(A6) (written only).
    case 0x20626:if(!pc3_get(c,r.a[5],0x5c8d,1,value))return false;r.pc=value!=0U?0x20654:0x2062e;return true;
    case 0x2062e: {
        std::uint32_t v4e=0;if(!pc3_get(c,r.a[6],0x46,4,value) || !pc3_get(c,r.a[6],0x4e,4,v4e))return false;
        r.d[0]=value-v4e;r.pc=(value^0x80000000U)>(v4e^0x80000000U)?0x20654:0x2063a;return true;
    }
    case 0x2063a:return am_call(c,0x1a988,0x20640);
    case 0x20640: {
        if(!pc3_get(c,r.a[6],0x46,2,value))return false;const std::uint32_t d0=r.d[0]&0xffffU;am_word(r.d[0],r.d[0]-value);
        r.pc=(d0^0x8000U)<=(value^0x8000U)?0x20654:0x20648;return true;
    }
    case 0x20648:if(!pc3_bit(c,0x61,7,1,old))return false;return pc3_install(c,0x20720,0x20654);
    case 0x20654:if(!pc3_bit(c,0xa8,1,0,old))return false;r.pc=old?0x2065e:0x20670;return true;          // BTST.B #1,a8(A6); BEQ.W 20670.
    // BSET.B #7,61(A6); MOVE.B #6,5e(A6); MOVE.L #20738,(A6) (written only).
    case 0x2065e:if(!pc3_bit(c,0x61,7,1,old) || !pc3_put(c,r.a[6],0x5e,1,6))return false;return pc3_install(c,0x20738,0x20670);
    case 0x20670:return am_call(c,0x206a4,0x20674);                                                       // BSR.W 206a4.
    // MOVE.B #ff,a6(A6); TST.B ab(A6); BEQ.W 20686 / SUBQ.B #1,ab(A6).
    case 0x20674:if(!pc3_put(c,r.a[6],0xa6,1,0xff))return false;return pc3_byte_is(c,r.a[6],0xab,0,0x20686,0x20682);
    case 0x20682:if(!pc3_get(c,r.a[6],0xab,1,value) || !pc3_put(c,r.a[6],0xab,1,value-1U))return false;r.pc=0x20686;return true;
    case 0x20686:return pc3_byte_is(c,r.a[6],0xac,0,0x2069c,0x2068e);                                    // TST.B ac(A6); BEQ.W 2069c.
    // SUBQ.B #1,ac(A6); MOVE.W 78(A6),D0; JSR 49bca.l.
    case 0x2068e:if(!pc3_get(c,r.a[6],0xac,1,value) || !pc3_put(c,r.a[6],0xac,1,value-1U))return false;return pc3_index_call(c,0x49bca,0x2069c);
    case 0x2069c:if(!pc3_bit(c,0xa8,7,2,old))return false;return am_return(c);                         // BCLR.B #7,a8(A6); RTS.
    // ---- 206a4: BCLR.B #0,a7(A6); MOVEQ #0,D0; MOVE.B a9(A6),D0; ADD.W D0,D0 twice; MOVEA.L 206d4(PC,D0.W),A0; CMPA.W #0,A0; BEQ.W 206d2 (fixed ROM
    // LONG table 206d4 + D0.W).
    case 0x206a4:
        if(!pc3_bit(c,0xa7,0,2,old))return false;r.d[0]=0;if(!pc3_get(c,r.a[6],0xa9,1,value))return false;am_byte(r.d[0],value);
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(0x206d4,r.d[0]&0xffffU),4,r.a[0]))return false;
        r.pc=r.a[0]==0U?0x206d2:0x206c0;return true;
    case 0x206c0:return am_call(c,0x4ae4a,0x206c6);                                                       // JSR 4ae4a.l.
    case 0x206c6:r.pc=(r.d[0]&0xffU)==0U?0x206d2:0x206cc;return true;                                   // TST.B D0; BEQ.W 206d2 (206cc is C6).
    // ---- RTS blocks (1ed32 215f6 21c1a keep the incoming C: dispatcher carry list).
    case 0x1ed32:case 0x206d2:case 0x215f6:case 0x21c1a:case 0x22236:return am_return(c);
    // ---- 2156a (BSR from 22216 and later units, BRA from 21ca0): MOVE.B 7a(A6),D0; EXT.W D0; MOVE.B 7b(A6),D1; EXT.W D1; BTST.B #0,15(A6);
    // BEQ.W 21582 / NEG.W D0 / BTST.B #1,15(A6); BEQ.W 2158e / NEG.W D1.
    case 0x2156a:
        if(!pc3_get(c,r.a[6],0x7a,1,value))return false;am_word(r.d[0],(value&0x80U)!=0U?(value|0xff00U):value);
        if(!pc3_get(c,r.a[6],0x7b,1,value))return false;am_word(r.d[1],(value&0x80U)!=0U?(value|0xff00U):value);
        if(!pc3_bit(c,0x15,0,0,old))return false;r.pc=old?0x21580:0x21582;return true;
    case 0x21580:am_word(r.d[0],0U-r.d[0]);r.pc=0x21582;return true;
    case 0x21582:if(!pc3_bit(c,0x15,1,0,old))return false;r.pc=old?0x2158c:0x2158e;return true;
    case 0x2158c:am_word(r.d[1],0U-r.d[1]);r.pc=0x2158e;return true;
    // MOVEM.W D0-D1,-(A7) (D0 at the lower address); ADD.W D0,2e / D1,32 / D0,42 / D1,46 / D0,4a / D1,4e(A6); MOVE.W 1e(A6),-(A7); MOVE.W #1,D0;
    // ADD.W D0,1e(A6); LEA 94(A6),A0; MOVE.W #100,D0; JSR 49fca.l.
    case 0x2158e:
        if(!am_push(c,2,r.d[1]&0xffffU) || !am_push(c,2,r.d[0]&0xffffU) || !pc3_add_word(c,0x2e,r.d[0]) || !pc3_add_word(c,0x32,r.d[1]) ||
           !pc3_add_word(c,0x42,r.d[0]) || !pc3_add_word(c,0x46,r.d[1]) || !pc3_add_word(c,0x4a,r.d[0]) || !pc3_add_word(c,0x4e,r.d[1]) ||
           !pc3_get(c,r.a[6],0x1e,2,value) || !am_push(c,2,value))return false;
        am_word(r.d[0],1);if(!pc3_add_word(c,0x1e,r.d[0]))return false;r.a[0]=am_index(r.a[6],0x94);am_word(r.d[0],0x100);
        return am_call(c,0x49fca,0x215c4);
    // MOVE.W (A7)+,1e(A6); MOVEM.W (A7)+,D0-D1 (each WORD sign-extended into the whole register); SUB.W D0,2e / D1,32 / D0,42 / D1,46 / D0,4a /
    // D1,4e(A6); RTS.
    case 0x215c4:
        if(!am_pop(c,2,value) || !pc3_put(c,r.a[6],0x1e,2,value) || !am_pop(c,2,value))return false;r.d[0]=am_extend_word(value);
        if(!am_pop(c,2,value))return false;r.d[1]=am_extend_word(value);
        if(!pc3_add_word(c,0x2e,0U-r.d[0]) || !pc3_add_word(c,0x32,0U-r.d[1]) || !pc3_add_word(c,0x42,0U-r.d[0]) || !pc3_add_word(c,0x46,0U-r.d[1]) ||
           !pc3_add_word(c,0x4a,0U-r.d[0]) || !pc3_add_word(c,0x4e,0U-r.d[1]))return false;
        return am_return(c);
    // ---- 215e6: MOVEQ #0,D0; MOVE.B 9c(A6),D0 / the (handler LONG, key WORD) list at A0: MOVEA.L (A0)+,A1; CMPA.W #0,A1; BNE.W 215f8 / RTS
    // (C Clear: CMPA) / CMP.W (A0)+,D0; BNE.B 215ec / ORI.B #1,CCR; RTS (C Set: A1 = the matched handler).
    case 0x215e6:r.d[0]=0;if(!pc3_get(c,r.a[6],0x9c,1,value))return false;am_byte(r.d[0],value);r.pc=0x215ec;return true;
    case 0x215ec:if(!am_read(c,r.a[0],4,r.a[1]))return false;r.a[0]+=4U;r.carry=AnimationCarryClear;r.pc=r.a[1]!=0U?0x215f8:0x215f6;return true;
    case 0x215f8:if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;r.pc=(r.d[0]&0xffffU)==value?0x215fc:0x215ec;return true;
    case 0x215fc:case 0x21bda:case 0x48362:return pc3_return_carry(c,AnimationCarrySet);
    // ---- 21602 (slot-84 value): BSET.B #5,a7(A6); MOVE.L #21610,84(A6) / MOVE.B #1,aa(A6); LEA 21622(PC),A0; BSR.B 215e6 / BCC.W 21662 (C6) /
    // JMP (A1) (contract decision 2: a handler of the list 21622, else checked).
    case 0x21602:if(!pc3_bit(c,0xa7,5,1,old))return false;return pc3_slot84(c,0x21610,0x21610);
    case 0x21610:if(!pc3_put(c,r.a[6],0xaa,1,1))return false;r.a[0]=0x21622;return am_call(c,0x215e6,0x2161c);
    case 0x2161c:return pc3_carry(c,0x21662,0x21620);
    case 0x21620:if(!pc3_listed(PC3_LIST_21622,10U,r.a[1]))return am_error(c,"unsupported animation player c3 jump target");r.pc=r.a[1];return true;
    // ---- 21baa: TST.B 9f(A6); BNE.W 21bc0 / MOVE.W 76(A6),D0; MOVE.B 21ba6(PC,D0.W),D0; CMP.B a1(A6),D0; RTS (C := unsigned D0.B < BYTE a1;
    // fixed ROM BYTE table 21ba6 + D0.W) / ANDI.B #fe,CCR; RTS.
    case 0x21baa:return pc3_byte_is(c,r.a[6],0x9f,0,0x21bb2,0x21bc0);
    case 0x21bb2:
        if(!pc3_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);if(!am_read(c,am_index(0x21ba6,r.d[0]&0xffffU),1,value))return false;
        am_byte(r.d[0],value);if(!pc3_get(c,r.a[6],0xa1,1,value))return false;
        return pc3_return_carry(c,(r.d[0]&0xffU)<value?AnimationCarrySet:AnimationCarryClear);
    case 0x21bc0:case 0x21be0:case 0x21bfa:case 0x21c1c:case 0x48392:case 0x4d100:case 0x4debc:return pc3_return_carry(c,AnimationCarryClear);
    // ---- 21bc6: CMPI.B #1,9e(A6); BNE.W 21be0 / BCLR.B #4,a7(A6); BEQ.W 21be0 / ORI.B #1,CCR; RTS.
    case 0x21bc6:return pc3_byte_is(c,r.a[6],0x9e,1,0x21bd0,0x21be0);
    case 0x21bd0:if(!pc3_bit(c,0xa7,4,2,old))return false;r.pc=old?0x21bda:0x21be0;return true;
    // ---- 21be6: ADDQ.B #1,a3(A6) (X := the carry out); SUBX.W D0,D0 (D0.W := 0 - 0 - X: ffff / 0, bits 16..31 kept; its Z is not read: OR.B sets
    // the flags again); OR.B D0,a3(A6) (ff saturates); CMPI.B #4,a3(A6); BCC.W 21c00 / ANDI.B #fe,CCR; RTS.
    case 0x21be6: {
        if(!pc3_get(c,r.a[6],0xa3,1,value))return false;const bool x=value==0xffU;
        if(!pc3_put(c,r.a[6],0xa3,1,value+1U))return false;am_word(r.d[0],x?0xffffU:0U);
        if(!pc3_get(c,r.a[6],0xa3,1,value) || !pc3_put(c,r.a[6],0xa3,1,value|(r.d[0]&0xffU)) || !pc3_get(c,r.a[6],0xa3,1,value))return false;
        r.pc=value>=4U?0x21c00:0x21bfa;return true;
    }
    case 0x21c00:return am_call(c,0x49a58,0x21c06);                                                       // JSR 49a58.l.
    // MOVEQ #0,D1; MOVE.B a3(A6),D1; CMP.W D1,D0; BCC.W 21c1a (C Clear, RTS) / 21c12 (C5, C Set).
    case 0x21c06: {
        r.d[1]=0;if(!pc3_get(c,r.a[6],0xa3,1,value))return false;am_byte(r.d[1],value);const bool borrow=(r.d[0]&0xffffU)<(r.d[1]&0xffffU);
        r.carry=borrow?AnimationCarrySet:AnimationCarryClear;r.pc=borrow?0x21c12:0x21c1a;return true;
    }
    // ---- 21c22 (handler of the list 21622): BSET.B #5,a7(A6); TST.B 9d(A6); BGT.W 21ca4 (C12); BLT.W 21d0e (C12) (signed BYTE).
    case 0x21c22:
        if(!pc3_bit(c,0xa7,5,1,old) || !pc3_get(c,r.a[6],0x9d,1,value))return false;
        r.pc=(value&0x80U)!=0U?0x21d0e:(value!=0U?0x21ca4:0x21c34);return true;
    case 0x21c34:if(!pc3_put(c,r.a[6],0x9d,1,0))return false;return am_call(c,0x21bc6,0x21c3a);         // CLR.B 9d(A6); BSR.B 21bc6.
    case 0x21c3a:return pc3_carry(c,0x21c3e,0x21f40);                                                     // BCS.W 21f40.
    case 0x21c3e:return am_call(c,0x21baa,0x21c42);                                                       // BSR.W 21baa.
    case 0x21c42:return pc3_carry(c,0x21c46,0x21f30);                                                     // BCS.W 21f30.
    case 0x21c46:return am_call(c,0x21c1c,0x21c48);                                                       // BSR.B 21c1c.
    case 0x21c48:return pc3_carry(c,0x21c4c,0x21fa6);                                                     // BCS.W 21fa6 (C12).
    case 0x21c4c:if(!pc3_put(c,r.a[6],0xaa,1,1))return false;r.a[0]=0x1b798;return am_call(c,0x1cabe,0x21c5a);  // MOVE.B #1,aa; LEA 1b798; BSR 1cabe.
    case 0x21c5a:if(!pc3_put(c,r.a[6],0xa3,1,0))return false;return pc3_slot84(c,0x21c66,0x21c66);      // CLR.B a3(A6); MOVE.L #21c66,84(A6).
    case 0x21c66:r.a[0]=0x21aee;return am_call(c,0x215e6,0x21c6e);                                        // LEA 21aee(PC),A0; BSR.W 215e6.
    case 0x21c6e:return pc3_carry(c,0x21c74,0x21c72);                                                     // BCC.W 21c74 (21c72 is C4).
    case 0x21c74:case 0x221e0:return am_call(c,0x1cd98,r.pc+4U);                                          // BSR.W 1cd98 / JSR 1cd98(PC).
    case 0x21c78:r.pc=(r.d[0]&1U)!=0U?0x223a0:0x21c80;return true;                                      // BTST.B #0,D0; BNE.W 223a0 (C13).
    case 0x21c80:r.pc=(r.d[0]&2U)!=0U?0x223d6:0x21c88;return true;                                      // BTST.B #1,D0; BNE.W 223d6 (C13).
    case 0x21c88:r.pc=(r.d[0]&0x40U)!=0U?0x21ffc:0x21c90;return true;                                   // BTST.B #6,D0; BNE.W 21ffc.
    case 0x21c90:r.pc=(r.d[0]&0x10U)!=0U?0x2210c:0x21c98;return true;                                   // BTST.B #4,D0; BNE.W 2210c (C12).
    case 0x21c98:return am_call(c,0x21be6,0x21c9c);                                                       // BSR.W 21be6.
    case 0x21c9c:return pc3_carry(c,0x21ca0,0x21f4c);                                                     // BCS.W 21f4c (C5).
    case 0x21ca0:r.pc=0x2156a;return true;                                                                 // BRA.W 2156a.
    // ---- 21f30 / 21f40: CLR.B a1(A6); LEA 1bc68(PC),A0; BSR.W 1cb40 / LEA 1b3c0(PC),A0; BSR.W 1cabe; BRA.W 21f58.
    case 0x21f30:if(!pc3_put(c,r.a[6],0xa1,1,0))return false;r.a[0]=0x1bc68;return am_call(c,0x1cb40,0x21f3c);
    case 0x21f3c:case 0x21f48:r.pc=0x21f58;return true;
    case 0x21f40:r.a[0]=0x1b3c0;return am_call(c,0x1cabe,0x21f48);
    // BCLR.B #5,a7(A6); MOVE.B #1,aa(A6); CLR.B 9d(A6); MOVE.L #21f70,84(A6) / LEA 21b26(PC),A0; BSR.W 215e6 (the return 21f78 is C5).
    case 0x21f58:
        if(!pc3_bit(c,0xa7,5,2,old) || !pc3_put(c,r.a[6],0xaa,1,1) || !pc3_put(c,r.a[6],0x9d,1,0))return false;return pc3_slot84(c,0x21f70,0x21f70);
    case 0x21f70:r.a[0]=0x21b26;return am_call(c,0x215e6,0x21f78);
    // ---- 21ffc: LEA 1b83c(PC),A0; BSR.W 1cabe / BCLR.B #5,a7(A6); CLR.B 9d(A6); CLR.B 7e(A6); ANDI.B #bf,a5(A6); ANDI.B #bf,a6(A6);
    // MOVE.B #2,aa(A6); BRA.W 221ca.
    case 0x21ffc:r.a[0]=0x1b83c;return am_call(c,0x1cabe,0x22004);
    case 0x22004:
        if(!pc3_bit(c,0xa7,5,2,old) || !pc3_put(c,r.a[6],0x9d,1,0) || !pc3_put(c,r.a[6],0x7e,1,0) || !pc3_get(c,r.a[6],0xa5,1,value) ||
           !pc3_put(c,r.a[6],0xa5,1,value&0xbfU) || !pc3_get(c,r.a[6],0xa6,1,value) || !pc3_put(c,r.a[6],0xa6,1,value&0xbfU) ||
           !pc3_put(c,r.a[6],0xaa,1,2))return false;
        r.pc=0x221ca;return true;
    // ---- 221ca: MOVE.L #221d2,84(A6) / LEA 216c8(PC),A0; BSR.W 215e6 / BCC.W 221e0 / JMP (A1) (contract decision 2: the handler 21602 of the list
    // 216c8, else checked).
    case 0x221ca:return pc3_slot84(c,0x221d2,0x221d2);
    case 0x221d2:r.a[0]=0x216c8;return am_call(c,0x215e6,0x221da);
    case 0x221da:return pc3_carry(c,0x221e0,0x221de);
    case 0x221de:if(r.a[1]!=0x21602U)return am_error(c,"unsupported animation player c3 jump target");r.pc=r.a[1];return true;
    case 0x221e4:return pc3_byte_is(c,r.a[6],0x7e,0,0x22216,0x221ec);                                    // TST.B 7e(A6); BEQ.W 22216.
    case 0x221ec:if(!pc3_bit(c,0xa5,4,0,old))return false;r.pc=old?0x221f6:0x221fe;return true;          // BTST.B #4,a5(A6); BEQ.W 221fe.
    case 0x221f6:return pc3_slot84(c,0x2210c,0x221fe);                                                    // MOVE.L #2210c,84(A6).
    case 0x221fe:if(!pc3_bit(c,0xa5,6,0,old))return false;r.pc=old?0x22208:0x22210;return true;          // BTST.B #6,a5(A6); BEQ.W 22210.
    case 0x22208:return pc3_slot84(c,0x21ffc,0x22210);                                                    // MOVE.L #21ffc,84(A6).
    case 0x22210:if(!pc3_put(c,r.a[6],0xaa,1,1))return false;r.pc=0x22216;return true;                 // MOVE.B #1,aa(A6).
    case 0x22216:return am_call(c,0x2156a,0x2221a);                                                       // BSR.W 2156a.
    case 0x2221a:r.pc=(r.d[7]&0xffffU)==0U?0x22228:0x22220;return true;                                 // TST.W D7; BEQ.W 22228.
    case 0x22220:return pc3_slot84(c,0x22452,0x22228);                                                    // MOVE.L #22452,84(A6).
    case 0x22228:return pc3_byte_is(c,r.a[6],0x7e,0,0x22230,0x22236);                                    // TST.B 7e(A6); BNE.W 22236.
    case 0x22230:if(!pc3_bit(c,0xa8,2,1,old))return false;r.pc=0x22236;return true;                    // BSET.B #2,a8(A6).
    // ---- 361e4 (28ae child of the C2 block 1d1e2): MOVE.W #ea,20(A6); MOVE.L 200098.l,22(A6) (bank window LONG); MOVE.W #fffe,68(A6);
    // MOVE.W #fffe,1e(A6); MOVEA.L c(A6),A0; MOVE.W 78(A0),D0; BNE.W 3622c.
    case 0x361e4:
        if(!pc3_put(c,r.a[6],0x20,2,0xea) || !am_read(c,0x200098,4,value) || !pc3_put(c,r.a[6],0x22,4,value) || !pc3_put(c,r.a[6],0x68,2,0xfffe) ||
           !pc3_put(c,r.a[6],0x1e,2,0xfffe) || !pc3_get(c,r.a[6],0xc,4,r.a[0]) || !pc3_get(c,r.a[0],0x78,2,value))return false;
        am_word(r.d[0],value);r.pc=value!=0U?0x3622c:0x3620a;return true;
    // MOVE.W #2a3 / #2a2,D0; MOVE.B #0,D1; JSR 8ebe.l / MOVEA.L #37e9c / #37ef2,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3620a:case 0x3622c:am_word(r.d[0],r.pc==0x3620aU?0x2a3U:0x2a2U);am_byte(r.d[1],0);return am_call(c,0x8ebe,r.pc+0xeU);
    case 0x36218:case 0x3623a:r.a[1]=r.pc==0x36218U?0x37e9cU:0x37ef2U;am_word(r.d[0],0x100);return am_call(c,0x49f8c,r.pc+0x10U);
    case 0x36228:r.pc=0x3624a;return true;                                                                 // BRA.W 3624a.
    case 0x3624a:r.d[0]=0;am_word(r.d[1],0x38);return am_call(c,0x49290,0x36256);                      // MOVEQ #0,D0; MOVE.W #38,D1; JSR 49290.l.
    case 0x3625c:r.pc=(r.d[0]&8U)==0U?0x3626a:0x36264;return true;                                      // BTST.B #3,D0; BEQ.W 3626a.
    case 0x36264:if(!pc3_put(c,r.a[6],0x32,2,0x28))return false;r.pc=0x3626a;return true;              // MOVE.W #28,32(A6).
    case 0x3626a:r.pc=(r.d[0]&0x40U)==0U?0x36278:0x36272;return true;                                   // BTST.B #6,D0; BEQ.W 36278.
    case 0x36272:if(!pc3_put(c,r.a[6],0x32,2,0x30))return false;r.pc=0x36278;return true;              // MOVE.W #30,32(A6).
    case 0x36278:if(!pc3_put(c,r.a[6],0x76,1,0))return false;return am_call(c,0x482aa,0x36282);         // CLR.B 76(A6); JSR 482aa.l.
    case 0x36282:return pc3_carry(c,0x3628c,0x36286);                                                     // BCC.W 3628c (C of 482aa).
    case 0x36286:if(!pc3_put(c,r.a[6],0x76,1,0x50))return false;r.pc=0x3628c;return true;              // MOVE.B #50,76(A6).
    case 0x3628c:return pc3_install(c,0x36292,0x36292);                                                   // MOVE.L #36292,(A6) (FR6, entered at once).
    // ---- 48350 (the Set side of the C1 block 48346): BTST.B #5,5683(A5); BNE.W 48362 / TST.B 568e(A5); BNE.W 48368 (C1: C Clear) / ORI.B #1,CCR; RTS.
    case 0x48350:if(!pc3_get(c,r.a[5],0x5683,1,value))return false;r.pc=(value&0x20U)!=0U?0x48362:0x4835a;return true;
    case 0x4835a:if(!pc3_get(c,r.a[5],0x568e,1,value))return false;r.pc=value!=0U?0x48368:0x48362;return true;
    // ---- 48384 (JSR from C2 1d1d0): TST.B 5684(A5); BEQ.W 48392 (C Clear) / 4838c (C6).
    case 0x48384:return pc3_byte_is(c,r.a[5],0x5684,0,0x48392,0x4838c);
    // ---- 484ca: MOVEQ #0,D0; MOVE.B 5682(A5),D0; RTS.
    case 0x484ca:r.d[0]=0;if(!pc3_get(c,r.a[5],0x5682,1,value))return false;am_byte(r.d[0],value);return am_return(c);
    // ---- 4d0a4: TST.W 78(A6); BNE.W 4d0b4 / LEA 5cba(A5),A4; BRA.W 4d0b8 / LEA 5ce6(A5),A4 / TST.W (A4); BNE.W 4d0cc (C8) / MOVE.B 22(A4),D0;
    // LSR.B #1,D0; MOVE.B D0,22(A4); BRA.W 4d100 (ANDI.B #fe,CCR; RTS).
    case 0x4d0a4:if(!pc3_get(c,r.a[6],0x78,2,value))return false;r.pc=value!=0U?0x4d0b4:0x4d0ac;return true;
    case 0x4d0ac:r.a[4]=am_index(r.a[5],0x5cba);r.pc=0x4d0b8;return true;
    case 0x4d0b4:r.a[4]=am_index(r.a[5],0x5ce6);r.pc=0x4d0b8;return true;
    case 0x4d0b8:if(!am_read(c,r.a[4],2,value))return false;r.pc=value!=0U?0x4d0cc:0x4d0be;return true;
    case 0x4d0be:if(!pc3_get(c,r.a[4],0x22,1,value))return false;am_byte(r.d[0],value>>1);if(!pc3_put(c,r.a[4],0x22,1,r.d[0]))return false;
        r.pc=0x4d100;return true;
    // ---- 4de9c: LEA 5d12(A5),A4; ANDI.W #1,D0; BEQ.W 4deac / LEA 5d18(A5),A4 / TST.W 4(A4); BPL.W 4dec2 / TST.B (A4); BEQ.W 4debc / SUBQ.B #1,(A4) /
    // ANDI.B #fe,CCR; RTS / CMPI.B #1,(A4); BNE.W 4ded4 / MOVE.B #2,(A4); ORI.B #1,CCR; RTS / MOVE.W #ffff,4(A4); CLR.B (A4); ANDI.B #fe,CCR; RTS.
    case 0x4de9c:r.a[4]=am_index(r.a[5],0x5d12);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&0xffffU)==0U?0x4deac:0x4dea8;return true;
    case 0x4dea8:r.a[4]=am_index(r.a[5],0x5d18);r.pc=0x4deac;return true;
    case 0x4deac:if(!pc3_get(c,r.a[4],4,2,value))return false;r.pc=(value&0x8000U)==0U?0x4dec2:0x4deb4;return true;
    case 0x4deb4:return pc3_byte_is(c,r.a[4],0,0,0x4debc,0x4deba);
    case 0x4deba:if(!am_read(c,r.a[4],1,value) || !am_write(c,r.a[4],1,(value-1U)&0xffU))return false;r.pc=0x4debc;return true;
    case 0x4dec2:return pc3_byte_is(c,r.a[4],0,1,0x4deca,0x4ded4);
    case 0x4deca:if(!am_write(c,r.a[4],1,2))return false;return pc3_return_carry(c,AnimationCarrySet);
    case 0x4ded4:if(!pc3_put(c,r.a[4],4,2,0xffff) || !am_write(c,r.a[4],1,0))return false;return pc3_return_carry(c,AnimationCarryClear);
    // ---- e8b5a (JSR from C2 1d314): CLR.B 5e2e(A5); MOVE.B #ff,5e2f(A5); MOVEA.L 5e26(A5),A4; MOVE.W (A4),D2; MOVE.W 2(A4),D3 / MOVE.W D0,-(A7);
    // LEA 538e(A5),A1; BTST.B #1,4(A4); BEQ.W e8b80 (FR7: e8b7e / e8b80).
    case 0xe8b5a:
        if(!pc3_put(c,r.a[5],0x5e2e,1,0) || !pc3_put(c,r.a[5],0x5e2f,1,0xff) || !pc3_get(c,r.a[5],0x5e26,4,r.a[4]) || !am_read(c,r.a[4],2,value))return false;
        am_word(r.d[2],value);if(!pc3_get(c,r.a[4],2,2,value))return false;am_word(r.d[3],value);r.pc=0xe8b6e;return true;
    case 0xe8b6e:
        if(!am_push(c,2,r.d[0]&0xffffU))return false;r.a[1]=am_index(r.a[5],0x538e);if(!pc3_get(c,r.a[4],4,1,value))return false;
        r.pc=(value&2U)==0U?0xe8b80:0xe8b7e;return true;
    default:return am_error(c,"unsupported animation player c3 PC");
    }
}
}
