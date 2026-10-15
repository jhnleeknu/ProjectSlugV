#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OB2D_BANK_94=0x200094;     // 3b04a 2d6ec: MOVE.L 200094.l,22(A6) (banked LONG through the live bus).
const std::uint32_t OB2D_BANK_B8=0x2000b8;     // 2d3b4 2d580: MOVE.L 2000b8.l,22(A6).
const std::uint32_t OB2D_BANK_8C=0x20008c;     // 2d52a: MOVE.L 20008c.l,22(A6).
const std::uint32_t OB2D_PAIRS=0x3b03c;        // 3b0ac: LEA 3b03c(PC),A1 (fixed ROM WORD pairs, read through the live bus).
std::uint32_t ob2d_b(std::uint32_t value) {return value&255U;}
std::uint32_t ob2d_w(std::uint32_t value) {return value&65535U;}
// ASR.L #n (1..8): the sign bit refills the vacated high bits (explicit, no signed shift).
std::uint32_t ob2d_asr_l(std::uint32_t value,unsigned int n) {
    const std::uint32_t fill=(value&0x80000000U)!=0U?~(0xffffffffU>>n):0U;return (value>>n)|fill;
}
// ASR.W #n (1..8) of the low WORD (the result is the new WORD value).
std::uint32_t ob2d_asr_w(std::uint32_t value,unsigned int n) {
    const std::uint32_t w=value&65535U;const std::uint32_t fill=(w&0x8000U)!=0U?((0xffffU<<(16U-n))&0xffffU):0U;return (w>>n)|fill;
}
bool ob2d_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob2d_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG).
bool ob2d_install(AnimationMachineContext& c,std::uint32_t value) {return ob2d_put(c,c.s.a[6],0,4,value);}
// BTST.B #bit,d16(An): true when the bit is 1.
bool ob2d_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob2d_get(c,base,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,d16(An).
bool ob2d_setbit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool on) {
    std::uint32_t value=0;if(!ob2d_get(c,base,displacement,1,value))return false;
    return ob2d_put(c,base,displacement,1,on?(value|(1U<<bit)):(value&~(1U<<bit)));
}
// Bcc on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob2d_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b2d caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #n,D0; JSR 28ae.l (the child value is data for 28ae, not an execution PC of this call).
bool ob2d_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t count,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],count);return am_call(c,0x28ae,return_pc);
}
// MOVEA.L #list,A0; JSR 3b302(PC) (animation list pointer is data).
bool ob2d_anim(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {c.s.a[0]=list;return am_call(c,0x3b302,return_pc);}
// BTST.B #5,94(An); SNE.B D0; BTST.B #0,15(An); SNE.B D1; EOR.B D1,D0 (facing test): true when D0.B != 0 afterwards.
bool ob2d_facing(AnimationMachineContext& c,std::uint32_t base,bool& differ) {
    bool b5=false;bool b0=false;if(!ob2d_bit(c,base,0x94,5,b5) || !ob2d_bit(c,base,0x15,0,b0))return false;
    am_byte(c.s.d[0],b5?0xffU:0U);am_byte(c.s.d[1],b0?0xffU:0U);am_byte(c.s.d[0],c.s.d[0]^c.s.d[1]);differ=ob2d_b(c.s.d[0])!=0U;return true;
}
// MOVE.B #b,b0/95(A6) etc. and MOVE.L #speed,64(A6) with BCLR/BSET.B #5,94(A6) (the walking state setters).
bool ob2d_walk(AnimationMachineContext& c,std::uint32_t speed,bool left) {
    return ob2d_put(c,c.s.a[6],0x64,4,speed) && ob2d_setbit(c,c.s.a[6],0x94,5,left);
}
// MOVE.W #12a,20(A6); MOVE.L 2000b8.l,22(A6); MOVE.W #1a55,D0; JSR 3af8.l (the shared head of 2d3ae / 2d57a).
bool ob2d_shot_head(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;
    if(!ob2d_put(c,c.s.a[6],0x20,2,0x12a) || !am_read(c,OB2D_BANK_B8,4,value) || !ob2d_put(c,c.s.a[6],0x22,4,value))return false;
    am_word(c.s.d[0],0x1a55);return am_call(c,0x3af8,return_pc);
}
// BSET.B #4,15(A6); MOVE.W #e000,68(A6); MOVE.W #e000,1e(A6); MOVEA.L #2e26c,A1; MOVE.W #0,D0; JSR 49f8c.l.
bool ob2d_shot_anim(AnimationMachineContext& c,std::uint32_t return_pc) {
    if(!ob2d_setbit(c,c.s.a[6],0x15,4,true) || !ob2d_put(c,c.s.a[6],0x68,2,0xe000) || !ob2d_put(c,c.s.a[6],0x1e,2,0xe000))return false;
    c.s.a[1]=0x2e26c;am_word(c.s.d[0],0);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #n,D0; MOVE.B #0,D1; JSR 8ebe.l.
bool ob2d_sound(AnimationMachineContext& c,std::uint32_t n,std::uint32_t return_pc) {am_word(c.s.d[0],n);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);}
// MOVE.L #160000,D0; MOVE.B 76(A6),D1; JSR 443d2.l.
bool ob2d_angle(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!ob2d_get(c,c.s.a[6],0x76,1,value))return false;c.s.d[0]=0x160000;am_byte(c.s.d[1],value);return am_call(c,0x443d2,return_pc);
}
// MOVE.B 76(A6),D0; ASR.W #3,D0; ANDI.B #1f,D0; MOVE.B D0,81(A6) (the upper byte of D0.W is the previous one).
bool ob2d_frame81(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!ob2d_get(c,c.s.a[6],0x76,1,value))return false;am_byte(c.s.d[0],value);
    am_word(c.s.d[0],ob2d_asr_w(c.s.d[0],3));am_byte(c.s.d[0],c.s.d[0]&0x1fU);return ob2d_put(c,c.s.a[6],0x81,1,c.s.d[0]);
}
// MOVE.W 42(A6),D0; ADDI.W #10,D0; CMPI.W #160,D0; BCC.W 2d572 / CMPI.W #100,46(A6); BMI.W 2d572 (screen test of 2d4e6 / 2d6ca).
bool ob2d_screen_x(AnimationMachineContext& c,std::uint32_t inside_pc) {
    std::uint32_t value=0;if(!ob2d_get(c,c.s.a[6],0x42,2,value))return false;am_word(c.s.d[0],value+0x10U);
    c.s.pc=ob2d_w(c.s.d[0])>=0x160U?0x2d572U:inside_pc;return true;
}
bool ob2d_screen_y(AnimationMachineContext& c,std::uint32_t inside_pc) {
    std::uint32_t value=0;if(!ob2d_get(c,c.s.a[6],0x46,2,value))return false;c.s.pc=((value-0x100U)&0x8000U)!=0U?0x2d572U:inside_pc;return true;
}
// MOVE.W 2c(A6),D0; SUBI.W #100,D0; ASR.W #3,D0; SUB.W D0,2c(A6).
bool ob2d_scale(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!ob2d_get(c,c.s.a[6],0x2c,2,value))return false;
    am_word(c.s.d[0],value-0x100U);am_word(c.s.d[0],ob2d_asr_w(c.s.d[0],3));return ob2d_put(c,c.s.a[6],0x2c,2,value-c.s.d[0]);
}
// Common input head of the 39366 states. Each entry: block, fall-through, branch target (see the cases).
struct Ob2dPair {std::uint32_t pc;std::uint32_t fall;std::uint32_t taken;};
const Ob2dPair OB2D_STATE_15[]={{0x391e8,0x391f2,0x398be},{0x392b0,0x392ba,0x398be},{0x39454,0x3945e,0x398be},{0x3955a,0x39564,0x398be}};
const Ob2dPair OB2D_INPUT[]={{0x391f2,0x391f6,0},{0x392ba,0x392be,0},{0x3945e,0x39462,0},{0x39564,0x39568,0}};
const Ob2dPair OB2D_BIT7[]={{0x391f6,0x391fe,0x39eb2},{0x392ea,0x392f2,0x39eb2},{0x39462,0x3946a,0x39eb2},{0x39568,0x39570,0x39eb2}};
const Ob2dPair OB2D_BIT1[]={{0x391fe,0x39206,0x39218},{0x392f2,0x392fa,0x3930c},{0x3946a,0x39472,0x39484},{0x39570,0x39578,0x3958a}};
const Ob2dPair OB2D_9F[]={{0x39206,0x3920e,0x39218},{0x392fa,0x39302,0x3930c},{0x39472,0x3947a,0x39484},{0x39578,0x39580,0x3958a}};
const Ob2dPair OB2D_GUARD[]={{0x3920e,0x39218,0x38ff4},{0x39302,0x3930c,0x38ff4},{0x3947a,0x39484,0x38ff4},{0x39580,0x3958a,0x38ff4}};
const Ob2dPair OB2D_BIT5[]={{0x39218,0x39220,0x38dd4},{0x3930c,0x39314,0x38dd4},{0x39484,0x3948c,0x38dd4},{0x3958a,0x39592,0x38dd4}};
const Ob2dPair OB2D_9D[]={{0x39220,0x3922a,0x39244},{0x39314,0x3931e,0x39338},{0x3948c,0x39496,0x394b0}};
const Ob2dPair OB2D_GRAB[]={{0x3922a,0x3923c,0},{0x3931e,0x39330,0},{0x39496,0x394a8,0}};
const Ob2dPair OB2D_GRABBED[]={{0x3923c,0x39244,0x39296},{0x39330,0x39338,0x39296},{0x394a8,0x394b0,0x39296}};
bool ob2d_find(const Ob2dPair* table,unsigned int count,std::uint32_t pc,Ob2dPair& out) {
    for(unsigned int i=0;i<count;++i)if(table[i].pc==pc){out=table[i];return true;}return false;
}
// BTST.B #n,D0; Bcc (Z of one bit of D0): taken_when_set selects BNE (true) or BEQ (false).
void ob2d_d0bit(AnimationMachineState& r,unsigned int bit,bool taken_when_set,std::uint32_t fall,std::uint32_t taken) {
    const bool set=((r.d[0]>>bit)&1U)!=0U;r.pc=set==taken_when_set?taken:fall;
}
// BTST.B #5,94(A6); Bcc.
bool ob2d_94bit(AnimationMachineContext& c,bool taken_when_set,std::uint32_t fall,std::uint32_t taken) {
    bool set=false;if(!ob2d_bit(c,c.s.a[6],0x94,5,set))return false;c.s.pc=set==taken_when_set?taken:fall;return true;
}
// 2d488 / 2d63c: ADD.W D0,D0; ADD.W D0,D0; JMP base(PC,D0.W) (no limit test in this block, as in the original).
void ob2d_table(AnimationMachineState& r,std::uint32_t base) {
    am_word(r.d[0],r.d[0]*2U);am_word(r.d[0],r.d[0]*2U);r.pc=(base+am_extend_word(r.d[0]))&0xffffffU;
}
}
// Objects B2d (220 block starts): the orphan state chain 39366 (391e8..395dc, 115; installed by B2b 38dc2 and N32a 391de) with its 28ae child
// 3b044 (3b044..3b118, 18) and the 28ae children 2d3ae / 2d57a of B2b 3a4da with their shared tail and the child 2d6e6 (2d3ae..2d7be, 87). Every
// callee and exit has an executor (3a5be's JSR (A0) target is live). Known C: none produced; the nine consumers 3923c 39330 394a8 (C returned by
// 3a4da), 39358 395ce (3b334), 3b0ec (288c), 3b10c 2d56e 2d7b2 (49fc6) read a known C or fail. Data reads: the fixed ROM WORD pairs 3b03c..3b044
// and the banked LONGs 200094 2000b8 20008c (live bus). No X / DIV / port / bank write.
bool animation_objects_b2d_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool bit=false;Ob2dPair p={0,0,0};
    if(ob2d_find(OB2D_STATE_15,4,r.pc,p)) {                                 // BTST.B #7,15(A6); BEQ.W 398be.
        if(!ob2d_bit(c,r.a[6],0x15,7,bit))return false;r.pc=bit?p.fall:p.taken;return true;
    }
    if(ob2d_find(OB2D_INPUT,4,r.pc,p))return am_call(c,0x3b424,p.fall);     // JSR 3b424(PC).
    if(ob2d_find(OB2D_BIT7,4,r.pc,p)){ob2d_d0bit(r,7,true,p.fall,p.taken);return true;}   // BTST.B #7,D0; BNE.W 39eb2.
    if(ob2d_find(OB2D_BIT1,4,r.pc,p)){ob2d_d0bit(r,1,true,p.fall,p.taken);return true;}   // BTST.B #1,D0; BNE.W.
    if(ob2d_find(OB2D_9F,4,r.pc,p)) {                                       // TST.B 9f(A6); BEQ.W.
        if(!ob2d_get(c,r.a[6],0x9f,1,value))return false;r.pc=value==0U?p.taken:p.fall;return true;
    }
    if(ob2d_find(OB2D_GUARD,4,r.pc,p)) {                                    // BTST.B #7,15(A6); BNE.W 38ff4.
        if(!ob2d_bit(c,r.a[6],0x15,7,bit))return false;r.pc=bit?p.taken:p.fall;return true;
    }
    if(ob2d_find(OB2D_BIT5,4,r.pc,p)){ob2d_d0bit(r,5,true,p.fall,p.taken);return true;}   // BTST.B #5,D0; BNE.W 38dd4.
    if(ob2d_find(OB2D_9D,3,r.pc,p)) {                                       // BTST.B #6,9d(A6); BEQ.W.
        if(!ob2d_bit(c,r.a[6],0x9d,6,bit))return false;r.pc=bit?p.fall:p.taken;return true;
    }
    if(ob2d_find(OB2D_GRAB,3,r.pc,p)) {                                     // MOVE.L D0,-(A7); ANDI.B #bf,9d(A6); ANDI.B #bf,9e(A6); JSR 3a4da(PC).
        if(!am_push(c,4,r.d[0]))return false;
        if(!ob2d_setbit(c,r.a[6],0x9d,6,false) || !ob2d_setbit(c,r.a[6],0x9e,6,false))return false;return am_call(c,0x3a4da,p.fall);
    }
    if(ob2d_find(OB2D_GRABBED,3,r.pc,p)) {                                  // MOVEM.L (A7)+,D0; BCS.W 39296 (C returned by 3a4da; MOVEM keeps it).
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects b2d caller requires known carry");
        if(!am_pop(c,4,value))return false;r.d[0]=value;r.pc=r.carry==AnimationCarrySet?p.taken:p.fall;return true;
    }
    switch(r.pc) {
    // ---- 39366 state chain: 391e8 body.
    case 0x39244:ob2d_d0bit(r,2,true,0x3924c,0x3939c);return true;            // BTST.B #2,D0; BNE.W 3939c.
    case 0x3924c:ob2d_d0bit(r,3,true,0x39254,0x39384);return true;            // BTST.B #3,D0; BNE.W 39384.
    // BSET.B #3,94(A6); MOVEA.L 82(A6),A0; JSR 3a5be(PC).
    case 0x39254:
        if(!ob2d_setbit(c,r.a[6],0x94,3,true) || !ob2d_get(c,r.a[6],0x82,4,value))return false;r.a[0]=value;return am_call(c,0x3a5be,0x39262);
    // MOVE.B 97(A6),D0; CMPI.B #0,D0; BEQ.W 39282.
    case 0x39262:if(!ob2d_get(c,r.a[6],0x97,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x39282:0x3926e;return true;
    case 0x3926e:r.pc=ob2d_b(r.d[0])==4U?0x39366:0x39276;return true;        // CMPI.B #4,D0; BEQ.W 39366.
    case 0x39276:case 0x39350:case 0x394ea:case 0x395c6:return am_call(c,0x3b288,r.pc+4U);   // JSR 3b288(PC).
    case 0x3927a:case 0x39354:case 0x394ee:case 0x395ca:return am_call(c,0x3b334,r.pc+4U);   // JSR 3b334(PC).
    case 0x3927e:case 0x39362:case 0x3951a:case 0x395d8:r.pc=0x3a350;return true;            // BRA.W 3a350 (N31).
    case 0x39282:return ob2d_anim(c,0x3b8e8,0x3928c);                        // MOVEA.L #3b8e8,A0; JSR 3b302(PC).
    case 0x3928c:if(!ob2d_install(c,0x39292))return false;r.pc=0x39292;return true;   // MOVE.L #39292,(A6).
    case 0x39292:case 0x39380:r.pc=0x391e8;return true;                      // BRA.W 391e8.
    // ---- 39296: MOVE.B #ff,98(A6); MOVEA.L #3b97e,A0; JSR 3b302(PC).
    case 0x39296:if(!ob2d_put(c,r.a[6],0x98,1,0xff))return false;return ob2d_anim(c,0x3b97e,0x392a6);
    case 0x392a6:return am_call(c,0x3a5d2,0x392aa);                          // JSR 3a5d2(PC) (N33).
    case 0x392aa:if(!ob2d_install(c,0x392b0))return false;r.pc=0x392b0;return true;   // MOVE.L #392b0,(A6).
    case 0x392be:if(!ob2d_get(c,r.a[6],0x98,1,value))return false;r.pc=value==0U?0x392ea:0x392c6;return true; // TST.B 98(A6); BEQ.W 392ea.
    // MOVEQ #0,D7; MOVE.L #2a000,D6; BTST.B #3,D0; BEQ.W 392d8.
    case 0x392c6:r.d[7]=0;r.d[6]=0x2a000;ob2d_d0bit(r,3,false,0x392d6,0x392d8);return true;
    case 0x392d6:r.d[7]+=r.d[6];r.pc=0x392d8;return true;                    // ADD.L D6,D7.
    case 0x392d8:ob2d_d0bit(r,2,false,0x392e0,0x392e2);return true;           // BTST.B #2,D0; BEQ.W 392e2.
    case 0x392e0:r.d[7]-=r.d[6];r.pc=0x392e2;return true;                    // SUB.L D6,D7.
    case 0x392e2:if(!ob2d_put(c,r.a[6],0x64,4,r.d[7]))return false;r.pc=0x39350;return true; // MOVE.L D7,64(A6); BRA.W 39350.
    case 0x39338:ob2d_d0bit(r,3,true,0x39340,0x393e8);return true;            // BTST.B #3,D0; BNE.W 393e8.
    case 0x39340:ob2d_d0bit(r,2,true,0x39348,0x39406);return true;            // BTST.B #2,D0; BNE.W 39406.
    case 0x39348:if(!ob2d_put(c,r.a[6],0x64,4,0))return false;r.pc=0x39350;return true;    // MOVE.L #0,64(A6).
    case 0x39358:return ob2d_carry(c,0x39362,0x3935c);                       // BCC.W 39362 (C returned by 3b334).
    case 0x3935c:case 0x395d2:if(!ob2d_install(c,0x39366))return false;r.pc=r.pc+6U;return true; // MOVE.L #39366,(A6).
    // ---- 39366: MOVEA.L #3b8dc,A0; JSR 3b302(PC) / MOVE.B #2,95(A6); CLR.L 64(A6); MOVE.L #39380,(A6).
    case 0x39366:return ob2d_anim(c,0x3b8dc,0x39370);
    case 0x39370:
        if(!ob2d_put(c,r.a[6],0x95,1,2) || !ob2d_put(c,r.a[6],0x64,4,0) || !ob2d_install(c,0x39380))return false;r.pc=0x39380;return true;
    // ---- 39384 / 3939c: MOVE.B #5,b0(A6); MOVE.L #speed,64(A6); BCLR / BSET.B #5,94(A6).
    case 0x39384:if(!ob2d_put(c,r.a[6],0xb0,1,5) || !ob2d_walk(c,0x2a000,false))return false;r.pc=0x393b0;return true;
    case 0x3939c:if(!ob2d_put(c,r.a[6],0xb0,1,5) || !ob2d_walk(c,0xfffd6000U,true))return false;r.pc=0x393b0;return true;
    case 0x393b0:if(!ob2d_facing(c,r.a[6],bit))return false;r.pc=bit?0x393d4:0x393c6;return true;
    case 0x393c6:return ob2d_anim(c,0x3b8ee,0x393d0);
    case 0x393d0:r.pc=0x393de;return true;                                    // BRA.W 393de.
    case 0x393d4:return ob2d_anim(c,0x3b8f4,0x393de);
    case 0x393de:case 0x3943a:r.pc=0x39448;return true;                      // BRA.W 39448.
    // ---- 393e2 / 39400: MOVE.B #3,b0(A6); 393e8 / 39406: MOVE.B #2,95(A6); MOVE.L #speed,64(A6); BCLR / BSET.B #5,94(A6).
    case 0x393e2:case 0x39400:if(!ob2d_put(c,r.a[6],0xb0,1,3))return false;r.pc=r.pc+6U;return true;
    case 0x393e8:if(!ob2d_put(c,r.a[6],0x95,1,2) || !ob2d_walk(c,0x2a000,false))return false;r.pc=0x3941a;return true;
    case 0x39406:if(!ob2d_put(c,r.a[6],0x95,1,2) || !ob2d_walk(c,0xfffd6000U,true))return false;r.pc=0x3941a;return true;
    case 0x3941a:if(!ob2d_facing(c,r.a[6],bit))return false;r.pc=bit?0x3943e:0x39430;return true;
    case 0x39430:return ob2d_anim(c,0x3b8fa,0x3943a);
    case 0x3943e:return ob2d_anim(c,0x3b900,0x39448);
    // MOVE.W #100,2c(A6); MOVE.L #39454,(A6).
    case 0x39448:if(!ob2d_put(c,r.a[6],0x2c,2,0x100) || !ob2d_install(c,0x39454))return false;r.pc=0x39454;return true;
    // ---- 39454 body.
    case 0x394b0:ob2d_d0bit(r,3,false,0x394b8,0x394c6);return true;           // BTST.B #3,D0; BEQ.W 394c6.
    case 0x394b8:return ob2d_94bit(c,true,0x394c2,0x393e2);                   // BTST.B #5,94(A6); BNE.W 393e2.
    case 0x394c2:case 0x394d8:r.pc=0x394e2;return true;                      // BRA.W 394e2.
    case 0x394c6:ob2d_d0bit(r,2,false,0x394ce,0x394dc);return true;           // BTST.B #2,D0; BEQ.W 394dc.
    case 0x394ce:return ob2d_94bit(c,false,0x394d8,0x39400);                  // BTST.B #5,94(A6); BEQ.W 39400.
    case 0x394dc:if(!ob2d_install(c,0x3951e))return false;r.pc=0x394e2;return true;   // MOVE.L #3951e,(A6).
    case 0x394e2:case 0x395be:                                              // MOVEA.L 82(A6),A0; JSR 3a5be(PC).
        if(!ob2d_get(c,r.a[6],0x82,4,value))return false;r.a[0]=value;return am_call(c,0x3a5be,r.pc+8U);
    // MOVEQ #0,D0; MOVE.B b0(A6),D0; BEQ.W 3951a.
    case 0x394f2:if(!ob2d_get(c,r.a[6],0xb0,1,value))return false;r.d[0]=value;r.pc=value==0U?0x3951a:0x394fc;return true;
    // LSL.B #4,D0; SUB.B D0,af(A6); BCC.W 3951a (borrow of the BYTE subtraction).
    case 0x394fc:
        am_byte(r.d[0],r.d[0]<<4);if(!ob2d_get(c,r.a[6],0xaf,1,value))return false;
        if(!ob2d_put(c,r.a[6],0xaf,1,value-ob2d_b(r.d[0])))return false;r.pc=ob2d_b(r.d[0])>value?0x39506:0x3951a;return true;
    // SUBQ.B #1,b0(A6); MOVEA.L #3b044,A0; MOVE.W #1e,D0; JSR 28ae.l (child 3b044).
    case 0x39506:if(!ob2d_get(c,r.a[6],0xb0,1,value) || !ob2d_put(c,r.a[6],0xb0,1,value-1U))return false;return ob2d_child(c,0x3b044,0x1e,0x3951a);
    // ---- 3951e: facing, animation 3b906 / 3b90c, MOVE.L #0,64(A6); MOVE.L #3955a,(A6).
    case 0x3951e:if(!ob2d_facing(c,r.a[6],bit))return false;r.pc=bit?0x39542:0x39534;return true;
    case 0x39534:return ob2d_anim(c,0x3b906,0x3953e);
    case 0x3953e:r.pc=0x3954c;return true;                                    // BRA.W 3954c.
    case 0x39542:return ob2d_anim(c,0x3b90c,0x3954c);
    case 0x3954c:if(!ob2d_put(c,r.a[6],0x64,4,0) || !ob2d_install(c,0x3955a))return false;r.pc=0x3955a;return true;
    // ---- 3955a body.
    case 0x39592:ob2d_d0bit(r,3,false,0x3959a,0x395a8);return true;           // BTST.B #3,D0; BEQ.W 395a8.
    case 0x3959a:return ob2d_94bit(c,false,0x395a4,0x393e8);                  // BTST.B #5,94(A6); BEQ.W 393e8.
    case 0x395a4:r.pc=0x39384;return true;                                    // BRA.W 39384.
    case 0x395a8:ob2d_d0bit(r,2,false,0x395b0,0x395be);return true;           // BTST.B #2,D0; BEQ.W 395be.
    case 0x395b0:return ob2d_94bit(c,true,0x395ba,0x39406);                   // BTST.B #5,94(A6); BNE.W 39406.
    case 0x395ba:r.pc=0x3939c;return true;                                    // BRA.W 3939c.
    case 0x395ce:return ob2d_carry(c,0x395d8,0x395d2);                       // BCC.W 395d8 (C returned by 3b334).
    // ---- 3b044: 28ae child of 39506.
    case 0x3b044:                                                           // MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); MOVEA.L #3d050,A1; MOVE.W #100,D0; JSR 49f8c.l.
        if(!ob2d_put(c,r.a[6],0x20,2,0xe2) || !am_read(c,OB2D_BANK_94,4,value) || !ob2d_put(c,r.a[6],0x22,4,value))return false;
        r.a[1]=0x3d050;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3b062);
    case 0x3b062:return ob2d_sound(c,0x204,0x3b070);                         // MOVE.W #204,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVEA.L c(A6),A0; MOVEQ #0,D0; MOVE.B af(A0),D0; ADDI.W #100,D0; MOVE.W D0,2c(A6); TST.L 36(A0); BPL.W 3b090.
    case 0x3b070:
        if(!ob2d_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ob2d_get(c,r.a[0],0xaf,1,value))return false;
        r.d[0]=value;am_word(r.d[0],r.d[0]+0x100U);if(!ob2d_put(c,r.a[6],0x2c,2,r.d[0]) || !ob2d_get(c,r.a[0],0x36,4,value))return false;
        r.pc=(value&0x80000000U)!=0U?0x3b08a:0x3b090;return true;
    case 0x3b08a:if(!ob2d_setbit(c,r.a[6],0x15,0,true))return false;r.pc=0x3b090;return true; // BSET.B #0,15(A6).
    // MOVEQ #0,D0; facing of the parent A0; BEQ.W 3b0ac.
    case 0x3b090:r.d[0]=0;if(!ob2d_facing(c,r.a[0],bit))return false;r.pc=bit?0x3b0a8:0x3b0ac;return true;
    case 0x3b0a8:am_word(r.d[0],4);r.pc=0x3b0ac;return true;                  // MOVE.W #4,D0.
    // LEA 3b03c(PC),A1; ADDA.W D0,A1; MOVE.W (A1)+,D0; MOVE.W (A1)+,D1; BTST.B #0,15(A0); BEQ.W 3b0c2.
    case 0x3b0ac:
        r.a[1]=OB2D_PAIRS+am_extend_word(r.d[0]);if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[0],value);r.a[1]+=2U;
        if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[1],value);r.a[1]+=2U;
        if(!ob2d_bit(c,r.a[0],0x15,0,bit))return false;r.pc=bit?0x3b0c0:0x3b0c2;return true;
    case 0x3b0c0:am_word(r.d[0],0x10000U-ob2d_w(r.d[0]));r.pc=0x3b0c2;return true;   // NEG.W D0.
    // ADD.W 42(A0),D0; ADD.W 46(A0),D1; LEA 538e(A5),A1; SUB.W 14(A1),D0; SUB.W 18(A1),D1; LEA 2e(A6),A0; JSR 43e08.l.
    case 0x3b0c2:
        if(!ob2d_get(c,r.a[0],0x42,2,value) || !ob2d_get(c,r.a[0],0x46,2,other))return false;am_word(r.d[0],r.d[0]+value);am_word(r.d[1],r.d[1]+other);
        r.a[1]=am_index(r.a[5],0x538e);if(!ob2d_get(c,r.a[1],0x14,2,value) || !ob2d_get(c,r.a[1],0x18,2,other))return false;
        am_word(r.d[0],r.d[0]-value);am_word(r.d[1],r.d[1]-other);r.a[0]=am_index(r.a[6],0x2e);return am_call(c,0x43e08,0x3b0e0);
    case 0x3b0e0:if(!ob2d_install(c,0x3b0e6))return false;r.pc=0x3b0e6;return true;   // MOVE.L #3b0e6,(A6).
    case 0x3b0e6:return am_call(c,0x288c,0x3b0ec);                           // JSR 288c.l.
    case 0x3b0ec:return ob2d_carry(c,0x3b0f0,0x3b0f6);                       // BCS.W 3b0f6 (C returned by 288c).
    case 0x3b0f0:case 0x3b110:case 0x2d572:case 0x2d7b6:r.pc=0x2a00;return true;     // JMP 2a00.l.
    // MOVE.W 1e(A0),1e(A6); ADDQ.W #1,1e(A6); JSR 43e34.l.
    case 0x3b0f6:
        if(!ob2d_get(c,r.a[0],0x1e,2,value) || !ob2d_put(c,r.a[6],0x1e,2,value) || !ob2d_put(c,r.a[6],0x1e,2,value+1U))return false;
        return am_call(c,0x43e34,0x3b106);
    case 0x3b106:case 0x2d568:case 0x2d7ac:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.l.
    case 0x3b10c:return ob2d_carry(c,0x3b116,0x3b110);                       // BCC.W 3b116 (C returned by 49fc6).
    case 0x3b116:case 0x2d50e:case 0x2d578:case 0x2d6e4:case 0x2d7bc:return am_return(c);  // RTS (C as the path left it).
    // ---- 2d3ae / 2d57a: 28ae children of B2b 3a4da (same head bytes at two addresses).
    case 0x2d3ae:return ob2d_shot_head(c,0x2d3c6);
    case 0x2d57a:return ob2d_shot_head(c,0x2d592);
    case 0x2d3c6:return ob2d_shot_anim(c,0x2d3e8);
    case 0x2d592:return ob2d_shot_anim(c,0x2d5b4);
    case 0x2d3e8:return ob2d_sound(c,0x258,0x2d3f6);
    case 0x2d5b4:return ob2d_sound(c,0x258,0x2d5c2);
    case 0x2d3f6:return ob2d_angle(c,0x2d406);
    case 0x2d5c2:return ob2d_angle(c,0x2d5d2);
    // MOVEA.L c(A6),A0; ADD.L 36(A0),D0; ADD.L 3a(A0),D1; MOVE.L D0,36(A6); MOVE.L D1,3a(A6); MOVE.L #2d420,(A6).
    case 0x2d406:
        if(!ob2d_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ob2d_get(c,r.a[0],0x36,4,value) || !ob2d_get(c,r.a[0],0x3a,4,other))return false;
        r.d[0]+=value;r.d[1]+=other;
        if(!ob2d_put(c,r.a[6],0x36,4,r.d[0]) || !ob2d_put(c,r.a[6],0x3a,4,r.d[1]) || !ob2d_install(c,0x2d420))return false;r.pc=0x2d420;return true;
    // MOVEQ #0,D0; SUB.L 36(A6),D0; ASR.L #3,D0; ADD.L D0,36(A6); MOVE.L #ffe40000,D1; SUB.L 3a(A6),D1; ASR.L #3,D1; MOVE.L 36(A6),D0; BPL.W 2d442.
    case 0x2d420:
        if(!ob2d_get(c,r.a[6],0x36,4,value))return false;r.d[0]=ob2d_asr_l(0U-value,3);if(!ob2d_put(c,r.a[6],0x36,4,value+r.d[0]))return false;
        if(!ob2d_get(c,r.a[6],0x3a,4,other))return false;r.d[1]=ob2d_asr_l(0xffe40000U-other,3);
        if(!ob2d_get(c,r.a[6],0x36,4,value))return false;r.d[0]=value;r.pc=(value&0x80000000U)!=0U?0x2d440:0x2d442;return true;
    case 0x2d440:r.d[0]=0U-r.d[0];r.pc=0x2d442;return true;                  // NEG.L D0.
    // ASR.L #8,D0; MULU.W #36,D0; ADD.L D0,D1; ADD.L D1,3a(A6); BYTE 81 from BYTE 76; JSR 4be34.l.
    case 0x2d442:
        r.d[0]=ob2d_asr_l(r.d[0],8);r.d[0]=(r.d[0]&65535U)*0x36U;r.d[1]+=r.d[0];
        if(!ob2d_get(c,r.a[6],0x3a,4,value) || !ob2d_put(c,r.a[6],0x3a,4,value+r.d[1]) || !ob2d_frame81(c))return false;return am_call(c,0x4be34,0x2d462);
    case 0x2d462:case 0x2d616:                                              // BTST.B #7,15(A6); BNE.W 2d4c4.
        if(!ob2d_bit(c,r.a[6],0x15,7,bit))return false;r.pc=bit?0x2d4c4:r.pc+0xaU;return true;
    case 0x2d46c:case 0x2d620:                                              // BTST.B #0,61(A6); BNE.W 2d4c4.
        if(!ob2d_bit(c,r.a[6],0x61,0,bit))return false;r.pc=bit?0x2d4c4:r.pc+0xaU;return true;
    case 0x2d476:r.a[0]=0x2d354;return am_call(c,0x4ae4a,0x2d480);            // LEA 2d354(PC),A0; JSR 4ae4a.l.
    case 0x2d62a:r.a[0]=0x2d390;return am_call(c,0x4ae4a,0x2d634);            // LEA 2d390(PC),A0; JSR 4ae4a.l.
    case 0x2d480:r.pc=ob2d_w(r.d[0])>=9U?0x2d4b4:0x2d488;return true;         // CMPI.W #9,D0; BCC.W 2d4b4.
    case 0x2d634:r.pc=ob2d_w(r.d[0])>=9U?0x2d668:0x2d63c;return true;         // CMPI.W #9,D0; BCC.W 2d668.
    case 0x2d488:ob2d_table(r,0x2d490);return true;
    case 0x2d63c:ob2d_table(r,0x2d644);return true;
    case 0x2d490:case 0x2d49c:case 0x2d4a0:case 0x2d4a4:case 0x2d4a8:case 0x2d4ac:case 0x2d4b0:r.pc=0x2d4b4;return true;    // BRA.W 2d4b4.
    case 0x2d494:case 0x2d498:r.pc=0x2d4c4;return true;                     // BRA.W 2d4c4.
    case 0x2d644:case 0x2d650:case 0x2d654:case 0x2d658:case 0x2d65c:case 0x2d660:case 0x2d664:r.pc=0x2d668;return true;    // BRA.W 2d668.
    case 0x2d648:case 0x2d64c:r.pc=0x2d678;return true;                     // BRA.W 2d678.
    case 0x2d4b4:case 0x2d668:                                              // BTST.B #1,61(A6); BEQ.W 2d4ca / 2d67e.
        if(!ob2d_bit(c,r.a[6],0x61,1,bit))return false;r.pc=bit?r.pc+0xaU:r.pc+0x16U;return true;
    case 0x2d4be:case 0x2d672:if(!ob2d_setbit(c,r.a[6],0x15,1,true))return false;r.pc=r.pc+6U;return true;   // BSET.B #1,15(A6).
    case 0x2d4c4:case 0x2d678:if(!ob2d_install(c,0x2d510))return false;r.pc=r.pc+6U;return true;            // MOVE.L #2d510,(A6).
    case 0x2d4ca:case 0x2d67e:return am_call(c,0x49fc6,r.pc+6U);             // JSR 49fc6.l (C not read).
    case 0x2d4d0:if(!ob2d_get(c,r.a[6],0x3a,4,value))return false;r.pc=(value&0x80000000U)!=0U?0x2d4d8:0x2d4e6;return true; // TST.L 3a(A6); BPL.W.
    // MOVE.W 76(A6),D0; SUBI.W #c000,D0; ASR.W #2,D0; SUB.W D0,76(A6).
    case 0x2d4d8:
        if(!ob2d_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value-0xc000U);am_word(r.d[0],ob2d_asr_w(r.d[0],2));
        if(!ob2d_put(c,r.a[6],0x76,2,value-r.d[0]))return false;r.pc=0x2d4e6;return true;
    case 0x2d4e6:if(!ob2d_scale(c))return false;return ob2d_screen_x(c,0x2d504);
    case 0x2d504:return ob2d_screen_y(c,0x2d50e);
    case 0x2d6ca:return ob2d_screen_x(c,0x2d6da);
    case 0x2d6da:return ob2d_screen_y(c,0x2d6e4);
    // ---- 2d510 (installed): MOVE.W #1a63,D0; JSR 3af8.l / LEA 2d372(PC),A0; JSR 4ae4a.l.
    case 0x2d510:am_word(r.d[0],0x1a63);return am_call(c,0x3af8,0x2d51a);
    case 0x2d51a:r.a[0]=0x2d372;return am_call(c,0x4ae4a,0x2d524);
    // MOVE.W #d2,20(A6); MOVE.L 20008c.l,22(A6); MOVE.W #378,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x2d524:
        if(!ob2d_put(c,r.a[6],0x20,2,0xd2) || !am_read(c,OB2D_BANK_8C,4,value) || !ob2d_put(c,r.a[6],0x22,4,value))return false;
        return ob2d_sound(c,0x378,0x2d540);
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); MOVEA.L #2ecaa / #2e206,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2d540:case 0x2d702:
        if(!ob2d_put(c,r.a[6],0x68,2,0x1001) || !ob2d_put(c,r.a[6],0x1e,2,0x1001))return false;
        r.a[1]=r.pc==0x2d540U?0x2ecaaU:0x2e206U;am_word(r.d[0],0x100);return am_call(c,0x49f8c,r.pc+0x1cU);
    case 0x2d55c:if(!ob2d_install(c,0x2d562))return false;r.pc=0x2d562;return true;   // MOVE.L #2d562,(A6).
    case 0x2d562:case 0x2d770:return am_call(c,0x43e34,r.pc+6U);             // JSR 43e34.l.
    case 0x2d56e:return ob2d_carry(c,0x2d578,0x2d572);                       // BCC.W 2d578 (C returned by 49fc6).
    // ---- 2d57a tail: MOVEA.L c(A6),A0; MOVE.L D0,36(A6); MOVE.L D1,3a(A6); ASR.L #4 both; MOVE.L 78/7c; BYTE 81; MOVE.L #2d600,(A6); RTS.
    case 0x2d5d2:
        if(!ob2d_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob2d_put(c,r.a[6],0x36,4,r.d[0]) || !ob2d_put(c,r.a[6],0x3a,4,r.d[1]))return false;r.d[0]=ob2d_asr_l(r.d[0],4);r.d[1]=ob2d_asr_l(r.d[1],4);
        if(!ob2d_put(c,r.a[6],0x78,4,r.d[0]) || !ob2d_put(c,r.a[6],0x7c,4,r.d[1]) || !ob2d_frame81(c) || !ob2d_install(c,0x2d600))return false;
        return am_return(c);
    // MOVE.L 78(A6),D0; MOVE.L 7c(A6),D1; ADD.L D0,36(A6); ADD.L D1,3a(A6); JSR 4be34.l.
    case 0x2d600:
        if(!ob2d_get(c,r.a[6],0x78,4,value) || !ob2d_get(c,r.a[6],0x7c,4,other))return false;r.d[0]=value;r.d[1]=other;
        if(!ob2d_get(c,r.a[6],0x36,4,value) || !ob2d_put(c,r.a[6],0x36,4,value+r.d[0]))return false;
        if(!ob2d_get(c,r.a[6],0x3a,4,value) || !ob2d_put(c,r.a[6],0x3a,4,value+r.d[1]))return false;return am_call(c,0x4be34,0x2d616);
    // scale 2c; SUBI.B #c0,80(A6); BCC.W 2d6ca (borrow when BYTE 80 < c0).
    case 0x2d684:
        if(!ob2d_scale(c) || !ob2d_get(c,r.a[6],0x80,1,value) || !ob2d_put(c,r.a[6],0x80,1,value-0xc0U))return false;
        r.pc=value<0xc0U?0x2d69c:0x2d6ca;return true;
    case 0x2d69c:return ob2d_child(c,0x2d6e6,0x1e,0x2d6ac);                  // MOVEA.L #2d6e6,A0; MOVE.W #1e,D0; JSR 28ae.l (child 2d6e6).
    // MOVE.L A0,-(A7); MOVE.L #fff80000,D0; MOVE.B 76(A6),D1; JSR 443d2.l.
    case 0x2d6ac:
        if(!am_push(c,4,r.a[0]) || !ob2d_get(c,r.a[6],0x76,1,value))return false;r.d[0]=0xfff80000U;am_byte(r.d[1],value);return am_call(c,0x443d2,0x2d6be);
    case 0x2d6be:am_swap(r.d[0]);am_swap(r.d[1]);if(!am_pop(c,4,value))return false;r.a[0]=value;return am_call(c,0x49214,0x2d6ca); // SWAP D0; SWAP D1; MOVEA.L (A7)+,A0; JSR 49214.l.
    // ---- 2d6e6: 28ae child of 2d69c. MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); MOVE.W #204,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x2d6e6:
        if(!ob2d_put(c,r.a[6],0x20,2,0xe2) || !am_read(c,OB2D_BANK_94,4,value) || !ob2d_put(c,r.a[6],0x22,4,value))return false;
        return ob2d_sound(c,0x204,0x2d702);
    // MOVEA.L c(A6),A0; MOVE.L 36(A0),D0; MOVE.L D0,36(A6); MOVE.L 3a(A0),D0; MOVE.L D0,3a(A6); MOVE.L #18000,D0; MOVE.B 76(A0),D1; ADDI.B #80,D1; JSR 443d2.l.
    case 0x2d71e:
        if(!ob2d_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob2d_get(c,r.a[0],0x36,4,value) || !ob2d_put(c,r.a[6],0x36,4,value) || !ob2d_get(c,r.a[0],0x3a,4,value) || !ob2d_put(c,r.a[6],0x3a,4,value))return false;
        if(!ob2d_get(c,r.a[0],0x76,1,other))return false;r.d[0]=0x18000;am_byte(r.d[1],other+0x80U);return am_call(c,0x443d2,0x2d746);
    // MOVEA.L c(A6),A0; MOVE.L D0,78(A6); MOVE.L D1,7c(A6); JSR 49a58.l.
    case 0x2d746:
        if(!ob2d_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob2d_put(c,r.a[6],0x78,4,r.d[0]) || !ob2d_put(c,r.a[6],0x7c,4,r.d[1]))return false;return am_call(c,0x49a58,0x2d758);
    case 0x2d758:r.pc=(r.d[0]&0x8000U)!=0U?0x2d75e:0x2d764;return true;       // TST.W D0; BPL.W 2d764.
    case 0x2d75e:if(!ob2d_setbit(c,r.a[6],0x15,0,true))return false;r.pc=0x2d764;return true;   // BSET.B #0,15(A6).
    case 0x2d764:r.pc=(r.d[0]&0x80U)!=0U?0x2d76a:0x2d770;return true;         // TST.B D0; BPL.W 2d770.
    case 0x2d76a:if(!ob2d_setbit(c,r.a[6],0x15,1,true))return false;r.pc=0x2d770;return true;   // BSET.B #1,15(A6).
    case 0x2d776:if(!ob2d_install(c,0x2d77e))return false;return am_return(c);  // MOVE.L #2d77e,(A6); RTS.
    // MOVEA.L 4(A6),A0; D0 = ((42(A0) - 42) ASR 7) + 78 -> ADD.L 36(A6); D0 = ((46(A0) - 46) ASR 7) + 7c -> ADD.L 3a(A6); JSR 43ea4.l.
    case 0x2d77e:
        if(!ob2d_get(c,r.a[6],0x4,4,value))return false;r.a[0]=value;
        if(!ob2d_get(c,r.a[0],0x42,4,value) || !ob2d_get(c,r.a[6],0x42,4,other))return false;r.d[0]=ob2d_asr_l(value-other,7);
        if(!ob2d_get(c,r.a[6],0x78,4,value))return false;r.d[0]+=value;
        if(!ob2d_get(c,r.a[6],0x36,4,value) || !ob2d_put(c,r.a[6],0x36,4,value+r.d[0]))return false;
        if(!ob2d_get(c,r.a[0],0x46,4,value) || !ob2d_get(c,r.a[6],0x46,4,other))return false;r.d[0]=ob2d_asr_l(value-other,7);
        if(!ob2d_get(c,r.a[6],0x7c,4,value))return false;r.d[0]+=value;
        if(!ob2d_get(c,r.a[6],0x3a,4,value) || !ob2d_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;return am_call(c,0x43ea4,0x2d7ac);
    case 0x2d7b2:return ob2d_carry(c,0x2d7bc,0x2d7b6);                       // BCC.W 2d7bc (C returned by 49fc6).
    default:return am_error(c,"unsupported animation objects b2d PC");
    }
}
}
