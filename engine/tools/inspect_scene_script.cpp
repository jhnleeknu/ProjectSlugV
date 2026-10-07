#include "ms5/scene_script.h"
#include <iostream>
#include <string>
namespace {
std::string hex(const std::vector<std::uint8_t>& bytes) {
    const char digits[] = "0123456789abcdef"; std::string text;
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        text += digits[bytes[i] >> 4]; text += digits[bytes[i] & 15];
    }
    return text;
}
}
int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "usage: inspect_scene_script SCRIPT_MS5D\n"; return 2; }
    ms5::SceneScript script; std::string error;
    if (!ms5::load_scene_script(argv[1],script,error)) { std::cerr << error << '\n'; return 1; }
    std::cout << "{\"source_cpu_address\":" << script.source.source_cpu_address << ",\"commands\":[";
    for (std::size_t i = 0; i < script.commands.size(); ++i) {
        const ms5::SceneCommand& command = script.commands[i];
        if (i != 0) std::cout << ',';
        std::cout << "{\"address\":" << command.source_cpu_address << ",\"opcode\":" << command.opcode
            << ",\"operandhex\":\"" << hex(command.operands) << "\",\"inlinehex\":\"" << hex(command.inline_data)
            << "\",\"next\":" << command.next_cpu_address << '}';
    }
    std::cout << "],\"terminator_address\":" << script.terminator_cpu_address << ",\"terminator_opcode\":" << script.terminator_opcode << "}\n";
    return 0;
}
