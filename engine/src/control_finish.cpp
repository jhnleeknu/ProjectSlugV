#include "ms5/control_finish.h"
#include "ms5/fixed_text.h"
#include <new>
namespace ms5 {
bool finish_control_menu(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& pause,
                         std::uint32_t frame_d0, std::uint16_t frame_style,
                         std::uint16_t frame_line, MenuFrameResult& result,
                         std::vector<VideoPortWrite>& writes, std::string& error) {
    if(ram.size()!=65536U) {
        error="control menu finish requires exactly 65536 RAM bytes";return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        MenuFrameResult outcome;outcome.line=frame_line;
        std::uint32_t d0=frame_d0;
        if((d0&255U)==0) {
            // 932a MOVE.W clears only the lower word.
            d0&=0xffff0000U;
        } else {
            candidate[0x7dee]=0;
            if(candidate[0x7df6]!=0 || candidate[0x7df7]!=0 ||
               candidate[0x7df8]!=0 || candidate[0x7df9]!=0) {
                error="control exit callback has not been reconstructed";return false;
            }
            if(candidate[0x7dfa]==0 && candidate[0x7dfb]==1) {
                const std::uint32_t address=0x9079U;
                if(pause.source_cpu_address!=pause.source_rom_offset || address<pause.source_cpu_address ||
                   address-pause.source_cpu_address>=pause.data.size()) {
                    error="control clear text is outside its fixed-ROM resource";return false;
                }
                const std::size_t offset=address-pause.source_cpu_address;
                const std::vector<std::uint8_t> script(pause.data.begin()+offset,pause.data.end());
                // 928e selects e84c8, not the menu's 9332 font remapper.
                // Native9079 selects direct font3, so no font table is read.
                if(!trace_table_fixed_text(script,static_cast<std::uint16_t>(d0),frame_style,
                                           pause,pending,error,&outcome.line))return false;
                candidate[0x7dee]=0;candidate[0x7df0]=0;d0=1;
            }
        }
        const std::uint8_t first=candidate[0x4caa],second=candidate[0x4cb0];
        candidate[0x4cab]=static_cast<std::uint8_t>(candidate[0x4cab]|((first^candidate[0x7dfc])&first));
        candidate[0x4cb1]=static_cast<std::uint8_t>(candidate[0x4cb1]|((second^candidate[0x7dfd])&second));
        candidate[0x7df3]=static_cast<std::uint8_t>(candidate[0x7df3]-1U);
        outcome.status=d0<=0x7fffffffU?static_cast<int>(d0):-1-static_cast<int>(~d0);
        ram.swap(candidate);writes.swap(pending);result=outcome;
    } catch(const std::bad_alloc&) {
        error="cannot allocate control menu finish state";return false;
    }
    error.clear();return true;
}
}
