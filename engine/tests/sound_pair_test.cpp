#include "ms5/sound_pair.h"
#include <cassert>
#include <iostream>

namespace {
ms5::SoundPairState initial(unsigned int saved = 0x10) {
    ms5::SoundPairState state;
    state.d0 = 0xabcdef00U | saved;
    state.d1 = 0x87654321U;
    state.d3 = 0x12345678U;
    return state;
}
bool same(const ms5::SoundPairState& a, const ms5::SoundPairState& b) {
    return a.entry == b.entry && a.next_pc == b.next_pc && a.d0 == b.d0 &&
        a.d1 == b.d1 && a.d3 == b.d3 && a.phase == b.phase && a.saved == b.saved &&
        a.byte.waiting == b.byte.waiting && a.byte.command == b.byte.command &&
        a.byte.tail == b.byte.tail && a.byte.next == b.byte.next;
}
}
int main() {
    std::string error;
    std::vector<std::uint8_t> ram(65536, 0);
    ms5::SoundPairState state = initial();
    assert(ms5::enqueue_sound_pair(ram, state, error));
    assert(ram[0x4cf4] == 10 && ram[0x4cf5] == 0x30 && ram[0x4d77] == 2);
    assert(state.phase == 3 && state.next_pc == 0x3af6 && state.saved == 0x10);
    assert(state.d0 == 0xabcdef30U && state.d1 == 0x87650002U && state.d3 == 0x12345678U);
    assert(!state.byte.waiting && state.byte.command == 0 && state.byte.tail == 0 && state.byte.next == 0);
    const std::vector<std::uint8_t> done = ram;
    const ms5::SoundPairState completed = state;
    assert(!ms5::enqueue_sound_pair(ram, state, error));
    assert(ram == done && same(state, completed));

    // First wait is repeatable; release publishes the captured slot and may
    // immediately stop in a distinct second wait without repeating the prefix.
    ram.assign(65536, 0);
    ram[0x4d75] = 1;
    state = initial();
    assert(ms5::enqueue_sound_pair(ram, state, error));
    assert(state.phase == 1 && state.byte.tail == 0 && state.byte.next == 1);
    assert(state.d0 == 0xabcdef0aU && state.d1 == 0x87650001U);
    const std::vector<std::uint8_t> waiting_ram = ram;
    const ms5::SoundPairState waiting = state;
    assert(ms5::enqueue_sound_pair(ram, state, error));
    assert(ram == waiting_ram && same(state, waiting));
    ram[0x4d77] = 99;
    ram[0x4d75] = 2;
    assert(ms5::enqueue_sound_pair(ram, state, error));
    assert(state.phase == 2 && state.byte.tail == 1 && state.byte.next == 2);
    assert(ram[0x4cf4] == 10 && ram[0x4d77] == 1 && ram[0x4cf5] == 0);
    const std::vector<std::uint8_t> second_ram = ram;
    const ms5::SoundPairState second = state;
    assert(ms5::enqueue_sound_pair(ram, state, error));
    assert(ram == second_ram && same(state, second));
    ram[0x4d75] = 128;
    const std::vector<std::uint8_t> malformed = ram;
    assert(!ms5::enqueue_sound_pair(ram, state, error));
    assert(ram == malformed && same(state, second));
    ram[0x4d75] = 3;
    ram[0x4d77] = 99;
    assert(ms5::enqueue_sound_pair(ram, state, error));
    assert(state.phase == 3 && ram[0x4cf5] == 0x30 && ram[0x4d77] == 2);

    // Carry makes the second command ff. A full queue after the prefix retains
    // that command and all upper register bits until the second publication.
    ram.assign(65536, 0);
    ram[0x4d75] = 2;
    state = initial(0xe0);
    state.entry = state.next_pc = 0x3d64;
    assert(ms5::enqueue_sound_pair(ram, state, error));
    assert(state.phase == 2 && state.byte.command == 255 && ram[0x4cf4] == 11);
    assert(state.d0 == 0xabcdefffU && state.d1 == 0x87650002U);
    ram[0x4d75] = 3;
    assert(ms5::enqueue_sound_pair(ram, state, error));
    assert(ram[0x4cf5] == 255 && state.d3 == 0x12345678U);

    ram.assign(65536, 0);
    ram[0x4d75] = 126;
    ram[0x4d77] = 127;
    state = initial(0xff);
    assert(ms5::enqueue_sound_pair(ram, state, error));
    assert(state.phase == 3 && ram[0x4d73] == 10 && ram[0x4cf4] == 255);
    assert(state.d1 == 0x87650001U && ram[0x4d77] == 1);

    ram.assign(65536, 0);
    state = initial();
    state.saved = 1;
    const ms5::SoundPairState invalid = state;
    assert(!ms5::enqueue_sound_pair(ram, state, error));
    assert(same(state, invalid) && ram[0x4d77] == 0);
    state = waiting;
    state.byte.next = 2;
    const ms5::SoundPairState invalid_next = state;
    assert(!ms5::enqueue_sound_pair(ram, state, error));
    assert(same(state, invalid_next) && ram[0x4d77] == 0);
    ram.resize(65535);
    state = initial();
    const ms5::SoundPairState wrong_size = state;
    assert(!ms5::enqueue_sound_pair(ram, state, error));
    assert(ram.size() == 65535 && same(state, wrong_size));
    std::cout << "Sound pair register carry, captured-slot waits and rollback passed\n";
}
