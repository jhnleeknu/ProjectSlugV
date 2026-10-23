#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool ofr10_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr10_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR / BCHG #bit,d16(An) (a memory operand: BYTE, bit modulo 8). op 0 tests, 1 sets, 2 clears, 3 changes; old is the bit before
// (the Z of the instruction is old = 0).
bool ofr10_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!ofr10_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    std::uint32_t next=value&~mask;
    if(op==1U || (op==3U && !old))next=value|mask;
    return ofr10_put(c,base,displacement,1,next);
}
// BTST #bit,d16(An); BEQ.W zero_pc (the bit clear) / BNE one_pc (the bit set).
bool ofr10_btst(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    bool old=false;if(!ofr10_bit(c,base,displacement,bit,0,old))return false;
    c.s.pc=old?one_pc:zero_pc;return true;
}
// BCHG.B #bit,d16(A6) (the Z is read by no FR10 block).
bool ofr10_change(AnimationMachineContext& c,unsigned int bit) {bool old=false;return ofr10_bit(c,c.s.a[6],0x15,bit,3,old);}
// TST.B / TST.W d16(A6); BEQ.W zero_pc / other_pc.
bool ofr10_test(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr10_get(c,c.s.a[6],displacement,size,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// BCC / BCS on the known C returned to the block: clear -> clear_pc, set -> set_pc; Unknown is a checked error.
bool ofr10_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr10 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #value,(A6) followed by next_pc (the value is entered only when it is next_pc; otherwise it is written only).
bool ofr10_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr10_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// ASR.L #n (n = 1..31): arithmetic right shift of the LONG (the sign bit fills the vacated bits; no signed shift).
std::uint32_t ofr10_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t shifted=value>>n;return (value&0x80000000U)!=0U?(shifted|~(0xffffffffU>>n)):shifted;
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus; FR4 ofr4_bank_anim).
bool ofr10_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=r.a[6]+0x26U;
    if(!ofr10_put(c,r.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr10_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=r.a[6]+0x26U;
    if(!ofr10_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!ofr10_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVEA.L #b7f6c,A1; ADD.W D0,D0; ADD.W D0,D0; MOVE.L (A1,D0.W),D0;
// MOVEA.L window.l,A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l (b6bb8 / b6bf4: the ROM LONG table b7f6c
// indexed by D0.W, then the bank-window LONG table indexed by that LONG's WORD; all reads through the live bus, WORD index arithmetic).
bool ofr10_table_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=r.a[6]+0x26U;
    if(!ofr10_put(c,r.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr10_put(c,r.a[6],0x22,4,value))return false;
    r.a[1]=0xb7f6c;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.d[0]=value;
    if(!am_read(c,window,4,value))return false;r.a[1]=value;am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 8a(A6),20(A6); MOVEA.L #anim,A1; MOVE.W #100,D0; JSR 49f8c.l.
bool ofr10_anim(AnimationMachineContext& c,std::uint32_t anim,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr10_get(c,r.a[6],0x8a,2,value) || !ofr10_put(c,r.a[6],0x20,2,value))return false;r.a[1]=anim;am_word(r.d[0],0x100);
    return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 8c(A6),D0; BNE.W other_pc (D0.W = 0 -> zero_pc).
bool ofr10_kind(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr10_get(c,c.s.a[6],0x8c,2,value))return false;am_word(c.s.d[0],value);
    c.s.pc=(c.s.d[0]&0xffffU)==0U?zero_pc:other_pc;return true;
}
// CMPI.W #k,D0; BNE.W other_pc (D0.W = k -> equal_pc).
void ofr10_select(AnimationMachineState& r,std::uint32_t k,std::uint32_t equal_pc,std::uint32_t other_pc) {
    r.pc=(r.d[0]&0xffffU)==k?equal_pc:other_pc;
}
// MOVE.W 8e(A6),D0; SUB.W 42(A6),D0; BTST.B #0,15(A6); SEQ.B D1; EXT.W D1; EOR.W D0,D1; BPL.W plus_pc (N = bit 15 of the new D1.W) / minus_pc.
bool ofr10_facing(AnimationMachineContext& c,std::uint32_t plus_pc,std::uint32_t minus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t a=0;std::uint32_t b=0;bool old=false;
    if(!ofr10_get(c,r.a[6],0x8e,2,a) || !ofr10_get(c,r.a[6],0x42,2,b))return false;am_word(r.d[0],a-b);
    if(!ofr10_bit(c,r.a[6],0x15,0,0,old))return false;
    am_byte(r.d[1],old?0U:0xffU);am_word(r.d[1],old?0U:0xffffU);   // SEQ.B D1; EXT.W D1 (the BYTE 00 / ff -> WORD 0000 / ffff)
    am_word(r.d[1],r.d[1]^r.d[0]);r.pc=(r.d[1]&0x8000U)==0U?plus_pc:minus_pc;return true;
}
// The N of the 49a58 tail SUB.W D0,(A3) (its only predecessor; A3 and that WORD are unchanged by its RTS; U12 70198): bit 15 of the WORD (A3),
// read again from work RAM / fixed ROM; any other address is a checked flag-source error (contract decision 3).
bool ofr10_random_negative(AnimationMachineContext& c,bool& negative) {
    std::uint32_t value=0;
    if((c.s.a[3]&0xffffffU)>=0x200000U)return am_error(c,"unsupported animation objects fr10 flag source");
    if(!am_read(c,c.s.a[3],2,value))return false;negative=(value&0x8000U)!=0U;return true;
}
// ADDQ.B #1,(An).
bool ofr10_count_byte(AnimationMachineContext& c,std::uint32_t address) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;return am_write(c,address,1,(value+1U)&0xffU);
}
}
// Objects FR10 (211 block starts, contract docs/analysis/animation-machine-frontier-fr10-contract.md, area C plan 10.5 FR10 row without the C7 table
// entry 252b4 -> 252ce (main decision 4: C10) and with the branch target cd804 of the sibling cd7c2): the area-D code that the extended-input IO
// observation reaches after C9 -- the object states 70e2a (FR2b install) -> 70ea2 / 70efe / 70f12 / 70f2c -> 70f3e .. 7102e with the C helper
// 70594 (705be ORI Set / 705c4 ANDI Clear: also the N15 711b6 callee), 713d8 / 71468 (N15 / FR2b installs) -> 7143a / 714ca, the U18 install b6ba0 ->
// b6c2c / b6c66 -> b6c72 with the helper b7a62 (MOVEM.W D0-D1 around 49392, 4e122) and b7b30 (U19 callee: EORI.B #1,CCR inverts the C of 4941e),
// the FR4 table entries cc7c4 / cc7d0 / cc846 -> cd94e / cd7c6 / ccaf8, the script callbacks 6f1ca / cca44 / cca52 (interpreter table 4a500), the
// states ccaf8 / cd7c6 .. cd8e0 -> cd8ee / cd94e -> cda34 -> cdafc (the C helper ccade: TST.B Clear, passed by ccae6 / ccaf6), the 28ae child
// cdd86 -> cde6e, the U18 install eaa00 -> eaa20 and the 28ae child eaac0 (C9 / FR3) -> eab2a.  No computed jump, no TRAP, no JSR (An).  ROM data:
// the LONG tables 70d72 (70fec), b7f6c (b6bb8 / b6bf4), ea732 (eaa00), eaa5c (eaada) and the bank-window LONGs 2000d0 / 2000d4 / 2001a8 / 2001ac /
// 200094, all through the live bus.  MOVE.L #v,(A6) enters v only when v is the next PC; 70f2c (MOVE.L last) leaves C Clear and 70f3e passes the C
// to the N15 consumer 71c48 (BTST+BEQ+BCS).  The 13 C consumers 70f8a 7145a 714ea eab36 (49fc6), 70fd6
// (7028e), 70ffe (705ca), 71016 (70594), b7a68 (484e2), b7a78 (MOVEM.W (A7)+; 49392), cd940 (ccade), cdd9c (28ae), eaa3a (eaa26 Clear or 49fc6) and
// eaac6 (BCS, 1abda) read a known C or fail; b7b40 inverts a known C (Unknown fails).  The Z reader 70ff4 recomputes the CMPA.W #0,A0 of 70ff0 from
// A0; the N reader cd80a recomputes the N of the 49a58 SUB.W D0,(A3) from the WORD (A3) (flag-source guard).
bool animation_objects_fr10_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool old=false;
    switch(r.pc) {
    case 0xb7a6c:case 0xb7aca:case 0xccaf6:case 0xeaa52:case 0xeab40:return am_return(c);   // RTS (ccaf6 passes the C of ccade / ccae6 / 4b54e).
    case 0xeaaca:case 0xeab3a:r.pc=0x2a00;return true;                                       // JMP 2a00.l.
    // ---- 4e122 (b7a80): ANDI.W #1,D0; ADD.W D0,D0; LEA 5d26(A5),A0; ADDQ.W #1,(A0,D0.W); RTS.
    case 0x4e122:
        am_word(r.d[0],r.d[0]&1U);am_word(r.d[0],r.d[0]+r.d[0]);r.a[0]=am_index(r.a[5],0x5d26);
        if(!ofr10_get(c,r.a[0],r.d[0],2,value) || !ofr10_put(c,r.a[0],r.d[0],2,value+1U))return false;return am_return(c);
    // ---- 6f1ca (script callback, table 4a500): TST.W 3a(A6); SPL.B 80(A6); RTS.
    case 0x6f1ca:
        if(!ofr10_get(c,r.a[6],0x3a,2,value) || !ofr10_put(c,r.a[6],0x80,1,(value&0x8000U)==0U?0xffU:0U))return false;return am_return(c);
    // ---- 70594 (C helper; N15 711b6, 71012): MOVE.W #1,D7; AND.W 80(A6),D7; BEQ.W 705c4.
    case 0x70594:
        if(!ofr10_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[7],1U&value);r.pc=(r.d[7]&0xffffU)==0U?0x705c4:0x705a0;return true;
    case 0x705a0:return ofr10_btst(c,r.a[6],0x82,5,0x705c4,0x705aa);                                  // BTST.B #5,82(A6); BEQ.W 705c4.
    // TST.W 64(A6); SMI.B D0; BTST.B #0,15(A6); SEQ.B D1; EOR.B D0,D1; BMI.W 705c4 (N = bit 7 of the new D1.B).
    case 0x705aa:
        if(!ofr10_get(c,r.a[6],0x64,2,value) || !ofr10_bit(c,r.a[6],0x15,0,0,old))return false;
        am_byte(r.d[0],(value&0x8000U)!=0U?0xffU:0U);am_byte(r.d[1],old?0U:0xffU);am_byte(r.d[1],r.d[1]^r.d[0]);
        r.pc=(r.d[1]&0x80U)!=0U?0x705c4:0x705be;return true;
    case 0x705be:r.carry=AnimationCarrySet;return am_return(c);                                       // ORI.B #1,CCR; RTS.
    case 0x705c4:r.carry=AnimationCarryClear;return am_return(c);                                     // ANDI.B #fe,CCR; RTS.
    // ---- 70e2a (FR2b 70cba install): the facing test; BPL.W 70ea2, else the later-unit PC 70e42.
    case 0x70e2a:return ofr10_facing(c,0x70ea2,0x70e42);
    case 0x70ea2:return ofr10_test(c,0x9c,2,0x70eaa,0x70ed6);                                          // TST.W 9c(A6); BNE.W 70ed6.
    case 0x70eaa:return ofr10_bank_anim(c,3,0x2000d0,0x11c,0x70ed2);
    case 0x70ed6:return ofr10_bank_anim(c,0xb,0x2000d4,0x194,0x70efe);
    case 0x70ed2:r.pc=0x70efe;return true;                                                            // BRA.W 70efe.
    // MOVE.L 8e(A6),D0; SUB.L 42(A6),D0; ASR.L #5,D0; MOVE.L D0,64(A6); JSR 49a58.l.
    case 0x70efe:
        if(!ofr10_get(c,r.a[6],0x8e,4,value) || !ofr10_get(c,r.a[6],0x42,4,other))return false;r.d[0]=ofr10_asr(value-other,5);
        if(!ofr10_put(c,r.a[6],0x64,4,r.d[0]))return false;return am_call(c,0x49a58,0x70f12);
    // ANDI.W #7fff,D0; SUBI.W #4000,D0; EXT.L D0; ADD.L 64(A6),D0; MOVE.L D0,64(A6); TST.L D0; BPL.W 70f2c.
    case 0x70f12:
        am_word(r.d[0],r.d[0]&0x7fffU);am_word(r.d[0],r.d[0]-0x4000U);r.d[0]=am_extend_word(r.d[0]);
        if(!ofr10_get(c,r.a[6],0x64,4,value))return false;r.d[0]=r.d[0]+value;if(!ofr10_put(c,r.a[6],0x64,4,r.d[0]))return false;
        r.pc=(r.d[0]&0x80000000U)==0U?0x70f2c:0x70f2a;return true;
    case 0x70f2a:r.d[0]=0U-r.d[0];r.pc=0x70f2c;return true;                                          // NEG.L D0.
    // LSL.L #6,D0; SWAP D0; ADDI.W #80,D0; MOVE.W D0,2c(A6); MOVE.L #70f3e,(A6) (next PC; the MOVE.L leaves C Clear for 70f3e -> N15 71c48).
    case 0x70f2c:
        r.d[0]=r.d[0]<<6;am_swap(r.d[0]);am_word(r.d[0],r.d[0]+0x80U);if(!ofr10_put(c,r.a[6],0x2c,2,r.d[0]))return false;
        r.carry=AnimationCarryClear;return ofr10_install(c,0x70f3e,0x70f3e);
    // BTST.B #7,15(A6); BEQ.W 71c48 (C passed: the BCS 71c52 of the N15 consumer 71c48 reads it when BYTE 82 bit 1 is set).
    case 0x70f3e:return ofr10_btst(c,r.a[6],0x15,7,0x71c48,0x70f48);
    case 0x70f48:case 0x7144e:return am_call(c,0x4bfa4,r.pc+6U);                                    // JSR 4bfa4.l.
    // MOVE.B #0,63(A6); SUBI.W #2800,D7; CMPI.W #3000,D7; BCS.W 70f84 (unsigned WORD < 3000), else the later-unit PC 70f60.
    case 0x70f4e:
        if(!ofr10_put(c,r.a[6],0x63,1,0))return false;am_word(r.d[7],r.d[7]-0x2800U);r.pc=(r.d[7]&0xffffU)<0x3000U?0x70f84:0x70f60;return true;
    case 0x70f84:case 0x71454:case 0x714e4:case 0xeab30:return am_call(c,0x49fc6,r.pc+6U);          // JSR 49fc6.l.
    case 0x70f8a:return ofr10_carry(c,0x70f94,0x70f8e);                                               // BCC.W 70f94 (C of 49fc6).
    case 0x70f94:return ofr10_facing(c,0x70fc2,0x70fac);
    case 0x70fc2:return ofr10_btst(c,r.a[6],0x82,7,0x70fd2,0x70fcc);                                  // BTST.B #7,82(A6); BEQ.W 70fd2.
    case 0x70fd2:return am_call(c,0x7028e,0x70fd6);                                                   // BSR.W 7028e.
    case 0x70fd6:return ofr10_carry(c,0x70fe0,0x70fda);                                               // BCC.W 70fe0 (C of 7028e).
    case 0x70fda:return ofr10_install(c,0x72978,0x70fe0);                                             // MOVE.L #72978,(A6) (written only).
    case 0x70fe0:return am_call(c,0x70302,0x70fe4);                                                   // BSR.W 70302.
    case 0x70fe4:r.a[0]=0x70d72;r.pc=0x70fe8;return true;                                            // LEA 70d72(PC),A0.
    case 0x70fe8:am_word(r.d[0],r.d[0]+r.d[0]);r.pc=0x70fea;return true;                            // ADD.W D0,D0.
    case 0x70fea:am_word(r.d[0],r.d[0]+r.d[0]);r.pc=0x70fec;return true;                            // ADD.W D0,D0.
    case 0x70fec:if(!ofr10_get(c,r.a[0],r.d[0],4,value))return false;r.a[0]=value;r.pc=0x70ff0;return true;   // MOVEA.L (A0,D0.W),A0.
    case 0x70ff0:r.pc=0x70ff4;return true;                                                            // CMPA.W #0,A0 (flags only).
    case 0x70ff4:r.pc=r.a[0]==0U?0x70ffa:0x70ff8;return true;        // BEQ.W 70ffa: Z of CMPA.W #0,A0 recomputed from A0 (decision 3).
    case 0x70ffa:return am_call(c,0x705ca,0x70ffe);                                                   // BSR.W 705ca.
    case 0x70ffe:return ofr10_carry(c,0x71008,0x71002);                                               // BCC.W 71008 (C of 705ca).
    case 0x71002:return ofr10_install(c,0x71dd6,0x71008);                                             // MOVE.L #71dd6,(A6) (written only).
    case 0x71008:return ofr10_btst(c,r.a[6],0x61,0,0x71020,0x71012);                                  // BTST.B #0,61(A6); BEQ.W 71020.
    case 0x71012:return am_call(c,0x70594,0x71016);                                                   // JSR 70594(PC).
    case 0x71016:return ofr10_carry(c,0x71020,0x7101a);                                               // BCC.W 71020 (C of 70594).
    case 0x7101a:return ofr10_install(c,0x712a0,0x71020);                                             // MOVE.L #712a0,(A6) (written only).
    case 0x71020:return ofr10_test(c,0x7c,2,0x71028,0x7102e);                                         // TST.W 7c(A6); BNE.W 7102e.
    case 0x7102e:case 0x71464:case 0x714fe:r.pc=0x72dd2;return true;                                 // BRA.W 72dd2.
    // ---- 713d8 (N15 71126 / 71148 install) / 71468 (FR2b 70cee, N15 71136 install).
    case 0x713d8:return ofr10_test(c,0x9c,2,0x713e0,0x7140c);                                         // TST.W 9c(A6); BNE.W 7140c.
    case 0x713e0:return ofr10_bank_anim(c,3,0x2000d0,8,0x71408);
    case 0x7140c:return ofr10_bank_anim(c,0xb,0x2000d4,8,0x71434);
    case 0x71408:r.pc=0x71434;return true;                                                            // BRA.W 71434.
    case 0x71434:return ofr10_install(c,0x7143a,0x7143a);                                             // MOVE.L #7143a,(A6) (next PC).
    // MOVE.L 64(A6),D0; ASR.L #3,D0; SUB.L D0,64(A6); BTST.B #7,15(A6); BEQ.W 71c90.
    case 0x7143a:
        if(!ofr10_get(c,r.a[6],0x64,4,value))return false;r.d[0]=ofr10_asr(value,3);if(!ofr10_put(c,r.a[6],0x64,4,value-r.d[0]))return false;
        return ofr10_btst(c,r.a[6],0x15,7,0x71c90,0x7144e);
    case 0x7145a:return ofr10_carry(c,0x71464,0x7145e);                                               // BCC.W 71464 (C of 49fc6).
    case 0x7145e:return ofr10_install(c,0x70c0c,0x71464);                                             // MOVE.L #70c0c,(A6) (written only).
    case 0x71468:return ofr10_test(c,0x9c,2,0x71470,0x7149c);                                         // TST.W 9c(A6); BNE.W 7149c.
    case 0x71470:return ofr10_bank_anim(c,3,0x2000d0,0x18,0x71498);
    case 0x7149c:return ofr10_bank_anim(c,0xb,0x2000d4,0x18,0x714c4);
    case 0x71498:r.pc=0x714c4;return true;                                                            // BRA.W 714c4.
    case 0x714c4:return ofr10_install(c,0x714ca,0x714ca);                                             // MOVE.L #714ca,(A6) (next PC).
    case 0x714ca:return ofr10_btst(c,r.a[6],0x15,7,0x71c90,0x714d4);                                  // BTST.B #7,15(A6); BEQ.W 71c90.
    // MOVE.L 64(A6),D0; ASR.L #2,D0; SUB.L D0,64(A6); JSR 4bfa4.l.
    case 0x714d4:
        if(!ofr10_get(c,r.a[6],0x64,4,value))return false;r.d[0]=ofr10_asr(value,2);if(!ofr10_put(c,r.a[6],0x64,4,value-r.d[0]))return false;
        return am_call(c,0x4bfa4,0x714e4);
    case 0x714ea:return ofr10_carry(c,0x714fe,0x714ee);                                               // BCC.W 714fe (C of 49fc6).
    case 0x714ee:r.a[0]=r.a[6]+0x26U;return am_call(c,0x492d0,0x714f8);                             // LEA 26(A6),A0; JSR 492d0.l.
    case 0x714f8:return ofr10_install(c,0x71032,0x714fe);                                             // MOVE.L #71032,(A6) (written only).
    // ---- b6ba0 (U18 b76c8 install): MOVE.B 9d(A6),D0; BSR.W b7a62.
    case 0xb6ba0:if(!ofr10_get(c,r.a[6],0x9d,1,value))return false;am_byte(r.d[0],value);return am_call(c,0xb7a62,0xb6ba8);
    // CLR.L 56(A6); MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b6bf4.
    case 0xb6ba8:
        if(!ofr10_put(c,r.a[6],0x56,4,0) || !ofr10_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[0],value);
        r.pc=(r.d[0]&0xffffU)==0U?0xb6bb8:0xb6bf4;return true;
    case 0xb6bb8:return ofr10_table_anim(c,0x1b3,0x2001a8,0xb6bf0);
    case 0xb6bf4:return ofr10_table_anim(c,0x1bb,0x2001ac,0xb6c2c);
    case 0xb6bf0:r.pc=0xb6c2c;return true;                                                            // BRA.W b6c2c.
    // MOVE.L #fffffffc,96(A6); MOVE.L #1a,98(A6); CMPI.W #c0,42(A6); BLE.W b6c58 (signed WORD <= c0; the later-unit PC b6c58).
    case 0xb6c2c:
        if(!ofr10_put(c,r.a[6],0x96,4,0xfffffffcU) || !ofr10_put(c,r.a[6],0x98,4,0x1a) || !ofr10_get(c,r.a[6],0x42,2,value))return false;
        r.pc=((value&0x8000U)!=0U || value<=0xc0U)?0xb6c58:0xb6c46;return true;
    // BSET.B #0,15(A6); MOVE.L #fff90000,64(A6); BRA.W b6c66.
    case 0xb6c46:
        if(!ofr10_bit(c,r.a[6],0x15,0,1,old) || !ofr10_put(c,r.a[6],0x64,4,0xfff90000U))return false;r.pc=0xb6c66;return true;
    // MOVE.W #4,84(A6); MOVE.L #b6c72,(A6) (next PC).
    case 0xb6c66:if(!ofr10_put(c,r.a[6],0x84,2,4))return false;return ofr10_install(c,0xb6c72,0xb6c72);
    case 0xb6c72:return am_call(c,0xb7cfa,0xb6c76);                                                   // BSR.W b7cfa.
    case 0xb6c76:return am_call(c,0x49fc6,0xb6c7c);                                                   // JSR 49fc6.l (C not read).
    // SUBQ.W #1,84(A6); BNE.W b6c9e (the new WORD).
    case 0xb6c7c:
        if(!ofr10_get(c,r.a[6],0x84,2,value) || !ofr10_put(c,r.a[6],0x84,2,value-1U))return false;
        r.pc=((value-1U)&0xffffU)!=0U?0xb6c9e:0xb6c84;return true;
    // BCHG.B #0,15(A6); MOVE.L #b6ca2,(A6) (written only); TST.W 7c(A6); BGT.W b6c9e (signed WORD > 0).
    case 0xb6c84:
        if(!ofr10_change(c,0) || !ofr10_put(c,r.a[6],0,4,0xb6ca2) || !ofr10_get(c,r.a[6],0x7c,2,value))return false;
        r.pc=((value&0x8000U)==0U && value!=0U)?0xb6c9e:0xb6c98;return true;
    case 0xb6c98:return ofr10_install(c,0xb6d82,0xb6c9e);                                             // MOVE.L #b6d82,(A6) (written only).
    case 0xb6c9e:r.pc=0xb76d2;return true;                                                            // BRA.W b76d2.
    // ---- b7a62 (b6ba0): JSR 484e2.l; BCC.W b7a6e / RTS.
    case 0xb7a62:return am_call(c,0x484e2,0xb7a68);
    case 0xb7a68:return ofr10_carry(c,0xb7a6e,0xb7a6c);                                               // BCC.W b7a6e (C of 484e2).
    // MOVEM.W D0-D1,-(A7) (D1 at A7 - 2, D0 at A7 - 4); JSR 49392.l.
    case 0xb7a6e:if(!am_push(c,2,r.d[1]&0xffffU) || !am_push(c,2,r.d[0]&0xffffU))return false;return am_call(c,0x49392,0xb7a78);
    // MOVEM.W (A7)+,D0-D1 (each WORD sign-extended to the LONG; flags unchanged); BCC.W b7aca (C of 49392).
    case 0xb7a78:
        if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr10 caller requires known carry");
        if(!am_pop(c,2,value) || !am_pop(c,2,other))return false;r.d[0]=am_extend_word(value);r.d[1]=am_extend_word(other);
        r.pc=c.s.carry==AnimationCarryClear?0xb7aca:0xb7a80;return true;
    case 0xb7a80:return am_call(c,0x4e122,0xb7a86);                                                   // JSR 4e122.l.
    case 0xb7a86:r.pc=(r.d[0]&0xffU)==0U?0xb7a8c:0xb7a9c;return true;                              // TST.B D0; BNE.W b7a9c.
    // LEA 5ddc(A5),A1; LEA 5de0(A5),A2; LEA 5de3(A5),A3; BRA.W b7aa8 / b7a9c: LEA 5de4(A5),A1; LEA 5de8(A5),A2; LEA 5deb(A5),A3.
    case 0xb7a8c:r.a[1]=am_index(r.a[5],0x5ddc);r.a[2]=am_index(r.a[5],0x5de0);r.a[3]=am_index(r.a[5],0x5de3);r.pc=0xb7aa8;return true;
    case 0xb7a9c:r.a[1]=am_index(r.a[5],0x5de4);r.a[2]=am_index(r.a[5],0x5de8);r.a[3]=am_index(r.a[5],0x5deb);r.pc=0xb7aa8;return true;
    // ADDQ.W #1,(A1); CMPI.W #64,(A1); BCS.W b7ab6 (unsigned WORD < 64).
    case 0xb7aa8:
        if(!am_read(c,r.a[1],2,value) || !am_write(c,r.a[1],2,(value+1U)&0xffffU) || !am_read(c,r.a[1],2,value))return false;
        r.pc=value<0x64U?0xb7ab6:0xb7ab2;return true;
    case 0xb7ab2:if(!am_write(c,r.a[1],2,0x63))return false;r.pc=0xb7ab6;return true;              // MOVE.W #63,(A1).
    case 0xb7ab6:if(!ofr10_get(c,r.a[6],0x7c,2,value))return false;r.pc=value!=0xffffU?0xb7ac2:0xb7ac0;return true;   // CMPI.W #ffff,7c(A6); BNE.
    case 0xb7ac0:if(!ofr10_count_byte(c,r.a[2]))return false;r.pc=0xb7ac2;return true;              // ADDQ.B #1,(A2).
    case 0xb7ac2:r.pc=(r.d[1]&0xffU)==0U?0xb7aca:0xb7ac8;return true;                              // TST.B D1; BEQ.W b7aca.
    case 0xb7ac8:if(!ofr10_count_byte(c,r.a[3]))return false;r.pc=0xb7aca;return true;              // ADDQ.B #1,(A3).
    // ---- b7b30 (U19 b7b68 / b7b7c): BTST.B #7,61(A0); BNE.W b7b46.
    case 0xb7b30:return ofr10_btst(c,r.a[0],0x61,7,0xb7b3a,0xb7b46);
    case 0xb7b3a:return am_call(c,0x4941e,0xb7b40);                                                   // JSR 4941e.l.
    // EORI.B #1,CCR; RTS: the known C of 4941e inverted (Unknown is a checked error).
    case 0xb7b40:
        if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr10 caller requires known carry");
        r.carry=c.s.carry==AnimationCarryClear?AnimationCarrySet:AnimationCarryClear;return am_return(c);
    case 0xb7b46:r.carry=AnimationCarryClear;return am_return(c);                                     // ANDI.B #fe,CCR; RTS.
    // ---- the FR4 BRA.W table entries (cc7a8 / cc82a).
    case 0xcc7c4:r.pc=0xcd94e;return true;                                                            // BRA.W cd94e.
    case 0xcc7d0:r.pc=0xcd7c6;return true;                                                            // BRA.W cd7c6.
    case 0xcc846:r.pc=0xccaf8;return true;                                                            // BRA.W ccaf8.
    // ---- cca44 / cca52 (script callbacks, table 4a500): MOVE.W (A0),D0; JSR 49a84.l / MOVE.B D0,77(A6); RTS / BSET.B #4,15(A6); RTS.
    case 0xcca44:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);return am_call(c,0x49a84,0xcca4c);
    case 0xcca4c:if(!ofr10_put(c,r.a[6],0x77,1,r.d[0]))return false;return am_return(c);
    case 0xcca52:if(!ofr10_bit(c,r.a[6],0x15,4,1,old))return false;return am_return(c);
    // ---- ccade (cd93c / cdafc): TST.B 7b(A6) (C Clear); BEQ.W ccaf6.
    case 0xccade:if(!ofr10_get(c,r.a[6],0x7b,1,value))return false;r.carry=AnimationCarryClear;r.pc=value==0U?0xccaf6:0xccae6;return true;
    case 0xccae6:return ofr10_btst(c,r.a[6],0x61,3,0xccaf0,0xccaf6);                                  // BTST.B #3,61(A6); BNE.W ccaf6 (C kept).
    case 0xccaf0:return am_call(c,0x4b54e,0xccaf6);                                                   // JSR 4b54e.l (its C reaches the RTS ccaf6).
    // ---- ccaf8 (cc846): the anim by WORD 8c(A6) 0..4 / other.
    case 0xccaf8:return ofr10_kind(c,0xccb00,0xccb1a);
    case 0xccb00:return ofr10_anim(c,0xce7ac,0xccb16);
    case 0xccb1a:ofr10_select(r,1,0xccb22,0xccb3c);return true;
    case 0xccb22:return ofr10_anim(c,0xcf10e,0xccb38);
    case 0xccb3c:ofr10_select(r,2,0xccb44,0xccb5e);return true;
    case 0xccb44:return ofr10_anim(c,0xd00c8,0xccb5a);
    case 0xccb5e:ofr10_select(r,3,0xccb66,0xccb80);return true;
    case 0xccb66:return ofr10_anim(c,0xcf858,0xccb7c);
    case 0xccb80:ofr10_select(r,4,0xccb88,0xccba2);return true;
    case 0xccb88:return ofr10_anim(c,0xd07e0,0xccb9e);
    case 0xccba2:return ofr10_anim(c,0xd0fd4,0xccbb8);
    case 0xccb16:case 0xccb38:case 0xccb5a:case 0xccb7c:case 0xccb9e:r.pc=0xccbb8;return true;   // BRA.W ccbb8.
    case 0xccbb8:if(!ofr10_put(c,r.a[6],0,4,0xcdd2e))return false;return am_return(c);            // MOVE.L #cdd2e,(A6) (written only); RTS.
    // ---- cd7c6 (cc7d0 / cc950): JSR 49a58.l.
    case 0xcd7c6:case 0xcd8f8:return am_call(c,0x49a58,r.pc+6U);
    // ANDI.L #ffff,D0; LSL.L #2,D0; SUBI.L #10000,D0; TST.B 5f(A6); BPL.W cd7e4 (else the later-unit PC cd7e2).
    case 0xcd7cc:
        r.d[0]=((r.d[0]&0xffffU)<<2)-0x10000U;if(!ofr10_get(c,r.a[6],0x5f,1,value))return false;r.pc=(value&0x80U)==0U?0xcd7e4:0xcd7e2;return true;
    // MOVE.L D0,7e(A6); MOVE.L D0,36(A6); JSR 49a58.l.
    case 0xcd7e4:if(!ofr10_put(c,r.a[6],0x7e,4,r.d[0]) || !ofr10_put(c,r.a[6],0x36,4,r.d[0]))return false;return am_call(c,0x49a58,0xcd7f2);
    // ANDI.L #ffff,D0; LSL.L #3,D0; ADDI.L #40000,D0; MOVE.L D0,3a(A6).
    case 0xcd7f2:r.d[0]=((r.d[0]&0xffffU)<<3)+0x40000U;if(!ofr10_put(c,r.a[6],0x3a,4,r.d[0]))return false;r.pc=0xcd804;return true;
    case 0xcd804:return am_call(c,0x49a58,0xcd80a);                                                   // JSR 49a58.l (also the cd7c2 BRA.W target).
    case 0xcd80a:if(!ofr10_random_negative(c,old))return false;r.pc=old?0xcd80e:0xcd814;return true;   // BPL.W cd814 (N of 49a58, decision 3).
    case 0xcd80e:if(!ofr10_change(c,0))return false;r.pc=0xcd814;return true;                      // BCHG.B #0,15(A6).
    // ANDI.W #3f,D0; ADDI.W #80,D0; MOVE.W D0,2c(A6); MOVE.W 8c(A6),D0; BNE.W cd842.
    case 0xcd814:am_word(r.d[0],(r.d[0]&0x3fU)+0x80U);if(!ofr10_put(c,r.a[6],0x2c,2,r.d[0]))return false;return ofr10_kind(c,0xcd828,0xcd842);
    case 0xcd828:return ofr10_anim(c,0xce5c2,0xcd83e);
    case 0xcd842:ofr10_select(r,1,0xcd84a,0xcd864);return true;
    case 0xcd84a:return ofr10_anim(c,0xcef78,0xcd860);
    case 0xcd864:ofr10_select(r,2,0xcd86c,0xcd886);return true;
    case 0xcd86c:return ofr10_anim(c,0xcf870,0xcd882);
    case 0xcd886:ofr10_select(r,3,0xcd88e,0xcd8a8);return true;
    case 0xcd88e:return ofr10_anim(c,0xcf126,0xcd8a4);
    case 0xcd8a8:ofr10_select(r,4,0xcd8b0,0xcd8ca);return true;
    case 0xcd8b0:return ofr10_anim(c,0xd00e0,0xcd8c6);
    case 0xcd8ca:return ofr10_anim(c,0xd07f8,0xcd8e0);
    case 0xcd83e:case 0xcd860:case 0xcd882:case 0xcd8a4:case 0xcd8c6:r.pc=0xcd8e0;return true;   // BRA.W cd8e0.
    // BCLR.B #7,15(A6); MOVE.L #cd8ee,(A6) (written: the next frame's callback); RTS.
    case 0xcd8e0:if(!ofr10_bit(c,r.a[6],0x15,7,2,old) || !ofr10_put(c,r.a[6],0,4,0xcd8ee))return false;return am_return(c);
    case 0xcd8ee:return ofr10_btst(c,r.a[6],0x15,7,0xcd8f8,0xcd92e);                                  // BTST.B #7,15(A6); BNE.W cd92e.
    // ANDI.W #f,D0; SUBI.W #a,D0; ADD.W 2c(A6),D0; CMPI.W #20,D0; BPL.W cd916 (N of the WORD D0 - 20).
    case 0xcd8fe:
        if(!ofr10_get(c,r.a[6],0x2c,2,value))return false;am_word(r.d[0],(r.d[0]&0xfU)-0xaU+value);
        r.pc=((r.d[0]-0x20U)&0x8000U)==0U?0xcd916:0xcd912;return true;
    case 0xcd912:am_word(r.d[0],0x20);r.pc=0xcd916;return true;                                     // MOVE.W #20,D0.
    // MOVE.W D0,2c(A6); TST.L 3a(A6); BPL.W cd92a.
    case 0xcd916:
        if(!ofr10_put(c,r.a[6],0x2c,2,r.d[0]) || !ofr10_get(c,r.a[6],0x3a,4,value))return false;r.pc=(value&0x80000000U)==0U?0xcd92a:0xcd922;return true;
    case 0xcd922:if(!ofr10_put(c,r.a[6],0x56,4,0xcc5c4))return false;r.pc=0xcd92a;return true;     // MOVE.L #cc5c4,56(A6).
    case 0xcd92a:r.pc=0xcd93c;return true;                                                            // BRA.W cd93c.
    case 0xcd93c:return am_call(c,0xccade,0xcd940);                                                   // JSR ccade(PC).
    case 0xcd940:return ofr10_carry(c,0xcd94a,0xcd944);                                               // BCC.W cd94a (C of ccade).
    case 0xcd944:return ofr10_install(c,0xcdc24,0xcd94a);                                             // MOVE.L #cdc24,(A6) (written only).
    case 0xcd94a:case 0xcdb04:r.pc=0xcdd2e;return true;                                              // BRA.W cdd2e.
    // ---- cd94e (cc7c4): TST.B 76(A6); BNE.W cd95a.
    case 0xcd94e:return ofr10_test(c,0x76,1,0xcd956,0xcd95a);
    case 0xcd956:return am_call(c,0xcdd86,0xcd95a);                                                   // JSR cdd86(PC).
    // MOVE.B 5f(A6),D0; BTST.B #0,15(A6); SNE.B D1; EOR.B D0,D1; BPL.W cda34 (N = bit 7 of the new D1.B; else the later-unit PC cd96c).
    case 0xcd95a:
        if(!ofr10_get(c,r.a[6],0x5f,1,value) || !ofr10_bit(c,r.a[6],0x15,0,0,old))return false;
        am_byte(r.d[0],value);am_byte(r.d[1],old?0xffU:0U);am_byte(r.d[1],r.d[1]^r.d[0]);r.pc=(r.d[1]&0x80U)==0U?0xcda34:0xcd96c;return true;
    case 0xcda34:return ofr10_kind(c,0xcda3c,0xcda56);
    case 0xcda3c:return ofr10_anim(c,0xcdfe6,0xcda52);
    case 0xcda56:ofr10_select(r,1,0xcda5e,0xcda78);return true;
    case 0xcda5e:return ofr10_anim(c,0xce838,0xcda74);
    case 0xcda78:ofr10_select(r,2,0xcda80,0xcda9a);return true;
    case 0xcda80:return ofr10_anim(c,0xcf8e4,0xcda96);
    case 0xcda9a:ofr10_select(r,3,0xcdaa2,0xcdabc);return true;
    case 0xcdaa2:return ofr10_anim(c,0xcf190,0xcdab8);
    case 0xcdabc:ofr10_select(r,4,0xcdac4,0xcdade);return true;
    case 0xcdac4:return ofr10_anim(c,0xd0140,0xcdada);
    case 0xcdade:return ofr10_anim(c,0xd0858,0xcdaf4);
    case 0xcda52:case 0xcda74:case 0xcda96:case 0xcdab8:case 0xcdada:r.pc=0xcdaf4;return true;   // BRA.W cdaf4.
    case 0xcdaf4:if(!ofr10_put(c,r.a[6],0,4,0xcdafc))return false;return am_return(c);            // MOVE.L #cdafc,(A6) (written); RTS.
    case 0xcdafc:return am_call(c,0xccade,0xcdb00);                                                   // JSR ccade(PC) (C not read).
    case 0xcdb00:return am_call(c,0xcc778,0xcdb04);                                                   // BSR.W cc778.
    // ---- cdd86 (cd956; 860c2): BCHG.B #0,15(A6); MOVEA.L #cde6e,A0; MOVE.W #1e,D0; JSR 28ae.l (the 28ae child cde6e).
    case 0xcdd86:if(!ofr10_change(c,0))return false;r.a[0]=0xcde6e;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0xcdd9c);
    case 0xcdd9c:return ofr10_carry(c,0xcddb2,0xcdda0);                                               // BCC.W cddb2 (C of 28ae).
    case 0xcdda0:am_word(r.d[0],8);am_word(r.d[1],0);return am_call(c,0x4970a,0xcddae);            // MOVE.W #8,D0; MOVE.W #0,D1; JSR 4970a.l.
    case 0xcddae:r.carry=AnimationCarrySet;r.pc=0xcddb2;return true;                                 // ORI.B #1,CCR (no reader after the RTS).
    case 0xcddb2:if(!ofr10_change(c,0))return false;return am_return(c);                            // BCHG.B #0,15(A6); RTS.
    // ---- cde6e (the 28ae child of cdd86): the bank anim #e2 (window 200094, LONG 3c) -> the routed cde96.
    case 0xcde6e:return ofr10_bank_anim(c,0xe2,0x200094,0x3c,0xcde96);
    // ---- eaa00 (U18 ea9e4 install): LEA ea732(PC),A1; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0;
    // JSR 49f8c.l.
    case 0xeaa00:
        r.a[1]=0xea732;if(!ofr10_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        if(!ofr10_get(c,r.a[1],r.d[0],4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xeaa1a);
    case 0xeaa1a:return ofr10_install(c,0xeaa20,0xeaa20);                                             // MOVE.L #eaa20,(A6) (next PC).
    case 0xeaa20:case 0xeab2a:return am_call(c,0x43e34,r.pc+6U);                                    // JSR 43e34.l.
    // ANDI.B #fe,CCR (C Clear); BCLR.B #7,5e50(A5); BNE.W eaa3a (the old bit set; C Clear reaches the consumer eaa3a).
    case 0xeaa26:
        r.carry=AnimationCarryClear;if(!ofr10_bit(c,r.a[5],0x5e50,7,2,old))return false;r.pc=old?0xeaa3a:0xeaa34;return true;
    case 0xeaa34:return am_call(c,0x49fc6,0xeaa3a);                                                   // JSR 49fc6.l.
    case 0xeaa3a:return ofr10_carry(c,0xeaa44,0xeaa3e);                                               // BCC.W eaa44 (C of eaa26 / 49fc6).
    case 0xeaa3e:return ofr10_install(c,0xea824,0xeaa44);                                             // MOVE.L #ea824,(A6) (written only).
    case 0xeaa44:return ofr10_test(c,0x78,1,0xeaa52,0xeaa4c);                                         // TST.B 78(A6); BEQ.W eaa52.
    case 0xeaa4c:return ofr10_install(c,0xea85a,0xeaa52);                                             // MOVE.L #ea85a,(A6) (written only).
    // ---- eaac0 (the 28ae child of C9 20cd8 / 20d44, FR3 ea6d4): JSR 1abda.l; BCS.W eaad0 / JMP 2a00.l.
    case 0xeaac0:return am_call(c,0x1abda,0xeaac6);
    case 0xeaac6:return ofr10_carry(c,0xeaaca,0xeaad0);                                               // BCS.W eaad0 (C of 1abda).
    case 0xeaad0:am_word(r.d[0],r.d[1]);r.d[1]=0;return am_call(c,0x8ebe,0xeaada);                  // MOVE.W D1,D0; MOVEQ #0,D1; JSR 8ebe.l.
    // MOVE.W #e2,20(A6); LEA eaa5c(PC),A0; LEA eaa5c(PC),A1; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0;
    // JSR 49f8c.l.
    case 0xeaada:
        if(!ofr10_put(c,r.a[6],0x20,2,0xe2))return false;r.a[0]=0xeaa5c;r.a[1]=0xeaa5c;if(!ofr10_get(c,r.a[6],0x76,2,value))return false;
        am_word(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);if(!ofr10_get(c,r.a[1],r.d[0],4,value))return false;
        r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xeaafe);
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); MOVE.W #4,D0; SUB.W 76(A6),D0; LSL.W #2,D0; ADDI.W #100,D0; MOVE.W D0,2c(A6); CLR.L 36(A6);
    // CLR.L 3a(A6); MOVE.L #eab2a,(A6) (next PC).
    case 0xeaafe:
        if(!ofr10_put(c,r.a[6],0x68,2,0x1001) || !ofr10_put(c,r.a[6],0x1e,2,0x1001) || !ofr10_get(c,r.a[6],0x76,2,value))return false;
        am_word(r.d[0],4U-value);am_word(r.d[0],(r.d[0]<<2)+0x100U);
        if(!ofr10_put(c,r.a[6],0x2c,2,r.d[0]) || !ofr10_put(c,r.a[6],0x36,4,0) || !ofr10_put(c,r.a[6],0x3a,4,0))return false;
        return ofr10_install(c,0xeab2a,0xeab2a);
    case 0xeab36:return ofr10_carry(c,0xeab40,0xeab3a);                                               // BCC.W eab40 (C of 49fc6).
    default:return am_error(c,"unsupported animation objects fr10 PC");
    }
}
}
