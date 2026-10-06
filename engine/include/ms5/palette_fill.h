#ifndef MS5_PALETTE_FILL_H
#define MS5_PALETTE_FILL_H

#include "ms5/palette_resource.h"

namespace ms5 {

// Fill setup at 68000 CPU address 0x008b64. RAM is a caller-owned 65536-byte
// image based at CPU 0x100000. The fill catalog must contain exactly 2048
// records with canonical IDs 0..2047, using context-correct hardware words.
// The selector aliases modulo 2048 after the original 16-bit multiplication
// by 32 and signed indexed address calculation. Copies hardware words 1..15
// to RAM 0x7da4..0x7dc1, preserving the first word at 0x7da2. Sets the fill
// count at 0x7dea to 0x2000 and clears the shadow word at 0x10. No MMIO is
// modeled. Failure preserves every RAM byte and sets error; success clears it.
bool setup_palette_fill(std::vector<std::uint8_t>& ram,
                        const std::vector<PaletteRecord>& fill_catalog,
                        std::uint16_t selector,
                        std::string& error);

} // namespace ms5

#endif
