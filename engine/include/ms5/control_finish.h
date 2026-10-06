#ifndef MS5_CONTROL_FINISH_H
#define MS5_CONTROL_FINISH_H
#include "ms5/menu_frame.h"
namespace ms5 {
// CPU9302 after the menu frame has returned. Inputs are the actual returned
// D0, D1 word and D3 word, not the registers from before calling a370.
// A nonzero exit callback is currently unsupported when D0's low byte is
// nonzero. Do not call this after a frame's external BIOS jump.
// status preserves signed full D0; the controller caller tests its low byte.
// Success replaces outputs. Failure preserves RAM/result/writes.
bool finish_control_menu(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& pause,
                         std::uint32_t frame_d0, std::uint16_t frame_style,
                         std::uint16_t frame_line, MenuFrameResult& result,
                         std::vector<VideoPortWrite>& writes, std::string& error);
}
#endif
