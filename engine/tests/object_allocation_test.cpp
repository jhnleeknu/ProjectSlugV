#include "ms5/object_allocation.h"
#include <cstdlib>
#include <iostream>
namespace {
void require(bool condition, const char* message) {
    if (!condition) { std::cerr << message << '\n'; std::exit(1); }
}
void put_word(std::vector<std::uint8_t>& ram, unsigned int at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void put(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t value) {
    put_word(ram,at,static_cast<std::uint16_t>(value >> 16)); put_word(ram,at + 2,static_cast<std::uint16_t>(value));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) | (static_cast<std::uint32_t>(ram[at + 1]) << 16) |
        (static_cast<std::uint32_t>(ram[at + 2]) << 8) | ram[at + 3];
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0xa5);
    put(ram,0x4c9c,0x100200); put_word(ram,0x4ca0,5);
    put(ram,0x208,0x100800); put(ram,0x408,0x100600); put_word(ram,0x410,0xffff);
    ram[0x46a] = 0x67; return ram;
}
ms5::AllocationState state() {
    ms5::AllocationState result; result.d0 = 0xabcd0004; result.a0 = 0x12345678;
    result.a1 = 0xdeadbeef; result.a6 = 0x100400; return result;
}
bool same(const ms5::AllocationState& a, const ms5::AllocationState& b) {
    return a.d0 == b.d0 && a.a0 == b.a0 && a.a1 == b.a1 && a.a6 == b.a6 && a.carry == b.carry;
}
void fails(std::vector<std::uint8_t>& ram, ms5::AllocationState& value, bool request = false) {
    const std::vector<std::uint8_t> before = ram; const ms5::AllocationState old = value; std::string error;
    const bool okay = request ? ms5::request_game_object(ram,value,error) : ms5::allocate_object(ram,value,error);
    require(!okay && !error.empty() && ram == before && same(value,old),"allocation error rollback");
}
}
int main() {
    std::vector<std::uint8_t> ram = fixture(); ms5::AllocationState value = state(); std::string error;
    require(ms5::allocate_object(ram,value,error),"allocate success");
    require(value.d0 == 0xabcd0000 && value.a0 == 0x100200 && value.a1 == 0x100600 && value.a6 == 0x100400 && value.carry,"success registers and word wrap");
    require(get(ram,0x4c9c) == 0x100800 && ram[0x4ca1] == 4 && get(ram,0x20c) == 0x100400 &&
        get(ram,0x204) == 0x100400 && get(ram,0x208) == 0x100600 && get(ram,0x604) == 0x100200 &&
        get(ram,0x408) == 0x100200 && get(ram,0x200) == 0x12345678 && ram[0x26a] == 0x67,"ring linking and inherited byte");
    for (unsigned int threshold = 5; threshold <= 6; ++threshold) {
        ram = fixture(); value = state(); value.d0 = 0xabcd0000U | threshold; value.a6 = 1;
        const std::vector<std::uint8_t> before = ram;
        require(ms5::allocate_object(ram,value,error) && !value.carry && value.a0 == 0x100e98 &&
            value.d0 == (0xabcd0000U | threshold) && value.a1 == 0xdeadbeef && ram == before,"unsigned threshold failure without dereference");
    }
    ram = fixture(); value = state(); value.a0 = 0; value.a6 = 1;
    const std::vector<std::uint8_t> before = ram;
    require(ms5::allocate_object(ram,value,error) && !value.carry && value.d0 == 0xabcd0004 && ram == before,"zero callback normal failure");
    // A node overlapping the allocator globals observes their ordered writes.
    ram = fixture(); value = state(); put(ram,0x4c9c,0x104c90); put(ram,0x4c98,0x100800); put_word(ram,0x410,7);
    require(ms5::allocate_object(ram,value,error) && value.d0 == 0xabcd0008 && ram[0x4ca1] == 8 &&
        get(ram,0x4c9c) == 0x100400,"overlap retains pop/count/parent/index write order");
    // Parent can be the allocated node; the live successor still comes from its old next link.
    ram = fixture(); value = state(); value.a6 = 0x100200; put_word(ram,0x210,9); ram[0x26a] = 0x39;
    require(ms5::allocate_object(ram,value,error) && value.d0 == 0xabcd000a && value.a1 == 0x100800 &&
        get(ram,0x208) == 0x100200 && ram[0x26a] == 0x39,"node-parent alias and live reads");
    ram = fixture(); value = state(); put(ram,0x408,0); fails(ram,value);
    ram = fixture(); value = state(); value.a6 = 0x10ff96; fails(ram,value);
    ram = fixture(); value = state(); put(ram,0x4c9c,0x100201); fails(ram,value);
    ram = fixture(); value = state(); put(ram,0x4c9c,0); fails(ram,value);
    ram.resize(65535); fails(ram,value);

    ram = fixture(); value = state(); ram[0xfd82] = 1; ram[1] = 1;
    require(ms5::request_game_object(ram,value,error) && value.carry && value.a0 == 0x100200 &&
        get(ram,0x200) == 0x4fb64 && ram[0x462] == 0,"request wrapper success");
    ram = fixture(); value = state(); ram[0xfd82] = 1; ram[1] = 1; put_word(ram,0x4ca0,0);
    require(ms5::request_game_object(ram,value,error) && !value.carry && value.d0 == 0xabcd0000 &&
        value.a0 == 0x100e98 && value.a1 == 0xdeadbeef && ram[0x462] == 255,"request full normal failure");
    for (unsigned int condition = 0; condition < 2; ++condition) {
        ram = fixture(); value = state(); value.carry = true; ram[0xfd82] = condition == 0 ? 0 : 1; ram[1] = 0;
        const ms5::AllocationState incoming = value;
        require(ms5::request_game_object(ram,value,error) && !value.carry && value.d0 == incoming.d0 &&
            value.a0 == incoming.a0 && value.a1 == incoming.a1 && value.a6 == incoming.a6 && ram[0x462] == 255,"request inactive condition preserves registers");
    }
    ram = fixture(); value = state(); ram[0xfd82] = 1; ram[1] = 1; put(ram,0x408,0x100601); fails(ram,value,true);
    ram = fixture(); value = state(); value.a6 = 0; ram[0xfd82] = 0; fails(ram,value,true);
    std::cout << "Object allocation order, widths, wrapper and rollback passed\n";
}
