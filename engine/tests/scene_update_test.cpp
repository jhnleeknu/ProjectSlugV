#include "ms5/scene_update.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& bytes, std::size_t at, unsigned int size, std::uint32_t value) {
    for (unsigned int i = 0; i < size; ++i) bytes[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
ms5::FixedDataResource tables() {
    ms5::FixedDataResource source; source.source_cpu_address = source.source_rom_offset = 0x1af12;
    source.data.assign(512,0); for (unsigned int i = 0; i < 256; ++i) put(source.data,2*i,2,0x320); return source;
}
ms5::SceneMapTransferState initial() {
    ms5::SceneMapTransferState state;
    for (unsigned int i = 0; i < 8; ++i) state.d[i] = 0xabcd1200+i;
    for (unsigned int i = 0; i < 5; ++i) state.a[i] = 0x12345600+i;
    return state;
}
bool same(const ms5::SceneMapTransferState& a, const ms5::SceneMapTransferState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.a[i] != b.a[i]) return false;
    return true;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::FixedDataResource table = tables();
    ms5::SceneMapTransferState state = initial(); std::vector<ms5::VideoPortWrite> ports;
    std::vector<ms5::FixedDataResource> windows; std::string error;
    const ms5::SceneMapTransferState old = state;
    assert(ms5::update_scene_debug_registers(ram,table,state,ports,error));
    assert(ports.empty() && state.d[6] == 0 && state.d[7] == 0 && state.d[0] == old.d[0] && state.a[3] == old.a[3]);
    // Debug off with a previous active flag executes caf0 and its full scratch effects.
    state = initial(); ram[0xd44e] = 1;
    assert(ms5::update_scene_debug_registers(ram,table,state,ports,error));
    assert(ports.size() == 2072 && state.d[0] == 0x75807500 && state.d[1] == 0x7000 && state.d[2] == 0 && state.d[3] == 32);
    assert(state.d[6] == 0 && state.d[7] == 0x75007000 && state.a[4] == 0x3c0000 && state.a[0] == old.a[0]);
    // Stable active path rechecks the first node while A1 names the second, leaving D6's mask high bits.
    ram.assign(65536,0); ram[0xf000] = 0x18; ram[0xd44e] = 1; state = initial();
    assert(ms5::update_scene_debug_registers(ram,table,state,ports,error));
    assert(ports.empty() && state.d[0] == 0 && state.d[1] == 0 && state.d[2] == 0 && state.d[3] == 0);
    assert(state.d[6] == 0xfff80001 && state.d[7] == 0xffffffff && state.a[0] == 0x109156 && state.a[1] == 0x10b1d6);
    assert(state.a[2] == old.a[2] && state.a[3] == old.a[3] && state.a[4] == old.a[4]);
    // Both layers return320: fallback uses node2 and preserves cache byte bits in D7.
    ram.assign(65536,0); ram[0xf000] = 0x18; state = initial();
    assert(ms5::update_scene_debug_registers(ram,table,state,ports,error));
    assert(ports.size() == 1280 && ports.front().value == 0x74ff0320 && ports.back().value == 0x70000320);
    assert(state.d[2] == 0xabcd0027 && state.d[3] == 0xabcdffff && state.d[4] == 0x70000320 && state.d[6] == 0xb0 && state.d[7] == 0xffff0058);
    assert(state.a[0] == 0x10b1d6 && state.a[1] == 0x1af12 && state.a[2] == 0x1afd2 && state.a[3] == old.a[3] && state.d[5] == old.d[5]);
    // A first-layer result skips second-layer lookup; tile upper bits are ROL.W3 flag offsets.
    ram.assign(65536,0); ram[0xf000] = 0x18; state = initial();
    put(table.data,0xb0,2,0x1234); put(table.data,0xc0,2,0x400);
    assert(ms5::update_scene_debug_registers(ram,table,state,ports,error));
    assert(state.a[0] == 0x109156 && state.d[4] == 0x70001634 && state.d[7] == 0xffff0000 && state.d[6] == 0xb0);
    // No-script composite runs coordinates/debug then all four metadata entries, preserving A3.
    ram.assign(65536,0); table = tables(); state = initial();
    assert(ms5::update_scene(ram,table,windows,state,ports,error));
    assert(ports.empty() && state.a[0] == 0x10d2d6 && state.a[1] == 0x10d380 && state.a[2] == 0 && state.a[3] == old.a[3]);
    // Four actual raw RAM streams execute in order after the coordinate prefix.
    ram.assign(65536,0); state = initial();
    const std::size_t metadata[] = {0xd356,0xd364,0xd372,0xd380};
    for (unsigned int i = 0; i < 4; ++i) {
        const std::size_t at = 0x600+8*i; put(ram,metadata[i],4,0x100000+at);
        put(ram,at,2,0x1c); put(ram,at+2,2,1); put(ram,at+4,2,2); put(ram,at+6,2,0xffff);
    }
    assert(ms5::update_scene(ram,table,windows,state,ports,error));
    for (unsigned int i = 0; i < 4; ++i) assert(ram[metadata[i]+5] == 1 && ram[metadata[i]+7] == 2);
    assert(state.a[2] == 0x100620 && state.a[3] == old.a[3] && state.d[0] == 2 && state.d[7] == 0xffff);
    // Debug succeeds and emits1280 writes, then a late fourth path error rolls the entire composite back.
    ram.assign(65536,0); ram[0xf000] = 8; state = initial();
    for (unsigned int i = 0; i < 4; ++i) {
        const std::size_t at = 0x600+8*i; put(ram,metadata[i],4,0x100000+at);
        put(ram,at,2,i == 3 ? 2 : 0x1c); put(ram,at+2,2,1); put(ram,at+4,2,2); put(ram,at+6,2,0xffff);
    }
    const std::vector<std::uint8_t> before = ram; const ms5::SceneMapTransferState registers = state;
    ms5::VideoPortWrite saved; saved.size = 1; saved.address = 0x300001; saved.value = 7; ports.assign(1,saved);
    assert(!ms5::update_scene(ram,table,windows,state,ports,error));
    assert(ram == before && same(state,registers) && ports.size() == 1 && ports[0].value == 7);
    table.data.pop_back();
    assert(!ms5::update_scene_debug_registers(ram,table,state,ports,error));
    assert(ram == before && same(state,registers) && ports.size() == 1);
    std::cout << "scene update tests passed\n";
}
