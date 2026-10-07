#include "ms5/input_control.h"
#include <cassert>
#include <iostream>
int main() {
    ms5::FixedDataResource absent,table;
    table.source_cpu_address=table.source_rom_offset=0xb58;table.data.assign(256,0);
    const std::vector<ms5::PaletteRecord> records;
    ms5::InputPortSamples ports={255,255,255,255,255};
    std::vector<std::uint8_t> ram(65536,0);
    ram[0x7df1]=1;ram[0x184]=1;ram[0x4d90]=255;ram[0x4d91]=0xf7;
    ram[0x16]=7;ram[0x4ca2]=5;
    const std::vector<std::uint8_t> before=ram;
    ms5::InputFrameResult result;result.next_pc=91;result.style=92;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=123;
    std::string error;
    assert(!ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0xabcd,0x7000,0x1feffc,result,writes,error));
    assert(ram==before && result.next_pc==91 && result.style==92 && writes.size()==1 && writes[0].address==123);
    ram[0x7ded]=128;
    assert(ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0xabcd,0x7000,0x1feffc,result,writes,error));
    assert(result.next_pc==0xec4 && result.style==0xab00 && result.read_count==5);
    assert(ram[0x1a]==7 && ram[0x16]==0 && ram[0x4ca2]==0 && ram[0x7df0]==1 && writes.size()==257);
    ram[0xf002]=1;ports.system=254;
    assert(ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0,0x7000,0x1feffc,result,writes,error));
    assert(result.next_pc==0 && ram[0x184]==2 && ram[0x0f]==1 && writes.size()==1);
    // A callback boundary bypasses all controller resources and stack checks.
    ram.assign(65536,0);ram[0x176]=0x12;ram[0x17d]=0xab;
    assert(ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0,0,1,result,writes,error));
    assert(result.next_pc==0xf3c && result.callback==0x12000000 && result.callback_context==0xab && writes.empty());
    std::cout<<"Input/controller activation, resume, callback bypass and late rollback passed\n";
}
