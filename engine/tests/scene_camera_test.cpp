#include "ms5/scene_camera.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, std::uint32_t v, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at, unsigned int size = 4) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < size; ++i) v = (v << 8) | b[at+i]; return v;
}
ms5::FixedDataResource path() {
    ms5::FixedDataResource p; p.source_cpu_address = p.source_rom_offset = 0x50000;
    const unsigned int words[] = {0,0x14,0,0,0,1000,0xffff};
    for (unsigned int i = 0; i < 7; ++i) { p.data.push_back(static_cast<std::uint8_t>(words[i] >> 8)); p.data.push_back(static_cast<std::uint8_t>(words[i])); } return p;
}
bool same(const ms5::SceneCommandState& a, const ms5::SceneCommandState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2 && a.a4 == b.a4;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::SceneCommandState s; std::string error;
    put(ram,0xd3ce,0x100,2); put(ram,0xd3d2,0x100,2); put(ram,0xd3e6,0x60000); put(ram,0xd3de,0x20000);
    s.d5 = 0x12345678; assert(ms5::step_scene_camera(ram,0x19a40,NULL,s,error)); assert(s.d7 == 0x40000 && get(ram,0xd3de) == 0x40000 && s.d5 == 0x12340000);
    put(ram,0xd3d0,0x100,2); put(ram,0xd3d4,0x100,2); put(ram,0xd3ea,0x60000); put(ram,0xd3e2,0x20000);
    assert(ms5::step_scene_camera(ram,0x19ac8,NULL,s,error)); assert(s.d7 == 0x60000 && get(ram,0xd3e2) == 0x60000);
    // ADD.L overflow followed by BGE uses N xor V, retaining the positive request.
    ram.assign(65536,0); put(ram,0xd3ce,0x100,2); put(ram,0xd3d2,0x100,2); put(ram,0xd3e6,0x7fffffff); s = ms5::SceneCommandState();
    assert(ms5::step_scene_camera(ram,0x19a40,NULL,s,error)); assert(s.d0 == 0x801a7fff && s.d7 == 0xd4000);
    // N-only margin tests preserve incoming D6.high when its WORD remains negative.
    ram.assign(65536,0); put(ram,0xd3d6,0x80,2); put(ram,0xd3e6,0x60000); s = ms5::SceneCommandState(); s.d6 = 0xabcd0000; s.d5 = 0x12340000; s.d1 = 0xbeef0000;
    assert(ms5::step_scene_camera(ram,0x19a40,NULL,s,error)); assert(s.d6 == 0xabcdff80 && s.d5 == 0x12340000 && s.d1 == 0xbeeffeec && s.d7 == 0xfffd0000);
    // WORD input sum wraps before ASR, and signed request clamps differ from N tests.
    ram.assign(65536,0); put(ram,0xd3ce,0x7fff,2); put(ram,0xd3d2,0x7fff,2); put(ram,0xd3e6,0x60000); s = ms5::SceneCommandState();
    assert(ms5::step_scene_camera(ram,0x19a40,NULL,s,error)); assert(s.d6 == 0xffff && s.d7 == 0);
    // Null progression reuses all public helpers, restores bounds and commits live base coordinates.
    ram.assign(65536,0); put(ram,0xd3b8,4,2); put(ram,0xd3ba,5,2); put(ram,0xd3fc,0x10000); put(ram,0xd400,0x20000); s = ms5::SceneCommandState(); s.a4 = 0xabcdef01;
    assert(ms5::step_scene_camera(ram,0x19b96,NULL,s,error)); assert(get(ram,0xd3bc) == 0x40000 && get(ram,0xd3c0) == 0x50000 && get(ram,0xd3de) == 0x10000 && get(ram,0xd3e2) == 0x20000 && s.a4 == 0xabcdef01);
    assert(get(ram,0xd3ce,2) == 0x7fff && get(ram,0xd3d4,2) == 0x8000);
    // Negative X adds the proposed WORD delta; negative Y omits that ADD.
    ram.assign(65536,0); ram[0xd3cc] = 1; put(ram,0xd3b8,0xffff,2); put(ram,0xd3d2,0x114,2); put(ram,0xd3e6,0x60000); s = ms5::SceneCommandState();
    assert(ms5::step_scene_camera(ram,0x19b96,NULL,s,error)); assert(get(ram,0xd3bc) == 0xffff0000);
    ram.assign(65536,0); ram[0xd3cc] = 2; put(ram,0xd3ba,0xffff,2); put(ram,0xd3d4,0xb8,2); put(ram,0xd3ea,0x60000); s = ms5::SceneCommandState();
    assert(ms5::step_scene_camera(ram,0x19b96,NULL,s,error)); assert(get(ram,0xd3c0) == 0 && get(ram,0xd3c8) == 0xffff0000 && get(ram,0xd3e2) == 0);
    // Rejection keeps the proposal while clearing both previous requests.
    ram.assign(65536,0); ram[0xd3cc] = 1; put(ram,0xd3b8,1,2); put(ram,0xd3ce,0x2b,2); put(ram,0xd3e6,0x60000); put(ram,0xd400,0x12340000); s = ms5::SceneCommandState();
    assert(ms5::step_scene_camera(ram,0x19b96,NULL,s,error)); assert(get(ram,0xd3bc) == 0 && get(ram,0xd3c4) == 0x10000 && get(ram,0xd3de) == 0 && get(ram,0xd3e2) == 0);
    // Forced speed is an unsigned WORD shifted by8, not sign-extended.
    ram.assign(65536,0); put(ram,0xd3b4,0x50000); put(ram,0xd3fa,0x8000,2); put(ram,0xd3ee,1000,2); ms5::FixedDataResource p = path(); s = ms5::SceneCommandState();
    assert(ms5::step_scene_camera(ram,0x19b96,&p,s,error)); assert(s.d7 == 0x800000 && get(ram,0xd3c4) == 0x800000 && get(ram,0xd3bc) == 0x800000);
    // A full-call failure occurs after request/base writes and preserves all input state.
    ram.assign(65536,0); put(ram,0xd3b4,0x50002); put(ram,0xd3fc,0x12345678); put(ram,0xd400,0x87654321); s = ms5::SceneCommandState(); s.d5 = 0xabcddcba;
    const std::vector<std::uint8_t> before = ram; const ms5::SceneCommandState saved = s;
    assert(!ms5::step_scene_camera(ram,0x19b96,&p,s,error)); assert(ram == before && same(s,saved));
    assert(!ms5::step_scene_camera(ram,0,NULL,s,error)); assert(ram == before && same(s,saved));
    std::cout << "scene camera tests passed\n";
}
