#include "ms5/animation_banked_lookup.h"
namespace ms5 {
namespace {
void word(std::uint32_t& r,std::uint32_t value) {r=(r&0xffff0000U)|(value&65535U);}
std::uint32_t indexed(std::uint32_t base,std::uint32_t value) {
    const std::uint32_t low=value&65535U;
    // Unsigned subtraction/addition explicitly implements32-bit wrapping.
    return (low&0x8000U)?base-(0x10000U-low):base+low;
}
bool next(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    const ProgramBusState& bus,SceneMapTransferState& r,unsigned int size,std::uint32_t& value,std::string& error) {
    if(!read_program_bus(ram,windows,bus,r.a[1],size,value,error))return false;
    r.a[1]+=size;return true;
}
}
bool execute_animation_banked_lookup(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,const ProgramBusState& bus,
    SceneMapTransferState& registers,std::uint32_t a6,std::string& error) {
    SceneMapTransferState r=registers;std::uint32_t value=0;r.d[0]=0;
    if(!next(ram,windows,bus,r,1,value,error))return false;r.d[0]=value;
    word(r.d[0],r.d[0]*2U);r.a[2]=0x4a76c;
    if(!read_program_bus(ram,windows,bus,indexed(r.a[2],r.d[0]),2,value,error))return false;word(r.d[0],value);
    if(!next(ram,windows,bus,r,2,value,error))return false;word(r.d[7],value);r.a[2]=0x200004;
    if(!read_program_bus(ram,windows,bus,indexed(r.a[2],r.d[7]),4,value,error))return false;r.a[2]=value;
    if(!next(ram,windows,bus,r,2,value,error))return false;word(r.d[7],value);
    if(!read_program_bus(ram,windows,bus,indexed(r.a[2],r.d[7]),4,value,error))return false;r.d[7]=value;
    if(!write_program_bus_ram(ram,indexed(a6,r.d[0]),4,r.d[7],error))return false;
    registers=r;error.clear();return true;
}
}
