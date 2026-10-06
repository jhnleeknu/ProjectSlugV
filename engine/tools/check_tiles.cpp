#include "ms5/tile_resource.h"

#include <iostream>

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: check_tiles RESOURCE.ms5t [RESOURCE.ms5t ...]\n";
        return 2;
    }
    bool failed = false;
    for (int argument = 1; argument < argc; ++argument) {
        ms5::TileResource resource;
        std::string error;
        if (!ms5::load_tile_resource(argv[argument], resource, error)) {
            std::cerr << argv[argument] << ": " << error << '\n';
            failed = true;
            continue;
        }
        std::uint64_t nonzero_pixels = 0;
        std::uint32_t nonzero_tiles = 0;
        const std::size_t area = static_cast<std::size_t>(resource.width) * resource.height;
        for (std::uint32_t tile = 0; tile < resource.count; ++tile) {
            bool has_pixels = false;
            for (std::size_t pixel = 0; pixel < area; ++pixel) {
                if (resource.pixels[static_cast<std::size_t>(tile) * area + pixel] != 0) {
                    ++nonzero_pixels;
                    has_pixels = true;
                }
            }
            if (has_pixels) {
                ++nonzero_tiles;
            }
        }
        std::cout << argv[argument] << ": kind=" << resource.kind
                  << " dimensions=" << resource.width << 'x' << resource.height
                  << " tiles=" << resource.count << " pixels=" << resource.pixels.size()
                  << " nonzero_tiles=" << nonzero_tiles
                  << " nonzero_pixels=" << nonzero_pixels << '\n';
    }
    return failed ? 1 : 0;
}
