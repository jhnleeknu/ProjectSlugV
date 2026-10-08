#include "ms5/sound_cancel_execution.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at + 1] = static_cast<std::uint8_t>(value);
}
unsigned int word(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return (static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1];
}
bool same(const ms5::SoundCancelExecutionState& a, const ms5::SoundCancelExecutionState& b) {
    if (a.phase != b.phase || a.saved_word != b.saved_word || a.byte.waiting != b.byte.waiting) return false;
    for (unsigned int i = 0; i < 8; ++i)
        if (a.byte.registers.d[i] != b.byte.registers.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i)
        if (a.byte.registers.a[i] != b.byte.registers.a[i]) return false;
    return true;
}
void rejects(std::vector<std::uint8_t>& ram, ms5::SoundCancelExecutionState& state) {
    const std::vector<std::uint8_t> before = ram;
    const ms5::SoundCancelExecutionState saved = state;
    std::string error;
    assert(!ms5::execute_sound_cancel(ram, state, error));
    assert(!error.empty() && ram == before && same(state, saved));
}
ms5::SoundCancelExecutionState initial(unsigned int command) {
    ms5::SoundCancelExecutionState s;
    for (unsigned int i = 0; i < 8; ++i) s.byte.registers.d[i] = 0xaabb1000U + i;
    for (unsigned int i = 0; i < 5; ++i) s.byte.registers.a[i] = 0xcccc2000U + i;
    s.byte.registers.d[0] = 0x98760000U | command;
    return s;
}
}
int main() {
    std::string error;
    // Each submission waits separately. Resumption retains the saved command
    // and must not scan a newly inserted matching queue entry.
    std::vector<std::uint8_t> ram(65536, 0);
    ms5::SoundCancelExecutionState s = initial(0x1d28);
    put(ram, 0x4d82, 0x1d28); put(ram, 0x4d8c, 2); put(ram, 0x4d74, 1);
    assert(ms5::execute_sound_cancel(ram, s, error));
    assert(error.empty() && s.phase == 1 && s.byte.waiting && s.saved_word == 0x1d28);
    assert(word(ram, 0x4d82) == 0 && s.byte.registers.a[1] == 0x104d82);
    put(ram, 0x4d82, 0x1d28); put(ram, 0x4d8a, 1); // Odd new head must be ignored.
    put(ram, 0x4d74, 2);
    assert(ms5::execute_sound_cancel(ram, s, error));
    assert(s.phase == 2 && s.byte.waiting && s.saved_word == 0x1d28);
    assert(ram[0x4cf4] == 0x14 && s.byte.registers.d[0] == 0x1d);
    put(ram, 0x4d74, 3);
    assert(ms5::execute_sound_cancel(ram, s, error));
    assert(s.phase == 3 && s.byte.waiting && s.saved_word == 0x1d28);
    assert(ram[0x4cf5] == 0x1d && s.byte.registers.d[0] == 0x1d28);
    put(ram, 0x4d74, 4);
    assert(ms5::execute_sound_cancel(ram, s, error));
    assert(s.phase == 0 && !s.byte.waiting && s.saved_word == 0);
    assert(ram[0x4cf6] == 0x28 && word(ram, 0x4d76) == 3 && word(ram, 0x4d82) == 0x1d28);
    assert(s.byte.registers.d[1] == 0xaabb0003U && s.byte.registers.a[1] == 0x104d82);
    for (unsigned int i = 2; i < 8; ++i) assert(s.byte.registers.d[i] == 0xaabb1000U + i);
    for (unsigned int i = 2; i < 5; ++i) assert(s.byte.registers.a[i] == 0xcccc2000U + i);
    // High command byte 3 bypasses the byte ring for the second submission.
    ram.assign(65536, 0); s = initial(0x0328); put(ram, 0x4d74, 3);
    assert(ms5::execute_sound_cancel(ram, s, error));
    assert(s.phase == 0 && ram[0x4d7b] == 255 && word(ram, 0x4d76) == 2);
    assert(ram[0x4cf4] == 0x14 && ram[0x4cf5] == 0x28 && s.byte.registers.d[0] == 0x0328);
    assert(s.byte.registers.a[1] == 0xcccc2001U); // Empty scan preserves A1.
    // A negative initial index can address any aligned actual RAM word.
    ram.assign(65536, 0); s = initial(0x1d28);
    put(ram, 0x4d8a, 0xfffe); put(ram, 0x4d80, 0x1d28);
    assert(ms5::execute_sound_cancel(ram, s, error));
    assert(word(ram, 0x4d80) == 0 && s.byte.registers.a[1] == 0x104d80);
    // Initial index aliases live tail: clearing it changes loop termination.
    ram.assign(65536, 0); s = initial(6);
    put(ram, 0x4d8a, 10); put(ram, 0x4d8c, 6); put(ram, 0x4d86, 6); put(ram, 0x4d88, 6);
    assert(ms5::execute_sound_cancel(ram, s, error));
    assert(word(ram, 0x4d8c) == 0 && word(ram, 0x4d86) == 0 && word(ram, 0x4d88) == 0);
    assert(s.byte.registers.a[1] == 0x104d88);
    // Odd and out-of-RAM signed indices reject transactionally.
    ram.assign(65536, 0); s = initial(0x1d28); put(ram, 0x4d8a, 0xffff); rejects(ram, s);
    put(ram, 0x4d8a, 0x8000); rejects(ram, s);
    // An unreachable tail produces a cycle even after modifying a match.
    ram.assign(65536, 0); s = initial(0x1d28);
    put(ram, 0x4d8c, 1); put(ram, 0x4d82, 0x1d28); rejects(ram, s);
    // A byte write failure after a successful scan rolls back its cleared word.
    ram.assign(65536, 0); s = initial(0x1d28);
    put(ram, 0x4d8c, 2); put(ram, 0x4d82, 0x1d28); put(ram, 0x4d76, 0x8000);
    rejects(ram, s);
    // The same invalid destination may pend, then fail on release; preserve
    // exactly the state at the start of the failing continuation.
    put(ram, 0x4d74, 1); assert(ms5::execute_sound_cancel(ram, s, error));
    assert(s.phase == 1 && s.byte.waiting && word(ram, 0x4d82) == 0);
    put(ram, 0x4d74, 2); rejects(ram, s);
    ram.assign(65536, 0); s = initial(0x1d28);
    s.byte.waiting = true; rejects(ram, s);
    s.byte.waiting = false; s.phase = 1; rejects(ram, s);
    s.phase = 4; s.byte.waiting = true; rejects(ram, s);
    s = initial(0x1d28); ram.resize(65535); rejects(ram, s);
    std::cout << "sound_cancel_execution_test passed\n";
}
