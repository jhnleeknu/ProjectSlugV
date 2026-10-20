#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ob4b_b(std::uint32_t value) {return value&255U;}
std::uint32_t ob4b_w(std::uint32_t value) {return value&65535U;}
// The low WORD / BYTE as a signed value.
std::int32_t ob4b_signed_word(std::uint32_t value) {
    const std::uint32_t w=value&65535U;return (w&0x8000U)!=0U?static_cast<std::int32_t>(w)-65536:static_cast<std::int32_t>(w);
}
std::int32_t ob4b_signed_byte(std::uint32_t value) {
    const std::uint32_t b=value&255U;return (b&0x80U)!=0U?static_cast<std::int32_t>(b)-256:static_cast<std::int32_t>(b);
}
// ASR.L #n (1 <= n <= 8): explicit sign refill of the n vacated bits.
std::uint32_t ob4b_asr_long(std::uint32_t value,unsigned int n) {
    return (value>>n)|((value&0x80000000U)!=0U?~(0xffffffffU>>n):0U);
}
// ASR.W #1 on the low WORD of a register; the upper WORD is kept.
void ob4b_asr_word1(std::uint32_t& r) {
    const std::uint32_t w=r&65535U;am_word(r,(w>>1)|(w&0x8000U));
}
// MULS.W: signed 16 x 16 -> 32 (|a*b| <= 2^30: no overflow); the result modulo 2^32 is well defined.
std::uint32_t ob4b_muls(std::uint32_t reg,std::uint32_t word) {
    const std::int32_t product=ob4b_signed_word(reg)*ob4b_signed_word(word);return static_cast<std::uint32_t>(product);
}
bool ob4b_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob4b_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// ADD/SUB/ADDQ/SUBQ on a memory operand d16(An): read, add `delta` (modulo the size), write.
bool ob4b_add(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t delta) {
    std::uint32_t value=0;if(!ob4b_get(c,base,displacement,size,value))return false;return ob4b_put(c,base,displacement,size,value+delta);
}
// MOVE.L d(A0),d(A6).
bool ob4b_copy_from_a0(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t value=0;if(!ob4b_get(c,c.s.a[0],displacement,4,value))return false;return ob4b_put(c,c.s.a[6],displacement,4,value);
}
// MOVE.L #value,(A6) (installed callback LONG); the fall-through enters the installed callback.
bool ob4b_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ob4b_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVE.L #value,(A6) followed by the next block (not the installed value).
bool ob4b_callback(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next) {
    if(!ob4b_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next;return true;
}
// MOVE.L #value,(A6); RTS.
bool ob4b_install_return(AnimationMachineContext& c,std::uint32_t value) {
    if(!ob4b_put(c,c.s.a[6],0,4,value))return false;return am_return(c);
}
// BTST.B #bit,d16(An); Bcc: one_pc when the bit is 1, zero_pc when it is 0.
bool ob4b_test(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t one_pc,std::uint32_t zero_pc) {
    std::uint32_t value=0;if(!ob4b_get(c,base,displacement,1,value))return false;c.s.pc=((value>>bit)&1U)!=0U?one_pc:zero_pc;return true;
}
// BSET.B / BCLR.B #bit,d16(A6).
bool ob4b_bset(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;if(!ob4b_get(c,c.s.a[6],displacement,1,value))return false;return ob4b_put(c,c.s.a[6],displacement,1,value|(1U<<bit));
}
bool ob4b_bclr(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;if(!ob4b_get(c,c.s.a[6],displacement,1,value))return false;return ob4b_put(c,c.s.a[6],displacement,1,value&~(1U<<bit));
}
// BCC on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob4b_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b4b caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.l (animation list start).
bool ob4b_anim(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #n,D0; MOVE.B #d1,D1; JSR 8ebe.l.
bool ob4b_8ebe(AnimationMachineContext& c,std::uint32_t n,std::uint32_t d1,std::uint32_t return_pc) {
    am_word(c.s.d[0],n);am_byte(c.s.d[1],d1);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #n,20(A6); MOVE.L address.l,22(A6) (a LONG of the bank window, read through the live bus).
bool ob4b_bank_head(AnimationMachineContext& c,std::uint32_t n,std::uint32_t address) {
    std::uint32_t value=0;
    if(!ob4b_put(c,c.s.a[6],0x20,2,n) || !am_read(c,address,4,value))return false;return ob4b_put(c,c.s.a[6],0x22,4,value);
}
// MOVE.W #value,68(A6); MOVE.W #value,1e(A6).
bool ob4b_pair68(AnimationMachineContext& c,std::uint32_t value) {
    return ob4b_put(c,c.s.a[6],0x68,2,value) && ob4b_put(c,c.s.a[6],0x1e,2,value);
}
// MOVE.W d(A6),D0; [SUBI.W #100,D0 = + add]; CMPI.W #limit,D0; unsigned: below_pc when D0.W < limit, else above_pc.
bool ob4b_range(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t add,std::uint32_t limit,std::uint32_t below_pc,std::uint32_t above_pc) {
    std::uint32_t value=0;if(!ob4b_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value+add);
    c.s.pc=ob4b_w(c.s.d[0])<limit?below_pc:above_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #n,D0; JSR 28ae.l (28ae child).
bool ob4b_28ae(AnimationMachineContext& c,std::uint32_t child,std::uint32_t n,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],n);return am_call(c,0x28ae,return_pc);
}
// CMPI.B #0,82(A6); BLE.W le_pc (signed BYTE <= 0).
bool ob4b_count(AnimationMachineContext& c,std::uint32_t le_pc,std::uint32_t gt_pc) {
    std::uint32_t value=0;if(!ob4b_get(c,c.s.a[6],0x82,1,value))return false;c.s.pc=ob4b_signed_byte(value)<=0?le_pc:gt_pc;return true;
}
// MOVEQ #0,Dn; MOVE.B (A1),Dn; ADD.W Dn,Dn (the angle index of a 28366 ring cell).
bool ob4b_angle(AnimationMachineContext& c,std::uint32_t& value) {
    std::uint32_t byte=0;if(!am_read(c,c.s.a[1],1,byte))return false;value=ob4b_b(byte)*2U;return true;
}
// The WORDs (A2,D4.W) / -80(A2,D4.W) of the fixed ROM table 4419e (cos / sin), read through the live bus.
bool ob4b_cos_sin(AnimationMachineContext& c,std::uint32_t table,std::uint32_t index,std::uint32_t& cos_word,std::uint32_t& sin_word) {
    return am_read(c,am_index(table,index),2,cos_word) && am_read(c,am_index(table-0x80U,index),2,sin_word);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L bank.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l.
bool ob4b_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t bank,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=c.s.a[6]+0x26U;
    if(!ob4b_bank_head(c,n,bank))return false;am_word(c.s.d[0],0x100);c.s.a[0]=c.s.a[6]+0x26U;
    if(!ob4b_get(c,c.s.a[6],0x22,4,value))return false;c.s.a[1]=value;
    if(!ob4b_get(c,c.s.a[1],displacement,4,value))return false;c.s.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// 2b74a / 2b78c: LEA 8e(A6),A1; MOVE.L A1,76(A0); MOVE.B #0,7a..7d(A0); MOVE.B #last,7e(A0); ORI.B #1,CCR (C Set).
bool ob4b_link(AnimationMachineContext& c,std::uint32_t last,std::uint32_t next) {
    c.s.a[1]=c.s.a[6]+0x8eU;
    if(!ob4b_put(c,c.s.a[0],0x76,4,c.s.a[1]))return false;
    for(std::uint32_t d=0x7a;d<0x7e;++d)if(!ob4b_put(c,c.s.a[0],d,1,0))return false;
    if(!ob4b_put(c,c.s.a[0],0x7e,1,last))return false;c.s.carry=AnimationCarrySet;c.s.pc=next;return true;
}
}
// Objects B4b (198 block starts, contract docs/analysis/animation-machine-deferred-b4b-contract.md): the 2986 child 23a3e of the child table
// 2282c (BYTE 9e = 3; 23a3e..23c56, installs 23ae4 23bfa 23c3e) with the helper 49636 / 4964e (49636..496a6), the U06-neighbour script handler
// e74f8 with its two-entry jump table e7504 / e7508 (e74f8..e7546) and the 28ae children 2b7be (sibling stage event callback 2b7b8; 2b6e6..2b7c6)
// and e7996 (e7996..e7a44; installs e79fe), the B4 children 22f7a (22f7a..22fe0; installs 22fc8), 23774 (23774..237ca; installs 237b2), 2334c
// (2334c..233bc, 233be..2347e, 23480..2353c; installs 2339c 233de 2345e 2349a 23536), d206a (d206a..d20b0), and the 23a3e child 281ea
// (281ea..2822a, 2825c..28490; installs 2825c) with the helper 4439e (4439e..443b8). Every exit is routed (1c9b8 22a4c 288c 28ae 3af8 43e34
// 43ea4 43eb8 443d2 44602 496c2 4970a 49f8c 49fc6 4ae4a 4be06 4be34 4bfa4 4c0ac 8ebe 8ff4 c6a96, JMP 2a00, BCC 22c82, BRA 2b8b6 / d239c); the
// indirect JSR e7504(PC,D0.W) of e74fc goes to the live target through the routing. Known C: 2b74a 2b78c (end with ORI.B #1,CCR) and e7a3a set
// C; the 9 consumers 22fd4 233ea 234c6 237be 23c4a (BCC, 49fc6), 28268 (BCC, 288c), 2b746 2b788 e7a2c (BCC, 28ae) read a known C or fail. Data
// through the live bus (no limit test, as in the original): the bank LONGs 20003c 200050 20008c 200090 200094 20009c, the bank LONGs c / 30 of
// LONG 22(A6), the WORDs 4419e / 4411e + sext(index) and the script WORD (A0)+. No X / DIV / TRAP / port / bank write.
bool animation_objects_b4b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    case 0x22fd8:case 0x233b6:case 0x23478:case 0x234da:case 0x23536:case 0x237c2:case 0x23c4e:case 0x28482:case 0xe7a3e:
        r.pc=0x2a00;return true;                                                             // JMP 2a00.l.
    case 0x22fde:case 0x2341c:case 0x23514:case 0x237c8:case 0x23bd8:case 0x23c54:case 0x2848e:case 0x2b7b6:case 0xe7544:case 0xe7a1a:case 0x496a4:
        return am_return(c);                                                                 // RTS.
    // ---- 22f7a (2986 child): MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); TST.B 8a(A6); BNE.W 22fa4.
    case 0x22f7a:
        if(!ob4b_bank_head(c,0xe2,0x200094) || !ob4b_get(c,r.a[6],0x8a,1,value))return false;r.pc=ob4b_b(value)!=0U?0x22fa4:0x22f90;return true;
    case 0x22f90:return ob4b_anim(c,0x24050,0x22fa0);                                         // MOVEA.L #24050,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x22fa0:r.pc=0x22fb4;return true;                                                    // BRA.W 22fb4.
    case 0x22fa4:return ob4b_anim(c,0x24120,0x22fb4);
    case 0x22fb4:return ob4b_8ebe(c,0x204,0,0x22fc2);                                         // MOVE.W #204,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x22fc2:return ob4b_install(c,0x22fc8);                                              // MOVE.L #22fc8,(A6).
    case 0x22fc8:case 0x233c4:case 0x233de:case 0x23c3e:case 0x28324:case 0x28488:return am_call(c,0x43e34,r.pc+6U);   // JSR 43e34.l.
    case 0x22fce:case 0x233e4:case 0x234c0:case 0x237b8:case 0x23bd2:case 0x23c44:case 0xe7a14:return am_call(c,0x49fc6,r.pc+6U);   // JSR 49fc6.l.
    case 0x22fd4:return ob4b_carry(c,0x22fde,0x22fd8);                                        // BCC.W 22fde (C of 49fc6).
    // ---- 2334c (28ae child): MOVE.W #d2,20(A6); MOVE.L 20008c.l,22(A6); JSR 4c0ac.l.
    case 0x2334c:if(!ob4b_bank_head(c,0xd2,0x20008c))return false;return am_call(c,0x4c0ac,0x23360);
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); CMPI.B #1,84(A6); BEQ.W 2341e.
    case 0x23360:if(!ob4b_pair68(c,0x1001) || !ob4b_get(c,r.a[6],0x84,1,value))return false;r.pc=ob4b_b(value)==1U?0x2341e:0x23376;return true;
    case 0x23376:return ob4b_8ebe(c,0xd5,0,0x23384);
    case 0x23384:return ob4b_anim(c,0x242e6,0x23394);
    case 0x23394:return ob4b_install_return(c,0x2339c);                                       // MOVE.L #2339c,(A6); RTS.
    case 0x2339c:return ob4b_count(c,0x233c4,0x233a6);                                        // CMPI.B #0,82(A6); BLE.W 233c4 (installed value).
    case 0x233a6:case 0x23468:return am_call(c,0x4bfa4,r.pc+6U);                             // JSR 4bfa4.l.
    case 0x233ac:return ob4b_test(c,r.a[6],0x15,7,0x233be,0x233b6);                          // BTST.B #7,15(A6); BNE.W 233be.
    case 0x233be:if(!ob4b_add(c,r.a[6],0x82,1,0xffU))return false;r.pc=0x2339c;return true; // SUBQ.B #1,82(A6); BRA.B 2339c.
    case 0x233ca:r.a[0]=0x2301c;return am_call(c,0x4ae4a,0x233d4);                            // LEA 2301c(PC),A0; JSR 4ae4a.l.
    case 0x233d4:return ob4b_callback(c,0x233de,0x233e4);                                     // MOVE.L #233de,(A6); BRA.W 233e4.
    case 0x233ea:return ob4b_carry(c,0x233f4,0x233ee);                                        // BCC.W 233f4 (C of 49fc6).
    case 0x233ee:return ob4b_callback(c,0x23536,0x233f4);                                     // MOVE.L #23536,(A6).
    case 0x233f4:return ob4b_range(c,0x42,0,0x140,0x23406,0x23400);                          // MOVE.W 42(A6),D0; CMPI.W #140,D0; BCS.W 23406.
    case 0x23400:return ob4b_callback(c,0x23536,0x23406);
    case 0x23406:return ob4b_range(c,0x46,0xff00U,0x140,0x2341c,0x23416);                    // MOVE.W 46(A6),D0; SUBI.W #100,D0; CMPI.W #140,D0; BCS.W 2341c.
    case 0x23416:return ob4b_callback(c,0x23536,0x2341c);
    // MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); MOVE.W #873,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x2341e:if(!ob4b_bank_head(c,0xe2,0x200094))return false;return ob4b_8ebe(c,0x873,0,0x2343a);
    case 0x2343a:return ob4b_anim(c,0x243ec,0x2344a);
    // MOVE.B #7f,D0; MOVE.B D0,12(A6); MOVE.B D0,13(A6); MOVE.L #2345e,(A6); RTS.
    case 0x2344a:
        am_byte(r.d[0],0x7f);if(!ob4b_put(c,r.a[6],0x12,1,r.d[0]) || !ob4b_put(c,r.a[6],0x13,1,r.d[0]))return false;return ob4b_install_return(c,0x2345e);
    case 0x2345e:return ob4b_count(c,0x23486,0x23468);                                        // CMPI.B #0,82(A6); BLE.W 23486 (installed value).
    case 0x2346e:return ob4b_test(c,r.a[6],0x15,7,0x23480,0x23478);
    case 0x23480:if(!ob4b_add(c,r.a[6],0x82,1,0xffU))return false;r.pc=0x2345e;return true; // SUBQ.B #1,82(A6); BRA.B 2345e.
    // LEA 2303a(PC),A0; MOVE.L A0,7c(A6); JSR 496c2.l.
    case 0x23486:r.a[0]=0x2303a;if(!ob4b_put(c,r.a[6],0x7c,4,r.a[0]))return false;return am_call(c,0x496c2,0x23494);
    case 0x23494:return ob4b_install(c,0x2349a);
    case 0x2349a:return am_call(c,0x4be06,0x234a0);                                           // JSR 4be06.l (installed value).
    case 0x234a0:if(!ob4b_get(c,r.a[6],0x7c,4,value))return false;r.d[0]=value;r.pc=value==0U?0x234c0:0x234a8;return true;   // MOVE.L 7c(A6),D0; BEQ.W 234c0.
    case 0x234a8:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0x234b0);                             // MOVEA.L D0,A0; JSR 4ae4a.l.
    case 0x234b0:r.pc=ob4b_w(r.d[0])==0U?0x234c0:0x234b8;return true;                        // CMPI.W #0,D0; BEQ.W 234c0.
    case 0x234b8:if(!ob4b_put(c,r.a[6],0x7c,4,0))return false;r.pc=0x234c0;return true;     // MOVE.L #0,7c(A6).
    case 0x234c6:return ob4b_carry(c,0x234d0,0x234ca);
    case 0x234ca:return ob4b_callback(c,0x23536,0x234d0);
    case 0x234d0:return ob4b_test(c,r.a[6],0x15,7,0x234e0,0x234da);
    case 0x234e0:return ob4b_range(c,0x42,0,0x140,0x234f2,0x234ec);
    case 0x234ec:return ob4b_callback(c,0x23536,0x234f2);
    case 0x234f2:return ob4b_range(c,0x46,0xff00U,0x140,0x23508,0x23502);
    case 0x23502:return ob4b_callback(c,0x23536,0x23508);
    // MOVE.B 12(A6),D1; CMPI.B #ff,D1; BNE.W 23516.
    case 0x23508:if(!ob4b_get(c,r.a[6],0x12,1,value))return false;am_byte(r.d[1],value);r.pc=ob4b_b(r.d[1])==0xffU?0x23514:0x23516;return true;
    // MOVE.B #ff,D0; SUB.B D1,D0; LSR.B #2,D0; ADD.B D0,D1; CMPI.B #e0,D1; BLS.W 2352c.
    case 0x23516:
        am_byte(r.d[0],0xffU-ob4b_b(r.d[1]));am_byte(r.d[0],ob4b_b(r.d[0])>>2);am_byte(r.d[1],r.d[1]+ob4b_b(r.d[0]));
        r.pc=ob4b_b(r.d[1])<=0xe0U?0x2352c:0x23528;return true;
    case 0x23528:am_byte(r.d[1],0xff);r.pc=0x2352c;return true;                              // MOVE.B #ff,D1.
    // MOVE.B D1,12(A6); MOVE.B D1,13(A6); RTS.
    case 0x2352c:if(!ob4b_put(c,r.a[6],0x12,1,r.d[1]) || !ob4b_put(c,r.a[6],0x13,1,r.d[1]))return false;return am_return(c);
    // ---- 23774 (2986 child): MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); MOVE.W #e000,68(A6); MOVE.W #e000,1e(A6); MOVE.W #8ba,D0;
    // MOVE.B #0,D1; JSR 8ebe.l.
    case 0x23774:if(!ob4b_bank_head(c,0xe2,0x200094) || !ob4b_pair68(c,0xe000))return false;return ob4b_8ebe(c,0x8ba,0,0x2379c);
    case 0x2379c:return ob4b_anim(c,0x24502,0x237ac);
    case 0x237ac:return ob4b_install(c,0x237b2);
    case 0x237b2:return am_call(c,0x4be34,r.pc+6U);             // JSR 4be34.l.
    case 0x237be:return ob4b_carry(c,0x237c8,0x237c2);
    // ---- 23a3e (2986 child of the table 2282c): MOVE.W #5a,20(A6); MOVE.L 200050.l,22(A6); MOVEA.L #281ea,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x23a3e:if(!ob4b_bank_head(c,0x5a,0x200050))return false;return ob4b_28ae(c,0x281ea,0xa,0x23a5c);
    // MOVE.W #10,76(A0); MOVEA.L #246cc,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x23a5c:if(!ob4b_put(c,r.a[0],0x76,2,0x10))return false;return ob4b_anim(c,0x246cc,0x23a72);
    case 0x23a72:return ob4b_8ebe(c,0x86e,0,0x23a80);
    case 0x23a80:if(!ob4b_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);return am_call(c,0x1c9b8,0x23a8a);   // MOVE.W 76(A6),D0; JSR 1c9b8.l.
    // MOVE.W #e000,68(A6); MOVE.W #e000,1e(A6); MOVE.W #1a66,D0; JSR 3af8.l.
    case 0x23a8a:if(!ob4b_pair68(c,0xe000))return false;am_word(r.d[0],0x1a66);return am_call(c,0x3af8,0x23aa0);
    // BSET.B #3,15(A6); BCLR.B #0,15(A6); CLR.L 84(A6); MOVE.L 3a(A6),D0; NEG.L D0; ASR.L #6,D0; MOVE.W D0,7e(A6); MOVE.L #80000,D0;
    // MOVE.L D0,64(A6); MOVE.B 78(A6),D1; JSR 443d2.l.
    case 0x23aa0:
        if(!ob4b_bset(c,0x15,3) || !ob4b_bclr(c,0x15,0) || !ob4b_put(c,r.a[6],0x84,4,0) || !ob4b_get(c,r.a[6],0x3a,4,value))return false;
        r.d[0]=ob4b_asr_long(0U-value,6);if(!ob4b_put(c,r.a[6],0x7e,2,r.d[0]))return false;r.d[0]=0x80000;
        if(!ob4b_put(c,r.a[6],0x64,4,r.d[0]) || !ob4b_get(c,r.a[6],0x78,1,value))return false;am_byte(r.d[1],value);return am_call(c,0x443d2,0x23ad0);
    // ADD.L D0,36(A6); ADD.L D1,3a(A6); MOVE.W #1c2,82(A6); MOVE.L #23ae4,(A6).
    case 0x23ad0:
        if(!ob4b_add(c,r.a[6],0x36,4,r.d[0]) || !ob4b_add(c,r.a[6],0x3a,4,r.d[1]) || !ob4b_put(c,r.a[6],0x82,2,0x1c2))return false;return ob4b_install(c,0x23ae4);
    case 0x23ae4:r.a[0]=0x23a02;return am_call(c,0x4ae4a,0x23aee);                            // LEA 23a02(PC),A0; JSR 4ae4a.l (installed value).
    case 0x23aee:r.pc=ob4b_b(r.d[0])!=0U?0x23bda:0x23af4;return true;                        // TST.B D0; BNE.W 23bda.
    case 0x23af4:return ob4b_test(c,r.a[6],0x15,5,0x23bda,0x23afe);                          // BTST.B #5,15(A6); BNE.W 23bda.
    // MOVE.L 84(A6),D0; ADDI.L #7fff,D0; CMPI.L #180000,D0; BCS.W 23b18.
    case 0x23afe:if(!ob4b_get(c,r.a[6],0x84,4,value))return false;r.d[0]=value+0x7fffU;r.pc=r.d[0]<0x180000U?0x23b18:0x23b12;return true;
    case 0x23b12:r.d[0]=0x180000;r.pc=0x23b18;return true;                                   // MOVE.L #180000,D0.
    // MOVE.L D0,84(A6); MOVEQ #0,D7; MOVE.W 82(A6),D0; BEQ.W 23b56.
    case 0x23b18:
        if(!ob4b_put(c,r.a[6],0x84,4,r.d[0]))return false;r.d[7]=0;if(!ob4b_get(c,r.a[6],0x82,2,value))return false;am_word(r.d[0],value);
        r.pc=ob4b_w(r.d[0])==0U?0x23b56:0x23b26;return true;
    // SUBQ.W #1,D0; MOVE.W D0,82(A6); LEA 239e4(PC),A0; JSR 4ae4a.l.
    case 0x23b26:am_word(r.d[0],r.d[0]-1U);if(!ob4b_put(c,r.a[6],0x82,2,r.d[0]))return false;r.a[0]=0x239e4;return am_call(c,0x4ae4a,0x23b36);
    case 0x23b36:r.d[7]=0;r.pc=ob4b_b(r.d[0])==0U?0x23b56:0x23b3e;return true;               // MOVEQ #0,D7; TST.B D0; BEQ.W 23b56.
    case 0x23b3e:return am_call(c,0x49636,0x23b44);                                           // JSR 49636.l.
    // MOVEQ #0,D7; MOVE.B D0,D7; LSL.W #8,D7; MOVE.B #80,D7; SUB.W 78(A6),D7; SWAP D7; ASR.L #3,D7.
    case 0x23b44:
        r.d[7]=ob4b_b(r.d[0]);am_word(r.d[7],r.d[7]<<8);am_byte(r.d[7],0x80);if(!ob4b_get(c,r.a[6],0x78,2,value))return false;
        am_word(r.d[7],r.d[7]-value);am_swap(r.d[7]);r.d[7]=ob4b_asr_long(r.d[7],3);r.pc=0x23b56;return true;
    // SUB.L 7e(A6),D7; ASR.L #1,D7; ADD.L D7,7e(A6); MOVE.W 7e(A6),D0; ADD.W D0,78(A6); MOVE.L 84(A6),D0; SUB.L 64(A6),D0; ASR.L #3,D0;
    // ADD.L D0,64(A6); MOVE.L 64(A6),D0; MOVE.B 78(A6),D1; JSR 443d2.l.
    case 0x23b56:
        if(!ob4b_get(c,r.a[6],0x7e,4,value))return false;r.d[7]=ob4b_asr_long(r.d[7]-value,1);
        if(!ob4b_add(c,r.a[6],0x7e,4,r.d[7]) || !ob4b_get(c,r.a[6],0x7e,2,value))return false;am_word(r.d[0],value);
        if(!ob4b_add(c,r.a[6],0x78,2,r.d[0]) || !ob4b_get(c,r.a[6],0x84,4,value) || !ob4b_get(c,r.a[6],0x64,4,other))return false;
        r.d[0]=ob4b_asr_long(value-other,3);if(!ob4b_add(c,r.a[6],0x64,4,r.d[0]) || !ob4b_get(c,r.a[6],0x64,4,value))return false;r.d[0]=value;
        if(!ob4b_get(c,r.a[6],0x78,1,value))return false;am_byte(r.d[1],value);return am_call(c,0x443d2,0x23b84);
    // SUB.L 36(A6),D0; ASR.L #3,D0; ADD.L D0,36(A6); SUB.L 3a(A6),D1; ASR.L #3,D1; ADD.L D1,3a(A6); MOVE.W 78(A6),D1; LSR.W #3,D1;
    // ADDI.W #80,D1; ANDI.W #1f00,D1; MOVE.W D1,7c(A6); MOVE.B 78(A6),63(A6); JSR 4be34.l.
    case 0x23b84:
        if(!ob4b_get(c,r.a[6],0x36,4,value))return false;r.d[0]=ob4b_asr_long(r.d[0]-value,3);
        if(!ob4b_add(c,r.a[6],0x36,4,r.d[0]) || !ob4b_get(c,r.a[6],0x3a,4,value))return false;r.d[1]=ob4b_asr_long(r.d[1]-value,3);
        if(!ob4b_add(c,r.a[6],0x3a,4,r.d[1]) || !ob4b_get(c,r.a[6],0x78,2,value))return false;
        am_word(r.d[1],ob4b_w(value)>>3);am_word(r.d[1],r.d[1]+0x80U);am_word(r.d[1],r.d[1]&0x1f00U);
        if(!ob4b_put(c,r.a[6],0x7c,2,r.d[1]) || !ob4b_get(c,r.a[6],0x78,1,value) || !ob4b_put(c,r.a[6],0x63,1,value))return false;
        return am_call(c,0x4be34,0x23bb6);
    case 0x23bb6:return ob4b_range(c,0x42,0,0x140,0x23bc2,0x22c82);                          // MOVE.W 42(A6),D0; CMPI.W #140,D0; BCC.W 22c82.
    case 0x23bc2:return ob4b_range(c,0x46,0xff00U,0x100,0x23bd2,0x22c82);                    // ...; SUBI.W #100,D0; CMPI.W #100,D0; BCC.W 22c82.
    case 0x23bda:am_word(r.d[0],0x1a24);return am_call(c,0x3af8,0x23be4);                     // MOVE.W #1a24,D0; JSR 3af8.l.
    case 0x23be4:return am_call(c,0x22a4c,0x23be8);                                           // BSR.W 22a4c.
    case 0x23be8:r.a[0]=0x23a20;return am_call(c,0x4ae4a,0x23bf2);                            // LEA 23a20(PC),A0; JSR 4ae4a.l.
    case 0x23bf2:return ob4b_install_return(c,0x23bfa);                                       // MOVE.L #23bfa,(A6); RTS.
    // BSET.B #7,61(A6); MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); JSR 8ff4.l (installed value).
    case 0x23bfa:if(!ob4b_bset(c,0x61,7) || !ob4b_pair68(c,0x1001))return false;return am_call(c,0x8ff4,0x23c12);
    case 0x23c12:return ob4b_8ebe(c,0x80b,1,0x23c20);
    case 0x23c20:return ob4b_anim(c,0x6f536,0x23c30);
    // CLR.L 36(A6); CLR.L 3a(A6); MOVE.L #23c3e,(A6).
    case 0x23c30:if(!ob4b_put(c,r.a[6],0x36,4,0) || !ob4b_put(c,r.a[6],0x3a,4,0))return false;return ob4b_install(c,0x23c3e);
    case 0x23c4a:return ob4b_carry(c,0x23c54,0x23c4e);
    // ---- 281ea (28ae child of 23a3e): MOVE.W #32,20(A6); MOVE.L 20003c.l,22(A6); MOVE.W #37c,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x281ea:if(!ob4b_bank_head(c,0x32,0x20003c))return false;return ob4b_8ebe(c,0x37c,0,0x28206);
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); MOVEA.L #28da2,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x28206:if(!ob4b_pair68(c,0x1001))return false;return ob4b_anim(c,0x28da2,0x28222);
    case 0x28222:return ob4b_install_return(c,0x2825c);                                       // MOVE.L #2825c,(A6); RTS.
    case 0x2825c:if(!ob4b_bset(c,0x61,7))return false;return am_call(c,0x288c,0x28268);       // BSET.B #7,61(A6); JSR 288c.l (installed value).
    case 0x28268:return ob4b_carry(c,0x282de,0x2826c);                                        // BCC.W 282de (C of 288c).
    case 0x2826c:return ob4b_test(c,r.a[0],0x61,7,0x282de,0x28276);                          // BTST.B #7,61(A0); BNE.W 282de.
    // BCLR.B #7,61(A6); MOVE.B 63(A0),D0; ADDI.B #80,D0; MOVE.B D0,b3(A6); MOVE.L 3e(A0),3e(A6); MOVE.L 2e(A0),2e(A6); MOVE.L 32(A0),32(A6);
    // MOVE.W 76(A6),D0; MOVE.B b3(A6),D1; JSR 4439e.l.
    case 0x28276:
        if(!ob4b_bclr(c,0x61,7) || !ob4b_get(c,r.a[0],0x63,1,value))return false;am_byte(r.d[0],value+0x80U);
        if(!ob4b_put(c,r.a[6],0xb3,1,r.d[0]) || !ob4b_copy_from_a0(c,0x3e) || !ob4b_copy_from_a0(c,0x2e) || !ob4b_copy_from_a0(c,0x32) ||
           !ob4b_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);
        if(!ob4b_get(c,r.a[6],0xb3,1,value))return false;am_byte(r.d[1],value);return am_call(c,0x4439e,0x282a8);
    // ADD.W D0,2e(A6); ADD.W D1,32(A6); MOVEA.L c(A6),A0; MOVE.L 36(A0),D0; BPL.W 282be.
    case 0x282a8:
        if(!ob4b_add(c,r.a[6],0x2e,2,r.d[0]) || !ob4b_add(c,r.a[6],0x32,2,r.d[1]) || !ob4b_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob4b_get(c,r.a[0],0x36,4,value))return false;r.d[0]=value;r.pc=(value&0x80000000U)!=0U?0x282bc:0x282be;return true;
    case 0x282bc:r.d[0]=0U-r.d[0];r.pc=0x282be;return true;                                  // NEG.L D0.
    case 0x282be:if(!ob4b_get(c,r.a[0],0x3a,4,value))return false;r.d[1]=value;r.pc=(value&0x80000000U)!=0U?0x282c6:0x282c8;return true;   // MOVE.L 3a(A0),D1; BPL.W 282c8.
    case 0x282c6:r.d[1]=0U-r.d[1];r.pc=0x282c8;return true;                                  // NEG.L D1.
    case 0x282c8:r.pc=r.d[1]>=r.d[0]?0x282d0:0x282ce;return true;                             // CMP.L D0,D1; BCC.W 282d0 (unsigned).
    case 0x282ce:value=r.d[0];r.d[0]=r.d[1];r.d[1]=value;r.pc=0x282d0;return true;            // EXG.L D0,D1.
    // ADD.L D1,D1; ADD.L D0,D1; SWAP D1; ADDI.W #10,D1; MOVE.B D1,64(A6).
    case 0x282d0:
        r.d[1]=r.d[1]+r.d[1]+r.d[0];am_swap(r.d[1]);am_word(r.d[1],r.d[1]+0x10U);if(!ob4b_put(c,r.a[6],0x64,1,r.d[1]))return false;r.pc=0x282de;return true;
    // SUBQ.B #1,62(A6); BCC.W 28324 (no borrow: the old BYTE was not 0).
    case 0x282de:if(!ob4b_get(c,r.a[6],0x62,1,value) || !ob4b_put(c,r.a[6],0x62,1,value-1U))return false;r.pc=ob4b_b(value)!=0U?0x28324:0x282e6;return true;
    // ADDQ.B #2,62(A6); MOVE.W b0(A6),D0; SUBQ.W #8,D0; BCC.W 282f8 (the old WORD was >= 8).
    case 0x282e6:
        if(!ob4b_add(c,r.a[6],0x62,1,2) || !ob4b_get(c,r.a[6],0xb0,2,value))return false;am_word(r.d[0],value-8U);
        r.pc=ob4b_w(value)>=8U?0x282f8:0x282f4;return true;
    case 0x282f4:am_word(r.d[0],r.d[0]+0x38U);r.pc=0x282f8;return true;                      // ADDI.W #38,D0.
    // MOVE.W D0,b0(A6); LEA 78(A6),A1; LEA (A1,D0.W),A1; CLR.W 2(A1); CLR.W 4(A1); CLR.B 7(A1); MOVE.B b3(A6),(A1); BTST.B #7,61(A6);
    // BNE.W 28324.
    case 0x282f8:
        if(!ob4b_put(c,r.a[6],0xb0,2,r.d[0]))return false;r.a[1]=am_index(r.a[6]+0x78U,r.d[0]);
        if(!ob4b_put(c,r.a[1],2,2,0) || !ob4b_put(c,r.a[1],4,2,0) || !ob4b_put(c,r.a[1],7,1,0) || !ob4b_get(c,r.a[6],0xb3,1,value) ||
           !ob4b_put(c,r.a[1],0,1,value))return false;return ob4b_test(c,r.a[6],0x61,7,0x28324,0x2831e);
    case 0x2831e:if(!ob4b_put(c,r.a[1],6,1,0x11))return false;r.pc=0x28324;return true;     // MOVE.B #11,6(A1).
    // MOVE.L 4a(A6),D0; MOVE.L 4e(A6),D1; MOVE.L 42(A6),D2; MOVE.L 46(A6),D3; SUB.L D0,D2; SUB.L D1,D3; MOVEA.L #0,A0; LEA 538e(A5),A1;
    // JSR 43eb8.l.
    case 0x2832a:
        if(!ob4b_get(c,r.a[6],0x4a,4,value))return false;r.d[0]=value;if(!ob4b_get(c,r.a[6],0x4e,4,value))return false;r.d[1]=value;
        if(!ob4b_get(c,r.a[6],0x42,4,value))return false;r.d[2]=value;if(!ob4b_get(c,r.a[6],0x46,4,value))return false;r.d[3]=value;
        r.d[2]-=r.d[0];r.d[3]-=r.d[1];r.a[0]=0;r.a[1]=am_index(r.a[5],0x538e);return am_call(c,0x43eb8,0x2834e);
    // ADD.L D0,D2; ADD.L D1,D3; MOVE.L A1,3e(A6); MOVE.L D2,2e(A6); MOVE.L D3,32(A6); MOVE.W b0(A6),D7; CLR.B 63(A6).
    case 0x2834e:
        r.d[2]+=r.d[0];r.d[3]+=r.d[1];
        if(!ob4b_put(c,r.a[6],0x3e,4,r.a[1]) || !ob4b_put(c,r.a[6],0x2e,4,r.d[2]) || !ob4b_put(c,r.a[6],0x32,4,r.d[3]) || !ob4b_get(c,r.a[6],0xb0,2,value))
            return false;am_word(r.d[7],value);if(!ob4b_put(c,r.a[6],0x63,1,0))return false;r.pc=0x28366;return true;
    // LEA 78(A6),A1; LEA (A1,D7.W),A1; TST.B 6(A1); BEQ.W 2845c.
    case 0x28366:r.a[1]=am_index(r.a[6]+0x78U,r.d[7]);if(!ob4b_get(c,r.a[1],6,1,value))return false;r.pc=ob4b_b(value)==0U?0x2845c:0x28376;return true;
    // MOVE.W D7,-(A7); MOVE.B #ff,63(A6); SUBQ.B #1,6(A1); LEA 4419e.l,A2; MOVEQ #0,D4; MOVE.B (A1),D4; ADD.W D4,D4; MOVE.W (A2,D4.W),D6;
    // MOVE.W -80(A2,D4.W),D7; MOVE.W 4(A1),D5; MULS.W D5,D6; MULS.W D5,D7; ADD.L D6,D0; ADD.L D7,D1; MOVE.L D0..D3,-(A7); SUB.L D2,D0;
    // SUB.L D3,D1; SWAP D0; SWAP D1; LSL.W #2,D0; LSL.W #2,D1; MOVE.W D0,D7; OR.W D1,D7; BNE.W 283c4.
    case 0x28376:
        if(!am_push(c,2,ob4b_w(r.d[7])) || !ob4b_put(c,r.a[6],0x63,1,0xff) || !ob4b_add(c,r.a[1],6,1,0xffU))return false;r.a[2]=0x4419e;
        if(!ob4b_angle(c,r.d[4]) || !ob4b_cos_sin(c,r.a[2],r.d[4],value,other))return false;am_word(r.d[6],value);am_word(r.d[7],other);
        if(!ob4b_get(c,r.a[1],4,2,value))return false;am_word(r.d[5],value);r.d[6]=ob4b_muls(r.d[6],r.d[5]);r.d[7]=ob4b_muls(r.d[7],r.d[5]);
        r.d[0]+=r.d[6];r.d[1]+=r.d[7];
        if(!am_push(c,4,r.d[0]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[2]) || !am_push(c,4,r.d[3]))return false;
        r.d[0]-=r.d[2];r.d[1]-=r.d[3];am_swap(r.d[0]);am_swap(r.d[1]);am_word(r.d[0],r.d[0]<<2);am_word(r.d[1],r.d[1]<<2);
        am_word(r.d[7],r.d[0]);am_word(r.d[7],r.d[7]|ob4b_w(r.d[1]));r.pc=ob4b_w(r.d[7])!=0U?0x283c4:0x283be;return true;
    case 0x283be:r.d[0]=0;r.pc=0x283d4;return true;                                          // MOVEQ #0,D0; BRA.W 283d4.
    case 0x283c4:if(!am_push(c,4,r.a[1]))return false;return am_call(c,0x44602,0x283cc);      // MOVE.L A1,-(A7); JSR 44602.l.
    // MOVEA.L (A7)+,A1; LSL.W #8,D0; SUB.W (A1),D0; ASR.W #1,D0.
    case 0x283cc:
        if(!am_pop(c,4,value))return false;r.a[1]=value;am_word(r.d[0],r.d[0]<<8);if(!ob4b_get(c,r.a[1],0,2,value))return false;
        am_word(r.d[0],r.d[0]-value);ob4b_asr_word1(r.d[0]);r.pc=0x283d4;return true;
    // SUB.W 2(A1),D0; ASR.W #1,D0; ADD.W 2(A1),D0; MOVE.W D0,2(A1); ADD.W D0,(A1); MOVEQ #0,D4; MOVE.B 7(A1),D4; ADD.B 64(A6),D4; SCS.B D5;
    // OR.B D5,D4; MOVE.B D4,7(A1); ADD.W D4,D4; ADD.W D4,D4; ADD.W 4(A1),D4; CMPI.W #1000,D4; BCS.W 2840a.
    case 0x283d4:
        if(!ob4b_get(c,r.a[1],2,2,value))return false;am_word(r.d[0],r.d[0]-value);ob4b_asr_word1(r.d[0]);am_word(r.d[0],r.d[0]+value);
        if(!ob4b_put(c,r.a[1],2,2,r.d[0]) || !ob4b_add(c,r.a[1],0,2,r.d[0]) || !ob4b_get(c,r.a[1],7,1,value) || !ob4b_get(c,r.a[6],0x64,1,other))return false;
        r.d[4]=ob4b_b(value)+ob4b_b(other);am_byte(r.d[5],r.d[4]>0xffU?0xffU:0U);r.d[4]=ob4b_b(r.d[4])|ob4b_b(r.d[5]);
        if(!ob4b_put(c,r.a[1],7,1,r.d[4]) || !ob4b_get(c,r.a[1],4,2,value))return false;am_word(r.d[4],r.d[4]*4U+value);
        r.pc=ob4b_w(r.d[4])<0x1000U?0x2840a:0x28406;return true;
    case 0x28406:am_word(r.d[4],0x1000);r.pc=0x2840a;return true;                            // MOVE.W #1000,D4.
    // MOVE.W D4,4(A1); LEA 4419e.l,A2; MOVEQ #0,D4; MOVE.B (A1),D4; ADD.W D4,D4; MOVE.W (A2,D4.W),D2; MOVE.W -80(A2,D4.W),D3; MOVE.W 4(A1),D5;
    // MULS.W D5,D2; MULS.W D5,D3; ADD.L (A7)+,D3; ADD.L (A7)+,D2; MOVE.L (A7)+,D1; MOVE.L (A7)+,D0; MOVE.L D2,D6; MOVE.L D3,D7;
    // ADD.L 53a2(A5),D6; ADD.L 53a6(A5),D7; MOVE.L D6,42(A6); MOVE.L D7,46(A6); MOVEM.L D0-D3,-(A7); MOVE.B 6(A1),b2(A6); JSR 49fc6.l.
    case 0x2840a:
        if(!ob4b_put(c,r.a[1],4,2,r.d[4]))return false;r.a[2]=0x4419e;
        if(!ob4b_angle(c,r.d[4]) || !ob4b_cos_sin(c,r.a[2],r.d[4],value,other))return false;am_word(r.d[2],value);am_word(r.d[3],other);
        if(!ob4b_get(c,r.a[1],4,2,value))return false;am_word(r.d[5],value);r.d[2]=ob4b_muls(r.d[2],r.d[5]);r.d[3]=ob4b_muls(r.d[3],r.d[5]);
        if(!am_pop(c,4,value))return false;r.d[3]+=value;if(!am_pop(c,4,value))return false;r.d[2]+=value;
        if(!am_pop(c,4,value))return false;r.d[1]=value;if(!am_pop(c,4,value))return false;r.d[0]=value;r.d[6]=r.d[2];r.d[7]=r.d[3];
        if(!ob4b_get(c,r.a[5],0x53a2,4,value))return false;r.d[6]+=value;if(!ob4b_get(c,r.a[5],0x53a6,4,value))return false;r.d[7]+=value;
        if(!ob4b_put(c,r.a[6],0x42,4,r.d[6]) || !ob4b_put(c,r.a[6],0x46,4,r.d[7]))return false;
        if(!am_push(c,4,r.d[3]) || !am_push(c,4,r.d[2]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;
        if(!ob4b_get(c,r.a[1],6,1,value) || !ob4b_put(c,r.a[6],0xb2,1,value))return false;return am_call(c,0x49fc6,0x28456);
    // MOVEM.L (A7)+,D0-D3; MOVE.W (A7)+,D7.
    case 0x28456:
        for(unsigned int i=0;i<4;++i){if(!am_pop(c,4,value))return false;r.d[i]=value;}
        if(!am_pop(c,2,value))return false;am_word(r.d[7],value);r.pc=0x2845c;return true;
    // ADDQ.W #8,D7; CMPI.W #38,D7; BCS.W 28468.
    case 0x2845c:am_word(r.d[7],r.d[7]+8U);r.pc=ob4b_w(r.d[7])<0x38U?0x28468:0x28466;return true;
    case 0x28466:r.d[7]=0;r.pc=0x28468;return true;                                          // MOVEQ #0,D7.
    case 0x28468:if(!ob4b_get(c,r.a[6],0xb0,2,value))return false;r.pc=ob4b_w(r.d[7])!=ob4b_w(value)?0x28366:0x28470;return true;   // CMP.W b0(A6),D7; BNE.W 28366.
    case 0x28470:if(!ob4b_get(c,r.a[6],0x63,1,value))return false;r.pc=ob4b_b(value)!=0U?0x28488:0x28478;return true;   // TST.B 63(A6); BNE.W 28488.
    case 0x28478:return ob4b_test(c,r.a[6],0x61,7,0x28482,0x28488);                          // BTST.B #7,61(A6); BEQ.W 28488.
    // ---- 2b6e6 (stage event sibling setup): MOVE.W #f2,20(A6); MOVE.L 20009c.l,22(A6); MOVE.L #2b3b8,9e(A6); MOVE.W #3d3,D0; MOVE.B #1,D1;
    // JSR 8ebe.l.
    case 0x2b6e6:if(!ob4b_bank_head(c,0xf2,0x20009c) || !ob4b_put(c,r.a[6],0x9e,4,0x2b3b8))return false;return ob4b_8ebe(c,0x3d3,1,0x2b70a);
    case 0x2b70a:return ob4b_8ebe(c,0x39d,1,0x2b718);
    case 0x2b718:return ob4b_8ebe(c,0x203,1,0x2b726);
    // MOVE.W #8080,8e(A6); BTST.B #0,15(A6); BNE.W 2b778.
    case 0x2b726:if(!ob4b_put(c,r.a[6],0x8e,2,0x8080))return false;return ob4b_test(c,r.a[6],0x15,0,0x2b778,0x2b736);
    case 0x2b736:case 0x2b778:return ob4b_28ae(c,0x41fe6,0xa,r.pc+0x10U);                    // MOVEA.L #41fe6,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x2b746:return ob4b_carry(c,0x2b774,0x2b74a);                                        // BCC.W 2b774 (C of 28ae).
    case 0x2b788:return ob4b_carry(c,0x2b7b6,0x2b78c);                                        // BCC.W 2b7b6 (C of 28ae).
    case 0x2b74a:return ob4b_link(c,0,0x2b774);
    case 0x2b78c:return ob4b_link(c,4,0x2b7b6);
    case 0x2b774:r.pc=0x2b7b6;return true;                                                    // BRA.W 2b7b6.
    case 0x2b7b8:if(!ob4b_bset(c,0x15,0))return false;r.pc=0x2b7be;return true;              // BSET.B #0,15(A6) (stage event value).
    case 0x2b7be:return am_call(c,0x2b6e6,0x2b7c2);                                           // BSR.W 2b6e6 (stage event value, 28ae child).
    case 0x2b7c2:r.pc=0x2b8b6;return true;                                                    // BRA.W 2b8b6.
    // ---- 4439e (helper): MOVEQ #0,D2; MOVE.B D1,D2; ADD.W D2,D2; MOVE.W D0,D1; LEA 4419e(PC),A0; MULS.W (A0,D2.W),D0; MULS.W -80(A0,D2.W),D1;
    // ASR.L #8,D0; ASR.L #8,D1; RTS.
    case 0x4439e:
        r.d[2]=ob4b_b(r.d[1])*2U;am_word(r.d[1],r.d[0]);r.a[0]=0x4419e;if(!ob4b_cos_sin(c,r.a[0],r.d[2],value,other))return false;
        r.d[0]=ob4b_asr_long(ob4b_muls(r.d[0],value),8);r.d[1]=ob4b_asr_long(ob4b_muls(r.d[1],other),8);return am_return(c);
    // ---- 49636 / 4964e (helper): JSR 4964e(PC).
    case 0x49636:return am_call(c,0x4964e,0x4963a);
    // SUB.W 42(A6),D0; SUB.W 46(A6),D1; JSR 44602.l.
    case 0x4963a:
        if(!ob4b_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],r.d[0]-value);if(!ob4b_get(c,r.a[6],0x46,2,value))return false;
        am_word(r.d[1],r.d[1]-value);return am_call(c,0x44602,0x49648);
    case 0x49648:am_word(r.d[0],r.d[0]&0xffU);return am_return(c);                           // ANDI.W #ff,D0; RTS.
    case 0x4964e:r.pc=r.a[0]==0U?0x49658:0x49662;return true;                                 // CMPA.L #0,A0; BNE.W 49662.
    case 0x49658:am_word(r.d[0],0xa0);am_word(r.d[1],0x180);return am_return(c);              // MOVE.W #a0,D0; MOVE.W #180,D1; RTS.
    // MOVE.W 42(A0),D0; MOVE.W 46(A0),D1; MOVEA.L 56(A0),A1; CMPA.W #0,A1; BEQ.W 496a4.
    case 0x49662:
        if(!ob4b_get(c,r.a[0],0x42,2,value))return false;am_word(r.d[0],value);if(!ob4b_get(c,r.a[0],0x46,2,value))return false;am_word(r.d[1],value);
        if(!ob4b_get(c,r.a[0],0x56,4,value))return false;r.a[1]=value;r.pc=r.a[1]==0U?0x496a4:0x49676;return true;
    // MOVE.W 4(A1),D2; MOVE.W 6(A1),D3; ASR.W #1,D2; ASR.W #1,D3; ADD.W (A1),D2; ADD.W 2(A1),D3; BTST.B #0,15(A0); BEQ.W 49694.
    case 0x49676:
        if(!ob4b_get(c,r.a[1],4,2,value))return false;am_word(r.d[2],value);if(!ob4b_get(c,r.a[1],6,2,value))return false;am_word(r.d[3],value);
        ob4b_asr_word1(r.d[2]);ob4b_asr_word1(r.d[3]);if(!ob4b_get(c,r.a[1],0,2,value))return false;am_word(r.d[2],r.d[2]+value);
        if(!ob4b_get(c,r.a[1],2,2,value))return false;am_word(r.d[3],r.d[3]+value);return ob4b_test(c,r.a[0],0x15,0,0x49692,0x49694);
    case 0x49692:am_word(r.d[2],0U-ob4b_w(r.d[2]));r.pc=0x49694;return true;                 // NEG.W D2.
    case 0x49694:return ob4b_test(c,r.a[0],0x15,1,0x4969e,0x496a0);                          // BTST.B #1,15(A0); BEQ.W 496a0.
    case 0x4969e:am_word(r.d[3],0U-ob4b_w(r.d[3]));r.pc=0x496a0;return true;                 // NEG.W D3.
    case 0x496a0:am_word(r.d[0],r.d[0]+r.d[2]);am_word(r.d[1],r.d[1]+r.d[3]);r.pc=0x496a4;return true;   // ADD.W D2,D0; ADD.W D3,D1.
    // ---- d206a (28ae child): MOVE.W #22,D0; MOVE.W #3,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xd206a:am_word(r.d[0],0x22);am_word(r.d[1],3);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xd207c);
    case 0xd207c:return ob4b_bank_anim(c,0xd2,0x20008c,0xc,0xd20a4);                          // ...; MOVEA.L c(A1),A1; JSR 49f8c.l.
    // LEA d3e64(PC),A0; MOVE.L A0,92(A6); BRA.W d239c.
    case 0xd20a4:r.a[0]=0xd3e64;if(!ob4b_put(c,r.a[6],0x92,4,r.a[0]))return false;r.pc=0xd239c;return true;
    // ---- e74f8 (U06 script handler): MOVE.W (A0)+,D0; MOVE.L A0,-(A7); JSR e7504(PC,D0.W) (the live target goes through the routing).
    case 0xe74f8:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.a[0]+=2U;if(!am_push(c,4,r.a[0]))return false;
        return am_call(c,am_index(0xe7504,r.d[0]),0xe7500);
    case 0xe7500:if(!am_pop(c,4,value))return false;r.a[0]=value;return am_return(c);        // MOVEA.L (A7)+,A0; RTS.
    case 0xe7504:r.pc=0xe750c;return true;                                                    // BRA.W e750c (jump table entry 0).
    case 0xe7508:r.pc=0xe7534;return true;                                                    // BRA.W e7534 (jump table entry 4).
    case 0xe750c:return ob4b_28ae(c,0x2b7be,0,0xe751c);                                       // MOVEA.L #2b7be,A0; MOVE.W #0,D0; JSR 28ae.l.
    // MOVE.W #ffff,76(A0); MOVE.L #a00000,2e(A0); MOVE.L #1ff0000,32(A0); RTS.
    case 0xe751c:
        if(!ob4b_put(c,r.a[0],0x76,2,0xffff) || !ob4b_put(c,r.a[0],0x2e,4,0xa00000) || !ob4b_put(c,r.a[0],0x32,4,0x1ff0000))return false;return am_return(c);
    case 0xe7534:return ob4b_28ae(c,0xe7996,0,0xe7544);                                       // MOVEA.L #e7996,A0; MOVE.W #0,D0; JSR 28ae.l.
    // ---- e7996 (28ae child): MOVE.W #e0ef,68(A6); MOVE.W #e0ef,1e(A6); MOVE.L #1400000,2e(A6); MOVE.L #1800000,32(A6); MOVE.L #fff80000,36(A6);
    // CLR.L 3a(A6); MOVE.W #23,D0; MOVE.W #c,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xe7996:
        if(!ob4b_pair68(c,0xe0ef) || !ob4b_put(c,r.a[6],0x2e,4,0x1400000) || !ob4b_put(c,r.a[6],0x32,4,0x1800000) ||
           !ob4b_put(c,r.a[6],0x36,4,0xfff80000U) || !ob4b_put(c,r.a[6],0x3a,4,0))return false;
        am_word(r.d[0],0x23);am_word(r.d[1],0xc);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xe79d0);
    case 0xe79d0:return ob4b_bank_anim(c,0xda,0x200090,0x30,0xe79f8);                         // ...; MOVEA.L 30(A1),A1; JSR 49f8c.l.
    case 0xe79f8:return ob4b_install(c,0xe79fe);
    case 0xe79fe:return am_call(c,0x43ea4,0xe7a04);                                           // JSR 43ea4.l (installed value).
    case 0xe7a04:r.a[0]=0xe7978;return am_call(c,0x4ae4a,0xe7a0e);                            // LEA e7978(PC),A0; JSR 4ae4a.l.
    case 0xe7a0e:r.pc=ob4b_w(r.d[0])!=0U?0xe7a1c:0xe7a14;return true;                        // TST.W D0; BNE.W e7a1c.
    case 0xe7a1c:return ob4b_28ae(c,0xd1d08,0x1e,0xe7a2c);                                    // MOVEA.L #d1d08,A0; MOVE.W #1e,D0; JSR 28ae.l.
    case 0xe7a2c:return ob4b_carry(c,0xe7a3e,0xe7a30);                                        // BCC.W e7a3e (C of 28ae).
    case 0xe7a30:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0xe7a3a);       // CLR.W D0; CLR.W D1; JSR 4970a.l.
    case 0xe7a3a:r.carry=AnimationCarrySet;r.pc=0xe7a3e;return true;                         // ORI.B #1,CCR.
    default:return am_error(c,"unsupported animation objects b4b PC");
    }
}
}
