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
                   std::uint16_t& maximum, std::string& error, std::uint32_t& d3) {
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
        d3 = (measurement.line_reset ? 0U : (d3 & 0xffff0000U)) | line;
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

bool configure_menu_slot(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& resource,
                         std::uint32_t slot_address,
                         std::uint32_t descriptor_address,
                         std::uint16_t x, std::uint16_t y,
                         std::uint16_t initial_line, std::string& error,
                         std::uint16_t* final_line,
                         std::uint16_t* final_style, std::uint32_t* d3) {
    if (ram.size() != 65536U) {
        error = "menu initialization requires exactly 65536 RAM bytes";
        return false;
    }
    if (slot_address < UINT32_C(0x107e0e) ||
        slot_address > UINT32_C(0x107efe) ||
        (slot_address - UINT32_C(0x107e0e)) % 16U != 0U) {
        error = "menu slot address is outside the aligned slot array";
        return false;
    }
    MenuDescriptor descriptor;
    if (!decode_menu_descriptor(resource, descriptor_address, descriptor, error)) {
        return false;
    }
    std::uint16_t style = y;
    std::uint16_t line = initial_line;
    std::uint16_t maximum = 0;
    std::uint32_t pending_d3 = (d3 == NULL ? 0U : (*d3 & 0xffff0000U)) | initial_line;
    if (descriptor.title_address != 0U &&
        !measure_title(resource, descriptor.title_address, style, line,
                       maximum, error, pending_d3)) {
        return false;
    }
    for (std::size_t index = 0; index < descriptor.items.size(); ++index) {
        const std::uint32_t address = descriptor.items[index].title_address;
        if (address != 0U && address != UINT32_C(0xfffffffe) &&
            !measure_title(resource, address, style, line, maximum, error, pending_d3)) {
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

    const std::size_t slot = slot_address - UINT32_C(0x100000);
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
    if (final_line != NULL) *final_line = line;
    if (final_style != NULL) *final_style = style;
    if (d3 != NULL) *d3 = pending_d3;
    error.clear();
    return true;
}

bool initialize_menu(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& resource,
                     std::uint32_t descriptor_address,
                     std::uint16_t x, std::uint16_t y,
                     std::uint16_t initial_line, std::string& error,
                     std::uint16_t* final_line,
                     std::uint16_t* final_style, std::uint32_t* d3) {
    if (!configure_menu_slot(ram, resource, UINT32_C(0x107efe),
                             descriptor_address, x, y, initial_line, error, final_line, final_style, d3)) {
        return false;
    }
    write_u32(ram, 0x7f16U, 0x00003650U);
    ram[0x7f1aU] = 0;
    write_u32(ram, 0x7f0eU, 0x00107efeU);
    ram[0x7f1bU] = 1;
    return true;
}

} // namespace ms5
