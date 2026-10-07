#ifndef MS5_FRAME_GATE_H
#define MS5_FRAME_GATE_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
// One observation of native ef2 waiting loop. If ready, consume the supplied
// 3c0006 word and update RAM18 before f12. Otherwise no video read/RAM change.
// Host scheduling supplies later interrupt state; this function never spins.
// Failure preserves RAM and ready; success sets ready and clears error.
bool poll_frame_gate(std::vector<std::uint8_t>& ram,std::uint16_t video,
                     bool& ready,std::string& error);
}
#endif
