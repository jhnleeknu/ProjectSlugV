#include "ms5/stage_sound_initialization.h"

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
    ms5::StageSoundState state; bool have_state = false, have_word = false, have_byte = false; int at = 1;
    while (at < argc && std::string(argv[at]).substr(0,2) == "--") {
        const std::string option = argv[at++];
        const int count = option == "--state" ? 6 : option == "--word" ? 7 : option == "--byte" ? 3 : -1;
        if (count < 0 || argc - at < count || (option == "--state" && have_state) || (option == "--word" && have_word) ||
            (option == "--byte" && have_byte)) { std::cerr << "invalid or duplicate option\n"; return 2; }
        std::uint32_t values[7] = {0};
        for (int i = 0; i < count; ++i) {
            const std::uint32_t maximum = option == "--state" ? (i == 5 ? 255 : 0xffffffffU) :
                option == "--word" ? (i == 0 || i == 1 || i == 2 || i == 4 ? 255 : 65535) : (i == 0 ? 255 : 65535);
            if (!parse_integer(argv[at++],maximum,values[i])) { std::cerr << "invalid unsigned number\n"; return 1; }
        }
        if (option == "--state") {
            have_state = true; state.next_pc = values[0]; state.d0 = values[1]; state.d1 = values[2]; state.d3 = values[3];
            state.a6 = values[4]; state.phase = static_cast<std::uint8_t>(values[5]);
        } else if (option == "--word") {
            have_word = true; state.word.kind = static_cast<std::uint8_t>(values[0]); state.word.phase = static_cast<std::uint8_t>(values[1]);
            state.word.low = static_cast<std::uint8_t>(values[2]); state.word.cursor = static_cast<std::uint16_t>(values[3]);
            state.word.byte.waiting = true; state.word.byte.command = static_cast<std::uint8_t>(values[4]);
            state.word.byte.tail = static_cast<std::uint16_t>(values[5]); state.word.byte.next = static_cast<std::uint16_t>(values[6]);
        } else {
            have_byte = true; state.byte.waiting = true; state.byte.command = static_cast<std::uint8_t>(values[0]);
            state.byte.tail = static_cast<std::uint16_t>(values[1]); state.byte.next = static_cast<std::uint16_t>(values[2]);
        }
    }
    if (!have_state || argc - at != 4) {
        std::cerr << "usage: step_stage_sound_initialization --state PC D0 D1 D3 A6 PHASE [--word KIND PHASE LOW CURSOR COMMAND TAIL NEXT] [--byte COMMAND TAIL NEXT] EXTERNAL INPUT_RAM OUTPUT_RAM CATALOG_DIR\n"; return 2;
    }
    std::uint32_t external = 0;
    if (!parse_integer(argv[at++],255,external)) { std::cerr << "invalid external byte\n"; return 1; }
    std::vector<std::string> paths;
    while (at < argc) paths.push_back(argv[at++]);
    for (unsigned int i = 0; i < 20; ++i) {
        std::string file = paths[2] + "/";
        if (i == 19) file += "stage_index.ms5d";
        else { file += "stage_group_"; file += static_cast<char>('0' + i/10); file += static_cast<char>('0' + i%10); file += ".ms5d"; }
        paths.push_back(file);
    }
    std::vector<std::string> canonical;
    for (std::size_t i = 0; i < paths.size(); ++i) {
        std::string resolved;
        if (!canonical_path(paths[i],resolved)) { std::cerr << "cannot resolve path\n"; return 1; }
        for (std::size_t j = 0; j < canonical.size(); ++j) {
            if (canonical[j] == resolved || same_inode(paths[i],paths[j])) { std::cerr << "all inputs and outputs must be distinct\n"; return 1; }
        }
        canonical.push_back(resolved);
    }
    std::ifstream input(paths[0].c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) { std::cerr << "RAM must contain exactly65536 bytes\n"; return 1; }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    std::string error; ms5::StageCatalog catalog; std::uint8_t reads = 0;
    if (!ms5::load_stage_catalog(paths[2],catalog,error) || !ms5::initialize_stage_sound(ram,catalog,static_cast<std::uint8_t>(external),state,reads,error)) {
        std::cerr << error << '\n'; return 1;
    }
    if (!save_bytes(paths[1],ram)) { std::cerr << "cannot write output\n"; return 1; }
    std::cout << "{\"next_pc\":" << state.next_pc << ",\"phase\":" << static_cast<unsigned int>(state.phase) << ",\"d0\":" << state.d0
        << ",\"d1\":" << state.d1 << ",\"d3\":" << state.d3 << ",\"a6\":" << state.a6 << ",\"external_reads\":" << static_cast<unsigned int>(reads)
        << ",\"word\":{\"kind\":" << static_cast<unsigned int>(state.word.kind) << ",\"phase\":" << static_cast<unsigned int>(state.word.phase)
        << ",\"low\":" << static_cast<unsigned int>(state.word.low) << ",\"cursor\":" << state.word.cursor << ",\"waiting\":" << (state.word.byte.waiting ? "true" : "false")
        << ",\"command\":" << static_cast<unsigned int>(state.word.byte.command) << ",\"tail\":" << state.word.byte.tail << ",\"next\":" << state.word.byte.next
        << "},\"byte\":{\"waiting\":" << (state.byte.waiting ? "true" : "false") << ",\"command\":" << static_cast<unsigned int>(state.byte.command)
        << ",\"tail\":" << state.byte.tail << ",\"next\":" << state.byte.next << "}}\n";
    return 0;
}
