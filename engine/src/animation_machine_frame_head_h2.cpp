#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t fh2_b(std::uint32_t value) {return value&255U;}
std::uint32_t fh2_w(std::uint32_t value) {return value&65535U;}
// d16(An): base + sign-extended displacement WORD (modulo 2^32).
std::uint32_t fh2_at(std::uint32_t base,std::uint32_t displacement) {return am_index(base,displacement);}
// (An,Dn.W): base + sign-extended WORD index (modulo 2^32).
std::uint32_t fh2_ix(std::uint32_t base,std::uint32_t index) {return base+am_extend_word(index&65535U);}
// MOVE.B port.l,D0; NOT.B D0: one declared input BYTE (380000 / 300000 / 340000) from the external-read queue (am_read: empty queue
// "animation machine external read queue empty", other front entry "... queue mismatch"; consumption is committed with the run).
bool fh2_input(AnimationMachineContext& c,std::uint32_t address) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;am_byte(c.s.d[0],fh2_b(~value));return true;
}
// Latch of one input block at A0 (+1 previous, +2 current, +3 new presses):
// MOVE.B 2(A0),D1; MOVE.B D1,1(A0); MOVE.B D0,2(A0); EOR.B D0,D1; AND.B D0,D1; MOVE.B D1,3(A0); BEQ.W repeat_pc (else edge_pc).
bool fh2_latch(AnimationMachineContext& c,std::uint32_t edge_pc,std::uint32_t repeat_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,r.a[0]+2U,1,value))return false;am_byte(r.d[1],value);
    if(!am_write(c,r.a[0]+1U,1,fh2_b(r.d[1])) || !am_write(c,r.a[0]+2U,1,fh2_b(r.d[0])))return false;
    am_byte(r.d[1],(fh2_b(r.d[1])^fh2_b(r.d[0]))&fh2_b(r.d[0]));
    if(!am_write(c,r.a[0]+3U,1,fh2_b(r.d[1])))return false;r.pc=fh2_b(r.d[1])==0U?repeat_pc:edge_pc;return true;
}
// LEA disp(A5),A0 followed by the latch.
bool fh2_block(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t edge_pc,std::uint32_t repeat_pc) {
    c.s.a[0]=fh2_at(c.s.a[5],displacement);return fh2_latch(c,edge_pc,repeat_pc);
}
// Edge: MOVE.B D1,4(A0); MOVE.B 104cd2.l,5(A0) (repeat delay); BRA.W next_pc.
bool fh2_edge(AnimationMachineContext& c,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_write(c,r.a[0]+4U,1,fh2_b(r.d[1])) || !am_read(c,0x104cd2,1,value) || !am_write(c,r.a[0]+5U,1,value))return false;
    r.pc=next_pc;return true;
}
// Repeat: SUBQ.B #1,5(A0); BNE.W clear_pc (else expire_pc).
bool fh2_repeat(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t expire_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!am_read(c,r.a[0]+5U,1,value))return false;
    value=fh2_b(value-1U);if(!am_write(c,r.a[0]+5U,1,value))return false;r.pc=value!=0U?clear_pc:expire_pc;return true;
}
// Expire: MOVE.B D0,4(A0); MOVE.B 104cd3.l,5(A0) (repeat rate); BRA.W next_pc.
bool fh2_expire(AnimationMachineContext& c,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_write(c,r.a[0]+4U,1,fh2_b(r.d[0])) || !am_read(c,0x104cd3,1,value) || !am_write(c,r.a[0]+5U,1,value))return false;
    r.pc=next_pc;return true;
}
// Clear: CLR.B 4(A0) (falls into next_pc).
bool fh2_clear(AnimationMachineContext& c,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[0]+4U,1,0))return false;c.s.pc=next_pc;return true;
}
// MOVE.B src,dst (memory to memory).
bool fh2_copy_byte(AnimationMachineContext& c,std::uint32_t source,std::uint32_t target) {
    std::uint32_t value=0;return am_read(c,source,1,value) && am_write(c,target,1,value);
}
// SUBQ.B #1 / ADDQ.B #1 / ORI.B #mask on a memory BYTE (read, then write); returns the old value.
bool fh2_rmw_byte(AnimationMachineContext& c,std::uint32_t address,int delta,std::uint32_t or_mask,std::uint32_t& old) {
    if(!am_read(c,address,1,old))return false;
    std::uint32_t value=old;if(delta>0)value+=1U;else if(delta<0)value-=1U;value|=or_mask;return am_write(c,address,1,fh2_b(value));
}
// BTST.B #bit,address (memory: bit mod 8); true when the bit is set.
bool fh2_test(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;set=((value>>(bit&7U))&1U)!=0;return true;
}
// TST.B address; true when the BYTE is not zero.
bool fh2_nonzero(AnimationMachineContext& c,std::uint32_t address,bool& nonzero) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;nonzero=fh2_b(value)!=0U;return true;
}
// MOVE.B p(A5),D6; MOVE.B q(A5),D7; EOR.B D6,D7; AND.B D6,D7; OR.B D7,t(A5) (one 92a8 half).
bool fh2_accumulate(AnimationMachineContext& c,std::uint32_t source,std::uint32_t snapshot,std::uint32_t target) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,fh2_at(r.a[5],source),1,value))return false;am_byte(r.d[6],value);
    if(!am_read(c,fh2_at(r.a[5],snapshot),1,value))return false;am_byte(r.d[7],value);
    am_byte(r.d[7],(fh2_b(r.d[7])^fh2_b(r.d[6]))&fh2_b(r.d[6]));
    if(!am_read(c,fh2_at(r.a[5],target),1,value))return false;return am_write(c,fh2_at(r.a[5],target),1,fh2_b(value|r.d[7]));
}
}
// F5 frame head H2 (154 block starts): the input sampler 31d6 (system 380000, P1 300000, P2 340000 latches with edge / repeat,
// mode 0 logical copies, mode 1 replay 352a or recorder 349c (reached only when ROM WORD 0180 != 0), mode >= 2 releases), the
// repeat setter 313c, the start request 9086, the pause / menu request 9136 with its string helper 3902 and the pause menu renderer
// 9332 (installed by 92ec through a2b8). Input BYTEs come from the declared external-read queue. Boundaries (other executors):
// 386e 3650 3918 a29c a2b8 a370 (card menu), ca9e (screen), e84c8 (933e JMP). The menu callback JSR (A0) at 931a is the D8 guard.
// No carry consumer, no known-carry producer.
bool animation_frame_head_h2_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool flag=false;
    switch(r.pc) {
    // ---- 313c repeat delay / rate (104cd2 = 10, 104cd3 = 02).
    case 0x313c:if(!am_write(c,fh2_at(r.a[5],0xccd2),2,0x1002))return false;return am_return(c);
    // ---- 31d6 input sampler.
    case 0x31d6:
        // MOVE.B 380000.l,D0; NOT.B D0; ANDI.B #f,D0; MOVE.B -334c(A5),D1; MOVE.B D0,-334c(A5); EOR.B D0,D1; AND.B D0,D1;
        // MOVE.B D1,-334b(A5); MOVE.B 300000.l,D0; NOT.B D0; LEA -334a(A5),A0; latch.
        if(!fh2_input(c,0x380000))return false;am_byte(r.d[0],r.d[0]&15U);
        if(!am_read(c,fh2_at(r.a[5],0xccb4),1,value))return false;am_byte(r.d[1],value);
        if(!am_write(c,fh2_at(r.a[5],0xccb4),1,fh2_b(r.d[0])))return false;
        am_byte(r.d[1],(fh2_b(r.d[1])^fh2_b(r.d[0]))&fh2_b(r.d[0]));
        if(!am_write(c,fh2_at(r.a[5],0xccb5),1,fh2_b(r.d[1])) || !fh2_input(c,0x300000))return false;
        return fh2_block(c,0xccb6,0x3216,0x3226);
    case 0x3216:return fh2_edge(c,0x3242);
    case 0x3226:return fh2_repeat(c,0x323e,0x322e);
    case 0x322e:return fh2_expire(c,0x3242);
    case 0x323e:return fh2_clear(c,0x3242);
    case 0x3242:if(!fh2_input(c,0x340000))return false;return fh2_block(c,0xccbc,0x3266,0x3276);
    case 0x3266:return fh2_edge(c,0x3292);
    case 0x3276:return fh2_repeat(c,0x328e,0x327e);
    case 0x327e:return fh2_expire(c,0x3292);
    case 0x328e:return fh2_clear(c,0x3292);
    case 0x3292:if(!am_read(c,fh2_at(r.a[5],0xccd4),1,value))return false;r.pc=fh2_b(value)!=0U?0x334e:0x329c;return true;
    // Mode 0: logical P1 / P2 blocks from the devices (first BYTE from the BIOS copies 10fd94 / 10fd9a).
    case 0x329c:
        if(!fh2_copy_byte(c,0x10fd94,fh2_at(r.a[5],0xcca8)) || !fh2_input(c,0x300000))return false;
        return fh2_block(c,0xcca8,0x32c8,0x32d8);
    case 0x32c8:return fh2_edge(c,0x32f4);
    case 0x32d8:return fh2_repeat(c,0x32f0,0x32e0);
    case 0x32e0:return fh2_expire(c,0x32f4);
    case 0x32f0:return fh2_clear(c,0x32f4);
    case 0x32f4:
        if(!fh2_copy_byte(c,0x10fd9a,fh2_at(r.a[5],0xccae)) || !fh2_input(c,0x340000))return false;
        return fh2_block(c,0xccae,0x3320,0x3330);
    case 0x3320:return fh2_edge(c,0x334c);
    case 0x3330:return fh2_repeat(c,0x3348,0x3338);
    case 0x3338:return fh2_expire(c,0x334c);
    case 0x3348:return fh2_clear(c,0x334c);
    case 0x334c:case 0x3404:case 0x349a:return am_return(c);
    // Mode 1: replay (or the recorder when ROM WORD 0180 != 0), then the logical blocks from WORD 104cc2.
    case 0x334e:if(!am_read(c,fh2_at(r.a[5],0xccd4),1,value))return false;r.pc=fh2_b(value)!=1U?0x3406:0x3358;return true;
    case 0x3358:if(!am_read(c,0x180,2,value))return false;r.pc=fh2_w(value)==0U?0x3368:0x3360;return true; // TST.W 0180.w (live bus).
    case 0x3360:return am_call(c,0x349c,0x3364);
    case 0x3364:r.pc=0x336c;return true;                                             // BRA.W 336c.
    case 0x3368:return am_call(c,0x352a,0x336c);
    case 0x336c:
        if(!am_read(c,fh2_at(r.a[5],0xccc2),1,value))return false;am_byte(r.d[0],value);return fh2_block(c,0xcca8,0x338c,0x339c);
    case 0x338c:return fh2_edge(c,0x33b8);
    case 0x339c:return fh2_repeat(c,0x33b4,0x33a4);
    case 0x33a4:return fh2_expire(c,0x33b8);
    case 0x33b4:return fh2_clear(c,0x33b8);
    case 0x33b8:
        if(!am_read(c,fh2_at(r.a[5],0xccc3),1,value))return false;am_byte(r.d[0],value);return fh2_block(c,0xccae,0x33d8,0x33e8);
    case 0x33d8:return fh2_edge(c,0x3404);
    case 0x33e8:return fh2_repeat(c,0x3400,0x33f0);
    case 0x33f0:return fh2_expire(c,0x3404);
    case 0x3400:return fh2_clear(c,0x3404);
    // Mode >= 2: both logical blocks latch zero.
    case 0x3406:am_byte(r.d[0],0);return fh2_block(c,0xcca8,0x3424,0x3434);
    case 0x3424:return fh2_edge(c,0x3450);
    case 0x3434:return fh2_repeat(c,0x344c,0x343c);
    case 0x343c:return fh2_expire(c,0x3450);
    case 0x344c:return fh2_clear(c,0x3450);
    case 0x3450:am_byte(r.d[0],0);return fh2_block(c,0xccae,0x346e,0x347e);
    case 0x346e:return fh2_edge(c,0x349a);
    case 0x347e:return fh2_repeat(c,0x3496,0x3486);
    case 0x3486:return fh2_expire(c,0x349a);
    case 0x3496:return fh2_clear(c,0x349a);
    // ---- 349c input recorder (run-length nibbles into the buffer LONG -3338(A5), limit 600).
    case 0x349c:
        // MOVE.B 300000.l,D0; NOT.B D0; LSL.W #8,D0; MOVE.B 340000.l,D0; NOT.B D0; MOVE.W -333e(A5),D1; MOVE.W D0,-333e(A5);
        // EOR.W D1,D0; MOVEA.L -3338(A5),A0; MOVE.B -3330(A5),D5; MOVE.W -3332(A5),D6; MOVE.W -3334(A5),D7; CMP.W D6,D7; SNE.B D1;
        // ORI.B #f,D1; CMP.B D5,D1; BNE.W 34e6.
        if(!fh2_input(c,0x300000))return false;am_word(r.d[0],fh2_w(r.d[0])<<8);if(!fh2_input(c,0x340000))return false;
        if(!am_read(c,fh2_at(r.a[5],0xccc2),2,value))return false;am_word(r.d[1],value);
        if(!am_write(c,fh2_at(r.a[5],0xccc2),2,fh2_w(r.d[0])))return false;am_word(r.d[0],fh2_w(r.d[0])^fh2_w(r.d[1]));
        if(!am_read(c,fh2_at(r.a[5],0xccc8),4,value))return false;r.a[0]=value;
        if(!am_read(c,fh2_at(r.a[5],0xccd0),1,value))return false;am_byte(r.d[5],value);
        if(!am_read(c,fh2_at(r.a[5],0xccce),2,value))return false;am_word(r.d[6],value);
        if(!am_read(c,fh2_at(r.a[5],0xcccc),2,value))return false;am_word(r.d[7],value);
        am_byte(r.d[1],fh2_w(r.d[7])!=fh2_w(r.d[6])?0xffU:0U);am_byte(r.d[1],r.d[1]|15U);
        r.pc=fh2_b(r.d[1])!=fh2_b(r.d[5])?0x34e6:0x34d6;return true;
    case 0x34d6:
        // MOVE.B D5,(A0,D6.W); ADDQ.W #1,D6; CMPI.W #600,D6; BCC.W 3522.
        if(!am_write(c,fh2_ix(r.a[0],r.d[6]),1,fh2_b(r.d[5])))return false;am_word(r.d[6],r.d[6]+1U);
        r.pc=fh2_w(r.d[6])>=0x600U?0x3522:0x34e4;return true;
    case 0x34e4:am_byte(r.d[5],0);r.pc=0x34e6;return true;                         // CLR.B D5.
    case 0x34e6:r.pc=fh2_w(r.d[0])==0U?0x3512:0x34ec;return true;                 // TST.W D0; BEQ.W 3512.
    case 0x34ec:r.d[1]=15U;r.pc=0x34ee;return true;                                 // MOVEQ #f,D1.
    case 0x34ee: {
        // LSL.W #1,D0; BCC.W 350e (C = the bit shifted out of D0.W bit 15).
        const bool out=(r.d[0]&0x8000U)!=0;am_word(r.d[0],fh2_w(r.d[0])<<1);r.pc=out?0x34f4:0x350e;return true;
    }
    case 0x34f4:
        // MOVE.B D5,(A0,D6.W); CLR.W D5; ADDQ.W #1,D6; MOVE.B D1,D2; LSL.B #4,D2; OR.B D2,(A0,D7.W); MOVE.W D6,D7;
        // CMPI.W #600,D6; BCC.W 3522; DBRA D1,34ee.
        if(!am_write(c,fh2_ix(r.a[0],r.d[6]),1,fh2_b(r.d[5])))return false;am_word(r.d[5],0);am_word(r.d[6],r.d[6]+1U);
        am_byte(r.d[2],r.d[1]);am_byte(r.d[2],fh2_b(r.d[2])<<4);
        if(!am_read(c,fh2_ix(r.a[0],r.d[7]),1,value) || !am_write(c,fh2_ix(r.a[0],r.d[7]),1,fh2_b(value|r.d[2])))return false;
        am_word(r.d[7],r.d[6]);if(fh2_w(r.d[6])>=0x600U) {r.pc=0x3522;return true;}
        am_word(r.d[1],r.d[1]-1U);r.pc=fh2_w(r.d[1])!=0xffffU?0x34ee:0x3512;return true;
    case 0x350e:am_word(r.d[1],r.d[1]-1U);r.pc=fh2_w(r.d[1])!=0xffffU?0x34ee:0x3512;return true; // DBRA D1,34ee.
    case 0x3512:
        if(!am_write(c,fh2_at(r.a[5],0xccce),2,fh2_w(r.d[6])) || !am_write(c,fh2_at(r.a[5],0xcccc),2,fh2_w(r.d[7])))return false;
        am_byte(r.d[5],r.d[5]+1U);if(!am_write(c,fh2_at(r.a[5],0xccd0),1,fh2_b(r.d[5])))return false;return am_return(c);
    case 0x3522:case 0x359a:if(!am_write(c,fh2_at(r.a[5],0xccd4),1,2))return false;return am_return(c); // MOVE.B #2,-332c(A5); RTS.
    // ---- 352a input replay (run-length nibbles from the stream LONG 104cc4, live bus).
    case 0x352a:
        if(!am_read(c,0x104cc4,4,value))return false;r.a[0]=value;
        if(!am_read(c,fh2_at(r.a[5],0xccce),2,value))return false;am_word(r.d[7],value);r.pc=0x3534;return true;
    case 0x3534:r.pc=fh2_w(r.d[7])>=0x600U?0x359a:0x353c;return true;             // CMPI.W #600,D7; BCC.W 359a.
    case 0x353c:
        // MOVE.B (A0,D7.W),D0; MOVE.B #ff,D1; CMP.W -3334(A5),D7; BNE.W 3552.
        if(!am_read(c,fh2_ix(r.a[0],r.d[7]),1,value))return false;am_byte(r.d[0],value);am_byte(r.d[1],0xff);
        if(!am_read(c,fh2_at(r.a[5],0xcccc),2,value))return false;r.pc=fh2_w(r.d[7])!=fh2_w(value)?0x3552:0x354c;return true;
    case 0x354c:am_byte(r.d[1],15U);am_byte(r.d[0],r.d[0]&15U);r.pc=0x3552;return true; // MOVE.B #f,D1; AND.B D1,D0.
    case 0x3552:if(!am_read(c,fh2_at(r.a[5],0xccd0),1,value))return false;r.pc=fh2_b(r.d[0])!=fh2_b(value)?0x3590:0x355a;return true;
    case 0x355a:
        // MOVE.B #0,-3330(A5); ADDQ.W #1,D7; CMP.B D1,D0; BNE.W 3572.
        if(!am_write(c,fh2_at(r.a[5],0xccd0),1,0))return false;am_word(r.d[7],r.d[7]+1U);
        r.pc=fh2_b(r.d[0])!=fh2_b(r.d[1])?0x3572:0x3568;return true;
    case 0x3568:if(!am_read(c,fh2_ix(r.a[0],r.d[7]),1,value))return false;r.pc=fh2_b(value)!=0U?0x3590:0x3570;return true;
    case 0x3570:am_word(r.d[7],r.d[7]+1U);r.pc=0x3572;return true;               // ADDQ.W #1,D7.
    case 0x3572:
        // MOVE.W -3334(A5),D0; MOVE.W D7,-3334(A5); MOVE.B (A0,D0.W),D0; LSR.B #4,D0; MOVE.W 104cc2.l,D1; BCHG.B D0,D1
        // (register: bit D0 mod 32); MOVE.W D1,104cc2.l; BRA.B 3534.
        if(!am_read(c,fh2_at(r.a[5],0xcccc),2,value))return false;am_word(r.d[0],value);
        if(!am_write(c,fh2_at(r.a[5],0xcccc),2,fh2_w(r.d[7])) || !am_read(c,fh2_ix(r.a[0],r.d[0]),1,value))return false;
        am_byte(r.d[0],value);am_byte(r.d[0],fh2_b(r.d[0])>>4);
        if(!am_read(c,0x104cc2,2,value))return false;am_word(r.d[1],value);r.d[1]^=1U<<(r.d[0]&31U);
        if(!am_write(c,0x104cc2,2,fh2_w(r.d[1])))return false;r.pc=0x3534;return true;
    case 0x3590:
        if(!am_write(c,fh2_at(r.a[5],0xccce),2,fh2_w(r.d[7])) || !fh2_rmw_byte(c,fh2_at(r.a[5],0xccd0),1,0,other))return false;
        return am_return(c);
    // ---- 3902 string loop (386e text step, 3650 glyph output).
    case 0x3902:am_word(r.d[3],r.d[0]);r.pc=0x3904;return true;                  // MOVE.W D0,D3.
    case 0x3904:return am_call(c,0x386e,0x3908);
    case 0x3908:r.pc=fh2_b(r.d[2])!=0U?0x3912:0x3910;return true;               // CMPI.B #0,D2; BNE.W 3912.
    case 0x3910:return am_return(c);
    case 0x3912:return am_call(c,0x3650,0x3916);
    case 0x3916:r.pc=0x3904;return true;                                           // BRA.B 3904.
    // ---- 9086 start request (D0 bit 1 = P1, bit 3 = P2).
    case 0x9086:
        r.d[0]=0;if(!am_read(c,fh2_at(r.a[5],0x8012),1,value))return false;r.pc=fh2_b(value)!=2U?0x910e:0x9092;return true;
    case 0x9092:if(!fh2_nonzero(c,fh2_at(r.a[5],0x7d82),flag))return false;r.pc=flag?0x90a2:0x909a;return true;
    case 0x909a:if(!am_read(c,fh2_at(r.a[5],0xccb5),1,value))return false;am_byte(r.d[0],value);r.pc=0x90d2;return true;
    case 0x90a2:if(!fh2_nonzero(c,fh2_at(r.a[5],0x7002),flag))return false;r.pc=flag?0x90aa:0x90d2;return true;
    case 0x90aa:r.d[0]=0;if(!fh2_test(c,fh2_at(r.a[5],0xccb9),7,flag))return false;r.pc=flag?0x90b6:0x90ba;return true;
    case 0x90b6:r.d[0]|=2U;r.pc=0x90ba;return true;                                // BSET.B #1,D0.
    case 0x90ba:if(!fh2_test(c,fh2_at(r.a[5],0xccbf),7,flag))return false;r.pc=flag?0x90c4:0x90c8;return true;
    case 0x90c4:r.d[0]|=8U;r.pc=0x90c8;return true;                                // BSET.B #3,D0.
    case 0x90c8:
        // MOVE.B -334c(A5),D1; ANDI.B #a,D1; AND.B D1,D0.
        if(!am_read(c,fh2_at(r.a[5],0xccb4),1,value))return false;am_byte(r.d[1],value&10U);am_byte(r.d[0],r.d[0]&r.d[1]);
        r.pc=0x90d2;return true;
    case 0x90d2:if(!am_read(c,fh2_at(r.a[5],0x7db6),1,value))return false;r.pc=fh2_b(value)!=0U?0x90e0:0x90dc;return true;
    case 0x90dc:case 0x90ea:r.d[0]&=~2U;r.pc=r.pc==0x90dcU?0x90e0:0x90ee;return true; // BCLR.B #1,D0.
    case 0x90e0:if(!am_read(c,fh2_at(r.a[5],0x7db6),1,value))return false;r.pc=fh2_b(value)!=3U?0x90ee:0x90ea;return true;
    case 0x90ee:if(!am_read(c,fh2_at(r.a[5],0x7db7),1,value))return false;r.pc=fh2_b(value)!=0U?0x90fc:0x90f8;return true;
    case 0x90f8:case 0x9106:r.d[0]&=~8U;r.pc=r.pc==0x90f8U?0x90fc:0x910a;return true; // BCLR.B #3,D0.
    case 0x90fc:if(!am_read(c,fh2_at(r.a[5],0x7db7),1,value))return false;r.pc=fh2_b(value)!=3U?0x910a:0x9106;return true;
    case 0x910a:r.pc=0x9134;return true;                                           // BRA.W 9134.
    case 0x910e:if(!fh2_nonzero(c,fh2_at(r.a[5],0x7002),flag))return false;r.pc=flag?0x9116:0x9134;return true;
    case 0x9116:r.d[0]=0;if(!fh2_test(c,fh2_at(r.a[5],0xccb9),7,flag))return false;r.pc=flag?0x9122:0x9126;return true;
    case 0x9122:r.d[0]|=2U;r.pc=0x9126;return true;                                // BSET.B #1,D0.
    case 0x9126:if(!fh2_test(c,fh2_at(r.a[5],0xccbf),7,flag))return false;r.pc=flag?0x9130:0x9134;return true;
    case 0x9130:r.d[0]|=8U;r.pc=0x9134;return true;                                // BSET.B #3,D0.
    case 0x9134:return am_return(c);
    // ---- 9136 pause / menu request (D0.B = 0: paused this frame).
    case 0x9136:if(!fh2_nonzero(c,fh2_at(r.a[5],0xfdf0),flag))return false;r.pc=flag?0x91c2:0x913e;return true;
    case 0x913e:
        if(!am_read(c,fh2_at(r.a[5],0xfdf1),1,value))return false;am_byte(r.d[0],value);r.pc=fh2_b(value)==0U?0x9154:0x9146;return true;
    case 0x9146:
        if(!am_write(c,fh2_at(r.a[5],0xfdf0),1,fh2_b(r.d[0])) || !am_write(c,fh2_at(r.a[5],0xfdf1),1,0))return false;r.pc=0x919a;return true;
    case 0x9154:if(!fh2_test(c,0x10f000,1,flag))return false;r.pc=flag?0x9168:0x9160;return true;
    case 0x9160:if(!fh2_nonzero(c,fh2_at(r.a[5],0xfdef),flag))return false;r.pc=flag?0x9196:0x9168;return true;
    case 0x9168:return am_call(c,0x9086,0x916c);
    case 0x916c:r.pc=fh2_b(r.d[0])==0U?0x9196:0x9172;return true;                // TST.B D0; BEQ.W 9196.
    case 0x9172:r.pc=(r.d[0]&2U)==0U?0x9184:0x917a;return true;                   // BTST.B #1,D0; BEQ.W 9184.
    case 0x917a:case 0x918c:
        // ORI.B #1 / #2,-210(A5); BRA.W 919a.
        if(!fh2_rmw_byte(c,fh2_at(r.a[5],0xfdf0),0,r.pc==0x917aU?1U:2U,other))return false;r.pc=0x919a;return true;
    case 0x9184:r.pc=(r.d[0]&8U)==0U?0x9196:0x918c;return true;                   // BTST.B #3,D0; BEQ.W 9196.
    case 0x9196:r.d[0]=1;return am_return(c);                                      // MOVEQ #1,D0; RTS.
    case 0x919a:if(!am_write(c,0x107df6,4,0))return false;return am_call(c,0x313c,0x91aa);
    case 0x91aa:
        if(!am_write(c,fh2_at(r.a[5],0xfdf3),1,0) || !fh2_copy_byte(c,fh2_at(r.a[5],0xccaa),fh2_at(r.a[5],0xfdfc)) ||
            !fh2_copy_byte(c,fh2_at(r.a[5],0xccb0),fh2_at(r.a[5],0xfdfd)))return false;
        r.d[0]=0;r.pc=0x92a8;return true;
    case 0x91c2:if(!fh2_nonzero(c,0x107dee,flag))return false;r.pc=flag?0x92fc:0x91cc;return true;
    case 0x91cc:return am_call(c,0x9086,0x91d0);
    case 0x91d0:if(!fh2_test(c,fh2_at(r.a[5],0xfdf0),0,flag))return false;r.pc=flag?0x91da:0x91fe;return true;
    case 0x91da:r.pc=(r.d[0]&2U)!=0U?0x928a:0x91e2;return true;                   // BTST.B #1,D0; BNE.W 928a.
    case 0x91e2:if(!fh2_nonzero(c,fh2_at(r.a[5],0x7002),flag))return false;r.pc=flag?0x91ea:0x91fe;return true;
    case 0x91ea:if(!fh2_test(c,fh2_at(r.a[5],0xccb5),0,flag))return false;r.pc=flag?0x925e:0x91f4;return true;
    case 0x91f4:if(!fh2_test(c,fh2_at(r.a[5],0xccb4),0,flag))return false;r.pc=flag?0x926c:0x91fe;return true;
    case 0x91fe:if(!fh2_test(c,fh2_at(r.a[5],0xfdf0),1,flag))return false;r.pc=flag?0x9208:0x922c;return true;
    case 0x9208:r.pc=(r.d[0]&8U)!=0U?0x928a:0x9210;return true;                   // BTST.B #3,D0; BNE.W 928a.
    case 0x9210:if(!fh2_nonzero(c,fh2_at(r.a[5],0x7002),flag))return false;r.pc=flag?0x9218:0x922c;return true;
    case 0x9218:if(!fh2_test(c,fh2_at(r.a[5],0xccb5),2,flag))return false;r.pc=flag?0x925e:0x9222;return true;
    case 0x9222:if(!fh2_test(c,fh2_at(r.a[5],0xccb4),2,flag))return false;r.pc=flag?0x926c:0x922c;return true;
    case 0x922c:if(!fh2_test(c,0x10f001,6,flag))return false;r.pc=flag?0x9256:0x9238;return true;
    case 0x9238:
        // LEA 9079(PC),A0; SUBQ.B #1,-20d(A5); MOVE.B -20d(A5),D7; ANDI.B #30,D7; BEQ.W 9250.
        r.a[0]=0x9079;if(!fh2_rmw_byte(c,fh2_at(r.a[5],0xfdf3),-1,0,other))return false;
        if(!am_read(c,fh2_at(r.a[5],0xfdf3),1,value))return false;am_byte(r.d[7],value&0x30U);
        r.pc=fh2_b(r.d[7])==0U?0x9250:0x924c;return true;
    case 0x924c:r.a[0]=0x9068;r.pc=0x9250;return true;                            // LEA 9068(PC),A0.
    case 0x9250:return am_call(c,0x3902,0x9256);
    case 0x9256:case 0x9282:case 0x932a:am_word(r.d[0],0);r.pc=0x92a8;return true; // MOVE.W #0,D0; BRA.W 92a8.
    case 0x925e:if(!am_write(c,fh2_at(r.a[5],0xfdf2),1,15))return false;am_word(r.d[0],2);r.pc=0x92a8;return true;
    case 0x926c:
        // SUBQ.B #1,-20e(A5); BCC.W 9282 (no borrow: the old BYTE was not 0).
        if(!fh2_rmw_byte(c,fh2_at(r.a[5],0xfdf2),-1,0,other))return false;r.pc=fh2_b(other)!=0U?0x9282:0x9274;return true;
    case 0x9274:if(!am_write(c,fh2_at(r.a[5],0xfdf2),1,1))return false;am_word(r.d[0],2);r.pc=0x92a8;return true;
    case 0x928a:r.pc=0x92ce;return true;                                           // BRA.W 92ce.
    case 0x928e:r.a[1]=0xe84c8;r.a[0]=0x9079;return am_call(c,0x3918,0x929e);
    case 0x929e:
        if(!am_write(c,fh2_at(r.a[5],0xfdee),1,0) || !am_write(c,fh2_at(r.a[5],0xfdf0),1,0))return false;r.d[0]=1;r.pc=0x92a8;return true;
    case 0x92a8:
        if(!fh2_accumulate(c,0xccaa,0xfdfc,0xccab) || !fh2_accumulate(c,0xccb0,0xfdfd,0xccb1) ||
            !fh2_rmw_byte(c,fh2_at(r.a[5],0xfdf3),-1,0,other))return false;
        return am_return(c);
    case 0x92ce:return am_call(c,0xca9e,0x92d4);
    case 0x92d4:
        if(!am_write(c,fh2_at(r.a[5],0xfdee),1,0xff))return false;r.a[0]=0x93e0;am_word(r.d[0],4);am_word(r.d[1],8);
        return am_call(c,0xa29c,0x92ec);
    case 0x92ec:r.a[0]=0x9332;return am_call(c,0xa2b8,0x92f6);
    case 0x92f6:if(!am_write(c,fh2_at(r.a[5],0xfdfa),2,0))return false;r.pc=0x92fc;return true;
    case 0x92fc:return am_call(c,0xa370,0x9302);
    case 0x9302:r.pc=fh2_b(r.d[0])==0U?0x932a:0x9308;return true;                // TST.B D0; BEQ.W 932a.
    case 0x9308:
        // MOVE.B #0,-212(A5); MOVEA.L -20a(A5),A0; CMPA.W #0,A0 (32-bit compare with sign-extended 0); BEQ.W 931c.
        if(!am_write(c,fh2_at(r.a[5],0xfdee),1,0) || !am_read(c,fh2_at(r.a[5],0xfdf6),4,value))return false;r.a[0]=value;
        r.pc=value==0U?0x931c:0x931a;return true;
    // Menu callback JSR (A0) (LONG 107df6 != 0): D8 guard, never executed.
    case 0x931a:return am_error(c,"unsupported animation frame head menu callback");
    case 0x931c:if(!am_read(c,fh2_at(r.a[5],0xfdfa),2,value))return false;r.pc=fh2_w(value)==1U?0x928e:0x9326;return true;
    case 0x9326:r.pc=0x92a8;return true;                                           // BRA.W 92a8.
    // ---- 9332 pause menu renderer (style 3 -> 6b, then the e84c8 table renderer).
    case 0x9332:r.pc=fh2_b(r.d[1])!=3U?0x933e:0x933a;return true;
    case 0x933a:am_byte(r.d[1],0x6b);r.pc=0x933e;return true;
    case 0x933e:r.pc=0xe84c8;return true;                                          // JMP e84c8.l.
    default:return am_error(c,"unsupported animation frame head h2 PC");
    }
}
}
