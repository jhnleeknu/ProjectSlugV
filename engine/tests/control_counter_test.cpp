#include "ms5/control_counter.h"
#include <cassert>
#include <iostream>
int main() {
    std::vector<std::uint8_t> ram(65536,0);
    bool trap=true;std::string error;
    ram[0x0e]=ram[0x0f]=ram[0x17e]=ram[0x17f]=255;ram[0xd494]=255;
    assert(ms5::advance_control_counter(ram,0x100100,trap,error) && !trap);
    assert(ram[0x0e]==0 && ram[0x0f]==0 && ram[0x17e]==0 && ram[0x17f]==0 && ram[0xd494]==2);
    ram[0x0e]=1;const std::vector<std::uint8_t> before=ram;
    assert(ms5::advance_control_counter(ram,0x100100,trap,error) && trap && ram==before);
    assert(!ms5::advance_control_counter(ram,0x10ff82,trap,error) && trap && ram==before);
    assert(!ms5::advance_control_counter(ram,0x100001,trap,error) && trap && ram==before);
    // Counter increment crosses high-byte parity before43dbc reads that byte.
    ram[0x0e]=0;ram[0x0f]=255;ram[0xd494]=0;ram[0xd495]=255;
    assert(ms5::advance_control_counter(ram,0x10d416,trap,error) && !trap);
    assert(ram[0x0e]==1 && ram[0x0f]==0 && ram[0xd494]==2 && ram[0xd495]==0);
    ram.resize(5);const std::vector<std::uint8_t> short_before=ram;
    assert(!ms5::advance_control_counter(ram,0x100100,trap,error) && !trap && ram==short_before);
    std::cout << "Control counter wrap, trap boundary, phase alias and invalid-input tests passed\n";
}
