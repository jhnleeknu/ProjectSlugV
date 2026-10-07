#include "ms5/menu_debug.h"
#include "ms5/menu_border.h"
#include "ms5/menu_descriptor.h"
#include "ms5/fixed_text.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t read_u32(const std::vector<std::uint8_t>& ram,std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at])<<24)|(static_cast<std::uint32_t>(ram[at+1])<<16)|
           (static_cast<std::uint32_t>(ram[at+2])<<8)|ram[at+3];
}
bool offset_at(const FixedDataResource& resource,std::uint32_t address,std::size_t& offset,std::string& error) {
    if (address<resource.source_cpu_address || address-resource.source_cpu_address>=resource.data.size()) {
        error="debug menu data lies outside the fixed resource";return false;
    }
    offset=address-resource.source_cpu_address;return true;
}
}
bool dispatch_debug_menu(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& resource,
                         const FixedDataResource* font,
                         std::uint16_t event,std::uint16_t& line,
                         std::uint32_t& a2,std::vector<VideoPortWrite>& writes,
                         std::string& error, std::uint32_t* d1, std::uint32_t* d3) {
    bool covered=false;
    if (!menu_position_occluded(ram,0x7000,covered,error)) return false;
    if (d3 != NULL && (*d3 & 0xffffU) != line) {
        error="debug menu D3 low word must match line";return false;
    }
    std::uint32_t pending_d3=d3 == NULL ? line : *d3;
    const std::uint32_t current=read_u32(ram,0x7f12);
    const std::uint32_t head=read_u32(ram,0x7f0e);
    const std::size_t slot=current-0x100000;
    std::vector<VideoPortWrite> pending;
    std::uint32_t result_a2=current;
    std::uint16_t result_line=line;
    const bool toggle=event==1 || event==2 || event==3;
    if (!toggle && event!=5) {
        if (event==4) {ram[0x7f1b]=2;result_a2=head;}
        writes.swap(pending);a2=result_a2;error.clear();return true;
    }
    if (font==NULL) {error="debug menu drawing requires the 6b font resource";return false;}
    MenuDescriptor descriptor;
    if (!decode_menu_descriptor(resource,read_u32(ram,slot),descriptor,error)) return false;
    const std::uint8_t row=ram[slot+8];
    if (row>=15 || row>=descriptor.items.size() || ram[slot+6]!=descriptor.items.size()) {
        error="debug menu row lies outside its 15-entry map";return false;
    }
    std::size_t map_offset=0;
    if (!offset_at(resource,0x9a98U+row,map_offset,error)) return false;
    if (resource.data[map_offset]>=16U) {
        error="debug bit map must name a bit in the 16-bit setting word";return false;
    }
    const unsigned int bit=resource.data[map_offset];
    std::uint16_t flags=static_cast<std::uint16_t>((ram[0xf000]<<8)|ram[0xf001]);
    if (toggle) flags=static_cast<std::uint16_t>(static_cast<std::uint32_t>(flags)^(UINT32_C(1)<<bit));
    const bool enabled=(static_cast<std::uint32_t>(flags)&(UINT32_C(1)<<bit))!=0;
    std::size_t text_offset=0;
    if (!offset_at(resource,enabled?0x99e3U:0x99e7U,text_offset,error)) return false;
    const unsigned int padding=(descriptor.flags&14U)!=0 ? 1U:3U;
    const std::uint8_t x=static_cast<std::uint8_t>(ram[slot+9]+padding);
    const std::uint8_t y=static_cast<std::uint8_t>(ram[slot+10]+1U+row);
    const unsigned int shifted=(static_cast<unsigned int>(x)+18U)<<5;
    const std::uint16_t address=static_cast<std::uint16_t>(0x7000U+(shifted&0xff00U)+((shifted+y)&255U));
    std::uint16_t style=0x006b;
    if (current!=head && ram[slot+7]!=row) style=0x066b;
    else if ((descriptor.flags&14U)==2U && ram[slot+7]!=row) style=0x0b6b;
    try {
        const std::vector<std::uint8_t> script(resource.data.begin()+text_offset,resource.data.end());
        if (!trace_table_fixed_text(script,address,style,*font,pending,error,&result_line,&style,&pending_d3)) return false;
    } catch (const std::bad_alloc&) {
        error="cannot allocate debug menu output";return false;
    }
    if (toggle) {ram[0xf000]=static_cast<std::uint8_t>(flags>>8);ram[0xf001]=static_cast<std::uint8_t>(flags);}
    writes.swap(pending);a2=result_a2;line=result_line;
    if (d1 != NULL) { *d1=style; } // 9f36 clears D1 before selecting text style.
    if (d3 != NULL) { *d3=pending_d3; }
    error.clear();return true;
}
}
