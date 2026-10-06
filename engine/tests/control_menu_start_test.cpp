#include "ms5/control_menu_start.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& data,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)data[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
void fails(std::vector<std::uint8_t>& ram,const ms5::FixedDataResource& menu,std::uint32_t stack) {
    const std::vector<std::uint8_t> before=ram;
    ms5::MenuFrameResult result;result.status=17;result.external_jump=123;result.line=456;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=7;writes[0].size=2;writes[0].value=789;
    std::string error;
    assert(!ms5::start_control_menu(ram,menu,0x7000,stack,result,writes,error));
    assert(!error.empty() && ram==before && result.status==17 && result.external_jump==123 && result.line==456);
    assert(writes.size()==1 && writes[0].address==7 && writes[0].size==2 && writes[0].value==789);
}
}
int main() {
    ms5::FixedDataResource menu;
    menu.source_cpu_address=menu.source_rom_offset=0x93e0;
    menu.data.assign(32,0);put(menu.data,0,0x93fe);put(menu.data,16,0x93fe);
    put(menu.data,20,0x9488);put(menu.data,26,0xffffffffU);menu.data[30]='A';
    std::vector<std::uint8_t> ram(65536,0xa5);
    ram[0x7df3]=0;ram[0x4caa]=0xf0;ram[0x7dfc]=0x30;ram[0x4cab]=1;
    ram[0x4cb0]=0x0f;ram[0x7dfd]=3;ram[0x4cb1]=0x80;
    std::string error;ms5::MenuFrameResult result;std::vector<ms5::VideoPortWrite> writes;
    fails(ram,menu,0x110102);fails(ram,menu,0x1feffd);
    ms5::FixedDataResource invalid=menu;put(invalid.data,6,0x1234);
    fails(ram,invalid,0x1feffc); // Initialization/773 queued writes precede frame validation.
    assert(ms5::start_control_menu(ram,menu,0x7000,0x1feffc,result,writes,error));
    assert(writes.size()==773 && writes[0].value==0x75000000 && writes[767].value==0x77ff0000);
    assert(writes[768].value==0x75000200 && writes[772].value==0x7580ff02);
    assert(ram[0x4cab]==0xc1 && ram[0x4cb1]==0x8c && ram[0x7df3]==255);
    assert(ram[0x7dee]==255 && ram[0x7dfa]==0 && ram[0x7dfb]==0 && ram[0x7f1b]==1);
    assert(ram[0x7f18]==0x93 && ram[0x7f19]==0x32 && result.status==0 && result.external_jump==0);
    ram.resize(5);fails(ram,menu,0x1feffc);
    std::cout << "Control menu startup writes, input edges and late-failure rollback passed\n";
}
