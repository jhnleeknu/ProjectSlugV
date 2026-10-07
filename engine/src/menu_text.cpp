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
                 std::uint16_t* final_line, const FixedDataResource* font,
                 std::uint32_t renderer, std::uint32_t& d1, std::uint32_t& d3) {
    std::vector<VideoPortWrite> text_writes;
    std::uint32_t text_d3 = (d3 & 0xffff0000U) | address;
    if (renderer == 0x9332U) {
        if (font == NULL) {
            error = "menu renderer CPU0x009332 requires the font resource";
            return false;
        }
        if (font->source_cpu_address >= 0x100000U ||
            font->source_cpu_address != font->source_rom_offset || font->data.empty() ||
            font->data.size() > 0x100000U - font->source_cpu_address) {
            error = "menu font resource must be a nonempty fixed-ROM range with matching CPU/ROM addresses";
            return false;
        }
        std::size_t position = 0;
        std::uint16_t line = address;
        std::uint16_t cursor = address;
        bool line_reset = false;
        for (;;) {
            std::uint8_t glyph = 0;
            if (!parse_fixed_text_glyph(script, position, style, line, cursor,
                                         glyph, error, &line_reset)) {
                return false;
            }
            text_d3 = (line_reset ? 0U : (text_d3 & 0xffff0000U)) | line;
            if (glyph == 0U) {
                if (final_line != NULL) *final_line = line;
                break;
            }
            if (clip) {
                bool visible = false;
                if (!glyph_visible(cursor, &ram, visible, error)) return false;
                // a008 returns immediately for covered glyphs, preserving D1,
                // renderer lookahead and D0's cursor for the next parser call.
                if (!visible) continue;
            }
            // 9332 changes D1 itself;3918 preserves that change next iteration.
            if ((style & 0xffU) == 3U) {
                style = static_cast<std::uint16_t>((style & 0xff00U) | 0x6bU);
            }
            std::vector<VideoPortWrite> glyph_writes;
            if (!render_table_text_glyph(glyph, script, position, cursor, style,
                                          *font, glyph_writes, error)) {
                return false;
            }
            if (glyph_writes.size() > 100000U - text_writes.size()) {
                error = "menu text trace exceeds 100000 port events";
                return false;
            }
            text_writes.insert(text_writes.end(), glyph_writes.begin(), glyph_writes.end());
        }
    } else {
        if (!trace_direct_fixed_text_visible(script, address, style,
                clip ? glyph_visible : NULL, &ram, text_writes, error, &style, &text_d3)) {
            return false;
        }
        if (final_line != NULL) *final_line = static_cast<std::uint16_t>(text_d3);
    }
    d1 = (d1 & 0xffff0000U) | style;
    d3 = text_d3;
    writes.insert(writes.end(), text_writes.begin(), text_writes.end());
    return true;
}

