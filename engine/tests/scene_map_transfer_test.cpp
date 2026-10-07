#include "ms5/scene_map_transfer.h"
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
std::vector<ms5::FixedDataResource> windows() {
    std::vector<ms5::FixedDataResource> result(2);
    result[0].source_cpu_address = 0x200004; result[0].source_rom_offset = 0x300004;
    result[0].data.assign(0x104,0);
    put(result[0].data,0,4,0x200008); put(result[0].data,4,4,0x200100);
    put(result[0].data,0x100,2,0x1234); put(result[0].data,0x102,2,0x5678);
    result[1].source_cpu_address = result[1].source_rom_offset = 0x200010;
    result[1].data.assign(0x100,0);
    put(result[1].data,0,4,0x200020); put(result[1].data,0x14,4,0x200100);
    put(result[1].data,0xf0,2,8); put(result[1].data,0xf2,2,10);
    put(result[1].data,0xf8,4,0x11223344); put(result[1].data,0xfc,4,0x55667788);
    return result;
}
bool same(const ms5::SceneMapTransferState& a, const ms5::SceneMapTransferState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.a[i] != b.a[i]) return false;
    return true;
}
}
int main() {
    std::vector<std::uint8_t> ram;
    std::vector<ms5::FixedDataResource> resources = windows();
    ms5::SceneMapTransferState state = fixture(ram);
    std::vector<ms5::VideoPortWrite> ports;
    std::string error; bool copied = false;
    assert(ms5::transfer_scene_map(ram,resources,state,copied,ports,error));
    assert(copied && ports.size() == 8 && ram[0x27a] == 0x80 && ram[0x10] == 0 && ram[0x11] == 0);
    assert(ports[0].address == 0x2ffff2 && ports[0].value == 0x2000);
    assert(ports[2].size == 4 && ports[2].address == 0x3c0000 && ports[2].value == 0x00401234);
    assert(ports[3].value == 0x00415678 && ports[4].value == 0x1000 && ports[6].value == 0x1000);
    assert(state.d[0] == 0 && state.d[1] == 0 && state.d[2] == 1 && state.d[3] == 1 && state.d[4] == 0 && state.d[5] == 0);
    assert(state.a[1] == 0x100100 && state.a[4] == 0x200108);
    // Rejection publishes clipping registers but changes no RAM or ports.
    state = fixture(ram); state.d[0] |= 1; const std::vector<std::uint8_t> before_reject = ram;
    assert(ms5::transfer_scene_map(ram,resources,state,copied,ports,error));
    assert(!copied && ports.empty() && ram == before_reject && state.d[0] == 0xabcd0001);
    // Negative sprite slot still resolves the primary lookup, but does not read cells.
    state = fixture(ram); put(ram,0x226,2,0xffff); resources[0].data.resize(8);
    assert(ms5::transfer_scene_map(ram,resources,state,copied,ports,error));
    assert(copied && ports.size() == 6 && state.d[0] == 0 && state.d[6] == 0xabcd0001);
    resources = windows();
    // Secondary columns use relative pointers, retain raw LONG cells, and consume twice the width.
    state = fixture(ram); put(ram,0x102,2,1);
    assert(ms5::transfer_scene_map(ram,resources,state,copied,ports,error));
    assert(copied && ram[0x280] == 0x11 && ram[0x283] == 0x44 && ram[0x300] == 0x55 && ram[0x303] == 0x88);
    assert(state.d[2] == 0 && (state.d[6] & 0xffff) == 0 && state.a[2] == 0x200104);
    // The sentinel clears the ring locations rather than dereferencing a cell source.
    state = fixture(ram); put(ram,0x102,2,1); put(ram,0x280,4,0xffffffff); put(ram,0x300,4,0xffffffff);
    put(resources[1].data,0x14,4,0xffffffff);
    assert(ms5::transfer_scene_map(ram,resources,state,copied,ports,error));
    assert(ram[0x280] == 0 && ram[0x300] == 0 && state.d[0] == 0);
    // Ring masking keeps sentinel writes within the last aligned LONG of each column.
    state = fixture(ram); state.d[5] = 0; put(ram,0x102,2,1);
    put(ram,0x2fc,4,0xffffffff); put(ram,0x37c,4,0xffffffff);
    assert(ms5::transfer_scene_map(ram,resources,state,copied,ports,error));
    assert(ram[0x2fc] == 0 && ram[0x37c] == 0 && ram[0x2fb] == 0);
    // The descriptor height is read LIVE again after the bank-shadow write.
    resources = windows(); state = fixture(ram); state.a[1] = 0x10000a;
    put(ram,0xa,2,0); put(ram,0xc,2,0); put(ram,0xe,2,1); put(ram,0x10,2,2);
    put(ram,0x226,2,0xffff);
    assert(ms5::transfer_scene_map(ram,resources,state,copied,ports,error));
    assert(copied && (state.d[6] & 0xffff) == 1 && ports.size() == 6);
    // MOVEM.W restoration sign-extends the clipped words instead of retaining input high halves.
    state = fixture(ram); state.d[0] = 0x12348000; put(ram,0x104,2,0xffff); put(ram,0x226,2,0xffff);
    assert(ms5::transfer_scene_map(ram,resources,state,copied,ports,error));
    assert(copied && state.d[0] == 0xffff8000 && state.d[2] == 1);
    // All late failures preserve preexisting caller outputs, including the first bank selection.
    for (unsigned int mutation = 0; mutation < 6; ++mutation) {
        resources = windows(); state = fixture(ram);
        if (mutation == 0) resources[0].data.resize(0x102); // second primary word missing
        if (mutation == 1) resources.push_back(resources[0]);
        if (mutation == 2) resources[0].source_cpu_address |= 1;
        if (mutation == 3) { put(ram,0x102,2,1); resources[1].data.resize(0xfa); }
        if (mutation == 4) state.a[0] = 0x10ff86; // final flag outside RAM after primary writes
        if (mutation == 5) state.a[1] |= 1;
        const std::vector<std::uint8_t> before = ram;
        const ms5::SceneMapTransferState registers = state;
        ms5::VideoPortWrite old; old.size = 1; old.address = 0x300001; old.value = 7;
        ports.assign(1,old); copied = true;
        assert(!ms5::transfer_scene_map(ram,resources,state,copied,ports,error));
        assert(ram == before && same(state,registers) && copied && ports.size() == 1 && ports[0].value == 7);
    }
    std::cout << "scene map transfer tests passed\n";
}
