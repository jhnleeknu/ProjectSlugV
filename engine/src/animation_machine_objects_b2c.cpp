#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OB2C_STATE_TABLE=0x3ab80;  // 3ab7a: MOVEA.L 3ab80(PC,D0.W),A0 (LONG state entries, fixed ROM, live bus).
const std::uint32_t OB2C_MASK_TABLE=0x3ab98;   // 3ab5a: LEA 3ab98(PC),A1; MOVE.W (A1,D1.W),D2 (WORD request masks).
const std::uint32_t OB2C_SLOT_TABLE=0x3abde;   // 3abd0: MOVE.B 3abde(PC,D1.W),D1 (16 BYTE slot numbers).
const std::uint32_t OB2C_OFFSET_TABLE=0x3b4bc; // 3b4a2 / 3b4b4: MOVE.B 3b4bc(PC,D1.W),D0 / 3b4bd(PC,D1.W),D1 (BYTE pairs).
const std::uint32_t OB2C_SCRIPT_INDEX=0x3af74; // 3afa8: LEA 3af74(PC),A0; MOVE.W (A0,D0.W),D0.
const std::uint32_t OB2C_SOUND_TABLE=0x3af6c;  // 3afd4: LEA 3af6c(PC),A0; MOVE.W (A0,D0.W),D0.
const std::uint32_t OB2C_ANIM_TABLE=0x1d1b0;   // 1d19e: LEA 1d1b0(PC,D0.W),A0 (LONG pointer + LONG value rows).
const std::uint32_t OB2C_BANK_9C=0x20009c;     // 3ae8a: MOVE.L 20009c.l,22(A6) (banked LONG through the live bus).
std::uint32_t ob2c_w(std::uint32_t value) {return value&65535U;}
// EXT.W: the BYTE sign bit refills the upper byte of the WORD (explicit, no signed conversion).
std::uint32_t ob2c_ext(std::uint32_t value) {const std::uint32_t u=value&255U;return (u&0x80U)!=0U?(u|0xff00U):u;}
// NEG.W Dn (low WORD only).
void ob2c_neg_w(std::uint32_t& reg) {am_word(reg,0x10000U-ob2c_w(reg));}
bool ob2c_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob2c_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST.B #bit,d16(A6): true when the bit is 1.
bool ob2c_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob2c_get(c,c.s.a[6],displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// ANDI.B #mask,d16(A6).
bool ob2c_and(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t mask) {
    std::uint32_t value=0;return ob2c_get(c,c.s.a[6],displacement,1,value) && ob2c_put(c,c.s.a[6],displacement,1,value&mask);
}
// Bcc on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob2c_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b2c caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #script,A1; JSR 3b398(PC) (N33: select the animation script of the sub-state).
bool ob2c_script(AnimationMachineContext& c,std::uint32_t script,std::uint32_t return_pc) {c.s.a[1]=script;return am_call(c,0x3b398,return_pc);}
// [MOVE.B #value,d16(A6)]; MOVE.L #next,82(A6) and fall into next (the installed sub-state re-entry).
bool ob2c_install(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,std::uint32_t next) {
    if(displacement!=0U && !ob2c_put(c,c.s.a[6],displacement,1,value))return false;
    if(!ob2c_put(c,c.s.a[6],0x82,4,next))return false;c.s.pc=next;return true;
}
// LEA continuation(PC),A0; BRA.W dispatcher (3ab3e request check / 3aba4 input slot table).
bool ob2c_dispatch(AnimationMachineContext& c,std::uint32_t continuation,std::uint32_t dispatcher) {c.s.a[0]=continuation;c.s.pc=dispatcher;return true;}
// BTST.B #bit,D0; BNE/BEQ: taken when the bit equals `when_set`.
bool ob2c_d0_bit(AnimationMachineContext& c,unsigned int bit,bool when_set,std::uint32_t taken,std::uint32_t fall) {
    const bool set=((c.s.d[0]>>bit)&1U)!=0U;c.s.pc=set==when_set?taken:fall;return true;
}
// BTST.B #4,9d(A6); BEQ.W keep / ANDI.B #ef,9d(A6); ANDI.B #ef,9e(A6); BRA.W 3a936.
bool ob2c_bit4(AnimationMachineContext& c,std::uint32_t keep) {
    bool bit=false;if(!ob2c_bit(c,0x9d,4,bit))return false;c.s.pc=bit?(c.s.pc+10U):keep;return true;                   // fall-through after BTST (6) + BEQ.W (4).
}
bool ob2c_clear4(AnimationMachineContext& c) {
    if(!ob2c_and(c,0x9d,0xef) || !ob2c_and(c,0x9e,0xef))return false;c.s.pc=0x3a936;return true;
}
}
// Objects B2c (218 block starts): the 82(A6) partner sub-state chain 3a60a..3abde (170: 27 installed sub-state re-entries, the request dispatcher
// 3ab3e with the LONG state table 3ab80 and the WORD mask table 3ab98, the input dispatcher 3aba4 with the BYTE slot table 3abde and the three 7-slot
// BRA.W tables 3a63c 3a782 3a960), the offset helper 3b48c (5), the partner initialisation 3b5a6 (5), the 28ae children 3af86 (14) and 3ae84 (20),
// and the leaf helpers 1bf80 (3) and 1d198 (1). The two indirect jumps 3ab7e JMP (A0) and 3abda JMP (A0,D1.W) go to the live target (no filter in the
// original). Data reads (the tables above, 3af74 3af6c 3b4bc 1d1b0, the banked LONGs) go through the live bus without a bound check. Known C: the three
// consumers 3af12 3af60 3b026 (BCC) read the C returned by 49fc6; every flag consumed inside a block is computed there; no block produces a known C
// for another block. Callees 3b398 3b446 3b22a 3a5d2 4b82e 4d98a 8ebe 49f8c 43e34 49fc6 49290 491c4 2a00 are routed elsewhere. No X / DIV / port.
bool animation_objects_b2c_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool bit=false;
    switch(r.pc) {
    // ---- 3a60a: MOVEA.L #0,A1; JSR 3b398(PC) / MOVE.B #ff,96(A6); MOVE.L #3a622,82(A6) / LEA 3a62a(PC),A0; BRA.W 3ab3e / BRA.W 3ab30.
    case 0x3a60a:return ob2c_script(c,0,0x3a614);
    case 0x3a614:return ob2c_install(c,0x96,0xff,0x3a622);
    case 0x3a622:return ob2c_dispatch(c,0x3a62a,0x3ab3e);
    case 0x3a62a:case 0x3a770:case 0x3a8b6:case 0x3a8f4:case 0x3a932:case 0x3aae4:case 0x3ab08:case 0x3ab2c:r.pc=0x3ab30;return true;
    // ---- group 0: 3a62e (MOVE.B #0,96(A6); LEA 3a63c(PC),A0; BRA.W 3aba4) and its slots 3a63c..3a654.
    case 0x3a62e:if(!ob2c_put(c,r.a[6],0x96,1,0))return false;return ob2c_dispatch(c,0x3a63c,0x3aba4);
    case 0x3a63c:r.pc=0x3a658;return true;
    case 0x3a640:r.pc=0x3a684;return true;
    case 0x3a644:r.pc=0x3a6a0;return true;
    case 0x3a648:r.pc=0x3a6bc;return true;
    case 0x3a64c:r.pc=0x3a6e4;return true;
    case 0x3a650:r.pc=0x3a70c;return true;
    case 0x3a654:r.pc=0x3a728;return true;
    case 0x3a658:return ob2c_script(c,0x3c88c,0x3a662);
    case 0x3a662:return ob2c_install(c,0x97,3,0x3a670);
    case 0x3a670:case 0x3a6d4:case 0x3a6fc:case 0x3a7b6:case 0x3a81a:case 0x3a842:case 0x3a9aa:case 0x3aa08:case 0x3aa2a:
        return am_call(c,0x3b446,r.pc+4U);                                     // BSR.W 3b446 (partner input bits in D0).
    case 0x3a674:return ob2c_d0_bit(c,0,true,0x3a62e,0x3a67a);                 // BTST.B #0,D0; BNE.B 3a62e.
    case 0x3a67a:return ob2c_d0_bit(c,1,true,0x3a62e,0x3a680);                 // BTST.B #1,D0; BNE.B 3a62e.
    case 0x3a680:case 0x3a69c:case 0x3a6b8:case 0x3a6e0:case 0x3a708:case 0x3a724:case 0x3a740:r.pc=0x3a744;return true;
    case 0x3a684:return ob2c_script(c,0x3c8ca,0x3a68e);
    case 0x3a68e:return ob2c_install(c,0x97,2,0x3a69c);
    case 0x3a6a0:return ob2c_script(c,0x3c956,0x3a6aa);
    case 0x3a6aa:return ob2c_install(c,0x97,2,0x3a6b8);
    case 0x3a6bc:return ob2c_script(c,0x3caee,0x3a6c6);
    case 0x3a6c6:return ob2c_install(c,0x97,3,0x3a6d4);
    case 0x3a6d8:return ob2c_d0_bit(c,0,false,0x3a62e,0x3a6e0);                // BTST.B #0,D0; BEQ.W 3a62e.
    case 0x3a6e4:return ob2c_script(c,0x3cb2c,0x3a6ee);
    case 0x3a6ee:return ob2c_install(c,0x97,3,0x3a6fc);
    case 0x3a700:return ob2c_d0_bit(c,1,false,0x3a62e,0x3a708);                // BTST.B #1,D0; BEQ.W 3a62e.
    case 0x3a70c:return ob2c_script(c,0x3ca68,0x3a716);
    case 0x3a716:return ob2c_install(c,0x97,2,0x3a724);
    case 0x3a728:return ob2c_script(c,0x3c9dc,0x3a732);
    case 0x3a732:return ob2c_install(c,0x97,2,0x3a740);
    case 0x3a744:return ob2c_bit4(c,0x3a75e);                                 // BTST.B #4,9d(A6); BEQ.W 3a75e.
    case 0x3a74e:case 0x3a894:case 0x3a8dc:case 0x3a91a:return ob2c_clear4(c); // ANDI.B #ef,9d(A6); ANDI.B #ef,9e(A6); BRA.W 3a936.
    case 0x3a75e:return ob2c_dispatch(c,0x3a766,0x3ab3e);
    case 0x3a766:if(!ob2c_bit(c,0x94,0,bit))return false;r.pc=bit?0x3a62e:0x3a770;return true;   // BTST.B #0,94(A6); BNE.W 3a62e.
    // ---- group 1: 3a774 (MOVE.B #1,96(A6); LEA 3a782(PC),A0; BRA.W 3aba4) and its slots 3a782..3a79a.
    case 0x3a774:if(!ob2c_put(c,r.a[6],0x96,1,1))return false;return ob2c_dispatch(c,0x3a782,0x3aba4);
    case 0x3a782:r.pc=0x3a79e;return true;
    case 0x3a786:r.pc=0x3a7ca;return true;
    case 0x3a78a:r.pc=0x3a7e6;return true;
    case 0x3a78e:r.pc=0x3a802;return true;
    case 0x3a792:r.pc=0x3a82a;return true;
    case 0x3a796:r.pc=0x3a852;return true;
    case 0x3a79a:r.pc=0x3a86e;return true;
    case 0x3a79e:return ob2c_script(c,0x3cb6a,0x3a7a8);
    case 0x3a7a8:return ob2c_install(c,0x97,3,0x3a7b6);
    case 0x3a7ba:return ob2c_d0_bit(c,0,true,0x3a774,0x3a7c0);
    case 0x3a7c0:return ob2c_d0_bit(c,1,true,0x3a774,0x3a7c6);
    case 0x3a7c6:case 0x3a7e2:case 0x3a7fe:case 0x3a826:case 0x3a84e:case 0x3a86a:case 0x3a886:r.pc=0x3a88a;return true;
    case 0x3a7ca:return ob2c_script(c,0x3c8ca,0x3a7d4);
    case 0x3a7d4:return ob2c_install(c,0x97,2,0x3a7e2);
    case 0x3a7e6:return ob2c_script(c,0x3c956,0x3a7f0);
    case 0x3a7f0:return ob2c_install(c,0x97,2,0x3a7fe);
    case 0x3a802:return ob2c_script(c,0x3caee,0x3a80c);
    case 0x3a80c:return ob2c_install(c,0x97,3,0x3a81a);
    case 0x3a81e:return ob2c_d0_bit(c,0,false,0x3a774,0x3a826);
    case 0x3a82a:return ob2c_script(c,0x3cb2c,0x3a834);
    case 0x3a834:return ob2c_install(c,0x97,3,0x3a842);
    case 0x3a846:return ob2c_d0_bit(c,1,false,0x3a774,0x3a84e);
    case 0x3a852:return ob2c_script(c,0x3ca68,0x3a85c);
    case 0x3a85c:return ob2c_install(c,0x97,2,0x3a86a);
    case 0x3a86e:return ob2c_script(c,0x3c9dc,0x3a878);
    case 0x3a878:return ob2c_install(c,0x97,2,0x3a886);
    case 0x3a88a:return ob2c_bit4(c,0x3a8a4);
    case 0x3a8a4:return ob2c_dispatch(c,0x3a8ac,0x3ab3e);
    case 0x3a8ac:if(!ob2c_bit(c,0x94,0,bit))return false;r.pc=bit?0x3a774:0x3a8b6;return true;
    // ---- states 2 and 3 (LONG table entries 3a8ba / 3a8f8).
    case 0x3a8ba:return ob2c_script(c,0x3c88c,0x3a8c4);
    case 0x3a8c4:return ob2c_install(c,0x96,2,0x3a8d2);
    case 0x3a8d2:return ob2c_bit4(c,0x3a8ec);
    case 0x3a8ec:return ob2c_dispatch(c,0x3a8f4,0x3ab3e);
    case 0x3a8f8:return ob2c_script(c,0x3ccce,0x3a902);
    case 0x3a902:return ob2c_install(c,0x96,3,0x3a910);
    case 0x3a910:return ob2c_bit4(c,0x3a92a);
    case 0x3a92a:return ob2c_dispatch(c,0x3a932,0x3ab3e);
    // ---- 3a936: ANDI.B #ef,9d(A6); ANDI.B #ef,9e(A6); MOVE.B #5,a6(A6); MOVE.B #6,a3(A6); CLR.B a8(A6).
    case 0x3a936:
        if(!ob2c_and(c,0x9d,0xef) || !ob2c_and(c,0x9e,0xef) || !ob2c_put(c,r.a[6],0xa6,1,5) || !ob2c_put(c,r.a[6],0xa3,1,6) ||
            !ob2c_put(c,r.a[6],0xa8,1,0))return false;
        r.pc=0x3a952;return true;
    // ---- group 2: 3a952 (MOVE.B #0,97(A6); LEA 3a960(PC),A0; BRA.W 3aba4) and its slots 3a960..3a978.
    case 0x3a952:if(!ob2c_put(c,r.a[6],0x97,1,0))return false;return ob2c_dispatch(c,0x3a960,0x3aba4);
    case 0x3a960:r.pc=0x3a97c;return true;
    case 0x3a964:r.pc=0x3a9be;return true;
    case 0x3a968:r.pc=0x3a9da;return true;
    case 0x3a96c:r.pc=0x3a9f6;return true;
    case 0x3a970:r.pc=0x3aa18;return true;
    case 0x3a974:r.pc=0x3aa3a;return true;
    case 0x3a978:r.pc=0x3aa56;return true;
    // CMPI.B #11,9f(A6); BCC.W 3a994 (BYTE >= 11 unsigned).
    case 0x3a97c:if(!ob2c_get(c,r.a[6],0x9f,1,value))return false;r.pc=value>=0x11U?0x3a994:0x3a986;return true;
    case 0x3a986:return ob2c_script(c,0x3cbf0,0x3a990);
    case 0x3a990:r.pc=0x3a9a2;return true;
    case 0x3a994:return ob2c_script(c,0x3cbf0,0x3a99e);
    case 0x3a99e:if(!ob2c_get(c,r.a[6],0xa3,1,value) || !ob2c_put(c,r.a[6],0xa3,1,value+3U))return false;r.pc=0x3a9a2;return true; // ADDQ.B #3,a3(A6).
    case 0x3a9a2:return ob2c_install(c,0,0,0x3a9aa);
    case 0x3a9ae:return ob2c_d0_bit(c,0,true,0x3a952,0x3a9b4);
    case 0x3a9b4:return ob2c_d0_bit(c,1,true,0x3a952,0x3a9ba);
    case 0x3a9ba:case 0x3a9d6:case 0x3a9f2:case 0x3aa14:case 0x3aa36:case 0x3aa52:case 0x3aa6e:r.pc=0x3aa72;return true;
    case 0x3a9be:return ob2c_script(c,0x3c904,0x3a9c8);
    case 0x3a9c8:return ob2c_install(c,0x97,2,0x3a9d6);
    case 0x3a9da:return ob2c_script(c,0x3c990,0x3a9e4);
    case 0x3a9e4:return ob2c_install(c,0x97,2,0x3a9f2);
    case 0x3a9f6:return ob2c_script(c,0x3cc3a,0x3aa00);
    case 0x3aa00:return ob2c_install(c,0,0,0x3aa08);
    case 0x3aa0c:return ob2c_d0_bit(c,0,false,0x3a952,0x3aa14);
    case 0x3aa18:return ob2c_script(c,0x3cc84,0x3aa22);
    case 0x3aa22:return ob2c_install(c,0,0,0x3aa2a);
    case 0x3aa2e:return ob2c_d0_bit(c,1,false,0x3a952,0x3aa36);
    case 0x3aa3a:return ob2c_script(c,0x3caa2,0x3aa44);
    case 0x3aa44:return ob2c_install(c,0x97,2,0x3aa52);
    case 0x3aa56:return ob2c_script(c,0x3ca16,0x3aa60);
    case 0x3aa60:return ob2c_install(c,0x97,2,0x3aa6e);
    case 0x3aa72:return ob2c_dispatch(c,0x3aa7a,0x3ab3e);
    case 0x3aa7a:if(!ob2c_bit(c,0x94,0,bit))return false;r.pc=bit?0x3a952:0x3aa84;return true;   // BTST.B #0,94(A6); BNE.W 3a952.
    case 0x3aa84:if(!ob2c_bit(c,0x94,4,bit))return false;r.pc=bit?0x3aa9c:0x3aa8e;return true;   // BTST.B #4,94(A6); BNE.W 3aa9c.
    case 0x3aa8e:if(!ob2c_get(c,r.a[6],0x97,1,value))return false;r.pc=(value&0x80U)==0U?0x3aa9c:0x3aa96;return true; // TST.B 97(A6); BPL.W.
    case 0x3aa96:if(!ob2c_put(c,r.a[6],0x97,1,0))return false;r.pc=0x3aa9c;return true;
    case 0x3aa9c:if(!ob2c_get(c,r.a[6],0xa3,1,value))return false;r.pc=value!=0U?0x3aae4:0x3aaa4;return true;   // TST.B a3(A6); BNE.W 3aae4.
    // ANDI.B #bf,9d / #bf,9e / #ef,9d / #ef,9e; MOVE.B 95(A6),D0; CMPI.B #ff,D0; BNE.W 3aacc.
    case 0x3aaa4:
        if(!ob2c_and(c,0x9d,0xbf) || !ob2c_and(c,0x9e,0xbf) || !ob2c_and(c,0x9d,0xef) || !ob2c_and(c,0x9e,0xef))return false;
        if(!ob2c_get(c,r.a[6],0x95,1,value))return false;am_byte(r.d[0],value);r.pc=value!=0xffU?0x3aacc:0x3aac8;return true;
    case 0x3aac8:if(!ob2c_get(c,r.a[6],0x96,1,value))return false;am_byte(r.d[0],value);r.pc=0x3aacc;return true;
    // MOVE.B D0,95(A6); MOVE.B #ff,96(A6); MOVE.L #3a60a,82(A6); MOVE.B #4,97(A6).
    case 0x3aacc:
        if(!ob2c_put(c,r.a[6],0x95,1,r.d[0]) || !ob2c_put(c,r.a[6],0x96,1,0xff) || !ob2c_put(c,r.a[6],0x82,4,0x3a60a) ||
            !ob2c_put(c,r.a[6],0x97,1,4))return false;
        r.pc=0x3aae4;return true;
    // ---- states 4 and 5 (LONG table entries 3aae8 / 3ab0c).
    case 0x3aae8:return ob2c_script(c,0x3c88c,0x3aaf2);
    case 0x3aaf2:return ob2c_install(c,0x96,4,0x3ab00);
    case 0x3ab00:return ob2c_dispatch(c,0x3ab08,0x3ab3e);
    case 0x3ab0c:return ob2c_script(c,0x3c88c,0x3ab16);
    case 0x3ab16:return ob2c_install(c,0x96,5,0x3ab24);
    case 0x3ab24:return ob2c_dispatch(c,0x3ab2c,0x3ab3e);
    // ---- 3ab30: BSR.W 3b48c / MOVE.B D0,a9(A6); MOVE.B D1,aa(A6); RTS.
    case 0x3ab30:return am_call(c,0x3b48c,0x3ab34);
    case 0x3ab34:if(!ob2c_put(c,r.a[6],0xa9,1,r.d[0]) || !ob2c_put(c,r.a[6],0xaa,1,r.d[1]))return false;return am_return(c);
    // ---- 3ab3e request dispatcher: MOVEQ #0,D0; MOVE.B 95(A6),D0; CMPI.B #ff,D0; BEQ.W 3ab7e.
    case 0x3ab3e:if(!ob2c_get(c,r.a[6],0x95,1,value))return false;r.d[0]=value;r.pc=value==0xffU?0x3ab7e:0x3ab4c;return true;
    // MOVEQ #0,D1; MOVE.B 96(A6),D1; CMPI.B #ff,D1; BEQ.W 3ab6c.
    case 0x3ab4c:if(!ob2c_get(c,r.a[6],0x96,1,value))return false;r.d[1]=value;r.pc=value==0xffU?0x3ab6c:0x3ab5a;return true;
    // LEA 3ab98(PC),A1; ADD.W D1,D1; MOVE.W (A1,D1.W),D2; BTST.L D0,D2 (bit D0 mod 32 of the whole LONG); BEQ.W 3ab6c.
    case 0x3ab5a:
        r.a[1]=OB2C_MASK_TABLE;am_word(r.d[1],r.d[1]+r.d[1]);
        if(!am_read(c,am_index(r.a[1],r.d[1]),2,value))return false;am_word(r.d[2],value);
        r.pc=((r.d[2]>>(r.d[0]&31U))&1U)==0U?0x3ab6c:0x3ab6a;return true;
    case 0x3ab6a:r.d[0]=0xffffffffU;r.pc=0x3ab6c;return true;                  // MOVEQ #ff,D0.
    case 0x3ab6c:r.pc=(r.d[0]&0x80U)!=0U?0x3ab7e:0x3ab72;return true;         // TST.B D0; BMI.W 3ab7e.
    // ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L 3ab80(PC,D0.W),A0 (no bound check; live bus).
    case 0x3ab72:
        am_word(r.d[0],r.d[0]&0xffU);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        if(!am_read(c,am_index(OB2C_STATE_TABLE,r.d[0]),4,value))return false;r.a[0]=value;r.pc=0x3ab7e;return true;
    case 0x3ab7e:r.pc=r.a[0];return true;                                    // JMP (A0) (live target).
    // ---- 3aba4 input dispatcher: MOVE.L A0,-(A7); BSR.W 3b446.
    case 0x3aba4:if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x3b446,0x3abaa);
    // BTST.B #0,D0; SNE.B D1; ANDI.B #1,D1; BTST.B #1,D0; BEQ.W 3abc0.
    case 0x3abaa:am_byte(r.d[1],(r.d[0]&1U)!=0U?1U:0U);r.pc=(r.d[0]&2U)==0U?0x3abc0:0x3abbc;return true;
    case 0x3abbc:am_byte(r.d[1],3);r.pc=0x3abc0;return true;                // MOVE.B #3,D1.
    // MOVE.B 9a(A6),D2; MOVE.B D1,99(A6); LSL.B #2,D2; OR.B D2,D1; ANDI.W #f,D1; MOVE.B 3abde(PC,D1.W),D1; ADD.W D1,D1 (x2);
    // MOVEA.L (A7)+,A0; JMP (A0,D1.W) (live target).
    case 0x3abc0:
        if(!ob2c_get(c,r.a[6],0x9a,1,value))return false;am_byte(r.d[2],value);
        if(!ob2c_put(c,r.a[6],0x99,1,r.d[1]))return false;
        am_byte(r.d[2],r.d[2]<<2);am_byte(r.d[1],r.d[1]|r.d[2]);am_word(r.d[1],r.d[1]&15U);
        if(!am_read(c,am_index(OB2C_SLOT_TABLE,r.d[1]),1,value))return false;am_byte(r.d[1],value);
        am_word(r.d[1],r.d[1]+r.d[1]);am_word(r.d[1],r.d[1]+r.d[1]);
        if(!am_pop(c,4,value))return false;r.a[0]=value;r.pc=am_index(r.a[0],r.d[1]);return true;
    // ---- 3b48c: MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B 9f(A6),D1; CMPI.B #11,D1; BLS.W 3b4a0.
    case 0x3b48c:if(!ob2c_get(c,r.a[6],0x9f,1,value))return false;r.d[0]=0;r.d[1]=value;r.pc=value<=0x11U?0x3b4a0:0x3b49c;return true;
    case 0x3b49c:am_byte(r.d[1],0x11);r.pc=0x3b4a0;return true;
    // ADD.W D1,D1; MOVE.B 3b4bc(PC,D1.W),D0; EXT.W D0; BTST.B #0,15(A6); BEQ.W 3b4b4.
    case 0x3b4a0:
        am_word(r.d[1],r.d[1]+r.d[1]);if(!am_read(c,am_index(OB2C_OFFSET_TABLE,r.d[1]),1,value))return false;
        am_byte(r.d[0],value);am_word(r.d[0],ob2c_ext(r.d[0]));
        if(!ob2c_bit(c,0x15,0,bit))return false;r.pc=bit?0x3b4b2:0x3b4b4;return true;
    case 0x3b4b2:ob2c_neg_w(r.d[0]);r.pc=0x3b4b4;return true;
    // MOVE.B 3b4bd(PC,D1.W),D1; EXT.W D1; RTS.
    case 0x3b4b4:
        if(!am_read(c,am_index(OB2C_OFFSET_TABLE+1U,r.d[1]),1,value))return false;am_byte(r.d[1],value);am_word(r.d[1],ob2c_ext(r.d[1]));
        return am_return(c);
    // ---- 3b5a6: JSR 3b22a(PC).
    case 0x3b5a6:return am_call(c,0x3b22a,0x3b5aa);
    // MOVE.B 1b(A6),14(A6); MOVE.L #0,64 / 7e; MOVE.W #0,8a; MOVE.B #11,9f; MOVE.B #0,99 / 9a / ab / b2; JSR 3a5d2(PC).
    case 0x3b5aa:
        if(!ob2c_get(c,r.a[6],0x1b,1,value) || !ob2c_put(c,r.a[6],0x14,1,value))return false;
        if(!ob2c_put(c,r.a[6],0x64,4,0) || !ob2c_put(c,r.a[6],0x7e,4,0) || !ob2c_put(c,r.a[6],0x8a,2,0) || !ob2c_put(c,r.a[6],0x9f,1,0x11) ||
            !ob2c_put(c,r.a[6],0x99,1,0) || !ob2c_put(c,r.a[6],0x9a,1,0) || !ob2c_put(c,r.a[6],0xab,1,0) || !ob2c_put(c,r.a[6],0xb2,1,0))return false;
        return am_call(c,0x3a5d2,0x3b5e8);
    // MOVE.L #3b882,56(A6); LEA 0.w,A0; JSR 4b82e.l.
    case 0x3b5e8:if(!ob2c_put(c,r.a[6],0x56,4,0x3b882))return false;r.a[0]=0;return am_call(c,0x4b82e,0x3b5fa);
    // BCLR.B #7,61(A6); MOVE.B #0,5e(A6); MOVE.W #8811,68(A6); MOVE.W #8811,1e(A6); CLR.B 9d / 9e; MOVE.W 86(A6),D0; MOVE.B #1,D7; JSR 4d98a.l.
    case 0x3b5fa:
        if(!ob2c_and(c,0x61,0x7f) || !ob2c_put(c,r.a[6],0x5e,1,0) || !ob2c_put(c,r.a[6],0x68,2,0x8811) || !ob2c_put(c,r.a[6],0x1e,2,0x8811) ||
            !ob2c_put(c,r.a[6],0x9d,1,0) || !ob2c_put(c,r.a[6],0x9e,1,0))return false;
        if(!ob2c_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],value);am_byte(r.d[7],1);return am_call(c,0x4d98a,0x3b628);
    case 0x3b628:case 0x3af6a:case 0x3b03a:return am_return(c);               // RTS.
    // ---- 3ae84 (28ae child of 3a4da): MOVE.W #f2,20(A6); MOVE.L 20009c.l,22(A6); MOVE.W #208,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x3ae84:
        if(!ob2c_put(c,r.a[6],0x20,2,0xf2) || !am_read(c,OB2C_BANK_9C,4,value) || !ob2c_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[0],0x208);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3aea0);
    // MOVEA.L c(A6),A0; CMPI.B #11,9f(A0); BCC.W 3af2e.
    case 0x3aea0:
        if(!ob2c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ob2c_get(c,r.a[0],0x9f,1,value))return false;
        r.pc=value>=0x11U?0x3af2e:0x3aeae;return true;
    case 0x3aeae:r.a[1]=0x3d0f2;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3aebe);   // MOVEA.L #3d0f2,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3aebe:if(!ob2c_put(c,r.a[6],0,4,0x3aec4))return false;r.pc=0x3aec4;return true;   // MOVE.L #3aec4,(A6).
    case 0x3aec4:case 0x3af54:return am_call(c,0x43e34,r.pc+6U);              // JSR 43e34.l.
    // MOVEQ #0,D0; MOVE.B 13(A6),D0; ADDQ.B #1,D0; BCS.W 3aee4 (BYTE carry out).
    case 0x3aeca:
        if(!ob2c_get(c,r.a[6],0x13,1,value))return false;r.d[0]=(value+1U)&255U;r.pc=value==0xffU?0x3aee4:0x3aed6;return true;
    // MULS.W 3a(A6),D0; ASR.L #8,D0; SUB.W 3a(A6),D0; SUB.W D0,46(A6).
    case 0x3aed6: {
        if(!ob2c_get(c,r.a[6],0x3a,2,value))return false;
        const std::int32_t a=static_cast<std::int32_t>(am_extend_word(r.d[0]&65535U));
        const std::int32_t b=static_cast<std::int32_t>(am_extend_word(value));
        const std::uint32_t product=static_cast<std::uint32_t>(a*b);              // |a*b| <= 2^30: no overflow.
        r.d[0]=(product>>8)|((product&0x80000000U)!=0U?0xff000000U:0U);             // ASR.L #8 (explicit sign fill).
        am_word(r.d[0],r.d[0]-value);
        std::uint32_t field=0;if(!ob2c_get(c,r.a[6],0x46,2,field) || !ob2c_put(c,r.a[6],0x46,2,field-r.d[0]))return false;
        r.pc=0x3aee4;return true;
    }
    // MOVE.B 8e(A6),D0; MOVE.B 8f(A6),D1; EXT.W D0; EXT.W D1; BTST.B #0,15(A6); BEQ.W 3aefc.
    case 0x3aee4:
        if(!ob2c_get(c,r.a[6],0x8e,1,value))return false;am_byte(r.d[0],value);
        if(!ob2c_get(c,r.a[6],0x8f,1,value))return false;am_byte(r.d[1],value);
        am_word(r.d[0],ob2c_ext(r.d[0]));am_word(r.d[1],ob2c_ext(r.d[1]));
        if(!ob2c_bit(c,0x15,0,bit))return false;r.pc=bit?0x3aefa:0x3aefc;return true;
    case 0x3aefa:ob2c_neg_w(r.d[0]);r.pc=0x3aefc;return true;
    // SUB.W 36(A6),D0; SUB.W 3a(A6),D1; SUB.W D0,42(A6); SUB.W D1,46(A6); JSR 49fc6.l.
    case 0x3aefc:
        if(!ob2c_get(c,r.a[6],0x36,2,value))return false;am_word(r.d[0],r.d[0]-value);
        if(!ob2c_get(c,r.a[6],0x3a,2,value))return false;am_word(r.d[1],r.d[1]-value);
        if(!ob2c_get(c,r.a[6],0x42,2,value) || !ob2c_put(c,r.a[6],0x42,2,value-r.d[0]))return false;
        if(!ob2c_get(c,r.a[6],0x46,2,value) || !ob2c_put(c,r.a[6],0x46,2,value-r.d[1]))return false;
        return am_call(c,0x49fc6,0x3af12);
    case 0x3af12:return ob2c_carry(c,0x3af1c,0x3af16);                       // BCC.W 3af1c (C returned by 49fc6).
    case 0x3af16:case 0x3af64:r.pc=0x2a00;return true;                       // JMP 2a00.l.
    // MOVEQ #0,D0; MOVE.B 13(A6),D0; SUBI.W #ff,D0; ASR.W #3,D0; SUB.B D0,13(A6); RTS.
    case 0x3af1c: {
        if(!ob2c_get(c,r.a[6],0x13,1,value))return false;
        const std::uint32_t word=(value-0xffU)&65535U;
        r.d[0]=(word>>3)|((word&0x8000U)!=0U?0xe000U:0U);                        // ASR.W #3 on the WORD (upper WORD stays 0).
        std::uint32_t field=0;if(!ob2c_get(c,r.a[6],0x13,1,field) || !ob2c_put(c,r.a[6],0x13,1,field-r.d[0]))return false;
        return am_return(c);
    }
    // MOVE.W 36(A6),D0; MOVE.W 3a(A6),D1; ADD.W D0,2e(A6); ADD.W D1,32(A6); MOVEA.L #3d198,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3af2e:
        if(!ob2c_get(c,r.a[6],0x36,2,value))return false;am_word(r.d[0],value);
        if(!ob2c_get(c,r.a[6],0x3a,2,value))return false;am_word(r.d[1],value);
        if(!ob2c_get(c,r.a[6],0x2e,2,value) || !ob2c_put(c,r.a[6],0x2e,2,value+r.d[0]))return false;
        if(!ob2c_get(c,r.a[6],0x32,2,value) || !ob2c_put(c,r.a[6],0x32,2,value+r.d[1]))return false;
        r.a[1]=0x3d198;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3af4e);
    case 0x3af4e:if(!ob2c_put(c,r.a[6],0,4,0x3af54))return false;r.pc=0x3af54;return true;   // MOVE.L #3af54,(A6).
    case 0x3af5a:return am_call(c,0x49fc6,0x3af60);                          // JSR 49fc6.l.
    case 0x3af60:return ob2c_carry(c,0x3af6a,0x3af64);                       // BCC.W 3af6a.
    // ---- 3af86 (28ae child of 38d56): MOVEA.L c(A6),A0; MOVE.W 88(A0),D0; JSR 1d198.l.
    case 0x3af86:
        if(!ob2c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ob2c_get(c,r.a[0],0x88,2,value))return false;
        am_word(r.d[0],value);return am_call(c,0x1d198,0x3af94);
    // MOVEA.L c(A6),A0; MOVE.W 86(A6),D0; JSR 1bf80.l.
    case 0x3af94:
        if(!ob2c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ob2c_get(c,r.a[6],0x86,2,value))return false;
        am_word(r.d[0],value);return am_call(c,0x1bf80,0x3afa2);
    // ANDI.W #ff,D0; ADD.W D0,D0; LEA 3af74(PC),A0; MOVE.W (A0,D0.W),D0; MOVE.W D0,D7; MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1;
    // ADD.W D7,D7 (x2); MOVEA.L (A1,D7.W),A1; JSR 49f8c.l.
    case 0x3afa2:
        am_word(r.d[0],r.d[0]&0xffU);am_word(r.d[0],r.d[0]+r.d[0]);r.a[0]=OB2C_SCRIPT_INDEX;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);am_word(r.d[7],value);
        am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);if(!ob2c_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
        am_word(r.d[7],r.d[7]+r.d[7]);am_word(r.d[7],r.d[7]+r.d[7]);
        if(!am_read(c,am_index(r.a[1],r.d[7]),4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,0x3afcc);
    // MOVEA.L c(A6),A4; MOVE.W 88(A4),D0; LEA 3af6c(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x3afcc:
        if(!ob2c_get(c,r.a[6],0xc,4,value))return false;r.a[4]=value;if(!ob2c_get(c,r.a[4],0x88,2,value))return false;am_word(r.d[0],value);
        r.a[0]=OB2C_SOUND_TABLE;am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);
        am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3afe8);
    case 0x3afe8:r.d[0]=0;r.d[1]=0;return am_call(c,0x49290,0x3aff2);       // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l.
    case 0x3aff2:return am_call(c,0x491c4,0x3aff8);                          // JSR 491c4.l.
    case 0x3aff8:if(!ob2c_put(c,r.a[6],0,4,0x3affe))return false;r.pc=0x3affe;return true;   // MOVE.L #3affe,(A6).
    // MOVE.W #5,D0; MOVE.W #23,D1; BTST.B #0,15(A6); BEQ.W 3b012.
    case 0x3affe:am_word(r.d[0],5);am_word(r.d[1],0x23);if(!ob2c_bit(c,0x15,0,bit))return false;r.pc=bit?0x3b010:0x3b012;return true;
    case 0x3b010:ob2c_neg_w(r.d[0]);r.pc=0x3b012;return true;
    // MOVE.W D0,2e(A6); MOVE.W D1,32(A6); JSR 43e34.l.
    case 0x3b012:if(!ob2c_put(c,r.a[6],0x2e,2,r.d[0]) || !ob2c_put(c,r.a[6],0x32,2,r.d[1]))return false;return am_call(c,0x43e34,0x3b020);
    case 0x3b020:return am_call(c,0x49fc6,0x3b026);                          // JSR 49fc6.l.
    case 0x3b026:return ob2c_carry(c,0x3b03a,0x3b02a);                       // BCC.W 3b03a.
    // MOVEA.L c(A6),A0; MOVE.B #ff,62(A0); JMP 2a00.l.
    case 0x3b02a:
        if(!ob2c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ob2c_put(c,r.a[0],0x62,1,0xff))return false;r.pc=0x2a00;return true;
    // ---- 1bf80: LEA -7348(A5),A0; TST.B D0; BEQ.W 1bf8e / LEA -7258(A5),A0 / MOVE.B 9f(A0),D0; RTS.
    case 0x1bf80:r.a[0]=am_index(r.a[5],0x8cb8);r.pc=(r.d[0]&255U)==0U?0x1bf8e:0x1bf8a;return true;
    case 0x1bf8a:r.a[0]=am_index(r.a[5],0x8da8);r.pc=0x1bf8e;return true;
    case 0x1bf8e:if(!ob2c_get(c,r.a[0],0x9f,1,value))return false;am_byte(r.d[0],value);return am_return(c);
    // ---- 1d198: ADD.W D0,D0 (x3); LEA 1d1b0(PC,D0.W),A0; MOVEA.L (A0)+,A1; MOVE.L (A1),22(A6); MOVE.L (A0),D0; MOVE.W D0,20(A6); RTS.
    case 0x1d198:
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);r.a[0]=am_index(OB2C_ANIM_TABLE,r.d[0]);
        if(!am_read(c,r.a[0],4,value))return false;r.a[1]=value;r.a[0]+=4U;
        if(!am_read(c,r.a[1],4,value) || !ob2c_put(c,r.a[6],0x22,4,value))return false;
        if(!am_read(c,r.a[0],4,value))return false;r.d[0]=value;if(!ob2c_put(c,r.a[6],0x20,2,r.d[0]))return false;return am_return(c);
    default:return am_error(c,"unsupported animation objects b2c PC");
    }
}
}
