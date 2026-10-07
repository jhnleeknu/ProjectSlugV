#ifndef MS5_SCENE_PLACEMENT_RESOURCE_H
#define MS5_SCENE_PLACEMENT_RESOURCE_H
#include "ms5/fixed_data_resource.h"
namespace ms5 {
struct ScenePlacementRecord {
    std::uint32_t source_cpu_address, source_rom_offset, next_cpu_address, next_rom_offset;
    std::uint16_t gate, inline_byte_count, x, y;
    std::uint32_t bounds_pointer, callback;
    std::vector<std::uint8_t> inline_data;
    ScenePlacementRecord() : source_cpu_address(0), source_rom_offset(0), next_cpu_address(0), next_rom_offset(0),
        gate(0), inline_byte_count(0), x(0), y(0), bounds_pointer(0), callback(0) {}
};
struct ScenePlacementResource {
    FixedDataResource source;
    std::vector<ScenePlacementRecord> records;
    std::uint32_t terminal_cpu_address, terminal_rom_offset;
    ScenePlacementResource() : terminal_cpu_address(0), terminal_rom_offset(0) {}
};
// Read-only raw syntax used by1a414/1a470, not handler execution. Only gateffff
// terminates. Other gate bits, coordinate WORDs and pointers are uninterpreted.
// Bounds/callback pointers are not dereferenced. Inline lengths must be even
// and below8000; signed/odd native skip/copy paths are outside this decoder.
// Source is an aligned CPU=ROM first1MiB window ending exactly after terminal.
// The source copy owns its bytes; every failed decode/load preserves output.
bool decode_scene_placement(const FixedDataResource& source, ScenePlacementResource& result, std::string& error);
bool load_scene_placement(const std::string& path, ScenePlacementResource& result, std::string& error);
}
#endif
