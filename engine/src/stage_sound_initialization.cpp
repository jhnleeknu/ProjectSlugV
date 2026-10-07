#include "ms5/stage_sound_initialization.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram,at)) << 16) | word(ram,at + 2);
}
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
bool idle_byte(const SoundBytePending& byte) {
    return !byte.waiting && byte.command == 0 && byte.tail == 0 && byte.next == 0;
}
bool idle_word(const SoundWordPending& word_pending) {
    return word_pending.kind == 0 && word_pending.phase == 0 && word_pending.low == 0 && word_pending.cursor == 0 && idle_byte(word_pending.byte);
}
bool word_phase(std::uint8_t phase) { return phase == 1 || (phase >= 4 && phase <= 6); }
bool valid(const std::vector<std::uint8_t>& ram, const StageSoundState& state) {
    if (ram.size() != 65536 || (state.a6 & 1U) || state.a6 < 0x100000 || state.a6 > 0x110000 - 0xc4) return false;
    if (state.phase == 0) return state.next_pc == 0x47a1c && idle_word(state.word) && idle_byte(state.byte);
    if (state.next_pc != 0x3aea || state.phase > 8) return false;
    const SoundBytePending& byte = word_phase(state.phase) ? state.word.byte : state.byte;
    if (!byte.waiting || byte.tail >= 128 || byte.next != ((byte.tail + 1U) & 127U) ||
        (state.d0 & 255U) != byte.command || (state.d1 & 65535U) != byte.next) return false;
    if (word_phase(state.phase)) {
        return idle_byte(state.byte) && state.word.kind == 1 && state.word.cursor == 0 &&
            (state.word.phase == 1 || state.word.phase == 2) && (state.word.phase != 2 || byte.command == state.word.low) &&
            (state.phase == 1 || (state.d0 & 0xff00U) == 0x1800U);
    }
    const std::uint16_t expected = state.phase == 2 ? 0x1908 : state.phase == 3 ? 0x1920 : state.phase == 7 ? 0x1808 : 0x1820;
    return idle_word(state.word) && (state.phase == 2 || state.phase == 3 || state.phase == 7 || state.phase == 8) &&
        byte.command == (expected & 255U) && (state.d0 & 65535U) == expected;
}
bool music(const StageCatalog& catalog, std::uint32_t address, std::uint16_t& result, std::string& error) {
    for (std::size_t group = 0; group < catalog.groups.size(); ++group) {
        for (std::size_t i = 0; i < catalog.groups[group].records.size(); ++i) {
            const StageRecord& record = catalog.groups[group].records[i];
            if (record.source_cpu_address != address) continue;
            if ((address & 1U) || address >= 0x100000 || record.data.size() < 18 || record.data.size() > 0x100000 - address) {
                error = "stage sound record requires aligned fixed-ROM payload of at least18 bytes"; return false;
            }
            result = word(record.data,0x10); return true;
        }
    }
    error = "stage sound live record pointer missing from catalog"; return false;
}
void advance(std::vector<std::uint8_t>& ram, StageSoundState& state) {
    if (state.phase == 1 || state.phase == 3) state.phase = 4;
    else if (state.phase == 6) { ram[0x4d7e] = 0; state.phase = 7; }
    else ++state.phase;
}
}
bool initialize_stage_sound(std::vector<std::uint8_t>& ram, const StageCatalog& catalog,
                            std::uint8_t external, StageSoundState& state,
                            std::uint8_t& reads, std::string& error) {
    if (!valid(ram,state)) { error = "invalid stage sound RAM, object or continuation"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; StageSoundState next = state; std::uint8_t next_reads = 0;
        bool resume = next.phase != 0;
        if (next.phase == 0) {
            std::uint16_t selected = 0;
            if (!music(catalog,longword(candidate,next.a6 - 0x100000 + 0x76),selected,error)) return false;
            next.d0 = (next.d0 & 0xffff0000U) | selected;
            next.d1 = (next.d1 & 0xffff0000U) | word(candidate,0xd686);
            put_word(candidate,0xd686,selected);
            if (selected == (next.d1 & 65535U) || selected == 0x10fe || selected == 0x19c1) next.phase = 4;
            else next.phase = selected == 0x19c0 ? 2 : 1;
        }
        while (next.phase != 9) {
            bool waiting;
            if (word_phase(next.phase)) {
                if (resume) {
                    if (!resume_sound_word_registers(candidate,next.d0,next.d1,next.word,error)) return false;
                } else {
                    if (next.phase >= 4) next.d0 = (next.d0 & 0xffff0000U) | (0x1890U + next.phase - 4U);
                    std::uint8_t word_reads = 0;
                    if (!enqueue_sound_word_registers(candidate,next.d0,next.d1,external,next.word,word_reads,error)) return false;
                    next_reads = static_cast<std::uint8_t>(next_reads + word_reads);
                }
                waiting = next.word.kind != 0;
            } else {
                if (resume) {
                    if (!resume_sound_byte(candidate,next.byte,error)) return false;
                } else {
                    const std::uint8_t command = next.phase == 2 || next.phase == 7 ? 8 : 0x20;
                    next.d0 = (next.d0 & 0xffffff00U) | command;
                    if (!enqueue_sound_byte(candidate,command,next.byte,error)) return false;
                }
                next.d1 = (next.d1 & 0xffff0000U) | next.byte.next;
                waiting = next.byte.waiting;
                if (!waiting) next.byte = SoundBytePending();
            }
            if (waiting) { next.next_pc = 0x3aea; break; }
            advance(candidate,next); resume = false;
        }
        if (next.phase == 9) next.next_pc = 0x47a94;
        ram.swap(candidate); state = next; reads = next_reads; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage sound transaction"; return false; }
}
}
