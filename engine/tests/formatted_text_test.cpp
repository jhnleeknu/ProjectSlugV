#include "ms5/formatted_text.h"
#include <cassert>
#include <iostream>
#include <cstring>
namespace {
void put(std::vector<std::uint8_t>& bytes,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)bytes[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
void text(ms5::FixedDataResource& resource,std::size_t at,const char* value) {
    const std::size_t count=std::strlen(value)+1;
    for(std::size_t i=0;i<count;++i)resource.data[at+i]=static_cast<std::uint8_t>(value[i]);
}
}
int main() {
    std::vector<ms5::FixedDataResource> resources(1);
    resources[0].source_cpu_address=resources[0].source_rom_offset=0x60000;
    resources[0].data.assign(8192,0);
    ms5::FixedDataResource font;
    font.source_cpu_address=font.source_rom_offset=0xe80c8;
    font.data.assign(1024,0);
    for(unsigned int i=0;i<512;++i) {
        font.data[2*i]=3;font.data[2*i+1]=static_cast<std::uint8_t>(i);
    }
    std::vector<std::uint8_t> ram(65536,0xa5);
    put(ram,0x7000,0x61000);
    std::vector<std::uint8_t> arguments;
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    text(resources[0],0,"X%s!");text(resources[0],0x1000,"AB");
    assert(ms5::format_fixed_text(ram,resources,font,0x60000,0x107000,arguments,0x7234,3,writes,error));
    assert(writes.size()==8 && writes[0].value==0x72340358U);
    assert(writes[2].value==0x72540341U && writes[4].value==0x72740342U);
    assert(writes[6].value==0x72940321U);
    assert(ram[0x4cd8]==0x72 && ram[0x4cd9]==0); // SEQ.B D3 quirk.
    text(resources[0],0,"%02x");resources[0].data[0x1000]=1;
    assert(ms5::format_fixed_text(ram,resources,font,0x60000,0x107000,arguments,0x7000,3,writes,error));
    assert(writes.size()==4 && writes[0].value==0x70000330U && writes[2].value==0x70200331U);
    text(resources[0],0,"%2x");
    assert(ms5::format_fixed_text(ram,resources,font,0x60000,0x107000,arguments,0x7000,3,writes,error));
    assert(writes[0].value==0x70000320U && writes[2].value==0x70200331U);
    // Caller-provided external stack argument table retains original CPU pointers.
    arguments.assign(4,0);put(arguments,0,0x61000);
    assert(ms5::format_fixed_text(ram,resources,font,0x60000,0x1fefe0,arguments,0x7000,3,writes,error));
    assert(ram[0x4ce4]==0 && ram[0x4ce5]==0x1f && ram[0x4ce6]==0xef && ram[0x4ce7]==0xe4);
    const std::vector<std::uint8_t> saved=ram;
    const std::uint32_t first=writes[0].value;
    const char* invalid[]={"A%0x","A%65536s","A%q","A%9x","A\\cQZ"};
    for(unsigned int i=0;i<5;++i) {
        text(resources[0],0,invalid[i]);
        if(i==3)put(arguments,0,0x61fff); // Width9 exhausts mapped data.
        assert(!ms5::format_fixed_text(ram,resources,font,0x60000,0x1fefe0,arguments,0x7000,3,writes,error));
        assert(ram==saved && writes.size()==4 && writes[0].value==first);
    }
    text(resources[0],0,"A%s");put(arguments,0,0x900000);
    assert(!ms5::format_fixed_text(ram,resources,font,0x60000,0x1fefe0,arguments,0x7000,3,writes,error));
    assert(ram==saved && writes[0].value==first);
    resources.push_back(resources[0]);
    assert(!ms5::format_fixed_text(ram,resources,font,0x60000,0x107000,arguments,0x7000,3,writes,error));
    assert(ram==saved);
    std::cout << "Formatted text state, padding, external arguments and rollback passed\n";
}
