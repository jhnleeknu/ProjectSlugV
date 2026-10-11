#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// 45798 JMP 4579c(PC,D7.W): the 96 BRA.W entries 4579c+4k (k = 0..5f) transcribed from the original code (decision 4).
// The callers' D7.W is the 447be/4483a result 4k (k < 60) with 160 skipped; the jump itself moves to the computed PC (F1 decision 3).
const std::uint32_t OU15B_TABLE=0x4579c;
const unsigned int OU15B_TABLE_ENTRIES=96;
const std::uint32_t OU15B_TARGETS[OU15B_TABLE_ENTRIES]={
    0x45aac,0x45ad4,0x45ad4,0x45aac,0x45aac,0x45ad4,0x45ad4,0x45aac,0x45aac,0x45ad4,0x45ad4,0x45aac,0x45aac,0x45ad4,0x45ad4,0x45aac,
    0x45aac,0x45ad4,0x45ad4,0x45aac,0x45aac,0x45ad4,0x45ad4,0x45aac,0x45aac,0x45ad4,0x45ad4,0x45aac,0x45aac,0x45ad4,0x45ad4,0x45aac,
    0x45932,0x45936,0x45932,0x45936,0x4593a,0x45960,0x45960,0x4593a,0x4593a,0x45960,0x45960,0x4593a,0x4593a,0x45960,0x45960,0x4593a,
    0x4593a,0x45960,0x45960,0x4593a,0x45988,0x459ae,0x459ae,0x45988,0x45988,0x459ae,0x459ae,0x45988,0x459d6,0x459f2,0x459f2,0x459d6,
    0x45a10,0x45a36,0x45a36,0x45a10,0x45a10,0x45a36,0x45a36,0x45a10,0x45a5e,0x45a84,0x45a84,0x45a5e,0x45a5e,0x45a84,0x45a84,0x45a5e,
    0x45a5e,0x45a84,0x45a84,0x45a5e,0x45a5e,0x45a84,0x45a84,0x45a5e,0x4591c,0x4591e,0x45922,0x4591e,0x4591e,0x45926,0x4591c,0x4591c};
