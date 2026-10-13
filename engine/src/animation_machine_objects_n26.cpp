#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONG (live bus, current PVC bank): the animation record base (id 18b) stored in LONG 22(A6).
const std::uint32_t ON26_BANK_18B=0x200194;
// Fixed ROM WORD tables (live bus; main decision 4).
const std::uint32_t ON26_TABLE_5F4B0=0x5f4b0;
const std::uint32_t ON26_TABLE_5F4BC=0x5f4bc;
const std::uint32_t ON26_TABLE_5FB06=0x5fb06;
const std::uint32_t ON26_TABLE_5FD04=0x5fd04;
const std::uint32_t ON26_TABLE_5FD0C=0x5fd0c;
const std::uint32_t ON26_TABLE_5FD14=0x5fd14;
const std::uint32_t ON26_TABLE_5FD1C=0x5fd1c;
// 28ae child of 5f3b4 / 5f3da / 5f404 / 5f42a (data value; orphan chain outside every unit, main decision 2).
const std::uint32_t ON26_CHILD=0x5f504;
std::uint32_t on26_b(std::uint32_t value) {return value&255U;}
std::uint32_t on26_w(std::uint32_t value) {return value&65535U;}
// Signed comparisons (two's complement, compared through the flipped sign bit).
bool on26_lt_w(std::uint32_t a,std::uint32_t b) {return ((a&65535U)^0x8000U)<((b&65535U)^0x8000U);}
bool on26_lt_b(std::uint32_t a,std::uint32_t b) {return ((a&255U)^0x80U)<((b&255U)^0x80U);}
bool on26_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on26_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// MOVEA.L c(A6),A0 (the parent node).
bool on26_parent(AnimationMachineContext& c) {std::uint32_t value=0;if(!on26_get(c,0xc,4,value))return false;c.s.a[0]=value;return true;}
// MOVEA.L c(A6),A0; BYTE/WORD d(A0) into value.
bool on26_parent_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return on26_parent(c) && am_read(c,am_index(c.s.a[0],displacement),size,value);
}
// BSET.B #6,15(A6) (read, then write).
bool on26_bset15(AnimationMachineContext& c) {
    std::uint32_t value=0;return on26_get(c,0x15,1,value) && on26_put(c,0x15,1,on26_b(value|0x40U));
}
// BSET.B #6,15(A6); MOVE.W #id,68(A6); MOVE.W #id,1e(A6); JSR 16ef0.l.
bool on26_ident(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    if(!on26_bset15(c) || !on26_put(c,0x68,2,id) || !on26_put(c,0x1e,2,id))return false;return am_call(c,0x16ef0,return_pc);
}
// MOVE.W #id,D0; MOVE.B #0,D1; JSR 8ebe.l.
bool on26_8ebe(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #id,D0; JSR target.l (3af8 / 3c44 / 4a496).
bool on26_id_call(AnimationMachineContext& c,std::uint32_t id,std::uint32_t target,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);return am_call(c,target,return_pc);
}
// MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l.
bool on26_anim(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!on26_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],displacement),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// LEA 26(A6),A0; MOVE.W #18b,20(A6); MOVE.L 200194.l,22(A6); then the animation LONG d(LONG 22).
bool on26_bank_anim(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=am_index(c.s.a[6],0x26);
    if(!on26_put(c,0x20,2,0x18b) || !am_read(c,ON26_BANK_18B,4,value) || !on26_put(c,0x22,4,value))return false;
    return on26_anim(c,displacement,return_pc);
}
// LSL.W #2,D0; MOVEA.L 22(A6),A1; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; LEA 26(A6),A0; JSR 49f8c.l.
bool on26_indexed_anim(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;am_word(r.d[0],(r.d[0]<<2)&65535U);
    if(!on26_get(c,0x22,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L c(A6),A0; MOVE.B 76(A0),D0; CMP.B 76(A6),D0; BEQ.W equal_pc.
bool on26_follow(AnimationMachineContext& c,std::uint32_t equal_pc,std::uint32_t changed_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on26_parent_get(c,0x76,1,value))return false;
    am_byte(r.d[0],value);if(!on26_get(c,0x76,1,value))return false;r.pc=on26_b(r.d[0])==on26_b(value)?equal_pc:changed_pc;return true;
}
// LEA table(PC),A0; MOVEQ #0,D0; MOVE.B 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; CLR.B 79(A6); CMPI.W #ffff,D0; BEQ.W done.
bool on26_table(AnimationMachineContext& c,std::uint32_t table,std::uint32_t done_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=table;r.d[0]=0;if(!on26_get(c,0x76,1,value))return false;am_byte(r.d[0],value);
    am_word(r.d[0],(r.d[0]*2U)&65535U);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
    if(!on26_put(c,0x79,1,0))return false;r.pc=on26_w(r.d[0])==0xffffU?done_pc:next_pc;return true;
}
// ST.B 79(A6); then the indexed animation.
bool on26_table_anim(AnimationMachineContext& c,std::uint32_t return_pc) {
    if(!on26_put(c,0x79,1,0xff))return false;return on26_indexed_anim(c,return_pc);
}
// MOVEQ #0,D0; MOVE.B 77(A6),D0; ADD.B D0,D0 (BYTE add: index = 2 * BYTE 77 mod 100); MOVE.W (A0,D0.W),D0; BNE.W nonzero_pc.
bool on26_step(AnimationMachineContext& c,std::uint32_t nonzero_pc,std::uint32_t zero_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[0]=0;if(!on26_get(c,0x77,1,value))return false;am_byte(r.d[0],value);
    am_byte(r.d[0],(r.d[0]*2U)&255U);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
    r.pc=on26_w(r.d[0])!=0U?nonzero_pc:zero_pc;return true;
}
// TST.B / CMPI.B #want,d(A6); Bcc.
bool on26_byte_is(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t want,std::uint32_t equal_pc,std::uint32_t not_pc) {
    std::uint32_t value=0;if(!on26_get(c,displacement,1,value))return false;c.s.pc=on26_b(value)==want?equal_pc:not_pc;return true;
}
// ADDQ.B #1,77(A6) (read, then write).
bool on26_inc77(AnimationMachineContext& c) {
    std::uint32_t value=0;return on26_get(c,0x77,1,value) && on26_put(c,0x77,1,on26_b(value+1U));
}
// SUBQ.W #1,d(A6) (read, then write); borrow = old WORD 0, zero = result 0.
bool on26_dec(AnimationMachineContext& c,std::uint32_t displacement,bool& borrow,bool& zero) {
    std::uint32_t value=0;if(!on26_get(c,displacement,2,value))return false;borrow=on26_w(value)==0U;zero=on26_w(value)==1U;
    return on26_put(c,displacement,2,(value-1U)&65535U);
}
// MOVEA.L #5f504,A0; MOVE.W #a,D0; JSR 28ae.l.
bool on26_spawn(AnimationMachineContext& c,std::uint32_t return_pc) {
    c.s.a[0]=ON26_CHILD;am_word(c.s.d[0],0xa);return am_call(c,0x28ae,return_pc);
}
// MOVE.W #x,D0; MOVE.W #y,D1; JSR 4970a.l.
bool on26_place(AnimationMachineContext& c,std::uint32_t x,std::uint32_t y,std::uint32_t return_pc) {
    am_word(c.s.d[0],x);am_word(c.s.d[1],y);return am_call(c,0x4970a,return_pc);
}
// BCC.W after a callee that returns its C (Unknown C -> checked error, state preserved).
bool on26_bcc(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n26 caller requires known carry");
    r.pc=r.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
}
// Objects F4 N26 (168 block starts): the N24 28ae children 5f24a / 5f25c, 5f760 / 5f76c and 5fb0e / 5fb20 (banked LONG 200194)
// with their installed callbacks 5f2c4 (parent BYTE 76 = 1 / BYTE 77 = 2 firing state, WORD tables 5f4b0 / 5f4bc, 3af8 and the
// 28ae children 5f504 placed by 4970a), 5f7ec (WORD table 5fb06, BYTE 77 = 0..3 stages, LONG 72 -> 4ae4a) and 5fb84 (WORD tables
// 5fd04 / 5fd0c / 5fd14 / 5fd1c, parent WORD 46 against 180). The parent BYTE 63 installs the N25 shared callback 5e8b0. No boundary
// callee. C consumers: 5f394 5f876 5fcb4 (BCC after JSR 49fc6) and 5f3c4 5f3ea 5f414 5f43a (BCC after JSR 28ae); 5f3d6 5f3fc 5f426
// 5f44c (ORI.B #1,CCR) set a known C nothing consumes. No port, no bank change, no X, no register-indirect control transfer.
bool animation_objects_n26_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool borrow=false;bool zero=false;
    switch(r.pc) {
    // ---- 28ae children 5f24a / 5f25c and 5fb0e / 5fb20: MOVE.B #0/#1,78(A6); MOVE.W #0,D0; MOVE.W #0,D1.
    case 0x5f24a:case 0x5f25c:case 0x5fb0e:case 0x5fb20: {
        const bool first=r.pc==0x5f24a || r.pc==0x5fb0e;if(!on26_put(c,0x78,1,first?0U:1U))return false;
        am_word(r.d[0],0);am_word(r.d[1],0);r.pc=r.pc<0x5fb00U?0x5f26aU:0x5fb2eU;return true;
    }
    // ---- 28ae children 5f760 / 5f76c: MOVE.W #ffe0,D0; MOVE.W #a8/#0,D1.
    case 0x5f760:case 0x5f76c:am_word(r.d[0],0xffe0);am_word(r.d[1],r.pc==0x5f760?0xa8U:0U);r.pc=0x5f774;return true;
    case 0x5f26a:case 0x5f774:case 0x5fb2e:return am_call(c,0x49290,r.pc+6U);   // JSR 49290.l.
    case 0x5f270:case 0x5f77a:case 0x5fb34:return am_call(c,0x491c4,r.pc+6U);   // JSR 491c4.l.
    // MOVE.B #ff,76(A6); MOVE.W #id,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x5f276:if(!on26_put(c,0x76,1,0xff))return false;return on26_8ebe(c,0xd5e,0x5f28a);
    case 0x5f780:if(!on26_put(c,0x76,1,0xff))return false;return on26_8ebe(c,0xd4e,0x5f794);
    case 0x5fb3a:if(!on26_put(c,0x76,1,0xff))return false;return on26_8ebe(c,0xd4b,0x5fb4e);
    case 0x5f28a:return on26_id_call(c,0xd62,0x4a496,0x5f294);                 // MOVE.W #d62,D0; JSR 4a496.l.
    case 0x5fb4e:return on26_id_call(c,0xd56,0x4a496,0x5fb58);                 // MOVE.W #d56,D0; JSR 4a496.l.
    case 0x5f294:return on26_ident(c,0x804,0x5f2ac);
    case 0x5f794:return on26_ident(c,0x802,0x5f7ac);
    case 0x5fb58:return on26_ident(c,0x802,0x5fb70);
    // MOVE.W #18b,20(A6); MOVE.L 200194.l,22(A6); [CLR.B 62(A6);] MOVE.L #callback,(A6) (fall-through).
    case 0x5f2ac:case 0x5fb70: {
        const bool first=r.pc==0x5f2ac;const std::uint32_t callback=first?0x5f2c4U:0x5fb84U;
        if(!on26_put(c,0x20,2,0x18b) || !am_read(c,ON26_BANK_18B,4,value) || !on26_put(c,0x22,4,value))return false;
        if(first && !on26_put(c,0x62,1,0))return false;
        if(!am_write(c,r.a[6],4,callback))return false;r.pc=callback;return true;
    }
    // ---- 5f2c4 (installed): MOVEA.L c(A6),A0; MOVE.B 76(A0),D0; CMPI.B #1,D0; BNE.W 5f33a.
    case 0x5f2c4:if(!on26_parent_get(c,0x76,1,value))return false;am_byte(r.d[0],value);r.pc=on26_b(r.d[0])==1U?0x5f2d4:0x5f33a;return true;
    case 0x5f2d4:if(!am_read(c,am_index(r.a[0],0x77),1,value))return false;r.pc=on26_b(value)==2U?0x5f2de:0x5f332;return true; // CMPI.B #2,77(A0).
    case 0x5f2de:return on26_byte_is(c,0x62,0,0x5f2e6,0x5f32e);
    // ST.B 62(A6); ST.B 79(A6); MOVE.B #0,77(A6); MOVE.W #6,80(A6); MOVE.W #0,7e(A6); TST.B 78(A6); BNE.W 5f310.
    case 0x5f2e6:
        if(!on26_put(c,0x62,1,0xff) || !on26_put(c,0x79,1,0xff) || !on26_put(c,0x77,1,0) || !on26_put(c,0x80,2,6) || !on26_put(c,0x7e,2,0))return false;
        return on26_byte_is(c,0x78,0,0x5f308,0x5f310);
    case 0x5f308:r.a[0]=ON26_TABLE_5F4B0;r.pc=0x5f314;return true;            // LEA 5f4b0(PC),A0; BRA.W 5f314.
    case 0x5f310:r.a[0]=ON26_TABLE_5F4BC;r.pc=0x5f314;return true;            // LEA 5f4bc(PC),A0.
    // MOVE.W (A0),D0; then the indexed animation.
    case 0x5f314:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);return on26_indexed_anim(c,0x5f32e);
    case 0x5f32e:r.pc=0x5f336;return true;                                    // BRA.W 5f336.
    case 0x5f336:r.pc=0x5f33e;return true;                                    // BRA.W 5f33e.
    case 0x5f332:case 0x5f33a:if(!on26_put(c,0x79,1,0))return false;r.pc=r.pc+4U;return true; // CLR.B 79(A6).
    // MOVEA.L c(A6),A0; TST.B 63(A0); BEQ.W.
    case 0x5f33e:if(!on26_parent_get(c,0x63,1,value))return false;r.pc=on26_b(value)==0U?0x5f354:0x5f34a;return true;
    case 0x5f84a:if(!on26_parent_get(c,0x63,1,value))return false;r.pc=on26_b(value)==0U?0x5f860:0x5f856;return true;
    case 0x5fc14:if(!on26_parent_get(c,0x63,1,value))return false;r.pc=on26_b(value)==0U?0x5fc70:0x5fc20;return true;
    // CLR.B 79(A6); MOVE.L #5e8b0,(A6) (fall-through).
    case 0x5f34a:case 0x5f856:if(!on26_put(c,0x79,1,0) || !am_write(c,r.a[6],4,0x5e8b0))return false;r.pc=r.pc+0xaU;return true;
    case 0x5f354:case 0x5f860:case 0x5fc70:return am_call(c,0x43e34,r.pc+6U); // JSR 43e34.l.
    // TST.W 7e(A6); BEQ.W.
    case 0x5f35a:if(!on26_get(c,0x7e,2,value))return false;r.pc=on26_w(value)==0U?0x5f37e:0x5f362;return true;
    case 0x5fa0a:if(!on26_get(c,0x7e,2,value))return false;r.pc=on26_w(value)==0U?0x5fb04:0x5fa12;return true;
    // SUBQ.W #1,7e(A6); BNE.W.
    case 0x5f362:if(!on26_dec(c,0x7e,borrow,zero))return false;r.pc=zero?0x5f36a:0x5f37e;return true;
    case 0x5fa12:if(!on26_dec(c,0x7e,borrow,zero))return false;r.pc=zero?0x5fa1a:0x5fb04;return true;
    // MOVEA.L c(A6),A0; MOVE.B #1,62(A0); MOVE.B #0,77(A6); CLR.B 62(A6).
    case 0x5f36a:
        if(!on26_parent(c) || !am_write(c,am_index(r.a[0],0x62),1,1) || !on26_put(c,0x77,1,0) || !on26_put(c,0x62,1,0))return false;
        r.pc=0x5f37e;return true;
    case 0x5f37e:return on26_byte_is(c,0x79,0,0x5f386,0x5f388);
    case 0x5f866:return on26_byte_is(c,0x79,0,0x5f86e,0x5f870);
    case 0x5fc9e:return on26_byte_is(c,0x79,0,0x5fca6,0x5fca8);
    case 0x5f386:case 0x5f4ae:case 0x5f86e:case 0x5f9f8:case 0x5fa66:case 0x5fab4:case 0x5fb02:case 0x5fb04:case 0x5fc8c:case 0x5fc9c:
    case 0x5fca6:case 0x5fd02:return am_return(c); // RTS.
    case 0x5f388:case 0x5fca8:return am_call(c,0x4a46c,r.pc+6U);               // JSR 4a46c.l.
    case 0x5f38e:case 0x5f870:case 0x5fcae:return am_call(c,0x49fc6,r.pc+6U); // JSR 49fc6.l.
    case 0x5f394:return on26_bcc(c,0x5f4ae,0x5f398);                          // BCC.W 5f4ae (C returned by 49fc6).
    case 0x5f398:return on26_byte_is(c,0x77,2,0x5f3a2,0x5f460);
    case 0x5f3a2:return on26_id_call(c,0x1a9f,0x3af8,0x5f3ac);                // MOVE.W #1a9f,D0; JSR 3af8.l.
    case 0x5f3ac:return on26_byte_is(c,0x78,0,0x5f3b4,0x5f404);
    case 0x5f3b4:case 0x5f3da:case 0x5f404:case 0x5f42a:return on26_spawn(c,r.pc+0x10U);
    // BCC.W after JSR 28ae (C returned by 28ae: Set = child created).
    case 0x5f3c4:return on26_bcc(c,0x5f3da,0x5f3c8);
    case 0x5f3ea:return on26_bcc(c,0x5f400,0x5f3ee);
    case 0x5f414:return on26_bcc(c,0x5f42a,0x5f418);
    case 0x5f43a:return on26_bcc(c,0x5f450,0x5f43e);
    case 0x5f3c8:return on26_place(c,0xffc0,0xffea,0x5f3d6);
    case 0x5f3ee:return on26_place(c,0xffc0,0xffe0,0x5f3fc);
    case 0x5f418:return on26_place(c,0xffc0,0x30,0x5f426);
    case 0x5f43e:return on26_place(c,0xffc0,0x3a,0x5f44c);
    case 0x5f3d6:case 0x5f3fc:case 0x5f426:case 0x5f44c:r.carry=AnimationCarrySet;r.pc=r.pc+4U;return true; // ORI.B #1,CCR.
    case 0x5f400:r.pc=0x5f450;return true;                                    // BRA.W 5f450.
    // SUBQ.W #1,80(A6); BCC.W 5f45c (C = borrow).
    case 0x5f450:if(!on26_dec(c,0x80,borrow,zero))return false;r.pc=borrow?0x5f458:0x5f45c;return true;
    case 0x5f458:case 0x5f460:if(!on26_inc77(c))return false;r.pc=r.pc+4U;return true; // ADDQ.B #1,77(A6).
    case 0x5f45c:r.pc=0x5f464;return true;                                    // BRA.W 5f464.
    case 0x5f464:return on26_byte_is(c,0x78,0,0x5f46c,0x5f474);
    case 0x5f46c:r.a[0]=ON26_TABLE_5F4B0;r.pc=0x5f478;return true;            // LEA 5f4b0(PC),A0; BRA.W 5f478.
    case 0x5f474:r.a[0]=ON26_TABLE_5F4BC;r.pc=0x5f478;return true;            // LEA 5f4bc(PC),A0.
    case 0x5f478:return on26_step(c,0x5f496,0x5f488);
    // CLR.B 79(A6); MOVE.W #78,7e(A6); BRA.W 5f4ae.
    case 0x5f488:if(!on26_put(c,0x79,1,0) || !on26_put(c,0x7e,2,0x78))return false;r.pc=0x5f4ae;return true;
    case 0x5f496:return on26_indexed_anim(c,0x5f4ae);
    // MOVE.W #3c,7e(A6); MOVE.W #0,80(A6); MOVE.B #0,77(A6); then the banked animation LONG ec.
    case 0x5f7ac:if(!on26_put(c,0x7e,2,0x3c) || !on26_put(c,0x80,2,0) || !on26_put(c,0x77,1,0))return false;return on26_bank_anim(c,0xec,0x5f7e6);
    case 0x5f7e6:if(!am_write(c,r.a[6],4,0x5f7ec))return false;r.pc=0x5f7ec;return true; // MOVE.L #5f7ec,(A6) (fall-through).
    // ---- 5f7ec (installed): follow the parent BYTE 76; table 5fb06.
    case 0x5f7ec:return on26_follow(c,0x5f84a,0x5f7fc);
    case 0x5f7fc:if(!on26_put(c,0x76,1,on26_b(r.d[0])))return false;return on26_table(c,ON26_TABLE_5FB06,0x5f838,0x5f81c);
    case 0x5f81c:return on26_table_anim(c,0x5f838);
    // MOVE.W #3c,7e(A6); MOVE.W #0,80(A6); MOVE.B #0,77(A6).
    case 0x5f838:if(!on26_put(c,0x7e,2,0x3c) || !on26_put(c,0x80,2,0) || !on26_put(c,0x77,1,0))return false;r.pc=0x5f84a;return true;
    case 0x5f876:return on26_bcc(c,0x5f9ea,0x5f87a);                          // BCC.W 5f9ea (C returned by 49fc6).
    // Stages by BYTE 77 (0..3; unchanged in the chain, so at most one runs).
    case 0x5f87a:return on26_byte_is(c,0x77,0,0x5f884,0x5f8d0);
    case 0x5f884:return on26_id_call(c,0x1acb,0x3af8,0x5f88e);
    case 0x5f88e:case 0x5f8ee:if(!on26_put(c,0x7e,2,0x1e))return false;return am_call(c,0x8ff4,r.pc+0xcU); // MOVE.W #1e,7e(A6); JSR 8ff4.l.
    case 0x5f89a:case 0x5f8fa:case 0x5f9aa:case 0x5fa30:return on26_8ebe(c,0xd4e,r.pc+0xeU);
    case 0x5f8a8:return on26_bank_anim(c,0xf0,0x5f8d0);
    case 0x5f8d0:return on26_byte_is(c,0x77,1,0x5f8da,0x5f930);
    case 0x5f8da:return on26_id_call(c,0x1acb,0x3c44,0x5f8e4);
    case 0x5f8e4:return on26_id_call(c,0x1acc,0x3af8,0x5f8ee);
    case 0x5f908:return on26_bank_anim(c,0xf8,0x5f930);
    case 0x5f930:return on26_byte_is(c,0x77,2,0x5f93a,0x5f99a);
    case 0x5f93a:return on26_id_call(c,0x1acc,0x3c44,0x5f944);
    case 0x5f944:return on26_id_call(c,0x1acd,0x3af8,0x5f94e);
    case 0x5f94e:if(!on26_put(c,0x7e,2,0x78))return false;return am_call(c,0x8ff4,0x5f95a); // MOVE.W #78,7e(A6); JSR 8ff4.l.
    case 0x5f95a:return on26_8ebe(c,0xd53,0x5f968);
    case 0x5f968:return on26_bank_anim(c,0x100,0x5f990);
    // MOVEA.L c(A6),A0; MOVE.B #1,62(A0).
    case 0x5f990:case 0x5f9e0:if(!on26_parent(c) || !am_write(c,am_index(r.a[0],0x62),1,1))return false;r.pc=r.pc+0xaU;return true;
    case 0x5f99a:return on26_byte_is(c,0x77,3,0x5f9a4,0x5f9ea);
    case 0x5f9a4:return am_call(c,0x8ff4,0x5f9aa);                             // JSR 8ff4.l.
    case 0x5f9b8:return on26_bank_anim(c,0xec,0x5f9e0);
    // MOVEA.L c(A6),A0; CMPI.B #2,77(A0); BGE.W 5f9fa (signed BYTE).
    case 0x5f9ea:if(!on26_parent_get(c,0x77,1,value))return false;r.pc=on26_lt_b(value,2)?0x5f9f8:0x5f9fa;return true;
    // MOVE.L 72(A6),D0; BEQ.W 5fa0a.
    case 0x5f9fa:if(!on26_get(c,0x72,4,value))return false;r.d[0]=value;r.pc=value==0U?0x5fa0a:0x5fa02;return true;
    case 0x5fa02:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0x5fa0a);             // MOVEA.L D0,A0; JSR 4ae4a.l.
    case 0x5fa1a:return on26_byte_is(c,0x77,0,0x5fa24,0x5fa68);
    case 0x5fa68:return on26_byte_is(c,0x77,1,0x5fa72,0x5fab6);
    case 0x5fab6:return on26_byte_is(c,0x77,2,0x5fac0,0x5fb04);
    // MOVE.B #1/#2/#3,77(A6); JSR 8ff4.l.
    case 0x5fa24:case 0x5fa72:case 0x5fac0: {
        const std::uint32_t stage=r.pc==0x5fa24?1U:(r.pc==0x5fa72?2U:3U);
        if(!on26_put(c,0x77,1,stage))return false;return am_call(c,0x8ff4,r.pc+0xcU);
    }
    case 0x5fa3e:return on26_bank_anim(c,0xf4,0x5fa66);
    case 0x5fa7e:return on26_8ebe(c,0xd52,0x5fa8c);
    case 0x5fa8c:return on26_bank_anim(c,0xfc,0x5fab4);
    case 0x5facc:return on26_8ebe(c,0xd54,0x5fada);
    case 0x5fada:return on26_bank_anim(c,0x104,0x5fb02);
    // ---- 5fb84 (installed): follow the parent BYTE 76; tables 5fd04 / 5fd0c by BYTE 78.
    case 0x5fb84:return on26_follow(c,0x5fc14,0x5fb94);
    case 0x5fb94:if(!on26_put(c,0x76,1,on26_b(r.d[0])))return false;return on26_byte_is(c,0x78,0,0x5fba0,0x5fbdc);
    case 0x5fba0:return on26_table(c,ON26_TABLE_5FD04,0x5fbd8,0x5fbbc);
    case 0x5fbbc:return on26_table_anim(c,0x5fbd8);
    case 0x5fbd8:r.pc=0x5fc14;return true;                                    // BRA.W 5fc14.
    case 0x5fbdc:return on26_table(c,ON26_TABLE_5FD0C,0x5fc14,0x5fbf8);
    case 0x5fbf8:return on26_table_anim(c,0x5fc14);
    case 0x5fc20:return on26_byte_is(c,0x76,3,0x5fc2a,0x5fc66);               // CMPI.B #3,76(A6); BNE.W 5fc66.
    case 0x5fc2a:return on26_byte_is(c,0x78,0,0x5fc32,0x5fc4c);
    case 0x5fc32:return on26_anim(c,0x120,0x5fc48);
    case 0x5fc4c:return on26_anim(c,0x124,0x5fc62);
    case 0x5fc48:r.pc=0x5fc62;return true;                                    // BRA.W 5fc62.
    case 0x5fc62:r.pc=0x5fc6a;return true;                                    // BRA.W 5fc6a.
    case 0x5fc66:if(!on26_put(c,0x79,1,0))return false;r.pc=0x5fc6a;return true; // CLR.B 79(A6).
    case 0x5fc6a:if(!am_write(c,r.a[6],4,0x5e8b0))return false;r.pc=0x5fc70;return true; // MOVE.L #5e8b0,(A6).
    // MOVEA.L c(A6),A0; TST.B 78(A6); BNE.W 5fc92.
    case 0x5fc76:if(!on26_parent(c))return false;return on26_byte_is(c,0x78,0,0x5fc82,0x5fc92);
    // CMPI.W #180,46(A0); BLE.W 5fc8e / BGE.W 5fc9e (signed WORD).
    case 0x5fc82:if(!am_read(c,am_index(r.a[0],0x46),2,value))return false;r.pc=on26_lt_w(0x180,value)?0x5fc8c:0x5fc8e;return true;
    case 0x5fc92:if(!am_read(c,am_index(r.a[0],0x46),2,value))return false;r.pc=on26_lt_w(value,0x180)?0x5fc9c:0x5fc9e;return true;
    case 0x5fc8e:r.pc=0x5fc9e;return true;                                    // BRA.W 5fc9e.
    case 0x5fcb4:return on26_bcc(c,0x5fd02,0x5fcb8);                          // BCC.W 5fd02 (C returned by 49fc6).
    // ADDQ.B #1,77(A6); TST.B 78(A6); BNE.W 5fccc.
    case 0x5fcb8:if(!on26_inc77(c))return false;return on26_byte_is(c,0x78,0,0x5fcc4,0x5fccc);
    case 0x5fcc4:r.a[0]=ON26_TABLE_5FD14;r.pc=0x5fcd0;return true;            // LEA 5fd14(PC),A0; BRA.W 5fcd0.
    case 0x5fccc:r.a[0]=ON26_TABLE_5FD1C;r.pc=0x5fcd0;return true;            // LEA 5fd1c(PC),A0.
    case 0x5fcd0:return on26_step(c,0x5fcea,0x5fce0);
    case 0x5fce0:if(!on26_put(c,0x77,1,0) || !on26_put(c,0x79,1,0))return false;r.pc=0x5fcea;return true; // MOVE.B #0,77(A6); CLR.B 79(A6).
    case 0x5fcea:return on26_indexed_anim(c,0x5fd02);
    default:return am_error(c,"unsupported animation objects n26 PC");
    }
}
}
