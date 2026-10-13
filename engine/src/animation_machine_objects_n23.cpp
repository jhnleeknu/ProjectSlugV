#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONGs (live bus, current PVC bank): animation record of 4db42 (id ea) and the c3a7c record / table base (id ca).
const std::uint32_t ON23_BANK_EA=0x200098;
const std::uint32_t ON23_BANK_CA=0x200088;
std::uint32_t on23_b(std::uint32_t value) {return value&255U;}
std::uint32_t on23_w(std::uint32_t value) {return value&65535U;}
// Sign extension of a BYTE to a WORD (EXT.W).
std::uint32_t on23_ext_b(std::uint32_t value) {return (value&0x80U)?((value&255U)|0xff00U):(value&255U);}
// Arithmetic shift right of a WORD / BYTE (sign bit refilled explicitly).
std::uint32_t on23_asr_w(std::uint32_t value,unsigned int count) {
    std::uint32_t u=value&65535U;for(unsigned int i=0;i<count;++i)u=(u>>1)|(u&0x8000U);return u;
}
std::uint32_t on23_asr_b(std::uint32_t value,unsigned int count) {
    std::uint32_t u=value&255U;for(unsigned int i=0;i<count;++i)u=(u>>1)|(u&0x80U);return u;
}
bool on23_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on23_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BYTE bit of the memory operand at address (BTST.B #bit,<ea>): true when the bit is 1.
bool on23_bit(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// MOVE.B <src d16(A6)>,<dst d16(A6)>.
bool on23_copy_b(AnimationMachineContext& c,std::uint32_t from,std::uint32_t to) {
    std::uint32_t value=0;return on23_get(c,c.s.a[6],from,1,value) && on23_put(c,c.s.a[6],to,1,on23_b(value));
}
// Bcc on a C returned by a callee (or produced by 4d344): BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on23_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n23 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ORI.B #1,CCR / ANDI.B #fe,CCR; RTS.
bool on23_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {c.s.carry=carry;return am_return(c);}
// LEA 5cba(A5),A4 / LEA 5ce6(A5),A4 then continue at next_pc.
bool on23_slot(AnimationMachineContext& c,bool second,std::uint32_t next_pc) {
    c.s.a[4]=am_index(c.s.a[5],second?0x5ce6U:0x5cbaU);c.s.pc=next_pc;return true;
}
// 4d3ca / 4d3e2 tail: D2.W = WORD first(A0), D0.W -= D2.W, D1.W -= D2.W, D2.W = WORD second(A0), D0.W -= D2.W (borrow returned).
bool on23_box(AnimationMachineContext& c,std::uint32_t first,std::uint32_t second,bool& borrow) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!on23_get(c,r.a[0],first,2,value))return false;am_word(r.d[2],value);
    am_word(r.d[0],(r.d[0]-r.d[2])&65535U);am_word(r.d[1],(r.d[1]-r.d[2])&65535U);
    if(!on23_get(c,r.a[0],second,2,value))return false;am_word(r.d[2],value);
    borrow=on23_w(r.d[0])<on23_w(r.d[2]);am_word(r.d[0],(r.d[0]-r.d[2])&65535U);return true;
}
// 4d3ac / 4d3e2 head: D0.W = WORD d(A3) - WORD d(A6), D1.W = WORD e(A3) - WORD e(A6).
bool on23_delta(AnimationMachineContext& c,std::uint32_t d,std::uint32_t e) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    if(!on23_get(c,r.a[3],d,2,value) || !on23_get(c,r.a[6],d,2,other))return false;am_word(r.d[0],(value-other)&65535U);
    if(!on23_get(c,r.a[3],e,2,value) || !on23_get(c,r.a[6],e,2,other))return false;am_word(r.d[1],(value-other)&65535U);
    return true;
}
}
// Objects F4 N23 (198 block starts): the 41fe6 child callback 420be (installed by N22 420b6), the 28ae child 4db42 (created by
// 4da4a / 4da50, installed 4db8e, JSR (A1) code pointer), the player tests 4d2d4 / 4d36e (JSR (A1) = 1bf02), 484b4 4d508 4d50e 4d766
// 4d900 4d958, and the stage event callback c3a7c (c3a9c, installed c3b4a). Boundaries without an executor: c3ce 4c2fa e9112.
// 4d38a and 4dbb0 JSR (A1) are live targets. 4219c recomputes the Z of the c3ce TST.B (A0,D0.W) and 42238 the N of 42228 CMPI.W
// #8000,D1 (unique predecessors). The 14 BCC/BCS/SCS consumers read a known C; ORI / ANDI CCR set / clear it, 4d344 (CMP.W D0,D1)
// and 4d77a (ADD.B D1,D1) compute it. 4236e ASR.B / ADDX.B keeps X inside the block. No port, no bank change.
bool animation_objects_n23_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool bit=false;
    switch(r.pc) {
    // ---- 420be (installed by N22 420b6): JSR 288c.l; BCC.W 42410; BTST.B #7,61(A0); BNE.W 42410.
    case 0x420be:return am_call(c,0x288c,0x420c4);
    case 0x420c4:return on23_carry(c,0x42410,0x420c8);                  // BCC.W 42410 (C returned by 288c).
    case 0x420c8:case 0x4dbc0:
        if(!on23_bit(c,am_index(r.a[0],0x61),7,bit))return false;
        r.pc=bit?(r.pc==0x420c8?0x42410U:0x4dbd6U):(r.pc==0x420c8?0x420d2U:0x4dbcaU);return true;
    // MOVEA.L 76(A6),A0; MOVE.W (A0),D0; CMPI.W #8000,D0; BEQ.W 42410.
    case 0x420d2:
        if(!on23_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);
        r.pc=on23_w(r.d[0])==0x8000U?0x42410:0x420e0;return true;
    case 0x420e0:r.pc=on23_w(r.d[0])!=0x8080U?0x420ea:0x420e8;return true; // CMPI.W #8080,D0; BNE.W 420ea.
    case 0x420e8:case 0x42408:case 0x4dbd4:case 0xc3c1a:return am_return(c); // RTS.
    // MOVEA.L 76(A6),A0; MOVE.B 3(A0),D0; BMI.W 42108.
    case 0x420ea:
        if(!on23_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;if(!on23_get(c,r.a[0],3,1,value))return false;am_byte(r.d[0],value);
        r.pc=(value&0x80U)!=0U?0x42108:0x420f6;return true;
    // MOVE.B #ff,3(A0); LSL.B #4,D0; LSL.W #8,D0; MOVE.W D0,86(A6); MOVE.W D0,8c(A6).
    case 0x420f6:
        if(!on23_put(c,r.a[0],3,1,0xff))return false;am_byte(r.d[0],(r.d[0]<<4)&255U);am_word(r.d[0],(r.d[0]<<8)&65535U);
        if(!on23_put(c,r.a[6],0x86,2,on23_w(r.d[0])) || !on23_put(c,r.a[6],0x8c,2,on23_w(r.d[0])))return false;r.pc=0x42108;return true;
    // LSR.W 8e(A6); JSR 4d900.l.
    case 0x42108:
        if(!on23_get(c,r.a[6],0x8e,2,value) || !on23_put(c,r.a[6],0x8e,2,on23_w(value)>>1))return false;return am_call(c,0x4d900,0x42112);
    case 0x42112:r.pc=(r.d[0]&0x80U)!=0U?0x42118:0x42134;return true;   // TST.B D0; BPL.W 42134.
    // MOVE.B #0,81(A6); MOVE.B #0,7f(A6); MOVE.B #0,80(A6); MOVE.B #0,93(A6); BRA.W 42354.
    case 0x42118:
        if(!on23_put(c,r.a[6],0x81,1,0) || !on23_put(c,r.a[6],0x7f,1,0) || !on23_put(c,r.a[6],0x80,1,0) || !on23_put(c,r.a[6],0x93,1,0))
            return false;
        r.pc=0x42354;return true;
    // ANDI.W #ff,D0 (twice); MOVE.W D0,90(A6); MOVEQ #0,D1; BSET.B D0,D1 (register: bit D0 mod 32); MOVE.B D1,60(A6); MOVEQ #0,D1;
    // MOVE.B 86(A6),D1; JSR 4d958.l.
    case 0x42134:
        am_word(r.d[0],r.d[0]&0xffU);if(!on23_put(c,r.a[6],0x90,2,on23_w(r.d[0])))return false;
        r.d[1]=1U<<(r.d[0]&31U);if(!on23_put(c,r.a[6],0x60,1,on23_b(r.d[1])))return false;
        r.d[1]=0;if(!on23_get(c,r.a[6],0x86,1,value))return false;am_byte(r.d[1],value);return am_call(c,0x4d958,0x42154);
    case 0x42154:return am_call(c,0x49be0,0x4215a);                     // JSR 49be0.l.
    // MOVE.W (A0),D0 / MOVE.W 2(A0),D0; BTST.B #4,D0 (register: LONG bit 4); BEQ.W.
    case 0x4215a:case 0x42182:
        if(!on23_get(c,r.a[0],r.pc==0x4215a?0U:2U,2,value))return false;am_word(r.d[0],value);
        r.pc=(r.d[0]&0x10U)==0U?(r.pc==0x4215a?0x42182U:0x421bcU):(r.pc==0x4215a?0x42164U:0x4218eU);return true;
    case 0x42164:if(!on23_get(c,r.a[6],0x80,1,value))return false;r.pc=on23_b(value)!=0U?0x42172:0x4216c;return true; // TST.B 80(A6).
    case 0x4216c:if(!on23_copy_b(c,0x7c,0x7f))return false;r.pc=0x42172;return true; // MOVE.B 7c(A6),7f(A6).
    // MOVE.B 7d(A6),80(A6); MOVE.B #8,93(A6); BRA.W 421bc.
    case 0x42172:if(!on23_copy_b(c,0x7d,0x80) || !on23_put(c,r.a[6],0x93,1,8))return false;r.pc=0x421bc;return true;
    // MOVEM.W D0,-(A7); MOVE.W 90(A6),D0; JSR c3ce.l (boundary).
    case 0x4218e:
        if(!am_push(c,2,on23_w(r.d[0])) || !on23_get(c,r.a[6],0x90,2,value))return false;am_word(r.d[0],value);return am_call(c,0xc3ce,0x4219c);
    // MOVEM.W (A7)+,D0; BEQ.W 421bc. Z is recomputed from the unique predecessor c3ce (TST.B (A0,D0.W); RTS): the same BYTE at the
    // entry A0 / D0.W (main decision 2), then D0 = sext(popped WORD).
    case 0x4219c:
        if(!am_read(c,am_index(r.a[0],r.d[0]),1,other) || !am_pop(c,2,value))return false;r.d[0]=am_extend_word(value);
        r.pc=on23_b(other)==0U?0x421bc:0x421a4;return true;
    // SUBQ.B #1,93(A6); BCC.W 421bc (borrow only from 0).
    case 0x421a4:
        if(!on23_get(c,r.a[6],0x93,1,value) || !on23_put(c,r.a[6],0x93,1,(value+0xffU)&255U))return false;
        r.pc=on23_b(value)!=0U?0x421bc:0x421ac;return true;
    // MOVE.B #0,93(A6); MOVE.B 7d(A6),80(A6); BRA.W 421f4.
    case 0x421ac:if(!on23_put(c,r.a[6],0x93,1,0) || !on23_copy_b(c,0x7d,0x80))return false;r.pc=0x421f4;return true;
    // MOVE.W 8c(A6),D2; ANDI.W #f,D0; MOVEQ #0,D1; MOVE.B 7e(A6),D1; LEA 41dfc(PC),A1; MOVEA.L (A1,D1.W),A1; MOVE.B (A1,D0.W),D0;
    // ADD.W D0,D0 (twice); LEA 41e76(PC),A1; MOVEQ #0,D1; MOVE.B 7a(A6),D1; ADD.W D1,D1 (twice); MOVEA.L (A1,D1.W),A1;
    // MOVE.L (A1,D0.W),D1; BPL.W 421fc.
    case 0x421bc:
        if(!on23_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[2],value);am_word(r.d[0],r.d[0]&0xfU);
        r.d[1]=0;if(!on23_get(c,r.a[6],0x7e,1,value))return false;am_byte(r.d[1],value);r.a[1]=0x41dfc;
        if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;
        if(!am_read(c,am_index(r.a[1],r.d[0]),1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],(r.d[0]*4U)&65535U);
        r.a[1]=0x41e76;r.d[1]=0;if(!on23_get(c,r.a[6],0x7a,1,value))return false;am_byte(r.d[1],value);am_word(r.d[1],(r.d[1]*4U)&65535U);
        if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;
        if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.d[1]=value;
        r.pc=(value&0x80000000U)!=0U?0x421f4:0x421fc;return true;
    // MOVE.W 86(A6),D1; MOVE.W D1,8c(A6).
    case 0x421f4:
        if(!on23_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[1],value);if(!on23_put(c,r.a[6],0x8c,2,on23_w(r.d[1])))return false;
        r.pc=0x421fc;return true;
    // MOVE.W 8c(A6),D2; MOVE.W D1,8c(A6); CMP.W D2,D1; BEQ.W 42216.
    case 0x421fc:
        if(!on23_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[2],value);if(!on23_put(c,r.a[6],0x8c,2,on23_w(r.d[1])))return false;
        r.pc=on23_w(r.d[1])==on23_w(r.d[2])?0x42216:0x4220a;return true;
    // MOVE.W #800,88(A6); MOVE.W #0,8a(A6).
    case 0x4220a:if(!on23_put(c,r.a[6],0x88,2,0x800) || !on23_put(c,r.a[6],0x8a,2,0))return false;r.pc=0x42216;return true;
    // MOVE.W 88(A6),D7; ADD.W 8a(A6),D7; MOVE.W 86(A6),D2; SUB.W D2,D1; BEQ.W 42272.
    case 0x42216:
        if(!on23_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[7],value);
        if(!on23_get(c,r.a[6],0x8a,2,value))return false;am_word(r.d[7],(r.d[7]+value)&65535U);
        if(!on23_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[2],value);am_word(r.d[1],(r.d[1]-r.d[2])&65535U);
        r.pc=on23_w(r.d[1])==0U?0x42272:0x42228;return true;
    case 0x42228:r.pc=on23_w(r.d[1])!=0x8000U?0x42238:0x42230;return true; // CMPI.W #8000,D1; BNE.W 42238.
    // NOT.B 82(A6); BRA.W 4223c.
    case 0x42230:if(!on23_get(c,r.a[6],0x82,1,value) || !on23_put(c,r.a[6],0x82,1,(~value)&255U))return false;r.pc=0x4223c;return true;
    // SPL.B 82(A6): N recomputed from the unique predecessor 42228 (CMPI.W #8000,D1, D1 unchanged): N = bit 15 of D1.W - 8000.
    case 0x42238:
        if(!on23_put(c,r.a[6],0x82,1,(((r.d[1]-0x8000U)&0x8000U)==0U)?0xffU:0U))return false;r.pc=0x4223c;return true;
    case 0x4223c:if(!on23_get(c,r.a[6],0x82,1,value))return false;r.pc=on23_b(value)==0U?0x42246:0x42244;return true; // TST.B 82(A6).
    case 0x42244:am_word(r.d[7],(0U-r.d[7])&65535U);r.pc=0x42246;return true; // NEG.W D7.
    // ADD.W D7,D2; SUB.W D7,D1; EOR.W D1,D7; BPL.W 42252.
    case 0x42246:
        am_word(r.d[2],(r.d[2]+r.d[7])&65535U);am_word(r.d[1],(r.d[1]-r.d[7])&65535U);am_word(r.d[7],(r.d[7]^r.d[1])&65535U);
        r.pc=(r.d[7]&0x8000U)==0U?0x42252:0x42250;return true;
    case 0x42250:am_word(r.d[2],(r.d[2]+r.d[1])&65535U);r.pc=0x42252;return true; // ADD.W D1,D2.
    // MOVE.W D2,86(A6); MOVE.W #fa00,D7; SUB.W 88(A6),D7; ASR.W #2,D7; ADD.W D7,88(A6); MOVE.W #3000,D7; SUB.W 8a(A6),D7;
    // ASR.W #4,D7; ADD.W D7,8a(A6).
    case 0x42252:
        if(!on23_put(c,r.a[6],0x86,2,on23_w(r.d[2])) || !on23_get(c,r.a[6],0x88,2,value))return false;
        am_word(r.d[7],(0xfa00U-value)&65535U);am_word(r.d[7],on23_asr_w(r.d[7],2));
        if(!on23_get(c,r.a[6],0x88,2,value) || !on23_put(c,r.a[6],0x88,2,(value+r.d[7])&65535U) || !on23_get(c,r.a[6],0x8a,2,value))return false;
        am_word(r.d[7],(0x3000U-value)&65535U);am_word(r.d[7],on23_asr_w(r.d[7],4));
        if(!on23_get(c,r.a[6],0x8a,2,value) || !on23_put(c,r.a[6],0x8a,2,(value+r.d[7])&65535U))return false;r.pc=0x42272;return true;
    // MOVE.B 80(A6),D0; BNE.W 42284.
    case 0x42272:if(!on23_get(c,r.a[6],0x80,1,value))return false;am_byte(r.d[0],value);r.pc=on23_b(value)!=0U?0x42284:0x4227a;return true;
    case 0x4227a:if(!on23_put(c,r.a[6],0x81,1,0))return false;r.pc=0x42354;return true; // MOVE.B #0,81(A6); BRA.W 42354.
    // SUBQ.B #1,7f(A6); BCC.W 42354.
    case 0x42284:
        if(!on23_get(c,r.a[6],0x7f,1,value) || !on23_put(c,r.a[6],0x7f,1,(value+0xffU)&255U))return false;
        r.pc=on23_b(value)!=0U?0x42354:0x4228c;return true;
    // SUBQ.B #1,D0; MOVE.B D0,80(A6); MOVE.B #ff,81(A6); MOVE.B 7b(A6),D0; ADD.B D0,7f(A6); MOVEQ #0,D0; MOVE.B 7a(A6),D0;
    // ADD.W D0,D0 (twice); LEA 41f1e(PC),A0; MOVEA.L (A0,D0.W),A0; MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0x4228c:
        am_byte(r.d[0],(r.d[0]+0xffU)&255U);if(!on23_put(c,r.a[6],0x80,1,on23_b(r.d[0])) || !on23_put(c,r.a[6],0x81,1,0xff))return false;
        if(!on23_get(c,r.a[6],0x7b,1,value))return false;am_byte(r.d[0],value);
        if(!on23_get(c,r.a[6],0x7f,1,value) || !on23_put(c,r.a[6],0x7f,1,(value+r.d[0])&255U))return false;
        r.d[0]=0;if(!on23_get(c,r.a[6],0x7a,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],(r.d[0]*4U)&65535U);
        r.a[0]=0x41f1e;if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;
        am_word(r.d[0],0xa);r.a[1]=0x100bf4;return am_call(c,0x2986,0x422c2);
    // MOVE.B 60(A6),60(A0); MOVEQ #0,D2; MOVE.B 86(A6),D1; CMP.B 84(A6),D1; BNE.W 422ee.
    case 0x422c2:
        if(!on23_get(c,r.a[6],0x60,1,value) || !on23_put(c,r.a[0],0x60,1,on23_b(value)))return false;r.d[2]=0;
        if(!on23_get(c,r.a[6],0x86,1,value))return false;am_byte(r.d[1],value);if(!on23_get(c,r.a[6],0x84,1,value))return false;
        r.pc=on23_b(r.d[1])!=on23_b(value)?0x422ee:0x422d6;return true;
    // MOVE.B 83(A6),D2; ADDQ.B #1,D2; CMPI.B #3,D2; BCS.W 422e6.
    case 0x422d6:
        if(!on23_get(c,r.a[6],0x83,1,value))return false;am_byte(r.d[2],(value+1U)&255U);r.pc=on23_b(r.d[2])<3U?0x422e6:0x422e4;return true;
    case 0x422e4:r.d[2]=0;r.pc=0x422e6;return true;                     // MOVEQ #0,D2.
    // MOVE.B D2,83(A6); SUBQ.B #1,D2; ADD.W D2,D2.
    case 0x422e6:
        if(!on23_put(c,r.a[6],0x83,1,on23_b(r.d[2])))return false;am_byte(r.d[2],(r.d[2]+0xffU)&255U);am_word(r.d[2],(r.d[2]*2U)&65535U);
        r.pc=0x422ee;return true;
    // MOVE.B D1,84(A6); ADD.B D2,D1; MOVE.B D1,76(A0); SUB.B D2,D1; MOVE.L #1c0000,D0; MOVE.L A0,-(A7); JSR 443d2.l.
    case 0x422ee:
        if(!on23_put(c,r.a[6],0x84,1,on23_b(r.d[1])))return false;am_byte(r.d[1],(r.d[1]+r.d[2])&255U);
        if(!on23_put(c,r.a[0],0x76,1,on23_b(r.d[1])))return false;am_byte(r.d[1],(r.d[1]-r.d[2])&255U);r.d[0]=0x1c0000;
        if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x443d2,0x42308);
    // MOVEA.L (A7)+,A0; SWAP D0; SWAP D1; MOVE.W D0,D2; MOVE.W D1,D3; MOVEQ #ff,D0; JSR 4c2fa.l (boundary).
    case 0x42308:
        if(!am_pop(c,4,value))return false;r.a[0]=value;am_swap(r.d[0]);am_swap(r.d[1]);am_word(r.d[2],r.d[0]);am_word(r.d[3],r.d[1]);
        r.d[0]=0xffffffffU;return am_call(c,0x4c2fa,0x4231a);
    case 0x4231a:r.pc=on23_b(r.d[6])==0U?0x42354:0x42320;return true;   // TST.B D6; BEQ.W 42354.
    case 0x42320:if(!on23_get(c,r.a[6],0x8e,2,value))return false;r.pc=on23_w(value)!=0U?0x42354:0x42328;return true; // TST.W 8e(A6).
    // MOVE.W #ff,8e(A6); MOVEM.L D0-D1/A1,-(A7) (A1, D1, D0); MOVEA.L #42600,A0; MOVE.W #1e,D0; JSR 28ae.l.
    case 0x42328:
        if(!on23_put(c,r.a[6],0x8e,2,0xff) || !am_push(c,4,r.a[1]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;
        r.a[0]=0x42600;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0x42342);
    // MOVEM.L (A7)+,D0-D1/A1; LEA 2e(A0),A0; SWAP D0; SWAP D1; JSR 43e08.l.
    case 0x42342:
        if(!am_pop(c,4,value))return false;r.d[0]=value;if(!am_pop(c,4,value))return false;r.d[1]=value;
        if(!am_pop(c,4,value))return false;r.a[1]=value;r.a[0]=am_index(r.a[0],0x2e);am_swap(r.d[0]);am_swap(r.d[1]);
        return am_call(c,0x43e08,0x42354);
    // MOVEQ #0,D1; MOVE.B 86(A6),D0; BTST.B #0,15(A6); BEQ.W 4236e.
    case 0x42354:
        r.d[1]=0;if(!on23_get(c,r.a[6],0x86,1,value))return false;am_byte(r.d[0],value);
        if(!on23_bit(c,am_index(r.a[6],0x15),0,bit))return false;r.pc=bit?0x42364:0x4236e;return true;
    // SUBI.B #40,D0; NEG.B D0; ADDI.B #40,D0.
    case 0x42364:
        am_byte(r.d[0],(r.d[0]-0x40U)&255U);am_byte(r.d[0],(0U-r.d[0])&255U);am_byte(r.d[0],(r.d[0]+0x40U)&255U);r.pc=0x4236e;return true;
    // ASR.B #3,D0 (X = the last bit shifted out = bit 2); ADDX.B D1,D0; ANDI.B #1f,D0; MOVE.B D0,92(A6); MOVEA.L c(A6),A0;
    // MOVE.W 68(A0),68(A6); MOVE.W 94(A6),1e(A6); BNE.W 42394.
    case 0x4236e: {
        const std::uint32_t x=(r.d[0]>>2)&1U;const std::uint32_t u=on23_asr_b(r.d[0],3);
        am_byte(r.d[0],(u+on23_b(r.d[1])+x)&255U);am_byte(r.d[0],r.d[0]&0x1fU);
        if(!on23_put(c,r.a[6],0x92,1,on23_b(r.d[0])) || !on23_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!on23_get(c,r.a[0],0x68,2,value) || !on23_put(c,r.a[6],0x68,2,on23_w(value)))return false;
        if(!on23_get(c,r.a[6],0x94,2,value) || !on23_put(c,r.a[6],0x1e,2,on23_w(value)))return false;
        r.pc=on23_w(value)!=0U?0x42394:0x4238e;return true;
    }
    case 0x4238e:if(!on23_get(c,r.a[0],0x1e,2,value) || !on23_put(c,r.a[6],0x1e,2,on23_w(value)))return false;r.pc=0x42394;return true;
    // MOVE.L 96(A6),D0; BEQ.W 423b2.
    case 0x42394:if(!on23_get(c,r.a[6],0x96,4,value))return false;r.d[0]=value;r.pc=value==0U?0x423b2:0x4239c;return true;
    // MOVEA.L D0,A0; MOVE.B 86(A6),D0; ADDQ.B #8,D0; LSR.B #4,D0; ANDI.W #f,D0; MOVE.B (A0,D0.W),D0; ADD.W D0,1e(A6).
    case 0x4239c:
        r.a[0]=r.d[0];if(!on23_get(c,r.a[6],0x86,1,value))return false;am_byte(r.d[0],value);am_byte(r.d[0],(r.d[0]+8U)&255U);
        am_byte(r.d[0],on23_b(r.d[0])>>4);am_word(r.d[0],r.d[0]&0xfU);if(!am_read(c,am_index(r.a[0],r.d[0]),1,value))return false;
        am_byte(r.d[0],value);if(!on23_get(c,r.a[6],0x1e,2,value) || !on23_put(c,r.a[6],0x1e,2,(value+r.d[0])&65535U))return false;
        r.pc=0x423b2;return true;
    // LEA 2e(A0),A1; MOVEA.L 76(A6),A0; MOVE.B (A0)+,D0; MOVE.B (A0),D1; EXT.W D0; EXT.W D1; MOVE.W D0,2e(A6); MOVE.W D1,32(A6);
    // JSR 43e34.l.
    case 0x423b2:
        r.a[1]=am_index(r.a[0],0x2e);if(!on23_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[0],value);r.a[0]+=1U;if(!am_read(c,r.a[0],1,value))return false;
        am_byte(r.d[1],value);am_word(r.d[0],on23_ext_b(r.d[0]));am_word(r.d[1],on23_ext_b(r.d[1]));
        if(!on23_put(c,r.a[6],0x2e,2,on23_w(r.d[0])) || !on23_put(c,r.a[6],0x32,2,on23_w(r.d[1])))return false;
        return am_call(c,0x43e34,0x423d0);
    case 0x423d0:return am_call(c,0x4a46c,0x423d6);                     // JSR 4a46c.l.
    case 0x423d6:return on23_carry(c,0x423e0,0x423da);                  // BCC.W 423e0 (C returned by 4a46c).
    case 0x423da:if(!on23_copy_b(c,0x1a,0x14))return false;r.pc=0x423e0;return true; // MOVE.B 1a(A6),14(A6).
    case 0x423e0:if(!on23_put(c,r.a[6],0x17,1,0xff))return false;return am_call(c,0x49fc6,0x423ec); // MOVE.B #ff,17(A6); JSR 49fc6.l.
    // MOVE.B 19(A6),14(A6); MOVEA.L 76(A6),A0; TST.B 2(A0); BEQ.W 42408.
    case 0x423ec:
        if(!on23_copy_b(c,0x19,0x14) || !on23_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        if(!on23_get(c,r.a[0],2,1,value))return false;r.pc=on23_b(value)==0U?0x42408:0x423fe;return true;
    // CLR.B 2(A0); MOVE.B 1a(A6),14(A6).
    case 0x423fe:if(!on23_put(c,r.a[0],2,1,0) || !on23_copy_b(c,0x1a,0x14))return false;r.pc=0x42408;return true;
    case 0x42410:return am_call(c,0x4d900,0x42416);                     // JSR 4d900.l.
    case 0x42416:r.pc=(r.d[0]&0x80U)!=0U?0x42424:0x4241c;return true;   // TST.B D0; BMI.W 42424.
    case 0x4241c:r.d[1]=0xffffffffU;return am_call(c,0x4d958,0x42424); // MOVEQ #ff,D1; JSR 4d958.l.
    // MOVEQ #0,D0; MOVE.B 7a(A6),D0; ADD.W D0,D0 (twice); MOVEA.L 42460(PC,D0.W),A0; MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0x42424:
        r.d[0]=0;if(!on23_get(c,r.a[6],0x7a,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],(r.d[0]*4U)&65535U);
        if(!am_read(c,am_index(0x42460,r.d[0]),4,value))return false;r.a[0]=value;am_word(r.d[0],0xa);r.a[1]=0x100bf4;
        return am_call(c,0x2986,0x42442);
    // MOVE.B 7a(A6),7a(A0); MOVEQ #0,D0; MOVEQ #0,D1; JSR 4970a.l.
    case 0x42442:
        if(!on23_get(c,r.a[6],0x7a,1,value) || !on23_put(c,r.a[0],0x7a,1,on23_b(value)))return false;r.d[0]=0;r.d[1]=0;
        return am_call(c,0x4970a,0x42452);
    // ADDQ.W #1,68(A0); ADDQ.W #1,1e(A0); JMP 2a00.l.
    case 0x42452:
        if(!on23_get(c,r.a[0],0x68,2,value) || !on23_put(c,r.a[0],0x68,2,(value+1U)&65535U))return false;
        if(!on23_get(c,r.a[0],0x1e,2,value) || !on23_put(c,r.a[0],0x1e,2,(value+1U)&65535U))return false;r.pc=0x2a00;return true;
    // ---- 484b4: BTST.B #3,5683(A5); BEQ.W 484c4 / ORI.B #1,CCR; RTS / ANDI.B #fe,CCR; RTS.
    case 0x484b4:if(!on23_bit(c,am_index(r.a[5],0x5683),3,bit))return false;r.pc=bit?0x484be:0x484c4;return true;
    case 0x484be:case 0x4d3a6:case 0x4d40c:return on23_return_carry(c,AnimationCarrySet);
    case 0x484c4:case 0x4d412:return on23_return_carry(c,AnimationCarryClear);
    // ---- 4d2d4: LEA 1bf02.l,A1; MOVEQ #0,D0; BSR.W 4d36e.
    case 0x4d2d4:r.a[1]=0x1bf02;r.d[0]=0;return am_call(c,0x4d36e,0x4d2e0);
    // SCS.B D7; MOVE.W D7,-(A7); LEA 1bf02.l,A1; MOVEQ #1,D0; BSR.W 4d36e (C consumed, then Unknown).
    case 0x4d2e0:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n23 caller requires known carry");
        am_byte(r.d[7],r.carry==AnimationCarrySet?0xffU:0U);r.carry=AnimationCarryUnknown;if(!am_push(c,2,on23_w(r.d[7])))return false;
        r.a[1]=0x1bf02;r.d[0]=1;return am_call(c,0x4d36e,0x4d2f0);
    // SCS.B D6; MOVE.W (A7)+,D7; EXT.W D7; MOVE.B D6,D7; TST.W D7; BNE.W 4d308.
    case 0x4d2f0:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n23 caller requires known carry");
        am_byte(r.d[6],r.carry==AnimationCarrySet?0xffU:0U);r.carry=AnimationCarryUnknown;if(!am_pop(c,2,value))return false;
        am_word(r.d[7],value);am_word(r.d[7],on23_ext_b(r.d[7]));am_byte(r.d[7],r.d[6]);r.pc=on23_w(r.d[7])!=0U?0x4d308:0x4d2fe;return true;
    case 0x4d2fe:r.d[0]=0xffffffffU;r.d[1]=0;return on23_return_carry(c,AnimationCarryClear); // MOVEQ #ff,D0; MOVEQ #0,D1; ANDI; RTS.
    case 0x4d308:r.pc=on23_w(r.d[7])!=0xffU?0x4d318:0x4d310;return true;   // CMPI.W #ff,D7; BNE.W 4d318.
    case 0x4d310:case 0x4d35e:r.d[0]=1;return on23_return_carry(c,AnimationCarrySet); // MOVEQ #1,D0; ORI.B #1,CCR; RTS.
    case 0x4d318:r.pc=on23_w(r.d[7])!=0xff00U?0x4d328:0x4d320;return true; // CMPI.W #ff00,D7; BNE.W 4d328.
    case 0x4d320:case 0x4d366:r.d[0]=0;return on23_return_carry(c,AnimationCarrySet); // MOVEQ #0,D0; ORI.B #1,CCR; RTS.
    // MOVE.W -731a(A5),D0 / -722a(A5),D1; SUB.W 2e(A6),Dn; BPL.W.
    case 0x4d328:case 0x4d336: {
        const unsigned int n=r.pc==0x4d328?0U:1U;
        if(!on23_get(c,r.a[5],n==0U?0x8ce6U:0x8dd6U,2,value) || !on23_get(c,r.a[6],0x2e,2,other))return false;
        am_word(r.d[n],(value-other)&65535U);
        r.pc=(r.d[n]&0x8000U)==0U?(n==0U?0x4d336U:0x4d344U):(n==0U?0x4d334U:0x4d342U);return true;
    }
    case 0x4d334:am_word(r.d[0],(0U-r.d[0])&65535U);r.pc=0x4d336;return true; // NEG.W D0.
    case 0x4d342:am_word(r.d[1],(0U-r.d[1])&65535U);r.pc=0x4d344;return true; // NEG.W D1.
    // CMP.W D0,D1; BNE.W 4d35a: computed C = D1.W < D0.W (unsigned borrow), consumed by 4d35a (main decision 4).
    case 0x4d344:
        r.carry=on23_w(r.d[1])<on23_w(r.d[0])?AnimationCarrySet:AnimationCarryClear;
        r.pc=on23_w(r.d[1])!=on23_w(r.d[0])?0x4d35a:0x4d34a;return true;
    case 0x4d34a:return am_call(c,0x49a58,0x4d350);                     // JSR 49a58.l.
    case 0x4d350:am_word(r.d[0],r.d[0]&1U);return on23_return_carry(c,AnimationCarrySet); // ANDI.W #1,D0; ORI; RTS.
    case 0x4d35a:return on23_carry(c,0x4d366,0x4d35e);                  // BCC.W 4d366 (C of 4d344).
    // ---- 4d36e: ANDI.W #1,D0; BNE.W 4d382 / LEA -7348(A5),A3; LEA 5cba(A5),A4 / LEA -7258(A5),A3; LEA 5ce6(A5),A4; JSR (A1).
    case 0x4d36e:am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&1U)!=0U?0x4d382:0x4d376;return true;
    case 0x4d376:r.a[3]=am_index(r.a[5],0x8cb8);return on23_slot(c,false,0x4d38a);
    case 0x4d382:r.a[3]=am_index(r.a[5],0x8da8);return on23_slot(c,true,0x4d38a);
    case 0x4d38a:return am_call(c,r.a[1],0x4d38c);                     // JSR (A1) (live target).
    case 0x4d38c:r.pc=(r.d[0]&0x80U)!=0U?0x4d412:0x4d392;return true;   // TST.B D0; BMI.W 4d412.
    case 0x4d392:if(!am_read(c,r.a[4],2,value))return false;r.pc=on23_w(value)!=0U?0x4d412:0x4d398;return true; // TST.W (A4).
    case 0x4d398:if(!on23_get(c,r.a[4],0x22,1,value))return false;r.pc=on23_b(value)!=0U?0x4d412:0x4d3a0;return true; // TST.B 22(A4).
    case 0x4d3a0:r.pc=on23_b(r.d[0])==0U?0x4d3ac:0x4d3a6;return true;   // TST.B D0; BEQ.W 4d3ac.
    // MOVE.W 42(A3),D0; SUB.W 42(A6),D0; MOVE.W 4a(A3),D1; SUB.W 4a(A6),D1; BTST.B #0,15(A6); BEQ.W 4d3ca.
    case 0x4d3ac:
        if(!on23_delta(c,0x42,0x4a) || !on23_bit(c,am_index(r.a[6],0x15),0,bit))return false;r.pc=bit?0x4d3c6:0x4d3ca;return true;
    case 0x4d3c6:am_word(r.d[0],(0U-r.d[0])&65535U);am_word(r.d[1],(0U-r.d[1])&65535U);r.pc=0x4d3ca;return true; // NEG.W D0; NEG.W D1.
    // MOVE.W (A0),D2; SUB.W D2,D0; SUB.W D2,D1; MOVE.W 4(A0),D2; SUB.W D2,D0; BCS.W 4d3e2.
    case 0x4d3ca:if(!on23_box(c,0,4,bit))return false;r.pc=bit?0x4d3e2:0x4d3da;return true;
    // SUB.W D2,D1; EOR.W D1,D0; BPL.W 4d412.
    case 0x4d3da:case 0x4d404:
        am_word(r.d[1],(r.d[1]-r.d[2])&65535U);am_word(r.d[0],(r.d[0]^r.d[1])&65535U);
        r.pc=(r.d[0]&0x8000U)==0U?0x4d412:(r.pc==0x4d3da?0x4d3e2U:0x4d40cU);return true;
    // MOVE.W 46(A3),D0; SUB.W 46(A6),D0; MOVE.W 4e(A3),D1; SUB.W 4e(A6),D1; MOVE.W 2(A0),D2; SUB.W D2,D0; SUB.W D2,D1;
    // MOVE.W 6(A0),D2; SUB.W D2,D0; BCS.W 4d40c.
    case 0x4d3e2:if(!on23_delta(c,0x46,0x4e) || !on23_box(c,2,6,bit))return false;r.pc=bit?0x4d40c:0x4d404;return true;
    // ---- 4d508: MOVEQ #ff,D5; MOVE.B #0,D6 / 4d50e: TST.B D0; BNE.W 4d51c; LEA 5cba(A5),A4 / 5ce6(A5),A4.
    case 0x4d508:r.d[5]=0xffffffffU;am_byte(r.d[6],0);r.pc=0x4d50e;return true;
    case 0x4d50e:r.pc=on23_b(r.d[0])!=0U?0x4d51c:0x4d514;return true;
    case 0x4d514:case 0x4d51c:return on23_slot(c,r.pc==0x4d51c,0x4d520);
    // MOVE.W 54(A6),1c(A4); MOVE.W #0,1a(A4); MOVE.B #0,2b(A4); MOVE.W #0,6(A4); CMPI.B #64,D2; BCS.W 4d544.
    case 0x4d520:
        if(!on23_get(c,r.a[6],0x54,2,value) || !on23_put(c,r.a[4],0x1c,2,on23_w(value)) || !on23_put(c,r.a[4],0x1a,2,0) ||
            !on23_put(c,r.a[4],0x2b,1,0) || !on23_put(c,r.a[4],6,2,0))return false;
        r.pc=on23_b(r.d[2])<0x64U?0x4d544:0x4d540;return true;
    case 0x4d540:am_byte(r.d[2],0x63);r.pc=0x4d544;return true;          // MOVE.B #63,D2.
    // MOVE.B D1,27(A4); MOVE.B D2,25(A4); MOVE.B D3,26(A4); MOVE.W D4,1c(A4); MOVE.W D5,20(A4); MOVE.B D6,2a(A4); RTS.
    case 0x4d544:
        if(!on23_put(c,r.a[4],0x27,1,on23_b(r.d[1])) || !on23_put(c,r.a[4],0x25,1,on23_b(r.d[2])) || !on23_put(c,r.a[4],0x26,1,on23_b(r.d[3])) ||
            !on23_put(c,r.a[4],0x1c,2,on23_w(r.d[4])) || !on23_put(c,r.a[4],0x20,2,on23_w(r.d[5])) || !on23_put(c,r.a[4],0x2a,1,on23_b(r.d[6])))
            return false;
        return am_return(c);
    // ---- 4d766: JSR 1bfb4.l; BTST.B #7,10f000.l; BEQ.W 4d77a; ST.B D1; ADD.B D1,D1; RTS (C = D1.B bit 7).
    case 0x4d766:return am_call(c,0x1bfb4,0x4d76c);
    case 0x4d76c:if(!on23_bit(c,0x10f000,7,bit))return false;r.pc=bit?0x4d778:0x4d77a;return true;
    case 0x4d778:am_byte(r.d[1],0xff);r.pc=0x4d77a;return true;
    case 0x4d77a:
        r.carry=(r.d[1]&0x80U)!=0U?AnimationCarrySet:AnimationCarryClear;am_byte(r.d[1],(r.d[1]<<1)&255U);return am_return(c);
    // ---- 4d900: MOVE.W e(A6),D0; LEA -7348(A5),A0; JSR 289e.l; BCC.W 4d92a; CMP.W 5cba(A5),D0; BNE.W 4d92a; TST.B 5cdc(A5); BEQ.
    case 0x4d900:if(!on23_get(c,r.a[6],0xe,2,value))return false;am_word(r.d[0],value);r.a[0]=am_index(r.a[5],0x8cb8);return am_call(c,0x289e,0x4d90e);
    case 0x4d90e:return on23_carry(c,0x4d92a,0x4d912);                  // BCC.W 4d92a (C returned by 289e).
    case 0x4d912:case 0x4d938:
        if(!on23_get(c,r.a[5],r.pc==0x4d912?0x5cbaU:0x5ce6U,2,value))return false;
        r.pc=on23_w(r.d[0])!=on23_w(value)?(r.pc==0x4d912?0x4d92aU:0x4d950U):(r.pc==0x4d912?0x4d91aU:0x4d940U);return true;
    case 0x4d91a:case 0x4d940:
        if(!on23_get(c,r.a[5],r.pc==0x4d91a?0x5cdcU:0x5d08U,1,value))return false;
        r.pc=on23_b(value)==0U?(r.pc==0x4d91a?0x4d92aU:0x4d950U):(r.pc==0x4d91a?0x4d922U:0x4d948U);return true;
    case 0x4d922:r.d[0]=0;return on23_return_carry(c,AnimationCarrySet); // MOVEQ #0,D0; ORI.B #1,CCR; RTS.
    case 0x4d92a:r.a[0]=am_index(r.a[5],0x8da8);return am_call(c,0x289e,0x4d934); // LEA -7258(A5),A0; JSR 289e.l.
    case 0x4d934:return on23_carry(c,0x4d950,0x4d938);                  // BCC.W 4d950 (C returned by 289e).
    case 0x4d948:r.d[0]=1;return on23_return_carry(c,AnimationCarrySet); // MOVEQ #1,D0; ORI.B #1,CCR; RTS.
    case 0x4d950:r.d[0]=0xffffffffU;return on23_return_carry(c,AnimationCarryClear); // MOVEQ #ff,D0; ANDI.B #fe,CCR; RTS.
    // ---- 4d958: TST.B D0; BNE.W 4d966; LEA 5cba(A5),A4 / 5ce6(A5),A4; MOVE.W D1,1e(A4); RTS.
    case 0x4d958:r.pc=on23_b(r.d[0])!=0U?0x4d966:0x4d95e;return true;
    case 0x4d95e:case 0x4d966:return on23_slot(c,r.pc==0x4d966,0x4d96a);
    case 0x4d96a:if(!on23_put(c,r.a[4],0x1e,2,on23_w(r.d[1])))return false;return am_return(c);
    // ---- 4da4a: MOVEA.L #0,A0 / 4da50: MOVE.L A0,-(A7); MOVEM.W D0-D1,-(A7) (D1, D0); MOVEA.L #4db42,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x4da4a:r.a[0]=0;r.pc=0x4da50;return true;
    case 0x4da50:
        if(!am_push(c,4,r.a[0]) || !am_push(c,2,on23_w(r.d[1])) || !am_push(c,2,on23_w(r.d[0])))return false;
        r.a[0]=0x4db42;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x4da66);
    // MOVE.W (A7)+,76(A0); MOVE.W (A7)+,78(A0); MOVE.L (A7)+,7a(A0); RTS.
    case 0x4da66:
        if(!am_pop(c,2,value) || !on23_put(c,r.a[0],0x76,2,on23_w(value)) || !am_pop(c,2,value) || !on23_put(c,r.a[0],0x78,2,on23_w(value)) ||
            !am_pop(c,4,value) || !on23_put(c,r.a[0],0x7a,4,value))return false;
        return am_return(c);
    // ---- 4db42 (28ae child): MOVE.W #ea,20(A6); MOVE.L 200098.l,22(A6); MOVEA.L #4dc66,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x4db42:
        if(!on23_put(c,r.a[6],0x20,2,0xea) || !am_read(c,ON23_BANK_EA,4,value) || !on23_put(c,r.a[6],0x22,4,value))return false;
        r.a[1]=0x4dc66;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x4db60);
    case 0x4db60:am_word(r.d[0],0x3ad);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x4db6e); // MOVE.W #3ad,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVE.W #fff1,68(A6); MOVE.W #fff1,1e(A6); MOVE.W 76(A6),D0; MOVE.W 78(A6),D1; JSR 49290.l.
    case 0x4db6e:
        if(!on23_put(c,r.a[6],0x68,2,0xfff1) || !on23_put(c,r.a[6],0x1e,2,0xfff1) || !on23_get(c,r.a[6],0x76,2,value))return false;
        am_word(r.d[0],value);if(!on23_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[1],value);return am_call(c,0x49290,0x4db88);
    case 0x4db88:if(!am_write(c,r.a[6],4,0x4db8e))return false;r.pc=0x4db8e;return true; // MOVE.L #4db8e,(A6).
    // ---- 4db8e (installed): JSR 43e34.l; JSR 484b4.l; BCC.W 4dba4; JSR 49fc6.l.
    case 0x4db8e:return am_call(c,0x43e34,0x4db94);
    case 0x4db94:return am_call(c,0x484b4,0x4db9a);
    case 0x4db9a:return on23_carry(c,0x4dba4,0x4db9e);                  // BCC.W 4dba4 (C returned by 484b4).
    case 0x4db9e:return am_call(c,0x49fc6,0x4dba4);
    case 0x4dba4:if(!on23_get(c,r.a[6],0x7a,4,value))return false;r.pc=value==0U?0x4dbb6:0x4dbac;return true; // TST.L 7a(A6); BEQ.W.
    case 0x4dbac:if(!on23_get(c,r.a[6],0x7a,4,value))return false;r.a[1]=value;return am_call(c,r.a[1],0x4dbb2); // MOVEA.L; JSR (A1).
    case 0x4dbb2:return on23_carry(c,0x4dbb6,0x4dbd6);                  // BCS.W 4dbd6 (C returned by the JSR (A1) callee).
    case 0x4dbb6:return am_call(c,0x288c,0x4dbbc);                     // JSR 288c.l.
    case 0x4dbbc:return on23_carry(c,0x4dbd6,0x4dbc0);                  // BCC.W 4dbd6 (C returned by 288c).
    case 0x4dbca:return am_call(c,0x4d900,0x4dbce);                     // JSR 4d900(PC).
    case 0x4dbce:r.pc=(r.d[0]&0x80U)!=0U?0x4dbd4:0x4dbd6;return true;   // TST.B D0; BPL.W 4dbd6.
    case 0x4dbd6:case 0xc3b7e:case 0xc3c02:r.pc=0x2a00;return true;     // JMP 2a00.l.
    // ---- c3a7c (stage event callback): MOVE.W #1,7a(A6); MOVE.L #c3a38,80(A6); MOVE.L #c3a50,7c(A6); MOVE.W #82,54(A6); MOVE.W #10,D0.
    case 0xc3a7c:
        if(!on23_put(c,r.a[6],0x7a,2,1) || !on23_put(c,r.a[6],0x80,4,0xc3a38) || !on23_put(c,r.a[6],0x7c,4,0xc3a50) ||
            !on23_put(c,r.a[6],0x54,2,0x82))return false;
        am_word(r.d[0],0x10);r.pc=0xc3a9c;return true;
    // MOVE.W 76(A6),D1; BEQ.W c3aa6 / SUBQ.W #1,D1.
    case 0xc3a9c:if(!on23_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[1],value);r.pc=on23_w(value)==0U?0xc3aa6:0xc3aa4;return true;
    case 0xc3aa4:am_word(r.d[1],(r.d[1]+0xffffU)&65535U);r.pc=0xc3aa6;return true;
    // MOVE.W D1,D2; MOVEA.L 80(A6),A0; ADD.W D2,D2 (twice); MOVE.L (A0,D2.W),80(A6); ADD.W D1,D0; LEA 26(A6),A0; MOVE.W #ca,20(A6);
    // MOVE.L 200088.l,22(A6); LEA 26(A6),A0; MOVE.W D0,D1; ADD.W D1,D1 (twice); MOVEA.L 200088.l,A1; MOVEA.L (A1,D1.W),A1;
    // MOVE.W #100,D0; JSR 49f8c.l.
    case 0xc3aa6:
        am_word(r.d[2],r.d[1]);if(!on23_get(c,r.a[6],0x80,4,value))return false;r.a[0]=value;am_word(r.d[2],(r.d[2]*4U)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[2]),4,value) || !on23_put(c,r.a[6],0x80,4,value))return false;
        am_word(r.d[0],(r.d[0]+r.d[1])&65535U);r.a[0]=am_index(r.a[6],0x26);
        if(!on23_put(c,r.a[6],0x20,2,0xca) || !am_read(c,ON23_BANK_CA,4,value) || !on23_put(c,r.a[6],0x22,4,value))return false;
        r.a[0]=am_index(r.a[6],0x26);am_word(r.d[1],r.d[0]);am_word(r.d[1],(r.d[1]*4U)&65535U);
        if(!am_read(c,ON23_BANK_CA,4,value))return false;r.a[1]=value;
        if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xc3ae8);
    case 0xc3ae8:if(!on23_get(c,r.a[6],0x76,2,value))return false;r.pc=on23_w(value)!=0U?0xc3b02:0xc3af0;return true; // TST.W 76(A6).
    case 0xc3af0:am_word(r.d[0],0xce5);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xc3afe); // MOVE.W #ce5,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0xc3afe:case 0xc3b5a:r.pc=r.pc==0xc3afe?0xc3b14:0xc3b64;return true; // BRA.W.
    // MOVE.W #21,D0; MOVE.W #b,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xc3b02:am_word(r.d[0],0x21);am_word(r.d[1],0xb);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xc3b14);
    case 0xc3b14:am_word(r.d[0],0xce6);return am_call(c,0x4a496,0xc3b1e); // MOVE.W #ce6,D0; JSR 4a496.l.
    case 0xc3b1e:if(!on23_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);r.pc=on23_w(value)!=0U?0xc3b36:0xc3b26;return true;
    // MOVE.W #0,68(A6); MOVE.W #0,1e(A6); BRA.W c3b3e / MOVE.W D0,68(A6); MOVE.W D0,1e(A6).
    case 0xc3b26:case 0xc3b36:
        value=r.pc==0xc3b26?0U:on23_w(r.d[0]);if(!on23_put(c,r.a[6],0x68,2,value) || !on23_put(c,r.a[6],0x1e,2,value))return false;
        r.pc=0xc3b3e;return true;
    case 0xc3b3e:return am_call(c,0x4c0ac,0xc3b44);                     // JSR 4c0ac.l.
    case 0xc3b44:if(!am_write(c,r.a[6],4,0xc3b4a))return false;r.pc=0xc3b4a;return true; // MOVE.L #c3b4a,(A6).
    // ---- c3b4a (installed): BTST.B #7,15(A6); BNE.W c3b5e; JSR 4be2c.l / JSR 4be06.l; JSR 49fc6.l.
    case 0xc3b4a:if(!on23_bit(c,am_index(r.a[6],0x15),7,bit))return false;r.pc=bit?0xc3b5e:0xc3b54;return true;
    case 0xc3b54:return am_call(c,0x4be2c,0xc3b5a);
    case 0xc3b5e:return am_call(c,0x4be06,0xc3b64);
    case 0xc3b64:return am_call(c,0x49fc6,0xc3b6a);
    case 0xc3b6a:if(!on23_get(c,r.a[6],0x7c,4,value))return false;r.a[0]=value;return am_call(c,0x1ab02,0xc3b74); // MOVEA.L 7c(A6),A0.
    case 0xc3b74:return on23_carry(c,0xc3b84,0xc3b78);                  // BCC.W c3b84 (C returned by 1ab02).
    case 0xc3b78:case 0xc3bfc:return am_call(c,0x46ef4,r.pc+6U);        // JSR 46ef4.l.
    case 0xc3b84:if(!on23_get(c,r.a[6],0x76,2,value))return false;r.pc=on23_w(value)!=1U?0xc3c08:0xc3b8e;return true; // CMPI.W #1,76(A6).
    case 0xc3b8e:return am_call(c,0x4b54e,0xc3b94);                     // JSR 4b54e.l.
    case 0xc3b94:return on23_carry(c,0xc3b9c,0xc3b98);                  // BCC.W c3b9c (C returned by 4b54e).
    case 0xc3b98:if(!on23_put(c,r.a[6],0x5e,1,0))return false;r.pc=0xc3b9c;return true; // CLR.B 5e(A6).
    case 0xc3b9c:if(!on23_bit(c,am_index(r.a[6],0x61),7,bit))return false;r.pc=bit?0xc3ba6:0xc3c08;return true; // BTST.B #7,61(A6); BEQ.
    case 0xc3ba6:return am_call(c,0xe9112,0xc3bac);                     // JSR e9112.l (boundary).
    case 0xc3bac:if(!on23_get(c,r.a[6],0x7a,2,value))return false;r.pc=on23_w(value)!=0U?0xc3bda:0xc3bb4;return true; // TST.W 7a(A6).
    // MOVEA.L #d1d08 / #d1d38,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0xc3bb4:case 0xc3bda:
        r.a[0]=r.pc==0xc3bb4?0xd1d08U:0xd1d38U;am_word(r.d[0],0x14);return am_call(c,0x28ae,r.pc==0xc3bb4?0xc3bc4U:0xc3beaU);
    case 0xc3bc4:return on23_carry(c,0xc3bd6,0xc3bc8);                  // BCC.W c3bd6 (C returned by 28ae).
    case 0xc3bea:return on23_carry(c,0xc3bfc,0xc3bee);                  // BCC.W c3bfc (C returned by 28ae).
    // CLR.W D0; CLR.W D1; JSR 4970a.l.
    case 0xc3bc8:case 0xc3bee:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,r.pc+0xaU);
    case 0xc3bd2:case 0xc3bf8:r.carry=AnimationCarrySet;r.pc=r.pc==0xc3bd2?0xc3bd6:0xc3bfc;return true; // ORI.B #1,CCR.
    case 0xc3bd6:r.pc=0xc3bfc;return true;                               // BRA.W c3bfc.
    // MOVEA.L 80(A6),A0; CMPA.W #0,A0; BEQ.W c3c1a / JSR 4706c.l.
    case 0xc3c08:if(!on23_get(c,r.a[6],0x80,4,value))return false;r.a[0]=value;r.pc=value==0U?0xc3c1a:0xc3c14;return true;
    case 0xc3c14:return am_call(c,0x4706c,0xc3c1a);
    default:return am_error(c,"unsupported animation objects n23 PC");
    }
}
}
