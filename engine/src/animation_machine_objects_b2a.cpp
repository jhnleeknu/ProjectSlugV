#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONGs (live bus, current PVC bank): the animation record bases 18b (200194) and da (200090) stored in LONG 22(A6).
const std::uint32_t OB2A_BANK_18B=0x200194;
const std::uint32_t OB2A_BANK_DA=0x200090;
// LEA d(PC),A0 operands (fixed ROM hit boxes in the N25 gap, passed to 4ae4a / 1ab02 as data) and the 490ba table.
const std::uint32_t OB2A_HIT_A=0x5eeac;
const std::uint32_t OB2A_HIT_B=0x5eeca;
const std::uint32_t OB2A_TABLE_60C54=0x60c54;
// 2986 parent node and child value (data, B1 decision 5; not an execution PC of this unit).
const std::uint32_t OB2A_PARENT=0x100bf4;
const std::uint32_t OB2A_CHILD_2986=0xb3dbc;
std::uint32_t ob2a_b(std::uint32_t value) {return value&255U;}
std::uint32_t ob2a_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ob2a_mask(unsigned int size) {return size==1?0xffU:(size==2?0xffffU:0xffffffffU);}
std::uint32_t ob2a_sign(unsigned int size) {return size==1?0x80U:(size==2?0x8000U:0x80000000U);}
// N Z V C of the 68000 two's complement operation (SUB / SUBQ / SUBI / CMP / CMPI: dst - src; ADD / ADDQ: dst + src).
struct Ob2aFlags {bool n;bool z;bool v;bool c;};
Ob2aFlags ob2a_sub(unsigned int size,std::uint32_t dst,std::uint32_t src,std::uint32_t& result) {
    const std::uint32_t m=ob2a_mask(size);const std::uint32_t s=ob2a_sign(size);
    const std::uint32_t d=dst&m;const std::uint32_t u=src&m;const std::uint32_t res=(d-u)&m;
    Ob2aFlags f;f.n=(res&s)!=0U;f.z=res==0U;f.v=(((d^u)&(d^res))&s)!=0U;f.c=u>d;result=res;return f;
}
Ob2aFlags ob2a_add(unsigned int size,std::uint32_t dst,std::uint32_t src,std::uint32_t& result) {
    const std::uint32_t m=ob2a_mask(size);const std::uint32_t s=ob2a_sign(size);
    const std::uint32_t d=dst&m;const std::uint32_t u=src&m;const std::uint32_t res=(d+u)&m;
    Ob2aFlags f;f.n=(res&s)!=0U;f.z=res==0U;f.v=((~(d^u)&(d^res))&s)!=0U;f.c=res<d;result=res;return f;
}
// Signed conditions: BLT (N != V), BGE (N == V), BGT (!Z and N == V), BLE (Z or N != V).
bool ob2a_lt(const Ob2aFlags& f) {return f.n!=f.v;}
bool ob2a_ge(const Ob2aFlags& f) {return f.n==f.v;}
bool ob2a_gt(const Ob2aFlags& f) {return !f.z && f.n==f.v;}
bool ob2a_le(const Ob2aFlags& f) {return f.z || f.n!=f.v;}
// ASR.L #n (1 <= n <= 8): the sign refills the upper bits.
std::uint32_t ob2a_asr(std::uint32_t value,unsigned int count) {
    const std::uint32_t fill=(value&0x80000000U)!=0U?(0xffffffffU<<(32U-count)):0U;return (value>>count)|fill;
}
// The exact C after a flag-writing instruction (a Bcc of the same block or a later consumer reads it).
void ob2a_set_c(AnimationMachineState& r,bool carry) {r.carry=carry?AnimationCarrySet:AnimationCarryClear;}
void ob2a_clear(AnimationMachineState& r) {r.carry=AnimationCarryClear;}
bool ob2a_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool ob2a_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value&ob2a_mask(size));
}
// SUBQ / SUBI / ADDQ / ADD d(A6) (read, then write) and CMPI / CMP d(A6) (read only); the flags go out through f.
bool ob2a_sub_mem(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t src,Ob2aFlags& f) {
    std::uint32_t value=0;std::uint32_t result=0;if(!ob2a_get(c,displacement,size,value))return false;
    f=ob2a_sub(size,value,src,result);return ob2a_put(c,displacement,size,result);
}
bool ob2a_add_mem(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t src,Ob2aFlags& f) {
    std::uint32_t value=0;std::uint32_t result=0;if(!ob2a_get(c,displacement,size,value))return false;
    f=ob2a_add(size,value,src,result);return ob2a_put(c,displacement,size,result);
}
bool ob2a_cmp_mem(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t src,Ob2aFlags& f) {
    std::uint32_t value=0;std::uint32_t result=0;if(!ob2a_get(c,displacement,size,value))return false;
    f=ob2a_sub(size,value,src,result);return true;
}
// BTST.B #bit,d(A6): set receives the bit (Z = !set); BSET / BCLR read, then write (C is not touched by any of them).
bool ob2a_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob2a_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
bool ob2a_bit_set(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;return ob2a_get(c,displacement,1,value) && ob2a_put(c,displacement,1,value|(1U<<bit));
}
bool ob2a_bit_clear(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;return ob2a_get(c,displacement,1,value) && ob2a_put(c,displacement,1,value&~(1U<<bit));
}
// MOVE.L #pc,(A6) (installed callback LONG; MOVE: C = 0).
bool ob2a_install(AnimationMachineContext& c,std::uint32_t pc) {
    if(!am_write(c,c.s.a[6],4,pc))return false;ob2a_clear(c.s);return true;
}
// Bcc on a C returned by a callee (JSR 4b6f4 / 49fc6 / 1ab02 / 4b54e / 28ae / 2986): clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob2a_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b2a caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W #id,D0; MOVE.B #0,D1; JSR 8ebe.l (MOVE: C = 0).
bool ob2a_8ebe(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);am_byte(c.s.d[1],0);ob2a_clear(c.s);return am_call(c,0x8ebe,return_pc);
}
// LEA 26(A6),A0; MOVE.W #id,20(A6); MOVE.L bank.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l.
bool ob2a_bank_anim(AnimationMachineContext& c,std::uint32_t bank,std::uint32_t id,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[6],0x26);
    if(!ob2a_put(c,0x20,2,id) || !am_read(c,bank,4,value) || !ob2a_put(c,0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!ob2a_get(c,0x22,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],displacement),4,value))return false;r.a[1]=value;
    ob2a_clear(r);return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L #child,A0; MOVE.W #a,D0; JSR 28ae.l (the child value is data; MOVE: C = 0).
