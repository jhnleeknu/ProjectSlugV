#include "ms5/palette_fill.h"

#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

bool parse_selector(const std::string& text, std::uint16_t& selector) {
    unsigned int base = 10;
    std::size_t first = 0;
    if (text.size() >= 2 && text[0] == '0' &&
        (text[1] == 'x' || text[1] == 'X')) {
        base = 16;
        first = 2;
    }
    if (first == text.size()) {
        return false;
    }
    unsigned int value = 0;
    for (std::size_t index = first; index < text.size(); ++index) {
        const char character = text[index];
        unsigned int digit;
        if (character >= '0' && character <= '9') {
            digit = static_cast<unsigned int>(character - '0');
        } else if (base == 16 && character >= 'a' && character <= 'f') {
            digit = static_cast<unsigned int>(character - 'a') + 10;
        } else if (base == 16 && character >= 'A' && character <= 'F') {
            digit = static_cast<unsigned int>(character - 'A') + 10;
        } else {
            return false;
        }
        if (digit >= base || value > (65535U - digit) / base) {
            return false;
        }
        value = value * base + digit;
    }
    selector = static_cast<std::uint16_t>(value);
    return true;
}

bool same_file(const std::string& left, const std::string& right) {
    struct stat left_stat;
    struct stat right_stat;
    return left == right ||
        (stat(left.c_str(), &left_stat) == 0 &&
         stat(right.c_str(), &right_stat) == 0 &&
         left_stat.st_dev == right_stat.st_dev &&
         left_stat.st_ino == right_stat.st_ino);
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: setup_palette_fill INPUT_RAM INPUT_FILL_MS5P OUTPUT_RAM SELECTOR\n";
        return 2;
    }
    std::uint16_t selector = 0;
    if (!parse_selector(argv[4], selector)) {
        std::cerr << "selector must be decimal or hexadecimal in 0..65535\n";
        return 2;
    }
    const std::string ram_path(argv[1]);
    const std::string resource_path(argv[2]);
    const std::string output_path(argv[3]);
    if (same_file(ram_path, output_path) ||
        same_file(resource_path, output_path)) {
        std::cerr << "RAM output must be distinct from both input files\n";
        return 1;
    }
    std::ifstream input(ram_path.c_str(), std::ios::binary | std::ios::ate);
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
    std::vector<ms5::PaletteRecord> records;
    std::string error;
    if (!ms5::load_palette_resource(resource_path, records, error) ||
        !ms5::setup_palette_fill(ram, records, selector, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open RAM output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&ram[0]), 65536);
    output.close();
    if (!output) {
        std::cerr << "cannot write RAM output\n";
        return 1;
    }
    return 0;
}
