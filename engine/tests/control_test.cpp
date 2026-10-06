#include "ms5/control.h"
#include <cassert>
#include <iostream>
namespace {
void fail(std::vector<std::uint8_t>& ram) {
    const std::vector<std::uint8_t> before=ram;
    const ms5::FixedDataResource absent;
    ms5::MenuFrameResult result;result.status=7;result.external_jump=8;result.line=9;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=1;writes[0].size=2;writes[0].value=3;
    std::string error;
    assert(!ms5::step_control(ram,absent,absent,0,0x7000,0x1feffc,result,writes,error));
    assert(!error.empty() && ram==before && result.status==7 && result.external_jump==8 && result.line==9);
    assert(writes.size()==1 && writes[0].address==1 && writes[0].size==2 && writes[0].value==3);
}
}
int main() {
    const ms5::FixedDataResource absent;
    std::vector<std::uint8_t> ram(65536,0);
    ms5::MenuFrameResult result;std::vector<ms5::VideoPortWrite> writes(1);std::string error="old";
    // Inactive branch wins even if the menu flag is stale. No resource/stack use.
    ram[0x7dee]=255;ram[0x7df1]=3;
    assert(ms5::step_control(ram,absent,absent,0,0x7123,1,result,writes,error));
    assert(result.status==0 && result.line==0x7123 && result.external_jump==0 && writes.empty() && error.empty());
    assert(ram[0x7df0]==3 && ram[0x7df1]==0 && ram[0x7dee]==255 && ram[0x7df3]==255);
    fail(ram); // Now active: stale menu state is not silently ignored.
    ram[0x7dee]=0;ram[0xf002]=1;ram[0x4cb5]=1;
    assert(ms5::step_control(ram,absent,absent,0,0x7123,1,result,writes,error));
    assert(result.status==2 && ram[0x7df2]==15 && ram[0x7df3]==254);
    ram[0x4cb5]=0;ram[0x4cb4]=1;ram[0x7df2]=0;
    assert(ms5::step_control(ram,absent,absent,0,0x7123,1,result,writes,error));
    assert(result.status==2 && ram[0x7df2]==1 && ram[0x7df3]==253);
    ram[0x4cb4]=0;fail(ram); // Idle display needs the native pause resource.
    ram[0x7df0]=0;ram[0x7def]=1;ram[0xf000]=0;
    const std::vector<std::uint8_t> before=ram;
    assert(ms5::step_control(ram,absent,absent,0,0x7654,1,result,writes,error));
    assert(result.status==1 && result.line==0x7654 && ram==before && writes.empty());
    ram.resize(5);fail(ram);
    std::cout << "Unified control branch ordering, carry state and failure preservation passed\n";
}
