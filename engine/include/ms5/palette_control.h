#ifndef MS5_PALETTE_CONTROL_H
#define MS5_PALETTE_CONTROL_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Effect setter at 68000 CPU 0x008c16. RAM is a caller-owned 65536-byte
// image based at CPU 0x100000; offsets below are RAM offsets. Raw channel
// words are interpreted as signed 16-bit values, clamped to -31..31, and
// stored as 8.8 targets at 0x7dc8/0x7dca/0x7dcc. Duration zero becomes one.
// Signed 16-bit target-minus-current deltas divide toward zero into steps
// at 0x7dce/0x7dd0/0x7dd2. All-zero deltas clear timer 0x7dd4 and preserve
// existing steps. Current words and palette dirty flags are not changed.
// Failure preserves RAM and sets error; success clears error.
bool set_palette_effect(std::vector<std::uint8_t>& ram,
                        std::uint16_t red, std::uint16_t green,
                        std::uint16_t blue, std::uint8_t duration,
                        std::string& error);

// Blend setter at 68000 CPU 0x008cda. Slot selects node 0x4d92 + slot*16.
// A zero reference word at node+8 is a no-op. Weight is capped at 32.
// A changed target at node+0xc stores target/weight and sets flag bit 7.
// A changed weight alone sets bit 7 only when target differs from node+0xa.
// List membership and all other node bytes are preserved.
// Failure preserves RAM and sets error; success clears error.
bool set_palette_blend(std::vector<std::uint8_t>& ram,
                       std::uint8_t slot, std::uint16_t target,
                       std::uint8_t weight, std::string& error);

} // namespace ms5

#endif
