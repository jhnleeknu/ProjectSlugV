#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Reverse sprite writer family (contract animation-machine-frame-head-h4-contract.md): the BRA.W table 11792 + 4k (k = 0..7) and eight
// routines that are one template with three flags taken from k: H (bit 0), V (bit 1), S (bit 2). Every routine has the same role
// blocks (start PCs below, transcribed from the ROM), a 32-entry BRA.W table into 32 unrolled 18-byte cells and, for S, 32 Duff entries
// (8 bytes apart; entry 31 is the tail block). advance exists only without H, scale and duff only with S (0 = absent).
struct Fh4Routine {
    std::uint32_t head,swap7,outer,height,step,advance,test,scale,clip,column,table,cells,duff,next,finish,end;
    bool h,v,s;
};
const Fh4Routine FH4_ROUTINES[8]={
    {0x117b2,0x1180a,0x1180c,0x1182a,0x11836,0x11846,0x11848,0,0x11850,0x1185c,0x118a2,0x11922,0,0x11b6e,0x11b78,0x11b7e,false,false,false},
    {0x11b7e,0x11bd6,0x11bd8,0x11bf8,0x11c04,0,0x11c14,0,0x11c1c,0x11c2a,0x11c70,0x11cf0,0,0x11f3c,0x11f46,0x11f4c,true,false,false},
    {0x11f4c,0x11fa4,0x11fa6,0x11fc4,0x11fd0,0x11fe0,0x11fe2,0,0x11fea,0x11ff6,0x12040,0x120c0,0,0x1230c,0x12316,0x1231c,false,true,false},
    {0x1231c,0x12374,0x12376,0x12396,0x123a2,0,0x123b2,0,0x123ba,0x123c8,0x12412,0x12492,0,0x126de,0x126e8,0x126ee,true,true,false},
    {0x126ee,0x12746,0x12748,0x12776,0x12782,0x12792,0x1279e,0x127a6,0x127ae,0x127ba,0x12804,0x12884,0x12ae6,0x12bec,0x12bf6,0x12bfc,false,false,true},
    {0x12bfc,0x12c54,0x12c56,0x12c88,0x12c94,0,0x12ca4,0x12cac,0x12cb4,0x12ccc,0x12d16,0x12d96,0x12ff8,0x130fe,0x13108,0x1310e,true,false,true},
    {0x1310e,0x13166,0x13168,0x13196,0x131a2,0x131b2,0x131be,0x131c6,0x131ce,0x131da,0x13228,0x132a8,0x13512,0x13618,0x13622,0x13628,false,true,true},
    {0x13628,0x13680,0x13682,0x136b4,0x136c0,0,0x136d0,0x136d8,0x136e0,0x136f8,0x13746,0x137c6,0x13a30,0x13b36,0x13b40,0x13b46,true,true,true}};
