#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OB2B_WORK_BIT=0x10f001;    // 4d6b4: BTST.B #2,10f001.l (work RAM BYTE, absolute).
const std::uint32_t OB2B_BANK_B4=0x2000b4;     // 3acd6: MOVE.L 2000b4.l,22(A6) (banked LONG through the live bus).
const std::uint32_t OB2B_ROM_PAIR_LOW=0x3a4d6; // 3a4fa: LEA 3a4d6(PC),A4 (two signed BYTEs, fixed ROM, live bus).
const std::uint32_t OB2B_ROM_PAIR_HIGH=0x3a4d8;// 3a502: LEA 3a4d8(PC),A4.
const std::uint32_t OB2B_BLOCK_A=0x1009a8;     // 4eeac: LEA 1009a8.l,A0 (D0.W == 0).
const std::uint32_t OB2B_BLOCK_B=0x100a6c;     // 4eeb6: LEA 100a6c.l,A0 (D0.W != 0).
const std::uint32_t OB2B_PORT=0x3c0000;        // 4f094 4f0a8 4f0bc: MOVE.L D0,3c0000.l (one LONG port write each).
const std::uint32_t OB2B_PARENT=0x100bf4;      // 338d2 4ffa4 d3d86: MOVEA.L #100bf4,A1 (2986 parent node).
std::uint32_t ob2b_b(std::uint32_t value) {return value&255U;}
std::uint32_t ob2b_w(std::uint32_t value) {return value&65535U;}
// EXT.W: the BYTE sign bit refills the upper byte of the WORD (explicit, no signed conversion).
std::uint32_t ob2b_ext(std::uint32_t value) {const std::uint32_t u=value&255U;return (u&0x80U)!=0U?(u|0xff00U):u;}
bool ob2b_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob2b_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.x from(An),to(Am) with the same base for both ends (A6 or A0 or A4 node fields).
bool ob2b_copy(AnimationMachineContext& c,std::uint32_t src,std::uint32_t from,std::uint32_t dst,std::uint32_t to,unsigned int size) {
    std::uint32_t value=0;return ob2b_get(c,src,from,size,value) && ob2b_put(c,dst,to,size,value);
}
// MOVE.L #value,(A6) (installed callback LONG).
bool ob2b_install(AnimationMachineContext& c,std::uint32_t value) {return ob2b_put(c,c.s.a[6],0,4,value);}
// BTST.B #bit,d16(An): true when the bit is 1.
bool ob2b_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob2b_get(c,base,displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// Bcc / Scc on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob2b_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b2b caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ORI.B #1,CCR / ANDI.B #fe,CCR (and a MOVE / TST / ANDI.W result) followed by RTS.
bool ob2b_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {c.s.carry=carry;return am_return(c);}
// MOVEA.L #child,A0; MOVE.W #n,D0; JSR 28ae.l (the child value is data, not an execution PC of this unit).
bool ob2b_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t count,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],count);return am_call(c,0x28ae,return_pc);
}
// MOVEA.L #child,A0; MOVE.W #n,D0; MOVEA.L #100bf4,A1; JSR 2986.l (child value is data).
bool ob2b_child_2986(AnimationMachineContext& c,std::uint32_t child,std::uint32_t count,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],count);c.s.a[1]=OB2B_PARENT;return am_call(c,0x2986,return_pc);
}
// MOVE.L #x,36(A0); MOVE.L #y,3a(A0); MOVE.W #n,54(A0) (one fragment row of the destruction chains).
bool ob2b_row(AnimationMachineContext& c,std::uint32_t x,std::uint32_t y,std::uint32_t n) {
    return ob2b_put(c,c.s.a[0],0x36,4,x) && ob2b_put(c,c.s.a[0],0x3a,4,y) && ob2b_put(c,c.s.a[0],0x54,2,n);
}
// LEA 5cba(A5),A4 / LEA 5ce6(A5),A4 (slot table) with the target LEA of 4d418 (8cb8 or 8da8) or 4d4b4 (8cb8 on both paths).
void ob2b_slot(AnimationMachineState& r,bool second,std::uint32_t target) {
    r.a[4]=am_index(r.a[5],second?0x5ce6U:0x5cbaU);r.a[0]=am_index(r.a[5],target);
}
// TST.B D0; BNE second / (first); the A4 LEA of the 4d6c6 / 4d734 / 4d98a family.
void ob2b_slot_a4(AnimationMachineState& r,bool second) {r.a[4]=am_index(r.a[5],second?0x5ce6U:0x5cbaU);}
// MOVEM.L d0-d3/a0,2e(A6) (stored in register order, no flag change).
bool ob2b_save(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    return ob2b_put(c,r.a[6],0x2e,4,r.d[0]) && ob2b_put(c,r.a[6],0x32,4,r.d[1]) && ob2b_put(c,r.a[6],0x36,4,r.d[2]) &&
        ob2b_put(c,r.a[6],0x3a,4,r.d[3]) && ob2b_put(c,r.a[6],0x3e,4,r.a[0]);
}
// op.L d(An),Dm: 32-bit add or subtract of a LONG field.
bool ob2b_add_long(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t& reg,bool subtract) {
    std::uint32_t value=0;if(!ob2b_get(c,base,displacement,4,value))return false;reg=subtract?reg-value:reg+value;return true;
}
// MOVE.L D0,3c0000.l: one ordered LONG port write.
void ob2b_port(AnimationMachineContext& c,std::uint32_t value) {
    VideoPortWrite port;port.address=OB2B_PORT;port.size=4;port.value=value;c.ports.push_back(port);
}
}
// Objects B2b (209 block starts): the orphan chains 3383c (N30 destruction, 15), 3a4a4 (partner approach 3a4a4 / 3a4be / 3a4da / 3a5be, 29), 3b424
// (partner input, 6), 4bfc0 (10), 38d56 (N31 installation, 18), 39f9c / 3a0dc (N31/N32b, 54), 3acd6 (N32b child, 12), 4c390 / 4c3cc (6) and the slot
// helpers 4d418 / 4d4b4 (21), plus the 38 blocks of the shared leaf helpers 4c2fa 4d6b4 4d734 4d98a 4d9ba 4eea2 (+4f08a) 4ff96 d3d7c. Boundaries without
// an executor: 4db18 3b5a6 4b6f4 (and every callee or child value outside this unit); the child values 3ae84 2d57a 2d3ae 338f8 3a2fa 4ffba d3d9c
// are data (the 2986 / 28ae child convention), 4c3ba is an unreferenced entry fragment and is not routed. Known C: 4d490 (Set) and 4d4ac (Clear)
// return the 4d418 C; 4d4e0 returns the CMP.W borrow (4d4b4); 3a5b2 (Set) / 3a5b8 (Clear), 4d6c0 4d6e0 (Set) / 4d6ec (Clear), the MOVE / TST /
// ANDI.W / CMP results of the other helpers are Clear. The six consumers 4d438 3a4ec 3ad26 3ad3c 38d70 (SCC) 38dbe read a known C of 289e,
// 4d6b4, 288c, 49fc6, 28ae, 3b334. One banked LONG read (2000b4), the LONG ports of 4f08a, no X / DIV.
bool animation_objects_b2b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool bit=false;
    switch(r.pc) {
    // ---- RTS blocks (33950 3a4ce 3b456 4d506 keep the known C of the path that reached them) and JMP blocks.
    case 0x33950:case 0x3a4ce:case 0x3b456:case 0x4d506:case 0x3ad46:return am_return(c);
    case 0x338f2:case 0x3ad2a:case 0x3ad40:r.pc=0x2a00;return true;           // JMP 2a00.l.
    case 0x3a4b8:r.pc=0x4d418;return true;                                    // JMP 4d418.l (the C is the one 4d418 returns).
    case 0x4eeea:                                                           // MOVEM.L (A7)+,A6; MOVEM.L (A7)+,A0; RTS (MOVEM keeps the CCR).
        if(!am_pop(c,4,value))return false;r.a[6]=value;if(!am_pop(c,4,value))return false;r.a[0]=value;return am_return(c);
    // ---- 3383c: N30 destruction (installed by N30a 337a8).
    case 0x3383c:r.a[0]=0x349ee;return am_call(c,0x4ae4a,0x33846);           // LEA 349ee(PC),A0; JSR 4ae4a.l.
    case 0x33846:am_byte(r.d[1],0);return am_call(c,0x33940,0x3384e);        // MOVE.B #0,D1; JSR 33940(PC).
    case 0x3384e:r.d[0]=1;r.d[1]=0;return am_call(c,0x4ff96,0x33858);         // MOVEQ #1,D0; MOVEQ #0,D1; JSR 4ff96.l.
    case 0x33858:return am_call(c,0xd3d7c,0x3385e);                          // JSR d3d7c.l.
    case 0x3385e:if(!ob2b_row(c,0xfff20000U,0x280000U,0xa))return false;return am_call(c,0xd3d7c,0x3387a);
    case 0x3387a:if(!ob2b_row(c,0xa0000U,0x250000U,7))return false;return am_call(c,0xd3d7c,0x33896);
    case 0x33896:if(!ob2b_row(c,0xfff70000U,0x10000U,7))return false;return am_call(c,0xd3d7c,0x338b2);
    case 0x338b2:if(!ob2b_row(c,0x70000U,0xfffc0000U,5))return false;return ob2b_child_2986(c,0x338f8,0x1e,0x338de);
    case 0x338de:r.d[0]=0;r.d[1]=0x10;return am_call(c,0x49214,0x338e8);      // MOVEQ #0,D0; MOVEQ #10,D1; JSR 49214.l.
    case 0x338e8:am_word(r.d[0],0x18de);return am_call(c,0x3af8,0x338f2);     // MOVE.W #18de,D0; JSR 3af8.l.
    // ---- 33940 / 3a4be: MOVE.B D1,-(A7); JSR 4d8d8.l; MOVE.B (A7)+,D1; TST.B D0; BPL.W (JMP 4d4b4.l) / RTS (Clear).
    case 0x33940:case 0x3a4be:
        if(!am_push(c,1,ob2b_b(r.d[1])))return false;return am_call(c,0x4d8d8,r.pc==0x33940U?0x33948U:0x3a4c6U);
    case 0x33948:case 0x3a4c6:
        if(!am_pop(c,1,value))return false;am_byte(r.d[1],value);r.carry=AnimationCarryClear;
        r.pc=(r.d[0]&0x80U)==0U?(r.pc==0x33948U?0x33952U:0x3a4d0U):(r.pc==0x33948U?0x33950U:0x3a4ceU);return true;
    case 0x33952:case 0x3a4d0:r.pc=0x4d4b4;return true;                     // JMP 4d4b4.l.
    // ---- 3a4a4: MOVE.W 86(A6),D0; MOVEQ #2,D2; MOVEQ #1e,D3; BTST.B #0,15(A6); BEQ.W 3a4b8 / NEG.W D2; JMP 4d418.l.
    case 0x3a4a4:
        if(!ob2b_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],value);r.d[2]=2;r.d[3]=0x1e;
        if(!ob2b_bit(c,r.a[6],0x15,0,bit))return false;r.pc=bit?0x3a4b6:0x3a4b8;return true;
    case 0x3a4b6:am_word(r.d[2],0x10000U-ob2b_w(r.d[2]));r.pc=0x3a4b8;return true; // NEG.W D2.
    // ---- 3a4da: TST.B b2(A6); BNE.W 3a5b8.
    case 0x3a4da:if(!ob2b_get(c,r.a[6],0xb2,1,value))return false;r.pc=value!=0U?0x3a5b8:0x3a4e2;return true;
    case 0x3a4e2:                                                           // MOVE.W 86(A6),D0; JSR 4d6b4.l.
        if(!ob2b_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],value);return am_call(c,0x4d6b4,0x3a4ec);
    case 0x3a4ec:return ob2b_carry(c,0x3a5b8,0x3a4f0);                       // BCC.W 3a5b8 (C returned by 4d6b4).
    // CMPI.B #11,9f(A6); BCC.W 3a502 (BYTE >= 11 unsigned).
    case 0x3a4f0:if(!ob2b_get(c,r.a[6],0x9f,1,value))return false;r.pc=value>=0x11U?0x3a502:0x3a4fa;return true;
    case 0x3a4fa:r.a[4]=OB2B_ROM_PAIR_LOW;r.pc=0x3a506;return true;          // LEA 3a4d6(PC),A4; BRA.W 3a506.
    case 0x3a502:r.a[4]=OB2B_ROM_PAIR_HIGH;r.pc=0x3a506;return true;         // LEA 3a4d8(PC),A4.
    // MOVE.L A4,-(A7); MOVE.B #18,b2(A6); MOVEA.L #3ae84,A0; MOVE.W #a,D0; JSR 28ae.l (child 3ae84, outside this unit).
    case 0x3a506:
        if(!am_push(c,4,r.a[4]) || !ob2b_put(c,r.a[6],0xb2,1,0x18))return false;return ob2b_child(c,0x3ae84,0xa,0x3a51e);
    case 0x3a51e:r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,0x3a528);        // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.l.
    case 0x3a528:return am_call(c,0x491b6,0x3a52e);                          // JSR 491b6.l.
    // MOVEA.L (A7),A4; MOVE.B (A4)+,D2; MOVE.B (A4),D3; EXT.W D2; EXT.W D3; BTST.B #0,15(A6); BEQ.W 3a544.
    case 0x3a52e:
        if(!am_read(c,r.a[7],4,value))return false;r.a[4]=value;if(!am_read(c,r.a[4],1,value))return false;am_byte(r.d[2],value);r.a[4]+=1U;
        if(!am_read(c,r.a[4],1,value))return false;am_byte(r.d[3],value);am_word(r.d[2],ob2b_ext(r.d[2]));am_word(r.d[3],ob2b_ext(r.d[3]));
        if(!ob2b_bit(c,r.a[6],0x15,0,bit))return false;r.pc=bit?0x3a542:0x3a544;return true;
    case 0x3a542:am_word(r.d[2],0x10000U-ob2b_w(r.d[2]));r.pc=0x3a544;return true; // NEG.W D2.
    // MOVE.W D2,36(A0); MOVE.W D3,3a(A0); MOVE.W 1e(A6),1e(A0); ADDQ.W #1,1e(A0); CMPI.B #5,ae(A6); BNE.W 3a574.
    case 0x3a544:
        if(!ob2b_put(c,r.a[0],0x36,2,r.d[2]) || !ob2b_put(c,r.a[0],0x3a,2,r.d[3]) || !ob2b_copy(c,r.a[6],0x1e,r.a[0],0x1e,2))return false;
        if(!ob2b_get(c,r.a[0],0x1e,2,value) || !ob2b_put(c,r.a[0],0x1e,2,value+1U))return false;
        if(!ob2b_get(c,r.a[6],0xae,1,value))return false;r.pc=value!=5U?0x3a574:0x3a560;return true;
    case 0x3a560:return ob2b_child(c,0x2d57a,0xa,0x3a570);                   // MOVEA.L #2d57a,A0; MOVE.W #a,D0; JSR 28ae.l (child outside).
    case 0x3a570:r.pc=0x3a584;return true;                                    // BRA.W 3a584.
    case 0x3a574:return ob2b_child(c,0x2d3ae,0xa,0x3a584);                   // MOVEA.L #2d3ae,A0; ...; JSR 28ae.l (child outside).
    // MOVE.B 60(A6),60(A0); MOVEA.L (A7)+,A4; MOVE.B (A4)+,D2; MOVE.B (A4),D3; MOVEQ #0,D0; EXT.W D2; EXT.W D3; BTST.B #0,15(A6); BEQ.W 3a5a6.
    case 0x3a584:
        if(!ob2b_copy(c,r.a[6],0x60,r.a[0],0x60,1))return false;
        if(!am_pop(c,4,value))return false;r.a[4]=value;if(!am_read(c,r.a[4],1,value))return false;am_byte(r.d[2],value);r.a[4]+=1U;
        if(!am_read(c,r.a[4],1,value))return false;am_byte(r.d[3],value);r.d[0]=0;am_word(r.d[2],ob2b_ext(r.d[2]));am_word(r.d[3],ob2b_ext(r.d[3]));
        if(!ob2b_bit(c,r.a[6],0x15,0,bit))return false;r.pc=bit?0x3a5a0:0x3a5a6;return true;
    case 0x3a5a0:am_word(r.d[0],r.d[0]+0x8000U);am_word(r.d[2],0x10000U-ob2b_w(r.d[2]));r.pc=0x3a5a6;return true; // ADDI.W #8000,D0; NEG.W D2.
    // MOVE.W D0,76(A0); MOVEQ #ff,D0; JSR 4c2fa.l.
    case 0x3a5a6:if(!ob2b_put(c,r.a[0],0x76,2,r.d[0]))return false;r.d[0]=0xffffffffU;return am_call(c,0x4c2fa,0x3a5b2);
    case 0x3a5b2:return ob2b_return_carry(c,AnimationCarrySet);              // ORI.B #1,CCR; RTS.
    case 0x3a5b8:return ob2b_return_carry(c,AnimationCarryClear);            // ANDI.B #fe,CCR; RTS.
    // ---- 3a5be: ST.B 97(A6); MOVE.B 9a(A6),99(A6); JSR (A0) (live target; the original has no filter).
    case 0x3a5be:
        if(!ob2b_put(c,r.a[6],0x97,1,0xff) || !ob2b_copy(c,r.a[6],0x9a,r.a[6],0x99,1))return false;return am_call(c,r.a[0],0x3a5ca);
    case 0x3a5ca:                                                           // MOVE.B 99(A6),9a(A6); RTS (MOVE leaves C = 0).
        if(!ob2b_copy(c,r.a[6],0x99,r.a[6],0x9a,1))return false;return ob2b_return_carry(c,AnimationCarryClear);
    // ---- 3b424: MOVE.W 86(A6),D0; JSR 49be0.l.
    case 0x3b424:
        if(!ob2b_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],value);return am_call(c,0x49be0,0x3b42e);
    // MOVE.L (A0),D7; SWAP D7; MOVEQ #ff,D0; MOVE.W D0,D1; SWAP D0; MOVE.W D1,D0; AND.L D7,D0; AND.B 9e(A6),D0; OR.B D0,9d(A6); RTS.
    case 0x3b42e:
        if(!am_read(c,r.a[0],4,value))return false;r.d[7]=(value<<16)|(value>>16);am_word(r.d[1],0xffffU);r.d[0]=r.d[7];
        if(!ob2b_get(c,r.a[6],0x9e,1,value))return false;am_byte(r.d[0],r.d[0]&value);
        if(!ob2b_get(c,r.a[6],0x9d,1,value) || !ob2b_put(c,r.a[6],0x9d,1,value|ob2b_b(r.d[0])))return false;
        return ob2b_return_carry(c,AnimationCarryClear);
    case 0x3b446:return am_call(c,0x3b424,0x3b448);                          // BSR.B 3b424.
    case 0x3b448:                                                           // BTST.B #7,15(A6); BEQ.W 3b456 (C unchanged).
        if(!ob2b_bit(c,r.a[6],0x15,7,bit))return false;r.pc=bit?0x3b452:0x3b456;return true;
    case 0x3b452:am_word(r.d[0],r.d[0]&0xfdfdU);r.carry=AnimationCarryClear;r.pc=0x3b456;return true; // ANDI.W #fdfd,D0.
    // ---- 4bfc0.
    case 0x4bfc0:return am_call(c,0x4bce0,0x4bfc4);                          // BSR.W 4bce0.
    case 0x4bfc4:return am_call(c,0x4c020,0x4bfc8);                          // BSR.W 4c020.
    case 0x4bfc8:return am_call(c,0x4b8e8,0x4bfce);                          // JSR 4b8e8.l.
    // ADD.B D7,D7; BCC.W 4bf0a (the ADD carry is the old bit 7 of D7.B and is consumed here).
    case 0x4bfce:bit=(r.d[7]&0x80U)!=0U;am_byte(r.d[7],r.d[7]<<1);r.pc=bit?0x4bfd4:0x4bf0a;return true;
    case 0x4bfd4:return am_call(c,0x469d8,0x4bfda);                          // JSR 469d8.l.
    // MOVE.L 36(A6),D2; MOVE.L 3a(A6),D3; MOVEA.L 3e(A6),A1; CMPA.W #0,A1; BEQ.W 4bffe.
    case 0x4bfda:
        if(!ob2b_get(c,r.a[6],0x36,4,value))return false;r.d[2]=value;if(!ob2b_get(c,r.a[6],0x3a,4,value))return false;r.d[3]=value;
        if(!ob2b_get(c,r.a[6],0x3e,4,value))return false;r.a[1]=value;r.pc=r.a[1]==0U?0x4bffe:0x4bfee;return true;
    // ADD.L 14(A1),D2; SUB.L 1c(A1),D2; ADD.L 18(A1),D3; SUB.L 20(A1),D3.
    case 0x4bfee:
        if(!ob2b_add_long(c,r.a[1],0x14,r.d[2],false) || !ob2b_add_long(c,r.a[1],0x1c,r.d[2],true) ||
            !ob2b_add_long(c,r.a[1],0x18,r.d[3],false) || !ob2b_add_long(c,r.a[1],0x20,r.d[3],true))return false;
        r.pc=0x4bffe;return true;
    case 0x4bffe:r.pc=r.a[0]==0U?0x4c016:0x4c006;return true;                // CMPA.W #0,A0; BEQ.W 4c016.
    // SUB.L 14(A0),D2; ADD.L 1c(A0),D2; SUB.L 18(A0),D3; ADD.L 20(A0),D3.
    case 0x4c006:
        if(!ob2b_add_long(c,r.a[0],0x14,r.d[2],true) || !ob2b_add_long(c,r.a[0],0x1c,r.d[2],false) ||
            !ob2b_add_long(c,r.a[0],0x18,r.d[3],true) || !ob2b_add_long(c,r.a[0],0x20,r.d[3],false))return false;
        r.pc=0x4c016;return true;
    case 0x4c016:if(!ob2b_save(c))return false;r.pc=0x4bf16;return true;      // MOVEM.L D0-D3/A0,2e(A6); BRA.W 4bf16.
    // ---- 38d56: N31 installation.
    case 0x38d56:if(!ob2b_put(c,r.a[6],0xb5,1,0xff))return false;return am_call(c,0x3b5a6,0x38d60); // MOVE.B #ff,b5(A6); JSR 3b5a6(PC) (boundary).
    case 0x38d60:return ob2b_child(c,0x3af86,0xa,0x38d70);                   // MOVEA.L #3af86,A0; MOVE.W #a,D0; JSR 28ae.l (child outside).
    case 0x38d70:                                                           // SCC.B 62(A6) (C returned by 28ae); JSR 4972c.l.
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects b2b caller requires known carry");
        if(!ob2b_put(c,r.a[6],0x62,1,r.carry==AnimationCarryClear?0xffU:0U))return false;return am_call(c,0x4972c,0x38d7a);
    case 0x38d7a:if(!ob2b_install(c,0x38d80))return false;r.pc=0x38d80;return true; // MOVE.L #38d80,(A6).
    case 0x38d80:if(!ob2b_get(c,r.a[6],0x62,1,value))return false;r.pc=value!=0U?0x38d9c:0x38d88;return true; // TST.B 62(A6); BNE.W 38d9c.
    case 0x38d88:return am_call(c,0x3b288,0x38d8c);                          // JSR 3b288(PC).
    case 0x38d8c:return am_call(c,0x3b334,0x38d90);                          // JSR 3b334(PC).
    case 0x38d90:am_word(r.d[0],0x1e);return am_call(c,0x3b2ee,0x38d98);      // MOVE.W #1e,D0; JSR 3b2ee(PC).
    case 0x38d98:case 0x38dd0:r.pc=0x3a350;return true;                       // BRA.W 3a350 (N31).
    case 0x38d9c:am_word(r.d[0],0x1a60);return am_call(c,0x3af8,0x38da6);     // MOVE.W #1a60,D0; JSR 3af8.l.
    case 0x38da6:r.a[0]=0x3b8a6;return am_call(c,0x3b302,0x38db0);            // MOVEA.L #3b8a6,A0; JSR 3b302(PC).
    case 0x38db0:if(!ob2b_install(c,0x38db6))return false;r.pc=0x38db6;return true; // MOVE.L #38db6,(A6).
    case 0x38db6:return am_call(c,0x3b288,0x38dba);                          // JSR 3b288(PC).
    case 0x38dba:return am_call(c,0x3b334,0x38dbe);                          // JSR 3b334(PC).
    case 0x38dbe:return ob2b_carry(c,0x38dc8,0x38dc2);                       // BCC.W 38dc8 (C returned by 3b334).
    case 0x38dc2:if(!ob2b_install(c,0x39366))return false;r.pc=0x38dc8;return true; // MOVE.L #39366,(A6).
    case 0x38dc8:am_word(r.d[0],0x1e);return am_call(c,0x3b2ee,0x38dd0);      // MOVE.W #1e,D0; JSR 3b2ee(PC).
    // ---- 39f9c: N32b installation (fragments).
    case 0x39f9c:am_word(r.d[0],0x1ac8);return am_call(c,0x3c44,0x39fa6);     // MOVE.W #1ac8,D0; JSR 3c44.l.
    case 0x39fa6:r.a[0]=0x3b7ce;return am_call(c,0x4ae4a,0x39fb0);            // LEA 3b7ce(PC),A0; JSR 4ae4a.l.
    case 0x39fb0:r.d[0]=1;r.d[1]=0;return am_call(c,0x4ff96,0x39fba);         // MOVEQ #1,D0; MOVEQ #0,D1; JSR 4ff96.l.
    case 0x39fba:return am_call(c,0xd3d7c,0x39fc0);                          // JSR d3d7c.l.
    case 0x39fc0:if(!ob2b_row(c,0xfff20000U,0x280000U,0xa))return false;return am_call(c,0xd3d7c,0x39fdc);
    case 0x39fdc:if(!ob2b_row(c,0xa0000U,0x250000U,7))return false;return am_call(c,0xd3d7c,0x39ff8);
    case 0x39ff8:if(!ob2b_row(c,0xfff70000U,0xffff0000U,7))return false;return am_call(c,0xd3d7c,0x3a014);
    case 0x3a014:if(!ob2b_row(c,0x70000U,0xfffc0000U,5))return false;return ob2b_child(c,0x3a2fa,0x1e,0x3a03a); // child 3a2fa (N31).
    case 0x3a03a:r.d[0]=0;r.d[1]=0x10;return am_call(c,0x49214,0x3a044);      // MOVEQ #0,D0; MOVEQ #10,D1; JSR 49214.l.
    case 0x3a044:r.pc=0x3a2f4;return true;                                    // BRA.W 3a2f4 (N31).
    // ---- 3a0dc: MOVE.B 5e(A6),D0; CMPI.B #1b,D0; BCC.W 3a160.
    case 0x3a0dc:
        if(!ob2b_get(c,r.a[6],0x5e,1,value))return false;am_byte(r.d[0],value);r.pc=value>=0x1bU?0x3a160:0x3a0e8;return true;
    // ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; JMP 3a0f4(PC,D0.W): the 27 BRA.W slots (no limit test here, as in the original).
    case 0x3a0e8:
        am_word(r.d[0],r.d[0]&255U);am_word(r.d[0],r.d[0]*2U);am_word(r.d[0],r.d[0]*2U);r.pc=(0x3a0f4U+am_extend_word(r.d[0]))&0xffffffU;return true;
    case 0x3a154:r.pc=0x3a24c;return true;                                    // BRA.W 3a24c (N33).
    case 0x3a0f4:case 0x3a0f8:case 0x3a0fc:case 0x3a100:case 0x3a104:case 0x3a108:case 0x3a10c:case 0x3a110:case 0x3a114:case 0x3a118:
    case 0x3a11c:case 0x3a120:case 0x3a124:case 0x3a128:case 0x3a12c:case 0x3a130:case 0x3a134:case 0x3a138:case 0x3a13c:case 0x3a140:
    case 0x3a144:case 0x3a148:case 0x3a14c:case 0x3a150:case 0x3a158:case 0x3a15c:r.pc=0x3a160;return true;       // BRA.W 3a160.
    case 0x3a160:return am_call(c,0x4d8d8,0x3a166);                          // JSR 4d8d8.l.
    case 0x3a166:r.pc=(r.d[0]&0x8000U)!=0U?0x3a1a0:0x3a16c;return true;      // TST.W D0; BMI.W 3a1a0.
    case 0x3a16c:if(!ob2b_get(c,r.a[6],0x9f,1,value))return false;r.pc=value>=8U?0x3a188:0x3a176;return true; // CMPI.B #8,9f(A6); BCC.W 3a188.
    case 0x3a176:r.a[0]=0x3b94e;return am_call(c,0x3b302,0x3a180);            // MOVEA.L #3b94e,A0; JSR 3b302(PC).
    case 0x3a180:r.d[0]=2;r.d[1]=0x40;r.pc=0x3a196;return true;               // MOVEQ #2,D0; MOVEQ #40,D1; BRA.W 3a196.
    case 0x3a188:r.a[0]=0x3b954;return am_call(c,0x3b302,0x3a192);            // MOVEA.L #3b954,A0; JSR 3b302(PC).
    case 0x3a192:r.d[0]=2;r.d[1]=0x30;r.pc=0x3a196;return true;               // MOVEQ #2,D0; MOVEQ #30,D1.
    case 0x3a196:if(!ob2b_put(c,r.a[6],0x95,1,5))return false;r.pc=0x3a1b2;return true; // MOVE.B #5,95(A6); BRA.W 3a1b2.
    case 0x3a1a0:r.a[0]=0x3b8a0;return am_call(c,0x3b302,0x3a1aa);            // MOVEA.L #3b8a0,A0; JSR 3b302(PC).
    case 0x3a1aa:return am_call(c,0x3a5d2,0x3a1ae);                          // JSR 3a5d2(PC) (N33).
    case 0x3a1ae:r.d[0]=2;r.d[1]=0x30;r.pc=0x3a1b2;return true;               // MOVEQ #2,D0; MOVEQ #30,D1.
    case 0x3a1b2:return am_call(c,0x4db18,0x3a1b8);                          // JSR 4db18.l (boundary).
    case 0x3a1b8:if(!ob2b_put(c,r.a[6],0x7e,4,0x3b68a))return false;return am_call(c,0x496c2,0x3a1c6); // MOVE.L #3b68a,7e(A6); JSR 496c2.l.
    // CLR.B a4(A6); MOVE.B #60,a7(A6); MOVE.W #1ac8,D0; JSR 3af8.l.
    case 0x3a1c6:if(!ob2b_put(c,r.a[6],0xa4,1,0) || !ob2b_put(c,r.a[6],0xa7,1,0x60))return false;am_word(r.d[0],0x1ac8);return am_call(c,0x3af8,0x3a1da);
    case 0x3a1da:if(!ob2b_install(c,0x3a1e0))return false;r.pc=0x3a1e0;return true; // MOVE.L #3a1e0,(A6) (falls into N33 3a1e0).
    // ---- 3acd6: N32b child (short effect).
    case 0x3acd6:
        if(!ob2b_put(c,r.a[6],0x20,2,0x122) || !am_read(c,OB2B_BANK_B4,4,value) || !ob2b_put(c,r.a[6],0x22,4,value))return false;
        if(!ob2b_get(c,r.a[6],0x15,1,value) || !ob2b_put(c,r.a[6],0x15,1,value|0x40U))return false; // BSET.B #6,15(A6).
        if(!ob2b_put(c,r.a[6],0x68,2,0xe000) || !ob2b_put(c,r.a[6],0x1e,2,0xe000))return false;
        r.a[1]=0x3ccfc;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x3ad06);  // MOVEA.L #3ccfc,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x3ad06:am_word(r.d[0],0xdb3);am_byte(r.d[1],0);return am_call(c,0x8ebe,0x3ad14); // MOVE.W #db3,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0x3ad14:return am_call(c,0x49274,0x3ad1a);                          // JSR 49274.l.
    case 0x3ad1a:if(!ob2b_install(c,0x3ad20))return false;r.pc=0x3ad20;return true; // MOVE.L #3ad20,(A6).
    case 0x3ad20:return am_call(c,0x288c,0x3ad26);                           // JSR 288c.l.
    case 0x3ad26:return ob2b_carry(c,0x3ad2a,0x3ad30);                       // BCS.W 3ad30 (C returned by 288c).
    case 0x3ad30:return am_call(c,0x43e34,0x3ad36);                          // JSR 43e34.l.
    case 0x3ad36:return am_call(c,0x49fc6,0x3ad3c);                          // JSR 49fc6.l.
    case 0x3ad3c:return ob2b_carry(c,0x3ad46,0x3ad40);                       // BCC.W 3ad46 (C returned by 49fc6).
    // ---- 4c390 / 4c3a2 / 4c3cc: MOVE.L A0,5c8e(A5); JSR 4bce0(PC) or 4bc44(PC) and the BYTE settings, BRA.W 4c810 (N34).
    case 0x4c390:case 0x4c3a2:case 0x4c3cc:
        if(!ob2b_put(c,r.a[5],0x5c8e,4,r.a[0]))return false;
        if(r.pc==0x4c390U)return am_call(c,0x4bce0,0x4c398);
        if(r.pc==0x4c3a2U)return am_call(c,0x4bc44,0x4c3aa);
        return am_call(c,0x4bce0,0x4c3d4);
    case 0x4c398:if(!ob2b_put(c,r.a[5],0x5cb4,1,0))return false;r.pc=0x4c810;return true;
    case 0x4c3aa:if(!ob2b_put(c,r.a[5],0x549f,1,0xff) || !ob2b_put(c,r.a[5],0x5cb4,1,0))return false;r.pc=0x4c810;return true;
    case 0x4c3d4:if(!ob2b_put(c,r.a[5],0x5cb4,1,0xff))return false;r.pc=0x4c810;return true;
    // ---- 4d418: slot test (D0.B = table choice, D2/D3 = offsets, A6 = node). Returns C Set (4d490) or Clear (4d4ac).
    case 0x4d418:r.pc=ob2b_b(r.d[0])!=0U?0x4d42a:0x4d41e;return true;        // TST.B D0; BNE.W 4d42a.
    case 0x4d41e:ob2b_slot(r,false,0x8cb8);r.pc=0x4d432;return true;           // LEA 5cba(A5),A4; LEA -7348(A5),A0; BRA.W 4d432.
    case 0x4d42a:ob2b_slot(r,true,0x8da8);r.pc=0x4d432;return true;            // LEA 5ce6(A5),A4; LEA -7258(A5),A0.
    case 0x4d432:return am_call(c,0x289e,0x4d438);                           // JSR 289e.l.
    case 0x4d438:return ob2b_carry(c,0x4d4ac,0x4d43c);                       // BCC.W 4d4ac (C returned by 289e).
    case 0x4d43c:if(!ob2b_bit(c,r.a[0],0x61,7,bit))return false;r.pc=bit?0x4d4ac:0x4d446;return true; // BTST.B #7,61(A0); BNE.W 4d4ac.
    // MOVE.L A6,D7; MOVE.W (A4),D0; BEQ.W 4d454.
    case 0x4d446:
        r.d[7]=r.a[6];if(!ob2b_get(c,r.a[4],0,2,value))return false;am_word(r.d[0],value);r.pc=value==0U?0x4d454:0x4d44e;return true;
    case 0x4d44e:r.pc=ob2b_w(r.d[7])==ob2b_w(r.d[0])?0x4d454:0x4d4ac;return true; // CMP.W D0,D7; BNE.W 4d4ac.
    // MOVE.W D2,2(A4); MOVE.W D3,4(A4); MOVE.L 3e(A6),c(A4); MOVE.L 2e(A6),10(A4); MOVE.L 32(A6),14(A4); TST.B 22(A4); BNE.W 4d4ac.
    case 0x4d454:
        if(!ob2b_put(c,r.a[4],2,2,r.d[2]) || !ob2b_put(c,r.a[4],4,2,r.d[3]))return false;
        if(!ob2b_copy(c,r.a[6],0x3e,r.a[4],0xc,4) || !ob2b_copy(c,r.a[6],0x2e,r.a[4],0x10,4) || !ob2b_copy(c,r.a[6],0x32,r.a[4],0x14,4))return false;
        if(!ob2b_get(c,r.a[4],0x22,1,value))return false;r.pc=value!=0U?0x4d4ac:0x4d476;return true;
    // MOVE.W D7,(A4); MOVE.B #ff,22(A4); MOVE.W -7ff2(A5),18(A4); MOVE.B 5e(A6),D0; BEQ.W 4d490.
    case 0x4d476:
        if(!ob2b_put(c,r.a[4],0,2,r.d[7]) || !ob2b_put(c,r.a[4],0x22,1,0xff) || !ob2b_copy(c,r.a[5],0x800e,r.a[4],0x18,2))return false;
        if(!ob2b_get(c,r.a[6],0x5e,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x4d490:0x4d48c;return true;
    case 0x4d48c:if(!ob2b_put(c,r.a[4],0x24,1,r.d[0]))return false;r.pc=0x4d490;return true; // MOVE.B D0,24(A4).
    // MOVE.B 60(A0),60(A6); MOVE.B #1,23(A4); MOVE.B 15(A6),28(A4); MOVE.W 76(A0),D0; ORI.B #1,CCR; RTS.
    case 0x4d490:
        if(!ob2b_copy(c,r.a[0],0x60,r.a[6],0x60,1) || !ob2b_put(c,r.a[4],0x23,1,1) || !ob2b_copy(c,r.a[6],0x15,r.a[4],0x28,1))return false;
        if(!ob2b_get(c,r.a[0],0x76,2,value))return false;am_word(r.d[0],value);return ob2b_return_carry(c,AnimationCarrySet);
    case 0x4d4ac:r.d[0]=0;return ob2b_return_carry(c,AnimationCarryClear);   // ANDI.B #fe,CCR; MOVEQ #0,D0; RTS.
    // ---- 4d4b4: MOVE.B 15(A6),D2; MOVEM.L D0-D1,-(A7); JSR 4eea2.l.
    case 0x4d4b4:
        if(!ob2b_get(c,r.a[6],0x15,1,value))return false;am_byte(r.d[2],value);
        if(!am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;return am_call(c,0x4eea2,0x4d4c2);
    case 0x4d4c2:                                                           // MOVEM.L (A7)+,D0-D1; TST.B D0; BNE.W 4d4d8.
        if(!am_pop(c,4,value))return false;r.d[0]=value;if(!am_pop(c,4,value))return false;r.d[1]=value;r.pc=ob2b_b(r.d[0])!=0U?0x4d4d8:0x4d4cc;return true;
    case 0x4d4cc:ob2b_slot(r,false,0x8cb8);r.pc=0x4d4e0;return true;           // LEA 5cba(A5),A4; LEA -7348(A5),A0; BRA.W 4d4e0.
    case 0x4d4d8:ob2b_slot(r,true,0x8cb8);r.pc=0x4d4e0;return true;            // LEA 5ce6(A5),A4; LEA -7348(A5),A0 (the original reuses 8cb8).
    // MOVE.L A6,D7; CMP.W (A4),D7; BNE.W 4d506 (C = borrow of D7.W - (A4).W, returned unchanged by the RTS at 4d506).
    case 0x4d4e0:
        r.d[7]=r.a[6];if(!ob2b_get(c,r.a[4],0,2,value))return false;r.carry=value>ob2b_w(r.d[7])?AnimationCarrySet:AnimationCarryClear;
        r.pc=value==ob2b_w(r.d[7])?0x4d4e8:0x4d506;return true;
    // MOVE.W #0,(A4); MOVE.B #2,22(A4); MOVE.B D1,23(A4); MOVE.B D2,28(A4); MOVE.B 5e(A6),D0; BEQ.W 4d506 (MOVE: C = 0).
    case 0x4d4e8:
        if(!ob2b_put(c,r.a[4],0,2,0) || !ob2b_put(c,r.a[4],0x22,1,2) || !ob2b_put(c,r.a[4],0x23,1,r.d[1]) || !ob2b_put(c,r.a[4],0x28,1,r.d[2]))return false;
        if(!ob2b_get(c,r.a[6],0x5e,1,value))return false;am_byte(r.d[0],value);r.carry=AnimationCarryClear;r.pc=value==0U?0x4d506:0x4d502;return true;
    case 0x4d502:if(!ob2b_put(c,r.a[4],0x24,1,r.d[0]))return false;r.carry=AnimationCarryClear;r.pc=0x4d506;return true; // MOVE.B D0,24(A4).
    // ---- 4c2fa: JSR 4bc44(PC) / MOVE.B #2,D1; SUB.B D0,D1; BCC.W 4c30a / MOVEQ #0,D1 / ... / JSR 469d8.l / ... ANDI.W #3,D6; RTS.
    case 0x4c2fa:return am_call(c,0x4bc44,0x4c2fe);
    case 0x4c2fe:
        bit=ob2b_b(r.d[0])>2U;am_byte(r.d[1],2U-r.d[0]);r.pc=bit?0x4c308:0x4c30a;return true;
    case 0x4c308:r.d[1]=0;r.pc=0x4c30a;return true;                          // MOVEQ #0,D1.
    // MOVE.B D1,549c(A5); MOVE.L A0,-(A7); MOVEA.L 3e(A6),A0; MOVE.L 2e(A6),D0; MOVE.L 32(A6),D1; SWAP D2; SWAP D3; CLR.W D2; CLR.W D3; JSR 469d8.l.
    case 0x4c30a:
        if(!ob2b_put(c,r.a[5],0x549c,1,r.d[1]) || !am_push(c,4,r.a[0]))return false;
        if(!ob2b_get(c,r.a[6],0x3e,4,value))return false;r.a[0]=value;if(!ob2b_get(c,r.a[6],0x2e,4,value))return false;r.d[0]=value;
        if(!ob2b_get(c,r.a[6],0x32,4,value))return false;r.d[1]=value;am_swap(r.d[2]);am_swap(r.d[3]);am_word(r.d[2],0);am_word(r.d[3],0);
        return am_call(c,0x469d8,0x4c32a);
    // MOVEA.L A0,A1; MOVEA.L (A7)+,A0; MOVE.L D0,2e(A0); MOVE.L D1,32(A0); MOVE.L A1,3e(A0); ANDI.W #3,D6; RTS.
    case 0x4c32a:
        r.a[1]=r.a[0];if(!am_pop(c,4,value))return false;r.a[0]=value;
        if(!ob2b_put(c,r.a[0],0x2e,4,r.d[0]) || !ob2b_put(c,r.a[0],0x32,4,r.d[1]) || !ob2b_put(c,r.a[0],0x3e,4,r.a[1]))return false;
        am_word(r.d[6],r.d[6]&3U);return ob2b_return_carry(c,AnimationCarryClear);
    // ---- 4d6b4: BTST.B #2,10f001.l; BEQ.W 4d6c6 / ORI.B #1,CCR; RTS (Set).
    case 0x4d6b4:if(!am_read(c,OB2B_WORK_BIT,1,value))return false;r.pc=(value&4U)==0U?0x4d6c6:0x4d6c0;return true;
    case 0x4d6c0:return ob2b_return_carry(c,AnimationCarrySet);
    case 0x4d6c6:r.pc=ob2b_b(r.d[0])!=0U?0x4d6d4:0x4d6cc;return true;         // TST.B D0; BNE.W 4d6d4.
    case 0x4d6cc:ob2b_slot_a4(r,false);r.pc=0x4d6d8;return true;               // LEA 5cba(A5),A4; BRA.W 4d6d8.
    case 0x4d6d4:ob2b_slot_a4(r,true);r.pc=0x4d6d8;return true;                // LEA 5ce6(A5),A4.
    case 0x4d6d8:if(!ob2b_get(c,r.a[4],0x25,1,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0x4d6ec:0x4d6e0;return true; // MOVE.B 25(A4),D0; BEQ.W.
    case 0x4d6e0:                                                           // SUBQ.B #1,D0; MOVE.B D0,25(A4); ORI.B #1,CCR; RTS (Set).
        am_byte(r.d[0],r.d[0]-1U);if(!ob2b_put(c,r.a[4],0x25,1,r.d[0]))return false;return ob2b_return_carry(c,AnimationCarrySet);
    case 0x4d6ec:return ob2b_return_carry(c,AnimationCarryClear);            // ANDI.B #fe,CCR; RTS.
    // ---- 4d734: slot choice, BTST.B #7,61(A6); BNE.W 4d75e / MOVE.W 1a(A4),D0; ADD.W D0,54(A6); MOVE.W #0,1a(A4) / MOVE.W 54(A6),1c(A4); RTS.
    case 0x4d734:r.pc=ob2b_b(r.d[0])!=0U?0x4d742:0x4d73a;return true;         // TST.B D0; BNE.W 4d742.
    case 0x4d73a:ob2b_slot_a4(r,false);r.pc=0x4d746;return true;               // LEA 5cba(A5),A4; BRA.W 4d746.
    case 0x4d742:ob2b_slot_a4(r,true);r.pc=0x4d746;return true;                // LEA 5ce6(A5),A4.
    case 0x4d746:if(!ob2b_bit(c,r.a[6],0x61,7,bit))return false;r.pc=bit?0x4d75e:0x4d750;return true; // BTST.B #7,61(A6); BNE.W 4d75e.
    case 0x4d750:
        if(!ob2b_get(c,r.a[4],0x1a,2,value))return false;am_word(r.d[0],value);
        if(!ob2b_get(c,r.a[6],0x54,2,other) || !ob2b_put(c,r.a[6],0x54,2,other+value) || !ob2b_put(c,r.a[4],0x1a,2,0))return false;
        r.pc=0x4d75e;return true;
    case 0x4d75e:if(!ob2b_copy(c,r.a[6],0x54,r.a[4],0x1c,2))return false;return ob2b_return_carry(c,AnimationCarryClear); // MOVE.W 54(A6),1c(A4); RTS.
    // ---- 4d98a: slot choice, MOVE.B D7,29(A4); RTS.
    case 0x4d98a:r.pc=ob2b_b(r.d[0])!=0U?0x4d998:0x4d990;return true;         // TST.B D0; BNE.W 4d998.
    case 0x4d990:ob2b_slot_a4(r,false);r.pc=0x4d99c;return true;               // LEA 5cba(A5),A4; BRA.W 4d99c.
    case 0x4d998:ob2b_slot_a4(r,true);r.pc=0x4d99c;return true;                // LEA 5ce6(A5),A4.
    case 0x4d99c:if(!ob2b_put(c,r.a[4],0x29,1,r.d[7]))return false;return ob2b_return_carry(c,AnimationCarryClear);
    // ---- 4d9ba: MOVEA.L A6,A0; LEA 5cba(A5),A4; TST.B D0; BEQ.W 4d9ca / LEA 5ce6(A5),A4 / MOVE.L A0,D0; MOVE.W D0,6(A4); MOVE.L A1,8(A4); RTS.
    case 0x4d9ba:r.a[0]=r.a[6];ob2b_slot_a4(r,false);r.pc=ob2b_b(r.d[0])==0U?0x4d9ca:0x4d9c6;return true;
    case 0x4d9c6:ob2b_slot_a4(r,true);r.pc=0x4d9ca;return true;                // LEA 5ce6(A5),A4.
    case 0x4d9ca:
        r.d[0]=r.a[0];if(!ob2b_put(c,r.a[4],6,2,r.d[0]) || !ob2b_put(c,r.a[4],8,4,r.a[1]))return false;return ob2b_return_carry(c,AnimationCarryClear);
    // ---- 4eea2: MOVEM.L A0,-(A7); TST.W D0; BNE.W 4eeb6 / LEA 1009a8.l,A0 / LEA 100a6c.l,A0; six WORD clears; MOVEM.L A6,-(A7); MOVEA.L A0,A6; BSR.W 4f08a.
    case 0x4eea2:if(!am_push(c,4,r.a[0]))return false;r.pc=ob2b_w(r.d[0])!=0U?0x4eeb6:0x4eeac;return true;
    case 0x4eeac:r.a[0]=OB2B_BLOCK_A;r.pc=0x4eebc;return true;                // LEA 1009a8.l,A0; BRA.W 4eebc.
    case 0x4eeb6:r.a[0]=OB2B_BLOCK_B;r.pc=0x4eebc;return true;                // LEA 100a6c.l,A0.
    case 0x4eebc:
        if(!ob2b_put(c,r.a[0],0x88,2,0) || !ob2b_put(c,r.a[0],0x8a,2,0) || !ob2b_put(c,r.a[0],0x8c,2,0) || !ob2b_put(c,r.a[0],0x8e,2,0) ||
            !ob2b_put(c,r.a[0],0x90,2,0) || !ob2b_put(c,r.a[0],0x94,2,0))return false;
        if(!am_push(c,4,r.a[6]))return false;r.a[6]=r.a[0];return am_call(c,0x4f08a,0x4eeea);
    // ---- 4f08a: MOVE.W 80(A6),D0; SWAP D0; MOVE.W #320,D0; MOVE.L D0,3c0000.l; ADDI.L #200000,D0; MOVE.W #5,D2; MOVE.W #320,D0.
    case 0x4f08a:
        if(!ob2b_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[0],value);am_swap(r.d[0]);am_word(r.d[0],0x320);
        ob2b_port(c,r.d[0]);r.d[0]+=0x200000U;am_word(r.d[2],5);am_word(r.d[0],0x320);r.pc=0x4f0a8;return true;
    // MOVE.L D0,3c0000.l; ADDI.L #200000,D0; SUBQ.W #1,D2; BNE.B 4f0a8.
    case 0x4f0a8:
        ob2b_port(c,r.d[0]);r.d[0]+=0x200000U;am_word(r.d[2],r.d[2]-1U);r.pc=ob2b_w(r.d[2])!=0U?0x4f0a8:0x4f0b8;return true;
    // MOVE.W #320,D0; MOVE.L D0,3c0000.l; RTS (MOVE: C = 0).
    case 0x4f0b8:am_word(r.d[0],0x320);ob2b_port(c,r.d[0]);return ob2b_return_carry(c,AnimationCarryClear);
    // ---- 4ff96: MOVE.W D0,-(A7); MOVE.B D1,-(A7); MOVEA.L #4ffba,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.l (child 4ffba is data).
    case 0x4ff96:
        if(!am_push(c,2,ob2b_w(r.d[0])) || !am_push(c,1,ob2b_b(r.d[1])))return false;return ob2b_child_2986(c,0x4ffba,0x14,0x4ffb0);
    case 0x4ffb0:                                                           // MOVE.B (A7)+,78(A0); MOVE.W (A7)+,76(A0); RTS (MOVE: C = 0).
        if(!am_pop(c,1,value) || !ob2b_put(c,r.a[0],0x78,1,value) || !am_pop(c,2,value) || !ob2b_put(c,r.a[0],0x76,2,value))return false;
        return ob2b_return_carry(c,AnimationCarryClear);
    // ---- d3d7c: MOVEA.L #d3d9c,A0; MOVE.W #1e,D0; MOVEA.L #100bf4,A1; JSR 2986.l (child d3d9c is data) / MOVEQ #0,D0; MOVEQ #0,D1; JMP 49214.l.
    case 0xd3d7c:return ob2b_child_2986(c,0xd3d9c,0x1e,0xd3d92);
    case 0xd3d92:r.d[0]=0;r.d[1]=0;r.pc=0x49214;return true;
    default:return am_error(c,"unsupported animation objects b2b PC");
    }
}
}
