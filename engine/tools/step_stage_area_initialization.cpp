#include "ms5/stage_area_initialization.h"

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
    ms5::StageAreaInitializationState state;
    bool have_state = false, have_init = false, have_word = false, have_byte = false;
    int at = 1;
    while (at < argc && std::string(argv[at]).substr(0,2) == "--") {
        const std::string option = argv[at++];
        const int count = option == "--state" ? 6 : option == "--init" ? 2 : option == "--word" ? 6 : option == "--byte" ? 3 : -1;
        if (count < 0 || argc - at < count || (option == "--state" && have_state) || (option == "--init" && have_init) ||
            (option == "--word" && have_word) || (option == "--byte" && have_byte)) { std::cerr << "invalid or duplicate option\n"; return 2; }
        std::uint32_t values[6] = {0};
        for (int i = 0; i < count; ++i) {
            std::uint32_t maximum;
            if (option == "--state") maximum = i == 5 ? 255 : 0xffffffffU;
            else if (option == "--init") maximum = i == 1 ? 255 : 0xffffffffU;
            else if (option == "--word") maximum = i == 0 || i == 1 || i == 3 ? 255 : 65535;
            else maximum = i == 0 ? 255 : 65535;
            if (!parse_integer(argv[at++],maximum,values[i])) { std::cerr << "invalid unsigned number\n"; return 1; }
        }
        ms5::GamePreludeState& prelude = state.initialization.prelude;
        if (option == "--state") {
            have_state = true; state.next_pc = values[0]; state.d0 = values[1]; state.d1 = values[2];
            state.d3 = values[3]; state.a6 = values[4]; state.phase = static_cast<std::uint8_t>(values[5]);
        } else if (option == "--init") {
            have_init = true; prelude.next_pc = values[0]; prelude.phase = static_cast<std::uint8_t>(values[1]);
        } else if (option == "--word") {
            have_word = true; prelude.word.kind = 1; prelude.word.phase = static_cast<std::uint8_t>(values[0]);
            prelude.word.low = static_cast<std::uint8_t>(values[1]); prelude.word.cursor = static_cast<std::uint16_t>(values[2]);
            prelude.word.byte.waiting = true; prelude.word.byte.command = static_cast<std::uint8_t>(values[3]);
            prelude.word.byte.tail = static_cast<std::uint16_t>(values[4]); prelude.word.byte.next = static_cast<std::uint16_t>(values[5]);
        } else {
            have_byte = true; prelude.byte.waiting = true; prelude.byte.command = static_cast<std::uint8_t>(values[0]);
            prelude.byte.tail = static_cast<std::uint16_t>(values[1]); prelude.byte.next = static_cast<std::uint16_t>(values[2]);
        }
    }
    if (!have_state || argc - at != 6) {
        std::cerr << "usage: step_stage_area_initialization --state PC D0 D1 D3 A6 PHASE [--init PC INNER_PHASE] [--word PHASE LOW CURSOR COMMAND TAIL NEXT] [--byte COMMAND TAIL NEXT] EXTERNAL INPUT_RAM OUTPUT_RAM RECORDS_MS5D PLAYER_LOOKUP_MS5D SELECTOR_LOOKUP_MS5D\n"; return 2;
    }
    if (state.phase == 1) {
        state.initialization.prelude.d0 = state.d0; state.initialization.prelude.d1 = state.d1; state.initialization.prelude.d3 = state.d3;
    }
    std::uint32_t external = 0;
    if (!parse_integer(argv[at++],255,external)) { std::cerr << "invalid external byte\n"; return 1; }
    std::vector<std::string> paths, canonical;
    while (at < argc) {
        paths.push_back(argv[at++]); std::string resolved;
        if (!canonical_path(paths.back(),resolved)) { std::cerr << "cannot resolve path\n"; return 1; }
        for (std::size_t i = 0; i < canonical.size(); ++i) {
            if (canonical[i] == resolved || same_inode(paths.back(),paths[i])) { std::cerr << "all files must be distinct\n"; return 1; }
        }
        canonical.push_back(resolved);
    }
    std::ifstream input(paths[0].c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) { std::cerr << "RAM input must contain exactly65536 bytes\n"; return 1; }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    ms5::FixedDataResource records, player_lookup, selector_lookup; std::string error;
    if (!ms5::load_fixed_data_resource(paths[2],records,error) || !ms5::load_fixed_data_resource(paths[3],player_lookup,error) ||
        !ms5::load_fixed_data_resource(paths[4],selector_lookup,error)) { std::cerr << error << '\n'; return 1; }
    std::uint8_t reads = 0;
    if (!ms5::step_stage_area_initialization(ram,records,player_lookup,selector_lookup,static_cast<std::uint8_t>(external),state,reads,error)) {
        std::cerr << error << '\n'; return 1;
    }
    if (!save_bytes(paths[1],ram)) { std::cerr << "cannot write output\n"; return 1; }
    const ms5::GamePreludeState& p = state.initialization.prelude;
    std::cout << "{\"next_pc\":" << state.next_pc << ",\"phase\":" << static_cast<unsigned int>(state.phase) << ",\"d0\":" << state.d0
        << ",\"d1\":" << state.d1 << ",\"d3\":" << state.d3 << ",\"a6\":" << state.a6 << ",\"external_reads\":" << static_cast<unsigned int>(reads)
        << ",\"initialization\":{\"returned\":" << (state.initialization.returned ? "true" : "false") << ",\"prelude\":{\"next_pc\":" << p.next_pc
        << ",\"phase\":" << static_cast<unsigned int>(p.phase) << ",\"d0\":" << p.d0 << ",\"d1\":" << p.d1 << ",\"d3\":" << p.d3
        << ",\"word\":{\"kind\":" << static_cast<unsigned int>(p.word.kind) << ",\"phase\":" << static_cast<unsigned int>(p.word.phase)
        << ",\"low\":" << static_cast<unsigned int>(p.word.low) << ",\"cursor\":" << p.word.cursor << ",\"waiting\":" << (p.word.byte.waiting ? "true" : "false")
        << ",\"command\":" << static_cast<unsigned int>(p.word.byte.command) << ",\"tail\":" << p.word.byte.tail << ",\"next\":" << p.word.byte.next
        << "},\"byte\":{\"waiting\":" << (p.byte.waiting ? "true" : "false") << ",\"command\":" << static_cast<unsigned int>(p.byte.command)
        << ",\"tail\":" << p.byte.tail << ",\"next\":" << p.byte.next << "}}}}\n";
    return 0;
}
