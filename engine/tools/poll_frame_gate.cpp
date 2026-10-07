#include "ms5/frame_gate.h"

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

int run_batch() {
    char input[5];
    while (true) {
        std::cin.read(input, sizeof(input));
        const std::streamsize count = std::cin.gcount();
        if (count == 0 && std::cin.eof()) {
            break;
        }
        if (count != static_cast<std::streamsize>(sizeof(input))) {
            std::cerr << "truncated batch record or input error\n";
            return 1;
        }
        std::vector<std::uint8_t> ram(65536U, 0U);
        ram[0x16U] = static_cast<std::uint8_t>(input[0]);
        ram[0x17U] = static_cast<std::uint8_t>(input[1]);
        ram[0x18U] = static_cast<std::uint8_t>(input[2]);
        const std::uint16_t video = static_cast<std::uint16_t>(
            (static_cast<unsigned char>(input[3]) << 8) |
            static_cast<unsigned char>(input[4]));
        bool ready = false;
        std::string error;
        if (!ms5::poll_frame_gate(ram, video, ready, error)) {
            std::cerr << error << '\n';
            return 1;
        }
        const char output[2] = {
            static_cast<char>(ready ? 1U : 0U), static_cast<char>(ram[0x18U])
        };
        std::cout.write(output, sizeof(output));
        if (!std::cout) {
            std::cerr << "cannot write batch output\n";
            return 1;
        }
    }
    std::cout.flush();
    if (!std::cout) {
        std::cerr << "cannot write batch output\n";
        return 1;
    }
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--batch") {
        return run_batch();
    }
    if (argc != 4) {
        std::cerr << "usage: poll_frame_gate INPUT_RAM OUTPUT_RAM VIDEO\n"
                  << "       poll_frame_gate --batch\n";
        return 2;
    }
    std::uint32_t video = 0U;
    if (!parse_integer(argv[3], 0xffffU, video)) {
        std::cerr << "VIDEO must be decimal or 0x-prefixed uint16\n";
        return 1;
    }
    const std::string input_path(argv[1]);
    const std::string output_path(argv[2]);
    if (same_file(input_path, output_path)) {
        std::cerr << "input and output must be distinct files\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    if (!read_ram(input_path, ram)) {
        return 1;
    }
    bool ready = false;
    std::string error;
    if (!ms5::poll_frame_gate(ram, static_cast<std::uint16_t>(video), ready, error)) {
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
    std::cout << "{\"ready\":" << (ready ? "true" : "false") << "}\n";
    return 0;
}
