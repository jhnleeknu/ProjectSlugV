#ifndef MS5_ANIMATION_EXECUTION_H
#define MS5_ANIMATION_EXECUTION_H
#include "ms5/animation_resource.h"
#include "ms5/fixed_data_resource.h"
#include "ms5/sprite_submit_execution.h"
#include "ms5/video_port.h"
namespace ms5 {
struct AnimationExecutionState {
    SpriteSubmitExecutionState sprite;
    std::uint32_t a5, a6;
    unsigned int phase;
    std::uint32_t saved_a0, saved_a1;
    std::uint16_t saved_bank;
    AnimationExecutionState() : a5(0x108000), a6(0), phase(0),
        saved_a0(0), saved_a1(0), saved_bank(0) {}
};
// Full49fc6 register/PVC/pending execution for opcodes00/04/08/28, plus0c
// and14 selectors1d/1e with reached MS5D data windows. Other eleven opcodes,
// callback1f/other callbacks and banked scripts remain
// checked unsupported paths. Fixed MS5A windows are unique and complete;
// RAM script fetches use current RAM. Only reached sprite submit/resume
// requires A5=108000. phase1 resumes a direct04 draw without its prefix.
// Exact64KiB RAM and10000-command cap. Errors preserve RAM/state/carry/ports;
// successful waits commit effects, preserve incoming carry, and replace ports
// with this invocation's writes. Completed calls return the native carry.
bool step_animation_execution(std::vector<std::uint8_t>& ram,
    const std::vector<AnimationResource>& scripts, AnimationExecutionState& state,
    bool& carry, std::vector<VideoPortWrite>& ports, std::string& error);
bool step_animation_execution(std::vector<std::uint8_t>& ram,
    const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows, AnimationExecutionState& state,
    bool& carry, std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
