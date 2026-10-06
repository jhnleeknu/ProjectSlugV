#include "ms5/palette_prepare.h"
#include <cstdlib>
#include <iostream>
void check(bool value) { if (!value) { std::cerr << "palette preparation test failed\n"; std::exit(1); } }
int main() {
    std::vector<std::uint8_t> ram(65536, 0);
    ms5::PaletteRecord record = {};
    record.id = 0;
    record.hardware_words[1] = 0x1234;
    std::vector<ms5::PaletteRecord> records(1, record);
    std::string error;
    ram[0x4da1] = 0x80;
    ram[0x4db1] = 0x80;
    ram[0x4dad] = 1; // second node source differs from target
    const std::vector<std::uint8_t> before = ram;
    check(!ms5::prepare_palettes(ram, records, error) && ram == before);
    ram[0x4dad] = 0;
    ram[0x7dc2] = 1;
    const std::vector<std::uint8_t> effect = ram;
    check(!ms5::prepare_palettes(ram, records, error) && ram == effect);
    ram[0x4da1] = ram[0x4db1] = 0x82;
    check(ms5::prepare_palettes(ram, records, error));
    check(ram[0x5da2] == 0x80 && ram[0x5da4] == 0x12 && ram[0x5da5] == 0x34);
    check(ram[0x7dd5] == 255 && ram[0x7ded] == 255);
    records.clear();
    check(ms5::prepare_palettes(ram, records, error)); // clean slots need no resource
    check(ram[0x7dd5] == 0 && ram[0x7ded] == 0);
    ram[0x4da1] = 0x82;
    const std::vector<std::uint8_t> missing = ram;
    check(!ms5::prepare_palettes(ram, records, error) && ram == missing);
    records.assign(2, record);
    check(!ms5::prepare_palettes(ram, records, error) && ram == missing);
    std::cout << "palette_prepare_test: passed\n";
}
