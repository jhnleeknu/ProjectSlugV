#include "ms5/menu_input.h"
#include <cassert>
#include <iostream>

int main() {
    std::vector<std::uint8_t> ram(65536, 0);
    ms5::MenuInput out;
    out.kind = ms5::MenuInputEvent; out.event = 99; out.sources = 77;
    std::string error;
    const std::vector<std::uint8_t> invalid = ram;
    std::uint32_t d1=0xabcdef12U;
    assert(!ms5::select_menu_input(ram, out, error,&d1));
    assert(d1==0xabcdef12U);
    assert(ram == invalid && out.event == 99 && out.sources == 77);
    ram[0x7f13] = 0x10; ram[0x7f14] = 0x7e; ram[0x7f15] = 0xfe;
    ram[0x7f0b] = 3;
    ram[0x4cba] = 0x10; ram[0x4cc0] = 0x20;
    assert(ms5::select_menu_input(ram, out, error,&d1));
    assert(d1==0x20U);
    assert(out.kind == ms5::MenuInputEvent && out.event == 4 && out.sources == 2);
    ram[0x4cba] = ram[0x4cc0] = 1;
    assert(ms5::select_menu_input(ram, out, error));
    assert(out.kind == ms5::MenuInputPrevious && out.event == 0 && out.sources == 3);
    ram[0x7f0b] = 0;
    assert(ms5::select_menu_input(ram, out, error));
    assert(out.kind == ms5::MenuInputNone && ram[0x7f1a] == 0);
    ram.resize(1);
    assert(!ms5::select_menu_input(ram, out, error));
    assert(out.kind == ms5::MenuInputNone && out.sources == 0);
    std::cout << "Menu input invalid state and output preservation passed\n";
}
