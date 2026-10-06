#include "ms5/control_wait.h"
#include "ms5/control_request.h"
#include "ms5/control_menu_start.h"
#include "ms5/fixed_text.h"
#include <new>
namespace ms5 {
bool step_control_wait(std::vector<std::uint8_t>& ram,
                       const FixedDataResource& menu,const FixedDataResource& pause,
                       std::uint16_t initial_style,std::uint16_t initial_line,
                       std::uint32_t entry_stack,MenuFrameResult& result,
                       std::vector<VideoPortWrite>& writes,std::string& error) {
    if(ram.size()!=65536U) {error="control wait requires exactly 65536 RAM bytes";return false;}
    if(ram[0x7df0]==0 || ram[0x7dee]!=0) {
        error="control wait requires active control without an open menu";return false;
    }
    std::uint8_t request=0;
    if(!read_control_request(ram,request,error))return false;
    // Preserve the original player-by-player priority: player1 step/hold
    // wins even over a simultaneous player2 menu request.
    unsigned int action=0; // 0 idle,1 new step,2 held step,3 open menu.
    for(unsigned int player=0;player<2;++player) {
        if((ram[0x7df0]&(1U<<player))==0)continue;
        const unsigned int request_bit=2U<<(player*2U);
        const unsigned int step_bit=1U<<(player*2U);
        if((request&request_bit)!=0)action=3;
        else if(ram[0xf002]!=0 && (ram[0x4cb5]&step_bit)!=0)action=1;
        else if(ram[0xf002]!=0 && (ram[0x4cb4]&step_bit)!=0)action=2;
        if(action!=0)break;
    }
    if(action==3)return start_control_menu(ram,menu,initial_line,entry_stack,result,writes,error);
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        MenuFrameResult outcome;outcome.line=initial_line;
        if(action==1) {
            candidate[0x7df2]=15;outcome.status=2;
        } else if(action==2) {
            const std::uint8_t previous=candidate[0x7df2];
            candidate[0x7df2]=static_cast<std::uint8_t>(previous-1U);
            if(previous==0) {candidate[0x7df2]=1;outcome.status=2;}
        } else if((candidate[0xf001]&0x40U)==0) {
            candidate[0x7df3]=static_cast<std::uint8_t>(candidate[0x7df3]-1U);
            const std::uint32_t address=(candidate[0x7df3]&0x30U)!=0?0x9068U:0x9079U;
            if(pause.source_cpu_address!=pause.source_rom_offset || address<pause.source_cpu_address ||
               address-pause.source_cpu_address>=pause.data.size()) {
                error="pause text address is outside its fixed-ROM resource";return false;
            }
            const std::size_t offset=address-pause.source_cpu_address;
            const std::vector<std::uint8_t> script(pause.data.begin()+offset,pause.data.end());
            std::uint16_t style=initial_style;
            // 9086 changes only D1's low byte in this selector branch.
            if(candidate[0x12]==2 && candidate[0xfd82]!=0 && candidate[0xf002]!=0) {
                style=static_cast<std::uint16_t>((style&0xff00U)|(candidate[0x4cb4]&10U));
            }
            if(!trace_direct_fixed_text(script,request,style,pending,error))return false;
            FixedTextMeasure measurement;
            if(!measure_fixed_text(script,style,request,measurement,error))return false;
            outcome.line=measurement.line;
            // 3650 leaves the last tile word in D0's upper half;9256 clears
            // only its low word. Preserve this register value, not just the
            // low-byte status used by the original caller.
            for(std::size_t i=pending.size();i>0;--i) {
                if(pending[i-1].size==4) {
                    const unsigned int tile=pending[i-1].value&0xffffU;
                    const int signed_tile=tile>=0x8000U?static_cast<int>(tile)-65536:static_cast<int>(tile);
                    outcome.status=signed_tile*65536;
                    break;
                }
            }
        }
        const std::uint8_t first=candidate[0x4caa],second=candidate[0x4cb0];
        candidate[0x4cab]=static_cast<std::uint8_t>(candidate[0x4cab]|((first^candidate[0x7dfc])&first));
        candidate[0x4cb1]=static_cast<std::uint8_t>(candidate[0x4cb1]|((second^candidate[0x7dfd])&second));
        candidate[0x7df3]=static_cast<std::uint8_t>(candidate[0x7df3]-1U);
        ram.swap(candidate);writes.swap(pending);result=outcome;
    } catch(const std::bad_alloc&) {error="cannot allocate control wait state";return false;}
    error.clear();return true;
}
}
