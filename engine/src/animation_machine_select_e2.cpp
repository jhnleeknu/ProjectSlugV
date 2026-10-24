#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool se2_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool se2_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// The signed value of the low WORD (CMPI.W followed by BLE / BGT / BLT / BGE: the exact signed comparison; no C++ signed overflow).
std::int32_t se2_signed_word(std::uint32_t value) {
    return static_cast<std::int32_t>(value&0x7fffU)-static_cast<std::int32_t>(value&0x8000U);
}
// MOVE.W #v,d16(A6) for the WORD fields of the node.
bool se2_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value) {
    return se2_put(c,c.s.a[6],displacement,2,value);
}
// SUBQ.W #1,d16(A6): the new WORD (the old one through old).
bool se2_decrement(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t& old,std::uint32_t& now) {
    if(!se2_get(c,c.s.a[6],displacement,2,old))return false;now=(old-1U)&0xffffU;return se2_put(c,c.s.a[6],displacement,2,now);
}
// BCC / BCS on the known C returned to the block: clear -> clear_pc, set -> set_pc; Unknown is a checked error.
bool se2_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"select e2 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #value,(A6) followed by next_pc (the value is entered only when it is next_pc).
bool se2_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!se2_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// MOVEA.L 7a(A6),A0; SUBA.W #4,A0 (the score LONG in front of the name buffer); CMPA.L #10de14,A0 / CMPA.L #10de1c,A0 decide the BYTE
// 5e12(A5) / 5e13(A5) writes (the caller tests the two compares one after the other).
bool se2_record(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!se2_get(c,c.s.a[6],0x7a,4,value))return false;c.s.a[0]=value-4U;return true;
}
// MOVEA.L 7a(A6),A3; MOVE.W 80(A6),D5 (the name buffer and the cursor column).
bool se2_cursor(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!se2_get(c,r.a[6],0x7a,4,value))return false;r.a[3]=value;if(!se2_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[5],value);return true;
}
// MOVE.B (An,Dn.W),(A3,D5.W) with source = table + sext(index.W) + source_d8 (LEA e6e06(PC),A4 before; the character table e6e06 is fixed ROM,
// read through the live bus without a limit test) and destination = A3 + sext(D5.W).
bool se2_store_char(AnimationMachineContext& c,std::uint32_t index,std::uint32_t source_d8) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,am_index(r.a[4],index&0xffffU)+source_d8,1,value))return false;return am_write(c,am_index(r.a[3],r.d[5]&0xffffU),1,value);
}
// MOVE.B (A0)+,D2; JSR e84c8.l (one character of the text at A0).
bool se2_text(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[2],value);r.a[0]+=1U;
    return am_call(c,0xe84c8,return_pc);
}
// MOVE.W #ff,D1; MOVEQ #d2,D2; MOVEQ #2,D3 (then JSR / JMP 35a2.l: the caller sets the PC).
void se2_box(AnimationMachineContext& c,std::uint32_t d2) {
    am_word(c.s.d[1],0xff);c.s.d[2]=d2;c.s.d[3]=2;
}
}
// Select E2 (129 block starts, contract docs/analysis/animation-machine-select-e2-contract.md, area C plan 10.5 E2 row): the area-E name entry that the
// extended-input IO observation reaches after the last life [I] -- the 28ae child e695a of the player C6 block 4ed7c (CLR.B 8c(A6); the score record
// 10de14 / 10de1c in front of the name buffer LONG 7a(A6) sets BYTE 5e12 / 5e13(A5); the default name e6e28 copied by e63ec; the cursor search e6d66;
// the WORD 104cd2 write 3144), its entry e695e (the BRA.W of the unrouted 28ae child e6952 of the FR2 block e693a lands there: a block start), the
// callback e69c0 (4836e C: wait; the input BYTE 3(A0) of the player input record e6dc8 (-3358 / -3352(A5)) bit 4 = enter (e6c26: C set -> the end),
// bit 5 = back (e6c96), the new-press BYTE of e6d8a (-3354 / -334e(A5)) bit 3 / 2 = next / previous character (e6cea / e6d2e), the blink count WORD
// 84, the time-outs WORD 88 / 8a), the rank and name redraw e6a4c (the rank text table e637a by e6496 - 1 or WORD 7e, the name characters, the
// cursor e6e30 and the end mark e6e25 / 35a2 box, MOVEM.L D0-D1/D7/A0), the end e6b24 (the bad-name list e6e32 compared by e63fa (C set: equal) and
// replaced by e6e2c, the 7f -> space pass e6416, the 35a2 box, the installs e6ba0 (blink) / e6bea (wait, then BYTE 62 of the parent c(A6), clear 5e12
// / 5e13, JMP 2a00)), and the two player selectors e6d8a / e6dc8 (D0.W > 1 signed: the TRAP #15 e6d92 / e6dd0 boundary, outside the unit).  ROM
// data read through the live bus: the character table e6e06, the texts e6e25 e6e28 e6e2c e6e30, the LONG tables e637a / e6e32 and their texts.
// The C consumers e69c6 (BCC, 4836e), e69e8 (BCS, e6c26: e6c44 / e6c68 Set, e6c90 Clear) and e6b64 (BCC, e63fa: e640a Set, e6410 Clear) read a known C
// or fail.  No Z / N crosses a block boundary.
bool animation_select_e2_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t old=0;std::uint32_t now=0;
    switch(r.pc) {
    case 0xe6430:case 0xe6446:case 0xe69ca:case 0xe6b22:case 0xe6c24:case 0xe6cf4:case 0xe6d38:return am_return(c);   // RTS.
    // ---- 3144: MOVE.W D0,104cd2.l; RTS.
    case 0x3144:if(!am_write(c,0x104cd2,2,r.d[0]&0xffffU))return false;return am_return(c);
    // ---- e63fa (compare D0.W bytes): SUBQ.W #1,D0; BCS.W e640a (borrow: D0.W was 0).
    case 0xe63fa:old=r.d[0]&0xffffU;am_word(r.d[0],old-1U);r.pc=old==0U?0xe640a:0xe6400;return true;
    // CMPM.B (A0)+,(A1)+; BNE.W e6410 (the BYTEs differ).
    case 0xe6400:
        if(!am_read(c,r.a[0],1,value) || !am_read(c,r.a[1],1,now))return false;r.a[0]+=1U;r.a[1]+=1U;r.pc=value!=now?0xe6410:0xe6406;return true;
    // DBRA D0,e6400 (D0.W decremented; ffff ends the loop).
    case 0xe6406:am_word(r.d[0],r.d[0]-1U);r.pc=(r.d[0]&0xffffU)!=0xffffU?0xe6400:0xe640a;return true;
    case 0xe640a:r.carry=AnimationCarrySet;return am_return(c);                                       // ORI.B #1,CCR; RTS (equal).
    case 0xe6410:r.carry=AnimationCarryClear;return am_return(c);                                     // ANDI.B #fe,CCR; RTS (different).
    // ---- e6416 (7f -> space over 3 BYTEs at A0): MOVE.W #2,D7.
    case 0xe6416:am_word(r.d[7],2);r.pc=0xe641a;return true;
    case 0xe641a:if(!am_read(c,r.a[0],1,value))return false;r.pc=value==0x7fU?0xe6422:0xe6426;return true;   // CMPI.B #7f,(A0); BNE.W e6426.
    case 0xe6422:if(!am_write(c,r.a[0],1,0x20))return false;r.pc=0xe6426;return true;               // MOVE.B #20,(A0).
    // ADDA.L #1,A0; DBRA D7,e641a.
    case 0xe6426:r.a[0]+=1U;am_word(r.d[7],r.d[7]-1U);r.pc=(r.d[7]&0xffffU)!=0xffffU?0xe641a:0xe6430;return true;
    // ---- e6432: TST.B 8d(A6); BNE.W e6446 / LEA e6e2c(PC),A0; MOVE.W #3,D0; JSR e63ec(PC) (the name "SNK").
    case 0xe6432:if(!se2_get(c,r.a[6],0x8d,1,value))return false;r.pc=value!=0U?0xe6446:0xe643a;return true;
    case 0xe643a:r.a[0]=0xe6e2c;am_word(r.d[0],3);return am_call(c,0xe63ec,0xe6446);
    // ---- e695a (the 28ae child of C6 4ed7c): CLR.B 8c(A6) -> e695e (also the BRA.W target of the 28ae child e6952).
    case 0xe695a:if(!se2_put(c,r.a[6],0x8c,1,0))return false;r.pc=0xe695e;return true;
    // MOVEA.L 7a(A6),A0; SUBA.W #4,A0; CMPA.L #10de14,A0; BNE.W e6974.
    case 0xe695e:if(!se2_record(c))return false;r.pc=r.a[0]==0x10de14U?0xe6970:0xe6974;return true;
    case 0xe6970:if(!se2_put(c,r.a[5],0x5e12,1,0xff))return false;r.pc=0xe6974;return true;          // ST.B 5e12(A5).
    case 0xe6974:r.pc=r.a[0]==0x10de1cU?0xe697e:0xe6982;return true;                                 // CMPA.L #10de1c,A0; BNE.W e6982.
    case 0xe697e:if(!se2_put(c,r.a[5],0x5e13,1,0xff))return false;r.pc=0xe6982;return true;          // ST.B 5e13(A5).
    // CLR.W 80(A6); MOVEA.L 7a(A6),A1; LEA e6e28(PC),A0; MOVE.W #3,D0; JSR e63ec(PC) (the default name "A  ").
    case 0xe6982:
        if(!se2_word(c,0x80,0) || !se2_get(c,r.a[6],0x7a,4,value))return false;r.a[1]=value;r.a[0]=0xe6e28;am_word(r.d[0],3);
        return am_call(c,0xe63ec,0xe6996);
    case 0xe6996:return am_call(c,0xe6d66,0xe699a);                                                   // JSR e6d66(PC).
    case 0xe699a:if(!se2_word(c,0x84,0xf))return false;am_word(r.d[0],0x2004);return am_call(c,0x3144,0xe69aa);   // MOVE.W #f,84; #2004,D0; JSR 3144.l.
    // MOVE.W #258,88(A6); MOVE.W #12c,8a(A6); CLR.B 8d(A6); MOVE.L #e69c0,(A6) (next PC).
    case 0xe69aa:
        if(!se2_word(c,0x88,0x258) || !se2_word(c,0x8a,0x12c) || !se2_put(c,r.a[6],0x8d,1,0))return false;return se2_install(c,0xe69c0,0xe69c0);
    // ---- e69c0 (callback): JSR 4836e.l; BCC.W e69cc (C of 4836e) / RTS.
    case 0xe69c0:return am_call(c,0x4836e,0xe69c6);
    case 0xe69c6:return se2_carry(c,0xe69cc,0xe69ca);
    case 0xe69cc:if(!se2_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);return am_call(c,0xe6dc8,0xe69d4);   // MOVE.W 76,D0; JSR e6dc8.
    // MOVE.B 3(A0),D0; BTST #4,D0; BEQ.W e69fa.
    case 0xe69d4:if(!am_read(c,r.a[0]+3U,1,value))return false;am_byte(r.d[0],value);r.pc=(r.d[0]&0x10U)==0U?0xe69fa:0xe69e0;return true;
    case 0xe69e0:if(!se2_put(c,r.a[6],0x8d,1,0xff))return false;return am_call(c,0xe6c26,0xe69e8);   // ST.B 8d(A6); JSR e6c26(PC).
    case 0xe69e8:return se2_carry(c,0xe69ec,0xe6b24);                                                // BCS.W e6b24 (C of e6c26).
    case 0xe69ec:case 0xe6b24:am_word(r.d[0],r.pc==0xe69ecU?0x1a6cU:0x1a6dU);return am_call(c,0x3af8,r.pc+10U);   // MOVE.W #n,D0; JSR 3af8.l.
    case 0xe69f6:case 0xe6a06:case 0xe6a1e:r.pc=0xe6a2e;return true;                                 // BRA.W e6a2e.
    case 0xe69fa:r.pc=(r.d[0]&0x20U)==0U?0xe6a0a:0xe6a02;return true;                               // BTST #5,D0; BEQ.W e6a0a.
    case 0xe6a02:return am_call(c,0xe6c96,0xe6a06);                                                   // JSR e6c96(PC).
    case 0xe6a0a:if(!se2_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);return am_call(c,0xe6d8a,0xe6a12);   // MOVE.W 76,D0; JSR e6d8a.
    case 0xe6a12:r.pc=(r.d[0]&0x8U)==0U?0xe6a22:0xe6a1a;return true;                                // BTST #3,D0; BEQ.W e6a22.
    case 0xe6a1a:return am_call(c,0xe6cea,0xe6a1e);                                                   // JSR e6cea(PC).
    case 0xe6a22:r.pc=(r.d[0]&0x4U)==0U?0xe6a2e:0xe6a2a;return true;                                // BTST #2,D0; BEQ.W e6a2e.
    case 0xe6a2a:return am_call(c,0xe6d2e,0xe6a2e);                                                   // JSR e6d2e(PC).
    case 0xe6a2e:if(!se2_decrement(c,0x84,old,now))return false;r.pc=now!=0U?0xe6a3c:0xe6a36;return true;   // SUBQ.W #1,84(A6); BNE.W e6a3c.
    case 0xe6a36:if(!se2_word(c,0x84,0xf))return false;r.pc=0xe6a3c;return true;                    // MOVE.W #f,84(A6).
    case 0xe6a3c:if(!se2_decrement(c,0x88,old,now))return false;r.pc=now==0U?0xe6b24:0xe6a44;return true;   // SUBQ.W #1,88(A6); BEQ.W e6b24.
    case 0xe6a44:if(!se2_decrement(c,0x8a,old,now))return false;r.pc=now==0U?0xe6b24:0xe6a4c;return true;   // SUBQ.W #1,8a(A6); BEQ.W e6b24.
    // ---- e6a4c (rank and name redraw): TST.B 8c(A6); BNE.W e6a66.
    case 0xe6a4c:if(!se2_get(c,r.a[6],0x8c,1,value))return false;r.pc=value!=0U?0xe6a66:0xe6a54;return true;
    case 0xe6a54:if(!se2_record(c))return false;return am_call(c,0xe6496,0xe6a60);                  // MOVEA.L 7a,A0; SUBA.W #4,A0; JSR e6496(PC).
    case 0xe6a60:am_word(r.d[0],r.d[0]-1U);r.pc=0xe6a6a;return true;                                // SUBQ.W #1,D0; BRA.W e6a6a.
    case 0xe6a66:if(!se2_get(c,r.a[6],0x7e,2,value))return false;am_word(r.d[0],value);r.pc=0xe6a6a;return true;   // MOVE.W 7e(A6),D0.
    // ADD.W D0,D0; ADD.W D0,D0; LEA e637a(PC),A4; MOVEA.L (A4,D0.W),A0; MOVE.W 78(A6),D0; MOVE.W #441,D1; MOVE.B (A0)+,D2; JSR e84c8.l.
    case 0xe6a6a:
        am_word(r.d[0],r.d[0]<<2);r.a[4]=0xe637a;if(!am_read(c,am_index(r.a[4],r.d[0]&0xffffU),4,value))return false;r.a[0]=value;
        if(!se2_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],0x441);return se2_text(c,0xe6a86);
    case 0xe6a86:am_word(r.d[1],3);am_word(r.d[0],r.d[0]+1U);return se2_text(c,0xe6a96);            // MOVE.W #3,D1; ADDI.W #1,D0; text.
    case 0xe6a96:return se2_text(c,0xe6a9e);
    case 0xe6a9e:return se2_text(c,0xe6aa6);
    // MOVE.W 78(A6),D0; ADDI.W #a0,D0; MOVE.W #441,D1; MOVEA.L 7a(A6),A0; MOVEQ #0,D7.
    case 0xe6aa6:
        if(!se2_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value+0xa0U);am_word(r.d[1],0x441);
        if(!se2_get(c,r.a[6],0x7a,4,value))return false;r.a[0]=value;r.d[7]=0;r.pc=0xe6ab8;return true;
    // MOVE.B (A0)+,D2; CMP.W 80(A6),D7; BNE.W e6ae8.
    case 0xe6ab8:
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[2],value);r.a[0]+=1U;if(!se2_get(c,r.a[6],0x80,2,value))return false;
        r.pc=(r.d[7]&0xffffU)!=value?0xe6ae8:0xe6ac2;return true;
    // CMPI.W #7,84(A6); BGT.W e6ae8 (signed WORD).
    case 0xe6ac2:if(!se2_get(c,r.a[6],0x84,2,value))return false;r.pc=se2_signed_word(value)>7?0xe6ae8:0xe6acc;return true;
    // MOVEM.L D0-D1/D7/A0,-(A7) (A0 at the highest LONG, D0 at the lowest); LEA e6e30(PC),A0; MOVE.B (A0)+,D2; JSR e84c8.l (the cursor).
    case 0xe6acc:
        if(!am_push(c,4,r.a[0]) || !am_push(c,4,r.d[7]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;r.a[0]=0xe6e30;
        return se2_text(c,0xe6adc);
    // MOVEM.L (A7)+,D0-D1/D7/A0; ADDI.W #40,D0; BRA.W e6b1a.
    case 0xe6adc:
        if(!am_pop(c,4,r.d[0]) || !am_pop(c,4,r.d[1]) || !am_pop(c,4,r.d[7]) || !am_pop(c,4,r.a[0]))return false;am_word(r.d[0],r.d[0]+0x40U);
        r.pc=0xe6b1a;return true;
    case 0xe6ae8:r.pc=(r.d[7]&0xffffU)!=3U?0xe6b14:0xe6af0;return true;                            // CMPI.W #3,D7; BNE.W e6b14.
    case 0xe6af0:if(!se2_get(c,r.a[6],0x80,2,value))return false;r.pc=value!=3U?0xe6b06:0xe6afa;return true;   // CMPI.W #3,80(A6); BNE.W e6b06.
    // LEA e6e25(PC),A0; MOVE.B (A0)+,D2; JMP e84c8.l (the end mark; e84c8 returns to the caller of e6a4c).
    case 0xe6afa:if(!am_read(c,0xe6e25,1,value))return false;am_byte(r.d[2],value);r.a[0]=0xe6e26;r.pc=0xe84c8;return true;
    case 0xe6b06:se2_box(c,2);return am_call(c,0x35a2,0xe6b14);                                     // MOVE.W #ff,D1; MOVEQ #2,D2; MOVEQ #2,D3; JSR 35a2.l.
    case 0xe6b14:return am_call(c,0xe84c8,0xe6b1a);                                                   // JSR e84c8.l.
    // ADDQ.W #1,D7; CMPI.W #3,D7; BLE.B e6ab8 (signed WORD).
    case 0xe6b1a:am_word(r.d[7],r.d[7]+1U);r.pc=se2_signed_word(r.d[7])<=3?0xe6ab8:0xe6b22;return true;
    // ---- e6b2e (the end): MOVE.W #ffff,80(A6); CLR.W 84(A6); MOVE.W #3c,86(A6); MOVEA.L 7a(A6),A1; JSR e6432(PC).
    case 0xe6b2e:
        if(!se2_word(c,0x80,0xffff) || !se2_word(c,0x84,0) || !se2_word(c,0x86,0x3c) || !se2_get(c,r.a[6],0x7a,4,value))return false;r.a[1]=value;
        return am_call(c,0xe6432,0xe6b46);
    case 0xe6b46:r.a[4]=0xe6e32;r.d[7]=0;r.pc=0xe6b4c;return true;                                  // LEA e6e32(PC),A4; MOVEQ #0,D7.
    // MOVEA.L (A4,D7.W),A0; CMPA.L #0,A0; BEQ.W e6b7c (the end of the bad-name list).
    case 0xe6b4c:if(!am_read(c,am_index(r.a[4],r.d[7]&0xffffU),4,value))return false;r.a[0]=value;r.pc=value==0U?0xe6b7c:0xe6b5a;return true;
    case 0xe6b5a:if(!se2_get(c,r.a[6],0x7a,4,value))return false;r.a[1]=value;r.d[0]=3;return am_call(c,0xe63fa,0xe6b64);   // MOVEQ #3,D0; JSR e63fa.
    case 0xe6b64:return se2_carry(c,0xe6b78,0xe6b68);                                                // BCC.W e6b78 (C of e63fa).
    // MOVEA.L 7a(A6),A1; LEA e6e2c(PC),A0; MOVE.W #3,D0; JSR e63ec(PC) (the name "SNK").
    case 0xe6b68:if(!se2_get(c,r.a[6],0x7a,4,value))return false;r.a[1]=value;r.a[0]=0xe6e2c;am_word(r.d[0],3);return am_call(c,0xe63ec,0xe6b78);
    case 0xe6b78:am_word(r.d[7],r.d[7]+4U);r.pc=0xe6b4c;return true;                               // ADDQ.W #4,D7; BRA.B e6b4c.
    case 0xe6b7c:if(!se2_get(c,r.a[6],0x7a,4,value))return false;r.a[0]=value;return am_call(c,0xe6416,0xe6b84);   // MOVEA.L 7a,A0; JSR e6416(PC).
    // MOVE.W 78(A6),D0; ADDI.W #a2,D0; MOVE.W #ff,D1; MOVEQ #8,D2; MOVEQ #2,D3; JSR 35a2.l.
    case 0xe6b84:if(!se2_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value+0xa2U);se2_box(c,8);return am_call(c,0x35a2,0xe6b9a);
    case 0xe6b9a:return se2_install(c,0xe6ba0,0xe6ba0);                                              // MOVE.L #e6ba0,(A6) (next PC).
    // ---- e6ba0 (callback, blink): SUBQ.W #1,86(A6); CMPI.W #24,86(A6); BLE.W e6be0 (signed WORD).
    case 0xe6ba0:if(!se2_decrement(c,0x86,old,now))return false;r.pc=se2_signed_word(now)<=0x24?0xe6be0:0xe6bae;return true;
    // ADDQ.W #1,84(A6); CMPI.W #6,84(A6); BLT.W e6bc0 (signed WORD).
    case 0xe6bae:
        if(!se2_get(c,r.a[6],0x84,2,value))return false;now=(value+1U)&0xffffU;if(!se2_word(c,0x84,now))return false;
        r.pc=se2_signed_word(now)<6?0xe6bc0:0xe6bbc;return true;
    case 0xe6bbc:if(!se2_word(c,0x84,0))return false;r.pc=0xe6bc0;return true;                     // CLR.W 84(A6).
    case 0xe6bc0:if(!se2_get(c,r.a[6],0x84,2,value))return false;r.pc=se2_signed_word(value)>=4?0xe6bce:0xe6bca;return true;   // CMPI.W #4; BGE.W e6bce.
    case 0xe6bca:r.pc=0xe6a4c;return true;                                                            // BRA.W e6a4c.
    // MOVE.W 78(A6),D0; MOVE.W #ff,D1; MOVEQ #b,D2; MOVEQ #2,D3; JMP 35a2.l.
    case 0xe6bce:if(!se2_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);se2_box(c,0xb);r.pc=0x35a2;return true;
    case 0xe6be0:return am_call(c,0xe6a4c,0xe6be4);                                                   // JSR e6a4c(PC).
    case 0xe6be4:return se2_install(c,0xe6bea,0xe6bea);                                              // MOVE.L #e6bea,(A6) (next PC).
    // ---- e6bea (callback, wait): SUBQ.W #1,86(A6); BCC.W e6c24 (no borrow: the old WORD was not 0).
    case 0xe6bea:if(!se2_decrement(c,0x86,old,now))return false;r.pc=old!=0U?0xe6c24:0xe6bf2;return true;
    // MOVEA.L c(A6),A0; ST.B 62(A0); MOVEA.L 7a(A6),A0; SUBA.W #4,A0; CMPA.L #10de14,A0; BNE.W e6c10.
    case 0xe6bf2:
        if(!se2_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!se2_put(c,r.a[0],0x62,1,0xff) || !se2_record(c))return false;
        r.pc=r.a[0]==0x10de14U?0xe6c0c:0xe6c10;return true;
    case 0xe6c0c:if(!se2_put(c,r.a[5],0x5e12,1,0))return false;r.pc=0xe6c10;return true;             // CLR.B 5e12(A5).
    case 0xe6c10:r.pc=r.a[0]==0x10de1cU?0xe6c1a:0xe6c1e;return true;                                 // CMPA.L #10de1c,A0; BNE.W e6c1e.
    case 0xe6c1a:if(!se2_put(c,r.a[5],0x5e13,1,0))return false;r.pc=0xe6c1e;return true;             // CLR.B 5e13(A5).
    case 0xe6c1e:r.pc=0x2a00;return true;                                                             // JMP 2a00.l.
    // ---- e6c26 (enter): MOVE.W #f,84(A6); MOVE.W #12c,8a(A6); MOVE.W 82(A6),D7; LEA e6e06(PC),A4; CMPI.B #7f,(A4,D7.W); BNE.W e6c5a.
    case 0xe6c26:
        if(!se2_word(c,0x84,0xf) || !se2_word(c,0x8a,0x12c) || !se2_get(c,r.a[6],0x82,2,value))return false;am_word(r.d[7],value);r.a[4]=0xe6e06;
        if(!am_read(c,am_index(r.a[4],r.d[7]&0xffffU),1,value))return false;r.pc=value!=0x7fU?0xe6c5a:0xe6c44;return true;
    // CLR.W 82(A6); MOVEA.L 7a(A6),A3; MOVE.W 80(A6),D5; MOVE.B (A4),(A3,D5.W); ORI.B #1,CCR; RTS (the end mark chosen).
    case 0xe6c44:
        if(!se2_word(c,0x82,0) || !se2_cursor(c) || !se2_store_char(c,0,0))return false;r.carry=AnimationCarrySet;return am_return(c);
    // ADDQ.W #1,80(A6); CMPI.W #3,80(A6); BLE.W e6c6e (signed WORD).
    case 0xe6c5a:
        if(!se2_get(c,r.a[6],0x80,2,value))return false;now=(value+1U)&0xffffU;if(!se2_word(c,0x80,now))return false;
        r.pc=se2_signed_word(now)<=3?0xe6c6e:0xe6c68;return true;
    case 0xe6c68:r.carry=AnimationCarrySet;return am_return(c);                                       // ORI.B #1,CCR; RTS (past the last column).
    case 0xe6c6e:if(!se2_get(c,r.a[6],0x80,2,value))return false;r.pc=value==3U?0xe6c90:0xe6c78;return true;   // CMPI.W #3,80(A6); BEQ.W e6c90.
    case 0xe6c78:if(!se2_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[5],value);r.pc=value==0U?0xe6c8c:0xe6c80;return true;   // MOVE.W 80,D5; BEQ.
    // MOVEA.L 7a(A6),A3; SUBQ.W #1,D5; MOVE.B (A3,D5.W),1(A3,D5.W) (the previous character carried into the new column).
    case 0xe6c80:
        if(!se2_get(c,r.a[6],0x7a,4,value))return false;r.a[3]=value;am_word(r.d[5],r.d[5]-1U);
        if(!am_read(c,am_index(r.a[3],r.d[5]&0xffffU),1,value))return false;if(!am_write(c,am_index(r.a[3],r.d[5]&0xffffU)+1U,1,value))return false;
        r.pc=0xe6c8c;return true;
    case 0xe6c8c:return am_call(c,0xe6d66,0xe6c90);                                                   // JSR e6d66(PC).
    case 0xe6c90:r.carry=AnimationCarryClear;return am_return(c);                                     // ANDI.B #fe,CCR; RTS.
    // ---- e6c96 (back): MOVE.W #f,84(A6); MOVE.W #12c,8a(A6); CMPI.W #3,80(A6); BEQ.W e6cbc.
    case 0xe6c96:
        if(!se2_word(c,0x84,0xf) || !se2_word(c,0x8a,0x12c) || !se2_get(c,r.a[6],0x80,2,value))return false;r.pc=value==3U?0xe6cbc:0xe6cac;return true;
    // LEA e6e06(PC),A4; MOVEA.L 7a(A6),A3; MOVE.W 80(A6),D5; MOVE.B (A4),(A3,D5.W).
    case 0xe6cac:r.a[4]=0xe6e06;if(!se2_cursor(c) || !se2_store_char(c,0,0))return false;r.pc=0xe6cbc;return true;
    case 0xe6cbc:if(!se2_decrement(c,0x80,old,now))return false;r.pc=old!=0U?0xe6cda:0xe6cc4;return true;   // SUBQ.W #1,80(A6); BCC.W e6cda.
    // CLR.W 80(A6); LEA e6e06(PC),A4; MOVEA.L 7a(A6),A3; MOVE.W 80(A6),D5; MOVE.B 1(A4),(A3,D5.W).
    case 0xe6cc4:r.a[4]=0xe6e06;if(!se2_word(c,0x80,0) || !se2_cursor(c) || !se2_store_char(c,0,1))return false;r.pc=0xe6cda;return true;
    case 0xe6cda:if(!se2_get(c,r.a[6],0x80,2,value))return false;r.pc=value!=0U?0xe6ce6:0xe6ce2;return true;   // TST.W 80(A6); BNE.W e6ce6.
    case 0xe6ce2:if(!se2_put(c,r.a[6],0x8d,1,0))return false;r.pc=0xe6ce6;return true;             // CLR.B 8d(A6).
    case 0xe6ce6:r.pc=0xe6d66;return true;                                                            // BRA.W e6d66.
    // ---- e6cea (next character): CMPI.W #3,80(A6); BNE.W e6cf6 / RTS.
    case 0xe6cea:case 0xe6d2e:if(!se2_get(c,r.a[6],0x80,2,value))return false;r.pc=value!=3U?r.pc+12U:r.pc+10U;return true;
    // MOVE.W #f,84(A6); MOVE.W #12c,8a(A6); ADDQ.W #1,82(A6); MOVE.W 82(A6),D7; LEA e6e06(PC),A4; MOVE.B (A4,D7.W),D6; TST.B D6; BNE.W e6d1e.
    case 0xe6cf6:
        if(!se2_word(c,0x84,0xf) || !se2_word(c,0x8a,0x12c) || !se2_get(c,r.a[6],0x82,2,value))return false;value=(value+1U)&0xffffU;
        if(!se2_word(c,0x82,value))return false;am_word(r.d[7],value);r.a[4]=0xe6e06;
        if(!am_read(c,am_index(r.a[4],r.d[7]&0xffffU),1,value))return false;am_byte(r.d[6],value);r.pc=value!=0U?0xe6d1e:0xe6d18;return true;
    case 0xe6d18:if(!se2_word(c,0x82,0))return false;r.d[7]=0;r.pc=0xe6d1e;return true;            // CLR.W 82(A6); MOVEQ #0,D7.
    // MOVEA.L 7a(A6),A3; MOVE.W 80(A6),D5; MOVE.B (A4,D7.W),(A3,D5.W); RTS.
    case 0xe6d1e:case 0xe6d4e:
        if(r.pc==0xe6d4eU){if(!se2_get(c,r.a[6],0x82,2,value))return false;am_word(r.d[7],value);r.a[4]=0xe6e06;}   // MOVE.W 82,D7; LEA e6e06(PC),A4.
        if(!se2_cursor(c) || !se2_store_char(c,r.d[7],0))return false;return am_return(c);
    // ---- e6d3a (previous character): MOVE.W #12c,8a(A6); SUBQ.W #1,82(A6); BCC.W e6d4e.
    case 0xe6d3a:if(!se2_word(c,0x8a,0x12c) || !se2_decrement(c,0x82,old,now))return false;r.pc=old!=0U?0xe6d4e:0xe6d48;return true;
    case 0xe6d48:if(!se2_word(c,0x82,0x1f))return false;r.pc=0xe6d4e;return true;                  // MOVE.W #1f,82(A6).
    // ---- e6d66 (the cursor character index): MOVEA.L 7a(A6),A3; MOVE.W 80(A6),D5; MOVE.B (A3,D5.W),D7; LEA e6e06(PC),A4; MOVEQ #0,D6.
    case 0xe6d66:
        if(!se2_cursor(c) || !am_read(c,am_index(r.a[3],r.d[5]&0xffffU),1,value))return false;am_byte(r.d[7],value);r.a[4]=0xe6e06;r.d[6]=0;
        r.pc=0xe6d78;return true;
    // CMP.B (A4,D6.W),D7; BEQ.W e6d84.
    case 0xe6d78:if(!am_read(c,am_index(r.a[4],r.d[6]&0xffffU),1,value))return false;r.pc=(r.d[7]&0xffU)==value?0xe6d84:0xe6d80;return true;
    case 0xe6d80:am_word(r.d[6],r.d[6]+1U);r.pc=0xe6d78;return true;                               // ADDQ.W #1,D6; BRA.B e6d78.
    case 0xe6d84:if(!se2_word(c,0x82,r.d[6]))return false;return am_return(c);                      // MOVE.W D6,82(A6); RTS.
    // ---- e6d8a / e6dc8 (the player selectors): CMPI.W #1,D0; BLE.W e6db6 / e6df4 (signed WORD), above 1: the TRAP #15 boundary e6d92 / e6dd0.
    case 0xe6d8a:case 0xe6dc8:r.pc=se2_signed_word(r.d[0])<=1?r.pc+0x2cU:r.pc+8U;return true;
    case 0xe6db6:r.pc=(r.d[0]&0xffffU)!=0U?0xe6dc2:0xe6dbc;return true;                            // TST.W D0; BNE.W e6dc2.
    // MOVE.B -3354(A5),D0 / MOVE.B -334e(A5),D0; RTS (the new-press BYTEs of the two players).
    case 0xe6dbc:case 0xe6dc2:if(!se2_get(c,r.a[5],r.pc==0xe6dbcU?0xccacU:0xccb2U,1,value))return false;am_byte(r.d[0],value);return am_return(c);
    case 0xe6df4:r.pc=(r.d[0]&0xffffU)!=0U?0xe6e00:0xe6dfa;return true;                            // TST.W D0; BNE.W e6e00.
    // LEA -3358(A5),A0 / LEA -3352(A5),A0; RTS (the input records of the two players).
    case 0xe6dfa:case 0xe6e00:r.a[0]=am_index(r.a[5],r.pc==0xe6dfaU?0xcca8U:0xccaeU);return am_return(c);
    default:return am_error(c,"unsupported animation select e2 PC");
    }
}
}
