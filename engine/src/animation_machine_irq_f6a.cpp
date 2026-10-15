#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// F6a vblank IRQ shell (contract docs/analysis/animation-machine-irq-f6a-contract.md, scope decisions E1-E10): vblank 20c, raster 29c,
// the default raster callback 3dcc, credit a2c/a4e/a74/bbe, service c8c with the task restore cf0/d2a, sound/Z80 3cac, sound timer 48156,
// column control 1adf8/187d8, sprite flush driver 16cfa and the clear runs 16092/166a0 with their 381 computed entries.
const std::uint32_t F6A_VIDEO=0x3c0000;        // VRAM address/data port (LONG writes through (A4)/(A6) when the register holds it)
const std::uint32_t F6A_BIOS_FLAGS=0x10fd80;   // BYTE: bit 7 = game mode (IRQ handled by the game)
const std::uint32_t F6A_VRAM_COPY=0x104d8e;    // WORD VRAM address copy (2be MOVE.W (A7),104d8e.l; absolute)
const std::uint32_t F6A_TASK_END=0x10081c;     // task queue end (CMPA.L #10081c,A6)
const std::uint32_t F6A_RUN_END=0x1669e;       // clear run RTS (n = 0 entry); entry n = 1669e - 4n, n = 0..380
const std::uint32_t F6A_RUN_FIRST=0x160ae;     // entry n = 380
const std::uint32_t F6A_CELL_FIRST=0x18834;    // column cell k: 18834 + 1e*k (ADD.W D1,D7) and +2 (SUBI.W #400,D6 ...), k = 0..31
const std::uint32_t F6A_CELL_BYTES=0x1e;
const std::uint32_t F6A_CELLS=32;
const std::uint32_t F6A_COLUMN_END=0x18be6;    // RTS after cell 31 (whose write half has no next-cell prefix)
std::uint32_t f6a_b(std::uint32_t value) {return value&255U;}
std::uint32_t f6a_w(std::uint32_t value) {return value&65535U;}
// Signed WORD view without implementation-defined conversion.
std::int32_t f6a_sw(std::uint32_t value) {return static_cast<std::int32_t>(f6a_w(value)^0x8000U)-0x8000;}
// One device port write of the original size (absolute MMIO addresses of this unit).
void f6a_port(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t value) {
    VideoPortWrite port;port.address=address;port.size=static_cast<std::uint8_t>(size);
    port.value=size==1?f6a_b(value):(size==2?f6a_w(value):value);c.ports.push_back(port);
}
// MOVE.L Dn,(An): An = 3c0000 is one size 4 video port event (D1 convention), any other An is an ordinary bus write.
bool f6a_video(AnimationMachineContext& c,std::uint32_t address,std::uint32_t value) {
    if((address&0xffffffU)!=F6A_VIDEO)return am_write(c,address,4,value);
    f6a_port(c,F6A_VIDEO,4,value);return true;
}
bool f6a_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool f6a_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BSET / BCLR / BCHG #bit,d16(An) (BYTE read, modified BYTE written); set = the tested bit before the change.
bool f6a_bit(AnimationMachineContext& c,std::uint32_t address,unsigned int bit,int mode,bool& set) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    const std::uint32_t mask=1U<<bit;set=(value&mask)!=0U;
    const std::uint32_t next=mode>0?(value|mask):(mode<0?(value&~mask):(value^mask));
    return am_write(c,address,1,f6a_b(next));
}
// TST.B / MOVE.B abs: the BYTE.
bool f6a_byte(AnimationMachineContext& c,std::uint32_t address,std::uint32_t& value) {return am_read(c,address,1,value);}
// RTE (scope decision E3): SR := WORD (A7)+, PC := LONG (A7)+ (A7 += 6), C := SR bit 0. The executor has one supervisor stack and no
// trace: a popped SR with S = 0 or T = 1 is a checked error.
bool f6a_rte(AnimationMachineContext& c) {
    std::uint32_t sr=0,pc=0;
    if(!am_pop(c,2,sr) || !am_pop(c,4,pc))return false;
    if((sr&0x2000U)==0U || (sr&0x8000U)!=0U)return am_error(c,"unsupported animation irq RTE status");
    c.s.pc=pc;c.s.carry=(sr&1U)!=0U?AnimationCarrySet:AnimationCarryClear;return true;
}
// SBCD D6,D7 with D6.B = 1 and X = 0 (a62): BCD BYTE subtract of the canonical BE ROM's M68000 (all 256 inputs checked against
// Unicorn 2.1.4): a low-nibble borrow subtracts 6 more, a high-nibble borrow (only 00) gives 99.
std::uint32_t f6a_sbcd_one(std::uint32_t value) {
    value=f6a_b(value);if(value==0U)return 0x99U;
    return f6a_b(value-((value&15U)==0U?7U:1U));
}
// a36..a42 / a56 shared LSR.B / LSR.W #1,D0: returns the bit shifted out (C).
bool f6a_lsr_b(AnimationMachineState& r) {const bool out=(r.d[0]&1U)!=0U;am_byte(r.d[0],f6a_b(r.d[0])>>1);return out;}
bool f6a_lsr_w(AnimationMachineState& r) {const bool out=(r.d[0]&1U)!=0U;am_word(r.d[0],f6a_w(r.d[0])>>1);return out;}
// DBRA D1,target: D1.W -= 1; loop while D1.W != ffff.
std::uint32_t f6a_dbra(AnimationMachineState& r,std::uint32_t loop_pc,std::uint32_t exit_pc) {
    am_word(r.d[1],r.d[1]-1U);return f6a_w(r.d[1])!=0xffffU?loop_pc:exit_pc;
}
// 3d16 / 3d1e ring scan of the Z80 command ring 104cf4 (A0 = A5 - 330c, index D1.W, cursor WORD -328a(A5)).
bool f6a_ring_byte(AnimationMachineContext& c,std::uint32_t& value) {return am_read(c,am_index(c.s.a[0],c.s.d[1]),1,value);}
// Column cell prefix: MOVE.W D0,D7; MOVE.W (A1)+,D1; ADDI.W #400,D6; CMP.W D6,D3; BLS (D3.W <= D6.W unsigned).
bool f6a_cell_prefix(AnimationMachineContext& c,bool& lower_same) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    am_word(r.d[7],r.d[0]);if(!am_read(c,r.a[1],2,value))return false;r.a[1]+=2U;am_word(r.d[1],value);
    am_word(r.d[6],r.d[6]+0x400U);lower_same=f6a_w(r.d[3])<=f6a_w(r.d[6]);return true;
}
// SUBI.W #400,D6; MOVE.L D6,(A4); ADD.L D5,D6; ADD.W D4,D6; MOVE.L D7,(A4); ADD.L D5,D7.
bool f6a_cell_write(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;
    am_word(r.d[6],r.d[6]-0x400U);if(!f6a_video(c,r.a[4],r.d[6]))return false;r.d[6]+=r.d[5];am_word(r.d[6],r.d[6]+r.d[4]);
    if(!f6a_video(c,r.a[4],r.d[7]))return false;r.d[7]+=r.d[5];return true;
}
// Clear run JMP (A1,D1.W) with A1 = 1669e (contract decision 3: the target is live; a run entry is executed by this unit, any other
// target is left to the routing of the next step).
void f6a_run_jump(AnimationMachineState& r) {
    am_word(r.d[1],r.d[1]+r.d[1]);am_word(r.d[1],r.d[1]+r.d[1]);r.a[1]=F6A_RUN_END;r.pc=am_index(r.a[1],r.d[1]);
}
// 16d6a / 16e26: CMPI.W #ffff,4(A2); SNE D7; ANDI.W #4,D7; OR.B D1,D7; ADD.W D7,D7 (twice); LEA table(PC),A3; JSR (A3,D7.W).
bool f6a_writer_call(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!f6a_get(c,r.a[2],4,2,value))return false;
    am_byte(r.d[7],value!=0xffffU?0xffU:0U);am_word(r.d[7],r.d[7]&4U);am_byte(r.d[7],r.d[7]|r.d[1]);
    am_word(r.d[7],r.d[7]+r.d[7]);am_word(r.d[7],r.d[7]+r.d[7]);r.a[3]=table;return am_call(c,am_index(r.a[3],r.d[7]),return_pc);
}
// MOVE.W 4(A4),D0; MOVE.W 6(A4),D1; CMP.W D1,D0; BGT / BLT (signed WORD).
bool f6a_pair(AnimationMachineContext& c,std::uint32_t displacement,bool greater,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[4]=am_index(r.a[5],displacement);
    if(!f6a_get(c,r.a[4],4,2,value))return false;am_word(r.d[0],value);if(!f6a_get(c,r.a[4],6,2,value))return false;am_word(r.d[1],value);
    const bool taken=greater?f6a_sw(r.d[0])>f6a_sw(r.d[1]):f6a_sw(r.d[0])<f6a_sw(r.d[1]);r.pc=taken?taken_pc:next_pc;return true;
}
// MOVE.W d(A4),D1; SUB.W D0,D1; BSR.W run.
bool f6a_span(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t run,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!f6a_get(c,r.a[4],displacement,2,value))return false;
    am_word(r.d[1],value-r.d[0]);return am_call(c,run,return_pc);
}
// 16d56 / 16e12 tail: MOVE.W 6(A2),D1; LEA d3e(A5),A4; BCLR #2,D1; BEQ.
bool f6a_slot(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!f6a_get(c,r.a[2],6,2,value))return false;am_word(r.d[1],value);
    r.a[4]=am_index(r.a[5],0xd3e);const bool set=(r.d[1]&4U)!=0U;r.d[1]&=~4U;r.pc=set?set_pc:clear_pc;return true;
}
// MOVE.W s(A4),d(A4) for A4 = d3e(A5) then d46(A5) (16d26 / 16dde copies).
bool f6a_copy_pair(AnimationMachineContext& c,std::uint32_t source,std::uint32_t target) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[4]=am_index(r.a[5],0xd3e);if(!f6a_get(c,r.a[4],source,2,value) || !f6a_put(c,r.a[4],target,2,value))return false;
    r.a[4]=am_index(r.a[5],0xd46);return f6a_get(c,r.a[4],source,2,value) && f6a_put(c,r.a[4],target,2,value);
}
// One clear run entry n (1..380): n times MOVE.L D0,(A6); ADD.L D2,D0, then the RTS block 1669e.
bool f6a_run(AnimationMachineContext& c,std::uint32_t count) {
    AnimationMachineState& r=c.s;
    for(std::uint32_t i=0;i<count;++i) {if(!f6a_video(c,r.a[6],r.d[0]))return false;r.d[0]+=r.d[2];}
    r.pc=F6A_RUN_END;return true;
}
}
bool animation_irq_f6a_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool set=false;
    // ---- clear run entries 160ae..1669a (n = (1669e - PC) / 4 = 1..380); 1669e (n = 0) is the RTS case below.
    if(r.pc>=F6A_RUN_FIRST && r.pc<F6A_RUN_END) {
        if(((F6A_RUN_END-r.pc)&3U)!=0U)return am_error(c,"unsupported animation irq f6a PC");
        return f6a_run(c,(F6A_RUN_END-r.pc)>>2);
    }
    // ---- column cells 18834..18bd8: cell k ADD.W D1,D7 at c, the write half at c+2.
    if(r.pc>=F6A_CELL_FIRST && r.pc<F6A_COLUMN_END) {
        const std::uint32_t offset=r.pc-F6A_CELL_FIRST,k=offset/F6A_CELL_BYTES,part=offset%F6A_CELL_BYTES;
        if(part==0U) {am_word(r.d[7],r.d[7]+r.d[1]);r.pc+=2U;return true;}
        if(part!=2U)return am_error(c,"unsupported animation irq f6a PC");
        if(!f6a_cell_write(c))return false;
        if(k+1U==F6A_CELLS) {r.pc=F6A_COLUMN_END;return true;}
        if(!f6a_cell_prefix(c,set))return false;
        const std::uint32_t next=F6A_CELL_FIRST+(k+1U)*F6A_CELL_BYTES;r.pc=set?next+2U:next;return true;
    }
    switch(r.pc) {
    // ---- RTS blocks.
    case 0x3dcc:case 0xa4c:case 0xa72:case 0xaba:case 0xb0a:case 0xbc8:case 0xbec:case 0xc96:case 0x3cde:case 0x3d06:case 0x4817e:
    case 0x18be6:case 0x1669e:return am_return(c);
    // ---- vblank IRQ 20c: MOVE.W #6,3c000c.l; TST.B 10fd80.l; BMI.W 224 / JMP c00438.l (BIOS INT1 boundary).
    case 0x20c:f6a_port(c,0x3c000c,2,6);if(!f6a_byte(c,F6A_BIOS_FLAGS,value))return false;r.pc=(value&0x80U)!=0U?0x224:0x21e;return true;
    case 0x21e:r.pc=0xc00438;return true;
    // MOVEM.L D0-D7/A0-A6,-(A7); LEA 108000.l,A5; MOVE.W -3272(A5),-(A7); MOVE.W -7ff0(A5),-(A7); MOVEA.L -7ffa(A5),A0; JSR (A0).
    case 0x224:
        for(int i=6;i>=0;--i)if(!am_push(c,4,r.a[i]))return false;
        for(int i=7;i>=0;--i)if(!am_push(c,4,r.d[i]))return false;
        r.a[5]=0x108000;
        if(!f6a_get(c,r.a[5],0xcd8e,2,value) || !am_push(c,2,value))return false;
        if(!f6a_get(c,r.a[5],0x8010,2,value) || !am_push(c,2,value))return false;
        if(!f6a_get(c,r.a[5],0x8006,4,value))return false;r.a[0]=value;return am_call(c,r.a[0],0x23c);
    case 0x23c:return am_call(c,0xc8c,0x242);
    case 0x242:return am_call(c,0xc0044a,0x248);   // BIOS SYSTEM_IO boundary (the declared resume to 248 is the frame driver's, E4).
    // MOVE.W #0,3c0004.l; LEA 108000.l,A5; MOVE.W (A7)+,-7ff0(A5); MOVEM.W D0/D7,-(A7); MOVE.W -7ff0(A5),D7; MOVE.W D7,D0;
    // ADDQ.W #1,D7; LSL.W #8,D7; LSL.W #4,D7; MOVE.W D7,2ffff2.l; MOVE.W #0,2ffff0.l; MOVEM.W (A7)+,D0/D7; MOVE.W (A7)+,D0;
    // MOVE.W D0,-3272(A5); MOVE.W D0,3c0000.l; MOVE.W 3c0006.l,D0; ANDI.B #8,D0; SNE -7ffe(A5); MOVEM.L (A7)+,D0-D7/A0-A6; RTE.
    case 0x248:{
        f6a_port(c,0x3c0004,2,0);r.a[5]=0x108000;
        if(!am_pop(c,2,value) || !f6a_put(c,r.a[5],0x8010,2,value))return false;
        if(!am_push(c,2,f6a_w(r.d[7])) || !am_push(c,2,f6a_w(r.d[0])))return false;
        if(!f6a_get(c,r.a[5],0x8010,2,value))return false;am_word(r.d[7],value);am_word(r.d[0],r.d[7]);
        am_word(r.d[7],r.d[7]+1U);am_word(r.d[7],f6a_w(r.d[7])<<12);
        if(!am_write(c,0x2ffff2,2,f6a_w(r.d[7])) || !am_write(c,0x2ffff0,2,0))return false;
        if(!am_pop(c,2,value))return false;r.d[0]=am_extend_word(value);if(!am_pop(c,2,value))return false;r.d[7]=am_extend_word(value);
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        if(!f6a_put(c,r.a[5],0xcd8e,2,r.d[0]))return false;f6a_port(c,F6A_VIDEO,2,r.d[0]);
        if(!am_read(c,0x3c0006,2,value))return false;am_word(r.d[0],value);am_byte(r.d[0],r.d[0]&8U);
        if(!f6a_put(c,r.a[5],0x8002,1,f6a_b(r.d[0])!=0U?0xffU:0U))return false;
        for(int i=0;i<8;++i) {if(!am_pop(c,4,value))return false;r.d[i]=value;}
        for(int i=0;i<7;++i) {if(!am_pop(c,4,value))return false;r.a[i]=value;}
        return f6a_rte(c);}
    // ---- raster IRQ 29c: TST.B 10fd80.l; BPL.B 2ce / MOVE.L A5,-(A7); LEA 108000.l,A5; MOVE.W -3272(A5),-(A7); MOVEA.L -7ff6(A5),A5;
    // JSR (A5).
    case 0x29c:if(!f6a_byte(c,F6A_BIOS_FLAGS,value))return false;r.pc=(value&0x80U)!=0U?0x2a4:0x2ce;return true;
    case 0x2a4:
        if(!am_push(c,4,r.a[5]))return false;r.a[5]=0x108000;
        if(!f6a_get(c,r.a[5],0xcd8e,2,value) || !am_push(c,2,value))return false;
        if(!f6a_get(c,r.a[5],0x800a,4,value))return false;r.a[5]=value;return am_call(c,r.a[5],0x2b6);
    // MOVE.W #2,3c000c.l; MOVE.W (A7),104d8e.l; MOVE.W (A7)+,3c0000.l; MOVEA.L (A7)+,A5; RTE.
    case 0x2b6:
        f6a_port(c,0x3c000c,2,2);if(!am_read(c,r.a[7],2,value) || !am_write(c,F6A_VRAM_COPY,2,value))return false;
        if(!am_pop(c,2,value))return false;f6a_port(c,F6A_VIDEO,2,value);if(!am_pop(c,4,value))return false;r.a[5]=value;
        return f6a_rte(c);
    case 0x2ce:f6a_port(c,0x3c000c,2,2);return f6a_rte(c);   // MOVE.W #2,3c000c.l; RTE.
    // ---- credit a2c: LEA 100004.l,A0; MOVEQ #1,D1; MOVE.B (A0)+,D2.
    case 0xa2c:r.a[0]=0x100004;r.d[1]=1;if(!am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;am_byte(r.d[2],value);r.pc=0xa36;return true;
    case 0xa36:r.pc=f6a_lsr_b(r)?0xa3c:0xa46;return true;                       // LSR.B #1,D0; BCC.W a46.
    case 0xa3c:set=f6a_b(r.d[2])==0U;am_byte(r.d[2],r.d[2]-1U);r.pc=set?0xa46:0xa42;return true; // SUBQ.B #1,D2; BCS.W a46.
    case 0xa42:am_byte(r.d[0],r.d[0]|2U);r.pc=0xa46;return true;                // ORI.B #2,D0.
    case 0xa46:if(!am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;am_byte(r.d[2],value);r.pc=f6a_dbra(r,0xa36,0xa4c);return true;
    // a4e: LEA 100004.l,A0; MOVEQ #1,D1 / LSR.W #1,D0; BCC.W a6c / MOVE.B (A0),D7; BEQ.W a6c.
    case 0xa4e:r.a[0]=0x100004;r.d[1]=1;r.pc=0xa56;return true;
    case 0xa56:r.pc=f6a_lsr_w(r)?0xa5c:0xa6c;return true;
    case 0xa5c:if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[7],value);r.pc=value==0U?0xa6c:0xa62;return true;
    // SUB.W D6,D6; MOVE.B #1,D6; SBCD D6,D7 (X = 0); MOVE.B D7,(A0).
    case 0xa62:am_word(r.d[6],0);am_byte(r.d[6],1);am_byte(r.d[7],f6a_sbcd_one(r.d[7]));if(!am_write(c,r.a[0],1,f6a_b(r.d[7])))return false;r.pc=0xa6c;return true;
    case 0xa6c:r.a[0]+=1U;r.pc=f6a_dbra(r,0xa56,0xa72);return true;            // ADDQ.W #1,A0; DBRA D1,a56.
    // ---- a74: MOVE.B 10fdaf.l,D0; CMPI.B #1,D0; BEQ.W a92 / CMPI.B #2,D0; BEQ.W abc / CLR.B 10fdb4.l; RTS.
    case 0xa74:if(!f6a_byte(c,0x10fdaf,value))return false;am_byte(r.d[0],value);r.pc=value==1U?0xa92:0xa82;return true;
    case 0xa82:r.pc=f6a_b(r.d[0])==2U?0xabc:0xa8a;return true;
    case 0xa8a:if(!am_write(c,0x10fdb4,1,0))return false;return am_return(c);
    case 0xa92:if(!f6a_byte(c,0x10fd82,value))return false;r.pc=value!=0U?0xabc:0xa9c;return true; // TST.B 10fd82.l; BNE.W abc.
    // MOVE.B 10fdb4.l,D0; AND.B 10f004.l,D0; BEQ.W aba / CLR.B 10fdb4.l; MOVE.B #2,10fdaf.l.
    case 0xa9c:
        if(!f6a_byte(c,0x10fdb4,value))return false;am_byte(r.d[0],value);if(!f6a_byte(c,0x10f004,value))return false;
        am_byte(r.d[0],r.d[0]&value);r.pc=f6a_b(r.d[0])==0U?0xaba:0xaac;return true;
    case 0xaac:case 0xaf4:
        if(r.pc==0xaacU && !am_write(c,0x10fdb4,1,0))return false;
        if(!am_write(c,0x10fdaf,1,2))return false;r.pc=r.pc==0xaacU?0xaba:0xafc;return true;
    // MOVE.B 10fdb4.l,D0; TST.B 10fd82.l; BNE.W ad0 / BSR.W a2c.
    case 0xabc:
        if(!f6a_byte(c,0x10fdb4,value))return false;am_byte(r.d[0],value);if(!f6a_byte(c,0x10fd82,value))return false;
        r.pc=value!=0U?0xad0:0xacc;return true;
    case 0xacc:return am_call(c,0xa2c,0xad0);
    // AND.B 10f004.l,D0; MOVE.B 10f006.l,D1; NOT.B D1; AND.B 10f007.l,D0; OR.B D0,10f006.l; MOVE.B D0,10fdb4.l; BEQ.W afc.
    case 0xad0:
        if(!f6a_byte(c,0x10f004,value))return false;am_byte(r.d[0],r.d[0]&value);
        if(!f6a_byte(c,0x10f006,value))return false;am_byte(r.d[1],value);am_byte(r.d[1],~r.d[1]);
        if(!f6a_byte(c,0x10f007,value))return false;am_byte(r.d[0],r.d[0]&value);
        if(!f6a_byte(c,0x10f006,value) || !am_write(c,0x10f006,1,f6a_b(value|r.d[0])))return false;
        if(!am_write(c,0x10fdb4,1,f6a_b(r.d[0])))return false;r.pc=f6a_b(r.d[0])==0U?0xafc:0xaf4;return true;
    case 0xafc:if(!f6a_byte(c,0x10fd82,value))return false;r.pc=value!=0U?0xb0a:0xb06;return true; // TST.B 10fd82.l; BNE.W b0a.
    case 0xb06:return am_call(c,0xa4e,0xb0a);
    // ---- credit request bbe: TST.B 10fd82.l; BEQ.W bca / MOVE.B 100014.l,D0; BEQ.W bec / OR.B D0,10fdb4.l; JSR a74(PC).
    case 0xbbe:if(!f6a_byte(c,0x10fd82,value))return false;r.pc=value==0U?0xbca:0xbc8;return true;
    case 0xbca:if(!f6a_byte(c,0x100014,value))return false;am_byte(r.d[0],value);r.pc=value==0U?0xbec:0xbd4;return true;
    case 0xbd4:if(!f6a_byte(c,0x10fdb4,value) || !am_write(c,0x10fdb4,1,f6a_b(value|r.d[0])))return false;return am_call(c,0xa74,0xbde);
    // MOVE.B 10fdb4.l,D0; NOT.B D0; AND.B D0,100014.l.
    case 0xbde:
        if(!f6a_byte(c,0x10fdb4,value))return false;am_byte(r.d[0],~value);
        if(!f6a_byte(c,0x100014,value) || !am_write(c,0x100014,1,f6a_b(value&r.d[0])))return false;r.pc=0xbec;return true;
    // ---- service c8c: BSET #7,-7fe7(A5); BEQ.W c98 / RTS (re-entry).
    case 0xc8c:if(!f6a_bit(c,am_index(r.a[5],0x8019),7,1,set))return false;r.pc=set?0xc96:0xc98;return true;
    // ADDQ.B #1,-7fea(A5); BCS.W caa / MOVE.B D0,300001.l (watchdog); BRA.W cb0 / MOVE.B #ff,-7fea(A5).
    case 0xc98:
        if(!f6a_get(c,r.a[5],0x8016,1,value) || !f6a_put(c,r.a[5],0x8016,1,value+1U))return false;r.pc=value==0xffU?0xcaa:0xca0;return true;
    case 0xca0:f6a_port(c,0x300001,1,r.d[0]);r.pc=0xcb0;return true;
    case 0xcaa:if(!f6a_put(c,r.a[5],0x8016,1,0xff))return false;r.pc=0xcb0;return true;
    case 0xcb0:return am_call(c,0xbbe,0xcb6);
    case 0xcb6:if(!f6a_get(c,r.a[5],0x801b,1,value))return false;r.pc=(value&0x80U)!=0U?0xcbe:0xd36;return true; // TST.B; BPL.W d36.
    case 0xcbe:return am_call(c,0x72fa,0xcc4);   // F6b palette transfer boundary.
    case 0xcc4:case 0xd36:
        if(!f6a_byte(c,0x10f001,value))return false;
        r.pc=(value&0x10U)!=0U?(r.pc==0xcc4U?0xcd0U:0xd42U):(r.pc==0xcc4U?0xcd6U:0xd48U);return true; // BTST #4,10f001.l; BEQ.W.
    case 0xcd0:f6a_port(c,0x3a0011,1,r.d[0]);r.pc=0xcd6;return true;
    case 0xcd6:return am_call(c,0x1adf8,0xcdc);
    case 0xcdc:return am_call(c,0x16cfa,0xce2);
    case 0xce2:if(!f6a_get(c,r.a[5],0x881c,4,value))return false;r.a[6]=value;r.pc=0xce6;return true; // MOVEA.L -77e4(A5),A6.
    case 0xce6:r.pc=r.a[6]>=F6A_TASK_END?0xd36:0xcf0;return true;              // CMPA.L #10081c,A6; BCC.W d36.
    // Task restore (E9): MOVE.B D0,300001.l; MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.l; MOVE.W #0,2ffff0.l;
    // MOVEM.L (A6)+,D0-D7/A0-A5; LEA 8(A6),A6; MOVE.L A6,-77e4(A5) (restored A5); MOVE.L #d2a,-(A7); MOVE.L -(A6),-(A7);
    // MOVEA.L -(A6),A6; LEA 108000.l,A5; RTS (the task PC is left to the routing).
    case 0xcf0:
        f6a_port(c,0x300001,1,r.d[0]);if(!am_zero_bank(c))return false;
        for(int i=0;i<8;++i) {if(!am_read(c,r.a[6],4,value))return false;r.a[6]+=4U;r.d[i]=value;}
        for(int i=0;i<6;++i) {if(!am_read(c,r.a[6],4,value))return false;r.a[6]+=4U;r.a[i]=value;}
        r.a[6]+=8U;if(!f6a_put(c,r.a[5],0x881c,4,r.a[6]) || !am_push(c,4,0xd2a))return false;
        r.a[6]-=4U;if(!am_read(c,r.a[6],4,value) || !am_push(c,4,value))return false;
        r.a[6]-=4U;if(!am_read(c,r.a[6],4,value))return false;r.a[6]=value;r.a[5]=0x108000;return am_return(c);
    case 0xd2a:r.a[5]=0x108000;if(!f6a_get(c,r.a[5],0x881c,4,value))return false;r.a[6]=value;r.pc=0xce6;return true;
    case 0xd42:f6a_port(c,0x3a0001,1,r.d[0]);r.pc=0xd48;return true;
    case 0xd48:return am_call(c,0x3cac,0xd4e);
    case 0xd4e:if(!f6a_put(c,r.a[5],0x8019,1,0))return false;return am_return(c);
    // ---- sound/Z80 3cac: JSR 48156.l / MOVE.B 320000.l,D0 (E7 external read); MOVE.B D0,-3284(A5); BCLR #7,-3285(A5); BEQ.W 3cd6.
    case 0x3cac:return am_call(c,0x48156,0x3cb2);
    case 0x3cb2:
        if(!am_read(c,0x320000,1,value))return false;am_byte(r.d[0],value);if(!f6a_put(c,r.a[5],0xcd7c,1,value))return false;
        if(!f6a_bit(c,am_index(r.a[5],0xcd7b),7,-1,set))return false;r.pc=set?0x3cc6:0x3cd6;return true;
    // MOVE.B #ff,-3286(A5); MOVE.B #3 / #7f,320000.l; RTS.
    case 0x3cc6:case 0x3cea:
        if(!f6a_put(c,r.a[5],0xcd7a,1,0xff))return false;f6a_port(c,0x320000,1,r.pc==0x3cc6U?3U:0x7fU);return am_return(c);
    case 0x3cd6:r.pc=f6a_b(r.d[0])!=1U?0x3ce0:0x3cde;return true;               // CMPI.B #1,D0; BNE.W 3ce0.
    case 0x3ce0:if(!f6a_bit(c,am_index(r.a[5],0x7003),7,-1,set))return false;r.pc=set?0x3cea:0x3cfa;return true; // BCLR #7,7003(A5).
    // MOVE.W -328c(A5),D1; CMP.W -328a(A5),D1; BNE.W 3d08.
    case 0x3cfa:
        if(!f6a_get(c,r.a[5],0xcd74,2,value))return false;am_word(r.d[1],value);if(!f6a_get(c,r.a[5],0xcd76,2,value))return false;
        r.pc=f6a_w(r.d[1])!=value?0x3d08:0x3d06;return true;
    // LEA -330c(A5),A0; MOVE.B (A0,D1.W),D0; ADDQ.W #1,D1; ANDI.W #7f,D1.
    case 0x3d08:
        r.a[0]=am_index(r.a[5],0xccf4);if(!f6a_ring_byte(c,value))return false;am_byte(r.d[0],value);
        am_word(r.d[1],r.d[1]+1U);am_word(r.d[1],r.d[1]&0x7fU);r.pc=0x3d16;return true;
    case 0x3d16:if(!f6a_get(c,r.a[5],0xcd76,2,value))return false;r.pc=f6a_w(r.d[1])==value?0x3d2e:0x3d1e;return true; // CMP.W; BEQ.W.
    case 0x3d1e:if(!f6a_ring_byte(c,value))return false;r.pc=f6a_b(r.d[0])!=value?0x3d2e:0x3d26;return true; // CMP.B (A0,D1.W),D0; BNE.W.
    case 0x3d26:am_word(r.d[1],r.d[1]+1U);am_word(r.d[1],r.d[1]&0x7fU);r.pc=0x3d16;return true;
    case 0x3d2e:if(!f6a_put(c,r.a[5],0xcd74,2,r.d[1]))return false;f6a_port(c,0x320000,1,r.d[0]);return am_return(c);
    // ---- sound timer 48156: MOVE.W 568c(A5),D0; BEQ.W 4817e / CMPI.W #f,D0; BLE.W 48170 / MOVEQ #0,D0; MOVE.W D0,568c(A5); BRA.W 48174 /
    // ADDQ.W #1,568c(A5) / ADDI.W #19c0,D0; JSR 3af8.l.
    case 0x48156:if(!f6a_get(c,r.a[5],0x568c,2,value))return false;am_word(r.d[0],value);r.pc=value==0U?0x4817e:0x4815e;return true;
    case 0x4815e:r.pc=f6a_sw(r.d[0])<=0xf?0x48170:0x48166;return true;
    case 0x48166:r.d[0]=0;if(!f6a_put(c,r.a[5],0x568c,2,0))return false;r.pc=0x48174;return true;
    case 0x48170:if(!f6a_get(c,r.a[5],0x568c,2,value) || !f6a_put(c,r.a[5],0x568c,2,value+1U))return false;r.pc=0x48174;return true;
    case 0x48174:am_word(r.d[0],r.d[0]+0x19c0U);return am_call(c,0x3af8,0x4817e);
    // ---- column control 1adf8: MOVE.W #1,-7ff0(A5); MOVE.W #2000,2ffff2.l; MOVE.W #0,2ffff0.l; LEA 109156.l,A0; JSR 187d8.l.
    case 0x1adf8:
        if(!f6a_put(c,r.a[5],0x8010,2,1) || !am_write(c,0x2ffff2,2,0x2000) || !am_write(c,0x2ffff0,2,0))return false;
        r.a[0]=0x109156;return am_call(c,0x187d8,0x1ae1a);
    case 0x1ae1a:r.a[0]=0x10b1d6;return am_call(c,0x187d8,0x1ae26);
    case 0x1ae26:r.a[0]=0x10d256;return am_call(c,0x187d8,0x1ae32);
    case 0x1ae32:r.a[0]=0x10d2d6;return am_call(c,0x187d8,0x1ae3e);
    case 0x1ae3e:if(!am_zero_bank(c))return false;return am_return(c);
    // ---- column refresh 187d8: BTST #0,7a(A0); BEQ.W 18be6 / BCLR #7,7a(A0); BEQ.W 18be6 / MOVE.W 26(A0),D7; BMI.W 18be6.
    case 0x187d8:if(!f6a_get(c,r.a[0],0x7a,1,value))return false;r.pc=(value&1U)==0U?0x18be6:0x187e2;return true;
    case 0x187e2:if(!f6a_bit(c,am_index(r.a[0],0x7a),7,-1,set))return false;r.pc=set?0x187ec:0x18be6;return true;
    case 0x187ec:if(!f6a_get(c,r.a[0],0x26,2,value))return false;am_word(r.d[7],value);r.pc=(value&0x8000U)!=0U?0x18be6:0x187f4;return true;
    // MOVE.W D7,D6; ADDI.W #8401,D6; ADDI.W #8201,D7; SWAP D7; SWAP D6; MOVE.W 7c(A0),D6; LSL.W #7,D6; MOVE.W 7e(A0),D0; LSL.W #7,D0;
    // LEA 3a(A0),A1; MOVE.L #10000,D5; MOVE.W #800,D4; MOVE.W #a000,D3; LEA 3c0000.l,A4; then the cell 0 prefix and BLS.W 18836.
    case 0x187f4:
        am_word(r.d[6],r.d[7]);am_word(r.d[6],r.d[6]+0x8401U);am_word(r.d[7],r.d[7]+0x8201U);am_swap(r.d[7]);am_swap(r.d[6]);
        if(!f6a_get(c,r.a[0],0x7c,2,value))return false;am_word(r.d[6],value<<7);
        if(!f6a_get(c,r.a[0],0x7e,2,value))return false;am_word(r.d[0],value<<7);
        r.a[1]=am_index(r.a[0],0x3a);r.d[5]=0x10000;am_word(r.d[4],0x800);am_word(r.d[3],0xa000);r.a[4]=F6A_VIDEO;
        if(!f6a_cell_prefix(c,set))return false;r.pc=set?0x18836:0x18834;return true;
    // ---- clear runs: 16092 ADDI.W #8201,D0; SWAP D0; MOVE.W #8000,D0; MOVEQ #1,D2; SWAP D2; NEG.W D1; ADD.W D1,D1 (twice);
    // LEA 1669e(PC),A1; JMP (A1,D1.W) / 166a0 ADDI.W #8200,D0; SWAP D0; MOVE.W #8000,D0; MOVE.L #ffff0000,D2; ADD.W D1,D1 (twice); JMP.
    case 0x16092:
        am_word(r.d[0],r.d[0]+0x8201U);am_swap(r.d[0]);am_word(r.d[0],0x8000);r.d[2]=0x10000;am_word(r.d[1],0U-r.d[1]);f6a_run_jump(r);return true;
    case 0x166a0:am_word(r.d[0],r.d[0]+0x8200U);am_swap(r.d[0]);am_word(r.d[0],0x8000);r.d[2]=0xffff0000U;f6a_run_jump(r);return true;
    // ---- sprite flush driver 16cfa: LEA 108000.l,A5; BCLR #7,d3d(A5); BEQ.W 16e9e.
    case 0x16cfa:r.a[5]=0x108000;if(!f6a_bit(c,am_index(r.a[5],0xd3d),7,-1,set))return false;r.pc=set?0x16d0a:0x16e9e;return true;
    // MOVE.W d34(A5),D0; MOVE.W d36(A5),D1; LEA b34(A5),A0; MOVEA.L A0,A1; ADDA.W D0,A0; ADDA.W D1,A1; BCHG #7,d3c(A5); BEQ.W 16dde.
    case 0x16d0a:
        if(!f6a_get(c,r.a[5],0xd34,2,value))return false;am_word(r.d[0],value);if(!f6a_get(c,r.a[5],0xd36,2,value))return false;am_word(r.d[1],value);
        r.a[0]=am_index(r.a[5],0xb34);r.a[1]=r.a[0];r.a[0]=am_index(r.a[0],r.d[0]);r.a[1]=am_index(r.a[1],r.d[1]);
        if(!f6a_bit(c,am_index(r.a[5],0xd3c),7,0,set))return false;r.pc=set?0x16d26:0x16dde;return true;
    // MOVE.L A6,-(A7); LEA 3c0000.l,A6; then the d3e/d46 copies (forward: (A4) to 4(A4); backward: 2(A4) to 6(A4)).
    case 0x16d26:case 0x16dde:
        if(!am_push(c,4,r.a[6]))return false;r.a[6]=F6A_VIDEO;
        if(r.pc==0x16d26U) {if(!f6a_copy_pair(c,0,4))return false;r.pc=0x16d3e;}
        else {if(!f6a_copy_pair(c,2,6))return false;r.pc=0x16dfa;}
        return true;
    case 0x16d3e:r.pc=r.a[1]==r.a[0]?0x16d86:0x16d44;return true;              // CMPA.L A0,A1; BEQ.W 16d86.
    // LEA -cc(A5),A2; ADDA.W (A0)+,A2; CMPA.L #108d34,A0; BNE.B 16d56 / LEA b34(A5),A0.
    case 0x16d44:
        r.a[2]=am_index(r.a[5],0xff34);if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;r.a[2]=am_index(r.a[2],value);
        r.pc=r.a[0]!=0x108d34U?0x16d56:0x16d52;return true;
    case 0x16d52:r.a[0]=am_index(r.a[5],0xb34);r.pc=0x16d56;return true;
    case 0x16d56:return f6a_slot(c,0x16d6a,0x16d66);
    case 0x16d66:case 0x16e22:r.a[4]=am_index(r.a[5],0xd46);r.pc+=4U;return true; // LEA d46(A5),A4.
    case 0x16d6a:return f6a_writer_call(c,0xf226,0x16d84);                      // F6c writer family A boundary (live target).
    case 0x16d84:r.pc=0x16d3e;return true;
    case 0x16d86:return f6a_pair(c,0xd3e,true,0x16d9a,0x16d98);
    case 0x16da4:return f6a_pair(c,0xd46,true,0x16db8,0x16db6);
    case 0x16e42:return f6a_pair(c,0xd3e,false,0x16e56,0x16e54);
    case 0x16e5e:return f6a_pair(c,0xd46,false,0x16e72,0x16e70);
    case 0x16d98:case 0x16db6:case 0x16e54:case 0x16e70:am_word(r.d[0],r.d[1]);r.pc+=2U;return true; // MOVE.W D1,D0.
    case 0x16d9a:return f6a_span(c,2,0x16092,0x16da4);
    case 0x16db8:return f6a_span(c,2,0x16092,0x16dc2);
    case 0x16e56:return f6a_span(c,0,0x166a0,0x16e5e);
    case 0x16e72:return f6a_span(c,0,0x166a0,0x16e7a);
    // MOVEA.L (A7)+,A6; MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.l; MOVE.W #0,2ffff0.l; BRA.W 16e92 (16dc2) / fall through (16e7a).
    case 0x16dc2:case 0x16e7a:if(!am_pop(c,4,value))return false;r.a[6]=value;if(!am_zero_bank(c))return false;r.pc=0x16e92;return true;
    case 0x16dfa:r.pc=r.a[1]==r.a[0]?0x16e42:0x16e00;return true;              // CMPA.L A0,A1; BEQ.W 16e42.
    case 0x16e00:r.a[2]=am_index(r.a[5],0xff34);r.pc=r.a[1]!=0x108b34U?0x16e10:0x16e0c;return true; // LEA -cc(A5),A2; CMPA.L #108b34,A1.
    case 0x16e0c:r.a[1]=am_index(r.a[5],0xd34);r.pc=0x16e10;return true;
    case 0x16e10:r.a[1]-=2U;if(!am_read(c,r.a[1],2,value))return false;r.a[2]=am_index(r.a[2],value);return f6a_slot(c,0x16e26,0x16e22);
    case 0x16e26:return f6a_writer_call(c,0x13b46,0x16e40);                     // F6c writer family B boundary (live target).
    case 0x16e40:r.pc=0x16dfa;return true;
    // MOVE.W d36(A5),d34(A5); ORI #1,CCR; RTS / ANDI #fe,CCR; RTS.
    case 0x16e92:
        if(!f6a_get(c,r.a[5],0xd36,2,value) || !f6a_put(c,r.a[5],0xd34,2,value))return false;r.carry=AnimationCarrySet;return am_return(c);
    case 0x16e9e:r.carry=AnimationCarryClear;return am_return(c);
    default:return am_error(c,"unsupported animation irq f6a PC");
    }
}
}
