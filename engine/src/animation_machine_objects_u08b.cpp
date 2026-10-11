#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool ou8b_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou8b_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// ORI.W #bits,d16(A5): WORD read-OR-write.
bool ou8b_ori(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t bits) {
    std::uint32_t value=0;
    return ou8b_get(c,c.s.a[5],displacement,2,value) && ou8b_put(c,c.s.a[5],displacement,2,(value|bits)&65535U);
}
std::uint32_t ou8b_low(std::uint32_t value) {return value&65535U;}
bool ou8b_negative(std::uint32_t value) {return (value>>31)!=0;}
// LONG N/Z/V of ADD.L s,d (r = d+s) and CMP.L/SUB.L s,d (r = d-s).
struct Ou8bFlags {bool n,z,v;};
Ou8bFlags ou8b_add(std::uint32_t d,std::uint32_t s) {
    const std::uint32_t r=d+s;Ou8bFlags f;f.n=ou8b_negative(r);f.z=r==0;f.v=((~(s^d)&(d^r))>>31)!=0;return f;
}
Ou8bFlags ou8b_cmp(std::uint32_t d,std::uint32_t s) {
    const std::uint32_t r=d-s;Ou8bFlags f;f.n=ou8b_negative(r);f.z=r==0;f.v=(((s^d)&(d^r))>>31)!=0;return f;
}
bool ou8b_ge(const Ou8bFlags& f) {return f.n==f.v;}          // BGE
bool ou8b_le(const Ou8bFlags& f) {return f.z || f.n!=f.v;}   // BLE
// SUBQ.W #8,D4; BCS: C is the WORD borrow.
bool ou8b_subq8(std::uint32_t& d4) {
    const std::uint32_t w=ou8b_low(d4);am_word(d4,w-8U);return w<8U;
}
// ADDI.L #80000000,D6; SUBX.L D4,D4; SUB.L D4,D6: X of the ADDI is the carry out (the original bit 31 of D6), D4 = 0-0-X.
void ou8b_subx(AnimationMachineState& r) {
    const bool x=ou8b_negative(r.d[6]);r.d[6]+=0x80000000U;r.d[4]=x?0xffffffffU:0U;r.d[6]-=r.d[4];
}
// MOVEM.L 2e(A6),D0-D3/A0 (2e 32 36 3a 3e).
bool ou8b_load_position(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t v[5];
    for(unsigned int i=0;i<5;++i)if(!ou8b_get(c,r.a[6],0x2eU+4U*i,4,v[i]))return false;
    for(unsigned int i=0;i<4;++i)r.d[i]=v[i];r.a[0]=v[4];return true;
}
// MOVEM.L D0-D3/A0,2e(A6).
bool ou8b_store_position(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    for(unsigned int i=0;i<4;++i)if(!ou8b_put(c,r.a[6],0x2eU+4U*i,4,r.d[i]))return false;
    return ou8b_put(c,r.a[6],0x3e,4,r.a[0]);
}
// MOVE.L D0,D4; ANDI.L #7ffff,D4; SUB.L D6,D0; SUB.L D6,D4; SWAP D4; SUBQ.W #8,D4; BCS borrow_pc (464ce / 46572).
void ou8b_step_down(AnimationMachineState& r,std::uint32_t borrow_pc,std::uint32_t next_pc) {
    r.d[4]=r.d[0]&0x7ffffU;r.d[0]-=r.d[6];r.d[4]-=r.d[6];am_swap(r.d[4]);r.pc=ou8b_subq8(r.d[4])?borrow_pc:next_pc;
}
// The three copies of the 447be result handling (bases 4640c, 464ea, 4658e; the same block offsets in each copy).
bool ou8b_result(AnimationMachineContext& c,std::uint32_t base,std::uint32_t offset) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(offset) {
    // MOVE.W D6,54b2(A5); MOVE.W 54ae(A5),D4; MOVE.W D7,54ae(A5); CMPI.W #178,D4; BNE +2c.
    case 0x00:
        if(!ou8b_put(c,r.a[5],0x54b2,2,ou8b_low(r.d[6])) || !ou8b_get(c,r.a[5],0x54ae,2,value))return false;am_word(r.d[4],value);
        if(!ou8b_put(c,r.a[5],0x54ae,2,ou8b_low(r.d[7])))return false;r.pc=base+(ou8b_low(r.d[4])!=0x178U?0x2cU:0x14U);return true;
    case 0x14:if(!ou8b_get(c,r.a[5],0x54a4,1,value))return false;r.pc=base+(value?0x24U:0x1cU);return true; // TST.B 54a4(A5); BNE +24.
    case 0x1c:r.pc=base+(ou8b_low(r.d[7])<0x160U?0x3cU:0x24U);return true;  // CMPI.W #160,D7; BCS +3c.
    case 0x24:if(!ou8b_get(c,r.a[5],0x54a5,1,value))return false;r.pc=base+(value?0x3cU:0x2cU);return true; // TST.B 54a5(A5); BNE +3c.
    case 0x2c:r.pc=base+(ou8b_low(r.d[4])!=0x17cU?0x46U:0x34U);return true; // CMPI.W #17c,D4; BNE +46.
    case 0x34:if(!ou8b_get(c,r.a[5],0x54a5,1,value))return false;r.pc=base+(value?0x3cU:0x46U);return true; // TST.B 54a5(A5); BEQ +46.
    case 0x3c:am_word(r.d[7],0x160);if(!ou8b_ori(c,0x54aa,0x10))return false;r.pc=base+0x46U;return true; // MOVE.W #160,D7; ORI.W #10,54aa(A5).
    case 0x46:r.pc=base+(ou8b_low(r.d[4])!=0x174U?0x5aU:0x4eU);return true; // CMPI.W #174,D4; BNE +5a.
    case 0x4e:r.pc=base+(ou8b_low(r.d[7])!=0x174U?0x5aU:0x56U);return true; // CMPI.W #174,D7; BNE +5a.
    case 0x56:am_word(r.d[7],0x160);r.pc=base+0x5aU;return true;             // MOVE.W #160,D7.
    case 0x5a:r.pc=base+(ou8b_low(r.d[7])==0x178U?0x68U:0x60U);return true; // CMPI.W #178,D7; BEQ +68.
    case 0x60:r.pc=base+(ou8b_low(r.d[7])!=0x17cU?0x72U:0x68U);return true; // CMPI.W #17c,D7; BNE +72.
    case 0x68:am_word(r.d[7],0x160);if(!ou8b_ori(c,0x54aa,0x400))return false;r.pc=base+0x72U;return true; // MOVE.W #160,D7; ORI.W #400.
    // MOVE.W D7,54b0(A5); SWAP D0; SWAP D1; MOVEQ #0,D4 (-> +7c).
    case 0x72:if(!ou8b_put(c,r.a[5],0x54b0,2,ou8b_low(r.d[7])))return false;am_swap(r.d[0]);am_swap(r.d[1]);r.d[4]=0;r.pc=base+0x7cU;return true;
    default:return am_error(c,"unsupported animation objects u08b PC");
    }
}
bool ou8b_result_block(std::uint32_t offset) {
    return offset==0x00 || offset==0x14 || offset==0x1c || offset==0x24 || offset==0x2c || offset==0x34 || offset==0x3c ||
        offset==0x46 || offset==0x4e || offset==0x56 || offset==0x5a || offset==0x60 || offset==0x68 || offset==0x72;
}
// SWAP D7; ADD.W d16(A1),D7; SWAP D7 (the high WORD of D7 gets the WORD added).
bool ou8b_add_high(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t value=0;if(!ou8b_get(c,c.s.a[1],displacement,2,value))return false;
    am_swap(c.s.d[7]);am_word(c.s.d[7],c.s.d[7]+value);am_swap(c.s.d[7]);return true;
}
// MOVEQ #0,D7; MOVE.W d16(A1),D7; SWAP D7.
bool ou8b_load_high(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t value=0;if(!ou8b_get(c,c.s.a[1],displacement,2,value))return false;c.s.d[7]=(value&65535U)<<16;return true;
}
// ADD.L D5,54b6(A5); BPL 4688a.
bool ou8b_accumulate(AnimationMachineContext& c,std::uint32_t minus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ou8b_get(c,r.a[5],0x54b6,4,value))return false;value+=r.d[5];if(!ou8b_put(c,r.a[5],0x54b6,4,value))return false;
    r.pc=ou8b_negative(value)?minus_pc:0x4688a;return true;
}
// MOVE.B #0,10d49d.L; MOVEM.L 2e(A6),D0-D3/A0; JSR target.L.
bool ou8b_enter(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    return am_write(c,0x10d49d,1,0) && ou8b_load_position(c) && am_call(c,target,return_pc);
}
// BTST #bit,D6; SNE D5; ANDI #mask,D5 (BYTE, or WORD for 4bf4a); OR.B D5 into target.
void ou8b_flag(AnimationMachineState& r,unsigned int bit,std::uint32_t mask,bool word,std::uint32_t& target) {
    am_byte(r.d[5],((r.d[6]>>bit)&1U)?0xffU:0U);
    if(word)am_word(r.d[5],r.d[5]&mask);else am_byte(r.d[5],r.d[5]&mask);
    am_byte(target,target|(r.d[5]&255U));
}
}
// Objects F4 U08b (165 block starts, the second part of the U08 split, groups C4/C6): the slope WORD 461ec (PC-relative data read
// 461f2+D7.W through the bus), the terrain step 46372 and loop 4683c, the screen clamp 468e0, the move-lock bits 4bb22, the terrain
// condition reset 4bc44, and the C4 object updates 4be34 / 4be82 with the shared tail 4bf0a / 4bf16. SUBX (46398 / 464ac) takes X
// from the ADDI.L inside the same block. 4beec recomputes the Z of the 4be9a ADD.B D7,D7 from D7.B (its only predecessor is the
// 4be9c BCC). U08b has no carry consumer across blocks and no known-carry producer. The callees 44ade 4578a 45b12 4662e 469d8
// 492c8 4b8e8 4bce0 have no executor.
bool animation_objects_u08b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- 461ec: MOVE.W 461f2(PC,D7.W),D7; RTS (ROM data through the bus).
    case 0x461ec:if(!am_read(c,am_index(0x461f2,r.d[7]),2,value))return false;am_word(r.d[7],value);return am_return(c);

    // ---- 46372: TST.L D2; BNE 4637c / MOVEQ #0,D6; RTS.
    case 0x46372:r.pc=r.d[2]!=0?0x4637c:0x46378;return true;
    case 0x46378:r.d[6]=0;return am_return(c);
    case 0x4637c:r.pc=ou8b_low(r.d[7])==0x160U?0x463d8:0x46384;return true; // CMPI.W #160,D7; BEQ 463d8.
    case 0x46384:return am_call(c,0x44ade,0x46388);                          // BSR 44ade (boundary).
    case 0x46388:r.d[6]-=0x80000000U;r.pc=r.d[6]==0?0x463d8:0x46392;return true; // SUBI.L #80000000,D6; BEQ 463d8.
    // ADD.L D2,D6; BVC 463d8.
    case 0x46392:{const Ou8bFlags f=ou8b_add(r.d[6],r.d[2]);r.d[6]+=r.d[2];r.pc=f.v?0x46398:0x463d8;return true;}
    // ADDI.L #80000000,D6; SUBX.L D4,D4; SUB.L D4,D6; SUB.L D6,D2; EXG D2,D6; ADD.L D6,D0; BSR 4483a.
    case 0x46398:
        ou8b_subx(r);r.d[2]-=r.d[6];value=r.d[2];r.d[2]=r.d[6];r.d[6]=value;r.d[0]+=r.d[6];return am_call(c,0x4483a,0x463ac);
    case 0x463ac:r.pc=ou8b_low(r.d[7])==0x160U?0x463c0:0x463b4;return true; // CMPI.W #160,D7; BEQ 463c0.
    case 0x463b4:return am_call(c,0x45b12,0x463b8);                          // BSR 45b12 (boundary).
    case 0x463b8:return am_call(c,0x4578a,0x463bc);                          // BSR 4578a (boundary).
    case 0x463bc:r.d[6]=0xffffffffU;return am_return(c);                     // MOVEQ #-1,D6; RTS.
    case 0x463c0:if(!ou8b_get(c,r.a[5],0x54b4,1,value))return false;r.pc=value?0x463d8:0x463c8;return true; // TST.B 54b4(A5); BNE.
    // ORI.W #40,54aa(A5); MOVE.B #ff,54b4(A5); MOVEQ #-1,D6; RTS.
    case 0x463c8:if(!ou8b_ori(c,0x54aa,0x40) || !ou8b_put(c,r.a[5],0x54b4,1,0xff))return false;r.d[6]=0xffffffffU;return am_return(c);
    // MOVEQ #8,D4; SWAP D4; MOVE.L D2,D5; CMP.L D4,D5; BLE 463e6.
    case 0x463d8:r.d[4]=0x80000U;r.d[5]=r.d[2];r.pc=ou8b_le(ou8b_cmp(r.d[5],r.d[4]))?0x463e6:0x463e4;return true;
    case 0x463e4:r.d[5]=r.d[4];r.pc=0x463e6;return true; // MOVE.L D4,D5.
    case 0x463e6:{const Ou8bFlags f=ou8b_add(r.d[4],r.d[5]);r.d[4]+=r.d[5];r.pc=ou8b_ge(f)?0x463ee:0x463ec;return true;} // ADD.L D5,D4; BGE.
    case 0x463ec:r.d[5]-=r.d[4];r.pc=0x463ee;return true; // SUB.L D4,D5.
    // MOVE.L D5,-(A7); MOVE.L D0,D4; ANDI.L #7ffff,D4; ADD.L D5,D0; ADD.L D5,D4; SWAP D4; SUBQ.W #8,D4; BCS 46488.
    case 0x463ee:
        if(!am_push(c,4,r.d[5]))return false;r.d[4]=r.d[0]&0x7ffffU;r.d[0]+=r.d[5];r.d[4]+=r.d[5];am_swap(r.d[4]);
        r.pc=ou8b_subq8(r.d[4])?0x46488:0x46404;return true;
    case 0x46404:am_swap(r.d[0]);am_swap(r.d[1]);return am_call(c,0x447be,0x4640c); // SWAP D0; SWAP D1; BSR 447be.
    // MOVE.L (A7)+,D5; TST.W D4; BNE 46624.
    case 0x46488:if(!am_pop(c,4,value))return false;r.d[5]=value;r.pc=ou8b_low(r.d[4])!=0?0x46624:0x46490;return true;
    case 0x46490:r.pc=ou8b_low(r.d[7])==0x160U?0x46624:0x46498;return true; // CMPI.W #160,D7; BEQ 46624.
    case 0x46498:return am_call(c,0x44ade,0x4649c);                          // BSR 44ade (boundary).
    case 0x4649c:r.d[6]-=0x80000000U;r.pc=r.d[6]==0?0x46624:0x464a6;return true; // SUBI.L #80000000,D6; BEQ 46624.
    case 0x464a6:r.pc=ou8b_cmp(r.d[6],r.d[5]).v?0x464ac:0x46624;return true;   // CMP.L D5,D6; BVC 46624.
    // ADDI.L #80000000,D6; SUBX.L D4,D4; SUB.L D4,D6; SUB.L D5,D2; ADD.L D6,D2; BSR 4483a.
    case 0x464ac:ou8b_subx(r);r.d[2]-=r.d[5];r.d[2]+=r.d[6];return am_call(c,0x4483a,0x464be);
    case 0x464be:r.pc=ou8b_low(r.d[7])==0x160U?0x4656a:0x464c6;return true; // CMPI.W #160,D7; BEQ 4656a.
    case 0x464c6:return am_call(c,0x45b12,0x464ca);                          // BSR 45b12 (boundary).
    case 0x464ca:return am_call(c,0x4578a,0x464ce);                          // BSR 4578a (boundary).
    case 0x464ce:ou8b_step_down(r,0x46566,0x464e2);return true;
    case 0x464e2:am_swap(r.d[0]);am_swap(r.d[1]);return am_call(c,0x447be,0x464ea); // SWAP D0; SWAP D1; BSR 447be.
    case 0x46566:r.d[6]=0xffffffffU;return am_return(c);                     // MOVEQ #-1,D6; RTS.
    case 0x4656a:if(!ou8b_get(c,r.a[5],0x54b4,1,value))return false;r.pc=value?0x46614:0x46572;return true; // TST.B 54b4(A5); BNE.
    case 0x46572:ou8b_step_down(r,0x4660a,0x46586);return true;
    case 0x46586:am_swap(r.d[0]);am_swap(r.d[1]);return am_call(c,0x447be,0x4658e); // SWAP D0; SWAP D1; BSR 447be.
    case 0x4660a:if(!ou8b_put(c,r.a[5],0x54b4,1,0xff))return false;r.d[6]=0xffffffffU;return am_return(c); // MOVE.B #ff,54b4; MOVEQ #-1.
    // SUB.L D6,D2; ORI.W #40,54aa(A5); CLR.B 54b4(A5); MOVEQ #0,D6; RTS.
    case 0x46614:r.d[2]-=r.d[6];if(!ou8b_ori(c,0x54aa,0x40) || !ou8b_put(c,r.a[5],0x54b4,1,0))return false;r.d[6]=0;return am_return(c);
    // SUB.L D5,D2; CLR.B 54b4(A5); MOVEQ #0,D6; RTS.
    case 0x46624:r.d[2]-=r.d[5];if(!ou8b_put(c,r.a[5],0x54b4,1,0))return false;r.d[6]=0;return am_return(c);

    // ---- 4683c: MOVE.W 54de(A5),-(A7); SWAP D0; SWAP D1; BSR 447be.
    case 0x4683c:
        if(!ou8b_get(c,r.a[5],0x54de,2,value) || !am_push(c,2,value))return false;am_swap(r.d[0]);am_swap(r.d[1]);
        return am_call(c,0x447be,0x46848);
    // MOVE.W D7,54ae(A5); CMPI.W #178,D7; BEQ 4685a.
    case 0x46848:if(!ou8b_put(c,r.a[5],0x54ae,2,ou8b_low(r.d[7])))return false;r.pc=ou8b_low(r.d[7])==0x178U?0x4685a:0x46852;return true;
    case 0x46852:r.pc=ou8b_low(r.d[7])!=0x17cU?0x46864:0x4685a;return true; // CMPI.W #17c,D7; BNE 46864.
    case 0x4685a:am_word(r.d[7],0x160);if(!ou8b_ori(c,0x54aa,0x400))return false;r.pc=0x46864;return true; // MOVE.W #160,D7; ORI.W #400.
    // MOVE.W D7,54b0(A5); MOVE.W D6,54b2(A5); CLR.B 54b4(A5); SWAP D0; SWAP D1; CLR.L 54b6(A5); TST.L D3; BNE 4688a.
    case 0x46864:
        if(!ou8b_put(c,r.a[5],0x54b0,2,ou8b_low(r.d[7])) || !ou8b_put(c,r.a[5],0x54b2,2,ou8b_low(r.d[6])) ||
            !ou8b_put(c,r.a[5],0x54b4,1,0))return false;
        am_swap(r.d[0]);am_swap(r.d[1]);if(!ou8b_put(c,r.a[5],0x54b6,4,0))return false;r.pc=r.d[3]!=0?0x4688a:0x4687e;return true;
    case 0x4687e:r.pc=r.d[2]!=0?0x468b6:0x46884;return true; // TST.L D2; BNE 468b6.
    case 0x46884:if(!am_pop(c,2,value) || !ou8b_put(c,r.a[5],0x54de,2,value))return false;return am_return(c); // MOVE.W (A7)+,54de(A5); RTS.
    case 0x4688a:return am_call(c,0x4662e,0x4688e);                          // BSR 4662e (boundary).
    case 0x4688e:r.d[4]=r.d[2]|r.d[3];r.pc=r.d[4]==0?0x46884:0x46894;return true; // MOVE.L D2,D4; OR.L D3,D4; BEQ 46884.
    case 0x46894:r.pc=(r.d[6]&255U)==0?0x468a2:0x4689a;return true;          // TST.B D6; BEQ 468a2.
    case 0x4689a:if(!ou8b_put(c,r.a[5],0x54de,2,0))return false;r.pc=0x468b6;return true; // CLR.W 54de(A5); BRA 468b6.
    case 0x468a2:r.pc=r.d[3]==0?0x468b6:0x468a8;return true;                 // TST.L D3; BEQ 468b6.
    case 0x468a8:r.d[5]=r.d[2];r.pc=ou8b_negative(r.d[5])?0x468b0:0x468ae;return true; // MOVE.L D2,D5; BMI 468b0.
    case 0x468ae:r.d[5]=0U-r.d[5];r.pc=0x468b0;return true;                  // NEG.L D5.
    case 0x468b0:return ou8b_accumulate(c,0x468b6);                          // ADD.L D5,54b6(A5); BPL 4688a.
    case 0x468b6:return am_call(c,0x46372,0x468ba);                          // BSR 46372.
    case 0x468ba:r.d[4]=r.d[2]|r.d[3];r.pc=r.d[4]==0?0x46884:0x468c0;return true; // MOVE.L D2,D4; OR.L D3,D4; BEQ 46884.
    case 0x468c0:r.pc=(r.d[6]&255U)==0?0x468cc:0x468c6;return true;          // TST.B D6; BEQ 468cc.
    case 0x468c6:if(!ou8b_put(c,r.a[5],0x54de,2,0))return false;r.pc=0x4688a;return true; // CLR.W 54de(A5); BRA 4688a.
    case 0x468cc:r.pc=r.d[2]==0?0x4688a:0x468d0;return true;                 // TST.L D2; BEQ 4688a.
    case 0x468d0:r.d[5]=r.d[3];r.pc=ou8b_negative(r.d[5])?0x468d6:0x468d8;return true; // MOVE.L D3,D5; BPL 468d8.
    case 0x468d6:r.d[5]=0U-r.d[5];r.pc=0x468d8;return true;                  // NEG.L D5.
    case 0x468d8:return ou8b_accumulate(c,0x468de);                          // ADD.L D5,54b6(A5); BPL 4688a.
    case 0x468de:r.pc=0x468b6;return true;                                   // BRA 468b6.

    // ---- 468e0: MOVEA.L 54a6(A5),A1; MOVEQ #0,D6; ADD.L D0,D2; ADD.L D1,D3; TST.B 54a2(A5); BNE 46938.
    case 0x468e0:
        if(!ou8b_get(c,r.a[5],0x54a6,4,value))return false;r.a[1]=value;r.d[6]=0;r.d[2]+=r.d[0];r.d[3]+=r.d[1];
        if(!ou8b_get(c,r.a[5],0x54a2,1,value))return false;r.pc=value?0x46938:0x468f2;return true;
    // MOVE.L 53bc(A5),D4; ADD.L 53a2(A5),D4; MOVE.L D4,D5; SUB.L D4,D0; SUB.L D5,D2; MOVEQ #0,D7; MOVE.W (A1),D7; SWAP D7;
    // CMP.L D0,D7; BLE 4690e.
    case 0x468f2:
        if(!ou8b_get(c,r.a[5],0x53bc,4,value) || !ou8b_get(c,r.a[5],0x53a2,4,other))return false;r.d[4]=value+other;r.d[5]=r.d[4];
        r.d[0]-=r.d[4];r.d[2]-=r.d[5];if(!ou8b_load_high(c,0))return false;r.pc=ou8b_le(ou8b_cmp(r.d[7],r.d[0]))?0x4690e:0x4690c;return true;
    case 0x4690c:r.d[7]=r.d[0];r.pc=0x4690e;return true;                     // MOVE.L D0,D7.
    case 0x4690e:r.pc=ou8b_ge(ou8b_cmp(r.d[2],r.d[7]))?0x4691a:0x46914;return true; // CMP.L D7,D2; BGE 4691a.
    case 0x46914:r.d[2]=r.d[7];am_byte(r.d[6],0xff);r.pc=0x4691a;return true; // MOVE.L D7,D2; MOVE.B #ff,D6.
    // SWAP D7; ADD.W 4(A1),D7; SWAP D7; CMP.L D0,D7; BGE 4692a.
    case 0x4691a:if(!ou8b_add_high(c,4))return false;r.pc=ou8b_ge(ou8b_cmp(r.d[7],r.d[0]))?0x4692a:0x46928;return true;
    case 0x46928:r.d[7]=r.d[0];r.pc=0x4692a;return true;                     // MOVE.L D0,D7.
    case 0x4692a:r.pc=ou8b_le(ou8b_cmp(r.d[2],r.d[7]))?0x46934:0x46930;return true; // CMP.L D7,D2; BLE 46934.
    case 0x46930:r.d[2]=r.d[7];r.d[6]=0xffffffffU;r.pc=0x46934;return true;  // MOVE.L D7,D2; MOVEQ #-1,D6.
    case 0x46934:r.d[0]+=r.d[4];r.d[2]+=r.d[5];r.pc=0x46938;return true;     // ADD.L D4,D0; ADD.L D5,D2.
    case 0x46938:if(!ou8b_get(c,r.a[5],0x54a3,1,value))return false;r.pc=value?0x46992:0x46940;return true; // TST.B 54a3(A5); BNE.
    // MOVE.L 53c0(A5),D4; ADD.L 53a6(A5),D4; MOVE.L D4,D5; SWAP D4; SUB.W 5404(A5),D4; ADD.W 5406(A5),D4; SWAP D4; SUB.L D4,D1;
    // SUB.L D5,D3; MOVEQ #0,D7; MOVE.W 2(A1),D7; SWAP D7; CMP.L D1,D7; BLE 4696a.
    case 0x46940:
        if(!ou8b_get(c,r.a[5],0x53c0,4,value) || !ou8b_get(c,r.a[5],0x53a6,4,other))return false;r.d[4]=value+other;r.d[5]=r.d[4];
        am_swap(r.d[4]);if(!ou8b_get(c,r.a[5],0x5404,2,value))return false;am_word(r.d[4],r.d[4]-value);
        if(!ou8b_get(c,r.a[5],0x5406,2,value))return false;am_word(r.d[4],r.d[4]+value);am_swap(r.d[4]);
        r.d[1]-=r.d[4];r.d[3]-=r.d[5];if(!ou8b_load_high(c,2))return false;r.pc=ou8b_le(ou8b_cmp(r.d[7],r.d[1]))?0x4696a:0x46968;return true;
    case 0x46968:r.d[7]=r.d[1];r.pc=0x4696a;return true;                     // MOVE.L D1,D7.
    case 0x4696a:r.pc=ou8b_ge(ou8b_cmp(r.d[3],r.d[7]))?0x46974:0x46970;return true; // CMP.L D7,D3; BGE 46974.
    case 0x46970:r.d[3]=r.d[7];r.d[6]=0xffffffffU;r.pc=0x46974;return true;  // MOVE.L D7,D3; MOVEQ #-1,D6.
    // SWAP D7; ADD.W 6(A1),D7; SWAP D7; CMP.L D1,D7; BGE 46984.
    case 0x46974:if(!ou8b_add_high(c,6))return false;r.pc=ou8b_ge(ou8b_cmp(r.d[7],r.d[1]))?0x46984:0x46982;return true;
    case 0x46982:r.d[7]=r.d[1];r.pc=0x46984;return true;                     // MOVE.L D1,D7.
    case 0x46984:r.pc=ou8b_le(ou8b_cmp(r.d[3],r.d[7]))?0x4698e:0x4698a;return true; // CMP.L D7,D3; BLE 4698e.
    case 0x4698a:r.d[3]=r.d[7];r.d[6]=0xffffffffU;r.pc=0x4698e;return true;  // MOVE.L D7,D3; MOVEQ #-1,D6.
    case 0x4698e:r.d[1]+=r.d[4];r.d[3]+=r.d[5];r.pc=0x46992;return true;     // ADD.L D4,D1; ADD.L D5,D3.
    case 0x46992:return am_return(c);                                       // RTS.

    // ---- 4bb22: MOVE.B 6d(A6),D7; BPL 4bb2c / RTS.
    case 0x4bb22:if(!ou8b_get(c,r.a[6],0x6d,1,value))return false;am_byte(r.d[7],value);r.pc=(value&0x80U)?0x4bb2a:0x4bb2c;return true;
    case 0x4bb2a:return am_return(c);
    case 0x4bb2c:value=r.d[7]&0x10U;r.d[7]&=~0x10U;r.pc=value==0?0x4bb3c:0x4bb34;return true; // BCLR #4,D7; BEQ 4bb3c.
    case 0x4bb34:r.pc=ou8b_negative(r.d[2])?0x4bb3a:0x4bb3c;return true;     // TST.L D2; BPL 4bb3c.
    case 0x4bb3a:r.d[2]=0;r.pc=0x4bb3c;return true;                          // MOVEQ #0,D2.
    case 0x4bb3c:value=r.d[7]&0x20U;r.d[7]&=~0x20U;r.pc=value==0?0x4bb4c:0x4bb44;return true; // BCLR #5,D7; BEQ 4bb4c.
    case 0x4bb44:r.pc=ou8b_negative(r.d[2])?0x4bb4c:0x4bb4a;return true;     // TST.L D2; BMI 4bb4c.
    case 0x4bb4a:r.d[2]=0;r.pc=0x4bb4c;return true;                          // MOVEQ #0,D2.
    case 0x4bb4c:if(!ou8b_put(c,r.a[6],0x6d,1,r.d[7]&255U))return false;return am_return(c); // MOVE.B D7,6d(A6); RTS.

    // ---- 4bc44: CLR.B 549f(A5); CLR.B 54a0(A5); MOVE.B #ff,54a2(A5); MOVE.B #ff,54a3(A5); MOVE.B #0,549d(A5);
    // MOVE.B #0,549e(A5); MOVE.B #2,549c(A5); BTST #4,15(A6); BEQ 4bc7a.
    case 0x4bc44:
        if(!ou8b_put(c,r.a[5],0x549f,1,0) || !ou8b_put(c,r.a[5],0x54a0,1,0) || !ou8b_put(c,r.a[5],0x54a2,1,0xff) ||
            !ou8b_put(c,r.a[5],0x54a3,1,0xff) || !ou8b_put(c,r.a[5],0x549d,1,0) || !ou8b_put(c,r.a[5],0x549e,1,0) ||
            !ou8b_put(c,r.a[5],0x549c,1,2) || !ou8b_get(c,r.a[6],0x15,1,value))return false;
        r.pc=(value&0x10U)?0x4bc74:0x4bc7a;return true;
    case 0x4bc74:if(!ou8b_put(c,r.a[5],0x549c,1,1))return false;r.pc=0x4bc7a;return true; // MOVE.B #1,549c(A5).
    case 0x4bc7a:if(!ou8b_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&0x08U)?0x4bc84:0x4bc8a;return true; // BTST #3,15(A6); BEQ.
    case 0x4bc84:if(!ou8b_put(c,r.a[5],0x549c,1,0))return false;r.pc=0x4bc8a;return true; // MOVE.B #0,549c(A5).
    // BTST #5,61(A6); SNE 54a4(A5); BTST #4,61(A6); SNE 54a5(A5); RTS.
    case 0x4bc8a:
        if(!ou8b_get(c,r.a[6],0x61,1,value) || !ou8b_put(c,r.a[5],0x54a4,1,(value&0x20U)?0xffU:0U))return false;
        if(!ou8b_get(c,r.a[6],0x61,1,value) || !ou8b_put(c,r.a[5],0x54a5,1,(value&0x10U)?0xffU:0U))return false;
        return am_return(c);

    // ---- 4be34: JSR 4bc44(PC) / MOVE.B #0,10d49d.L; MOVEM.L 2e(A6),D0-D3/A0; JSR 4bb22.L / BRA 4bf0a.
    case 0x4be34:return am_call(c,0x4bc44,0x4be38);
    case 0x4be38:return ou8b_enter(c,0x4bb22,0x4be4c);
    case 0x4be4c:r.pc=0x4bf0a;return true;
    // ---- 4be82: JSR 4bce0(PC) (boundary) / MOVE.B #0,10d49d.L; MOVEM.L 2e(A6),D0-D3/A0; JSR 4b8e8.L (boundary).
    case 0x4be82:return am_call(c,0x4bce0,0x4be86);
    case 0x4be86:return ou8b_enter(c,0x4b8e8,0x4be9a);
    // ADD.B D7,D7; BCC 4beec.
    case 0x4be9a:value=r.d[7]&255U;am_byte(r.d[7],value<<1);r.pc=(value&0x80U)?0x4bea0:0x4beec;return true;
    case 0x4bea0:return am_call(c,0x469d8,0x4bea6);                          // JSR 469d8.L (boundary, U09).
    // MOVE.L 36(A6),D2; MOVE.L 3a(A6),D3; MOVEA.L 3e(A6),A1; CMPA.W #0,A1; BEQ 4beca.
    case 0x4bea6:
        if(!ou8b_get(c,r.a[6],0x36,4,r.d[2]) || !ou8b_get(c,r.a[6],0x3a,4,r.d[3]) || !ou8b_get(c,r.a[6],0x3e,4,value))return false;
        r.a[1]=value;r.pc=r.a[1]==0?0x4beca:0x4beba;return true;
    // ADD.L 14(A1),D2; SUB.L 1c(A1),D2; ADD.L 18(A1),D3; SUB.L 20(A1),D3.
    case 0x4beba:
        if(!ou8b_get(c,r.a[1],0x14,4,value))return false;r.d[2]+=value;if(!ou8b_get(c,r.a[1],0x1c,4,value))return false;r.d[2]-=value;
        if(!ou8b_get(c,r.a[1],0x18,4,value))return false;r.d[3]+=value;if(!ou8b_get(c,r.a[1],0x20,4,value))return false;r.d[3]-=value;
        r.pc=0x4beca;return true;
    case 0x4beca:r.pc=r.a[0]==0?0x4bee2:0x4bed2;return true;                 // CMPA.W #0,A0; BEQ 4bee2.
    // SUB.L 14(A0),D2; ADD.L 1c(A0),D2; SUB.L 18(A0),D3; ADD.L 20(A0),D3.
    case 0x4bed2:
        if(!ou8b_get(c,r.a[0],0x14,4,value))return false;r.d[2]-=value;if(!ou8b_get(c,r.a[0],0x1c,4,value))return false;r.d[2]+=value;
        if(!ou8b_get(c,r.a[0],0x18,4,value))return false;r.d[3]-=value;if(!ou8b_get(c,r.a[0],0x20,4,value))return false;r.d[3]+=value;
        r.pc=0x4bee2;return true;
    case 0x4bee2:if(!ou8b_store_position(c))return false;r.pc=0x4bf16;return true; // MOVEM.L D0-D3/A0,2e(A6); BRA 4bf16.
    case 0x4beec:r.pc=(r.d[7]&255U)==0?0x4bf0a:0x4bef0;return true;          // BEQ 4bf0a (Z of the 4be9a ADD.B, from D7.B).
    case 0x4bef0:r.d[4]=0x40000U;r.pc=(r.d[7]&0x80U)?0x4befe:0x4befc;return true; // MOVE.L #40000,D4; TST.B D7; BMI 4befe.
    case 0x4befc:r.d[4]=0U-r.d[4];r.pc=0x4befe;return true;                  // NEG.L D4.
    // MOVE.L #60000,D3; NEG.L D2; ASR.L #1,D2; ADD.L D4,D2.
    case 0x4befe:r.d[3]=0x60000U;r.d[2]=0U-r.d[2];r.d[2]=(r.d[2]>>1)|(r.d[2]&0x80000000U);r.d[2]+=r.d[4];r.pc=0x4bf0a;return true;
    case 0x4bf0a:return am_call(c,0x469d8,0x4bf10);                          // JSR 469d8.L (boundary, U09).
    case 0x4bf10:if(!ou8b_store_position(c))return false;r.pc=0x4bf16;return true; // MOVEM.L D0-D3/A0,2e(A6).
    // ---- 4bf16: MOVE.B 15(A6),D0; MOVE.B 61(A6),D1; ANDI.B #5f,D0; ANDI.B #fc,D1; BTST #7,D6; BEQ 4bf38.
    case 0x4bf16:
        if(!ou8b_get(c,r.a[6],0x15,1,value) || !ou8b_get(c,r.a[6],0x61,1,other))return false;
        am_byte(r.d[0],value&0x5fU);am_byte(r.d[1],other&0xfcU);r.pc=(r.d[6]&0x80U)?0x4bf2e:0x4bf38;return true;
    // ORI.B #80,D1; MOVE.B #18,5e(A6).
    case 0x4bf2e:am_byte(r.d[1],r.d[1]|0x80U);if(!ou8b_put(c,r.a[6],0x5e,1,0x18))return false;r.pc=0x4bf38;return true;
    // BTST/SNE D5/ANDI/OR (bits 0..3 of D6 into D0/D1); MOVE.B D0,15(A6); MOVE.B D1,61(A6); MOVEM.L D4/D6-D7,-(A7); LSR.L #8,D7;
    // MOVE.W D7,6e(A6); JSR 43e34.L.
    case 0x4bf38:
        ou8b_flag(r,0,0x80,false,r.d[0]);ou8b_flag(r,1,0x20,true,r.d[0]);ou8b_flag(r,2,0x01,false,r.d[1]);ou8b_flag(r,3,0x02,false,r.d[1]);
        if(!ou8b_put(c,r.a[6],0x15,1,r.d[0]&255U) || !ou8b_put(c,r.a[6],0x61,1,r.d[1]&255U))return false;
        if(!am_push(c,4,r.d[7]) || !am_push(c,4,r.d[6]) || !am_push(c,4,r.d[4]))return false;
        r.d[7]>>=8;if(!ou8b_put(c,r.a[6],0x6e,2,ou8b_low(r.d[7])))return false;return am_call(c,0x43e34,0x4bf80);
    case 0x4bf80:if(!ou8b_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&0x80U)?0x4bf98:0x4bf8a;return true; // BTST #7,15(A6); BNE.
    case 0x4bf8a:return am_call(c,0x1aa3a,0x4bf90);                          // JSR 1aa3a.L.
    case 0x4bf90:am_word(r.d[0],r.d[0]&0xc8U);r.pc=ou8b_low(r.d[0])==0?0x4bf9e:0x4bf98;return true; // ANDI.W #c8,D0; BEQ 4bf9e.
    case 0x4bf98:return am_call(c,0x492c8,0x4bf9e);                          // JSR 492c8.L (boundary).
    // MOVEM.L (A7)+,D4/D6-D7; RTS.
    case 0x4bf9e:
        if(!am_pop(c,4,value))return false;r.d[4]=value;if(!am_pop(c,4,value))return false;r.d[6]=value;
        if(!am_pop(c,4,value))return false;r.d[7]=value;return am_return(c);
    default:
        if(r.pc>=0x4640c && r.pc<0x46488 && ou8b_result_block(r.pc-0x4640c))return ou8b_result(c,0x4640c,r.pc-0x4640c);
        if(r.pc>=0x464ea && r.pc<0x46566 && ou8b_result_block(r.pc-0x464ea))return ou8b_result(c,0x464ea,r.pc-0x464ea);
        if(r.pc>=0x4658e && r.pc<0x4660a && ou8b_result_block(r.pc-0x4658e))return ou8b_result(c,0x4658e,r.pc-0x4658e);
        return am_error(c,"unsupported animation objects u08b PC");
    }
}
}
