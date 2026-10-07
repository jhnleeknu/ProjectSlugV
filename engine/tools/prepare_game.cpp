#include "ms5/game_prelude.h"

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
    ms5::GamePreludeState state;
    bool have_state = false, have_word = false, have_byte = false;
    int at = 1;
    while (at < argc && std::string(argv[at]).substr(0,2) == "--") {
        const std::string option = argv[at++];
        const int count = option == "--state" ? 5 : option == "--word" ? 6 : option == "--byte" ? 3 : -1;
        if (count < 0 || argc - at < count || (option == "--state" && have_state) ||
            (option == "--word" && have_word) || (option == "--byte" && have_byte)) {
            std::cerr << "invalid or duplicate option\n"; return 2;
        }
        std::uint32_t values[6] = {0,0,0,0,0,0};
        for (int index = 0; index < count; ++index) {
            std::uint32_t maximum = 65535;
            if (option == "--state") maximum = index == 4 ? 255 : 0xffffffffU;
            else if (option == "--word") maximum = index == 0 || index == 1 || index == 3 ? 255 : 65535;
            else if (index == 0) maximum = 255;
            if (!parse_integer(argv[at++],maximum,values[index])) { std::cerr << "invalid unsigned number\n"; return 1; }
        }
        if (option == "--state") {
            have_state = true; state.next_pc = values[0]; state.d0 = values[1]; state.d1 = values[2]; state.d3 = values[3]; state.phase = values[4];
        } else if (option == "--word") {
            have_word = true; state.word.kind = 1; state.word.phase = values[0]; state.word.low = values[1]; state.word.cursor = values[2];
            state.word.byte.waiting = true; state.word.byte.command = values[3]; state.word.byte.tail = values[4]; state.word.byte.next = values[5];
        } else {
            have_byte = true; state.byte.waiting = true; state.byte.command = values[0]; state.byte.tail = values[1]; state.byte.next = values[2];
        }
    }
    if (!have_state || argc - at != 3) {
        std::cerr << "usage: prepare_game --state PC D0 D1 D3 PHASE [--word PHASE LOW CURSOR COMMAND TAIL NEXT] [--byte COMMAND TAIL NEXT] EXTERNAL INPUT_RAM OUTPUT_RAM\n"; return 2;
    }
    std::uint32_t external = 0;
    if (!parse_integer(argv[at++],255,external)) { std::cerr << "invalid external byte\n"; return 1; }
    const std::string input_path = argv[at++], output_path = argv[at];
    std::string input_canonical, output_canonical;
    if (!canonical_path(input_path,input_canonical) || !canonical_path(output_path,output_canonical) ||
        input_canonical == output_canonical || same_inode(input_path,output_path)) {
        std::cerr << "RAM input and output must be distinct resolvable files\n"; return 1;
    }
    std::ifstream input(input_path.c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) { std::cerr << "RAM input must contain exactly 65536 bytes\n"; return 1; }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    std::uint8_t reads = 0; std::string error;
    if (!ms5::prepare_game_prelude(ram,external,state,reads,error)) { std::cerr << error << '\n'; return 1; }
    if (!save_bytes(output_path,ram)) { std::cerr << "cannot write output\n"; return 1; }
    std::cout << "{\"next_pc\":" << state.next_pc << ",\"d0\":" << state.d0 << ",\"d1\":" << state.d1
              << ",\"d3\":" << state.d3 << ",\"phase\":" << static_cast<unsigned int>(state.phase)
              << ",\"external_reads\":" << static_cast<unsigned int>(reads)
              << ",\"word\":{\"kind\":" << static_cast<unsigned int>(state.word.kind) << ",\"phase\":" << static_cast<unsigned int>(state.word.phase)
              << ",\"low\":" << static_cast<unsigned int>(state.word.low) << ",\"cursor\":" << state.word.cursor
              << ",\"waiting\":" << (state.word.byte.waiting ? "true" : "false") << ",\"command\":" << static_cast<unsigned int>(state.word.byte.command)
              << ",\"tail\":" << state.word.byte.tail << ",\"next\":" << state.word.byte.next
              << "},\"byte\":{\"waiting\":" << (state.byte.waiting ? "true" : "false") << ",\"command\":" << static_cast<unsigned int>(state.byte.command)
              << ",\"tail\":" << state.byte.tail << ",\"next\":" << state.byte.next << "}}\n";
    return 0;
}
