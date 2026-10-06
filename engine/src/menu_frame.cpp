#include "ms5/menu_frame.h"
#include "ms5/menu_descriptor.h"
#include "ms5/menu_border.h"
#include "ms5/menu_motion.h"
#include "ms5/menu_text.h"
#include "ms5/menu_redraw.h"
#include "ms5/menu_header.h"
#include "ms5/menu_event.h"
#include "ms5/menu_input.h"
#include "ms5/menu_navigation.h"
#include "ms5/stage_group_menu.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t get(const std::vector<std::uint8_t>& ram,std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at])<<24)|(static_cast<std::uint32_t>(ram[at+1])<<16)|
           (static_cast<std::uint32_t>(ram[at+2])<<8)|ram[at+3];
}
void put(std::vector<std::uint8_t>& ram,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)ram[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
bool valid(std::uint32_t slot,bool empty=false) {
    return slot>=0x107e0eU && slot<=(empty?0x107f0eU:0x107efeU) && (slot-0x107e0eU)%16U==0U;
}
std::uint16_t base(const std::vector<std::uint8_t>& ram,std::size_t slot) {
    const unsigned int x=static_cast<unsigned int>(ram[slot+9])<<5;
    return static_cast<std::uint16_t>(0x7000U+(x&0xff00U)+((x+ram[slot+10])&255U));
}
struct Frame {
    std::vector<std::uint8_t>& ram;
    const FixedDataResource& resource;
    const FixedDataResource* font;
    const StageGroupMenuContext* resources;
    std::uint32_t stack;
    std::uint32_t renderer;
    MenuFrameResult out;
    std::vector<VideoPortWrite> writes;
    std::string& error;
    Frame(std::vector<std::uint8_t>& r,const FixedDataResource& d,const FixedDataResource* f,
          const StageGroupMenuContext* c,std::uint32_t s,std::uint16_t line,std::string& e)
        :ram(r),resource(d),font(f),resources(c),stack(s),renderer(get(r,0x7f16)),error(e) {out.line=line;}
};
const StageGroupMenuContext* context(Frame& f,unsigned int depth,StageGroupMenuContext& c) {
    if(f.resources==NULL)return NULL;
    c=*f.resources;c.callback_stack=f.stack-depth;return &c;
}
bool descriptor(Frame& f,std::uint32_t current,MenuDescriptor& d) {
    if(!valid(current) || current<get(f.ram,0x7f0e)) {f.error="frame current is not an allocated slot";return false;}
    if(!decode_menu_descriptor(f.resource,get(f.ram,current-0x100000U),d,f.error))return false;
    if(d.flags!=0 || d.callback10!=0 || (d.callback6!=0 && d.callback6!=0x9430U)) {
        f.error="frame descriptor flags/header callback has not been reconstructed";return false;
    }
    const std::size_t slot=current-0x100000U;
    if(d.items.size()!=f.ram[slot+6] || d.items.empty() || f.ram[slot+7]>=d.items.size()) {
        f.error="frame requires matching nonempty items and a valid selection";return false;
    }
    return true;
}
void append(Frame& f,const std::vector<VideoPortWrite>& writes) {
    f.writes.insert(f.writes.end(),writes.begin(),writes.end());
}
void append_border(Frame& f,const std::vector<FixedWrite>& writes) {
    for(std::size_t i=0;i<writes.size();++i) {
        VideoPortWrite w;w.address=0x3c0000U;w.size=4;
        w.value=(static_cast<std::uint32_t>(writes[i].address)<<16)|writes[i].value;f.writes.push_back(w);
    }
}
void border_line(Frame& f,std::size_t slot,unsigned int height) {
    if(height!=0)f.out.line=static_cast<std::uint16_t>(base(f.ram,slot)+(height<2?2:height));
}
bool motion(Frame& f,bool closing) {
    const std::size_t slot=get(f.ram,0x7f12)-0x100000U;
    const unsigned int old_height=f.ram[slot+4];
    std::vector<FixedWrite> writes;
    if(!(closing?close_menu_step(f.ram,f.resource,writes,f.error):
                 open_menu_step(f.ram,f.resource,writes,f.error)))return false;
    border_line(f,slot,closing?f.ram[slot+4]:old_height);
    append_border(f,writes);f.renderer=0xa008U;return true;
}
bool text(Frame& f,unsigned int depth,bool border) {
    const std::size_t slot=get(f.ram,0x7f12)-0x100000U;
    if(border) {
        std::vector<FixedWrite> writes;
        if(!trace_menu_border(f.ram,f.resource,writes,f.error))return false;
        append_border(f,writes);border_line(f,slot,f.ram[slot+4]);
    }
    StageGroupMenuContext c;std::vector<VideoPortWrite> writes;
    if(!draw_menu_text(f.ram,f.resource,f.renderer==0xa008U,f.out.line,writes,f.error,
                      &f.out.line,f.font,context(f,depth,c),f.renderer==0xa008U?0x3650U:f.renderer))return false;
    append(f,writes);return true;
}
bool redraw(Frame& f,std::uint32_t last,unsigned int depth) {
    StageGroupMenuContext c;std::vector<VideoPortWrite> writes;
    if(!redraw_menu_stack(f.ram,f.resource,last,f.out.line,writes,f.error,f.font,
                          context(f,depth,c),&f.out.line))return false;
    append(f,writes);f.renderer=0xa008U;return true;
}
bool event(Frame& f,std::uint16_t value,unsigned int depth) {
    StageGroupMenuContext c;MenuEventResult result;std::vector<VideoPortWrite> writes;
    if(!dispatch_menu_event(f.ram,f.resource,value,f.out.line,result,writes,f.error,
                            f.font,context(f,depth,c),&f.out.line))return false;
    append(f,writes);f.out.external_jump=result.external_jump;return true;
}
bool pending(Frame& f,std::uint32_t current) {
    const std::size_t slot=current-0x100000U;
    for(unsigned int i=0;i<1024;++i) {
        const std::uint8_t value=f.ram[slot+14];
        if(value==255)return true;
        f.ram[slot+14]=255;
        if(!event(f,value,8))return false;
        if(f.out.external_jump!=0)return true;
        put(f.ram,0x7f12,current);
    }
    f.error="menu pending events did not terminate";return false;
}
bool run(Frame& f) {
    for(std::uint32_t current=0x107efeU;current>=get(f.ram,0x7f0e);current-=16U) {
        put(f.ram,0x7f12,current);
        MenuDescriptor d;if(!descriptor(f,current,d))return false;
        const std::size_t slot=current-0x100000U;
        if(current!=get(f.ram,0x7f0e) && (f.ram[slot+15]&1U) && f.ram[slot+4]!=0) {
            if(!motion(f,true))return false;
            if(f.ram[slot+4]==0 && !redraw(f,current,36))return false;
        }
        // Native descriptors have no +10 callback; unsupported ones fail above.
    }
    std::uint32_t current=get(f.ram,0x7f0e);
    if(current==0x107f0eU) {f.out.status=-1;return true;}
    put(f.ram,0x7f12,current);
    std::size_t slot=current-0x100000U;
    const std::uint8_t mode=f.ram[0x7f1b];
    if(mode>2) {f.out.status=-1;return true;}
    if(mode==2) {
        if(f.ram[slot+4]!=0)return motion(f,true);
        // 9e94 with zero visible height still initializes D3 from slot xy.
        f.out.line=base(f.ram,slot);
        current+=16U;put(f.ram,0x7f0e,current);
        if(current==0x107f0eU) {f.out.status=-1;return true;}
        f.ram[0x7f1b]=0;put(f.ram,0x7f12,current);
        slot=current-0x100000U;f.ram[slot+8]=f.ram[slot+7];
        if(!event(f,7,8) || f.out.external_jump!=0)return f.out.external_jump!=0;
        if(current==get(f.ram,0x7f0e)) {
            put(f.ram,0x7f12,current);f.ram[slot+8]=f.ram[slot+7];
            if(!event(f,0,4) || f.out.external_jump!=0)return f.out.external_jump!=0;
        }
        return redraw(f,get(f.ram,0x7f12),32);
    }
    if(f.ram[slot+4]<f.ram[slot+12])return motion(f,false);
    if(mode==1) {
        f.ram[0x7f1b]=0;
        MenuDescriptor d;if(!descriptor(f,current,d))return false;
        unsigned int attempts=0;
        while(d.items[f.ram[slot+7]].callback==0) {
            if(++attempts>=d.items.size()) {f.error="opening menu has no callback (original loops)";return false;}
            f.ram[slot+7]=static_cast<std::uint8_t>((f.ram[slot+7]+1U)%d.items.size());
        }
        f.ram[slot+8]=f.ram[slot+7];f.renderer=get(f.ram,0x7f16);
        if(!text(f,24,true))return false;
        current=get(f.ram,0x7f12);slot=current-0x100000U;f.ram[slot+8]=f.ram[slot+7];
        if(!event(f,6,4) || f.out.external_jump!=0)return f.out.external_jump!=0;
        current=get(f.ram,0x7f12);slot=current-0x100000U;f.ram[slot+8]=f.ram[slot+7];
        return event(f,0,4);
    }
    const bool background=(f.ram[slot+15]&1U)!=0;
    f.ram[slot+15]=static_cast<std::uint8_t>(f.ram[slot+15]&254U);
    if(background && !text(f,28,false))return false;
    put(f.ram,0x7f12,current);
    MenuDescriptor d;if(!descriptor(f,current,d))return false;
    if(d.callback6==0x9430U) {
        std::uint32_t a2=current;
        if(!update_menu_header(f.ram,a2,f.error))return false;
    }
    put(f.ram,0x7f12,current);f.ram[slot+8]=f.ram[slot+7];
    if(!pending(f,current) || f.out.external_jump!=0)return f.out.external_jump!=0;
    MenuInput input;if(!select_menu_input(f.ram,input,f.error))return false;
    if(input.kind==MenuInputPrevious || input.kind==MenuInputNext) {
        f.ram[slot+15]=static_cast<std::uint8_t>((f.ram[slot+15]&253U)|
            (input.kind==MenuInputPrevious?2U:0U));
        StageGroupMenuContext c;std::vector<VideoPortWrite> writes;
        if(!navigate_menu(f.ram,f.resource,false,0,writes,f.error,f.font,context(f,24,c),&f.out.line))return false;
        append(f,writes);f.renderer=0xa008U;
    } else if(input.kind==MenuInputEvent)f.ram[slot+14]=input.event;
    else return true;
    return pending(f,current);
}
}
bool step_menu_frame(std::vector<std::uint8_t>& ram,const FixedDataResource& resource,
                     std::uint16_t initial_line,std::uint32_t entry_stack,
                     MenuFrameResult& result,std::vector<VideoPortWrite>& writes,
                     std::string& error,const FixedDataResource* font,
                     const StageGroupMenuContext* stage_context) {
    if(ram.size()!=65536U || !valid(get(ram,0x7f0e),true)) {
        error="menu frame requires 65536 RAM bytes and an aligned stack head";return false;
    }
    if((entry_stack&1U) || entry_stack<0x110100U || entry_stack>0xfffffcU) {
        error="menu frame requires an even external diagnostic stack";return false;
    }
    const std::uint32_t renderer=get(ram,0x7f16);
    if(renderer!=0x3650U && renderer!=0x9332U) {
        error="menu frame text renderer has not been reconstructed";return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        Frame f(candidate,resource,font,stage_context,entry_stack,initial_line,error);
        if(!run(f))return false;
        ram.swap(candidate);writes.swap(f.writes);result=f.out;
    } catch(const std::bad_alloc&) {error="cannot allocate menu frame state";return false;}
    error.clear();return true;
}
}
