#include "ms5/scene_placement_resource.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& data, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(data[at])<<8)|data[at+1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& data, std::size_t at) {
    return (static_cast<std::uint32_t>(word(data,at))<<16)|word(data,at+2);
}
}
bool decode_scene_placement(const FixedDataResource& source, ScenePlacementResource& result, std::string& error) {
    const std::uint32_t base = source.source_cpu_address;
    if ((base&1U) || base >= 0x100000 || source.source_rom_offset != base || source.data.size() > 0x100000-base) {
        error = "scene placement requires an aligned fixed CPU/ROM first1MiB window"; return false;
    }
    try {
        ScenePlacementResource candidate; candidate.source = source; std::size_t cursor = 0;
        for (;;) {
            if (source.data.size()-cursor < 2) { error = "scene placement missing terminal or truncated gate"; return false; }
            const std::uint16_t gate = word(source.data,cursor);
            if (gate == 0xffff) {
                if (cursor+2 != source.data.size()) { error = "scene placement trailing bytes after terminal"; return false; }
                candidate.terminal_cpu_address = base+static_cast<std::uint32_t>(cursor);
                candidate.terminal_rom_offset = candidate.terminal_cpu_address;
                result.source.data.swap(candidate.source.data); result.records.swap(candidate.records);
                result.source.source_cpu_address = candidate.source.source_cpu_address; result.source.source_rom_offset = candidate.source.source_rom_offset;
                result.terminal_cpu_address = candidate.terminal_cpu_address; result.terminal_rom_offset = candidate.terminal_rom_offset;
                error.clear(); return true;
            }
            if (source.data.size()-cursor < 16) { error = "scene placement truncated16-byte record header"; return false; }
            const std::uint16_t length = word(source.data,cursor+2);
            if ((length&0x8001U) != 0) { error = "scene placement inline length must be even and below8000"; return false; }
            if (source.data.size()-cursor-16 < length) { error = "scene placement truncated inline payload"; return false; }
            ScenePlacementRecord record; record.source_cpu_address = base+static_cast<std::uint32_t>(cursor);
            record.source_rom_offset = record.source_cpu_address; record.gate = gate; record.inline_byte_count = length;
            record.x = word(source.data,cursor+4); record.y = word(source.data,cursor+6);
            record.bounds_pointer = longword(source.data,cursor+8); record.callback = longword(source.data,cursor+12);
            record.inline_data.assign(source.data.begin()+cursor+16,source.data.begin()+cursor+16+length);
            cursor += 16+length; record.next_cpu_address = base+static_cast<std::uint32_t>(cursor); record.next_rom_offset = record.next_cpu_address;
            candidate.records.push_back(record);
        }
    } catch (const std::bad_alloc&) { error = "cannot allocate scene placement decoding"; return false; }
}
bool load_scene_placement(const std::string& path, ScenePlacementResource& result, std::string& error) {
    FixedDataResource source; if (!load_fixed_data_resource(path,source,error)) return false;
    return decode_scene_placement(source,result,error);
}
}
