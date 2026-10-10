#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// MOVEA.L -ee(A5),A2.
bool input_frame(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!am_read(c,am_index(c.s.a[5],0xff12),4,value))return false;c.s.a[2]=value;return true;
}
// MOVE.L A2,-ee(A5).
bool input_save(AnimationMachineContext& c) {return am_write(c,am_index(c.s.a[5],0xff12),4,c.s.a[2]);}
// MOVE.B d(An),Dn: one live BYTE read, low BYTE replaced.
bool input_byte(AnimationMachineContext& c,std::uint32_t address,std::uint32_t& reg) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;am_byte(reg,value);return true;
}
// MOVEA.L (A7)+,A2.
bool input_pop_a2(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!am_pop(c,4,value))return false;c.s.a[2]=value;return true;
}
// BCLR/BSET #bit,f(A2): BYTE read-modify-write; Z (old bit clear) is returned.
bool input_bit(AnimationMachineContext& c,std::uint32_t bit,bool set,bool& was_clear) {
    std::uint32_t value=0;const std::uint32_t address=c.s.a[2]+0xfU;
    if(!am_read(c,address,1,value))return false;was_clear=(value&(1U<<bit))==0U;
    value=set?(value|(1U<<bit)):(value&~(1U<<bit));return am_write(c,address,1,value&255U);
}
// CMPI.B #ff,e(A2); BEQ.
bool input_pending(AnimationMachineContext& c,std::uint32_t empty_pc,std::uint32_t event_pc) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[2]+0xeU,1,value))return false;
    c.s.pc=value==0xffU?empty_pc:event_pc;return true;
}
// MOVE.L A2,-(A7); MOVEQ #0,D0; MOVE.B e(A2),D0; MOVE.B #ff,e(A2); BSR 9b3e.
bool input_event(AnimationMachineContext& c,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;if(!am_push(c,4,r.a[2]))return false;
    r.d[0]=0;if(!input_byte(c,r.a[2]+0xeU,r.d[0]) || !am_write(c,r.a[2]+0xeU,1,0xff))return false;
    return am_call(c,0x9b3e,return_pc);
}
// MOVEA.L (A7)+,A2; MOVE.L A2,-ee(A5); BRA.
bool input_event_return(AnimationMachineContext& c,std::uint32_t loop_pc) {
    if(!input_pop_a2(c) || !input_save(c))return false;c.s.pc=loop_pc;return true;
}
// SNE Dn: BYTE ff when the tested bit is set, 00 otherwise (high bytes kept).
void input_sne(std::uint32_t& reg,bool nonzero) {am_byte(reg,nonzero?0xffU:0U);}
// BTST #bit,D0; SNE D6; BTST #bit,D1; SNE D7; ANDI.B #1,D6; ANDI.B #2,D7; OR.B D6,D7; BEQ.
// BTST on a data register is LONG (bit mod 32); ANDI.B/OR.B change only the low BYTE.
void input_group(AnimationMachineContext& c,std::uint32_t bit,std::uint32_t hit_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    input_sne(r.d[6],(r.d[0]&(1U<<bit))!=0U);input_sne(r.d[7],(r.d[1]&(1U<<bit))!=0U);
    am_byte(r.d[6],r.d[6]&1U);am_byte(r.d[7],r.d[7]&2U);am_byte(r.d[7],(r.d[7]|r.d[6])&255U);
    r.pc=(r.d[7]&255U)?hit_pc:next_pc;
}
// MOVE.B D7,-e6(A5); BRA.
bool input_hit(AnimationMachineContext& c,std::uint32_t next_pc) {
    if(!am_write(c,am_index(c.s.a[5],0xff1a),1,c.s.d[7]&255U))return false;c.s.pc=next_pc;return true;
}
// MOVE.B #event,e(A2); BRA a5aa.
bool input_set_event(AnimationMachineContext& c,std::uint32_t event) {
    if(!am_write(c,c.s.a[2]+0xeU,1,event))return false;c.s.pc=0xa5aa;return true;
}
// MOVE.B 10fdb6/10fdb7.L,D1; CMPI.B #1,D1; BEQ.
bool input_card(AnimationMachineContext& c,std::uint32_t address,std::uint32_t one_pc,std::uint32_t other_pc) {
    if(!input_byte(c,address,c.s.d[1]))return false;c.s.pc=(c.s.d[1]&255U)==1U?one_pc:other_pc;return true;
}
// MOVEA.L -ee(A5),A2; MOVE.B D0,offset(A2); RTS.
bool input_store(AnimationMachineContext& c,std::uint32_t offset) {
    if(!input_frame(c) || !am_write(c,c.s.a[2]+offset,1,c.s.d[0]&255U))return false;return am_return(c);
}
}
// Card menu input frame a406 (entered from a3e2 with -e5=0): growth a412, redraw a424 (9e1a),
// descriptor frame hook a43e (JSR 6(desc)), pending event loops a44e/a5aa (9b3e), P1/P2 input
// groups a472..a562 (bits 0,1,2,3,5,4), cursor a566/a574 (a216), events a582..a5a0.
// c188 hook bf2c: 7e countdown -> 9ff4 (e=3), 80(A6) -> a70a, 10fdb6/10fdb7 -> 9fc4 (d).
// a70a: sound 1a5b (3af8) then a1ee (-e5=2, A2=-f2). a662 (close unit) and bd26 (save unit) run elsewhere;
// other hook targets are boundaries.
bool animation_card_menu_input_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;bool clear=false;
    switch(r.pc) {
    case 0x9fc4:return input_store(c,0xdU);
    case 0x9ff4:return input_store(c,0xeU);
    // MOVE.B #2,-e5(A5); MOVEA.L -f2(A5),A2; RTS.
    case 0xa1ee:
        if(!am_write(c,am_index(r.a[5],0xff1b),1,2) || !am_read(c,am_index(r.a[5],0xff0e),4,value))return false;
        r.a[2]=value;return am_return(c);
    // MOVE.B 4(A2),D0; CMP.B c(A2),D0; BCC a41a (unsigned D0.B >= c).
    case 0xa406:
        if(!input_byte(c,r.a[2]+4U,r.d[0]) || !am_read(c,r.a[2]+0xcU,1,value))return false;
        r.pc=(r.d[0]&255U)>=value?0xa41a:0xa412;return true;
    case 0xa412:return am_call(c,0xa348,0xa416);
    case 0xa416:case 0xa5ce:r.d[0]=0;return am_return(c);
    // BCLR #0,f(A2); BEQ a42c (old bit0 clear).
    case 0xa41a:if(!input_bit(c,0,false,clear))return false;r.pc=clear?0xa42c:0xa424;return true;
    // MOVE.L A2,-(A7); JSR 9e1a(PC).
    case 0xa424:if(!am_push(c,4,r.a[2]))return false;return am_call(c,0x9e1a,0xa42a);
    case 0xa42a:if(!input_pop_a2(c))return false;r.pc=0xa42c;return true;
    case 0xa442:if(!input_pop_a2(c))return false;r.pc=0xa444;return true;
    // MOVE.L A2,-ee(A5); MOVEA.L (A2),A3; MOVEA.L 6(A3),A3; CMPA.W #0,A3 (full 32-bit); BEQ a444.
    case 0xa42c:
        if(!input_save(c) || !am_read(c,r.a[2],4,value))return false;r.a[3]=value;
        if(!am_read(c,r.a[3]+6U,4,value))return false;r.a[3]=value;r.pc=r.a[3]?0xa43e:0xa444;return true;
    // MOVE.L A2,-(A7); JSR (A3): an odd target is a checked error, not an executed fetch.
    case 0xa43e:
        if(!am_push(c,4,r.a[2]))return false;
        if(r.a[3]&1U)return am_error(c,"animation card menu input odd jump target");
        return am_call(c,r.a[3],0xa442);
    // MOVE.L A2,-ee(A5); MOVE.B 7(A2),8(A2).
    case 0xa444:
        if(!input_save(c) || !am_read(c,r.a[2]+7U,1,value) || !am_write(c,r.a[2]+8U,1,value))return false;
        r.pc=0xa44e;return true;
    case 0xa44e:return input_pending(c,0xa472,0xa458);
    case 0xa458:return input_event(c,0xa46a);
    case 0xa46a:return input_event_return(c,0xa44e);
    case 0xa5aa:return input_pending(c,0xa5ce,0xa5b4);
    case 0xa5b4:return input_event(c,0xa5c6);
    case 0xa5c6:return input_event_return(c,0xa5aa);
    // MOVEQ #0,D0; MOVEQ #0,D1; MOVE.B D1,-e6(A5); BTST #0,d(A2); BEQ a488.
    case 0xa472:
        r.d[0]=0;r.d[1]=0;if(!am_write(c,am_index(r.a[5],0xff1a),1,0) || !am_read(c,r.a[2]+0xdU,1,value))return false;
        r.pc=(value&1U)?0xa484:0xa488;return true;
    case 0xa484:if(!input_byte(c,am_index(r.a[5],0xccba),r.d[0]))return false;r.pc=0xa488;return true;
    case 0xa488:if(!am_read(c,r.a[2]+0xdU,1,value))return false;r.pc=(value&2U)?0xa492:0xa496;return true;
    case 0xa492:if(!input_byte(c,am_index(r.a[5],0xccc0),r.d[1]))return false;r.pc=0xa496;return true;
    case 0xa496:input_group(c,0,0xa4b0,0xa4b8);return true;
    case 0xa4b8:input_group(c,1,0xa4d2,0xa4da);return true;
    case 0xa4da:input_group(c,2,0xa4f4,0xa4fc);return true;
    case 0xa4fc:input_group(c,3,0xa516,0xa51e);return true;
    case 0xa51e:input_group(c,5,0xa538,0xa540);return true;
    case 0xa540:input_group(c,4,0xa55a,0xa562);return true;
    case 0xa4b0:return input_hit(c,0xa566);
    case 0xa4d2:return input_hit(c,0xa574);
    case 0xa4f4:return input_hit(c,0xa596);
    case 0xa516:return input_hit(c,0xa5a0);
    case 0xa538:return input_hit(c,0xa58c);
    case 0xa55a:return input_hit(c,0xa582);
    case 0xa562:r.pc=0xa5ce;return true;
    // BSET #1,f(A2); BSR a216 (step backward) / BCLR #1,f(A2); BSR a216 (step forward).
    case 0xa566:if(!input_bit(c,1,true,clear))return false;return am_call(c,0xa216,0xa570);
    case 0xa574:if(!input_bit(c,1,false,clear))return false;return am_call(c,0xa216,0xa57e);
    case 0xa570:case 0xa57e:r.pc=0xa5aa;return true;
    case 0xa582:return input_set_event(c,3);
    case 0xa58c:return input_set_event(c,4);
    case 0xa596:return input_set_event(c,1);
    case 0xa5a0:return input_set_event(c,2);
    // MOVE.W #1a5b,D0; JSR 3af8; JMP a1ee.
    case 0xa70a:am_word(r.d[0],0x1a5b);return am_call(c,0x3af8,0xa714);
    case 0xa714:r.pc=0xa1ee;return true;
    // MOVE.W 7e(A6),D0; BEQ bf48.
    case 0xbf2c:
        if(!am_read(c,r.a[6]+0x7eU,2,value))return false;am_word(r.d[0],value);
        r.pc=(r.d[0]&65535U)?0xbf34:0xbf48;return true;
    // SUBQ.W #1,D0; MOVE.W D0,7e(A6); BNE bf48.
    case 0xbf34:
        am_word(r.d[0],r.d[0]-1U);if(!am_write(c,r.a[6]+0x7eU,2,r.d[0]&65535U))return false;
        r.pc=(r.d[0]&65535U)?0xbf48:0xbf3e;return true;
    case 0xbf3e:am_word(r.d[0],3);return am_call(c,0x9ff4,0xbf48);
    // TST.B 80(A6); BEQ bf5c.
    case 0xbf48:if(!am_read(c,r.a[6]+0x80U,1,value))return false;r.pc=value?0xbf50:0xbf5c;return true;
    case 0xbf50:return am_call(c,0xa70a,0xbf56);
    case 0xbf56:r.d[0]=0;r.pc=0xbf8e;return true;
    case 0xbf5c:r.d[0]=0;return input_card(c,0x10fdb6,0xbf72,0xbf6a);
    case 0xbf6a:r.pc=(r.d[1]&255U)!=3U?0xbf76:0xbf72;return true;
    case 0xbf72:am_word(r.d[0],r.d[0]|1U);r.pc=0xbf76;return true;
    case 0xbf76:return input_card(c,0x10fdb7,0xbf8a,0xbf82);
    case 0xbf82:r.pc=(r.d[1]&255U)!=3U?0xbf8e:0xbf8a;return true;
    case 0xbf8a:am_word(r.d[0],r.d[0]|2U);r.pc=0xbf8e;return true;
    case 0xbf8e:r.pc=0x9fc4;return true;
    default:return am_error(c,"unsupported animation card menu input PC");
    }
}
}
