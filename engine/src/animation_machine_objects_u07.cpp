#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Work RAM operands of the original code (U07 reads no ROM or bank window data).
const std::uint32_t OU7_SLOT0=0x1009a8;   // 4e18c LEA 1009a8.L,A0 (D0.W = 0)
const std::uint32_t OU7_SLOT1=0x100a6c;   // 4e196 LEA 100a6c.L,A0 (D0.W != 0)
const std::uint32_t OU7_LEFT=0x10de14;    // e58fc LEA 10de14.L,A0
const std::uint32_t OU7_RIGHT=0x10de1c;   // e58fc LEA 10de1c.L,A1
const std::uint32_t OU7_MOTION0=0x10b1d6; // e59a0 LEA 10b1d6.L,A1
const std::uint32_t OU7_MOTION1=0x10d256; // e59a0 LEA 10d256.L,A1
bool ou7_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou7_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Two's complement views (explicit, no implementation-defined conversion).
std::int32_t ou7_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
long long ou7_signed_long(std::uint32_t value) {
    return (value&0x80000000U)?static_cast<long long>(value)-4294967296LL:static_cast<long long>(value);
}
// ASR.L #n,Dn (1 <= n <= 8): arithmetic shift keeping the sign bit.
std::uint32_t ou7_asr_long(std::uint32_t value,unsigned int n) {
    return (value&0x80000000U)?((value>>n)|~(0xffffffffU>>n)):(value>>n);
}
// CMPI.W #limit,d16(A6) followed by BGT (greater) or BLT (less): taken_pc when the signed WORD compare holds, else next_pc.
bool ou7_word_test(AnimationMachineContext& c,std::uint32_t displacement,std::int32_t limit,bool greater,std::uint32_t taken_pc,
    std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ou7_get(c,c.s.a[6],displacement,2,value))return false;
    const std::int32_t v=ou7_signed_word(value);c.s.pc=(greater?v>limit:v<limit)?taken_pc:next_pc;return true;
}
// d16(A6) LONG read-modify-write by addend (ADD.L Dn / ADDI.L / SUB.L Dn / SUBI.L).
bool ou7_add_long(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t addend) {
    std::uint32_t value=0;if(!ou7_get(c,c.s.a[6],displacement,4,value))return false;
    return ou7_put(c,c.s.a[6],displacement,4,(value+addend)&0xffffffffU);
}
// MOVEA.L #callback,A0; MOVE.W #priority,D0; JSR 28ae.L (fade_card object creation).
bool ou7_spawn(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t return_pc) {
    c.s.a[0]=callback;am_word(c.s.d[0],0xa);return am_call(c,0x28ae,return_pc);
}
// MOVE.W d16(A6),8c(A0) (WORD copy into the node returned by 28ae).
bool ou7_copy(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t value=0;if(!ou7_get(c,c.s.a[6],displacement,2,value))return false;return ou7_put(c,c.s.a[0],0x8c,2,value);
}
// MOVEQ #0,D0; JSR 49a58.L (stage area RNG).
bool ou7_random(AnimationMachineContext& c,std::uint32_t return_pc) {c.s.d[0]=0;return am_call(c,0x49a58,return_pc);}
// MOVE.L 3a(A6),D0; ASR.L #2,D0; SUB.L D0,3a(A6).
bool ou7_damp_y(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!ou7_get(c,r.a[6],0x3a,4,value))return false;
    r.d[0]=ou7_asr_long(value,2);return ou7_add_long(c,0x3a,(0U-r.d[0])&0xffffffffU);
}
}
// Objects F4 U07 (85 block starts): the lookup 4e186 (node 1009a8/100a6c chosen by D0.W; readiness 289e returns C, consumed by the
// BCC 4e1a2; D1 = 1/0 with D2.B = BYTE 98 when BYTE 9c is 2/1, else D1 = -1 and D2 = 0), the creator callback e585c (2986 child e5878,
// then the fade_card JMP 2a00), and the object callback e5878 (U01 48296, sound 3af8, three 28ae children, two 4e186 lookups that pick
// the 28ae children e5d86/e5d72, the e59a0 motion records and RNG 49a58, then the installed callback e59f6: U04 43ea4 and the state
// machine 7a(A6) = 0..3 with RNG velocities, damping and the 48256 boundary when 2e(A6) >= 140). The returned C of 4e186 stays Unknown
// (every caller sets its own flags); the only C consumer is 4e1a2. U07 reads only work RAM and writes no port.
bool animation_objects_u07_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- 4e186: TST.W D0; BNE 4e196.
    case 0x4e186:r.pc=(r.d[0]&65535U)?0x4e196:0x4e18c;return true;
    case 0x4e18c:r.a[0]=OU7_SLOT0;r.pc=0x4e19c;return true;          // LEA 1009a8.L,A0; BRA 4e19c.
    case 0x4e196:r.a[0]=OU7_SLOT1;r.pc=0x4e19c;return true;          // LEA 100a6c.L,A0.
    case 0x4e19c:return am_call(c,0x289e,0x4e1a2);                    // JSR 289e.L.
    // BCC 4e1be (C returned by 289e: Clear when the callback LONG is 270e).
    case 0x4e1a2:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u07 caller requires known carry");
        r.pc=r.carry==AnimationCarryClear?0x4e1be:0x4e1a6;return true;
    // MOVE.B 9c(A0),D7; MOVEQ #1,D1; CMPI.B #2,D7; BEQ 4e1c4.
    case 0x4e1a6:
        if(!ou7_get(c,r.a[0],0x9c,1,value))return false;am_byte(r.d[7],value);r.d[1]=1;
        r.pc=(r.d[7]&255U)==2U?0x4e1c4:0x4e1b4;return true;
    case 0x4e1b4:r.d[1]=0;r.pc=(r.d[7]&255U)==1U?0x4e1c4:0x4e1be;return true; // MOVEQ #0,D1; CMPI.B #1,D7; BEQ 4e1c4.
    case 0x4e1be:r.d[2]=0;r.d[1]=0xffffffffU;return am_return(c);     // MOVEQ #0,D2; MOVEQ #-1,D1; RTS.
    // MOVEQ #0,D2; MOVE.B 98(A0),D2; RTS.
    case 0x4e1c4:r.d[2]=0;if(!ou7_get(c,r.a[0],0x98,1,value))return false;am_byte(r.d[2],value);return am_return(c);

    // ---- e585c (callback): MOVEA.L #e5878,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.L.
    case 0xe585c:r.a[0]=0xe5878;am_word(r.d[0],0x14);r.a[1]=0x100bf4;return am_call(c,0x2986,0xe5872);
    case 0xe5872:r.pc=0x2a00;return true;                             // JMP 2a00.L.

    // ---- e5878 (callback): JSR 48296.L.
    case 0xe5878:return am_call(c,0x48296,0xe587e);
    case 0xe587e:am_word(r.d[0],0x738);return am_call(c,0x3af8,0xe5888); // MOVE.W #738,D0; JSR 3af8.L.
    case 0xe5888:return ou7_spawn(c,0xe5ea0,0xe5898);
    case 0xe5898:return ou7_spawn(c,0xe5bb0,0xe58a8);
    case 0xe58a8:return ou7_spawn(c,0xe5c74,0xe58b8);
    // MOVE.W #ffff,8e(A6); MOVE.W #ffff,90(A6); MOVEQ #0,D0; JSR 4e186.L.
    case 0xe58b8:
        if(!ou7_put(c,r.a[6],0x8e,2,0xffff) || !ou7_put(c,r.a[6],0x90,2,0xffff))return false;
        r.d[0]=0;return am_call(c,0x4e186,0xe58cc);
    case 0xe58cc:r.pc=(r.d[1]&65535U)==1U?0xe58d4:0xe58d8;return true; // CMPI.W #1,D1; BNE e58d8.
    case 0xe58d4:if(!ou7_put(c,r.a[6],0x8e,2,r.d[2]&65535U))return false;r.pc=0xe58d8;return true; // MOVE.W D2,8e(A6).
    case 0xe58d8:r.d[0]=1;return am_call(c,0x4e186,0xe58e0);          // MOVEQ #1,D0; JSR 4e186.L.
    case 0xe58e0:r.pc=(r.d[1]&65535U)==1U?0xe58e8:0xe58ec;return true; // CMPI.W #1,D1; BNE e58ec.
    case 0xe58e8:if(!ou7_put(c,r.a[6],0x90,2,r.d[2]&65535U))return false;r.pc=0xe58ec;return true; // MOVE.W D2,90(A6).
    case 0xe58ec:if(!ou7_get(c,r.a[6],0x8e,2,value))return false;r.pc=(value&0x8000U)?0xe598a:0xe58f4;return true; // TST.W; BMI.
    case 0xe58f4:if(!ou7_get(c,r.a[6],0x90,2,value))return false;r.pc=(value&0x8000U)?0xe5970:0xe58fc;return true; // TST.W; BMI.
    // LEA 10de14.L,A0; LEA 10de1c.L,A1; MOVE.L (A0),D0; CMP.L (A1),D0; BLT e5940 (signed LONG).
    case 0xe58fc:
        r.a[0]=OU7_LEFT;r.a[1]=OU7_RIGHT;if(!am_read(c,r.a[0],4,value))return false;r.d[0]=value;
        if(!am_read(c,r.a[1],4,other))return false;
        r.pc=ou7_signed_long(value)<ou7_signed_long(other)?0xe5940:0xe5910;return true;
    case 0xe5910:return ou7_spawn(c,0xe5d86,0xe5920);
    case 0xe5920:if(!ou7_copy(c,0x8e))return false;return ou7_spawn(c,0xe5d72,0xe5936); // MOVE.W 8e(A6),8c(A0); ... JSR 28ae.L.
    case 0xe5936:if(!ou7_copy(c,0x90))return false;r.pc=0xe596c;return true;           // MOVE.W 90(A6),8c(A0); BRA e596c.
    case 0xe5940:return ou7_spawn(c,0xe5d72,0xe5950);
    case 0xe5950:if(!ou7_copy(c,0x8e))return false;return ou7_spawn(c,0xe5d86,0xe5966);
    case 0xe5966:if(!ou7_copy(c,0x90))return false;r.pc=0xe596c;return true;
    case 0xe596c:r.pc=0xe5986;return true;                            // BRA e5986.
    case 0xe5970:return ou7_spawn(c,0xe5d72,0xe5980);
    case 0xe5980:if(!ou7_copy(c,0x8e))return false;r.pc=0xe5986;return true;
    case 0xe5986:r.pc=0xe59a0;return true;                            // BRA e59a0.
    case 0xe598a:return ou7_spawn(c,0xe5d72,0xe599a);
    case 0xe599a:if(!ou7_copy(c,0x90))return false;r.pc=0xe59a0;return true;
    // LEA 10b1d6.L,A1; MOVE.L #fffa0000,8(A1); MOVE.L #0,c(A1); LEA 10d256.L,A1; MOVE.L #fffe8000,8(A1); MOVE.L #0,c(A1);
    // JSR 49a58.L.
    case 0xe59a0:
        r.a[1]=OU7_MOTION0;if(!ou7_put(c,r.a[1],8,4,0xfffa0000U) || !ou7_put(c,r.a[1],0xc,4,0))return false;
        r.a[1]=OU7_MOTION1;if(!ou7_put(c,r.a[1],8,4,0xfffe8000U) || !ou7_put(c,r.a[1],0xc,4,0))return false;
        return am_call(c,0x49a58,0xe59d2);
    // ANDI.W #7f,D0; MOVE.W D0,78(A6); MOVE.W #ffe0,2e(A6); MOVE.W #140,32(A6); CLR.B 63(A6); MOVE.W #168,7c(A6);
    // MOVE.L #e59f6,(A6) (then the callback e59f6).
    case 0xe59d2:
        am_word(r.d[0],r.d[0]&0x7fU);
        if(!ou7_put(c,r.a[6],0x78,2,r.d[0]&65535U) || !ou7_put(c,r.a[6],0x2e,2,0xffe0) || !ou7_put(c,r.a[6],0x32,2,0x140) ||
           !ou7_put(c,r.a[6],0x63,1,0) || !ou7_put(c,r.a[6],0x7c,2,0x168) || !am_write(c,r.a[6],4,0xe59f6))return false;
        r.pc=0xe59f6;return true;
    // MOVE.B #0,62(A6); JSR 43ea4.L (callback entry).
    case 0xe59f6:if(!ou7_put(c,r.a[6],0x62,1,0))return false;return am_call(c,0x43ea4,0xe5a02);
    case 0xe5a02:if(!ou7_get(c,r.a[6],0x63,1,value))return false;r.pc=(value&255U)?0xe5a0a:0xe5a1e;return true; // TST.B 63(A6); BEQ.
    case 0xe5a0a:am_word(r.d[0],0x738);return am_call(c,0x3af8,0xe5a14); // MOVE.W #738,D0; JSR 3af8.L.
    case 0xe5a14:if(!ou7_put(c,r.a[6],0x7a,2,2) || !ou7_put(c,r.a[6],0x63,1,0))return false;r.pc=0xe5a1e;return true;
    // MOVE.W 7a(A6),D0; BNE e5a7c.
    case 0xe5a1e:if(!ou7_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)?0xe5a7c:0xe5a26;return true;
    // CMPI.L #20000,36(A6); BGE e5a3a (signed LONG).
    case 0xe5a26:if(!ou7_get(c,r.a[6],0x36,4,value))return false;r.pc=ou7_signed_long(value)>=0x20000LL?0xe5a3a:0xe5a32;return true;
    case 0xe5a32:if(!ou7_add_long(c,0x36,0x8000))return false;r.pc=0xe5a3a;return true; // ADDI.L #8000,36(A6).
    case 0xe5a3a:return ou7_word_test(c,0x2e,0xa0,false,0xe5a7a,0xe5a44); // CMPI.W #a0,2e(A6); BLT e5a7a.
    case 0xe5a44:return ou7_random(c,0xe5a4c);
    // ADDI.L #10000,D0; NEG.L D0; MOVE.L D0,36(A6); MOVEQ #0,D0; JSR 49a58.L.
    case 0xe5a4c:
        r.d[0]=(0U-((r.d[0]+0x10000U)&0xffffffffU))&0xffffffffU;if(!ou7_put(c,r.a[6],0x36,4,r.d[0]))return false;
        return ou7_random(c,0xe5a60);
    // SUBI.L #8000,D0; MOVE.L D0,3a(A6); MOVE.W #1,7a(A6); MOVE.W #19e0,D0; JSR 3af8.L.
    case 0xe5a60:
        r.d[0]=(r.d[0]-0x8000U)&0xffffffffU;if(!ou7_put(c,r.a[6],0x3a,4,r.d[0]) || !ou7_put(c,r.a[6],0x7a,2,1))return false;
        am_word(r.d[0],0x19e0);return am_call(c,0x3af8,0xe5a7a);
    case 0xe5a7a:case 0xe5af8:case 0xe5b48:case 0xe5bac:case 0xe5bae:return am_return(c); // RTS.
    case 0xe5a7c:r.pc=(r.d[0]&65535U)==1U?0xe5a84:0xe5afa;return true; // CMPI.W #1,D0; BNE e5afa.
    case 0xe5a84:return ou7_word_test(c,0x32,0x130,true,0xe5aa0,0xe5a8e); // CMPI.W #130,32(A6); BGT e5aa0.
    case 0xe5a8e:return ou7_random(c,0xe5a96);
    case 0xe5a96:r.d[0]=(r.d[0]+0x4000U)&0xffffffffU;if(!ou7_put(c,r.a[6],0x3a,4,r.d[0]))return false;r.pc=0xe5aa0;return true;
    case 0xe5aa0:return ou7_word_test(c,0x32,0x160,false,0xe5abe,0xe5aaa); // CMPI.W #160,32(A6); BLT e5abe.
    case 0xe5aaa:return ou7_random(c,0xe5ab2);
    // ADDI.L #4000,D0; NEG.L D0; MOVE.L D0,3a(A6).
    case 0xe5ab2:
        r.d[0]=(0U-((r.d[0]+0x4000U)&0xffffffffU))&0xffffffffU;if(!ou7_put(c,r.a[6],0x3a,4,r.d[0]))return false;r.pc=0xe5abe;return true;
    case 0xe5abe:return ou7_word_test(c,0x2e,0x30,true,0xe5ada,0xe5ac8); // CMPI.W #30,2e(A6); BGT e5ada.
    case 0xe5ac8:return ou7_random(c,0xe5ad0);
    case 0xe5ad0:r.d[0]=(r.d[0]+0x10000U)&0xffffffffU;if(!ou7_put(c,r.a[6],0x36,4,r.d[0]))return false;r.pc=0xe5ada;return true;
    case 0xe5ada:return ou7_word_test(c,0x2e,0x110,false,0xe5af8,0xe5ae4); // CMPI.W #110,2e(A6); BLT e5af8.
    case 0xe5ae4:return ou7_random(c,0xe5aec);
    // ADDI.L #10000,D0; NEG.L D0; MOVE.L D0,36(A6).
    case 0xe5aec:
        r.d[0]=(0U-((r.d[0]+0x10000U)&0xffffffffU))&0xffffffffU;if(!ou7_put(c,r.a[6],0x36,4,r.d[0]))return false;r.pc=0xe5af8;return true;
    case 0xe5afa:r.pc=(r.d[0]&65535U)==2U?0xe5b02:0xe5b4a;return true; // CMPI.W #2,D0; BNE e5b4a.
    // MOVE.L 3a(A6),D0; ASR.L #2,D0; SUB.L D0,3a(A6); MOVE.L 36(A6),D0; BPL e5b30.
    case 0xe5b02:
        if(!ou7_damp_y(c) || !ou7_get(c,r.a[6],0x36,4,value))return false;r.d[0]=value;
        r.pc=(value&0x80000000U)?0xe5b14:0xe5b30;return true;
    // CMPI.L #fffe0000,D0; BLE e5b2c (signed LONG).
    case 0xe5b14:r.pc=ou7_signed_long(r.d[0])<=-0x20000LL?0xe5b2c:0xe5b1e;return true;
    // ASR.L #2,D0; ADD.L D0,36(A6); SUBI.L #1000,36(A6).
    case 0xe5b1e:
        r.d[0]=ou7_asr_long(r.d[0],2);if(!ou7_add_long(c,0x36,r.d[0]) || !ou7_add_long(c,0x36,(0U-0x1000U)&0xffffffffU))return false;
        r.pc=0xe5b2c;return true;
    case 0xe5b2c:r.pc=0xe5b36;return true;                            // BRA e5b36.
    case 0xe5b30:if(!ou7_put(c,r.a[6],0x7a,2,3))return false;r.pc=0xe5b36;return true; // MOVE.W #3,7a(A6).
    case 0xe5b36:return ou7_word_test(c,0x2e,0x30,true,0xe5b48,0xe5b40); // CMPI.W #30,2e(A6); BGT e5b48.
    case 0xe5b40:if(!ou7_put(c,r.a[6],0x36,4,0))return false;r.pc=0xe5b48;return true; // MOVE.L #0,36(A6).
    case 0xe5b4a:r.pc=(r.d[0]&65535U)==3U?0xe5b52:0xe5bae;return true; // CMPI.W #3,D0; BNE e5bae.
    // MOVE.L 3a(A6),D0; ASR.L #2,D0; SUB.L D0,3a(A6); CMPI.W #130,32(A6); BGT e5b6e.
    case 0xe5b52:if(!ou7_damp_y(c))return false;return ou7_word_test(c,0x32,0x130,true,0xe5b6e,0xe5b66);
    case 0xe5b66:if(!ou7_put(c,r.a[6],0x3a,4,0))return false;r.pc=0xe5b6e;return true; // MOVE.L #0,3a(A6).
    case 0xe5b6e:return ou7_word_test(c,0x32,0x160,false,0xe5b80,0xe5b78); // CMPI.W #160,32(A6); BLT e5b80.
    case 0xe5b78:if(!ou7_put(c,r.a[6],0x3a,4,0))return false;r.pc=0xe5b80;return true; // MOVE.L #0,3a(A6).
    // MOVE.L 36(A6),D0; CMPI.L #40000,D0; BGE e5b9c (signed LONG).
    case 0xe5b80:
        if(!ou7_get(c,r.a[6],0x36,4,value))return false;r.d[0]=value;
        r.pc=ou7_signed_long(value)>=0x40000LL?0xe5b9c:0xe5b8e;return true;
    // ASR.L #3,D0; ADD.L D0,36(A6); ADDI.L #4000,36(A6).
    case 0xe5b8e:
        r.d[0]=ou7_asr_long(r.d[0],3);if(!ou7_add_long(c,0x36,r.d[0]) || !ou7_add_long(c,0x36,0x4000))return false;
        r.pc=0xe5b9c;return true;
    case 0xe5b9c:return ou7_word_test(c,0x2e,0x140,false,0xe5bac,0xe5ba6); // CMPI.W #140,2e(A6); BLT e5bac.
    case 0xe5ba6:return am_call(c,0x48256,0xe5bac);                   // JSR 48256.L (boundary without an executor).
    default:return am_error(c,"unsupported animation objects u07 PC");
    }
}
}
