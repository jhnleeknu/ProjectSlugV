#include "animation_machine_internal.h"
namespace ms5 {
// Objects F4 U06b (3 block starts): the U06 boundary callee e7562 (BSR from e7462/e7478/e7486 and the script handler of the
// e774e end entry through e74ac JSR (A0,D0.W)) and the shared leaf 48250 (BYTE 5681(A5) := D0.B; ROM callers 965a 308c0 d64b2
// d6b3c d6c98 e7566). No C consumer; no known C is produced (48250 MOVE.B clears C natively, no caller reads it).
bool animation_objects_u06b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- e7562: MOVE.L A0,-(A7); MOVEQ #1,D0; JSR 48250.L.
    case 0xe7562:if(!am_push(c,4,r.a[0]))return false;r.d[0]=1;return am_call(c,0x48250,0xe756c);
    // MOVEA.L (A7)+,A0; RTS.
    case 0xe756c:if(!am_pop(c,4,value))return false;r.a[0]=value;return am_return(c);
    // ---- 48250: MOVE.B D0,5681(A5); RTS.
    case 0x48250:if(!am_write(c,am_index(r.a[5],0x5681),1,r.d[0]&255U))return false;return am_return(c);
    default:return am_error(c,"unsupported animation objects u06b PC");
    }
}
}
