#include "ms5/scene_command.h"
#include <cassert>
#include <iostream>
namespace {
void append(std::vector<std::uint8_t>& data, unsigned int value) {
    data.push_back(static_cast<std::uint8_t>(value >> 8)); data.push_back(static_cast<std::uint8_t>(value));
}
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size = 4) {
    std::uint32_t value = 0;
    for (unsigned int i = 0; i < size; ++i) value = (value << 8) | ram[at + i];
    return value;
}
ms5::SceneScript script(unsigned int opcode, const std::vector<unsigned int>& words, unsigned int inline_bytes = 0) {
    ms5::FixedDataResource source; source.source_cpu_address = source.source_rom_offset = 0x50000;
    append(source.data,opcode);
    for (std::size_t i = 0; i < words.size(); ++i) append(source.data,words[i]);
    for (unsigned int i = 0; i < inline_bytes; ++i) source.data.push_back(255);
    append(source.data,0xffff); ms5::SceneScript result; std::string error;
    assert(ms5::decode_scene_script(source,result,error)); return result;
}
ms5::SceneCommandState initial() {
    ms5::SceneCommandState state; state.d0 = 0x12345678; state.d1 = 0x23456789; state.d2 = 0x24681357; state.d4 = 0x13572468; state.d3 = 0x3456789a;
    state.d5 = 0x76543210; state.d6 = 0x6543210f; state.d7 = 0x456789ab; state.a0 = 0x56789abc; state.a1 = 0x50000; state.a2 = 0xabcdefff; return state;
}
ms5::FixedDataResource pointers() {
    ms5::FixedDataResource result; result.source_cpu_address = result.source_rom_offset = 0x1a08e; result.data.assign(16,0);
    for (unsigned int i = 0; i < 4; ++i) put(result.data,i*4,0x101000 + i*0x100);
    return result;
}
bool same(const ms5::SceneCommandState& a, const ms5::SceneCommandState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d4 == b.d4 && a.d3 == b.d3 && a.d5 == b.d5 && a.d6 == b.d6 && a.d7 == b.d7 && a.a0 == b.a0 && a.a1 == b.a1 && a.a2 == b.a2;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::SceneCommandState state; std::vector<ms5::VideoPortWrite> ports;
    std::string error; ms5::FixedDataResource table = pointers(), empty;
    const unsigned int opcodes[9] = {0x0c,0x28,0x30,0x38,0x3c,0x44,0x48,0x4c,0x20};
    const std::size_t destinations[8] = {0xd40e,0xd416,0xd426,0xd3fc,0xd432,0xd42e,0xd43c,0xd434};
    for (unsigned int i = 0; i < 9; ++i) {
        const unsigned int lengths[9] = {2,1,4,4,1,2,1,2,1};
        std::vector<unsigned int> words(lengths[i],0x1234); ms5::SceneScript source = script(opcodes[i],words);
        state = initial(); ram[0xd40c] = 0xff;
        assert(ms5::execute_scene_command(ram,source,empty,state,ports,error));
        assert(state.a1 == 0x50002 + lengths[i]*2 && ports.empty() && state.d5 == 0x76543210 && state.d6 == 0x6543210f);
        assert(state.d7 == (i == 8 ? 0x45670036U : (0x45670000U | opcodes[i])));
        if (i < 8) assert(get(ram,destinations[i],i == 0 || i == 3 || i == 7 ? 4 : 2) == (i == 0 || i == 3 || i == 7 ? 0x12341234U : 0x1234U));
    }
    state = initial(); ram[0xd3cc] = 0xf8;
    assert(ms5::execute_scene_command(ram,script(0x34,{0x8001}),empty,state,ports,error));
    assert(state.d0 == 0x12340003 && state.d1 == 0x234567fb && ram[0xd3cc] == 0xfb);
    state = initial();
    assert(ms5::execute_scene_command(ram,script(0x2c,{0xffff,0x8000,4},4),empty,state,ports,error));
    assert(get(ram,0xd416,2) == 0x7fff && get(ram,0xd41e,2) == 0x7fff && get(ram,0xd420,2) == 0xffff);
    assert(get(ram,0xd422) == 0x50008 && state.d0 == 0x12340004 && state.a1 == 0x5000c);
    state = initial(); ram[0x4d91] = 0xf3;
    assert(ms5::execute_scene_command(ram,script(0x40,{0}),empty,state,ports,error));
    assert(state.d0 == 0x1234ffff && ram[0x4d90] == 0 && ram[0x4d91] == 0xfb && ports.size() == 1 && ports[0].value == 0xfb);
    state = initial();
    assert(ms5::execute_scene_command(ram,script(0x40,{0x123}),empty,state,ports,error));
    assert(state.d0 == 0x12340122 && ports[0].value == 0x22f3 && ports[0].address == 0x3c0006 && ports[0].size == 2);
    state = initial();
    assert(ms5::execute_scene_command(ram,script(0x18,{4,0xfffe,0x1234}),table,state,ports,error));
    assert(get(ram,0x1128) == 0xfffe1234 && state.a0 == 0x101100 && state.d7 == 0x45670004);
    state = initial(); ram[0x117a] = 0x42;
    assert(ms5::execute_scene_command(ram,script(0x1c,{4,1}),table,state,ports,error));
    assert(ram[0x117a] == 0xc3);
    state = initial(); put(ram,0x1126,0xffff,2);
    assert(ms5::execute_scene_command(ram,script(0x1c,{4,0}),table,state,ports,error));
    assert(ram[0x117a] == 0xc2 && ports.empty() && state.d7 == 0x4567ffff && state.d5 == 0x76543210 && state.d6 == 0x6543210f);
    const unsigned int slots[3] = {0,1,0x7fff};
    for (unsigned int index = 0; index < 3; ++index) {
        const unsigned int slot = slots[index]; state = initial(); put(ram,0x1126,slot,2);
        assert(ms5::execute_scene_command(ram,script(0x1c,{4,0}),table,state,ports,error));
        assert(ports.size() == 65 && ports[0].size == 1 && ports[0].address == 0x300001 && ports[0].value == 0x78);
        const std::uint32_t first7 = (static_cast<std::uint32_t>(static_cast<std::uint16_t>(slot + 0x8201)) << 16) | 0x8000U;
        const std::uint32_t first6 = (static_cast<std::uint32_t>(static_cast<std::uint16_t>(slot + 0x8001)) << 16) | 0x0fffU;
        for (unsigned int column = 0; column < 32; ++column) {
            assert(ports[column*2 + 1].size == 4 && ports[column*2 + 1].address == 0x3c0000 && ports[column*2 + 1].value == first7 + column*0x10000U);
            assert(ports[column*2 + 2].size == 4 && ports[column*2 + 2].address == 0x3c0000 && ports[column*2 + 2].value == first6 + column*0x10000U);
        }
        assert(state.d7 == first7 + 0x200000U && state.d6 == first6 + 0x200000U && state.d5 == 0x10000);
        assert(state.d0 == 0x12345678 && state.d1 == 0x23456789 && state.d3 == 0x3456789a && state.a1 == 0x50006);
    }
    state = initial(); put(ram,0x1126,0x8000,2);
    assert(ms5::execute_scene_command(ram,script(0x1c,{4,0}),table,state,ports,error));
    assert(ports.empty() && state.d7 == 0x45678000 && state.d5 == 0x76543210 && state.d6 == 0x6543210f);
    state = initial(); put(ram,0xd38e,0x00008000); put(ram,0xd392,0xffff8000); put(ram,0x1018,0xdeadbeef); put(ram,0x1014,0x87654321); ram[0xd494] = 0xab;
    assert(ms5::execute_scene_command(ram,script(0x14,{0,0xffff,2}),table,state,ports,error));
    assert(state.d2 == 0x87654321 && state.d4 == 0x13572400 && state.d5 == 0x765432ab && state.d6 == 0x6543210f);
    assert(state.d0 == 0xffff8000 && state.d1 == 0x00018000 && state.d3 == 0xdeadbeef && state.d7 == 0 && state.a0 == 0x101000 && state.a1 == 0x50008);
    assert(get(ram,0x1014) == 0xffff8000 && get(ram,0x1018) == 0x18000 && get(ram,0x102c,2) == 0);
    // Global stamp aliases a history field written after the native D5 read.
    ms5::FixedDataResource alias_table = table; put(alias_table.data,0,0x10d478);
    state = initial(); ram[0xd494] = 0xab;
    assert(ms5::execute_scene_command(ram,script(0x14,{0,0,0}),alias_table,state,ports,error));
    assert(state.d5 == 0x765432ab && ram[0xd494] != 0xab);
    assert(state.d4 == 0x13572400 && state.d7 == 0 && state.d6 == 0x6543210f);
    std::vector<ms5::FixedDataResource> dependencies;
    ms5::FixedDataResource indirect; indirect.source_cpu_address = indirect.source_rom_offset = 0x60000; indirect.data.assign(4,0); dependencies.push_back(indirect);
    state = initial();
    assert(ms5::execute_scene_command(ram,script(0x10,{6,0}),empty,state,ports,error,&dependencies));
    assert(state.a0 == 0xe89ec && get(ram,0xde2a) == 0xe89ec && state.a2 == 0xabcdefff);
    put(dependencies[0].data,0,0x12345678); state = initial();
    assert(ms5::execute_scene_command(ram,script(0x10,{6,0}),empty,state,ports,error,&dependencies));
    assert(state.a0 == 0x12345678 && get(ram,0xde2a) == 0x12345678);
    ms5::FixedDataResource paths; paths.source_cpu_address = paths.source_rom_offset = 0x1a0a6; paths.data.assign(16,0);
    put(paths.data,4,0x101234); dependencies.push_back(paths); state = initial();
    assert(ms5::execute_scene_command(ram,script(0x24,{4,0xffff,0xffff}),empty,state,ports,error,&dependencies));
    assert(get(ram,0x1234) == 0xffffffff && state.a2 == 0xffffffff && state.d7 == 0x45670004 && state.a1 == 0x50008);
    state = initial(); put(ram,0xd3a2,0x12345678); put(ram,0xd3a6,0x87654321); ram[0xd494] = 0x5a;
    assert(ms5::execute_scene_command(ram,script(0,{1,2,0,0}),empty,state,ports,error));
    assert(state.d0 == 0xffff0000 && state.d1 == 0x00fe0000 && state.d2 == 0x12345678 && state.d3 == 0x87654321);
    assert(state.d4 == 0x13572400 && state.d5 == 0x7654325a && state.d7 == 0x7fff && state.a0 == 0x10d38e && state.a2 == 0);
    ms5::FixedDataResource motion; motion.source_cpu_address = motion.source_rom_offset = 0x70000;
    const unsigned int motion_words[7] = {1,0x14,0,2,4,10,0xffff};
    for (unsigned int i = 0; i < 7; ++i) append(motion.data,motion_words[i]);
    dependencies.push_back(motion); state = initial();
    assert(ms5::execute_scene_command(ram,script(0,{1,2,7,0}),empty,state,ports,error,&dependencies));
    assert(get(ram,0xd3ba,2) == 4 && get(ram,0xd3c0,2) == 6 && state.d1 == 0x00fa0000 && state.d4 == 0x13570000 && state.d7 == 9);
    dependencies.back().data[3] = 0x64; state = initial();
    assert(ms5::execute_scene_command(ram,script(0,{1,2,7,0}),empty,state,ports,error,&dependencies));
    assert(get(ram,0xd3b8,2) == 3 && get(ram,0xd3bc,2) == 5 && state.d0 == 0xfffb0000);
    const std::vector<std::uint8_t> invalid_before = ram; state = initial(); const ms5::SceneCommandState invalid_state = state;
    dependencies.back().data[3] = 1; ports.assign(1,ms5::VideoPortWrite{123,456,2});
    assert(!ms5::execute_scene_command(ram,script(0,{1,2,7,0}),empty,state,ports,error,&dependencies));
    assert(ram == invalid_before && same(state,invalid_state) && ports[0].value == 456);
    dependencies.back().data[3] = 0x14; dependencies.back().data.pop_back();
    assert(!ms5::execute_scene_command(ram,script(0,{1,2,7,0}),empty,state,ports,error,&dependencies));
    assert(ram == invalid_before && same(state,invalid_state) && ports[0].value == 456);
    assert(!ms5::execute_scene_command(ram,script(0x10,{6,0}),empty,state,ports,error));
    assert(ram == invalid_before && same(state,invalid_state) && ports[0].value == 456);
    assert(!ms5::execute_scene_command(ram,script(0x24,{2,0,0}),empty,state,ports,error,&dependencies));
    assert(ram == invalid_before && same(state,invalid_state) && ports[0].value == 456);
    put(dependencies[1].data,4,0x10fffe);
    assert(!ms5::execute_scene_command(ram,script(0x24,{4,0,0}),empty,state,ports,error,&dependencies));
    assert(ram == invalid_before && same(state,invalid_state) && ports[0].value == 456);
    // Forged decoded metadata cannot redirect execution away from raw source.
    ms5::SceneScript forged = script(0x4c,{0x1234,0x5678}); forged.commands[0].opcode = 0x40; forged.commands[0].operands.clear();
    state = initial();
    assert(ms5::execute_scene_command(ram,forged,empty,state,ports,error));
    assert(get(ram,0xd434) == 0x12345678 && state.d7 == 0x4567004c);
    // Failed resource/node checks preserve every output.
    const unsigned int unsupported[2] = {4,8}; const unsigned int counts[2] = {1,2};
    ms5::VideoPortWrite marker = {123,456,2}; ports.assign(1,marker);
    for (unsigned int i = 0; i < 2; ++i) {
        state = initial(); const ms5::SceneCommandState old = state; const std::vector<std::uint8_t> before = ram;
        assert(!ms5::execute_scene_command(ram,script(unsupported[i],std::vector<unsigned int>(counts[i],0)),empty,state,ports,error));
        assert(ram == before && same(state,old) && ports.size() == 1 && ports[0].value == 456);
    }
    state = initial(); const ms5::SceneCommandState old = state; const std::vector<std::uint8_t> before = ram;
    assert(!ms5::execute_scene_command(ram,script(0x14,{2,0,0}),table,state,ports,error));
    assert(ram == before && same(state,old) && ports[0].value == 456);
    put(table.data,0,0x100001);
    assert(!ms5::execute_scene_command(ram,script(0x14,{0,0,0}),table,state,ports,error));
    assert(ram == before && same(state,old) && ports[0].value == 456);
    state.a1 += 2; const ms5::SceneCommandState inside = state;
    assert(!ms5::execute_scene_command(ram,forged,empty,state,ports,error));
    assert(ram == before && same(state,inside) && ports[0].value == 456);
    std::cout << "scene_command_test: passed\n";
}
