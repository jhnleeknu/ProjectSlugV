#include "ms5/menu_stack.h"
#include "ms5/menu_init.h"
#include "ms5/menu_border.h"
#include "ms5/menu_text.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t read_u32(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) |
           (static_cast<std::uint32_t>(ram[at+1U]) << 16) |
           (static_cast<std::uint32_t>(ram[at+2U]) << 8) | ram[at+3U];
}
void put_u32(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4U; ++i) {
        ram[at+i] = static_cast<std::uint8_t>(value >> (24U-i*8U));
    }
}
std::uint16_t base_address(std::uint8_t x, std::uint8_t y) {
    const unsigned int shifted = static_cast<unsigned int>(x) << 5;
    return static_cast<std::uint16_t>(0x7000U + (shifted & 0xff00U) + ((shifted+y)&0xffU));
}
}
bool push_menu(std::vector<std::uint8_t>& ram,
               const FixedDataResource& resource, std::uint32_t descriptor_address,
               std::uint16_t x, std::uint16_t y, std::uint16_t initial_line,
               std::vector<VideoPortWrite>& writes, std::string& error) {
    if (ram.size() != 65536U) {
        error = "menu stack requires exactly 65536 RAM bytes";
        return false;
    }
    const std::uint32_t head = read_u32(ram, 0x7f0eU);
    if (head <= 0x107e0eU || head > 0x107f0eU || (head-0x107e0eU)%16U != 0U) {
        error = "menu stack is full or its head is invalid";
        return false;
    }
    const std::uint32_t saved_current = read_u32(ram, 0x7f12U);
    const std::uint32_t new_head = head-16U;
    const std::size_t slot = new_head-0x100000U;
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        put_u32(candidate, 0x7f0eU, new_head);
        put_u32(candidate, 0x7f12U, head);
        // The original suppresses occlusion by the as-yet-uninitialized slot.
        candidate[slot+9U] = candidate[slot+10U] = 255U;
        candidate[slot+11U] = candidate[slot+12U] = 0U;
        std::uint16_t line = initial_line;
        if (head < 0x107f0eU) {
            std::vector<FixedWrite> border;
            if (!trace_menu_border(candidate, resource, border, error)) {
                return false;
            }
            for (std::size_t i = 0; i < border.size(); ++i) {
                VideoPortWrite write;
                write.address = 0x3c0000U;
                write.size = 4U;
                write.value = (static_cast<std::uint32_t>(border[i].address)<<16) | border[i].value;
                pending.push_back(write);
            }
            const std::size_t parent = head-0x100000U;
            const unsigned int height = candidate[parent+4U];
            if (height != 0U) {
                // Supported visible text requires flags0: border9b58 leaves
                // D3 at base + max(height,2), including its final increment.
                line = static_cast<std::uint16_t>(base_address(candidate[parent+9U],
                    candidate[parent+10U]) + (height < 2U ? 2U : height));
            }
            std::vector<VideoPortWrite> text;
            if (!draw_menu_text(candidate, resource, true, line, text, error, &line)) {
                return false;
            }
            pending.insert(pending.end(), text.begin(), text.end());
        }
        put_u32(candidate, 0x7f12U, new_head);
        if (!configure_menu_slot(candidate, resource, new_head, descriptor_address,
                                  x, y, line, error)) {
            return false;
        }
        candidate[0x7f1bU] = 1U;
        put_u32(candidate, 0x7f12U, saved_current);
        ram.swap(candidate);
        writes.swap(pending);
    } catch (const std::bad_alloc&) {
        error = "cannot allocate menu stack output";
        return false;
    }
    error.clear();
    return true;
}
}
