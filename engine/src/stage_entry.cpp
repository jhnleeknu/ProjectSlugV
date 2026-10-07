#include "ms5/stage_entry.h"
#include "ms5/game_screen_reset.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t get32(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) | (static_cast<std::uint32_t>(ram[at+1]) << 16) |
        (static_cast<std::uint32_t>(ram[at+2]) << 8) | ram[at+3];
}
std::uint16_t get16(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at+1]);
}
void put32(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 24); ram[at+1] = static_cast<std::uint8_t>(value >> 16);
    ram[at+2] = static_cast<std::uint8_t>(value >> 8); ram[at+3] = static_cast<std::uint8_t>(value);
}
bool idle(const SoundPairState& sound) {
    return sound.entry == 0x3d58 && sound.next_pc == 0x3d58 && sound.phase == 0 && sound.saved == 0 &&
        sound.d0 == 0 && sound.d1 == 0 && sound.d3 == 0 && !sound.byte.waiting && sound.byte.command == 0 &&
        sound.byte.tail == 0 && sound.byte.next == 0;
}
bool valid(const StageEntryState& state) {
    if ((state.a6 & 1U) || state.a6 < 0x100000 || state.a6 > 0x110000-0xc4) return false;
    if (state.phase == 0) return (state.next_pc == 0x477e4 || state.next_pc == 0x477ee) && idle(state.sound);
    return state.phase == 1 && state.next_pc == 0x3aea && state.sound.entry == 0x3d58 &&
        (state.sound.phase == 1 || state.sound.phase == 2) && state.sound.next_pc == 0x3aea &&
        state.sound.d0 == state.d0 && state.sound.d1 == state.d1 && state.sound.d3 == state.d3;
}
bool record_at(const StageCatalog& catalog, std::uint32_t address, const StageRecord*& result, std::string& error) {
    result = NULL;
    for (std::size_t group = 0; group < catalog.groups.size(); ++group) {
        std::uint16_t count = 0; std::uint32_t record = 0, name = 0;
        if (!query_stage(catalog,static_cast<std::uint16_t>(group),0,count,record,name,error)) return false;
        for (std::size_t area = 0; area < catalog.groups[group].records.size(); ++area) {
            const StageRecord& item = catalog.groups[group].records[area];
            if (item.source_cpu_address == address) result = &item;
        }
    }
    if (result == NULL) { error = "stage entry live record pointer not found in validated catalog"; return false; }
    return true;
}
void copy_sound(StageEntryState& state) {
    state.d0 = state.sound.d0; state.d1 = state.sound.d1; state.d3 = state.sound.d3;
}
}
bool step_stage_entry(std::vector<std::uint8_t>& ram, const StageCatalog& catalog,
                      const FixedDataResource& debug_tables, StageEntryState& state,
                      std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || !valid(state)) { error = "invalid stage entry RAM or continuation"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; StageEntryState next = state; std::vector<VideoPortWrite> output;
        const std::size_t object = next.a6 - 0x100000;
        bool sound_done = false;
        if (next.phase == 0) {
            if (next.next_pc == 0x477e4 &&
                !initialize_stage_scene(candidate,debug_tables,next.d0,next.d1,next.d3,output,error)) return false;
            next.next_pc = 0x477ee;
            candidate[object+0x7c] = candidate[0xd680]; candidate[object+0x7d] = candidate[0xd681];
            bool found = false;
            for (unsigned int iteration = 0; iteration < 256; ++iteration) {
                const std::uint8_t stage = candidate[object+0x7c];
                std::uint16_t count = 0; std::uint32_t record = 0, name = 0;
                if (!query_stage(catalog,stage,candidate[object+0x7d],count,record,name,error)) return false;
                const std::size_t group = stage < 19 ? stage : 0;
                candidate[0xd684] = static_cast<std::uint8_t>(catalog.groups[group].header >> 8);
                if (record == 0) candidate[object+0x7d] = 0;
                else { put32(candidate,object+0x76,record); found = true; break; }
            }
            if (!found) { error = "stage entry native empty-group loop unsupported"; return false; }
            candidate[0x967] = 255;
            const std::size_t objects[2] = {0xcb8,0xda8};
            for (unsigned int i = 0; i < 2; ++i) {
                const std::size_t at = objects[i];
                if (get32(candidate,at) != 0x270e) { candidate[at+0x61] |= 0x40; candidate[at+0xa8] |= 1; }
            }
            candidate[0x965] = 0; candidate[0xdd1f] = 0; candidate[0x7def] = 255; candidate[0xd683] &= 0xc8;
            const StageRecord* record = NULL;
            if (!record_at(catalog,get32(candidate,object+0x76),record,error)) return false;
            next.d0 = (static_cast<unsigned int>(record->data[0x10]) << 8) | record->data[0x11];
            next.d1 = get16(candidate,0xd686);
            if (next.d0 != next.d1) {
                next.d0 = next.d0 == 0x19c1 ? 0x38 : 0x80;
                next.sound = SoundPairState(); next.sound.d0 = next.d0; next.sound.d1 = next.d1; next.sound.d3 = next.d3;
                if (!enqueue_sound_pair(candidate,next.sound,error)) return false;
                copy_sound(next);
                if (next.sound.phase != 3) { next.phase = 1; next.next_pc = 0x3aea; }
                else sound_done = true;
            }
        } else {
            if (!enqueue_sound_pair(candidate,next.sound,error)) return false;
            copy_sound(next);
            if (next.sound.phase == 3) sound_done = true;
        }
        if (next.phase != 1 || sound_done) {
            if (sound_done) { candidate[0xd68c] = 0; candidate[0xd68d] = 1; }
            std::vector<VideoPortWrite> screen;
            if (!reset_game_screen(candidate,0xca9e,next.d0,next.d1,next.d3,screen,error)) return false;
            output.insert(output.end(),screen.begin(),screen.end());
            const StageRecord* record = NULL;
            if (!record_at(catalog,get32(candidate,object+0x76),record,error)) return false;
            next.d0 = record->data[0];
            if (next.d0 >= 0x18 || (next.d0 & 3U)) { error = "stage entry unsupported native selector trap or misalignment"; return false; }
            const std::uint32_t targets[6] = {0x478c4,0x478f0,0x4791c,0x47934,0x4794c,0x47964};
            next.next_pc = targets[next.d0/4]; next.phase = 2;
        }
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage entry transaction"; return false; }
}
}
