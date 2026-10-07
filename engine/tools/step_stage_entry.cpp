#include "ms5/stage_entry.h"
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
    if (argc != 17) { std::cerr << "usage: step_stage_entry PC PHASE D0 D1 D3 A6 PAIR_PHASE SAVED COMMAND TAIL NEXT INPUT OUTPUT PORTS CATALOG_DIR TABLES\n"; return 2; }
    std::uint32_t values[11] = {0};
    for (unsigned int i = 0; i < 11; ++i) {
        const std::uint32_t maximum = (i == 1 || (i >= 6 && i <= 8)) ? 255U : (i >= 9 ? 65535U : 0xffffffffU);
        if (!parse_integer(argv[i+1],maximum,values[i])) { std::cerr << "invalid unsigned number\n"; return 1; }
    }
    ms5::StageEntryState state;
    state.next_pc=values[0]; state.phase=static_cast<std::uint8_t>(values[1]);
    state.d0=values[2]; state.d1=values[3]; state.d3=values[4]; state.a6=values[5];
    state.sound.phase=static_cast<std::uint8_t>(values[6]); state.sound.saved=static_cast<std::uint8_t>(values[7]);
    state.sound.byte.command=static_cast<std::uint8_t>(values[8]); state.sound.byte.tail=static_cast<std::uint16_t>(values[9]);
    state.sound.byte.next=static_cast<std::uint16_t>(values[10]);
    state.sound.next_pc=state.sound.phase == 0 ? 0x3d58 : (state.sound.phase == 3 ? 0x3af6 : 0x3aea);
    state.sound.byte.waiting=state.sound.phase == 1 || state.sound.phase == 2;
    if (state.sound.phase == 1 || state.sound.phase == 2) {
        state.sound.d0=state.d0; state.sound.d1=state.d1; state.sound.d3=state.d3;
    }
    std::vector<std::string> paths, canonical;
    for (int i=12; i<argc; ++i) {
        paths.push_back(argv[i]); std::string resolved;
        if (!canonical_path(paths.back(),resolved)) { std::cerr << "cannot resolve path\n"; return 1; }
        for (std::size_t other=0; other<canonical.size(); ++other) {
            if (canonical[other] == resolved || same_inode(paths.back(),paths[other])) {
                std::cerr << "inputs and outputs must be distinct\n"; return 1;
            }
        }
        canonical.push_back(resolved);
    }
    // Protect every catalog resource from direct, symlink and hardlink output aliases.
    for (unsigned int resource=0; resource<20; ++resource) {
        std::string file=paths[3]+"/";
        if (resource == 19) file += "stage_index.ms5d";
        else { file += "stage_group_"; file += static_cast<char>('0'+resource/10); file += static_cast<char>('0'+resource%10); file += ".ms5d"; }
        std::string resolved;
        if (!canonical_path(file,resolved)) { std::cerr << "cannot resolve catalog resource\n"; return 1; }
        for (unsigned int output=1; output<=2; ++output) {
            if (canonical[output] == resolved || same_inode(paths[output],file)) {
                std::cerr << "output aliases catalog resource\n"; return 1;
            }
        }
    }
    std::ifstream input(paths[0].c_str(),std::ios::binary|std::ios::ate);
    if (!input || input.tellg()!=static_cast<std::streamoff>(65536)) { std::cerr << "RAM input must contain exactly 65536 bytes\n"; return 1; }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    ms5::StageCatalog catalog; ms5::FixedDataResource tables; std::string error;
    std::vector<ms5::VideoPortWrite> ports;
    if (!ms5::load_stage_catalog(paths[3],catalog,error) || !ms5::load_fixed_data_resource(paths[4],tables,error) ||
        !ms5::step_stage_entry(ram,catalog,tables,state,ports,error)) { std::cerr << error << '\n'; return 1; }
    std::vector<std::uint8_t> bytes;
    for (std::size_t i=0; i<ports.size(); ++i) {
        bytes.push_back(ports[i].size);
        for (unsigned int byte=0; byte<4; ++byte) bytes.push_back(static_cast<std::uint8_t>(ports[i].address>>(24-byte*8)));
        for (unsigned int byte=0; byte<4; ++byte) bytes.push_back(static_cast<std::uint8_t>(ports[i].value>>(24-byte*8)));
    }
    if (!save_bytes(paths[1],ram) || !save_bytes(paths[2],bytes)) { std::cerr << "cannot write outputs\n"; return 1; }
    const ms5::SoundPairState& sound=state.sound;
    std::cout << "{\"next_pc\":" << state.next_pc << ",\"phase\":" << static_cast<unsigned int>(state.phase)
        << ",\"d0\":" << state.d0 << ",\"d1\":" << state.d1 << ",\"d3\":" << state.d3 << ",\"a6\":" << state.a6
        << ",\"writes\":" << ports.size() << ",\"sound\":{\"entry\":" << sound.entry << ",\"next_pc\":" << sound.next_pc
        << ",\"d0\":" << sound.d0 << ",\"d1\":" << sound.d1 << ",\"d3\":" << sound.d3
        << ",\"phase\":" << static_cast<unsigned int>(sound.phase) << ",\"saved\":" << static_cast<unsigned int>(sound.saved)
        << ",\"byte\":{\"waiting\":" << (sound.byte.waiting ? "true" : "false") << ",\"command\":" << static_cast<unsigned int>(sound.byte.command)
        << ",\"tail\":" << sound.byte.tail << ",\"next\":" << sound.byte.next << "}}}\n";
    return 0;
}
