#include "ms5/video_control.h"

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

void write_port(std::ostream& output, const ms5::VideoPortWrite& write) {
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
    output.write(bytes, sizeof(bytes));
}

void write_word(std::ostream& output, std::uint16_t value) {
    const char bytes[2] = {
        static_cast<char>((value >> 8) & 0xffU),
        static_cast<char>(value & 0xffU)
    };
    output.write(bytes, sizeof(bytes));
}

int run_batch() {
    char input[4];
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
        const std::uint16_t shadow = static_cast<std::uint16_t>(
            (static_cast<unsigned char>(input[0]) << 8) |
            static_cast<unsigned char>(input[1]));
        const std::uint16_t value = static_cast<std::uint16_t>(
            (static_cast<unsigned char>(input[2]) << 8) |
            static_cast<unsigned char>(input[3]));
        std::vector<std::uint8_t> ram(65536U, 0U);
        ram[0x4d90U] = static_cast<std::uint8_t>(shadow >> 8);
        ram[0x4d91U] = static_cast<std::uint8_t>(shadow & 0xffU);
        std::uint16_t before = 0U;
        std::uint16_t after = 0U;
        std::vector<ms5::VideoPortWrite> writes;
        std::string error;
        if (!ms5::query_video_control(ram, before, error) ||
            !ms5::set_video_control(ram, value, writes, error) ||
            !ms5::query_video_control(ram, after, error)) {
            std::cerr << error << '\n';
            return 1;
        }
        if (writes.size() != 1U) {
            std::cerr << "batch requires exactly one video port write\n";
            return 1;
        }
        const std::uint16_t final_shadow = static_cast<std::uint16_t>(
            (static_cast<std::uint16_t>(ram[0x4d90U]) << 8) | ram[0x4d91U]);
        // Diagnostic record: three BE16 values, followed by one port record.
        write_word(std::cout, before);
        write_word(std::cout, after);
        write_word(std::cout, final_shadow);
        write_port(std::cout, writes[0]);
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
    if (argc != 5) {
        std::cerr << "usage: video_control INPUT_RAM OUTPUT_RAM OUTPUT_PORTS VALUE\n"
                  << "       video_control --batch\n";
        return 2;
    }
    std::uint32_t value = 0U;
    if (!parse_integer(argv[4], 0xffffU, value)) {
        std::cerr << "VALUE must be decimal or 0x-prefixed uint16\n";
        return 1;
    }
    const std::string ram_path(argv[1]);
    const std::string output_ram_path(argv[2]);
    const std::string output_ports_path(argv[3]);
    if (same_file(ram_path, output_ram_path) ||
        same_file(ram_path, output_ports_path) ||
        same_file(output_ram_path, output_ports_path)) {
        std::cerr << "outputs must be distinct from the input and each other\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    if (!read_ram(ram_path, ram)) {
        return 1;
    }
    std::vector<ms5::VideoPortWrite> writes;
    std::uint16_t query = 0U;
    std::string error;
    if (!ms5::set_video_control(ram, static_cast<std::uint16_t>(value), writes, error) ||
        !ms5::query_video_control(ram, query, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output_ram(output_ram_path.c_str(), std::ios::binary | std::ios::trunc);
    std::ofstream output_ports(output_ports_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output_ram || !output_ports) {
        std::cerr << "cannot open output files\n";
        return 1;
    }
    output_ram.write(reinterpret_cast<const char*>(&ram[0]),
                     static_cast<std::streamsize>(ram.size()));
    // Diagnostic records: byte size, BE32 CPU port address, BE32 value.
    for (std::size_t index = 0U; index < writes.size(); ++index) {
        write_port(output_ports, writes[index]);
    }
    output_ram.close();
    output_ports.close();
    if (!output_ram || !output_ports) {
        std::cerr << "cannot write output files\n";
        return 1;
    }
    std::cout << "{\"value\":" << query << "}\n";
    return 0;
}
