#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t WALK_SIGN=0x80000000U;
// A5-relative fields (A5=108000 -> 10d3xx): cursor LONG, base X/Y WORDs, current/proposed X/Y LONGs.
const std::uint32_t WALK_CURSOR=0x53b4,WALK_BASE_X=0x53b8,WALK_BASE_Y=0x53ba;
const std::uint32_t WALK_CUR_X=0x53bc,WALK_CUR_Y=0x53c0,WALK_NEW_X=0x53c4,WALK_NEW_Y=0x53c8;
// BCC/BCS right after a call (or after MOVEM.L (A7)+, which keeps the flags): consumes the C returned
// by 18c06 (ORI/ANDI CCR), 19710/1971c (TST.W Clear or ORI Set) or 192c4 (AND.W Clear or ORI Set).
bool walk_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"motion walk caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// Two's-complement LONG value for SLT/SGT after CMP.L (N xor V is the exact signed comparison).
std::int64_t walk_signed_long(std::uint32_t value) {
    const std::int64_t low=static_cast<std::int64_t>(value&0x7fffffffU);
    return (value&WALK_SIGN)?low-static_cast<std::int64_t>(0x80000000LL):low;
}
std::int32_t walk_signed_word(std::uint32_t value) {
    const std::int32_t low=static_cast<std::int32_t>(value&0x7fffU);
    return (value&0x8000U)?low-0x8000:low;
}
// ASR.W/ASR.L #1..3: sign bits shifted in.
std::uint32_t walk_asr_word(std::uint32_t value,unsigned int count) {
    const std::uint32_t word=value&65535U;
    const std::uint32_t fill=(word&0x8000U)?((65535U<<(16U-count))&65535U):0U;
    return (word>>count)|fill;
}
std::uint32_t walk_asr_long(std::uint32_t value,unsigned int count) {
    const std::uint32_t fill=(value&WALK_SIGN)?(0xffffffffU<<(32U-count)):0U;
    return (value>>count)|fill;
}
// Shift code shared by the handler tables: 0 none, -1 LSL #1, 1..3 ASR #n.
void walk_shift_word(std::uint32_t& reg,int shift) {
    if(shift<0)am_word(reg,(reg&65535U)<<1);
    else if(shift>0)am_word(reg,walk_asr_word(reg,static_cast<unsigned int>(shift)));
}
void walk_shift_long(std::uint32_t& reg,int shift) {
    if(shift<0)reg<<=1;
    else if(shift>0)reg=walk_asr_long(reg,static_cast<unsigned int>(shift));
}
// EXT.W Dn: low BYTE sign-extended into the low WORD, upper WORD kept.
void walk_ext_word(std::uint32_t& reg) {
    am_word(reg,(reg&0x80U)?(0xff00U|(reg&255U)):(reg&255U));
}
bool walk_field(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool walk_store(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// WORD at d16(A1) of the current 10-byte record (live bus read; odd A1 is a checked error).
bool walk_record(AnimationMachineContext& c,std::uint32_t offset,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[1],offset),2,value);
}
// ADD.W Dn,d16(A5) / SUB.W Dn,d16(A5): WORD read-modify-write with wrap.
bool walk_add_field(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t reg) {
    std::uint32_t value=0;if(!walk_field(c,displacement,2,value))return false;
    return walk_store(c,displacement,2,(value+reg)&65535U);
}
bool walk_sub_field(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t reg) {
    std::uint32_t value=0;if(!walk_field(c,displacement,2,value))return false;
    return walk_store(c,displacement,2,(value-reg)&65535U);
}
// MOVE.W 2(A1),D4; JMP table(PC,D4.W): no range check, the computed PC is followed as is.
bool walk_dispatch(AnimationMachineContext& c,std::uint32_t table) {
    std::uint32_t value=0;if(!walk_record(c,2,value))return false;
    am_word(c.s.d[4],value);c.s.pc=am_index(table,c.s.d[4]);return true;
}
// MOVEQ #0,Dn; MOVE.W d16(A1),Dn; SWAP Dn [; SUBQ.L #1,Dn]: record time as a 16.16 LONG.
bool walk_time(AnimationMachineContext& c,std::uint32_t offset,bool minus_one) {
    std::uint32_t value=0;if(!walk_record(c,offset,value))return false;
    c.s.d[7]=0;am_word(c.s.d[7],value);am_swap(c.s.d[7]);if(minus_one)c.s.d[7]-=1U;return true;
}
// MOVE.L 53bc/53c0/53c4/53c8(A5),D0-D3; MOVEM.L D6-D7,-(A7) (D7 at A7-4, D6 at A7-8); BSR 192c4.
bool walk_pair(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!walk_field(c,WALK_CUR_X,4,value))return false;r.d[0]=value;
    if(!walk_field(c,WALK_CUR_Y,4,value))return false;r.d[1]=value;
    if(!walk_field(c,WALK_NEW_X,4,value))return false;r.d[2]=value;
    if(!walk_field(c,WALK_NEW_Y,4,value))return false;r.d[3]=value;
    if(!am_push(c,4,r.d[7]) || !am_push(c,4,r.d[6]))return false;
    return am_call(c,0x192c4,return_pc);
}
// MOVEM.L (A7)+,D6-D7 (flags kept); BCS: C returned by 192c4.
bool walk_unpair(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_pop(c,4,value))return false;r.d[6]=value;
    if(!am_pop(c,4,value))return false;r.d[7]=value;
    return walk_carry(c,clear_pc,set_pc);
}
// 1935c (base Y, D1/D3) and 19564 (base X, D0/D2): MOVEQ #0,D4; MOVEQ #0,D5; MOVE.W base(A5),D4;
// MOVE.W 4(A1),D5; ADD.W D4,D5; CMP.W D5,D4; BLE (signed WORD) to the test, else EXG.L D4,D5 first.
bool walk_band(AnimationMachineContext& c,std::uint32_t base,std::uint32_t le_pc,std::uint32_t swap_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.d[4]=0;r.d[5]=0;
    if(!walk_field(c,base,2,value))return false;am_word(r.d[4],value);
    if(!walk_record(c,4,value))return false;am_word(r.d[5],value);
    am_word(r.d[5],r.d[5]+r.d[4]);
    r.pc=walk_signed_word(r.d[4])<=walk_signed_word(r.d[5])?le_pc:swap_pc;return true;
}
// 19372/1957a: SUBQ.W #1,D4; ADDQ.W #1,D5 (WORD wrap); SWAP D4; CMP.L D4,a; SLT.B D6; CMP.L D4,b; SLT.B D7;
// EXT.W D6; EXT.W D7; SWAP D5; CMP.L D5,a; SGT.B D6; CMP.L D5,b; SGT.B D7; AND.W D6,D7 (C=0); BNE rts.
bool walk_band_test(AnimationMachineContext& c,std::uint32_t a,std::uint32_t b,std::uint32_t ne_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;
    am_word(r.d[4],r.d[4]-1U);am_word(r.d[5],r.d[5]+1U);am_swap(r.d[4]);
    am_byte(r.d[6],walk_signed_long(a)<walk_signed_long(r.d[4])?0xffU:0U);
    am_byte(r.d[7],walk_signed_long(b)<walk_signed_long(r.d[4])?0xffU:0U);
    walk_ext_word(r.d[6]);walk_ext_word(r.d[7]);am_swap(r.d[5]);
    am_byte(r.d[6],walk_signed_long(a)>walk_signed_long(r.d[5])?0xffU:0U);
    am_byte(r.d[7],walk_signed_long(b)>walk_signed_long(r.d[5])?0xffU:0U);
    am_word(r.d[7],r.d[7]&r.d[6]);
    r.carry=AnimationCarryClear;r.pc=(r.d[7]&65535U)?ne_pc:set_pc;return true;
}
// 18f92/18fb2: MOVE.L Dn,D7; SWAP D7; SUB.W base(A5),D7; ADD.W (A1),D7; SWAP D7; RTS.
bool walk_time_forward(AnimationMachineContext& c,std::uint32_t source,std::uint32_t base) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.d[7]=source;am_swap(r.d[7]);
    if(!walk_field(c,base,2,value))return false;am_word(r.d[7],r.d[7]-value);
    if(!walk_record(c,0,value))return false;am_word(r.d[7],r.d[7]+value);
    am_swap(r.d[7]);return am_return(c);
}
// 18fa0/18fc0: MOVEQ #0,D7; MOVE.W base(A5),D7; SWAP D7; SUB.L Dn,D7 (LONG borrow); SWAP D7;
// ADD.W (A1),D7; SWAP D7; RTS.
bool walk_time_reverse(AnimationMachineContext& c,std::uint32_t source,std::uint32_t base) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.d[7]=0;if(!walk_field(c,base,2,value))return false;am_word(r.d[7],value);
    am_swap(r.d[7]);r.d[7]-=source;am_swap(r.d[7]);
    if(!walk_record(c,0,value))return false;am_word(r.d[7],r.d[7]+value);
    am_swap(r.d[7]);return am_return(c);
}
// Indexed JMP tables: 36 BRA.W slots (4 bytes each) after each dispatcher (original BRA.W targets).
struct WalkSlots {std::uint32_t table;std::uint32_t target[36];};
const WalkSlots WALK_SLOTS[5]={
    {0x18c0e,{0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,
              0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18c9e,0x18ca4,0x18ca4,
              0x18ca4,0x18ca4,0x18ca4,0x18ca4,0x18ca4,0x18ca4,0x18ca4,0x18ca4,0x18ca4,0x18ca4,0x18ca4,0x18ca4}},
    {0x18cb2,{0x18d42,0x18d4e,0x18d58,0x18d64,0x18d70,0x18d7c,0x18d86,0x18d94,0x18da2,0x18db0,0x18dbc,0x18dca,
              0x18dd8,0x18de4,0x18df2,0x18e00,0x18e0e,0x18e18,0x18e24,0x18e30,0x18e3c,0x18e46,0x18e52,0x18e5c,
              0x18e68,0x18e74,0x18e7e,0x18e8c,0x18e9a,0x18ea6,0x18eb2,0x18ec0,0x18ece,0x18ed8,0x18ee4,0x18ef0}},
    {0x18f02,{0x18f92,0x18f92,0x18f92,0x18f92,0x18f92,0x18f92,0x18f92,0x18f92,0x18f92,0x18f92,0x18f92,0x18fa0,
              0x18fa0,0x18fa0,0x18fa0,0x18fa0,0x18fa0,0x18fa0,0x18fa0,0x18fa0,0x18fa0,0x18fa0,0x18fb2,0x18fb2,
              0x18fb2,0x18fb2,0x18fb2,0x18fb2,0x18fb2,0x18fc0,0x18fc0,0x18fc0,0x18fc0,0x18fc0,0x18fc0,0x18fc0}},
    {0x18fda,{0x1906a,0x1907a,0x19088,0x19098,0x190a8,0x190b8,0x190c6,0x190d8,0x190ea,0x190fc,0x1910c,0x1911e,
              0x19130,0x19140,0x19152,0x19164,0x19176,0x19184,0x19194,0x191a4,0x191b4,0x191c2,0x191d2,0x191e0,
              0x191f0,0x19200,0x1920e,0x19220,0x19232,0x19242,0x19252,0x19264,0x19276,0x19284,0x19294,0x192a4}},
    {0x192cc,{0x1939a,0x193b0,0x193c2,0x193d8,0x193f0,0x1935c,0x19408,0x19420,0x19438,0x19450,0x19464,0x1947c,
              0x19494,0x194a8,0x194c0,0x194d8,0x1935c,0x194f0,0x19508,0x19520,0x19538,0x1954c,0x195a2,0x195b4,
              0x195ca,0x19564,0x195e0,0x195f8,0x19610,0x19624,0x19638,0x19650,0x19564,0x19668,0x19680,0x19698}}};
