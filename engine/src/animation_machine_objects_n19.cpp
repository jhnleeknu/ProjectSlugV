#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// -7348(A5) / -7258(A5): the two player nodes (100cb8 / 100da8 with A5 = 108000).
const std::uint32_t ON19_PLAYER1=0x8cb8;
const std::uint32_t ON19_PLAYER2=0x8da8;
bool on19_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on19_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Two's complement WORD as a signed number (no signed overflow in C++).
int on19_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<int>(value)-65536:static_cast<int>(value);
}
// Bcc on a C returned by a callee: BCC goes to clear_pc, otherwise set_pc (BCS: the caller swaps the targets).
bool on19_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n19 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.L #target,(A6) then continue at next_pc.
bool on19_install(AnimationMachineContext& c,std::uint32_t target,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,target))return false;c.s.pc=next_pc;return true;
}
// MOVE.L #target,(A6); RTS.
bool on19_install_return(AnimationMachineContext& c,std::uint32_t target) {
    if(!am_write(c,c.s.a[6],4,target))return false;return am_return(c);
}
// BTST.B #bit,displacement(A6): true when the bit is set.
bool on19_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on19_get(c,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,displacement(A6) (set: true sets, false clears).
bool on19_bitop(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!on19_get(c,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;value=set?(value|mask):(value&~mask);return on19_put(c,displacement,1,value&255U);
}
// MOVE.W #value,displacement(A6).
bool on19_set_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value) {
    return on19_put(c,displacement,2,value&65535U);
}
// MOVE.W from_displacement(A6),to_displacement(A6).
bool on19_copy_word(AnimationMachineContext& c,std::uint32_t from_displacement,std::uint32_t to_displacement) {
    std::uint32_t value=0;return on19_get(c,from_displacement,2,value) && on19_set_word(c,to_displacement,value);
}
// MOVEA.L #record,A1; MOVE.W #100,D0; JSR 49f8c.L.
bool on19_animation(AnimationMachineContext& c,std::uint32_t record,std::uint32_t return_pc) {
    c.s.a[1]=record;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #value,D0; MOVE.B #0,D1; JSR 8ebe.L.
bool on19_sprite(AnimationMachineContext& c,std::uint32_t value,std::uint32_t return_pc) {
    am_word(c.s.d[0],value);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// NEG.W Dn.
void on19_neg_word(std::uint32_t& reg) {
    am_word(reg,(0U-reg)&65535U);
}
}
// Objects F4 N19 (210 block starts): the installed callback 86742 handed over by N18 (shared tail 8625a and helper 864b6 stay in N18),
// the b16ea family (stage event callback b16ea with the child generator b1d40 and the installed b16fc; 28ae children b175a (installed
// b17dc), b1842 (installed b188e, b192c, b1986) and b1b24 (installed b1b42); helpers b15e0 b160a b17f4 b182e b1b62 b1b76 b1b8c b1bc2 b1bf6
// b1c0e b1c4a b1cf8 b1d1e b1dae b1dfa b1fd6) and the stage event callback dbf5e. Boundaries without an executor: 44602 b43de b441e b1e2a
// b1e74 b1ecc b1ee6 b1f1a. The 14 BCC/BCS consumers read the C of 4b54e 287e 28ae 497a6 49fc6 4945e 1ab02 b1ee6 and of the N19 helpers
// b15e0 (b15fe ORI / b1604 ANDI before RTS), b1fd6 (4945e or b1ffc ANDI) and b1dfa (49fc6); b174c (ORI CCR) sets a known C. MOVEM.W
// (A7)+ sign-extends the WORDs into the full registers. N19 writes no port, changes no bank and reads no banked data.
bool animation_objects_n19_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool flag=false;
    switch(r.pc) {
    // ---- 86742 (installed by N18 86734): JSR 864b6(PC); JSR 4be06.L; JSR 49fc6.L.
    case 0x86742:return am_call(c,0x864b6,0x86746);
    case 0x86746:return am_call(c,0x4be06,0x8674c);
    case 0x8674c:return am_call(c,0x49fc6,0x86752);
    case 0x86752:if(!on19_get(c,0x85,1,value))return false;r.pc=(value&0x80U)?0x86800:0x8675a;return true; // TST.B 85(A6); BMI.W.
    case 0x8675a:if(!on19_bit(c,0x84,0,flag))return false;r.pc=flag?0x8676e:0x86764;return true; // BTST.B #0,84(A6); BNE.W 8676e.
    case 0x86764:return on19_install(c,0x86e76,0x86800);                   // MOVE.L #86e76,(A6); BRA.W 86800.
    case 0x8676e:if(!on19_get(c,0x85,1,value))return false;r.pc=(value&255U)!=0U?0x8677e:0x86776;return true; // TST.B 85(A6); BNE.W.
    case 0x86776:r.a[0]=am_index(r.a[5],ON19_PLAYER1);r.pc=0x86782;return true; // LEA -7348(A5),A0; BRA.W 86782.
    case 0x8677e:r.a[0]=am_index(r.a[5],ON19_PLAYER2);r.pc=0x86782;return true; // LEA -7258(A5),A0.
    // MOVE.W 42(A0),D0; SUB.W 42(A6),D0; BPL.W 86790.
    case 0x86782:
        if(!am_read(c,am_index(r.a[0],0x42),2,value))return false;am_word(r.d[0],value);if(!on19_get(c,0x42,2,value))return false;
        am_word(r.d[0],(r.d[0]-value)&65535U);r.pc=(r.d[0]&0x8000U)?0x8678e:0x86790;return true;
    case 0x8678e:on19_neg_word(r.d[0]);r.pc=0x86790;return true;          // NEG.W D0.
    // CMP.W 8c(A6),D0; BLE.W 867b2 (signed D0.W <= 8c.W).
    case 0x86790:
        if(!on19_get(c,0x8c,2,value))return false;r.pc=on19_signed_word(r.d[0])<=on19_signed_word(value)?0x867b2:0x86798;return true;
    case 0x86798:if(!on19_bit(c,0x84,7,flag))return false;r.pc=flag?0x867a2:0x867ac;return true; // BTST.B #7,84(A6); BEQ.W 867ac.
    case 0x867a2:return on19_install(c,0x86fca,0x867b2);                   // MOVE.L #86fca,(A6); BRA.W 867b2.
    case 0x867ac:return on19_install(c,0x8698c,0x867b2);                   // MOVE.L #8698c,(A6).
    case 0x867b2:r.pc=on19_signed_word(r.d[0])>=0x30?0x867e8:0x867ba;return true; // CMPI.W #30,D0; BGE.W 867e8 (signed).
    // MOVE.W #fff8,D0; BTST.B #0,15(A6); BNE.W 867ca.
    case 0x867ba:am_word(r.d[0],0xfff8);if(!on19_bit(c,0x15,0,flag))return false;r.pc=flag?0x867ca:0x867c8;return true;
    case 0x867c8:on19_neg_word(r.d[0]);r.pc=0x867ca;return true;          // NEG.W D0.
    case 0x867ca:return am_call(c,0x4c1de,0x867d0);
    case 0x867d0:r.pc=(r.d[6]&1U)!=0U?0x867e2:0x867d8;return true;         // BTST.B #0,D6; BNE.W 867e2.
    case 0x867d8:return on19_install(c,0x86fca,0x867e8);                   // MOVE.L #86fca,(A6); BRA.W 867e8.
    case 0x867e2:return on19_install(c,0x86d0c,0x867e8);                   // MOVE.L #86d0c,(A6).
    case 0x867e8:if(!on19_get(c,0x8e,2,value))return false;r.pc=(value&65535U)!=0U?0x86800:0x867f0;return true; // TST.W 8e(A6); BNE.W.
    case 0x867f0:if(!on19_bit(c,0x84,3,flag))return false;r.pc=flag?0x867fa:0x86800;return true; // BTST.B #3,84(A6); BEQ.W 86800.
    case 0x867fa:return on19_install(c,0x871ee,0x86800);                   // MOVE.L #871ee,(A6).
    case 0x86800:if(!on19_bit(c,0x15,7,flag))return false;r.pc=flag?0x86810:0x8680a;return true; // BTST.B #7,15(A6); BNE.W 86810.
    case 0x8680a:return on19_install(c,0x86f1c,0x86810);                   // MOVE.L #86f1c,(A6).
    case 0x86810:r.pc=0x8625a;return true;                                 // BRA.W 8625a (N18 shared tail).
    // ---- b15e0 (helper): JSR 4b54e.L; BCC.W b15f4; MOVE.B 5e(A6),a7(A6); CLR.B 5e(A6); 61 bit 7 -> C (RTS).
    case 0xb15e0:return am_call(c,0x4b54e,0xb15e6);
    case 0xb15e6:return on19_carry(c,0xb15f4,0xb15ea);                    // BCC.W b15f4 (C returned by 4b54e).
    case 0xb15ea:if(!on19_get(c,0x5e,1,value) || !on19_put(c,0xa7,1,value) || !on19_put(c,0x5e,1,0))return false;r.pc=0xb15f4;return true;
    case 0xb15f4:if(!on19_bit(c,0x61,7,flag))return false;r.pc=flag?0xb15fe:0xb1604;return true; // BTST.B #7,61(A6); BEQ.W b1604.
    case 0xb15fe:r.carry=AnimationCarrySet;return am_return(c);           // ORI.B #1,CCR; RTS.
    case 0xb1604:r.carry=AnimationCarryClear;return am_return(c);         // ANDI.B #fe,CCR; RTS.
    // ---- b160a (helper): JSR 49a58.L; D0.B & 3 selects the animation record b2040 / b2022 / b2004.
    case 0xb160a:return am_call(c,0x49a58,0xb1610);
    case 0xb1610:am_byte(r.d[0],r.d[0]&3U);r.pc=(r.d[0]&255U)!=0U?0xb162a:0xb1618;return true; // ANDI.B #3,D0; BNE.W b162a.
    case 0xb1618:return on19_animation(c,0xb2040,0xb1628);
    case 0xb162a:r.pc=(r.d[0]&255U)!=1U?0xb1644:0xb1632;return true;       // CMPI.B #1,D0; BNE.W b1644.
    case 0xb1632:return on19_animation(c,0xb2022,0xb1642);
    case 0xb1644:return on19_animation(c,0xb2004,0xb1654);
    case 0xb1628:case 0xb1642:case 0xb1654:case 0xb17f2:case 0xb182c:case 0xb1916:case 0xb1972:case 0xb19b0:case 0xb1b60:case 0xb1b8a:
    case 0xb1bc0:case 0xb1c80:case 0xb1d8a:case 0xb1db8:case 0xb1e28:case 0xb2002:return am_return(c); // RTS.
    // ---- b16ea (stage event callback): JSR b1d40(PC); CLR.B a6(A6); JSR b182e(PC); MOVE.L #b16fc,(A6).
    case 0xb16ea:return am_call(c,0xb1d40,0xb16ee);
    case 0xb16ee:if(!on19_put(c,0xa6,1,0))return false;return am_call(c,0xb182e,0xb16f6);
    case 0xb16f6:return on19_install(c,0xb16fc,0xb16fc);
    // ---- b16fc (installed): JSR 287e.L; BCS.W b170c; JMP 2a00.L.
    case 0xb16fc:return am_call(c,0x287e,0xb1702);
    case 0xb1702:return on19_carry(c,0xb1706,0xb170c);                    // BCS.W b170c (C returned by 287e).
    case 0xb1706:case 0xb17ec:case 0xdbf68:r.pc=0x2a00;return true;        // JMP 2a00.L.
    case 0xb170c:return am_call(c,0xb17f4,0xb1710);
    // SUBQ.W #1,9c(A6); BPL.W b171e.
    case 0xb1710:if(!on19_get(c,0x9c,2,value) || !on19_set_word(c,0x9c,value-1U))return false;r.pc=((value-1U)&0x8000U)?0xb1718:0xb171e;return true;
    case 0xb1718:if(!on19_set_word(c,0x9c,0))return false;r.pc=0xb171e;return true; // MOVE.W #0,9c(A6).
    case 0xb171e:if(!on19_get(c,0x9c,2,value))return false;r.pc=(value&65535U)!=0U?0xb1754:0xb1726;return true; // TST.W 9c(A6); BNE.W.
    case 0xb1726:if(!on19_get(c,0xa6,1,value))return false;r.pc=(value&255U)==0U?0xb1754:0xb172e;return true; // TST.B a6(A6); BEQ.W.
    case 0xb172e:r.a[0]=0xb175a;am_word(r.d[0],0x14);return am_call(c,0x28ae,0xb173e); // MOVEA.L #b175a,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0xb173e:return on19_carry(c,0xb1750,0xb1742);                    // BCC.W b1750 (C returned by 28ae).
    case 0xb1742:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x4970a,0xb174c); // CLR.W D0; CLR.W D1; JSR 4970a.L.
    case 0xb174c:r.carry=AnimationCarrySet;r.pc=0xb1750;return true;       // ORI.B #1,CCR.
    case 0xb1750:return am_call(c,0xb182e,0xb1754);
    case 0xb1754:if(!on19_put(c,0xa6,1,0))return false;return am_return(c); // CLR.B a6(A6); RTS.
    // ---- b175a (28ae child of b172e): JSR 497a6.L; BCS.W b1776; 8ebe with 37a / 3ba.
    case 0xb175a:return am_call(c,0x497a6,0xb1760);
    case 0xb1760:return on19_carry(c,0xb1764,0xb1776);                    // BCS.W b1776 (C returned by 497a6).
    case 0xb1764:return on19_sprite(c,0x37a,0xb1772);
    case 0xb1772:r.pc=0xb1784;return true;                                 // BRA.W b1784.
    case 0xb1776:return on19_sprite(c,0x3ba,0xb1784);
    case 0xb1784:if(!on19_bitop(c,0x15,0,false))return false;return am_call(c,0x49a58,0xb1790); // BCLR.B #0,15(A6); JSR 49a58.L.
    case 0xb1790:am_word(r.d[1],0xc);r.pc=(r.d[0]&0x80U)?0xb179a:0xb17a2;return true; // MOVE.W #c,D1; TST.B D0; BPL.W b17a2.
    case 0xb179a:if(!on19_bitop(c,0x15,0,true))return false;on19_neg_word(r.d[1]);r.pc=0xb17a2;return true; // BSET.B #0,15(A6); NEG.W D1.
    // MOVEA.L c(A6),A0; MOVEA.L 8a(A0),A0; MOVE.L 2e(A0),2e(A6); MOVE.L 32(A0),32(A6); ADD.W D1,2e(A6); ADDI.W #10,32(A6);
    // MOVE.W #e2,20(A6); MOVEA.L #b23f0,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0xb17a2:
        if(!on19_get(c,0x0c,4,value))return false;r.a[0]=value;if(!am_read(c,am_index(r.a[0],0x8a),4,value))return false;r.a[0]=value;
        if(!am_read(c,am_index(r.a[0],0x2e),4,value) || !on19_put(c,0x2e,4,value))return false;
        if(!am_read(c,am_index(r.a[0],0x32),4,value) || !on19_put(c,0x32,4,value))return false;
        if(!on19_get(c,0x2e,2,value) || !on19_set_word(c,0x2e,value+r.d[1]))return false;
        if(!on19_get(c,0x32,2,value) || !on19_set_word(c,0x32,value+0x10U) || !on19_set_word(c,0x20,0xe2))return false;
        return on19_animation(c,0xb23f0,0xb17d6);
    case 0xb17d6:return on19_install(c,0xb17dc,0xb17dc);
    // ---- b17dc (installed): JSR 43e34.L; JSR 49fc6.L; BCC.W b17f2; JMP 2a00.L.
    case 0xb17dc:return am_call(c,0x43e34,0xb17e2);
    case 0xb17e2:return am_call(c,0x49fc6,0xb17e8);
    case 0xb17e8:return on19_carry(c,0xb17f2,0xb17ec);                    // BCC.W b17f2 (C returned by 49fc6).
    // ---- b17f4 (helper): CLR.L 36(A6); CLR.L 3a(A6); CLR.L 8a(A6); JSR b1fd6(PC); BCS.W b1826.
    case 0xb17f4:if(!on19_put(c,0x36,4,0) || !on19_put(c,0x3a,4,0) || !on19_put(c,0x8a,4,0))return false;return am_call(c,0xb1fd6,0xb1804);
    case 0xb1804:return on19_carry(c,0xb1808,0xb1826);                    // BCS.W b1826 (C returned by b1fd6).
    // MOVE.L A0,8a(A6); ANDI.W #ff,D0; MOVE.W D0,D1; MOVE.L #20000,D0; JSR 443d2.L.
    case 0xb1808:
        if(!on19_put(c,0x8a,4,r.a[0]))return false;am_word(r.d[0],r.d[0]&255U);am_word(r.d[1],r.d[0]);r.d[0]=0x20000;
        return am_call(c,0x443d2,0xb181e);
    case 0xb181e:if(!on19_put(c,0x36,4,r.d[0]) || !on19_put(c,0x3a,4,r.d[1]))return false;r.pc=0xb1826;return true; // MOVE.L D0/D1.
    case 0xb1826:case 0xb1954:return am_call(c,0x43ea4,r.pc==0xb1826?0xb182c:0xb195a);
    // ---- b182e (helper): MOVE.W #50,D0; JSR 49a84.L; ADDI.W #28,D0; MOVE.W D0,9c(A6); RTS.
    case 0xb182e:am_word(r.d[0],0x50);return am_call(c,0x49a84,0xb1838);
    case 0xb1838:am_word(r.d[0],r.d[0]+0x28U);if(!on19_set_word(c,0x9c,r.d[0]))return false;return am_return(c);
    // ---- b1842 (28ae child of b1d4c): MOVE.W #1fb,20(A6); MOVE.B #1,9e(A6); JSR b1c0e(PC); 28ae child b1b24.
    case 0xb1842:if(!on19_set_word(c,0x20,0x1fb) || !on19_put(c,0x9e,1,1))return false;return am_call(c,0xb1c0e,0xb1852);
    case 0xb1852:r.a[0]=0xb1b24;am_word(r.d[0],0x14);return am_call(c,0x28ae,0xb1862); // MOVEA.L #b1b24,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0xb1862:if(!on19_get(c,0x90,2,value))return false;r.pc=(value&65535U)!=0U?0xb1918:0xb186a;return true; // TST.W 90(A6); BNE.W.
    // BCLR.B #0,15(A6); CLR.L 64(A6); MOVEA.L #b2206,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0xb186a:if(!on19_bitop(c,0x15,0,false) || !on19_put(c,0x64,4,0))return false;return on19_animation(c,0xb2206,0xb1884);
    case 0xb1884:return am_call(c,0xb1b62,0xb1888);
    case 0xb1888:return on19_install(c,0xb188e,0xb188e);
    // ---- b188e (installed): JSR 4be06.L; JSR b1dfa(PC); BCC.W b18ac.
    case 0xb188e:return am_call(c,0x4be06,0xb1894);
    case 0xb1894:case 0xb195a:case 0xb1998:return am_call(c,0xb1dfa,r.pc==0xb1894?0xb1898:(r.pc==0xb195a?0xb195e:0xb199c));
    case 0xb1898:return on19_carry(c,0xb18ac,0xb189c);                    // BCC.W b18ac (C returned by b1dfa).
    case 0xb189c:return on19_animation(c,0xb2206,0xb18ac);
    // SUBQ.W #1,94(A6); BPL.W b18ea.
    case 0xb18ac:if(!on19_get(c,0x94,2,value) || !on19_set_word(c,0x94,value-1U))return false;r.pc=((value-1U)&0x8000U)?0xb18b4:0xb18ea;return true;
    case 0xb18b4:return am_call(c,0xb1b62,0xb18b8);
    case 0xb18b8:return am_call(c,0x49a58,0xb18be);
    case 0xb18be:am_byte(r.d[0],r.d[0]&1U);r.pc=(r.d[0]&255U)!=0U?0xb18da:0xb18c6;return true; // ANDI.B #1,D0; BNE.W b18da.
    case 0xb18c6:return on19_animation(c,0xb225c,0xb18d6);
    case 0xb18d6:case 0xb19d6:r.pc=r.pc==0xb18d6?0xb18ea:0xb19ea;return true; // BRA.W.
    case 0xb18da:return on19_animation(c,0xb22e0,0xb18ea);
    case 0xb18ea:case 0xb195e:case 0xb19a4:return am_call(c,0xb1b76,r.pc==0xb18ea?0xb18ee:(r.pc==0xb195e?0xb1962:0xb19a8));
    case 0xb18ee:case 0xb1962:case 0xb199c:return am_call(c,0xb15e0,r.pc==0xb18ee?0xb18f2:(r.pc==0xb1962?0xb1966:0xb19a0));
    case 0xb18f2:return on19_carry(c,0xb18f6,0xb19b2);                    // BCS.W b19b2 (C returned by b15e0).
    // SUBQ.W #1,9a(A6); BMI.W b1918.
    case 0xb18f6:if(!on19_get(c,0x9a,2,value) || !on19_set_word(c,0x9a,value-1U))return false;r.pc=((value-1U)&0x8000U)?0xb1918:0xb18fe;return true;
    // MOVE.W 10d418.L,D0; CMP.W 98(A6),D0; BCS.W b1916 (unsigned D0.W < 98.W).
    case 0xb18fe:
        if(!am_read(c,0x10d418,2,value))return false;am_word(r.d[0],value);if(!on19_get(c,0x98,2,other))return false;
        r.pc=(r.d[0]&65535U)<(other&65535U)?0xb1916:0xb190c;return true;
    case 0xb190c:if(!on19_set_word(c,0x98,0xffff))return false;r.pc=0xb1918;return true; // MOVE.W #ffff,98(A6); BRA.W b1918.
    case 0xb1918:return am_call(c,0xb160a,0xb191c);
    case 0xb191c:if(!on19_put(c,0x62,1,0))return false;return am_call(c,0xb1dae,0xb1924); // CLR.B 62(A6); JSR b1dae(PC).
    case 0xb1924:return on19_install_return(c,0xb192c);                   // MOVE.L #b192c,(A6); RTS.
    // ---- b192c (installed): 9e = 1 -> b1e2a, b1f1a; 9e = 2 -> b1ee6 (BCS.W b186a), b1e74; then 43ea4, b1dfa, b1b76, b15e0.
    case 0xb192c:if(!on19_get(c,0x9e,1,value))return false;r.pc=(value&255U)!=1U?0xb193e:0xb1936;return true; // CMPI.B #1,9e(A6); BNE.W.
    case 0xb1936:return am_call(c,0xb1e2a,0xb193a);
    case 0xb193a:return am_call(c,0xb1f1a,0xb193e);
    case 0xb193e:if(!on19_get(c,0x9e,1,value))return false;r.pc=(value&255U)!=2U?0xb1954:0xb1948;return true; // CMPI.B #2,9e(A6); BNE.W.
    case 0xb1948:return am_call(c,0xb1ee6,0xb194c);
    case 0xb194c:return on19_carry(c,0xb1950,0xb186a);                    // BCS.W b186a (C returned by b1ee6).
    case 0xb1950:return am_call(c,0xb1e74,0xb1954);
    case 0xb1966:case 0xb19a0:return on19_carry(c,r.pc==0xb1966?0xb196a:0xb19a4,0xb19b2); // BCS.W b19b2 (C returned by b15e0).
    case 0xb196a:if(!on19_get(c,0x62,1,value))return false;r.pc=(value&255U)!=0U?0xb1974:0xb1972;return true; // TST.B 62(A6); BNE.W.
    case 0xb1974:return am_call(c,0xb1b8c,0xb1978);
    case 0xb1978:if(!on19_set_word(c,0x96,7))return false;return on19_install_return(c,0xb1986); // MOVE.W #7,96(A6); MOVE.L #b1986,(A6); RTS.
    // ---- b1986 (installed): MOVE.L 82(A6),36(A6); MOVE.L 86(A6),3a(A6); JSR 43ea4.L.
    case 0xb1986:
        if(!on19_get(c,0x82,4,value) || !on19_put(c,0x36,4,value) || !on19_get(c,0x86,4,value) || !on19_put(c,0x3a,4,value))return false;
        return am_call(c,0x43ea4,0xb1998);
    // SUBQ.W #1,96(A6); BMI.W b1918.
    case 0xb19a8:if(!on19_get(c,0x96,2,value) || !on19_set_word(c,0x96,value-1U))return false;r.pc=((value-1U)&0x8000U)?0xb1918:0xb19b0;return true;
    case 0xb19b2:am_word(r.d[0],0x187f);return am_call(c,0x3af8,0xb19bc);  // MOVE.W #187f,D0; JSR 3af8.L.
    case 0xb19bc:if(!on19_get(c,0xa7,1,value))return false;r.pc=(value&255U)!=7U?0xb19da:0xb19c6;return true; // CMPI.B #7,a7(A6); BNE.W.
    case 0xb19c6:return on19_animation(c,0xb213a,0xb19d6);
    case 0xb19da:return on19_animation(c,0xb205a,0xb19ea);
    case 0xb19ea:return on19_install_return(c,0xb19f2);                   // MOVE.L #b19f2,(A6); RTS.
    // ---- b1b24 (28ae child of b1852): CLR.W D0; CLR.W D1; JSR 49290.L; MOVE.L #b150a,56(A6); MOVE.W #7000,54(A6); MOVE.L #b1b42,(A6).
    case 0xb1b24:am_word(r.d[0],0);am_word(r.d[1],0);return am_call(c,0x49290,0xb1b2e);
    case 0xb1b2e:if(!on19_put(c,0x56,4,0xb150a) || !on19_set_word(c,0x54,0x7000))return false;return on19_install(c,0xb1b42,0xb1b42);
    // ---- b1b42 (installed): JSR 43e34.L; JSR 4b54e.L; BCC.W b1b60; MOVEA.L c(A6),A0; MOVE.B #1,62(A0); CLR.B 5e(A6).
    case 0xb1b42:return am_call(c,0x43e34,0xb1b48);
    case 0xb1b48:return am_call(c,0x4b54e,0xb1b4e);
    case 0xb1b4e:return on19_carry(c,0xb1b60,0xb1b52);                    // BCC.W b1b60 (C returned by 4b54e).
    case 0xb1b52:
        if(!on19_get(c,0x0c,4,value))return false;r.a[0]=value;if(!am_write(c,am_index(r.a[0],0x62),1,1) || !on19_put(c,0x5e,1,0))return false;
        r.pc=0xb1b60;return true;
    // ---- b1b62 (helper): MOVE.W #dc,D0; JSR 49a84.L; ADDI.W #50,D0; MOVE.W D0,94(A6); RTS.
    case 0xb1b62:am_word(r.d[0],0xdc);return am_call(c,0x49a84,0xb1b6c);
    case 0xb1b6c:am_word(r.d[0],r.d[0]+0x50U);if(!on19_set_word(c,0x94,r.d[0]))return false;return am_return(c);
    // ---- b1b76 (helper): LEA b14a0(PC),A0; JSR 1ab02.L; BCC.W b1b8a; JMP 2a24.L.
    case 0xb1b76:r.a[0]=0xb14a0;return am_call(c,0x1ab02,0xb1b80);
    case 0xb1b80:return on19_carry(c,0xb1b8a,0xb1b84);                    // BCC.W b1b8a (C returned by 1ab02).
    case 0xb1b84:case 0xb1e1c:r.pc=0x2a24;return true;                     // JMP 2a24.L.
    // ---- b1b8c (helper): JSR 49a58.L; ANDI.W #7f,D0; MOVE.W D0,D1; MOVE.L #38000,D0; JSR 443d2.L.
    case 0xb1b8c:return am_call(c,0x49a58,0xb1b92);
    case 0xb1b92:am_word(r.d[0],r.d[0]&0x7fU);am_word(r.d[1],r.d[0]);r.d[0]=0x38000;return am_call(c,0x443d2,0xb1ba4);
    // MOVE.L D0,82(A6); MOVE.L D1,86(A6); BCLR.B #0,15(A6); TST.L 82(A6); BMI.W b1bc0.
    case 0xb1ba4:
        if(!on19_put(c,0x82,4,r.d[0]) || !on19_put(c,0x86,4,r.d[1]) || !on19_bitop(c,0x15,0,false) || !on19_get(c,0x82,4,value))return false;
        r.pc=(value&0x80000000U)?0xb1bc0:0xb1bba;return true;
    case 0xb1bba:case 0xb1de0:if(!on19_bitop(c,0x15,0,true))return false;r.pc=r.pc==0xb1bba?0xb1bc0:0xb1de6;return true; // BSET.B #0,15(A6).
    // ---- b1bc2 (helper): TST.W 76(A6); BEQ.W b1be0; 8ebe with b7 (9f = 1) or e46 (9f = 0).
    case 0xb1bc2:if(!on19_get(c,0x76,2,value))return false;r.pc=(value&65535U)==0U?0xb1be0:0xb1bca;return true;
    case 0xb1bca:return on19_sprite(c,0xb7,0xb1bd8);
    case 0xb1bd8:if(!on19_put(c,0x9f,1,1))return false;return am_return(c); // MOVE.B #1,9f(A6); RTS.
    case 0xb1be0:return on19_sprite(c,0xe46,0xb1bee);
    case 0xb1bee:if(!on19_put(c,0x9f,1,0))return false;return am_return(c); // MOVE.B #0,9f(A6); RTS.
    // ---- b1bf6 (helper): LEA b14b0(PC),A0; CMPI.B #0,9e(A6); BNE.W b1c08; LEA b14ce(PC),A0; MOVE.L A0,56(A6); RTS.
    case 0xb1bf6:r.a[0]=0xb14b0;if(!on19_get(c,0x9e,1,value))return false;r.pc=(value&255U)!=0U?0xb1c08:0xb1c04;return true;
    case 0xb1c04:r.a[0]=0xb14ce;r.pc=0xb1c08;return true;
    case 0xb1c08:if(!on19_put(c,0x56,4,r.a[0]))return false;return am_return(c);
    // ---- b1c0e (helper): JSR b1bc2(PC); JSR b1c4a(PC); MOVE.W #e0ed,68(A6); MOVE.W #e0ed,1e(A6); JSR b1bf6(PC); LEA c8e5e.L,A0;
    // JSR 490ba.L; MOVE.W D0,54(A6); CLR.B a5(A6); CLR.B a0(A6); CLR.B a7(A6); MOVE.W #7fff,9a(A6); RTS.
    case 0xb1c0e:return am_call(c,0xb1bc2,0xb1c12);
    case 0xb1c12:return am_call(c,0xb1c4a,0xb1c16);
    case 0xb1c16:if(!on19_set_word(c,0x68,0xe0ed) || !on19_set_word(c,0x1e,0xe0ed))return false;return am_call(c,0xb1bf6,0xb1c26);
    case 0xb1c26:r.a[0]=0xc8e5e;return am_call(c,0x490ba,0xb1c32);
    case 0xb1c32:
        if(!on19_set_word(c,0x54,r.d[0]) || !on19_put(c,0xa5,1,0) || !on19_put(c,0xa0,1,0) || !on19_put(c,0xa7,1,0) ||
            !on19_set_word(c,0x9a,0x7fff))return false;
        return am_return(c);
    // ---- b1c4a (helper): 9e = 1 -> 90 = 7a, 98 = 7c; 9e = 2 -> 98 = 78, 76 = 2e, 78 = 32.
    case 0xb1c4a:if(!on19_get(c,0x9e,1,value))return false;r.pc=(value&255U)!=1U?0xb1c62:0xb1c54;return true;
    case 0xb1c54:if(!on19_copy_word(c,0x7a,0x90) || !on19_copy_word(c,0x7c,0x98))return false;return am_return(c);
    case 0xb1c62:if(!on19_get(c,0x9e,1,value))return false;r.pc=(value&255U)!=2U?0xb1c80:0xb1c6c;return true;
    case 0xb1c6c:if(!on19_copy_word(c,0x78,0x98) || !on19_copy_word(c,0x2e,0x76) || !on19_copy_word(c,0x32,0x78))return false;return am_return(c);
    // ---- b1cf8 (helper): MOVE.W 76/78/7a/7c/7e/80(A6) to the same displacements of A0; RTS.
    case 0xb1cf8:
        for(unsigned int i=0;i<6;++i) {
            const std::uint32_t displacement=0x76U+2U*i;
            if(!on19_get(c,displacement,2,value) || !am_write(c,am_index(r.a[0],displacement),2,value))return false;
        }
        return am_return(c);
    // ---- b1d1e (helper): two 49a84 draws (D0.W = 11) -> D0.W - 8, D1.W - 8 (the first draw kept on the stack).
    case 0xb1d1e:am_word(r.d[0],0x11);return am_call(c,0x49a84,0xb1d28);
    case 0xb1d28:if(!am_push(c,2,r.d[0]&65535U))return false;am_word(r.d[0],0x11);return am_call(c,0x49a84,0xb1d34); // MOVE.W D0,-(A7).
    case 0xb1d34:
        if(!am_pop(c,2,value))return false;am_word(r.d[1],value);am_word(r.d[0],r.d[0]-8U);am_word(r.d[1],r.d[1]-8U);return am_return(c);
    // ---- b1d40 (child generator): MOVE.W 78(A6),D0; SUBQ.W #1,D0; loop b1d46 .. b1d7a (D0.W + 1 children b1842).
    case 0xb1d40:if(!on19_get(c,0x78,2,value))return false;am_word(r.d[0],value-1U);r.pc=0xb1d46;return true;
    case 0xb1d46:if(!am_push(c,2,r.d[0]&65535U))return false;return am_call(c,0xb1d1e,0xb1d4c); // MOVE.W D0,-(A7); JSR b1d1e(PC).
    // MOVEM.W D0-D1,-(A7) (D0 at the lower address); MOVEA.L #b1842,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0xb1d4c:
        if(!am_push(c,2,r.d[1]&65535U) || !am_push(c,2,r.d[0]&65535U))return false;r.a[0]=0xb1842;am_word(r.d[0],0x14);
        return am_call(c,0x28ae,0xb1d60);
    // MOVEM.W (A7)+,D0-D1 (sign-extended to LONG); JSR 4970a.L.
    case 0xb1d60:
        if(!am_pop(c,2,value) || !am_pop(c,2,other))return false;r.d[0]=am_extend_word(value);r.d[1]=am_extend_word(other);
        return am_call(c,0x4970a,0xb1d6a);
    case 0xb1d6a:return am_call(c,0xb1cf8,0xb1d6e);
    case 0xb1d6e:if(!am_push(c,4,r.a[0]))return false;am_word(r.d[0],0x101);return am_call(c,0x49a84,0xb1d7a); // MOVE.L A0,-(A7).
    // ADDI.W #100,D0; MOVEA.L (A7)+,A0; MOVE.W D0,92(A0); MOVE.W (A7)+,D0; SUBQ.W #1,D0; BPL.B b1d46.
    case 0xb1d7a:
        am_word(r.d[0],r.d[0]+0x100U);if(!am_pop(c,4,value))return false;r.a[0]=value;
        if(!am_write(c,am_index(r.a[0],0x92),2,r.d[0]&65535U) || !am_pop(c,2,value))return false;am_word(r.d[0],value-1U);
        r.pc=(r.d[0]&0x8000U)?0xb1d8a:0xb1d46;return true;
    // ---- b1dae (helper): 9e = 2 -> new 49a84 direction (D0.W = 3, redrawn while equal to a0.B), b1ecc, 15 bit 0, 9a = 3c + draw.
    case 0xb1dae:if(!on19_get(c,0x9e,1,value))return false;r.pc=(value&255U)==2U?0xb1dba:0xb1db8;return true;
    case 0xb1dba:am_word(r.d[0],3);return am_call(c,0x49a84,0xb1dc4);
    case 0xb1dc4:if(!on19_get(c,0xa0,1,value))return false;r.pc=(r.d[0]&255U)==(value&255U)?0xb1dba:0xb1dca;return true; // CMP.B a0(A6),D0; BEQ.B.
    // MOVE.B D0,a0(A6); BCLR.B #0,15(A6); JSR b1ecc(PC).
    case 0xb1dca:if(!on19_put(c,0xa0,1,r.d[0]&255U) || !on19_bitop(c,0x15,0,false))return false;return am_call(c,0xb1ecc,0xb1dd8);
    // SUB.W 2e(A6),D0; BMI.W b1de6.
    case 0xb1dd8:if(!on19_get(c,0x2e,2,value))return false;am_word(r.d[0],r.d[0]-value);r.pc=(r.d[0]&0x8000U)?0xb1de6:0xb1de0;return true;
    case 0xb1de6:am_word(r.d[0],0x3d);return am_call(c,0x49a84,0xb1df0);
    case 0xb1df0:am_word(r.d[0],r.d[0]+0x3cU);if(!on19_set_word(c,0x9a,r.d[0]))return false;return am_return(c);
    // ---- b1dfa (helper): TST.B 9f(A6); BEQ.W b1e22; b43de / b441e with b14a8 / b15bc, JMP 2a24.L; JSR 49fc6.L; RTS.
    case 0xb1dfa:if(!on19_get(c,0x9f,1,value))return false;r.pc=(value&255U)==0U?0xb1e22:0xb1e02;return true;
    case 0xb1e02:r.a[0]=0xb14a8;return am_call(c,0xb43de,0xb1e0c);
    case 0xb1e0c:r.pc=(r.d[0]&255U)==0U?0xb1e22:0xb1e12;return true;       // TST.B D0; BEQ.W b1e22.
    case 0xb1e12:r.a[0]=0xb15bc;return am_call(c,0xb441e,0xb1e1c);
    case 0xb1e22:return am_call(c,0x49fc6,0xb1e28);
    // ---- b1fd6 (helper): JSR 4945e.L; BCS.W b2002; distance to the selected player -> 44602; ANDI.B #fe,CCR; RTS.
    case 0xb1fd6:return am_call(c,0x4945e,0xb1fdc);
    case 0xb1fdc:return on19_carry(c,0xb1fe0,0xb2002);                    // BCS.W b2002 (C returned by 4945e).
    // MOVE.W 42(A0),D0; SUB.W 42(A6),D0; MOVE.W 46(A0),D1; ADDI.W #20,D1; SUB.W 46(A6),D1; MOVE.L A0,-(A7); JSR 44602.L.
    case 0xb1fe0:
        if(!am_read(c,am_index(r.a[0],0x42),2,value))return false;am_word(r.d[0],value);if(!on19_get(c,0x42,2,value))return false;
        am_word(r.d[0],r.d[0]-value);if(!am_read(c,am_index(r.a[0],0x46),2,value))return false;am_word(r.d[1],value+0x20U);
        if(!on19_get(c,0x46,2,value))return false;am_word(r.d[1],r.d[1]-value);if(!am_push(c,4,r.a[0]))return false;
        return am_call(c,0x44602,0xb1ffc);
    case 0xb1ffc:if(!am_pop(c,4,value))return false;r.a[0]=value;r.carry=AnimationCarryClear;r.pc=0xb2002;return true; // MOVEA.L (A7)+,A0; ANDI.
    // ---- dbf5e (stage event callback): MOVE.W #19d7,D0; JSR 3af8.L; JMP 2a00.L.
    case 0xdbf5e:am_word(r.d[0],0x19d7);return am_call(c,0x3af8,0xdbf68);
    default:return am_error(c,"unsupported animation objects n19 PC");
    }
}
}
