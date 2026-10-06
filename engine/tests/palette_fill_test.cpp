#include "ms5/palette_fill.h"
#include <cstdlib>
#include <iostream>
void check(bool value) { if (!value) { std::cerr << "palette fill test failed\n"; std::exit(1); } }
int main() {
    ms5::PaletteRecord zero = {};
    std::vector<ms5::PaletteRecord> records(2048,zero);
    for (std::size_t i=0;i<records.size();++i) { records[i].id=static_cast<std::uint32_t>(i); records[i].hardware_words[1]=static_cast<std::uint16_t>(i); }
    std::vector<std::uint8_t> ram(65536,0xaa);
    std::string error;
    check(ms5::setup_palette_fill(ram,records,65535,error));
    check(ram[0x7da2]==0xaa && ram[0x7da3]==0xaa && ram[0x7da4]==7 && ram[0x7da5]==255);
    check(ram[0x7dea]==0x20 && ram[0x7deb]==0 && ram[0x10]==0 && ram[0x11]==0);
    check(ram[0x7dec]==0xaa && ram[0x7ded]==0xaa);
    check(ms5::setup_palette_fill(ram,records,2048,error));
    check(ram[0x7da4]==0 && ram[0x7da5]==0);
    records.back().id=2046;
    const std::vector<std::uint8_t> before=ram;
    check(!ms5::setup_palette_fill(ram,records,0,error) && ram==before);
    records.resize(22);
    check(!ms5::setup_palette_fill(ram,records,0,error) && ram==before);
    std::cout << "palette_fill_test: passed\n";
}
