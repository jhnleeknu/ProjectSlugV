#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr4_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ofr4_b(std::uint32_t value) {return value&255U;}
// Signed value of the low WORD (for BLE on CMPI.W).
int ofr4_sw(std::uint32_t value) {const int v=static_cast<int>(value&65535U);return v>=32768?v-65536:v;}
bool ofr4_negative(std::uint32_t value) {return (value&0x80000000U)!=0U;}
bool ofr4_negative_word(std::uint32_t value) {return (value&0x8000U)!=0U;}
// ASR.L #count (1..31) of a 32-bit value: arithmetic, the sign bit is replicated (no signed shift in C++).
std::uint32_t ofr4_asr_long(std::uint32_t value,unsigned int count) {
    const std::uint32_t fill=ofr4_negative(value)?~(0xffffffffU>>count):0U;return (value>>count)|fill;
}
// ASR.W #1,Dn: the low WORD shifted right by one with its sign bit kept; the upper WORD of Dn stays.
void ofr4_asr_word1(std::uint32_t& r) {const std::uint32_t w=ofr4_w(r);am_word(r,(w>>1)|(w&0x8000U));}
bool ofr4_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr4_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG) whose fall-through is the installed callback itself: enter it.
bool ofr4_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ofr4_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVE.L #value,(A6) that only writes the callback LONG for a later frame (contract decision 4); then next_pc.
bool ofr4_callback(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr4_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// BCC / BCS on a known C (returned by a callee): clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ofr4_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr4 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// BTST.B #bit,d(An); BEQ.W zero_pc (bit clear); otherwise set_pc.
bool ofr4_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!ofr4_get(c,base,displacement,1,value))return false;c.s.pc=((value>>bit)&1U)==0U?zero_pc:set_pc;return true;
}
// TST.W / TST.B d(An); BNE.W nonzero_pc (otherwise zero_pc).
bool ofr4_test(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t nonzero_pc) {
    std::uint32_t value=0;if(!ofr4_get(c,base,displacement,size,value))return false;c.s.pc=value!=0U?nonzero_pc:zero_pc;return true;
}
// TST.W / TST.L d(A6); BPL.W plus_pc (sign bit clear), otherwise minus_pc.
bool ofr4_sign(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t plus_pc,std::uint32_t minus_pc) {
    std::uint32_t value=0;if(!ofr4_get(c,c.s.a[6],displacement,size,value))return false;
    const bool negative=size==2?ofr4_negative_word(value):ofr4_negative(value);c.s.pc=negative?minus_pc:plus_pc;return true;
}
// BSET / BCLR / BCHG.B #bit,d(An) (mode 0 / 1 / 2); old = the tested bit (the Z of the instruction is old == 0).
bool ofr4_set_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int mode,std::uint32_t& old) {
    std::uint32_t value=0;if(!ofr4_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;old=(value>>bit)&1U;
    const std::uint32_t next=mode==0U?(value|mask):(mode==1U?(value&~mask):(value^mask));
    return ofr4_put(c,base,displacement,1,next);
}
// SUBQ.W #1,d(A6); BCC.W no_borrow_pc (the old WORD was not 0), otherwise borrow_pc.
bool ofr4_count(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t no_borrow_pc,std::uint32_t borrow_pc) {
    std::uint32_t value=0;if(!ofr4_get(c,c.s.a[6],displacement,2,value) || !ofr4_put(c,c.s.a[6],displacement,2,value-1U))return false;
    c.s.pc=value!=0U?no_borrow_pc:borrow_pc;return true;
}
// NEG.L d(A6).
bool ofr4_neg_long(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t value=0;return ofr4_get(c,c.s.a[6],displacement,4,value) && ofr4_put(c,c.s.a[6],displacement,4,0U-value);
}
// ADDI.L #value,d(A6) (SUBI.L as the two's complement).
bool ofr4_add_long(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t addend) {
    std::uint32_t value=0;return ofr4_get(c,c.s.a[6],displacement,4,value) && ofr4_put(c,c.s.a[6],displacement,4,value+addend);
}
// MOVE.W #value,68(A6); MOVE.W #value,1e(A6).
bool ofr4_words68(AnimationMachineContext& c,std::uint32_t value) {
    return ofr4_put(c,c.s.a[6],0x68,2,value) && ofr4_put(c,c.s.a[6],0x1e,2,value);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus).
bool ofr4_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr4_put(c,c.s.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr4_put(c,c.s.a[6],0x22,4,value))return false;
    am_word(c.s.d[0],0x100);c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr4_get(c,c.s.a[6],0x22,4,value))return false;c.s.a[1]=value;
    if(!ofr4_get(c,c.s.a[1],displacement,4,value))return false;c.s.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #d0,D0; MOVE.W #d1,D1; MOVE.B #0,D2; JSR c6a96.l.
