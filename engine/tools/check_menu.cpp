#include "ms5/menu_descriptor.h"

#include <iostream>
#include <limits>

namespace {

bool parse_address(const std::string& text, std::uint32_t& address) {
    std::size_t position = 0;
    unsigned int radix = 10;
    if (text.size() >= 2U && text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) {
        position = 2;
        radix = 16;
    }
    if (position == text.size()) {
        return false;
    }
    std::uint32_t value = 0;
    for (; position < text.size(); ++position) {
        const char character = text[position];
        unsigned int digit;
        if (character >= '0' && character <= '9') {
            digit = static_cast<unsigned int>(character - '0');
        } else if (radix == 16U && character >= 'a' && character <= 'f') {
            digit = static_cast<unsigned int>(character - 'a') + 10U;
        } else if (radix == 16U && character >= 'A' && character <= 'F') {
            digit = static_cast<unsigned int>(character - 'A') + 10U;
        } else {
            return false;
        }
        if (digit >= radix || value > (std::numeric_limits<std::uint32_t>::max() - digit) / radix) {
            return false;
        }
        value = value * radix + digit;
    }
    address = value;
    return true;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: check_menu INPUT_MS5D CPU_ADDRESS\n";
        return 2;
    }
    std::uint32_t address = 0;
    if (!parse_address(argv[2], address)) {
        std::cerr << "invalid CPU address: expected decimal or 0x hexadecimal uint32\n";
        return 2;
    }
    ms5::FixedDataResource resource;
    ms5::MenuDescriptor descriptor;
    std::string error;
    if (!ms5::load_fixed_data_resource(argv[1], resource, error) ||
        !ms5::decode_menu_descriptor(resource, address, descriptor, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::cout << "{\"source_cpu_address\":" << descriptor.source_cpu_address
              << ",\"title_address\":" << descriptor.title_address
              << ",\"min_width\":" << static_cast<unsigned int>(descriptor.min_width)
              << ",\"min_height\":" << static_cast<unsigned int>(descriptor.min_height)
              << ",\"callback6\":" << descriptor.callback6
              << ",\"callback10\":" << descriptor.callback10
              << ",\"flags\":" << descriptor.flags
              << ",\"end_cpu_address\":" << descriptor.end_cpu_address
              << ",\"items\":[";
    for (std::size_t i = 0; i < descriptor.items.size(); ++i) {
        const ms5::MenuItem& item = descriptor.items[i];
        if (i != 0U) {
            std::cout << ',';
        }
        std::cout << "{\"source_cpu_address\":" << item.source_cpu_address
                  << ",\"title_address\":" << item.title_address
                  << ",\"callback\":" << item.callback
                  << ",\"argument\":" << item.argument << '}';
    }
    std::cout << "]}\n";
    return std::cout ? 0 : 1;
}
