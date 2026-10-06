#include "ms5/fixed_text.h"

#include <cstddef>

namespace ms5 {
namespace {

// Shared control grammar; callers decide whether to count or render glyphs.
bool next_text_glyph(const std::vector<std::uint8_t>& script,
                     std::size_t& position, std::uint16_t& style,
                     std::uint16_t& line, std::uint16_t& cursor,
                     std::uint8_t& glyph, std::string& error) {
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
                             pending.line, cursor, glyph, error)) {
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
                             std::string& error) {
    std::vector<VideoPortWrite> pending;
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

} // namespace ms5
