#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONG (live bus, current PVC bank): animation record of 2b7ce (id f2).
const std::uint32_t ON28_BANK_F2=0x20009c;
// WORD pair table indexed by 4 * BYTE 7c (2b668 / 2b692 / 2b9d6).
const std::uint32_t ON28_PAIRS=0x2d8b8;
std::uint32_t on28_b(std::uint32_t value) {return value&255U;}
std::uint32_t on28_w(std::uint32_t value) {return value&65535U;}
// A WORD as a signed value (BGE / BGT), converted explicitly.
std::int32_t on28_signed_w(std::uint32_t value) {
    const std::uint32_t u=value&65535U;return (u&0x8000U)?static_cast<std::int32_t>(u)-65536:static_cast<std::int32_t>(u);
}
// Arithmetic shift right of a WORD / LONG (sign bit refilled explicitly; a LONG count of 32 or more leaves only sign bits).
std::uint32_t on28_asr_w(std::uint32_t value,unsigned int count) {
    std::uint32_t u=value&65535U;for(unsigned int i=0;i<count;++i)u=(u>>1)|(u&0x8000U);return u;
}
std::uint32_t on28_asr_l(std::uint32_t value,unsigned int count) {
    std::uint32_t u=value;for(unsigned int i=0;i<count;++i)u=(u>>1)|(u&0x80000000U);return u;
}
bool on28_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on28_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// BYTE bit of the memory operand d16(base) (BTST.B #bit,<ea>): true when the bit is 1.
bool on28_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on28_get(c,base,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,d16(A6) (read, then write the BYTE; only Z changes, which no N28 branch reads).
bool on28_bset(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!on28_get(c,c.s.a[6],displacement,1,value))return false;
    return on28_put(c,c.s.a[6],displacement,1,set?(value|(1U<<bit))&255U:(value&~(1U<<bit))&255U);
}
// MOVE.B <src d16(A6)>,<dst d16(A6)>.
bool on28_copy_b(AnimationMachineContext& c,std::uint32_t from,std::uint32_t to) {
    std::uint32_t value=0;return on28_get(c,c.s.a[6],from,1,value) && on28_put(c,c.s.a[6],to,1,on28_b(value));
}
// MOVE.L #value,(A6) (installed callback LONG).
bool on28_install(AnimationMachineContext& c,std::uint32_t value) {return on28_put(c,c.s.a[6],0,4,value);}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on28_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n28 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEQ #0,Dx; MOVE.B 7c(node),Dx; ADD.W Dx,Dx (twice); LEA 2d8b8(PC),A4; ADDA.W Dx,A4; MOVE.W (A4)+,D0; MOVE.W (A4)+,D1;
// BTST.B #0,15(node); BEQ.W skip_pc (else neg_pc). Dx = D0 (index_d0) or D1.
bool on28_pair(AnimationMachineContext& c,std::uint32_t node,bool index_d0,std::uint32_t neg_pc,std::uint32_t skip_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool bit=false;
    std::uint32_t& index=index_d0?r.d[0]:r.d[1];
    index=0;if(!on28_get(c,node,0x7c,1,value))return false;am_byte(index,value);am_word(index,(index*4U)&65535U);
    r.a[4]=am_index(ON28_PAIRS,index);
    if(!am_read(c,r.a[4],2,value))return false;am_word(r.d[0],value);r.a[4]+=2U;
    if(!am_read(c,r.a[4],2,value))return false;am_word(r.d[1],value);r.a[4]+=2U;
    if(!on28_bit(c,node,0x15,0,bit))return false;r.pc=bit?neg_pc:skip_pc;return true;
}
// LEA 8e(A6),A1; MOVE.L A1,76(A0); MOVE.B #6,7a(A0); MOVE.B #0,7b(A0); MOVE.B #0,7c(A0); MOVE.B #0,7d(A0); MOVE.B #b7e,7e(A0);
// ORI.B #1,CCR (2b832 / 2b874).
bool on28_child(AnimationMachineContext& c,std::uint32_t b7e,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;r.a[1]=am_index(r.a[6],0x8e);
    if(!on28_put(c,r.a[0],0x76,4,r.a[1]) || !on28_put(c,r.a[0],0x7a,1,6) || !on28_put(c,r.a[0],0x7b,1,0) || !on28_put(c,r.a[0],0x7c,1,0) ||
       !on28_put(c,r.a[0],0x7d,1,0) || !on28_put(c,r.a[0],0x7e,1,b7e))return false;
    r.carry=AnimationCarrySet;r.pc=next_pc;return true;
}
// MOVE.L #l36,36(A0); MOVE.L #l3a,3a(A0); MOVE.W #w54,54(A0) (the d3d7c node).
bool on28_spark(AnimationMachineContext& c,std::uint32_t l36,std::uint32_t l3a,std::uint32_t w54) {
    AnimationMachineState& r=c.s;return on28_put(c,r.a[0],0x36,4,l36) && on28_put(c,r.a[0],0x3a,4,l3a) && on28_put(c,r.a[0],0x54,2,w54);
}
}
// Objects F4 N28 (151 block starts): the stage event callbacks 2b8a0 / 2b8a6 (2b7ce setup, 28ae child 41fe6; installs 2b96c and the
// 2b99c fall-through, then 2c7fe / 2c838 and 2ca68), the direction helper 2b418 (JMP 49fc6), 2b668 (JMP 4da50 with the code pointer
// 2b692; ANDI Clear), 2c760, the stage event callback 306a8 (installs 30718 / 3075a) and the shared tails 2c8ca / 30f84. Boundaries
// without an executor: 2b63e 2c71a 3165e 316b2 318b8 318d8 319f6 4c37c 4c3a2 4c3de 4d4b4 4db18 4ff96 8d34 d3d7c. The 10 BCC/BCS
// consumers read a known C returned by 28ae / 1aa7e / 4d2d4 / 2b63e / 319f6 / 4d766; ORI CCR (2b832 2b874) sets and ANDI CCR (2b6b6)
// clears it. Every other flag test stays inside its block. No register-indirect transfer, no port, no bank change.
bool animation_objects_n28_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool bit=false;
    switch(r.pc) {
    // ---- 2b418 (JSR / BSR from 2b9be 2c8b4 and outside callers): BTST.B #7,15(A6); BNE.W 2b42a.
    case 0x2b418:if(!on28_bit(c,r.a[6],0x15,7,bit))return false;r.pc=bit?0x2b42a:0x2b422;return true;
    case 0x2b422:r.a[0]=0x2b374;r.pc=0x2b440;return true;               // LEA 2b374(PC),A0; BRA.W 2b440.
    // CMPI.B #1,7f(A6); BCC.W 2b43c (unsigned BYTE >= 1).
    case 0x2b42a:if(!on28_get(c,r.a[6],0x7f,1,value))return false;r.pc=on28_b(value)>=1U?0x2b43c:0x2b434;return true;
    case 0x2b434:r.a[0]=0x2b2ec;r.pc=0x2b440;return true;               // LEA 2b2ec(PC),A0; BRA.W 2b440.
    case 0x2b43c:r.a[0]=0x2b330;r.pc=0x2b440;return true;               // LEA 2b330(PC),A0.
    // MOVEQ #0,D0; MOVE.B 7c(A6),D0; ADD.W D0,D0 (twice); MOVE.L (A0,D0.W),56(A6); TST.L 36(A6); SNE.B 80(A6); MOVE.W 8c(A6),D0;
    // BTST.B #0,15(A6); BEQ.W 2b468.
    case 0x2b440:
        r.d[0]=0;if(!on28_get(c,r.a[6],0x7c,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],(r.d[0]*4U)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value) || !on28_put(c,r.a[6],0x56,4,value))return false;
        if(!on28_get(c,r.a[6],0x36,4,value) || !on28_put(c,r.a[6],0x80,1,value!=0U?0xffU:0U))return false;
        if(!on28_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],value);
        if(!on28_bit(c,r.a[6],0x15,0,bit))return false;r.pc=bit?0x2b466:0x2b468;return true;
    case 0x2b466:am_word(r.d[0],(0U-r.d[0])&65535U);r.pc=0x2b468;return true; // NEG.W D0.
    // ASR.W #5,D0; BMI.W 2b47e.
    case 0x2b468:am_word(r.d[0],on28_asr_w(r.d[0],5));r.pc=(r.d[0]&0x8000U)!=0U?0x2b47e:0x2b46e;return true;
    // SUBQ.W #1,D0; BCS.W 2b478 (borrow when the WORD was 0).
    case 0x2b46e:bit=on28_w(r.d[0])==0U;am_word(r.d[0],(r.d[0]+0xffffU)&65535U);r.pc=bit?0x2b478:0x2b474;return true;
    case 0x2b474:am_word(r.d[0],r.d[0]&0xffU);r.pc=0x2b478;return true; // ANDI.W #ff,D0.
    case 0x2b478:am_word(r.d[0],(r.d[0]+1U)&65535U);r.pc=0x2b486;return true; // ADDQ.W #1,D0; BRA.W 2b486.
    case 0x2b47e:am_word(r.d[0],(r.d[0]|0xff1fU)&65535U);r.pc=0x2b486;return true; // NOT.W D0; ANDI.W #e0,D0; NOT.W D0.
    // ADDI.W #100,D0; LSR.W #5,D0; MOVE.B D0,7c(A6); MOVE.W 8c(A6),D1; BTST.B #0,15(A6); BEQ.W 2b4a0.
    case 0x2b486:
        am_word(r.d[0],(r.d[0]+0x100U)&65535U);am_word(r.d[0],on28_w(r.d[0])>>5);if(!on28_put(c,r.a[6],0x7c,1,on28_b(r.d[0])))return false;
        if(!on28_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[1],value);
        if(!on28_bit(c,r.a[6],0x15,0,bit))return false;r.pc=bit?0x2b49e:0x2b4a0;return true;
    case 0x2b49e:am_word(r.d[1],(0U-r.d[1])&65535U);r.pc=0x2b4a0;return true; // NEG.W D1.
    // CMPI.W #eb00,D1; BGE.W 2b4b2 / CMPI.W #fb00,D1; BGE.W 2b4c4 / CMPI.W #500,D1; BGT.W 2b4d6 / CMPI.W #1500,D1; BGT.W 2b4e8 (signed).
    case 0x2b4a0:r.pc=on28_signed_w(r.d[1])>=-0x1500?0x2b4b2:0x2b4a8;return true;
    case 0x2b4b2:r.pc=on28_signed_w(r.d[1])>=-0x500?0x2b4c4:0x2b4ba;return true;
    case 0x2b4c4:r.pc=on28_signed_w(r.d[1])>0x500?0x2b4d6:0x2b4cc;return true;
    case 0x2b4d6:r.pc=on28_signed_w(r.d[1])>0x1500?0x2b4e8:0x2b4de;return true;
    // MOVE.B #0..4,7d(A6); BRA.W 2b4ee (2b4e8 falls through).
    case 0x2b4a8:case 0x2b4ba:case 0x2b4cc:case 0x2b4de:case 0x2b4e8:
        value=r.pc==0x2b4a8?0U:(r.pc==0x2b4ba?1U:(r.pc==0x2b4cc?2U:(r.pc==0x2b4de?3U:4U)));
        if(!on28_put(c,r.a[6],0x7d,1,value))return false;r.pc=0x2b4ee;return true;
    case 0x2b4ee:r.pc=(r.d[1]&0x8000U)!=0U?0x2b4f4:0x2b4f8;return true; // TST.W D1; BPL.W 2b4f8.
    case 0x2b4f4:am_word(r.d[1],(r.d[1]+0x1ffU)&65535U);r.pc=0x2b4f8;return true; // ADDI.W #1ff,D1.
    // ASR.W #1,D1; ANDI.W #ff00,D1; MOVEQ #0,D7; (CMPI.W #k,D1; SEQ.B D0; OR.B D0,D7) for k = 1000 500 0 fb00 f000;
    // MOVE.B D7,7e(A6); JMP 49fc6.l.
    case 0x2b4f8: {
        am_word(r.d[1],on28_asr_w(r.d[1],1));am_word(r.d[1],r.d[1]&0xff00U);r.d[7]=0;
        const std::uint32_t keys[5]={0x1000U,0x500U,0U,0xfb00U,0xf000U};
        for(unsigned int i=0;i<5;++i){am_byte(r.d[0],on28_w(r.d[1])==keys[i]?0xffU:0U);am_byte(r.d[7],(r.d[7]|r.d[0])&255U);}
        if(!on28_put(c,r.a[6],0x7e,1,on28_b(r.d[7])))return false;r.pc=0x49fc6;return true;
    }
    // ---- 2b668 (BSR from 2b992, outside 2ce5a): the 2d8b8 pair by BYTE 7c (D1 index), NEG.W D0 when BYTE 15 bit 0 = 1.
    case 0x2b668:return on28_pair(c,r.a[6],false,0x2b686,0x2b688);
    case 0x2b686:case 0x2b6b4:case 0x2b9f8:                              // NEG.W D0.
        am_word(r.d[0],(0U-r.d[0])&65535U);r.pc=r.pc==0x2b686?0x2b688U:(r.pc==0x2b6b4?0x2b6b6U:0x2b9faU);return true;
    case 0x2b688:r.a[0]=0x2b692;r.pc=0x4da50;return true;               // LEA 2b692(PC),A0; JMP 4da50.l.
    // 2b692 (code pointer, 4dbb0 JSR (A1)): MOVEA.L c(A6),A0; the 2d8b8 pair by BYTE 7c(A0), NEG.W D0 when BYTE 15(A0) bit 0 = 1.
    case 0x2b692:if(!on28_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;return on28_pair(c,r.a[0],false,0x2b6b4,0x2b6b6);
    // MOVE.W D0,2e(A6); MOVE.W D1,32(A6); ANDI.B #fe,CCR; RTS.
    case 0x2b6b6:
        if(!on28_put(c,r.a[6],0x2e,2,on28_w(r.d[0])) || !on28_put(c,r.a[6],0x32,2,on28_w(r.d[1])))return false;
        r.carry=AnimationCarryClear;return am_return(c);
    // ---- 2b7ce (BSR from 2b8a6): MOVE.W #f2,20(A6); MOVE.L 20009c.l,22(A6); MOVE.L #2b3d0,9e(A6); MOVE.W #87d,D0; MOVE.B #1,D1;
    // JSR 8ebe.l.
    case 0x2b7ce:
        if(!on28_put(c,r.a[6],0x20,2,0xf2) || !am_read(c,ON28_BANK_F2,4,value) || !on28_put(c,r.a[6],0x22,4,value) ||
           !on28_put(c,r.a[6],0x9e,4,0x2b3d0))return false;
        am_word(r.d[0],0x87d);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x2b7f2);
    case 0x2b7f2:am_word(r.d[0],0x39d);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x2b800); // MOVE.W #39d,D0; MOVE.B #1,D1; JSR 8ebe.l.
    case 0x2b800:am_word(r.d[0],0x87a);am_byte(r.d[1],1);return am_call(c,0x8ebe,0x2b80e); // MOVE.W #87a,D0; MOVE.B #1,D1; JSR 8ebe.l.
    // MOVE.W #8080,8e(A6); BTST.B #0,15(A6); BNE.W 2b860.
    case 0x2b80e:if(!on28_put(c,r.a[6],0x8e,2,0x8080) || !on28_bit(c,r.a[6],0x15,0,bit))return false;r.pc=bit?0x2b860:0x2b81e;return true;
    // MOVEA.L #41fe6,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x2b81e:case 0x2b860:r.a[0]=0x41fe6;am_word(r.d[0],0xa);return am_call(c,0x28ae,r.pc==0x2b81e?0x2b82eU:0x2b870U);
    case 0x2b82e:return on28_carry(c,0x2b85c,0x2b832);                  // BCC.W 2b85c (C returned by 28ae).
    case 0x2b870:return on28_carry(c,0x2b89e,0x2b874);                  // BCC.W 2b89e (C returned by 28ae).
    case 0x2b832:return on28_child(c,0,0x2b85c);
    case 0x2b874:return on28_child(c,4,0x2b89e);
    case 0x2b85c:r.pc=0x2b89e;return true;                               // BRA.W 2b89e.
    case 0x2b89e:case 0x2c8f0:case 0x31000:return am_return(c);          // RTS.
    // ---- stage event callbacks 2b8a0 (BSET.B #0,15(A6), falls into 2b8a6) and 2b8a6 (BSR.W 2b7ce; BRA.W 2b8b6).
    case 0x2b8a0:if(!on28_bset(c,0x15,0,true))return false;r.pc=0x2b8a6;return true;
    case 0x2b8a6:return am_call(c,0x2b7ce,0x2b8aa);
    case 0x2b8aa:r.pc=0x2b8b6;return true;
    // TST.W 76(A6); BNE.W 2b8c4 / JSR 4c0ac.l.
    case 0x2b8b6:if(!on28_get(c,r.a[6],0x76,2,value))return false;r.pc=on28_w(value)!=0U?0x2b8c4:0x2b8be;return true;
    case 0x2b8be:return am_call(c,0x4c0ac,0x2b8c4);
    // MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); MOVE.W #0,8c(A6); JSR 4c37c.l (boundary).
    case 0x2b8c4:
        if(!on28_put(c,r.a[6],0x68,2,0x8810) || !on28_put(c,r.a[6],0x1e,2,0x8810) || !on28_put(c,r.a[6],0x8c,2,0))return false;
        return am_call(c,0x4c37c,0x2b8dc);
    // MOVE.L A0,94(A6); MOVEQ #1,D1; JSR 4d81c.l.
    case 0x2b8dc:if(!on28_put(c,r.a[6],0x94,4,r.a[0]))return false;r.d[1]=1;return am_call(c,0x4d81c,0x2b8e8);
    // MOVE.B D1,83(A6); MOVE.B D2,84(A6); MOVE.W D3,54(A6); MOVE.L #2b96c,(A6); RTS.
    case 0x2b8e8:
        if(!on28_put(c,r.a[6],0x83,1,on28_b(r.d[1])) || !on28_put(c,r.a[6],0x84,1,on28_b(r.d[2])) || !on28_put(c,r.a[6],0x54,2,on28_w(r.d[3])) ||
           !on28_install(c,0x2b96c))return false;
        return am_return(c);
    // ---- 2b96c (installed): MOVE.B 1b(A6),14(A6); MOVE.L #0,98(A6); MOVEA.L #645da,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2b96c:
        if(!on28_copy_b(c,0x1b,0x14) || !on28_put(c,r.a[6],0x98,4,0))return false;r.a[1]=0x645da;am_word(r.d[0],0x100);
        return am_call(c,0x49f8c,0x2b98a);
    case 0x2b98a:if(!on28_put(c,r.a[6],0x64,4,0))return false;return am_call(c,0x2b668,0x2b996); // MOVE.L #0,64(A6); BSR.W 2b668.
    case 0x2b996:if(!on28_install(c,0x2b99c))return false;r.pc=0x2b99c;return true; // MOVE.L #2b99c,(A6) (falls through).
    // 2b99c (installed): TST.W 54(A6); BEQ.W 2c7fe / BTST.B #7,61(A6); BNE.W 2ca68.
    case 0x2b99c:if(!on28_get(c,r.a[6],0x54,2,value))return false;r.pc=on28_w(value)==0U?0x2c7fe:0x2b9a4;return true;
    case 0x2b9a4:if(!on28_bit(c,r.a[6],0x61,7,bit))return false;r.pc=bit?0x2ca68:0x2b9ae;return true;
    // MOVE.B #0,5e(A6); MOVE.B #8,86(A6); BSR.W 2c760.
    case 0x2b9ae:if(!on28_put(c,r.a[6],0x5e,1,0) || !on28_put(c,r.a[6],0x86,1,8))return false;return am_call(c,0x2c760,0x2b9be);
    case 0x2b9be:return am_call(c,0x2b418,0x2b9c2);                     // JSR 2b418(PC).
    case 0x2b9c2:r.a[0]=0x2b6ce;return am_call(c,0x1aa7e,0x2b9cc);      // LEA 2b6ce(PC),A0; JSR 1aa7e.l.
    case 0x2b9cc:return on28_carry(c,0x2b9d6,0x2b9d0);                  // BCC.W 2b9d6 (C returned by 1aa7e).
    case 0x2b9d0:case 0x2cb2a:r.pc=0x2a00;return true;                   // JMP 2a00.l.
    // LEA 2b6d6(PC),A0; the 2d8b8 pair by BYTE 7c (D0 index), NEG.W D0 when BYTE 15 bit 0 = 1.
    case 0x2b9d6:r.a[0]=0x2b6d6;return on28_pair(c,r.a[6],true,0x2b9f8,0x2b9fa);
    // MOVE.W 42(A6),-(A7); MOVE.W 46(A6),-(A7); ADD.W D0,42(A6); ADD.W D1,46(A6); JSR 4d2d4.l.
    case 0x2b9fa:
        if(!on28_get(c,r.a[6],0x42,2,value) || !am_push(c,2,value) || !on28_get(c,r.a[6],0x46,2,value) || !am_push(c,2,value))return false;
        if(!on28_get(c,r.a[6],0x42,2,value) || !on28_put(c,r.a[6],0x42,2,(value+r.d[0])&65535U))return false;
        if(!on28_get(c,r.a[6],0x46,2,value) || !on28_put(c,r.a[6],0x46,2,(value+r.d[1])&65535U))return false;
        return am_call(c,0x4d2d4,0x2ba10);
    case 0x2ba10:return on28_carry(c,0x2ba44,0x2ba14);                  // BCC.W 2ba44 (C returned by 4d2d4).
    // MOVE.W D0,88(A6); BSR.W 2b63e (boundary).
    case 0x2ba14:if(!on28_put(c,r.a[6],0x88,2,on28_w(r.d[0])))return false;return am_call(c,0x2b63e,0x2ba1c);
    case 0x2ba1c:return on28_carry(c,0x2ba44,0x2ba20);                  // BCC.W 2ba44 (C returned by 2b63e).
    // MOVE.W D0,8a(A6); MOVE.W 88(A6),D0; MOVE.B #1,D1; MOVE.B 83(A6),D2; MOVE.B 84(A6),D3; MOVE.W 54(A6),D4; JSR 4d508.l.
    case 0x2ba20:
        if(!on28_put(c,r.a[6],0x8a,2,on28_w(r.d[0])) || !on28_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],1);
        if(!on28_get(c,r.a[6],0x83,1,value))return false;am_byte(r.d[2],value);if(!on28_get(c,r.a[6],0x84,1,value))return false;am_byte(r.d[3],value);
        if(!on28_get(c,r.a[6],0x54,2,value))return false;am_word(r.d[4],value);return am_call(c,0x4d508,0x2ba3e);
    case 0x2ba3e:if(!on28_install(c,0x2ba50))return false;r.pc=0x2ba44;return true; // MOVE.L #2ba50,(A6).
    // MOVE.W (A7)+,46(A6); MOVE.W (A7)+,42(A6); BRA.W 2c8ca.
    case 0x2ba44:
        if(!am_pop(c,2,value) || !on28_put(c,r.a[6],0x46,2,value) || !am_pop(c,2,value) || !on28_put(c,r.a[6],0x42,2,value))return false;
        r.pc=0x2c8ca;return true;
    // ---- 2c760 (BSR from 2b9ba 2c8b0, outside 2c9f2): MOVEA.L 94(A6),A0; BTST.B #7,15(A6); BEQ.W 2c77a / JSR 4c3de.l (boundary).
    case 0x2c760:
        if(!on28_get(c,r.a[6],0x94,4,value))return false;r.a[0]=value;if(!on28_bit(c,r.a[6],0x15,7,bit))return false;
        r.pc=bit?0x2c76e:0x2c77a;return true;
    case 0x2c76e:return am_call(c,0x4c3de,0x2c774);
    case 0x2c774:case 0x2c7a0:if(!on28_put(c,r.a[6],0x8c,2,on28_w(r.d[0])))return false;return am_return(c); // MOVE.W D0,8c(A6); RTS.
    // MOVE.L 64(A6),36(A6); MOVEA.L 9e(A6),A4; MOVE.L 10(A4),D0; SUB.L 3a(A6),D0; MOVEA.L 9e(A6),A4; MOVE.W 6(A4),D1; ASR.L D1,D0
    // (count D1 mod 64); ADD.L D0,3a(A6); JSR 4c3a2.l (boundary).
    case 0x2c77a:
        if(!on28_get(c,r.a[6],0x64,4,value) || !on28_put(c,r.a[6],0x36,4,value) || !on28_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;
        if(!on28_get(c,r.a[4],0x10,4,value))return false;r.d[0]=value;if(!on28_get(c,r.a[6],0x3a,4,value))return false;r.d[0]-=value;
        if(!on28_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;if(!on28_get(c,r.a[4],6,2,value))return false;am_word(r.d[1],value);
        r.d[0]=on28_asr_l(r.d[0],r.d[1]&63U);
        if(!on28_get(c,r.a[6],0x3a,4,value) || !on28_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;return am_call(c,0x4c3a2,0x2c7a0);
    // ---- 2c7fe (2b99c BEQ, outside install 2c456): MOVE.W #1ac8,D0; JSR 3af8.l.
    case 0x2c7fe:am_word(r.d[0],0x1ac8);return am_call(c,0x3af8,0x2c808);
    case 0x2c808:r.a[1]=0x65f56;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x2c818); // MOVEA.L #65f56,A1; MOVE.W #100,D0; JSR 49f8c.l.
    // MOVE.L #2c7a6,98(A6); MOVEQ #0,D0; MOVE.W #38,D1; JSR 4db18.l (boundary).
    case 0x2c818:if(!on28_put(c,r.a[6],0x98,4,0x2c7a6))return false;r.d[0]=0;am_word(r.d[1],0x38);return am_call(c,0x4db18,0x2c82c);
    // MOVE.W #60,92(A6); MOVE.L #2c838,(A6) (falls through).
    case 0x2c82c:if(!on28_put(c,r.a[6],0x92,2,0x60) || !on28_install(c,0x2c838))return false;r.pc=0x2c838;return true;
    // 2c838 (installed): MOVEA.L 98(A6),A0; CMPA.W #0,A0; BEQ.W 2c866.
    case 0x2c838:if(!on28_get(c,r.a[6],0x98,4,value))return false;r.a[0]=value;r.pc=r.a[0]==0U?0x2c866:0x2c844;return true;
    // MOVE.B 1a(A6),14(A6); MOVE.W (A0)+,D1; CMPI.W #ffff,D1; BNE.W 2c858.
    case 0x2c844:
        if(!on28_copy_b(c,0x1a,0x14) || !am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);r.a[0]+=2U;
        r.pc=on28_w(r.d[1])!=0xffffU?0x2c858:0x2c854;return true;
    // ADDA.W (A0),A0; MOVE.W (A0)+,D1.
    case 0x2c854:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]=am_index(r.a[0],value);if(!am_read(c,r.a[0],2,value))return false;
        am_word(r.d[1],value);r.a[0]+=2U;r.pc=0x2c858;return true;
    // MOVE.L A0,98(A6); MOVE.B 14(A6),D0; JSR 8d34.l (boundary).
    case 0x2c858:
        if(!on28_put(c,r.a[6],0x98,4,r.a[0]) || !on28_get(c,r.a[6],0x14,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x8d34,0x2c866);
    // CLR.L 64(A6); MOVE.B #ff,86(A6); MOVE.W 88(A6),D0; BMI.W 2c8b0.
    case 0x2c866:
        if(!on28_put(c,r.a[6],0x64,4,0) || !on28_put(c,r.a[6],0x86,1,0xff) || !on28_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);
        r.pc=(value&0x8000U)!=0U?0x2c8b0:0x2c878;return true;
    case 0x2c878:if(!on28_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49be0,0x2c882); // MOVE.W 88(A6),D0; JSR 49be0.l.
    // MOVE.W (A0),D0; BTST.B #5,D0 (register: LONG bit 5); BEQ.W 2c89a.
    case 0x2c882:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.pc=(r.d[0]&0x20U)==0U?0x2c89a:0x2c88c;return true;
    // MOVE.B #1,D1; MOVE.W 88(A6),D0; JSR 4d4b4.l (boundary).
    case 0x2c88c:am_byte(r.d[1],1);if(!on28_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4d4b4,0x2c89a);
    case 0x2c89a:return am_call(c,0x2b63e,0x2c89e);                     // BSR.W 2b63e (boundary).
    case 0x2c89e:return on28_carry(c,0x2c8a2,0x2c8a8);                  // BCS.W 2c8a8 (C returned by 2b63e).
    case 0x2c8a2:if(!on28_put(c,r.a[6],0x88,2,0xffff))return false;r.pc=0x2c8a8;return true; // MOVE.W #ffff,88(A6).
    case 0x2c8a8:return am_call(c,0x2c71a,0x2c8ac);                     // BSR.W 2c71a (boundary).
    case 0x2c8ac:case 0x2c8c6:r.pc=r.pc==0x2c8ac?0x2c8b4U:0x2c8caU;return true; // BRA.W.
    case 0x2c8b0:return am_call(c,0x2c760,0x2c8b4);                     // BSR.W 2c760.
    case 0x2c8b4:return am_call(c,0x2b418,0x2c8b8);                     // BSR.W 2b418.
    // SUBQ.W #1,92(A6); BPL.W 2c8c6.
    case 0x2c8b8:
        if(!on28_get(c,r.a[6],0x92,2,value))return false;other=(value+0xffffU)&65535U;if(!on28_put(c,r.a[6],0x92,2,other))return false;
        r.pc=(other&0x8000U)==0U?0x2c8c6:0x2c8c0;return true;
    case 0x2c8c0:if(!on28_install(c,0x2ca68))return false;r.pc=0x2c8c6;return true; // MOVE.L #2ca68,(A6).
    // ---- 2c8ca (shared tail): CMPI.W #8000,8e(A6); BEQ.W 2c8f0.
    case 0x2c8ca:if(!on28_get(c,r.a[6],0x8e,2,value))return false;r.pc=on28_w(value)==0x8000U?0x2c8f0:0x2c8d4;return true;
    // MOVEA.L 78(A6),A0; MOVE.B (A0)+,D0; MOVE.B (A0)+,D1; BTST.B #0,15(A6); BEQ.W 2c8e8.
    case 0x2c8d4:
        if(!on28_get(c,r.a[6],0x78,4,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[0],value);r.a[0]+=1U;
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[1],value);r.a[0]+=1U;
        if(!on28_bit(c,r.a[6],0x15,0,bit))return false;r.pc=bit?0x2c8e6:0x2c8e8;return true;
    case 0x2c8e6:am_byte(r.d[0],(0U-r.d[0])&255U);r.pc=0x2c8e8;return true; // NEG.B D0.
    // MOVE.B D0,8e(A6); MOVE.B D1,8f(A6).
    case 0x2c8e8:if(!on28_put(c,r.a[6],0x8e,1,on28_b(r.d[0])) || !on28_put(c,r.a[6],0x8f,1,on28_b(r.d[1])))return false;r.pc=0x2c8f0;return true;
    // ---- 2ca68 (2b9a4 BNE, installs 2c8c0 / outside 2c68a): MOVE.W #18de,D0; JSR 3af8.l.
    case 0x2ca68:am_word(r.d[0],0x18de);return am_call(c,0x3af8,0x2ca72);
    case 0x2ca72:r.a[0]=0x2c94c;return am_call(c,0x4ae4a,0x2ca7c);      // LEA 2c94c(PC),A0; JSR 4ae4a.l.
    // MOVE.B #0,D1; MOVE.W 88(A6),D0; MOVE.B #7,5e(A6); JSR 4d4b4.l (boundary).
    case 0x2ca7c:
        am_byte(r.d[1],0);if(!on28_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);if(!on28_put(c,r.a[6],0x5e,1,7))return false;
        return am_call(c,0x4d4b4,0x2ca90);
    case 0x2ca90:r.d[0]=1;r.d[1]=0;return am_call(c,0x4ff96,0x2ca9a);   // MOVEQ #1,D0; MOVEQ #0,D1; JSR 4ff96.l (boundary).
    case 0x2ca9a:return am_call(c,0xd3d7c,0x2caa0);                     // JSR d3d7c.l (boundary).
    case 0x2caa0:if(!on28_spark(c,0xfff20000U,0x280000U,0xa))return false;return am_call(c,0xd3d7c,0x2cabc);
    case 0x2cabc:if(!on28_spark(c,0xa0000U,0x250000U,7))return false;return am_call(c,0xd3d7c,0x2cad8);
    case 0x2cad8:if(!on28_spark(c,0xfff70000U,0x10000U,7))return false;return am_call(c,0xd3d7c,0x2caf4);
    // MOVE.L #70000,36(A0); MOVE.L #fffc0000,3a(A0); MOVE.W #5,54(A0); MOVEA.L #2cb30,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0x2caf4:
        if(!on28_spark(c,0x70000U,0xfffc0000U,5))return false;r.a[0]=0x2cb30;am_word(r.d[0],0x1e);r.a[1]=0x100bf4;return am_call(c,0x2986,0x2cb20);
    case 0x2cb20:r.d[0]=0;r.d[1]=0x10;return am_call(c,0x49214,0x2cb2a); // MOVEQ #0,D0; MOVEQ #10,D1; JSR 49214.l.
    // ---- stage event callback 306a8: JSR 318d8(PC) (boundary); MOVE.L #30718,(A6); RTS.
    case 0x306a8:return am_call(c,0x318d8,0x306ac);
    case 0x306ac:if(!on28_install(c,0x30718))return false;return am_return(c);
    // ---- 30718 (installed): MOVEA.L #31d6e,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x30718:r.a[1]=0x31d6e;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x30728);
    // MOVE.B 1b(A6),14(A6); MOVE.L #0,76(A6); MOVE.L #0,56(A6); MOVEQ #8,D0; MOVEQ #28,D1; JSR 4da4a.l.
    case 0x30728:
        if(!on28_copy_b(c,0x1b,0x14) || !on28_put(c,r.a[6],0x76,4,0) || !on28_put(c,r.a[6],0x56,4,0))return false;r.d[0]=8;r.d[1]=0x28;
        return am_call(c,0x4da4a,0x30748);
    case 0x30748:return am_call(c,0x496c2,0x3074e);                     // JSR 496c2.l.
    // MOVE.B #ff,94(A6); MOVE.L #3075a,(A6) (falls through).
    case 0x3074e:if(!on28_put(c,r.a[6],0x94,1,0xff) || !on28_install(c,0x3075a))return false;r.pc=0x3075a;return true;
    case 0x3075a:return am_call(c,0x316b2,0x3075e);                     // 3075a (installed): JSR 316b2(PC) (boundary).
    case 0x3075e:r.a[0]=0x31ad4;return am_call(c,0x1aa7e,0x3076a);      // LEA 31ad4.l,A0; JSR 1aa7e.l.
    case 0x3076a:return on28_carry(c,0x30774,0x3076e);                  // BCC.W 30774 (C returned by 1aa7e).
    case 0x3076e:if(!on28_install(c,0x31002))return false;r.pc=0x30774;return true; // MOVE.L #31002,(A6).
    case 0x30774:return am_call(c,0x3165e,0x30778);                     // JSR 3165e(PC) (boundary).
    case 0x30778:r.a[0]=0x31ae4;return am_call(c,0x4d2d4,0x30784);      // LEA 31ae4.l,A0; JSR 4d2d4.l.
    case 0x30784:return on28_carry(c,0x307d6,0x30788);                  // BCC.W 307d6 (C returned by 4d2d4).
    // MOVE.W D0,84(A6); JSR 319f6(PC) (boundary).
    case 0x30788:if(!on28_put(c,r.a[6],0x84,2,on28_w(r.d[0])))return false;return am_call(c,0x319f6,0x30790);
    case 0x30790:return on28_carry(c,0x307d6,0x30794);                  // BCC.W 307d6 (C returned by 319f6).
    // MOVE.W 84(A6),D0; MOVE.B #9,D1; MOVE.B 99(A6),D2; MOVE.B 9a(A6),D3; MOVE.W 54(A6),D4; JSR 4d508.l.
    case 0x30794:
        if(!on28_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],9);
        if(!on28_get(c,r.a[6],0x99,1,value))return false;am_byte(r.d[2],value);if(!on28_get(c,r.a[6],0x9a,1,value))return false;am_byte(r.d[3],value);
        if(!on28_get(c,r.a[6],0x54,2,value))return false;am_word(r.d[4],value);return am_call(c,0x4d508,0x307ae);
    // MOVE.L #307da,(A6); TST.W 92(A6); BMI.W 307d6.
    case 0x307ae:
        if(!on28_install(c,0x307da) || !on28_get(c,r.a[6],0x92,2,value))return false;r.pc=(value&0x8000U)!=0U?0x307d6:0x307bc;return true;
    case 0x307bc:return am_call(c,0x48296,0x307c2);                     // JSR 48296.l.
    case 0x307c2:r.d[0]=0;return am_call(c,0x49c66,0x307ca);            // MOVEQ #0,D0; JSR 49c66.l.
    case 0x307ca:r.d[0]=1;return am_call(c,0x49c66,0x307d2);            // MOVEQ #1,D0; JSR 49c66.l.
    case 0x307d2:if(!on28_put(c,r.a[5],0x5c8d,1,0xff))return false;r.pc=0x307d6;return true; // ST.B 5c8d(A5).
    case 0x307d6:r.pc=0x30ed2;return true;                               // BRA.W 30ed2.
    case 0x30ed2:r.pc=0x30f84;return true;                               // BRA.W 30f84.
    // ---- 30f84 (tail): JSR 4b54e.l.
    case 0x30f84:return am_call(c,0x4b54e,0x30f8a);
    // BTST.B #7,61(A6); SNE.B D0; BEQ.W 30f9c.
    case 0x30f8a:if(!on28_bit(c,r.a[6],0x61,7,bit))return false;am_byte(r.d[0],bit?0xffU:0U);r.pc=bit?0x30f96:0x30f9c;return true;
    case 0x30f96:if(!on28_install(c,0x30b6c))return false;r.pc=0x30f9c;return true; // MOVE.L #30b6c,(A6).
    // AND.B D0,5e(A6); BCLR.B #6,61(A6); TST.W 88(A6); BEQ.W 30fb8.
    case 0x30f9c:
        if(!on28_get(c,r.a[6],0x5e,1,value) || !on28_put(c,r.a[6],0x5e,1,(value&r.d[0])&255U) || !on28_bset(c,0x61,6,false) ||
           !on28_get(c,r.a[6],0x88,2,value))return false;
        r.pc=on28_w(value)==0U?0x30fb8:0x30fae;return true;
    // SUBQ.W #1,88(A6); BSET.B #6,61(A6).
    case 0x30fae:
        if(!on28_get(c,r.a[6],0x88,2,value) || !on28_put(c,r.a[6],0x88,2,(value+0xffffU)&65535U) || !on28_bset(c,0x61,6,true))return false;
        r.pc=0x30fb8;return true;
    case 0x30fb8:return am_call(c,0x4d766,0x30fbe);                     // JSR 4d766.l.
    case 0x30fbe:return on28_carry(c,0x30fc8,0x30fc2);                  // BCC.W 30fc8 (C returned by 4d766).
    case 0x30fc2:if(!on28_bset(c,0x61,6,true))return false;r.pc=0x30fc8;return true; // BSET.B #6,61(A6).
    case 0x30fc8:if(!on28_get(c,r.a[6],0x76,4,value))return false;r.pc=value==0U?0x30fe4:0x30fd0;return true; // TST.L 76(A6); BEQ.W 30fe4.
    case 0x30fd0:if(!on28_copy_b(c,0x1a,0x14))return false;return am_call(c,0x318b8,0x30fda); // MOVE.B 1a(A6),14(A6); JSR 318b8(PC) (boundary).
    case 0x30fda:if(!on28_bset(c,0x61,6,true))return false;r.pc=0x31000;return true; // BSET.B #6,61(A6); BRA.W 31000.
    // MOVE.B 1b(A6),14(A6); MOVE.W 88(A6),D0; ANDI.W #1,D0; BEQ.W 31000.
    case 0x30fe4:
        if(!on28_copy_b(c,0x1b,0x14) || !on28_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value&1U);
        r.pc=on28_w(r.d[0])==0U?0x31000:0x30ff6;return true;
    // MOVE.B 19(A6),14(A6); ST.B 8c(A6).
    case 0x30ff6:if(!on28_copy_b(c,0x19,0x14) || !on28_put(c,r.a[6],0x8c,1,0xff))return false;r.pc=0x31000;return true;
    default:return am_error(c,"unsupported animation objects n28 PC");
    }
}
}
