#include "ms5/input_frame.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t long_word(const std::vector<std::uint8_t>& ram,std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at])<<24)|
           (static_cast<std::uint32_t>(ram[at+1])<<16)|
           (static_cast<std::uint32_t>(ram[at+2])<<8)|ram[at+3];
}
}
bool begin_input_frame(std::vector<std::uint8_t>& ram,const FixedDataResource& streams,
                       const FixedDataResource& table,const InputPortSamples& ports,
                       std::uint32_t object_address,std::uint16_t initial_style,
                       InputFrameResult& result,std::string& error,
                       std::uint32_t* d1,std::uint32_t* d3) {
    if(d1!=NULL && (*d1&0xffffU)!=initial_style) {
        error="input frame D1 low word must match style";return false;
    }
    // 31d6/352a only write D1 bytes/words; b68 preserves it. D3 is untouched.
    (void)d3;
    if(ram.size()!=65536U || (object_address&1U)!=0 || object_address<0x100000U ||
       object_address>0x10ff82U) {error="input frame requires 64KiB RAM and an even complete object span";return false;}
    std::vector<std::uint8_t> candidate;
    try {candidate=ram;} catch(const std::bad_alloc&) {error="cannot allocate input frame state";return false;}
    candidate[0x1a]=candidate[0x16];candidate[0x16]=0;
    candidate[0x4ca2]=0;candidate[0x4ca3]=0;
    InputFrameResult next;
    next.style=initial_style;
    if(!step_input(candidate,streams,table,ports,next.read_count,error,&next.style)) return false;
    const std::size_t at=object_address-0x100000U;
    next.callback=long_word(candidate,at+0x76U);
    next.next_pc=next.callback==0 ? 0xf54U : 0xf3cU;
    if(next.callback!=0) next.callback_context=long_word(candidate,at+0x7aU);
    ram.swap(candidate);result=next;
    if(d1!=NULL)*d1=(*d1&0xffff0000U)|next.style;
    error.clear();return true;
}
}
