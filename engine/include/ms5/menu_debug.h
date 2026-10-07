#ifndef MS5_MENU_DEBUG_H
#define MS5_MENU_DEBUG_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
namespace ms5 {
// CPU9aa8 debug flag event. event1/2/3 toggle the ROM-mapped bit and draw;
// event5 only draws; event4 requests close. Uses CPU9a98 mapping and the
// e80c8 font table supplied in a separate MS5D. line is D3 in/out, a2 is
// the resulting menu pointer. Failure preserves all outputs and RAM.
// Optional D1/D3 receive full native results; D3.lowword must match line.
// The callback context corresponds to the current slot, as established by9b3e.
bool dispatch_debug_menu(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& resource,
                         const FixedDataResource* font,
                         std::uint16_t event, std::uint16_t& line,
                         std::uint32_t& a2, std::vector<VideoPortWrite>& writes,
                         std::string& error,
                         std::uint32_t* d1 = NULL, std::uint32_t* d3 = NULL);
}
#endif
