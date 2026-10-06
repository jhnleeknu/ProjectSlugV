#include "ms5/palette_prepare.h"

#include <cstddef>
#include <new>

namespace {

std::uint16_t read_be16(const std::vector<std::uint8_t>& ram,
                        std::size_t offset) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(ram[offset]) << 8) | ram[offset + 1]);
}

void write_be16(std::vector<std::uint8_t>& ram, std::size_t offset,
                std::uint16_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 1] = static_cast<std::uint8_t>(value);
}

const ms5::PaletteRecord* find_record(
        const std::vector<ms5::PaletteRecord>& records, std::uint16_t id) {
    std::size_t first = 0;
    std::size_t last = records.size();
    while (first < last) {
        const std::size_t middle = first + (last - first) / 2;
        if (records[middle].id < id) {
            first = middle + 1;
        } else {
            last = middle;
        }
    }
    if (first == records.size() || records[first].id != id) {
        return NULL;
    }
    return &records[first];
}

} // namespace

namespace ms5 {

bool prepare_palettes(std::vector<std::uint8_t>& ram,
                      const std::vector<PaletteRecord>& records,
                      std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    for (std::size_t i = 0; i < records.size(); ++i) {
        if (records[i].id > 0xffffU ||
            (i != 0 && records[i].id <= records[i - 1].id)) {
            error = "palette IDs must be 16-bit and strictly ascending";
            return false;
        }
    }
    std::vector<std::uint8_t> candidate;
    try {
        candidate = ram;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate palette preparation RAM";
        return false;
    }
    candidate[0x7dd5] = 0;
    write_be16(candidate, 0x10, 0);
    const std::uint8_t effects = static_cast<std::uint8_t>(
        candidate[0x7dc2] | candidate[0x7dc4] | candidate[0x7dc6]);
    for (std::size_t slot = 0; slot < 256; ++slot) {
        const std::size_t node = 0x4d92 + slot * 16;
        const std::uint8_t flags = candidate[node + 15];
        if ((flags & 0x80U) == 0) {
            continue;
        }
        candidate[node + 15] = static_cast<std::uint8_t>(flags & 0x7fU);
        const std::uint16_t first_id = read_be16(candidate, node + 0xa);
        const std::uint16_t second_id = read_be16(candidate, node + 0xc);
        if (first_id != second_id) {
            error = "unsupported palette interpolation";
            return false;
        }
        if (effects != 0 && (flags & 2U) == 0) {
            error = "unsupported palette color effects";
            return false;
        }
        const PaletteRecord* record = find_record(records, first_id);
        if (record == NULL) {
            error = "palette ID is absent from resource";
            return false;
        }
        const std::size_t staging = 0x5da2 + slot * 32;
        for (std::size_t word = 1; word < 16; ++word) {
            write_be16(candidate, staging + word * 2,
                       record->hardware_words[word]);
        }
        write_be16(candidate, staging, 0x8000);
        candidate[0x7dd5] = 0xff;
    }
    candidate[0x7ded] = candidate[0x7dd5];
    write_be16(candidate, 0x10, 0);
    ram.swap(candidate);
    error.clear();
    return true;
}

} // namespace ms5
