#ifndef MS5_MENU_TEXT_H
#define MS5_MENU_TEXT_H

#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"

namespace ms5 {

struct StageGroupMenuContext;

// Confirmed CPU 0x009d3a current-item layout. The current slot's byte +8
// chooses the item and byte +7 chooses the selection. A row outside the
// visible height returns before descriptor or renderer validation. Visible
// rows support flags zero, ordinary or empty titles, known event-5 no-op
// callbacks, debug callback 0x009aa8, and stage callbacks 0x009602 /
// 0x009802. Dynamic drawing requires font and stage drawing requires context.
// Separators use the original9cd4 tiles and unconditional occlusion. clip
// selects RAM0x107f16 renderer3650 or9332;9332 requires font.
// Success replaces RAM and writes and clears error; failure
// preserves both. Optional final_line receives D3 only on success; hidden
// rows preserve its input value. Optional full D1/D3 outputs are transactional;
// final_line must match incoming D3.low when both are supplied. With no
// final_line, incoming D3 supplies its initial word. Hidden rows replace only
// D1.byte with index+1; visible rows clear D1 then pass item.argument in D1.word.
bool draw_menu_item(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource, bool clip,
                    std::vector<VideoPortWrite>& writes, std::string& error,
                    const FixedDataResource* font = NULL,
                    const StageGroupMenuContext* stage_context = NULL,
                    std::uint16_t* final_line = NULL,
                    std::uint32_t* d1 = NULL, std::uint32_t* d3 = NULL);

// Confirmed CPU 0x009e1a flags-zero menu layout. RAM maps CPU
// 0x100000..0x10ffff. Known event-5 no-op callbacks and debug callback
// 0x009aa8 and stage callbacks 0x009602 / 0x009802 are accepted. Dynamic
// drawing requires font and stage drawing requires context. clip selects
// per-glyph occlusion through RAM 0x107f16,
// which must name renderer0x003650 or0x009332. initial_line supplies the
// title measurement's initial D3 word. Port writes preserve original order.
// Success replaces RAM and writes and clears error; failure preserves both.
// Height zero succeeds without decoding the resource or checking callbacks.
// Unclipped renderer supports CPU3650 or9332;9332 requires font and maps
// style low byte3 to6b, retaining that style until another stream control.
// clip selects RAM0x107f16 regardless of renderer argument. Covered glyphs
// preserve the cursor and skip renderer style changes and lookahead consumption.
// Optional final_line receives the final D3 low word only on success. Each
// rendered title resets the line to its start address before stream controls;
// hidden items and event-5 no-ops preserve it. Height zero returns initial_line.
// Optional D1/D3 retain native word/byte write widths and commit only on success.
// initial_line must match incoming D3.low; height zero preserves both full regs.
// Location controls clear D3.high; other line controls preserve it.
bool draw_menu_text(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource, bool clip,
                    std::uint16_t initial_line,
                    std::vector<VideoPortWrite>& writes, std::string& error,
                    std::uint16_t* final_line = NULL,
                    const FixedDataResource* font = NULL,
                    const StageGroupMenuContext* stage_context = NULL,
                    std::uint32_t renderer = 0x3650U,
                    std::uint32_t* d1 = NULL, std::uint32_t* d3 = NULL);

} // namespace ms5

#endif
