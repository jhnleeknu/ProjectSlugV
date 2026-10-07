#include "ms5/sound_pair.h"

#include <cstdlib>
#include <fstream>
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
    if (argc != 12) { std::cerr << "usage: step_sound_pair ENTRY D0 D1 D3 PHASE SAVED COMMAND TAIL NEXT INPUT_RAM OUTPUT_RAM\n"; return 2; }
    ms5::SoundPairState state; std::uint32_t values[9] = {0};
    for (unsigned int index = 0; index < 9; ++index) {
        const std::uint32_t maximum = index < 4 ? 0xffffffffU : (index < 7 ? 255U : 65535U);
        if (!parse_integer(argv[index + 1],maximum,values[index])) { std::cerr << "invalid unsigned number\n"; return 1; }
    }
    state.entry = values[0]; state.d0 = values[1]; state.d1 = values[2]; state.d3 = values[3];
    state.phase = values[4]; state.saved = values[5]; state.byte.command = values[6]; state.byte.tail = values[7]; state.byte.next = values[8];
    state.next_pc = state.phase == 0 ? state.entry : (state.phase == 3 ? 0x3af6 : 0x3aea);
    state.byte.waiting = state.phase == 1 || state.phase == 2;
    std::vector<std::string> paths, canonical;
    for (int index = 10; index < argc; ++index) {
        paths.push_back(argv[index]); std::string resolved;
        if (!canonical_path(paths.back(),resolved)) { std::cerr << "cannot resolve path\n"; return 1; }
        for (std::size_t other = 0; other < canonical.size(); ++other) {
            if (canonical[other] == resolved || same_inode(paths.back(),paths[other])) {
                std::cerr << "all inputs and outputs must be distinct files\n"; return 1;
            }
        }
        canonical.push_back(resolved);
    }
    std::ifstream input(paths[0].c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) { std::cerr << "RAM input must contain exactly 65536 bytes\n"; return 1; }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    std::string error;


    if (!ms5::enqueue_sound_pair(ram,state,error)) { std::cerr << error << '\n'; return 1; }
    if (!save_bytes(paths[1],ram)) { std::cerr << "cannot write output\n"; return 1; }
    std::cout << "{\"entry\":" << state.entry << ",\"next_pc\":" << state.next_pc << ",\"d0\":" << state.d0
              << ",\"d1\":" << state.d1 << ",\"d3\":" << state.d3 << ",\"phase\":" << static_cast<unsigned int>(state.phase)
              << ",\"saved\":" << static_cast<unsigned int>(state.saved) << ",\"byte\":{\"waiting\":" << (state.byte.waiting ? "true" : "false")
              << ",\"command\":" << static_cast<unsigned int>(state.byte.command) << ",\"tail\":" << state.byte.tail << ",\"next\":" << state.byte.next << "}}\n";
    return 0;
}
