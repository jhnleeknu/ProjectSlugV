#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// NEG.L Dn (32-bit two's complement; 80000000 stays 80000000).
std::uint32_t on35_neg(std::uint32_t value) {return (0U-value)&0xffffffffU;}
// Bcc on a C returned by a callee: clear -> clear_pc, set -> set_pc.
bool on35_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n35 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
}
// Objects F4 N35 (26 block starts): the 28ae child callback 4cf52 (N33 4c37c), the slot test 4d8d8, the speed maximum 4c6f0 (N34
// 4ca68 4ccb8) and the terrain call ea680. Calls leave to 288c (stage_event_ops), 2a00 (fade_card), 1abda (U12) and ea65a (U18).
// The 2 consumers 4cf58 / ea686 read a known C returned by 288c / 1abda. No bank read, no port, no X / DIV.
bool animation_objects_n35_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 4c6f0: |D0| (D7) against |LONG 5c92(A5)| (D6); MOVE.L D0,5c92(A5) when D6 <u D7. The same for D1 and 5c96(A5). RTS.
    case 0x4c6f0:r.d[7]=r.d[0];r.pc=(r.d[7]&0x80000000U)==0U?0x4c6f8:0x4c6f6;return true; // MOVE.L D0,D7; BPL.W 4c6f8.
    case 0x4c6f6:case 0x4c712:r.d[7]=on35_neg(r.d[7]);r.pc+=2U;return true;   // NEG.L D7.
    case 0x4c700:case 0x4c71c:r.d[6]=on35_neg(r.d[6]);r.pc+=2U;return true;   // NEG.L D6.
    case 0x4c6f8:                                                             // MOVE.L 5c92(A5),D6; BPL.W 4c702.
        if(!am_read(c,am_index(r.a[5],0x5c92),4,value))return false;r.d[6]=value;r.pc=(value&0x80000000U)==0U?0x4c702:0x4c700;return true;
    case 0x4c702:r.pc=r.d[6]>=r.d[7]?0x4c70c:0x4c708;return true;             // CMP.L D7,D6; BCC.W 4c70c.
    case 0x4c708:if(!am_write(c,am_index(r.a[5],0x5c92),4,r.d[0]))return false;r.pc=0x4c70c;return true; // MOVE.L D0,5c92(A5).
    case 0x4c70c:r.d[7]=r.d[1];r.pc=(r.d[7]&0x80000000U)==0U?0x4c714:0x4c712;return true; // MOVE.L D1,D7; BPL.W 4c714.
    case 0x4c714:                                                             // MOVE.L 5c96(A5),D6; BPL.W 4c71e.
        if(!am_read(c,am_index(r.a[5],0x5c96),4,value))return false;r.d[6]=value;r.pc=(value&0x80000000U)==0U?0x4c71e:0x4c71c;return true;
    case 0x4c71e:r.pc=r.d[6]>=r.d[7]?0x4c728:0x4c724;return true;             // CMP.L D7,D6; BCC.W 4c728.
    case 0x4c724:if(!am_write(c,am_index(r.a[5],0x5c96),4,r.d[1]))return false;r.pc=0x4c728;return true; // MOVE.L D1,5c96(A5).
    case 0x4c728:case 0x4cf62:case 0xea68a:return am_return(c);               // RTS.
    // ---- 28ae child callback 4cf52: JSR 288c.l (parent check); BCS.W 4cf62 (RTS); JMP 2a00.l (delete).
    case 0x4cf52:return am_call(c,0x288c,0x4cf58);
    case 0x4cf58:return on35_carry(c,0x4cf5c,0x4cf62);
    case 0x4cf5c:r.pc=0x2a00;return true;
    // ---- 4d8d8: MOVE.L A6,D0; CMP.W 5cba(A5),D0; BNE.W 4d8ea.
    case 0x4d8d8:
        r.d[0]=r.a[6];if(!am_read(c,am_index(r.a[5],0x5cba),2,value))return false;r.pc=(r.d[0]&65535U)!=value?0x4d8ea:0x4d8e2;return true;
    // MOVEQ #0,D0; MOVE.B 5ce1(A5),D1; RTS.
    case 0x4d8e2:r.d[0]=0;if(!am_read(c,am_index(r.a[5],0x5ce1),1,value))return false;am_byte(r.d[1],value);return am_return(c);
    // CMP.W 5ce6(A5),D0; BNE.W 4d8fa.
    case 0x4d8ea:if(!am_read(c,am_index(r.a[5],0x5ce6),2,value))return false;r.pc=(r.d[0]&65535U)!=value?0x4d8fa:0x4d8f2;return true;
    // MOVEQ #1,D0; MOVE.B 5d0d(A5),D1; RTS.
    case 0x4d8f2:r.d[0]=1;if(!am_read(c,am_index(r.a[5],0x5d0d),1,value))return false;am_byte(r.d[1],value);return am_return(c);
    case 0x4d8fa:r.d[0]=0xffffffffU;r.d[1]=0;return am_return(c);            // MOVEQ #ff,D0; MOVEQ #0,D1; RTS.
    // ---- ea680: JSR 1abda.l; BCS.W ea68c (C returned by 1abda); RTS.
    case 0xea680:return am_call(c,0x1abda,0xea686);
    case 0xea686:return on35_carry(c,0xea68a,0xea68c);
    // MOVE.L 42(A6),D0; MOVE.L 46(A6),D1; MOVEA.W #0,A0; MOVEQ #8,D7; BRA.B ea65a (U18).
    case 0xea68c:{
        std::uint32_t other=0;
        if(!am_read(c,am_index(r.a[6],0x42),4,value) || !am_read(c,am_index(r.a[6],0x46),4,other))return false;
        r.d[0]=value;r.d[1]=other;r.a[0]=0;r.d[7]=8;r.pc=0xea65a;return true;}
    default:return am_error(c,"unsupported animation objects n35 PC");
    }
}
}
