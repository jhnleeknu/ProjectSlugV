#include "ms5/stage_sound_frame.h"
#include "ms5/sound_word_execution.h"
#include "ms5/sound_cancel_execution.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& r, unsigned int at, unsigned int v) {
    r[at] = static_cast<std::uint8_t>(v >> 8); r[at + 1] = static_cast<std::uint8_t>(v);
}
unsigned int word(const std::vector<std::uint8_t>& r, unsigned int at) {
    return (static_cast<unsigned int>(r[at]) << 8) | r[at + 1];
}
ms5::StageSoundFrameState initial() {
    ms5::StageSoundFrameState s;
    for (unsigned int i = 0; i < 8; ++i) s.byte.registers.d[i] = 0xabcdf180U + i;
    for (unsigned int i = 0; i < 5; ++i) s.byte.registers.a[i] = 0x76543210U + i;
    return s;
}
bool same_byte(const ms5::SoundByteExecutionState& a, const ms5::SoundByteExecutionState& b) {
    if (a.waiting != b.waiting) return false;
    for (unsigned int i = 0; i < 8; ++i) if (a.registers.d[i] != b.registers.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.registers.a[i] != b.registers.a[i]) return false;
    return true;
}
bool same(const ms5::StageSoundFrameState& a, const ms5::StageSoundFrameState& b) {
    return a.kind == b.kind && a.phase == b.phase && a.saved == b.saved && same_byte(a.byte, b.byte);
}
void success(std::vector<std::uint8_t>& r, ms5::StageSoundFrameState& s, unsigned int external = 0, unsigned int expected_reads = 0) {
    std::uint8_t reads = 99; std::string error = "old";
    assert(ms5::step_stage_sound_frame(r, s, static_cast<std::uint8_t>(external), reads, error));
    assert(reads == expected_reads && error.empty());
}
void failure(std::vector<std::uint8_t>& r, ms5::StageSoundFrameState& s) {
    const std::vector<std::uint8_t> old = r; const ms5::StageSoundFrameState saved = s;
    std::uint8_t reads = 99; std::string error;
    assert(!ms5::step_stage_sound_frame(r, s, 0, reads, error));
    assert(r == old && same(s, saved) && reads == 99 && !error.empty());
}
void full(std::vector<std::uint8_t>& r) {
    put(r, 0x4d8a, 2); put(r, 0x4d8c, 0);
    put(r, 0x4d84, 0x082b); put(r, 0x4d86, 0x0629); put(r, 0x4d88, 0x072a);
}
}
int main() {
    // All transition pairs, including noncanonical previous nonzero bytes,
    // preserve the original MOVE.B widths before dispatching the helper.
    const unsigned int values[] = {0, 1, 255};
    for (unsigned int i = 0; i < 3; ++i) for (unsigned int j = 0; j < 3; ++j) {
        std::vector<std::uint8_t> r(65536, 0); ms5::StageSoundFrameState s = initial();
        r[0xd490] = static_cast<std::uint8_t>(values[i]); r[0xd491] = static_cast<std::uint8_t>(values[j]);
        std::vector<std::uint8_t> expected = r; ms5::StageSoundFrameState e = s;
        e.byte.registers.d[1] = (e.byte.registers.d[1] & 0xffffff00U) | values[j];
        e.byte.registers.d[0] = (e.byte.registers.d[0] & 0xffffff00U) | (values[i] != 0 ? 255U : 0U);
        expected[0xd491] = values[i] != 0 ? 255 : 0;
        std::string error;
        if (values[i] != 0 && values[j] == 0) {
            e.byte.registers.d[0] = (e.byte.registers.d[0] & 0xffff0000U) | 0x1d28;
            ms5::SoundWordExecutionState helper; helper.byte = e.byte; std::uint8_t reads = 99;
            assert(ms5::execute_sound_word(expected, helper, 0, reads, error)); e.byte = helper.byte;
        } else if (values[i] == 0 && values[j] != 0) {
            e.byte.registers.d[0] = (e.byte.registers.d[0] & 0xffff0000U) | 0x1d28;
            ms5::SoundCancelExecutionState helper; helper.byte = e.byte;
            assert(ms5::execute_sound_cancel(expected, helper, error)); e.byte = helper.byte;
        }
        success(r, s); assert(r == expected && same(s, e));
        for (unsigned int k = 2; k < 8; ++k) assert(s.byte.registers.d[k] == 0xabcdf180U + k);
        for (unsigned int k = 2; k < 5; ++k) assert(s.byte.registers.a[k] == 0x76543210U + k);
    }
    // Fresh rising edge samples the external gate once and publishes even when rejected.
    std::vector<std::uint8_t> r(65536, 0); ms5::StageSoundFrameState s = initial();
    r[0xd490] = 1; r[0x12] = 1; r[0xfd82] = 1; r[0xfd8d] = 1;
    success(r, s, 1, 1); assert(r[0xd491] == 255 && word(r, 0x4d8c) == 0 && s.kind == 0);
    assert(s.byte.registers.d[0] == 0xabcd1d28 && s.byte.registers.d[1] == 0xabcd1d00);
    // Both rising-edge submissions wait, hold, and release independently. A
    // changed frame flag, gate and word queue must not cause fresh dispatch.
    r.assign(65536, 0); s = initial(); r[0xd490] = 1; full(r); put(r, 0x4d74, 1);
    r[0x12] = 1; r[0xfd82] = 1; r[0xfd8d] = 1;
    success(r, s, 0, 1); assert(s.kind == 1 && s.phase == 1 && s.saved == 0x2b && s.byte.waiting && r[0xd491] == 255);
    assert(s.byte.registers.d[0] == 0xabcd1d08);
    r[0xd490] = 0; r[0xd491] = 0x73; r[0xfd8d] = 0; r[0x4d7e] = 1; put(r, 0x4d8a, 1); put(r, 0x4d8c, 0xffff);
    success(r, s, 1); assert(s.kind == 1 && s.phase == 1 && r[0xd491] == 0x73);
    put(r, 0x4d74, 2); success(r, s, 1); assert(s.kind == 1 && s.phase == 2 && s.byte.waiting && r[0xd491] == 0x73);
    assert(r[0x4cf4] == 8 && s.byte.registers.d[0] == 0xabcd1d2b);
    success(r, s, 1); assert(s.phase == 2 && r[0xd491] == 0x73);
    put(r, 0x4d74, 3); success(r, s, 1); assert(s.kind == 0 && s.phase == 0 && s.saved == 0 && !s.byte.waiting && r[0x4cf5] == 0x2b && r[0xd491] == 0x73);
    // Three falling-edge submissions resume without rescanning or republishing.
    r.assign(65536, 0); s = initial(); r[0xd491] = 255;
    put(r, 0x4d82, 0x1d28); put(r, 0x4d8c, 2); put(r, 0x4d74, 1);
    success(r, s, 255); assert(s.kind == 2 && s.phase == 1 && s.saved == 0x1d28 && r[0xd491] == 0 && word(r, 0x4d82) == 0);
    r[0xd490] = 1; r[0xd491] = 0x74; put(r, 0x4d82, 0x1d28); put(r, 0x4d8a, 1);
    for (unsigned int phase = 1; phase <= 3; ++phase) {
        success(r, s, 255); assert(s.kind == 2 && s.phase == phase && s.saved == 0x1d28 && r[0xd491] == 0x74);
        put(r, 0x4d74, phase + 1); success(r, s, 255);
        assert(r[0xd491] == 0x74 && word(r, 0x4d82) == 0x1d28);
        if (phase < 3) assert(s.kind == 2 && s.phase == phase + 1 && s.byte.waiting);
    }
    assert(s.kind == 0 && s.phase == 0 && s.saved == 0 && !s.byte.waiting);
    assert(r[0x4cf4] == 0x14 && r[0x4cf5] == 0x1d && r[0x4cf6] == 0x28 && s.byte.registers.d[0] == 0x1d28);
    // Scan/byte failures roll back the earlier frame publication and external count.
    r.assign(65536, 0); s = initial(); r[0xd490] = 1; r[0x12] = 1; r[0xfd82] = 1; r[0xfd8d] = 1; put(r, 0x4d8a, 1); failure(r, s);
    r.assign(65536, 0); s = initial(); r[0xd491] = 255; put(r, 0x4d8a, 1); failure(r, s);
    r.assign(65536, 0); s = initial(); r[0xd491] = 255; put(r, 0x4d76, 0x8000); failure(r, s);
    put(r, 0x4d74, 1); success(r, s); assert(s.kind == 2 && s.phase == 1); put(r, 0x4d74, 2); failure(r, s);
    // A rising-edge failure after word queue writes and a later byte failure
    // still preserve d491, the external count, and the captured continuation.
    r.assign(65536, 0); s = initial(); r[0xd490] = 1; full(r); put(r, 0x4d76, 0x8000);
    r[0x12] = 1; r[0xfd82] = 1; r[0xfd8d] = 1; failure(r, s);
    put(r, 0x4d74, 1); success(r, s, 0, 1); assert(s.kind == 1 && s.phase == 1);
    put(r, 0x4d74, 2); failure(r, s);
    // A fresh state does not interpret a stale saved value as a continuation.
    r.assign(65536, 0); s = initial(); s.saved = 65535; success(r, s);
    assert(s.kind == 0 && s.phase == 0 && s.saved == 0);
    // Invalid continuation combinations and RAM sizes are transactional.
    r.assign(65536, 0); s = initial(); s.byte.waiting = true; failure(r, s);
    s = initial(); s.phase = 1; failure(r, s);
    s = initial(); s.kind = 3; failure(r, s);
    for (unsigned int kind = 1; kind <= 2; ++kind) {
        s = initial(); s.kind = kind; failure(r, s);
        s.byte.waiting = true; failure(r, s);
        s.phase = kind == 1 ? 3 : 4; failure(r, s);
        s.phase = 1; s.byte.waiting = false; failure(r, s);
    }
    s = initial(); s.kind = 1; s.phase = 1; s.saved = 256; s.byte.waiting = true; failure(r, s);
    s = initial(); r.resize(65535); failure(r, s);
    std::cout << "stage_sound_frame_test passed\n";
}
