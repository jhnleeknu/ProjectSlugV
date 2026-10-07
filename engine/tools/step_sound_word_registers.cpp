#include "ms5/sound_word.h"

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
    const bool enqueue = argc >= 2 && std::string(argv[1]) == "enqueue";
    const bool resume = argc >= 2 && std::string(argv[1]) == "resume";
    if ((!enqueue && !resume) || (enqueue && argc != 7) || (resume && argc != 13)) {
        std::cerr << "usage: step_sound_word_registers enqueue INPUT_RAM OUTPUT_RAM D0 D1 EXTERNAL\n"
                  << "       step_sound_word_registers resume INPUT_RAM OUTPUT_RAM D0 D1 KIND PHASE LOW CURSOR COMMAND TAIL NEXT\n"; return 2;
    }
    std::uint32_t d0 = 0, d1 = 0, external = 0;
    if (!parse_integer(argv[4],0xffffffffU,d0) || !parse_integer(argv[5],0xffffffffU,d1) ||
        (enqueue && !parse_integer(argv[6],255,external))) { std::cerr << "invalid register or status\n"; return 1; }
    ms5::SoundWordPending pending;
    if (resume) {
        std::uint32_t fields[7] = {0};
        for (unsigned int i = 0; i < 7; ++i) {
            const std::uint32_t maximum = i == 0 || i == 1 || i == 2 || i == 4 ? 255 : 65535;
            if (!parse_integer(argv[6 + i],maximum,fields[i])) { std::cerr << "invalid pending field\n"; return 1; }
        }
        pending.kind = static_cast<std::uint8_t>(fields[0]); pending.phase = static_cast<std::uint8_t>(fields[1]); pending.low = static_cast<std::uint8_t>(fields[2]);
        pending.cursor = static_cast<std::uint16_t>(fields[3]); pending.byte.waiting = true; pending.byte.command = static_cast<std::uint8_t>(fields[4]);
        pending.byte.tail = static_cast<std::uint16_t>(fields[5]); pending.byte.next = static_cast<std::uint16_t>(fields[6]);
    }
    std::string input_canonical, output_canonical;
    if (!canonical_path(argv[2],input_canonical) || !canonical_path(argv[3],output_canonical) ||
        input_canonical == output_canonical || same_inode(argv[2],argv[3])) { std::cerr << "input/output must be distinct\n"; return 1; }
    std::ifstream input(argv[2],std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) { std::cerr << "RAM must contain exactly65536 bytes\n"; return 1; }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    std::string error; std::uint8_t reads = 0;
    const bool success = enqueue ? ms5::enqueue_sound_word_registers(ram,d0,d1,static_cast<std::uint8_t>(external),pending,reads,error)
                                 : ms5::resume_sound_word_registers(ram,d0,d1,pending,error);
    if (!success) { std::cerr << error << '\n'; return 1; }
    if (!save_bytes(argv[3],ram)) { std::cerr << "cannot write output\n"; return 1; }
    std::cout << "{\"d0\":" << d0 << ",\"d1\":" << d1 << ",\"external_reads\":" << static_cast<unsigned int>(reads)
        << ",\"pending\":{\"kind\":" << static_cast<unsigned int>(pending.kind) << ",\"phase\":" << static_cast<unsigned int>(pending.phase)
        << ",\"low\":" << static_cast<unsigned int>(pending.low) << ",\"cursor\":" << pending.cursor << ",\"waiting\":" << (pending.byte.waiting ? "true" : "false")
        << ",\"command\":" << static_cast<unsigned int>(pending.byte.command) << ",\"tail\":" << pending.byte.tail << ",\"next\":" << pending.byte.next << "}}\n";
    return 0;
}
