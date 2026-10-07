#ifndef MS5_SOUND_PAIR_H
#define MS5_SOUND_PAIR_H
#include "ms5/sound_byte.h"
namespace ms5 {
struct SoundPairState {
    std::uint32_t entry, next_pc, d0, d1, d3;
    std::uint8_t phase, saved;
    SoundBytePending byte;
    SoundPairState() : entry(0x3d58), next_pc(0x3d58), d0(0), d1(0), d3(0), phase(0), saved(0) {}
};
// Native3d58/3d64 two-byte producers. Phase1/2 stop at3aea; phase3 ends at
// native3af6 RTS boundary, not caller return PC. Captured queue tail retained.
// Full D3 preserved. Errors preserve RAM and entire pending/register state.
bool enqueue_sound_pair(std::vector<std::uint8_t>& ram, SoundPairState& state,
                        std::string& error);
}
#endif
