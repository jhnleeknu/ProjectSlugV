#include "ms5/stage_cue_control.h"

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
            if (j >= 2 && paths[j] == files[i]) { duplicate = true; break; }
            if (canonical[j] == resolved || same_inode(files[i],paths[j])) { error = "all input and output files must be distinct"; return false; }
        }
        if (duplicate) continue;
        std::ifstream header(files[i].c_str(),std::ios::binary); unsigned char kind[4] = {0}; header.seekg(8);
        if (!header.read(reinterpret_cast<char*>(kind),4)) { error = "resource header truncated"; return false; }
        const bool banked = kind[0] == 2 && kind[1] == 0 && kind[2] == 0 && kind[3] == 0;
        ms5::FixedDataResource resource;
        if (banked) { error = "stage cue control resources must be fixed MS5D windows"; return false; }
        if (!ms5::load_fixed_data_resource(files[i],resource,error)) return false;
        paths.push_back(files[i]); canonical.push_back(resolved); windows.push_back(resource);
    }
    return true;
}
} // namespace
int main(int argc, char** argv) {
    if (argc < 19) { std::cerr << "usage: step_stage_cue_control ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 CARRY INPUT_RAM OUTPUT_RAM [MS5D_OR_DIRECTORY ...]\n"; return 2; }
    std::uint32_t entry = 0;
    if (!parse_integer(argv[1],0xffffffffU,entry) || (entry != 0xe89fa && entry != 0xe8a1c && entry != 0xe8ad0 && entry != 0xe8af4 && entry != 0x2986)) { std::cerr << "unsupported entry\n"; return 1; }
    --argc; ++argv;
    ms5::SceneMapTransferState state;
    for (unsigned int i = 0; i < 13; ++i) {
        std::uint32_t value = 0;
        if (!parse_integer(argv[i+1],0xffffffffU,value)) { std::cerr << "invalid unsigned number\n"; return 1; }
        if (i < 8) state.d[i] = value; else state.a[i-8] = value;
    }
    std::uint32_t parent_a6 = 0;
    if (!parse_integer(argv[14],0xffffffffU,parent_a6)) { std::cerr << "invalid A6\n"; return 1; }
    std::uint32_t carry_value = 0;
    if (!parse_integer(argv[15],1,carry_value)) { std::cerr << "invalid carry\n"; return 1; }
    bool allocation_carry = carry_value != 0;
    std::vector<std::string> paths, canonical;
    for (int i = 16; i < 18; ++i) {
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
    for (int i = 18; i < argc; ++i) if (!load_windows(argv[i],paths,canonical,windows,error)) { std::cerr << error << '\n'; return 1; }
    if (!ms5::step_stage_cue_control(ram,entry,windows,state,parent_a6,allocation_carry,error)) { std::cerr << error << '\n'; return 1; }
    if (!save_bytes(paths[1],ram)) { std::cerr << "cannot write output\n"; return 1; }
    std::cout << "{";
    for (unsigned int i = 0; i < 8; ++i) std::cout << (i == 0 ? "" : ",") << "\"d" << i << "\":" << state.d[i];
    for (unsigned int i = 0; i < 5; ++i) std::cout << ",\"a" << i << "\":" << state.a[i];
    std::cout << ",\"a6\":" << parent_a6 << ",\"allocation_carry\":" << (allocation_carry ? "true" : "false") << "}\n"; return 0;
}
