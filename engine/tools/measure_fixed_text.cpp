#include "ms5/fixed_data_resource.h"
#include "ms5/fixed_text.h"

#include <iostream>
#include <string>
#include <vector>

namespace {

bool parse_integer(const std::string& text, std::uint32_t maximum,
                   std::uint32_t& result) {
    unsigned int base = 10;
    std::size_t start = 0;
    if (text.size() >= 2 && text[0] == '0' &&
        (text[1] == 'x' || text[1] == 'X')) {
        base = 16;
        start = 2;
    }
    if (start == text.size()) {
        return false;
    }
    std::uint32_t value = 0;
    for (std::size_t index = start; index < text.size(); ++index) {
        const char c = text[index];
        unsigned int digit;
        if (c >= '0' && c <= '9') {
            digit = static_cast<unsigned int>(c - '0');
        } else if (base == 16 && c >= 'a' && c <= 'f') {
            digit = static_cast<unsigned int>(c - 'a') + 10U;
        } else if (base == 16 && c >= 'A' && c <= 'F') {
            digit = static_cast<unsigned int>(c - 'A') + 10U;
        } else {
            return false;
        }
        if (digit >= base || digit > maximum || value > (maximum - digit) / base) {
            return false;
        }
        value = value * base + digit;
    }
    result = value;
    return true;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: measure_fixed_text INPUT_MS5D CPU_ADDRESS STYLE LINE\n";
        return 2;
    }
    std::uint32_t address;
    std::uint32_t style;
    std::uint32_t line;
    if (!parse_integer(argv[2], 0xffffffffU, address) ||
        !parse_integer(argv[3], 0xffffU, style) ||
        !parse_integer(argv[4], 0xffffU, line)) {
        std::cerr << "address, style and line must be decimal or 0x-prefixed integers in range\n";
        return 1;
    }
    ms5::FixedDataResource resource;
    std::string error;
    if (!ms5::load_fixed_data_resource(argv[1], resource, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    if (address < resource.source_cpu_address ||
        address - resource.source_cpu_address >= resource.data.size()) {
        std::cerr << "CPU address must lie within the fixed data resource\n";
        return 1;
    }
    const std::size_t offset = address - resource.source_cpu_address;
    const std::vector<std::uint8_t> script(resource.data.begin() + offset,
                                         resource.data.end());
    ms5::FixedTextMeasure measurement;
    if (!ms5::measure_fixed_text(script, static_cast<std::uint16_t>(style),
                                 static_cast<std::uint16_t>(line), measurement, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::cout << "{\"glyph_count\":" << measurement.glyph_count
              << ",\"style\":" << measurement.style
              << ",\"line\":" << measurement.line
              << ",\"end_cpu_address\":" << address + measurement.consumed_bytes
              << "}\n";
    return std::cout ? 0 : 1;
}
