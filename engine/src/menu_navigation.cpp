#include "ms5/menu_navigation.h"
#include "ms5/menu_border.h"
#include "ms5/menu_descriptor.h"
#include "ms5/menu_text.h"
#include <new>

namespace ms5 {
namespace {
std::uint32_t read_u32(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) |
           (static_cast<std::uint32_t>(ram[at + 1U]) << 16) |
           (static_cast<std::uint32_t>(ram[at + 2U]) << 8) | ram[at + 3U];
}
std::uint8_t advance(std::uint8_t index, std::uint8_t count, bool previous) {
    if (previous) {
        return index == 0U ? static_cast<std::uint8_t>(count - 1U) :
                            static_cast<std::uint8_t>(index - 1U);
    }
    const std::uint8_t next = static_cast<std::uint8_t>(index + 1U);
    return next < count ? next : 0U;
}
}

bool navigate_menu(std::vector<std::uint8_t>& ram,
                   const FixedDataResource& resource, bool explicit_selection,
                   std::uint8_t requested,
                   std::vector<VideoPortWrite>& writes, std::string& error,
                   const FixedDataResource* font) {
    bool covered = false;
    if (!menu_position_occluded(ram, 0x7000U, covered, error)) {
        return false;
    }
    const std::size_t slot = read_u32(ram, 0x7f12U) - 0x100000U;
    MenuDescriptor descriptor;
    if (!decode_menu_descriptor(resource, read_u32(ram, slot), descriptor, error)) {
        return false;
    }
    const std::uint8_t count = ram[slot + 6U];
    const std::uint8_t old_index = ram[slot + 7U];
    if (count == 0U || count != descriptor.items.size() || old_index >= count) {
        error = "menu navigation requires a nonempty matching count and valid old index";
        return false;
    }
    const bool previous = (ram[slot + 15U] & 2U) != 0U;
    std::uint8_t index = explicit_selection ?
        (requested < count ? requested : static_cast<std::uint8_t>(count - 1U)) :
        advance(old_index, count, previous);
    unsigned int attempts = 0U;
    while (descriptor.items[index].callback == 0U ||
           descriptor.items[index].title_address == 0xfffffffeU) {
        ++attempts;
        if (attempts >= count) {
            error = "menu navigation has no selectable item (original search would loop)";
            return false;
        }
        index = advance(index, count, previous);
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        std::vector<VideoPortWrite> row;
        candidate[slot + 7U] = index;
        candidate[slot + 8U] = old_index;
        if (!draw_menu_item(candidate, resource, true, pending, error, font)) {
            return false;
        }
        candidate[slot + 8U] = index;
        if (!draw_menu_item(candidate, resource, true, row, error, font)) {
            return false;
        }
        pending.insert(pending.end(), row.begin(), row.end());
        candidate[slot + 14U] = 0U;
        ram.swap(candidate);
        writes.swap(pending);
    } catch (const std::bad_alloc&) {
        error = "cannot allocate menu navigation output";
        return false;
    }
    error.clear();
    return true;
}
} // namespace ms5
