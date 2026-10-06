#include "ms5/fixed_data_resource.h"

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

bool load_fixed_data_resource(const std::string& path,
                              FixedDataResource& resource, std::string& error) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        return fail(error, "cannot open fixed data resource");
    }
    const std::streamoff file_size = input.tellg();
    if (file_size < 32) {
        return fail(error, "fixed data resource header is truncated");
    }
    if (file_size > 32 + 1048576) {
        return fail(error, "fixed data resource exceeds maximum size");
    }
    input.seekg(0, std::ios::beg);
    unsigned char header[32];
    if (!input.read(reinterpret_cast<char*>(header), 32)) {
        return fail(error, "cannot read fixed data resource header");
    }
    if (header[0] != 'M' || header[1] != 'S' || header[2] != '5' || header[3] != 'D') {
        return fail(error, "invalid fixed data resource magic");
    }
    if (read_u32(header + 4) != 1 || read_u32(header + 8) != 1) {
        return fail(error, "unsupported fixed data resource version or kind");
    }
    const std::uint32_t cpu_address = read_u32(header + 12);
    const std::uint32_t rom_offset = read_u32(header + 16);
    const std::uint32_t payload_size = read_u32(header + 20);
    if (cpu_address >= 0x100000U || cpu_address != rom_offset) {
        return fail(error, "fixed data source must map the fixed program ROM");
    }
    if (payload_size == 0 || payload_size > 0x100000U - cpu_address) {
        return fail(error, "invalid fixed data window size");
    }
    if (read_u32(header + 28) != 0) {
        return fail(error, "fixed data reserved field must be zero");
    }
    if (file_size != static_cast<std::streamoff>(32U + payload_size)) {
        return fail(error, "fixed data resource is truncated or has trailing bytes");
    }
    FixedDataResource candidate;
    try {
        candidate.data.resize(payload_size);
    } catch (const std::bad_alloc&) {
        return fail(error, "cannot allocate fixed data resource");
    }
    if (!input.read(reinterpret_cast<char*>(&candidate.data[0]), payload_size)) {
        return fail(error, "cannot read fixed data payload");
    }
    char extra;
    if (input.get(extra) || input.bad() || !input.eof()) {
        return fail(error, "fixed data resource size changed or read failed");
    }
    if (payload_crc32(candidate.data) != read_u32(header + 24)) {
        return fail(error, "fixed data payload CRC32 mismatch");
    }
    resource.data.swap(candidate.data);
    resource.source_cpu_address = cpu_address;
    resource.source_rom_offset = rom_offset;
    error.clear();
    return true;
}

} // namespace ms5
