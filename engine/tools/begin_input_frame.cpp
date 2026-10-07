#include "ms5/input_frame.h"
#include "ms5/input_sampler.h"

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
    bool registers_mode = false;
    std::uint32_t d1 = 0U, d3 = 0U;
    if (argc > 1 && std::string(argv[1]) == "--registers") {
        if (argc < 4 || !parse_integer(argv[2], 0xffffffffU, d1) ||
            !parse_integer(argv[3], 0xffffffffU, d3)) {
            std::cerr << "--registers requires decimal or 0x-prefixed uint32 D1 and D3\n";
            return 1;
        }
        registers_mode = true;
        argc -= 3;
        argv += 3;
    }
    if (argc != 12) {
        std::cerr << "usage: begin_input_frame [--registers D1 D3] INPUT_RAM STREAMS_MS5D TABLE_MS5D OUTPUT_RAM OBJECT_ADDRESS STYLE SYSTEM P1_RAW P2_RAW P1_GAME P2_GAME\n";
        return 2;
    }
    std::uint32_t object_address = 0U;
    std::uint32_t style = 0U;
    if (!parse_integer(argv[5], 0xffffffffU, object_address) ||
        !parse_integer(argv[6], 0xffffU, style)) {
        std::cerr << "OBJECT_ADDRESS must be decimal or 0x-prefixed uint32; STYLE must be decimal or 0x-prefixed uint16\n";
        return 1;
    }
    if (registers_mode && style != (d1 & 0xffffU)) {
        std::cerr << "STYLE must match D1.low16\n";
        return 1;
    }
    std::uint32_t values[5] = {0U, 0U, 0U, 0U, 0U};
    for (unsigned int index = 0U; index < 5U; ++index) {
        if (!parse_integer(argv[index + 7U], 0xffU, values[index])) {
            std::cerr << "SYSTEM, P1_RAW, P2_RAW, P1_GAME and P2_GAME must be decimal or 0x-prefixed uint8\n";
            return 1;
        }
    }
    const std::string ram_path(argv[1]);
    const std::string streams_path(argv[2]);
    const std::string table_path(argv[3]);
    const std::string output_path(argv[4]);
    if (same_file(ram_path, output_path) || same_file(streams_path, output_path) ||
        same_file(table_path, output_path)) {
        std::cerr << "RAM output must be distinct from all inputs\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    if (!read_ram(ram_path, ram)) {
        return 1;
    }
    ms5::FixedDataResource streams;
    ms5::FixedDataResource table;
    ms5::InputPortSamples ports;
    ports.system = static_cast<std::uint8_t>(values[0]);
    ports.player1_raw = static_cast<std::uint8_t>(values[1]);
    ports.player2_raw = static_cast<std::uint8_t>(values[2]);
    ports.player1_game = static_cast<std::uint8_t>(values[3]);
    ports.player2_game = static_cast<std::uint8_t>(values[4]);
    ms5::InputFrameResult result;
    std::string error;
    if (!ms5::load_fixed_data_resource(streams_path, streams, error) ||
        !ms5::load_fixed_data_resource(table_path, table, error) ||
        !ms5::begin_input_frame(ram, streams, table, ports, object_address,
                               static_cast<std::uint16_t>(style), result, error,
                               registers_mode ? &d1 : NULL, registers_mode ? &d3 : NULL)) {
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
    std::cout << "{\"next_pc\":" << result.next_pc
              << ",\"callback\":" << result.callback
              << ",\"callback_context\":" << result.callback_context
              << ",\"style\":" << result.style
              << ",\"read_count\":" << static_cast<unsigned int>(result.read_count);
    if (registers_mode) std::cout << ",\"d1\":" << d1 << ",\"d3\":" << d3;
    std::cout << "}\n";
    return 0;
}
