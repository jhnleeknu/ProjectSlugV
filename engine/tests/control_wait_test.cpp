#include "ms5/control_wait.h"
#include <cassert>
#include <iostream>
namespace {
void fail(std::vector<std::uint8_t>& ram,const ms5::FixedDataResource& menu,
          const ms5::FixedDataResource& pause) {
    const std::vector<std::uint8_t> before=ram;
    ms5::MenuFrameResult result;result.status=7;result.external_jump=8;result.line=9;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=1;writes[0].size=2;writes[0].value=3;
    std::string error;
    assert(!ms5::step_control_wait(ram,menu,pause,0x0603,0x7000,0x1feffc,result,writes,error));
    assert(!error.empty() && ram==before && result.status==7 && result.external_jump==8 && result.line==9);
    assert(writes.size()==1 && writes[0].address==1 && writes[0].size==2 && writes[0].value==3);
}
}
int main() {
    ms5::FixedDataResource menu,pause;
    pause.source_cpu_address=pause.source_rom_offset=0x9068;
    const unsigned char data[]={92,'l',18,26,92,'p',0,92,'c',3,'P','A','U','S','E',0,0,
                               92,'l',18,26,92,'c',3,' ',' ',' ',' ',' ',0};
    pause.data.assign(data,data+sizeof(data));
    std::vector<std::uint8_t> ram(65536,0);
    ram[0x7df0]=3;ram[0x12]=2;ram[0xfdb6]=ram[0xfdb7]=1;ram[0xf002]=1;
    ram[0x4cb5]=8;ram[0x4cb4]=1;ram[0x7df2]=0;
    ms5::MenuFrameResult result;std::vector<ms5::VideoPortWrite> writes;std::string error;
    assert(ms5::step_control_wait(ram,menu,pause,0,0x7000,0x1feffc,result,writes,error));
    assert(result.status==2 && ram[0x7df2]==1 && writes.empty()); // P1 held beats P2 menu.
    assert(ms5::step_control_wait(ram,menu,pause,0,0x7000,0x1feffc,result,writes,error));
    assert(result.status==0 && ram[0x7df2]==0);
    ram[0x4cb5]=9;
    assert(ms5::step_control_wait(ram,menu,pause,0,0x7000,0x1feffc,result,writes,error));
    assert(result.status==2 && ram[0x7df2]==15); // P1 new step beats P2 menu.
    ram[0x4cb5]=0;ram[0x4cb4]=0;ram[0x7df3]=1;
    assert(ms5::step_control_wait(ram,menu,pause,0x0603,0x7000,0x1feffc,result,writes,error));
    assert(result.status==0x63200000 && result.line==0x725a && ram[0x7df3]==255 && writes.size()==10);
    assert(writes[0].value==0x725a6320);
    ram[0x7df3]=0;
    assert(ms5::step_control_wait(ram,menu,pause,0x0603,0x7000,0x1feffc,result,writes,error));
    assert(ram[0x7df3]==254 && writes[0].value==0x725a0350);
    ram[0xf001]=0x40;
    assert(ms5::step_control_wait(ram,menu,pause,0x0603,0x7123,0x1feffc,result,writes,error));
    assert(writes.empty() && ram[0x7df3]==253 && result.line==0x7123);
    ram[0xf001]=0;pause.data.clear();fail(ram,menu,pause);
    ram[0x7dee]=1;fail(ram,menu,pause);
    ram[0x7dee]=0;ram[0x7df0]=0;fail(ram,menu,pause);
    ram.resize(5);fail(ram,menu,pause);
    std::cout << "Control wait priority, repeat/phase wrap and late-error rollback passed\n";
}
