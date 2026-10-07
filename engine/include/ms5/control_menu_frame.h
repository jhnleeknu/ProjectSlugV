#ifndef MS5_CONTROL_MENU_FRAME_H
#define MS5_CONTROL_MENU_FRAME_H
#include "ms5/menu_frame.h"
namespace ms5 {
// CPU92fc for an already open controller menu. Incoming A1 is the global
// menu renderer; initial_style/line are D1/D3 words. Valid native modes0..2.
// entry_stack is controller A7; a370 receives entry_stack-4.
// A BIOS jump bypasses the controller tail. Nonzero exit callbacks fail.
// Optional full D1/D3 must match the initial style/line low words.
// Success replaces outputs; failure preserves RAM/result/writes/registers.
bool step_control_menu(std::vector<std::uint8_t>& ram,
                       const FixedDataResource& menu,const FixedDataResource& pause,
                       std::uint16_t initial_style,std::uint16_t initial_line,
                       std::uint32_t entry_stack,MenuFrameResult& result,
                       std::vector<VideoPortWrite>& writes,std::string& error,
                       const FixedDataResource* font = NULL,
                       const StageGroupMenuContext* stage_context = NULL,
                         std::uint32_t* d1 = NULL,std::uint32_t* d3 = NULL);
}
#endif
