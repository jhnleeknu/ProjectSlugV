#include "ms5/scene_motion.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, std::uint32_t v, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < 4; ++i) v = (v << 8) | b[at+i]; return v;
}
ms5::FixedDataResource path(const std::vector<unsigned int>& words) {
    ms5::FixedDataResource p; p.source_cpu_address = p.source_rom_offset = 0x50000;
    for (std::size_t i = 0; i < words.size(); ++i) { p.data.push_back(static_cast<std::uint8_t>(words[i] >> 8)); p.data.push_back(static_cast<std::uint8_t>(words[i])); } return p;
}
bool same(const ms5::SceneCommandState& a, const ms5::SceneCommandState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2 && a.a4 == b.a4;
}
void coordinates(std::vector<std::uint8_t>& ram, unsigned int current, unsigned int proposed, unsigned int y = 0) {
    put(ram,0xd3bc,current << 16); put(ram,0xd3c0,y << 16); put(ram,0xd3c4,proposed << 16); put(ram,0xd3c8,y << 16);
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::SceneCommandState s; bool carry = true; std::string error;
    s.d0 = 0x12345678; assert(ms5::step_scene_motion_pair(ram,0x19832,NULL,s,carry,error)); assert(!carry && s.a1 == 0 && s.d6 == 0 && s.d7 == 0 && s.d0 == 0x12345678);
    // Direct strip consumes A1, independent of the published RAM cursor.
    for (unsigned int type = 0; type <= 0x8c; type += 4) {
        ms5::FixedDataResource p = path({0,type,10,0,0,10,0xffff}); s = ms5::SceneCommandState(); s.a1 = 0x50000; s.d6 = 0xabcd1234; s.d7 = 0xbeef9876;
        const std::vector<std::uint8_t> before = ram; assert(ms5::step_scene_motion_pair(ram,0x192c4,&p,s,carry,error));
        assert(carry && ram == before && s.d6 == 0xabcd0000 && s.d7 == 0xbeef0000 && s.d4 == 0xffff0000 && s.d5 == 0xb0000);
    }
    // Original reverse Y strips deliberately add the transformed D0 twice.
    ms5::FixedDataResource p = path({0,0x18,30,0,0,10,0xffff}); s = ms5::SceneCommandState(); s.a1 = 0x50000;
    s.d0 = 8U << 16; s.d2 = 16U << 16; s.d1 = 10U << 16; s.d3 = 20U << 16;
    assert(ms5::step_scene_motion_pair(ram,0x192c4,&p,s,carry,error)); assert(s.d0 == 0x10000 && s.d2 == 0x20000 && s.d1 == 0xb0000 && s.d3 == 0x150000 && carry);
    p = path({0,0x68,30,0,0,10,0xffff}); s = ms5::SceneCommandState(); s.a1 = 0x50000; s.d0 = 10U << 16; s.d2 = 20U << 16; s.d1 = 8U << 16; s.d3 = 12U << 16;
    assert(ms5::step_scene_motion_pair(ram,0x192c4,&p,s,carry,error)); assert(s.d0 == 0xc0000 && s.d2 == 0x170000 && s.d1 == 0x20000 && s.d3 == 0x30000);
    // EXT.W then upper-byte predicates retain high words and native mask logic.
    p = path({0,0x14,10,0,0,10,0xffff}); s = ms5::SceneCommandState(); s.a1 = 0x50000; s.d1 = 0xfffd0000; s.d3 = 0xfffc0000; s.d6 = 0xabcd1234; s.d7 = 0xbeef9876;
    assert(ms5::step_scene_motion_pair(ram,0x192c4,&p,s,carry,error)); assert(!carry && s.d6 == 0xabcdff00 && s.d7 == 0xbeefff00);
    s.d3 = 12U << 16; assert(ms5::step_scene_motion_pair(ram,0x192c4,&p,s,carry,error)); assert(carry && s.d7 == 0xbeef0000);
    // Forward/backward transitions use live bases and retain projected D6/D7.
    p = path({0,0x14,0,0,0,10,0x14,0,0,0,20,0xffff}); ram.assign(65536,0); put(ram,0xd3b4,0x50000); coordinates(ram,5,15); s = ms5::SceneCommandState();
    assert(ms5::step_scene_motion_pair(ram,0x19832,&p,s,carry,error)); assert(!carry && s.a1 == 0x5000a && get(ram,0xd3b4) == 0x5000a && s.d6 == 0x50000 && s.d7 == 0xf0000 && s.d5 == 15);
    assert(ram[0xd3b8] == 0 && ram[0xd3b9] == 10);
    coordinates(ram,15,5); s = ms5::SceneCommandState(); assert(ms5::step_scene_motion_pair(ram,0x19832,&p,s,carry,error)); assert(!carry && s.a1 == 0x50000 && s.d6 == 0xf0000 && s.d7 == 0x50000 && ram[0xd3b9] == 0);
    // Rejected next strip retreats and clamps to end-1; rejected previous advances to start.
    ram.assign(65536,0); put(ram,0xd3b4,0x50000); coordinates(ram,5,15,5); s = ms5::SceneCommandState();
    assert(ms5::step_scene_motion_pair(ram,0x19832,&p,s,carry,error)); assert(!carry && s.a1 == 0x50000 && s.d7 == 0x9ffff && get(ram,0xd3b4) == 0x50000);
    put(ram,0xd3b4,0x5000a); put(ram,0xd3b8,10,2); coordinates(ram,15,5,5); s = ms5::SceneCommandState();
    assert(ms5::step_scene_motion_pair(ram,0x19832,&p,s,carry,error)); assert(!carry && s.a1 == 0x5000a && s.d7 == 0xa0000 && ram[0xd3b9] == 10);
    // Terminal/end and first/start clips without strip traversal.
    coordinates(ram,15,25); s = ms5::SceneCommandState(); assert(ms5::step_scene_motion_pair(ram,0x19832,&p,s,carry,error)); assert(s.d7 == 0x13ffff && !carry);
    ram.assign(65536,0); put(ram,0xd3b4,0x50000); put(ram,0xd3c4,0xffff0000); s = ms5::SceneCommandState();
    assert(ms5::step_scene_motion_pair(ram,0x19832,&p,s,carry,error)); assert(s.d7 == 0 && !carry);
    // A late retreat outside the exact path rolls back bases, states and carry.
    p = path({10,0x14,0,7,0,20,0xffff}); ram.assign(65536,0); put(ram,0xd3b4,0x50000); put(ram,0xd3c4,0xffff0000); s = ms5::SceneCommandState(); carry = true;
    const std::vector<std::uint8_t> before = ram; const ms5::SceneCommandState saved = s;
    assert(!ms5::step_scene_motion_pair(ram,0x19832,&p,s,carry,error)); assert(ram == before && same(s,saved) && carry);
    s.a1 = 0; assert(!ms5::step_scene_motion_pair(ram,0x192c4,&p,s,carry,error)); assert(carry && ram == before);
    std::cout << "scene motion pair tests passed\n";
}
