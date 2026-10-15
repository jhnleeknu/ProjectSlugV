#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OC3_WAIT_COUNTER=0x216;  // -216(A5) = WORD 107dea (A5 = 108000), the boot wait counter (decremented only by IRQ c8c).
const std::uint32_t OC3_PALETTE_BUFFER=0x25e; // LEA -25e(A5),A4 = 107da2.
const std::uint32_t OC3_BANK_SOURCE=0x200004; // MOVEA.L 200004.l,A0 (bank window LONG, read after the bank 200000 select).
const std::uint32_t OC3_BANK_SECOND=0x200008; // MOVEA.L 200008.l,A3.
// d16 is a WORD displacement (sign extended), as in -216(A5).
std::uint32_t oc3_at(std::uint32_t base,std::uint32_t displacement) {return am_index(base,(0x10000U-displacement)&65535U);}
}
// Controller C3a (9 block starts): the boot head c52a / c530 / c55a and the boot wait callback c560 / c566 / c56c, with the boot fill
// helper 8b64 / 8b98 and the counter read 8bb6. Callees of other units: area_clear 9056 (c52a), H3 4718 (8b64 BSR). Boundary: c56e (C3b,
// the boot after the wait; no executor here). Ports: the PVC bank 200000 select (WORD 2ffff2 = 1000, WORD 2ffff0 = 0) in 8b64 and 8b98
// through the existing bank model. No known C is produced or consumed (the c566 TST.W / BEQ.W flag is used in the same block).
bool animation_controller_c3_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- boot head c52a: JSR 9056.l (area_clear).
    case 0xc52a:return am_call(c,0x9056,0xc530);
    // CLR.W 76/78/7a/7c/7e(A6); CLR.B 80/81/83(A6) (+82 and +84 kept); MOVE.W #0,D0; JSR 8b64.l.
    case 0xc530:{
        static const std::uint32_t words[5]={0x76,0x78,0x7a,0x7c,0x7e};
        static const std::uint32_t bytes[3]={0x80,0x81,0x83};
        for(unsigned int i=0;i<5;++i)if(!am_write(c,am_index(r.a[6],words[i]),2,0))return false;
        for(unsigned int i=0;i<3;++i)if(!am_write(c,am_index(r.a[6],bytes[i]),1,0))return false;
        am_word(r.d[0],0);return am_call(c,0x8b64,0xc55a);}
    // MOVE.L #c560,(A6) (callback install; execution falls into c560).
    case 0xc55a:if(!am_write(c,r.a[6],4,0xc560))return false;r.pc=0xc560;return true;
    // ---- boot wait c560: JSR 8bb6.l / TST.W D0; BEQ.W c56e / RTS.
    case 0xc560:return am_call(c,0x8bb6,0xc566);
    case 0xc566:r.pc=(r.d[0]&65535U)==0U?0xc56e:0xc56c;return true;
    case 0xc56c:return am_return(c);
    // ---- boot fill 8b64: MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.l; MOVE.W #0,2ffff0.l (bank 200000); MOVEA.L 200004.l,A0;
    // MOVEA.L 200008.l,A3; LEA -25e(A5),A4; ANDI.W #ffff,D0 (no change); LSL.L #5,D0; LEA (A0,D0.W),A0; BSR.W 4718.
    case 0x8b64:
        if(!am_zero_bank(c) || !am_read(c,OC3_BANK_SOURCE,4,value))return false;
        r.a[0]=value;
        if(!am_read(c,OC3_BANK_SECOND,4,value))return false;
        r.a[3]=value;r.a[4]=oc3_at(r.a[5],OC3_PALETTE_BUFFER);
        r.d[0]=(r.d[0]<<5)&0xffffffffU;r.a[0]=am_index(r.a[0],r.d[0]&65535U);return am_call(c,0x4718,0x8b98);
    // MOVE.W #2000,-216(A5); MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.l; MOVE.W #0,2ffff0.l; RTS.
    case 0x8b98:if(!am_write(c,oc3_at(r.a[5],OC3_WAIT_COUNTER),2,0x2000) || !am_zero_bank(c))return false;return am_return(c);
    // ---- counter read 8bb6: MOVE.W -216(A5),D0; RTS.
    case 0x8bb6:if(!am_read(c,oc3_at(r.a[5],OC3_WAIT_COUNTER),2,value))return false;am_word(r.d[0],value);return am_return(c);
    default:return am_error(c,"unsupported animation controller c3 PC");
    }
}
}
