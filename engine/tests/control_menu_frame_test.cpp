#include "ms5/control_menu_frame.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& data,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)data[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
void fail(std::vector<std::uint8_t>& ram,const ms5::FixedDataResource& menu,
          const ms5::FixedDataResource& pause,std::uint32_t stack) {
    const std::vector<std::uint8_t> before=ram;
    ms5::MenuFrameResult result;result.status=7;result.external_jump=8;result.line=9;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=1;writes[0].size=2;writes[0].value=3;
    std::string error;
    std::uint32_t d1=0xabcd0603U,d3=0x98767123U;
    assert(!ms5::step_control_menu(ram,menu,pause,0x0603,0x7123,stack,result,writes,error,
                                  NULL,NULL,&d1,&d3));
    assert(d1==0xabcd0603U && d3==0x98767123U);
    assert(!error.empty() && ram==before && result.status==7 && result.external_jump==8 && result.line==9);
    assert(writes.size()==1 && writes[0].address==1 && writes[0].size==2 && writes[0].value==3);
}
}
int main() {
    ms5::FixedDataResource menu,pause;
    menu.source_cpu_address=menu.source_rom_offset=0x200;
    menu.data.assign(32,0);put(menu.data,0,0x21e);put(menu.data,16,0x21e);
    put(menu.data,20,0x9488);put(menu.data,26,0xffffffffU);menu.data[30]='A';
    pause.source_cpu_address=pause.source_rom_offset=0x9079;
    const unsigned char data[]={92,'l',18,26,92,'c',3,' ',' ',' ',' ',' ',0};
    pause.data.assign(data,data+sizeof(data));
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0x7f0e,0x107efe);put(ram,0x7f12,0x107efe);put(ram,0x7f16,0x9332);
    put(ram,0x7efe,0x200);ram[0x7f04]=1;ram[0x7f1b]=2;
    ram[0x7dee]=255;ram[0x7df0]=3;ram[0x7dfb]=1;
    // Frame pops the root before the tail discovers the unsupported callback.
    ram[0x7df9]=1;fail(ram,menu,pause,0x1feffc);ram[0x7df9]=0;
    const ms5::FixedDataResource absent;
    fail(ram,menu,absent,0x1feffc);
    fail(ram,menu,pause,0x110102);fail(ram,menu,pause,0x1feffd);
    ram[0x7f1b]=3;fail(ram,menu,pause,0x1feffc);ram[0x7f1b]=2;
    ms5::MenuFrameResult result;std::vector<ms5::VideoPortWrite> writes;std::string error;
    std::uint32_t d1=0xabcd0603U,d3=0x98767123U;
    const std::vector<std::uint8_t> before_registers=ram;
    result.status=7;result.external_jump=8;result.line=9;
    writes.resize(1);writes[0].value=123;
    assert(!ms5::step_control_menu(ram,menu,pause,0x0604,0x7123,0x1feffc,result,writes,error,
                                  NULL,NULL,&d1,&d3));
    assert(!ms5::step_control_menu(ram,menu,pause,0x0603,0x7124,0x1feffc,result,writes,error,
                                  NULL,NULL,&d1,&d3));
    assert(ram==before_registers && d1==0xabcd0603U && d3==0x98767123U);
    assert(result.status==7 && result.external_jump==8 && result.line==9 && writes.size()==1 && writes[0].value==123);
    assert(ms5::step_control_menu(ram,menu,pause,0x0603,0x7123,0x1feffc,result,writes,error,
                                 NULL,NULL,&d1,&d3));
    assert(d1==0xabcd0603U && d3==0x725aU);
    assert(result.status==1 && result.line==0x725a && result.external_jump==0);
    assert(writes.size()==10 && writes[0].value==0x725a6320);
    assert(ram[0x7f10]==0x7f && ram[0x7f11]==0x0e && ram[0x7dee]==0 && ram[0x7df0]==0 && ram[0x7df3]==255);
    fail(ram,menu,pause,0x1feffc);
    std::cout << "Control menu final pop, style preservation and late-error rollback passed\n";
}
