#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// MOVE.L D0,3c0000: one original LONG write is one observed video event.
void close_port(AnimationMachineContext& c,std::uint32_t value) {
    VideoPortWrite port;port.address=0x3c0000;port.size=4;port.value=value;c.ports.push_back(port);
}
// MOVE.B d(An),Dn: one live BYTE read, low BYTE replaced.
bool close_byte(AnimationMachineContext& c,std::uint32_t address,std::uint32_t& reg) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;am_byte(reg,value);return true;
}
}
// Card menu close (-e5=2 at a3e2): a662 shrinks the -f2 frame by a2be (box redraw 9b58 at the
// new height, erase loop with the a018 cover test) until 4(A2)=0; then 9e94 (flag-bit0 clear
// rows, nothing when 4(A2)=0), ADDI.L #10,-f2 pops the frame and a694 returns D0=-1 to c2c0.
// c2c8 child end: fade 8c16, 7e timer c2e0, parent 62(c(A6))=ff and JMP 2a00.
// Boundary without an executor: a698 (nested menu return, -f2 still below 107f0e).
bool animation_card_menu_close_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // MOVEA.L 107f12.L,A2; MOVEQ #0,D0; MOVE.B 9(A2),D0; LSL.W #5,D0; ADD.B a(A2),D0 (BYTE);
    // ADDI.W #7000,D0; MOVE.W D0,D3; MOVE.B 4(A2),D7.
    case 0x9e94:
        if(!am_read(c,0x107f12,4,value))return false;r.a[2]=value;
        r.d[0]=0;if(!close_byte(c,r.a[2]+9U,r.d[0]))return false;am_word(r.d[0],(r.d[0]&65535U)<<5);
        if(!am_read(c,r.a[2]+0xaU,1,value))return false;am_byte(r.d[0],r.d[0]+value);
        am_word(r.d[0],r.d[0]+0x7000U);am_word(r.d[3],r.d[0]);
        if(!close_byte(c,r.a[2]+4U,r.d[7]))return false;r.pc=0x9eb0;return true;
    // CMPI.B #0,D7; BEQ 9ee4.
    case 0x9eb0:r.pc=(r.d[7]&255U)?0x9eb8:0x9ee4;return true;
    // SWAP D0; MOVE.W #ff,D0; MOVE.B b(A2),D6.
    case 0x9eb8:
        am_swap(r.d[0]);am_word(r.d[0],0x00ff);if(!close_byte(c,r.a[2]+0xbU,r.d[6]))return false;
        r.pc=0x9ec2;return true;
    // CMPI.B #0,D6; BEQ 9eda.
    case 0x9ec2:r.pc=(r.d[6]&255U)?0x9eca:0x9eda;return true;
    // MOVE.L D0,3c0000; ADDI.L #200000,D0 (32-bit, carry out of bit 31 lost); SUBQ.B #1,D6; BRA 9ec2.
    case 0x9eca:
        close_port(c,r.d[0]);r.d[0]+=0x200000U;am_byte(r.d[6],r.d[6]-1U);r.pc=0x9ec2;return true;
    // SWAP D0; ADDQ.W #1,D3; MOVE.W D3,D0; SUBQ.B #1,D7; BRA 9eb0.
    case 0x9eda:
        am_swap(r.d[0]);am_word(r.d[3],r.d[3]+1U);am_word(r.d[0],r.d[3]);am_byte(r.d[7],r.d[7]-1U);
        r.pc=0x9eb0;return true;
    case 0x9ee4:case 0xc2f8:return am_return(c);
    // MOVEQ #0,D0; MOVE.B 6(A2),D0; LSL.W #6,D0; MOVE.W 4(A2),D1 (WORD incl. byte 5);
    // SUB.W D0,D1; BCC a2d6 (no WORD borrow).
    case 0xa2be:
        r.d[0]=0;if(!close_byte(c,r.a[2]+6U,r.d[0]))return false;am_word(r.d[0],(r.d[0]&65535U)<<6);
        if(!am_read(c,r.a[2]+4U,2,value))return false;am_word(r.d[1],value);
        am_word(r.d[1],value-(r.d[0]&65535U));r.pc=value>=(r.d[0]&65535U)?0xa2d6:0xa2d0;return true;
    // Borrow: ADD.W D1,D0 (D0.W becomes the old WORD); MOVE.W #0,D1.
    case 0xa2d0:am_word(r.d[0],r.d[0]+r.d[1]);am_word(r.d[1],0);r.pc=0xa2d6;return true;
    // MOVE.W D1,4(A2); ANDI.W #ff,D1; ADD.W D0,D1; LSR.W #8,D1; MOVE.W D1,-(A7); LEA a008,A1; BSR 9b58.
    case 0xa2d6:
        if(!am_write(c,r.a[2]+4U,2,r.d[1]&65535U))return false;
        am_word(r.d[1],r.d[1]&0xffU);am_word(r.d[1],r.d[1]+r.d[0]);am_word(r.d[1],(r.d[1]&65535U)>>8);
        if(!am_push(c,2,r.d[1]&65535U))return false;r.a[1]=0xa008;return am_call(c,0x9b58,0xa2ec);
    // MOVE.W #ff,D0; SWAP D0; CLR.W D0; MOVE.B 9(A2),D0; LSL.W #5,D0; ADD.B a(A2),D0;
    // ADDI.W #7000,D0; ADD.B 4(A2),D0 (BYTE: the new row count).
    case 0xa2ec:
        am_word(r.d[0],0x00ff);am_swap(r.d[0]);am_word(r.d[0],0);
        if(!close_byte(c,r.a[2]+9U,r.d[0]))return false;am_word(r.d[0],(r.d[0]&65535U)<<5);
        if(!am_read(c,r.a[2]+0xaU,1,value))return false;am_byte(r.d[0],r.d[0]+value);
        am_word(r.d[0],r.d[0]+0x7000U);
        if(!am_read(c,r.a[2]+4U,1,value))return false;am_byte(r.d[0],r.d[0]+value);r.pc=0xa306;return true;
    // CMPI.W #0,(A7); BEQ a344.
    case 0xa306:
        if(!am_read(c,r.a[7],2,value))return false;r.pc=value?0xa30e:0xa344;return true;
    // MOVE.W D0,-(A7); MOVEA.L -ee(A5),A2; MOVE.B b(A2),D7.
    case 0xa30e:
        if(!am_push(c,2,r.d[0]&65535U) || !am_read(c,am_index(r.a[5],0xff12),4,value))return false;r.a[2]=value;
        if(!close_byte(c,r.a[2]+0xbU,r.d[7]))return false;r.pc=0xa318;return true;
    // CMPI.B #0,D7; BEQ a33c.
    case 0xa318:r.pc=(r.d[7]&255U)?0xa320:0xa33c;return true;
    case 0xa320:return am_call(c,0xa018,0xa324);
    // BCS a332: consumes the C left by a06c (Clear) or a076 (Set).
    case 0xa324:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"card menu caller requires known carry");
        r.pc=r.carry==AnimationCarryClear?0xa328:0xa332;return true;
    // SWAP D0; MOVE.L D0,3c0000; SWAP D0.
    case 0xa328:am_swap(r.d[0]);close_port(c,r.d[0]);am_swap(r.d[0]);r.pc=0xa332;return true;
    // ADDI.L #20,D0 (32-bit); SUBQ.B #1,D7; BRA a318.
    case 0xa332:r.d[0]+=0x20U;am_byte(r.d[7],r.d[7]-1U);r.pc=0xa318;return true;
    // MOVE.W (A7)+,D0; ADDQ.W #1,D0; SUBQ.W #1,(A7) (WORD read-modify-write); BRA a306.
    case 0xa33c:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value+1U);
        if(!am_read(c,r.a[7],2,value) || !am_write(c,r.a[7],2,(value-1U)&65535U))return false;
        r.pc=0xa306;return true;
    // ADDQ.W #2,A7 (address register: whole 32 bits); RTS.
    case 0xa344:r.a[7]+=2U;return am_return(c);
    // MOVE.L A2,-ee(A5); MOVE.B 4(A2),D7; CMPI.B #0,D7; BLS a67a (C is 0, so only Z).
    case 0xa662:
        if(!am_write(c,am_index(r.a[5],0xff12),4,r.a[2]) || !close_byte(c,r.a[2]+4U,r.d[7]))return false;
        r.pc=(r.d[7]&255U)?0xa672:0xa67a;return true;
    case 0xa672:return am_call(c,0xa2be,0xa676);
    case 0xa676:r.d[0]=0;return am_return(c);
    case 0xa67a:return am_call(c,0x9e94,0xa67e);
    // ADDI.L #10,-f2(A5) (LONG read-modify-write); MOVEA.L -f2(A5),A2 (live re-read);
    // CMPA.L #107f0e,A2; BCS a698 (unsigned A2 < 107f0e).
    case 0xa67e:
        if(!am_read(c,am_index(r.a[5],0xff0e),4,value) ||
           !am_write(c,am_index(r.a[5],0xff0e),4,value+0x10U) ||
           !am_read(c,am_index(r.a[5],0xff0e),4,value))return false;
        r.a[2]=value;r.pc=r.a[2]<0x107f0eU?0xa698:0xa694;return true;
    case 0xa694:r.d[0]=0xffffffffU;return am_return(c);
    // MOVEQ #e1,D0/D1/D2 (sign-extended); MOVEQ #14,D3; JSR 8c16.
    case 0xc2c8:
        r.d[0]=0xffffffe1U;r.d[1]=0xffffffe1U;r.d[2]=0xffffffe1U;r.d[3]=0x14;return am_call(c,0x8c16,0xc2d6);
    // MOVE.W D3,7e(A6); MOVE.L #c2e0,(A6); execution falls into c2e0.
    case 0xc2d6:
        if(!am_write(c,r.a[6]+0x7eU,2,r.d[3]&65535U) || !am_write(c,r.a[6],4,0xc2e0))return false;
        r.pc=0xc2e0;return true;
    // SUBQ.W #1,7e(A6); BNE c2f8 (Z of the WORD result).
    case 0xc2e0:
        if(!am_read(c,r.a[6]+0x7eU,2,value))return false;value=(value-1U)&65535U;
        if(!am_write(c,r.a[6]+0x7eU,2,value))return false;r.pc=value?0xc2f8:0xc2e8;return true;
    // MOVEA.L c(A6),A0; MOVE.B #ff,62(A0); JMP 2a00.
    case 0xc2e8:
        if(!am_read(c,r.a[6]+0xcU,4,value))return false;r.a[0]=value;
        if(!am_write(c,r.a[0]+0x62U,1,0xff))return false;r.pc=0x2a00;return true;
    default:return am_error(c,"unsupported animation card menu close PC");
    }
}
}
