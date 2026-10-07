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

void port(std::vector<ms5::VideoPortWrite>& ports, std::uint8_t size,
          std::uint32_t address, std::uint32_t value) {
    ms5::VideoPortWrite write;
    write.size = size;
    write.address = address;
    write.value = value;
    ports.push_back(write);
}

} // namespace

namespace ms5 {

SpritePreparePending::SpritePreparePending() : waiting(false), cursor(0) {}

bool begin_sprite_queue(std::vector<std::uint8_t>& ram,
                        SpritePreparePending& pending, std::string& error,
                        std::uint32_t* d1, std::uint32_t* d3) {
    if (pending.waiting) {
        error = "prepare queue already has a pending wait";
        return false;
    }
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
    const unsigned int deferred_bytes = word(ram, 0x914e);
    const unsigned int normal_bytes = (normal_end + 512U - start) & 510U;
    if (((normal_end + deferred_bytes) & 510U) != end ||
        normal_bytes + deferred_bytes > 510U) {
        error = "prepare queue producer end must match normal plus deferred entries, at most 255";
        return false;
    }
    std::vector<std::uint8_t> updated(ram);
    if (!sort_deferred_sprites(updated, 0, error) ||
        !radix_sort_sprite_queue(updated, error)) {
        return false;
    }
    SpritePreparePending next;
    next.waiting = true;
    next.cursor = word(updated, 0x8d36);
    // The final radix pass consumes its temporary array backwards. Its last
    // D1 is twice the high key byte of the first temporary record; MOVEQ
    // clears its high word. D3 was cleared by the radix histogram setup.
    if (start != end) {
        if (d1 != 0) *d1 = static_cast<std::uint32_t>(
            updated[0x7f34U + word(updated, 0x8f4e)]) * 2U;
        if (d3 != 0) *d3 = 0;
    }
    ram.swap(updated);
    pending = next;
    error.clear();
    return true;
}

bool resume_sprite_queue(std::vector<std::uint8_t>& ram,
                         const std::vector<CompositionResource>& resources,
                         SpritePreparePending& pending,
                         std::vector<SpriteWrite>& writes, std::string& error,
                         std::uint32_t* d1, std::uint32_t* d3,
                         std::vector<VideoPortWrite>* ports) {
    if (ram.size() != 65536U || !pending.waiting ||
        pending.cursor > 510U || (pending.cursor & 1U)) {
        error = "prepare queue resume requires RAM and a valid pending cursor";
        return false;
    }
    const std::uint16_t read = word(ram, 0x8d34);
    if (read > 510U || (read & 1U)) {
        error = "prepare queue read cursor must be even and in 0..510";
        return false;
    }
    if (read != pending.cursor) {
        writes.clear();
        if (ports != 0) ports->clear();
        error.clear();
        return true;
    }
    const std::uint16_t start = word(ram, 0x8d36);
    const std::uint16_t end = word(ram, 0x8d3a);
    if (start > 510U || end > 510U || (start & 1U) || (end & 1U)) {
        error = "prepare queue prepared and end cursors must be even and in 0..510";
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
    std::vector<SpriteWrite> output;
    std::vector<VideoPortWrite> port_output;
    std::uint32_t next_d1 = d1 != 0 ? *d1 : 0;
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
            (style & 0xf8U) != 0U) {
            error = "prepare queue supports only rectangle records with style low byte in 0..7";
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
        const std::uint16_t emitter_style = static_cast<std::uint16_t>(style & 0xfffbU);
        next_d1 = (next_d1 & 0xffff0000U) | emitter_style;
        port(port_output, 2, 0x2ffff2U, ((identifier & 7U) + 1U) << 12);
        port(port_output, 2, 0x2ffff0U, 0);
        const std::size_t pool = pools[(style & 4U) != 0 ? 1 : 0];
        const std::uint16_t u = static_cast<std::uint16_t>(word(updated, record + 2) >> 6);
        const bool disabled = word(updated, pool) == 0xffffU;
        const std::uint16_t first = disabled ? 0U : word(updated, pool + current_offset);
        const std::uint16_t limit = disabled ? 0U : word(updated, pool + opposite_offset);
        std::uint16_t next_slot = 0;
        std::vector<SpriteWrite> record_writes;
        const bool emitted = emit_sprite_blocks(resource->data, u, 0U,
            emitter_style, first, limit,
            false, !forward, 0U, record_writes, next_slot, error, &next_d1);
        if (!emitted) {
            return false;
        }
        if (!disabled) {
            put(updated, pool + current_offset, next_slot);
            output.insert(output.end(), record_writes.begin(), record_writes.end());
            for (std::size_t index = 0; index < record_writes.size(); ++index) {
                port(port_output, 4, 0x3c0000U,
                     (static_cast<std::uint32_t>(record_writes[index].address) << 16) |
                     record_writes[index].value);
            }
        }
    }
    port(port_output, 2, 0x2ffff2U, 0x1000U);
    port(port_output, 2, 0x2ffff0U, 0);
    put(updated, 0x10, 0);
    put(updated, 0x8d36, end);
    put(updated, 0x8d38, end);
    updated[0x8d3d] = 0xffU;
    ram.swap(updated);
    writes.swap(output);
    pending = SpritePreparePending();
    if (d1 != 0) *d1 = next_d1;
    // Emitters save and restore D3 around their unrolled tile loops.
    (void)d3;
    if (ports != 0) ports->swap(port_output);
    error.clear();
    return true;
}

bool prepare_sprite_queue(std::vector<std::uint8_t>& ram,
                          const std::vector<CompositionResource>& resources,
                          std::vector<SpriteWrite>& writes, std::string& error,
                          std::uint32_t* d1, std::uint32_t* d3,
                          std::vector<VideoPortWrite>* ports) {
    // Preserve the synchronous API's all-or-nothing contract.
    std::vector<std::uint8_t> updated(ram);
    SpritePreparePending pending;
    std::uint32_t next_d1 = d1 != 0 ? *d1 : 0;
    std::uint32_t next_d3 = d3 != 0 ? *d3 : 0;
    if (!begin_sprite_queue(updated, pending, error, &next_d1, &next_d3)) {
        return false;
    }
    if (word(updated, 0x8d34) != pending.cursor) {
        error = "prepare queue consumer-not-synchronized: read and prepared cursors differ";
        return false;
    }
    if (!resume_sprite_queue(updated, resources, pending, writes, error,
                             &next_d1, &next_d3, ports)) {
        return false;
    }
    ram.swap(updated);
    if (d1 != 0) *d1 = next_d1;
    if (d3 != 0) *d3 = next_d3;
    error.clear();
    return true;
}

} // namespace ms5
