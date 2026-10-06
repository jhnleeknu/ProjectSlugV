#ifndef MS5_PALETTE_RESOURCE_H
#define MS5_PALETTE_RESOURCE_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Words retain the original 16-bit representation, not expanded RGB values.
struct PaletteRecord {
    std::uint32_t id;
    std::uint16_t source_words[16];
    std::uint16_t hardware_words[16];
};

// Owns the loaded records. Failure leaves records unchanged and sets error.
// Success clears error. Sparse source IDs are strictly ascending.
bool load_palette_resource(const std::string& path,
                           std::vector<PaletteRecord>& records,
                           std::string& error);

} // namespace ms5

#endif
