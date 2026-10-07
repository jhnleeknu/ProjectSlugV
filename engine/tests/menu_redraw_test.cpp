#include "ms5/menu_redraw.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& data, std::size_t at, std::uint32_t value) {
    for (unsigned int i=0; i<4U; ++i) data[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
void fails(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& menu,
           std::uint32_t last) {
    const std::vector<std::uint8_t> before=ram;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].value=987;
    std::uint16_t line=123;std::string error;
    assert(!ms5::redraw_menu_stack(ram,menu,last,0x7000,writes,error,NULL,NULL,&line));
    assert(ram==before && writes.size()==1 && writes[0].value==987 && line==123);
    assert(!error.empty());
}
}
int main() {
    ms5::FixedDataResource menu;
    menu.source_cpu_address=menu.source_rom_offset=0x200;
    menu.data.assign(32,0);
    put(menu.data,0,0x21e);put(menu.data,16,0x21e);put(menu.data,26,0xffffffffU);
    menu.data[30]='A';
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0x7f0e,0x107eee);put(ram,0x7f12,0xdeadbeef);put(ram,0x7f16,0x3650);
    for (std::size_t slot=0x7eee;slot<=0x7efe;slot+=16) {
        put(ram,slot,0x200);ram[slot+4]=3;ram[slot+6]=1;ram[slot+11]=5;
        ram[slot+9]=static_cast<std::uint8_t>(slot==0x7eee?20:4);
        ram[slot+10]=8;
    }
    put(ram,0x7eee,0x400);fails(ram,menu,0x107eee); // After oldest was drawn.
    put(ram,0x7eee,0x200);fails(ram,menu,0x107eed);fails(ram,menu,0x107ede);
    std::string error;std::vector<ms5::VideoPortWrite> writes(1);
    std::uint16_t line=0;
    const std::vector<std::uint8_t> before=ram;
    assert(ms5::redraw_menu_stack(ram,menu,0x107f0e,456,writes,error,NULL,NULL,&line));
    assert(ram==before && writes.empty() && line==456);
    {
        std::uint32_t d1=0xabcd1234U, d3=0x987601c8U;
        assert(ms5::redraw_menu_stack(ram,menu,0x107f0e,456,writes,error,
                                     NULL,NULL,&line,&d1,&d3));
        assert(ram==before && writes.empty() && line==456);
        assert(d1==0xabcd1234U && d3==0x987601c8U);
        writes.resize(1);writes[0].value=987;line=123;
        assert(!ms5::redraw_menu_stack(ram,menu,0x107f0e,457,writes,error,
                                      NULL,NULL,&line,&d1,&d3));
        assert(ram==before && writes.size()==1 && writes[0].value==987 && line==123);
        assert(d1==0xabcd1234U && d3==0x987601c8U);
        put(ram,0x7eee,0x400);
        const std::vector<std::uint8_t> late_before=ram;
        d3=0x98767000U;
        assert(!ms5::redraw_menu_stack(ram,menu,0x107eee,0x7000,writes,error,
                                      NULL,NULL,&line,&d1,&d3));
        assert(ram==late_before && writes.size()==1 && writes[0].value==987 && line==123);
        assert(d1==0xabcd1234U && d3==0x98767000U);
        put(ram,0x7eee,0x200);
        assert(ms5::redraw_menu_stack(ram,menu,0x107eee,0x7000,writes,error,
                                     NULL,NULL,&line,&d1,&d3));
        assert(!writes.empty() && static_cast<std::uint16_t>(d3)==line);
    }
    assert(ms5::redraw_menu_stack(ram,menu,0x107eee,0x7000,writes,error,NULL,NULL,&line));
    assert(!writes.empty() && ram[0x7f14]==0x7e && ram[0x7f15]==0xee);
    ram.resize(5);fails(ram,menu,0x107eee);
    std::cout << "Menu stack redraw bounds, empty range and late-error rollback passed\n";
}
