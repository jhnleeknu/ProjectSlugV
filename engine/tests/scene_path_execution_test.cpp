#include "ms5/scene_path_execution.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& bytes, std::size_t at, unsigned int size, std::uint32_t value) {
    for (unsigned int i = 0; i < size; ++i) bytes[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
ms5::SceneMapTransferState fixture(std::vector<std::uint8_t>& ram) {
    ram.assign(65536,0); put(ram,0x104,2,1); put(ram,0x106,2,1);
    ms5::SceneMapTransferState state;
    for (unsigned int i = 0; i < 8; ++i) state.d[i] = 0xabcd0000;
    state.d[2] |= 1; state.d[3] |= 1; state.d[5] |= 31;
    state.a[0] = 0x100200; state.a[1] = 0x100100;
    return state;
}
bool same(const ms5::SceneMapTransferState& a, const ms5::SceneMapTransferState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.a[i] != b.a[i]) return false;
    return true;
}
}
int main() {
    std::vector<std::uint8_t> ram; std::vector<ms5::FixedDataResource> resources;
    ms5::SceneMapTransferState state = fixture(ram);
    std::vector<ms5::VideoPortWrite> ports; std::string error;
    state.a[1] = 0x123456; state.a[2] = 0xffffffff; state.d[0] = 0xabcd0800; state.d[1] = 0x1234ffff;
    assert(ms5::configure_scene_map_descriptor(ram,resources,state,ports,error));
    assert(state.d[0] == 0xabcdf800 && state.d[1] == 0x1234ffff && ram[0x232] == 0xf8 && ram[0x235] == 0xff);
    assert(ram[0x22f] == 0x12 && ram[0x230] == 0x34 && ram[0x231] == 0x56 && ram[0x236] == 0xff && ports.empty());
    // NULL cursor validates only the metadata LONG, not any node descriptor or trailing metadata span.
    state = fixture(ram); state.a[1] = 0x10fffc;
    const ms5::SceneMapTransferState null_input = state;
    assert(ms5::execute_scene_path(ram,resources,state,ports,error));
    assert(state.a[2] == 0 && state.d[0] == null_input.d[0] && state.d[7] == null_input.d[7] && ports.empty());
    // Terminal advances the stream pointer but does not publish a new persistent metadata cursor.
    state = fixture(ram); state.a[1] = 0x100400; put(ram,0x400,4,0x100500); put(ram,0x500,2,0x8000);
    assert(ms5::execute_scene_path(ram,resources,state,ports,error));
    assert(state.a[2] == 0x100502 && state.d[7] == 0xabcd8000 && ram[0x403] == 0);
    // OR.W flags changes both bytes, unlike opcode00's BYTE initialization.
    state = fixture(ram); state.a[1] = 0x100400; put(ram,0x400,4,0x100500); ram[0x40d] = 0x80;
    put(ram,0x500,2,0); put(ram,0x502,2,5); put(ram,0x504,2,6);
    put(ram,0x506,2,0x18); put(ram,0x508,2,0x0123); put(ram,0x50a,2,2); put(ram,0x50c,2,3);
    put(ram,0x50e,2,0x1c); put(ram,0x510,2,0xffff); put(ram,0x512,2,4); put(ram,0x514,2,0xffff);
    assert(ms5::execute_scene_path(ram,resources,state,ports,error));
    assert(ram[0x405] == 4 && ram[0x407] == 10 && ram[0x409] == 2 && ram[0x40b] == 3);
    assert(ram[0x40c] == 0x11 && ram[0x40d] == 0xa3 && state.d[0] == 0xabcd0004 && state.a[2] == 0x100516);
    // Descriptor replacement consumes old/new dimensions in order, removes BYTE flags and publishes the next opcode.
    state = fixture(ram); state.a[1] = 0x100400; put(ram,0x400,4,0x100500); put(ram,0x404,2,5); put(ram,0x406,2,6);
    put(ram,0x408,2,2); put(ram,0x40a,2,3); ram[0x40c] = 0x6f;
    put(ram,0x22e,4,0x100700); put(ram,0x704,2,10); put(ram,0x706,2,20);
    put(ram,0x500,2,4); put(ram,0x506,2,1); put(ram,0x508,2,1); put(ram,0x50a,4,0xffffffff); put(ram,0x50e,2,0xffff);
    assert(ms5::execute_scene_path(ram,resources,state,ports,error));
    assert(ram[0x405] == 16 && ram[0x406] == 0xff && ram[0x407] == 0xf6 && ram[0x40c] == 0);
    assert(ram[0x27a] == 0x18 && ram[0x233] == 16 && ram[0x234] == 0xff && ram[0x235] == 0xf6);
    assert(state.a[1] == 0x100400 && state.a[2] == 0x100510 && ram[0x402] == 5 && ram[0x403] == 14 && ports.empty());
    // All four conditional branches execute their distinct tests and share flags/delta/cursor stores.
    for (unsigned int opcode = 8; opcode <= 0x14; opcode += 4) {
        state = fixture(ram); state.a[1] = 0x100400; put(ram,0x400,4,0x100500);
        put(ram,0x22e,4,0x100700); put(ram,0x704,2,1); put(ram,0x706,2,1);
        if (opcode == 8) put(ram,0x21c,2,0xffff);
        if (opcode == 0x0c) put(ram,0x21c,2,1);
        if (opcode == 0x10) put(ram,0x220,2,1);
        if (opcode == 0x14) put(ram,0x218,2,0x100);
        put(ram,0x500,2,opcode); put(ram,0x502,2,0); put(ram,0x504,2,0x80);
        put(ram,0x506,2,1); put(ram,0x508,2,2); put(ram,0x50a,4,0x100600); put(ram,0x600,2,0xffff);
        assert(ms5::execute_scene_path(ram,resources,state,ports,error));
        assert(state.a[2] == 0x100602 && ram[0x402] == 6 && ram[0x403] == 0 && ram[0x40d] == 0x80);
        assert(ram[0x409] == 1 && ram[0x40b] == 2 && state.d[0] == 0xabcd0080);
    }
    // A failed condition skips ten operand bytes without publishing metadata cursor or OR flags.
    state = fixture(ram); state.a[1] = 0x100400; put(ram,0x400,4,0x100500); put(ram,0x21c,2,1);
    put(ram,0x500,2,8); put(ram,0x50e,2,0xffff);
    assert(ms5::execute_scene_path(ram,resources,state,ports,error));
    assert(state.a[2] == 0x100510 && ram[0x402] == 5 && ram[0x403] == 0 && ram[0x40c] == 0);
    // A backwards branch is finite and reuses the same raw RAM stream reader.
    state = fixture(ram); state.a[1] = 0x100400; put(ram,0x400,4,0x100500); put(ram,0x21c,2,0xffff);
    put(ram,0x500,2,8); put(ram,0x50a,4,0x100480); put(ram,0x480,2,0x1c);
    put(ram,0x482,2,1); put(ram,0x484,2,2); put(ram,0x486,2,0xffff);
    assert(ms5::execute_scene_path(ram,resources,state,ports,error));
    assert(state.a[2] == 0x100488 && ram[0x405] == 1 && ram[0x407] == 2 && ram[0x403] == 0x80);
    // Initial moved refresh emits before the first opcode, while preserving the metadata/stream address pair.
    state = fixture(ram); state.a[1] = 0x100400; put(ram,0x400,4,0x100500); put(ram,0x500,2,0xffff);
    put(ram,0x22e,4,0x100100); ram[0x27a] = 2; put(ram,0x214,2,0xffa0); put(ram,0x21c,2,0xff90); put(ram,0x218,2,0x270);
    ms5::FixedDataResource primary; primary.source_cpu_address = 0x200004; primary.source_rom_offset = 0x300004;
    primary.data.assign(0x104,0); put(primary.data,0,4,0x200008); put(primary.data,4,4,0x200100);
    put(primary.data,0x100,2,0x1234); put(primary.data,0x102,2,0x5678); resources.push_back(primary);
    assert(ms5::execute_scene_path(ram,resources,state,ports,error));
    assert(ports.size() == 8 && state.a[1] == 0x100400 && state.a[2] == 0x100502 && state.d[7] % 65536 == 0xffff);
    resources.clear();
    // Late invalid commands/reads undo earlier metadata writes and caller ports/registers.
    for (unsigned int mutation = 0; mutation < 3; ++mutation) {
        state = fixture(ram); state.a[1] = 0x100400; put(ram,0x400,4,0x100500);
        put(ram,0x500,2,0); put(ram,0x502,2,5); put(ram,0x504,2,6); put(ram,0x506,2,2);
        if (mutation == 1) { state.a[1] = 0x10fffc; put(ram,0xfffc,4,0x100500); }
        if (mutation == 2) { put(ram,0x506,2,0x18); put(ram,0x50c,2,1); }
        const std::vector<std::uint8_t> before = ram; const ms5::SceneMapTransferState registers = state;
        ms5::VideoPortWrite old; old.size = 1; old.address = 0x300001; old.value = 7; ports.assign(1,old);
        assert(!ms5::execute_scene_path(ram,resources,state,ports,error));
        assert(ram == before && same(state,registers) && ports.size() == 1 && ports[0].value == 7);
    }
    std::cout << "scene path execution tests passed\n";
}
