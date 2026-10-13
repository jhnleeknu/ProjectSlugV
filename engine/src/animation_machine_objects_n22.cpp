#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONGs (live bus, current PVC bank): animation records of 3df44 / 3e0f6 (id 1a3) and of the 41fe6 child (id 12a).
const std::uint32_t ON22_BANK_1A3=0x2001a0;
const std::uint32_t ON22_BANK_12A=0x2000b8;
bool on22_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on22_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// BYTE bit of the memory operand at address (BTST.B #bit,<ea>): true when the bit is 1.
bool on22_bit(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,<ea> (read, then write the BYTE; only Z changes, which no N22a branch reads).
bool on22_change(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    value=set?(value|(1U<<bit)):(value&~(1U<<bit));return am_write(c,address,1,value&255U);
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on22_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n22 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,(A6) then continue at next_pc.
bool on22_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// MOVE.W #id,20(A6); MOVE.L bank,22(A6) (the bank LONG is read after the WORD write).
bool on22_animation_id(AnimationMachineContext& c,std::uint32_t id,std::uint32_t bank) {
    std::uint32_t value=0;
    return on22_put(c,0x20,2,id) && am_read(c,bank,4,value) && on22_put(c,0x22,4,value);
}
// MOVE.W #d0,D0; MOVE.B #1,D1; JSR 8ebe.l (3de06 sequence).
bool on22_sound(AnimationMachineContext& c,std::uint32_t d0,std::uint32_t return_pc) {
    am_word(c.s.d[0],d0);am_byte(c.s.d[1],1);return am_call(c,0x8ebe,return_pc);
}
// 28ae child record (3df96 / 3dfe6): LONG 76 = A6 + offset, BYTEs 7a..7e, then ORI #1,CCR.
bool on22_child(AnimationMachineContext& c,std::uint32_t offset,std::uint32_t b7a,std::uint32_t b7b,std::uint32_t b7c,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;r.a[1]=am_index(r.a[6],offset);
    if(!am_write(c,am_index(r.a[0],0x76),4,r.a[1]) || !am_write(c,am_index(r.a[0],0x7a),1,b7a) || !am_write(c,am_index(r.a[0],0x7b),1,b7b) ||
        !am_write(c,am_index(r.a[0],0x7c),1,b7c) || !am_write(c,am_index(r.a[0],0x7d),1,0) || !am_write(c,am_index(r.a[0],0x7e),1,0))return false;
    r.carry=AnimationCarrySet;r.pc=next_pc;return true;
}
// BSET.B #6,15(A0); MOVE.W #6,68(A0); MOVE.W #6,1e(A0) (3dfc0 / 3e010).
bool on22_child_flags(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    return on22_change(c,am_index(r.a[0],0x15),6,true) && am_write(c,am_index(r.a[0],0x68),2,6) && am_write(c,am_index(r.a[0],0x1e),2,6);
}
// WORD table (fixed ROM, live bus): D0 = BYTE 7a(A6) (MOVEQ #0 first), D0.W = 2 * D0.W, value = WORD(table + sext(D0.W)).
bool on22_table_word(AnimationMachineContext& c,std::uint32_t table,std::uint32_t& value) {
    AnimationMachineState& r=c.s;std::uint32_t index=0;r.d[0]=0;
    if(!on22_get(c,0x7a,1,index))return false;am_byte(r.d[0],index);am_word(r.d[0],(r.d[0]*2U)&65535U);r.a[0]=table;
    return am_read(c,am_index(r.a[0],r.d[0]),2,value);
}
}
// Objects F4 N22a (151 block starts): the stage event callback 3d228 (3df44 children 41fe6 / 3e0f6, installs 3d280 3d32c 3d3b2 3d2b4,
// shared tail 3dbba / 3dc24), the N23 callees 1bf02 1bfb4, the code pointer 3d3de, the 28ae children 41fe6 and 3e0f6 (installs 3e1ce
// 3e214, LONG table targets 3e1c2 3e1ec, continuations 3e1e2 3e22a). Boundaries without an executor: 484b4 4d2d4 4d508 4d766 4da50
// (N23 / N35) and 3dcac 3defa (N22b). 3e1b6 JMP (A0) is a live target. The 16 BCC/BCS/SCS consumers read the C of their callee; ORI
// CCR (1bf5c 3d3ea 3df96 3dfe6) sets, 3d3de (TST.B) clears and 3dd08 (LSR.B #1) computes a known C. No port, no bank change.
bool animation_objects_n22_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool bit=false;
    switch(r.pc) {
    // ---- 1bf02 (N23 4d36e JSR (A1)): MOVE.L A0,-(A7); JSR 484b4.l; BCC.W 1bf66.
    case 0x1bf02:if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x484b4,0x1bf0a);
    case 0x1bf0a:return on22_carry(c,0x1bf66,0x1bf0e);
    case 0x1bf0e:r.pc=(r.d[0]&255U)!=0U?0x1bf1e:0x1bf14;return true;     // TST.B D0; BNE.W 1bf1e.
    case 0x1bf14:case 0x1bfbc:r.a[0]=0x100cb8;r.pc=r.pc==0x1bf14?0x1bf24:0x1bfcc;return true; // LEA 100cb8.l,A0; BRA.W.
    case 0x1bf1e:case 0x1bfc6:r.a[0]=0x100da8;r.pc=r.pc==0x1bf1e?0x1bf24:0x1bfcc;return true; // LEA 100da8.l,A0.
    case 0x1bf24:return am_call(c,0x289e,0x1bf2a);                       // JSR 289e.l.
    case 0x1bf2a:return on22_carry(c,0x1bf66,0x1bf2e);                  // BCC.W 1bf66 (C returned by 289e).
    // BTST.B #7,61(A0) / 15(A0); BNE.W 1bf66.
    case 0x1bf2e:case 0x1bf52:
        if(!on22_bit(c,am_index(r.a[0],r.pc==0x1bf2e?0x61U:0x15U),7,bit))return false;
        r.pc=bit?0x1bf66:(r.pc==0x1bf2e?0x1bf38U:0x1bf5cU);return true;
    // LEA 1bef8(PC),A1; MOVEQ #0,D0; MOVE.B 9f(A0),D0; TST.B (A1,D0.W); BEQ.W 1bf66.
    case 0x1bf38:
        r.a[1]=0x1bef8;r.d[0]=0;if(!am_read(c,am_index(r.a[0],0x9f),1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,am_index(r.a[1],r.d[0]),1,value))return false;r.pc=(value&255U)==0U?0x1bf66:0x1bf4a;return true;
    // TST.L 3a(A0); BPL.W 1bf66.
    case 0x1bf4a:if(!am_read(c,am_index(r.a[0],0x3a),4,value))return false;r.pc=(value&0x80000000U)==0U?0x1bf66:0x1bf52;return true;
    // MOVEQ #0,D0; MOVEA.L (A7)+,A0; ORI.B #1,CCR; RTS.
    case 0x1bf5c:r.d[0]=0;if(!am_pop(c,4,value))return false;r.a[0]=value;r.carry=AnimationCarrySet;return am_return(c);
    // MOVEA.L (A7)+,A0; MOVEQ #ff,D0; RTS.
    case 0x1bf66:if(!am_pop(c,4,value))return false;r.a[0]=value;r.d[0]=0xffffffffU;return am_return(c);
    // ---- 1bfb4 (N23 4d766): ANDI.W #1,D0; BNE.W 1bfc6.
    case 0x1bfb4:am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&1U)!=0U?0x1bfc6:0x1bfbc;return true;
    case 0x1bfcc:return am_call(c,0x289e,0x1bfd2);
    case 0x1bfd2:return on22_carry(c,0x1c00a,0x1bfd6);                  // BCC.W 1c00a (C returned by 289e).
    case 0x1bfd6:if(!on22_bit(c,am_index(r.a[0],0x61),7,bit))return false;r.pc=bit?0x1c00a:0x1bfe0;return true;
    // TST.W 90(A0); SNE.B D1; BTST.B #0,a8(A0); BEQ.W 1bff2.
    case 0x1bfe0:
        if(!am_read(c,am_index(r.a[0],0x90),2,value))return false;am_byte(r.d[1],(value&65535U)!=0U?0xff:0);
        if(!on22_bit(c,am_index(r.a[0],0xa8),0,bit))return false;r.pc=bit?0x1bff0:0x1bff2;return true;
    case 0x1bff0:r.d[1]=0xffffffffU;r.pc=0x1bff2;return true;           // MOVEQ #ff,D1.
    // MOVEQ #0,D3; BTST.B #2,a7(A0); SNE.B D2; BEQ.W 1c008.
    case 0x1bff2:
        r.d[3]=0;if(!on22_bit(c,am_index(r.a[0],0xa7),2,bit))return false;am_byte(r.d[2],bit?0xff:0);r.pc=bit?0x1c000:0x1c008;return true;
    // BTST.B #6,a8(A0); SNE.B D3.
    case 0x1c000:if(!on22_bit(c,am_index(r.a[0],0xa8),6,bit))return false;am_byte(r.d[3],bit?0xff:0);r.pc=0x1c008;return true;
    case 0x1c008:case 0x3d3ee:case 0x3de44:case 0x3de52:case 0x3e03c:case 0x3e178:case 0x3e248:return am_return(c); // RTS.
    case 0x1c00a:r.d[1]=0;r.d[2]=0;r.d[3]=0;return am_return(c);       // MOVEQ #0,D1/D2/D3; RTS.
    // ---- 3d228 (stage event callback): JSR 3df44(PC); MOVE.L #3d280,(A6); RTS.
    case 0x3d228:return am_call(c,0x3df44,0x3d22c);
    case 0x3d22c:if(!am_write(c,r.a[6],4,0x3d280))return false;return am_return(c);
    // ---- 3d280 (installed): MOVE.W #0,68(A6); MOVE.W #0,1e(A6); LEA 0.w,A0; JSR 4b82e.l.
    case 0x3d280:if(!on22_put(c,0x68,2,0) || !on22_put(c,0x1e,2,0))return false;r.a[0]=0;return am_call(c,0x4b82e,0x3d296);
    case 0x3d296:if(!on22_put(c,0x9d,1,0))return false;return am_call(c,0x3de06,0x3d2a0); // MOVE.B #0,9d(A6); JSR 3de06(PC).
    // MOVE.B 1b(A6),14(A6); MOVE.L #0,80(A6); JSR 496c2.l.
    case 0x3d2a0:
        if(!on22_get(c,0x1b,1,value) || !on22_put(c,0x14,1,value) || !on22_put(c,0x80,4,0))return false;return am_call(c,0x496c2,0x3d2b4);
    case 0x3d2b4:if(!on22_get(c,0xa1,1,value))return false;r.pc=(value&255U)!=0U?0x3d388:0x3d2bc;return true; // TST.B a1(A6); BNE.W.
    // MOVE.W #0,86(A6); MOVE.B #0,a0(A6); MOVE.B #0,a1(A6); MOVEA.L #3e754,A1; MOVE.W #100,D0; LEA 8a(A6),A0; JSR 49f96.l.
    case 0x3d2bc:
        if(!on22_put(c,0x86,2,0) || !on22_put(c,0xa0,1,0) || !on22_put(c,0xa1,1,0))return false;
        r.a[1]=0x3e754;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x8a);return am_call(c,0x49f96,0x3d2e2);
    case 0x3d2e2:r.a[1]=0x3e808;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3d2f2); // MOVEA.L #3e808,A1; MOVE.W #100,D0; JSR 49f8c.
    // BCLR.B #3,15(A6); MOVE.L #0,56(A6); MOVEQ #0,D0; MOVEQ #40,D1; BTST.B #0,15(A6); BEQ.W 3d310.
    case 0x3d2f2:
        if(!on22_change(c,am_index(r.a[6],0x15),3,false) || !on22_put(c,0x56,4,0))return false;r.d[0]=0;r.d[1]=0x40;
        if(!on22_bit(c,am_index(r.a[6],0x15),0,bit))return false;r.pc=bit?0x3d30e:0x3d310;return true;
    case 0x3d30e:am_word(r.d[0],(0x10000U-(r.d[0]&65535U))&65535U);r.pc=0x3d310;return true; // NEG.W D0.
    case 0x3d310:r.a[0]=0x3d3de;return am_call(c,0x4da50,0x3d31a);     // LEA 3d3de(PC),A0; JSR 4da50.l (boundary).
    // MOVE.B #0,78(A6); MOVE.B #0,b3(A6); MOVE.L #3d32c,(A6).
    case 0x3d31a:if(!on22_put(c,0x78,1,0) || !on22_put(c,0xb3,1,0))return false;return on22_install(c,0x3d32c,0x3d32c);
    // ---- 3d32c (installed): LEA 3f6f0.l,A0; JSR 1aa7e.l; BCS.W 3db62; JSR 3de46(PC); LEA 3f708.l,A0; JSR 4d2d4.l; BCC.W 3d380.
    case 0x3d32c:r.a[0]=0x3f6f0;return am_call(c,0x1aa7e,0x3d338);
    case 0x3d338:return on22_carry(c,0x3d33c,0x3db62);                  // BCS.W 3db62 (C returned by 1aa7e).
    case 0x3d33c:case 0x3d3b2:return am_call(c,0x3de46,r.pc+4U);       // JSR 3de46(PC).
    case 0x3d340:r.a[0]=0x3f708;return am_call(c,0x4d2d4,0x3d34c);     // JSR 4d2d4.l (boundary).
    case 0x3d34c:return on22_carry(c,0x3d380,0x3d350);                  // BCC.W 3d380 (C returned by 4d2d4).
    case 0x3d350:if(!on22_put(c,0x84,2,r.d[0]&65535U))return false;return am_call(c,0x3dcac,0x3d358); // MOVE.W D0,84(A6); JSR 3dcac(PC).
    case 0x3d358:return on22_carry(c,0x3d380,0x3d35c);                  // BCC.W 3d380 (C returned by 3dcac -> 4d418).
    // MOVE.W D0,86(A6); MOVE.W 84(A6),D0; MOVE.B #12,D1; MOVE.B a5(A6),D2; MOVE.B a6(A6),D3; MOVE.W 54(A6),D4; JSR 4d508.l.
    case 0x3d35c:
        if(!on22_put(c,0x86,2,r.d[0]&65535U) || !on22_get(c,0x84,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0x12);
        if(!on22_get(c,0xa5,1,value))return false;am_byte(r.d[2],value);if(!on22_get(c,0xa6,1,value))return false;am_byte(r.d[3],value);
        if(!on22_get(c,0x54,2,value))return false;am_word(r.d[4],value);return am_call(c,0x4d508,0x3d37a);
    case 0x3d37a:return on22_install(c,0x3d3f0,0x3d380);                // MOVE.L #3d3f0,(A6) (N22b install value).
    case 0x3d380:case 0x3d3b6:return am_call(c,0x3dcf2,r.pc+4U);       // JSR 3dcf2(PC).
    case 0x3d384:case 0x3d3da:r.pc=0x3dbba;return true;                 // BRA.W 3dbba.
    // MOVEA.L #3e754,A1; MOVE.W #100,D0; LEA 8a(A6),A0; JSR 49f96.l / MOVEA.L #3e92e,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3d388:r.a[1]=0x3e754;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x8a);return am_call(c,0x49f96,0x3d39c);
    case 0x3d39c:r.a[1]=0x3e92e;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3d3ac);
    case 0x3d3ac:return on22_install(c,0x3d3b2,0x3d3b2);                // MOVE.L #3d3b2,(A6).
    case 0x3d3ba:return on22_carry(c,0x3d3c4,0x3d3be);                  // BCC.W 3d3c4 (C returned by 3dcf2).
    case 0x3d3be:return on22_install(c,0x3d2b4,0x3d3c4);                // MOVE.L #3d2b4,(A6).
    case 0x3d3c4:r.a[0]=0x3f6f0;return am_call(c,0x1ab02,0x3d3d0);     // LEA 3f6f0.l,A0; JSR 1ab02.l.
    case 0x3d3d0:return on22_carry(c,0x3d3da,0x3d3d4);                  // BCC.W 3d3da (C returned by 1ab02).
    case 0x3d3d4:return on22_install(c,0x3db62,0x3d3da);                // MOVE.L #3db62,(A6).
    // ---- 3d3de (code pointer, N23 4dbb0 JSR (A1)): MOVEA.L c(A6),A0; TST.B b1(A0); BEQ.W 3d3ee (C = 0) / ORI.B #1,CCR.
    case 0x3d3de:
        if(!on22_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0xb1),1,value))return false;
        r.carry=AnimationCarryClear;r.pc=(value&255U)==0U?0x3d3ee:0x3d3ea;return true;
    case 0x3d3ea:r.carry=AnimationCarrySet;r.pc=0x3d3ee;return true;
    case 0x3db62:case 0x3e24a:r.pc=0x2a00;return true;                  // JMP 2a00.l.
    case 0x3dbba:r.pc=0x3dc24;return true;                               // BRA.W 3dc24.
    // ---- shared tail: JSR 4b54e.l; BTST.B #7,61(A6); SNE.B D0; BEQ.W 3dc3c; MOVE.L #3d982,(A6); AND.B D0,5e(A6).
    case 0x3dc24:return am_call(c,0x4b54e,0x3dc2a);
    case 0x3dc2a:if(!on22_bit(c,am_index(r.a[6],0x61),7,bit))return false;am_byte(r.d[0],bit?0xff:0);r.pc=bit?0x3dc36:0x3dc3c;return true;
    case 0x3dc36:return on22_install(c,0x3d982,0x3dc3c);                // 3d982: outside every unit (install value only).
    case 0x3dc3c:if(!on22_get(c,0x5e,1,value) || !on22_put(c,0x5e,1,value&r.d[0]&255U))return false;r.pc=0x3dc40;return true;
    // BCLR.B #6,61(A6); TST.W 88(A6); BEQ.W 3dc58 / SUBQ.W #1,88(A6); BSET.B #6,61(A6).
    case 0x3dc40:
        if(!on22_change(c,am_index(r.a[6],0x61),6,false) || !on22_get(c,0x88,2,value))return false;
        r.pc=(value&65535U)==0U?0x3dc58:0x3dc4e;return true;
    case 0x3dc4e:
        if(!on22_get(c,0x88,2,value) || !on22_put(c,0x88,2,(value+0xffffU)&65535U) || !on22_change(c,am_index(r.a[6],0x61),6,true))return false;
        r.pc=0x3dc58;return true;
    case 0x3dc58:return am_call(c,0x4d766,0x3dc5e);                     // JSR 4d766.l (boundary).
    case 0x3dc5e:return on22_carry(c,0x3dc68,0x3dc62);                  // BCC.W 3dc68 (C returned by 4d766).
    case 0x3dc62:if(!on22_change(c,am_index(r.a[6],0x61),6,true))return false;r.pc=0x3dc68;return true; // BSET.B #6,61(A6).
    case 0x3dc68:if(!on22_get(c,0x80,4,value))return false;r.pc=value==0U?0x3dc84:0x3dc70;return true; // TST.L 80(A6); BEQ.W 3dc84.
    // MOVE.B 1a(A6),14(A6); JSR 3defa(PC) (N22b boundary).
    case 0x3dc70:if(!on22_get(c,0x1a,1,value) || !on22_put(c,0x14,1,value))return false;return am_call(c,0x3defa,0x3dc7a);
    case 0x3dc7a:if(!on22_change(c,am_index(r.a[6],0x61),6,true))return false;r.pc=0x3dca4;return true; // BSET.B #6,61(A6); BRA.W 3dca4.
    // MOVE.B 1b(A6),14(A6); MOVE.W 88(A6),D0; ANDI.W #1,D0; BEQ.W 3dca4.
    case 0x3dc84:
        if(!on22_get(c,0x1b,1,value) || !on22_put(c,0x14,1,value) || !on22_get(c,0x88,2,value))return false;
        am_word(r.d[0],value&1U);r.pc=(value&1U)==0U?0x3dca4:0x3dc96;return true;
    // MOVE.B 19(A6),14(A6); ST.B 94(A6); ST.B 98(A6).
    case 0x3dc96:
        if(!on22_get(c,0x19,1,value) || !on22_put(c,0x14,1,value) || !on22_put(c,0x94,1,0xff) || !on22_put(c,0x98,1,0xff))return false;
        r.pc=0x3dca4;return true;
    case 0x3dca4:if(!on22_put(c,0x9f,1,0xff))return false;return am_return(c); // MOVE.B #ff,9f(A6); RTS.
    // ---- 3dcf2: MOVE.W 1e(A6),D0; JSR ce02.l; JSR 49fc6.l; SCS.B -(A7); BSR.W 3dd6a; MOVE.B (A7)+,D0; LSR.B #1,D0; RTS.
    case 0x3dcf2:if(!on22_get(c,0x1e,2,value))return false;am_word(r.d[0],value);return am_call(c,0xce02,0x3dcfc);
    case 0x3dcfc:return am_call(c,0x49fc6,0x3dd02);
    case 0x3dd02:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n22 caller requires known carry");
        if(!am_push(c,1,r.carry==AnimationCarrySet?0xffU:0U))return false;return am_call(c,0x3dd6a,0x3dd08);
    case 0x3dd08:
        if(!am_pop(c,1,value))return false;value&=255U;r.carry=(value&1U)?AnimationCarrySet:AnimationCarryClear;am_byte(r.d[0],value>>1);
        return am_return(c);
    // ---- 3dd6a: MOVE.W 1e(A6),-(A7); MOVE.B 14(A6),-(A7); MOVEQ #0,D1; MOVE.B b0(A6),D1; ADD.W D1,46(A6); ADDI.W #12,D1;
    // ANDI.W #ff,D1; MOVE.W #ee00,D0; MOVE.B D1,D0; MOVE.W D0,96(A6); MOVE.W #1200,D0; MOVE.B D1,D0; MOVE.W D0,92(A6);
    // MOVE.B 14(A6),D0; CMP.B 1b(A6),D0; BNE.W 3ddaa.
    case 0x3dd6a:
        if(!on22_get(c,0x1e,2,value) || !am_push(c,2,value&65535U) || !on22_get(c,0x14,1,value) || !am_push(c,1,value&255U))return false;
        r.d[1]=0;if(!on22_get(c,0xb0,1,value))return false;am_byte(r.d[1],value);
        if(!on22_get(c,0x46,2,value) || !on22_put(c,0x46,2,(value+(r.d[1]&65535U))&65535U))return false;
        am_word(r.d[1],((r.d[1]&65535U)+0x12U)&0xffU);
        am_word(r.d[0],0xee00);am_byte(r.d[0],r.d[1]);if(!on22_put(c,0x96,2,r.d[0]&65535U))return false;
        am_word(r.d[0],0x1200);am_byte(r.d[0],r.d[1]);if(!on22_put(c,0x92,2,r.d[0]&65535U))return false;
        if(!on22_get(c,0x14,1,value))return false;am_byte(r.d[0],value);if(!on22_get(c,0x1b,1,other))return false;
        r.pc=((value^other)&255U)!=0U?0x3ddaa:0x3dda4;return true;
    case 0x3dda4:if(!on22_get(c,0x1c,1,value) || !on22_put(c,0x14,1,value))return false;r.pc=0x3ddaa;return true; // MOVE.B 1c(A6),14(A6).
    // MOVE.W #2,1e(A6); BCLR.B #0,9b(A6); LEA 8a(A6),A0; JSR 49fca.l.
    case 0x3ddaa:
        if(!on22_put(c,0x1e,2,2) || !on22_change(c,am_index(r.a[6],0x9b),0,false))return false;r.a[0]=am_index(r.a[6],0x8a);
        return am_call(c,0x49fca,0x3ddc0);
    case 0x3ddc0:return on22_carry(c,0x3ddca,0x3ddc4);                  // BCC.W 3ddca (C returned by 49fca).
    case 0x3ddc4:if(!on22_change(c,am_index(r.a[6],0x9b),0,true))return false;r.pc=0x3ddca;return true; // BSET.B #0,9b(A6).
    case 0x3ddca:case 0x3e1e2:case 0x3e238:return am_call(c,0x43e34,r.pc+6U); // JSR 43e34.l.
    // MOVE.B (A7)+,14(A6); MOVE.W (A7)+,1e(A6); BTST.B #0,9b(A6); SNE.B D0; LSR.B #1,D0; RTS (C left Unknown: no consumer).
    case 0x3ddd0:
        if(!am_pop(c,1,value) || !on22_put(c,0x14,1,value&255U) || !am_pop(c,2,value) || !on22_put(c,0x1e,2,value&65535U))return false;
        if(!on22_bit(c,am_index(r.a[6],0x9b),0,bit))return false;am_byte(r.d[0],bit?0x7f:0);return am_return(c);
    // ---- 3de06: JSR 8ff4.l; JSR 8ebe.l with D0.W / D1.B = e18 / 1, e0e / 1, e0e / 1, e0f / 1; RTS.
    case 0x3de06:return am_call(c,0x8ff4,0x3de0c);
    case 0x3de0c:return on22_sound(c,0xe18,0x3de1a);
    case 0x3de1a:return on22_sound(c,0xe0e,0x3de28);
    case 0x3de28:return on22_sound(c,0xe0e,0x3de36);
    case 0x3de36:return on22_sound(c,0xe0f,0x3de44);
    // ---- 3de46: MOVE.L 64(A6),36(A6); JSR 43ea4.l; RTS.
    case 0x3de46:if(!on22_get(c,0x64,4,value) || !on22_put(c,0x36,4,value))return false;return am_call(c,0x43ea4,0x3de52);
    // ---- 3df44: MOVE.W #1a3,20(A6); MOVE.L 2001a0.l,22(A6); JSR 3de06(PC).
    case 0x3df44:if(!on22_animation_id(c,0x1a3,ON22_BANK_1A3))return false;return am_call(c,0x3de06,0x3df56);
    // MOVE.B 1b(A6),14(A6); BSET.B #6,15(A6); MOVE.W #2,68(A6); MOVE.W #2,1e(A6); MOVEQ #12,D1; JSR 4d81c.l.
    case 0x3df56:
        if(!on22_get(c,0x1b,1,value) || !on22_put(c,0x14,1,value) || !on22_change(c,am_index(r.a[6],0x15),6,true) ||
            !on22_put(c,0x68,2,2) || !on22_put(c,0x1e,2,2))return false;
        r.d[1]=0x12;return am_call(c,0x4d81c,0x3df76);
    // MOVE.B D1,a5(A6); MOVE.B D2,a6(A6); MOVE.W D3,54(A6); MOVEA.L #41fe6,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x3df76:
        if(!on22_put(c,0xa5,1,r.d[1]&255U) || !on22_put(c,0xa6,1,r.d[2]&255U) || !on22_put(c,0x54,2,r.d[3]&65535U))return false;
        r.a[0]=0x41fe6;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x3df92);
    case 0x3df92:return on22_carry(c,0x3dfc0,0x3df96);                  // BCC.W 3dfc0 (C returned by 28ae).
    case 0x3df96:return on22_child(c,0x96,0x12,4,0,0x3dfc0);           // child 76 = A6+96, 7a..7e = 12 4 0 0 0; ORI.B #1,CCR.
    case 0x3dfc0:if(!on22_child_flags(c))return false;r.a[0]=0x41fe6;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x3dfe2);
    case 0x3dfe2:return on22_carry(c,0x3e010,0x3dfe6);                  // BCC.W 3e010 (C returned by 28ae).
    case 0x3dfe6:return on22_child(c,0x92,0x13,4,2,0x3e010);           // child 76 = A6+92, 7a..7e = 13 4 2 0 0; ORI.B #1,CCR.
    // BSET/MOVE.W child flags; MOVE.B #0,9a(A6); MOVEA.L #3e0f6,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x3e010:
        if(!on22_child_flags(c) || !on22_put(c,0x9a,1,0))return false;r.a[0]=0x3e0f6;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x3e038);
    case 0x3e038:return on22_carry(c,0x3db62,0x3e03c);                  // BCC.W 3db62 (C returned by 28ae).
    // ---- 3e0f6 (28ae child): MOVE.W #1a3,20(A6); MOVE.L 2001a0.l,22(A6); BSET.B #6,15(A6); MOVE.W #5,68(A6); MOVE.W #5,1e(A6);
    // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0x3e0f6:
        if(!on22_animation_id(c,0x1a3,ON22_BANK_1A3) || !on22_change(c,am_index(r.a[6],0x15),6,true) || !on22_put(c,0x68,2,5) ||
            !on22_put(c,0x1e,2,5))return false;
        r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x3e120);
    // MOVE.B #0,9d(A6); MOVE.W #ffff,86(A6); BRA.W 3e1c2.
    case 0x3e120:if(!on22_put(c,0x9d,1,0) || !on22_put(c,0x86,2,0xffff))return false;r.pc=0x3e1c2;return true;
    // ---- 3e130: JSR 491c4.l; MOVE.B b0(A0),b0(A6); MOVE.B 60(A0),60(A6); MOVE.W 84(A0),84(A6); MOVE.W 86(A0),D0; CMP.W 86(A6),D0;
    // BEQ.W 3e178.
    case 0x3e130:return am_call(c,0x491c4,0x3e136);
    case 0x3e136:
        if(!am_read(c,am_index(r.a[0],0xb0),1,value) || !on22_put(c,0xb0,1,value) || !am_read(c,am_index(r.a[0],0x60),1,value) ||
            !on22_put(c,0x60,1,value) || !am_read(c,am_index(r.a[0],0x84),2,value) || !on22_put(c,0x84,2,value) ||
            !am_read(c,am_index(r.a[0],0x86),2,value))return false;
        am_word(r.d[0],value);if(!on22_get(c,0x86,2,other))return false;r.pc=((value^other)&65535U)==0U?0x3e178:0x3e154;return true;
    case 0x3e154:if(!on22_put(c,0x86,2,r.d[0]&65535U))return false;return am_call(c,0x8ff4,0x3e15e); // MOVE.W D0,86(A6); JSR 8ff4.l.
    // MOVE.W 86(A6),D0; LEA 3fc6e.l,A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x3e15e:
        if(!on22_get(c,0x86,2,value))return false;am_word(r.d[0],value);r.a[0]=0x3fc6e;am_word(r.d[0],(r.d[0]*2U)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3e178);
    // ---- 3e17a: MOVEQ #0,D0; MOVEQ #0,D1; MOVEA.L c(A6),A1; MOVE.B 9d(A1),D0; BMI.W 3e1b6.
    case 0x3e17a:
        r.d[0]=0;r.d[1]=0;if(!on22_get(c,0xc,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],0x9d),1,value))return false;
        am_byte(r.d[0],value);r.pc=(value&0x80U)!=0U?0x3e1b6:0x3e18a;return true;
    case 0x3e18a:if(!on22_get(c,0x9d,1,value))return false;am_byte(r.d[1],value);r.pc=(value&0x80U)!=0U?0x3e1a0:0x3e192;return true;
    // LEA 3e1b8(PC),A1; MOVE.B (A1,D1.W),D2; BTST.L D0,D2; BNE.W 3e1b6.
    case 0x3e192:
        r.a[1]=0x3e1b8;if(!am_read(c,am_index(r.a[1],r.d[1]),1,value))return false;am_byte(r.d[2],value);
        r.pc=((r.d[2]>>(r.d[0]&31U))&1U)!=0U?0x3e1b6:0x3e1a0;return true;
    // MOVE.B D0,9d(A6); ADD.W D0,D0; ADD.W D0,D0; MOVEA.L 3e1ba(PC,D0.W),A0; MOVEA.L c(A6),A1; MOVE.B #ff,9d(A1).
    case 0x3e1a0:
        if(!on22_put(c,0x9d,1,r.d[0]&255U))return false;am_word(r.d[0],(r.d[0]*4U)&65535U);
        if(!am_read(c,am_index(0x3e1ba,r.d[0]),4,value))return false;r.a[0]=value;if(!on22_get(c,0xc,4,value))return false;r.a[1]=value;
        if(!am_write(c,am_index(r.a[1],0x9d),1,0xff))return false;r.pc=0x3e1b6;return true;
    case 0x3e1b6:r.pc=r.a[0];return true;                                // JMP (A0) (live target).
    // ---- 3e1c2 (LONG table entry 0): MOVE.B #0,9d(A6); MOVE.L #3e1ce,(A6).
    case 0x3e1c2:if(!on22_put(c,0x9d,1,0))return false;return on22_install(c,0x3e1ce,0x3e1ce);
    case 0x3e1ce:case 0x3e214:return am_call(c,0x288c,r.pc+6U);        // JSR 288c.l.
    case 0x3e1d4:case 0x3e21a:return on22_carry(c,0x3e24a,r.pc+4U);    // BCC.W 3e24a (C returned by 288c).
    case 0x3e1d8:case 0x3e21e:return am_call(c,0x3e130,r.pc+4U);       // JSR 3e130(PC).
    case 0x3e1dc:r.a[0]=0x3e1e2;r.pc=0x3e17a;return true;               // LEA 3e1e2(PC),A0; BRA.B 3e17a.
    case 0x3e222:r.a[0]=0x3e22a;r.pc=0x3e17a;return true;               // LEA 3e22a(PC),A0; BRA.W 3e17a.
    case 0x3e1e8:case 0x3e244:r.pc=0x3e248;return true;                 // BRA.W 3e248.
    // ---- 3e1ec (LONG table entry 1): MOVE.B #1,9d(A6); LEA 3fc86.l,A1; MOVE.W 86(A6),D0; ADD.W D0,D0; ADD.W D0,D0;
    // MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3e1ec:
        if(!on22_put(c,0x9d,1,1))return false;r.a[1]=0x3fc86;if(!on22_get(c,0x86,2,value))return false;am_word(r.d[0],(value*4U)&65535U);
        if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3e20e);
    case 0x3e20e:return on22_install(c,0x3e214,0x3e214);                // MOVE.L #3e214,(A6).
    // ---- 3e22a (continuation): MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B b0(A6),D1; JSR 49290.l; JSR 43e34.l; JSR 49fc6.l.
    case 0x3e22a:r.d[0]=0;r.d[1]=0;if(!on22_get(c,0xb0,1,value))return false;am_byte(r.d[1],value);return am_call(c,0x49290,0x3e238);
    case 0x3e23e:return am_call(c,0x49fc6,0x3e244);
    // ---- 41fe6 (28ae child): MOVE.W #12a,20(A6); MOVE.L 2000b8.l,22(A6); MOVEA.L c(A6),A0; LEA 2e(A0),A1; MOVEA.L 76(A6),A0;
    // MOVE.B (A0)+,D0; MOVE.B (A0)+,D1; CLR.B (A0); EXT.W D0; EXT.W D1; JSR 43e04.l.
    case 0x41fe6:
        if(!on22_animation_id(c,0x12a,ON22_BANK_12A) || !on22_get(c,0xc,4,value))return false;r.a[0]=value;r.a[1]=am_index(r.a[0],0x2e);
        if(!on22_get(c,0x76,4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[0],value);r.a[0]+=1U;
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[1],value);r.a[0]+=1U;
        if(!am_write(c,r.a[0],1,0))return false;
        am_word(r.d[0],(r.d[0]&0x80U)?(0xff00U|(r.d[0]&255U)):(r.d[0]&255U));  // EXT.W D0.
        am_word(r.d[1],(r.d[1]&0x80U)?(0xff00U|(r.d[1]&255U)):(r.d[1]&255U));  // EXT.W D1.
        return am_call(c,0x43e04,0x42010);
    // MOVEQ #0,D0; MOVE.B 7a(A6),D0; ADD.W D0,D0; LEA 41e4c(PC),A0; MOVE.W (A0,D0.W),86(A6); MOVEA.L 76(A6),A0; MOVE.B #ff,3(A0);
    // MOVEQ #0,D0; MOVE.B 7a(A6),D0; LEA 41eca(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x42010:
        if(!on22_table_word(c,0x41e4c,value) || !on22_put(c,0x86,2,value) || !on22_get(c,0x76,4,other))return false;r.a[0]=other;
        if(!am_write(c,am_index(r.a[0],3),1,0xff) || !on22_table_word(c,0x41eca,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);
        return am_call(c,0x8ebe,0x42046);
    case 0x42046:if(!on22_table_word(c,0x41ef4,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x42060);
    // MOVE.B 19(A6),14(A6); MOVEQ #0,D0; MOVE.B 7a(A6),D0; ADD.W D0,D0; ADD.W D0,D0; LEA 41f92(PC),A0; MOVE.L (A0,D0.W),96(A6);
    // TST.B 7b(A6); BNE.W 42088.
    case 0x42060:
        if(!on22_get(c,0x19,1,value) || !on22_put(c,0x14,1,value))return false;r.d[0]=0;if(!on22_get(c,0x7a,1,value))return false;
        am_byte(r.d[0],value);am_word(r.d[0],(r.d[0]*4U)&65535U);r.a[0]=0x41f92;
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value) || !on22_put(c,0x96,4,value) || !on22_get(c,0x7b,1,value))return false;
        r.pc=(value&255U)!=0U?0x42088:0x42082;return true;
    case 0x42082:if(!on22_put(c,0x7b,1,2))return false;r.pc=0x42088;return true; // MOVE.B #2,7b(A6).
    case 0x42088:if(!on22_get(c,0x7d,1,value))return false;r.pc=(value&255U)!=0U?0x42096:0x42090;return true; // TST.B 7d(A6); BNE.W.
    case 0x42090:if(!on22_put(c,0x7d,1,5))return false;r.pc=0x42096;return true; // MOVE.B #5,7d(A6).
    // MOVE.W 1e(A6),D0; CMPI.W #ffff,D0; BEQ.W 420a6 / MOVE.W D0,94(A6).
    case 0x42096:if(!on22_get(c,0x1e,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)==0xffffU?0x420a6:0x420a2;return true;
    case 0x420a2:if(!on22_put(c,0x94,2,r.d[0]&65535U))return false;r.pc=0x420a6;return true;
    case 0x420a6:r.a[1]=0x4264a;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x420b6); // MOVEA.L #4264a,A1; MOVE.W #100,D0; JSR 49f8c.
    case 0x420b6:if(!am_write(c,r.a[6],4,0x420be))return false;return am_return(c); // MOVE.L #420be,(A6) (N23 install value); RTS.
    default:return am_error(c,"unsupported animation objects n22 PC");
    }
}
}
