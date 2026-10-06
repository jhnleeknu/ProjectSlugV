#include "ms5/palette_transfer.h"
#include <cstdlib>
#include <iostream>
void check(bool value) { if (!value) { std::cerr << "palette transfer test failed\n"; std::exit(1); } }
int main() {
    std::vector<std::uint8_t> ram(65536,0), palette(8192,0x55);
    std::uint8_t bank=9; std::string error;
    ram[0x7dea]=1;
    const std::vector<std::uint8_t> before=ram, colors=palette;
    check(!ms5::transfer_palette_frame(ram,palette,bank,error));
    check(ram==before && palette==colors && bank==9);
    ram[0x7dea]=0;ram[0x5da2]=0x12;ram[0x5da3]=0x34;
    check(ms5::transfer_palette_frame(ram,palette,bank,error));
    check(ram[0x5da2]==0x12 && ram[0x5da3]==0x34 && palette==colors && bank==0);
    ram[0x7ded]=255;ram[0x7dec]=1;
    check(ms5::transfer_palette_frame(ram,palette,bank,error));
    check(ram[0x5da2]==0 && ram[0x5da3]==0 && palette==colors && ram[0x7ded]==127 && bank==1);
    ram[0x7ded]=128;ram[0x5da2]=0x92;ram[0x5da3]=0x34;
    check(ms5::transfer_palette_frame(ram,palette,bank,error));
    check(palette[0]==0 && palette[1]==0 && ram[0x7ded]==0);
    std::vector<std::uint8_t> bank1(8192,0xaa);
    ram[0x7dea]=0x20;ram[0x7deb]=0;ram[0x7ded]=255;
    for (std::size_t i=0;i<32;++i) ram[0x7da2+i]=static_cast<std::uint8_t>(i);
    const std::vector<std::uint8_t> normal_bank=palette;
    check(ms5::transfer_palette_banks(ram,palette,bank1,bank,error));
    check(palette==normal_bank && bank1[0]==0 && bank1[1]==0 && bank1[33]==1);
    check(ram[0x7dea]==0 && ram[0x7deb]==0 && ram[0x7ded]==255);
    ram[0x7deb]=1;
    const std::vector<std::uint8_t> bad_counter=ram, saved_bank1=bank1;
    check(!ms5::transfer_palette_banks(ram,palette,bank1,bank,error));
    check(ram==bad_counter && bank1==saved_bank1 && palette==normal_bank);
    ram[0x7deb]=0;
    check(!ms5::transfer_palette_banks(ram,palette,palette,bank,error));
    check(palette==normal_bank);
    std::cout << "palette_transfer_test: passed\n";
}
