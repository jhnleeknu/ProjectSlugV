#include "ms5/control_menu_frame.h"
#include "ms5/control_finish.h"
#include <new>
namespace ms5 {
bool step_control_menu(std::vector<std::uint8_t>& ram,
                       const FixedDataResource& menu,const FixedDataResource& pause,
                       std::uint16_t initial_style,std::uint16_t initial_line,
                       std::uint32_t entry_stack,MenuFrameResult& result,
                       std::vector<VideoPortWrite>& writes,std::string& error,
                       const FixedDataResource* font,
                       const StageGroupMenuContext* stage_context) {
    if(ram.size()!=65536U || ram[0x7df0]==0 || ram[0x7dee]==0 || ram[0x7f1b]>2) {
        error="control menu frame requires an active open menu and native mode0..2";return false;
    }
    if((entry_stack&1U)!=0 || entry_stack<0x110104U || entry_stack>0xfffffcU) {
        error="control menu frame requires an even external diagnostic stack";return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        MenuFrameResult outcome;
        if(!step_menu_frame(candidate,menu,initial_line,entry_stack-4U,outcome,pending,error,font,stage_context))return false;
        if(outcome.external_jump==0) {
            // In modes0..2 a370 returns -1 only for an empty stack or after
            // popping the sole zero-height root. Neither path changes D1.
            // Every other returning path has D0=0, so the tail ignores D1.
            std::vector<VideoPortWrite> tail;
            if(!finish_control_menu(candidate,pause,static_cast<std::uint32_t>(outcome.status),
                                    initial_style,outcome.line,outcome,tail,error))return false;
            pending.insert(pending.end(),tail.begin(),tail.end());
        }
        ram.swap(candidate);writes.swap(pending);result=outcome;
    } catch(const std::bad_alloc&) {error="cannot allocate control menu frame state";return false;}
    error.clear();return true;
}
}
