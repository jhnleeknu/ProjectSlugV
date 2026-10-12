#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t ON15_BANK_D0=0x2000d0;        // MOVE.L 2000d0.L,22(A6) / MOVEA.L 2000d0.L,A1 (banked window LONG, live bus).
const std::uint32_t ON15_BANK_D4=0x2000d4;        // MOVE.L 2000d4.L,22(A6) / MOVEA.L 2000d4.L,A1.
const std::uint32_t ON15_NEXT_TABLE=0x7117e;      // 7116c MOVE.L 7117e(PC,D0.W),D0 (8 LONG install values, index D0.W & 1c).
const std::uint32_t ON15_STATE_TABLE=0x70d72;     // 711e6 LEA 70d72(PC),A0; MOVEA.L (A0,D0.W),A0 (index from the boundary 70302).
const std::uint32_t ON15_PLAYER_1=0x100cb8;       // 493c8 CMPA.L #100cb8,A0.
const std::uint32_t ON15_PLAYER_2=0x100da8;       // 493d4 CMPA.L #100da8,A0.
std::uint32_t on15_w(std::uint32_t v) {return v&65535U;}
bool on15_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on15_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// MOVE.x d16(As),d16(Ad) (read, then write).
bool on15_copy(AnimationMachineContext& c,std::uint32_t src,std::uint32_t src_d,std::uint32_t dst,std::uint32_t dst_d,unsigned int size) {
    std::uint32_t value=0;if(!on15_get(c,src,src_d,size,value))return false;return on15_put(c,dst,dst_d,size,value);
}
// ASR.L #n (sign bit fills, n < 32).
std::uint32_t on15_asr_l(std::uint32_t v,unsigned int n) {
    const std::uint32_t shifted=v>>n;return (v&0x80000000U)?(shifted|~(0xffffffffU>>n)):shifted;
}
// EXT.L of the low WORD.
std::uint32_t on15_ext_l(std::uint32_t v) {return am_extend_word(v&65535U);}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool on15_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n15 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #value,(A6), then continue at next_pc.
bool on15_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,value))return false;c.s.pc=next_pc;return true;
}
// BTST.B #bit,d16(An); BEQ/BNE: set_pc when the bit is 1, clear_pc when it is 0.
bool on15_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t set_pc,
    std::uint32_t clear_pc) {
    std::uint32_t value=0;if(!on15_get(c,base,displacement,1,value))return false;
    c.s.pc=((value>>bit)&1U)?set_pc:clear_pc;return true;
}
// BSET.B / BCLR.B #bit,d16(An) (BYTE read-modify-write).
bool on15_bchange(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool set_bit) {
    std::uint32_t value=0;if(!on15_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;return on15_put(c,base,displacement,1,set_bit?((value|mask)&255U):(value&~mask&255U));
}
// TST.W d16(A6); BEQ/BNE: zero_pc when the WORD is 0, other_pc otherwise.
bool on15_test_w(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!on15_get(c,c.s.a[6],displacement,2,value))return false;
    c.s.pc=on15_w(value)==0U?zero_pc:other_pc;return true;
}
// LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1;
// JSR 49f8c.L (the banked LONG and the LONG it points to are read through the live bus).
bool on15_animation(AnimationMachineContext& c,std::uint32_t k,std::uint32_t bank,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!on15_put(c,r.a[6],0x20,2,k) || !am_read(c,bank,4,value) || !on15_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!on15_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!on15_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// TST.W 9c(A6); BNE: side 3 (bank 2000d0) at the fall-through when 9c = 0, side b (bank 2000d4) at the BNE target otherwise.
bool on15_side(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {return on15_test_w(c,0x9c,zero_pc,other_pc);}
// MOVE.L 64(A6),D0; SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6); MOVE.L #fff00000,D0; SUB.L 3a(A6),D0; ASR.L #5,D0;
// ADD.L D0,3a(A6); JSR 4be34.L.
bool on15_approach(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    if(!on15_get(c,r.a[6],0x64,4,value) || !on15_get(c,r.a[6],0x36,4,other))return false;
    r.d[0]=on15_asr_l((value-other)&0xffffffffU,5);if(!on15_put(c,r.a[6],0x36,4,(other+r.d[0])&0xffffffffU))return false;
    if(!on15_get(c,r.a[6],0x3a,4,value))return false;
    r.d[0]=on15_asr_l((0xfff00000U-value)&0xffffffffU,5);if(!on15_put(c,r.a[6],0x3a,4,(value+r.d[0])&0xffffffffU))return false;
    return am_call(c,0x4be34,return_pc);
}
// MOVE.B #ff,17(A6); LEA list.L,A0; MOVEA.L bank.L,A1; MOVE.W #d1,D1; MOVE.W #d2,D2; JMP target.L (boundary).
bool on15_death(AnimationMachineContext& c,std::uint32_t list,std::uint32_t bank,std::uint32_t d1,std::uint32_t d2,std::uint32_t target) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!on15_put(c,r.a[6],0x17,1,0xff))return false;r.a[0]=list;
    if(!am_read(c,bank,4,value))return false;r.a[1]=value;am_word(r.d[1],d1);am_word(r.d[2],d2);r.pc=target;return true;
}
// MOVE.W #ffe8,D0; MOVE.W #1a,D1; JSR target.L.
bool on15_box(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    am_word(c.s.d[0],0xffe8);am_word(c.s.d[1],0x1a);return am_call(c,target,return_pc);
}
}
// Objects F4 N15 (217 block starts): the helper 493bc (A0 player node check, C returned; TRAP boundary 493c6), the helpers 7028e
// 7054c 705ca (C returned), the node callback 708a6, the 7090a state machine callbacks 71032 (installed 710e4 with the LONG tables
// 7117e and 70d72), 71a80 (installed 71b04), 71bc0, the 710e4 branch 71c48 (bundled BCS reading the incoming C), 71d48 (installed
// 71db2), 71dd6 (installed 71e4e) and the shared tail 72d66, the node callback 76d18 (installed 76d56 76d66 76d94 76e2a 76e90, shared
// tail 76ebe), the interpreter command callback 76f1e and the helper 76f98 (C returned). 71c86 runs the N04 instruction 71c98
// (TST.W 9c(A6); BNE.W 71ccc) folded after its BRA.W. Consumers 71152 711a2 711c0 711ce 71c48 71dc8 76daa 76dba 76e4a 76eb0 76ed4
// 76f28 76f3e 76f84 76fbc 76fe2. Known C: Clear 493ee 70298 702c6 70588 705fe 76fc0 76fe6 710d2, Set 493e8 702c0 7058e 705f8,
// computed 493c8 493d4 7029e. Boundaries without an executor: 70302 70594 cc8b4 cc778 e9112 4970a (N14) and TRAP 493c6.
bool animation_objects_n15_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- 493bc: CMPA.L #108000,A5; BEQ.W 493c8 (else the TRAP #f boundary 493c6).
    case 0x493bc:r.pc=r.a[5]==0x108000U?0x493c8:0x493c6;return true;
    // MOVEQ #0,D0; CMPA.L #100cb8,A0; BEQ.W 493e0 (C = A0 < 100cb8 unsigned).
    case 0x493c8:
        r.d[0]=0;r.carry=r.a[0]<ON15_PLAYER_1?AnimationCarrySet:AnimationCarryClear;r.pc=r.a[0]==ON15_PLAYER_1?0x493e0:0x493d4;return true;
    // MOVEQ #1,D0; CMPA.L #100da8,A0; BNE.W 493ee (C = A0 < 100da8 unsigned).
    case 0x493d4:
        r.d[0]=1;r.carry=r.a[0]<ON15_PLAYER_2?AnimationCarrySet:AnimationCarryClear;r.pc=r.a[0]==ON15_PLAYER_2?0x493e0:0x493ee;return true;
    // BTST.B D0,568e(A5) (memory: bit D0 mod 8); BEQ.W 493ec.
    case 0x493e0:return on15_bit(c,r.a[5],0x568e,r.d[0]&7U,0x493e8,0x493ec);
    case 0x493e8:r.carry=AnimationCarrySet;r.pc=0x493ec;return true;                      // ORI.B #1,CCR.
    case 0x493ec:case 0x702ae:case 0x76f2c:case 0x76f96:return am_return(c);             // RTS.
    // MOVEQ #0,D0; CMPA.L #100cb8,A0; ANDI.B #fe,CCR; RTS.
    case 0x493ee:r.d[0]=0;r.carry=AnimationCarryClear;return am_return(c);

    // ---- 7028e: BTST.B #3,15(A6); BEQ.W 7029e.
    case 0x7028e:return on15_bit(c,r.a[6],0x15,3,0x70298,0x7029e);
    case 0x70298:case 0x702c6:case 0x70588:case 0x76fc0:case 0x76fe6:r.carry=AnimationCarryClear;return am_return(c); // ANDI.B #fe,CCR; RTS.
    // MOVE.W 42(A6),D0; SUBI.W #30,D0; CMPI.W #e0,D0; BCS.W 702b0 (C = D0.W < e0 unsigned).
    case 0x7029e:
        if(!on15_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],(value-0x30U)&65535U);
        if(on15_w(r.d[0])<0xe0U) {r.carry=AnimationCarrySet;r.pc=0x702b0;} else {r.carry=AnimationCarryClear;r.pc=0x702ae;}return true;
    case 0x702b0:r.a[0]=0x6fe3c;return am_call(c,0x4ae4a,0x702ba);                         // LEA 6fe3c(PC),A0; JSR 4ae4a.L.
    case 0x702ba:r.pc=(r.d[0]&255U)==0U?0x702c6:0x702c0;return true;                       // TST.B D0; BEQ.W 702c6.
    case 0x702c0:case 0x7058e:case 0x705f8:r.carry=AnimationCarrySet;return am_return(c); // ORI.B #1,CCR; RTS.

    // ---- 7054c: BTST.B #5,61(A6); BEQ.W 7056a.
    case 0x7054c:return on15_bit(c,r.a[6],0x61,5,0x70556,0x7056a);
    case 0x70556:return on15_bit(c,r.a[6],0x82,4,0x70560,0x7056a);                         // BTST.B #4,82(A6); BEQ.W 7056a.
    // CMPI.B #40,6f(A6); BEQ.W 7058e.
    case 0x70560:if(!on15_get(c,r.a[6],0x6f,1,value))return false;r.pc=(value&255U)==0x40U?0x7058e:0x7056a;return true;
    case 0x7056a:return on15_bit(c,r.a[6],0x82,5,0x70588,0x70574);                         // BTST.B #5,82(A6); BNE.W 70588.
    case 0x70574:return on15_bit(c,r.a[6],0x82,6,0x70588,0x7057e);                         // BTST.B #6,82(A6); BNE.W 70588.
    case 0x7057e:return on15_bit(c,r.a[6],0x82,2,0x7058e,0x70588);                         // BTST.B #2,82(A6); BNE.W 7058e.

    // ---- 705ca: BTST.B #1,82(A6); BEQ.W 705fe.
    case 0x705ca:return on15_bit(c,r.a[6],0x82,1,0x705d4,0x705fe);
    // CMPI.B #40,6f(A6); BNE.W 705fe.
    case 0x705d4:if(!on15_get(c,r.a[6],0x6f,1,value))return false;r.pc=(value&255U)==0x40U?0x705de:0x705fe;return true;
    // MOVE.W 42(A6),D0; MOVE.W 46(A6),D1; ADDI.W #20,D1; JSR 4bc04.L.
    case 0x705de:
        if(!on15_get(c,r.a[6],0x42,2,value) || !on15_get(c,r.a[6],0x46,2,other))return false;
        am_word(r.d[0],value);am_word(r.d[1],(other+0x20U)&65535U);return am_call(c,0x4bc04,0x705f0);
    case 0x705f0:r.pc=on15_w(r.d[0])<0x40U?0x705fe:0x705f8;return true;                    // CMPI.W #40,D0; BCS.W 705fe.
    case 0x705fe:r.d[0]=0;r.carry=AnimationCarryClear;return am_return(c);                // MOVEQ #0,D0; ANDI.B #fe,CCR; RTS.

    // ---- 708a6 (node callback): MOVE.W #0,9c(A6); JSR 70418(PC).
    case 0x708a6:if(!on15_put(c,r.a[6],0x9c,2,0))return false;return am_call(c,0x70418,0x708b0);
    // MOVE.B #e0,87(A6); BRA.W 70932.
    case 0x708b0:if(!on15_put(c,r.a[6],0x87,1,0xe0))return false;r.pc=0x70932;return true;

    // ---- 71032 (installed outside the range): TST.W 9c(A6); BNE.W 71066.
    case 0x71032:return on15_side(c,0x7103a,0x71066);
    case 0x7103a:return on15_animation(c,0x3,ON15_BANK_D0,0x4,0x71062);
    case 0x71066:return on15_animation(c,0xb,ON15_BANK_D4,0x4,0x7108e);
    case 0x71062:r.pc=0x7108e;return true;                                                // BRA.W 7108e.
    case 0x7108e:return am_call(c,0x49a58,0x71094);
    // EXT.L D0; MOVE.L D0,64(A6); JSR 49a58.L.
    case 0x71094:r.d[0]=on15_ext_l(r.d[0]);if(!on15_put(c,r.a[6],0x64,4,r.d[0]))return false;return am_call(c,0x49a58,0x710a0);
    // EXT.L D0; ADDI.L #28000,D0; ADD.L 64(A6),D0; TST.W 9a(A6); BEQ.W 710ba.
    case 0x710a0:
        if(!on15_get(c,r.a[6],0x64,4,value))return false;r.d[0]=(on15_ext_l(r.d[0])+0x28000U+value)&0xffffffffU;
        return on15_test_w(c,0x9a,0x710ba,0x710b4);
    case 0x710b4:r.d[0]=(r.d[0]+0x10000U)&0xffffffffU;r.pc=0x710ba;return true;          // ADDI.L #10000,D0.
    case 0x710ba:return on15_bit(c,r.a[6],0x15,0,0x710c6,0x710c4);                         // BTST.B #0,15(A6); BNE.W 710c6.
    case 0x710c4:r.d[0]=(0U-r.d[0])&0xffffffffU;r.pc=0x710c6;return true;                 // NEG.L D0.
    // MOVE.L D0,64(A6); TST.L D0; BPL.W 710d2.
    case 0x710c6:if(!on15_put(c,r.a[6],0x64,4,r.d[0]))return false;r.pc=(r.d[0]&0x80000000U)?0x710d0:0x710d2;return true;
    case 0x710d0:r.d[0]=(0U-r.d[0])&0xffffffffU;r.pc=0x710d2;return true;                 // NEG.L D0.
    // LSL.L #6,D0; SWAP D0; ADDI.W #80,D0; MOVE.W D0,2c(A6); MOVE.L #710e4,(A6) (MOVE leaves C = 0 for 71c48).
    case 0x710d2:
        r.d[0]=(r.d[0]<<6)&0xffffffffU;am_swap(r.d[0]);am_word(r.d[0],(r.d[0]+0x80U)&65535U);
        if(!on15_put(c,r.a[6],0x2c,2,r.d[0]&65535U) || !on15_install(c,0x710e4,0x710e4))return false;r.carry=AnimationCarryClear;return true;

    // ---- 710e4 (installed): BTST.B #7,15(A6); BEQ.W 71c48.
    case 0x710e4:return on15_bit(c,r.a[6],0x15,7,0x710ee,0x71c48);
    case 0x710ee:case 0x71dbc:return am_call(c,0x4bfa4,r.pc+6U);                           // JSR 4bfa4.L.
    case 0x710f4:r.d[6]&=0xffff0020U;r.pc=(r.d[6]&65535U)==0U?0x7110e:0x710fc;return true;  // ANDI.W #20,D6; BEQ.W 7110e.
    // MOVE.W #1,D6; AND.W 80(A6),D6; BEQ.W 7110e.
    case 0x710fc:
        if(!on15_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[6],value&1U);r.pc=(value&1U)==0U?0x7110e:0x71108;return true;
    case 0x71108:return on15_install(c,0x712a0,0x7110e);                                  // MOVE.L #712a0,(A6).
    // JSR 49fc6.L.
    case 0x7110e:case 0x71b28:case 0x71dc2:case 0x71e72:case 0x76df2:case 0x76e44:case 0x76eaa:return am_call(c,0x49fc6,r.pc+6U);
    // MOVE.W 8e(A6),D0; SUB.W 42(A6),D0; MOVE.W 64(A6),D1; EOR.W D0,D1; BPL.W 7113c.
    case 0x71114:
        if(!on15_get(c,r.a[6],0x8e,2,value) || !on15_get(c,r.a[6],0x42,2,other))return false;am_word(r.d[0],(value-other)&65535U);
        if(!on15_get(c,r.a[6],0x64,2,value))return false;am_word(r.d[1],(value^r.d[0])&65535U);
        r.pc=(r.d[1]&0x8000U)?0x71126:0x7113c;return true;
    // MOVE.L #713d8,(A6); BTST.B #1,82(A6); BEQ.W 7113c.
    case 0x71126:if(!am_write(c,r.a[6],4,0x713d8))return false;return on15_bit(c,r.a[6],0x82,1,0x71136,0x7113c);
    case 0x71136:return on15_install(c,0x71468,0x7113c);                                  // MOVE.L #71468,(A6).
    // MOVE.B 6e(A6),D0; CMPI.B #3,D0; BNE.W 7114e.
    case 0x7113c:if(!on15_get(c,r.a[6],0x6e,1,value))return false;am_byte(r.d[0],value);r.pc=(value&255U)==3U?0x71148:0x7114e;return true;
    case 0x71148:return on15_install(c,0x713d8,0x7114e);                                  // MOVE.L #713d8,(A6).
    case 0x7114e:return am_call(c,0x7054c,0x71152);                                       // BSR.W 7054c.
    case 0x71152:return on15_consume(c,false,0x7115c,0x71156);                            // BCC.W 7115c (C of 7054c).
    case 0x71156:return on15_install(c,0x71a80,0x7115c);                                  // MOVE.L #71a80,(A6).
    case 0x7115c:return on15_bit(c,r.a[6],0x82,7,0x71166,0x7119e);                         // BTST.B #7,82(A6); BEQ.W 7119e.
    case 0x71166:case 0x71c56:return am_call(c,0x49a58,r.pc+6U);                           // JSR 49a58.L.
    // ANDI.W #1c,D0; MOVE.L 7117e(PC,D0.W),D0; BEQ.W 7117a.
    case 0x7116c:
        am_word(r.d[0],r.d[0]&0x1cU);if(!am_read(c,am_index(ON15_NEXT_TABLE,r.d[0]),4,value))return false;r.d[0]=value;
        r.pc=value==0U?0x7117a:0x71178;return true;
    case 0x71178:if(!am_write(c,r.a[6],4,r.d[0]))return false;r.pc=0x7117a;return true;   // MOVE.L D0,(A6).
    case 0x7117a:r.pc=0x7119e;return true;                                                // BRA.W 7119e.
    case 0x7119e:return am_call(c,0x705ca,0x711a2);                                       // BSR.W 705ca.
    case 0x711a2:return on15_consume(c,false,0x711ac,0x711a6);                            // BCC.W 711ac (C of 705ca).
    case 0x711a6:return on15_install(c,0x71dd6,0x711ac);                                  // MOVE.L #71dd6,(A6).
    case 0x711ac:return on15_bit(c,r.a[6],0x61,0,0x711b6,0x711ca);                         // BTST.B #0,61(A6); BEQ.W 711ca.
    // MOVE.L #71bc0,(A6); BSR.W 70594 (boundary).
    case 0x711b6:if(!am_write(c,r.a[6],4,0x71bc0))return false;return am_call(c,0x70594,0x711c0);
    case 0x711c0:return on15_consume(c,false,0x711ca,0x711c4);                            // BCC.W 711ca (C of 70594).
    case 0x711c4:return on15_install(c,0x7120e,0x711ca);                                  // MOVE.L #7120e,(A6).
    case 0x711ca:return am_call(c,0x7028e,0x711ce);                                       // BSR.W 7028e.
    case 0x711ce:return on15_consume(c,false,0x711d8,0x711d2);                            // BCC.W 711d8 (C of 7028e).
    case 0x711d2:return on15_install(c,0x72978,0x711d8);                                  // MOVE.L #72978,(A6).
    case 0x711d8:return on15_bit(c,r.a[6],0x82,0,0x711e2,0x711fc);                         // BTST.B #0,82(A6); BEQ.W 711fc.
    case 0x711e2:return am_call(c,0x70302,0x711e6);                                       // BSR.W 70302 (boundary).
    // LEA 70d72(PC),A0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A0,D0.W),A0; CMPA.W #0,A0; BEQ.W 711fc.
    case 0x711e6:
        am_word(r.d[0],(r.d[0]<<2)&65535U);r.a[0]=ON15_STATE_TABLE;
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;r.pc=value==0U?0x711fc:0x711fa;return true;
    case 0x711fa:if(!am_write(c,r.a[6],4,r.a[0]))return false;r.pc=0x711fc;return true;   // MOVE.L A0,(A6).
    case 0x711fc:return on15_test_w(c,0x7c,0x71204,0x7120a);                               // TST.W 7c(A6); BNE.W 7120a.
    case 0x71204:return on15_install(c,0x72f8a,0x7120a);                                  // MOVE.L #72f8a,(A6).
    case 0x7120a:case 0x71b3e:case 0x71dd2:r.pc=0x72dd2;return true;                       // BRA.W 72dd2 (N04).

    // ---- 71a80 (installed): MOVE.L #8a000,3a(A6); MOVE.L #28000,D0; BTST.B #0,15(A6); BNE.W 71a9a.
    case 0x71a80:if(!on15_put(c,r.a[6],0x3a,4,0x8a000U))return false;r.d[0]=0x28000U;return on15_bit(c,r.a[6],0x15,0,0x71a9a,0x71a98);
    case 0x71a98:case 0x71c2c:r.d[0]=(0U-r.d[0])&0xffffffffU;r.pc=r.pc+2U;return true;    // NEG.L D0.
    // MOVE.L D0,64(A6); MOVE.L D0,36(A6); TST.W 9c(A6); BNE.W 71ad6.
    case 0x71a9a:if(!on15_put(c,r.a[6],0x64,4,r.d[0]) || !on15_put(c,r.a[6],0x36,4,r.d[0]))return false;return on15_side(c,0x71aaa,0x71ad6);
    case 0x71aaa:return on15_animation(c,0x3,ON15_BANK_D0,0x28,0x71ad2);
    case 0x71ad6:return on15_animation(c,0xb,ON15_BANK_D4,0x28,0x71afe);
    case 0x71ad2:r.pc=0x71afe;return true;                                                // BRA.W 71afe.
    case 0x71afe:return on15_install(c,0x71b04,0x71b04);                                  // MOVE.L #71b04,(A6).
    case 0x71b04:return on15_approach(c,0x71b28);
    case 0x71b2e:return on15_bit(c,r.a[6],0x15,7,0x71b38,0x71b3e);                         // BTST.B #7,15(A6); BEQ.W 71b3e.
    case 0x71b38:return on15_install(c,0x71d48,0x71b3e);                                  // MOVE.L #71d48,(A6).

    // ---- 71bc0 (installed): TST.W 9c(A6); BNE.W 71bf4.
    case 0x71bc0:return on15_side(c,0x71bc8,0x71bf4);
    case 0x71bc8:return on15_animation(c,0x3,ON15_BANK_D0,0x1c,0x71bf0);
    case 0x71bf4:return on15_animation(c,0xb,ON15_BANK_D4,0x1c,0x71c1c);
    case 0x71bf0:r.pc=0x71c1c;return true;                                                // BRA.W 71c1c.
    // MOVE.L #30000,D0; BTST.B #0,15(A6); BEQ.W 71c2e.
    case 0x71c1c:r.d[0]=0x30000U;return on15_bit(c,r.a[6],0x15,0,0x71c2c,0x71c2e);
    // MOVE.L D0,64(A6); MOVE.L D0,36(A6); MOVE.L #20000,3a(A6); MOVE.L #71d0a,(A6); BRA.W 71d0a (N04).
    case 0x71c2e:
        if(!on15_put(c,r.a[6],0x64,4,r.d[0]) || !on15_put(c,r.a[6],0x36,4,r.d[0]) || !on15_put(c,r.a[6],0x3a,4,0x20000U))return false;
        return on15_install(c,0x71d0a,0x71d0a);

    // ---- 71c48 (710e4 branch): BTST.B #1,82(A6); BEQ.W 71c56; BCS.W 71a80 (the BCS reads the incoming C only when the bit is 1).
    case 0x71c48:
        if(!on15_get(c,r.a[6],0x82,1,value))return false;
        if(((value>>1)&1U)==0U) {r.pc=0x71c56;return true;}
        return on15_consume(c,true,0x71a80,0x71c56);
    // CMPI.W #160,46(A6); BCC.W 71c72 (unsigned 46 >= 160).
    case 0x71c5c:if(!on15_get(c,r.a[6],0x46,2,value))return false;r.pc=on15_w(value)>=0x160U?0x71c72:0x71c66;return true;
    case 0x71c66:am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&65535U)==0U?0x71a80:0x71c6e;return true; // ANDI.W #1,D0; BEQ.W 71a80.
    case 0x71c6e:r.pc=0x71c86;return true;                                                // BRA.W 71c86.
    case 0x71c72:am_word(r.d[0],r.d[0]&3U);r.pc=(r.d[0]&65535U)==0U?0x71dd6:0x71c7a;return true; // ANDI.W #3,D0; BEQ.W 71dd6.
    // SUBQ.W #1,D0; BEQ.W 71a80 / 71dd6.
    case 0x71c7a:case 0x71c80:
        am_word(r.d[0],(r.d[0]+65535U)&65535U);
        if((r.d[0]&65535U)==0U)r.pc=r.pc==0x71c7aU?0x71a80:0x71dd6;else r.pc=r.pc==0x71c7aU?0x71c80:0x71c86;return true;
    // MOVE.L 64(A6),36(A6); BRA.W 71c98; [N04 71c98] TST.W 9c(A6); BNE.W 71ccc (folded; 71ca0 / 71ccc are N04 block starts).
    case 0x71c86:if(!on15_copy(c,r.a[6],0x64,r.a[6],0x36,4))return false;return on15_side(c,0x71ca0,0x71ccc);

    // ---- 71d48 (installed): TST.W 9c(A6); BNE.W 71d7c.
    case 0x71d48:return on15_side(c,0x71d50,0x71d7c);
    case 0x71d50:return on15_animation(c,0x3,ON15_BANK_D0,0x24,0x71d78);
    case 0x71d7c:return on15_animation(c,0xb,ON15_BANK_D4,0x24,0x71da4);
    case 0x71d78:r.pc=0x71da4;return true;                                                // BRA.W 71da4.
    // MOVE.L #0,64(A6); MOVE.L #71db2,(A6).
    case 0x71da4:if(!on15_put(c,r.a[6],0x64,4,0))return false;return on15_install(c,0x71db2,0x71db2);
    case 0x71db2:return on15_bit(c,r.a[6],0x15,7,0x71dbc,0x71c90);                         // BTST.B #7,15(A6); BEQ.W 71c90 (N04).
    case 0x71dc8:return on15_consume(c,false,0x71dd2,0x71dcc);                            // BCC.W 71dd2 (C of 49fc6).
    case 0x71dcc:return on15_install(c,0x70c0c,0x71dd2);                                  // MOVE.L #70c0c,(A6).

    // ---- 71dd6 (installed): TST.W 9c(A6); BNE.W 71e0a.
    case 0x71dd6:return on15_side(c,0x71dde,0x71e0a);
    case 0x71dde:return on15_animation(c,0x3,ON15_BANK_D0,0x20,0x71e06);
    case 0x71e0a:return on15_animation(c,0xb,ON15_BANK_D4,0x20,0x71e32);
    case 0x71e06:r.pc=0x71e32;return true;                                                // BRA.W 71e32.
    // MOVE.L 64(A6),36(A6); MOVE.L #10000,3a(A6); MOVE.L #0,64(A6); MOVE.L #71e4e,(A6).
    case 0x71e32:
        if(!on15_copy(c,r.a[6],0x64,r.a[6],0x36,4) || !on15_put(c,r.a[6],0x3a,4,0x10000U) || !on15_put(c,r.a[6],0x64,4,0))return false;
        return on15_install(c,0x71e4e,0x71e4e);
    case 0x71e4e:return on15_approach(c,0x71e72);
    case 0x71e78:return on15_bit(c,r.a[6],0x15,7,0x71e82,0x71e88);                         // BTST.B #7,15(A6); BEQ.W 71e88.
    case 0x71e82:return on15_install(c,0x71e8c,0x71e88);                                  // MOVE.L #71e8c,(A6).
    case 0x71e88:r.pc=0x72d66;return true;                                                // BRA.W 72d66.

    // ---- 72d66 (shared tail): JSR 4b54e.L.
    case 0x72d66:case 0x76ede:return am_call(c,0x4b54e,r.pc+6U);
    case 0x72d6c:return on15_bit(c,r.a[6],0x61,7,0x72d76,0x72dce);                         // BTST.B #7,61(A6); BEQ.W 72dce.
    // MOVEA.L c(A6),A0; ST.B 62(A0); TST.W 9c(A6); BNE.W 72dac.
    case 0x72d76:
        if(!on15_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!on15_put(c,r.a[0],0x62,1,0xff))return false;
        return on15_side(c,0x72d86,0x72dac);
    case 0x72d86:return on15_death(c,0xcdeea,ON15_BANK_D0,0x3,0x0,0xcc8b4);
    case 0x72dac:return on15_death(c,0xcdef8,ON15_BANK_D4,0xb,0x1,0xcc8b4);
    case 0x72dce:r.pc=0x72e3e;return true;                                                // BRA.W 72e3e (N04).

    // ---- 76d18 (node callback): MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVE.W #34,D0; MOVE.W #f,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0x76d18:
        if(!on15_put(c,r.a[6],0x68,2,0x8820) || !on15_put(c,r.a[6],0x1e,2,0x8820))return false;
        am_word(r.d[0],0x34);am_word(r.d[1],0xf);am_byte(r.d[2],0);return am_call(c,0xc6a96,0x76d36);
    // BCLR.B #0,15(A6); TST.W 76(A6); BNE.W 76d4a.
    case 0x76d36:if(!on15_bchange(c,r.a[6],0x15,0,false))return false;return on15_test_w(c,0x76,0x76d44,0x76d4a);
    case 0x76d44:if(!on15_bchange(c,r.a[6],0x15,0,true))return false;r.pc=0x76d4a;return true; // BSET.B #0,15(A6).
    case 0x76d4a:return am_call(c,0x4c0ac,0x76d50);
    case 0x76d50:if(!on15_put(c,r.a[6],0x54,2,1))return false;r.pc=0x76d56;return true;    // MOVE.W #1,54(A6).
    case 0x76d56:r.a[0]=0xc88ee;return am_call(c,0x490ba,0x76d62);                         // LEA c88ee.L,A0; JSR 490ba.L.
    case 0x76d62:if(!on15_put(c,r.a[6],0x86,2,r.d[0]&65535U))return false;r.pc=0x76d66;return true; // MOVE.W D0,86(A6).
    case 0x76d66:return on15_animation(c,0xb,ON15_BANK_D4,0x3c,0x76d8e);
    case 0x76d8e:return on15_install(c,0x76d94,0x76d94);                                  // MOVE.L #76d94,(A6).

    // ---- 76d94 (installed): TST.W 86(A6); BNE.W 76dae.
    case 0x76d94:return on15_test_w(c,0x86,0x76d9c,0x76dae);
    case 0x76d9c:return on15_box(c,0x4983e,0x76daa);
    case 0x76daa:return on15_consume(c,true,0x76e62,0x76dae);                             // BCS.W 76e62 (C of 4983e).
    case 0x76dae:return on15_test_w(c,0x78,0x76db6,0x76dd8);                               // TST.W 78(A6); BNE.W 76dd8.
    case 0x76db6:return am_call(c,0x76f98,0x76dba);                                       // JSR 76f98(PC).
    case 0x76dba:return on15_consume(c,true,0x76dd8,0x76dbe);                             // BCS.W 76dd8 (C of 76f98).
    // MOVE.W 42(A0),D0; SUB.W 42(A6),D0; BTST.B #0,15(A6); BNE.W 76dd2.
    case 0x76dbe:
        if(!on15_get(c,r.a[0],0x42,2,value) || !on15_get(c,r.a[6],0x42,2,other))return false;am_word(r.d[0],(value-other)&65535U);
        return on15_bit(c,r.a[6],0x15,0,0x76dd2,0x76dd0);
    case 0x76dd0:am_word(r.d[0],(0U-r.d[0])&65535U);r.pc=0x76dd2;return true;             // NEG.W D0.
    case 0x76dd2:r.pc=(r.d[0]&0x8000U)?0x76dfc:0x76dd8;return true;                       // TST.W D0; BMI.W 76dfc.
    // BTST.B #7,15(A6); BNE.W 76dec / 76e3e / 76ea4.
    case 0x76dd8:return on15_bit(c,r.a[6],0x15,7,0x76dec,0x76de2);
    case 0x76e2a:return on15_bit(c,r.a[6],0x15,7,0x76e3e,0x76e34);
    case 0x76e90:return on15_bit(c,r.a[6],0x15,7,0x76ea4,0x76e9a);
    case 0x76de2:case 0x76e34:case 0x76e9a:return am_call(c,0x4be2c,r.pc+6U);              // JSR 4be2c.L.
    case 0x76dec:case 0x76e3e:case 0x76ea4:return am_call(c,0x4be06,r.pc+6U);              // JSR 4be06.L.
    case 0x76de8:r.pc=0x76df2;return true;                                                // BRA.W 76df2.
    case 0x76e3a:r.pc=0x76e44;return true;                                                // BRA.W 76e44.
    case 0x76ea0:r.pc=0x76eaa;return true;                                                // BRA.W 76eaa.
    case 0x76df8:case 0x76e5e:case 0x76eba:r.pc=0x76ebe;return true;                       // BRA.W 76ebe.
    case 0x76dfc:return on15_animation(c,0xb,ON15_BANK_D4,0x44,0x76e24);
    case 0x76e24:return on15_install(c,0x76e2a,0x76e2a);                                  // MOVE.L #76e2a,(A6).
    case 0x76e4a:return on15_consume(c,false,0x76e5e,0x76e4e);                            // BCC.W 76e5e (C of 49fc6).
    case 0x76e4e:r.a[0]=am_index(r.a[6],0x26);return am_call(c,0x492d0,0x76e58);           // LEA 26(A6),A0; JSR 492d0.L.
    case 0x76e58:return on15_install(c,0x76d66,0x76e5e);                                  // MOVE.L #76d66,(A6).
    case 0x76e62:return on15_animation(c,0xb,ON15_BANK_D4,0x40,0x76e8a);
    case 0x76e8a:return on15_install(c,0x76e90,0x76e90);                                  // MOVE.L #76e90,(A6).
    case 0x76eb0:return on15_consume(c,false,0x76eba,0x76eb4);                            // BCC.W 76eba (C of 49fc6).
    case 0x76eb4:return on15_install(c,0x76d56,0x76eba);                                  // MOVE.L #76d56,(A6).

    // ---- 76ebe (shared tail): TST.W 86(A6); BEQ.W 76eca.
    case 0x76ebe:return on15_test_w(c,0x86,0x76eca,0x76ec6);
    // SUBQ.W #1,86(A6).
    case 0x76ec6:if(!on15_get(c,r.a[6],0x86,2,value) || !on15_put(c,r.a[6],0x86,2,(value+65535U)&65535U))return false;r.pc=0x76eca;return true;
    case 0x76eca:r.a[0]=0x772be;return am_call(c,0x1ab02,0x76ed4);                         // LEA 772be(PC),A0; JSR 1ab02.L.
    case 0x76ed4:return on15_consume(c,false,0x76ede,0x76ed8);                            // BCC.W 76ede (C of 1ab02).
    case 0x76ed8:r.pc=0x2a00;return true;                                                 // JMP 2a00.L.
    case 0x76ee4:return on15_bit(c,r.a[6],0x61,7,0x76eee,0x76f18);                         // BTST.B #7,61(A6); BEQ.W 76f18.
    case 0x76eee:return am_call(c,0xe9112,0x76ef4);                                       // JSR e9112.L (boundary).
    case 0x76ef4:return on15_death(c,0xcdef8,ON15_BANK_D4,0xb,0x1,0xcc778);
    case 0x76f18:if(!on15_put(c,r.a[6],0x5e,1,0))return false;return am_return(c);         // CLR.B 5e(A6); RTS.

    // ---- 76f1e (interpreter command callback): LEA 772be(PC),A0; JSR 1ab80.L.
    case 0x76f1e:r.a[0]=0x772be;return am_call(c,0x1ab80,0x76f28);
    case 0x76f28:return on15_consume(c,false,0x76f2e,0x76f2c);                            // BCC.W 76f2e (C of 1ab80).
    // MOVEA.L #7706a,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0x76f2e:r.a[0]=0x7706a;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x76f3e);
    case 0x76f3e:return on15_consume(c,false,0x76f54,0x76f42);                            // BCC.W 76f54 (C of 28ae).
    case 0x76f42:return on15_box(c,0x4970a,0x76f50);                                      // JSR 4970a.L (N14 boundary).
    case 0x76f50:r.pc=0x76f54;return true;                                                // ORI.B #1,CCR (overwritten by 76f54).
    // CMPI.W #a,7a(A6); BCC.W 76f68 (unsigned 7a >= a).
    case 0x76f54:if(!on15_get(c,r.a[6],0x7a,2,value))return false;r.pc=on15_w(value)>=0xaU?0x76f68:0x76f5e;return true;
    case 0x76f5e:if(!on15_put(c,r.a[0],0x7a,2,0x28))return false;r.pc=0x76f6e;return true; // MOVE.W #28,7a(A0); BRA.W 76f6e.
    case 0x76f68:if(!on15_copy(c,r.a[6],0x7a,r.a[0],0x7a,2))return false;r.pc=0x76f6e;return true; // MOVE.W 7a(A6),7a(A0).
    // MOVE.W 7c(A6),7c(A0); MOVEA.L #76ff2,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0x76f6e:if(!on15_copy(c,r.a[6],0x7c,r.a[0],0x7c,2))return false;r.a[0]=0x76ff2;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x76f84);
    case 0x76f84:return on15_consume(c,false,0x76f96,0x76f88);                            // BCC.W 76f96 (C of 28ae).
    // CLR.W D0; CLR.W D1; JSR 4970a.L (N14 boundary).
    case 0x76f88:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0x76f92);
    case 0x76f92:r.pc=0x76f96;return true;                                                // ORI.B #1,CCR (no consumer: interpreter return).

    // ---- 76f98: TST.W 7c(A6); BEQ.W 76fec.
    case 0x76f98:return on15_test_w(c,0x7c,0x76fec,0x76fa0);
    // MOVE.W #0/#1,D0; JSR 4d7a6.L / 49392.L.
    case 0x76fa0:am_word(r.d[0],0);return am_call(c,0x4d7a6,0x76faa);
    case 0x76fb2:am_word(r.d[0],0);return am_call(c,0x49392,0x76fbc);
    case 0x76fc6:am_word(r.d[0],1);return am_call(c,0x4d7a6,0x76fd0);
    case 0x76fd8:am_word(r.d[0],1);return am_call(c,0x49392,0x76fe2);
    case 0x76faa:r.pc=(r.d[0]&255U)==0U?0x76fc6:0x76fb2;return true;                       // CMPI.B #0,D0; BEQ.W 76fc6.
    case 0x76fd0:r.pc=(r.d[0]&255U)==0U?0x76fec:0x76fd8;return true;                       // CMPI.B #0,D0; BEQ.W 76fec.
    case 0x76fbc:return on15_consume(c,false,0x76fc6,0x76fc0);                            // BCC.W 76fc6 (C of 49392).
    case 0x76fe2:return on15_consume(c,false,0x76fec,0x76fe6);                            // BCC.W 76fec (C of 49392).
    case 0x76fec:r.pc=0x4945e;return true;                                                // JMP 4945e.L.
    default:return am_error(c,"unsupported animation objects n15 PC");
    }
}
}
