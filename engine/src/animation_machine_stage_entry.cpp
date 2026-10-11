#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (LEA/MOVEA xxx.L, CLR.B xxx.L, MOVEA.L #, MOVE.L #, LEA d16(PC)).
const std::uint32_t SE_SCENE_CLEAR=0x10d44e;                      // 1a620 CLR.B xxx.L
const std::uint32_t SE_BUFFER1=0x109156,SE_BUFFER2=0x10b1d6;      // 1a642/1a64e and 19dee/19dfe LEA xxx.L
const std::uint32_t SE_BUFFER3=0x10d256,SE_BUFFER4=0x10d2d6;      // 19e0e/19e1e LEA xxx.L
const std::uint32_t SE_HEADER1=0x10d356,SE_HEADER2=0x10d364;      // 19df4/19e04 LEA xxx.L
const std::uint32_t SE_HEADER3=0x10d372,SE_HEADER4=0x10d380;      // 19e14/19e24 LEA xxx.L
const std::uint32_t SE_CUE_DEFAULT=0xe89e4;                       // e8a24 LEA e89e4(PC),A0 (address only)
const std::uint32_t SE_EVENT_CALLBACK=0xe9150;                    // e9064 LEA e9150(PC),A1 (address only)
const std::uint32_t SE_HUD_TABLE=0xddfa4;                         // ddf9a LEA ddfa4(PC),A0 (read through the live bus)
const std::uint32_t SE_PALETTE_CLEAR=0x107def;                    // 9060 CLR.B xxx.L
const std::uint32_t SE_CHILD1=0x4fcce,SE_CHILD2=0x4fd20,SE_CHILD3=0x4ff12; // 47b76/47b8c/47bc4 MOVEA.L # (callbacks)
const std::uint32_t SE_TABLE=0x47b06;                             // 47b02 JMP 47b06(PC,D0.W)
// d16(A5) operands use the live A5 (negative displacements are written as their 16-bit two's complement).
bool se_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool se_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// d16(An) read (live register; WORD/LONG alignment is checked by the bus).
bool se_at(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
// BSET #n,d16(A5): memory BYTE read-modify-write, bit number mod 8 (Z not consumed).
bool se_bset(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t bit) {
    std::uint32_t value=0;if(!se_read(c,displacement,1,value))return false;
    return se_write(c,displacement,1,(value|(1U<<(bit&7U)))&255U);
}
// Consumers of a C returned by a callee: BCC clear_pc, otherwise set_pc.
bool se_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"stage entry caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// LEA d16(A5),A0; MOVE.L (A0),D0; MOVE.L 4(A0),D1; MOVEA.W #0,A1; JSR target.L.
bool se_pair_call(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t target,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[5],displacement);
    if(!am_read(c,r.a[0],4,value))return false;r.d[0]=value;
    if(!se_at(c,r.a[0],4,4,value))return false;r.d[1]=value;
    r.a[1]=0;return am_call(c,target,return_pc);
}
// LEA buffer.L,A0; LEA header.L,A1; JSR 19e30(PC).
bool se_header_call(AnimationMachineContext& c,std::uint32_t buffer,std::uint32_t header,std::uint32_t return_pc) {
    c.s.a[0]=buffer;c.s.a[1]=header;return am_call(c,0x19e30,return_pc);
}
}
// Stage controller F1a: entry body 47a94..47aec (1a5a4 scene initialization and phase catch-up with 19768 19938
// 199d4 199ea 19b50 19dee/19e30 1a07a 1a3c8 1a414 and the 17292 unrolled 8 KiB clear, e8a1c cue install, e905c event
// node reinstall and lookup walk), the 72f0 palette gate 47af0/47af6, the 47b06 table and its eight targets with the
// dispatcher callbacks 47b5c/47bfc, and the activation 47c04 (9060 4e254 477a2->ddf9a->362a ca76 ca56 c3c0).
// Existing executors called: U1 480bc, U2 1a29e/1a26a/19cee, U3 1972a/18fd2/18c06/1971c (known C), U4 1a7a8,
// U5 19772/1a40e/1a470/16fee, U7 e8af4, cleanup 43e22/2a28, palette_bind 16fac, exit 48398/8c16/47c5a, screen caf0,
// fade_card 28ae (known C)/480b6/4809a, hud 35f0. 47af6 with C clear leaves PC 47af0 and returns Waiting (main decision
// 2): the IRQ that clears 107ded bit7 is a declared host change before the resume. The 47b06 JMP index has no range
// check: the computed PC 47b06+index is followed (odd targets fail as unaligned, non-start targets as unsupported).
// e909c (TRAP #f) is a boundary without an executor. PVC bank writes use the existing am_write path. ROM data
// (catalog/lookup/event records, ddfa4 HUD table) is read through the live bus; 47aa6/47aca re-read LONG 76(A6) and
// the record live. All d16(A5) operands use the live A5. Loops 1a65a 1a422 e908a 362a have no extra limit (block
// budget only).
bool animation_stage_entry_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // 47a94: MOVEA.L 76(A6),A4; MOVEA.L 2(A4),A0; MOVE.W e(A4),D0; JSR 1a5a4.L.
    case 0x47a94:
        if(!se_at(c,r.a[6],0x76,4,value))return false;r.a[4]=value;
        if(!se_at(c,r.a[4],2,4,value))return false;r.a[0]=value;
        if(!se_at(c,r.a[4],0xe,2,value))return false;am_word(r.d[0],value);
        return am_call(c,0x1a5a4,0x47aa6);
    // MOVEA.L 76(A6),A4 (live re-read); MOVEA.L 6(A4),A0; JSR e8a1c.L.
    case 0x47aa6:
        if(!se_at(c,r.a[6],0x76,4,value))return false;r.a[4]=value;
        if(!se_at(c,r.a[4],6,4,value))return false;r.a[0]=value;
        return am_call(c,0xe8a1c,0x47ab4);
    // BSET #1/#3/#5,5683(A5); BSR 48398.
    case 0x47ab4:
        if(!se_bset(c,0x5683,1) || !se_bset(c,0x5683,3) || !se_bset(c,0x5683,5))return false;
        return am_call(c,0x48398,0x47aca);
    // MOVEA.L 76(A6),A4; MOVEA.L a(A4),A0; CMPA.W #0,A0 (whole LONG); BEQ 47adc.
    case 0x47aca:
        if(!se_at(c,r.a[6],0x76,4,value))return false;r.a[4]=value;
        if(!se_at(c,r.a[4],0xa,4,value))return false;r.a[0]=value;
        r.pc=value?0x47ada:0x47adc;return true;
    case 0x47ada:if(!am_read(c,r.a[0],4,value))return false;r.a[0]=value;r.pc=0x47adc;return true; // MOVEA.L (A0),A0.
    // MOVE.W e(A4),D0; JSR e905c.L.
    case 0x47adc:if(!se_at(c,r.a[4],0xe,2,value))return false;am_word(r.d[0],value);return am_call(c,0xe905c,0x47ae6);
    case 0x47ae6:if(!am_write(c,r.a[6],4,0x47af0))return false;r.pc=0x480bc;return true; // MOVE.L #47af0,(A6); BRA 480bc.
    // 47af0 (dispatcher callback): JSR 72f0.L. 47af6: BCC 47af0 (C clear: wait at 47af0, main decision 2).
    case 0x47af0:return am_call(c,0x72f0,0x47af6);
    case 0x47af6:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"stage entry caller requires known carry");
        if(r.carry==AnimationCarryClear) {r.pc=0x47af0;c.waiting=true;return true;}
        r.pc=0x47af8;return true;
    // MOVEA.L 76(A6),A0; MOVEQ #0,D0; MOVE.B 1(A0),D0; JMP 47b06(PC,D0.W) (no range check: computed PC).
    case 0x47af8:
        if(!se_at(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        r.d[0]=0;if(!se_at(c,r.a[0],1,1,value))return false;am_byte(r.d[0],value);
        r.pc=am_index(SE_TABLE,r.d[0]);return true;
    // Table slots (BRA.W).
    case 0x47b06:r.pc=0x47b26;return true;
    case 0x47b0a:r.pc=0x47b3e;return true;
    case 0x47b0e:r.pc=0x47b68;return true;
    case 0x47b12:r.pc=0x47b76;return true;
    case 0x47b16:r.pc=0x47b8c;return true;
    case 0x47b1a:r.pc=0x47ba2;return true;
    case 0x47b1e:r.pc=0x480b6;return true;
    case 0x47b22:r.pc=0x4809a;return true;
    case 0x47b26:return am_call(c,0xcaf0,0x47b2c); // JSR caf0.L.
    case 0x47b2c:r.d[0]=0;r.d[1]=0;r.d[2]=0;r.d[3]=0;return am_call(c,0x8c16,0x47b3a); // MOVEQ #0,D0..D3; JSR 8c16.L.
    case 0x47b3a:case 0x47b64:r.pc=0x47c04;return true; // BRA 47c04.
    // MOVEQ #0,D0..D2; MOVEQ #14,D3; MOVE.W D3,7a(A6).
    case 0x47b3e:
        r.d[0]=0;r.d[1]=0;r.d[2]=0;r.d[3]=0x14;
        if(!am_write(c,am_index(r.a[6],0x7a),2,r.d[3]&65535U))return false;r.pc=0x47b4a;return true;
    case 0x47b4a:return am_call(c,0x8c16,0x47b50); // JSR 8c16.L.
    case 0x47b50:return am_call(c,0xcaf0,0x47b56); // JSR caf0.L.
    case 0x47b56:if(!am_write(c,r.a[6],4,0x47b5c))return false;r.pc=0x47b5c;return true; // MOVE.L #47b5c,(A6).
    // 47b5c (dispatcher callback): SUBQ.W #1,7a(A6); BCC 480bc (C = borrow, 0 -> ffff falls through).
    case 0x47b5c:
        if(!se_at(c,r.a[6],0x7a,2,value))return false;
        if(!am_write(c,am_index(r.a[6],0x7a),2,(value-1U)&65535U))return false;
        r.pc=(value&65535U)==0U?0x47b64:0x480bc;return true;
    // MOVEQ #0,D0..D2; MOVEQ #20,D3; MOVE.W D3,7a(A6); BRA 47b4a.
    case 0x47b68:
        r.d[0]=0;r.d[1]=0;r.d[2]=0;r.d[3]=0x20;
        if(!am_write(c,am_index(r.a[6],0x7a),2,r.d[3]&65535U))return false;r.pc=0x47b4a;return true;
    // MOVEA.L #child,A0; MOVE.W #0,D0; JSR 28ae.L (known C).
    case 0x47b76:r.a[0]=SE_CHILD1;am_word(r.d[0],0);return am_call(c,0x28ae,0x47b86);
    case 0x47b86:return se_carry(c,0x47b26,0x47b88); // BCC 47b26.
    case 0x47b88:case 0x47b9e:r.pc=0x47be4;return true; // BRA 47be4.
    case 0x47b8c:r.a[0]=SE_CHILD2;am_word(r.d[0],0);return am_call(c,0x28ae,0x47b9c);
    case 0x47b9c:return se_carry(c,0x47b26,0x47b9e); // BCC 47b26.
    // MOVEA.L 76(A6),A0; MOVEA.L 6(A0),A0; JSR e8af4.L.
    case 0x47ba2:
        if(!se_at(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        if(!se_at(c,r.a[0],6,4,value))return false;r.a[0]=value;
        return am_call(c,0xe8af4,0x47bb0);
    // LEA 538e(A5),A0; ADD.W 14(A0),D0; ADD.W 18(A0),D1; MOVE.W D0,5690(A5); MOVE.W D1,5692(A5); MOVEA.L #4ff12,A0;
    // MOVE.W #0,D0; JSR 28ae.L.
    case 0x47bb0:
        r.a[0]=am_index(r.a[5],0x538e);
        if(!se_at(c,r.a[0],0x14,2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!se_at(c,r.a[0],0x18,2,value))return false;am_word(r.d[1],r.d[1]+value);
        if(!se_write(c,0x5690,2,r.d[0]&65535U) || !se_write(c,0x5692,2,r.d[1]&65535U))return false;
        r.a[0]=SE_CHILD3;am_word(r.d[0],0);return am_call(c,0x28ae,0x47bd4);
    case 0x47bd4:return se_carry(c,0x47b26,0x47bd8); // BCC 47b26.
    // MOVE.W 5690(A5),76(A0); MOVE.W 5692(A5),78(A0) (A0 = the new object).
    case 0x47bd8:
        if(!se_read(c,0x5690,2,value) || !am_write(c,am_index(r.a[0],0x76),2,value&65535U))return false;
        if(!se_read(c,0x5692,2,value) || !am_write(c,am_index(r.a[0],0x78),2,value&65535U))return false;
        r.pc=0x47be4;return true;
    // CLR.B 62(A6); MOVEQ #0,D0..D3; JSR 8c16.L.
    case 0x47be4:
        if(!am_write(c,am_index(r.a[6],0x62),1,0))return false;
        r.d[0]=0;r.d[1]=0;r.d[2]=0;r.d[3]=0;return am_call(c,0x8c16,0x47bf6);
    case 0x47bf6:if(!am_write(c,r.a[6],4,0x47bfc))return false;r.pc=0x47bfc;return true; // MOVE.L #47bfc,(A6).
    // 47bfc (dispatcher callback): TST.B 62(A6); BEQ 480bc.
    case 0x47bfc:if(!se_at(c,r.a[6],0x62,1,value))return false;r.pc=(value&255U)?0x47c04:0x480bc;return true;

    // 47c04 activation: TST.B 5684(A5); BNE 47c1e.
    case 0x47c04:if(!se_read(c,0x5684,1,value))return false;r.pc=(value&255U)?0x47c1e:0x47c0c;return true;
    case 0x47c0c:return am_call(c,0x9060,0x47c12);  // JSR 9060.L.
    case 0x47c12:return am_call(c,0x4e254,0x47c18); // JSR 4e254.L.
    case 0x47c18:if(!se_bset(c,0x5683,4))return false;r.pc=0x47c1e;return true; // BSET #4,5683(A5).
    // MOVEQ #1,D0; AND.B 5684(A5),D0; BEQ 47c2c.
    case 0x47c1e:
        r.d[0]=1;if(!se_read(c,0x5684,1,value))return false;am_byte(r.d[0],r.d[0]&value);
        r.pc=(r.d[0]&255U)?0x47c28:0x47c2c;return true;
    case 0x47c28:return am_call(c,0x477a2,0x47c2c); // BSR 477a2.
    // MOVEQ #4,D0; AND.B 5684(A5),D0; BNE 47c3c.
    case 0x47c2c:
        r.d[0]=4;if(!se_read(c,0x5684,1,value))return false;am_byte(r.d[0],r.d[0]&value);
        r.pc=(r.d[0]&255U)?0x47c3c:0x47c36;return true;
    case 0x47c36:return am_call(c,0xca76,0x47c3c); // JSR ca76.L.
    case 0x47c3c:return am_call(c,0xca56,0x47c42); // JSR ca56.L.
    // BSET #2,5683(A5); MOVE.B 7c(A6),D0; CMPI.B #6,D0; BCC 47c5a.
    case 0x47c42:
        if(!se_bset(c,0x5683,2))return false;
        if(!se_at(c,r.a[6],0x7c,1,value))return false;am_byte(r.d[0],value);
        r.pc=(r.d[0]&255U)>=6U?0x47c5a:0x47c54;return true;
    case 0x47c54:return am_call(c,0xc3c0,0x47c5a); // JSR c3c0.L.

    // 72f0: MOVE.B -213(A5),D0; SUBI.B #80,D0 (C = borrow: BYTE < 80); RTS.
    case 0x72f0:
        if(!se_read(c,0xfded,1,value))return false;
        am_byte(r.d[0],value-0x80U);r.carry=(value&255U)<0x80U?AnimationCarrySet:AnimationCarryClear;
        return am_return(c);

    // 1a5a4: MOVE.W #1,-7ff0(A5); MOVE.W #2000,2ffff2.L; MOVE.W #0,2ffff0.L; MOVE.W D0,541c(A5); JSR 1a07a(PC).
    case 0x1a5a4:
        if(!se_write(c,0x8010,2,1) || !am_write(c,0x2ffff2,2,0x2000) || !am_write(c,0x2ffff0,2,0))return false;
        if(!se_write(c,0x541c,2,r.d[0]&65535U))return false;
        return am_call(c,0x1a07a,0x1a5c2);
    // Scene field initialization in original order, CLR.B 10d44e.L, BSR 19768.
    case 0x1a5c2:
        if(!se_write(c,0x5418,2,0) || !se_write(c,0x5426,2,0xa0) || !se_write(c,0x5428,2,0x80) ||
           !se_write(c,0x542a,2,0) || !se_write(c,0x542c,2,0) || !se_write(c,0x5444,2,0x8000) ||
           !se_write(c,0x5446,2,0x8000) || !se_write(c,0x5448,2,0) || !se_write(c,0x544a,2,0) ||
           !se_write(c,0x5442,2,0x7fff) || !se_write(c,0x5440,2,0x7fff) || !se_write(c,0x544c,2,0) ||
           !se_write(c,0x542e,2,0xffff) || !se_write(c,0x5430,2,0xffff) || !se_write(c,0x5432,2,0) ||
           !se_write(c,0x5434,4,0) || !se_write(c,0x5438,4,0) || !se_write(c,0x543c,2,0) ||
           !se_write(c,0x540c,2,0) || !am_write(c,SE_SCENE_CLEAR,1,0))return false;
        return am_call(c,0x19768,0x1a62a);
    case 0x1a62a:return am_call(c,0x1a29e,0x1a62e); // BSR 1a29e.
    case 0x1a62e:return am_call(c,0x19b50,0x1a632); // BSR 19b50.
    case 0x1a632:return am_call(c,0x19dee,0x1a636); // BSR 19dee.
    case 0x1a636:return am_call(c,0x1a3c8,0x1a63a); // BSR 1a3c8.
    case 0x1a63a:r.a[0]=0;return am_call(c,0x1a40e,0x1a642); // MOVEA.W #0,A0; BSR 1a40e.
    case 0x1a642:r.a[0]=SE_BUFFER1;return am_call(c,0x17292,0x1a64e); // LEA 109156.L,A0; JSR 17292.L.
    case 0x1a64e:r.a[0]=SE_BUFFER2;return am_call(c,0x17292,0x1a65a); // LEA 10b1d6.L,A0; JSR 17292.L.
    case 0x1a65a:return am_call(c,0x1a26a,0x1a65e); // BSR 1a26a.
    case 0x1a65e:return am_call(c,0x199d4,0x1a662); // BSR 199d4.
    // MOVE.W 541c(A5),D6; CMP.W D6,D7; BCC 1a67c.
    case 0x1a662:
        if(!se_read(c,0x541c,2,value))return false;am_word(r.d[6],value);
        r.pc=(r.d[7]&65535U)>=(r.d[6]&65535U)?0x1a67c:0x1a66c;return true;
    case 0x1a66c:return am_call(c,0x199ea,0x1a670); // BSR 199ea.
    case 0x1a670:return se_carry(c,0x1a678,0x1a674); // BCC 1a678 (C from 199f6 ORI or U3 1971c).
    case 0x1a674:if(!se_write(c,0x541c,2,r.d[7]&65535U))return false;r.pc=0x1a678;return true; // MOVE.W D7,541c(A5).
    case 0x1a678:r.pc=0x1a67e;return true; // BRA 1a67e.
    case 0x1a67c:am_word(r.d[7],r.d[6]);r.pc=0x1a67e;return true; // MOVE.W D6,D7.
    // MOVE.W 5416(A5),D6; CMP.W D6,D7; BCS 1a68a.
    case 0x1a67e:
        if(!se_read(c,0x5416,2,value))return false;am_word(r.d[6],value);
        r.pc=(r.d[7]&65535U)<(r.d[6]&65535U)?0x1a68a:0x1a688;return true;
    case 0x1a688:am_word(r.d[7],r.d[6]);r.pc=0x1a68a;return true; // MOVE.W D6,D7.
    // MOVE.W D7,5418(A5); SWAP D7; CLR.W D7; BSR 19938.
    case 0x1a68a:
        if(!se_write(c,0x5418,2,r.d[7]&65535U))return false;am_swap(r.d[7]);am_word(r.d[7],0);
        return am_call(c,0x19938,0x1a696);
    // MOVE.L D0,53bc(A5); MOVE.L D1,53c0(A5); BSR 1a7a8.
    case 0x1a696:
        if(!se_write(c,0x53bc,4,r.d[0]) || !se_write(c,0x53c0,4,r.d[1]))return false;
        return am_call(c,0x1a7a8,0x1a6a2);
    // MOVE.W 5418(A5),D7; CMP.W 541c(A5),D7; BCS 1a65a.
    case 0x1a6a2:
        if(!se_read(c,0x5418,2,value))return false;am_word(r.d[7],value);
        if(!se_read(c,0x541c,2,value))return false;
        r.pc=(r.d[7]&65535U)<(value&65535U)?0x1a65a:0x1a6ac;return true;
    case 0x1a6ac:return se_pair_call(c,0x538e,0x43e22,0x1a6c0);
    case 0x1a6c0:return se_pair_call(c,0x1156,0x16fee,0x1a6d4);
    case 0x1a6d4:return se_pair_call(c,0x31d6,0x16fee,0x1a6e8);
    case 0x1a6e8:return se_pair_call(c,0x5256,0x16fee,0x1a6fc);
    case 0x1a6fc:return se_pair_call(c,0x52d6,0x16fee,0x1a710);
    // MOVE.W 541e(A5),D7; CMP.W 541c(A5),D7; BCC 1a720.
    case 0x1a710:
        if(!se_read(c,0x541e,2,value))return false;am_word(r.d[7],value);
        if(!se_read(c,0x541c,2,value))return false;
        r.pc=(r.d[7]&65535U)>=(value&65535U)?0x1a720:0x1a71c;return true;
    case 0x1a71c:return am_call(c,0x1a29e,0x1a720); // BSR 1a29e.
    case 0x1a720:return am_call(c,0x1a414,0x1a724); // BSR 1a414.
    // MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L; RTS.
    case 0x1a724:if(!am_zero_bank(c))return false;return am_return(c);

    // 17292: LEA 80(A0),A1; MOVEQ #0,D0; 2048 x MOVE.L D0,(A1)+ (ascending; any failure rolls back); RTS.
    case 0x17292:
        r.a[1]=am_index(r.a[0],0x80);r.d[0]=0;
        for(unsigned int i=0;i<2048;++i) {if(!am_write(c,r.a[1],4,0))return false;r.a[1]+=4U;}
        return am_return(c);
    // 19768: MOVEA.L #0,A1; MOVEQ #0,D0; MOVEQ #0,D1; falls through into U5 19772.
    case 0x19768:r.a[1]=0;r.d[0]=0;r.d[1]=0;r.pc=0x19772;return true;
    // 19938: MOVEA.L 53b4(A5),A1; CMPA.W #0,A1; BNE 19956.
    case 0x19938:if(!se_read(c,0x53b4,4,value))return false;r.a[1]=value;r.pc=value?0x19956:0x19944;return true;
    // MOVEQ #0,D0; MOVEQ #0,D1; MOVE.W 53b8(A5),D0; MOVE.W 53ba(A5),D1; SWAP D0; SWAP D1; RTS.
    case 0x19944:
        r.d[0]=0;r.d[1]=0;
        if(!se_read(c,0x53b8,2,value))return false;am_word(r.d[0],value);
        if(!se_read(c,0x53ba,2,value))return false;am_word(r.d[1],value);
        am_swap(r.d[0]);am_swap(r.d[1]);return am_return(c);
    case 0x19956:return am_call(c,0x1972a,0x1995a); // BSR 1972a.
    case 0x1995a:if(!se_write(c,0x53b4,4,r.a[1]))return false;return am_call(c,0x18fd2,0x19962); // MOVE.L A1,53b4(A5); BSR 18fd2.
    // MOVEQ #0,D2; MOVE.W 8(A1),D2; SWAP D2; BSR 18c06.
    case 0x19962:
        r.d[2]=0;if(!se_at(c,r.a[1],8,2,value))return false;am_word(r.d[2],value);am_swap(r.d[2]);
        return am_call(c,0x18c06,0x1996e);
    case 0x1996e:return se_carry(c,0x19974,0x19972); // BCC 19974.
    case 0x19972:r.d[1]+=r.d[2];r.pc=0x19974;return true; // ADD.L D2,D1.
    case 0x19974:r.d[0]+=r.d[2];return am_return(c);    // ADD.L D2,D0; RTS.
    // 199d4: MOVEA.L 53b4(A5),A1; CMPA.W #0,A1; BNE 199e4.
    case 0x199d4:if(!se_read(c,0x53b4,4,value))return false;r.a[1]=value;r.pc=value?0x199e4:0x199e0;return true;
    case 0x199e0:r.d[7]=0;return am_return(c); // MOVEQ #0,D7; RTS.
    case 0x199e4:if(!se_at(c,r.a[1],0xa,2,value))return false;am_word(r.d[7],value);return am_return(c); // MOVE.W a(A1),D7; RTS.
    // 199ea: MOVEA.L 53b4(A5),A1; CMPA.W #0,A1; BNE 199fc.
    case 0x199ea:if(!se_read(c,0x53b4,4,value))return false;r.a[1]=value;r.pc=value?0x199fc:0x199f6;return true;
    case 0x199f6:r.carry=AnimationCarrySet;return am_return(c); // ORI #1,CCR; RTS.
    case 0x199fc:r.pc=0x1971c;return true; // BRA 1971c (U3 returns its known C).
    // 19b50: CLR.B 53cc; CLR.L 53de/53e2/53fc/5400; CLR.W 53ee/53f0; MOVE.W #a0,53d6; MOVE.W #80,53d8; CLR.W 53da/53dc;
    // MOVE.L #60000,53e6/53ea; BSR 19cee.
    case 0x19b50:
        if(!se_write(c,0x53cc,1,0) || !se_write(c,0x53de,4,0) || !se_write(c,0x53e2,4,0) || !se_write(c,0x53fc,4,0) ||
           !se_write(c,0x5400,4,0) || !se_write(c,0x53ee,2,0) || !se_write(c,0x53f0,2,0) || !se_write(c,0x53d6,2,0xa0) ||
           !se_write(c,0x53d8,2,0x80) || !se_write(c,0x53da,2,0) || !se_write(c,0x53dc,2,0) ||
           !se_write(c,0x53e6,4,0x60000) || !se_write(c,0x53ea,4,0x60000))return false;
        return am_call(c,0x19cee,0x19b94);
    case 0x19b94:case 0x19e2e:return am_return(c); // RTS.
    // 19dee: four (buffer, header) pairs through JSR 19e30(PC).
    case 0x19dee:return se_header_call(c,SE_BUFFER1,SE_HEADER1,0x19dfe);
    case 0x19dfe:return se_header_call(c,SE_BUFFER2,SE_HEADER2,0x19e0e);
    case 0x19e0e:return se_header_call(c,SE_BUFFER3,SE_HEADER3,0x19e1e);
    case 0x19e1e:return se_header_call(c,SE_BUFFER4,SE_HEADER4,0x19e2e);
    // 19e30: CLR.L (A1); CLR.W 4/6/8/a(A1); MOVE.B #10,c(A1); JSR 16fac.L.
    case 0x19e30:
        if(!am_write(c,r.a[1],4,0) || !am_write(c,am_index(r.a[1],4),2,0) || !am_write(c,am_index(r.a[1],6),2,0) ||
           !am_write(c,am_index(r.a[1],8),2,0) || !am_write(c,am_index(r.a[1],0xa),2,0) ||
           !am_write(c,am_index(r.a[1],0xc),1,0x10))return false;
        return am_call(c,0x16fac,0x19e4e);
    // MOVEA.W #0,A1; MOVE.L 538e(A5),D0; MOVE.L 5392(A5),D1; JMP 16fee.L (tail call).
    case 0x19e4e:
        r.a[1]=0;if(!se_read(c,0x538e,4,value))return false;r.d[0]=value;
        if(!se_read(c,0x5392,4,value))return false;r.d[1]=value;r.pc=0x16fee;return true;
    // 1a07a: MOVE.L A0,5412(A5); MOVE.W #0,5416(A5); RTS.
    case 0x1a07a:if(!se_write(c,0x5412,4,r.a[0]) || !se_write(c,0x5416,2,0))return false;return am_return(c);
    // 1a3c8: CLR.W 5404(A5); CLR.W 5406(A5); CLR.L 5408(A5); RTS.
    case 0x1a3c8:
        if(!se_write(c,0x5404,2,0) || !se_write(c,0x5406,2,0) || !se_write(c,0x5408,4,0))return false;return am_return(c);
    // 1a414: MOVEA.L 540e(A5),A0; CMPA.W #0,A0; BNE 1a422.
    case 0x1a414:if(!se_read(c,0x540e,4,value))return false;r.a[0]=value;r.pc=value?0x1a422:0x1a420;return true;
    case 0x1a420:case 0x1a42c:case 0x1a436:return am_return(c); // RTS.
    // MOVE.W (A0),D7; CMPI.W #ffff,D7; BNE 1a42e.
    case 0x1a422:if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[7],value);r.pc=(value&65535U)==0xffffU?0x1a42c:0x1a42e;return true;
    // CMP.W 5418(A5),D7; BLS 1a438 (unsigned D7 <= WORD).
    case 0x1a42e:if(!se_read(c,0x5418,2,value))return false;r.pc=(r.d[7]&65535U)<=(value&65535U)?0x1a438:0x1a436;return true;
    case 0x1a438:return am_call(c,0x1a470,0x1a43c); // BSR 1a470.
    case 0x1a43c:if(!se_write(c,0x540e,4,r.a[0]))return false;r.pc=0x1a422;return true; // MOVE.L A0,540e(A5); BRA 1a422.

    // e8a1c: CMPA.W #0,A0; BNE e8a28 / LEA e89e4(PC),A0.
    case 0xe8a1c:r.pc=r.a[0]?0xe8a28:0xe8a24;return true;
    case 0xe8a24:r.a[0]=SE_CUE_DEFAULT;r.pc=0xe8a28;return true;
    // MOVE.L A0,5e26(A5); MOVE.B #ff,5e2e(A5); MOVE.B #0,5e2f(A5); RTS.
    case 0xe8a28:
        if(!se_write(c,0x5e26,4,r.a[0]) || !se_write(c,0x5e2e,1,0xff) || !se_write(c,0x5e2f,1,0))return false;
        return am_return(c);
    // e905c: MOVE.L A0,-(A7); MOVE.W D0,-(A7); LEA -740c(A5),A0; LEA e9150(PC),A1; JSR 2a28.L.
    case 0xe905c:
        if(!am_push(c,4,r.a[0]) || !am_push(c,2,r.d[0]&65535U))return false;
        r.a[0]=am_index(r.a[5],0x8bf4);r.a[1]=SE_EVENT_CALLBACK;return am_call(c,0x2a28,0xe906e);
    // MOVE.W (A7)+,D0 (low WORD); MOVE.L (A7)+,D7; BNE e907c (Z of the LONG).
    case 0xe906e:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        if(!am_pop(c,4,value))return false;r.d[7]=value;r.pc=value?0xe907c:0xe9076;return true;
    case 0xe9076:if(!am_write(c,am_index(r.a[0],0x76),4,r.d[7]))return false;return am_return(c); // MOVE.L D7,76(A0); RTS.
    // MOVEA.L D7,A1; MOVE.W (A1)+,D1; TST.W D0; BEQ e90ac.
    case 0xe907c:
        r.a[1]=r.d[7];if(!am_read(c,r.a[1],2,value))return false;r.a[1]+=2U;am_word(r.d[1],value);
        r.pc=(r.d[0]&65535U)?0xe9086:0xe90ac;return true;
    case 0xe9086:r.a[1]=am_index(r.a[1],r.d[1]);r.pc=0xe908a;return true; // LEA (A1,D1.W),A1.
    // MOVE.B (A1),D1; CMPI.B #ff,D1; BEQ e90ac.
    case 0xe908a:if(!am_read(c,r.a[1],1,value))return false;am_byte(r.d[1],value);r.pc=(value&255U)==0xffU?0xe90ac:0xe9094;return true;
    case 0xe9094:r.pc=(r.d[1]&255U)==0U?0xe909e:0xe909c;return true; // CMPI.B #0,D1; BEQ e909e (else TRAP #f boundary).
    // CMP.W 2(A1),D0; BLS e90ac (unsigned D0 <= WORD).
    case 0xe909e:if(!se_at(c,r.a[1],2,2,value))return false;r.pc=(r.d[0]&65535U)<=(value&65535U)?0xe90ac:0xe90a6;return true;
    case 0xe90a6:if(!se_at(c,r.a[1],4,2,value))return false;r.a[1]=am_index(r.a[1],value);r.pc=0xe908a;return true; // ADDA.W 4(A1),A1; BRA e908a.
    // MOVE.L A1,D7; MOVE.L D7,76(A0); bank 1000 reset (-7ff0(A5), 2ffff2, 2ffff0); RTS.
    case 0xe90ac:
        r.d[7]=r.a[1];if(!am_write(c,am_index(r.a[0],0x76),4,r.d[7]) || !am_zero_bank(c))return false;
        return am_return(c);

    // 477a2: MOVE.W #7162,D0; JMP ddf9a.L. ddf9a: LEA ddfa4(PC),A0; JMP 362a.L.
    case 0x477a2:am_word(r.d[0],0x7162);r.pc=0xddf9a;return true;
    case 0xddf9a:r.a[0]=SE_HUD_TABLE;r.pc=0x362a;return true;
    // 362a: MOVE.W (A0)+,D1; CMPI.W #ffff,D1; BNE 3636.
    case 0x362a:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[1],value);
        r.pc=(value&65535U)==0xffffU?0x3634:0x3636;return true;
    case 0x3634:return am_return(c); // RTS.
    // MOVE.W D0,-(A7); ADD.W D1,D0; MOVEQ #0,D2; MOVEQ #0,D3; MOVE.W (A0)+,D1; MOVE.B (A0)+,D2; MOVE.B (A0)+,D3;
    // MOVE.L A0,-(A7); JSR 35f0(PC).
    case 0x3636:
        if(!am_push(c,2,r.d[0]&65535U))return false;am_word(r.d[0],r.d[0]+r.d[1]);r.d[2]=0;r.d[3]=0;
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[1],value);
        if(!am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;am_byte(r.d[2],value);
        if(!am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;am_byte(r.d[3],value);
        if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x35f0,0x364a);
    // MOVEA.L (A7)+,A0; MOVE.W (A7)+,D0 (low WORD); BRA 362a.
    case 0x364a:
        if(!am_pop(c,4,value))return false;r.a[0]=value;
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.pc=0x362a;return true;

    case 0x9060:if(!am_write(c,SE_PALETTE_CLEAR,1,0))return false;return am_return(c); // CLR.B 107def.L; RTS.
    // 4e254: MOVE.B #ff,5d1f(A5); CLR.B 5d20(A5); MOVE.B #0,-75be(A5); MOVE.B #0,-74fa(A5); RTS.
    case 0x4e254:
        if(!se_write(c,0x5d1f,1,0xff) || !se_write(c,0x5d20,1,0) || !se_write(c,0x8a42,1,0) || !se_write(c,0x8b06,1,0))return false;
        return am_return(c);
    case 0xca56:if(!se_write(c,0x8967,1,0))return false;return am_return(c);    // CLR.B -7699(A5); RTS.
    case 0xca76:if(!se_write(c,0x8965,1,0xff))return false;return am_return(c); // MOVE.B #ff,-769b(A5); RTS.
    // c3c0: CMP.B -cf(A5),D0; BLE c3cc (signed D0.B <= BYTE).
    case 0xc3c0:{
        if(!se_read(c,0xff31,1,value))return false;
        const int left=static_cast<int>(r.d[0]&255U)-((r.d[0]&0x80U)?256:0);
        const int right=static_cast<int>(value&255U)-((value&0x80U)?256:0);
        r.pc=left<=right?0xc3cc:0xc3c8;return true;}
    case 0xc3c8:if(!se_write(c,0xff31,1,r.d[0]&255U))return false;r.pc=0xc3cc;return true; // MOVE.B D0,-cf(A5).
    case 0xc3cc:return am_return(c); // RTS.
    default:return am_error(c,"unsupported animation stage entry PC");
    }
}
}
