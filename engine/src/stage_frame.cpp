#include "ms5/stage_frame.h"
#include "ms5/stage_input_loop.h"
#include "ms5/scene_frame.h"
#include "ms5/stage_region_frame.h"
#include "ms5/stage_spatial_frame.h"
#include "ms5/stage_cue_frame.h"
#include "ms5/stage_sound_frame.h"
#include <new>
namespace ms5 {
namespace {
bool valid(const StageFrameState& state) {
    if ((state.buffer.bank != 2 && state.buffer.bank != 3) || state.stage > 3) return false;
    if (state.cue_status < SpriteAccepted || state.cue_status > SpriteWaiting) return false;
    if (state.stage == 1) {
        if (state.buffer.phase != 1 && state.buffer.phase != 2) return false;
    } else if (state.buffer.phase != 0 || state.buffer.saved_a6 != 0 ||
        state.buffer.saved_slot_a4 != 0 || state.buffer.saved_slot_d7 != 0 ||
        state.buffer.saved_d0 != 0 || state.buffer.saved_d1 != 0 ||
        state.buffer.saved_d7 != 0 || state.buffer.saved_a0 != 0) return false;
    if (state.stage != 3) return state.sound_kind == 0 && state.sound_phase == 0 && state.sound_saved == 0;
    return (state.sound_kind == 1 && state.sound_phase >= 1 && state.sound_phase <= 2 && state.sound_saved <= 255) ||
        (state.sound_kind == 2 && state.sound_phase >= 1 && state.sound_phase <= 3);
}
bool run(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows, StageFrameState& state,
    std::uint8_t external_status, std::uint8_t& reads,
    std::vector<VideoPortWrite>& ports, std::string& error) {
    StageBufferFrameState& buffer = state.buffer;
    if (state.stage == 0) {
        if (!step_stage_input_loop(ram,0x47642,windows,buffer.registers,buffer.a6,error)) return false;
        std::vector<VideoPortWrite> scene_ports;
        if (!step_scene_frame(ram,tables,windows,buffer.registers,buffer.a6,scene_ports,error)) return false;
        ports.insert(ports.end(),scene_ports.begin(),scene_ports.end());
        buffer.bank = 2;
        if (!step_stage_input_loop(ram,0x49b0c,windows,buffer.registers,buffer.a6,error)) return false;
    }
    if (state.stage <= 1) {
        std::vector<VideoPortWrite> buffer_ports;
        if (!step_stage_buffer_frame(ram,windows,buffer,buffer_ports,error)) return false;
        ports.insert(ports.end(),buffer_ports.begin(),buffer_ports.end());
        if (buffer.phase != 0) { state.stage = 1; return true; }
        bool activity_carry = false;
        if (!step_stage_region_frame(ram,0xb4a2a,windows,buffer.registers,buffer.a6,buffer.bank,activity_carry,error)) return false;
        // Native6f1c2 is RTS; no state or memory effects.
        if (!step_stage_spatial_frame(ram,0x4701e,windows,buffer.registers,buffer.bank,error)) return false;
    }
    if (state.stage <= 2) {
        StageCueFrameState cue;
        cue.registers = buffer.registers; cue.waiting_for_sprite = state.stage == 2;
        if (!step_stage_cue_frame(ram,windows,cue,buffer.a6,state.cue_status,error)) return false;
        buffer.registers = cue.registers;
        if (cue.waiting_for_sprite) { state.stage = 2; return true; }
    }
    StageSoundFrameState sound;
    sound.byte.registers = buffer.registers; sound.byte.waiting = state.stage == 3;
    sound.kind = state.sound_kind; sound.phase = state.sound_phase; sound.saved = state.sound_saved;
    if (!step_stage_sound_frame(ram,sound,external_status,reads,error)) return false;
    buffer.registers = sound.byte.registers;
    state.sound_kind = sound.kind; state.sound_phase = sound.phase; state.sound_saved = sound.saved;
    state.stage = sound.byte.waiting ? 3 : 0;
    return true;
}
}
bool step_stage_frame(std::vector<std::uint8_t>& ram,
    const FixedDataResource& tables, const std::vector<FixedDataResource>& windows,
    StageFrameState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || !valid(state)) {
        error = "stage frame requires64KiB RAM, bank2/3 and valid continuation metadata"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; StageFrameState next = state;
        std::vector<VideoPortWrite> output; std::uint8_t reads = 0;
        if (!run(candidate,tables,windows,next,external_status,reads,output,error)) return false;
        ram.swap(candidate); state = next; ports.swap(output); external_reads = reads; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage frame transaction"; return false; }
}
}
