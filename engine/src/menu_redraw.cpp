#include "ms5/menu_redraw.h"
#include "ms5/menu_border.h"
#include "ms5/menu_text.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t read_u32(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) |
           (static_cast<std::uint32_t>(ram[at+1U]) << 16) |
           (static_cast<std::uint32_t>(ram[at+2U]) << 8) | ram[at+3U];
}
void put_u32(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    for (unsigned int i=0; i<4U; ++i) {
        ram[at+i]=static_cast<std::uint8_t>(value >> (24U-i*8U));
    }
}
bool aligned_slot(std::uint32_t address) {
    return address>=0x107e0eU && address<=0x107f0eU &&
           (address-0x107e0eU)%16U==0U;
}
}
bool redraw_menu_stack(std::vector<std::uint8_t>& ram,
                       const FixedDataResource& resource,
                       std::uint32_t last_slot, std::uint16_t initial_line,
                       std::vector<VideoPortWrite>& writes, std::string& error,
                       const FixedDataResource* font,
                       const StageGroupMenuContext* stage_context,
                       std::uint16_t* final_line,std::uint32_t* d1,std::uint32_t* d3) {
    if(d3!=NULL && static_cast<std::uint16_t>(*d3)!=initial_line) {
        error="menu redraw line must match D3 low word";return false;
    }
    if (ram.size()!=65536U) {
        error="menu redraw requires exactly 65536 RAM bytes";
        return false;
    }
    const std::uint32_t head=read_u32(ram,0x7f0eU);
    if (!aligned_slot(head) || !aligned_slot(last_slot) || head>last_slot) {
        error="menu redraw requires aligned allocated slots or an empty range";
        return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        std::uint16_t line=initial_line;
        std::uint32_t pending_d1=d1!=NULL?*d1:0U;
        std::uint32_t pending_d3=d3!=NULL?*d3:initial_line;
        for (std::uint32_t current=0x107efeU; current>=last_slot; current-=16U) {
            put_u32(candidate,0x7f12U,current);
            std::vector<FixedWrite> border;
            if (!trace_menu_border(candidate,resource,border,error,&pending_d3)) return false;
            for (std::size_t i=0; i<border.size(); ++i) {
                VideoPortWrite write;
                write.address=0x3c0000U;write.size=4U;
                write.value=(static_cast<std::uint32_t>(border[i].address)<<16)|border[i].value;
                pending.push_back(write);
            }
            line=static_cast<std::uint16_t>(pending_d3);
            std::vector<VideoPortWrite> text;
            if (!draw_menu_text(candidate,resource,true,line,text,error,&line,font,stage_context,0x3650U,&pending_d1,&pending_d3)) {
                return false;
            }
            pending.insert(pending.end(),text.begin(),text.end());
        }
        ram.swap(candidate);writes.swap(pending);
        if (final_line!=NULL) *final_line=line;
        if(d1!=NULL)*d1=pending_d1;
        if(d3!=NULL)*d3=pending_d3;
    } catch (const std::bad_alloc&) {
        error="cannot allocate menu redraw output";
        return false;
    }
    error.clear();return true;
}
}
