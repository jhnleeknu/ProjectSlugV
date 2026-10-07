#include "ms5/scene_coordinates.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) | (static_cast<std::uint32_t>(ram[at + 1]) << 16) | (static_cast<std::uint32_t>(ram[at + 2]) << 8) | ram[at + 3];
}
ms5::SceneNodeState initial() {
    ms5::SceneNodeState s; s.d0 = 0x12345678; s.d1 = 0x23456789; s.d2 = 0x3456789a; s.d3 = 0x456789ab;
    s.d4 = 0x56789abc; s.d5 = 0x6789abcd; s.d6 = 0x789abcde; s.d7 = 0x89abcdef;
    s.a0 = 0x101000; s.a1 = 0xaabbccdd; s.a2 = 0xbcdef012; s.a4 = 0xcdef0123; return s;
}
bool same(const ms5::SceneNodeState& a, const ms5::SceneNodeState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2 && a.a4 == b.a4;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0); const std::size_t nodes[4] = {0x9156,0xb1d6,0xd256,0xd2d6};
    for (unsigned int i = 0; i < 4; ++i) { put(ram,nodes[i] + 0x28,0x100,2); put(ram,nodes[i] + 0x2a,0x100,2); }
    put(ram,0xd38e,0x10000); put(ram,0xd392,0x20000); put(ram,0xd3bc,0x30000); put(ram,0xd3c0,0x50000); put(ram,0xd404,4,2); ram[0xd494] = 5; return ram;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::SceneNodeState state = initial(); std::string error;
    // Full scratch from parent carries, stamp change and old history values.
    put(ram,0x1000,0xffff); put(ram,0x1004,0xffff); put(ram,0x1010,0x102000); put(ram,0x1014,0xaaaa5555); put(ram,0x1018,0xbbbb6666);
    put(ram,0x2014,0x20002); put(ram,0x2018,0x30002); ram[0x2025] = 0x80; ram[0x1024] = 7; ram[0xd494] = 5;
    assert(ms5::step_scene_node(ram,0x43e38,state,error));
    assert(state.d0 == 0x30001 && state.d1 == 0x40001 && state.d2 == 0xaaaa5555 && state.d3 == 0xbbbb6666);
    assert(state.d4 == 0x20007 && state.d5 == 0x30005 && state.d6 == 0x789a0001 && state.d7 == 0x83 && state.a1 == 0x102000);
    assert(get(ram,0x101c) == 0xaaaa5555 && get(ram,0x1020) == 0xbbbb6666 && ram[0x1024] == 5);
    // Scaling exposes unsigned product, fraction carry and factor scratch.
    state = initial(); state.d0 = 0x800100ff; put(ram,0x1028,0xffff,2); ram[0x102c] = 0xff;
    assert(ms5::step_scene_node(ram,0x1724c,state,error));
    assert(state.d5 == 0xffffffff && state.d7 == 0x89abffff && state.d6 == 0xff00 && state.d0 == 0x0080fe00);
    assert(state.d1 == 0x23456789 && state.d2 == 0x3456789a && state.a2 == 0xbcdef012 && state.a4 == 0xcdef0123);
    // Global stamp aliases a history write; D5 retains its prehistory value.
    ram.assign(65536,0); state = initial(); state.a0 = 0x10d478; ram[0xd494] = 0x5a;
    assert(ms5::step_scene_node(ram,0x43e38,state,error));
    assert(state.d5 == 0x6789ab5a && ram[0xd494] == 0 && state.d7 == 0);
    ram = fixture(); state = initial();
    assert(ms5::update_scene_coordinates(ram,state,error));
    assert(get(ram,0xd38e) == 0xfffd0000 && get(ram,0xd3a6) == 0x00ff0000);
    assert(get(ram,0xd2ee) == 0x00fd0000 && state.d0 == 0xfffc0004 && state.d1 == 0x00f90000);
    assert(state.a0 == 0x10d2d6 && state.a1 == 0 && state.a2 == 0xbcdef012 && state.a4 == 0xcdef0123);
    // LIVE parent chain observes the scroll-adjusted previous node worldY.
    ram = fixture(); put(ram,0x9166,0x10d38e); put(ram,0xb1e6,0x109156); put(ram,0xd266,0x10b1d6); put(ram,0xd2e6,0x10d256); state = initial();
    assert(ms5::update_scene_coordinates(ram,state,error));
    assert(state.a1 == 0x10d256 && get(ram,0xd2ea) == 0xffed0000 && get(ram,0xd2ee) == 0x04f30000);
    ram = fixture(); put(ram,0xd2e6,0x100001); state = initial(); const std::vector<std::uint8_t> before = ram; const ms5::SceneNodeState old = state;
    assert(!ms5::update_scene_coordinates(ram,state,error)); assert(ram == before && same(state,old));
    std::cout << "scene_coordinates_test: passed\n";
}
