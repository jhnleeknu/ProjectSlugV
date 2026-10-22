#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr8_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ofr8_b(std::uint32_t value) {return value&255U;}
// Signed value of the low WORD (CMP.W + BLT, CMPI.W #0 + BGT).
int ofr8_sw(std::uint32_t value) {const int v=static_cast<int>(value&65535U);return v>=32768?v-65536:v;}
bool ofr8_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr8_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BSET.B / BCLR.B / BCHG.B #bit,d(An): read-modify-write of one BYTE (mode 0 clear, 1 set, 2 change).
bool ofr8_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int mode) {
    std::uint32_t value=0;if(!ofr8_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;
    const std::uint32_t out=mode==1U?(value|mask):(mode==0U?(value&~mask):(value^mask));
    return ofr8_put(c,base,displacement,1,out);
}
// BTST.B #bit,d(An); BEQ zero_pc (bit clear) / one_pc (bit set).
bool ofr8_btst(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    std::uint32_t value=0;if(!ofr8_get(c,base,displacement,1,value))return false;
    c.s.pc=(value&(1U<<bit))==0U?zero_pc:one_pc;return true;
}
// BTST.B #bit,D0 (register form: bit of the LONG); BNE one_pc / zero_pc.
void ofr8_dbit(AnimationMachineContext& c,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    c.s.pc=(c.s.d[0]&(1U<<bit))==0U?zero_pc:one_pc;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool ofr8_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr8 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ADD.W / SUB.W d(An) with a WORD: WORD field += addend (modulo 2^16).
bool ofr8_add_word(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t addend) {
    std::uint32_t value=0;if(!ofr8_get(c,base,displacement,2,value))return false;return ofr8_put(c,base,displacement,2,value+addend);
}
// 42ef4 / 42f18 / 42f38 / 42f52: ANDI.W #f,D0; SUBQ.W #7,D0; ADD.W D0,field(A6).
bool ofr8_jitter(AnimationMachineContext& c,std::uint32_t field) {
    AnimationMachineState& r=c.s;am_word(r.d[0],r.d[0]&0xfU);am_word(r.d[0],r.d[0]-7U);return ofr8_add_word(c,r.a[6],field,r.d[0]);
}
// MOVE.B 76(A6),D0; BTST.B #5,D0; BEQ.W zero_pc / one_pc (42e0c-style tail of the angle splits).
bool ofr8_angle(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t one_pc) {
    std::uint32_t value=0;if(!ofr8_get(c,c.s.a[6],0x76,1,value))return false;am_byte(c.s.d[0],value);
    c.s.pc=(c.s.d[0]&0x20U)==0U?zero_pc:one_pc;return true;
}
// 42e0c / 43030: MOVE.L D0,36(A6); MOVE.L D1,3a(A6); then the angle test.
bool ofr8_speed(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t one_pc) {
    AnimationMachineState& r=c.s;
    if(!ofr8_put(c,r.a[6],0x36,4,r.d[0]) || !ofr8_put(c,r.a[6],0x3a,4,r.d[1]))return false;return ofr8_angle(c,zero_pc,one_pc);
}
// 42e24 / 43048: LSR.W #4,D0; ANDI.W #f,D0; MOVE.B D0,8c(A6); then the angle test.
bool ofr8_split16(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t one_pc) {
    AnimationMachineState& r=c.s;am_word(r.d[0],ofr8_w(r.d[0])>>4);am_word(r.d[0],r.d[0]&0xfU);
    if(!ofr8_put(c,r.a[6],0x8c,1,r.d[0]))return false;return ofr8_angle(c,zero_pc,one_pc);
}
// 42e54 / 43060: LSR.W #2,D0; ANDI.W #3f,D0; MOVE.B D0,8e(A6).
bool ofr8_split64(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;am_word(r.d[0],ofr8_w(r.d[0])>>2);am_word(r.d[0],r.d[0]&0x3fU);return ofr8_put(c,r.a[6],0x8e,1,r.d[0]);
}
// 43060 / 430ba tail: MOVEA.L #430e6,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
bool ofr8_shard(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;r.a[0]=0x430e6;am_word(r.d[0],0x1e);r.a[1]=0x100bf4;return am_call(c,0x2986,return_pc);
}
// 43080 / 430d0: MOVE.L 7c(A6),7c(A0); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.l.
bool ofr8_shard_link(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr8_get(c,r.a[6],0x7c,4,value) || !ofr8_put(c,r.a[0],0x7c,4,value))return false;r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,return_pc);
}
// cdc2c..cdcce: MOVE.W 8a(A6),20(A6); MOVEA.L #anim,A1; MOVE.W #100,D0; JSR 49f8c.l.
bool ofr8_kind(AnimationMachineContext& c,std::uint32_t anim,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr8_get(c,r.a[6],0x8a,2,value) || !ofr8_put(c,r.a[6],0x20,2,value))return false;r.a[1]=anim;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// ae960 / ae9bc: MOVEA.L #d1d38,A0; MOVE.W #1e,D0; JSR 28ae.l.
bool ofr8_child_d1d38(AnimationMachineContext& c,std::uint32_t return_pc) {c.s.a[0]=0xd1d38;am_word(c.s.d[0],0x1e);return am_call(c,0x28ae,return_pc);}
// ae986 / ae9d6: MOVE.W #e0ed,68(A0); MOVE.W #e0ed,1e(A0); ADDI.W #offset,32(A6); JSR 43e34.l.
bool ofr8_child_place(AnimationMachineContext& c,std::uint32_t offset,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;
    if(!ofr8_put(c,r.a[0],0x68,2,0xe0ed) || !ofr8_put(c,r.a[0],0x1e,2,0xe0ed) || !ofr8_add_word(c,r.a[6],0x32,offset))return false;
    return am_call(c,0x43e34,return_pc);
}
// d384a / d386c: MOVEA.L 96(A6),A1; ADD.W field(A1),D0; BTST.B #bit,15(A6); BEQ.W zero_pc / NEG.W one_pc.
bool ofr8_offset(AnimationMachineContext& c,std::uint32_t field,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr8_get(c,r.a[6],0x96,4,r.a[1]) || !ofr8_get(c,r.a[1],field,2,value))return false;am_word(r.d[0],r.d[0]+value);
    return ofr8_btst(c,r.a[6],0x15,bit,zero_pc,one_pc);
}
}
// Objects FR8 (229 block starts, contract docs/analysis/animation-machine-frontier-fr8-contract.md): the C-gated area-D roots after FR7 except the
// af990 family (FR9) -- the object 42d9c (2986 child of B2e 3ac60; install 42e68) with the computed jump 42f9a (9-entry BRA.W table 42fa2..42fc2,
// every entry a block start here) and the shard tail 430ba, the emitter object d3500 (28ae child of the helper d3802; install d3554) with d383c, the
// object cdc24 (FR4 cdc1c install; BRA cdd2e FR7), the object 38e92 (N32 / N32b install; installs 38eb4 38ece 38ee2 38f08), the object aea38 (LONG
// table e8eac) with the state machine ae930 (installs aeab0 aeb32) and the child helpers d39f6 / d3a2e, and the FR4 table entry cc7b4.  No TRAP, no
// JSR (An); every exit is a routed block start.  MOVE.L #v,(A6) enters v only when v is the next PC (or the BRA target 42e68); 4313a 4309a aec04
// aeb4c are written only.  The 6 consumers 38fb4 (3a4da), ae936 (4b54e), aea22 (1ab02), cdd0c (497a6), d3814 d3a4c (28ae) read a known C or fail;
// d3822 / d3a5a (ORI.B #1,CCR) set C without a reader.  Data through the live bus (no limit test).
bool animation_objects_fr8_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    case 0x42ec6:case 0xaea36:case 0xaeb4a:case 0xd357e:case 0xd3a36:case 0xd3a6e:
        return am_return(c);                                                                              // RTS.
    case 0x42eaa:case 0x42ec0:case 0x430e0:case 0xd3546:case 0xd3578:
        r.pc=0x2a00;return true;                                                                          // JMP 2a00.l.
    // ---- 38e92 (N32 / N32b install): MOVE.B #0,95(A6); CLR.L 64(A6); TST.B 99(A6); BNE.W 38ed2.
    case 0x38e92:
        if(!ofr8_put(c,r.a[6],0x95,1,0) || !ofr8_put(c,r.a[6],0x64,4,0) || !ofr8_get(c,r.a[6],0x99,1,value))return false;
        r.pc=value!=0U?0x38ed2:0x38ea4;return true;
    case 0x38ea4:r.a[0]=0x3b8b2;return am_call(c,0x3b302,0x38eae);                                         // MOVEA.L #3b8b2,A0; JSR 3b302(PC).
    case 0x38eae:if(!ofr8_put(c,r.a[6],0,4,0x38eb4))return false;r.pc=0x38eb4;return true;                // MOVE.L #38eb4,(A6) (next PC).
    case 0x38eb4:if(!ofr8_get(c,r.a[6],0x99,1,value))return false;r.pc=value!=0U?0x38e92:0x38eba;return true; // TST.B 99(A6); BNE.B 38e92.
    case 0x38eba:case 0x38ece:case 0x38ee8:case 0x38f08:r.pc=0x38f14;return true;                         // BRA.W 38f14.
    case 0x38ebe:r.a[0]=0x3b8b8;return am_call(c,0x3b302,0x38ec8);                                         // MOVEA.L #3b8b8,A0; JSR 3b302(PC).
    case 0x38ec8:if(!ofr8_put(c,r.a[6],0,4,0x38ece))return false;r.pc=0x38ece;return true;                // MOVE.L #38ece,(A6) (next PC).
    case 0x38ed2:r.a[0]=0x3b8be;return am_call(c,0x3b302,0x38edc);                                         // MOVEA.L #3b8be,A0; JSR 3b302(PC).
    case 0x38edc:if(!ofr8_put(c,r.a[6],0,4,0x38ee2))return false;r.pc=0x38ee2;return true;                // MOVE.L #38ee2,(A6) (next PC).
    case 0x38ee2:if(!ofr8_get(c,r.a[6],0x99,1,value))return false;r.pc=value==0U?0x38e92:0x38ee8;return true; // TST.B 99(A6); BEQ.B 38e92.
    // LEA 38f0c(PC),A0; MOVEQ #0,D0; MOVE.B 99(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A0,D0.W),A0; JSR 3b302(PC).
    case 0x38eec:
        r.a[0]=0x38f0c;r.d[0]=0;if(!ofr8_get(c,r.a[6],0x99,1,value))return false;am_byte(r.d[0],value);
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;
        r.a[0]=value;return am_call(c,0x3b302,0x38f02);
    case 0x38f02:if(!ofr8_put(c,r.a[6],0,4,0x38f08))return false;r.pc=0x38f08;return true;                // MOVE.L #38f08,(A6) (next PC).
    case 0x38f14:return ofr8_btst(c,r.a[6],0x15,7,0x398be,0x38f1e);                                       // BTST.B #7,15(A6); BEQ.W 398be.
    case 0x38f1e:return am_call(c,0x3b424,0x38f22);                                                        // JSR 3b424(PC).
    case 0x38f22:ofr8_dbit(c,7,0x38f2a,0x39db4);return true;                                               // BTST.B #7,D0; BNE.W 39db4.
    case 0x38f2a:ofr8_dbit(c,1,0x38f3c,0x38f32);return true;                                               // BTST.B #1,D0; BEQ.W 38f3c.
    case 0x38f32:return ofr8_btst(c,r.a[6],0x15,7,0x38f3c,0x39156);                                       // BTST.B #7,15(A6); BNE.W 39156.
    case 0x38f3c:ofr8_dbit(c,1,0x38f44,0x38f56);return true;                                               // BTST.B #1,D0; BNE.W 38f56.
    case 0x38f44:if(!ofr8_get(c,r.a[6],0x9f,1,value))return false;r.pc=value==0U?0x38f56:0x38f4c;return true; // TST.B 9f(A6); BEQ.W 38f56.
    case 0x38f4c:return ofr8_btst(c,r.a[6],0x15,7,0x38f56,0x38ff4);                                       // BTST.B #7,15(A6); BNE.W 38ff4.
    case 0x38f56:ofr8_dbit(c,5,0x38f5e,0x3976a);return true;                                               // BTST.B #5,D0; BNE.W 3976a.
    case 0x38f5e:ofr8_dbit(c,2,0x38f66,0x395dc);return true;                                               // BTST.B #2,D0; BNE.W 395dc.
    case 0x38f66:ofr8_dbit(c,3,0x38f6e,0x395f8);return true;                                               // BTST.B #3,D0; BNE.W 395f8.
    case 0x38f6e:return ofr8_btst(c,r.a[6],0x94,2,0x38f78,0x38f98);                                       // BTST.B #2,94(A6); BNE.W 38f98.
    case 0x38f78:return ofr8_btst(c,r.a[6],0x9d,4,0x38f98,0x38f82);                                       // BTST.B #4,9d(A6); BEQ.W 38f98.
    case 0x38f82:if(!am_push(c,4,r.d[0]))return false;r.a[0]=0x3b756;return am_call(c,0x4ae4a,0x38f8e);  // MOVE.L D0,-(A7); LEA 3b756(PC),A0; JSR 4ae4a.l.
    // TST.W D0; MOVEM.L (A7)+,D0 (no flag change); BNE.W 39b72 on the TST.
    case 0x38f8e:{const bool zero=ofr8_w(r.d[0])==0U;if(!am_pop(c,4,value))return false;r.d[0]=value;r.pc=zero?0x38f98:0x39b72;return true;}
    case 0x38f98:return ofr8_btst(c,r.a[6],0x9d,6,0x38fbc,0x38fa2);                                       // BTST.B #6,9d(A6); BEQ.W 38fbc.
    // MOVE.L D0,-(A7); ANDI.B #bf,9d(A6); ANDI.B #bf,9e(A6); JSR 3a4da(PC).
    case 0x38fa2:
        if(!am_push(c,4,r.d[0]) || !ofr8_bit(c,r.a[6],0x9d,6,0) || !ofr8_bit(c,r.a[6],0x9e,6,0))return false;return am_call(c,0x3a4da,0x38fb4);
    // MOVEM.L (A7)+,D0; BCS.W 39076 (C returned by 3a4da; MOVEM keeps the flags).
    case 0x38fb4:if(!am_pop(c,4,value))return false;r.d[0]=value;return ofr8_carry(c,0x38fbc,0x39076);
    case 0x38fbc:if(!ofr8_get(c,r.a[6],0x82,4,r.a[0]))return false;return am_call(c,0x3a5be,0x38fc4);      // MOVEA.L 82(A6),A0; JSR 3a5be(PC).
    // MOVE.B 97(A6),D0; CMPI.B #0,D0; BEQ.W 38eec / CMPI.B #2 -> 38ebe / #3, #4 -> 38e92.
    case 0x38fc4:if(!ofr8_get(c,r.a[6],0x97,1,value))return false;am_byte(r.d[0],value);r.pc=ofr8_b(r.d[0])==0U?0x38eec:0x38fd0;return true;
    case 0x38fd0:r.pc=ofr8_b(r.d[0])==2U?0x38ebe:0x38fd8;return true;
    case 0x38fd8:r.pc=ofr8_b(r.d[0])==3U?0x38e92:0x38fe0;return true;
    case 0x38fe0:r.pc=ofr8_b(r.d[0])==4U?0x38e92:0x38fe8;return true;
    case 0x38fe8:return am_call(c,0x3b288,0x38fec);                                                        // JSR 3b288(PC).
    case 0x38fec:return am_call(c,0x3b334,0x38ff0);                                                        // JSR 3b334(PC).
    case 0x38ff0:r.pc=0x3a350;return true;                                                                 // BRA.W 3a350.
    // ---- 42d9c (2986 child of B2e 3ac60): MOVE.W #1a65,D0; BSR.W 4356e.
    case 0x42d9c:am_word(r.d[0],0x1a65);return am_call(c,0x4356e,0x42da4);
    // MOVE.L #6f364,7c(A6); MOVE.L #100000,78(A6); MOVE.W #2a,20(A6); MOVE.L 200038.l,22(A6) (bank window); MOVEA.L #43942,A1; MOVE.W #100,D0;
    // JSR 49f8c.l.
    case 0x42da4:
        if(!ofr8_put(c,r.a[6],0x7c,4,0x6f364) || !ofr8_put(c,r.a[6],0x78,4,0x100000) || !ofr8_put(c,r.a[6],0x20,2,0x2a) ||
           !am_read(c,0x200038,4,value) || !ofr8_put(c,r.a[6],0x22,4,value))return false;
        r.a[1]=0x43942;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x42dd2);
    case 0x42dd2:case 0x42f7c:am_word(r.d[0],0x202);am_byte(r.d[1],0);return am_call(c,0x8ebe,r.pc==0x42dd2U?0x42de0U:0x42f8aU); // MOVE.W #202,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVE.B #3,8f(A6); BSET.B #3,15(A6); MOVE.W #e000,68(A6); MOVE.W #e000,1e(A6); BCLR.B #0,15(A6); MOVE.L 78(A6),D0; MOVE.B 76(A6),D1;
    // JSR 443d2.l.
    case 0x42de0:
        if(!ofr8_put(c,r.a[6],0x8f,1,3) || !ofr8_bit(c,r.a[6],0x15,3,1) || !ofr8_put(c,r.a[6],0x68,2,0xe000) || !ofr8_put(c,r.a[6],0x1e,2,0xe000) ||
           !ofr8_bit(c,r.a[6],0x15,0,0) || !ofr8_get(c,r.a[6],0x78,4,r.d[0]) || !ofr8_get(c,r.a[6],0x76,1,value))return false;
        am_byte(r.d[1],value);return am_call(c,0x443d2,0x42e0c);
    case 0x42e0c:return ofr8_speed(c,0x42e24,0x42e20);                                                     // MOVE.L D0,36(A6); MOVE.L D1,3a(A6); angle bit 5.
    case 0x42e20:case 0x43044:am_byte(r.d[0],r.d[0]+0xfU);r.pc=r.pc==0x42e20U?0x42e24U:0x43048U;return true;   // ADDI.B #f,D0.
    case 0x42e24:return ofr8_split16(c,0x42e3c,0x42e3a);                                                   // LSR.W #4; ANDI.W #f; 8c; angle bit 5.
    case 0x42e3a:am_byte(r.d[0],r.d[0]+7U);r.pc=0x42e3c;return true;                                       // ADDQ.B #7,D0.
    // LSR.W #3,D0; ANDI.B #1f,D0 (bits 8..15 stay); MOVE.B D0,8d(A6); angle bit 5.
    case 0x42e3c:
        am_word(r.d[0],ofr8_w(r.d[0])>>3);am_byte(r.d[0],r.d[0]&0x1fU);if(!ofr8_put(c,r.a[6],0x8d,1,r.d[0]))return false;
        return ofr8_angle(c,0x42e54,0x42e52);
    case 0x42e52:case 0x4305e:am_byte(r.d[0],r.d[0]+3U);r.pc=r.pc==0x42e52U?0x42e54U:0x43060U;return true;   // ADDQ.B #3,D0.
    // LSR.W #2,D0; ANDI.W #3f,D0; MOVE.B D0,8e(A6); MOVE.L #42e68,(A6); BRA.W 42e68.
    case 0x42e54:if(!ofr8_split64(c) || !ofr8_put(c,r.a[6],0,4,0x42e68))return false;r.pc=0x42e68;return true;
    case 0x42e68:return am_call(c,0x4be34,0x42e6e);                                                        // JSR 4be34.l (installed value).
    // MOVE.B 8c(A6),D0; ANDI.W #f,D0; ADD.W D0,D0; ADD.W D0,D0; LEA 4376c(PC),A0; MOVEA.L (A0,D0.W),A0; JSR 4ae4a.l.
    case 0x42e6e:
        if(!ofr8_get(c,r.a[6],0x8c,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]&0xfU);
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);r.a[0]=0x4376c;if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;
        r.a[0]=value;return am_call(c,0x4ae4a,0x42e88);
    case 0x42e88:r.pc=ofr8_b(r.d[0])!=0U?0x42f92:0x42e8e;return true;                                     // TST.B D0; BNE.W 42f92.
    case 0x42e8e:return ofr8_btst(c,r.a[6],0x15,5,0x42e98,0x42ec8);                                       // BTST.B #5,15(A6); BNE.W 42ec8.
    case 0x42e98:return am_call(c,0x49fc6,0x42e9e);                                                        // JSR 49fc6.l.
    // MOVE.W 42(A6),D0; CMPI.W #140,D0; BCS.W 42eb0 (unsigned).
    case 0x42e9e:if(!ofr8_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value);r.pc=ofr8_w(r.d[0])<0x140U?0x42eb0:0x42eaa;return true;
    // MOVE.W 46(A6),D0; SUBI.W #100,D0; CMPI.W #100,D0; BCS.W 42ec6 (unsigned).
    case 0x42eb0:
        if(!ofr8_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]-0x100U);
        r.pc=ofr8_w(r.d[0])<0x100U?0x42ec6:0x42ec0;return true;
    // CMPI.B #40,76(A6); BMI.W 42ed8 (bit 7 of the BYTE difference).
    case 0x42ec8:if(!ofr8_get(c,r.a[6],0x76,1,value))return false;r.pc=(ofr8_b(value-0x40U)&0x80U)!=0U?0x42ed8:0x42ed2;return true;
    case 0x42ed2:if(!ofr8_bit(c,r.a[6],0x15,0,1))return false;r.pc=0x42ed8;return true;                    // BSET.B #0,15(A6).
    // MOVE.W #e0ed,68(A6); MOVE.W #e0ed,1e(A6); BTST.B #0,61(A6); BEQ.W 42f08.
    case 0x42ed8:
        if(!ofr8_put(c,r.a[6],0x68,2,0xe0ed) || !ofr8_put(c,r.a[6],0x1e,2,0xe0ed))return false;return ofr8_btst(c,r.a[6],0x61,0,0x42f08,0x42eee);
    case 0x42eee:return am_call(c,0x49a58,0x42ef4);                                                        // JSR 49a58.l.
    case 0x42ef4:if(!ofr8_jitter(c,0x32))return false;r.a[0]=0x43bb0;r.pc=0x42f62;return true;           // ..., ADD.W D0,32(A6); LEA 43bb0.l,A0; BRA.W.
    case 0x42f08:return ofr8_btst(c,r.a[6],0x61,1,0x42f32,0x42f12);                                       // BTST.B #1,61(A6); BEQ.W 42f32.
    case 0x42f12:return am_call(c,0x49a58,0x42f18);                                                        // JSR 49a58.l.
    // ..., ADD.W D0,2e(A6); BSET.B #1,15(A6); LEA 43b4a.l,A0; BRA.W 42f62.
    case 0x42f18:if(!ofr8_jitter(c,0x2e) || !ofr8_bit(c,r.a[6],0x15,1,1))return false;r.a[0]=0x43b4a;r.pc=0x42f62;return true;
    case 0x42f32:return am_call(c,0x49a58,0x42f38);                                                        // JSR 49a58.l.
    // ..., ADD.W D0,2e(A6); CMPI.B #40,6f(A6); BEQ.W 42f5c.
    case 0x42f38:if(!ofr8_jitter(c,0x2e) || !ofr8_get(c,r.a[6],0x6f,1,value))return false;r.pc=value==0x40U?0x42f5c:0x42f4c;return true;
    case 0x42f4c:return am_call(c,0x49a58,0x42f52);                                                        // JSR 49a58.l.
    case 0x42f52:if(!ofr8_jitter(c,0x32))return false;r.pc=0x42f5c;return true;                           // ..., ADD.W D0,32(A6).
    case 0x42f5c:r.a[0]=0x43b4a;r.pc=0x42f62;return true;                                                  // LEA 43b4a.l,A0.
    // MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6) (bank window); MOVEA.L A0,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x42f62:
        if(!ofr8_put(c,r.a[6],0x20,2,0xe2) || !am_read(c,0x200094,4,value) || !ofr8_put(c,r.a[6],0x22,4,value))return false;
        r.a[1]=r.a[0];am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x42f7c);
    case 0x42f8a:if(!ofr8_put(c,r.a[6],0,4,0x4313a))return false;return am_return(c);                     // MOVE.L #4313a,(A6) (written only); RTS.
    case 0x42f92:r.pc=ofr8_w(r.d[0])>=9U?0x42fec:0x42f9a;return true;                                     // CMPI.W #9,D0; BCC.W 42fec (unsigned).
    // ADD.W D0,D0; ADD.W D0,D0; JMP 42fa2(PC,D0.W): the computed PC goes through the routing (contract decision 2).
    case 0x42f9a:am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);r.pc=am_index(0x42fa2,r.d[0]);return true;
    // The 9-entry BRA.W table 42fa2..42fc2.
    case 0x42fa2:case 0x42fb2:case 0x42fb6:case 0x42fbe:r.pc=0x42fec;return true;
    case 0x42fa6:r.pc=0x42ff0;return true;
    case 0x42faa:case 0x42fc2:r.pc=0x42fc6;return true;
    case 0x42fae:case 0x42fba:r.pc=0x42fd4;return true;
    case 0x42fc6:am_word(r.d[0],0x1a5d);return am_call(c,0x3af8,0x42fd0);                                  // MOVE.W #1a5d,D0; JSR 3af8.l.
    case 0x42fd0:case 0x42fe8:case 0x42fec:r.pc=0x430ba;return true;                                       // BRA.W 430ba.
    case 0x42fd4:return ofr8_btst(c,r.a[2],0x61,7,0x42fde,0x42fe8);                                       // BTST.B #7,61(A2); BNE.W 42fe8.
    case 0x42fde:am_word(r.d[0],0x189d);return am_call(c,0x3af8,0x42fe8);                                  // MOVE.W #189d,D0; JSR 3af8.l.
    case 0x42ff0:am_word(r.d[0],0x1a5e);return am_call(c,0x3af8,0x42ffa);                                  // MOVE.W #1a5e,D0; JSR 3af8.l.
    // SUBQ.B #1,8f(A6); BLT.W 430ba (N != V of the BYTE subtraction: 80 -> 7f overflows).
    case 0x42ffa:{
        if(!ofr8_get(c,r.a[6],0x8f,1,value))return false;const std::uint32_t res=ofr8_b(value-1U);if(!ofr8_put(c,r.a[6],0x8f,1,res))return false;
        const bool n=(res&0x80U)!=0U;const bool v=((value^1U)&(value^res)&0x80U)!=0U;r.pc=n!=v?0x430ba:0x43002;return true;}
    case 0x43002:return am_call(c,0x49a58,0x43008);                                                        // JSR 49a58.l.
    // ANDI.W #3fff,D0; SUBI.W #1f80,D0; MOVE.B 76(A6),D1; LSL.W #8,D1; ADDI.W #8000,D1; ADD.W D1,D0; LSR.W #8,D0; MOVE.B D0,76(A6);
    // MOVE.L 78(A6),D0; MOVE.B 76(A6),D1; JSR 443d2.l.
    case 0x43008:
        am_word(r.d[0],r.d[0]&0x3fffU);am_word(r.d[0],r.d[0]-0x1f80U);if(!ofr8_get(c,r.a[6],0x76,1,value))return false;am_byte(r.d[1],value);
        am_word(r.d[1],ofr8_w(r.d[1])<<8);am_word(r.d[1],r.d[1]+0x8000U);am_word(r.d[0],r.d[0]+r.d[1]);am_word(r.d[0],ofr8_w(r.d[0])>>8);
        if(!ofr8_put(c,r.a[6],0x76,1,r.d[0]) || !ofr8_get(c,r.a[6],0x78,4,r.d[0]) || !ofr8_get(c,r.a[6],0x76,1,value))return false;
        am_byte(r.d[1],value);return am_call(c,0x443d2,0x43030);
    case 0x43030:return ofr8_speed(c,0x43048,0x43044);                                                     // MOVE.L D0,36(A6); MOVE.L D1,3a(A6); angle bit 5.
    case 0x43048:return ofr8_split16(c,0x43060,0x4305e);                                                   // LSR.W #4; ANDI.W #f; 8c; angle bit 5.
    case 0x43060:if(!ofr8_split64(c))return false;return ofr8_shard(c,0x43080);                            // LSR.W #2; ANDI.W #3f; 8e; child 430e6 (2986).
    case 0x43080:return ofr8_shard_link(c,0x43090);                                                        // MOVE.L 7c(A6),7c(A0); MOVEQ; MOVEQ; JSR 49214.l.
    case 0x43090:if(!ofr8_put(c,r.a[6],0,4,0x4309a))return false;r.pc=0x42e8e;return true;                // MOVE.L #4309a,(A6) (written only); BRA.W 42e8e.
    case 0x430ba:return ofr8_shard(c,0x430d0);                                                             // child 430e6 (2986).
    case 0x430d0:return ofr8_shard_link(c,0x430e0);                                                        // MOVE.L 7c(A6),7c(A0); MOVEQ; MOVEQ; JSR 49214.l.
    // ---- ae930 (state machine of aea38): JSR 4b54e.l / BCC.W ae93e (C returned by 4b54e) / CLR.B 5e(A6).
    case 0xae930:return am_call(c,0x4b54e,0xae936);
    case 0xae936:return ofr8_carry(c,0xae93e,0xae93a);
    case 0xae93a:if(!ofr8_put(c,r.a[6],0x5e,1,0))return false;r.pc=0xae93e;return true;
    case 0xae93e:return ofr8_btst(c,r.a[6],0x61,7,0xaea18,0xae948);                                       // BTST.B #7,61(A6); BEQ.W aea18.
    // ADDQ.W #1,7e(A6); CMPI.W #4,7e(A6); BEQ.W aea08.
    case 0xae948:
        if(!ofr8_add_word(c,r.a[6],0x7e,1) || !ofr8_get(c,r.a[6],0x7e,2,value))return false;r.pc=value==4U?0xaea08:0xae956;return true;
    case 0xae956:am_word(r.d[0],0x182f);return am_call(c,0x3af8,0xae960);                                  // MOVE.W #182f,D0; JSR 3af8.l.
    // BCLR.B #7,61(A6); MOVE.W #57,54(A6); child d1d38 (28ae).
    case 0xae960:if(!ofr8_bit(c,r.a[6],0x61,7,0) || !ofr8_put(c,r.a[6],0x54,2,0x57))return false;return ofr8_child_d1d38(c,0xae97c);
    case 0xae97c:r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,0xae986);                                      // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.l.
    case 0xae986:return ofr8_child_place(c,0x40,0xae99e);                                                  // 68 / 1e(A0) := e0ed; ADDI.W #40,32(A6); JSR 43e34.l.
    case 0xae99e:am_word(r.d[0],2);return am_call(c,0xd39f6,0xae9a8);                                      // MOVE.W #2,D0; JSR d39f6.l.
    case 0xae9a8:if(!ofr8_add_word(c,r.a[6],0x32,0x10000U-0x40U))return false;return am_call(c,0x43e34,0xae9b4); // SUBI.W #40,32(A6); JSR 43e34.l.
    case 0xae9b4:if(!ofr8_get(c,r.a[6],0x7a,2,value))return false;r.pc=value==0U?0xaea04:0xae9bc;return true; // TST.W 7a(A6); BEQ.W aea04.
    case 0xae9bc:return ofr8_child_d1d38(c,0xae9cc);                                                       // child d1d38 (28ae).
    case 0xae9cc:r.d[0]=0;r.d[1]=0x60;return am_call(c,0x49214,0xae9d6);                                   // MOVEQ #0,D0; MOVEQ #60,D1; JSR 49214.l.
    case 0xae9d6:return ofr8_child_place(c,0x80,0xae9ee);                                                  // 68 / 1e(A0) := e0ed; ADDI.W #80,32(A6); JSR 43e34.l.
    case 0xae9ee:am_word(r.d[0],2);return am_call(c,0xd39f6,0xae9f8);                                      // MOVE.W #2,D0; JSR d39f6.l.
    case 0xae9f8:if(!ofr8_add_word(c,r.a[6],0x32,0x10000U-0x80U))return false;return am_call(c,0x43e34,0xaea04); // SUBI.W #80,32(A6); JSR 43e34.l.
    case 0xaea04:r.pc=0xaea18;return true;                                                                 // BRA.W aea18.
    case 0xaea08:am_word(r.d[0],0x1830);return am_call(c,0x3af8,0xaea12);                                  // MOVE.W #1830,D0; JSR 3af8.l.
    case 0xaea12:if(!ofr8_put(c,r.a[6],0,4,0xaec04))return false;r.pc=0xaea18;return true;                // MOVE.L #aec04,(A6) (written only).
    case 0xaea18:r.a[0]=0xae6a8;return am_call(c,0x1ab02,0xaea22);                                         // LEA ae6a8(PC),A0; JSR 1ab02.l.
    case 0xaea22:return ofr8_carry(c,0xaea36,0xaea26);                                                     // BCC.W aea36 (C returned by 1ab02).
    // BSET.B #7,61(A6); CLR.W 54(A6); JMP 2a00.l.
    case 0xaea26:if(!ofr8_bit(c,r.a[6],0x61,7,1) || !ofr8_put(c,r.a[6],0x54,2,0))return false;r.pc=0x2a00;return true;
    // ---- aea38 (LONG table e8eac): MOVE.W #4d,D0; MOVE.W #1,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xaea38:am_word(r.d[0],0x4d);am_word(r.d[1],1);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xaea4a);
    case 0xaea4a:am_word(r.d[0],0xc85);return am_call(c,0x4a496,0xaea54);                                  // MOVE.W #c85,D0; JSR 4a496.l.
    // MOVE.W #0,68(A6); MOVE.W #0,1e(A6); TST.W 7a(A6); BNE.W aea72.
    case 0xaea54:
        if(!ofr8_put(c,r.a[6],0x68,2,0) || !ofr8_put(c,r.a[6],0x1e,2,0) || !ofr8_get(c,r.a[6],0x7a,2,value))return false;
        r.pc=value!=0U?0xaea72:0xaea68;return true;
    case 0xaea68:case 0xaea72:if(!ofr8_put(c,r.a[0],0x82,2,r.pc==0xaea68U?2U:0xdU))return false;r.pc=0xaea78;return true; // MOVE.W #2 / #d,82(A0).
    // MOVE.W #57,54(A6); MOVE.W #0,7c(A6); TST.W 76(A6); BNE.W aea92.
    case 0xaea78:
        if(!ofr8_put(c,r.a[6],0x54,2,0x57) || !ofr8_put(c,r.a[6],0x7c,2,0) || !ofr8_get(c,r.a[6],0x76,2,value))return false;
        r.pc=value!=0U?0xaea92:0xaea8c;return true;
    case 0xaea8c:if(!ofr8_bit(c,r.a[6],0x15,0,2))return false;r.pc=0xaea92;return true;                   // BCHG.B #0,15(A6).
    case 0xaea92:if(!ofr8_get(c,r.a[6],0x7a,2,value))return false;r.pc=value==0U?0xaea9e:0xaea9a;return true; // TST.W 7a(A6); BEQ.W aea9e.
    case 0xaea9a:r.pc=0xaeb2c;return true;                                                                 // BRA.W aeb2c.
    case 0xaea9e:if(!ofr8_put(c,r.a[6],0x7e,2,0))return false;return am_call(c,0x4c0ac,0xaeaaa);          // MOVE.W #0,7e(A6); JSR 4c0ac.l.
    case 0xaeaaa:if(!ofr8_put(c,r.a[6],0,4,0xaeab0))return false;r.pc=0xaeab0;return true;                // MOVE.L #aeab0,(A6) (next PC).
    case 0xaeab0:return ofr8_btst(c,r.a[6],0x15,7,0xaeaba,0xaeac4);                                       // BTST.B #7,15(A6); BNE.W aeac4.
    case 0xaeaba:return am_call(c,0x4be2c,0xaeac0);                                                        // JSR 4be2c.l.
    case 0xaeac0:r.pc=0xaeaca;return true;                                                                 // BRA.W aeaca.
    case 0xaeac4:return am_call(c,0x4be06,0xaeaca);                                                        // JSR 4be06.l.
    // MOVE.W 7e(A6),D0; ADD.W D0,D0; ADDQ.W #1,D0; LEA 26(A6),A0; MOVE.W #d3,20(A6); MOVE.L 200138.l,22(A6); LEA 26(A6),A0; MOVE.W D0,D1;
    // ADD.W D1,D1; ADD.W D1,D1; MOVEA.L 200138.l,A1; MOVEA.L (A1,D1.W),A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xaeaca:
        if(!ofr8_get(c,r.a[6],0x7e,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+1U);
        r.a[0]=r.a[6]+0x26U;if(!ofr8_put(c,r.a[6],0x20,2,0xd3) || !am_read(c,0x200138,4,value) || !ofr8_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]+r.d[1]);am_word(r.d[1],r.d[1]+r.d[1]);
        if(!am_read(c,0x200138,4,r.a[1]) || !am_read(c,am_index(r.a[1],r.d[1]),4,value))return false;r.a[1]=value;
        am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xaeb02);
    case 0xaeb02:return am_call(c,0x49fc6,0xaeb08);                                                        // JSR 49fc6.l.
    case 0xaeb08:return ofr8_btst(c,r.a[6],0x15,0,0xaeb12,0xaeb1c);                                       // BTST.B #0,15(A6); BNE.W aeb1c.
    case 0xaeb12:r.a[0]=0xae6b0;r.pc=0xaeb22;return true;                                                  // MOVEA.L #ae6b0,A0; BRA.W aeb22.
    case 0xaeb1c:r.a[0]=0xae728;r.pc=0xaeb22;return true;                                                  // MOVEA.L #ae728,A0.
    case 0xaeb22:return am_call(c,0x4706c,0xaeb28);                                                        // JSR 4706c.l.
    case 0xaeb28:r.pc=0xae930;return true;                                                                 // BRA.W ae930.
    case 0xaeb2c:if(!ofr8_put(c,r.a[6],0,4,0xaeb32))return false;r.pc=0xaeb32;return true;                // MOVE.L #aeb32,(A6) (next PC).
    case 0xaeb32:return am_call(c,0x43e34,0xaeb38);                                                        // JSR 43e34.l (installed value).
    // MOVE.W 5418(A5),D0; CMP.W 7a(A6),D0; BLT.W aeb4a (signed WORD).
    case 0xaeb38:
        if(!ofr8_get(c,r.a[5],0x5418,2,value) || !ofr8_get(c,r.a[6],0x7a,2,other))return false;am_word(r.d[0],value);
        r.pc=ofr8_sw(r.d[0])<ofr8_sw(other)?0xaeb4a:0xaeb44;return true;
    case 0xaeb44:if(!ofr8_put(c,r.a[6],0,4,0xaeb4c))return false;r.pc=0xaeb4a;return true;                // MOVE.L #aeb4c,(A6) (written only).
    // ---- cc7b4 (entry 2 of the FR4 BRA.W table cc7ac): BRA.W cdc1c.
    case 0xcc7b4:r.pc=0xcdc1c;return true;
    // ---- cdc24 (installed by FR4 cdc1c): MOVE.W 8c(A6),D0; BNE.W cdc46 / CMPI.W #1..#4,D0; BNE.W next.
    case 0xcdc24:if(!ofr8_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],value);r.pc=ofr8_w(r.d[0])!=0U?0xcdc46:0xcdc2c;return true;
    case 0xcdc46:r.pc=ofr8_w(r.d[0])!=1U?0xcdc68:0xcdc4e;return true;
    case 0xcdc68:r.pc=ofr8_w(r.d[0])!=2U?0xcdc8a:0xcdc70;return true;
    case 0xcdc8a:r.pc=ofr8_w(r.d[0])!=3U?0xcdcac:0xcdc92;return true;
    case 0xcdcac:r.pc=ofr8_w(r.d[0])!=4U?0xcdcce:0xcdcb4;return true;
    case 0xcdc2c:return ofr8_kind(c,0xcdf86,0xcdc42);
    case 0xcdc4e:return ofr8_kind(c,0xce7c4,0xcdc64);
    case 0xcdc70:return ofr8_kind(c,0xcf870,0xcdc86);
    case 0xcdc92:return ofr8_kind(c,0xcf126,0xcdca8);
    case 0xcdcb4:return ofr8_kind(c,0xd00e0,0xcdcca);
    case 0xcdcce:return ofr8_kind(c,0xd07f8,0xcdce4);
    case 0xcdc42:case 0xcdc64:case 0xcdc86:case 0xcdca8:case 0xcdcca:r.pc=0xcdce4;return true;            // BRA.W cdce4.
    // LEA cdf3e(PC),A0; MOVE.W 8c(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A0,D0.W),A0; MOVE.W #3,D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0;
    // BEQ.W cdd24; BPL.W cdd1a (the bundled pair on the N / Z of the MOVE).
    case 0xcdce4:
        r.a[0]=0xcdf3e;if(!ofr8_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);
        am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;am_word(r.d[0],3);
        am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
        r.pc=ofr8_w(r.d[0])==0U?0xcdd24:((r.d[0]&0x8000U)==0U?0xcdd1a:0xcdd06);return true;
    case 0xcdd06:return am_call(c,0x497a6,0xcdd0c);                                                        // JSR 497a6.l.
    case 0xcdd0c:return ofr8_carry(c,0xcdd10,0xcdd16);                                                     // BCS.W cdd16 (C returned by 497a6).
    case 0xcdd10:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.pc=0xcdd1a;return true; // MOVE.W (A0),D0; BRA.W cdd1a.
    case 0xcdd16:if(!ofr8_get(c,r.a[0],2,2,value))return false;am_word(r.d[0],value);r.pc=0xcdd1a;return true; // MOVE.W 2(A0),D0.
    case 0xcdd1a:am_byte(r.d[1],0);return am_call(c,0x8ebe,0xcdd24);                                       // MOVE.B #0,D1; JSR 8ebe.l.
    case 0xcdd24:if(!ofr8_put(c,r.a[6],0,4,0xcdd2e))return false;r.pc=0xcdd2e;return true;               // MOVE.L #cdd2e,(A6); BRA.W cdd2e (FR7).
    // ---- d3500 (28ae child of d3802): MOVEA.L 96(A6),A0; MOVE.B 1(A0),a0(A6); MOVE.W 2(A0),9e(A6); CMPI.B #0,(A0); BEQ.W d3522.
    case 0xd3500:
        if(!ofr8_get(c,r.a[6],0x96,4,r.a[0]) || !ofr8_get(c,r.a[0],1,1,value) || !ofr8_put(c,r.a[6],0xa0,1,value) ||
           !ofr8_get(c,r.a[0],2,2,value) || !ofr8_put(c,r.a[6],0x9e,2,value) || !am_read(c,r.a[0],1,value))return false;
        r.pc=value==0U?0xd3522:0xd3518;return true;
    case 0xd3518:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x49290,0xd3522);                   // CLR.W D0; CLR.W D1; JSR 49290.l.
    case 0xd3522:return am_call(c,0x43e34,0xd3528);                                                        // JSR 43e34.l.
    case 0xd3528:if(!ofr8_get(c,r.a[6],0xa0,1,value))return false;r.pc=value!=0xffU?0xd354e:0xd3532;return true; // CMPI.B #ff,a0(A6); BNE.W d354e.
    case 0xd3532:if(!ofr8_get(c,r.a[6],0x9e,2,value))return false;r.pc=value==0U?0xd3546:0xd353c;return true; // CMPI.W #0,9e(A6); BEQ.W d3546.
    case 0xd353c:return am_call(c,0xd383c,0xd3540);                                                        // JSR d383c(PC).
    case 0xd3540:if(!ofr8_add_word(c,r.a[6],0x9e,0xffffU))return false;r.pc=0xd3532;return true;          // SUBQ.W #1,9e(A6); BRA.B d3532.
    case 0xd354e:if(!ofr8_put(c,r.a[6],0,4,0xd3554))return false;r.pc=0xd3554;return true;                // MOVE.L #d3554,(A6) (next PC).
    case 0xd3554:return am_call(c,0x43e34,0xd355a);                                                        // JSR 43e34.l (installed value).
    // SUBQ.B #1,a0(A6); BNE.W d3570.
    case 0xd355a:
        if(!ofr8_get(c,r.a[6],0xa0,1,value) || !ofr8_put(c,r.a[6],0xa0,1,value-1U))return false;r.pc=ofr8_b(value-1U)!=0U?0xd3570:0xd3562;return true;
    // MOVEA.L 96(A6),A0; MOVE.B 1(A0),a0(A6); JSR d383c(PC).
    case 0xd3562:
        if(!ofr8_get(c,r.a[6],0x96,4,r.a[0]) || !ofr8_get(c,r.a[0],1,1,value) || !ofr8_put(c,r.a[6],0xa0,1,value))return false;
        return am_call(c,0xd383c,0xd3570);
    // SUBQ.W #1,9e(A6); BNE.W d357e.
    case 0xd3570:
        if(!ofr8_get(c,r.a[6],0x9e,2,value) || !ofr8_put(c,r.a[6],0x9e,2,value-1U))return false;r.pc=ofr8_w(value-1U)!=0U?0xd357e:0xd3578;return true;
    // ---- d3802 (subroutine): MOVE.L A1,-(A7); MOVEA.L #d3500,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0xd3802:if(!am_push(c,4,r.a[1]))return false;r.a[0]=0xd3500;am_word(r.d[0],0x14);return am_call(c,0x28ae,0xd3814);
    case 0xd3814:return ofr8_carry(c,0xd3826,0xd3818);                                                     // BCC.W d3826 (C returned by 28ae).
    case 0xd3818:case 0xd3a50:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,r.pc==0xd3818U?0xd3822U:0xd3a5aU); // CLR.W D0; CLR.W D1; JSR 4970a.l.
    case 0xd3822:case 0xd3a5a:r.carry=AnimationCarrySet;r.pc=r.pc==0xd3822U?0xd3826U:0xd3a5eU;return true;  // ORI.B #1,CCR (own C, no reader).
    case 0xd3826:return ofr8_btst(c,r.a[6],0x15,2,0xd3836,0xd3830);                                       // BTST.B #2,15(A6); BEQ.W d3836.
    case 0xd3830:if(!ofr8_bit(c,r.a[0],0x15,2,1))return false;r.pc=0xd3836;return true;                   // BSET.B #2,15(A0).
    case 0xd3836:if(!am_pop(c,4,value) || !ofr8_put(c,r.a[0],0x96,4,value))return false;return am_return(c); // MOVE.L (A7)+,96(A0); RTS.
    // ---- d383c (subroutine): MOVEA.L 96(A6),A1; MOVE.W 6(A1),D0; JSR 49a84.l.
    case 0xd383c:if(!ofr8_get(c,r.a[6],0x96,4,r.a[1]) || !ofr8_get(c,r.a[1],6,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49a84,0xd384a);
    case 0xd384a:return ofr8_offset(c,4,0,0xd385e,0xd385c);                                                // MOVEA.L 96(A6),A1; ADD.W 4(A1),D0; BTST.B #0,15(A6).
    case 0xd385c:case 0xd387e:am_word(r.d[0],0U-r.d[0]);r.pc=r.pc==0xd385cU?0xd385eU:0xd3880U;return true;   // NEG.W D0.
    // MOVE.W D0,36(A6); MOVE.W a(A1),D0; JSR 49a84.l.
    case 0xd385e:if(!ofr8_put(c,r.a[6],0x36,2,r.d[0]) || !ofr8_get(c,r.a[1],0xa,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49a84,0xd386c);
    case 0xd386c:return ofr8_offset(c,8,1,0xd3880,0xd387e);                                                // MOVEA.L 96(A6),A1; ADD.W 8(A1),D0; BTST.B #1,15(A6).
    // MOVE.W D0,3a(A6); MOVEA.L e(A1),A0; CMPI.B #0,d(A1); BEQ.W d38a0.
    case 0xd3880:
        if(!ofr8_put(c,r.a[6],0x3a,2,r.d[0]) || !ofr8_get(c,r.a[1],0xe,4,r.a[0]) || !ofr8_get(c,r.a[1],0xd,1,value))return false;
        r.pc=value==0U?0xd38a0:0xd3892;return true;
    case 0xd3892:return am_call(c,0x49a58,0xd3898);                                                        // JSR 49a58.l.
    // ANDI.W #3c,D0; MOVEA.L (A0,D0.W),A0.
    case 0xd3898:am_word(r.d[0],r.d[0]&0x3cU);if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;r.pc=0xd38a0;return true;
    case 0xd38a0:am_word(r.d[0],0x1e);return am_call(c,0x28ae,0xd38ac);                                    // MOVEA.L A0,A0; MOVE.W #1e,D0; JSR 28ae.l.
    // MOVE.W 1e(A6),1e(A0); BTST.B #2,15(A6); BEQ.W d38c2.
    case 0xd38ac:if(!ofr8_get(c,r.a[6],0x1e,2,value) || !ofr8_put(c,r.a[0],0x1e,2,value))return false;return ofr8_btst(c,r.a[6],0x15,2,0xd38c2,0xd38bc);
    case 0xd38bc:if(!ofr8_bit(c,r.a[0],0x15,2,1))return false;r.pc=0xd38c2;return true;                   // BSET.B #2,15(A0).
    // MOVE.W 36(A6),D0; MOVE.W 3a(A6),D1; JSR 49214.l.
    case 0xd38c2:
        if(!ofr8_get(c,r.a[6],0x36,2,value) || !ofr8_get(c,r.a[6],0x3a,2,other))return false;am_word(r.d[0],value);am_word(r.d[1],other);
        return am_call(c,0x49214,0xd38d0);
    // MOVEA.L c(A6),A1; MOVE.B 12(A1),12(A0); MOVE.B 13(A1),13(A0); RTS.
    case 0xd38d0:
        if(!ofr8_get(c,r.a[6],0xc,4,r.a[1]) || !ofr8_get(c,r.a[1],0x12,1,value) || !ofr8_put(c,r.a[0],0x12,1,value) ||
           !ofr8_get(c,r.a[1],0x13,1,value) || !ofr8_put(c,r.a[0],0x13,1,value))return false;
        return am_return(c);
    // ---- d39f6 / d3a2e (child helper): LEA d4046(PC),A1; BRA.W d3a2e / MOVE.L A1,D1; TST.W D0; BNE.W d3a38.
    case 0xd39f6:r.a[1]=0xd4046;r.pc=0xd3a2e;return true;
    case 0xd3a2e:r.d[1]=r.a[1];r.pc=ofr8_w(r.d[0])!=0U?0xd3a38:0xd3a36;return true;
    // MOVE.W D0,-(A7); MOVE.L D1,-(A7); MOVEA.L #d309a,A0; MOVE.W #1e,D0; JSR 28ae.l.
    case 0xd3a38:if(!am_push(c,2,r.d[0]) || !am_push(c,4,r.d[1]))return false;r.a[0]=0xd309a;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0xd3a4c);
    case 0xd3a4c:return ofr8_carry(c,0xd3a5e,0xd3a50);                                                     // BCC.W d3a5e (C returned by 28ae).
    // MOVE.L (A7)+,D1; MOVE.W (A7)+,D0; MOVE.L D1,82(A0); SUBQ.W #1,D0; CMPI.W #0,D0; BGT.B d3a38 (signed WORD > 0).
    case 0xd3a5e:
        if(!am_pop(c,4,r.d[1]) || !am_pop(c,2,value))return false;am_word(r.d[0],value);if(!ofr8_put(c,r.a[0],0x82,4,r.d[1]))return false;
        am_word(r.d[0],r.d[0]-1U);r.pc=ofr8_sw(r.d[0])>0?0xd3a38:0xd3a6e;return true;
    default:
        return am_error(c,"unsupported animation objects fr8 PC");
    }
}
}
