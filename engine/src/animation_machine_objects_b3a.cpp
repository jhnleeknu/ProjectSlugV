#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OB3A_PAIRS=0x2d8b8;        // 2b64c: LEA 2d8b8(PC),A4 (fixed ROM WORD pairs, read through the live bus, no limit test).
const std::uint32_t OB3A_WORDS=0x2b6c4;        // 2c23e: LEA 2b6c4(PC),A0 (fixed ROM WORDs, read through the live bus, no limit test).
const std::uint32_t OB3A_LISTS=0x104d92;       // 8d3a: LEA 104d92.l,A1 (work RAM list heads / nodes of the leaf 8d34).
const std::uint32_t OB3A_RECORD=0x2b3d0;       // 2c3cc / 2c3f6: CMPI.L #2b3d0,9e(A6) (the record pointer value of N28 2b7ce).
std::uint32_t ob3a_b(std::uint32_t value) {return value&255U;}
std::uint32_t ob3a_w(std::uint32_t value) {return value&65535U;}
// EXT.W of a BYTE (the result is the new low WORD).
std::uint32_t ob3a_ext_b(std::uint32_t value) {return (value&0x80U)!=0U?(0xff00U|(value&255U)):(value&255U);}
// ASR.L by a count 0..63 (68000: register count modulo 64; 32 and more leave only sign bits). Explicit sign refill, no signed shift.
std::uint32_t ob3a_asr_l(std::uint32_t value,unsigned int count) {
    const std::uint32_t sign=(value&0x80000000U)!=0U?0xffffffffU:0U;
    if(count==0U)return value;
    if(count>=32U)return sign;
    return (value>>count)|(sign&~(0xffffffffU>>count));
}
bool ob3a_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob3a_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG).
bool ob3a_install(AnimationMachineContext& c,std::uint32_t value) {return ob3a_put(c,c.s.a[6],0,4,value);}
// BTST.B #bit,d16(An): true when the bit is 1.
bool ob3a_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob3a_get(c,base,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,d16(An).
bool ob3a_setbit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool on) {
    std::uint32_t value=0;if(!ob3a_get(c,base,displacement,1,value))return false;
    return ob3a_put(c,base,displacement,1,on?(value|(1U<<bit)):(value&~(1U<<bit)));
}
// Bcc on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob3a_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b3a caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #n,D0; JSR 28ae.l (the child value is data for 28ae, not an execution PC of this call).
bool ob3a_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t count,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],count);return am_call(c,0x28ae,return_pc);
}
// MOVE.W #n,D0; JSR 3af8.l (sound request).
bool ob3a_sound(AnimationMachineContext& c,std::uint32_t n,std::uint32_t return_pc) {am_word(c.s.d[0],n);return am_call(c,0x3af8,return_pc);}
// (MOVEA.L #list,A1 / LEA list.l,A1 done by the caller;) MOVE.W #100,D0; JSR 49f8c.l (animation list start).
bool ob3a_anim(AnimationMachineContext& c,std::uint32_t return_pc) {am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);}
// MOVE.W 88(A6),D0; JSR target.
bool ob3a_slot_call(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!ob3a_get(c,c.s.a[6],0x88,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MOVEA.L 78(A6),A4; MOVE.B off(A4),D2; MOVE.B off+1(A4),D3; EXT.W D2; EXT.W D3; BTST.B #0,15(A6); BEQ.W taken (fall: NEG.W D2).
bool ob3a_pair78(AnimationMachineContext& c,std::uint32_t off,std::uint32_t fall,std::uint32_t taken) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool bit=false;
    if(!ob3a_get(c,r.a[6],0x78,4,value))return false;r.a[4]=value;
    if(!ob3a_get(c,r.a[4],off,1,value))return false;am_byte(r.d[2],value);
    if(!ob3a_get(c,r.a[4],off+1U,1,value))return false;am_byte(r.d[3],value);
    am_word(r.d[2],ob3a_ext_b(r.d[2]));am_word(r.d[3],ob3a_ext_b(r.d[3]));
    if(!ob3a_bit(c,r.a[6],0x15,0,bit))return false;r.pc=bit?fall:taken;return true;
}
// MOVEA.L 9e(A6),A4; MOVE.L 10(A4),D0; SUB.L 3a(A6),D0; MOVEA.L 9e(A6),A4; MOVE.W 6(A4),D1; ASR.L D1,D0; ADD.L D0,3a(A6) (approach of LONG 3a).
bool ob3a_approach(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    if(!ob3a_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;
    if(!ob3a_get(c,r.a[4],0x10,4,value) || !ob3a_get(c,r.a[6],0x3a,4,other))return false;r.d[0]=value-other;
    if(!ob3a_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;
    if(!ob3a_get(c,r.a[4],0x6,2,value))return false;am_word(r.d[1],value);
    r.d[0]=ob3a_asr_l(r.d[0],r.d[1]&63U);
    if(!ob3a_get(c,r.a[6],0x3a,4,value))return false;return ob3a_put(c,r.a[6],0x3a,4,value+r.d[0]);
}
// MOVE.W (A0),D0; MOVEQ #start,D7; MOVEA.L 9e(A6),A4; MOVE.L (A4),D6; BTST.B #3,D0; BEQ.W taken (input speed head).
bool ob3a_speed_head(AnimationMachineContext& c,std::uint32_t start,std::uint32_t fall,std::uint32_t taken) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.d[7]=start;
    if(!ob3a_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;
    if(!am_read(c,r.a[4],4,value))return false;r.d[6]=value;
    r.pc=((r.d[0]>>3)&1U)!=0U?fall:taken;return true;
}
// MOVE.W (A0),D0; MOVEQ #0,D7; MOVEA.L 9e(A6),A4; MOVE.W 6(A4),D6; MOVEA.L 9e(A6),A4; MOVE.L 8(A4),D5; MOVEA.L 9e(A6),A4; MOVE.W e(A4),D4;
// BTST.B #2,D0; BEQ.W taken (horizontal head).
bool ob3a_horizontal_head(AnimationMachineContext& c,std::uint32_t fall,std::uint32_t taken) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.d[7]=0;
    if(!ob3a_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;if(!ob3a_get(c,r.a[4],0x6,2,value))return false;am_word(r.d[6],value);
    if(!ob3a_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;if(!ob3a_get(c,r.a[4],0x8,4,value))return false;r.d[5]=value;
    if(!ob3a_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;if(!ob3a_get(c,r.a[4],0xe,2,value))return false;am_word(r.d[4],value);
    r.pc=((r.d[0]>>2)&1U)!=0U?fall:taken;return true;
}
// SUB.L 36(A6),D7; ASR.L D6,D7; ADD.L D7,36(A6) (approach of LONG 36).
bool ob3a_approach36(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ob3a_get(c,r.a[6],0x36,4,value))return false;r.d[7]=ob3a_asr_l(r.d[7]-value,r.d[6]&63U);
    if(!ob3a_get(c,r.a[6],0x36,4,value))return false;return ob3a_put(c,r.a[6],0x36,4,value+r.d[7]);
}
// BTST.B #n,D0; Bcc (Z of one bit of D0): taken_when_set selects BNE (true) or BEQ (false).
void ob3a_d0bit(AnimationMachineState& r,unsigned int bit,bool taken_when_set,std::uint32_t fall,std::uint32_t taken) {
    const bool set=((r.d[0]>>bit)&1U)!=0U;r.pc=set==taken_when_set?taken:fall;
}
// BTST.B #7,15(A6); BEQ.W taken.
bool ob3a_live(AnimationMachineContext& c,std::uint32_t fall,std::uint32_t taken) {
    bool bit=false;if(!ob3a_bit(c,c.s.a[6],0x15,7,bit))return false;c.s.pc=bit?fall:taken;return true;
}
// TST.B 5f(A6); BPL.W taken.
bool ob3a_5f(AnimationMachineContext& c,std::uint32_t fall,std::uint32_t taken) {
    std::uint32_t value=0;if(!ob3a_get(c,c.s.a[6],0x5f,1,value))return false;c.s.pc=(value&0x80U)!=0U?fall:taken;return true;
}
// MOVE.L #0,64(A6); MOVE.L #next,(A6) (fall-through into the installed callback).
bool ob3a_stop_install(AnimationMachineContext& c,std::uint32_t next) {
    if(!ob3a_put(c,c.s.a[6],0x64,4,0) || !ob3a_install(c,next))return false;c.s.pc=next;return true;
}
// MOVE.W D0,8c(A6).
bool ob3a_8c(AnimationMachineContext& c) {return ob3a_put(c,c.s.a[6],0x8c,2,c.s.d[0]);}
}
// Objects B3a (216 block starts): the N28 range-outside installation chain 2ba50 without its middle states (B3b): the installed head 2ba50..2baf4
// (17), the later states with the shared per-frame tail 2c562 and the helper 2c71a (2c0fc..2c760, 166), the helpers 2b532 / 2b608 / 2b63e
// (2b532..2b668, 25) and the leaf 8d34 (8d34..8da2, 8). Boundaries without an executor: 2bef6 2bfcc 2c96a (B3b) and 1c114. Known C: 2b5fc (ORI,
// Set) and 2b602 (ANDI, Clear); the 10 consumers 2b544 (4d6b4), 2ba66 (SCC, 28ae), 2bac8 2c1a0 2c2d0 2c382 2c43c 2c6fc (2b418), 2c618 (4d766),
// 2c626 (2b63e -> 4d418) read a known C or fail. Data reads through the live bus: the fixed ROM tables 2d8b8 (4 * BYTE 7c) and 2b6c4
// (2 * BYTE 7d) without limit test, the record of LONG 9e(A6), the BYTE pairs of LONG 78(A6), the path list of LONG 98(A6) and the work RAM
// lists 104d92 of 8d34. No X / MUL / DIV / TRAP / port / bank write.
bool animation_objects_b3a_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool bit=false;
    switch(r.pc) {
    // ---- 8d34 leaf: ANDI.W #ff,D0; LSL.W #4,D0; LEA 104d92.l,A1; LEA (A1,D0.W),A2; TST.W 8(A2); BNE.W 8d4e.
    case 0x8d34:
        am_word(r.d[0],(r.d[0]&0xffU)<<4);r.a[1]=OB3A_LISTS;r.a[2]=am_index(r.a[1],r.d[0]);
        if(!ob3a_get(c,r.a[2],0x8,2,value))return false;r.pc=value!=0U?0x8d4e:0x8d4c;return true;
    case 0x8d4c:case 0x8da0:case 0x2b63c:return am_return(c);               // RTS (C as the path left it, not consumed).
    case 0x8d4e:if(!ob3a_get(c,r.a[2],0xa,2,value))return false;r.pc=value!=ob3a_w(r.d[1])?0x8d5c:0x8d54;return true;   // CMP.W a(A2),D1; BNE.B 8d5c.
    case 0x8d54:if(!ob3a_get(c,r.a[2],0xc,2,value))return false;r.pc=value==ob3a_w(r.d[1])?0x8da0:0x8d5c;return true;   // CMP.W c(A2),D1; BEQ.W 8da0.
    // MOVE.W D1,D4; ANDI.W #ff,D4; LSL.W #4,D4; ADDQ.W #4,D4; LEA (A1,D4.W),A4; CMP.W 2(A4),D0; BEQ.W 8d92.
    case 0x8d5c:
        am_word(r.d[4],r.d[1]);am_word(r.d[4],(r.d[4]&0xffU)<<4);am_word(r.d[4],r.d[4]+4U);r.a[4]=am_index(r.a[1],r.d[4]);
        if(!ob3a_get(c,r.a[4],0x2,2,value))return false;r.pc=value==ob3a_w(r.d[0])?0x8d92:0x8d72;return true;
    // MOVE.W (A2),D2; MOVE.W 2(A2),D3; MOVE.W D2,(A1,D3.W); MOVE.W D3,2(A1,D2.W); MOVE.W 2(A4),D3; MOVE.W D0,(A1,D3.W); MOVE.W D3,2(A2);
    // MOVE.W D4,(A2); MOVE.W D0,2(A4) (unlink the node, link it at the end of list D1).
    case 0x8d72:
        if(!ob3a_get(c,r.a[2],0,2,value))return false;am_word(r.d[2],value);if(!ob3a_get(c,r.a[2],0x2,2,value))return false;am_word(r.d[3],value);
        if(!am_write(c,am_index(r.a[1],r.d[3]),2,ob3a_w(r.d[2])) || !am_write(c,am_index(r.a[1],r.d[2])+2U,2,ob3a_w(r.d[3])))return false;
        if(!ob3a_get(c,r.a[4],0x2,2,value))return false;am_word(r.d[3],value);
        if(!am_write(c,am_index(r.a[1],r.d[3]),2,ob3a_w(r.d[0])) || !ob3a_put(c,r.a[2],0x2,2,r.d[3]) || !ob3a_put(c,r.a[2],0,2,r.d[4]) ||
           !ob3a_put(c,r.a[4],0x2,2,r.d[0]))return false;
        r.pc=0x8d92;return true;
    // MOVE.W D1,a(A2); MOVE.W D1,c(A2); BSET.B #7,f(A2).
    case 0x8d92:if(!ob3a_put(c,r.a[2],0xa,2,r.d[1]) || !ob3a_put(c,r.a[2],0xc,2,r.d[1]) || !ob3a_setbit(c,r.a[2],0xf,7,true))return false;r.pc=0x8da0;return true;
    // ---- 2b532 helper: TST.W 92(A6); BNE.W 2b602.
    case 0x2b532:if(!ob3a_get(c,r.a[6],0x92,2,value))return false;r.pc=value!=0U?0x2b602:0x2b53a;return true;
    case 0x2b53a:return ob3a_slot_call(c,0x4d6b4,0x2b544);                  // MOVE.W 88(A6),D0; JSR 4d6b4.l.
    case 0x2b544:return ob3a_carry(c,0x2b602,0x2b548);                       // BCC.W 2b602 (C returned by 4d6b4).
    // MOVE.W #18,92(A6); MOVEA.L #2d7be,A0; MOVE.W #a,D0; JSR 28ae.l (child 2d7be).
    case 0x2b548:if(!ob3a_put(c,r.a[6],0x92,2,0x18))return false;return ob3a_child(c,0x2d7be,0xa,0x2b55e);
    case 0x2b55e:r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,0x2b568);          // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.l.
    case 0x2b568:return am_call(c,0x491b6,0x2b56e);                          // JSR 491b6.l.
    case 0x2b56e:return ob3a_pair78(c,0x4,0x2b588,0x2b58a);                  // BYTE pair 4/5 of LONG 78(A6); BTST.B #0,15(A6); BEQ.W 2b58a.
    case 0x2b588:case 0x2b634:case 0x2b660:am_word(r.d[2],0x10000U-ob3a_w(r.d[2]));r.pc=r.pc+2U;return true;   // NEG.W D2.
    // MOVE.W D2,36(A0); MOVE.W D3,3a(A0); MOVE.W 1e(A6),1e(A0); CMPI.B #5,84(A6); BNE.W 2b5b6.
    case 0x2b58a:
        if(!ob3a_put(c,r.a[0],0x36,2,r.d[2]) || !ob3a_put(c,r.a[0],0x3a,2,r.d[3]))return false;
        if(!ob3a_get(c,r.a[6],0x1e,2,value) || !ob3a_put(c,r.a[0],0x1e,2,value) || !ob3a_get(c,r.a[6],0x84,1,value))return false;
        r.pc=value!=5U?0x2b5b6:0x2b5a2;return true;
    case 0x2b5a2:return ob3a_child(c,0x2d57a,0xa,0x2b5b2);                   // MOVEA.L #2d57a,A0; MOVE.W #a,D0; JSR 28ae.l (child 2d57a).
    case 0x2b5b2:r.pc=0x2b5c6;return true;                                    // BRA.W 2b5c6.
    case 0x2b5b6:return ob3a_child(c,0x2d3ae,0xa,0x2b5c6);                   // MOVEA.L #2d3ae,A0; MOVE.W #a,D0; JSR 28ae.l (child 2d3ae).
    // MOVE.B 60(A6),60(A0); MOVE.W 8c(A6),D0; BYTE pair 4/5 of LONG 78(A6); BTST.B #0,15(A6); BEQ.W 2b5f0.
    case 0x2b5c6:
        if(!ob3a_get(c,r.a[6],0x60,1,value) || !ob3a_put(c,r.a[0],0x60,1,value) || !ob3a_get(c,r.a[6],0x8c,2,value))return false;
        am_word(r.d[0],value);return ob3a_pair78(c,0x4,0x2b5ea,0x2b5f0);
    case 0x2b5ea:am_word(r.d[0],r.d[0]+0x8000U);am_word(r.d[2],0x10000U-ob3a_w(r.d[2]));r.pc=0x2b5f0;return true;   // ADDI.W #8000,D0; NEG.W D2.
    // MOVE.W D0,76(A0); MOVEQ #ff,D0; JSR 4c2fa.l.
    case 0x2b5f0:if(!ob3a_put(c,r.a[0],0x76,2,r.d[0]))return false;r.d[0]=0xffffffffU;return am_call(c,0x4c2fa,0x2b5fc);
    case 0x2b5fc:r.carry=AnimationCarrySet;return am_return(c);               // ORI.B #1,CCR; RTS (known Set).
    case 0x2b602:r.carry=AnimationCarryClear;return am_return(c);             // ANDI.B #fe,CCR; RTS (known Clear).
    // ---- 2b608 helper: TST.W 92(A6); BNE.W 2b63c.
    case 0x2b608:if(!ob3a_get(c,r.a[6],0x92,2,value))return false;r.pc=value!=0U?0x2b63c:0x2b610;return true;
    // MOVE.W #6,92(A6); MOVE.W 88(A6),D0; BYTE pair 2/3 of LONG 78(A6); BTST.B #0,15(A6); BEQ.W 2b636.
    case 0x2b610:
        if(!ob3a_put(c,r.a[6],0x92,2,6) || !ob3a_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);return ob3a_pair78(c,0x2,0x2b634,0x2b636);
    case 0x2b636:return am_call(c,0x1c114,0x2b63c);                          // JSR 1c114.l (boundary).
    // ---- 2b63e helper: MOVE.W 88(A6),D0; MOVEQ #0,D1; MOVE.B 7c(A6),D1; ADD.W D1,D1 (twice); LEA 2d8b8(PC),A4; ADDA.W D1,A4;
    // MOVE.W (A4)+,D2; MOVE.W (A4)+,D3; BTST.B #0,15(A6); BEQ.W 2b662.
    case 0x2b63e:
        if(!ob3a_get(c,r.a[6],0x88,2,value) || !ob3a_get(c,r.a[6],0x7c,1,other))return false;am_word(r.d[0],value);
        r.d[1]=other;am_word(r.d[1],r.d[1]*2U);am_word(r.d[1],r.d[1]*2U);r.a[4]=OB3A_PAIRS+am_extend_word(r.d[1]);
        if(!am_read(c,r.a[4],2,value))return false;am_word(r.d[2],value);r.a[4]+=2U;
        if(!am_read(c,r.a[4],2,value))return false;am_word(r.d[3],value);r.a[4]+=2U;
        if(!ob3a_bit(c,r.a[6],0x15,0,bit))return false;r.pc=bit?0x2b660:0x2b662;return true;
    case 0x2b662:r.pc=0x4d418;return true;                                    // JMP 4d418.l (its RTS gives the known C).
    // ---- 2ba50 (installed by N28 2ba3e): MOVE.W #0,92(A6); MOVEA.L #2d916,A0; MOVE.W #0,D0; JSR 28ae.l (child 2d916).
    case 0x2ba50:if(!ob3a_put(c,r.a[6],0x92,2,0))return false;return ob3a_child(c,0x2d916,0,0x2ba66);
    // SCC.B 62(A6) (C returned by 28ae); MOVE.L #2ba70,(A6) (MOVE clears C).
    case 0x2ba66:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects b3a caller requires known carry");
        if(!ob3a_put(c,r.a[6],0x62,1,r.carry==AnimationCarryClear?0xffU:0U) || !ob3a_install(c,0x2ba70))return false;
        r.carry=AnimationCarryClear;r.pc=0x2ba70;return true;
    // MOVE.B #f,86(A6); TST.B 62(A6); BNE.W 2ba92.
    case 0x2ba70:if(!ob3a_put(c,r.a[6],0x86,1,0xf) || !ob3a_get(c,r.a[6],0x62,1,value))return false;r.pc=value!=0U?0x2ba92:0x2ba7e;return true;
    case 0x2ba7e:if(!ob3a_put(c,r.a[6],0x64,4,0))return false;return am_call(c,0x2c71a,0x2ba8a);   // MOVE.L #0,64(A6); JSR 2c71a(PC).
    case 0x2ba8a:case 0x2bac4:case 0x2c19c:case 0x2c37e:case 0x2c438:case 0x2c55a:case 0x2c6f8:return am_call(c,0x2b418,r.pc+4U);   // JSR/BSR 2b418 (N28).
    case 0x2ba8e:case 0x2baf0:case 0x2c1aa:case 0x2c20e:case 0x2c2fc:case 0x2c38c:case 0x2c45c:case 0x2c55e:r.pc=0x2c562;return true;   // BRA.W 2c562.
    case 0x2ba92:case 0x2c1ae:return ob3a_sound(c,0x1a60,r.pc+0xaU);         // MOVE.W #1a60,D0; JSR 3af8.l.
    case 0x2ba9c:r.a[1]=0x64674;return ob3a_anim(c,0x2baac);                  // MOVEA.L #64674,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2baac:if(!ob3a_install(c,0x2bab2))return false;r.pc=0x2bab2;return true;   // MOVE.L #2bab2,(A6).
    // MOVE.B #f,86(A6); MOVE.L #0,64(A6); JSR 2c71a(PC).
    case 0x2bab2:if(!ob3a_put(c,r.a[6],0x86,1,0xf) || !ob3a_put(c,r.a[6],0x64,4,0))return false;return am_call(c,0x2c71a,0x2bac4);
    case 0x2bac8:return ob3a_carry(c,0x2bad2,0x2bacc);                       // BCC.W 2bad2 (C returned by 2b418).
    case 0x2bacc:if(!ob3a_install(c,0x2c0fc))return false;r.pc=0x2bad2;return true;   // MOVE.L #2c0fc,(A6).
    case 0x2bad2:return ob3a_slot_call(c,0x49be0,0x2badc);                  // MOVE.W 88(A6),D0; JSR 49be0.l.
    // MOVE.W (A0),D0; ANDI.W #22,D0; CMPI.W #22,D0; BNE.W 2baf0.
    case 0x2badc:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value&0x22U);r.pc=ob3a_w(r.d[0])!=0x22U?0x2baf0:0x2baea;return true;
    case 0x2baea:if(!ob3a_install(c,0x2c6cc))return false;r.pc=0x2baf0;return true;   // MOVE.L #2c6cc,(A6).
    // ---- 2c0fc: MOVE.W #1a62,D0; JSR 3af8.l.
    case 0x2c0fc:case 0x2c6cc:return ob3a_sound(c,0x1a62,r.pc+0xaU);
    // MOVE.B 7e(A6),82(A6); MOVEA.L #64c44,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2c106:if(!ob3a_get(c,r.a[6],0x7e,1,value) || !ob3a_put(c,r.a[6],0x82,1,value))return false;r.a[1]=0x64c44;return ob3a_anim(c,0x2c11c);
    case 0x2c11c:if(!ob3a_install(c,0x2c122))return false;r.pc=0x2c122;return true;   // MOVE.L #2c122,(A6).
    case 0x2c122:return ob3a_live(c,0x2c12c,0x2c212);                         // BTST.B #7,15(A6); BEQ.W 2c212.
    // MOVE.B 7e(A6),D0; CMP.B 82(A6),D0; BEQ.W 2c14c.
    case 0x2c12c:if(!ob3a_get(c,r.a[6],0x7e,1,value) || !ob3a_get(c,r.a[6],0x82,1,other))return false;am_byte(r.d[0],value);r.pc=value==other?0x2c14c:0x2c138;return true;
    // MOVE.B D0,82(A6); MOVEA.L #64c44,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2c138:if(!ob3a_put(c,r.a[6],0x82,1,r.d[0]))return false;r.a[1]=0x64c44;return ob3a_anim(c,0x2c14c);
    case 0x2c14c:case 0x2c1d6:case 0x2c332:case 0x2c408:return ob3a_slot_call(c,0x49be0,r.pc+0xaU);   // MOVE.W 88(A6),D0; JSR 49be0.l.
    case 0x2c156:return ob3a_speed_head(c,0,0x2c168,0x2c16a);
    case 0x2c33c:return ob3a_speed_head(c,1,0x2c34e,0x2c350);
    case 0x2c412:return ob3a_speed_head(c,0,0x2c424,0x2c426);
    case 0x2c168:case 0x2c34e:case 0x2c424:r.d[7]+=r.d[6];r.pc=r.pc+2U;return true;   // ADD.L D6,D7.
    case 0x2c16a:ob3a_d0bit(r,2,false,0x2c172,0x2c174);return true;           // BTST.B #2,D0; BEQ.W 2c174.
    case 0x2c350:ob3a_d0bit(r,2,false,0x2c358,0x2c35a);return true;           // BTST.B #2,D0; BEQ.W 2c35a.
    case 0x2c426:ob3a_d0bit(r,2,false,0x2c42e,0x2c430);return true;           // BTST.B #2,D0; BEQ.W 2c430.
    case 0x2c172:case 0x2c358:case 0x2c42e:r.d[7]-=r.d[6];r.pc=r.pc+2U;return true;   // SUB.L D6,D7.
    // MOVE.L D7,64(A6); BTST.B #7,D0; BNE.W 2c96a (B3b).
    case 0x2c174:if(!ob3a_put(c,r.a[6],0x64,4,r.d[7]))return false;ob3a_d0bit(r,7,true,0x2c180,0x2c96a);return true;
    case 0x2c180:ob3a_d0bit(r,5,true,0x2c188,0x2c1ae);return true;            // BTST.B #5,D0; BNE.W 2c1ae.
    case 0x2c188:ob3a_d0bit(r,1,true,0x2c190,0x2bfcc);return true;            // BTST.B #1,D0; BNE.W 2bfcc (B3b).
    case 0x2c190:ob3a_d0bit(r,6,true,0x2c198,0x2bef6);return true;            // BTST.B #6,D0; BNE.W 2bef6 (B3b).
    case 0x2c198:case 0x2c37a:case 0x2c434:case 0x2c6f4:return am_call(c,0x2c71a,r.pc+4U);   // BSR.W 2c71a.
    case 0x2c1a0:return ob3a_carry(c,0x2c1aa,0x2c1a4);                       // BCC.W 2c1aa (C returned by 2b418).
    case 0x2c1a4:case 0x2c386:if(!ob3a_install(c,0x2baf4))return false;r.pc=r.pc+6U;return true;   // MOVE.L #2baf4,(A6) (B3b value).
    // ---- 2c1ae: MOVE.L #0,3a(A6); MOVEA.L #6bdb6,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2c1b8:if(!ob3a_put(c,r.a[6],0x3a,4,0))return false;r.a[1]=0x6bdb6;return ob3a_anim(c,0x2c1d0);
    case 0x2c1d0:if(!ob3a_install(c,0x2c1d6))return false;r.pc=0x2c1d6;return true;   // MOVE.L #2c1d6,(A6).
    // MOVE.W (A0),D0; BTST.B #6,D0; BEQ.W 2c1ee.
    case 0x2c1e0:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);ob3a_d0bit(r,6,false,0x2c1ea,0x2c1ee);return true;
    case 0x2c1ea:case 0x2c2ba:case 0x2c376:return am_call(c,0x2b532,r.pc+4U);   // BSR.W 2b532 (C not read here).
    case 0x2c1ee:case 0x2c2be:if(!ob3a_get(c,r.a[6],0x94,4,value))return false;r.a[0]=value;return am_call(c,0x4c390,r.pc+0xaU);   // MOVEA.L 94(A6),A0; JSR 4c390.l.
    case 0x2c1f8:case 0x2c2c8:if(!ob3a_8c(c))return false;return am_call(c,0x2b418,r.pc+8U);   // MOVE.W D0,8c(A6); BSR.W 2b418.
    // TST.L 3a(A6); BEQ.W 2c20e.
    case 0x2c200:if(!ob3a_get(c,r.a[6],0x3a,4,value))return false;r.pc=value==0U?0x2c20e:0x2c208;return true;
    case 0x2c208:if(!ob3a_install(c,0x2c236))return false;r.pc=0x2c20e;return true;   // MOVE.L #2c236,(A6).
    // ---- 2c212: LEA 65f56.l,A1; TST.B 7f(A6); BEQ.W 2c226.
    case 0x2c212:r.a[1]=0x65f56;if(!ob3a_get(c,r.a[6],0x7f,1,value))return false;r.pc=value==0U?0x2c226:0x2c220;return true;
    case 0x2c220:r.a[1]=0x64c44;r.pc=0x2c226;return true;                    // LEA 64c44.l,A1.
    case 0x2c226:return ob3a_anim(c,0x2c230);                                 // MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2c230:if(!ob3a_install(c,0x2c236))return false;r.pc=0x2c236;return true;   // MOVE.L #2c236,(A6).
    // MOVEQ #0,D0; MOVE.B 7d(A6),D0; ADD.W D0,D0; LEA 2b6c4(PC),A0; MOVE.W (A0,D0.W),D0; MOVEA.L 94(A6),A0; JSR 4c408.l.
    case 0x2c236:
        if(!ob3a_get(c,r.a[6],0x7d,1,value))return false;r.d[0]=value;am_word(r.d[0],r.d[0]*2U);r.a[0]=OB3A_WORDS;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
        if(!ob3a_get(c,r.a[6],0x94,4,value))return false;r.a[0]=value;return am_call(c,0x4c408,0x2c250);
    // approach of LONG 3a; MOVE.W 88(A6),D0; JSR 49be0.l.
    case 0x2c250:if(!ob3a_approach(c))return false;return ob3a_slot_call(c,0x49be0,0x2c274);
    case 0x2c274:return ob3a_horizontal_head(c,0x2c298,0x2c29c);
    case 0x2c4d4:return ob3a_horizontal_head(c,0x2c4f8,0x2c4fc);
    case 0x2c298:case 0x2c4f8:r.d[7]-=r.d[5];am_word(r.d[6],r.d[4]);r.pc=r.pc+4U;return true;   // SUB.L D5,D7; MOVE.W D4,D6.
    case 0x2c2a4:case 0x2c504:r.d[7]+=r.d[5];am_word(r.d[6],r.d[4]);r.pc=r.pc+4U;return true;   // ADD.L D5,D7; MOVE.W D4,D6.
    case 0x2c29c:ob3a_d0bit(r,3,false,0x2c2a4,0x2c2a8);return true;           // BTST.B #3,D0; BEQ.W 2c2a8.
    case 0x2c4fc:ob3a_d0bit(r,3,false,0x2c504,0x2c508);return true;           // BTST.B #3,D0; BEQ.W 2c508.
    // approach of LONG 36; BTST.B #6,D0; BEQ.W 2c2be.
    case 0x2c2a8:if(!ob3a_approach36(c))return false;ob3a_d0bit(r,6,false,0x2c2ba,0x2c2be);return true;
    case 0x2c2d0:return ob3a_carry(c,0x2c2e4,0x2c2d4);                       // BCC.W 2c2e4 (C returned by 2b418).
    case 0x2c2d4:r.a[1]=0x65f56;return ob3a_anim(c,0x2c2e4);                  // MOVEA.L #65f56,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2c2e4:return ob3a_live(c,0x2c2ee,0x2c2fc);                         // BTST.B #7,15(A6); BEQ.W 2c2fc.
    case 0x2c2ee:if(!ob3a_get(c,r.a[6],0x3a,4,value))return false;r.pc=(value&0x80000000U)!=0U?0x2c2f6:0x2c2fc;return true;   // TST.L 3a(A6); BPL.W 2c2fc.
    case 0x2c2f6:if(!ob3a_install(c,0x2c300))return false;r.pc=0x2c2fc;return true;   // MOVE.L #2c300,(A6).
    // ---- 2c300: MOVE.W #1a61,D0; JSR 3af8.l / MOVEA.L #6c176,A1; MOVE.W #100,D0; JSR 49f8c.l / MOVE.L #0,64(A6); MOVE.L #2c328,(A6).
    case 0x2c300:return ob3a_sound(c,0x1a61,0x2c30a);
    case 0x2c30a:r.a[1]=0x6c176;return ob3a_anim(c,0x2c31a);
    case 0x2c31a:return ob3a_stop_install(c,0x2c328);
    case 0x2c328:return ob3a_live(c,0x2c332,0x2c212);                         // BTST.B #7,15(A6); BEQ.W 2c212.
    // MOVE.L D7,64(A6); BTST.B #5,D0; BNE.W 2c1ae.
    case 0x2c35a:if(!ob3a_put(c,r.a[6],0x64,4,r.d[7]))return false;ob3a_d0bit(r,5,true,0x2c366,0x2c1ae);return true;
    case 0x2c366:ob3a_d0bit(r,1,true,0x2c36e,0x2bfcc);return true;            // BTST.B #1,D0; BNE.W 2bfcc (B3b).
    case 0x2c36e:ob3a_d0bit(r,6,false,0x2c376,0x2c37a);return true;           // BTST.B #6,D0; BEQ.W 2c37a.
    case 0x2c382:return ob3a_carry(c,0x2c38c,0x2c386);                       // BCC.W 2c38c (C returned by 2b418).
    // ---- 2c390 (installed by 2c67a): MOVE.B #0,5e(A6); BTST.B #7,15(A6); BEQ.W 2c460.
    case 0x2c390:if(!ob3a_put(c,r.a[6],0x5e,1,0))return false;return ob3a_live(c,0x2c3a0,0x2c460);
    case 0x2c3a0:return ob3a_5f(c,0x2c3a8,0x2c3bc);                           // TST.B 5f(A6); BPL.W 2c3bc.
    case 0x2c460:return ob3a_5f(c,0x2c468,0x2c47c);                           // TST.B 5f(A6); BPL.W 2c47c.
    case 0x2c52a:return ob3a_5f(c,0x2c532,0x2c53c);                           // TST.B 5f(A6); BPL.W 2c53c.
    case 0x2c3a8:case 0x2c468:return ob3a_sound(c,0x1a59,r.pc+0xaU);         // MOVE.W #1a59,D0; JSR 3af8.l.
    case 0x2c3bc:case 0x2c47c:return ob3a_sound(c,0x1a5a,r.pc+0xaU);         // MOVE.W #1a5a,D0; JSR 3af8.l.
    case 0x2c3b2:r.a[1]=0x6e11c;r.pc=0x2c3cc;return true;                    // LEA 6e11c.l,A1; BRA.W 2c3cc.
    case 0x2c3c6:r.a[1]=0x6e73c;r.pc=0x2c3cc;return true;                    // LEA 6e73c.l,A1.
    // CMPI.L #2b3d0,9e(A6); BNE.W 2c3de.
    case 0x2c3cc:if(!ob3a_get(c,r.a[6],0x9e,4,value))return false;r.pc=value!=OB3A_RECORD?0x2c3de:0x2c3d8;return true;
    case 0x2c3d8:r.a[1]=0x6e8e2;r.pc=0x2c3de;return true;                    // LEA 6e8e2.l,A1.
    case 0x2c3de:return ob3a_anim(c,0x2c3e8);                                 // MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2c3e8:return ob3a_stop_install(c,0x2c3f6);                         // MOVE.L #0,64(A6); MOVE.L #2c3f6,(A6).
    // ORI.B #3e,86(A6); CMPI.L #2b3d0,9e(A6); BNE.W 2c434.
    case 0x2c3f6:
        if(!ob3a_get(c,r.a[6],0x86,1,value) || !ob3a_put(c,r.a[6],0x86,1,value|0x3eU) || !ob3a_get(c,r.a[6],0x9e,4,value))return false;
        r.pc=value!=OB3A_RECORD?0x2c434:0x2c408;return true;
    case 0x2c430:if(!ob3a_put(c,r.a[6],0x64,4,r.d[7]))return false;r.pc=0x2c434;return true;   // MOVE.L D7,64(A6).
    case 0x2c43c:return ob3a_carry(c,0x2c45c,0x2c440);                       // BCC.W 2c45c (C returned by 2b418).
    // MOVE.L #0,98(A6); MOVE.L #2baf4,(A6); TST.W 54(A6); BNE.W 2c45c.
    case 0x2c440:
        if(!ob3a_put(c,r.a[6],0x98,4,0) || !ob3a_install(c,0x2baf4) || !ob3a_get(c,r.a[6],0x54,2,value))return false;
        r.pc=value!=0U?0x2c45c:0x2c456;return true;
    case 0x2c456:if(!ob3a_install(c,0x2c7fe))return false;r.pc=0x2c45c;return true;   // MOVE.L #2c7fe,(A6) (N28 value).
    case 0x2c472:r.a[1]=0x6d7ec;r.pc=0x2c48c;return true;                    // LEA 6d7ec.l,A1; BRA.W 2c48c.
    case 0x2c486:r.a[1]=0x6d84e;r.pc=0x2c48c;return true;                    // LEA 6d84e.l,A1.
    case 0x2c48c:return ob3a_anim(c,0x2c496);                                 // MOVE.W #100,D0; JSR 49f8c.l.
    // MOVEA.L 9e(A6),A4; MOVE.L 14(A4),D0; ASR.L #1,D0; ADD.L D0,3a(A6); MOVE.L #2c4aa,(A6).
    case 0x2c496:
        if(!ob3a_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;if(!ob3a_get(c,r.a[4],0x14,4,value))return false;r.d[0]=ob3a_asr_l(value,1);
        if(!ob3a_get(c,r.a[6],0x3a,4,value) || !ob3a_put(c,r.a[6],0x3a,4,value+r.d[0]) || !ob3a_install(c,0x2c4aa))return false;r.pc=0x2c4aa;return true;
    // ORI.B #3e,86(A6); approach of LONG 3a; MOVE.W 88(A6),D0; JSR 49be0.l.
    case 0x2c4aa:
        if(!ob3a_get(c,r.a[6],0x86,1,value) || !ob3a_put(c,r.a[6],0x86,1,value|0x3eU) || !ob3a_approach(c))return false;
        return ob3a_slot_call(c,0x49be0,0x2c4d4);
    // approach of LONG 36; MOVEA.L 94(A6),A0; JSR 4c390.l.
    case 0x2c508:if(!ob3a_approach36(c) || !ob3a_get(c,r.a[6],0x94,4,value))return false;r.a[0]=value;return am_call(c,0x4c390,0x2c51c);
    case 0x2c51c:if(!ob3a_8c(c))return false;return ob3a_live(c,0x2c52a,0x2c55a);   // MOVE.W D0,8c(A6); BTST.B #7,15(A6); BEQ.W 2c55a.
    case 0x2c532:r.a[1]=0x6d890;r.pc=0x2c542;return true;                    // LEA 6d890.l,A1; BRA.W 2c542.
    case 0x2c53c:r.a[1]=0x6dca2;r.pc=0x2c542;return true;                    // LEA 6dca2.l,A1.
    case 0x2c542:return ob3a_anim(c,0x2c54c);                                 // MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2c54c:if(!ob3a_put(c,r.a[6],0x64,4,0) || !ob3a_install(c,0x2c3f6))return false;r.pc=0x2c55a;return true;   // MOVE.L #0,64(A6); MOVE.L #2c3f6,(A6).
    // ---- 2c562 shared tail: CMPI.B #7,7f(A6); BCC.W 2c574.
    case 0x2c562:if(!ob3a_get(c,r.a[6],0x7f,1,value))return false;r.pc=value>=7U?0x2c574:0x2c56c;return true;
    case 0x2c56c:am_byte(r.d[7],1);r.pc=0x2c578;return true;                 // MOVE.B #1,D7; BRA.W 2c578.
    case 0x2c574:am_byte(r.d[7],0);r.pc=0x2c578;return true;                 // MOVE.B #0,D7.
    case 0x2c578:return ob3a_slot_call(c,0x4d98a,0x2c582);                  // MOVE.W 88(A6),D0; JSR 4d98a.l.
    case 0x2c582:if(!ob3a_get(c,r.a[6],0x92,2,value))return false;r.pc=value==0U?0x2c58e:0x2c58a;return true;   // TST.W 92(A6); BEQ.W 2c58e.
    case 0x2c58a:if(!ob3a_get(c,r.a[6],0x92,2,value) || !ob3a_put(c,r.a[6],0x92,2,value-1U))return false;r.pc=0x2c58e;return true;   // SUBQ.W #1,92(A6).
    // BCLR.B #6,61(A6); BEQ.W 2c5ae (Z of the old bit).
    case 0x2c58e:if(!ob3a_bit(c,r.a[6],0x61,6,bit) || !ob3a_setbit(c,r.a[6],0x61,6,false))return false;r.pc=bit?0x2c598:0x2c5ae;return true;
    case 0x2c598:if(!ob3a_get(c,r.a[6],0x5e,1,value))return false;r.pc=value==0x18U?0x2c5ae:0x2c5a2;return true;   // CMPI.B #18,5e(A6); BEQ.W 2c5ae.
    case 0x2c5a2:if(!ob3a_setbit(c,r.a[6],0x61,7,false) || !ob3a_put(c,r.a[6],0x5e,1,0))return false;r.pc=0x2c5ae;return true;   // BCLR.B #7,61(A6); MOVE.B #0,5e(A6).
    // MOVEA.L 98(A6),A0; CMPA.W #0,A0; BEQ.W 2c5e6 (32-bit compare with the extended WORD 0).
    case 0x2c5ae:if(!ob3a_get(c,r.a[6],0x98,4,value))return false;r.a[0]=value;r.pc=value==0U?0x2c5e6:0x2c5ba;return true;
    // MOVE.B 1a(A6),14(A6); MOVE.W (A0)+,D1; CMPI.W #ffff,D1; BNE.W 2c5ce.
    case 0x2c5ba:
        if(!ob3a_get(c,r.a[6],0x1a,1,value) || !ob3a_put(c,r.a[6],0x14,1,value) || !am_read(c,r.a[0],2,value))return false;
        am_word(r.d[1],value);r.a[0]+=2U;r.pc=ob3a_w(r.d[1])!=0xffffU?0x2c5ce:0x2c5ca;return true;
    // ADDA.W (A0),A0; MOVE.W (A0)+,D1.
    case 0x2c5ca:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=am_extend_word(value);if(!am_read(c,r.a[0],2,value))return false;
        am_word(r.d[1],value);r.a[0]+=2U;r.pc=0x2c5ce;return true;
    // MOVE.L A0,98(A6); MOVE.B 14(A6),D0; JSR 8d34.l.
    case 0x2c5ce:if(!ob3a_put(c,r.a[6],0x98,4,r.a[0]) || !ob3a_get(c,r.a[6],0x14,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x8d34,0x2c5dc);
    case 0x2c5dc:if(!ob3a_setbit(c,r.a[6],0x61,6,true))return false;r.pc=0x2c612;return true;   // BSET.B #6,61(A6); BRA.W 2c612.
    // MOVE.B 1b(A6),14(A6); MOVE.B 86(A6),D0; BEQ.W 2c612.
    case 0x2c5e6:
        if(!ob3a_get(c,r.a[6],0x1b,1,value) || !ob3a_put(c,r.a[6],0x14,1,value) || !ob3a_get(c,r.a[6],0x86,1,value))return false;
        am_byte(r.d[0],value);r.pc=value==0U?0x2c612:0x2c5f4;return true;
    // SUBQ.B #1,D0; MOVE.B D0,86(A6); BTST.B #0,D0; BEQ.W 2c60c.
    case 0x2c5f4:am_byte(r.d[0],r.d[0]-1U);if(!ob3a_put(c,r.a[6],0x86,1,r.d[0]))return false;ob3a_d0bit(r,0,false,0x2c602,0x2c60c);return true;
    // MOVE.B 19(A6),14(A6); ST.B 90(A6).
    case 0x2c602:if(!ob3a_get(c,r.a[6],0x19,1,value) || !ob3a_put(c,r.a[6],0x14,1,value) || !ob3a_put(c,r.a[6],0x90,1,0xff))return false;r.pc=0x2c60c;return true;
    case 0x2c60c:case 0x2c61c:if(!ob3a_setbit(c,r.a[6],0x61,6,true))return false;r.pc=r.pc+6U;return true;   // BSET.B #6,61(A6).
    case 0x2c612:return am_call(c,0x4d766,0x2c618);                          // JSR 4d766.l.
    case 0x2c618:return ob3a_carry(c,0x2c622,0x2c61c);                       // BCC.W 2c622 (C returned by 4d766).
    case 0x2c622:return am_call(c,0x2b63e,0x2c626);                          // BSR.W 2b63e.
    case 0x2c626:return ob3a_carry(c,0x2c62a,0x2c642);                       // BCS.W 2c642 (C returned by 2b63e -> 4d418).
    // MOVE.W 88(A6),D0; MOVE.B #1,D1; JSR 4d4b4.l.
    case 0x2c62a:case 0x2c700:if(!ob3a_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],1);return am_call(c,0x4d4b4,r.pc+0xeU);
    case 0x2c638:if(!ob3a_install(c,0x2b96c))return false;r.pc=0x2c65c;return true;   // MOVE.L #2b96c,(A6) (N28 value); BRA.W 2c65c.
    case 0x2c642:return ob3a_slot_call(c,0x4d7a6,0x2c64c);                  // MOVE.W 88(A6),D0; JSR 4d7a6.l.
    case 0x2c64c:r.pc=ob3a_b(r.d[0])!=1U?0x2c65c:0x2c654;return true;        // CMPI.B #1,D0; BNE.W 2c65c.
    case 0x2c654:if(!ob3a_put(c,r.a[6],0x83,1,r.d[1]) || !ob3a_put(c,r.a[6],0x84,1,r.d[2]))return false;r.pc=0x2c65c;return true;   // MOVE.B D1,83(A6); MOVE.B D2,84(A6).
    case 0x2c65c:return ob3a_slot_call(c,0x4d734,0x2c666);                  // MOVE.W 88(A6),D0; JSR 4d734.l.
    case 0x2c666:return am_call(c,0x4b54e,0x2c66c);                          // JSR 4b54e.l.
    case 0x2c66c:if(!ob3a_get(c,r.a[6],0x5e,1,value))return false;r.pc=value==0U?0x2c69e:0x2c674;return true;   // TST.B 5e(A6); BEQ.W 2c69e.
    // BSET.B #6,61(A6); MOVE.L #2c390,(A6); CMPI.B #18,5e(A6); BNE.W 2c690.
    case 0x2c674:
        if(!ob3a_setbit(c,r.a[6],0x61,6,true) || !ob3a_install(c,0x2c390) || !ob3a_get(c,r.a[6],0x5e,1,value))return false;
        r.pc=value!=0x18U?0x2c690:0x2c68a;return true;
    case 0x2c68a:if(!ob3a_install(c,0x2ca68))return false;r.pc=0x2c690;return true;   // MOVE.L #2ca68,(A6) (N28 value).
    case 0x2c690:if(!ob3a_get(c,r.a[6],0x5e,1,value))return false;r.pc=value!=0x19U?0x2c69e:0x2c69a;return true;   // CMPI.B #19,5e(A6); BNE.W 2c69e.
    case 0x2c69a:if(!ob3a_put(c,r.a[6],0x54,2,0))return false;r.pc=0x2c69e;return true;   // CLR.W 54(A6).
    case 0x2c69e:return ob3a_live(c,0x2c6a8,0x2c6ba);                         // BTST.B #7,15(A6); BEQ.W 2c6ba.
    case 0x2c6a8:if(!ob3a_get(c,r.a[6],0x64,2,value))return false;r.pc=value==0U?0x2c6ba:0x2c6b0;return true;   // TST.W 64(A6); BEQ.W 2c6ba.
    case 0x2c6b0:r.a[0]=0x2c92e;return am_call(c,0x4ae4a,0x2c6ba);           // LEA 2c92e(PC),A0; JSR 4ae4a.l.
    // MOVE.W 88(A6),D0; MOVEA.L 56(A6),A1; JSR 4d9ba.l.
    case 0x2c6ba:
        if(!ob3a_get(c,r.a[6],0x88,2,value) || !ob3a_get(c,r.a[6],0x56,4,other))return false;am_word(r.d[0],value);r.a[1]=other;return am_call(c,0x4d9ba,0x2c6c8);
    case 0x2c6c8:r.pc=0x2c8ca;return true;                                    // BRA.W 2c8ca (N28 shared tail).
    // ---- 2c6cc: MOVEA.L #6495e,A1; MOVE.W #100,D0; JSR 49f8c.l / MOVE.L #0,64(A6); MOVE.L #2c6f4,(A6).
    case 0x2c6d6:r.a[1]=0x6495e;return ob3a_anim(c,0x2c6e6);
    case 0x2c6e6:return ob3a_stop_install(c,0x2c6f4);
    case 0x2c6fc:return ob3a_carry(c,0x2c70e,0x2c700);                       // BCC.W 2c70e (C returned by 2b418).
    case 0x2c70e:if(!ob3a_put(c,r.a[6],0x56,4,0))return false;r.pc=0x2c562;return true;   // MOVE.L #0,56(A6); BRA.W 2c562.
    // ---- 2c71a helper: MOVEA.L 94(A6),A0; BTST.B #7,15(A6); BEQ.W 2c734.
    case 0x2c71a:if(!ob3a_get(c,r.a[6],0x94,4,value))return false;r.a[0]=value;return ob3a_live(c,0x2c728,0x2c734);
    case 0x2c728:return am_call(c,0x4c3cc,0x2c72e);                          // JSR 4c3cc.l.
    case 0x2c72e:case 0x2c75a:if(!ob3a_8c(c))return false;return am_return(c);   // MOVE.W D0,8c(A6); RTS.
    // MOVE.L 64(A6),36(A6); approach of LONG 3a; JSR 4c390.l.
    case 0x2c734:
        if(!ob3a_get(c,r.a[6],0x64,4,value) || !ob3a_put(c,r.a[6],0x36,4,value) || !ob3a_approach(c))return false;return am_call(c,0x4c390,0x2c75a);
    default:return am_error(c,"unsupported animation objects b3a PC");
    }
}
}
