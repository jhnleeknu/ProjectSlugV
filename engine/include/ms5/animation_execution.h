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
    std::uint32_t saved_list_end;
    std::uint32_t callback_saved_a0;
    unsigned int callback_sound_phase;
    std::uint8_t callback_saved_low;
    bool callback_waiting;
    AnimationExecutionState() : a5(0x108000), a6(0), phase(0),
        saved_a0(0), saved_a1(0), saved_bank(0), saved_list_end(0), callback_saved_a0(0),
        callback_sound_phase(0), callback_saved_low(0), callback_waiting(false) {}
};
// Full49fc6 register/PVC/pending execution for opcodes00/04/08/28, plus0c
// indexed10, field18/1c/20/24/34/38/2c and14 selectors03/1d/1e with reached
// MS5D data windows. 3c WORD selectors support actual targets3679e/2b3e8/2b3fa
// and47672 (external-input overload only). Remaining40 opcode,
// other callbacks and banked scripts remain
// checked unsupported paths. Fixed MS5A windows are unique and complete;
// RAM script fetches use current RAM. Only reached sprite submit/resume
// requires A5=108000. phase1 resumes a direct04 draw without its prefix.
// phase3 resumes indexed10 draw and retains its separate saved_list_end.
// The external-input overload also supports14/1f through47672; phase2
// retains its nested sound wait. It also supports30/phase4 direct sound,
// sharing callback sound metadata without a callback_saved_a0. The older
// overloads reject1f/30 and phases2/4.
// Only reached sound calls/resumes require canonical A5. external_reads
// reports this invocation and is preserved on failure.
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
bool step_animation_execution(std::vector<std::uint8_t>& ram,
    const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows, AnimationExecutionState& state,
    std::uint8_t external_status, std::uint32_t& external_reads,
    bool& carry, std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
