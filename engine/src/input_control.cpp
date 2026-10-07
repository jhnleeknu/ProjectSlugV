#include "ms5/input_control.h"
#include <new>
namespace ms5 {
bool step_input_control(std::vector<std::uint8_t>& ram,
                        const FixedDataResource& streams,const FixedDataResource& table,
                        const FixedDataResource& menu,const FixedDataResource& pause,
                        const std::vector<PaletteRecord>& records,const InputPortSamples& ports,
                        std::uint32_t object_address,std::uint16_t initial_style,
                        std::uint16_t initial_line,std::uint32_t entry_stack,
                        InputFrameResult& result,std::vector<VideoPortWrite>& writes,
                        std::string& error,const FixedDataResource* font,
                        const StageGroupMenuContext* stage_context) {
    try {
        std::vector<std::uint8_t> candidate(ram);
        InputFrameResult outcome;
        std::vector<VideoPortWrite> pending;
        if(!begin_input_frame(candidate,streams,table,ports,object_address,initial_style,outcome,error)) return false;
        if(outcome.next_pc==0xf54U &&
           !step_control_caller(candidate,menu,pause,records,object_address,outcome.style,
                                initial_line,entry_stack,outcome.next_pc,pending,error,font,stage_context)) return false;
        ram.swap(candidate);writes.swap(pending);result=outcome;
    } catch(const std::bad_alloc&) {error="cannot allocate input/controller state";return false;}
    error.clear();return true;
}
}
