#include "ms5/control.h"
#include "ms5/control_activation.h"
#include "ms5/control_wait.h"
#include "ms5/control_menu_frame.h"
namespace ms5 {
bool step_control(std::vector<std::uint8_t>& ram,
                  const FixedDataResource& menu,const FixedDataResource& pause,
                  std::uint16_t initial_style,std::uint16_t initial_line,
                  std::uint32_t entry_stack,MenuFrameResult& result,
                  std::vector<VideoPortWrite>& writes,std::string& error,
                  const FixedDataResource* font,
                  const StageGroupMenuContext* stage_context) {
    if(ram.size()!=65536U) {error="control requires exactly 65536 RAM bytes";return false;}
    if(ram[0x7df0]==0) {
        std::uint8_t status=0;
        if(!activate_control(ram,status,error))return false;
        MenuFrameResult outcome;outcome.status=status;outcome.line=initial_line;
        result=outcome;writes.clear();return true;
    }
    if(ram[0x7dee]==0)
        return step_control_wait(ram,menu,pause,initial_style,initial_line,entry_stack,result,writes,error);
    return step_control_menu(ram,menu,pause,initial_style,initial_line,entry_stack,result,writes,error,font,stage_context);
}
}
