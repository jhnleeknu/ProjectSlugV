#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code.
const std::uint32_t ON05_CHILD_TABLE=0xc6012;  // LEA c6012(PC),A1: fixed ROM LONG table of 28ae children (live bus, no bound).
const std::uint32_t ON05_RECT=0xbe1dc;         // LEA be1dc.L,A0: rectangle read by 1ab02.
const std::uint32_t ON05_MOVER_BANK=0x2001dc;  // MOVE.L 2001dc.L,22(A6): banked window LONG (live bus).
const std::uint32_t ON05_PIECE_BANK=0x20008c;  // MOVE.L 20008c.L,22(A6).
const std::uint32_t ON05_TAIL_BANK=0x200094;   // MOVE.L 200094.L,22(A6).
const std::uint32_t ON05_MAP=0x10b1d6;         // LEA 10b1d6.L,A1 (LONG c(A1) tested).
const std::uint32_t ON05_FLAG=0x100012;        // CMPI.B #1,100012.L.
// A5 displacements (sign-extended WORDs).
const std::uint32_t ON05_SIDE=0x5408;          // 1a3ae: WORD 5408(A5).
const std::uint32_t ON05_PROGRESS=0x5418;      // WORD 5418(A5) compared with 270/32a/198.
const std::uint32_t ON05_CAMERA=0x538e;        // LEA 538e(A5),A1 (LONGs +14..+20).
bool on05_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on05_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// Signed view of a WORD / LONG (explicit two's complement).
std::int32_t on05_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
bool on05_negative_long(std::uint32_t value) {return (value&0x80000000U)!=0U;}
// ADD.W D1,D0; NEG.W D0.
void on05_add_negate(AnimationMachineState& r) {am_word(r.d[0],r.d[0]+r.d[1]);am_word(r.d[0],0U-(r.d[0]&65535U));}
// CMPI.W #k,D2; BGT (greater) / BLT 1aafc, else next_pc (signed WORD compare).
void on05_edge(AnimationMachineState& r,std::int32_t limit,bool greater,std::uint32_t next_pc) {
    const std::int32_t value=on05_signed_word(r.d[2]);r.pc=(greater?value>limit:value<limit)?0x1aafc:next_pc;
}
// Consumers of a known C: BCC (taken when clear) or BCS (taken when set).
bool on05_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects n05 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #priority,D0; JSR 28ae.L.
bool on05_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t priority,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],priority);return am_call(c,0x28ae,return_pc);
}
// MOVE.W #d0,D0; MOVE.W #d1,D1; MOVE.B #0,D2; JSR c6a96.L.
bool on05_palette_object(AnimationMachineContext& c,std::uint32_t d0,std::uint32_t d1,std::uint32_t return_pc) {
    am_word(c.s.d[0],d0);am_word(c.s.d[1],d1);am_byte(c.s.d[2],0);return am_call(c,0xc6a96,return_pc);
}
// LEA 26(A6),A0; MOVE.W #id,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1;
// MOVEA.L entry(A1),A1; JSR 49f8c.L.
bool on05_animation(AnimationMachineContext& c,std::uint32_t id,std::uint32_t bank,std::uint32_t entry,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!on05_put(c,0x20,2,id) || !am_read(c,bank,4,value) || !on05_put(c,0x22,4,value))return false;
    am_word(r.d[0],0x100);if(!on05_get(c,0x22,4,value))return false;r.a[1]=value;
    if(!am_read(c,am_index(r.a[1],entry),4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.L #0,3a(A6); ANDI.L #ffff0000,32(A6).
bool on05_stop(AnimationMachineContext& c) {
    std::uint32_t value=0;return on05_put(c,0x3a,4,0) && on05_get(c,0x32,4,value) && on05_put(c,0x32,4,value&0xffff0000U);
}
// MOVE.L 3a(A6),D3; ASR.L #3,D3; SUB.L D3,3a(A6) (D3 keeps the shifted value).
bool on05_damp(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on05_get(c,0x3a,4,value))return false;
    r.d[3]=(value>>3)|(on05_negative_long(value)?0xe0000000U:0U);return on05_put(c,0x3a,4,value-r.d[3]);
}
// SUB.W 7a(A6),D2; BPL plus_pc (else minus_pc).
bool on05_approach(AnimationMachineContext& c,std::uint32_t plus_pc,std::uint32_t minus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on05_get(c,0x7a,2,value))return false;
    am_word(r.d[2],r.d[2]-value);r.pc=(r.d[2]&0x8000U)==0U?plus_pc:minus_pc;return true;
}
// LEA rect(PC),A0; BRA.W d1e58.
bool on05_rect(AnimationMachineState& r,std::uint32_t rect) {r.a[0]=rect;r.pc=0xd1e58;return true;}
}
// Objects F4 N05 (old U21/R04; 128 block starts): the node callbacks dceca (100012 test; sound 73a, U01 48296, area clear 1c5b0,
// input 49c66/49c32, U17 482c0, installed dcef8 waiting for 5418(A5) >= 198, installed dcf22 counting 76 down to the 28ae child
// 4841a), bdcc6 (28ae children bdec4/bdedc with U08 49290; U05 c6a96, banked animation 2001dc for interpreter 49f8c, installed
// bdd3e/bdd8a/bde50/bdea0/bdf40, U04 43ea4, U05 1ab02 with the fixed rectangle be1dc, stage event ops 288c, U09 4706c), c5e6c (helper
// 1a3ae), c5fd8 (28ae child from the fixed LONG table c6012 indexed by 76, helper 49214) with the table children d22e6/d1cd8/d1d08/
// d1d38/d1d98/d1dc8 (banked animation 20008c/200094, U02 8ebe, helper d3c2a with stage area 49a58, installed d23b2, the screen range
// test 1ab80 on the rectangle LONG 92). 1abd4 returns C clear (U01 1aafc returns C set). bddb4 recomputes the N of the SUB.W of its
// only predecessor bdd8a from D2. N05 writes no port and changes no bank; the unreferenced d1d68..d1d98, d1df8..d1e58 and
// d232c..d239c stay outside the routing.
bool animation_objects_n05_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 1a3ae (helper): CMPI.W #8,D0; BCS.W 1a3b8.
    case 0x1a3ae:r.pc=(r.d[0]&65535U)<8U?0x1a3b8:0x1a3b6;return true;
    case 0x1a3b6:r.d[0]=8;r.pc=0x1a3b8;return true;                           // MOVEQ #8,D0.
    // TST.W 5408(A5); BPL.W 1a3c2.
    case 0x1a3b8:if(!am_read(c,am_index(r.a[5],ON05_SIDE),2,value))return false;r.pc=(value&0x8000U)==0U?0x1a3c2:0x1a3c0;return true;
    case 0x1a3c0:am_word(r.d[0],0U-(r.d[0]&65535U));r.pc=0x1a3c2;return true;  // NEG.W D0.
    // MOVE.W D0,5408(A5); RTS.
    case 0x1a3c2:if(!am_write(c,am_index(r.a[5],ON05_SIDE),2,r.d[0]&65535U))return false;return am_return(c);

    // ---- 1ab80 (screen range test): MOVE.L (A0)+,D0; MOVE.L (A0)+,D1; BTST.B #1,15(A6); BEQ.W 1ab92.
    case 0x1ab80:
        if(!am_read(c,r.a[0],4,value))return false;r.d[0]=value;r.a[0]+=4U;
        if(!am_read(c,r.a[0],4,value))return false;r.d[1]=value;r.a[0]+=4U;
        if(!on05_get(c,0x15,1,value))return false;r.pc=(value&2U)!=0U?0x1ab8e:0x1ab92;return true;
    case 0x1ab8e:on05_add_negate(r);r.pc=0x1ab92;return true;                  // ADD.W D1,D0; NEG.W D0.
    case 0x1abb8:on05_add_negate(r);r.pc=0x1abbc;return true;
    // MOVE.W 46(A6),D2; ADD.W D0,D2; CMPI.W #200,D2; BGT.W 1aafc.
    case 0x1ab92:if(!on05_get(c,0x46,2,value))return false;am_word(r.d[2],value+r.d[0]);on05_edge(r,0x200,true,0x1aba0);return true;
    case 0x1aba0:am_word(r.d[2],r.d[2]+r.d[1]);on05_edge(r,0x100,false,0x1abaa);return true; // ADD.W D1,D2; CMPI.W #100,D2; BLT.W 1aafc.
    // SWAP D0; SWAP D1; BTST.B #0,15(A6); BEQ.W 1abbc.
    case 0x1abaa:am_swap(r.d[0]);am_swap(r.d[1]);if(!on05_get(c,0x15,1,value))return false;r.pc=(value&1U)!=0U?0x1abb8:0x1abbc;return true;
    // MOVE.W 42(A6),D2; ADD.W D0,D2; CMPI.W #140,D2; BGT.W 1aafc.
    case 0x1abbc:if(!on05_get(c,0x42,2,value))return false;am_word(r.d[2],value+r.d[0]);on05_edge(r,0x140,true,0x1abca);return true;
    case 0x1abca:am_word(r.d[2],r.d[2]+r.d[1]);on05_edge(r,0,false,0x1abd4);return true; // ADD.W D1,D2; CMPI.W #0,D2; BLT.W 1aafc.
    case 0x1abd4:r.carry=AnimationCarryClear;return am_return(c);               // ANDI.B #fe,CCR; RTS.

    // ---- 49214 (helper): SWAP D0; CLR.W D0; SWAP D1; CLR.W D1; MOVE.L D0,D2; MOVE.L D1,D3; ADD.L 42/46/4a/4e(A6),D0-D3;
    // LEA 538e(A5),A1; SUB.L 14/18/1c/20(A1),D0-D3; SUB.L D0,D2; SUB.L D1,D3; NEG.L D2; NEG.L D3; LEA 2e(A0),A0;
    // MOVEM.L D0-D3/A1,(A0); JSR 43e38.L.
    case 0x49214:{
        r.d[0]=(r.d[0]&65535U)<<16;r.d[1]=(r.d[1]&65535U)<<16;r.d[2]=r.d[0];r.d[3]=r.d[1];
        const std::uint32_t own[4]={0x42,0x46,0x4a,0x4e};
        for(unsigned int i=0;i<4;++i){if(!on05_get(c,own[i],4,value))return false;r.d[i]+=value;}
        r.a[1]=am_index(r.a[5],ON05_CAMERA);
        for(unsigned int i=0;i<4;++i){if(!am_read(c,r.a[1]+0x14U+4U*i,4,value))return false;r.d[i]-=value;}
        r.d[2]=r.d[0]-r.d[2];r.d[3]=r.d[1]-r.d[3];r.a[0]+=0x2eU;
        for(unsigned int i=0;i<4;++i)if(!am_write(c,r.a[0]+4U*i,4,r.d[i]))return false;
        if(!am_write(c,r.a[0]+16U,4,r.a[1]))return false;return am_call(c,0x43e38,0x4925a);}
    case 0x4925a:r.a[0]-=0x2eU;return am_return(c);                             // SUBA.W #2e,A0; RTS.

    // ---- bdcc6 (callback): 28ae children bdec4 / bdedc.
    case 0xbdcc6:return on05_child(c,0xbdec4,0xa,0xbdcd6);
    case 0xbdcd6:return on05_child(c,0xbdedc,0xa,0xbdce6);
    // MOVE.W 76(A6),D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,7a(A6); MOVE.W #1,68(A6); MOVE.W #1,1e(A6); then c6a96 (76, 17).
    case 0xbdce6:
        if(!on05_get(c,0x76,2,value))return false;r.d[0]=am_extend_word(value)<<8;
        if(!on05_put(c,0x7a,4,r.d[0]) || !on05_put(c,0x68,2,1) || !on05_put(c,0x1e,2,1))return false;
        return on05_palette_object(c,0x76,0x17,0xbdd10);
    case 0xbdd10:return on05_animation(c,0x21b,ON05_MOVER_BANK,0x5c,0xbdd38);
    case 0xbdd38:if(!am_write(c,r.a[6],4,0xbdd3e))return false;r.pc=0xbdd3e;return true; // MOVE.L #bdd3e,(A6).
    case 0xbdd3e:return am_call(c,0x43e34,0xbdd44);                            // JSR 43e34.L.
    case 0xbdea0:return am_call(c,0x43e34,0xbdea6);
    case 0xbdf40:return am_call(c,0x43e34,0xbdf46);
    case 0xbdd44:return am_call(c,0x49fc6,0xbdd4a);                            // JSR 49fc6.L.
    case 0xbde32:return am_call(c,0x49fc6,0xbde38);
    case 0xbdea6:return am_call(c,0x49fc6,0xbdeac);
    case 0xbdf58:return am_call(c,0x49fc6,0xbdf5e);
    // LEA 10b1d6.L,A1; TST.L c(A1); BEQ.W bdd72.
    case 0xbdd4a:r.a[1]=ON05_MAP;if(!am_read(c,ON05_MAP+0xcU,4,value))return false;r.pc=value==0U?0xbdd72:0xbdd58;return true;
    // CMPI.W #270,5418(A5); BLT.W bdd6c.
    case 0xbdd58:
        if(!am_read(c,am_index(r.a[5],ON05_PROGRESS),2,value))return false;r.pc=on05_signed_word(value)<0x270?0xbdd6c:0xbdd62;return true;
    case 0xbdd62:am_word(r.d[0],0x732);return am_call(c,0x3af8,0xbdd6c);      // MOVE.W #732,D0; JSR 3af8.L.
    case 0xbdd6c:if(!am_write(c,r.a[6],4,0xbdd8a))return false;r.pc=0xbdd72;return true; // MOVE.L #bdd8a,(A6).
    case 0xbdd72:r.a[0]=ON05_RECT;return am_call(c,0x1ab02,0xbdd7e);           // LEA be1dc.L,A0; JSR 1ab02.L.
    case 0xbde38:r.a[0]=ON05_RECT;return am_call(c,0x1ab02,0xbde44);
    case 0xbdeac:r.a[0]=ON05_RECT;return am_call(c,0x1ab02,0xbdeb8);
    case 0xbdd7e:return on05_carry(c,0xbdd88,0xbdd82);                         // BCC.W bdd88 (C returned by 1ab02).
    case 0xbde44:return on05_carry(c,0xbde4e,0xbde48);
    case 0xbdeb8:return on05_carry(c,0xbdec2,0xbdebc);
    case 0xbdd82:case 0xbde48:case 0xbdebc:case 0xbdf68:case 0xc5e76:case 0xc600c:case 0xd23d2:case 0xdcf10:case 0xdcf3c:
        r.pc=0x2a00;return true;                                               // JMP 2a00.L.
    case 0xbdd88:case 0xbde4e:case 0xbdec2:case 0xbdf80:case 0xd23d0:case 0xd3c3e:case 0xdcf02:case 0xdcf2a:
        return am_return(c);                                                   // RTS.
    // ---- bdd8a (installed): MOVE.W 46(A6),D0; MOVE.L 7a(A6),D1; MOVE.W 78(A6),D2; ADDI.W #100,D2; SUB.W D0,D2; BNE.W bddb4.
    case 0xbdd8a:
        if(!on05_get(c,0x46,2,value))return false;am_word(r.d[0],value);if(!on05_get(c,0x7a,4,value))return false;r.d[1]=value;
        if(!on05_get(c,0x78,2,value))return false;am_word(r.d[2],value+0x100U-r.d[0]);r.pc=(r.d[2]&65535U)!=0U?0xbddb4:0xbdda0;return true;
    // CMPI.W #32a,5418(A5); BLT.W bddb0.
    case 0xbdda0:
        if(!am_read(c,am_index(r.a[5],ON05_PROGRESS),2,value))return false;r.pc=on05_signed_word(value)<0x32a?0xbddb0:0xbddaa;return true;
    case 0xbddaa:if(!am_write(c,r.a[6],4,0xbde50))return false;r.pc=0xbddb0;return true; // MOVE.L #bde50,(A6).
    case 0xbddb0:case 0xbddf2:r.pc=0xbde2c;return true;                        // BRA.W bde2c.
    case 0xbddb4:r.pc=(r.d[2]&0x8000U)==0U?0xbddf6:0xbddb8;return true;       // BPL.W bddf6 (N of the bdd8a SUB.W = D2 bit 15).
    // NEG.W D2; CMPI.W #1,D2; BGT.W bddd6.
    case 0xbddb8:am_word(r.d[2],0U-(r.d[2]&65535U));r.pc=on05_signed_word(r.d[2])>1?0xbddd6:0xbddc2;return true;
    case 0xbddc2:if(!on05_stop(c))return false;r.pc=0xbddf2;return true;      // MOVE.L #0,3a(A6); ANDI.L #ffff0000,32(A6); BRA.W bddf2.
    case 0xbddd6:return on05_approach(c,0xbddec,0xbddde);                      // SUB.W 7a(A6),D2; BPL.W bddec.
    case 0xbddde:if(!on05_damp(c))return false;r.pc=0xbddf2;return true;      // MOVE.L 3a(A6),D3; ASR.L #3,D3; SUB.L D3,3a(A6); BRA.W bddf2.
    case 0xbddec:r.d[1]=0U-r.d[1];if(!on05_put(c,0x3a,4,r.d[1]))return false;r.pc=0xbddf2;return true; // NEG.L D1; MOVE.L D1,3a(A6).
    case 0xbddf6:r.pc=on05_signed_word(r.d[2])>1?0xbde12:0xbddfe;return true; // CMPI.W #1,D2; BGT.W bde12.
    case 0xbddfe:if(!on05_stop(c))return false;r.pc=0xbde2c;return true;
    case 0xbde12:return on05_approach(c,0xbde28,0xbde1a);
    case 0xbde1a:if(!on05_damp(c))return false;r.pc=0xbde2c;return true;
    case 0xbde28:if(!on05_put(c,0x3a,4,r.d[1]))return false;r.pc=0xbde2c;return true; // MOVE.L D1,3a(A6).
    case 0xbde2c:return am_call(c,0x43ea4,0xbde32);                            // JSR 43ea4.L.
    // ---- bde50 (installed): MOVE.W #733,D0; JSR 3af8.L.
    case 0xbde50:am_word(r.d[0],0x733);return am_call(c,0x3af8,0xbde5a);
    // MOVE.L #0,36(A6); MOVE.L #0,3a(A6); ANDI.L #ffff0000,32(A6); then the banked animation 2001dc + 5c.
    case 0xbde5a:if(!on05_put(c,0x36,4,0) || !on05_stop(c))return false;return on05_animation(c,0x21b,ON05_MOVER_BANK,0x5c,0xbde9a);
    case 0xbde9a:if(!am_write(c,r.a[6],4,0xbdea0))return false;r.pc=0xbdea0;return true; // MOVE.L #bdea0,(A6).
    // ---- bdec4 / bdedc (28ae children): LEA k(PC),A0; MOVE.L A0,7e(A6); MOVE.W #d0,D0; MOVEQ #10,D1; JSR 49290.L.
    case 0xbdec4:r.a[0]=0xbdfdc;if(!on05_put(c,0x7e,4,r.a[0]))return false;am_word(r.d[0],0x88);r.d[1]=0x10;return am_call(c,0x49290,0xbded8);
    case 0xbdedc:r.a[0]=0xbdf82;if(!on05_put(c,0x7e,4,r.a[0]))return false;am_word(r.d[0],0xff78);r.d[1]=0x10;return am_call(c,0x49290,0xbdef0);
    case 0xbded8:case 0xbdef0:r.pc=0xbdef4;return true;                        // BRA.W bdef4.
    case 0xbdef4:return on05_palette_object(c,0x76,0x18,0xbdf06);
    // MOVE.W #0,68(A6); MOVE.W #0,1e(A6); then the banked animation 2001dc + 60.
    case 0xbdf06:if(!on05_put(c,0x68,2,0) || !on05_put(c,0x1e,2,0))return false;return on05_animation(c,0x21b,ON05_MOVER_BANK,0x60,0xbdf3a);
    case 0xbdf3a:if(!am_write(c,r.a[6],4,0xbdf40))return false;r.pc=0xbdf40;return true; // MOVE.L #bdf40,(A6).
    // LEA 10b1d6.L,A1; CMPI.L #80000,c(A1); BLT.W bdf5e.
    case 0xbdf46:{
        r.a[1]=ON05_MAP;if(!am_read(c,ON05_MAP+0xcU,4,value))return false;
        r.pc=(on05_negative_long(value) || value<0x80000U)?0xbdf5e:0xbdf58;return true;} // signed LONG < 80000.
    case 0xbdf5e:return am_call(c,0x288c,0xbdf64);                             // JSR 288c.L.
    case 0xbdf64:return on05_carry(c,0xbdf68,0xbdf6e);                         // BCS.W bdf6e (C returned by 288c).
    // MOVEA.L 7e(A6),A0; CMPA.W #0,A0; BEQ.W bdf80.
    case 0xbdf6e:if(!on05_get(c,0x7e,4,value))return false;r.a[0]=value;r.pc=value==0U?0xbdf80:0xbdf7a;return true;
    case 0xbdf7a:return am_call(c,0x4706c,0xbdf80);                            // JSR 4706c.L.

    // ---- c5e6c (callback): MOVE.W 76(A6),D0; JSR 1a3ae.L.
    case 0xc5e6c:if(!on05_get(c,0x76,2,value))return false;am_word(r.d[0],value);return am_call(c,0x1a3ae,0xc5e76);
    // ---- c5fd8 (callback): LEA c6012(PC),A1; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A0; MOVE.W #1e,D0;
    // JSR 28ae.L.
    case 0xc5fd8:
        r.a[1]=ON05_CHILD_TABLE;if(!on05_get(c,0x76,2,value))return false;am_word(r.d[0],value<<2);
        if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[0]=value;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0xc5ff2);
    case 0xc5ff2:return on05_carry(c,0xc600c,0xc5ff6);                         // BCC.W c600c (C returned by 28ae).
    // MOVE.W 78(A6),68(A0); MOVE.W 78(A6),1e(A0); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.L.
    case 0xc5ff6:
        if(!on05_get(c,0x78,2,value) || !am_write(c,am_index(r.a[0],0x68),2,value) || !on05_get(c,0x78,2,value) ||
            !am_write(c,am_index(r.a[0],0x1e),2,value))return false;
        r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,0xc600c);

    // ---- table children d1cd8 d1d08 d1d38 d1d98 d1dc8: banked animation 20008c + k, then a rectangle into 92(A6).
    case 0xd1cd8:return on05_animation(c,0xd2,ON05_PIECE_BANK,0x4,0xd1d00);
    case 0xd1d08:return on05_animation(c,0xd2,ON05_PIECE_BANK,0x8,0xd1d30);
    case 0xd1d38:return on05_animation(c,0xd2,ON05_PIECE_BANK,0xc,0xd1d60);
    case 0xd1d98:return on05_animation(c,0xd2,ON05_PIECE_BANK,0x40,0xd1dc0);
    case 0xd1dc8:return on05_animation(c,0xd2,ON05_PIECE_BANK,0x40,0xd1df0);
    case 0xd1d00:case 0xd1dc0:case 0xd1df0:return on05_rect(r,0xd3e5c);        // LEA d3e5c(PC),A0; BRA.W d1e58.
    case 0xd1d30:return on05_rect(r,0xd3e54);
    case 0xd1d60:return on05_rect(r,0xd3e64);
    // MOVE.L A0,92(A6); MOVE.W #cec,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xd1e58:if(!on05_put(c,0x92,4,r.a[0]))return false;am_word(r.d[0],0xcec);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xd1e6a);
    case 0xd1e6a:r.pc=0xd239c;return true;                                     // BRA.W d239c.
    // ---- d22e6 (table child): c6a96 (24, 6), banked animation 200094 + 18, 92(A6) = d3e8c.
    case 0xd22e6:return on05_palette_object(c,0x24,0x6,0xd22f8);
    case 0xd22f8:return on05_animation(c,0xe2,ON05_TAIL_BANK,0x18,0xd2320);
    case 0xd2320:if(!on05_put(c,0x92,4,0xd3e8c))return false;r.pc=0xd23a0;return true; // MOVE.L #d3e8c,92(A6); BRA.W d23a0.
    case 0xd239c:return am_call(c,0xd3c2a,0xd23a0);                            // JSR d3c2a(PC).
    // BCLR.B #1,15(A6); MOVE.B #ff,17(A6); MOVE.L #d23b2,(A6).
    case 0xd23a0:
        if(!on05_get(c,0x15,1,value) || !on05_put(c,0x15,1,value&0xfdU) || !on05_put(c,0x17,1,0xff) || !am_write(c,r.a[6],4,0xd23b2))
            return false;
        r.pc=0xd23b2;return true;
    // ---- d23b2 (installed): JSR 43e34.L; JSR 49fc6.L; BCS.W d23d2; MOVEA.L 92(A6),A0; JSR 1ab80.L; BCS.W d23d2; RTS.
    case 0xd23b2:return am_call(c,0x43e34,0xd23b8);
    case 0xd23b8:return am_call(c,0x49fc6,0xd23be);
    case 0xd23be:return on05_carry(c,0xd23c2,0xd23d2);                         // BCS.W d23d2 (C returned by 49fc6).
    case 0xd23c2:if(!on05_get(c,0x92,4,value))return false;r.a[0]=value;return am_call(c,0x1ab80,0xd23cc);
    case 0xd23cc:return on05_carry(c,0xd23d0,0xd23d2);                         // BCS.W d23d2 (C returned by 1ab80).

    // ---- d3c2a (helper): JSR 49a58.L; ANDI.B #2,D0; BNE.W d3c3e; BCHG.B #0,15(A6); RTS.
    case 0xd3c2a:return am_call(c,0x49a58,0xd3c30);
    case 0xd3c30:am_byte(r.d[0],r.d[0]&2U);r.pc=(r.d[0]&2U)!=0U?0xd3c3e:0xd3c38;return true;
    case 0xd3c38:if(!on05_get(c,0x15,1,value) || !on05_put(c,0x15,1,value^1U))return false;r.pc=0xd3c3e;return true;

    // ---- dceca (callback): CMPI.B #1,100012.L; BEQ.W dcf16.
    case 0xdceca:if(!am_read(c,ON05_FLAG,1,value))return false;r.pc=value==1U?0xdcf16:0xdced6;return true;
    case 0xdced6:am_word(r.d[0],0x73a);return am_call(c,0x3af8,0xdcee0);      // MOVE.W #73a,D0; JSR 3af8.L.
    case 0xdcee0:return am_call(c,0x48296,0xdcee6);                            // JSR 48296.L.
    case 0xdcee6:return am_call(c,0x1c5b0,0xdceec);                            // JSR 1c5b0.L.
    case 0xdceec:return am_call(c,0x49c66,0xdcef2);                            // JSR 49c66.L.
    case 0xdcef2:if(!am_write(c,r.a[6],4,0xdcef8))return false;r.pc=0xdcef8;return true; // MOVE.L #dcef8,(A6).
    // ---- dcef8 (installed): CMPI.W #198,5418(A5); BGE.W dcf04.
    case 0xdcef8:
        if(!am_read(c,am_index(r.a[5],ON05_PROGRESS),2,value))return false;r.pc=on05_signed_word(value)>=0x198?0xdcf04:0xdcf02;return true;
    case 0xdcf04:return am_call(c,0x482c0,0xdcf0a);                            // JSR 482c0.L.
    case 0xdcf0a:return am_call(c,0x49c32,0xdcf10);                            // JSR 49c32.L.
    // MOVE.W #294,76(A6); MOVE.L #dcf22,(A6).
    case 0xdcf16:if(!on05_put(c,0x76,2,0x294) || !am_write(c,r.a[6],4,0xdcf22))return false;r.pc=0xdcf22;return true;
    // ---- dcf22 (installed): SUBQ.W #1,76(A6); BCS.W dcf2c.
    case 0xdcf22:if(!on05_get(c,0x76,2,value) || !on05_put(c,0x76,2,(value-1U)&65535U))return false;r.pc=value==0U?0xdcf2c:0xdcf2a;return true;
    case 0xdcf2c:return on05_child(c,0x4841a,0xa,0xdcf3c);                    // MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L.
    default:return am_error(c,"unsupported animation objects n05 PC");
    }
}
}