bool ob2a_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],0xa);ob2a_clear(c.s);return am_call(c,0x28ae,return_pc);
}
// MOVE.W #0,D0; MOVE.W #0,D1; JSR 4970a.l.
bool ob2a_4970a(AnimationMachineContext& c,std::uint32_t return_pc) {
    am_word(c.s.d[0],0);am_word(c.s.d[1],0);ob2a_clear(c.s);return am_call(c,0x4970a,return_pc);
}
// Seven MOVE.W #n,-(A7) (3 0 0 0 1 0 0); MOVEA.L #b3dbc,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.l (MOVE: C = 0).
bool ob2a_2986(AnimationMachineContext& c,std::uint32_t return_pc) {
    static const std::uint32_t pushed[7]={3,0,0,0,1,0,0};
    for(unsigned int i=0;i<7;++i) {if(!am_push(c,2,pushed[i]))return false;}
    c.s.a[0]=OB2A_CHILD_2986;am_word(c.s.d[0],0x14);c.s.a[1]=OB2A_PARENT;ob2a_clear(c.s);return am_call(c,0x2986,return_pc);
}
// MOVEM.W (A7)+,D0-D6 (each WORD sign-extended to the whole register, no flag change); BCC.W target (C returned by 2986).
bool ob2a_movem_pop(AnimationMachineContext& c) {
    std::uint32_t value=0;
    for(unsigned int i=0;i<7;++i) {if(!am_pop(c,2,value))return false;c.s.d[i]=am_extend_word(value);}
    return true;
}
// MOVE.W d2..d6,76 78 7a 7c 7e(A0); JSR 49214.l.
bool ob2a_fill_child(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;
    if(!am_write(c,am_index(r.a[0],0x76),2,ob2a_w(r.d[2])) || !am_write(c,am_index(r.a[0],0x78),2,ob2a_w(r.d[3])) ||
        !am_write(c,am_index(r.a[0],0x7a),2,ob2a_w(r.d[4])) || !am_write(c,am_index(r.a[0],0x7c),2,ob2a_w(r.d[5])) ||
        !am_write(c,am_index(r.a[0],0x7e),2,ob2a_w(r.d[6])))return false;
    ob2a_clear(r);return am_call(c,0x49214,return_pc);
}
// MOVE.L d0,36(A6); MOVE.L d1,3a(A6); JSR 43ea4.l.
bool ob2a_store_xy(AnimationMachineContext& c,std::uint32_t return_pc) {
    if(!ob2a_put(c,0x36,4,c.s.d[0]) || !ob2a_put(c,0x3a,4,c.s.d[1]))return false;ob2a_clear(c.s);return am_call(c,0x43ea4,return_pc);
}
// MOVE.L 90(A6) or 96(A6),D0; MOVE.B 8e(A6) or 94(A6),D1; JSR 443d2.l.
bool ob2a_polar(AnimationMachineContext& c,std::uint32_t speed,std::uint32_t angle,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!ob2a_get(c,speed,4,value))return false;c.s.d[0]=value;
    if(!ob2a_get(c,angle,1,value))return false;am_byte(c.s.d[1],value);ob2a_clear(c.s);return am_call(c,0x443d2,return_pc);
}
// MOVE.L 72(A6),D0 (MOVE: C = 0); BEQ.W zero_pc.
bool ob2a_target(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ob2a_get(c,0x72,4,value))return false;c.s.d[0]=value;ob2a_clear(c.s);c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// CMPI.L #limit,d(A6); BLE / BGE.
bool ob2a_cmp_long(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t limit,Ob2aFlags& f) {
    if(!ob2a_cmp_mem(c,displacement,4,limit,f))return false;ob2a_set_c(c.s,f.c);return true;
}
// MOVE.L 90(A6),D0; CMPI.L #limit,D0.
bool ob2a_cmp_speed(AnimationMachineContext& c,std::uint32_t limit,Ob2aFlags& f) {
    std::uint32_t value=0;std::uint32_t result=0;if(!ob2a_get(c,0x90,4,value))return false;c.s.d[0]=value;
    f=ob2a_sub(4,value,limit,result);ob2a_set_c(c.s,f.c);return true;
}
// ADDQ.B / SUBQ.B #1,d(A6) followed by a fall-through or BRA.W to next_pc.
bool ob2a_step_byte(AnimationMachineContext& c,std::uint32_t displacement,bool subtract,std::uint32_t next_pc) {
    Ob2aFlags f;if(subtract){if(!ob2a_sub_mem(c,displacement,1,1,f))return false;}else{if(!ob2a_add_mem(c,displacement,1,1,f))return false;}
    ob2a_set_c(c.s,f.c);c.s.pc=next_pc;return true;
}
// SUBI.L #4000,90(A6) and the fall-through to next_pc.
bool ob2a_slow_speed(AnimationMachineContext& c,std::uint32_t next_pc) {
    Ob2aFlags f;if(!ob2a_sub_mem(c,0x90,4,0x4000,f))return false;ob2a_set_c(c.s,f.c);c.s.pc=next_pc;return true;
}
// SUBQ.W #1,7e(A6); BCC.W: the timer borrow is the C (borrow: timer 0 -> fall through; no borrow: branch).
bool ob2a_timer(AnimationMachineContext& c,std::uint32_t branch_pc,std::uint32_t fall_pc) {
    Ob2aFlags f;if(!ob2a_sub_mem(c,0x7e,2,1,f))return false;ob2a_set_c(c.s,f.c);c.s.pc=f.c?fall_pc:branch_pc;return true;
}
// BTST.B #0,15(A6); BEQ.W / BNE.W (Z = bit clear).
bool ob2a_phase_bit(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    bool bit=false;if(!ob2a_bit(c,0x15,0,bit))return false;c.s.pc=bit?set_pc:clear_pc;return true;
}
// CMPI.B #want,D0; BNE.W not_pc.
bool ob2a_state(AnimationMachineContext& c,std::uint32_t want,std::uint32_t equal_pc,std::uint32_t not_pc) {
    std::uint32_t result=0;const Ob2aFlags f=ob2a_sub(1,c.s.d[0],want,result);ob2a_set_c(c.s,f.c);c.s.pc=f.z?equal_pc:not_pc;return true;
}
}
// Objects B2a (180 block starts): the three orphan 28ae children of the seed 32 33 objects, 5eed2 (N25 child, 28), 5f504 (N26 child, 53) and 60516
// (N27 child, 99). Contract counts 181; the BLT at 60690 reads the N and V of two different CMPI predecessors (60684 with #80, 6068c with #ff80),
// which cannot be recomputed from the registers, so it is folded into both (interior PC, the N04 ab1a6 / N09 af7b0 precedent) and the other three
// Bcc blocks that follow a Bcc of the same flags (5f592 5f678 60680) are folded into their predecessors 5f584 5f66a 60670 as the contract counts them.
// Boundaries without an executor: 4b6f4 (pinned area_clear verifier, main decision), 44602 and every callee or child value outside this unit
// (b3dbc is the 2986 child data). The hit boxes 5eeac / 5eeca and the table 60c54 are passed as data. Known C: 4970a-spawn paths ORI Set (5f714
// 60640 60706 60790 6084a 60870 608ee 60914) fall into JMP 2a00 / the next block; every flag writer leaves its exact C (MOVE TST CLR AND: Clear,
// SUB CMP: borrow, ADD: carry), the consumers read a known C of 4b6f4 49fc6 1ab02 4b54e 28ae 2986. One banked LONG read per animation (200194 /
// 200090). No port, no bank change, no X, no register-indirect control transfer.
bool animation_objects_b2a_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;std::uint32_t result=0;bool bit=false;Ob2aFlags f;
    switch(r.pc) {
    // ================= 5eed2 (N25 28ae child; installed callbacks 5ef42 / 5ef8c / 5efba)
    // MOVE.L #40000,D0; MOVE.W 8a(A6),D1; JSR 443d2.l.
    case 0x5eed2:
        r.d[0]=0x40000;if(!ob2a_get(c,0x8a,2,value))return false;am_word(r.d[1],value);ob2a_clear(r);return am_call(c,0x443d2,0x5eee2);
    case 0x5eee2:if(!ob2a_put(c,0x36,4,r.d[0]) || !ob2a_put(c,0x3a,4,r.d[1]))return false;return ob2a_8ebe(c,0xd5f,0x5eef8);
    case 0x5eef8:return ob2a_8ebe(c,0xd60,0x5ef06);
    case 0x5ef06:return ob2a_8ebe(c,0xd61,0x5ef14);
    case 0x5ef14:return ob2a_bank_anim(c,OB2A_BANK_18B,0x18b,0x20c,0x5ef3c);
    case 0x5ef3c:if(!ob2a_install(c,0x5ef42))return false;r.pc=0x5ef42;return true;
    case 0x5ef42:return am_call(c,0x43ea4,0x5ef48);                            // JSR 43ea4.l.
    case 0x5ef48:return am_call(c,0x49fc6,0x5ef4e);                            // JSR 49fc6.l.
    case 0x5ef4e:r.a[0]=OB2A_HIT_A;return am_call(c,0x4ae4a,0x5ef58);          // LEA 5eeac(PC),A0; JSR 4ae4a.l.
    // CMPI.W #0,D0; BEQ.W 5ef66.
    case 0x5ef58:f=ob2a_sub(2,r.d[0],0,result);ob2a_set_c(r,f.c);r.pc=f.z?0x5ef66:0x5ef60;return true;
    case 0x5ef60:if(!ob2a_install(c,0x5ef8c))return false;r.pc=0x5ef66;return true;
    case 0x5ef66:case 0x5f5e0:case 0x5f73e:return am_call(c,0x4b6f4,r.pc==0x5ef66U?0x5ef6cU:(r.pc==0x5f5e0U?0x5f5e6U:0x5f744U)); // JSR 4b6f4.l (boundary).
    case 0x5ef6c:return ob2a_carry(c,0x5ef76,0x5ef70);                          // BCC.W 5ef76 (C returned by 4b6f4).
    case 0x5ef70:case 0x5ef84:case 0x5efca:case 0x5efde:case 0x5f5ea:case 0x5f718:case 0x5f738:case 0x5f748:case 0x5f758:
    case 0x60644:case 0x6070a:case 0x60794:case 0x60874:case 0x60918:case 0x60932:r.pc=0x2a00;return true; // JMP 2a00.l.
    case 0x5ef76:case 0x5efd0:r.a[0]=OB2A_HIT_B;return am_call(c,0x1ab02,r.pc==0x5ef76U?0x5ef80U:0x5efdaU); // LEA 5eeca(PC),A0; JSR 1ab02.l.
    case 0x5ef80:return ob2a_carry(c,0x5ef8a,0x5ef84);                          // BCC.W 5ef8a (C returned by 1ab02).
    case 0x5ef8a:case 0x5efe4:case 0x5f5f0:case 0x5f75e:case 0x60938:return am_return(c); // RTS.
    case 0x5ef8c:return ob2a_bank_anim(c,OB2A_BANK_18B,0x18b,0x210,0x5efb4);
    case 0x5efb4:if(!ob2a_install(c,0x5efba))return false;r.pc=0x5efba;return true;
    case 0x5efba:return am_call(c,0x43ea4,0x5efc0);
    case 0x5efc0:case 0x5f5c8:case 0x5f6b6:case 0x607d0:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.l.
    case 0x5efc6:return ob2a_carry(c,0x5efd0,0x5efca);                          // BCC.W 5efd0 (C returned by 49fc6).
    case 0x5efda:return ob2a_carry(c,0x5efe4,0x5efde);                          // BCC.W 5efe4 (C returned by 1ab02).
    // ================= 5f504 (N26 28ae child; installed callbacks 5f57c / 5f5f2 / 5f66a)
    case 0x5f504:return am_call(c,0x49a58,0x5f50a);
    // ANDI.W #1f,D0; SUBI.W #f,D0; ANDI.W #ff,D0; MOVE.B D0,94(A6); JSR 4b702.l.
    case 0x5f50a:
        am_word(r.d[0],r.d[0]&0x1fU);am_word(r.d[0],ob2a_w(r.d[0])-0xfU);am_word(r.d[0],r.d[0]&0xffU);
        if(!ob2a_put(c,0x94,1,ob2a_b(r.d[0])))return false;ob2a_clear(r);return am_call(c,0x4b702,0x5f520);
    // MOVE.L #90000,96(A6); MOVE.W #8,7e(A6); BSET.B #3,15(A6); MOVE.W #1110,68(A6); MOVE.W #1110,1e(A6); MOVE.W #cfb,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x5f520:
        if(!ob2a_put(c,0x96,4,0x90000) || !ob2a_put(c,0x7e,2,8) || !ob2a_bit_set(c,0x15,3) || !ob2a_put(c,0x68,2,0x1110) || !ob2a_put(c,0x1e,2,0x1110))return false;
        return ob2a_8ebe(c,0xcfb,0x5f54e);
    case 0x5f54e:return ob2a_bank_anim(c,OB2A_BANK_DA,0xda,0x24,0x5f576);
    case 0x5f576:if(!ob2a_install(c,0x5f57c))return false;r.pc=0x5f57c;return true;
    case 0x5f57c:return ob2a_timer(c,0x5f5a2,0x5f584);                          // SUBQ.W #1,7e(A6); BCC.W 5f5a2.
    // MOVE.W #8,7e(A6); TST.B 94(A6); BEQ.W 5f5a2; BMI.W 5f59e (the BMI at 5f592 is folded; Z and N of the same TST).
    case 0x5f584:
        if(!ob2a_put(c,0x7e,2,8) || !ob2a_get(c,0x94,1,value))return false;ob2a_clear(r);
        r.pc=ob2a_b(value)==0U?0x5f5a2:((value&0x80U)!=0U?0x5f59e:0x5f596);return true;
    case 0x5f596:return ob2a_step_byte(c,0x94,true,0x5f5a2);                    // SUBQ.B #1,94(A6); BRA.W 5f5a2.
    case 0x5f59e:return ob2a_step_byte(c,0x94,false,0x5f5a2);                   // ADDQ.B #1,94(A6).
    // MOVE.L 96(A6),D0; ASR.L #5,D0; SUB.L D0,96(A6); then ob2a_polar (MOVE.L 96(A6),D0; MOVE.B 94(A6),D1; JSR 443d2.l).
    case 0x5f5a2:
        if(!ob2a_get(c,0x96,4,value))return false;r.d[0]=ob2a_asr(value,5);if(!ob2a_sub_mem(c,0x96,4,r.d[0],f))return false;
        return ob2a_polar(c,0x96,0x94,0x5f5ba);
    case 0x5f5ba:return ob2a_store_xy(c,0x5f5c8);
    // CMPI.L #10000,36(A6); BGE.W 5f5e0.
    case 0x5f5ce:if(!ob2a_cmp_long(c,0x36,0x10000,f))return false;r.pc=ob2a_ge(f)?0x5f5e0:0x5f5da;return true;
    case 0x5f5da:if(!ob2a_install(c,0x5f5f2))return false;r.pc=0x5f5e0;return true;
    case 0x5f5e6:return ob2a_carry(c,0x5f5f0,0x5f5ea);                          // BCC.W 5f5f0 (C returned by 4b6f4).
    // MOVE.L #5f4e6,56(A6); MOVEQ #0,D0; JSR 49a58.l.
    case 0x5f5f2:if(!ob2a_put(c,0x56,4,0x5f4e6))return false;r.d[0]=0;ob2a_clear(r);return am_call(c,0x49a58,0x5f602);
    // ANDI.W #1fff,D0; LSL.L #4,D0; ADDI.L #40000,D0; NEG.L D0; MOVE.L D0,9a(A6); MOVE.L #ffffc000,96(A6); MOVE.W #e0ef,68(A6) 1e(A6); JSR 8ff4.l.
    case 0x5f602:
        am_word(r.d[0],r.d[0]&0x1fffU);r.d[0]=r.d[0]<<4;r.d[0]+=0x40000U;r.d[0]=0U-r.d[0];
        if(!ob2a_put(c,0x9a,4,r.d[0]) || !ob2a_put(c,0x96,4,0xffffc000U) || !ob2a_put(c,0x68,2,0xe0ef) || !ob2a_put(c,0x1e,2,0xe0ef))return false;
        ob2a_clear(r);return am_call(c,0x8ff4,0x5f62e);
    case 0x5f62e:return ob2a_8ebe(c,0xcfc,0x5f63c);
    case 0x5f63c:return ob2a_bank_anim(c,OB2A_BANK_DA,0xda,0x28,0x5f664);
    case 0x5f664:if(!ob2a_install(c,0x5f66a))return false;r.pc=0x5f66a;return true;
    // MOVE.W #2,7e(A6); TST.B 94(A6); BEQ.W 5f688; BMI.W 5f684 (the BMI at 678 is folded; Z and N of the same TST).
    case 0x5f66a:
        if(!ob2a_put(c,0x7e,2,2) || !ob2a_get(c,0x94,1,value))return false;ob2a_clear(r);
        r.pc=ob2a_b(value)==0U?0x5f688:((value&0x80U)!=0U?0x5f684:0x5f67c);return true;
    case 0x5f67c:return ob2a_step_byte(c,0x94,true,0x5f688);                    // SUBQ.B #1,94(A6); BRA.W 5f688.
    case 0x5f684:return ob2a_step_byte(c,0x94,false,0x5f688);                   // ADDQ.B #1,94(A6).
    // MOVE.L 96(A6),D0; CMP.L 9a(A6),D0; BLE.W 5f69a.
    case 0x5f688:
        if(!ob2a_get(c,0x96,4,value) || !ob2a_get(c,0x9a,4,other))return false;r.d[0]=value;
        f=ob2a_sub(4,value,other,result);ob2a_set_c(r,f.c);r.pc=ob2a_le(f)?0x5f69a:0x5f694;return true;
    // ASR.L #4,D0; ADD.L D0,96(A6); falls into 5f69a.
    case 0x5f694:
        r.d[0]=ob2a_asr(r.d[0],4);if(!ob2a_add_mem(c,0x96,4,r.d[0],f))return false;ob2a_set_c(r,f.c);r.pc=0x5f69a;return true;
    case 0x5f69a:return ob2a_polar(c,0x96,0x94,0x5f6a8);
    case 0x5f6a8:return ob2a_store_xy(c,0x5f6b6);
    case 0x5f6bc:return am_call(c,0x4b54e,0x5f6c2);                            // JSR 4b54e.l.
    case 0x5f6c2:case 0x60880:return ob2a_carry(c,r.pc==0x5f6c2U?0x5f6caU:0x60888U,r.pc==0x5f6c2U?0x5f6c6U:0x60884U); // BCC.W (C returned by 4b54e).
    case 0x5f6c6:case 0x60884:                                              // CLR.B 5e(A6) (C = 0).
        if(!ob2a_put(c,0x5e,1,0))return false;ob2a_clear(r);r.pc=r.pc+4U;return true;
    // BTST.B #7,61(A6); BEQ.W (Z = bit clear; C is not touched).
    case 0x5f6ca:if(!ob2a_bit(c,0x61,7,bit))return false;r.pc=bit?0x5f6d4:0x5f6da;return true;
    case 0x5f6d4:if(!ob2a_put(c,0x54,2,1))return false;ob2a_clear(r);r.pc=0x5f6da;return true; // MOVE.W #1,54(A6).
    case 0x5f6da:return ob2a_target(c,0x5f6ea,0x5f6e2);                          // MOVE.L 72(A6),D0; BEQ.W 5f6ea.
    case 0x5f6e2:case 0x607de:r.a[0]=r.d[0];return am_call(c,0x4ae4a,r.pc==0x5f6e2U?0x5f6eaU:0x607e6U); // MOVEA.L D0,A0; JSR 4ae4a.l.
    // CMPI.W #0,D0; BEQ.W 5f71e.
    case 0x5f6ea:f=ob2a_sub(2,r.d[0],0,result);ob2a_set_c(r,f.c);r.pc=f.z?0x5f71e:0x5f6f2;return true;
    case 0x5f6f2:return ob2a_child(c,0xd22e6,0x5f702);                           // MOVEA.L #d22e6,A0; MOVE.W #a,D0; JSR 28ae.l (child d22e6 is data).
    case 0x5f702:return ob2a_carry(c,0x5f718,0x5f706);                          // BCC.W 5f718 (C returned by 28ae).
    case 0x5f706:return ob2a_4970a(c,0x5f714);
    case 0x5f714:case 0x60640:case 0x60706:case 0x60790:case 0x6084a:case 0x60870:case 0x608ee:case 0x60914:
        r.carry=AnimationCarrySet;r.pc=r.pc+4U;return true;                      // ORI.B #1,CCR.
    // CMPI.W #140,42(A6); BGT.W 5f73e.
    case 0x5f71e:if(!ob2a_cmp_mem(c,0x42,2,0x140,f))return false;ob2a_set_c(r,f.c);r.pc=ob2a_gt(f)?0x5f73e:0x5f728;return true;
    // MOVE.W 46(A6),D0; SUBI.W #100,D0; CMPI.W #100,D0; BCS.W 5f73e.
    case 0x5f728:
        if(!ob2a_get(c,0x46,2,value))return false;am_word(r.d[0],value);f=ob2a_sub(2,r.d[0],0x100,result);am_word(r.d[0],result);
        f=ob2a_sub(2,r.d[0],0x100,result);ob2a_set_c(r,f.c);r.pc=f.c?0x5f73e:0x5f738;return true;
    case 0x5f744:return ob2a_carry(c,0x5f74e,0x5f748);                          // BCC.W 5f74e (C returned by 4b6f4).
    // CMPI.W #ffe0,42(A6); BGE.W 5f75e.
    case 0x5f74e:if(!ob2a_cmp_mem(c,0x42,2,0xffe0,f))return false;ob2a_set_c(r,f.c);r.pc=ob2a_ge(f)?0x5f75e:0x5f758;return true;
    // ================= 60516 (N27 28ae child; installed callback 605ae)
    case 0x60516:return am_call(c,0x49a58,0x6051c);
    // ANDI.W #3f,D0; ADDI.W #60,D0; MOVE.B D0,8e(A6); MOVE.L #30000,90(A6); LEA 60c54.l,A0; JSR 490ba.l.
    case 0x6051c:
        am_word(r.d[0],r.d[0]&0x3fU);am_word(r.d[0],ob2a_w(r.d[0])+0x60U);
        if(!ob2a_put(c,0x8e,1,ob2a_b(r.d[0])) || !ob2a_put(c,0x90,4,0x30000))return false;
        r.a[0]=OB2A_TABLE_60C54;ob2a_clear(r);return am_call(c,0x490ba,0x6053c);
    case 0x6053c:if(!ob2a_put(c,0x54,2,ob2a_w(r.d[0])))return false;ob2a_clear(r);return am_call(c,0x4b702,0x60546); // MOVE.W D0,54(A6); JSR 4b702.l.
    // BCLR.B #0,15(A6); TST.B 8f(A6); BEQ.W 6056c.
    case 0x60546:
        if(!ob2a_bit_clear(c,0x15,0) || !ob2a_get(c,0x8f,1,value))return false;ob2a_clear(r);r.pc=ob2a_b(value)==0U?0x6056c:0x60554;return true;
    // MOVE.W #1,54(A6); MOVE.W #d64,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x60554:if(!ob2a_put(c,0x54,2,1))return false;return ob2a_8ebe(c,0xd64,0x60568);
    case 0x60568:r.pc=0x6057a;return true;                                       // BRA.W 6057a.
    case 0x6056c:return ob2a_8ebe(c,0xd59,0x6057a);
    case 0x6057a:return ob2a_bank_anim(c,OB2A_BANK_18B,0x18b,0x12c,0x605a2);
    case 0x605a2:if(!ob2a_put(c,0x7e,2,4) || !ob2a_install(c,0x605ae))return false;r.pc=0x605ae;return true; // MOVE.W #4,7e(A6); MOVE.L #605ae,(A6).
    // MOVEA.L c(A6),A0; MOVE.B 77(A0),D0; CMPI.B #1,D0; BNE.W 605f8.
    case 0x605ae:
        if(!ob2a_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x77),1,value))return false;am_byte(r.d[0],value);
        f=ob2a_sub(1,r.d[0],1,result);ob2a_set_c(r,f.c);r.pc=f.z?0x605be:0x605f8;return true;
    case 0x605be:return ob2a_timer(c,0x605f4,0x605c6);                          // SUBQ.W #1,7e(A6); BCC.W 605f4.
    // MOVE.W #4,7e(A6); TST.B 8e(A6); BMI.W 605dc.
    case 0x605c6:
        if(!ob2a_put(c,0x7e,2,4) || !ob2a_get(c,0x8e,1,value))return false;ob2a_clear(r);r.pc=(value&0x80U)!=0U?0x605dc:0x605d4;return true;
    case 0x605d4:return ob2a_step_byte(c,0x8e,false,0x605e0);                   // ADDQ.B #1,8e(A6); BRA.W 605e0.
    case 0x605dc:return ob2a_step_byte(c,0x8e,true,0x605e0);                    // SUBQ.B #1,8e(A6).
    // MOVE.L 90(A6),D0; CMPI.L #40000,D0; BGE.W 605f4.
    case 0x605e0:if(!ob2a_cmp_speed(c,0x40000,f))return false;r.pc=ob2a_ge(f)?0x605f4:0x605ee;return true;
    // ASR.L #3,D0; ADD.L D0,90(A6); falls into 605f4.
    case 0x605ee:
        r.d[0]=ob2a_asr(r.d[0],3);if(!ob2a_add_mem(c,0x90,4,r.d[0],f))return false;ob2a_set_c(r,f.c);r.pc=0x605f4;return true;
    case 0x605f4:case 0x606ba:case 0x6074a:case 0x607b0:r.pc=0x607b4;return true; // BRA.W 607b4.
    case 0x605f8:return ob2a_state(c,2,0x60600,0x606be);                        // CMPI.B #2,D0; BNE.W 606be.
    case 0x60600:return ob2a_phase_bit(c,0x6060a,0x60616);                      // BTST.B #0,15(A6); BNE.W 60616.
    case 0x6060a:case 0x606d0:                                                  // BSET.B #0,15(A6); MOVE.W #f0 / #78,7e(A6).
        if(!ob2a_bit_set(c,0x15,0) || !ob2a_put(c,0x7e,2,r.pc==0x6060aU?0xf0U:0x78U))return false;ob2a_clear(r);r.pc=r.pc==0x6060aU?0x60616U:0x606dcU;return true;
    case 0x60616:return ob2a_timer(c,0x6064a,0x6061e);                          // SUBQ.W #1,7e(A6); BCC.W 6064a.
    case 0x6061e:case 0x606e4:case 0x6076e:case 0x608f2:case 0x6084e:
        return ob2a_child(c,0xd1cd8,r.pc==0x6061eU?0x6062eU:(r.pc==0x606e4U?0x606f4U:(r.pc==0x6076eU?0x6077eU:(r.pc==0x608f2U?0x60902U:0x6085eU)))); // child d1cd8 is data.
    case 0x6062e:return ob2a_carry(c,0x60644,0x60632);                          // BCC.W 60644 (C returned by 28ae).
    case 0x60632:return ob2a_4970a(c,0x60640);
    // MOVEA.L c(A6),A0; MOVEA.L c(A0),A0; MOVE.W 2e(A0),D0; MOVE.W 32(A0),D1; ADDI.W #ffd0,D0; ADDI.W #10,D1; SUB.W 2e(A6),D0; SUB.W 32(A6),D1; JSR 44602.l.
    case 0x6064a:
        if(!ob2a_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0xc),4,value))return false;r.a[0]=value;
        if(!am_read(c,am_index(r.a[0],0x2e),2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,am_index(r.a[0],0x32),2,value))return false;am_word(r.d[1],value);
        am_word(r.d[0],ob2a_w(r.d[0])+0xffd0U);am_word(r.d[1],ob2a_w(r.d[1])+0x10U);
        if(!ob2a_get(c,0x2e,2,value))return false;f=ob2a_sub(2,r.d[0],value,result);am_word(r.d[0],result);
        if(!ob2a_get(c,0x32,2,value))return false;f=ob2a_sub(2,r.d[1],value,result);am_word(r.d[1],result);
        ob2a_set_c(r,f.c);return am_call(c,0x44602,0x60670);
    // ANDI.W #ff,D0; MOVEQ #0,D1; MOVE.B 8e(A6),D1; SUB.W D1,D0; BEQ.W 6069c; BLT.W 6068c (the BLT at 60680 is folded; N and V of the same SUB).
    case 0x60670:
        am_word(r.d[0],r.d[0]&0xffU);r.d[1]=0;if(!ob2a_get(c,0x8e,1,value))return false;am_byte(r.d[1],value);
        f=ob2a_sub(2,r.d[0],r.d[1],result);am_word(r.d[0],result);ob2a_set_c(r,f.c);
        r.pc=f.z?0x6069c:(ob2a_lt(f)?0x6068c:0x60684);return true;
    // CMPI.W #80,D0 / #ff80,D0; BRA.W 60690; BLT.W 6069a (the BLT at 60690 is folded into both CMPI).
    case 0x60684:case 0x6068c:
        f=ob2a_sub(2,r.d[0],r.pc==0x60684U?0x80U:0xff80U,result);ob2a_set_c(r,f.c);r.pc=ob2a_lt(f)?0x6069a:0x60694;return true;
    case 0x60694:f=ob2a_add(2,r.d[1],4,result);am_word(r.d[1],result);ob2a_set_c(r,f.c);r.pc=0x6069c;return true; // ADDQ.W #4,D1; BRA.W 6069c.
    case 0x6069a:f=ob2a_sub(2,r.d[1],4,result);am_word(r.d[1],result);ob2a_set_c(r,f.c);r.pc=0x6069c;return true; // SUBQ.W #4,D1.
    // ANDI.W #ff,D1; MOVE.B D1,8e(A6); MOVE.L 90(A6),D0; CMPI.L #fffc0000,D0; BLE.W 606ba.
    case 0x6069c:
        am_word(r.d[1],r.d[1]&0xffU);if(!ob2a_put(c,0x8e,1,ob2a_b(r.d[1])))return false;
        if(!ob2a_cmp_speed(c,0xfffc0000U,f))return false;r.pc=ob2a_le(f)?0x606ba:0x606b2;return true;
    case 0x606b2:case 0x60742:case 0x607a8:return ob2a_slow_speed(c,r.pc==0x606b2U?0x606baU:(r.pc==0x60742U?0x6074aU:0x607b0U)); // SUBI.L #4000,90(A6).
    case 0x606be:return ob2a_state(c,3,0x606c6,0x6074e);                        // CMPI.B #3,D0; BNE.W 6074e.
    case 0x606c6:return ob2a_phase_bit(c,0x606d0,0x606dc);                      // BTST.B #0,15(A6); BNE.W 606dc.
    case 0x606dc:return ob2a_timer(c,0x60710,0x606e4);                          // SUBQ.W #1,7e(A6); BCC.W 60710.
    case 0x606f4:return ob2a_carry(c,0x6070a,0x606f8);                          // BCC.W 6070a (C returned by 28ae).
    case 0x606f8:return ob2a_4970a(c,0x60706);
    // MOVE.B 8e(A6),D0; BMI.W 60728.
    case 0x60710:if(!ob2a_get(c,0x8e,1,value))return false;am_byte(r.d[0],value);ob2a_clear(r);r.pc=(value&0x80U)!=0U?0x60728:0x60718;return true;
    // CMPI.B #40,D0; BLE.W 60724.
    case 0x60718:f=ob2a_sub(1,r.d[0],0x40,result);ob2a_set_c(r,f.c);r.pc=ob2a_le(f)?0x60724:0x60720;return true;
    case 0x60720:return ob2a_step_byte(c,0x8e,true,0x60724);                    // SUBQ.B #1,8e(A6).
    case 0x60724:r.pc=0x60734;return true;                                       // BRA.W 60734.
    // CMPI.B #c0,D0; BGE.W 60734.
    case 0x60728:f=ob2a_sub(1,r.d[0],0xc0,result);ob2a_set_c(r,f.c);r.pc=ob2a_ge(f)?0x60734:0x60730;return true;
    case 0x60730:return ob2a_step_byte(c,0x8e,false,0x60734);                   // ADDQ.B #1,8e(A6).
    // MOVE.L 90(A6),D0; CMPI.L #fffc0000,D0; BLE.W 6074a.
    case 0x60734:if(!ob2a_cmp_speed(c,0xfffc0000U,f))return false;r.pc=ob2a_le(f)?0x6074a:0x60742;return true;
    case 0x6074e:return ob2a_state(c,5,0x60756,0x607b4);                        // CMPI.B #5,D0; BNE.W 607b4.
    case 0x60756:return ob2a_phase_bit(c,0x60766,0x60760);                      // BTST.B #0,15(A6); BEQ.W 60766.
    case 0x60760:if(!ob2a_bit_clear(c,0x15,0))return false;r.pc=0x60766;return true; // BCLR.B #0,15(A6).
    case 0x60766:return ob2a_timer(c,0x6079a,0x6076e);                          // SUBQ.W #1,7e(A6); BCC.W 6079a.
    case 0x6077e:return ob2a_carry(c,0x60794,0x60782);                          // BCC.W 60794 (C returned by 28ae).
    case 0x60782:return ob2a_4970a(c,0x60790);
    // MOVE.L 90(A6),D0; CMPI.L #fff80000,D0; BLE.W 607b0.
    case 0x6079a:if(!ob2a_cmp_speed(c,0xfff80000U,f))return false;r.pc=ob2a_le(f)?0x607b0:0x607a8;return true;
    case 0x607b4:return ob2a_polar(c,0x90,0x8e,0x607c2);
    case 0x607c2:return ob2a_store_xy(c,0x607d0);
    case 0x607d6:return ob2a_target(c,0x607e6,0x607de);                          // MOVE.L 72(A6),D0; BEQ.W 607e6.
    // CMPI.W #0,D0; BEQ.W 6087a.
    case 0x607e6:f=ob2a_sub(2,r.d[0],0,result);ob2a_set_c(r,f.c);r.pc=f.z?0x6087a:0x607ee;return true;
    // TST.B 8f(A6); BEQ.W 6084e / 608f2.
    case 0x607ee:case 0x60892:
        if(!ob2a_get(c,0x8f,1,value))return false;ob2a_clear(r);
        if(r.pc==0x607eeU)r.pc=ob2a_b(value)==0U?0x6084eU:0x607f6U;else r.pc=ob2a_b(value)==0U?0x608f2U:0x6089aU;return true;
    case 0x607f6:return ob2a_2986(c,0x60828);                                    // seven pushes; JSR 2986.l (child b3dbc is data).
    case 0x6089a:return ob2a_2986(c,0x608cc);
    // MOVEM.W (A7)+,D0-D6; BCC.W 6084e / 608f2 (C returned by 2986).
    case 0x60828:case 0x608cc:
        if(!ob2a_movem_pop(c))return false;return ob2a_carry(c,r.pc==0x60828U?0x6084eU:0x608f2U,r.pc==0x60828U?0x60830U:0x608d4U);
    case 0x60830:return ob2a_fill_child(c,0x6084a);
    case 0x608d4:return ob2a_fill_child(c,0x608ee);
    case 0x6085e:return ob2a_carry(c,0x60874,0x60862);                          // BCC.W 60874 (C returned by 28ae).
    case 0x60862:return ob2a_4970a(c,0x60870);
    case 0x6087a:return am_call(c,0x4b54e,0x60880);                              // JSR 4b54e.l.
    // BTST.B #7,61(A6); BEQ.W 6091e.
    case 0x60888:if(!ob2a_bit(c,0x61,7,bit))return false;r.pc=bit?0x60892:0x6091e;return true;
    case 0x60902:return ob2a_carry(c,0x60918,0x60906);                          // BCC.W 60918 (C returned by 28ae).
    case 0x60906:return ob2a_4970a(c,0x60914);
    // CMPI.B #3,D0; BNE.W 60938.
    case 0x6091e:return ob2a_state(c,3,0x60926,0x60938);
    // MOVE.W 42(A6),D0; CMPI.W #140,D0; BCC.W 60938.
    case 0x60926:
        if(!ob2a_get(c,0x42,2,value))return false;am_word(r.d[0],value);f=ob2a_sub(2,r.d[0],0x140,result);ob2a_set_c(r,f.c);
        r.pc=f.c?0x60932:0x60938;return true;
    default:return am_error(c,"unsupported animation objects b2a PC");
    }
}
}
