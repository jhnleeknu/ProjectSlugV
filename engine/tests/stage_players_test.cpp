#include "ms5/stage_players.h"
#include "ms5/game_objects.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size = 4) {
    std::uint32_t value = 0;
    for (unsigned int i = 0; i < size; ++i) value = (value << 8) | ram[at + i];
    return value;
}
ms5::StagePlayersState initial() {
    ms5::StagePlayersState state; state.d0 = 0x12340000; state.d1 = 0xabcd0002; state.d3 = 0x98761234; return state;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0xcb8,0x270e); put(ram,0xda8,0x270e); put(ram,0x9a8,0x270e); put(ram,0xa6c,0x270e);
    ram[0xcb8 + 0x6c] = ram[0xda8 + 0x6c] = 255;
    put(ram,0xd722,0x10d6b4); put(ram,0xd6b4,5,2); return ram;
}
ms5::FixedDataResource table() {
    ms5::FixedDataResource resource; resource.source_cpu_address = resource.source_rom_offset = 0x476bc;
    resource.data.assign(1040,0);
    for (unsigned int i = 0; i < 3; ++i) put(resource.data,0x14 + i*4,0x476bc + i*8);
    put(resource.data,0,2,2); put(resource.data,2,3,2); return resource;
}
bool same(const ms5::StagePlayersState& a, const ms5::StagePlayersState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d3 == b.d3 && a.a6 == b.a6;
}
}
int main() {
    std::vector<std::uint8_t> ram = fixture(); ms5::StagePlayersState state = initial();
    std::vector<ms5::VideoPortWrite> ports; std::string error;
    assert(ms5::configure_stage_player(ram,state,ports,error));
    assert(get(ram,0xcb8) == 0x1d1f4 && get(ram,0xcb8 + 0x76,2) == 2 && get(ram,0xcb8 + 0x78,2) == 0);
    assert(get(ram,0xcb8 + 0x8c) == 0x10d450 && ram[0xd456] == 1 && ram[0xd457] == 10);
    assert(state.d0 == 2 && state.d1 == 0xffffffff && state.d3 == 0x98761234 && ports.size() == 1 && ports[0].value == 0);
    // Active callback zero skips restart and first initialization; D1 is preserved.
    ram = fixture(); put(ram,0xda8,0); put(ram,0xda8 + 0x78,0x1234,2);
    state = initial(); state.d0 |= 2; state.d1 = 0xabcd0004;
    assert(ms5::configure_stage_player(ram,state,ports,error));
    assert(state.d0 == 0x12340001 && state.d1 == 0xabcd0004 && ports.empty());
    assert(get(ram,0xda8) == 0 && get(ram,0xda8 + 0x78,2) == 0x1234 && get(ram,0xda8 + 0x76,2) == 1);
    assert(get(ram,0xd722) == 0x10d6b6);
    ram = fixture(); state = initial(); state.a6 = 0xffffffff; state.d1 = 0xabcdffff;
    assert(ms5::configure_stage_player(ram,state,ports,error));
    assert(state.a6 == 0xffffffff && state.d0 == 0 && state.d1 == 0xffffffff && state.d3 == 0x98761234);
    assert(get(ram,0xcb8) == 0x270e && ports.size() == 1);
    // Exposed first setup retains its original parity-vs-nonzero distinction.
    ram = fixture(); put(ram,0xcb8,0); put(ram,0xcb8 + 0x78,2,2); ram[0xd450] = 9; ram[0xd460] = 9;
    std::uint32_t d0 = 0x43210000;
    assert(ms5::initialize_game_object(ram,0x100cb8,d0,error));
    assert(d0 == 0x43210002 && get(ram,0xcb8 + 0x8c) == 0x10d460 && ram[0xd450] == 0 && ram[0xd460] == 9);
    ms5::FixedDataResource resource = table(); ram = fixture(); state = initial();
    assert(ms5::configure_stage_players(ram,resource,state,ports,error));
    assert(get(ram,0xcb8 + 0x76,2) == 2 && get(ram,0xda8 + 0x76,2) == 3 && ports.size() == 2);
    assert(state.d0 == 3 && state.d1 == 0xffffffff && state.a6 == 0x100b30);
    ram = fixture(); put(ram,0x9a8,0); put(ram,0xa6c,0); ram[0xbad] = 255;
    state = initial();
    assert(ms5::configure_stage_players(ram,resource,state,ports,error));
    assert(state.d0 == 1020 && state.d1 == 0xabcd0000 && ports.empty());
    // First player changes are discarded when second removal reaches a TRAP-excluded depth.
    ram = fixture(); put(resource.data,2,0xffff,2); put(ram,0xda8 + 0x10,1,2); state = initial();
    ms5::VideoPortWrite marker = {123,456,2}; ports.assign(1,marker);
    const std::vector<std::uint8_t> before = ram; const ms5::StagePlayersState old = state;
    assert(!ms5::configure_stage_players(ram,resource,state,ports,error));
    assert(ram == before && same(state,old) && ports.size() == 1 && ports[0].value == 456);
    // Caller bypass does not validate an unused table or arbitrary A6.
    ram = fixture(); state = initial(); state.a6 = 0xffffffff; ms5::FixedDataResource empty;
    assert(ms5::begin_stage_players(ram,empty,state,ports,error));
    assert(ram[0xd681] == 255 && state.d0 == 0x12340000 && state.a6 == 0xffffffff && ports.empty());
    // With A6+7d aliasing d681, area is read AFTER caller stores ff.
    ram = fixture(); put(ram,0x9a8,0); put(ram,0xa6c,0); ram[0xd680] = 8; ram[0xd684] = 1;
    resource = table(); put(resource.data,1036,0x1234,2); put(resource.data,1038,0x5678,2);
    state = initial(); state.a6 = 0x10d604;
    assert(ms5::begin_stage_players(ram,resource,state,ports,error));
    assert(state.d0 == 1020 && state.d1 == 0xabcd5678 && state.a6 == 0x10d604 && ports.empty());
    ram = fixture(); ram[0xd684] = 1; state = initial();
    const std::vector<std::uint8_t> enabled = ram;
    assert(!ms5::begin_stage_players(ram,empty,state,ports,error));
    assert(ram == enabled && same(state,old) && ports.empty());
    std::cout << "stage_players_test: passed\n";
}
