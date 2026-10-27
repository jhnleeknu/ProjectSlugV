#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool pc11_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool pc11_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BTST / BSET / BCLR #bit,d16(An) or BTST Dn,d16(An) (a memory operand: BYTE, bit modulo 8). op 0 tests, 1 sets, 2 clears; old is the bit before (the
// Z of the instruction is old = 0).
bool pc11_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t bit,unsigned int op,bool& old) {
    std::uint32_t value=0;if(!pc11_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<(bit&7U);
    old=(value&mask)!=0U;
    if(op==0U)return true;
    return pc11_put(c,base,displacement,1,op==1U?(value|mask):(value&~mask));
}
// BTST #bit,d16(An); BEQ.W zero_pc (the bit clear) / other_pc.
bool pc11_field_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t other_pc) {
    bool old=false;if(!pc11_bit(c,base,displacement,bit,0,old))return false;
    c.s.pc=old?other_pc:zero_pc;return true;
}
// TST.B / TST.W d16(An); BEQ / BNE: zero_pc when the BYTE / WORD is 0, else other_pc.
bool pc11_zero(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc11_get(c,base,displacement,size,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// CMPI.W #k,D7; BEQ.W equal_pc (the D7 dispatch of the appearance type 1d388 .. 1d434; WORD compare) / the next compare.
void pc11_type(AnimationMachineState& r,std::uint32_t k,std::uint32_t equal_pc) {
    r.pc=(r.d[7]&0xffffU)==k?equal_pc:r.pc+8U;
}
// BCC / BCS on the known C returned by the callee: clear -> clear_pc, set -> set_pc.
bool pc11_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"player c11 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W d16(A6),D0 (D0 bits 16..31 kept); JSR target.
bool pc11_field_call(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!pc11_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[0],value);return am_call(c,target,return_pc);
}
// MOVE.W 76(A6),D0; MOVEQ #k,D1; JSR b0c.l (the player-slot state request).
bool pc11_b0c(AnimationMachineContext& c,std::uint32_t k,std::uint32_t return_pc) {
    c.s.d[1]=k;return pc11_field_call(c,0x76,0xb0c,return_pc);
}
// MOVE.L #v,(A6): the node callback LONG, then next_pc.
bool pc11_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!pc11_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next_pc;return true;
}
// SUBQ.W #1,d16(A6); BCS.W borrow_pc (the WORD was 0) / other_pc (the RTS of the counting callback).
bool pc11_count_down(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t borrow_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!pc11_get(c,c.s.a[6],displacement,2,value) || !pc11_put(c,c.s.a[6],displacement,2,value-1U))return false;
    c.s.pc=(value&0xffffU)==0U?borrow_pc:other_pc;return true;
}
// MOVE.W 78(A6),D0; JSR 49c38.l (both input-slot callers 1d5c4 / 1d5fc) and MOVE.W 78(A6),D0; LEA callback(PC),A0; JSR 49c20.l.
bool pc11_input_slot(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t return_pc) {
    c.s.a[0]=callback;return pc11_field_call(c,0x78,0x49c20,return_pc);
}
// The signed WORD of a 68000 MULS.W operand (no implementation-defined conversion).
std::int32_t pc11_signed_word(std::uint32_t value) {
    const std::int32_t low=static_cast<std::int32_t>(value&0xffffU);
    return low>=0x8000?low-0x10000:low;
}
// MULS.W (A0,D1.W),Dn: Dn.L := Dn.W x WORD (A0 + sext D1.W), both signed (the product of two signed WORDs fits a signed LONG).
bool pc11_muls(AnimationMachineContext& c,std::uint32_t& dn) {
    std::uint32_t value=0;if(!am_read(c,am_index(c.s.a[0],c.s.d[1]&0xffffU),2,value))return false;
    const std::int32_t product=pc11_signed_word(dn)*pc11_signed_word(value);
    dn=static_cast<std::uint32_t>(product);return true;
}
// The Z of the TST.B (A0); RTS that ends 4a974 (4a9b0 / 4a9c6), read by 4eb84 BNE (contract decision 3; controller C1 / player C4 / C6 rule): A0 is
// 10fdb0 / 10fdb1 or 100004 / 100005 and the RTS does not change that BYTE, so it is read again; any other A0 is the checked flag-source error.
bool pc11_flag_4a974(AnimationMachineContext& c,std::uint32_t& value) {
    const std::uint32_t a0=c.s.a[0];
    if(a0!=0x10fdb0U && a0!=0x10fdb1U && a0!=0x100004U && a0!=0x100005U)return am_error(c,"unsupported animation player c11 flag source");
    return am_read(c,a0,1,value);
}
// JMP (A1) 21a82 (contract decision 2): the handler list 216c8 = (21602, 0), LONG 0 (ROM bytes) that C3 215e6 matched; A1 21602 (routed, C3), any
// other A1 (compared as a LONG) is the checked jump-target error.
bool pc11_list_jump(AnimationMachineContext& c) {
    if(c.s.a[1]!=0x21602U)return am_error(c,"unsupported animation player c11 jump target");
    c.s.pc=c.s.a[1];return true;
}
}
// Player C11 (209 block starts, contract docs/analysis/animation-machine-player-c11-contract.md; area-C plan 11.5 / 11.8 unit C-1): the continue
// counter helpers ca64 / ca6a, the stage-script helper 1a952, the record animation helper 1cb72 / 1cb76, the rest of the appearance-type D7 chain 1d3e0
// .. 1d434 of 1d388 (types f 10 c d 11 19 1a 1b 18 14 16) with the entries 1d722 1d746 (-> callback 1d75a) 1d8e2 1d906 1d9b2 (2986 child 3fedc) 1db28
// 1db46 (-> callback 1db7c) 1ddd8 (-> callback 1dde8) and the helpers 1d508 1d5c4 1d5fc, the velocity helper 1e5aa (49bf2, MULS x 2, 4c2c4), 1e640 /
// 1e65a, the 28ae child callback 1e67a -> 1e6c0, the state 1e8de -> 1e918 -> callback 1e92c, the slot-84 states 21950 -> 21960 and 21a42 -> 21a76
// (JMP (A1) 21a82 on the list 216c8), the 2986 child callback 3fedc, the WORD table helper 49bf2, the credit reader 4a90e, the record base helper
// 4d196, the continue entry 4eb6a -> callback 4ebe2 -> 4ec32 .. 4ed34 and the appearance helper e8c3a (MOVEM.W, 2986 child b3dfc).
// C: the 9 consumers 1d5ce 1d606 (BCS, 49c38), 1d770 (BCC, 4836e), 1d8fa (BCC, 1d510), 1db9c (BCS, 1d508 -> 1d514), 1e5ec (BCC, 4c2c4), 21968 21a7e
// (BCC, 215e6), e8c7c (MOVEM.W (A7)+,D0-D6; BCC, 2986) read a known C or fail; every C11 block leaves C Unknown (no C11 block produces or passes a C
// that a reader uses).  Z: 4eb84 (BNE after JSR 4a974) re-reads the BYTE (A0) of the TST.B (A0); RTS that ends 4a974.
bool animation_player_c11_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool old=false;
    switch(r.pc) {
    // ---- ca64 / ca6a (the continue counter WORD 10095c): CLR.W -76a4(A5); RTS / CLR.B -76a3(A5); RTS.
    case 0xca64:if(!pc11_put(c,r.a[5],0x895c,2,0))return false;return am_return(c);
    case 0xca6a:if(!pc11_put(c,r.a[5],0x895d,1,0))return false;return am_return(c);
    // ---- 1a952: ANDI.W #3,D0; MOVE.B 53cc(A5),D1; ANDI.B #fc,D1; OR.B D0,D1; MOVE.B D1,53cc(A5); RTS (D0 / D1 bits 16..31 / 8..31 kept).
    case 0x1a952:
        am_word(r.d[0],r.d[0]&3U);if(!pc11_get(c,r.a[5],0x53cc,1,value))return false;am_byte(r.d[1],(value&0xfcU)|(r.d[0]&0xffU));
        if(!pc11_put(c,r.a[5],0x53cc,1,r.d[1]))return false;return am_return(c);
    // ---- 1cb72: LEA 94(A6),A1 / 1cb76: MOVEA.L 8c(A6),A4; MOVEQ #0,D7; MOVE.B 4(A4),D7; LEA 1c1c4(PC),A4; MOVE.B (A4,D7.W),D7; ADD.W D7,D7; MOVE.W
    // (A0,D7.W),D7; ADD.W D7,D7 twice; MOVEA.L 22(A6),A0; MOVE.L (A0,D7.W),D7; BNE.W 1cba4 / MOVE.L #1cafe,D7 / 1cba4: MOVEA.L D7,A0; EXG A0,A1; MOVE.W
    // #100,D0; JMP 49f96.l.  The fixed ROM BYTE table 1c1c4 and the caller's WORD record A0 are read through the live bus (no bound check).
    case 0x1cb72:r.a[1]=am_index(r.a[6],0x94);r.pc=0x1cb76;return true;
    case 0x1cb76:
        if(!pc11_get(c,r.a[6],0x8c,4,r.a[4]))return false;r.d[7]=0;if(!pc11_get(c,r.a[4],4,1,value))return false;am_byte(r.d[7],value);
        r.a[4]=0x1c1c4;if(!am_read(c,am_index(r.a[4],r.d[7]&0xffffU),1,value))return false;am_byte(r.d[7],value);am_word(r.d[7],r.d[7]+r.d[7]);
        if(!am_read(c,am_index(r.a[0],r.d[7]&0xffffU),2,value))return false;am_word(r.d[7],value);am_word(r.d[7],r.d[7]+r.d[7]);am_word(r.d[7],r.d[7]+r.d[7]);
        if(!pc11_get(c,r.a[6],0x22,4,r.a[0]) || !am_read(c,am_index(r.a[0],r.d[7]&0xffffU),4,r.d[7]))return false;
        r.pc=r.d[7]!=0U?0x1cba4:0x1cb9e;return true;
    case 0x1cb9e:r.d[7]=0x1cafe;r.pc=0x1cba4;return true;
    case 0x1cba4:r.a[0]=r.a[1];r.a[1]=r.d[7];am_word(r.d[0],0x100);r.pc=0x49f96;return true;
    // ---- 1d3e0 .. 1d434 (the C6 1d3d8 BEQ fall-through: the rest of the D7 dispatch of 1d388): CMPI.W #k,D7; BEQ.W target for k = f 10 c d 11 19 1a 1b
    // 18 14 16; the last falls into 1d438 (a later-unit stop).
    case 0x1d3e0:pc11_type(r,0xf,0x1db0a);return true;
    case 0x1d3e8:pc11_type(r,0x10,0x1db28);return true;
    case 0x1d3f0:pc11_type(r,0xc,0x1d8e2);return true;
    case 0x1d3f8:pc11_type(r,0xd,0x1d906);return true;
    case 0x1d400:pc11_type(r,0x11,0x1db46);return true;
    case 0x1d408:pc11_type(r,0x19,0x1d9b2);return true;
    case 0x1d410:pc11_type(r,0x1a,0x1d940);return true;
    case 0x1d418:pc11_type(r,0x1b,0x1d940);return true;
    case 0x1d420:pc11_type(r,0x18,0x1ddd8);return true;
    case 0x1d428:pc11_type(r,0x14,0x1d722);return true;
    case 0x1d430:pc11_type(r,0x16,0x1d746);return true;
    // ---- 1d508 (BSR from 1db98): LEA 1d4b8(PC),A0; BRA.W 1d514 (C6: the CMPI.W #14,D1 C goes back to 1db9c).
    case 0x1d508:r.a[0]=0x1d4b8;r.pc=0x1d514;return true;
    // ---- 1d5c4 / 1d5fc (JSR (PC) from 1db86 / 1db8a / 1ddd8): MOVE.W 78(A6),D0; JSR 49c38.l / BCS.W the RTS (C of 49c38) / MOVE.W 78(A6),D0; LEA
    // 1d5e2 / 1d61a(PC),A0; JSR 49c20.l / RTS (no caller reads its flags).
    case 0x1d5c4:case 0x1d5fc:return pc11_field_call(c,0x78,0x49c38,r.pc+0xaU);
    case 0x1d5ce:case 0x1d606:return pc11_carry(c,r.pc+4U,r.pc+0x12U);
    case 0x1d5d2:return pc11_input_slot(c,0x1d5e2,0x1d5e0);
    case 0x1d60a:return pc11_input_slot(c,0x1d61a,0x1d618);
    case 0x1d5e0:case 0x1d618:case 0x1d774:case 0x1db84:case 0x1ddfa:case 0x1e65a:case 0x1e774:case 0x21aaa:return am_return(c);   // RTS (no reader of the flags).
    // ---- 1d722 (type 14): MOVE.W 547a(A5),D0; MOVE.W 547c(A5),D1; LEA 538e(A5),A1; SUB.W (A1),D0; ADDI.W #100,D1; SUB.W 4(A1),D1; LEA 2e(A6),A0; JSR
    // 43e08.l / BRA.W 1dbf0 (a later-unit stop).
    case 0x1d722:
        if(!pc11_get(c,r.a[5],0x547a,2,value))return false;am_word(r.d[0],value);if(!pc11_get(c,r.a[5],0x547c,2,value))return false;am_word(r.d[1],value);
        r.a[1]=am_index(r.a[5],0x538e);if(!pc11_get(c,r.a[1],0,2,value))return false;am_word(r.d[0],r.d[0]-value);am_word(r.d[1],r.d[1]+0x100U);
        if(!pc11_get(c,r.a[1],4,2,value))return false;am_word(r.d[1],r.d[1]-value);r.a[0]=am_index(r.a[6],0x2e);return am_call(c,0x43e08,0x1d742);
    case 0x1d742:r.pc=0x1dbf0;return true;
    // ---- 1d746 (type 16): JSR 48296.l / CLR.L D0; JSR 1a952.l / MOVE.L #1d75a,(A6) / 1d75a: MOVE.W 78(A6),D0; JSR 49bca.l / JSR ea626.l / JSR 4836e.l /
    // BCC.W 1d776 (C of 4836e; a later-unit stop) / RTS.
    case 0x1d746:return am_call(c,0x48296,0x1d74c);
    case 0x1d74c:r.d[0]=0;return am_call(c,0x1a952,0x1d754);
    case 0x1d754:return pc11_install(c,0x1d75a,0x1d75a);
    case 0x1d75a:return pc11_field_call(c,0x78,0x49bca,0x1d764);
    case 0x1d764:return am_call(c,0xea626,0x1d76a);
    case 0x1d76a:return am_call(c,0x4836e,0x1d770);
    case 0x1d770:return pc11_carry(c,0x1d776,0x1d774);
    // ---- 1d8e2 (type c) / 1d906 (type d): BSR.W 1d582 (return 1d8e6 / 1d90a) / MOVE.W 78(A6),D0; JSR 48210.l / TST.W D1; BEQ.W 1ddfc / BSR.W 1d510 /
    // BCC.W 1d902 (C of 1d510) / BRA.W 1dbc6 / BRA.W 1ddfc.
    case 0x1d8e2:case 0x1d906:return am_call(c,0x1d582,r.pc+4U);
    case 0x1d8e6:return pc11_field_call(c,0x78,0x48210,0x1d8f0);
    case 0x1d8f0:r.pc=(r.d[1]&0xffffU)==0U?0x1ddfc:0x1d8f6;return true;
    case 0x1d8f6:return am_call(c,0x1d510,0x1d8fa);
    case 0x1d8fa:return pc11_carry(c,0x1d902,0x1d8fe);
    case 0x1d8fe:r.pc=0x1dbc6;return true;                                                  // BRA.W 1dbc6 (C6).
    case 0x1d902:r.pc=0x1ddfc;return true;                                                                // BRA.W 1ddfc (C6).
    // ---- 1d9b2 (type 19): JSR 4d196.l / MOVE.W 42(A6),D0; SUB.W 53a2(A5),D0; MOVE.W D0,ae(A6); TST.W 78(A6); BEQ.W 1d9d8 / MOVE.W #ffb8,D0; ADD.W
    // D0,ae(A6); ADD.W D0,42(A6) / MOVE.W 78(A6),D0; MOVEQ #13,D1; JSR 481de.l / MOVE.W 78(A6),D0; JSR 481b2.l / MOVEA.L #3fedc,A0; MOVE.W #0,D0;
    // MOVEA.L #100bf4,A1; JSR 2986.l (the 2986 child 3fedc) / MOVE.W 78(A6),76(A0); MOVE.W ae(A6),D0; MOVE.W 32(A6),D1; JSR 49260.l / BCLR.B
    // #0,15(A6); MOVE.W 78(A6),D0; MOVE.W 42(A6),D1; SUB.W 53a2(A5),D1; MOVE.W D1,ae(A6); LEA 1da60(PC),A0; JSR 49c20.l / MOVEA.L #0,A1; MOVE.W #0,D0;
    // TST.W 78(A6); BEQ.W 1da4e / MOVE.W #ffb8,D0 / MOVE.W 46(A6),D1; LEA 2e(A6),A0; JSR 43e08.l / BRA.W 1ddc8 (C6).
    case 0x1d9b2:return am_call(c,0x4d196,0x1d9b8);
    case 0x1d9b8:
        if(!pc11_get(c,r.a[6],0x42,2,value) || !pc11_get(c,r.a[5],0x53a2,2,other))return false;am_word(r.d[0],value-other);
        if(!pc11_put(c,r.a[6],0xae,2,r.d[0]))return false;return pc11_zero(c,r.a[6],0x78,2,0x1d9d8,0x1d9cc);
    case 0x1d9cc:
        am_word(r.d[0],0xffb8);if(!pc11_get(c,r.a[6],0xae,2,value) || !pc11_put(c,r.a[6],0xae,2,value+0xffb8U))return false;
        if(!pc11_get(c,r.a[6],0x42,2,value) || !pc11_put(c,r.a[6],0x42,2,value+0xffb8U))return false;r.pc=0x1d9d8;return true;
    case 0x1d9d8:r.d[1]=0x13;return pc11_field_call(c,0x78,0x481de,0x1d9e4);
    case 0x1d9e4:return pc11_field_call(c,0x78,0x481b2,0x1d9ee);
    case 0x1d9ee:r.a[0]=0x3fedc;am_word(r.d[0],0);r.a[1]=0x100bf4;return am_call(c,0x2986,0x1da04);
    case 0x1da04:
        if(!pc11_get(c,r.a[6],0x78,2,value) || !pc11_put(c,r.a[0],0x76,2,value))return false;
        if(!pc11_get(c,r.a[6],0xae,2,value))return false;am_word(r.d[0],value);if(!pc11_get(c,r.a[6],0x32,2,value))return false;am_word(r.d[1],value);
        return am_call(c,0x49260,0x1da18);
    case 0x1da18:
        if(!pc11_bit(c,r.a[6],0x15,0,2,old) || !pc11_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);
        if(!pc11_get(c,r.a[6],0x42,2,value) || !pc11_get(c,r.a[5],0x53a2,2,other))return false;am_word(r.d[1],value-other);
        if(!pc11_put(c,r.a[6],0xae,2,r.d[1]))return false;r.a[0]=0x1da60;return am_call(c,0x49c20,0x1da38);
    case 0x1da38:r.a[1]=0;am_word(r.d[0],0);return pc11_zero(c,r.a[6],0x78,2,0x1da4e,0x1da4a);
    case 0x1da4a:am_word(r.d[0],0xffb8);r.pc=0x1da4e;return true;
    case 0x1da4e:if(!pc11_get(c,r.a[6],0x46,2,value))return false;am_word(r.d[1],value);r.a[0]=am_index(r.a[6],0x2e);return am_call(c,0x43e08,0x1da5c);
    case 0x1da5c:r.pc=0x1ddc8;return true;                                                                // BRA.W 1ddc8 (C6).
    // ---- 1db28 (type 10): BSR.W 1d698 / MOVEA.W #0,A1; MOVE.W 42(A6),D0; MOVE.W #e0,D1; LEA 2e(A6),A0; JSR 43e08.l / BRA.W 1d90a (C6).
    case 0x1db28:return am_call(c,0x1d698,0x1db2c);
    case 0x1db2c:
        r.a[1]=0;if(!pc11_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],0xe0);r.a[0]=am_index(r.a[6],0x2e);
        return am_call(c,0x43e08,0x1db42);
    case 0x1db42:r.pc=0x1d90a;return true;
    // ---- 1db46 (type 11): MOVE.B #ff,81(A6); MOVE.B #ff,82(A6); MOVE.W 78(A6),D0; JSR 48210.l / CMPI.B #9,D1; BNE.W 1db8a / MOVE.W #6,88(A6); TST.W
    // 78(A6); BEQ.W 1db76 / ADDQ.W #4,88(A6) / MOVE.L #1db7c,(A6) / 1db7c: SUBQ.W #1,88(A6); BCS.W 1db86 / RTS / JSR 1d5c4(PC) / JSR 1d5fc(PC) / MOVE.W
    // 78(A6),D0; JSR 48210.l / BSR.W 1d508 / BCS.W 1dbc6 (C of 1d514) / CLR.L 36(A6); MOVE.L #e2000,3a(A6); BSET.B #2,a7(A6); BSR.W 1d1d0 / MOVE.W
    // #8834,68(A6); MOVE.W #8834,1e(A6); BRA.W 1fae8 (C2).
    case 0x1db46:if(!pc11_put(c,r.a[6],0x81,1,0xff) || !pc11_put(c,r.a[6],0x82,1,0xff))return false;return pc11_field_call(c,0x78,0x48210,0x1db5c);
    case 0x1db5c:r.pc=(r.d[1]&0xffU)!=9U?0x1db8a:0x1db64;return true;
    case 0x1db64:if(!pc11_put(c,r.a[6],0x88,2,6))return false;return pc11_zero(c,r.a[6],0x78,2,0x1db76,0x1db72);
    case 0x1db72:if(!pc11_get(c,r.a[6],0x88,2,value) || !pc11_put(c,r.a[6],0x88,2,value+4U))return false;r.pc=0x1db76;return true;
    case 0x1db76:return pc11_install(c,0x1db7c,0x1db7c);
    case 0x1db7c:return pc11_count_down(c,0x88,0x1db86,0x1db84);
    case 0x1db86:return am_call(c,0x1d5c4,0x1db8a);
    case 0x1db8a:return am_call(c,0x1d5fc,0x1db8e);
    case 0x1db8e:return pc11_field_call(c,0x78,0x48210,0x1db98);
    case 0x1db98:return am_call(c,0x1d508,0x1db9c);
    case 0x1db9c:return pc11_carry(c,0x1dba0,0x1dbc6);
    case 0x1dba0:
        if(!pc11_put(c,r.a[6],0x36,4,0) || !pc11_put(c,r.a[6],0x3a,4,0xe2000) || !pc11_bit(c,r.a[6],0xa7,2,1,old))return false;return am_call(c,0x1d1d0,0x1dbb6);
    case 0x1dbb6:if(!pc11_put(c,r.a[6],0x68,2,0x8834) || !pc11_put(c,r.a[6],0x1e,2,0x8834))return false;r.pc=0x1fae8;return true;
    // ---- 1ddd8 (type 18): JSR 1d5fc(PC) / MOVE.W #14,b0(A6); MOVE.L #1dde8,(A6) / 1dde8: MOVE.W 78(A6),D0; JSR 49bca.l / SUBQ.W #1,b0(A6); BCS.W 1ddfc
    // (C6) / RTS.
    case 0x1ddd8:return am_call(c,0x1d5fc,0x1dddc);
    case 0x1dddc:if(!pc11_put(c,r.a[6],0xb0,2,0x14))return false;return pc11_install(c,0x1dde8,0x1dde8);
    case 0x1dde8:return pc11_field_call(c,0x78,0x49bca,0x1ddf2);
    case 0x1ddf2:return pc11_count_down(c,0xb0,0x1ddfc,0x1ddfa);
    // ---- 1e5aa (BSR from 1e93a, 1e996 1e9f8 1ea5a): JSR 49bf2.l / MOVEQ #0,D2; MOVEQ #0,D3; TST.W D1; BMI.W 1e5d8 / MOVE.W #500,D2; MOVE.W #400,D3; ADD.W
    // D1,D1; LEA 4419e.l,A0; MULS.W (A0,D1.W),D2; LEA 4411e.l,A0; MULS.W (A0,D1.W),D3 (fixed ROM WORD tables, live bus) / MOVE.L D2,36(A6); MOVE.L
    // D3,3a(A6); MOVE.W D0,-(A7); MOVE.W #ffe8,D0; JSR 4c2c4.l (a later-unit stop) / BCC.W 1e604 (C of 4c2c4) / NEG.W D0; MOVE.W D0,D7; SUBI.W #10,D0;
    // BPL.W 1e600 / SUB.W D0,3a(A6) / BRA.W 1e606 / MOVEQ #ff,D7 / MOVE.W (A7)+,D0; RTS.
    case 0x1e5aa:return am_call(c,0x49bf2,0x1e5b0);
    case 0x1e5b0:r.d[2]=0;r.d[3]=0;r.pc=(r.d[1]&0x8000U)!=0U?0x1e5d8:0x1e5ba;return true;
    case 0x1e5ba:
        am_word(r.d[2],0x500);am_word(r.d[3],0x400);am_word(r.d[1],r.d[1]+r.d[1]);r.a[0]=0x4419e;if(!pc11_muls(c,r.d[2]))return false;
        r.a[0]=0x4411e;if(!pc11_muls(c,r.d[3]))return false;r.pc=0x1e5d8;return true;
    case 0x1e5d8:
        if(!pc11_put(c,r.a[6],0x36,4,r.d[2]) || !pc11_put(c,r.a[6],0x3a,4,r.d[3]) || !am_push(c,2,r.d[0]&0xffffU))return false;am_word(r.d[0],0xffe8);
        return am_call(c,0x4c2c4,0x1e5ec);
    case 0x1e5ec:return pc11_carry(c,0x1e604,0x1e5f0);
    case 0x1e5f0:
        am_word(r.d[0],0U-r.d[0]);am_word(r.d[7],r.d[0]);am_word(r.d[0],r.d[0]-0x10U);r.pc=(r.d[0]&0x8000U)==0U?0x1e600:0x1e5fc;return true;
    case 0x1e5fc:if(!pc11_get(c,r.a[6],0x3a,2,value) || !pc11_put(c,r.a[6],0x3a,2,value-r.d[0]))return false;r.pc=0x1e600;return true;
    case 0x1e600:r.pc=0x1e606;return true;
    case 0x1e604:r.d[7]=0xffffffffU;r.pc=0x1e606;return true;
    case 0x1e606:if(!am_pop(c,2,value))return false;am_word(r.d[0],value);return am_return(c);
    // ---- 1e640 (BSR from 1e94a, 1e9a6 1ea1a 1ea66): BTST #6,D0; BEQ.W 1e65a (the RTS) / 1e648 (a later-unit stop).
    case 0x1e640:r.pc=(r.d[0]&0x40U)==0U?0x1e65a:0x1e648;return true;
    // ---- 1e67a (the 28ae child of 1e8e4 and C6 1e828): MOVE.W #ca,20(A6); MOVE.L 200088.l,22(A6) (bank window); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49290.l /
    // BSET.B #6,15(A6); MOVE.W #8cd,D0; MOVE.B #0,D1; JSR 8ebe.l / MOVEA.L #6f1e2,A1; MOVE.W #100,D0; JSR 49f8c.l / CLR.B 88(A6); MOVE.L #1e6c0,(A6) /
    // 1e6c0: MOVEA.L c(A6),A0; MOVE.W 78(A0),D0; JSR 49be0.l / MOVE.W (A0),D0; BTST #3,D0; SNE.B D0; MOVE.B 88(A6),D1; MOVE.B D0,88(A6); EOR.B D0,D1;
    // BEQ.W 1e70e / TST.B D0; BEQ.W 1e6fe / MOVEA.L #6f21a,A1; MOVE.W #100,D0; JSR 49f8c.l / BRA.W 1e70e / MOVEA.L #6f1e2,A1; MOVE.W #100,D0; JSR 49f8c.l
    // / MOVEA.L c(A6),A0; MOVE.B 9e(A0),D0; CMPI.B #3,D0; BEQ.W 1e724 / (1e71e: a later-unit stop).
    case 0x1e67a:
        if(!pc11_put(c,r.a[6],0x20,2,0xca) || !am_read(c,0x200088,4,value) || !pc11_put(c,r.a[6],0x22,4,value))return false;r.d[0]=0;r.d[1]=0;
        return am_call(c,0x49290,0x1e692);
    case 0x1e692:if(!pc11_bit(c,r.a[6],0x15,6,1,old))return false;am_word(r.d[0],0x8cd);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x1e6a6);
    case 0x1e6a6:case 0x1e6fe:r.a[1]=0x6f1e2;am_word(r.d[0],0x100);return am_call(c,0x49f8c,r.pc+0x10U);
    case 0x1e6b6:if(!pc11_put(c,r.a[6],0x88,1,0))return false;return pc11_install(c,0x1e6c0,0x1e6c0);
    case 0x1e6c0:
        if(!pc11_get(c,r.a[6],0xc,4,r.a[0]) || !pc11_get(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49be0,0x1e6ce);
    case 0x1e6ce:
        if(!pc11_get(c,r.a[0],0,2,value))return false;am_word(r.d[0],value);am_byte(r.d[0],(r.d[0]&8U)!=0U?0xffU:0U);
        if(!pc11_get(c,r.a[6],0x88,1,value))return false;am_byte(r.d[1],value);if(!pc11_put(c,r.a[6],0x88,1,r.d[0]))return false;
        am_byte(r.d[1],r.d[1]^r.d[0]);r.pc=(r.d[1]&0xffU)==0U?0x1e70e:0x1e6e4;return true;
    case 0x1e6e4:r.pc=(r.d[0]&0xffU)==0U?0x1e6fe:0x1e6ea;return true;
    case 0x1e6ea:r.a[1]=0x6f21a;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x1e6fa);
    case 0x1e6fa:r.pc=0x1e70e;return true;
    case 0x1e70e:
        if(!pc11_get(c,r.a[6],0xc,4,r.a[0]) || !pc11_get(c,r.a[0],0x9e,1,value))return false;am_byte(r.d[0],value);r.pc=value==3U?0x1e724:0x1e71e;return true;
    // ---- 1e724: BTST.B #7,a7(A0); BEQ.W 1e734 / JMP 2a00.l / BTST.B #6,a7(A0); BEQ.W 1e744 / JMP 2a00.l / MOVEQ #0,D0; MOVE.B 7c(A0),D0; ADD.W D0,D0;
    // MOVE.W 1e776(PC,D0.W),1e(A6); ADD.W D0,D0; ADD.W 76(A0),D0; ADD.W D0,D0; MOVE.W 1e77c(PC,D0.W),32(A6) (fixed ROM WORD tables, live bus); MOVE.W
    // 1e(A0),D0; ADD.W D0,1e(A6); JSR 43e34.l / JSR 49fc6.l / RTS.
    case 0x1e724:return pc11_field_bit(c,r.a[0],0xa7,7,0x1e734,0x1e72e);
    case 0x1e72e:case 0x1e73e:r.pc=0x2a00;return true;                                                 // JMP 2a00.l.
    case 0x1e734:return pc11_field_bit(c,r.a[0],0xa7,6,0x1e744,0x1e73e);
    case 0x1e744:
        r.d[0]=0;if(!pc11_get(c,r.a[0],0x7c,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);
        if(!am_read(c,am_index(0x1e776,r.d[0]&0xffffU),2,value) || !pc11_put(c,r.a[6],0x1e,2,value))return false;am_word(r.d[0],r.d[0]+r.d[0]);
        if(!pc11_get(c,r.a[0],0x76,2,value))return false;am_word(r.d[0],r.d[0]+value);am_word(r.d[0],r.d[0]+r.d[0]);
        if(!am_read(c,am_index(0x1e77c,r.d[0]&0xffffU),2,value) || !pc11_put(c,r.a[6],0x32,2,value))return false;
        if(!pc11_get(c,r.a[0],0x1e,2,value))return false;am_word(r.d[0],value);
        if(!pc11_get(c,r.a[6],0x1e,2,value) || !pc11_put(c,r.a[6],0x1e,2,value+r.d[0]))return false;return am_call(c,0x43e34,0x1e76e);
    case 0x1e76e:case 0x1e962:return am_call(c,0x49fc6,r.pc+6U);
    // ---- 1e8de (C2 1de34 BNE; written by C10 1dcc6, 1e81a): BSET.B #2,a7(A6); MOVEA.L #1e67a,A0; MOVE.W #0,D0; JSR 28ae.l (the 28ae child 1e67a) / MOVE.L
    // #21602,84(A6); MOVE.B #0,9c(A6); MOVE.B #1,aa(A6); CLR.W 7a(A6); BCLR.B #0,15(A6); MOVE.W #180,7c(A6) / 1e918 (written by C6 1e8d4, the LONG
    // table 20444 of C10 2043e): LEA 1bcce(PC),A0; BSR.W 1cb38 / MOVE.B #4,a9(A6); MOVE.L #1e92c,(A6) / 1e92c: BSR.W 1cd98 / BTST.B #3,a7(A6); BNE.W
    // 1e96c / BSR.W 1e5aa / CMPI.W #18,D7; BCS.W 1e96c (a later-unit stop) / BSR.W 1e60a / BSR.W 1e640 / JSR 4be82.l / JSR 1e65c(PC) / MOVE.W 1e(A6),D0;
    // JSR ce02.l / JSR 49fc6.l / BRA.W 201a2 (C3).
    case 0x1e8de:if(!pc11_bit(c,r.a[6],0xa7,2,1,old))return false;r.a[0]=0x1e67a;am_word(r.d[0],0);return am_call(c,0x28ae,0x1e8f4);
    case 0x1e8f4:
        if(!pc11_put(c,r.a[6],0x84,4,0x21602) || !pc11_put(c,r.a[6],0x9c,1,0) || !pc11_put(c,r.a[6],0xaa,1,1) || !pc11_put(c,r.a[6],0x7a,2,0) ||
           !pc11_bit(c,r.a[6],0x15,0,2,old) || !pc11_put(c,r.a[6],0x7c,2,0x180))return false;
        r.pc=0x1e918;return true;
    case 0x1e918:r.a[0]=0x1bcce;return am_call(c,0x1cb38,0x1e920);
    case 0x1e920:if(!pc11_put(c,r.a[6],0xa9,1,4))return false;return pc11_install(c,0x1e92c,0x1e92c);
    case 0x1e92c:case 0x2196e:case 0x21a84:return am_call(c,0x1cd98,r.pc+4U);                          // BSR.W 1cd98.
    case 0x1e930:return pc11_field_bit(c,r.a[6],0xa7,3,0x1e93a,0x1e96c);
    case 0x1e93a:return am_call(c,0x1e5aa,0x1e93e);
    case 0x1e93e:r.pc=(r.d[7]&0xffffU)<0x18U?0x1e96c:0x1e946;return true;
    case 0x1e946:return am_call(c,0x1e60a,0x1e94a);
    case 0x1e94a:return am_call(c,0x1e640,0x1e94e);
    case 0x1e94e:return am_call(c,0x4be82,0x1e954);
    case 0x1e954:return am_call(c,0x1e65c,0x1e958);
    case 0x1e958:return pc11_field_call(c,0x1e,0xce02,0x1e962);
    case 0x1e968:r.pc=0x201a2;return true;
    // ---- 21950 (the C3 21620 list handler): LEA 1bcde(PC),A0; BSR.W 1cb72 / MOVE.L #21960,84(A6) / 21960 (slot-84 value): LEA 21930(PC),A0; BSR.W 215e6
    // / BCC.W 2196e (C of 215e6; Set: 2196c, a later-unit stop) / BSR.W 1cd98 / BTST #4,D0; BNE.W 21a42 / BRA.W 2156a (C3).
    case 0x21950:r.a[0]=0x1bcde;return am_call(c,0x1cb72,0x21958);
    case 0x21958:if(!pc11_put(c,r.a[6],0x84,4,0x21960))return false;r.pc=0x21960;return true;
    case 0x21960:r.a[0]=0x21930;return am_call(c,0x215e6,0x21968);
    case 0x21968:return pc11_carry(c,0x2196e,0x2196c);
    case 0x21972:r.pc=(r.d[0]&0x10U)!=0U?0x21a42:0x2197a;return true;
    case 0x2197a:r.pc=0x2156a;return true;
    // ---- 21a42 (21976, 219b0 219ee 21a96 BNE): BCLR.B #5,a7(A6); MOVEA.L 8c(A6),A4; MOVEQ #0,D0; MOVE.B 4(A4),D0; ADD.W D0,D0 twice; MOVEA.L
    // 219f6(PC,D0.W),A0 (fixed ROM LONG table, live bus); BSR.W 1cb72 / ANDI.B #ef,a5(A6); ANDI.B #ef,a6(A6); CLR.B 7e(A6); MOVE.L #21a76,84(A6) / 21a76
    // (slot-84 value): LEA 216c8(PC),A0; BSR.W 215e6 / BCC.W 21a84 (C of 215e6) / JMP (A1) (list 216c8) / BSR.W 1cd98 / TST.B 7e(A6); BEQ.W 21a98 (else
    // 21a90, a later-unit stop) / BSR.W 2156a / TST.W D7; BEQ.W 21aaa (else 21aa2, a later-unit stop) / RTS.
    case 0x21a42:
        if(!pc11_bit(c,r.a[6],0xa7,5,2,old) || !pc11_get(c,r.a[6],0x8c,4,r.a[4]))return false;r.d[0]=0;if(!pc11_get(c,r.a[4],4,1,value))return false;
        am_byte(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);if(!am_read(c,am_index(0x219f6,r.d[0]&0xffffU),4,r.a[0]))return false;
        return am_call(c,0x1cb72,0x21a5e);
    case 0x21a5e:
        if(!pc11_get(c,r.a[6],0xa5,1,value) || !pc11_put(c,r.a[6],0xa5,1,value&0xefU) || !pc11_get(c,r.a[6],0xa6,1,value) ||
           !pc11_put(c,r.a[6],0xa6,1,value&0xefU) || !pc11_put(c,r.a[6],0x7e,1,0) || !pc11_put(c,r.a[6],0x84,4,0x21a76))return false;
        r.pc=0x21a76;return true;
    case 0x21a76:r.a[0]=0x216c8;return am_call(c,0x215e6,0x21a7e);
    case 0x21a7e:return pc11_carry(c,0x21a84,0x21a82);
    case 0x21a82:return pc11_list_jump(c);
    case 0x21a88:return pc11_zero(c,r.a[6],0x7e,1,0x21a98,0x21a90);
    case 0x21a98:return am_call(c,0x2156a,0x21a9c);
    case 0x21a9c:r.pc=(r.d[7]&0xffffU)==0U?0x21aaa:0x21aa2;return true;
    // ---- 3fedc (the 2986 child of 1d9ee): JSR 4c0ac.l / MOVE.W 76(A6),-(A7); CLR.W 76(A6); BSR.W 40a5a (a later-unit stop) / MOVE.W (A7)+,D0; MOVE.W
    // D0,8a(A6); MOVE.L #3ff14,(A6) (written only); RTS.
    case 0x3fedc:return am_call(c,0x4c0ac,0x3fee2);
    case 0x3fee2:
        if(!pc11_get(c,r.a[6],0x76,2,value) || !am_push(c,2,value) || !pc11_put(c,r.a[6],0x76,2,0))return false;return am_call(c,0x40a5a,0x3feee);
    case 0x3feee:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);if(!pc11_put(c,r.a[6],0x8a,2,value) || !pc11_put(c,r.a[6],0,4,0x3ff14))return false;
        return am_return(c);
    // ---- 49bf2 (JSR from 1e5aa, 1e02c): MOVE.W D0,D1; ANDI.W #f,D1; ADD.W D1,D1; MOVE.W 49c00(PC,D1.W),D1 (fixed ROM WORD table, 16 entries); RTS.
    case 0x49bf2:
        am_word(r.d[1],(r.d[0]&0xfU)<<1);if(!am_read(c,0x49c00U+(r.d[1]&0xffffU),2,value))return false;am_word(r.d[1],value);return am_return(c);
    // ---- 4a90e (the credit BYTE; JSR from 4ebc0 4ec36): TST.B 7d82(A5); BNE.W 4a91e / LEA -7ffc(A5),A1; BRA.W 4a930 / LEA d00034.l,A1; TST.B 7e80(A5);
    // BEQ.W 4a930 / LEA 7e00(A5),A1 / ANDI.W #1,D0; TST.B -7ffd(A5); BNE.W 4a93e / MOVEQ #0,D0 / MOVE.B (A1,D0.W),D0; RTS.
    case 0x4a90e:return pc11_zero(c,r.a[5],0x7d82,1,0x4a916,0x4a91e);
    case 0x4a916:r.a[1]=am_index(r.a[5],0x8004);r.pc=0x4a930;return true;
    case 0x4a91e:r.a[1]=0xd00034;return pc11_zero(c,r.a[5],0x7e80,1,0x4a930,0x4a92c);
    case 0x4a92c:r.a[1]=am_index(r.a[5],0x7e00);r.pc=0x4a930;return true;
    case 0x4a930:am_word(r.d[0],r.d[0]&1U);return pc11_zero(c,r.a[5],0x8003,1,0x4a93c,0x4a93e);
    case 0x4a93c:r.d[0]=0;r.pc=0x4a93e;return true;
    case 0x4a93e:if(!am_read(c,am_index(r.a[1],r.d[0]&0xffffU),1,value))return false;am_byte(r.d[0],value);return am_return(c);
    // ---- 4d196 (JSR from 1d9b2, 1d95a): TST.W 78(A6); BNE.W 4d1a6 / LEA 5cba(A5),A4; BRA.W 4d1aa / LEA 5ce6(A5),A4 / BRA.B 4d17c.
    case 0x4d196:return pc11_zero(c,r.a[6],0x78,2,0x4d19e,0x4d1a6);
    case 0x4d19e:r.a[4]=am_index(r.a[5],0x5cba);r.pc=0x4d1aa;return true;
    case 0x4d1a6:r.a[4]=am_index(r.a[5],0x5ce6);r.pc=0x4d1aa;return true;
    case 0x4d1aa:r.pc=0x4d17c;return true;
    // ---- 4eb6a (C6 4eb60 fall-through, BYTE 10fd8a not 0): TST.B 5d21(A5); BNE.W 4ed3c / TST.B 7d82(A5); BNE.W 4eba8 / MOVE.W 76(A6),D0; JSR 4a974.l /
    // BNE.W 4eba8 (the Z of 4a974, re-read; contract decision 3) / JSR 4a9ca.l / TST.B D7; BEQ.W 4eb9e / JSR ca5c.l (a later-unit stop) / BRA.W 4eba4 / JSR
    // ca64.l / BRA.W 4ed3c (C6).
    case 0x4eb6a:return pc11_zero(c,r.a[5],0x5d21,1,0x4eb72,0x4ed3c);
    case 0x4eb72:return pc11_zero(c,r.a[5],0x7d82,1,0x4eb7a,0x4eba8);
    case 0x4eb7a:return pc11_field_call(c,0x76,0x4a974,0x4eb84);
    case 0x4eb84:if(!pc11_flag_4a974(c,value))return false;r.pc=value!=0U?0x4eba8:0x4eb88;return true;
    case 0x4eb88:return am_call(c,0x4a9ca,0x4eb8e);
    case 0x4eb8e:r.pc=(r.d[7]&0xffU)==0U?0x4eb9e:0x4eb94;return true;
    case 0x4eb94:case 0x4ebb6:case 0x4ec4a:case 0x4ed2e:return am_call(c,0xca5c,r.pc+6U);                // JSR ca5c.l (E-1).
    case 0x4eb9a:r.pc=0x4eba4;return true;
    case 0x4eb9e:return am_call(c,0xca64,0x4eba4);
    case 0x4eba4:r.pc=0x4ed3c;return true;
    // ---- 4eba8: BSR.W 4e4da / MOVE.W 76(A6),D0; JSR e8c3a.l / JSR ca5c.l / MOVE.W 76(A6),D0; JSR 4a90e.l / MOVE.B D0,a2(A6); MOVE.W 76(A6),D0; MOVEQ
    // #2,D1; JSR b0c.l / MOVE.B #3,9c(A6); MOVE.L #4ebe2,(A6) / 4ebe2 (the continue-wait callback): LEA 7db6(A5),A0; ADDA.W 76(A6),A0; MOVE.B (A0),D0;
    // CMPI.B #3,D0; BEQ.W 4ed3c / CMPI.B #1,D0; BNE.W 4ec32 (else 4ebfc, a later-unit stop).
    case 0x4eba8:return am_call(c,0x4e4da,0x4ebac);
    case 0x4ebac:return pc11_field_call(c,0x76,0xe8c3a,0x4ebb6);
    case 0x4ebbc:case 0x4ec32:return pc11_field_call(c,0x76,0x4a90e,r.pc+0xaU);
    case 0x4ebc6:if(!pc11_put(c,r.a[6],0xa2,1,r.d[0]))return false;return pc11_b0c(c,2,0x4ebd6);
    case 0x4ebd6:if(!pc11_put(c,r.a[6],0x9c,1,3))return false;return pc11_install(c,0x4ebe2,0x4ebe2);
    case 0x4ebe2:
        if(!pc11_get(c,r.a[6],0x76,2,value))return false;r.a[0]=am_index(am_index(r.a[5],0x7db6),value);if(!am_read(c,r.a[0],1,value))return false;
        am_byte(r.d[0],value);r.pc=value==3U?0x4ed3c:0x4ebf4;return true;
    case 0x4ebf4:r.pc=(r.d[0]&0xffU)!=1U?0x4ec32:0x4ebfc;return true;
    // ---- 4ec32: MOVE.W 76(A6),D0; JSR 4a90e.l / MOVE.B a2(A6),D1; MOVE.B D0,a2(A6); CMP.B D1,D0; BLS.W 4ec50 / JSR ca5c.l / TST.B 5d21(A5); BEQ.W 4ec64
    // / MOVE.W 76(A6),D0; MOVEQ #3,D1; JSR b0c.l / JSR ca70.l / MOVE.W (A0),D0; BNE.W 4ec80 / MOVE.W 76(A6),D0; MOVEQ #3,D1; JSR b0c.l / BRA.W 4ecac /
    // CMPI.W #800,D0; BCC.W 4ecac / LEA 104ca8.l,A0; TST.W 76(A6); BEQ.W 4ec9c / LEA 104cae.l,A0 / BTST.B #5,3(A0); BEQ.W 4ecac / JSR ca6a.l.
    case 0x4ec3c:
        if(!pc11_get(c,r.a[6],0xa2,1,value))return false;am_byte(r.d[1],value);if(!pc11_put(c,r.a[6],0xa2,1,r.d[0]))return false;
        r.pc=(r.d[0]&0xffU)<=(r.d[1]&0xffU)?0x4ec50:0x4ec4a;return true;
    case 0x4ec50:return pc11_zero(c,r.a[5],0x5d21,1,0x4ec64,0x4ec58);
    case 0x4ec58:return pc11_b0c(c,3,0x4ec64);
    case 0x4ec64:case 0x4ece6:return am_call(c,0xca70,r.pc+6U);                                         // JSR ca70.l (A0 := 10095c).
    case 0x4ec6a:if(!pc11_get(c,r.a[0],0,2,value))return false;am_word(r.d[0],value);r.pc=value!=0U?0x4ec80:0x4ec70;return true;
    case 0x4ec70:return pc11_b0c(c,3,0x4ec7c);
    case 0x4ec7c:r.pc=0x4ecac;return true;
    case 0x4ec80:r.pc=(r.d[0]&0xffffU)>=0x800U?0x4ecac:0x4ec88;return true;
    case 0x4ec88:r.a[0]=0x104ca8;return pc11_zero(c,r.a[6],0x76,2,0x4ec9c,0x4ec96);
    case 0x4ec96:r.a[0]=0x104cae;r.pc=0x4ec9c;return true;
    case 0x4ec9c:return pc11_field_bit(c,r.a[0],3,5,0x4ecac,0x4eca6);
    case 0x4eca6:return am_call(c,0xca6a,0x4ecac);
    // ---- 4ecac: MOVE.W 76(A6),D0; BTST D0,7004(A5) (BYTE, bit D0 mod 8); SEQ.B a1(A6); MOVE.B 5d1f(A5),D0; CMP.B 9a(A6),D0; BEQ.W 4ecd8 / LEA 4e382(PC),A0;
    // TST.B a1(A6); BEQ.W 4ecd4 / LEA 4e34c(PC),A0 / BSR.W 4e564 / MOVE.B a1(A6),D0; NOT.B D0; AND.B 5d1f(A5),D0; BEQ.W 4ed26 / JSR ca70.l / MOVEQ #0,D0;
    // MOVE.B (A0),D0; ADD.W D0,D0; LEA 4e396(PC),A0; MOVE.W (A0,D0.W),D1 (fixed ROM WORD table, live bus); MOVEQ #1,D2; MOVEQ #2,D3; MOVE.W 7c(A6),D0;
    // CMPI.W #0,76(A6); BNE.W 4ed14 / ADDI.W #20,D0; BRA.W 4ed18 / ADDI.W #80,D0 / ADDI.W #140,D0; JSR 35f0.l / BRA.W 4ed34 / TST.B 5d21(A5); BNE.W 4ed34 /
    // JSR ca5c.l / MOVE.B 5d1f(A5),9a(A6); RTS.
    case 0x4ecac:
        if(!pc11_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);if(!pc11_bit(c,r.a[5],0x7004,r.d[0],0,old))return false;
        if(!pc11_put(c,r.a[6],0xa1,1,old?0U:0xffU) || !pc11_get(c,r.a[5],0x5d1f,1,value) || !pc11_get(c,r.a[6],0x9a,1,other))return false;
        am_byte(r.d[0],value);r.pc=value==other?0x4ecd8:0x4ecc4;return true;
    case 0x4ecc4:r.a[0]=0x4e382;return pc11_zero(c,r.a[6],0xa1,1,0x4ecd4,0x4ecd0);
    case 0x4ecd0:r.a[0]=0x4e34c;r.pc=0x4ecd4;return true;
    case 0x4ecd4:return am_call(c,0x4e564,0x4ecd8);
    case 0x4ecd8:
        if(!pc11_get(c,r.a[6],0xa1,1,value) || !pc11_get(c,r.a[5],0x5d1f,1,other))return false;am_byte(r.d[0],(~value)&other);
        r.pc=(r.d[0]&0xffU)==0U?0x4ed26:0x4ece6;return true;
    case 0x4ecec:
        r.d[0]=0;if(!pc11_get(c,r.a[0],0,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]+r.d[0]);r.a[0]=0x4e396;
        if(!am_read(c,am_index(r.a[0],r.d[0]&0xffffU),2,value))return false;am_word(r.d[1],value);r.d[2]=1;r.d[3]=2;
        if(!pc11_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[0],value);return pc11_zero(c,r.a[6],0x76,2,0x4ed0c,0x4ed14);
    case 0x4ed0c:am_word(r.d[0],r.d[0]+0x20U);r.pc=0x4ed18;return true;
    case 0x4ed14:am_word(r.d[0],r.d[0]+0x80U);r.pc=0x4ed18;return true;
    case 0x4ed18:am_word(r.d[0],r.d[0]+0x140U);return am_call(c,0x35f0,0x4ed22);
    case 0x4ed22:r.pc=0x4ed34;return true;
    case 0x4ed26:return pc11_zero(c,r.a[5],0x5d21,1,0x4ed2e,0x4ed34);
    case 0x4ed34:if(!pc11_get(c,r.a[5],0x5d1f,1,value) || !pc11_put(c,r.a[6],0x9a,1,value))return false;return am_return(c);
    // ---- e8c3a (JSR from 4ebb0): MOVE.W D0,-(A7); BSR.W e8ad0 / MOVEQ #0,D0; MOVE.B 3(A0),D0; MOVE.B e8c22(PC,D0.W),D2 (fixed ROM BYTE table, live bus);
    // MOVE.L A0,-(A7); MOVE.W #0 / #0 / #0 / #384 / D2 / #0 / #0,-(A7); MOVEA.L #b3dfc,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.l (the 2986 child
    // b3dfc) / MOVEM.W (A7)+,D0-D6 (sign-extended; flags unchanged); BCC.W e8ca2 (C of 2986) / MOVE.W D2 / D3 / D4 / D5 / D6,76 / 78 / 7a / 7c / 7e(A0);
    // JSR 49214.l / ORI.B #1,CCR (no reader: the MOVE.W of e8ca2 sets C again) / MOVEA.L (A7)+,A4; MOVE.W (A7)+,D0; MOVE.L A6,-(A7); MOVEA.L A0,A6;
    // MOVE.W 2(A4),D3; LEA 4(A4),A4; MOVE.W (A4),D2; MOVE.W 2(A4),D3; JSR e8b6e(PC) / MOVEA.L (A7)+,A6; RTS.
    case 0xe8c3a:if(!am_push(c,2,r.d[0]&0xffffU))return false;return am_call(c,0xe8ad0,0xe8c40);
    case 0xe8c40: {
        r.d[0]=0;if(!pc11_get(c,r.a[0],3,1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,am_index(0xe8c22,r.d[0]&0xffffU),1,value))return false;am_byte(r.d[2],value);
        if(!am_push(c,4,r.a[0]))return false;
        const std::uint32_t words[7]={0,0,0,0x384,r.d[2]&0xffffU,0,0};
        for(unsigned int i=0;i<7U;++i)if(!am_push(c,2,words[i]))return false;
        r.a[0]=0xb3dfc;am_word(r.d[0],0x14);r.a[1]=0x100bf4;return am_call(c,0x2986,0xe8c7c);
    }
    case 0xe8c7c:
        for(unsigned int i=0;i<7U;++i){if(!am_pop(c,2,value))return false;r.d[i]=am_extend_word(value);}
        return pc11_carry(c,0xe8ca2,0xe8c84);
    case 0xe8c84:
        for(unsigned int i=0;i<5U;++i)if(!pc11_put(c,r.a[0],0x76U+2U*i,2,r.d[2U+i]))return false;
        return am_call(c,0x49214,0xe8c9e);
    case 0xe8c9e:r.pc=0xe8ca2;return true;                                                                // ORI.B #1,CCR (the C is not read).
    case 0xe8ca2:
        if(!am_pop(c,4,r.a[4]) || !am_pop(c,2,value))return false;am_word(r.d[0],value);if(!am_push(c,4,r.a[6]))return false;r.a[6]=r.a[0];
        if(!pc11_get(c,r.a[4],2,2,value))return false;am_word(r.d[3],value);r.a[4]=r.a[4]+4U;if(!pc11_get(c,r.a[4],0,2,value))return false;
        am_word(r.d[2],value);if(!pc11_get(c,r.a[4],2,2,value))return false;am_word(r.d[3],value);return am_call(c,0xe8b6e,0xe8cbc);
    case 0xe8cbc:if(!am_pop(c,4,r.a[6]))return false;return am_return(c);
    default:return am_error(c,"unsupported animation player c11 PC");
    }
}
}
