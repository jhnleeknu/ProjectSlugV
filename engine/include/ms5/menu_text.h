#ifndef MS5_MENU_TEXT_H
#define MS5_MENU_TEXT_H

#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"

namespace ms5 {

// Confirmed CPU 0x009d3a current-item layout. The current slot's byte +8
// chooses the item and byte +7 chooses the selection. A row outside the
// visible height returns before descriptor or renderer validation. Visible
// rows support flags zero, ordinary or empty titles, and known event-5 no-op
// callbacks. Separators are rejected. clip requires the direct renderer at
// CPU 0x003650. Success replaces writes and clears error without changing
// RAM; failure preserves RAM and writes.
bool draw_menu_item(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource, bool clip,
                    std::vector<VideoPortWrite>& writes, std::string& error);

// Confirmed CPU 0x009e1a flags-zero menu layout. RAM maps CPU
// 0x100000..0x10ffff. Only event-5 callbacks confirmed to have no effects
// are accepted. clip selects per-glyph occlusion through RAM 0x107f16,
// which must name the direct 0x003650 renderer. initial_line supplies the
// title measurement's initial D1 word. Port writes preserve original order.
// Success replaces RAM and writes and clears error; failure preserves both.
// Height zero succeeds without decoding the resource or checking callbacks.
bool draw_menu_text(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource, bool clip,
                    std::uint16_t initial_line,
                    std::vector<VideoPortWrite>& writes, std::string& error);

} // namespace ms5

#endif
