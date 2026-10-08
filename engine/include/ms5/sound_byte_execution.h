#ifndef MS5_SOUND_BYTE_EXECUTION_H
#define MS5_SOUND_BYTE_EXECUTION_H
#include "ms5/scene_map_transfer.h"
namespace ms5 {
struct SoundByteExecutionState {
    SceneMapTransferState registers;
    bool waiting;
    SoundByteExecutionState() : waiting(false) {}
};
// Whole3ac8 or captured3aea continuation. Only live head is read on resume.
// A0 is the captured signed-WORD indexed write address; D1.low is masked next.
// Resume expects the captured address from this API, without 24-bit aliasing.
// Errors preserve RAM/registers/waiting. No logical ring-domain restriction.
bool execute_sound_byte(std::vector<std::uint8_t>& ram,
    SoundByteExecutionState& state, std::string& error);
}
#endif
