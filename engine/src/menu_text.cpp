#include "ms5/menu_text.h"

#include "ms5/fixed_text.h"
#include "ms5/menu_border.h"
#include "ms5/menu_descriptor.h"
#include "ms5/menu_debug.h"
#include "ms5/stage_area_menu.h"
#include "ms5/stage_group_menu.h"

#include <new>

namespace ms5 {
namespace {

std::uint32_t read_u32(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) |
           (static_cast<std::uint32_t>(ram[at + 1U]) << 16) |
           (static_cast<std::uint32_t>(ram[at + 2U]) << 8) | ram[at + 3U];
}

bool supported_callback(std::uint32_t address) {
    return address == 0U || address == 0x9488U || address == 0x94d6U ||
           address == 0x949aU || address == 0x94b8U || address == 0x950cU ||
           address == 0x9532U || address == 0x9aa8U ||
           address == 0x9602U || address == 0x9802U;
}

bool script_at(const FixedDataResource& resource, std::uint32_t address,
               std::vector<std::uint8_t>& script, std::string& error) {
    if (address < resource.source_cpu_address ||
        address - resource.source_cpu_address >= resource.data.size()) {
        error = "menu text address must lie inside the fixed data resource";
        return false;
    }
    const std::size_t offset = address - resource.source_cpu_address;
    script.assign(resource.data.begin() + offset, resource.data.end());
    return true;
}

bool glyph_visible(std::uint16_t address, void* context, bool& visible,
                   std::string& error) {
    const std::vector<std::uint8_t>& ram =
        *static_cast<const std::vector<std::uint8_t>*>(context);
    bool covered = false;
    if (!menu_position_occluded(ram, address, covered, error)) {
        return false;
    }
    visible = !covered;
    return true;
}

std::uint16_t base_address(std::uint8_t x, std::uint8_t y) {
    const unsigned int shifted = static_cast<unsigned int>(x) << 5;
    return static_cast<std::uint16_t>(
        0x7000U + (shifted & 0xff00U) + ((shifted + y) & 0xffU));
}

bool append_text(const std::vector<std::uint8_t>& script,
                 std::uint16_t address, std::uint16_t style, bool clip,
                 std::vector<std::uint8_t>& ram,
                 std::vector<VideoPortWrite>& writes, std::string& error,
                 std::uint16_t* final_line) {
    std::vector<VideoPortWrite> text_writes;
    if (!trace_direct_fixed_text_visible(script, address, style,
            clip ? glyph_visible : NULL, &ram, text_writes, error)) {
        return false;
    }
    if (final_line != NULL) {
        FixedTextMeasure measurement;
        if (!measure_fixed_text(script, style, address, measurement, error)) {
            return false;
        }
        *final_line = measurement.line;
    }
    writes.insert(writes.end(), text_writes.begin(), text_writes.end());
    return true;
}

bool append_item(const MenuItem& item, std::size_t index,
                 std::size_t slot, std::uint32_t head, std::uint32_t current,
                 const FixedDataResource& resource, bool clip,
                 std::vector<std::uint8_t>& ram,
                 std::vector<VideoPortWrite>& writes, std::string& error,
                 std::uint16_t* final_line, const FixedDataResource* font,
                 const StageGroupMenuContext* stage_context) {
    const std::uint8_t row = static_cast<std::uint8_t>(index + 1U);
    if (row >= ram[slot + 4U]) {
        return true;
    }
    const std::uint8_t selected = ram[slot + 7U];
    std::uint16_t address = static_cast<std::uint16_t>(
        static_cast<unsigned int>(base_address(ram[slot + 9U],
                                                ram[slot + 10U])) + 0x20U);
    address = static_cast<std::uint16_t>((address & 0xff00U) |
        ((static_cast<unsigned int>(address) + row) & 0xffU));
    for (unsigned int half_index = 0; half_index < 2U; ++half_index) {
        bool covered = false;
        if (!menu_position_occluded(ram, address, covered, error)) {
            return false;
        }
        if (!covered) {
            VideoPortWrite write;
            write.size = 4U;
            write.address = 0x3c0000U;
            const std::uint16_t tile = index == selected ?
                static_cast<std::uint16_t>(0x0313U + half_index) : 0x00ffU;
            write.value = (static_cast<std::uint32_t>(address) << 16) | tile;
            writes.push_back(write);
        }
        address = static_cast<std::uint16_t>(
            static_cast<unsigned int>(address) + 0x20U);
    }
    std::uint16_t line = final_line != NULL ? *final_line : 0U;
    if (item.title_address != 0U) {
        std::vector<std::uint8_t> script;
        if (!script_at(resource, item.title_address, script, error)) {
            return false;
        }
        const std::uint16_t style = current != head && index != selected ?
                                   0x0603U : 0x0003U;
        if (!append_text(script, address, style, clip, ram, writes, error,
                         &line)) {
            return false;
        }
    }
    if (item.callback == 0x9aa8U || item.callback == 0x9602U ||
        item.callback == 0x9802U) {
        std::uint32_t a2 = current;
        std::vector<VideoPortWrite> ports;
        if (item.callback == 0x9aa8U) {
            if (!dispatch_debug_menu(ram, resource, font, 5U, line, a2,
                                     ports, error)) {
                return false;
            }
        } else if (item.callback == 0x9602U) {
            if (!dispatch_stage_area_menu(ram, resource, font, stage_context,
                                          5U, line, a2, ports, error)) {
                return false;
            }
        } else {
            if (!dispatch_stage_group_menu(ram, resource, font, stage_context,
                                           5U, a2, ports, error)) {
                return false;
            }
            // The native 0x9781 format ends in a literal space and zero,
            // leaving D3 equal to the formatter's stored line word.
            line = static_cast<std::uint16_t>(
                (static_cast<unsigned int>(ram[0x4cd8U]) << 8) |
                ram[0x4cd9U]);
        }
        writes.insert(writes.end(), ports.begin(), ports.end());
    }
    if (final_line != NULL) {
        *final_line = line;
    }
    // Other supported callbacks return from event 5 without RAM or video writes.
    return true;
}

} // namespace