const std::uint32_t FH4_TABLE=0x11792;         // BRA.W routine k at 11792 + 4k
const std::uint32_t FH4_BANK_TABLE=0x200004;   // LEA 200004.l,A3 (bank window, live PVC bank)
const std::uint32_t FH4_VIDEO=0x3c0000;
const std::uint32_t FH4_CELL_BYTES=18;         // MOVE.W (A3)+,D5 .. ADD.L D2,D0 (9 instructions)
const std::uint32_t FH4_DUFF_BYTES=8;          // MOVE.L D4,(A6); ADD.L D2,D4; MOVE.L D0,(A6); ADD.L D2,D0
const std::uint32_t FH4_ENTRIES=32;
std::uint32_t fh4_w(std::uint32_t value) {return value&65535U;}
// d16(An): base + sign-extended displacement (mod 2^32).
std::uint32_t fh4_at(std::uint32_t base,std::uint32_t displacement) {return am_index(base,displacement);}
// Signed WORD value without implementation-defined conversions.
std::int32_t fh4_signed_word(std::uint32_t value) {return static_cast<std::int32_t>(fh4_w(value)^0x8000U)-0x8000;}
// MOVE.L Dn,(A6) (main decision 4): A6 = 3c0000 is one size 4 video port event, any other A6 is an ordinary bus write.
bool fh4_video(AnimationMachineContext& c,std::uint32_t value) {
    if((c.s.a[6]&0xffffffU)!=FH4_VIDEO)return am_write(c,c.s.a[6],4,value);
    VideoPortWrite port;port.address=FH4_VIDEO;port.size=4;port.value=value;c.ports.push_back(port);return true;
}
// MOVE.W (A3)+,Dn.
bool fh4_next_word(AnimationMachineContext& c,std::uint32_t& target) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[3],2,value))return false;c.s.a[3]+=2U;am_word(target,value);return true;
}
// SUBI.W #$100,D7: C (borrow) = D7.W < $100; the low BYTE does not change.
bool fh4_count_column(AnimationMachineState& r) {
    const bool borrow=fh4_w(r.d[7])<0x100U;am_word(r.d[7],r.d[7]-0x100U);return borrow;
}
// The column re-entry: advance without H, test with H (the H routines apply the column step in clip).
std::uint32_t fh4_reentry(const Fh4Routine& f) {return f.h?f.test:f.advance;}
// S column step: MOVE.W D4,D2; ADDI.W #$100,D2; CLR.B D2; LSR.W #2,D2 (the value added to / subtracted from D5.W).
void fh4_scaled_step(AnimationMachineState& r) {
    am_word(r.d[2],r.d[4]);am_word(r.d[2],r.d[2]+0x100U);am_byte(r.d[2],0);am_word(r.d[2],fh4_w(r.d[2])>>2);
}
// MOVEM.L (A7)+,D3-D5 (LONG pops in register order).
bool fh4_pop_d3_d5(AnimationMachineContext& c) {
    for(unsigned int i=3;i<=5;++i) {std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.d[i]=value;}
    return true;
}
// One 18-byte cell: MOVE.W (A3)+,D5; ADD.W D3,D5; EOR.B D1,D5; MOVE.W D5,D4; MOVE.L D4,(A6); ADD.L D2,D4; MOVE.W (A3)+,D0;
// MOVE.L D0,(A6); ADD.L D2,D0.
bool fh4_cell(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    if(!fh4_next_word(c,r.d[5]))return false;am_word(r.d[5],r.d[5]+r.d[3]);am_byte(r.d[5],r.d[5]^r.d[1]);am_word(r.d[4],r.d[5]);
    if(!fh4_video(c,r.d[4]))return false;r.d[4]+=r.d[2];
    if(!fh4_next_word(c,r.d[0]) || !fh4_video(c,r.d[0]))return false;r.d[0]+=r.d[2];return true;
}
bool fh4_head(AnimationMachineContext& c,const Fh4Routine& f) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    // MOVEQ #0,D2; MOVE.L 8(A2),D2; MOVE.W D2,D7; ANDI.W #7,D7; MOVE.W D0,-(A7); MOVE.W D7,D0; MOVE.W D7,-7ff0(A5).
    r.d[2]=0;if(!am_read(c,fh4_at(r.a[2],8),4,value))return false;r.d[2]=value;am_word(r.d[7],r.d[2]);am_word(r.d[7],r.d[7]&7U);
    if(!am_push(c,2,fh4_w(r.d[0])))return false;am_word(r.d[0],r.d[7]);
    if(!am_write(c,fh4_at(r.a[5],0x8010),2,fh4_w(r.d[7])))return false;
    // ADDQ.W #1,D7; LSL.W #8,D7; LSL.W #4,D7; MOVE.W D7,2ffff2.l; MOVE.W #0,2ffff0.l (PVC bank select); MOVE.W D0,D7; MOVE.W (A7)+,D0.
    am_word(r.d[7],r.d[7]+1U);am_word(r.d[7],fh4_w(r.d[7])<<8);am_word(r.d[7],fh4_w(r.d[7])<<4);
    if(!am_write(c,0x2ffff2,2,fh4_w(r.d[7])) || !am_write(c,0x2ffff0,2,0))return false;
    am_word(r.d[7],r.d[0]);if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
    // LSR.L #1,D2; MOVE.W D2,D7; ANDI.W #3fc,D7; LEA 200004.l,A3; MOVEA.L (A3,D7.W),A3; LSR.L #8,D2; MOVE.W D2,D7; ANDI.W #3ffc,D7;
    // MOVEA.L (A3,D7.W),A3; MOVE.W 6(A4),D6; MOVE.W (A3)+,D7; SUBI.W #$100,D7; BCS.W finish.
    r.d[2]>>=1;am_word(r.d[7],r.d[2]);am_word(r.d[7],r.d[7]&0x3fcU);r.a[3]=FH4_BANK_TABLE;
    if(!am_read(c,fh4_at(r.a[3],r.d[7]),4,value))return false;r.a[3]=value;
    r.d[2]>>=8;am_word(r.d[7],r.d[2]);am_word(r.d[7],r.d[7]&0x3ffcU);
    if(!am_read(c,fh4_at(r.a[3],r.d[7]),4,value))return false;r.a[3]=value;
    if(!am_read(c,fh4_at(r.a[4],6),2,value))return false;am_word(r.d[6],value);
    if(!fh4_next_word(c,r.d[7]))return false;r.pc=fh4_count_column(r)?f.finish:f.swap7;return true;
}
bool fh4_outer(AnimationMachineContext& c,const Fh4Routine& f) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    // SWAP D6; MOVE.W (A3)+,D5; MOVE.W (A3)+,D6; NEG.W D6; MOVE.W (A3)+,D7; [H: NEG.W D5].
    am_swap(r.d[6]);if(!fh4_next_word(c,r.d[5]) || !fh4_next_word(c,r.d[6]))return false;am_word(r.d[6],0U-r.d[6]);
    if(!fh4_next_word(c,r.d[7]))return false;if(f.h)am_word(r.d[5],0U-r.d[5]);
    if(!f.s) {
        // LSL.W #6,D5; ADD.W 2(A2),D5; MOVE.W #$400,D4.
        am_word(r.d[5],fh4_w(r.d[5])<<6);if(!am_read(c,fh4_at(r.a[2],2),2,value))return false;am_word(r.d[5],r.d[5]+value);
        am_word(r.d[4],0x400);
    } else {
        // MOVEQ #0,D3; MOVE.B 4(A2),D3; ADDQ.W #1,D3; MULS.W D3,D5 (32-bit signed product: the two's complement bits of
        // sext(D5.W) * sext(D3.W) mod 2^32); LSL.W #4,D3; SUBI.W #$100,D3; MOVE.B D5,D4; [H: SUB.B D3,D4]; CLR.B D5; ASR.L #2,D5;
        // ADD.W 2(A2),D5.
        r.d[3]=0;if(!am_read(c,fh4_at(r.a[2],4),1,value))return false;am_byte(r.d[3],value);am_word(r.d[3],r.d[3]+1U);
        r.d[5]=am_extend_word(fh4_w(r.d[5]))*am_extend_word(fh4_w(r.d[3]));
        am_word(r.d[3],fh4_w(r.d[3])<<4);am_word(r.d[3],r.d[3]-0x100U);am_byte(r.d[4],r.d[5]);if(f.h)am_byte(r.d[4],r.d[4]-r.d[3]);
        am_byte(r.d[5],0);r.d[5]=(r.d[5]>>2)|((r.d[5]&0x80000000U)?0xc0000000U:0U);
        if(!am_read(c,fh4_at(r.a[2],2),2,value))return false;am_word(r.d[5],r.d[5]+value);
    }
    // SWAP D6; SUBI.W #$100,D7; BCS.W finish.
    am_swap(r.d[6]);r.pc=fh4_count_column(r)?f.finish:f.height;return true;
}
bool fh4_column(AnimationMachineContext& c,const Fh4Routine& f) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    // SUBQ.W #1,D6; MOVE.W D6,D0; ADDI.W #$8401,D0; SWAP D0; MOVE.W D5,D0; ADD.W D0,D0; MOVE.L D0,(A6).
    am_word(r.d[6],r.d[6]-1U);am_word(r.d[0],r.d[6]);am_word(r.d[0],r.d[0]+0x8401U);am_swap(r.d[0]);am_word(r.d[0],r.d[5]);
    am_word(r.d[0],r.d[0]+r.d[0]);if(!fh4_video(c,r.d[0]))return false;
    // [not S: MOVEQ #-1,D0]; MOVE.W D6,D0; ADDI.W #$8001,D0; SWAP D0; [S: MOVE.W D4,D0; MOVE.B 5(A2),D0]; MOVE.L D0,(A6).
    if(!f.s)r.d[0]=0xffffffffU;
    am_word(r.d[0],r.d[6]);am_word(r.d[0],r.d[0]+0x8001U);am_swap(r.d[0]);
    if(f.s) {am_word(r.d[0],r.d[4]);if(!am_read(c,fh4_at(r.a[2],5),1,value))return false;am_byte(r.d[0],value);}
    if(!fh4_video(c,r.d[0]))return false;
    // MOVEQ #2,D2; SWAP D2; MOVEQ #0,D0; MOVE.W D6,D0; ADDQ.W #1,D0; LSL.W #6,D0; [V: ADD.B D7,D0; NEG.L D2]; SWAP D1; MOVE.W D0,D1;
    // ADDQ.W #1,D1; SWAP D1; SWAP D0; MOVE.B D7,D0; ADD.W D0,D0.
    r.d[2]=0x20000U;r.d[0]=0;am_word(r.d[0],r.d[6]);am_word(r.d[0],r.d[0]+1U);am_word(r.d[0],fh4_w(r.d[0])<<6);
    if(f.v) {am_byte(r.d[0],r.d[0]+r.d[7]);r.d[2]=0U-r.d[2];}
    am_swap(r.d[1]);am_word(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]+1U);am_swap(r.d[1]);am_swap(r.d[0]);am_byte(r.d[0],r.d[7]);
    am_word(r.d[0],r.d[0]+r.d[0]);
    // MOVEM.L D3-D5,-(A7); MOVE.W D1,D3; MOVE.L D1,D4; ANDI.W #$ff00,D3; JMP table(PC,D0.W) (live target, main decision 3).
    if(!am_push(c,4,r.d[5]) || !am_push(c,4,r.d[4]) || !am_push(c,4,r.d[3]))return false;
    am_word(r.d[3],r.d[1]);r.d[4]=r.d[1];am_word(r.d[3],r.d[3]&0xff00U);r.pc=f.table+am_extend_word(fh4_w(r.d[0]));return true;
}
// Cell 31 of an S routine continues into the Duff head: CLR.W D0; MOVEQ #2,D2; SWAP D2; SWAP D3; CLR.W D3; MOVE.B D7,D3;
// [V: SWAP D0; ADD.W D3,D0; ADDQ.W #4,D0; SWAP D0]; MOVE.L D0,D4; CLR.W D4; ADDI.L #$10000,D0; MOVE.W #$100,D0; ADD.W D3,D3 (twice);
// JMP duff(PC,D3.W) (live target, main decision 3).
void fh4_duff_head(AnimationMachineState& r,const Fh4Routine& f) {
    am_word(r.d[0],0);r.d[2]=0x20000U;am_swap(r.d[3]);am_word(r.d[3],0);am_byte(r.d[3],r.d[7]);
    if(f.v) {am_swap(r.d[0]);am_word(r.d[0],r.d[0]+r.d[3]);am_word(r.d[0],r.d[0]+4U);am_swap(r.d[0]);}
    r.d[4]=r.d[0];am_word(r.d[4],0);r.d[0]+=0x10000U;am_word(r.d[0],0x100);am_word(r.d[3],r.d[3]+r.d[3]);am_word(r.d[3],r.d[3]+r.d[3]);
    r.pc=f.duff+am_extend_word(fh4_w(r.d[3]));
}
bool fh4_routine_block(AnimationMachineContext& c,const Fh4Routine& f) {
    AnimationMachineState& r=c.s;const std::uint32_t pc=r.pc;std::uint32_t value=0;
    if(pc==f.head)return fh4_head(c,f);
    if(pc==f.swap7) {am_swap(r.d[7]);r.pc=f.outer;return true;}               // SWAP D7.
    if(pc==f.outer)return fh4_outer(c,f);
    if(pc==f.height) {
        // SUBQ.B #1,D7; ANDI.B #$1f,D7; ADD.B D7,D7; BRA.W test.
        am_byte(r.d[7],r.d[7]-1U);am_byte(r.d[7],r.d[7]&0x1fU);am_byte(r.d[7],r.d[7]+r.d[7]);r.pc=f.test;return true;
    }
    if(pc==f.step) {
        // MOVEQ #2,D2; ADD.B D7,D2; LSL.W #1,D2; ADDA.W D2,A3; SUBI.W #$100,D7; BCS.W next (else the re-entry).
        r.d[2]=2;am_byte(r.d[2],r.d[2]+r.d[7]);am_word(r.d[2],fh4_w(r.d[2])<<1);r.a[3]+=am_extend_word(fh4_w(r.d[2]));
        r.pc=fh4_count_column(r)?f.next:fh4_reentry(f);return true;
    }
    if(f.advance!=0 && pc==f.advance) {
        // Not H: ADD.W D4,D5 (S: the scaled step added to D5.W); falls into test.
        if(f.s)fh4_scaled_step(r);
        am_word(r.d[5],r.d[5]+(f.s?r.d[2]:r.d[4]));r.pc=f.test;return true;
    }
    if(pc==f.test) {
        // CMP.W 4(A4),D6; BLE.W finish (signed WORD).
        if(!am_read(c,fh4_at(r.a[4],4),2,value))return false;
        r.pc=fh4_signed_word(r.d[6])<=fh4_signed_word(value)?f.finish:(f.s?f.scale:f.clip);return true;
    }
    if(f.scale!=0 && pc==f.scale) {
        // ANDI.W #$ff,D4; ADD.W D3,D4; BMI.B step.
        am_word(r.d[4],r.d[4]&0xffU);am_word(r.d[4],r.d[4]+r.d[3]);r.pc=(r.d[4]&0x8000U)!=0U?f.step:f.clip;return true;
    }
    if(pc==f.clip) {
        // [H: SUB.W D4,D5 (S: the scaled step subtracted)]; MOVE.W D5,D2; ADDI.W #$200,D2; CMPI.W #$5000,D2; BCC.B step.
        if(f.h) {if(f.s)fh4_scaled_step(r);am_word(r.d[5],r.d[5]-(f.s?r.d[2]:r.d[4]));}
        am_word(r.d[2],r.d[5]);am_word(r.d[2],r.d[2]+0x200U);r.pc=fh4_w(r.d[2])>=0x5000U?f.step:f.column;return true;
    }
    if(pc==f.column)return fh4_column(c,f);
    if(pc>=f.table && pc<f.table+4U*FH4_ENTRIES && ((pc-f.table)&3U)==0) {
        // BRA.W cells + 18 * (31 - i).
        r.pc=f.cells+FH4_CELL_BYTES*(FH4_ENTRIES-1U-(pc-f.table)/4U);return true;
    }
    if(pc>=f.cells && pc<f.cells+FH4_CELL_BYTES*FH4_ENTRIES && (pc-f.cells)%FH4_CELL_BYTES==0) {
        const std::uint32_t j=(pc-f.cells)/FH4_CELL_BYTES;if(!fh4_cell(c))return false;
        if(j+1U<FH4_ENTRIES) {r.pc=pc+FH4_CELL_BYTES;return true;}
        if(f.s) {fh4_duff_head(r,f);return true;}
        // MOVEM.L (A7)+,D3-D5; SUBI.W #$100,D7; BCC.W re-entry (else next).
        if(!fh4_pop_d3_d5(c))return false;r.pc=fh4_count_column(r)?f.next:fh4_reentry(f);return true;
    }
    if(f.duff!=0 && pc>=f.duff && pc<f.duff+FH4_DUFF_BYTES*FH4_ENTRIES && (pc-f.duff)%FH4_DUFF_BYTES==0) {
        if(pc+FH4_DUFF_BYTES<f.duff+FH4_DUFF_BYTES*FH4_ENTRIES) {
            // MOVE.L D4,(A6); ADD.L D2,D4; MOVE.L D0,(A6); ADD.L D2,D0.
            if(!fh4_video(c,r.d[4]))return false;r.d[4]+=r.d[2];if(!fh4_video(c,r.d[0]))return false;r.d[0]+=r.d[2];
            r.pc=pc+FH4_DUFF_BYTES;return true;
        }
        // SWAP D3; MOVEM.L (A7)+,D3-D5; SUBI.W #$100,D7; BCC.W re-entry (else next).
        am_swap(r.d[3]);if(!fh4_pop_d3_d5(c))return false;r.pc=fh4_count_column(r)?f.next:fh4_reentry(f);return true;
    }
    if(pc==f.next) {
        // SUBI.L #$1000000,D7; BCC.W outer (else finish).
        const bool borrow=r.d[7]<0x1000000U;r.d[7]-=0x1000000U;r.pc=borrow?f.finish:f.outer;return true;
    }
    if(pc==f.finish) {
        // MOVE.W D6,6(A4); RTS.
        if(!am_write(c,fh4_at(r.a[4],6),2,fh4_w(r.d[6])))return false;return am_return(c);
    }
    return am_error(c,"unsupported animation frame head h4 PC");
}
}
// F5 frame head H4 (contract: the whole reverse writer family H4..H7, 736 block starts): the table 11792..117b2 entered by the H1
// writer JSR (A3,D7.W) at 16cb2 (live target; landings outside the table run the block they hit or give the h4 interior error), and
// the eight routines 117b2..13b46 executed by one template with the flags H / V / S. The computed JMPs (cell table, Duff) set the
// live target; on every path from a routine head D7.B is an even value 0..62, so the targets are the 32 table entries / Duff entries.
// MOVE.L Dn,(A6) with A6 = 3c0000 is one size 4 video port event. No callee, wait, TRAP, carry consumer or known-carry producer.
bool animation_frame_head_h4_block(AnimationMachineContext& c) {
    const std::uint32_t pc=c.s.pc;
    if(pc>=FH4_TABLE && pc<FH4_ROUTINES[0].head) {
        if(((pc-FH4_TABLE)&3U)!=0)return am_error(c,"unsupported animation frame head h4 PC");
        c.s.pc=FH4_ROUTINES[(pc-FH4_TABLE)/4U].head;return true;                  // BRA.W routine k.
    }
    for(unsigned int k=0;k<8;++k) {
        const Fh4Routine& f=FH4_ROUTINES[k];
        if(pc>=f.head && pc<f.end)return fh4_routine_block(c,f);
    }
    return am_error(c,"unsupported animation frame head h4 PC");
}
}
