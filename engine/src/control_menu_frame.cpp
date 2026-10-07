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
                       const StageGroupMenuContext* stage_context,
                         std::uint32_t* d1,std::uint32_t* d3) {
    if ((d1 != NULL && (*d1 & 0xffffU) != initial_style) ||
        (d3 != NULL && (*d3 & 0xffffU) != initial_line)) {
        error="control register low words must match style and line";return false;
    }

    if(ram.size()!=65536U || ram[0x7df0]==0 || ram[0x7dee]==0 || ram[0x7f1b]>2) {
        error="control menu frame requires an active open menu and native mode0..2";return false;
    }
    if((entry_stack&1U)!=0 || entry_stack<0x110104U || entry_stack>0xfffffcU) {
        error="control menu frame requires an even external diagnostic stack";return false;
    }
    std::uint32_t pending_d1=d1==NULL?initial_style:*d1;
    std::uint32_t pending_d3=d3==NULL?initial_line:*d3;
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        MenuFrameResult outcome;
        if(!step_menu_frame(candidate,menu,initial_line,entry_stack-4U,outcome,pending,error,font,stage_context,&pending_d1,&pending_d3))return false;
        if(outcome.external_jump==0) {
            // The tail consumes the actual a370 return registers.
            std::vector<VideoPortWrite> tail;
            if(!finish_control_menu(candidate,pause,static_cast<std::uint32_t>(outcome.status),
                                    static_cast<std::uint16_t>(pending_d1),outcome.line,outcome,tail,error,&pending_d1,&pending_d3))return false;
            pending.insert(pending.end(),tail.begin(),tail.end());
        }
        ram.swap(candidate);writes.swap(pending);result=outcome;
    } catch(const std::bad_alloc&) {error="cannot allocate control menu frame state";return false;}
    if(d1!=NULL)*d1=pending_d1;
    if(d3!=NULL)*d3=pending_d3;
    error.clear();return true;
}
}
