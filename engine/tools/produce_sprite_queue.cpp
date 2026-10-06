#include "ms5/sprite_producer.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>
#include <sys/stat.h>
#include <unistd.h>

namespace {

bool parse_u32(const std::string& text, std::uint32_t& result) {
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
        if (digit >= base ||
            value > (std::numeric_limits<std::uint32_t>::max() - digit) / base) {
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
    const bool init = argc == 4 && std::string(argv[1]) == "init";
    const bool submit = argc == 9 && std::string(argv[1]) == "submit";
    if (!init && !submit) {
        std::cerr << "usage: produce_sprite_queue init INPUT OUTPUT\n"
                     "       produce_sprite_queue submit INPUT OUTPUT STATUS D0 D1 D5 D7\n";
        return 2;
    }
    std::uint32_t registers[4] = {0, 0, 0, 0};
    if (submit) {
        for (unsigned int index = 0; index < 4; ++index) {
            if (!parse_u32(argv[5 + index], registers[index])) {
                std::cerr << "register values must be decimal or 0x-prefixed uint32 integers\n";
                return 1;
            }
        }
    }
    const std::string input_path(argv[2]);
    const std::string output_path(argv[3]);
    const std::string status_path = submit ? argv[4] : "";
    if (same_file(input_path, output_path) ||
        (submit && (same_file(input_path, status_path) ||
                    same_file(output_path, status_path)))) {
        std::cerr << "input, output and status paths must identify distinct files\n";
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
    ms5::SpriteSubmitStatus status = ms5::SpriteAccepted;
    const bool valid = init ? ms5::initialize_sprite_queue(ram, error) :
        ms5::submit_sprite(ram, registers[0], registers[1], registers[2],
                           registers[3], status, error);
    if (!valid) {
        std::cerr << error << '\n';
        return 1;
    }
    // All arguments and RAM invariants are checked before opening outputs.
    if (!write_bytes(output_path, &ram[0], ram.size())) {
        return 1;
    }
    if (submit) {
        const std::uint32_t value = static_cast<std::uint32_t>(status);
        const std::uint8_t bytes[4] = {
            static_cast<std::uint8_t>(value >> 24),
            static_cast<std::uint8_t>(value >> 16),
            static_cast<std::uint8_t>(value >> 8),
            static_cast<std::uint8_t>(value)
        };
        if (!write_bytes(status_path, bytes, 4)) {
            return 1;
        }
    }
    return 0;
}
