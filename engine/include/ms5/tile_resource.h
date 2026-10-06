#ifndef MS5_TILE_RESOURCE_H
#define MS5_TILE_RESOURCE_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Owns all indexed pixels in tile, row, column order. Index zero is transparent.
struct TileResource {
    std::uint32_t kind;
    std::uint32_t width;
    std::uint32_t height;
    std::uint32_t count;
    std::vector<std::uint8_t> pixels;

    TileResource() : kind(0), width(0), height(0), count(0) {}
};

// Failure leaves resource unchanged and sets error; success clears error.
bool load_tile_resource(const std::string& path, TileResource& resource,
                        std::string& error);
// Failure leaves pixel unchanged, including for an incomplete resource.
bool get_tile_pixel(const TileResource& resource, std::uint32_t tile,
                    std::uint32_t x, std::uint32_t y, std::uint8_t& pixel);

} // namespace ms5

#endif
