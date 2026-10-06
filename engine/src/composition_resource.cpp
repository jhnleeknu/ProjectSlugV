#include "ms5/composition_resource.h"

#include <fstream>
#include <new>

namespace ms5 {
namespace {

std::uint32_t read_u32(const unsigned char* bytes) {
    return static_cast<std::uint32_t>(bytes[0]) |
           (static_cast<std::uint32_t>(bytes[1]) << 8) |
           (static_cast<std::uint32_t>(bytes[2]) << 16) |
           (static_cast<std::uint32_t>(bytes[3]) << 24);
}

std::uint32_t payload_crc32(const std::vector<std::uint8_t>& bytes) {
    std::uint32_t crc = UINT32_C(0xffffffff);
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        crc ^= bytes[i];
        for (unsigned int bit = 0; bit < 8; ++bit) {
            crc = (crc >> 1) ^ ((crc & 1U) ? UINT32_C(0xedb88320) : 0U);
        }
    }
    return crc ^ UINT32_C(0xffffffff);
}

bool fail(std::string& error, const char* message) {
    error = message;
    return false;
}

} // namespace

bool load_composition_resource(const std::string& path,
                               CompositionResource& resource,
                               std::string& error) {
    const std::uint32_t maximum_single_payload = 8U + 255U * 32U * 4U;
    const std::uint32_t maximum_blocks_payload = 2U + 255U * (6U + 255U * 32U * 4U);
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        return fail(error, "cannot open composition resource");
    }
    const std::streamoff file_size = input.tellg();
    if (file_size < 32) {
        return fail(error, "composition resource header is truncated");
    }
    if (file_size > static_cast<std::streamoff>(32U + maximum_blocks_payload)) {
        return fail(error, "composition resource exceeds maximum size");
    }
    input.seekg(0, std::ios::beg);
    unsigned char header[32];
    if (!input.read(reinterpret_cast<char*>(header), 32)) {
        return fail(error, "cannot read composition resource header");
    }
    if (header[0] != 'M' || header[1] != 'S' || header[2] != '5' || header[3] != 'C') {
        return fail(error, "invalid composition resource magic");
    }
    const std::uint32_t kind = read_u32(header + 8);
    if (read_u32(header + 4) != 1 || (kind != 1 && kind != 2)) {
        return fail(error, "unsupported composition resource version or kind");
    }
    const std::uint32_t id = read_u32(header + 12);
    const std::uint32_t source_offset = read_u32(header + 16);
    const std::uint32_t payload_size = read_u32(header + 20);
    const std::uint32_t maximum_payload = kind == 1 ? maximum_single_payload : maximum_blocks_payload;
    if (id > 0x7fffffU || (id & 7U) > 5U) {
        return fail(error, "composition packed ID is out of range");
    }
    if (payload_size < 12 || payload_size > maximum_payload) {
        return fail(error, "invalid composition payload size");
    }
    if (source_offset >= 0x800000U || payload_size > 0x800000U - source_offset) {
        return fail(error, "composition source ROM range is out of bounds");
    }
    if (read_u32(header + 28) != 0) {
        return fail(error, "composition reserved field must be zero");
    }
    if (file_size != static_cast<std::streamoff>(32U + payload_size)) {
        return fail(error, "composition resource is truncated or has trailing bytes");
    }
    CompositionResource candidate;
    try {
        candidate.data.resize(payload_size);
    } catch (const std::bad_alloc&) {
        return fail(error, "cannot allocate composition resource");
    }
    if (!input.read(reinterpret_cast<char*>(&candidate.data[0]), payload_size)) {
        return fail(error, "cannot read composition payload");
    }
    if (payload_crc32(candidate.data) != read_u32(header + 24)) {
        return fail(error, "composition payload CRC32 mismatch");
    }
    const std::uint32_t count = candidate.data[0];
    if (count == 0 || candidate.data[1] != 0 || (kind == 1 && count != 1)) {
        return fail(error, "invalid composition rectangle count or flags");
    }
    std::size_t position = 2;
    for (std::uint32_t block = 0; block < count; ++block) {
        if (candidate.data.size() - position < 6U) {
            return fail(error, "composition rectangle header is truncated");
        }
        const std::uint32_t width = candidate.data[position + 4];
        const std::uint32_t height = candidate.data[position + 5];
        if (width == 0 || height == 0 || height > 32) {
            return fail(error, "invalid composition rectangle dimensions");
        }
        position += 6U;
        const std::size_t tile_bytes = width * height * 4U;
        if (tile_bytes > candidate.data.size() - position) {
            return fail(error, "composition rectangle tiles are truncated");
        }
        position += tile_bytes;
    }
    if (position != candidate.data.size()) {
        return fail(error, "composition payload has trailing bytes");
    }
    resource.data.swap(candidate.data);
    resource.id = id;
    resource.source_rom_offset = source_offset;
    error.clear();
    return true;
}

} // namespace ms5
