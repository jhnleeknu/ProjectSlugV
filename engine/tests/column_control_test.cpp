#include "ms5/column_control.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,unsigned int value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0);std::vector<ms5::VideoPortWrite> writes;
    std::uint32_t d0=0xabcdffff;std::string error;
    ram[0x7a]=0x81;put(ram,0x26,0x7fff);put(ram,0x7c,0x138);put(ram,0x7e,0x1ff);
    for(unsigned int i=0;i<32;++i) put(ram,0x3a+2*i,0x101);
    assert(ms5::refresh_column_controls(ram,0x100000,d0,writes,error));
    assert(ram[0x7a]==1 && d0==0xabcdff80 && writes.size()==64);
    assert(writes[0].value==0x04009c00 && writes[1].value==0x0200ff80); // test==a000 excludes offset
    assert(writes[26].value==0x040d0400 && writes[27].value==0x020d0081); // X wraps and offset applies
    assert(ms5::refresh_column_controls(ram,0x100000,d0,writes,error));assert(writes.empty());
    ram[0x7a]=0x81;put(ram,0x26,0x8000);
    assert(ms5::refresh_column_controls(ram,0x100000,d0,writes,error));assert(ram[0x7a]==1 && writes.empty());
    ram[0x7a]=0x80;
    assert(ms5::refresh_column_controls(ram,0x100000,d0,writes,error));assert(ram[0x7a]==0x80);
    ram.assign(65536,0);ram[0x10]=0xff;ram[0x11]=0xff;
    assert(ms5::refresh_scene_columns(ram,d0,writes,error));
    assert(writes.size()==4 && writes[0].address==0x2ffff2 && writes[0].value==0x2000 && writes[2].value==0x1000);
    assert(ram[0x10]==0 && ram[0x11]==0 && d0==0xabcdff80);
    const std::vector<std::uint8_t> before=ram;
    assert(!ms5::refresh_column_controls(ram,0x10ff82,d0,writes,error));assert(ram==before && writes.size()==4 && d0==0xabcdff80);
    std::cout<<"Column controls unsigned threshold, address/coordinate wrap and bank sequence passed\n";
}