// 18caa (WORD) and 18fd2 (LONG) handlers. Primary axis D0 (X) or D1 (Y): forward n-s / t-(s<<16), or
// reverse s-n / (s<<16)-t. Secondary: MOVEQ #0 (whole LONG) or a copy, then NEG, then the shift.
enum WalkSecondary {WALK_COPY=0,WALK_ZERO=1};
struct WalkDelta {std::uint32_t pc;unsigned int y;unsigned int reverse;unsigned int secondary;unsigned int neg;int shift;};
const WalkDelta WALK_WORD[36]={
    {0x18d42,0,0,WALK_COPY,0,-1},{0x18d4e,0,0,WALK_COPY,0,0},{0x18d58,0,0,WALK_COPY,0,1},{0x18d64,0,0,WALK_COPY,0,2},
    {0x18d70,0,0,WALK_COPY,0,3},{0x18d7c,0,0,WALK_ZERO,0,0},{0x18d86,0,0,WALK_COPY,1,3},{0x18d94,0,0,WALK_COPY,1,2},
    {0x18da2,0,0,WALK_COPY,1,1},{0x18db0,0,0,WALK_COPY,1,0},{0x18dbc,0,0,WALK_COPY,1,-1},{0x18dca,0,1,WALK_COPY,1,-1},
    {0x18dd8,0,1,WALK_COPY,1,0},{0x18de4,0,1,WALK_COPY,1,1},{0x18df2,0,1,WALK_COPY,1,2},{0x18e00,0,1,WALK_COPY,1,3},
    {0x18e0e,0,1,WALK_ZERO,0,0},{0x18e18,0,1,WALK_COPY,0,3},{0x18e24,0,1,WALK_COPY,0,2},{0x18e30,0,1,WALK_COPY,0,1},
    {0x18e3c,0,1,WALK_COPY,0,0},{0x18e46,0,1,WALK_COPY,0,-1},{0x18e52,1,0,WALK_COPY,0,0},{0x18e5c,1,0,WALK_COPY,0,1},
    {0x18e68,1,0,WALK_COPY,0,2},{0x18e74,1,0,WALK_ZERO,0,0},{0x18e7e,1,0,WALK_COPY,1,2},{0x18e8c,1,0,WALK_COPY,1,1},
    {0x18e9a,1,0,WALK_COPY,1,0},{0x18ea6,1,1,WALK_COPY,1,0},{0x18eb2,1,1,WALK_COPY,1,1},{0x18ec0,1,1,WALK_COPY,1,2},
    {0x18ece,1,1,WALK_ZERO,0,0},{0x18ed8,1,1,WALK_COPY,0,2},{0x18ee4,1,1,WALK_COPY,0,1},{0x18ef0,1,1,WALK_COPY,0,0}};
