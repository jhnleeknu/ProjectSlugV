#include "ms5/menu_descriptor.h"

#include <new>

namespace ms5 {
namespace {

std::uint16_t read_u16(const std::uint8_t* bytes) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(bytes[0]) << 8) | bytes[1]);
}

std::uint32_t read_u32(const std::uint8_t* bytes) {
    return (static_cast<std::uint32_t>(bytes[0]) << 24) |
           (static_cast<std::uint32_t>(bytes[1]) << 16) |
           (static_cast<std::uint32_t>(bytes[2]) << 8) |
           static_cast<std::uint32_t>(bytes[3]);
}

bool fail(std::string& error, const char* message) {
    error = message;
    return false;
}

} // namespace

bool decode_menu_descriptor(const FixedDataResource& resource,
                            std::uint32_t address, MenuDescriptor& descriptor,
                            std::string& error) {
    const std::uint32_t base = resource.source_cpu_address;
    if (base >= 0x100000U || base != resource.source_rom_offset || (base & 1U)) {
        return fail(error, "menu resource must map an even fixed program ROM address");
    }
    if (resource.data.empty() || resource.data.size() > 0x100000U - base) {
        return fail(error, "menu resource exceeds the fixed program ROM window");
    }
    if ((address & 1U) || address < base || address - base >= resource.data.size()) {
        return fail(error, "menu address must be even and inside the resource");
    }
    const std::size_t start = address - base;
    if (resource.data.size() - start < 16U) {
        return fail(error, "menu descriptor header is truncated");
    }
    MenuDescriptor candidate;
    const std::uint8_t* header = &resource.data[start];
    candidate.source_cpu_address = address;
    candidate.title_address = read_u32(header);
    candidate.min_width = header[4];
    candidate.min_height = header[5];
    candidate.callback6 = read_u32(header + 6);
    candidate.callback10 = read_u32(header + 10);
    candidate.flags = read_u16(header + 14);
    std::size_t cursor = start + 16U;
    for (;;) {
        if (resource.data.size() - cursor < 4U) {
            return fail(error, "menu descriptor terminator is missing or truncated");
        }
        const std::uint32_t title = read_u32(&resource.data[cursor]);
        if (title == UINT32_C(0xffffffff)) {
            cursor += 4U;
            break;
        }
        if (candidate.items.size() >= 255U) {
            return fail(error, "menu descriptor exceeds the 255-item count limit");
        }
        if (resource.data.size() - cursor < 10U) {
            return fail(error, "menu descriptor item is truncated");
        }
        MenuItem item;
        item.source_cpu_address = base + static_cast<std::uint32_t>(cursor);
        item.title_address = title;
        item.callback = read_u32(&resource.data[cursor + 4U]);
        item.argument = read_u16(&resource.data[cursor + 8U]);
        try {
            candidate.items.push_back(item);
        } catch (const std::bad_alloc&) {
            return fail(error, "cannot allocate menu descriptor items");
        }
        cursor += 10U;
    }
    candidate.consumed_bytes = static_cast<std::uint32_t>(cursor - start);
    candidate.end_cpu_address = base + static_cast<std::uint32_t>(cursor);
    descriptor.items.swap(candidate.items);
    descriptor.source_cpu_address = candidate.source_cpu_address;
    descriptor.title_address = candidate.title_address;
    descriptor.min_width = candidate.min_width;
    descriptor.min_height = candidate.min_height;
    descriptor.callback6 = candidate.callback6;
    descriptor.callback10 = candidate.callback10;
    descriptor.flags = candidate.flags;
    descriptor.consumed_bytes = candidate.consumed_bytes;
    descriptor.end_cpu_address = candidate.end_cpu_address;
    error.clear();
    return true;
}

} // namespace ms5
