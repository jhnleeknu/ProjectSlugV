#include "ms5/game_restart.h"
#include <cstdlib>
#include <iostream>
namespace {
void require(bool condition, const char* message) {
    if (!condition) { std::cerr << message << '\n'; std::exit(1); }
}
void put(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 24); ram[at + 1] = static_cast<std::uint8_t>(value >> 16);
    ram[at + 2] = static_cast<std::uint8_t>(value >> 8); ram[at + 3] = static_cast<std::uint8_t>(value);
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) | (static_cast<std::uint32_t>(ram[at + 1]) << 16) |
        (static_cast<std::uint32_t>(ram[at + 2]) << 8) | ram[at + 3];
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0); put(ram,0x820,0xc610); put(ram,0x824,0x100820); put(ram,0x828,0x100820);
    put(ram,0xcb8,0x270e); put(ram,0xda8,0x270e); return ram;
}
ms5::FixedDataResource records() {
    ms5::FixedDataResource result; result.source_cpu_address = result.source_rom_offset = 0x4cf64;
    result.data.assign(320,0); result.data[1] = 0x42; result.data[2] = 0x53; return result;
}
ms5::FixedDataResource streams() {
    ms5::FixedDataResource result; result.source_cpu_address = result.source_rom_offset = 0xf01fe;
    result.data.assign(0x1810,0); put(result.data,0xc00,0xf0200); put(result.data,0xc04,0xf0800);
    put(result.data,0x1808,0xf1000); put(result.data,0x180c,0xf1400); return result;
}
ms5::GameRestartState state() {
    ms5::GameRestartState result; result.a6 = 0x100820;
    result.initialization.prelude.d0 = 0xabcdef01; result.initialization.prelude.d1 = 0x12345678;
    result.initialization.prelude.d3 = 0x87654321; return result;
}
bool same_byte(const ms5::SoundBytePending& a, const ms5::SoundBytePending& b) {
    return a.waiting == b.waiting && a.command == b.command && a.tail == b.tail && a.next == b.next;
}
bool same(const ms5::GameRestartState& a, const ms5::GameRestartState& b) {
    const ms5::GamePreludeState& x = a.initialization.prelude; const ms5::GamePreludeState& y = b.initialization.prelude;
    return a.phase == b.phase && a.a6 == b.a6 && a.initialization.returned == b.initialization.returned &&
        x.phase == y.phase && x.next_pc == y.next_pc && x.d0 == y.d0 && x.d1 == y.d1 && x.d3 == y.d3 &&
        x.word.kind == y.word.kind && x.word.phase == y.word.phase && x.word.low == y.word.low &&
        x.word.cursor == y.word.cursor && same_byte(x.word.byte,y.word.byte) && same_byte(x.byte,y.byte);
}
void fails(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& table, const ms5::FixedDataResource& input,
           ms5::GameRestartState& value) {
    const std::vector<std::uint8_t> before = ram; const ms5::GameRestartState old = value;
    std::vector<ms5::VideoPortWrite> ports(1); ports[0].value = 0x4321; std::uint8_t reads = 77; std::string error;
    require(!ms5::restart_game(ram,table,input,0,value,reads,ports,error),"expected restart failure");
    require(ram == before && same(value,old) && reads == 77 && ports.size() == 1 && ports[0].value == 0x4321 && !error.empty(),"whole restart rollback");
}
}
int main() {
    const ms5::FixedDataResource table = records(), input = streams(), absent;
    std::vector<std::uint8_t> ram = fixture(); ms5::GameRestartState value = state();
    std::vector<ms5::VideoPortWrite> ports; std::uint8_t reads = 77; std::string error;
    fails(ram,table,absent,value); // Successful full 47570 followed by late input failure must roll back the screen/seed too.
    require(ms5::restart_game(ram,table,input,0,value,reads,ports,error),"complete restart");
    require(value.phase == 2 && value.initialization.returned && value.initialization.prelude.next_pc == 0x475a4 &&
        value.initialization.prelude.d0 == 0 && value.initialization.prelude.d1 == 0 && value.initialization.prelude.d3 == 0 &&
        value.a6 == 0x100820 && get(ram,0x820) == 0xc654 && ports.size() == 2072 && reads == 0,"return boundary and callback");
    require(ram[0xf02a] == 0 && ram[0xf02b] == 1 && ram[0xd680] == 7 && ram[0x4cd4] == 1 &&
        get(ram,0x4cc4) == 0xf0800 && get(ram,0x4cc8) == 0xf1400,"stage7 and input selector1");
    fails(ram,table,input,value);
    ram = fixture(); ram[0x4d75] = 1; value = state();
    require(ms5::restart_game(ram,absent,absent,0,value,reads,ports,error) && value.phase == 1 &&
        value.initialization.prelude.phase == 2 && !value.initialization.returned && ports.size() == 2072,"first wait returns initial screen ports");
    ram[0x966] = 0x55; ram[0xf02b] = 0; ram[0xd6b4] = 0x69;
    const std::vector<std::uint8_t> waited = ram; const ms5::GameRestartState pending = value;
    require(ms5::restart_game(ram,absent,absent,255,value,reads,ports,error) && ram == waited && same(value,pending) &&
        ports.empty() && reads == 0,"repoll does not seed/remove/screen/read status");
    ram[0x4d75] = 0; fails(ram,table,absent,value);
    require(ms5::restart_game(ram,table,input,255,value,reads,ports,error) && value.phase == 2 && ports.empty() && reads == 0 &&
        ram[0x966] == 0x55 && ram[0xd6b4] == 0x69 && ram[0xd680] == 6 && get(ram,0x4cc4) == 0xf0200 &&
        get(ram,0x4cc8) == 0xf1000,"resume uses live selector0 without replaying prefix");
    ram = fixture(); value = state(); value.initialization.prelude.byte.command = 8; fails(ram,table,input,value);
    value = state(); value.phase = 1; fails(ram,table,input,value);
    value = state(); value.a6 = 0x100821; fails(ram,table,input,value);
    value = state(); put(ram,0x828,0); fails(ram,table,input,value);
    std::cout << "Game restart seed/removal/screen suspension and transactional completion passed\n";
}
