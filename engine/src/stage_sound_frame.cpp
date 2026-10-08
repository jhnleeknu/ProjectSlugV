#include "ms5/stage_sound_frame.h"
#include "ms5/sound_word_execution.h"
#include "ms5/sound_cancel_execution.h"
#include <new>
namespace ms5 {
namespace {
bool run(std::vector<std::uint8_t>& ram, StageSoundFrameState& state,
    std::uint8_t external_status, std::uint8_t& reads, std::string& error) {
    const bool fresh = state.kind == 0 && state.phase == 0 && !state.byte.waiting;
    const bool word_resume = state.kind == 1 && state.phase >= 1 && state.phase <= 2 &&
        state.saved <= 255 && state.byte.waiting;
    const bool cancel_resume = state.kind == 2 && state.phase >= 1 && state.phase <= 3 && state.byte.waiting;
    if (!fresh && !word_resume && !cancel_resume) {
        error = "invalid stage sound frame continuation"; return false;
    }
    if (fresh) {
        SceneMapTransferState& s = state.byte.registers;
        const std::uint8_t previous = ram[0xd491];
        const std::uint8_t current = ram[0xd490] != 0 ? 255 : 0;
        s.d[1] = (s.d[1] & 0xffffff00U) | previous;
        s.d[0] = (s.d[0] & 0xffffff00U) | current;
        ram[0xd491] = current;
        state.saved = 0;
        if (current != 0 && previous == 0) state.kind = 1;
        else if (current == 0 && previous != 0) state.kind = 2;
        else return true;
        s.d[0] = (s.d[0] & 0xffff0000U) | 0x1d28U;
    }
    if (state.kind == 1) {
        SoundWordExecutionState helper;
        helper.byte = state.byte;
        helper.saved_low = static_cast<std::uint8_t>(state.saved);
        helper.phase = state.phase;
        if (!execute_sound_word(ram, helper, external_status, reads, error)) return false;
        state.byte = helper.byte; state.saved = helper.saved_low; state.phase = helper.phase;
    } else {
        SoundCancelExecutionState helper;
        helper.byte = state.byte; helper.saved_word = state.saved; helper.phase = state.phase;
        if (!execute_sound_cancel(ram, helper, error)) return false;
        state.byte = helper.byte; state.saved = helper.saved_word; state.phase = helper.phase;
    }
    if (!state.byte.waiting) { state.kind = 0; state.phase = 0; state.saved = 0; }
    return true;
}
}
bool step_stage_sound_frame(std::vector<std::uint8_t>& ram,
    StageSoundFrameState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::string& error) {
    if (ram.size() != 65536) { error = "stage sound frame requires64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram;
        StageSoundFrameState next = state;
        std::uint8_t reads = 0;
        if (!run(candidate, next, external_status, reads, error)) return false;
        ram.swap(candidate); state = next; external_reads = reads; error.clear(); return true;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate stage sound frame transaction"; return false;
    }
}
}
