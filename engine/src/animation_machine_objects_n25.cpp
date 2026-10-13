#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Banked LONG (live bus, current PVC bank): the animation record base (id 18b) stored in LONG 22(A6) by 5e912 / 5eb4a / 5f048.
const std::uint32_t ON25_BANK_18B=0x200194;
// Fixed ROM data tables (live bus; main decision 3): WORD tables indexed by 2 * BYTE 76(A6), WORD pair table indexed by 8 * WORD 8c(A6).
const std::uint32_t ON25_TABLE_5E940=0x5ea38;
const std::uint32_t ON25_PAIRS=0x5ea42;
const std::uint32_t ON25_TABLE_5F094_0=0x5f23a;
const std::uint32_t ON25_TABLE_5F094_1=0x5f242;
// 28ae child of 5ee20 / 5ee4e (data value, outside every unit; main decision 2).
const std::uint32_t ON25_CHILD=0x5eed2;
std::uint32_t on25_b(std::uint32_t value) {return value&255U;}
std::uint32_t on25_w(std::uint32_t value) {return value&65535U;}
// Signed WORD comparisons (two's complement, compared through the flipped sign bit).
bool on25_lt_w(std::uint32_t a,std::uint32_t b) {return ((a&65535U)^0x8000U)<((b&65535U)^0x8000U);}
bool on25_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on25_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// MOVEA.L c(A6),A0 (the parent node).
bool on25_parent(AnimationMachineContext& c) {std::uint32_t value=0;if(!on25_get(c,0xc,4,value))return false;c.s.a[0]=value;return true;}
// BSET.B #6,15(A6) (read, then write).
bool on25_bset15(AnimationMachineContext& c) {
    std::uint32_t value=0;return on25_get(c,0x15,1,value) && on25_put(c,0x15,1,on25_b(value|0x40U));
}
// MOVE.W #id,D0; MOVE.B #0,D1; JSR 8ebe.l.
bool on25_8ebe(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l.
bool on25_anim(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!on25_get(c,0x22,4,value))return false;r.a[1]=value;if(!am_read(c,am_index(r.a[1],displacement),4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L 22(A6),A1; MOVEA.L (A1,Dn.W),A1; MOVE.W #100,D0; LEA 26(A6),A0; JSR 49f8c.l (index = the low WORD of index_register).
bool on25_indexed_anim(AnimationMachineContext& c,std::uint32_t index_register,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on25_get(c,0x22,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],index_register),4,value))return false;r.a[1]=value;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    return am_call(c,0x49f8c,return_pc);
}
// MOVEA.L c(A6),A0; MOVE.B 76(A0),D0; CMP.B 76(A6),D0; BEQ.W equal_pc.
bool on25_follow(AnimationMachineContext& c,std::uint32_t equal_pc,std::uint32_t changed_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on25_parent(c) || !am_read(c,am_index(r.a[0],0x76),1,value))return false;
    am_byte(r.d[0],value);if(!on25_get(c,0x76,1,value))return false;r.pc=on25_b(r.d[0])==on25_b(value)?equal_pc:changed_pc;return true;
}
// LEA table(PC),A0; MOVEQ #0,D0; MOVE.B 76(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; CLR.B 79(A6); CMPI.W #ffff,D0; BEQ.W done.
bool on25_table(AnimationMachineContext& c,std::uint32_t table,std::uint32_t done_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=table;r.d[0]=0;if(!on25_get(c,0x76,1,value))return false;am_byte(r.d[0],value);
    am_word(r.d[0],(r.d[0]*2U)&65535U);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
    if(!on25_put(c,0x79,1,0))return false;r.pc=on25_w(r.d[0])==0xffffU?done_pc:next_pc;return true;
}
// ST.B 79(A6); LSL.W #2,D0; MOVEA.L 22(A6),A1; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; LEA 26(A6),A0; JSR 49f8c.l.
bool on25_table_anim(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;if(!on25_put(c,0x79,1,0xff))return false;am_word(r.d[0],(r.d[0]<<2)&65535U);
    return on25_indexed_anim(c,r.d[0],return_pc);
}
// TST.B d(A6) / CMPI.B #want,d(A6); Bcc.
bool on25_byte_is(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t want,std::uint32_t equal_pc,std::uint32_t not_pc) {
    std::uint32_t value=0;if(!on25_get(c,displacement,1,value))return false;c.s.pc=on25_b(value)==want?equal_pc:not_pc;return true;
}
// MOVE.B from(A6),14(A6).
bool on25_copy14(AnimationMachineContext& c,std::uint32_t from) {
    std::uint32_t value=0;return on25_get(c,from,1,value) && on25_put(c,0x14,1,on25_b(value));
}
// 5ec2c / 5ed30: ANDI.W #ff,D1; MOVE.W D1,8a(A6); LSR.W #3,D1; CMPI.W #f,D1; BGT.W high_pc.
bool on25_direction(AnimationMachineContext& c,std::uint32_t high_pc,std::uint32_t low_pc) {
    AnimationMachineState& r=c.s;am_word(r.d[1],r.d[1]&0xffU);if(!on25_put(c,0x8a,2,on25_w(r.d[1])))return false;
    am_word(r.d[1],on25_w(r.d[1])>>3);r.pc=on25_lt_w(0xf,r.d[1])?high_pc:low_pc;return true;
}
// SUBQ.W #7,D1 / SUBI.W #27,D1; NEG.W D1.
void on25_reflect(AnimationMachineState& r,std::uint32_t base) {am_word(r.d[1],(r.d[1]-base)&65535U);am_word(r.d[1],(0U-on25_w(r.d[1]))&65535U);}
// SUBQ.W #1,d(A6) (read, then write); returns the borrow (old WORD = 0) or the zero result through the out parameters.
bool on25_dec(AnimationMachineContext& c,std::uint32_t displacement,bool& borrow,bool& zero) {
    std::uint32_t value=0;if(!on25_get(c,displacement,2,value))return false;borrow=on25_w(value)==0U;zero=on25_w(value)==1U;
    return on25_put(c,displacement,2,(value-1U)&65535U);
}
// 5ee30 / 5ee5e: MOVE.W 8a(A6),8a(A0); LEA 5ea42(PC),A1; MOVE.W 8c(A6),D2; LSL.W #3,D2; MOVE.W o(A1,D2.W),D0; MOVE.W o+2(A1,D2.W),D1;
// JSR 4970a.l.
bool on25_pair(AnimationMachineContext& c,std::uint32_t offset,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on25_get(c,0x8a,2,value) || !am_write(c,am_index(r.a[0],0x8a),2,on25_w(value)))return false;
    r.a[1]=ON25_PAIRS;if(!on25_get(c,0x8c,2,value))return false;am_word(r.d[2],value);am_word(r.d[2],(r.d[2]<<3)&65535U);
    if(!am_read(c,am_index(r.a[1],r.d[2])+offset,2,value))return false;am_word(r.d[0],value);
    if(!am_read(c,am_index(r.a[1],r.d[2])+offset+2U,2,value))return false;am_word(r.d[1],value);
    return am_call(c,0x4970a,return_pc);
}
}
// Objects F4 N25 (168 block starts): the shared callback 5e8b0 (installed / branched to by N25..N27), the N24 28ae children 5e8c8,
// 5eac2 / 5ead4 and 5efe6 / 5eff8 (banked LONG 200194) with their installed callbacks 5e940, 5eb74 (BYTE 77 = 0..2 aiming state
// machine, 28ae children 5eed2) and 5f094. Boundaries without an executor: 4964e and 44602. The WORD tables 5ea38 / 5ea42 / 5f23a /
// 5f242 are read on the live bus. C consumers: 5ec9c (BCS after JSR 49370), 5ee1c and 5f190 (BCC after JSR 49fc6). No port, no
// bank change, no X, no register-indirect control transfer.
bool animation_objects_n25_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool borrow=false;bool zero=false;
    switch(r.pc) {
    // ---- 5e8b0 (shared): JSR 43e34.l; TST.B 79(A6); BNE.W 5e8c0; RTS; JSR 49fc6.l; RTS.
    case 0x5e8b0:case 0x5ebd0:case 0x5f174:return am_call(c,0x43e34,r.pc+6U);
    case 0x5e8b6:return on25_byte_is(c,0x79,0,0x5e8be,0x5e8c0);
    case 0x5e8c0:case 0x5ee16:case 0x5f18a:return am_call(c,0x49fc6,r.pc+6U);
    case 0x5e8be:case 0x5e8c6:case 0x5e9d4:case 0x5ebde:case 0x5eeaa:case 0x5f182:case 0x5f238:return am_return(c); // RTS.
    // ---- 5e8c8 (28ae child): MOVE.B #ff,76(A6); MOVE.W #0,D0; MOVE.W #0,D1; JSR 49290.l.
    case 0x5e8c8:if(!on25_put(c,0x76,1,0xff))return false;am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x49290,0x5e8dc);
    case 0x5e8dc:case 0x5eae8:case 0x5f00c:return am_call(c,0x491c4,r.pc+6U);  // JSR 491c4.l.
    case 0x5eae2:case 0x5f006:return am_call(c,0x49290,r.pc+6U);               // JSR 49290.l.
    case 0x5e8e2:case 0x5e9f6:return on25_8ebe(c,0xd4c,r.pc+0xeU);
    case 0x5e962:return on25_8ebe(c,0xd4c,0x5e970);
    case 0x5e984:return on25_8ebe(c,0xd4a,0x5e992);
    case 0x5e8f0:case 0x5e970:case 0x5e992:am_word(r.d[0],0xd56);return am_call(c,0x4a496,r.pc+0xaU); // MOVE.W #d56,D0; JSR 4a496.l.
    // BSET.B #6,15(A6); MOVE.W #801/#804/#803,68(A6); MOVE.W #same,1e(A6); JSR 16ef0.l.
    case 0x5e8fa:case 0x5f030: {
        const std::uint32_t id=r.pc==0x5e8fa?0x801U:0x803U;
        if(!on25_bset15(c) || !on25_put(c,0x68,2,id) || !on25_put(c,0x1e,2,id))return false;return am_call(c,0x16ef0,r.pc+0x18U);
    }
    // LEA 26(A6),A0; MOVE.W #18b,20(A6); MOVE.L 200194.l,22(A6); then the animation LONG 8(LONG 22).
    case 0x5e912:
        r.a[0]=am_index(r.a[6],0x26);if(!on25_put(c,0x20,2,0x18b) || !am_read(c,ON25_BANK_18B,4,value) || !on25_put(c,0x22,4,value))return false;
        return on25_anim(c,0x8,0x5e93a);
    case 0x5e93a:if(!am_write(c,r.a[6],4,0x5e940))return false;r.pc=0x5e940;return true; // MOVE.L #5e940,(A6) (fall-through).
    // ---- 5e940 (installed): follow the parent BYTE 76.
    case 0x5e940:return on25_follow(c,0x5e9d6,0x5e950);
    // MOVE.B D0,76(A6); CMPI.W #1,D0 (the whole low WORD; main decision 6); BNE.W 5e97e.
    case 0x5e950:if(!on25_put(c,0x76,1,on25_b(r.d[0])))return false;r.pc=on25_w(r.d[0])==1U?0x5e95c:0x5e97e;return true;
    case 0x5e95c:case 0x5e97e:case 0x5e9ec:                                   // [ST.B 79(A6);] JSR 8ff4.l.
        if(r.pc==0x5e9ec && !on25_put(c,0x79,1,0xff))return false;return am_call(c,0x8ff4,r.pc+(r.pc==0x5e9ec?0xaU:6U));
    case 0x5e97a:r.pc=0x5e99c;return true;                                    // BRA.W 5e99c.
    case 0x5e99c:return on25_table(c,ON25_TABLE_5E940,0x5e9d4,0x5e9b8);
    case 0x5e9b8:return on25_table_anim(c,0x5e9d4);
    // MOVEA.L c(A6),A0; TST.B 63(A0); BEQ.W 5ea2e.
    case 0x5e9d6:if(!on25_parent(c) || !am_read(c,am_index(r.a[0],0x63),1,value))return false;r.pc=on25_b(value)==0U?0x5ea2e:0x5e9e2;return true;
    case 0x5e9e2:if(!am_read(c,am_index(r.a[0],0x76),1,value))return false;r.pc=on25_b(value)==1U?0x5e9ec:0x5ea24;return true; // CMPI.B #1,76(A0).
    case 0x5ea04:return on25_anim(c,0xe0,0x5ea1a);
    case 0x5ea1a:if(!am_write(c,r.a[6],4,0x5e8b0))return false;r.pc=0x5ea2e;return true; // MOVE.L #5e8b0,(A6); BRA.W 5ea2e.
    case 0x5ea24:if(!on25_put(c,0x79,1,0) || !am_write(c,r.a[6],4,0x5e8b0))return false;r.pc=0x5ea2e;return true; // CLR.B 79(A6); MOVE.L.
    case 0x5ea2e:case 0x5f184:return am_call(c,0x4a46c,r.pc+6U);               // JSR 4a46c.l.
    case 0x5ea34:r.pc=0x5e8b0;return true;                                    // BRA.W 5e8b0.
    // ---- 5eac2 / 5ead4 (28ae children): MOVE.B #0/#1,78(A6); MOVE.W #7/#0,D0; MOVE.W #7b/#0,D1.
    case 0x5eac2:case 0x5ead4: {
        const bool first=r.pc==0x5eac2;if(!on25_put(c,0x78,1,first?0U:1U))return false;
        am_word(r.d[0],first?7U:0U);am_word(r.d[1],first?0x7bU:0U);r.pc=0x5eae2;return true;
    }
    case 0x5eaee:if(!on25_put(c,0x76,1,0xff))return false;return on25_8ebe(c,0xd47,0x5eb02); // MOVE.B #ff,76(A6).
    case 0x5eb02:return on25_8ebe(c,0xd49,0x5eb10);
    case 0x5eb10:return on25_8ebe(c,0xd55,0x5eb1e);
    case 0x5eb1e:return on25_8ebe(c,0xd58,0x5eb2c);
    // MOVE.B 19(A6),14(A6); BSET.B #6,15(A6); MOVE.W #804,68(A6); MOVE.W #804,1e(A6); JSR 16ef0.l.
    case 0x5eb2c:
        if(!on25_copy14(c,0x19) || !on25_bset15(c) || !on25_put(c,0x68,2,0x804) || !on25_put(c,0x1e,2,0x804))return false;
        return am_call(c,0x16ef0,0x5eb4a);
    // MOVE.W #18b,20(A6); MOVE.L 200194.l,22(A6); animation LONG 58(LONG 22).
    case 0x5eb4a:
        if(!on25_put(c,0x20,2,0x18b) || !am_read(c,ON25_BANK_18B,4,value) || !on25_put(c,0x22,4,value))return false;
        return on25_anim(c,0x58,0x5eb6e);
    case 0x5eb6e:if(!am_write(c,r.a[6],4,0x5eb74))return false;r.pc=0x5eb74;return true; // MOVE.L #5eb74,(A6) (fall-through).
    // ---- 5eb74 (installed).
    case 0x5eb74:return on25_follow(c,0x5ebd0,0x5eb84);
    // MOVE.B D0,76(A6); CMPI.B #1,D0; BNE.W 5ebcc.
    case 0x5eb84:if(!on25_put(c,0x76,1,on25_b(r.d[0])))return false;r.pc=on25_b(r.d[0])==1U?0x5eb90:0x5ebcc;return true;
    // ST.B 79(A6); MOVE.W #0,8a(A6); MOVE.W #8,8c(A6); MOVE.B #0,77(A6); MOVE.W #3c,7e(A6); MOVE.W #8,80(A6); animation LONG 58.
    case 0x5eb90:
        if(!on25_put(c,0x79,1,0xff) || !on25_put(c,0x8a,2,0) || !on25_put(c,0x8c,2,8) || !on25_put(c,0x77,1,0) || !on25_put(c,0x7e,2,0x3c) ||
            !on25_put(c,0x80,2,8))return false;
        return on25_anim(c,0x58,0x5ebc8);
    case 0x5ebc8:r.pc=0x5ebd0;return true;                                    // BRA.W 5ebd0.
    case 0x5ebcc:if(!on25_put(c,0x79,1,0))return false;r.pc=0x5ebd0;return true; // CLR.B 79(A6).
    case 0x5ebd6:return on25_byte_is(c,0x79,0,0x5ebde,0x5ebe0);
    // MOVEA.L c(A6),A0; TST.B 63(A0); BEQ.W 5ebfa.
    case 0x5ebe0:if(!on25_parent(c) || !am_read(c,am_index(r.a[0],0x63),1,value))return false;r.pc=on25_b(value)==0U?0x5ebfa:0x5ebec;return true;
    // CLR.B 79(A6); MOVE.L #5e8b0,(A6); BRA.W 5e8b0.
    case 0x5ebec:if(!on25_put(c,0x79,1,0) || !am_write(c,r.a[6],4,0x5e8b0))return false;r.pc=0x5e8b0;return true;
    case 0x5ebfa:return on25_byte_is(c,0x77,0,0x5ec04,0x5ec8c);
    // State 0: MOVE.W 8a(A6),D1; BEQ.W 5ec2c.
    case 0x5ec04:if(!on25_get(c,0x8a,2,value))return false;am_word(r.d[1],value);r.pc=on25_w(r.d[1])==0U?0x5ec2c:0x5ec0c;return true;
    case 0x5ec0c:r.pc=on25_lt_w(r.d[1],0x80)?0x5ec14:0x5ec22;return true;     // CMPI.W #80,D1; BGE.W 5ec22.
    // SUBQ.W #2,D1; BCC.W 5ec1e (C = borrow).
    case 0x5ec14:borrow=on25_w(r.d[1])<2U;am_word(r.d[1],(r.d[1]-2U)&65535U);r.pc=borrow?0x5ec1a:0x5ec1e;return true;
    // ADDQ.W #2,D1; BCC.W 5ec2c (C = carry out of bit 15).
    case 0x5ec22:borrow=on25_w(r.d[1])+2U>65535U;am_word(r.d[1],(r.d[1]+2U)&65535U);r.pc=borrow?0x5ec28:0x5ec2c;return true;
    case 0x5ec1a:case 0x5ec28:am_word(r.d[1],0);r.pc=r.pc+4U;return true;   // MOVE.W #0,D1.
    case 0x5ec1e:r.pc=0x5ec2c;return true;                                    // BRA.W 5ec2c.
    case 0x5ec2c:return on25_direction(c,0x5ec46,0x5ec3e);
    case 0x5ed30:return on25_direction(c,0x5ed4a,0x5ed42);
    case 0x5ec3e:on25_reflect(r,7);r.pc=0x5ec4c;return true;                // SUBQ.W #7,D1; NEG.W D1; BRA.W 5ec4c.
    case 0x5ec46:on25_reflect(r,0x27);r.pc=0x5ec4c;return true;             // SUBI.W #27,D1; NEG.W D1.
    case 0x5ed42:on25_reflect(r,7);r.pc=0x5ed50;return true;
    case 0x5ed4a:on25_reflect(r,0x27);r.pc=0x5ed50;return true;
    // ANDI.W #f,D1; MOVE.W D1,8c(A6); ADDI.W #f,D1; LSL.W #2,D1; animation LONG (LONG 22 + D1.W).
    case 0x5ec4c:
        am_word(r.d[1],r.d[1]&0xfU);if(!on25_put(c,0x8c,2,on25_w(r.d[1])))return false;am_word(r.d[1],(r.d[1]+0xfU)&65535U);
        am_word(r.d[1],(r.d[1]<<2)&65535U);return on25_indexed_anim(c,r.d[1],0x5ec70);
    // CLR.B 62(A6); MOVEA.L c(A6),A0; CMPI.B #1,77(A0); BNE.W 5ec88.
    case 0x5ec70:
        if(!on25_put(c,0x62,1,0) || !on25_parent(c) || !am_read(c,am_index(r.a[0],0x77),1,value))return false;
        r.pc=on25_b(value)==1U?0x5ec82:0x5ec88;return true;
    case 0x5ec82:if(!on25_put(c,0x77,1,1))return false;r.pc=0x5ec88;return true; // MOVE.B #1,77(A6).
    case 0x5ec88:case 0x5ed94:case 0x5edce:r.pc=0x5edd2;return true;           // BRA.W 5edd2.
    // State 1.
    case 0x5ec8c:return on25_byte_is(c,0x77,1,0x5ec96,0x5ed98);
    case 0x5ec96:return am_call(c,0x49370,0x5ec9c);
    case 0x5ec9c:                                                            // BCS.W 5ed5c (C returned by 49370).
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n25 caller requires known carry");
        r.pc=r.carry==AnimationCarrySet?0x5ed5c:0x5eca0;return true;
    case 0x5eca0:return am_call(c,0x4945e,0x5eca6);
    case 0x5eca6:return am_call(c,0x4964e,0x5ecac);                           // Boundary without an executor.
    // SUBI.W #ffce,D0; SUBI.W #ffd8,D1; SUB.W 42(A6),D0; SUB.W 46(A6),D1; JSR 44602.l (boundary).
    case 0x5ecac:
        am_word(r.d[0],(r.d[0]+0x32U)&65535U);am_word(r.d[1],(r.d[1]+0x28U)&65535U);
        if(!on25_get(c,0x42,2,value))return false;am_word(r.d[0],(r.d[0]-value)&65535U);
        if(!on25_get(c,0x46,2,value))return false;am_word(r.d[1],(r.d[1]-value)&65535U);
        return am_call(c,0x44602,0x5ecc2);
    // SUBQ.W #4,D0; ANDI.W #ff,D0; MOVE.W 8a(A6),D1; CMPI.W #80,D1; BGE.W 5ed04.
    case 0x5ecc2:
        am_word(r.d[0],(r.d[0]-4U)&0xffU);if(!on25_get(c,0x8a,2,value))return false;am_word(r.d[1],value);
        r.pc=on25_lt_w(r.d[1],0x80)?0x5ecd4:0x5ed04;return true;
    case 0x5ecd4:r.pc=on25_lt_w(r.d[0],0x80)?0x5ecdc:0x5ecfe;return true;     // CMPI.W #80,D0; BGE.W 5ecfe.
    case 0x5ed04:r.pc=on25_lt_w(r.d[0],0x80)?0x5ed0c:0x5ed12;return true;     // CMPI.W #80,D0; BGE.W 5ed12.
    // CMP.W D0,D1; BEQ.W equal; BGE.W greater (D1.W > D0.W, signed) else less.
    case 0x5ecdc:r.pc=on25_w(r.d[1])==on25_w(r.d[0])?0x5ecfa:(on25_lt_w(r.d[1],r.d[0])?0x5ece6:0x5ecf8);return true;
    case 0x5ed12:r.pc=on25_w(r.d[1])==on25_w(r.d[0])?0x5ed30:(on25_lt_w(r.d[1],r.d[0])?0x5ed1c:0x5ed22);return true;
    // ADDQ.W #2,D1; CMPI.W #3f,D1; BLE.W 5ecf4.
    case 0x5ece6:am_word(r.d[1],(r.d[1]+2U)&65535U);r.pc=on25_lt_w(0x3f,r.d[1])?0x5ecf0:0x5ecf4;return true;
    case 0x5ecf0:am_word(r.d[1],0x3f);r.pc=0x5ecf4;return true;              // MOVE.W #3f,D1.
    case 0x5ecf4:r.pc=0x5ecfa;return true;
    case 0x5ecfa:r.pc=0x5ed00;return true;
    case 0x5ed00:r.pc=0x5ed30;return true;
    case 0x5ecf8:case 0x5ecfe:am_word(r.d[1],(r.d[1]-2U)&65535U);r.pc=r.pc+2U;return true; // SUBQ.W #2,D1.
    case 0x5ed0c:case 0x5ed1c:am_word(r.d[1],(r.d[1]+2U)&65535U);r.pc=0x5ed30;return true; // ADDQ.W #2,D1; BRA.W 5ed30.
    // SUBQ.W #2,D1; CMPI.W #c1,D1; BGE.W 5ed30.
    case 0x5ed22:am_word(r.d[1],(r.d[1]-2U)&65535U);r.pc=on25_lt_w(r.d[1],0xc1)?0x5ed2c:0x5ed30;return true;
    case 0x5ed2c:am_word(r.d[1],0xc1);r.pc=0x5ed30;return true;              // MOVE.W #c1,D1.
    // ANDI.W #f,D1; MOVE.W D1,8c(A6); BRA.W 5ed60.
    case 0x5ed50:am_word(r.d[1],r.d[1]&0xfU);if(!on25_put(c,0x8c,2,on25_w(r.d[1])))return false;r.pc=0x5ed60;return true;
    case 0x5ed5c:if(!on25_get(c,0x8c,2,value))return false;am_word(r.d[1],value);r.pc=0x5ed60;return true; // MOVE.W 8c(A6),D1.
    // ADDI.W #f,D1; LSL.W #2,D1; animation LONG (LONG 22 + D1.W).
    case 0x5ed60:am_word(r.d[1],(r.d[1]+0xfU)&65535U);am_word(r.d[1],(r.d[1]<<2)&65535U);return on25_indexed_anim(c,r.d[1],0x5ed7c);
    // CLR.B 62(A6); SUBQ.W #1,7e(A6); BCC.W 5ed94.
    case 0x5ed7c:if(!on25_put(c,0x62,1,0) || !on25_dec(c,0x7e,borrow,zero))return false;r.pc=borrow?0x5ed88:0x5ed94;return true;
    // MOVE.W #5,7e(A6); MOVE.B #2,77(A6).
    case 0x5ed88:if(!on25_put(c,0x7e,2,5) || !on25_put(c,0x77,1,2))return false;r.pc=0x5ed94;return true;
    // State 2.
    case 0x5ed98:return on25_byte_is(c,0x77,2,0x5eda2,0x5edd2);
    case 0x5eda2:if(!on25_dec(c,0x7e,borrow,zero))return false;r.pc=borrow?0x5edaa:0x5edce;return true; // SUBQ.W #1,7e(A6); BCC.W 5edce.
    // MOVE.W 8c(A6),D0; ADDI.W #20,D0; LSL.W #2,D0; MOVEA.L 22(A6),A1; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; LEA 26(A6),A0; JSR 49f8c.l.
    case 0x5edaa:
        if(!on25_get(c,0x8c,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],(r.d[0]+0x20U)&65535U);
        am_word(r.d[0],(r.d[0]<<2)&65535U);return on25_indexed_anim(c,r.d[0],0x5edca);
    case 0x5edca:if(!on25_put(c,0x62,1,0xff))return false;r.pc=0x5edce;return true; // ST.B 62(A6).
    // Common: MOVEA.L c(A6),A0; MOVE.B 17(A0),D0; ANDI.B #1,D0; BNE.W 5edfe.
    case 0x5edd2:
        if(!on25_parent(c) || !am_read(c,am_index(r.a[0],0x17),1,value))return false;am_byte(r.d[0],value);am_byte(r.d[0],r.d[0]&1U);
        r.pc=on25_b(r.d[0])!=0U?0x5edfe:0x5ede2;return true;
    case 0x5ede2:return on25_byte_is(c,0x62,0,0x5edea,0x5edf4);
    case 0x5edfe:return on25_byte_is(c,0x62,0,0x5ee06,0x5ee10);
    case 0x5edea:if(!on25_copy14(c,0x19))return false;r.pc=0x5edfa;return true; // MOVE.B 19(A6),14(A6); BRA.W 5edfa.
    case 0x5edf4:if(!on25_copy14(c,0x1a))return false;r.pc=0x5edfa;return true;
    case 0x5edfa:r.pc=0x5ee16;return true;                                    // BRA.W 5ee16.
    case 0x5ee06:if(!on25_copy14(c,0x1b))return false;r.pc=0x5ee16;return true;
    case 0x5ee10:if(!on25_copy14(c,0x1c))return false;r.pc=0x5ee16;return true;
    case 0x5ee1c:                                                            // BCC.W 5eeaa (C returned by 49fc6).
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n25 caller requires known carry");
        r.pc=r.carry==AnimationCarryClear?0x5eeaa:0x5ee20;return true;
    // MOVEA.L #5eed2,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0x5ee20:case 0x5ee4e:r.a[0]=ON25_CHILD;am_word(r.d[0],0xa);return am_call(c,0x28ae,r.pc+0x10U);
    case 0x5ee30:return on25_pair(c,0,0x5ee4e);
    case 0x5ee5e:return on25_pair(c,4,0x5ee7c);
    case 0x5ee7c:if(!on25_dec(c,0x80,borrow,zero))return false;r.pc=zero?0x5ee84:0x5ee9e;return true; // SUBQ.W #1,80(A6); BNE.W 5ee9e.
    // MOVEA.L c(A6),A0; MOVE.B #1,62(A0); MOVE.W #8,80(A6); MOVE.B #0,77(A6); BRA.W 5eeaa.
    case 0x5ee84:
        if(!on25_parent(c) || !am_write(c,am_index(r.a[0],0x62),1,1) || !on25_put(c,0x80,2,8) || !on25_put(c,0x77,1,0))return false;
        r.pc=0x5eeaa;return true;
    case 0x5ee9e:if(!on25_put(c,0x7e,2,5) || !on25_put(c,0x77,1,1))return false;r.pc=0x5eeaa;return true; // MOVE.W #5,7e; MOVE.B #1,77.
    // ---- 5efe6 / 5eff8 (28ae children): MOVE.B #0/#1,78(A6); MOVE.W #0,D0; MOVE.W #0,D1.
    case 0x5efe6:case 0x5eff8:
        if(!on25_put(c,0x78,1,r.pc==0x5efe6?0U:1U))return false;am_word(r.d[0],0);am_word(r.d[1],0);r.pc=0x5f006;return true;
    case 0x5f012:if(!on25_put(c,0x76,1,0xff))return false;return on25_8ebe(c,0xd4c,0x5f026); // MOVE.B #ff,76(A6).
    case 0x5f026:am_word(r.d[0],0xd57);return am_call(c,0x4a496,0x5f030);     // MOVE.W #d57,D0; JSR 4a496.l.
    // MOVE.W #18b,20(A6); MOVE.L 200194.l,22(A6); TST.B 78(A6); BNE.W 5f078.
    case 0x5f048:
        if(!on25_put(c,0x20,2,0x18b) || !am_read(c,ON25_BANK_18B,4,value) || !on25_put(c,0x22,4,value))return false;
        return on25_byte_is(c,0x78,0,0x5f05e,0x5f078);
    case 0x5f05e:return on25_anim(c,0x1a4,0x5f074);
    case 0x5f078:return on25_anim(c,0x1b4,0x5f08e);
    case 0x5f074:r.pc=0x5f08e;return true;                                    // BRA.W 5f08e.
    case 0x5f08e:if(!am_write(c,r.a[6],4,0x5f094))return false;r.pc=0x5f094;return true; // MOVE.L #5f094,(A6) (fall-through).
    // ---- 5f094 (installed).
    case 0x5f094:return on25_follow(c,0x5f124,0x5f0a4);
    // MOVE.B D0,76(A6); TST.B 78(A6); BNE.W 5f0ec.
    case 0x5f0a4:if(!on25_put(c,0x76,1,on25_b(r.d[0])))return false;return on25_byte_is(c,0x78,0,0x5f0b0,0x5f0ec);
    case 0x5f0b0:return on25_table(c,ON25_TABLE_5F094_0,0x5f0e8,0x5f0cc);
    case 0x5f0cc:return on25_table_anim(c,0x5f0e8);
    case 0x5f0e8:r.pc=0x5f124;return true;                                    // BRA.W 5f124.
    case 0x5f15a:r.pc=0x5f174;return true;                                    // BRA.W 5f174.
    case 0x5f0ec:return on25_table(c,ON25_TABLE_5F094_1,0x5f124,0x5f108);
    case 0x5f108:return on25_table_anim(c,0x5f124);
    case 0x5f124:return on25_byte_is(c,0x62,0,0x5f12c,0x5f174);              // TST.B 62(A6); BNE.W 5f174.
    // MOVEA.L c(A6),A0; TST.B 63(A0); BEQ.W 5f174.
    case 0x5f12c:if(!on25_parent(c) || !am_read(c,am_index(r.a[0],0x63),1,value))return false;r.pc=on25_b(value)==0U?0x5f174:0x5f138;return true;
    // ST.B 62(A6); TST.B 78(A6); BNE.W 5f15e.
    case 0x5f138:if(!on25_put(c,0x62,1,0xff))return false;return on25_byte_is(c,0x78,0,0x5f144,0x5f15e);
    case 0x5f144:return on25_anim(c,0x1ac,0x5f15a);
    case 0x5f15e:return on25_anim(c,0x1bc,0x5f174);
    case 0x5f17a:return on25_byte_is(c,0x79,0,0x5f182,0x5f184);              // TST.B 79(A6); BNE.W 5f184.
    case 0x5f190:                                                            // BCC.W 5f238 (C returned by 49fc6).
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n25 caller requires known carry");
        r.pc=r.carry==AnimationCarryClear?0x5f238:0x5f194;return true;
    case 0x5f194:return on25_byte_is(c,0x62,0,0x5f238,0x5f19c);              // TST.B 62(A6); BEQ.W 5f238.
    case 0x5f19c:return on25_byte_is(c,0x78,0,0x5f1a4,0x5f1e0);
    case 0x5f1a4:return on25_byte_is(c,0x77,0,0x5f1ac,0x5f1c6);
    case 0x5f1e0:return on25_byte_is(c,0x77,0,0x5f1e8,0x5f202);
    case 0x5f1ac:return on25_anim(c,0x1ac,0x5f1c2);
    case 0x5f1c6:return on25_anim(c,0x1b0,0x5f1dc);
    case 0x5f1e8:return on25_anim(c,0x1bc,0x5f1fe);
    case 0x5f202:return on25_anim(c,0x1c0,0x5f218);
    case 0x5f1c2:r.pc=0x5f1dc;return true;                                    // BRA.W 5f1dc.
    case 0x5f1dc:case 0x5f1fe:r.pc=0x5f218;return true;                       // BRA.W 5f218.
    case 0x5f218:return am_call(c,0x49a58,0x5f21e);
    // ANDI.W #7f,D0; ADDI.W #180,D0; LEA 26(A6),A0; MOVE.W D0,6(A0); ADDQ.B #1,77(A6); ANDI.B #1,77(A6).
    case 0x5f21e:
        am_word(r.d[0],((r.d[0]&0x7fU)+0x180U)&65535U);r.a[0]=am_index(r.a[6],0x26);if(!am_write(c,r.a[0]+6U,2,on25_w(r.d[0])))return false;
        if(!on25_get(c,0x77,1,value) || !on25_put(c,0x77,1,on25_b(value+1U)) || !on25_get(c,0x77,1,value) || !on25_put(c,0x77,1,value&1U))
            return false;
        r.pc=0x5f238;return true;
    default:return am_error(c,"unsupported animation objects n25 PC");
    }
}
}
