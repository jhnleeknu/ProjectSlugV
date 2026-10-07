#include "ms5/scene_script_run.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size = 4) {
    std::uint32_t value = 0;
    for (unsigned int i = 0; i < size; ++i) value = (value << 8) | ram[at + i];
    return value;
}
ms5::SceneScript script(const std::vector<unsigned int>& words) {
    ms5::FixedDataResource source; source.source_cpu_address = source.source_rom_offset = 0x50000;
    for (std::size_t i = 0; i < words.size(); ++i) { source.data.push_back(static_cast<std::uint8_t>(words[i] >> 8)); source.data.push_back(static_cast<std::uint8_t>(words[i])); }
    ms5::SceneScript result; std::string error; assert(ms5::decode_scene_script(source,result,error)); return result;
}
ms5::SceneCommandState initial() {
    ms5::SceneCommandState state; state.d0 = 0x12345678; state.d1 = 0x23456789; state.d2 = 0x3456789a; state.d3 = 0x456789ab;
    state.d4 = 0x56789abc; state.d5 = 0x6789abcd; state.d6 = 0x789abcde; state.d7 = 0x89abcdef;
    state.a0 = 0x9abcdef0; state.a1 = 0xaabbccdd; state.a2 = 0xbcdef012; state.a4 = 0xcdef0123; return state;
}
bool same(const ms5::SceneCommandState& a, const ms5::SceneCommandState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2 && a.a4 == b.a4;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::SceneCommandState state = initial(); ms5::SceneScript empty; ms5::FixedDataResource pointers;
    ms5::SceneScriptRunResult result; std::vector<ms5::VideoPortWrite> ports; std::string error;
    assert(ms5::run_scene_script(ram,empty,pointers,state,result,ports,error));
    assert(result.reason == ms5::NoScript && result.commands_executed == 0 && state.a1 == 0 && state.d0 == 0x12345678 && ports.empty());
    put(ram,0xd412,0xdeadbeef); put(ram,0xd418,0x7fff,2); put(ram,0xd416,0x8000,2); state = initial();
    assert(ms5::run_scene_script(ram,empty,pointers,state,result,ports,error));
    assert(result.reason == ms5::Waiting && state.a1 == 0xdeadbeef && state.d0 == 0x12347fff && result.commands_executed == 0);
    const ms5::SceneScript gated = script({0x28,5,0x4c,0x1234,0x5678,0xffff});
    put(ram,0xd412,0x50000); put(ram,0xd418,4,2); put(ram,0xd416,4,2); state = initial();
    assert(ms5::run_scene_script(ram,gated,pointers,state,result,ports,error));
    assert(result.reason == ms5::Waiting && result.commands_executed == 1 && state.d0 == 0x12340004 && state.a1 == 0x50004 && get(ram,0xd412) == 0x50004);
    put(ram,0xd418,5,2);
    assert(ms5::run_scene_script(ram,gated,pointers,state,result,ports,error));
    assert(result.reason == ms5::Terminator && result.commands_executed == 1 && state.a1 == 0x5000a && state.d0 == 0x12340005);
    assert(get(ram,0xd434) == 0x12345678 && get(ram,0xd416,2) == 0xffff);
    assert(ms5::run_scene_script(ram,empty,pointers,state,result,ports,error));
    assert(result.reason == ms5::Waiting && result.commands_executed == 0); // Recalling terminal is gated before dereference.
    put(ram,0xd418,0xffff,2);
    assert(ms5::run_scene_script(ram,gated,pointers,state,result,ports,error));
    assert(result.reason == ms5::Terminator && result.commands_executed == 0 && state.d0 == 0x1234ffff);
    const ms5::SceneScript inline_script = script({0x2c,1,0,4,0xdead,0xbeef,0x40,0,0xffff});
    put(ram,0xd412,0x50000); put(ram,0xd418,2,2); put(ram,0xd416,0,2); state = initial();
    assert(ms5::run_scene_script(ram,inline_script,pointers,state,result,ports,error));
    assert(result.reason == ms5::Terminator && result.commands_executed == 2 && state.a1 == 0x50010 && state.d0 == 0x12340002);
    assert(get(ram,0xd422) == 0x50008 && ports.size() == 1 && ports[0].address == 0x3c0006);
    // A resource failure after a hardware-writing command rolls back all outputs.
    const ms5::SceneScript late = script({0x40,1,0x10,6,0,0xffff});
    put(ram,0xd412,0x50000); put(ram,0xd416,0,2); state = initial();
    result.reason = ms5::Terminator; result.commands_executed = 77; ports.assign(1,ms5::VideoPortWrite{123,456,2});
    const std::vector<std::uint8_t> before = ram; const ms5::SceneCommandState old = state;
    assert(!ms5::run_scene_script(ram,late,pointers,state,result,ports,error));
    assert(ram == before && same(state,old) && result.reason == ms5::Terminator && result.commands_executed == 77 && ports[0].value == 456);
    put(ram,0xd412,0x50002); const std::vector<std::uint8_t> inside = ram;
    assert(!ms5::run_scene_script(ram,gated,pointers,state,result,ports,error));
    assert(ram == inside && same(state,old) && result.commands_executed == 77);
    std::cout << "scene_script_run_test: passed\n";
}
