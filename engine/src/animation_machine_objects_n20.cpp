#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONGs (live bus, current PVC bank): animation records of the 736d2 family (id 3) and of the b9832 family (id 203 / 223).
const std::uint32_t ON20_BANK_3=0x2000d0;
const std::uint32_t ON20_BANK_203=0x2001d0;
const std::uint32_t ON20_BANK_223=0x2001e0;
bool on20_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on20_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Two's complement WORD as a signed number (no signed overflow in C++).
int on20_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<int>(value)-65536:static_cast<int>(value);
}
// MULU.W: 16 x 16 unsigned -> 32 (at most fffe0001).
std::uint32_t on20_mulu(std::uint32_t a,std::uint32_t b) {
    return (a&65535U)*(b&65535U);
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on20_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n20 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,(A6) then continue at next_pc.
bool on20_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// BTST.B #bit,displacement(A6): true when the bit is set.
bool on20_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on20_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// LEA 26(A6),A0; MOVE.W #id,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L offset(A1),A1;
// JSR 49f8c.L.
bool on20_animation(AnimationMachineContext& c,std::uint32_t bank,std::uint32_t id,std::uint32_t offset,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[6],0x26);
    if(!on20_put(c,0x20,2,id) || !am_read(c,bank,4,value) || !on20_put(c,0x22,4,value))return false;am_word(r.d[0],0x100);
    if(!on20_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],offset),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #d,D0; ADD.W 76(A6),D0; LEA 26(A6),A0; MOVE.W #223,20(A6); MOVE.L 2001e0.L,22(A6); LEA 26(A6),A0; MOVE.W D0,D1;
// ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 2001e0.L,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
bool on20_indexed_animation(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!on20_get(c,0x76,2,value))return false;am_word(r.d[0],(0xdU+value)&65535U);r.a[0]=am_index(r.a[6],0x26);
    if(!on20_put(c,0x20,2,0x223) || !am_read(c,ON20_BANK_223,4,value) || !on20_put(c,0x22,4,value))return false;
    am_word(r.d[1],(r.d[0]*4U)&65535U);if(!am_read(c,ON20_BANK_223,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);
    return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L #child,A0; MOVE.W #a,D0; JSR 28ae.L (the child callback is data here).
bool on20_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],0xa);return am_call(c,0x28ae,return_pc);
}
// MOVE.W 80(A6),D0; BNE.W (CMP.W 5418(A5),D0 branch) else the 1ab02 rectangle b982a.
bool on20_screen(AnimationMachineContext& c,std::uint32_t nonzero_pc,std::uint32_t zero_pc) {
    std::uint32_t value=0;if(!on20_get(c,0x80,2,value))return false;am_word(c.s.d[0],value);
    c.s.pc=(value&65535U)!=0U?nonzero_pc:zero_pc;return true;
}
// CMP.W 5418(A5),D0; BHI.W (unsigned D0.W > A5 WORD 5418).
bool on20_progress(AnimationMachineContext& c,std::uint32_t higher_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!am_read(c,am_index(c.s.a[5],0x5418),2,value))return false;
    c.s.pc=(c.s.d[0]&65535U)>(value&65535U)?higher_pc:other_pc;return true;
}
// MOVEA.L 84(A6),A0; CMPA.W #0,A0 (sign-extended 0: the full LONG); BEQ.W.
bool on20_pointer(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!on20_get(c,0x84,4,value))return false;c.s.a[0]=value;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// MOVE.L #value,D0; MOVE.L D0,3a(A6).
bool on20_speed(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    c.s.d[0]=value;if(!on20_put(c,0x3a,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #ba2fa,8c(A6); TST.B 7a(A6); BNE.W.
bool on20_table(AnimationMachineContext& c,std::uint32_t nonzero_pc,std::uint32_t zero_pc) {
    std::uint32_t value=0;if(!on20_put(c,0x8c,4,0xba2fa) || !on20_get(c,0x7a,1,value))return false;
    c.s.pc=(value&255U)!=0U?nonzero_pc:zero_pc;return true;
}
// MOVE.W 92/94(A6),D0; BEQ.W skip_pc / SUBQ.W #1,D0; MOVE.W D0,92/94(A6).
bool on20_count(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!on20_get(c,displacement,2,value))return false;am_word(c.s.d[0],value);
    c.s.pc=(value&65535U)==0U?zero_pc:other_pc;return true;
}
bool on20_decrement(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t next_pc) {
    am_word(c.s.d[0],(c.s.d[0]-1U)&65535U);if(!on20_put(c,displacement,2,c.s.d[0]&65535U))return false;c.s.pc=next_pc;return true;
}
}
// Objects F4 N20 (218 block starts): the stage event callback 736d2 with the installed callbacks 7377e 737ba 73800 7382e 73854 73882
// 7389e 738da 738fa 73928, the helpers 735b0 (tail) 735c6 7361a 7364e 73690 736a2 736c4 7394e 73992 and the shared function 49580
// (nearest player, computed C), and the stage event callback b9832 with the 28ae children b9c6e b9c80 and the installed b99be b9a36
// b9aae b9cde. Boundaries without an executor: cc778 and b9c0e (moved out of N20). The eleven BCC/BCS consumers read the C of 1ab02
// 49fc6 288c 49580 73690; 495d8 (CMPI.W #8000,D0; EORI.B #1,CCR) sets the computed C = D0.W bit 15. N20 writes no port and changes
// no bank.
bool animation_objects_n20_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool flag=false;
    switch(r.pc) {
    // ---- 49580: JSR 49370(PC); the nearer player (x distance, sign by 15 bit 0) in A0 / D0.W; C = D0.W bit 15.
    case 0x49580:return am_call(c,0x49370,0x49584);
    // MOVE.B D0,D7; LEA 100cb8.L,A0; MOVE.W #8000,D0; BTST.B #0,D7; BEQ.W 495ac.
    case 0x49584:am_byte(r.d[7],r.d[0]);r.a[0]=0x100cb8;am_word(r.d[0],0x8000);r.pc=(r.d[7]&1U)?0x49598:0x495ac;return true;
    // MOVE.W 42(A0),D0; SUB.W 42(A6),D0; BTST.B #0,15(A6); BNE.W 495ac.
    case 0x49598:
        if(!am_read(c,am_index(r.a[0],0x42),2,value) || !on20_get(c,0x42,2,other))return false;am_word(r.d[0],(value-other)&65535U);
        if(!on20_bit(c,0x15,0,flag))return false;r.pc=flag?0x495ac:0x495aa;return true;
    case 0x495aa:am_word(r.d[0],(0U-r.d[0])&65535U);r.pc=0x495ac;return true; // NEG.W D0.
    case 0x495ac:r.pc=(r.d[7]&2U)?0x495b4:0x495d8;return true;             // BTST.B #1,D7; BEQ.W 495d8.
    // LEA 100da8.L,A1; MOVE.W 42(A1),D1; SUB.W 42(A6),D1; BTST.B #0,15(A6); BNE.W 495ce.
    case 0x495b4:
        r.a[1]=0x100da8;if(!am_read(c,am_index(r.a[1],0x42),2,value) || !on20_get(c,0x42,2,other))return false;
        am_word(r.d[1],(value-other)&65535U);if(!on20_bit(c,0x15,0,flag))return false;r.pc=flag?0x495ce:0x495cc;return true;
    case 0x495cc:am_word(r.d[1],(0U-r.d[1])&65535U);r.pc=0x495ce;return true; // NEG.W D1.
    // CMP.W D1,D0; BLS.W 495d8 (unsigned D0.W <= D1.W).
    case 0x495ce:r.pc=(r.d[0]&65535U)<=(r.d[1]&65535U)?0x495d8:0x495d4;return true;
    case 0x495d4:r.a[0]=r.a[1];am_word(r.d[0],r.d[1]);r.pc=0x495d8;return true; // MOVEA.L A1,A0; MOVE.W D1,D0.
    // CMPI.W #8000,D0 (C = D0.W < 8000 unsigned); EORI.B #1,CCR (C = D0.W bit 15); RTS.
    case 0x495d8:r.carry=(r.d[0]&0x8000U)?AnimationCarrySet:AnimationCarryClear;return am_return(c);
    // ---- 735b0 (tail): LEA 735a8(PC),A0; JSR 1ab02.L; BCC.W 735c4 / JMP 2a00.L.
    case 0x735b0:r.a[0]=0x735a8;return am_call(c,0x1ab02,0x735ba);
    case 0x735ba:return on20_carry(c,0x735c4,0x735be);                    // BCC.W 735c4 (C returned by 1ab02).
    case 0x735be:r.pc=0x2a00;return true;                                  // JMP 2a00.L.
    case 0x735c4:case 0x7364c:case 0x7368e:case 0x736a0:case 0x736d0:case 0x73990:case 0x739be:case 0xb9a34:case 0xb9b8a:
    case 0xb9d08:return am_return(c);                                      // RTS.
    // ---- 735c6: MOVE.B 98(A6),D0; CMPI.B #0,D0; BNE.W 735e2; BTST.B #7,15(A6); BNE.W 735e2; JMP 4be2c.L / JMP 4be06.L.
    case 0x735c6:if(!on20_get(c,0x98,1,value))return false;am_byte(r.d[0],value);r.pc=(value&255U)!=0U?0x735e2:0x735d2;return true;
    case 0x735d2:if(!on20_bit(c,0x15,7,flag))return false;r.pc=flag?0x735e2:0x735dc;return true;
    case 0x735dc:r.pc=0x4be2c;return true;
    case 0x735e2:r.pc=0x4be06;return true;
    // ---- 7361a: JSR 4b54e.L; BTST.B #7,61(A6); BEQ.W 7364c.
    case 0x7361a:return am_call(c,0x4b54e,0x73620);
    case 0x73620:if(!on20_bit(c,0x61,7,flag))return false;r.pc=flag?0x7362a:0x7364c;return true;
    // MOVE.B #ff,17(A6); LEA cdeea.L,A0; MOVEA.L 2000d0.L,A1; MOVE.W #3,D1; MOVE.W #0,D2; JMP cc778.L (boundary).
    case 0x7362a:
        if(!on20_put(c,0x17,1,0xff))return false;r.a[0]=0xcdeea;if(!am_read(c,ON20_BANK_3,4,value))return false;r.a[1]=value;
        am_word(r.d[1],3);am_word(r.d[2],0);r.pc=0xcc778;return true;
    // ---- 7364e: MOVE.W 10000e.L,D0; ANDI.B #1f,D0; BNE.W 7366e.
    case 0x7364e:
        if(!am_read(c,0x10000e,2,value))return false;am_word(r.d[0],value);am_byte(r.d[0],r.d[0]&0x1fU);
        r.pc=(r.d[0]&0x1fU)!=0U?0x7366e:0x7365c;return true;
    case 0x7365c:return am_call(c,0x73690,0x73660);                       // JSR 73690(PC).
    case 0x73660:return on20_carry(c,0x7366a,0x73664);                    // BCC.W 7366a (C returned by 73690).
    case 0x73664:return on20_install(c,0x738fa,0x7366a);                  // MOVE.L #738fa,(A6).
    case 0x7366a:if(!on20_put(c,0x86,4,r.a[0]))return false;r.pc=0x7366e;return true; // MOVE.L A0,86(A6).
    // MOVE.W 42(A6),D0; MOVE.W 46(A6),D1; JSR 4bc04.L.
    case 0x7366e:
        if(!on20_get(c,0x42,2,value))return false;am_word(r.d[0],value);if(!on20_get(c,0x46,2,value))return false;am_word(r.d[1],value);
        return am_call(c,0x4bc04,0x7367c);
    case 0x7367c:r.pc=(r.d[0]&65535U)==0U?0x7368e:0x73682;return true;     // TST.W D0; BEQ.W 7368e.
    // MOVE.W #0,70(A6); MOVE.L #72eb0,(A6).
    case 0x73682:if(!on20_put(c,0x70,2,0))return false;return on20_install(c,0x72eb0,0x7368e);
    // ---- 73690: JSR 49580.L; BCC.W 736a0; MOVEA.L #0,A0; RTS (the C of 49580 passes through).
    case 0x73690:return am_call(c,0x49580,0x73696);
    case 0x73696:return on20_carry(c,0x736a0,0x7369a);                    // BCC.W 736a0 (C returned by 49580).
    case 0x7369a:r.a[0]=0;r.pc=0x736a0;return true;                        // MOVEA.L #0,A0.
    // ---- 736a2: JSR 73690(PC); BCS.W 736b6; 82 = 1c / 3; MOVE.L A0,86(A6); RTS.
    case 0x736a2:return am_call(c,0x73690,0x736a6);
    case 0x736a6:return on20_carry(c,0x736aa,0x736b6);                    // BCS.W 736b6 (C returned by 73690).
    case 0x736aa:if(!on20_put(c,0x82,4,0x1c))return false;r.pc=0x736be;return true; // MOVE.L #1c,82(A6); BRA.W 736be.
    case 0x736b6:if(!on20_put(c,0x82,4,3))return false;r.pc=0x736be;return true;    // MOVE.L #3,82(A6).
    case 0x736be:if(!on20_put(c,0x86,4,r.a[0]))return false;return am_return(c); // MOVE.L A0,86(A6); RTS.
    // ---- 736c4: TST.W 94(A6); BNE.W 736d0; MOVE.L 8a(A6),(A6).
    case 0x736c4:if(!on20_get(c,0x94,2,value))return false;r.pc=(value&65535U)!=0U?0x736d0:0x736cc;return true;
    case 0x736cc:if(!on20_get(c,0x8a,4,value) || !am_write(c,r.a[6],4,value))return false;r.pc=0x736d0;return true;
    // ---- 736d2 (stage event callback): MOVE.W #0,70(A6); MOVE.B #0,98(A6); MOVE.L #4,7e(A6); MOVE.L #1d,82(A6);
    // MOVE.L #72eb0,8a(A6); BRA.W 736fa.
    case 0x736d2:
        if(!on20_put(c,0x70,2,0) || !on20_put(c,0x98,1,0) || !on20_put(c,0x7e,4,4) || !on20_put(c,0x82,4,0x1d) ||
            !on20_put(c,0x8a,4,0x72eb0))return false;
        r.pc=0x736fa;return true;
    case 0x736fa:am_word(r.d[0],0x33);am_word(r.d[1],4);am_byte(r.d[2],0);return am_call(c,0xc6a96,0x7370c); // c6a96 33/4/0.
    case 0x7370c:return am_call(c,0xea5f0,0x73712);                       // JSR ea5f0.L.
    // CLR.B 97(A6); MOVE.W 78(A6),D0; BNE.W 73724.
    case 0x73712:
        if(!on20_put(c,0x97,1,0) || !on20_get(c,0x78,2,value))return false;am_word(r.d[0],value);
        r.pc=(value&65535U)!=0U?0x73724:0x7371e;return true;
    case 0x7371e:r.d[0]=0xffffffffU;r.pc=0x73736;return true;              // MOVEQ #ff,D0; BRA.W 73736.
    // MOVE.W D0,-(A7); LEA c868e.L,A0; JSR 490ba.L.
    case 0x73724:if(!am_push(c,2,r.d[0]&65535U))return false;r.a[0]=0xc868e;return am_call(c,0x490ba,0x73732);
    // MULU.W (A7)+,D0; LSR.L #8,D0.
    case 0x73732:if(!am_pop(c,2,value))return false;r.d[0]=on20_mulu(r.d[0],value)>>8;r.pc=0x73736;return true;
    // MOVE.W D0,92(A6); LEA c85cc.L,A0; JSR 490ba.L.
    case 0x73736:if(!on20_put(c,0x92,2,r.d[0]&65535U))return false;r.a[0]=0xc85cc;return am_call(c,0x490ba,0x73746);
    // MOVE.W 7a(A6),D1; MULU.W D1,D0; LSR.L #8,D0; CMPI.W #100,D0; BCS.W 7375a (unsigned D0.W < 100).
    case 0x73746:
        if(!on20_get(c,0x7a,2,value))return false;am_word(r.d[1],value);r.d[0]=on20_mulu(r.d[0],r.d[1])>>8;
        r.pc=(r.d[0]&65535U)<0x100U?0x7375a:0x73756;return true;
    case 0x73756:am_word(r.d[0],0xff);r.pc=0x7375a;return true;            // MOVE.W #ff,D0.
    // MOVE.W D0,7a(A6); MOVE.W 7c(A6),D0; BNE.W 73768.
    case 0x7375a:
        if(!on20_put(c,0x7a,2,r.d[0]&65535U) || !on20_get(c,0x7c,2,value))return false;am_word(r.d[0],value);
        r.pc=(value&65535U)!=0U?0x73768:0x73766;return true;
    case 0x73766:r.d[0]=0xffffffffU;r.pc=0x73768;return true;              // MOVEQ #ff,D0.
    // MOVE.W D0,94(A6); MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); JSR 4c0ac.L.
    case 0x73768:
        if(!on20_put(c,0x94,2,r.d[0]&65535U) || !on20_put(c,0x68,2,0x8820) || !on20_put(c,0x1e,2,0x8820))return false;
        return am_call(c,0x4c0ac,0x7377e);
    // ---- 7377e (installed): MOVE.L 7e(A6),D0; CMPI.L #4,D0; BNE.W 737b4.
    case 0x7377e:if(!on20_get(c,0x7e,4,value))return false;r.d[0]=value;r.pc=value!=4U?0x737b4:0x7378c;return true;
    case 0x7378c:return on20_animation(c,ON20_BANK_3,3,0x10,0x737b4);     // animation record + 10.
    case 0x737b4:return on20_install(c,0x737ba,0x737ba);                  // MOVE.L #737ba,(A6).
    case 0x737ba:case 0x738da:return am_call(c,0x7394e,r.pc==0x737ba?0x737be:0x738de); // BSR.W 7394e.
    case 0x737be:case 0x7382e:case 0x73882:case 0x738de:case 0x73928:     // BSR.W 735c6.
        return am_call(c,0x735c6,r.pc+4U);
    case 0x737c2:case 0x73832:case 0x73886:case 0x738e2:case 0x7392c:case 0xb99c4:case 0xb9b36:case 0xb9cf2: // JSR 49fc6.L.
        return am_call(c,0x49fc6,r.pc+6U);
    // MOVE.B 98(A6),D0; CMPI.B #0,D0; BNE.W 737ec.
    case 0x737c8:if(!on20_get(c,0x98,1,value))return false;am_byte(r.d[0],value);r.pc=(value&255U)!=0U?0x737ec:0x737d4;return true;
    case 0x737d4:return am_call(c,0x7364e,0x737d8);                       // BSR.W 7364e.
    case 0x737d8:if(!on20_bit(c,0x15,7,flag))return false;r.pc=flag?0x737e8:0x737e2;return true; // BTST.B #7,15(A6); BNE.W 737e8.
    case 0x737e2:return on20_install(c,0x73800,0x737e8);                  // MOVE.L #73800,(A6).
    case 0x737e8:r.pc=0x737f0;return true;                                 // BRA.W 737f0.
    case 0x737ec:return am_call(c,0x736a2,0x737f0);                       // BSR.W 736a2.
    case 0x737f0:return am_call(c,0x73992,0x737f4);                       // BSR.W 73992.
    case 0x737f4:return am_call(c,0x736c4,0x737f8);                       // BSR.W 736c4.
    case 0x737f8:case 0x7384c:case 0x73896:case 0x738f2:case 0x73946:     // JSR 7361a(PC).
        return am_call(c,0x7361a,r.pc+4U);
    case 0x737fc:case 0x73850:case 0x7389a:case 0x738f6:case 0x7394a:r.pc=0x735b0;return true; // BRA.W 735b0.
    // ---- 73800 / 73854 / 738fa (installed): animation record + 20 / 24 / 18, then install 7382e / 73882 / 73928.
    case 0x73800:return on20_animation(c,ON20_BANK_3,3,0x20,0x73828);
    case 0x73828:return on20_install(c,0x7382e,0x7382e);
    case 0x73838:return on20_carry(c,0x7384c,0x7383c);                    // BCC.W 7384c (C returned by 49fc6).
    case 0x7383c:if(!on20_bit(c,0x15,7,flag))return false;r.pc=flag?0x73846:0x7384c;return true; // BTST.B #7,15(A6); BEQ.W 7384c.
    case 0x73846:return on20_install(c,0x73854,0x7384c);                  // MOVE.L #73854,(A6).
    case 0x73854:return on20_animation(c,ON20_BANK_3,3,0x24,0x7387c);
    case 0x7387c:return on20_install(c,0x73882,0x73882);
    case 0x7388c:return on20_carry(c,0x73896,0x73890);                    // BCC.W 73896 (C returned by 49fc6).
    case 0x73890:case 0x738ec:return on20_install(c,0x7377e,r.pc+6U);     // MOVE.L #7377e,(A6).
    // ---- 7389e (installed by 739b2): MOVE.L 82(A6),D0; CMPI.L #1d,D0; BNE.W 738d4.
    case 0x7389e:if(!on20_get(c,0x82,4,value))return false;r.d[0]=value;r.pc=value!=0x1dU?0x738d4:0x738ac;return true;
    case 0x738ac:return on20_animation(c,ON20_BANK_3,3,0x74,0x738d4);
    case 0x738d4:return on20_install(c,0x738da,0x738da);
    case 0x738e8:return on20_carry(c,0x738f2,0x738ec);                    // BCC.W 738f2 (C returned by 49fc6).
    case 0x738fa:return on20_animation(c,ON20_BANK_3,3,0x18,0x73922);
    case 0x73922:return on20_install(c,0x73928,0x73928);
    case 0x73932:return on20_carry(c,0x73946,0x73936);                    // BCC.W 73946 (C returned by 49fc6).
    case 0x73936:r.a[0]=am_index(r.a[6],0x26);return am_call(c,0x492d0,0x73940); // LEA 26(A6),A0; JSR 492d0.L.
    case 0x73940:return on20_install(c,0x7377e,0x73946);
    // ---- 7394e: TST.B 97(A6); BNE.W 73974.
    case 0x7394e:if(!on20_get(c,0x97,1,value))return false;r.pc=(value&255U)!=0U?0x73974:0x73956;return true;
    // MOVE.W 76(A6),D0; LSL.W #3,D0; NEG.W D0; ADDI.W #140,D0; CMP.W 42(A6),D0; BMI.W 73970.
    case 0x73956:
        if(!on20_get(c,0x76,2,value))return false;am_word(r.d[0],(0x140U-((value<<3)&65535U))&65535U);
        if(!on20_get(c,0x42,2,value))return false;r.pc=((r.d[0]-value)&0x8000U)?0x73970:0x7396a;return true;
    case 0x7396a:if(!on20_put(c,0x97,1,1))return false;r.pc=0x73970;return true; // MOVE.B #1,97(A6).
    case 0x73970:r.pc=0x73990;return true;                                 // BRA.W 73990.
    case 0x73974:return on20_count(c,0x92,0x73982,0x7397c);
    case 0x7397c:return on20_decrement(c,0x92,0x73982);
    case 0x73982:return on20_count(c,0x94,0x73990,0x7398a);
    case 0x7398a:return on20_decrement(c,0x94,0x73990);
    // ---- 73992: TST.W 92(A6); BNE.W 739be.
    case 0x73992:if(!on20_get(c,0x92,2,value))return false;r.pc=(value&65535U)!=0U?0x739be:0x7399a;return true;
    // MOVE.W 42(A6),D0; SUBI.W #30,D0; CMPI.W #f0,D0; BCC.W 739be (unsigned D0.W >= f0).
    case 0x7399a:
        if(!on20_get(c,0x42,2,value))return false;am_word(r.d[0],(value-0x30U)&65535U);
        r.pc=(r.d[0]&65535U)>=0xf0U?0x739be:0x739aa;return true;
    case 0x739aa:if(!on20_get(c,0x86,4,value))return false;r.d[0]=value;r.pc=value==0U?0x739be:0x739b2;return true; // MOVE.L 86(A6),D0; BEQ.W.
    // MOVE.W 7a(A6),92(A6); MOVE.L #7389e,(A6).
    case 0x739b2:if(!on20_get(c,0x7a,2,value) || !on20_put(c,0x92,2,value))return false;return on20_install(c,0x7389e,0x739be);
    // ---- b9832 (stage event callback): MOVE.B #0,a3(A6); MOVE.W 82(A6),D0; BNE.W b9884.
    case 0xb9832:
        if(!on20_put(c,0xa3,1,0) || !on20_get(c,0x82,2,value))return false;am_word(r.d[0],value);
        r.pc=(value&65535U)!=0U?0xb9884:0xb9840;return true;
    case 0xb9840:case 0xb9898:return on20_child(c,0xb9c6e,r.pc+0x10U);
    case 0xb9850:case 0xb98a8:return on20_child(c,0xb9c80,r.pc+0x10U);
    case 0xb9860:case 0xb98bc:return on20_child(c,0xb9d0a,r.pc+0x10U);
    case 0xb9870:case 0xb98cc:return on20_child(c,0xb9d1c,r.pc+0x10U);
    case 0xb9880:case 0xb988c:case 0xb98b8:r.pc=0xb98dc;return true;      // BRA.W b98dc.
    case 0xb9884:r.pc=(r.d[0]&65535U)!=1U?0xb9890:0xb988c;return true;     // CMPI.W #1,D0; BNE.W b9890.
    case 0xb9890:r.pc=(r.d[0]&65535U)!=2U?0xb98bc:0xb9898;return true;     // CMPI.W #2,D0; BNE.W b98bc.
    // LEA b9da6(PC),A0; MOVE.L A0,84(A6); MOVE.L #ba2fa,8c(A6); TST.B 7a(A6); BNE.W b98fc.
    case 0xb98dc:r.a[0]=0xb9da6;if(!on20_put(c,0x84,4,r.a[0]))return false;return on20_table(c,0xb98fc,0xb98f4);
    case 0xb98f4:case 0xb9922:if(!on20_put(c,0x8c,4,0xba304))return false;r.pc=r.pc+8U;return true; // MOVE.L #ba304,8c(A6).
    case 0xb98fc:am_word(r.d[0],0x73);am_word(r.d[1],0xa);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xb990e); // c6a96 73/a/0.
    case 0xb990e:r.pc=0xb9912;return true;                                 // BRA.W b9912.
    case 0xb9912:return on20_table(c,0xb992a,0xb9922);
    // MOVE.W #801,68(A6); MOVE.W #801,1e(A6); TST.W 7c(A6); BNE.W b994c.
    case 0xb992a:
        if(!on20_put(c,0x68,2,0x801) || !on20_put(c,0x1e,2,0x801) || !on20_get(c,0x7c,2,value))return false;
        r.pc=(value&65535U)!=0U?0xb994c:0xb993e;return true;
    case 0xb993e:case 0xb99d6:am_word(r.d[0],0x1a50);return am_call(c,0x3af8,r.pc+0xaU); // MOVE.W #1a50,D0; JSR 3af8.L.
    case 0xb9948:r.pc=0xb9a36;return true;                                 // BRA.W b9a36.
    // TST.B a3(A6); BNE.W b9980.
    case 0xb994c:if(!on20_get(c,0xa3,1,value))return false;r.pc=(value&255U)!=0U?0xb9980:0xb9954;return true;
    case 0xb9954:return on20_animation(c,ON20_BANK_203,0x203,0x28,0xb997c);
    case 0xb997c:r.pc=0xb99b8;return true;                                 // BRA.W b99b8.
    case 0xb9980:return on20_indexed_animation(c,0xb99b8);
    case 0xb99b8:return on20_install(c,0xb99be,0xb99be);
    // ---- b99be (installed): JSR 43ea4.L; JSR 49fc6.L; MOVE.W 7c(A6),D0; CMP.W 5418(A5),D0; BHI.W b99e6.
    case 0xb99be:case 0xb9b30:return am_call(c,0x43ea4,r.pc+6U);
    case 0xb99ca:if(!on20_get(c,0x7c,2,value))return false;am_word(r.d[0],value);return on20_progress(c,0xb99e6,0xb99d6);
    case 0xb99e0:return on20_install(c,0xb9a36,0xb99e6);                  // MOVE.L #b9a36,(A6).
    case 0xb99e6:return on20_screen(c,0xb9a0e,0xb99ee);
    case 0xb99ee:case 0xb9b44:r.a[0]=0xb982a;return am_call(c,0x1ab02,r.pc+0xcU); // MOVEA.L #b982a,A0; JSR 1ab02.L.
    case 0xb99fa:return on20_carry(c,0xb9a0a,0xb99fe);                    // BCC.W b9a0a (C returned by 1ab02).
    case 0xb99fe:case 0xb9a16:case 0xb9b54:case 0xb9b6c:return am_call(c,0x46ef4,r.pc+6U); // JSR 46ef4.L.
    case 0xb9a04:case 0xb9a1c:case 0xb9b5a:case 0xb9b72:r.pc=0x2a24;return true; // JMP 2a24.L.
    case 0xb9a0a:r.pc=0xb9a22;return true;                                 // BRA.W b9a22.
    case 0xb9a0e:return on20_progress(c,0xb9a22,0xb9a16);
    case 0xb9a22:return on20_pointer(c,0xb9a34,0xb9a2e);
    case 0xb9a2e:case 0xb9b84:return am_call(c,0x4706c,r.pc+6U);          // JSR 4706c.L.
    // ---- b9a36 (installed by b99e0): MOVE.W #0,98(A6); TST.B a3(A6); BNE.W b9a70.
    case 0xb9a36:
        if(!on20_put(c,0x98,2,0) || !on20_get(c,0xa3,1,value))return false;r.pc=(value&255U)!=0U?0xb9a70:0xb9a44;return true;
    case 0xb9a44:return on20_animation(c,ON20_BANK_203,0x203,0x28,0xb9a6c);
    case 0xb9a6c:r.pc=0xb9aa8;return true;                                 // BRA.W b9aa8.
    case 0xb9a70:return on20_indexed_animation(c,0xb9aa8);
    case 0xb9aa8:return on20_install(c,0xb9aae,0xb9aae);
    // ---- b9aae (installed): MOVE.L #10000,D0; MOVE.L D0,3a(A6); TST.B a3(A6); BNE.W b9aec.
    case 0xb9aae:
        r.d[0]=0x10000;if(!on20_put(c,0x3a,4,0x10000) || !on20_get(c,0xa3,1,value))return false;
        r.pc=(value&255U)!=0U?0xb9aec:0xb9ac0;return true;
    // CMPI.W #1,76(A6); BNE.W b9ad4 / CMPI.W #2,76(A6); BNE.W b9ae8.
    case 0xb9ac0:if(!on20_get(c,0x76,2,value))return false;r.pc=(value&65535U)!=1U?0xb9ad4:0xb9aca;return true;
    case 0xb9aca:return on20_speed(c,0x18000,0xb9ad4);
    case 0xb9ad4:if(!on20_get(c,0x76,2,value))return false;r.pc=(value&65535U)!=2U?0xb9ae8:0xb9ade;return true;
    case 0xb9ade:return on20_speed(c,0x20000,0xb9ae8);
    case 0xb9ae8:r.pc=0xb9b00;return true;                                 // BRA.W b9b00.
    // CMPI.W #2,76(A6); BLT.W b9b00 (signed).
    case 0xb9aec:if(!on20_get(c,0x76,2,value))return false;r.pc=on20_signed_word(value)<2?0xb9b00:0xb9af6;return true;
    case 0xb9af6:return on20_speed(c,0x18000,0xb9b00);
    // TST.B 7a(A6); BNE.W b9b0c / NEG.L 3a(A6).
    case 0xb9b00:if(!on20_get(c,0x7a,1,value))return false;r.pc=(value&255U)!=0U?0xb9b0c:0xb9b08;return true;
    case 0xb9b08:if(!on20_get(c,0x3a,4,value) || !on20_put(c,0x3a,4,0U-value))return false;r.pc=0xb9b0c;return true;
    // MOVE.L 98(A6),D1; ADD.L D0,D1; MOVE.L D1,98(A6); CLR.W D1; SWAP D1; CMP.W 7e(A6),D1; BLE.W b9b30 (signed).
    case 0xb9b0c:
        if(!on20_get(c,0x98,4,value))return false;r.d[1]=value+r.d[0];if(!on20_put(c,0x98,4,r.d[1]))return false;
        am_word(r.d[1],0);am_swap(r.d[1]);if(!on20_get(c,0x7e,2,value))return false;
        r.pc=on20_signed_word(r.d[1])<=on20_signed_word(value)?0xb9b30:0xb9b22;return true;
    case 0xb9b22:am_word(r.d[0],0x1a51);return am_call(c,0x3af8,0xb9b2c); // MOVE.W #1a51,D0; JSR 3af8.L.
    case 0xb9b2c:r.pc=0xb9b8c;return true;                                 // BRA.W b9b8c.
    case 0xb9b3c:return on20_screen(c,0xb9b64,0xb9b44);
    case 0xb9b50:return on20_carry(c,0xb9b60,0xb9b54);                    // BCC.W b9b60 (C returned by 1ab02).
    case 0xb9b60:r.pc=0xb9b78;return true;                                 // BRA.W b9b78.
    case 0xb9b64:return on20_progress(c,0xb9b78,0xb9b6c);
    case 0xb9b78:return on20_pointer(c,0xb9b8a,0xb9b84);
    // MOVE.L #0,3a(A6); TST.B a3(A6); BNE.W b9bc8.
    case 0xb9b8c:
        if(!on20_put(c,0x3a,4,0) || !on20_get(c,0xa3,1,value))return false;r.pc=(value&255U)!=0U?0xb9bc8:0xb9b9c;return true;
    case 0xb9b9c:return on20_animation(c,ON20_BANK_203,0x203,0x28,0xb9bc4);
    case 0xb9bc4:r.pc=0xb9c00;return true;                                 // BRA.W b9c00.
    case 0xb9bc8:return on20_indexed_animation(c,0xb9c00);
    // ANDI.L #ffff0000,32(A6); MOVE.L #b9c0e,(A6) (fall-through into b9c0e, boundary).
    case 0xb9c00:if(!on20_get(c,0x32,4,value) || !on20_put(c,0x32,4,value&0xffff0000U))return false;return on20_install(c,0xb9c0e,0xb9c0e);
    // ---- b9c6e / b9c80 (28ae children): MOVE.W #ffca/#3c,D0; MOVE.W #0,D1; JSR 49290.L; BRA.W b9c92.
    case 0xb9c6e:am_word(r.d[0],0xffca);am_word(r.d[1],0);return am_call(c,0x49290,0xb9c7c);
    case 0xb9c80:am_word(r.d[0],0x3c);am_word(r.d[1],0);return am_call(c,0x49290,0xb9c8e);
    case 0xb9c7c:case 0xb9c8e:r.pc=0xb9c92;return true;
    // MOVE.W #800,68(A6); MOVE.W #800,1e(A6); MOVE.W #73,D0; MOVE.W #9,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xb9c92:
        if(!on20_put(c,0x68,2,0x800) || !on20_put(c,0x1e,2,0x800))return false;am_word(r.d[0],0x73);am_word(r.d[1],9);am_byte(r.d[2],0);
        return am_call(c,0xc6a96,0xb9cb0);
    case 0xb9cb0:return on20_animation(c,ON20_BANK_203,0x203,0x24,0xb9cd8);
    case 0xb9cd8:return on20_install(c,0xb9cde,0xb9cde);
    // ---- b9cde (installed): JSR 43e34.L; MOVEA.L c(A6),A0; CMPI.W #200,46(A0); BGT.W b9cf8 (signed); JSR 49fc6.L; JSR 288c.L.
    case 0xb9cde:return am_call(c,0x43e34,0xb9ce4);
    case 0xb9ce4:
        if(!on20_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x46),2,value))return false;
        r.pc=on20_signed_word(value)>0x200?0xb9cf8:0xb9cf2;return true;
    case 0xb9cf8:return am_call(c,0x288c,0xb9cfe);
    case 0xb9cfe:return on20_carry(c,0xb9d02,0xb9d08);                    // BCS.W b9d08 (C returned by 288c).
    case 0xb9d02:r.pc=0x2a00;return true;                                  // JMP 2a00.L.
    default:return am_error(c,"unsupported animation objects n20 PC");
    }
}
}
