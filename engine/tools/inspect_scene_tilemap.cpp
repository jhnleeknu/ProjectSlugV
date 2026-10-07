#include "ms5/scene_map_resource.h"
#include <iostream>
int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "usage: inspect_scene_tilemap RESOURCE_MS5D\n"; return 2; }
    ms5::TilemapResource resource; std::string error;
    if (!ms5::load_scene_tilemap(argv[1],resource,error)) { std::cerr << error << '\n'; return 1; }
    std::cout << "{\"source_cpu_address\":" << resource.source.source_cpu_address << ",\"source_rom_offset\":" << resource.source.source_rom_offset
        << ",\"width\":" << resource.width << ",\"height\":" << resource.height << ",\"cells\":[";
    bool first = true;
    for (std::uint32_t column = 0; column < resource.width; ++column) {
        for (std::uint32_t row = 0; row < resource.height; ++row) {
            ms5::SceneTilemapCell cell;
            if (!ms5::read_scene_tilemap_cell(resource,column,row,cell,error)) { std::cerr << error << '\n'; return 1; }
            if (!first) std::cout << ','; first = false;
            std::cout << '[' << column << ',' << row << ',' << cell.source_cpu_address << ',' << cell.source_rom_offset << ',' << cell.word0 << ',' << cell.word1 << ']';
        }
    }
    std::cout << "]}\n"; return 0;
}
