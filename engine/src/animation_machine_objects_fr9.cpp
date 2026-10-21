#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool ofr9_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr9_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BSET.B / BCLR.B / BCHG.B #bit,d(An): read-modify-write of one BYTE (mode 0 clear, 1 set, 2 change).
bool ofr9_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,unsigned int mode) {
    std::uint32_t value=0;if(!ofr9_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;
    const std::uint32_t out=mode==1U?(value|mask):(mode==0U?(value&~mask):(value^mask));
    return ofr9_put(c,base,displacement,1,out);
}
// BTST.B #bit,d(An); BEQ zero_pc (bit clear) / one_pc (bit set).
bool ofr9_btst(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    std::uint32_t value=0;if(!ofr9_get(c,base,displacement,1,value))return false;
    c.s.pc=(value&(1U<<bit))==0U?zero_pc:one_pc;return true;
}
// BCC on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool ofr9_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr9 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ADD.W / SUB.W D0,d(A6): WORD field += addend (modulo 2^16).
bool ofr9_add_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t addend) {
    std::uint32_t value=0;if(!ofr9_get(c,c.s.a[6],displacement,2,value))return false;return ofr9_put(c,c.s.a[6],displacement,2,value+addend);
}
// ASR.L #n (n = 1..31): arithmetic right shift of the LONG (the sign bit fills the vacated bits).
std::uint32_t ofr9_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t shifted=value>>n;return (value&0x80000000U)!=0U?(shifted|~(0xffffffffU>>n)):shifted;
}
// MOVE.W #163,20(A6); MOVEA.L #anim,A1; MOVE.W #100,D0; JSR 49f8c.l.
bool ofr9_anim(AnimationMachineContext& c,std::uint32_t anim,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;if(!ofr9_put(c,r.a[6],0x20,2,0x163))return false;r.a[1]=anim;am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #187f,D0; JSR 3af8.l.
bool ofr9_sound(AnimationMachineContext& c,std::uint32_t return_pc) {am_word(c.s.d[0],0x187f);return am_call(c,0x3af8,return_pc);}
// MOVE.B 5e(A6),D0; CMPI.B #1b,D0; BCC.W high_pc (unsigned BYTE >= 1b) / jump_pc.
bool ofr9_kind(AnimationMachineContext& c,std::uint32_t high_pc,std::uint32_t jump_pc) {
    std::uint32_t value=0;if(!ofr9_get(c,c.s.a[6],0x5e,1,value))return false;am_byte(c.s.d[0],value);
    c.s.pc=(c.s.d[0]&255U)>=0x1bU?high_pc:jump_pc;return true;
}
// ANDI.W #mask,D0; ADD.W D0,D0; ADD.W D0,D0; JMP table(PC,D0.W): the computed PC goes through the routing (contract decision 2).
void ofr9_table(AnimationMachineContext& c,std::uint32_t mask,std::uint32_t table) {
    AnimationMachineState& r=c.s;am_word(r.d[0],r.d[0]&mask);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);r.pc=am_index(table,r.d[0]);
}
// ANDI.W #mask,D0; ADDI.W #base,D0; EXT.L D0; LSL.L #8,D0; JSR 443d2.l.
bool ofr9_speed(AnimationMachineContext& c,std::uint32_t mask,std::uint32_t base,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;am_word(r.d[0],r.d[0]&mask);am_word(r.d[0],r.d[0]+base);r.d[0]=am_extend_word(r.d[0]);r.d[0]=r.d[0]<<8;
    return am_call(c,0x443d2,return_pc);
}
// MOVE.L D0,36(A6); MOVE.L D1,3a(A6); JSR 49a58.l.
bool ofr9_store_speed(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;if(!ofr9_put(c,r.a[6],0x36,4,r.d[0]) || !ofr9_put(c,r.a[6],0x3a,4,r.d[1]))return false;return am_call(c,0x49a58,return_pc);
}
// MOVE.B D0,D1; ANDI.B #3f,D1 (D1 bits 8..31 stay).
void ofr9_spread(AnimationMachineContext& c) {am_byte(c.s.d[1],c.s.d[0]&0x3fU);}
// MOVEA.L c(A6),A0; SUBQ.B #1,62(A0); JMP 2a00.l.
bool ofr9_release(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr9_get(c,r.a[6],0xc,4,r.a[0]) || !ofr9_get(c,r.a[0],0x62,1,value) || !ofr9_put(c,r.a[0],0x62,1,value-1U))return false;r.pc=0x2a00;return true;
}
// MOVE.L f(A6),D0; ASR.L #n,D0; SUB.L D0,f(A6).
bool ofr9_decay(AnimationMachineContext& c,std::uint32_t field,unsigned int n) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!ofr9_get(c,r.a[6],field,4,value))return false;r.d[0]=ofr9_asr(value,n);
    return ofr9_put(c,r.a[6],field,4,value-r.d[0]);
}
// ADDI.L #addend,3a(A6).
bool ofr9_fall(AnimationMachineContext& c,std::uint32_t addend) {
    std::uint32_t value=0;if(!ofr9_get(c,c.s.a[6],0x3a,4,value))return false;return ofr9_put(c,c.s.a[6],0x3a,4,value+addend);
}
// TST.B 5f(A6); BPL.W plus_pc / minus_pc.
bool ofr9_side(AnimationMachineContext& c,std::uint32_t plus_pc,std::uint32_t minus_pc) {
    std::uint32_t value=0;if(!ofr9_get(c,c.s.a[6],0x5f,1,value))return false;c.s.pc=(value&0x80U)==0U?plus_pc:minus_pc;return true;
}
}
// Objects FR9 (220 block starts, contract docs/analysis/animation-machine-frontier-fr9-contract.md): the last C-gated area-D roots -- the af990
// family: the object af8cc (N09 af768 install; installs af8f2 af910), the hit-reaction selector af990 (N09 af97e install) with the computed jumps
// af9bc / afa40 / afac4 (27-entry BRA.W tables af9c8 / afa4c / afad0 after CMPI.B #1b + BCC) and afb44 / afb5e / afb78 / afbaa (2 / 2 / 8 / 2
// entries, bounded by their ANDI.W), the reactions afbbe (N09 af626 install) afcf2 afda6 afe0a afe98 aff00 aff52 aff86 with the installs afd7c afe40 aff30
// b001a, and the helper b051a (the 2986 child b3dbc).  No TRAP, no JSR (An), no ROM data read; every exit is a routed block start.  MOVE.L #v,(A6)
// enters v only when v is the next PC; af910 (af906), aff00 (afe7a) and afed8 (afe8e) are written only.  The 5 consumers afd90 aff3c b0048 (49fc6),
// afe6a (b0468) and b0556 (MOVEM.W (A7)+,D0-D6; 2986) read a known C or fail; b0578 (ORI.B #1,CCR) sets C, the RTS b057c passes no C to a reader.
bool animation_objects_fr9_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0xb057c:return am_return(c);                                                                     // RTS.
    // ---- af8cc (N09 af768 install): LEA caba0.l,A0; JSR 490ba.l.
    case 0xaf8cc:r.a[0]=0xcaba0;return am_call(c,0x490ba,0xaf8d8);
    case 0xaf8d8:am_word(r.d[0],r.d[0]-1U);r.pc=(r.d[0]&0x8000U)!=0U?0xaf910:0xaf8de;return true;      // SUBQ.W #1,D0; BMI.W af910 (N of the WORD).
    // MOVE.W D0,96(A6); MOVE.W #80,2c(A6); SF.B 9d(A6); MOVE.L #af8f2,(A6) (next PC).
    case 0xaf8de:
        if(!ofr9_put(c,r.a[6],0x96,2,r.d[0]) || !ofr9_put(c,r.a[6],0x2c,2,0x80) || !ofr9_put(c,r.a[6],0x9d,1,0) || !ofr9_put(c,r.a[6],0,4,0xaf8f2))return false;
        r.pc=0xaf8f2;return true;
    case 0xaf8f2:return am_call(c,0x4be06,0xaf8f8);                                                        // JSR 4be06.l (installed value).
    case 0xaf8f8:return am_call(c,0x49fc6,0xaf8fe);                                                        // JSR 49fc6.l (C not read).
    // SUBQ.W #1,96(A6); BPL.W af90c (N of the new WORD).
    case 0xaf8fe:
        if(!ofr9_get(c,r.a[6],0x96,2,value) || !ofr9_put(c,r.a[6],0x96,2,value-1U))return false;
        r.pc=((value-1U)&0x8000U)==0U?0xaf90c:0xaf906;return true;
    case 0xaf906:if(!ofr9_put(c,r.a[6],0,4,0xaf910))return false;r.pc=0xaf90c;return true;                // MOVE.L #af910,(A6) (written only).
    case 0xaf90c:r.pc=0xaf96a;return true;                                                                 // BRA.W af96a (N09).
    case 0xaf910:return ofr9_anim(c,0xb0e94,0xaf926);                                                      // anim b0e94 (installed value).
    case 0xaf926:if(!ofr9_put(c,r.a[6],0,4,0xaf92c))return false;r.pc=0xaf92c;return true;                // MOVE.L #af92c,(A6) (next PC, N09).
    // ---- af990 (N09 af97e install): JSR 8ff4.l; JSR e9112.l; the selector.
    case 0xaf990:return am_call(c,0x8ff4,0xaf996);
    case 0xaf996:return am_call(c,0xe9112,0xaf99c);
    case 0xaf99c:return ofr9_btst(c,r.a[6],0x61,1,0xaf9a6,0xafa34);                                       // BTST.B #1,61(A6); BNE.W afa34.
    case 0xaf9a6:return ofr9_btst(c,r.a[6],0x15,7,0xafab8,0xaf9b0);                                       // BTST.B #7,15(A6); BEQ.W afab8.
    case 0xaf9b0:return ofr9_kind(c,0xafb3e,0xaf9bc);                                                      // BYTE 5e >= 1b -> afb3e.
    case 0xafa34:return ofr9_kind(c,0xafba4,0xafa40);                                                      // BYTE 5e >= 1b -> afba4.
    case 0xafab8:return ofr9_kind(c,0xaff00,0xafac4);                                                      // BYTE 5e >= 1b -> aff00.
    case 0xaf9bc:ofr9_table(c,0xffU,0xaf9c8);return true;                                                  // ANDI.W #ff; JMP af9c8(PC,D0.W).
    case 0xafa40:ofr9_table(c,0xffU,0xafa4c);return true;                                                  // ANDI.W #ff; JMP afa4c(PC,D0.W).
    case 0xafac4:ofr9_table(c,0xffU,0xafad0);return true;                                                  // ANDI.W #ff; JMP afad0(PC,D0.W).
    case 0xafb44:ofr9_table(c,1U,0xafb50);return true;                                                     // ANDI.W #1; JMP afb50(PC,D0.W).
    case 0xafb5e:ofr9_table(c,1U,0xafb6a);return true;                                                     // ANDI.W #1; JMP afb6a(PC,D0.W).
    case 0xafb78:ofr9_table(c,7U,0xafb84);return true;                                                     // ANDI.W #7; JMP afb84(PC,D0.W).
    case 0xafbaa:ofr9_table(c,1U,0xafbb6);return true;                                                     // ANDI.W #1; JMP afbb6(PC,D0.W).
    // The 27-entry BRA.W table af9c8..afa30.
    case 0xaf9c8:case 0xaf9cc:case 0xaf9d8:case 0xaf9e0:case 0xaf9e8:case 0xafa00:case 0xafa08:case 0xafa0c:case 0xafa10:case 0xafa14:
    case 0xafa18:case 0xafa1c:case 0xafa20:case 0xafa24:case 0xafa28:case 0xafa2c:case 0xafa30:r.pc=0xafb3e;return true;
    case 0xaf9d0:case 0xaf9d4:r.pc=0xafb58;return true;
    case 0xaf9dc:case 0xaf9ec:case 0xaf9f8:case 0xaf9fc:case 0xafa04:r.pc=0xafb72;return true;
    case 0xaf9e4:r.pc=0xafbbe;return true;
    case 0xaf9f0:case 0xafa74:case 0xafaf8:r.pc=0xaff52;return true;                                      // index a of the three tables.
    case 0xaf9f4:case 0xafa78:case 0xafafc:r.pc=0xaff86;return true;                                      // index b of the three tables.
    // The 27-entry BRA.W table afa4c..afab4 (a -> aff52, b -> aff86 above).
    case 0xafa4c:case 0xafa50:case 0xafa54:case 0xafa58:case 0xafa5c:case 0xafa60:case 0xafa64:case 0xafa68:case 0xafa6c:case 0xafa70:
    case 0xafa7c:case 0xafa80:case 0xafa84:case 0xafa88:case 0xafa8c:case 0xafa90:case 0xafa94:case 0xafa98:case 0xafa9c:case 0xafaa0:
    case 0xafaa4:case 0xafaa8:case 0xafaac:case 0xafab0:case 0xafab4:r.pc=0xafba4;return true;
    // The 27-entry BRA.W table afad0..afb38 (a -> aff52, b -> aff86 above).
    case 0xafad0:case 0xafad4:case 0xafad8:case 0xafadc:case 0xafae0:case 0xafae4:case 0xafae8:case 0xafaec:case 0xafaf0:case 0xafaf4:
    case 0xafb00:case 0xafb04:case 0xafb08:case 0xafb0c:case 0xafb10:case 0xafb14:case 0xafb18:case 0xafb1c:case 0xafb20:case 0xafb24:
    case 0xafb28:case 0xafb2c:case 0xafb30:case 0xafb34:case 0xafb38:r.pc=0xaff00;return true;
    case 0xafb3e:case 0xafb58:case 0xafb72:case 0xafba4:                                                   // JSR 49a58.l.
        return am_call(c,0x49a58,r.pc==0xafb3eU?0xafb44U:(r.pc==0xafb58U?0xafb5eU:(r.pc==0xafb72U?0xafb78U:0xafbaaU)));
    // The BRA.W tables afb50 / afb6a / afb84 / afbb6.
    case 0xafb50:case 0xafb84:case 0xafb88:r.pc=0xafbbe;return true;
    case 0xafb54:case 0xafb6e:case 0xafb8c:r.pc=0xafe98;return true;
    case 0xafb6a:case 0xafb90:case 0xafb94:r.pc=0xafcf2;return true;
    case 0xafb98:case 0xafb9c:r.pc=0xafda6;return true;
    case 0xafba0:case 0xafbb6:r.pc=0xaff00;return true;
    case 0xafbba:r.pc=0xafe0a;return true;
    // ---- afbbe (N09 af626 install): BTST.B #7,61(A6); BEQ.W afbe2.
    case 0xafbbe:return ofr9_btst(c,r.a[6],0x61,7,0xafbe2,0xafbc8);
    case 0xafbc8:return ofr9_anim(c,0xb10f0,0xafbde);                                                      // anim b10f0.
    case 0xafbde:case 0xaffdc:r.pc=r.pc==0xafbdeU?0xafbf8U:0xafff6U;return true;                          // BRA.W afbf8 / afff6.
    case 0xafbe2:return ofr9_anim(c,0xb12ac,0xafbf8);                                                      // anim b12ac.
    case 0xafbf8:return am_call(c,0x49a58,0xafbfe);                                                        // JSR 49a58.l.
    // ANDI.W #7f,D0; ADD.W D0,2c(A6); MOVE.W #0,96(A6); CLR.B 63(A6); MOVE.L #afc16,(A6) (next PC, N09).
    case 0xafbfe:
        am_word(r.d[0],r.d[0]&0x7fU);
        if(!ofr9_add_word(c,0x2c,r.d[0]) || !ofr9_put(c,r.a[6],0x96,2,0) || !ofr9_put(c,r.a[6],0x63,1,0) || !ofr9_put(c,r.a[6],0,4,0xafc16))return false;
        r.pc=0xafc16;return true;
    // ---- the reaction heads afcf2 / afe98 / aff00 / b000a: MOVE.W #187f,D0; JSR 3af8.l.
    case 0xafcf2:return ofr9_sound(c,0xafcfc);
    case 0xafe98:return ofr9_sound(c,0xafea2);
    case 0xaff00:return ofr9_sound(c,0xaff0a);
    case 0xb000a:return ofr9_sound(c,0xb0014);
    // JSR b051a(PC).
    case 0xafcfc:return am_call(c,0xb051a,0xafd00);
    case 0xafea2:return am_call(c,0xb051a,0xafea6);
    case 0xaff0a:return am_call(c,0xb051a,0xaff0e);
    case 0xaff52:return am_call(c,0xb051a,0xaff56);
    case 0xaff86:return am_call(c,0xb051a,0xaff8a);
    // ---- afcf2 reaction.
    case 0xafd00:return ofr9_anim(c,0xb0fe8,0xafd16);                                                      // anim b0fe8.
    case 0xafd16:case 0xafd42:case 0xafdbc:case 0xafdd8:case 0xaff56:case 0xaff8a:case 0xaff9a:case 0xafff6:  // JSR 49a58.l.
        return am_call(c,0x49a58,r.pc==0xafd16U?0xafd1cU:(r.pc==0xafd42U?0xafd48U:(r.pc==0xafdbcU?0xafdc2U:(r.pc==0xafdd8U?0xafddeU:
            (r.pc==0xaff56U?0xaff5cU:(r.pc==0xaff8aU?0xaff90U:(r.pc==0xaff9aU?0xaffa0U:0xafffcU)))))));
    case 0xafd1c:am_byte(r.d[1],r.d[0]&0x1fU);return ofr9_side(c,0xafd38,0xafd2a);                       // MOVE.B D0,D1; ANDI.B #1f,D1; TST.B 5f(A6); BPL.W.
    case 0xafd2a:am_byte(r.d[1],r.d[1]+0x48U);if(!ofr9_bit(c,r.a[6],0x15,0,1))return false;r.pc=0xafd42;return true; // ADDI.B #48,D1; BSET #0,15.
    case 0xafd38:am_byte(r.d[1],r.d[1]+0x18U);if(!ofr9_bit(c,r.a[6],0x15,0,0))return false;r.pc=0xafd42;return true; // ADDI.B #18,D1; BCLR #0,15.
    case 0xafd48:return ofr9_speed(c,0x3ffU,0x200U,0xafd5a);                                              // (D0.W & 3ff) + 200, EXT.L, LSL.L #8.
    case 0xafd5a:case 0xafdf0:case 0xaffb2:                                                                // MOVE.L D0,36(A6); MOVE.L D1,3a(A6); JSR 49a58.l.
        return ofr9_store_speed(c,r.pc==0xafd5aU?0xafd68U:(r.pc==0xafdf0U?0xafdfeU:0xaffc0U));
    // ANDI.W #7f,D0; SUB.W D0,2c(A6); JSR 49274.l.
    case 0xafd68:case 0xafffc:
        am_word(r.d[0],r.d[0]&0x7fU);if(!ofr9_add_word(c,0x2c,0U-r.d[0]))return false;return am_call(c,0x49274,r.pc==0xafd68U?0xafd76U:0xb000aU);
    case 0xafd76:if(!ofr9_put(c,r.a[6],0,4,0xafd7c))return false;r.pc=0xafd7c;return true;                // MOVE.L #afd7c,(A6) (next PC).
    case 0xafd7c:if(!ofr9_fall(c,0xffffb000U))return false;return am_call(c,0x43ea4,0xafd8a);              // ADDI.L #ffffb000,3a(A6); JSR 43ea4.l.
    case 0xafd8a:return am_call(c,0x49fc6,0xafd90);                                                        // JSR 49fc6.l.
    case 0xafd90:return ofr9_carry(c,0xafda2,0xafd94);                                                     // BCC.W afda2 (C returned by 49fc6).
    case 0xafd94:case 0xaff40:case 0xb004c:return ofr9_release(c);                                         // parent BYTE 62 -= 1; JMP 2a00.l.
    case 0xafda2:case 0xafe94:case 0xaff4e:case 0xb005a:r.pc=0xb005e;return true;                         // BRA.W b005e (N09).
    // ---- afda6 reaction.
    case 0xafda6:return ofr9_anim(c,0xb13ee,0xafdbc);                                                      // anim b13ee.
    // MOVE.B D0,D1; ANDI.B #3f,D1; ADDI.B #20,D1; TST.W D0; BPL.W afdd8.
    case 0xafdc2:ofr9_spread(c);am_byte(r.d[1],r.d[1]+0x20U);r.pc=(r.d[0]&0x8000U)==0U?0xafdd8:0xafdd2;return true;
    case 0xafdd2:if(!ofr9_bit(c,r.a[6],0x15,0,2))return false;r.pc=0xafdd8;return true;                   // BCHG.B #0,15(A6).
    case 0xafdde:return ofr9_speed(c,0x7ffU,0x300U,0xafdf0);                                              // (D0.W & 7ff) + 300, EXT.L, LSL.L #8.
    case 0xafdfe:am_word(r.d[0],r.d[0]&0x7fU);if(!ofr9_add_word(c,0x2c,r.d[0]))return false;r.pc=0xafe30;return true; // ANDI.W #7f; ADD.W D0,2c; BRA.
    // ---- afe0a reaction.
    case 0xafe0a:return ofr9_anim(c,0xb13ee,0xafe20);                                                      // anim b13ee.
    // MOVEQ #0,D0; MOVE.L D0,36(A6); MOVE.L D0,3a(A6); BCLR.B #1,15(A6).
    case 0xafe20:
        r.d[0]=0;if(!ofr9_put(c,r.a[6],0x36,4,0) || !ofr9_put(c,r.a[6],0x3a,4,0) || !ofr9_bit(c,r.a[6],0x15,1,0))return false;r.pc=0xafe30;return true;
    // BSET.B #3,15(A6); ST.B 9b(A6); MOVE.L #afe40,(A6) (next PC).
    case 0xafe30:
        if(!ofr9_bit(c,r.a[6],0x15,3,1) || !ofr9_put(c,r.a[6],0x9b,1,0xff) || !ofr9_put(c,r.a[6],0,4,0xafe40))return false;r.pc=0xafe40;return true;
    case 0xafe40:if(!ofr9_fall(c,0xffff8000U))return false;return am_call(c,0x4be34,0xafe4e);              // ADDI.L #ffff8000,3a(A6); JSR 4be34.l.
    case 0xafe4e:return am_call(c,0x49fc6,0xafe54);                                                        // JSR 49fc6.l (C not read).
    // MOVE.L 36(A6),D0; ASR.L #6,D0; SUB.L D0,36(A6); TST.B 9b(A6); BEQ.W afe84.
    case 0xafe54:
        if(!ofr9_decay(c,0x36,6) || !ofr9_get(c,r.a[6],0x9b,1,value))return false;r.pc=value==0U?0xafe84:0xafe66;return true;
    case 0xafe66:return am_call(c,0xb0468,0xafe6a);                                                        // JSR b0468(PC) (N09).
    case 0xafe6a:return ofr9_carry(c,0xafe84,0xafe6e);                                                     // BCC.W afe84 (C returned by b0468).
    case 0xafe6e:return am_call(c,0x49a58,0xafe74);                                                        // JSR 49a58.l.
    case 0xafe74:r.pc=(r.d[0]&0x8000U)==0U?0xafe80:0xafe7a;return true;                                   // TST.W D0; BPL.W afe80.
    case 0xafe7a:if(!ofr9_put(c,r.a[6],0,4,0xaff00))return false;r.pc=0xafe80;return true;                // MOVE.L #aff00,(A6) (written only).
    case 0xafe80:if(!ofr9_put(c,r.a[6],0x9b,1,0))return false;r.pc=0xafe84;return true;                   // SF.B 9b(A6).
    case 0xafe84:return ofr9_btst(c,r.a[6],0x15,7,0xafe94,0xafe8e);                                       // BTST.B #7,15(A6); BEQ.W afe94.
    case 0xafe8e:if(!ofr9_put(c,r.a[6],0,4,0xafed8))return false;r.pc=0xafe94;return true;                // MOVE.L #afed8,(A6) (written only).
    // ---- afe98 reaction.
    case 0xafea6:return ofr9_anim(c,0xb0fe8,0xafebc);                                                      // anim b0fe8.
    case 0xafebc:return ofr9_side(c,0xafece,0xafec4);                                                      // TST.B 5f(A6); BPL.W afece.
    case 0xafec4:if(!ofr9_bit(c,r.a[6],0x15,0,1))return false;r.pc=0xafed4;return true;                   // BSET.B #0,15(A6); BRA.W afed4.
    case 0xafece:if(!ofr9_bit(c,r.a[6],0x15,0,0))return false;r.pc=0xafed4;return true;                   // BCLR.B #0,15(A6).
    case 0xafed4:r.pc=0xaff24;return true;                                                                 // BRA.W aff24.
    // ---- aff00 reaction.
    case 0xaff0e:return ofr9_anim(c,0xb1076,0xaff24);                                                      // anim b1076.
    case 0xaff24:return am_call(c,0x49274,0xaff2a);                                                        // JSR 49274.l.
    case 0xaff2a:if(!ofr9_put(c,r.a[6],0,4,0xaff30))return false;r.pc=0xaff30;return true;                // MOVE.L #aff30,(A6) (next PC).
    case 0xaff30:return am_call(c,0x43e34,0xaff36);                                                        // JSR 43e34.l (installed value).
    case 0xaff36:return am_call(c,0x49fc6,0xaff3c);                                                        // JSR 49fc6.l.
    case 0xaff3c:return ofr9_carry(c,0xaff4e,0xaff40);                                                     // BCC.W aff4e (C returned by 49fc6).
    // ---- aff52 / aff86 reactions (index a / b).
    case 0xaff5c:ofr9_spread(c);return ofr9_side(c,0xaff78,0xaff6a);                                       // MOVE.B D0,D1; ANDI.B #3f,D1; TST.B 5f(A6).
    case 0xaff6a:am_byte(r.d[1],r.d[1]+0x50U);if(!ofr9_bit(c,r.a[6],0x15,0,1))return false;r.pc=0xaff82;return true; // ADDI.B #50,D1; BSET #0,15.
    case 0xaff78:am_byte(r.d[1],r.d[1]-0xfU);if(!ofr9_bit(c,r.a[6],0x15,0,0))return false;r.pc=0xaff82;return true;  // SUBI.B #f,D1; BCLR #0,15.
    case 0xaff82:r.pc=0xaff9a;return true;                                                                 // BRA.W aff9a.
    case 0xaff90:ofr9_spread(c);am_byte(r.d[1],r.d[1]+0x20U);r.pc=0xaff9a;return true;                    // MOVE.B D0,D1; ANDI.B #3f; ADDI.B #20.
    case 0xaffa0:return ofr9_speed(c,0x7ffU,0xa00U,0xaffb2);                                              // (D0.W & 7ff) + a00, EXT.L, LSL.L #8.
    case 0xaffc0:r.pc=(r.d[0]&0x8000U)!=0U?0xaffe0:0xaffc6;return true;                                   // TST.W D0; BMI.W affe0.
    case 0xaffc6:return ofr9_anim(c,0xb0fe8,0xaffdc);                                                      // anim b0fe8.
    case 0xaffe0:return ofr9_anim(c,0xb13ee,0xafff6);                                                      // anim b13ee.
    case 0xb0014:if(!ofr9_put(c,r.a[6],0,4,0xb001a))return false;r.pc=0xb001a;return true;                // MOVE.L #b001a,(A6) (next PC).
    // CMPI.B #b,5e(A6); BNE.W b0032.
    case 0xb001a:if(!ofr9_get(c,r.a[6],0x5e,1,value))return false;r.pc=value!=0xbU?0xb0032:0xb0024;return true;
    case 0xb0024:if(!ofr9_decay(c,0x36,2))return false;r.pc=0xb003c;return true;                           // LONG 36 -= ASR.L(LONG 36, 2); BRA.W.
    case 0xb0032:if(!ofr9_decay(c,0x3a,2))return false;r.pc=0xb003c;return true;                           // LONG 3a -= ASR.L(LONG 3a, 2).
    case 0xb003c:return am_call(c,0x43ea4,0xb0042);                                                        // JSR 43ea4.l.
    case 0xb0042:return am_call(c,0x49fc6,0xb0048);                                                        // JSR 49fc6.l.
    case 0xb0048:return ofr9_carry(c,0xb005a,0xb004c);                                                     // BCC.W b005a (C returned by 49fc6).
    // ---- b051a (helper): CMPI.W #0,92(A6); BEQ.W b057c.
    case 0xb051a:if(!ofr9_get(c,r.a[6],0x92,2,value))return false;r.pc=value==0U?0xb057c:0xb0524;return true;
    // MOVE.W #0,-(A7) x3; MOVE.W 94(A6),-(A7); MOVE.W 92(A6),-(A7); MOVE.W #10,-(A7); MOVE.W #0,-(A7); MOVEA.L #b3dbc,A0; MOVE.W #14,D0;
    // MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0xb0524:{
        std::uint32_t other=0;
        if(!am_push(c,2,0) || !am_push(c,2,0) || !am_push(c,2,0) || !ofr9_get(c,r.a[6],0x94,2,value) || !am_push(c,2,value) ||
           !ofr9_get(c,r.a[6],0x92,2,other) || !am_push(c,2,other) || !am_push(c,2,0x10) || !am_push(c,2,0))return false;
        r.a[0]=0xb3dbc;am_word(r.d[0],0x14);r.a[1]=0x100bf4;return am_call(c,0x2986,0xb0556);}
    // MOVEM.W (A7)+,D0-D6 (each WORD sign-extended to the LONG; no flag change); BCC.W b057c (C returned by 2986).
    case 0xb0556:
        for(unsigned int i=0;i<7U;++i){if(!am_pop(c,2,value))return false;r.d[i]=am_extend_word(value);}
        return ofr9_carry(c,0xb057c,0xb055e);
    // MOVE.W D2,76(A0); MOVE.W D3,78(A0); MOVE.W D4,7a(A0); MOVE.W D5,7c(A0); MOVE.W D6,7e(A0); JSR 49214.l.
    case 0xb055e:
        for(unsigned int i=0;i<5U;++i)if(!ofr9_put(c,r.a[0],0x76U+2U*i,2,r.d[2U+i]))return false;
        return am_call(c,0x49214,0xb0578);
    case 0xb0578:r.carry=AnimationCarrySet;r.pc=0xb057c;return true;                                       // ORI.B #1,CCR (Set; RTS b057c).
    default:
        return am_error(c,"unsupported animation objects fr9 PC");
    }
}
}