const WalkDelta WALK_LONG[36]={
    {0x1906a,0,0,WALK_COPY,0,-1},{0x1907a,0,0,WALK_COPY,0,0},{0x19088,0,0,WALK_COPY,0,1},{0x19098,0,0,WALK_COPY,0,2},
    {0x190a8,0,0,WALK_COPY,0,3},{0x190b8,0,0,WALK_ZERO,0,0},{0x190c6,0,0,WALK_COPY,1,3},{0x190d8,0,0,WALK_COPY,1,2},
    {0x190ea,0,0,WALK_COPY,1,1},{0x190fc,0,0,WALK_COPY,1,0},{0x1910c,0,0,WALK_COPY,1,-1},{0x1911e,0,1,WALK_COPY,1,-1},
    {0x19130,0,1,WALK_COPY,1,0},{0x19140,0,1,WALK_COPY,1,1},{0x19152,0,1,WALK_COPY,1,2},{0x19164,0,1,WALK_COPY,1,3},
    {0x19176,0,1,WALK_ZERO,0,0},{0x19184,0,1,WALK_COPY,0,3},{0x19194,0,1,WALK_COPY,0,2},{0x191a4,0,1,WALK_COPY,0,1},
    {0x191b4,0,1,WALK_COPY,0,0},{0x191c2,0,1,WALK_COPY,0,-1},{0x191d2,1,0,WALK_COPY,0,0},{0x191e0,1,0,WALK_COPY,0,1},
    {0x191f0,1,0,WALK_COPY,0,2},{0x19200,1,0,WALK_ZERO,0,0},{0x1920e,1,0,WALK_COPY,1,2},{0x19220,1,0,WALK_COPY,1,1},
    {0x19232,1,0,WALK_COPY,1,0},{0x19242,1,1,WALK_COPY,1,0},{0x19252,1,1,WALK_COPY,1,1},{0x19264,1,1,WALK_COPY,1,2},
    {0x19276,1,1,WALK_ZERO,0,0},{0x19284,1,1,WALK_COPY,0,2},{0x19294,1,1,WALK_COPY,0,1},{0x192a4,1,1,WALK_COPY,0,0}};
