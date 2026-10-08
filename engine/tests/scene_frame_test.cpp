#include "ms5/scene_frame.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, std::uint32_t v, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at, unsigned int size = 4) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < size; ++i) v = (v << 8) | b[at+i]; return v;
}
ms5::FixedDataResource resource(std::uint32_t base, const std::vector<unsigned int>& words) {
    ms5::FixedDataResource r; r.source_cpu_address = r.source_rom_offset = base;
    for (std::size_t i = 0; i < words.size(); ++i) { r.data.push_back(static_cast<std::uint8_t>(words[i] >> 8)); r.data.push_back(static_cast<std::uint8_t>(words[i])); } return r;
}
ms5::FixedDataResource tables() {
    ms5::FixedDataResource r; r.source_cpu_address = r.source_rom_offset = 0x1af12; r.data.assign(512,0);
    for (unsigned int i = 0; i < 256; ++i) put(r.data,2*i,0x320,2); return r;
}
bool same(const ms5::SceneMapTransferState& a, const ms5::SceneMapTransferState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.a[i] != b.a[i]) return false; return true;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); std::vector<ms5::FixedDataResource> windows; ms5::FixedDataResource t = tables();
    ms5::SceneMapTransferState s; s.a[3] = 0x12345678; std::vector<ms5::VideoPortWrite> ports; std::string error;
    assert(ms5::step_scene_frame(ram,t,windows,s,0x103000,ports,error));
    assert(ports.size() == 4 && ports[0].address == 0x2ffff2 && ports[0].value == 0x2000 && ports[1].address == 0x2ffff0 && ports[1].value == 0);
    assert(ports[2].address == 0x2ffff2 && ports[2].value == 0x1000 && ports[3].address == 0x2ffff0 && ports[3].value == 0 && s.a[3] == 0x12345678 && get(ram,0x10,2) == 0);
    // False condition bypasses an invalid script; phase never regresses.
    ram.assign(65536,0); put(ram,0xd422,0x105000); put(ram,0x5000,0,2); put(ram,0x5002,0,2); put(ram,0xd418,5,2); put(ram,0xd41e,6,2); put(ram,0xd412,0xffffffff); s = ms5::SceneMapTransferState();
    assert(ms5::step_scene_frame(ram,t,windows,s,0x103000,ports,error)); assert(get(ram,0xd412) == 0xffffffff && get(ram,0xd418,2) == 5 && get(ram,0xd422) == 0x105000);
    // One call establishes motion/script state, advances phase and consumes one placement.
    ram.assign(65536,0); put(ram,0xd412,0x40000); put(ram,0xd440,0x7fff,2); put(ram,0xd442,0x7fff,2); put(ram,0xd3fc,0x10000);
    put(ram,0x4ca0,1,2); put(ram,0x4c9c,0x102000); put(ram,0x3008,0x103000);
    windows.push_back(resource(0x40000,{0,0,0,5,0,0xc,6,0,0x28,1,0xffff}));
    windows.push_back(resource(0x50000,{0,0x14,0,0,0,10,0xffff}));
    windows.push_back(resource(0x60000,{1,2,1,0,0,0,4,0,0x1122,1,0,2,0,0,0,4,0,0xffff}));
    s = ms5::SceneMapTransferState(); s.a[3] = 0xaabbccdd;
    assert(ms5::step_scene_frame(ram,t,windows,s,0x103000,ports,error));
    assert(get(ram,0xd418,2) == 1 && get(ram,0xd40e) == 0x60012 && get(ram,0x2076,2) == 0x1122 && s.a[3] == 0xaabbccdd);
    // Debug ports appear between the bank envelope prefix/suffix.
    ram.assign(65536,0); ram[0xf000] = 8; windows.clear(); s = ms5::SceneMapTransferState();
    assert(ms5::step_scene_frame(ram,t,windows,s,0x103000,ports,error));
    assert(ports.size() == 1284 && ports[0].value == 0x2000 && ports[2].address == 0x3c0000 && ports[1281].address == 0x3c0000 && ports[1282].value == 0x1000);
    // Early selector error and late placement failure preserve all prior outputs.
    ram.assign(65536,0); put(ram,0xd422,0x105000); put(ram,0x5000,12,2); s = ms5::SceneMapTransferState(); s.d[3] = 0x87654321;
    std::vector<std::uint8_t> before = ram; ms5::SceneMapTransferState saved = s;
    ms5::VideoPortWrite old; old.size = 1; old.address = 0x300001; old.value = 9; ports.assign(1,old);
    assert(!ms5::step_scene_frame(ram,t,windows,s,0x103000,ports,error)); assert(ram == before && same(s,saved) && ports.size() == 1 && ports[0].value == 9);
    ram.assign(65536,0); ram[0xf000] = 8; put(ram,0xd40e,0xffffffff); s = ms5::SceneMapTransferState(); s.a[3] = 0xabcdef01; before = ram; saved = s;
    assert(!ms5::step_scene_frame(ram,t,windows,s,0x103000,ports,error)); assert(ram == before && same(s,saved) && ports.size() == 1 && ports[0].value == 9);
    t.data.pop_back(); assert(!ms5::step_scene_frame(ram,t,windows,s,0x103000,ports,error)); assert(ram == before && same(s,saved));
    std::cout << "scene frame tests passed\n";
}
