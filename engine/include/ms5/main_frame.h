#ifndef MS5_MAIN_FRAME_H
#define MS5_MAIN_FRAME_H
#include "ms5/input_control.h"
#include "ms5/sound_word.h"
#include "ms5/sprite_prepare_queue.h"
namespace ms5 {
struct MainFrameState {
    std::uint32_t next_pc,object_address,d1,d3;
    SoundWordPending sound;
    SpritePreparePending sprite;
    MainFrameState() : next_pc(0xec4),object_address(0),d1(0),d3(0) {}
};
// Native e74 through ec4, including sound and sprite consumer waits. Resume
// only at e74, 3aea (captured sound byte), or 16bd0 (captured sprite cursor).
// Sound/sprite pending fields and full D1/D3 must be carried between calls.
// Video is sampled only after all preparation completes. Output PC is ec4 or
// the active wait; ordered CPU port writes are replaced on each call.
// Host consumer progress, other scratch registers/CCR and timing are external.
// Failure preserves RAM/state/writes, including failures after earlier stages.
bool prepare_main_frame(std::vector<std::uint8_t>& ram,
                        const std::vector<CompositionResource>& compositions,
                        const std::vector<PaletteRecord>& records,
                        std::uint16_t video, MainFrameState& state,
                        std::vector<VideoPortWrite>& writes, std::string& error);

// Resume at e74/3aea/16bd0 (preparation), ec4 (debug then gate),
// ef2 (gate only), f12 (input), or
// f4c (callback wait AFTER palette processing). A wait retains its own PC,
// so repeated polling never reruns debug or palette processing.
// Run at most one input/controller frame; ec4 output is the next frame.
// Callback f3c, BIOS c00444, TRAP fee and normal return0 are boundaries.
// The host supplies video/input samples and delivers IRQ RAM changes between
// calls. D1/D3 are full registers; other scratch registers/CCR and IRQ entry,
// external callbacks, physical timing and RTE are not represented here.
// Optional compositions supply preparation resources; NULL means empty.
// The supplied video value is used for each video read reached in this call.
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
                     const StageGroupMenuContext* stage_context = NULL,
                     const std::vector<CompositionResource>* compositions = NULL);
}
#endif
