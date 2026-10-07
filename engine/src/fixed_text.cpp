#include "ms5/fixed_text.h"

#include <cstddef>

namespace ms5 {
namespace {

// Shared control grammar; callers decide whether to count or render glyphs.
bool next_text_glyph(const std::vector<std::uint8_t>& script,
                     std::size_t& position, std::uint16_t& style,
                     std::uint16_t& line, std::uint16_t& cursor,
                     std::uint8_t& glyph, std::string& error,
                     bool* line_reset = NULL) {
    while (position < script.size()) {
        glyph = script[position++];
        if (glyph == 0x5cU) {
            if (position == script.size()) {
                error = "missing text escape operand";
                return false;
            }
            glyph = script[position++];
            if (glyph == 'c' || glyph == 'p') {
                if (position == script.size()) {
                    error = "missing text style operand";
                    return false;
                }
                const std::uint8_t operand = script[position++];
                if (glyph == 'c') {
                    style = static_cast<std::uint16_t>((style & 0xff00U) | operand);
                } else {
                    style = static_cast<std::uint16_t>((style & 0x00ffU) |
                              ((static_cast<unsigned int>(operand) & 0x0fU) << 8));
                }
                continue;
            }
            if (glyph == 'l') {
                if (script.size() - position < 2) {
                    error = "missing text location operands";
                    return false;
                }
                const unsigned int x = script[position++];
                const unsigned int y = script[position++];
                const unsigned int shifted = x << 5;
                // The original ADD.B only changes the low byte; carry is lost.
                line = static_cast<std::uint16_t>(0x7000U + (shifted & 0xff00U) +
                                                 ((shifted + y) & 0x00ffU));
                if (line >= 0x7500U) {
                    error = "unsupported text location trap (VRAM address >= 0x7500)";
                    return false;
                }
                cursor = line;
                if (line_reset != NULL) {
                    *line_reset = true;
                }
                continue;
            }
            if (glyph == 'n') {
                line = static_cast<std::uint16_t>(static_cast<unsigned int>(line) + 1U);
                if (line >= 0x7500U) {
                    error = "unsupported text newline trap (VRAM address >= 0x7500)";
                    return false;
                }
                cursor = line;
                continue;
            }
            if (glyph == 'r') {
                cursor = line;
                continue;
            }
            // An unknown escape emits its second byte as a glyph.
        }
        return true;
    }
    error = "missing text stream terminator";
    return false;
}

} // namespace

bool parse_fixed_text_glyph(const std::vector<std::uint8_t>& script,
                            std::size_t& position, std::uint16_t& style,
                            std::uint16_t& line, std::uint16_t& cursor,
                            std::uint8_t& glyph, std::string& error) {
    std::size_t pending_position = position;
    std::uint16_t pending_style = style;
    std::uint16_t pending_line = line;
    std::uint16_t pending_cursor = cursor;
    std::uint8_t pending_glyph = 0;
    if (!next_text_glyph(script, pending_position, pending_style, pending_line,
                         pending_cursor, pending_glyph, error)) {
        return false;
    }
    position = pending_position;
    style = pending_style;
    line = pending_line;
    cursor = pending_cursor;
    glyph = pending_glyph;
    error.clear();
    return true;
}

bool measure_fixed_text(const std::vector<std::uint8_t>& script,
                        std::uint16_t initial_style,
                        std::uint16_t initial_line,
                        FixedTextMeasure& measurement,
                        std::string& error) {
    FixedTextMeasure pending;
    pending.style = initial_style;
    pending.line = initial_line;
    std::uint16_t cursor = initial_line;
    for (;;) {
        std::uint8_t glyph = 0;
        if (!next_text_glyph(script, pending.consumed_bytes, pending.style,
                             pending.line, cursor, glyph, error, &pending.line_reset)) {
            return false;
        }
        if (glyph == 0) {
            measurement = pending;
            error.clear();
            return true;
        }
        pending.glyph_count = static_cast<std::uint16_t>(
            static_cast<unsigned int>(pending.glyph_count) + 1U);
    }
}

bool trace_fixed_text(const std::vector<std::uint8_t>& script,
                      std::uint16_t initial_address,
                      std::uint16_t initial_style,
                      std::vector<FixedWrite>& writes,
                      std::string& error) {
    std::vector<FixedWrite> pending;
    std::uint16_t cursor = initial_address;
    std::uint16_t line = initial_address;
    std::uint16_t style = initial_style;
    std::size_t position = 0;
    for (;;) {
        std::uint8_t glyph = 0;
        if (!next_text_glyph(script, position, style, line, cursor, glyph, error)) {
            return false;
        }
        if (glyph == 0) {
            writes.swap(pending);
            error.clear();
            return true;
        }
        if ((style & 0x00ffU) != 0x61U) {
            error = "unsupported text font: only style low byte 0x61 is confirmed";
            return false;
        }
        if (glyph >= 0x80U) {
            error = "unsupported text glyph: only ASCII bytes below 0x80 are confirmed";
            return false;
        }
        if (pending.size() >= 100000U) {
            error = "text trace exceeds 100000 writes";
            return false;
        }
        const std::uint16_t tile = static_cast<std::uint16_t>(
            ((static_cast<unsigned int>(style) << 4) & 0xf000U) | 0x0a00U |
            (((static_cast<unsigned int>(glyph) & 0xf0U) * 2U) & 0xffU) |
            (static_cast<unsigned int>(glyph) & 0x0fU));
        FixedWrite first;
        first.address = cursor;
        first.value = tile;
        pending.push_back(first);
        FixedWrite second;
        second.address = static_cast<std::uint16_t>(static_cast<unsigned int>(cursor) + 1U);
        second.value = static_cast<std::uint16_t>(static_cast<unsigned int>(tile) + 0x10U);
        pending.push_back(second);
        cursor = static_cast<std::uint16_t>(static_cast<unsigned int>(cursor) + 0x20U);
    }
}

bool trace_direct_fixed_text(const std::vector<std::uint8_t>& script,
                             std::uint16_t initial_address,
                             std::uint16_t initial_style,
                             std::vector<VideoPortWrite>& writes,
                             std::string& error,
                             std::uint16_t* final_style, std::uint32_t* d3) {
    return trace_direct_fixed_text_visible(script, initial_address, initial_style,
                                           NULL, NULL, writes, error, final_style, d3);
}

bool trace_direct_fixed_text_visible(const std::vector<std::uint8_t>& script,
                                     std::uint16_t initial_address,
                                     std::uint16_t initial_style,
                                     FixedTextVisibility visibility,
                                     void* context,
                                     std::vector<VideoPortWrite>& writes,
                                     std::string& error,
                                     std::uint16_t* final_style, std::uint32_t* d3) {
    std::vector<VideoPortWrite> pending;
    std::uint16_t cursor = initial_address;
    std::uint16_t line = initial_address;
    std::uint16_t style = initial_style;
    std::size_t position = 0;
    bool line_reset = false;
    for (;;) {
        std::uint8_t glyph = 0;
        if (!next_text_glyph(script, position, style, line, cursor, glyph, error, &line_reset)) {
            return false;
        }
        if (glyph == 0) {
            writes.swap(pending);
            if (final_style != NULL) { *final_style = style; }
            if (d3 != NULL) {
                *d3 = (line_reset ? 0U : (*d3 & 0xffff0000U)) | line;
            }
            error.clear();
            return true;
        }
        bool visible = true;
        if (visibility != NULL && !visibility(cursor, context, visible, error)) {
            return false;
        }
        if (!visible) {
            continue;
        }
        if (pending.size() >= 200000U) {
            error = "direct text trace exceeds 200000 port events";
            return false;
        }
        const std::uint32_t tile =
            ((static_cast<std::uint32_t>(style) & 0x0f00U) << 4) |
            ((static_cast<std::uint32_t>(style) & 0x000fU) << 8) |
            static_cast<std::uint32_t>(glyph);
        VideoPortWrite write;
        write.address = 0x3c0000U;
        write.value = (static_cast<std::uint32_t>(cursor) << 16) | tile;
        write.size = 4;
        pending.push_back(write);
        cursor = static_cast<std::uint16_t>(static_cast<unsigned int>(cursor) + 0x20U);
        write.value = 0x8200U;
        write.size = 2;
        pending.push_back(write);
    }
}

bool render_table_text_glyph(std::uint8_t glyph,
                             const std::vector<std::uint8_t>& script,
                             std::size_t& position, std::uint16_t& cursor,
                             std::uint16_t style, const FixedDataResource& font,
                             std::vector<VideoPortWrite>& writes,
                             std::string& error) {
    if (font.source_cpu_address >= 0x100000U ||
        font.source_cpu_address != font.source_rom_offset || font.data.empty() ||
        font.data.size() > 0x100000U - font.source_cpu_address) {
        error = "text font resource must be a nonempty fixed-ROM range with matching CPU/ROM addresses";
        return false;
    }
    std::size_t pending_position = position;
    std::uint16_t pending_cursor = cursor;
    std::vector<VideoPortWrite> pending;
    const unsigned int font_id = style & 0x00ffU;
    if (font_id < 0x10U) {
        // e84c8 jumps to 3650 before examining lookahead or '@'.
        VideoPortWrite write;
        write.address = 0x3c0000U;
        write.size = 4;
        write.value = (static_cast<std::uint32_t>(pending_cursor) << 16) |
                      ((static_cast<std::uint32_t>(style) & 0x0f00U) << 4) |
                      (font_id << 8) | glyph;
        pending.push_back(write);
        write.size = 2;
        write.value = 0x8200U;
        pending.push_back(write);
        pending_cursor = static_cast<std::uint16_t>(static_cast<unsigned int>(pending_cursor) + 0x20U);
        position = pending_position;
        cursor = pending_cursor;
        writes.swap(pending);
        error.clear();
        return true;
    }
    if (font_id != 0x6bU && font_id != 0x68U && font_id != 0x30U) {
        error = "unsupported table text font: supported fonts are 0x00..0x0f, 0x30, 0x68 and 0x6b";
        return false;
    }
    const std::uint32_t table_address = font_id == 0x68U ? 0x0e82c8U : 0x0e80c8U;
    if (font_id != 0x30U && (font.source_cpu_address > table_address ||
        font.data.size() < table_address + 512U - font.source_cpu_address)) {
        error = "text font resource does not contain the selected complete lookup table";
        return false;
    }
    const std::size_t table_offset = font_id == 0x30U ? 0U :
                                     table_address - font.source_cpu_address;
    // CPU 0x0e84d6 peeks before applying the font-specific '@' grammar.
    if (pending_position >= script.size()) {
        error = "missing table text glyph lookahead";
        return false;
    }
    const std::uint8_t mark = script[pending_position];
    if (mark == 0xdeU && glyph == 0xb3U) {
        ++pending_position;
        glyph = 0xe0U;
    } else if (mark == 0xdeU && glyph >= 0xb6U && glyph <= 0xc4U) {
        ++pending_position;
        glyph = static_cast<std::uint8_t>(static_cast<unsigned int>(glyph) + 0x2bU);
    } else if ((mark == 0xdeU || mark == 0xdfU) &&
               glyph >= 0xcaU && glyph <= 0xceU) {
        ++pending_position;
        glyph = static_cast<std::uint8_t>(
            0xf0U + 2U * (static_cast<unsigned int>(glyph) - 0xcaU) +
            (mark == 0xdfU ? 1U : 0U));
    }
    if (font_id == 0x30U) {
        // e8558 uses direct font3 after combining marks, before '@'.
        VideoPortWrite write;
        write.address = 0x3c0000U;
        write.size = 4;
        write.value = (static_cast<std::uint32_t>(pending_cursor) << 16) |
                      ((static_cast<std::uint32_t>(style) & 0x0f00U) << 4) |
                      0x300U | glyph;
        pending.push_back(write);
        write.size = 2;
        write.value = 0x8200U;
        pending.push_back(write);
        pending_cursor = static_cast<std::uint16_t>(static_cast<unsigned int>(pending_cursor) + 0x20U);
        position = pending_position;
        cursor = pending_cursor;
        writes.swap(pending);
        error.clear();
        return true;
    }
    if (glyph == 0x40U) {
        // The initial lookahead also establishes this operand is present.
        glyph = script[pending_position++];
        unsigned int selector = 0;
        bool selected = true;
        if (glyph == '.') {
            selector = 0;
        } else if (glyph == ':') {
            selector = 1;
        } else if (glyph == '~' || glyph == '-') {
            selector = 2;
        } else {
            selected = false;
        }
        if (selected || glyph == '`') {
            if (pending_position >= script.size()) {
                error = "missing table text '@' operand";
                return false;
            }
            glyph = script[pending_position++];
            if (selected) {
                unsigned int value = selector;
                bool mapped = true;
                if (glyph == 'a') {
                    value += 0;
                } else if (glyph == 'u') {
                    value += 3;
                } else if (glyph == 'e') {
                    value += 6;
                } else if (glyph == 'o') {
                    value += 8;
                } else {
                    mapped = false;
                }
                if (mapped) {
                    glyph = static_cast<std::uint8_t>(0x80U + value);
                }
            }
        }
    }
    const std::size_t offset = table_offset + 2U * static_cast<unsigned int>(glyph);
    const std::uint32_t tile =
        (static_cast<std::uint32_t>(font.data[offset]) << 8) |
        static_cast<std::uint32_t>(font.data[offset + 1]) |
        ((static_cast<std::uint32_t>(style) & 0x0f00U) << 4);
    VideoPortWrite write;
    write.address = 0x3c0000U;
    write.value = (static_cast<std::uint32_t>(pending_cursor) << 16) | tile;
    write.size = 4;
    pending.push_back(write);
    pending_cursor = static_cast<std::uint16_t>(static_cast<unsigned int>(pending_cursor) + 0x20U);
    position = pending_position;
    cursor = pending_cursor;
    writes.swap(pending);
    error.clear();
    return true;
}

bool trace_table_fixed_text(const std::vector<std::uint8_t>& script,
                            std::uint16_t initial_address,
                            std::uint16_t initial_style,
                            const FixedDataResource& font,
                            std::vector<VideoPortWrite>& writes,
                            std::string& error,
                            std::uint16_t* final_line, std::uint16_t* final_style,
                            std::uint32_t* d3) {
    if (font.source_cpu_address >= 0x100000U ||
        font.source_cpu_address != font.source_rom_offset || font.data.empty() ||
        font.data.size() > 0x100000U - font.source_cpu_address) {
        error = "text font resource must be a nonempty fixed-ROM range with matching CPU/ROM addresses";
        return false;
    }
    std::vector<VideoPortWrite> pending;
    std::uint16_t cursor = initial_address;
    std::uint16_t line = initial_address;
    std::uint16_t style = initial_style;
    std::size_t position = 0;
    bool line_reset = false;
    for (;;) {
        std::uint8_t glyph = 0;
        if (!next_text_glyph(script, position, style, line, cursor, glyph, error, &line_reset)) {
            return false;
        }
        if (glyph == 0) {
            writes.swap(pending);
            if (final_line != NULL) {
                *final_line = line;
            }
            if (final_style != NULL) {
                *final_style = style;
            }
            if (d3 != NULL) {
                *d3 = (line_reset ? 0U : (*d3 & 0xffff0000U)) | line;
            }
            error.clear();
            return true;
        }
        std::vector<VideoPortWrite> glyph_writes;
        if (!render_table_text_glyph(glyph, script, position, cursor, style,
                                      font, glyph_writes, error)) {
            return false;
        }
        if (glyph_writes.size() > 100000U - pending.size()) {
            error = "table text trace exceeds 100000 port events";
            return false;
        }
        pending.insert(pending.end(), glyph_writes.begin(), glyph_writes.end());
    }
}

} // namespace ms5
