#include "ms5/menu_motion.h"

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
    const bool registers = argc > 1 && std::string(argv[1]) == "--registers";
    std::uint32_t d1 = 0U;
    std::uint32_t d3 = 0U;
    if (registers) {
        if (argc != 9) {
            std::cerr << "usage: step_menu_motion [--registers INPUT_D1 INPUT_D3] open|close INPUT_RAM INPUT_MS5D OUTPUT_RAM OUTPUT_WRITES\n";
            return 2;
        }
        if (!parse_integer(argv[2], 0xffffffffU, d1) ||
            !parse_integer(argv[3], 0xffffffffU, d3)) {
            std::cerr << "INPUT_D1 and INPUT_D3 must be decimal or 0x-prefixed uint32\n";
            return 1;
        }
        argc -= 3;
        argv += 3;
    }
    if (argc != 6 || (std::string(argv[1]) != "open" && std::string(argv[1]) != "close")) {
        std::cerr << "usage: step_menu_motion [--registers INPUT_D1 INPUT_D3] open|close INPUT_RAM INPUT_MS5D OUTPUT_RAM OUTPUT_WRITES\n";
        return 2;
    }
    const bool opening = std::string(argv[1]) == "open";
    const std::string ram_path(argv[2]);
    const std::string resource_path(argv[3]);
    const std::string output_ram_path(argv[4]);
    const std::string output_writes_path(argv[5]);
    if (same_file(ram_path, output_ram_path) ||
        same_file(resource_path, output_ram_path) ||
        same_file(ram_path, output_writes_path) ||
        same_file(resource_path, output_writes_path) ||
        same_file(output_ram_path, output_writes_path)) {
        std::cerr << "outputs must be distinct from both inputs and each other\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    ms5::FixedDataResource resource;
    std::string error;
    if (!read_ram(ram_path, ram)) {
        return 1;
    }
    if (!ms5::load_fixed_data_resource(resource_path, resource, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::vector<ms5::FixedWrite> writes;
    const bool success = opening ? ms5::open_menu_step(ram, resource, writes, error, registers ? &d1 : NULL, registers ? &d3 : NULL) :
        ms5::close_menu_step(ram, resource, writes, error, registers ? &d1 : NULL, registers ? &d3 : NULL);
    if (!success) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream ram_output(output_ram_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!ram_output) {
        std::cerr << "cannot open RAM output\n";
        return 1;
    }
    ram_output.write(reinterpret_cast<const char*>(&ram[0]),
                     static_cast<std::streamsize>(ram.size()));
    ram_output.close();
    if (!ram_output) {
        std::cerr << "cannot write RAM output\n";
        return 1;
    }
    std::ofstream output(output_writes_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open writes output\n";
        return 1;
    }
    for (std::size_t index = 0; index < writes.size(); ++index) {
        const ms5::FixedWrite& write = writes[index];
        const char bytes[4] = {
            static_cast<char>(write.address >> 8),
            static_cast<char>(write.address & 0xffU),
            static_cast<char>(write.value >> 8),
            static_cast<char>(write.value & 0xffU)
        };
        output.write(bytes, sizeof(bytes));
    }
    output.close();
    if (!output) {
        std::cerr << "cannot write writes output\n";
        return 1;
    }
    if (registers) {
        std::cout << "{\"d1\":" << d1 << ",\"d3\":" << d3 << "}\n";
    }
    return 0;
}
