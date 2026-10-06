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

std::uint16_t blend_word(std::uint16_t first, std::uint16_t second,
                         std::uint8_t weight) {
    std::uint16_t value = 0;
    for (unsigned int shift = 0; shift <= 10; shift += 5) {
        const std::int32_t a = (first >> shift) & 31U;
        const std::int32_t b = (second >> shift) & 31U;
        // C++11 signed division truncates toward zero, matching the ROM table.
        const std::int32_t channel = a + (b - a) * weight / 31;
        value = static_cast<std::uint16_t>(
            value | (static_cast<std::uint16_t>(channel) << shift));
    }
    return static_cast<std::uint16_t>(
        ((value & 1U) << 12) | ((value & 0x20U) << 8) |
        ((value & 0x400U) << 4) | ((value >> 1) & 15U) |
        ((value >> 2) & 0xf0U) | ((value >> 3) & 0xf00U));
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
        if (effects != 0 && (flags & 2U) == 0) {
            error = "unsupported palette color effects";
            return false;
        }
        const std::uint8_t weight = candidate[node + 0xe];
        const bool blend = first_id != second_id && weight > 0 && weight < 31;
        const std::uint16_t selected_id =
            first_id != second_id && weight >= 31 ? second_id : first_id;
        const PaletteRecord* first = find_record(records, selected_id);
        const PaletteRecord* second = blend ? find_record(records, second_id) : NULL;
        if (first == NULL || (blend && second == NULL)) {
            error = "palette ID is absent from resource";
            return false;
        }
        const std::size_t staging = 0x5da2 + slot * 32;
        for (std::size_t word = 1; word < 16; ++word) {
            std::uint16_t hardware = first->hardware_words[word];
            if (blend) {
                if (first->source_words[word] > 0x7fffU ||
                    second->source_words[word] > 0x7fffU) {
                    error = "unsupported palette interpolation source bit 15";
                    return false;
                }
                hardware = blend_word(first->source_words[word],
                                      second->source_words[word], weight);
            }
            write_be16(candidate, staging + word * 2, hardware);
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
