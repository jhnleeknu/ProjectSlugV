#include "ms5/scene_map_resource.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& data, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(data[at]) << 8) | data[at + 1]);
}
bool tilemap_header(const FixedDataResource& source, std::uint16_t& width, std::uint16_t& height, std::string& error) {
    const std::uint32_t cpu = source.source_cpu_address;
    if (cpu < 0x200000 || cpu >= 0x2ffff0 || (cpu & 1U) || source.source_rom_offset != cpu + 0x100000 ||
        source.data.size() < 4 || source.data.size() > 0x2ffff0 - cpu) { error = "tilemap requires exact aligned bank3 window"; return false; }
    width = word(source.data,0); height = word(source.data,2);
    const std::uint64_t size = 4U + 4ULL*width*height;
    if (width == 0 || height == 0 || size != source.data.size()) { error = "tilemap dimensions or exact cell span invalid"; return false; }
    return true;
}
void publish_source(FixedDataResource& result, FixedDataResource& next) {
    result.data.swap(next.data); result.source_cpu_address = next.source_cpu_address; result.source_rom_offset = next.source_rom_offset;
}
}
bool decode_scene_tilemap(const FixedDataResource& source, TilemapResource& result, std::string& error) {
    std::uint16_t width = 0, height = 0;
    if (!tilemap_header(source,width,height,error)) return false;
    try {
        FixedDataResource next = source; publish_source(result.source,next); result.width = width; result.height = height;
        error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate tilemap resource"; return false; }
}
bool load_scene_tilemap(const std::string& path, TilemapResource& result, std::string& error) {
    FixedDataResource source;
    return load_banked_data_resource(path,source,error) && decode_scene_tilemap(source,result,error);
}
bool read_scene_tilemap_cell(const TilemapResource& resource, std::uint32_t column, std::uint32_t row,
    SceneTilemapCell& result, std::string& error) {
    std::uint16_t width = 0, height = 0;
    if (!tilemap_header(resource.source,width,height,error)) return false;
    if (resource.width != width || resource.height != height || column >= width || row >= height) { error = "tilemap cache or cell coordinates invalid"; return false; }
    const std::size_t offset = 4 + 4*(static_cast<std::size_t>(column)*height + row);
    SceneTilemapCell next; next.source_cpu_address = resource.source.source_cpu_address + static_cast<std::uint32_t>(offset);
    next.source_rom_offset = resource.source.source_rom_offset + static_cast<std::uint32_t>(offset);
    next.word0 = word(resource.source.data,offset); next.word1 = word(resource.source.data,offset + 2);
    result = next; error.clear(); return true;
}
bool decode_scene_path(const FixedDataResource& source, ScenePath& result, std::string& error) {
    const std::uint32_t cpu = source.source_cpu_address;
    if (cpu == 0 || (cpu & 1U) || cpu >= 0x100000 || source.source_rom_offset != cpu || source.data.size() < 2 ||
        source.data.size() > 65536 || source.data.size() > 0x100000 - cpu) { error = "path requires aligned exact fixed-ROM window"; return false; }
    try {
        ScenePath next; next.source = source;
        const unsigned int lengths[8] = {4,12,12,12,12,12,6,4};
        std::size_t cursor = 0;
        while (cursor + 2 <= source.data.size()) {
            const std::uint16_t opcode = word(source.data,cursor);
            if (opcode & 0x8000U) {
                if (cursor + 2 != source.data.size()) { error = "path has bytes after terminal"; return false; }
                next.terminal_cpu_address = cpu + static_cast<std::uint32_t>(cursor); next.terminal_opcode = opcode;
                publish_source(result.source,next.source); result.commands.swap(next.commands);
                result.terminal_cpu_address = next.terminal_cpu_address; result.terminal_opcode = next.terminal_opcode;
                error.clear(); return true;
            }
            if (opcode > 0x1c || (opcode & 3U)) { error = "unsupported path opcode"; return false; }
            const std::size_t length = lengths[opcode / 4];
            if (source.data.size() - cursor - 2 < length) { error = "path operand truncated"; return false; }
            ScenePathCommand command; command.source_cpu_address = cpu + static_cast<std::uint32_t>(cursor); command.opcode = opcode;
            command.operands.assign(source.data.begin() + cursor + 2,source.data.begin() + cursor + 2 + length);
            cursor += 2 + length; command.next_cpu_address = cpu + static_cast<std::uint32_t>(cursor); next.commands.push_back(command);
        }
        error = "path terminal missing or truncated"; return false;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene path resource"; return false; }
}
bool load_scene_path(const std::string& path, ScenePath& result, std::string& error) {
    FixedDataResource source;
    return load_fixed_data_resource(path,source,error) && decode_scene_path(source,result,error);
}
}
