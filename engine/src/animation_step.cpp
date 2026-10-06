#include "ms5/animation_step.h"
#include "ms5/animation_draw.h"
#include "ms5/sprite_producer.h"

namespace {

std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint32_t>(ram[at]) << 8) | ram[at + 1]);
}

std::uint32_t longword(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram, at)) << 16) |
           word(ram, at + 2);
}

void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at + 1] = static_cast<std::uint8_t>(value);
}

void put_long(std::vector<std::uint8_t>& ram, std::size_t at,
              std::uint32_t value) {
    put(ram, at, static_cast<std::uint16_t>(value >> 16));
    put(ram, at + 2, static_cast<std::uint16_t>(value));
}

std::int32_t signed_word(std::uint16_t value) {
    return value < 32768U ? static_cast<std::int32_t>(value) :
                           static_cast<std::int32_t>(value) - 65536;
}

bool fetch(const std::vector<std::uint8_t>& script, std::uint32_t base,
           std::uint64_t cursor, std::uint64_t count, std::string& error) {
    if (cursor < base || cursor - base > script.size() ||
        count > script.size() - (cursor - base)) {
        error = "animation instruction fetch is outside the script";
        return false;
    }
    return true;
}

} // namespace

namespace ms5 {

bool step_animation(std::vector<std::uint8_t>& ram,
                    std::size_t object_offset,
                    const std::vector<std::uint8_t>& script,
                    std::uint32_t script_base,
                    bool& carry, std::string& error) {
    error.clear();
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes";
        return false;
    }
    if (object_offset > 65536 - 0x62) {
        error = "object offset must leave 0x62 bytes in RAM";
        return false;
    }
    const std::size_t state = object_offset + 0x26;
    std::uint32_t pointer = longword(ram, state);
    if (pointer == 0) {
        put(ram, 0x10, 0);
        carry = true;
        return true;
    }
    if (script_base > 0x1000000U ||
        script.size() > 0x1000000U - script_base) {
        error = "script range must fit the 24-bit CPU address space";
        return false;
    }
    std::vector<std::uint8_t> next(ram);
    put(next, 0x10, 0);
    next[0xd742] = 0;
    if (next[object_offset + 0x17] > 0 && next[object_offset + 0x17] < 128) {
        --next[object_offset + 0x17];
    }
    std::uint64_t cursor = pointer;
    for (unsigned int steps = 0; steps < 10000; ++steps) {
        if (!fetch(script, script_base, cursor, 1, error)) {
            return false;
        }
        const std::uint8_t opcode = script[static_cast<std::size_t>(cursor - script_base)];
        ++cursor;
        std::uint16_t timer = word(next, state + 4);
        if (opcode == 0x28) {
            if (signed_word(timer) < 0) {
                put(next, state + 4, 0);
                cursor = pointer;
                continue;
            }
            next[state + 4] = 0;
            ram.swap(next);
            carry = true;
            return true;
        }
        if (opcode == 0x08) {
            if (!fetch(script, script_base, cursor, 5, error)) return false;
            const std::size_t at = static_cast<std::size_t>(cursor - script_base);
            pointer = longword(script, at + 1);
            put_long(next, state, pointer);
            cursor = pointer;
            continue;
        }
        if (opcode == 0x04) {
            if (!fetch(script, script_base, cursor, 7, error)) {
                return false;
            }
            const std::size_t offset = static_cast<std::size_t>(cursor - script_base);
            const std::vector<std::uint8_t> operand(script.begin() + offset,
                                                    script.begin() + offset + 7);
            cursor += 7;
            AnimationDraw draw;
            if (!decode_animation_draw(next, object_offset, operand, draw, error)) {
                return false;
            }
            if (!draw.skipped) {
                SpriteSubmitStatus status;
                if (!submit_sprite(next, draw.d0, draw.d1, draw.d5, draw.d7,
                                   status, error)) {
                    return false;
                }
                if (status == SpriteWaiting) {
                    error = "animation sprite producer wait cannot resume in this API";
                    return false;
                }
            }
            continue;
        }
        if (opcode != 0x00) {
            error = "unsupported animation opcode";
            return false;
        }
        next[0xd742] = static_cast<std::uint8_t>(next[0xd742] + 1U);
        if (!fetch(script, script_base, cursor, 1, error)) {
            return false;
        }
        const std::uint8_t duration = script[static_cast<std::size_t>(cursor - script_base)];
        ++cursor;
        if (duration == 0) {
            if (signed_word(timer) < 0) {
                put(next, state + 4, 0);
                cursor = pointer;
                continue;
            }
            ram.swap(next);
            carry = false;
            return true;
        }
        const std::uint16_t old = timer;
        if (signed_word(old) <= 0) {
            timer = static_cast<std::uint16_t>(
                (((static_cast<std::uint32_t>(timer >> 8) + duration) & 255U) << 8) |
                (timer & 255U));
        }
        if (signed_word(old) >= 0) {
            timer = static_cast<std::uint16_t>(
                static_cast<std::uint32_t>(timer) - word(next, state + 6));
        }
        put(next, state + 4, timer);
        if (signed_word(timer) > 0) {
            cursor = pointer;
        }
        if (!fetch(script, script_base, cursor, 1, error)) {
            return false;
        }
        const bool ended = script[static_cast<std::size_t>(cursor - script_base)] == 0x28;
        if (ended) {
            cursor = pointer;
        }
        if (signed_word(old) < 0) {
            continue;
        }
        put_long(next, state, static_cast<std::uint32_t>(cursor));
        ram.swap(next);
        carry = ended;
        return true;
    }
    error = "animation instruction limit of 10000 exceeded";
    return false;
}

} // namespace ms5
