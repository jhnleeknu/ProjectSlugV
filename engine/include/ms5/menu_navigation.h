#ifndef MS5_MENU_NAVIGATION_H
#define MS5_MENU_NAVIGATION_H

#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"

namespace ms5 {

struct StageGroupMenuContext;

// CPU a216 (step) / a280 (explicit selection), followed by old/new row
// redraws. Direction is slot+15 bit1: set=previous, clear=next.
// Explicit selection clamps the requested byte before skipping disabled rows.
// Event 0 is queued in slot+14, not dispatched here. Rendering supports the
// draw_menu_item profile. Invalid slots and nonterminating searches fail.
// Failure preserves RAM, writes and final_line; success replaces outputs and
// clears error. Optional final_line tracks D3 across both row redraws.
// Full D1/D3 are carried across redraws; final_line must match D3.low16
// when both are supplied. All register outputs are preserved on error.
bool navigate_menu(std::vector<std::uint8_t>& ram,
                   const FixedDataResource& resource, bool explicit_selection,
                   std::uint8_t requested,
                   std::vector<VideoPortWrite>& writes, std::string& error,
                   const FixedDataResource* font = NULL,
                   const StageGroupMenuContext* stage_context = NULL,
                   std::uint16_t* final_line = NULL,
                   std::uint32_t* d1 = NULL, std::uint32_t* d3 = NULL);

} // namespace ms5
#endif
