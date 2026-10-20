#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (LEA xxx.L, MOVEA.L #, MOVE.L #, MOVE.W #).
const std::uint32_t SC_FRAME_HEAD=0x100820;  // 2aac LEA 100820,A6
const std::uint32_t SC_BASE_LONG=0x104ca4;   // 2ab2 MOVE.L A7,104ca4 (dispatcher level A7 restored by 2a02)
const std::uint32_t SC_FADE_ROWS=0x50074;    // 4fcda MOVEA.L #50074,A0 (WORD rows ending with ffff, physical window only)
const std::uint32_t SC_VIDEO=0x3c0000;       // 4fd6a LEA 3c0000,A4
// The callback 4fcda is installed by 4fcce (MOVE.L #4fcda,(A6)); the 7a(A6) WORD starts at ffe2 and steps by 3 per frame.
bool sc_signed_less(std::uint32_t word,std::uint32_t limit) {
    word&=65535U;return (word&0x8000U)!=0 || word<limit; // CMPI.W #limit,Dn; BLT with a positive limit.
}
}
// Scheduler shell F2: the boot entry 2aac (LEA 100820,A6; MOVE.L A7,104ca4; fall-through into the fade_card dispatcher
// 2ab8), the idle callback 270e..271c (TST.W 10(A6); BEQ 271a; ADDQ.W #1,-335e(A5); RTS) and the stage controller fade
// child 4fcce..4fd0a / 4fd58..4fda6 (13 blocks; created by 47b76 through 28ae). The frame pass is a run from PC 2ac2 with
// A6 = 1008e4 and A7 = SPd that stops at the frame head callback LONG (100820) (e4a / e74); the host rejects any other
// stop value before the run. Nodes without an executor roll the whole pass back. Existing executors used: fade_card
// 2ab8..2ac6 (dispatcher loop) and 2a00 (self delete: 299c, A7 = LONG 104ca4, BRA 2ac2). 2ab2 and the BEQ/BCC/BLT/BGT
// after TST/CMPI are bundled into their block. No carry consumer; 271a and 4fda4 (RTS only) keep C. The 4fd8c MOVEM.W
// D3-D4,(A4) is one 3c0000 size 4 video event (map_transfer convention) when A4 = 3c0000, otherwise two WORD writes.
bool animation_scheduler_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // LEA 100820,A6; MOVE.L A7,104ca4 (A7 unchanged); fall into 2ab8.
    case 0x2aac:
        r.a[6]=SC_FRAME_HEAD;
        if(!am_write(c,SC_BASE_LONG,4,r.a[7]))return false;r.pc=0x2ab8;return true;
    // TST.W 10(A6); BEQ.W 271a (depth 0: static idle node).
    case 0x270e:
        if(!am_read(c,r.a[6]+0x10U,2,value))return false;r.pc=(value&65535U)?0x2716:0x271a;return true;
    // ADDQ.W #1,-335e(A5): zombie visit counter (WORD wrap).
    case 0x2716: {
        const std::uint32_t address=am_index(r.a[5],0xcca2);
        if(!am_read(c,address,2,value) || !am_write(c,address,2,(value+1U)&65535U))return false;
        r.pc=0x271a;return true;
    }
    case 0x271a:case 0x4fda4:return am_return(c);
    // MOVE.W #ffe2,7a(A6); MOVE.L #4fcda,(A6); fall into the callback.
    case 0x4fcce:
        if(!am_write(c,r.a[6]+0x7aU,2,0xffe2) || !am_write(c,r.a[6],4,0x4fcda))return false;
        r.pc=0x4fcda;return true;
    // MOVEA.L #50074,A0; MOVE.W 7a(A6),D1; ADDQ.W #3,D1; CMPI.W #28,D1; BLT.W 4fcfe (signed).
    case 0x4fcda:
        r.a[0]=SC_FADE_ROWS;
        if(!am_read(c,r.a[6]+0x7aU,2,value))return false;
        am_word(r.d[1],value+3U);r.pc=sc_signed_less(r.d[1],0x28)?0x4fcfe:0x4fcee;return true;
    // 4fce0 (tail of 4fcda, entered by BRA.W from 4fcc4 with A0 = 50030): MOVE.W 7a(A6),D1; ADDQ.W #3,D1; CMPI.W #28,D1; BLT.W 4fcfe (signed).
    case 0x4fce0:
        if(!am_read(c,r.a[6]+0x7aU,2,value))return false;
        am_word(r.d[1],value+3U);r.pc=sc_signed_less(r.d[1],0x28)?0x4fcfe:0x4fcee;return true;
    // MOVEA.L c(A6),A0; MOVE.B #1,62(A0); JMP 2a00 (parent completion flag, then self delete).
    case 0x4fcee:
        if(!am_read(c,r.a[6]+0xcU,4,value))return false;r.a[0]=value;
        if(!am_write(c,r.a[0]+0x62U,1,1))return false;r.pc=0x2a00;return true;
    // MOVE.W D1,7a(A6); MOVE.W #1,D2; BRA.W 4fd58.
    case 0x4fcfe:
        if(!am_write(c,r.a[6]+0x7aU,2,r.d[1]&65535U))return false;am_word(r.d[2],1);r.pc=0x4fd58;return true;
    // TST.W D1; BGT.W 4fd6a (signed).
    case 0x4fd58:{
        const std::uint32_t word=r.d[1]&65535U;r.pc=(word!=0 && !(word&0x8000U))?0x4fd6a:0x4fd5e;return true;
    }
    // NEG.W D1; ADDQ.W #1,D1; ADD.W D1,D1; ADDA.W D1,A0 (sign-extended); MOVE.W #1,D1.
    case 0x4fd5e:
        am_word(r.d[1],0U-(r.d[1]&65535U));am_word(r.d[1],(r.d[1]&65535U)+1U);am_word(r.d[1],(r.d[1]&65535U)*2U);
        r.a[0]=am_index(r.a[0],r.d[1]&65535U);am_word(r.d[1],1);r.pc=0x4fd6a;return true;
    // LEA 3c0000,A4; MOVE.W D2,D5.
    case 0x4fd6a:r.a[4]=SC_VIDEO;am_word(r.d[5],r.d[2]);r.pc=0x4fd72;return true;
    // MOVE.W (A0)+,D4; CMPI.W #27,D1; BCC.W 4fda4 (unsigned).
    case 0x4fd72:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[4],value);r.a[0]+=2U;
        r.pc=(r.d[1]&65535U)>=0x27U?0x4fda4:0x4fd7c;return true;
    // CMPI.W #ffff,D4; BEQ.W 4fda4.
    case 0x4fd7c:r.pc=(r.d[4]&65535U)==0xffffU?0x4fda4:0x4fd84;return true;
    // CMPI.W #1f,D2; BCC.W 4fd9e (unsigned).
    case 0x4fd84:r.pc=(r.d[2]&65535U)>=0x1fU?0x4fd9e:0x4fd8c;return true;
    // MOVE.W D1,D3; LSL.W #5,D3; ADD.W D2,D3; ADDI.W #7000,D3; MOVEM.W D3-D4,(A4); ADDQ.W #1,D2; BRA.B 4fd84.
    case 0x4fd8c:
        am_word(r.d[3],(r.d[1]&65535U)<<5);am_word(r.d[3],(r.d[3]&65535U)+(r.d[2]&65535U));am_word(r.d[3],(r.d[3]&65535U)+0x7000U);
        if((r.a[4]&0xffffffU)==SC_VIDEO) {
            VideoPortWrite port;port.address=SC_VIDEO;port.size=4;port.value=((r.d[3]&65535U)<<16)|(r.d[4]&65535U);c.ports.push_back(port);
        } else if(!am_write(c,r.a[4],2,r.d[3]&65535U) || !am_write(c,r.a[4]+2U,2,r.d[4]&65535U))return false;
        am_word(r.d[2],(r.d[2]&65535U)+1U);r.pc=0x4fd84;return true;
    // ADDQ.W #1,D1; MOVE.W D5,D2; BRA.B 4fd72.
    case 0x4fd9e:am_word(r.d[1],(r.d[1]&65535U)+1U);am_word(r.d[2],r.d[5]);r.pc=0x4fd72;return true;
    default:return am_error(c,"unsupported animation scheduler PC");
    }
}
}
