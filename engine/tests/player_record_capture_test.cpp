#include "ms5/player_record_capture.h"
#include "ms5/game_initialization.h"
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
ms5::FixedDataResource table() {
    ms5::FixedDataResource lookup; lookup.source_cpu_address = lookup.source_rom_offset = 0x4cf64;
    lookup.data.assign(4092,0); put(lookup.data,26,0xabcd); put(lookup.data,42,0x1234); put(lookup.data,4090,0xffff);
    return lookup;
}
ms5::PlayerRecordState initial() {
    ms5::PlayerRecordState state;
    state.d0 = 0x12340100; state.d1 = 0x23456789; state.d2 = 0x3456789a;
    state.d3 = 0x456789ab; state.d4 = 0x56789abc; state.d5 = 0x6789abcd; state.d6 = 0x789abcde; return state;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0xcb8 + 0x8c,0x10d450,4); put(ram,0xda8 + 0x8c,0x10d460,4);
    for (unsigned int i = 0; i < 2; ++i) {
        const std::size_t source = 0xdcba + i*0x2c;
        put(ram,source,1); ram[source + 0x27] = static_cast<std::uint8_t>(i + 1);
        ram[source + 0x25] = static_cast<std::uint8_t>(0x12 + i); ram[source + 0x26] = static_cast<std::uint8_t>(0x23 + i);
        ram[source + 0x2a] = static_cast<std::uint8_t>(0x34 + i); put(ram,source + 0x1c,0x5678 + i); put(ram,source + 0x20,0x9abc + i);
    }
    return ram;
}
bool same(const ms5::PlayerRecordState& a, const ms5::PlayerRecordState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4 && a.d5 == b.d5 && a.d6 == b.d6;
}
}
int main() {
    std::vector<std::uint8_t> ram = fixture(); ms5::FixedDataResource lookup = table(); std::string error;
    ms5::PlayerRecordState state = initial(); const std::vector<std::uint8_t> original = ram;
    assert(ms5::read_player_record(ram,lookup,state,error));
    assert(ram == original && state.d0 == 1 && state.d1 == 0x23456712 && state.d2 == 0x34567823);
    assert(state.d3 == 0x45675678 && state.d4 == 0xabcd && state.d5 == 0x67899abc && state.d6 == 0x789abc34);
    state = initial(); state.d0 = 0x123400ff;
    assert(ms5::read_player_record(ram,lookup,state,error));
    assert(state.d0 == 2 && state.d4 == 0x1234 && state.d1 == 0x23456713);
    ram[0xdce6 + 0x27] = 255; state = initial(); state.d0 = 1;
    assert(ms5::read_player_record(ram,lookup,state,error));
    assert(state.d0 == 255 && state.d4 == 0xffff);
    // Inactive and source-zero paths do not inspect an unused lookup.
    ram = fixture(); put(ram,0xcb8,0x270e,4); state = initial(); ms5::FixedDataResource empty;
    assert(ms5::read_player_record(ram,empty,state,error));
    assert(state.d0 == 0x12340000 && state.d1 == 0 && state.d2 == 0 && state.d3 == 0 && state.d4 == 0 && state.d5 == 0xffffffff && state.d6 == 0);
    put(ram,0xcb8,0,4); put(ram,0xdcba,0); state = initial();
    assert(ms5::read_player_record(ram,empty,state,error));
    assert(state.d5 == 0xffffffff && state.d0 == 0x12340000);
    ram = fixture(); state = initial(); state.d0 = 0x12340002;
    assert(ms5::capture_player_record(ram,lookup,state,error));
    assert(ram[0xd694] == 1 && ram[0xd695] == 0x34 && ram[0xd696] == 0x23 && ram[0xd697] == 0x12);
    assert(get(ram,0xd698) == 0x5678 && get(ram,0xd69a) == 0x9abc && ram[0xd69c] == 0);
    state = initial(); state.d0 = 0xffffffff;
    assert(ms5::capture_player_record(ram,lookup,state,error));
    assert(ram[0xd69c] == 2 && get(ram,0xd6a0) == 0x5679 && get(ram,0xd6a2) == 0x9abd);
    ram = fixture(); ram[0xdcba + 0x27] = 0; state = initial();
    const std::vector<std::uint8_t> malformed = ram; const ms5::PlayerRecordState old = state;
    assert(!ms5::capture_player_record(ram,lookup,state,error));
    assert(ram == malformed && same(state,old));
    ram = fixture(); const std::vector<std::uint8_t> valid = ram;
    assert(!ms5::read_player_record(ram,empty,state,error));
    assert(ram == valid && same(state,old));
    // Both captures survive the area resets, while active sources are cleared.
    std::uint32_t d0 = 0x12345678, d1 = 0x23456789, d3 = 0x3456789a;
    assert(ms5::resume_stage_area(ram,lookup,d0,d1,d3,error));
    assert(d0 == 0 && d1 == 0 && d3 == 0 && get(ram,0xd690) == 0xa0 && get(ram,0xd692) == 0x180);
    assert(ram[0xd694] == 1 && ram[0xd69c] == 2 && get(ram,0xd698) == 0x5678 && get(ram,0xd6a0) == 0x5679);
    assert(get(ram,0xdcba) == 0 && get(ram,0xdce6) == 0);
    ram = fixture(); ram[0xdce6 + 0x27] = 0;
    const std::vector<std::uint8_t> second_bad = ram; d0 = 0x12345678; d1 = 0x23456789; d3 = 0x3456789a;
    assert(!ms5::resume_stage_area(ram,lookup,d0,d1,d3,error));
    assert(ram == second_bad && d0 == 0x12345678 && d1 == 0x23456789 && d3 == 0x3456789a);
    ram = fixture(); put(ram,0xda8 + 0x8c,0x100001,4);
    const std::vector<std::uint8_t> late_bad = ram;
    assert(!ms5::resume_stage_area(ram,lookup,d0,d1,d3,error));
    assert(ram == late_bad && d0 == 0x12345678 && d1 == 0x23456789 && d3 == 0x3456789a);
    assert(!ms5::reset_stage_area(ram,d0,d1,d3,error));
    assert(ram == late_bad && d0 == 0x12345678 && d1 == 0x23456789 && d3 == 0x3456789a);
    std::cout << "player_record_capture_test: passed\n";
}
