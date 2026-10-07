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
    std::uint32_t d1=0xabcd0000U,d3=0x98767000U;
    assert(!ms5::step_control_caller(ram,absent,absent,records,0x100100,0,0x7000,stack,boundary,writes,error,
                                    NULL,NULL,&d1,&d3));
    assert(d1==0xabcd0000U && d3==0x98767000U);
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
    std::uint32_t d1=0xabcd0000U,d3=0x98767000U;
    const std::vector<std::uint8_t> before_registers=ram;
    writes.resize(1);writes[0].value=123;
    assert(!ms5::step_control_caller(ram,absent,absent,records,0x100100,1,0x7000,
                                   0x1feffc,boundary,writes,error,NULL,NULL,&d1,&d3));
    assert(!ms5::step_control_caller(ram,absent,absent,records,0x100100,0,0x7001,
                                   0x1feffc,boundary,writes,error,NULL,NULL,&d1,&d3));
    assert(ram==before_registers && boundary==123 && d1==0xabcd0000U && d3==0x98767000U);
    assert(writes.size()==1 && writes[0].value==123);
    assert(ms5::step_control_caller(ram,absent,absent,records,0x100100,0,0x7000,
                                  0x1feffc,boundary,writes,error,NULL,NULL,&d1,&d3));
    // Fade divides fc00 by4, then its first tick writes the middle-byte
    // difference (0 - ff = 1) into D1.lowbyte. Native f54 returns ff01/4.
    assert(d1==0x0000ff01U && d3==4U);
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
