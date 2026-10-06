#include "ms5/hardware_color.h"

#include <fstream>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/stat.h>

static bool same_file(const std::string& first, const std::string& second) {
    struct stat first_stat;
    struct stat second_stat;
    return first == second ||
        (stat(first.c_str(), &first_stat) == 0 &&
         stat(second.c_str(), &second_stat) == 0 &&
         first_stat.st_dev == second_stat.st_dev &&
         first_stat.st_ino == second_stat.st_ino);
}

static int convert_words(const std::string& input_path,
                         const std::string& output_path, bool shadow) {
    if (same_file(input_path, output_path)) {
        std::cerr << "input and output must be distinct files\n";
        return 1;
    }
    std::ifstream input(input_path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        std::cerr << "cannot open words input\n";
        return 1;
    }
    const std::streamoff input_length = input.tellg();
    if (input_length <= 0 || input_length % 2 != 0) {
        std::cerr << "input must contain nonempty big-endian 16-bit words\n";
        return 1;
    }
    const std::uintmax_t length = static_cast<std::uintmax_t>(input_length);
    const std::uintmax_t word_count = length / 2;
    const std::vector<std::uint8_t> empty_bytes;
    if (length > std::numeric_limits<std::size_t>::max() ||
        length > static_cast<std::uintmax_t>(std::numeric_limits<std::streamsize>::max()) ||
        length > empty_bytes.max_size() ||
        word_count > std::numeric_limits<std::size_t>::max() / 3 ||
        word_count > static_cast<std::uintmax_t>(std::numeric_limits<std::streamsize>::max()) / 3 ||
        word_count > empty_bytes.max_size() / 3) {
        std::cerr << "input or RGB output is too large\n";
        return 1;
    }
    const std::size_t input_size = static_cast<std::size_t>(length);
    const std::size_t output_size = static_cast<std::size_t>(word_count) * 3;
    std::vector<std::uint8_t> bytes(input_size);
    input.seekg(0, std::ios::beg);
    input.read(reinterpret_cast<char*>(&bytes[0]), static_cast<std::streamsize>(input_size));
    if (!input) {
        std::cerr << "cannot read words input\n";
        return 1;
    }
    input.close();
    std::vector<std::uint8_t> rgb(output_size);
    for (std::size_t offset = 0; offset < input_size; offset += 2) {
        const std::uint16_t word = static_cast<std::uint16_t>(
            (static_cast<unsigned int>(bytes[offset]) << 8) | bytes[offset + 1]);
        const ms5::RgbColor color = ms5::hardware_color_to_rgb(word, shadow);
        const std::size_t rgb_offset = (offset / 2) * 3;
        rgb[rgb_offset] = color.red;
        rgb[rgb_offset + 1] = color.green;
        rgb[rgb_offset + 2] = color.blue;
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open RGB output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&rgb[0]),
                 static_cast<std::streamsize>(output_size));
    output.close();
    if (!output) {
        std::cerr << "cannot write RGB output\n";
        return 1;
    }
    return 0;
}

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: convert_color_words INPUT_BE_WORDS OUTPUT_RGB MODE (normal|shadow)\n";
        return 2;
    }
    const std::string mode(argv[3]);
    if (mode != "normal" && mode != "shadow") {
        std::cerr << "mode must be normal or shadow\n";
        return 2;
    }
    try {
        return convert_words(argv[1], argv[2], mode == "shadow");
    } catch (const std::bad_alloc&) {
        std::cerr << "cannot allocate conversion buffers\n";
    } catch (const std::length_error&) {
        std::cerr << "input or RGB output is too large\n";
    }
    return 1;
}
