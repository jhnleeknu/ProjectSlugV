#ifndef MS5_PALETTE_PREPARE_H
#define MS5_PALETTE_PREPARE_H

#include "ms5/palette_resource.h"

namespace ms5 {

// Normal preparation at 68000 CPU address 0x007196. RAM is a caller-owned
// 65536-byte image based at CPU 0x100000. Normal preparation supports equal
// palette IDs and interpolation of 15-bit source colors at weights 1..30.
// Weight 0 selects the first record; weights >=31 select the second record.
// Endpoints need only the selected record and use hardware words directly
// when effects are inactive or flag mask 2 bypasses effects. Equal IDs select
// the first record regardless of weight. Active effects use only RAM bytes
// 0x7dc2, 0x7dc4, 0x7dc6 for source bits 10..14, 5..9, 0..4 respectively.
// Each effect adds modulo 256, maps a set sign bit to 0, and otherwise clamps
// to 31. Effects follow interpolation; endpoint effects ignore source bit 15.
// Source words with bit 15 set reject interior blending.
// Records must have strictly ascending 16-bit IDs. Empty catalogs are valid
// when no node needs preparation. Hardware MMIO writes are not modeled.
// Optional d1 supplies/receives the native D1 value; upper 16 bits persist.
// Direct copy preserves D1; transforms leave their final color scratch value.
// Failure preserves d1 and all RAM bytes and sets error; success clears error.
bool prepare_palettes(std::vector<std::uint8_t>& ram,
                      const std::vector<PaletteRecord>& records,
                      std::string& error, std::uint32_t* d1 = NULL);

} // namespace ms5

#endif
