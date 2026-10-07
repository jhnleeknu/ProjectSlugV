#include "ms5/menu_border.h"

#include "ms5/menu_descriptor.h"

#include <new>

namespace ms5 {
namespace {

std::uint32_t read_u32(const std::vector<std::uint8_t>& ram,
                       std::size_t offset) {
    return (static_cast<std::uint32_t>(ram[offset]) << 24) |
           (static_cast<std::uint32_t>(ram[offset + 1U]) << 16) |
           (static_cast<std::uint32_t>(ram[offset + 2U]) << 8) |
           static_cast<std::uint32_t>(ram[offset + 3U]);
}

bool valid_slot(std::uint32_t address) {
    return address >= 0x00107e0eU && address <= 0x00107efeU &&
           (address - 0x00107e0eU) % 16U == 0U;
}

bool validate_slots(const std::vector<std::uint8_t>& ram,
                    std::size_t& head, std::size_t& current,
                    std::string& error) {
    if (ram.size() != 65536U) {
        error = "menu border requires exactly 65536 RAM bytes";
        return false;
    }
    const std::uint32_t head_address = read_u32(ram, 0x7f0eU);
    const std::uint32_t current_address = read_u32(ram, 0x7f12U);
    if (!valid_slot(head_address) || !valid_slot(current_address) ||
        head_address > current_address) {
        error = "menu border requires aligned menu slots with head <= current";
        return false;
    }
    head = head_address - 0x00100000U;
    current = current_address - 0x00100000U;
    return true;
}

bool occluded(const std::vector<std::uint8_t>& ram, std::size_t head,
              std::size_t current, std::uint16_t address) {
    const std::uint16_t delta = static_cast<std::uint16_t>(
        static_cast<unsigned int>(address) - 0x7000U);
    const std::uint8_t column = static_cast<std::uint8_t>(delta >> 5);
    const std::uint8_t row = static_cast<std::uint8_t>(delta & 31U);
    for (std::size_t cursor = current; cursor > head;) {
        cursor -= 16U;
        if ((ram[cursor + 15U] & 1U) != 0U) {
            continue;
        }
        const std::uint8_t relative_x = static_cast<std::uint8_t>(
            static_cast<unsigned int>(column) - ram[cursor + 9U]);
        const std::uint8_t relative_y = static_cast<std::uint8_t>(
            static_cast<unsigned int>(row) - ram[cursor + 10U]);
        if (relative_x < ram[cursor + 11U] && relative_y < ram[cursor + 4U]) {
            return true;
        }
    }
    return false;
}

void emit_border(const std::vector<std::uint8_t>& ram, std::size_t head,
                 std::size_t current, std::uint16_t& address,
                 std::uint16_t value, std::vector<FixedWrite>& writes) {
    if (occluded(ram, head, current, address)) {
        // The original ADD.W #0x20 is inside the visible-write branch.
        return;
    }
    FixedWrite write;
    write.address = address;
    write.value = value;
    writes.push_back(write);
    address = static_cast<std::uint16_t>(static_cast<unsigned int>(address) + 0x20U);
}

void emit_border_row(const std::vector<std::uint8_t>& ram, std::size_t head,
                     std::size_t current, std::uint16_t row_start,
                     unsigned int width, std::uint16_t color,
                     std::uint8_t left, std::uint8_t middle, std::uint8_t right,
                     std::vector<FixedWrite>& writes) {
    std::uint16_t address = row_start;
    emit_border(ram, head, current, address,
                static_cast<std::uint16_t>(color | left), writes);
    const unsigned int middle_count = width > 2U ? width - 2U : 0U;
    for (unsigned int index = 0; index < middle_count; ++index) {
        emit_border(ram, head, current, address,
                    static_cast<std::uint16_t>(color | middle), writes);
    }
    emit_border(ram, head, current, address,
                static_cast<std::uint16_t>(color | right), writes);
}

} // namespace

bool menu_position_occluded(const std::vector<std::uint8_t>& ram,
                            std::uint16_t address, bool& covered,
                            std::string& error) {
    std::size_t head = 0U;
    std::size_t current = 0U;
    if (!validate_slots(ram, head, current, error)) {
        return false;
    }
    covered = occluded(ram, head, current, address);
    error.clear();
    return true;
}

bool trace_menu_border(const std::vector<std::uint8_t>& ram,
                       const FixedDataResource& resource,
                       std::vector<FixedWrite>& writes, std::string& error,
                       std::uint32_t* d3) {
    std::size_t head = 0U;
    std::size_t current = 0U;
    if (!validate_slots(ram, head, current, error)) {
        return false;
    }
    const unsigned int height = ram[current + 4U];
    std::vector<FixedWrite> pending;
    if (height == 0U) {
        writes.swap(pending);
        error.clear();
        return true;
    }
    MenuDescriptor descriptor;
    if (!decode_menu_descriptor(resource, read_u32(ram, current), descriptor, error)) {
        return false;
    }
    const unsigned int shifted_x = static_cast<unsigned int>(ram[current + 9U]) << 5;
    std::uint16_t row_start = static_cast<std::uint16_t>(
        0x7000U + (shifted_x & 0xff00U) +
        ((shifted_x + ram[current + 10U]) & 0xffU));
    const unsigned int width = ram[current + 11U];
    try {
        if ((descriptor.flags & 1U) != 0U) {
            for (unsigned int row = 0; row < height; ++row) {
                std::uint16_t address = row_start;
                for (unsigned int column = 0; column < width; ++column) {
                    FixedWrite write;
                    write.address = address;
                    write.value = 0x00ffU;
                    pending.push_back(write);
                    address = static_cast<std::uint16_t>(
                        static_cast<unsigned int>(address) + 0x20U);
                }
                row_start = static_cast<std::uint16_t>(
                    static_cast<unsigned int>(row_start) + 1U);
            }
        } else {
            const std::uint16_t color = head == current ? 0x0b00U : 0x6b00U;
            emit_border_row(ram, head, current, row_start, width, color,
                            0xf4U, 0xf0U, 0xf5U, pending);
            row_start = static_cast<std::uint16_t>(
                static_cast<unsigned int>(row_start) + 1U);
            const unsigned int middle_rows = height > 2U ? height - 2U : 0U;
            for (unsigned int row = 0; row < middle_rows; ++row) {
                emit_border_row(ram, head, current, row_start, width, color,
                                0xf2U, 0x60U, 0xf3U, pending);
                row_start = static_cast<std::uint16_t>(
                    static_cast<unsigned int>(row_start) + 1U);
            }
            emit_border_row(ram, head, current, row_start, width, color,
                            0xf6U, 0xf1U, 0xf7U, pending);
            row_start = static_cast<std::uint16_t>(row_start + 1U);
        }
    } catch (const std::bad_alloc&) {
        error = "cannot allocate menu border writes";
        return false;
    }
    writes.swap(pending);
    if (d3 != NULL) { *d3 = (*d3 & 0xffff0000U) | row_start; }
    error.clear();
    return true;
}

} // namespace ms5
