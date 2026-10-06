#include "ms5/palette_frame.h"

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

} // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: step_palette_frame INPUT_RAM INPUT_MS5P OUTPUT_RAM\n";
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
        !ms5::step_palette_frame(ram, records, error)) {
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
