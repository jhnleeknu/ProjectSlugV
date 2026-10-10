#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (BTST xxx.L, MOVE.B xxx.L, LEA xxx.L, CMPA.L #, MOVEA.L #, LEA d16(PC)).
const std::uint32_t BC_DEBUG=0x10f001;                       // 4aa88/4ab4e/e8ac2 BTST.B #n,xxx.L
const std::uint32_t BC_SLOTS=0x10daf8,BC_SLOTS_END=0x10db78; // 4aa96 LEA, 4aaf4 CMPA.L #
const std::uint32_t BC_RING_END=0x10dc88;                    // 4ab24 CMPA.L #
const std::uint32_t BC_INPUT1=0x104cab,BC_INPUT2=0x104cb1;   // 4ab5a/4ab60 MOVE.B/OR.B xxx.L
const std::uint32_t BC_CUE_CALLBACK=0xd5f16,BC_PARENT=0x100bf4; // e8a74/e8a7e MOVEA.L # (address constants, not read)
const std::uint32_t BC_POSITION_TABLE=0xe8a0c;               // e8aa2 LEA e8a0c(PC),A1 (read through the live bus)
const std::uint32_t BC_DEBUG_POSITION=0x10d38e;              // e8b18 LEA xxx.L,A1
const std::uint32_t BC_CUE_RETURN=0xe8a8a;                   // return LONG of the e8a84 JSR 2986
const std::uint32_t BC_LIMIT=0x104ca0;                       // 28b4 CMP.W xxx.L,D0 (re-read by 298e on failure)
const std::uint32_t BC_CUE=0x10de26,BC_ADD_X=0x10d3bc,BC_ADD_Y=0x10d3c0; // e8a54/e8b04/e8b12 with A5=108000
// d16(A5) operands use the live A5.
bool bc_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool bc_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// BTST #n,<memory BYTE>; branch on the tested bit (bit number mod 8; Z only).
bool bc_test(AnimationMachineContext& c,std::uint32_t address,std::uint32_t bit,std::uint32_t set_pc,std::uint32_t clear_pc) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    c.s.pc=((value>>(bit&7U))&1U)?set_pc:clear_pc;return true;
}
// MOVE.B src(A5),dst(A5) (one BYTE read, one BYTE write).
bool bc_copy(AnimationMachineContext& c,std::uint32_t source,std::uint32_t target) {
    std::uint32_t value=0;return bc_read(c,source,1,value) && bc_write(c,target,1,value&255U);
}
// MOVE.W (A1)+,(A0)+: WORD read, A1+=2, WORD write, A0+=2.
bool bc_move_word(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[1],2,value))return false;c.s.a[1]+=2U;
    if(!am_write(c,c.s.a[0],2,value&65535U))return false;c.s.a[0]+=2U;return true;
}
// True when a RAM byte of [address,address+size) is also a byte of [low,low+span); RAM is the 64 KiB mirror over
// 100000..1fffff, so mirrored addresses alias. Non-RAM bytes never alias the stack.
bool bc_alias(std::uint32_t address,unsigned int size,std::uint32_t low,unsigned int span) {
    for(unsigned int i=0;i<size;++i) {
        const std::uint32_t a=(address+i)&0xffffffU;if(a<0x100000U || a>=0x200000U)continue;
        for(unsigned int j=0;j<span;++j) {
            const std::uint32_t b=(low+j)&0xffffffU;
            if(b>=0x100000U && b<0x200000U && ((a^b)&65535U)==0U)return true;
        }
    }
    return false;
}
// Live re-read for the failure-path X; it must be the value the original e8a50/e8af4 read (no alias with the stack
// written since then, and not the d00046 BYTE whose read is an external event).
bool bc_reread(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t low,unsigned int span,
    std::uint32_t& value) {
    if(bc_alias(address,size,low,span))return am_error(c,"cue wrapper caller X source overlaps the stack");
    if(size==1 && (address&0xffffffU)==0xd00046U)return am_error(c,"cue wrapper caller X source is a device read");
    return am_read(c,address,size,value);
}
// X at 2986 entry for the e8a48 caller (return LONG e8a8a at S = A7 after the A6 pop). The last X producer is the
// e8af4 ADD.W: flags BYTE 4(cue) bit0 -> carry of WORD 2(cue)+WORD 10d3c0, else bit1 -> carry of WORD (cue)+WORD
// 10d3bc, else the e8a5e SUBI.W borrow, which is 0 on the allocation path. Cue = LONG 10de26 (A5=108000 is required
// at e8a48). 10de26 was read before the e8a6a index push, the cue fields after the e8a6c BSR push.
bool bc_caller_x(AnimationMachineContext& c,std::uint32_t& x) {
    const std::uint32_t s=c.s.a[7];std::uint32_t cue=0,flags=0,field=0,addend=0;
    if(!bc_reread(c,BC_CUE,4,s-8U,18,cue) || !bc_reread(c,cue+4U,1,s-8U,16,flags))return false;
    x=0;
    if(flags&1U) {
        if(!bc_reread(c,cue+2U,2,s-8U,16,field) || !bc_reread(c,BC_ADD_Y,2,s-8U,16,addend))return false;
        x=((field&65535U)+(addend&65535U))>>16;
    } else if(flags&2U) {
        if(!bc_reread(c,cue,2,s-8U,16,field) || !bc_reread(c,BC_ADD_X,2,s-8U,16,addend))return false;
        x=((field&65535U)+(addend&65535U))>>16;
    }
    return true;
}
// 298e..299a (one block): MOVEA.L (A7)+,A6; MOVE SR,-(A7); MOVE.B 6a(A6),6a(A0); MOVE (A7)+,SR; RTS.
// The pushed WORD is system BYTE 20 and the CCR left by 28ae (main decision 1, option A):
//   success (2908 ORI #1): X=(D0.W==0) from the 28e6 ADDQ.W, N/Z of the 2902 MOVE.B (BYTE 6a(A0)), V=0, C=1;
//   failure 28ba (D0.W >= WORD 104ca0): N/Z/V of CMP.W D0.W-M, C=0, X of the caller;
//   failure 28c2 (A0 input 0): Z=1, N=V=C=0, X of the caller.
// The caller X is computed only for the e8a48 caller; the popped WORD must equal the pushed one.
bool bc_status(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"cue wrapper requires known carry");
    const bool success=r.carry==AnimationCarrySet;
    if(!am_pop(c,4,value))return false;r.a[6]=value;
    const std::uint32_t d0=r.d[0]&65535U;std::uint32_t ccr=0;
    if(success) {
        if(!am_read(c,am_index(r.a[0],0x6a),1,value))return false;
        ccr=1U|((value&0x80U)?8U:0U)|((value&255U)==0U?4U:0U)|(d0==0U?0x10U:0U);
    } else {
        if(!am_read(c,BC_LIMIT,2,value))return false;const std::uint32_t m=value&65535U;
        if(d0>=m) {
            const std::uint32_t result=(d0-m)&65535U;
            ccr=((result&0x8000U)?8U:0U)|(result==0U?4U:0U)|((((d0^m)&(d0^result))&0x8000U)?2U:0U);
        } else ccr=4U;
        if(!am_read(c,r.a[7],4,value))return false;
        if(value!=BC_CUE_RETURN)return am_error(c,"cue wrapper failure requires known caller X");
        std::uint32_t x=0;if(!bc_caller_x(c,x))return false;if(x)ccr|=0x10U;
    }
    const std::uint32_t pushed=0x2000U|ccr;
    if(!am_push(c,2,pushed))return false;
    if(!am_read(c,am_index(r.a[6],0x6a),1,value) || !am_write(c,am_index(r.a[0],0x6a),1,value&255U))return false;
    if(!am_pop(c,2,value))return false;
    if(value!=pushed)return am_error(c,"cue wrapper status WORD overwritten");
    r.carry=(value&1U)?AnimationCarrySet:AnimationCarryClear;
    return am_return(c);
}
}
// 480bc frame helper U7: frame buffer 4aa88 (10f001 bit7 debug slot loop over 10daf8..10db78 with the 4b784 two-sprite
// submission and bank 1000 resets, the 10dc88 ring cursor with sixteen LSR.W (A0)+ and the 10db88 wrap, the 10db84..87
// BYTE shifts, the 10f001 bit0 / 104cab|104cb1 bit7 override, the 10d744 bit7 double buffer 10d746/10d918 cleared by
// CLR.W 1d0 and MOVEM.L) and cue e8a48 (10de2f allocation request through 2986/28ae, 43e08 position and the e8a0c
// position table, 10de2e stream progression e8ad0, e8af4 cue position, 10f001 bit1 debug cue sprite). Existing
// executors called: cd58 (sprite; the callback LONG must be cd50; waits at cda4 keep the live stack), 28ae (fade card,
// known C), 43e08 (cleanup). A5=108000 is required at e8a48. ROM data e8a0c.. is read through the live bus (physical
// program ROM). The e8ae0 stream walk has no terminator (block budget only). All d16(A5) operands use the live A5.
bool animation_buffer_cue_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // 4aa88: BTST.B #7,10f001.L; BEQ 4aafe.
    case 0x4aa88:return bc_test(c,BC_DEBUG,7,0x4aa94,0x4aafe);
    // MOVE.L A6,-(A7); LEA 10daf8.L,A4; MOVEQ #0,D7.
    case 0x4aa94:if(!am_push(c,4,r.a[6]))return false;r.a[4]=BC_SLOTS;r.d[7]=0;r.pc=0x4aa9e;return true;
    // MOVEA.L (A4),A6; MOVEA.L 4(A4),A0; CMPA.W #0,A6 (whole LONG); BEQ 4aaee.
    case 0x4aa9e:
        if(!am_read(c,r.a[4],4,value))return false;r.a[6]=value;
        if(!am_read(c,am_index(r.a[4],4),4,value))return false;r.a[0]=value;
        r.pc=r.a[6]?0x4aaac:0x4aaee;return true;
    case 0x4aaac:r.pc=r.a[0]?0x4aab4:0x4aaee;return true; // CMPA.W #0,A0; BEQ 4aaee.
    // MOVE.B 6d(A6),D6; ANDI.B #f,D6; CMP.B D6,D7; BNE 4aaee.
    case 0x4aab4:
        if(!am_read(c,am_index(r.a[6],0x6d),1,value))return false;am_byte(r.d[6],value&15U);
        r.pc=((r.d[7]^r.d[6])&255U)?0x4aaee:0x4aac2;return true;
    // MOVE.L A4,-(A7); MOVE.W D7,-(A7); LEA 4(A0),A0; MOVE.L #122b,D7; JSR 4b784(PC).
    case 0x4aac2:
        if(!am_push(c,4,r.a[4]) || !am_push(c,2,r.d[7]&65535U))return false;
        r.a[0]=am_index(r.a[0],4);r.d[7]=0x122b;return am_call(c,0x4b784,0x4aad4);
    // MOVE.W (A7)+,D7 (low WORD only); MOVEA.L (A7)+,A4; bank 1000 reset (-7ff0(A5), 2ffff2, 2ffff0).
    case 0x4aad4:
        if(!am_pop(c,2,value))return false;am_word(r.d[7],value);
        if(!am_pop(c,4,value))return false;r.a[4]=value;
        if(!am_zero_bank(c))return false;r.pc=0x4aaee;return true;
    // ADDQ.W #1,D7; LEA 8(A4),A4; CMPA.L #10db78,A4; BCS 4aa9e.
    case 0x4aaee:am_word(r.d[7],r.d[7]+1U);r.a[4]=am_index(r.a[4],8);r.pc=r.a[4]<BC_SLOTS_END?0x4aa9e:0x4aafc;return true;
    case 0x4aafc:if(!am_pop(c,4,value))return false;r.a[6]=value;r.pc=0x4aafe;return true; // MOVEA.L (A7)+,A6.
    // MOVEQ #0,D7; MOVEA.L 5c88(A5),A0; 16 x LSR.W (A0)+ (WORD read, logical >>1, WORD write, A0+=2, in order);
    // CMPA.L #10dc88,A0; BCS 4ab32.
    case 0x4aafe:
        r.d[7]=0;if(!bc_read(c,0x5c88,4,value))return false;r.a[0]=value;
        for(unsigned int i=0;i<16;++i) {
            if(!am_read(c,r.a[0],2,value) || !am_write(c,r.a[0],2,(value&65535U)>>1))return false;r.a[0]+=2U;
        }
        r.pc=r.a[0]<BC_RING_END?0x4ab32:0x4ab2e;return true;
    case 0x4ab2e:r.a[0]=am_index(r.a[5],0x5b88);r.pc=0x4ab32;return true; // LEA 5b88(A5),A0.
    // MOVE.L A0,5c88(A5); MOVE.B 5b85->5b84; CLR 5b85 (MOVE.B #0); MOVE.B 5b87->5b86; MOVE.B #0,5b87;
    // BTST.B #0,10f001.L; BEQ 4ab74.
    case 0x4ab32:
        if(!bc_write(c,0x5c88,4,r.a[0]) || !bc_copy(c,0x5b85,0x5b84) || !bc_write(c,0x5b85,1,0) ||
           !bc_copy(c,0x5b87,0x5b86) || !bc_write(c,0x5b87,1,0))return false;
        return bc_test(c,BC_DEBUG,0,0x4ab5a,0x4ab74);
    // MOVE.B 104cab.L,D0; OR.B 104cb1.L,D0; ANDI.B #80,D0; BEQ 4ab74.
    case 0x4ab5a:
        if(!am_read(c,BC_INPUT1,1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,BC_INPUT2,1,value))return false;am_byte(r.d[0],(r.d[0]|value)&0x80U);
        r.pc=(r.d[0]&255U)?0x4ab6e:0x4ab74;return true;
    case 0x4ab6e:if(!bc_write(c,0x5b84,1,0xff))return false;r.pc=0x4ab74;return true; // MOVE.B #ff,5b84(A5).
    // LEA 5746(A5),A4; LEA 5918(A5),A3; BCHG.B #7,5744(A5) (Z = previous bit7 clear); BNE 4ab88.
    case 0x4ab74:
        r.a[4]=am_index(r.a[5],0x5746);r.a[3]=am_index(r.a[5],0x5918);
        if(!bc_read(c,0x5744,1,value) || !bc_write(c,0x5744,1,(value^0x80U)&255U))return false;
        r.pc=(value&0x80U)?0x4ab88:0x4ab86;return true;
    case 0x4ab86:value=r.a[3];r.a[3]=r.a[4];r.a[4]=value;r.pc=0x4ab88;return true; // EXG A3,A4.
    // MOVEQ #-1,D1; CLR.W 1d0(A4); MOVEQ #0,D0..D7; LEA d0(A4),A4; 6 x MOVEM.L D0-D7,-(A4); MOVEM.L D0-D3,-(A4); RTS.
    // Predecrement MOVEM stores the highest register first; every value is 0.
    case 0x4ab88:
        r.d[1]=0xffffffffU;if(!am_write(c,am_index(r.a[4],0x1d0),2,0))return false;
        for(unsigned int i=0;i<8;++i)r.d[i]=0;
        r.a[4]=am_index(r.a[4],0xd0);
        for(unsigned int k=0;k<7;++k) {
            const unsigned int count=k<6?8U:4U;
            for(unsigned int i=0;i<count;++i) {r.a[4]-=4U;if(!am_write(c,r.a[4],4,0))return false;}
        }
        return am_return(c);

    // 4b784 (slot object A6, A0 = record+4, D7=122b): MOVE.L #ffff0000,D1; BTST.B #2,15(A6); BEQ 4b798.
    case 0x4b784:r.d[1]=0xffff0000U;return bc_test(c,am_index(r.a[6],0x15),2,0x4b794,0x4b798);
    case 0x4b794:am_word(r.d[1],4);r.pc=0x4b798;return true; // MOVE.W #4,D1.
    // MOVE.L (A0)+,D0; BTST.B #0,15(A6); BEQ 4b7ae.
    case 0x4b798:
        if(!am_read(c,r.a[0],4,value))return false;r.d[0]=value;r.a[0]+=4U;
        return bc_test(c,am_index(r.a[6],0x15),0,0x4b7a4,0x4b7ae);
    case 0x4b7a4:am_swap(r.d[0]);am_word(r.d[0],0U-r.d[0]);am_swap(r.d[0]);r.d[1]|=1U;r.pc=0x4b7ae;return true; // SWAP; NEG.W; SWAP; BSET #0,D1.
    case 0x4b7ae:return bc_test(c,am_index(r.a[6],0x15),1,0x4b7b8,0x4b7be); // BTST.B #1,15(A6); BEQ 4b7be.
    case 0x4b7b8:am_word(r.d[0],0U-r.d[0]);r.d[1]|=2U;r.pc=0x4b7be;return true; // NEG.W D0; BSET #1,D1.
    // SWAP D0; ADD.W 42(A6),D0; SWAP D0; ADD.W 46(A6),D0; MOVE.L D0/D1/D7/A0,-(A7); MOVEQ #-1,D5; JSR cd58.L.
    case 0x4b7be:
        am_swap(r.d[0]);if(!am_read(c,am_index(r.a[6],0x42),2,value))return false;am_word(r.d[0],r.d[0]+value);
        am_swap(r.d[0]);if(!am_read(c,am_index(r.a[6],0x46),2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!am_push(c,4,r.d[0]) || !am_push(c,4,r.d[1]) || !am_push(c,4,r.d[7]) || !am_push(c,4,r.a[0]))return false;
        r.d[5]=0xffffffffU;return am_call(c,0xcd58,0x4b7da);
    // MOVEA.L (A7)+,A0; MOVE.L (A7)+,D7/D1/D0; MOVE.W (A0)+,D2; MOVE.W (A0)+,D3 (live after any wait); EORI.W #3,D1;
    // BTST.B #0,15(A6); BEQ 4b7f6.
    case 0x4b7da:
        if(!am_pop(c,4,value))return false;r.a[0]=value;
        if(!am_pop(c,4,value))return false;r.d[7]=value;
        if(!am_pop(c,4,value))return false;r.d[1]=value;
        if(!am_pop(c,4,value))return false;r.d[0]=value;
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[2],value);r.a[0]+=2U;
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[3],value);r.a[0]+=2U;
        am_word(r.d[1],r.d[1]^3U);return bc_test(c,am_index(r.a[6],0x15),0,0x4b7f4,0x4b7f6);
    case 0x4b7f4:am_word(r.d[2],0U-r.d[2]);r.pc=0x4b7f6;return true; // NEG.W D2.
    case 0x4b7f6:return bc_test(c,am_index(r.a[6],0x15),1,0x4b800,0x4b802); // BTST.B #1,15(A6); BEQ 4b802.
    case 0x4b800:am_word(r.d[3],0U-r.d[3]);r.pc=0x4b802;return true; // NEG.W D3.
    // SWAP D0; ADD.W D2,D0; SWAP D0; ADD.W D3,D0; MOVE.L A0,-(A7); MOVEQ #-1,D5; JSR cd58.L.
    case 0x4b802:
        am_swap(r.d[0]);am_word(r.d[0],r.d[0]+r.d[2]);am_swap(r.d[0]);am_word(r.d[0],r.d[0]+r.d[3]);
        if(!am_push(c,4,r.a[0]))return false;r.d[5]=0xffffffffU;return am_call(c,0xcd58,0x4b814);
    // MOVEA.L (A7)+,A0; bank 1000 reset; RTS.
    case 0x4b814:
        if(!am_pop(c,4,value))return false;r.a[0]=value;if(!am_zero_bank(c))return false;return am_return(c);

    // e8a48: TST.B 5e2f(A5); BEQ e8aae (A5=108000 required: the 298e caller-X rule re-reads absolute addresses).
    case 0xe8a48:
        if(r.a[5]!=0x108000U)return am_error(c,"cue requires A5 108000");
        if(!bc_read(c,0x5e2f,1,value))return false;r.pc=(value&255U)?0xe8a50:0xe8aae;return true;
    // CLR.B 5e2f(A5); MOVEA.L 5e26(A5),A0; MOVEQ #0,D0; MOVE.B 7(A0),D0; SUBI.W #1c,D0; CMPI.B #20,D0; BCC e8aae.
    case 0xe8a50:
        if(!bc_write(c,0x5e2f,1,0) || !bc_read(c,0x5e26,4,value))return false;r.a[0]=value;
        r.d[0]=0;if(!am_read(c,am_index(r.a[0],7),1,value))return false;am_byte(r.d[0],value);
        am_word(r.d[0],r.d[0]-0x1cU);r.pc=(r.d[0]&255U)>=0x20U?0xe8aae:0xe8a6a;return true;
    case 0xe8a6a:if(!am_push(c,2,r.d[0]&65535U))return false;return am_call(c,0xe8af4,0xe8a70); // MOVE.W D0,-(A7); BSR e8af4.
    // MOVE.W D0,-(A7); MOVE.W D1,-(A7); MOVEA.L #d5f16,A0; MOVE.W #0,D0; MOVEA.L #100bf4,A1; JSR 2986.L.
    case 0xe8a70:
        if(!am_push(c,2,r.d[0]&65535U) || !am_push(c,2,r.d[1]&65535U))return false;
        r.a[0]=BC_CUE_CALLBACK;am_word(r.d[0],0);r.a[1]=BC_PARENT;return am_call(c,0x2986,BC_CUE_RETURN);
    // LEA 2e(A0),A0; LEA 538e(A5),A1; MOVE.W (A7)+,D1; MOVE.W (A7)+,D0; JSR 43e08.L.
    case 0xe8a8a:
        r.a[0]=am_index(r.a[0],0x2e);r.a[1]=am_index(r.a[5],0x538e);
        if(!am_pop(c,2,value))return false;am_word(r.d[1],value);
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        return am_call(c,0x43e08,0xe8a9c);
    // LEA 48(A0),A0; MOVE.W (A7)+,D0; LEA e8a0c(PC),A1; LSL.W #2,D0; ADDA.W D0,A1; 2 x MOVE.W (A1)+,(A0)+.
    case 0xe8a9c:
        r.a[0]=am_index(r.a[0],0x48);if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        r.a[1]=BC_POSITION_TABLE;am_word(r.d[0],r.d[0]<<2);r.a[1]=am_index(r.a[1],r.d[0]);
        if(!bc_move_word(c) || !bc_move_word(c))return false;r.pc=0xe8aae;return true;
    case 0xe8aae:if(!bc_read(c,0x5e2e,1,value))return false;r.pc=(value&255U)?0xe8ac2:0xe8ab6;return true; // TST.B 5e2e(A5); BNE e8ac2.
    case 0xe8ab6:return am_call(c,0xe8ad0,0xe8aba); // BSR e8ad0.
    // LEA 4(A0),A1; MOVE.L A1,5e26(A5) (a null e8ad0 result stores 4).
    case 0xe8aba:r.a[1]=am_index(r.a[0],4);if(!bc_write(c,0x5e26,4,r.a[1]))return false;r.pc=0xe8ac2;return true;
    case 0xe8ac2:return bc_test(c,BC_DEBUG,1,0xe8b18,0xe8ace); // BTST.B #1,10f001.L; BNE e8b18.
    case 0xe8ace:case 0xe8af2:case 0xe8b16:case 0xe8b58:return am_return(c);
    // e8ad0: MOVEA.L 5e2a(A5),A0; CMPA.W #0,A0; BEQ e8af2.
    case 0xe8ad0:if(!bc_read(c,0x5e2a,4,value))return false;r.a[0]=value;r.pc=value?0xe8adc:0xe8af2;return true;
    case 0xe8adc:if(!bc_read(c,0x5418,2,value))return false;am_word(r.d[0],value);r.pc=0xe8ae0;return true; // MOVE.W 5418(A5),D0.
    // CMP.W c(A0),D0; BCS e8aee (no terminator: block budget only).
    case 0xe8ae0:
        if(!am_read(c,am_index(r.a[0],0xc),2,value))return false;
        r.pc=(r.d[0]&65535U)<(value&65535U)?0xe8aee:0xe8ae8;return true;
    case 0xe8ae8:r.a[0]=am_index(r.a[0],0xc);r.pc=0xe8ae0;return true; // ADDA.W #c,A0; BRA e8ae0.
    case 0xe8aee:if(!bc_write(c,0x5e2a,4,r.a[0]))return false;r.pc=0xe8af2;return true; // MOVE.L A0,5e2a(A5).
    // e8af4: MOVE.W (A0),D0; MOVE.W 2(A0),D1; BTST.B #1,4(A0); BEQ e8b08.
    case 0xe8af4:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,am_index(r.a[0],2),2,value))return false;am_word(r.d[1],value);
        return bc_test(c,am_index(r.a[0],4),1,0xe8b04,0xe8b08);
    case 0xe8b04:if(!bc_read(c,0x53bc,2,value))return false;am_word(r.d[0],r.d[0]+value);r.pc=0xe8b08;return true; // ADD.W 53bc(A5),D0.
    case 0xe8b08:return bc_test(c,am_index(r.a[0],4),0,0xe8b12,0xe8b16); // BTST.B #0,4(A0); BEQ e8b16.
    case 0xe8b12:if(!bc_read(c,0x53c0,2,value))return false;am_word(r.d[1],r.d[1]+value);r.pc=0xe8b16;return true; // ADD.W 53c0(A5),D1.
    // e8b18: LEA 10d38e.L,A1; MOVEA.L 5e26(A5),A0; CMPA.W #0,A0; BEQ e8b58.
    case 0xe8b18:r.a[1]=BC_DEBUG_POSITION;if(!bc_read(c,0x5e26,4,value))return false;r.a[0]=value;r.pc=value?0xe8b2a:0xe8b58;return true;
    case 0xe8b2a:return am_call(c,0xe8af4,0xe8b2e); // JSR e8af4(PC).
    // ADD.W 53a2(A5),D0; ADD.W 53a6(A5),D1; SWAP D0; MOVE.W D1,D0; MOVEQ #-1,D1; CLR.W D1; CMPI.W #1e0,D0; BCS e8b4a.
    case 0xe8b2e:
        if(!bc_read(c,0x53a2,2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!bc_read(c,0x53a6,2,value))return false;am_word(r.d[1],r.d[1]+value);
        am_swap(r.d[0]);am_word(r.d[0],r.d[1]);r.d[1]=0xffff0000U;
        r.pc=(r.d[0]&65535U)<0x1e0U?0xe8b4a:0xe8b46;return true;
    case 0xe8b46:r.d[1]|=2U;r.pc=0xe8b4a;return true; // BSET #1,D1.
    case 0xe8b4a:r.d[5]=0xffffffffU;r.d[7]=0xba2b;return am_call(c,0xcd58,0xe8b58); // MOVEQ #-1,D5; MOVE.L #ba2b,D7; JSR cd58.L.

    // 2986: MOVE.L A6,-(A7); MOVEA.L A1,A6; BSR 28ae.
    case 0x2986:if(!am_push(c,4,r.a[6]))return false;r.a[6]=r.a[1];return am_call(c,0x28ae,0x298e);
    case 0x298e:return bc_status(c);
    default:return am_error(c,"unsupported animation buffer cue PC");
    }
}
}
