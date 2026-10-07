#include "ms5/input_status.h"
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
    const bool sample = argc > 1 && std::string(argv[1]) == "--sample";
    if ((!sample && argc != 4) || (sample && argc != 11)) {
        std::cerr << "usage: update_input_status INPUT_RAM TABLE_MS5D OUTPUT_RAM\n"
                  << "       update_input_status --sample INPUT_RAM STREAMS_MS5D TABLE_MS5D OUTPUT_RAM SYSTEM P1_RAW P2_RAW P1_GAME P2_GAME\n";
        return 2;
    }
    std::uint32_t values[5] = {0U, 0U, 0U, 0U, 0U};
    if (sample) {
        for (unsigned int index = 0U; index < 5U; ++index) {
            if (!parse_integer(argv[index + 6U], 0xffU, values[index])) {
                std::cerr << "SYSTEM, P1_RAW, P2_RAW, P1_GAME and P2_GAME must be decimal or 0x-prefixed uint8\n";
                return 1;
            }
        }
    }
    const std::string ram_path(argv[sample ? 2 : 1]);
    const std::string table_path(argv[sample ? 4 : 2]);
    const std::string output_path(argv[sample ? 5 : 3]);
    const std::string streams_path = sample ? argv[3] : "";
    if (same_file(ram_path, output_path) || same_file(table_path, output_path) ||
        (sample && same_file(streams_path, output_path))) {
        std::cerr << "RAM output must be distinct from all inputs\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    if (!read_ram(ram_path, ram)) {
        return 1;
    }
    ms5::FixedDataResource table;
    ms5::FixedDataResource streams;
    ms5::InputPortSamples ports;
    ports.system = static_cast<std::uint8_t>(values[0]);
    ports.player1_raw = static_cast<std::uint8_t>(values[1]);
    ports.player2_raw = static_cast<std::uint8_t>(values[2]);
    ports.player1_game = static_cast<std::uint8_t>(values[3]);
    ports.player2_game = static_cast<std::uint8_t>(values[4]);
    std::uint8_t read_count = 0U;
    std::string error;
    if (!ms5::load_fixed_data_resource(table_path, table, error) ||
        (sample && !ms5::load_fixed_data_resource(streams_path, streams, error))) {
        std::cerr << error << '\n';
        return 1;
    }
    const bool succeeded = sample ? ms5::step_input(ram, streams, table, ports, read_count, error) :
                                    ms5::update_input_status(ram, table, error);
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
    std::cout << "{\"status\":" << static_cast<unsigned int>(ram[0xf007U]);
    if (sample) {
        std::cout << ",\"read_count\":" << static_cast<unsigned int>(read_count);
    }
    std::cout << "}\n";
    return 0;
}
