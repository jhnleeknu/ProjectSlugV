#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OB1B_BANK_1A3=0x2001a0;   // MOVE.L 2001a0.l,22(A6) (banked LONG, live bus, current PVC bank).
const std::uint32_t OB1B_TABLE_3DD42=0x3dd42; // LONG table of 3dd30 (fixed ROM, live bus).
const std::uint32_t OB1B_DATA_3DEF2=0x3def2;  // WORD data of 3de64 (fixed ROM, live bus).
const std::uint32_t OB1B_TABLE_B15C0=0xb15c0; // LONG table of b1670 (fixed ROM, live bus).
bool ob1b_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool ob1b_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
bool ob1b_get_at(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob1b_put_at(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BTST.B #bit,d16(A6): true when the bit is set.
bool ob1b_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob1b_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,d16(A6) (read, then write the BYTE; only Z changes, which no branch of this unit reads afterwards).
bool ob1b_change(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!ob1b_get(c,displacement,1,value))return false;
    value=set?(value|(1U<<bit)):(value&~(1U<<bit));return ob1b_put(c,displacement,1,value&255U);
}
// TST.B d16(A6): true when the BYTE is zero.
bool ob1b_zero_b(AnimationMachineContext& c,std::uint32_t displacement,bool& zero) {
    std::uint32_t value=0;if(!ob1b_get(c,displacement,1,value))return false;zero=(value&255U)==0U;return true;
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool ob1b_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b1b caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,(A6) then continue at next_pc.
bool ob1b_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// MOVE.W #value,D0; JSR target.l.
bool ob1b_call_d0(AnimationMachineContext& c,std::uint32_t value,std::uint32_t target,std::uint32_t return_pc) {
    am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MOVEA.L #record,A1; MOVE.W #100,D0; JSR 49f8c.l (animation block of the node, A0 unchanged).
bool ob1b_animation(AnimationMachineContext& c,std::uint32_t record,std::uint32_t return_pc) {
    c.s.a[1]=record;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L #record,A1; MOVE.W #100,D0; LEA 8a(A6),A0; JSR 49f96.l (animation block of the node with the A0 = node + 8a record).
bool ob1b_animation_record(AnimationMachineContext& c,std::uint32_t record,std::uint32_t return_pc) {
    c.s.a[1]=record;am_word(c.s.d[0],0x100);c.s.a[0]=am_index(c.s.a[6],0x8a);return am_call(c,0x49f96,return_pc);
}
// MOVE.L #x,36(A0); MOVE.L #y,3a(A0); MOVE.W #w,54(A0) (the debris child returned by d3d7c).
bool ob1b_debris(AnimationMachineContext& c,std::uint32_t x,std::uint32_t y,std::uint32_t w) {
    return ob1b_put_at(c,c.s.a[0],0x36,4,x) && ob1b_put_at(c,c.s.a[0],0x3a,4,y) && ob1b_put_at(c,c.s.a[0],0x54,2,w);
}
// MOVEA.L #3db68,A0; MOVE.W #1e,D0; JSR 28ae.l (the explosion child).
bool ob1b_child(AnimationMachineContext& c,std::uint32_t return_pc) {
    c.s.a[0]=0x3db68;am_word(c.s.d[0],0x1e);return am_call(c,0x28ae,return_pc);
}
// Signed LONG compare a < b (two's complement, no implementation-defined conversion).
bool ob1b_less(std::uint32_t a,std::uint32_t b) {
    return (a^0x80000000U)<(b^0x80000000U);
}
// Signed WORD view.
bool ob1b_less_word(std::uint32_t a,std::uint32_t b) {
    return ((a&65535U)^0x8000U)<((b&65535U)^0x8000U);
}
// MOVEM.W (A7)+,Dx-Dy: WORDs sign-extended to the full register.
bool ob1b_pop_word_ext(AnimationMachineContext& c,std::uint32_t& reg) {
    std::uint32_t value=0;if(!am_pop(c,2,value))return false;reg=am_extend_word(value);return true;
}
}
// Objects deferred B1b (207 block starts of the contract's 211: the contract's 3d8de chain lists 9 starts, not 13): the N22b
// part 3d3f0 3d7e8 3da72 3db68 3dbbe 3dcac 3dcda 3dd0e 3dd30 3dde4 3de54 3defa 3df30 3e03e 3e0a8 (154), the 3d8de chain (9, installed
// by 3d8d4, table slots 3d8ac 3d8b0) and the 3e250 28ae child of 3d3fa (13), and the N19b part b1656 b16d6 (stage event callback table
// e8ec8 / e8ed0) b1c82 b1c9e b1d8c (31). Boundaries without an executor here: the shared helpers 4d418 4d4b4 4d734 4d7a6 4d98a
// 4ff96 d3d7c 19a00 8d34 and the chains 3d526 3d982, the TRAP #f at b1c90 (b1c82 falls into it when D0.W - 1 > 5). The BCC/BCS/SCC
// consumers 3d40a (28ae) 3d478 (3dcf2) 3dbae 3e2ec (49fc6) 3dbca (3dcac -> 4d418) 3e2dc (288c) b16c2 (b15e0) b1cb4 (28ae) read the C of
// their callee; b1cc2 (ORI CCR) sets a known C. 3dac2 (BNE) reads the Z of its two predecessors 3dab6 / 3dabe and is recomputed from
// BYTE a4(A6). The BRA.W table 3d8a8 (9 slots, 3d8a0 shifts D0.W by 2 twice and jumps to base + sext(D0.W)) is transcribed.
bool animation_objects_b1b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool bit=false,zero=false;
    switch(r.pc) {
    // ---- N22b: 3d3f0 (installed by 3d37a): MOVE.B #ff,b3(A6); JSR 3e03e(PC).
    case 0x3d3f0:if(!ob1b_put(c,0xb3,1,0xff))return false;return am_call(c,0x3e03e,0x3d3fa);
    // MOVEA.L #3e250,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x3d3fa:r.a[0]=0x3e250;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x3d40a);
    // SCC.B 62(A6) (C returned by 28ae: BYTE = ff when C is clear); JSR 4972c.l.
    case 0x3d40a:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects b1b caller requires known carry");
        if(!ob1b_put(c,0x62,1,r.carry==AnimationCarryClear?0xffU:0U))return false;return am_call(c,0x4972c,0x3d414);
    case 0x3d414:return ob1b_install(c,0x3d41a,0x3d41a);                // MOVE.L #3d41a,(A6).
    case 0x3d41a:if(!ob1b_zero_b(c,0x62,zero))return false;r.pc=zero?0x3d422:0x3d436;return true; // TST.B 62(A6); BNE.W 3d436.
    case 0x3d422:case 0x3d470:case 0x3d4e2:case 0x3d812:return am_call(c,0x3de54,r.pc+4U); // JSR 3de54(PC).
    case 0x3d426:case 0x3d474:case 0x3d4e6:case 0x3d816:return am_call(c,0x3dcf2,r.pc+4U); // JSR 3dcf2(PC).
    // MOVE.W #1e,D0; JSR 3df30(PC).
    case 0x3d42a:return ob1b_call_d0(c,0x1e,0x3df30,0x3d432);
    case 0x3d48c:return ob1b_call_d0(c,0x1e,0x3df30,0x3d494);
    case 0x3d432:case 0x3d494:r.pc=0x3dbbe;return true;                  // BRA.W 3dbbe.
    // MOVEA.L #3e7c0,A1; MOVE.W #100,D0; LEA 8a(A6),A0; JSR 49f96.l / MOVEA.L #3e85c,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3d436:return ob1b_animation_record(c,0x3e7c0,0x3d44a);
    case 0x3d44a:return ob1b_animation(c,0x3e85c,0x3d45a);
    // MOVE.B #1,9d(A6); MOVE.W #1a60,D0; JSR 3af8.l.
    case 0x3d45a:if(!ob1b_put(c,0x9d,1,1))return false;return ob1b_call_d0(c,0x1a60,0x3af8,0x3d46a);
    case 0x3d46a:return ob1b_install(c,0x3d470,0x3d470);                // MOVE.L #3d470,(A6).
    case 0x3d478:return ob1b_carry(c,0x3d48c,0x3d47c);                  // BCC.W 3d48c (C returned by 3dcf2).
    case 0x3d47c:if(!ob1b_bit(c,0x9b,0,bit))return false;r.pc=bit?0x3d486:0x3d48c;return true; // BTST.B #0,9b(A6); BEQ.W 3d48c.
    case 0x3d486:return ob1b_install(c,0x3d526,0x3d48c);                // MOVE.L #3d526,(A6) (chain 3d526: boundary).
    // MOVE.W #0,88(A6); MOVE.W #1a62,D0; JSR 3af8.l.
    case 0x3d498:if(!ob1b_put(c,0x88,2,0))return false;return ob1b_call_d0(c,0x1a62,0x3af8,0x3d4a8);
    // BSET.B #4,9b(A6); MOVEA.L #3e778,A1; MOVE.W #100,D0; LEA 8a(A6),A0; JSR 49f96.l.
    case 0x3d4a8:if(!ob1b_change(c,0x9b,4,true))return false;return ob1b_animation_record(c,0x3e778,0x3d4c2);
    case 0x3d4c2:case 0x3d856:return ob1b_animation(c,0x3e92e,r.pc==0x3d4c2U?0x3d4d2U:0x3d866U); // MOVEA.L #3e92e,A1; ...; JSR 49f8c.l.
    // MOVE.B #1,9d(A6); CLR.L 64(A6); MOVE.L #3d4e2,(A6).
    case 0x3d4d2:if(!ob1b_put(c,0x9d,1,1) || !ob1b_put(c,0x64,4,0))return false;return ob1b_install(c,0x3d4e2,0x3d4e2);
    case 0x3d4ea:if(!ob1b_bit(c,0x9b,0,bit))return false;r.pc=bit?0x3d4f4:0x3d51a;return true; // BTST.B #0,9b(A6); BEQ.W 3d51a.
    // MOVE.B #0,9d(A6); MOVE.W 84(A6),D0; MOVE.B #1,D1; JSR 4d4b4.l.
    case 0x3d4f4:
        if(!ob1b_put(c,0x9d,1,0) || !ob1b_get(c,0x84,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],1);
        return am_call(c,0x4d4b4,0x3d508);
    // MOVE.L #3d280,(A6); MOVE.L #0,56(A6); BRA.W 3dbba.
    case 0x3d508:if(!am_write(c,r.a[6],4,0x3d280) || !ob1b_put(c,0x56,4,0))return false;r.pc=0x3dbba;return true;
    case 0x3d51a:if(!ob1b_put(c,0x56,4,0))return false;r.pc=0x3dbbe;return true; // MOVE.L #0,56(A6); BRA.W 3dbbe.
    // ---- 3d7e8 (installed by 3d7e2): JSR 3dde4(PC); BTST.B #1,D0; BEQ.W 3d7fc.
    case 0x3d7e8:return am_call(c,0x3dde4,0x3d7ec);
    case 0x3d7ec:r.pc=((r.d[0]>>1)&1U)==0U?0x3d7fc:0x3d7f4;return true;
    case 0x3d7f4:r.pc=((r.d[0]>>5)&1U)!=0U?0x3d498:0x3d7fc;return true; // BTST.B #5,D0; BNE.W 3d498.
    case 0x3d7fc:r.pc=((r.d[0]>>7)&1U)!=0U?0x3d81e:0x3d804;return true; // BTST.B #7,D0; BNE.W 3d81e.
    case 0x3d804:if(!ob1b_zero_b(c,0x62,zero))return false;r.pc=zero?0x3d812:0x3d80c;return true; // TST.B 62(A6); BEQ.W 3d812.
    case 0x3d80c:return ob1b_install(c,0x3d526,0x3d812);                // MOVE.L #3d526,(A6).
    case 0x3d81a:r.pc=0x3dbbe;return true;                               // BRA.W 3dbbe.
    case 0x3d81e:return ob1b_call_d0(c,0x1ac8,0x3af8,0x3d828);          // MOVE.W #1ac8,D0; JSR 3af8.l.
    // MOVE.B #3,9a(A6); MOVE.B #1,D1; JSR 3dcda(PC).
    case 0x3d828:if(!ob1b_put(c,0x9a,1,3))return false;am_byte(r.d[1],1);return am_call(c,0x3dcda,0x3d836);
    // MOVE.B #40,ac(A6); BSET.B #4,9b(A6); MOVEA.L #3e760,A1; MOVE.W #100,D0; LEA 8a(A6),A0; JSR 49f96.l.
    case 0x3d836:
        if(!ob1b_put(c,0xac,1,0x40) || !ob1b_change(c,0x9b,4,true))return false;return ob1b_animation_record(c,0x3e760,0x3d856);
    // MOVE.B #0,9d(A6); MOVE.L #3f644,80(A6); JSR 496c2.l.
    case 0x3d866:if(!ob1b_put(c,0x9d,1,0) || !ob1b_put(c,0x80,4,0x3f644))return false;return am_call(c,0x496c2,0x3d87a);
    case 0x3d87a:return ob1b_install(c,0x3d880,0x3d880);                // MOVE.L #3d880,(A6).
    case 0x3d880:return am_call(c,0x3de46,0x3d884);                      // JSR 3de46(PC).
    case 0x3d884:return am_call(c,0x3dcf2,0x3d888);                      // JSR 3dcf2(PC).
    case 0x3d888:return am_call(c,0x3dd0e,0x3d88c);                      // BSR.W 3dd0e.
    case 0x3d88c:r.a[0]=0x3fa9c;return am_call(c,0x4ae4a,0x3d898);      // LEA 3fa9c.l,A0; JSR 4ae4a.l.
    case 0x3d898:r.pc=(r.d[0]&65535U)>=9U?0x3d8cc:0x3d8a0;return true;   // CMPI.W #9,D0; BCC.W 3d8cc.
    // ADD.W D0,D0 twice; JMP 3d8a8(PC,D0.W): the BRA.W table (9 slots) is transcribed, any other D0.W jumps to base + sext(D0.W).
    case 0x3d8a0:am_word(r.d[0],(r.d[0]*4U)&65535U);r.pc=am_index(0x3d8a8,r.d[0]);return true;
    case 0x3d8a8:case 0x3d8b4:case 0x3d8b8:case 0x3d8bc:case 0x3d8c0:case 0x3d8c4:case 0x3d8c8:r.pc=0x3d8cc;return true; // BRA.W 3d8cc.
    case 0x3d8ac:case 0x3d8b0:r.pc=0x3d8de;return true;                  // BRA.W 3d8de (slots 1 and 2).
    // SUBQ.B #1,ac(A6); BPL.W 3d8da.
    case 0x3d8cc:
        if(!ob1b_get(c,0xac,1,value))return false;value=(value-1U)&255U;if(!ob1b_put(c,0xac,1,value))return false;
        r.pc=(value&0x80U)==0U?0x3d8da:0x3d8d4;return true;
    case 0x3d8d4:return ob1b_install(c,0x3d8de,0x3d8da);                // MOVE.L #3d8de,(A6).
    case 0x3d8da:case 0x3dacc:r.pc=0x3dc40;return true;                  // BRA.W 3dc40.
    // ---- 3d8de chain (installed by 3d8d4, table slots 3d8ac 3d8b0): LEA 3faba.l,A0; JSR 4ae4a.l.
    case 0x3d8de:r.a[0]=0x3faba;return am_call(c,0x4ae4a,0x3d8ea);
    // MOVEQ #1,D0; MOVEQ #0,D1; JSR 4ff96.l (boundary).
    case 0x3d8ea:case 0x3dae4:r.d[0]=1;r.d[1]=0;return am_call(c,0x4ff96,r.pc==0x3d8eaU?0x3d8f4U:0x3daeeU);
    case 0x3d8f4:case 0x3daee:return am_call(c,0xd3d7c,r.pc==0x3d8f4U?0x3d8faU:0x3daf4U); // JSR d3d7c.l (boundary).
    case 0x3d8fa:if(!ob1b_debris(c,0xfff20000U,0x280000U,0xa))return false;return am_call(c,0xd3d7c,0x3d916);
    case 0x3d916:if(!ob1b_debris(c,0xa0000U,0x250000U,7))return false;return am_call(c,0xd3d7c,0x3d932);
    case 0x3d932:if(!ob1b_debris(c,0xfff70000U,0xffff0000U,7))return false;return am_call(c,0xd3d7c,0x3d94e);
    case 0x3d94e:if(!ob1b_debris(c,0x70000U,0xfffc0000U,5))return false;return ob1b_child(c,0x3d974);
    case 0x3d974:r.d[0]=0;r.d[1]=0x10;return am_call(c,0x49214,0x3d97e); // MOVEQ #0,D0; MOVEQ #10,D1; JSR 49214.l.
    case 0x3d97e:r.pc=0x3db62;return true;                               // BRA.W 3db62.
    case 0x3db5c:r.pc=0x2a00;return true;                                // JMP 2a00.l.
    // ---- 3da72 (installed by 3da6c): JSR 4d8d8.l; TST.B D0; BMI.W 3daa4.
    case 0x3da72:return am_call(c,0x4d8d8,0x3da78);
    case 0x3da78:r.pc=(r.d[0]&0x80U)!=0U?0x3daa4:0x3da7e;return true;
    case 0x3da7e:return am_call(c,0x3dde4,0x3da82);                      // JSR 3dde4(PC).
    case 0x3da82:r.pc=((r.d[0]>>5)&1U)==0U?0x3da98:0x3da8a;return true; // BTST.B #5,D0; BEQ.W 3da98.
    // MOVE.B #0,9d(A6); MOVE.B #1,D1; JSR 3dcda(PC).
    case 0x3da8a:if(!ob1b_put(c,0x9d,1,0))return false;am_byte(r.d[1],1);return am_call(c,0x3dcda,0x3da98);
    case 0x3da98:return am_call(c,0x3dcac,0x3da9c);                      // JSR 3dcac(PC).
    case 0x3da9c:return am_call(c,0x3de54,0x3daa0);                      // JSR 3de54(PC).
    case 0x3daa0:r.pc=0x3daae;return true;                               // BRA.W 3daae.
    case 0x3daa4:if(!ob1b_put(c,0x9d,1,0))return false;return am_call(c,0x3de46,0x3daae); // MOVE.B #0,9d(A6); JSR 3de46(PC).
    case 0x3daae:return am_call(c,0x3dcf2,0x3dab2);                      // JSR 3dcf2(PC).
    case 0x3dab2:return am_call(c,0x3dd0e,0x3dab6);                      // BSR.W 3dd0e.
    case 0x3dab6:if(!ob1b_zero_b(c,0xa4,zero))return false;r.pc=zero?0x3dac2:0x3dabe;return true; // TST.B a4(A6); BEQ.W 3dac2.
    // SUBQ.B #1,a4(A6).
    case 0x3dabe:if(!ob1b_get(c,0xa4,1,value) || !ob1b_put(c,0xa4,1,(value-1U)&255U))return false;r.pc=0x3dac2;return true;
    // BNE.W 3dacc: Z of 3dab6 (BYTE zero) or of 3dabe (the decremented BYTE) = BYTE a4(A6) is zero.
    case 0x3dac2:if(!ob1b_zero_b(c,0xa4,zero))return false;r.pc=zero?0x3dac6:0x3dacc;return true;
    case 0x3dac6:return ob1b_install(c,0x3dad0,0x3dacc);                // MOVE.L #3dad0,(A6).
    case 0x3dad0:r.a[0]=0x3fad8;return am_call(c,0x4ae4a,0x3dadc);      // LEA 3fad8.l,A0; JSR 4ae4a.l.
    case 0x3dadc:am_byte(r.d[1],0);return am_call(c,0x3dcda,0x3dae4);   // MOVE.B #0,D1; JSR 3dcda(PC).
    // MOVE.L #fff30000,36(A0); MOVE.L #180000,3a(A0); MOVE.W #a,54(A0); JSR d3d7c.l.
    case 0x3daf4:if(!ob1b_debris(c,0xfff30000U,0x180000U,0xa))return false;return am_call(c,0xd3d7c,0x3db10);
    case 0x3db10:if(!ob1b_debris(c,0xb0000U,0x150000U,7))return false;return am_call(c,0xd3d7c,0x3db2c);
    case 0x3db2c:if(!ob1b_debris(c,0x80000U,0xfffc0000U,5))return false;return ob1b_child(c,0x3db52);
    case 0x3db52:r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,0x3db5c);   // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.l.
    // ---- 28ae child 3db68: MOVE.W #18de,D0; JSR 3af8.l.
    case 0x3db68:return ob1b_call_d0(c,0x18de,0x3af8,0x3db72);
    // MOVE.W #363,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x3db72:am_word(r.d[0],0x363);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3db80);
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); MOVEA.L #6f536,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3db80:if(!ob1b_put(c,0x68,2,0x1001) || !ob1b_put(c,0x1e,2,0x1001))return false;return ob1b_animation(c,0x6f536,0x3db9c);
    case 0x3db9c:return ob1b_install(c,0x3dba2,0x3dba2);                // MOVE.L #3dba2,(A6).
    case 0x3dba2:return am_call(c,0x4be06,0x3dba8);                      // JSR 4be06.l.
    case 0x3dba8:return am_call(c,0x49fc6,0x3dbae);                      // JSR 49fc6.l.
    case 0x3dbae:return ob1b_carry(c,0x3dbb8,0x3dbb2);                  // BCC.W 3dbb8 (C returned by 49fc6).
    case 0x3dbb2:r.pc=0x2a00;return true;                                // JMP 2a00.l.
    case 0x3dbb8:case 0x3dcea:case 0x3dd2e:case 0x3def0:case 0x3e0a6:case 0x3e0a8:case 0x3e2f0:case 0xb16d4:case 0xb1cf6:
        return am_return(c);                                              // RTS.
    // ---- 3dbbe: BSR.W 3dd0e; JSR 3dd30(PC); JSR 3dcac(PC); BCS.W 3dbd8.
    case 0x3dbbe:return am_call(c,0x3dd0e,0x3dbc2);
    case 0x3dbc2:return am_call(c,0x3dd30,0x3dbc6);
    case 0x3dbc6:return am_call(c,0x3dcac,0x3dbca);
    case 0x3dbca:return ob1b_carry(c,0x3dbce,0x3dbd8);                  // BCS.W 3dbd8 (C returned by 3dcac -> 4d418).
    case 0x3dbce:if(!am_write(c,r.a[6],4,0x3d280))return false;r.pc=0x3dc24;return true; // MOVE.L #3d280,(A6); BRA.W 3dc24.
    // MOVE.W 84(A6),D0; JSR 4d7a6.l.
    case 0x3dbd8:if(!ob1b_get(c,0x84,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4d7a6,0x3dbe2);
    case 0x3dbe2:r.pc=(r.d[0]&255U)!=0x12U?0x3dbf2:0x3dbea;return true;  // CMPI.B #12,D0; BNE.W 3dbf2.
    // MOVE.B D1,a5(A6); MOVE.B D2,a6(A6).
    case 0x3dbea:if(!ob1b_put(c,0xa5,1,r.d[1]&255U) || !ob1b_put(c,0xa6,1,r.d[2]&255U))return false;r.pc=0x3dbf2;return true;
    // MOVE.W 84(A6),D0; JSR 4d734.l.
    case 0x3dbf2:if(!ob1b_get(c,0x84,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4d734,0x3dbfc);
    case 0x3dbfc:if(!ob1b_zero_b(c,0x5e,zero))return false;r.pc=zero?0x3dc24:0x3dc04;return true; // TST.B 5e(A6); BEQ.W 3dc24.
    case 0x3dc04:if(!ob1b_bit(c,0x61,6,bit))return false;r.pc=bit?0x3dc24:0x3dc0e;return true; // BTST.B #6,61(A6); BNE.W 3dc24.
    case 0x3dc0e:return ob1b_call_d0(c,0x1e,0x3df30,0x3dc16);           // MOVE.W #1e,D0; JSR 3df30(PC).
    case 0x3dc16:return ob1b_call_d0(c,0x1a59,0x3af8,0x3dc20);          // MOVE.W #1a59,D0; JSR 3af8.l.
    case 0x3dc20:return am_call(c,0x3e0a8,0x3dc24);                      // BSR.W 3e0a8.
    // ---- 3dcac: MOVE.W 84(A6),D0; MOVE.W #0,D2; TST.B a0(A6); BNE.W 3dcc4.
    case 0x3dcac:
        if(!ob1b_get(c,0x84,2,value))return false;am_word(r.d[0],value);am_word(r.d[2],0);
        if(!ob1b_zero_b(c,0xa0,zero))return false;r.pc=zero?0x3dcbc:0x3dcc4;return true;
    case 0x3dcbc:am_word(r.d[3],0x38);r.pc=0x3dcc8;return true;          // MOVE.W #38,D3; BRA.W 3dcc8.
    case 0x3dcc4:am_word(r.d[3],0x2ea);r.pc=0x3dcc8;return true;         // MOVE.W #2ea,D3.
    case 0x3dcc8:if(!ob1b_bit(c,0x15,0,bit))return false;r.pc=bit?0x3dcd2:0x3dcd4;return true; // BTST.B #0,15(A6); BEQ.W 3dcd4.
    case 0x3dcd2:am_word(r.d[2],(0x10000U-(r.d[2]&65535U))&65535U);r.pc=0x3dcd4;return true; // NEG.W D2.
    case 0x3dcd4:r.pc=0x4d418;return true;                               // JMP 4d418.l (boundary).
    // ---- 3dcda: MOVE.B D1,-(A7); JSR 4d8d8.l.
    case 0x3dcda:if(!am_push(c,1,r.d[1]&255U))return false;return am_call(c,0x4d8d8,0x3dce2);
    // MOVE.B (A7)+,D1; TST.B D0; BPL.W 3dcec.
    case 0x3dce2:if(!am_pop(c,1,value))return false;am_byte(r.d[1],value);r.pc=(r.d[0]&0x80U)==0U?0x3dcec:0x3dcea;return true;
    case 0x3dcec:r.pc=0x4d4b4;return true;                               // JMP 4d4b4.l (boundary).
    // ---- 3dd0e: BTST.B #0,9a(A6); BEQ.W 3dd1e; MOVE.W #8000,92(A6); BTST.B #1,9a(A6); BEQ.W 3dd2e; MOVE.W #8000,96(A6); RTS.
    case 0x3dd0e:if(!ob1b_bit(c,0x9a,0,bit))return false;r.pc=bit?0x3dd18:0x3dd1e;return true;
    case 0x3dd18:if(!ob1b_put(c,0x92,2,0x8000))return false;r.pc=0x3dd1e;return true;
    case 0x3dd1e:if(!ob1b_bit(c,0x9a,1,bit))return false;r.pc=bit?0x3dd28:0x3dd2e;return true;
    case 0x3dd28:if(!ob1b_put(c,0x96,2,0x8000))return false;r.pc=0x3dd2e;return true;
    // ---- 3dd30: MOVEQ #0,D0; MOVE.B a1(A6),D0; ADD.W D0,D0 twice; MOVE.L 3dd42(PC,D0.W),56(A6); RTS.
    case 0x3dd30:
        r.d[0]=0;if(!ob1b_get(c,0xa1,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],(r.d[0]*4U)&65535U);
        if(!am_read(c,am_index(OB1B_TABLE_3DD42,r.d[0]),4,value) || !ob1b_put(c,0x56,4,value))return false;return am_return(c);
    // ---- 3dde4: MOVE.W 84(A6),D0; JSR 49be0.l.
    case 0x3dde4:if(!ob1b_get(c,0x84,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49be0,0x3ddee);
    // MOVE.L (A0),D7; SWAP D7; MOVEQ #ff,D0; MOVE.W D0,D1; SWAP D0; MOVE.W D1,D0; AND.L D7,D0; AND.B 9f(A6),D0; OR.B D0,9e(A6); RTS.
    case 0x3ddee:
        if(!am_read(c,r.a[0],4,value))return false;r.d[7]=(value<<16)|(value>>16);am_word(r.d[1],0xffffU);
        r.d[0]=r.d[7];if(!ob1b_get(c,0x9f,1,value))return false;am_byte(r.d[0],r.d[0]&value);
        if(!ob1b_get(c,0x9e,1,value) || !ob1b_put(c,0x9e,1,(value|r.d[0])&255U))return false;return am_return(c);
    // ---- 3de54: MOVE.L 64(A6),36(A6); MOVE.L 42(A6),-(A7); JSR 43ea4.l.
    case 0x3de54:
        if(!ob1b_get(c,0x64,4,value) || !ob1b_put(c,0x36,4,value) || !ob1b_get(c,0x42,4,value) || !am_push(c,4,value))return false;
        return am_call(c,0x43ea4,0x3de64);
    // LEA 3def2(PC),A1; MOVE.L (A7)+,D0; MOVE.L 42(A6),D2; SUB.L D2,2e(A6); MOVE.L 53bc(A5),D4; ADD.L 53a2(A5),D4; MOVE.L D4,D5;
    // SUB.L D4,D0; SUB.L D5,D2; MOVEQ #0,D7; MOVE.W (A1),D7; SWAP D7; CMP.L D0,D7; BLE.W 3de8e.
    case 0x3de64:
        r.a[1]=OB1B_DATA_3DEF2;if(!am_pop(c,4,value))return false;r.d[0]=value;
        if(!ob1b_get(c,0x42,4,value))return false;r.d[2]=value;if(!ob1b_get(c,0x2e,4,value) || !ob1b_put(c,0x2e,4,value-r.d[2]))return false;
        if(!ob1b_get_at(c,r.a[5],0x53bc,4,value) || !ob1b_get_at(c,r.a[5],0x53a2,4,other))return false;
        r.d[4]=value+other;r.d[5]=r.d[4];r.d[0]-=r.d[4];r.d[2]-=r.d[5];
        if(!am_read(c,r.a[1],2,value))return false;r.d[7]=(value&65535U)<<16;
        r.pc=!ob1b_less(r.d[0],r.d[7])?0x3de8e:0x3de8c;return true;    // BLE: D7 <= D0 (signed).
    case 0x3de8c:r.d[7]=r.d[0];r.pc=0x3de8e;return true;                 // MOVE.L D0,D7.
    case 0x3de8e:r.pc=!ob1b_less(r.d[2],r.d[7])?0x3de9a:0x3de94;return true; // CMP.L D7,D2; BGE.W 3de9a (D2 >= D7 signed).
    case 0x3de94:r.d[2]=r.d[7];am_byte(r.d[6],0xff);r.pc=0x3de9a;return true; // MOVE.L D7,D2; MOVE.B #ff,D6.
    // SWAP D7; ADD.W 4(A1),D7; SWAP D7; CMP.L D0,D7; BGE.W 3deaa.
    case 0x3de9a:
        if(!am_read(c,am_index(r.a[1],4),2,value))return false;
        r.d[7]=(r.d[7]<<16)|(r.d[7]>>16);am_word(r.d[7],r.d[7]+value);r.d[7]=(r.d[7]<<16)|(r.d[7]>>16);
        r.pc=!ob1b_less(r.d[7],r.d[0])?0x3deaa:0x3dea8;return true;
    case 0x3dea8:r.d[7]=r.d[0];r.pc=0x3deaa;return true;                 // MOVE.L D0,D7.
    case 0x3deaa:r.pc=!ob1b_less(r.d[7],r.d[2])?0x3deb4:0x3deb0;return true; // CMP.L D7,D2; BLE.W 3deb4 (D2 <= D7 signed).
    case 0x3deb0:r.d[2]=r.d[7];r.d[6]=0xffffffffU;r.pc=0x3deb4;return true; // MOVE.L D7,D2; MOVEQ #ff,D6.
    // ADD.L D4,D0; ADD.L D5,D2; MOVE.L D2,42(A6); MOVE.L 2e(A6),-(A7); ADD.L D2,2e(A6); MOVE.W 42(A6),D0; MOVE.W 46(A6),D1;
    // MOVEQ #ff,D7; JSR 19a00.l.
    case 0x3deb4:
        r.d[0]+=r.d[4];r.d[2]+=r.d[5];if(!ob1b_put(c,0x42,4,r.d[2]))return false;
        if(!ob1b_get(c,0x2e,4,value) || !am_push(c,4,value) || !ob1b_put(c,0x2e,4,value+r.d[2]))return false;
        if(!ob1b_get(c,0x42,2,value))return false;am_word(r.d[0],value);if(!ob1b_get(c,0x46,2,value))return false;am_word(r.d[1],value);
        r.d[7]=0xffffffffU;return am_call(c,0x19a00,0x3ded4);
    // MOVE.L (A7)+,D1; MOVE.W #980,D0; CMP.W 2e(A6),D0; BGT.W 3def0.
    case 0x3ded4:
        if(!am_pop(c,4,value))return false;r.d[1]=value;am_word(r.d[0],0x980);if(!ob1b_get(c,0x2e,2,value))return false;
        r.pc=ob1b_less_word(value,r.d[0])?0x3def0:0x3dee2;return true;   // BGT: D0.W > WORD (signed).
    // MOVE.W D0,2e(A6); MOVE.L 2e(A6),42(A6); SUB.L D1,42(A6).
    case 0x3dee2:
        if(!ob1b_put(c,0x2e,2,r.d[0]&65535U) || !ob1b_get(c,0x2e,4,value) || !ob1b_put(c,0x42,4,value))return false;
        if(!ob1b_get(c,0x42,4,value) || !ob1b_put(c,0x42,4,value-r.d[1]))return false;r.pc=0x3def0;return true;
    // ---- 3defa: MOVEA.L 80(A6),A0; MOVE.W (A0)+,D1; BPL.W 3df22.
    case 0x3defa:
        if(!ob1b_get(c,0x80,4,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);r.a[0]+=2U;
        r.pc=(value&0x8000U)==0U?0x3df22:0x3df04;return true;
    // NEG.W D1; CMPI.W #4,D1; BCC.W 3df1e.
    case 0x3df04:am_word(r.d[1],(0x10000U-(r.d[1]&65535U))&65535U);r.pc=(r.d[1]&65535U)>=4U?0x3df1e:0x3df0e;return true;
    // MOVE.B 19(A6,D1.W),14(A6); MOVE.L A0,80(A6); RTS.
    case 0x3df0e:
        if(!am_read(c,am_index(am_index(r.a[6],0x19),r.d[1]),1,value) || !ob1b_put(c,0x14,1,value) || !ob1b_put(c,0x80,4,r.a[0]))return false;
        return am_return(c);
    // ADDA.W (A0),A0; MOVE.W (A0)+,D1.
    case 0x3df1e:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]=am_index(r.a[0],value);
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);r.a[0]+=2U;r.pc=0x3df22;return true;
    // MOVE.L A0,80(A6); MOVE.B 14(A6),D0; JMP 8d34.l (boundary).
    case 0x3df22:
        if(!ob1b_put(c,0x80,4,r.a[0]) || !ob1b_get(c,0x14,1,value))return false;am_byte(r.d[0],value);r.pc=0x8d34;return true;
    // ---- 3df30: ANDI.W #fffe,D0; MOVE.W 88(A6),D1; ANDI.W #1,D1; OR.W D1,D0; MOVE.W D0,88(A6); RTS.
    case 0x3df30:
        if(!ob1b_get(c,0x88,2,value))return false;am_word(r.d[1],value&1U);am_word(r.d[0],(r.d[0]&0xfffeU)|(value&1U));
        if(!ob1b_put(c,0x88,2,r.d[0]&65535U))return false;return am_return(c);
    // ---- 3e03e: JSR 3de06(PC).
    case 0x3e03e:return am_call(c,0x3de06,0x3e042);
    // MOVE.B 1b(A6),14(A6); MOVE.L #0,64(A6); MOVE.L #0,80(A6); MOVE.W #0,88(A6); MOVE.B #0,a1(A6); MOVE.B #0,9d(A6); JSR 3dd30(PC).
    case 0x3e042:
        if(!ob1b_get(c,0x1b,1,value) || !ob1b_put(c,0x14,1,value) || !ob1b_put(c,0x64,4,0) || !ob1b_put(c,0x80,4,0) || !ob1b_put(c,0x88,2,0) ||
            !ob1b_put(c,0xa1,1,0) || !ob1b_put(c,0x9d,1,0))return false;
        return am_call(c,0x3dd30,0x3e06e);
    case 0x3e06e:r.a[0]=0;return am_call(c,0x4b82e,0x3e078);            // LEA 0.w,A0; JSR 4b82e.l.
    // BCLR.B #7,61(A6); BSET.B #5,9b(A6); BCLR.B #4,9b(A6); MOVE.B #0,5e(A6); CLR.B 9e(A6); CLR.B 9f(A6); MOVE.W 84(A6),D0; MOVE.B #1,D7; JSR 4d98a.l.
    case 0x3e078:
        if(!ob1b_change(c,0x61,7,false) || !ob1b_change(c,0x9b,5,true) || !ob1b_change(c,0x9b,4,false) || !ob1b_put(c,0x5e,1,0) ||
            !ob1b_put(c,0x9e,1,0) || !ob1b_put(c,0x9f,1,0) || !ob1b_get(c,0x84,2,value))return false;
        am_word(r.d[0],value);am_byte(r.d[7],1);return am_call(c,0x4d98a,0x3e0a6);
    // ---- 3e250 (28ae child of 3d3fa): MOVE.W #1a3,20(A6); MOVE.L 2001a0.l,22(A6); MOVE.W #1a60,D0; JSR 3af8.l.
    case 0x3e250:
        if(!ob1b_put(c,0x20,2,0x1a3) || !am_read(c,OB1B_BANK_1A3,4,value) || !ob1b_put(c,0x22,4,value))return false;
        return ob1b_call_d0(c,0x1a60,0x3af8,0x3e268);
    // BSET.B #6,15(A6); MOVE.W #5,68(A6); MOVE.W #5,1e(A6); JSR 491c4.l.
    case 0x3e268:
        if(!ob1b_change(c,0x15,6,true) || !ob1b_put(c,0x68,2,5) || !ob1b_put(c,0x1e,2,5))return false;return am_call(c,0x491c4,0x3e280);
    // MOVE.W 84(A0),84(A6); MOVE.W 86(A0),86(A6); MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B b0(A0),D1; JSR 49290.l.
    case 0x3e280:
        if(!ob1b_get_at(c,r.a[0],0x84,2,value) || !ob1b_put(c,0x84,2,value) || !ob1b_get_at(c,r.a[0],0x86,2,value) || !ob1b_put(c,0x86,2,value))return false;
        r.d[0]=0;r.d[1]=0;if(!ob1b_get_at(c,r.a[0],0xb0,1,value))return false;am_byte(r.d[1],value);return am_call(c,0x49290,0x3e29a);
    // LEA 3fc76.l,A1; MOVE.W 86(A6),D0; ADD.W D0,D0 twice; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3e29a:
        r.a[1]=0x3fc76;if(!ob1b_get(c,0x86,2,value))return false;am_word(r.d[0],(value*4U)&65535U);
        if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3e2b6);
    // MOVE.W 86(A6),D0; LEA 3fc6e.l,A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x3e2b6:
        if(!ob1b_get(c,0x86,2,value))return false;r.a[0]=0x3fc6e;am_word(r.d[0],(value*2U)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3e2d0);
    case 0x3e2d0:return ob1b_install(c,0x3e2d6,0x3e2d6);                // MOVE.L #3e2d6,(A6).
    case 0x3e2d6:return am_call(c,0x288c,0x3e2dc);                       // JSR 288c.l.
    case 0x3e2dc:return ob1b_carry(c,0x3e2f2,0x3e2e0);                  // BCC.W 3e2f2 (C returned by 288c).
    case 0x3e2e0:return am_call(c,0x43e34,0x3e2e6);                      // JSR 43e34.l.
    case 0x3e2e6:return am_call(c,0x49fc6,0x3e2ec);                      // JSR 49fc6.l.
    case 0x3e2ec:return ob1b_carry(c,0x3e2f0,0x3e2f2);                  // BCS.W 3e2f2 (C returned by 49fc6).
    // MOVEA.L c(A6),A0; MOVE.B #ff,62(A0); JMP 2a00.l.
    case 0x3e2f2:
        if(!ob1b_get(c,0xc,4,value))return false;r.a[0]=value;if(!ob1b_put_at(c,r.a[0],0x62,1,0xff))return false;r.pc=0x2a00;return true;
    // ---- N19b: b1656 (stage event callback table e8ec8): JSR b1c82(PC); JMP 2a00.l.
    case 0xb1656:return am_call(c,0xb1c82,0xb165a);
    case 0xb165a:r.pc=0x2a00;return true;
    // ---- 28ae child b1660: MOVE.W #1fb,20(A6); MOVE.B #0,9e(A6); JSR b1c0e(PC).
    case 0xb1660:if(!ob1b_put(c,0x20,2,0x1fb) || !ob1b_put(c,0x9e,1,0))return false;return am_call(c,0xb1c0e,0xb1670);
    // MOVE.W 8e(A6),D0; ADD.W D0,D0 twice; LEA b15c0(PC),A0; MOVE.L (A0,D0.W),86(A6); JSR b160a(PC).
    case 0xb1670:
        if(!ob1b_get(c,0x8e,2,value))return false;am_word(r.d[0],(value*4U)&65535U);r.a[0]=OB1B_TABLE_B15C0;
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value) || !ob1b_put(c,0x86,4,value))return false;return am_call(c,0xb160a,0xb1686);
    case 0xb1686:return ob1b_call_d0(c,0x1e1,0x49a84,0xb1690);          // MOVE.W #1e1,D0; JSR 49a84.l.
    // ADD.W 7a(A6),D0; SUBI.W #f0,D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,36(A6); BMI.W b16aa.
    case 0xb1690:
        if(!ob1b_get(c,0x7a,2,value))return false;am_word(r.d[0],r.d[0]+value-0xf0U);r.d[0]=am_extend_word(r.d[0])<<8;
        if(!ob1b_put(c,0x36,4,r.d[0]))return false;r.pc=(r.d[0]&0x80000000U)!=0U?0xb16aa:0xb16a4;return true;
    case 0xb16a4:if(!ob1b_change(c,0x15,0,true))return false;r.pc=0xb16aa;return true; // BSET.B #0,15(A6).
    case 0xb16aa:return ob1b_install(c,0xb16b0,0xb16b0);                // MOVE.L #b16b0,(A6).
    // MOVE.L 86(A6),3a(A6); SUBI.L #ffffec00,86(A6); JSR b15e0(PC).
    case 0xb16b0:
        if(!ob1b_get(c,0x86,4,value) || !ob1b_put(c,0x3a,4,value) || !ob1b_put(c,0x86,4,value-0xffffec00U))return false;
        return am_call(c,0xb15e0,0xb16c2);
    case 0xb16c2:return ob1b_carry(c,0xb16c6,0xb19b2);                  // BCS.W b19b2 (C returned by b15e0).
    case 0xb16c6:return am_call(c,0x43ea4,0xb16cc);                      // JSR 43ea4.l.
    case 0xb16cc:return am_call(c,0xb1b76,0xb16d0);                      // JSR b1b76(PC).
    case 0xb16d0:return am_call(c,0xb1dfa,0xb16d4);                      // JSR b1dfa(PC).
    // ---- b16d6 (stage event callback table e8ed0): MOVE.W #1fb,20(A6); MOVE.B #2,9e(A6); JSR b1c0e(PC); BRA.W b186a.
    case 0xb16d6:if(!ob1b_put(c,0x20,2,0x1fb) || !ob1b_put(c,0x9e,1,2))return false;return am_call(c,0xb1c0e,0xb16e6);
    case 0xb16e6:r.pc=0xb186a;return true;
    // ---- b1c82: MOVE.W 78(A6),D0; SUBQ.W #1,D0; CMPI.W #5,D0; BLS.W b1c9e (else the TRAP #f at b1c90: boundary).
    case 0xb1c82:
        if(!ob1b_get(c,0x78,2,value))return false;am_word(r.d[0],value-1U);r.pc=(r.d[0]&65535U)<=5U?0xb1c9e:0xb1c90;return true;
    case 0xb1c9e:r.d[1]=0;r.pc=0xb1ca0;return true;                      // MOVEQ #0,D1.
    // MOVEM.W D0-D1,-(A7); MOVEA.L #b1660,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0xb1ca0:
        if(!am_push(c,2,r.d[1]&65535U) || !am_push(c,2,r.d[0]&65535U))return false;
        r.a[0]=0xb1660;am_word(r.d[0],0x14);return am_call(c,0x28ae,0xb1cb4);
    case 0xb1cb4:return ob1b_carry(c,0xb1cc6,0xb1cb8);                  // BCC.W b1cc6 (C returned by 28ae).
    case 0xb1cb8:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0xb1cc2); // CLR.W D0; CLR.W D1; JSR 4970a.l.
    case 0xb1cc2:r.carry=AnimationCarrySet;r.pc=0xb1cc6;return true;     // ORI.B #1,CCR.
    case 0xb1cc6:return am_call(c,0xb1cf8,0xb1cca);                      // JSR b1cf8(PC).
    // MOVEM.W (A7)+,D0-D1 (sign-extended).
    case 0xb1cca:
        if(!ob1b_pop_word_ext(c,r.d[0]) || !ob1b_pop_word_ext(c,r.d[1]))return false;r.pc=0xb1cce;return true;
    // MOVEM.L D0-D1/A0,-(A7); MOVE.W #5,D0; JSR 49a84.l.
    case 0xb1cce:
        if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;
        am_word(r.d[0],5);return am_call(c,0x49a84,0xb1cdc);
    // MOVE.W D0,D2; ANDI.L #1f,D2; MOVEM.L (A7)+,D0-D1/A0; BTST.L D2,D1; BNE.B b1cce.
    case 0xb1cdc:
        am_word(r.d[2],r.d[0]);r.d[2]&=0x1fU;
        if(!am_pop(c,4,value))return false;r.d[0]=value;if(!am_pop(c,4,value))return false;r.d[1]=value;if(!am_pop(c,4,value))return false;r.a[0]=value;
        r.pc=((r.d[1]>>(r.d[2]&31U))&1U)!=0U?0xb1cce:0xb1cec;return true;
    // BSET.B D2,D1; MOVE.W D2,8e(A0); SUBQ.W #1,D0; BPL.B b1ca0.
    case 0xb1cec:
        r.d[1]|=1U<<(r.d[2]&31U);if(!ob1b_put_at(c,r.a[0],0x8e,2,r.d[2]&65535U))return false;
        am_word(r.d[0],r.d[0]-1U);r.pc=(r.d[0]&0x8000U)==0U?0xb1ca0:0xb1cf6;return true;
    // ---- b1d8c: JSR 49a58.l; ANDI.W #ff,D0; MOVE.W D0,D1; MOVE.L #40000,D0; JSR 443d2.l.
    case 0xb1d8c:return am_call(c,0x49a58,0xb1d92);
    case 0xb1d92:am_word(r.d[0],r.d[0]&255U);am_word(r.d[1],r.d[0]);r.d[0]=0x40000;return am_call(c,0x443d2,0xb1da4);
    // ADD.L D0,36(A6); ADD.L D1,3a(A6); RTS.
    case 0xb1da4:
        if(!ob1b_get(c,0x36,4,value) || !ob1b_put(c,0x36,4,value+r.d[0]) || !ob1b_get(c,0x3a,4,value) || !ob1b_put(c,0x3a,4,value+r.d[1]))return false;
        return am_return(c);
    default:return am_error(c,"unsupported animation objects b1b PC");
    }
}
}
