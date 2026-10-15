#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// F6c IRQ-only sprite writer families (contract docs/analysis/animation-machine-irq-f6c-contract.md; scope main decision: parametric
// executor, every entry PC routed). Family A (table f226 + 4k, forward) is the H8 frame-head routine k and family B (table 13b46 + 4k,
// reverse) the H4 routine k, each with the same edits (proof: tools/check_animation_irq_f6c_template.py, exact instruction text and
// mapped branch targets for all 16 routines; flags H = bit 0, V = bit 1, S = bit 2 of k):
//   outer   [V: MOVEQ #0,D4; MOVE.B D7,D4; LSL.W #4,D4; NOT.W D6; ADD.W D4,D6] after the (A3)+ reads, then the SCB3 word in D6.W
//           (not S: LSL.W #7,D6; ADD.W ANDI(8(A2),ff80); OR.B D7,D6 / S: the MULS / MULU scaled form, see f6c_outer);
//   test    A: CMP.W 2(A4),D6; BPL.W finish (H8: 6(A4))   B: CMP.W (A4),D6; BLE.W finish (H4: 4(A4));
//   scb3    a new block before the column: [B: SUBQ.W #1,D6 (moved from the H4 column)]; MOVE.L #8201,D2; MOVE.L D6,D0; ADD.W D2,D0;
//           SWAP D0; MOVE.L D0,(A6) (one extra video event per column); A: CMP.W 6(A4),D6; BMI.B skip / B: CMP.W 4(A4),D6; BPL.B step;
//   skip    A only: the ADDQ.W #1,D6 at step - 2 (unreached in H8) is the BMI target, falling into step.
// The column, cell table, cells, Duff run, cell / Duff tails, next and finish blocks are the H8 (A) / H4 (B) blocks unchanged.
// Role start PCs (derived from the ROM by the template proof, which also compares this table): advance only without H, skip only in A,
// scale and duff only with S (0 = absent).
struct F6cRoutine {
    std::uint32_t head,swap7,outer,height,skip,step,advance,test,scale,clip,scb3,column,table,cells,duff,next,finish,end;
    bool h,v,s;
};
const F6cRoutine F6C_A[8]={
    {0xf246,0xf29e,0xf2a0,0xf2cc,0xf2d8,0xf2da,0xf2ea,0xf2ec,0,0xf2f4,0xf300,0xf314,0xf358,0xf3d8,0,0xf626,0xf630,0xf636,false,false,false},
    {0xf636,0xf68e,0xf690,0xf6be,0xf6ca,0xf6cc,0,0xf6dc,0,0xf6e4,0xf6f2,0xf706,0xf74a,0xf7ca,0,0xfa18,0xfa22,0xfa28,true,false,false},
    {0xfa28,0xfa80,0xfa82,0xfab8,0xfac4,0xfac6,0xfad6,0xfad8,0,0xfae0,0xfaec,0xfb00,0xfb48,0xfbc8,0,0xfe16,0xfe20,0xfe26,false,true,false},
    {0xfe26,0xfe7e,0xfe80,0xfeb8,0xfec4,0xfec6,0,0xfed6,0,0xfede,0xfeec,0xff00,0xff48,0xffc8,0,0x10216,0x10220,0x10226,true,true,false},
    {0x10226,0x1027e,0x10280,0x102d8,0x102e4,0x102e6,0x102f6,0x10302,0x1030a,0x10312,0x1031e,0x10332,0x1037a,0x103fa,0x1065c,0x10764,0x1076e,
     0x10774,false,false,true},
    {0x10774,0x107cc,0x107ce,0x1082a,0x10836,0x10838,0,0x10848,0x10850,0x10858,0x10870,0x10884,0x108cc,0x1094c,0x10bae,0x10cb6,0x10cc0,0x10cc6,
     true,false,true},
    {0x10cc6,0x10d1e,0x10d20,0x10d82,0x10d8e,0x10d90,0x10da0,0x10dac,0x10db4,0x10dbc,0x10dc8,0x10ddc,0x10e28,0x10ea8,0x11112,0x1121a,0x11224,
     0x1122a,false,true,true},
    {0x1122a,0x11282,0x11284,0x112ea,0x112f6,0x112f8,0,0x11308,0x11310,0x11318,0x11330,0x11344,0x11390,0x11410,0x1167a,0x11782,0x1178c,0x11792,
     true,true,true}};
