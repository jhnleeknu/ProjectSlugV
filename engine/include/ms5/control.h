#ifndef MS5_CONTROL_H
#define MS5_CONTROL_H
#include "ms5/menu_frame.h"
namespace ms5 {
// Original9136: inactive acceptance, active waiting and open-menu frames.
// RAM is the caller-owned 64KiB image at100000. Initial style/line are words;
// A1 equals global menu renderer when entering an already open menu.
// Resources and external entry_stack are validated only on paths using them.
// result.status is signed full D0; consumers must inspect its low byte.
// BIOS external_jump stops before firmware execution. Existing component
// limits (native menu modes/descriptors and no nonzero exit callback) apply.
// Optional full D1/D3 must match the initial style/line low words.
// Success replaces outputs; failure preserves RAM/result/writes/registers.
bool step_control(std::vector<std::uint8_t>& ram,
                  const FixedDataResource& menu,const FixedDataResource& pause,
                  std::uint16_t initial_style,std::uint16_t initial_line,
                  std::uint32_t entry_stack,MenuFrameResult& result,
                  std::vector<VideoPortWrite>& writes,std::string& error,
                  const FixedDataResource* font = NULL,
                  const StageGroupMenuContext* stage_context = NULL,
                         std::uint32_t* d1 = NULL,std::uint32_t* d3 = NULL);
}
#endif
