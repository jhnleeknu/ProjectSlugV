#include "ms5/main_frame.h"
#include <cassert>
#include <iostream>

namespace {
void put(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at + 1] = static_cast<std::uint8_t>(value);
}
bool same_state(const ms5::MainFrameState& a, const ms5::MainFrameState& b) {
    return a.next_pc == b.next_pc && a.object_address == b.object_address && a.d1 == b.d1 && a.d3 == b.d3 &&
           a.sound.kind == b.sound.kind && a.sound.phase == b.sound.phase && a.sound.low == b.sound.low &&
           a.sound.cursor == b.sound.cursor && a.sound.byte.waiting == b.sound.byte.waiting &&
           a.sound.byte.command == b.sound.byte.command && a.sound.byte.tail == b.sound.byte.tail &&
           a.sound.byte.next == b.sound.byte.next && a.sprite.waiting == b.sprite.waiting && a.sprite.cursor == b.sprite.cursor;
}
void fail(std::vector<std::uint8_t>& ram, ms5::MainFrameState& state) {
    const std::vector<std::uint8_t> before = ram;
    const ms5::MainFrameState saved = state;
    const std::vector<ms5::CompositionResource> resources;
    const std::vector<ms5::PaletteRecord> records;
    std::vector<ms5::VideoPortWrite> writes(1);
    writes[0].size = 2; writes[0].address = 123; writes[0].value = 456;
    std::string error;
    assert(!ms5::prepare_main_frame(ram, resources, records, 0, state, writes, error));
    assert(ram == before && same_state(state, saved) && !error.empty());
    assert(writes.size() == 1 && writes[0].size == 2 && writes[0].address == 123 && writes[0].value == 456);
}
}
int main() {
    const std::vector<ms5::CompositionResource> resources;
    const std::vector<ms5::PaletteRecord> records;
    std::vector<std::uint8_t> ram(65536, 0);
    ms5::MainFrameState state;
    state.next_pc = 0xe74; state.d1 = 0x12345678; state.d3 = 0x98765432;
    put(ram, 0x4d82, 0x422); put(ram, 0x4d8c, 2); put(ram, 0x4d76, 127);
    put(ram, 0x8d34, 2); // Consumer will hold the empty prepared ring at cursor0.
    ram[0x7ded] = 128; ram[0x7dd4] = 2; ram[0x7dcf] = 1;
    std::string error;
    std::vector<ms5::VideoPortWrite> writes;
    assert(ms5::prepare_main_frame(ram, resources, records, 0xffff, state, writes, error));
    assert(state.next_pc == 0x3aea && state.sound.kind == 2 && state.sound.byte.waiting);
    assert(writes.size() == 2 && writes[0].size == 2 && writes[0].address == 0x3c0004 && writes[0].value == 0 &&
           writes[1].size == 4 && writes[1].address == 0x3c0000 && writes[1].value == 0x82000000);
    assert((state.d1 & 0xffff0000U) == 0x12340000U && state.d3 == 0x98765432U && ram[0x7dd4] == 2);
    const std::vector<std::uint8_t> sound_wait = ram;
    const ms5::MainFrameState sound_state = state;
    assert(ms5::prepare_main_frame(ram, resources, records, 0xffff, state, writes, error));
    assert(ram == sound_wait && same_state(state, sound_state) && writes.empty());
    put(ram, 0x4d74, 2);
    assert(ms5::prepare_main_frame(ram, resources, records, 0xffff, state, writes, error));
    assert(state.next_pc == 0x16bd0 && state.sound.kind == 0 && state.sprite.waiting && state.sprite.cursor == 0);
    assert(writes.empty() && ram[0x7dd4] == 2 && (state.d1 & 0xffffU) == 2);
    const std::vector<std::uint8_t> sprite_wait = ram;
    const ms5::MainFrameState sprite_state = state;
    assert(ms5::prepare_main_frame(ram, resources, records, 0xffff, state, writes, error));
    assert(ram == sprite_wait && same_state(state, sprite_state) && writes.empty());
    put(ram, 0x8d34, 0);
    assert(ms5::prepare_main_frame(ram, resources, records, 0xffff, state, writes, error));
    assert(state.next_pc == 0xec4 && !state.sprite.waiting && state.sound.kind == 0);
    assert(ram[0x7dd4] == 1 && (ram[0x1b] & 128U) != 0 && ram[0x18] == 255);
    assert(writes.size() == 6 && writes[0].address == 0x2ffff2 && writes[0].value == 0x1000 &&
           writes[1].address == 0x2ffff0 && writes[2].address == 0x2ffff2 && writes[2].value == 0x2000 &&
           writes[3].address == 0x2ffff0 && writes[4].address == 0x2ffff2 && writes[4].value == 0x1000 &&
           writes[5].address == 0x2ffff0);
    fail(ram, state); // ec4 is beyond this prelude; palette timer cannot run twice.

    // Invalid sound ring after the initial video writes rolls back the prefix.
    ram.assign(65536, 0); state = ms5::MainFrameState(); state.next_pc = 0xe74;
    put(ram, 0x4d8c, 3); fail(ram, state);
    put(ram, 0x4d8c, 0); state.sound.kind = 2; fail(ram, state);
    state.sound = ms5::SoundWordPending(); state.next_pc = 0x3aea; fail(ram, state);
    state.next_pc = 0x16bd0; fail(ram, state);
    // Video conversion saturates before subtracting the previous byte, then wraps.
    const unsigned int videos[4] = {0, 0x8000, 0x8080, 0xffff};
    const unsigned int expected[4] = {2, 2, 3, 1};
    for (unsigned int index = 0; index < 4; ++index) {
        ram.assign(65536, 0); ram[0x7ded] = 128; ram[0x18] = 254;
        state = ms5::MainFrameState(); state.next_pc = 0xe74;
        assert(ms5::prepare_main_frame(ram, resources, records, static_cast<std::uint16_t>(videos[index]), state, writes, error));
        assert(state.next_pc == 0xec4 && ram[0x18] == expected[index]);
    }
    std::cout << "Main prelude prefix ordering, sound/sprite resume and rollback passed\n";
}
