#include "ms5/sound_byte_execution.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram,unsigned int at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at])<<8)|ram[at+1]);
}
void put(std::vector<std::uint8_t>& ram,unsigned int at,std::uint32_t value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
bool run(std::vector<std::uint8_t>& ram,SoundByteExecutionState& state,std::string& error) {
    SceneMapTransferState& s=state.registers;
    if(!state.waiting) {
        if((s.d[0]&255U)==3) { ram[0x4d7b]=255; return true; }
        const std::uint32_t tail=word(ram,0x4d76);
        const std::int32_t offset=tail<32768U?static_cast<std::int32_t>(tail):static_cast<std::int32_t>(tail)-65536;
        s.a[0]=0x104cf4U+static_cast<std::uint32_t>(offset);
        s.d[1]=(s.d[1]&0xffff0000U)|((tail+1U)&127U);
    }
    state.waiting=(s.d[1]&65535U)==word(ram,0x4d74);
    if(state.waiting) return true;
    if(s.a[0]<0x100000U || s.a[0]>=0x110000U) { error="sound byte write outside64KiB RAM"; return false; }
    ram[s.a[0]-0x100000U]=static_cast<std::uint8_t>(s.d[0]);
    put(ram,0x4d76,s.d[1]);return true;
}
}
bool execute_sound_byte(std::vector<std::uint8_t>& ram,SoundByteExecutionState& state,std::string& error) {
    if(ram.size()!=65536) { error="sound byte execution requires64KiB RAM";return false; }
    try {
        std::vector<std::uint8_t> candidate=ram;SoundByteExecutionState next=state;
        if(!run(candidate,next,error)) return false;
        ram.swap(candidate);state=next;error.clear();return true;
    } catch(const std::bad_alloc&) {error="cannot allocate sound byte transaction";return false;}
}
}
