#include "ms5/object_restart.h"

#include "ms5/object_state.h"
#include "ms5/palette_allocator.h"
#include "ms5/position_state.h"

#include <new>

namespace {

void write_word(std::vector<std::uint8_t>& ram, std::size_t offset,
                std::uint16_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 1] = static_cast<std::uint8_t>(value);
}

void write_long(std::vector<std::uint8_t>& ram, std::size_t offset,
                std::uint32_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 24);
    ram[offset + 1] = static_cast<std::uint8_t>(value >> 16);
    ram[offset + 2] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 3] = static_cast<std::uint8_t>(value);
}

} // namespace

namespace ms5 {

bool restart_static_object(std::vector<std::uint8_t>& ram,
                           std::uint32_t object_address,
                           std::uint32_t callback, std::uint8_t watchdog,
                           std::vector<VideoPortWrite>& writes,
                           std::string& error) {
    if (ram.size() != 65536U) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    if (object_address < 0x100000U || object_address > 0x110000U - 0xc4U ||
        (object_address & 1U) != 0) {
        error = "object address must be even and contain 0xc4 bytes in RAM";
        return false;
    }
    if (callback >= 0x100000U || (callback & 1U) != 0) {
        error = "callback must be an even fixed-ROM address below 0x100000";
        return false;
    }
    const std::size_t object = object_address - 0x100000U;
    if (ram[object + 0x10U] != 0 || ram[object + 0x11U] != 0) {
        error = "original object restart TRAP: object +0x10 word is nonzero";
        return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        VideoPortWrite watchdog_write;
        watchdog_write.address = 0x300001U;
        watchdog_write.value = watchdog;
        watchdog_write.size = 1;
        pending.push_back(watchdog_write);

        // CPU 0x00299c calls 0x008ff4 before 0x046ef4. Read the
        // coordinate index after releasing palettes to preserve write order.
        if (!release_palettes(candidate, object, error)) {
            return false;
        }
        const std::uint8_t index = candidate[object + 0x6cU];
        if ((index & 0x80U) == 0) {
            if (index >= 8) {
                error = "object coordinate index must be below eight or have bit 7 set";
                return false;
            }
            const std::uint32_t coordinate = 0x10d4e6U +
                static_cast<std::uint32_t>(index) * 0x2cU;
            const std::size_t offset = coordinate - 0x100000U;
            write_word(candidate, offset + 0x26U, 0xffffU);
            write_word(candidate, offset + 0x2aU, 2U);
            candidate[object + 0x6cU] = 0xffU;
            if (!update_position(&candidate[0], candidate.size(), coordinate,
                                 false, error)) {
                return false;
            }
        }
        write_long(candidate, object, 0x00270eU);
        if (candidate[object + 0x10U] != 0U || candidate[object + 0x11U] != 0U) {
            error = "cleanup changed object type; linked restart path is unsupported";
            return false;
        }
        if (!reset_object_fields(&candidate[object], candidate.size() - object)) {
            error = "object field reset requires 0xc4 bytes";
            return false;
        }
        write_long(candidate, object, callback);
        ram.swap(candidate);
        writes.swap(pending);
    } catch (const std::bad_alloc&) {
        error = "cannot allocate static object restart";
        return false;
    }
    error.clear();
    return true;
}

} // namespace ms5
