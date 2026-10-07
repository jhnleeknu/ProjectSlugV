#include "ms5/control_caller.h"
#include <cassert>
#include <iostream>
namespace {
void fail(std::vector<std::uint8_t>& ram) {
    const std::vector<std::uint8_t> before=ram;
    const std::vector<ms5::PaletteRecord> absent;
    std::uint32_t boundary=123;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=1;writes[0].size=2;writes[0].value=3;
    std::string error;
    assert(!ms5::consume_control_result(ram,absent,0x100100,0,boundary,writes,error));
    assert(!error.empty() && ram==before && boundary==123);
    assert(writes.size()==1 && writes[0].address==1 && writes[0].size==2 && writes[0].value==3);
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0);
    ram[0x184]=1;ram[0x4d90]=255;ram[0x4d91]=0xf7;
    fail(ram); // Video changed, palette saved and dirty flags set before missing ID.
    ms5::PaletteRecord record={};record.id=0;
    std::vector<ms5::PaletteRecord> records(1,record);
    std::vector<ms5::VideoPortWrite> writes;std::string error;std::uint32_t boundary=123;
    assert(ms5::consume_control_result(ram,records,0x100100,0xdeadbe00U,boundary,writes,error));
    assert(boundary==0xec4 && ram[0x184]==0 && ram[0x180]==255);
    assert(ram[0x182]==1 && ram[0x183]==0 && ram[0x7dd4]==3 && ram[0x7dc2]==255);
    assert(writes.size()==261 && writes[0].address==0x3c0006 && writes[0].value==255);
    for(std::size_t i=1;i<257;++i)assert(writes[i].address==0x300001 && writes[i].size==1 && writes[i].value==1);
    assert(writes[257].address==0x2ffff2 && writes[257].value==0x1000 && writes[258].address==0x2ffff0);
    assert(ms5::consume_control_result(ram,records,0x100100,0xdeadbe02U,boundary,writes,error));
    assert(boundary==0 && ram[0x184]==2 && ram[0x180]==0 && ram[0x7dd4]==1);
    assert(ram[0x17f]==1 && ram[0x0f]==1 && ram[0xd494]==1);
    assert(writes.size()==1 && writes[0].address==0x3c0006 && writes[0].value==0xfff7);
    ram[0x184]=0;ram[0x180]=255;ram[0x0f]=2;
    assert(ms5::consume_control_result(ram,records,0x100100,1,boundary,writes,error));
    assert(boundary==0xfee && ram[0x184]==1 && ram[0x180]==0 && ram[0x17f]==1 && ram[0x0f]==2);
    assert(writes.size()==1); // A trap boundary commits earlier restoration.
    ram.resize(5);fail(ram);
    std::cout << "Control caller video/palette order, trap commit and late-failure rollback passed\n";
}
