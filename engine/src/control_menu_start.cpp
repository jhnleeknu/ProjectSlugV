#include "ms5/control_menu_start.h"
#include "ms5/menu_init.h"
#include <new>
namespace ms5 {
namespace {
void emit(std::vector<VideoPortWrite>& writes,std::uint16_t address,std::uint16_t value) {
    VideoPortWrite write;write.address=0x3c0000U;write.size=4;
    write.value=(static_cast<std::uint32_t>(address)<<16)|value;writes.push_back(write);
}
}
bool start_control_menu(std::vector<std::uint8_t>& ram,const FixedDataResource& menu,
                        std::uint16_t initial_line,std::uint32_t entry_stack,
                        MenuFrameResult& result,std::vector<VideoPortWrite>& writes,
                        std::string& error, std::uint32_t* d1, std::uint32_t* d3) {
    if(ram.size()!=65536U) {error="control menu start requires exactly 65536 RAM bytes";return false;}
    if((entry_stack&1U) || entry_stack<0x110104U || entry_stack>0xfffffcU) {
        error="control menu start requires an even external diagnostic stack";return false;
    }
    if (d3 != NULL && (*d3 & 0xffffU) != initial_line) {
        error="menu start D3 low word must match initial line";return false;
    }
    std::uint32_t pending_d3 = d3 == NULL ? initial_line : *d3;
    std::uint16_t final_style = 8;
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        pending.reserve(773U);
        // ca9e writes the native video control area in this exact order.
        for(unsigned int i=0;i<768U;++i)emit(pending,static_cast<std::uint16_t>(0x7500U+i),0);
        for(unsigned int i=0;i<4U;++i)emit(pending,static_cast<std::uint16_t>(0x7500U+i*32U),0x200U);
        emit(pending,0x7580U,0xff02U);
        candidate[0x7dee]=255;
        std::uint16_t line=initial_line;
        if(!initialize_menu(candidate,menu,0x93e0U,4,8,line,error,&line,&final_style,&pending_d3))return false;
        if (candidate[0x7f0a] == 0) {
            error="native root menu must have a nonzero opening target";return false;
        }
        candidate[0x7f16]=0;candidate[0x7f17]=0;candidate[0x7f18]=0x93;candidate[0x7f19]=0x32;
        candidate[0x7dfa]=0;candidate[0x7dfb]=0;
        MenuFrameResult outcome;std::vector<VideoPortWrite> frame_writes;
        if(!step_menu_frame(candidate,menu,line,entry_stack-4U,outcome,frame_writes,error))return false;
        if(outcome.status!=0 || outcome.external_jump!=0) {
            error="native control menu start must enter its first opening frame";return false;
        }
        pending.insert(pending.end(),frame_writes.begin(),frame_writes.end());
        const std::uint8_t first=candidate[0x4caa];
        const std::uint8_t second=candidate[0x4cb0];
        candidate[0x4cab]=static_cast<std::uint8_t>(candidate[0x4cab]|((first^candidate[0x7dfc])&first));
        candidate[0x4cb1]=static_cast<std::uint8_t>(candidate[0x4cb1]|((second^candidate[0x7dfd])&second));
        candidate[0x7df3]=static_cast<std::uint8_t>(candidate[0x7df3]-1U);
        ram.swap(candidate);writes.swap(pending);result=outcome;
    } catch(const std::bad_alloc&) {error="cannot allocate control menu start state";return false;}
    if (d1 != NULL) { *d1 = final_style; } // ca9e clears the whole register.
    if (d3 != NULL) { *d3 = pending_d3; }
    error.clear();return true;
}
}
