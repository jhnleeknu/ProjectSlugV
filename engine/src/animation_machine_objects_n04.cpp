#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t ON04_BANK_B8=0x2000b8;        // MOVE.L 2000b8.L,22(A6) / MOVEA.L 2000b8.L,A1 (ab136 ab1d8; banked window LONG, live bus).
const std::uint32_t ON04_BANK_D0=0x2000d0;        // MOVE.L 2000d0.L,22(A6) (side 3) / MOVEA.L 2000d0.L,A1 (72df2).
const std::uint32_t ON04_BANK_D4=0x2000d4;        // MOVE.L 2000d4.L,22(A6) (side b) / MOVEA.L 2000d4.L,A1 (72e18).
const std::uint32_t ON04_BANK_154=0x200154;       // MOVE.L 200154.L,22(A6) (aa994).
std::uint32_t on04_w(std::uint32_t v) {return v&65535U;}
std::int32_t on04_s(std::uint32_t v) {return static_cast<std::int32_t>(am_extend_word(v&65535U));}
bool on04_neg_w(std::uint32_t v) {return (v&0x8000U)!=0U;}
bool on04_neg_l(std::uint32_t v) {return (v&0x80000000U)!=0U;}
// ASR.W #n / ASR.L #n with the sign bit copied explicitly (no signed right shift).
std::uint32_t on04_asr_w(std::uint32_t v,unsigned int n) {
    std::uint32_t u=v&65535U;for(unsigned int i=0;i<n;++i)u=(u>>1)|(u&0x8000U);return u;
}
std::uint32_t on04_asr_l(std::uint32_t v,unsigned int n) {
    std::uint32_t u=v;for(unsigned int i=0;i<n;++i)u=(u>>1)|(u&0x80000000U);return u;
}
bool on04_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on04_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool on04_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n04 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #callback,(A6) then continue at next_pc.
bool on04_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// TST.W d16(A6) / TST.B d16(A6) (and other zero tests): branch to zero_pc when the value is 0.
bool on04_test(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!on04_get(c,base,displacement,size,value))return false;
    c.s.pc=value==0U?zero_pc:next_pc;return true;
}
// BTST.B #bit,d16(An); Bcc: set_pc when the bit is set.
bool on04_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t set_pc,std::uint32_t clear_pc) {
    std::uint32_t value=0;if(!on04_get(c,base,displacement,1,value))return false;
    c.s.pc=((value>>bit)&1U)!=0U?set_pc:clear_pc;return true;
}
// BSET/BCLR/BCHG.B #bit,d16(An) (BYTE read-modify-write; Z only).
bool on04_bit_op(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int op) {
    std::uint32_t value=0;if(!on04_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;
    if(op==0)value|=mask;else if(op==1)value&=~mask;else value^=mask;
    return on04_put(c,base,displacement,1,value&255U);
}
// ADDI.W/SUBI.W #v,d16(A6) (WORD read-modify-write, delta modulo 10000).
bool on04_add_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t delta) {
    std::uint32_t value=0;if(!on04_get(c,c.s.a[6],displacement,2,value))return false;
    return on04_put(c,c.s.a[6],displacement,2,(value+delta)&65535U);
}
// LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1;
// JSR 49f8c.L (the bank LONG and the LONG at its value + d16 through the live bus).
bool on04_animation(AnimationMachineContext& c,std::uint32_t k,std::uint32_t bank,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!on04_put(c,r.a[6],0x20,2,k) || !am_read(c,bank,4,value) || !on04_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!on04_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!on04_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// TST.W 9c(A6); BNE: side 3 (bank 2000d0, d16 a) when 9c = 0, else side b (bank 2000d4, d16 b) at the BNE target.
bool on04_side(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    return on04_test(c,c.s.a[6],0x9c,2,zero_pc,other_pc);
}
// MOVE.W #2,80(A6) (ab136 only); MOVE.W #1,D0; ADD.W 88(A6),D0; LEA 26(A6),A0; MOVE.W #12a,20(A6); MOVE.L 2000b8.L,22(A6);
// LEA 26(A6),A0; MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 2000b8.L,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.L
// (the bank LONG is read twice; WORD index sign-extended).
bool on04_index_animation(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    am_word(r.d[0],1);if(!on04_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],(r.d[0]+value)&65535U);
    r.a[0]=am_index(r.a[6],0x26);
    if(!on04_put(c,r.a[6],0x20,2,0x12a) || !am_read(c,ON04_BANK_B8,4,value) || !on04_put(c,r.a[6],0x22,4,value))return false;
    r.a[0]=am_index(r.a[6],0x26);am_word(r.d[1],r.d[0]);am_word(r.d[1],(r.d[1]<<2)&65535U);
    if(!am_read(c,ON04_BANK_B8,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;
    am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// SUB.W src,Dn (WORD); returns the new low WORD (the caller tests N).
std::uint32_t on04_sub_w(std::uint32_t& reg,std::uint32_t src) {am_word(reg,(reg-src)&65535U);return reg&65535U;}
std::uint32_t on04_add_w(std::uint32_t& reg,std::uint32_t src) {am_word(reg,(reg+src)&65535U);return reg&65535U;}
// BPL on a WORD result: next when bit 15 is set.
bool on04_pl_w(AnimationMachineContext& c,std::uint32_t v,std::uint32_t pl_pc,std::uint32_t mi_pc) {c.s.pc=on04_neg_w(v)?mi_pc:pl_pc;return true;}
// MOVE.B #ff,17(A6); LEA table.L,A0; MOVEA.L bank.L,A1; MOVE.W #d1,D1; MOVE.W #d2,D2; JMP cc778.L (boundary tail).
bool on04_tail(AnimationMachineContext& c,std::uint32_t table,std::uint32_t bank,std::uint32_t d1,std::uint32_t d2) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!on04_put(c,r.a[6],0x17,1,0xff))return false;r.a[0]=table;
    if(!am_read(c,bank,4,value))return false;r.a[1]=value;am_word(r.d[1],d1);am_word(r.d[2],d2);r.pc=0xcc778;return true;
}
// LEA/MOVEA.L #address,A0; JSR target.L.
bool on04_a0_call(AnimationMachineContext& c,std::uint32_t address,std::uint32_t target,std::uint32_t return_pc) {
    c.s.a[0]=address;return am_call(c,target,return_pc);
}
}
// Objects F4 N04 (224 block starts): 4a46c (parent BYTE 17 parity, returns C: ORI/ANDI CCR), 4bc04 (work RAM grid WORD 5b88(A5)), the
// motion update 6feb4 and 70036 (WORD/LONG arithmetic with explicit ASR/NEG/SWAP), the U13 callbacks 71c90 (installed 71d0a) and 72a18
// (installed 72bcc 72c72 72ce4 72d42; banks 2000d0/2000d4 + d16) with the shared tail 72dd2 (BSR 6feb4, BRA 70054 U12), the U07 child
// aa93e (installed aa9ec, 28ae child ab0b8 with installed ab11a ab17a, tail ab02a; banks 200154 2000b8) and the interpreter table handlers
// eb752 eb766. Consumers 72be2 72d04 (49fc6), 72bfc 72c08 (boundary 49c38), 72c18 72c30 (289e), 72c46 (boundary 494c0), 72e4c aaa02
// (1ab02) and ab06c (288c). Producers 4a48a (Set) and 4a490 (Clear). Boundaries without an executor: 494c0 4970a 49c38 4bb52 cc778 and
// the N03 callee 4b82e. The BLT ab1a6 is folded into its two CMPI predecessors ab19a and ab1a2 (ab1a6 is an interior PC; decision 3).
bool animation_objects_n04_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,value2=0;
    switch(r.pc) {
    // ---- 4a46c: MOVEA.L c(A6),A0; MOVE.B 17(A0),D0; BEQ.W 4a490; BMI.W 4a47e (bundled).
    case 0x4a46c:
        if(!on04_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!on04_get(c,r.a[0],0x17,1,value))return false;am_byte(r.d[0],value);
        r.pc=(value&255U)==0U?0x4a490:((value&0x80U)!=0U?0x4a47e:0x4a47c);return true;
    case 0x4a47c:am_byte(r.d[0],(r.d[0]+1U)&255U);r.pc=0x4a47e;return true;            // ADDQ.B #1,D0.
    // MOVE.B D0,17(A6); BTST.B #0,D0; BNE.W 4a490.
    case 0x4a47e:if(!on04_put(c,r.a[6],0x17,1,r.d[0]&255U))return false;r.pc=(r.d[0]&1U)!=0U?0x4a490:0x4a48a;return true;
    case 0x4a48a:r.carry=AnimationCarrySet;return am_return(c);                         // ORI.B #1,CCR; RTS.
    case 0x4a490:r.carry=AnimationCarryClear;return am_return(c);                       // ANDI.B #fe,CCR; RTS.

    // ---- 4bc04: SUBI.W #100,D1; CMPI.W #100,D1; BCC.W 4bc40 (unsigned).
    case 0x4bc04:am_word(r.d[1],(r.d[1]-0x100U)&65535U);r.pc=on04_w(r.d[1])>=0x100U?0x4bc40:0x4bc10;return true;
    // LSR.W #4,D1; ANDI.W #e,D1; SUBI.W #20,D0; CMPI.W #200,D0; BCC.W 4bc40.
    case 0x4bc10:
        am_word(r.d[1],(on04_w(r.d[1])>>4)&0xeU);am_word(r.d[0],(r.d[0]-0x20U)&65535U);
        r.pc=on04_w(r.d[0])>=0x200U?0x4bc40:0x4bc22;return true;
    // LSR.W #1,D0; ANDI.W #f0,D0; LEA 5b88(A5),A0; ADDA.W D0,A0; ADDA.W D1,A0; MOVE.W (A0),D0; CMPI.W #100,D0; BCS.W 4bc3e.
    case 0x4bc22:
        am_word(r.d[0],(on04_w(r.d[0])>>1)&0xf0U);r.a[0]=am_index(r.a[5],0x5b88);
        r.a[0]=am_index(r.a[0],r.d[0]);r.a[0]=am_index(r.a[0],r.d[1]);
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);
        r.pc=on04_w(r.d[0])<0x100U?0x4bc3e:0x4bc3a;return true;
    case 0x4bc3a:am_word(r.d[0],0xff);r.pc=0x4bc3e;return true;                         // MOVE.W #ff,D0.
    // RTS (keeps C).
    case 0x4bc3e:case 0x70052:case 0x72d54:case 0xaaa16:case 0xab076:case 0xeb75a:case 0xeb772:return am_return(c);
    case 0x4bc40:r.d[0]=0;return am_return(c);                                          // MOVEQ #0,D0; RTS.

    // ---- 6feb4: MOVEQ #0,D2; MOVEQ #0,D3; MOVE.W 42(A6),D0; SUBI.W #20,D0; CMPI.W #100,D0; BCC.W 6ffd6.
    case 0x6feb4:
        r.d[2]=0;r.d[3]=0;if(!on04_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],(value-0x20U)&65535U);
        r.pc=on04_w(r.d[0])>=0x100U?0x6ffd6:0x6fec8;return true;
    case 0x6fec8:return am_call(c,0x48502,0x6fece);                                     // JSR 48502.L.
    case 0x6fece:r.pc=on04_w(r.d[7])==0U?0x6ff74:0x6fed4;return true;                   // TST.W D7; BEQ.W 6ff74.
    // MOVE.W #60,D6; SUB.W 46(A6),D1; BPL.W 6fee2.
    case 0x6fed4:
        am_word(r.d[6],0x60);if(!on04_get(c,r.a[6],0x46,2,value))return false;
        return on04_pl_w(c,on04_sub_w(r.d[1],value),0x6fee2,0x6fee0);
    case 0x6fee0:am_word(r.d[1],on04_asr_w(r.d[1],1));r.pc=0x6fee2;return true;         // ASR.W #1,D1.
    // ASR.W #1,D1; SUB.W D1,D6; BPL.W 6feee.
    case 0x6fee2:am_word(r.d[1],on04_asr_w(r.d[1],1));return on04_pl_w(c,on04_sub_w(r.d[6],r.d[1]&65535U),0x6feee,0x6feea);
    case 0x6feea:am_word(r.d[6],0);r.pc=0x6feee;return true;                            // MOVE.W #0,D6.
    // SUB.W 8e(A6),D0; BPL.W 6fefc.
    case 0x6feee:if(!on04_get(c,r.a[6],0x8e,2,value))return false;return on04_pl_w(c,on04_sub_w(r.d[0],value),0x6fefc,0x6fef6);
    case 0x6fef6:on04_add_w(r.d[0],r.d[6]&65535U);r.pc=0x6fefe;return true;             // ADD.W D6,D0; BRA.W 6fefe.
    case 0x6fefc:on04_sub_w(r.d[0],r.d[6]&65535U);r.pc=0x6fefe;return true;             // SUB.W D6,D0.
    // CMPI.B #0,86(A6); BEQ.W 6ff0e.
    case 0x6fefe:if(!on04_get(c,r.a[6],0x86,1,value))return false;r.pc=(value&255U)==0U?0x6ff0e:0x6ff08;return true;
    // MOVE.W D0,D7; ASR.W #2,D7; SUB.W D7,D0.
    case 0x6ff08:am_word(r.d[7],on04_asr_w(r.d[0],2));on04_sub_w(r.d[0],r.d[7]&65535U);r.pc=0x6ff0e;return true;
    // MOVE.W #60,D6; SUB.W 46(A6),D3; BPL.W 6ff1c.
    case 0x6ff0e:
        am_word(r.d[6],0x60);if(!on04_get(c,r.a[6],0x46,2,value))return false;
        return on04_pl_w(c,on04_sub_w(r.d[3],value),0x6ff1c,0x6ff1a);
    case 0x6ff1a:am_word(r.d[3],on04_asr_w(r.d[3],1));r.pc=0x6ff1c;return true;         // ASR.W #1,D3.
    // ASR.W #1,D3; SUB.W D3,D6; BPL.W 6ff26.
    case 0x6ff1c:am_word(r.d[3],on04_asr_w(r.d[3],1));return on04_pl_w(c,on04_sub_w(r.d[6],r.d[3]&65535U),0x6ff26,0x6ff24);
    case 0x6ff24:r.d[6]=0;r.pc=0x6ff26;return true;                                     // MOVEQ #0,D6.
    // SUB.W 8e(A6),D2; BPL.W 6ff34.
    case 0x6ff26:if(!on04_get(c,r.a[6],0x8e,2,value))return false;return on04_pl_w(c,on04_sub_w(r.d[2],value),0x6ff34,0x6ff2e);
    case 0x6ff2e:on04_add_w(r.d[2],r.d[6]&65535U);r.pc=0x6ff36;return true;             // ADD.W D6,D2; BRA.W 6ff36.
    case 0x6ff34:on04_sub_w(r.d[2],r.d[6]&65535U);r.pc=0x6ff36;return true;             // SUB.W D6,D2.
    // CMPI.B #1,86(A6); BEQ.W 6ff46.
    case 0x6ff36:if(!on04_get(c,r.a[6],0x86,1,value))return false;r.pc=(value&255U)==1U?0x6ff46:0x6ff40;return true;
    // MOVE.W D2,D7; ASR.W #2,D7; SUB.W D7,D2.
    case 0x6ff40:am_word(r.d[7],on04_asr_w(r.d[2],2));on04_sub_w(r.d[2],r.d[7]&65535U);r.pc=0x6ff46;return true;
    case 0x6ff46:am_word(r.d[7],r.d[0]);return on04_pl_w(c,r.d[7],0x6ff4e,0x6ff4c);     // MOVE.W D0,D7; BPL.W 6ff4e.
    case 0x6ff4c:am_word(r.d[7],(0U-r.d[7])&65535U);r.pc=0x6ff4e;return true;           // NEG.W D7.
    case 0x6ff4e:am_word(r.d[6],r.d[2]);return on04_pl_w(c,r.d[6],0x6ff56,0x6ff54);     // MOVE.W D2,D6; BPL.W 6ff56.
    case 0x6ff54:am_word(r.d[6],(0U-r.d[6])&65535U);r.pc=0x6ff56;return true;           // NEG.W D6.
    case 0x6ff56:r.pc=on04_w(r.d[7])<on04_w(r.d[6])?0x6ff5e:0x6ff5c;return true;        // CMP.W D6,D7; BCS.W 6ff5e (unsigned).
    case 0x6ff5c:am_word(r.d[2],r.d[0]);r.pc=0x6ff5e;return true;                       // MOVE.W D0,D2.
    // MOVE.W D2,D0; ADDI.W #18,D0; CMPI.W #30,D0; BCC.W 6ff70.
    case 0x6ff5e:am_word(r.d[0],(r.d[2]+0x18U)&65535U);r.pc=on04_w(r.d[0])>=0x30U?0x6ff70:0x6ff6c;return true;
    // NEG.W D2; ASR.W #1,D2.
    case 0x6ff6c:am_word(r.d[2],(0U-r.d[2])&65535U);am_word(r.d[2],on04_asr_w(r.d[2],1));r.pc=0x6ff70;return true;
    case 0x6ff70:am_swap(r.d[2]);am_word(r.d[2],0);r.pc=0x6ff74;return true;            // SWAP D2; CLR.W D2.
    // MOVE.W 9a(A6),D7; BEQ.W 6ffd6.
    case 0x6ff74:if(!on04_get(c,r.a[6],0x9a,2,value))return false;am_word(r.d[7],value);r.pc=on04_w(value)==0U?0x6ffd6:0x6ff7c;return true;
    // MOVE.W 46(A6),D1; SUB.W 98(A6),D1; SUB.W 53a6(A5),D1; BPL.W 6ff8e.
    case 0x6ff7c:
        if(!on04_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],value);
        if(!on04_get(c,r.a[6],0x98,2,value) || !on04_get(c,r.a[5],0x53a6,2,value2))return false;
        on04_sub_w(r.d[1],value);return on04_pl_w(c,on04_sub_w(r.d[1],value2),0x6ff8e,0x6ff8c);
    case 0x6ff8c:am_word(r.d[1],(0U-r.d[1])&65535U);r.pc=0x6ff8e;return true;           // NEG.W D1.
    // SUB.W D1,D7; BCC.W 6ff96 (no borrow: unsigned D7.W >= D1.W).
    case 0x6ff8e:value=on04_w(r.d[7]);value2=on04_w(r.d[1]);on04_sub_w(r.d[7],value2);r.pc=value>=value2?0x6ff96:0x6ff94;return true;
    case 0x6ff94:r.d[7]=0;r.pc=0x6ff96;return true;                                     // MOVEQ #0,D7.
    // MOVE.W 96(A6),D0; ADD.W 53a2(A5),D0; SUB.W 42(A6),D0; BMI.W 6ffb2.
    case 0x6ff96:
        if(!on04_get(c,r.a[6],0x96,2,value))return false;am_word(r.d[0],value);
        if(!on04_get(c,r.a[5],0x53a2,2,value) || !on04_get(c,r.a[6],0x42,2,value2))return false;
        on04_add_w(r.d[0],value);return on04_pl_w(c,on04_sub_w(r.d[0],value2),0x6ffa6,0x6ffb2);
    case 0x6ffa6:return on04_pl_w(c,on04_sub_w(r.d[0],r.d[7]&65535U),0x6ffac,0x6ffae);  // SUB.W D7,D0; BMI.W 6ffae.
    case 0x6ffac:case 0x6ffb8:r.d[0]=0;r.pc=r.pc==0x6ffacU?0x6ffaeU:0x6ffbaU;return true; // MOVEQ #0,D0.
    case 0x6ffae:r.pc=0x6ffba;return true;                                              // BRA.W 6ffba.
    case 0x6ffb2:return on04_pl_w(c,on04_add_w(r.d[0],r.d[7]&65535U),0x6ffba,0x6ffb8);  // ADD.W D7,D0; BPL.W 6ffba.
    // SWAP D0; CLR.W D0; MOVE.L D0,D7; BPL.W 6ffc6.
    case 0x6ffba:am_swap(r.d[0]);am_word(r.d[0],0);r.d[7]=r.d[0];r.pc=on04_neg_l(r.d[7])?0x6ffc4:0x6ffc6;return true;
    case 0x6ffc4:r.d[7]=0U-r.d[7];r.pc=0x6ffc6;return true;                             // NEG.L D7.
    case 0x6ffc6:r.d[6]=r.d[2];r.pc=on04_neg_l(r.d[6])?0x6ffcc:0x6ffce;return true;     // MOVE.L D2,D6; BPL.W 6ffce.
    case 0x6ffcc:r.d[6]=0U-r.d[6];r.pc=0x6ffce;return true;                             // NEG.L D6.
    case 0x6ffce:r.pc=r.d[7]<r.d[6]?0x6ffd6:0x6ffd4;return true;                        // CMP.L D6,D7; BCS.W 6ffd6 (unsigned).
    case 0x6ffd4:r.d[2]=r.d[0];r.pc=0x6ffd6;return true;                                // MOVE.L D0,D2.
    // MOVE.L #a00000,D0; SUB.L 8e(A6),D0; BPL.W 6fff4.
    case 0x6ffd6:if(!on04_get(c,r.a[6],0x8e,4,value))return false;r.d[0]=0xa00000U-value;r.pc=on04_neg_l(r.d[0])?0x6ffe4:0x6fff4;return true;
    case 0x6ffe4:r.d[0]+=0x600000U;r.pc=on04_neg_l(r.d[0])?0x6fff0:0x6ffee;return true; // ADDI.L #600000,D0; BMI.W 6fff0.
    case 0x6ffee:case 0x6fffe:r.d[0]=0;r.pc=r.pc==0x6ffeeU?0x6fff0U:0x70000U;return true; // MOVEQ #0,D0.
    case 0x6fff0:r.pc=0x70000;return true;                                              // BRA.W 70000.
    case 0x6fff4:r.d[0]-=0x600000U;r.pc=on04_neg_l(r.d[0])?0x6fffe:0x70000;return true; // SUBI.L #600000,D0; BPL.W 70000.
    // ADD.L D0,D2; MOVEQ #0,D0; MOVE.W 8c(A6),D0; ADDI.W #13f,D0; MOVE.W D0,8c(A6); LSL.L #3,D0; SUB.L 92(A6),D2; MOVE.L 92(A6),D1;
    // BMI.W 70020.
    case 0x70000:
        r.d[2]+=r.d[0];r.d[0]=0;if(!on04_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],(value+0x13fU)&65535U);
        if(!on04_put(c,r.a[6],0x8c,2,r.d[0]&65535U) || !on04_get(c,r.a[6],0x92,4,value))return false;
        r.d[0]<<=3;r.d[2]-=value;r.d[1]=value;r.pc=on04_neg_l(r.d[1])?0x70020:0x7001e;return true;
    case 0x7001e:r.d[0]=0U-r.d[0];r.pc=0x70020;return true;                             // NEG.L D0.
    // ADD.L D0,D1; ASR.L #5,D1; ASR.L #7,D2; SUB.L D1,D2; ADD.L 92(A6),D2; MOVE.L D2,92(A6); ADD.L D2,8e(A6); RTS.
    case 0x70020:
        r.d[1]=on04_asr_l(r.d[1]+r.d[0],5);r.d[2]=on04_asr_l(r.d[2],7)-r.d[1];
        if(!on04_get(c,r.a[6],0x92,4,value))return false;r.d[2]+=value;
        if(!on04_put(c,r.a[6],0x92,4,r.d[2]) || !on04_get(c,r.a[6],0x8e,4,value) || !on04_put(c,r.a[6],0x8e,4,value+r.d[2]))return false;
        return am_return(c);
    // ---- 70036: CMP.W 9a(A6),D0; BLS.W 70052 (unsigned D0.W <= WORD 9a).
    case 0x70036:if(!on04_get(c,r.a[6],0x9a,2,value))return false;r.pc=on04_w(r.d[0])<=on04_w(value)?0x70052:0x7003e;return true;
    // MOVE.W D0,9a(A6); SUB.W 53a2(A5),D2; SUB.W 53a6(A5),D3; MOVE.W D2,96(A6); MOVE.W D3,98(A6).
    case 0x7003e:
        if(!on04_put(c,r.a[6],0x9a,2,r.d[0]&65535U) || !on04_get(c,r.a[5],0x53a2,2,value) || !on04_get(c,r.a[5],0x53a6,2,value2))return false;
        on04_sub_w(r.d[2],value);on04_sub_w(r.d[3],value2);
        if(!on04_put(c,r.a[6],0x96,2,r.d[2]&65535U) || !on04_put(c,r.a[6],0x98,2,r.d[3]&65535U))return false;r.pc=0x70052;return true;

    // ---- 71c90 (U13 callback): MOVE.L #0,36(A6); TST.W 9c(A6); BNE.W 71ccc.
    case 0x71c90:if(!on04_put(c,r.a[6],0x36,4,0))return false;return on04_side(c,0x71ca0,0x71ccc);
    case 0x71ca0:return on04_animation(c,0x3,ON04_BANK_D0,0x1c,0x71cc8);
    case 0x71ccc:return on04_animation(c,0xb,ON04_BANK_D4,0x1c,0x71cf4);
    // MOVE.L #0,64(A6); MOVE.L #0,3a(A6); MOVE.L #71d0a,(A6).
    case 0x71cf4:if(!on04_put(c,r.a[6],0x64,4,0) || !on04_put(c,r.a[6],0x3a,4,0))return false;return on04_install(c,0x71d0a,0x71d0a);
    // (installed callback) MOVE.L 64(A6),D0; SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6); MOVE.L #fff00000,D0; SUB.L 3a(A6),D0;
    // ASR.L #5,D0; ADD.L D0,3a(A6); JSR 4be34.L.
    case 0x71d0a:
        if(!on04_get(c,r.a[6],0x64,4,value) || !on04_get(c,r.a[6],0x36,4,value2))return false;
        r.d[0]=on04_asr_l(value-value2,5);if(!on04_put(c,r.a[6],0x36,4,value2+r.d[0]) || !on04_get(c,r.a[6],0x3a,4,value))return false;
        r.d[0]=on04_asr_l(0xfff00000U-value,5);if(!on04_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;return am_call(c,0x4be34,0x71d2e);
    // JSR 49fc6.L.
    case 0x71d2e:case 0x72bdc:case 0x72cfe:case 0xaa9f2:case 0xab1c6:return am_call(c,0x49fc6,r.pc+6U);
    case 0x71d34:case 0x72bcc:return on04_bit(c,r.a[6],0x15,7,r.pc==0x71d34U?0x71d3eU:0x72bd6U,r.pc==0x71d34U?0x71d44U:0x71c90U); // BTST.B #7,15(A6); BEQ.W.
    case 0x71d3e:return on04_install(c,0x71d48,0x71d44);                                // MOVE.L #71d48,(A6) (orphan install value).
    // BRA.W 72dd2.
    case 0x71d44:case 0x72c6e:case 0x72d3e:r.pc=0x72dd2;return true;
    // BRA.W (FLOW_ONLY).
    case 0x71cc8:r.pc=0x71cf4;return true;
    case 0x72a5e:r.pc=0x72a8a;return true;
    case 0x72a8a:case 0x72af2:case 0x72b5a:case 0x72bc2:r.pc=0x72bc6;return true;
    case 0x72ac6:r.pc=0x72af2;return true;
    case 0x72b2e:r.pc=0x72b5a;return true;
    case 0x72b96:r.pc=0x72bc2;return true;
    case 0x72ca2:r.pc=0x72cce;return true;
    case 0x72cf4:r.pc=0x72cfe;return true;
    case 0x72e3a:r.pc=0x72e3e;return true;
    case 0x72e8a:r.pc=0x70054;return true;
    case 0xaa9bc:r.pc=0xaa9d6;return true;
    case 0xab222:r.pc=0xab02a;return true;

    // ---- 72a18 (U13 callback): MOVE.L #0,64(A6); JSR 49a58.L.
    case 0x72a18:if(!on04_put(c,r.a[6],0x64,4,0))return false;return am_call(c,0x49a58,0x72a26);
    case 0x72a26:am_word(r.d[0],r.d[0]&3U);r.pc=on04_w(r.d[0])!=0U?0x72a8e:0x72a2e;return true; // ANDI.W #3,D0; BNE.W 72a8e.
    case 0x72a2e:return on04_side(c,0x72a36,0x72a62);
    case 0x72a36:return on04_animation(c,0x3,ON04_BANK_D0,0x168,0x72a5e);
    case 0x72a62:return on04_animation(c,0xb,ON04_BANK_D4,0x1b4,0x72a8a);
    case 0x72a8e:r.pc=on04_w(r.d[0])!=1U?0x72af6:0x72a96;return true;                   // CMPI.W #1,D0; BNE.W 72af6.
    case 0x72a96:return on04_side(c,0x72a9e,0x72aca);
    case 0x72a9e:return on04_animation(c,0x3,ON04_BANK_D0,0x16c,0x72ac6);
    case 0x72aca:return on04_animation(c,0xb,ON04_BANK_D4,0x1b8,0x72af2);
    case 0x72af6:r.pc=on04_w(r.d[0])!=2U?0x72b5e:0x72afe;return true;                   // CMPI.W #2,D0; BNE.W 72b5e.
    case 0x72afe:return on04_side(c,0x72b06,0x72b32);
    case 0x72b06:return on04_animation(c,0x3,ON04_BANK_D0,0x170,0x72b2e);
    case 0x72b32:return on04_animation(c,0xb,ON04_BANK_D4,0x1bc,0x72b5a);
    case 0x72b5e:r.pc=on04_w(r.d[0])!=3U?0x72bc6:0x72b66;return true;                   // CMPI.W #3,D0; BNE.W 72bc6.
    case 0x72b66:return on04_side(c,0x72b6e,0x72b9a);
    case 0x72b6e:return on04_animation(c,0x3,ON04_BANK_D0,0x174,0x72b96);
    case 0x72b9a:return on04_animation(c,0xb,ON04_BANK_D4,0x1c0,0x72bc2);
    case 0x72bc6:return on04_install(c,0x72bcc,0x72bcc);                                // MOVE.L #72bcc,(A6).
    case 0x72bd6:return am_call(c,0x4bfa4,0x72bdc);                                     // JSR 4bfa4.L.
    case 0x72be2:return on04_consume(c,false,0x72bec,0x72be6);                          // BCC.W 72bec (C returned by 49fc6).
    case 0x72be6:return on04_install(c,0x72a18,0x72bec);                                // MOVE.L #72a18,(A6).
    // TST.B 86(A6); BMI.W 72c6e.
    case 0x72bec:if(!on04_get(c,r.a[6],0x86,1,value))return false;r.pc=(value&0x80U)!=0U?0x72c6e:0x72bf4;return true;
    case 0x72bf4:case 0x72c00:r.d[0]=r.pc==0x72bf4U?0U:1U;return am_call(c,0x49c38,r.pc+8U); // MOVEQ #0/#1,D0; JSR 49c38.L (boundary).
    case 0x72bfc:return on04_consume(c,true,0x72c6e,0x72c00);                           // BCS.W 72c6e (C returned by 49c38).
    case 0x72c08:return on04_consume(c,true,0x72c6e,0x72c0c);
    case 0x72c0c:return on04_a0_call(c,0x100cb8,0x289e,0x72c18);                        // LEA 100cb8.L,A0; JSR 289e.L.
    case 0x72c18:return on04_consume(c,false,0x72c24,0x72c1c);                          // BCC.W 72c24 (C returned by 289e).
    case 0x72c1c:return on04_test(c,r.a[0],0x81,1,0x72c6e,0x72c24);                     // TST.B 81(A0); BEQ.W 72c6e.
    case 0x72c24:return on04_a0_call(c,0x100da8,0x289e,0x72c30);                        // LEA 100da8.L,A0; JSR 289e.L.
    case 0x72c30:return on04_consume(c,false,0x72c3c,0x72c34);
    case 0x72c34:return on04_test(c,r.a[0],0x81,1,0x72c6e,0x72c3c);
    case 0x72c3c:return on04_a0_call(c,0x72a10,0x494c0,0x72c46);                        // LEA 72a10(PC),A0; JSR 494c0.L (boundary).
    case 0x72c46:return on04_consume(c,true,0x72c50,0x72c4a);                           // BCS.W 72c50 (C returned by 494c0).
    case 0x72c4a:return on04_install(c,0x72c72,0x72c50);                                // MOVE.L #72c72,(A6).
    // MOVE.W 42(A6),D0; MOVE.W 46(A6),D1; ADDI.W #10,D1; JSR 4bc04.L.
    case 0x72c50:
        if(!on04_get(c,r.a[6],0x42,2,value) || !on04_get(c,r.a[6],0x46,2,value2))return false;
        am_word(r.d[0],value);am_word(r.d[1],(value2+0x10U)&65535U);return am_call(c,0x4bc04,0x72c62);
    case 0x72c62:r.pc=on04_w(r.d[0])==0U?0x72c6e:0x72c68;return true;                   // TST.W D0; BEQ.W 72c6e.
    case 0x72c68:return on04_install(c,0x72c72,0x72c6e);                                // MOVE.L #72c72,(A6).

    // ---- 72c72 (installed callback): TST.W 9c(A6); BNE.W 72ca6.
    case 0x72c72:return on04_side(c,0x72c7a,0x72ca6);
    case 0x72c7a:return on04_animation(c,0x3,ON04_BANK_D0,0x2c,0x72ca2);
    case 0x72ca6:return on04_animation(c,0xb,ON04_BANK_D4,0x2c,0x72cce);
    case 0x72cce:return on04_bit(c,r.a[6],0x82,0,0x72cde,0x72cd8);                      // BTST.B #0,82(A6); BNE.W 72cde.
    case 0x72cd8:if(!on04_bit_op(c,r.a[6],0x15,0,2))return false;r.pc=0x72cde;return true; // BCHG.B #0,15(A6).
    case 0x72cde:return on04_install(c,0x72ce4,0x72ce4);                                // MOVE.L #72ce4,(A6).
    case 0x72ce4:return on04_bit(c,r.a[6],0x15,7,0x72cf8,0x72cee);                      // (installed callback) BTST.B #7,15(A6); BNE.W 72cf8.
    case 0x72cee:return am_call(c,0x4be2c,0x72cf4);                                     // JSR 4be2c.L.
    case 0x72cf8:case 0xaa9ec:return am_call(c,0x4be06,r.pc+6U);                        // JSR 4be06.L.
    case 0x72d04:return on04_consume(c,false,0x72d3e,0x72d08);                          // BCC.W 72d3e (C returned by 49fc6).
    // ADDI.W #20,46(A6); ADDI.W #40,42(A6); JSR 4bb52.L (boundary).
    case 0x72d08:if(!on04_add_word(c,0x46,0x20) || !on04_add_word(c,0x42,0x40))return false;return am_call(c,0x4bb52,0x72d1a);
    case 0x72d1a:if(!on04_add_word(c,0x42,0x10000U-0x80U))return false;return am_call(c,0x4bb52,0x72d26); // SUBI.W #80,42(A6); JSR 4bb52.L.
    case 0x72d26:if(!on04_add_word(c,0x42,0x40))return false;return am_call(c,0x4bb52,0x72d32); // ADDI.W #40,42(A6); JSR 4bb52.L.
    // SUBI.W #20,46(A6); MOVE.L #71032,(A6) (N15 install value).
    case 0x72d32:if(!on04_add_word(c,0x46,0x10000U-0x20U))return false;return on04_install(c,0x71032,0x72d3e);

    // ---- 72d42 (installed callback): JSR 43e34.L.
    case 0x72d42:case 0xab1ba:return am_call(c,0x43e34,r.pc+6U);
    case 0x72d48:return on04_test(c,r.a[6],0x62,1,0x72d50,0x72d54);                     // TST.B 62(A6); BNE.W 72d54.
    case 0x72d50:if(!on04_get(c,r.a[6],0x9e,4,value))return false;return on04_install(c,value,0x72d54); // MOVE.L 9e(A6),(A6).

    // ---- 72dd2 (shared tail): JSR 4b54e.L.
    case 0x72dd2:return am_call(c,0x4b54e,0x72dd8);
    case 0x72dd8:return on04_bit(c,r.a[6],0x61,7,0x72de2,0x72e3a);                      // BTST.B #7,61(A6); BEQ.W 72e3a.
    // MOVEA.L c(A6),A0; ST.B 62(A0); TST.W 9c(A6); BNE.W 72e18.
    case 0x72de2:
        if(!on04_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!on04_put(c,r.a[0],0x62,1,0xff))return false;
        return on04_side(c,0x72df2,0x72e18);
    case 0x72df2:return on04_tail(c,0xcdeea,ON04_BANK_D0,3,0);
    case 0x72e18:return on04_tail(c,0xcdef8,ON04_BANK_D4,0xb,1);
    case 0x72e3e:return am_call(c,0x6feb4,0x72e42);                                     // BSR.W 6feb4.
    case 0x72e42:return on04_a0_call(c,0x72d56,0x1ab02,0x72e4c);                        // LEA 72d56(PC),A0; JSR 1ab02.L.
    case 0x72e4c:return on04_consume(c,false,0x72e5e,0x72e50);                          // BCC.W 72e5e (C returned by 1ab02).
    // MOVEA.L c(A6),A0; ST.B 62(A0); JMP 2a00.L (ST keeps the CCR).
    case 0x72e50:if(!on04_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!on04_put(c,r.a[0],0x62,1,0xff))return false;r.pc=0x2a00;return true;
    // MOVE.B 62(A6),D0; BEQ.W 72e8a.
    case 0x72e5e:if(!on04_get(c,r.a[6],0x62,1,value))return false;am_byte(r.d[0],value);r.pc=(value&255U)==0U?0x72e8a:0x72e66;return true;
    // SUBQ.W #1,D0; ANDI.W #1,D0; BNE.W 72e7a.
    case 0x72e66:am_word(r.d[0],(r.d[0]-1U)&1U);r.pc=on04_w(r.d[0])!=0U?0x72e7a:0x72e70;return true;
    case 0x72e70:if(!on04_bit_op(c,r.a[6],0x15,0,0))return false;r.pc=0x72e80;return true; // BSET.B #0,15(A6); BRA.W 72e80.
    case 0x72e7a:if(!on04_bit_op(c,r.a[6],0x15,0,1))return false;r.pc=0x72e80;return true; // BCLR.B #0,15(A6).
    // MOVE.L (A6),9e(A6); MOVE.L #72d42,(A6).
    case 0x72e80:if(!am_read(c,r.a[6],4,value) || !on04_put(c,r.a[6],0x9e,4,value))return false;return on04_install(c,0x72d42,0x72e8a);

    // ---- aa93e (U07 child): MOVE.W #54,D0; MOVE.W #2,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xaa93e:am_word(r.d[0],0x54);am_word(r.d[1],2);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xaa950);
    case 0xaa950:case 0xab0ee:am_word(r.d[0],0xc2e);return am_call(c,0x4a496,r.pc+0xaU); // MOVE.W #c2e,D0; JSR 4a496.L.
    // BSET.B #6,15(A6); MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.W 76(A6),90(A6); MOVE.W 78(A6),92(A6); JSR 4c0ac.L.
    case 0xaa95a:
        if(!on04_bit_op(c,r.a[6],0x15,6,0) || !on04_put(c,r.a[6],0x68,2,0) || !on04_put(c,r.a[6],0x1e,2,0) ||
           !on04_get(c,r.a[6],0x76,2,value) || !on04_put(c,r.a[6],0x90,2,value) || !on04_get(c,r.a[6],0x78,2,value) ||
           !on04_put(c,r.a[6],0x92,2,value))return false;
        return am_call(c,0x4c0ac,0xaa97e);
    case 0xaa97e:return on04_test(c,r.a[6],0x92,2,0xaa986,0xaa98c);                     // TST.W 92(A6); BNE.W aa98c.
    case 0xaa986:if(!on04_bit_op(c,r.a[6],0x15,0,0))return false;r.pc=0xaa98c;return true; // BSET.B #0,15(A6).
    case 0xaa98c:return on04_test(c,r.a[6],0x90,2,0xaa994,0xaa9c0);                     // TST.W 90(A6); BNE.W aa9c0.
    case 0xaa994:return on04_animation(c,0x10b,ON04_BANK_154,0x4,0xaa9bc);
    // MOVE.W #10b,20(A6); MOVEA.L #acbfe,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0xaa9c0:if(!on04_put(c,r.a[6],0x20,2,0x10b))return false;r.a[1]=0xacbfe;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xaa9d6);
    case 0xaa9d6:r.a[0]=0xab0b8;am_word(r.d[0],0xa);return am_call(c,0x28ae,0xaa9e6);  // MOVEA.L #ab0b8,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0xaa9e6:return on04_install(c,0xaa9ec,0xaa9ec);                                // MOVE.L #aa9ec,(A6).
    case 0xaa9f8:return on04_a0_call(c,0xaa8ba,0x1ab02,0xaaa02);                        // LEA aa8ba(PC),A0; JSR 1ab02.L.
    case 0xaaa02:return on04_consume(c,false,0xaaa16,0xaaa06);                          // BCC.W aaa16 (C returned by 1ab02).
    // BSET.B #7,61(A6); CLR.W 54(A6); JMP 2a00.L.
    case 0xaaa06:if(!on04_bit_op(c,r.a[6],0x61,7,0) || !on04_put(c,r.a[6],0x54,2,0))return false;r.pc=0x2a00;return true;

    // ---- ab02a: MOVEA.L c(A6),A0; BTST.B #7,61(A0); BEQ.W ab066.
    case 0xab02a:if(!on04_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;return on04_bit(c,r.a[0],0x61,7,0xab038,0xab066);
    // MOVEA.L #ab424,A0; MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.L.
    case 0xab038:r.a[0]=0xab424;am_word(r.d[0],0xa);r.a[1]=0x100bf4;return am_call(c,0x2986,0xab04e);
    case 0xab04e:r.d[0]=0;r.d[1]=0;return am_call(c,0x4970a,0xab058);                   // MOVEQ #0,D0; MOVEQ #0,D1; JSR 4970a.L (boundary).
    // ADDQ.W #1,68(A0); ADDQ.W #1,1e(A0); JMP 2a00.L.
    case 0xab058:
        if(!on04_get(c,r.a[0],0x68,2,value) || !on04_put(c,r.a[0],0x68,2,(value+1U)&65535U) ||
           !on04_get(c,r.a[0],0x1e,2,value) || !on04_put(c,r.a[0],0x1e,2,(value+1U)&65535U))return false;
        r.pc=0x2a00;return true;
    case 0xab066:return am_call(c,0x288c,0xab06c);                                      // JSR 288c.L.
    case 0xab06c:return on04_consume(c,true,0xab076,0xab070);                           // BCS.W ab076 (C returned by 288c).
    case 0xab070:r.pc=0x2a00;return true;                                               // JMP 2a00.L.
    // ---- ab0b8 (28ae child): MOVEA.L c(A6),A0; TST.W 92(A0); BNE.W ab0d0.
    case 0xab0b8:case 0xab11a:
        if(!on04_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        return r.pc==0xab0b8U?on04_test(c,r.a[0],0x92,2,0xab0c4,0xab0d0):on04_test(c,r.a[0],0x92,2,0xab126,0xab130);
    // MOVE.W #c/#4,88(A6); MOVEQ #-14/#14,D0; (BRA.W) ab0d8.
    case 0xab0c4:case 0xab0d0:
        if(!on04_put(c,r.a[6],0x88,2,r.pc==0xab0c4U?0xcU:0x4U))return false;r.d[0]=r.pc==0xab0c4U?0xffffffecU:0x14U;r.pc=0xab0d8;return true;
    case 0xab0d8:r.d[1]=0x14;return am_call(c,0x49290,0xab0e0);                         // MOVEQ #14,D1; JSR 49290.L.
    case 0xab0e0:am_word(r.d[0],0xc2c);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xab0ee); // MOVE.W #c2c,D0; MOVE.B #0,D1; JSR 8ebe.L.
    // BSET.B #6,15(A6); MOVEA.L c(A6),A0; MOVE.W 68(A0),68(A6); MOVE.W 1e(A0),1e(A6); ADDI.W #100,68(A6); ADDI.W #100,1e(A6).
    case 0xab0f8:
        if(!on04_bit_op(c,r.a[6],0x15,6,0) || !on04_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!on04_get(c,r.a[0],0x68,2,value) || !on04_put(c,r.a[6],0x68,2,value) || !on04_get(c,r.a[0],0x1e,2,value) ||
           !on04_put(c,r.a[6],0x1e,2,value) || !on04_add_word(c,0x68,0x100) || !on04_add_word(c,0x1e,0x100))return false;
        r.pc=0xab11a;return true;
    // MOVE.W #c/#4,84(A6); (BRA.W) ab136.
    case 0xab126:case 0xab130:if(!on04_put(c,r.a[6],0x84,2,r.pc==0xab126U?0xcU:0x4U))return false;r.pc=0xab136;return true;
    // MOVE.W #2,80(A6); then the 2000b8 index animation (1 + 88).
    case 0xab136:if(!on04_put(c,r.a[6],0x80,2,2))return false;return on04_index_animation(c,0xab174);
    case 0xab174:return on04_install(c,0xab17a,0xab17a);                                // MOVE.L #ab17a,(A6).
    // (installed callback) SUBQ.W #1,80(A6); BNE.W ab1ba.
    case 0xab17a:
        if(!on04_get(c,r.a[6],0x80,2,value))return false;value=(value-1U)&65535U;if(!on04_put(c,r.a[6],0x80,2,value))return false;
        r.pc=value!=0U?0xab1ba:0xab182;return true;
    // MOVE.W #2,80(A6); MOVE.W 88(A6),D0; MOVE.W 84(A6),D1; SUB.W D0,D1; BEQ.W ab1ba; BLT.W ab1a2 (bundled: Z and N^V of the SUB).
    case 0xab182:
        if(!on04_put(c,r.a[6],0x80,2,2) || !on04_get(c,r.a[6],0x88,2,value) || !on04_get(c,r.a[6],0x84,2,value2))return false;
        am_word(r.d[0],value);am_word(r.d[1],value2);on04_sub_w(r.d[1],value);
        r.pc=on04_w(r.d[1])==0U?0xab1ba:(on04_s(value2)<on04_s(value)?0xab1a2:0xab19a);return true;
    // CMPI.W #10,D1; BRA.W ab1a6; BLT.W ab1b0 (the BLT at ab1a6 is folded into both CMPI predecessors: N^V of this CMPI).
    case 0xab19a:r.pc=on04_s(r.d[1])<on04_s(0x10)?0xab1b0:0xab1aa;return true;
    // CMPI.W #fff0,D1; BLT.W ab1b0 (folded ab1a6).
    case 0xab1a2:r.pc=on04_s(r.d[1])<on04_s(0xfff0)?0xab1b0:0xab1aa;return true;
    case 0xab1aa:am_word(r.d[0],(r.d[0]-1U)&65535U);r.pc=0xab1b2;return true;           // SUBQ.W #1,D0; BRA.W ab1b2.
    case 0xab1b0:am_word(r.d[0],(r.d[0]+1U)&65535U);r.pc=0xab1b2;return true;           // ADDQ.W #1,D0.
    // ANDI.W #1f,D0; MOVE.W D0,88(A6).
    case 0xab1b2:am_word(r.d[0],r.d[0]&0x1fU);if(!on04_put(c,r.a[6],0x88,2,r.d[0]&65535U))return false;r.pc=0xab1ba;return true;
    case 0xab1c0:return am_call(c,0x4a46c,0xab1c6);                                     // JSR 4a46c.L.
    // LEA 26(A6),A0; TST.W 4(A0); BNE.W ab210.
    case 0xab1cc:r.a[0]=am_index(r.a[6],0x26);return on04_test(c,r.a[0],0x4,2,0xab1d8,0xab210);
    case 0xab1d8:return on04_index_animation(c,0xab210);
    // MOVEA.L c(A6),A0; TST.B 62(A0); BEQ.W ab222.
    case 0xab210:if(!on04_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;return on04_test(c,r.a[0],0x62,1,0xab222,0xab21c);
    case 0xab21c:return on04_install(c,0xab226,0xab222);                                // MOVE.L #ab226,(A6) (orphan install value).

    // ---- eb752 / eb766 (interpreter table handlers): MOVEA.L (A0),A0 / MOVEA.L #0,A0; JSR 4b82e.L (N03 boundary).
    case 0xeb752:if(!am_read(c,r.a[0],4,value))return false;r.a[0]=value;return am_call(c,0x4b82e,0xeb75a);
    case 0xeb766:r.a[0]=0;return am_call(c,0x4b82e,0xeb772);
    default:return am_error(c,"unsupported animation objects n04 PC");
    }
}
}
