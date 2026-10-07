#include "ms5/game_ready.h"
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
    std::vector<std::uint8_t> ram(65536,0); put(ram,0x820,0xc654); put(ram,0x824,0x100820); put(ram,0x828,0x100820);
    put(ram,0xb30,0x270e); ram[0xb9c] = 255; put(ram,0x4c9c,0x100200); put(ram,0x208,0x100300); ram[0x4ca1] = 2;
    return ram;
}
ms5::GameReadyState state(unsigned int pc) {
    ms5::GameReadyState result; result.next_pc = pc; result.d0 = 0xabcdef34; result.d1 = 0x12345678;
    result.d3 = 0x87654321; result.a6 = 0x100820; return result;
}
void fails(std::vector<std::uint8_t>& ram, ms5::GameReadyState& value) {
    const std::vector<std::uint8_t> before = ram; const ms5::GameReadyState old = value; std::string error;
    std::vector<ms5::VideoPortWrite> ports(1); ports[0].value = 0x9876;
    require(!ms5::step_game_ready(ram,value,ports,error),"expected ready failure");
    require(ram == before && value.next_pc == old.next_pc && value.d0 == old.d0 && value.d1 == old.d1 && value.d3 == old.d3 &&
        value.a6 == old.a6 && ports.size() == 1 && ports[0].value == 0x9876 && !error.empty(),"ready whole transaction rollback");
}
}
int main() {
    std::vector<std::uint8_t> ram = fixture(); ms5::GameReadyState value = state(0xc654);
    std::vector<ms5::VideoPortWrite> ports; std::string error;
    ram[0x4cd4] = 1;
    require(ms5::step_game_ready(ram,value,ports,error),"static start and replay gate");
    require(value.next_pc == 0xc724 && value.d0 == 0 && value.d1 == 0xffffffffU && value.d3 == 0x87654321 && value.a6 == 0x100820 &&
        get(ram,0xb30) == 0x477e4 && get(ram,0x820) == 0xc66a && ports.size() == 1 && ports[0].value == 0x34,"same-call gate and static restart register outputs");
    for (unsigned int callback = 0; callback < 2; ++callback) {
        for (unsigned int mode = 0; mode < 3; ++mode) {
            ram = fixture(); value = state(0xc66a); ram[0x4cd4] = static_cast<std::uint8_t>(mode);
            put(ram,0xb30,callback == 0 ? 0x270e : 0);
            require(ms5::step_game_ready(ram,value,ports,error),"callback/replay gate combinations");
            if (callback == 1 && mode == 1) {
                require(value.next_pc == 0xc724 && value.d0 == 0xabcdef34 && value.d1 == 0x12345678 &&
                    value.d3 == 0x87654321 && ports.empty(),"zero callback active gate preserves regs");
            } else {
                require(value.next_pc == 0xc73e && value.d0 == 0x75800001 && value.d1 == 0x7000 && value.d3 == 32 &&
                    ports.size() == 2072 && get(ram,0x200) == 0xe66aa && get(ram,0x820) == 0xc6c0 && ram[0x965] == 255 && ram[0x882] == 0,"cleanup/screen/allocator fallthrough");
            }
        }
    }
    ram = fixture(); value = state(0xc654); ram[0x4ca1] = 0;
    require(ms5::step_game_ready(ram,value,ports,error) && value.next_pc == 0xc73e && value.d0 == 0x75800000 &&
        ports.size() == 2073 && get(ram,0x200) == 0 && get(ram,0x820) == 0xc6c0 && ram[0x882] == 0,"normal allocation failure carry ignored");
    for (unsigned int flag = 0; flag < 2; ++flag) {
        ram = fixture(); value = state(0xc6c0); ram[0x882] = static_cast<std::uint8_t>(flag); const std::vector<std::uint8_t> before = ram;
        require(ms5::step_game_ready(ram,value,ports,error) && value.next_pc == (flag == 0 ? 0xc73eU : 0xc00444U) &&
            ram == before && value.d0 == 0xabcdef34 && value.d1 == 0x12345678 && value.d3 == 0x87654321 && ports.empty(),"c6c0 actual boundary without BIOS execution");
    }
    ram = fixture(); value = state(0xc654); put(ram,0x4c9c,0); fails(ram,value);
    ram = fixture(); value = state(0xc654); ram[0xb9c] = 8; fails(ram,value);
    ram = fixture(); value = state(0xc654); ram[0xb41] = 1; fails(ram,value);
    ram = fixture(); value = state(0xc686); put(ram,0x828,0); fails(ram,value);
    ram = fixture(); value = state(0xc724); fails(ram,value);
    value = state(0xc654); value.a6 = 0x100821; fails(ram,value);
    ram.resize(65535); value = state(0xc654); fails(ram,value);
    std::cout << "Game ready gates, fallthrough, boundaries and transactional rollback passed\n";
}
