#include "ms5/palette_frame.h"

#include <cstdlib>
#include "ms5/video_port.h"
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
    bool trace_d1 = false;
    bool registers_mode = false;
    std::uint32_t d1 = 0U;
    std::uint32_t d3 = 0U;
    if (argc > 1 && (std::string(argv[1]) == "--d1" ||
                     std::string(argv[1]) == "--registers")) {
        registers_mode = std::string(argv[1]) == "--registers";
        trace_d1 = !registers_mode;
        const int values = registers_mode ? 2 : 1;
        if (argc < values + 2 || !parse_integer(argv[2], 0xffffffffU, d1) ||
            (registers_mode && !parse_integer(argv[3], 0xffffffffU, d3))) {
            std::cerr << "register options require uint32 values\n";
            return 1;
        }
        argc -= values + 1;
        argv += values + 1;
        if (argc > 1 && (std::string(argv[1]) == "--d1" ||
                         std::string(argv[1]) == "--registers")) {
            std::cerr << "--d1 and --registers cannot be repeated or combined\n";
            return 1;
        }
    }
    if (argc != 4 && argc != 5) {
        std::cerr << "usage: step_palette_frame [--d1 INPUT_D1 | --registers D1 D3] INPUT_RAM INPUT_MS5P OUTPUT_RAM [OUTPUT_PORTS]\n";
        return 2;
    }
    const std::string ram_path(argv[1]);
    const std::string resource_path(argv[2]);
    const std::string output_path(argv[3]);
    if (same_file(ram_path, output_path) ||
        same_file(resource_path, output_path)) {
        std::cerr << "RAM output must be distinct from both input files\n";
        return 1;
    }
    if (argc == 5 && (same_file(argv[4], ram_path) ||
                      same_file(argv[4], resource_path) ||
                      same_file(argv[4], output_path))) {
        std::cerr << "port output must be distinct from inputs and RAM output\n";
        return 1;
    }
    std::ifstream input(ram_path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        std::cerr << "cannot open RAM input\n";
        return 1;
    }
    if (input.tellg() != 65536) {
        std::cerr << "RAM input must contain exactly 65536 bytes\n";
        return 1;
    }
    input.seekg(0, std::ios::beg);
    std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]), 65536)) {
        std::cerr << "cannot read RAM input\n";
        return 1;
    }
    input.close();
    std::vector<ms5::PaletteRecord> records;
    std::string error;
    std::vector<ms5::VideoPortWrite> writes;
    if (!ms5::load_palette_resource(resource_path, records, error) ||
        !ms5::step_palette_frame(ram, records, error, argc == 5 ? &writes : NULL, (trace_d1 || registers_mode) ? &d1 : NULL,
                                    registers_mode ? &d3 : NULL)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open RAM output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&ram[0]), 65536);
    output.close();
    if (!output) {
        std::cerr << "cannot write RAM output\n";
        return 1;
    }
    if (argc == 5) {
        std::ofstream ports(argv[4], std::ios::binary | std::ios::trunc);
        if (!ports) {
            std::cerr << "cannot open port output\n";
            return 1;
        }
        // Diagnostic records: byte size, BE32 CPU port address, BE32 value.
        for (std::size_t index = 0; index < writes.size(); ++index) {
            const ms5::VideoPortWrite& write = writes[index];
            const char bytes[9] = {
                static_cast<char>(write.size),
                static_cast<char>((write.address >> 24) & 0xffU),
                static_cast<char>((write.address >> 16) & 0xffU),
                static_cast<char>((write.address >> 8) & 0xffU),
                static_cast<char>(write.address & 0xffU),
                static_cast<char>((write.value >> 24) & 0xffU),
                static_cast<char>((write.value >> 16) & 0xffU),
                static_cast<char>((write.value >> 8) & 0xffU),
                static_cast<char>(write.value & 0xffU)
            };
            ports.write(bytes, sizeof(bytes));
        }
        ports.close();
        if (!ports) {
            std::cerr << "cannot write port output\n";
            return 1;
        }
    }
    if (trace_d1 || registers_mode) {
        std::cout << "{\"d1\":" << d1;
        if (registers_mode) std::cout << ",\"d3\":" << d3;
        std::cout << "}\n";
    }
    return 0;
}
