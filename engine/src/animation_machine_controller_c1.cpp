#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Controller C1 (F5 contract animation-machine-controller-c1-contract.md, main decisions in animation-machine-controller-d9-decision.md):
// the per-frame controller gates c66a / c7fc, the common tail c988..ca20 with the credit / timer helpers, the BCD digit renderer
// 3670..3706, the credit text helpers c49c / c4f8 / 4a88e and the credit value helpers 4a944 / 4a974 / 4a9ca, the soft-dip bit tests
// 30bc / 30d4 and the replay-mode test 314c. 116 block starts.
//
// Carry: the known-C producers 30c8 30e0 3156 (ORI CCR, Set), 30ce 30e6 315c (ANDI CCR, Clear) and ca32 (CMPI.B #aa: borrow when the BYTE
// is below aa). The six consumers c4a0 c674 c67e c806 c996 c9ba read the C returned by ca32 / 289e / 314c / 30bc / 30d4 and fail with a
// checked error when it is Unknown. 4a974 ends with TST.B (A0); RTS and the callers 4a9d0 / 4a9da start with BEQ: the Z flag is not
// carried across the RTS but recomputed there from BYTE (A0), which is checked to be one of the four work RAM bytes 4a974 can point at.
// SBCD and the byte push (A7 changes by 2) follow the 68000.
const std::uint32_t AC1_DIP=0x10fd8fU;       // BIOS soft-dip BYTE tested by 30bc (bit 1) and 30d4 (bit 0).
const std::uint32_t AC1_CREDIT_BIOS=0xc00450U;
const std::uint32_t AC1_CREDIT_ANSWER=0x01010000U;
bool ac1_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ac1_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
bool ac1_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
// BCC / BCS on the C of the callee that just returned: Unknown C is a checked error.
bool ac1_branch_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"controller c1 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// BTST.B #bit,10fd8f.l; BEQ.W zero_pc (fall through to set_pc). Only Z changes, C is kept.
bool ac1_dip_test(AnimationMachineContext& c,unsigned int bit,std::uint32_t zero_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!am_read(c,AC1_DIP,1,value))return false;
    c.s.pc=(value&(1U<<bit))==0U?zero_pc:set_pc;return true;
}
// TST.B d16(An) / CMPI.B #imm,d16(An): BYTE at base + d16 (the caller decides the branch).
bool ac1_byte(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t& value) {
    return ac1_get(c,base,displacement,1,value);
}
// BYTE (A1) / WORD (A1) read of the credit helpers: the MVS backup RAM d00034 is not modelled (checked error).
bool ac1_read_a1(AnimationMachineContext& c,unsigned int size,std::uint32_t& value) {
    if(((c.s.a[1]&0xffffffU)&0xff0000U)==0xd00000U)return am_error(c,"unsupported animation controller backup RAM read");
    return am_read(c,c.s.a[1],size,value);
}
// Z of the TST.B (A0) that ended 4a974 (4a9b0 / 4a9c6), recomputed from BYTE (A0): A0 is 10fdb0 / 10fdb1 (7db0(A5), A5 = 108000, plus
// D0.W in 0..1) or 100004 / 100005; RTS only reads the stack, so the byte is unchanged.
bool ac1_flag_zero(AnimationMachineContext& c,bool& zero) {
    const std::uint32_t a0=c.s.a[0];
    if(a0!=0x10fdb0U && a0!=0x10fdb1U && a0!=0x100004U && a0!=0x100005U)return am_error(c,"unsupported animation controller flag source");
    std::uint32_t value=0;if(!am_read(c,a0,1,value))return false;
    zero=value==0U;return true;
}
// BEQ.W zero_pc after the Z of 4a974 (fall through to set_pc).
bool ac1_credit_flag(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t set_pc) {
    bool zero=false;if(!ac1_flag_zero(c,zero))return false;
    c.s.pc=zero?zero_pc:set_pc;return true;
}
// MOVE.B (A0),D2; BTST.B #0,D4; BNE.W odd_pc (fall through to even_pc).
bool ac1_digit_read(AnimationMachineContext& c,std::uint32_t odd_pc,std::uint32_t even_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[2],value);
    r.pc=(r.d[4]&1U)!=0U?odd_pc:even_pc;return true;
}
// ANDI.W #f,D2; BNE.B nonzero_pc (fall through to zero_pc).
void ac1_digit_mask(AnimationMachineState& r,std::uint32_t nonzero_pc,std::uint32_t zero_pc) {
    am_word(r.d[2],r.d[2]&0xfU);r.pc=(r.d[2]&65535U)!=0U?nonzero_pc:zero_pc;
}
// CMPI.W #1,D4; BNE.W different_pc (fall through to equal_pc).
void ac1_digit_last(AnimationMachineState& r,std::uint32_t different_pc,std::uint32_t equal_pc) {
    r.pc=(r.d[4]&65535U)!=1U?different_pc:equal_pc;
}
// MOVE.L A0,-(A7); LEA 370c(PC),A0; MOVE.B (A0,D2.W),D2; LEA 3650(PC),A0; JSR (A1). A1 is live: the callee is the PC it holds.
bool ac1_digit_draw(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_push(c,4,r.a[0]))return false;
    r.a[0]=0x370cU;if(!am_read(c,am_index(r.a[0],r.d[2]&65535U),1,value))return false;am_byte(r.d[2],value);
    r.a[0]=0x3650U;return am_call(c,r.a[1],return_pc);
}
// SUBQ.W #1,D4; BNE loop_pc (fall through to done_pc).
void ac1_digit_next(AnimationMachineState& r,std::uint32_t loop_pc,std::uint32_t done_pc) {
    am_word(r.d[4],r.d[4]-1U);r.pc=(r.d[4]&65535U)!=0U?loop_pc:done_pc;
}
// SBCD.B Ds,Dd as the 68000 (and the pinned Unicorn M68000 oracle, all 512 inputs of ca06) computes it: each decimal digit subtracts
// with the borrow of the digit below; a borrowing digit is corrected by -6. X = C = the borrow out of the high digit. The block only
// reaches it with a zero source byte. Z is not written (BCC is the only reader).
std::uint32_t ac1_sbcd(std::uint32_t destination,std::uint32_t source,bool borrow_in,bool& borrow_out) {
    int low=static_cast<int>(destination&15U)-static_cast<int>(source&15U)-(borrow_in?1:0);
    const bool low_borrow=low<0;
    if(low_borrow)low=(low-6)&15;
    int high=static_cast<int>((destination>>4)&15U)-static_cast<int>((source>>4)&15U)-(low_borrow?1:0);
    borrow_out=high<0;
    if(borrow_out)high=(high-6)&15;
    return (static_cast<std::uint32_t>(high&15)<<4)|static_cast<std::uint32_t>(low&15);
}
// ca06: MOVE.B 7a(A6),D1; MOVEQ #0,D2; SUBQ.B #8,D0; SBCD.B D2,D1; BCC.W ca18 (fall through to ca14).
bool ac1_timer(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ac1_get(c,r.a[6],0x7a,1,value))return false;am_byte(r.d[1],value);
    r.d[2]=0;
    const std::uint32_t low=r.d[0]&255U;const bool borrow_in=low<8U;am_byte(r.d[0],low-8U);
    bool borrow_out=false;am_byte(r.d[1],ac1_sbcd(r.d[1]&255U,r.d[2]&255U,borrow_in,borrow_out));
    r.pc=borrow_out?0xca14U:0xca18U;return true;
}
}
bool animation_controller_c1_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // Soft-dip bit tests (30bc bit 1, 30d4 bit 0) and their C producers.
    case 0x30bc:return ac1_dip_test(c,1,0x30ce,0x30c8);
    case 0x30d4:return ac1_dip_test(c,0,0x30e6,0x30e0);
    case 0x30c8:case 0x30e0:case 0x3156:return ac1_return_carry(c,AnimationCarrySet);
    case 0x30ce:case 0x30e6:case 0x315c:return ac1_return_carry(c,AnimationCarryClear);
    // Replay-mode test: BYTE 104cd4 (-332c(A5)) = 1 gives C Set.
    case 0x314c:
        if(!ac1_byte(c,r.a[5],0xccd4,value))return false;
        r.pc=value!=1U?0x315c:0x3156;return true;
    // BCD digit renderer: 3670 draws leading zeros, 3706 skips them (36c0 clears D3).
    case 0x3670:return ac1_digit_read(c,0x3680,0x367a);
    case 0x367a:am_byte(r.d[2],(r.d[2]&255U)>>4);r.pc=0x3682;return true;
    case 0x3680:r.a[0]+=1U;r.pc=0x3682;return true;
    case 0x3682:ac1_digit_mask(r,0x3690,0x3688);return true;
    case 0x3688:ac1_digit_last(r,0x3698,0x3690);return true;
    case 0x3690:am_byte(r.d[3],0xffU);r.pc=0x36a2;return true;
    case 0x3698:r.pc=(r.d[3]&255U)!=0U?0x36a2U:0x369eU;return true;
    case 0x369e:am_byte(r.d[2],0x10U);r.pc=0x36a2;return true;
    case 0x36a2:return ac1_digit_draw(c,0x36b2);
    case 0x36b2:
        if(!am_pop(c,4,value))return false;r.a[0]=value;ac1_digit_next(r,0x3670,0x36b8);return true;
    case 0x36b8:return am_return(c);
    case 0x36ba:r.a[1]=0x3650U;r.pc=0x3670;return true;
    case 0x36c0:am_byte(r.d[3],0);r.pc=0x36c2;return true;
    case 0x36c2:return ac1_digit_read(c,0x36d2,0x36cc);
    case 0x36cc:am_byte(r.d[2],(r.d[2]&255U)>>4);r.pc=0x36d4;return true;
    case 0x36d2:r.a[0]+=1U;r.pc=0x36d4;return true;
    case 0x36d4:ac1_digit_mask(r,0x36e2,0x36da);return true;
    case 0x36da:ac1_digit_last(r,0x36e6,0x36e2);return true;
    case 0x36e2:am_byte(r.d[3],0xffU);r.pc=0x36e6;return true;
    case 0x36e6:r.pc=(r.d[3]&255U)==0U?0x36feU:0x36ecU;return true;
    case 0x36ec:return ac1_digit_draw(c,0x36fc);
    case 0x36fc:
        if(!am_pop(c,4,value))return false;r.a[0]=value;r.pc=0x36fe;return true;
    case 0x36fe:ac1_digit_next(r,0x36c2,0x3702);return true;
    case 0x3702:am_swap(r.d[0]);return am_return(c);
    case 0x3706:r.a[1]=0x3650U;r.pc=0x36c0;return true;
    // Credit text (c49c; the BYTE 100964 test is ca32) and credit count (c4f8, with the byte push of c50e).
    case 0xc49c:return am_call(c,0xca32,0xc4a0);
    case 0xc4a0:return ac1_branch_carry(c,0xc4b6,0xc4a4);
    case 0xc4a4:return am_call(c,0x4a9ca,0xc4aa);
    case 0xc4aa:
        am_word(r.d[7],r.d[7]+r.d[7]);am_word(r.d[7],r.d[7]+r.d[7]);
        if(!am_read(c,am_index(0xc48cU,r.d[7]&65535U),4,value))return false;r.a[0]=value;r.pc=0xc4ba;return true;
    case 0xc4b6:r.a[0]=0xc46eU;r.pc=0xc4ba;return true;
    case 0xc4ba:am_word(r.d[0],0x7157U);r.a[1]=0xe84c8U;r.pc=0x3918;return true;
    case 0xc4f8:
        am_word(r.d[0],0x723dU);am_word(r.d[1],0xb5aU);am_word(r.d[2],5U);am_word(r.d[3],1U);
        return am_call(c,0x35f0,0xc50e);
    case 0xc50e:
        am_word(r.d[1],3U);
        if(!am_read(c,0x10fd8bU,1,value))return false;
        if(!am_push(c,1,value))return false; // A7 -= 2, the BYTE at the new (A7)
        r.a[0]=r.a[7];
        if(!am_read(c,r.a[0],1,value))return false;
        if(!am_write(c,r.a[0],1,(value+1U)&255U))return false;
        am_word(r.d[4],1U);return am_call(c,0x3706,0xc526);
    case 0xc526:
        if(!am_pop(c,1,value))return false;am_byte(r.d[0],value);return am_return(c);
    // Demo gate c654 / c66a (BYTE 104cd4 = 1 replay): C2 owns c686 (transition) and c74c (game start).
    case 0xc654:
        r.a[0]=am_index(r.a[5],0x8b30);r.a[1]=0x477e4U;return am_call(c,0x2a28,0xc664);
    case 0xc664:
        if(!am_write(c,r.a[6],4,0xc66aU))return false;r.pc=0xc66a;return true;
    case 0xc66a:
        r.a[0]=am_index(r.a[5],0x8b30);return am_call(c,0x289e,0xc674);
    case 0xc674:return ac1_branch_carry(c,0xc686,0xc678);
    case 0xc678:return am_call(c,0x314c,0xc67e);
    case 0xc67e:return ac1_branch_carry(c,0xc686,0xc682);
    case 0xc682:r.pc=0xc724;return true;
    // Mode check: BYTE 100012 (-7fee(A5)) = 2 is the game mode (C2 c74c).
    case 0xc724:case 0xc73e:
        if(!ac1_byte(c,r.a[5],0x8012,value))return false;
        r.pc=value==2U?0xc74cU:(r.pc==0xc724?0xc72eU:0xc748U);return true;
    case 0xc72e:
        if(!ac1_get(c,r.a[6],0x81,1,value))return false;
        r.pc=value==0U?0xc988U:0xc736U;return true;
    case 0xc736:return am_call(c,0xc49c,0xc73a);
    case 0xc73a:case 0xc748:r.pc=0xc988;return true;
    // Game gate c7fc: a stage controller node whose callback is not 270e keeps the tail, an idle one transitions (C2 c76a).
    case 0xc7fc:
        r.a[0]=am_index(r.a[5],0x8b30);return am_call(c,0x289e,0xc806);
    case 0xc806:return ac1_branch_carry(c,0xc80a,0xc988);
    case 0xc80a:r.pc=0xc76a;return true;
    // Common tail: credit text flag 81, change detection 7e / 80, countdown 78, BCD timer 7a / 7b with the stop flag 83.
    case 0xc988:
        if(!ac1_get(c,r.a[6],0x81,1,value))return false;
        r.pc=value==0U?0xc9c2U:0xc990U;return true;
    case 0xc990:return am_call(c,0x30bc,0xc996);
    case 0xc996:return ac1_branch_carry(c,0xc9ac,0xc99a);
    case 0xc99a:
        am_word(r.d[0],0x709dU);am_word(r.d[2],0x737dU);am_word(r.d[1],3U);return am_call(c,0x4a88e,0xc9ac);
    case 0xc9ac:
        if(!ac1_get(c,r.a[6],0x82,1,value))return false;
        r.pc=value!=0U?0xc9c2U:0xc9b4U;return true;
    case 0xc9b4:return am_call(c,0x30d4,0xc9ba);
    case 0xc9ba:return ac1_branch_carry(c,0xc9c2,0xc9be);
    case 0xc9be:return am_call(c,0xc4f8,0xc9c2);
    case 0xc9c2:
        if(!ac1_get(c,r.a[6],0x81,1,value) || !ac1_put(c,r.a[6],0x82,1,value))return false;
        return am_call(c,0x4a944,0xc9ce);
    case 0xc9ce:
        if(!ac1_get(c,r.a[6],0x7e,2,value))return false;
        r.pc=(r.d[0]&65535U)==value?0xc9deU:0xc9d6U;return true;
    case 0xc9d6:
        if(!ac1_put(c,r.a[6],0x7e,2,r.d[0]) || !ac1_put(c,r.a[6],0x80,1,0))return false;
        r.pc=0xc9de;return true;
    case 0xc9de:
        if(!ac1_get(c,r.a[6],0x80,1,value) || !ac1_put(c,r.a[6],0x80,1,value+6U))return false;
        if(!ac1_get(c,r.a[6],0x78,2,value))return false;
        am_word(r.d[0],value);r.pc=value==0U?0xc9f6U:0xc9eaU;return true;
    case 0xc9ea: {
        const std::uint32_t before=r.d[0]&65535U;
        am_word(r.d[0],before-4U);r.pc=before<4U?0xc9f0U:0xc9f2U;return true;
    }
    case 0xc9f0:r.d[0]=0;r.pc=0xc9f2;return true;
    case 0xc9f2:
        if(!ac1_put(c,r.a[6],0x78,2,r.d[0]))return false;r.pc=0xc9f6;return true;
    case 0xc9f6:
        if(!ac1_get(c,r.a[6],0x83,1,value))return false;
        r.pc=value!=0U?0xca20U:0xc9feU;return true;
    case 0xc9fe:
        if(!ac1_get(c,r.a[6],0x7a,2,value))return false;
        am_word(r.d[0],value);r.pc=value==0U?0xca20U:0xca06U;return true;
    case 0xca06:return ac1_timer(c);
    case 0xca14:r.d[0]=0;r.d[1]=0;r.pc=0xca18;return true;
    case 0xca18:
        if(!ac1_put(c,r.a[6],0x7b,1,r.d[0]) || !ac1_put(c,r.a[6],0x7a,1,r.d[1]))return false;
        r.pc=0xca20;return true;
    case 0xca20:return am_return(c);
    // CMPI.B #aa,-769c(A5); RTS: C = BYTE 100964 below aa.
    case 0xca32:
        if(!ac1_byte(c,r.a[5],0x8964,value))return false;
        return ac1_return_carry(c,value<0xaaU?AnimationCarrySet:AnimationCarryClear);
    // Credit text 4a88e: the credit BYTE pointer A1 (100004 / 10fe00 / d00034), two digits (the second after a BSR when 100003 is set).
    case 0x4a88e:
        if(!ac1_get(c,r.a[5],0x7d82,1,value))return false;
        r.pc=value!=0U?0x4a89eU:0x4a896U;return true;
    case 0x4a896:r.a[1]=am_index(r.a[5],0x8004);r.pc=0x4a8b0;return true;
    case 0x4a89e:
        r.a[1]=0xd00034U;
        if(!ac1_get(c,r.a[5],0x7e80,1,value))return false;
        r.pc=value==0U?0x4a8b0U:0x4a8acU;return true;
    case 0x4a8ac:r.a[1]=am_index(r.a[5],0x7e00);r.pc=0x4a8b0;return true;
    case 0x4a8b0:
        if(!am_read(c,0x100003U,1,value))return false;
        r.pc=value==0U?0x4a8ccU:0x4a8baU;return true;
    case 0x4a8ba:
        if(!am_push(c,2,r.d[2]) || !am_push(c,4,r.a[1]))return false;
        return am_call(c,0x4a8ce,0x4a8c2);
    case 0x4a8c2:
        if(!am_pop(c,4,value))return false;r.a[1]=value;
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        r.a[1]+=1U;r.pc=0x4a8ce;return true;
    case 0x4a8cc:am_word(r.d[0],r.d[2]);r.pc=0x4a8ce;return true;
    case 0x4a8ce:
        r.a[0]=0x4a903U;
        if(!ac1_read_a1(c,1,value))return false;
        r.pc=value>=2U?0x4a8deU:0x4a8daU;return true;
    case 0x4a8da:r.a[0]=0x4a8f8U;r.pc=0x4a8de;return true;
    case 0x4a8de:
        if(!am_push(c,4,r.a[1]))return false;return am_call(c,0x3902,0x4a8e6);
    case 0x4a8e6:
        am_word(r.d[0],r.d[0]-0x40U);
        if(!am_pop(c,4,value))return false;r.a[0]=value;
        r.d[3]=0xffffffffU;am_word(r.d[4],2U);r.pc=0x36ba;return true;
    // Credit value 4a944: WORD (A1), then the BYTE (A1) when 100003 is clear.
    case 0x4a944:
        if(!ac1_get(c,r.a[5],0x7d82,1,value))return false;
        r.pc=value!=0U?0x4a954U:0x4a94cU;return true;
    case 0x4a94c:r.a[1]=am_index(r.a[5],0x8004);r.pc=0x4a966;return true;
    case 0x4a954:
        r.a[1]=0xd00034U;
        if(!ac1_get(c,r.a[5],0x7e80,1,value))return false;
        r.pc=value==0U?0x4a966U:0x4a962U;return true;
    case 0x4a962:r.a[1]=am_index(r.a[5],0x7e00);r.pc=0x4a966;return true;
    case 0x4a966:
        if(!ac1_read_a1(c,2,value))return false;am_word(r.d[0],value);
        if(!ac1_get(c,r.a[5],0x8003,1,value))return false;
        r.pc=value!=0U?0x4a972U:0x4a970U;return true;
    case 0x4a970:
        if(!ac1_read_a1(c,1,value))return false;am_byte(r.d[0],value);r.pc=0x4a972;return true;
    case 0x4a972:return am_return(c);
    // Credit check 4a974: D0.W & 1 selects the player; BIOS c00450 answers into 10fdb0 / 10fdb1 when BYTE 10fd82 is set.
    case 0x4a974:
        am_word(r.d[0],r.d[0]&1U);
        if(!am_read(c,0x10fd82U,1,value))return false;
        r.pc=value==0U?0x4a9b4U:0x4a982U;return true;
    case 0x4a982:
        if(!ac1_put(c,r.a[5],0x7db0,4,AC1_CREDIT_ANSWER) || !am_push(c,2,r.d[0]))return false;
        return am_call(c,AC1_CREDIT_BIOS,0x4a992);
    case 0x4a992:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        r.a[5]=0x108000U;r.a[0]=am_index(r.a[5],0x7db0);
        if(!ac1_get(c,r.a[5],0x8003,1,value))return false;
        r.pc=value!=0U?0x4a9aeU:0x4a9a4U;return true;
    case 0x4a9a4:
        if(!ac1_byte(c,r.a[5],0x8012,value))return false;
        r.pc=value==2U?0x4a9b0U:0x4a9aeU;return true;
    case 0x4a9ae:case 0x4a9c4:r.a[0]=am_index(r.a[0],r.d[0]&65535U);r.pc=r.pc==0x4a9ae?0x4a9b0U:0x4a9c6U;return true;
    case 0x4a9b0:case 0x4a9c6: // TST.B (A0); RTS: the Z flag is recomputed by the consumers 4a9d0 / 4a9da.
        if(!am_read(c,r.a[0],1,value))return false;return am_return(c);
    case 0x4a9b4:
        r.a[0]=0x100004U;
        if(!am_read(c,0x100003U,1,value))return false;
        r.pc=value==0U?0x4a9c6U:0x4a9c4U;return true;
    // Credit bits 4a9ca: D7 bit n = player n has a credit.
    case 0x4a9ca:r.d[7]=0;r.d[0]=0;return am_call(c,0x4a974,0x4a9d0);
    case 0x4a9d0:return ac1_credit_flag(c,0x4a9d6,0x4a9d4);
    case 0x4a9d4:case 0x4a9de:r.d[7]|=1U<<(r.d[0]&31U);r.pc=r.pc==0x4a9d4?0x4a9d6U:0x4a9e0U;return true;
    case 0x4a9d6:r.d[0]=1;return am_call(c,0x4a974,0x4a9da);
    case 0x4a9da:return ac1_credit_flag(c,0x4a9e0,0x4a9de);
    case 0x4a9e0:return am_return(c);
    default:return am_error(c,"unsupported animation controller c1 PC");
    }
}
}
