#include "ms5/sound_word.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

std::string resolved_path(const std::string& path) {
    char* resolved = realpath(path.c_str(), NULL);
    if (resolved != NULL) {
        const std::string result(resolved);
        std::free(resolved);
        return result;
    }
    const std::string::size_type slash = path.find_last_of('/');
    const std::string parent = slash == std::string::npos ? "." :
        (slash == 0 ? "/" : path.substr(0, slash));
    const std::string name = slash == std::string::npos ? path : path.substr(slash + 1);
    resolved = realpath(parent.c_str(), NULL);
    if (resolved == NULL) {
        return path;
    }
    const std::string result = std::string(resolved) + "/" + name;
    std::free(resolved);
    return result;
}

bool same_file(const std::string& left, const std::string& right) {
    struct stat left_stat;
    struct stat right_stat;
    return left == right || resolved_path(left) == resolved_path(right) ||
        (stat(left.c_str(), &left_stat) == 0 &&
         stat(right.c_str(), &right_stat) == 0 &&
         left_stat.st_dev == right_stat.st_dev &&
         left_stat.st_ino == right_stat.st_ino);
}

bool read_ram(const std::string& path, std::vector<std::uint8_t>& ram) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        std::cerr << "cannot open RAM input\n";
        return false;
    }
    if (input.tellg() != static_cast<std::streamoff>(65536U)) {
        std::cerr << "RAM input must contain exactly 65536 bytes\n";
        return false;
    }
    input.seekg(0, std::ios::beg);
    ram.resize(65536U);
    if (!input.read(reinterpret_cast<char*>(&ram[0]), 65536)) {
        std::cerr << "cannot read RAM input\n";
        return false;
    }
    return true;
}

bool parse_integer(const std::string& text, std::uint32_t maximum,
                   std::uint32_t& result) {
    unsigned int base = 10;
    std::size_t start = 0;
    if (text.size() >= 2 && text[0] == '0' &&
        (text[1] == 'x' || text[1] == 'X')) {
        base = 16;
        start = 2;
    }
    if (start == text.size()) {
        return false;
    }
    std::uint32_t value = 0;
    for (std::size_t index = start; index < text.size(); ++index) {
        const char c = text[index];
        unsigned int digit;
        if (c >= '0' && c <= '9') {
            digit = static_cast<unsigned int>(c - '0');
        } else if (base == 16 && c >= 'a' && c <= 'f') {
            digit = static_cast<unsigned int>(c - 'a') + 10U;
        } else if (base == 16 && c >= 'A' && c <= 'F') {
            digit = static_cast<unsigned int>(c - 'A') + 10U;
        } else {
            return false;
        }
        if (digit >= base || digit > maximum || value > (maximum - digit) / base) {
            return false;
        }
        value = value * base + digit;
    }
    result = value;
    return true;
}

} // namespace

int main(int argc, char** argv) {
    const std::string action = argc > 1 ? argv[1] : "";
    const bool enqueue = action == "enqueue";
    const bool drain = action == "drain";
    const bool resume = action == "resume";
    if ((!enqueue && !drain && !resume) || (enqueue && argc != 6) ||
        (drain && argc != 4) || (resume && argc != 11)) {
        std::cerr << "usage: sound_word enqueue INPUT_RAM OUTPUT_RAM COMMAND EXTERNAL_BYTE\n"
                  << "       sound_word drain INPUT_RAM OUTPUT_RAM\n"
                  << "       sound_word resume INPUT_RAM OUTPUT_RAM KIND PHASE LOW CURSOR BYTE_COMMAND BYTE_TAIL BYTE_NEXT\n";
        return 2;
    }
    std::uint32_t command = 0U;
    std::uint32_t external = 0U;
    std::uint32_t fields[7] = {0U, 0U, 0U, 0U, 0U, 0U, 0U};
    if (enqueue && (!parse_integer(argv[4], 0xffffU, command) ||
                    !parse_integer(argv[5], 0xffU, external))) {
        std::cerr << "COMMAND must be decimal or 0x-prefixed uint16; EXTERNAL_BYTE uint8\n";
        return 1;
    }
    if (resume) {
        const std::uint32_t limits[7] = {0xffU, 0xffU, 0xffU, 0xffffU, 0xffU, 0xffffU, 0xffffU};
        for (unsigned int index = 0U; index < 7U; ++index) {
            if (!parse_integer(argv[index + 4U], limits[index], fields[index])) {
                std::cerr << "KIND, PHASE, LOW and BYTE_COMMAND must be decimal or 0x-prefixed uint8; CURSOR, BYTE_TAIL and BYTE_NEXT uint16\n";
                return 1;
            }
        }
    }
    const std::string input_path(argv[2]);
    const std::string output_path(argv[3]);
    if (same_file(input_path, output_path)) {
        std::cerr << "input and output must be distinct files\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    if (!read_ram(input_path, ram)) {
        return 1;
    }
    ms5::SoundWordPending pending;
    if (resume) {
        pending.kind = static_cast<std::uint8_t>(fields[0]);
        pending.phase = static_cast<std::uint8_t>(fields[1]);
        pending.low = static_cast<std::uint8_t>(fields[2]);
        pending.cursor = static_cast<std::uint16_t>(fields[3]);
        pending.byte.waiting = true;
        pending.byte.command = static_cast<std::uint8_t>(fields[4]);
        pending.byte.tail = static_cast<std::uint16_t>(fields[5]);
        pending.byte.next = static_cast<std::uint16_t>(fields[6]);
    }
    std::string error;
    bool succeeded;
    if (enqueue) {
        succeeded = ms5::enqueue_sound_word(ram, static_cast<std::uint16_t>(command),
                                            static_cast<std::uint8_t>(external), pending, error);
    } else if (drain) {
        succeeded = ms5::drain_sound_words(ram, pending, error);
    } else {
        succeeded = ms5::resume_sound_word(ram, pending, error);
    }
    if (!succeeded) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open RAM output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&ram[0]),
                 static_cast<std::streamsize>(ram.size()));
    output.close();
    if (!output) {
        std::cerr << "cannot write RAM output\n";
        return 1;
    }
    std::cout << "{\"kind\":" << static_cast<unsigned int>(pending.kind)
              << ",\"phase\":" << static_cast<unsigned int>(pending.phase)
              << ",\"low\":" << static_cast<unsigned int>(pending.low)
              << ",\"cursor\":" << pending.cursor
              << ",\"command\":" << static_cast<unsigned int>(pending.byte.command)
              << ",\"tail\":" << pending.byte.tail
              << ",\"next\":" << pending.byte.next << "}\n";
    return 0;
}
