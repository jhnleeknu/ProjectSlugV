#include "ms5/scene_motion.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& data, std::size_t at, std::uint32_t value, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) data[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& data, std::size_t at) {
    return (static_cast<std::uint32_t>(data[at]) << 24) | (static_cast<std::uint32_t>(data[at + 1]) << 16) | (static_cast<std::uint32_t>(data[at + 2]) << 8) | data[at + 3];
}
ms5::FixedDataResource path(const std::vector<unsigned int>& words) {
    ms5::FixedDataResource result; result.source_cpu_address = result.source_rom_offset = 0x50000;
    for (std::size_t i = 0; i < words.size(); ++i) { result.data.push_back(static_cast<std::uint8_t>(words[i] >> 8)); result.data.push_back(static_cast<std::uint8_t>(words[i])); }
    return result;
}
ms5::SceneCommandState initial() {
    ms5::SceneCommandState s; s.d0 = 0x12345678; s.d1 = 0x23456789; s.d2 = 0x3456789a; s.d3 = 0x456789ab;
    s.d4 = 0x56789abc; s.d5 = 0x6789abcd; s.d6 = 0x789abcde; s.d7 = 0x89abcdef;
    s.a0 = 0x9abcdef0; s.a1 = 0xaabbccdd; s.a2 = 0xbcdef012; s.a4 = 0xcdef0123; return s;
}
bool same(const ms5::SceneCommandState& a, const ms5::SceneCommandState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2 && a.a4 == b.a4;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::SceneCommandState state = initial(); std::string error;
    put(ram,0xd3b8,10,2); put(ram,0xd3ba,20,2); const std::vector<std::uint8_t> null_ram = ram;
    assert(ms5::evaluate_scene_motion(ram,NULL,state,error));
    assert(ram == null_ram && state.a1 == 0 && state.d0 == 0xa0000 && state.d1 == 0x140000 && state.d2 == 0x3456789a && state.d7 == 0x89abcdef);
    ms5::FixedDataResource motion = path({0,0x18,0,7,2,10,0xffff});
    put(ram,0xd3b4,0x50000); state = initial(); state.d7 = 0x3ffff;
    assert(ms5::evaluate_scene_motion(ram,&motion,state,error));
    assert(state.d0 == 0xfffff && state.d1 == 0x158000 && state.d2 == 0x20000 && state.d4 == 0x56780018 && state.d7 == 0x3ffff);
    assert(state.a1 == 0x50000 && state.d3 == 0x456789ab && state.d5 == 0x6789abcd && state.d6 == 0x789abcde && state.a0 == 0x9abcdef0 && state.a2 == 0xbcdef012 && state.a4 == 0xcdef0123);
    state.d7 = 0x140000;
    assert(ms5::evaluate_scene_motion(ram,&motion,state,error));
    assert(state.d7 == 0x9ffff && state.d0 == 0x15ffff && state.d1 == 0x14c000);
    state.d7 = 0xffff0000;
    assert(ms5::evaluate_scene_motion(ram,&motion,state,error));
    assert(state.d7 == 0 && state.d0 == 0xc0000 && state.d1 == 0x160000); // N-only first-record clip.
    motion = path({0,0x88,0,0,2,10,0xffff}); state = initial(); state.d7 = 0x3ffff;
    assert(ms5::evaluate_scene_motion(ram,&motion,state,error));
    assert(state.d0 == 0xa0000 && state.d1 == 0x100001); // Reverse Y-axis with arithmetic right shift; D2 added only to X.
    motion = path({0,0,0,0,0,10,0x14,0,3,4,20,0xffff});
    put(ram,0xd3b8,0,2); put(ram,0xd3ba,0,2); state = initial(); state.d7 = 0xc8000;
    assert(ms5::evaluate_scene_motion(ram,&motion,state,error));
    assert(state.a1 == 0x5000a && get(ram,0xd3b4) == 0x5000a && state.d0 == 0x108000 && state.d1 == 0x1b0000);
    state.d7 = 0x50000;
    assert(ms5::evaluate_scene_motion(ram,&motion,state,error));
    assert(state.a1 == 0x50000 && get(ram,0xd3b4) == 0x50000 && state.d0 == 0x50000 && state.d1 == 0xa0000);
    assert(ram[0xd3b8] == 0 && ram[0xd3b9] == 0 && ram[0xd3ba] == 0 && ram[0xd3bb] == 0);
    motion = path({10,0,0,7,0,20,0xffff}); state = initial(); state.d7 = 0x50000;
    const std::vector<std::uint8_t> before = ram; const ms5::SceneCommandState old = state;
    assert(!ms5::evaluate_scene_motion(ram,&motion,state,error)); // Backward crossing modifies candidate before span failure.
    assert(ram == before && same(state,old));
    motion.data[3] = 1;
    assert(!ms5::evaluate_scene_motion(ram,&motion,state,error)); assert(ram == before && same(state,old));
    motion = path({0,0,0,0,0,20,0xffff}); motion.data.pop_back();
    assert(!ms5::evaluate_scene_motion(ram,&motion,state,error)); assert(ram == before && same(state,old));
    put(ram,0xd3b4,0x50002); const std::vector<std::uint8_t> invalid_cursor = ram;
    motion = path({0,0,0,0,0,20,0xffff});
    assert(!ms5::evaluate_scene_motion(ram,&motion,state,error)); assert(ram == invalid_cursor && same(state,old));
    std::cout << "scene_motion_test: passed\n";
}
