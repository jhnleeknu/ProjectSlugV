#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OU17_BANK_RISE=0x200140;      // MOVE.L 200140.L,22(A6) (bbf98; banked window LONG, live bus).
const std::uint32_t OU17_BANK_SHOW=0x200088;      // MOVE.L 200088.L,22(A6) (c3dbc c3e42 c3f40; banked window LONG, live bus).
const std::uint32_t OU17_SINE=0x4419e;            // LEA 4419e(PC),A0 (443ea; fixed ROM WORD table 4411e..4439e).
const std::uint32_t OU17_PLAYER1=0x100cb8;        // LEA 100cb8.L,A0 (1c5ea).
const std::uint32_t OU17_PLAYER2=0x100da8;        // LEA 100da8.L,A0 (1c600).
const std::uint32_t OU17_SCREEN=0x10d38e;         // LEA 10d38e.L,A0 (4929e).
bool ou17_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou17_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool ou17_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u17 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #callback,(A6) then continue at next_pc (the fall-through block).
bool ou17_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// BSET/BCLR.B #bit,d16(An) (read-modify-write BYTE; Z only).
bool ou17_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!ou17_get(c,base,displacement,1,value))return false;
    value=set?(value|(1U<<bit)):(value&~(1U<<bit));return ou17_put(c,base,displacement,1,value&255U);
}
// ASR.L #n (sign bit replicated, no implementation-defined shift of a negative value).
std::uint32_t ou17_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t shifted=value>>n;
    return (value&0x80000000U)?(shifted|~(0xffffffffU>>n)):shifted;
}
// MULS.W: signed 16 x 16 -> 32 (two's complement LONG computed without signed overflow).
std::uint32_t ou17_muls(std::uint32_t a,std::uint32_t b) {
    const std::uint32_t x=a&65535U,y=b&65535U;
    const std::uint32_t mx=(x&0x8000U)?(65536U-x):x,my=(y&0x8000U)?(65536U-y):y;
    const std::uint32_t magnitude=mx*my;  // <= 0x40000000
    const bool negative=((x&0x8000U)!=0U)!=((y&0x8000U)!=0U);
    return negative?((0U-magnitude)&0xffffffffU):magnitude;
}
// Signed compare helpers for BGE/BGT (the bias moves the sign bit; unsigned compare of the biased values).
bool ou17_long_ge(std::uint32_t a,std::uint32_t b) {return (a^0x80000000U)>=(b^0x80000000U);}
bool ou17_word_gt(std::uint32_t a,std::uint32_t b) {return ((a&65535U)^0x8000U)>((b&65535U)^0x8000U);}
// LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1;
// JSR 49f8c.L (the bank LONG and the LONG at its value + d16 through the live bus).
bool ou17_animation(AnimationMachineContext& c,std::uint32_t k,std::uint32_t bank,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!ou17_put(c,r.a[6],0x20,2,k) || !am_read(c,bank,4,value) || !ou17_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!ou17_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!ou17_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 42(A6),547a(A5); MOVE.W 46(A6),547c(A5); JSR 49fc6.L.
bool ou17_focus(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ou17_get(c,r.a[6],0x42,2,value) || !ou17_put(c,r.a[5],0x547a,2,value))return false;
    if(!ou17_get(c,r.a[6],0x46,2,value) || !ou17_put(c,r.a[5],0x547c,2,value))return false;
    return am_call(c,0x49fc6,return_pc);
}
// MOVE.W #k,D0; MOVE.B #0,D1; JSR 8ebe.L.
bool ou17_palette(AnimationMachineContext& c,std::uint32_t k,std::uint32_t return_pc) {
    am_word(c.s.d[0],k);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVEA.L #child,A0; MOVE.W #k,D0; JSR 28ae.L (fade_card child).
bool ou17_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t k,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],k);return am_call(c,0x28ae,return_pc);
}
// LEA table(PC),A0; CMPA.W #0,A0; BEQ.W rts_pc (A0 is never 0 here; the comparison is kept).
bool ou17_table(AnimationMachineContext& c,std::uint32_t table,std::uint32_t rts_pc,std::uint32_t call_pc) {
    c.s.a[0]=table;c.s.pc=c.s.a[0]==0U?rts_pc:call_pc;return true;
}
// MOVE.W #v,68(A6); MOVE.W #v,1e(A6).
bool ou17_height(AnimationMachineContext& c,std::uint32_t v) {
    return ou17_put(c,c.s.a[6],0x68,2,v) && ou17_put(c,c.s.a[6],0x1e,2,v);
}
// MOVE.B 19(A6),14(A6).
bool ou17_copy_frame(AnimationMachineContext& c) {
    std::uint32_t value=0;return ou17_get(c,c.s.a[6],0x19,1,value) && ou17_put(c,c.s.a[6],0x14,1,value);
}
}
// Objects F4 U17 (109 block starts): the player node cleanup 1c5ea (readiness 289e twice, consuming its C before BCLR a8 bit 0), the
// C5 sine/cosine product 443ea (fixed ROM WORD table 4411e..4439e), 482c0 (BSET 5683 bits, stage_entry ca56, exit 48398, 1c5ea), the C3
// helpers 491c4 (parent 15 low bits) and 4929e (screen offsets 10d38e), the C4 motion 4bfa4 (U08b 4bc44/4bb22, 4c020, U08b tail 4bf0a)
// and 4c020 (velocity vector from 64/6f through 443ea), the object callback bbf56 with its installed callbacks bbf70 bbf80 bbfd2 bc020
// bc044 bc060 bc076 (bank LONG 200140 and the LONG at its value + d4, interpreter 49f8c/49fc6 whose C bc054 consumes, U18 boundary
// 4be2c, fade_card child bc08c) and the object callback c3d60 with its installed callbacks c3df2 c3e38 c3e70 c3ec0 c3edc c3f74 c3faa and
// the children c3f08 c3f92 (bank LONG 200088 and the LONGs at its value + 64/68/6c, 49fc6 C consumed by c3e88, 288c C consumed by c3f86
// and c3fb6). The only boundary without an executor here is 4be2c (U18). U17 produces no known carry and writes no port.
bool animation_objects_u17_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- 1c5ea: LEA 100cb8.L,A0; JSR 289e.L.
    case 0x1c5ea:r.a[0]=OU17_PLAYER1;return am_call(c,0x289e,0x1c5f6);
    case 0x1c5f6:return ou17_consume(c,false,0x1c600,0x1c5fa);              // BCC.W 1c600 (C returned by 289e).
    case 0x1c5fa:if(!ou17_bit(c,r.a[0],0xa8,0,false))return false;r.pc=0x1c600;return true; // BCLR.B #0,a8(A0).
    case 0x1c600:r.a[0]=OU17_PLAYER2;return am_call(c,0x289e,0x1c60c);     // LEA 100da8.L,A0; JSR 289e.L.
    case 0x1c60c:return ou17_consume(c,false,0x1c616,0x1c610);              // BCC.W 1c616.
    case 0x1c610:if(!ou17_bit(c,r.a[0],0xa8,0,false))return false;r.pc=0x1c616;return true; // BCLR.B #0,a8(A0).
    // RTS (keeps C).
    case 0x1c616:case 0x482e8:case 0xbbf7e:case 0xbc01e:case 0xbc05e:case 0xbc08a:case 0xc3e36:case 0xc3ebe:case 0xc3f06:case 0xc3f90:
    case 0xc3fd2:return am_return(c);

    // ---- 443ea: LSR.W #8,D1; MOVE.W D1,D2; ASR.L #8,D0; MOVE.L D0,D1; ADD.W D2,D2; LEA 4419e(PC),A0; MULS.W (A0,D2.W),D0;
    // MULS.W -80(A0,D2.W),D1; RTS.
    case 0x443ea:
        am_word(r.d[1],(r.d[1]&65535U)>>8);am_word(r.d[2],r.d[1]);r.d[0]=ou17_asr(r.d[0],8);r.d[1]=r.d[0];
        am_word(r.d[2],(r.d[2]<<1)&65535U);r.a[0]=OU17_SINE;
        if(!am_read(c,am_index(r.a[0],r.d[2]),2,value) || !am_read(c,am_index(r.a[0],r.d[2])-0x80U,2,other))return false;
        r.d[0]=ou17_muls(r.d[0],value);r.d[1]=ou17_muls(r.d[1],other);return am_return(c);

    // ---- 482c0: BSET.B #5/#3/#1/#4,5683(A5); JSR ca56.L.
    case 0x482c0:
        if(!ou17_bit(c,r.a[5],0x5683,5,true) || !ou17_bit(c,r.a[5],0x5683,3,true) || !ou17_bit(c,r.a[5],0x5683,1,true) ||
           !ou17_bit(c,r.a[5],0x5683,4,true))return false;
        return am_call(c,0xca56,0x482de);
    case 0x482de:return am_call(c,0x48398,0x482e2);                          // JSR 48398(PC).
    case 0x482e2:return am_call(c,0x1c5ea,0x482e8);                          // JSR 1c5ea.L.

    // ---- 491c4: MOVEA.L c(A6),A0; MOVE.B 15(A0),D0; MOVE.B 15(A6),D1; ANDI.B #3,D0; ANDI.B #fc,D1; OR.B D0,D1; MOVE.B D1,15(A6); RTS.
    case 0x491c4:
        if(!ou17_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ou17_get(c,r.a[0],0x15,1,value) || !ou17_get(c,r.a[6],0x15,1,other))return false;
        am_byte(r.d[0],value&3U);am_byte(r.d[1],(other&0xfcU)|(value&3U));
        if(!ou17_put(c,r.a[6],0x15,1,r.d[1]&255U))return false;return am_return(c);
    // ---- 4929e: LEA 10d38e.L,A0; ADD.W 14(A0),D0; ADD.W 18(A0),D1; RTS.
    case 0x4929e:
        r.a[0]=OU17_SCREEN;if(!ou17_get(c,r.a[0],0x14,2,value) || !ou17_get(c,r.a[0],0x18,2,other))return false;
        am_word(r.d[0],(r.d[0]+value)&65535U);am_word(r.d[1],(r.d[1]+other)&65535U);return am_return(c);

    // ---- 4bfa4: BSR.W 4bc44; BSR.W 4c020; BSR.W 4bb22; BRA.W 4bf0a.
    case 0x4bfa4:return am_call(c,0x4bc44,0x4bfa8);
    case 0x4bfa8:return am_call(c,0x4c020,0x4bfac);
    case 0x4bfac:return am_call(c,0x4bb22,0x4bfb0);
    case 0x4bfb0:r.pc=0x4bf0a;return true;
    // ---- 4c020: MOVE.B #ff,549d(A5); MOVE.L 64(A6),D0; MOVE.B 6f(A6),D1; LSL.W #8,D1; JSR 443ea.L.
    case 0x4c020:
        if(!ou17_put(c,r.a[5],0x549d,1,0xff) || !ou17_get(c,r.a[6],0x64,4,value) || !ou17_get(c,r.a[6],0x6f,1,other))return false;
        r.d[0]=value;am_byte(r.d[1],other);am_word(r.d[1],(r.d[1]<<8)&65535U);return am_call(c,0x443ea,0x4c036);
    // MOVE.L D0,D3; MOVE.L D1,D2; NEG.L D3; CMPI.B #8,6e(A6); BNE.W 4c060.
    case 0x4c036:
        r.d[3]=(0U-r.d[0])&0xffffffffU;r.d[2]=r.d[1];if(!ou17_get(c,r.a[6],0x6e,1,value))return false;
        r.pc=(value&255U)!=8U?0x4c060:0x4c046;return true;
    // MOVE.L 36(A6),D0; MOVE.L 3a(A6),D1; SUBI.L #5000,D1; SUB.L D0,D2; SUB.L D1,D3; ASR.L #5,D2; ASR.L #5,D3; ADD.L D0,D2; ADD.L D1,D3.
    case 0x4c046:
        if(!ou17_get(c,r.a[6],0x36,4,value) || !ou17_get(c,r.a[6],0x3a,4,other))return false;
        r.d[0]=value;r.d[1]=(other-0x5000U)&0xffffffffU;
        r.d[2]=ou17_asr((r.d[2]-r.d[0])&0xffffffffU,5);r.d[3]=ou17_asr((r.d[3]-r.d[1])&0xffffffffU,5);
        r.d[2]=(r.d[2]+r.d[0])&0xffffffffU;r.d[3]=(r.d[3]+r.d[1])&0xffffffffU;r.pc=0x4c060;return true;
    // MOVEM.L 2e(A6),D0-D1; MOVEA.L 3e(A6),A0; RTS.
    case 0x4c060:
        if(!ou17_get(c,r.a[6],0x2e,4,value) || !ou17_get(c,r.a[6],0x32,4,other))return false;r.d[0]=value;r.d[1]=other;
        if(!ou17_get(c,r.a[6],0x3e,4,value))return false;r.a[0]=value;return am_return(c);

    // ---- bbf56 (callback): CLR.L 36(A6); CLR.L 3a(A6); JSR 48296.L.
    case 0xbbf56:if(!ou17_put(c,r.a[6],0x36,4,0) || !ou17_put(c,r.a[6],0x3a,4,0))return false;return am_call(c,0x48296,0xbbf64);
    // MOVE.W #1e,76(A6); MOVE.L #bbf70,(A6).
    case 0xbbf64:if(!ou17_put(c,r.a[6],0x76,2,0x1e))return false;return ou17_install(c,0xbbf70,0xbbf70);
    // bbf70 (installed callback): SUBQ.W #1,76(A6); BCC.W bbf7e (borrow: the WORD was 0).
    case 0xbbf70:
        if(!ou17_get(c,r.a[6],0x76,2,value) || !ou17_put(c,r.a[6],0x76,2,(value-1U)&65535U))return false;
        r.pc=value==0U?0xbbf78:0xbbf7e;return true;
    case 0xbbf78:return ou17_install(c,0xbbf80,0xbbf7e);                    // MOVE.L #bbf80,(A6).
    // bbf80 (installed callback): BSET.B #0,15(A6); MOVE.W #4f,D0; MOVE.W #35,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xbbf80:
        if(!ou17_bit(c,r.a[6],0x15,0,true))return false;am_word(r.d[0],0x4f);am_word(r.d[1],0x35);am_byte(r.d[2],0);
        return am_call(c,0xc6a96,0xbbf98);
    case 0xbbf98:return ou17_animation(c,0xe3,OU17_BANK_RISE,0xd4,0xbbfc0);  // animation e3, bank LONG 200140, + d4.
    // MOVE.W #8838,68(A6); MOVE.W #8838,1e(A6); MOVE.L #bbfd2,(A6).
    case 0xbbfc0:if(!ou17_height(c,0x8838))return false;return ou17_install(c,0xbbfd2,0xbbfd2);
    // bbfd2 (installed callback): CLR.L 36(A6); ADDI.L #ffffb000,3a(A6); JSR 4be34.L.
    case 0xbbfd2:
        if(!ou17_put(c,r.a[6],0x36,4,0) || !ou17_get(c,r.a[6],0x3a,4,value) || !ou17_put(c,r.a[6],0x3a,4,(value+0xffffb000U)&0xffffffffU))
            return false;
        return am_call(c,0x4be34,0xbbfe4);
    // BTST.B #7,15(A6); BEQ.W bc018.
    case 0xbbfe4:if(!ou17_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&0x80U)==0U?0xbc018:0xbbfee;return true;
    case 0xbbfee:am_word(r.d[0],0x186a);return am_call(c,0x3af8,0xbbff8);    // MOVE.W #186a,D0; JSR 3af8.L.
    // MOVE.L 3a(A6),D0; ASR.L #2,D0; SUB.L D0,3a(A6); NEG.L 3a(A6); CMPI.L #8000,3a(A6); BGE.W bc018.
    case 0xbbff8:
        if(!ou17_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ou17_asr(value,2);
        value=(0U-((value-r.d[0])&0xffffffffU))&0xffffffffU;if(!ou17_put(c,r.a[6],0x3a,4,value))return false;
        r.pc=ou17_long_ge(value,0x8000U)?0xbc018:0xbc012;return true;
    case 0xbc012:return ou17_install(c,0xbc020,0xbc018);                    // MOVE.L #bc020,(A6).
    case 0xbc018:return am_call(c,0x49fc6,0xbc01e);                         // JSR 49fc6.L.
    // bc020 (installed callback): MOVE.L #a00000,2e(A6); MOVE.W #e3,20(A6); MOVEA.L #bcb32,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0xbc020:
        if(!ou17_put(c,r.a[6],0x2e,4,0xa00000) || !ou17_put(c,r.a[6],0x20,2,0xe3))return false;r.a[1]=0xbcb32;am_word(r.d[0],0x100);
        return am_call(c,0x49f8c,0xbc03e);
    case 0xbc03e:return ou17_install(c,0xbc044,0xbc044);                    // MOVE.L #bc044,(A6).
    // bc044 (installed callback): CLR.L 36(A6); JSR 4be2c.L (U18 boundary).
    case 0xbc044:if(!ou17_put(c,r.a[6],0x36,4,0))return false;return am_call(c,0x4be2c,0xbc04e);
    case 0xbc04e:return am_call(c,0x49fc6,0xbc054);                         // JSR 49fc6.L.
    case 0xbc054:return ou17_consume(c,false,0xbc05e,0xbc058);              // BCC.W bc05e (C returned by 49fc6).
    case 0xbc058:return ou17_install(c,0xbc060,0xbc05e);                    // MOVE.L #bc060,(A6).
    case 0xbc060:return ou17_child(c,0xbc08c,0x14,0xbc070);                 // (installed callback) MOVEA.L #bc08c,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0xbc070:return ou17_install(c,0xbc076,0xbc076);                    // MOVE.L #bc076,(A6).
    case 0xbc076:return am_call(c,0x43e34,0xbc07c);                         // (installed callback) JSR 43e34.L.
    case 0xbc07c:if(!ou17_get(c,r.a[6],0x62,1,value))return false;r.pc=(value&255U)!=0U?0xbc08a:0xbc084;return true; // TST.B 62(A6); BNE.W bc08a.
    case 0xbc084:return am_call(c,0x49fc6,0xbc08a);                         // JSR 49fc6.L.

    // ---- c3d60 (callback): JSR ca48.L; JSR 48296.L.
    case 0xc3d60:return am_call(c,0xca48,0xc3d66);
    case 0xc3d66:return am_call(c,0x48296,0xc3d6c);
    // MOVE.W #8810,68(A6); MOVE.W #8810,1e(A6); MOVE.W #cd8,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xc3d6c:if(!ou17_height(c,0x8810))return false;return ou17_palette(c,0xcd8,0xc3d86);
    case 0xc3d86:return ou17_palette(c,0xce4,0xc3d94);                      // MOVE.W #ce4,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xc3d94:if(!ou17_copy_frame(c))return false;return am_call(c,0x4c0ac,0xc3da0); // MOVE.B 19(A6),14(A6); JSR 4c0ac.L.
    case 0xc3da0:return ou17_child(c,0xc3f92,0xa,0xc3db0);                  // MOVEA.L #c3f92,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0xc3db0:if(!ou17_get(c,r.a[6],0x76,2,value))return false;r.pc=(value&65535U)!=0U?0xc3dbc:0xc3db8;return true; // TST.W 76(A6); BNE.W c3dbc.
    case 0xc3db8:r.pc=0xc3e38;return true;                                  // BRA.W c3e38.
    case 0xc3dbc:return ou17_animation(c,0xca,OU17_BANK_SHOW,0x64,0xc3de4);   // animation ca, bank LONG 200088, + 64.
    // MOVE.L #20000,64(A6); MOVE.L #c3df2,(A6).
    case 0xc3de4:if(!ou17_put(c,r.a[6],0x64,4,0x20000))return false;return ou17_install(c,0xc3df2,0xc3df2);
    case 0xc3df2:return am_call(c,0x4bfa4,0xc3df8);                         // (installed callback) JSR 4bfa4.L.
    case 0xc3df8:return ou17_focus(c,0xc3e0a);
    // MOVE.W 76(A6),D0; MOVEQ #0,D1; JSR 4929e.L.
    case 0xc3e0a:if(!ou17_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.d[1]=0;return am_call(c,0x4929e,0xc3e16);
    // CMP.W 42(A6),D0; BGT.W c3e24.
    case 0xc3e16:if(!ou17_get(c,r.a[6],0x42,2,value))return false;r.pc=ou17_word_gt(r.d[0],value)?0xc3e24:0xc3e1e;return true;
    case 0xc3e1e:return ou17_install(c,0xc3e38,0xc3e24);                    // MOVE.L #c3e38,(A6).
    case 0xc3e24:return ou17_table(c,0xc3c1c,0xc3e36,0xc3e30);              // LEA c3c1c(PC),A0; CMPA.W #0,A0; BEQ.W c3e36.
    case 0xc3e30:case 0xc3eb8:return am_call(c,0x4706c,r.pc==0xc3e30?0xc3e36:0xc3ebe); // JSR 4706c.L.
    case 0xc3f00:return am_call(c,0x4706c,0xc3f06);
    case 0xc3fcc:return am_call(c,0x4706c,0xc3fd2);
    case 0xc3e38:am_word(r.d[0],0x185c);return am_call(c,0x3af8,0xc3e42);    // (installed callback) MOVE.W #185c,D0; JSR 3af8.L.
    case 0xc3e42:return ou17_animation(c,0xca,OU17_BANK_SHOW,0x68,0xc3e6a);   // animation ca, bank LONG 200088, + 68.
    case 0xc3e6a:return ou17_install(c,0xc3e70,0xc3e70);                    // MOVE.L #c3e70,(A6).
    case 0xc3e70:return am_call(c,0x4be06,0xc3e76);                         // (installed callback) JSR 4be06.L.
    case 0xc3e76:return ou17_focus(c,0xc3e88);
    case 0xc3e88:return ou17_consume(c,false,0xc3eac,0xc3e8c);              // BCC.W c3eac (C returned by 49fc6).
    case 0xc3e8c:am_word(r.d[0],0x1821);return am_call(c,0x3af8,0xc3e96);    // MOVE.W #1821,D0; JSR 3af8.L.
    case 0xc3e96:return ou17_child(c,0xc3f08,0xa,0xc3ea6);                  // MOVEA.L #c3f08,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0xc3ea6:return ou17_install(c,0xc3ec0,0xc3eac);                    // MOVE.L #c3ec0,(A6).
    case 0xc3eac:return ou17_table(c,0xc3c1c,0xc3ebe,0xc3eb8);              // LEA c3c1c(PC),A0; CMPA.W #0,A0; BEQ.W c3ebe.
    case 0xc3ec0:return am_call(c,0x482c0,0xc3ec6);                         // (installed callback) JSR 482c0.L.
    // MOVE.W 42(A6),5d3e(A5); MOVE.W 46(A6),5d40(A5); ST.B 5d44(A5); MOVE.L #c3edc,(A6).
    case 0xc3ec6:
        if(!ou17_get(c,r.a[6],0x42,2,value) || !ou17_put(c,r.a[5],0x5d3e,2,value))return false;
        if(!ou17_get(c,r.a[6],0x46,2,value) || !ou17_put(c,r.a[5],0x5d40,2,value) || !ou17_put(c,r.a[5],0x5d44,1,0xff))return false;
        return ou17_install(c,0xc3edc,0xc3edc);
    case 0xc3edc:return am_call(c,0x4be06,0xc3ee2);                         // (installed callback) JSR 4be06.L.
    case 0xc3ee2:return ou17_focus(c,0xc3ef4);
    case 0xc3ef4:return ou17_table(c,0xc3c96,0xc3f06,0xc3f00);              // LEA c3c96(PC),A0; CMPA.W #0,A0; BEQ.W c3f06.
    case 0xc3f08:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0xc3f12);        // (child) MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.L.
    case 0xc3f12:return am_call(c,0x491c4,0xc3f18);                         // JSR 491c4.L.
    // MOVE.W #fff1,68(A6); MOVE.W #fff1,1e(A6); MOVE.W #cd8,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xc3f18:if(!ou17_height(c,0xfff1))return false;return ou17_palette(c,0xcd8,0xc3f32);
    case 0xc3f32:return ou17_palette(c,0xce4,0xc3f40);                      // MOVE.W #ce4,D0; MOVE.B #0,D1; JSR 8ebe.L.
    // MOVE.B 19(A6),14(A6); then animation ca, bank LONG 200088, + 6c.
    case 0xc3f40:if(!ou17_copy_frame(c))return false;return ou17_animation(c,0xca,OU17_BANK_SHOW,0x6c,0xc3f6e);
    case 0xc3f6e:return ou17_install(c,0xc3f74,0xc3f74);                    // MOVE.L #c3f74,(A6).
    case 0xc3f74:return am_call(c,0x43e34,0xc3f7a);                         // (installed callback) JSR 43e34.L.
    case 0xc3f7a:return am_call(c,0x49fc6,0xc3f80);                         // JSR 49fc6.L.
    case 0xc3f80:return am_call(c,0x288c,0xc3f86);                          // JSR 288c.L.
    case 0xc3f86:return ou17_consume(c,true,0xc3f90,0xc3f8a);               // BCS.W c3f90 (C returned by 288c).
    case 0xc3f8a:case 0xc3fba:r.pc=0x2a00;return true;                      // JMP 2a00.L.
    // c3f92 (child): MOVEQ #0,D0; MOVE.W #12,D1; JSR 49290.L.
    case 0xc3f92:r.d[0]=0;am_word(r.d[1],0x12);return am_call(c,0x49290,0xc3f9e);
    case 0xc3f9e:return am_call(c,0x491c4,0xc3fa4);                         // JSR 491c4.L.
    case 0xc3fa4:return ou17_install(c,0xc3faa,0xc3faa);                    // MOVE.L #c3faa,(A6).
    case 0xc3faa:return am_call(c,0x43e34,0xc3fb0);                         // (installed callback) JSR 43e34.L.
    case 0xc3fb0:return am_call(c,0x288c,0xc3fb6);                          // JSR 288c.L.
    case 0xc3fb6:return ou17_consume(c,true,0xc3fc0,0xc3fba);               // BCS.W c3fc0 (C returned by 288c).
    case 0xc3fc0:return ou17_table(c,0xc3d10,0xc3fd2,0xc3fcc);              // LEA c3d10(PC),A0; CMPA.W #0,A0; BEQ.W c3fd2.
    default:return am_error(c,"unsupported animation objects u17 PC");
    }
}
}
