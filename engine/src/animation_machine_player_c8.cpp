#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc8_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc8_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR / BCHG #bit,<memory BYTE> (bit modulo 8). op 0 tests, 1 sets, 2 clears, 3 changes; old is the bit before (Z = old is 0).
bool pc8_bit(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    std::uint32_t next=value&~mask;
    if(op==1U || (op==3U && !old))next=value|mask;
    return am_write(c,address,1,next);
}
// BTST #bit,d16(A6); BEQ.W zero_pc (the bit clear) / other_pc.
bool pc8_field_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t other_pc) {
    bool old=false;if(!pc8_bit(c,am_index(c.s.a[6],displacement),bit,0,old))return false;
    c.s.pc=old?other_pc:zero_pc;return true;
}
// BTST #bit,D0 (a register operand: the LONG bit); BEQ.W zero_pc / other_pc.
void pc8_input_bit(AnimationMachineState& r,unsigned int bit,std::uint32_t zero_pc,std::uint32_t other_pc) {
    r.pc=(r.d[0]&(1U<<bit))==0U?zero_pc:other_pc;
}
// TST.B / CMPI.B #0,d16(A6); BEQ.W zero_pc / other_pc.
bool pc8_byte_zero(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc8_get(c,c.s.a[6],displacement,1,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// MOVE.W #c,D1; AND.W D0,D1 (WORD: D1 bits 16..31 kept); BNE.W other_pc / zero_pc.
void pc8_mask_c(AnimationMachineState& r,std::uint32_t zero_pc,std::uint32_t other_pc) {
    am_word(r.d[1],0xcU);am_word(r.d[1],r.d[1]&r.d[0]);r.pc=(r.d[1]&0xffffU)==0U?zero_pc:other_pc;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc8_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c8 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W d16(A6),D0 (D0 bits 16..31 kept); JSR target.
bool pc8_field_call(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc8_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MOVE.L #v,(A6): the node callback LONG.
bool pc8_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc8_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #21602,84(A6); MOVE.B #0,9c(A6); MOVE.B #1,aa(A6); CLR.W 7a(A6); MOVE.B #a9,a9(A6) (the slot part of 1f3f0 / 1fcd4).
bool pc8_slot(AnimationMachineContext& c,std::uint32_t a9) {
    const std::uint32_t a6=c.s.a[6];
    return pc8_put(c,a6,0x84,4,0x21602) && pc8_put(c,a6,0x9c,1,0) && pc8_put(c,a6,0xaa,1,1) && pc8_put(c,a6,0x7a,2,0) && pc8_put(c,a6,0xa9,1,a9);
}
// ASR.L Dn,Dm: the count is Dn modulo 64 (68000: the low 6 bits of the register); a count of 32 or more leaves only the sign; written without a
// signed shift (no implementation-defined right shift of a negative value).
std::uint32_t pc8_asr(std::uint32_t value,std::uint32_t count_register) {
    const unsigned int count=static_cast<unsigned int>(count_register&63U);
    if(count==0U)return value;
    const bool negative=(value&0x80000000U)!=0U;
    if(count>=32U)return negative?0xffffffffU:0U;
    const std::uint32_t shifted=value>>count;
    return negative?(shifted|(0xffffffffU<<(32U-count))):shifted;
}
// The handlers of the (handler LONG, key WORD) list 21b0a that C3 215e6 matched for C4 21d92 (contract decision 2; JMP (A1) 21d9e) and of the list
// 21b3c that 215e6 matched for C8 21e6a (JMP (A1) 21e76).  ROM bytes: 21b0a (21602,0) (21c22,1) (21e48,3) (21e3a,4) 0; 21b3c (21602,0) (21c22,1)
// (21d60,2) 0.  21e48 is not routed: the next dispatch is the 'unsupported animation machine PC' declared stop.
const std::uint32_t PC8_LIST_21B0A[4]={0x21602,0x21c22,0x21e48,0x21e3a};
const std::uint32_t PC8_LIST_21B3C[3]={0x21602,0x21c22,0x21d60};
// JMP (A1) (contract decision 2): A1 one of the list handlers (the LONG that 215e6 loaded with MOVEA.L (A0)+,A1), else the checked jump-target error.
bool pc8_list_jump(AnimationMachineContext& c,const std::uint32_t* list,unsigned int count) {
    for(unsigned int i=0;i<count;++i)if(list[i]==c.s.a[1]){c.s.pc=c.s.a[1];return true;}
    return am_error(c,"unsupported animation player c8 jump target");
}
}
// Player C8 (99 block starts, contract docs/analysis/animation-machine-player-c8-contract.md; area C plan unit C8 = the re-measured closure (98) and the
// callback 1fcd4 that C6 1dbca installs, contract decision 1; demo-only code of the IO observation): the player states 1f3d8 -> 1f3ec -> 1f418 (1cab6,
// 1cd98, 4bfc0 ce02 49fc6, 201a2; installed by 1f756 after C7 1f752), 1fa68 -> 1fafc -> 1fb02 (1cb08, 1cab6, the motion helpers 1cfde / 1cff8 / 1d066
// on the LONGs 36 / 3a(A6): ASR.L, 4be82), 201bc -> 1fcce / 1fcd4 -> 1fd12 (ea626, 4de7a, the record helper 4d1ac: MOVEM.L D0-D3/A1,2e(A6), 43e34;
// 484b4), the C3 helper tail 4d0cc (484b4), the C4 input branch 1ef4c, 1eb98, 1ce98, and the slot-84 state 21e3a -> 21e52 -> 21e6a (215e6 list 21b3c,
// JMP (A1) 21e76) with the JMP (A1) 21d9e of C4 21d92 (list 21b0a).
// C: the 5 consumers 1f47c (BCC, 49fc6), 1fa70 (BCS, 1cb08), 1fd34 4d0e6 (BCC, 484b4), 21e72 (BCC, 215e6) read a known C or fail; 4d0ea Set (ORI.B
// #1,CCR; RTS; read by C3 201b8); 4d0f6 falls into the C3 Clear block 4d100.  No other C or Z crosses a block boundary.
bool animation_player_c8_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool old=false;
    switch(r.pc) {
    // ---- 1ce98 (C2 1ce94 BEQ fall-through): BTST.B #0,15(A6); BNE.W 1cea8 / BSET.B #3,a7(A6) (falls into C2 1cea8).
    case 0x1ce98:return pc8_field_bit(c,0x15,0,0x1cea2,0x1cea8);
    case 0x1cea2:if(!pc8_bit(c,am_index(r.a[6],0xa7),3,1,old))return false;r.pc=0x1cea8;return true;
    // ---- 1cfde (BSR from 1fa7c and C2 1fa4c 1fac4): CMPI.B #8,6e(A6); BEQ.W 1cfec / CLR.L 3a(A6) / BSR.B 1cfbe (C4: A0 = the record LONG of
    // the fixed ROM table 1cfce + 4 x BYTE 9e) / MOVE.L 10(A0),D0; ADD.L D0,3a(A6); RTS.
    case 0x1cfde:if(!pc8_get(c,r.a[6],0x6e,1,value))return false;r.pc=value==8U?0x1cfec:0x1cfe8;return true;
    case 0x1cfe8:if(!pc8_put(c,r.a[6],0x3a,4,0))return false;r.pc=0x1cfec;return true;
    case 0x1cfec:case 0x1cff8:return am_call(c,0x1cfbe,r.pc+2U);                                         // BSR.B 1cfbe.
    case 0x1cfee:
        if(!pc8_get(c,r.a[0],0x10,4,r.d[0]) || !pc8_get(c,r.a[6],0x3a,4,value) || !pc8_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;
        return am_return(c);
    // ---- 1cff8 (BSR from 1fb06 and the later 1ff1e): BSR.B 1cfbe / MOVE.L 18(A0),D1; MOVE.W #5,D2; SUB.L 3a(A6),D1; ASR.L D2,D1; ADD.L D1,3a(A6);
    // MOVEQ #0,D1; BTST.B #0,61(A6); BNE.W 1d01c / MOVE.L 14(A0),D1 / MOVEQ #0,D7; BTST.B #2,D0; BEQ.W 1d02c / SUB.L D1,D7; MOVE.W #2,D2 / BTST.B
    // #3,D0; BEQ.W 1d03a / ADD.L D1,D7; MOVE.W #2,D2 / SUB.L 36(A6),D7; ASR.L D2,D7; ADD.L D7,36(A6); BTST.B #3,a7(A6); BEQ.W 1d064 / MOVE.W #50,D1;
    // AND.W D0,D1; BEQ.W 1d064 / BCHG.B #0,15(A6); BCLR.B #3,a7(A6) / RTS.  (LONG arithmetic modulo 2^32; D2 bits 16..31 kept by MOVE.W.)
    case 0x1cffa:
        if(!pc8_get(c,r.a[0],0x18,4,r.d[1]) || !pc8_get(c,r.a[6],0x3a,4,value))return false;
        am_word(r.d[2],5);r.d[1]=pc8_asr(r.d[1]-value,r.d[2]);
        if(!pc8_put(c,r.a[6],0x3a,4,value+r.d[1]))return false;r.d[1]=0;
        return pc8_field_bit(c,0x61,0,0x1d018,0x1d01c);
    case 0x1d018:if(!pc8_get(c,r.a[0],0x14,4,r.d[1]))return false;r.pc=0x1d01c;return true;
    case 0x1d01c:r.d[7]=0;pc8_input_bit(r,2,0x1d02c,0x1d026);return true;
    case 0x1d026:r.d[7]-=r.d[1];am_word(r.d[2],2);r.pc=0x1d02c;return true;
    case 0x1d02c:pc8_input_bit(r,3,0x1d03a,0x1d034);return true;
    case 0x1d034:r.d[7]+=r.d[1];am_word(r.d[2],2);r.pc=0x1d03a;return true;
    case 0x1d03a:
        if(!pc8_get(c,r.a[6],0x36,4,value))return false;r.d[7]=pc8_asr(r.d[7]-value,r.d[2]);
        if(!pc8_put(c,r.a[6],0x36,4,value+r.d[7]))return false;return pc8_field_bit(c,0xa7,3,0x1d064,0x1d04e);
    case 0x1d04e:am_word(r.d[1],0x50U);am_word(r.d[1],r.d[1]&r.d[0]);r.pc=(r.d[1]&0xffffU)==0U?0x1d064:0x1d058;return true;
    case 0x1d058:
        if(!pc8_bit(c,am_index(r.a[6],0x15),0,3,old) || !pc8_bit(c,am_index(r.a[6],0xa7),3,2,old))return false;r.pc=0x1d064;return true;
    case 0x1d064:case 0x1d084:case 0x4d206:return am_return(c);                                          // RTS.
    // ---- 1d066 (BSR from 1fb0a and the later 1dfa6 1ff30): MOVE.L 3a(A6),-(A7); JSR 4be82.l / MOVE.L (A7)+,D0; BMI.W 1d084 (N of the LONG) / BTST.B
    // #1,61(A6); BNE.W 1d084 / MOVE.L D0,3a(A6) / RTS.
    case 0x1d066:if(!pc8_get(c,r.a[6],0x3a,4,value) || !am_push(c,4,value))return false;return am_call(c,0x4be82,0x1d070);
    case 0x1d070:if(!am_pop(c,4,r.d[0]))return false;r.pc=(r.d[0]&0x80000000U)!=0U?0x1d084:0x1d076;return true;
    case 0x1d076:return pc8_field_bit(c,0x61,1,0x1d080,0x1d084);
    case 0x1d080:if(!pc8_put(c,r.a[6],0x3a,4,r.d[0]))return false;r.pc=0x1d084;return true;
    // ---- 1eb98 (BEQ.W from C7 1f59a 1f724, C8 1f448 and the later 1f39e 1f4e6): LEA 1b328(PC),A0; BRA.W 1ebbe (C6).
    case 0x1eb98:r.a[0]=0x1b328;r.pc=0x1ebbe;return true;
    // ---- 1ef4c (C4 1ef44 BTST.B #5,D0 fall-through): CMPI.B #0,9e(A6); BNE.W 1ef5e / BTST.B #1,D0; BNE.W 1f7a4 / MOVE.W #c,D1; AND.W D0,D1; BNE.W
    // 1fa68 / BRA.W 1fa3c.
    case 0x1ef4c:return pc8_byte_zero(c,0x9e,0x1ef56,0x1ef5e);
    case 0x1ef56:pc8_input_bit(r,1,0x1ef5e,0x1f7a4);return true;
    case 0x1ef5e:pc8_mask_c(r,0x1ef68,0x1fa68);return true;
    case 0x1ef68:r.pc=0x1fa3c;return true;
    // ---- 1f3d8 (installed by 1f756): LEA 1b2ae(PC),A0; BRA.W 1f3ec / BSR.W 1cab6 / the slot part (LONG 84 := 21602, 9c := 0, aa := 1, WORD 7a := 0,
    // a9 := 2); CLR.L 64(A6); MOVE.L #1f418,(A6) / 1f418: BSR.W 1cd98 / BTST.B #7,15(A6); BEQ.W 1fad2 / BTST.B #5,D0; BEQ.W 1f444 / CMPI.B #0,9e(A6);
    // BNE.W 1f440 / BTST.B #1,D0; BNE.W 1f7a4 / BRA.W 1f76e / BTST.B #1,D0; BEQ.W 1eb98 / BTST.B #6,D0; BNE.W 1f5d2 / BTST.B #4,D0; BNE.W 1f5f2 /
    // MOVE.W #c,D1; AND.W D0,D1; BNE.W 1f48a (deferred, C11) / JSR 4bfc0.l / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l / BCC.W 1f486 (C of 49fc6) /
    // MOVE.L #1f3e8,(A6) (written only) / BRA.W 201a2.
    case 0x1f3d8:r.a[0]=0x1b2ae;r.pc=0x1f3ec;return true;
    case 0x1f3ec:return am_call(c,0x1cab6,0x1f3f0);                                                       // BSR.W 1cab6.
    case 0x1f3f0:if(!pc8_slot(c,2) || !pc8_put(c,r.a[6],0x64,4,0))return false;return pc8_install(c,0x1f418,0x1f418);
    case 0x1f418:case 0x1fb02:case 0x21e78:return am_call(c,0x1cd98,r.pc+4U);                           // BSR.W 1cd98.
    case 0x1f41c:return pc8_field_bit(c,0x15,7,0x1fad2,0x1f426);
    case 0x1f426:pc8_input_bit(r,5,0x1f444,0x1f42e);return true;
    case 0x1f42e:return pc8_byte_zero(c,0x9e,0x1f438,0x1f440);
    case 0x1f438:pc8_input_bit(r,1,0x1f440,0x1f7a4);return true;
    case 0x1f440:r.pc=0x1f76e;return true;
    case 0x1f444:pc8_input_bit(r,1,0x1eb98,0x1f44c);return true;
    case 0x1f44c:pc8_input_bit(r,6,0x1f454,0x1f5d2);return true;
    case 0x1f454:pc8_input_bit(r,4,0x1f45c,0x1f5f2);return true;
    case 0x1f45c:pc8_mask_c(r,0x1f466,0x1f48a);return true;
    case 0x1f466:return am_call(c,0x4bfc0,0x1f46c);
    case 0x1f46c:case 0x1fb0e:return pc8_field_call(c,0x1e,0xce02,r.pc+0xaU);                           // MOVE.W 1e(A6),D0; JSR ce02.l.
    case 0x1f476:case 0x1fb18:return am_call(c,0x49fc6,r.pc+6U);                                         // JSR 49fc6.l.
    case 0x1f47c:return pc8_carry(c,0x1f486,0x1f480);
    case 0x1f480:return pc8_install(c,0x1f3e8,0x1f486);
    case 0x1f486:case 0x1fb2e:case 0x1fd38:r.pc=0x201a2;return true;                                     // BRA.W 201a2.
    // ---- 1f756 (C7 1f752 BCC fall-through): MOVE.L #1f3d8,(A6); TST.B 88(A6); BEQ.W 1f76a (C7) / MOVE.L #1f3e0,(A6) (written only; falls into 1f76a).
    case 0x1f756:if(!pc8_put(c,r.a[6],0,4,0x1f3d8))return false;return pc8_byte_zero(c,0x88,0x1f76a,0x1f764);
    case 0x1f764:return pc8_install(c,0x1f3e0,0x1f76a);
    // ---- 1fa68 (BNE.W from C6 1ec24, C2 1edde, C3 1f194, C7 1f302, C8 1ef64 and the later 1ece6 1f012 1f0dc): LEA 1b716(PC),A0; BSR.W 1cb08 /
    // BCS.W 1fa90 (C of 1cb08) / LEA 1b74a(PC),A0; BSR.W 1cab6 / BSR.W 1cfde / MOVE.B #4,9c(A6); MOVE.B #1,a9(A6); BRA.W 1fafc / MOVE.L #1fb02,(A6) /
    // 1fb02: BSR.W 1cd98 / BSR.W 1cff8 / BSR.W 1d066 / MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l / BTST.B #7,15(A6); BEQ.W 1fb2e / (1fb28, deferred,
    // C11) / BRA.W 201a2.
    case 0x1fa68:r.a[0]=0x1b716;return am_call(c,0x1cb08,0x1fa70);
    case 0x1fa70:return pc8_carry(c,0x1fa74,0x1fa90);
    case 0x1fa74:r.a[0]=0x1b74a;return am_call(c,0x1cab6,0x1fa7c);
    case 0x1fa7c:return am_call(c,0x1cfde,0x1fa80);
    case 0x1fa80:if(!pc8_put(c,r.a[6],0x9c,1,4) || !pc8_put(c,r.a[6],0xa9,1,1))return false;r.pc=0x1fafc;return true;
    case 0x1fafc:return pc8_install(c,0x1fb02,0x1fb02);
    case 0x1fb06:return am_call(c,0x1cff8,0x1fb0a);
    case 0x1fb0a:return am_call(c,0x1d066,0x1fb0e);
    case 0x1fb1e:return pc8_field_bit(c,0x15,7,0x1fb2e,0x1fb28);
    // ---- 1fcce (installed by 201c6): MOVE.W #8,90(A6) / 1fcd4 (installed by C6 1dbca): BCLR.B #7,61(A6); CLR.B 5e(A6); MOVE.B #ff,82(A6); MOVE.B
    // #ff,81(A6); CLR.L 56(A6); the slot part (a9 := 0); MOVE.L #1fd12,(A6) / 1fd12: JSR ea626.l / BSET.B #3,a8(A6); MOVE.W 78(A6),D0; JSR 4de7a.l /
    // JSR 4d1ac.l / JSR 484b4.l / BCC.W 1fd3c (C of 484b4; deferred, C11) / BRA.W 201a2.
    case 0x1fcce:if(!pc8_put(c,r.a[6],0x90,2,8))return false;r.pc=0x1fcd4;return true;
    case 0x1fcd4:
        if(!pc8_bit(c,am_index(r.a[6],0x61),7,2,old) || !pc8_put(c,r.a[6],0x5e,1,0) || !pc8_put(c,r.a[6],0x82,1,0xff) ||
           !pc8_put(c,r.a[6],0x81,1,0xff) || !pc8_put(c,r.a[6],0x56,4,0) || !pc8_slot(c,0))return false;
        return pc8_install(c,0x1fd12,0x1fd12);
    case 0x1fd12:return am_call(c,0xea626,0x1fd18);
    case 0x1fd18:if(!pc8_bit(c,am_index(r.a[6],0xa8),3,1,old))return false;return pc8_field_call(c,0x78,0x4de7a,0x1fd28);
    case 0x1fd28:return am_call(c,0x4d1ac,0x1fd2e);
    case 0x1fd2e:return am_call(c,0x484b4,0x1fd34);
    case 0x1fd34:return pc8_carry(c,0x1fd3c,0x1fd38);
    // ---- 201bc (the Set side of C3 201b8 BCC, C of 4d0a4): BSET.B #7,a7(A6); BNE.W 201cc / MOVE.L #1fcce,(A6) / BRA.W 201da (C3).
    case 0x201bc:if(!pc8_bit(c,am_index(r.a[6],0xa7),7,1,old))return false;r.pc=old?0x201cc:0x201c6;return true;
    case 0x201c6:return pc8_install(c,0x1fcce,0x201cc);
    case 0x201cc:r.pc=0x201da;return true;
    // ---- 21d9e (the Set side of C4 21d9a BCC, C of 215e6 on the list 21b0a): JMP (A1) (contract decision 2).
    case 0x21d9e:return pc8_list_jump(c,PC8_LIST_21B0A,4U);
    // ---- 21e3a (a handler of the lists 21622 / 21aee / 21b26 / 21b0a): MOVE.B #1,aa(A6); LEA 1b9c6(PC),A0; BRA.W 21e52 / TST.B 9d(A6); BGT.W 21ea0
    // (deferred, C12; signed BYTE) / BLT.W 21d0e (deferred, C12; the second Bcc of the same TST) / BSR.W 1cabe / MOVE.L #21e6a,84(A6) (slot 84, entered
    // at once) / LEA 21b3c(PC),A0; BSR.W 215e6 / BCC.W 21e78 (C of 215e6) / JMP (A1) / BSR.W 1cd98 / BTST.B #0 / #1 / #6 / #4,D0; BNE.W 223a0 (C13) /
    // 223d6 (C13) / 21ffc / 2210c (C12) / BRA.W 2156a.
    case 0x21e3a:if(!pc8_put(c,r.a[6],0xaa,1,1))return false;r.a[0]=0x1b9c6;r.pc=0x21e52;return true;
    case 0x21e52:
        if(!pc8_get(c,r.a[6],0x9d,1,value))return false;
        r.pc=value==0U?0x21e5e:((value&0x80U)!=0U?0x21d0e:0x21ea0);return true;
    case 0x21e5e:return am_call(c,0x1cabe,0x21e62);
    case 0x21e62:if(!pc8_put(c,r.a[6],0x84,4,0x21e6a))return false;r.pc=0x21e6a;return true;
    case 0x21e6a:r.a[0]=0x21b3c;return am_call(c,0x215e6,0x21e72);
    case 0x21e72:return pc8_carry(c,0x21e78,0x21e76);
    case 0x21e76:return pc8_list_jump(c,PC8_LIST_21B3C,3U);
    case 0x21e7c:pc8_input_bit(r,0,0x21e84,0x223a0);return true;
    case 0x21e84:pc8_input_bit(r,1,0x21e8c,0x223d6);return true;
    case 0x21e8c:pc8_input_bit(r,6,0x21e94,0x21ffc);return true;
    case 0x21e94:pc8_input_bit(r,4,0x21e9c,0x2210c);return true;
    case 0x21e9c:r.pc=0x2156a;return true;
    // ---- 4d0cc (C3 4d0ba BNE.W, the WORD (A4) not 0): TST.B 22(A4); BEQ.W 4d0f6 / MOVE.W 18(A4),D0; CMP.W -7ff2(A5),D0; BNE.W 4d0f6 / JSR 484b4.l /
    // BCC.W 4d0f6 (C of 484b4) / MOVE.B #0,22(A4); ORI.B #1,CCR; RTS / MOVE.W #0,(A4); MOVE.B #1,22(A4) (falls into C3 4d100: ANDI.B #fe,CCR; RTS).
    case 0x4d0cc:if(!pc8_get(c,r.a[4],0x22,1,value))return false;r.pc=value==0U?0x4d0f6:0x4d0d4;return true;
    case 0x4d0d4:
        if(!pc8_get(c,r.a[4],0x18,2,value) || !pc8_get(c,r.a[5],0x800eU,2,other))return false;am_word(r.d[0],value);
        r.pc=value==other?0x4d0e0:0x4d0f6;return true;
    case 0x4d0e0:return am_call(c,0x484b4,0x4d0e6);
    case 0x4d0e6:return pc8_carry(c,0x4d0f6,0x4d0ea);
    case 0x4d0ea:if(!pc8_put(c,r.a[4],0x22,1,0))return false;r.carry=AnimationCarrySet;return am_return(c);
    case 0x4d0f6:if(!pc8_put(c,r.a[4],0,2,0) || !pc8_put(c,r.a[4],0x22,1,1))return false;r.pc=0x4d100;return true;
    // ---- 4d1ac (JSR from 1fd28): TST.W 78(A6); BNE.W 4d1bc / LEA 5cba(A5),A4; BRA.W 4d1c0 / LEA 5ce6(A5),A4 / TST.W (A4); BEQ.W 4d206 / MOVE.B
    // 28(A4),D0; MOVE.B #81,D1; AND.B D1,D0; NOT.B D1; AND.B D1,15(A6); OR.B D0,15(A6); MOVEA.L c(A4),A1; MOVEQ #0,D0; MOVEQ #0,D1; MOVE.W 2(A4),D0;
    // MOVE.W 4(A4),D1; SWAP D0; SWAP D1; ADD.L 10(A4),D0; ADD.L 14(A4),D1; MOVEQ #0,D2; MOVEQ #0,D3; MOVEM.L D0-D3/A1,2e(A6) (the LONGs 2e 32 36 3a
    // 3e in register order); JSR 43e34.l / RTS.
    case 0x4d1ac:if(!pc8_get(c,r.a[6],0x78,2,value))return false;r.pc=value!=0U?0x4d1bc:0x4d1b4;return true;
    case 0x4d1b4:r.a[4]=am_index(r.a[5],0x5cba);r.pc=0x4d1c0;return true;
    case 0x4d1bc:r.a[4]=am_index(r.a[5],0x5ce6);r.pc=0x4d1c0;return true;
    case 0x4d1c0:if(!am_read(c,r.a[4],2,value))return false;r.pc=value==0U?0x4d206:0x4d1c6;return true;
    case 0x4d1c6:
        if(!pc8_get(c,r.a[4],0x28,1,value))return false;am_byte(r.d[0],value);am_byte(r.d[1],0x81U);am_byte(r.d[0],r.d[0]&r.d[1]);
        am_byte(r.d[1],~r.d[1]);
        if(!pc8_get(c,r.a[6],0x15,1,value) || !pc8_put(c,r.a[6],0x15,1,value&r.d[1]) || !pc8_get(c,r.a[6],0x15,1,value) ||
           !pc8_put(c,r.a[6],0x15,1,value|(r.d[0]&0xffU)) || !pc8_get(c,r.a[4],0xc,4,r.a[1]))return false;
        r.d[0]=0;r.d[1]=0;
        if(!pc8_get(c,r.a[4],2,2,value))return false;am_word(r.d[0],value);
        if(!pc8_get(c,r.a[4],4,2,value))return false;am_word(r.d[1],value);
        am_swap(r.d[0]);am_swap(r.d[1]);
        if(!pc8_get(c,r.a[4],0x10,4,value))return false;r.d[0]+=value;
        if(!pc8_get(c,r.a[4],0x14,4,value))return false;r.d[1]+=value;
        r.d[2]=0;r.d[3]=0;
        if(!pc8_put(c,r.a[6],0x2e,4,r.d[0]) || !pc8_put(c,r.a[6],0x32,4,r.d[1]) || !pc8_put(c,r.a[6],0x36,4,r.d[2]) ||
           !pc8_put(c,r.a[6],0x3a,4,r.d[3]) || !pc8_put(c,r.a[6],0x3e,4,r.a[1]))return false;
        return am_call(c,0x43e34,0x4d206);
    // ---- ea626 (JSR from 1fd12 and C6 1dad8 1dc2a 1dd00 1dd54, the later 1d764 1dc00 1de4c): MOVE.B #ff,5e50(A5); RTS (no caller reads its flags).
    case 0xea626:if(!pc8_put(c,r.a[5],0x5e50,1,0xff))return false;return am_return(c);
    default:return am_error(c,"unsupported animation player c8 PC");
    }
}
}
