#include "ms5/object_removal.h"

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
    if (argc != 10) { std::cerr << "usage: remove_object ENTRY TARGET D0 D1 D3 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS\n"; return 2; }
    ms5::RemovalState state; std::uint32_t entry = 0, target = 0;
    if (!parse_integer(argv[1],0xffffffffU,entry) || !parse_integer(argv[2],0xffffffffU,target) ||
        !parse_integer(argv[3],0xffffffffU,state.d0) || !parse_integer(argv[4],0xffffffffU,state.d1) ||
        !parse_integer(argv[5],0xffffffffU,state.d3) || !parse_integer(argv[6],0xffffffffU,state.a6)) {
        std::cerr << "entry, target and registers must be unsigned32 decimal/hex\n"; return 1;
    }
    std::vector<std::string> paths,canonical;
    for (int index = 7; index < argc; ++index) {
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
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) {
        std::cerr << "RAM input must contain exactly 65536 bytes\n"; return 1;
    }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    std::vector<ms5::VideoPortWrite> ports; std::string error;
    if (!ms5::remove_objects(ram,entry,target,state,ports,error)) { std::cerr << error << '\n'; return 1; }
    std::vector<std::uint8_t> bytes;
    for (std::size_t index = 0; index < ports.size(); ++index) {
        bytes.push_back(ports[index].size);
        for (unsigned int byte = 0; byte < 4; ++byte) bytes.push_back(static_cast<std::uint8_t>(ports[index].address >> (24 - byte * 8)));
        for (unsigned int byte = 0; byte < 4; ++byte) bytes.push_back(static_cast<std::uint8_t>(ports[index].value >> (24 - byte * 8)));
    }
    if (!save_bytes(paths[1],ram) || !save_bytes(paths[2],bytes)) { std::cerr << "cannot write outputs\n"; return 1; }
    std::cout << "{\"d0\":" << state.d0 << ",\"d1\":" << state.d1 << ",\"d3\":" << state.d3
              << ",\"a6\":" << state.a6 << ",\"writes\":" << ports.size() << "}\n"; return 0;
}
