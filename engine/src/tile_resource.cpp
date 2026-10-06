#include "ms5/tile_resource.h"

#include <fstream>
#include <limits>
#include <new>
#include <utility>

namespace ms5 {
namespace {

std::uint32_t read_u32(const unsigned char* bytes) {
    return static_cast<std::uint32_t>(bytes[0]) |
           (static_cast<std::uint32_t>(bytes[1]) << 8) |
           (static_cast<std::uint32_t>(bytes[2]) << 16) |
           (static_cast<std::uint32_t>(bytes[3]) << 24);
}

std::uint32_t pixel_crc32(const std::vector<std::uint8_t>& pixels) {
    std::uint32_t crc = UINT32_C(0xffffffff);
    for (std::size_t i = 0; i < pixels.size(); ++i) {
        crc ^= pixels[i];
        for (unsigned int bit = 0; bit < 8; ++bit) {
            if ((crc & 1U) != 0) {
                crc = (crc >> 1) ^ UINT32_C(0xedb88320);
            } else {
                crc >>= 1;
            }
        }
    }
    return crc ^ UINT32_C(0xffffffff);
}

bool fail(std::string& error, const char* message) {
    error = message;
    return false;
}

} // namespace

bool load_tile_resource(const std::string& path, TileResource& resource,
                        std::string& error) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        return fail(error, "cannot open tile resource");
    }
    const std::streamoff file_size = input.tellg();
    if (file_size < 32) {
        return fail(error, "tile resource header is truncated");
    }
    input.seekg(0, std::ios::beg);
    unsigned char header[32];
    if (!input.read(reinterpret_cast<char*>(header), 32)) {
        return fail(error, "cannot read tile resource header");
    }
    if (header[0] != 'M' || header[1] != 'S' || header[2] != '5' || header[3] != 'T') {
        return fail(error, "invalid tile resource magic");
    }
    if (read_u32(header + 4) != 1) {
        return fail(error, "unsupported tile resource version");
    }
    TileResource candidate;
    candidate.kind = read_u32(header + 8);
    candidate.width = read_u32(header + 12);
    candidate.height = read_u32(header + 16);
    candidate.count = read_u32(header + 20);
    const std::uint32_t payload_size = read_u32(header + 24);
    const std::uint32_t expected_crc = read_u32(header + 28);
    const std::uint64_t area = static_cast<std::uint64_t>(candidate.width) * candidate.height;
    if (candidate.count != 0 && area > std::numeric_limits<std::uint64_t>::max() / candidate.count) {
        return fail(error, "tile pixel count overflows");
    }
    const std::uint64_t pixel_count = area * candidate.count;
    if (pixel_count > UINT64_C(134217728) || payload_size > UINT32_C(134217728)) {
        return fail(error, "tile payload exceeds 128 MiB limit");
    }
    if (candidate.kind == 1) {
        if (candidate.width != 16 || candidate.height != 16 || candidate.count != 524288) {
            return fail(error, "invalid MS5 sprite dimensions or count");
        }
    } else if (candidate.kind == 2) {
        if (candidate.width != 8 || candidate.height != 8 || candidate.count != 4096) {
            return fail(error, "invalid MS5 fixed dimensions or count");
        }
    } else {
        return fail(error, "unsupported tile resource kind");
    }
    if (pixel_count != payload_size) {
        return fail(error, "tile payload size does not match dimensions");
    }
    const std::uint64_t expected_size = UINT64_C(32) + payload_size;
    if (static_cast<std::uint64_t>(file_size) != expected_size) {
        return fail(error, "tile resource is truncated or has trailing bytes");
    }
    try {
        candidate.pixels.resize(payload_size);
    } catch (const std::bad_alloc&) {
        return fail(error, "cannot allocate tile payload");
    }
    if (!input.read(reinterpret_cast<char*>(&candidate.pixels[0]), payload_size)) {
        return fail(error, "cannot read tile payload");
    }
    if (pixel_crc32(candidate.pixels) != expected_crc) {
        return fail(error, "tile payload CRC32 mismatch");
    }
    for (std::size_t i = 0; i < candidate.pixels.size(); ++i) {
        if (candidate.pixels[i] > 15) {
            return fail(error, "tile palette index exceeds 15");
        }
    }
    resource = std::move(candidate);
    error.clear();
    return true;
}

bool get_tile_pixel(const TileResource& resource, std::uint32_t tile,
                    std::uint32_t x, std::uint32_t y, std::uint8_t& pixel) {
    if (tile >= resource.count || x >= resource.width || y >= resource.height) {
        return false;
    }
    const std::uint64_t area = static_cast<std::uint64_t>(resource.width) * resource.height;
    // Guard caller-created resources as well as validated resources.
    if (area != 0 && tile > std::numeric_limits<std::uint64_t>::max() / area) {
        return false;
    }
    const std::uint64_t tile_offset = area * tile;
    const std::uint64_t local_offset = static_cast<std::uint64_t>(y) * resource.width + x;
    if (tile_offset > std::numeric_limits<std::uint64_t>::max() - local_offset) {
        return false;
    }
    const std::uint64_t offset = tile_offset + local_offset;
    if (offset >= resource.pixels.size()) {
        return false;
    }
    pixel = resource.pixels[static_cast<std::size_t>(offset)];
    return true;
}

} // namespace ms5
