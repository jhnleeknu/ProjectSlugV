#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr5_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ofr5_b(std::uint32_t value) {return value&255U;}
// Signed value of the low WORD (CMPI.W + BLE / BLT).
int ofr5_sw(std::uint32_t value) {const int v=static_cast<int>(value&65535U);return v>=32768?v-65536:v;}
bool ofr5_negative(std::uint32_t value) {return (value&0x80000000U)!=0U;}
// Signed LONG a <= b (CMP.L b,a; BLE): compare with the sign bits flipped (no signed conversion in C++).
bool ofr5_le_long(std::uint32_t a,std::uint32_t b) {return (a^0x80000000U)<=(b^0x80000000U);}
// ASR.L #8: arithmetic, the sign bit is replicated (no signed shift in C++).
std::uint32_t ofr5_asr8(std::uint32_t value) {return (value>>8)|(ofr5_negative(value)?0xff000000U:0U);}
// MULU.W: the unsigned product of the two low WORDs (at most fffe0001, no overflow in 32 bits).
std::uint32_t ofr5_mulu(std::uint32_t a,std::uint32_t b) {return ofr5_w(a)*ofr5_w(b);}
bool ofr5_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr5_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BCC / BCS on a known C (returned by a callee): clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ofr5_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr5 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W #183,20(A6); MOVE.L 200190.l,22(A6) (the bank-window LONG read through the live bus).
bool ofr5_bank_head(AnimationMachineContext& c) {
    std::uint32_t value=0;return ofr5_put(c,c.s.a[6],0x20,2,0x183) && am_read(c,0x200190,4,value) && ofr5_put(c,c.s.a[6],0x22,4,value);
}
// LONG (A7 + 2) += addend (ADD.L D2,2(A7)); carry = the 32-bit carry out (BCC.B skips the ADDQ.W #1,(A7) of the high WORD).
bool ofr5_add_middle(AnimationMachineContext& c,std::uint32_t addend,bool& carry) {
    std::uint32_t value=0;if(!ofr5_get(c,c.s.a[7],2,4,value))return false;
    const std::uint32_t sum=value+addend;carry=sum<value;return ofr5_put(c,c.s.a[7],2,4,sum);
}
// One step of the unrolled division 5aeea..5b1f6 (contract decision 4): ADD.L D0,D0 (X := old bit 31); ADDX.W D1,D1 (WORD, X := the 16-bit carry,
// the upper WORD of D1 stays); ADDX.L D3,D3; CMP.L D2,D3; BCS.W next_pc (D3 < D2 unsigned), otherwise subtract_pc.  X never leaves the block.
void ofr5_divide_step(AnimationMachineState& r,std::uint32_t next_pc,std::uint32_t subtract_pc) {
    std::uint32_t x=r.d[0]>>31;r.d[0]=r.d[0]<<1;
    const std::uint32_t word=(ofr5_w(r.d[1])<<1)+x;x=word>>16;am_word(r.d[1],word);
    r.d[3]=(r.d[3]<<1)+x;
    r.pc=r.d[3]<r.d[2]?next_pc:subtract_pc;
}
}
// Objects FR5 (195 block starts, contract docs/analysis/animation-machine-frontier-fr5-contract.md): the area-D IO frontier of the FR4 IO rerun
// 5ab82 (the 28ae child of N13 5ab3a: a thrown projectile [I]) with its installs 5ac84 / 5add8, the 28ae child 5ad98, the fixed-point multiply
// 5ae66 (5ae54 / 5ae10 / 5aebe), the fixed-point divide 5b1f8 (5aede and its 48 unrolled steps) and the distance helper 4464a.  Every exit is routed
// except the TRAP #15 5ae0e (decision 2: 5ae56 / 5aee4 end with PC := 5ae0e, the next dispatch fails).  MOVE.L #v,(A6) enters v only when v is the
// next PC (5add8), otherwise it only writes the callback LONG (5ac84 5aca6 5ad66).  The 6 consumers 5abd6 (4945e), 5acac (4b6f4), 5ad60 5ae02
// (1ab80), 5ad80 (28ae) and 5adf2 (49fc6) read a known C or fail; 5ad8e (ORI) sets C without a reader.  X stays inside its block.  Data through the
// live bus (no limit test).
bool animation_objects_fr5_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool carry=false;
    switch(r.pc) {
    case 0x5ad64:case 0x5ae06:case 0x5ae64:case 0x5aed8:case 0x5b1f6:case 0x5b21e:return am_return(c);   // RTS.
    case 0x5ad92:case 0x5ae08:r.pc=0x2a00;return true;                                                    // JMP 2a00.l.
    // ---- 4464a: TST.W D0; BPL.B 44650 / NEG.W D0; TST.W D1; BPL.B 44656 / NEG.W D1; CMP.W D0,D1; BLS.B 44660 (D1.W <= D0.W unsigned).
    case 0x4464a:r.pc=(r.d[0]&0x8000U)!=0U?0x4464e:0x44650;return true;
    case 0x4464e:am_word(r.d[0],0U-r.d[0]);r.pc=0x44650;return true;
    case 0x44650:r.pc=(r.d[1]&0x8000U)!=0U?0x44654:0x44656;return true;
    case 0x44654:am_word(r.d[1],0U-r.d[1]);r.pc=0x44656;return true;
    case 0x44656:r.pc=ofr5_w(r.d[1])<=ofr5_w(r.d[0])?0x44660:0x4465a;return true;
    case 0x4465a:am_word(r.d[0],(ofr5_w(r.d[0])>>1)+r.d[1]);return am_return(c);                   // LSR.W #1,D0; ADD.W D1,D0; RTS.
    case 0x44660:am_word(r.d[1],ofr5_w(r.d[1])>>1);am_word(r.d[0],r.d[0]+r.d[1]);return am_return(c);   // LSR.W #1,D1; ADD.W D1,D0; RTS.
    // ---- 5ab82 (28ae child value of N13 5ab3a) / 5ad98 (28ae child value of 5ad1c): MOVE.W #183,20(A6); MOVE.L 200190.l,22(A6);
    // 5ab82: MOVE.W #1a21,D0; JSR 3af8.l / 5ad98: JSR 8ff4.l.
    case 0x5ab82:if(!ofr5_bank_head(c))return false;am_word(r.d[0],0x1a21);return am_call(c,0x3af8,0x5ab9a);
    case 0x5ad98:if(!ofr5_bank_head(c))return false;return am_call(c,0x8ff4,0x5adac);
    case 0x5ab9a:return am_call(c,0x8ff4,0x5aba0);                                                     // JSR 8ff4.l.
    case 0x5aba0:case 0x5adac:am_word(r.d[0],0xd42);am_byte(r.d[1],0);return am_call(c,0x8ebe,r.pc+14U);   // MOVE.W #d42,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVEA.L #5cf10 | 5cf3e,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x5abae:case 0x5adba:r.a[1]=r.pc==0x5abaeU?0x5cf10U:0x5cf3eU;am_word(r.d[0],0x100);return am_call(c,0x49f8c,r.pc+16U);
    // MOVE.W #e0ef,68(A6); MOVE.W #e0ef,1e(A6); BSET.B #3,15(A6); JSR 4945e.l.
    case 0x5abbe:
        if(!ofr5_put(c,r.a[6],0x68,2,0xe0ef) || !ofr5_put(c,r.a[6],0x1e,2,0xe0ef) || !ofr5_get(c,r.a[6],0x15,1,value) ||
           !ofr5_put(c,r.a[6],0x15,1,value|8U))return false;
        return am_call(c,0x4945e,0x5abd6);
    case 0x5abd6:return ofr5_carry(c,0x5abda,0x5abe2);                                                // BCS.W 5abe2 (C of 4945e).
    case 0x5abda:if(!ofr5_get(c,r.a[0],0x42,2,value))return false;am_word(r.d[0],value);r.pc=0x5abea;return true;   // MOVE.W 42(A0),D0; BRA.W 5abea.
    case 0x5abe2:if(!ofr5_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value-0x60U);r.pc=0x5abea;return true;   // MOVE.W 42(A6),D0; SUBI.W #60,D0.
    // SUB.W 42(A6),D0; CMPI.W #ffc0,D0; BLE.W 5abfa (signed WORD <= -40) / 5abf6: MOVE.W #ffc0,D0.
    case 0x5abea:if(!ofr5_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],r.d[0]-value);r.pc=ofr5_sw(r.d[0])<=-64?0x5abfa:0x5abf6;return true;
    case 0x5abf6:am_word(r.d[0],0xffc0);r.pc=0x5abfa;return true;
    // MOVE.W #120,D1; SUB.W 46(A6),D1; MOVEM.W D0-D1,-(A7) (D0.W at the lower address); MOVE.L #1000000,D2; MOVE.L D2,-(A7); JSR 4464a.l.
    case 0x5abfa:
        if(!ofr5_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],0x120U-value);
        if(!am_push(c,2,ofr5_w(r.d[1])) || !am_push(c,2,ofr5_w(r.d[0])))return false;r.d[2]=0x1000000U;if(!am_push(c,4,r.d[2]))return false;
        return am_call(c,0x4464a,0x5ac14);
    // MOVE.L (A7)+,D1; SWAP D0; CLR.W D0; JSR 5b1f8(PC).
    case 0x5ac14:if(!am_pop(c,4,value))return false;r.d[1]=value;am_swap(r.d[0]);am_word(r.d[0],0);return am_call(c,0x5b1f8,0x5ac1e);
    // MOVE.L D0,-(A7); MOVEA.L c(A6),A0; BTST.B #1,80(A0); BNE.W 5ac3e.
    case 0x5ac1e:
        if(!am_push(c,4,r.d[0]) || !ofr5_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ofr5_get(c,r.a[0],0x80,1,value))return false;r.pc=(value&2U)!=0U?0x5ac3e:0x5ac2e;return true;
    case 0x5ac2e:r.a[0]=0x5ddde;return am_call(c,0x490ba,0x5ac3a);                                    // LEA 5ddde.l,A0; JSR 490ba.l.
    case 0x5ac3a:r.pc=0x5ac4a;return true;                                                             // BRA.W 5ac4a.
    case 0x5ac3e:r.a[0]=0x5de40;return am_call(c,0x490ba,0x5ac4a);                                    // LEA 5de40.l,A0; JSR 490ba.l.
    // EXT.L D0; ASL.L #8,D0; MOVE.L D0,D1; MOVE.L (A7)+,D0; JSR 5ae66(PC).
    case 0x5ac4a:r.d[0]=am_extend_word(r.d[0])<<8;r.d[1]=r.d[0];if(!am_pop(c,4,value))return false;r.d[0]=value;return am_call(c,0x5ae66,0x5ac56);
    // MOVE.L D0,D2; MOVEM.W (A7)+,D0-D1 (sign-extended, D0 from the lower address); CLR.W D3; MOVE.B #70,D3; JSR d1028.l.
    case 0x5ac56:
        r.d[2]=r.d[0];if(!am_pop(c,2,value))return false;r.d[0]=am_extend_word(value);if(!am_pop(c,2,value))return false;r.d[1]=am_extend_word(value);
        am_word(r.d[3],0);am_byte(r.d[3],0x70);return am_call(c,0xd1028,0x5ac68);
    // MOVE.L D0,36(A6); MOVE.L D1,3a(A6); MOVE.L D2,90(A6); MOVE.L D3,94(A6); CLR.W 8a(A6); MOVE.L #5ac84,(A6) (write only); RTS.
    case 0x5ac68:
        if(!ofr5_put(c,r.a[6],0x36,4,r.d[0]) || !ofr5_put(c,r.a[6],0x3a,4,r.d[1]) || !ofr5_put(c,r.a[6],0x90,4,r.d[2]) || !ofr5_put(c,r.a[6],0x94,4,r.d[3]) ||
           !ofr5_put(c,r.a[6],0x8a,2,0) || !ofr5_put(c,r.a[6],0,4,0x5ac84))return false;
        return am_return(c);
    // ---- 5ac84 (installed value): TST.L 36(A6); BMI.W 5ac9e / 5ac8c: CLR.L 36(A6); CLR.L 90(A6); MOVE.L #5aca6,(A6) (write only); BRA.W 5aca6.
    case 0x5ac84:if(!ofr5_get(c,r.a[6],0x36,4,value))return false;r.pc=ofr5_negative(value)?0x5ac9e:0x5ac8c;return true;
    case 0x5ac8c:
        if(!ofr5_put(c,r.a[6],0x36,4,0) || !ofr5_put(c,r.a[6],0x90,4,0) || !ofr5_put(c,r.a[6],0,4,0x5aca6))return false;r.pc=0x5aca6;return true;
    // MOVE.L 90(A6),D0; ADD.L D0,36(A6).
    case 0x5ac9e:
        if(!ofr5_get(c,r.a[6],0x90,4,value))return false;r.d[0]=value;if(!ofr5_get(c,r.a[6],0x36,4,value) || !ofr5_put(c,r.a[6],0x36,4,value+r.d[0]))return false;
        r.pc=0x5aca6;return true;
    case 0x5aca6:return am_call(c,0x4b6f4,0x5acac);                                                   // JSR 4b6f4.l.
    case 0x5acac:return ofr5_carry(c,0x5acb0,0x5ad66);                                                // BCS.W 5ad66 (C of 4b6f4).
    // MOVEA.L c(A6),A0; BTST.B #7,61(A0); BNE.W 5ad66.
    case 0x5acb0:
        if(!ofr5_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr5_get(c,r.a[0],0x61,1,value))return false;
        r.pc=(value&0x80U)!=0U?0x5ad66:0x5acbe;return true;
    // MOVE.W 1e(A6),84(A6); MOVE.L 94(A6),D1; ADD.L D1,3a(A6); MOVE.L 36(A6),D0; MOVE.L 3a(A6),D1; ASR.L #8,D0; ASR.L #8,D1; JSR 4464a.l.
    case 0x5acbe:
        if(!ofr5_get(c,r.a[6],0x1e,2,value) || !ofr5_put(c,r.a[6],0x84,2,value) || !ofr5_get(c,r.a[6],0x94,4,value))return false;r.d[1]=value;
        if(!ofr5_get(c,r.a[6],0x3a,4,value) || !ofr5_put(c,r.a[6],0x3a,4,value+r.d[1]) || !ofr5_get(c,r.a[6],0x36,4,value))return false;r.d[0]=value;
        if(!ofr5_get(c,r.a[6],0x3a,4,value))return false;r.d[1]=value;r.d[0]=ofr5_asr8(r.d[0]);r.d[1]=ofr5_asr8(r.d[1]);
        return am_call(c,0x4464a,0x5acde);
    // ADD.W D0,8a(A6); JSR 43ea4.l.
    case 0x5acde:if(!ofr5_get(c,r.a[6],0x8a,2,value) || !ofr5_put(c,r.a[6],0x8a,2,value+r.d[0]))return false;return am_call(c,0x43ea4,0x5ace8);
    // MOVEQ #0,D0; MOVEA.L c(A6),A0; MOVE.W 86(A0),D0; SWAP D0; MOVE.L 32(A6),D1; CMP.L D1,D0; BLE.W 5ad0c (signed).
    case 0x5ace8:
        r.d[0]=0;if(!ofr5_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr5_get(c,r.a[0],0x86,2,value))return false;am_word(r.d[0],value);
        am_swap(r.d[0]);if(!ofr5_get(c,r.a[6],0x32,4,value))return false;r.d[1]=value;r.pc=ofr5_le_long(r.d[0],r.d[1])?0x5ad0c:0x5acfe;return true;
    // CLR.L 3a(A6); MOVE.L D0,32(A6); MOVE.L #5ad66,(A6) (write only).
    case 0x5acfe:
        if(!ofr5_put(c,r.a[6],0x3a,4,0) || !ofr5_put(c,r.a[6],0x32,4,r.d[0]) || !ofr5_put(c,r.a[6],0,4,0x5ad66))return false;r.pc=0x5ad0c;return true;
    case 0x5ad0c:return am_call(c,0x49fc6,0x5ad12);                                                   // JSR 49fc6.l (its C is not read).
    // CMPI.W #1200,8a(A6); BLT.W 5ad40 (signed).
    case 0x5ad12:if(!ofr5_get(c,r.a[6],0x8a,2,value))return false;r.pc=ofr5_sw(value)<0x1200?0x5ad40:0x5ad1c;return true;
    // SUBI.W #1200,8a(A6); MOVEA.L #5ad98,A0; MOVE.W #1e,D0; JSR 28ae.l (its C is not read).
    case 0x5ad1c:
        if(!ofr5_get(c,r.a[6],0x8a,2,value) || !ofr5_put(c,r.a[6],0x8a,2,value-0x1200U))return false;r.a[0]=0x5ad98;am_word(r.d[0],0x1e);
        return am_call(c,0x28ae,0x5ad32);
    case 0x5ad32:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x49214,0x5ad40);               // MOVE.W #0,D0; MOVE.W #0,D1; JSR 49214.l.
    case 0x5ad40:r.a[0]=0x5dc22;return am_call(c,0x4ae4a,0x5ad4c);                                    // LEA 5dc22.l,A0; JSR 4ae4a.l.
    case 0x5ad4c:r.pc=ofr5_w(r.d[0])!=0U?0x5ad66:0x5ad54;return true;                                // CMPI.W #0,D0; BNE.W 5ad66.
    case 0x5ad54:case 0x5adf6:r.a[0]=0x5dc1a;return am_call(c,0x1ab80,r.pc+12U);                     // LEA 5dc1a.l,A0; JSR 1ab80.l.
    case 0x5ad60:return ofr5_carry(c,0x5ad64,0x5ad92);                                                // BCS.W 5ad92 (C of 1ab80).
    case 0x5ad66:am_word(r.d[0],0x1a21);return am_call(c,0x3af8,0x5ad70);                            // MOVE.W #1a21,D0; JSR 3af8.l.
    case 0x5ad70:r.a[0]=0xd1d08;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0x5ad80);               // MOVEA.L #d1d08,A0; MOVE.W #1e,D0; JSR 28ae.l.
    case 0x5ad80:return ofr5_carry(c,0x5ad92,0x5ad84);                                                // BCC.W 5ad92 (C of 28ae).
    case 0x5ad84:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0x5ad8e);               // CLR.W D0; CLR.W D1; JSR 4970a.l.
    case 0x5ad8e:r.carry=AnimationCarrySet;r.pc=0x5ad92;return true;                                  // ORI.B #1,CCR (no reader).
    // ---- 5ad98 child: CLR.L 36(A6); CLR.L 3a(A6); MOVE.L #5add8,(A6) (the next PC: enter it).
    case 0x5adca:
        if(!ofr5_put(c,r.a[6],0x36,4,0) || !ofr5_put(c,r.a[6],0x3a,4,0) || !ofr5_put(c,r.a[6],0,4,0x5add8))return false;r.pc=0x5add8;return true;
    // MOVEA.L c(A6),A0; SUBQ.W #1,84(A0); MOVE.W 84(A0),1e(A6); JSR 43e34.l.
    case 0x5add8:
        if(!ofr5_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ofr5_get(c,r.a[0],0x84,2,value) || !ofr5_put(c,r.a[0],0x84,2,value-1U) || !ofr5_get(c,r.a[0],0x84,2,value) ||
           !ofr5_put(c,r.a[6],0x1e,2,value))return false;
        return am_call(c,0x43e34,0x5adec);
    case 0x5adec:return am_call(c,0x49fc6,0x5adf2);                                                   // JSR 49fc6.l.
    case 0x5adf2:return ofr5_carry(c,0x5adf6,0x5ae08);                                                // BCS.W 5ae08 (C of 49fc6).
    case 0x5ae02:return ofr5_carry(c,0x5ae06,0x5ae08);                                                // BCS.W 5ae08 (C of 1ab80).
    // ---- 5ae10 (64-bit unsigned product D1:D0 := D0 x D1): MOVE.W D1,D2; MULU.W D0,D2; MOVE.L D2,-(A7); CLR.L -(A7); MOVE.L D0,D2; SWAP D2;
    // MULU.W D1,D2; ADD.L D2,2(A7); BCC.B 5ae26 / 5ae24: ADDQ.W #1,(A7).
    case 0x5ae10:
        am_word(r.d[2],r.d[1]);r.d[2]=ofr5_mulu(r.d[2],r.d[0]);if(!am_push(c,4,r.d[2]) || !am_push(c,4,0))return false;
        r.d[2]=r.d[0];am_swap(r.d[2]);r.d[2]=ofr5_mulu(r.d[2],r.d[1]);if(!ofr5_add_middle(c,r.d[2],carry))return false;
        r.pc=carry?0x5ae24:0x5ae26;return true;
    case 0x5ae24:case 0x5ae32:
        if(!ofr5_get(c,r.a[7],0,2,value) || !ofr5_put(c,r.a[7],0,2,value+1U))return false;r.pc=r.pc+2U;return true;
    // SWAP D1; MOVE.L D0,D2; MULU.W D1,D2; ADD.L D2,2(A7); BCC.B 5ae34 / 5ae32.
    case 0x5ae26:am_swap(r.d[1]);r.d[2]=ofr5_mulu(r.d[0],r.d[1]);if(!ofr5_add_middle(c,r.d[2],carry))return false;r.pc=carry?0x5ae32:0x5ae34;return true;
    // SWAP D0; MULU.W D0,D1; ADD.L (A7)+,D1; MOVE.L (A7)+,D0; RTS.
    case 0x5ae34:
        am_swap(r.d[0]);r.d[1]=ofr5_mulu(r.d[1],r.d[0]);if(!am_pop(c,4,value))return false;r.d[1]=r.d[1]+value;if(!am_pop(c,4,value))return false;
        r.d[0]=value;return am_return(c);
    case 0x5ae54:return am_call(c,0x5ae10,0x5ae56);                                                   // BSR.B 5ae10.
    case 0x5ae56:r.pc=ofr5_negative(r.d[1])?0x5ae0e:0x5ae5a;return true;                             // TST.L D1; BMI.B 5ae0e (TRAP #15, decision 2).
    case 0x5ae5a:r.pc=ofr5_b(r.d[7])==0U?0x5ae64:0x5ae60;return true;                                // TST.B D7; BEQ.W 5ae64.
    case 0x5aed0:r.pc=ofr5_b(r.d[7])==0U?0x5aed8:0x5aed6;return true;                                // TST.B D7; BEQ.W 5aed8.
    // NEG.L D0 (X := D0 != 0); NEGX.L D1.
    case 0x5ae60:{const std::uint32_t x=r.d[0]!=0U?1U:0U;r.d[0]=0U-r.d[0];r.d[1]=0U-r.d[1]-x;r.pc=0x5ae64;return true;}
    // ---- 5ae66 (fixed-point multiply): MOVEQ #0,D7; MOVEQ #1,D3; SWAP D3; TST.L D0; BPL.W 5ae76 / 5ae72: NEG.L D0; NOT.B D7.
    case 0x5ae66:r.d[7]=0;r.d[3]=0x10000U;r.pc=ofr5_negative(r.d[0])?0x5ae72:0x5ae76;return true;
    case 0x5ae72:case 0x5b200:r.d[0]=0U-r.d[0];am_byte(r.d[7],~r.d[7]);r.pc=r.pc+4U;return true;
    case 0x5ae76:r.pc=ofr5_negative(r.d[1])?0x5ae7c:0x5ae80;return true;                             // TST.L D1; BPL.W 5ae80.
    case 0x5ae7c:case 0x5b20a:r.d[1]=0U-r.d[1];am_byte(r.d[7],~r.d[7]);r.pc=r.pc+4U;return true;     // NEG.L D1; NOT.B D7.
    case 0x5ae80:r.pc=r.d[0]>=r.d[3]?0x5ae90:0x5ae86;return true;                                    // CMP.L D3,D0; BCC.W 5ae90 (unsigned).
    case 0x5ae86:r.pc=r.d[1]>=r.d[3]?0x5ae90:0x5ae8c;return true;                                    // CMP.L D3,D1; BCC.W 5ae90.
    case 0x5ae8c:r.pc=0x5aebe;return true;                                                             // BRA.W 5aebe.
    case 0x5ae90:return am_call(c,0x5ae54,0x5ae92);                                                   // BSR.B 5ae54.
    case 0x5ae92:am_word(r.d[0],r.d[1]);am_swap(r.d[0]);return am_return(c);                          // MOVE.W D1,D0; SWAP D0; RTS.
    case 0x5aebe:r.pc=r.d[1]==r.d[3]?0x5aed0:0x5aec4;return true;                                    // CMP.L D3,D1; BEQ.W 5aed0.
    case 0x5aec4:r.pc=r.d[0]==r.d[3]?0x5aeda:0x5aeca;return true;                                    // CMP.L D3,D0; BEQ.W 5aeda.
    case 0x5aeca:r.d[0]=ofr5_mulu(r.d[0],r.d[1]);am_word(r.d[0],0);am_swap(r.d[0]);r.pc=0x5aed0;return true;   // MULU.W D1,D0; SUB.W D0,D0; SWAP D0.
    case 0x5aed6:case 0x5b21c:r.d[0]=0U-r.d[0];r.pc=r.pc+2U;return true;                               // NEG.L D0.
    case 0x5aeda:r.d[0]=r.d[1];r.pc=0x5aed0;return true;                                              // MOVE.L D1,D0; BRA.B 5aed0.
    // ---- 5aede (unsigned 16.16 divide): TST.L D0; BEQ.W 5b1f6 / TST.L D1; BEQ.W 5ae0e (TRAP #15, decision 2).
    case 0x5aede:r.pc=r.d[0]==0U?0x5b1f6:0x5aee4;return true;
    case 0x5aee4:r.pc=r.d[1]==0U?0x5ae0e:0x5aeea;return true;
    // MOVE.L D1,D2; MOVE.L D0,D1; SWAP D0; CLR.W D0; SWAP D1; MOVEQ #0,D3; the first step.
    case 0x5aeea:r.d[2]=r.d[1];r.d[1]=r.d[0];am_swap(r.d[0]);am_word(r.d[0],0);am_swap(r.d[1]);r.d[3]=0;ofr5_divide_step(r,0x5af06,0x5af02);return true;
    // The 47 further steps (5af06 + 16 k): the step; its BCS.W goes to the next step (the last one to 5b1f6), the fall-through to pc + 12.
    case 0x5af06:case 0x5af16:case 0x5af26:case 0x5af36:case 0x5af46:case 0x5af56:case 0x5af66:case 0x5af76:case 0x5af86:case 0x5af96:case 0x5afa6:
    case 0x5afb6:case 0x5afc6:case 0x5afd6:case 0x5afe6:case 0x5aff6:case 0x5b006:case 0x5b016:case 0x5b026:case 0x5b036:case 0x5b046:case 0x5b056:
    case 0x5b066:case 0x5b076:case 0x5b086:case 0x5b096:case 0x5b0a6:case 0x5b0b6:case 0x5b0c6:case 0x5b0d6:case 0x5b0e6:case 0x5b0f6:case 0x5b106:
    case 0x5b116:case 0x5b126:case 0x5b136:case 0x5b146:case 0x5b156:case 0x5b166:case 0x5b176:case 0x5b186:case 0x5b196:case 0x5b1a6:case 0x5b1b6:
    case 0x5b1c6:case 0x5b1d6:case 0x5b1e6:
        ofr5_divide_step(r,r.pc+16U,r.pc+12U);return true;
    // The 48 subtract blocks (5af02 + 16 k): ADDQ.W #1,D0 (WORD); SUB.L D2,D3; fall through to the next step (the last one to 5b1f6).
    case 0x5af02:case 0x5af12:case 0x5af22:case 0x5af32:case 0x5af42:case 0x5af52:case 0x5af62:case 0x5af72:case 0x5af82:case 0x5af92:case 0x5afa2:
    case 0x5afb2:case 0x5afc2:case 0x5afd2:case 0x5afe2:case 0x5aff2:case 0x5b002:case 0x5b012:case 0x5b022:case 0x5b032:case 0x5b042:case 0x5b052:
    case 0x5b062:case 0x5b072:case 0x5b082:case 0x5b092:case 0x5b0a2:case 0x5b0b2:case 0x5b0c2:case 0x5b0d2:case 0x5b0e2:case 0x5b0f2:case 0x5b102:
    case 0x5b112:case 0x5b122:case 0x5b132:case 0x5b142:case 0x5b152:case 0x5b162:case 0x5b172:case 0x5b182:case 0x5b192:case 0x5b1a2:case 0x5b1b2:
    case 0x5b1c2:case 0x5b1d2:case 0x5b1e2:case 0x5b1f2:
        am_word(r.d[0],r.d[0]+1U);r.d[3]=r.d[3]-r.d[2];r.pc=r.pc+4U;return true;
    // ---- 5b1f8 (signed fixed-point divide): MOVEQ #0,D7; TST.L D0; BPL.W 5b204 / 5b200: NEG.L D0; NOT.B D7.
    case 0x5b1f8:r.d[7]=0;r.pc=ofr5_negative(r.d[0])?0x5b200:0x5b204;return true;
    case 0x5b204:r.pc=ofr5_negative(r.d[1])?0x5b20a:0x5b20e;return true;                             // TST.L D1; BPL.W 5b20e.
    case 0x5b20e:if(!am_push(c,2,ofr5_w(r.d[7])))return false;return am_call(c,0x5aede,0x5b214);    // MOVE.W D7,-(A7); BSR.W 5aede.
    // MOVE.W (A7)+,D7 (WORD, the upper WORD stays); TST.B D7; BEQ.W 5b21e / 5b21c: NEG.L D0.
    case 0x5b214:if(!am_pop(c,2,value))return false;am_word(r.d[7],value);r.pc=ofr5_b(r.d[7])==0U?0x5b21e:0x5b21c;return true;
    default:return am_error(c,"unsupported animation objects fr5 PC");
    }
}
}
