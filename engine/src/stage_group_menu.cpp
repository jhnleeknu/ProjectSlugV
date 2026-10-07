#include "ms5/stage_group_menu.h"
#include "ms5/menu_border.h"
#include "ms5/menu_descriptor.h"
#include "ms5/formatted_text.h"
#include "ms5/stage_state.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t read_long(const std::vector<std::uint8_t>& bytes,std::size_t at) {
    return (static_cast<std::uint32_t>(bytes[at])<<24)|
           (static_cast<std::uint32_t>(bytes[at+1])<<16)|
           (static_cast<std::uint32_t>(bytes[at+2])<<8)|bytes[at+3];
}
void put_long(std::vector<std::uint8_t>& bytes,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)bytes[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
}
bool dispatch_stage_group_menu(std::vector<std::uint8_t>& ram,
                               const FixedDataResource& menu,
                               const FixedDataResource* font,
                               const StageGroupMenuContext* context,
                               std::uint16_t event, std::uint32_t& a2,
                               std::vector<VideoPortWrite>& writes,
                               std::string& error, std::uint32_t* d1, std::uint32_t* d3) {
    bool covered=false;
    if(!menu_position_occluded(ram,0x7000U,covered,error))return false;
    const std::uint32_t current=read_long(ram,0x7f12);
    const std::uint32_t head=read_long(ram,0x7f0e);
    const std::size_t slot=current-0x100000U;
    MenuDescriptor descriptor;
    if(!decode_menu_descriptor(menu,read_long(ram,slot),descriptor,error))return false;
    const std::uint8_t row=ram[slot+8];
    if(descriptor.items.size()!=10U || ram[slot+6]!=10U || row>=10U ||
       descriptor.items[row].callback!=0x9802U) {
        error="stage group menu requires a valid row in the ten-entry9802 menu";return false;
    }
    std::uint32_t pending_d1=d1==NULL?0U:*d1;
    std::uint32_t pending_d3=d3==NULL?0U:*d3;
    try {
        std::vector<std::uint8_t> candidate=ram;
        std::vector<VideoPortWrite> pending;
        std::uint32_t result_a2=current;
        if(event==3U) {
            pending_d1=static_cast<std::uint8_t>(candidate[slot+10U]+1U+row);
            candidate[0x7dfa]=0;candidate[0x7dfb]=1;
            if(!set_stage_state(candidate,SelectStage,static_cast<std::uint16_t>(row+9U),error))return false;
            candidate[0x7f1b]=2;result_a2=head;
        } else if(event==4U) {
            candidate[0x7f1b]=2;result_a2=head;
        } else if(event==5U) {
            if(font==NULL || context==NULL || context->catalog==NULL) {
                error="stage group drawing requires fonts and stage catalog context";return false;
            }
            const std::uint32_t stack=context->callback_stack;
            if((stack&1U) || stack<0x110010U || stack>0xfffffcU) {
                error="stage group callback stack must be even and above fixed ROM/work RAM";return false;
            }
            std::uint16_t count=0;
            std::uint32_t record=0,name=0;
            if(!query_stage(*context->catalog,static_cast<std::uint16_t>(row+9U),0,
                            count,record,name,error))return false;
            std::vector<FixedDataResource> resources;
            resources.push_back(menu);
            if(name==0U) {
                if(context->null_name==NULL || context->null_name->source_cpu_address!=0U ||
                   context->null_name->source_rom_offset!=0U || context->null_name->data.size()!=4U) {
                    error="zero stage name pointer requires the raw four-byte ROM prefix";return false;
                }
                resources.push_back(*context->null_name);
            } else {
                const StageRecord& selected=context->catalog->groups[row+9U].records[0];
                FixedDataResource name_resource;
                name_resource.source_cpu_address=selected.source_cpu_address;
                name_resource.source_rom_offset=selected.source_cpu_address;
                name_resource.data=selected.data;
                resources.push_back(name_resource);
            }
            candidate[0x7e07]=static_cast<std::uint8_t>(row+1U);
            put_long(candidate,0x7e0a,name);
            const unsigned int padding=(descriptor.flags&14U)!=0U?1U:3U;
            const std::uint8_t x=static_cast<std::uint8_t>(candidate[slot+9]+padding);
            const std::uint8_t y=static_cast<std::uint8_t>(candidate[slot+10]+1U+row);
            const unsigned int shifted=static_cast<unsigned int>(x)<<5;
            const std::uint16_t cursor=static_cast<std::uint16_t>(0x7000U+(shifted&0xff00U)+((shifted+y)&255U));
            std::uint16_t style=3;
            if(current!=head && candidate[slot+7]!=row)style=0x603;
            else if((descriptor.flags&14U)==2U && candidate[slot+7]!=row)style=0xb03;
            std::vector<std::uint8_t> arguments(4,0);
            put_long(arguments,0,name);
            if(!format_fixed_text(candidate,resources,*font,0x9781U,stack-4U,
                                  arguments,cursor,style,pending,error,0xe84c8U,&style,NULL,&pending_d3))return false;
            pending_d1=style; // 9f36/9850 clear the full D1 before style selection.
            // 396e has advanced the argument pointer back to the entry stack;
            // 9880 restores A7 but leaves A2 at that consumed argument pointer.
            result_a2=stack;
        }
        ram.swap(candidate);writes.swap(pending);a2=result_a2;
    } catch(const std::bad_alloc&) {
        error="cannot allocate stage group menu state";return false;
    }
    if(d1!=NULL) *d1=pending_d1;
    if(d3!=NULL) *d3=pending_d3;
    error.clear();return true;
}
}
