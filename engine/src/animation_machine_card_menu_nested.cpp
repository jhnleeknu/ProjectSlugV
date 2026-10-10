#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// MOVE.L A2,-ee(A5); MOVE.B 7(A2),8(A2); MOVE.W #d0,D0 (high WORD kept).
bool nested_select(AnimationMachineContext& c,std::uint32_t d0) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_write(c,am_index(r.a[5],0xff12),4,r.a[2]) || !am_read(c,r.a[2]+7U,1,value) ||
       !am_write(c,r.a[2]+8U,1,value))return false;
    am_word(r.d[0],d0);return true;
}
// MOVEA.L -ee(A5),A2.
bool nested_frame(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!am_read(c,am_index(c.s.a[5],0xff12),4,value))return false;c.s.a[2]=value;return true;
}
}
// Nested menu return a698 (close unit a690 BCS: -f2 still below 107f0e after the pop): -e5=0,
// the parent cursor item callback with D0=7 (9b3e), then, while -f2 still equals the parent frame,
// the same callback with D0=0; a6da redraws every frame from the oldest 107efe down to the pushed A2
// (9b58 box then 9e1a rows with A1=a008). a6da is also reached from a3b4 (open unit a370 frame).
bool animation_card_menu_nested_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // MOVE.B #0,-e5(A5); MOVE.L A2,-ee(A5); MOVE.B 7(A2),8(A2); MOVE.W #7,D0; MOVE.L A2,-(A7); JSR 9b3e.
    case 0xa698:
        if(!am_write(c,am_index(r.a[5],0xff1b),1,0) || !nested_select(c,7) || !am_push(c,4,r.a[2]))return false;
        return am_call(c,0x9b3e,0xa6b2);
    // MOVEA.L (A7)+,A2; CMPA.L -f2(A5),A2 (live LONG); BNE a6ce.
    case 0xa6b2:
        if(!am_pop(c,4,value))return false;r.a[2]=value;
        if(!am_read(c,am_index(r.a[5],0xff0e),4,value))return false;r.pc=r.a[2]!=value?0xa6ce:0xa6bc;return true;
    // MOVE.L A2,-ee(A5); MOVE.B 7(A2),8(A2); MOVE.W #0,D0; JSR 9b3e.
    case 0xa6bc:if(!nested_select(c,0))return false;return am_call(c,0x9b3e,0xa6ce);
    // MOVEA.L -ee(A5),A2; BSR a6da.
    case 0xa6ce:if(!nested_frame(c))return false;return am_call(c,0xa6da,0xa6d6);
    // MOVEQ #0,D0; RTS.
    case 0xa6d6:r.d[0]=0;return am_return(c);
    // MOVE.L A2,-(A7); MOVEA.L #107f0e,A2; SUBA.W #10,A2 (whole 32 bits); LEA a008,A1.
    case 0xa6da:
        if(!am_push(c,4,r.a[2]))return false;r.a[2]=0x107efeU;r.a[1]=0xa008;r.pc=0xa6ea;return true;
    // CMPA.L (A7),A2 (live LONG read of the stack); BCS a706 (unsigned A2 < pushed LONG).
    case 0xa6ea:
        if(!am_read(c,r.a[7],4,value))return false;r.pc=r.a[2]<value?0xa706:0xa6f0;return true;
    // MOVE.L A2,-ee(A5); BSR 9b58.
    case 0xa6f0:
        if(!am_write(c,am_index(r.a[5],0xff12),4,r.a[2]))return false;return am_call(c,0x9b58,0xa6f8);
    case 0xa6f8:return am_call(c,0x9e1a,0xa6fc);
    // MOVEA.L -ee(A5),A2; SUBA.W #10,A2; BRA a6ea.
    case 0xa6fc:if(!nested_frame(c))return false;r.a[2]-=0x10U;r.pc=0xa6ea;return true;
    // MOVEA.L (A7)+,A2; RTS.
    case 0xa706:if(!am_pop(c,4,value))return false;r.a[2]=value;return am_return(c);
    default:return am_error(c,"unsupported animation card menu nested PC");
    }
}
}
