#include "ms5/formatted_text.h"
#include "ms5/fixed_data_resource.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

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

std::string canonical_path(const std::string& path) {
    char* resolved = realpath(path.c_str(), NULL);
    if (resolved != NULL) {
        const std::string result(resolved);
        std::free(resolved);
        return result;
    }
    const std::size_t slash = path.find_last_of('/');
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
    return canonical_path(left) == canonical_path(right) ||
        (stat(left.c_str(), &left_stat) == 0 &&
         stat(right.c_str(), &right_stat) == 0 &&
         left_stat.st_dev == right_stat.st_dev &&
         left_stat.st_ino == right_stat.st_ino);
}

bool read_bytes(const std::string& path, std::size_t maximum, bool exact,
                std::vector<std::uint8_t>& bytes) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        std::cerr << "cannot open input: " << path << '\n';
        return false;
    }
    const std::streamoff length = input.tellg();
    if (length < 0 || static_cast<std::uint64_t>(length) > maximum ||
        (exact && static_cast<std::uint64_t>(length) != maximum)) {
        std::cerr << (exact ? "input must contain exactly " : "input must contain at most ")
                  << maximum << " bytes: " << path << '\n';
        return false;
    }
    input.seekg(0, std::ios::beg);
    if (!input) {
        std::cerr << "cannot seek input: " << path << '\n';
        return false;
    }
    bytes.resize(static_cast<std::size_t>(length));
    if (!bytes.empty()) {
        input.read(reinterpret_cast<char*>(&bytes[0]),
                   static_cast<std::streamsize>(bytes.size()));
        if (input.gcount() != static_cast<std::streamsize>(bytes.size()) || input.bad()) {
            std::cerr << "cannot read input: " << path << '\n';
            return false;
        }
    }
    char extra;
    if (input.get(extra) || input.bad() || !input.eof()) {
        std::cerr << "input size changed or read failed: " << path << '\n';
        return false;
    }
    return true;
}

bool write_bytes(const std::string& path, const std::uint8_t* bytes,
                 std::size_t size) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output: " << path << '\n';
        return false;
    }
    output.write(reinterpret_cast<const char*>(bytes),
                 static_cast<std::streamsize>(size));
    output.close();
    if (!output) {
        std::cerr << "cannot write output: " << path << '\n';
        return false;
    }
    return true;
}

} // namespace

int main(int argc, char** argv) {
    std::uint32_t renderer = 0xe84c8U;
    std::uint32_t d1 = 0U;
    std::uint32_t d3 = 0U;
    bool renderer_option = false;
    bool registers = false;
    while (argc > 1) {
        const std::string option(argv[1]);
        if (option == "--renderer") {
            if (renderer_option || argc < 3) {
                std::cerr << "--renderer requires one value and cannot be repeated\n";
                return 2;
            }
            if (!parse_integer(argv[2], 0xffffffffU, renderer) ||
                (renderer != 0x3650U && renderer != 0xe84c8U)) {
                std::cerr << "renderer must be decimal or 0x-prefixed CPU address 0x3650 or 0xe84c8\n";
                return 1;
            }
            renderer_option = true;
            argc -= 2;
            argv += 2;
        } else if (option == "--registers") {
            if (registers || argc < 4) {
                std::cerr << "--registers requires D1 and D3 and cannot be repeated\n";
                return 2;
            }
            if (!parse_integer(argv[2], 0xffffffffU, d1) ||
                !parse_integer(argv[3], 0xffffffffU, d3)) {
                std::cerr << "D1 and D3 must be decimal or 0x-prefixed uint32\n";
                return 1;
            }
            registers = true;
            argc -= 3;
            argv += 3;
        } else {
            break;
        }
    }
    if (argc != 10) {
        std::cerr << "usage: format_text [--renderer CPU] [--registers D1 D3] INPUT_RAM OUTPUT_RAM MEMORY_MS5D FONT_MS5D FORMAT_CPU ARGUMENT_CPU CURSOR STYLE OUTPUT_PORTS\n";
        return 2;
    }
    std::uint32_t format_address;
    std::uint32_t arguments_address;
    std::uint32_t cursor;
    std::uint32_t style;
    if (!parse_integer(argv[5], 0xffffffU, format_address) ||
        !parse_integer(argv[6], 0xffffffU, arguments_address) ||
        !parse_integer(argv[7], 0xffffU, cursor) ||
        !parse_integer(argv[8], 0xffffU, style)) {
        std::cerr << "CPU addresses must be 24-bit and cursor/style 16-bit decimal or 0x-prefixed integers\n";
        return 1;
    }
    if (registers && (d1 & 0xffffU) != style) {
        std::cerr << "STYLE must match D1 low16 bits in registers mode\n";
        return 1;
    }
    std::uint16_t final_style = static_cast<std::uint16_t>(style);
    const std::string input_paths[3] = {argv[1], argv[3], argv[4]};
    const std::string output_paths[2] = {argv[2], argv[9]};
    if (same_file(output_paths[0], output_paths[1])) {
        std::cerr << "outputs must identify distinct files\n";
        return 1;
    }
    for (std::size_t output = 0; output < 2; ++output) {
        for (std::size_t input = 0; input < 3; ++input) {
            if (same_file(output_paths[output], input_paths[input])) {
                std::cerr << "outputs must be distinct from RAM and resource inputs\n";
                return 1;
            }
        }
    }
    std::vector<std::uint8_t> ram;
    if (!read_bytes(input_paths[0], 65536, true, ram)) {
        return 1;
    }
    std::vector<ms5::FixedDataResource> resources(1);
    ms5::FixedDataResource font;
    std::string error;
    if (!ms5::load_fixed_data_resource(input_paths[1], resources[0], error) ||
        !ms5::load_fixed_data_resource(input_paths[2], font, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    const std::vector<std::uint8_t> argument_bytes;
    std::vector<ms5::VideoPortWrite> writes;
    if (!ms5::format_fixed_text(ram, resources, font, format_address,
                                arguments_address, argument_bytes,
                                static_cast<std::uint16_t>(cursor),
                                static_cast<std::uint16_t>(style), writes, error, renderer, registers ? &final_style : NULL, NULL, registers ? &d3 : NULL)) {
        std::cerr << error << '\n';
        return 1;
    }
    // Diagnostic records: byte size, BE32 CPU port address, BE32 value.
    std::vector<std::uint8_t> port_bytes;
    for (std::size_t index = 0; index < writes.size(); ++index) {
        const ms5::VideoPortWrite& write = writes[index];
        port_bytes.push_back(write.size);
        for (int shift = 24; shift >= 0; shift -= 8) {
            port_bytes.push_back(static_cast<std::uint8_t>((write.address >> shift) & 0xffU));
        }
        for (int shift = 24; shift >= 0; shift -= 8) {
            port_bytes.push_back(static_cast<std::uint8_t>((write.value >> shift) & 0xffU));
        }
    }
    // Complete all semantic and alias checks before truncating either output.
    const std::uint8_t empty_output = 0;
    if (!write_bytes(output_paths[0], &ram[0], ram.size()) ||
        !write_bytes(output_paths[1], port_bytes.empty() ? &empty_output : &port_bytes[0],
                     port_bytes.size())) {
        return 1;
    }
    if (registers) {
        d1 = (d1 & 0xffff0000U) | final_style;
        std::cout << "{\"d1\":" << d1 << ",\"d3\":" << d3 << "}\n";
    }
    return 0;
}
