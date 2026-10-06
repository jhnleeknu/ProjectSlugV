#ifndef MS5_MENU_REDRAW_H
#define MS5_MENU_REDRAW_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
namespace ms5 {
struct StageGroupMenuContext;
// CPU a6da: redraw oldest slot107efe down to last_slot, inclusive. The
// current pointer ends at last_slot; an empty range preserves it. A newer
// head may occlude the redrawn slots. Only aligned allocated slots are valid.
// Visible menus use the flags0/known-callback subset supported by menu_text.
// Context carries actual event5 entry A7 (a6da entry S minus28), unchanged.
// Failure preserves RAM, writes and optional final_line.
bool redraw_menu_stack(std::vector<std::uint8_t>& ram,
                       const FixedDataResource& resource,
                       std::uint32_t last_slot, std::uint16_t initial_line,
                       std::vector<VideoPortWrite>& writes, std::string& error,
                       const FixedDataResource* font = NULL,
                       const StageGroupMenuContext* stage_context = NULL,
                       std::uint16_t* final_line = NULL);
}
#endif
