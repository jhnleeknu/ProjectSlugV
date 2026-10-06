#include "ms5/control_finish.h"
#include <cassert>
#include <iostream>
namespace {
void fail(std::vector<std::uint8_t>& ram,const ms5::FixedDataResource& pause) {
    const std::vector<std::uint8_t> before=ram;
    ms5::MenuFrameResult result;result.status=7;result.external_jump=8;result.line=9;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=1;writes[0].size=2;writes[0].value=3;
    std::string error;
    assert(!ms5::finish_control_menu(ram,pause,0xffffffffU,0x0603,0x7000,result,writes,error));
    assert(!error.empty() && ram==before && result.status==7 && result.external_jump==8 && result.line==9);
    assert(writes.size()==1 && writes[0].address==1 && writes[0].size==2 && writes[0].value==3);
}
}
int main() {
    ms5::FixedDataResource pause;
    pause.source_cpu_address=pause.source_rom_offset=0x9079;
    const unsigned char data[]={92,'l',18,26,92,'c',3,' ',' ',' ',' ',' ',0};
    pause.data.assign(data,data+sizeof(data));
    std::vector<std::uint8_t> ram(65536,0);
    ram[0x7dee]=255;ram[0x7df0]=3;ram[0x7dfb]=1;
    ram[0x4caa]=0xaa;ram[0x7dfc]=0x88;ram[0x4cab]=0x10;
    ms5::MenuFrameResult result;std::vector<ms5::VideoPortWrite> writes;std::string error;
    // Continued frame ignores callback and exit flag, and clears only D0 low word.
    ram[0x7df9]=1;
    assert(ms5::finish_control_menu(ram,pause,0xffff1200U,0x0603,0x7123,result,writes,error));
    assert(result.status==-65536 && result.line==0x7123 && writes.empty());
    assert(ram[0x7dee]==255 && ram[0x7df0]==3 && ram[0x7df3]==255 && ram[0x4cab]==0x32);
    fail(ram,pause);ram[0x7df9]=0;
    // A bytewise test would incorrectly treat 0101 as the exit value1.
    ram[0x7dfa]=1;
    assert(ms5::finish_control_menu(ram,pause,0x800012ffU,0x0603,0x7123,result,writes,error));
    assert(result.status==-2147478785 && result.line==0x7123 && writes.empty());
    assert(ram[0x7dee]==0 && ram[0x7df0]==3);
    ram[0x7dee]=255;ram[0x7dfa]=0;
    assert(ms5::finish_control_menu(ram,pause,0xffffffffU,0x0603,0x7123,result,writes,error));
    assert(result.status==1 && result.line==0x725a && writes.size()==10);
    assert(writes[0].value==0x725a6320 && ram[0x7dee]==0 && ram[0x7df0]==0);
    // Failure after the candidate menu flag changed must roll back all outputs.
    ram[0x7dee]=255;pause.data.pop_back();fail(ram,pause);
    ram.resize(5);fail(ram,pause);
    std::cout << "Control finish width, palette and transactional error tests passed\n";
}
