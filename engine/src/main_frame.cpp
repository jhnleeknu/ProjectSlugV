#include "ms5/main_frame.h"
#include "ms5/formatted_text.h"
#include <new>
namespace ms5 {
bool step_main_frame(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& streams,const FixedDataResource& table,
                     const FixedDataResource& menu,const FixedDataResource& pause,
                     const FixedDataResource& debug,
                     const std::vector<PaletteRecord>& records,const InputPortSamples& ports,
                     std::uint16_t video,std::uint32_t entry_stack,
                     MainFrameState& state,InputFrameResult& result,
                     std::vector<VideoPortWrite>& writes,std::string& error,
                     const FixedDataResource* font,
                     const StageGroupMenuContext* stage_context) {
    if(state.next_pc!=0xec4U && state.next_pc!=0xef2U &&
       state.next_pc!=0xf12U && state.next_pc!=0xf4cU) {
        error="main frame requires a supported resume boundary";return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        MainFrameState next=state;
        InputFrameResult outcome;
        std::vector<VideoPortWrite> pending,frame_writes;
        if(next.next_pc==0xec4U) {
            if(!step_main_debug(candidate,debug,next.object_address,next.d1,
                                pending,error,NULL,&next.d3))return false;
            next.next_pc=0xef2U;
        }
        const std::uint16_t style=static_cast<std::uint16_t>(next.d1);
        const std::uint16_t line=static_cast<std::uint16_t>(next.d3);
        bool succeeded=false;
        if(next.next_pc==0xef2U) {
            succeeded=poll_input_control(candidate,streams,table,menu,pause,records,ports,
                video,next.object_address,style,line,entry_stack,outcome,frame_writes,error,
                font,stage_context,&next.d1,&next.d3);
        } else if(next.next_pc==0xf4cU) {
            succeeded=poll_callback_input_control(candidate,streams,table,menu,pause,records,ports,
                next.object_address,style,line,entry_stack,outcome,frame_writes,error,
                font,stage_context,&next.d1,&next.d3);
        } else {
            succeeded=step_input_control(candidate,streams,table,menu,pause,records,ports,
                next.object_address,style,line,entry_stack,outcome,frame_writes,error,
                font,stage_context,&next.d1,&next.d3);
        }
        if(!succeeded)return false;
        pending.insert(pending.end(),frame_writes.begin(),frame_writes.end());
        next.next_pc=outcome.next_pc;
        ram.swap(candidate);writes.swap(pending);state=next;result=outcome;
    } catch(const std::bad_alloc&) {
        error="cannot allocate main frame state";return false;
    }
    error.clear();return true;
}
}
