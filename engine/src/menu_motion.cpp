#include "ms5/menu_motion.h"

#include <new>

namespace ms5 {
namespace {

std::size_t current_slot(const std::vector<std::uint8_t>& ram) {
    const std::uint32_t address =
        (static_cast<std::uint32_t>(ram[0x7f12U]) << 24) |
        (static_cast<std::uint32_t>(ram[0x7f13U]) << 16) |
        (static_cast<std::uint32_t>(ram[0x7f14U]) << 8) |
        static_cast<std::uint32_t>(ram[0x7f15U]);
    return address - 0x00100000U;
}

unsigned int height_word(const std::vector<std::uint8_t>& ram,
                         std::size_t current) {
    return (static_cast<unsigned int>(ram[current + 4U]) << 8) |
           ram[current + 5U];
}

void store_height(std::vector<std::uint8_t>& ram, std::size_t current,
                  unsigned int height) {
    ram[current + 4U] = static_cast<std::uint8_t>(height >> 8);
    ram[current + 5U] = static_cast<std::uint8_t>(height & 0xffU);
}

} // namespace

bool open_menu_step(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource,
                    std::vector<FixedWrite>& writes, std::string& error) {
    std::vector<FixedWrite> pending;
    if (!trace_menu_border(ram, resource, pending, error)) {
        return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        const std::size_t current = current_slot(candidate);
        const unsigned int target = candidate[current + 12U];
        unsigned int next = (height_word(candidate, current) + (target << 6)) & 0xffffU;
        if (next > (target << 8)) {
            next = target << 8;
        }
        store_height(candidate, current, next);
        ram.swap(candidate);
        writes.swap(pending);
    } catch (const std::bad_alloc&) {
        error = "cannot allocate menu opening step";
        return false;
    }
    error.clear();
    return true;
}

bool close_menu_step(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& resource,
                     std::vector<FixedWrite>& writes, std::string& error) {
    bool covered = false;
    if (!menu_position_occluded(ram, 0x7000U, covered, error)) {
        return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<FixedWrite> pending;
        const std::size_t current = current_slot(candidate);
        const unsigned int old = height_word(candidate, current);
        const unsigned int step = static_cast<unsigned int>(candidate[current + 6U]) << 6;
        const unsigned int decrement = old < step ? old : step;
        const unsigned int next = old - decrement;
        const unsigned int clear_rows = ((next & 0xffU) + decrement) >> 8;
        store_height(candidate, current, next);
        if (!trace_menu_border(candidate, resource, pending, error)) {
            return false;
        }
        const unsigned int shifted_x = static_cast<unsigned int>(candidate[current + 9U]) << 5;
        const std::uint16_t base = static_cast<std::uint16_t>(
            0x7000U + (shifted_x & 0xff00U) +
            ((shifted_x + candidate[current + 10U]) & 0xffU));
        std::uint16_t row_start = static_cast<std::uint16_t>(
            (base & 0xff00U) | ((static_cast<unsigned int>(base) + (next >> 8)) & 0xffU));
        const unsigned int width = candidate[current + 11U];
        for (unsigned int row = 0; row < clear_rows; ++row) {
            std::uint16_t address = row_start;
            for (unsigned int column = 0; column < width; ++column) {
                if (!menu_position_occluded(candidate, address, covered, error)) {
                    return false;
                }
                if (!covered) {
                    FixedWrite write;
                    write.address = address;
                    write.value = 0x00ffU;
                    pending.push_back(write);
                }
                // The close clear loop advances even when the tile is covered.
                address = static_cast<std::uint16_t>(static_cast<unsigned int>(address) + 0x20U);
            }
            row_start = static_cast<std::uint16_t>(static_cast<unsigned int>(row_start) + 1U);
        }
        ram.swap(candidate);
        writes.swap(pending);
    } catch (const std::bad_alloc&) {
        error = "cannot allocate menu closing step";
        return false;
    }
    error.clear();
    return true;
}

} // namespace ms5
