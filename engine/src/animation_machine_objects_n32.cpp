#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t on32_b(std::uint32_t value) {return value&255U;}
std::uint32_t on32_w(std::uint32_t value) {return value&65535U;}
bool on32_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on32_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// BTST.B #bit,d16(A6): true when the bit is 1.
bool on32_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on32_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,d16(A6) (read, then write the changed BYTE).
bool on32_change(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool on) {
    std::uint32_t value=0;if(!on32_get(c,displacement,1,value))return false;
    value=on?(value|(1U<<bit)):(value&~(1U<<bit));return on32_put(c,displacement,1,value&255U);
}
// ANDI.B #mask,9d(A6); ANDI.B #mask,9e(A6) (read, then write each BYTE in order).
bool on32_mask(AnimationMachineContext& c,std::uint32_t mask) {
    std::uint32_t value=0;
    if(!on32_get(c,0x9d,1,value) || !on32_put(c,0x9d,1,value&mask&255U))return false;
    return on32_get(c,0x9e,1,value) && on32_put(c,0x9e,1,value&mask&255U);
}
// TST.B d16(A6): true when the BYTE is zero.
bool on32_zero(AnimationMachineContext& c,std::uint32_t displacement,bool& zero) {
    std::uint32_t value=0;if(!on32_get(c,displacement,1,value))return false;zero=on32_b(value)==0U;return true;
}
// MOVE.L #value,(A6) (installed callback LONG).
bool on32_install(AnimationMachineContext& c,std::uint32_t value) {return on32_put(c,0,4,value);}
// Bcc on a C returned by a boundary callee (3b334 / 3a4da): clear -> clear_pc, set -> set_pc.
bool on32_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n32 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEM.L (A7)+,D0 (no CCR change), then BCS.W set_pc on the C of JSR 3a4da.
bool on32_pop_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.d[0]=value;return on32_carry(c,clear_pc,set_pc);
}
// TST.W D0; MOVEM.L (A7)+,D0; BNE.W 39b72 (Z of the D0 returned by 4ae4a).
bool on32_pop_test(AnimationMachineContext& c,std::uint32_t zero_pc) {
    const bool zero=on32_w(c.s.d[0])==0U;std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.d[0]=value;
    c.s.pc=zero?zero_pc:0x39b72;return true;
}
// MOVE.L D0,-(A7); LEA 3b756(PC),A0; JSR 4ae4a.l.
bool on32_match(AnimationMachineContext& c,std::uint32_t return_pc) {
    if(!am_push(c,4,c.s.d[0]))return false;c.s.a[0]=0x3b756;return am_call(c,0x4ae4a,return_pc);
}
// MOVE.L D0,-(A7); ANDI.B #bf,9d(A6); ANDI.B #bf,9e(A6); JSR 3a4da(PC).
bool on32_hit(AnimationMachineContext& c,std::uint32_t return_pc) {
    if(!am_push(c,4,c.s.d[0]) || !on32_mask(c,0xbf))return false;return am_call(c,0x3a4da,return_pc);
}
// MOVEA.L #list,A0; JSR 3b302(PC).
bool on32_animation(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {c.s.a[0]=list;return am_call(c,0x3b302,return_pc);}
// MOVEA.L 82(A6),A0; JSR 3a5be(PC).
bool on32_partner(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!on32_get(c,0x82,4,value))return false;c.s.a[0]=value;return am_call(c,0x3a5be,return_pc);
}
// MOVE.W #id,D0; JSR 3af8.l.
bool on32_sound(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {am_word(c.s.d[0],id);return am_call(c,0x3af8,return_pc);}
// MOVE.L D0,D1; SWAP D1; BTST.B #5,D1; BNE.W set_pc (bit 21 of D0).
void on32_high(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    c.s.d[1]=c.s.d[0];am_swap(c.s.d[1]);c.s.pc=((c.s.d[1]>>5)&1U)!=0U?set_pc:clear_pc;
}
// CLR.B a4(A6); ANDI.B #df,9d(A6); ANDI.B #df,9e(A6).
bool on32_release(AnimationMachineContext& c) {return on32_put(c,0xa4,1,0) && on32_mask(c,0xdf);}
// BTST.B #5,9d(A6); BEQ.W skip_pc / TST.W 3a(A6); BGT.W skip_pc / TST.B 9c(A6); BNE.W 3990c.
bool on32_ready(AnimationMachineContext& c,std::uint32_t skip_pc,std::uint32_t next_pc) {
    bool bit=false;if(!on32_bit(c,0x9d,5,bit))return false;c.s.pc=bit?next_pc:skip_pc;return true;
}
bool on32_rising(AnimationMachineContext& c,std::uint32_t skip_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!on32_get(c,0x3a,2,value))return false;
    const bool negative=(value&0x8000U)!=0U,zero=on32_w(value)==0U;c.s.pc=(!negative && !zero)?skip_pc:next_pc;return true;
}
bool on32_count(AnimationMachineContext& c,std::uint32_t skip_pc) {
    bool zero=false;if(!on32_zero(c,0x9c,zero))return false;c.s.pc=zero?skip_pc:0x3990c;return true;
}
// MOVE.L 3a(A6),D7; ADDI.L #ffff6000,D7; MOVE.L D7,3a(A6); JSR 3b2a0(PC) (32-bit wrap).
bool on32_fall(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!on32_get(c,0x3a,4,value))return false;c.s.d[7]=(value+0xffff6000U)&0xffffffffU;
    if(!on32_put(c,0x3a,4,c.s.d[7]))return false;return am_call(c,0x3b2a0,return_pc);
}
}
// Objects F4 N32a (203 block starts): the 39cda function body below 39b72 (rescope N32 split, main decision 1): the states 38dd4 /
// 38e20 / 38ff4 / 39076 / 39156 / 395dc / 395f8 / 3973c / 3976a / 39834 / 398be / 3990c / 3995e with their installed callbacks
// (38dfc 38e4e 39028 39090 3917a 39654 39754 3979e 397d2 397fa 39848 398ca 398d0 398e0 39932 3996e) and the shared tail 3999a.
// Exits into the 39b72 part (39b72 39db4 39eb2) and into 3a34c / 3a350 are stop-only boundaries; the callees 39a1a 3a4da 3a5be 3a5d2
// 3b288 3b2a0 3b2a6 3b302 3b334 3b424 4d4b4 have no executor here. The 14 consumers read the C of 3b334 (BCC.W) or 3a4da (MOVEM.L
// (A7)+,D0; BCS.W). Install values outside the routing (38bac 38e86 38e92 39366 39a76) are data. No port, no bank, no fixed ROM read.
bool animation_objects_n32_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool bit=false,zero=false;
    switch(r.pc) {
    // ---- 38dd4: CMPI.B #11,9f(A6); BCC.W 38e20 (unsigned).
    case 0x38dd4:if(!on32_get(c,0x9f,1,value))return false;r.pc=on32_b(value)>=0x11U?0x38e20:0x38dde;return true;
    case 0x38dde:return on32_animation(c,0x3b8d6,0x38de8);
    case 0x38de8:return am_call(c,0x3a5d2,0x38dec);                      // JSR 3a5d2(PC).
    // MOVE.B #4,95(A6); CLR.L 64(A6); MOVE.L #38dfc,(A6) (falls through into the installed 38dfc).
    case 0x38dec:if(!on32_put(c,0x95,1,4) || !on32_put(c,0x64,4,0) || !on32_install(c,0x38dfc))return false;r.pc=0x38dfc;return true;
    // BSET.B #3,94(A6); MOVEA.L 82(A6),A0; JSR 3a5be(PC).
    case 0x38dfc:case 0x391b2:if(!on32_change(c,0x94,3,true))return false;return on32_partner(c,r.pc==0x38dfc?0x38e0a:0x391c0);
    case 0x38e0a:return am_call(c,0x3b288,0x38e0e);                      // JSR 3b288(PC).
    case 0x38e0e:return am_call(c,0x3b334,0x38e12);                      // JSR 3b334(PC).
    case 0x38e12:return on32_carry(c,0x38e1c,0x38e16);                   // BCC.W 38e1c (C returned by 3b334).
    case 0x38e16:if(!on32_install(c,0x38e20))return false;r.pc=0x38e1c;return true; // MOVE.L #38e20,(A6).
    // BRA.W 3a350 (stop-only boundary).
    case 0x38e1c:case 0x39072:case 0x39152:case 0x391e4:case 0x39738:case 0x39766:case 0x397ce:case 0x398ba:case 0x39a16:r.pc=0x3a350;return true;
    // ---- 38e20: MOVE.W #0,8a(A6); MOVE.B #11,9f(A6); MOVE.W #1a62,D0; JSR 3af8.l.
    case 0x38e20:if(!on32_put(c,0x8a,2,0) || !on32_put(c,0x9f,1,0x11))return false;return on32_sound(c,0x1a62,0x38e36);
    case 0x38e36:return on32_animation(c,0x3b8ac,0x38e40);
    case 0x38e40:return am_call(c,0x3a5d2,0x38e44);
    case 0x38e44:if(!on32_put(c,0x64,4,0) || !on32_install(c,0x38e4e))return false;r.pc=0x38e4e;return true; // CLR.L 64(A6); MOVE.L #38e4e,(A6).
    case 0x38e4e:return am_call(c,0x3b288,0x38e52);
    case 0x38e52:return am_call(c,0x3b334,0x38e56);
    case 0x38e56:return on32_carry(c,0x38e7a,0x38e5a);                   // BCC.W 38e7a (C returned by 3b334).
    // MOVE.W 86(A6),D0; MOVE.B #1,D1; JSR 4d4b4.l (boundary).
    case 0x38e5a:if(!on32_get(c,0x86,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],1);return am_call(c,0x4d4b4,0x38e68);
    // MOVE.L #38bac,(A6) (N31 value); MOVE.L #0,56(A6); BRA.W 3a34c.
    case 0x38e68:if(!on32_install(c,0x38bac) || !on32_put(c,0x56,4,0))return false;r.pc=0x3a34c;return true;
    case 0x38e7a:if(!on32_put(c,0x56,4,0))return false;r.pc=0x3a350;return true; // MOVE.L #0,56(A6); BRA.W 3a350.
    // ---- 38ff4: MOVE.W #1a62,D0; JSR 3af8.l.
    case 0x38ff4:return on32_sound(c,0x1a62,0x38ffe);
    case 0x38ffe:if(!on32_get(c,0x9f,1,value))return false;r.pc=on32_b(value)<=0x11U?0x3900e:0x39008;return true; // CMPI.B #11; BLS.W.
    case 0x39008:if(!on32_put(c,0x9f,1,0x11))return false;r.pc=0x3900e;return true; // MOVE.B #11,9f(A6).
    case 0x3900e:return on32_animation(c,0x3b8d0,0x39018);
    // MOVE.B #2,95(A6); CLR.L 64(A6); MOVE.L #39028,(A6) (falls through into the installed 39028).
    case 0x39018:if(!on32_put(c,0x95,1,2) || !on32_put(c,0x64,4,0) || !on32_install(c,0x39028))return false;r.pc=0x39028;return true;
    case 0x39028:return am_call(c,0x3b424,0x3902c);                      // JSR 3b424(PC).
    case 0x3902c:r.pc=((r.d[0]>>7)&1U)!=0U?0x39db4:0x39034;return true;  // BTST.B #7,D0; BNE.W 39db4.
    case 0x39034:r.pc=((r.d[0]>>1)&1U)==0U?0x39046:0x3903c;return true;  // BTST.B #1,D0; BEQ.W 39046.
    case 0x3903c:if(!on32_bit(c,0x15,7,bit))return false;r.pc=bit?0x39156:0x39046;return true; // BTST.B #7,15(A6); BNE.W 39156.
    case 0x39046:return on32_partner(c,0x3904e);
    case 0x3904e:return am_call(c,0x3b288,0x39052);
    case 0x39052:return am_call(c,0x3b334,0x39056);
    case 0x39056:return on32_carry(c,0x39072,0x3905a);                   // BCC.W 39072 (C returned by 3b334).
    // ANDI.B #bf,9d(A6); ANDI.B #bf,9e(A6); MOVE.B #0,9f(A6); MOVE.L #38e92,(A6) (value outside the routing).
    case 0x3905a:if(!on32_mask(c,0xbf) || !on32_put(c,0x9f,1,0) || !on32_install(c,0x38e92))return false;r.pc=0x39072;return true;
    // ---- 39076: MOVE.B #ff,98(A6); MOVEA.L #3b972,A0; JSR 3b302(PC).
    case 0x39076:if(!on32_put(c,0x98,1,0xff))return false;return on32_animation(c,0x3b972,0x39086);
    case 0x39086:return am_call(c,0x3a5d2,0x3908a);
    case 0x3908a:if(!on32_install(c,0x39090))return false;r.pc=0x39090;return true; // MOVE.L #39090,(A6).
    // BTST.B #7,15(A6); BEQ.W 398be.
    case 0x39090:case 0x3917a:case 0x39654:case 0x3979e:
        if(!on32_bit(c,0x15,7,bit))return false;
        r.pc=!bit?0x398be:(r.pc==0x39090?0x3909a:(r.pc==0x3917a?0x39184:(r.pc==0x39654?0x3965e:0x397a8)));return true;
    case 0x3909a:if(!on32_zero(c,0x98,zero))return false;r.pc=zero?0x390a2:0x39140;return true; // TST.B 98(A6); BNE.W 39140.
    case 0x390a2:return am_call(c,0x3b424,0x390a6);
    case 0x390a6:r.pc=((r.d[0]>>7)&1U)!=0U?0x39db4:0x390ae;return true;  // BTST.B #7,D0; BNE.W 39db4.
    case 0x390ae:r.pc=((r.d[0]>>1)&1U)==0U?0x390c0:0x390b6;return true;  // BTST.B #1,D0; BEQ.W 390c0.
    case 0x390b6:if(!on32_bit(c,0x15,7,bit))return false;r.pc=bit?0x39156:0x390c0;return true; // BTST.B #7,15(A6); BNE.W 39156.
    case 0x390c0:r.pc=((r.d[0]>>1)&1U)!=0U?0x390da:0x390c8;return true;  // BTST.B #1,D0; BNE.W 390da.
    case 0x390c8:if(!on32_zero(c,0x9f,zero))return false;r.pc=zero?0x390da:0x390d0;return true; // TST.B 9f(A6); BEQ.W 390da.
    case 0x390d0:if(!on32_bit(c,0x15,7,bit))return false;r.pc=bit?0x38ff4:0x390da;return true; // BTST.B #7,15(A6); BNE.W 38ff4.
    case 0x390da:r.pc=((r.d[0]>>5)&1U)!=0U?0x3976a:0x390e2;return true;  // BTST.B #5,D0; BNE.W 3976a.
    case 0x390e2:if(!on32_bit(c,0x94,2,bit))return false;r.pc=bit?0x3910c:0x390ec;return true; // BTST.B #2,94(A6); BNE.W 3910c.
    case 0x390ec:if(!on32_bit(c,0x9d,4,bit))return false;r.pc=!bit?0x3910c:0x390f6;return true; // BTST.B #4,9d(A6); BEQ.W 3910c.
    case 0x390f6:return on32_match(c,0x39102);
    case 0x39102:return on32_pop_test(c,0x3910c);
    case 0x3910c:if(!on32_bit(c,0x9d,6,bit))return false;r.pc=!bit?0x39130:0x39116;return true; // BTST.B #6,9d(A6); BEQ.W 39130.
    case 0x39116:return on32_hit(c,0x39128);
    case 0x39128:return on32_pop_carry(c,0x39130,0x39076);               // MOVEM.L (A7)+,D0; BCS.W 39076 (C returned by 3a4da).
    case 0x39130:r.pc=((r.d[0]>>2)&1U)!=0U?0x395dc:0x39138;return true;  // BTST.B #2,D0; BNE.W 395dc.
    case 0x39138:r.pc=((r.d[0]>>3)&1U)!=0U?0x395f8:0x39140;return true;  // BTST.B #3,D0; BNE.W 395f8.
    case 0x39140:return am_call(c,0x3b288,0x39144);
    case 0x39144:return am_call(c,0x3b334,0x39148);
    case 0x39148:return on32_carry(c,0x39152,0x3914c);                   // BCC.W 39152 (C returned by 3b334).
    case 0x3914c:case 0x39722:if(!on32_install(c,0x38e92))return false;r.pc=r.pc==0x3914c?0x39152:0x39728;return true; // MOVE.L #38e92,(A6).
    // ---- 39156: MOVE.W #1a5f,D0; JSR 3af8.l.
    case 0x39156:return on32_sound(c,0x1a5f,0x39160);
    case 0x39160:return on32_animation(c,0x3b8d6,0x3916a);
    // MOVE.B #2,95(A6); CLR.L 64(A6); MOVE.L #3917a,(A6) (falls through into the installed 3917a).
    case 0x3916a:if(!on32_put(c,0x95,1,2) || !on32_put(c,0x64,4,0) || !on32_install(c,0x3917a))return false;r.pc=0x3917a;return true;
    case 0x39184:return am_call(c,0x3b424,0x39188);
    case 0x39188:r.pc=((r.d[0]>>7)&1U)!=0U?0x39eb2:0x39190;return true;  // BTST.B #7,D0; BNE.W 39eb2.
    case 0x39190:r.pc=((r.d[0]>>1)&1U)!=0U?0x391aa:0x39198;return true;  // BTST.B #1,D0; BNE.W 391aa.
    case 0x39198:if(!on32_zero(c,0x9f,zero))return false;r.pc=zero?0x391aa:0x391a0;return true; // TST.B 9f(A6); BEQ.W 391aa.
    case 0x391a0:if(!on32_bit(c,0x15,7,bit))return false;r.pc=bit?0x38ff4:0x391aa;return true; // BTST.B #7,15(A6); BNE.W 38ff4.
    case 0x391aa:r.pc=((r.d[0]>>5)&1U)!=0U?0x38dd4:0x391b2;return true;  // BTST.B #5,D0; BNE.W 38dd4.
    case 0x391c0:return am_call(c,0x3b288,0x391c4);
    case 0x391c4:return am_call(c,0x3b334,0x391c8);
    case 0x391c8:return on32_carry(c,0x391e4,0x391cc);                   // BCC.W 391e4 (C returned by 3b334).
    // ANDI.B #bf,9d(A6); ANDI.B #bf,9e(A6); MOVE.B #11,9f(A6); MOVE.L #39366,(A6) (value outside the routing).
    case 0x391cc:if(!on32_mask(c,0xbf) || !on32_put(c,0x9f,1,0x11) || !on32_install(c,0x39366))return false;r.pc=0x391e4;return true;
    // ---- 395dc / 395f8: BTST.B #0,15(A6); BNE.W 395ee / BEQ.W 3960a; TST.B a3(A6); BEQ.W 3973c.
    case 0x395dc:if(!on32_bit(c,0x15,0,bit))return false;r.pc=bit?0x395ee:0x395e6;return true;
    case 0x395e6:if(!on32_zero(c,0xa3,zero))return false;r.pc=zero?0x3973c:0x395ee;return true;
    case 0x395ee:if(!on32_change(c,0x94,5,true))return false;r.pc=0x39610;return true; // BSET.B #5,94(A6); BRA.W 39610.
    case 0x395f8:if(!on32_bit(c,0x15,0,bit))return false;r.pc=!bit?0x3960a:0x39602;return true;
    case 0x39602:if(!on32_zero(c,0xa3,zero))return false;r.pc=zero?0x3973c:0x3960a;return true;
    case 0x3960a:if(!on32_change(c,0x94,5,false))return false;r.pc=0x39610;return true; // BCLR.B #5,94(A6).
    // BTST.B #5,94(A6); SNE.B D0; BTST.B #0,15(A6); SNE.B D1; EOR.B D1,D0; BNE.W 39634.
    case 0x39610:
        if(!on32_bit(c,0x94,5,bit))return false;am_byte(r.d[0],bit?0xffU:0U);
        if(!on32_bit(c,0x15,0,bit))return false;am_byte(r.d[1],bit?0xffU:0U);
        am_byte(r.d[0],on32_b(r.d[0])^on32_b(r.d[1]));r.pc=on32_b(r.d[0])!=0U?0x39634:0x39626;return true;
    case 0x39626:return on32_animation(c,0x3b912,0x39630);
    case 0x39630:r.pc=0x3963e;return true;                               // BRA.W 3963e.
    case 0x39634:return on32_animation(c,0x3b918,0x3963e);
    // MOVE.W #aa,2c(A6); MOVE.B #1,95(A6); CLR.L 64(A6); MOVE.L #39654,(A6) (falls through into the installed 39654).
    case 0x3963e:
        if(!on32_put(c,0x2c,2,0xaa) || !on32_put(c,0x95,1,1) || !on32_put(c,0x64,4,0) || !on32_install(c,0x39654))return false;
        r.pc=0x39654;return true;
    case 0x3965e:return am_call(c,0x3b424,0x39662);
    case 0x39662:r.pc=((r.d[0]>>7)&1U)!=0U?0x39db4:0x3966a;return true;  // BTST.B #7,D0; BNE.W 39db4.
    case 0x3966a:r.pc=((r.d[0]>>1)&1U)==0U?0x3967c:0x39672;return true;  // BTST.B #1,D0; BEQ.W 3967c.
    case 0x39672:if(!on32_bit(c,0x15,7,bit))return false;r.pc=bit?0x39156:0x3967c;return true; // BTST.B #7,15(A6); BNE.W 39156.
    case 0x3967c:r.pc=((r.d[0]>>5)&1U)!=0U?0x3976a:0x39684;return true;  // BTST.B #5,D0; BNE.W 3976a.
    case 0x39684:if(!on32_bit(c,0x94,2,bit))return false;r.pc=bit?0x396ae:0x3968e;return true; // BTST.B #2,94(A6); BNE.W 396ae.
    case 0x3968e:if(!on32_bit(c,0x9d,4,bit))return false;r.pc=!bit?0x396ae:0x39698;return true; // BTST.B #4,9d(A6); BEQ.W 396ae.
    case 0x39698:return on32_match(c,0x396a4);
    case 0x396a4:return on32_pop_test(c,0x396ae);
    case 0x396ae:if(!on32_bit(c,0x9d,6,bit))return false;r.pc=!bit?0x396d2:0x396b8;return true; // BTST.B #6,9d(A6); BEQ.W 396d2.
    case 0x396b8:return on32_hit(c,0x396ca);
    case 0x396ca:return on32_pop_carry(c,0x396d2,0x39076);               // MOVEM.L (A7)+,D0; BCS.W 39076 (C returned by 3a4da).
    case 0x396d2:r.pc=((r.d[0]>>3)&1U)==0U?0x396fa:0x396da;return true;  // BTST.B #3,D0; BEQ.W 396fa.
    case 0x396da:if(!on32_bit(c,0x15,0,bit))return false;r.pc=!bit?0x396ec:0x396e4;return true; // BTST.B #0,15(A6); BEQ.W 396ec.
    case 0x396e4:case 0x3970c:if(!on32_zero(c,0xa3,zero))return false;r.pc=zero?0x3973c:(r.pc==0x396e4?0x396ec:0x39714);return true;
    case 0x396ec:if(!on32_bit(c,0x94,5,bit))return false;r.pc=bit?0x395f8:0x396f6;return true; // BTST.B #5,94(A6); BNE.W 395f8.
    case 0x396f6:case 0x3971e:r.pc=0x39728;return true;                  // BRA.W 39728.
    case 0x396fa:r.pc=((r.d[0]>>2)&1U)==0U?0x39722:0x39702;return true;  // BTST.B #2,D0; BEQ.W 39722.
    case 0x39702:if(!on32_bit(c,0x15,0,bit))return false;r.pc=bit?0x39714:0x3970c;return true; // BTST.B #0,15(A6); BNE.W 39714.
    case 0x39714:if(!on32_bit(c,0x94,5,bit))return false;r.pc=!bit?0x395dc:0x3971e;return true; // BTST.B #5,94(A6); BEQ.W 395dc.
    case 0x39728:return on32_partner(c,0x39730);
    case 0x39730:return am_call(c,0x3b288,0x39734);
    case 0x39734:return am_call(c,0x3b334,0x39738);
    // ---- 3973c: MOVEA.L #3b95a,A0; JSR 3b302(PC).
    case 0x3973c:return on32_animation(c,0x3b95a,0x39746);
    case 0x39746:return am_call(c,0x3a5d2,0x3974a);
    case 0x3974a:if(!on32_put(c,0x64,4,0) || !on32_install(c,0x39754))return false;r.pc=0x39754;return true; // CLR.L 64(A6); MOVE.L #39754,(A6).
    case 0x39754:return am_call(c,0x3b288,0x39758);
    case 0x39758:return am_call(c,0x3b334,0x3975c);
    case 0x3975c:return on32_carry(c,0x39766,0x39760);                   // BCC.W 39766 (C returned by 3b334).
    case 0x39760:if(!on32_install(c,0x38e86))return false;r.pc=0x39766;return true; // MOVE.L #38e86,(A6) (value outside the routing).
    // ---- 3976a: MOVEA.L #3b91e,A0; JSR 3b302(PC).
    case 0x3976a:return on32_animation(c,0x3b91e,0x39774);
    // MOVE.B #3,95(A6); MOVE.B #0,9a(A6); ANDI.B #ef,9d(A6); ANDI.B #ef,9e(A6); JSR 496c2.l.
    case 0x39774:if(!on32_put(c,0x95,1,3) || !on32_put(c,0x9a,1,0) || !on32_mask(c,0xef))return false;return am_call(c,0x496c2,0x39792);
    case 0x39792:if(!on32_put(c,0x9f,1,0) || !on32_install(c,0x3979e))return false;r.pc=0x3979e;return true; // MOVE.B #0,9f(A6); MOVE.L #3979e,(A6).
    case 0x397a8:return am_call(c,0x3b424,0x397ac);
    case 0x397ac:r.pc=((r.d[0]>>7)&1U)!=0U?0x39db4:0x397b4;return true;  // BTST.B #7,D0; BNE.W 39db4.
    case 0x397b4:return on32_partner(c,0x397bc);
    case 0x397bc:return am_call(c,0x3b2a6,0x397c0);                      // JSR 3b2a6(PC).
    case 0x397c0:return am_call(c,0x3b334,0x397c4);
    case 0x397c4:return on32_carry(c,0x397ce,0x397c8);                   // BCC.W 397ce (C returned by 3b334).
    case 0x397c8:if(!on32_install(c,0x397d2))return false;r.pc=0x397ce;return true; // MOVE.L #397d2,(A6).
    // ---- installed callback 397d2: MOVE.W #1a61,D0; JSR 3af8.l.
    case 0x397d2:return on32_sound(c,0x1a61,0x397dc);
    case 0x397dc:return on32_animation(c,0x3b924,0x397e6);
    // MOVE.B #0,95(A6); MOVE.L #8fc4e,3a(A6); MOVE.L #397fa,(A6) (falls through into the installed 397fa).
    case 0x397e6:if(!on32_put(c,0x95,1,0) || !on32_put(c,0x3a,4,0x8fc4e) || !on32_install(c,0x397fa))return false;r.pc=0x397fa;return true;
    case 0x397fa:return am_call(c,0x3b424,0x397fe);
    // BTST.B #6,9d(A6); BEQ.W skip.
    case 0x397fe:if(!on32_bit(c,0x9d,6,bit))return false;r.pc=!bit?0x39822:0x39808;return true;
    case 0x39808:return on32_hit(c,0x3981a);
    case 0x3981a:return on32_pop_carry(c,0x39822,0x39834);               // MOVEM.L (A7)+,D0; BCS.W 39834 (C returned by 3a4da).
    // TST.W 3a(A6); BPL.W 39830.
    case 0x39822:if(!on32_get(c,0x3a,2,value))return false;r.pc=(value&0x8000U)==0U?0x39830:0x3982a;return true;
    case 0x3982a:if(!on32_install(c,0x398d0))return false;r.pc=0x39830;return true; // MOVE.L #398d0,(A6).
    case 0x39830:case 0x39908:case 0x3995a:case 0x39996:r.pc=0x3999a;return true; // BRA.W 3999a.
    // ---- 39834: JSR 3a5d2(PC).
    case 0x39834:return am_call(c,0x3a5d2,0x39838);
    case 0x39838:return on32_animation(c,0x3b978,0x39842);
    case 0x39842:if(!on32_install(c,0x39848))return false;r.pc=0x39848;return true; // MOVE.L #39848,(A6).
    case 0x39848:return am_call(c,0x3b424,0x3984c);
    case 0x3984c:on32_high(c,0x39858,0x39868);return true;
    case 0x39858:if(!on32_release(c))return false;r.pc=0x39868;return true;
    case 0x39868:return on32_ready(c,0x39882,0x39872);                   // BTST.B #5,9d(A6); BEQ.W 39882.
    case 0x39872:return on32_rising(c,0x39882,0x3987a);                  // TST.W 3a(A6); BGT.W 39882.
    case 0x3987a:return on32_count(c,0x39882);                           // TST.B 9c(A6); BNE.W 3990c.
    case 0x39882:return am_call(c,0x3b424,0x39886);
    case 0x39886:return am_call(c,0x39a1a,0x3988a);                      // JSR 39a1a(PC) (boundary).
    case 0x3988a:return on32_fall(c,0x3989c);
    case 0x3989c:return am_call(c,0x3b334,0x398a0);
    case 0x398a0:return on32_carry(c,0x398aa,0x398a4);                   // BCC.W 398aa (C returned by 3b334).
    case 0x398a4:if(!on32_install(c,0x398ca))return false;r.pc=0x398aa;return true; // MOVE.L #398ca,(A6).
    // BTST.B #7,15(A6); BEQ.W 398ba / 39a16; MOVE.L #39a76,(A6) (value outside the routing).
    case 0x398aa:case 0x39a06:if(!on32_bit(c,0x15,7,bit))return false;
        r.pc=r.pc==0x398aa?(bit?0x398b4:0x398ba):(bit?0x39a10:0x39a16);return true;
    case 0x398b4:case 0x39a10:if(!on32_install(c,0x39a76))return false;r.pc=r.pc==0x398b4?0x398ba:0x39a16;return true;
    // ---- 398be: ANDI.B #df,9d(A6); ANDI.B #df,9e(A6); 398ca: MOVE.B #0,95(A6); 398d0: MOVEA.L #3b92a,A0; JSR 3b302(PC).
    case 0x398be:if(!on32_mask(c,0xdf))return false;r.pc=0x398ca;return true;
    case 0x398ca:if(!on32_put(c,0x95,1,0))return false;r.pc=0x398d0;return true;
    case 0x398d0:return on32_animation(c,0x3b92a,0x398da);
    case 0x398da:if(!on32_install(c,0x398e0))return false;r.pc=0x398e0;return true; // MOVE.L #398e0,(A6).
    case 0x398e0:return am_call(c,0x3b424,0x398e4);
    case 0x398e4:if(!on32_bit(c,0x9d,6,bit))return false;r.pc=!bit?0x39908:0x398ee;return true;
    case 0x398ee:return on32_hit(c,0x39900);
    case 0x39900:return on32_pop_carry(c,0x39908,0x39834);
    // ANDI.B #df,9d(A6); ANDI.B #df,9e(A6); SUBQ.B #1,9c(A6); MOVE.B #a,a4(A6); MOVE.W #1aa7,D0; JSR 3af8.l.
    case 0x3990c:
        if(!on32_mask(c,0xdf) || !on32_get(c,0x9c,1,value) || !on32_put(c,0x9c,1,(value+255U)&255U) || !on32_put(c,0xa4,1,0xa))return false;
        return on32_sound(c,0x1aa7,0x3992c);
    case 0x3992c:if(!on32_install(c,0x39932))return false;r.pc=0x39932;return true; // MOVE.L #39932,(A6).
    case 0x39932:return am_call(c,0x3b424,0x39936);
    case 0x39936:if(!on32_bit(c,0x9d,6,bit))return false;r.pc=!bit?0x3995a:0x39940;return true;
    case 0x39940:return on32_hit(c,0x39952);
    case 0x39952:return on32_pop_carry(c,0x3995a,0x39834);
    // ---- 3995e (no static reference, main decision 2): MOVEA.L #3b948,A0; JSR 3b302(PC).
    case 0x3995e:return on32_animation(c,0x3b948,0x39968);
    case 0x39968:if(!on32_install(c,0x3996e))return false;r.pc=0x3996e;return true; // MOVE.L #3996e,(A6).
    case 0x3996e:return am_call(c,0x3b424,0x39972);
    case 0x39972:if(!on32_bit(c,0x9d,6,bit))return false;r.pc=!bit?0x39996:0x3997c;return true;
    case 0x3997c:return on32_hit(c,0x3998e);
    case 0x3998e:return on32_pop_carry(c,0x39996,0x39834);
    // ---- shared tail 3999a: MOVEA.L 82(A6),A0; JSR 3a5be(PC).
    case 0x3999a:return on32_partner(c,0x399a2);
    // MOVE.B 97(A6),D0; CMPI.B #4,D0; BEQ.W 398ca.
    case 0x399a2:if(!on32_get(c,0x97,1,value))return false;am_byte(r.d[0],value);r.pc=on32_b(value)==4U?0x398ca:0x399ae;return true;
    case 0x399ae:return am_call(c,0x3b424,0x399b2);
    case 0x399b2:on32_high(c,0x399be,0x399ce);return true;
    case 0x399be:if(!on32_release(c))return false;r.pc=0x399ce;return true;
    case 0x399ce:return on32_ready(c,0x399e8,0x399d8);
    case 0x399d8:return on32_rising(c,0x399e8,0x399e0);
    case 0x399e0:return on32_count(c,0x399e8);
    case 0x399e8:return am_call(c,0x3b424,0x399ec);
    case 0x399ec:return am_call(c,0x39a1a,0x399f0);
    case 0x399f0:return on32_fall(c,0x39a02);
    case 0x39a02:return am_call(c,0x3b334,0x39a06);
    default:return am_error(c,"unsupported animation objects n32 PC");
    }
}
}
