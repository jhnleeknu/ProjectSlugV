#include "ms5/control_caller_step.h"
#include <cassert>
#include <iostream>
namespace {
void fail(std::vector<std::uint8_t>& ram,std::uint32_t stack) {
    const std::vector<std::uint8_t> before=ram;
    const ms5::FixedDataResource absent;
    const std::vector<ms5::PaletteRecord> records;
    std::uint32_t boundary=123;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=1;writes[0].size=2;writes[0].value=3;
    std::string error;
    assert(!ms5::step_control_caller(ram,absent,absent,records,0x100100,0,0x7000,stack,boundary,writes,error));
    assert(ram==before && boundary==123 && !error.empty());
    assert(writes.size()==1 && writes[0].address==1 && writes[0].size==2 && writes[0].value==3);
}
}
int main() {
    const ms5::FixedDataResource absent;
    const std::vector<ms5::PaletteRecord> records;
    std::vector<std::uint8_t> ram(65536,0);
    ram[0x7df1]=1;ram[0x184]=1;ram[0x4d90]=255;ram[0x4d91]=0xf7;
    fail(ram,0x1feffc); // Activation completes before missing palette ID fails.
    fail(ram,0x110106);fail(ram,0x1feffd);
    ram[0x7ded]=128;
    std::uint32_t boundary=123;std::string error;std::vector<ms5::VideoPortWrite> writes;
    assert(ms5::step_control_caller(ram,absent,absent,records,0x100100,0,0x7000,
                                  0x1feffc,boundary,writes,error));
    assert(boundary==0xec4 && ram[0x7df0]==1 && ram[0x7df1]==0 && ram[0x184]==0);
    assert(ram[0x7df3]==255 && ram[0x7dd4]==3 && writes.size()==257);
    ram[0xf002]=1;ram[0x4cb5]=1;
    assert(ms5::step_control_caller(ram,absent,absent,records,0x100100,0,0x7000,
                                  0x1feffc,boundary,writes,error));
    assert(boundary==0 && ram[0x184]==2 && ram[0x7df2]==15 && ram[0x180]==0);
    assert(ram[0x0f]==1 && ram[0x17f]==1 && writes.size()==1 && writes[0].value==0xfff7);
    ram[0x0f]=2;
    assert(ms5::step_control_caller(ram,absent,absent,records,0x100100,0,0x7000,
                                  0x1feffc,boundary,writes,error));
    assert(boundary==0xfee && ram[0x7df3]==253 && writes.empty());
    ram.resize(5);fail(ram,0x1feffc);
    std::cout << "Full control caller activation, resume, trap commit and late rollback passed\n";
}
