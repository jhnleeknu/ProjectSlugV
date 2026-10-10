#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// MOVE.L/MOVE.W to absolute 3c0000: one original write is one observed video event.
void open_port(AnimationMachineContext& c,unsigned int size,std::uint32_t value) {
    VideoPortWrite port;port.address=0x3c0000;port.size=static_cast<std::uint8_t>(size);port.value=value;
    c.ports.push_back(port);
}
// SWAP D0; MOVE.B/MOVE.W #tile,D0; MOVE.L D0,3c0000; SWAP D0; ADDI.W #20,D0.
bool open_tile(AnimationMachineContext& c,unsigned int size,std::uint32_t tile,std::uint32_t next) {
    AnimationMachineState& r=c.s;am_swap(r.d[0]);
    if(size==1)am_byte(r.d[0],tile);else am_word(r.d[0],tile);
    open_port(c,4,r.d[0]);am_swap(r.d[0]);am_word(r.d[0],r.d[0]+0x20U);r.pc=next;return true;
}
// BCS after BSR a018: consumes the C left by a06c (Clear) or a076 (Set).
bool open_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"card menu caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.B d(An),Dn: one live BYTE read, low BYTE replaced.
bool open_byte(AnimationMachineContext& c,std::uint32_t address,std::uint32_t& reg) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;am_byte(reg,value);return true;
}
// MOVE.B 7(A2),8(A2).
bool open_cursor(AnimationMachineContext& c) {
    std::uint32_t value=0;return am_read(c,c.s.a[2]+7U,1,value) && am_write(c,c.s.a[2]+8U,1,value);
}
// MOVEA.L -ee(A5),A2.
bool open_frame(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!am_read(c,am_index(c.s.a[5],0xff12),4,value))return false;c.s.a[2]=value;return true;
}
// JSR/JMP through a register: an odd target is a checked error, not an executed fetch.
bool open_target(AnimationMachineContext& c,std::uint32_t target) {
    if(target&1U)return am_error(c,"animation card menu open odd jump target");
    return true;
}
// CMP.B mem,Dn then BCS: taken when Dn.B < mem BYTE (unsigned).
bool open_below(AnimationMachineContext& c,std::uint32_t reg,std::uint32_t address,
    std::uint32_t below_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    c.s.pc=(reg&255U)<value?below_pc:other_pc;return true;
}
// MOVEM.L (A7)+,D5-D7/A0-A1 (ascending D5,D6,D7,A0,A1); then the CCR op; RTS.
bool open_a018_return(AnimationMachineContext& c,AnimationCarryState carry) {
    AnimationMachineState& r=c.s;
    if(!am_pop(c,4,r.d[5]) || !am_pop(c,4,r.d[6]) || !am_pop(c,4,r.d[7]) ||
       !am_pop(c,4,r.a[0]) || !am_pop(c,4,r.a[1]))return false;
    r.carry=carry;return am_return(c);
}
}
// Card menu frame a370 (opening animation a5d2/a348 and first full draw a5ea),
// box 9b58, items 9e1a/9d3a, cover test a018, text loop 3918 with renderers
// a008/e84c8->3650, item callbacks 9b3e -> c1c4/bf94 (a73e sound, a216 cursor).
// c2c0/c2c6 (TST.B D0 after JSR a370) return the c2ba frame to its caller.
// Executed by other units: a406/a70a (input), 9e94/a2be/a662/c2c8 (close).
// Boundaries without an executor: 9f36 a6da a71a bd26 e84d6 a63c.
bool animation_card_menu_open_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // SWAP D0; MOVE.W D1,D0; LSL.B #4; LSL.W #4; MOVE.B D2,D0; MOVE.L D0,3c0000;
    // SWAP D0; ADDI.W #20,D0; MOVE.W #8200,3c0000; RTS.
    case 0x3650:
        am_swap(r.d[0]);am_word(r.d[0],r.d[1]);am_byte(r.d[0],(r.d[0]&255U)<<4);
        am_word(r.d[0],(r.d[0]&65535U)<<4);am_byte(r.d[0],r.d[2]);open_port(c,4,r.d[0]);
        am_swap(r.d[0]);am_word(r.d[0],r.d[0]+0x20U);open_port(c,2,0x8200);return am_return(c);
    case 0x3918:am_word(r.d[3],r.d[0]);r.pc=0x391a;return true;
    case 0x391a:return am_call(c,0x386e,0x391e);
    case 0x391e:r.pc=(r.d[2]&255U)?0x3928:0x3926;return true;
    case 0x3928:if(!open_target(c,r.a[1]))return false;return am_call(c,r.a[1],0x392a);
    case 0x392a:r.pc=0x391a;return true;
    // MOVEA.L -ee(A5),A2; MOVEA.L (A2),A3; ADDA.W #10,A3; MOVEQ #0,D0; MOVE.B 8(A2),D0;
    // MULU.W #a,D0 (32-bit product); ADDA.W D0,A3 (sign-extended WORD); RTS.
    case 0x9b26:
        if(!open_frame(c) || !am_read(c,r.a[2],4,value))return false;r.a[3]=am_index(value,0x10);
        r.d[0]=0;if(!open_byte(c,r.a[2]+8U,r.d[0]))return false;r.d[0]=(r.d[0]&65535U)*10U;
        r.a[3]=am_index(r.a[3],r.d[0]);return am_return(c);
    case 0x9b3e:
        if(!am_push(c,2,r.d[0]&65535U))return false;return am_call(c,0x9b26,0x9b42);
    // MOVE.W (A7)+,D0; MOVEA.L 4(A3),A0; MOVE.W 8(A3),D1; CMPA.W #0,A0 (full 32-bit).
    case 0x9b42:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,r.a[3]+4U,4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[3]+8U,2,value))return false;am_word(r.d[1],value);
        r.pc=r.a[0]?0x9b54:0x9b56;return true;
    case 0x9b54:if(!open_target(c,r.a[0]))return false;r.pc=r.a[0];return true;
    case 0x9b56:case 0x9b64:case 0x9b78:case 0x9d38:case 0x9d4a:case 0x9e26:case 0x9e92:
    case 0x3926:case 0xa016:case 0xa36e:case 0xbfbc:case 0xc212:case 0xc2c6:return am_return(c);
    case 0x9b58:
        if(!open_frame(c) || !open_byte(c,r.a[2]+4U,r.d[7]))return false;
        r.pc=(r.d[7]&255U)?0x9b66:0x9b64;return true;
    // MOVEA.L (A2),A3; MOVE.W #1,D0; AND.W e(A3),D0; BEQ 9b7a; BNE 9e94.
    case 0x9b66:
        if(!am_read(c,r.a[2],4,value))return false;r.a[3]=value;
        if(!am_read(c,r.a[3]+0xeU,2,value))return false;am_word(r.d[0],value&1U);
        r.pc=(r.d[0]&65535U)?0x9e94:0x9b7a;return true;
    case 0x9b7a:
        if(!am_read(c,am_index(r.a[5],0xff0e),4,value))return false;r.pc=r.a[2]!=value?0x9b8a:0x9b82;return true;
    case 0x9b82:am_word(r.d[0],0x0b00);r.pc=0x9b8e;return true;
    case 0x9b8a:am_word(r.d[0],0x6b00);r.pc=0x9b8e;return true;
    // SWAP; CLR.W; MOVE.B 9(A2); LSL.W #5; ADD.B a(A2) (BYTE); ADDI.W #7000; MOVE.W D0,D3; BSR a018.
    case 0x9b8e:
        am_swap(r.d[0]);am_word(r.d[0],0);if(!open_byte(c,r.a[2]+9U,r.d[0]))return false;
        am_word(r.d[0],(r.d[0]&65535U)<<5);if(!am_read(c,r.a[2]+0xaU,1,value))return false;
        am_byte(r.d[0],r.d[0]+value);am_word(r.d[0],r.d[0]+0x7000U);am_word(r.d[3],r.d[0]);
        return am_call(c,0xa018,0x9ba6);
    case 0x9ba6:return open_carry(c,0x9baa,0x9bbc);
    case 0x9baa:return open_tile(c,1,0xf4,0x9bbc);
    case 0x9bbc:if(!open_byte(c,r.a[2]+0xbU,r.d[6]))return false;r.pc=0x9bc0;return true;
    // CMPI.B #2,D6; BLS: unsigned D6.B <= 2.
    case 0x9bc0:r.pc=(r.d[6]&255U)<=2U?0x9be6:0x9bc8;return true;
    case 0x9bc8:return am_call(c,0xa018,0x9bcc);
    case 0x9bcc:return open_carry(c,0x9bd0,0x9be2);
    case 0x9bd0:return open_tile(c,1,0xf0,0x9be2);
    case 0x9be2:am_byte(r.d[6],r.d[6]-1U);r.pc=0x9bc0;return true;
    case 0x9be6:return am_call(c,0xa018,0x9bea);
    case 0x9bea:return open_carry(c,0x9bee,0x9c00);
    case 0x9bee:return open_tile(c,1,0xf5,0x9c00);
    case 0x9c00:r.pc=(r.d[7]&255U)<=2U?0x9c6e:0x9c08;return true;
    case 0x9c08:case 0x9c6e:
        am_word(r.d[3],r.d[3]+1U);am_word(r.d[0],r.d[3]);
        return am_call(c,0xa018,r.pc==0x9c08?0x9c10:0x9c76);
    case 0x9c10:return open_carry(c,0x9c14,0x9c26);
    case 0x9c14:return open_tile(c,1,0xf2,0x9c26);
    case 0x9c26:if(!open_byte(c,r.a[2]+0xbU,r.d[6]))return false;r.pc=0x9c2a;return true;
    case 0x9c2a:r.pc=(r.d[6]&255U)<=2U?0x9c50:0x9c32;return true;
    case 0x9c32:return am_call(c,0xa018,0x9c36);
    case 0x9c36:return open_carry(c,0x9c3a,0x9c4c);
    case 0x9c3a:return open_tile(c,1,0x60,0x9c4c);
    case 0x9c4c:am_byte(r.d[6],r.d[6]-1U);r.pc=0x9c2a;return true;
    case 0x9c50:return am_call(c,0xa018,0x9c54);
    case 0x9c54:return open_carry(c,0x9c58,0x9c6a);
    case 0x9c58:return open_tile(c,1,0xf3,0x9c6a);
    case 0x9c6a:am_byte(r.d[7],r.d[7]-1U);r.pc=0x9c00;return true;
    case 0x9c76:return open_carry(c,0x9c7a,0x9c8c);
    case 0x9c7a:return open_tile(c,1,0xf6,0x9c8c);
    case 0x9c8c:if(!open_byte(c,r.a[2]+0xbU,r.d[6]))return false;r.pc=0x9c90;return true;
    case 0x9c90:r.pc=(r.d[6]&255U)<=2U?0x9cb6:0x9c98;return true;
    case 0x9c98:return am_call(c,0xa018,0x9c9c);
    case 0x9c9c:return open_carry(c,0x9ca0,0x9cb2);
    case 0x9ca0:return open_tile(c,1,0xf1,0x9cb2);
    case 0x9cb2:am_byte(r.d[6],r.d[6]-1U);r.pc=0x9c90;return true;
    case 0x9cb6:return am_call(c,0xa018,0x9cba);
    case 0x9cba:return open_carry(c,0x9cbe,0x9cd0);
    case 0x9cbe:return open_tile(c,1,0xf7,0x9cd0);
    case 0x9cd0:am_word(r.d[3],r.d[3]+1U);return am_return(c);
    // Separator: bf8, bf9 while D7.B >= 2 (SUBQ.B first, then SUBQ.W), bfa when D7.B == 1.
    case 0x9cd4:return am_call(c,0xa018,0x9cd8);
    case 0x9cd8:return open_carry(c,0x9cdc,0x9cee);
    case 0x9cdc:return open_tile(c,2,0x0bf8,0x9cee);
    case 0x9cee:am_byte(r.d[7],r.d[7]-1U);r.pc=0x9cf0;return true;
    case 0x9cf0:r.pc=(r.d[7]&255U)<2U?0x9d16:0x9cf8;return true;
    case 0x9cf8:return am_call(c,0xa018,0x9cfc);
    case 0x9cfc:return open_carry(c,0x9d00,0x9d12);
    case 0x9d00:return open_tile(c,2,0x0bf9,0x9d12);
    case 0x9d12:am_word(r.d[7],r.d[7]-1U);r.pc=0x9cf0;return true;
    case 0x9d16:r.pc=(r.d[7]&255U)!=1U?0x9d38:0x9d1e;return true;
    case 0x9d1e:return am_call(c,0xa018,0x9d22);
    case 0x9d22:return open_carry(c,0x9d26,0x9d38);
    case 0x9d26:return open_tile(c,2,0x0bfa,0x9d38);
    // MOVE.B #1,D1; ADD.B 8(A2),D1; CMP.B 4(A2),D1; BCS.
    case 0x9d3a:
        am_byte(r.d[1],1);if(!am_read(c,r.a[2]+8U,1,value))return false;am_byte(r.d[1],r.d[1]+value);
        return open_below(c,r.d[1],r.a[2]+4U,0x9d4c,0x9d4a);
    // Row position, flags AND e in D7, item record (A3)=desc+10+8(A2)*a, A0=text LONG.
    case 0x9d4c:
        am_word(r.d[0],0);if(!open_byte(c,r.a[2]+9U,r.d[0]))return false;am_word(r.d[0],(r.d[0]&65535U)<<5);
        if(!am_read(c,r.a[2]+0xaU,1,value))return false;am_byte(r.d[0],r.d[0]+value);
        am_word(r.d[0],r.d[0]+0x7000U);am_word(r.d[0],r.d[0]+0x20U);am_byte(r.d[0],r.d[0]+r.d[1]);
        if(!am_read(c,r.a[2],4,value))return false;r.a[3]=value;
        if(!am_read(c,r.a[3]+0xeU,2,value))return false;am_word(r.d[7],value&0xeU);
        r.a[3]=am_index(r.a[3],0x10);r.d[1]=0;if(!open_byte(c,r.a[2]+8U,r.d[1]))return false;
        r.d[1]=(r.d[1]&65535U)*10U;r.a[3]=am_index(r.a[3],r.d[1]);
        if(!am_read(c,r.a[3],4,value))return false;r.a[0]=value;
        r.pc=r.a[0]==0xfffffffeU?0x9d86:0x9d9a;return true; // CMPA.W #fffe sign-extends.
    // MOVEQ #0,D7; MOVE.B b(A2),D7; SUBQ.W #2,D7; BCS (WORD borrow).
    case 0x9d86:
        r.d[7]=0;if(!open_byte(c,r.a[2]+0xbU,r.d[7]))return false;
        value=r.d[7]&65535U;am_word(r.d[7],value-2U);r.pc=value<2U?0x9d96:0x9d92;return true;
    case 0x9d92:return am_call(c,0x9cd4,0x9d96);
    case 0x9d96:r.pc=0x9e08;return true;
    case 0x9d9a:r.pc=(r.d[7]&255U)?0x9df6:0x9da0;return true;
    case 0x9da0:
        am_swap(r.d[0]);if(!open_byte(c,r.a[2]+8U,r.d[0]) || !am_read(c,r.a[2]+7U,1,value))return false;
        r.pc=(r.d[0]&255U)==value?0x9db6:0x9dae;return true;
    case 0x9dae:am_word(r.d[0],0x00ff);r.pc=0x9dba;return true;
    case 0x9db6:am_word(r.d[0],0x0313);r.pc=0x9dba;return true;
    case 0x9dba:am_swap(r.d[0]);return am_call(c,0xa018,0x9dc0);
    case 0x9dc0:return open_carry(c,0x9dc4,0x9dce);
    case 0x9dc4:am_swap(r.d[0]);open_port(c,4,r.d[0]);am_swap(r.d[0]);r.pc=0x9dce;return true;
    case 0x9dce:am_word(r.d[0],r.d[0]+0x20U);return am_call(c,0xa018,0x9dd6);
    case 0x9dd6:return open_carry(c,0x9dda,0x9df2);
    case 0x9dda:
        am_swap(r.d[0]);if(!open_byte(c,r.a[2]+8U,r.d[7]) || !am_read(c,r.a[2]+7U,1,value))return false;
        r.pc=(r.d[7]&255U)!=value?0x9dea:0x9de8;return true;
    case 0x9de8:am_byte(r.d[0],r.d[0]+1U);r.pc=0x9dea;return true;
    case 0x9dea:open_port(c,4,r.d[0]);am_swap(r.d[0]);r.pc=0x9df2;return true;
    case 0x9df2:am_word(r.d[0],r.d[0]+0x20U);r.pc=0x9df6;return true;
    case 0x9df6:r.pc=r.a[0]?0x9dfe:0x9e08;return true;
    case 0x9dfe:return am_call(c,0x9f7c,0x9e02);
    case 0x9e02:return am_call(c,0x3918,0x9e08);
    // MOVE.W #5,D0; MOVEM.L A1-A3,-(A7) (memory ascending A1,A2,A3); BSR 9b3e.
    case 0x9e08:
        am_word(r.d[0],5);
        if(!am_push(c,4,r.a[3]) || !am_push(c,4,r.a[2]) || !am_push(c,4,r.a[1]))return false;
        return am_call(c,0x9b3e,0x9e14);
    case 0x9e14:
        if(!am_pop(c,4,r.a[1]) || !am_pop(c,4,r.a[2]) || !am_pop(c,4,r.a[3]))return false;return am_return(c);
    case 0x9e1a:
        if(!open_frame(c) || !am_read(c,r.a[2]+4U,1,value))return false;r.pc=value?0x9e28:0x9e26;return true;
    case 0x9e28:
        if(!am_read(c,r.a[2],4,value))return false;r.a[3]=value;
        if(!am_read(c,r.a[3],4,value))return false;r.a[0]=value;r.pc=r.a[0]?0x9e34:0x9e78;return true;
    case 0x9e34:return am_call(c,0x38e8,0x9e3a);
    // NEG.B; ADD.B b(A2); ASR.B #1 (signed); ADD.B 9(A2); ANDI.W #ff; LSL.W #5; ADD.B a(A2); ADDI.W #7000.
    case 0x9e3a:
        am_byte(r.d[0],0U-(r.d[0]&255U));if(!am_read(c,r.a[2]+0xbU,1,value))return false;am_byte(r.d[0],r.d[0]+value);
        value=r.d[0]&255U;am_byte(r.d[0],(value>>1)|(value&0x80U));
        if(!am_read(c,r.a[2]+9U,1,value))return false;am_byte(r.d[0],r.d[0]+value);
        am_word(r.d[0],r.d[0]&0xffU);am_word(r.d[0],(r.d[0]&65535U)<<5);
        if(!am_read(c,r.a[2]+0xaU,1,value))return false;am_byte(r.d[0],r.d[0]+value);am_word(r.d[0],r.d[0]+0x7000U);
        if(!am_read(c,r.a[3],4,value))return false;r.a[0]=value;r.pc=r.a[0]?0x9e5e:0x9e78;return true;
    case 0x9e5e:
        if(!am_read(c,am_index(r.a[5],0xff0e),4,value))return false;r.pc=r.a[2]!=value?0x9e6e:0x9e66;return true;
    case 0x9e66:am_word(r.d[1],0x0103);r.pc=0x9e72;return true;
    case 0x9e6e:am_word(r.d[1],0x0603);r.pc=0x9e72;return true;
    case 0x9e72:return am_call(c,0x3918,0x9e78);
    case 0x9e78:r.d[0]=0;r.pc=0x9e7a;return true;
    // CMP.B 6(A2),D0; BCC: D0.B >= item count (unsigned).
    case 0x9e7a:return open_below(c,r.d[0],r.a[2]+6U,0x9e82,0x9e92);
    case 0x9e82:
        if(!am_write(c,r.a[2]+8U,1,r.d[0]&255U))return false;return am_call(c,0x9d3a,0x9e8a);
    case 0x9e8a:
        if(!open_byte(c,r.a[2]+8U,r.d[0]))return false;am_byte(r.d[0],r.d[0]+1U);r.pc=0x9e7a;return true;
    case 0x9f7c:
        if(!am_read(c,am_index(r.a[5],0xff0e),4,value))return false;r.pc=r.a[2]==value?0x9f96:0x9f84;return true;
    case 0x9f84:
        if(!open_byte(c,r.a[2]+7U,r.d[7]) || !am_read(c,r.a[2]+8U,1,value))return false;
        r.pc=(r.d[7]&255U)==value?0x9f96:0x9f90;return true;
    case 0x9f90:am_word(r.d[1],0x0603);return am_return(c);
    // MOVE.L A3,-(A7); MOVEA.L (A2),A3; MOVE.W e(A3),D1; MOVEA.L (A7)+,A3; ANDI.W #e; CMPI.W #2.
    case 0x9f96:
        if(!am_push(c,4,r.a[3]) || !am_read(c,r.a[2],4,value))return false;r.a[3]=value;
        if(!am_read(c,r.a[3]+0xeU,2,value))return false;am_word(r.d[1],value);
        if(!am_pop(c,4,value))return false;r.a[3]=value;am_word(r.d[1],r.d[1]&0xeU);
        r.pc=(r.d[1]&65535U)!=2U?0x9fbe:0x9fac;return true;
    case 0x9fac:
        if(!open_byte(c,r.a[2]+7U,r.d[1]) || !am_read(c,r.a[2]+8U,1,value))return false;
        r.pc=(r.d[1]&255U)==value?0x9fbe:0x9fb8;return true;
    case 0x9fb8:am_word(r.d[1],0x0b03);return am_return(c);
    case 0x9fbe:am_word(r.d[1],0x0003);return am_return(c);
    // Renderer a008: covered cell returns at a016; otherwise MOVE.L -ea(A5),-(A7); RTS.
    case 0xa008:return am_call(c,0xa018,0xa00c);
    case 0xa00c:return open_carry(c,0xa010,0xa016);
    case 0xa010:
        if(!am_read(c,am_index(r.a[5],0xff16),4,value) || !am_push(c,4,value))return false;return am_return(c);
    // MOVEM.L D5-D7/A0-A1,-(A7): memory ascending D5,D6,D7,A0,A1. D7=D0-7000, D6=D7>>5 (LSR.W),
    // D7&=1f; A0=LONG 107f12 (-ee), A1=LONG 107f0e (-f2); SUBA.W #10,A0.
    case 0xa018:
        if(!am_push(c,4,r.a[1]) || !am_push(c,4,r.a[0]) || !am_push(c,4,r.d[7]) ||
           !am_push(c,4,r.d[6]) || !am_push(c,4,r.d[5]))return false;
        am_word(r.d[7],r.d[0]);am_word(r.d[7],r.d[7]-0x7000U);am_word(r.d[6],r.d[7]);
        am_word(r.d[6],(r.d[6]&65535U)>>5);am_word(r.d[7],r.d[7]&0x1fU);
        if(!am_read(c,0x107f12,4,value))return false;r.a[0]=value;
        if(!am_read(c,0x107f0e,4,value))return false;r.a[1]=value;
        r.a[0]-=0x10U;r.pc=0xa03a;return true;
    // CMPA.L A0,A1; BHI: unsigned A1 > A0 ends the scan uncovered.
    case 0xa03a:r.pc=r.a[1]>r.a[0]?0xa06c:0xa040;return true;
    case 0xa040:
        if(!am_read(c,r.a[0]+0xfU,1,value))return false;r.pc=(value&1U)?0xa066:0xa04a;return true;
    // MOVE.B D6,D5; SUB.B 9(A0),D5; CMP.B b(A0),D5; BCC.
    case 0xa04a:
        am_byte(r.d[5],r.d[6]);if(!am_read(c,r.a[0]+9U,1,value))return false;am_byte(r.d[5],r.d[5]-value);
        if(!am_read(c,r.a[0]+0xbU,1,value))return false;r.pc=(r.d[5]&255U)>=value?0xa066:0xa058;return true;
    // MOVE.B D7,D5; SUB.B a(A0),D5; CMP.B 4(A0),D5; BCS.
    case 0xa058:
        am_byte(r.d[5],r.d[7]);if(!am_read(c,r.a[0]+0xaU,1,value))return false;am_byte(r.d[5],r.d[5]-value);
        return open_below(c,r.d[5],r.a[0]+4U,0xa076,0xa066);
    case 0xa066:r.a[0]-=0x10U;r.pc=0xa03a;return true;
    case 0xa06c:return open_a018_return(c,AnimationCarryClear); // ANDI #fe,CCR
    case 0xa076:return open_a018_return(c,AnimationCarrySet);   // ORI #1,CCR
    // Item callback YES (D0=6): cursor step. Original 7(A2) pushed as a BYTE (A7-2, even address).
    case 0xa216:
        if(!open_frame(c) || !am_read(c,r.a[2]+7U,1,value) || !am_push(c,1,value))return false;r.pc=0xa21e;return true;
    case 0xa21e:
        if(!open_byte(c,r.a[2]+7U,r.d[0]) || !am_read(c,r.a[2]+0xfU,1,value))return false;
        r.pc=(value&2U)?0xa23c:0xa22c;return true;
    case 0xa22c:
        am_byte(r.d[0],r.d[0]+1U);return open_below(c,r.d[0],r.a[2]+6U,0xa238,0xa236);
    case 0xa236:r.d[0]=0;r.pc=0xa238;return true;
    case 0xa238:r.pc=0xa246;return true;
    // SUBQ.B #1,D0; BCC: borrow only when D0.B was 0.
    case 0xa23c:value=r.d[0]&255U;am_byte(r.d[0],value-1U);r.pc=value?0xa246:0xa242;return true;
    case 0xa242:
        if(!am_read(c,r.a[2]+6U,1,value))return false;am_byte(r.d[0],r.d[0]+value);r.pc=0xa246;return true;
    case 0xa246:
        if(!am_write(c,r.a[2]+7U,1,r.d[0]&255U) || !am_write(c,r.a[2]+8U,1,r.d[0]&255U))return false;
        return am_call(c,0x9b26,0xa252);
    case 0xa252:
        if(!am_read(c,r.a[3]+4U,4,value))return false;r.d[0]=value;r.pc=value?0xa258:0xa21e;return true;
    case 0xa258:
        if(!am_read(c,r.a[3],4,value))return false;r.d[0]=value;r.pc=value==0xfffffffeU?0xa21e:0xa262;return true;
    // LEA a008,A1; MOVE.B (A7)+,8(A2): BYTE at the even A7, A7+2.
    case 0xa262:
        r.a[1]=0xa008;if(!am_pop(c,1,value) || !am_write(c,r.a[2]+8U,1,value))return false;
        return am_call(c,0x9d3a,0xa26e);
    case 0xa26e:if(!open_cursor(c))return false;return am_call(c,0x9d3a,0xa278);
    case 0xa278:if(!am_write(c,r.a[2]+0xeU,1,0))return false;return am_return(c);
    case 0xa348:r.a[1]=0xa008;return am_call(c,0x9b58,0xa350);
    // MOVEQ #0,D0; MOVE.B c(A2),D0; LSL.W #6; ADD.W D0,4(A2) (WORD incl. byte 5);
    // MOVE.B c(A2),D0; LSL.W #8; CMP.W 4(A2),D0; BCC (unsigned D0.W >= WORD).
    case 0xa350:
        r.d[0]=0;if(!open_byte(c,r.a[2]+0xcU,r.d[0]))return false;am_word(r.d[0],(r.d[0]&65535U)<<6);
        if(!am_read(c,r.a[2]+4U,2,value) || !am_write(c,r.a[2]+4U,2,(value+r.d[0])&65535U))return false;
        if(!open_byte(c,r.a[2]+0xcU,r.d[0]))return false;am_word(r.d[0],(r.d[0]&65535U)<<8);
        if(!am_read(c,r.a[2]+4U,2,value))return false;r.pc=(r.d[0]&65535U)>=value?0xa36e:0xa36a;return true;
    case 0xa36a:if(!am_write(c,r.a[2]+4U,2,r.d[0]&65535U))return false;r.pc=0xa36e;return true;
    // LEA 108000,A5; MOVEA.L #107f0e,A2; SUBA.W #10,A2.
    case 0xa370:r.a[5]=0x108000;r.a[2]=0x107efeU;r.pc=0xa380;return true;
    // CMPA.L -f2(A5),A2; BCS: unsigned A2 < -f2.
    case 0xa380:
        if(!am_read(c,am_index(r.a[5],0xff0e),4,value))return false;r.pc=r.a[2]<value?0xa3d0:0xa388;return true;
    case 0xa388:
        if(!am_push(c,4,r.a[2]) || !am_write(c,am_index(r.a[5],0xff12),4,r.a[2]) ||
           !am_read(c,am_index(r.a[5],0xff0e),4,value))return false;
        r.pc=r.a[2]==value?0xa3b8:0xa396;return true;
    case 0xa396:
        if(!am_read(c,r.a[2]+0xfU,1,value))return false;r.pc=(value&1U)?0xa3a0:0xa3b8;return true;
    case 0xa3a0:if(!open_byte(c,r.a[2]+4U,r.d[0]))return false;r.pc=(r.d[0]&255U)?0xa3a8:0xa3b8;return true;
    case 0xa3a8:return am_call(c,0xa2be,0xa3ac);
    case 0xa3ac:if(!am_read(c,r.a[2]+4U,1,value))return false;r.pc=value?0xa3b8:0xa3b4;return true;
    case 0xa3b4:return am_call(c,0xa6da,0xa3b8);
    // MOVEA.L (A2),A3; MOVEA.L a(A3),A4; CMPA.W #0,A4 (full 32-bit).
    case 0xa3b8:
        if(!am_read(c,r.a[2],4,value))return false;r.a[3]=value;
        if(!am_read(c,r.a[3]+0xaU,4,value))return false;r.a[4]=value;r.pc=r.a[4]?0xa3c6:0xa3c8;return true;
    case 0xa3c6:if(!open_target(c,r.a[4]))return false;return am_call(c,r.a[4],0xa3c8);
    case 0xa3c8:if(!am_pop(c,4,value))return false;r.a[2]=value-0x10U;r.pc=0xa380;return true;
    case 0xa3d0:
        if(!am_read(c,am_index(r.a[5],0xff0e),4,value))return false;r.a[2]=value;
        r.pc=r.a[2]<0x107f0eU?0xa3e2:0xa3de;return true;
    case 0xa3de:case 0xa402:r.d[0]=0xffffffffU;return am_return(c);
    case 0xa3e2:
        if(!am_write(c,am_index(r.a[5],0xff12),4,r.a[2]) || !open_byte(c,am_index(r.a[5],0xff1b),r.d[0]))return false;
        r.pc=(r.d[0]&255U)==1U?0xa5d2:0xa3f2;return true;
    case 0xa3f2:r.pc=(r.d[0]&255U)==2U?0xa662:0xa3fa;return true;
    case 0xa3fa:r.pc=(r.d[0]&255U)==0U?0xa406:0xa402;return true;
    // Opening: 4(A2) BYTE below c(A2) grows by a348; otherwise the first full draw at a5ea.
    case 0xa5d2:
        if(!am_write(c,am_index(r.a[5],0xff12),4,r.a[2]) || !open_byte(c,r.a[2]+4U,r.d[7]))return false;
        if(!am_read(c,r.a[2]+0xcU,1,value))return false;r.pc=(r.d[7]&255U)>=value?0xa5ea:0xa5e2;return true;
    case 0xa5e2:return am_call(c,0xa348,0xa5e6);
    case 0xa5e6:case 0xa65e:r.d[0]=0;return am_return(c);
    case 0xa5ea:
        if(!am_write(c,am_index(r.a[5],0xff1b),1,0) || !open_frame(c))return false;r.pc=0xa5f4;return true;
    case 0xa5f4:if(!open_cursor(c))return false;return am_call(c,0x9b26,0xa5fe);
    case 0xa5fe:if(!am_read(c,r.a[3]+4U,4,value))return false;r.pc=value?0xa61c:0xa606;return true;
    case 0xa606:
        if(!open_byte(c,r.a[2]+7U,r.d[0]))return false;am_byte(r.d[0],r.d[0]+1U);
        return open_below(c,r.d[0],r.a[2]+6U,0xa616,0xa614);
    case 0xa614:r.d[0]=0;r.pc=0xa616;return true;
    case 0xa616:if(!am_write(c,r.a[2]+7U,1,r.d[0]&255U))return false;r.pc=0xa5f4;return true;
    case 0xa61c:
        if(!am_read(c,am_index(r.a[5],0xff16),4,value))return false;r.a[1]=value;return am_call(c,0x9b58,0xa624);
    case 0xa624:return am_call(c,0x9e1a,0xa628);
    // CMPI.L #ffffffff,(desc+10): an empty item list reaches TRAP #f at a63c.
    case 0xa628:
        if(!open_frame(c) || !am_read(c,r.a[2],4,value))return false;r.a[3]=am_index(value,0x10);
        if(!am_read(c,r.a[3],4,value))return false;r.pc=value==0xffffffffU?0xa63c:0xa63e;return true;
    case 0xa63e:if(!open_cursor(c))return false;am_word(r.d[0],6);return am_call(c,0x9b3e,0xa64c);
    case 0xa64c:if(!open_frame(c) || !open_cursor(c))return false;am_word(r.d[0],0);return am_call(c,0x9b3e,0xa65e);
    // MOVE.W D0,-(A7); MOVE.W D1,-(A7); CMPI.W #0,D0; BNE.
    case 0xa73e:
        if(!am_push(c,2,r.d[0]&65535U) || !am_push(c,2,r.d[1]&65535U))return false;
        r.pc=(r.d[0]&65535U)?0xa754:0xa74a;return true;
    case 0xa74a:am_word(r.d[0],0x1a6c);return am_call(c,0x3af8,0xa754);
    case 0xa754:
        if(!am_pop(c,2,value))return false;am_word(r.d[1],value);
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);return am_return(c);
    case 0xbf94:return am_call(c,0xa73e,0xbf9a);
    case 0xbf9a:r.pc=(r.d[0]&65535U)!=6U?0xbfa8:0xbfa2;return true;
    case 0xbfa2:if(!am_write(c,r.a[6]+0x7eU,2,0x001e))return false;r.pc=0xbfa8;return true;
    case 0xbfa8:r.pc=(r.d[0]&65535U)!=3U?0xbfbc:0xbfb0;return true;
    case 0xbfb0:if(!am_write(c,r.a[6]+0x80U,1,0xff))return false;r.pc=0xa70a;return true;
    case 0xc1c4:return am_call(c,0xa73e,0xc1ca);
    case 0xc1ca:r.pc=(r.d[0]&65535U)!=6U?0xc1de:0xc1d2;return true;
    case 0xc1d2:if(!am_write(c,r.a[6]+0x7eU,2,0x012c))return false;r.pc=0xa216;return true;
    case 0xc1de:r.pc=(r.d[0]&65535U)!=3U?0xc212:0xc1e6;return true;
    case 0xc1e6:return am_call(c,0xbd26,0xc1ea);
    case 0xc1ee:case 0xc202:return am_call(c,0x9f36,r.pc==0xc1ee?0xc1f4:0xc208);
    case 0xc1f4:r.a[0]=0xc214;return am_call(c,0xa71a,0xc1fe);
    case 0xc1fe:r.pc=0xc212;return true;
    case 0xc208:r.a[0]=0xc232;return am_call(c,0xa71a,0xc212);
    // c2c0 TST.B D0; BNE c2c8 (close unit); c2c6 RTS.
    case 0xc2c0:r.pc=(r.d[0]&255U)?0xc2c8:0xc2c6;return true;
    // CMPI.B #10,D1; BCC e84d6 (kana renderer, no executor); JMP 3650.
    case 0xe84c8:r.pc=(r.d[1]&255U)>=0x10U?0xe84d6:0xe84d0;return true;
    case 0xe84d0:r.pc=0x3650;return true;
    default:return am_error(c,"unsupported animation card menu open PC");
    }
}
}
