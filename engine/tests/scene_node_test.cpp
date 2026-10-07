#include "ms5/scene_node.h"
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
ms5::SceneNodeState state() {
    ms5::SceneNodeState result; result.d0 = 0x12345678; result.d1 = 0x87654321; result.d3 = 0xabcdef01;
    result.a0 = 0x100200; result.a1 = 0x100500; return result;
}
void fails(std::vector<std::uint8_t>& ram, unsigned int entry, ms5::SceneNodeState& value) {
    const std::vector<std::uint8_t> before = ram; const ms5::SceneNodeState old = value; std::string error;
    require(!ms5::step_scene_node(ram,entry,value,error) && !error.empty() && ram == before &&
        value.d0 == old.d0 && value.d1 == old.d1 && value.d2 == old.d2 && value.d3 == old.d3 && value.d4 == old.d4 &&
        value.d5 == old.d5 && value.d6 == old.d6 && value.d7 == old.d7 && value.a0 == old.a0 && value.a1 == old.a1 &&
        value.a2 == old.a2 && value.a4 == old.a4,"scene transaction rollback");
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0xa5); ms5::SceneNodeState value = state(); std::string error;
    require(ms5::step_scene_node(ram,0x43dda,value,error) && value.d0 == 0 && value.d1 == 0x87654321 &&
        value.d3 == 0xabcdef01 && value.a0 == 0x100200 && value.a1 == 0x100500,"basic clear registers");
    for (unsigned int at = 0; at < 65536; ++at) require(ram[at] == (at >= 0x200 && at < 0x226 ? 0 : 0xa5),"26-byte clear extent");
    ram.assign(65536,0xa5); value = state();
    require(ms5::step_scene_node(ram,0x16fac,value,error),"extended initialization");
    require(get(ram,0x22e) == 0 && get(ram,0x236) == 0xffffffffU && ram[0x228] == 1 && ram[0x229] == 0 &&
        ram[0x22a] == 1 && ram[0x22b] == 0 && ram[0x27a] == 6 && ram[0x226] == 0xa5 && ram[0x227] == 0xa5 &&
        ram[0x23a] == 0xa5 && value.d0 == 0 && value.d1 == 0x87654321 && value.d3 == 0xabcdef01,"extended exact defaults and preserved gaps");
    ram.assign(65536,0xa5); value = state(); value.a0 = 0x10df80;
    require(ms5::step_scene_node(ram,0x17292,value,error) && value.a1 == 0x110000 && value.d0 == 0 && value.d1 == 0x87654321 && value.d3 == 0xabcdef01,"large clear end pointer");
    for (unsigned int at = 0; at < 65536; ++at) require(ram[at] == (at >= 0xe000 ? 0 : 0xa5),"8192 clear preserves prefix");
    const std::uint32_t velocities[] = {0xffff0001U,0x0000ffffU,0x80008000U,0xffff00ffU};
    const unsigned int factors[] = {0x100,0xffff,0x8000,2};
    const unsigned int fractions[] = {255,255,0,2};
    const std::uint32_t expected[] = {0xffff0001U,0xfffffe01U,0x00400000U,0xfffffe02U};
    for (unsigned int axis = 0; axis < 2; ++axis) {
        for (unsigned int index = 0; index < 4; ++index) {
            ram.assign(65536,0); value = state();
            if (axis == 0) value.d0 = velocities[index]; else value.d1 = velocities[index];
            word(ram,0x200 + (axis == 0 ? 0x28 : 0x2a),factors[index]); ram[0x200 + (axis == 0 ? 0x2c : 0x2d)] = fractions[index];
            require(ms5::step_scene_node(ram,axis == 0 ? 0x1724c : 0x1726c,value,error),"scale edge");
            require((axis == 0 ? value.d0 : value.d1) == expected[index] && get(ram,0x200 + (axis == 0 ? 8 : 12)) == expected[index] &&
                (axis == 0 ? value.d1 == 0x87654321 : value.d0 == 0x12345678) && value.d3 == 0xabcdef01 && value.a1 == 0x100500,"scale signed high/unsigned low arithmetic");
        }
    }
    for (unsigned int alias = 0; alias < 2; ++alias) {
        ram.assign(65536,0); value = state(); put(ram,0x200,0xffff); put(ram,0x204,0xffffffffU);
        put(ram,0x208,1); put(ram,0x20c,2); put(ram,0x210,0x100500); put(ram,0x214,0x11223344); put(ram,0x218,0xdeadbeef);
        put(ram,0x514,0x10000); put(ram,0x518,0x20000); ram[0x525] = 4; ram[0x224] = 1; ram[0xd494] = 3;
        require(ms5::step_scene_node(ram,alias == 0 ? 0x43ea8 : 0x1728c,value,error) && value.d0 == 0x20000 && value.d1 == 0x20001 &&
            value.d3 == 0xdeadbeef && value.a1 == 0x100500 && get(ram,0x21c) == 0x11223344 && get(ram,0x220) == 0xdeadbeef && ram[0x224] == 3,"advance capture and history timing");
    }
    ram.assign(65536,0); value = state(); value.a1 = 0; put(ram,0x218,0x69abcdef);
    require(ms5::step_scene_node(ram,0x16fee,value,error) && value.d0 == 0x12345678 && value.d1 == 0x87654321 && value.d3 == 0x69abcdef && value.a1 == 0 &&
        get(ram,0x210) == 0 && ram[0x22c] == 0 && ram[0x22d] == 0,"position prefix and old worldY");
    //43e08 consumes low WORD coordinates, unlike43e22's full LONG input.
    ram.assign(65536,0); value = state(); value.a1 = 0;
    value.d4 = 0xabcd1234; value.d5 = 0x23456789; value.d6 = 0x3456789a; value.d7 = 0x456789ab;
    value.a2 = 0x56789abc; value.a4 = 0x6789abcd; ram[0xd494] = 0x5a;
    put(ram,0x214,0x11112222); put(ram,0x218,0x33334444);
    require(ms5::step_scene_node(ram,0x43e08,value,error),"low-WORD position entry");
    require(value.d0 == 0x56780000 && value.d1 == 0x43210000 && get(ram,0x200) == 0x56780000 && get(ram,0x204) == 0x43210000 &&
        value.d2 == 0x11112222 && value.d3 == 0x33334444 && value.d4 == 0xabcd1200 && value.d5 == 0x2345675a &&
        value.d6 == 0x3456789a && value.d7 == 0 && value.a0 == 0x100200 && value.a1 == 0 && value.a2 == 0x56789abc && value.a4 == 0x6789abcd,
        "low-WORD conversion and full position scratch");
    require(get(ram,0x210) == 0 && get(ram,0x21c) == 0x56780000 && get(ram,0x220) == 0x43210000 && ram[0x224] == 0x5a,"low-WORD prefix/history writes");
    ram.assign(65536,0); value = state(); value.a1 = 0;
    require(ms5::step_scene_node(ram,0x43e22,value,error) && value.d0 == 0x12345678 && value.d1 == 0x87654321,"LONG position entry remains distinct");
    ram.assign(65536,0xa5); value = state(); value.a1 = 0x100001;
    value.d2 = 0x11223344; value.d4 = 0x22334455; value.d5 = 0x33445566; value.d6 = 0x44556677; value.d7 = 0x55667788;
    value.a2 = 0x66778899; value.a4 = 0x778899aa; fails(ram,0x43e08,value);
    ram.assign(65536,0xa5); value = state(); value.a1 = 1; fails(ram,0x16fee,value);
    ram.assign(65536,0); value = state(); put(ram,0x210,0x10ffff); fails(ram,0x43ea8,value);
    value = state(); value.a0 = 0x100201; fails(ram,0x43dda,value);
    value = state(); value.a0 = 0x10df82; fails(ram,0x17292,value);
    value = state(); fails(ram,0x1234,value); ram.resize(65535); fails(ram,0x43dda,value);
    std::cout << "Scene node clears, fixed-width scales, advance capture and rollback passed\n";
}
