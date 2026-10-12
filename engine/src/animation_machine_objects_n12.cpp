#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Fixed ROM tables read through the live bus (the original never range-checks their indexes).
const std::uint32_t ON12_Y_TABLE=0x52e64;           // MOVE.W 52e64(PC,D0.W),D0 (52e4a): WORD per 94(A6).
const std::uint32_t ON12_NEXT_STATE=0x531a2;        // LEA 531a2(PC,D0.W),A0 (53148): 4 x 4 BYTE next-state table.
const std::uint32_t ON12_STATE_CALLBACKS=0x531b2;   // MOVE.L 531b2(PC,D0.W),D7 (5315e): LONG callback per state.
const std::uint32_t ON12_CHILD_CALLBACKS=0x53b50;   // MOVE.L 53b50(PC,D7.W),D7 (53ad0): LONG 28ae child callback.
const std::uint32_t ON12_PART_LISTS=0x53b58;        // LEA 53b58(PC),A1 (53a8e): LONG animation list per parent 9b.
// Banked LONGs (live bus, current PVC bank).
const std::uint32_t ON12_BANK_RECORD=0x200188;      // MOVE.L 200188.L,22(A6).
const std::uint32_t ON12_BANK_POINTER=0x200370;     // MOVEA.L 200370.L,A0 (52fe4).
bool on12_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on12_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
std::int32_t on12_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
// ASR.L #n with the sign bit copied in (n < 32).
std::uint32_t on12_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t fill=(value&0x80000000U)?~(0xffffffffU>>n):0U;return (value>>n)|fill;
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc.
bool on12_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n12 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,(A6) then continue at next_pc.
bool on12_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// MOVEA.L #list,A1; MOVE.W #rate,D0; JSR 49f8c.L.
bool on12_animation(AnimationMachineContext& c,std::uint32_t list,std::uint32_t rate,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],rate);return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L #target,A0; MOVE.W #0,D0; JSR 28ae.L.
bool on12_child(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    c.s.a[0]=target;am_word(c.s.d[0],0);return am_call(c,0x28ae,return_pc);
}
// BTST.B #bit,displacement(A6): true when the bit is set.
bool on12_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on12_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET/BCLR.B #bit,displacement(A6); was = the bit before the change.
bool on12_bit_op(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool set_bit,bool& was) {
    std::uint32_t value=0;if(!on12_get(c,displacement,1,value))return false;const std::uint32_t mask=1U<<bit;was=(value&mask)!=0U;
    value=set_bit?(value|mask):(value&~mask);return on12_put(c,displacement,1,value&255U);
}
// TST.B displacement(A6): true when non-zero.
bool on12_nonzero(AnimationMachineContext& c,std::uint32_t displacement,bool& nonzero) {
    std::uint32_t value=0;if(!on12_get(c,displacement,1,value))return false;nonzero=value!=0U;return true;
}
// CMPI.B #value,9e(A6): true when equal.
bool on12_state(AnimationMachineContext& c,std::uint32_t value,bool& equal) {
    std::uint32_t got=0;if(!on12_get(c,0x9e,1,got))return false;equal=got==value;return true;
}
// Child head: MOVE.W #173,20(A6); MOVE.L 200188.L,22(A6); MOVE.W #0,D0; MOVE.W #0,D1; JSR 49290.L.
bool on12_part_head(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;
    if(!on12_put(c,0x20,2,0x173) || !am_read(c,ON12_BANK_RECORD,4,value) || !on12_put(c,0x22,4,value))return false;
    am_word(c.s.d[0],0);am_word(c.s.d[1],0);return am_call(c,0x49290,return_pc);
}
// BSET.B #6,15(A6); MOVE.W #look,68(A6); MOVE.W #look,1e(A6); JSR 16ef0.L.
bool on12_look(AnimationMachineContext& c,std::uint32_t look,std::uint32_t return_pc) {
    bool was=false;
    if(!on12_bit_op(c,0x15,6,true,was) || !on12_put(c,0x68,2,look) || !on12_put(c,0x1e,2,look))return false;return am_call(c,0x16ef0,return_pc);
}
// MOVE.W #look,68(A0); MOVE.W #look,1e(A0) on the node returned by d3802.
bool on12_spawn_look(AnimationMachineContext& c,std::uint32_t look) {
    return am_write(c,am_index(c.s.a[0],0x68),2,look) && am_write(c,am_index(c.s.a[0],0x1e),2,look);
}
}
// Objects F4 N12 (old U26; 212 block starts): the parent callback 53050 (helper 52fe4, position helper 52e4a, state callbacks 53102
// 53122 531c2 5327a 53222 5310c and the C helper 5317c), the five 28ae children 539f8 53b70 53c42 53d14 53e70 with their installed
// states, the shared tails 52e9c (death: 2a0a, d3802, 4b6ec, 49274, 482fa, child 52f80, 8ff4, 8ebe, 49f8c -> 52f4a/52f96) 52f9c
// 539e4, and the interpreter command callbacks 52e78 (command 30) and 53ad0 (command 31). Boundaries without an executor: 482fa,
// d3802, 4833e. Known C: Set 53196, Clear 5319c (returned to the consumer 53130). N12 writes no port and changes no bank.
bool animation_objects_n12_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool flag=false;
    switch(r.pc) {
    // ---- 52e4a (helper): MOVEQ #0,D0; MOVE.W 94(A6),D0; ADD.W D0,D0; MOVE.W 52e64(PC,D0.W),D0; SWAP D0; MOVE.L D0,32(A6);
    // JSR 43e34.L.
    case 0x52e4a:
        r.d[0]=0;if(!on12_get(c,0x94,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]<<1);
        if(!am_read(c,am_index(ON12_Y_TABLE,r.d[0]),2,value))return false;am_word(r.d[0],value);am_swap(r.d[0]);
        if(!on12_put(c,0x32,4,r.d[0]))return false;return am_call(c,0x43e34,0x52e62);
    case 0x52e62:case 0x52e9a:case 0x52f94:case 0x52fe2:case 0x539f6:case 0x53ace:case 0x53c40:case 0x53d12:case 0x53db8:
    case 0x53e2c:case 0x53e6e:
        return am_return(c);                                                 // RTS.
    // ---- 52e78 (interpreter command 30, A0 = arguments): MOVE.W (A0)+,D0; MOVE.B D0,9c(A6); MOVEQ #0,D0; MOVE.W (A0),D0; SWAP D0;
    // BTST.B #0,15(A6); BEQ.W 52e90; NEG.L D0 (52e8e).
    case 0x52e78:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[0],value);if(!on12_put(c,0x9c,1,r.d[0]&255U))return false;
        r.d[0]=0;if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);am_swap(r.d[0]);
        if(!on12_bit(c,0x15,0,flag))return false;r.pc=flag?0x52e8e:0x52e90;return true;
    case 0x52e8e:r.d[0]=0U-r.d[0];r.pc=0x52e90;return true;
    // ADD.L D0,32(A6); JSR 43e34.L.
    case 0x52e90:if(!on12_get(c,0x32,4,value) || !on12_put(c,0x32,4,value+r.d[0]))return false;return am_call(c,0x43e34,0x52e9a);
    // ---- 52e9c (death tail).
    case 0x52e9c:return am_call(c,0x2a0a,0x52ea2);                           // JSR 2a0a.L.
    case 0x52ea2:r.a[1]=0x549bc;return am_call(c,0xd3802,0x52eac);          // LEA 549bc(PC),A1; JSR d3802.L (boundary).
    case 0x52eac:if(!on12_spawn_look(c,0xe0ed))return false;return am_call(c,0x4b6ec,0x52ebe);
    case 0x52ebe:return am_call(c,0x49274,0x52ec4);                          // JSR 49274.L.
    // BCLR.B #2,9d(A6); ST.B 5d44(A5); JSR 482fa.L (boundary).
    case 0x52ec4:
        if(!on12_bit_op(c,0x9d,2,false,flag) || !am_write(c,am_index(r.a[5],0x5d44),1,0xff))return false;return am_call(c,0x482fa,0x52ed4);
    case 0x52ed4:return on12_child(c,0x52f80,0x52ee4);                       // 28ae child 52f80.
    // MOVE.W #3c,76(A0); LEA 549e0(PC),A1; JSR d3802.L.
    case 0x52ee4:if(!am_write(c,am_index(r.a[0],0x76),2,0x3c))return false;r.a[1]=0x549e0;return am_call(c,0xd3802,0x52ef4);
    case 0x52ef4:if(!on12_spawn_look(c,0xe0ed))return false;r.a[1]=0x549ce;return am_call(c,0xd3802,0x52f0a);
    case 0x52f0a:if(!on12_spawn_look(c,0xe0ec))return false;return am_call(c,0x8ff4,0x52f1c);
    case 0x52f1c:am_word(r.d[0],0xd28);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x52f2a); // MOVE.W #d28,D0; MOVE.B #0,D1; JSR 8ebe.L.
    // MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 90(A1),A1; JSR 49f8c.L.
    case 0x52f2a:
        am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);if(!on12_get(c,0x22,4,value))return false;r.a[1]=value;
        if(!am_read(c,am_index(r.a[1],0x90),4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,0x52f40);
    case 0x52f40:if(!on12_put(c,0x36,4,0))return false;return on12_install(c,0x52f4a,0x52f4a); // CLR.L 36(A6); MOVE.L #52f4a,(A6).
    // ---- 52f4a (installed).
    case 0x52f4a:return am_call(c,0x4b6ec,0x52f50);
    // MOVE.L #ffff0000,D1; SUB.L 3a(A6),D1; ASR.L #5,D1; ADD.L D1,3a(A6); JSR 43ea4.L.
    case 0x52f50:
        if(!on12_get(c,0x3a,4,value))return false;r.d[1]=on12_asr(0xffff0000U-value,5);
        if(!on12_get(c,0x3a,4,value) || !on12_put(c,0x3a,4,value+r.d[1]))return false;return am_call(c,0x43ea4,0x52f66);
    case 0x52f66:return am_call(c,0x49fc6,0x52f6c);
    // CMPI.W #a0,46(A6); BGT.W 52f7c (signed).
    case 0x52f6c:if(!on12_get(c,0x46,2,value))return false;r.pc=on12_signed_word(value)>0xa0?0x52f7c:0x52f76;return true;
    case 0x52f76:return on12_install(c,0x52f96,0x52f7c);                     // MOVE.L #52f96,(A6).
    case 0x52f7c:case 0x53178:r.pc=0x52f9c;return true;                     // BRA.W 52f9c.
    // ---- 52f80 (28ae child): SUBQ.W #1,76(A6); BPL.W 52f94; JSR 4833e.L (boundary); JMP 2a00.L.
    case 0x52f80:
        if(!on12_get(c,0x76,2,value))return false;value=(value-1U)&65535U;if(!on12_put(c,0x76,2,value))return false;
        r.pc=(value&0x8000U)?0x52f88:0x52f94;return true;
    case 0x52f88:return am_call(c,0x4833e,0x52f8e);
    case 0x52f8e:r.pc=0x2a00;return true;
    // ---- 52f96 (installed): JMP 2a24.L.
    case 0x52f96:r.pc=0x2a24;return true;
    // ---- 52f9c (shared tail): MOVE.W 54(A6),D0; CMP.W 78(A6),D0; BCC.W 52fb6 (unsigned).
    case 0x52f9c:
        if(!on12_get(c,0x54,2,value))return false;am_word(r.d[0],value);if(!on12_get(c,0x78,2,other))return false;
        r.pc=(r.d[0]&65535U)>=other?0x52fb6:0x52fa8;return true;
    case 0x52fa8:if(!on12_bit_op(c,0x9d,1,true,flag))return false;r.pc=flag?0x52fb6:0x52fb2;return true; // BSET.B #1,9d(A6); BNE.
    case 0x52fb2:if(!on12_put(c,0x9f,1,0xff))return false;r.pc=0x52fb6;return true; // ST.B 9f(A6).
    case 0x52fb6:if(!on12_bit(c,0x9d,0,flag))return false;r.pc=flag?0x52fe2:0x52fc0;return true; // BTST.B #0,9d(A6); BNE.
    case 0x52fc0:if(!on12_bit(c,0x61,7,flag))return false;r.pc=flag?0x52fca:0x52fd8;return true; // BTST.B #7,61(A6); BEQ.
    // MOVE.L #0,56(A6); BSET.B #0,9d(A6).
    case 0x52fca:if(!on12_put(c,0x56,4,0) || !on12_bit_op(c,0x9d,0,true,flag))return false;r.pc=0x52fd8;return true;
    case 0x52fd8:return am_call(c,0x4b54e,0x52fde);
    case 0x52fde:if(!on12_put(c,0x5e,1,0))return false;r.pc=0x52fe2;return true; // CLR.B 5e(A6).
    // ---- 52fe4 (helper): MOVE.W #173,20(A6); MOVE.L 200188.L,22(A6); MOVEA.L 200370.L,A0; MOVEA.L 4(A0),A0; MOVE.L A0,56(A6);
    // LEA 55a82.L,A0; JSR 490ba.L.
    case 0x52fe4:
        if(!on12_put(c,0x20,2,0x173) || !am_read(c,ON12_BANK_RECORD,4,value) || !on12_put(c,0x22,4,value))return false;
        if(!am_read(c,ON12_BANK_POINTER,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],4),4,value))return false;
        r.a[0]=value;if(!on12_put(c,0x56,4,r.a[0]))return false;r.a[0]=0x55a82;return am_call(c,0x490ba,0x5300c);
    case 0x5300c:if(!on12_put(c,0x54,2,r.d[0]&65535U))return false;r.a[0]=0x55acc;return am_call(c,0x490ba,0x5301c);
    // MOVE.W D0,78(A6); MOVE.W #0,98(A6); MOVE.W #0,94(A6); BSR.W 52e4a.
    case 0x5301c:
        if(!on12_put(c,0x78,2,r.d[0]&65535U) || !on12_put(c,0x98,2,0) || !on12_put(c,0x94,2,0))return false;return am_call(c,0x52e4a,0x53030);
    // MOVE.L #1280000,2e(A6); ST.B 9a(A6); MOVE.B #ff,9b(A6); MOVE.W #ffff,90(A6); MOVE.B #a,a1(A6); RTS.
    case 0x53030:
        if(!on12_put(c,0x2e,4,0x1280000) || !on12_put(c,0x9a,1,0xff) || !on12_put(c,0x9b,1,0xff) || !on12_put(c,0x90,2,0xffff) ||
            !on12_put(c,0xa1,1,0xa))return false;
        return am_return(c);
    // ---- 53050 (parent callback).
    case 0x53050:return am_call(c,0x52fe4,0x53052);                          // BSR.B 52fe4.
    case 0x53052:case 0x53a14:case 0x53b8c:case 0x53c5e:case 0x53e8c:       // MOVE.W #d25,D0; MOVE.B #0,D1; JSR 8ebe.L.
        am_word(r.d[0],0xd25);am_byte(r.d[1],0);
        return am_call(c,0x8ebe,r.pc==0x53052?0x53060:r.pc==0x53a14?0x53a22:r.pc==0x53b8c?0x53b9a:r.pc==0x53c5e?0x53c6c:0x53e9a);
    case 0x53d30:am_word(r.d[0],0xd29);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x53d3e);
    case 0x53060:case 0x53a22:case 0x53b9a:case 0x53c6c:case 0x53e9a:       // MOVE.W #922,D0; JSR 4a496.L.
        am_word(r.d[0],0x922);
        return am_call(c,0x4a496,r.pc==0x53060?0x5306a:r.pc==0x53a22?0x53a2c:r.pc==0x53b9a?0x53ba4:r.pc==0x53c6c?0x53c76:0x53ea4);
    case 0x5306a:return on12_look(c,0x800,0x53082);
    case 0x53082:return on12_child(c,0x53e70,0x53092);
    case 0x53092:return on12_child(c,0x539f8,0x530a2);
    case 0x530a2:return on12_child(c,0x53b70,0x530b2);
    // MOVE.B #0,9e(A0); MOVE.L A0,84/80/88(A6); next child.
    case 0x530b2:
        if(!am_write(c,am_index(r.a[0],0x9e),1,0) || !on12_put(c,0x84,4,r.a[0]))return false;return on12_child(c,0x53c42,0x530cc);
    case 0x530cc:
        if(!am_write(c,am_index(r.a[0],0x9e),1,0) || !on12_put(c,0x80,4,r.a[0]))return false;return on12_child(c,0x53d14,0x530e6);
    // MOVE.B #0,9e(A0); MOVE.L A0,88(A6); MOVE.W #2,96(A6); MOVE.L #53102,7c(A6); BRA.W 531c2.
    case 0x530e6:
        if(!am_write(c,am_index(r.a[0],0x9e),1,0) || !on12_put(c,0x88,4,r.a[0]) || !on12_put(c,0x96,2,2) ||
            !on12_put(c,0x7c,4,0x53102))return false;
        r.pc=0x531c2;return true;
    // ---- 53102 (callback from 7c): MOVE.W #19d4,D0; JSR 3af8.L; then 5310c (also installed out of range).
    case 0x53102:am_word(r.d[0],0x19d4);return am_call(c,0x3af8,0x5310c);
    case 0x5310c:return on12_animation(c,0x54e12,0x100,0x5311c);
    case 0x5311c:return on12_install(c,0x53122,0x53122);
    // ---- 53122 / 531c2 / 53222 / 5327a: BTST.B #0,9d(A6); BNE.W 52e9c.
    case 0x53122:case 0x531c2:case 0x53222:case 0x5327a:
        if(!on12_bit(c,0x9d,0,flag))return false;
        r.pc=flag?0x52e9c:r.pc==0x53122?0x5312c:r.pc==0x531c2?0x531cc:r.pc==0x53222?0x5322c:0x53284;return true;
    case 0x5312c:return am_call(c,0x5317c,0x53130);                          // JSR 5317c(PC).
    case 0x53130:return on12_carry(c,0x5316c,0x53134);                        // BCC.W 5316c (C returned by 5317c).
    // MOVE.W 90(A6),D0; CMPI.W #ffff,D0; BNE.W 53148; MOVE.W #0,D0 (53140).
    case 0x53134:if(!on12_get(c,0x90,2,value))return false;am_word(r.d[0],value);r.pc=(value&65535U)!=0xffffU?0x53148:0x53140;return true;
    case 0x53140:am_word(r.d[0],0);r.pc=0x5315e;return true;
    // ADD.W D0,D0 (twice); LEA 531a2(PC,D0.W),A0; JSR 49a58.L.
    case 0x53148:am_word(r.d[0],r.d[0]<<2);r.a[0]=am_index(ON12_NEXT_STATE,r.d[0]);return am_call(c,0x49a58,0x53156);
    // ANDI.W #3,D0; MOVE.B (A0,D0.W),D0.
    case 0x53156:am_word(r.d[0],r.d[0]&3U);if(!am_read(c,am_index(r.a[0],r.d[0]),1,value))return false;am_byte(r.d[0],value);r.pc=0x5315e;return true;
    // MOVE.W D0,90(A6); ADD.W D0,D0 (twice); MOVE.L 531b2(PC,D0.W),D7; MOVE.L D7,(A6).
    case 0x5315e:
        if(!on12_put(c,0x90,2,r.d[0]&65535U))return false;am_word(r.d[0],r.d[0]<<2);
        if(!am_read(c,am_index(ON12_STATE_CALLBACKS,r.d[0]),4,value))return false;r.d[7]=value;return on12_install(c,r.d[7],0x5316c);
    case 0x5316c:case 0x531dc:case 0x53ab2:case 0x53c20:case 0x53cf2:case 0x53dac:case 0x53e02:case 0x53e44:case 0x539e4: // JSR 43e34.L.
        return am_call(c,0x43e34,r.pc+6U);
    case 0x53172:case 0x531e2:case 0x5322c:case 0x53284:case 0x53ab8:case 0x53c26:case 0x53cf8:case 0x53db2:case 0x53e08:
    case 0x53e4a:case 0x539ea:                                              // JSR 49fc6.L.
        return am_call(c,0x49fc6,r.pc+6U);
    // ---- 5317c (helper, C returned): MOVEQ #0,D0; JSR 49392.L.
    case 0x5317c:r.d[0]=0;return am_call(c,0x49392,0x53184);
    // SCS.B D7 (C of 49392); MOVEQ #1,D0 (C no longer consumed); JSR 49392.L.
    case 0x53184:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n12 caller requires known carry");
        am_byte(r.d[7],r.carry==AnimationCarrySet?0xffU:0U);r.d[0]=1;r.carry=AnimationCarryUnknown;return am_call(c,0x49392,0x5318e);
    // SCS.B D0; OR.B D7,D0; BEQ.W 5319c.
    case 0x5318e:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n12 caller requires known carry");
        am_byte(r.d[0],r.carry==AnimationCarrySet?0xffU:0U);am_byte(r.d[0],(r.d[0]|r.d[7])&255U);r.carry=AnimationCarryUnknown;
        r.pc=(r.d[0]&255U)==0U?0x5319c:0x53196;return true;
    case 0x53196:r.carry=AnimationCarrySet;return am_return(c);             // ORI.B #1,CCR; RTS.
    case 0x5319c:r.carry=AnimationCarryClear;return am_return(c);           // ANDI.B #fe,CCR; RTS.
    // ---- 531c2 body: MOVE.W 94(A6),D0; CMP.W 96(A6),D0; BGT.W 531f0; BLT.W 53248 (signed).
    case 0x531cc:
        if(!on12_get(c,0x94,2,value))return false;am_word(r.d[0],value);if(!on12_get(c,0x96,2,other))return false;
        r.pc=on12_signed_word(value)>on12_signed_word(other)?0x531f0:on12_signed_word(value)<on12_signed_word(other)?0x53248:0x531dc;
        return true;
    case 0x531e8:if(!on12_get(c,0x7c,4,value))return false;return on12_install(c,value,0x52f9c); // MOVE.L 7c(A6),(A6); BRA.W 52f9c.
    // TST.B 9f(A6); BNE.W 5320c / 53264.
    case 0x531f0:case 0x53248:
        if(!on12_nonzero(c,0x9f,flag))return false;r.pc=r.pc==0x531f0?(flag?0x5320c:0x531f8):(flag?0x53264:0x53250);return true;
    case 0x531f8:return on12_animation(c,0x551ea,0x140,0x53208);
    case 0x5320c:return on12_animation(c,0x551ea,0x200,0x5321c);
    case 0x53250:return on12_animation(c,0x54ed8,0x140,0x53260);
    case 0x53264:return on12_animation(c,0x54ed8,0x1c0,0x53274);
    case 0x53208:r.pc=0x5321c;return true;                                   // BRA.W 5321c.
    case 0x53260:r.pc=0x53274;return true;                                   // BRA.W 53274.
    case 0x5321c:return on12_install(c,0x53222,0x53222);
    case 0x53274:return on12_install(c,0x5327a,0x5327a);
    case 0x53232:return on12_carry(c,0x52f9c,0x53236);                        // BCC.W 52f9c (C returned by 49fc6).
    case 0x5328a:return on12_carry(c,0x52f9c,0x5328e);
    // SUBQ.W #1 / ADDQ.W #1,94(A6); BSR.W 52e4a.
    case 0x53236:case 0x5328e:
        if(!on12_get(c,0x94,2,value) || !on12_put(c,0x94,2,(r.pc==0x53236?value-1U:value+1U)&65535U))return false;
        return am_call(c,0x52e4a,r.pc==0x53236?0x5323e:0x53296);
    case 0x5323e:case 0x53296:return on12_install(c,0x531c2,0x52f9c);       // MOVE.L #531c2,(A6); BRA.W 52f9c.
    // ---- 539e4 (child tail): JSR 43e34 / 49fc6 (above); JSR 4a46c.L; RTS.
    case 0x539f0:return am_call(c,0x4a46c,0x539f6);
    case 0x53ac8:return am_call(c,0x4a46c,0x53ace);
    case 0x53c3a:return am_call(c,0x4a46c,0x53c40);
    case 0x53d0c:return am_call(c,0x4a46c,0x53d12);
    // ---- children 539f8 53b70 53c42 53d14 53e70 (28ae): head, sound, 4a496, look, animation.
    case 0x539f8:return on12_part_head(c,0x53a14);
    case 0x53b70:return on12_part_head(c,0x53b8c);
    case 0x53c42:return on12_part_head(c,0x53c5e);
    case 0x53d14:return on12_part_head(c,0x53d30);
    case 0x53e70:return on12_part_head(c,0x53e8c);
    case 0x53a2c:return on12_look(c,0x803,0x53a44);
    case 0x53ba4:return on12_look(c,0x804,0x53bbc);
    case 0x53c76:return on12_look(c,0x801,0x53c8e);
    case 0x53d3e:return on12_look(c,0x802,0x53d56);
    case 0x53ea4:return on12_look(c,0x805,0x53ebc);
    case 0x53a44:return on12_animation(c,0x54bc6,0x100,0x53a54);
    case 0x53bbc:return on12_animation(c,0x554fc,0x100,0x53bcc);
    case 0x53c8e:return on12_animation(c,0x55652,0x100,0x53c9e);
    case 0x53d56:return on12_animation(c,0x55732,0x100,0x53d66);
    case 0x53ebc:return on12_animation(c,0x54ccc,0x100,0x53ecc);
    // ---- 539f8 states: MOVEA.L c(A6),A0; ST.B 9a(A0); MOVE.L #53a62,(A6).
    case 0x53a54:
        if(!on12_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_write(c,am_index(r.a[0],0x9a),1,0xff))return false;
        return on12_install(c,0x53a62,0x53a62);
    // MOVEA.L c(A6),A0; MOVE.B 98(A0),D0; ANDI.B #1f,D0; MOVE.B D0,9c(A6); MOVEQ #0,D0; MOVE.B 9b(A0),D0; CMPI.B #ff,D0; BEQ.W 53a8a.
    case 0x53a62:
        if(!on12_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x98),1,value))return false;
        am_byte(r.d[0],value&0x1fU);if(!on12_put(c,0x9c,1,r.d[0]&255U))return false;r.d[0]=0;
        if(!am_read(c,am_index(r.a[0],0x9b),1,value))return false;am_byte(r.d[0],value);r.pc=(value&255U)==0xffU?0x53a8a:0x53a80;return true;
    case 0x53a80:if(!am_write(c,am_index(r.a[0],0x9b),1,0xff))return false;r.pc=0x53a8e;return true; // MOVE.B #ff,9b(A0); BRA.W 53a8e.
    case 0x53a8a:case 0x53bf2:case 0x53cc4:r.pc=0x539e4;return true;       // BRA.W 539e4.
    // LEA 53b58(PC),A1; ADD.W D0,D0 (twice); MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x53a8e:
        r.a[1]=ON12_PART_LISTS;am_word(r.d[0],r.d[0]<<2);if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;
        am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x53aa4);
    // MOVEA.L c(A6),A0; CLR.B 9a(A0); MOVE.L #53ab2,(A6).
    case 0x53aa4:
        if(!on12_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_write(c,am_index(r.a[0],0x9a),1,0))return false;
        return on12_install(c,0x53ab2,0x53ab2);
    case 0x53abe:return on12_carry(c,0x53ac8,0x53ac2);                        // BCC.W 53ac8 (C returned by 49fc6).
    case 0x53ac2:return on12_install(c,0x53a44,0x53ac8);
    // ---- 53ad0 (interpreter command 31, A0 = arguments): MOVE.W (A0)+,D7/D0/D1; MOVE.W D0,-(A7); MOVE.W D1,-(A7); ADD.W D7,D7
    // (twice); MOVE.L 53b50(PC,D7.W),D7; MOVEA.L D7,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0x53ad0:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[7],value);
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[0],value);
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[1],value);
        if(!am_push(c,2,r.d[0]&65535U) || !am_push(c,2,r.d[1]&65535U))return false;am_word(r.d[7],r.d[7]<<2);
        if(!am_read(c,am_index(ON12_CHILD_CALLBACKS,r.d[7]),4,value))return false;r.d[7]=value;r.a[0]=value;am_word(r.d[0],0xa);
        return am_call(c,0x28ae,0x53aee);
    case 0x53aee:return on12_carry(c,0x53b2c,0x53af2);                        // BCC.W 53b2c (C returned by 28ae).
    case 0x53b3c:return on12_carry(c,0x53b4c,0x53b40);
    // ADDQ.B #1,a0(A6); MOVE.W (A7),D1; MOVE.W 2(A7),D0; JSR 49214.L (53b40: the same without ADDQ).
    case 0x53af2:case 0x53b40:
        if(r.pc==0x53af2 && (!on12_get(c,0xa0,1,value) || !on12_put(c,0xa0,1,(value+1U)&255U)))return false;
        if(!am_read(c,r.a[7],2,value) || !am_read(c,r.a[7]+2U,2,other))return false;am_word(r.d[1],value);am_word(r.d[0],other);
        return am_call(c,0x49214,r.pc==0x53af2?0x53b02:0x53b4c);
    // CLR.B a2(A0); TST.B a1(A6); BNE.W 53b28.
    case 0x53b02:if(!am_write(c,am_index(r.a[0],0xa2),1,0) || !on12_nonzero(c,0xa1,flag))return false;r.pc=flag?0x53b28:0x53b0e;return true;
    // MOVE.B #ff,a2(A0); LEA 55a38.L,A0; JSR 490ba.L.
    case 0x53b0e:if(!am_write(c,am_index(r.a[0],0xa2),1,0xff))return false;r.a[0]=0x55a38;return am_call(c,0x490ba,0x53b20);
    case 0x53b20:if(!on12_put(c,0xa1,1,r.d[0]&255U))return false;r.pc=0x53b2c;return true; // MOVE.B D0,a1(A6); BRA.W 53b2c.
    case 0x53b28:if(!on12_get(c,0xa1,1,value) || !on12_put(c,0xa1,1,(value-1U)&255U))return false;r.pc=0x53b2c;return true;
    // MOVEA.L #54082,A0; MOVE.W #1e,D0; JSR 28ae.L.
    case 0x53b2c:r.a[0]=0x54082;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0x53b3c);
    case 0x53b4c:r.a[7]+=4U;return am_return(c);                            // ADDQ.W #4,A7; RTS.
    // ---- 53b70 / 53c42 states: MOVE.L #state,(A6); CMPI.B #1/#2,9e(A6); MOVE.L #anim state,(A6).
    case 0x53bcc:return on12_install(c,0x53bd2,0x53bd2);
    case 0x53c9e:return on12_install(c,0x53ca4,0x53ca4);
    case 0x53bd2:if(!on12_state(c,1,flag))return false;r.pc=flag?0x53bdc:0x53be2;return true;
    case 0x53ca4:if(!on12_state(c,1,flag))return false;r.pc=flag?0x53cae:0x53cb4;return true;
    case 0x53bdc:return on12_install(c,0x53bf6,0x53be2);
    case 0x53cae:return on12_install(c,0x53cc8,0x53cb4);
    case 0x53be2:if(!on12_state(c,2,flag))return false;r.pc=flag?0x53bec:0x53bf2;return true;
    case 0x53cb4:if(!on12_state(c,2,flag))return false;r.pc=flag?0x53cbe:0x53cc4;return true;
    case 0x53bec:return on12_install(c,0x53c0a,0x53bf2);
    case 0x53cbe:return on12_install(c,0x53cdc,0x53cc4);
    case 0x53bf6:return on12_animation(c,0x55506,0x100,0x53c06);
    case 0x53c0a:return on12_animation(c,0x555ac,0x100,0x53c1a);
    case 0x53cc8:return on12_animation(c,0x55662,0x100,0x53cd8);
    case 0x53cdc:return on12_animation(c,0x556d2,0x100,0x53cec);
    case 0x53c06:r.pc=0x53c1a;return true;                                   // BRA.W 53c1a.
    case 0x53cd8:r.pc=0x53cec;return true;                                   // BRA.W 53cec.
    case 0x53c1a:return on12_install(c,0x53c20,0x53c20);
    case 0x53cec:return on12_install(c,0x53cf2,0x53cf2);
    case 0x53c2c:return on12_carry(c,0x53c3a,0x53c30);                        // BCC (C returned by 49fc6).
    case 0x53cfe:return on12_carry(c,0x53d0c,0x53d02);
    // CLR.B 9e(A6); MOVE.L #53bcc / #53c9e,(A6).
    case 0x53c30:if(!on12_put(c,0x9e,1,0))return false;return on12_install(c,0x53bcc,0x53c3a);
    case 0x53d02:if(!on12_put(c,0x9e,1,0))return false;return on12_install(c,0x53c9e,0x53d0c);
    // ---- 53d14 states.
    case 0x53d66:return on12_install(c,0x53d6c,0x53d6c);
    case 0x53d6c:if(!on12_state(c,3,flag))return false;r.pc=flag?0x53d76:0x53d7c;return true;
    case 0x53d76:return on12_install(c,0x53dec,0x53d7c);
    case 0x53d7c:if(!on12_state(c,4,flag))return false;r.pc=flag?0x53d86:0x53d8c;return true;
    case 0x53d86:return on12_install(c,0x53e2e,0x53d8c);
    case 0x53d8c:if(!on12_state(c,5,flag))return false;r.pc=flag?0x53d96:0x53d9c;return true;
    case 0x53d96:return on12_install(c,0x53dba,0x53d9c);
    case 0x53d9c:if(!on12_state(c,6,flag))return false;r.pc=flag?0x53da6:0x53dac;return true;
    case 0x53da6:return on12_install(c,0x53dd8,0x53dac);
    case 0x53dba:am_word(r.d[0],0x188d);return am_call(c,0x3af8,0x53dc4);  // MOVE.W #188d,D0; JSR 3af8.L.
    case 0x53dc4:return on12_animation(c,0x557c6,0x100,0x53dd4);
    case 0x53dd8:return on12_animation(c,0x55854,0x100,0x53de8);
    case 0x53dec:return on12_animation(c,0x5573c,0x100,0x53dfc);
    case 0x53e2e:return on12_animation(c,0x558e2,0x100,0x53e3e);
    case 0x53dd4:case 0x53de8:r.pc=0x53dfc;return true;                     // BRA.W 53dfc.
    case 0x53dfc:return on12_install(c,0x53e02,0x53e02);
    case 0x53e3e:return on12_install(c,0x53e44,0x53e44);
    case 0x53e0e:return on12_carry(c,0x53e2c,0x53e12);                        // BCC (C returned by 49fc6).
    case 0x53e50:return on12_carry(c,0x53e6e,0x53e54);
    // CLR.B 9e(A6); MOVE.L #53d66,(A6); MOVEA.L #55798 / #55732,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x53e12:case 0x53e54:
        if(!on12_put(c,0x9e,1,0) || !am_write(c,r.a[6],4,0x53d66))return false;
        return on12_animation(c,r.pc==0x53e12?0x55798U:0x55732U,0x100,r.pc==0x53e12?0x53e2c:0x53e6e);
    // ---- 53e70 state: MOVE.L #53ed2,(A6); MOVEA.L c(A6),A0; MOVE.B 9c(A0),9c(A6); BRA.W 539e4.
    case 0x53ecc:return on12_install(c,0x53ed2,0x53ed2);
    case 0x53ed2:
        if(!on12_get(c,0xc,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x9c),1,value) || !on12_put(c,0x9c,1,value))return false;
        r.pc=0x539e4;return true;
    default:return am_error(c,"unsupported animation objects n12 PC");
    }
}
}
