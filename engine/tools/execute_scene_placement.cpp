#include "ms5/scene_placement_execution.h"

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

bool load_resource(const std::string& file, std::vector<std::string>& paths,
    std::vector<std::string>& canonical, std::vector<ms5::FixedDataResource>& windows, std::string& error) {
    std::string resolved;
    if (!canonical_path(file,resolved)) { error = "cannot resolve resource"; return false; }
    for (std::size_t j = 0; j < paths.size(); ++j) {
        if (j >= 2 && paths[j] == file) return true;
        if (canonical[j] == resolved || same_inode(file,paths[j])) { error = "all input and output files must be distinct"; return false; }
    }
    ms5::FixedDataResource resource;
    if (!ms5::load_fixed_data_resource(file,resource,error)) return false;
    paths.push_back(file); canonical.push_back(resolved); windows.push_back(resource); return true;
}
bool load_windows(const std::string& path, std::vector<std::string>& paths,
    std::vector<std::string>& canonical, std::vector<ms5::FixedDataResource>& windows, std::string& error) {
    struct stat info;
    if (stat(path.c_str(),&info) != 0) { error = "cannot inspect resource path"; return false; }
    if (!S_ISDIR(info.st_mode)) return load_resource(path,paths,canonical,windows,error);
    DIR* folder = opendir(path.c_str());
    if (folder == NULL) { error = "cannot open resource directory"; return false; }
    std::vector<std::string> files; struct dirent* item;
    while ((item = readdir(folder)) != NULL) {
        const std::string name = item->d_name;
        if (name.size() >= 5 && name.substr(name.size()-5) == ".ms5d") files.push_back(path+"/"+name);
    }
    closedir(folder); std::sort(files.begin(),files.end());
    for (std::size_t i = 0; i < files.size(); ++i) if (!load_resource(files[i],paths,canonical,windows,error)) return false;
    return true;
}
} // namespace
int main(int argc, char** argv) {
    if (argc < 17) { std::cerr << "usage: execute_scene_placement ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 A6 INPUT_RAM OUTPUT_RAM [RESOURCE_FILE_OR_DIR ...]\n"; return 2; }
    std::uint32_t entry = 0, values[13] = {0};
    if (!parse_integer(argv[1],0xffffffffU,entry) || (entry != 0x1a414 && entry != 0x1a470)) { std::cerr << "unsupported entry\n"; return 1; }
    for (unsigned int i = 0; i < 13; ++i) {
        if (!parse_integer(argv[i+2],0xffffffffU,values[i])) { std::cerr << "invalid unsigned number\n"; return 1; }
    }
    ms5::SceneCommandState state; state.d0 = values[0]; state.d1 = values[1]; state.d2 = values[2]; state.d3 = values[3];
    state.d4 = values[4]; state.d5 = values[5]; state.d6 = values[6]; state.d7 = values[7]; state.a0 = values[8]; state.a1 = values[9]; state.a2 = values[10]; state.a4 = values[11];
    std::vector<std::string> paths, canonical;
    for (int i = 15; i < 17; ++i) {
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
    for (int i = 17; i < argc; ++i) if (!load_windows(argv[i],paths,canonical,windows,error)) { std::cerr << error << '\n'; return 1; }
    if (!ms5::execute_scene_placement(ram,entry,windows,state,values[12],error)) { std::cerr << error << '\n'; return 1; }
    if (!save_bytes(paths[1],ram)) { std::cerr << "cannot write output\n"; return 1; }
    std::cout << "{\"entry\":" << entry << ",\"d0\":" << state.d0 << ",\"d1\":" << state.d1 << ",\"d2\":" << state.d2 << ",\"d3\":" << state.d3 << ",\"d4\":" << state.d4 << ",\"d5\":" << state.d5 << ",\"d6\":" << state.d6 << ",\"d7\":" << state.d7
        << ",\"a0\":" << state.a0 << ",\"a1\":" << state.a1 << ",\"a2\":" << state.a2 << ",\"a4\":" << state.a4 << ",\"a6\":" << values[12] << "}\n";
    return 0;
}
