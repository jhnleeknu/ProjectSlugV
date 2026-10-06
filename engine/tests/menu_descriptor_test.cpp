#include "ms5/menu_descriptor.h"
#include <cassert>
#include <iostream>

static ms5::FixedDataResource resource(unsigned int count) {
    ms5::FixedDataResource value;
    value.source_cpu_address = value.source_rom_offset = 0x200;
    value.data.assign(16 + count * 10 + 4, 0);
    for (unsigned int byte = 0; byte < 4; ++byte) {
        value.data[16 + count * 10 + byte] = 255;
    }
    return value;
}

int main() {
    ms5::MenuDescriptor result;
    std::string error;
    ms5::FixedDataResource data = resource(0);
    assert(ms5::decode_menu_descriptor(data, 0x200, result, error));
    assert(result.items.empty() && result.end_cpu_address == 0x214);
    data = resource(255);
    assert(ms5::decode_menu_descriptor(data, 0x200, result, error));
    assert(result.items.size() == 255);
    const std::uint32_t end = result.end_cpu_address;
    data = resource(256);
    assert(!ms5::decode_menu_descriptor(data, 0x200, result, error));
    assert(result.items.size() == 255 && result.end_cpu_address == end);
    data = resource(1);
    data.data[16] = data.data[17] = data.data[18] = 255;
    data.data[19] = 254; // fffffffe is an item, not the terminator.
    assert(ms5::decode_menu_descriptor(data, 0x200, result, error));
    assert(result.items.size() == 1 && result.items[0].title_address == 0xfffffffeU);
    for (unsigned int size = 0; size < 30; ++size) {
        ms5::FixedDataResource truncated = data;
        truncated.data.resize(size);
        assert(!ms5::decode_menu_descriptor(truncated, 0x200, result, error));
        assert(result.items.size() == 1 && result.items[0].title_address == 0xfffffffeU);
    }
    assert(!ms5::decode_menu_descriptor(data, 0x201, result, error));
    assert(!ms5::decode_menu_descriptor(data, 0x100, result, error));
    data.source_rom_offset = 0x202;
    assert(!ms5::decode_menu_descriptor(data, 0x200, result, error));
    std::cout << "Menu descriptor boundaries and failure preservation passed\n";
}
