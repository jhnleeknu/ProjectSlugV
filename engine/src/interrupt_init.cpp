#include "ms5/interrupt_init.h"
namespace ms5 {
bool initialize_interrupt_state(std::vector<std::uint8_t>& ram,std::string& error) {
    if(ram.size()!=65536U) {error="interrupt initialization requires 64KiB RAM";return false;}
    ram[0x16]=0;ram[0x17]=2;ram[0x1a]=0;ram[0x19]=0;ram[0x1b]=0;
    ram[0x81c]=0;ram[0x81d]=0x10;ram[0x81e]=0x08;ram[0x81f]=0x1c;
    error.clear();return true;
}
bool initialize_irq_callbacks(std::vector<std::uint8_t>& ram,std::uint32_t& a0,std::string& error) {
    if(ram.size()!=65536U) {error="IRQ callback initialization requires 64KiB RAM";return false;}
    ram[0x4d91]&=0xefU;
    for(unsigned int at=6;at<=10;at+=4) {
        ram[at]=0;ram[at+1]=0;ram[at+2]=0x3d;ram[at+3]=0xcc;
    }
    a0=0x3dcc;error.clear();return true;
}
}
