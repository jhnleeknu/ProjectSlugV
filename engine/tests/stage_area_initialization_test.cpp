#include "ms5/stage_area_initialization.h"
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
ms5::FixedDataResource records() {
    ms5::FixedDataResource data; data.source_cpu_address = data.source_rom_offset = 0x4cf64; data.data.assign(320,0); return data;
}
ms5::FixedDataResource selectors() {
    ms5::FixedDataResource data; data.source_cpu_address = data.source_rom_offset = 0x4e4d2; data.data.assign(128,0);
    data.data[2] = 1; data.data[3] = 6; return data;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0); put(ram,0xcb8,0x270e,4); put(ram,0xda8,0x270e,4);
    ram[0xdd2a] = 2; ram[0xdd2b] = 3; ram[0xdd1e] = 255; return ram;
}
ms5::StageAreaInitializationState initial() {
    ms5::StageAreaInitializationState state; state.d0 = 0x12345678; state.d1 = 0xabcd1234; state.d3 = 0x98765432; return state;
}
bool same_byte(const ms5::SoundBytePending& a, const ms5::SoundBytePending& b) {
    return a.waiting == b.waiting && a.command == b.command && a.tail == b.tail && a.next == b.next;
}
bool same(const ms5::StageAreaInitializationState& a, const ms5::StageAreaInitializationState& b) {
    const ms5::GamePreludeState& p = a.initialization.prelude; const ms5::GamePreludeState& q = b.initialization.prelude;
    return a.next_pc == b.next_pc && a.phase == b.phase && a.d0 == b.d0 && a.d1 == b.d1 && a.d3 == b.d3 && a.a6 == b.a6 &&
        a.initialization.returned == b.initialization.returned && p.next_pc == q.next_pc && p.phase == q.phase && p.d0 == q.d0 && p.d1 == q.d1 && p.d3 == q.d3 &&
        p.word.kind == q.word.kind && p.word.phase == q.word.phase && p.word.low == q.word.low && p.word.cursor == q.word.cursor &&
        same_byte(p.word.byte,q.word.byte) && same_byte(p.byte,q.byte);
}
void fails(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& record, const ms5::FixedDataResource& lookup,
           const ms5::FixedDataResource& selector, ms5::StageAreaInitializationState& state) {
    const std::vector<std::uint8_t> before = ram; const ms5::StageAreaInitializationState old = state;
    std::uint8_t reads = 77; std::string error;
    assert(!ms5::step_stage_area_initialization(ram,record,lookup,selector,0,state,reads,error));
    assert(ram == before && same(state,old) && reads == 77 && !error.empty());
}
}
int main() {
    ms5::FixedDataResource record = records(), selector = selectors(), empty;
    std::vector<std::uint8_t> ram = fixture(); ms5::StageAreaInitializationState state = initial(); std::uint8_t reads = 99; std::string error;
    ram[0xd683] = 0x55;
    assert(ms5::step_stage_area_initialization(ram,record,empty,selector,0,state,reads,error));
    assert(state.phase == 2 && state.next_pc == 0x47a1c && state.d0 == 4 && state.d1 == 0 && state.d3 == 0 && reads == 0);
    assert(state.initialization.returned && ram[0xdd2a] == 255 && ram[0xdd2b] == 255 && ram[0xdd1e] == 0xbd);
    assert(ram[0xd683] == 0x55 && get(ram,0xddec) == 1 && get(ram,0xddf2) == 0 && get(ram,0xddf8) == 0x96);
    assert(get(ram,0xd734,4) == 0 && get(ram,0xd738,4) == 0);
    fails(ram,record,empty,selector,state);
    // First-area selector skips do not validate an unused lookup.
    ram = fixture(); ram[0xdd2a] = 0x80; ram[0xdd2b] = 255; state = initial();
    assert(ms5::step_stage_area_initialization(ram,record,empty,empty,0,state,reads,error));
    assert(ram[0xdd2a] == 0x80 && ram[0xdd2b] == 255 && ram[0xdd1e] == 255);
    // Non-first captures inactive records without either source lookup; it skips
    // first-area selector release, yet runs the same LIVE d684 allocation tail.
    ram = fixture(); ram[0xbad] = 1; state = initial();
    assert(ms5::step_stage_area_initialization(ram,empty,empty,empty,0,state,reads,error));
    assert(state.phase == 2 && !state.initialization.returned && state.initialization.prelude.next_pc == 0x47570);
    assert(ram[0xdd2a] == 2 && ram[0xdd2b] == 3 && get(ram,0xd69a) == 0xffff);
    ram = fixture(); ram[0xd684] = 1; state = initial();
    assert(ms5::step_stage_area_initialization(ram,record,empty,empty,0,state,reads,error));
    assert(get(ram,0xddec) == 0 && ram[0xdd2a] == 2);
    // Allocation has the original parent/live-list order and stores callback only.
    ram = fixture(); put(ram,0x4c9c,0x101800,4); put(ram,0x4ca0,1); put(ram,0xb38,0x100820,4); put(ram,0xb40,4);
    state = initial();
    assert(ms5::step_stage_area_initialization(ram,record,empty,selector,0,state,reads,error));
    assert(get(ram,0x1800,4) == 0xd764a && get(ram,0x4ca0) == 0 && get(ram,0xb38,4) == 0x101800 && state.d0 == 4);
    // Actual saved initialization is resumed despite host changing the area byte.
    ram = fixture(); ram[0xd684] = 1; put(ram,0x4d8c,6); put(ram,0x4d82,0x0455); put(ram,0x4d74,1);
    ram[0x12] = 1; ram[0xfd82] = 1; ram[0xfd8d] = 1; state = initial();
    assert(ms5::step_stage_area_initialization(ram,record,empty,empty,0,state,reads,error));
    assert(state.phase == 1 && state.next_pc == 0x3aea && state.d0 == 0x12340704 && reads == 1);
    ram[0xbad] = 1; ram[0xd683] = 0x66;
    const std::vector<std::uint8_t> waiting_ram = ram; const ms5::StageAreaInitializationState waiting = state;
    assert(ms5::step_stage_area_initialization(ram,record,empty,empty,255,state,reads,error));
    assert(ram == waiting_ram && same(state,waiting) && reads == 0);
    ms5::StageAreaInitializationState inconsistent = state; inconsistent.d1 ^= 1;
    fails(ram,record,empty,empty,inconsistent);
    for (unsigned int head = 2; head <= 5; ++head) {
        put(ram,0x4d74,head);
        assert(ms5::step_stage_area_initialization(ram,record,empty,empty,255,state,reads,error));
        assert(reads == 0);
    }
    assert(state.phase == 2 && state.initialization.returned && state.d0 == 4 && ram[0xd683] == 0x66);
    // Errors after the entire initialization/selector prefix discard all outputs.
    ram = fixture(); state = initial(); fails(ram,record,empty,empty,state);
    ram = fixture(); put(ram,0x4ca0,1); put(ram,0x4c9c,0x100001,4); state = initial();
    fails(ram,record,empty,selector,state);
    ram = fixture(); state = initial(); state.a6 |= 1; fails(ram,record,empty,selector,state);
    ram = fixture(); state = initial(); state.initialization.prelude.d0 = 1; fails(ram,record,empty,selector,state);
    std::cout << "stage_area_initialization_test: passed\n";
}
