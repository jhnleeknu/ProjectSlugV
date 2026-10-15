#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OC3_WAIT_COUNTER=0x216;  // -216(A5) = WORD 107dea (A5 = 108000), the boot wait counter (decremented only by IRQ c8c).
const std::uint32_t OC3_PALETTE_BUFFER=0x25e; // LEA -25e(A5),A4 = 107da2.
const std::uint32_t OC3_BANK_SOURCE=0x200004; // MOVEA.L 200004.l,A0 (bank window LONG, read after the bank 200000 select).
const std::uint32_t OC3_BANK_SECOND=0x200008; // MOVEA.L 200008.l,A3.
const std::uint32_t OC3_BIOS_REQUEST=0x10fdaeU;   // BYTE 10fdae: BIOS request (0 / 1 = BIOS return, 3 = title, else demo).
const std::uint32_t OC3_BIOS_RETURN=0xc00444U;    // JMP c00444.l (the system return; the frame driver owns the checked terminal error).
const std::uint32_t OC3_ROM_WORD_180=0x180U;      // TST.W 180.l (canonical ROM WORD 0, live bus read).
const std::uint32_t OC3_DEMO_COUNT=150U;          // MOVE.W #96,76(A6): the demo intro frame count.
// d16 is a WORD displacement (sign extended), as in -216(A5).
std::uint32_t oc3_at(std::uint32_t base,std::uint32_t displacement) {return am_index(base,(0x10000U-displacement)&65535U);}
// d16(An) with a positive displacement, as in 702a(A5) 7dda(A5) 7d82(A5) and 62(A6).
std::uint32_t oc3_plus(std::uint32_t base,std::uint32_t displacement) {return am_index(base,displacement&65535U);}
// MOVEA.L #imm,A0; MOVE.W #0,D0; JSR 28ae.l (the child allocation calls of c5da c6de 4fb2c).
bool oc3_child(AnimationMachineContext& c,std::uint32_t child,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],0);return am_call(c,0x28ae,return_pc);
}
// MOVE.L #callback,(A6): the callback install, then execution continues at `next_pc`.
bool oc3_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// TST.B 62(A6) (the wait flag of the demo child): BEQ to `zero_pc`, else `other_pc`.
bool oc3_wait_flag(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!am_read(c,oc3_plus(c.s.a[6],0x62),1,value))return false;
    c.s.pc=value==0U?zero_pc:other_pc;return true;
}
}
// Controller C3 (C3a 9 + C3b 38 block starts). C3b is the boot after the wait (c56e..c64c), the title (c6da..c720) and the demo child
// allocation (4fb1a..4fb42); its blocks are reached by fixtures (the wait WORD 107dea reaches 0 only by IRQ c8c). Callees of other units
// are boundaries: C2 49a1a 47570 4823a 3162 c4cc, C1 36ba c654 c724 c73e, routed e7bf4 ca7e ca76 caf0 28ae 3902. The BIOS requests c598
// c5a6 end in JMP c00444 (no executor there; the frame driver reports the system return). Carry: 4fb3c (SCC.B after 28ae) is the only
// consumer and fails with a checked error when C is Unknown; no block produces a known C.
// C3a (9 block starts): the boot head c52a / c530 / c55a and the boot wait callback c560 / c566 / c56c, with the boot fill
// helper 8b64 / 8b98 and the counter read 8bb6. Callees of other units: area_clear 9056 (c52a), H3 4718 (8b64 BSR). Ports: the PVC bank 200000 select (WORD 2ffff2 = 1000, WORD 2ffff0 = 0) in 8b64 and 8b98
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
    // ---- C3b boot after the wait: JSR e7bf4.l / MOVEQ #0,D0; JSR 49a1a.l / MOVE.B #3,10f004.l; JSR 47570.l.
    case 0xc56e:return am_call(c,0xe7bf4,0xc574);
    case 0xc574:r.d[0]=0;return am_call(c,0x49a1a,0xc57c);
    case 0xc57c:if(!am_write(c,0x10f004,1,3))return false;return am_call(c,0x47570,0xc58a);
    // MOVE.B 10fdae.l,D0; CMPI.B #0,D0; BNE.W c59e (fall into the BIOS return c598).
    case 0xc58a:if(!am_read(c,OC3_BIOS_REQUEST,1,value))return false;am_byte(r.d[0],value);r.pc=(r.d[0]&255U)!=0U?0xc59e:0xc598;return true;
    case 0xc598:case 0xc5a6:r.pc=OC3_BIOS_RETURN;return true;
    case 0xc59e:r.pc=(r.d[0]&255U)!=1U?0xc5ac:0xc5a6;return true;
    // CMPI.B #3,D0; BEQ.W c6da (title); TST.W 180.l; BNE.W c610 (restart).
    case 0xc5ac:r.pc=(r.d[0]&255U)==3U?0xc6da:0xc5b4;return true;
    case 0xc5b4:if(!am_read(c,OC3_ROM_WORD_180,2,value))return false;r.pc=value!=0U?0xc610:0xc5be;return true;
    // ---- demo intro: JSR ca7e(PC) / JSR 4fb1a.l / MOVE.L #c5ce,(A6).
    case 0xc5be:return am_call(c,0xca7e,0xc5c2);
    case 0xc5c2:return am_call(c,0x4fb1a,0xc5c8);
    case 0xc5c8:return oc3_install(c,0xc5ce,0xc5ce);
    // c5ce: TST.B 62(A6); BEQ.W c73e (C1 wait tail), else JSR ca76(PC); the child de024; CLR.B 62(A6); MOVE.L #c5f4,(A6).
    case 0xc5ce:return oc3_wait_flag(c,0xc73e,0xc5d6);
    case 0xc5d6:return am_call(c,0xca76,0xc5da);
    case 0xc5da:return oc3_child(c,0xde024,0xc5ea);
    case 0xc5ea:if(!am_write(c,oc3_plus(r.a[6],0x62),1,0))return false;return oc3_install(c,0xc5f4,0xc5f4);
    // c5f4: TST.B 62(A6); BEQ.W c724, else MOVE.W #96,76(A6); MOVE.L #c608,(A6).
    case 0xc5f4:return oc3_wait_flag(c,0xc724,0xc5fc);
    case 0xc5fc:if(!am_write(c,oc3_plus(r.a[6],0x76),2,OC3_DEMO_COUNT))return false;return oc3_install(c,0xc608,0xc608);
    // c608: SUBQ.W #1,76(A6) (WORD wrap); BNE.W c724 (C1 wait tail), else fall into c610.
    case 0xc608:
        if(!am_read(c,oc3_plus(r.a[6],0x76),2,value))return false;value=(value-1U)&65535U;
        if(!am_write(c,oc3_plus(r.a[6],0x76),2,value))return false;r.pc=value!=0U?0xc724:0xc610;return true;
    // ---- restart c610: MOVE.W #1,702a(A5); MOVEQ #0,D0; JSR 49a1a.l / BSR.W c4cc / BSR.W caf0 / JSR 47570.l.
    case 0xc610:if(!am_write(c,oc3_plus(r.a[5],0x702a),2,1))return false;r.d[0]=0;return am_call(c,0x49a1a,0xc61e);
    case 0xc61e:return am_call(c,0xc4cc,0xc622);
    case 0xc622:return am_call(c,0xcaf0,0xc626);
    case 0xc626:return am_call(c,0x47570,0xc62c);
    // MOVE.W 702a(A5),D0; ANDI.W #1,D0; MOVE.W D0,702a(A5); ADDI.W #6,D0; JSR 4823a.l.
    case 0xc62c:
        if(!am_read(c,oc3_plus(r.a[5],0x702a),2,value))return false;value&=1U;
        if(!am_write(c,oc3_plus(r.a[5],0x702a),2,value))return false;
        am_word(r.d[0],(value+6U)&65535U);return am_call(c,0x4823a,0xc642);
    // MOVE.W 702a(A5),D0; JSR 3162.l; then MOVE.L #c654,(A6); RTS.
    case 0xc642:if(!am_read(c,oc3_plus(r.a[5],0x702a),2,value))return false;am_word(r.d[0],value);return am_call(c,0x3162,0xc64c);
    case 0xc64c:if(!am_write(c,r.a[6],4,0xc654))return false;return am_return(c);
    // ---- title (BIOS request 3): JSR ca76(PC) / the child de376 / MOVE.L #c6f4,(A6).
    case 0xc6da:return am_call(c,0xca76,0xc6de);
    case 0xc6de:return oc3_child(c,0xde376,0xc6ee);
    case 0xc6ee:return oc3_install(c,0xc6f4,0xc6f4);
    // MOVE.W #7257,D0; LEA c6ce(PC),A0 (the "TIME" string); JSR 3902.l.
    case 0xc6f4:am_word(r.d[0],0x7257);r.a[0]=0xc6ce;return am_call(c,0x3902,0xc702);
    // MOVE.W #7278,D0; LEA 7dda(A5),A0; MOVE.W #3,D1; MOVEQ #0,D3; MOVEQ #2,D4; JSR 36ba.l (C1).
    case 0xc702:
        am_word(r.d[0],0x7278);r.a[0]=oc3_plus(r.a[5],0x7dda);am_word(r.d[1],3);r.d[3]=0;r.d[4]=2;return am_call(c,0x36ba,0xc718);
    // TST.B 7dda(A5); BEQ.W c73e, else BRA.W c724.
    case 0xc718:
        if(!am_read(c,oc3_plus(r.a[5],0x7dda),1,value))return false;r.pc=value==0U?0xc73e:0xc720;return true;
    case 0xc720:r.pc=0xc724;return true;
    // ---- demo child allocation 4fb1a (called by c5c2): TST.B 7d82(A5); BEQ.W 4fb42; CMPI.B #1,-7fff(A5); BNE.W 4fb42.
    case 0x4fb1a:if(!am_read(c,oc3_plus(r.a[5],0x7d82),1,value))return false;r.pc=value==0U?0x4fb42:0x4fb22;return true;
    case 0x4fb22:if(!am_read(c,oc3_at(r.a[5],0x7fff),1,value))return false;r.pc=value!=1U?0x4fb42:0x4fb2c;return true;
    case 0x4fb2c:return oc3_child(c,0x4fb64,0x4fb3c);
    // SCC.B 62(A6) (C Clear -> ff, C Set -> 00; the C returned by 28ae); RTS.
    case 0x4fb3c:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"controller c3 caller requires known carry");
        if(!am_write(c,oc3_plus(r.a[6],0x62),1,r.carry==AnimationCarryClear?0xffU:0U))return false;return am_return(c);
    case 0x4fb42:if(!am_write(c,oc3_plus(r.a[6],0x62),1,0xff))return false;return am_return(c);
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
