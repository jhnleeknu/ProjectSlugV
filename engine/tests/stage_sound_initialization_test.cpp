#include "ms5/stage_sound_initialization.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value, unsigned int size = 2) {
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size = 2) {
    std::uint32_t value = 0;
    for (unsigned int i = 0; i < size; ++i) value = (value << 8) | ram[at + i];
    return value;
}
ms5::StageCatalog catalog(unsigned int selected) {
    ms5::StageCatalog result; result.groups.resize(1); ms5::StageRecord record;
    record.source_cpu_address = 0x50004; record.data.assign(18,0); put(record.data,16,selected);
    result.groups[0].records.push_back(record); return result;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0); put(ram,0xba6,0x50004,4); return ram;
}
ms5::StageSoundState initial() {
    ms5::StageSoundState state; state.d0 = 0x12345678; state.d1 = 0xabcd1234; state.d3 = 0x98765432; return state;
}
bool same_byte(const ms5::SoundBytePending& a, const ms5::SoundBytePending& b) {
    return a.waiting == b.waiting && a.command == b.command && a.tail == b.tail && a.next == b.next;
}
bool same(const ms5::StageSoundState& a, const ms5::StageSoundState& b) {
    return a.next_pc == b.next_pc && a.phase == b.phase && a.d0 == b.d0 && a.d1 == b.d1 && a.d3 == b.d3 && a.a6 == b.a6 &&
        a.word.kind == b.word.kind && a.word.phase == b.word.phase && a.word.low == b.word.low && a.word.cursor == b.word.cursor &&
        same_byte(a.word.byte,b.word.byte) && same_byte(a.byte,b.byte);
}
void fails(std::vector<std::uint8_t>& ram, const ms5::StageCatalog& data, ms5::StageSoundState& state) {
    const std::vector<std::uint8_t> before = ram; const ms5::StageSoundState old = state; std::uint8_t reads = 77; std::string error;
    assert(!ms5::initialize_stage_sound(ram,data,0,state,reads,error));
    assert(ram == before && same(state,old) && reads == 77 && !error.empty());
}
}
int main() {
    std::vector<std::uint8_t> ram = fixture(); ms5::StageSoundState state = initial(); std::uint8_t reads = 99; std::string error;
    ram[0x4d7e] = 1;
    assert(ms5::initialize_stage_sound(ram,catalog(0x19c0),0,state,reads,error));
    assert(state.phase == 9 && state.next_pc == 0x47a94 && state.d0 == 0x12341820 && state.d1 == 0xabcd0004 && state.d3 == 0x98765432);
    assert(get(ram,0xd686) == 0x19c0 && ram[0x4cf4] == 8 && ram[0x4cf5] == 0x20 && ram[0x4cf6] == 8 && ram[0x4cf7] == 0x20 && ram[0x4d7e] == 0);
    fails(ram,catalog(0x19c0),state);
    // Synthetic10fe skip is distinct from claims about canonical ROM records.
    ram = fixture(); state = initial();
    assert(ms5::initialize_stage_sound(ram,catalog(0x10fe),0,state,reads,error));
    assert(state.d1 == 0xabcd0002 && get(ram,0x4d82) == 0x1890 && get(ram,0x4d84) == 0x1891 && get(ram,0x4d86) == 0x1892);
    ram = fixture(); state = initial(); ram[0x12] = 1; ram[0xfd82] = 1; ram[0xfd8d] = 1;
    assert(ms5::initialize_stage_sound(ram,catalog(0x0620),0,state,reads,error));
    assert(reads == 4 && state.d0 == 0x12341820 && state.d1 == 0xabcd0004 && ram[0x4cf4] == 6 && ram[0x4cf5] == 0x20);
    // Initial+three common words each suspend on both bytes, then final08/20.
    ram = fixture(); state = initial(); put(ram,0x4d82,0x0422); put(ram,0x4d84,0x0523); put(ram,0x4d86,0x0624);
    put(ram,0x4d8c,6); put(ram,0x4d74,1);
    assert(ms5::initialize_stage_sound(ram,catalog(0x0725),0,state,reads,error));
    assert(state.phase == 1 && state.word.phase == 1 && state.d0 == 0x12340704);
    put(ram,0xba6,0xffff,4); put(ram,0xd686,0xbeef);
    const std::vector<std::uint8_t> waiting_ram = ram; const ms5::StageSoundState waiting = state; ms5::StageCatalog empty;
    assert(ms5::initialize_stage_sound(ram,empty,255,state,reads,error));
    assert(ram == waiting_ram && same(state,waiting) && reads == 0);
    const unsigned int phases[10] = {1,4,4,5,5,6,6,7,8,9};
    for (unsigned int i = 0; i < 10; ++i) {
        put(ram,0x4d74,i + 2);
        assert(ms5::initialize_stage_sound(ram,empty,0,state,reads,error));
        assert(state.phase == phases[i] && state.d3 == 0x98765432 && state.a6 == 0x100b30);
    }
    assert(state.d0 == 0x12341820 && state.d1 == 0xabcd000a && get(ram,0xd686) == 0xbeef);
    ram = fixture(); state = initial(); put(ram,0x4d74,1);
    assert(ms5::initialize_stage_sound(ram,catalog(0x19c0),0,state,reads,error));
    assert(state.phase == 2 && state.d0 == 0x12341908);
    put(ram,0x4d74,2);
    assert(ms5::initialize_stage_sound(ram,empty,0,state,reads,error));
    assert(state.phase == 3 && state.d0 == 0x12341920);
    ms5::StageSoundState bad = state; bad.d1 ^= 1; fails(ram,empty,bad);
    put(ram,0x4d74,128); fails(ram,empty,state);
    // Late byte failure rolls back music publication and three word enqueues.
    ram = fixture(); state = initial(); put(ram,0x4d74,128); fails(ram,catalog(0x19c1),state);
    ram = fixture(); state = initial(); fails(ram,empty,state);
    ms5::StageCatalog short_record = catalog(0x19c1); short_record.groups[0].records[0].data.resize(17);
    fails(ram,short_record,state);
    state.word.low = 1; fails(ram,catalog(0x19c1),state);
    std::cout << "stage_sound_initialization_test: passed\n";
}