// 192c4 transforms (32; slots 5/16/25/32 branch straight to 1935c/19564): base X with D0/D2 into the D1/D3
// band test at 1935c, or base Y with D1/D3 into the D0/D2 test at 19564. 'add' X: D1+=D0; D3+=D0 (original
// asymmetry, d280 d680); Y: D0+=D1; D2+=D3. Otherwise X: D1-=D0; D3-=D2; Y: D0-=D1; D2-=D3.
struct WalkPair {std::uint32_t pc;unsigned int y;int shift;unsigned int add;};
const WalkPair WALK_PAIR[32]={
    {0x1939a,0,-1,0},{0x193b0,0,0,0},{0x193c2,0,1,0},{0x193d8,0,2,0},{0x193f0,0,3,0},{0x19408,0,3,1},{0x19420,0,2,1},
    {0x19438,0,1,1},{0x19450,0,0,1},{0x19464,0,-1,1},{0x1947c,0,-1,0},{0x19494,0,0,0},{0x194a8,0,1,0},{0x194c0,0,2,0},
    {0x194d8,0,3,0},{0x194f0,0,3,1},{0x19508,0,2,1},{0x19520,0,1,1},{0x19538,0,0,1},{0x1954c,0,-1,1},{0x195a2,1,0,0},
    {0x195b4,1,1,0},{0x195ca,1,2,0},{0x195e0,1,2,1},{0x195f8,1,1,1},{0x19610,1,0,1},{0x19624,1,0,0},{0x19638,1,1,0},
    {0x19650,1,2,0},{0x19668,1,2,1},{0x19680,1,1,1},{0x19698,1,0,1}};
