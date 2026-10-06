#ifndef MS5_MENU_TEXT_H
#define MS5_MENU_TEXT_H

#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"

namespace ms5 {

// Confirmed CPU 0x009d3a current-item layout. The current slot's byte +8
// chooses the item and byte +7 chooses the selection. A row outside the
// visible height returns before descriptor or renderer validation. Visible
// rows support flags zero, ordinary or empty titles, known event-5 no-op
// callbacks, and debug callback 0x009aa8. Debug drawing requires font.
// Separators are rejected. clip requires the direct renderer at
// CPU 0x003650. Success replaces writes and clears error without changing
// RAM; failure preserves RAM and writes.
bool draw_menu_item(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource, bool clip,
                    std::vector<VideoPortWrite>& writes, std::string& error,
                    const FixedDataResource* font = NULL);

// Confirmed CPU 0x009e1a flags-zero menu layout. RAM maps CPU
// 0x100000..0x10ffff. Known event-5 no-op callbacks and debug callback
// 0x009aa8 are accepted; debug drawing requires font. clip selects per-glyph
// occlusion through RAM 0x107f16,
// which must name the direct 0x003650 renderer. initial_line supplies the
// title measurement's initial D3 word. Port writes preserve original order.
// Success replaces RAM and writes and clears error; failure preserves both.
// Height zero succeeds without decoding the resource or checking callbacks.
// Optional final_line receives the final D3 low word only on success. Each
// rendered title resets the line to its start address before stream controls;
// hidden items and event-5 no-ops preserve it. Height zero returns initial_line.
bool draw_menu_text(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource, bool clip,
                    std::uint16_t initial_line,
                    std::vector<VideoPortWrite>& writes, std::string& error,
                    std::uint16_t* final_line = NULL,
                    const FixedDataResource* font = NULL);

} // namespace ms5

#endif
