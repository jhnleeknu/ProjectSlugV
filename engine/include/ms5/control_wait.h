#ifndef MS5_CONTROL_WAIT_H
#define MS5_CONTROL_WAIT_H
#include "ms5/menu_frame.h"
namespace ms5 {
// CPU9136 active state with RAM7df0!=0 and RAM7dee==0. Selects a new menu,
// one-step/repeat response or pause display, then executes common92a8 tail.
// initial_style is incoming D1 word; initial_line is incoming D3 word.
// result.status preserves signed D0, including the last glyph in its upper
// word after idle drawing. Only its low byte is the caller's status (0/2).
// Menu entry uses the same original entry_stack. RAM and all outputs are
// transactional; the already-open menu/exit callback path is a separate stage.
// Optional D1/D3 return full registers and are preserved on failure.
// D3 low word must match initial_line; wait D1 low word must match initial_style.
bool step_control_wait(std::vector<std::uint8_t>& ram,
                       const FixedDataResource& menu,const FixedDataResource& pause,
                       std::uint16_t initial_style,std::uint16_t initial_line,
                       std::uint32_t entry_stack,MenuFrameResult& result,
                       std::vector<VideoPortWrite>& writes,std::string& error,
                       std::uint32_t* d1 = NULL, std::uint32_t* d3 = NULL);
}
#endif
