#include "ms5/fixed_renderer.h"
#include "ms5/fixed_text.h"
#include "ms5/hardware_color.h"
#include "ms5/palette_resource.h"
#include "ms5/text_resource.h"

#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

bool same_file(const std::string& first, const std::string& second) {
    struct stat first_stat;
    struct stat second_stat;
    return first == second ||
        (stat(first.c_str(), &first_stat) == 0 &&
         stat(second.c_str(), &second_stat) == 0 &&
         first_stat.st_dev == second_stat.st_dev &&
         first_stat.st_ino == second_stat.st_ino);
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: render_text_scene TEXT.ms5x FIXED.ms5t PALETTES.ms5p OUTPUT.ppm\n";
        return 2;
    }
    const std::string output_path(argv[4]);
    for (int index = 1; index < 4; ++index) {
        if (same_file(argv[index], output_path)) {
            std::cerr << "input and output must be distinct files\n";
            return 1;
        }
    }
    ms5::TextResource text;
    ms5::TileResource tiles;
    std::vector<ms5::PaletteRecord> records;
    std::string error;
    if (!ms5::load_text_resource(argv[1], text, error) ||
        !ms5::load_tile_resource(argv[2], tiles, error) ||
        !ms5::load_palette_resource(argv[3], records, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::vector<std::uint16_t> palette(256, 0);
    bool bound[16] = {};
    for (std::size_t i = 0; i < text.bindings.size(); ++i) {
        const ms5::TextPaletteBinding& binding = text.bindings[i];
        bool found = false;
        for (std::size_t j = 0; j < records.size(); ++j) {
            if (records[j].id == binding.source_id) {
                for (unsigned int color = 0; color < 16; ++color) {
                    palette[binding.slot * 16U + color] = records[j].hardware_words[color];
                }
                found = true;
                break;
            }
        }
        if (!found) {
            std::cerr << "text binding references missing palette source ID "
                      << binding.source_id << '\n';
            return 1;
        }
        bound[binding.slot] = true;
    }
    std::vector<ms5::FixedWrite> writes;
    if (!ms5::trace_fixed_text(text.script, 0, 0, writes, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::vector<std::uint16_t> vram(1280, 0);
    for (std::size_t i = 0; i < writes.size(); ++i) {
        const ms5::FixedWrite& write = writes[i];
        if (write.address < 0x7000U || write.address > 0x74ffU) {
            std::cerr << "fixed write address must be in 0x7000..0x74ff\n";
            return 1;
        }
        if (!bound[write.value >> 12]) {
            std::cerr << "fixed write references an unbound palette slot\n";
            return 1;
        }
        vram[write.address - 0x7000U] = write.value;
    }
    std::vector<std::uint16_t> frame(320 * 256, 0);
    if (!ms5::render_fixed_layer_words(tiles, vram, palette, frame, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    // Diagnostic single frame: no boot state, prior VRAM or prior framebuffer.
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 1;
    }
    output << "P6\n320 256\n255\n";
    for (std::size_t i = 0; i < frame.size(); ++i) {
        const ms5::RgbColor rgb = ms5::hardware_color_to_rgb(frame[i], false);
        const char bytes[3] = {
            static_cast<char>(rgb.red), static_cast<char>(rgb.green),
            static_cast<char>(rgb.blue)
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
