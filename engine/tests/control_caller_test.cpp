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
    // Nonzero status with a nonzero previous state only replaces D1.byte.
    ram.assign(65536,0); ram[0x184]=2;
    std::uint32_t d1=0x123456a5U; std::uint32_t d3=0xdeadbeefU;
    assert(ms5::consume_control_result(ram,records,0x100100,2,boundary,writes,error,&d1,&d3));
    assert(boundary==0 && d1==0x12345602U && d3==0xdeadbeefU && writes.empty());

    // Already-at-target channels produce zero deltas and skip preparation.
    ram.assign(65536,0); ram[0x184]=1; ram[0x7ded]=128;
    ram[0x7dc2]=ram[0x7dc4]=ram[0x7dc6]=0xfc;
    d1=0x89abcdefU; d3=0xfedcba98U;
    assert(ms5::consume_control_result(ram,records,0x100100,0,boundary,writes,error,&d1,&d3));
    assert(boundary==0xec4 && d1==0xffff0000U && d3==0);
    assert(ram[0x7dd4]==0 && writes.size()==1 && writes[0].address==0x3c0006U);

    // Missing palette after effect arithmetic preserves both scratch registers.
    ram.assign(65536,0); ram[0x184]=1;
    const std::vector<std::uint8_t> register_rollback=ram;
    const std::vector<ms5::PaletteRecord> absent;
    d1=0x76543210U; d3=0x01234567U; boundary=0xabcdefU;
    ms5::VideoPortWrite sentinel;
    sentinel.address=0x3c0000U; sentinel.size=4; sentinel.value=0x11223344U;
    writes.assign(1,sentinel);
    assert(!ms5::consume_control_result(ram,absent,0x100100,0,boundary,writes,error,&d1,&d3));
    assert(!error.empty() && ram==register_rollback && boundary==0xabcdefU);
    assert(d1==0x76543210U && d3==0x01234567U);
    assert(writes.size()==1 && writes[0].address==0x3c0000U &&
           writes[0].size==4 && writes[0].value==0x11223344U);
    ram.resize(5);fail(ram);
    std::cout << "Control caller video/palette order, trap commit and late-failure rollback passed\n";
}
