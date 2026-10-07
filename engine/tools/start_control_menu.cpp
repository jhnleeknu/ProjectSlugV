#include "ms5/control_menu_start.h"

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
        if (argc != 10) {
            std::cerr << "usage: start_control_menu [--registers INPUT_D1 INPUT_D3] INPUT_RAM MENU_MS5D OUTPUT_RAM OUTPUT_PORTS LINE ENTRY_STACK\n";
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
    if (argc != 7) {
        std::cerr << "usage: start_control_menu [--registers INPUT_D1 INPUT_D3] INPUT_RAM MENU_MS5D OUTPUT_RAM OUTPUT_PORTS LINE ENTRY_STACK\n";
        return 2;
    }
    std::uint32_t entry_stack = 0U;
    std::uint32_t line = 0U;
    if (!parse_integer(argv[5], 0xffffU, line) ||
        !parse_integer(argv[6], 0xffffffU, entry_stack)) {
        std::cerr << "LINE must be decimal or 0x-prefixed uint16; ENTRY_STACK must be decimal or 0x-prefixed uint24\n";
        return 1;
    }
    if (registers && (d3 & 0xffffU) != line) {
        std::cerr << "LINE must match INPUT_D3 low16 bits in registers mode\n";
        return 1;
    }
    const std::string ram_path(argv[1]);
    const std::string resource_path(argv[2]);
    const std::string output_ram_path(argv[3]);
    const std::string output_writes_path(argv[4]);
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
    std::vector<ms5::VideoPortWrite> writes;
    ms5::MenuFrameResult result;
    if (!ms5::load_fixed_data_resource(resource_path, resource, error) ||
        !ms5::start_control_menu(ram, resource, static_cast<std::uint16_t>(line),
                                 entry_stack, result, writes, error, registers ? &d1 : NULL, registers ? &d3 : NULL)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output_ram(output_ram_path.c_str(), std::ios::binary | std::ios::trunc);
    std::ofstream output_writes(output_writes_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output_ram || !output_writes) {
        std::cerr << "cannot open output files\n";
        return 1;
    }
    output_ram.write(reinterpret_cast<const char*>(&ram[0]),
                     static_cast<std::streamsize>(ram.size()));
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
        output_writes.write(bytes, sizeof(bytes));
    }
    output_ram.close();
    output_writes.close();
    if (!output_ram || !output_writes) {
        std::cerr << "cannot write output files\n";
        return 1;
    }
    std::cout << "{\"status\":" << result.status
              << ",\"external_jump\":" << result.external_jump
              << ",\"line\":" << result.line;
    if (registers) {
        std::cout << ",\"d1\":" << d1 << ",\"d3\":" << d3;
    }
    std::cout << "}\n";
    return 0;
}
