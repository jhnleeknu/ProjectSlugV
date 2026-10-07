#ifndef MS5_MAIN_FRAME_H
#define MS5_MAIN_FRAME_H
#include "ms5/input_control.h"
namespace ms5 {
struct MainFrameState {
    std::uint32_t next_pc,object_address,d1,d3;
    MainFrameState() : next_pc(0xec4),object_address(0),d1(0),d3(0) {}
};
// Resume at ec4 (debug then gate), ef2 (gate only), f12 (input), or
// f4c (callback wait AFTER palette processing). A wait retains its own PC,
// so repeated polling never reruns debug or palette processing.
// Run at most one input/controller frame; ec4 output is the next frame.
// Callback f3c, BIOS c00444, TRAP fee and normal return0 are boundaries.
// The host supplies video/input samples and delivers IRQ RAM changes between
// calls. D1/D3 are full registers; other scratch registers/CCR and IRQ entry,
// external callbacks, physical timing and RTE are not represented here.
// All mutable outputs are committed together; any error preserves them.
bool step_main_frame(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& streams,const FixedDataResource& table,
                     const FixedDataResource& menu,const FixedDataResource& pause,
                     const FixedDataResource& debug,
                     const std::vector<PaletteRecord>& records,const InputPortSamples& ports,
                     std::uint16_t video,std::uint32_t entry_stack,
                     MainFrameState& state,InputFrameResult& result,
                     std::vector<VideoPortWrite>& writes,std::string& error,
                     const FixedDataResource* font = NULL,
                     const StageGroupMenuContext* stage_context = NULL);
}
#endif
