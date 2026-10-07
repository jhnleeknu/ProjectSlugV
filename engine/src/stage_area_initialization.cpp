#include "ms5/stage_area_initialization.h"
#include "ms5/player_record_capture.h"
#include "ms5/object_allocation.h"
#include <new>
namespace ms5 {
namespace {
bool idle_byte(const SoundBytePending& byte) {
    return !byte.waiting && byte.command == 0 && byte.tail == 0 && byte.next == 0;
}
bool idle_init(const GameInitializationState& init) {
    const GamePreludeState& prelude = init.prelude;
    return !init.returned && prelude.next_pc == 0x47570 && prelude.phase == 0 &&
        prelude.d0 == 0 && prelude.d1 == 0 && prelude.d3 == 0 && idle_byte(prelude.byte) &&
        prelude.word.kind == 0 && prelude.word.phase == 0 && prelude.word.low == 0 &&
        prelude.word.cursor == 0 && idle_byte(prelude.word.byte);
}
bool valid(const std::vector<std::uint8_t>& ram, const StageAreaInitializationState& state) {
    if (ram.size() != 65536 || (state.a6 & 1U) || state.a6 < 0x100000 || state.a6 > 0x110000 - 0xc4) return false;
    if (state.phase == 0) return state.next_pc == 0x479d0 && idle_init(state.initialization);
    const GamePreludeState& prelude = state.initialization.prelude;
    return state.phase == 1 && state.next_pc == 0x3aea && !state.initialization.returned &&
        prelude.next_pc == 0x3aea && prelude.phase >= 1 && prelude.phase <= 3 &&
        prelude.d0 == state.d0 && prelude.d1 == state.d1 && prelude.d3 == state.d3;
}
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void put_long(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    put_word(ram,at,static_cast<std::uint16_t>(value >> 16)); put_word(ram,at + 2,static_cast<std::uint16_t>(value));
}
void copy_init(StageAreaInitializationState& state) {
    state.d0 = state.initialization.prelude.d0; state.d1 = state.initialization.prelude.d1; state.d3 = state.initialization.prelude.d3;
}
bool release_selectors(std::vector<std::uint8_t>& ram, const FixedDataResource& lookup,
                       std::uint32_t& d0, std::string& error) {
    for (unsigned int i = 0; i < 2; ++i) {
        const std::size_t at = 0xdd2a + i;
        d0 = (d0 & 0xffffff00U) | ram[at];
        if ((d0 & 0x80U) != 0) continue;
        if (lookup.source_cpu_address != 0x4e4d2 || lookup.source_rom_offset != 0x4e4d2 || lookup.data.size() != 128) {
            error = "stage selectors require exact4e4d2/128-byte window"; return false;
        }
        const std::uint32_t index = d0 & 65535U;
        if (index >= 128) { error = "stage selector index outside fixed lookup"; return false; }
        d0 = (d0 & 0xffffff00U) | lookup.data[index];
        ram[0xdd1e] &= static_cast<std::uint8_t>(~(1U << (d0 & 7U)));
        ram[at] = 255;
    }
    return true;
}
bool tail(std::vector<std::uint8_t>& ram, StageAreaInitializationState& state, std::string& error) {
    if (ram[0xd684] == 0) {
        put_word(ram,0xddec,1); put_word(ram,0xddee,0x108); put_word(ram,0xddf0,0x1a0);
        put_word(ram,0xddf2,0); put_word(ram,0xddf4,0x108); put_word(ram,0xddf6,0x1a0); put_word(ram,0xddf8,0x96);
        AllocationState allocation; allocation.d0 = state.d0 & 0xffff0000U; allocation.a0 = 0xd764a; allocation.a6 = state.a6;
        if (!allocate_object(ram,allocation,error)) return false;
        state.d0 = allocation.d0;
    }
    state.d0 = 0; put_long(ram,0xd734,0);
    state.d0 = 1; put_long(ram,0xd738,0);
    state.d0 = 4; state.phase = 2; state.next_pc = 0x47a1c; return true;
}
}
bool step_stage_area_initialization(std::vector<std::uint8_t>& ram,
    const FixedDataResource& records, const FixedDataResource& player_lookup,
    const FixedDataResource& selector_lookup, std::uint8_t external,
    StageAreaInitializationState& state, std::uint8_t& reads, std::string& error) {
    if (!valid(ram,state)) { error = "invalid stage area RAM, object or continuation"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; StageAreaInitializationState next = state;
        std::uint8_t next_reads = 0; bool first_area;
        if (next.phase == 0) {
            first_area = candidate[next.a6 - 0x100000 + 0x7d] == 0;
            if (first_area) {
                GamePreludeState& prelude = next.initialization.prelude;
                prelude.next_pc = 0x47594; prelude.d0 = next.d0; prelude.d1 = next.d1; prelude.d3 = next.d3;
            } else if (!resume_stage_area(candidate,player_lookup,next.d0,next.d1,next.d3,error)) return false;
        } else first_area = true;
        if (first_area) {
            if (!initialize_game(candidate,records,external,next.initialization,next_reads,error)) return false;
            copy_init(next);
            if (!next.initialization.returned) {
                next.phase = 1; next.next_pc = 0x3aea;
                ram.swap(candidate); state = next; reads = next_reads; error.clear(); return true;
            }
            if (candidate[0xd684] == 0 && !release_selectors(candidate,selector_lookup,next.d0,error)) return false;
        }
        if (!tail(candidate,next,error)) return false;
        ram.swap(candidate); state = next; reads = next_reads; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage area initialization transaction"; return false; }
}
}
