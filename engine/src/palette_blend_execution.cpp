#include "ms5/palette_blend_execution.h"
#include "ms5/palette_control.h"
namespace ms5 {
bool execute_palette_blend(std::vector<std::uint8_t>& ram,
    ObjectRestartState& state, std::string& error) {
    if (ram.size()!=65536) { error="palette blend execution requires64KiB RAM"; return false; }
    const std::uint8_t slot=static_cast<std::uint8_t>(state.d[0]);
    const std::uint32_t offset=static_cast<std::uint32_t>(slot)*16U;
    const std::size_t node=0x4d92+offset;
    const bool referenced=ram[node+8]!=0 || ram[node+9]!=0;
    ObjectRestartState next=state;
    next.d[0]=(next.d[0]&0xffff0000U)|offset;
    next.a[1]=0x104d92; next.a[2]=next.a[1]+offset;
    if (referenced && (next.d[2]&255U)>=32) next.d[2]=32;
    // Size was validated above; the existing setter has no later error or
    // allocation path. Capture reference before it can update the node.
    if (!set_palette_blend(ram,slot,static_cast<std::uint16_t>(state.d[1]),
        static_cast<std::uint8_t>(state.d[2]),error)) return false;
    state=next; return true;
}
}