const F6cRoutine F6C_B[8]={
    {0x13b66,0x13bbe,0x13bc0,0x13bec,0,0x13bf8,0x13c08,0x13c0a,0,0x13c10,0x13c1c,0x13c32,0x13c76,0x13cf6,0,0x13f42,0x13f4c,0x13f52,false,false,false},
    {0x13f52,0x13faa,0x13fac,0x13fda,0,0x13fe6,0,0x13ff6,0,0x13ffc,0x1400a,0x14020,0x14064,0x140e4,0,0x14330,0x1433a,0x14340,true,false,false},
    {0x14340,0x14398,0x1439a,0x143d0,0,0x143dc,0x143ec,0x143ee,0,0x143f4,0x14400,0x14416,0x1445e,0x144de,0,0x1472a,0x14734,0x1473a,false,true,false},
    {0x1473a,0x14792,0x14794,0x147cc,0,0x147d8,0,0x147e8,0,0x147ee,0x147fc,0x14812,0x1485a,0x148da,0,0x14b26,0x14b30,0x14b36,true,true,false},
    {0x14b36,0x14b8e,0x14b90,0x14be8,0,0x14bf4,0x14c04,0x14c10,0x14c16,0x14c1e,0x14c2a,0x14c40,0x14c88,0x14d08,0x14f6a,0x15070,0x1507a,0x15080,
     false,false,true},
    {0x15080,0x150d8,0x150da,0x15136,0,0x15142,0,0x15152,0x15158,0x15160,0x15178,0x1518e,0x151d6,0x15256,0x154b8,0x155be,0x155c8,0x155ce,
     true,false,true},
    {0x155ce,0x15626,0x15628,0x1568a,0,0x15696,0x156a6,0x156b2,0x156b8,0x156c0,0x156cc,0x156e2,0x1572e,0x157ae,0x15a18,0x15b1e,0x15b28,0x15b2e,
     false,true,true},
    {0x15b2e,0x15b86,0x15b88,0x15bee,0,0x15bfa,0,0x15c0a,0x15c10,0x15c18,0x15c30,0x15c46,0x15c92,0x15d12,0x15f7c,0x16082,0x1608c,0x16092,
     true,true,true}};
