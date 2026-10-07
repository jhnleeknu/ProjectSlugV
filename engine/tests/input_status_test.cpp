#include "ms5/input_status.h"
#include <cassert>
#include <iostream>
int main() {
    ms5::FixedDataResource table;
    table.source_cpu_address=table.source_rom_offset=0xb58;
    table.data.assign(256,0);
    table.data[0]=1;table.data[255]=2;table.data[5]=3;
    std::vector<std::uint8_t> ram(65536,0xa5);
    ram[0xf006]=0xa4;ram[0xfdaf]=0x72;
    ram[0xfdb6]=252;ram[0xfdb7]=251;ram[0xfdb8]=0;ram[0xfdb9]=0;
    std::vector<std::uint8_t> expected=ram;
    expected[0xf006]=0xa0;expected[0x12]=0x72;
    expected[0xfdb8]=1;expected[0xf007]=7;
    std::string error;
    assert(ms5::update_input_status(ram,table,error));
    assert(ram==expected && error.empty());
    // Repeated calls retain slots; pending bits are consumed once.
    assert(ms5::update_input_status(ram,table,error));assert(ram==expected);
    ms5::FixedDataResource absent;
    assert(!ms5::update_input_status(ram,absent,error));assert(ram==expected);
    // A failure in status lookup must roll back the preceding successful sample.
    ram[0x4cd4]=0;expected=ram;
    ms5::InputPortSamples ports={255,254,253,251,247};
    std::uint8_t reads=91;
    assert(!ms5::step_input(ram,absent,absent,ports,reads,error));
    assert(ram==expected && reads==91);
    assert(ms5::step_input(ram,absent,table,ports,reads,error));
    assert(reads==5 && ram[0x4caa]==4 && ram[0x4cb0]==8 && ram[0xf007]==7);
    expected=ram;ram.resize(65535);expected=ram;
    assert(!ms5::step_input(ram,absent,table,ports,reads,error));
    assert(ram==expected && reads==5);
    std::cout<<"Input status byte wrap, pending bits and integrated rollback passed\n";
}
