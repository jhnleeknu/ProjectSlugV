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
    // Coordinate preparation uses explicit 16-bit subtraction and cache checks.
    std::uint32_t d1=0x98761234U,d3=0xdeadbeefU;
    for(unsigned int flags=0;flags<4;++flags) {
        ram.assign(65536,0);
        ram[0x25]=static_cast<std::uint8_t>(flags);ram[0x7a]=0x35;
        put(ram,0x14,0);put(ram,0x18,0);
        const std::uint16_t x=(flags&1U)!=0?0xffffU:0U;
        const std::uint16_t y=(flags&2U)!=0?0xffffU:0U;
        put(ram,0x7c,static_cast<std::uint16_t>(x+1U));put(ram,0x7e,static_cast<std::uint16_t>(y+1U));
        d0=0xabcd1234U;d1=0x98761234U;d3=0xdeadbeefU;
        assert(ms5::prepare_column_controls(ram,0x100000,d0,d1,d3,error));
        assert(d0==(0xabcd0000U|x) && d1==(0x98760000U|y) && d3==0U);
        assert(ram[0x7a]==0xb5 && ram[0x7c]==static_cast<std::uint8_t>(x>>8) &&
               ram[0x7d]==static_cast<std::uint8_t>(x) && ram[0x7e]==static_cast<std::uint8_t>(y>>8) &&
               ram[0x7f]==static_cast<std::uint8_t>(y));
        ram[0x7a]=0x35; // Identical caches preserve all flags.
        assert(ms5::prepare_column_controls(ram,0x100000,d0,d1,d3,error));
        assert(ram[0x7a]==0x35);
    }
    const std::vector<std::uint8_t> prepare_before=ram;
    const std::uint32_t old_d0=d0,old_d1=d1,old_d3=d3;
    assert(!ms5::prepare_column_controls(ram,0x100001,d0,d1,d3,error));
    assert(ram==prepare_before && d0==old_d0 && d1==old_d1 && d3==old_d3);
    ram.assign(65536,0);
    const unsigned int objects[]={0x9156U,0xb1d6U,0xd256U,0xd2d6U};
    for(unsigned int i=0;i<4;++i) {
        put(ram,objects[i]+0x14U,10U+i);put(ram,objects[i]+0x18U,20U+i);
        ram[objects[i]+0x25U]=3U;
    }
    d0=0xabcd1234U;d1=0x98761234U;d3=0xdeadbeefU;
    assert(ms5::prepare_scene_columns(ram,d0,d1,d3,writes,error));
    assert(d0==0xabcd000cU && d1==0x98760016U && d3==0U && writes.size()==4);
    const unsigned int bank_values[]={0x2000U,0U,0x1000U,0U};
    for(unsigned int i=0;i<4;++i) {
        assert(writes[i].address==((i&1U)!=0?0x2ffff0U:0x2ffff2U) &&
               writes[i].size==2U && writes[i].value==bank_values[i]);
        assert(ram[objects[i]+0x7aU]==0x80U);
    }
    ram.resize(5);
    const std::vector<std::uint8_t> short_before=ram;
    assert(!ms5::prepare_scene_columns(ram,d0,d1,d3,writes,error));
    assert(ram==short_before && d0==0xabcd000cU && d1==0x98760016U && d3==0U && writes.size()==4);
    std::cout<<"Column controls unsigned threshold, address/coordinate wrap and bank sequence passed\n";
}
