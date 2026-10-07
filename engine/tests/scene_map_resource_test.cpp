#include "ms5/scene_map_resource.h"
#include <cassert>
#include <iostream>
namespace {
void append(std::vector<std::uint8_t>& data, unsigned int value) {
    data.push_back(static_cast<std::uint8_t>(value >> 8)); data.push_back(static_cast<std::uint8_t>(value));
}
bool source_same(const ms5::FixedDataResource& a, const ms5::FixedDataResource& b) {
    return a.source_cpu_address == b.source_cpu_address && a.source_rom_offset == b.source_rom_offset && a.data == b.data;
}
}
int main() {
    std::string error;
    ms5::FixedDataResource raw; raw.source_cpu_address = 0x200100; raw.source_rom_offset = 0x300100;
    append(raw.data,2); append(raw.data,3);
    for (unsigned int i = 0; i < 12; ++i) append(raw.data,0x1000 + i);
    ms5::TilemapResource map;
    assert(ms5::decode_scene_tilemap(raw,map,error)); assert(map.width == 2 && map.height == 3 && source_same(map.source,raw));
    ms5::SceneTilemapCell cell;
    assert(ms5::read_scene_tilemap_cell(map,1,2,cell,error));
    assert(cell.source_cpu_address == 0x200118 && cell.source_rom_offset == 0x300118 && cell.word0 == 0x100a && cell.word1 == 0x100b);
    // Reads borrowed raw cells, rather than caching their contents.
    map.source.data[24] = 0xab;
    assert(ms5::read_scene_tilemap_cell(map,1,2,cell,error)); assert(cell.word0 == 0xab0a);
    const ms5::SceneTilemapCell saved_cell = cell;
    map.width = 3;
    assert(!ms5::read_scene_tilemap_cell(map,0,0,cell,error));
    assert(cell.word0 == saved_cell.word0 && cell.word1 == saved_cell.word1 && cell.source_cpu_address == saved_cell.source_cpu_address && cell.source_rom_offset == saved_cell.source_rom_offset);
    map.width = 2;
    assert(!ms5::read_scene_tilemap_cell(map,2,0,cell,error)); assert(!ms5::read_scene_tilemap_cell(map,0,3,cell,error));
    const ms5::TilemapResource saved = map;
    for (unsigned int mutation = 0; mutation < 6; ++mutation) {
        ms5::FixedDataResource bad = raw;
        if (mutation == 0) bad.source_rom_offset = 0x200100;
        if (mutation == 1) bad.source_cpu_address = 0x200101;
        if (mutation == 2) { bad.source_cpu_address = 0x2fffee; bad.source_rom_offset = 0x3fffee; }
        if (mutation == 3) bad.data[1] = 0;
        if (mutation == 4) bad.data.push_back(0);
        if (mutation == 5) { bad.data[0] = bad.data[1] = bad.data[2] = bad.data[3] = 255; }
        assert(!ms5::decode_scene_tilemap(bad,map,error));
        assert(source_same(map.source,saved.source) && map.width == saved.width && map.height == saved.height);
    }
    ms5::FixedDataResource path_source; path_source.source_cpu_address = path_source.source_rom_offset = 0x50000;
    const unsigned int sizes[8] = {4,12,12,12,12,12,6,4};
    for (unsigned int i = 0; i < 8; ++i) {
        append(path_source.data,i*4);
        for (unsigned int j = 0; j < sizes[i]; ++j) path_source.data.push_back(255); // External branch addresses remain raw.
    }
    append(path_source.data,0x8000);
    ms5::ScenePath path;
    assert(ms5::decode_scene_path(path_source,path,error));
    assert(path.commands.size() == 8 && path.terminal_opcode == 0x8000 && path.terminal_cpu_address == 0x5005a);
    std::uint32_t cursor = 0x50000;
    for (unsigned int i = 0; i < 8; ++i) {
        assert(path.commands[i].source_cpu_address == cursor && path.commands[i].opcode == i*4 && path.commands[i].operands.size() == sizes[i]);
        cursor += 2 + sizes[i]; assert(path.commands[i].next_cpu_address == cursor);
    }
    const ms5::ScenePath before = path;
    for (unsigned int mutation = 0; mutation < 7; ++mutation) {
        ms5::FixedDataResource bad = path_source;
        if (mutation == 0) bad.data.push_back(0);
        if (mutation == 1) bad.data.pop_back();
        if (mutation == 2) bad.data.resize(10);
        if (mutation == 3) bad.data[1] = 1;
        if (mutation == 4) { bad.source_cpu_address = 0x200000; bad.source_rom_offset = 0x300000; }
        if (mutation == 5) bad.source_rom_offset += 2;
        if (mutation == 6) bad.data.resize(65538,0);
        assert(!ms5::decode_scene_path(bad,path,error));
        assert(source_same(path.source,before.source) && path.commands.size() == before.commands.size() && path.commands[7].operands == before.commands[7].operands && path.terminal_opcode == before.terminal_opcode && path.terminal_cpu_address == before.terminal_cpu_address);
    }
    ms5::FixedDataResource terminal; terminal.source_cpu_address = terminal.source_rom_offset = 0xffffe; append(terminal.data,0xffff);
    assert(ms5::decode_scene_path(terminal,path,error)); assert(path.commands.empty() && path.terminal_cpu_address == 0xffffe);
    std::cout << "scene_map_resource_test: passed\n";
}
