#include "ms5/game_startup.h"
#include "ms5/palette_state.h"
#include "ms5/random_state.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& data,std::size_t at,unsigned int value) {
    data[at] = static_cast<std::uint8_t>(value >> 8); data[at + 1] = static_cast<std::uint8_t>(value);
}
ms5::FixedDataResource bindings() {
    ms5::FixedDataResource data;
    data.source_cpu_address = data.source_rom_offset = 0xe7b58;
    data.data.assign(104,0);
    for (unsigned int index = 0; index < 17; ++index) {
        put(data.data,index * 6,index); put(data.data,index * 6 + 2,index + 1);
    }
    put(data.data,102,0xffff); return data;
}
bool same(const ms5::GameStartupState& a,const ms5::GameStartupState& b) {
    return a.next_pc == b.next_pc && a.object_offset == b.object_offset && a.d0 == b.d0 && a.d1 == b.d1 && a.d3 == b.d3;
}
void fails(std::vector<std::uint8_t>& ram,const std::vector<ms5::PaletteRecord>& fill,
           const ms5::FixedDataResource& table,ms5::GameStartupState& state) {
    const std::vector<std::uint8_t> before = ram; const ms5::GameStartupState saved = state;
    std::vector<ms5::VideoPortWrite> ports(1); ports[0].size = 2; ports[0].address = 123; ports[0].value = 456;
    std::string error;
    assert(!ms5::step_game_startup(ram,fill,table,state,ports,error));
    assert(ram == before && same(state,saved) && !error.empty());
    assert(ports.size() == 1 && ports[0].size == 2 && ports[0].address == 123 && ports[0].value == 456);
}
}
int main() {
    std::vector<ms5::PaletteRecord> fill(2048);
    for (unsigned int index = 0; index < 2048; ++index) fill[index].id = index;
    for (unsigned int index = 0; index < 16; ++index) fill[0].hardware_words[index] = static_cast<std::uint16_t>(0x1230 + index);
    const ms5::FixedDataResource table = bindings(),absent;
    std::vector<std::uint8_t> ram(65536,0);
    std::string error; assert(ms5::initialize_palette_state(&ram[0],ram.size(),error));
    for (unsigned int offset = 0x76; offset <= 0x83; ++offset) ram[0x200 + offset] = 0xa5;
    ram[0x284] = 0x69; put(ram,0x7da2,0x5678);
    ms5::GameStartupState state; state.object_offset = 0x200;
    state.d0 = 0xabcd1234; state.d1 = 0x9876abcd; state.d3 = 0xbeef1234;
    std::vector<ms5::VideoPortWrite> ports;
    assert(ms5::step_game_startup(ram,fill,absent,state,ports,error));
    assert(state.next_pc == 0xc560 && state.d0 == 0x79a02000 && state.d1 == 0x9876abcd && state.d3 == 0xbeef1234);
    assert(ports.size() == 4);
    for (unsigned int index = 0; index < 4; ++index) {
        assert(ports[index].size == 2 && ports[index].address == ((index & 1) ? 0x2ffff0U : 0x2ffff2U));
        assert(ports[index].value == ((index & 1) ? 0U : 0x1000U));
    }
    assert(ram[0x7dea] == 0x20 && ram[0x7deb] == 0 && ram[0x7def] == 255);
    assert(ram[0x200] == 0 && ram[0x201] == 0 && ram[0x202] == 0xc5 && ram[0x203] == 0x60);
    for (unsigned int offset = 0x76; offset <= 0x81; ++offset) assert(ram[0x200 + offset] == 0);
    assert(ram[0x282] == 0xa5 && ram[0x283] == 0 && ram[0x284] == 0x69);
    assert(ram[0x7da2] == 0x56 && ram[0x7da3] == 0x78 && ram[0x7da4] == 0x12 && ram[0x7da5] == 0x31);
    // Once c560 is reached, polling does not redo object clearing or fill setup.
    ram[0x276] = 0x69;
    const std::vector<std::uint8_t> waiting = ram; const ms5::GameStartupState pending = state;
    const std::vector<ms5::PaletteRecord> no_fill;
    assert(ms5::step_game_startup(ram,no_fill,absent,state,ports,error));
    assert(ram == waiting && same(state,pending) && ports.empty());
    put(ram,0x7dea,0);
    fails(ram,no_fill,absent,state); // Late invalid binding after c560 reads ready.
    const std::vector<std::uint8_t> before_ready = ram;
    std::vector<std::uint8_t> expected = ram;
    std::uint32_t expected_d0 = 0,expected_d1 = 0x98760001;
    assert(ms5::seed_random(expected,expected_d0,expected_d1,error));
    assert(ms5::step_game_startup(ram,no_fill,table,state,ports,error));
    assert(state.next_pc == 0xc584 && state.d0 == expected_d0 && state.d1 == expected_d1 && (state.d3 >> 16) == 0xbeef);
    assert(ram[0xf004] == 3 && ram[0x276] == before_ready[0x276] && ram[0x282] == 0xa5);
    for (unsigned int at = 0xd6b4; at < 0xd726; ++at) assert(ram[at] == expected[at]);
    assert(ports.size() == 2 && ports[0].address == 0x300001 && ports[0].value == 0 && ports[1].value == 0);
    fails(ram,fill,table,state); // c584 external stage call is beyond this API.
    state.next_pc = 0xc52a; fails(ram,no_fill,table,state);
    state.object_offset = 1; fails(ram,fill,table,state);
    state.object_offset = 65536 - 0x82; fails(ram,fill,table,state);
    state.object_offset = 0x200; state.next_pc = 0xc560;
    // Corrupt the last target bucket so earlier fixed bindings cannot leak out.
    put(ram,0x4d92 + 17 * 16 + 6,0x1234); fails(ram,no_fill,table,state);
    std::cout << "Game startup fill suspension, register carry, seed and rollback passed\n";
}
