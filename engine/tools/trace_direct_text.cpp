#include "ms5/fixed_data_resource.h"
#include "ms5/fixed_text.h"

#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

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
    if (argc != 6) {
        std::cerr << "usage: trace_direct_text INPUT_MS5D CPU_ADDRESS CURSOR STYLE OUTPUT_WRITES\n";
        return 2;
    }
    std::uint32_t address;
    std::uint32_t cursor;
    std::uint32_t style;
    if (!parse_integer(argv[2], 0xffffffffU, address) ||
        !parse_integer(argv[3], 0xffffU, cursor) ||
        !parse_integer(argv[4], 0xffffU, style)) {
        std::cerr << "address, cursor and style must be decimal or 0x-prefixed integers in range\n";
        return 1;
    }
    const std::string input_path(argv[1]);
    const std::string output_path(argv[5]);
    struct stat input_stat;
    struct stat output_stat;
    if (input_path == output_path ||
        (stat(input_path.c_str(), &input_stat) == 0 &&
         stat(output_path.c_str(), &output_stat) == 0 &&
         input_stat.st_dev == output_stat.st_dev &&
         input_stat.st_ino == output_stat.st_ino)) {
        std::cerr << "input and output must be distinct files\n";
        return 1;
    }
    ms5::FixedDataResource resource;
    std::string error;
    if (!ms5::load_fixed_data_resource(input_path, resource, error)) {
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
    std::vector<ms5::VideoPortWrite> writes;
    if (!ms5::trace_direct_fixed_text(script, static_cast<std::uint16_t>(cursor),
                                      static_cast<std::uint16_t>(style), writes, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 1;
    }
    // Diagnostic records: byte size, BE32 CPU port address, BE32 value.
    for (std::size_t index = 0; index < writes.size(); ++index) {
        const ms5::VideoPortWrite& write = writes[index];
        const char bytes[9] = {
            static_cast<char>(write.size),
            static_cast<char>((write.address >> 24) & 0xffU),
            static_cast<char>((write.address >> 16) & 0xffU),
            static_cast<char>((write.address >> 8) & 0xffU),
            static_cast<char>(write.address & 0xffU),
            static_cast<char>((write.value >> 24) & 0xffU),
            static_cast<char>((write.value >> 16) & 0xffU),
            static_cast<char>((write.value >> 8) & 0xffU),
            static_cast<char>(write.value & 0xffU)
        };
        output.write(bytes, sizeof(bytes));
    }
    output.close();
    if (!output) {
        std::cerr << "cannot write output\n";
        return 1;
    }
    return 0;
}
