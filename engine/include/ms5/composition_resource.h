#ifndef MS5_COMPOSITION_RESOURCE_H
#define MS5_COMPOSITION_RESOURCE_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

struct CompositionResource {
    std::uint32_t id;
    std::uint32_t source_rom_offset;
    std::vector<std::uint8_t> data;
};

// MS5C v1 kind 1: one original BE normal rectangle; kind 2: 1..255
// original BE rectangles. Both retain the packed source ID and decrypted ROM
// file offset. Header fields are LE32; payload remains BE, with a count byte,
// zero byte, then dx/dy BE16, width/height bytes and attr/tile BE16 pairs
// for each rectangle (width 1..255, height 1..32).
// Validates bounds, CRC32 and every rectangle before replacing resource.
// Failure preserves all resource fields and reports error; success clears error.
bool load_composition_resource(const std::string& path,
                               CompositionResource& resource,
                               std::string& error);

} // namespace ms5

#endif
