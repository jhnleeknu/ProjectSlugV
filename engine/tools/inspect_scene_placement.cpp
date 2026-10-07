#include "ms5/scene_placement_resource.h"
#include <iomanip>
#include <iostream>
int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "usage: inspect_scene_placement RESOURCE_MS5D\n"; return 2; }
    ms5::ScenePlacementResource resource; std::string error;
    if (!ms5::load_scene_placement(argv[1],resource,error)) { std::cerr << error << '\n'; return 1; }
    std::cout << "{\"source_cpu_address\":" << resource.source.source_cpu_address << ",\"source_rom_offset\":" << resource.source.source_rom_offset << ",\"payload_size\":" << resource.source.data.size() << ",\"records\":[";
    for (std::size_t i = 0; i < resource.records.size(); ++i) {
        const ms5::ScenePlacementRecord& record = resource.records[i]; if (i != 0) std::cout << ',';
        std::cout << "{\"source_cpu_address\":" << record.source_cpu_address << ",\"source_rom_offset\":" << record.source_rom_offset
            << ",\"next_cpu_address\":" << record.next_cpu_address << ",\"next_rom_offset\":" << record.next_rom_offset
            << ",\"gate\":" << record.gate << ",\"inline_byte_count\":" << record.inline_byte_count << ",\"x\":" << record.x << ",\"y\":" << record.y
            << ",\"bounds_pointer\":" << record.bounds_pointer << ",\"callback\":" << record.callback << ",\"inline_hex\":\"";
        for (std::size_t j = 0; j < record.inline_data.size(); ++j) std::cout << std::hex << std::setfill('0') << std::setw(2) << static_cast<unsigned int>(record.inline_data[j]);
        std::cout << std::dec << "\"}";
    }
    std::cout << "],\"terminal_cpu_address\":" << resource.terminal_cpu_address << ",\"terminal_rom_offset\":" << resource.terminal_rom_offset << ",\"terminal_gate\":65535}\n"; return 0;
}
