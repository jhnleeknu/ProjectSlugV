#include "ms5/sound_pair.h"
#include <new>
namespace ms5 {
namespace {
bool valid(const SoundPairState& state) {
    if (state.entry != 0x3d58 && state.entry != 0x3d64) return false;
    if (state.phase == 0) return state.next_pc == state.entry && state.saved == 0 && !state.byte.waiting &&
        state.byte.command == 0 && state.byte.tail == 0 && state.byte.next == 0;
    if ((state.phase != 1 && state.phase != 2) || state.next_pc != 0x3aea || !state.byte.waiting ||
        state.byte.tail >= 128 || state.byte.next != ((state.byte.tail + 1U) & 127U)) return false;
    const unsigned int command = state.phase == 1 ? (state.entry == 0x3d58 ? 10U : 11U)
        : (state.saved >= 0xe0 ? 255U : state.saved + 0x20U);
    return state.byte.command == command && (state.d0 & 255U) == command && (state.d1 & 65535U) == state.byte.next;
}
void capture(SoundPairState& state) {
    state.d1 = (state.d1 & 0xffff0000U) | state.byte.next;
    state.next_pc = 0x3aea;
}
bool second(std::vector<std::uint8_t>& ram, SoundPairState& state, std::string& error) {
    const bool carry = state.saved >= 0xe0;
    state.d0 = (state.d0 & 0xffffff00U) | static_cast<std::uint8_t>(state.saved + 0x20U);
    state.d1 = (state.d1 & 0xffffff00U) | (carry ? 255U : 0U);
    state.d0 |= state.d1 & 65535U;
    if (!enqueue_sound_byte(ram,static_cast<std::uint8_t>(state.d0),state.byte,error)) return false;
    capture(state); state.phase = 2;
    return true;
}
}
bool enqueue_sound_pair(std::vector<std::uint8_t>& ram, SoundPairState& state, std::string& error) {
    if (ram.size() != 65536 || !valid(state)) { error = "invalid sound pair RAM or continuation"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SoundPairState next = state;
        if (next.phase == 0) {
            next.saved = static_cast<std::uint8_t>(next.d0);
            next.d0 = (next.d0 & 0xffffff00U) | (next.entry == 0x3d58 ? 10U : 11U);
            if (!enqueue_sound_byte(candidate,static_cast<std::uint8_t>(next.d0),next.byte,error)) return false;
            capture(next); next.phase = 1;
        } else {
            if (!resume_sound_byte(candidate,next.byte,error)) return false;
            capture(next);
        }
        if (!next.byte.waiting && next.phase == 1 && !second(candidate,next,error)) return false;
        if (!next.byte.waiting && next.phase == 2) {
            next.phase = 3; next.next_pc = 0x3af6; next.byte = SoundBytePending();
        }
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate sound pair transaction"; return false; }
}
}
