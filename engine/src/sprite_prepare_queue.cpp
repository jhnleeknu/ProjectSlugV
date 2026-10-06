#include "ms5/sprite_prepare_queue.h"
#include "ms5/sprite_queue.h"

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

bool prepare_sprite_queue(std::vector<std::uint8_t>& ram,
                          const std::vector<CompositionResource>& resources,
                          std::vector<SpriteWrite>& writes,
                          std::string& error) {
    if (ram.size() != 65536U) {
        error = "prepare queue requires exactly 65536 RAM bytes";
        return false;
    }
    const std::uint16_t read = word(ram, 0x8d34);
    const std::uint16_t start = word(ram, 0x8d36);
    const std::uint16_t normal_end = word(ram, 0x8d38);
    const std::uint16_t end = word(ram, 0x8d3a);
    if (read > 510U || start > 510U || normal_end > 510U || end > 510U ||
        (read & 1U) || (start & 1U) || (normal_end & 1U) || (end & 1U)) {
        error = "prepare queue ring indices must be even and in 0..510";
        return false;
    }
    if (read != start) {
        error = "prepare queue consumer-not-synchronized: read and prepared cursors differ";
        return false;
    }
    const unsigned int deferred_bytes = word(ram, 0x914e);
    const unsigned int normal_bytes = (normal_end + 512U - start) & 510U;
    if (((normal_end + deferred_bytes) & 510U) != end ||
        normal_bytes + deferred_bytes > 510U) {
        error = "prepare queue producer end must match normal plus deferred entries, at most 255";
        return false;
    }
    const std::size_t pools[2] = {0x8d3e, 0x8d46};
    for (unsigned int index = 0; index < 2; ++index) {
        const std::size_t pool = pools[index];
        const std::uint16_t lower = word(ram, pool);
        const std::uint16_t upper = word(ram, pool + 2);
        const std::uint16_t left = word(ram, pool + 4);
        const std::uint16_t right = word(ram, pool + 6);
        if (lower > upper || upper > 380U || left < lower || left > upper ||
            right < lower || right > upper) {
            error = "prepare queue pool bounds or current/cached slots are invalid";
            return false;
        }
    }
    for (std::size_t index = 0; index < resources.size(); ++index) {
        for (std::size_t other = 0; other < index; ++other) {
            if (resources[index].id == resources[other].id) {
                error = "prepare queue resource IDs must be unique";
                return false;
            }
        }
    }
    std::vector<std::uint8_t> updated(ram);
    if (!sort_deferred_sprites(updated, 0, error) ||
        !radix_sort_sprite_queue(updated, error)) {
        return false;
    }
    std::vector<SpriteWrite> output;
    const bool forward = (ram[0x8d3c] & 0x80U) != 0;
    const std::size_t current_offset = forward ? 4U : 6U;
    const std::size_t opposite_offset = forward ? 6U : 4U;
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
            error = "prepare queue record offset must be a multiple of 12 in 0..3060";
            return false;
        }
        const std::size_t record = 0x7f34U + offset;
        const std::uint16_t style = word(updated, record + 6);
        if (word(updated, record + 4) != 0xffffU ||
            ((style & 0xffU) != 0U && (style & 0xffU) != 4U)) {
            error = "prepare queue supports only normal rectangle records with style low byte 0 or 4";
            return false;
        }
        if ((word(updated, record + 2) & 0x3fU) != 0) {
            error = "prepare queue record X must have its low six bits zero";
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
            error = "prepare queue composition resource ID is missing";
            return false;
        }
        const std::size_t pool = pools[(style & 4U) != 0 ? 1 : 0];
        const std::uint16_t u = static_cast<std::uint16_t>(word(updated, record + 2) >> 6);
        const std::uint16_t first = word(updated, pool + current_offset);
        const std::uint16_t limit = word(updated, pool + opposite_offset);
        std::uint16_t next_slot = 0;
        std::vector<SpriteWrite> record_writes;
        const bool emitted = forward
            ? emit_sprite_rectangle(resource->data, u,
                static_cast<std::uint16_t>(style & 0xfffbU), first, limit,
                record_writes, next_slot, error)
            : emit_sprite_rectangle_reverse(resource->data, u,
                static_cast<std::uint16_t>(style & 0xfffbU), first, limit,
                record_writes, next_slot, error);
        if (!emitted) {
            return false;
        }
        put(updated, pool + current_offset, next_slot);
        output.insert(output.end(), record_writes.begin(), record_writes.end());
    }
    put(updated, 0x10, 0);
    put(updated, 0x8d36, end);
    put(updated, 0x8d38, end);
    updated[0x8d3d] = 0xffU;
    ram.swap(updated);
    writes.swap(output);
    error.clear();
    return true;
}

} // namespace ms5
