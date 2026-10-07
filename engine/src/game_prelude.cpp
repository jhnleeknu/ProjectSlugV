#include "ms5/game_prelude.h"
#include <new>
namespace ms5 {
namespace {
bool empty_byte(const SoundBytePending& byte) {
    return !byte.waiting && byte.command == 0 && byte.tail == 0 && byte.next == 0;
}
bool empty_word(const SoundWordPending& word) {
    return word.kind == 0 && word.phase == 0 && word.low == 0 && word.cursor == 0 && empty_byte(word.byte);
}
bool valid_state(const GamePreludeState& state) {
    if (state.phase == 0) return state.next_pc == 0x47570 && empty_word(state.word) && empty_byte(state.byte);
    if (state.next_pc != 0x3aea || state.phase > 3) return false;
    const SoundBytePending& byte = state.phase == 1 ? state.word.byte : state.byte;
    if (!byte.waiting || byte.command == 3 || byte.tail >= 128 || byte.next != ((byte.tail + 1U) & 127U) ||
        (state.d1 & 65535U) != byte.next) return false;
    if (state.phase == 1) return empty_byte(state.byte) && state.word.kind == 1 &&
        (state.word.phase == 1 || state.word.phase == 2) && state.word.cursor == 0 &&
        (state.word.phase != 2 || byte.command == state.word.low) && state.d0 == (0x700U | byte.command);
    return empty_word(state.word) && byte.command == (state.phase == 2 ? 8 : 0x20) && state.d0 == (0x700U | byte.command);
}
void capture(GamePreludeState& state, const SoundBytePending& byte) {
    state.d0 = 0x700U | byte.command;
    state.d1 = (state.d1 & 0xffff0000U) | byte.next;
    state.next_pc = 0x3aea;
}
bool run(std::vector<std::uint8_t>& ram, std::uint8_t external, GamePreludeState& state,
         std::uint8_t& reads, std::string& error) {
    if (state.phase == 0) {
        ram[0xd683] = 0; ram[0xd694] = 0; ram[0xd69c] = 0;
        ram[0x000e] = 0; ram[0x000f] = 0; ram[0x089e] = 0; ram[0x089f] = 0;
        for (unsigned int byte = 0; byte < 4; ++byte) { ram[0xde14 + byte] = 0; ram[0xde1c + byte] = 0; }
        ram[0xd680] = 0; ram[0xd681] = 0;
        ram[0xde26] = 0; ram[0xde27] = 0x0e; ram[0xde28] = 0x89; ram[0xde29] = 0xe4;
        ram[0xde2e] = 255; ram[0xde2f] = 0;
        state.d0 = 0x720;
        if (ram[0x12] == 1 && ram[0xfd82] != 0 && ram[0xfe80] == 0) reads = 1;
        if (!enqueue_sound_word(ram,0x720,external,state.word,error)) return false;
        if (state.word.kind != 0) { state.phase = 1; capture(state,state.word.byte); return true; }
    } else if (state.phase == 1) {
        if (!resume_sound_word(ram,state.word,error)) return false;
        if (state.word.kind != 0) { capture(state,state.word.byte); return true; }
    } else {
        if (!resume_sound_byte(ram,state.byte,error)) return false;
        capture(state,state.byte);
        if (state.byte.waiting) return true;
        if (state.phase == 3) { state.phase = 4; state.next_pc = 0x475a4; state.byte = SoundBytePending(); return true; }
    }
    if (state.phase <= 1) {
        ram[0x4d7e] = 0;
        if (!enqueue_sound_byte(ram,8,state.byte,error)) return false;
        state.phase = 2; capture(state,state.byte);
        if (state.byte.waiting) return true;
    }
    if (!enqueue_sound_byte(ram,0x20,state.byte,error)) return false;
    state.phase = 3; capture(state,state.byte);
    if (!state.byte.waiting) { state.phase = 4; state.next_pc = 0x475a4; state.byte = SoundBytePending(); }
    return true;
}
}
bool prepare_game_prelude(std::vector<std::uint8_t>& ram, std::uint8_t external,
                          GamePreludeState& state, std::uint8_t& reads, std::string& error) {
    if (ram.size() != 65536 || !valid_state(state)) { error = "invalid game prelude RAM or continuation"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; GamePreludeState next = state; std::uint8_t next_reads = 0;
        if (!run(candidate,external,next,next_reads,error)) return false;
        ram.swap(candidate); state = next; reads = next_reads; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate game prelude transaction"; return false; }
}
}
