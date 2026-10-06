#include "ms5/stage_area_menu.h"
#include "ms5/menu_border.h"
#include "ms5/menu_descriptor.h"
#include "ms5/menu_navigation.h"
#include "ms5/formatted_text.h"
#include "ms5/stage_state.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t read_long(const std::vector<std::uint8_t>& data,std::size_t at) {
    return (static_cast<std::uint32_t>(data[at])<<24)|(static_cast<std::uint32_t>(data[at+1])<<16)|
           (static_cast<std::uint32_t>(data[at+2])<<8)|data[at+3];
}
void put_long(std::vector<std::uint8_t>& data,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)data[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
std::uint16_t screen_address(unsigned int x,unsigned int y) {
    const unsigned int shifted=(x<<5)&65535U;
    return static_cast<std::uint16_t>(0x7000U+(shifted&0xff00U)+((shifted+y)&255U));
}
bool append_script(const FixedDataResource& resource,std::uint32_t address,
                   const FixedDataResource& font,std::uint16_t& cursor,std::uint16_t& style,
                   std::uint16_t& line,std::vector<VideoPortWrite>& writes,std::string& error) {
    if(address<resource.source_cpu_address || address-resource.source_cpu_address>=resource.data.size()) {
        error="stage area text lies outside supplied ROM resource";return false;
    }
    const std::vector<std::uint8_t> script(resource.data.begin()+(address-resource.source_cpu_address),resource.data.end());
    std::size_t position=0;line=cursor;
    for(;;) {
        std::uint8_t glyph=0;
        if(!parse_fixed_text_glyph(script,position,style,line,cursor,glyph,error))return false;
        if(glyph==0)return true;
        std::vector<VideoPortWrite> item;
        if(!render_table_text_glyph(glyph,script,position,cursor,style,font,item,error))return false;
        if(writes.size()+item.size()>100000U) {error="stage area output exceeds100000 events";return false;}
        writes.insert(writes.end(),item.begin(),item.end());
    }
}
}
bool dispatch_stage_area_menu(std::vector<std::uint8_t>& ram,
                              const FixedDataResource& menu,const FixedDataResource* font,
                              const StageGroupMenuContext* context,
                              std::uint16_t event,std::uint16_t& line,
                              std::uint32_t& a2,std::vector<VideoPortWrite>& writes,std::string& error) {
    bool covered=false;
    if(!menu_position_occluded(ram,0x7000,covered,error))return false;
    const std::uint32_t current=read_long(ram,0x7f12),head=read_long(ram,0x7f0e);
    const std::size_t slot=current-0x100000U;
    MenuDescriptor descriptor;
    if(!decode_menu_descriptor(menu,read_long(ram,slot),descriptor,error))return false;
    const std::uint8_t row=ram[slot+8];
    if(descriptor.items.size()!=10U || ram[slot+6]!=10U || row<2U || row>=10U ||
       descriptor.items[row].callback!=0x9602U) {
        error="stage area callback requires native rows2..9 in a ten-entry menu";return false;
    }
    try {
        std::vector<std::uint8_t> candidate=ram;
        std::vector<VideoPortWrite> pending;
        std::uint32_t result_a2=current;
        std::uint16_t result_line=line;
        if(event==3U) {
            candidate[0x7dfa]=0;candidate[0x7dfb]=1;
            const std::uint8_t group=candidate[0x7dfe];
            if(!set_stage_state(candidate,SelectStage,group,error) ||
               !set_stage_state(candidate,SelectStageArea,candidate[0x7dffU+group],error))return false;
            candidate[0x7f1b]=2;result_a2=head;
        } else if(event==4U) {
            candidate[0x7f1b]=2;result_a2=head;
        } else if(event==6U) {
            StageGroupMenuContext nested;
            const StageGroupMenuContext* nested_pointer=NULL;
            if(context!=NULL) {
                if(context->callback_stack<0x110024U || context->callback_stack>0xfffffcU ||
                   (context->callback_stack&1U)) {
                    error="stage navigation callback stack is invalid";return false;
                }
                nested=*context;nested.callback_stack-=20U;nested_pointer=&nested;
            }
            const std::uint8_t requested=static_cast<std::uint8_t>(candidate[0x7dfe]+2U);
            if(!navigate_menu(candidate,menu,true,requested,pending,error,font,nested_pointer,&result_line))return false;
        } else if(event==0U || event==1U || event==2U || event==5U) {
            if(font==NULL || context==NULL || context->catalog==NULL ||
               context->callback_stack<0x110020U || context->callback_stack>0xfffffcU ||
               (context->callback_stack&1U)) {
                error="stage area drawing requires fonts, catalog and external callback stack";return false;
            }
            if(event==0U)candidate[0x7dfe]=static_cast<std::uint8_t>(row-2U);
            if(event==1U || event==2U) {
                const unsigned int group=candidate[0x7dfe];
                if(group>=8U) {error="area editing requires a selected group0..7";return false;}
                std::uint16_t count=0;std::uint32_t record=0,name=0;
                if(!query_stage(*context->catalog,static_cast<std::uint16_t>(group),0,count,record,name,error))return false;
                const std::uint8_t previous=candidate[0x7dffU+group];
                if(event==1U)candidate[0x7dffU+group]=static_cast<std::uint8_t>(previous-1U+(previous==0U?count:0U));
                else {
                    const std::uint8_t next=static_cast<std::uint8_t>(previous+1U);
                    candidate[0x7dffU+group]=next<static_cast<std::uint8_t>(count)?next:0U;
                }
            }
            const unsigned int group=row-2U;
            const std::uint8_t area=candidate[0x7dffU+group];
            std::uint16_t count=0;std::uint32_t record=0,name=0;
            if(!query_stage(*context->catalog,static_cast<std::uint16_t>(group),area,count,record,name,error))return false;
            FixedDataResource name_resource;
            if(name==0U) {
                if(context->null_name==NULL || context->null_name->source_cpu_address!=0U ||
                   context->null_name->source_rom_offset!=0U || context->null_name->data.size()!=4U) {
                    error="zero area name requires the four-byte original ROM prefix";return false;
                }
                name_resource=*context->null_name;
            } else {
                const StageRecord& selected=context->catalog->groups[group].records[area];
                name_resource.source_cpu_address=name_resource.source_rom_offset=selected.source_cpu_address;
                name_resource.data=selected.data;
            }
            candidate[0x7e07]=static_cast<std::uint8_t>(group+1U);
            candidate[0x7e08]=static_cast<std::uint8_t>(area+1U);
            put_long(candidate,0x7e0a,name);
            const unsigned int padding=(descriptor.flags&14U)!=0U?1U:3U;
            const std::uint8_t x=static_cast<std::uint8_t>(candidate[slot+9]+padding);
            const std::uint8_t y=static_cast<std::uint8_t>(candidate[slot+10]+1U+row);
            std::uint16_t cursor=screen_address(x,y),style=3;
            if(current!=head && candidate[slot+7]!=row)style=0x603;
            else if((descriptor.flags&14U)==2U && candidate[slot+7]!=row)style=0xb03;
            if(!append_script(menu,0x956c,*font,cursor,style,result_line,pending,error))return false;
            std::vector<FixedDataResource> resources;
            resources.push_back(menu);resources.push_back(name_resource);
            std::vector<std::uint8_t> arguments(12,0);
            put_long(arguments,0,0x107e07);put_long(arguments,4,0x107e08);put_long(arguments,8,name);
            std::vector<VideoPortWrite> formatted;
            if(!format_fixed_text(candidate,resources,*font,0x955e,context->callback_stack-12U,
                                  arguments,cursor,style,formatted,error))return false;
            pending.insert(pending.end(),formatted.begin(),formatted.end());
            // Native format ends in%s; its final style is the saved formatter style.
            style=static_cast<std::uint16_t>((candidate[0x4cda]<<8)|candidate[0x4cdb]);
            // 9f12 gives byte coordinates, but +3/+1 here are WORD additions.
            cursor=screen_address(static_cast<unsigned int>(candidate[slot+9])+3U,
                                  static_cast<unsigned int>(candidate[slot+10])+1U);
            if(!append_script(menu,0x956c,*font,cursor,style,result_line,pending,error) ||
               !append_script(name_resource,name,*font,cursor,style,result_line,pending,error))return false;
        }
        ram.swap(candidate);writes.swap(pending);line=result_line;a2=result_a2;
    } catch(const std::bad_alloc&) {
        error="cannot allocate stage area callback state";return false;
    }
    error.clear();return true;
}
}
