#ifndef MS5_RANDOM_STATE_H
#define MS5_RANDOM_STATE_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
// Native 49a1a/49a58/49a84. RAM is the full 64 KiB at CPU100000.
// Seed fills 55 BE16 words at d6b4 and sets cursor d722 to CPU10d720.
// Nonzero D0.low16 selects f02c+1 modulo16 as seed and updates f02c.
// Next reads the old cursor word into D0.low16, advances/wraps the cursor,
// and subtracts that old word from the offset23 target word modulo16.
// Scale uses incoming D0.low16 as limit, multiplies the next word unsigned,
// then swaps the product's 16-bit halves. Full returned D0/D1 follow native
// instruction widths. Next/scale preserve D1 (not passed to these APIs).
// Failure preserves RAM/register outputs; success clears error. Invalid
// next/scale cursors (odd or outside CPU10d6b4..10d720) are rejected.
bool seed_random(std::vector<std::uint8_t>& ram, std::uint32_t& d0,
                 std::uint32_t& d1, std::string& error);
bool next_random(std::vector<std::uint8_t>& ram, std::uint32_t& d0,
                 std::string& error);
bool scale_random(std::vector<std::uint8_t>& ram, std::uint32_t& d0,
                  std::string& error);
}
#endif