bool append_item(const MenuItem& item, std::size_t index,
                 std::size_t slot, std::uint32_t head, std::uint32_t current,
                 const FixedDataResource& resource, bool clip,
                 std::vector<std::uint8_t>& ram,
                 std::vector<VideoPortWrite>& writes, std::string& error,
                 std::uint16_t* final_line, const FixedDataResource* font,
                 const StageGroupMenuContext* stage_context,
                 std::uint32_t renderer, std::uint32_t& d1, std::uint32_t& d3) {
    const std::uint8_t row = static_cast<std::uint8_t>(index + 1U);
    d1 = (d1 & 0xffffff00U) | row;
    if (row >= ram[slot + 4U]) {
        return true;
    }
    d1 = 0U;
    const std::uint8_t selected = ram[slot + 7U];
    std::uint16_t address = static_cast<std::uint16_t>(
        static_cast<unsigned int>(base_address(ram[slot + 9U],
                                                ram[slot + 10U])) + 0x20U);
    address = static_cast<std::uint16_t>((address & 0xff00U) |
        ((static_cast<unsigned int>(address) + row) & 0xffU));
    std::uint16_t line = static_cast<std::uint16_t>(d3);
    if (item.title_address == 0xfffffffeU) {
        // 9d86 subtracts width as a word; 9cd4 then decrements its low byte.
        // Width2 therefore emits256 cells, rather than an empty separator.
        if (ram[slot + 11U] >= 2U) {
            const unsigned int width = ram[slot + 11U];
            const unsigned int cells = width == 2U ? 256U : width - 2U;
            for (unsigned int column = 0; column < cells; ++column) {
                bool covered = false;
                if (!menu_position_occluded(ram, address, covered, error)) {
                    return false;
                }
                if (!covered) {
                    VideoPortWrite write;
                    write.address = 0x3c0000U;
                    write.size = 4U;
                    const std::uint16_t tile = column == 0U ? 0x0bf8U :
                        column + 1U == cells ? 0x0bfaU : 0x0bf9U;
                    write.value = (static_cast<std::uint32_t>(address) << 16) | tile;
                    writes.push_back(write);
                    // Covered cells do not advance the cursor in9cd4.
                    address = static_cast<std::uint16_t>(address + 0x20U);
                }
            }
        }
    } else {
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
        if (item.title_address != 0U) {
            std::vector<std::uint8_t> script;
            if (!script_at(resource, item.title_address, script, error)) {
                return false;
            }
            const std::uint16_t style = current != head && index != selected ?
                                       0x0603U : 0x0003U;
            d1 = (d1 & 0xffff0000U) | style;
            if (!append_text(script, address, style, clip, ram, writes, error,
                             &line, font, renderer, d1, d3)) {
                return false;
            }
        }
    }
    d1 = (d1 & 0xffff0000U) | item.argument;
    if (item.callback == 0x9aa8U || item.callback == 0x9602U ||
        item.callback == 0x9802U) {
        std::uint32_t a2 = current;
        std::vector<VideoPortWrite> ports;
        if (item.callback == 0x9aa8U) {
            if (!dispatch_debug_menu(ram, resource, font, 5U, line, a2,
                                     ports, error, &d1, &d3)) {
                return false;
            }
        } else if (item.callback == 0x9602U) {
            if (!dispatch_stage_area_menu(ram, resource, font, stage_context,
                                          5U, line, a2, ports, error, &d1, &d3)) {
                return false;
            }
        } else {
            if (!dispatch_stage_group_menu(ram, resource, font, stage_context,
                                           5U, a2, ports, error, &d1, &d3)) {
                return false;
            }
            line = static_cast<std::uint16_t>(d3);
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
                    std::uint16_t* final_line,
                    std::uint32_t* d1, std::uint32_t* d3) {
    if (d3 != NULL && final_line != NULL && static_cast<std::uint16_t>(*d3) != *final_line) {
        error = "menu item final_line must match incoming D3 low word";
        return false;
    }
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
        if (d1 != NULL) *d1 = (*d1 & 0xffffff00U) | row;
        writes.swap(pending);
        error.clear();
        return true;
    }
    const std::uint32_t effective_renderer = clip ? read_u32(ram, 0x7f16U) : 0x3650U;
    if (effective_renderer != 0x3650U && effective_renderer != 0x9332U) {
        error = "menu text renderer must be CPU0x003650 or CPU0x009332";
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
        std::uint32_t candidate_d1 = d1 != NULL ? *d1 : 0U;
        std::uint32_t candidate_d3 = d3 != NULL ? *d3 :
            (final_line != NULL ? *final_line : 0U);
        std::uint16_t candidate_line = static_cast<std::uint16_t>(candidate_d3);
        const MenuItem& item = descriptor.items[index];
        if (!supported_callback(item.callback)) {
            error = "menu item event-5 callback is unsupported";
            return false;
        }
        if (!append_item(item, index, slot, head, current, resource, clip,
                         candidate, pending, error, &candidate_line, font,
                         stage_context, effective_renderer, candidate_d1, candidate_d3)) {
            return false;
        }
        ram.swap(candidate);
        writes.swap(pending);
        if (d1 != NULL) *d1 = candidate_d1;
        if (d3 != NULL) *d3 = candidate_d3;
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
                    const StageGroupMenuContext* stage_context,
                    std::uint32_t renderer, std::uint32_t* d1, std::uint32_t* d3) {
    if (d3 != NULL && static_cast<std::uint16_t>(*d3) != initial_line) {
        error = "menu text initial_line must match incoming D3 low word";
        return false;
    }
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
    const std::uint32_t effective_renderer = clip ? read_u32(ram, 0x7f16U) : renderer;
    if (effective_renderer != 0x3650U && effective_renderer != 0x9332U) {
        error = "menu text renderer must be CPU0x003650 or CPU0x009332";
        return false;
    }
    if (effective_renderer == 0x9332U && font == NULL) {
        error = "menu renderer CPU0x009332 requires the font resource";
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
        if (item.title_address == 0U) {
            error = "menu text does not support empty items";
            return false;
        }
        if (!supported_callback(item.callback)) {
            error = "menu item event-5 callback is unsupported";
            return false;
        }
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::uint32_t pending_d1 = d1 != NULL ? *d1 : 0U;
        std::uint32_t pending_d3 = d3 != NULL ? *d3 : initial_line;
        std::uint16_t pending_line = initial_line;
        std::uint16_t* line_output = &pending_line;
        std::vector<std::uint8_t> script;
        if (!script_at(resource, descriptor.title_address, script, error)) {
            return false;
        }
        FixedTextMeasure measurement;
        if (!measure_fixed_text(script, static_cast<std::uint16_t>(pending_d1), initial_line, measurement, error)) {
            return false;
        }
        pending_d3 = (measurement.line_reset ? 0U : (pending_d3 & 0xffff0000U)) | measurement.line;
        const std::uint8_t center_byte = static_cast<std::uint8_t>(
            static_cast<unsigned int>(ram[slot + 11U]) - measurement.glyph_count);
        const int center = center_byte < 128U ? static_cast<int>(center_byte) :
                           static_cast<int>(center_byte) - 256;
        const int half = center >= 0 ? center / 2 : -((-center + 1) / 2);
        const std::uint8_t column = static_cast<std::uint8_t>(
            static_cast<int>(ram[slot + 9U]) + half);
        const std::uint16_t title_address = base_address(column, ram[slot + 10U]);
        const std::uint16_t title_style = head == current ? 0x0103U : 0x0603U;
        pending_d1 = (pending_d1 & 0xffff0000U) | title_style;
        if (!append_text(script, title_address, title_style, clip, candidate,
                         pending, error, line_output, font, effective_renderer, pending_d1, pending_d3)) {
            return false;
        }
        for (std::size_t index = 0; index < descriptor.items.size(); ++index) {
            candidate[slot + 8U] = static_cast<std::uint8_t>(index);
            if (!append_item(descriptor.items[index], index, slot, head, current,
                             resource, clip, candidate, pending, error,
                             line_output, font, stage_context, effective_renderer, pending_d1, pending_d3)) {
                return false;
            }
        }
        ram.swap(candidate);
        writes.swap(pending);
        if (d1 != NULL) *d1 = pending_d1;
        if (d3 != NULL) *d3 = pending_d3;
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
