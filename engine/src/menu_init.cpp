#include "ms5/menu_init.h"

#include "ms5/fixed_text.h"
#include "ms5/menu_descriptor.h"

#include <new>

namespace ms5 {
namespace {

void write_u32(std::vector<std::uint8_t>& ram, std::size_t offset,
               std::uint32_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 24);
    ram[offset + 1U] = static_cast<std::uint8_t>(value >> 16);
    ram[offset + 2U] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 3U] = static_cast<std::uint8_t>(value);
}

bool measure_title(const FixedDataResource& resource, std::uint32_t address,
                   std::uint16_t& style, std::uint16_t& line,
                   std::uint16_t& maximum, std::string& error) {
    if (address < resource.source_cpu_address ||
        address - resource.source_cpu_address >= resource.data.size()) {
        error = "menu title address is outside the fixed data resource";
        return false;
    }
    const std::size_t offset = address - resource.source_cpu_address;
    try {
        const std::vector<std::uint8_t> script(resource.data.begin() + offset,
                                              resource.data.end());
        FixedTextMeasure measurement;
        if (!measure_fixed_text(script, style, line, measurement, error)) {
            return false;
        }
        style = measurement.style;
        line = measurement.line;
        if (measurement.glyph_count > maximum) {
            maximum = measurement.glyph_count;
        }
    } catch (const std::bad_alloc&) {
        error = "cannot allocate menu title stream";
        return false;
    }
    return true;
}

} // namespace

bool initialize_menu(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& resource,
                     std::uint32_t descriptor_address,
                     std::uint16_t x, std::uint16_t y,
                     std::uint16_t initial_line, std::string& error) {
    if (ram.size() != 65536U) {
        error = "menu initialization requires exactly 65536 RAM bytes";
        return false;
    }
    MenuDescriptor descriptor;
    if (!decode_menu_descriptor(resource, descriptor_address, descriptor, error)) {
        return false;
    }
    std::uint16_t style = y;
    std::uint16_t line = initial_line;
    std::uint16_t maximum = 0;
    if (descriptor.title_address != 0U &&
        !measure_title(resource, descriptor.title_address, style, line,
                       maximum, error)) {
        return false;
    }
    for (std::size_t index = 0; index < descriptor.items.size(); ++index) {
        const std::uint32_t address = descriptor.items[index].title_address;
        if (address != 0U && address != UINT32_C(0xfffffffe) &&
            !measure_title(resource, address, style, line, maximum, error)) {
            return false;
        }
    }
    const unsigned int padding = (descriptor.flags & 0x000eU) != 0U ? 2U : 4U;
    const std::uint8_t width_candidate = static_cast<std::uint8_t>(
        (static_cast<unsigned int>(maximum) + padding) & 0xffU);
    const std::uint8_t height_candidate = static_cast<std::uint8_t>(
        (descriptor.items.size() + 2U) & 0xffU);
    const std::uint8_t width = width_candidate > descriptor.min_width ?
        width_candidate : descriptor.min_width;
    const std::uint8_t height = height_candidate > descriptor.min_height ?
        height_candidate : descriptor.min_height;

    write_u32(ram, 0x7f16U, 0x00003650U);
    ram[0x7f1aU] = 0;
    write_u32(ram, 0x7f0eU, 0x00107efeU);
    const std::size_t slot = 0x7efeU;
    write_u32(ram, slot, descriptor_address);
    ram[slot + 4U] = 0;
    ram[slot + 6U] = static_cast<std::uint8_t>(descriptor.items.size());
    ram[slot + 7U] = 0;
    ram[slot + 8U] = 0;
    ram[slot + 9U] = static_cast<std::uint8_t>(x);
    ram[slot + 10U] = static_cast<std::uint8_t>(y);
    ram[slot + 11U] = width;
    ram[slot + 12U] = height;
    ram[slot + 13U] = 3;
    ram[slot + 14U] = 0xffU;
    ram[slot + 15U] = 0;
    ram[0x7f1bU] = 1;
    error.clear();
    return true;
}

} // namespace ms5
