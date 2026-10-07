#include "ms5/main_frame.h"
#include "ms5/column_control.h"
#include "ms5/palette_frame.h"
#include <new>

namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
bool sound_idle(const ms5::SoundWordPending& sound) {
    return sound.kind == 0 && sound.phase == 0 && sound.low == 0 &&
        sound.cursor == 0 && !sound.byte.waiting && sound.byte.command == 0 &&
        sound.byte.tail == 0 && sound.byte.next == 0;
}
void write_port(std::vector<ms5::VideoPortWrite>& writes, std::uint8_t size,
                std::uint32_t address, std::uint32_t value) {
    ms5::VideoPortWrite write;
    write.size = size; write.address = address; write.value = value;
    writes.push_back(write);
}
}

namespace ms5 {
bool prepare_main_frame(std::vector<std::uint8_t>& ram,
                        const std::vector<CompositionResource>& compositions,
                        const std::vector<PaletteRecord>& records,
                        std::uint16_t video, MainFrameState& state,
                        std::vector<VideoPortWrite>& writes, std::string& error) {
    const bool start = state.next_pc == 0xe74U;
    const bool sound_wait = state.next_pc == 0x3aeaU;
    const bool sprite_wait = state.next_pc == 0x16bd0U;
    if (ram.size() != 65536U || (!start && !sound_wait && !sprite_wait)) {
        error = "main preparation requires 64KiB RAM and e74/3aea/16bd0 boundary";
        return false;
    }
    const bool no_sprite = !state.sprite.waiting && state.sprite.cursor == 0;
    if ((start && (!sound_idle(state.sound) || !no_sprite)) ||
        (sound_wait && (state.sound.kind != 2 || !no_sprite ||
                       static_cast<std::uint16_t>(state.d1) != state.sound.byte.next)) ||
        (sprite_wait && (!sound_idle(state.sound) || !state.sprite.waiting))) {
        error = "main preparation pending state does not match its resume boundary";
        return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        MainFrameState next = state;
        std::vector<VideoPortWrite> output, stage_writes;
        if (start) {
            write_port(output, 2, 0x3c0004U, 0);
            write_port(output, 4, 0x3c0000U, 0x82000000U);
            if (!drain_sound_words(candidate, next.sound, error)) return false;
        } else if (sound_wait) {
            if (!resume_sound_word(candidate, next.sound, error)) return false;
        }
        if (!sprite_wait) {
            // The word cursor is saved across each byte enqueue. While the
            // byte ring waits D1.low holds its captured next index; at 3c40
            // the restored word cursor has reached the live word tail.
            const std::uint16_t cursor = next.sound.kind != 0 ?
                next.sound.byte.next : word(candidate, 0x4d8a);
            next.d1 = (next.d1 & 0xffff0000U) | cursor;
            if (next.sound.kind != 0) {
                next.next_pc = 0x3aeaU;
            } else {
                if (!begin_sprite_queue(candidate, next.sprite, error, &next.d1, &next.d3)) return false;
                next.next_pc = 0x16bd0U;
            }
        }
        if (next.next_pc == 0x16bd0U) {
            std::vector<SpriteWrite> sprite_writes;
            if (!resume_sprite_queue(candidate, compositions, next.sprite,
                    sprite_writes, error, &next.d1, &next.d3, &stage_writes)) return false;
            output.insert(output.end(), stage_writes.begin(), stage_writes.end());
            if (!next.sprite.waiting) {
                // D0 is scratch here. The following video read replaces its
                // low word before the byte result is published to RAM18.
                std::uint32_t d0 = 0;
                if (!prepare_scene_columns(candidate, d0, next.d1, next.d3, stage_writes, error)) return false;
                output.insert(output.end(), stage_writes.begin(), stage_writes.end());
                candidate[0x1b] = static_cast<std::uint8_t>(candidate[0x1b] & 0x7fU);
                if (!step_palette_frame(candidate, records, error, &stage_writes, &next.d1, &next.d3)) return false;
                output.insert(output.end(), stage_writes.begin(), stage_writes.end());
                candidate[0x1b] = static_cast<std::uint8_t>(candidate[0x1b] | 0x80U);
                const unsigned int scanline = static_cast<unsigned int>(video) >> 7;
                const unsigned int elapsed = scanline >= 0x100U ? scanline - 0x100U : 0U;
                candidate[0x18] = static_cast<std::uint8_t>(elapsed - candidate[0x18]);
                next.next_pc = 0xec4U;
            }
        }
        ram.swap(candidate);
        writes.swap(output);
        state = next;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate main preparation state";
        return false;
    }
    error.clear();
    return true;
}
}
