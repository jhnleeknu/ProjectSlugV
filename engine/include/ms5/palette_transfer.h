#ifndef MS5_PALETTE_TRANSFER_H
#define MS5_PALETTE_TRANSFER_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Normal transfer path at 68000 CPU 0x0072fa. RAM is an exact 65536-byte
// image based at CPU 0x100000; palette0 is logical palette bank 0 and must
// contain exactly 8192 bytes. A nonzero big-endian word at RAM 0x7dea
// selects an unsupported special-fill path and fails without changes.
// Clear pending bit 7 at 0x7ded. If it was set, mask the first staging word
// at 0x5da2 with 0x8000, then upload dirty 32-byte blocks to palette bank 0.
// This mask discards the first slot's color-zero low bits even if clean.
// Finally select display bank 1 if RAM byte 0x7dec is nonzero, else bank 0.
// MMIO write timing and the intermediate bank-0 selection are not modeled.
// Failure preserves RAM, palette0 and display_bank; success clears error.
bool transfer_palette_frame(std::vector<std::uint8_t>& ram,
                            std::vector<std::uint8_t>& palette0,
                            std::uint8_t& display_bank,
                            std::string& error);

} // namespace ms5

#endif