bool draw_menu_item(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource, bool clip,
                    std::vector<VideoPortWrite>& writes, std::string& error,
                    const FixedDataResource* font,
                    const StageGroupMenuContext* stage_context,
                    std::uint16_t* final_line) {
    bool covered = false;
    if (!menu_position_occluded(ram, 0x7000U, covered, error)) {
        return false;
    }
    const std::uint32_t head = read_u32(ram, 0x7f0eU);
    const std::uint32_t current = read_u32(ram, 0x7f12U);
    const std::size_t slot = current - 0x100000U;
    const std::uint8_t index = ram[slot + 8U];
    const std::uint8_t row = static_cast<std::uint8_t>(
        static_cast<unsigned int>(index) + 1U);
    std::vector<VideoPortWrite> pending;
    if (row >= ram[slot + 4U]) {
        writes.swap(pending);
        error.clear();
        return true;
    }
    if (clip && read_u32(ram, 0x7f16U) != 0x3650U) {
        error = "clipped menu text requires the direct renderer at CPU 0x003650";
        return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        MenuDescriptor descriptor;
        if (!decode_menu_descriptor(resource, read_u32(ram, slot), descriptor, error)) {
            return false;
        }
        if (descriptor.flags != 0U || descriptor.items.size() > 255U) {
            error = "menu text supports only flags zero and at most 255 items";
            return false;
        }
        if (ram[slot + 6U] != descriptor.items.size()) {
            error = "menu slot item count does not match the descriptor";
            return false;
        }
        if (index >= descriptor.items.size()) {
            error = "menu item index lies outside the descriptor";
            return false;
        }
        std::uint16_t candidate_line = final_line != NULL ? *final_line : 0U;
        const MenuItem& item = descriptor.items[index];
        if (item.title_address == 0xfffffffeU) {
            error = "menu item drawing does not support separator items";
            return false;
        }
        if (!supported_callback(item.callback)) {
            error = "menu item event-5 callback is unsupported";
            return false;
        }
        if (!append_item(item, index, slot, head, current, resource, clip,
                         candidate, pending, error, &candidate_line, font,
                         stage_context)) {
            return false;
        }
        ram.swap(candidate);
        writes.swap(pending);
        if (final_line != NULL) {
            *final_line = candidate_line;
        }
    } catch (const std::bad_alloc&) {
        error = "cannot allocate menu text output";
        return false;
    }
    error.clear();
    return true;
}

