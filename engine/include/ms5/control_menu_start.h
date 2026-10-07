#ifndef MS5_CONTROL_MENU_START_H
#define MS5_CONTROL_MENU_START_H
#include "ms5/menu_frame.h"
namespace ms5 {
// Original92ce: prepare video area, enter native root menu, install9332,
// execute its first opening frame, then collect input edges through92a8.
// Entry stack is external original A7; first a370 call uses entry_stack-4.
// This entry assumes the caller already accepted a menu request. It does
// not implement the active9136 controller or menu-exit indirect callback.
// Failure preserves all outputs. Input ROM resource is caller-owned MS5D.
// Optional D1/D3 return full registers and are preserved on failure.
// D3 low word must match initial_line. Native ca9e clears all of D1.
// The root descriptor must have a nonzero opening target height.
bool start_control_menu(std::vector<std::uint8_t>& ram,
                        const FixedDataResource& menu,
                        std::uint16_t initial_line, std::uint32_t entry_stack,
                        MenuFrameResult& result,
                        std::vector<VideoPortWrite>& writes, std::string& error,
                       std::uint32_t* d1 = NULL, std::uint32_t* d3 = NULL);
}
#endif
