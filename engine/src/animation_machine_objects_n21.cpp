#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONGs (live bus, current PVC bank): animation records of the b9d0a / b9d1c children (id 203) and of c3fdc (id ca).
const std::uint32_t ON21_BANK_203=0x2001d0;
const std::uint32_t ON21_BANK_CA=0x200088;
bool on21_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on21_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Two's complement WORD as a signed number (no signed overflow in C++).
int on21_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<int>(value)-65536:static_cast<int>(value);
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on21_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n21 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,(A6) then continue at next_pc.
bool on21_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// CMP.W 5418(A5),D0 (unsigned): true when D0.W > A5 WORD 5418 (BHI), with the read value for BCC.
bool on21_progress(AnimationMachineContext& c,std::uint32_t& progress) {
    return am_read(c,am_index(c.s.a[5],0x5418),2,progress);
}
}
// Objects F4 N21 (44 block starts): the installed callback b9c0e (installed by N20 b9c00, moved out of N20), the 28ae children
// b9d0a / b9d1c with the installed b9d7a, and the stage event callback c3fdc with the installed c404c. Boundary without an executor:
// c41a4 (c4064 BSR). c4068 stores c4084 (outside every unit) in (A6) as data. The three BCC/BCS consumers read the C of 1ab02 (b9c32
// c4078) and 288c (b9d9a). N21 produces no known C, writes no port and changes no bank.
bool animation_objects_n21_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- b9c0e (installed): JSR ba2d6(PC); JSR 43ea4.L; JSR 49fc6.L.
    case 0xb9c0e:return am_call(c,0xba2d6,0xb9c12);
    case 0xb9c12:return am_call(c,0x43ea4,0xb9c18);
    case 0xb9c18:return am_call(c,0x49fc6,0xb9c1e);
    // MOVE.W 80(A6),D0; BNE.W b9c46.
    case 0xb9c1e:if(!on21_get(c,0x80,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)!=0U?0xb9c46:0xb9c26;return true;
    case 0xb9c26:r.a[0]=0xb982a;return am_call(c,0x1ab02,0xb9c32);     // MOVEA.L #b982a,A0; JSR 1ab02.L.
    case 0xb9c32:return on21_carry(c,0xb9c42,0xb9c36);                  // BCC.W b9c42 (C returned by 1ab02).
    case 0xb9c36:case 0xb9c4e:return am_call(c,0x46ef4,r.pc+6U);        // JSR 46ef4.L.
    case 0xb9c3c:case 0xb9c54:r.pc=0x2a24;return true;                   // JMP 2a24.L.
    case 0xb9c42:r.pc=0xb9c5a;return true;                               // BRA.W b9c5a.
    // CMP.W 5418(A5),D0; BHI.W b9c5a (unsigned D0.W > A5 WORD 5418).
    case 0xb9c46:if(!on21_progress(c,value))return false;r.pc=(r.d[0]&65535U)>(value&65535U)?0xb9c5a:0xb9c4e;return true;
    // MOVEA.L 84(A6),A0; CMPA.W #0,A0 (sign-extended 0: the full LONG); BEQ.W b9c6c.
    case 0xb9c5a:if(!on21_get(c,0x84,4,value))return false;r.a[0]=value;r.pc=value==0U?0xb9c6c:0xb9c66;return true;
    case 0xb9c66:return am_call(c,0x4706c,0xb9c6c);                     // JSR 4706c.L.
    case 0xb9c6c:case 0xb9da4:case 0xc4082:return am_return(c);         // RTS.
    // ---- b9d0a / b9d1c (28ae children): MOVE.W #ffca/#3c,D0; MOVE.W #100,D1; JSR 49290.L; BRA.W b9d2e.
    case 0xb9d0a:am_word(r.d[0],0xffca);am_word(r.d[1],0x100);return am_call(c,0x49290,0xb9d18);
    case 0xb9d1c:am_word(r.d[0],0x3c);am_word(r.d[1],0x100);return am_call(c,0x49290,0xb9d2a);
    case 0xb9d18:case 0xb9d2a:r.pc=0xb9d2e;return true;
    // MOVE.W #800,68(A6); MOVE.W #800,1e(A6); MOVE.W #73,D0; MOVE.W #9,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xb9d2e:
        if(!on21_put(c,0x68,2,0x800) || !on21_put(c,0x1e,2,0x800))return false;am_word(r.d[0],0x73);am_word(r.d[1],9);am_byte(r.d[2],0);
        return am_call(c,0xc6a96,0xb9d4c);
    // LEA 26(A6),A0; MOVE.W #203,20(A6); MOVE.L 2001d0.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 24(A1),A1;
    // JSR 49f8c.L.
    case 0xb9d4c:
        r.a[0]=am_index(r.a[6],0x26);if(!on21_put(c,0x20,2,0x203) || !am_read(c,ON21_BANK_203,4,value) || !on21_put(c,0x22,4,value))return false;
        am_word(r.d[0],0x100);if(!on21_get(c,0x22,4,value))return false;r.a[1]=value;
        if(!am_read(c,am_index(r.a[1],0x24),4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,0xb9d74);
    case 0xb9d74:return on21_install(c,0xb9d7a,0xb9d7a);                // MOVE.L #b9d7a,(A6).
    // ---- b9d7a (installed): JSR 43e34.L; MOVEA.L c(A6),A0; CMPI.W #100,46(A0); BGT.W b9d94 (signed); JSR 49fc6.L; JSR 288c.L.
    case 0xb9d7a:case 0xc404c:return am_call(c,0x43e34,r.pc+6U);
    case 0xb9d80:
        if(!on21_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x46),2,value))return false;
        r.pc=on21_signed_word(value)>0x100?0xb9d94:0xb9d8e;return true;
    case 0xb9d8e:case 0xc4052:return am_call(c,0x49fc6,r.pc+6U);        // JSR 49fc6.L.
    case 0xb9d94:return am_call(c,0x288c,0xb9d9a);
    case 0xb9d9a:return on21_carry(c,0xb9d9e,0xb9da4);                  // BCS.W b9da4 (C returned by 288c).
    case 0xb9d9e:case 0xc407c:r.pc=0x2a00;return true;                   // JMP 2a00.L.
    // ---- c3fdc (stage event callback): MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.W #21,D0; MOVE.W #1f,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xc3fdc:
        if(!on21_put(c,0x68,2,0) || !on21_put(c,0x1e,2,0))return false;am_word(r.d[0],0x21);am_word(r.d[1],0x1f);am_byte(r.d[2],0);
        return am_call(c,0xc6a96,0xc3ffa);
    // MOVE.W 78(A6),D0; BEQ.W c400e / ADDI.W #1e,D0; MOVE.W D0,90(A6); BRA.W c4014 / MOVE.W #25,90(A6).
    case 0xc3ffa:if(!on21_get(c,0x78,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)==0U?0xc400e:0xc4002;return true;
    case 0xc4002:am_word(r.d[0],(r.d[0]+0x1eU)&65535U);if(!on21_put(c,0x90,2,r.d[0]&65535U))return false;r.pc=0xc4014;return true;
    case 0xc400e:if(!on21_put(c,0x90,2,0x25))return false;r.pc=0xc4014;return true;
    // LEA 26(A6),A0; MOVE.W #ca,20(A6); MOVE.L 200088.L,22(A6); LEA 26(A6),A0; MOVE.W 90(A6),D1; ADD.W D1,D1; ADD.W D1,D1;
    // MOVEA.L 200088.L,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0xc4014:
        r.a[0]=am_index(r.a[6],0x26);if(!on21_put(c,0x20,2,0xca) || !am_read(c,ON21_BANK_CA,4,value) || !on21_put(c,0x22,4,value))return false;
        if(!on21_get(c,0x90,2,value))return false;am_word(r.d[1],(value*4U)&65535U);if(!am_read(c,ON21_BANK_CA,4,value))return false;
        r.a[1]=value;if(!am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);
        return am_call(c,0x49f8c,0xc4046);
    case 0xc4046:return on21_install(c,0xc404c,0xc404c);                // MOVE.L #c404c,(A6).
    // ---- c404c (installed): JSR 43e34.L; JSR 49fc6.L; MOVE.W 76(A6),D0; CMP.W 5418(A5),D0; BCC.W c406e (unsigned D0.W >= 5418).
    case 0xc4058:
        if(!on21_get(c,0x76,2,value))return false;am_word(r.d[0],value);if(!on21_progress(c,other))return false;
        r.pc=(value&65535U)>=(other&65535U)?0xc406e:0xc4064;return true;
    case 0xc4064:return am_call(c,0xc41a4,0xc4068);                     // BSR.W c41a4 (boundary without an executor).
    case 0xc4068:return on21_install(c,0xc4084,0xc406e);                // MOVE.L #c4084,(A6) (c4084: data, outside every unit).
    case 0xc406e:r.a[0]=0xc3fd4;return am_call(c,0x1ab02,0xc4078);      // LEA c3fd4(PC),A0; JSR 1ab02.L.
    case 0xc4078:return on21_carry(c,0xc4082,0xc407c);                  // BCC.W c4082 (C returned by 1ab02).
    default:return am_error(c,"unsupported animation objects n21 PC");
    }
}
}
