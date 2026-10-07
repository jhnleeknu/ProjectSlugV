#include "ms5/scene_motion.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& bytes, std::size_t at, unsigned int size, std::uint32_t value) {
    for (unsigned int i = 0; i < size; ++i) bytes[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    return (static_cast<std::uint32_t>(bytes[at])<<24)|(static_cast<std::uint32_t>(bytes[at+1])<<16)|(static_cast<std::uint32_t>(bytes[at+2])<<8)|bytes[at+3];
}
ms5::SceneCommandState initial() {
    ms5::SceneCommandState s; s.d0 = 0x12345678; s.d1 = 0x23456789; s.d2 = 0x3456789a; s.d3 = 0x456789ab;
    s.d4 = 0x56789abc; s.d5 = 0x6789abcd; s.d6 = 0x789abcde; s.d7 = 0x89abcdef;
    s.a0 = 0x101000; s.a1 = 0xaabbccdd; s.a2 = 0xbcdef012; s.a4 = 0xcdef0123; return s;
}
bool same(const ms5::SceneCommandState& a, const ms5::SceneCommandState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2 && a.a4 == b.a4;
}
ms5::FixedDataResource path(unsigned int records) {
    ms5::FixedDataResource resource; resource.source_cpu_address = resource.source_rom_offset = 0x60000;
    resource.data.assign(records*10+4,0);
    for (unsigned int i = 0; i < records; ++i) { put(resource.data,i*10,2,i*10); put(resource.data,i*10+2,2,4); }
    put(resource.data,records*10,2,records*10); put(resource.data,records*10+2,2,0xffff); return resource;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::SceneCommandState state = initial(); std::string error;
    const ms5::SceneCommandState old = state;
    assert(ms5::resolve_scene_motion_time(ram,NULL,state,error));
    assert(state.a1 == 0 && state.d7 == 0 && state.d0 == old.d0 && state.d1 == old.d1 && state.a0 == old.a0);
    // All four projection groups preserve full axes, including fractions and reverse SUB.L borrow.
    const unsigned int types[] = {0x04,0x2c,0x58,0x74};
    for (unsigned int i = 0; i < 4; ++i) {
        ram.assign(65536,0); ms5::FixedDataResource resource = path(1); put(resource.data,2,2,types[i]);
        put(ram,0xd3b4,4,0x60000); state = initial();
        const bool y = i >= 2, reverse = (i&1U) != 0;
        const std::uint32_t coordinate = reverse ? 0x00018001 : 0x00028001;
        if (y) { state.d1 = coordinate; put(ram,0xd3ba,2,reverse ? 5 : 1); }
        else { state.d0 = coordinate; put(ram,0xd3b8,2,reverse ? 5 : 1); }
        const std::uint32_t input0 = state.d0, input1 = state.d1;
        assert(ms5::resolve_scene_motion_time(ram,&resource,state,error));
        assert(state.d0 == input0 && state.d1 == input1 && state.d7 == (reverse ? 0x00037fffU : 0x00018001U));
        assert(state.d4 == (old.d4&0xffff0000U)+types[i] && state.d2 == old.d2 && state.d3 == old.d3 && state.a1 == 0x60000);
    }
    // A forward move must publish then project again on the new reverse-X type; its backward publication ends the outer loop.
    ram.assign(65536,0); ms5::FixedDataResource resource = path(2); put(resource.data,12,2,0x2c);
    put(ram,0xd3b4,4,0x60000); state = initial(); state.d0 = 0x000c8000;
    assert(ms5::resolve_scene_motion_time(ram,&resource,state,error));
    assert(state.a1 == 0x60000 && get(ram,0xd3b4) == 0x60000 && state.d7 == 0x00078000);
    assert(state.d0 == 0x000c8000 && state.d1 == old.d1 && ram[0xd3b8] == 0 && ram[0xd3b9] == 0 && ram[0xd3bb] == 0);
    // Direct Y-to-X backward movement does not recompute using the preserved X axis after its cursor publication.
    ram.assign(65536,0); resource = path(2); put(resource.data,12,2,0x58); put(resource.data,16,2,2);
    put(ram,0xd3b4,4,0x6000a); put(ram,0xd3b8,2,12); put(ram,0xd3ba,2,10);
    state = initial(); state.d0 = 0x00028000; state.d1 = 0x00058000;
    assert(ms5::resolve_scene_motion_time(ram,&resource,state,error));
    assert(state.a1 == 0x60000 && state.d7 == 0x00058000 && state.d0 == 0x00028000 && state.d1 == 0x00058000);
    assert(get(ram,0xd3b4) == 0x60000 && ram[0xd3b9] == 0 && ram[0xd3bb] == 0);
    // Terminal clipping remains visible in D7 while full saved input axes are restored.
    ram.assign(65536,0); resource = path(1); put(ram,0xd3b4,4,0x60000); state = initial(); state.d0 = 0x000b0001;
    assert(ms5::resolve_scene_motion_time(ram,&resource,state,error)); assert(state.d7 == 0x0009ffff && state.d0 == 0x000b0001);
    // Missing previous window is discovered after scratch/base subtraction; entire caller state and RAM roll back.
    ram.assign(65536,0); resource = path(1); put(resource.data,0,2,10); put(resource.data,6,2,3); put(resource.data,10,2,20);
    put(ram,0xd3b4,4,0x60000); put(ram,0xd3b8,2,20); put(ram,0xd3ba,2,7); state = initial(); state.d0 = 0;
    const std::vector<std::uint8_t> before = ram; const ms5::SceneCommandState registers = state;
    assert(!ms5::resolve_scene_motion_time(ram,&resource,state,error)); assert(ram == before && same(state,registers));
    assert(!ms5::resolve_scene_motion_time(ram,NULL,state,error)); assert(ram == before && same(state,registers));
    std::cout << "scene motion time tests passed\n";
}
