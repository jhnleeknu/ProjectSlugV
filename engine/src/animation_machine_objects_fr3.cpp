#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr3_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ofr3_b(std::uint32_t value) {return value&255U;}
// Signed value of the low WORD (for BLE / BGE on CMP.W).
int ofr3_sw(std::uint32_t value) {const int v=static_cast<int>(value&65535U);return v>=32768?v-65536:v;}
bool ofr3_negative(std::uint32_t value) {return (value&0x80000000U)!=0U;}
// ASR.L #count (1..31) of a 32-bit value: arithmetic, the sign bit is replicated (no signed shift in C++).
std::uint32_t ofr3_asr_long(std::uint32_t value,unsigned int count) {
    const std::uint32_t fill=ofr3_negative(value)?~(0xffffffffU>>count):0U;return (value>>count)|fill;
}
// MULS.W source,Dn: the two low WORDs sign-extended, the 32-bit product (fits; computed modulo 2^32 on unsigned values).
std::uint32_t ofr3_muls(std::uint32_t source,std::uint32_t destination) {
    return am_extend_word(ofr3_w(source))*am_extend_word(ofr3_w(destination));
}
// MULU.W source,Dn: the two low WORDs unsigned, the 32-bit product (the upper WORDs are not inputs).
std::uint32_t ofr3_mulu(std::uint32_t source,std::uint32_t destination) {return ofr3_w(source)*ofr3_w(destination);}
// DIVU.W divisor,Dn (68000): zero WORD divisor -> checked error (the original takes the vector 5 exception, not modeled); quotient > ffff sets V
// and leaves Dn unchanged; otherwise Dn = remainder:quotient.  The flags are never read in this unit.
bool ofr3_divu(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t divisor) {
    const std::uint32_t v=divisor&0xffffU;
    if(v==0U)return am_error(c,"objects fr3 DIVU zero divisor");
    const std::uint32_t quotient=d/v;const std::uint32_t remainder=d%v;
    if(quotient>0xffffU)return true;
    d=(remainder<<16)|quotient;return true;
}
bool ofr3_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr3_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG) whose fall-through is the installed callback itself: enter it.
bool ofr3_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ofr3_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVE.L #value,(A6) that only writes the callback LONG for a later frame (contract decision 2); then next_pc.
bool ofr3_callback(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!ofr3_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// BCC on a known C (returned by a callee): clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ofr3_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr3 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// BTST.B #bit,d(An); BEQ.W zero_pc (bit clear); otherwise set_pc.
bool ofr3_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!ofr3_get(c,base,displacement,1,value))return false;c.s.pc=((value>>bit)&1U)==0U?zero_pc:set_pc;return true;
}
// TST.W / TST.B d(An); BNE.W nonzero_pc (otherwise zero_pc).
bool ofr3_test(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t nonzero_pc) {
    std::uint32_t value=0;if(!ofr3_get(c,base,displacement,size,value))return false;c.s.pc=value!=0U?nonzero_pc:zero_pc;return true;
}
// BSET / BCLR / BCHG.B #bit,d(An) (mode 0 / 1 / 2); old = the tested bit (the Z of the instruction is old == 0).
bool ofr3_set_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int mode,std::uint32_t& old) {
    std::uint32_t value=0;if(!ofr3_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;old=(value>>bit)&1U;
    const std::uint32_t next=mode==0U?(value|mask):(mode==1U?(value&~mask):(value^mask));
    return ofr3_put(c,base,displacement,1,next);
}
// SUBQ.W #1,d(A6); BCC.W no_borrow_pc (the old WORD was not 0), otherwise borrow_pc.
bool ofr3_count(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t no_borrow_pc,std::uint32_t borrow_pc) {
    std::uint32_t value=0;if(!ofr3_get(c,c.s.a[6],displacement,2,value) || !ofr3_put(c,c.s.a[6],displacement,2,value-1U))return false;
    c.s.pc=value!=0U?no_borrow_pc:borrow_pc;return true;
}
// MOVE.W #value,68(A6); MOVE.W #value,1e(A6).
bool ofr3_words68(AnimationMachineContext& c,std::uint32_t value) {
    return ofr3_put(c,c.s.a[6],0x68,2,value) && ofr3_put(c,c.s.a[6],0x1e,2,value);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L window.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus).
bool ofr3_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t window,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr3_put(c,c.s.a[6],0x20,2,n) || !am_read(c,window,4,value) || !ofr3_put(c,c.s.a[6],0x22,4,value))return false;
    am_word(c.s.d[0],0x100);c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr3_get(c,c.s.a[6],0x22,4,value))return false;c.s.a[1]=value;
    if(!ofr3_get(c,c.s.a[1],displacement,4,value))return false;c.s.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #d0,D0; MOVE.W #d1,D1; MOVE.B #0,D2; JSR c6a96.l.
