#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t ON13_BANK_190=0x200190;       // MOVE.L 200190.L,22(A6) (5aa40 5b226; banked window LONG, live bus).
std::uint32_t on13_w(std::uint32_t v) {return v&65535U;}
std::uint32_t on13_b(std::uint32_t v) {return v&255U;}
bool on13_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on13_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// MOVE.x d16(As),d16(Ad) (read, then write).
bool on13_copy(AnimationMachineContext& c,std::uint32_t src,std::uint32_t src_d,std::uint32_t dst,std::uint32_t dst_d,unsigned int size) {
    std::uint32_t value=0;if(!on13_get(c,src,src_d,size,value))return false;return on13_put(c,dst,dst_d,size,value);
}
// Two's complement value of a WORD / LONG as a 64-bit signed number (no signed overflow, no implementation-defined conversion).
std::int64_t on13_sw(std::uint32_t v) {const std::int64_t x=static_cast<std::int64_t>(v&65535U);return (v&0x8000U)?x-65536:x;}
std::int64_t on13_sl(std::uint32_t v) {const std::int64_t x=static_cast<std::int64_t>(v);return (v&0x80000000U)?x-4294967296LL:x;}
// EXT.W of a BYTE (sign-extended BYTE as a WORD).
std::uint32_t on13_ext_b(std::uint32_t v) {return (v&0x80U)?((v&255U)|0xff00U):(v&255U);}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool on13_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n13 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #value,(A6), then continue at next_pc.
bool on13_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,value))return false;c.s.pc=next_pc;return true;
}
// BTST.B #bit,d16(An): bit value (Z is its inverse).
bool on13_btst(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!on13_get(c,base,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,d16(An) (BYTE read-modify-write; old bit returned for Z).
bool on13_bchange(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool set_bit,bool& old) {
    std::uint32_t value=0;if(!on13_get(c,base,displacement,1,value))return false;old=((value>>bit)&1U)!=0U;
    const std::uint32_t mask=1U<<bit;return on13_put(c,base,displacement,1,set_bit?((value|mask)&255U):(value&~mask&255U));
}
// MOVEQ #0,Dn; MOVE.W 86(A6),Dn; SWAP Dn (the WORD in the high half).
bool on13_target(AnimationMachineContext& c,std::uint32_t& d) {
    std::uint32_t value=0;if(!on13_get(c,c.s.a[6],0x86,2,value))return false;d=on13_w(value)<<16;return true;
}
// MOVE.W #k,D0; MOVE.B #0,D1; JSR 8ebe.L.
bool on13_part(AnimationMachineContext& c,std::uint32_t k,std::uint32_t return_pc) {
    am_word(c.s.d[0],k);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #k,68(An); MOVE.W #k,1e(An).
bool on13_frame(AnimationMachineContext& c,std::uint32_t base,std::uint32_t k) {
    return on13_put(c,base,0x68,2,k) && on13_put(c,base,0x1e,2,k);
}
// MOVEA.L #list,A1; MOVE.W #100,D0; JSR 49f8c.L.
bool on13_animation(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W #183,20(A6); MOVE.L 200190.L,22(A6) (banked LONG through the live bus).
bool on13_bank_animation(AnimationMachineContext& c) {
    std::uint32_t value=0;
    return on13_put(c,c.s.a[6],0x20,2,0x183) && am_read(c,ON13_BANK_190,4,value) && on13_put(c,c.s.a[6],0x22,4,value);
}
// DIVU.W divisor,Dn (68000): zero divisor -> checked error (the original takes the vector 5 exception, not modeled); quotient > ffff
// sets V and leaves Dn unchanged; otherwise Dn = remainder:quotient. C is cleared and X kept (no consumer here).
bool on13_divu(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t divisor) {
    const std::uint32_t v=on13_w(divisor);
    if(v==0U)return am_error(c,"objects n13 DIVU zero divisor");
    const std::uint32_t quotient=d/v,remainder=d%v;
    if(quotient>65535U)return true;
    d=(remainder<<16)|quotient;return true;
}
}
// Objects F4 N13 (175 block starts): the node callback 59ea2 (installed 59ed6, shared 5a802 with installed 5a880, the installed
// chain 5a8dc and 5a9ae, shared tail 5a9c2), the helpers 5aa3a (banked animation 200190, 28ae child 5b220) and 5ab5a (returns the C
// of 49fc6), the interpreter command callbacks 5ab16 5ab1c 5ab22 5ab3a, the 28ae child 5b220 (installed 5b2ae; ADDX 5b356, DIVU
// 5b442 5b454, N recomputed at 5b326 from its unique predecessor 5b316), the 28ae child d3580 (installed d35ce), the helpers d3ab8
// d3ae8 d3b1a and the node callback dbfac. Consumers 5a8be (5ab5a/49fc6), 5aa2c (4b54e), 5b2b4 d3608 (288c), 5b3d0 (28ae) and
// 5b48c (4a46c). No known-carry producer. Boundaries without an executor: 482fa d3802 1a3ac.
bool animation_objects_n13_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool flag=false;
    switch(r.pc) {
    // ---- 59ea2: MOVE.W #100,2e(A6); MOVE.W #80,32(A6); JSR 4c0ac.L.
    case 0x59ea2:if(!on13_put(c,r.a[6],0x2e,2,0x100) || !on13_put(c,r.a[6],0x32,2,0x80))return false;return am_call(c,0x4c0ac,0x59eb4);
    // MOVE.W 32(A6),86(A6); JSR 5aa3a(PC).
    case 0x59eb4:if(!on13_copy(c,r.a[6],0x32,r.a[6],0x86,2))return false;return am_call(c,0x5aa3a,0x59ebe);
    case 0x59ebe:r.pc=0x59ec2;return true;                                                // BRA.W 59ec2.
    // MOVE.W #280,2e(A6); MOVE.L #fffe0000,36(A6); MOVE.L #59ed6,(A6).
    case 0x59ec2:
        if(!on13_put(c,r.a[6],0x2e,2,0x280) || !on13_put(c,r.a[6],0x36,4,0xfffe0000U))return false;return on13_install(c,0x59ed6,0x59ed6);
    // BTST.B #0,80(A6); BNE.W 5a802.
    case 0x59ed6:if(!on13_btst(c,r.a[6],0x80,0,flag))return false;r.pc=flag?0x5a802:0x59ee0;return true;
    case 0x59ee0:return am_call(c,0x43ea4,0x59ee6);
    // MOVE.L #1780000,D0; CMP.L 2e(A6),D0; BLE.W 59f12 (signed LONG D0 <= 2e).
    case 0x59ee6:
        r.d[0]=0x1780000U;if(!on13_get(c,r.a[6],0x2e,4,value))return false;r.pc=on13_sl(r.d[0])<=on13_sl(value)?0x59f12:0x59ef4;return true;
    // MOVE.L D0,2e(A6); MOVE.W #743,D0; JSR 3af8.L.
    case 0x59ef4:if(!on13_put(c,r.a[6],0x2e,4,r.d[0]))return false;am_word(r.d[0],0x743);return am_call(c,0x3af8,0x59f02);
    case 0x59f02:am_word(r.d[0],0x19d4);return am_call(c,0x3af8,0x59f0c);                 // MOVE.W #19d4,D0; JSR 3af8.L.
    case 0x59f0c:return on13_install(c,0x5a376,0x59f12);                                  // MOVE.L #5a376,(A6).
    case 0x59f12:case 0x5a7fa:case 0x5a8ba:return am_call(c,0x5ab5a,r.pc+4U);             // BSR.W 5ab5a.
    case 0x59f16:case 0x5a7fe:r.pc=0x5a9c2;return true;                                   // BRA.W 5a9c2.

    // ---- 5a7c8 (installed outside the range): BTST.B #0,80(A6); BNE.W 5a802; JSR 43ea4.L.
    case 0x5a7c8:if(!on13_btst(c,r.a[6],0x80,0,flag))return false;r.pc=flag?0x5a802:0x5a7d2;return true;
    case 0x5a7d2:return am_call(c,0x43ea4,0x5a7d8);
    // MOVE.L #1780000,D0; CMP.L 2e(A6),D0; BGE.W 5a7fa (signed LONG D0 >= 2e).
    case 0x5a7d8:
        r.d[0]=0x1780000U;if(!on13_get(c,r.a[6],0x2e,4,value))return false;r.pc=on13_sl(r.d[0])>=on13_sl(value)?0x5a7fa:0x5a7e6;return true;
    case 0x5a7e6:am_word(r.d[0],0x743);return am_call(c,0x3af8,0x5a7f0);                  // MOVE.W #743,D0; JSR 3af8.L.
    // MOVE.L D0,2e(A6); MOVE.L #5a376,(A6).
    case 0x5a7f0:if(!on13_put(c,r.a[6],0x2e,4,r.d[0]))return false;return on13_install(c,0x5a376,0x5a7fa);

    // ---- 5a802: ST.B 5d44(A5); JSR 482fa.L (boundary).
    case 0x5a802:if(!on13_put(c,r.a[5],0x5d44,1,0xff))return false;return am_call(c,0x482fa,0x5a80c);
    // BSET.B #4,80(A6); MOVE.W #20,7a(A6); JSR 4b6ec.L.
    case 0x5a80c:if(!on13_bchange(c,r.a[6],0x80,4,true,flag) || !on13_put(c,r.a[6],0x7a,2,0x20))return false;return am_call(c,0x4b6ec,0x5a81e);
    case 0x5a81e:am_word(r.d[0],0x743);return am_call(c,0x3af8,0x5a828);                  // MOVE.W #743,D0; JSR 3af8.L.
    case 0x5a828:return am_call(c,0x46ef4,0x5a82e);
    case 0x5a82e:r.a[1]=0x5b5e6;return am_call(c,0xd3802,0x5a838);                        // LEA 5b5e6(PC),A1; JSR d3802.L (boundary).
    // MOVE.W #e0ed,68(A0); MOVE.W #e0ed,1e(A0); MOVEA.L #5c40e,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x5a838:if(!on13_frame(c,r.a[0],0xe0ed))return false;return on13_animation(c,0x5c40e,0x5a854);
    case 0x5a854:return am_call(c,0x496c2,0x5a85a);
    // MOVE.L #80000,36(A6); MOVEQ #0,D0; MOVE.W 86(A6),D0; SWAP D0; CMP.L 32(A6),D0; BEQ.W 5a87a.
    case 0x5a85a:
        if(!on13_put(c,r.a[6],0x36,4,0x80000U) || !on13_target(c,r.d[0]) || !on13_get(c,r.a[6],0x32,4,value))return false;
        r.pc=r.d[0]==value?0x5a87a:0x5a872;return true;
    case 0x5a872:if(!on13_put(c,r.a[6],0x3a,4,0x40000U))return false;r.pc=0x5a87a;return true; // MOVE.L #40000,3a(A6).
    case 0x5a87a:return on13_install(c,0x5a880,0x5a880);                                  // MOVE.L #5a880,(A6).
    case 0x5a880:return am_call(c,0x43ea4,0x5a886);
    // MOVE.L 36(A6),D0; ASR.L #3,D0; SUB.L D0,36(A6); TST.L 3a(A6); BEQ.W 5a8ba.
    case 0x5a886:
        if(!on13_get(c,r.a[6],0x36,4,value))return false;
        r.d[0]=(value>>3)|((value&0x80000000U)?0xe0000000U:0U);
        if(!on13_put(c,r.a[6],0x36,4,(value-r.d[0])&0xffffffffU) || !on13_get(c,r.a[6],0x3a,4,value))return false;
        r.pc=value==0U?0x5a8ba:0x5a898;return true;
    // ADDI.L #ffffb0fe,3a(A6); MOVEQ #0,D0; MOVE.W 86(A6),D0; SWAP D0; MOVE.L 32(A6),D1; CMP.L D1,D0; BLE.W 5a8ba (signed D0 <= D1).
    case 0x5a898:
        if(!on13_get(c,r.a[6],0x3a,4,value) || !on13_put(c,r.a[6],0x3a,4,(value+0xffffb0feU)&0xffffffffU))return false;
        if(!on13_target(c,r.d[0]) || !on13_get(c,r.a[6],0x32,4,value))return false;r.d[1]=value;
        r.pc=on13_sl(r.d[0])<=on13_sl(r.d[1])?0x5a8ba:0x5a8b2;return true;
    // MOVE.L D0,32(A6); CLR.L 3a(A6).
    case 0x5a8b2:if(!on13_put(c,r.a[6],0x32,4,r.d[0]) || !on13_put(c,r.a[6],0x3a,4,0))return false;r.pc=0x5a8ba;return true;
    case 0x5a8be:return on13_consume(c,false,0x5a8d8,0x5a8c2);                             // BCC.W 5a8d8 (C of 5ab5a / 49fc6).
    // MOVEQ #0,D0; MOVE.W 86(A6),D0; SWAP D0; CMP.L 32(A6),D0; BNE.W 5a8d8.
    case 0x5a8c2:
        if(!on13_target(c,r.d[0]) || !on13_get(c,r.a[6],0x32,4,value))return false;r.pc=r.d[0]!=value?0x5a8d8:0x5a8d2;return true;
    case 0x5a8d2:return on13_install(c,0x5a8dc,0x5a8d8);                                  // MOVE.L #5a8dc,(A6).
    case 0x5a8d8:case 0x5a9b8:r.pc=0x5aa34;return true;                                   // BRA.W 5aa34.

    // ---- 5a8dc (installed): BSET.B #3,80(A6); JSR 1a3ac.L (boundary).
    case 0x5a8dc:if(!on13_bchange(c,r.a[6],0x80,3,true,flag))return false;return am_call(c,0x1a3ac,0x5a8e8);
    case 0x5a8e8:r.a[1]=0x5b5d4;return am_call(c,0xd3802,0x5a8f2);                        // LEA 5b5d4(PC),A1; JSR d3802.L.
    // MOVE.W #e0ed,68(A0); MOVE.W #e0ed,1e(A0); MOVEA.L #5ab6c,A0; MOVE.W #0,D0; JSR 28ae.L.
    case 0x5a8f2:if(!on13_frame(c,r.a[0],0xe0ed))return false;r.a[0]=0x5ab6c;am_word(r.d[0],0);return am_call(c,0x28ae,0x5a90e);
    // MOVE.W #3c,76(A0); LEA 5b60a(PC),A1; JSR d3802.L.
    case 0x5a90e:if(!on13_put(c,r.a[0],0x76,2,0x3c))return false;r.a[1]=0x5b60a;return am_call(c,0xd3802,0x5a91e);
    // MOVE.W #e0ea,68(A0); MOVE.W #e0ea,1e(A0); LEA 5b5f8(PC),A1; JSR d3802.L.
    case 0x5a91e:if(!on13_frame(c,r.a[0],0xe0ea))return false;r.a[1]=0x5b5f8;return am_call(c,0xd3802,0x5a934);
    // MOVE.W #e0ed,68(A0); MOVE.W #e0ed,1e(A0); LEA 5b5e6(PC),A1; JSR d3802.L.
    case 0x5a934:if(!on13_frame(c,r.a[0],0xe0ed))return false;r.a[1]=0x5b5e6;return am_call(c,0xd3802,0x5a94a);
    // MOVE.W #e0ec,68(A0); MOVE.W #e0ec,1e(A0); JSR 8ff4.L.
    case 0x5a94a:if(!on13_frame(c,r.a[0],0xe0ec))return false;return am_call(c,0x8ff4,0x5a95c);
    case 0x5a95c:return on13_part(c,0xd3e,0x5a96a);
    case 0x5a96a:return on13_part(c,0xd3f,0x5a978);
    case 0x5a978:return on13_part(c,0xd40,0x5a986);
    // MOVE.B 19(A6),14(A6); MOVEA.L #5cef4,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x5a986:if(!on13_copy(c,r.a[6],0x19,r.a[6],0x14,1))return false;return on13_animation(c,0x5cef4,0x5a99c);
    case 0x5a99c:return am_call(c,0x496c2,0x5a9a2);
    case 0x5a9a2:return am_call(c,0x4b6ec,0x5a9a8);
    case 0x5a9a8:return on13_install(c,0x5a9ae,0x5a9ae);                                  // MOVE.L #5a9ae,(A6).
    // ---- 5a9ae (installed): JSR 43ea4.L; BSR.W 5ab5a; BRA.W 5aa34.
    case 0x5a9ae:return am_call(c,0x43ea4,0x5a9b4);
    case 0x5a9b4:return am_call(c,0x5ab5a,0x5a9b8);

    // ---- 5a9c2: TST.L 7c(A6); BEQ.W 5a9e4.
    case 0x5a9c2:if(!on13_get(c,r.a[6],0x7c,4,value))return false;r.pc=value==0U?0x5a9e4:0x5a9ca;return true;
    // MOVEA.L 7c(A6),A0; MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B 88(A6),D0; MOVE.B 89(A6),D1; EXT.W D0; EXT.W D1; JSR 47070.L.
    case 0x5a9ca:
        if(!on13_get(c,r.a[6],0x7c,4,value))return false;r.a[0]=value;
        if(!on13_get(c,r.a[6],0x88,1,value) || !on13_get(c,r.a[6],0x89,1,other))return false;
        r.d[0]=on13_ext_b(value);r.d[1]=on13_ext_b(other);return am_call(c,0x47070,0x5a9e4);
    // MOVE.W 54(A6),D0; CMP.W 82(A6),D0; BCC.W 5aa04 (unsigned D0.W >= 82).
    case 0x5a9e4:
        if(!on13_get(c,r.a[6],0x54,2,value) || !on13_get(c,r.a[6],0x82,2,other))return false;am_word(r.d[0],value);
        r.pc=value>=other?0x5aa04:0x5a9f0;return true;
    // BSET.B #1,80(A6); BNE.W 5aa04 (the old bit).
    case 0x5a9f0:if(!on13_bchange(c,r.a[6],0x80,1,true,flag))return false;r.pc=flag?0x5aa04:0x5a9fa;return true;
    // ST.B 81(A6); MOVE.L #5a5ca,(A6).
    case 0x5a9fa:if(!on13_put(c,r.a[6],0x81,1,0xff))return false;return on13_install(c,0x5a5ca,0x5aa04);
    // BTST.B #0,80(A6); BNE.W 5aa34.
    case 0x5aa04:if(!on13_btst(c,r.a[6],0x80,0,flag))return false;r.pc=flag?0x5aa34:0x5aa0e;return true;
    // BTST.B #7,61(A6); BEQ.W 5aa26.
    case 0x5aa0e:if(!on13_btst(c,r.a[6],0x61,7,flag))return false;r.pc=flag?0x5aa18:0x5aa26;return true;
    // MOVE.L #0,56(A6); BSET.B #0,80(A6).
    case 0x5aa18:if(!on13_put(c,r.a[6],0x56,4,0) || !on13_bchange(c,r.a[6],0x80,0,true,flag))return false;r.pc=0x5aa26;return true;
    case 0x5aa26:return am_call(c,0x4b54e,0x5aa2c);
    case 0x5aa2c:return on13_consume(c,false,0x5aa34,0x5aa30);                             // BCC.W 5aa34 (C of 4b54e).
    case 0x5aa30:if(!on13_put(c,r.a[6],0x5e,1,0))return false;r.pc=0x5aa34;return true;   // CLR.B 5e(A6).
    case 0x5aa34:if(!on13_put(c,r.a[6],0x5e,1,0))return false;return am_return(c);        // CLR.B 5e(A6); RTS.

    // ---- 5aa3a: MOVE.W #183,20(A6); MOVE.L 200190.L,22(A6); JSR 8ff4.L.
    case 0x5aa3a:if(!on13_bank_animation(c))return false;return am_call(c,0x8ff4,0x5aa4e);
    case 0x5aa4e:return on13_part(c,0xd3c,0x5aa5c);
    case 0x5aa5c:return on13_part(c,0xd3d,0x5aa6a);
    // MOVE.B 19(A6),14(A6); MOVE.W #922,D0; JSR 4a496.L.
    case 0x5aa6a:if(!on13_copy(c,r.a[6],0x19,r.a[6],0x14,1))return false;am_word(r.d[0],0x922);return am_call(c,0x4a496,0x5aa7a);
    // BSET.B #6,15(A6); MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.W #734,D0; JSR 3af8.L.
    case 0x5aa7a:
        if(!on13_bchange(c,r.a[6],0x15,6,true,flag) || !on13_frame(c,r.a[6],0))return false;am_word(r.d[0],0x734);return am_call(c,0x3af8,0x5aa96);
    case 0x5aa96:return on13_animation(c,0x5b9d2,0x5aaa6);
    case 0x5aaa6:r.a[0]=0x5b220;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x5aab6);     // MOVEA.L #5b220,A0; MOVE.W #a,D0; JSR 28ae.L.
    // LEA 76(A6),A1; MOVE.L A1,76(A0); LEA 5dcaa.L,A0; JSR 490ba.L.
    case 0x5aab6:r.a[1]=am_index(r.a[6],0x76);if(!on13_put(c,r.a[0],0x76,4,r.a[1]))return false;r.a[0]=0x5dcaa;return am_call(c,0x490ba,0x5aaca);
    // MOVE.W D0,54(A6); LEA 5dcf4.L,A0; JSR 490ba.L.
    case 0x5aaca:if(!on13_put(c,r.a[6],0x54,2,on13_w(r.d[0])))return false;r.a[0]=0x5dcf4;return am_call(c,0x490ba,0x5aada);
    // MOVE.W D0,82(A6); CLR.B 81(A6); MOVE.L #0,98(A6); MOVE.L #5dc5e,56(A6); MOVE.L #5d85e,7c(A6); MOVE.W #8,D0; MOVE.W #10,D1;
    // MOVE.W #2f,D2; MOVE.W #3f,D3; JSR d3ab8.L.
    case 0x5aada:
        if(!on13_put(c,r.a[6],0x82,2,on13_w(r.d[0])) || !on13_put(c,r.a[6],0x81,1,0) || !on13_put(c,r.a[6],0x98,4,0) ||
            !on13_put(c,r.a[6],0x56,4,0x5dc5eU) || !on13_put(c,r.a[6],0x7c,4,0x5d85eU))return false;
        am_word(r.d[0],8);am_word(r.d[1],0x10);am_word(r.d[2],0x2f);am_word(r.d[3],0x3f);return am_call(c,0xd3ab8,0x5ab10);
    case 0x5ab10:if(!on13_put(c,r.a[6],0x9d,1,0))return false;return am_return(c);        // CLR.B 9d(A6); RTS.

    // ---- interpreter command callbacks: MOVE.W (A0),76(A6) / 88(A6); RTS.
    case 0x5ab16:case 0x5ab1c:
        if(!am_read(c,r.a[0],2,value) || !on13_put(c,r.a[6],r.pc==0x5ab16?0x76U:0x88U,2,value))return false;return am_return(c);
    case 0x5ab22:r.a[1]=0x5b61c;return am_call(c,0xd3802,0x5ab2c);                        // LEA 5b61c(PC),A1; JSR d3802.L.
    case 0x5ab2c:if(!on13_frame(c,r.a[0],0xe0ec))return false;return am_return(c);        // MOVE.W #e0ec,68/1e(A0); RTS.
    case 0x5ab3a:r.a[0]=0x5ab82;am_word(r.d[0],0x14);return am_call(c,0x28ae,0x5ab4a);    // MOVEA.L #5ab82,A0; MOVE.W #14,D0; JSR 28ae.L.
    case 0x5ab4a:am_word(r.d[0],0xffe8);am_word(r.d[1],0x72);return am_call(c,0x49214,0x5ab58); // MOVE.W #ffe8,D0; MOVE.W #72,D1; JSR 49214.L.
    // RTS (keeps C).
    case 0x5ab58:case 0x5ab6a:case 0x5b4be:case 0xd3612:return am_return(c);

    // ---- 5ab5a: MOVE.W 1e(A6),D0; JSR ce02.L; JSR 49fc6.L; RTS (returns the C of 49fc6).
    case 0x5ab5a:if(!on13_get(c,r.a[6],0x1e,2,value))return false;am_word(r.d[0],value);return am_call(c,0xce02,0x5ab64);
    case 0x5ab64:return am_call(c,0x49fc6,0x5ab6a);

    // ---- 5b220 (28ae child): MOVE.W #183,20(A6); MOVE.L 200190.L,22(A6); MOVEA.L c(A6),A0; LEA 2e(A0),A1; MOVEA.L 76(A6),A0;
    // MOVE.B (A0),D0; MOVE.B 1(A0),D1; CLR.B 2(A0); EXT.W D0; EXT.W D1; JSR 43e04.L.
    case 0x5b220:
        if(!on13_bank_animation(c) || !on13_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;r.a[1]=am_index(r.a[0],0x2e);
        if(!on13_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        if(!on13_get(c,r.a[0],0,1,value))return false;am_byte(r.d[0],value);
        if(!on13_get(c,r.a[0],1,1,value))return false;am_byte(r.d[1],value);
        if(!on13_put(c,r.a[0],2,1,0))return false;am_word(r.d[0],on13_ext_b(r.d[0]));am_word(r.d[1],on13_ext_b(r.d[1]));
        return am_call(c,0x43e04,0x5b24e);
    // MOVE.W #2000,D0; MOVE.W D0,80(A6); MOVE.W D0,84(A6); MOVEA.L 76(A6),A0; MOVE.W #ffff,4(A0); MOVE.W #d3a,D0; MOVE.B #0,D1;
    // JSR 8ebe.L.
    case 0x5b24e:
        am_word(r.d[0],0x2000);if(!on13_put(c,r.a[6],0x80,2,0x2000) || !on13_put(c,r.a[6],0x84,2,0x2000) || !on13_get(c,r.a[6],0x76,4,value))return false;
        r.a[0]=value;if(!on13_put(c,r.a[0],4,2,0xffff))return false;return on13_part(c,0xd3a,0x5b272);
    case 0x5b272:return on13_part(c,0xd45,0x5b280);
    // MOVE.B 19(A6),14(A6); BSET.B #6,15(A6); MOVE.W #1,68(A6); MOVE.W #1,1e(A6); MOVEA.L #5cff4,A1; MOVE.W #100,D0; JSR 49f8c.L.
    case 0x5b280:
        if(!on13_copy(c,r.a[6],0x19,r.a[6],0x14,1) || !on13_bchange(c,r.a[6],0x15,6,true,flag) || !on13_frame(c,r.a[6],1))return false;
        return on13_animation(c,0x5cff4,0x5b2a8);
    case 0x5b2a8:return on13_install(c,0x5b2ae,0x5b2ae);                                  // MOVE.L #5b2ae,(A6).
    case 0x5b2ae:case 0xd3602:return am_call(c,0x288c,r.pc+6U);                           // JSR 288c.L.
    case 0x5b2b4:return on13_consume(c,false,0x5b4c0,0x5b2b8);                             // BCC.W 5b4c0 (C of 288c).
    // BTST.B #3,80(A0); BNE.W 5b4c0.
    case 0x5b2b8:if(!on13_btst(c,r.a[0],0x80,3,flag))return false;r.pc=flag?0x5b4c0:0x5b2c2;return true;
    // BTST.B #4,80(A0); BEQ.W 5b2de.
    case 0x5b2c2:if(!on13_btst(c,r.a[0],0x80,4,flag))return false;r.pc=flag?0x5b2cc:0x5b2de;return true;
    // BCLR.B #4,80(A0); MOVE.W 80(A6),D0; MOVE.W D0,84(A6); CLR.B 7b(A6).
    case 0x5b2cc:
        if(!on13_bchange(c,r.a[0],0x80,4,false,flag) || !on13_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[0],value);
        if(!on13_put(c,r.a[6],0x84,2,value) || !on13_put(c,r.a[6],0x7b,1,0))return false;r.pc=0x5b2de;return true;
    // MOVEQ #0,D0; MOVE.W 84(A6),D1; MOVEA.L 76(A6),A0; MOVE.W 4(A0),D0; BMI.W 5b2f4.
    case 0x5b2de:
        if(!on13_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[1],value);
        if(!on13_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        if(!on13_get(c,r.a[0],4,2,value))return false;r.d[0]=on13_w(value);r.pc=(value&0x8000U)?0x5b2f4:0x5b2f0;return true;
    case 0x5b2f0:am_word(r.d[0],(r.d[0]<<8)&65535U);am_word(r.d[1],r.d[0]);r.pc=0x5b2f4;return true; // LSL.W #8,D0; MOVE.W D0,D1.
    // MOVE.W 84(A6),D2; MOVE.W D1,84(A6); CMP.W D2,D1; BEQ.W 5b308.
    case 0x5b2f4:
        if(!on13_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[2],value);if(!on13_put(c,r.a[6],0x84,2,on13_w(r.d[1])))return false;
        r.pc=on13_w(r.d[1])==on13_w(r.d[2])?0x5b308:0x5b302;return true;
    case 0x5b302:if(!on13_put(c,r.a[6],0x82,2,0x400))return false;r.pc=0x5b308;return true; // MOVE.W #400,82(A6).
    // MOVE.W 82(A6),D7; MOVE.W 80(A6),D2; SUB.W D2,D1; BEQ.W 5b348.
    case 0x5b308:
        if(!on13_get(c,r.a[6],0x82,2,value))return false;am_word(r.d[7],value);
        if(!on13_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[2],value);
        am_word(r.d[1],(r.d[1]-r.d[2])&65535U);r.pc=on13_w(r.d[1])==0U?0x5b348:0x5b316;return true;
    case 0x5b316:r.pc=on13_w(r.d[1])!=0x8000U?0x5b326:0x5b31e;return true;               // CMPI.W #8000,D1; BNE.W 5b326.
    // NOT.B 7d(A6); BRA.W 5b32a.
    case 0x5b31e:if(!on13_get(c,r.a[6],0x7d,1,value) || !on13_put(c,r.a[6],0x7d,1,(~value)&255U))return false;r.pc=0x5b32a;return true;
    // SPL.B 7d(A6): N recomputed from the unique predecessor 5b316 (CMPI.W #8000,D1, D1 unchanged): N = bit 15 of D1.W - 8000.
    case 0x5b326:
        if(!on13_put(c,r.a[6],0x7d,1,(((r.d[1]-0x8000U)&0x8000U)==0U)?0xffU:0U))return false;r.pc=0x5b32a;return true;
    // TST.B 7d(A6); BEQ.W 5b334.
    case 0x5b32a:if(!on13_get(c,r.a[6],0x7d,1,value))return false;r.pc=on13_b(value)==0U?0x5b334:0x5b332;return true;
    case 0x5b332:am_word(r.d[7],(0U-r.d[7])&65535U);r.pc=0x5b334;return true;             // NEG.W D7.
    // ADD.W D7,D2; SUB.W D7,D1; EOR.W D1,D7; BPL.W 5b340.
    case 0x5b334:
        am_word(r.d[2],(r.d[2]+r.d[7])&65535U);am_word(r.d[1],(r.d[1]-r.d[7])&65535U);am_word(r.d[7],(r.d[7]^r.d[1])&65535U);
        r.pc=(r.d[7]&0x8000U)==0U?0x5b340:0x5b33e;return true;
    case 0x5b33e:am_word(r.d[2],(r.d[2]+r.d[1])&65535U);r.pc=0x5b340;return true;         // ADD.W D1,D2.
    case 0x5b340:if(!on13_put(c,r.a[6],0x80,2,on13_w(r.d[2])))return false;r.pc=0x5b34e;return true; // MOVE.W D2,80(A6); BRA.W 5b34e.
    case 0x5b348:if(!on13_put(c,r.a[0],4,2,0xffff))return false;r.pc=0x5b34e;return true;  // MOVE.W #ffff,4(A0).
    // MOVEQ #0,D1; MOVE.B 80(A6),D0; ASR.B #3,D0 (X = the last bit shifted out = bit 2); ADDX.B D1,D0; ANDI.B #1f,D0;
    // MOVE.B D0,86(A6); MOVEA.L 76(A6),A0; MOVE.B (A0)+,D0; MOVE.B (A0),D1; EXT.W D0; EXT.W D1; MOVE.W D0,2e(A6);
    // MOVE.W D1,32(A6); JSR 43e34.L.
    case 0x5b34e: {
        r.d[1]=0;if(!on13_get(c,r.a[6],0x80,1,value))return false;
        const std::uint32_t x=(value>>2)&1U;std::uint32_t u=on13_b(value);
        for(unsigned int i=0;i<3;++i)u=(u>>1)|(u&0x80U);
        am_byte(r.d[0],(u+on13_b(r.d[1])+x)&255U);am_byte(r.d[0],r.d[0]&0x1fU);
        if(!on13_put(c,r.a[6],0x86,1,on13_b(r.d[0])) || !on13_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[0],value);r.a[0]+=1U;
        if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[1],value);
        am_word(r.d[0],on13_ext_b(r.d[0]));am_word(r.d[1],on13_ext_b(r.d[1]));
        if(!on13_put(c,r.a[6],0x2e,2,on13_w(r.d[0])) || !on13_put(c,r.a[6],0x32,2,on13_w(r.d[1])))return false;
        return am_call(c,0x43e34,0x5b37a);
    }
    // MOVEA.L 76(A6),A0; MOVE.B 7b(A6),D0; MOVE.B 3(A0),D1; CLR.B 3(A0); ADD.B D1,7b(A6); TST.B 7b(A6); BNE.W 5b3a0.
    case 0x5b37a:
        if(!on13_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        if(!on13_get(c,r.a[6],0x7b,1,value))return false;am_byte(r.d[0],value);
        if(!on13_get(c,r.a[0],3,1,value))return false;am_byte(r.d[1],value);
        if(!on13_put(c,r.a[0],3,1,0) || !on13_get(c,r.a[6],0x7b,1,value))return false;
        value=(value+on13_b(r.d[1]))&255U;if(!on13_put(c,r.a[6],0x7b,1,value))return false;r.pc=value!=0U?0x5b3a0:0x5b396;return true;
    case 0x5b396:if(!on13_put(c,r.a[6],0x7c,1,0))return false;r.pc=0x5b472;return true;   // MOVE.B #0,7c(A6); BRA.W 5b472.
    // MOVE.B #1,7c(A6); CLR.B D7; TST.B D0; BNE.W 5b3b4.
    case 0x5b3a0:if(!on13_put(c,r.a[6],0x7c,1,1))return false;am_byte(r.d[7],0);r.pc=on13_b(r.d[0])!=0U?0x5b3b4:0x5b3ae;return true;
    case 0x5b3ae:am_byte(r.d[7],0xff);r.pc=0x5b3ba;return true;                           // ST.B D7; BRA.W 5b3ba.
    // SUBQ.B #1,7a(A6); SEQ.B D7.
    case 0x5b3b4:
        if(!on13_get(c,r.a[6],0x7a,1,value))return false;value=(value+255U)&255U;if(!on13_put(c,r.a[6],0x7a,1,value))return false;
        am_byte(r.d[7],value==0U?0xffU:0U);r.pc=0x5b3ba;return true;
    case 0x5b3ba:r.pc=on13_b(r.d[7])==0U?0x5b472:0x5b3c0;return true;                    // TST.B D7; BEQ.W 5b472.
    case 0x5b3c0:r.a[0]=0x5b4c6;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x5b3d0);     // MOVEA.L #5b4c6,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0x5b3d0:return on13_consume(c,false,0x5b420,0x5b3d4);                             // BCC.W 5b420 (C of 28ae).
    // MOVEQ #0,D2; MOVE.B 80(A6),D1; CMP.B 7f(A6),D1; BNE.W 5b3f4.
    case 0x5b3d4:
        r.d[2]=0;if(!on13_get(c,r.a[6],0x80,1,value) || !on13_get(c,r.a[6],0x7f,1,other))return false;am_byte(r.d[1],value);
        r.pc=on13_b(value)!=on13_b(other)?0x5b3f4:0x5b3e2;return true;
    // MOVE.B 7e(A6),D2; ADDQ.B #1,D2; ANDI.W #3,D2; MOVE.B D2,7e(A6); SUBQ.B #1,D2; ADD.W D2,D2.
    case 0x5b3e2:
        if(!on13_get(c,r.a[6],0x7e,1,value))return false;am_byte(r.d[2],value);am_byte(r.d[2],r.d[2]+1U);am_word(r.d[2],r.d[2]&3U);
        if(!on13_put(c,r.a[6],0x7e,1,on13_b(r.d[2])))return false;am_byte(r.d[2],r.d[2]+255U);am_word(r.d[2],r.d[2]+r.d[2]);
        r.pc=0x5b3f4;return true;
    // MOVE.B D1,7f(A6); ADD.B D2,D1; MOVE.B D1,76(A0); SUB.B D2,D1; MOVE.L #2c0000,D0; MOVE.L A0,-(A7); JSR 443d2.L.
    case 0x5b3f4:
        if(!on13_put(c,r.a[6],0x7f,1,on13_b(r.d[1])))return false;am_byte(r.d[1],r.d[1]+r.d[2]);
        if(!on13_put(c,r.a[0],0x76,1,on13_b(r.d[1])))return false;am_byte(r.d[1],r.d[1]-r.d[2]);r.d[0]=0x2c0000U;
        if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x443d2,0x5b40e);
    // MOVEA.L (A7)+,A0; SWAP D0; SWAP D1; JSR 49214.L.
    case 0x5b40e:if(!am_pop(c,4,value))return false;r.a[0]=value;am_swap(r.d[0]);am_swap(r.d[1]);return am_call(c,0x49214,0x5b41a);
    case 0x5b41a:if(!on13_copy(c,r.a[6],0xc,r.a[0],0xc,4))return false;r.pc=0x5b420;return true; // MOVE.L c(A6),c(A0).
    // SUBQ.B #1,7b(A6); BEQ.W 5b46c.
    case 0x5b420:
        if(!on13_get(c,r.a[6],0x7b,1,value))return false;value=(value+255U)&255U;if(!on13_put(c,r.a[6],0x7b,1,value))return false;
        r.pc=value==0U?0x5b46c:0x5b428;return true;
    // MOVEQ #0,D0; MOVE.W 84(A6),D0; MOVE.W 80(A6),D1; SUB.W D1,D0; BEQ.W 5b466.
    case 0x5b428:
        if(!on13_get(c,r.a[6],0x84,2,value))return false;r.d[0]=on13_w(value);
        if(!on13_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[1],value);
        am_word(r.d[0],(r.d[0]-r.d[1])&65535U);r.pc=on13_w(r.d[0])==0U?0x5b466:0x5b438;return true;
    // TST.B 7d(A6); BEQ.W 5b442.
    case 0x5b438:if(!on13_get(c,r.a[6],0x7d,1,value))return false;r.pc=on13_b(value)==0U?0x5b442:0x5b440;return true;
    case 0x5b440:am_word(r.d[0],(0U-r.d[0])&65535U);r.pc=0x5b442;return true;             // NEG.W D0.
    // DIVU.W 82(A6),D0; ANDI.L #ffff,D0; MOVEQ #0,D1; MOVE.B 7b(A6),D1; ADDQ.B #1,D1; DIVU.W D1,D0; TST.W D0; BNE.W 5b45e.
    case 0x5b442:
        if(!on13_get(c,r.a[6],0x82,2,value) || !on13_divu(c,r.d[0],value))return false;r.d[0]&=65535U;
        r.d[1]=0;if(!on13_get(c,r.a[6],0x7b,1,value))return false;am_byte(r.d[1],value);am_byte(r.d[1],r.d[1]+1U);
        if(!on13_divu(c,r.d[0],r.d[1]))return false;r.pc=on13_w(r.d[0])!=0U?0x5b45e:0x5b45c;return true;
    case 0x5b45c:am_word(r.d[0],r.d[0]+1U);r.pc=0x5b45e;return true;                     // ADDQ.W #1,D0.
    case 0x5b45e:if(!on13_put(c,r.a[6],0x7a,1,on13_b(r.d[0])))return false;r.pc=0x5b46c;return true; // MOVE.B D0,7a(A6); BRA.W 5b46c.
    case 0x5b466:if(!on13_put(c,r.a[6],0x7a,1,6))return false;r.pc=0x5b46c;return true;   // MOVE.B #6,7a(A6).
    case 0x5b46c:if(!on13_put(c,r.a[6],0x8a,2,0x180))return false;r.pc=0x5b472;return true; // MOVE.W #180,8a(A6).
    // MOVE.W 8a(A6),D0; ADD.W D0,88(A6); ANDI.B #3,88(A6); LSR.W #4,D0; SUB.W D0,8a(A6); JSR 4a46c.L.
    case 0x5b472:
        if(!on13_get(c,r.a[6],0x8a,2,value))return false;am_word(r.d[0],value);
        if(!on13_get(c,r.a[6],0x88,2,value) || !on13_put(c,r.a[6],0x88,2,(value+r.d[0])&65535U))return false;
        if(!on13_get(c,r.a[6],0x88,1,value) || !on13_put(c,r.a[6],0x88,1,value&3U))return false;
        am_word(r.d[0],on13_w(r.d[0])>>4);
        if(!on13_get(c,r.a[6],0x8a,2,value) || !on13_put(c,r.a[6],0x8a,2,(value-on13_w(r.d[0]))&65535U))return false;
        return am_call(c,0x4a46c,0x5b48c);
    case 0x5b48c:return on13_consume(c,false,0x5b496,0x5b490);                             // BCC.W 5b496 (C of 4a46c).
    case 0x5b490:if(!on13_copy(c,r.a[6],0x1a,r.a[6],0x14,1))return false;r.pc=0x5b496;return true; // MOVE.B 1a(A6),14(A6).
    case 0x5b496:if(!on13_put(c,r.a[6],0x17,1,0xff))return false;return am_call(c,0x49fc6,0x5b4a2); // MOVE.B #ff,17(A6); JSR 49fc6.L.
    // MOVE.B 19(A6),14(A6); MOVEA.L 76(A6),A0; TST.B 2(A0); BEQ.W 5b4be.
    case 0x5b4a2:
        if(!on13_copy(c,r.a[6],0x19,r.a[6],0x14,1) || !on13_get(c,r.a[6],0x76,4,value))return false;r.a[0]=value;
        if(!on13_get(c,r.a[0],2,1,value))return false;r.pc=on13_b(value)==0U?0x5b4be:0x5b4b4;return true;
    // CLR.B 2(A0); MOVE.B 1a(A6),14(A6).
    case 0x5b4b4:if(!on13_put(c,r.a[0],2,1,0) || !on13_copy(c,r.a[6],0x1a,r.a[6],0x14,1))return false;r.pc=0x5b4be;return true;
    case 0x5b4c0:r.pc=0x2a00;return true;                                                 // JMP 2a00.L.

    // ---- d3580 (28ae child): MOVE.W 76(A6),D0; MOVE.W 78(A6),D1; JSR 49290.L.
    case 0xd3580:
        if(!on13_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);
        if(!on13_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[1],value);return am_call(c,0x49290,0xd358e);
    // MOVEA.L c(A6),A0; MOVE.W 54(A0),D0; LSR.W #1,D0; TST.W 7e(A6); BNE.W d35a4.
    case 0xd358e:
        if(!on13_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!on13_get(c,r.a[0],0x54,2,value))return false;
        am_word(r.d[0],on13_w(value)>>1);if(!on13_get(c,r.a[6],0x7e,2,value))return false;r.pc=value!=0U?0xd35a4:0xd35a0;return true;
    case 0xd35a0:if(!on13_put(c,r.a[6],0x7e,2,on13_w(r.d[0])))return false;r.pc=0xd35a4;return true; // MOVE.W D0,7e(A6).
    // LSR.W #1,D0; TST.W 80(A6); BNE.W d35b2.
    case 0xd35a4:am_word(r.d[0],on13_w(r.d[0])>>1);if(!on13_get(c,r.a[6],0x80,2,value))return false;r.pc=value!=0U?0xd35b2:0xd35ae;return true;
    case 0xd35ae:if(!on13_put(c,r.a[6],0x80,2,on13_w(r.d[0])))return false;r.pc=0xd35b2;return true; // MOVE.W D0,80(A6).
    case 0xd35b2:return on13_animation(c,0xd418c,0xd35c2);
    case 0xd35c2:return am_call(c,0x49fc6,0xd35c8);
    case 0xd35c8:return on13_install(c,0xd35ce,0xd35ce);                                  // MOVE.L #d35ce,(A6).
    case 0xd35ce:return am_call(c,0xd3b1a,0xd35d2);                                       // JSR d3b1a(PC).
    // MOVE.W 54(A6),D0; CMP.W 7e(A6),D0; BGT.W d35e4 (signed WORD D0 > 7e).
    case 0xd35d2:
        if(!on13_get(c,r.a[6],0x54,2,value) || !on13_get(c,r.a[6],0x7e,2,other))return false;am_word(r.d[0],value);
        r.pc=on13_sw(value)>on13_sw(other)?0xd35e4:0xd35de;return true;
    case 0xd35de:return on13_install(c,0xd3614,0xd35e4);                                  // MOVE.L #d3614,(A6).
    // CMP.W 80(A6),D0; BGT.W d35f2.
    case 0xd35e4:if(!on13_get(c,r.a[6],0x80,2,other))return false;r.pc=on13_sw(r.d[0])>on13_sw(other)?0xd35f2:0xd35ec;return true;
    case 0xd35ec:return on13_install(c,0xd3646,0xd35f2);                                  // MOVE.L #d3646,(A6).
    // BTST.B #7,61(A6); BEQ.W d3602.
    case 0xd35f2:if(!on13_btst(c,r.a[6],0x61,7,flag))return false;r.pc=flag?0xd35fc:0xd3602;return true;
    case 0xd35fc:return on13_install(c,0xd3678,0xd3602);                                  // MOVE.L #d3678,(A6).
    case 0xd3608:return on13_consume(c,true,0xd3612,0xd360c);                              // BCS.W d3612 (C of 288c).
    case 0xd360c:return on13_install(c,0xd3678,0xd3612);                                  // MOVE.L #d3678,(A6).

    // ---- d3ab8: MOVEQ #0,D4; MOVEQ #0,D5; JSR d3ae8(PC); MOVE.W #1001,68(A0); MOVE.W #1001,1e(A0); RTS.
    case 0xd3ab8:r.d[4]=0;r.d[5]=0;return am_call(c,0xd3ae8,0xd3ac0);
    case 0xd3ac0:if(!on13_frame(c,r.a[0],0x1001))return false;return am_return(c);
    // MOVEM.L D0-D5,-(A7) (D0 at the lowest address); MOVEA.L #d3580,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0xd3ae8:
        for(unsigned int i=6;i>0;--i)if(!am_push(c,4,r.d[i-1]))return false;
        r.a[0]=0xd3580;am_word(r.d[0],0xa);return am_call(c,0x28ae,0xd3afc);
    // MOVEM.L (A7)+,D0-D5; MOVE.W D0..D5,76/78/7a/7c/7e/80(A0); RTS.
    case 0xd3afc:
        for(unsigned int i=0;i<6;++i){if(!am_pop(c,4,value))return false;r.d[i]=value;}
        for(unsigned int i=0;i<6;++i)if(!on13_put(c,r.a[0],0x76U+2U*i,2,on13_w(r.d[i])))return false;
        return am_return(c);

    // ---- d3b1a: JSR 43e34.L.
    case 0xd3b1a:return am_call(c,0x43e34,0xd3b20);
    // MOVEA.L c(A6),A0; MOVE.B 12(A0),12(A6); MOVE.B 13(A0),13(A6); BTST.B #0,15(A0); BNE.W d3b44.
    case 0xd3b20:
        if(!on13_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!on13_copy(c,r.a[0],0x12,r.a[6],0x12,1) || !on13_copy(c,r.a[0],0x13,r.a[6],0x13,1) || !on13_btst(c,r.a[0],0x15,0,flag))return false;
        r.pc=flag?0xd3b44:0xd3b3a;return true;
    case 0xd3b3a:if(!on13_bchange(c,r.a[6],0x15,0,false,flag))return false;r.pc=0xd3b4a;return true; // BCLR.B #0,15(A6); BRA.W d3b4a.
    case 0xd3b44:if(!on13_bchange(c,r.a[6],0x15,0,true,flag))return false;r.pc=0xd3b4a;return true;  // BSET.B #0,15(A6).
    // BCLR.B #7,61(A6); TST.B a3(A6); BNE.W d3b68.
    case 0xd3b4a:
        if(!on13_bchange(c,r.a[6],0x61,7,false,flag) || !on13_get(c,r.a[6],0xa3,1,value))return false;r.pc=value!=0U?0xd3b68:0xd3b58;return true;
    // BTST.B #7,61(A0); BEQ.W d3b68.
    case 0xd3b58:if(!on13_btst(c,r.a[0],0x61,7,flag))return false;r.pc=flag?0xd3b62:0xd3b68;return true;
    case 0xd3b62:if(!on13_bchange(c,r.a[6],0x61,7,true,flag))return false;r.pc=0xd3b68;return true; // BSET.B #7,61(A6).
    case 0xd3b68:if(!on13_copy(c,r.a[0],0x54,r.a[6],0x54,2))return false;return am_return(c); // MOVE.W 54(A0),54(A6); RTS.

    // ---- dbfac: MOVE.B #ff,5c8d(A5); JMP 2a00.L.
    case 0xdbfac:if(!on13_put(c,r.a[5],0x5c8d,1,0xff))return false;r.pc=0x2a00;return true;
    default:return am_error(c,"unsupported animation objects n13 PC");
    }
}
}
