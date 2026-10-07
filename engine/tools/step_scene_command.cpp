#include "ms5/scene_command.h"

#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

// Canonicalize an existing path, or its existing parent for a new output.
bool canonical_path(const std::string& path, std::string& canonical) {
    char* resolved = realpath(path.c_str(), 0);
    if (resolved != 0) {
        canonical.assign(resolved);
        std::free(resolved);
        return true;
    }
    const std::size_t slash = path.find_last_of('/');
    const std::string parent = slash == std::string::npos ? "."
        : (slash == 0 ? "/" : path.substr(0, slash));
    const std::string basename = slash == std::string::npos ? path : path.substr(slash + 1);
    if (basename.empty() || basename == "." || basename == "..") {
        return false;
    }
    resolved = realpath(parent.c_str(), 0);
    if (resolved == 0) {
        return false;
    }
    canonical.assign(resolved);
    std::free(resolved);
    canonical += "/" + basename;
    return true;
}

bool same_inode(const std::string& left, const std::string& right) {
    struct stat left_stat;
    struct stat right_stat;
    return stat(left.c_str(), &left_stat) == 0 &&
        stat(right.c_str(), &right_stat) == 0 &&
        left_stat.st_dev == right_stat.st_dev &&
        left_stat.st_ino == right_stat.st_ino;
}

bool save_bytes(const std::string& path, const std::vector<std::uint8_t>& bytes) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        return false;
    }
    if (!bytes.empty()) {
        output.write(reinterpret_cast<const char*>(&bytes[0]),
                     static_cast<std::streamsize>(bytes.size()));
    }
    output.close();
    return static_cast<bool>(output);
}

bool parse_integer(const std::string& text, std::uint32_t maximum, std::uint32_t& result) {
    unsigned int base = 10U;
    std::size_t start = 0U;
    if (text.size() >= 2U && text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) {
        base = 16U; start = 2U;
    }
    if (start == text.size()) return false;
    unsigned int value = 0U;
    for (std::size_t index = start; index < text.size(); ++index) {
        const char c = text[index];
        unsigned int digit;
        if (c >= '0' && c <= '9') digit = static_cast<unsigned int>(c - '0');
        else if (base == 16U && c >= 'a' && c <= 'f') digit = static_cast<unsigned int>(c - 'a') + 10U;
        else if (base == 16U && c >= 'A' && c <= 'F') digit = static_cast<unsigned int>(c - 'A') + 10U;
        else return false;
        if (digit >= base || digit > maximum || value > (maximum - digit) / base) return false;
        value = value * base + digit;
    }
    result = value;
    return true;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 17 && argc != 18) { std::cerr << "usage: step_scene_command D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS SCRIPT_MS5D NODE_POINTERS_MS5D [DEPENDENCIES_DIR]\n"; return 2; }
    std::uint32_t values[11] = {0};
    for (unsigned int i = 0; i < 11; ++i) {
        if (!parse_integer(argv[i + 1],0xffffffffU,values[i])) { std::cerr << "invalid unsigned number\n"; return 1; }
    }
    ms5::SceneCommandState state; state.d0 = values[0]; state.d1 = values[1]; state.d2 = values[2]; state.d3 = values[3];
    state.d4 = values[4]; state.d5 = values[5]; state.d6 = values[6]; state.d7 = values[7]; state.a0 = values[8]; state.a1 = values[9]; state.a2 = values[10];
    std::vector<std::string> paths, canonical;
    for (int i = 12; i < 17; ++i) {
        paths.push_back(argv[i]); std::string resolved;
        if (!canonical_path(paths.back(),resolved)) { std::cerr << "cannot resolve path\n"; return 1; }
        for (std::size_t j = 0; j < canonical.size(); ++j) {
            if (canonical[j] == resolved || same_inode(paths.back(),paths[j])) { std::cerr << "all files must be distinct\n"; return 1; }
        }
        canonical.push_back(resolved);
    }
    std::ifstream input(paths[0].c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) { std::cerr << "RAM must contain exactly65536 bytes\n"; return 1; }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    ms5::SceneScript script; ms5::FixedDataResource pointers; std::vector<ms5::VideoPortWrite> ports; std::string error;
    if (!ms5::load_scene_script(paths[3],script,error) || !ms5::load_fixed_data_resource(paths[4],pointers,error)) { std::cerr << error << '\n'; return 1; }
    std::vector<ms5::FixedDataResource> dependencies;
    for (std::size_t i = 0; i < script.commands.size(); ++i) {
        const ms5::SceneCommand& command = script.commands[i];
        if (command.source_cpu_address != state.a1) continue;
        std::string filename;
        std::uint32_t address = 0;
        if (command.opcode == 0 || command.opcode == 0x10) {
            const std::size_t at = command.opcode == 0 ? 4 : 0;
            for (unsigned int j = 0; j < 4; ++j) address = (address << 8) | command.operands[at + j];
            if (command.opcode == 0x10 || address != 0) {
                std::ostringstream name; name << (command.opcode == 0 ? "motion_" : "indirect_") << std::hex << std::setfill('0') << std::setw(6) << address << ".ms5d"; filename = name.str();
            }
        } else if (command.opcode == 0x24) filename = "path_nodes.ms5d";
        if (!filename.empty()) {
            if (argc != 18) { std::cerr << "command requires DEPENDENCIES_DIR\n"; return 1; }
            const std::string path = std::string(argv[17]) + "/" + filename; std::string resolved;
            if (!canonical_path(path,resolved)) { std::cerr << "cannot resolve dependency\n"; return 1; }
            for (std::size_t j = 0; j < paths.size(); ++j) {
                if (canonical[j] == resolved || same_inode(path,paths[j])) { std::cerr << "all files must be distinct\n"; return 1; }
            }
            ms5::FixedDataResource resource;
            if (!ms5::load_fixed_data_resource(path,resource,error)) { std::cerr << error << '\n'; return 1; }
            dependencies.push_back(resource);
        }
        break;
    }
    if (!ms5::execute_scene_command(ram,script,pointers,state,ports,error,&dependencies)) { std::cerr << error << '\n'; return 1; }
    std::vector<std::uint8_t> bytes;
    for (std::size_t i = 0; i < ports.size(); ++i) {
        bytes.push_back(ports[i].size);
        for (int shift = 24; shift >= 0; shift -= 8) bytes.push_back(static_cast<std::uint8_t>(ports[i].address >> shift));
        for (int shift = 24; shift >= 0; shift -= 8) bytes.push_back(static_cast<std::uint8_t>(ports[i].value >> shift));
    }
    if (!save_bytes(paths[1],ram) || !save_bytes(paths[2],bytes)) { std::cerr << "cannot write outputs\n"; return 1; }
    std::cout << "{\"d0\":" << state.d0 << ",\"d1\":" << state.d1 << ",\"d2\":" << state.d2 << ",\"d3\":" << state.d3 << ",\"d4\":" << state.d4 << ",\"d5\":" << state.d5 << ",\"d6\":" << state.d6 << ",\"d7\":" << state.d7
        << ",\"a0\":" << state.a0 << ",\"a1\":" << state.a1 << ",\"a2\":" << state.a2 << ",\"writes\":" << ports.size() << "}\n";
    return 0;
}
