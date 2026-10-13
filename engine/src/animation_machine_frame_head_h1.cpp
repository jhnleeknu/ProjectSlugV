#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Fixed ROM BYTE table read by b98 (TST.B (A1,D6.W) with A1 = b58; live bus).
const std::uint32_t FH1_TABLE_B58=0xb58;
// Constant A0 / A1 ring limits of the flush loops (CMPA.L #imm; fixed, not A5-relative).
const std::uint32_t FH1_RING_END=0x108d34;
const std::uint32_t FH1_RING_START=0x108b34;
std::uint32_t fh1_b(std::uint32_t value) {return value&255U;}
std::uint32_t fh1_w(std::uint32_t value) {return value&65535U;}
// d16(An) and d8(An,Dn.W): base + sign-extended displacement (+ sign-extended WORD index), modulo 2^32.
std::uint32_t fh1_at(std::uint32_t base,std::uint32_t displacement) {return am_index(base,displacement);}
std::uint32_t fh1_ix(std::uint32_t base,std::uint32_t displacement,std::uint32_t index) {
    return am_index(base,displacement)+am_extend_word(index&65535U);
}
// MOVE.W/MOVE.L #imm,3c0000/3c0004 (absolute): one original write is one observed video port event.
void fh1_port(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t value) {
    VideoPortWrite port;port.address=address;port.size=static_cast<std::uint8_t>(size);port.value=value;c.ports.push_back(port);
}
// MOVE.W 3c0006.l,D0 (raster, D3): the declared external-read queue is not representable through the current
// public API (contract main decision 2), so the queue is always empty: checked error, state preserved.
bool fh1_raster(AnimationMachineContext& c) {return am_error(c,"animation machine external read queue empty");}
// BSET.B / BCLR.B #bit,address (read, then write).
bool fh1_bit(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    const std::uint32_t mask=1U<<bit;return am_write(c,address,1,set?fh1_b(value|mask):fh1_b(value&~mask));
}
// ADDQ.B / SUBQ.B #1,address (read, then write; 8-bit wrap).
bool fh1_step_byte(AnimationMachineContext& c,std::uint32_t address,bool up) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;return am_write(c,address,1,fh1_b(up?value+1U:value-1U));
}
// MOVE.W src,dst (memory to memory).
bool fh1_copy_word(AnimationMachineContext& c,std::uint32_t source,std::uint32_t target) {
    std::uint32_t value=0;return am_read(c,source,2,value) && am_write(c,target,2,value);
}
// CMPI.W #ffff,4(A2); SNE.B D7; ANDI.W #4,D7; OR.B D1,D7; ADD.W D7,D7; ADD.W D7,D7; LEA table,A3; JSR (A3,D7.W).
// The target is live (contract main decision 5): the table owner (H4 / H8) routes it.
bool fh1_writer(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!am_read(c,fh1_at(r.a[2],4),2,value))return false;
    am_byte(r.d[7],fh1_w(value)!=0xffffU?0xffU:0U);am_word(r.d[7],r.d[7]&4U);am_byte(r.d[7],r.d[7]|fh1_b(r.d[1]));
    am_word(r.d[7],r.d[7]*2U);am_word(r.d[7],r.d[7]*2U);r.a[3]=table;
    return am_call(c,r.a[3]+am_extend_word(fh1_w(r.d[7])),return_pc);
}
// MOVE.W 6(A2),D1; LEA d3e(A5),A4; BCLR.B #2,D1; BEQ.W zero_pc (bit was 0) else set_pc (LEA d46(A5),A4).
void fh1_entry_kind(AnimationMachineContext& c,std::uint32_t value,std::uint32_t zero_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;am_word(r.d[1],value);r.a[4]=r.a[5]+0xd3eU;
    const bool was_set=(r.d[1]&4U)!=0;r.d[1]&=~4U;r.pc=was_set?set_pc:zero_pc;
}
// MOVEA.L (A7)+,A6; MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.l; MOVE.W #0,2ffff0.l.
bool fh1_flush_end(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.a[6]=value;return am_zero_bank(c);
}
// One 1879c sub-step: X = bit 0 of D2.B; LSR.B #1,D2; SUBX.W D3,Dn (D3 = 0: Dn.W -= X).
void fh1_subx(AnimationMachineState& r,std::uint32_t& target) {
    const std::uint32_t x=r.d[2]&1U;am_byte(r.d[2],fh1_b(r.d[2])>>1);
    am_word(target,target-am_extend_word(fh1_w(r.d[3]))-x);
}
}
// F5 frame head H1 (120 block starts): the head body e4a / e74 .. 1000 (first frame init 903a / 9546, sound word flush 3c08,
// sprite flush 16bba with the 166bc radix sort and the D5 wait 16bd0, background snapshot 1ae56 / 1879c, vblank wait ef2 (D2),
// BIOS mode / player mod b68, pause palette copies 8bc8 / 8be0, 3db2, frame parity 43dbc). Boundaries (never executed here):
// 31d6 / 9136 (H2), 5728 (H3), the live writer table targets of 16c48 / 16cc8 (H8 / H4), TRAP #15 at fee (D8), the controller
// callback LONG (1008e4) entered by the dispatcher (D1). The raster reads at ea4 / efc are the empty external-read queue error
// (main decision 2). The aux callback path f3c / f44 / f4c / f52 is the D8 guard. No carry consumer, no known-carry producer.
bool animation_frame_head_h1_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    // ---- b68 BIOS mode copy and player mod scan.
    case 0xb68:
        if(!am_read(c,0x10fdaf,1,value) || !am_write(c,0x100012,1,value))return false;
        r.a[0]=0x10fdb6;r.a[1]=FH1_TABLE_B58;r.d[7]=0;if(!am_write(c,0x10f007,1,r.d[7]&255U))return false;
        am_word(r.d[0],3);r.pc=0xb88;return true;
    case 0xb88: {
        // BCLR.B D0,10f006.l (bit D0 mod 8); BEQ.W b98 (the bit was 0).
        const unsigned int bit=r.d[0]&7U;if(!am_read(c,0x10f006,1,value))return false;const bool was_set=((value>>bit)&1U)!=0;
        if(!am_write(c,0x10f006,1,fh1_b(value&~(1U<<bit))))return false;r.pc=was_set?0xb92:0xb98;return true;
    }
    case 0xb92:if(!am_write(c,fh1_ix(r.a[0],0,r.d[0]),1,1))return false;r.pc=0xb98;return true; // MOVE.B #1,(A0,D0.W).
    case 0xb98:
        // MOVE.W #4,D6; ADD.B (A0,D0.W),D6; TST.B (A1,D6.W); BEQ.W baa.
        am_word(r.d[6],4);if(!am_read(c,fh1_ix(r.a[0],0,r.d[0]),1,value))return false;am_byte(r.d[6],r.d[6]+value);
        if(!am_read(c,fh1_ix(r.a[1],0,r.d[6]),1,value))return false;r.pc=fh1_b(value)==0U?0xbaa:0xba8;return true;
    case 0xba8:r.d[7]|=1U<<(r.d[0]&31U);r.pc=0xbaa;return true;                 // BSET.B D0,D7 (bit D0 mod 32).
    case 0xbaa: {
        // SUBQ.W #1,D0; BCC.B b88 (no borrow: the old D0.W was not 0).
        const bool borrow=fh1_w(r.d[0])==0U;am_word(r.d[0],r.d[0]-1U);r.pc=borrow?0xbae:0xb88;return true;
    }
    case 0xbae:if(!am_write(c,0x10f007,1,fh1_b(r.d[7])))return false;return am_return(c);
    // ---- head body.
    case 0xe4a:return am_call(c,0xe7bf4,0xe50);                                    // JSR e7bf4.l.
    case 0xe50:
        // MOVEQ #0,D0; MOVE.W D0,-7ff2(A5); MOVE.W D0,7e(A6); MOVE.B #1,84(A6); MOVE.L #0,76(A6); JSR 903a.l.
        r.d[0]=0;if(!am_write(c,fh1_at(r.a[5],0x800e),2,0) || !am_write(c,fh1_at(r.a[6],0x7e),2,0) ||
            !am_write(c,fh1_at(r.a[6],0x84),1,1) || !am_write(c,fh1_at(r.a[6],0x76),4,0))return false;
        return am_call(c,0x903a,0xe6e);
    case 0xe6e:if(!am_write(c,r.a[6],4,0xe74))return false;r.pc=0xe74;return true; // MOVE.L #e74,(A6).
    case 0xe74:fh1_port(c,0x3c0004,2,0);fh1_port(c,0x3c0000,4,0x82000000U);return am_call(c,0x3c08,0xe8c);
    case 0xe8c:return am_call(c,0x16bba,0xe92);
    case 0xe92:return am_call(c,0x1ae56,0xe98);
    case 0xe98:if(!fh1_bit(c,fh1_at(r.a[5],0x801b),7,false))return false;return am_call(c,0x5728,0xea4);
    case 0xea4:if(!fh1_bit(c,fh1_at(r.a[5],0x801b),7,true))return false;return fh1_raster(c);
    case 0xeba:r.d[0]=0;r.pc=0xebc;return true;                                    // MOVEQ #0,D0.
    case 0xebc:
        // SUB.B -7fe8(A5),D0; MOVE.B D0,-7fe8(A5).
        if(!am_read(c,fh1_at(r.a[5],0x8018),1,value))return false;am_byte(r.d[0],r.d[0]-value);
        if(!am_write(c,fh1_at(r.a[5],0x8018),1,fh1_b(r.d[0])))return false;r.pc=0xec4;return true;
    case 0xec4:if(!am_read(c,0x10f000,1,value))return false;r.pc=(value&1U)==0U?0xef2:0xed0;return true;
    case 0xed0:if(!am_read(c,fh1_at(r.a[6],0x84),1,value))return false;r.pc=fh1_b(value)==0U?0xef2:0xeda;return true;
    case 0xeda:am_word(r.d[0],0x7066);r.a[0]=0xd56;r.a[1]=0x3650;r.a[2]=0xdf0;return am_call(c,0x3a70,0xef2);
    case 0xef2:
        // MOVE.B -7fea(A5),D0; CMP.B -7fe9(A5),D0; BCS.B ef2. While BYTE 100016 < BYTE 100017 (unsigned) the block waits before its
        // first instruction (main decision 3, D2): nothing changes; the declared release writes BYTE 100016 := BYTE 100017.
        if(!am_read(c,fh1_at(r.a[5],0x8016),1,value) || !am_read(c,fh1_at(r.a[5],0x8017),1,other))return false;
        if(fh1_b(value)<fh1_b(other)) {c.waiting=true;return true;}
        am_byte(r.d[0],value);r.pc=0xefc;return true;
    case 0xefc:return fh1_raster(c);
    case 0xf0c:r.d[0]=0;r.pc=0xf0e;return true;                                    // MOVEQ #0,D0.
    case 0xf0e:if(!am_write(c,fh1_at(r.a[5],0x8018),1,fh1_b(r.d[0])))return false;r.pc=0xf12;return true;
    case 0xf12:
        // MOVE.B -7fea(A5),-7fe6(A5); MOVE.B #0,-7fea(A5); MOVE.W #0,-335e(A5); JSR 31d6.l.
        if(!am_read(c,fh1_at(r.a[5],0x8016),1,value) || !am_write(c,fh1_at(r.a[5],0x801a),1,value) ||
            !am_write(c,fh1_at(r.a[5],0x8016),1,0) || !am_write(c,fh1_at(r.a[5],0xcca2),2,0))return false;
        return am_call(c,0x31d6,0xf2a);
    case 0xf2a:return am_call(c,0xb68,0xf30);
    case 0xf30:
        // MOVEA.L 76(A6),A0; CMPA.W #0,A0 (32-bit compare with sign-extended 0); BEQ.W f54.
        if(!am_read(c,fh1_at(r.a[6],0x76),4,value))return false;r.a[0]=value;r.pc=value==0U?0xf54:0xf3c;return true;
    // Aux callback path (100896 != 0): D8 guard, never executed.
    case 0xf3c:case 0xf44:case 0xf4c:case 0xf52:return am_error(c,"unsupported animation frame head aux callback");
    case 0xf54:return am_call(c,0x9136,0xf5a);
    case 0xf5a:
        // MOVE.B 84(A6),D1; MOVE.B D0,84(A6); BNE.W fbc.
        if(!am_read(c,fh1_at(r.a[6],0x84),1,value))return false;am_byte(r.d[1],value);
        if(!am_write(c,fh1_at(r.a[6],0x84),1,fh1_b(r.d[0])))return false;r.pc=fh1_b(r.d[0])!=0U?0xfbc:0xf66;return true;
    case 0xf66:r.pc=fh1_b(r.d[1])==0U?0xf84:0xf6e;return true;                    // CMPI.B #0,D1; BEQ.W f84.
    case 0xf6e:if(!am_push(c,2,fh1_w(r.d[1])))return false;return am_call(c,0x3db2,0xf76);
    case 0xf76:
        if(!am_write(c,fh1_at(r.a[6],0x82),2,fh1_w(r.d[0])))return false;r.d[0]=0;return am_call(c,0x3d7e,0xf82);
    case 0xf82:if(!am_pop(c,2,value))return false;am_word(r.d[1],value);r.pc=0xf84;return true;
    case 0xf84:r.pc=fh1_b(r.d[1])!=1U?0xfae:0xf8c;return true;                    // CMPI.B #1,D1; BNE.W fae.
    case 0xf8c:r.d[0]=0;return am_call(c,0x8bbc,0xf94);
    case 0xf94:return am_call(c,0x8bc8,0xf9a);
    case 0xf9a:
        if(!am_write(c,fh1_at(r.a[6],0x80),1,0xff))return false;
        r.d[0]=0xfffffffcU;r.d[1]=0xfffffffcU;r.d[2]=0xfffffffcU;r.d[3]=4;return am_call(c,0x8c16,0xfae);
    case 0xfae:return am_call(c,0x5728,0xfb4);
    case 0xfb4:r.pc=0xec4;return true;                                             // BRA.W ec4 (head pause loop).
    case 0xfbc:r.pc=fh1_b(r.d[1])!=0U?0xfe2:0xfc4;return true;                    // CMPI.B #0,D1; BNE.W fe2.
    case 0xfc4:if(!am_read(c,fh1_at(r.a[6],0x82),2,value))return false;am_word(r.d[0],value);return am_call(c,0x3d7e,0xfce);
    case 0xfce:if(!am_read(c,fh1_at(r.a[6],0x80),1,value))return false;r.pc=fh1_b(value)==0U?0xfe2:0xfd6;return true;
    case 0xfd6:return am_call(c,0x8be0,0xfdc);
    case 0xfdc:if(!am_write(c,fh1_at(r.a[6],0x80),1,0))return false;r.pc=0xfe2;return true;
    case 0xfe2:
        // MOVE.W 7e(A6),D0; CMP.W -7ff2(A5),D0; BEQ.W ff0 (else the fee TRAP #15 boundary, D8).
        if(!am_read(c,fh1_at(r.a[6],0x7e),2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,fh1_at(r.a[5],0x800e),2,value))return false;r.pc=fh1_w(r.d[0])==fh1_w(value)?0xff0:0xfee;return true;
    case 0xff0:
        am_word(r.d[0],r.d[0]+1U);
        if(!am_write(c,fh1_at(r.a[5],0x800e),2,fh1_w(r.d[0])) || !am_write(c,fh1_at(r.a[6],0x7e),2,fh1_w(r.d[0])))return false;
        return am_call(c,0x43dbc,0x1000);
    case 0x1000:return am_return(c);
    // ---- 3c08 sound word flush (ring 104d82, cursors -3276 / -3274).
    case 0x3c08:if(!am_read(c,fh1_at(r.a[5],0xcd8a),2,value))return false;am_word(r.d[1],value);r.pc=0x3c0c;return true;
    case 0x3c0c:if(!am_read(c,fh1_at(r.a[5],0xcd8c),2,value))return false;r.pc=fh1_w(r.d[1])==fh1_w(value)?0x3c3c:0x3c14;return true;
    case 0x3c14:
        // LEA -327e(A5),A0; LEA (A0,D1.W),A0; TST.W (A0); BEQ.W 3c34.
        r.a[0]=fh1_ix(r.a[5],0xcd82,r.d[1]);if(!am_read(c,r.a[0],2,value))return false;r.pc=fh1_w(value)==0U?0x3c34:0x3c22;return true;
    case 0x3c22:
        // MOVE.W D1,-(A7); MOVE.B (A0)+,D0; MOVE.B (A0)+,-(A7) (BYTE stack -2); BSR.W 3ac8.
        if(!am_push(c,2,fh1_w(r.d[1])) || !am_read(c,r.a[0],1,value))return false;am_byte(r.d[0],value);r.a[0]+=1U;
        if(!am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;if(!am_push(c,1,value))return false;return am_call(c,0x3ac8,0x3c2c);
    case 0x3c2c:if(!am_pop(c,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x3ac8,0x3c32);
    case 0x3c32:if(!am_pop(c,2,value))return false;am_word(r.d[1],value);r.pc=0x3c34;return true;
    case 0x3c34:am_word(r.d[1],r.d[1]+2U);am_word(r.d[1],r.d[1]&6U);r.pc=0x3c0c;return true; // ADDQ.W #2,D1; ANDI.W #6,D1; BRA.B 3c0c.
    case 0x3c3c:if(!am_write(c,fh1_at(r.a[5],0xcd8a),2,fh1_w(r.d[1])))return false;return am_return(c);
    // ---- 3db2.
    case 0x3db2:r.d[0]=0;if(!am_read(c,0x104d91,1,value))return false;r.pc=(value&8U)==0U?0x3dc2:0x3dc0;return true;
    case 0x3dc0:return am_return(c);
    case 0x3dc2:if(!am_read(c,0x104d90,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]+1U);return am_return(c);
    // ---- 8bc8 / 8be0 palette copies (20 bytes, one byte per 8bd8 block).
    case 0x8bc8:r.a[1]=0x107dc2;r.a[0]=0x107dd6;r.pc=0x8bd4;return true;
    case 0x8bd4:am_word(r.d[7],0x14);r.pc=0x8bd8;return true;
    case 0x8bd8:
        // MOVE.B (A1)+,(A0)+; SUBQ.W #1,D7; BNE.B 8bd8.
        if(!am_read(c,r.a[1],1,value))return false;r.a[1]+=1U;if(!am_write(c,r.a[0],1,value))return false;r.a[0]+=1U;
        am_word(r.d[7],r.d[7]-1U);r.pc=fh1_w(r.d[7])!=0U?0x8bd8:0x8bde;return true;
    case 0x8bde:return am_return(c);
    case 0x8be0:
        if(!am_read(c,fh1_at(r.a[5],0xfdc2),1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,fh1_at(r.a[5],0xfdc4),1,value))return false;am_byte(r.d[1],value);
        if(!am_read(c,fh1_at(r.a[5],0xfdc6),1,value))return false;am_byte(r.d[2],value);
        r.a[0]=0x107dc2;r.a[1]=0x107dd6;return am_call(c,0x8bd4,0x8bfa);
    case 0x8bfa:if(!am_read(c,fh1_at(r.a[5],0xfdd4),1,value))return false;r.pc=fh1_b(value)!=0U?0x8c14:0x8c02;return true;
    case 0x8c02:
        if(!am_write(c,fh1_at(r.a[5],0xfdd4),1,1) || !am_write(c,fh1_at(r.a[5],0xfdc2),1,fh1_b(r.d[0])) ||
            !am_write(c,fh1_at(r.a[5],0xfdc4),1,fh1_b(r.d[1])) || !am_write(c,fh1_at(r.a[5],0xfdc6),1,fh1_b(r.d[2])))return false;
        r.pc=0x8c14;return true;
    case 0x8c14:return am_return(c);
    // ---- 903a / 9546 first frame init.
    case 0x903a:return am_call(c,0x9056,0x903e);
    case 0x903e:
        if(!am_write(c,0x107dee,1,0) || !am_write(c,0x107df0,1,0) || !am_write(c,0x107df1,1,0))return false;
        return am_call(c,0x9546,0x9054);
    case 0x9054:return am_return(c);
    case 0x9546:
        if(!am_write(c,fh1_at(r.a[5],0xfdfe),1,0))return false;am_word(r.d[7],7);r.d[0]=0;r.a[0]=fh1_at(r.a[5],0xfdff);
        r.pc=0x9556;return true;
    case 0x9556:
        // MOVE.B D0,(A0)+; DBRA D7,9556.
        if(!am_write(c,r.a[0],1,fh1_b(r.d[0])))return false;r.a[0]+=1U;am_word(r.d[7],r.d[7]-1U);
        r.pc=fh1_w(r.d[7])!=0xffffU?0x9556:0x955c;return true;
    case 0x955c:return am_return(c);
    // ---- 166bc sprite radix sort (two BYTE keys counted in one WORD table at A5+d4e..f4e).
    case 0x166bc:
        if(!am_read(c,r.a[5]+0xd3aU,2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,r.a[5]+0xd36U,2,value))return false;am_word(r.d[0],r.d[0]-value);r.pc=fh1_w(r.d[0])!=0U?0x166ca:0x166c8;return true;
    case 0x166c8:return am_return(c);
    case 0x166ca:
        // LEA f4e(A5),A4; MOVEQ #0,D0..D7; MOVEM.L D0-D7,-(A4) x16 (128 zero LONGs, highest first); MOVE.W #1fe,D5;
        // LEA -cc(A5),A0; LEA b34(A5),A1; MOVE.W d36(A5),D6; MOVE.W d3a(A5),D7.
        r.a[4]=r.a[5]+0xf4eU;for(unsigned int i=0;i<8;++i)r.d[i]=0;
        for(unsigned int i=0;i<128;++i) {r.a[4]-=4U;if(!am_write(c,r.a[4],4,0))return false;}
        am_word(r.d[5],0x1fe);r.a[0]=fh1_at(r.a[5],0xff34);r.a[1]=r.a[5]+0xb34U;
        if(!am_read(c,r.a[5]+0xd36U,2,value))return false;am_word(r.d[6],value);
        if(!am_read(c,r.a[5]+0xd3aU,2,value))return false;am_word(r.d[7],value);r.pc=0x16732;return true;
    case 0x16732:
        r.d[0]=0;r.d[1]=0;if(!am_read(c,fh1_ix(r.a[1],0,r.d[6]),2,value))return false;am_word(r.d[2],value);
        if(!am_read(c,fh1_ix(r.a[0],0,r.d[2]),1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,fh1_ix(r.a[0],1,r.d[2]),1,value))return false;am_byte(r.d[1],value);
        am_word(r.d[0],r.d[0]*2U);am_word(r.d[1],r.d[1]*2U);
        if(!fh1_step_byte(c,fh1_ix(r.a[4],0,r.d[0]),true) || !fh1_step_byte(c,fh1_ix(r.a[4],1,r.d[1]),true))return false;
        am_word(r.d[6],r.d[6]+2U);am_word(r.d[6],r.d[6]&r.d[5]);r.pc=fh1_w(r.d[6])!=fh1_w(r.d[7])?0x16732:0x16756;return true;
    case 0x16756:
        // MOVEA.L A4,A2; MOVE.W (A2)+,D7; (ADD.W (A2),D7; MOVE.W D7,(A2)+) x255; ANDI.W #ff,D7; LEA f4e(A5),A2;
        // MOVE.W d3a(A5),D6; MOVE.W D7,D4; SUBQ.W #1,D4.
        r.a[2]=r.a[4];if(!am_read(c,r.a[2],2,value))return false;am_word(r.d[7],value);r.a[2]+=2U;
        for(unsigned int i=0;i<255;++i) {
            if(!am_read(c,r.a[2],2,value))return false;am_word(r.d[7],r.d[7]+value);
            if(!am_write(c,r.a[2],2,fh1_w(r.d[7])))return false;r.a[2]+=2U;
        }
        am_word(r.d[7],r.d[7]&0xffU);r.a[2]=r.a[5]+0xf4eU;if(!am_read(c,r.a[5]+0xd3aU,2,value))return false;am_word(r.d[6],value);
        am_word(r.d[4],r.d[7]);am_word(r.d[4],r.d[4]-1U);r.pc=0x16b66;return true;
    case 0x16b66:
        am_word(r.d[6],r.d[6]-2U);am_word(r.d[6],r.d[6]&r.d[5]);if(!am_read(c,fh1_ix(r.a[1],0,r.d[6]),2,value))return false;
        am_word(r.d[0],value);r.d[1]=0;if(!am_read(c,fh1_ix(r.a[0],1,r.d[0]),1,value))return false;am_byte(r.d[1],value);
        am_word(r.d[1],r.d[1]*2U);if(!fh1_step_byte(c,fh1_ix(r.a[4],1,r.d[1]),false))return false;
        r.d[2]=0;if(!am_read(c,fh1_ix(r.a[4],1,r.d[1]),1,value))return false;am_byte(r.d[2],value);am_word(r.d[2],r.d[2]*2U);
        if(!am_write(c,fh1_ix(r.a[2],0,r.d[2]),2,fh1_w(r.d[0])))return false;
        am_word(r.d[4],r.d[4]-1U);r.pc=fh1_w(r.d[4])!=0xffffU?0x16b66:0x16b8a;return true;
    case 0x16b8a:
        am_word(r.d[4],r.d[7]);am_word(r.d[4],r.d[4]-1U);am_word(r.d[7],r.d[7]*2U);r.a[2]+=am_extend_word(fh1_w(r.d[7]));
        if(!am_read(c,r.a[5]+0xd36U,2,value))return false;am_word(r.d[6],value);r.pc=0x16b96;return true;
    case 0x16b96:
        r.a[2]-=2U;if(!am_read(c,r.a[2],2,value))return false;am_word(r.d[0],value);
        r.d[1]=0;if(!am_read(c,fh1_ix(r.a[0],0,r.d[0]),1,value))return false;am_byte(r.d[1],value);am_word(r.d[1],r.d[1]*2U);
        if(!fh1_step_byte(c,fh1_ix(r.a[4],0,r.d[1]),false))return false;
        r.d[2]=0;if(!am_read(c,fh1_ix(r.a[4],0,r.d[1]),1,value))return false;am_byte(r.d[2],value);
        am_word(r.d[2],r.d[2]*2U);am_word(r.d[2],r.d[2]+r.d[6]);am_word(r.d[2],r.d[2]&r.d[5]);
        if(!am_write(c,fh1_ix(r.a[1],0,r.d[2]),2,fh1_w(r.d[0])))return false;
        am_word(r.d[4],r.d[4]-1U);r.pc=fh1_w(r.d[4])!=0xffffU?0x16b96:0x16bb8;return true;
    case 0x16bb8:return am_return(c);
    // ---- 16bba sprite flush.
    case 0x16bba:r.a[5]=0x108000;r.d[0]=0;return am_call(c,0xce02,0x16bc8);
    case 0x16bc8:return am_call(c,0x166bc,0x16bcc);
    case 0x16bcc:if(!am_read(c,r.a[5]+0xd36U,2,value))return false;am_word(r.d[0],value);r.pc=0x16bd0;return true;
    case 0x16bd0:
        // CMP.W d34(A5),D0; BNE.B 16bd0. While WORD d34(A5) != D0.W the block waits (main decision 3, D5): nothing changes; the
        // declared release writes WORD 108d34 := D0.W.
        if(!am_read(c,r.a[5]+0xd34U,2,value))return false;
        if(fh1_w(value)!=fh1_w(r.d[0])) {c.waiting=true;return true;}
        r.pc=0x16bd6;return true;
    case 0x16bd6:
        r.a[0]=r.a[5]+0xb34U;r.a[1]=r.a[0];
        if(!am_read(c,r.a[5]+0xd36U,2,value))return false;r.a[0]+=am_extend_word(value);
        if(!am_read(c,r.a[5]+0xd3aU,2,value))return false;r.a[1]+=am_extend_word(value);
        if(!am_read(c,r.a[5]+0xd3cU,1,value))return false;r.pc=(value&0x80U)==0U?0x16c6a:0x16bec;return true;
    case 0x16bec:
        // MOVE.L A6,-(A7); LEA 3c0000,A6; LEA d3e(A5),A4; MOVE.W (A4),4(A4); LEA d46(A5),A4; MOVE.W (A4),4(A4).
        if(!am_push(c,4,r.a[6]))return false;r.a[6]=0x3c0000;r.a[4]=r.a[5]+0xd3eU;
        if(!fh1_copy_word(c,r.a[4],r.a[4]+4U))return false;r.a[4]=r.a[5]+0xd46U;
        if(!fh1_copy_word(c,r.a[4],r.a[4]+4U))return false;r.pc=0x16c04;return true;
    case 0x16c04:r.pc=r.a[1]==r.a[0]?0x16c4e:0x16c0a;return true;
    case 0x16c0a:
        // LEA -cc(A5),A2; ADDA.W (A0)+,A2; CMPA.L #108d34,A0; BNE.B 16c1c.
        r.a[2]=fh1_at(r.a[5],0xff34);if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;r.a[2]+=am_extend_word(value);
        r.pc=r.a[0]!=FH1_RING_END?0x16c1c:0x16c18;return true;
    case 0x16c18:r.a[0]=r.a[5]+0xb34U;r.pc=0x16c1c;return true;
    case 0x16c1c:if(!am_read(c,r.a[2]+6U,2,value))return false;fh1_entry_kind(c,value,0x16c30,0x16c2c);return true;
    case 0x16c2c:r.a[4]=r.a[5]+0xd46U;r.pc=0x16c30;return true;
    case 0x16c30:return fh1_writer(c,0xce62,0x16c4c);
    case 0x16c4c:r.pc=0x16c04;return true;                                         // BRA.B 16c04.
    case 0x16c4e:if(!fh1_flush_end(c))return false;r.pc=0x16ce6;return true;
    case 0x16c6a:
        // MOVE.L A6,-(A7); LEA 3c0000,A6; LEA d3e(A5),A4; MOVE.W 2(A4),6(A4); LEA d46(A5),A4; MOVE.W 2(A4),6(A4).
        if(!am_push(c,4,r.a[6]))return false;r.a[6]=0x3c0000;r.a[4]=r.a[5]+0xd3eU;
        if(!fh1_copy_word(c,r.a[4]+2U,r.a[4]+6U))return false;r.a[4]=r.a[5]+0xd46U;
        if(!fh1_copy_word(c,r.a[4]+2U,r.a[4]+6U))return false;r.pc=0x16c86;return true;
    case 0x16c86:r.pc=r.a[1]==r.a[0]?0x16cce:0x16c8c;return true;
    case 0x16c8c:r.a[2]=fh1_at(r.a[5],0xff34);r.pc=r.a[1]!=FH1_RING_START?0x16c9c:0x16c98;return true;
    case 0x16c98:r.a[1]=r.a[5]+0xd34U;r.pc=0x16c9c;return true;
    case 0x16c9c:
        // ADDA.W -(A1),A2; MOVE.W 6(A2),D1; LEA d3e(A5),A4; BCLR.B #2,D1; BEQ.W 16cb2.
        r.a[1]-=2U;if(!am_read(c,r.a[1],2,value))return false;r.a[2]+=am_extend_word(value);
        if(!am_read(c,r.a[2]+6U,2,value))return false;fh1_entry_kind(c,value,0x16cb2,0x16cae);return true;
    case 0x16cae:r.a[4]=r.a[5]+0xd46U;r.pc=0x16cb2;return true;
    case 0x16cb2:return fh1_writer(c,0x11792,0x16ccc);
    case 0x16ccc:r.pc=0x16c86;return true;                                         // BRA.B 16c86.
    case 0x16cce:if(!fh1_flush_end(c))return false;r.pc=0x16ce6;return true;
    case 0x16ce6:
        if(!am_read(c,r.a[5]+0xd3aU,2,value))return false;am_word(r.d[0],value);
        if(!am_write(c,r.a[5]+0xd36U,2,fh1_w(r.d[0])) || !am_write(c,r.a[5]+0xd38U,2,fh1_w(r.d[0])) ||
            !am_write(c,r.a[5]+0xd3dU,1,0xff))return false;
        return am_return(c);
    // ---- 1879c / 1ae56 background coordinate snapshot (X of SUBX from the LSR.B in the same block).
    case 0x1879c:
        if(!am_read(c,r.a[0]+0x14U,2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,r.a[0]+0x18U,2,value))return false;am_word(r.d[1],value);
        if(!am_read(c,r.a[0]+0x25U,1,value))return false;am_byte(r.d[2],value);r.d[3]=0;
        fh1_subx(r,r.d[0]);fh1_subx(r,r.d[1]);
        if(!am_read(c,r.a[0]+0x7cU,2,value))return false;r.pc=fh1_w(r.d[0])==fh1_w(value)?0x187c4:0x187ba;return true;
    case 0x187ba:
        if(!am_write(c,r.a[0]+0x7cU,2,fh1_w(r.d[0])) || !fh1_bit(c,r.a[0]+0x7aU,7,true))return false;r.pc=0x187c4;return true;
    case 0x187c4:if(!am_read(c,r.a[0]+0x7eU,2,value))return false;r.pc=fh1_w(r.d[1])==fh1_w(value)?0x187d6:0x187cc;return true;
    case 0x187cc:
        if(!am_write(c,r.a[0]+0x7eU,2,fh1_w(r.d[1])) || !fh1_bit(c,r.a[0]+0x7aU,7,true))return false;r.pc=0x187d6;return true;
    case 0x187d6:return am_return(c);
    case 0x1ae56:
        // MOVE.W #1,-7ff0(A5); MOVE.W #2000,2ffff2.l; MOVE.W #0,2ffff0.l; LEA 109156,A0; JSR 1879c.l.
        if(!am_write(c,fh1_at(r.a[5],0x8010),2,1) || !am_write(c,0x2ffff2,2,0x2000) || !am_write(c,0x2ffff0,2,0))return false;
        r.a[0]=0x109156;return am_call(c,0x1879c,0x1ae78);
    case 0x1ae78:r.a[0]=0x10b1d6;return am_call(c,0x1879c,0x1ae84);
    case 0x1ae84:r.a[0]=0x10d256;return am_call(c,0x1879c,0x1ae90);
    case 0x1ae90:r.a[0]=0x10d2d6;return am_call(c,0x1879c,0x1ae9c);
    case 0x1ae9c:if(!am_zero_bank(c))return false;return am_return(c);
    // ---- 43dbc frame parity.
    case 0x43dbc:
        if(!am_read(c,r.a[5]+0x5494U,1,value))return false;am_byte(r.d[0],value);am_byte(r.d[0],r.d[0]&1U);am_byte(r.d[0],r.d[0]+1U);
        if(!am_write(c,r.a[5]+0x5494U,1,fh1_b(r.d[0])))return false;return am_return(c);
    default:return am_error(c,"unsupported animation frame head h1 PC");
    }
}
}
