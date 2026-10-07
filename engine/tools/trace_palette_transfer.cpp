#include "ms5/palette_transfer.h"
#include "ms5/video_port.h"

#include <fstream>
#include <iostream>
#include <cstdlib>
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
    // Resolve an existing parent as well so two names for a not-yet-created
    // output (including paths through a directory symlink) cannot collide.
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

bool read_exact(const std::string& path, std::size_t size,
                std::vector<std::uint8_t>& bytes) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        std::cerr << "cannot open input: " << path << '\n';
        return false;
    }
    if (input.tellg() != static_cast<std::streamoff>(size)) {
        std::cerr << "input must contain exactly " << size << " bytes: " << path << '\n';
        return false;
    }
    input.seekg(0, std::ios::beg);
    bytes.resize(size);
    if (!input.read(reinterpret_cast<char*>(&bytes[0]),
                    static_cast<std::streamsize>(size))) {
        std::cerr << "cannot read input: " << path << '\n';
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
    if (argc != 7) {
        std::cerr << "usage: trace_palette_transfer INPUT_RAM INPUT_BANKS OUTPUT_RAM OUTPUT_BANKS OUTPUT_PORTS D0\n";
        return 2;
    }
    std::uint32_t d0 = 0U;
    if (!parse_integer(argv[6], 0xffffffffU, d0)) {
        std::cerr << "D0 must be decimal or 0x-prefixed uint32\n";
        return 1;
    }
    const std::string paths[5] = {argv[1], argv[2], argv[3], argv[4], argv[5]};
    for (std::size_t output = 1; output < 5; ++output) {
        for (std::size_t other = 0; other < output; ++other) {
            if (same_file(paths[output], paths[other])) {
                std::cerr << "all input and output paths must be distinct\n";
                return 1;
            }
        }
    }
    std::vector<std::uint8_t> ram;
    std::vector<std::uint8_t> banks;
    if (!read_exact(paths[0], 65536, ram) || !read_exact(paths[1], 16384, banks)) {
        return 1;
    }
    std::vector<std::uint8_t> palette0(banks.begin(), banks.begin() + 8192);
    std::vector<std::uint8_t> palette1(banks.begin() + 8192, banks.end());
    std::uint8_t display_bank = 0;
    std::string error;
    std::vector<ms5::VideoPortWrite> writes;
    if (!ms5::transfer_palette_banks_traced(ram, palette0, palette1, display_bank, d0, writes, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    for (std::size_t index = 0; index < 8192; ++index) {
        banks[index] = palette0[index];
        banks[8192 + index] = palette1[index];
    }
    if (!write_bytes(paths[2], &ram[0], ram.size()) ||
        !write_bytes(paths[3], &banks[0], banks.size())) {
        return 1;
    }
    std::ofstream output_writes(paths[4].c_str(), std::ios::binary | std::ios::trunc);
    if (!output_writes) {
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
        output_writes.write(bytes, sizeof(bytes));
    }
    output_writes.close();
    if (!output_writes) {
        std::cerr << "cannot write port output\n";
        return 1;
    }
    std::cout << "{\"display_bank\":" << static_cast<unsigned int>(display_bank)
              << ",\"d0\":" << d0 << ",\"writes\":" << writes.size() << "}\n";
    return 0;
}
