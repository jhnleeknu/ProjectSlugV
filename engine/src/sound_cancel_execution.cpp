#include "ms5/sound_cancel_execution.h"
#include <new>
#include <set>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
bool run(std::vector<std::uint8_t>& ram, SoundCancelExecutionState& state,
         std::string& error) {
    if (state.phase > 3 || ((state.phase == 0) == state.byte.waiting)) {
        error = "sound cancel phase and byte waiting state are inconsistent";
        return false;
    }
    SceneMapTransferState& s = state.byte.registers;
    if (state.phase == 0) {
        state.saved_word = static_cast<std::uint16_t>(s.d[0]);
        s.a[0] = 0x104d82U;
        s.d[1] = (s.d[1] & 0xffff0000U) | word(ram, 0x4d8a);
        std::set<std::uint32_t> visited;
        for (;;) {
            const std::uint32_t index = s.d[1] & 0xffffU;
            const std::uint32_t tail = word(ram, 0x4d8c);
            if (index == tail) break;
            // After the initial signed index, all targets are the four slots.
            // They cannot alter tail, so a repeated header tuple is a cycle.
            if (!visited.insert((index << 16) | tail).second) {
                error = "sound cancel scan does not terminate";
                return false;
            }
            const std::int32_t offset = index < 32768U
                ? static_cast<std::int32_t>(index) : static_cast<std::int32_t>(index) - 65536;
            s.a[1] = s.a[0] + static_cast<std::uint32_t>(offset);
            s.d[1] = (s.d[1] & 0xffff0000U) | ((index + 2U) & 6U);
            if ((s.a[1] & 1U) != 0 || s.a[1] < 0x100000U || s.a[1] >= 0x10ffffU) {
                error = "sound cancel scan requires an aligned WORD in 64KiB RAM";
                return false;
            }
            const unsigned int at = s.a[1] - 0x100000U;
            if (word(ram, at) == state.saved_word) {
                ram[at] = 0;
                ram[at + 1] = 0;
            }
        }
        s.d[0] = 0x14U;
        state.phase = 1;
    }
    for (;;) {
        if (!execute_sound_byte(ram, state.byte, error)) return false;
        if (state.byte.waiting) return true;
        if (state.phase == 1) {
            s.d[0] = (s.d[0] & 0xffffff00U) | (state.saved_word >> 8);
            state.phase = 2;
        } else if (state.phase == 2) {
            s.d[0] = (s.d[0] & 0xffff0000U) | state.saved_word;
            state.phase = 3;
        } else {
            state.phase = 0;
            state.saved_word = 0;
            return true;
        }
    }
}
}
bool execute_sound_cancel(std::vector<std::uint8_t>& ram,
    SoundCancelExecutionState& state, std::string& error) {
    if (ram.size() != 65536) {
        error = "sound cancel execution requires 64KiB RAM";
        return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram;
        SoundCancelExecutionState next = state;
        if (!run(candidate, next, error)) return false;
        ram.swap(candidate);
        state = next;
        error.clear();
        return true;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate sound cancel transaction";
        return false;
    }
}
}
