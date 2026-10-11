#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code.
const std::uint32_t OU9_POINTER_LIST=0x46994;  // 469a0 MOVE.L #46994,54e2(A5) (LONG list ended by a zero LONG, fixed ROM, live bus)
const std::uint32_t OU9_WORK=0x108000;         // 469d8 LEA 108000.L,A5
const std::uint32_t OU9_DEFAULT_TERRAIN=0x10d38e; // 46a90/46baa LEA 10d38e.L,A1
const std::uint32_t OU9_SLOT_STRIDE=0x2c;      // MULU.W #2c / LEA -2c(An),An (slot table 54e6(A5), 8 slots)
bool ou9_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou9_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Two's complement WORD view (explicit, no implementation-defined conversion).
std::int32_t ou9_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
// ORI.W #mask,d16(A5) (read-modify-write).
bool ou9_or_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t mask) {
    std::uint32_t value=0;if(!ou9_get(c,c.s.a[5],displacement,2,value))return false;
    return ou9_put(c,c.s.a[5],displacement,2,(value|mask)&65535U);
}
// ADDI.B #k,d16(A5); returns the BYTE carry.
bool ou9_add_byte(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t k,bool& carry) {
    std::uint32_t value=0;if(!ou9_get(c,c.s.a[5],displacement,1,value))return false;
    const std::uint32_t sum=(value&255U)+k;carry=sum>255U;return ou9_put(c,c.s.a[5],displacement,1,sum&255U);
}
// CLR.B 54e0(A5); MOVE.W #ffff,54de(A5) (46a32 and 46a4c).
bool ou9_reset_step(AnimationMachineContext& c) {
    return ou9_put(c,c.s.a[5],0x54e0,1,0) && ou9_put(c,c.s.a[5],0x54de,2,0xffff);
}
// SUB.L low_src,low; SUBX.L high_src,high (X from the SUB.L borrow). Returns the Z after SUBX: SUBX only clears Z on a
// non-zero result, so Z is set when both LONG results are zero.
bool ou9_sub_pair(std::uint32_t& low,std::uint32_t& high,std::uint32_t low_src,std::uint32_t high_src) {
    const std::uint32_t x=low_src>low?1U:0U;
    low=(low-low_src)&0xffffffffU;high=(high-high_src-x)&0xffffffffU;
    return low==0U && high==0U;
}
// SWAP D0; SWAP D1; CLR.W D0; CLR.W D1; ADD.L 42(A6),D0; ADD.L 46(A6),D1; LEA 538e(A5),A1; SUB.L 14(A1),D0; SUB.L 18(A1),D1.
bool ou9_slot_origin(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    am_swap(r.d[0]);am_swap(r.d[1]);am_word(r.d[0],0);am_word(r.d[1],0);
    if(!ou9_get(c,r.a[6],0x42,4,value))return false;r.d[0]=(r.d[0]+value)&0xffffffffU;
    if(!ou9_get(c,r.a[6],0x46,4,value))return false;r.d[1]=(r.d[1]+value)&0xffffffffU;
    r.a[1]=am_index(r.a[5],0x538e);
    if(!ou9_get(c,r.a[1],0x14,4,value))return false;r.d[0]=(r.d[0]-value)&0xffffffffU;
    if(!ou9_get(c,r.a[1],0x18,4,value))return false;r.d[1]=(r.d[1]-value)&0xffffffffU;
    return true;
}
// DBRA Dn,loop_pc (WORD counter; falls through to exit_pc at -1).
void ou9_dbra(AnimationMachineState& r,std::uint32_t& counter,std::uint32_t loop_pc,std::uint32_t exit_pc) {
    const std::uint32_t next=(counter-1U)&65535U;am_word(counter,next);r.pc=next!=65535U?loop_pc:exit_pc;
}
// OR.B (A1)+,Dn; DBRA counter (471ec/471fa scan loops).
bool ou9_or_scan(AnimationMachineContext& c,std::uint32_t& accumulator,std::uint32_t& counter,std::uint32_t loop_pc,std::uint32_t exit_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!am_read(c,r.a[1],1,value))return false;
    r.a[1]=(r.a[1]+1U)&0xffffffffU;am_byte(accumulator,(accumulator|value)&255U);ou9_dbra(r,counter,loop_pc,exit_pc);return true;
}
// MOVE.W 7c(A6),86(A6); ...; MOVE.L #callback,(A6) (then the installed callback).
bool ou9_restart_timer(AnimationMachineContext& c,bool clear_flag,std::uint32_t callback) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ou9_get(c,r.a[6],0x7c,2,value) || !ou9_put(c,r.a[6],0x86,2,value))return false;
    if(clear_flag && !ou9_put(c,r.a[6],0x88,1,0))return false;
    if(!am_write(c,r.a[6],4,callback))return false;r.pc=callback;return true;
}
// MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.L (interpreter animation list).
bool ou9_animation(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L #76852,A0; MOVE.W #a,D0; JSR 28ae.L (fade_card object creation of the child 76852).
bool ou9_spawn(AnimationMachineContext& c,std::uint32_t return_pc) {
    c.s.a[0]=0x76852;am_word(c.s.d[0],0xa);return am_call(c,0x28ae,return_pc);
}
}
// Objects F4 U09 (150 block starts): the C6 terrain search 469d8 (U08a 43eb8/447be/4483a, U08b 468e0/4683c/461ec and U11 45176
// are boundaries without an executor here), the pointer list walk 469a0/469ae (LONG list 46994 through the live bus, then the
// overlap check 47134 and the overlap slot walk 47212), the slot registration 4706c/47070 (cleanup 43e22/43e38, then the
// frame_helpers 46f52; TRAP 470e6 is a boundary) and the object callback 7670e/76718 with its installed callbacks 76768, 7678a,
// 767b6, 767c6 and 767ec (U02 8ebe, U08a 49274 boundary, interpreter 49f8c/49fc6, cleanup 43e34, fade_card 28ae/2a00, U05
// 1ab02). The SUBX blocks 46a3c/46b54 compute X inside the block. The only C consumer across blocks is 76a08 (C returned by 1ab02).
// U09 reads work RAM and the fixed ROM list 46994 and writes no port.
bool animation_objects_u09_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool carry=false;
    switch(r.pc) {
    // ---- 469a0: MOVE.L #46994,54e2(A5); JMP 47134.L.
    case 0x469a0:if(!ou9_put(c,r.a[5],0x54e2,4,OU9_POINTER_LIST))return false;r.pc=0x47134;return true;
    // ---- 469ae: MOVEA.L 54e2(A5),A3.
    case 0x469ae:if(!ou9_get(c,r.a[5],0x54e2,4,value))return false;r.a[3]=value;r.pc=0x469b2;return true;
    // MOVEA.L (A3)+,A1; CMPA.W #0,A1; BEQ 469d2.
    case 0x469b2:
        if(!am_read(c,r.a[3],4,value))return false;r.a[3]=(r.a[3]+4U)&0xffffffffU;r.a[1]=value;
        r.pc=value==0U?0x469d2:0x469bc;return true;
    // MOVE.L A3,54e2(A5); MOVEA.L 2e(A1),A2; CMPA.W #0,A2; BEQ 469b2.
    case 0x469bc:
        if(!ou9_put(c,r.a[5],0x54e2,4,r.a[3]) || !ou9_get(c,r.a[1],0x2e,4,value))return false;r.a[2]=value;
        r.pc=value==0U?0x469b2:0x469ca;return true;
    case 0x469ca:if(!ou9_get(c,r.a[2],2,2,value))return false;r.pc=value==0U?0x469b2:0x469d0;return true; // TST.W 2(A2); BEQ.
    case 0x469d0:case 0x470a8:case 0x76a12:return am_return(c);         // RTS.
    case 0x469d2:r.pc=0x47212;return true;                              // JMP 47212.L.

    // ---- 469d8: LEA 108000.L,A5; MOVEQ #0,D7; MOVE.W D7,54aa(A5); MOVE.B D7,54c6(A5); MOVE.B D7,54e0(A5); MOVE.W D7,54de(A5);
    // MOVE.L #ffffffff,54c2(A5); MOVE.L D7,54d4(A5); MOVE.L #160,54d8(A5); MOVE.L #80000000,54d0(A5); MOVEA.W #0,A1;
    // JSR 43eb8.L (U08a boundary).
    case 0x469d8:
        r.a[5]=OU9_WORK;r.d[7]=0;
        if(!ou9_put(c,r.a[5],0x54aa,2,0) || !ou9_put(c,r.a[5],0x54c6,1,0) || !ou9_put(c,r.a[5],0x54e0,1,0) ||
           !ou9_put(c,r.a[5],0x54de,2,0) || !ou9_put(c,r.a[5],0x54c2,4,0xffffffffU) || !ou9_put(c,r.a[5],0x54d4,4,0) ||
           !ou9_put(c,r.a[5],0x54d8,4,0x160) || !ou9_put(c,r.a[5],0x54d0,4,0x80000000U))return false;
        r.a[1]=0;return am_call(c,0x43eb8,0x46a16);
    case 0x46a16:r.a[0]=r.a[1];r.pc=0x46a18;return true;               // MOVEA.L A1,A0.
    case 0x46a18:if(!ou9_get(c,r.a[5],0x54c2,2,value))return false;r.pc=(value&0x8000U)?0x46a64:0x46a20;return true; // TST.W; BMI.
    case 0x46a20:if(!ou9_get(c,r.a[5],0x54de,2,value))return false;r.pc=value?0x46a5a:0x46a28;return true;           // TST.W; BNE.
    case 0x46a28:if(!ou9_add_byte(c,0x54e0,4,carry))return false;r.pc=carry?0x46a32:0x46a3c;return true; // ADDI.B #4; BCC 46a3c.
    case 0x46a32:if(!ou9_reset_step(c))return false;r.pc=0x46a3c;return true;
    // MOVE.L 54c8(A5),D4; MOVE.L 54cc(A5),D5; SUB.L D2,D4; SUBX.L D3,D5; BNE 46a56.
    case 0x46a3c:
        if(!ou9_get(c,r.a[5],0x54c8,4,value))return false;r.d[4]=value;
        if(!ou9_get(c,r.a[5],0x54cc,4,value))return false;r.d[5]=value;
        r.pc=ou9_sub_pair(r.d[4],r.d[5],r.d[2],r.d[3])?0x46a4c:0x46a56;return true;
    case 0x46a4c:if(!ou9_reset_step(c))return false;r.pc=0x46a56;return true;
    case 0x46a56:r.pc=0x46a64;return true;                              // BRA 46a64.
    case 0x46a5a:if(!ou9_add_byte(c,0x54e0,0x20,carry))return false;r.pc=carry?0x46a86:0x46a64;return true; // ADDI.B #20; BCS 46a86.
    // MOVE.L D2,54c8(A5); MOVE.L D3,54cc(A5); CLR.B 54c6(A5); BSR 469a0.
    case 0x46a64:
        if(!ou9_put(c,r.a[5],0x54c8,4,r.d[2]) || !ou9_put(c,r.a[5],0x54cc,4,r.d[3]) || !ou9_put(c,r.a[5],0x54c6,1,0))return false;
        return am_call(c,0x469a0,0x46a74);
    case 0x46a74:return am_call(c,0x468e0,0x46a78);                     // BSR 468e0 (U08b boundary).
    // SUB.L D0,D2; SUB.L D1,D3; TST.B D6; BNE 46b6e.
    case 0x46a78:
        r.d[2]=(r.d[2]-r.d[0])&0xffffffffU;r.d[3]=(r.d[3]-r.d[1])&0xffffffffU;r.pc=(r.d[6]&255U)?0x46b6e:0x46a82;return true;
    case 0x46a82:r.pc=0x46b78;return true;                              // BRA 46b78.
    // ORI.W #80,54aa(A5); MOVEQ #0,D2; MOVEQ #0,D3; LEA 10d38e.L,A1; BRA 46bde.
    case 0x46a86:if(!ou9_or_word(c,0x54aa,0x80))return false;r.d[2]=0;r.d[3]=0;r.a[1]=OU9_DEFAULT_TERRAIN;r.pc=0x46bde;return true;
    // MOVEM.L D0-D1,54ba(A5); MOVE.L D2,-(A7); MOVE.L D3,-(A7); BSR 4683c (U08b boundary).
    case 0x46a9a:
        if(!ou9_put(c,r.a[5],0x54ba,4,r.d[0]) || !ou9_put(c,r.a[5],0x54be,4,r.d[1]) || !am_push(c,4,r.d[2]) || !am_push(c,4,r.d[3]))
            return false;
        return am_call(c,0x4683c,0x46aa8);
    // MOVE.W 54b0(A5),D7; MOVEQ #0,D2; MOVEQ #-1,D3; TST.B 549d(A5); BNE 46abe.
    case 0x46aa8:
        if(!ou9_get(c,r.a[5],0x54b0,2,value))return false;am_word(r.d[7],value);r.d[2]=0;r.d[3]=0xffffffffU;
        if(!ou9_get(c,r.a[5],0x549d,1,value))return false;r.pc=value?0x46abe:0x46ab8;return true;
    // ADD.L (A7),D3; ADD.L 4(A7),D2 (the saved D3 and D2).
    case 0x46ab8:
        if(!am_read(c,r.a[7],4,value))return false;r.d[3]=(r.d[3]+value)&0xffffffffU;
        if(!ou9_get(c,r.a[7],4,4,value))return false;r.d[2]=(r.d[2]+value)&0xffffffffU;r.pc=0x46abe;return true;
    case 0x46abe:return am_call(c,0x4483a,0x46ac2);                     // BSR 4483a (U08a boundary).
    case 0x46ac2:r.pc=(r.d[7]&65535U)==0x160U?0x46ad4:0x46aca;return true; // CMPI.W #160,D7; BEQ 46ad4.
    case 0x46aca:return am_call(c,0x45176,0x46ace);                     // BSR 45176 (U11 boundary).
    case 0x46ace:r.pc=(r.d[6]&0x80000000U)?0x46ad4:0x46b3a;return true; // TST.L D6; BPL 46b3a.
    // SWAP D0; SWAP D1; SUBQ.W #8,D1; BSR 447be (U08a boundary).
    case 0x46ad4:am_swap(r.d[0]);am_swap(r.d[1]);am_word(r.d[1],r.d[1]-8U);return am_call(c,0x447be,0x46ade);
    // MOVE.W D6,54b2(A5); MOVE.W 54ae(A5),D4; MOVE.W D7,54ae(A5); CMPI.W #174,D4; BNE 46afe.
    case 0x46ade:
        if(!ou9_put(c,r.a[5],0x54b2,2,r.d[6]&65535U) || !ou9_get(c,r.a[5],0x54ae,2,value))return false;am_word(r.d[4],value);
        if(!ou9_put(c,r.a[5],0x54ae,2,r.d[7]&65535U))return false;r.pc=(r.d[4]&65535U)!=0x174U?0x46afe:0x46af2;return true;
    case 0x46af2:r.pc=(r.d[7]&65535U)!=0x174U?0x46afe:0x46afa;return true; // CMPI.W #174,D7; BNE 46afe.
    case 0x46afa:am_word(r.d[7],0x160);r.pc=0x46afe;return true;        // MOVE.W #160,D7.
    case 0x46afe:r.pc=(r.d[7]&65535U)==0x178U?0x46b0c:0x46b04;return true; // CMPI.W #178,D7; BEQ 46b0c.
    case 0x46b04:r.pc=(r.d[7]&65535U)!=0x17cU?0x46b16:0x46b0c;return true; // CMPI.W #17c,D7; BNE 46b16.
    case 0x46b0c:am_word(r.d[7],0x160);if(!ou9_or_word(c,0x54aa,0x400))return false;r.pc=0x46b16;return true; // MOVE.W; ORI.W #400.
    // MOVE.W D7,54b0(A5); ADDQ.W #8,D1; SWAP D1; SWAP D0; CMPI.W #160,D7; BEQ 46b54.
    case 0x46b16:
        if(!ou9_put(c,r.a[5],0x54b0,2,r.d[7]&65535U))return false;am_word(r.d[1],r.d[1]+8U);am_swap(r.d[1]);am_swap(r.d[0]);
        r.pc=(r.d[7]&65535U)==0x160U?0x46b54:0x46b28;return true;
    case 0x46b28:return am_call(c,0x4483a,0x46b2c);                     // BSR 4483a (U08a boundary).
    case 0x46b2c:return am_call(c,0x45176,0x46b30);                     // BSR 45176 (U11 boundary).
    case 0x46b30:r.d[6]=(r.d[6]+0x80000U)&0xffffffffU;r.pc=(r.d[6]&0x80000000U)?0x46b54:0x46b3a;return true; // ADDI.L; BMI 46b54.
    // CMP.L 54d0(A5),D6; BHI 46b54 (unsigned D6 > LONG).
    case 0x46b3a:if(!ou9_get(c,r.a[5],0x54d0,4,value))return false;r.pc=r.d[6]>value?0x46b54:0x46b42;return true;
    // MOVE.W 54b2(A5),54dc(A5); MOVE.L D6,54d0(A5); MOVE.L D7,54d8(A5); MOVE.L A0,54d4(A5).
    case 0x46b42:
        if(!ou9_get(c,r.a[5],0x54b2,2,value) || !ou9_put(c,r.a[5],0x54dc,2,value) || !ou9_put(c,r.a[5],0x54d0,4,r.d[6]) ||
           !ou9_put(c,r.a[5],0x54d8,4,r.d[7]) || !ou9_put(c,r.a[5],0x54d4,4,r.a[0]))return false;
        r.pc=0x46b54;return true;
    // MOVE.L (A7)+,D5; MOVE.L (A7)+,D4; MOVE.L D0,D2; MOVE.L D1,D3; MOVEM.L 54ba(A5),D0-D1; SUB.L D0,D2; SUB.L D1,D3;
    // SUB.L D2,D4; SUBX.L D3,D5; BEQ 46b78.
    case 0x46b54:
        if(!am_pop(c,4,r.d[5]) || !am_pop(c,4,r.d[4]))return false;r.d[2]=r.d[0];r.d[3]=r.d[1];
        if(!ou9_get(c,r.a[5],0x54ba,4,value))return false;r.d[0]=value;
        if(!ou9_get(c,r.a[5],0x54be,4,value))return false;r.d[1]=value;
        r.d[2]=(r.d[2]-r.d[0])&0xffffffffU;r.d[3]=(r.d[3]-r.d[1])&0xffffffffU;
        r.pc=ou9_sub_pair(r.d[4],r.d[5],r.d[2],r.d[3])?0x46b78:0x46b6e;return true;
    // MOVE.L A0,54c2(A5); MOVE.B #ff,54c6(A5).
    case 0x46b6e:if(!ou9_put(c,r.a[5],0x54c2,4,r.a[0]) || !ou9_put(c,r.a[5],0x54c6,1,0xff))return false;r.pc=0x46b78;return true;
    case 0x46b78:return am_call(c,0x469ae,0x46b7c);                     // BSR 469ae.
    case 0x46b7c:if(!ou9_get(c,r.a[5],0x54c2,4,value))return false;r.pc=r.a[1]==value?0x46b9c:0x46b84;return true; // CMPA.L; BEQ.
    case 0x46b84:return am_call(c,0x43eb8,0x46b8a);                     // JSR 43eb8.L (U08a boundary).
    case 0x46b8a:r.a[0]=r.a[1];r.pc=r.a[0]!=0U?0x46a9a:0x46b94;return true; // MOVEA.L A1,A0; CMPA.W #0,A0; BNE 46a9a.
    case 0x46b94:if(!ou9_get(c,r.a[5],0x54c6,1,value))return false;r.pc=value?0x46a18:0x46b9c;return true; // TST.B; BNE 46a18.
    // MOVEA.W #0,A1; CMPI.B #1,54a0(A5); BEQ 46bb0.
    case 0x46b9c:r.a[1]=0;if(!ou9_get(c,r.a[5],0x54a0,1,value))return false;r.pc=value==1U?0x46bb0:0x46baa;return true;
    case 0x46baa:r.a[1]=OU9_DEFAULT_TERRAIN;r.pc=0x46bb0;return true;   // LEA 10d38e.L,A1.
    // MOVE.L 54d0(A5),D6; BMI 46bde; BEQ 46bc6 (bundled 46bb8).
    case 0x46bb0:
        if(!ou9_get(c,r.a[5],0x54d0,4,value))return false;r.d[6]=value;
        r.pc=(value&0x80000000U)?0x46bde:(value==0U?0x46bc6:0x46bbc);return true;
    case 0x46bbc:if(!ou9_get(c,r.a[5],0x549d,1,value))return false;r.pc=value==0U?0x46bde:0x46bc4;return true; // TST.B; BEQ 46bde.
    case 0x46bc4:r.d[3]=(r.d[3]-r.d[6])&0xffffffffU;r.pc=0x46bc6;return true; // SUB.L D6,D3.
    // ORI.W #1,54aa(A5); TST.W 54dc(A5); BEQ 46bda.
    case 0x46bc6:
        if(!ou9_or_word(c,0x54aa,1) || !ou9_get(c,r.a[5],0x54dc,2,value))return false;r.pc=value==0U?0x46bda:0x46bd4;return true;
    case 0x46bd4:if(!ou9_or_word(c,0x54aa,0x100))return false;r.pc=0x46bda;return true; // ORI.W #100,54aa(A5).
    case 0x46bda:if(!ou9_get(c,r.a[5],0x54d4,4,value))return false;r.a[1]=value;r.pc=0x46bde;return true; // MOVEA.L 54d4(A5),A1.
    case 0x46bde:return am_call(c,0x43eb8,0x46be4);                     // JSR 43eb8.L (U08a boundary).
    // MOVEA.L A1,A0; ADD.L D2,D0; ADD.L D3,D1; MOVE.L 54d8(A5),D7; BSR 461ec (U08b boundary).
    case 0x46be4:
        r.a[0]=r.a[1];r.d[0]=(r.d[0]+r.d[2])&0xffffffffU;r.d[1]=(r.d[1]+r.d[3])&0xffffffffU;
        if(!ou9_get(c,r.a[5],0x54d8,4,value))return false;r.d[7]=value;return am_call(c,0x461ec,0x46bf2);
    // MOVE.W 54aa(A5),D6; MOVE.W 54ac(A5),D4; RTS.
    case 0x46bf2:
        if(!ou9_get(c,r.a[5],0x54aa,2,value))return false;am_word(r.d[6],value);
        if(!ou9_get(c,r.a[5],0x54ac,2,value))return false;am_word(r.d[4],value);return am_return(c);

    // ---- 4706c: MOVEQ #0,D0; MOVEQ #0,D1.
    case 0x4706c:r.d[0]=0;r.d[1]=0;r.pc=0x47070;return true;
    case 0x47070:r.pc=r.a[0]!=0U?0x4707c:0x47078;return true;           // CMPA.W #0,A0; BNE 4707c.
    case 0x47078:r.a[0]=0xffffffffU;r.pc=0x4707c;return true;           // MOVEA.W #ffff,A0.
    // MOVEQ #0,D2; MOVE.B 6c(A6),D2; CMPI.B #ff,D2; BNE 470de.
    case 0x4707c:r.d[2]=0;if(!ou9_get(c,r.a[6],0x6c,1,value))return false;am_byte(r.d[2],value);r.pc=value!=0xffU?0x470de:0x4708a;return true;
    case 0x4708a:r.a[4]=am_index(r.a[5],0x561a);r.d[7]=7;r.pc=0x47090;return true; // LEA 561a(A5),A4; MOVEQ #7,D7.
    case 0x47090:if(!ou9_get(c,r.a[4],0x26,2,value))return false;r.pc=(value&0x8000U)?0x47098:0x470a0;return true; // TST.W; BPL.
    case 0x47098:if(!ou9_get(c,r.a[4],0x2a,2,value))return false;r.pc=value==0U?0x470aa:0x470a0;return true;        // TST.W; BEQ.
    case 0x470a0:r.a[4]=am_index(r.a[4],0x10000U-OU9_SLOT_STRIDE);ou9_dbra(r,r.d[7],0x47090,0x470a8);return true; // LEA -2c(A4); DBRA.
    // MOVE.B D7,6c(A6); MOVE.W D7,567c(A5); MOVE.L A0,26(A4); (slot origin); MOVEA.L A4,A0; JSR 43e22.L.
    case 0x470aa:
        if(!ou9_put(c,r.a[6],0x6c,1,r.d[7]&255U) || !ou9_put(c,r.a[5],0x567c,2,r.d[7]&65535U) || !ou9_put(c,r.a[4],0x26,4,r.a[0]) ||
           !ou9_slot_origin(c))return false;
        r.a[0]=r.a[4];return am_call(c,0x43e22,0x470da);
    case 0x470da:case 0x47130:r.pc=0x46f52;return true;                // BRA 46f52 (frame_helpers).
    case 0x470de:r.pc=(r.d[2]&65535U)<8U?0x470e8:0x470e6;return true;   // CMPI.W #8,D2; BCS 470e8 (else the TRAP 470e6 boundary).
    // MOVE.W D2,567c(A5); MULU.W #2c,D2; LEA 54e6(A5),A4; ADDA.W D2,A4; MOVE.L A0,26(A4); (slot origin); MOVEA.L A4,A0;
    // MOVE.L D0,(A0); MOVE.L D1,4(A0); MOVE.L A1,10(A0); CLR.L 8(A0); CLR.L c(A0); JSR 43e38.L.
    case 0x470e8:
        if(!ou9_put(c,r.a[5],0x567c,2,r.d[2]&65535U))return false;
        r.d[2]=(r.d[2]&65535U)*OU9_SLOT_STRIDE;r.a[4]=am_index(am_index(r.a[5],0x54e6),r.d[2]&65535U);
        if(!ou9_put(c,r.a[4],0x26,4,r.a[0]) || !ou9_slot_origin(c))return false;r.a[0]=r.a[4];
        if(!am_write(c,r.a[0],4,r.d[0]) || !ou9_put(c,r.a[0],4,4,r.d[1]) || !ou9_put(c,r.a[0],0x10,4,r.a[1]) ||
           !ou9_put(c,r.a[0],8,4,0) || !ou9_put(c,r.a[0],0xc,4,0))return false;
        return am_call(c,0x43e38,0x47130);

    // ---- 47134: MOVEM.L D0-D3/A0,-(A7) (A0 highest; memory from low to high D0..D3, A0); MOVEQ #0,D7; MOVE.B 549c(A5),D7;
    // CMPI.B #3,D7; BCS 4714a.
    case 0x47134:
        if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.d[3]) || !am_push(c,4,r.d[2]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;
        r.d[7]=0;if(!ou9_get(c,r.a[5],0x549c,1,value))return false;am_byte(r.d[7],value);r.pc=value<3U?0x4714a:0x47146;return true;
    case 0x47146:am_byte(r.d[7],2);r.pc=0x4714a;return true;            // MOVE.B #2,D7.
    // LEA 5666(A5),A1; ADDA.W D7,A1; MOVE.B (A1),567a(A5); BEQ 47206.
    case 0x4714a:
        r.a[1]=am_index(am_index(r.a[5],0x5666),r.d[7]&65535U);if(!am_read(c,r.a[1],1,value) || !ou9_put(c,r.a[5],0x567a,1,value))return false;
        r.pc=value==0U?0x47206:0x47158;return true;
    // ADD.L D0,D2; ADD.L D1,D3; CMPA.W #0,A0; BEQ 47174.
    case 0x47158:r.d[2]=(r.d[2]+r.d[0])&0xffffffffU;r.d[3]=(r.d[3]+r.d[1])&0xffffffffU;r.pc=r.a[0]==0U?0x47174:0x47164;return true;
    // ADD.L 1c(A0),D0; ADD.L 20(A0),D1; ADD.L 14(A0),D2; ADD.L 18(A0),D3.
    case 0x47164:
        if(!ou9_get(c,r.a[0],0x1c,4,value))return false;r.d[0]=(r.d[0]+value)&0xffffffffU;
        if(!ou9_get(c,r.a[0],0x20,4,value))return false;r.d[1]=(r.d[1]+value)&0xffffffffU;
        if(!ou9_get(c,r.a[0],0x14,4,value))return false;r.d[2]=(r.d[2]+value)&0xffffffffU;
        if(!ou9_get(c,r.a[0],0x18,4,value))return false;r.d[3]=(r.d[3]+value)&0xffffffffU;r.pc=0x47174;return true;
    // SWAP D0..D3; CMP.W D2,D0; BLE 47184 (signed WORD D0 <= D2).
    case 0x47174:
        am_swap(r.d[0]);am_swap(r.d[1]);am_swap(r.d[2]);am_swap(r.d[3]);
        r.pc=ou9_signed_word(r.d[0])<=ou9_signed_word(r.d[2])?0x47184:0x47182;return true;
    case 0x47182:value=r.d[2];r.d[2]=r.d[0];r.d[0]=value;r.pc=0x47184;return true; // EXG D2,D0.
    case 0x47184:r.pc=ou9_signed_word(r.d[1])<=ou9_signed_word(r.d[3])?0x4718c:0x4718a;return true; // CMP.W D3,D1; BLE 4718c.
    case 0x4718a:value=r.d[3];r.d[3]=r.d[1];r.d[1]=value;r.pc=0x4718c;return true; // EXG D3,D1.
    // MOVE.W #ffa0,D4; MOVE.W #19f,D5; CMP.W D5,D0; BGT 47202.
    case 0x4718c:
        am_word(r.d[4],0xffa0);am_word(r.d[5],0x19f);r.pc=ou9_signed_word(r.d[0])>ou9_signed_word(r.d[5])?0x47202:0x4719a;return true;
    case 0x4719a:r.pc=ou9_signed_word(r.d[2])<ou9_signed_word(r.d[4])?0x47202:0x471a0;return true; // CMP.W D4,D2; BLT 47202.
    // SUB.W D4,D0; BGE 471a8 (N xor V clear: signed D0 >= D4).
    case 0x471a0:
        r.pc=ou9_signed_word(r.d[0])>=ou9_signed_word(r.d[4])?0x471a8:0x471a6;am_word(r.d[0],r.d[0]-r.d[4]);return true;
    case 0x471a6:am_word(r.d[0],0);r.pc=0x471a8;return true;            // CLR.W D0.
    case 0x471a8:r.pc=ou9_signed_word(r.d[2])<=ou9_signed_word(r.d[5])?0x471b0:0x471ae;return true; // CMP.W D5,D2; BLE 471b0.
    case 0x471ae:am_word(r.d[2],r.d[5]);r.pc=0x471b0;return true;       // MOVE.W D5,D2.
    // SUB.W D4,D2; MOVE.W #80,D4; MOVE.W #27f,D5; CMP.W D5,D1; BGT 47202.
    case 0x471b0:
        am_word(r.d[2],r.d[2]-r.d[4]);am_word(r.d[4],0x80);am_word(r.d[5],0x27f);
        r.pc=ou9_signed_word(r.d[1])>ou9_signed_word(r.d[5])?0x47202:0x471c0;return true;
    case 0x471c0:r.pc=ou9_signed_word(r.d[3])<ou9_signed_word(r.d[4])?0x47202:0x471c6;return true; // CMP.W D4,D3; BLT 47202.
    case 0x471c6:
        r.pc=ou9_signed_word(r.d[1])>=ou9_signed_word(r.d[4])?0x471ce:0x471cc;am_word(r.d[1],r.d[1]-r.d[4]);return true; // SUB.W; BGE.
    case 0x471cc:am_word(r.d[1],0);r.pc=0x471ce;return true;            // CLR.W D1.
    case 0x471ce:r.pc=ou9_signed_word(r.d[3])<=ou9_signed_word(r.d[5])?0x471d6:0x471d4;return true; // CMP.W D5,D3; BLE 471d6.
    case 0x471d4:am_word(r.d[3],r.d[5]);r.pc=0x471d6;return true;       // MOVE.W D5,D3.
    // SUB.W D4,D3; LSR.W #5,D0..D3; SUB.W D0,D2; SUB.W D1,D3; LEA 5646(A5),A1; ADDA.W D0,A1; MOVEQ #0,D7.
    case 0x471d6:
        am_word(r.d[3],r.d[3]-r.d[4]);
        am_word(r.d[0],(r.d[0]&65535U)>>5);am_word(r.d[1],(r.d[1]&65535U)>>5);am_word(r.d[2],(r.d[2]&65535U)>>5);
        am_word(r.d[3],(r.d[3]&65535U)>>5);am_word(r.d[2],r.d[2]-r.d[0]);am_word(r.d[3],r.d[3]-r.d[1]);
        r.a[1]=am_index(am_index(r.a[5],0x5646),r.d[0]&65535U);r.d[7]=0;r.pc=0x471ec;return true;
    case 0x471ec:return ou9_or_scan(c,r.d[7],r.d[2],0x471ec,0x471f2);   // OR.B (A1)+,D7; DBRA D2,471ec.
    case 0x471f2:r.a[1]=am_index(am_index(r.a[5],0x5656),r.d[1]&65535U);r.d[6]=0;r.pc=0x471fa;return true; // LEA; ADDA.W D1; MOVEQ.
    case 0x471fa:return ou9_or_scan(c,r.d[6],r.d[3],0x471fa,0x47200);   // OR.B (A1)+,D6; DBRA D3,471fa.
    case 0x47200:am_byte(r.d[7],r.d[7]&r.d[6]&255U);r.pc=0x47202;return true; // AND.B D6,D7.
    case 0x47202:                                                        // AND.B D7,567a(A5).
        if(!ou9_get(c,r.a[5],0x567a,1,value) || !ou9_put(c,r.a[5],0x567a,1,value&r.d[7]&255U))return false;r.pc=0x47206;return true;
    // MOVE.W #8,567c(A5); MOVEM.L (A7)+,D0-D3/A0; RTS.
    case 0x47206:
        if(!ou9_put(c,r.a[5],0x567c,2,8) || !am_pop(c,4,r.d[0]) || !am_pop(c,4,r.d[1]) || !am_pop(c,4,r.d[2]) || !am_pop(c,4,r.d[3]) ||
           !am_pop(c,4,r.a[0]))return false;
        return am_return(c);

    // ---- 47212: MOVE.W 567c(A5),D7; BEQ 4727a.
    case 0x47212:if(!ou9_get(c,r.a[5],0x567c,2,value))return false;am_word(r.d[7],value);r.pc=value==0U?0x4727a:0x4721a;return true;
    // LEA 54e6(A5),A1; MOVE.W D7,D5; MULU.W #2c,D5; ADDA.W D5,A1; MOVE.B 567a(A5),D6.
    case 0x4721a:
        r.a[1]=am_index(r.a[5],0x54e6);r.d[5]=(r.d[7]&65535U)*OU9_SLOT_STRIDE;r.a[1]=am_index(r.a[1],r.d[5]&65535U);
        if(!ou9_get(c,r.a[5],0x567a,1,value))return false;am_byte(r.d[6],value);r.pc=0x4722a;return true;
    case 0x4722a:r.pc=(r.d[6]&255U)==0U?0x4727a:0x47230;return true;    // TST.B D6; BEQ 4727a.
    // SUBQ.W #1,D7; LEA -2c(A1),A1; ADD.B D6,D6; BCC 4722a.
    case 0x47230:
        am_word(r.d[7],r.d[7]-1U);r.a[1]=am_index(r.a[1],0x10000U-OU9_SLOT_STRIDE);value=(r.d[6]&255U)*2U;am_byte(r.d[6],value);
        r.pc=value>255U?0x4723a:0x4722a;return true;
    case 0x4723a:if(!ou9_get(c,r.a[1],0x26,2,value))return false;r.pc=(value&0x8000U)?0x4722a:0x47240;return true; // TST.W; BMI.
    // MOVE.B 6c(A6),D5; BMI 47270.
    case 0x47240:if(!ou9_get(c,r.a[6],0x6c,1,value))return false;am_byte(r.d[5],value);r.pc=(value&0x80U)?0x47270:0x47248;return true;
    case 0x47248:r.pc=(r.d[7]&255U)==(r.d[5]&255U)?0x4722a:0x4724c;return true; // CMP.B D5,D7; BEQ 4722a.
    // LEA 54e6(A5),A4; ANDI.W #ff,D5; MULU.W #2c,D5; ADDA.W D5,A4; MOVEA.L 10(A1),A3.
    case 0x4724c:
        r.a[4]=am_index(r.a[5],0x54e6);am_word(r.d[5],r.d[5]&0xffU);r.d[5]=(r.d[5]&65535U)*OU9_SLOT_STRIDE;
        r.a[4]=am_index(r.a[4],r.d[5]&65535U);if(!ou9_get(c,r.a[1],0x10,4,value))return false;r.a[3]=value;r.pc=0x4725e;return true;
    case 0x4725e:r.pc=r.a[3]==0U?0x47270:0x47266;return true;           // CMPA.W #0,A3; BEQ 47270.
    case 0x47266:r.pc=r.a[3]==r.a[4]?0x4722a:0x4726a;return true;       // CMPA.L A4,A3; BEQ 4722a.
    case 0x4726a:if(!ou9_get(c,r.a[3],0x10,4,value))return false;r.a[3]=value;r.pc=0x4725e;return true; // MOVEA.L 10(A3),A3; BRA.
    // MOVE.W D7,567c(A5); MOVE.B D6,567a(A5); RTS.
    case 0x47270:if(!ou9_put(c,r.a[5],0x567c,2,r.d[7]&65535U) || !ou9_put(c,r.a[5],0x567a,1,r.d[6]&255U))return false;return am_return(c);
    // MOVE.W #0,567c(A5); MOVEA.L #0,A1; RTS.
    case 0x4727a:if(!ou9_put(c,r.a[5],0x567c,2,0))return false;r.a[1]=0;return am_return(c);

    // ---- 7670e/76718 (callbacks): MOVE.B #0/#1,89(A6).
    case 0x7670e:if(!ou9_put(c,r.a[6],0x89,1,0))return false;r.pc=0x7671e;return true;
    case 0x76718:if(!ou9_put(c,r.a[6],0x89,1,1))return false;r.pc=0x7671e;return true;
    case 0x7671e:am_word(r.d[0],0xc53);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x7672c); // MOVE.W #c53,D0; MOVE.B #0,D1; JSR 8ebe.L.
    // MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); TST.W 76(A6); BEQ 76746.
    case 0x7672c:
        if(!ou9_put(c,r.a[6],0x68,2,0x8820) || !ou9_put(c,r.a[6],0x1e,2,0x8820) || !ou9_get(c,r.a[6],0x76,2,value))return false;
        r.pc=value==0U?0x76746:0x76740;return true;
    case 0x76740:                                                        // BSET.B #0,15(A6).
        if(!ou9_get(c,r.a[6],0x15,1,value) || !ou9_put(c,r.a[6],0x15,1,(value|1U)&255U))return false;r.pc=0x76746;return true;
    case 0x76746:return am_call(c,0x49274,0x7674c);                     // JSR 49274.L (U08a boundary).
    // MOVE.W #b,20(A6); MOVEA.L #76aa0,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x7674c:if(!ou9_put(c,r.a[6],0x20,2,0xb))return false;return ou9_animation(c,0x76aa0,0x76762);
    case 0x76762:if(!am_write(c,r.a[6],4,0x76768))return false;r.pc=0x76768;return true; // MOVE.L #76768,(A6).
    case 0x76768:case 0x767b6:case 0x767ec:return am_call(c,0x43e34,r.pc+6U); // JSR 43e34.L (installed callback entries).
    case 0x7676e:case 0x767bc:case 0x767f2:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.L.
    // MOVE.W 5418(A5),D0; CMP.W 78(A6),D0; BLT 76786 (signed WORD).
    case 0x76774:
        if(!ou9_get(c,r.a[5],0x5418,2,value))return false;am_word(r.d[0],value);if(!ou9_get(c,r.a[6],0x78,2,value))return false;
        r.pc=ou9_signed_word(r.d[0])<ou9_signed_word(value)?0x76786:0x76780;return true;
    case 0x76780:if(!am_write(c,r.a[6],4,0x7678a))return false;r.pc=0x76786;return true; // MOVE.L #7678a,(A6).
    case 0x76786:case 0x7684a:r.pc=0x7684e;return true;                 // BRA 7684e.
    case 0x7678a:return ou9_animation(c,0x76aac,0x7679a);               // (callback) MOVEA.L #76aac,A1; ...; JSR 49f8c.L.
    case 0x7679a:return ou9_spawn(c,0x767aa);
    case 0x767aa:return ou9_restart_timer(c,false,0x767b6);             // MOVE.W 7c(A6),86(A6); MOVE.L #767b6,(A6).
    case 0x767c2:r.pc=0x76818;return true;                              // BRA 76818.
    // (callback) MOVE.W #c,82(A6); MOVEA.L #76852,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0x767c6:if(!ou9_put(c,r.a[6],0x82,2,0xc))return false;return ou9_spawn(c,0x767dc);
    case 0x767dc:return ou9_restart_timer(c,true,0x767ec);              // MOVE.W 7c(A6),86(A6); SF.B 88(A6); MOVE.L #767ec,(A6).
    case 0x767f8:if(!ou9_get(c,r.a[6],0x82,2,value))return false;r.pc=(value&0x8000U)?0x76818:0x76800;return true; // TST.W; BMI.
    // SUBQ.W #1,82(A6); BNE 76818.
    case 0x76800:
        if(!ou9_get(c,r.a[6],0x82,2,value))return false;value=(value-1U)&65535U;if(!ou9_put(c,r.a[6],0x82,2,value))return false;
        r.pc=value!=0U?0x76818:0x76808;return true;
    case 0x76808:return ou9_animation(c,0x76b8c,0x76818);
    // SUBQ.W #1,86(A6); SCS.B D0; EXT.W D0; EOR.W D0,86(A6); CMPI.W #1,7a(A6); BLS 7684a (unsigned).
    case 0x76818:
        if(!ou9_get(c,r.a[6],0x86,2,value))return false;am_byte(r.d[0],(value&65535U)==0U?0xff:0);
        if(!ou9_put(c,r.a[6],0x86,2,(value-1U)&65535U))return false;
        am_word(r.d[0],(r.d[0]&0x80U)?(0xff00U|(r.d[0]&255U)):(r.d[0]&255U));
        if(!ou9_get(c,r.a[6],0x86,2,value) || !ou9_put(c,r.a[6],0x86,2,(value^r.d[0])&65535U) || !ou9_get(c,r.a[6],0x7a,2,value))
            return false;
        r.pc=(value&65535U)<=1U?0x7684a:0x7682e;return true;
    // TST.W 86(A6); SEQ.B D0; TST.B 88(A6); SNE.B D1; AND.B D0,D1; BEQ 7684a.
    case 0x7682e:
        if(!ou9_get(c,r.a[6],0x86,2,value))return false;am_byte(r.d[0],value==0U?0xff:0);
        if(!ou9_get(c,r.a[6],0x88,1,value))return false;am_byte(r.d[1],value!=0U?0xff:0);
        am_byte(r.d[1],r.d[0]&r.d[1]&255U);r.pc=(r.d[1]&255U)==0U?0x7684a:0x76840;return true;
    // SUBQ.W #1,7a(A6); MOVE.L #767c6,(A6).
    case 0x76840:
        if(!ou9_get(c,r.a[6],0x7a,2,value) || !ou9_put(c,r.a[6],0x7a,2,(value-1U)&65535U) || !am_write(c,r.a[6],4,0x767c6))return false;
        r.pc=0x7684a;return true;
    case 0x7684e:r.pc=0x769fc;return true;                              // BRA 769fc.
    case 0x769fc:r.a[0]=0x76a14;return am_call(c,0x1ab02,0x76a08);      // LEA 76a14.L,A0; JSR 1ab02.L.
    // BCC 76a12 (C returned by 1ab02).
    case 0x76a08:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u09 caller requires known carry");
        r.pc=r.carry==AnimationCarryClear?0x76a12:0x76a0c;return true;
    case 0x76a0c:r.pc=0x2a00;return true;                               // JMP 2a00.L.
    default:return am_error(c,"unsupported animation objects u09 PC");
    }
}
}