// ASR.L #shift (shift 1..31): sign fill written out (no signed shift of C++).
std::uint32_t ou15b_asr_long(std::uint32_t value,unsigned int shift) {
    const std::uint32_t fill=(value&0x80000000U)?~(0xffffffffU>>shift):0U;return (value>>shift)|fill;
}
// Signed LONG tests of TST.L (V = 0): BGT = positive non-zero, BLT = negative.
bool ou15b_positive(std::uint32_t value) {return value!=0U && (value&0x80000000U)==0U;}
bool ou15b_negative(std::uint32_t value) {return (value&0x80000000U)!=0U;}
// Slope head: LSL.L #s,Dq (or ADD.L Dq,Dq for s = 1; s = 0: Dq unchanged); ADD.L/SUB.L Dq,Dp; BPL.W tail_pc (else the NOT.L D4
// block not_pc).
void ou15b_head(AnimationMachineState& r,unsigned int p,unsigned int q,unsigned int s,bool subtract,std::uint32_t tail_pc,
    std::uint32_t not_pc) {
    r.d[q]<<=s;r.d[p]=subtract?r.d[p]-r.d[q]:r.d[p]+r.d[q];r.pc=(r.d[p]&0x80000000U)?not_pc:tail_pc;
}
// Slope tail: [m > 0: MOVE.L Dp,Dq; LSL.L #m,Dp; SUB.L Dq,Dp;] ANDI.L #mask,D4; ADD.L D4,Dp; ANDI.L #~mask,Dp; ASR.L #a,Dp (a = 12:
// two ASR.L #6); MOVE.L Dp,Dq; LSL.L #f,Dq (or ADD.L Dq,Dq); [NEG.L Dq;] RTS.
bool ou15b_tail(AnimationMachineContext& c,unsigned int p,unsigned int q,unsigned int m,std::uint32_t mask,unsigned int a,
    unsigned int f,bool negate) {
    AnimationMachineState& r=c.s;
    if(m){r.d[q]=r.d[p];r.d[p]=(r.d[p]<<m)-r.d[q];}
    r.d[4]&=mask;r.d[p]+=r.d[4];r.d[p]&=~mask;r.d[p]=ou15b_asr_long(r.d[p],a);
    r.d[q]=r.d[p]<<f;if(negate)r.d[q]=0U-r.d[q];return am_return(c);
}
}
// Objects F4 U15b (144 block starts): the terrain step table 4578a (MOVE.L D2,D5; OR.L D3,D5; BEQ 4591c), 45792 (MOVE.W 54de(A5),
// D4; EXT.L D4; JMP 4579c(PC,D7.W)) with all 96 BRA.W entries 4579c..45918, the target bodies 4591c..45afc and 45afe (CMPI.W #174,
// D7; BNE 4578a; TST.L D3; BGT 45922; BLT 4591e). 45792 moves to the computed PC 4579c+D7.W through the routing. U15b has no
// call, no carry consumer across blocks and no known-carry producer; it reads the work RAM WORD 54de(A5) and writes no RAM or port.
bool animation_objects_u15b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 4578a: MOVE.L D2,D5; OR.L D3,D5; BEQ.W 4591c.
    case 0x4578a:r.d[5]=r.d[2]|r.d[3];r.pc=r.d[5]?0x45792:0x4591c;return true;
    // MOVE.W 54de(A5),D4; EXT.L D4; JMP 4579c(PC,D7.W) (computed PC through the routing).
    case 0x45792:
        if(!am_read(c,am_index(r.a[5],0x54de),2,value))return false;r.d[4]=am_extend_word(value);
        r.pc=am_index(OU15B_TABLE,r.d[7]);return true;
    case 0x4591c:case 0x45930:case 0x45b10:return am_return(c);              // RTS.
    case 0x4591e:case 0x45922:r.d[3]=0;return am_return(c);                 // MOVEQ #0,D3; RTS.
    case 0x45932:case 0x45936:r.d[2]=0;return am_return(c);                 // MOVEQ #0,D2; RTS.
    // TST.L D2; BGT.W 45932; BLT.W 45936.
    case 0x45926:r.pc=ou15b_positive(r.d[2])?0x45932:(ou15b_negative(r.d[2])?0x45936:0x45930);return true;
    // ---- Slope bodies: head (BPL to the tail), NOT.L D4 (-> tail), tail.
    case 0x4593a:ou15b_head(r,2,3,2,false,0x45944,0x45942);return true;
    case 0x45960:ou15b_head(r,2,3,2,true,0x4596a,0x45968);return true;
    case 0x45988:ou15b_head(r,2,3,1,false,0x45992,0x45990);return true;
    case 0x459ae:ou15b_head(r,2,3,1,true,0x459b8,0x459b6);return true;
    case 0x459d6:ou15b_head(r,3,2,0,false,0x459de,0x459dc);return true;
    case 0x459f2:ou15b_head(r,3,2,0,true,0x459fa,0x459f8);return true;
    case 0x45a10:ou15b_head(r,3,2,1,false,0x45a1a,0x45a18);return true;
    case 0x45a36:ou15b_head(r,3,2,1,true,0x45a40,0x45a3e);return true;
    case 0x45a5e:ou15b_head(r,3,2,2,false,0x45a68,0x45a66);return true;
    case 0x45a84:ou15b_head(r,3,2,2,true,0x45a8e,0x45a8c);return true;
    case 0x45aac:ou15b_head(r,3,2,3,false,0x45ab6,0x45ab4);return true;
    case 0x45ad4:ou15b_head(r,3,2,3,true,0x45ade,0x45adc);return true;
    // NOT.L D4 (falls into the tail 2 bytes later).
    case 0x45942:case 0x45968:case 0x45990:case 0x459b6:case 0x459dc:case 0x459f8:case 0x45a18:case 0x45a3e:case 0x45a66:case 0x45a8c:
    case 0x45ab4:case 0x45adc:r.d[4]=~r.d[4];r.pc+=2U;return true;
    case 0x45944:return ou15b_tail(c,2,3,4,0x7ffffU,8,2,false);
    case 0x4596a:return ou15b_tail(c,2,3,4,0x7ffffU,8,2,true);
    case 0x45992:return ou15b_tail(c,2,3,2,0x7fffU,4,1,false);
    case 0x459b8:return ou15b_tail(c,2,3,2,0x7fffU,4,1,true);
    case 0x459de:return ou15b_tail(c,3,2,0,0x3ffU,1,0,false);
    case 0x459fa:return ou15b_tail(c,3,2,0,0x3ffU,1,0,true);
    case 0x45a1a:return ou15b_tail(c,3,2,2,0x7fffU,4,1,false);
    case 0x45a40:return ou15b_tail(c,3,2,2,0x7fffU,4,1,true);
    case 0x45a68:return ou15b_tail(c,3,2,4,0x7ffffU,8,2,false);
    case 0x45a8e:return ou15b_tail(c,3,2,4,0x7ffffU,8,2,true);
    case 0x45ab6:return ou15b_tail(c,3,2,6,0x3fffffU,12,3,false);
    case 0x45ade:return ou15b_tail(c,3,2,6,0x3fffffU,12,3,true);
    // ---- 45afe: CMPI.W #174,D7; BNE.W 4578a.
    case 0x45afe:r.pc=(r.d[7]&65535U)!=0x174U?0x4578a:0x45b06;return true;
    // TST.L D3; BGT.W 45922; BLT.W 4591e.
    case 0x45b06:r.pc=ou15b_positive(r.d[3])?0x45922:(ou15b_negative(r.d[3])?0x4591e:0x45b10);return true;
    default:
        // Table entries 4579c+4k: BRA.W to the transcribed target. The displacement WORDs are interior PCs.
        if(r.pc>=OU15B_TABLE && r.pc<OU15B_TABLE+4U*OU15B_TABLE_ENTRIES && ((r.pc-OU15B_TABLE)&3U)==0){
            r.pc=OU15B_TARGETS[(r.pc-OU15B_TABLE)>>2];return true;
        }
        return am_error(c,"unsupported animation objects u15b PC");
    }
}
}
