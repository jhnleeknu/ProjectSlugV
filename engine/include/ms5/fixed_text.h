#ifndef MS5_FIXED_TEXT_H
#define MS5_FIXED_TEXT_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "ms5/video_port.h"

namespace ms5 {

struct FixedWrite {
    std::uint16_t address;
    std::uint16_t value;
};

struct FixedTextMeasure {
    std::uint16_t glyph_count;
    std::uint16_t style;
    std::uint16_t line;
    std::size_t consumed_bytes;

    FixedTextMeasure() : glyph_count(0), style(0), line(0), consumed_bytes(0) {}
};

// CPU 0x0038e8 counts nonzero glyphs returned by the 0x00386e stream parser.
// The count wraps at 16 bits. Measurement accepts all glyph bytes and fonts;
// it does not render. consumed_bytes includes controls and the first returned
// zero terminator. Success replaces measurement and clears error; failure
// preserves measurement. line is a VRAM word address, not a CPU address.
bool measure_fixed_text(const std::vector<std::uint8_t>& script,
                        std::uint16_t initial_style,
                        std::uint16_t initial_line,
                        FixedTextMeasure& measurement,
                        std::string& error);

// Confirmed ASCII/font-0x61 subset of the text stream at CPU 0x00386e,
// 0x003918 and 0x0e84c8. This is not a general text engine. Addresses are
// VRAM word addresses, not CPU addresses or ROM offsets. Other font paths
// and glyphs >= 0x80 are unsupported. A successful trace replaces writes;
// on failure writes is unchanged. Bytes after the first terminator are ignored.
bool trace_fixed_text(const std::vector<std::uint8_t>& script,
                      std::uint16_t initial_address,
                      std::uint16_t initial_style,
                      std::vector<FixedWrite>& writes,
                      std::string& error);

// Direct text output from CPU 0x003650 with the shared 0x00386e parser.
// Each nonzero glyph emits a long address/data write followed by a word
// address reset to 0x8200 at CPU port 0x3c0000. All glyphs and styles are
// accepted. Cursor and line are VRAM word addresses. Success replaces
// writes and clears error; failure preserves writes. The trace is bounded
// to 200000 port events and ignores bytes after the first terminator.
bool trace_direct_fixed_text(const std::vector<std::uint8_t>& script,
                             std::uint16_t initial_address,
                             std::uint16_t initial_style,
                             std::vector<VideoPortWrite>& writes,
                             std::string& error);

// Called for each nonzero glyph at its current VRAM word address. Returning
// false fails the trace; visible=false skips both port events and cursor advance.
typedef bool (*FixedTextVisibility)(std::uint16_t address, void* context,
                                    bool& visible, std::string& error);

// Uses the same control grammar and transactional output as the direct trace.
// Controls still update the cursor when glyphs are hidden. A null callback
// accepts every glyph. The event bound counts only emitted port events.
bool trace_direct_fixed_text_visible(const std::vector<std::uint8_t>& script,
                                     std::uint16_t initial_address,
                                     std::uint16_t initial_style,
                                     FixedTextVisibility visibility,
                                     void* context,
                                     std::vector<VideoPortWrite>& writes,
                                     std::string& error);

} // namespace ms5

#endif
