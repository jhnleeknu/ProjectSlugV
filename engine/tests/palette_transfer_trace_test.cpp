#include "ms5/palette_transfer.h"
#include <cassert>
#include <iostream>
int main() {
    std::vector<std::uint8_t> ram(65536,0),p0(8192,0x55),p1(8192,0x66);
    std::vector<ms5::VideoPortWrite> writes;std::string error;std::uint8_t bank=1;std::uint32_t d0=0xabcd1234;
    assert(ms5::transfer_palette_banks_traced(ram,p0,p1,bank,d0,writes,error));
    assert(d0==0xabcd1234 && writes.size()==2 && writes[0].address==0x300001 && writes[0].value==0x34 && bank==0);
    ram[0x7ded]=128;ram[0x5da2]=255;ram[0x5da3]=255;ram[0x5da4]=0x12;ram[0x5da5]=0x78;
    assert(ms5::transfer_palette_banks_traced(ram,p0,p1,bank,d0,writes,error));
    assert(writes.size()==11 && writes[0].value==0x34 && writes[1].value==0x1278 && d0==0x1278);
    assert(writes[9].address==0x300001 && writes[9].value==0x78);
    ram[0x7dea]=0x20;ram[0x7deb]=0;ram[0x7dec]=1;
    for(unsigned int i=0;i<32;++i) ram[0x7da2+i]=static_cast<std::uint8_t>(i);
    assert(ms5::transfer_palette_banks_traced(ram,p0,p1,bank,d0,writes,error));
    assert(writes.size()==2051 && d0==0x00010203 && bank==1);
    assert(writes[0].address==0x3a001f && writes[0].value==0x78);
    assert(writes[1].address==0x401ffc && writes[1].value==0x1c1d1e1f);
    assert(writes[2048].address==0x400000 && writes[2048].value==0x00010203);
    assert(writes[2049].size==2 && writes[2049].value==0 && p1[0]==0 && p1[1]==0);
    const std::vector<std::uint8_t> saved=p0;ram[0x7deb]=1;
    assert(!ms5::transfer_palette_banks_traced(ram,p0,p1,bank,d0,writes,error));
    assert(p0==saved && ram[0x7deb]==1 && writes.size()==2051 && d0==0x00010203);
    assert(!ms5::transfer_palette_banks_traced(ram,p0,p0,bank,d0,writes,error));
    std::cout<<"Palette trace D0, masked slot, descending fill and error preservation passed\n";
}
