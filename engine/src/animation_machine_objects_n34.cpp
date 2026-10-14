#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t ON34_SINE=0x4419e;   // LEA 4419e.l,A1 (fixed ROM WORD table, read through the live bus).
const std::uint32_t ON34_COSINE=0x4411e; // LEA 4411e.l,A2 (fixed ROM WORD table, read through the live bus).
const std::uint32_t ON34_FRAME=0x538e;   // LEA 538e(A5),Ax (frame record of the probe results).
std::uint32_t on34_b(std::uint32_t value) {return value&255U;}
std::uint32_t on34_w(std::uint32_t value) {return value&65535U;}
// Signed BYTE / WORD views (two's complement; no implementation-defined conversion).
std::int32_t on34_sb(std::uint32_t value) {value&=255U;return value>=128U?static_cast<std::int32_t>(value)-256:static_cast<std::int32_t>(value);}
std::int32_t on34_sw(std::uint32_t value) {value&=65535U;return value>=32768U?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);}
// N of a 32-bit result (BMI / BPL / BLT / BGE after TST.L / MOVE.L read only N; V = 0).
bool on34_minus(std::uint32_t value) {return (value&0x80000000U)!=0U;}
bool on34_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on34_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// op.W #value,d16(An) / op.W Dn,d16(An): read the WORD, write old + value (ADD) or old | value (OR).
bool on34_add_w(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t value) {
    std::uint32_t old=0;return on34_get(c,base,displacement,2,old) && on34_put(c,base,displacement,2,old+value);
}
bool on34_or_w(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t value) {
    std::uint32_t old=0;return on34_get(c,base,displacement,2,old) && on34_put(c,base,displacement,2,old|value);
}
// ADD.L Dn,d16(A5) / SUB.L Dn,d16(A5).
bool on34_add_l(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,bool subtract) {
    std::uint32_t old=0;if(!on34_get(c,c.s.a[5],displacement,4,old))return false;
    return on34_put(c,c.s.a[5],displacement,4,subtract?old-value:old+value);
}
// TST.B d16(An): true when the BYTE is zero.
bool on34_zero_b(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,bool& zero) {
    std::uint32_t value=0;if(!on34_get(c,base,displacement,1,value))return false;zero=value==0U;return true;
}
// MOVE.L a(A6),Dx; MOVE.L b(A6),Dy (two LONGs of one base, in order).
bool on34_pair(AnimationMachineContext& c,std::uint32_t base,std::uint32_t first,std::uint32_t& x,std::uint32_t& y) {
    return on34_get(c,base,first,4,x) && on34_get(c,base,first+4U,4,y);
}
// MULS.W (table,Dn.W),Dm: the signed low WORD of Dm times the signed table WORD (32-bit result into Dm).
bool on34_muls(AnimationMachineContext& c,std::uint32_t table,std::uint32_t index,std::uint32_t& r) {
    std::uint32_t value=0;if(!am_read(c,am_index(table,index),2,value))return false;
    const std::int32_t product=on34_sw(r)*on34_sw(value);r=static_cast<std::uint32_t>(product);return true;
}
// ASR.L #n,Dn (1 <= n <= 8).
std::uint32_t on34_asr_l(std::uint32_t value,unsigned int count) {
    const std::uint32_t shifted=value>>count;return on34_minus(value)?(shifted|~(0xffffffffU>>count)):shifted;
}
// ASR.W Dx,Dy: count = Dx mod 64; 16 or more fills the WORD with the sign bit.
std::uint32_t on34_asr_w(std::uint32_t value,std::uint32_t count) {
    value&=65535U;count&=63U;const bool negative=(value&0x8000U)!=0U;
    if(count>=16U)return negative?65535U:0U;
    std::uint32_t shifted=value>>count;if(negative)shifted|=(0xffffU<<(16U-count))&65535U;return shifted;
}
// MOVEA.L A1,A2; MOVEA.L A0,A1; LEA 538e(A5),A0; ADD.L 14(A1),D0; ADD.L 18(A1),D1; SUB.L 14(A0),D0; SUB.L 18(A0),D1;
// MOVEA.L 5c8e(A5),A0 (probe frame to the 538e frame, then A0 = the record R).
bool on34_rebase(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[2]=r.a[1];r.a[1]=r.a[0];r.a[0]=am_index(r.a[5],ON34_FRAME);
    if(!on34_get(c,r.a[1],0x14,4,value))return false;r.d[0]+=value;if(!on34_get(c,r.a[1],0x18,4,value))return false;r.d[1]+=value;
    if(!on34_get(c,r.a[0],0x14,4,value))return false;r.d[0]-=value;if(!on34_get(c,r.a[0],0x18,4,value))return false;r.d[1]-=value;
    if(!on34_get(c,r.a[5],0x5c8e,4,value))return false;r.a[0]=value;return true;
}
// MOVE.L x(A0),D0; MOVE.L x+4(A0),D1; MOVE.L 2e(A6),D2; MOVE.L 32(A6),D3; SUB.L D0,D2; SUB.L D1,D3; LEA 538e(A5),A0; JSR 469d8.l
// (from_node false), or the node to the record (from_node true: D0/D1 = 2e/32(A6), D2/D3 = record - node).
bool on34_probe(AnimationMachineContext& c,std::uint32_t displacement,bool from_node,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t x=0,y=0,nx=0,ny=0;
    if(from_node) {if(!on34_pair(c,r.a[6],0x2e,nx,ny) || !on34_pair(c,r.a[0],displacement,x,y))return false;r.d[0]=nx;r.d[1]=ny;r.d[2]=x-nx;r.d[3]=y-ny;}
    else {if(!on34_pair(c,r.a[0],displacement,x,y) || !on34_pair(c,r.a[6],0x2e,nx,ny))return false;r.d[0]=x;r.d[1]=y;r.d[2]=nx-x;r.d[3]=ny-y;}
    r.a[0]=am_index(r.a[5],ON34_FRAME);return am_call(c,0x469d8,return_pc);
}
// MOVE.L D2,-(A7); MOVE.L D3,-(A7); SUB.L D0,D2; SUB.L D1,D3; TST.B 5cb4(A5); BEQ.W skip (target pushed, delta in D2/D3).
bool on34_target(AnimationMachineContext& c,std::uint32_t skip_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;bool zero=false;
    if(!am_push(c,4,r.d[2]) || !am_push(c,4,r.d[3]))return false;r.d[2]-=r.d[0];r.d[3]-=r.d[1];
    if(!on34_zero_b(c,r.a[5],0x5cb4,zero))return false;r.pc=zero?skip_pc:next_pc;return true;
}
// SUBI.W #4000,D7; MOVE.W D7,x(A0); OR.W D6,y(A0); MOVE.L (A7)+,D3; MOVE.L (A7)+,D2; SUB.L D2,D0; SUB.L D3,D1; BSR.W 4c6f0.
bool on34_settle(AnimationMachineContext& c,std::uint32_t slope,std::uint32_t flags,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    am_word(r.d[7],r.d[7]+0xc000U);if(!on34_put(c,r.a[0],slope,2,r.d[7]) || !on34_or_w(c,r.a[0],flags,r.d[6]&65535U))return false;
    if(!am_pop(c,4,value))return false;r.d[3]=value;if(!am_pop(c,4,value))return false;r.d[2]=value;
    r.d[0]-=r.d[2];r.d[1]-=r.d[3];return am_call(c,0x4c6f0,return_pc);
}
// MOVE.W #mask,D1; AND.W D0,D1 (D1.W = D0.W & mask; returns the WORD).
std::uint32_t on34_mask_d1(AnimationMachineState& r,std::uint32_t mask) {am_word(r.d[1],r.d[0]&mask);return on34_w(r.d[1]);}
// MOVE.W #mask,D5; AND.W D6,D5 (D5.W = D6.W & mask; returns the WORD).
std::uint32_t on34_mask_d5(AnimationMachineState& r,std::uint32_t mask) {am_word(r.d[5],r.d[6]&mask);return on34_w(r.d[5]);}
// 4c4e2 / 4c57a: MOVE.W x(A0),D0; MOVE.W #8005,D1; AND.W D0,D1; CMPI.W #1,D1; BNE.W.
bool on34_pattern(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t miss_pc,std::uint32_t hit_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on34_get(c,r.a[0],displacement,2,value))return false;am_word(r.d[0],value);
    r.pc=on34_mask_d1(r,0x8005U)!=1U?miss_pc:hit_pc;return true;
}
// MOVE.B x(A0),D2; MOVE.B #value,9a(A0).
bool on34_pick(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t side) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on34_get(c,r.a[0],displacement,1,value))return false;am_byte(r.d[2],value);
    return on34_put(c,r.a[0],0x9a,1,side);
}
// MOVE.W #1,D1; AND.W x(A0),D1; BEQ.W.
bool on34_bit0(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on34_get(c,r.a[0],displacement,2,value))return false;
    am_word(r.d[1],value&1U);r.pc=(value&1U)==0U?zero_pc:set_pc;return true;
}
// MOVE.W D0,D1; OR.W 7e(A0),D1; ANDI.W #4,D1; BEQ.W.
bool on34_bit2(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on34_get(c,r.a[0],0x7e,2,value))return false;
    am_word(r.d[1],(r.d[0]|value)&4U);r.pc=on34_w(r.d[1])==0U?zero_pc:set_pc;return true;
}
// MOVE.W #11,D1; AND.W 7e(A0),D1; CMPI.W #11,D1; BNE.W.
bool on34_eleven(AnimationMachineContext& c,std::uint32_t miss_pc,std::uint32_t hit_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on34_get(c,r.a[0],0x7e,2,value))return false;
    am_word(r.d[1],value&0x11U);r.pc=on34_w(r.d[1])!=0x11U?miss_pc:hit_pc;return true;
}
// MOVE.B #0,9a(A0); MOVE.B 84(A0),D2; MOVE.W D2,D3; MOVE.L 2e(A6),x(A0); MOVE.L 32(A6),x+4(A0).
bool on34_flat(AnimationMachineContext& c,std::uint32_t displacement) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!on34_put(c,r.a[0],0x9a,1,0) || !on34_get(c,r.a[0],0x84,1,value))return false;am_byte(r.d[2],value);am_word(r.d[3],r.d[2]);
    if(!on34_get(c,r.a[6],0x2e,4,value) || !on34_put(c,r.a[0],displacement,4,value))return false;
    return on34_get(c,r.a[6],0x32,4,value) && on34_put(c,r.a[0],displacement+4U,4,value);
}
// MOVE.L 2e(A6),x(A0); MOVE.L 32(A6),x+4(A0).
bool on34_copy_node(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t value=0;
    return on34_get(c,c.s.a[6],0x2e,4,value) && on34_put(c,c.s.a[0],displacement,4,value) && on34_get(c,c.s.a[6],0x32,4,value) &&
        on34_put(c,c.s.a[0],displacement+4U,4,value);
}
// 4c660 / 4c688 tail: SUB.B D1,D0; MOVE.B D0,78(A0); MOVE.B #80,79(A0).
bool on34_clamp(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;am_byte(r.d[0],r.d[0]-r.d[1]);
    return on34_put(c,r.a[0],0x78,1,r.d[0]) && on34_put(c,r.a[0],0x79,1,0x80);
}
// MOVE.B 76(A0),D1; ADD.B D0,D1; SUBI.B #limit,D1 (returns the BYTE before the SUBI).
bool on34_reach(AnimationMachineContext& c,std::uint32_t limit,std::uint32_t& before) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on34_get(c,r.a[0],0x76,1,value))return false;
    am_byte(r.d[1],value+r.d[0]);before=on34_b(r.d[1]);am_byte(r.d[1],before-limit);return true;
}
// CMPI.W #0,76(A0); BLT.W (true when the WORD is negative).
bool on34_negative_76(AnimationMachineContext& c,bool& negative) {
    std::uint32_t value=0;if(!on34_get(c,c.s.a[0],0x76,2,value))return false;negative=(value&0x8000U)!=0U;return true;
}
// TST.L 64(A6) (the LONG).
bool on34_speed(AnimationMachineContext& c,std::uint32_t& value) {return on34_get(c,c.s.a[6],0x64,4,value);}
}
// Objects F4 N34 (220 block starts): the entry 4c3de (N28 2c76e; BRA.W into the body 4c810), the leaf 4c408 (2c24a, unrouted
// caller), the helpers 4c410 4c44c 4c4bc 4c660 4c6a4 4c72a (main decision: 4c72a..4c7a4 is called only by the body) and the body
// 4c810..4cf50. Callees of other units: u08b 4bc44 4bb22 4bf16, U08 43eb8, U09 469d8, N33 46bfc 4b8e8, N35 4c6f0. Boundary without an
// executor: 44602. 4c3f6..4c408 is unreferenced (interior). Fixed ROM reads: the WORD tables 4419e / 4411e (live bus). No consumer of
// a callee C, no known C producer, no port, X, DIV, bank.
bool animation_objects_n34_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool zero=false;
    switch(r.pc) {
    case 0x4c44a:case 0x4c488:case 0x4c4ac:case 0x4c4ba:case 0x4c65e:case 0x4c686:case 0x4c6a2:return am_return(c); // RTS.
    // ---- entry 4c3de: MOVE.L A0,5c8e(A5); JSR 4bc44(PC) / MOVE.B #ff,549f(A5); MOVE.B #ff,5cb4(A5); BRA.W 4c810.
    case 0x4c3de:if(!on34_put(c,r.a[5],0x5c8e,4,r.a[0]))return false;return am_call(c,0x4bc44,0x4c3e6);
    case 0x4c3e6:if(!on34_put(c,r.a[5],0x549f,1,0xff) || !on34_put(c,r.a[5],0x5cb4,1,0xff))return false;r.pc=0x4c810;return true;
    // ---- leaf 4c408: MOVE.W #80,78(A0); RTS.
    case 0x4c408:if(!on34_put(c,r.a[0],0x78,2,0x80))return false;return am_return(c);
    // ---- helper 4c410: ANDI.W #c005,D0; BNE.W 4c41c / MOVEQ #2,D7; RTS.
    case 0x4c410:am_word(r.d[0],r.d[0]&0xc005U);r.pc=on34_w(r.d[0])!=0U?0x4c41c:0x4c418;return true;
    case 0x4c418:r.d[7]=2;return am_return(c);
    case 0x4c41c:r.d[7]=0;am_word(r.d[1],r.d[1]&1U);r.pc=on34_w(r.d[1])==0U?0x4c428:0x4c426;return true; // MOVEQ #0,D7; ANDI.W #1,D1; BEQ.W.
    case 0x4c426:case 0x4c448:am_word(r.d[7],r.d[7]+1U);r.pc=r.pc==0x4c426U?0x4c428U:0x4c44aU;return true; // ADDQ.W #1,D7.
    case 0x4c428:am_word(r.d[2],r.d[0]&1U);r.pc=on34_w(r.d[2])==0U?0x4c436:0x4c432;return true; // MOVE.W #1,D2; AND.W D0,D2; BEQ.W.
    case 0x4c432:am_word(r.d[7],r.d[7]+1U);return am_return(c);       // ADDQ.W #1,D7; RTS.
    // ANDI.W #c000,D0; SNE.B D2; ANDI.W #1,D1; SNE.B D3; EOR.B D2,D3; BEQ.W 4c44a.
    case 0x4c436:
        am_word(r.d[0],r.d[0]&0xc000U);am_byte(r.d[2],on34_w(r.d[0])!=0U?0xffU:0U);am_word(r.d[1],r.d[1]&1U);
        am_byte(r.d[3],on34_w(r.d[1])!=0U?0xffU:0U);am_byte(r.d[3],r.d[3]^r.d[2]);r.pc=on34_b(r.d[3])==0U?0x4c44a:0x4c448;return true;
    // ---- helper 4c44c: MOVE.W 7a(A0),D0; MOVE.W 7e(A0),D1; BSR.B 4c410 / MOVE.W D7,D6; MOVE.W 7c(A0),D0; MOVE.W 7e(A0),D1; BSR.B 4c410.
    case 0x4c44c:case 0x4c456:
        if(r.pc==0x4c456U)am_word(r.d[6],r.d[7]);
        if(!on34_get(c,r.a[0],r.pc==0x4c44cU?0x7aU:0x7cU,2,value))return false;am_word(r.d[0],value);
        if(!on34_get(c,r.a[0],0x7e,2,value))return false;am_word(r.d[1],value);return am_call(c,0x4c410,r.pc==0x4c44cU?0x4c456U:0x4c462U);
    // CMP.B D6,D7; BEQ.W 4c47c; BMI.W 4c476.
    case 0x4c462:value=(r.d[7]-r.d[6])&255U;r.pc=value==0U?0x4c47c:((value&0x80U)!=0U?0x4c476:0x4c46c);return true;
    case 0x4c46c:if(!on34_add_w(c,r.a[0],0x78,0x10000U-0xa0U))return false;r.pc=0x4c47c;return true; // SUBI.W #a0,78(A0); BRA.W.
    case 0x4c476:if(!on34_add_w(c,r.a[0],0x78,0xa0))return false;r.pc=0x4c47c;return true;          // ADDI.W #a0,78(A0).
    // MOVE.W 7e(A0),D5; ANDI.W #1,D5; BNE.W 4c48a.
    case 0x4c47c:if(!on34_get(c,r.a[0],0x7e,2,value))return false;am_word(r.d[5],value&1U);r.pc=(value&1U)!=0U?0x4c48a:0x4c488;return true;
    // MOVE.W 84(A0),D0; SUB.W 76(A0),D0; BNE.W 4c49c.
    case 0x4c48a:
        if(!on34_get(c,r.a[0],0x84,2,value) || !on34_get(c,r.a[0],0x76,2,other))return false;am_word(r.d[0],value-other);
        r.pc=on34_w(r.d[0])!=0U?0x4c49c:0x4c496;return true;
    case 0x4c496:if(!on34_put(c,r.a[0],0x78,2,r.d[0]))return false;return am_return(c); // MOVE.W D0,78(A0); RTS.
    // BMI.W 4c4ae: N of 4c48e SUB.W (unique predecessor 4c492; the result is D0.W).
    case 0x4c49c:r.pc=(r.d[0]&0x8000U)!=0U?0x4c4ae:0x4c4a0;return true;
    // CMP.W 78(A0),D0; BGE.W 4c4ac / BLE.W 4c4ba (signed WORD compare).
    case 0x4c4a0:case 0x4c4ae:
        if(!on34_get(c,r.a[0],0x78,2,value))return false;
        if(r.pc==0x4c4a0U)r.pc=on34_sw(r.d[0])>=on34_sw(value)?0x4c4ac:0x4c4a8;else r.pc=on34_sw(r.d[0])<=on34_sw(value)?0x4c4ba:0x4c4b6;
        return true;
    case 0x4c4a8:case 0x4c4b6:if(!on34_put(c,r.a[0],0x78,2,r.d[0]))return false;r.pc+=4U;return true; // MOVE.W D0,78(A0).
    // ---- helper 4c4bc: MOVE.B 78(A0),9a(A0); TST.B 5cb4(A5); BEQ.W 4c65e.
    case 0x4c4bc:
        if(!on34_get(c,r.a[0],0x78,1,value) || !on34_put(c,r.a[0],0x9a,1,value) || !on34_zero_b(c,r.a[5],0x5cb4,zero))return false;
        r.pc=zero?0x4c65e:0x4c4ca;return true;
    // MOVEQ #0,D2; MOVE.B 76(A0),D2; MOVE.W D2,D3; TST.L 64(A6); BEQ.W 4c60e.
    case 0x4c4ca:
        r.d[2]=0;if(!on34_get(c,r.a[0],0x76,1,value))return false;am_byte(r.d[2],value);am_word(r.d[3],r.d[2]);
        if(!on34_speed(c,value))return false;r.pc=value==0U?0x4c60e:0x4c4da;return true;
    case 0x4c4da:if(!on34_speed(c,value))return false;r.pc=on34_minus(value)?0x4c4e2:0x4c57a;return true; // TST.L 64(A6); BPL.W 4c57a.
    case 0x4c4e2:return on34_pattern(c,0x7a,0x4c502,0x4c4f4);
    case 0x4c57a:return on34_pattern(c,0x7c,0x4c59a,0x4c58c);
    case 0x4c4f4:if(!on34_pick(c,0x80,0xff))return false;r.pc=0x4c522;return true; // MOVE.B 80(A0),D2; MOVE.B #ff,9a(A0); BRA.W.
    case 0x4c58c:if(!on34_pick(c,0x82,1))return false;r.pc=0x4c5ba;return true;    // MOVE.B 82(A0),D2; MOVE.B #1,9a(A0); BRA.W.
    // MOVE.W #8000,D1; AND.W D0,D1; BNE.W.
    case 0x4c502:r.pc=on34_mask_d1(r,0x8000U)!=0U?0x4c522:0x4c50c;return true;
    case 0x4c59a:r.pc=on34_mask_d1(r,0x8000U)!=0U?0x4c5ba:0x4c5a4;return true;
    case 0x4c50c:return on34_bit0(c,0x7c,0x4c522,0x4c518);                   // MOVE.W #1,D1; AND.W 7c(A0),D1; BEQ.W 4c522.
    case 0x4c5a4:return on34_bit0(c,0x7a,0x4c5ba,0x4c5b0);                   // MOVE.W #1,D1; AND.W 7a(A0),D1; BEQ.W 4c5ba.
    case 0x4c518:if(!on34_pick(c,0x82,1))return false;r.pc=0x4c522;return true;     // MOVE.B 82(A0),D2; MOVE.B #1,9a(A0).
    case 0x4c5b0:if(!on34_pick(c,0x80,0xff))return false;r.pc=0x4c5ba;return true;  // MOVE.B 80(A0),D2; MOVE.B #ff,9a(A0).
    // MOVE.W #4000,D1; AND.W D0,D1; BEQ.W.
    case 0x4c522:r.pc=on34_mask_d1(r,0x4000U)==0U?0x4c52e:0x4c52c;return true;
    case 0x4c5ba:r.pc=on34_mask_d1(r,0x4000U)==0U?0x4c5c6:0x4c5c4;return true;
    case 0x4c52c:case 0x4c5c4:am_word(r.d[3],r.d[2]);r.pc+=2U;return true;  // MOVE.W D2,D3.
    case 0x4c52e:return on34_bit2(c,0x4c546,0x4c53c);
    case 0x4c5c6:return on34_bit2(c,0x4c5de,0x4c5d4);
    case 0x4c53c:am_byte(r.d[3],0xe0);if(!on34_put(c,r.a[0],0x9a,1,1))return false;r.pc=0x4c546;return true;   // MOVE.B #e0,D3; MOVE.B #1,9a(A0).
    case 0x4c5d4:am_word(r.d[3],0x20);if(!on34_put(c,r.a[0],0x9a,1,0xff))return false;r.pc=0x4c5de;return true; // MOVE.W #20,D3; MOVE.B #ff,9a(A0).
    case 0x4c546:return on34_eleven(c,0x4c576,0x4c556);
    case 0x4c5de:return on34_eleven(c,0x4c60e,0x4c5ee);
    // TST.B 99(A0); BEQ.W.
    case 0x4c556:case 0x4c5ee:
        if(!on34_zero_b(c,r.a[0],0x99,zero))return false;
        r.pc=r.pc==0x4c556U?(zero?0x4c576U:0x4c55eU):(zero?0x4c60eU:0x4c5f6U);return true;
    case 0x4c55e:if(!on34_flat(c,0x8e))return false;r.pc=0x4c576;return true;
    case 0x4c5f6:if(!on34_flat(c,0x86))return false;r.pc=0x4c60e;return true;
    case 0x4c576:r.pc=0x4c60e;return true;                                   // BRA.W 4c60e.
    // ADD.W D2,D2; MOVE.L 64(A6),D0; ASR.L #8,D0; MOVE.L D0,D1; LEA 4419e.l,A1; LEA 4411e.l,A2; MULS.W (A1,D2.W),D0;
    // MULS.W (A2,D2.W),D1; MOVE.L D0,36(A6); MOVE.L D1,3a(A6); SUB.B 76(A0),D3; BEQ.W 4c65e.
    case 0x4c60e:
        am_word(r.d[2],r.d[2]+r.d[2]);if(!on34_speed(c,value))return false;r.d[0]=on34_asr_l(value,8);r.d[1]=r.d[0];
        r.a[1]=ON34_SINE;r.a[2]=ON34_COSINE;if(!on34_muls(c,r.a[1],r.d[2],r.d[0]) || !on34_muls(c,r.a[2],r.d[2],r.d[1]))return false;
        if(!on34_put(c,r.a[6],0x36,4,r.d[0]) || !on34_put(c,r.a[6],0x3a,4,r.d[1]) || !on34_get(c,r.a[0],0x76,1,value))return false;
        am_byte(r.d[3],r.d[3]-value);r.pc=on34_b(r.d[3])==0U?0x4c65e:0x4c63c;return true;
    // LSL.W #8,D3; MOVE.W 64(A6),D0; BMI.W 4c648.
    case 0x4c63c:
        am_word(r.d[3],r.d[3]<<8);if(!on34_get(c,r.a[6],0x64,2,value))return false;am_word(r.d[0],value);
        r.pc=(value&0x8000U)!=0U?0x4c648:0x4c646;return true;
    case 0x4c646:am_word(r.d[0],~r.d[0]);r.pc=0x4c648;return true;          // NOT.W D0.
    // ADDI.W #9,D0; BCC.W 4c652 (WORD carry).
    case 0x4c648:value=on34_w(r.d[0])+9U;am_word(r.d[0],value);r.pc=value>65535U?0x4c650:0x4c652;return true;
    case 0x4c650:am_word(r.d[3],on34_asr_w(r.d[3],r.d[0]));r.pc=0x4c652;return true; // ASR.W D0,D3.
    case 0x4c652:r.pc=(r.d[3]&0x8000U)!=0U?0x4c65a:0x4c658;return true;    // TST.W D3; BMI.W 4c65a.
    case 0x4c658:am_word(r.d[3],r.d[3]+1U);r.pc=0x4c65a;return true;      // ADDQ.W #1,D3.
    case 0x4c65a:if(!on34_add_w(c,r.a[0],0x78,r.d[3]&65535U))return false;r.pc=0x4c65e;return true; // ADD.W D3,78(A0).
    // ---- helper 4c660: MOVE.B 78(A0),D0; BEQ.W 4c6a2; BMI.W 4c688.
    case 0x4c660:
        if(!on34_get(c,r.a[0],0x78,1,value))return false;am_byte(r.d[0],value);
        r.pc=value==0U?0x4c6a2:((value&0x80U)!=0U?0x4c688:0x4c66c);return true;
    // MOVE.B 76(A0),D1; ADD.B D0,D1; SUBI.B #20,D1; BLE.W 4c686 / SUBI.B #e0,D1; BGE.W 4c6a2 (signed BYTE compare).
    case 0x4c66c:if(!on34_reach(c,0x20,value))return false;r.pc=on34_sb(value)<=0x20?0x4c686:0x4c67a;return true;
    case 0x4c688:if(!on34_reach(c,0xe0,value))return false;r.pc=on34_sb(value)>=-0x20?0x4c6a2:0x4c696;return true;
    case 0x4c67a:case 0x4c696:if(!on34_clamp(c))return false;r.pc+=12U;return true;
    // ---- helper 4c6a4: the 5cac / 5cb0 and 5ca4 / 5ca8 vectors (MULS.W 1800 by the tables at BYTE 76 and 76 + 78), RTS.
    case 0x4c6a4:
        am_word(r.d[0],0x1800);am_word(r.d[1],r.d[0]);am_word(r.d[2],r.d[0]);am_word(r.d[3],r.d[0]);r.d[7]=0;
        if(!on34_get(c,r.a[0],0x76,1,value))return false;am_byte(r.d[7],value);am_word(r.d[7],r.d[7]+r.d[7]);
        r.a[1]=ON34_SINE;r.a[2]=ON34_COSINE;if(!on34_muls(c,r.a[1],r.d[7],r.d[0]) || !on34_muls(c,r.a[2],r.d[7],r.d[1]))return false;
        if(!on34_put(c,r.a[5],0x5cac,4,r.d[0]) || !on34_put(c,r.a[5],0x5cb0,4,r.d[1]) || !on34_get(c,r.a[0],0x78,1,value))return false;
        am_word(r.d[7],on34_w(r.d[7])>>1);am_byte(r.d[7],r.d[7]+value);am_word(r.d[7],r.d[7]+r.d[7]);
        if(!on34_muls(c,r.a[1],r.d[7],r.d[2]) || !on34_muls(c,r.a[2],r.d[7],r.d[3]))return false;r.d[2]-=r.d[0];r.d[3]-=r.d[1];
        if(!on34_put(c,r.a[5],0x5ca4,4,r.d[2]) || !on34_put(c,r.a[5],0x5ca8,4,r.d[3]))return false;return am_return(c);
    // ---- helper 4c72a: LSL.L #2,D0; BPL.W 4c736 / ADDI.L #ffff,D0 / LSL.L #2,D1; BPL.W 4c742 / ADDI.L #ffff,D1 (N of the LSL result).
    case 0x4c72a:case 0x4c736:{
        const unsigned int k=r.pc==0x4c72aU?0U:1U;r.d[k]<<=2;r.pc=on34_minus(r.d[k])?r.pc+6U:r.pc+12U;return true;}
    case 0x4c730:case 0x4c73c:{const unsigned int k=r.pc==0x4c730U?0U:1U;r.d[k]+=0xffffU;r.pc+=6U;return true;}
    case 0x4c742:am_swap(r.d[0]);am_swap(r.d[1]);return am_call(c,0x44602,0x4c74c); // SWAP D0; SWAP D1; JSR 44602.l (boundary).
    // MOVEA.L 5c8e(A5),A0; SUB.B 76(A0),D0; LSL.W #8,D0; SUBI.W #80,D0; MOVEQ #0,D1; MOVE.B 79(A0),D1; ADD.W D1,D0; SUB.W D0,5c9a(A5);
    // LEA 4419e.l,A1; LEA 4411e.l,A2; MOVE.W 78(A0),D1; SUB.W D0,D1; LSR.W #8,D1; MOVEQ #0,D0; MOVE.B 76(A0),D0; ADD.B D0,D1;
    // ADD.B 78(A0),D0; ADD.W D0,D0; ADD.W D1,D1; MOVE.W (A1,D1.W),D2; MOVE.W (A2,D1.W),D3; SUB.W (A1,D0.W),D2; SUB.W (A2,D0.W),D3;
    // MULS.W #1800,D2; MULS.W #1800,D3; RTS.
    case 0x4c74c:{
        if(!on34_get(c,r.a[5],0x5c8e,4,value))return false;r.a[0]=value;if(!on34_get(c,r.a[0],0x76,1,value))return false;
        am_byte(r.d[0],r.d[0]-value);am_word(r.d[0],r.d[0]<<8);am_word(r.d[0],r.d[0]+0x10000U-0x80U);r.d[1]=0;
        if(!on34_get(c,r.a[0],0x79,1,value))return false;am_byte(r.d[1],value);am_word(r.d[0],r.d[0]+r.d[1]);
        if(!on34_get(c,r.a[5],0x5c9a,2,value) || !on34_put(c,r.a[5],0x5c9a,2,value-r.d[0]))return false;
        r.a[1]=ON34_SINE;r.a[2]=ON34_COSINE;if(!on34_get(c,r.a[0],0x78,2,value))return false;am_word(r.d[1],value-r.d[0]);
        am_word(r.d[1],on34_w(r.d[1])>>8);r.d[0]=0;if(!on34_get(c,r.a[0],0x76,1,value))return false;am_byte(r.d[0],value);
        am_byte(r.d[1],r.d[1]+r.d[0]);if(!on34_get(c,r.a[0],0x78,1,value))return false;am_byte(r.d[0],r.d[0]+value);
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[1],r.d[1]+r.d[1]);
        if(!am_read(c,am_index(r.a[1],r.d[1]),2,value))return false;am_word(r.d[2],value);
        if(!am_read(c,am_index(r.a[2],r.d[1]),2,value))return false;am_word(r.d[3],value);
        if(!am_read(c,am_index(r.a[1],r.d[0]),2,value))return false;am_word(r.d[2],r.d[2]-value);
        if(!am_read(c,am_index(r.a[2],r.d[0]),2,value))return false;am_word(r.d[3],r.d[3]-value);
        r.d[2]=static_cast<std::uint32_t>(on34_sw(r.d[2])*0x1800);r.d[3]=static_cast<std::uint32_t>(on34_sw(r.d[3])*0x1800);return am_return(c);}
    // ---- body 4c810: CLR.B 549d(A5); MOVEM.L 2e(A6),D0-D3/A0; LEA 538e(A5),A1; JSR 43eb8.l.
    case 0x4c810:{
        std::uint32_t v[5]={0,0,0,0,0};if(!on34_put(c,r.a[5],0x549d,1,0))return false;
        for(unsigned int i=0;i<5;++i)if(!on34_get(c,r.a[6],0x2eU+4U*i,4,v[i]))return false;
        r.d[0]=v[0];r.d[1]=v[1];r.d[2]=v[2];r.d[3]=v[3];r.a[0]=v[4];r.a[1]=am_index(r.a[5],ON34_FRAME);return am_call(c,0x43eb8,0x4c824);}
    // MOVEM.L D0-D3/A1,2e(A6); MOVEA.L 5c8e(A5),A0; TST.B 9b(A0); BEQ.W 4c83c.
    case 0x4c824:{
        const std::uint32_t v[5]={r.d[0],r.d[1],r.d[2],r.d[3],r.a[1]};
        for(unsigned int i=0;i<5;++i)if(!on34_put(c,r.a[6],0x2eU+4U*i,4,v[i]))return false;
        if(!on34_get(c,r.a[5],0x5c8e,4,value))return false;r.a[0]=value;if(!on34_zero_b(c,r.a[0],0x9b,zero))return false;
        r.pc=zero?0x4c83c:0x4c836;return true;}
    case 0x4c836:if(!on34_get(c,r.a[5],0x54a4,2,value) || !on34_put(c,r.a[0],0x98,2,value))return false;r.pc=0x4c83c;return true;
    case 0x4c83c:return am_call(c,0x4c44c,0x4c840);                          // BSR.W 4c44c.
    case 0x4c840:return am_call(c,0x4c4bc,0x4c844);                          // BSR.W 4c4bc.
    case 0x4c844:return am_call(c,0x4c660,0x4c848);                          // BSR.W 4c660.
    // MOVE.B #ff,9b(A0); CLR.B 9c(A0); MOVEA.L 5c8e(A5),A0; BSR.W 4c6a4.
    case 0x4c848:
        if(!on34_put(c,r.a[0],0x9b,1,0xff) || !on34_put(c,r.a[0],0x9c,1,0) || !on34_get(c,r.a[5],0x5c8e,4,value))return false;
        r.a[0]=value;return am_call(c,0x4c6a4,0x4c85a);
    // CLR.L 5c92 5c96, CLR.W 5c9a, CLR.L 5c9c 5ca0 (A5); MOVE.W 54a2(A5),-(A7); MOVE.W #ffff,54a2(A5); CLR.W 7a(A0); CLR.W 7c(A0);
    // MOVE.L #ffffffff,5cb6(A5); MOVE.W #ff,54a4(A5); the 8e / 92 probe from the node (JSR 469d8.l).
    case 0x4c85a:
        if(!on34_put(c,r.a[5],0x5c92,4,0) || !on34_put(c,r.a[5],0x5c96,4,0) || !on34_put(c,r.a[5],0x5c9a,2,0) ||
            !on34_put(c,r.a[5],0x5c9c,4,0) || !on34_put(c,r.a[5],0x5ca0,4,0) || !on34_get(c,r.a[5],0x54a2,2,value) || !am_push(c,2,value) ||
            !on34_put(c,r.a[5],0x54a2,2,0xffff) || !on34_put(c,r.a[0],0x7a,2,0) || !on34_put(c,r.a[0],0x7c,2,0) ||
            !on34_put(c,r.a[5],0x5cb6,4,0xffffffffU) || !on34_put(c,r.a[5],0x54a4,2,0xff))return false;
        return on34_probe(c,0x8e,true,0x4c8ac);
    case 0x4c8ac:case 0x4c90e:case 0x4c9f8:case 0x4cacc:case 0x4cb3e:case 0x4cc38:return am_call(c,0x46bfc,r.pc+6U); // JSR 46bfc.l.
    // Rebase; MOVE.W #2,D5; AND.W D6,D5; BEQ.W.
    case 0x4c8b2:if(!on34_rebase(c))return false;r.pc=on34_mask_d5(r,2)==0U?0x4c8e2:0x4c8d8;return true;
    case 0x4cad2:if(!on34_rebase(c))return false;r.pc=on34_mask_d5(r,2)==0U?0x4cb12:0x4caf8;return true;
    // ORI.W #4000,7a(A0); MOVE.L A2,5cb6(A5).
    case 0x4c8d8:if(!on34_or_w(c,r.a[0],0x7a,0x4000) || !on34_put(c,r.a[5],0x5cb6,4,r.a[2]))return false;r.pc=0x4c8e2;return true;
    // MOVE.W #400,D5; AND.W D6,D5; BEQ.W.
    case 0x4c8e2:r.pc=on34_mask_d5(r,0x400)==0U?0x4c8f0:0x4c8ec;return true;
    case 0x4cb12:r.pc=on34_mask_d5(r,0x400)==0U?0x4cb20:0x4cb1c;return true;
    case 0x4c8ec:case 0x4cb1c:if(!on34_put(c,r.a[0],0x9b,1,0))return false;r.pc+=4U;return true; // CLR.B 9b(A0).
    case 0x4c8f0:return on34_probe(c,0x8e,false,0x4c90e);                    // the probe from 8e / 92 to the node.
    case 0x4cb20:return on34_probe(c,0x86,false,0x4cb3e);                    // the probe from 86 / 8a to the node.
    // Rebase; ANDI.W #2,D6; BEQ.W.
    case 0x4c914:case 0x4cb44:
        if(!on34_rebase(c))return false;am_word(r.d[6],r.d[6]&2U);
        r.pc=on34_w(r.d[6])==0U?(r.pc==0x4c914U?0x4c992U:0x4cbd2U):(r.pc==0x4c914U?0x4c938U:0x4cb68U);return true;
    // ORI.W #8000,7a(A0); MOVE.L A2,5cb6(A5); CMPI.B #e0,76(A0); BNE.W 4c992.
    case 0x4c938:
        if(!on34_or_w(c,r.a[0],0x7a,0x8000) || !on34_put(c,r.a[5],0x5cb6,4,r.a[2]) || !on34_get(c,r.a[0],0x76,1,value))return false;
        r.pc=value!=0xe0U?0x4c992:0x4c94c;return true;
    // MOVE.W 7e(A0),D0; OR.W 7c(A0),D0 (7a(A0) at 4cb8c); ANDI.W #1,D0; BNE.W.
    case 0x4c94c:case 0x4cb8c:
        if(!on34_get(c,r.a[0],0x7e,2,value) || !on34_get(c,r.a[0],r.pc==0x4c94cU?0x7cU:0x7aU,2,other))return false;
        am_word(r.d[0],(value|other)&1U);r.pc=on34_w(r.d[0])!=0U?(r.pc==0x4c94cU?0x4c992U:0x4cbd2U):(r.pc==0x4c94cU?0x4c95cU:0x4cb9cU);return true;
    // TST.B 5cb4(A5); BEQ.W.
    case 0x4c95c:case 0x4cb9c:
        if(!on34_zero_b(c,r.a[5],0x5cb4,zero))return false;
        r.pc=zero?(r.pc==0x4c95cU?0x4c96cU:0x4cbacU):(r.pc==0x4c95cU?0x4c964U:0x4cba4U);return true;
    case 0x4c964:if(!on34_speed(c,value))return false;r.pc=on34_minus(value)?0x4c992:0x4c96c;return true; // TST.L 64(A6); BLT.W.
    case 0x4cba4:if(!on34_speed(c,value))return false;r.pc=(!on34_minus(value) && value!=0U)?0x4cbd2:0x4cbac;return true; // BGT.W.
    // MOVE.B #ff,9c(A0); D0/D1 = 2e/32(A6); D2/D3 = the record pair; SUB.L; ASR.L #1 (D2 D3 / D3 D2); ADD.L D0,D2; ADD.L D1,D3; BRA.W.
    case 0x4c96c:case 0x4cbac:{
        const bool first=r.pc==0x4c96cU;std::uint32_t x=0,y=0;
        if(!on34_put(c,r.a[0],0x9c,1,0xff) || !on34_pair(c,r.a[6],0x2e,value,other) || !on34_pair(c,r.a[0],first?0x8eU:0x86U,x,y))return false;
        r.d[0]=value;r.d[1]=other;r.d[2]=on34_asr_l(x-value,1)+value;r.d[3]=on34_asr_l(y-other,1)+other;r.pc=first?0x4c9d0:0x4cc10;return true;}
    // D0/D1 = the record pair; D2/D3 = 2e/32(A6) -/+ 5cac/5cb0(A5); MOVE.B 9a(A0),D6; BLT.W 4c9c8 / BGT.W 4cc08.
    case 0x4c992:case 0x4cbd2:{
        const bool first=r.pc==0x4c992U;std::uint32_t x=0,y=0;
        if(!on34_pair(c,r.a[0],first?0x8eU:0x86U,value,other) || !on34_pair(c,r.a[6],0x2e,x,y))return false;r.d[0]=value;r.d[1]=other;
        std::uint32_t ax=0,ay=0;if(!on34_pair(c,r.a[5],0x5cac,ax,ay))return false;
        r.d[2]=first?x-ax:x+ax;r.d[3]=first?y-ay:y+ay;if(!on34_get(c,r.a[0],0x9a,1,value))return false;am_byte(r.d[6],value);
        if(first)r.pc=(value&0x80U)!=0U?0x4c9c8:0x4c9b2;else r.pc=((value&0x80U)==0U && value!=0U)?0x4cc08:0x4cbf2;return true;}
    // MOVE.L 5ca4(A5),D4; MOVE.L 5ca8(A5),D5; TST.B D6; BLE.W 4c9c4 / BGE.W 4cc04.
    case 0x4c9b2:case 0x4cbf2:
        if(!on34_pair(c,r.a[5],0x5ca4,value,other))return false;r.d[4]=value;r.d[5]=other;value=on34_b(r.d[6]);
        if(r.pc==0x4c9b2U)r.pc=((value&0x80U)!=0U || value==0U)?0x4c9c4:0x4c9c0;else r.pc=(value&0x80U)==0U?0x4cc04:0x4cc00;return true;
    case 0x4c9c0:case 0x4cc00:r.d[4]+=r.d[4];r.d[5]+=r.d[5];r.pc+=4U;return true; // ADD.L D4,D4; ADD.L D5,D5.
    case 0x4c9c4:r.d[2]-=r.d[4];r.d[3]-=r.d[5];r.pc=0x4c9c8;return true;    // SUB.L D4,D2; SUB.L D5,D3.
    case 0x4cc04:r.d[2]+=r.d[4];r.d[3]+=r.d[5];r.pc=0x4cc08;return true;    // ADD.L D4,D2; ADD.L D5,D3.
    // ADD.L 36(A6),D2; ADD.L 3a(A6),D3.
    case 0x4c9c8:case 0x4cc08:if(!on34_pair(c,r.a[6],0x36,value,other))return false;r.d[2]+=value;r.d[3]+=other;r.pc+=8U;return true;
    case 0x4c9d0:return on34_target(c,0x4c9ee,0x4c9e0);
    case 0x4cc10:return on34_target(c,0x4cc2e,0x4cc20);
    case 0x4c9e0:if(!on34_speed(c,value))return false;r.pc=on34_minus(value)?0x4c9e8:0x4c9ee;return true; // TST.L 64(A6); BGE.W 4c9ee.
    case 0x4cc20:if(!on34_speed(c,value))return false;r.pc=(on34_minus(value) || value==0U)?0x4cc2e:0x4cc28;return true; // BLE.W 4cc2e.
    // MOVE.W 98(A0),54a4(A5).
    case 0x4c9e8:case 0x4cc28:if(!on34_get(c,r.a[0],0x98,2,value) || !on34_put(c,r.a[5],0x54a4,2,value))return false;r.pc+=6U;return true;
    // LEA 538e(A5),A0; JSR 469d8.l.
    case 0x4c9ee:case 0x4cc2e:r.a[0]=am_index(r.a[5],ON34_FRAME);return am_call(c,0x469d8,r.pc+10U);
    // Rebase; BTST.B #0,D6; BEQ.W.
    case 0x4c9fe:if(!on34_rebase(c))return false;r.pc=(r.d[6]&1U)==0U?0x4ca26:0x4ca22;return true;
    case 0x4cc3e:if(!on34_rebase(c))return false;r.pc=(r.d[6]&1U)==0U?0x4cc76:0x4cc62;return true;
    case 0x4ca22:case 0x4cc72:if(!on34_put(c,r.a[5],0x5cb6,4,r.a[1]))return false;r.pc+=4U;return true; // MOVE.L A1,5cb6(A5).
    // MOVE.L D0,x(A0); MOVE.L D1,x+4(A0); MOVE.W #10,D5; AND.W D6,D5; BEQ.W.
    case 0x4ca26:case 0x4cc76:{
        const bool first=r.pc==0x4ca26U;
        if(!on34_put(c,r.a[0],first?0x8eU:0x86U,4,r.d[0]) || !on34_put(c,r.a[0],first?0x92U:0x8aU,4,r.d[1]))return false;
        r.pc=on34_mask_d5(r,0x10)==0U?(first?0x4ca54U:0x4cca4U):(first?0x4ca38U:0x4cc88U);return true;}
    // TST.B 5cb4(A5); BEQ.W / TST.B 99(A0); BEQ.W.
    case 0x4ca38:case 0x4cc88:if(!on34_zero_b(c,r.a[5],0x5cb4,zero))return false;r.pc=zero?r.pc+0x1cU:r.pc+8U;return true;
    case 0x4ca40:case 0x4cc90:if(!on34_zero_b(c,r.a[0],0x99,zero))return false;r.pc=zero?r.pc+0x14U:r.pc+8U;return true;
    case 0x4ca48:if(!on34_copy_node(c,0x8e))return false;r.pc=0x4ca54;return true;
    case 0x4cc98:if(!on34_copy_node(c,0x86))return false;r.pc=0x4cca4;return true;
    case 0x4ca54:return on34_settle(c,0x80,0x7a,0x4ca6c);
    case 0x4cca4:return on34_settle(c,0x82,0x7c,0x4ccbc);
    // MOVE.L D0,D7; OR.L D1,D7; BEQ.W.
    case 0x4ca6c:case 0x4ccbc:r.d[7]=r.d[0]|r.d[1];r.pc=r.d[7]==0U?r.pc+0x3cU+(r.pc==0x4ccbcU?4U:0U):r.pc+8U;return true;
    // MOVE.W #4,D6; AND.W 7a(A0),D6 (7c(A0) at 4ccc4); BNE.W.
    case 0x4ca74:case 0x4ccc4:
        if(!on34_get(c,r.a[0],r.pc==0x4ca74U?0x7aU:0x7cU,2,value))return false;am_word(r.d[6],value&4U);
        r.pc=on34_w(r.d[6])!=0U?(r.pc==0x4ca74U?0x4caa8U:0x4ccfcU):r.pc+0xcU;return true;
    case 0x4ca80:if(!on34_get(c,r.a[0],0x9a,1,value))return false;r.pc=(value&0x80U)!=0U?0x4caa8:0x4ca88;return true; // TST.B 9a; BLT.W.
    // MOVEQ #0,D0; MOVEQ #0,D1; TST.B 9a(A0); BGT.W 4ccfc.
    case 0x4ccd0:r.d[0]=0;r.d[1]=0;if(!on34_get(c,r.a[0],0x9a,1,value))return false;r.pc=((value&0x80U)==0U && value!=0U)?0x4ccfc:0x4ccdc;return true;
    // D0/D1 = 5cac/5cb0(A5); SUB.L 2e(A6),D2; SUB.L 32(A6),D3; SUB.L (ADD.L at 4ccdc) D2,D0 / D3,D1; BSR.W 4c72a.
    case 0x4ca88:case 0x4ccdc:{
        std::uint32_t x=0,y=0;if(!on34_pair(c,r.a[5],0x5cac,value,other) || !on34_pair(c,r.a[6],0x2e,x,y))return false;
        r.d[2]-=x;r.d[3]-=y;
        if(r.pc==0x4ca88U){r.d[0]=value-r.d[2];r.d[1]=other-r.d[3];}else {r.d[0]=value+r.d[2];r.d[1]=other+r.d[3];}
        return am_call(c,0x4c72a,r.pc+0x18U);}
    // ADD.L D2,5c9c(A5); ADD.L D3,5ca0(A5) / SUB.L.
    case 0x4caa0:case 0x4ccf4:{
        const bool subtract=r.pc==0x4ccf4U;
        if(!on34_add_l(c,0x5c9c,r.d[2],subtract) || !on34_add_l(c,0x5ca0,r.d[3],subtract))return false;r.pc+=8U;return true;}
    // MOVE.W #ff,54a4(A5); the 86 / 8a probe from the node (JSR 469d8.l).
    case 0x4caa8:if(!on34_put(c,r.a[5],0x54a4,2,0xff))return false;return on34_probe(c,0x86,true,0x4cacc);
    // MOVE.W #4000,7c(A0); TST.W 5cb6(A5); BMI.B 4cb0e.
    case 0x4caf8:
        if(!on34_put(c,r.a[0],0x7c,2,0x4000) || !on34_get(c,r.a[5],0x5cb6,2,value))return false;
        r.pc=(value&0x8000U)!=0U?0x4cb0e:0x4cb04;return true;
    // ORI.W #8000,7c(A0); TST.L 5cb6(A5); BMI.B 4cb7e.
    case 0x4cb68:
        if(!on34_or_w(c,r.a[0],0x7c,0x8000) || !on34_get(c,r.a[5],0x5cb6,4,value))return false;r.pc=on34_minus(value)?0x4cb7e:0x4cb74;return true;
    case 0x4cc62:if(!on34_get(c,r.a[5],0x5cb6,4,value))return false;r.pc=on34_minus(value)?0x4cc72:0x4cc68;return true; // TST.L; BMI.B.
    // CMPI.W #0,76(A0); BLT.W.
    case 0x4cb04:if(!on34_negative_76(c,zero))return false;r.pc=zero?0x4cb12:0x4cb0e;return true;
    case 0x4cb74:if(!on34_negative_76(c,zero))return false;r.pc=zero?0x4cb82:0x4cb7e;return true;
    case 0x4cc68:if(!on34_negative_76(c,zero))return false;r.pc=zero?0x4cc76:0x4cc72;return true;
    case 0x4cb0e:case 0x4cb7e:if(!on34_put(c,r.a[5],0x5cb6,4,r.a[2]))return false;r.pc+=4U;return true; // MOVE.L A2,5cb6(A5).
    // CMPI.B #20,76(A0); BNE.W 4cbd2.
    case 0x4cb82:if(!on34_get(c,r.a[0],0x76,1,value))return false;r.pc=value!=0x20U?0x4cbd2:0x4cb8c;return true;
    // MOVE.W (A7)+,54a2(A5); TST.B 5cb4(A5); BEQ.W 4cd50.
    case 0x4ccfc:
        if(!am_pop(c,2,value) || !on34_put(c,r.a[5],0x54a2,2,value) || !on34_zero_b(c,r.a[5],0x5cb4,zero))return false;
        r.pc=zero?0x4cd50:0x4cd08;return true;
    case 0x4cd08:if(!on34_speed(c,value))return false;r.pc=value!=0U?0x4cd50:0x4cd10;return true; // TST.L 64(A6); BNE.W 4cd50.
    // MOVE.L 5c92(A5),D0 / 5c96(A5),D1; BPL.W.
    case 0x4cd10:case 0x4cd1a:{
        const unsigned int k=r.pc==0x4cd10U?0U:1U;if(!on34_get(c,r.a[5],k==0U?0x5c92U:0x5c96U,4,value))return false;r.d[k]=value;
        r.pc=on34_minus(value)?r.pc+8U:r.pc+10U;return true;}
    case 0x4cd18:case 0x4cd22:{const unsigned int k=r.pc==0x4cd18U?0U:1U;r.d[k]=0U-r.d[k];r.pc+=2U;return true;} // NEG.L.
    // ADD.L D0,D1; CMPI.L #10000,D1; BCC.W 4cd38.
    case 0x4cd24:r.d[1]+=r.d[0];r.pc=r.d[1]>=0x10000U?0x4cd38:0x4cd30;return true;
    case 0x4cd30:if(!on34_put(c,r.a[5],0x5c92,4,0) || !on34_put(c,r.a[5],0x5c96,4,0))return false;r.pc=0x4cd38;return true;
    // MOVE.W 5c9a(A5),D0; ADDI.W #100,D0; CMPI.W #200,D0; BHI.W 4cd50.
    case 0x4cd38:
        if(!on34_get(c,r.a[5],0x5c9a,2,value))return false;am_word(r.d[0],value+0x100U);r.pc=on34_w(r.d[0])>0x200U?0x4cd50:0x4cd48;return true;
    case 0x4cd48:if(!on34_put(c,r.a[5],0x5c9c,4,0) || !on34_put(c,r.a[5],0x5ca0,4,0))return false;r.pc=0x4cd50;return true;
    // MOVEM.L 2e(A6),D0-D3; ADD.L 5c92 5c96 5c9c 5ca0 (A5); TST.B 78(A0); BEQ.W 4cd86; BMI.W 4cd7e.
    case 0x4cd50:{
        std::uint32_t v[4]={0,0,0,0};for(unsigned int i=0;i<4;++i)if(!on34_get(c,r.a[6],0x2eU+4U*i,4,v[i]))return false;
        r.d[0]=v[0];r.d[1]=v[1];r.d[2]=v[2];r.d[3]=v[3];
        if(!on34_get(c,r.a[5],0x5c92,4,value))return false;r.d[2]+=value;if(!on34_get(c,r.a[5],0x5c96,4,value))return false;r.d[3]+=value;
        if(!on34_get(c,r.a[5],0x5c9c,4,value))return false;r.d[2]+=value;if(!on34_get(c,r.a[5],0x5ca0,4,value))return false;r.d[3]+=value;
        if(!on34_get(c,r.a[0],0x78,1,value))return false;r.pc=value==0U?0x4cd86:((value&0x80U)!=0U?0x4cd7e:0x4cd72);return true;}
    // SUB.L 5ca4(A5),D2; SUB.L 5ca8(A5),D3; BRA.W 4cd86 / ADD.L.
    case 0x4cd72:case 0x4cd7e:
        if(!on34_pair(c,r.a[5],0x5ca4,value,other))return false;
        if(r.pc==0x4cd72U){r.d[2]-=value;r.d[3]-=other;}else {r.d[2]+=value;r.d[3]+=other;}r.pc=0x4cd86;return true;
    // MOVEQ #0,D7; MOVE.W 96(A0),D7; SWAP D7; SUB.L D7,D3; LEA 10d38e.l,A0; TST.B 549f(A5); BEQ.W 4cda8.
    case 0x4cd86:
        r.d[7]=0;if(!on34_get(c,r.a[0],0x96,2,value))return false;am_word(r.d[7],value);am_swap(r.d[7]);r.d[3]-=r.d[7];r.a[0]=0x10d38e;
        if(!on34_zero_b(c,r.a[5],0x549f,zero))return false;r.pc=zero?0x4cda8:0x4cd9e;return true;
    case 0x4cd9e:return am_call(c,0x4b8e8,0x4cda4);                          // JSR 4b8e8.l.
    case 0x4cda4:r.pc=0x4cdae;return true;                                   // BRA.W 4cdae.
    case 0x4cda8:return am_call(c,0x4bb22,0x4cdae);                          // JSR 4bb22.l.
    // MOVEM.L D0-D3,-(A7); LEA 538e(A5),A0; JSR 469d8.l.
    case 0x4cdae:
        for(unsigned int i=4;i>0;--i)if(!am_push(c,4,r.d[i-1U]))return false;r.a[0]=am_index(r.a[5],ON34_FRAME);return am_call(c,0x469d8,0x4cdbc);
    // MOVEA.L 5c8e(A5),A0; MOVE.W #10,D5; AND.W D5,D6; BEQ.W 4cdd8.
    case 0x4cdbc:
        if(!on34_get(c,r.a[5],0x5c8e,4,value))return false;r.a[0]=value;am_word(r.d[5],0x10);am_word(r.d[6],r.d[6]&0x10U);
        r.pc=on34_w(r.d[6])==0U?0x4cdd8:0x4cdca;return true;
    case 0x4cdca:if(!on34_zero_b(c,r.a[0],0x99,zero))return false;r.pc=zero?0x4cdd8:0x4cdd2;return true; // TST.B 99(A0); BEQ.W.
    case 0x4cdd2:if(!on34_put(c,r.a[5],0x549d,1,0xff))return false;r.pc=0x4cdd8;return true;           // MOVE.B #ff,549d(A5).
    // MOVE.W #1,D5; AND.W D6,D5; BEQ.W.
    case 0x4cdd8:r.pc=on34_mask_d5(r,1)==0U?0x4cde6:0x4cde2;return true;
    case 0x4cde2:case 0x4ce06:if(!on34_put(c,r.a[0],0x84,2,r.d[7]))return false;r.pc+=4U;return true; // MOVE.W D7,84(A0).
    // MOVEM.L (A7)+,D0-D3; LEA 538e(A5),A0; MOVE.W D6,-(A7); JSR 469d8.l.
    case 0x4cde6:
        for(unsigned int i=0;i<4;++i)if(!am_pop(c,4,r.d[i]))return false;r.a[0]=am_index(r.a[5],ON34_FRAME);
        if(!am_push(c,2,on34_w(r.d[6])))return false;return am_call(c,0x469d8,0x4cdf6);
    // MOVEA.L A0,A1; MOVEA.L 5c8e(A5),A0; MOVE.W #1,D5; AND.W D6,D5; BEQ.W 4ce0a.
    case 0x4cdf6:
        r.a[1]=r.a[0];if(!on34_get(c,r.a[5],0x5c8e,4,value))return false;r.a[0]=value;r.pc=on34_mask_d5(r,1)==0U?0x4ce0a:0x4ce06;return true;
    // OR.W (A7)+,D6; MOVE.W D6,7e(A0); SUBI.B #40,84(A0); TST.B 5cb4(A5); BEQ.W 4ce42.
    case 0x4ce0a:
        if(!am_pop(c,2,value))return false;am_word(r.d[6],r.d[6]|value);if(!on34_put(c,r.a[0],0x7e,2,r.d[6]))return false;
        if(!on34_get(c,r.a[0],0x84,1,value) || !on34_put(c,r.a[0],0x84,1,value-0x40U) || !on34_zero_b(c,r.a[5],0x5cb4,zero))return false;
        r.pc=zero?0x4ce42:0x4ce1e;return true;
    case 0x4ce1e:r.pc=(r.d[6]&4U)==0U?0x4ce42:0x4ce26;return true;          // BTST.B #2,D6; BEQ.W 4ce42.
    case 0x4ce26:if(!on34_speed(c,value))return false;r.pc=on34_minus(value)?0x4ce34:0x4ce2e;return true; // TST.L 64(A6); BLT.W.
    case 0x4ce2e:if(!on34_or_w(c,r.a[0],0x7c,0x8000))return false;r.pc=0x4ce34;return true;          // ORI.W #8000,7c(A0).
    case 0x4ce34:if(!on34_speed(c,value))return false;r.pc=(!on34_minus(value) && value!=0U)?0x4ce42:0x4ce3c;return true; // BGT.W.
    case 0x4ce3c:if(!on34_or_w(c,r.a[0],0x7a,0x8000))return false;r.pc=0x4ce42;return true;          // ORI.W #8000,7a(A0).
    // ANDI.W #fffb,D6; OR.W 7a(A0),D6; OR.W 7c(A0),D6; TST.B 5cb4(A5); BEQ.W 4ce82.
    case 0x4ce42:
        am_word(r.d[6],r.d[6]&0xfffbU);if(!on34_get(c,r.a[0],0x7a,2,value) || !on34_get(c,r.a[0],0x7c,2,other))return false;
        am_word(r.d[6],r.d[6]|value|other);if(!on34_zero_b(c,r.a[5],0x5cb4,zero))return false;r.pc=zero?0x4ce82:0x4ce56;return true;
    // TST.L 64(A6); BEQ.W 4ce82; BMI.W 4ce74.
    case 0x4ce56:if(!on34_speed(c,value))return false;r.pc=value==0U?0x4ce82:(on34_minus(value)?0x4ce74:0x4ce62);return true;
    // CMPI.B #20 / #e0,76(A0); BEQ.W.
    case 0x4ce62:if(!on34_get(c,r.a[0],0x76,1,value))return false;r.pc=value==0x20U?0x4ce70:0x4ce6c;return true;
    case 0x4ce74:if(!on34_get(c,r.a[0],0x76,1,value))return false;r.pc=value==0xe0U?0x4ce82:0x4ce7e;return true;
    case 0x4ce6c:case 0x4ce7e:am_word(r.d[6],r.d[6]&0xfffbU);r.pc+=4U;return true; // ANDI.W #fffb,D6.
    case 0x4ce70:r.pc=0x4ce82;return true;                                    // BRA.W 4ce82.
    case 0x4ce82:if(!on34_zero_b(c,r.a[0],0x9c,zero))return false;r.pc=zero?0x4ce8a:0x4ce98;return true; // TST.B 9c(A0); BNE.W.
    case 0x4ce8a:r.pc=on34_mask_d5(r,0xc000)==0U?0x4ce98:0x4ce94;return true;   // MOVE.W #c000,D5; AND.W D6,D5; BEQ.W.
    case 0x4ce94:am_word(r.d[6],r.d[6]|1U);r.pc=0x4ce98;return true;          // ORI.W #1,D6.
    // MOVE.W #1,D5; AND.W 7e(A0),D5; BNE.W 4cec2.
    case 0x4ce98:if(!on34_get(c,r.a[0],0x7e,2,value))return false;am_word(r.d[5],value&1U);r.pc=(value&1U)!=0U?0x4cec2:0x4cea4;return true;
    // MOVEA.L 5cb6(A5),A2; CMPA.W #ffff,A2; BEQ.W 4cec2.
    case 0x4cea4:if(!on34_get(c,r.a[5],0x5cb6,4,value))return false;r.a[2]=value;r.pc=value==0xffffffffU?0x4cec2:0x4ceb0;return true;
    // ADD.L 14(A1),D0; ADD.L 18(A1),D1; SUB.L 14(A2),D0; SUB.L 18(A2),D1; MOVEA.L A2,A1.
    case 0x4ceb0:
        if(!on34_pair(c,r.a[1],0x14,value,other))return false;r.d[0]+=value;r.d[1]+=other;
        if(!on34_pair(c,r.a[2],0x14,value,other))return false;r.d[0]-=value;r.d[1]-=other;r.a[1]=r.a[2];r.pc=0x4cec2;return true;
    // D2/D3 from 36/3a(A6) and the 538e / A1 frames; MOVEM.L D0-D3/A1,2e(A6); TST.B 5cb4(A5); BNE.W 4cf04.
    case 0x4cec2:{
        std::uint32_t f[4]={0,0,0,0},g[4]={0,0,0,0};
        if(!on34_pair(c,r.a[6],0x36,value,other))return false;r.a[2]=am_index(r.a[5],ON34_FRAME);
        // Read order of the original: 14 1c 18 20 (A2 = 538e frame), then 14 1c 18 20 (A1).
        static const unsigned int order[4]={0,2,1,3};
        for(unsigned int i=0;i<4;++i)if(!on34_get(c,r.a[2],0x14U+4U*order[i],4,f[order[i]]))return false;
        for(unsigned int i=0;i<4;++i)if(!on34_get(c,r.a[1],0x14U+4U*order[i],4,g[order[i]]))return false;
        r.d[2]=value+f[0]-f[2]-g[0]+g[2];r.d[3]=other+f[1]-f[3]-g[1]+g[3];
        const std::uint32_t v[5]={r.d[0],r.d[1],r.d[2],r.d[3],r.a[1]};
        for(unsigned int i=0;i<5;++i)if(!on34_put(c,r.a[6],0x2eU+4U*i,4,v[i]))return false;
        if(!on34_zero_b(c,r.a[5],0x5cb4,zero))return false;r.pc=zero?0x4cefc:0x4cf04;return true;}
    case 0x4cefc:case 0x4cf0e:if(!on34_put(c,r.a[0],0x96,2,0))return false;r.pc=0x4cf30;return true; // CLR.W 96(A0); BRA.W 4cf30.
    case 0x4cf04:r.pc=on34_mask_d5(r,1)==0U?0x4cf16:0x4cf0e;return true;      // MOVE.W #1,D5; AND.W D6,D5; BEQ.W 4cf16.
    case 0x4cf16:if(!on34_zero_b(c,r.a[0],0x9c,zero))return false;r.pc=zero?0x4cf1e:0x4cf30;return true; // TST.B 9c(A0); BNE.W.
    case 0x4cf1e:if(!on34_get(c,r.a[0],0x96,2,value))return false;r.pc=value>=4U?0x4cf30:0x4cf28;return true; // CMPI.W #4; BCC.W.
    case 0x4cf28:if(!on34_add_w(c,r.a[0],0x96,1))return false;am_word(r.d[6],r.d[6]|1U);r.pc=0x4cf30;return true; // ADDQ.W #1; ORI.W #1,D6.
    case 0x4cf30:return am_call(c,0x4bf16,0x4cf34);                          // BSR.W 4bf16.
    // MOVEA.L 5c8e(A5),A0; MOVE.W 5c9a(A5),D0; ADD.W D0,78(A0); BSR.W 4c660.
    case 0x4cf34:
        if(!on34_get(c,r.a[5],0x5c8e,4,value))return false;r.a[0]=value;if(!on34_get(c,r.a[5],0x5c9a,2,value))return false;am_word(r.d[0],value);
        if(!on34_add_w(c,r.a[0],0x78,value))return false;return am_call(c,0x4c660,0x4cf44);
    // MOVE.B 78(A0),D0; ADD.B D0,76(A0); MOVE.W 76(A0),D0; RTS.
    case 0x4cf44:
        if(!on34_get(c,r.a[0],0x78,1,value))return false;am_byte(r.d[0],value);if(!on34_get(c,r.a[0],0x76,1,other) || !on34_put(c,r.a[0],0x76,1,other+value))return false;
        if(!on34_get(c,r.a[0],0x76,2,value))return false;am_word(r.d[0],value);return am_return(c);
    default:return am_error(c,"unsupported animation objects n34 PC");
    }
}
}
