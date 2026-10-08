#include "ms5/scene_frame_control.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, std::uint32_t v, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at, unsigned int size = 4) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < size; ++i) v = (v << 8) | b[at+i]; return v;
}
bool same(const ms5::SceneCommandState& a, const ms5::SceneCommandState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2 && a.a4 == b.a4;
}
void object(std::vector<std::uint8_t>& ram, std::size_t at, unsigned int x, unsigned int y) {
    put(ram,at,0x40000); ram[at+0x15] = 0x80; put(ram,at+0x42,x,2); put(ram,at+0x46,y,2);
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); std::vector<ms5::FixedDataResource> windows; ms5::SceneCommandState s; bool carry = false; std::string error;
    s.d7 = 0xabcd1234; assert(ms5::step_scene_frame_control(ram,0x1a2b4,windows,s,carry,error)); assert(carry && s.a1 == 0 && s.d7 == 0xabcd1234);
    // Dormant/disabled object early exits do not dereference invalid rectangle.
    s.a0 = 0x102000; s.a1 = 0xffffffff; put(ram,0x2000,0x270e);
    assert(ms5::step_scene_frame_control(ram,0x1a34c,windows,s,carry,error)); assert(carry && s.a1 == 0xffffffff);
    put(ram,0x2000,0x40000); assert(ms5::step_scene_frame_control(ram,0x1a34c,windows,s,carry,error)); assert(!carry);
    // Packed LONG addition propagates low WORD carry into the X upper bound.
    object(ram,0x2000,11,0xffff); put(ram,0x5000,0x000afffe); put(ram,0x5004,0x00010004);
    s.a1 = 0x105000; s.d0 = 0xabcd0000; s.d1 = 0x12340000;
    assert(ms5::step_scene_frame_control(ram,0x1a34c,windows,s,carry,error)); assert(carry && s.d4 == 0xfffe000a && s.d5 == 0x0002000c && s.d0 == 0xabcd000b && s.d1 == 0x1234ffff);
    // Exclusive edges and signed ordering; successful Y check swaps whole longs.
    put(ram,0x5000,0x000a000a); put(ram,0x5004,0x00020002); object(ram,0x2000,11,11);
    assert(ms5::step_scene_frame_control(ram,0x1a34c,windows,s,carry,error)); assert(carry && s.d4 == 0x000a000a && s.d5 == 0x000c000c);
    put(ram,0x2042,12,2); assert(ms5::step_scene_frame_control(ram,0x1a34c,windows,s,carry,error)); assert(!carry);
    // Selector0 false leaves its forced-speed write; true resets duration and speed.
    ram.assign(65536,0); put(ram,0xd422,0x105000); put(ram,0x5000,0,2); put(ram,0x5002,9,2); put(ram,0xd418,4,2); put(ram,0xd41e,5,2); s = ms5::SceneCommandState();
    assert(ms5::step_scene_frame_control(ram,0x1a2b4,windows,s,carry,error)); assert(!carry && get(ram,0xd43e,2) == 9 && s.a1 == 0x105004 && s.d0 == 4);
    put(ram,0xd418,5,2); s.d7 = 0x12340000; assert(ms5::step_scene_frame_control(ram,0x1a2b4,windows,s,carry,error)); assert(carry && get(ram,0xd422) == 0 && get(ram,0xd43e,2) == 0 && s.d7 == 0x12347fff && s.a1 == 0);
    // Selector8 falls back to its second rectangle after first-object rejection.
    ram.assign(65536,0); put(ram,0xd422,0x105000); put(ram,0x5000,8,2); put(ram,0x5002,0); put(ram,0x5006,0x00010001); put(ram,0x500a,0x000a000a); put(ram,0x500e,0x00020002); ram[0xd68e] = 1;
    object(ram,0xcb8,11,11); object(ram,0xda8,12,11); s = ms5::SceneCommandState();
    assert(ms5::step_scene_frame_control(ram,0x1a2b4,windows,s,carry,error)); assert(!carry && s.a0 == 0x100da8 && s.a1 == 0x10500a && s.d0 == 12);
    // Raw duration accepts non-typed record type and preserves D7.high.
    ram.assign(65536,0); put(ram,0xd3b4,0x105000); put(ram,0x5002,0xaaaa,2); put(ram,0x500a,0,2); put(ram,0x500c,0xffff,2); s.d7 = 0xbeef5678;
    assert(ms5::step_scene_frame_control(ram,0x1a29e,windows,s,carry,error)); assert(!carry && s.a1 == 0x10500a && s.d7 == 0xbeefffff && get(ram,0xd41e,2) == 0xffff);
    // d422 clear aliases the first raw duration type and must be observed live.
    ram.assign(65536,0); put(ram,0xd3b4,0x10d420); put(ram,0xd422,0xffffffff); put(ram,0xd42a,7,2); put(ram,0xd42c,0xffff,2);
    assert(ms5::step_scene_frame_control(ram,0x1a29e,windows,s,carry,error)); assert(s.a1 == 0x10d42a && (s.d7 & 0xffff) == 6);
    // Settings preserve register high words, unsigned limits and D0-only fallback.
    ram.assign(65536,0); put(ram,0xd41e,0xffff,2); put(ram,0xd420,1,2); put(ram,0xd440,2,2); put(ram,0xd442,0x8000,2);
    put(ram,0xd444,0x8000,2); put(ram,0xd448,4,2); put(ram,0xd426,9,2); put(ram,0xd42a,10,2); put(ram,0xd446,11,2); put(ram,0xd44a,0x8000,2); put(ram,0xd43e,0x8000,2); put(ram,0xd44c,0x7fff,2);
    s.d0 = 0xabcd0000; s.d1 = 0xbcde0000; s.d2 = 0xcdef0000;
    assert(ms5::step_scene_frame_control(ram,0x1a526,windows,s,carry,error)); assert(!carry && s.d0 == 0xabcd8000 && s.d1 == 0xbcde8000 && s.d2 == 0xcdef8000);
    assert(get(ram,0xd3ee,2) == 2 && get(ram,0xd3f0,2) == 1 && get(ram,0xd3d6,2) == 9 && get(ram,0xd3da,2) == 10 && get(ram,0xd3d8,2) == 11 && get(ram,0xd3dc,2) == 0x8000);
    // Shake clamps whole LONG only outside [-8,8] and carries prior amplitude.
    ram.assign(65536,0); put(ram,0xd408,0x100000); put(ram,0xd404,0x1234,2);
    assert(ms5::step_scene_frame_control(ram,0x1a3d6,windows,s,carry,error)); assert(!carry && s.d0 == 0xfffffff8 && s.d1 == 0x10000 && get(ram,0xd408) == 0xfff10000 && get(ram,0xd406,2) == 0x1234);
    // Late duration read failure rolls back prior clear and handler writes/carry.
    ram.assign(65536,0); put(ram,0xd422,0x105000); put(ram,0x5000,0,2); put(ram,0x5002,9,2); put(ram,0xd3b4,0x10fffc); s = ms5::SceneCommandState(); carry = false;
    const std::vector<std::uint8_t> before = ram; const ms5::SceneCommandState saved = s;
    assert(!ms5::step_scene_frame_control(ram,0x1a2b4,windows,s,carry,error)); assert(ram == before && same(s,saved) && !carry);
    carry = true; assert(!ms5::step_scene_frame_control(ram,0x1a2b4,windows,s,carry,error)); assert(ram == before && same(s,saved) && carry);
    assert(!ms5::step_scene_frame_control(ram,0,windows,s,carry,error)); assert(ram == before && same(s,saved) && carry);
    const std::size_t bad_sizes[] = {0,65535,65537};
    for (unsigned int i = 0; i < 3; ++i) {
        std::vector<std::uint8_t> bad(bad_sizes[i],0x55); const std::vector<std::uint8_t> original = bad;
        assert(!ms5::step_scene_frame_control(bad,0x1a29e,windows,s,carry,error)); assert(bad == original && same(s,saved) && carry);
    }
    std::cout << "scene frame control tests passed\n";
}
