#include "ms5/stage_counter.h"
#include <new>
namespace ms5 {
namespace {
void byte(std::uint32_t& value,std::uint32_t input) {value=(value&0xffffff00U)|(input&255U);}
bool address(std::uint32_t a5,int displacement,std::size_t& at,std::string& error) {
    const std::int64_t cpu=static_cast<std::int64_t>(a5)+displacement;
    if(cpu<0x100000 || cpu>=0x110000) {error="stage counter BYTE access outside CPU RAM";return false;}
    at=static_cast<std::size_t>(cpu-0x100000);return true;
}
bool read(const std::vector<std::uint8_t>& ram,std::uint32_t a5,int displacement,
    std::uint8_t& value,std::string& error) {
    std::size_t at=0;if(!address(a5,displacement,at,error))return false;value=ram[at];return true;
}
bool write(std::vector<std::uint8_t>& ram,std::uint32_t a5,int displacement,
    std::uint32_t value,std::string& error) {
    std::size_t at=0;if(!address(a5,displacement,at,error))return false;
    ram[at]=static_cast<std::uint8_t>(value);return true;
}
bool run(std::vector<std::uint8_t>& ram,ObjectRestartState& s,std::string& error) {
    std::uint8_t value=0;
    if(!read(ram,s.a[5],0x5683,value,error))return false;
    if((value&16U)==0)return true;
    if(!read(ram,s.a[5],0x7db6,value,error))return false;
    byte(s.d[0],value==1?255:0);
    if(!read(ram,s.a[5],0x7db7,value,error))return false;
    byte(s.d[1],value==1?255:0);byte(s.d[1],s.d[1]|s.d[0]);
    if((s.d[1]&255U)==0)return true;
    if(!read(ram,s.a[5],0x567f,value,error))return false;
    byte(s.d[0],value);const unsigned int low_input=value;
    if(!read(ram,s.a[5],0x567e,value,error))return false;
    byte(s.d[1],value);s.d[2]=0;
    byte(s.d[0],low_input-2U);
    // Source0 behavior follows the independently audited external hardware
    // reference described in stage-counter-contract.md, not a local hardware
    // experiment. With X clear every input BYTE is unchanged, including nonBCD.
    if(low_input<2) {
        if(value==0) {s.d[0]=0;s.d[1]=0;}
        else byte(s.d[1],static_cast<unsigned int>(value)-((value&15U)==0?7U:1U));
    }
    return write(ram,s.a[5],0x567e,s.d[1],error) && write(ram,s.a[5],0x567f,s.d[0],error);
}
}
bool execute_stage_counter(std::vector<std::uint8_t>& ram,ObjectRestartState& state,std::string& error) {
    if(ram.size()!=65536){error="stage counter requires64KiB RAM";return false;}
    try {
        std::vector<std::uint8_t> candidate=ram;ObjectRestartState next=state;
        if(!run(candidate,next,error))return false;
        ram.swap(candidate);state=next;error.clear();return true;
    } catch(const std::bad_alloc&){error="cannot allocate stage counter transaction";return false;}
}
}
