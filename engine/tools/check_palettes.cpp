#include "ms5/palette_resource.h"

#include <iomanip>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: check_palettes RESOURCE.ms5p\n";
        return 2;
    }
    std::vector<ms5::PaletteRecord> records;
    std::string error;
    if (!ms5::load_palette_resource(argv[1], records, error)) {
        std::cerr << argv[1] << ": " << error << '\n';
        return 1;
    }
    std::cout << argv[1] << ": palettes=" << records.size() << '\n';
    for (std::size_t i = 0; i < records.size(); ++i) {
        std::cout << "id=" << std::dec << records[i].id << " hardware=";
        for (unsigned int word = 0; word < 16; ++word) {
            if (word != 0) {
                std::cout << ' ';
            }
            std::cout << std::hex << std::setfill('0') << std::setw(4)
                      << records[i].hardware_words[word];
        }
        std::cout << '\n';
    }
    return 0;
}
