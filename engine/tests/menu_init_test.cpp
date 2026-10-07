#include "ms5/menu_init.h"
#include <cassert>
#include <iostream>

int main() {
    std::vector<std::uint8_t> ram(65536, 0xa5);
    ms5::FixedDataResource resource;
    resource.source_cpu_address = resource.source_rom_offset = 0x200;
    resource.data.assign(20, 0);
    for (unsigned int i = 16; i < 20; ++i) resource.data[i] = 255;
    std::string error;
    assert(ms5::initialize_menu(ram, resource, 0x200, 0x1234, 0xabcd, 0x7000, error));
    assert(ram[0x7f03] == 0xa5 && ram[0x7f12] == 0xa5 && ram[0x7f15] == 0xa5);
    assert(ram[0x7f07] == 0x34 && ram[0x7f08] == 0xcd);
    assert(ram[0x7f09] == 4 && ram[0x7f0a] == 2);
    const std::vector<std::uint8_t> before = ram;
    resource.data[2] = 3; // title pointer 0x300 outside the resource.
    assert(!ms5::initialize_menu(ram, resource, 0x200, 0, 0, 0, error));
    assert(ram == before);
    resource.data[2] = 2;
    resource.data[3] = 20; // title begins at0x214, inside after extension.
    resource.data.push_back(92);
    resource.data.push_back('n');
    resource.data.push_back(0);
    assert(!ms5::initialize_menu(ram, resource, 0x200, 0, 0, 0x74ff, error));
    assert(ram == before);
    ram.pop_back();
    const std::vector<std::uint8_t> short_ram = ram;
    assert(!ms5::initialize_menu(ram, resource, 0x200, 0, 0, 0, error));
    assert(ram == short_ram);
    // Title measurement can reset full D3 and change terminal style even
    // when it emits no glyphs. These outputs must roll back on late failure.
    ram.assign(65536, 0);
    resource.data.resize(20);
    const unsigned char title[]={92,'l',2,3,92,'c',0x68,0};
    resource.data.insert(resource.data.end(),title,title+sizeof(title));
    std::uint16_t line=0x7000,style=0xffff;
    std::uint32_t d3=0xdead7000U;
    assert(ms5::initialize_menu(ram,resource,0x200,4,8,line,error,&line,&style,&d3));
    assert(line==0x7043 && style==0x68 && d3==0x7043U);
    const std::vector<std::uint8_t> final_ram=ram;
    resource.data.pop_back();
    d3=0xdead7043U;
    assert(!ms5::initialize_menu(ram,resource,0x200,4,8,line,error,&line,&style,&d3));
    assert(ram==final_ram && line==0x7043 && style==0x68 && d3==0xdead7043U);
    std::cout << "Menu initialization preservation and failure checks passed\n";
}
