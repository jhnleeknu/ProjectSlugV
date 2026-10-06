#include "ms5/palette_control.h"

#include <cerrno>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

bool parse_number(const char* text, unsigned long maximum,
                  unsigned long& value) {
    if (text[0] == '\0' || text[0] == '-' || text[0] == '+' ||
        text[0] == ' ' || text[0] == '\t' || text[0] == '\n' ||
        text[0] == '\r' || text[0] == '\v' || text[0] == '\f') {
        return false;
    }
    char* end = NULL;
    errno = 0;
    value = std::strtoul(text, &end, 0);
    return errno == 0 && end != text && *end == '\0' && value <= maximum;
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

void usage() {
    std::cerr << "usage: control_palette effect INPUT OUTPUT R G B DURATION\n"
              << "       control_palette blend INPUT OUTPUT SLOT TARGET WEIGHT\n";
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        usage();
        return 2;
    }
    const std::string operation(argv[1]);
    const bool effect = operation == "effect";
    if ((!effect && operation != "blend") || argc != (effect ? 8 : 7)) {
        usage();
        return 2;
    }
    unsigned long values[4] = {0, 0, 0, 0};
    const unsigned long effect_limits[4] = {65535, 65535, 65535, 255};
    const unsigned long blend_limits[3] = {255, 65535, 255};
    for (int argument = 0; argument < (effect ? 4 : 3); ++argument) {
        const unsigned long maximum = effect ? effect_limits[argument] :
            blend_limits[argument];
        if (!parse_number(argv[4 + argument], maximum, values[argument])) {
            std::cerr << "invalid palette control argument\n";
            return 2;
        }
    }
    const std::string input_path(argv[2]);
    const std::string output_path(argv[3]);
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
    std::string error;
    const bool succeeded = effect ?
        ms5::set_palette_effect(ram, static_cast<std::uint16_t>(values[0]),
                                static_cast<std::uint16_t>(values[1]),
                                static_cast<std::uint16_t>(values[2]),
                                static_cast<std::uint8_t>(values[3]), error) :
        ms5::set_palette_blend(ram, static_cast<std::uint8_t>(values[0]),
                               static_cast<std::uint16_t>(values[1]),
                               static_cast<std::uint8_t>(values[2]), error);
    if (!succeeded) {
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
