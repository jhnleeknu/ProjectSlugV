#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// F6b IRQ palette transfer 72fa..8b64 (contract docs/analysis/animation-machine-irq-f6b-contract.md, scope decision E6 as decided):
// head 72fa / 7302 / 730c, the 256 staging cells (7326 = cell 0 copy; cell k = 1..255: test s = 732e + 14*(k-1), copy s + 8), the tail
// 871a / 8720 / 8728 / 8732 / 8738 and the special fill 873a / 8b5c / 8b60. A5 = 108000 in the caller c8c; every RAM operand is A5
// relative as in the original. Palette RAM writes go through am_write (the E6 mirror when a palette device is attached, otherwise the
// existing "unsupported animation machine write device" checked error).
const std::uint32_t F6B_CELL_FIRST=0x732e;   // cell 1 test block; cell k test = F6B_CELL_FIRST + F6B_CELL_BYTES*(k-1)
const std::uint32_t F6B_CELL_BYTES=0x14;     // BCLR #7,d16(A0) (6) + BEQ.B (2) + MOVEM.L d16(A0),D0-D7 (6) + MOVEM.L D0-D7,d16(A1) (6)
const std::uint32_t F6B_TAIL=0x871a;         // MOVE.B D0,300001.l after cell 255
const std::uint32_t F6B_BLOCK=0x20;          // staging / palette block size (8 LONG)
const std::uint32_t F6B_BLOCKS=256;
const std::uint32_t F6B_PALETTE=0x400000;    // LEA 400000.l,A1 / A0
const std::uint32_t F6B_BANK0=0x3a000f;      // system latch: palette bank 0
const std::uint32_t F6B_BANK1=0x3a001f;      // system latch: palette bank 1
const std::uint32_t F6B_WATCHDOG=0x300001;
// One BYTE device port (D0.B, the original MOVE.B D0,abs.l).
void f6b_port(AnimationMachineContext& c,std::uint32_t address,std::uint32_t value) {
    VideoPortWrite port;port.address=address;port.size=1;port.value=value&255U;c.ports.push_back(port);
}
// MOVE.B D0,3a000f.l / 3a001f.l: an ordered port; with an attached palette device it also selects the bank (the address selects).
void f6b_select(AnimationMachineContext& c,std::uint32_t address) {
    f6b_port(c,address,c.s.d[0]);
    if(c.palette!=0)c.palette->selected=address==F6B_BANK1?1U:0U;
}
// BCLR #7,<address>: Z of the tested bit; set = bit 7 before the clear.
bool f6b_bclr7(AnimationMachineContext& c,std::uint32_t address,bool& set) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    set=(value&0x80U)!=0U;return am_write(c,address,1,value&0x7fU);
}
// MOVEM.L <address>,D0-D7 (no sign extension for LONG; no flags).
bool f6b_load(AnimationMachineContext& c,std::uint32_t address) {
    for(unsigned int i=0;i<8;++i)if(!am_read(c,address+4U*i,4,c.s.d[i]))return false;
    return true;
}
// MOVEM.L D0-D7,<address> (D0 at the lowest address). The -(A0) form stores the same 8 LONG below A0; only the final memory is
// modelled (contract decision 2: the bus order is not compared under E6 b).
bool f6b_store(AnimationMachineContext& c,std::uint32_t address) {
    for(unsigned int i=0;i<8;++i)if(!am_write(c,address+4U*i,4,c.s.d[i]))return false;
    return true;
}
// Cell k copy: MOVEM.L d(A0),D0-D7; MOVEM.L D0-D7,d(A1) with d = 20*k (positive d16 <= 1fe0).
bool f6b_copy(AnimationMachineContext& c,std::uint32_t k) {
    const std::uint32_t d=F6B_BLOCK*k;
    return f6b_load(c,c.s.a[0]+d) && f6b_store(c,c.s.a[1]+d);
}
}
bool animation_irq_f6b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool set=false;
    // ---- cells 1..255: test block s = 732e + 14*(k-1), copy block s + 8.
    if(r.pc>=F6B_CELL_FIRST && r.pc<F6B_TAIL) {
        const std::uint32_t offset=r.pc-F6B_CELL_FIRST,k=offset/F6B_CELL_BYTES+1U,part=offset%F6B_CELL_BYTES;
        const std::uint32_t next=r.pc-part+F6B_CELL_BYTES;
        if(part==0U) {
            if(!f6b_bclr7(c,r.a[0]+F6B_BLOCK*k,set))return false;
            r.pc=set?r.pc+8U:next;return true;
        }
        if(part!=8U)return am_error(c,"unsupported animation irq f6b PC");
        if(!f6b_copy(c,k))return false;
        r.pc=next;return true;
    }
    switch(r.pc) {
    // TST.W -216(A5); BNE.W 873a.
    case 0x72fa:if(!am_read(c,am_index(r.a[5],0xfdea),2,value))return false;r.pc=value!=0U?0x873a:0x7302;return true;
    // BCLR #7,-213(A5); BEQ.W 871a.
    case 0x7302:if(!f6b_bclr7(c,am_index(r.a[5],0xfded),set))return false;r.pc=set?0x730c:F6B_TAIL;return true;
    // MOVE.B D0,3a000f.l; LEA -225e(A5),A0; ANDI.W #8000,(A0); LEA 400000.l,A1; BCLR #7,(A0); BEQ.B 732e.
    case 0x730c:
        f6b_select(c,F6B_BANK0);r.a[0]=am_index(r.a[5],0xdda2);
        if(!am_read(c,r.a[0],2,value) || !am_write(c,r.a[0],2,value&0x8000U))return false;
        r.a[1]=F6B_PALETTE;if(!f6b_bclr7(c,r.a[0],set))return false;
        r.pc=set?0x7326:F6B_CELL_FIRST;return true;
    // Cell 0 copy: MOVEM.L (A0),D0-D7; MOVEM.L D0-D7,(A1).
    case 0x7326:if(!f6b_copy(c,0))return false;r.pc=F6B_CELL_FIRST;return true;
    // MOVE.B D0,300001.l (watchdog; D0 may be the last copied LONG, as in the original).
    case 0x871a:f6b_port(c,F6B_WATCHDOG,r.d[0]);r.pc=0x8720;return true;
    // TST.B -214(A5); BNE.W 8732.
    case 0x8720:if(!am_read(c,am_index(r.a[5],0xfdec),1,value))return false;r.pc=value!=0U?0x8732:0x8728;return true;
    // MOVE.B D0,3a000f.l; BRA.W 8738.
    case 0x8728:f6b_select(c,F6B_BANK0);r.pc=0x8738;return true;
    // MOVE.B D0,3a001f.l.
    case 0x8732:f6b_select(c,F6B_BANK1);r.pc=0x8738;return true;
    case 0x8738:return am_return(c);
    // Special fill: MOVE.B D0,3a001f.l; LEA 400000.l,A0; ADDA.W -216(A5),A0; LEA -25e(A5),A1; MOVEM.L (A1),D0-D7;
    // 256 x MOVEM.L D0-D7,-(A0); SUBI.W #2000,-216(A5); BNE.W 8b60.
    case 0x873a:
        f6b_select(c,F6B_BANK1);
        if(!am_read(c,am_index(r.a[5],0xfdea),2,value))return false;
        r.a[0]=am_index(F6B_PALETTE,value);r.a[1]=am_index(r.a[5],0xfda2);
        if(!f6b_load(c,r.a[1]))return false;
        for(std::uint32_t i=0;i<F6B_BLOCKS;++i) {r.a[0]-=F6B_BLOCK;if(!f6b_store(c,r.a[0]))return false;}
        if(!am_read(c,am_index(r.a[5],0xfdea),2,value))return false;
        value=(value-0x2000U)&0xffffU;if(!am_write(c,am_index(r.a[5],0xfdea),2,value))return false;
        r.pc=value!=0U?0x8b60:0x8b5c;return true;
    // MOVE.W #0,(A0).
    case 0x8b5c:if(!am_write(c,r.a[0],2,0))return false;r.pc=0x8b60;return true;
    // BRA.W 8720.
    case 0x8b60:r.pc=0x8720;return true;
    default:return am_error(c,"unsupported animation irq f6b PC");
    }
}
}
