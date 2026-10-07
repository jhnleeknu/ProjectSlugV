#include "ms5/control_caller_step.h"
#include <new>
namespace ms5 {
bool step_control_caller(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& menu,const FixedDataResource& pause,
                         const std::vector<PaletteRecord>& records,
                         std::uint32_t object_address,std::uint16_t initial_style,
                         std::uint16_t initial_line,std::uint32_t entry_stack,
                         std::uint32_t& next_pc,std::vector<VideoPortWrite>& writes,
                         std::string& error,const FixedDataResource* font,
                         const StageGroupMenuContext* stage_context) {
    if(ram.size()!=65536U || (object_address&1U)!=0 ||
       object_address<0x100000U || object_address>0x10ff7aU) {
        error="control caller step requires 64KiB RAM and an even complete object span";return false;
    }
    if((entry_stack&1U)!=0 || entry_stack<0x110108U || entry_stack>0xfffffcU) {
        error="control caller step requires an even external diagnostic stack";return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        MenuFrameResult control;
        if(!step_control(candidate,menu,pause,initial_style,initial_line,entry_stack-4U,
                         control,pending,error,font,stage_context))return false;
        std::uint32_t boundary=control.external_jump;
        if(boundary==0) {
            std::vector<VideoPortWrite> tail;
            if(!consume_control_result(candidate,records,object_address,
                static_cast<std::uint32_t>(control.status),boundary,tail,error))return false;
            pending.insert(pending.end(),tail.begin(),tail.end());
        }
        ram.swap(candidate);writes.swap(pending);next_pc=boundary;
    } catch(const std::bad_alloc&) {error="cannot allocate full control caller state";return false;}
    error.clear();return true;
}
}
