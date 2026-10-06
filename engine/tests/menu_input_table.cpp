#include "ms5/menu_input.h"
#include <fstream>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    std::ofstream output(argv[1], std::ios::binary | std::ios::trunc);
    if (!output) return 1;
    std::vector<std::uint8_t> ram(65536, 0);
    ram[0x7f13] = 0x10; ram[0x7f14] = 0x7e; ram[0x7f15] = 0xfe;
    const unsigned int flags[] = {0, 1, 2, 3, 255};
    ms5::MenuInput result;
    std::string error;
    for (unsigned int f = 0; f < 5; ++f) {
        ram[0x7f0b] = static_cast<std::uint8_t>(flags[f]);
        for (unsigned int a = 0; a < 256; ++a) {
            ram[0x4cba] = static_cast<std::uint8_t>(a);
            for (unsigned int b = 0; b < 256; ++b) {
                ram[0x4cc0] = static_cast<std::uint8_t>(b);
                ram[0x7f1a] = 0xa5;
                std::vector<std::uint8_t> expected(ram);
                if (!ms5::select_menu_input(ram, result, error)) return 1;
                expected[0x7f1a] = result.sources;
                if (ram != expected) return 1;
                const char bytes[] = {static_cast<char>(result.kind), static_cast<char>(result.event), static_cast<char>(result.sources)};
                output.write(bytes, 3);
            }
        }
    }
    output.close();
    return output ? 0 : 1;
}
