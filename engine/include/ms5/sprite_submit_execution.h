#ifndef MS5_SPRITE_SUBMIT_EXECUTION_H
#define MS5_SPRITE_SUBMIT_EXECUTION_H
#include "ms5/scene_map_transfer.h"
#include "ms5/sprite_producer.h"
namespace ms5 {
struct SpriteSubmitExecutionState {
    SceneMapTransferState registers;
    bool waiting;
    SpriteSubmitExecutionState() : waiting(false) {}
};
// Native cd58 with default RTS callback cd50. Waiting retains the cda4
// register snapshot and resumes only its live consumer comparison. Signed
// WORD indexed addresses may access any aligned complete64KiB RAM span.
// Clip/full return their native register changes; failure preserves RAM,
// registers, waiting and status. A6 is unused and all resources are RAM.
bool execute_sprite_submit(std::vector<std::uint8_t>& ram,
    SpriteSubmitExecutionState& state, SpriteSubmitStatus& status,
    std::string& error);
}
#endif