const std::uint32_t F6C_TABLE_A=0xf226;          // BRA.W routine k at f226 + 4k (entered from 16d80 JSR (A3,D7.W))
const std::uint32_t F6C_TABLE_B=0x13b46;         // BRA.W routine k at 13b46 + 4k (entered from 16e3c JSR (A3,D7.W))
const std::uint32_t F6C_BANK_TABLE=0x200004;     // LEA 200004.l,A3 (bank window, live PVC bank)
const std::uint32_t F6C_VIDEO=0x3c0000;
const std::uint32_t F6C_CELL_BYTES=18;           // MOVE.W (A3)+,D5 .. ADD.L D2,D0 (9 instructions)
const std::uint32_t F6C_DUFF_BYTES=8;            // MOVE.L D4,(A6); ADD.L D2,D4; MOVE.L D0,(A6); ADD.L D2,D0
const std::uint32_t F6C_ENTRIES=32;
const char* const F6C_ERROR="unsupported animation irq f6c PC";
std::uint32_t f6c_w(std::uint32_t value) {return value&65535U;}
// Signed WORD value without implementation-defined conversions.
std::int32_t f6c_signed_word(std::uint32_t value) {return static_cast<std::int32_t>(f6c_w(value)^0x8000U)-0x8000;}
// d16(An): base + sign-extended displacement (mod 2^32).
std::uint32_t f6c_at(std::uint32_t base,std::uint32_t displacement) {return am_index(base,displacement);}
// MOVE.L Dn,(A6) (contract decision 3): A6 = 3c0000 is one size 4 video port event, any other A6 is an ordinary bus write.
bool f6c_video(AnimationMachineContext& c,std::uint32_t value) {
    if((c.s.a[6]&0xffffffU)!=F6C_VIDEO)return am_write(c,c.s.a[6],4,value);
    VideoPortWrite port;port.address=F6C_VIDEO;port.size=4;port.value=value;c.ports.push_back(port);return true;
}
// MOVE.W (A3)+,Dn.
bool f6c_next_word(AnimationMachineContext& c,std::uint32_t& target) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[3],2,value))return false;c.s.a[3]+=2U;am_word(target,value);return true;
}
// SUBI.W #$100,D7: C (borrow) = D7.W < $100; the low BYTE does not change.
bool f6c_count_column(AnimationMachineState& r) {
    const bool borrow=f6c_w(r.d[7])<0x100U;am_word(r.d[7],r.d[7]-0x100U);return borrow;
}
// The column re-entry: advance without H, test with H (the H routines apply the column step in clip).
std::uint32_t f6c_reentry(const F6cRoutine& f) {return f.h?f.test:f.advance;}
// S column step: MOVE.W D4,D2; ADDI.W #$100,D2; CLR.B D2; LSR.W #2,D2 (the value added to / subtracted from D5.W).
void f6c_scaled_step(AnimationMachineState& r) {
    am_word(r.d[2],r.d[4]);am_word(r.d[2],r.d[2]+0x100U);am_byte(r.d[2],0);am_word(r.d[2],f6c_w(r.d[2])>>2);
}
// ASR.L #n,Dn (n = 1 or 2) without implementation-defined signed shifts.
std::uint32_t f6c_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t fill=(value&0x80000000U)!=0U?~(0xffffffffU>>n):0U;return (value>>n)|fill;
}
// MOVEM.L (A7)+,D3-D5 (LONG pops in register order); A: ADDQ.W #1,D6 (H8 direction edit 5).
bool f6c_pop_d3_d5(AnimationMachineContext& c,bool forward) {
    for(unsigned int i=3;i<=5;++i) {std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.d[i]=value;}
    if(forward)am_word(c.s.d[6],c.s.d[6]+1U);
    return true;
}
// One 18-byte cell: MOVE.W (A3)+,D5; ADD.W D3,D5; EOR.B D1,D5; MOVE.W D5,D4; MOVE.L D4,(A6); ADD.L D2,D4; MOVE.W (A3)+,D0;
// MOVE.L D0,(A6); ADD.L D2,D0.
bool f6c_cell(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    if(!f6c_next_word(c,r.d[5]))return false;am_word(r.d[5],r.d[5]+r.d[3]);am_byte(r.d[5],r.d[5]^r.d[1]);am_word(r.d[4],r.d[5]);
    if(!f6c_video(c,r.d[4]))return false;r.d[4]+=r.d[2];
    if(!f6c_next_word(c,r.d[0]) || !f6c_video(c,r.d[0]))return false;r.d[0]+=r.d[2];return true;
}
bool f6c_head(AnimationMachineContext& c,const F6cRoutine& f,bool forward) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    // MOVEQ #0,D2; MOVE.L 8(A2),D2; MOVE.W D2,D7; ANDI.W #7,D7; MOVE.W D0,-(A7); MOVE.W D7,D0; MOVE.W D7,-7ff0(A5).
    r.d[2]=0;if(!am_read(c,f6c_at(r.a[2],8),4,value))return false;r.d[2]=value;am_word(r.d[7],r.d[2]);am_word(r.d[7],r.d[7]&7U);
    if(!am_push(c,2,f6c_w(r.d[0])))return false;am_word(r.d[0],r.d[7]);
    if(!am_write(c,f6c_at(r.a[5],0x8010),2,f6c_w(r.d[7])))return false;
    // ADDQ.W #1,D7; LSL.W #8,D7; LSL.W #4,D7; MOVE.W D7,2ffff2.l; MOVE.W #0,2ffff0.l (PVC bank select); MOVE.W D0,D7; MOVE.W (A7)+,D0.
    am_word(r.d[7],r.d[7]+1U);am_word(r.d[7],f6c_w(r.d[7])<<8);am_word(r.d[7],f6c_w(r.d[7])<<4);
    if(!am_write(c,0x2ffff2,2,f6c_w(r.d[7])) || !am_write(c,0x2ffff0,2,0))return false;
    am_word(r.d[7],r.d[0]);if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
    // LSR.L #1,D2; MOVE.W D2,D7; ANDI.W #3fc,D7; LEA 200004.l,A3; MOVEA.L (A3,D7.W),A3; LSR.L #8,D2; MOVE.W D2,D7; ANDI.W #3ffc,D7;
    // MOVEA.L (A3,D7.W),A3; MOVE.W 4(A4),D6 (A) / 6(A4),D6 (B); MOVE.W (A3)+,D7; SUBI.W #$100,D7; BCS.W finish.
    r.d[2]>>=1;am_word(r.d[7],r.d[2]);am_word(r.d[7],r.d[7]&0x3fcU);r.a[3]=F6C_BANK_TABLE;
    if(!am_read(c,f6c_at(r.a[3],r.d[7]),4,value))return false;r.a[3]=value;
    r.d[2]>>=8;am_word(r.d[7],r.d[2]);am_word(r.d[7],r.d[7]&0x3ffcU);
    if(!am_read(c,f6c_at(r.a[3],r.d[7]),4,value))return false;r.a[3]=value;
    if(!am_read(c,f6c_at(r.a[4],forward?4U:6U),2,value))return false;am_word(r.d[6],value);
    if(!f6c_next_word(c,r.d[7]))return false;r.pc=f6c_count_column(r)?f.finish:f.swap7;return true;
}
bool f6c_outer(AnimationMachineContext& c,const F6cRoutine& f) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    // SWAP D6; MOVE.W (A3)+,D5; MOVE.W (A3)+,D6; NEG.W D6; MOVE.W (A3)+,D7; [H: NEG.W D5].
    am_swap(r.d[6]);if(!f6c_next_word(c,r.d[5]) || !f6c_next_word(c,r.d[6]))return false;am_word(r.d[6],0U-r.d[6]);
    if(!f6c_next_word(c,r.d[7]))return false;if(f.h)am_word(r.d[5],0U-r.d[5]);
    // [V: MOVEQ #0,D4; MOVE.B D7,D4; LSL.W #4,D4; NOT.W D6; ADD.W D4,D6].
    if(f.v) {r.d[4]=r.d[7]&0xffU;am_word(r.d[4],f6c_w(r.d[4])<<4);am_word(r.d[6],~r.d[6]);am_word(r.d[6],r.d[6]+r.d[4]);}
    if(!f.s) {
        // LSL.W #6,D5; ADD.W 2(A2),D5; LSL.W #7,D6; MOVE.W 8(A2),D4; ANDI.W #ff80,D4; ADD.W D4,D6; OR.B D7,D6; MOVE.W #$400,D4.
        am_word(r.d[5],f6c_w(r.d[5])<<6);if(!am_read(c,f6c_at(r.a[2],2),2,value))return false;am_word(r.d[5],r.d[5]+value);
        am_word(r.d[6],f6c_w(r.d[6])<<7);if(!am_read(c,f6c_at(r.a[2],8),2,value))return false;am_word(r.d[4],value);
        am_word(r.d[4],r.d[4]&0xff80U);am_word(r.d[6],r.d[6]+r.d[4]);am_byte(r.d[6],r.d[6]|(r.d[7]&0xffU));am_word(r.d[4],0x400);
    } else {
        // MOVEQ #0,D2; MOVE.B 5(A2),D2; ADDQ.W #1,D2; MOVE.W D6,D3; MULS.W D2,D3 (32-bit signed product: the two's complement bits of
        // sext(D3.W) * sext(D2.W) mod 2^32); CLR.B D3; ASR.L #1,D3; MOVE.W D3,D6.
        r.d[2]=0;if(!am_read(c,f6c_at(r.a[2],5),1,value))return false;am_byte(r.d[2],value);am_word(r.d[2],r.d[2]+1U);
        am_word(r.d[3],r.d[6]);r.d[3]=am_extend_word(f6c_w(r.d[3]))*am_extend_word(f6c_w(r.d[2]));am_byte(r.d[3],0);
        r.d[3]=f6c_asr(r.d[3],1);am_word(r.d[6],r.d[3]);
        // MOVE.W 8(A2),D3; ANDI.W #ff80,D3; ADD.W D3,D6; MOVEQ #0,D3; MOVE.B D7,D3; MULU.W D2,D3 (16 x 16 unsigned, at most ff * 100);
        // ADDI.W #$ff,D3; LSR.W #8,D3; OR.B D3,D6.
        if(!am_read(c,f6c_at(r.a[2],8),2,value))return false;am_word(r.d[3],value);am_word(r.d[3],r.d[3]&0xff80U);
        am_word(r.d[6],r.d[6]+r.d[3]);r.d[3]=(r.d[7]&0xffU)*f6c_w(r.d[2]);am_word(r.d[3],r.d[3]+0xffU);am_word(r.d[3],f6c_w(r.d[3])>>8);
        am_byte(r.d[6],r.d[6]|(r.d[3]&0xffU));
        // MOVEQ #0,D3; MOVE.B 4(A2),D3; ADDQ.W #1,D3; MULS.W D3,D5; LSL.W #4,D3; SUBI.W #$100,D3; MOVE.B D5,D4; [H: SUB.B D3,D4];
        // CLR.B D5; ASR.L #2,D5; ADD.W 2(A2),D5.
        r.d[3]=0;if(!am_read(c,f6c_at(r.a[2],4),1,value))return false;am_byte(r.d[3],value);am_word(r.d[3],r.d[3]+1U);
        r.d[5]=am_extend_word(f6c_w(r.d[5]))*am_extend_word(f6c_w(r.d[3]));
        am_word(r.d[3],f6c_w(r.d[3])<<4);am_word(r.d[3],r.d[3]-0x100U);am_byte(r.d[4],r.d[5]);if(f.h)am_byte(r.d[4],r.d[4]-r.d[3]);
        am_byte(r.d[5],0);r.d[5]=f6c_asr(r.d[5],2);
        if(!am_read(c,f6c_at(r.a[2],2),2,value))return false;am_word(r.d[5],r.d[5]+value);
    }
    // SWAP D6; SUBI.W #$100,D7; BCS.W finish.
    am_swap(r.d[6]);r.pc=f6c_count_column(r)?f.finish:f.height;return true;
}
// SCB3 block: [B: SUBQ.W #1,D6]; MOVE.L #$8201,D2; MOVE.L D6,D0; ADD.W D2,D0; SWAP D0; MOVE.L D0,(A6);
// A: CMP.W 6(A4),D6; BMI.B skip (N of the WORD difference)   B: CMP.W 4(A4),D6; BPL.B step.
bool f6c_scb3(AnimationMachineContext& c,const F6cRoutine& f,bool forward) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!forward)am_word(r.d[6],r.d[6]-1U);
    r.d[2]=0x8201U;r.d[0]=r.d[6];am_word(r.d[0],r.d[0]+r.d[2]);am_swap(r.d[0]);if(!f6c_video(c,r.d[0]))return false;
    if(!am_read(c,f6c_at(r.a[4],forward?6U:4U),2,value))return false;
    const bool negative=(f6c_w(r.d[6]-value)&0x8000U)!=0U;
    if(forward)r.pc=negative?f.skip:f.column;else r.pc=negative?f.column:f.step;
    return true;
}
bool f6c_column(AnimationMachineContext& c,const F6cRoutine& f) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    // MOVE.W D6,D0; ADDI.W #$8401,D0; SWAP D0; MOVE.W D5,D0; ADD.W D0,D0; MOVE.L D0,(A6).
    am_word(r.d[0],r.d[6]);am_word(r.d[0],r.d[0]+0x8401U);am_swap(r.d[0]);am_word(r.d[0],r.d[5]);
    am_word(r.d[0],r.d[0]+r.d[0]);if(!f6c_video(c,r.d[0]))return false;
    // [not S: MOVEQ #-1,D0]; MOVE.W D6,D0; ADDI.W #$8001,D0; SWAP D0; [S: MOVE.W D4,D0; MOVE.B 5(A2),D0]; MOVE.L D0,(A6).
    if(!f.s)r.d[0]=0xffffffffU;
    am_word(r.d[0],r.d[6]);am_word(r.d[0],r.d[0]+0x8001U);am_swap(r.d[0]);
    if(f.s) {am_word(r.d[0],r.d[4]);if(!am_read(c,f6c_at(r.a[2],5),1,value))return false;am_byte(r.d[0],value);}
    if(!f6c_video(c,r.d[0]))return false;
    // MOVEQ #2,D2; SWAP D2; MOVEQ #0,D0; MOVE.W D6,D0; ADDQ.W #1,D0; LSL.W #6,D0; [V: ADD.B D7,D0; NEG.L D2]; SWAP D1; MOVE.W D0,D1;
    // ADDQ.W #1,D1; SWAP D1; SWAP D0; MOVE.B D7,D0; ADD.W D0,D0.
    r.d[2]=0x20000U;r.d[0]=0;am_word(r.d[0],r.d[6]);am_word(r.d[0],r.d[0]+1U);am_word(r.d[0],f6c_w(r.d[0])<<6);
    if(f.v) {am_byte(r.d[0],r.d[0]+r.d[7]);r.d[2]=0U-r.d[2];}
    am_swap(r.d[1]);am_word(r.d[1],r.d[0]);am_word(r.d[1],r.d[1]+1U);am_swap(r.d[1]);am_swap(r.d[0]);am_byte(r.d[0],r.d[7]);
    am_word(r.d[0],r.d[0]+r.d[0]);
    // MOVEM.L D3-D5,-(A7); MOVE.W D1,D3; MOVE.L D1,D4; ANDI.W #$ff00,D3; JMP table(PC,D0.W) (live target, contract decision 2).
    if(!am_push(c,4,r.d[5]) || !am_push(c,4,r.d[4]) || !am_push(c,4,r.d[3]))return false;
    am_word(r.d[3],r.d[1]);r.d[4]=r.d[1];am_word(r.d[3],r.d[3]&0xff00U);r.pc=f.table+am_extend_word(f6c_w(r.d[0]));return true;
}
// Cell 31 of an S routine continues into the Duff head: CLR.W D0; MOVEQ #2,D2; SWAP D2; SWAP D3; CLR.W D3; MOVE.B D7,D3;
// [V: SWAP D0; ADD.W D3,D0; ADDQ.W #4,D0; SWAP D0]; MOVE.L D0,D4; CLR.W D4; ADDI.L #$10000,D0; MOVE.W #$100,D0; ADD.W D3,D3 (twice);
// JMP duff(PC,D3.W) (live target, contract decision 2).
void f6c_duff_head(AnimationMachineState& r,const F6cRoutine& f) {
    am_word(r.d[0],0);r.d[2]=0x20000U;am_swap(r.d[3]);am_word(r.d[3],0);am_byte(r.d[3],r.d[7]);
    if(f.v) {am_swap(r.d[0]);am_word(r.d[0],r.d[0]+r.d[3]);am_word(r.d[0],r.d[0]+4U);am_swap(r.d[0]);}
    r.d[4]=r.d[0];am_word(r.d[4],0);r.d[0]+=0x10000U;am_word(r.d[0],0x100);am_word(r.d[3],r.d[3]+r.d[3]);am_word(r.d[3],r.d[3]+r.d[3]);
    r.pc=f.duff+am_extend_word(f6c_w(r.d[3]));
}
bool f6c_routine_block(AnimationMachineContext& c,const F6cRoutine& f,bool forward) {
    AnimationMachineState& r=c.s;const std::uint32_t pc=r.pc;std::uint32_t value=0;
    if(pc==f.head)return f6c_head(c,f,forward);
    if(pc==f.swap7) {am_swap(r.d[7]);r.pc=f.outer;return true;}               // SWAP D7.
    if(pc==f.outer)return f6c_outer(c,f);
    if(pc==f.height) {
        // SUBQ.B #1,D7; ANDI.B #$1f,D7; ADD.B D7,D7; BRA.W test.
        am_byte(r.d[7],r.d[7]-1U);am_byte(r.d[7],r.d[7]&0x1fU);am_byte(r.d[7],r.d[7]+r.d[7]);r.pc=f.test;return true;
    }
    if(f.skip!=0 && pc==f.skip) {am_word(r.d[6],r.d[6]+1U);r.pc=f.step;return true;}   // A: ADDQ.W #1,D6; falls into step.
    if(pc==f.step) {
        // MOVEQ #2,D2; ADD.B D7,D2; LSL.W #1,D2; ADDA.W D2,A3; SUBI.W #$100,D7; BCS.W next (else the re-entry).
        r.d[2]=2;am_byte(r.d[2],r.d[2]+r.d[7]);am_word(r.d[2],f6c_w(r.d[2])<<1);r.a[3]+=am_extend_word(f6c_w(r.d[2]));
        r.pc=f6c_count_column(r)?f.next:f6c_reentry(f);return true;
    }
    if(f.advance!=0 && pc==f.advance) {
        // Not H: ADD.W D4,D5 (S: the scaled step added to D5.W); falls into test.
        if(f.s)f6c_scaled_step(r);
        am_word(r.d[5],r.d[5]+(f.s?r.d[2]:r.d[4]));r.pc=f.test;return true;
    }
    if(pc==f.test) {
        if(forward) {
            // CMP.W 2(A4),D6; BPL.W finish: N of the WORD difference D6.W - 2(A4) clear (V is not used).
            if(!am_read(c,f6c_at(r.a[4],2),2,value))return false;
            r.pc=(f6c_w(r.d[6]-value)&0x8000U)==0U?f.finish:(f.s?f.scale:f.clip);return true;
        }
        // CMP.W (A4),D6; BLE.W finish (signed WORD).
        if(!am_read(c,r.a[4],2,value))return false;
        r.pc=f6c_signed_word(r.d[6])<=f6c_signed_word(value)?f.finish:(f.s?f.scale:f.clip);return true;
    }
    if(f.scale!=0 && pc==f.scale) {
        // ANDI.W #$ff,D4; ADD.W D3,D4; BMI.B step.
        am_word(r.d[4],r.d[4]&0xffU);am_word(r.d[4],r.d[4]+r.d[3]);r.pc=(r.d[4]&0x8000U)!=0U?f.step:f.clip;return true;
    }
    if(pc==f.clip) {
        // [H: SUB.W D4,D5 (S: the scaled step subtracted)]; MOVE.W D5,D2; ADDI.W #$200,D2; CMPI.W #$5000,D2; BCC.B step.
        if(f.h) {if(f.s)f6c_scaled_step(r);am_word(r.d[5],r.d[5]-(f.s?r.d[2]:r.d[4]));}
        am_word(r.d[2],r.d[5]);am_word(r.d[2],r.d[2]+0x200U);r.pc=f6c_w(r.d[2])>=0x5000U?f.step:f.scb3;return true;
    }
    if(pc==f.scb3)return f6c_scb3(c,f,forward);
    if(pc==f.column)return f6c_column(c,f);
    if(pc>=f.table && pc<f.table+4U*F6C_ENTRIES && ((pc-f.table)&3U)==0) {
        // BRA.W cells + 18 * (31 - i).
        r.pc=f.cells+F6C_CELL_BYTES*(F6C_ENTRIES-1U-(pc-f.table)/4U);return true;
    }
    if(pc>=f.cells && pc<f.cells+F6C_CELL_BYTES*F6C_ENTRIES && (pc-f.cells)%F6C_CELL_BYTES==0) {
        const std::uint32_t j=(pc-f.cells)/F6C_CELL_BYTES;if(!f6c_cell(c))return false;
        if(j+1U<F6C_ENTRIES) {r.pc=pc+F6C_CELL_BYTES;return true;}
        if(f.s) {f6c_duff_head(r,f);return true;}
        // MOVEM.L (A7)+,D3-D5; [A: ADDQ.W #1,D6]; SUBI.W #$100,D7; BCC.W re-entry (else next).
        if(!f6c_pop_d3_d5(c,forward))return false;r.pc=f6c_count_column(r)?f.next:f6c_reentry(f);return true;
    }
    if(f.duff!=0 && pc>=f.duff && pc<f.duff+F6C_DUFF_BYTES*F6C_ENTRIES && (pc-f.duff)%F6C_DUFF_BYTES==0) {
        if(pc+F6C_DUFF_BYTES<f.duff+F6C_DUFF_BYTES*F6C_ENTRIES) {
            // MOVE.L D4,(A6); ADD.L D2,D4; MOVE.L D0,(A6); ADD.L D2,D0.
            if(!f6c_video(c,r.d[4]))return false;r.d[4]+=r.d[2];if(!f6c_video(c,r.d[0]))return false;r.d[0]+=r.d[2];
            r.pc=pc+F6C_DUFF_BYTES;return true;
        }
        // SWAP D3; MOVEM.L (A7)+,D3-D5; [A: ADDQ.W #1,D6]; SUBI.W #$100,D7; BCC.W re-entry (else next).
        am_swap(r.d[3]);if(!f6c_pop_d3_d5(c,forward))return false;r.pc=f6c_count_column(r)?f.next:f6c_reentry(f);return true;
    }
    if(pc==f.next) {
        // SUBI.L #$1000000,D7; BCC.W outer (else finish).
        const bool borrow=r.d[7]<0x1000000U;r.d[7]-=0x1000000U;r.pc=borrow?f.finish:f.outer;return true;
    }
    if(pc==f.finish) {
        // MOVE.W D6,4(A4) (A) / 6(A4) (B); RTS.
        if(!am_write(c,f6c_at(r.a[4],forward?4U:6U),2,f6c_w(r.d[6])))return false;return am_return(c);
    }
    return am_error(c,F6C_ERROR);
}
bool f6c_family_block(AnimationMachineContext& c,std::uint32_t table,const F6cRoutine* family,bool forward) {
    const std::uint32_t pc=c.s.pc;
    if(pc>=table && pc<family[0].head) {
        if(((pc-table)&3U)!=0)return am_error(c,F6C_ERROR);
        c.s.pc=family[(pc-table)/4U].head;return true;                          // BRA.W routine k.
    }
    for(unsigned int k=0;k<8;++k) {
        const F6cRoutine& f=family[k];
        if(pc>=f.head && pc<f.end)return f6c_routine_block(c,f,forward);
    }
    return am_error(c,F6C_ERROR);
}
}
// F6c IRQ sprite writer families (contract animation-machine-irq-f6c-contract.md): family A f226..11792 (624 block starts + 128 Duff
// entries, entered by the F6a writer JSR (A3,D7.W) at 16d80) and family B 13b46..16092 (616 + 128, JSR at 16e3c). The table JSR and the
// computed JMPs (cell table, Duff) set the live target (contract decision 2): a target inside this unit runs the block it hits or gives
// the f6c interior error, a target outside is left to its own routing. On every path from a routine head D7.B is an even value 0..62
// (height block), so the targets are the 32 table entries / Duff entries. MOVE.L Dn,(A6) with A6 = 3c0000 is one size 4 video port
// event. No callee, wait, TRAP, carry consumer or known-carry producer (every Bcc reads flags made in its own block).
bool animation_irq_f6c_block(AnimationMachineContext& c) {
    const std::uint32_t pc=c.s.pc;
    if(pc>=F6C_TABLE_A && pc<F6C_A[7].end)return f6c_family_block(c,F6C_TABLE_A,F6C_A,true);
    if(pc>=F6C_TABLE_B && pc<F6C_B[7].end)return f6c_family_block(c,F6C_TABLE_B,F6C_B,false);
    return am_error(c,F6C_ERROR);
}
}
