#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONG (live bus, current PVC bank): the animation record base of 5deec (id 18b) stored in LONG 22(A6).
const std::uint32_t ON24_BANK_18B=0x200194;
// Fixed ROM WORD table indexed by 2 * BYTE 76(A6) (data, live bus; main decision 3).
const std::uint32_t ON24_TABLE=0x5e8a6;
std::uint32_t on24_b(std::uint32_t value) {return value&255U;}
std::uint32_t on24_w(std::uint32_t value) {return value&65535U;}
// Signed comparisons of LONG / WORD values (two's complement, compared through the flipped sign bit).
bool on24_le_l(std::uint32_t a,std::uint32_t b) {return (a^0x80000000U)<=(b^0x80000000U);}
bool on24_lt_w(std::uint32_t a,std::uint32_t b) {return ((a&65535U)^0x8000U)<((b&65535U)^0x8000U);}
bool on24_le_w(std::uint32_t a,std::uint32_t b) {return ((a&65535U)^0x8000U)<=((b&65535U)^0x8000U);}
// ASR.L #count (sign bit refilled explicitly).
std::uint32_t on24_asr_l(std::uint32_t value,unsigned int count) {
    std::uint32_t u=value;for(unsigned int i=0;i<count;++i)u=(u>>1)|(u&0x80000000U);return u;
}
bool on24_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on24_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// <op>.L #/Dn,d(A6): LONG read-modify-write adding addend (two's complement; SUB passes the negated value).
bool on24_add_l(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t addend) {
    std::uint32_t value=0;return on24_get(c,displacement,4,value) && on24_put(c,displacement,4,value+addend);
}
// MOVE.L 3a(A6),D0; ASR.L #shift,D0; SUB.L D0,3a(A6).
bool on24_damp(AnimationMachineContext& c,unsigned int shift) {
    std::uint32_t value=0;if(!on24_get(c,0x3a,4,value))return false;c.s.d[0]=on24_asr_l(value,shift);
    return on24_add_l(c,0x3a,0U-c.s.d[0]);
}
// MOVE.L 36(A6),D0 (the LONG compared afterwards in the same block).
bool on24_load36(AnimationMachineContext& c) {std::uint32_t value=0;if(!on24_get(c,0x36,4,value))return false;c.s.d[0]=value;return true;}
// BSET.B #bit,15(A6) (read, then write).
bool on24_bset15(AnimationMachineContext& c,unsigned int bit) {
    std::uint32_t value=0;return on24_get(c,0x15,1,value) && on24_put(c,0x15,1,on24_b(value|(1U<<bit)));
}
// MOVE.W 46(A6),D0; SUBI.W #100,D0; LSR.W #4,D0; ANDI.B #f,D0; MOVE.B D0,88(A6).
bool on24_dir(AnimationMachineContext& c) {
    std::uint32_t value=0;AnimationMachineState& r=c.s;if(!on24_get(c,0x46,2,value))return false;
    am_word(r.d[0],(value+0xff00U)&65535U);am_word(r.d[0],on24_w(r.d[0])>>4);am_byte(r.d[0],r.d[0]&0xfU);return on24_put(c,0x88,1,on24_b(r.d[0]));
}
// MOVE.W #id,D0; MOVE.B #0,D1; JSR 8ebe.l (all followed by the next block at pc + e).
bool on24_8ebe(AnimationMachineContext& c,std::uint32_t id) {am_word(c.s.d[0],id);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,c.s.pc+0xeU);}
// MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l.
bool on24_anim(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!on24_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],displacement),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// 5e1d2 / 5e4ec: LEA 5e8a6(PC),A0; MOVEQ #0,D0; MOVE.B 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; CLR.B 79(A6); CMPI.W #ffff,D0;
// BEQ.W done.
bool on24_table(AnimationMachineContext& c,std::uint32_t done_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=ON24_TABLE;r.d[0]=0;if(!on24_get(c,0x76,1,value))return false;am_byte(r.d[0],value);
    am_word(r.d[0],(r.d[0]*2U)&65535U);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
    if(!on24_put(c,0x79,1,0))return false;r.pc=on24_w(r.d[0])==0xffffU?done_pc:next_pc;return true;
}
// 5e1ee / 5e508: ST.B 79(A6); LSL.W #2,D0; MOVEA.L 22(A6),A1; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; LEA 26(A6),A0; JSR 49f8c.l.
bool on24_table_anim(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on24_put(c,0x79,1,0xff))return false;am_word(r.d[0],(r.d[0]<<2)&65535U);
    if(!on24_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);return am_call(c,0x49f8c,return_pc);
}
// CMPI.B #value,d(A6); BNE.W not_pc (else equal_pc).
bool on24_byte_is(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t want,std::uint32_t equal_pc,std::uint32_t not_pc) {
    std::uint32_t value=0;if(!on24_get(c,displacement,1,value))return false;c.s.pc=on24_b(value)==want?equal_pc:not_pc;return true;
}
// CMPI.W #limit,2e(A6); BGE.W ge_pc (else lt_pc).
bool on24_2e_ge(AnimationMachineContext& c,std::uint32_t limit,std::uint32_t ge_pc,std::uint32_t lt_pc) {
    std::uint32_t value=0;if(!on24_get(c,0x2e,2,value))return false;c.s.pc=on24_lt_w(value,limit)?lt_pc:ge_pc;return true;
}
// CMPI.W #limit,2e(A6); BLE.W le_pc (else gt_pc).
bool on24_2e_le(AnimationMachineContext& c,std::uint32_t limit,std::uint32_t le_pc,std::uint32_t gt_pc) {
    std::uint32_t value=0;if(!on24_get(c,0x2e,2,value))return false;c.s.pc=on24_le_w(value,limit)?le_pc:gt_pc;return true;
}
// CMPI.L #limit,3a(A6); BLE.W / BGE.W.
bool on24_3a_le(AnimationMachineContext& c,std::uint32_t limit,std::uint32_t le_pc,std::uint32_t gt_pc) {
    std::uint32_t value=0;if(!on24_get(c,0x3a,4,value))return false;c.s.pc=on24_le_l(value,limit)?le_pc:gt_pc;return true;
}
bool on24_3a_ge(AnimationMachineContext& c,std::uint32_t limit,std::uint32_t ge_pc,std::uint32_t lt_pc) {
    std::uint32_t value=0;if(!on24_get(c,0x3a,4,value))return false;c.s.pc=(on24_le_l(value,limit)&&value!=limit)?lt_pc:ge_pc;return true;
}
// MOVE.W 32(A6),D0; CMP.W 86(A6),D0; BEQ.W equal; BLE.W less (else greater).
bool on24_32_86(AnimationMachineContext& c,std::uint32_t equal_pc,std::uint32_t less_pc,std::uint32_t greater_pc) {
    std::uint32_t value=0;if(!on24_get(c,0x32,2,value))return false;am_word(c.s.d[0],value);if(!on24_get(c,0x86,2,value))return false;
    c.s.pc=on24_w(c.s.d[0])==on24_w(value)?equal_pc:(on24_lt_w(c.s.d[0],value)?less_pc:greater_pc);return true;
}
// TST.B 62(A6); BEQ.W zero_pc / CLR.B 62(A6) blocks.
bool on24_62(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!on24_get(c,0x62,1,value))return false;c.s.pc=on24_b(value)==0U?zero_pc:set_pc;return true;
}
}
// Objects F4 N24 (195 block starts): the stage event callback 5deec (fixed ROM LONG e9048; 16 children through 28ae, banked LONG
// 200194) and the installed callback 5e0c0 (state BYTE 76 = 0..3, sub state BYTE 77 = 0..4: LONG 36 / 3a speeds, WORD 2e / 32
// positions), the common tail 5e7dc (43ea4, 49fc6, 4b54e, BYTE 61 bit 7 -> install 6093a and BRA.W 6093a). Boundary without an
// executor: 6093a. The WORD table 5e8a6 is read on the live bus. The only C consumer is 5e7f6 (BCC.W after JSR 4b54e). No port, no
// bank change, no X, no register-indirect control transfer.
bool animation_objects_n24_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 5deec (stage event callback).
    case 0x5deec:case 0x5e3a2:case 0x5e7b0:return on24_8ebe(c,0xd48);  // MOVE.W #d48,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x5e056:case 0x5e1ba:case 0x5e4d4:case 0x5e822:case 0x5e854:return on24_8ebe(c,0xd4b);
    case 0x5e87c:return on24_8ebe(c,0xd4d);
    // BSET.B #6,15(A6); MOVE.W #800,68(A6); MOVE.W #800,1e(A6); JSR 16ef0.l.
    case 0x5defa:
        if(!on24_bset15(c,6) || !on24_put(c,0x68,2,0x800) || !on24_put(c,0x1e,2,0x800))return false;return am_call(c,0x16ef0,0x5df12);
    // MOVE.W #18b,20(A6); MOVE.L 200194.l,22(A6); BSET.B #0,15(A6); MOVE.W #190,2e(A6); MOVE.W #0,32(A6); JSR 43e34.l.
    case 0x5df12:
        if(!on24_put(c,0x20,2,0x18b) || !am_read(c,ON24_BANK_18B,4,value) || !on24_put(c,0x22,4,value) || !on24_bset15(c,0) ||
            !on24_put(c,0x2e,2,0x190) || !on24_put(c,0x32,2,0))return false;
        return am_call(c,0x43e34,0x5df38);
    // ST.B 79(A6); CLR.B 63(A6) (twice); MOVE.B #0,76(A6); MOVE.B #0,77(A6); MOVEA.L #5e8c8,A0; MOVE.W #0,D0; JSR 28ae.l.
    case 0x5df38:
        if(!on24_put(c,0x79,1,0xff) || !on24_put(c,0x63,1,0) || !on24_put(c,0x63,1,0) || !on24_put(c,0x76,1,0) || !on24_put(c,0x77,1,0))
            return false;
        r.a[0]=0x5e8c8;am_word(r.d[0],0);return am_call(c,0x28ae,0x5df60);
    // MOVEA.L #child,A0; MOVE.W #0,D0; JSR 28ae.l (15 children, next block at pc + 10).
    case 0x5df60:case 0x5df70:case 0x5df80:case 0x5df90:case 0x5dfa0:case 0x5dfb0:case 0x5dfc0:case 0x5dfd0:case 0x5dfe0:case 0x5dff0:
    case 0x5e000:case 0x5e010:case 0x5e020:case 0x5e030:case 0x5e040: {
        const std::uint32_t children[15]={0x5eac2,0x5ead4,0x5efe6,0x5eff8,0x5f24a,0x5f25c,0x5f760,0x5f76c,0x5fb0e,0x5fb20,0x5fd24,0x5fd36,
            0x60008,0x6031e,0x6041e};
        r.a[0]=children[(r.pc-0x5df60U)/0x10U];am_word(r.d[0],0);return am_call(c,0x28ae,r.pc+0x10U);
    }
    case 0x5e050:case 0x5e7aa:return am_call(c,0x8ff4,r.pc+6U);           // JSR 8ff4.l.
    case 0x5e064:case 0x5e1c8:case 0x5e3b0:case 0x5e4e2:case 0x5e7be:am_word(r.d[0],0xd56);return am_call(c,0x4a496,r.pc+0xaU); // JSR 4a496.l.
    case 0x5e06e:return on24_anim(c,0xc8,0x5e084);
    case 0x5e084:if(!on24_put(c,0x88,1,7))return false;r.a[0]=0x60c0a;return am_call(c,0x490ba,0x5e096); // MOVE.B #7,88(A6); LEA 60c0a.l,A0.
    case 0x5e096:if(!on24_put(c,0x54,2,on24_w(r.d[0])))return false;am_word(r.d[0],0x74e);return am_call(c,0x3af8,0x5e0a4); // MOVE.W D0,54(A6).
    // MOVE.L #0,36(A6); MOVE.L #0,3a(A6); MOVE.W #f0,86(A6); MOVE.L #5e0c0,(A6) (fall-through into the installed callback).
    case 0x5e0a4:
        if(!on24_put(c,0x36,4,0) || !on24_put(c,0x3a,4,0) || !on24_put(c,0x86,2,0xf0) || !am_write(c,r.a[6],4,0x5e0c0))return false;
        r.pc=0x5e0c0;return true;
    // ---- 5e0c0 (installed): CMPI.B #0,76(A6); BNE.W 5e20e.
    case 0x5e0c0:return on24_byte_is(c,0x76,0,0x5e0ca,0x5e20e);
    // State 0: MOVE.L #0,56(A6); MOVE.W 32(A6),D0; CMP.W 86(A6),D0; BEQ.W 5e13c; BLE.W 5e108.
    case 0x5e0ca:if(!on24_put(c,0x56,4,0))return false;return on24_32_86(c,0x5e13c,0x5e108,0x5e0e2);
    case 0x5e0e2:return on24_3a_le(c,0xfffe0000U,0x5e0fa,0x5e0ee);         // CMPI.L #fffe0000,3a(A6); BLE.W 5e0fa.
    case 0x5e0ee:if(!on24_add_l(c,0x3a,0xffffc000U))return false;r.pc=0x5e104;return true; // ADDI.L #ffffc000,3a(A6); BRA.W.
    case 0x5e0fa:case 0x5e120:case 0x5e40a:case 0x5e430:                   // MOVE.L 3a(A6),D0; ASR.L #3,D0; SUB.L D0,3a(A6).
        if(!on24_damp(c,3))return false;r.pc=r.pc==0x5e0fa?0x5e104U:(r.pc==0x5e120?0x5e12aU:(r.pc==0x5e40a?0x5e414U:0x5e43aU));return true;
    case 0x5e6d4:case 0x5e6fa:if(!on24_damp(c,2))return false;r.pc=r.pc==0x5e6d4?0x5e6deU:0x5e704U;return true; // ASR.L #2.
    case 0x5e104:case 0x5e114:                                               // BRA.W 5e12a (5e114: ADDI.L #4000,3a(A6) first).
        if(r.pc==0x5e114 && !on24_add_l(c,0x3a,0x4000))return false;r.pc=0x5e12a;return true;
    case 0x5e108:return on24_3a_ge(c,0x20000,0x5e120,0x5e114);               // CMPI.L #20000,3a(A6); BGE.W 5e120.
    case 0x5e12a:if(!on24_dir(c))return false;r.pc=0x5e13c;return true;
    // MOVE.L 36(A6),D0; CMPI.L #fffb0000,D0; BLE.W 5e156 / ASR.L #3,D0; SUBI.L #1000,D0; ADD.L D0,36(A6).
    case 0x5e13c:if(!on24_load36(c))return false;r.pc=on24_le_l(r.d[0],0xfffb0000U)?0x5e156:0x5e14a;return true;
    case 0x5e14a:r.d[0]=on24_asr_l(r.d[0],3)-0x1000U;if(!on24_add_l(c,0x36,r.d[0]))return false;r.pc=0x5e156;return true;
    case 0x5e156:return on24_2e_ge(c,0xffb0,0x5e20a,0x5e160);                // CMPI.W #ffb0,2e(A6); BGE.W 5e20a.
    case 0x5e160:if(!on24_get(c,0x89,1,value))return false;r.pc=on24_b(value)!=0U?0x5e176:0x5e168;return true; // TST.B 89(A6); BNE.W.
    case 0x5e168:if(!on24_put(c,0x89,1,0xff))return false;am_word(r.d[0],0x19d4);return am_call(c,0x3af8,0x5e176); // ST.B 89(A6).
    case 0x5e176:case 0x5e470:am_word(r.d[0],0x750);return am_call(c,0x3af8,r.pc+0xaU); // MOVE.W #750,D0; JSR 3af8.l.
    // MOVE.B #1,76(A6); MOVE.B #0,77(A6); MOVE.L #4000,36(A6); MOVE.L #0,3a(A6); MOVE.W #ff80,2e(A6); MOVE.W #84,32(A6);
    // MOVE.B #ff,12(A6); MOVE.B #ff,13(A6); JSR 8ff4.l.
    case 0x5e180:
        if(!on24_put(c,0x76,1,1) || !on24_put(c,0x77,1,0) || !on24_put(c,0x36,4,0x4000) || !on24_put(c,0x3a,4,0) || !on24_put(c,0x2e,2,0xff80) ||
            !on24_put(c,0x32,2,0x84) || !on24_put(c,0x12,1,0xff) || !on24_put(c,0x13,1,0xff))return false;
        return am_call(c,0x8ff4,0x5e1ba);
    case 0x5e1d2:return on24_table(c,0x5e20a,0x5e1ee);
    case 0x5e4ec:return on24_table(c,0x5e524,0x5e508);
    case 0x5e1ee:return on24_table_anim(c,0x5e20a);
    case 0x5e508:return on24_table_anim(c,0x5e524);
    // BRA.W 5e7dc.
    case 0x5e20a:case 0x5e27c:case 0x5e2de:case 0x5e340:case 0x5e3ca:case 0x5e3ce:case 0x5e524:case 0x5e57e:case 0x5e5ec:case 0x5e65a:
    case 0x5e728:case 0x5e7d8:r.pc=0x5e7dc;return true;
    // Other BRA.W blocks.
    case 0x5e246:r.pc=0x5e27c;return true;
    case 0x5e2ae:r.pc=0x5e2c2;return true;
    case 0x5e310:r.pc=0x5e324;return true;
    case 0x5e414:r.pc=0x5e43a;return true;
    case 0x5e574:r.pc=0x5e57e;return true;
    case 0x5e5bc:r.pc=0x5e5da;return true;
    case 0x5e62a:r.pc=0x5e648;return true;
    case 0x5e68e:r.pc=0x5e6ac;return true;
    case 0x5e6de:r.pc=0x5e704;return true;
    // ---- State 1 (BYTE 76 = 1).
    case 0x5e20e:return on24_byte_is(c,0x76,1,0x5e218,0x5e3d2);
    case 0x5e218:return on24_byte_is(c,0x77,0,0x5e222,0x5e280);
    case 0x5e222:return on24_2e_ge(c,0x40,0x5e24a,0x5e22c);
    // MOVE.L 36(A6),D0; CMPI.L #60000,D0; BGE.W (skip).
    case 0x5e22c:case 0x5e294:case 0x5e2f6:case 0x5e5c0:case 0x5e62e:case 0x5e692: {
        if(!on24_load36(c))return false;const bool ge=!(on24_le_l(r.d[0],0x60000)&&r.d[0]!=0x60000U);
        switch(r.pc) {
        case 0x5e22c:r.pc=ge?0x5e246U:0x5e23aU;break;
        case 0x5e294:r.pc=ge?0x5e2aeU:0x5e2a2U;break;
        case 0x5e2f6:r.pc=ge?0x5e310U:0x5e304U;break;
        case 0x5e5c0:r.pc=ge?0x5e5daU:0x5e5ceU;break;
        case 0x5e62e:r.pc=ge?0x5e648U:0x5e63cU;break;
        default:r.pc=ge?0x5e6acU:0x5e6a0U;break;
        }
        return true;
    }
    // ASR.L #3,D0; ADDI.L #1000,D0; ADD.L D0,36(A6).
    case 0x5e23a:case 0x5e2a2:case 0x5e304:case 0x5e45a:case 0x5e74e:
        r.d[0]=on24_asr_l(r.d[0],3)+0x1000U;if(!on24_add_l(c,0x36,r.d[0]))return false;
        r.pc=r.pc==0x5e23a?0x5e246U:(r.pc==0x5e2a2?0x5e2aeU:(r.pc==0x5e304?0x5e310U:(r.pc==0x5e45a?0x5e466U:0x5e75aU)));return true;
    // MOVE.L 36(A6),D0; ASR.L #2,D0; ADDI.L #1000,D0; SUB.L D0,36(A6) (5e24a: then CLR.B 62(A6); JSR 49a58.l).
    case 0x5e24a:case 0x5e2b2:case 0x5e314:
        if(!on24_load36(c))return false;r.d[0]=on24_asr_l(r.d[0],2)+0x1000U;if(!on24_add_l(c,0x36,0U-r.d[0]))return false;
        if(r.pc==0x5e24a) {if(!on24_put(c,0x62,1,0))return false;return am_call(c,0x49a58,0x5e264);}
        r.pc=r.pc==0x5e2b2?0x5e2c2U:0x5e324U;return true;
    case 0x5e264:am_byte(r.d[0],r.d[0]&3U);r.pc=(r.d[0]&3U)!=0U?0x5e276:0x5e26c;return true; // ANDI.B #3,D0; BNE.W 5e276.
    case 0x5e26c:case 0x5e276:if(!on24_put(c,0x77,1,r.pc==0x5e26c?1U:2U))return false;r.pc=0x5e27c;return true; // MOVE.B #1/#2,77(A6).
    case 0x5e280:return on24_byte_is(c,0x77,1,0x5e28a,0x5e2e2);
    case 0x5e28a:return on24_2e_ge(c,0x20,0x5e2b2,0x5e294);
    case 0x5e2c2:return on24_62(c,0x5e2de,0x5e2ca);
    case 0x5e324:return on24_62(c,0x5e340,0x5e32c);
    // CLR.B 62(A6); MOVE.W #74f,D0; JSR 3af8.l.
    case 0x5e2ca:case 0x5e32c:case 0x5e70c:if(!on24_put(c,0x62,1,0))return false;am_word(r.d[0],0x74f);return am_call(c,0x3af8,r.pc+0xeU);
    case 0x5e2d8:case 0x5e33a:if(!on24_put(c,0x77,1,3))return false;r.pc=r.pc+6U;return true; // MOVE.B #3,77(A6).
    case 0x5e2e2:return on24_byte_is(c,0x77,2,0x5e2ec,0x5e344);
    case 0x5e2ec:return on24_2e_ge(c,0x20,0x5e314,0x5e2f6);
    case 0x5e344:return on24_byte_is(c,0x77,3,0x5e34e,0x5e3ce);
    // MOVE.L 36(A6),D0; CMPI.L #fffa0000,D0; BLE.W.
    case 0x5e34e:case 0x5e550:case 0x5e5a0:case 0x5e60e:case 0x5e672: {
        if(!on24_load36(c))return false;const bool le=on24_le_l(r.d[0],0xfffa0000U);
        switch(r.pc) {
        case 0x5e34e:r.pc=le?0x5e368U:0x5e35cU;break;
        case 0x5e550:r.pc=le?0x5e56eU:0x5e55eU;break;
        case 0x5e5a0:r.pc=le?0x5e5bcU:0x5e5aeU;break;
        case 0x5e60e:r.pc=le?0x5e62aU:0x5e61cU;break;
        default:r.pc=le?0x5e68eU:0x5e680U;break;
        }
        return true;
    }
    // ASR.L #3,D0; ADDI.L #fffff000,D0; ADD.L D0,36(A6) (5e55e: then BRA.W 5e574).
    case 0x5e35c:case 0x5e55e:
        r.d[0]=on24_asr_l(r.d[0],3)+0xfffff000U;if(!on24_add_l(c,0x36,r.d[0]))return false;r.pc=r.pc==0x5e35c?0x5e368U:0x5e574U;return true;
    case 0x5e368:return on24_2e_ge(c,0xffa0,0x5e3ca,0x5e372);
    case 0x5e372:case 0x5e764:am_word(r.d[0],0x74e);return am_call(c,0x3af8,r.pc+0xaU); // MOVE.W #74e,D0; JSR 3af8.l.
    // MOVE.B #2,76(A6); MOVE.B #0,77(A6); MOVE.L #8000,36(A6); MOVE.W #ffa0,2e(A6); MOVE.W #f0,32(A6); JSR 8ff4.l.
    case 0x5e37c:
        if(!on24_put(c,0x76,1,2) || !on24_put(c,0x77,1,0) || !on24_put(c,0x36,4,0x8000) || !on24_put(c,0x2e,2,0xffa0) || !on24_put(c,0x32,2,0xf0))
            return false;
        return am_call(c,0x8ff4,0x5e3a2);
    case 0x5e3ba:case 0x5e7c8:r.a[1]=0x60c9e;am_word(r.d[0],0x100);return am_call(c,0x49f8c,r.pc+0x10U); // MOVEA.L #60c9e,A1; JSR 49f8c.
    // ---- State 2 (BYTE 76 = 2): MOVE.L #0,56(A6); CMPI.W #0,32(A6); BEQ.W 5e43a; BLE.W 5e418.
    case 0x5e3d2:return on24_byte_is(c,0x76,2,0x5e3dc,0x5e528);
    case 0x5e3dc:
        if(!on24_put(c,0x56,4,0) || !on24_get(c,0x32,2,value))return false;
        r.pc=on24_w(value)==0U?0x5e43a:((value&0x8000U)!=0U?0x5e418:0x5e3f2);return true;
    case 0x5e3f2:return on24_3a_le(c,0xfffe0000U,0x5e40a,0x5e3fe);
    case 0x5e3fe:if(!on24_add_l(c,0x3a,0xffffc000U))return false;r.pc=0x5e414;return true;
    case 0x5e418:return on24_3a_ge(c,0x20000,0x5e430,0x5e424);
    case 0x5e424:if(!on24_add_l(c,0x3a,0x4000))return false;r.pc=0x5e43a;return true;
    // 88 = direction nibble; MOVE.L 36(A6),D0; CMPI.L #50000,D0; BGE.W 5e466.
    case 0x5e43a:
        if(!on24_dir(c) || !on24_load36(c))return false;r.pc=(on24_le_l(r.d[0],0x50000)&&r.d[0]!=0x50000U)?0x5e45a:0x5e466;return true;
    case 0x5e466:return on24_2e_le(c,0x190,0x5e524,0x5e470);
    case 0x5e47a:am_word(r.d[0],0x736);return am_call(c,0x3af8,0x5e484);   // MOVE.W #736,D0; JSR 3af8.l.
    // MOVE.B #3,76(A6); MOVE.B #0,77(A6); JSR 49a58.l.
    case 0x5e484:if(!on24_put(c,0x76,1,3) || !on24_put(c,0x77,1,0))return false;return am_call(c,0x49a58,0x5e496);
    case 0x5e496:am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&1U)!=0U?0x5e4a8:0x5e49e;return true; // ANDI.W #1,D0; BNE.W 5e4a8.
    case 0x5e49e:case 0x5e4a8:if(!on24_put(c,0x86,2,r.pc==0x5e49e?0U:0x100U))return false;r.pc=0x5e4ae;return true; // MOVE.W #0/#100,86(A6).
    // MOVE.L #ffff8000,36(A6); MOVE.W #1b0,2e(A6); MOVE.W #84,32(A6); MOVE.B #ff,12(A6); MOVE.B #ff,13(A6); JSR 8ff4.l.
    case 0x5e4ae:
        if(!on24_put(c,0x36,4,0xffff8000U) || !on24_put(c,0x2e,2,0x1b0) || !on24_put(c,0x32,2,0x84) || !on24_put(c,0x12,1,0xff) ||
            !on24_put(c,0x13,1,0xff))return false;
        return am_call(c,0x8ff4,0x5e4d4);
    // ---- State 3 (BYTE 76 = 3).
    case 0x5e528:return on24_byte_is(c,0x76,3,0x5e532,0x5e7dc);
    case 0x5e532:return on24_byte_is(c,0x77,0,0x5e53c,0x5e582);
    // MOVE.L 3a(A6),D0; ASR.L #3,D0; SUB.L D0,3a(A6); CMPI.W #limit,2e(A6); BLE.W.
    case 0x5e53c:if(!on24_damp(c,3))return false;return on24_2e_le(c,0xf0,0x5e578,0x5e550);
    case 0x5e58c:if(!on24_damp(c,3))return false;return on24_2e_le(c,0xf0,0x5e5c0,0x5e5a0);
    case 0x5e5fa:if(!on24_damp(c,3))return false;return on24_2e_le(c,0x100,0x5e62e,0x5e60e);
    case 0x5e56e:r.d[0]=on24_asr_l(r.d[0],3);if(!on24_add_l(c,0x36,0U-r.d[0]))return false;r.pc=0x5e574;return true; // SUB.L D0,36(A6).
    case 0x5e578:if(!on24_put(c,0x77,1,1))return false;r.pc=0x5e57e;return true; // MOVE.B #1,77(A6).
    case 0x5e582:return on24_byte_is(c,0x77,1,0x5e58c,0x5e5f0);
    // ASR.L #3,D0; SUB.L D0,36(A6); ADDI.L #fffff000,36(A6).
    case 0x5e5ae:case 0x5e61c:case 0x5e680:
        r.d[0]=on24_asr_l(r.d[0],3);if(!on24_add_l(c,0x36,0U-r.d[0]) || !on24_add_l(c,0x36,0xfffff000U))return false;
        r.pc=r.pc==0x5e5ae?0x5e5bcU:(r.pc==0x5e61c?0x5e62aU:0x5e68eU);return true;
    // ASR.L #3,D0; ADDI.L #fffff000,D0; SUB.L D0,36(A6).
    case 0x5e5ce:case 0x5e63c:case 0x5e6a0:
        r.d[0]=on24_asr_l(r.d[0],3)+0xfffff000U;if(!on24_add_l(c,0x36,0U-r.d[0]))return false;
        r.pc=r.pc==0x5e5ce?0x5e5daU:(r.pc==0x5e63c?0x5e648U:0x5e6acU);return true;
    case 0x5e5da:return on24_62(c,0x5e5ec,0x5e5e2);
    case 0x5e648:return on24_62(c,0x5e65a,0x5e650);
    // CLR.B 62(A6); MOVE.B #2/#3,77(A6).
    case 0x5e5e2:case 0x5e650:
        if(!on24_put(c,0x62,1,0) || !on24_put(c,0x77,1,r.pc==0x5e5e2?2U:3U))return false;r.pc=r.pc+0xaU;return true;
    case 0x5e5f0:return on24_byte_is(c,0x77,2,0x5e5fa,0x5e65e);
    case 0x5e65e:return on24_byte_is(c,0x77,3,0x5e668,0x5e72c);
    case 0x5e668:return on24_2e_le(c,0x100,0x5e692,0x5e672);
    case 0x5e6ac:return on24_32_86(c,0x5e704,0x5e6e2,0x5e6bc);
    case 0x5e6bc:return on24_3a_le(c,0xfffc8000U,0x5e6d4,0x5e6c8);
    case 0x5e6c8:if(!on24_add_l(c,0x3a,0xffff0000U))return false;r.pc=0x5e6de;return true;
    case 0x5e6e2:return on24_3a_ge(c,0x38000,0x5e6fa,0x5e6ee);
    case 0x5e6ee:if(!on24_add_l(c,0x3a,0x10000))return false;r.pc=0x5e704;return true;
    case 0x5e704:return on24_62(c,0x5e728,0x5e70c);
    // MOVE.B #4,77(A6); MOVE.L #8000,36(A6).
    case 0x5e71a:if(!on24_put(c,0x77,1,4) || !on24_put(c,0x36,4,0x8000))return false;r.pc=0x5e728;return true;
    case 0x5e72c:return on24_byte_is(c,0x77,4,0x5e736,0x5e7d8);
    // MOVE.L 3a(A6),D0; ASR.L #3,D0; SUB.L D0,3a(A6); MOVE.L 36(A6),D0; CMPI.L #60000,D0; BGE.W 5e75a.
    case 0x5e736:
        if(!on24_damp(c,3) || !on24_load36(c))return false;r.pc=(on24_le_l(r.d[0],0x60000)&&r.d[0]!=0x60000U)?0x5e74e:0x5e75a;return true;
    case 0x5e75a:return on24_2e_le(c,0x190,0x5e7d8,0x5e764);
    // MOVE.B #0,76(A6); MOVE.B #0,77(A6); MOVE.L #ffffc000,36(A6); MOVE.L #0,3a(A6); MOVE.W #190,2e(A6); CMPI.W #80,32(A6); BLE.W 5e7a4.
    case 0x5e76e:
        if(!on24_put(c,0x76,1,0) || !on24_put(c,0x77,1,0) || !on24_put(c,0x36,4,0xffffc000U) || !on24_put(c,0x3a,4,0) ||
            !on24_put(c,0x2e,2,0x190) || !on24_get(c,0x32,2,value))return false;
        r.pc=on24_le_w(value,0x80)?0x5e7a4:0x5e79a;return true;
    case 0x5e79a:case 0x5e7a4:if(!on24_put(c,0x86,2,r.pc==0x5e79a?0U:0xf0U))return false;r.pc=0x5e7aa;return true; // MOVE.W #0/#f0,86(A6).
    // ---- Common tail: JSR 43ea4.l; TST.B 79(A6); BEQ.W 5e7f0; JSR 49fc6.l; JSR 4b54e.l; BCC.W 5e7fe; CLR.B 5e(A6).
    case 0x5e7dc:return am_call(c,0x43ea4,0x5e7e2);
    case 0x5e7e2:if(!on24_get(c,0x79,1,value))return false;r.pc=on24_b(value)==0U?0x5e7f0:0x5e7ea;return true;
    case 0x5e7ea:return am_call(c,0x49fc6,0x5e7f0);
    case 0x5e7f0:return am_call(c,0x4b54e,0x5e7f6);
    case 0x5e7f6:                                                            // BCC.W 5e7fe (C returned by 4b54e).
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n24 caller requires known carry");
        r.pc=r.carry==AnimationCarryClear?0x5e7fe:0x5e7fa;return true;
    case 0x5e7fa:if(!on24_put(c,0x5e,1,0))return false;r.pc=0x5e7fe;return true;
    // BTST.B #7,61(A6); BEQ.W 5e8a4.
    case 0x5e7fe:if(!on24_get(c,0x61,1,value))return false;r.pc=(value&0x80U)==0U?0x5e8a4:0x5e808;return true;
    // ST.B 63(A6); MOVE.L #6093a,(A6); JSR 8ff4.l.
    case 0x5e808:if(!on24_put(c,0x63,1,0xff) || !am_write(c,r.a[6],4,0x6093a))return false;return am_call(c,0x8ff4,0x5e818);
    case 0x5e818:return on24_byte_is(c,0x76,1,0x5e822,0x5e84a);
    case 0x5e84a:return on24_byte_is(c,0x76,3,0x5e854,0x5e87c);
    case 0x5e830:return on24_anim(c,0xdc,0x5e846);
    case 0x5e862:return on24_anim(c,0xd8,0x5e878);
    case 0x5e88a:return on24_anim(c,0xe4,0x5e8a0);
    case 0x5e846:case 0x5e878:case 0x5e8a0:r.pc=0x6093a;return true;        // BRA.W 6093a (boundary).
    case 0x5e8a4:return am_return(c);                                       // RTS.
    default:return am_error(c,"unsupported animation objects n24 PC");
    }
}
}
