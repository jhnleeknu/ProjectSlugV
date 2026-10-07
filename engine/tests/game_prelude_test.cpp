#include "ms5/game_prelude.h"
#include <cstdlib>
#include <iostream>
namespace {
void require(bool condition, const char* message) {
    if (!condition) { std::cerr << message << '\n'; std::exit(1); }
}
void put(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
bool same_byte(const ms5::SoundBytePending& a, const ms5::SoundBytePending& b) {
    return a.waiting == b.waiting && a.command == b.command && a.tail == b.tail && a.next == b.next;
}
bool same(const ms5::GamePreludeState& a, const ms5::GamePreludeState& b) {
    return a.next_pc == b.next_pc && a.d0 == b.d0 && a.d1 == b.d1 && a.d3 == b.d3 && a.phase == b.phase &&
        a.word.kind == b.word.kind && a.word.phase == b.word.phase && a.word.low == b.word.low &&
        a.word.cursor == b.word.cursor && same_byte(a.word.byte,b.word.byte) && same_byte(a.byte,b.byte);
}
void fails(std::vector<std::uint8_t>& ram, ms5::GamePreludeState& state) {
    const std::vector<std::uint8_t> before = ram; const ms5::GamePreludeState old = state;
    std::uint8_t reads = 77; std::string error;
    require(!ms5::prepare_game_prelude(ram,0,state,reads,error),"expected failure");
    require(ram == before && same(state,old) && reads == 77 && !error.empty(),"failure rollback");
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::GamePreludeState state; std::string error; std::uint8_t reads = 99;
    state.d0 = 0xffffffffU; state.d1 = 0xabcdffffU; state.d3 = 0x87654321U;
    ram[0xd683] = 7; ram[0xd694] = 8; ram[0xd69c] = 9; ram[0xd686] = 0x65;
    put(ram,0x4d76,127); put(ram,0x4d74,126);
    require(ms5::prepare_game_prelude(ram,0,state,reads,error),"normal prefix");
    require(state.phase == 4 && state.next_pc == 0x475a4 && state.d0 == 0x720 && state.d1 == 0xabcd0001U &&
        state.d3 == 0x87654321U && reads == 0,"completion register carry");
    require(ram[0x4d73] == 8 && ram[0x4cf4] == 0x20 && ram[0x4d77] == 1,"byte queue wrap");
    require(ram[0xd683] == 0 && ram[0xd694] == 0 && ram[0xd69c] == 0 && ram[0xd686] == 0x65 &&
        ram[0xde26] == 0 && ram[0xde27] == 0x0e && ram[0xde28] == 0x89 && ram[0xde29] == 0xe4 &&
        ram[0xde2e] == 255 && ram[0xde2f] == 0,"prefix clears and pointer, bounded suffix");
    fails(ram,state);

    ram.assign(65536,0); state = ms5::GamePreludeState(); state.d1 = 0x12340000; state.d3 = 0xabcdef01;
    put(ram,0x4d8c,6); put(ram,0x4d82,0x0325); put(ram,0x4d74,1);
    ram[0x12] = 1; ram[0xfd82] = 1; ram[0xfd8d] = 1; ram[0x4d7e] = 69;
    require(ms5::prepare_game_prelude(ram,0,state,reads,error),"word overflow");
    require(state.phase == 1 && state.word.phase == 2 && state.word.byte.command == 0x25 &&
        state.d0 == 0x725 && state.d1 == 0x12340001 && reads == 1 && ram[0x4d7b] == 255 && ram[0x4d7e] == 69,"priority and overflow wait");
    ram[0xd683] = 0x55;
    const std::vector<std::uint8_t> waiting = ram; const ms5::GamePreludeState pending = state;
    require(ms5::prepare_game_prelude(ram,255,state,reads,error) && ram == waiting && same(state,pending) && reads == 0,"poll does not replay prefix/status");
    ms5::GamePreludeState bad = state; bad.d1 ^= 1; fails(ram,bad);
    bad = state; bad.word.kind = 2; fails(ram,bad);
    put(ram,0x4d74,2);
    require(ms5::prepare_game_prelude(ram,255,state,reads,error) && state.phase == 2 && state.byte.command == 8 &&
        state.d0 == 0x708 && state.d1 == 0x12340002 && ram[0x4d7e] == 0 && reads == 0,"word resumes into byte8 wait");
    put(ram,0x4d74,3);
    require(ms5::prepare_game_prelude(ram,255,state,reads,error) && state.phase == 3 && state.byte.command == 0x20 &&
        state.d0 == 0x720 && state.d1 == 0x12340003,"byte8 resumes into byte20 wait");
    put(ram,0x4d74,128); fails(ram,state); put(ram,0x4d74,4);
    require(ms5::prepare_game_prelude(ram,255,state,reads,error) && state.phase == 4 && !state.byte.waiting && state.byte.command == 0 &&
        state.d1 == 0x12340003 && state.d3 == 0xabcdef01 && ram[0xd683] == 0x55,"final resume preserves intervening RAM");

    ram.assign(65536,0); state = ms5::GamePreludeState(); put(ram,0x4d74,128); ram[0xd683] = 0x71; fails(ram,state);
    ram.assign(65536,0); state = ms5::GamePreludeState(); state.byte.command = 8; fails(ram,state);
    std::cout << "Game prelude prefix, sound waits, register carry and rollback passed\n";
}
