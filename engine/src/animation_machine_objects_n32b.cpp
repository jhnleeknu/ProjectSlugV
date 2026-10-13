#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t on32b_b(std::uint32_t value) {return value&255U;}
std::uint32_t on32b_w(std::uint32_t value) {return value&65535U;}
bool on32b_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on32b_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// BTST.B #bit,d16(A6): true when the bit is 1.
bool on32b_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on32b_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// ANDI.B #mask,9d(A6); ANDI.B #mask,9e(A6) (read, then write each BYTE in order).
bool on32b_mask(AnimationMachineContext& c,std::uint32_t mask) {
    std::uint32_t value=0;
    if(!on32b_get(c,0x9d,1,value) || !on32b_put(c,0x9d,1,value&mask&255U))return false;
    return on32b_get(c,0x9e,1,value) && on32b_put(c,0x9e,1,value&mask&255U);
}
// TST.B d16(A6): true when the BYTE is zero.
bool on32b_zero(AnimationMachineContext& c,std::uint32_t displacement,bool& zero) {
    std::uint32_t value=0;if(!on32b_get(c,displacement,1,value))return false;zero=on32b_b(value)==0U;return true;
}
// MOVE.L #value,(A6) (installed callback LONG).
bool on32b_install(AnimationMachineContext& c,std::uint32_t value) {return on32b_put(c,0,4,value);}
// Bcc on a C returned by a callee (3b334 / 3a4da boundaries, 28ae / 1ab02 executors): clear -> clear_pc, set -> set_pc.
bool on32b_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n32b caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEM.L (A7)+,D0 (no CCR change), then BCS.W 39076 on the C of JSR 3a4da.
bool on32b_pop_carry(AnimationMachineContext& c,std::uint32_t clear_pc) {
    std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.d[0]=value;return on32b_carry(c,clear_pc,0x39076);
}
// TST.W D0; MOVEM.L (A7)+,D0; BNE.W nonzero_pc (Z of the D0 returned by 4ae4a).
bool on32b_pop_test(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t nonzero_pc) {
    const bool zero=on32b_w(c.s.d[0])==0U;std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.d[0]=value;
    c.s.pc=zero?zero_pc:nonzero_pc;return true;
}
// MOVE.L D0,-(A7); LEA 3b756(PC),A0; JSR 4ae4a.l.
bool on32b_match(AnimationMachineContext& c,std::uint32_t return_pc) {
    if(!am_push(c,4,c.s.d[0]))return false;c.s.a[0]=0x3b756;return am_call(c,0x4ae4a,return_pc);
}
// MOVE.L D0,-(A7); ANDI.B #bf,9d(A6); ANDI.B #bf,9e(A6); JSR 3a4da(PC).
bool on32b_hit(AnimationMachineContext& c,std::uint32_t return_pc) {
    if(!am_push(c,4,c.s.d[0]) || !on32b_mask(c,0xbf))return false;return am_call(c,0x3a4da,return_pc);
}
// MOVEA.L #list,A0 / LEA list(PC),A0; JSR target.
bool on32b_a0_call(AnimationMachineContext& c,std::uint32_t list,std::uint32_t target,std::uint32_t return_pc) {
    c.s.a[0]=list;return am_call(c,target,return_pc);
}
// MOVEA.L 82(A6),A0; JSR 3a5be(PC).
bool on32b_partner(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!on32b_get(c,0x82,4,value))return false;c.s.a[0]=value;return am_call(c,0x3a5be,return_pc);
}
// BTST.B #bit,D0; Bcc: set -> set_pc, clear -> clear_pc.
void on32b_dbit(AnimationMachineContext& c,unsigned int bit,std::uint32_t clear_pc,std::uint32_t set_pc) {
    c.s.pc=((c.s.d[0]>>bit)&1U)!=0U?set_pc:clear_pc;
}
// BTST.B #bit,d16(A6); Bcc: set -> set_pc, clear -> clear_pc.
bool on32b_mbit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,std::uint32_t clear_pc,std::uint32_t set_pc) {
    bool bit_set=false;if(!on32b_bit(c,displacement,bit,bit_set))return false;c.s.pc=bit_set?set_pc:clear_pc;return true;
}
// TST.B d16(A6); BEQ.W zero_pc.
bool on32b_tst(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t next_pc) {
    bool zero=false;if(!on32b_zero(c,displacement,zero))return false;c.s.pc=zero?zero_pc:next_pc;return true;
}
// CLR.B ac(A6) (39d8a) / CLR.B 98(A6) (39c7c); MOVEA.L #child,A0; MOVE.W #1e,D0; JSR 28ae.l.
bool on32b_spawn(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t child,std::uint32_t return_pc) {
    if(!on32b_put(c,displacement,1,0))return false;c.s.a[0]=child;am_word(c.s.d[0],0x1e);return am_call(c,0x28ae,return_pc);
}
// CLR.W D0; CLR.W D1; JSR 4970a.l.
bool on32b_face(AnimationMachineContext& c,std::uint32_t return_pc) {
    am_word(c.s.d[0],0);am_word(c.s.d[1],0);return am_call(c,0x4970a,return_pc);
}
// MOVE.W #1ac8,D0; JSR 3af8.l (39db4 / 39eb2) or JSR 3c44.l (39f80).
bool on32b_sound(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    am_word(c.s.d[0],0x1ac8);return am_call(c,target,return_pc);
}
// CMPI.W #9,D0; BCC.W skip_pc (unsigned).
void on32b_bound(AnimationMachineContext& c,std::uint32_t skip_pc,std::uint32_t next_pc) {
    c.s.pc=on32b_w(c.s.d[0])>=9U?skip_pc:next_pc;
}
// ADD.W D0,D0; ADD.W D0,D0; JMP table(PC,D0.W) (F1 decision 3: no bound check here; 39e6a / 39f3e bound the index to 0..8).
void on32b_table(AnimationMachineContext& c,std::uint32_t table) {
    am_word(c.s.d[0],(c.s.d[0]*2U)&65535U);am_word(c.s.d[0],(c.s.d[0]*2U)&65535U);c.s.pc=am_index(table,on32b_w(c.s.d[0]));
}
// ASR.L #5 (32-bit arithmetic right shift with bit 31 copied in).
std::uint32_t on32b_asr5(std::uint32_t value) {
    const std::uint32_t shifted=(value&0xffffffffU)>>5;return (value&0x80000000U)!=0U?(shifted|0xf8000000U):shifted;
}
}
// Objects F4 N32b (125 block starts): the 39cda function body at and above 39b72 (rescope N32 split, N32a main decision 1; the shared
// tail 3a34c..3a4a4 belongs to N31): the states 39b72 / 39b80 (installed 39bb2), the installed 39cb0 with the function entry 39cda,
// 39db4 (installed 39e24, BRA.W table 39e76) and 39eb2 (installed 39ef4, BRA.W table 39f4a). Entries back into N32a (39076 39156
// 395dc 395f8 3976a 398be) and the N31 tail (3a350 3a41c) go to their executors; 3a4be 3a4da 3a5be 3a5d2 3b282 3b288 3b302 3b334
// 3b424 d0fec and the branch exits 39f9c 3a242 have no executor here. The 8 consumers read the C of 3b334 / 28ae / 1ab02 (BCC.W) or
// 3a4da (MOVEM.L (A7)+,D0; BCS.W); 39c9e / 39dac (ORI.B #1,CCR) produce Set. The only fixed ROM read is the BYTE table 39ca6 (39c74,
// unchecked sign-extended D0.W index, live bus). No port, no bank change.
bool animation_objects_n32b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool bit=false;
    switch(r.pc) {
    // ---- 39b72 / 39b80: animation 3b936 / 3b93c, JSR 3a5d2.
    case 0x39b72:return on32b_a0_call(c,0x3b936,0x3b302,0x39b7c);       // MOVEA.L #3b936,A0; JSR 3b302(PC).
    case 0x39b7c:r.pc=0x39b8a;return true;                               // BRA.W 39b8a.
    case 0x39b80:return on32b_a0_call(c,0x3b93c,0x3b302,0x39b8a);       // MOVEA.L #3b93c,A0; JSR 3b302(PC).
    case 0x39b8a:return am_call(c,0x3a5d2,0x39b8e);                      // JSR 3a5d2(PC).
    // CLR.L 64(A6); MOVE.B #0,9f(A6); ANDI.B #ef,9d(A6); ANDI.B #ef,9e(A6); CLR.B 98(A6); CLR.B ac(A6); MOVE.L #39bb2,(A6).
    case 0x39b8e:
        if(!on32b_put(c,0x64,4,0) || !on32b_put(c,0x9f,1,0) || !on32b_mask(c,0xef) || !on32b_put(c,0x98,1,0) || !on32b_put(c,0xac,1,0) ||
            !on32b_install(c,0x39bb2))return false;
        r.pc=0x39bb2;return true;
    // ---- installed 39bb2: BTST.B #7,15(A6); BEQ.W 398be (N32a).
    case 0x39bb2:return on32b_mbit(c,0x15,7,0x398be,0x39bbc);
    case 0x39bbc:return am_call(c,0x3b424,0x39bc0);                      // JSR 3b424(PC).
    case 0x39bc0:return on32b_tst(c,0xac,0x39c48,0x39bc8);              // TST.B ac(A6); BEQ.W 39c48.
    case 0x39bc8:on32b_dbit(c,7,0x39bd0,0x39db4);return true;           // BTST.B #7,D0; BNE.W 39db4.
    case 0x39bd0:on32b_dbit(c,1,0x39be2,0x39bd8);return true;           // BTST.B #1,D0; BEQ.W 39be2.
    case 0x39bd8:return on32b_mbit(c,0x15,7,0x39be2,0x39156);           // BTST.B #7,15(A6); BNE.W 39156 (N32a).
    case 0x39be2:on32b_dbit(c,5,0x39bea,0x3976a);return true;           // BTST.B #5,D0; BNE.W 3976a (N32a).
    case 0x39bea:return on32b_mbit(c,0x94,2,0x39bf4,0x39c14);           // BTST.B #2,94(A6); BNE.W 39c14.
    case 0x39bf4:return on32b_mbit(c,0x9d,4,0x39c14,0x39bfe);           // BTST.B #4,9d(A6); BEQ.W 39c14.
    case 0x39bfe:return on32b_match(c,0x39c0a);
    case 0x39c0a:return on32b_pop_test(c,0x39c14,0x39b80);              // TST.W D0; MOVEM.L (A7)+,D0; BNE.W 39b80.
    case 0x39c14:return on32b_mbit(c,0x9d,6,0x39c38,0x39c1e);           // BTST.B #6,9d(A6); BEQ.W 39c38.
    case 0x39c1e:return on32b_hit(c,0x39c30);
    case 0x39c30:return on32b_pop_carry(c,0x39c38);                      // MOVEM.L (A7)+,D0; BCS.W 39076 (C returned by 3a4da).
    case 0x39c38:on32b_dbit(c,2,0x39c40,0x395dc);return true;           // BTST.B #2,D0; BNE.W 395dc (N32a).
    case 0x39c40:on32b_dbit(c,3,0x39c48,0x395f8);return true;           // BTST.B #3,D0; BNE.W 395f8 (N32a).
    case 0x39c48:return on32b_partner(c,0x39c50);
    case 0x39c50:return am_call(c,0x3b288,0x39c54);                      // JSR 3b288(PC).
    case 0x39c54:return am_call(c,0x3b334,0x39c58);                      // JSR 3b334(PC).
    case 0x39c58:return on32b_carry(c,0x39c62,0x39c5c);                  // BCC.W 39c62 (C returned by 3b334).
    case 0x39c5c:if(!on32b_install(c,0x39cb0))return false;r.pc=0x39c62;return true; // MOVE.L #39cb0,(A6).
    case 0x39c62:return on32b_tst(c,0x98,0x39ca2,0x39c6a);              // TST.B 98(A6); BEQ.W 39ca2.
    case 0x39c6a:return on32b_a0_call(c,0x3b774,0x4ae4a,0x39c74);       // LEA 3b774(PC),A0; JSR 4ae4a.l.
    // MOVE.B 39ca6(PC,D0.W),D1; BEQ.W 39ca2 (fixed ROM BYTE table, sign-extended D0.W index without a bound check, live bus).
    case 0x39c74:
        if(!am_read(c,am_index(0x39ca6,on32b_w(r.d[0])),1,value))return false;am_byte(r.d[1],value);
        r.pc=on32b_b(value)==0U?0x39ca2:0x39c7c;return true;
    case 0x39c7c:return on32b_spawn(c,0x98,0x3b1ae,0x39c90);
    case 0x39c90:return on32b_carry(c,0x39ca2,0x39c94);                  // BCC.W 39ca2 (C returned by 28ae).
    case 0x39c94:return on32b_face(c,0x39c9e);
    case 0x39c9e:case 0x39dac:r.carry=AnimationCarrySet;r.pc=r.pc+4U;return true; // ORI.B #1,CCR (Set).
    case 0x39ca2:case 0x39db0:r.pc=0x3a350;return true;                // BRA.W 3a350 (N31).
    // ---- installed 39cb0: animation 3b942.
    case 0x39cb0:return on32b_a0_call(c,0x3b942,0x3b302,0x39cba);
    // MOVE.B #0,95(A6); CLR.L 64(A6); ANDI.B #8f,9d(A6); ANDI.B #8f,9e(A6); CLR.B ac(A6); MOVE.L #39cda,(A6).
    case 0x39cba:
        if(!on32b_put(c,0x95,1,0) || !on32b_put(c,0x64,4,0) || !on32b_mask(c,0x8f) || !on32b_put(c,0xac,1,0) || !on32b_install(c,0x39cda))
            return false;
        r.pc=0x39cda;return true;
    // ---- installed 39cda (function entry).
    case 0x39cda:return on32b_mbit(c,0x15,7,0x398be,0x39ce4);
    case 0x39ce4:return am_call(c,0x3b424,0x39ce8);
    case 0x39ce8:on32b_dbit(c,7,0x39cf0,0x39db4);return true;
    case 0x39cf0:on32b_dbit(c,1,0x39d02,0x39cf8);return true;
    case 0x39cf8:return on32b_mbit(c,0x15,7,0x39d02,0x39156);
    case 0x39d02:on32b_dbit(c,5,0x39d0a,0x3976a);return true;
    case 0x39d0a:return on32b_mbit(c,0x94,2,0x39d14,0x39d34);
    case 0x39d14:return on32b_mbit(c,0x9d,4,0x39d34,0x39d1e);
    case 0x39d1e:return on32b_match(c,0x39d2a);
    case 0x39d2a:return on32b_pop_test(c,0x39d34,0x39b72);              // TST.W D0; MOVEM.L (A7)+,D0; BNE.W 39b72.
    case 0x39d34:return on32b_mbit(c,0x9d,6,0x39d58,0x39d3e);
    case 0x39d3e:return on32b_hit(c,0x39d50);
    case 0x39d50:return on32b_pop_carry(c,0x39d58);
    case 0x39d58:on32b_dbit(c,2,0x39d60,0x395dc);return true;
    case 0x39d60:on32b_dbit(c,3,0x39d68,0x395f8);return true;
    case 0x39d68:return on32b_partner(c,0x39d70);
    case 0x39d70:return am_call(c,0x3b288,0x39d74);
    case 0x39d74:return am_call(c,0x3b334,0x39d78);
    case 0x39d78:return on32b_carry(c,0x39d82,0x39d7c);                  // BCC.W 39d82 (C returned by 3b334).
    case 0x39d7c:if(!on32b_install(c,0x38e92))return false;r.pc=0x39d82;return true; // MOVE.L #38e92,(A6) (value outside the routing).
    case 0x39d82:return on32b_tst(c,0xac,0x39db0,0x39d8a);              // TST.B ac(A6); BEQ.W 39db0.
    case 0x39d8a:return on32b_spawn(c,0xac,0x3acd6,0x39d9e);
    case 0x39d9e:return on32b_carry(c,0x39db0,0x39da2);                  // BCC.W 39db0 (C returned by 28ae).
    case 0x39da2:return on32b_face(c,0x39dac);
    // ---- 39db4: sound 1ac8, 3a4be, animation 3b960, 3a5d2.
    case 0x39db4:return on32b_sound(c,0x3af8,0x39dbe);
    case 0x39dbe:am_byte(r.d[1],1);return am_call(c,0x3a4be,0x39dc6);   // MOVE.B #1,D1; JSR 3a4be(PC).
    case 0x39dc6:return on32b_a0_call(c,0x3b960,0x3b302,0x39dd0);
    case 0x39dd0:return am_call(c,0x3a5d2,0x39dd4);
    // CLR.B 9f(A6); LEA 3b792(PC),A0; JSR 4ae4a.l.
    case 0x39dd4:if(!on32b_put(c,0x9f,1,0))return false;return on32b_a0_call(c,0x3b792,0x4ae4a,0x39de2);
    case 0x39de2:r.pc=(r.a[0]&0xffffffffU)==0U?0x39dfe:0x39dea;return true; // CMPA.W #0,A0; BEQ.W 39dfe.
    // MOVE.W 42(A0),D0; SUB.W 42(A6),D0; MOVE.W 46(A0),D1; SUB.W 46(A6),D1; BRA.W 39e02 (16-bit wrap).
    case 0x39dea:
        if(!am_read(c,am_index(r.a[0],0x42),2,value))return false;am_word(r.d[0],value);
        if(!on32b_get(c,0x42,2,other))return false;am_word(r.d[0],(on32b_w(r.d[0])+65536U-on32b_w(other))&65535U);
        if(!am_read(c,am_index(r.a[0],0x46),2,value))return false;am_word(r.d[1],value);
        if(!on32b_get(c,0x46,2,other))return false;am_word(r.d[1],(on32b_w(r.d[1])+65536U-on32b_w(other))&65535U);
        r.pc=0x39e02;return true;
    case 0x39dfe:r.d[0]=0x30;r.d[1]=0;r.pc=0x39e02;return true;          // MOVEQ #30,D0; MOVEQ #0,D1.
    // MOVE.L #ffff6000,D2; MOVEQ #23,D3; JSR d0fec.l.
    case 0x39e02:r.d[2]=0xffff6000U;r.d[3]=0x23;return am_call(c,0xd0fec,0x39e10);
    // MOVEM.L D0-D1,36(A6); MOVE.L #3b68a,7e(A6); MOVE.L #39e24,(A6).
    case 0x39e10:
        if(!on32b_put(c,0x36,4,r.d[0]) || !on32b_put(c,0x3a,4,r.d[1]) || !on32b_put(c,0x7e,4,0x3b68a) || !on32b_install(c,0x39e24))return false;
        r.pc=0x39e24;return true;
    // ---- installed 39e24: TST.W 3a(A6); BLE.W 39e36.
    case 0x39e24:
        if(!on32b_get(c,0x3a,2,value))return false;
        r.pc=((value&0x8000U)!=0U || on32b_w(value)==0U)?0x39e36:0x39e2c;return true;
    case 0x39e2c:if(!on32b_put(c,0xa4,1,0x7f))return false;r.pc=0x39e50;return true; // MOVE.B #7f,a4(A6); BRA.W 39e50.
    case 0x39e36:return on32b_a0_call(c,0x3b736,0x1ab02,0x39e40);       // LEA 3b736(PC),A0; JSR 1ab02.l.
    case 0x39e40:return on32b_carry(c,0x39e4a,0x39e44);                  // BCC.W 39e4a (C returned by 1ab02).
    case 0x39e44:if(!on32b_install(c,0x3a2f4))return false;r.pc=0x39e4a;return true; // MOVE.L #3a2f4,(A6) (N31 value).
    case 0x39e4a:if(!on32b_put(c,0xa4,1,0))return false;r.pc=0x39e50;return true; // MOVE.B #0,a4(A6).
    // ADDI.L #ffff6000,3a(A6) (32-bit wrap); JSR 3b282(PC).
    case 0x39e50:
        if(!on32b_get(c,0x3a,4,value) || !on32b_put(c,0x3a,4,(value+0xffff6000U)&0xffffffffU))return false;
        return am_call(c,0x3b282,0x39e5c);
    case 0x39e5c:return am_call(c,0x3b334,0x39e60);
    case 0x39e60:return on32b_a0_call(c,0x3b7b0,0x4ae4a,0x39e6a);
    case 0x39e6a:on32b_bound(c,0x39e9e,0x39e72);return true;            // CMPI.W #9,D0; BCC.W 39e9e.
    case 0x39e72:on32b_table(c,0x39e7a);return true;                     // JMP 39e7a(PC,D0.W).
    // The 9 BRA.W slots of 39e7a: k = 1, 2 -> 39f9c (boundary), every other k -> 39e9e.
    case 0x39e7e:case 0x39e82:r.pc=0x39f9c;return true;
    case 0x39e7a:case 0x39e86:case 0x39e8a:case 0x39e8e:case 0x39e92:case 0x39e96:case 0x39e9a:r.pc=0x39e9e;return true;
    case 0x39e9e:return on32b_mbit(c,0x15,5,0x39eae,0x39ea8);           // BTST.B #5,15(A6); BEQ.W 39eae.
    case 0x39ea8:if(!on32b_install(c,0x39f9c))return false;r.pc=0x39eae;return true; // MOVE.L #39f9c,(A6) (value outside the routing).
    case 0x39eae:case 0x39f98:r.pc=0x3a41c;return true;                // BRA.W 3a41c (N31).
    // ---- 39eb2: sound 1ac8, 3a4be, animation 3b8fa, 3a5d2.
    case 0x39eb2:return on32b_sound(c,0x3af8,0x39ebc);
    case 0x39ebc:am_byte(r.d[1],1);return am_call(c,0x3a4be,0x39ec4);
    case 0x39ec4:return on32b_a0_call(c,0x3b8fa,0x3b302,0x39ece);
    case 0x39ece:return am_call(c,0x3a5d2,0x39ed2);
    // MOVE.B #5,95(A6); MOVE.B #11,9f(A6); MOVE.L #3b68a,7e(A6); MOVE.L #0,36(A6); MOVE.L #39ef4,(A6).
    case 0x39ed2:
        if(!on32b_put(c,0x95,1,5) || !on32b_put(c,0x9f,1,0x11) || !on32b_put(c,0x7e,4,0x3b68a) || !on32b_put(c,0x36,4,0) ||
            !on32b_install(c,0x39ef4))return false;
        r.pc=0x39ef4;return true;
    // ---- installed 39ef4: partner.
    case 0x39ef4:return on32b_partner(c,0x39efc);
    // MOVE.L #c0000,D0; BTST.B #0,15(A6); BEQ.W 39f0e.
    case 0x39efc:r.d[0]=0xc0000;if(!on32b_bit(c,0x15,0,bit))return false;r.pc=bit?0x39f0c:0x39f0e;return true;
    case 0x39f0c:r.d[0]=(0U-r.d[0])&0xffffffffU;r.pc=0x39f0e;return true; // NEG.L D0.
    // SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6) (second read of 36); JSR 3b282(PC).
    case 0x39f0e:
        if(!on32b_get(c,0x36,4,value))return false;r.d[0]=on32b_asr5((r.d[0]-value)&0xffffffffU);
        if(!on32b_get(c,0x36,4,value) || !on32b_put(c,0x36,4,(value+r.d[0])&0xffffffffU))return false;
        return am_call(c,0x3b282,0x39f1c);
    case 0x39f1c:return am_call(c,0x3b334,0x39f20);
    case 0x39f20:return on32b_mbit(c,0x15,7,0x39f80,0x39f2a);           // BTST.B #7,15(A6); BEQ.W 39f80.
    case 0x39f2a:return on32b_mbit(c,0x61,0,0x39f34,0x39f80);           // BTST.B #0,61(A6); BNE.W 39f80.
    case 0x39f34:return on32b_a0_call(c,0x3b80a,0x4ae4a,0x39f3e);
    case 0x39f3e:on32b_bound(c,0x39f72,0x39f46);return true;            // CMPI.W #9,D0; BCC.W 39f72.
    case 0x39f46:on32b_table(c,0x39f4e);return true;                     // JMP 39f4e(PC,D0.W).
    // The 9 BRA.W slots of 39f4e: k = 1, 2 -> 39f80, every other k -> 39f72.
    case 0x39f52:case 0x39f56:r.pc=0x39f80;return true;
    case 0x39f4e:case 0x39f5a:case 0x39f5e:case 0x39f62:case 0x39f66:case 0x39f6a:case 0x39f6e:r.pc=0x39f72;return true;
    case 0x39f72:return on32b_a0_call(c,0x3b736,0x1ab02,0x39f7c);
    case 0x39f7c:return on32b_carry(c,0x39f98,0x39f80);                  // BCC.W 39f98 (C returned by 1ab02).
    case 0x39f80:return on32b_sound(c,0x3c44,0x39f8a);                   // MOVE.W #1ac8,D0; JSR 3c44.l.
    case 0x39f8a:return on32b_a0_call(c,0x3b828,0x4ae4a,0x39f94);
    case 0x39f94:r.pc=0x3a242;return true;                               // BRA.W 3a242 (boundary).
    default:return am_error(c,"unsupported animation objects n32b PC");
    }
}
}
