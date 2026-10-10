#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute layer nodes and their 14-byte path states (LEA xxx.L in 1a7d2..1a8fe).
const std::uint32_t UPD_NODE0=0x109156,UPD_NODE1=0x10b1d6,UPD_NODE2=0x10d256,UPD_NODE3=0x10d2d6;
const std::uint32_t UPD_DEBUG=0x10f000; // BTST #3/#4 of this absolute BYTE (1afda, 1b084, 1b0b8).
// d16(A5) operands use the live A5 (43e38 itself sets A5=108000).
bool upd_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool upd_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// d16(An) operand (live register, WORD/LONG alignment checked by the bus).
bool upd_at(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool upd_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// ADD.W/SUB.W/OR.W Dn,d16(An): WORD read-modify-write with wrap.
enum UpdOp {UPD_ADD=0,UPD_SUB=1,UPD_OR=2};
bool upd_modify(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t reg,UpdOp op) {
    std::uint32_t value=0;if(!upd_at(c,base,displacement,2,value))return false;
    if(op==UPD_ADD)value+=reg;else if(op==UPD_SUB)value-=reg;else value|=reg;
    return upd_put(c,base,displacement,2,value&65535U);
}
// MOVE.W (A2)+,dst: one live WORD read, A2 advanced by 2.
bool upd_stream(AnimationMachineContext& c,std::uint32_t& value) {
    if(!am_read(c,c.s.a[2],2,value))return false;c.s.a[2]+=2U;return true;
}
// BTST #n,absolute or d16(A5) BYTE (bit n mod 8): Z is the inverted bit.
bool upd_test(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,std::uint32_t set_pc,std::uint32_t clear_pc) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    c.s.pc=((value>>bit)&1U)?set_pc:clear_pc;return true;
}
// BCLR #n,12(A1); the branch follows the bit before clearing (Z=inverted old bit).
bool upd_clear(AnimationMachineContext& c,unsigned int bit,std::uint32_t set_pc,std::uint32_t clear_pc) {
    std::uint32_t value=0;if(!upd_at(c,c.s.a[1],12,1,value))return false;
    if(!upd_put(c,c.s.a[1],12,1,value&~(1U<<bit)&255U))return false;
    c.s.pc=((value>>bit)&1U)?set_pc:clear_pc;return true;
}
// ASR.W #4 (sign bits shifted in) and ASR.L #8.
std::uint32_t upd_asr4(std::uint32_t value) {
    const std::uint32_t word=value&65535U;return (word>>4)|((word&0x8000U)?0xf000U:0U);
}
std::uint32_t upd_asr8_long(std::uint32_t value) {return (value>>8)|((value&0x80000000U)?0xff000000U:0U);}
// Two's-complement 16-bit value without implementation-defined casts.
std::int32_t upd_signed(std::uint32_t value) {
    const std::int32_t low=static_cast<std::int32_t>(value&0x7fffU);return (value&0x8000U)?low-0x8000:low;
}
// 1724c (axis 0: D0, scale 28, fraction 2c, velocity 8) / 1726c (axis 1: D1, 2a, 2d, c), one block:
// MOVE.W scale(A0),D7; MOVE.W Dn,D6; MULU.W D7,D6; ADD.B D6,frac(A0) (X=C=BYTE carry); SUBX.L D5,D5
// (D5=-X); ASR.L #8,D6; SUB.L D5,D6; SWAP Dn; MULS.W D7,Dn; LSL.L #8,Dn; ADD.L D6,Dn; MOVE.L Dn,vel(A0); RTS.
// X is produced and consumed inside this block only (not part of the machine state).
bool upd_scale(AnimationMachineContext& c,unsigned int axis) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t& reg=r.d[axis];
    if(!upd_at(c,r.a[0],axis?0x2aU:0x28U,2,value))return false;am_word(r.d[7],value);
    am_word(r.d[6],reg);
    r.d[6]=(r.d[6]&65535U)*(r.d[7]&65535U);
    if(!upd_at(c,r.a[0],axis?0x2dU:0x2cU,1,value))return false;
    const std::uint32_t sum=value+(r.d[6]&255U);const std::uint32_t x=(sum>>8)&1U;
    if(!upd_put(c,r.a[0],axis?0x2dU:0x2cU,1,sum&255U))return false;
    r.d[5]=0U-x;
    r.d[6]=upd_asr8_long(r.d[6]);r.d[6]-=r.d[5];
    am_swap(reg);
    const std::int64_t product=static_cast<std::int64_t>(upd_signed(reg))*static_cast<std::int64_t>(upd_signed(r.d[7]));
    reg=static_cast<std::uint32_t>(product);reg<<=8;reg+=r.d[6];
    if(!upd_put(c,r.a[0],axis?0xcU:0x8U,4,reg))return false;
    return am_return(c);
}
// MOVE.W 5404(A5),D0; ADD.W D0,24(A0); LEA node,A0; BTST #bit,540c(A5); BNE skip.
bool upd_shake(AnimationMachineContext& c,std::uint32_t node,unsigned int bit,std::uint32_t set_pc,std::uint32_t clear_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!upd_read(c,0x5404,2,value))return false;am_word(r.d[0],value);
    if(!upd_modify(c,r.a[0],0x18,r.d[0]&65535U,UPD_ADD))return false;
    r.a[0]=node;return upd_test(c,am_index(r.a[5],0x540c),bit,set_pc,clear_pc);
}
// MOVE.L 5396(A5),D0; JSR 1724c / MOVE.L 539a(A5),D1; JSR 1726c.
bool upd_velocity(AnimationMachineContext& c,unsigned int axis,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!upd_read(c,axis?0x539aU:0x5396U,4,value))return false;
    c.s.d[axis]=value;return am_call(c,axis?0x1726cU:0x1724cU,return_pc);
}
// 1b042/1b05e: MOVE.L 20/24/28/32(A0),D0-D3; SUB.L D0,D2; SUBX.L D1,D3; BNE. X and Z are computed here
// (SUBX clears Z only for a non-zero result). 1b05e loads A1 but compares A0 again (original bytes).
bool upd_compare(AnimationMachineContext& c,std::uint32_t ne_pc,std::uint32_t eq_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!upd_at(c,r.a[0],0x14,4,value))return false;r.d[0]=value;
    if(!upd_at(c,r.a[0],0x18,4,value))return false;r.d[1]=value;
    if(!upd_at(c,r.a[0],0x1c,4,value))return false;r.d[2]=value;
    if(!upd_at(c,r.a[0],0x20,4,value))return false;r.d[3]=value;
    const std::uint32_t x=r.d[2]<r.d[0]?1U:0U;r.d[2]-=r.d[0];bool z=r.d[2]==0U;
    r.d[3]=r.d[3]-r.d[1]-x;if(r.d[3])z=false;
    r.pc=z?eq_pc:ne_pc;return true;
}
// DBRA Dn: WORD decrement, loop unless the result is ffff.
void upd_dbra(std::uint32_t& reg,std::uint32_t& pc,std::uint32_t loop_pc,std::uint32_t exit_pc) {
    am_word(reg,reg-1U);pc=(reg&65535U)!=65535U?loop_pc:exit_pc;
}
// 186e0/18692 tail: MOVE.W D4,D0; MOVE.W D5,D1; SUB.W 50(A0),D0; SUB.W 52(A0),D1; NEG.W D1; BSR 18702.
bool upd_transfer(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    am_word(r.d[0],r.d[4]);am_word(r.d[1],r.d[5]);
    if(!upd_at(c,r.a[0],0x32,2,value))return false;am_word(r.d[0],r.d[0]-value);
    if(!upd_at(c,r.a[0],0x34,2,value))return false;am_word(r.d[1],r.d[1]-value);
    am_word(r.d[1],0U-r.d[1]);return am_call(c,0x18702,return_pc);
}
// Path condition opcodes 08/0c/10/14: MOVE.W (A2)+,D7; MOVE.W first(A0),D0; MOVE.W second(A0),D1; SUB.W D0,D1.
bool upd_condition(AnimationMachineContext& c,std::uint32_t first,std::uint32_t second) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!upd_stream(c,value))return false;am_word(r.d[7],value);
    if(!upd_at(c,r.a[0],first,2,value))return false;am_word(r.d[0],value);
    if(!upd_at(c,r.a[0],second,2,value))return false;am_word(r.d[1],value);
    am_word(r.d[1],r.d[1]-r.d[0]);return true;
}
// ...; ADD.W D7,D1; LSL.W #4,D1; ADD.W D1,D0; SUBI.W #k,D0 (N of the WORD result is returned).
bool upd_threshold(AnimationMachineContext& c,std::uint32_t k) {
    AnimationMachineState& r=c.s;
    am_word(r.d[1],r.d[1]+r.d[7]);am_word(r.d[1],r.d[1]<<4);am_word(r.d[0],r.d[0]+r.d[1]);am_word(r.d[0],r.d[0]-k);
    return (r.d[0]&0x8000U)!=0U;
}
// MOVE.W (A2)+,D0; OR.W D0,12(A1); MOVE.W (A2)+,8(A1); MOVE.W (A2)+,10(A1) (opcodes 18 and true conditions).
bool upd_flags_move(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!upd_stream(c,value))return false;am_word(r.d[0],value);
    if(!upd_modify(c,r.a[1],12,r.d[0]&65535U,UPD_OR))return false;
    if(!upd_stream(c,value) || !upd_put(c,r.a[1],8,2,value))return false;
    if(!upd_stream(c,value) || !upd_put(c,r.a[1],10,2,value))return false;
    return true;
}
}
// 480bc frame helper U4: scene update 1a7a8 (camera velocity, four layer nodes 1724c/1726c/1728c -> 43ea8 ->
// existing 43e38), the display/debug check 1afda (non-debug JMP caf0, debug grid 1b016..1b126 with the
// PC-relative tables 1af12/1afd2 read through the live bus) and the path walk 19e64 with the moved-map
// refresh 18656. Existing executors: 43e38, 16ff8, 1861a, 18702, caf0. The path opcode index (19e86) follows
// the computed PC. All A5-relative operands use the live A5.
bool animation_scene_update_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // 1a7a8: LEA 538e(A5),A0; D0=53bc(A5)+(A0); D1=53c0(A5)+4(A0)-01000000; NEG.L both; MOVE.L to 8/12(A0);
    // JSR 43ea8.
    case 0x1a7a8:
        r.a[0]=am_index(r.a[5],0x538e);
        if(!upd_read(c,0x53bc,4,value))return false;r.d[0]=value;
        if(!upd_at(c,r.a[0],0,4,value))return false;r.d[0]+=value;
        if(!upd_read(c,0x53c0,4,value))return false;r.d[1]=value;
        if(!upd_at(c,r.a[0],4,4,value))return false;r.d[1]+=value;r.d[1]-=0x01000000U;
        r.d[0]=0U-r.d[0];r.d[1]=0U-r.d[1];
        if(!upd_put(c,r.a[0],8,4,r.d[0]) || !upd_put(c,r.a[0],12,4,r.d[1]))return false;
        return am_call(c,0x43ea8,0x1a7d2);
    case 0x1a7d2:return upd_shake(c,UPD_NODE0,0,0x1a7f4,0x1a7ea);
    case 0x1a80e:return upd_shake(c,UPD_NODE1,2,0x1a830,0x1a826);
    case 0x1a84a:return upd_shake(c,UPD_NODE2,4,0x1a86c,0x1a862);
    case 0x1a886:return upd_shake(c,UPD_NODE3,6,0x1a8a8,0x1a89e);
    case 0x1a7ea:return upd_velocity(c,0,0x1a7f4);
    case 0x1a826:return upd_velocity(c,0,0x1a830);
    case 0x1a862:return upd_velocity(c,0,0x1a86c);
    case 0x1a89e:return upd_velocity(c,0,0x1a8a8);
    case 0x1a7f4:return upd_test(c,am_index(r.a[5],0x540c),1,0x1a808,0x1a7fe);
    case 0x1a830:return upd_test(c,am_index(r.a[5],0x540c),3,0x1a844,0x1a83a);
    case 0x1a86c:return upd_test(c,am_index(r.a[5],0x540c),5,0x1a880,0x1a876);
    case 0x1a8a8:return upd_test(c,am_index(r.a[5],0x540c),7,0x1a8bc,0x1a8b2);
    case 0x1a7fe:return upd_velocity(c,1,0x1a808);
    case 0x1a83a:return upd_velocity(c,1,0x1a844);
    case 0x1a876:return upd_velocity(c,1,0x1a880);
    case 0x1a8b2:return upd_velocity(c,1,0x1a8bc);
    case 0x1a808:return am_call(c,0x1728c,0x1a80e);
    case 0x1a844:return am_call(c,0x1728c,0x1a84a);
    case 0x1a880:return am_call(c,0x1728c,0x1a886);
    case 0x1a8bc:return am_call(c,0x1728c,0x1a8c2);
    // MOVE.W 5404(A5),D0; ADD.W D0,24(A0); BSR 1afda.
    case 0x1a8c2:
        if(!upd_read(c,0x5404,2,value))return false;am_word(r.d[0],value);
        if(!upd_modify(c,r.a[0],0x18,r.d[0]&65535U,UPD_ADD))return false;
        return am_call(c,0x1afda,0x1a8ce);
    // LEA node,A0; LEA path,A1; BSR 19e64.
    case 0x1a8ce:r.a[0]=UPD_NODE0;r.a[1]=0x10d356;return am_call(c,0x19e64,0x1a8de);
    case 0x1a8de:r.a[0]=UPD_NODE1;r.a[1]=0x10d364;return am_call(c,0x19e64,0x1a8ee);
    case 0x1a8ee:r.a[0]=UPD_NODE2;r.a[1]=0x10d372;return am_call(c,0x19e64,0x1a8fe);
    case 0x1a8fe:r.a[0]=UPD_NODE3;r.a[1]=0x10d380;return am_call(c,0x19e64,0x1a90e);
    case 0x1a90e:case 0x1b014:case 0x1b07a:case 0x1b0de:case 0x1b126:case 0x19e6e:case 0x19e84:case 0x18700:
        return am_return(c);

    case 0x1724c:return upd_scale(c,0);
    case 0x1726c:return upd_scale(c,1);
    case 0x1728c:r.pc=0x43ea8;return true; // JMP 43ea8 (caller's return LONG kept)
    // MOVE.L 8(A0),D0; ADD.L D0,(A0); MOVE.L 12(A0),D0; ADD.L D0,4(A0); BRA.B 43e38.
    case 0x43ea8:
        if(!upd_at(c,r.a[0],8,4,value))return false;r.d[0]=value;
        if(!upd_at(c,r.a[0],0,4,value) || !upd_put(c,r.a[0],0,4,value+r.d[0]))return false;
        if(!upd_at(c,r.a[0],12,4,value))return false;r.d[0]=value;
        if(!upd_at(c,r.a[0],4,4,value) || !upd_put(c,r.a[0],4,4,value+r.d[0]))return false;
        r.pc=0x43e38;return true;

    // 1afda: MOVEQ #0,D7; MOVEQ #0,D6; BTST #3,10f000; BEQ 1afec / MOVEQ #-1,D7; BTST #4 ...; TST.B D7; BNE 1b016.
    case 0x1afda:r.d[7]=0;r.d[6]=0;return upd_test(c,UPD_DEBUG,3,0x1afea,0x1afec);
    case 0x1afea:r.d[7]=0xffffffffU;r.pc=0x1afec;return true;
    case 0x1afec:return upd_test(c,UPD_DEBUG,4,0x1aff8,0x1affa);
    case 0x1aff8:r.d[7]=0xffffffffU;r.pc=0x1affa;return true;
    case 0x1affa:r.pc=(r.d[7]&255U)?0x1b016:0x1b000;return true;
    // MOVE.B 544e(A5),D6; MOVE.B D7,544e(A5); TST.B D6; BEQ 1b014 / JMP caf0.
    case 0x1b000:
        if(!upd_read(c,0x544e,1,value))return false;am_byte(r.d[6],value);
        if(!upd_write(c,0x544e,1,r.d[7]&255U))return false;
        r.pc=(r.d[6]&255U)?0x1b00e:0x1b014;return true;
    case 0x1b00e:r.pc=0xcaf0;return true;
    // Debug: MOVE.L #fff80000,D6; AND.L D6 into six coordinate LONGs; MOVE.B 544e(A5),D6; MOVE.B D7,544e(A5);
    // TST.B D6; BEQ 1b07c.
    case 0x1b016: {
        static const std::uint32_t fields[6]={0x53a2,0x53a6,0x116a,0x116e,0x31ea,0x31ee};
        r.d[6]=0xfff80000U;
        for(unsigned int i=0;i<6;++i) {
            if(!upd_read(c,fields[i],4,value) || !upd_write(c,fields[i],4,value&r.d[6]))return false;
        }
        if(!upd_read(c,0x544e,1,value))return false;am_byte(r.d[6],value);
        if(!upd_write(c,0x544e,1,r.d[7]&255U))return false;
        r.pc=(r.d[6]&255U)?0x1b042:0x1b07c;return true;
    }
    case 0x1b042:r.a[0]=am_index(r.a[5],0x1156);return upd_compare(c,0x1b07c,0x1b05e);
    case 0x1b05e:r.a[1]=am_index(r.a[5],0x31d6);return upd_compare(c,0x1b07c,0x1b07a);
    case 0x1b07c:am_word(r.d[2],0x27);am_word(r.d[3],0x1f);r.pc=0x1b084;return true;
    // MOVE.W D2,D4; LSL.W #5,D4; ADD.W D3,D4; ADDI.W #7000,D4; SWAP D4; MOVE.W #320,D4; LEA 1af12(PC),A1;
    // LEA 1afd2(PC),A2; BTST #3,10f000; BEQ 1b0b8.
    case 0x1b084:
        am_word(r.d[4],r.d[2]);am_word(r.d[4],r.d[4]<<5);am_word(r.d[4],r.d[4]+r.d[3]);am_word(r.d[4],r.d[4]+0x7000U);
        am_swap(r.d[4]);am_word(r.d[4],0x320);r.a[1]=0x1af12;r.a[2]=0x1afd2;
        return upd_test(c,UPD_DEBUG,3,0x1b0a8,0x1b0b8);
    case 0x1b0a8:r.a[0]=am_index(r.a[5],0x1156);return am_call(c,0x1b0e0,0x1b0b0);
    case 0x1b0b0:r.pc=(r.d[4]&65535U)!=0x320U?0x1b0cc:0x1b0b8;return true; // CMPI.W #320,D4; BNE 1b0cc
    case 0x1b0b8:return upd_test(c,UPD_DEBUG,4,0x1b0c4,0x1b0cc);
    case 0x1b0c4:r.a[0]=am_index(r.a[5],0x31d6);return am_call(c,0x1b0e0,0x1b0cc);
    // MOVE.L D4,3c0000 (one original LONG write = one video port event); DBRA D2,1b084.
    case 0x1b0cc: {
        VideoPortWrite port;port.address=0x3c0000;port.size=4;port.value=r.d[4];c.ports.push_back(port);
        upd_dbra(r.d[2],r.pc,0x1b084,0x1b0d6);return true;
    }
    case 0x1b0d6:am_word(r.d[2],0x27);upd_dbra(r.d[3],r.pc,0x1b084,0x1b0de);return true;
    // 1b0e0: cell index from D2/D3 and 20/24(A0); D7.W=(A0+D0.W); ADDI.B #58,D7; D4.W=(A1+2*D7.B); CMPI.W #320.
    case 0x1b0e0:
        am_word(r.d[0],r.d[2]);am_word(r.d[0],r.d[0]<<3);
        if(!upd_at(c,r.a[0],0x14,2,value))return false;am_word(r.d[0],r.d[0]-value);
        am_word(r.d[1],r.d[3]);am_word(r.d[1],r.d[1]<<3);
        if(!upd_at(c,r.a[0],0x18,2,value))return false;am_word(r.d[1],r.d[1]+value);
        am_word(r.d[0],r.d[0]&0x1f8U);am_word(r.d[1],r.d[1]&0x1f8U);am_word(r.d[1],(r.d[1]&65535U)>>2);
        am_word(r.d[0],r.d[0]<<4);am_word(r.d[0],r.d[0]+r.d[1]);am_word(r.d[0],r.d[0]+0x80U);
        if(!upd_at(c,r.a[0],r.d[0]&65535U,2,value))return false;am_word(r.d[7],value);
        am_byte(r.d[7],r.d[7]+0x58U);r.d[6]=0;am_byte(r.d[6],r.d[7]);am_word(r.d[6],r.d[6]+r.d[6]);
        if(!upd_at(c,r.a[1],r.d[6]&65535U,2,value))return false;am_word(r.d[4],value);
        r.pc=(r.d[4]&65535U)==0x320U?0x1b126:0x1b11c;return true;
    // ANDI.W #c000,D7; ROL.W #3,D7; OR.W (A2,D7.W),D4.
    case 0x1b11c: {
        const std::uint32_t word=r.d[7]&0xc000U;am_word(r.d[7],((word<<3)|(word>>13))&65535U);
        if(!upd_at(c,r.a[2],r.d[7]&65535U,2,value))return false;am_word(r.d[4],r.d[4]|value);
        r.pc=0x1b126;return true;
    }

    // 19e64: MOVEA.L (A1),A2; CMPA.W #0,A2; BNE 19e70.
    case 0x19e64:if(!am_read(c,r.a[1],4,value))return false;r.a[2]=value;r.pc=value?0x19e70:0x19e6e;return true;
    // MOVEM.L A1-A2,-(A7) ((A7)=A1, 4(A7)=A2); JSR 18656.
    case 0x19e70:if(!am_push(c,4,r.a[2]) || !am_push(c,4,r.a[1]))return false;return am_call(c,0x18656,0x19e7a);
    case 0x19e7a:
        if(!am_pop(c,4,value))return false;r.a[1]=value;
        if(!am_pop(c,4,value))return false;r.a[2]=value;r.pc=0x19e7e;return true;
    // MOVE.W (A2)+,D7; BPL 19e86 (negative opcode ends the walk without posting the cursor).
    case 0x19e7e:if(!upd_stream(c,value))return false;am_word(r.d[7],value);r.pc=(value&0x8000U)?0x19e84:0x19e86;return true;
    // JMP 19e8a(PC,D7.W): no range check, the computed PC is followed as is.
    case 0x19e86:r.pc=am_index(0x19e8a,r.d[7]);return true;
    case 0x19e8a:r.pc=0x19eaa;return true;
    case 0x19e8e:r.pc=0x19ed0;return true;
    case 0x19e92:r.pc=0x19f9e;return true;
    case 0x19e96:r.pc=0x19fc4;return true;
    case 0x19e9a:r.pc=0x19ff4;return true;
    case 0x19e9e:r.pc=0x1a01c;return true;
    case 0x19ea2:r.pc=0x1a068;return true;
    case 0x19ea6:r.pc=0x19ec2;return true;
    // 00: MOVE.B #10,12(A1); MOVE.W (A2)+,4(A1); MOVE.W (A2)+,6(A1); CLR.W 8(A1); CLR.W 10(A1).
    case 0x19eaa:
        if(!upd_put(c,r.a[1],12,1,0x10))return false;
        if(!upd_stream(c,value) || !upd_put(c,r.a[1],4,2,value))return false;
        if(!upd_stream(c,value) || !upd_put(c,r.a[1],6,2,value))return false;
        if(!upd_put(c,r.a[1],8,2,0) || !upd_put(c,r.a[1],10,2,0))return false;
        r.pc=0x19e7e;return true;
    // 1c: MOVE.W (A2)+,D0; ADD.W D0,4(A1); MOVE.W (A2)+,D0; ADD.W D0,6(A1).
    case 0x19ec2:
        if(!upd_stream(c,value))return false;am_word(r.d[0],value);
        if(!upd_modify(c,r.a[1],4,r.d[0]&65535U,UPD_ADD))return false;
        if(!upd_stream(c,value))return false;am_word(r.d[0],value);
        if(!upd_modify(c,r.a[1],6,r.d[0]&65535U,UPD_ADD))return false;
        r.pc=0x19e7e;return true;
    // 04: MOVEA.L 46(A0),A3; CMPA.W #0,A3; BEQ 19f00.
    case 0x19ed0:if(!upd_at(c,r.a[0],0x2e,4,value))return false;r.a[3]=value;r.pc=value?0x19edc:0x19f00;return true;
    case 0x19edc:return upd_clear(c,1,0x19ee6,0x19eee);
    case 0x19ee6:
        if(!upd_at(c,r.a[3],4,2,value))return false;am_word(r.d[0],value);
        if(!upd_modify(c,r.a[1],4,r.d[0]&65535U,UPD_ADD))return false;r.pc=0x19eee;return true;
    case 0x19eee:return upd_clear(c,3,0x19ef8,0x19f00);
    case 0x19ef8:
        if(!upd_at(c,r.a[3],6,2,value))return false;am_word(r.d[0],value);
        if(!upd_modify(c,r.a[1],6,r.d[0]&65535U,UPD_SUB))return false;r.pc=0x19f00;return true;
    case 0x19f00:return upd_clear(c,0,0x19f0a,0x19f12);
    case 0x19f0a:
        if(!upd_at(c,r.a[2],4,2,value))return false;am_word(r.d[0],value);
        if(!upd_modify(c,r.a[1],4,r.d[0]&65535U,UPD_SUB))return false;r.pc=0x19f12;return true;
    case 0x19f12:return upd_clear(c,2,0x19f1c,0x19f24);
    case 0x19f1c:
        if(!upd_at(c,r.a[2],6,2,value))return false;am_word(r.d[0],value);
        if(!upd_modify(c,r.a[1],6,r.d[0]&65535U,UPD_ADD))return false;r.pc=0x19f24;return true;
    // MOVE.W 8(A1),D0; ADD.W D0,4(A1); MOVE.W 10(A1),D0; ADD.W D0,6(A1); MOVE.B 122(A0),D7; ANDI.B #e7,D7;
    // BCLR #5,12(A1); BEQ 19f4a.
    case 0x19f24:
        if(!upd_at(c,r.a[1],8,2,value))return false;am_word(r.d[0],value);
        if(!upd_modify(c,r.a[1],4,r.d[0]&65535U,UPD_ADD))return false;
        if(!upd_at(c,r.a[1],10,2,value))return false;am_word(r.d[0],value);
        if(!upd_modify(c,r.a[1],6,r.d[0]&65535U,UPD_ADD))return false;
        if(!upd_at(c,r.a[0],0x7a,1,value))return false;am_byte(r.d[7],value);am_byte(r.d[7],r.d[7]&0xe7U);
        return upd_clear(c,5,0x19f46,0x19f4a);
    case 0x19f46:r.d[7]|=8U;r.pc=0x19f4a;return true;   // BSET #3,D7
    case 0x19f4a:return upd_clear(c,6,0x19f54,0x19f58);
    case 0x19f54:r.d[7]|=0x10U;r.pc=0x19f58;return true; // BSET #4,D7
    // MOVE.B D7,122(A0); MOVE.W 4(A1),D0; MOVE.W 6(A1),D1; MOVE.L A2,-(A7); MOVE.L A1,-(A7); MOVEA.L A2,A1;
    // MOVEA.L 8(A1),A2; JSR 16ff8.
    case 0x19f58:
        if(!upd_put(c,r.a[0],0x7a,1,r.d[7]&255U))return false;
        if(!upd_at(c,r.a[1],4,2,value))return false;am_word(r.d[0],value);
        if(!upd_at(c,r.a[1],6,2,value))return false;am_word(r.d[1],value);
        if(!am_push(c,4,r.a[2]) || !am_push(c,4,r.a[1]))return false;
        r.a[1]=r.a[2];if(!upd_at(c,r.a[1],8,4,value))return false;r.a[2]=value;
        return am_call(c,0x16ff8,0x19f74);
    // MOVEA.L (A7),A1; BCLR #4,12(A1); BNE 19f8a.
    case 0x19f74:if(!am_read(c,r.a[7],4,value))return false;r.a[1]=value;return upd_clear(c,4,0x19f8a,0x19f80);
    case 0x19f80:return am_call(c,0x18656,0x19f86);
    case 0x19f86:r.pc=0x19f90;return true;
    case 0x19f8a:return am_call(c,0x1861a,0x19f90);
    // MOVEA.L (A7)+,A1; MOVEA.L (A7)+,A2; LEA 12(A2),A2; MOVE.L A2,(A1); BRA 19e7e.
    case 0x19f90:
        if(!am_pop(c,4,value))return false;r.a[1]=value;
        if(!am_pop(c,4,value))return false;r.a[2]=am_index(value,12);
        if(!am_write(c,r.a[1],4,r.a[2]))return false;r.pc=0x19e7e;return true;
    // 08: SUB.W 20(A0) from 28(A0); BPL 1a060 (N only).
    case 0x19f9e:if(!upd_condition(c,0x14,0x1c))return false;r.pc=(r.d[1]&0x8000U)?0x19fae:0x1a060;return true;
    case 0x19fae:
        if(!upd_at(c,r.a[0],0x32,2,value))return false;am_word(r.d[1],value);
        r.pc=upd_threshold(c,0xffa0)?0x19fc0:0x1a04a;return true; // BPL 1a04a
    // 0c: TST.W D1; BLE 1a060 (Z or N, V=0).
    case 0x19fc4:if(!upd_condition(c,0x14,0x1c))return false;r.pc=(!(r.d[1]&65535U) || (r.d[1]&0x8000U))?0x1a060:0x19fd6;return true;
    case 0x19fd6:
        if(!upd_at(c,r.a[0],0x2e,4,value))return false;r.a[3]=value;
        if(!upd_at(c,r.a[0],0x32,2,value))return false;am_word(r.d[1],value);
        if(!upd_at(c,r.a[3],4,2,value))return false;am_word(r.d[1],r.d[1]+value);
        r.pc=upd_threshold(c,0x1a1)?0x1a04a:0x19ff0;return true; // BMI 1a04a
    // 10: Y axis, TST.W; BLE 1a060.
    case 0x19ff4:if(!upd_condition(c,0x18,0x20))return false;r.pc=(!(r.d[1]&65535U) || (r.d[1]&0x8000U))?0x1a060:0x1a006;return true;
    case 0x1a006:
        if(!upd_at(c,r.a[0],0x34,2,value))return false;am_word(r.d[1],value);
        r.pc=upd_threshold(c,0x270)?0x1a04a:0x1a018;return true; // BMI 1a04a
    // 14: Y axis, BPL 1a060 (N only).
    case 0x1a01c:if(!upd_condition(c,0x18,0x20))return false;r.pc=(r.d[1]&0x8000U)?0x1a02c:0x1a060;return true;
    case 0x1a02c:
        if(!upd_at(c,r.a[0],0x2e,4,value))return false;r.a[3]=value;
        if(!upd_at(c,r.a[0],0x34,2,value))return false;am_word(r.d[1],value);
        if(!upd_at(c,r.a[3],6,2,value))return false;am_word(r.d[1],r.d[1]-value);
        r.pc=upd_threshold(c,0x71)?0x1a046:0x1a04a;return true; // BPL 1a04a
    case 0x19fc0:case 0x19ff0:case 0x1a018:case 0x1a046:r.pc=0x1a060;return true;
    // True condition: flags/move words, then MOVEA.L (A2),A2; MOVE.L A2,(A1) (cursor posted).
    case 0x1a04a:
        if(!upd_flags_move(c))return false;
        if(!am_read(c,r.a[2],4,value))return false;r.a[2]=value;
        if(!am_write(c,r.a[1],4,r.a[2]))return false;r.pc=0x19e7e;return true;
    case 0x1a060:r.a[2]=am_index(r.a[2],10);r.pc=0x19e7e;return true; // LEA 10(A2),A2
    case 0x1a068:if(!upd_flags_move(c))return false;r.pc=0x19e7e;return true;

    // 18656: MOVEA.L 46(A0),A1; CMPA.W #0,A1; BEQ 18700.
    case 0x18656:if(!upd_at(c,r.a[0],0x2e,4,value))return false;r.a[1]=value;r.pc=value?0x18662:0x18700;return true;
    case 0x18662:return upd_test(c,am_index(r.a[0],0x7a),1,0x1866c,0x186b2);
    // MOVE.W 20(A0),D2; MOVE.W 28(A0),D3; ASR.W #4 both; SUB.W D3,D2; BEQ 186b2.
    case 0x1866c:
        if(!upd_at(c,r.a[0],0x14,2,value))return false;am_word(r.d[2],value);
        if(!upd_at(c,r.a[0],0x1c,2,value))return false;am_word(r.d[3],value);
        am_word(r.d[2],upd_asr4(r.d[2]));am_word(r.d[3],upd_asr4(r.d[3]));am_word(r.d[2],r.d[2]-r.d[3]);
        r.pc=(r.d[2]&65535U)?0x1867e:0x186b2;return true;
    // MOVEQ #-6,D4; SUB.W D3,D4; SUB.W D2,D4; TST.W D2; BPL 18692.
    case 0x1867e:
        r.d[4]=0xfffffffaU;am_word(r.d[4],r.d[4]-r.d[3]);am_word(r.d[4],r.d[4]-r.d[2]);
        r.pc=(r.d[2]&0x8000U)?0x1868a:0x18692;return true;
    // ADDI.W #20,D4; ADD.W D2,D4; NEG.W D2.
    case 0x1868a:am_word(r.d[4],r.d[4]+0x20U);am_word(r.d[4],r.d[4]+r.d[2]);am_word(r.d[2],0U-r.d[2]);r.pc=0x18692;return true;
    // MOVE.W #27,D5; MOVE.W 24(A0),D3; ASR.W #4,D3; SUB.W D3,D5; MOVEQ #20,D3; transfer tail (BSR 18702).
    case 0x18692:
        am_word(r.d[5],0x27);if(!upd_at(c,r.a[0],0x18,2,value))return false;am_word(r.d[3],upd_asr4(value));
        am_word(r.d[5],r.d[5]-r.d[3]);r.d[3]=0x20;return upd_transfer(c,0x186b2);
    case 0x186b2:return upd_test(c,am_index(r.a[0],0x7a),2,0x186bc,0x18700);
    // MOVE.W 24(A0),D3; MOVE.W 32(A0),D2; ASR.W #4 both; SUB.W D2,D3; BEQ 18700.
    case 0x186bc:
        if(!upd_at(c,r.a[0],0x18,2,value))return false;am_word(r.d[3],value);
        if(!upd_at(c,r.a[0],0x20,2,value))return false;am_word(r.d[2],value);
        am_word(r.d[3],upd_asr4(r.d[3]));am_word(r.d[2],upd_asr4(r.d[2]));am_word(r.d[3],r.d[3]-r.d[2]);
        r.pc=(r.d[3]&65535U)?0x186ce:0x18700;return true;
    // MOVEQ #7,D5; SUB.W D2,D5; TST.W D3; BPL 186e0.
    case 0x186ce:r.d[5]=7;am_word(r.d[5],r.d[5]-r.d[2]);r.pc=(r.d[3]&0x8000U)?0x186d8:0x186e0;return true;
    // NEG.W D3; ADDI.W #20,D5; ADD.W D3,D5.
    case 0x186d8:am_word(r.d[3],0U-r.d[3]);am_word(r.d[5],r.d[5]+0x20U);am_word(r.d[5],r.d[5]+r.d[3]);r.pc=0x186e0;return true;
    // MOVE.W 20(A0),D2; ASR.W #4,D2; MOVE.W #fffa,D4; SUB.W D2,D4; MOVEQ #20,D2; transfer tail (BSR 18702).
    case 0x186e0:
        if(!upd_at(c,r.a[0],0x14,2,value))return false;am_word(r.d[2],upd_asr4(value));
        am_word(r.d[4],0xfffa);am_word(r.d[4],r.d[4]-r.d[2]);r.d[2]=0x20;return upd_transfer(c,0x18700);
    default:return am_error(c,"unsupported animation scene update PC");
    }
}
}
