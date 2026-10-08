#include "ms5/sound_word_execution.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
void put(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at + 1] = static_cast<std::uint8_t>(value);
}
void low_word(std::uint32_t& reg, std::uint32_t value) {
    reg = (reg & 0xffff0000U) | (value & 65535U);
}
std::uint32_t indexed(std::uint32_t base, std::uint32_t value) {
    const std::uint32_t low = value & 65535U;
    const std::int32_t offset = low < 32768U ? static_cast<std::int32_t>(low) : static_cast<std::int32_t>(low) - 65536;
    return base + static_cast<std::uint32_t>(offset);
}
bool address(std::uint32_t at, unsigned int& offset, std::string& error) {
    if ((at & 1U) != 0) { error = "unaligned sound word access"; return false; }
    if (at < 0x100000U || at > 0x10fffeU) { error = "sound word access outside64KiB RAM"; return false; }
    offset = static_cast<unsigned int>(at - 0x100000U);
    return true;
}
bool submit(std::vector<std::uint8_t>& ram, SoundWordExecutionState& state, std::string& error) {
    if (!execute_sound_byte(ram, state.byte, error)) return false;
    if (state.byte.waiting) return true;
    if (state.phase == 1) {
        state.byte.registers.d[0] = (state.byte.registers.d[0] & 0xffffff00U) | state.saved_low;
        state.phase = 2;
        if (!execute_sound_byte(ram, state.byte, error)) return false;
        if (state.byte.waiting) return true;
    }
    state.phase = 0;
    state.saved_low = 0;
    return true;
}
bool run(std::vector<std::uint8_t>& ram, SoundWordExecutionState& state,
    std::uint8_t external_status, std::uint8_t& reads, std::string& error) {
    if (state.phase > 2 || (state.phase == 0 && state.byte.waiting) ||
        (state.phase != 0 && !state.byte.waiting)) {
        error = "invalid sound word continuation"; return false;
    }
    if (state.phase != 0) return submit(ram, state, error);
    state.saved_low = 0;
    SceneMapTransferState& s = state.byte.registers;
    const std::uint32_t command = s.d[0] & 65535U;
    if (command >= 0x2000U || (command & 255U) < 0x20U) return true;
    low_word(s.d[1], command & 0xff00U);
    const std::uint32_t category = s.d[1] & 65535U;
    if (category == 0x100U || category == 0x300U || category == 0x200U) return true;
    if (ram[0x12] == 1) {
        if (category == 0) return true;
        if (ram[0xfd82] != 0 && ram[0xfe80] == 0) {
            reads = 1;
            if (external_status != 0) return true;
        }
        if (ram[0xfd8d] == 0) return true;
    }
    if (ram[0x4d7e] != 0 && command >= 0x1000U) return true;
    if ((ram[0xf001] & 0x20U) != 0 && category == 0) return true;
    s.a[0] = 0x104d82U;
    low_word(s.d[1], word(ram, 0x4d8a));
    std::vector<std::uint32_t> visited;
    while ((s.d[1] & 65535U) != word(ram, 0x4d8c)) {
        const std::uint32_t index = s.d[1] & 65535U;
        for (unsigned int i = 0; i < visited.size(); ++i) {
            if (visited[i] == index) { error = "nonterminating sound word scan"; return false; }
        }
        visited.push_back(index);
        s.a[1] = indexed(s.a[0], index);
        low_word(s.d[1], (index + 2U) & 6U);
        unsigned int current = 0;
        if (!address(s.a[1], current, error)) return false;
        if (word(ram, current) == command) {
            if ((s.d[1] & 65535U) != word(ram, 0x4d8c)) {
                unsigned int following = 0;
                if (!address(indexed(s.a[0], s.d[1]), following, error)) return false;
                const std::uint16_t next_word = word(ram, following);
                put(ram, current, next_word);
                put(ram, following, s.d[0]);
            }
            return true;
        }
    }
    unsigned int destination = 0;
    if (!address(indexed(s.a[0], s.d[1]), destination, error)) return false;
    put(ram, destination, s.d[0]);
    low_word(s.d[1], ((s.d[1] & 65535U) + 2U) & 6U);
    put(ram, 0x4d8c, s.d[1]);
    if ((s.d[1] & 65535U) != word(ram, 0x4d8a)) return true;
    s.a[0] = indexed(s.a[0], s.d[1]);
    low_word(s.d[1], ((s.d[1] & 65535U) + 2U) & 6U);
    put(ram, 0x4d8a, s.d[1]);
    if (!address(s.a[0], destination, error)) return false;
    if (word(ram, destination) == 0) return true;
    s.d[0] = (s.d[0] & 0xffffff00U) | ram[destination];
    state.saved_low = ram[destination + 1];
    s.a[0] += 2U;
    state.phase = 1;
    return submit(ram, state, error);
}
}
bool execute_sound_word(std::vector<std::uint8_t>& ram,
    SoundWordExecutionState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::string& error) {
    if (ram.size() != 65536) { error = "sound word execution requires64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram;
        SoundWordExecutionState next = state;
        std::uint8_t reads = 0;
        if (!run(candidate, next, external_status, reads, error)) return false;
        ram.swap(candidate); state = next; external_reads = reads; error.clear(); return true;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate sound word transaction"; return false;
    }
}
}
