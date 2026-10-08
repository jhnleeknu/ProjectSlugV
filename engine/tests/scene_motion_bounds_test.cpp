#include "ms5/scene_motion.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, std::uint32_t v, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at, unsigned int size = 4) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < size; ++i) v = (v << 8) | b[at+i]; return v;
}
ms5::FixedDataResource path(unsigned int type, unsigned int extent) {
    ms5::FixedDataResource p; p.source_cpu_address = p.source_rom_offset = 0x50000;
    const unsigned int words[] = {0,type,extent,0,7,10,0xffff};
    for (unsigned int i = 0; i < 7; ++i) { p.data.push_back(static_cast<std::uint8_t>(words[i] >> 8)); p.data.push_back(static_cast<std::uint8_t>(words[i])); } return p;
}
bool same(const ms5::SceneCommandState& a, const ms5::SceneCommandState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2 && a.a4 == b.a4;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::SceneCommandState s; std::string error;
    put(ram,0xd3b8,0xfffe,2); put(ram,0xd3ba,3,2); s.d2 = 0xffffffff; s.d3 = 0xffffffff; s.d7 = 0x12345678;
    assert(ms5::step_scene_motion_bounds(ram,0x198ee,NULL,s,error)); assert(s.d0 == 0xfffe0000 && s.d1 == 0x30000 && s.d2 == 0 && s.d3 == 0 && s.d7 == 0x12345678);
    assert(ms5::step_scene_motion_bounds(ram,0x19978,NULL,s,error)); assert(get(ram,0xd3c4) == 0xfffe0000 && get(ram,0xd3c8) == 0x30000);
    // All36 validated types share position calculation but span excludes +8 bias.
    for (unsigned int type = 0; type <= 0x8c; type += 4) {
        ram.assign(65536,0); put(ram,0xd3b4,0x50000); ms5::FixedDataResource p = path(type,0xfffe);
        ms5::SceneCommandState span, biased; span.d7 = biased.d7 = 0x30000; span.d4 = biased.d4 = 0x12340000;
        std::vector<std::uint8_t> second = ram; assert(ms5::evaluate_scene_motion(second,&p,biased,error));
        assert(ms5::step_scene_motion_bounds(ram,0x198ee,&p,span,error));
        assert(span.d0 == biased.d0-0x70000 && span.d1 == biased.d1-(type < 0x58 ? 0x70000 : 0U));
        assert(span.d2 == (type < 0x58 ? 0U : 0xfffe0000U) && span.d3 == (type < 0x58 ? 0xfffe0000U : 0U) && span.d4 == (0x12340000U | type));
    }
    // N-only endpoint swap differs from signed comparison when overflow occurs.
    ram.assign(65536,0); put(ram,0xd3b4,0x50000); put(ram,0xd3ba,0x8000,2); ms5::FixedDataResource p = path(0x14,0xffff); s = ms5::SceneCommandState();
    assert(ms5::step_scene_motion_bounds(ram,0x19978,&p,s,error)); assert(get(ram,0xd3c8) == 0x7fff0000 && s.d1 == 0x7fff0000 && s.d3 == 0x10000);
    // Signed WORD extent ordering, high fractional WORDs and untouched registers.
    ram.assign(65536,0); put(ram,0xd3b4,0x50000); put(ram,0xd3b8,5,2); put(ram,0xd3ba,10,2);
    put(ram,0xd3f2,0x7fff,2); put(ram,0xd3f6,0x7fff,2); put(ram,0xd3f4,0x8000,2); put(ram,0xd3f8,0x8000,2);
    p = path(0x14,0xfffd); s = ms5::SceneCommandState(); s.d7 = 0xabcd0002; s.d6 = 0x12345678; s.a4 = 0x76543210;
    assert(ms5::step_scene_motion_bounds(ram,0x19d98,&p,s,error));
    assert(get(ram,0xd3f2,2) == 7 && get(ram,0xd3f4,2) == 7 && get(ram,0xd3f6,2) == 7 && get(ram,0xd3f8,2) == 10 && s.d6 == 0x12345678 && s.a4 == 0x76543210);
    // Saturation depends on the last ADD only, including negative overflow.
    ram.assign(65536,0); put(ram,0xd3b8,0x100,2); put(ram,0xd3a2,0x7e00,2); s = ms5::SceneCommandState(); s.d6 = 0xaaaa0000;
    assert(ms5::step_scene_motion_bounds(ram,0x19d08,NULL,s,error)); assert(get(ram,0xd3f4,2) == 0x7fff && s.d0 == 0x7fff && s.d6 == 0xaaaa0000);
    ram.assign(65536,0); put(ram,0xd3b8,0x7fff,2); put(ram,0xd3a2,0x7fff,2); s = ms5::SceneCommandState();
    assert(ms5::step_scene_motion_bounds(ram,0x19d08,NULL,s,error)); assert(get(ram,0xd3f4,2) == 0x13e);
    ram.assign(65536,0); put(ram,0xd3ba,0x8000,2); put(ram,0xd3a6,0x8000,2); s = ms5::SceneCommandState();
    assert(ms5::step_scene_motion_bounds(ram,0x19d08,NULL,s,error)); assert(get(ram,0xd3f8,2) == 0x7fff);
    // Late backward selection failure after bounds reset preserves all state/RAM.
    ram.assign(65536,0); put(ram,0xd3b4,0x50000); put(ram,0xd3f2,0x11223344); p = path(0,2); put(p.data,0,10,2);
    s = ms5::SceneCommandState(); s.d7 = 0x12345678; const std::vector<std::uint8_t> before = ram; const ms5::SceneCommandState saved = s;
    assert(!ms5::step_scene_motion_bounds(ram,0x19d08,&p,s,error)); assert(ram == before && same(s,saved));
    assert(!ms5::step_scene_motion_bounds(ram,0,NULL,s,error)); assert(ram == before && same(s,saved));
    std::cout << "scene motion bounds tests passed\n";
}