bool ofr3_c6a96(AnimationMachineContext& c,std::uint32_t d0,std::uint32_t d1,std::uint32_t return_pc) {
    am_word(c.s.d[0],d0);am_word(c.s.d[1],d1);am_byte(c.s.d[2],0);return am_call(c,0xc6a96,return_pc);
}
// ea880 / ea8ae: LEA table(PC),A1; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
bool ofr3_table_anim(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[1]=table;
    if(!ofr3_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
}
// Objects FR3 (197 block starts, contract docs/analysis/animation-machine-frontier-fr3-contract.md): the area-D IO-frontier objects of the FR2b IO
// rerun c5370 (object table e9004; c53ec / c561a / c564e, the empty helper c579e) and bc93c (FR2b install; bc972 / bc9e0 / bca0e) with their natural
// successors in the same runs: the N15 28ae children 76ff2 (7703e) and 7706a (77138, 771e6, the helpers 77284, d0fec, ea69c) with its child 77206
// (77258), the U18 install ea85a (ea8d2), the FR2b install 70d92 (70dfc), the FR1c 28ae child bc404 (bc464), and the rest of the d0fec helper module
// d1028 (d108a, d10b4).  Every exit is routed; MOVE.L #v,(A6) enters v only when v is the next PC, otherwise it only writes the callback LONG (stops
// bca2c bcaa0 c5432 c554c c5696, the in-range writes bc9e0 bc93c 77138 and the routed 70c0c ea908).  Known C: ea6fc (ORI; RTS) Set, ea70a (ANDI;
// RTS) Clear, ea8e8 (ANDI; BCLR; BNE) Clear on both exits, 771d8 (ORI) Set without a reader.  The 17 consumers 70e12 7704a 77264 bc470 bca1a ea8fc
// (49fc6), 7705e (1ab80), 77158 77278 (1ab02), 770bc (76f98), 77170 (SCS, ea69c), 771ca (28ae), c5412 c5682 (4b54e), ea6b8 (1abda), ea6cc (ea65a),
// ea86e (4c2cc) read a known C or fail.  No X, no computed jump, no TRAP.  Data through the live bus (no limit test).
bool animation_objects_fr3_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    case 0x77068:case 0x771dc:case 0x77282:case 0xbc47a:case 0xbc9de:case 0xbca2a:case 0xc5430:case 0xc5694:case 0xc579e:case 0xd10ba:case 0xea906:
        return am_return(c);                                                                  // RTS.
    case 0x7704e:case 0x77062:case 0x7715c:case 0x77186:case 0x77268:case 0x7727c:case 0xbc474:r.pc=0x2a00;return true;   // JMP 2a00.l.
    // ---- 70d92 (FR2b install): TST.W 9c(A6); BNE.W 70dc6 / anim(3 | b, 2000d0 | 2000d4, 18).
    case 0x70d92:return ofr3_test(c,r.a[6],0x9c,2,0x70d9a,0x70dc6);
    case 0x70d9a:return ofr3_bank_anim(c,3,0x2000d0,0x18,0x70dc2);
    case 0x70dc2:r.pc=0x70dee;return true;                                                   // BRA.W 70dee.
    case 0x70dc6:return ofr3_bank_anim(c,0xb,0x2000d4,0x18,0x70dee);
    case 0x70dee:if(!ofr3_put(c,r.a[6],0x64,4,0))return false;return ofr3_install(c,0x70dfc);    // MOVE.L #0,64(A6); MOVE.L #70dfc,(A6).
    case 0x70dfc:return ofr3_bit(c,r.a[6],0x15,7,0x71c90,0x70e06);                          // BTST.B #7,15(A6); BEQ.W 71c90.
    case 0x70e06:return am_call(c,0x4bfa4,0x70e0c);                                          // JSR 4bfa4.l.
    case 0x70e0c:return am_call(c,0x49fc6,0x70e12);                                          // JSR 49fc6.l.
    case 0x70e12:return ofr3_carry(c,0x70e26,0x70e16);                                       // BCC.W 70e26 (C of 49fc6).
    case 0x70e16:r.a[0]=r.a[6]+0x26U;return am_call(c,0x492d0,0x70e20);                     // LEA 26(A6),A0; JSR 492d0.l.
    case 0x70e20:return ofr3_callback(c,0x70c0c,0x70e26);                                    // MOVE.L #70c0c,(A6).
    case 0x70e26:r.pc=0x72dd2;return true;                                                   // BRA.W 72dd2.
    // ---- 76ff2 (N15 28ae child): MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); c6a96(23, 7) / anim(da, 200090, 1c) / MOVE.L #7703e,(A6).
    case 0x76ff2:if(!ofr3_words68(c,0x8820))return false;return ofr3_c6a96(c,0x23,7,0x77010);
    case 0x77010:return ofr3_bank_anim(c,0xda,0x200090,0x1c,0x77038);
    case 0x77038:return ofr3_install(c,0x7703e);
    case 0x7703e:return am_call(c,0x43e34,0x77044);                                          // JSR 43e34.l.
    case 0x77044:return am_call(c,0x49fc6,0x7704a);                                          // JSR 49fc6.l.
    case 0x7704a:return ofr3_carry(c,0x77054,0x7704e);                                       // BCC.W 77054 (C of 49fc6).
    case 0x77054:r.a[0]=0x772be;return am_call(c,0x1ab80,0x7705e);                           // LEA 772be(PC),A0; JSR 1ab80.l.
    case 0x7705e:return ofr3_carry(c,0x77068,0x77062);                                       // BCC.W 77068 (C of 1ab80).
    // ---- 7706a (N15 28ae child): MOVE.W #e0ef,68(A6); MOVE.W #e0ef,1e(A6); c6a96(23, 35).
    case 0x7706a:if(!ofr3_words68(c,0xe0ef))return false;return ofr3_c6a96(c,0x23,0x35,0x77088);
    // MOVE.W #da,20(A6); MOVEA.L #772ce,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x77088:if(!ofr3_put(c,r.a[6],0x20,2,0xda))return false;r.a[1]=0x772ce;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x7709e);
    // BSET.B #3,15(A6); JSR 43e34.l.
    case 0x7709e:if(!ofr3_set_bit(c,r.a[6],0x15,3,0,other))return false;return am_call(c,0x43e34,0x770aa);
    case 0x770aa:r.a[0]=0xc88d4;return am_call(c,0x490ba,0x770b6);                           // LEA c88d4.l,A0; JSR 490ba.l.
    case 0x770b6:if(!am_push(c,2,ofr3_w(r.d[0])))return false;return am_call(c,0x76f98,0x770bc);   // MOVE.W D0,-(A7); JSR 76f98(PC).
    case 0x770bc:return ofr3_carry(c,0x770c2,0x770c0);                                       // BCC.W 770c2 (C of 76f98).
    case 0x770c0:r.a[0]=r.a[6];r.pc=0x770c2;return true;                                     // MOVEA.L A6,A0.
    // MOVE.W 42(A0),D0; SUB.W 42(A6),D0; BTST.B #0,15(A6); BNE.W 770d6 / 770d4: NEG.W D0.
    case 0x770c2:
        if(!ofr3_get(c,r.a[0],0x42,2,value) || !ofr3_get(c,r.a[6],0x42,2,other))return false;am_word(r.d[0],value-other);
        return ofr3_bit(c,r.a[6],0x15,0,0x770d4,0x770d6);
    case 0x770d4:case 0x770f6:am_word(r.d[0],0U-r.d[0]);r.pc=r.pc==0x770d4U?0x770d6:0x770f8;return true;   // NEG.W D0.
    // MOVE.W (A7)+,D2; CMP.W D2,D0; BLE.W 770e0 (signed) / 770de: MOVE.W D2,D0.
    case 0x770d6:if(!am_pop(c,2,value))return false;am_word(r.d[2],value);r.pc=ofr3_sw(r.d[0])<=ofr3_sw(r.d[2])?0x770e0:0x770de;return true;
    case 0x770de:am_word(r.d[0],r.d[2]);r.pc=0x770e0;return true;
    case 0x770e0:r.pc=ofr3_sw(r.d[0])>=0x40?0x770ec:0x770e8;return true;                    // CMPI.W #40,D0; BGE.W 770ec (signed).
    case 0x770e8:am_word(r.d[0],0x40);r.pc=0x770ec;return true;                              // MOVE.W #40,D0.
    case 0x770ec:return ofr3_bit(c,r.a[6],0x15,0,0x770f6,0x770f8);                          // BTST.B #0,15(A6); BNE.W 770f8.
    // MOVE.W 46(A0),D1; ADDI.W #10,D1; SUB.W 46(A6),D1; MOVE.L #ffffac60,D2; MOVE.W 7a(A6),D3; JSR d0fec.l.
    case 0x770f8:
        if(!ofr3_get(c,r.a[0],0x46,2,value) || !ofr3_get(c,r.a[6],0x46,2,other))return false;am_word(r.d[1],value+0x10U-other);
        r.d[2]=0xffffac60U;if(!ofr3_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[3],value);return am_call(c,0xd0fec,0x77114);
    // MOVEM.L D0-D1,36(A6); MOVE.L #0,7e(A6); MOVE.L D2,82(A6); CLR.B 89(A6); BCLR.B #0,15(A6); MOVE.L #77138,(A6); RTS.
    case 0x77114:
        if(!ofr3_put(c,r.a[6],0x36,4,r.d[0]) || !ofr3_put(c,r.a[6],0x3a,4,r.d[1]) || !ofr3_put(c,r.a[6],0x7e,4,0) || !ofr3_put(c,r.a[6],0x82,4,r.d[2]) ||
           !ofr3_put(c,r.a[6],0x89,1,0) || !ofr3_set_bit(c,r.a[6],0x15,0,1,other) || !ofr3_put(c,r.a[6],0,4,0x77138))return false;
        return am_return(c);
    // ---- 77138 (installed value): MOVE.L 7e(A6),D0; ADD.L D0,36(A6); MOVE.L 82(A6),D0; ADD.L D0,3a(A6); JSR 4be34.l.
    case 0x77138:
        if(!ofr3_get(c,r.a[6],0x7e,4,value))return false;r.d[0]=value;if(!ofr3_get(c,r.a[6],0x36,4,value) || !ofr3_put(c,r.a[6],0x36,4,value+r.d[0]))return false;
        if(!ofr3_get(c,r.a[6],0x82,4,value))return false;r.d[0]=value;if(!ofr3_get(c,r.a[6],0x3a,4,value) || !ofr3_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;
        return am_call(c,0x4be34,0x7714e);
    case 0x7714e:r.a[0]=0x772c6;return am_call(c,0x1ab02,0x77158);                           // LEA 772c6(PC),A0; JSR 1ab02.l.
    case 0x77158:return ofr3_carry(c,0x77162,0x7715c);                                       // BCC.W 77162 (C of 1ab02).
    case 0x77162:return ofr3_test(c,r.a[6],0x8a,1,0x7716a,0x77174);                         // TST.B 8a(A6); BNE.W 77174.
    case 0x7716a:return am_call(c,0xea69c,0x77170);                                          // JSR ea69c.l.
    // SCS.B 8a(A6) (the C of ea69c).
    case 0x77170:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects fr3 caller requires known carry");
        if(!ofr3_put(c,r.a[6],0x8a,1,r.carry==AnimationCarrySet?0xffU:0U))return false;r.pc=0x77174;return true;
    case 0x77174:return ofr3_bit(c,r.a[6],0x15,5,0x7718c,0x7717e);                          // BTST.B #5,15(A6); BEQ.W 7718c.
    case 0x7717e:return ofr3_test(c,r.a[6],0x8a,1,0x771e6,0x77186);                         // TST.B 8a(A6); BEQ.W 771e6.
    // LEA 772a0(PC),A0; MOVE.L A0,D0; BEQ.W 7719e (never: A0 is the constant 772a0).
    case 0x7718c:r.a[0]=0x772a0;r.d[0]=r.a[0];r.pc=r.d[0]==0U?0x7719e:0x77196;return true;
    case 0x77196:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0x7719e);                            // MOVEA.L D0,A0; JSR 4ae4a.l.
    case 0x7719e:r.pc=ofr3_w(r.d[0])!=0U?0x771e6:0x771a6;return true;                       // CMPI.W #0,D0; BNE.W 771e6.
    case 0x771a6:return am_call(c,0x77284,0x771aa);                                          // JSR 77284(PC).
    case 0x771aa:return am_call(c,0x49fc6,0x771b0);                                          // JSR 49fc6.l.
    // SUBI.B #38,89(A6); BCC.W 771dc (no borrow: unsigned old BYTE >= 38).
    case 0x771b0:if(!ofr3_get(c,r.a[6],0x89,1,value) || !ofr3_put(c,r.a[6],0x89,1,value-0x38U))return false;r.pc=value>=0x38U?0x771dc:0x771ba;return true;
    case 0x771ba:r.a[0]=0x77206;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x771ca);       // MOVEA.L #77206,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0x771ca:return ofr3_carry(c,0x771dc,0x771ce);                                       // BCC.W 771dc (C of 28ae).
    case 0x771ce:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0x771d8);     // CLR.W D0; CLR.W D1; JSR 4970a.l.
    case 0x771d8:r.carry=AnimationCarrySet;r.pc=0x771dc;return true;                        // ORI.B #1,CCR (no reader).
    case 0x771e6:return am_call(c,0x8ff4,0x771ec);                                           // JSR 8ff4.l.
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); MOVE.L #0,56(A6); JMP d1d08.l.
    case 0x771ec:if(!ofr3_words68(c,0x1001) || !ofr3_put(c,r.a[6],0x56,4,0))return false;r.pc=0xd1d08;return true;
    // ---- 77206 (28ae child of 771ba): JSR 496c2.l / MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); c6a96(e, 5) / anim(32, 20003c, 14) / install 77258.
    case 0x77206:return am_call(c,0x496c2,0x7720c);
    case 0x7720c:if(!ofr3_words68(c,0x1001))return false;return ofr3_c6a96(c,0xe,5,0x7722a);
    case 0x7722a:return ofr3_bank_anim(c,0x32,0x20003c,0x14,0x77252);
    case 0x77252:return ofr3_install(c,0x77258);
    case 0x77258:return am_call(c,0x43ea4,0x7725e);                                          // JSR 43ea4.l.
    case 0x7725e:return am_call(c,0x49fc6,0x77264);                                          // JSR 49fc6.l.
    case 0x77264:return ofr3_carry(c,0x7726e,0x77268);                                       // BCC.W 7726e (C of 49fc6).
    case 0x7726e:r.a[0]=0x772be;return am_call(c,0x1ab02,0x77278);                           // LEA 772be(PC),A0; JSR 1ab02.l.
    case 0x77278:return ofr3_carry(c,0x77282,0x7727c);                                       // BCC.W 77282 (C of 1ab02).
    // ---- 77284: MOVEM.L 36(A6),D0-D1; ASR.L #8,D0; ASR.L #8,D1; ASR.L #4,D0; ASR.L #4,D1; JSR 44602.l.
    case 0x77284:
        if(!ofr3_get(c,r.a[6],0x36,4,value) || !ofr3_get(c,r.a[6],0x3a,4,other))return false;
        r.d[0]=ofr3_asr_long(ofr3_asr_long(value,8),4);r.d[1]=ofr3_asr_long(ofr3_asr_long(other,8),4);return am_call(c,0x44602,0x77298);
    case 0x77298:am_byte(r.d[0],ofr3_b(r.d[0])>>3);if(!ofr3_put(c,r.a[6],0x88,1,r.d[0]))return false;return am_return(c);   // LSR.B #3,D0; MOVE.B D0,88(A6); RTS.
    // ---- bc404 (FR1c 28ae child): MOVE.W #0,D0; MOVE.W #0,D1; JSR 49290.l / JSR 491c4.l / c6a96(1f, e) / anim(ba, 200080, 38).
    case 0xbc404:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x49290,0xbc412);
    case 0xbc412:return am_call(c,0x491c4,0xbc418);
    case 0xbc418:return ofr3_c6a96(c,0x1f,0xe,0xbc42a);
    case 0xbc42a:return ofr3_bank_anim(c,0xba,0x200080,0x38,0xbc452);
    case 0xbc452:if(!ofr3_words68(c,0xe0ef))return false;return ofr3_install(c,0xbc464);    // MOVE.W #e0ef,68 / 1e(A6); MOVE.L #bc464,(A6).
    case 0xbc464:return am_call(c,0x43e34,0xbc46a);                                          // JSR 43e34.l.
    case 0xbc46a:return am_call(c,0x49fc6,0xbc470);                                          // JSR 49fc6.l.
    case 0xbc470:return ofr3_carry(c,0xbc47a,0xbc474);                                       // BCC.W bc47a (C of 49fc6).
    // ---- bc93c (FR2b install): MOVE.W #8,D0; MOVE.W D0,76(A6); anim(e3, 200140, 4) / MOVE.L #bc972,(A6).
    case 0xbc93c:am_word(r.d[0],8);if(!ofr3_put(c,r.a[6],0x76,2,r.d[0]))return false;return ofr3_bank_anim(c,0xe3,0x200140,4,0xbc96c);
    case 0xbc96c:return ofr3_install(c,0xbc972);
    case 0xbc972:return am_call(c,0x43e34,0xbc978);                                          // JSR 43e34.l.
    case 0xbc978:return am_call(c,0x49fc6,0xbc97e);                                          // JSR 49fc6.l (C not read).
    // MOVEA.L c(A6),A0; MOVE.W 42(A0),D0; CMP.W 42(A6),D0; BGE.W bc9a2 (signed).
    case 0xbc97e:
        if(!ofr3_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr3_get(c,r.a[0],0x42,2,value))return false;am_word(r.d[0],value);
        if(!ofr3_get(c,r.a[6],0x42,2,other))return false;r.pc=ofr3_sw(r.d[0])>=ofr3_sw(other)?0xbc9a2:0xbc98e;return true;
    case 0xbc98e:return ofr3_bit(c,r.a[6],0x15,0,0xbc99e,0xbc998);                          // BTST.B #0,15(A6); BEQ.W bc99e.
    case 0xbc998:return ofr3_callback(c,0xbc9e0,0xbc99e);                                    // MOVE.L #bc9e0,(A6).
    case 0xbc99e:r.pc=0xbc9b2;return true;                                                   // BRA.W bc9b2.
    case 0xbc9a2:return ofr3_bit(c,r.a[6],0x15,0,0xbc9ac,0xbc9b2);                          // BTST.B #0,15(A6); BNE.W bc9b2.
    case 0xbc9ac:return ofr3_callback(c,0xbc9e0,0xbc9b2);                                    // MOVE.L #bc9e0,(A6).
    case 0xbc9b2:return ofr3_test(c,r.a[0],0x63,1,0xbc9c8,0xbc9ba);                         // TST.B 63(A0); BEQ.W bc9c8.
    case 0xbc9ba:return ofr3_count(c,0x76,0xbc9c8,0xbc9c2);                                  // SUBQ.W #1,76(A6); BCC.W bc9c8.
    case 0xbc9c2:return ofr3_callback(c,0xbcaa0,0xbc9c8);                                    // MOVE.L #bcaa0,(A6).
    case 0xbc9c8:return ofr3_test(c,r.a[0],0x62,1,0xbc9d0,0xbc9de);                         // TST.B 62(A0); BNE.W bc9de.
    case 0xbc9d0:return ofr3_count(c,0x76,0xbc9de,0xbc9d8);                                  // SUBQ.W #1,76(A6); BCC.W bc9de.
    case 0xbc9d8:return ofr3_callback(c,0xbca2c,0xbc9de);                                    // MOVE.L #bca2c,(A6).
    case 0xbc9e0:return ofr3_bank_anim(c,0xe3,0x200140,8,0xbca08);
    case 0xbca08:return ofr3_install(c,0xbca0e);
    case 0xbca0e:return am_call(c,0x43e34,0xbca14);                                          // JSR 43e34.l.
    case 0xbca14:return am_call(c,0x49fc6,0xbca1a);                                          // JSR 49fc6.l.
    case 0xbca1a:return ofr3_carry(c,0xbca2a,0xbca1e);                                       // BCC.W bca2a (C of 49fc6).
    case 0xbca1e:if(!ofr3_set_bit(c,r.a[6],0x15,0,2,other))return false;return ofr3_callback(c,0xbc93c,0xbca2a);   // BCHG.B #0,15(A6); MOVE.L #bc93c,(A6).
    // ---- c5370 (object table e9004): MOVE.W #64,54(A6); c6a96(1f, 50) / JSR 4c0ac.l.
    case 0xc5370:if(!ofr3_put(c,r.a[6],0x54,2,0x64))return false;return ofr3_c6a96(c,0x1f,0x50,0xc5388);
    case 0xc5388:return am_call(c,0x4c0ac,0xc538e);
    // MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.W 76(A6),D0; BEQ.W c53be.
    case 0xc538e:if(!ofr3_words68(c,0) || !ofr3_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.pc=value==0U?0xc53be:0xc53a2;return true;
    // EXT.L D0; LSL.L #8,D0; MOVE.L D0,86(A6); MOVE.W 2e(A6),D0; CMP.W 7a(A6),D0; BLE.W c53ba (signed).
    case 0xc53a2:
        r.d[0]=am_extend_word(ofr3_w(r.d[0]))<<8;if(!ofr3_put(c,r.a[6],0x86,4,r.d[0]) || !ofr3_get(c,r.a[6],0x2e,2,value))return false;am_word(r.d[0],value);
        if(!ofr3_get(c,r.a[6],0x7a,2,other))return false;r.pc=ofr3_sw(r.d[0])<=ofr3_sw(other)?0xc53ba:0xc53b6;return true;
    case 0xc53b6:if(!ofr3_get(c,r.a[6],0x86,4,value) || !ofr3_put(c,r.a[6],0x86,4,0U-value))return false;r.pc=0xc53ba;return true;   // NEG.L 86(A6).
    case 0xc53ba:r.pc=0xc561a;return true;                                                   // BRA.W c561a.
    case 0xc53be:return ofr3_bank_anim(c,0xba,0x200080,0x140,0xc53e6);
    case 0xc53e6:return ofr3_install(c,0xc53ec);
    case 0xc53ec:return ofr3_bit(c,r.a[6],0x15,7,0xc53f6,0xc5400);                          // BTST.B #7,15(A6); BNE.W c5400.
    case 0xc53f6:return am_call(c,0x4be2c,0xc53fc);                                          // JSR 4be2c.l.
    case 0xc53fc:r.pc=0xc5406;return true;                                                   // BRA.W c5406.
    case 0xc5400:return am_call(c,0x4be06,0xc5406);                                          // JSR 4be06.l.
    case 0xc5406:return am_call(c,0x49fc6,0xc540c);                                          // JSR 49fc6.l.
    case 0xc540c:return am_call(c,0x4b54e,0xc5412);                                          // JSR 4b54e.l.
    case 0xc5412:return ofr3_carry(c,0xc5430,0xc5416);                                       // BCC.W c5430 (C of 4b54e).
    // CLR.B 5e(A6); MOVE.L #c5432,(A6); BTST.B #7,61(A6); BEQ.W c5430.
    case 0xc5416:if(!ofr3_put(c,r.a[6],0x5e,1,0) || !ofr3_put(c,r.a[6],0,4,0xc5432))return false;return ofr3_bit(c,r.a[6],0x61,7,0xc5430,0xc542a);
    case 0xc542a:case 0xc568e:return ofr3_callback(c,0xc554c,r.pc==0xc542aU?0xc5430:0xc5694);   // MOVE.L #c554c,(A6).
    // MOVE.W 7e(A6),82(A6); anim(ba, 200080, 140).
    case 0xc561a:if(!ofr3_get(c,r.a[6],0x7e,2,value) || !ofr3_put(c,r.a[6],0x82,2,value))return false;return ofr3_bank_anim(c,0xba,0x200080,0x140,0xc5648);
    case 0xc5648:return ofr3_install(c,0xc564e);
    case 0xc564e:return ofr3_bit(c,r.a[6],0x15,7,0xc5658,0xc5662);                          // BTST.B #7,15(A6); BNE.W c5662.
    case 0xc5658:return am_call(c,0x4be2c,0xc565e);                                          // JSR 4be2c.l.
    case 0xc565e:r.pc=0xc5668;return true;                                                   // BRA.W c5668.
    case 0xc5662:return am_call(c,0x4be06,0xc5668);                                          // JSR 4be06.l.
    case 0xc5668:return am_call(c,0x49fc6,0xc566e);                                          // JSR 49fc6.l.
    case 0xc566e:return ofr3_count(c,0x82,0xc567c,0xc5676);                                  // SUBQ.W #1,82(A6); BCC.W c567c.
    case 0xc5676:return ofr3_callback(c,0xc5696,0xc567c);                                    // MOVE.L #c5696,(A6).
    case 0xc567c:return am_call(c,0x4b54e,0xc5682);                                          // JSR 4b54e.l.
    case 0xc5682:return ofr3_carry(c,0xc5694,0xc5686);                                       // BCC.W c5694 (C of 4b54e).
    case 0xc5686:if(!ofr3_put(c,r.a[6],0x5e,1,0))return false;return am_call(c,0xc579e,0xc568e);   // CLR.B 5e(A6); BSR.W c579e.
    // ---- d0fec: MOVE.L D2,-(A7); BPL.W d0ff4 / d0ff2: NEG.L D2.
    case 0xd0fec:if(!am_push(c,4,r.d[2]))return false;r.pc=ofr3_negative(r.d[2])?0xd0ff2:0xd0ff4;return true;
    case 0xd0ff2:r.d[2]=0U-r.d[2];r.pc=0xd0ff4;return true;
    case 0xd0ff4:r.pc=ofr3_sw(r.d[3])>=2?0xd1000:0xd0ffc;return true;                       // CMPI.W #2,D3; BGE.W d1000 (signed).
    case 0xd0ffc:am_word(r.d[3],2);r.pc=0xd1000;return true;                                 // MOVE.W #2,D3.
    // MOVE.L #10000,D4; DIVU.W D3,D4; MULS.W D4,D0; MULS.W D4,D1; MOVE.W D3,D5; MULU.W D2,D3; SWAP D2; MULU.W D2,D5; SWAP D5; CLR.W D5;
    // ADD.L D5,D3; ASR.L #1,D3; MOVE.L (A7)+,D2; BPL.W d1024.
    case 0xd1000:
        r.d[4]=0x10000U;if(!ofr3_divu(c,r.d[4],r.d[3]))return false;r.d[0]=ofr3_muls(r.d[4],r.d[0]);r.d[1]=ofr3_muls(r.d[4],r.d[1]);
        am_word(r.d[5],r.d[3]);r.d[3]=ofr3_mulu(r.d[2],r.d[3]);am_swap(r.d[2]);r.d[5]=ofr3_mulu(r.d[2],r.d[5]);am_swap(r.d[5]);am_word(r.d[5],0);
        r.d[3]=ofr3_asr_long(r.d[3]+r.d[5],1);if(!am_pop(c,4,value))return false;r.d[2]=value;r.pc=ofr3_negative(r.d[2])?0xd1022:0xd1024;return true;
    case 0xd1022:r.d[3]=0U-r.d[3];r.pc=0xd1024;return true;                                  // NEG.L D3.
    case 0xd1024:r.d[1]=r.d[1]-r.d[3];return am_return(c);                                   // SUB.L D3,D1; RTS.
    // ---- d1028: MOVEM.W D0-D1,-(A7); MOVE.L D2,D0; MOVE.B D3,D1; JSR 443d2.l.
    case 0xd1028:
        if(!am_push(c,2,ofr3_w(r.d[1])) || !am_push(c,2,ofr3_w(r.d[0])))return false;r.d[0]=r.d[2];am_byte(r.d[1],r.d[3]);return am_call(c,0x443d2,0xd1036);
    // MOVE.L D0,D2; MOVE.L D1,D3; MOVEM.W (A7)+,D0-D1 (sign-extended); ASR.L #8,D2; ASR.L #8,D3; TST.W D0; BNE.W d104c.
    case 0xd1036:
        r.d[2]=r.d[0];r.d[3]=r.d[1];if(!am_pop(c,2,value) || !am_pop(c,2,other))return false;r.d[0]=am_extend_word(value);r.d[1]=am_extend_word(other);
        r.d[2]=ofr3_asr_long(r.d[2],8);r.d[3]=ofr3_asr_long(r.d[3],8);r.pc=ofr3_w(r.d[0])!=0U?0xd104c:0xd1048;return true;
    case 0xd1048:am_word(r.d[0],1);r.pc=0xd104c;return true;                                 // MOVE.W #1,D0.
    // EXT.L D2; EXT.L D3; MOVEM.L D2-D3,-(A7); MOVE.L D2,D4; MULS.W D2,D4; MOVE.L D4,D7; BSR.W d108a.
    case 0xd104c:
        r.d[2]=am_extend_word(ofr3_w(r.d[2]));r.d[3]=am_extend_word(ofr3_w(r.d[3]));if(!am_push(c,4,r.d[3]) || !am_push(c,4,r.d[2]))return false;
        r.d[4]=ofr3_muls(r.d[2],r.d[2]);r.d[7]=r.d[4];return am_call(c,0xd108a,0xd105e);
    // MOVE.L D7,D4; ASR.L #1,D4; NEG.L D4; MOVE.L D2,D5; MULS.W D1,D5; MOVE.L D5,D7; BSR.W d108a.
    case 0xd105e:r.d[4]=0U-ofr3_asr_long(r.d[7],1);r.d[5]=ofr3_muls(r.d[1],r.d[2]);r.d[7]=r.d[5];return am_call(c,0xd108a,0xd106e);
    // MOVE.L D7,D5; ASR.L #1,D5; SUB.L D3,D5; MULS.W D2,D5; MOVE.L D5,D7; BSR.W d108a.
    case 0xd106e:r.d[5]=ofr3_muls(r.d[2],ofr3_asr_long(r.d[7],1)-r.d[3]);r.d[7]=r.d[5];return am_call(c,0xd108a,0xd107c);
    // MOVE.L D4,D2; MOVE.L D7,D3; MOVEM.L (A7)+,D0-D1; LSL.L #8,D0; LSL.L #8,D1; RTS.
    case 0xd107c:
        r.d[2]=r.d[4];r.d[3]=r.d[7];if(!am_pop(c,4,value) || !am_pop(c,4,other))return false;r.d[0]=value<<8;r.d[1]=other<<8;return am_return(c);
    // ---- d108a: MOVEM.L D0-D1,-(A7); TST.L D0; SMI.B D1; BPL.W d1098 / d1096: NEG.L D0.
    case 0xd108a:
        if(!am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;am_byte(r.d[1],ofr3_negative(r.d[0])?0xffU:0U);
        r.pc=ofr3_negative(r.d[0])?0xd1096:0xd1098;return true;
    case 0xd1096:r.d[0]=0U-r.d[0];r.pc=0xd1098;return true;
    case 0xd1098:r.pc=ofr3_negative(r.d[7])?0xd109e:0xd10a2;return true;                    // TST.L D7; BPL.W d10a2.
    case 0xd109e:r.d[7]=0U-r.d[7];am_byte(r.d[1],~r.d[1]);r.pc=0xd10a2;return true;        // NEG.L D7; NOT.B D1.
    case 0xd10a2:return am_call(c,0xd10b4,0xd10a6);                                          // BSR.W d10b4.
    case 0xd10a6:r.pc=ofr3_b(r.d[1])==0U?0xd10ae:0xd10ac;return true;                       // TST.B D1; BEQ.W d10ae.
    case 0xd10ac:r.d[7]=0U-r.d[7];r.pc=0xd10ae;return true;                                  // NEG.L D7.
    case 0xd10ae:if(!am_pop(c,4,value) || !am_pop(c,4,other))return false;r.d[0]=value;r.d[1]=other;return am_return(c);   // MOVEM.L (A7)+,D0-D1; RTS.
    case 0xd10b4:r.pc=r.d[0]!=0U?0xd10bc:0xd10ba;return true;                               // TST.L D0; BNE.W d10bc.
    // MOVE.L D7,D6; CLR.W D6; SWAP D6; DIVU.W D0,D6; SWAP D6; SWAP D7; MOVE.W D6,D7; SWAP D7; DIVU.W D0,D7; SWAP D6; SWAP D7; MOVE.W D6,D7;
    // SWAP D7; RTS.
    case 0xd10bc:
        r.d[6]=r.d[7];am_word(r.d[6],0);am_swap(r.d[6]);if(!ofr3_divu(c,r.d[6],r.d[0]))return false;am_swap(r.d[6]);am_swap(r.d[7]);am_word(r.d[7],r.d[6]);
        am_swap(r.d[7]);if(!ofr3_divu(c,r.d[7],r.d[0]))return false;am_swap(r.d[6]);am_swap(r.d[7]);am_word(r.d[7],r.d[6]);am_swap(r.d[7]);return am_return(c);
    // ---- ea69c: MOVEQ #0,D2; BRA.W ea6b0 / MOVE.W D2,-(A7); JSR 1abda.l / BCC.W ea70a (C of 1abda).
    case 0xea69c:r.d[2]=0;r.pc=0xea6b0;return true;
    case 0xea6b0:if(!am_push(c,2,ofr3_w(r.d[2])))return false;return am_call(c,0x1abda,0xea6b8);
    case 0xea6b8:return ofr3_carry(c,0xea70a,0xea6bc);
    // MOVE.L 42(A6),D0; MOVE.L 46(A6),D1; MOVEA.W #0,A0; MOVEQ #2,D7; BSR.B ea65a.
    case 0xea6bc:
        if(!ofr3_get(c,r.a[6],0x42,4,value) || !ofr3_get(c,r.a[6],0x46,4,other))return false;r.d[0]=value;r.d[1]=other;r.a[0]=0;r.d[7]=2;
        return am_call(c,0xea65a,0xea6cc);
    case 0xea6cc:return ofr3_carry(c,0xea70a,0xea6d0);                                       // BCC.W ea70a (C of ea65a).
    // MOVEM.L D0-D1/A0,-(A7); MOVEA.L #eaac0,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0xea6d0:
        if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;r.a[0]=0xeaac0;am_word(r.d[0],0x1e);r.a[1]=0x100bf4;
        return am_call(c,0x2986,0xea6ea);
    // MOVEM.L (A7)+,D0-D1/A1 (A1 := the pushed A0); SWAP D0; SWAP D1; LEA 2e(A0),A0; JSR 43e08.l.
    case 0xea6ea:
        if(!am_pop(c,4,value))return false;r.d[0]=value;if(!am_pop(c,4,value))return false;r.d[1]=value;if(!am_pop(c,4,value))return false;r.a[1]=value;
        am_swap(r.d[0]);am_swap(r.d[1]);r.a[0]=r.a[0]+0x2eU;return am_call(c,0x43e08,0xea6fc);
    // LEA -2e(A0),A0; MOVE.W (A7)+,76(A0); ORI.B #1,CCR; RTS.
    case 0xea6fc:
        r.a[0]=am_index(r.a[0],0xffd2);if(!am_pop(c,2,value) || !ofr3_put(c,r.a[0],0x76,2,value))return false;r.carry=AnimationCarrySet;return am_return(c);
    case 0xea70a:r.a[7]=r.a[7]+2U;r.carry=AnimationCarryClear;return am_return(c);          // ADDQ.W #2,A7; ANDI.B #fe,CCR; RTS.
    // ---- ea85a (U18 install): JSR 8ff4.l / ADDQ.W #1,32(A6); MOVE.W #ffe0,D0; JSR 4c2cc.l / BCC.W ea89e (C of 4c2cc).
    case 0xea85a:return am_call(c,0x8ff4,0xea860);
    case 0xea860:if(!ofr3_get(c,r.a[6],0x32,2,value) || !ofr3_put(c,r.a[6],0x32,2,value+1U))return false;am_word(r.d[0],0xffe0);return am_call(c,0x4c2cc,0xea86e);
    case 0xea86e:return ofr3_carry(c,0xea89e,0xea872);
    case 0xea872:return am_call(c,0x1abda,0xea878);                                          // JSR 1abda.l.
    case 0xea878:r.d[1]=0;return am_call(c,0x8ebe,0xea880);                                  // MOVEQ #0,D1; JSR 8ebe.l.
    case 0xea880:return ofr3_table_anim(c,0xea712,0xea89a);
    case 0xea89a:r.pc=0xea8c8;return true;                                                   // BRA.W ea8c8.
    case 0xea89e:return am_call(c,0x1abda,0xea8a4);                                          // JSR 1abda.l.
    case 0xea8a4:am_word(r.d[0],r.d[1]);r.d[1]=0;return am_call(c,0x8ebe,0xea8ae);          // MOVE.W D1,D0; MOVEQ #0,D1; JSR 8ebe.l.
    case 0xea8ae:return ofr3_table_anim(c,0xea722,0xea8c8);
    // SUBQ.W #1,32(A6); MOVE.L #ea8d2,(A6).
    case 0xea8c8:if(!ofr3_get(c,r.a[6],0x32,2,value) || !ofr3_put(c,r.a[6],0x32,2,value-1U))return false;return ofr3_install(c,0xea8d2);
    // BCLR.B #7,5e51(A5); BNE.W ea8e2 (the old bit was set).
    case 0xea8d2:if(!ofr3_set_bit(c,r.a[5],0x5e51,7,1,other))return false;r.pc=other!=0U?0xea8e2:0xea8dc;return true;
    case 0xea8dc:r.d[7]=8;return am_call(c,0xea762,0xea8e2);                                 // MOVEQ #8,D7; JSR ea762(PC).
    case 0xea8e2:return am_call(c,0x43e34,0xea8e8);                                          // JSR 43e34.l.
    // ANDI.B #fe,CCR; BCLR.B #7,5e50(A5); BNE.W ea8fc (C Clear on both exits: BCLR changes only Z).
    case 0xea8e8:r.carry=AnimationCarryClear;if(!ofr3_set_bit(c,r.a[5],0x5e50,7,1,other))return false;r.pc=other!=0U?0xea8fc:0xea8f6;return true;
    case 0xea8f6:return am_call(c,0x49fc6,0xea8fc);                                          // JSR 49fc6.l.
    case 0xea8fc:return ofr3_carry(c,0xea906,0xea900);                                       // BCC.W ea906 (C of 49fc6 or of ea8e8).
    case 0xea900:return ofr3_callback(c,0xea908,0xea906);                                    // MOVE.L #ea908,(A6).
    default:return am_error(c,"unsupported animation objects fr3 PC");
    }
}
}
