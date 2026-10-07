#include "ms5/scene_map_refresh.h"
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
    std::vector<ms5::VideoPortWrite> ports; std::string error;
    put(ram,0x22e,4,0x100100); put(ram,0x104,2,4);
    state.d[2] = 0xabcd0002;
    assert(ms5::update_scene_columns(ram,resources,state,ports,error));
    assert(ports.empty() && ram[0x23a] == 0 && ram[0x23b] == 0x21 && ram[0x23d] == 0x21);
    assert(state.d[0] == 0xabcd0000 && state.d[4] == 0xabcd0000 && state.d[6] == 0xabcdffff);
    put(ram,0x236,4,0xffffffff); ram[0x23a] = 255; ram[0x23b] = 0x55;
    state.d[2] = 0xabcd0001;
    assert(ms5::update_scene_columns(ram,resources,state,ports,error));
    assert(ram[0x23a] == 0 && ram[0x23b] == 0x55);
    // Cursor movement searches backwards and then forwards without reloading the initial pointer.
    put(ram,0x236,4,0x100604); ram[0x235] = 10;
    put(ram,0x600,2,0); ram[0x602] = 3; ram[0x603] = 0x21;
    put(ram,0x604,2,2); ram[0x606] = 7; ram[0x607] = 0x22; put(ram,0x608,2,0xffff);
    state.d[0] = 0xabcd0001; state.d[2] = 0xabcd0002;
    assert(ms5::update_scene_columns(ram,resources,state,ports,error));
    assert(ram[0x23a] == 0x40 && ram[0x23b] == 0x21 && ram[0x23c] == 0x20 && ram[0x23d] == 0x22);
    assert(state.a[2] == 0x100604 && state.a[4] == 0x100608 && state.d[0] == 0xabcd0001);
    // Descriptor width is LIVE: the first column control store can change the next column's bound.
    state = fixture(ram); state.a[1] = 0x100236; put(ram,0x22e,4,state.a[1]);
    put(ram,0x23a,2,1); state.d[2] = 2;
    assert(ms5::update_scene_columns(ram,resources,state,ports,error));
    assert(ram[0x23a] == 0 && ram[0x23b] == 0x21 && ram[0x23c] == 0 && ram[0x23d] == 0x21);
    // Zero DBRA count executes a complete WORD cycle even when every source column is skipped.
    state = fixture(ram); put(ram,0x22e,4,0x100100); put(ram,0x104,2,0); state.d[2] = 0;
    assert(ms5::update_scene_columns(ram,resources,state,ports,error));
    assert(state.d[0] == 0xabcd0000 && state.d[4] == 0xabcd0000 && state.d[6] == 0xabcdffff);
    // Wrapped X performs DIVU/SWAP, restores WORD registers, then attempts the left overlap.
    state = fixture(ram); put(ram,0x22e,4,0x100100); put(ram,0x104,2,2); ram[0x27a] = 8;
    state.d[0] = 0x12340003;
    resources[0].data.resize(0x10c); put(resources[0].data,0x104,2,0xabcd); put(resources[0].data,0x106,2,0xef01);
    assert(ms5::transfer_wrapped_scene_map(ram,resources,state,ports,error));
    assert(ports.size() == 8 && ports[2].value == 0x0040abcd && ports[3].value == 0x0041ef01);
    assert(state.d[0] == 0xffffffff && state.a[1] == 0x100100);
    // NULL descriptor makes both refresh entries no-ops, publishing A1=0 only.
    state = fixture(ram); const ms5::SceneMapTransferState before_noop = state;
    assert(ms5::refresh_scene_map(ram,resources,state,ports,error));
    assert(ports.empty() && state.a[1] == 0 && state.d[0] == before_noop.d[0]);
    assert(ms5::refresh_moved_scene_map(ram,resources,state,ports,error)); assert(ports.empty());
    // Stationary moved refresh preserves incoming data registers without touching resources.
    put(ram,0x22e,4,0x100100); ram[0x27a] = 6;
    assert(ms5::refresh_moved_scene_map(ram,resources,state,ports,error));
    assert(ports.empty() && state.d[2] == 0xabcd0000 && state.d[3] == 0xabcd0000);
    // Negative screen X is shifted arithmetically; the caller WORD snapshot sign-extends on return.
    resources = windows(); state = fixture(ram); put(ram,0x22e,4,0x100100);
    put(ram,0x214,2,0xfff0); put(ram,0x218,2,0x0270);
    assert(ms5::refresh_scene_map(ram,resources,state,ports,error));
    assert(ports.size() == 8 && state.d[0] == 0xfffffffb && state.d[4] == 0xfffffffb && state.d[5] == 0);
    // A moved negative-Y strip takes the NEG.W branch and keeps MOVE.W D4's incoming high half.
    state = fixture(ram); put(ram,0x22e,4,0x100100); ram[0x27a] = 4; put(ram,0x218,2,0xffff);
    assert(ms5::refresh_moved_scene_map(ram,resources,state,ports,error));
    assert(ports.empty() && state.d[4] == 0xfffffffa && state.d[5] == 40 && state.d[3] == 1);
    // Errors after column writes or the first bank selection roll back all aggregate outputs.
    for (unsigned int mutation = 0; mutation < 4; ++mutation) {
        resources = windows(); state = fixture(ram); put(ram,0x22e,4,0x100100);
        if (mutation == 0) resources[0].data.resize(4);
        if (mutation == 1) { ram[0x27a] = 8; put(ram,0x104,2,0); }
        if (mutation == 2) { put(ram,0x236,4,0x10fffc); put(ram,0xfffc,2,0); }
        if (mutation == 3) state.a[0] = 0x10ffda;
        const std::vector<std::uint8_t> before = ram; const ms5::SceneMapTransferState registers = state;
        ms5::VideoPortWrite old; old.size = 1; old.address = 0x300001; old.value = 7; ports.assign(1,old);
        assert(!ms5::transfer_wrapped_scene_map(ram,resources,state,ports,error));
        assert(ram == before && same(state,registers) && ports.size() == 1 && ports[0].value == 7);
    }
    std::cout << "scene map refresh tests passed\n";
}
