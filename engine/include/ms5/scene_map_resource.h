#ifndef MS5_SCENE_MAP_RESOURCE_H
#define MS5_SCENE_MAP_RESOURCE_H
#include "ms5/fixed_data_resource.h"
namespace ms5 {
struct TilemapResource {
    FixedDataResource source;
    std::uint16_t width, height;
    TilemapResource() : width(0), height(0) {}
};
struct SceneTilemapCell {
    std::uint32_t source_cpu_address, source_rom_offset;
    std::uint16_t word0, word1;
    SceneTilemapCell() : source_cpu_address(0), source_rom_offset(0), word0(0), word1(0) {}
};
// Exact bank3 header/cells. Failure preserves resource or cell output.
bool decode_scene_tilemap(const FixedDataResource& source, TilemapResource& result, std::string& error);
bool load_scene_tilemap(const std::string& path, TilemapResource& result, std::string& error);
// Reads raw source directly; inconsistent cached dimensions are rejected.
bool read_scene_tilemap_cell(const TilemapResource& resource, std::uint32_t column, std::uint32_t row,
    SceneTilemapCell& result, std::string& error);
struct ScenePathCommand {
    std::uint32_t source_cpu_address, next_cpu_address;
    std::uint16_t opcode;
    std::vector<std::uint8_t> operands;
    ScenePathCommand() : source_cpu_address(0), next_cpu_address(0), opcode(0) {}
};
struct ScenePath {
    FixedDataResource source;
    std::vector<ScenePathCommand> commands;
    std::uint32_t terminal_cpu_address;
    std::uint16_t terminal_opcode;
    ScenePath() : terminal_cpu_address(0), terminal_opcode(0) {}
};
// Raw fixed-ROM syntax only. Branch operands are preserved without resolving
// pointers, executing handlers or establishing branch feasibility.
bool decode_scene_path(const FixedDataResource& source, ScenePath& result, std::string& error);
bool load_scene_path(const std::string& path, ScenePath& result, std::string& error);
}
#endif
