#include "ms5/palette_transfer.h"

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

} // namespace

int main(int argc, char** argv) {
    if (argc != 6) {
        std::cerr << "usage: transfer_palette_banks INPUT_RAM INPUT_BANKS OUTPUT_RAM OUTPUT_BANKS OUTPUT_DISPLAY\n";
        return 2;
    }
    const std::string paths[5] = {argv[1], argv[2], argv[3], argv[4], argv[5]};
    for (std::size_t output = 2; output < 5; ++output) {
        for (std::size_t other = 0; other < output; ++other) {
            if (same_file(paths[output], paths[other])) {
                std::cerr << "output files must be distinct from inputs and one another\n";
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
    if (!ms5::transfer_palette_banks(ram, palette0, palette1, display_bank, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    for (std::size_t index = 0; index < 8192; ++index) {
        banks[index] = palette0[index];
        banks[8192 + index] = palette1[index];
    }
    if (!write_bytes(paths[2], &ram[0], ram.size()) ||
        !write_bytes(paths[3], &banks[0], banks.size()) ||
        !write_bytes(paths[4], &display_bank, 1)) {
        return 1;
    }
    return 0;
}
