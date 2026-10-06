#ifndef MS5_MENU_FRAME_H
#define MS5_MENU_FRAME_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
namespace ms5 {
struct StageGroupMenuContext;
struct MenuFrameResult {
    int status;
    std::uint32_t external_jump;
    std::uint16_t line;
    MenuFrameResult() : status(0), external_jump(0), line(0) {}
};
// One a370 frame for reconstructed native menu descriptors/callbacks.
// Incoming A1 is taken to equal RAM7f16 (3650 or9332); entry_stack is the
// original external diagnostic A7, not a host pointer. Context provides
// resources; its callback_stack is replaced by each actual call depth.
// Success replaces outputs. Failure preserves RAM/result/writes. A BIOS
// external_jump ends the frame before firmware execution.
bool step_menu_frame(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& resource,
                     std::uint16_t initial_line, std::uint32_t entry_stack,
                     MenuFrameResult& result, std::vector<VideoPortWrite>& writes,
                     std::string& error, const FixedDataResource* font = NULL,
                     const StageGroupMenuContext* stage_context = NULL);
}
#endif
