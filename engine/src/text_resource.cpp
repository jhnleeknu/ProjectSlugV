#include "ms5/text_resource.h"

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

bool load_text_resource(const std::string& path, TextResource& resource,
                        std::string& error) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        return fail(error, "cannot open text resource");
    }
    const std::streamoff file_size = input.tellg();
    if (file_size < 32) {
        return fail(error, "text resource header is truncated");
    }
    if (file_size > 32 + 128 + 1048576) {
        return fail(error, "text resource exceeds maximum size");
    }
    input.seekg(0, std::ios::beg);
    unsigned char header[32];
    if (!input.read(reinterpret_cast<char*>(header), 32)) {
        return fail(error, "cannot read text resource header");
    }
    if (header[0] != 'M' || header[1] != 'S' || header[2] != '5' || header[3] != 'X') {
        return fail(error, "invalid text resource magic");
    }
    if (read_u32(header + 4) != 1 || read_u32(header + 8) != 1) {
        return fail(error, "unsupported text resource version or kind");
    }
    const std::uint32_t id = read_u32(header + 12);
    const std::uint32_t count = read_u32(header + 16);
    const std::uint32_t payload_size = read_u32(header + 20);
    if (id >= 0x800000U) {
        return fail(error, "text source ROM offset is out of range");
    }
    if (count == 0 || count > 16) {
        return fail(error, "invalid text palette binding count");
    }
    const std::uint32_t binding_bytes = count * 8U;
    if (payload_size <= binding_bytes || payload_size - binding_bytes > 1048576U) {
        return fail(error, "invalid text script size");
    }
    if (read_u32(header + 28) != 0) {
        return fail(error, "text reserved field must be zero");
    }
    if (file_size != static_cast<std::streamoff>(32U + payload_size)) {
        return fail(error, "text resource is truncated or has trailing bytes");
    }
    std::vector<std::uint8_t> payload;
    TextResource candidate;
    try {
        payload.resize(payload_size);
        candidate.bindings.resize(count);
        candidate.script.resize(payload_size - binding_bytes);
    } catch (const std::bad_alloc&) {
        return fail(error, "cannot allocate text resource");
    }
    if (!input.read(reinterpret_cast<char*>(&payload[0]), payload_size)) {
        return fail(error, "cannot read text payload");
    }
    if (payload_crc32(payload) != read_u32(header + 24)) {
        return fail(error, "text payload CRC32 mismatch");
    }
    bool bound[16] = {};
    for (std::uint32_t i = 0; i < count; ++i) {
        TextPaletteBinding& binding = candidate.bindings[i];
        binding.slot = read_u32(&payload[i * 8U]);
        binding.source_id = read_u32(&payload[i * 8U + 4U]);
        if (binding.slot >= 16 || binding.source_id > 65535) {
            return fail(error, "text palette binding is out of range");
        }
        if (bound[binding.slot]) {
            return fail(error, "text palette slots must be unique");
        }
        bound[binding.slot] = true;
    }
    for (std::size_t i = 0; i < candidate.script.size(); ++i) {
        candidate.script[i] = payload[binding_bytes + i];
    }
    resource.bindings.swap(candidate.bindings);
    resource.script.swap(candidate.script);
    resource.id = id;
    error.clear();
    return true;
}

} // namespace ms5
