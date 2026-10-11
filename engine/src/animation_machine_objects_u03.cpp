#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// PC relative data operands (fixed ROM, read through the live bus).
const std::uint32_t OV_PAIR_TABLE=0xe7c44;  // e8758 LEA e7c44(PC),A1 (LONG: tile WORD, key WORD; key 0 ends)
const std::uint32_t OV_FONT_48=0xe7cc8;     // e85b2 LEA e7cc8(PC),A1 (WORD x 256)
const std::uint32_t OV_FONT_4B=0xe7ec8;     // e85c2 LEA e7ec8(PC),A1
const std::uint32_t OV_FONT_6B=0xe80c8;     // e869c LEA e80c8(PC),A1
const std::uint32_t OV_FONT_68=0xe82c8;     // e868c LEA e82c8(PC),A1
const std::uint32_t OV_VRAM_PORT=0x3c0000;  // MOVE.L D0,3c0000.l
// MOVE.L D0,3c0000.l: one original LONG write is one observed video event (no device state).
void ov_port(AnimationMachineContext& c,std::uint32_t value) {
    VideoPortWrite port;port.address=OV_VRAM_PORT;port.size=4;port.value=value;c.ports.push_back(port);
}
// ADD.B/ADD.W/ADDI.W on a data register (upper bits kept).
void ov_add_byte(std::uint32_t& d,std::uint32_t src) {am_byte(d,(d+src)&255U);}
void ov_add_word(std::uint32_t& d,std::uint32_t src) {am_word(d,(d+src)&65535U);}
// MOVE.B (A0)+,Dn / MOVE.B (A0),Dn.
bool ov_string_byte(AnimationMachineContext& c,std::uint32_t& d,bool advance) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[0],1,value))return false;am_byte(d,value);
    if(advance)c.s.a[0]+=1U;return true;
}
// SWAP D0; MOVE.W D1,D0; MOVE.B #fill,D0; LSL.W #4,D0; MOVE.B D2,D0 (the shared tile head of e8576/e85e6/e864c/e87aa/e886a).
void ov_tile_head(AnimationMachineState& r,std::uint32_t fill) {
    am_swap(r.d[0]);am_word(r.d[0],r.d[1]);am_byte(r.d[0],fill);am_word(r.d[0],(r.d[0]<<4)&65535U);am_byte(r.d[0],r.d[2]);
}
// SWAP D0; MOVE.W D1,D0; LSL.W #4,D0; ANDI.W #f000,D0 (attribute nibble only).
void ov_attribute_head(AnimationMachineState& r) {
    am_swap(r.d[0]);am_word(r.d[0],r.d[1]);am_word(r.d[0],(r.d[0]<<4)&0xf000U);
}
// SWAP D0; ADDI.W #step,D0; BRA e88c0.
bool ov_finish(AnimationMachineState& r,std::uint32_t step) {am_swap(r.d[0]);ov_add_word(r.d[0],step);r.pc=0xe88c0;return true;}
// LSL.W #4,D1; ANDI.W #f000,D1; OR.W D1,D0.
void ov_attribute_or(AnimationMachineState& r) {
    am_word(r.d[1],(r.d[1]<<4)&0xf000U);am_word(r.d[0],(r.d[0]|r.d[1])&65535U);
}
// CMPI.B #k,D2; BEQ e885a with LEA table(PC),A1 first.
void ov_vowel(AnimationMachineState& r,std::uint32_t table,std::uint32_t key,std::uint32_t other_pc) {
    r.a[1]=table;r.pc=(r.d[2]&255U)==key?0xe885a:other_pc;
}
// MOVEM.L D1-D7/A1-A6,-(A7): A6 first at the highest address; memory from low to high is D1..D7, A1..A6.
bool ov_save(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    for(unsigned int i=6;i>=1;--i)if(!am_push(c,4,r.a[i]))return false;
    for(unsigned int i=7;i>=1;--i)if(!am_push(c,4,r.d[i]))return false;
    return true;
}
// MOVEM.L (A7)+,D1-D7/A1-A6 (ascending D1..D7, A1..A6).
bool ov_restore(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    for(unsigned int i=1;i<=7;++i)if(!am_pop(c,4,r.d[i]))return false;
    for(unsigned int i=1;i<=6;++i)if(!am_pop(c,4,r.a[i]))return false;
    return true;
}
}
// Objects F4 U03 (83 block starts): the VRAM glyph writer e84d6, entered only from the card menu open block e84c8 (D1.B >= 10).
// In: A0 = lookahead BYTE, D0.W = VRAM address, D1.B = mode, D1.W bits 8..11 = attribute, D2.B = glyph. The dakuten/handakuten
// marks de/df combine with the glyph (e84d6..e8548); mode 30 and every unknown mode call the existing 3650 writer with D1.B = 3;
// modes 61/41/31/48/4b/68/6b/58/32 write 1, 2, 3 or 4 LONGs to 3c0000 (one video event each) through the font tables e7cc8/e7ec8/
// e80c8/e82c8, the pair LONG table e7c44 or the vowel tables e88c6..e89d8 (fixed ROM, live bus). D1-D7/A1-A6 are saved and
// restored by MOVEM. No block consumes or produces a known C; the BRA/LEA blocks and e88c0 (MOVEM+RTS) keep the incoming C.
// The table searches e875c/e885a have no extra limit (block budget only). The only callee is 3650 (card menu open executor).
bool animation_objects_u03_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- e84d6: MOVEM.L D1-D7/A1-A6,-(A7); MOVE.B (A0),D7; CMPI.B #de,D7; BNE e8530.
    case 0xe84d6:
        if(!ov_save(c) || !ov_string_byte(c,r.d[7],false))return false;r.pc=(r.d[7]&255U)!=0xdeU?0xe8530:0xe84e4;return true;
    case 0xe84e4:r.pc=(r.d[2]&255U)!=0xb3U?0xe84f6:0xe84ec;return true;              // CMPI.B #b3,D2; BNE e84f6.
    case 0xe84ec:r.a[0]+=1U;am_byte(r.d[2],0xe0);r.pc=0xe8558;return true;            // ADDQ.W #1,A0; MOVE.B #e0,D2; BRA e8558.
    case 0xe84f6:r.pc=(r.d[2]&255U)<0xb6U?0xe8510:0xe84fe;return true;               // CMPI.B #b6,D2; BCS e8510.
    case 0xe84fe:r.pc=(r.d[2]&255U)>0xc4U?0xe8510:0xe8506;return true;               // CMPI.B #c4,D2; BHI e8510.
    case 0xe8506:r.a[0]+=1U;ov_add_byte(r.d[2],0x2b);r.pc=0xe8558;return true;       // ADDQ.W #1,A0; ADDI.B #2b,D2; BRA e8558.
    case 0xe8510:case 0xe8538:r.pc=(r.d[2]&255U)<0xcaU?(r.pc==0xe8510?0xe8530:0xe8558):r.pc+8U;return true; // CMPI.B #ca,D2; BCS.
    case 0xe8518:case 0xe8540:r.pc=(r.d[2]&255U)>0xceU?(r.pc==0xe8518?0xe8530:0xe8558):r.pc+8U;return true; // CMPI.B #ce,D2; BHI.
    // ADDQ.W #1,A0; SUBI.B #ca,D2; ADD.B D2,D2; ADDI.B #f0/#f1,D2; BRA e8558.
    case 0xe8520:case 0xe8548:
        r.a[0]+=1U;am_byte(r.d[2],(r.d[2]-0xcaU)&255U);ov_add_byte(r.d[2],r.d[2]);ov_add_byte(r.d[2],r.pc==0xe8520?0xf0U:0xf1U);
        r.pc=0xe8558;return true;
    case 0xe8530:r.pc=(r.d[7]&255U)!=0xdfU?0xe8558:0xe8538;return true;              // CMPI.B #df,D7; BNE e8558.

    // ---- mode dispatch on D1.B.
    case 0xe8558:r.pc=(r.d[1]&255U)!=0x30U?0xe856e:0xe8560;return true;
    case 0xe8560:case 0xe88b6:am_byte(r.d[1],3);return am_call(c,0x3650,r.pc==0xe8560?0xe856a:0xe88c0); // MOVE.B #3,D1; JSR 3650.
    case 0xe856a:r.pc=0xe88c0;return true;                                            // BRA e88c0.
    case 0xe856e:r.pc=(r.d[1]&255U)!=0x61U?0xe85aa:0xe8576;return true;
    // Mode 61: tile head a0; ANDI.B #f0,D0; ADD.B D0,D0; ANDI.B #f,D2; ADD.B D2,D0; two LONGs (+10010); SWAP; +1f.
    case 0xe8576:
        ov_tile_head(r,0xa0);am_byte(r.d[0],r.d[0]&0xf0U);ov_add_byte(r.d[0],r.d[0]);am_byte(r.d[2],r.d[2]&0xfU);ov_add_byte(r.d[0],r.d[2]);
        ov_port(c,r.d[0]);r.d[0]+=0x10010U;ov_port(c,r.d[0]);return ov_finish(r,0x1f);
    case 0xe85aa:r.pc=(r.d[1]&255U)!=0x48U?0xe85ba:0xe85b2;return true;
    case 0xe85b2:r.a[1]=OV_FONT_48;r.pc=0xe85c6;return true;                         // LEA e7cc8(PC),A1; BRA e85c6.
    case 0xe85ba:r.pc=(r.d[1]&255U)!=0x4bU?0xe85de:0xe85c2;return true;
    case 0xe85c2:r.a[1]=OV_FONT_4B;r.pc=0xe85c6;return true;                         // LEA e7ec8(PC),A1.
    // Attribute head; ANDI.W #ff,D2; ADD.W D2,D2; OR.W (A1,D2.W),D0; BRA e8610.
    case 0xe85c6:
        ov_attribute_head(r);am_word(r.d[2],(r.d[2]&255U)<<1);
        if(!am_read(c,am_index(r.a[1],r.d[2]),2,value))return false;am_word(r.d[0],(r.d[0]|value)&65535U);r.pc=0xe8610;return true;
    case 0xe85de:r.pc=(r.d[1]&255U)!=0x41U?0xe8644:0xe85e6;return true;
    // Mode 41: tile head 80; ANDI.B #f0,D0; ADD.B D0,D0; ANDI.B #f,D2; CMPI.B #8,D2; BCS e8608.
    case 0xe85e6:
        ov_tile_head(r,0x80);am_byte(r.d[0],r.d[0]&0xf0U);ov_add_byte(r.d[0],r.d[0]);am_byte(r.d[2],r.d[2]&0xfU);
        r.pc=(r.d[2]&255U)<8U?0xe8608:0xe8604;return true;
    case 0xe8604:ov_add_word(r.d[0],0x100);r.pc=0xe8608;return true;                 // ADDI.W #100,D0.
    // ANDI.B #7,D2; ADD.B D2,D2; OR.B D2,D0.
    case 0xe8608:am_byte(r.d[2],r.d[2]&7U);ov_add_byte(r.d[2],r.d[2]);am_byte(r.d[0],(r.d[0]|r.d[2])&255U);r.pc=0xe8610;return true;
    // Four LONGs: D0, +10010, +200001, -10010; SWAP; +20.
    case 0xe8610:
        ov_port(c,r.d[0]);r.d[0]+=0x10010U;ov_port(c,r.d[0]);r.d[0]+=0x200001U;ov_port(c,r.d[0]);r.d[0]-=0x10010U;ov_port(c,r.d[0]);
        return ov_finish(r,0x20);
    case 0xe8644:r.pc=(r.d[1]&255U)!=0x31U?0xe8684:0xe864c;return true;
    // Mode 31: tile head 40; ADDI.B #80,D0; three LONGs (+10010 each); SWAP; +1e.
    case 0xe864c:
        ov_tile_head(r,0x40);ov_add_byte(r.d[0],0x80);ov_port(c,r.d[0]);r.d[0]+=0x10010U;ov_port(c,r.d[0]);r.d[0]+=0x10010U;ov_port(c,r.d[0]);
        return ov_finish(r,0x1e);
    case 0xe8684:r.pc=(r.d[1]&255U)!=0x68U?0xe8694:0xe868c;return true;
    case 0xe868c:r.a[1]=OV_FONT_68;r.pc=0xe86a0;return true;                         // LEA e82c8(PC),A1; BRA e86a0.
    case 0xe8694:r.pc=(r.d[1]&255U)!=0x6bU?0xe8734:0xe869c;return true;
    case 0xe869c:r.a[1]=OV_FONT_6B;r.pc=0xe86a0;return true;                         // LEA e80c8(PC),A1.
    // '@' grammar of modes 68/6b.
    case 0xe86a0:r.pc=(r.d[2]&255U)!=0x40U?0xe8710:0xe86a8;return true;              // CMPI.B #40,D2; BNE e8710.
    // MOVE.B (A0)+,D2; MOVEQ #0,D7; CMPI.B #2e,D2; BEQ e86de.
    case 0xe86a8:if(!ov_string_byte(c,r.d[2],true))return false;r.d[7]=0;r.pc=(r.d[2]&255U)==0x2eU?0xe86de:0xe86b4;return true;
    case 0xe86b4:r.d[7]=1;r.pc=(r.d[2]&255U)==0x3aU?0xe86de:0xe86be;return true;    // MOVEQ #1,D7; CMPI.B #3a,D2; BEQ e86de.
    case 0xe86be:r.d[7]=2;r.pc=(r.d[2]&255U)==0x7eU?0xe86de:0xe86c8;return true;    // MOVEQ #2,D7; CMPI.B #7e,D2; BEQ e86de.
    case 0xe86c8:r.pc=(r.d[2]&255U)==0x2dU?0xe86de:0xe86d0;return true;              // CMPI.B #2d,D2; BEQ e86de.
    case 0xe86d0:r.pc=(r.d[2]&255U)!=0x60U?0xe86da:0xe86d8;return true;              // CMPI.B #60,D2; BNE e86da.
    case 0xe86d8:if(!ov_string_byte(c,r.d[2],true))return false;r.pc=0xe86da;return true; // MOVE.B (A0)+,D2.
    case 0xe86da:case 0xe8706:r.pc=0xe8710;return true;                               // BRA e8710.
    // MOVE.B (A0)+,D2; CMPI.B #61,D2; BEQ e870a.
    case 0xe86de:if(!ov_string_byte(c,r.d[2],true))return false;r.pc=(r.d[2]&255U)==0x61U?0xe870a:0xe86e8;return true;
    case 0xe86e8:ov_add_word(r.d[7],3);r.pc=(r.d[2]&255U)==0x75U?0xe870a:0xe86f2;return true; // ADDQ.W #3,D7; CMPI.B #75,D2.
    case 0xe86f2:ov_add_word(r.d[7],3);r.pc=(r.d[2]&255U)==0x65U?0xe870a:0xe86fc;return true; // ADDQ.W #3,D7; CMPI.B #65,D2.
    case 0xe86fc:ov_add_word(r.d[7],2);r.pc=(r.d[2]&255U)==0x6fU?0xe870a:0xe8706;return true; // ADDQ.W #2,D7; CMPI.B #6f,D2.
    case 0xe870a:am_word(r.d[2],r.d[7]);ov_add_word(r.d[2],0x80);r.pc=0xe8710;return true; // MOVE.W D7,D2; ADDI.W #80,D2.
    // ANDI.W #ff,D2; ADD.W D2,D2; SWAP D0; MOVE.W (A1,D2.W),D0.
    case 0xe8710:
        am_word(r.d[2],(r.d[2]&255U)<<1);am_swap(r.d[0]);
        if(!am_read(c,am_index(r.a[1],r.d[2]),2,value))return false;am_word(r.d[0],value);r.pc=0xe871c;return true;
    // LSL.W #4,D1; ANDI.W #f000,D1; OR.W D1,D0; one LONG; SWAP; +20.
    case 0xe871c:ov_attribute_or(r);ov_port(c,r.d[0]);return ov_finish(r,0x20);
    // Mode 58: pair glyphs 80..9f and e0..ff.
    case 0xe8734:r.pc=(r.d[1]&255U)!=0x58U?0xe877a:0xe873c;return true;
    case 0xe873c:r.pc=(r.d[2]&255U)<0x80U?0xe85e6:0xe8744;return true;               // CMPI.B #80,D2; BCS e85e6.
    case 0xe8744:r.pc=(r.d[2]&255U)<0xa0U?0xe8754:0xe874c;return true;               // CMPI.B #a0,D2; BCS e8754.
    case 0xe874c:r.pc=(r.d[2]&255U)<0xe0U?0xe85e6:0xe8754;return true;               // CMPI.B #e0,D2; BCS e85e6.
    // LSL.W #8,D2; MOVE.B (A0)+,D2; LEA e7c44(PC),A1.
    case 0xe8754:
        am_word(r.d[2],(r.d[2]<<8)&65535U);if(!ov_string_byte(c,r.d[2],true))return false;r.a[1]=OV_PAIR_TABLE;r.pc=0xe875c;return true;
    // MOVE.L (A1)+,D7; CMP.W D7,D2; BEQ e8768.
    case 0xe875c:
        if(!am_read(c,r.a[1],4,value))return false;r.a[1]+=4U;r.d[7]=value;
        r.pc=(r.d[2]&65535U)==(r.d[7]&65535U)?0xe8768:0xe8764;return true;
    case 0xe8764:r.pc=(r.d[7]&65535U)?0xe875c:0xe8768;return true;                   // TST.W D7; BNE e875c.
    // SWAP D7; SWAP D0; MOVE.W D7,D0; attribute OR; BRA e8610.
    case 0xe8768:am_swap(r.d[7]);am_swap(r.d[0]);am_word(r.d[0],r.d[7]);ov_attribute_or(r);r.pc=0xe8610;return true;
    // Mode 32: '@' then '!', 'c'/'C' or a vowel pair.
    case 0xe877a:r.pc=(r.d[1]&255U)!=0x32U?0xe88b6:0xe8782;return true;
    case 0xe8782:r.pc=(r.d[2]&255U)!=0x40U?0xe88b6:0xe878a;return true;
    // MOVE.B (A0)+,D2; CMPI.B #21,D2; BNE e879c.
    case 0xe878a:if(!ov_string_byte(c,r.d[2],true))return false;r.pc=(r.d[2]&255U)!=0x21U?0xe879c:0xe8794;return true;
    case 0xe8794:am_swap(r.d[0]);am_word(r.d[0],0xbea);r.pc=0xe871c;return true;     // SWAP D0; MOVE.W #bea,D0; BRA e871c.
    case 0xe879c:r.pc=(r.d[2]&255U)==0x63U?0xe87aa:0xe87a2;return true;              // CMPI.B #63,D2; BEQ e87aa.
    case 0xe87a2:r.pc=(r.d[2]&255U)!=0x43U?0xe87da:0xe87aa;return true;              // CMPI.B #43,D2; BNE e87da.
    // Tile head 30; LONG; ADDI.L #10000,D0; ANDI.W #f00,D0; ORI.W #beb,D0; LONG; SWAP; +1f.
    case 0xe87aa:
        ov_tile_head(r,0x30);ov_port(c,r.d[0]);r.d[0]+=0x10000U;am_word(r.d[0],r.d[0]&0xf00U);am_word(r.d[0],(r.d[0]|0xbebU)&65535U);
        ov_port(c,r.d[0]);return ov_finish(r,0x1f);
    // LSL.W #8,D2; MOVE.B (A0),D2; LEA e88c6(PC),A1; CMPI.B #61,D2; BEQ e885a.
    case 0xe87da:
        am_word(r.d[2],(r.d[2]<<8)&65535U);if(!ov_string_byte(c,r.d[2],false))return false;ov_vowel(r,0xe88c6,0x61,0xe87ea);return true;
    case 0xe87ea:ov_vowel(r,0xe8900,0x69,0xe87f6);return true;
    case 0xe87f6:ov_vowel(r,0xe890a,0x75,0xe8802);return true;
    case 0xe8802:ov_vowel(r,0xe8924,0x65,0xe880e);return true;
    case 0xe880e:ov_vowel(r,0xe8946,0x6f,0xe881a);return true;
    case 0xe881a:ov_vowel(r,0xe8970,0x41,0xe8826);return true;
    case 0xe8826:ov_vowel(r,0xe8992,0x49,0xe8832);return true;
    case 0xe8832:ov_vowel(r,0xe899c,0x55,0xe883e);return true;
    case 0xe883e:ov_vowel(r,0xe89a6,0x45,0xe884a);return true;
    case 0xe884a:ov_vowel(r,0xe89c0,0x4f,0xe8856);return true;
    case 0xe8856:r.pc=0xe886a;return true;                                            // BRA e886a.
    // MOVE.W (A1)+,D3; BEQ e886a.
    case 0xe885a:if(!am_read(c,r.a[1],2,value))return false;r.a[1]+=2U;am_word(r.d[3],value);r.pc=(value&65535U)?0xe8860:0xe886a;return true;
    case 0xe8860:r.pc=(r.d[3]&65535U)==(r.d[2]&65535U)?0xe8886:0xe8866;return true;  // CMP.W D2,D3; BEQ e8886.
    case 0xe8866:r.a[1]+=6U;r.pc=0xe885a;return true;                                // ADDQ.W #6,A1; BRA e885a.
    // Tile head 30; one LONG; SWAP; +20.
    case 0xe886a:ov_tile_head(r,0x30);ov_port(c,r.d[0]);return ov_finish(r,0x20);
    // ADDQ.W #1,A0; attribute head; OR.W (A1)+,D0; LONG; SUBI.L #10000,D0; ANDI.W #f000,D0; OR.W (A1),D0; LONG; SWAP; +21.
    case 0xe8886:
        r.a[0]+=1U;ov_attribute_head(r);
        if(!am_read(c,r.a[1],2,value))return false;r.a[1]+=2U;am_word(r.d[0],(r.d[0]|value)&65535U);ov_port(c,r.d[0]);
        r.d[0]-=0x10000U;am_word(r.d[0],r.d[0]&0xf000U);
        if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[0],(r.d[0]|value)&65535U);ov_port(c,r.d[0]);return ov_finish(r,0x21);
    // MOVEM.L (A7)+,D1-D7/A1-A6; RTS.
    case 0xe88c0:if(!ov_restore(c))return false;return am_return(c);
    default:return am_error(c,"unsupported animation objects u03 PC");
    }
}
}
