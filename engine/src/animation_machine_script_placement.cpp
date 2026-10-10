#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// d16(A5) operands use the live A5 (43e38 itself sets A5=108000).
bool sp_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool sp_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// MOVE.W/MOVE.L (A1)+,dst: one live read, A1 advanced by the operand size.
bool sp_stream(AnimationMachineContext& c,unsigned int size,std::uint32_t& value) {
    return am_fetch(c,size,value);
}
// MOVE.W (A1)+,d16(A5) / MOVE.L (A1)+,d16(A5).
bool sp_copy(AnimationMachineContext& c,unsigned int size,std::uint32_t displacement) {
    std::uint32_t value=0;return sp_stream(c,size,value) && sp_write(c,displacement,size,value);
}
// MOVE.W (A1)+,D7 (low WORD only).
bool sp_index(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!sp_stream(c,2,value))return false;am_word(c.s.d[7],value);return true;
}
// BCC right after BSR 18c06: consumes the known C returned by the U3 dispatcher.
bool sp_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"script placement caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// Two's-complement WORD for the signed BGT/BLT compares, without implementation-defined casts.
std::int32_t sp_signed(std::uint32_t value) {
    const std::int32_t low=static_cast<std::int32_t>(value&0x7fffU);return (value&0x8000U)?low-0x8000:low;
}
// ADD.W src,D2; [SUB.W 53a6(A5),D2;] CMP.W limit(A5),D2. Returns the signed WORD comparison D2-limit.
bool sp_bound(AnimationMachineContext& c,std::uint32_t add,bool subtract,std::uint32_t limit,std::int32_t& order) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    am_word(r.d[2],r.d[2]+add);
    if(subtract) {if(!sp_read(c,0x53a6,2,value))return false;am_word(r.d[2],r.d[2]-value);}
    if(!sp_read(c,limit,2,value))return false;
    order=sp_signed(r.d[2])-sp_signed(value);return true;
}
// MOVE.W d16(A5),3c0006: one original WORD write = one video port event (LSPC mode register, inferred).
bool sp_mode_port(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!sp_read(c,0xcd90,2,value))return false;
    VideoPortWrite port;port.address=0x3c0006;port.size=2;port.value=value&65535U;c.ports.push_back(port);
    return am_return(c);
}
// BSET/BCLR #3,-326f(A5) (BYTE read-modify-write; Z is not consumed).
bool sp_mode_bit(AnimationMachineContext& c,bool set) {
    std::uint32_t value=0;if(!sp_read(c,0xcd91,1,value))return false;
    value=set?(value|8U):(value&~8U);return sp_write(c,0xcd91,1,value&255U);
}
}
// 480bc frame helper U5: script opcode dispatcher 1a0b6 (20 indexed BRA.W slots, handlers 1a10c..1a252, the
// node/path helpers 1a086/1a09e/19e60, motion reset 19772, LSPC mode 3d7e, cue pointer e89fa, 16fee) and the
// placement step 1a470 (bounding box test, 28ae spawn, 43e08 coordinates, 1a514 payload copy). Existing
// executors: 18c06, 197da, 19802, 8da2, 43ffc, 17012, 1701a, 28ae and 43e38 (43e08/43e22 are cleanup cases).
// The opcode index (1a0b8) and the table indexes (1a086/1a09e) follow the computed address with no range
// check; PC-relative tables 1a08e/1a0a6 and every pointer are read through the live bus (current bank).
bool animation_script_placement_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // 1a0b6: MOVE.W (A1)+,D7; JMP 1a0bc(PC,D7.W).
    case 0x1a0b6:if(!sp_index(c))return false;r.pc=am_index(0x1a0bc,r.d[7]);return true;
    case 0x1a0bc:r.pc=0x1a174;return true;
    case 0x1a0c0:r.pc=0x1a192;return true;
    case 0x1a0c4:r.pc=0x1a1c2;return true;
    case 0x1a0c8:r.pc=0x1a116;return true;
    case 0x1a0cc:r.pc=0x1a10c;return true;
    case 0x1a0d0:r.pc=0x1a1d0;return true;
    case 0x1a0d4:r.pc=0x1a1fa;return true;
    case 0x1a0d8:r.pc=0x1a20a;return true;
    case 0x1a0dc:r.pc=0x1a222;return true;
    case 0x1a0e0:r.pc=0x1a230;return true;
    case 0x1a0e4:r.pc=0x1a242;return true;
    case 0x1a0e8:r.pc=0x1a248;return true;
    case 0x1a0ec:r.pc=0x1a11c;return true;
    case 0x1a0f0:r.pc=0x1a12e;return true;
    case 0x1a0f4:r.pc=0x1a146;return true;
    case 0x1a0f8:r.pc=0x1a150;return true;
    case 0x1a0fc:r.pc=0x1a156;return true;
    case 0x1a100:r.pc=0x1a15e;return true;
    case 0x1a104:r.pc=0x1a168;return true;
    case 0x1a108:r.pc=0x1a16e;return true;
    // 10: MOVEA.L (A1)+,A0; MOVEA.L (A0),A0; JMP e89fa.
    case 0x1a10c:
        if(!sp_stream(c,4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0],4,value))return false;r.a[0]=value;r.pc=0xe89fa;return true;
    // 0c: MOVEA.L (A1)+,A0; BRA 1a40e.
    case 0x1a116:if(!sp_stream(c,4,value))return false;r.a[0]=value;r.pc=0x1a40e;return true;
    // 1a40e: MOVE.L A0,540e(A5); RTS.
    case 0x1a40e:if(!sp_write(c,0x540e,4,r.a[0]))return false;return am_return(c);
    // 30: four WORDs to 5426/5428/542a/542c(A5).
    case 0x1a11c:
        if(!sp_copy(c,2,0x5426) || !sp_copy(c,2,0x5428) || !sp_copy(c,2,0x542a) || !sp_copy(c,2,0x542c))return false;
        return am_return(c);
    // 34: MOVE.W (A1)+,D0; ROL.W #1,D0; ANDI.W #3,D0; MOVE.B 53cc(A5),D1; ANDI.B #fc,D1; OR.B D0,D1;
    // MOVE.B D1,53cc(A5).
    case 0x1a12e: {
        if(!sp_stream(c,2,value))return false;am_word(r.d[0],value);
        const std::uint32_t word=r.d[0]&65535U;am_word(r.d[0],(((word<<1)|(word>>15))&65535U)&3U);
        if(!sp_read(c,0x53cc,1,value))return false;am_byte(r.d[1],value);
        am_byte(r.d[1],r.d[1]&0xfcU);am_byte(r.d[1],r.d[1]|(r.d[0]&255U));
        if(!sp_write(c,0x53cc,1,r.d[1]&255U))return false;return am_return(c);
    }
    // 38: two LONGs to 53fc/5400(A5).
    case 0x1a146:if(!sp_copy(c,4,0x53fc) || !sp_copy(c,4,0x5400))return false;return am_return(c);
    case 0x1a150:if(!sp_copy(c,2,0x5432))return false;return am_return(c);           // 3c
    // 40: MOVE.W (A1)+,D0; JMP 3d7e.
    case 0x1a156:if(!sp_stream(c,2,value))return false;am_word(r.d[0],value);r.pc=0x3d7e;return true;
    case 0x1a15e:if(!sp_copy(c,2,0x542e) || !sp_copy(c,2,0x5430))return false;return am_return(c); // 44
    case 0x1a168:if(!sp_copy(c,2,0x543c))return false;return am_return(c);           // 48
    case 0x1a16e:if(!sp_copy(c,4,0x5434))return false;return am_return(c);           // 4c
    // 00: MOVE.W (A1)+,D0; MOVE.W (A1)+,D1; MOVEA.L (A1)+,A2; MOVE.L A1,-(A7); MOVEA.L A2,A1; BSR 19772.
    case 0x1a174:
        if(!sp_stream(c,2,value))return false;am_word(r.d[0],value);
        if(!sp_stream(c,2,value))return false;am_word(r.d[1],value);
        if(!sp_stream(c,4,value))return false;r.a[2]=value;
        if(!am_push(c,4,r.a[1]))return false;r.a[1]=r.a[2];return am_call(c,0x19772,0x1a182);
    case 0x1a182:return am_call(c,0x197da,0x1a186);
    // MOVE.W D7,541e(A5); MOVE.W D7,5420(A5); MOVEA.L (A7)+,A1; RTS.
    case 0x1a186:
        if(!sp_write(c,0x541e,2,r.d[7]&65535U) || !sp_write(c,0x5420,2,r.d[7]&65535U))return false;
        if(!am_pop(c,4,value))return false;r.a[1]=value;return am_return(c);
    // 04: MOVE.W (A1)+,D0; zero bank (WORD 0 -> -7ff0(A5), 1000 -> 2ffff2, 0 -> 2ffff0); MOVEA.L 20000c,A0
    // (read after the bank write); LSL.W #2,D0; MOVEA.L 0(A0,D0.W),A0; MOVE.L A1,-(A7); JSR 8da2.
    case 0x1a192:
        if(!sp_stream(c,2,value))return false;am_word(r.d[0],value);
        if(!am_zero_bank(c))return false;
        if(!am_read(c,0x20000c,4,value))return false;r.a[0]=value;am_word(r.d[0],r.d[0]<<2);
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;
        if(!am_push(c,4,r.a[1]))return false;return am_call(c,0x8da2,0x1a1be);
    // MOVEA.L (A7)+,A1; RTS.
    case 0x1a1be:case 0x1a1cc:case 0x1a1f6:case 0x1a23e:
        if(!am_pop(c,4,value))return false;r.a[1]=value;return am_return(c);
    // 08: MOVEA.L (A1)+,A0; MOVE.L A1,-(A7); JSR 43ffc.
    case 0x1a1c2:
        if(!sp_stream(c,4,value))return false;r.a[0]=value;
        if(!am_push(c,4,r.a[1]))return false;return am_call(c,0x43ffc,0x1a1cc);
    // 14/18/1c: MOVE.W (A1)+,D7; BSR 1a086.
    case 0x1a1d0:if(!sp_index(c))return false;return am_call(c,0x1a086,0x1a1d6);
    case 0x1a1fa:if(!sp_index(c))return false;return am_call(c,0x1a086,0x1a200);
    case 0x1a20a:if(!sp_index(c))return false;return am_call(c,0x1a086,0x1a210);
    // MOVEQ #0,D0; MOVEQ #0,D1; MOVE.W (A1)+,D0/D1; SWAP both; ADD.L 538e(A5),D0; ADD.L 5392(A5),D1;
    // MOVE.L A1,-(A7); MOVEA.W #0,A1; JSR 16fee.
    case 0x1a1d6:
        r.d[0]=0;r.d[1]=0;
        if(!sp_stream(c,2,value))return false;am_word(r.d[0],value);
        if(!sp_stream(c,2,value))return false;am_word(r.d[1],value);
        am_swap(r.d[0]);am_swap(r.d[1]);
        if(!sp_read(c,0x538e,4,value))return false;r.d[0]+=value;
        if(!sp_read(c,0x5392,4,value))return false;r.d[1]+=value;
        if(!am_push(c,4,r.a[1]))return false;r.a[1]=0;return am_call(c,0x16fee,0x1a1f6);
    // MOVE.W (A1)+,40(A0); MOVE.W (A1)+,42(A0); RTS.
    case 0x1a200:
        if(!sp_stream(c,2,value) || !am_write(c,am_index(r.a[0],0x28),2,value))return false;
        if(!sp_stream(c,2,value) || !am_write(c,am_index(r.a[0],0x2a),2,value))return false;
        return am_return(c);
    // TST.W (A1)+; BEQ 1a21c.
    case 0x1a210:if(!sp_stream(c,2,value))return false;r.pc=(value&65535U)?0x1a216:0x1a21c;return true;
    case 0x1a216:r.pc=0x17012;return true; // JMP: the RTS of 17012/1701a returns to 1a296.
    case 0x1a21c:r.pc=0x1701a;return true;
    // 20: MOVE.B 540c(A5),D7; AND.B (A1)+,D7; OR.B (A1)+,D7; MOVE.B D7,540c(A5).
    case 0x1a222:
        if(!sp_read(c,0x540c,1,value))return false;am_byte(r.d[7],value);
        if(!sp_stream(c,1,value))return false;am_byte(r.d[7],r.d[7]&value);
        if(!sp_stream(c,1,value))return false;am_byte(r.d[7],r.d[7]|value);
        if(!sp_write(c,0x540c,1,r.d[7]&255U))return false;return am_return(c);
    // 24: MOVE.W (A1)+,D7; MOVEA.L (A1)+,A2; MOVE.L A1,-(A7); BSR 1a09e.
    case 0x1a230:
        if(!sp_index(c))return false;
        if(!sp_stream(c,4,value))return false;r.a[2]=value;
        if(!am_push(c,4,r.a[1]))return false;return am_call(c,0x1a09e,0x1a23a);
    case 0x1a23a:return am_call(c,0x19e60,0x1a23e);
    case 0x1a242:if(!sp_copy(c,2,0x5416))return false;return am_return(c);           // 28
    // 2c: MOVE.W (A1)+,D0; BPL 1a252 (N only).
    case 0x1a248:if(!sp_stream(c,2,value))return false;am_word(r.d[0],value);r.pc=(value&0x8000U)?0x1a24e:0x1a252;return true;
    case 0x1a24e:am_word(r.d[0],0x7fff);r.pc=0x1a252;return true;
    // MOVE.W D0,5416(A5); MOVE.W D0,541e(A5); SUB.W (A1)+,D0; MOVE.W D0,5420(A5); MOVE.W (A1)+,D0;
    // MOVE.L A1,5422(A5); ADDA.W D0,A1; RTS.
    case 0x1a252:
        if(!sp_write(c,0x5416,2,r.d[0]&65535U) || !sp_write(c,0x541e,2,r.d[0]&65535U))return false;
        if(!sp_stream(c,2,value))return false;am_word(r.d[0],r.d[0]-value);
        if(!sp_write(c,0x5420,2,r.d[0]&65535U))return false;
        if(!sp_stream(c,2,value))return false;am_word(r.d[0],value);
        if(!sp_write(c,0x5422,4,r.a[1]))return false;r.a[1]=am_index(r.a[1],r.d[0]);return am_return(c);

    // 1a086/1a09e: MOVEA.L 1a08e/1a0a6(PC,D7.W),A0/A1; NOP; RTS (no range check, live bus).
    case 0x1a086:if(!am_read(c,am_index(0x1a08e,r.d[7]),4,value))return false;r.a[0]=value;return am_return(c);
    case 0x1a09e:if(!am_read(c,am_index(0x1a0a6,r.d[7]),4,value))return false;r.a[1]=value;return am_return(c);
    // 19e60: MOVE.L A2,(A1); RTS.
    case 0x19e60:if(!am_write(c,r.a[1],4,r.a[2]))return false;return am_return(c);
    // 16fee: CLR.W 44(A0); JMP 43e22.
    case 0x16fee:if(!am_write(c,am_index(r.a[0],0x2c),2,0))return false;r.pc=0x43e22;return true;

    // 19772: MOVE.W D0,53b8(A5); MOVE.W D1,53ba(A5); SWAP/CLR.W D0 and D1; MOVE.L D0,53bc(A5);
    // MOVE.L D1,53c0(A5); MOVE.L A1,53b4(A5); CMPA.W #0,A1; BEQ 197ba.
    case 0x19772:
        if(!sp_write(c,0x53b8,2,r.d[0]&65535U) || !sp_write(c,0x53ba,2,r.d[1]&65535U))return false;
        am_swap(r.d[0]);am_word(r.d[0],0);am_swap(r.d[1]);am_word(r.d[1],0);
        if(!sp_write(c,0x53bc,4,r.d[0]) || !sp_write(c,0x53c0,4,r.d[1]) || !sp_write(c,0x53b4,4,r.a[1]))return false;
        r.pc=r.a[1]?0x19796:0x197ba;return true;
    // MOVE.W 6(A1),D0; MOVE.W 8(A1),D1; BSR 18c06.
    case 0x19796:
        if(!am_read(c,am_index(r.a[1],6),2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,am_index(r.a[1],8),2,value))return false;am_word(r.d[1],value);
        return am_call(c,0x18c06,0x197a2);
    case 0x197a2:return sp_carry(c,0x197b2,0x197a6); // BCC 197b2
    // C=1: ADD.W D0,53ba(A5); ADD.W D1,53c0(A5); BRA 197ba. C=0: ADD.W D0,53b8(A5); ADD.W D1,53bc(A5).
    case 0x197a6:case 0x197b2: {
        const bool set=r.pc==0x197a6;
        if(!sp_read(c,set?0x53baU:0x53b8U,2,value) || !sp_write(c,set?0x53baU:0x53b8U,2,(value+r.d[0])&65535U))return false;
        if(!sp_read(c,set?0x53c0U:0x53bcU,2,value) || !sp_write(c,set?0x53c0U:0x53bcU,2,(value+r.d[1])&65535U))return false;
        r.pc=0x197ba;return true;
    }
    // MOVE.L 53bc(A5),D0; MOVE.L 53c0(A5),D1; NEG.L both; ADDI.L #01000000,D1; LEA 538e(A5),A0;
    // MOVEA.W #0,A1; JMP 43e22 (its RTS returns to 1a182).
    case 0x197ba:
        if(!sp_read(c,0x53bc,4,value))return false;r.d[0]=0U-value;
        if(!sp_read(c,0x53c0,4,value))return false;r.d[1]=(0U-value)+0x01000000U;
        r.a[0]=am_index(r.a[5],0x538e);r.a[1]=0;r.pc=0x43e22;return true;

    // 3d7e: SUBQ.W #1,D0; BCC 3d9c (C only for an old WORD 0).
    case 0x3d7e: {
        const bool borrow=(r.d[0]&65535U)==0U;am_word(r.d[0],r.d[0]-1U);r.pc=borrow?0x3d84:0x3d9c;return true;
    }
    // MOVE.B #0,104d90; BSET #3,-326f(A5); MOVE.W -3270(A5),3c0006; RTS.
    case 0x3d84:
        if(!am_write(c,0x104d90,1,0) || !sp_mode_bit(c,true))return false;return sp_mode_port(c);
    // MOVE.B D0,104d90; BCLR #3,-326f(A5); MOVE.W -3270(A5),3c0006; RTS.
    case 0x3d9c:
        if(!am_write(c,0x104d90,1,r.d[0]&255U) || !sp_mode_bit(c,false))return false;return sp_mode_port(c);

    // e89fa: CMPA.W #0,A0; BNE e8a06 / LEA e89ec(PC),A0 / MOVE.L A0,5e2a(A5); RTS.
    case 0xe89fa:r.pc=r.a[0]?0xe8a06:0xe8a02;return true;
    case 0xe8a02:r.a[0]=0xe89ec;r.pc=0xe8a06;return true;
    case 0xe8a06:if(!sp_write(c,0x5e2a,4,r.a[0]))return false;return am_return(c);

    // 1a470: MOVEQ #0,D7; MOVE.W (A0),D7; MOVE.W 4(A0),D0; MOVE.W 6(A0),D1; SWAP D0; SWAP D1; JSR 19802.
    case 0x1a470:
        r.d[7]=0;if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[7],value);
        if(!am_read(c,am_index(r.a[0],4),2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,am_index(r.a[0],6),2,value))return false;am_word(r.d[1],value);
        am_swap(r.d[0]);am_swap(r.d[1]);return am_call(c,0x19802,0x1a484);
    // SWAP D0; SWAP D1; SWAP D7; CMP.W 5418(A5),D7; BCC 1a4da (unsigned D7.W >= phase).
    case 0x1a484:
        am_swap(r.d[0]);am_swap(r.d[1]);am_swap(r.d[7]);
        if(!sp_read(c,0x5418,2,value))return false;r.pc=(r.d[7]&65535U)>=(value&65535U)?0x1a4da:0x1a492;return true;
    // MOVEQ #0,D2; MOVEQ #0,D3; MOVEA.L 8(A0),A1; CMPA.W #0,A1; BEQ 1a4a6.
    case 0x1a492:
        r.d[2]=0;r.d[3]=0;if(!am_read(c,am_index(r.a[0],8),4,value))return false;r.a[1]=value;
        r.pc=value?0x1a4a2:0x1a4a6;return true;
    case 0x1a4a2:
        if(!sp_stream(c,4,value))return false;r.d[2]=value;
        if(!sp_stream(c,4,value))return false;r.d[3]=value;r.pc=0x1a4a6;return true;
    // Bounding box: Y side (D1, 53f8 BGT / 53f6 BLT), then SWAP D2/D3 and X side (D0, 53f4 / 53f2). Both
    // sides subtract 53a6(A5) (original bytes).
    case 0x1a4a6: {
        std::int32_t order=0;if(!sp_bound(c,r.d[1]&65535U,true,0x53f8,order))return false;
        r.pc=order>0?0x1a51c:0x1a4b4;return true;
    }
    case 0x1a4b4: {
        std::int32_t order=0;if(!sp_bound(c,r.d[3]&65535U,false,0x53f6,order))return false;
        r.pc=order<0?0x1a51c:0x1a4be;return true;
    }
    case 0x1a4be: {
        am_swap(r.d[2]);am_swap(r.d[3]);
        std::int32_t order=0;if(!sp_bound(c,r.d[0]&65535U,true,0x53f4,order))return false;
        r.pc=order>0?0x1a51c:0x1a4d0;return true;
    }
    case 0x1a4d0: {
        std::int32_t order=0;if(!sp_bound(c,r.d[3]&65535U,false,0x53f2,order))return false;
        r.pc=order<0?0x1a51c:0x1a4da;return true;
    }
    // MOVE.L A0,-(A7); MOVE.W D0,-(A7); MOVE.W D1,-(A7); MOVEA.L 12(A0),A0; MOVE.W #0,D0; JSR 28ae.
    case 0x1a4da:
        if(!am_push(c,4,r.a[0]) || !am_push(c,2,r.d[0]&65535U) || !am_push(c,2,r.d[1]&65535U))return false;
        if(!am_read(c,am_index(r.a[0],0xc),4,value))return false;r.a[0]=value;am_word(r.d[0],0);
        return am_call(c,0x28ae,0x1a4ee);
    // MOVE.W (A7)+,D1; MOVE.W (A7)+,D0; LEA 46(A0),A0; LEA 538e(A5),A1; JSR 43e08. The C returned by 28ae is
    // not consumed: on failure its A0 (A5-7168) is used as is.
    case 0x1a4ee:
        if(!am_pop(c,2,value))return false;am_word(r.d[1],value);
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        r.a[0]=am_index(r.a[0],0x2e);r.a[1]=am_index(r.a[5],0x538e);return am_call(c,0x43e08,0x1a500);
    // LEA 72(A0),A1; MOVEA.L (A7)+,A0; MOVE.W 2(A0),D0; LEA 16(A0),A0; TST.W D0; BEQ 1a51a.
    case 0x1a500:
        r.a[1]=am_index(r.a[0],0x48);if(!am_pop(c,4,value))return false;r.a[0]=value;
        if(!am_read(c,am_index(r.a[0],2),2,value))return false;am_word(r.d[0],value);
        r.a[0]=am_index(r.a[0],0x10);r.pc=(r.d[0]&65535U)?0x1a514:0x1a51a;return true;
    // MOVE.W (A0)+,(A1)+; SUBQ.W #2,D0; BNE 1a514 (an odd length never reaches 0).
    case 0x1a514:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;
        if(!am_write(c,r.a[1],2,value))return false;r.a[1]+=2U;
        am_word(r.d[0],r.d[0]-2U);r.pc=(r.d[0]&65535U)?0x1a514:0x1a51a;return true;
    case 0x1a51a:return am_return(c);
    // Skip: MOVE.W 2(A0),D0; LEA 16(A0,D0.W),A0; RTS (signed length).
    case 0x1a51c:
        if(!am_read(c,am_index(r.a[0],2),2,value))return false;am_word(r.d[0],value);
        r.a[0]=am_index(r.a[0],0x10)+am_extend_word(r.d[0]);return am_return(c);
    default:return am_error(c,"unsupported animation script placement PC");
    }
}
}
