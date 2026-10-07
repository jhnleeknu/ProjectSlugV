#include "ms5/scene_general_initialization.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, unsigned int size, std::uint32_t v) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at, unsigned int size) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < size; ++i) v = (v << 8) | b[at+i]; return v;
}
ms5::FixedDataResource resource(std::uint32_t base, const std::vector<unsigned int>& words) {
    ms5::FixedDataResource r; r.source_cpu_address = r.source_rom_offset = base;
    for (std::size_t i = 0; i < words.size(); ++i) { r.data.push_back(static_cast<std::uint8_t>(words[i] >> 8)); r.data.push_back(static_cast<std::uint8_t>(words[i])); } return r;
}
ms5::FixedDataResource tables() {
    ms5::FixedDataResource r; r.source_cpu_address = r.source_rom_offset = 0x1af12; r.data.assign(512,0);
    for (unsigned int i = 0; i < 256; ++i) put(r.data,2*i,2,0x320); return r;
}
bool same(const ms5::SceneMapTransferState& a, const ms5::SceneMapTransferState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.a[i] != b.a[i]) return false;
    return true;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); std::vector<ms5::FixedDataResource> windows; ms5::FixedDataResource t = tables();
    ms5::SceneMapTransferState s; s.d[0] = 0xabcd0009; s.a[3] = 0x12345678;
    ram[0xd363] = 0x77; ram[0xd371] = 0x88; ram[0xd37f] = 0x99; ram[0xd38d] = 0xaa;
    ram[0xd3f2] = 0x12; ram[0xd40d] = 0xff;
    std::vector<ms5::VideoPortWrite> ports; std::string error;
    assert(ms5::initialize_scene(ram,t,windows,s,0x103000,ports,error));
    assert(get(ram,0xd41c,2) == 0 && get(ram,0xd416,2) == 0 && s.a[0] == 0 && s.a[3] == 0x12345678);
    assert(ports.size() == 4 && ports[0].address == 0x2ffff2 && ports[0].value == 0x2000 && ports[2].value == 0x1000);
    assert(ram[0xd363] == 0x77 && ram[0xd371] == 0x88 && ram[0xd37f] == 0x99 && ram[0xd38d] == 0xaa && ram[0xd3f2] == 0x12 && ram[0xd40d] == 0);
    // A simple non-null script runs despite nonzero input target; null motion lowers target.
    ram.assign(65536,0); s = ms5::SceneMapTransferState(); s.d[0] = 7; s.a[0] = 0x40000;
    windows.push_back(resource(0x40000,{0x30,1,2,3,4,0xffff}));
    assert(ms5::initialize_scene(ram,t,windows,s,0x103000,ports,error));
    assert(get(ram,0xd426,2) == 1 && get(ram,0xd42c,2) == 4 && get(ram,0xd416,2) == 0xffff && get(ram,0xd41c,2) == 0);
    // Script establishes motion, placement and a wait; all execute within one general call.
    ram.assign(65536,0); put(ram,0x4ca0,2,1); put(ram,0x4c9c,4,0x102000); put(ram,0x3008,4,0x103000);
    s = ms5::SceneMapTransferState(); s.d[0] = 1; s.a[0] = 0x40000; s.a[3] = 0x13572468;
    windows.clear(); windows.push_back(resource(0x40000,{0,0,0,5,0,0xc,6,0,0x28,1,0xffff}));
    windows.push_back(resource(0x50000,{0,0,0,0,0,2,0xffff}));
    windows.push_back(resource(0x60000,{1,2,1,0,0,0,4,0,0x1122,0xffff}));
    assert(ms5::initialize_scene(ram,t,windows,s,0x103000,ports,error));
    assert(get(ram,0xd418,2) == 1 && get(ram,0xd41c,2) == 1 && get(ram,0xd3bc,4) == 0x10000);
    assert(get(ram,0x2000,4) == 0x40000 && get(ram,0x2076,2) == 0x1122 && get(ram,0xd40e,4) == 0x60012 && s.a[3] == 0x13572468);
    // A late placement error preserves the whole transaction and previous output ports.
    ram.assign(65536,0); s = ms5::SceneMapTransferState(); s.d[0] = 1; s.a[0] = 0x40000;
    windows[2].data[3] = 3; const std::vector<std::uint8_t> before = ram; const ms5::SceneMapTransferState old = s;
    ms5::VideoPortWrite saved; saved.size = 1; saved.address = 0x300001; saved.value = 9; ports.assign(1,saved);
    assert(!ms5::initialize_scene(ram,t,windows,s,0x103000,ports,error));
    assert(ram == before && same(s,old) && ports.size() == 1 && ports[0].value == 9);
    // Duplicate script windows reject before observable initialization writes.
    windows.push_back(windows[0]); assert(!ms5::initialize_scene(ram,t,windows,s,0x103000,ports,error)); assert(ram == before && same(s,old));
    std::cout << "scene general initialization tests passed\n";
}
