#include "ms5/sprite_refresh_queue.h"

namespace {

std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t offset) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(ram[offset]) << 8) | ram[offset + 1]);
}

void put(std::vector<std::uint8_t>& ram, std::size_t offset,
         std::uint16_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 1] = static_cast<std::uint8_t>(value);
}

} // namespace

namespace ms5 {

bool refresh_sprite_queue(std::vector<std::uint8_t>& ram,
                          const std::vector<CompositionResource>& resources,
                          std::vector<SpriteWrite>& writes,
                          bool& processed, std::string& error, std::uint32_t* d0) {
    if (ram.size() != 65536U) {
        error = "refresh queue requires exactly 65536 RAM bytes";
        return false;
    }
    if ((ram[0x8d3d] & 0x80U) == 0) {
        ram[0x8d3d] &= 0x7fU;
        writes.clear();
        processed = false;
        error.clear();
        return true;
    }
    const std::uint16_t start = word(ram, 0x8d34);
    const std::uint16_t end = word(ram, 0x8d36);
    if (start > 510U || end > 510U || (start & 1U) || (end & 1U)) {
        error = "refresh queue ring indices must be even and in 0..510";
        return false;
    }
    const std::size_t pools[2] = {0x8d3e, 0x8d46};
    for (unsigned int index = 0; index < 2; ++index) {
        const std::size_t pool = pools[index];
        const std::uint16_t lower = word(ram, pool);
        const std::uint16_t upper = word(ram, pool + 2);
        const std::uint16_t left = word(ram, pool + 4);
        const std::uint16_t right = word(ram, pool + 6);
        const bool disabled = lower == 0xffffU && upper == 0xffffU &&
                              left == 0xffffU && right == 0xffffU;
        if (!disabled && (lower > upper || upper > 380U || left < lower || left > upper ||
                          right < lower || right > upper)) {
            error = "refresh queue pool bounds or current/cached slots are invalid";
            return false;
        }
    }
    for (std::size_t index = 0; index < resources.size(); ++index) {
        for (std::size_t other = 0; other < index; ++other) {
            if (resources[index].id == resources[other].id) {
                error = "refresh queue resource IDs must be unique";
                return false;
            }
        }
    }
    std::vector<std::uint8_t> updated(ram);
    std::vector<SpriteWrite> output;
    const bool forward = (ram[0x8d3c] & 0x80U) != 0;
    const std::size_t current_offset = forward ? 4U : 6U;
    const std::size_t cached_offset = forward ? 6U : 4U;
    for (unsigned int index = 0; index < 2; ++index) {
        put(updated, pools[index] + current_offset,
            word(updated, pools[index] + (forward ? 0U : 2U)));
    }
    std::uint16_t cursor = forward ? start : end;
    const std::uint16_t finish = forward ? end : start;
    while (cursor != finish) {
        if (!forward) {
            cursor = static_cast<std::uint16_t>((cursor + 510U) & 0x1feU);
        }
        const std::uint16_t offset = word(updated, 0x8b34U + cursor);
        if (forward) {
            cursor = static_cast<std::uint16_t>((cursor + 2U) & 0x1feU);
        }
        if (offset > 3060U || offset % 12U != 0) {
            error = "refresh queue record offset must be a multiple of 12 in 0..3060";
            return false;
        }
        const std::size_t record = 0x7f34U + offset;
        const std::uint16_t style = word(updated, record + 6);
        if (word(updated, record + 4) != 0xffffU ||
            (style & 0xf8U) != 0U) {
            error = "refresh queue supports only rectangle records with style low byte in 0..7";
            return false;
        }
        if ((word(updated, record + 2) & 0x3fU) != 0) {
            error = "refresh queue record X must have its low six bits zero";
            return false;
        }
        std::uint32_t packed = 0;
        for (unsigned int byte = 0; byte < 4; ++byte) {
            packed = (packed << 8) | updated[record + 8 + byte];
        }
        const std::uint32_t identifier = packed & 0x7fffffU;
        const CompositionResource* resource = 0;
        for (std::size_t index = 0; index < resources.size(); ++index) {
            if (resources[index].id == identifier) {
                resource = &resources[index];
                break;
            }
        }
        if (resource == 0) {
            error = "refresh queue composition resource ID is missing";
            return false;
        }
        const std::size_t pool = pools[(style & 4U) != 0 ? 1 : 0];
        const std::uint16_t u = static_cast<std::uint16_t>(word(updated, record + 2) >> 6);
        const std::uint16_t v = static_cast<std::uint16_t>(packed >> 23);
        const bool disabled = word(updated, pool) == 0xffffU;
        const std::uint16_t first = disabled ? 0U : word(updated, pool + current_offset);
        const std::uint16_t limit = disabled ? 0U : word(updated, pool + (forward ? 2U : 0U));
        const std::uint16_t cached = disabled ? 0U : word(updated, pool + cached_offset);
        std::uint16_t next_slot = 0;
        std::vector<SpriteWrite> record_writes;
        const bool emitted = emit_sprite_blocks(resource->data, u, v,
            static_cast<std::uint16_t>(style & 0xfffbU), first, limit,
            true, !forward, cached, record_writes, next_slot, error);
        if (!emitted) {
            return false;
        }
        if (!disabled) {
            put(updated, pool + current_offset, next_slot);
            output.insert(output.end(), record_writes.begin(), record_writes.end());
        }
    }
    for (unsigned int index = 0; index < 2; ++index) {
        const std::size_t pool = pools[index];
        const std::uint16_t left = word(updated, pool + 4);
        const std::uint16_t right = word(updated, pool + 6);
        unsigned int slot = forward ? (left > right ? left : right)
                                    : (left < right ? left : right);
        const unsigned int limit = word(updated, pool + (forward ? 2U : 0U));
        while (forward ? slot < limit : slot > limit) {
            SpriteWrite write;
            write.address = static_cast<std::uint16_t>((forward ? 0x8201U : 0x8200U) + slot);
            write.value = 0x8000U;
            output.push_back(write);
            if (forward) {
                ++slot;
            } else {
                --slot;
            }
        }
    }
    put(updated, 0x10, 0);
    put(updated, 0x8d34, end);
    updated[0x8d3c] ^= 0x80U;
    updated[0x8d3d] &= 0x7fU;
    // Both cleanup calls overwrite D0 with address:8000 even for zero writes.
    // The second pool determines the final address; incoming upper bits vanish.
    const std::uint32_t final_address=(static_cast<std::uint32_t>(
        word(updated, pools[1]+(forward ? 2U : 0U)))+(forward ? 0x8201U : 0x8200U))&65535U;
    ram.swap(updated);
    writes.swap(output);
    processed = true;
    if(d0!=0) *d0=(final_address<<16)|0x8000U;
    error.clear();
    return true;
}

} // namespace ms5
