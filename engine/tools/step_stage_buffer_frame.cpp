#include "ms5/stage_buffer_frame.h"

#include <cstdlib>
#include <algorithm>
#include <dirent.h>
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

bool load_windows(const std::string& directory, std::vector<std::string>& paths,
    std::vector<std::string>& canonical, std::vector<ms5::FixedDataResource>& windows, std::string& error) {
    std::vector<std::string> files, folders, seen;
    struct stat item;
    if (stat(directory.c_str(),&item) == 0 && S_ISREG(item.st_mode)) files.push_back(directory);
    else folders.push_back(directory);
    for (std::size_t n = 0; n < folders.size(); ++n) {
        std::string resolved;
        if (!canonical_path(folders[n],resolved)) { error = "cannot resolve resource directory"; return false; }
        if (std::find(seen.begin(),seen.end(),resolved) != seen.end()) continue;
        seen.push_back(resolved);
        DIR* folder = opendir(folders[n].c_str());
        if (folder == NULL) { error = "cannot open resource file or directory"; return false; }
        struct dirent* entry;
        while ((entry = readdir(folder)) != NULL) {
            const std::string name = entry->d_name;
            if (name == "." || name == "..") continue;
            const std::string path = folders[n]+"/"+name;
            if (stat(path.c_str(),&item) != 0) continue;
            if (S_ISDIR(item.st_mode)) folders.push_back(path);
            else if (S_ISREG(item.st_mode) && name.size() >= 5 && name.substr(name.size()-5) == ".ms5d") files.push_back(path);
        }
        closedir(folder);
    }
    std::sort(files.begin(),files.end());
    for (std::size_t i = 0; i < files.size(); ++i) {
        bool duplicate = false; std::string resolved;
        if (!canonical_path(files[i],resolved)) { error = "cannot resolve resource"; return false; }
        for (std::size_t j = 0; j < paths.size(); ++j) {
            if (j >= 3 && paths[j] == files[i]) { duplicate = true; break; }
            if (canonical[j] == resolved || same_inode(files[i],paths[j])) { error = "all input and output files must be distinct"; return false; }
        }
        if (duplicate) continue;
        std::ifstream header(files[i].c_str(),std::ios::binary); unsigned char kind[4] = {0}; header.seekg(8);
        if (!header.read(reinterpret_cast<char*>(kind),4)) { error = "resource header truncated"; return false; }
        const bool banked = kind[0] == 2 && kind[1] == 0 && kind[2] == 0 && kind[3] == 0;
        ms5::FixedDataResource resource;
        if (!(banked ? ms5::load_banked_data_resource(files[i],resource,error) : ms5::load_fixed_data_resource(files[i],resource,error))) return false;
        paths.push_back(files[i]); canonical.push_back(resolved); windows.push_back(resource);
    }
    return true;
}
} // namespace
int main(int argc, char** argv) {
    if (argc < 27) { std::cerr << "usage: step_stage_buffer_frame D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 BANK PHASE SAVED_A6 SAVED_SLOT_A4 SAVED_SLOT_D7 SAVED_D0 SAVED_D1 SAVED_D7 SAVED_A0 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [MS5D_OR_DIRECTORY ...]\n"; return 2; }
    ms5::StageBufferFrameState state;
    for (unsigned int i = 0; i < 13; ++i) {
        std::uint32_t value = 0;
        if (!parse_integer(argv[i+1],0xffffffffU,value)) { std::cerr << "invalid unsigned number\n"; return 1; }
        if (i < 8) state.registers.d[i] = value; else state.registers.a[i-8] = value;
    }
    std::uint32_t* fields[10] = {&state.a6,&state.bank,&state.phase,&state.saved_a6,&state.saved_slot_a4,&state.saved_slot_d7,&state.saved_d0,&state.saved_d1,&state.saved_d7,&state.saved_a0};
    for (unsigned int i = 0; i < 10; ++i) if (!parse_integer(argv[i+14],0xffffffffU,*fields[i])) { std::cerr << "invalid state number\n"; return 1; }
    std::vector<std::string> paths, canonical;
    for (int i = 24; i < 27; ++i) {
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
    std::vector<ms5::FixedDataResource> windows; std::string error;
    for (int i = 27; i < argc; ++i) if (!load_windows(argv[i],paths,canonical,windows,error)) { std::cerr << error << '\n'; return 1; }
    std::vector<ms5::VideoPortWrite> ports;
    if (!ms5::step_stage_buffer_frame(ram,windows,state,ports,error)) { std::cerr << error << '\n'; return 1; }
    std::vector<std::uint8_t> packed;
    for (std::size_t i = 0; i < ports.size(); ++i) {
        packed.push_back(ports[i].size);
        for (int shift = 24; shift >= 0; shift -= 8) packed.push_back(static_cast<std::uint8_t>(ports[i].address >> shift));
        for (int shift = 24; shift >= 0; shift -= 8) packed.push_back(static_cast<std::uint8_t>(ports[i].value >> shift));
    }
    if (!save_bytes(paths[1],ram) || !save_bytes(paths[2],packed)) { std::cerr << "cannot write output\n"; return 1; }
    std::cout << "{";
    for (unsigned int i = 0; i < 8; ++i) std::cout << (i == 0 ? "" : ",") << "\"d" << i << "\":" << state.registers.d[i];
    for (unsigned int i = 0; i < 5; ++i) std::cout << ",\"a" << i << "\":" << state.registers.a[i];
    const char* names[10] = {"a6","bank","phase","saved_a6","saved_slot_a4","saved_slot_d7","saved_d0","saved_d1","saved_d7","saved_a0"};
    for (unsigned int i = 0; i < 10; ++i) std::cout << ",\"" << names[i] << "\":" << *fields[i];
    std::cout << ",\"port_count\":" << ports.size() << "}\n"; return 0;
}
