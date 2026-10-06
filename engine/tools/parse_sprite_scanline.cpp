#include "ms5/sprite_scanline.h"

#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

bool parse_scanline(const std::string& text, std::uint16_t& result) {
    std::size_t position = 0;
    std::uint32_t base = 10;
    if (text.size() > 2U && text[0] == '0' &&
        (text[1] == 'x' || text[1] == 'X')) {
        position = 2;
        base = 16;
    }
    if (position == text.size()) {
        return false;
    }
    std::uint32_t value = 0;
    for (; position < text.size(); ++position) {
        const char character = text[position];
        std::uint32_t digit = 0;
        if (character >= '0' && character <= '9') {
            digit = static_cast<std::uint32_t>(character - '0');
        } else if (character >= 'a' && character <= 'f') {
            digit = static_cast<std::uint32_t>(character - 'a') + 10U;
        } else if (character >= 'A' && character <= 'F') {
            digit = static_cast<std::uint32_t>(character - 'A') + 10U;
        } else {
            return false;
        }
        if (digit >= base || value > (511U - digit) / base) {
            return false;
        }
        value = value * base + digit;
    }
    result = static_cast<std::uint16_t>(value);
    return true;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: parse_sprite_scanline INPUT OUTPUT SCANLINE\n"
                  << "scanline: decimal or 0x hexadecimal, 0..511\n"
                  << "input/output: exactly 0x11000 bytes of big-endian VRAM words\n";
        return 2;
    }
    std::uint16_t scanline = 0;
    if (!parse_scanline(argv[3], scanline)) {
        std::cerr << "invalid scanline\n";
        return 2;
    }
    const std::string input_path(argv[1]);
    const std::string output_path(argv[2]);
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
    std::ifstream input(input_path.c_str(), std::ios::binary);
    if (!input) {
        std::cerr << "cannot open input\n";
        return 1;
    }
    std::vector<unsigned char> bytes(0x11000U);
    input.read(reinterpret_cast<char*>(&bytes[0]),
               static_cast<std::streamsize>(bytes.size()));
    if (input.gcount() != static_cast<std::streamsize>(bytes.size()) ||
        input.bad()) {
        std::cerr << "input must contain exactly 0x11000 bytes\n";
        return 1;
    }
    char extra = 0;
    if (input.get(extra) || !input.eof() || input.bad()) {
        std::cerr << "input must contain exactly 0x11000 bytes\n";
        return 1;
    }
    std::vector<std::uint16_t> vram(0x8800U);
    for (std::size_t index = 0; index < vram.size(); ++index) {
        vram[index] = static_cast<std::uint16_t>(
            (static_cast<std::uint16_t>(bytes[index * 2U]) << 8) |
            bytes[index * 2U + 1U]);
    }
    std::string error;
    if (!ms5::parse_sprite_scanline(vram, scanline, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    for (std::size_t index = 0; index < vram.size(); ++index) {
        bytes[index * 2U] = static_cast<unsigned char>(vram[index] >> 8);
        bytes[index * 2U + 1U] = static_cast<unsigned char>(vram[index]);
    }
    // Fully validate and transform before opening the output for writing.
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&bytes[0]),
                 static_cast<std::streamsize>(bytes.size()));
    output.close();
    if (!output) {
        std::cerr << "cannot write output\n";
        return 1;
    }
    return 0;
}
