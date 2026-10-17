#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ob3c_b(std::uint32_t value) {return value&255U;}
std::uint32_t ob3c_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ob3c_sext_byte(std::uint32_t value) {return (value&0x80U)!=0U?((value&255U)|0xff00U):(value&255U);}
// The low WORD as a signed 16-bit value.
std::int32_t ob3c_signed_word(std::uint32_t value) {
    const std::uint32_t w=value&65535U;return (w&0x8000U)!=0U?static_cast<std::int32_t>(w)-65536:static_cast<std::int32_t>(w);
}
bool ob3c_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob3c_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG); the fall-through enters the installed callback.
bool ob3c_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ob3c_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// BTST.B #bit,d16(An): true when the bit is 1.
bool ob3c_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob3c_get(c,base,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BTST.B #0,15(A6); BEQ.W taken (bit 0 clear) / fall (bit 0 set).
bool ob3c_face(AnimationMachineContext& c,std::uint32_t fall,std::uint32_t taken) {
    bool bit=false;if(!ob3c_bit(c,c.s.a[6],0x15,0,bit))return false;c.s.pc=bit?fall:taken;return true;
}
// Bcc on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob3c_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b3c caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.l (animation list start).
bool ob3c_anim(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #n,D0; MOVE.B #0,D1; JSR 8ebe.l.
bool ob3c_8ebe(AnimationMachineContext& c,std::uint32_t n,std::uint32_t return_pc) {
    am_word(c.s.d[0],n);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #n,20(A6); MOVE.L address.l,22(A6) (a LONG of the bank window, read through the live bus).
bool ob3c_bank_head(AnimationMachineContext& c,std::uint32_t n,std::uint32_t address) {
    std::uint32_t value=0;
    if(!ob3c_put(c,c.s.a[6],0x20,2,n) || !am_read(c,address,4,value))return false;return ob3c_put(c,c.s.a[6],0x22,4,value);
}
// MOVE.W (An)+,D0; MOVE.W (An)+,D1 (a WORD pair of a fixed ROM table, read through the live bus).
bool ob3c_pair(AnimationMachineContext& c,std::uint32_t& a) {
    std::uint32_t value=0;
    if(!am_read(c,a,2,value))return false;am_word(c.s.d[0],value);a+=2U;
    if(!am_read(c,a,2,value))return false;am_word(c.s.d[1],value);a+=2U;return true;
}
// NEG.W Dn.
void ob3c_neg_word(std::uint32_t& r) {am_word(r,0U-ob3c_w(r));}
}
// Objects B3c (71 block starts): the 28ae children of the N28 range-outside chain, 2d7be..2d8b8 (20; B3a 2b548: installs 2d810 / 2d8a0),
// 2d916..2d9dc (14; B3a 2ba50: installs 2d98e) and 2db06..2dbda (16; B3b 2bdbe: installs 2dbac), and the callee 1c114..1c1ba (15; B3a 2b636)
// with its shared tail 2291a..2296a (6). Every exit is routed (289e 288c 2986 4c2fa 8ebe 43e34 43e08 49f8c 49fc6 1d198 1bf80 49290 491c4,
// JMP 2a00, JMP 491b6). Known C: none produced; the 6 consumers 1c128 (BCS, 289e), 2d85e 2d8ac 2d9c6 2dbce (BCC, 49fc6) and 2dbb2 (BCS, 288c)
// read a known C or fail. Data through the live bus (no limit test, as in the original): the bank LONGs 20009c / 200094, the WORD tables
// 2d8b8 / 2d8fc / 2d904 / 2d9dc, the LONG tables 2284c and its four 4-LONG child tables, and LONG (LONG 22(A6) + 4 * WORD). The table bytes
// stay unrouted. No X / DIV / TRAP / port / bank write.
bool animation_objects_b3c_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool bit=false;
    switch(r.pc) {
    // ---- 1c114 (callee): LEA -7348(A5),A0; TST.W D0; BEQ.W 1c122.
    case 0x1c114:r.a[0]=r.a[5]-0x7348U;r.pc=ob3c_w(r.d[0])==0U?0x1c122:0x1c11e;return true;
    case 0x1c11e:r.a[0]=r.a[5]-0x7258U;r.pc=0x1c122;return true;           // LEA -7258(A5),A0.
    case 0x1c122:return am_call(c,0x289e,0x1c128);                           // JSR 289e.l (readiness: C Clear when LONG (A0) = 270e).
    case 0x1c128:return ob3c_carry(c,0x1c12c,0x1c12e);                       // BCS.W 1c12e (C returned by 289e).
    case 0x1c12c:case 0x1c146:case 0x2d8b6:case 0x2d9da:case 0x2dbd8:return am_return(c);   // RTS.
    // MOVEA.L 8c(A0),A4; BTST.B #2,10f001.l; BNE.W 1c14c.
    case 0x1c12e:
        if(!ob3c_get(c,r.a[0],0x8c,4,value))return false;r.a[4]=value;
        if(!ob3c_bit(c,0x10f001,0,2,bit))return false;r.pc=bit?0x1c14c:0x1c13e;return true;
    // TST.B 7(A4); BNE.W 1c148.
    case 0x1c13e:if(!ob3c_get(c,r.a[4],7,1,value))return false;r.pc=ob3c_b(value)!=0U?0x1c148:0x1c146;return true;
    // SUBQ.B #1,7(A4).
    case 0x1c148:if(!ob3c_get(c,r.a[4],7,1,value) || !ob3c_put(c,r.a[4],7,1,value-1U))return false;r.pc=0x1c14c;return true;
    // MOVEM.W D0/D2-D3,-(A7) (D3.W, D2.W, D0.W pushed: D0.W at the lowest address); MOVEQ #0,D0; MOVE.B 9e(A0),D0; ADD.W D0,D0 twice;
    // LEA 2284c(PC),A1; MOVEA.L (A1,D0.W),A1; MOVEQ #0,D0; MOVE.B 6(A4),D0; CMPI.B #4,D0; BCS.W 1c172 (unsigned).
    case 0x1c14c:
        if(!am_push(c,2,ob3c_w(r.d[3])) || !am_push(c,2,ob3c_w(r.d[2])) || !am_push(c,2,ob3c_w(r.d[0])))return false;
        if(!ob3c_get(c,r.a[0],0x9e,1,value))return false;r.d[0]=ob3c_b(value);am_word(r.d[0],r.d[0]*2U);am_word(r.d[0],r.d[0]*2U);
        if(!am_read(c,am_index(0x2284cU,r.d[0]),4,value))return false;r.a[1]=value;
        if(!ob3c_get(c,r.a[4],6,1,value))return false;r.d[0]=ob3c_b(value);r.pc=r.d[0]<4U?0x1c172:0x1c170;return true;
    case 0x1c170:r.d[0]=0;r.pc=0x1c172;return true;                          // MOVEQ #0,D0.
    // ADD.W D0,D0 twice; MOVEA.L (A1,D0.W),A0; MOVE.W #a,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0x1c172:
        am_word(r.d[0],r.d[0]*2U);am_word(r.d[0],r.d[0]*2U);
        if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[0]=value;am_word(r.d[0],0xa);r.a[1]=0x100bf4;return am_call(c,0x2986,0x1c18a);
    // MOVE.B 60(A6),60(A0); MOVEM.W (A7)+,D0/D2-D3 (each WORD sign-extended to the whole register); MOVE.W D0,76(A0); MOVE.B #20,D0;
    // BTST.B #0,15(A6); BEQ.W 1c1ae.
    case 0x1c18a:
        if(!ob3c_get(c,r.a[6],0x60,1,value) || !ob3c_put(c,r.a[0],0x60,1,value))return false;
        if(!am_pop(c,2,value))return false;r.d[0]=am_extend_word(value);
        if(!am_pop(c,2,value))return false;r.d[2]=am_extend_word(value);
        if(!am_pop(c,2,value))return false;r.d[3]=am_extend_word(value);
        if(!ob3c_put(c,r.a[0],0x76,2,r.d[0]))return false;am_byte(r.d[0],0x20);return ob3c_face(c,0x1c1a6,0x1c1ae);
    // NEG.B D0; ADDI.B #80,D0; NEG.W D2.
    case 0x1c1a6:am_byte(r.d[0],0U-ob3c_b(r.d[0]));am_byte(r.d[0],ob3c_b(r.d[0])+0x80U);ob3c_neg_word(r.d[2]);r.pc=0x1c1ae;return true;
    // MOVE.B D0,78(A0); MOVE.B #ff,D0; BRA.W 2291a.
    case 0x1c1ae:if(!ob3c_put(c,r.a[0],0x78,1,r.d[0]))return false;am_byte(r.d[0],0xff);r.pc=0x2291a;return true;
    // ---- 2291a (shared tail): JSR 4c2fa.l.
    case 0x2291a:return am_call(c,0x4c2fa,0x22920);
    // MOVEA.L 3e(A6),A2; MOVE.L 36(A6),D0; MOVE.L 3a(A6),D1; CMPA.W #0,A2 (32-bit compare with 0); BEQ.W 22944.
    case 0x22920:
        if(!ob3c_get(c,r.a[6],0x3e,4,value))return false;r.a[2]=value;
        if(!ob3c_get(c,r.a[6],0x36,4,value))return false;r.d[0]=value;
        if(!ob3c_get(c,r.a[6],0x3a,4,value))return false;r.d[1]=value;r.pc=r.a[2]==0U?0x22944:0x22934;return true;
    // ADD.L 14(A2),D0; SUB.L 1c(A2),D0; ADD.L 18(A2),D1; SUB.L 20(A2),D1.
    case 0x22934:
        if(!ob3c_get(c,r.a[2],0x14,4,value))return false;r.d[0]+=value;
        if(!ob3c_get(c,r.a[2],0x1c,4,value))return false;r.d[0]-=value;
        if(!ob3c_get(c,r.a[2],0x18,4,value))return false;r.d[1]+=value;
        if(!ob3c_get(c,r.a[2],0x20,4,value))return false;r.d[1]-=value;r.pc=0x22944;return true;
    case 0x22944:r.pc=r.a[1]==0U?0x2295c:0x2294c;return true;               // CMPA.W #0,A1; BEQ.W 2295c.
    // SUB.L 14(A1),D0; ADD.L 1c(A1),D0; SUB.L 18(A1),D1; ADD.L 20(A1),D1.
    case 0x2294c:
        if(!ob3c_get(c,r.a[1],0x14,4,value))return false;r.d[0]-=value;
        if(!ob3c_get(c,r.a[1],0x1c,4,value))return false;r.d[0]+=value;
        if(!ob3c_get(c,r.a[1],0x18,4,value))return false;r.d[1]-=value;
        if(!ob3c_get(c,r.a[1],0x20,4,value))return false;r.d[1]+=value;r.pc=0x2295c;return true;
    // MOVE.L D0,36(A0); MOVE.L D1,3a(A0); JMP 491b6.l.
    case 0x2295c:if(!ob3c_put(c,r.a[0],0x36,4,r.d[0]) || !ob3c_put(c,r.a[0],0x3a,4,r.d[1]))return false;r.pc=0x491b6;return true;
    // ---- 2d7be (28ae child): MOVE.W #f2,20(A6); MOVE.L 20009c.l,22(A6); MOVE.W #208,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x2d7be:if(!ob3c_bank_head(c,0xf2,0x20009c))return false;return ob3c_8ebe(c,0x208,0x2d7da);
    // MOVEA.L c(A6),A0; MOVE.B 7c(A0),7c(A6); MOVE.B 7e(A0),7e(A6); BTST.B #7,15(A0); BEQ.W 2d87a.
    case 0x2d7da:
        if(!ob3c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob3c_get(c,r.a[0],0x7c,1,value) || !ob3c_put(c,r.a[6],0x7c,1,value))return false;
        if(!ob3c_get(c,r.a[0],0x7e,1,value) || !ob3c_put(c,r.a[6],0x7e,1,value))return false;
        if(!ob3c_bit(c,r.a[0],0x15,7,bit))return false;r.pc=bit?0x2d7f4:0x2d87a;return true;
    case 0x2d7f4:return ob3c_anim(c,0x2dbda,0x2d80a);                        // LEA 2dbda.l,A1; MOVEA.L #2dbda,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2d80a:return ob3c_install(c,0x2d810);                             // MOVE.L #2d810,(A6).
    case 0x2d89a:return ob3c_install(c,0x2d8a0);                             // MOVE.L #2d8a0,(A6).
    case 0x2d988:return ob3c_install(c,0x2d98e);                             // MOVE.L #2d98e,(A6).
    case 0x2dba6:return ob3c_install(c,0x2dbac);                             // MOVE.L #2dbac,(A6).
    case 0x2d810:case 0x2d8a0:return am_call(c,0x43e34,r.pc+6U);             // JSR 43e34.l (installed values).
    // MOVEQ #0,D0; MOVE.B 13(A6),D0; ADDQ.B #1,D0; BCS.W 2d830 (carry out of the BYTE: the old BYTE was ff).
    case 0x2d816:
        if(!ob3c_get(c,r.a[6],0x13,1,value))return false;r.d[0]=ob3c_b(value+1U);r.pc=ob3c_b(value)==0xffU?0x2d830:0x2d822;return true;
    // MULS.W 3a(A6),D0 (signed 16 x 16 -> 32); ASR.L #8,D0 (explicit sign refill); SUB.W 3a(A6),D0; SUB.W D0,46(A6).
    case 0x2d822: {
        if(!ob3c_get(c,r.a[6],0x3a,2,value))return false;
        const std::int32_t a=ob3c_signed_word(r.d[0]);const std::int32_t b=ob3c_signed_word(value);
        const std::int32_t product=a*b;                                      // |a*b| <= 2^30: no overflow.
        r.d[0]=static_cast<std::uint32_t>(product);                          // modulo 2^32 (well defined).
        r.d[0]=(r.d[0]>>8)|((r.d[0]&0x80000000U)!=0U?0xff000000U:0U);
        am_word(r.d[0],r.d[0]-value);
        if(!ob3c_get(c,r.a[6],0x46,2,other) || !ob3c_put(c,r.a[6],0x46,2,other-r.d[0]))return false;r.pc=0x2d830;return true;}
    // MOVE.B 8e(A6),D0; MOVE.B 8f(A6),D1; EXT.W D0; EXT.W D1; BTST.B #0,15(A6); BEQ.W 2d848.
    case 0x2d830:
        if(!ob3c_get(c,r.a[6],0x8e,1,value))return false;am_word(r.d[0],ob3c_sext_byte(value));
        if(!ob3c_get(c,r.a[6],0x8f,1,value))return false;am_word(r.d[1],ob3c_sext_byte(value));return ob3c_face(c,0x2d846,0x2d848);
    case 0x2d846:ob3c_neg_word(r.d[0]);r.pc=0x2d848;return true;              // NEG.W D0.
    // SUB.W 36(A6),D0; SUB.W 3a(A6),D1; SUB.W D0,42(A6); SUB.W D1,46(A6); JSR 49fc6.l.
    case 0x2d848:
        if(!ob3c_get(c,r.a[6],0x36,2,value))return false;am_word(r.d[0],r.d[0]-value);
        if(!ob3c_get(c,r.a[6],0x3a,2,value))return false;am_word(r.d[1],r.d[1]-value);
        if(!ob3c_get(c,r.a[6],0x42,2,value) || !ob3c_put(c,r.a[6],0x42,2,value-r.d[0]))return false;
        if(!ob3c_get(c,r.a[6],0x46,2,value) || !ob3c_put(c,r.a[6],0x46,2,value-r.d[1]))return false;return am_call(c,0x49fc6,0x2d85e);
    case 0x2d85e:return ob3c_carry(c,0x2d868,0x2d862);                       // BCC.W 2d868 (C returned by 49fc6).
    case 0x2d8ac:return ob3c_carry(c,0x2d8b6,0x2d8b0);
    case 0x2d9c6:return ob3c_carry(c,0x2d9da,0x2d9ca);
    case 0x2dbce:return ob3c_carry(c,0x2dbd8,0x2dbd2);
    case 0x2dbb2:return ob3c_carry(c,0x2dbb6,0x2dbbc);                       // BCS.W 2dbbc (C returned by 288c).
    case 0x2d862:case 0x2d8b0:case 0x2dbb6:case 0x2dbd2:r.pc=0x2a00;return true;   // JMP 2a00.l (object removal).
    // MOVEQ #0,D0; MOVE.B 13(A6),D0; SUBI.W #ff,D0; ASR.W #3,D0 (WORD, explicit sign refill); SUB.B D0,13(A6); RTS.
    case 0x2d868:
        if(!ob3c_get(c,r.a[6],0x13,1,value))return false;r.d[0]=ob3c_w(value-0xffU);
        r.d[0]=(r.d[0]>>3)|((r.d[0]&0x8000U)!=0U?0xe000U:0U);
        if(!ob3c_put(c,r.a[6],0x13,1,value-r.d[0]))return false;return am_return(c);
    // MOVE.W 36(A6),D0; MOVE.W 3a(A6),D1; ADD.W D0,2e(A6); ADD.W D1,32(A6); MOVEA.L #2df6a,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2d87a:
        if(!ob3c_get(c,r.a[6],0x36,2,value))return false;am_word(r.d[0],value);
        if(!ob3c_get(c,r.a[6],0x3a,2,value))return false;am_word(r.d[1],value);
        if(!ob3c_get(c,r.a[6],0x2e,2,value) || !ob3c_put(c,r.a[6],0x2e,2,value+r.d[0]))return false;
        if(!ob3c_get(c,r.a[6],0x32,2,value) || !ob3c_put(c,r.a[6],0x32,2,value+r.d[1]))return false;return ob3c_anim(c,0x2df6a,0x2d89a);
    case 0x2d8a6:case 0x2d9c0:case 0x2dbc8:return am_call(c,0x49fc6,r.pc+6U);   // JSR 49fc6.l.
    // ---- 2d916 (28ae child): MOVEA.L c(A6),A0; MOVE.W 8a(A0),D0; JSR 1d198.l.
    case 0x2d916:
        if(!ob3c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob3c_get(c,r.a[0],0x8a,2,value))return false;am_word(r.d[0],value);return am_call(c,0x1d198,0x2d924);
    // MOVEA.L c(A6),A0; MOVE.W 88(A6),D0; JSR 1bf80.l.
    case 0x2d924:
        if(!ob3c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob3c_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);return am_call(c,0x1bf80,0x2d932);
    // ANDI.W #ff,D0; ADD.W D0,D0; LEA 2d904(PC),A0; MOVE.W (A0,D0.W),D0; MOVE.W D0,D7; MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1;
    // ADD.W D7,D7 twice; MOVEA.L (A1,D7.W),A1; JSR 49f8c.l.
    case 0x2d932:
        am_word(r.d[0],r.d[0]&0xffU);am_word(r.d[0],r.d[0]*2U);r.a[0]=0x2d904;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);am_word(r.d[7],value);am_word(r.d[0],0x100);
        r.a[0]=am_index(r.a[6],0x26);if(!ob3c_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
        am_word(r.d[7],r.d[7]*2U);am_word(r.d[7],r.d[7]*2U);
        if(!am_read(c,am_index(r.a[1],r.d[7]),4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,0x2d95c);
    // MOVEA.L c(A6),A4; MOVE.W 8a(A4),D0; LEA 2d8fc(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x2d95c:
        if(!ob3c_get(c,r.a[6],0xc,4,value))return false;r.a[4]=value;
        if(!ob3c_get(c,r.a[4],0x8a,2,value))return false;am_word(r.d[0],value);r.a[0]=0x2d8fc;am_word(r.d[0],r.d[0]*2U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;return ob3c_8ebe(c,value,0x2d978);
    case 0x2d978:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x2d982);        // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0x2d982:return am_call(c,0x491c4,0x2d988);                          // JSR 491c4.l.
    // MOVEA.L c(A6),A0; MOVEQ #0,D0; MOVE.B 7c(A0),D0; ADD.W D0,D0 twice; LEA 2d8b8(PC),A4; ADDA.W D0,A4; MOVE.W (A4)+,D0; MOVE.W (A4)+,D1;
    // BTST.B #0,15(A6); BEQ.W 2d9b2.
    case 0x2d98e:
        if(!ob3c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob3c_get(c,r.a[0],0x7c,1,value))return false;r.d[0]=ob3c_b(value);am_word(r.d[0],r.d[0]*2U);am_word(r.d[0],r.d[0]*2U);
        r.a[4]=am_index(0x2d8b8,r.d[0]);if(!ob3c_pair(c,r.a[4]))return false;return ob3c_face(c,0x2d9b0,0x2d9b2);
    case 0x2d9b0:case 0x2db86:ob3c_neg_word(r.d[0]);r.pc+=2U;return true;    // NEG.W D0.
    // MOVE.W D0,2e(A6); MOVE.W D1,32(A6); JSR 43e34.l.
    case 0x2d9b2:if(!ob3c_put(c,r.a[6],0x2e,2,r.d[0]) || !ob3c_put(c,r.a[6],0x32,2,r.d[1]))return false;return am_call(c,0x43e34,0x2d9c0);
    // MOVEA.L c(A6),A0; MOVE.B #ff,62(A0); JMP 2a00.l.
    case 0x2d9ca:if(!ob3c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ob3c_put(c,r.a[0],0x62,1,0xff))return false;r.pc=0x2a00;return true;
    // ---- 2db06 (28ae child): MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); MOVEA.L #2ed9c,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2db06:if(!ob3c_bank_head(c,0xe2,0x200094))return false;return ob3c_anim(c,0x2ed9c,0x2db24);
    case 0x2db24:return ob3c_8ebe(c,0x204,0x2db32);                          // MOVE.W #204,D0; MOVE.B #0,D1; JSR 8ebe.l.
    // MOVEA.L c(A6),A0; MOVEQ #0,D0; MOVE.B 9c(A0),D0; ADDI.W #100,D0; MOVE.W D0,2c(A6); MOVE.B 7d(A0),7d(A6); MOVE.B 7c(A0),7c(A6);
    // TST.L 36(A0); BPL.W 2db6a.
    case 0x2db32:
        if(!ob3c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ob3c_get(c,r.a[0],0x9c,1,value))return false;r.d[0]=ob3c_b(value);am_word(r.d[0],r.d[0]+0x100U);
        if(!ob3c_put(c,r.a[6],0x2c,2,r.d[0]))return false;
        if(!ob3c_get(c,r.a[0],0x7d,1,value) || !ob3c_put(c,r.a[6],0x7d,1,value))return false;
        if(!ob3c_get(c,r.a[0],0x7c,1,value) || !ob3c_put(c,r.a[6],0x7c,1,value))return false;
        if(!ob3c_get(c,r.a[0],0x36,4,value))return false;r.pc=(value&0x80000000U)!=0U?0x2db58:0x2db6a;return true;
    // BSET.B #0,15(A6); MOVE.B 7d(A6),D0; NEG.B D0; ADDQ.B #4,D0; MOVE.B D0,7d(A6).
    case 0x2db58:
        if(!ob3c_get(c,r.a[6],0x15,1,value) || !ob3c_put(c,r.a[6],0x15,1,value|1U))return false;
        if(!ob3c_get(c,r.a[6],0x7d,1,value))return false;am_byte(r.d[0],0U-ob3c_b(value));am_byte(r.d[0],ob3c_b(r.d[0])+4U);
        if(!ob3c_put(c,r.a[6],0x7d,1,r.d[0]))return false;r.pc=0x2db6a;return true;
    // MOVEQ #0,D0; MOVE.B 7c(A6),D0; LSL.W #3,D0; LEA 2d9dc(PC),A1; ADDA.W D0,A1; MOVE.W (A1)+,D0; MOVE.W (A1)+,D1; BTST.B #0,15(A6); BEQ.W 2db88.
    case 0x2db6a:
        if(!ob3c_get(c,r.a[6],0x7c,1,value))return false;r.d[0]=ob3c_b(value)<<3;
        r.a[1]=am_index(0x2d9dc,r.d[0]);if(!ob3c_pair(c,r.a[1]))return false;return ob3c_face(c,0x2db86,0x2db88);
    // ADD.W 42(A0),D0; ADD.W 46(A0),D1; LEA 538e(A5),A1; SUB.W 14(A1),D0; SUB.W 18(A1),D1; LEA 2e(A6),A0; JSR 43e08.l.
    case 0x2db88:
        if(!ob3c_get(c,r.a[0],0x42,2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!ob3c_get(c,r.a[0],0x46,2,value))return false;am_word(r.d[1],r.d[1]+value);
        r.a[1]=am_index(r.a[5],0x538e);
        if(!ob3c_get(c,r.a[1],0x14,2,value))return false;am_word(r.d[0],r.d[0]-value);
        if(!ob3c_get(c,r.a[1],0x18,2,value))return false;am_word(r.d[1],r.d[1]-value);
        r.a[0]=am_index(r.a[6],0x2e);return am_call(c,0x43e08,0x2dba6);
    case 0x2dbac:return am_call(c,0x288c,0x2dbb2);                           // JSR 288c.l (installed value).
    // MOVE.W 1e(A0),1e(A6); JSR 43e34.l.
    case 0x2dbbc:if(!ob3c_get(c,r.a[0],0x1e,2,value) || !ob3c_put(c,r.a[6],0x1e,2,value))return false;return am_call(c,0x43e34,0x2dbc8);
    default:return am_error(c,"unsupported animation objects b3c PC");
    }
}
}
