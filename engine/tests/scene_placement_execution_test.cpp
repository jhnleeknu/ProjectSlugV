#include "ms5/scene_placement_execution.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, unsigned int size, std::uint32_t v) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at, unsigned int size) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < size; ++i) v = (v << 8) | b[at+i]; return v;
}
std::vector<std::uint8_t> initial() {
    std::vector<std::uint8_t> b(65536,0); put(b,0x4ca0,2,1); put(b,0x4c9c,4,0x102000);
    put(b,0x3008,4,0x103000); put(b,0xd418,2,0); b[0xd494] = 3; return b;
}
void record(std::vector<std::uint8_t>& b, std::size_t at, std::uint16_t length) {
    put(b,at,2,0); put(b,at+2,2,length); put(b,at+4,2,0xfffe); put(b,at+6,2,5);
    put(b,at+8,4,0); put(b,at+12,4,0x40000);
    for (unsigned int i = 0; i < length; ++i) b[at+16+i] = static_cast<std::uint8_t>(i+1);
}
bool same(const ms5::SceneCommandState& a, const ms5::SceneCommandState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2 && a.a4 == b.a4;
}
}
int main() {
    std::vector<ms5::FixedDataResource> windows; std::string error;
    std::vector<std::uint8_t> b = initial(); record(b,0x5000,4);
    ms5::SceneCommandState s; s.a0 = 0x105000; s.d0 = 0x12340000; s.d1 = 0xabcd0000;
    assert(ms5::execute_scene_placement(b,0x1a470,windows,s,0x103000,error));
    assert(s.a0 == 0x105014 && s.a1 == 0x10207a && s.d0 == 0xfffe0000 && s.d1 == 0x50000);
    assert(get(b,0x2000,4) == 0x40000 && get(b,0x202e,4) == 0xfffe0000 && get(b,0x2032,4) == 0x50000);
    assert(get(b,0x2076,4) == 0x01020304);
    // Gate/terminal preserve high WORD, terminal remains unconsumed.
    b = initial(); record(b,0x5000,0); put(b,0x5010,2,0xffff); put(b,0xd40e,4,0x105000);
    s = ms5::SceneCommandState(); assert(ms5::execute_scene_placement(b,0x1a414,windows,s,0x103000,error));
    assert(s.a0 == 0x105010 && (s.d7 & 0xffff) == 0xffff && get(b,0xd40e,4) == 0x105010);
    b = initial(); put(b,0x5000,2,1); put(b,0xd40e,4,0x105000); s = ms5::SceneCommandState(); s.d7 = 0x12345678;
    assert(ms5::execute_scene_placement(b,0x1a414,windows,s,0x103000,error)); assert(s.d7 == 0x12340001 && s.a0 == 0x105000);
    // Out-of-bounds skip keeps length in D0.low and performs no allocation.
    b = initial(); record(b,0x5000,4); put(b,0xd418,2,1); s = ms5::SceneCommandState(); s.a0 = 0x105000;
    assert(ms5::execute_scene_placement(b,0x1a470,windows,s,0x103000,error)); assert(s.a0 == 0x105014 && s.d0 == 4 && get(b,0x4ca0,2) == 1);
    // Carry rejection still executes position and payload at the fallback node.
    b = initial(); record(b,0x5000,4); put(b,0x4ca0,2,0); s = ms5::SceneCommandState(); s.a0 = 0x105000;
    assert(ms5::execute_scene_placement(b,0x1a470,windows,s,0x103000,error)); assert(get(b,0xec6,4) == 0xfffe0000 && get(b,0xf0e,4) == 0x01020304);
    // Destination two bytes after source: live WORD copying propagates first WORD.
    b = initial(); record(b,0x2064,6); put(b,0x2074,2,0x1122); put(b,0x2076,2,0x3344); put(b,0x2078,2,0x5566);
    s = ms5::SceneCommandState(); s.a0 = 0x102064;
    assert(ms5::execute_scene_placement(b,0x1a470,windows,s,0x103000,error)); assert(get(b,0x2076,2) == 0x1122 && get(b,0x2078,2) == 0x1122 && get(b,0x207a,2) == 0x1122);
    // Errors after allocation or a prior record preserve every RAM byte and register.
    b = initial(); record(b,0x5000,3); const std::vector<std::uint8_t> before = b; s = ms5::SceneCommandState(); s.a0 = 0x105000;
    const ms5::SceneCommandState saved = s; assert(!ms5::execute_scene_placement(b,0x1a470,windows,s,0x103000,error)); assert(b == before && same(s,saved));
    b = initial(); record(b,0x5000,0); put(b,0xd40e,4,0x105000); put(b,0x5010,2,0); put(b,0x5012,2,1);
    const std::vector<std::uint8_t> stream_before = b; s = ms5::SceneCommandState(); const ms5::SceneCommandState stream_saved = s;
    assert(!ms5::execute_scene_placement(b,0x1a414,windows,s,0x103000,error)); assert(b == stream_before && same(s,stream_saved));
    // Borrowed fixed window reads; ambiguous and partial windows are errors.
    b = initial(); ms5::FixedDataResource w; w.source_cpu_address = 0x50000; w.source_rom_offset = 0x50000; w.data.resize(20); record(w.data,0,4); windows.push_back(w);
    s = ms5::SceneCommandState(); s.a0 = 0x50000; assert(ms5::execute_scene_placement(b,0x1a470,windows,s,0x103000,error));
    windows.push_back(w); b = initial(); s.a0 = 0x50000; assert(!ms5::execute_scene_placement(b,0x1a470,windows,s,0x103000,error));
    windows.resize(1); windows[0].data.resize(15); assert(!ms5::execute_scene_placement(b,0x1a470,windows,s,0x103000,error));
    std::cout << "scene placement execution tests passed\n";
}
