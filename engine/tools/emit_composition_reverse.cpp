#include "ms5/sprite_composition.h"

#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

bool parse_word(const std::string& text, std::uint16_t& result) {
    std::size_t position = 0;
    std::uint32_t base = 10;
    if (text.size() > 2 && text[0] == '0' &&
        (text[1] == 'x' || text[1] == 'X')) {
        base = 16;
        position = 2;
    }
    if (position == text.size()) {
        return false;
    }
    std::uint32_t value = 0;
    for (; position < text.size(); ++position) {
        const char character = text[position];
        std::uint32_t digit;
        if (character >= '0' && character <= '9') {
            digit = static_cast<std::uint32_t>(character - '0');
        } else if (character >= 'a' && character <= 'f') {
            digit = static_cast<std::uint32_t>(character - 'a') + 10U;
        } else if (character >= 'A' && character <= 'F') {
            digit = static_cast<std::uint32_t>(character - 'A') + 10U;
        } else {
            return false;
        }
        if (digit >= base || value > (65535U - digit) / base) {
            return false;
        }
        value = value * base + digit;
    }
    result = static_cast<std::uint16_t>(value);
    return true;
}

void append_word(std::vector<std::uint8_t>& bytes, std::uint16_t value) {
    bytes.push_back(static_cast<std::uint8_t>(value >> 8));
    bytes.push_back(static_cast<std::uint8_t>(value));
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 10) {
        std::cerr << "usage: emit_composition_reverse INPUT OUTPUT U V STYLE FIRST LOWER CACHED MODE\n"
                  << "mode: normal or refresh\n"
                  << "numbers: decimal or 0x hexadecimal, 0..65535\n"
                  << "output: BE32 next slot followed by BE16 address/value pairs\n";
        return 2;
    }
    std::uint16_t numbers[6];
    for (int index = 0; index < 6; ++index) {
        if (!parse_word(argv[index + 3], numbers[index])) {
            std::cerr << "invalid numeric argument " << argv[index + 3] << '\n';
            return 2;
        }
    }
    const std::string mode(argv[9]);
    if (mode != "normal" && mode != "refresh") {
        std::cerr << "mode must be normal or refresh\n";
        return 2;
    }
    // CACHED remains a validated word in normal mode, although it is unused.
    if (numbers[5] > 380) {
        std::cerr << "cached_begin must be <= 380\n";
        return 1;
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
    const std::vector<std::uint8_t> bytes(
        (std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    if (input.bad()) {
        std::cerr << "cannot read input\n";
        return 1;
    }
    input.close();
    std::vector<ms5::SpriteWrite> writes;
    std::uint16_t next_slot = 0;
    std::string error;
    const bool success = mode == "refresh"
        ? ms5::emit_sprite_rectangle_reverse_refresh(
              bytes, numbers[0], numbers[1], numbers[2], numbers[3], numbers[4],
              numbers[5], writes, next_slot, error)
        : ms5::emit_sprite_rectangle_reverse(
              bytes, numbers[0], numbers[2], numbers[3], numbers[4],
              writes, next_slot, error);
    if (!success) {
        std::cerr << error << '\n';
        return 1;
    }
    std::vector<std::uint8_t> output_bytes;
    output_bytes.reserve(4 + writes.size() * 4);
    append_word(output_bytes, 0);
    append_word(output_bytes, next_slot);
    for (std::size_t index = 0; index < writes.size(); ++index) {
        append_word(output_bytes, writes[index].address);
        append_word(output_bytes, writes[index].value);
    }
    // Validate every parameter before opening and potentially truncating output.
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&output_bytes[0]),
                 static_cast<std::streamsize>(output_bytes.size()));
    output.close();
    if (!output) {
        std::cerr << "cannot write output\n";
        return 1;
    }
    return 0;
}
