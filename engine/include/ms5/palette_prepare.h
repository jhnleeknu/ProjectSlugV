#ifndef MS5_PALETTE_PREPARE_H
#define MS5_PALETTE_PREPARE_H

#include "ms5/palette_resource.h"

namespace ms5 {

// Normal preparation at 68000 CPU address 0x007196. RAM is a caller-owned
// 65536-byte image based at CPU 0x100000. Normal preparation supports equal
// palette IDs and interpolation of 15-bit source colors at weights 1..30.
// Weight 0 selects the first record; weights >=31 select the second record.
// Endpoints use hardware words directly and need only the selected record.
// Equal IDs select the first record regardless of weight. Active color effects
// without flag mask 2 are rejected. Effects use only the high bytes of the
// three effect words. Source words with bit 15 set reject interior blending.
// Records must have strictly ascending 16-bit IDs. Empty catalogs are valid
// when no node needs preparation. Hardware MMIO writes are not modeled.
// Failure preserves all RAM bytes and sets error; success clears error.
bool prepare_palettes(std::vector<std::uint8_t>& ram,
                      const std::vector<PaletteRecord>& records,
                      std::string& error);

} // namespace ms5

#endif
