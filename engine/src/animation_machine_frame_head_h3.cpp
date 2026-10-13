#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Dirty-mark cell family: cell k (k = 0..255) is the 26 identical bytes at 578c + 26k (MOVE.B D0,300001.l; BTST.B #1,f(A2);
// BNE.W +8; BSET.B #7,f(A2); LEA 10(A2),A2). Block starts: B_k = 579c + 26k (BSET) and L_k = 57a2 + 26k (LEA + next cell head).
const std::uint32_t FH3_CELL_FIRST=0x578c;
const std::uint32_t FH3_CELL_SIZE=26;
const std::uint32_t FH3_CELL_COUNT=256;
const std::uint32_t FH3_CELL_BSET=16;
const std::uint32_t FH3_CELL_LEA=22;
// Fixed constants: palette buffer end (CMPA.L #107da2,A4) and the blend table base (LEA 3f78(PC),A2 at 4c54 / 5060).
const std::uint32_t FH3_BUFFER_END=0x107da2;
const std::uint32_t FH3_BLEND=0x3f78;
// Bank window LONGs read after the bank switch to 200000: palette source base (A6) and colour translation table (A3).
const std::uint32_t FH3_SOURCE_LONG=0x200004;
const std::uint32_t FH3_TABLE_LONG=0x200008;
// A5-relative displacement WORDs (A5 = 108000 in the natural head: 107dc2.., 104d92, 105da2).
const std::uint32_t FH3_FADE_R=0xfdc2,FH3_FADE_G=0xfdc4,FH3_FADE_B=0xfdc6;
const std::uint32_t FH3_TARGET_R=0xfdc8,FH3_TARGET_G=0xfdca,FH3_TARGET_B=0xfdcc;
const std::uint32_t FH3_STEP_R=0xfdce,FH3_STEP_G=0xfdd0,FH3_STEP_B=0xfdd2;
const std::uint32_t FH3_TIMER=0xfdd4,FH3_DIRTY=0xfdd5,FH3_BUILT=0xfded;
const std::uint32_t FH3_SLOTS=0xcd92,FH3_BUFFER=0xdda2;
// Every helper converts colours 1..15 of one 16-colour palette (15 identical unrolled bodies).
const unsigned int FH3_COLOURS=15;
std::uint32_t fh3_b(std::uint32_t value) {return value&255U;}
std::uint32_t fh3_w(std::uint32_t value) {return value&65535U;}
std::uint32_t fh3_at(std::uint32_t base,std::uint32_t displacement) {return am_index(base,displacement);}
std::uint32_t fh3_bset_pc(std::uint32_t k) {return FH3_CELL_FIRST+FH3_CELL_SIZE*k+FH3_CELL_BSET;}
std::uint32_t fh3_lea_pc(std::uint32_t k) {return FH3_CELL_FIRST+FH3_CELL_SIZE*k+FH3_CELL_LEA;}
// MOVE.B D0,300001.l (watchdog): one original write is one observed port event.
void fh3_watchdog(AnimationMachineContext& c) {
    VideoPortWrite port;port.address=0x300001;port.size=1;port.value=fh3_b(c.s.d[0]);c.ports.push_back(port);
}
// Cell k head: MOVE.B D0,300001.l; BTST.B #1,f(A2); BNE.W L_k (bit set) else B_k.
bool fh3_cell_head(AnimationMachineContext& c,std::uint32_t k) {
    std::uint32_t value=0;fh3_watchdog(c);if(!am_read(c,fh3_at(c.s.a[2],0xf),1,value))return false;
    c.s.pc=(value&2U)!=0U?fh3_lea_pc(k):fh3_bset_pc(k);return true;
}
// BSET.B / BCLR.B #bit,f(A2) (read, then write); returns the old bit.
bool fh3_bit(AnimationMachineContext& c,unsigned int bit,bool set,bool& was_set) {
    const std::uint32_t address=fh3_at(c.s.a[2],0xf);std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    const std::uint32_t mask=1U<<bit;was_set=(value&mask)!=0U;return am_write(c,address,1,set?fh3_b(value|mask):fh3_b(value&~mask));
}
// MOVE.W (A3,Dn.W),(A4)+: read the translated colour, then write it.
bool fh3_translate(AnimationMachineContext& c,std::uint32_t index) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!am_read(c,r.a[3]+am_extend_word(fh3_w(index)),2,value))return false;
    if(!am_write(c,r.a[4],2,value))return false;r.a[4]+=2U;return true;
}
// MOVE.W (An)+,Dn.
bool fh3_next(AnimationMachineContext& c,std::uint32_t& address,std::uint32_t& target) {
    std::uint32_t value=0;if(!am_read(c,address,2,value))return false;address+=2U;am_word(target,value);return true;
}
// ADD.B fade(A5),X; SPL D4; AND.B D4,X; CMP.B D7,X; SCC D4; OR.B D4,X; AND.B D7,X (channel + fade clamped to 0..D7.B).
bool fh3_clamp(AnimationMachineContext& c,std::uint32_t& x,std::uint32_t displacement) {
    AnimationMachineState& r=c.s;std::uint32_t fade=0;if(!am_read(c,fh3_at(r.a[5],displacement),1,fade))return false;
    am_byte(x,x+fade);am_byte(r.d[4],(x&0x80U)==0U?0xffU:0U);am_byte(x,x&r.d[4]);
    am_byte(r.d[4],fh3_b(x)>=fh3_b(r.d[7])?0xffU:0U);am_byte(x,x|r.d[4]);am_byte(x,x&r.d[7]);return true;
}
// MOVE.W Dn,Dk; MOVE.W Dm,Dj; AND.W D7,Dk; AND.W D7,Dj; SUB.W Dk,Dj; MOVE.B (A2,Dj.W),Dj; ADD.W Dk,Dj (one blended 5-bit channel).
bool fh3_blend_channel(AnimationMachineContext& c,std::uint32_t source,std::uint32_t target,std::uint32_t& base,std::uint32_t& out) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    am_word(base,source);am_word(out,target);am_word(base,base&r.d[7]);am_word(out,out&r.d[7]);am_word(out,out-base);
    if(!am_read(c,r.a[2]+am_extend_word(fh3_w(out)),1,value))return false;am_byte(out,value);am_word(out,out+base);return true;
}
// 4718: copy colours 1..15 through the translation table.
bool fh3_copy(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;r.d[7]=r.a[4];r.a[4]+=2U;r.a[0]+=2U;
    for(unsigned int i=0;i<FH3_COLOURS;++i) {
        if(!fh3_next(c,r.a[0],r.d[0]))return false;am_word(r.d[0],r.d[0]*2U);if(!fh3_translate(c,r.d[0]))return false;
    }
    r.a[4]=r.d[7];return am_return(c);
}
// 479e: copy colours 1..15 with the fade offsets -23e / -23c / -23a(A5) clamped per channel.
bool fh3_copy_fade(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;r.d[7]=0x1f;r.d[6]=r.a[4];r.a[4]+=2U;r.a[0]+=2U;
    for(unsigned int i=0;i<FH3_COLOURS;++i) {
        if(!fh3_next(c,r.a[0],r.d[0]))return false;
        am_byte(r.d[2],r.d[0]);am_word(r.d[2],r.d[2]&r.d[7]);am_word(r.d[0],fh3_w(r.d[0])>>5);
        am_word(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]&r.d[7]);am_word(r.d[0],fh3_w(r.d[0])>>5);am_word(r.d[0],r.d[0]&r.d[7]);
        if(!fh3_clamp(c,r.d[0],FH3_FADE_R) || !fh3_clamp(c,r.d[1],FH3_FADE_G) || !fh3_clamp(c,r.d[2],FH3_FADE_B))return false;
        am_word(r.d[0],fh3_w(r.d[0])<<5);am_byte(r.d[0],r.d[0]|r.d[1]);am_word(r.d[0],fh3_w(r.d[0])<<5);am_byte(r.d[0],r.d[0]|r.d[2]);
        am_word(r.d[0],r.d[0]*2U);if(!fh3_translate(c,r.d[0]))return false;
    }
    r.a[4]=r.d[6];return am_return(c);
}
// 4c50 / 505c: blend source (A1) toward target (A0) through the table row A2 = 3f78 + 64 * level (505c also clamps the fade).
bool fh3_blend(AnimationMachineContext& c,bool fade) {
    AnimationMachineState& r=c.s;r.d[6]=r.a[4];r.d[5]=r.a[2];r.a[2]=FH3_BLEND;am_word(r.d[0],fh3_w(r.d[0])<<6);
    r.a[2]+=am_extend_word(fh3_w(r.d[0]));r.a[4]+=2U;r.a[0]+=2U;r.a[1]+=2U;
    for(unsigned int i=0;i<FH3_COLOURS;++i) {
        if(!fh3_next(c,r.a[1],r.d[0]) || !fh3_next(c,r.a[0],r.d[1]))return false;
        if(!fh3_blend_channel(c,r.d[0],r.d[1],r.d[4],r.d[3]))return false;
        am_word(r.d[0],fh3_w(r.d[0])>>5);am_word(r.d[1],fh3_w(r.d[1])>>5);
        if(!fh3_blend_channel(c,r.d[0],r.d[1],r.d[4],r.d[2]))return false;
        am_word(r.d[0],fh3_w(r.d[0])>>5);am_word(r.d[1],fh3_w(r.d[1])>>5);
        // SUB.W D0,D1; MOVE.B (A2,D1.W),D1; ADD.W D0,D1 (red: no mask, bit 15 of the colour WORD is included).
        std::uint32_t value=0;am_word(r.d[1],r.d[1]-r.d[0]);
        if(!am_read(c,r.a[2]+am_extend_word(fh3_w(r.d[1])),1,value))return false;am_byte(r.d[1],value);am_word(r.d[1],r.d[1]+r.d[0]);
        if(fade && (!fh3_clamp(c,r.d[1],FH3_FADE_R) || !fh3_clamp(c,r.d[2],FH3_FADE_G) || !fh3_clamp(c,r.d[3],FH3_FADE_B)))return false;
        am_word(r.d[1],fh3_w(r.d[1])<<5);am_byte(r.d[1],r.d[1]|r.d[2]);am_word(r.d[1],fh3_w(r.d[1])<<5);am_byte(r.d[1],r.d[1]|r.d[3]);
        am_word(r.d[1],r.d[1]*2U);if(!fh3_translate(c,r.d[1]))return false;
    }
    r.a[2]=r.d[5];r.a[4]=r.d[6];return am_return(c);
}
// MOVEQ #0,D7; MOVEQ #0,D6; MOVE.W a(A2),D7; MOVE.W c(A2),D6 (source / target palette numbers).
bool fh3_numbers(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[7]=0;r.d[6]=0;
    if(!am_read(c,fh3_at(r.a[2],0xa),2,value))return false;am_word(r.d[7],value);
    if(!am_read(c,fh3_at(r.a[2],0xc),2,value))return false;am_word(r.d[6],value);return true;
}
// LSL.L #5,D6; LSL.L #5,D7; LEA (A6,D7.L),A0; LEA (A6,D6.L),A1; MOVEQ #0,D0; MOVE.B e(A2),D0.
bool fh3_blend_args(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[6]<<=5;r.d[7]<<=5;r.a[0]=r.a[6]+r.d[7];r.a[1]=r.a[6]+r.d[6];r.d[0]=0;
    if(!am_read(c,fh3_at(r.a[2],0xe),1,value))return false;am_byte(r.d[0],value);return true;
}
// MOVE.W #8000,(A4); MOVE.B #ff,-22b(A5).
bool fh3_built(AnimationMachineContext& c) {
    return am_write(c,c.s.a[4],2,0x8000) && am_write(c,fh3_at(c.s.a[5],FH3_DIRTY),1,0xff);
}
// MOVE.B -22b(A5),-213(A5); MOVEA.L (A7)+,A6; bank 200000 (WORD -7ff0(A5) = 0, 2ffff2 = 1000, 2ffff0 = 0); RTS.
bool fh3_finish(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,fh3_at(r.a[5],FH3_DIRTY),1,value) || !am_write(c,fh3_at(r.a[5],FH3_BUILT),1,value))return false;
    if(!am_pop(c,4,value))return false;r.a[6]=value;if(!am_zero_bank(c))return false;return am_return(c);
}
// Dirty-mark cell family blocks (main decision 2): only B_k / L_k are starts; every other PC is interior.
bool fh3_cell(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;const std::uint32_t offset=r.pc-FH3_CELL_FIRST;
    const std::uint32_t k=offset/FH3_CELL_SIZE;const std::uint32_t at=offset%FH3_CELL_SIZE;
    if(at==FH3_CELL_BSET) {bool was_set=false;if(!fh3_bit(c,7,true,was_set))return false;r.pc=fh3_lea_pc(k);return true;}
    if(at!=FH3_CELL_LEA)return am_error(c,"unsupported animation frame head h3 PC");
    r.a[2]+=0x10U;                                                          // LEA 10(A2),A2.
    if(k+1U==FH3_CELL_COUNT) {r.pc=FH3_CELL_FIRST+FH3_CELL_SIZE*FH3_CELL_COUNT;return true;} // L_255 = 7188 falls to 718c.
    return fh3_cell_head(c,k+1U);
}
}
// F5 frame head H3 (551 block starts = 39 unique + the 256-cell dirty-mark family x 2): the palette frame 5728 (fade timer step
// 5728..5788, dirty-mark cells 578c..718c with one watchdog write each, palette rebuild 718c..72ee with bank 200000) and the colour
// helpers 4718 (copy), 479e (copy + fade clamp), 4c40 / 4c50 (blend) and 504c / 505c (blend + fade clamp). The unrolled helper
// bodies are 15 byte-identical repetitions executed as loops. No call leaves H3 (the only exits are the RTS to the caller), no
// device read, no wait, no carry consumer and no known-carry producer.
bool animation_frame_head_h3_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool was_set=false;
    switch(r.pc) {
    // ---- fade timer step.
    case 0x5728:
        // MOVE.B -22c(A5),D7; BEQ.W 718c.
        if(!am_read(c,fh3_at(r.a[5],FH3_TIMER),1,value))return false;am_byte(r.d[7],value);r.pc=fh3_b(r.d[7])==0U?0x718c:0x5730;return true;
    case 0x5730:
        // MOVE.B -23e/-23c/-23a(A5),D0/D1/D2; SUBQ.B #1,D7; MOVE.B D7,-22c(A5); BNE.W 575c.
        if(!am_read(c,fh3_at(r.a[5],FH3_FADE_R),1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,fh3_at(r.a[5],FH3_FADE_G),1,value))return false;am_byte(r.d[1],value);
        if(!am_read(c,fh3_at(r.a[5],FH3_FADE_B),1,value))return false;am_byte(r.d[2],value);
        am_byte(r.d[7],r.d[7]-1U);if(!am_write(c,fh3_at(r.a[5],FH3_TIMER),1,fh3_b(r.d[7])))return false;
        r.pc=fh3_b(r.d[7])!=0U?0x575c:0x5746;return true;
    case 0x5746: {
        // MOVE.W -238/-236/-234(A5),-23e/-23c/-23a(A5); BRA.W 5774 (last step: the targets).
        const std::uint32_t from[3]={FH3_TARGET_R,FH3_TARGET_G,FH3_TARGET_B};const std::uint32_t to[3]={FH3_FADE_R,FH3_FADE_G,FH3_FADE_B};
        for(unsigned int i=0;i<3;++i)if(!am_read(c,fh3_at(r.a[5],from[i]),2,value) || !am_write(c,fh3_at(r.a[5],to[i]),2,value))return false;
        r.pc=0x5774;return true;
    }
    case 0x575c: {
        // MOVE.W step(A5),D7; ADD.W D7,fade(A5) for the three channels.
        const std::uint32_t step[3]={FH3_STEP_R,FH3_STEP_G,FH3_STEP_B};const std::uint32_t to[3]={FH3_FADE_R,FH3_FADE_G,FH3_FADE_B};
        for(unsigned int i=0;i<3;++i) {
            if(!am_read(c,fh3_at(r.a[5],step[i]),2,value))return false;am_word(r.d[7],value);
            if(!am_read(c,fh3_at(r.a[5],to[i]),2,value) || !am_write(c,fh3_at(r.a[5],to[i]),2,fh3_w(value+r.d[7])))return false;
        }
        r.pc=0x5774;return true;
    }
    case 0x5774:
        // SUB.B -23e/-23c/-23a(A5),D0/D1/D2; OR.B D1,D0; OR.B D2,D0; BEQ.W 718c (no integer fade change).
        if(!am_read(c,fh3_at(r.a[5],FH3_FADE_R),1,value))return false;am_byte(r.d[0],r.d[0]-value);
        if(!am_read(c,fh3_at(r.a[5],FH3_FADE_G),1,value))return false;am_byte(r.d[1],r.d[1]-value);
        if(!am_read(c,fh3_at(r.a[5],FH3_FADE_B),1,value))return false;am_byte(r.d[2],r.d[2]-value);
        am_byte(r.d[0],r.d[0]|r.d[1]);am_byte(r.d[0],r.d[0]|r.d[2]);r.pc=fh3_b(r.d[0])==0U?0x718c:0x5788;return true;
    case 0x5788:r.a[2]=fh3_at(r.a[5],FH3_SLOTS);return fh3_cell_head(c,0);     // LEA -326e(A5),A2; cell 0 head.
    // ---- palette rebuild.
    case 0x718c:
        // TST.B -213(A5); BPL.W 7196.
        if(!am_read(c,fh3_at(r.a[5],FH3_BUILT),1,value))return false;r.pc=(value&0x80U)==0U?0x7196:0x7194;return true;
    case 0x7194:return am_return(c);
    case 0x7196:
        // MOVE.B #0,-22b(A5); MOVE.L A6,-(A7); LEA -326e(A5),A2; LEA -225e(A5),A4; bank 200000; MOVEA.L 200004.l,A6;
        // MOVEA.L 200008.l,A3; MOVE.B -23e(A5),D0; OR.B -23c(A5),D0; OR.B -23a(A5),D0; BNE.W 7252.
        if(!am_write(c,fh3_at(r.a[5],FH3_DIRTY),1,0) || !am_push(c,4,r.a[6]))return false;
        r.a[2]=fh3_at(r.a[5],FH3_SLOTS);r.a[4]=fh3_at(r.a[5],FH3_BUFFER);if(!am_zero_bank(c))return false;
        if(!am_read(c,FH3_SOURCE_LONG,4,value))return false;r.a[6]=value;
        if(!am_read(c,FH3_TABLE_LONG,4,value))return false;r.a[3]=value;
        if(!am_read(c,fh3_at(r.a[5],FH3_FADE_R),1,value))return false;am_byte(r.d[0],value);
        if(!am_read(c,fh3_at(r.a[5],FH3_FADE_G),1,value))return false;am_byte(r.d[0],r.d[0]|value);
        if(!am_read(c,fh3_at(r.a[5],FH3_FADE_B),1,value))return false;am_byte(r.d[0],r.d[0]|value);
        r.pc=fh3_b(r.d[0])!=0U?0x7252:0x71d8;return true;
    case 0x71d8:if(!fh3_bit(c,7,false,was_set))return false;r.pc=was_set?0x71e2:0x7222;return true; // BCLR.B #7,f(A2); BEQ.W 7222.
    case 0x71e2:if(!fh3_numbers(c))return false;r.pc=fh3_w(r.d[7])==fh3_w(r.d[6])?0x71f4:0x7202;return true;
    case 0x71f4:r.d[7]<<=5;r.a[0]=r.a[6]+r.d[7];return am_call(c,0x4718,0x71fe);   // LSL.L #5,D7; LEA (A6,D7.L),A0; BSR.W 4718.
    case 0x71fe:r.pc=0x7218;return true;                                           // BRA.W 7218.
    case 0x7202:if(!fh3_blend_args(c))return false;return am_call(c,0x4c40,0x7218);
    case 0x7218:if(!fh3_built(c))return false;r.pc=0x7222;return true;
    case 0x7222:
        // LEA 20(A4),A4; LEA 10(A2),A2; CMPA.L #107da2,A4; BNE.B 71d8.
        r.a[4]+=0x20U;r.a[2]+=0x10U;r.pc=r.a[4]!=FH3_BUFFER_END?0x71d8:0x7232;return true;
    case 0x7232:return fh3_finish(c);
    case 0x7252:if(!fh3_bit(c,7,false,was_set))return false;r.pc=was_set?0x725c:0x72c0;return true; // BCLR.B #7,f(A2); BEQ.W 72c0.
    case 0x725c:if(!fh3_numbers(c))return false;r.pc=fh3_w(r.d[7])==fh3_w(r.d[6])?0x726e:0x728e;return true;
    case 0x726e:
        // LSL.L #5,D7; LEA (A6,D7.L),A0; BTST.B #1,f(A2); BEQ.W 7286.
        r.d[7]<<=5;r.a[0]=r.a[6]+r.d[7];if(!am_read(c,fh3_at(r.a[2],0xf),1,value))return false;
        r.pc=(value&2U)==0U?0x7286:0x727e;return true;
    case 0x727e:return am_call(c,0x4718,0x7282);
    case 0x7282:r.pc=0x728a;return true;                                           // BRA.W 728a.
    case 0x7286:return am_call(c,0x479e,0x728a);
    case 0x728a:r.pc=0x72b6;return true;                                           // BRA.W 72b6.
    case 0x728e:
        // blend arguments; BTST.B #1,f(A2); BEQ.W 72b2.
        if(!fh3_blend_args(c) || !am_read(c,fh3_at(r.a[2],0xf),1,value))return false;r.pc=(value&2U)==0U?0x72b2:0x72aa;return true;
    case 0x72aa:return am_call(c,0x4c40,0x72ae);
    case 0x72ae:r.pc=0x72b6;return true;                                           // BRA.W 72b6.
    case 0x72b2:return am_call(c,0x504c,0x72b6);
    case 0x72b6:if(!fh3_built(c))return false;r.pc=0x72c0;return true;
    case 0x72c0:
        // LEA 10(A2),A2; LEA 20(A4),A4; CMPA.L #107da2,A4; BNE.B 7252.
        r.a[2]+=0x10U;r.a[4]+=0x20U;r.pc=r.a[4]!=FH3_BUFFER_END?0x7252:0x72d0;return true;
    case 0x72d0:return fh3_finish(c);
    // ---- colour helpers.
    case 0x4718:return fh3_copy(c);
    case 0x479e:return fh3_copy_fade(c);
    case 0x4c40:r.pc=fh3_w(r.d[0])==0U?0x4718:0x4c46;return true;                  // TST.W D0; BEQ.W 4718.
    case 0x4c46:
        // EXG.L A1,A0; MOVEQ #1f,D7; CMP.W D7,D0; BCC.W 4718 (level >= 1f: the target palette).
        value=r.a[0];r.a[0]=r.a[1];r.a[1]=value;r.d[7]=0x1f;r.pc=fh3_w(r.d[0])>=fh3_w(r.d[7])?0x4718:0x4c50;return true;
    case 0x4c50:return fh3_blend(c,false);
    case 0x504c:r.pc=fh3_w(r.d[0])==0U?0x479e:0x5052;return true;                  // TST.W D0; BEQ.W 479e.
    case 0x5052:
        value=r.a[0];r.a[0]=r.a[1];r.a[1]=value;r.d[7]=0x1f;r.pc=fh3_w(r.d[0])>=fh3_w(r.d[7])?0x479e:0x505c;return true;
    case 0x505c:return fh3_blend(c,true);
    default:
        if(r.pc>FH3_CELL_FIRST && r.pc<FH3_CELL_FIRST+FH3_CELL_SIZE*FH3_CELL_COUNT)return fh3_cell(c);
        return am_error(c,"unsupported animation frame head h3 PC");
    }
}
}
