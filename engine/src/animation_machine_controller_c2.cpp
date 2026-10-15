#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Controller C2 (F5 contract animation-machine-controller-c2-contract.md, main decisions in animation-machine-controller-d9-decision.md):
// the controller transitions and teardown (c4cc node teardown, c686 demo end, c76a game stage end, c7c6 restart, c80e continue, the card
// request c2fa, the waiting states c6c0 c79a c82e c89c c8e8 c940), their helpers (input mode 3162, frame counter 100e / 101c, card menu table
// bbd4, game initialisation 47570 4755e e62ec 4823a, RNG table 49a1a, 4e1cc) and, for the game mode continuation, the child b300 / b344
// (stage end menu) with the four menu item handlers a856 a876 a896 a8bc and the common a75a. 164 block starts.
//
// Boundaries (set the PC only): the BIOS c00444 (JMP at c6c8 c7c0 c982 a8c8: the frame driver reports it), the card BIOS c00468 (JSR at
// c310, return c316; the frame driver resumes it), the C1 tail c988 / gates c73e c7fc, the C3 boot c610 and every routed callee of other units.
// ROM write: c690 CLR.W 180.l (reached only for a non-zero ROM WORD 180) fails in am_write.
//
// Carry: no known C is produced. The consumers c87e and c916 read the C returned by 289e and fail with a checked error when it is Unknown.
// c964 / c97a (BNE after JSR 4a974) read the Z of the TST.B (A0) that ended 4a974: Z is not carried across the RTS but recomputed from
// BYTE (A0), which must be one of the four work RAM bytes 4a974 can point at (the C1 rule). The FLOW blocks keep the incoming C.
const std::uint32_t AC2_BIOS_RETURN=0xc00444U;
const std::uint32_t AC2_BIOS_CARD=0xc00468U;
// The displacement -d(An) as the 16-bit pattern am_index sign extends.
std::uint32_t ac2_neg(std::uint32_t d) {return (0x10000U-d)&65535U;}
bool ac2_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ac2_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BYTE d16(An): TST.B / CMPI.B #imm + BEQ.W equal_pc (fall through to other_pc). Only Z changes.
bool ac2_byte_branch(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t compare,std::uint32_t equal_pc,
    std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ac2_get(c,base,displacement,1,value))return false;
    c.s.pc=value==compare?equal_pc:other_pc;return true;
}
// BCC / BCS on the C of the callee that just returned: Unknown C is a checked error.
bool ac2_branch_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"controller c2 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// BNE.W nonzero_pc after the Z of 4a974 (fall through to zero_pc), recomputed from BYTE (A0): A0 is 10fdb0 / 10fdb1 (7db0(A5), A5 = 108000,
// plus D0.W in 0..1) or 100004 / 100005; RTS only reads the stack, so the byte is unchanged since the TST.B.
bool ac2_credit_flag(AnimationMachineContext& c,std::uint32_t nonzero_pc,std::uint32_t zero_pc) {
    const std::uint32_t a0=c.s.a[0];
    if(a0!=0x10fdb0U && a0!=0x10fdb1U && a0!=0x100004U && a0!=0x100005U)return am_error(c,"unsupported animation controller flag source");
    std::uint32_t value=0;if(!am_read(c,a0,1,value))return false;
    c.s.pc=value!=0U?nonzero_pc:zero_pc;return true;
}
// MOVE.L #handler,(A6): the callback install; the original block then runs on into the installed PC.
bool ac2_install(AnimationMachineContext& c,std::uint32_t callback) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=callback;return true;
}
// The common JSR / BSR shape: the callee is another unit's block (boundary), the return PC the next block of this unit.
bool ac2_call(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    return am_call(c,target,return_pc);
}
// MOVEA.L #child,A0; MOVE.W #d0,D0; JSR 28ae.l (allocate a child node).
bool ac2_spawn(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t d0,std::uint32_t return_pc) {
    c.s.a[0]=callback;am_word(c.s.d[0],d0);return am_call(c,0x28ae,return_pc);
}
// The 49a3e body: ADDI.W #7925,D1; ADD.W D0,D1; MULU.W D1,D1; LSR.L #8,D1; EXG.L D1,D0; MOVE.W D0,(A0)+; DBRA D7. Registers keep their upper words
// exactly as the 68000 does (the word operations leave bits 31..16, EXG swaps the full registers).
bool ac2_random_step(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    am_word(r.d[1],r.d[1]+0x7925U);am_word(r.d[1],r.d[1]+r.d[0]);
    r.d[1]=(r.d[1]&65535U)*(r.d[1]&65535U);r.d[1]>>=8;
    const std::uint32_t swap=r.d[1];r.d[1]=r.d[0];r.d[0]=swap;
    if(!am_write(c,r.a[0],2,r.d[0]&65535U))return false;
    r.a[0]+=2U;
    am_word(r.d[7],r.d[7]-1U);
    r.pc=(r.d[7]&65535U)!=65535U?0x49a3eU:0x49a50U;return true;
}
// 3162 (input mode): LEA 108000,A5; CLR.L -3358(A5); CLR.W -3354(A5); CLR.L -3352(A5); CLR.W -334e(A5); CMPI.W #2,D0; BCS.W 3188.
bool ac2_input_mode(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    r.a[5]=0x108000U;r.a[0]=am_index(r.a[5],ac2_neg(0x3358));
    if(!am_write(c,r.a[0],4,0))return false;
    r.a[0]+=4U;
    if(!am_write(c,r.a[0],2,0))return false;
    r.a[0]=am_index(r.a[5],ac2_neg(0x3352));
    if(!am_write(c,r.a[0],4,0))return false;
    r.a[0]+=4U;
    if(!am_write(c,r.a[0],2,0))return false;
    r.pc=(r.d[0]&65535U)<2U?0x3188U:0x3180U;return true;
}
// 3188 (replay mode): BYTE 104cd4 := 1, the replay / recorder pointers from the two tables indexed by 4 * D0.W, the counters cleared, then ROM WORD 180.
bool ac2_replay_mode(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ac2_put(c,r.a[5],ac2_neg(0x332c),1,1))return false;
    am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    r.a[0]=0xf0dfeU;
    if(!am_read(c,am_index(r.a[0],r.d[0]&65535U),4,value) || !ac2_put(c,r.a[5],ac2_neg(0x333c),4,value))return false;
    r.a[0]=0xf1a06U;
    if(!am_read(c,am_index(r.a[0],r.d[0]&65535U),4,value) || !ac2_put(c,r.a[5],ac2_neg(0x3338),4,value))return false;
    am_word(r.d[0],0);
    if(!ac2_put(c,r.a[5],ac2_neg(0x3334),2,0) || !ac2_put(c,r.a[5],ac2_neg(0x3332),2,0) || !ac2_put(c,r.a[5],ac2_neg(0x333e),2,0) ||
        !ac2_put(c,r.a[5],ac2_neg(0x3330),1,0))return false;
    if(!am_read(c,0x180U,2,value))return false;
    am_word(r.d[0],value);
    r.pc=value==0U?0x31d4U:0x31c4U;return true;
}
}
bool animation_controller_c2_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- Frame counter 100e and the IRQ requirement byte 101c.
    case 0x100e:
        if(!ac2_put(c,r.a[5],ac2_neg(0x7ff2),2,0) || !ac2_put(c,r.a[5],ac2_neg(0x7762),2,0))return false;
        return am_return(c);
    case 0x101c:
        if(!ac2_put(c,r.a[5],ac2_neg(0x7fe9),1,r.d[0]))return false;
        return am_return(c);
    // ---- Input mode 3162: realtime (BYTE 104cd4 := 0) for D0.W >= 2, replay for 0 / 1 (the recorder fill 31c4 / 31ce needs ROM WORD 180 != 0).
    case 0x3162:return ac2_input_mode(c);
    case 0x3180:
        if(!ac2_put(c,r.a[5],ac2_neg(0x332c),1,0))return false;
        return am_return(c);
    case 0x3188:return ac2_replay_mode(c);
    case 0x31c4:
        if(!ac2_get(c,r.a[5],ac2_neg(0x3338),4,value))return false;
        r.a[0]=value;r.d[1]=0xffffffffU;am_word(r.d[7],0x5ffU);r.pc=0x31ce;return true;
    case 0x31ce:
        if(!am_write(c,r.a[0],1,r.d[1]&255U))return false;
        r.a[0]+=1U;am_word(r.d[7],r.d[7]-1U);
        r.pc=(r.d[7]&65535U)!=65535U?0x31ceU:0x31d4U;return true;
    case 0x31d4:return am_return(c);
    // ---- Card menu table preparation bbd4 (c2fa).
    case 0xbbd4:
        r.a[0]=0x107f1cU;r.a[1]=0xbb8eU;am_word(r.d[7],0x18U);return ac2_call(c,0xbbb8,0xbbe4);
    case 0xbbe4:
        r.a[0]=am_index(r.a[5],ac2_neg(0xe4));
        if(!ac2_put(c,r.a[5],ac2_neg(0xcf),1,0xffU))return false;
        am_word(r.d[7],0x16U);return ac2_call(c,0xbb74,0xbbf4);
    case 0xbbf4:
        if(!ac2_put(c,r.a[5],ac2_neg(0xce),2,r.d[0]))return false;
        return am_return(c);
    // ---- Card request c2fa: the BIOS card call c00468 (return c316), then the card child c250 or the failure byte.
    case 0xc2fa:return ac2_call(c,0xbbd4,0xc2fe);
    case 0xc2fe:
        if(!am_push(c,4,r.a[6]) || !am_write(c,0x10fdc4U,1,1U) || !am_write(c,0x10fdceU,2,0x268U))return false;
        return am_call(c,AC2_BIOS_CARD,0xc316);
    case 0xc316:
        if(!am_pop(c,4,value))return false;
        r.a[6]=value;r.a[5]=0x108000U;
        return ac2_byte_branch(c,r.a[5],0x7dc6,0,0xc326,0xc35c);
    case 0xc326:
        if(!ac2_get(c,r.a[5],0x7dd0,2,value))return false;
        am_word(r.d[0],value);r.pc=(value&1U)==0U?0xc35cU:0xc332U;return true;
    case 0xc332:
        if(!ac2_put(c,r.a[6],0x62,1,0))return false;
        return ac2_spawn(c,0xc250,0,0xc346);
    case 0xc346:
        if(!ac2_put(c,r.a[0],0x76,4,0xbef0U) || !ac2_put(c,r.a[0],0x7a,2,4) || !ac2_put(c,r.a[0],0x7c,2,4))return false;
        return am_return(c);
    case 0xc35c:
        if(!ac2_put(c,r.a[6],0x62,1,0xffU))return false;
        return am_return(c);
    // ---- Teardown c4cc: the cleanups 3dce / 2a0a, then every node after the controller up to the list head 100820 is removed by 2a84.
    case 0xc4cc:return ac2_call(c,0x3dce,0xc4d2);
    case 0xc4d2:return ac2_call(c,0x2a0a,0xc4d8);
    case 0xc4d8:
        if(!ac2_get(c,r.a[6],8,4,value))return false;
        r.a[0]=value;r.pc=0xc4dc;return true;
    case 0xc4dc:r.pc=r.a[0]==0x100820U?0xc4f6U:0xc4e6U;return true;
    case 0xc4e6:
        if(!am_push(c,4,r.a[0]))return false;
        return ac2_call(c,0x2a84,0xc4ee);
    case 0xc4ee:
        if(!am_pop(c,4,value))return false;
        r.a[0]=value;
        if(!ac2_get(c,r.a[0],8,4,value))return false;
        r.a[0]=value;r.pc=0xc4dc;return true;
    case 0xc4f6:return am_return(c);
    // ---- Demo end c686: ROM WORD 180 (0 in the canonical ROM), teardown, screen reset, the child e66aa, the waiting state c6c0.
    case 0xc686:
        if(!am_read(c,0x180U,2,value))return false;
        r.pc=value==0U?0xc69aU:0xc690U;return true;
    case 0xc690:
        if(!am_write(c,0x180U,2,0))return false;
        r.pc=0xc610;return true;
    case 0xc69a:return ac2_call(c,0xc4cc,0xc69e);
    case 0xc69e:return ac2_call(c,0xcaf0,0xc6a2);
    case 0xc6a2:return ac2_call(c,0xca76,0xc6a6);
    case 0xc6a6:return ac2_spawn(c,0xe66aaU,0,0xc6b6);
    case 0xc6b6:
        if(!ac2_put(c,r.a[6],0x62,1,0))return false;
        return ac2_install(c,0xc6c0);
    case 0xc6c0:return ac2_byte_branch(c,r.a[6],0x62,0,0xc73e,0xc6c8);
    case 0xc6c8:r.pc=AC2_BIOS_RETURN;return true;
    // ---- Game start c74c, stage end transition c76a, waiting state c79a, restart c7c6.
    case 0xc74c:r.d[0]=0;return ac2_call(c,0x8bbc,0xc754);
    case 0xc754:am_byte(r.d[0],2U);return ac2_call(c,0x101c,0xc75e);
    case 0xc75e:return ac2_byte_branch(c,r.a[5],0x7d82,0,0xc76a,0xc766);
    case 0xc766:r.pc=0xc80e;return true;
    case 0xc76a:r.d[0]=0xffffffffU;return ac2_call(c,0x3162,0xc772);
    case 0xc772:return ac2_call(c,0xc4cc,0xc776);
    case 0xc776:return ac2_call(c,0xca76,0xc77a);
    case 0xc77a:return ac2_call(c,0xcaf0,0xc77e);
    case 0xc77e:
        if(!ac2_put(c,r.a[6],0x62,1,0))return false;
        return ac2_spawn(c,0xb300,0x14U,0xc794);
    case 0xc794:return ac2_install(c,0xc79a);
    case 0xc79a:return ac2_byte_branch(c,r.a[5],0x7db6,1,0xc80e,0xc7a4);
    case 0xc7a4:return ac2_byte_branch(c,r.a[5],0x7db7,1,0xc80e,0xc7ae);
    case 0xc7ae:
        if(!ac2_get(c,r.a[6],0x62,1,value))return false;
        am_byte(r.d[0],value);r.pc=value==2U?0xc7c6U:0xc7baU;return true;
    case 0xc7ba:r.pc=(r.d[0]&255U)==0U?0xc988U:0xc7c0U;return true;
    case 0xc7c0:r.pc=AC2_BIOS_RETURN;return true;
    case 0xc7c6:r.d[0]=0xffffffffU;return ac2_call(c,0x49a1a,0xc7ce);
    case 0xc7ce:return ac2_call(c,0xc4cc,0xc7d2);
    case 0xc7d2:return ac2_call(c,0xcaf0,0xc7d6);
    case 0xc7d6:return ac2_call(c,0x47570,0xc7dc);
    case 0xc7dc:am_word(r.d[0],8U);return ac2_call(c,0x4823a,0xc7e6);
    case 0xc7e6:
        r.a[0]=am_index(r.a[5],ac2_neg(0x74d0));r.a[1]=0x477e4U;return ac2_call(c,0x2a28,0xc7f6);
    case 0xc7f6:return ac2_install(c,0xc7fc);
    // ---- Continue path c80e and the waiting states c82e c874 c89c c8e8 c90c c940.
    case 0xc80e:
        if(!ac2_put(c,r.a[5],0x702a,2,0))return false;
        r.d[0]=0xffffffffU;return ac2_call(c,0x3162,0xc81a);
    case 0xc81a:return ac2_call(c,0xc4cc,0xc81e);
    case 0xc81e:r.d[0]=0xffffffffU;return ac2_call(c,0x49a1a,0xc826);
    case 0xc826:
        if(!am_write(c,r.a[6],4,0xc82eU))return false;
        return am_return(c);
    case 0xc82e:return ac2_byte_branch(c,r.a[5],0x7d82,0,0xc882,0xc836);
    case 0xc836:return ac2_byte_branch(c,r.a[5],0x7d8e,0,0xc882,0xc83e);
    case 0xc83e:r.d[0]=0xffffffffU;return ac2_call(c,0x49a1a,0xc846);
    case 0xc846:return ac2_call(c,0xc4cc,0xc84a);
    case 0xc84a:return ac2_call(c,0xcaf0,0xc84e);
    case 0xc84e:return ac2_call(c,0x47570,0xc854);
    case 0xc854:am_word(r.d[0],8U);return ac2_call(c,0x4823a,0xc85e);
    case 0xc85e:
        r.a[0]=am_index(r.a[5],ac2_neg(0x74d0));r.a[1]=0x477e4U;return ac2_call(c,0x2a28,0xc86e);
    case 0xc86e:return ac2_install(c,0xc874);
    case 0xc874:
        r.a[0]=am_index(r.a[5],ac2_neg(0x74d0));return ac2_call(c,0x289e,0xc87e);
    case 0xc87e:return ac2_branch_carry(c,0xc882,0xc988);
    case 0xc882:return ac2_call(c,0xc4cc,0xc886);
    case 0xc886:return ac2_call(c,0xcaf0,0xc88a);
    case 0xc88a:return ac2_call(c,0x47570,0xc890);
    case 0xc890:return ac2_call(c,0xc2fa,0xc896);
    case 0xc896:return ac2_install(c,0xc89c);
    case 0xc89c:return ac2_byte_branch(c,r.a[6],0x62,0,0xc988,0xc8a4);
    case 0xc8a4:return ac2_install(c,0xc8aa);
    case 0xc8aa:return ac2_call(c,0x9060,0xc8b0);
    case 0xc8b0:return ac2_call(c,0xc4cc,0xc8b4);
    case 0xc8b4:return ac2_call(c,0xcaf0,0xc8b8);
    case 0xc8b8:
        if(!ac2_put(c,r.a[6],0x7c,2,0x30ffU))return false;
        return ac2_call(c,0xe7bf4,0xc8c4);
    case 0xc8c4:return ac2_call(c,0x4e1cc,0xc8ca);
    case 0xc8ca:return ac2_call(c,0xca48,0xc8ce);
    case 0xc8ce:
        if(!ac2_put(c,r.a[6],0x62,1,0))return false;
        return ac2_spawn(c,0xde660U,0,0xc8e2);
    case 0xc8e2:return ac2_install(c,0xc8e8);
    case 0xc8e8:return ac2_byte_branch(c,r.a[6],0x62,0,0xc988,0xc8f0);
    case 0xc8f0:
        if(!ac2_put(c,r.a[6],0x7c,2,0x9ffU))return false;
        r.a[0]=am_index(r.a[5],ac2_neg(0x74d0));r.a[1]=0x477e4U;return ac2_call(c,0x2a28,0xc906);
    case 0xc906:return ac2_install(c,0xc90c);
    case 0xc90c:
        r.a[0]=am_index(r.a[5],ac2_neg(0x74d0));return ac2_call(c,0x289e,0xc916);
    case 0xc916:return ac2_branch_carry(c,0xc91a,0xc988);
    case 0xc91a:return ac2_call(c,0xc4cc,0xc91e);
    case 0xc91e:return ac2_call(c,0xcaf0,0xc922);
    case 0xc922:return ac2_call(c,0xca76,0xc926);
    case 0xc926:return ac2_spawn(c,0xe66aaU,0,0xc936);
    case 0xc936:
        if(!ac2_put(c,r.a[6],0x62,1,0))return false;
        return ac2_install(c,0xc940);
    case 0xc940:return ac2_byte_branch(c,r.a[6],0x62,0,0xc948,0xc982);
    case 0xc948:
        if(!am_read(c,0x10fd82U,1,value))return false;
        r.pc=value==0U?0xc97eU:0xc952U;return true;
    case 0xc952:case 0xc968:
        if(!ac2_get(c,r.a[5],ac2_neg(0x334b),1,value))return false;
        if(r.pc==0xc952)r.pc=(value&1U)==0U?0xc968U:0xc95cU;
        else r.pc=(value&4U)==0U?0xc97eU:0xc972U;
        return true;
    case 0xc95c:r.d[0]=0;return ac2_call(c,0x4a974,0xc964);
    case 0xc964:return ac2_credit_flag(c,0xc982,0xc968);
    case 0xc972:r.d[0]=1;return ac2_call(c,0x4a974,0xc97a);
    case 0xc97a:return ac2_credit_flag(c,0xc982,0xc97e);
    case 0xc97e:r.pc=0xc988;return true;
    case 0xc982:r.pc=AC2_BIOS_RETURN;return true;
    // ---- Game initialisation 47570 (4755e, e62ec), the stage selector 4823a and the RNG table 49a1a.
    case 0x4755e:r.d[0]=0;return ac2_call(c,0xe62ec,0x47566);
    case 0x47566:r.d[0]=1;return ac2_call(c,0xe62ec,0x4756e);
    case 0x4756e:return am_return(c);
    case 0x47570:
        if(!ac2_put(c,r.a[5],0x5683,1,0) || !ac2_put(c,r.a[5],0x5694,1,0) || !ac2_put(c,r.a[5],0x569c,1,0))return false;
        return ac2_call(c,0x100e,0x47582);
    case 0x47582:return ac2_call(c,0x4755e,0x47584);
    case 0x47584:r.d[0]=0;return ac2_call(c,0x4823a,0x4758a);
    case 0x4758a:r.a[0]=0;return ac2_call(c,0xe8a1c,0x47594);
    case 0x4823a:r.pc=(r.d[0]&65535U)<0x13U?0x48244U:0x48242U;return true;
    case 0x48242:r.d[0]=0;r.pc=0x48244;return true;
    case 0x48244:
        if(!ac2_put(c,r.a[5],0x5680,1,r.d[0]) || !ac2_put(c,r.a[5],0x5681,1,0))return false;
        return am_return(c);
    case 0x49a1a:
        r.a[5]=0x108000U;r.pc=(r.d[0]&65535U)==0U?0x49a34U:0x49a26U;return true;
    case 0x49a26:
        if(!am_read(c,0x10f02cU,2,value))return false;
        am_word(r.d[0],value+1U);
        if(!am_write(c,0x10f02cU,2,r.d[0]&65535U))return false;
        r.pc=0x49a34;return true;
    case 0x49a34:
        r.a[0]=am_index(r.a[5],0x56b4);am_word(r.d[7],0x36U);am_word(r.d[1],r.d[0]);r.pc=0x49a3e;return true;
    case 0x49a3e:return ac2_random_step(c);
    case 0x49a50:
        r.a[0]-=2U;
        if(!ac2_put(c,r.a[5],0x5722,4,r.a[0]))return false;
        return am_return(c);
    case 0x4e1cc:
        if(!ac2_put(c,r.a[5],0x5d1e,1,0) || !ac2_put(c,r.a[5],0x5d1f,1,0) || !ac2_put(c,r.a[5],0x5d20,1,0) || !ac2_put(c,r.a[5],0x5d21,1,0) ||
            !ac2_put(c,r.a[5],0x5d2a,1,0xffU) || !ac2_put(c,r.a[5],0x5d2b,1,0xffU))return false;
        r.a[0]=0x1009a8U;r.a[1]=0x4e68eU;return ac2_call(c,0x2a28,0x4e1f8);
    case 0x4e1f8:
        if(!ac2_put(c,r.a[0],0x76,2,0))return false;
        r.a[0]=0x100a6cU;r.a[1]=0x4e68eU;return ac2_call(c,0x2a28,0x4e20e);
    case 0x4e20e:
        if(!ac2_put(c,r.a[0],0x76,2,1))return false;
        return am_return(c);
    case 0xe62ec:r.pc=(r.d[0]&255U)!=0U?0xe62fcU:0xe62f2U;return true;
    case 0xe62f2:r.a[0]=0x10de14U;r.pc=0xe6302;return true;
    case 0xe62fc:r.a[0]=0x10de1cU;r.pc=0xe6302;return true;
    case 0xe6302:
        if(!am_write(c,r.a[0],4,0))return false;
        return am_return(c);
    // ---- Child b300 (game mode stage end menu) and b344 (menu loop).
    case 0xb300:return ac2_call(c,0x3d3a,0xb306);
    case 0xb306:return ac2_call(c,0xde424,0xb30c);
    case 0xb30c:r.a[0]=0xa810U;r.d[0]=3;r.d[1]=4;return ac2_call(c,0xa29c,0xb31a);
    case 0xb31a:r.a[0]=0xe84c8U;return ac2_call(c,0xa2b8,0xb326);
    case 0xb326:am_word(r.d[0],0x7095U);return ac2_call(c,0xddf9a,0xb330);
    case 0xb330:r.d[0]=0;r.d[1]=0;r.d[2]=0;r.d[3]=0;return ac2_call(c,0x8c16,0xb33e);
    case 0xb33e:return ac2_install(c,0xb344);
    case 0xb344:return ac2_call(c,0xa370,0xb34a);
    case 0xb34a:r.pc=(r.d[0]&255U)==0U?0xb360U:0xb350U;return true;
    case 0xb350:
        if(!ac2_get(c,r.a[6],0xc,4,value))return false;
        r.a[0]=value;
        if(!ac2_put(c,r.a[0],0x62,1,3))return false;
        r.pc=0x2a00;return true;
    case 0xb360:return am_return(c);
    // ---- Menu item handlers a856 a876 a896 a8bc and the common a75a.
    case 0xa75a:return ac2_call(c,0x9f36,0xa760);
    case 0xa760:
        if(!am_push(c,2,r.d[1]&65535U) || !am_push(c,2,r.d[0]&65535U))return false;
        return ac2_call(c,0x38e8,0xa76a);
    case 0xa76a:
        if(!am_pop(c,2,value))return false;
        am_word(r.d[0],r.d[0]+value);
        if(!am_pop(c,2,value))return false;
        am_word(r.d[1],value);return am_return(c);
    case 0xa856:return ac2_call(c,0xa73e,0xa85a);
    case 0xa876:return ac2_call(c,0xa73e,0xa87a);
    case 0xa896:return ac2_call(c,0xa73e,0xa89a);
    case 0xa8bc:return ac2_call(c,0xa73e,0xa8c0);
    case 0xa85a:r.pc=(r.d[0]&65535U)==3U?0xa868U:0xa860U;return true;
    case 0xa87a:r.pc=(r.d[0]&65535U)==3U?0xa888U:0xa880U;return true;
    case 0xa89a:r.pc=(r.d[0]&65535U)==3U?0xa8a8U:0xa8a0U;return true;
    case 0xa860:r.pc=(r.d[0]&65535U)!=2U?0xa874U:0xa868U;return true;
    case 0xa880:r.pc=(r.d[0]&65535U)!=2U?0xa894U:0xa888U;return true;
    case 0xa8a0:r.pc=(r.d[0]&65535U)!=2U?0xa8baU:0xa8a8U;return true;
    case 0xa868:return ac2_call(c,0xa75a,0xa86c);
    case 0xa888:return ac2_call(c,0xa75a,0xa88c);
    case 0xa86c:r.a[0]=0xa8f8U;r.pc=0xa71a;return true;
    case 0xa88c:r.a[0]=0xa952U;return ac2_call(c,0xa71a,0xa894);
    case 0xa8a8:return ac2_call(c,0x9f36,0xa8ae);
    case 0xa8ae:
        am_byte(r.d[0],r.d[0]+4U);am_byte(r.d[1],r.d[1]-2U);r.a[0]=0xaa24U;r.pc=0xa71a;return true;
    case 0xa8c0:r.pc=(r.d[0]&65535U)!=3U?0xa8ceU:0xa8c8U;return true;
    case 0xa8c8:r.pc=AC2_BIOS_RETURN;return true;
    case 0xa874:case 0xa894:case 0xa8ba:case 0xa8ce:return am_return(c);
    default:return am_error(c,"unsupported animation controller c2 PC");
    }
}
}
