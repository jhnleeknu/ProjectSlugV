#include "ms5/main_startup.h"
#include "ms5/palette_state.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& bytes,std::size_t at,unsigned int value) {
    bytes[at] = static_cast<std::uint8_t>(value >> 8); bytes[at + 1] = static_cast<std::uint8_t>(value);
}
unsigned int word(const std::vector<std::uint8_t>& bytes,std::size_t at) {
    return (static_cast<unsigned int>(bytes[at]) << 8) | bytes[at + 1];
}
ms5::FixedDataResource table() {
    ms5::FixedDataResource bindings;
    bindings.source_cpu_address = bindings.source_rom_offset = 0xe7b58;
    bindings.data.assign(104,0);
    for (unsigned int slot = 0; slot < 17; ++slot) {
        put(bindings.data,slot * 6,slot); put(bindings.data,slot * 6 + 2,7);
        bindings.data[slot * 6 + 4] = 2;
    }
    put(bindings.data,102,0xffff);
    return bindings;
}
void fails(std::vector<std::uint8_t>& ram,const ms5::FixedDataResource& bindings,std::size_t object) {
    const std::vector<std::uint8_t> before = ram;
    std::uint32_t d0 = 0x123456ab,d1 = 0x9876abcd,d3 = 0xbeef1234;
    std::vector<ms5::VideoPortWrite> ports(1);
    ports[0].size = 2; ports[0].address = 123; ports[0].value = 456;
    std::string error;
    assert(!ms5::initialize_main_frame(ram,object,bindings,d0,d1,d3,ports,error));
    assert(ram == before && d0 == 0x123456ab && d1 == 0x9876abcd && d3 == 0xbeef1234 && !error.empty());
    assert(ports.size() == 1 && ports[0].size == 2 && ports[0].address == 123 && ports[0].value == 456);
}
}
int main() {
    ms5::FixedDataResource bindings = table();
    std::vector<std::uint8_t> ram(65536,0);
    std::string error;
    assert(ms5::initialize_palette_state(&ram[0],ram.size(),error));
    const std::size_t base = 0x4d92;
    ram[base + 5 * 16 + 14] = 19;
    // A normal-reference node outside the fixed destinations remains untouched.
    put(ram,base + 30 * 16 + 8,3);
    put(ram,base + 30 * 16 + 10,0x1234); ram[base + 30 * 16 + 14] = 23;
    // A fixed node in the free ring is released to its tail before binding.
    put(ram,base + 20 * 16 + 8,0xffff);
    put(ram,base + 20 * 16 + 10,0x4567); ram[base + 20 * 16 + 14] = 17;
    put(ram,0x0e,0x1234); put(ram,0x200 + 0x7e,0x5678);
    ram[0x200 + 0x76] = 0xff; ram[0x200 + 0x79] = 0xff;
    ram[0x7dee] = ram[0x7df0] = ram[0x7df1] = 123;
    for (unsigned int at = 0x7dfe; at <= 0x7e06; ++at) ram[at] = 123;
    std::uint32_t d0 = 0x123456ab,d1 = 0x9876abcd,d3 = 0xbeef1234;
    std::vector<ms5::VideoPortWrite> ports;
    assert(ms5::initialize_main_frame(ram,0x200,bindings,d0,d1,d3,ports,error));
    assert(d0 == 0 && d1 == 0x98760001 && d3 == 0xbeef00f0);
    assert(ports.size() == 2 && ports[0].address == 0x300001 && ports[0].size == 1 && ports[0].value == 0xab &&
           ports[1].address == 0x300001 && ports[1].size == 1 && ports[1].value == 0);
    // Seventeen shared-source bindings are prepended: slot16 is the head.
    assert(word(ram,base + 7 * 16 + 6) == 16 * 16);
    for (unsigned int slot = 0; slot < 17; ++slot) {
        const std::size_t at = base + slot * 16;
        assert(word(ram,at + 8) == 0xffff && word(ram,at + 10) == 7 && ram[at + 15] == 0x82);
        assert(word(ram,at + 2) == (slot == 0 ? 7 * 16 + 4 : (slot - 1) * 16));
    }
    assert(word(ram,base + 6 * 16 + 12) == 1 && ram[base + 6 * 16 + 14] == 12);
    assert(ram[base + 5 * 16 + 14] == 19 && ram[base + 20 * 16 + 14] == 17);
    assert(word(ram,base + 20 * 16 + 8) == 0 && word(ram,base + 20 * 16 + 10) == 0xffff);
    assert(word(ram,base + 30 * 16 + 8) == 3 && word(ram,base + 30 * 16 + 10) == 0x1234 && ram[base + 30 * 16 + 14] == 23);
    assert(word(ram,0x0e) == 0 && word(ram,0x27e) == 0 && ram[0x284] == 1);
    assert(ram[0x276] == 0 && ram[0x279] == 0 && word(ram,0x200) == 0 && word(ram,0x202) == 0xe74);
    assert(ram[0x7def] == 255 && ram[0x7dee] == 0 && ram[0x7df0] == 0 && ram[0x7df1] == 0);
    for (unsigned int at = 0x7dfe; at <= 0x7e06; ++at) assert(ram[at] == 0);
    assert(ms5::initialize_main_frame(ram,0x200,bindings,d0,d1,d3,ports,error));
    assert(ram[base + 5 * 16 + 14] == 19 && ram[base + 20 * 16 + 14] == 17 && word(ram,base + 30 * 16 + 8) == 3);
    {
        std::vector<std::uint8_t> blank(65536,0);
        assert(ms5::initialize_palette_state(&blank[0],blank.size(),error));
        ms5::FixedDataResource unbound = table();
        put(unbound.data,16 * 6 + 2,0xffff); unbound.data[16 * 6 + 4] = 0x7f;
        blank[base + 16 * 16 + 14] = 29;
        assert(ms5::initialize_main_frame(blank,0x200,unbound,d0,d1,d3,ports,error));
        assert(word(blank,base + 16 * 16 + 8) == 0xffff && word(blank,base + 16 * 16 + 10) == 0xffff &&
               word(blank,base + 16 * 16 + 12) == 0xffff && blank[base + 16 * 16 + 15] == 2 &&
               blank[base + 16 * 16 + 14] == 29);
    }
    // Late bad bucket is reached only after earlier bindings/releases succeeded.
    put(ram,base + 7 * 16 + 6,0x1234); fails(ram,bindings,0x200);
    assert(ms5::initialize_palette_state(&ram[0],ram.size(),error));
    bindings.data[16 * 6 + 2] = 1; bindings.data[16 * 6 + 3] = 0x22;
    put(ram,base + 0x224 + 2,0x1234); fails(ram,bindings,0x200);
    bindings = table(); fails(ram,bindings,1); fails(ram,bindings,65536 - 0x84);
    bindings.data[103] = 0; fails(ram,bindings,0x200);
    bindings = table(); put(bindings.data,0,256); fails(ram,bindings,0x200);
    std::cout << "Main startup bucket-head binding, fixed release and rollback passed\n";
}
