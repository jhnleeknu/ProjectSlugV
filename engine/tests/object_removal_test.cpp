#include "ms5/object_removal.h"
#include "ms5/palette_allocator.h"
#include <cstdlib>
#include <iostream>
namespace {
void require(bool condition, const char* message) {
    if (!condition) { std::cerr << message << '\n'; std::exit(1); }
}
void word(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void put(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t value) {
    word(ram,at,value >> 16); word(ram,at + 2,value);
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) | (static_cast<std::uint32_t>(ram[at + 1]) << 16) |
        (static_cast<std::uint32_t>(ram[at + 2]) << 8) | ram[at + 3];
}
void node(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int previous, unsigned int next, unsigned int depth) {
    put(ram,at,0x1234); put(ram,at + 4,0x100000U + previous); put(ram,at + 8,0x100000U + next);
    word(ram,at + 0x10,depth); ram[at + 0x6c] = 255;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0);
    node(ram,0x820,0xc00,0x900,0); put(ram,0x820,0x270e);
    node(ram,0x900,0x820,0xa00,0); node(ram,0xa00,0x900,0xb00,1);
    node(ram,0xb00,0xa00,0xc00,2); node(ram,0xc00,0xb00,0x820,1);
    put(ram,0x4c9c,0x101000); word(ram,0x4ca0,20); return ram;
}
ms5::RemovalState state(unsigned int at) {
    ms5::RemovalState result; result.d0 = 0xabcdef34; result.d1 = 0x76543210; result.d3 = 0x98765432;
    result.a6 = 0x100000U + at; return result;
}
void fails(std::vector<std::uint8_t>& ram, unsigned int entry, unsigned int target, ms5::RemovalState& value) {
    const std::vector<std::uint8_t> before = ram; const ms5::RemovalState old = value;
    std::vector<ms5::VideoPortWrite> ports(1); ports[0].value = 0x1234; std::string error;
    require(!ms5::remove_objects(ram,entry,target,value,ports,error),"expected removal error");
    require(ram == before && value.d0 == old.d0 && value.d1 == old.d1 && value.d3 == old.d3 &&
        value.a6 == old.a6 && ports.size() == 1 && ports[0].value == 0x1234 && !error.empty(),"removal rollback");
}
}
int main() {
    std::vector<std::uint8_t> ram = fixture(); ms5::RemovalState value = state(0xa00);
    std::vector<ms5::VideoPortWrite> ports; std::string error;
    require(ms5::remove_objects(ram,0x299c,0,value,ports,error),"deferred removal");
    require(get(ram,0xa00) == 0x270e && get(ram,0x908) == 0x100a00 && value.a6 == 0x100a00 &&
        value.d0 == 1 && value.d1 == 0x76543210 && value.d3 == 0x98765432 && ram[0x4ca1] == 20,"deferred node retained");
    require(ports.size() == 1 && ports[0].size == 1 && ports[0].address == 0x300001 && ports[0].value == 0x34,"watchdog input low byte");
    value.a6 = 0x100b00;
    require(ms5::remove_objects(ram,0x299c,0,value,ports,error),"cascade free");
    require(value.a6 == 0x100900 && value.d0 == 0 && value.d1 == 0xffffffffU && ports.size() == 1 &&
        get(ram,0x4c9c) == 0x100a00 && get(ram,0xa08) == 0x100b00 && get(ram,0xb08) == 0x101000 &&
        get(ram,0x908) == 0x100c00 && get(ram,0xc04) == 0x100900 && ram[0x4ca1] == 22,"cascade order and single cleanup");
    ram = fixture(); value = state(0x900);
    require(ms5::remove_objects(ram,0x2a0a,0,value,ports,error) && value.a6 == 0x100900 && ports.size() == 3 &&
        ram[0x4ca1] == 23 && get(ram,0x908) == 0x100820,"children consume returned A6");
    ram = fixture(); value = state(0x820);
    require(ms5::remove_objects(ram,0x2a84,0x100900,value,ports,error) && value.a6 == 0x100820 &&
        ports.size() == 4 && ram[0x4ca1] == 23 && get(ram,0x900) == 0x270e,"target group restores A6/static not freed");
    ram = fixture(); value = state(0x820); ram[0x4d91] = 255;
    require(ms5::remove_objects(ram,0xc4cc,0,value,ports,error) && value.a6 == 0x100820 &&
        get(ram,6) == 0x3dcc && get(ram,10) == 0x3dcc && ram[0x4d91] == 0xef && ports.size() == 4,"c4cc callback and live next traversal");
    ram = fixture(); value = state(0xa00); ram[0xa6c] = 0;
    put(ram,0xd4e6,0x12345678); put(ram,0xd4ea,0xdeadbeef); put(ram,0xd4fe,0x98765432);
    require(ms5::remove_objects(ram,0x299c,0,value,ports,error) && value.d0 == 0x12340001 &&
        value.d1 == 0xdeadbeef && value.d3 == 0x98765432 && ram[0xa6c] == 255 && ram[0xd50d] == 255 && ram[0xd511] == 2,"coordinate old Y and world outputs before depth test");
    ram = fixture(); value = state(0xa00); ram[0xa6c] = 8; fails(ram,0x299c,0,value);
    ram = fixture(); value = state(0xa00); put(ram,0xa08,0); fails(ram,0x299c,0,value);
    ram = fixture(); value = state(0x820); fails(ram,0x2a84,0x100a00,value);
    ram = fixture(); value = state(0xa00); ram[0xa6c] = 0; put(ram,0xd4f6,1); fails(ram,0x299c,0,value);
    ram = fixture(); value = state(0x820); put(ram,0x908,1); fails(ram,0xc4cc,0,value);
    fails(ram,0x1234,0,value); ram.resize(65535); fails(ram,0x299c,0,value);

    // Palette optional D1 reads references before decrement, preserving high word.
    ram.assign(65536,0); std::uint32_t d1 = 0xabcd1234, d3 = 0x98765432;
    require(ms5::release_palettes(ram,0x900,error,&d3,&d1) && d1 == 0xabcd1234 && d3 == 0x98765432,"count zero registers preserved");
    ram[0x91d] = 2; ram[0x919] = 0; ram[0x91a] = 1; word(ram,0x4daa,0xffff); word(ram,0x4d9a,2);
    require(ms5::release_palettes(ram,0x900,error,&d3,&d1) && d1 == 0xabcd0002 && ram[0x4d9b] == 1,"last reference read and high word");
    ram[0x91d] = 1; word(ram,0x4d9a,1); const std::vector<std::uint8_t> before = ram;
    d1 = 0x12345678; d3 = 0x87654321;
    require(!ms5::release_palettes(ram,0x900,error,&d3,&d1) && ram == before && d1 == 0x12345678 && d3 == 0x87654321,"palette failed release rolls back registers");
    std::cout << "Object removal defer/cascade/children/coordinates and rollback passed\n";
}