bool draw_menu_text(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource, bool clip,
                    std::uint16_t initial_line,
                    std::vector<VideoPortWrite>& writes, std::string& error,
                    std::uint16_t* final_line,
                    const FixedDataResource* font,
                    const StageGroupMenuContext* stage_context) {
    bool covered = false;
    if (!menu_position_occluded(ram, 0x7000U, covered, error)) {
        return false;
    }
    const std::uint32_t head = read_u32(ram, 0x7f0eU);
    const std::uint32_t current = read_u32(ram, 0x7f12U);
    const std::size_t slot = current - 0x100000U;
    const unsigned int height = ram[slot + 4U];
    std::vector<VideoPortWrite> pending;
    if (height == 0U) {
        writes.swap(pending);
        if (final_line != NULL) {
            *final_line = initial_line;
        }
        error.clear();
        return true;
    }
    if (clip && read_u32(ram, 0x7f16U) != 0x3650U) {
        error = "clipped menu text requires the direct renderer at CPU 0x003650";
        return false;
    }
    MenuDescriptor descriptor;
    if (!decode_menu_descriptor(resource, read_u32(ram, slot), descriptor, error)) {
        return false;
    }
    if (descriptor.flags != 0U || descriptor.items.size() > 255U) {
        error = "menu text supports only flags zero and at most 255 items";
        return false;
    }
    if (ram[slot + 6U] != descriptor.items.size()) {
        error = "menu slot item count does not match the descriptor";
        return false;
    }
    if (descriptor.title_address == 0U) {
        error = "menu text requires a nonzero title address";
        return false;
    }
    for (std::size_t index = 0; index < descriptor.items.size(); ++index) {
        const MenuItem& item = descriptor.items[index];
        if (item.title_address == 0U || item.title_address == 0xfffffffeU) {
            error = "menu text does not support empty or separator items";
            return false;
        }
        if (!supported_callback(item.callback)) {
            error = "menu item event-5 callback is unsupported";
            return false;
        }
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::uint16_t pending_line = initial_line;
        std::uint16_t* line_output = &pending_line;
        std::vector<std::uint8_t> script;
        if (!script_at(resource, descriptor.title_address, script, error)) {
            return false;
        }
        FixedTextMeasure measurement;
        if (!measure_fixed_text(script, 0U, initial_line, measurement, error)) {
            return false;
        }
        const std::uint8_t center_byte = static_cast<std::uint8_t>(
            static_cast<unsigned int>(ram[slot + 11U]) - measurement.glyph_count);
        const int center = center_byte < 128U ? static_cast<int>(center_byte) :
                           static_cast<int>(center_byte) - 256;
        const int half = center >= 0 ? center / 2 : -((-center + 1) / 2);
        const std::uint8_t column = static_cast<std::uint8_t>(
            static_cast<int>(ram[slot + 9U]) + half);
        const std::uint16_t title_address = base_address(column, ram[slot + 10U]);
        const std::uint16_t title_style = head == current ? 0x0103U : 0x0603U;
        if (!append_text(script, title_address, title_style, clip, candidate,
                         pending, error, line_output)) {
            return false;
        }
        for (std::size_t index = 0; index < descriptor.items.size(); ++index) {
            candidate[slot + 8U] = static_cast<std::uint8_t>(index);
            if (!append_item(descriptor.items[index], index, slot, head, current,
                             resource, clip, candidate, pending, error,
                             line_output, font, stage_context)) {
                return false;
            }
        }
        ram.swap(candidate);
        writes.swap(pending);
        if (final_line != NULL) {
            *final_line = pending_line;
        }
    } catch (const std::bad_alloc&) {
        error = "cannot allocate menu text output";
        return false;
    }
    error.clear();
    return true;
}

} // namespace ms5
