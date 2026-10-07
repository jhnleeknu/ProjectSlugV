#ifndef MS5_INPUT_CONTROL_H
#define MS5_INPUT_CONTROL_H
#include "ms5/input_frame.h"
#include "ms5/control_caller_step.h"
namespace ms5 {
// f12 input prefix followed by f54 controller/caller when no callback is set.
// Callback branch stops before f3c; other boundaries follow step_control_caller.
// result.style is D1.word at the input boundary, not the final CPU D1 value.
// All failures preserve RAM, result and writes.
bool step_input_control(std::vector<std::uint8_t>& ram,
                        const FixedDataResource& streams,const FixedDataResource& table,
                        const FixedDataResource& menu,const FixedDataResource& pause,
                        const std::vector<PaletteRecord>& records,const InputPortSamples& ports,
                        std::uint32_t object_address,std::uint16_t initial_style,
                        std::uint16_t initial_line,std::uint32_t entry_stack,
                        InputFrameResult& result,std::vector<VideoPortWrite>& writes,
                        std::string& error,const FixedDataResource* font = NULL,
                        const StageGroupMenuContext* stage_context = NULL);
}
#endif
