#include "ms5/sound_byte.h"

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
    const bool resume = argc > 1 && std::string(argv[1]) == "--resume";
    if ((!resume && argc != 4) || (resume && argc != 7)) {
        std::cerr << "usage: enqueue_sound_byte INPUT_RAM OUTPUT_RAM COMMAND\n"
                  << "       enqueue_sound_byte --resume INPUT_RAM OUTPUT_RAM COMMAND TAIL NEXT\n";
        return 2;
    }
    const unsigned int start = resume ? 2U : 1U;
    std::uint32_t command = 0U;
    std::uint32_t tail = 0U;
    std::uint32_t next = 0U;
    if (!parse_integer(argv[start + 2U], 0xffU, command) ||
        (resume && (!parse_integer(argv[5], 0xffffU, tail) ||
                    !parse_integer(argv[6], 0xffffU, next)))) {
        std::cerr << "COMMAND must be decimal or 0x-prefixed uint8; TAIL and NEXT uint16\n";
        return 1;
    }
    const std::string input_path(argv[start]);
    const std::string output_path(argv[start + 1U]);
    if (same_file(input_path, output_path)) {
        std::cerr << "input and output must be distinct files\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    if (!read_ram(input_path, ram)) {
        return 1;
    }
    ms5::SoundBytePending pending;
    if (resume) {
        pending.waiting = true;
        pending.command = static_cast<std::uint8_t>(command);
        pending.tail = static_cast<std::uint16_t>(tail);
        pending.next = static_cast<std::uint16_t>(next);
    }
    std::string error;
    const bool succeeded = resume ? ms5::resume_sound_byte(ram, pending, error) :
        ms5::enqueue_sound_byte(ram, static_cast<std::uint8_t>(command), pending, error);
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
    std::cout << "{\"waiting\":" << (pending.waiting ? "true" : "false")
              << ",\"command\":" << static_cast<unsigned int>(pending.command)
              << ",\"tail\":" << pending.tail
              << ",\"next\":" << pending.next << "}\n";
    return 0;
}
