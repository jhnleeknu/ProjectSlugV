#include "ms5/sprite_producer.h"

namespace {

std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(ram[at]) << 8) | ram[at + 1]);
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

bool valid_cursor(std::uint16_t value) {
    return value <= 510 && (value & 1U) == 0;
}

} // namespace

namespace ms5 {

bool initialize_sprite_queue(std::vector<std::uint8_t>& ram,
                             std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes";
        return false;
    }
    put_long(ram, 0x9152, 0xcd50);
    ram[0x8d3d] = 0;
    for (std::size_t at = 0x8d34; at < 0x8d3c; at += 2) {
        put(ram, at, 0);
    }
    put_long(ram, 0x914e, 0);
    for (std::size_t index = 0; index < 256; ++index) {
        put(ram, 0x8b34 + index * 2,
            static_cast<std::uint16_t>(index * 12));
    }
    for (std::size_t at = 0x8d3e; at < 0x8d4e; at += 2) {
        put(ram, at, 0xffff);
    }
    error.clear();
    return true;
}

bool submit_sprite(std::vector<std::uint8_t>& ram, std::uint32_t d0,
                   std::uint32_t d1, std::uint32_t d5, std::uint32_t d7,
                   SpriteSubmitStatus& status, std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes";
        return false;
    }
    if (longword(ram, 0x9152) != 0xcd50) {
        error = "only the default callback at CPU 0x00cd50 is supported";
        return false;
    }
    const std::uint32_t u = d0 >> 16;
    const std::uint32_t v = d0 & 0xffffU;
    if (((v - 64U) & 0xffffU) >= 640U ||
        ((u + 352U) & 0xffffU) >= 1024U) {
        status = SpriteClipped;
        error.clear();
        return true;
    }
    const std::uint16_t read = word(ram, 0x8d34);
    const std::uint16_t prepared = word(ram, 0x8d36);
    const std::uint16_t normal = word(ram, 0x8d38);
    const std::uint16_t producer = word(ram, 0x8d3a);
    if (!valid_cursor(read) || !valid_cursor(prepared) ||
        !valid_cursor(normal) || !valid_cursor(producer)) {
        error = "queue cursors must be even byte offsets in 0..510";
        return false;
    }
    const std::uint16_t next = static_cast<std::uint16_t>((producer + 2U) & 510U);
    if (next == read) {
        status = prepared == read ? SpriteFull : SpriteWaiting;
        error.clear();
        return true;
    }
    const std::uint16_t offset = word(ram, 0x8b34 + next);
    if (offset > 3060 || offset % 12 != 0) {
        error = "chosen record offset must be a multiple of 12 in 0..3060";
        return false;
    }
    const bool deferred = (d1 & 64U) != 0;
    const std::uint16_t count = deferred ? word(ram, 0x914e) : 0;
    if (deferred && !valid_cursor(count)) {
        error = "deferred count must be even and at most 510 bytes";
        return false;
    }
    // No fallible validation remains after the first mutation.
    put(ram, 0x8d3a, next);
    if (deferred) {
        put(ram, 0x914e, static_cast<std::uint16_t>(count + 2U));
        put(ram, 0x8f4e + count, offset);
    } else {
        put(ram, 0x8b34 + normal, offset);
        put(ram, 0x8d38, static_cast<std::uint16_t>((normal + 2U) & 510U));
    }
    const std::size_t record = 0x7f34 + offset;
    put_long(ram, record, ((d5 & 0xffffU) << 16) | ((u << 6) & 0xffffU));
    put_long(ram, record + 4, d1 & 0xffffff07U);
    put_long(ram, record + 8, d7 | (v << 23));
    status = SpriteAccepted;
    error.clear();
    return true;
}

} // namespace ms5
