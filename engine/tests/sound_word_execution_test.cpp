#include "ms5/sound_word_execution.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& r, unsigned int at, unsigned int v) {
    r[at] = static_cast<std::uint8_t>(v >> 8); r[at + 1] = static_cast<std::uint8_t>(v);
}
unsigned int word(const std::vector<std::uint8_t>& r, unsigned int at) { return (static_cast<unsigned int>(r[at]) << 8) | r[at + 1]; }
ms5::SoundWordExecutionState initial(unsigned int command = 0x0528) {
    ms5::SoundWordExecutionState s;
    for (unsigned int i = 0; i < 8; ++i) s.byte.registers.d[i] = 0xabcd0000U + i;
    for (unsigned int i = 0; i < 5; ++i) s.byte.registers.a[i] = 0x12340000U + i;
    s.byte.registers.d[0] |= command; s.byte.registers.d[1] = 0x87654321U;
    return s;
}
bool same(const ms5::SoundWordExecutionState& a, const ms5::SoundWordExecutionState& b) {
    if (a.phase != b.phase || a.saved_low != b.saved_low || a.byte.waiting != b.byte.waiting) return false;
    for (unsigned int i = 0; i < 8; ++i) if (a.byte.registers.d[i] != b.byte.registers.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.byte.registers.a[i] != b.byte.registers.a[i]) return false;
    return true;
}
void success(std::vector<std::uint8_t>& r, ms5::SoundWordExecutionState& s, unsigned int status = 0, unsigned int expected_reads = 0) {
    std::uint8_t reads = 99; std::string error = "old";
    assert(ms5::execute_sound_word(r, s, static_cast<std::uint8_t>(status), reads, error));
    assert(reads == expected_reads && error.empty());
}
void failure(std::vector<std::uint8_t>& r, ms5::SoundWordExecutionState& s) {
    const std::vector<std::uint8_t> old = r; const ms5::SoundWordExecutionState saved = s;
    std::uint8_t reads = 99; std::string error;
    assert(!ms5::execute_sound_word(r, s, 0, reads, error));
    assert(r == old && same(s, saved) && reads == 99 && !error.empty());
}
void full(std::vector<std::uint8_t>& r, unsigned int discarded) {
    put(r, 0x4d8a, 2); put(r, 0x4d8c, 0);
    put(r, 0x4d84, discarded); put(r, 0x4d86, 0x0629); put(r, 0x4d88, 0x072a);
}
}
int main() {
    // Every early gate keeps A0/A1 and unrelated registers intact.
    const unsigned int commands[] = {0x2000, 0x051f, 0x0128, 0x0228, 0x0328, 0x0028, 0x0528, 0x0528, 0x1028, 0x0028};
    for (unsigned int i = 0; i < 10; ++i) {
        std::vector<std::uint8_t> r(65536, 0); ms5::SoundWordExecutionState s = initial(commands[i]);
        s.saved_low = 12;
        if (i == 5 || i == 6 || i == 7) r[0x12] = 1;
        if (i == 7) { r[0xfd82] = 1; r[0xfd8d] = 1; }
        if (i == 8) r[0x4d7e] = 1;
        if (i == 9) r[0xf001] = 0x20;
        const std::vector<std::uint8_t> old = r;
        success(r, s, 1, i == 7 ? 1 : 0);
        assert(r == old && s.saved_low == 0 && s.phase == 0);
        assert(s.byte.registers.a[0] == 0x12340000 && s.byte.registers.a[1] == 0x12340001);
        assert(s.byte.registers.d[0] == (0xabcd0000U | commands[i]));
        assert(s.byte.registers.d[1] == (i < 2 ? 0x87654321U : (0x87650000U | (commands[i] & 0xff00U))));
        assert(s.byte.registers.d[7] == 0xabcd0007U && s.byte.registers.a[4] == 0x12340004U);
    }
    // External status is sampled only within the mode-1 conditional path.
    for (unsigned int mode = 0; mode < 3; ++mode) for (unsigned int enabled = 0; enabled < 2; ++enabled) for (unsigned int busy = 0; busy < 2; ++busy) {
        std::vector<std::uint8_t> r(65536, 0); ms5::SoundWordExecutionState s = initial();
        r[0x12] = static_cast<std::uint8_t>(mode); r[0xfd82] = static_cast<std::uint8_t>(enabled); r[0xfe80] = static_cast<std::uint8_t>(busy); r[0xfd8d] = 1;
        const bool read = mode == 1 && enabled != 0 && busy == 0;
        success(r, s, 1, read ? 1 : 0);
        assert(word(r, 0x4d8c) == (read ? 0 : 2));
    }
    std::vector<std::uint8_t> r(65536, 0); ms5::SoundWordExecutionState s = initial();
    success(r, s); assert(word(r, 0x4d82) == 0x0528 && word(r, 0x4d8c) == 2);
    assert(s.byte.registers.a[0] == 0x104d82 && s.byte.registers.a[1] == 0x12340001 && s.byte.registers.d[1] == 0x87650002);
    // Duplicate moves forward, while the final queued duplicate returns unchanged.
    r.assign(65536, 0); s = initial(); put(r, 0x4d8c, 4); put(r, 0x4d82, 0x0528); put(r, 0x4d84, 0x0629);
    success(r, s); assert(word(r, 0x4d82) == 0x0629 && word(r, 0x4d84) == 0x0528 && s.byte.registers.a[1] == 0x104d82);
    s = initial(); const std::vector<std::uint8_t> duplicate = r; success(r, s); assert(r == duplicate && s.byte.registers.d[1] == 0x87650004 && s.byte.registers.a[1] == 0x104d84);
    // Initial index may alias the tail: source read precedes live tail overwrite.
    r.assign(65536, 0); s = initial(); put(r, 0x4d8a, 10); put(r, 0x4d8c, 0x0528); put(r, 0x4d86, 0xabcd);
    success(r, s); assert(word(r, 0x4d8c) == 0xabcd && word(r, 0x4d86) == 0x0528 && s.byte.registers.a[1] == 0x104d8c);
    // Full queue discards zero without submitting bytes.
    r.assign(65536, 0); s = initial(); full(r, 0); success(r, s);
    assert(word(r, 0x4d8c) == 2 && word(r, 0x4d8a) == 4 && word(r, 0x4d76) == 0 && s.byte.registers.a[0] == 0x104d84);
    // Both byte waits resume without rescanning gates, queue, or external status.
    r.assign(65536, 0); s = initial(); full(r, 0x082b); put(r, 0x4d74, 1);
    r[0x12] = 1; r[0xfd82] = 1; r[0xfd8d] = 1;
    success(r, s, 0, 1); assert(s.phase == 1 && s.byte.waiting && s.saved_low == 0x2b && s.byte.registers.d[0] == 0xabcd0508);
    assert(s.byte.registers.a[0] == 0x104cf4 && s.byte.registers.a[1] == 0x104d88);
    put(r, 0x4d8c, 0xffff); success(r, s, 1); assert(s.phase == 1);
    put(r, 0x4d74, 2); success(r, s, 1); assert(s.phase == 2 && s.byte.waiting && r[0x4cf4] == 8 && s.byte.registers.d[0] == 0xabcd052b);
    assert(s.byte.registers.a[0] == 0x104cf5 && s.byte.registers.d[1] == 0x87650002);
    put(r, 0x4d74, 3); success(r, s, 1); assert(s.phase == 0 && !s.byte.waiting && s.saved_low == 0 && r[0x4cf5] == 0x2b);
    // Special high byte 3 bypass preserves postincremented A0 until the low call.
    r.assign(65536, 0); s = initial(); full(r, 0x032b); put(r, 0x4d74, 1);
    success(r, s); assert(s.phase == 2 && r[0x4d7b] == 255 && s.saved_low == 0x2b);
    put(r, 0x4d74, 2); success(r, s); assert(s.phase == 0 && r[0x4cf4] == 0x2b);
    r.assign(65536, 0); s = initial(); full(r, 0x0303);
    success(r, s); assert(s.phase == 0 && s.saved_low == 0 && r[0x4d7b] == 255);
    assert(s.byte.registers.a[0] == 0x104d86 && s.byte.registers.d[1] == 0x87650004 && s.byte.registers.d[0] == 0xabcd0503);
    r.assign(65536, 0); s = initial(); full(r, 0x082b);
    success(r, s); assert(s.phase == 0 && r[0x4cf4] == 8 && r[0x4cf5] == 0x2b && word(r, 0x4d76) == 2);
    // Valid negative index can precede the normal ring and advances using &6.
    r.assign(65536, 0); s = initial(); put(r, 0x4d8a, 0xfffe); success(r, s);
    assert(s.byte.registers.a[1] == 0x104d80 && word(r, 0x4d82) == 0x0528);
    r.assign(65536, 0); s = initial(); put(r, 0x4d8a, 0xfffe); put(r, 0x4d8c, 0xfffe); success(r, s);
    assert(word(r, 0x4d80) == 0x0528 && word(r, 0x4d8c) == 0);
    // Signed access below RAM, misalignment, and impossible live tail fail atomically.
    r.assign(65536, 0); s = initial(); put(r, 0x4d8a, 0x8000); failure(r, s);
    r.assign(65536, 0); s = initial(); put(r, 0x4d8a, 1); failure(r, s);
    r.assign(65536, 0); s = initial(); put(r, 0x4d8c, 1); failure(r, s);
    r.assign(65536, 0); s = initial(); put(r, 0x4d8a, 1); put(r, 0x4d8c, 1); failure(r, s);
    // A later byte failure rolls back already performed word and byte writes.
    r.assign(65536, 0); s = initial(); full(r, 0x082b); put(r, 0x4d76, 0x8000); put(r, 0x4d74, 2); r[0x12] = 1; r[0xfd82] = 1; r[0xfd8d] = 1; failure(r, s);
    // High byte 3 writes the special flag successfully before a bad low-byte
    // destination fails. Roll back the flag, word queue, state, and read count.
    r.assign(65536, 0); s = initial(); full(r, 0x032b);
    r[0x4d7b] = 0x42; put(r, 0x4d76, 0x8000); put(r, 0x4d74, 2);
    r[0x12] = 1; r[0xfd82] = 1; r[0xfd8d] = 1; failure(r, s);
    // Releasing either captured submission with an invalid A0 must preserve
    // the exact pending phase and saved byte, rather than commit partial state.
    const std::uint32_t invalid_addresses[] = {0x0fffffU, 0x110000U};
    for (unsigned int phase = 1; phase <= 2; ++phase) {
        for (unsigned int i = 0; i < 2; ++i) {
            r.assign(65536, 0); s = initial(); s.phase = phase;
            s.saved_low = 0x2b; s.byte.waiting = true;
            s.byte.registers.a[0] = invalid_addresses[i];
            s.byte.registers.d[1] = 0x87650002U; put(r, 0x4d74, 3);
            failure(r, s);
        }
    }
    r.assign(65536, 0); s = initial(); s.phase = 1; failure(r, s);
    s = initial(); s.byte.waiting = true; failure(r, s);
    s = initial(); s.phase = 3; s.byte.waiting = true; failure(r, s);
    s = initial(); r.resize(65535); failure(r, s);
    std::cout << "sound_word_execution_test passed\n";
}
