#include "ms5/control_request.h"

#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

bool same_file(const std::string& left, const std::string& right) {
    struct stat left_stat;
    struct stat right_stat;
    return left == right ||
        (stat(left.c_str(), &left_stat) == 0 &&
         stat(right.c_str(), &right_stat) == 0 &&
         left_stat.st_dev == right_stat.st_dev &&
         left_stat.st_ino == right_stat.st_ino);
}

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
    const bool trace_d1 = argc > 1 && std::string(argv[1]) == "--d1";
    std::uint32_t d1 = 0U;
    if (trace_d1) {
        if (argc != 5) {
            std::cerr << "usage: read_control_request [--d1 INPUT_D1] INPUT_RAM OUTPUT_MASK\n";
            return 2;
        }
        if (!parse_integer(argv[2], 0xffffffffU, d1)) {
            std::cerr << "INPUT_D1 must be decimal or 0x-prefixed uint32\n";
            return 1;
        }
        argc -= 2;
        argv += 2;
    }
    if (argc != 3) {
        std::cerr << "usage: read_control_request [--d1 INPUT_D1] INPUT_RAM OUTPUT_MASK\n";
        return 2;
    }
    const std::string input_path(argv[1]);
    const std::string output_path(argv[2]);
    if (same_file(input_path, output_path)) {
        std::cerr << "input and output must be distinct files\n";
        return 1;
    }
    std::ifstream input(input_path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        std::cerr << "cannot open RAM input\n";
        return 1;
    }
    if (input.tellg() != 65536) {
        std::cerr << "RAM input must contain exactly 65536 bytes\n";
        return 1;
    }
    input.seekg(0, std::ios::beg);
    std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]), 65536)) {
        std::cerr << "cannot read RAM input\n";
        return 1;
    }
    input.close();
    std::uint8_t result = 0;
    std::string error;
    if (!ms5::read_control_request(ram, result, error, trace_d1 ? &d1 : NULL)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open mask output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&result), 1);
    output.close();
    if (!output) {
        std::cerr << "cannot write mask output\n";
        return 1;
    }
    if (trace_d1) {
        std::cout << "{\"d1\":" << d1 << "}\n";
    }
    return 0;
}
