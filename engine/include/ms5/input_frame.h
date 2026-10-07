#ifndef MS5_INPUT_FRAME_H
#define MS5_INPUT_FRAME_H
#include "ms5/input_status.h"
namespace ms5 {
struct InputFrameResult {
    std::uint32_t next_pc, callback, callback_context;
    std::uint16_t style;
    std::uint8_t read_count;
    InputFrameResult() : next_pc(0), callback(0), callback_context(0), style(0), read_count(0) {}
};
// f12 through the branch before f54 or f3c. Callback context is a native address,
// not a host pointer. Does not execute a callback or model the external stack.
// Failure preserves RAM/result. D1.word is propagated for later text rendering.
bool begin_input_frame(std::vector<std::uint8_t>& ram,const FixedDataResource& streams,
                       const FixedDataResource& table,const InputPortSamples& ports,
                       std::uint32_t object_address,std::uint16_t initial_style,
                       InputFrameResult& result,std::string& error);
}
#endif
