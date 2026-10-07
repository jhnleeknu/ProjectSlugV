#include "ms5/player_record_capture.h"
#include "ms5/game_initialization.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram,at)) << 16) | word(ram,at + 2);
}
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
}
bool read_player_record(const std::vector<std::uint8_t>& ram, const FixedDataResource& lookup,
                        PlayerRecordState& state, std::string& error) {
    if (ram.size() != 65536) { error = "player record read requires exactly64KiB RAM"; return false; }
    PlayerRecordState next = state;
    const bool second = (next.d0 & 255U) != 0;
    const std::size_t object = second ? 0xda8 : 0xcb8;
    const std::size_t source = second ? 0xdce6 : 0xdcba;
    if (longword(ram,object) == 0x270e || word(ram,source) == 0) {
        next.d0 &= 0xffff0000U; next.d1 = next.d2 = next.d3 = next.d4 = next.d6 = 0; next.d5 = 0xffffffffU;
    } else {
        const std::uint8_t index = ram[source + 0x27];
        if (index == 0) { error = "player record zero-index native TRAP unsupported"; return false; }
        if (lookup.source_cpu_address != 0x4cf64 || lookup.source_rom_offset != 0x4cf64 || lookup.data.size() != 4092) {
            error = "player record lookup requires exact4cf64/4092-byte window"; return false;
        }
        next.d0 = index;
        next.d1 = (next.d1 & 0xffffff00U) | ram[source + 0x25];
        next.d2 = (next.d2 & 0xffffff00U) | ram[source + 0x26];
        next.d3 = (next.d3 & 0xffff0000U) | word(ram,source + 0x1c);
        next.d5 = (next.d5 & 0xffff0000U) | word(ram,source + 0x20);
        next.d6 = (next.d6 & 0xffffff00U) | ram[source + 0x2a];
        next.d4 = word(lookup.data,index*16U + 0x0a);
    }
    state = next; error.clear(); return true;
}
bool capture_player_record(std::vector<std::uint8_t>& ram, const FixedDataResource& lookup,
                           PlayerRecordState& state, std::string& error) {
    if (ram.size() != 65536) { error = "player record capture requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; PlayerRecordState next = state;
        next.d0 = (next.d0 & 0xffff0000U) | (next.d0 & 1U);
        const std::size_t destination = (next.d0 & 65535U) == 0 ? 0xd694 : 0xd69c;
        if (!read_player_record(candidate,lookup,next,error)) return false;
        candidate[destination] = static_cast<std::uint8_t>(next.d0);
        candidate[destination + 3] = static_cast<std::uint8_t>(next.d1);
        candidate[destination + 2] = static_cast<std::uint8_t>(next.d2);
        put_word(candidate,destination + 4,static_cast<std::uint16_t>(next.d3));
        put_word(candidate,destination + 6,static_cast<std::uint16_t>(next.d5));
        candidate[destination + 1] = static_cast<std::uint8_t>(next.d6);
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate player record capture transaction"; return false; }
}
bool resume_stage_area(std::vector<std::uint8_t>& ram, const FixedDataResource& lookup,
                       std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3, std::string& error) {
    if (ram.size() != 65536) { error = "stage area resume requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; PlayerRecordState next; next.d1 = d1; next.d3 = d3;
        if (!capture_player_record(candidate,lookup,next,error)) return false;
        next.d0 = 1;
        if (!capture_player_record(candidate,lookup,next,error)) return false;
        if (!reset_stage_area(candidate,next.d0,next.d1,next.d3,error)) return false;
        ram.swap(candidate); d0 = next.d0; d1 = next.d1; d3 = next.d3; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage area resume transaction"; return false; }
}
}
