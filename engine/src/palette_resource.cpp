#include "ms5/palette_resource.h"

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

std::uint16_t read_word(const unsigned char* bytes) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint32_t>(bytes[0]) << 8) | bytes[1]);
}

std::uint32_t payload_crc32(const std::vector<unsigned char>& bytes) {
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

bool load_palette_resource(const std::string& path,
                           std::vector<PaletteRecord>& records,
                           std::string& error) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        return fail(error, "cannot open palette resource");
    }
    const std::streamoff file_size = input.tellg();
    if (file_size < 32) {
        return fail(error, "palette resource header is truncated");
    }
    if (file_size > 32 + 65536 * 68) {
        return fail(error, "palette resource exceeds maximum catalog size");
    }
    input.seekg(0, std::ios::beg);
    unsigned char header[32];
    if (!input.read(reinterpret_cast<char*>(header), 32)) {
        return fail(error, "cannot read palette resource header");
    }
    if (header[0] != 'M' || header[1] != 'S' || header[2] != '5' || header[3] != 'P') {
        return fail(error, "invalid palette resource magic");
    }
    if (read_u32(header + 4) != 1) {
        return fail(error, "unsupported palette resource version");
    }
    const std::uint32_t count = read_u32(header + 8);
    const std::uint32_t payload_size = read_u32(header + 16);
    if (count == 0 || count > 65536) {
        return fail(error, "invalid palette record count");
    }
    if (read_u32(header + 12) != 68 || payload_size != count * 68U) {
        return fail(error, "invalid palette record or payload size");
    }
    if (read_u32(header + 24) != 0 || read_u32(header + 28) != 0) {
        return fail(error, "palette reserved fields must be zero");
    }
    if (file_size != static_cast<std::streamoff>(32U + payload_size)) {
        return fail(error, "palette resource is truncated or has trailing bytes");
    }
    std::vector<unsigned char> payload;
    std::vector<PaletteRecord> candidate;
    try {
        payload.resize(payload_size);
        candidate.resize(count);
    } catch (const std::bad_alloc&) {
        return fail(error, "cannot allocate palette catalog");
    }
    if (!input.read(reinterpret_cast<char*>(&payload[0]), payload_size)) {
        return fail(error, "cannot read palette payload");
    }
    if (payload_crc32(payload) != read_u32(header + 20)) {
        return fail(error, "palette payload CRC32 mismatch");
    }
    for (std::uint32_t i = 0; i < count; ++i) {
        const unsigned char* bytes = &payload[static_cast<std::size_t>(i) * 68];
        PaletteRecord& record = candidate[i];
        record.id = read_u32(bytes);
        if (record.id > 65535 || (i != 0 && record.id <= candidate[i - 1].id)) {
            return fail(error, "palette IDs must be 16-bit and strictly ascending");
        }
        for (unsigned int word = 0; word < 16; ++word) {
            record.source_words[word] = read_word(bytes + 4 + word * 2);
            record.hardware_words[word] = read_word(bytes + 36 + word * 2);
        }
        if (record.hardware_words[0] != 0) {
            return fail(error, "palette hardware word zero must be zero");
        }
    }
    records.swap(candidate);
    error.clear();
    return true;
}

} // namespace ms5