// 18caa handler: MOVE.W 10(A1),Dp; SUB.W (A1),Dp (or (A1) minus 10(A1)); secondary WORD ops; RTS.
bool walk_word_delta(AnimationMachineContext& c,const WalkDelta& h) {
    AnimationMachineState& r=c.s;std::uint32_t first=0,second=0;
    std::uint32_t& p=h.y?r.d[1]:r.d[0];std::uint32_t& q=h.y?r.d[0]:r.d[1];
    if(!walk_record(c,h.reverse?0U:10U,first) || !walk_record(c,h.reverse?10U:0U,second))return false;
    am_word(p,first);am_word(p,p-second);
    if(h.secondary==WALK_ZERO)q=0;
    else {am_word(q,p);if(h.neg)am_word(q,0U-q);walk_shift_word(q,h.shift);}
    return am_return(c);
}
// 18fd2 handler: forward MOVE.L D7,Dp; SWAP; SUB.W (A1); SWAP (WORD wrap of the integer part), or reverse
// MOVEQ #0,Dp; MOVE.W (A1),Dp; SWAP; SUB.L D7,Dp (LONG borrow); secondary LONG ops; BRA 192b2.
bool walk_long_delta(AnimationMachineContext& c,const WalkDelta& h) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    std::uint32_t& p=h.y?r.d[1]:r.d[0];std::uint32_t& q=h.y?r.d[0]:r.d[1];
    if(!walk_record(c,0,value))return false;
    if(h.reverse) {p=0;am_word(p,value);am_swap(p);p-=r.d[7];}
    else {p=r.d[7];am_swap(p);am_word(p,p-value);am_swap(p);}
    if(h.secondary==WALK_ZERO)q=0;
    else {q=p;if(h.neg)q=0U-q;walk_shift_long(q,h.shift);}
    r.pc=0x192b2;return true;
}
// 192c4 transform: MOVEQ #0,D4; MOVE.W base(A5),D4; SWAP D4; SUB.L D4 from both primary LONGs; shift both;
// combine into the other axis; BRA to the band test.
bool walk_pair_transform(AnimationMachineContext& c,const WalkPair& h) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.d[4]=0;if(!walk_field(c,h.y?WALK_BASE_Y:WALK_BASE_X,2,value))return false;am_word(r.d[4],value);am_swap(r.d[4]);
    if(!h.y) {
        r.d[0]-=r.d[4];r.d[2]-=r.d[4];walk_shift_long(r.d[0],h.shift);walk_shift_long(r.d[2],h.shift);
        if(h.add) {r.d[1]+=r.d[0];r.d[3]+=r.d[0];} else {r.d[1]-=r.d[0];r.d[3]-=r.d[2];}
        r.pc=0x1935c;
    } else {
        r.d[1]-=r.d[4];r.d[3]-=r.d[4];walk_shift_long(r.d[1],h.shift);walk_shift_long(r.d[3],h.shift);
        if(h.add) {r.d[0]+=r.d[1];r.d[2]+=r.d[3];} else {r.d[0]-=r.d[1];r.d[2]-=r.d[3];}
        r.pc=0x19564;
    }
    return true;
}
// Slot BRA.W blocks and the regular handler blocks; false when pc is none of them.
bool walk_table_block(AnimationMachineContext& c,bool& ok) {
    const std::uint32_t pc=c.s.pc;
    for(unsigned int t=0;t<5;++t) {
        const std::uint32_t table=WALK_SLOTS[t].table;
        if(pc>=table && pc<table+144U && !((pc-table)&3U)) {c.s.pc=WALK_SLOTS[t].target[(pc-table)/4U];ok=true;return true;}
    }
    for(unsigned int i=0;i<36;++i) {
        if(WALK_WORD[i].pc==pc) {ok=walk_word_delta(c,WALK_WORD[i]);return true;}
        if(WALK_LONG[i].pc==pc) {ok=walk_long_delta(c,WALK_LONG[i]);return true;}
    }
    for(unsigned int i=0;i<32;++i)if(WALK_PAIR[i].pc==pc) {ok=walk_pair_transform(c,WALK_PAIR[i]);return true;}
    return false;
}
}
// 480bc frame helper U3: motion walk 19812 (re-post loop), 19844 (pair walk), 19910 (segment + width) and
// their callees 1972a (segment select), 196ac/196de (forward/backward step), 19710/1971c (first/last
// record C), and the type dispatchers 18c06 (major axis C), 18caa (WORD deltas), 18efa (time), 18fd2
// (position, tail 192b2) and 192c4 (pair transform, band tests 1935c/19564). All 36 type slots; types
// outside the tables follow the computed PC. No calls leave U3. All A5-relative operands use the live A5.
bool animation_motion_walk_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // Dispatchers: MOVE.W 2(A1),D4; JMP table(PC,D4.W).
    case 0x18c06:return walk_dispatch(c,0x18c0e);
    case 0x18caa:return walk_dispatch(c,0x18cb2);
    case 0x18efa:return walk_dispatch(c,0x18f02);
    case 0x18fd2:return walk_dispatch(c,0x18fda);
    case 0x192c4:return walk_dispatch(c,0x192cc);
    case 0x18c9e:r.carry=AnimationCarrySet;return am_return(c);   // ORI #1,CCR; RTS (type < 58)
    case 0x18ca4:r.carry=AnimationCarryClear;return am_return(c); // ANDI #fe,CCR; RTS
    case 0x18f92:return walk_time_forward(c,r.d[0],WALK_BASE_X);
    case 0x18fa0:return walk_time_reverse(c,r.d[0],WALK_BASE_X);
    case 0x18fb2:return walk_time_forward(c,r.d[1],WALK_BASE_Y);
    case 0x18fc0:return walk_time_reverse(c,r.d[1],WALK_BASE_Y);
    // 192b2: SWAP D0; SWAP D1; ADD.W 53b8(A5),D0; ADD.W 53ba(A5),D1; SWAP D0; SWAP D1; RTS.
    case 0x192b2:
        am_swap(r.d[0]);am_swap(r.d[1]);
        if(!walk_field(c,WALK_BASE_X,2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!walk_field(c,WALK_BASE_Y,2,value))return false;am_word(r.d[1],r.d[1]+value);
        am_swap(r.d[0]);am_swap(r.d[1]);return am_return(c);
    // Band tests: 1935c (Y band, D1/D3) and 19564 (X band, D0/D2); C=1 unless both are below or both above.
    case 0x1935c:return walk_band(c,WALK_BASE_Y,0x19372,0x19370);
    case 0x19564:return walk_band(c,WALK_BASE_X,0x1957a,0x19578);
    case 0x19370:case 0x19578:value=r.d[4];r.d[4]=r.d[5];r.d[5]=value;r.pc+=2U;return true; // EXG.L D4,D5
    case 0x19372:return walk_band_test(c,r.d[1],r.d[3],0x19398,0x19394);
    case 0x1957a:return walk_band_test(c,r.d[0],r.d[2],0x195a0,0x1959c);
    case 0x19394:case 0x1959c:case 0x19716:case 0x19724:r.carry=AnimationCarrySet;r.pc+=4U;return true; // ORI #1,CCR
    case 0x19398:case 0x195a0:case 0x1971a:case 0x19728:case 0x19830:return am_return(c);

    // 196ac forward step: BSR 18caa; ADD.W D0,53b8(A5); ADD.W D1,53ba(A5); LEA 10(A1),A1; BSR 18c06.
    case 0x196ac:return am_call(c,0x18caa,0x196b0);
    case 0x196b0:
        if(!walk_add_field(c,WALK_BASE_X,r.d[0]&65535U) || !walk_add_field(c,WALK_BASE_Y,r.d[1]&65535U))return false;
        r.a[1]=am_index(r.a[1],10);return am_call(c,0x18c06,0x196c0);
    case 0x196c0:return walk_carry(c,0x196d0,0x196c4); // BCC 196d0
    // MOVE.W 6(A1),D0; ADD.W D0 to the major axis base (Y when C=1, X when C=0).
    case 0x196c4:case 0x196d0:
        if(!walk_record(c,6,value))return false;am_word(r.d[0],value);
        if(!walk_add_field(c,r.pc==0x196c4?WALK_BASE_Y:WALK_BASE_X,r.d[0]&65535U))return false;
        r.pc=0x196d8;return true;
    case 0x196d8:r.carry=AnimationCarrySet;return am_return(c); // ORI #1,CCR; RTS (no consumer)
    // 196de backward step: BSR 18c06 (current record).
    case 0x196de:return am_call(c,0x18c06,0x196e2);
    case 0x196e2:return walk_carry(c,0x196f2,0x196e6); // BCC 196f2
    case 0x196e6:case 0x196f2:
        if(!walk_record(c,6,value))return false;am_word(r.d[0],value);
        if(!walk_sub_field(c,r.pc==0x196e6?WALK_BASE_Y:WALK_BASE_X,r.d[0]&65535U))return false;
        r.pc=0x196fa;return true;
    case 0x196fa:r.a[1]=am_index(r.a[1],0xfff6);return am_call(c,0x18caa,0x19702); // LEA -10(A1),A1; BSR 18caa
    // SUB.W D0,53b8(A5); SUB.W D1,53ba(A5); MOVE.L A1,53b4(A5); RTS.
    case 0x19702:
        if(!walk_sub_field(c,WALK_BASE_X,r.d[0]&65535U) || !walk_sub_field(c,WALK_BASE_Y,r.d[1]&65535U) ||
           !walk_store(c,WALK_CURSOR,4,r.a[1]))return false;
        return am_return(c);
    // 19710: TST.W (A1) (C=0); BNE 1971a; else ORI. 1971c: TST.W 12(A1) (C=0); BPL 19728; else ORI.
    case 0x19710:if(!walk_record(c,0,value))return false;r.carry=AnimationCarryClear;r.pc=value?0x1971a:0x19716;return true;
    case 0x1971c:if(!walk_record(c,12,value))return false;r.carry=AnimationCarryClear;r.pc=(value&0x8000U)?0x19724:0x19728;return true;

    // 1972a segment select: SWAP D7; CMP.W (A1),D7; BPL 19744 (N only).
    case 0x1972a:am_swap(r.d[7]);r.pc=0x1972c;return true;
    case 0x1972c:if(!walk_record(c,0,value))return false;r.pc=((r.d[7]-value)&0x8000U)?0x19732:0x19744;return true;
    case 0x19732:return am_call(c,0x19710,0x19734);
    case 0x19734:return walk_carry(c,0x19738,0x1973c); // BCS 1973c (first record)
    case 0x19738:return am_call(c,0x196de,0x1973a);
    case 0x1973a:case 0x19756:r.pc=0x1972c;return true;
    case 0x1973c:if(!walk_time(c,0,false))return false;return am_return(c);
    // CMP.W 10(A1),D7; BMI 19764 (N only).
    case 0x19744:if(!walk_record(c,10,value))return false;r.pc=((r.d[7]-value)&0x8000U)?0x19764:0x1974c;return true;
    case 0x1974c:return am_call(c,0x1971c,0x1974e);
    case 0x1974e:return walk_carry(c,0x19752,0x19758); // BCS 19758 (last record)
    case 0x19752:return am_call(c,0x196ac,0x19756);
    case 0x19758:if(!walk_time(c,10,true))return false;return am_return(c);
    case 0x19764:am_swap(r.d[7]);return am_return(c);

    // 19812: MOVE.L D0,-(A7); MOVE.L D1,-(A7); BSR 18efa; BSR 1972a; MOVE.L (A7)+,D1; MOVE.L (A7)+,D0;
    // CMPA.L 53b4(A5),A1; BEQ 19830 / MOVE.L A1,53b4(A5); BRA 19812 (no iteration limit in the original).
    case 0x19812:if(!am_push(c,4,r.d[0]) || !am_push(c,4,r.d[1]))return false;return am_call(c,0x18efa,0x1981a);
    case 0x1981a:return am_call(c,0x1972a,0x1981e);
    case 0x1981e:
        if(!am_pop(c,4,value))return false;r.d[1]=value;
        if(!am_pop(c,4,value))return false;r.d[0]=value;
        if(!walk_field(c,WALK_CURSOR,4,value))return false;r.pc=r.a[1]==value?0x19830:0x1982a;return true;
    case 0x1982a:if(!walk_store(c,WALK_CURSOR,4,r.a[1]))return false;r.pc=0x19812;return true;

    // 19844: D0/D1 = current X/Y LONGs; BSR 18efa; D6=D7; D0/D1 = proposed X/Y; BSR 18efa.
    case 0x19844:
        if(!walk_field(c,WALK_CUR_X,4,value))return false;r.d[0]=value;
        if(!walk_field(c,WALK_CUR_Y,4,value))return false;r.d[1]=value;
        return am_call(c,0x18efa,0x19850);
    case 0x19850:
        r.d[6]=r.d[7];
        if(!walk_field(c,WALK_NEW_X,4,value))return false;r.d[0]=value;
        if(!walk_field(c,WALK_NEW_Y,4,value))return false;r.d[1]=value;
        return am_call(c,0x18efa,0x1985e);
    // MOVE.L D7,D5; SWAP D5; CMP.L D6,D7; BMI 198ae (N only).
    case 0x1985e:r.d[5]=r.d[7];am_swap(r.d[5]);r.pc=((r.d[7]-r.d[6])&WALK_SIGN)?0x198ae:0x19868;return true;
    // Forward: CMP.W 10(A1),D5; BMI 198a8 (N only).
    case 0x19868:if(!walk_record(c,10,value))return false;r.pc=((r.d[5]-value)&0x8000U)?0x198a8:0x19870;return true;
    case 0x19870:return am_call(c,0x1971c,0x19874);
    case 0x19874:return walk_carry(c,0x19878,0x1989e); // BCS 1989e
    case 0x19878:return am_call(c,0x196ac,0x1987c);
    case 0x1987c:return walk_pair(c,0x19894);
    case 0x19894:return walk_unpair(c,0x1989a,0x1985e); // BCS 1985e (repeat)
    case 0x1989a:return am_call(c,0x196de,0x1989e);
    case 0x1989e:if(!walk_time(c,10,true))return false;r.pc=0x198a8;return true;
    case 0x198a8:case 0x198e8:if(!walk_store(c,WALK_CURSOR,4,r.a[1]))return false;return am_return(c);
    // Backward: CMP.W (A1),D5; BPL 198e8 (N only).
    case 0x198ae:if(!walk_record(c,0,value))return false;r.pc=((r.d[5]-value)&0x8000U)?0x198b4:0x198e8;return true;
    case 0x198b4:return am_call(c,0x19710,0x198b8);
    case 0x198b8:return walk_carry(c,0x198bc,0x198e2); // BCS 198e2
    case 0x198bc:return am_call(c,0x196de,0x198c0);
    case 0x198c0:return walk_pair(c,0x198d8);
    case 0x198d8:return walk_unpair(c,0x198de,0x1985e);
    case 0x198de:return am_call(c,0x196ac,0x198e2);
    case 0x198e2:if(!walk_time(c,0,false))return false;r.pc=0x198e8;return true;

    // 19910: BSR 1972a; MOVE.L A1,53b4(A5); BSR 18fd2; MOVEQ #0,D2; MOVEQ #0,D3; BSR 18c06; BCC 19930.
    case 0x19910:return am_call(c,0x1972a,0x19914);
    case 0x19914:if(!walk_store(c,WALK_CURSOR,4,r.a[1]))return false;return am_call(c,0x18fd2,0x1991c);
    case 0x1991c:r.d[2]=0;r.d[3]=0;return am_call(c,0x18c06,0x19924);
    case 0x19924:return walk_carry(c,0x19930,0x19928);
    // MOVE.W 4(A1),D3 (C=1) or D2 (C=0); SWAP; RTS.
    case 0x19928:if(!walk_record(c,4,value))return false;am_word(r.d[3],value);am_swap(r.d[3]);return am_return(c);
    case 0x19930:if(!walk_record(c,4,value))return false;am_word(r.d[2],value);am_swap(r.d[2]);return am_return(c);
    default: {
        bool ok=false;if(walk_table_block(c,ok))return ok;
        return am_error(c,"unsupported animation motion walk PC");
    }
    }
}
}
