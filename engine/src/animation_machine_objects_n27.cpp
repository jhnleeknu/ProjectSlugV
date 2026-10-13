#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONG (live bus, current PVC bank): the animation record base (id 18b) stored in LONG 22(A6).
const std::uint32_t ON27_BANK_18B=0x200194;
// Fixed ROM WORD tables (live bus; main decision 4).
const std::uint32_t ON27_TABLE_5FFD8=0x5ffd8;
const std::uint32_t ON27_TABLE_5FFE0=0x5ffe0;
const std::uint32_t ON27_TABLE_5FFE8=0x5ffe8;
const std::uint32_t ON27_TABLE_5FFF8=0x5fff8;
const std::uint32_t ON27_TABLE_60316=0x60316;
const std::uint32_t ON27_TABLE_60416=0x60416;
const std::uint32_t ON27_TABLE_60506=0x60506;
// 28ae child of 6018e / 601b8 (data value; orphan chain outside every unit, main decision 2).
const std::uint32_t ON27_CHILD=0x60516;
// dcf56: LEA 10b1d6.l,A1; MOVE.L #fffe0000,8(A1).
const std::uint32_t ON27_DCF56_A1=0x10b1d6;
const std::uint32_t ON27_DCF56_VALUE=0xfffe0000U;
// BSR.W target inside the unit (the rescope's "boundary 5ff90", main decision 1).
const std::uint32_t ON27_STEP=0x5ff90;
std::uint32_t on27_b(std::uint32_t value) {return value&255U;}
std::uint32_t on27_w(std::uint32_t value) {return value&65535U;}
bool on27_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on27_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// MOVEA.L c(A6),A0 (the parent node).
bool on27_parent(AnimationMachineContext& c) {std::uint32_t value=0;if(!on27_get(c,0xc,4,value))return false;c.s.a[0]=value;return true;}
// MOVEA.L c(A6),A0; BYTE/LONG d(A0) into value.
bool on27_parent_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return on27_parent(c) && am_read(c,am_index(c.s.a[0],displacement),size,value);
}
// BSET.B #6,15(A6); MOVE.W #id,68(A6); MOVE.W #id,1e(A6); JSR 16ef0.l (BSET reads, then writes).
bool on27_ident(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    std::uint32_t value=0;
    if(!on27_get(c,0x15,1,value) || !on27_put(c,0x15,1,on27_b(value|0x40U)) || !on27_put(c,0x68,2,id) || !on27_put(c,0x1e,2,id))return false;
    return am_call(c,0x16ef0,return_pc);
}
// MOVE.W #id,D0; MOVE.B #0,D1; JSR 8ebe.l.
bool on27_8ebe(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #id,D0; JSR target.l (3af8 / 3c44 / 4a496).
bool on27_id_call(AnimationMachineContext& c,std::uint32_t id,std::uint32_t target,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);return am_call(c,target,return_pc);
}
// MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l.
bool on27_anim(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!on27_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],displacement),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// LEA 26(A6),A0; MOVE.W #18b,20(A6); MOVE.L 200194.l,22(A6); then the animation LONG d(LONG 22).
bool on27_bank_anim(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=am_index(c.s.a[6],0x26);
    if(!on27_put(c,0x20,2,0x18b) || !am_read(c,ON27_BANK_18B,4,value) || !on27_put(c,0x22,4,value))return false;
    return on27_anim(c,displacement,return_pc);
}
// LSL.W #2,D0; MOVEA.L 22(A6),A1; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; LEA 26(A6),A0; JSR 49f8c.l.
bool on27_indexed_anim(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;am_word(r.d[0],(r.d[0]<<2)&65535U);
    if(!on27_get(c,0x22,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L c(A6),A0; MOVE.B 76(A0),D0; CMP.B 76(A6),D0; BEQ.W equal_pc.
bool on27_follow(AnimationMachineContext& c,std::uint32_t equal_pc,std::uint32_t changed_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on27_parent_get(c,0x76,1,value))return false;
    am_byte(r.d[0],value);if(!on27_get(c,0x76,1,value))return false;r.pc=on27_b(r.d[0])==on27_b(value)?equal_pc:changed_pc;return true;
}
// LEA table(PC),A0; MOVEQ #0,D0; MOVE.B 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; CLR.B 79(A6); CMPI.W #ffff,D0; BEQ.W done.
bool on27_table(AnimationMachineContext& c,std::uint32_t table,std::uint32_t done_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=table;r.d[0]=0;if(!on27_get(c,0x76,1,value))return false;am_byte(r.d[0],value);
    am_word(r.d[0],(r.d[0]*2U)&65535U);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
    if(!on27_put(c,0x79,1,0))return false;r.pc=on27_w(r.d[0])==0xffffU?done_pc:next_pc;return true;
}
// MOVE.B D0,76(A6) (the followed parent BYTE 76), then [TST.B 78(A6) (60096; flags unused);] the table selection.
bool on27_follow_table(AnimationMachineContext& c,bool test78,std::uint32_t table,std::uint32_t done_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!on27_put(c,0x76,1,on27_b(c.s.d[0])))return false;
    if(test78 && !on27_get(c,0x78,1,value))return false;return on27_table(c,table,done_pc,next_pc);
}
// ST.B 79(A6); then the indexed animation.
bool on27_table_anim(AnimationMachineContext& c,std::uint32_t return_pc) {
    if(!on27_put(c,0x79,1,0xff))return false;return on27_indexed_anim(c,return_pc);
}
// MOVEQ #0,D0; MOVE.B 77(A6),D0; ADD.B D0,D0 (BYTE add: index = 2 * BYTE 77 mod 100); MOVE.W (A0,D0.W),D0; BNE.W nonzero_pc.
bool on27_step(AnimationMachineContext& c,std::uint32_t nonzero_pc,std::uint32_t zero_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[0]=0;if(!on27_get(c,0x77,1,value))return false;am_byte(r.d[0],value);
    am_byte(r.d[0],(r.d[0]*2U)&255U);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
    r.pc=on27_w(r.d[0])!=0U?nonzero_pc:zero_pc;return true;
}
// TST.B / CMPI.B #want,d(A6); Bcc.
bool on27_byte_is(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t want,std::uint32_t equal_pc,std::uint32_t not_pc) {
    std::uint32_t value=0;if(!on27_get(c,displacement,1,value))return false;c.s.pc=on27_b(value)==want?equal_pc:not_pc;return true;
}
// MOVEA.L c(A6),A0; CMPI.B #want,77(A0); BNE.W not_pc.
bool on27_parent77_is(AnimationMachineContext& c,std::uint32_t want,std::uint32_t equal_pc,std::uint32_t not_pc) {
    std::uint32_t value=0;if(!on27_parent_get(c,0x77,1,value))return false;c.s.pc=on27_b(value)==want?equal_pc:not_pc;return true;
}
// CLR.B 62(A6); MOVE.B #stage,77(A6); BSR.W 5ff90.
bool on27_advance(AnimationMachineContext& c,std::uint32_t stage,std::uint32_t return_pc) {
    if(!on27_put(c,0x62,1,0) || !on27_put(c,0x77,1,stage))return false;return am_call(c,ON27_STEP,return_pc);
}
// SUBQ.W #1,d(A6) (read, then write); borrow = old WORD 0 (the C read by BCC).
bool on27_dec(AnimationMachineContext& c,std::uint32_t displacement,bool& borrow) {
    std::uint32_t value=0;if(!on27_get(c,displacement,2,value))return false;borrow=on27_w(value)==0U;
    return on27_put(c,displacement,2,(value-1U)&65535U);
}
// MOVEA.L #60516,A0; MOVE.W #a,D0; JSR 28ae.l.
bool on27_spawn(AnimationMachineContext& c,std::uint32_t return_pc) {
    c.s.a[0]=ON27_CHILD;am_word(c.s.d[0],0xa);return am_call(c,0x28ae,return_pc);
}
// MOVE.W #x,D0; MOVE.W #y,D1; JSR 4970a.l.
bool on27_place(AnimationMachineContext& c,std::uint32_t x,std::uint32_t y,std::uint32_t return_pc) {
    am_word(c.s.d[0],x);am_word(c.s.d[1],y);return am_call(c,0x4970a,return_pc);
}
// MOVE.B #4,77(A6); MOVE.W #1e,7e(A6); MOVE.W #1aca,D0; JSR 3c44.l.
bool on27_stage4(AnimationMachineContext& c,std::uint32_t return_pc) {
    if(!on27_put(c,0x77,1,4) || !on27_put(c,0x7e,2,0x1e))return false;return on27_id_call(c,0x1aca,0x3c44,return_pc);
}
// BCC.W after a callee that returns its C (Unknown C -> checked error, state preserved).
bool on27_bcc(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n27 caller requires known carry");
    r.pc=r.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
}
// Objects F4 N27 (162 block starts): the N24 28ae children 5fd24 / 5fd36, 60008, 6031e and 6041e (banked LONG 200194) with their
// installed callbacks 5fd9a (WORD tables 5ffd8 / 5ffe0, BYTE 77 = 0..6 stage machine against the parent BYTE 77 / LONG 3a, BSR 5ff90
// step tables 5ffe8 / 5fff8, 49fc6 C -> BYTE 62), 60086 (WORD table 60316, parent BYTE 63 with BYTE 76 = 3, BYTE 77 = 0..4 stages,
// 49a58 random, 28ae children 60516 placed by 4970a, 82 / 80 / 7e counters), 60396 (WORD table 60416) and 6048c (WORD table 60506), and
// the node callback dcf56 (LONG 10b1de = fffe0000, JMP 2a00). The parent BYTE 63 installs the N25 shared callback 5e8b0. No boundary
// callee. C consumers: 5ff7e (BCC after JSR 49fc6) and 6019e 601c8 (BCC after JSR 28ae); 601b0 601da (ORI.B #1,CCR) set a known C
// nothing consumes. No port, no bank change, no X, no register-indirect control transfer.
bool animation_objects_n27_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool borrow=false;
    switch(r.pc) {
    // ---- 28ae children 5fd24 / 5fd36: MOVE.B #0/#1,78(A6); MOVE.W #0,D0; MOVE.W #0,D1.
    case 0x5fd24:case 0x5fd36:if(!on27_put(c,0x78,1,r.pc==0x5fd24?0U:1U))return false;am_word(r.d[0],0);am_word(r.d[1],0);r.pc=0x5fd44;return true;
    case 0x5fd44:return am_call(c,0x49290,0x5fd4a);                           // JSR 49290.l.
    case 0x5fd4a:case 0x6001c:case 0x60332:case 0x60432:return am_call(c,0x491c4,r.pc+6U); // JSR 491c4.l.
    case 0x5fd50:if(!on27_put(c,0x76,1,0xff))return false;return on27_8ebe(c,0xd5d,0x5fd64); // MOVE.B #ff,76(A6); 8ebe d5d.
    case 0x5fd64:case 0x60346:return on27_id_call(c,0xd56,0x4a496,r.pc+0xaU); // MOVE.W #d56,D0; JSR 4a496.l.
    case 0x5fd6e:return on27_ident(c,0x804,0x5fd86);
    // MOVE.W #18b,20(A6); MOVE.L 200194.l,22(A6); MOVE.L #5fd9a,(A6) (fall-through).
    case 0x5fd86:
        if(!on27_put(c,0x20,2,0x18b) || !am_read(c,ON27_BANK_18B,4,value) || !on27_put(c,0x22,4,value) || !am_write(c,r.a[6],4,0x5fd9a))return false;
        r.pc=0x5fd9a;return true;
    // ---- 5fd9a (installed): follow the parent BYTE 76; tables 5ffd8 / 5ffe0 by BYTE 78.
    case 0x5fd9a:return on27_follow(c,0x5fe2a,0x5fdaa);
    case 0x5fdaa:if(!on27_put(c,0x76,1,on27_b(r.d[0])))return false;return on27_byte_is(c,0x78,0,0x5fdb6,0x5fdf2);
    case 0x5fdb6:return on27_table(c,ON27_TABLE_5FFD8,0x5fdee,0x5fdd2);
    case 0x5fdd2:return on27_table_anim(c,0x5fdee);
    case 0x5fdee:r.pc=0x5fe2a;return true;                                    // BRA.W 5fe2a.
    case 0x5fdf2:return on27_table(c,ON27_TABLE_5FFE0,0x5fe2a,0x5fe0e);
    case 0x5fe0e:return on27_table_anim(c,0x5fe2a);
    // MOVEA.L c(A6),A0; TST.B 63(A0); BEQ.W.
    case 0x5fe2a:if(!on27_parent_get(c,0x63,1,value))return false;r.pc=on27_b(value)==0U?0x5fe40:0x5fe36;return true;
    case 0x600e2:if(!on27_parent_get(c,0x63,1,value))return false;r.pc=on27_b(value)==0U?0x60134:0x600ee;return true;
    case 0x603e2:if(!on27_parent_get(c,0x63,1,value))return false;r.pc=on27_b(value)==0U?0x603f8:0x603ee;return true;
    case 0x604d8:if(!on27_parent_get(c,0x63,1,value))return false;r.pc=on27_b(value)==0U?0x604ee:0x604e4;return true;
    // CLR.B 79(A6); MOVE.L #5e8b0,(A6) (fall-through).
    case 0x5fe36:case 0x603ee:case 0x604e4:if(!on27_put(c,0x79,1,0) || !am_write(c,r.a[6],4,0x5e8b0))return false;r.pc=r.pc+0xaU;return true;
    case 0x5fe40:case 0x600dc:case 0x603f8:case 0x604ee:return am_call(c,0x43e34,r.pc+6U); // JSR 43e34.l.
    // TST.B 79(A6); BNE.W.
    case 0x5fe46:return on27_byte_is(c,0x79,0,0x5fe4e,0x5fe50);
    case 0x60134:return on27_byte_is(c,0x79,0,0x6013c,0x6013e);
    case 0x603fe:return on27_byte_is(c,0x79,0,0x60406,0x60408);
    case 0x604f4:return on27_byte_is(c,0x79,0,0x604fc,0x604fe);
    case 0x5fe4e:case 0x5ff8e:case 0x5ffd6:case 0x6013c:case 0x60314:case 0x60406:case 0x60414:case 0x604fc:case 0x60504:return am_return(c); // RTS.
    // ---- Stage machine by BYTE 77 (one stage per run).
    case 0x5fe50:return on27_byte_is(c,0x77,0,0x5fe5a,0x5fe7a);
    case 0x5fe5a:return on27_parent77_is(c,2,0x5fe68,0x5fe76);
    case 0x5fe68:return on27_advance(c,1,0x5fe76);
    case 0x5fe76:case 0x5feb2:case 0x5fedc:case 0x5ff06:case 0x5ff2a:case 0x5ff4e:case 0x5ff6e:r.pc=0x5ff72;return true; // BRA.W 5ff72.
    case 0x5fe7a:return on27_byte_is(c,0x77,1,0x5fe84,0x5feb6);
    case 0x5fe84:return on27_parent77_is(c,3,0x5fe92,0x5feb2);
    // CLR.B 62(A6); TST.L 3a(A0); BMI.W 5fea8 (bit 31).
    case 0x5fe92:
        if(!on27_put(c,0x62,1,0) || !am_read(c,am_index(r.a[0],0x3a),4,value))return false;r.pc=(value&0x80000000U)!=0U?0x5fea8:0x5fe9e;return true;
    case 0x5fe9e:if(!on27_put(c,0x77,1,2))return false;r.pc=0x5feae;return true; // MOVE.B #2,77(A6); BRA.W 5feae.
    case 0x5fea8:if(!on27_put(c,0x77,1,4))return false;r.pc=0x5feae;return true; // MOVE.B #4,77(A6).
    case 0x5feae:return am_call(c,ON27_STEP,0x5feb2);                         // BSR.W 5ff90.
    case 0x5feb6:return on27_byte_is(c,0x77,2,0x5fec0,0x5fee0);
    case 0x5fec0:return on27_parent77_is(c,4,0x5fece,0x5fedc);
    case 0x5fece:return on27_advance(c,3,0x5fedc);
    case 0x5fee0:return on27_byte_is(c,0x77,4,0x5feea,0x5ff0a);
    case 0x5feea:return on27_parent77_is(c,4,0x5fef8,0x5ff06);
    case 0x5fef8:return on27_advance(c,5,0x5ff06);
    case 0x5ff0a:return on27_byte_is(c,0x77,3,0x5ff14,0x5ff2e);
    case 0x5ff14:return on27_byte_is(c,0x62,0,0x5ff2a,0x5ff1c);
    case 0x5ff1c:return on27_advance(c,6,0x5ff2a);
    case 0x5ff2e:return on27_byte_is(c,0x77,5,0x5ff38,0x5ff52);
    case 0x5ff38:return on27_byte_is(c,0x62,0,0x5ff4e,0x5ff40);
    case 0x5ff40:return on27_advance(c,6,0x5ff4e);
    case 0x5ff52:return on27_byte_is(c,0x77,6,0x5ff5c,0x5ff72);
    case 0x5ff5c:return on27_byte_is(c,0x62,0,0x5ff6e,0x5ff64);
    case 0x5ff64:if(!on27_put(c,0x62,1,0) || !on27_put(c,0x77,1,0))return false;r.pc=0x5ff6e;return true; // CLR.B 62; MOVE.B #0,77.
    case 0x5ff72:case 0x60308:case 0x60408:return am_call(c,0x4a46c,r.pc+6U); // JSR 4a46c.l.
    case 0x5ff78:case 0x6030e:case 0x6040e:case 0x604fe:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.l.
    case 0x5ff7e:return on27_bcc(c,0x5ff8e,0x5ff82);                          // BCC.W 5ff8e (C returned by 49fc6).
    case 0x5ff82:return on27_byte_is(c,0x62,0,0x5ff8a,0x5ff8e);
    case 0x5ff8a:if(!on27_put(c,0x62,1,0xff))return false;r.pc=0x5ff8e;return true; // ST.B 62(A6).
    // ---- BSR subroutine 5ff90: step tables 5ffe8 / 5fff8 by BYTE 78.
    case 0x5ff90:return on27_byte_is(c,0x78,0,0x5ff98,0x5ffa0);
    case 0x5ff98:r.a[0]=ON27_TABLE_5FFE8;r.pc=0x5ffa4;return true;            // LEA 5ffe8(PC),A0; BRA.W 5ffa4.
    case 0x5ffa0:r.a[0]=ON27_TABLE_5FFF8;r.pc=0x5ffa4;return true;            // LEA 5fff8(PC),A0.
    case 0x5ffa4:return on27_step(c,0x5ffbe,0x5ffb4);
    case 0x5ffb4:if(!on27_put(c,0x77,1,0) || !on27_put(c,0x79,1,0))return false;r.pc=0x5ffbe;return true; // MOVE.B #0,77(A6); CLR.B 79(A6).
    case 0x5ffbe:return on27_indexed_anim(c,0x5ffd6);
    // ---- 28ae child 60008: MOVE.B #ff,76(A6); MOVE.W #0,D0; MOVE.W #0,D1; JSR 49290.l.
    case 0x60008:if(!on27_put(c,0x76,1,0xff))return false;am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x49290,0x6001c);
    case 0x60022:return on27_8ebe(c,0xd5a,0x60030);
    case 0x60030:return on27_id_call(c,0xd63,0x4a496,0x6003a);                // MOVE.W #d63,D0; JSR 4a496.l.
    case 0x6003a:return on27_ident(c,0x802,0x60052);
    case 0x60052:if(!on27_put(c,0x82,2,2))return false;return on27_bank_anim(c,0x134,0x60080); // MOVE.W #2,82(A6); banked animation 134.
    case 0x60080:if(!am_write(c,r.a[6],4,0x60086))return false;r.pc=0x60086;return true; // MOVE.L #60086,(A6) (fall-through).
    // ---- 60086 (installed): follow the parent BYTE 76; table 60316.
    case 0x60086:return on27_follow(c,0x600dc,0x60096);
    case 0x60096:return on27_follow_table(c,true,ON27_TABLE_60316,0x600d6,0x600ba);
    case 0x600ba:return on27_table_anim(c,0x600d6);
    case 0x600d6:if(!on27_put(c,0x77,1,0))return false;r.pc=0x600dc;return true; // MOVE.B #0,77(A6).
    case 0x600ee:return on27_byte_is(c,0x76,3,0x600f8,0x6012a);               // CMPI.B #3,76(A6); BNE.W 6012a.
    case 0x600f8:if(!on27_put(c,0x79,1,0xff))return false;return am_call(c,0x8ff4,0x60102); // ST.B 79(A6); JSR 8ff4.l.
    case 0x60102:return on27_8ebe(c,0xd5b,0x60110);
    case 0x60110:return on27_anim(c,0x13c,0x60126);
    case 0x60126:r.pc=0x6012e;return true;                                    // BRA.W 6012e.
    case 0x6012a:if(!on27_put(c,0x79,1,0))return false;r.pc=0x6012e;return true; // CLR.B 79(A6).
    case 0x6012e:if(!am_write(c,r.a[6],4,0x5e8b0))return false;r.pc=0x60134;return true; // MOVE.L #5e8b0,(A6).
    // MOVE.B 77(A6),D0; BNE.W 6016a.
    case 0x6013e:if(!on27_get(c,0x77,1,value))return false;am_byte(r.d[0],value);r.pc=on27_b(r.d[0])!=0U?0x6016a:0x60146;return true;
    case 0x60146:return on27_parent77_is(c,1,0x60154,0x60166);
    // MOVE.B #1,77(A6); MOVE.W #4,7e(A6); MOVE.W #18,80(A6).
    case 0x60154:if(!on27_put(c,0x77,1,1) || !on27_put(c,0x7e,2,4) || !on27_put(c,0x80,2,0x18))return false;r.pc=0x60166;return true;
    case 0x60166:case 0x60242:case 0x60294:case 0x602e6:case 0x60304:r.pc=0x60308;return true; // BRA.W 60308.
    // CMPI.B #k,D0; BNE.W.
    case 0x6016a:r.pc=on27_b(r.d[0])==1U?0x60172:0x60246;return true;
    case 0x60246:r.pc=on27_b(r.d[0])==2U?0x6024e:0x60298;return true;
    case 0x60298:r.pc=on27_b(r.d[0])==3U?0x602a0:0x602ea;return true;
    case 0x602ea:r.pc=on27_b(r.d[0])==4U?0x602f2:0x60308;return true;
    // SUBQ.W #1,7e(A6); BCC.W (C = borrow).
    case 0x60172:if(!on27_dec(c,0x7e,borrow))return false;r.pc=borrow?0x6017a:0x60242;return true;
    case 0x6024e:if(!on27_dec(c,0x7e,borrow))return false;r.pc=borrow?0x60256:0x60294;return true;
    case 0x602a0:if(!on27_dec(c,0x7e,borrow))return false;r.pc=borrow?0x602a8:0x602e6;return true;
    case 0x602f2:if(!on27_dec(c,0x7e,borrow))return false;r.pc=borrow?0x602fa:0x60304;return true;
    case 0x6017a:if(!on27_put(c,0x7e,2,4))return false;return am_call(c,0x49a58,0x60186); // MOVE.W #4,7e(A6); JSR 49a58.l.
    case 0x60186:am_word(r.d[0],r.d[0]&1U);r.pc=on27_w(r.d[0])!=0U?0x601b8:0x6018e;return true; // ANDI.W #1,D0; BNE.W 601b8.
    case 0x6018e:case 0x601b8:return on27_spawn(c,r.pc+0x10U);
    // BCC.W after JSR 28ae (C returned by 28ae: Set = child created).
    case 0x6019e:return on27_bcc(c,0x601b4,0x601a2);
    case 0x601c8:return on27_bcc(c,0x601de,0x601cc);
    case 0x601a2:return on27_place(c,0xffe0,0x12,0x601b0);
    case 0x601cc:return on27_place(c,0xffe0,0x24,0x601da);
    case 0x601b0:case 0x601da:r.carry=AnimationCarrySet;r.pc=r.pc+4U;return true; // ORI.B #1,CCR.
    case 0x601b4:r.pc=0x601de;return true;                                    // BRA.W 601de.
    // SUBQ.W #1,82(A6); BCC.W 601f2.
    case 0x601de:if(!on27_dec(c,0x82,borrow))return false;r.pc=borrow?0x601e6:0x601f2;return true;
    // MOVE.W #1a,82(A6); MOVE.B #1,8f(A0).
    case 0x601e6:if(!on27_put(c,0x82,2,0x1a) || !am_write(c,am_index(r.a[0],0x8f),1,1))return false;r.pc=0x601f2;return true;
    // SUBQ.W #1,80(A6); BCC.W 60242.
    case 0x601f2:if(!on27_dec(c,0x80,borrow))return false;r.pc=borrow?0x601fa:0x60242;return true;
    case 0x601fa:return am_call(c,0x49a58,0x60200);                           // JSR 49a58.l.
    // ANDI.B #1,D0; ADDQ.B #2,D0; MOVE.B D0,77(A6); MOVE.W #78,7e(A6); MOVE.W #1aca,D0; JSR 3af8.l.
    case 0x60200:
        am_byte(r.d[0],(r.d[0]&1U)+2U);if(!on27_put(c,0x77,1,on27_b(r.d[0])) || !on27_put(c,0x7e,2,0x78))return false;
        return on27_id_call(c,0x1aca,0x3af8,0x6021a);
    case 0x6021a:return on27_bank_anim(c,0x138,0x60242);
    case 0x60256:return on27_stage4(c,0x6026c);
    case 0x6026c:return on27_bank_anim(c,0x134,0x60294);
    case 0x602a8:return on27_stage4(c,0x602be);
    case 0x602be:return on27_bank_anim(c,0x134,0x602e6);
    // MOVEA.L c(A6),A0; MOVE.B #1,62(A0).
    case 0x602fa:if(!on27_parent(c) || !am_write(c,am_index(r.a[0],0x62),1,1))return false;r.pc=0x60304;return true;
    // ---- 28ae child 6031e: MOVE.B #ff,76(A6); MOVE.W #ffe0,D0; MOVE.W #0,D1; JSR 49290.l.
    case 0x6031e:if(!on27_put(c,0x76,1,0xff))return false;am_word(r.d[0],0xffe0);am_word(r.d[1],0);return am_call(c,0x49290,0x60332);
    case 0x60338:return on27_8ebe(c,0xd4a,0x60346);
    case 0x60350:return on27_ident(c,0x802,0x60368);
    case 0x60368:return on27_bank_anim(c,0x11c,0x60390);
    case 0x60390:if(!am_write(c,r.a[6],4,0x60396))return false;r.pc=0x60396;return true; // MOVE.L #60396,(A6) (fall-through).
    // ---- 60396 (installed): follow the parent BYTE 76; table 60416.
    case 0x60396:return on27_follow(c,0x603e2,0x603a6);
    case 0x603a6:return on27_follow_table(c,false,ON27_TABLE_60416,0x603e2,0x603c6);
    case 0x603c6:return on27_table_anim(c,0x603e2);
    // ---- 28ae child 6041e: MOVE.B #ff,76(A6); MOVE.W #0,D0; MOVE.W #0,D1; JSR 49290.l.
    case 0x6041e:if(!on27_put(c,0x76,1,0xff))return false;am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x49290,0x60432);
    case 0x60438:return on27_8ebe(c,0xd4c,0x60446);
    case 0x60446:return on27_ident(c,0x802,0x6045e);
    case 0x6045e:return on27_bank_anim(c,0x18,0x60486);
    case 0x60486:if(!am_write(c,r.a[6],4,0x6048c))return false;r.pc=0x6048c;return true; // MOVE.L #6048c,(A6) (fall-through).
    // ---- 6048c (installed): follow the parent BYTE 76; table 60506.
    case 0x6048c:return on27_follow(c,0x604d8,0x6049c);
    case 0x6049c:return on27_follow_table(c,false,ON27_TABLE_60506,0x604d8,0x604bc);
    case 0x604bc:return on27_table_anim(c,0x604d8);
    // ---- dcf56 (node callback): LEA 10b1d6.l,A1; MOVE.L #fffe0000,8(A1); JMP 2a00.l.
    case 0xdcf56:r.a[1]=ON27_DCF56_A1;if(!am_write(c,am_index(r.a[1],8),4,ON27_DCF56_VALUE))return false;r.pc=0x2a00;return true;
    default:return am_error(c,"unsupported animation objects n27 PC");
    }
}
}
