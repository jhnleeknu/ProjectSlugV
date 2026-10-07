#include "ms5/game_objects.h"
#include <cstdlib>
#include <iostream>
namespace {
void require(bool condition, const char* message) {
    if (!condition) { std::cerr << message << '\n'; std::exit(1); }
}
void put(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void put_long(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t value) {
    put(ram,at,value >> 16); put(ram,at + 2,value);
}
std::uint32_t get_long(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) | (static_cast<std::uint32_t>(ram[at + 1]) << 16) |
        (static_cast<std::uint32_t>(ram[at + 2]) << 8) | ram[at + 3];
}
void fails(std::vector<std::uint8_t>& ram, std::uint32_t entry, std::uint32_t& d0) {
    const std::vector<std::uint8_t> before = ram; const std::uint32_t old = d0; std::string error;
    require(!ms5::reset_game_objects(ram,entry,d0,error),"expected reset failure");
    require(ram == before && d0 == old && !error.empty(),"object reset failure rollback");
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0xa5); std::string error; std::uint32_t d0 = 0xabcd1234;
    put_long(ram,0xcb8,0x270e); put_long(ram,0xda8,0x270e);
    const std::vector<std::uint8_t> inactive = ram;
    require(ms5::reset_game_objects(ram,0x1bcfe,d0,error) && d0 == 0xabcd1234,"inactive preserves full D0");
    for (unsigned int at = 0; at < 65536; ++at) {
        require(ram[at] == ((at >= 0xd474 && at < 0xd47a) ? 0 : inactive[at]),"inactive changes only shared clears");
    }
    // Zero callback is active; selector 2 stores the nonzero pointer but uses even parity for 1be84.
    ram = inactive; put_long(ram,0xcb8,0); put(ram,0xcb8 + 0x78,2);
    require(ms5::reset_game_objects(ram,0x1bcfe,d0,error),"even nonzero selector");
    require(d0 == 0xabcd0002 && get_long(ram,0xcb8) == 0x1d1f4 && get_long(ram,0xcb8 + 0x8c) == 0x10d460,"active callback, raw selector and pointer");
    require(ram[0xd450] == 0 && ram[0xd458] == 0 && ram[0xd459] == 0 && ram[0xd460] == 0xa5 &&
        ram[0xd468] == 0xa5 && ram[0xd469] == 0xa5,"nonzero even parity differs from pointer");
    require(ram[0xd461] == 0 && ram[0xd462] == 0 && ram[0xd463] == 255 && ram[0xd466] == 1 && ram[0xd467] == 10 &&
        ram[0xd46a] == 0 && ram[0xd46b] == 0 && ram[0xd46c] == 255 && ram[0xd46d] == 255 && ram[0xd48f] == 0 && ram[0xd487] == 0xa5,"chosen buffer fields");
    require(ram[0xcb8 + 0x15] == 0 && ram[0xcb8 + 0x61] == 128 && ram[0xcb8 + 0xa8] == 0xb5 &&
        ram[0xcb8 + 0x9e] == 0 && ram[0xcb8 + 0xa1] == 0 && ram[0xcb8 + 0x81] == 0 && ram[0xcb8 + 0x82] == 0,"object flag operations");
    // Entry 1bd12 uses each live pointer and skips the first-entry field clears.
    ram = inactive; put_long(ram,0xcb8,0x1234); put_long(ram,0xcb8 + 0x8c,0x10e100); put(ram,0xcb8 + 0x78,0);
    put_long(ram,0xda8,0x5678); put_long(ram,0xda8 + 0x8c,0x10e200); put(ram,0xda8 + 0x78,7);
    require(ms5::reset_game_objects(ram,0x1bd12,d0,error) && d0 == 0xabcd0007,"last active selector wins");
    require(ram[0xe101] == 0 && ram[0xe102] == 0 && ram[0xe10a] == 0 && ram[0xe10b] == 0 &&
        ram[0xe201] == 0 && ram[0xe202] == 0 && ram[0xe20a] == 0 && ram[0xe20b] == 0 &&
        ram[0xcb8 + 0x9e] == 0xa5 && get_long(ram,0xcb8 + 0x8c) == 0x10e100,"live pointers and entry distinction");
    put_long(ram,0xda8 + 0x8c,0x10fff6); fails(ram,0x1bd12,d0);
    put_long(ram,0xda8 + 0x8c,0x10e201); fails(ram,0x1bd12,d0);
    fails(ram,0x1bd2e,d0); ram.resize(65535); fails(ram,0x1bcfe,d0);
    std::cout << "Game object resets, parity, live pointers and rollback passed\n";
}
