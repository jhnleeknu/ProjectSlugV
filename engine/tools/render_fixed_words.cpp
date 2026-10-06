#include "ms5/fixed_renderer.h"
#include "ms5/palette_resource.h"

#include <fstream>
#include <iostream>
#include <iterator>
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

int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: render_fixed_words FIXED.ms5t WRITES.bin PALETTES.ms5p OUTPUT.bin\n";
        return 2;
    }
    const std::string output_path(argv[4]);
    for (int index = 1; index < 4; ++index) {
        if (same_file(argv[index], output_path)) {
            std::cerr << "input and output must be distinct files\n";
            return 1;
        }
    }
    ms5::TileResource tiles;
    std::vector<ms5::PaletteRecord> records;
    std::string error;
    if (!ms5::load_tile_resource(argv[1], tiles, error) ||
        !ms5::load_palette_resource(argv[3], records, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::vector<std::uint16_t> palette(256, 0);
    bool found_palette = false;
    for (std::size_t index = 0; index < records.size(); ++index) {
        if (records[index].id == 0x897U) {
            for (std::size_t color = 0; color < 16; ++color) {
                palette[color] = records[index].hardware_words[color];
            }
            found_palette = true;
            break;
        }
    }
    if (!found_palette) {
        std::cerr << "diagnostic fixture requires palette source ID 0x897\n";
        return 1;
    }
    std::ifstream input(argv[2], std::ios::binary);
    if (!input) {
        std::cerr << "cannot open writes input\n";
        return 1;
    }
    const std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(input)),
                                        std::istreambuf_iterator<char>());
    if (input.bad() || bytes.size() % 4 != 0) {
        std::cerr << "writes input must be readable big-endian address/value pairs\n";
        return 1;
    }
    input.close();
    std::vector<std::uint16_t> vram(1280, 0);
    for (std::size_t offset = 0; offset < bytes.size(); offset += 4) {
        const std::uint16_t address = static_cast<std::uint16_t>(
            (static_cast<std::uint16_t>(bytes[offset]) << 8) | bytes[offset + 1]);
        const std::uint16_t value = static_cast<std::uint16_t>(
            (static_cast<std::uint16_t>(bytes[offset + 2]) << 8) | bytes[offset + 3]);
        if (address < 0x7000U || address > 0x74ffU) {
            std::cerr << "fixed write address must be in 0x7000..0x74ff\n";
            return 1;
        }
        if ((value >> 12) != 0) {
            std::cerr << "diagnostic fixture supports only palette slot zero\n";
            return 1;
        }
        vram[address - 0x7000U] = value;
    }
    std::vector<std::uint16_t> frame(320 * 256, 0);
    if (!ms5::render_fixed_layer_words(tiles, vram, palette, frame, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::cerr << "warning: diagnostic fixture maps source palette 0x897 to slot zero; mapping is grounded in the original warning registration table\n";
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 1;
    }
    for (std::size_t index = 0; index < frame.size(); ++index) {
        const char word[2] = {
            static_cast<char>(frame[index] >> 8),
            static_cast<char>(frame[index] & 0xffU)
        };
        output.write(word, sizeof(word));
    }
    output.close();
    if (!output) {
        std::cerr << "cannot write output\n";
        return 1;
    }
    return 0;
}
