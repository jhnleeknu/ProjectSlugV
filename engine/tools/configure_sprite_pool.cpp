#include "ms5/sprite_pool.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>
#include <sys/stat.h>
#include <unistd.h>

namespace {

bool parse_u16(const std::string& text, std::uint16_t& result) {
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
    std::uint16_t value = 0;
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
        if (digit >= base ||
            value > (std::numeric_limits<std::uint16_t>::max() - digit) / base) {
            return false;
        }
        value = value * base + digit;
    }
    result = value;
    return true;
}

std::string canonical_path(const std::string& path, unsigned int depth = 0) {
    char* resolved = realpath(path.c_str(), NULL);
    if (resolved != NULL) {
        const std::string result(resolved);
        std::free(resolved);
        return result;
    }
    // Resolve the parent too, so aliases of a not-yet-created output are caught.
    const std::size_t slash = path.find_last_of('/');
    const std::string parent = slash == std::string::npos ? "." :
        (slash == 0 ? "/" : path.substr(0, slash));
    const std::string name = slash == std::string::npos ? path : path.substr(slash + 1);
    struct stat link_stat;
    if (depth < 40 && lstat(path.c_str(), &link_stat) == 0 &&
        S_ISLNK(link_stat.st_mode)) {
        // A dangling output symlink can still alias another future output.
        const std::size_t capacity = link_stat.st_size > 0 ?
            static_cast<std::size_t>(link_stat.st_size) + 1 : 4096;
        std::vector<char> target(capacity);
        const ssize_t length = readlink(path.c_str(), &target[0], target.size());
        if (length > 0 && static_cast<std::size_t>(length) < target.size()) {
            const std::string target_path(&target[0], static_cast<std::size_t>(length));
            return canonical_path(target_path[0] == '/' ? target_path :
                                  parent + "/" + target_path, depth + 1);
        }
    }
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

bool write_bytes(const std::string& path, const std::uint8_t* data,
                 std::size_t size) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output: " << path << '\n';
        return false;
    }
    output.write(reinterpret_cast<const char*>(data),
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
        std::cerr << "usage: configure_sprite_pool INPUT OUTPUT SELECT LOWER UPPER\n";
        return 2;
    }
    std::uint16_t values[3] = {0, 0, 0};
    for (unsigned int index = 0; index < 3; ++index) {
        if (!parse_u16(argv[3 + index], values[index])) {
            std::cerr << "values must be decimal or 0x-prefixed uint16 integers\n";
            return 1;
        }
    }
    const std::string input_path(argv[1]);
    const std::string output_path(argv[2]);
    if (same_file(input_path, output_path)) {
        std::cerr << "input and output paths must identify distinct files\n";
        return 1;
    }
    std::ifstream input(input_path.c_str(), std::ios::binary);
    if (!input) {
        std::cerr << "cannot open input\n";
        return 1;
    }
    std::vector<std::uint8_t> ram(65536);
    input.read(reinterpret_cast<char*>(&ram[0]), 65536);
    if (input.gcount() != 65536 || input.bad()) {
        std::cerr << "input must contain exactly 65536 bytes\n";
        return 1;
    }
    char extra;
    if (input.get(extra) || input.bad() || !input.eof()) {
        std::cerr << "input must contain exactly 65536 bytes\n";
        return 1;
    }
    input.close();
    std::string error;
    if (!ms5::configure_sprite_pool(ram, values[0], values[1], values[2], error)) {
        std::cerr << error << '\n';
        return 1;
    }
    return write_bytes(output_path, &ram[0], ram.size()) ? 0 : 1;
}