bool ofr4_c6a96(AnimationMachineContext& c,std::uint32_t d0,std::uint32_t d1,std::uint32_t return_pc) {
    am_word(c.s.d[0],d0);am_word(c.s.d[1],d1);am_byte(c.s.d[2],0);return am_call(c,0xc6a96,return_pc);
}
// MOVE.B #ff,17(A6); LEA args.l,A0; MOVEA.L window.l,A1; MOVE.W #d1,D1; MOVE.W #d2,D2; JMP cc778.l (the bank-window LONG read through the live bus).
bool ofr4_hit(AnimationMachineContext& c,std::uint32_t args,std::uint32_t window,std::uint32_t d1,std::uint32_t d2) {
    std::uint32_t value=0;if(!ofr4_put(c,c.s.a[6],0x17,1,0xff))return false;c.s.a[0]=args;
    if(!am_read(c,window,4,value))return false;c.s.a[1]=value;am_word(c.s.d[1],d1);am_word(c.s.d[2],d2);c.s.pc=0xcc778;return true;
}
// cc610 / cc654: LEA cdf3e(PC),A0; MOVE.W 8c(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A0,D0.W),A0; MOVE.W #k,D0; ADD.W D0,D0;
// MOVE.W (A0,D0.W),D0; BEQ.W zero_pc; BPL.W plus_pc; otherwise minus_pc (a flag-sharing Bcc pair: N and Z of the MOVE.W).
bool ofr4_sound(AnimationMachineContext& c,std::uint32_t k,std::uint32_t zero_pc,std::uint32_t plus_pc,std::uint32_t minus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=0xcdf3e;
    if(!ofr4_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;
    am_word(r.d[0],k);am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
    r.pc=value==0U?zero_pc:(ofr4_negative_word(value)?minus_pc:plus_pc);return true;
}
// cc7a0 / cc822: ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; JMP table(PC,D0.W): the computed PC goes through the routing (contract decision 2).
bool ofr4_table_jump(AnimationMachineContext& c,std::uint32_t table) {
    AnimationMachineState& r=c.s;am_word(r.d[0],r.d[0]&0xffU);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    r.pc=am_index(table,r.d[0]);return true;
}
}
// Objects FR4 (192 block starts, contract docs/analysis/animation-machine-frontier-fr4-contract.md): the area-D IO-frontier objects of the FR3 IO
// rerun 72f8a (installed by the N15 / FR2b family; 730a6 / 73218 / 73296 / 73304 / 73392 and the common tail 7345e that jumps into the hit entry
// cc778 with its helpers cca76 / cc600 and cdc1c) and 878dc (object table 4a6b0; the 28ae child 8790c with 87982 / 87a3e / 87a50 / 87a6c), with
// their natural successors in the same runs: the FR3 stop install bca2c (bca62) and the FR1c 28ae child bc7d6 (bc836).  Every exit is routed except
// the targets of the two computed jumps cc7a8 / cc82a (27-entry BRA.W tables, decision 2: the PC goes through the routing).  MOVE.L #v,(A6) enters v
// only when v is the next PC, otherwise it only writes the callback LONG (stops 733d0 bcaa0 cdc24, the in-range writes 72f8a 87a3e and the routed
// 71a80 72d42 bc93c).  The 7 consumers 73124 (7054c), 73468 (1ab80), 878ec (28ae), 87a9e (1ab02), cc60c cc638 cc67c (497a6) read a known C or
// fail.  No X, no TRAP, no known-C producer.  Data through the live bus (no limit test).
bool animation_objects_fr4_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    case 0x8790a:case 0x87a6a:case 0x87a8a:case 0x87aa8:case 0xbc842:case 0xbca9e:case 0xcc694:case 0xcc818:return am_return(c);   // RTS.
    case 0x7346c:case 0x87a64:case 0x87aa2:                                                   // (7346c: MOVEA.L c(A6),A0; ST.B 62(A0);) JMP 2a00.l.
        if(r.pc==0x7346cU){if(!ofr4_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr4_put(c,r.a[0],0x62,1,0xff))return false;}
        r.pc=0x2a00;return true;
    // ---- 72f8a (installed value): JSR 49a58.l / ANDI.L #ff,D0; SUBI.L #80,D0; MOVE.L D0,92(A6); TST.B 83(A6); BEQ.W 73008.
    case 0x72f8a:case 0x73064:case 0x730d2:return am_call(c,0x49a58,r.pc+6U);                 // JSR 49a58.l.
    case 0x72f90:r.d[0]=(r.d[0]&0xffU)-0x80U;if(!ofr4_put(c,r.a[6],0x92,4,r.d[0]))return false;return ofr4_test(c,r.a[6],0x83,1,0x73008,0x72fa8);
    case 0x72fa8:return ofr4_test(c,r.a[6],0x9c,2,0x72fb0,0x72fdc);                          // TST.W 9c(A6); BNE.W 72fdc.
    case 0x73008:return ofr4_test(c,r.a[6],0x9c,2,0x73010,0x7303c);                          // TST.W 9c(A6); BNE.W 7303c.
    case 0x72fb0:return ofr4_bank_anim(c,3,0x2000d0,4,0x72fd8);
    case 0x73010:return ofr4_bank_anim(c,3,0x2000d0,4,0x73038);
    case 0x72fdc:return ofr4_bank_anim(c,0xb,0x2000d4,4,0x73004);
    case 0x7303c:return ofr4_bank_anim(c,0xb,0x2000d4,4,0x73064);
    case 0x72fd8:r.pc=0x73004;return true;                                                   // BRA.W 73004.
    case 0x73004:case 0x73038:r.pc=0x73064;return true;                                      // BRA.W 73064.
    // ANDI.L #ffff,D0; ADDI.L #40000,D0; BTST.B #0,15(A6); BNE.W 73082 / 73080: NEG.L D0.
    case 0x7306a:r.d[0]=(r.d[0]&0xffffU)+0x40000U;return ofr4_bit(c,r.a[6],0x15,0,0x73080,0x73082);
    case 0x73080:case 0x7308c:case 0x73284:case 0x73326:                                    // NEG.L D0.
        r.d[0]=0U-r.d[0];r.pc=r.pc==0x73080U?0x73082:(r.pc==0x7308cU?0x7308e:(r.pc==0x73284U?0x73286:0x73328));return true;
    // MOVE.L D0,64(A6); TST.L D0; BPL.W 7308e.
    case 0x73082:if(!ofr4_put(c,r.a[6],0x64,4,r.d[0]))return false;r.pc=ofr4_negative(r.d[0])?0x7308c:0x7308e;return true;
    // LSL.L #6,D0; SWAP D0; ADDI.W #80,D0; MOVE.W D0,2c(A6); MOVE.L 42(A6),8e(A6); MOVE.L #730a6,(A6).
    case 0x7308e:
        r.d[0]=r.d[0]<<6;am_swap(r.d[0]);am_word(r.d[0],r.d[0]+0x80U);
        if(!ofr4_put(c,r.a[6],0x2c,2,r.d[0]) || !ofr4_get(c,r.a[6],0x42,4,value) || !ofr4_put(c,r.a[6],0x8e,4,value))return false;return ofr4_install(c,0x730a6);
    case 0x730a6:case 0x732c2:return ofr4_bit(c,r.a[6],0x15,7,0x73304,r.pc+10U);            // BTST.B #7,15(A6); BEQ.W 73304.
    case 0x730b0:return ofr4_bit(c,r.a[6],0x61,0,0x730ba,0x73218);                          // BTST.B #0,61(A6); BNE.W 73218.
    // MOVE.L 8e(A6),D0; SUB.L 42(A6),D0; MOVE.L 64(A6),D1; MOVE.L D1,D2; LSL.L #3,D2; ADD.L D2,D0; EOR.L D1,D0; BPL.W 730ea.
    case 0x730ba:
        if(!ofr4_get(c,r.a[6],0x8e,4,value) || !ofr4_get(c,r.a[6],0x42,4,other))return false;r.d[0]=value-other;
        if(!ofr4_get(c,r.a[6],0x64,4,value))return false;r.d[1]=value;r.d[2]=r.d[1]<<3;r.d[0]=(r.d[0]+r.d[2])^r.d[1];
        r.pc=ofr4_negative(r.d[0])?0x730d2:0x730ea;return true;
    case 0x730d8:am_byte(r.d[0],r.d[0]&7U);r.pc=ofr4_b(r.d[0])==0U?0x71a80:0x730e0;return true;   // ANDI.B #7,D0; BEQ.W 71a80.
    // NEG.L 64(A6); BCHG.B #0,15(A6).
    case 0x730e0:if(!ofr4_neg_long(c,0x64) || !ofr4_set_bit(c,r.a[6],0x15,0,2,other))return false;r.pc=0x730ea;return true;
    case 0x730ea:am_word(r.d[0],0x40);return ofr4_bit(c,r.a[6],0x15,0,0x730f8,0x730fa);     // MOVE.W #40,D0; BTST.B #0,15(A6); BNE.W 730fa.
    case 0x730f8:am_word(r.d[0],0U-r.d[0]);r.pc=0x730fa;return true;                         // NEG.W D0.
    // ADD.W 42(A6),D0; MOVE.W 46(A6),D1; MOVEM.W D0-D1,-(A7) (D0.W at the lower address); JSR 4bc04.l.
    case 0x730fa:
        if(!ofr4_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],r.d[0]+value);if(!ofr4_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],value);
        if(!am_push(c,2,ofr4_w(r.d[1])) || !am_push(c,2,ofr4_w(r.d[0])))return false;return am_call(c,0x4bc04,0x7310c);
    // MOVEM.W (A7)+,D2-D3 (sign-extended); BSR.W 70036.
    case 0x7310c:
        if(!am_pop(c,2,value) || !am_pop(c,2,other))return false;r.d[2]=am_extend_word(value);r.d[3]=am_extend_word(other);return am_call(c,0x70036,0x73114);
    case 0x73114:case 0x732cc:return am_call(c,0x4bfa4,r.pc+6U);                              // JSR 4bfa4.l.
    case 0x7311a:case 0x732fa:case 0x733b6:case 0x87a22:case 0x87a56:case 0xbc83c:case 0xbca68:return am_call(c,0x49fc6,r.pc+6U);   // JSR 49fc6.l.
    case 0x73120:return am_call(c,0x7054c,0x73124);                                          // BSR.W 7054c.
    case 0x73124:return ofr4_carry(c,0x7312e,0x73128);                                       // BCC.W 7312e (C of 7054c).
    case 0x73128:return ofr4_callback(c,0x71a80,0x7312e);                                    // MOVE.L #71a80,(A6).
    case 0x7312e:case 0x73300:case 0x733cc:r.pc=0x7345e;return true;                          // BRA.W 7345e.
    // ---- 73218: TST.W 9c(A6); BNE.W 7324c / anim(3 | b, 2000d0 | 2000d4, c).
    case 0x73218:return ofr4_test(c,r.a[6],0x9c,2,0x73220,0x7324c);
    case 0x73220:return ofr4_bank_anim(c,3,0x2000d0,0xc,0x73248);
    case 0x73248:r.pc=0x73274;return true;                                                   // BRA.W 73274.
    case 0x7324c:return ofr4_bank_anim(c,0xb,0x2000d4,0xc,0x73274);
    case 0x73274:r.d[0]=0x10000U;return ofr4_bit(c,r.a[6],0x15,0,0x73284,0x73286);          // MOVE.L #10000,D0; BTST.B #0,15(A6); BNE.W 73286.
    // MOVE.L D0,64(A6); MOVE.L 42(A6),8e(A6); MOVE.L #73296,(A6).
    case 0x73286:
        if(!ofr4_put(c,r.a[6],0x64,4,r.d[0]) || !ofr4_get(c,r.a[6],0x42,4,value) || !ofr4_put(c,r.a[6],0x8e,4,value))return false;return ofr4_install(c,0x73296);
    // ---- 73296 (installed value): MOVE.W 64(A6),D2; LSL.W #2,D2; ADD.W 42(A6),D2; MOVE.W 46(A6),D3; MOVE.W #ff,D0; BSR.W 70036.
    case 0x73296:
        if(!ofr4_get(c,r.a[6],0x64,2,value) || !ofr4_get(c,r.a[6],0x42,2,other))return false;am_word(r.d[2],(value<<2)+other);
        if(!ofr4_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[3],value);am_word(r.d[0],0xff);return am_call(c,0x70036,0x732ac);
    // MOVE.W 8e(A6),D0; SUB.W 42(A6),D0; MOVE.W 64(A6),D1; EOR.W D1,D0; BPL.W 732c2 / 732be: NEG.L 64(A6).
    case 0x732ac:
        if(!ofr4_get(c,r.a[6],0x8e,2,value) || !ofr4_get(c,r.a[6],0x42,2,other))return false;am_word(r.d[0],value-other);
        if(!ofr4_get(c,r.a[6],0x64,2,value))return false;am_word(r.d[1],value);am_word(r.d[0],r.d[0]^r.d[1]);
        r.pc=ofr4_negative_word(r.d[0])?0x732be:0x732c2;return true;
    case 0x732be:if(!ofr4_neg_long(c,0x64))return false;r.pc=0x732c2;return true;
    case 0x732d2:return ofr4_bit(c,r.a[6],0x61,0,0x732dc,0x732fa);                          // BTST.B #0,61(A6); BNE.W 732fa.
    case 0x732dc:return ofr4_sign(c,0x64,2,0x732ee,0x732e4);                                 // TST.W 64(A6); BPL.W 732ee.
    case 0x732e4:if(!ofr4_set_bit(c,r.a[6],0x15,0,1,other))return false;r.pc=0x732f4;return true;   // BCLR.B #0,15(A6); BRA.W 732f4.
    case 0x732ee:if(!ofr4_set_bit(c,r.a[6],0x15,0,0,other))return false;r.pc=0x732f4;return true;   // BSET.B #0,15(A6).
    case 0x732f4:return ofr4_callback(c,0x72f8a,0x732fa);                                    // MOVE.L #72f8a,(A6).
    // ---- 73304: CMPI.W #180,46(A6); BCS.W 73316 (unsigned WORD < 180) / 7330e: MOVE.L #8a000,3a(A6).
    case 0x73304:if(!ofr4_get(c,r.a[6],0x46,2,value))return false;r.pc=value<0x180U?0x73316:0x7330e;return true;
    case 0x7330e:if(!ofr4_put(c,r.a[6],0x3a,4,0x8a000))return false;r.pc=0x73316;return true;
    case 0x73316:r.d[0]=0x28000U;return ofr4_bit(c,r.a[6],0x15,0,0x73326,0x73328);          // MOVE.L #28000,D0; BTST.B #0,15(A6); BNE.W 73328.
    // MOVE.L D0,64(A6); MOVE.L D0,36(A6); TST.W 9c(A6); BNE.W 73364.
    case 0x73328:if(!ofr4_put(c,r.a[6],0x64,4,r.d[0]) || !ofr4_put(c,r.a[6],0x36,4,r.d[0]))return false;return ofr4_test(c,r.a[6],0x9c,2,0x73338,0x73364);
    case 0x73338:return ofr4_bank_anim(c,3,0x2000d0,0x28,0x73360);
    case 0x73360:r.pc=0x7338c;return true;                                                   // BRA.W 7338c.
    case 0x73364:return ofr4_bank_anim(c,0xb,0x2000d4,0x28,0x7338c);
    case 0x7338c:return ofr4_install(c,0x73392);
    // ---- 73392 (installed value): MOVE.L 64(A6),D0; SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6); MOVE.L #fff00000,D0; SUB.L 3a(A6),D0;
    // ASR.L #5,D0; ADD.L D0,3a(A6); JSR 4be34.l.
    case 0x73392:
        if(!ofr4_get(c,r.a[6],0x64,4,value) || !ofr4_get(c,r.a[6],0x36,4,other))return false;r.d[0]=ofr4_asr_long(value-other,5);
        if(!ofr4_put(c,r.a[6],0x36,4,other+r.d[0]) || !ofr4_get(c,r.a[6],0x3a,4,other))return false;r.d[0]=ofr4_asr_long(0xfff00000U-other,5);
        if(!ofr4_put(c,r.a[6],0x3a,4,other+r.d[0]))return false;return am_call(c,0x4be34,0x733b6);
    case 0x733bc:return ofr4_bit(c,r.a[6],0x15,7,0x733cc,0x733c6);                          // BTST.B #7,15(A6); BEQ.W 733cc.
    case 0x733c6:return ofr4_callback(c,0x733d0,0x733cc);                                    // MOVE.L #733d0,(A6).
    // ---- 7345e (common tail): LEA 72d5e(PC),A0; JSR 1ab80.l / BCC.W 7347a (C of 1ab80).
    case 0x7345e:r.a[0]=0x72d5e;return am_call(c,0x1ab80,0x73468);
    case 0x73468:return ofr4_carry(c,0x7347a,0x7346c);
    // MOVE.B 62(A6),D0; BEQ.W 734a6 / 73482: SUBQ.W #1,D0; ANDI.W #1,D0; BNE.W 73496.
    case 0x7347a:if(!ofr4_get(c,r.a[6],0x62,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x734a6:0x73482;return true;
    case 0x73482:am_word(r.d[0],r.d[0]-1U);am_word(r.d[0],r.d[0]&1U);r.pc=ofr4_w(r.d[0])!=0U?0x73496:0x7348c;return true;
    case 0x7348c:if(!ofr4_set_bit(c,r.a[6],0x15,0,0,other))return false;r.pc=0x7349c;return true;   // BSET.B #0,15(A6); BRA.W 7349c.
    case 0x73496:if(!ofr4_set_bit(c,r.a[6],0x15,0,1,other))return false;r.pc=0x7349c;return true;   // BCLR.B #0,15(A6).
    // MOVE.L (A6),9e(A6); MOVE.L #72d42,(A6).
    case 0x7349c:if(!ofr4_get(c,r.a[6],0,4,value) || !ofr4_put(c,r.a[6],0x9e,4,value))return false;return ofr4_callback(c,0x72d42,0x734a6);
    case 0x734a6:return am_call(c,0x48502,0x734ac);                                          // JSR 48502.l.
    case 0x734ac:ofr4_asr_word1(r.d[1]);r.pc=ofr4_negative_word(r.d[1])?0x734b2:0x734b4;return true;   // ASR.W #1,D1; BPL.W 734b4.
    case 0x734b2:case 0x734bc:am_word(r.d[1],0U-r.d[1]);r.pc=r.pc==0x734b2U?0x734b4:0x734be;return true;   // NEG.W D1.
    case 0x734ce:case 0x734d8:am_word(r.d[3],0U-r.d[3]);r.pc=r.pc==0x734ceU?0x734d0:0x734da;return true;   // NEG.W D3.
    // SUB.W 8e(A6),D0; BPL.W 734be.
    case 0x734b4:if(!ofr4_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[0],r.d[0]-value);r.pc=ofr4_negative_word(r.d[0])?0x734bc:0x734be;return true;
    // ADD.W D1,D0; ADDI.W #8000,D0; SWAP D0; ASR.L #8,D0; ASR.W #1,D3; BPL.W 734d0.
    case 0x734be:
        am_word(r.d[0],r.d[0]+r.d[1]);am_word(r.d[0],r.d[0]+0x8000U);am_swap(r.d[0]);r.d[0]=ofr4_asr_long(r.d[0],8);ofr4_asr_word1(r.d[3]);
        r.pc=ofr4_negative_word(r.d[3])?0x734ce:0x734d0;return true;
    // SUB.W 8e(A6),D2; BPL.W 734da.
    case 0x734d0:if(!ofr4_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[2],r.d[2]-value);r.pc=ofr4_negative_word(r.d[2])?0x734d8:0x734da;return true;
    // ADD.W D3,D2; ADDI.W #8000,D2; SWAP D2; ASR.L #8,D2; ADD.L D0,D2; TST.W 9a(A6); BEQ.W 73506.
    case 0x734da:
        am_word(r.d[2],r.d[2]+r.d[3]);am_word(r.d[2],r.d[2]+0x8000U);am_swap(r.d[2]);r.d[2]=ofr4_asr_long(r.d[2],8)+r.d[0];
        return ofr4_test(c,r.a[6],0x9a,2,0x73506,0x734ee);
    // MOVE.W 96(A6),D0; ADD.W 53a2(A5),D0; SUB.W 42(A6),D0; ADDI.W #8000,D0; SWAP D0; CLR.W D0; ASR.L #6,D0; ADD.L D0,D2.
    case 0x734ee:
        if(!ofr4_get(c,r.a[6],0x96,2,value))return false;am_word(r.d[0],value);if(!ofr4_get(c,r.a[5],0x53a2,2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!ofr4_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],r.d[0]-value);am_word(r.d[0],r.d[0]+0x8000U);am_swap(r.d[0]);am_word(r.d[0],0);
        r.d[0]=ofr4_asr_long(r.d[0],6);r.d[2]=r.d[2]+r.d[0];r.pc=0x73506;return true;
    // ASR.L #6,D2; MOVEQ #0,D0; MOVE.W 8c(A6),D0; ADDI.W #77,D0; MOVE.W D0,8c(A6); MOVE.L 92(A6),D1; BMI.W 73520 / 7351e: NEG.L D0.
    case 0x73506:
        r.d[2]=ofr4_asr_long(r.d[2],6);if(!ofr4_get(c,r.a[6],0x8c,2,value))return false;r.d[0]=(value+0x77U)&0xffffU;
        if(!ofr4_put(c,r.a[6],0x8c,2,r.d[0]) || !ofr4_get(c,r.a[6],0x92,4,value))return false;r.d[1]=value;r.pc=ofr4_negative(r.d[1])?0x73520:0x7351e;return true;
    case 0x7351e:r.d[0]=0U-r.d[0];r.pc=0x73520;return true;
    // LSL.L #1,D0; ASR.L #6,D1; ADD.W D0,D1; SUB.L D1,D2; ADD.L 92(A6),D2; MOVE.L D2,92(A6); ADD.L 8e(A6),D2; BVS.W 7353c (signed 32-bit overflow).
    case 0x73520:
        r.d[0]=r.d[0]<<1;r.d[1]=ofr4_asr_long(r.d[1],6);am_word(r.d[1],r.d[1]+r.d[0]);r.d[2]=r.d[2]-r.d[1];
        if(!ofr4_get(c,r.a[6],0x92,4,value))return false;r.d[2]=r.d[2]+value;if(!ofr4_put(c,r.a[6],0x92,4,r.d[2]) || !ofr4_get(c,r.a[6],0x8e,4,value))return false;
        other=r.d[2]+value;r.pc=(((r.d[2]^other)&(value^other))&0x80000000U)!=0U?0x7353c:0x73538;r.d[2]=other;return true;
    case 0x73538:if(!ofr4_put(c,r.a[6],0x8e,4,r.d[2]))return false;r.pc=0x7353c;return true;   // MOVE.L D2,8e(A6).
    case 0x7353c:return am_call(c,0x4b54e,0x73542);                                          // JSR 4b54e.l.
    case 0x73542:return ofr4_bit(c,r.a[6],0x61,7,0x735a4,0x7354c);                          // BTST.B #7,61(A6); BEQ.W 735a4.
    // MOVEA.L c(A6),A0; ST.B 62(A0); TST.W 9c(A6); BNE.W 73582.
    case 0x7354c:if(!ofr4_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr4_put(c,r.a[0],0x62,1,0xff))return false;return ofr4_test(c,r.a[6],0x9c,2,0x7355c,0x73582);
    case 0x7355c:return ofr4_hit(c,0xcdeea,0x2000d0,3,0);
    case 0x73582:return ofr4_hit(c,0xcdef8,0x2000d4,0xb,1);
    case 0x735a4:r.pc=0x70054;return true;                                                   // BRA.W 70054.
    // ---- 878dc (object table 4a6b0): MOVEA.L #8790c,A0; MOVE.W #a,D0; JSR 28ae.l / BCC.W 8790a (C of 28ae).
    case 0x878dc:r.a[0]=0x8790c;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x878ec);
    case 0x878ec:return ofr4_carry(c,0x8790a,0x878f0);
    case 0x878f0:am_word(r.d[0],0xffe8);return ofr4_bit(c,r.a[6],0x15,0,0x87900,0x878fe);   // MOVE.W #ffe8,D0; BTST.B #0,15(A6); BEQ.W 87900.
    case 0x878fe:am_word(r.d[0],0U-r.d[0]);r.pc=0x87900;return true;                         // NEG.W D0.
    case 0x87900:am_word(r.d[1],0x20);return am_call(c,0x4970a,0x8790a);                    // MOVE.W #20,D1; JSR 4970a.l.
    // ---- 8790c (28ae child of 878dc): JSR 491c4.l / MOVE.L #80000,36(A6); MOVE.L #0,3a(A6); MOVE.W #8,76(A6); BTST.B #0,15(A6); BNE.W 87936.
    case 0x8790c:case 0xbc7e4:return am_call(c,0x491c4,r.pc+6U);                              // JSR 491c4.l.
    case 0x87912:
        if(!ofr4_put(c,r.a[6],0x36,4,0x80000) || !ofr4_put(c,r.a[6],0x3a,4,0) || !ofr4_put(c,r.a[6],0x76,2,8))return false;
        return ofr4_bit(c,r.a[6],0x15,0,0x87932,0x87936);
    case 0x87932:if(!ofr4_neg_long(c,0x36))return false;r.pc=0x87936;return true;           // NEG.L 36(A6).
    case 0x87936:if(!ofr4_words68(c,0xe0ef))return false;return ofr4_c6a96(c,0x1f,0x13,0x87954);
    case 0x87954:return ofr4_bank_anim(c,0xba,0x200080,0x4c,0x8797c);
    case 0x8797c:return ofr4_install(c,0x87982);
    case 0x87982:return am_call(c,0x87a6c,0x87986);                                          // JSR 87a6c(PC).
    // LEA 26(A6),A0; MOVE.W #ba,20(A6); MOVE.L 200080.l,22(A6); LEA 26(A6),A0; MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 200080.l,A1;
    // MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x87986:
        r.a[0]=r.a[6]+0x26U;if(!ofr4_put(c,r.a[6],0x20,2,0xba) || !am_read(c,0x200080,4,value) || !ofr4_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]+r.d[1]);am_word(r.d[1],r.d[1]+r.d[1]);if(!am_read(c,0x200080,4,value))return false;r.a[1]=value;
        if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x879b6);
    case 0x879b6:return ofr4_bit(c,r.a[6],0x15,0,0x879c0,0x879d4);                          // BTST.B #0,15(A6); BNE.W 879d4.
    case 0x879c0:return ofr4_sign(c,0x36,4,0x879d0,0x879c8);                                 // TST.L 36(A6); BPL.W 879d0.
    case 0x879c8:if(!ofr4_add_long(c,0x36,0x2000))return false;r.pc=0x879d0;return true;    // ADDI.L #2000,36(A6).
    case 0x879d0:r.pc=0x879e4;return true;                                                   // BRA.W 879e4.
    case 0x879d4:return ofr4_sign(c,0x36,4,0x879dc,0x879e4);                                 // TST.L 36(A6); BMI.W 879e4.
    case 0x879dc:if(!ofr4_add_long(c,0x36,0U-0x2000U))return false;r.pc=0x879e4;return true;   // SUBI.L #2000,36(A6).
    case 0x879e4:return ofr4_test(c,r.a[6],0x76,2,0x879f4,0x879ec);                         // TST.W 76(A6); BEQ.W 879f4.
    // SUBQ.W #1,76(A6); BRA.W 879fc.
    case 0x879ec:if(!ofr4_get(c,r.a[6],0x76,2,value) || !ofr4_put(c,r.a[6],0x76,2,value-1U))return false;r.pc=0x879fc;return true;
    case 0x879f4:if(!ofr4_add_long(c,0x3a,0U-0x4900U))return false;r.pc=0x879fc;return true;   // SUBI.L #4900,3a(A6).
    case 0x879fc:return am_call(c,0x4be34,0x87a02);                                          // JSR 4be34.l.
    case 0x87a02:return ofr4_bit(c,r.a[6],0x15,7,0x87a12,0x87a0c);                          // BTST.B #7,15(A6); BEQ.W 87a12.
    case 0x87a0c:return ofr4_callback(c,0x87a3e,0x87a12);                                    // MOVE.L #87a3e,(A6).
    case 0x87a12:return ofr4_bit(c,r.a[6],0x61,0,0x87a22,0x87a1c);                          // BTST.B #0,61(A6); BEQ.W 87a22.
    case 0x87a1c:return ofr4_callback(c,0x87a3e,0x87a22);                                    // MOVE.L #87a3e,(A6).
    // MOVE.L 72(A6),D0; BEQ.W 87a38 / 87a30: MOVEA.L D0,A0; JSR 4ae4a.l.
    case 0x87a28:if(!ofr4_get(c,r.a[6],0x72,4,value))return false;r.d[0]=value;r.pc=value==0U?0x87a38:0x87a30;return true;
    case 0x87a30:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0x87a38);
    case 0x87a38:r.pc=0x87a94;return true;                                                   // BRA.W 87a94.
    // ---- 87a3e (installed value): BSET.B #3,61(A6); MOVE.W #14,76(A6); MOVE.L #87a50,(A6).
    case 0x87a3e:if(!ofr4_set_bit(c,r.a[6],0x61,3,0,other) || !ofr4_put(c,r.a[6],0x76,2,0x14))return false;return ofr4_install(c,0x87a50);
    case 0x87a50:case 0xbc836:case 0xbca62:return am_call(c,0x43e34,r.pc+6U);                // JSR 43e34.l.
    case 0x87a94:r.a[0]=0x87a8c;return am_call(c,0x1ab02,0x87a9e);                           // LEA 87a8c(PC),A0; JSR 1ab02.l.
    case 0x87a5c:return ofr4_count(c,0x76,0x87a6a,0x87a64);                                  // SUBQ.W #1,76(A6); BCC.W 87a6a.
    // ---- 87a6c: MOVE.W #13,D0; MOVE.W 3a(A6),D1; BPL.W 87a8a / 87a78: NEG.W D1; LSR.W #1,D1; CMPI.W #4,D1; BLE.W 87a88 (signed).
    case 0x87a6c:
        am_word(r.d[0],0x13);if(!ofr4_get(c,r.a[6],0x3a,2,value))return false;am_word(r.d[1],value);r.pc=ofr4_negative_word(value)?0x87a78:0x87a8a;return true;
    case 0x87a78:am_word(r.d[1],0U-r.d[1]);am_word(r.d[1],ofr4_w(r.d[1])>>1);r.pc=ofr4_sw(r.d[1])<=4?0x87a88:0x87a84;return true;
    case 0x87a84:am_word(r.d[1],4);r.pc=0x87a88;return true;                                 // MOVE.W #4,D1.
    case 0x87a88:am_word(r.d[0],r.d[0]+r.d[1]);r.pc=0x87a8a;return true;                     // ADD.W D1,D0.
    case 0x87a9e:return ofr4_carry(c,0x87aa8,0x87aa2);                                       // BCC.W 87aa8 (C of 1ab02).
    // ---- bc7d6 (FR1c 28ae child): MOVE.W #0,D0; MOVE.W #0,D1; JSR 49290.l / JSR 491c4.l / c6a96(4f, 37) / anim(e3, 200140, dc).
    case 0xbc7d6:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x49290,0xbc7e4);
    case 0xbc7ea:return ofr4_c6a96(c,0x4f,0x37,0xbc7fc);
    case 0xbc7fc:return ofr4_bank_anim(c,0xe3,0x200140,0xdc,0xbc824);
    case 0xbc824:if(!ofr4_words68(c,0x8838))return false;return ofr4_install(c,0xbc836);    // MOVE.W #8838,68 / 1e(A6); MOVE.L #bc836,(A6).
    // ---- bca2c (FR3 install): MOVE.W #8,D0; MOVE.W D0,76(A6); anim(e3, 200140, 90) / MOVE.L #bca62,(A6).
    case 0xbca2c:am_word(r.d[0],8);if(!ofr4_put(c,r.a[6],0x76,2,r.d[0]))return false;return ofr4_bank_anim(c,0xe3,0x200140,0x90,0xbca5c);
    case 0xbca5c:return ofr4_install(c,0xbca62);
    // MOVEA.L c(A6),A0; TST.B 62(A0); BEQ.W bca88.
    case 0xbca6e:if(!ofr4_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;return ofr4_test(c,r.a[0],0x62,1,0xbca88,0xbca7a);
    case 0xbca7a:return ofr4_count(c,0x76,0xbca88,0xbca82);                                  // SUBQ.W #1,76(A6); BCC.W bca88.
    case 0xbca82:return ofr4_callback(c,0xbc93c,0xbca88);                                    // MOVE.L #bc93c,(A6).
    case 0xbca88:return ofr4_test(c,r.a[0],0x63,1,0xbca9e,0xbca90);                         // TST.B 63(A0); BEQ.W bca9e.
    case 0xbca90:return ofr4_count(c,0x76,0xbca9e,0xbca98);                                  // SUBQ.W #1,76(A6); BCC.W bca9e.
    case 0xbca98:return ofr4_callback(c,0xbcaa0,0xbca9e);                                    // MOVE.L #bcaa0,(A6).
    // ---- cc600: JSR 8ff4.l / JSR 497a6.l / BCS.W cc654 (C of 497a6).
    case 0xcc600:return am_call(c,0x8ff4,0xcc606);
    case 0xcc606:case 0xcc632:case 0xcc676:return am_call(c,0x497a6,r.pc+6U);                 // JSR 497a6.l.
    case 0xcc60c:return ofr4_carry(c,0xcc610,0xcc654);
    case 0xcc610:return ofr4_sound(c,0,0xcc650,0xcc646,0xcc632);
    case 0xcc654:return ofr4_sound(c,1,0xcc694,0xcc68a,0xcc676);
    case 0xcc638:return ofr4_carry(c,0xcc63c,0xcc642);                                       // BCS.W cc642 (C of 497a6).
    case 0xcc67c:return ofr4_carry(c,0xcc680,0xcc686);                                       // BCS.W cc686 (C of 497a6).
    // MOVE.W (A0),D0; BRA.W cc646 | cc68a / MOVE.W 2(A0),D0.
    case 0xcc63c:case 0xcc642:case 0xcc680:case 0xcc686:
        if(!ofr4_get(c,r.a[0],(r.pc==0xcc642U||r.pc==0xcc686U)?2U:0U,2,value))return false;am_word(r.d[0],value);r.pc=r.pc<0xcc650U?0xcc646:0xcc68a;return true;
    case 0xcc646:case 0xcc68a:am_byte(r.d[1],0);return am_call(c,0x8ebe,r.pc+10U);            // MOVE.B #0,D1; JSR 8ebe.l.
    case 0xcc650:r.pc=0xcc694;return true;                                                   // BRA.W cc694.
    // ---- cc778 (JMP target of 7355c / 73582 and other units): MOVE.B 5e(A6),D0; BEQ.W cc818 / cc780: JSR cca76(PC).
    case 0xcc778:if(!ofr4_get(c,r.a[6],0x5e,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0xcc818:0xcc780;return true;
    case 0xcc780:return am_call(c,0xcca76,0xcc784);
    // MOVE.B 5e(A6),D0; MOVE.B #0,5e(A6); BTST.B #7,15(A6); BEQ.W cc81a.
    case 0xcc784:if(!ofr4_get(c,r.a[6],0x5e,1,value) || !ofr4_put(c,r.a[6],0x5e,1,0))return false;am_byte(r.d[0],value);return ofr4_bit(c,r.a[6],0x15,7,0xcc81a,0xcc798);
    // CMPI.B #1b,D0; BCC.W cdc1c (unsigned BYTE >= 1b).
    case 0xcc798:case 0xcc81a:r.pc=ofr4_b(r.d[0])>=0x1bU?0xcdc1c:(r.pc==0xcc798U?0xcc7a0:0xcc822);return true;
    case 0xcc7a0:return ofr4_table_jump(c,0xcc7ac);
    case 0xcc822:return ofr4_table_jump(c,0xcc82e);
    case 0xcdc1c:if(!ofr4_put(c,r.a[6],0,4,0xcdc24))return false;return am_return(c);         // MOVE.L #cdc24,(A6); RTS.
    // ---- cca76: BSET.B #6,61(A6); BNE.W cca9c / cca80: MOVE.B #0,76(A6); MOVE.B #ff,7b(A6); MOVE.L A0,82(A6); MOVE.L A1,86(A6); MOVE.W D1,8a(A6);
    // MOVE.W D2,8c(A6).
    case 0xcca76:if(!ofr4_set_bit(c,r.a[6],0x61,6,0,other))return false;r.pc=other!=0U?0xcca9c:0xcca80;return true;
    case 0xcca80:
        if(!ofr4_put(c,r.a[6],0x76,1,0) || !ofr4_put(c,r.a[6],0x7b,1,0xff) || !ofr4_put(c,r.a[6],0x82,4,r.a[0]) || !ofr4_put(c,r.a[6],0x86,4,r.a[1]) ||
           !ofr4_put(c,r.a[6],0x8a,2,r.d[1]) || !ofr4_put(c,r.a[6],0x8c,2,r.d[2]))return false;
        r.pc=0xcca9c;return true;
    case 0xcca9c:if(!ofr4_put(c,r.a[6],0x56,4,0))return false;return am_call(c,0xcc600,0xccaa8);   // MOVE.L #0,56(A6); BSR.W cc600.
    case 0xccaa8:if(!ofr4_put(c,r.a[6],0x56,4,0))return false;return am_call(c,0xe9112,0xccab6);   // MOVE.L #0,56(A6); JSR e9112.l.
    // BTST.B #7,15(A6); SNE.B 78(A6); CLR.B 7a(A6); CLR.L 7e(A6); CLR.L 64(A6); CLR.B 79(A6); CLR.B 7d(A6); CLR.B 77(A6); CLR.B 7c(A6); RTS.
    case 0xccab6:
        if(!ofr4_get(c,r.a[6],0x15,1,value) || !ofr4_put(c,r.a[6],0x78,1,(value&0x80U)!=0U?0xffU:0U) || !ofr4_put(c,r.a[6],0x7a,1,0) ||
           !ofr4_put(c,r.a[6],0x7e,4,0) || !ofr4_put(c,r.a[6],0x64,4,0) || !ofr4_put(c,r.a[6],0x79,1,0) || !ofr4_put(c,r.a[6],0x7d,1,0) ||
           !ofr4_put(c,r.a[6],0x77,1,0) || !ofr4_put(c,r.a[6],0x7c,1,0))return false;
        return am_return(c);
    default:return am_error(c,"unsupported animation objects fr4 PC");
    }
}
}
