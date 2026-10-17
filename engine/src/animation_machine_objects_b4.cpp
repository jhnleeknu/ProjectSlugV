#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ob4_b(std::uint32_t value) {return value&255U;}
std::uint32_t ob4_w(std::uint32_t value) {return value&65535U;}
// The low WORD / BYTE as a signed value.
std::int32_t ob4_signed_word(std::uint32_t value) {
    const std::uint32_t w=value&65535U;return (w&0x8000U)!=0U?static_cast<std::int32_t>(w)-65536:static_cast<std::int32_t>(w);
}
std::int32_t ob4_signed_byte(std::uint32_t value) {
    const std::uint32_t b=value&255U;return (b&0x80U)!=0U?static_cast<std::int32_t>(b)-256:static_cast<std::int32_t>(b);
}
// ASR.L #n (1 <= n <= 8): explicit sign refill of the n vacated bits.
std::uint32_t ob4_asr_long(std::uint32_t value,unsigned int n) {
    return (value>>n)|((value&0x80000000U)!=0U?~(0xffffffffU>>n):0U);
}
// ASR.W #n (1 <= n <= 8) on the low WORD of a register; the upper WORD is kept.
void ob4_asr_word(std::uint32_t& r,unsigned int n) {
    const std::uint32_t w=r&65535U;
    am_word(r,(w>>n)|((w&0x8000U)!=0U?((0xffffU<<(16U-n))&0xffffU):0U));
}
// MULS.W: signed 16 x 16 -> 32 (|a*b| <= 2^30: no overflow); the result modulo 2^32 is well defined.
std::uint32_t ob4_muls(std::uint32_t reg,std::uint32_t word) {
    const std::int32_t product=ob4_signed_word(reg)*ob4_signed_word(word);return static_cast<std::uint32_t>(product);
}
bool ob4_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob4_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// ADD/SUB/ADDI/SUBI/ADDQ/SUBQ/ORI on a memory operand d16(An): read, add `delta` (modulo the size), write.
bool ob4_add(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t delta) {
    std::uint32_t value=0;if(!ob4_get(c,base,displacement,size,value))return false;return ob4_put(c,base,displacement,size,value+delta);
}
// Copy a field of A6 to the same displacement of A0 (MOVE.x d(A6),d(A0)).
bool ob4_copy(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size) {
    std::uint32_t value=0;if(!ob4_get(c,c.s.a[6],displacement,size,value))return false;return ob4_put(c,c.s.a[0],displacement,size,value);
}
// MOVE.L d(A6),e(A6).
bool ob4_move_long(AnimationMachineContext& c,std::uint32_t from,std::uint32_t to) {
    std::uint32_t value=0;if(!ob4_get(c,c.s.a[6],from,4,value))return false;return ob4_put(c,c.s.a[6],to,4,value);
}
// MOVE.L #value,(A6) (installed callback LONG); the fall-through enters the installed callback.
bool ob4_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ob4_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVE.L #value,(A6) followed by the next block (not the installed value).
bool ob4_callback(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next) {
    if(!ob4_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next;return true;
}
// BTST.B #bit,d16(An): true when the bit is 1.
bool ob4_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob4_get(c,base,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BTST.B #bit,d16(A6); Bcc: one_pc when the bit is 1, zero_pc when it is 0.
bool ob4_test(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,std::uint32_t one_pc,std::uint32_t zero_pc) {
    bool set=false;if(!ob4_bit(c,c.s.a[6],displacement,bit,set))return false;c.s.pc=set?one_pc:zero_pc;return true;
}
// BSET.B / BCLR.B #bit,d16(A6).
bool ob4_bset(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;if(!ob4_get(c,c.s.a[6],displacement,1,value))return false;return ob4_put(c,c.s.a[6],displacement,1,value|(1U<<bit));
}
bool ob4_bclr(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;if(!ob4_get(c,c.s.a[6],displacement,1,value))return false;return ob4_put(c,c.s.a[6],displacement,1,value&~(1U<<bit));
}
// Bcc on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob4_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b4 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.l (animation list start).
bool ob4_anim(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #n,D0; MOVE.B #d1,D1; JSR 8ebe.l.
bool ob4_8ebe(AnimationMachineContext& c,std::uint32_t n,std::uint32_t d1,std::uint32_t return_pc) {
    am_word(c.s.d[0],n);am_byte(c.s.d[1],d1);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #n,20(A6); MOVE.L address.l,22(A6) (a LONG of the bank window, read through the live bus).
bool ob4_bank_head(AnimationMachineContext& c,std::uint32_t n,std::uint32_t address) {
    std::uint32_t value=0;
    if(!ob4_put(c,c.s.a[6],0x20,2,n) || !am_read(c,address,4,value))return false;return ob4_put(c,c.s.a[6],0x22,4,value);
}
// MOVE.L #speed,D0; MOVE.B 78(A6),D1; JSR 443d2.l.
bool ob4_443d2(AnimationMachineContext& c,std::uint32_t speed,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.d[0]=speed;if(!ob4_get(c,c.s.a[6],0x78,1,value))return false;am_byte(c.s.d[1],value);
    return am_call(c,0x443d2,return_pc);
}
// ADD.L D0,36(A6); MOVE.L D1,3a(A6) (the 443d2 result).
bool ob4_speed(AnimationMachineContext& c) {
    return ob4_add(c,c.s.a[6],0x36,4,c.s.d[0]) && ob4_put(c,c.s.a[6],0x3a,4,c.s.d[1]);
}
// MOVE.W #value,68(A6); MOVE.W #value,1e(A6) (or of A0).
bool ob4_pair68(AnimationMachineContext& c,std::uint32_t base,std::uint32_t value) {
    return ob4_put(c,base,0x68,2,value) && ob4_put(c,base,0x1e,2,value);
}
// MOVE.W d(A6),D0; [ADDI.W/SUBI.W #k,D0 = + add]; CMPI.W #limit,D0; unsigned: below_pc when D0.W < limit, else above_pc.
bool ob4_range(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t add,std::uint32_t limit,std::uint32_t below_pc,std::uint32_t above_pc) {
    std::uint32_t value=0;if(!ob4_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value+add);
    c.s.pc=ob4_w(c.s.d[0])<limit?below_pc:above_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l (2986 child).
bool ob4_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],0x1e);c.s.a[1]=0x100bf4;return am_call(c,0x2986,return_pc);
}
// MOVEA.L #child,A0; MOVE.W #n,D0; JSR 28ae.l (28ae child).
bool ob4_28ae(AnimationMachineContext& c,std::uint32_t child,std::uint32_t n,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],n);return am_call(c,0x28ae,return_pc);
}
// The sin / cos WORD of a fixed ROM table: (An,D4.W), read through the live bus.
bool ob4_table(AnimationMachineContext& c,std::uint32_t table,std::uint32_t& value) {
    return am_read(c,am_index(table,c.s.d[4]),2,value);
}
// MOVEA.L d(A6),A4; TST.L (A4) / CMPI.L #0,(A4); BEQ.W empty_pc.
bool ob4_list_head(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t empty_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ob4_get(c,c.s.a[6],displacement,4,value))return false;c.s.a[4]=value;
    if(!am_read(c,c.s.a[4],4,value))return false;c.s.pc=value==0U?empty_pc:next_pc;return true;
}
// MOVEA.L (A4)+,A0; MOVE.L A4,d(A6); JSR 4ae4a.l.
bool ob4_list_next(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[4],4,value))return false;c.s.a[0]=value;c.s.a[4]+=4U;
    if(!ob4_put(c,c.s.a[6],displacement,4,c.s.a[4]))return false;return am_call(c,0x4ae4a,return_pc);
}
// 4bb52 grid: ADDI.W #delta,d(A0).
bool ob4_cell(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t delta,std::uint32_t next) {
    if(!ob4_add(c,c.s.a[0],displacement,2,delta))return false;c.s.pc=next;return true;
}
}
// Objects B4 (= B4a, 218 block starts): the 2986 child callbacks of the child tables 227fc / 2280c / 2281c (B3c 1c172: BYTE 9e = 0, 1, 2):
// 22ad4 / 22b04 (22ad4..22c8c, 22c8e..22d64; installs 22b96 22cb0 22d06), 22d94 / 22dbc (22d94..22f7a; installs 22e48), 23058 / 2308e
// (23058..2334c; installs 230fa 231bc 23242 23328 23348) and 235ca (235ca..23774; installs 23664 236d0 23726), with the shared helpers
// 1c9b8 / 1c9ce (1c9b8..1c9ec), 22a10 / 22a4c / 22a62 (22a10..22a8a) and the shared leaf 4bb52 (4bb52..4bc04). Every exit is routed
// (1ab80 287e 28ae 2986 3af8 43e34 443d2 491b6 49214 4970a 49f8c 49fc6 4ae4a 4be06 4be34 8cda 8ebe 8ff4 ea5e0, JMP 2a00). Known C: the
// four ORI.B #1,CCR blocks 2319e 231ec 23292 232cc set C; the 8 consumers 22d2c 23768 (BCC, 49fc6), 23190 231de 23284 232be (BCC, 28ae),
// 23336 (BCC, 287e) and 236be (BCS, 1ab80) read a known C or fail. Data through the live bus (no limit test, as in the original): the bank
// LONGs 20006c 200070 200078 20008c 200094, the sin / cos WORDs 4411e / 4419e + sext(D4.W), the WORD table 22d82 and the LONG lists of
// LONG 8c(A6) / 80(A6). The table bytes and the unreached RTS 22c8c stay unrouted. No X / DIV / TRAP / port / bank write.
bool animation_objects_b4_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    // ---- 1c9b8 / 1c9ce (helpers): LEA 5450(A5),A4; ANDI.W #1,D0; BEQ.W (A4 := 5460(A5) when D0 bit 0 = 1).
    case 0x1c9b8:case 0x1c9ce:
        r.a[4]=am_index(r.a[5],0x5450);am_word(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&1U)==0U?r.pc+0x10U:r.pc+0xcU;return true;
    case 0x1c9c4:case 0x1c9da:r.a[4]=am_index(r.a[5],0x5460);r.pc+=4U;return true;          // LEA 5460(A5),A4.
    case 0x1c9c8:if(!ob4_add(c,r.a[4],1,1,1))return false;return am_return(c);              // ADDQ.B #1,1(A4); RTS.
    case 0x1c9de:if(!ob4_get(c,r.a[4],1,1,value))return false;r.pc=ob4_b(value)==0U?0x1c9ea:0x1c9e6;return true;   // TST.B 1(A4); BEQ.W 1c9ea.
    case 0x1c9e6:if(!ob4_add(c,r.a[4],1,1,0xffU))return false;r.pc=0x1c9ea;return true;     // SUBQ.B #1,1(A4).
    case 0x1c9ea:case 0x22a60:case 0x22c80:case 0x22cae:case 0x22d62:case 0x22f78:case 0x2315c:case 0x23346:case 0x236c2:case 0x23772:
        return am_return(c);                                                                 // RTS.
    // ---- 22a10 (helper): LEA 4411e.l,A0; LEA 4419e.l,A1; MOVE.L D0,D2; MOVE.L D1,D3; ADD.W D4,D4; ASR.L #8,D2; ASR.L #8,D3;
    // MULS.W (A0,D4.W),D2; MULS.W (A1,D4.W),D3; SUB.L D3,D2; ASR.L #8,D2; MOVE.L D2,D3; MULS.W (A0,D4.W),D2; MULS.W (A1,D4.W),D3; NEG.L D3;
    // SUB.L D2,D0; SUB.L D3,D1; NEG.L D0; NEG.L D1; ADD.L D2,D0; ADD.L D3,D1; RTS.
    case 0x22a10:
        r.a[0]=0x4411e;r.a[1]=0x4419e;r.d[2]=r.d[0];r.d[3]=r.d[1];am_word(r.d[4],r.d[4]*2U);
        r.d[2]=ob4_asr_long(r.d[2],8);r.d[3]=ob4_asr_long(r.d[3],8);
        if(!ob4_table(c,r.a[0],value))return false;r.d[2]=ob4_muls(r.d[2],value);
        if(!ob4_table(c,r.a[1],value))return false;r.d[3]=ob4_muls(r.d[3],value);
        r.d[2]-=r.d[3];r.d[2]=ob4_asr_long(r.d[2],8);r.d[3]=r.d[2];
        if(!ob4_table(c,r.a[0],value))return false;r.d[2]=ob4_muls(r.d[2],value);
        if(!ob4_table(c,r.a[1],value))return false;r.d[3]=ob4_muls(r.d[3],value);
        r.d[3]=0U-r.d[3];r.d[0]-=r.d[2];r.d[1]-=r.d[3];r.d[0]=0U-r.d[0];r.d[1]=0U-r.d[1];r.d[0]+=r.d[2];r.d[1]+=r.d[3];return am_return(c);
    // ---- 22a4c (helper): MOVE.W 76(A6),D0; BMI.W 22a60.
    case 0x22a4c:if(!ob4_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.pc=(value&0x8000U)!=0U?0x22a60:0x22a54;return true;
    case 0x22a54:return am_call(c,0x1c9ce,0x22a5a);                                           // JSR 1c9ce.l.
    case 0x22a5a:if(!ob4_get(c,r.a[6],0x76,2,value) || !ob4_put(c,r.a[6],0x76,2,value|0x8000U))return false;r.pc=0x22a60;return true; // ORI.W #8000,76(A6).
    // ---- 22a62 (helper): MOVE.L #fff05398,D0; SUB.L 3a(A6),D0; ASR.L #4,D0; ADD.L D0,3a(A6); MOVEQ #0,D0; SUB.L 36(A6),D0; BMI.W 22a82.
    case 0x22a62:
        if(!ob4_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ob4_asr_long(0xfff05398U-value,4);
        if(!ob4_add(c,r.a[6],0x3a,4,r.d[0]) || !ob4_get(c,r.a[6],0x36,4,value))return false;r.d[0]=0U-value;
        r.pc=(r.d[0]&0x80000000U)!=0U?0x22a82:0x22a7c;return true;
    case 0x22a7c:r.d[0]+=0xfU;r.pc=0x22a82;return true;                                       // ADDI.L #f,D0.
    case 0x22a82:r.d[0]=ob4_asr_long(r.d[0],4);if(!ob4_add(c,r.a[6],0x36,4,r.d[0]))return false;return am_return(c);   // ASR.L #4,D0; ADD.L D0,36(A6); RTS.
    // ---- 22ad4 / 22b04 (2986 children): MOVE.W #92,20(A6); MOVE.L 20006c.l,22(A6); MOVE.W #204 / #27c,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x22ad4:if(!ob4_bank_head(c,0x92,0x20006c))return false;return ob4_8ebe(c,0x204,0,0x22af0);
    case 0x22b04:if(!ob4_bank_head(c,0x92,0x20006c))return false;return ob4_8ebe(c,0x27c,0,0x22b20);
    case 0x22af0:return ob4_anim(c,0x23e02,0x22b00);                                          // MOVEA.L #23e02,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x22b20:return ob4_anim(c,0x23cfa,0x22b30);
    case 0x22b00:r.pc=0x22b30;return true;                                                    // BRA.W 22b30.
    case 0x22b30:case 0x22df2:return ob4_443d2(c,0xbc897,r.pc+0x10U);                       // MOVE.L #bc897,D0; MOVE.B 78(A6),D1; JSR 443d2.l.
    // ADD.L D0,36(A6); MOVE.L D1,3a(A6); MOVE.W #280,D2; BTST.B #0,15(A6); BEQ.W 22b58.
    case 0x22b40:if(!ob4_speed(c))return false;am_word(r.d[2],0x280);return ob4_test(c,0x15,0,0x22b56,0x22b58);
    case 0x22b56:am_word(r.d[2],0U-ob4_w(r.d[2]));r.pc=0x22b58;return true;                  // NEG.W D2.
    // MOVE.W D2,80(A6); MOVE.W #0,7e(A6); MOVE.W #e000,68(A6); MOVE.W #e000,1e(A6); BSET.B #4,15(A6); BCLR.B #0,15(A6); MOVE.W #1,7c(A6);
    // JSR ea5e0.l.
    case 0x22b58:
        if(!ob4_put(c,r.a[6],0x80,2,r.d[2]) || !ob4_put(c,r.a[6],0x7e,2,0) || !ob4_pair68(c,r.a[6],0xe000) || !ob4_bset(c,0x15,4) ||
           !ob4_bclr(c,0x15,0) || !ob4_put(c,r.a[6],0x7c,2,1))return false;return am_call(c,0xea5e0,0x22b86);
    // MOVE.W 76(A6),D0; JSR 1c9b8.l.
    case 0x22b86:case 0x22e28:if(!ob4_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);return am_call(c,0x1c9b8,r.pc+0xaU);
    case 0x22b90:return ob4_install(c,0x22b96);                                               // MOVE.L #22b96,(A6).
    case 0x22b96:r.a[0]=0x229a8;return am_call(c,0x4ae4a,0x22ba0);                            // LEA 229a8(PC),A0; JSR 4ae4a.l (installed value).
    case 0x22ba0:r.pc=ob4_b(r.d[0])!=0U?0x22c8e:0x22ba6;return true;                         // TST.B D0; BNE.W 22c8e.
    // MOVE.L 36(A6),84(A6); MOVE.L 3a(A6),88(A6); JSR 4be34.l.
    case 0x22ba6:if(!ob4_move_long(c,0x36,0x84) || !ob4_move_long(c,0x3a,0x88))return false;return am_call(c,0x4be34,0x22bb8);
    // MOVE.W D4,82(A6); BTST.B #7,15(A6); BEQ.W 22c42.
    case 0x22bb8:if(!ob4_put(c,r.a[6],0x82,2,r.d[4]))return false;return ob4_test(c,0x15,7,0x22bc6,0x22c42);
    case 0x22bc6:case 0x22ee2:return am_call(c,0x4bb52,r.pc+6U);                             // JSR 4bb52.l.
    // MOVEQ #0,D4; MOVE.B 82(A6),D4; MOVE.L 84(A6),D0; MOVE.L 88(A6),D1; BSR.W 22a10.
    case 0x22bcc:
        if(!ob4_get(c,r.a[6],0x82,1,value))return false;r.d[4]=ob4_b(value);
        if(!ob4_get(c,r.a[6],0x84,4,value))return false;r.d[0]=value;
        if(!ob4_get(c,r.a[6],0x88,4,value))return false;r.d[1]=value;return am_call(c,0x22a10,0x22bde);
    // MOVE.L D0,36(A6); MOVE.L D1,3a(A6); LEA 4411e.l,A0; LEA 4419e.l,A1; MOVEQ #0,D4; MOVE.B 82(A6),D4; ADD.W D4,D4; MOVE.L D2,D0; MOVE.L D3,D1;
    // ASR.L #8,D0; ASR.L #8,D1; MULS.W (A0,D4.W),D0; MULS.W (A1,D4.W),D1; SUB.L D1,D0; ASR.L #8,D0; ASR.L #3,D0; MOVE.W 80(A6),D1; SUB.W D1,D0;
    // ASR.W #1,D0; ADD.W D0,80(A6); LSL.W #3,D1; MOVE.W D1,D0; MULS.W (A0,D4.W),D0; MULS.W (A1,D4.W),D1; NEG.L D1; SUB.L D2,D0; SUB.L D3,D1;
    // ASR.L #1,D0; ASR.L #1,D1; ADD.L D0,36(A6); ADD.L D1,3a(A6); SUBQ.W #1,7c(A6); BCS.W 22c94 (borrow: the old WORD was 0).
    case 0x22bde:
        if(!ob4_put(c,r.a[6],0x36,4,r.d[0]) || !ob4_put(c,r.a[6],0x3a,4,r.d[1]))return false;
        r.a[0]=0x4411e;r.a[1]=0x4419e;if(!ob4_get(c,r.a[6],0x82,1,value))return false;r.d[4]=ob4_b(value);am_word(r.d[4],r.d[4]*2U);
        r.d[0]=ob4_asr_long(r.d[2],8);r.d[1]=ob4_asr_long(r.d[3],8);
        if(!ob4_table(c,r.a[0],value))return false;r.d[0]=ob4_muls(r.d[0],value);
        if(!ob4_table(c,r.a[1],value))return false;r.d[1]=ob4_muls(r.d[1],value);
        r.d[0]-=r.d[1];r.d[0]=ob4_asr_long(ob4_asr_long(r.d[0],8),3);
        if(!ob4_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[1],value);am_word(r.d[0],r.d[0]-r.d[1]);ob4_asr_word(r.d[0],1);
        if(!ob4_add(c,r.a[6],0x80,2,r.d[0]))return false;am_word(r.d[1],ob4_w(r.d[1])<<3);am_word(r.d[0],r.d[1]);
        if(!ob4_table(c,r.a[0],value))return false;r.d[0]=ob4_muls(r.d[0],value);
        if(!ob4_table(c,r.a[1],value))return false;r.d[1]=ob4_muls(r.d[1],value);
        r.d[1]=0U-r.d[1];r.d[0]-=r.d[2];r.d[1]-=r.d[3];r.d[0]=ob4_asr_long(r.d[0],1);r.d[1]=ob4_asr_long(r.d[1],1);
        if(!ob4_add(c,r.a[6],0x36,4,r.d[0]) || !ob4_add(c,r.a[6],0x3a,4,r.d[1]) || !ob4_get(c,r.a[6],0x7c,2,value) ||
           !ob4_put(c,r.a[6],0x7c,2,value-1U))return false;r.pc=ob4_w(value)==0U?0x22c94:0x22c42;return true;
    case 0x22c42:case 0x22f52:return am_call(c,0x22a62,r.pc+4U);                             // BSR.W 22a62.
    case 0x2311a:return am_call(c,0x22a62,0x2311e);
    // MOVE.W 80(A6),D0; MOVE.W D0,D1; ASR.W #5,D1; SUB.W D1,80(A6); ADD.W 7e(A6),D0; ANDI.W #1fff,D0; MOVE.W D0,7e(A6); JSR 49fc6.l.
    case 0x22c46:
        if(!ob4_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],value);ob4_asr_word(r.d[1],5);
        if(!ob4_add(c,r.a[6],0x80,2,0U-ob4_w(r.d[1])) || !ob4_get(c,r.a[6],0x7e,2,value))return false;
        am_word(r.d[0],r.d[0]+value);am_word(r.d[0],r.d[0]&0x1fffU);if(!ob4_put(c,r.a[6],0x7e,2,r.d[0]))return false;return am_call(c,0x49fc6,0x22c64);
    // MOVE.W 42(A6),D0; CMPI.W #140,D0; BCC.W 22c82 / MOVE.W 46(A6),D0; SUBI.W #100,D0; CMPI.W #140,D0; BCC.W 22c82 (unsigned).
    case 0x22c64:return ob4_range(c,0x42,0,0x140,0x22c70,0x22c82);
    case 0x22c70:return ob4_range(c,0x46,0xff00,0x140,0x22c80,0x22c82);
    case 0x22f5c:return ob4_range(c,0x42,0,0x140,0x22f68,0x22c82);
    case 0x22f68:return ob4_range(c,0x46,0xff00,0x140,0x22f78,0x22c82);
    case 0x22c82:case 0x22c94:case 0x236c4:return am_call(c,0x22a4c,r.pc+4U);                // BSR.W 22a4c.
    case 0x22ed8:if(!ob4_bset(c,0x61,3))return false;return am_call(c,0x22a4c,0x22ee2);       // BSET.B #3,61(A6); BSR.W 22a4c.
    case 0x22eae:if(!ob4_bset(c,0x61,3))return false;return am_call(c,0x22a4c,0x22eb8);
    case 0x22c86:case 0x22d30:case 0x22d46:case 0x22d5c:case 0x22f4c:case 0x2376c:r.pc=0x2a00;return true;   // JMP 2a00.l (object removal).
    case 0x22c8e:return am_call(c,0x4be06,0x22c94);                                           // JSR 4be06.l.
    case 0x23242:return am_call(c,0x4be06,0x23248);
    // MOVEQ #0,D0; MOVE.L D0,36(A6); MOVE.L D0,3a(A6); MOVE.L #22cb0,(A6); JSR 49fc6.l.
    case 0x22c98:
        r.d[0]=0;if(!ob4_put(c,r.a[6],0x36,4,0) || !ob4_put(c,r.a[6],0x3a,4,0) || !ob4_put(c,r.a[6],0,4,0x22cb0))return false;
        return am_call(c,0x49fc6,0x22cae);
    // MOVE.W #d2,20(A6); MOVE.L 20008c.l,22(A6); MOVE.W #1a26,D0; JSR 3af8.l (installed value).
    case 0x22cb0:if(!ob4_bank_head(c,0xd2,0x20008c))return false;am_word(r.d[0],0x1a26);return am_call(c,0x3af8,0x22cc8);
    case 0x22cc8:return am_call(c,0x8ff4,0x22cce);                                            // JSR 8ff4.l.
    case 0x22cce:return ob4_8ebe(c,0x378,0,0x22cdc);
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); MOVEA.L #23f22,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x22cdc:if(!ob4_pair68(c,r.a[6],0x1001))return false;return ob4_anim(c,0x23f22,0x22cf8);
    case 0x22cf8:if(!ob4_put(c,r.a[6],0x8c,4,0x22a02))return false;return ob4_install(c,0x22d06);   // MOVE.L #22a02,8c(A6); MOVE.L #22d06,(A6).
    case 0x22d06:return ob4_list_head(c,0x8c,0x22d20,0x22d14);                               // MOVEA.L 8c(A6),A4; CMPI.L #0,(A4); BEQ.W 22d20.
    case 0x22d14:return ob4_list_next(c,0x8c,0x22d20);                                       // MOVEA.L (A4)+,A0; MOVE.L A4,8c(A6); JSR 4ae4a.l.
    case 0x22d20:return am_call(c,0x43e34,0x22d26);                                           // JSR 43e34.l.
    case 0x22d26:case 0x22f56:case 0x23762:return am_call(c,0x49fc6,r.pc+6U);               // JSR 49fc6.l.
    case 0x2311e:return am_call(c,0x49fc6,0x23124);
    case 0x22d2c:return ob4_carry(c,0x22d36,0x22d30);                                         // BCC.W 22d36 (C returned by 49fc6).
    case 0x23768:return ob4_carry(c,0x23772,0x2376c);
    case 0x23190:return ob4_carry(c,0x231a2,0x23194);                                         // BCC.W (C returned by 28ae).
    case 0x231de:return ob4_carry(c,0x231f0,0x231e2);
    case 0x23284:return ob4_carry(c,0x23296,0x23288);
    case 0x232be:return ob4_carry(c,0x232d0,0x232c2);
    case 0x23336:return ob4_carry(c,0x23348,0x2333a);                                         // BCC.W 23348 (C returned by 287e).
    case 0x236be:return ob4_carry(c,0x236c2,0x22c82);                                         // BCS.W 22c82 (C returned by 1ab80).
    // MOVE.W 42(A6),D0; ADDI.W #20,D0; CMPI.W #180,D0; BCS.W 22d4c / MOVE.W 46(A6),D0; SUBI.W #100,D0; CMPI.W #140,D0; BCS.W 22d62.
    case 0x22d36:return ob4_range(c,0x42,0x20,0x180,0x22d4c,0x22d46);
    case 0x22d4c:return ob4_range(c,0x46,0xff00,0x140,0x22d62,0x22d5c);
    // ---- 22d94 / 22dbc (2986 children): MOVE.W #e2,20(A6); MOVE.L 200094.l,22(A6); MOVE.B #ff / #0,8a(A6); MOVEA.L #240ca / #23ffa,A1;
    // MOVE.W #100,D0; JSR 49f8c.l.
    case 0x22d94:if(!ob4_bank_head(c,0xe2,0x200094) || !ob4_put(c,r.a[6],0x8a,1,0xff))return false;return ob4_anim(c,0x240ca,0x22db8);
    case 0x22dbc:if(!ob4_bank_head(c,0xe2,0x200094) || !ob4_put(c,r.a[6],0x8a,1,0))return false;return ob4_anim(c,0x23ffa,0x22de0);
    case 0x22db8:case 0x22de0:r.pc=0x22de4;return true;                                      // BRA.W 22de4.
    case 0x22de4:return ob4_8ebe(c,0x20a,0,0x22df2);
    // ADD.L D0,36(A6); MOVE.L D1,3a(A6); MOVE.W #e000,68(A6); MOVE.W #e000,1e(A6); BCLR.B #0,15(A6); MOVE.W #3,7c(A6); JSR ea5e0.l.
    case 0x22e02:
        if(!ob4_speed(c) || !ob4_pair68(c,r.a[6],0xe000) || !ob4_bclr(c,0x15,0) || !ob4_put(c,r.a[6],0x7c,2,3))return false;
        return am_call(c,0xea5e0,0x22e28);
    // BSET.B #4,15(A6); CLR.B 8b(A6); MOVE.W #1e,80(A6); MOVE.L #22e48,(A6).
    case 0x22e32:if(!ob4_bset(c,0x15,4) || !ob4_put(c,r.a[6],0x8b,1,0) || !ob4_put(c,r.a[6],0x80,2,0x1e))return false;return ob4_install(c,0x22e48);
    case 0x22e48:return ob4_test(c,0x61,3,0x22eb8,0x22e52);                                  // BTST.B #3,61(A6); BNE.W 22eb8 (installed value).
    case 0x22e52:r.a[0]=0x22d64;return am_call(c,0x4ae4a,0x22e5c);                            // LEA 22d64(PC),A0; JSR 4ae4a.l.
    case 0x22e5c:r.pc=ob4_b(r.d[0])==0U?0x22eb8:0x22e62;return true;                         // TST.B D0; BEQ.W 22eb8.
    // LEA 22d82(PC),A0; ANDI.W #ff,D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; JSR 3af8.l.
    case 0x22e62:
        r.a[0]=0x22d82;am_word(r.d[0],r.d[0]&0xffU);am_word(r.d[0],r.d[0]*2U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);return am_call(c,0x3af8,0x22e76);
    // NEG.L 36(A6); MOVE.L 3a(A6),D0; BPL.W 22e88.
    case 0x22e76:
        if(!ob4_get(c,r.a[6],0x36,4,value) || !ob4_put(c,r.a[6],0x36,4,0U-value) || !ob4_get(c,r.a[6],0x3a,4,value))return false;
        r.d[0]=value;r.pc=(value&0x80000000U)!=0U?0x22e82:0x22e88;return true;
    case 0x22e82:r.d[0]=0U-r.d[0];if(!ob4_put(c,r.a[6],0x3a,4,r.d[0]))return false;r.pc=0x22e88;return true;   // NEG.L D0; MOVE.L D0,3a(A6).
    case 0x22e88:return ob4_child(c,0x22f7a,0x22e9e);                                         // MOVEA.L #22f7a,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l.
    case 0x22f0c:return ob4_child(c,0x22f7a,0x22f22);
    case 0x235ee:return ob4_child(c,0x23774,0x23604);
    // MOVE.B 8a(A6),8a(A0); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.l.
    case 0x22e9e:case 0x22f22:if(!ob4_copy(c,0x8a,1))return false;r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,r.pc==0x22e9eU?0x22eae:0x22f32);
    // MOVE.L 36(A6),82(A6); MOVE.L 3a(A6),86(A6); JSR 4be34.l.
    case 0x22eb8:if(!ob4_move_long(c,0x36,0x82) || !ob4_move_long(c,0x3a,0x86))return false;return am_call(c,0x4be34,0x22eca);
    // MOVE.W D4,7e(A6); BTST.B #7,15(A6); BEQ.W 22f3a.
    case 0x22eca:if(!ob4_put(c,r.a[6],0x7e,2,r.d[4]))return false;return ob4_test(c,0x15,7,0x22ed8,0x22f3a);
    // MOVE.L 82(A6),D0; MOVE.L 86(A6),D1; MOVEQ #0,D4; MOVE.B 7e(A6),D4; JSR 22a10(PC).
    case 0x22ee8:
        if(!ob4_get(c,r.a[6],0x82,4,value))return false;r.d[0]=value;
        if(!ob4_get(c,r.a[6],0x86,4,value))return false;r.d[1]=value;
        if(!ob4_get(c,r.a[6],0x7e,1,value))return false;r.d[4]=ob4_b(value);return am_call(c,0x22a10,0x22efa);
    // MOVE.L D0,36(A6); MOVE.L D1,3a(A6); CMPI.W #2,3a(A6); BLE.W 22f32 (signed).
    case 0x22efa:
        if(!ob4_put(c,r.a[6],0x36,4,r.d[0]) || !ob4_put(c,r.a[6],0x3a,4,r.d[1]) || !ob4_get(c,r.a[6],0x3a,2,value))return false;
        r.pc=ob4_signed_word(value)<=2?0x22f32:0x22f0c;return true;
    case 0x22f32:if(!ob4_add(c,r.a[6],0x7c,2,0xffffU))return false;r.pc=0x22f3a;return true; // SUBQ.W #1,7c(A6); BNE.W 22f3a (both sides 22f3a).
    case 0x22f3a:return ob4_test(c,0x61,3,0x22f44,0x22f52);                                  // BTST.B #3,61(A6); BEQ.W 22f52.
    // SUBQ.W #1,80(A6); BCC.W 22f52 (no borrow: the old WORD was not 0).
    case 0x22f44:
        if(!ob4_get(c,r.a[6],0x80,2,value) || !ob4_put(c,r.a[6],0x80,2,value-1U))return false;r.pc=ob4_w(value)!=0U?0x22f52:0x22f4c;return true;
    // ---- 23058 / 2308e (2986 children): MOVE.W #9a,20(A6); MOVE.L 200070.l,22(A6); MOVE.W #203 / #872,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x23058:if(!ob4_bank_head(c,0x9a,0x200070))return false;return ob4_8ebe(c,0x203,0,0x23074);
    case 0x2308e:if(!ob4_bank_head(c,0x9a,0x200070))return false;return ob4_8ebe(c,0x872,0,0x230aa);
    case 0x23074:return ob4_anim(c,0x2419a,0x23084);
    case 0x230aa:return ob4_anim(c,0x24240,0x230ba);
    case 0x23084:if(!ob4_put(c,r.a[6],0x84,1,0))return false;r.pc=0x230c0;return true;      // MOVE.B #0,84(A6); BRA.W 230c0.
    case 0x230ba:if(!ob4_put(c,r.a[6],0x84,1,1))return false;r.pc=0x230c0;return true;      // MOVE.B #1,84(A6).
    case 0x230c0:return ob4_443d2(c,0xa4f84,0x230d0);                                         // MOVE.L #a4f84,D0; MOVE.B 78(A6),D1; JSR 443d2.l.
    // ADD.L D0,36(A6); MOVE.L D1,3a(A6); BSET.B #4,15(A6); MOVE.W 76(A6),D0; JSR 1c9b8.l.
    case 0x230d0:
        if(!ob4_speed(c) || !ob4_bset(c,0x15,4) || !ob4_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);return am_call(c,0x1c9b8,0x230e8);
    case 0x230e8:if(!ob4_pair68(c,r.a[6],0xe000))return false;return ob4_install(c,0x230fa);  // MOVE.W #e000,68(A6) / 1e(A6); MOVE.L #230fa,(A6).
    case 0x230fa:r.a[0]=0x22fe0;return am_call(c,0x4ae4a,0x23104);                            // LEA 22fe0(PC),A0; JSR 4ae4a.l (installed value).
    case 0x23104:r.pc=ob4_b(r.d[0])==2U?0x2315e:0x2310c;return true;                         // CMPI.B #2,D0; BEQ.W 2315e.
    case 0x2310c:r.pc=ob4_b(r.d[0])==1U?0x2315e:0x23114;return true;                         // CMPI.B #1,D0; BEQ.W 2315e.
    case 0x23114:return am_call(c,0x4be34,0x2311a);                                           // JSR 4be34.l.
    case 0x23674:return am_call(c,0x4be34,0x2367a);
    case 0x2375c:return am_call(c,0x4be34,0x23762);
    case 0x23124:return ob4_test(c,0x15,7,0x2312e,0x23134);                                  // BTST.B #7,15(A6); BEQ.W 23134.
    case 0x2312e:return ob4_callback(c,0x231bc,0x23134);                                     // MOVE.L #231bc,(A6).
    case 0x23140:return ob4_callback(c,0x23348,0x23146);                                     // MOVE.L #23348,(A6).
    case 0x23156:return ob4_callback(c,0x23348,0x2315c);
    case 0x232f6:return ob4_callback(c,0x23328,0x232fc);                                     // MOVE.L #23328,(A6).
    case 0x23308:return ob4_callback(c,0x23328,0x2330e);
    case 0x2331e:return ob4_callback(c,0x23328,0x23324);
    case 0x23134:return ob4_range(c,0x42,0,0x140,0x23146,0x23140);                           // MOVE.W 42(A6),D0; CMPI.W #140,D0; BCS.W 23146.
    case 0x23146:return ob4_range(c,0x46,0xff00,0x140,0x2315c,0x23156);
    case 0x232fc:return ob4_range(c,0x42,0,0x140,0x2330e,0x23308);
    case 0x2330e:return ob4_range(c,0x46,0xff00,0x140,0x23324,0x2331e);
    // CMPI.B #1,84(A6); BEQ.W 23176.
    case 0x2315e:if(!ob4_get(c,r.a[6],0x84,1,value))return false;r.pc=ob4_b(value)==1U?0x23176:0x23168;return true;
    case 0x23168:am_word(r.d[0],0x1a26);return am_call(c,0x3af8,0x23172);                    // MOVE.W #1a26,D0; JSR 3af8.l.
    case 0x23176:am_word(r.d[0],0x1a24);return am_call(c,0x3af8,0x23180);                    // MOVE.W #1a24,D0; JSR 3af8.l.
    case 0x236d0:am_word(r.d[0],0x1a24);return am_call(c,0x3af8,0x236da);
    case 0x23172:r.pc=0x23180;return true;                                                    // BRA.W 23180.
    case 0x23180:return ob4_28ae(c,0xd206a,0x14,0x23190);                                     // MOVEA.L #d206a,A0; MOVE.W #14,D0; JSR 28ae.l.
    // CLR.W D0; CLR.W D1; JSR 4970a.l.
    case 0x23194:case 0x231e2:case 0x23288:case 0x232c2:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,r.pc+0xaU);
    // ORI.B #1,CCR: C Set (the next block's first MOVE clears it; no block reads it).
    case 0x2319e:case 0x231ec:case 0x23292:case 0x232cc:r.carry=AnimationCarrySet;r.pc+=4U;return true;
    // MOVE.W #1001,68(A0); MOVE.W #1001,1e(A0); LEA 22ffe(PC),A0; JSR 4ae4a.l.
    case 0x231a2:if(!ob4_pair68(c,r.a[0],0x1001))return false;r.a[0]=0x22ffe;return am_call(c,0x4ae4a,0x231b8);
    case 0x231b8:r.pc=0x23348;return true;                                                    // BRA.W 23348.
    // CLR.B 82(A6); CLR.L 64(A6); ADDQ.W #4,32(A6); JSR 43e34.l (installed value).
    case 0x231bc:
        if(!ob4_put(c,r.a[6],0x82,1,0) || !ob4_put(c,r.a[6],0x64,4,0) || !ob4_add(c,r.a[6],0x32,2,4))return false;return am_call(c,0x43e34,0x231ce);
    case 0x235e2:if(!ob4_bset(c,0x15,4))return false;return am_call(c,0x43e34,0x235ee);       // BSET.B #4,15(A6); JSR 43e34.l.
    case 0x231ce:return ob4_28ae(c,0x2334c,0xa,0x231de);                                      // MOVEA.L #2334c,A0; MOVE.W #a,D0; JSR 28ae.l.
    // MOVE.B 60(A6),60(A0); MOVE.B 84(A6),84(A0); MOVE.L #100000,64(A6); CMPI.B #1,84(A6); BNE.W 23228.
    case 0x231f0:
        if(!ob4_copy(c,0x60,1) || !ob4_copy(c,0x84,1) || !ob4_put(c,r.a[6],0x64,4,0x100000) || !ob4_get(c,r.a[6],0x84,1,value))return false;
        r.pc=ob4_b(value)!=1U?0x23228:0x2320e;return true;
    // MOVE.W #4,80(A6); MOVE.B #18,83(A6); MOVE.W #1a99,D0; JSR 3af8.l / CLR.W 80(A6); MOVE.B #0,83(A6); MOVE.W #1a64,D0; JSR 3af8.l.
    case 0x2320e:if(!ob4_put(c,r.a[6],0x80,2,4) || !ob4_put(c,r.a[6],0x83,1,0x18))return false;am_word(r.d[0],0x1a99);return am_call(c,0x3af8,0x23224);
    case 0x23228:if(!ob4_put(c,r.a[6],0x80,2,0) || !ob4_put(c,r.a[6],0x83,1,0))return false;am_word(r.d[0],0x1a64);return am_call(c,0x3af8,0x2323c);
    case 0x23224:r.pc=0x2323c;return true;                                                    // BRA.W 2323c.
    case 0x2323c:return ob4_install(c,0x23242);                                               // MOVE.L #23242,(A6).
    // SUBQ.W #1,80(A6); CMPI.W #0,80(A6); BGT.W 232fc (signed).
    case 0x23248:
        if(!ob4_add(c,r.a[6],0x80,2,0xffffU) || !ob4_get(c,r.a[6],0x80,2,value))return false;r.pc=ob4_signed_word(value)>0?0x232fc:0x23256;return true;
    case 0x23256:if(!ob4_get(c,r.a[6],0x84,1,value))return false;r.pc=ob4_b(value)==1U?0x2326a:0x23260;return true;   // CMPI.B #1,84(A6); BEQ.W 2326a.
    case 0x23260:case 0x2326a:if(!ob4_put(c,r.a[6],0x80,2,r.pc==0x23260U?2U:3U))return false;r.pc=0x23270;return true; // MOVE.W #2 / #3,80(A6).
    // ADDQ.B #1,82(A6); MOVEA.L #2334c,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0x23270:if(!ob4_add(c,r.a[6],0x82,1,1))return false;return ob4_28ae(c,0x2334c,0x14,0x23284);
    // MOVE.B 60(A6),60(A0); MOVE.L 64(A6),64(A0); MOVE.B 82(A6),82(A0); MOVE.B 84(A6),84(A0); MOVEA.L #2334c,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0x23296:
        if(!ob4_copy(c,0x60,1) || !ob4_copy(c,0x64,4) || !ob4_copy(c,0x82,1) || !ob4_copy(c,0x84,1))return false;return ob4_28ae(c,0x2334c,0x14,0x232be);
    // MOVE.B 60(A6),60(A0); MOVE.L 64(A6),D0; NEG.L D0; MOVE.L D0,64(A0); MOVE.B 82(A6),82(A0); MOVE.B 84(A6),84(A0); CMPI.B #4,82(A6);
    // BLT.W 232fc (signed).
    case 0x232d0:
        if(!ob4_copy(c,0x60,1) || !ob4_get(c,r.a[6],0x64,4,value))return false;r.d[0]=0U-value;
        if(!ob4_put(c,r.a[0],0x64,4,r.d[0]) || !ob4_copy(c,0x82,1) || !ob4_copy(c,0x84,1) || !ob4_get(c,r.a[6],0x82,1,value))return false;
        r.pc=ob4_signed_byte(value)<4?0x232fc:0x232f6;return true;
    case 0x23324:r.pc=0x2333a;return true;                                                    // BRA.W 2333a.
    // TST.B 83(A6); BLE.W 23348 / 23346 (signed).
    case 0x23328:if(!ob4_get(c,r.a[6],0x83,1,value))return false;r.pc=ob4_signed_byte(value)<=0?0x23348:0x23330;return true;
    case 0x2333a:if(!ob4_get(c,r.a[6],0x83,1,value))return false;r.pc=ob4_signed_byte(value)<=0?0x23346:0x23342;return true;
    case 0x23330:return am_call(c,0x287e,0x23336);                                            // JSR 287e.l.
    case 0x23342:if(!ob4_add(c,r.a[6],0x83,1,0xffU))return false;r.pc=0x23346;return true;   // SUBQ.B #1,83(A6).
    case 0x23348:r.pc=0x22c82;return true;                                                    // BRA.W 22c82 (installed value too).
    // ---- 235ca (2986 child): MOVE.W #aa,20(A6); MOVE.L 200078.l,22(A6); MOVE.W 76(A6),D0; JSR 1c9b8.l.
    case 0x235ca:
        if(!ob4_bank_head(c,0xaa,0x200078) || !ob4_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);return am_call(c,0x1c9b8,0x235e2);
    case 0x23604:return am_call(c,0x491b6,0x2360a);                                           // JSR 491b6.l.
    // MOVEM.L 2e(A6),D0-D3/A1; MOVEM.L D0-D3/A1,2e(A0); MOVE.W #e000,68(A6); MOVE.W #e000,1e(A6); MOVE.W #8ba,D0; MOVE.B #1,D1; JSR 8ebe.l.
    case 0x2360a: {
        std::uint32_t moved[5]={0,0,0,0,0};
        for(unsigned int i=0;i<5;++i)if(!ob4_get(c,r.a[6],0x2eU+4U*i,4,moved[i]))return false;
        r.d[0]=moved[0];r.d[1]=moved[1];r.d[2]=moved[2];r.d[3]=moved[3];r.a[1]=moved[4];
        for(unsigned int i=0;i<5;++i)if(!ob4_put(c,r.a[0],0x2eU+4U*i,4,moved[i]))return false;
        if(!ob4_pair68(c,r.a[6],0xe000))return false;return ob4_8ebe(c,0x8ba,1,0x23630);}
    case 0x23630:return ob4_anim(c,0x2457c,0x23640);
    case 0x23640:return ob4_443d2(c,0x180000,0x23650);
    // ADD.L D0,36(A6); MOVE.L D1,3a(A6); MOVE.W #19,7e(A6); MOVE.L #23664,(A6).
    case 0x23650:if(!ob4_speed(c) || !ob4_put(c,r.a[6],0x7e,2,0x19))return false;return ob4_install(c,0x23664);
    case 0x23664:r.a[0]=0x2355c;return am_call(c,0x4ae4a,0x2366e);                            // LEA 2355c(PC),A0; JSR 4ae4a.l (installed value).
    case 0x2366e:r.pc=ob4_b(r.d[0])!=0U?0x236c4:0x23674;return true;                         // TST.B D0; BNE.W 236c4.
    case 0x2367a:return ob4_test(c,0x15,7,0x236c4,0x23684);                                  // BTST.B #7,15(A6); BNE.W 236c4.
    // SUBQ.W #1,7e(A6); BCS.W 236c4 (borrow: the old WORD was 0).
    case 0x23684:
        if(!ob4_get(c,r.a[6],0x7e,2,value) || !ob4_put(c,r.a[6],0x7e,2,value-1U))return false;r.pc=ob4_w(value)==0U?0x236c4:0x2368c;return true;
    // MOVE.L #fff00000,D0; SUB.L 3a(A6),D0; ASR.L #3,D0; ADD.L D0,3a(A6); MOVEQ #0,D0; SUB.L 36(A6),D0; BMI.W 236a8.
    case 0x2368c:
        if(!ob4_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ob4_asr_long(0xfff00000U-value,3);
        if(!ob4_add(c,r.a[6],0x3a,4,r.d[0]) || !ob4_get(c,r.a[6],0x36,4,value))return false;r.d[0]=0U-value;
        r.pc=(r.d[0]&0x80000000U)!=0U?0x236a8:0x236a6;return true;
    case 0x236a6:r.d[0]+=7U;r.pc=0x236a8;return true;                                         // ADDQ.L #7,D0.
    // ASR.L #3,D0; ADD.L D0,36(A6); JSR 49fc6.l.
    case 0x236a8:r.d[0]=ob4_asr_long(r.d[0],3);if(!ob4_add(c,r.a[6],0x36,4,r.d[0]))return false;return am_call(c,0x49fc6,0x236b4);
    case 0x236b4:r.a[0]=0x235c2;return am_call(c,0x1ab80,0x236be);                            // LEA 235c2(PC),A0; JSR 1ab80.l.
    case 0x236c8:if(!ob4_put(c,r.a[6],0,4,0x236d0))return false;return am_return(c);         // MOVE.L #236d0,(A6); RTS.
    // MOVE.W #1001,68(A6); MOVE.W #1001,1e(A6); JSR 8ff4.l.
    case 0x236da:if(!ob4_pair68(c,r.a[6],0x1001))return false;return am_call(c,0x8ff4,0x236ec);
    case 0x236ec:return ob4_8ebe(c,0x80c,1,0x236fa);
    // MOVE.B #20,7c(A6); MOVEA.L #6f536,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x236fa:if(!ob4_put(c,r.a[6],0x7c,1,0x20))return false;return ob4_anim(c,0x6f536,0x23710);
    // MOVE.L #235b6,80(A6); CLR.L 36(A6); CLR.L 3a(A6); MOVE.L #23726,(A6).
    case 0x23710:
        if(!ob4_put(c,r.a[6],0x80,4,0x235b6) || !ob4_put(c,r.a[6],0x36,4,0) || !ob4_put(c,r.a[6],0x3a,4,0))return false;return ob4_install(c,0x23726);
    case 0x23726:return ob4_list_head(c,0x80,0x2373c,0x23730);                               // MOVEA.L 80(A6),A4; TST.L (A4); BEQ.W 2373c.
    case 0x23730:return ob4_list_next(c,0x80,0x2373c);                                       // MOVEA.L (A4)+,A0; MOVE.L A4,80(A6); JSR 4ae4a.l.
    // MOVE.B 14(A6),D0; MOVE.W #80b,D1; MOVE.B 7c(A6),D2; JSR 8cda.l.
    case 0x2373c:
        if(!ob4_get(c,r.a[6],0x14,1,value) || !ob4_get(c,r.a[6],0x7c,1,other))return false;am_byte(r.d[0],value);am_word(r.d[1],0x80b);am_byte(r.d[2],other);
        return am_call(c,0x8cda,0x2374e);
    // SUBI.W #140,7c(A6); BCC.W 2375c (no borrow: the old WORD was >= 140, unsigned).
    case 0x2374e:
        if(!ob4_get(c,r.a[6],0x7c,2,value) || !ob4_put(c,r.a[6],0x7c,2,value-0x140U))return false;r.pc=ob4_w(value)>=0x140U?0x2375c:0x23758;return true;
    case 0x23758:if(!ob4_put(c,r.a[6],0x7c,2,0))return false;r.pc=0x2375c;return true;      // CLR.W 7c(A6).
    // ---- 4bb52 (shared leaf): MOVEM.L D0-D1/A0,-(A7) (A0, D1, D0 pushed: D0 at the lowest address); MOVE.W 46(A6),D0; SUBI.W #100,D0;
    // CMPI.W #100,D0; BCC.W 4bbfe.
    case 0x4bb52:
        if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]) || !ob4_get(c,r.a[6],0x46,2,value))return false;
        am_word(r.d[0],value-0x100U);r.pc=ob4_w(r.d[0])>=0x100U?0x4bbfe:0x4bb66;return true;
    // LSR.W #4,D0; ANDI.W #e,D0; MOVE.W 42(A6),D1; SUBI.W #20,D1; CMPI.W #200,D1; BCC.W 4bbfe.
    case 0x4bb66:
        am_word(r.d[0],(ob4_w(r.d[0])>>4)&0xeU);if(!ob4_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[1],value-0x20U);
        r.pc=ob4_w(r.d[1])>=0x200U?0x4bbfe:0x4bb7c;return true;
    // LSR.W #1,D1; ANDI.W #f0,D1; LEA 5b88(A5),A0; ADDA.W D0,A0; ADDA.W D1,A0; ADDI.W #100,(A0); CMPI.W #2,D0; BCS.W 4bbb8.
    case 0x4bb7c:
        am_word(r.d[1],(ob4_w(r.d[1])>>1)&0xf0U);r.a[0]=am_index(am_index(am_index(r.a[5],0x5b88),r.d[0]),r.d[1]);
        if(!ob4_add(c,r.a[0],0,2,0x100))return false;r.pc=ob4_w(r.d[0])<2U?0x4bbb8:0x4bb96;return true;
    // ADDI.W #c0,-2(A0); CMPI.W #10,D1; BCS.W 4bbaa.
    case 0x4bb96:if(!ob4_add(c,r.a[0],0xfffe,2,0xc0))return false;r.pc=ob4_w(r.d[1])<0x10U?0x4bbaa:0x4bba4;return true;
    case 0x4bba4:return ob4_cell(c,0xffee,0x80,0x4bbaa);                                      // ADDI.W #80,-12(A0).
    case 0x4bbaa:r.pc=ob4_w(r.d[1])>=0xf0U?0x4bbb8:0x4bbb2;return true;                      // CMPI.W #f0,D1; BCC.W 4bbb8.
    case 0x4bbb2:return ob4_cell(c,0xe,0x80,0x4bbb8);                                         // ADDI.W #80,e(A0).
    case 0x4bbb8:r.pc=ob4_w(r.d[1])<0x10U?0x4bbc6:0x4bbc0;return true;                       // CMPI.W #10,D1; BCS.W 4bbc6.
    case 0x4bbc0:return ob4_cell(c,0xfff0,0xc0,0x4bbc6);                                      // ADDI.W #c0,-10(A0).
    case 0x4bbc6:r.pc=ob4_w(r.d[1])>=0xf0U?0x4bbd4:0x4bbce;return true;                      // CMPI.W #f0,D1; BCC.W 4bbd4.
    case 0x4bbce:return ob4_cell(c,0x10,0xc0,0x4bbd4);                                        // ADDI.W #c0,10(A0).
    case 0x4bbd4:r.pc=ob4_w(r.d[0])>=0xeU?0x4bbfe:0x4bbdc;return true;                       // CMPI.W #e,D0; BCC.W 4bbfe.
    // ADDI.W #c0,2(A0); CMPI.W #10,D1; BCS.W 4bbf0.
    case 0x4bbdc:if(!ob4_add(c,r.a[0],2,2,0xc0))return false;r.pc=ob4_w(r.d[1])<0x10U?0x4bbf0:0x4bbea;return true;
    case 0x4bbea:return ob4_cell(c,0xfff2,0x80,0x4bbf0);                                      // ADDI.W #80,-e(A0).
    case 0x4bbf0:r.pc=ob4_w(r.d[1])>=0xf0U?0x4bbfe:0x4bbf8;return true;                      // CMPI.W #f0,D1; BCC.W 4bbfe.
    case 0x4bbf8:return ob4_cell(c,0x12,0x80,0x4bbfe);                                        // ADDI.W #80,12(A0).
    // MOVEM.L (A7)+,D0-D1/A0 (D0, D1, A0 popped); RTS.
    case 0x4bbfe:
        if(!am_pop(c,4,value))return false;r.d[0]=value;if(!am_pop(c,4,value))return false;r.d[1]=value;
        if(!am_pop(c,4,value))return false;r.a[0]=value;return am_return(c);
    default:return am_error(c,"unsupported animation objects b4 PC");
    }
}
}
