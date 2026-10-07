#include "ms5/scene_map_resource.h"
#include <iomanip>
#include <iostream>
int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "usage: inspect_scene_path RESOURCE_MS5D\n"; return 2; }
    ms5::ScenePath resource; std::string error;
    if (!ms5::load_scene_path(argv[1],resource,error)) { std::cerr << error << '\n'; return 1; }
    std::cout << "{\"source_cpu_address\":" << resource.source.source_cpu_address << ",\"source_rom_offset\":" << resource.source.source_rom_offset << ",\"commands\":[";
    for (std::size_t i = 0; i < resource.commands.size(); ++i) {
        const ms5::ScenePathCommand& command = resource.commands[i];
        if (i != 0) std::cout << ',';
        std::cout << "{\"source_cpu_address\":" << command.source_cpu_address << ",\"next_cpu_address\":" << command.next_cpu_address << ",\"opcode\":" << command.opcode << ",\"operand_hex\":\"";
        for (std::size_t j = 0; j < command.operands.size(); ++j) std::cout << std::hex << std::setfill('0') << std::setw(2) << static_cast<unsigned int>(command.operands[j]);
        std::cout << std::dec << "\"}";
    }
    std::cout << "],\"terminal_cpu_address\":" << resource.terminal_cpu_address << ",\"terminal_opcode\":" << resource.terminal_opcode << "}\n"; return 0;
}
