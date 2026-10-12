#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code.
const std::uint32_t ON10_SPRITES=0xc5854;       // LEA c5854(PC),A0: LONG table indexed by 76(A6) (live bus).
const std::uint32_t ON10_SOUNDS=0xc5880;        // LEA c5880(PC),A0: WORD table indexed by 76(A6) (live bus).
const std::uint32_t ON10_RECT=0xc584c;          // LEA c584c(PC),A0: rectangle read by 1ab02.
bool on10_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on10_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
}
// Objects F4 N10 (old R10; 18 block starts): the node callback c5896 (LONG c5854 + 4 x 76 -> 7c, sound WORD c5880 + 2 x 76 for U02
// 8ebe, 15 bit 0 from 78, U12 4c0ac when 7a = 0) and the installed c58ee (7a = 2: 4be2c or cleanup 43e34 by 15 bit 7, else 43e34;
// sprite 16ea4 with D7 = 7c; U05 1ab02 on the rectangle c584c, JMP 2a00 when C is set). The 76 index is not range-checked by the
// original (WORD arithmetic, sign-extended index). c5932 consumes the C of 1ab02. N10 writes no port and changes no bank.
bool animation_objects_n10_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // LEA c5854(PC),A0; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVE.L (A0,D0.W),7c(A6); LEA c5880(PC),A0; MOVE.W 76(A6),D0;
    // ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xc5896:
        r.a[0]=ON10_SPRITES;if(!on10_get(c,0x76,2,value))return false;am_word(r.d[0],value<<2);
        if(!am_read(c,am_index(r.a[0],r.d[0]&65535U),4,value) || !on10_put(c,0x7c,4,value))return false;
        r.a[0]=ON10_SOUNDS;if(!on10_get(c,0x76,2,value))return false;am_word(r.d[0],value<<1);
        if(!am_read(c,am_index(r.a[0],r.d[0]&65535U),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);
        return am_call(c,0x8ebe,0xc58c0);
    // MOVE.W #0,68(A6); MOVE.W #0,1e(A6); TST.W 78(A6); BEQ.W c58da; BSET.B #0,15(A6).
    case 0xc58c0:
        if(!on10_put(c,0x68,2,0) || !on10_put(c,0x1e,2,0) || !on10_get(c,0x78,2,value))return false;r.pc=value!=0U?0xc58d4:0xc58da;return true;
    case 0xc58d4:if(!on10_get(c,0x15,1,value) || !on10_put(c,0x15,1,value|1U))return false;r.pc=0xc58da;return true;
    // TST.W 7a(A6); BNE.W c58e8; JSR 4c0ac.L; MOVE.L #c58ee,(A6).
    case 0xc58da:if(!on10_get(c,0x7a,2,value))return false;r.pc=value!=0U?0xc58e8:0xc58e2;return true;
    case 0xc58e2:return am_call(c,0x4c0ac,0xc58e8);
    case 0xc58e8:if(!am_write(c,r.a[6],4,0xc58ee))return false;r.pc=0xc58ee;return true;
    // ---- c58ee (installed): CMPI.W #2,7a(A6); BNE.W c5916; BTST.B #7,15(A6); BNE.W c590c; JSR 4be2c.L; BRA.W c5912 / JSR 43e34.L.
    case 0xc58ee:if(!on10_get(c,0x7a,2,value))return false;r.pc=value!=2U?0xc5916:0xc58f8;return true;
    case 0xc58f8:if(!on10_get(c,0x15,1,value))return false;r.pc=(value&0x80U)!=0U?0xc590c:0xc5902;return true;
    case 0xc5902:return am_call(c,0x4be2c,0xc5908);
    case 0xc5908:r.pc=0xc5912;return true;                                   // BRA.W c5912.
    case 0xc590c:return am_call(c,0x43e34,0xc5912);
    case 0xc5912:r.pc=0xc591c;return true;                                   // BRA.W c591c.
    case 0xc5916:return am_call(c,0x43e34,0xc591c);
    // MOVE.L 7c(A6),D7; MOVEQ #0,D0; JSR 16ea4.L.
    case 0xc591c:if(!on10_get(c,0x7c,4,value))return false;r.d[7]=value;r.d[0]=0;return am_call(c,0x16ea4,0xc5928);
    case 0xc5928:r.a[0]=ON10_RECT;return am_call(c,0x1ab02,0xc5932);       // LEA c584c(PC),A0; JSR 1ab02.L.
    case 0xc5932:                                                           // BCC.W c593c (C returned by 1ab02).
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n10 caller requires known carry");
        r.pc=r.carry==AnimationCarryClear?0xc593c:0xc5936;return true;
    case 0xc5936:r.pc=0x2a00;return true;                                   // JMP 2a00.L.
    case 0xc593c:return am_return(c);                                        // RTS.
    default:return am_error(c,"unsupported animation objects n10 PC");
    }
}
}
