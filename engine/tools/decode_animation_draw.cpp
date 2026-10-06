#include "ms5/animation_draw.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

bool parse_offset(const std::string& text, std::size_t& result) {
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
    std::size_t value = 0;
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
        if (digit >= base || value > (65535U - digit) / base) {
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

bool read_bytes(const std::string& path, std::size_t size,
                std::vector<std::uint8_t>& bytes) {
    std::ifstream input(path.c_str(), std::ios::binary);
    if (!input) {
        std::cerr << "cannot open input: " << path << '\n';
        return false;
    }
    bytes.resize(size);
    input.read(reinterpret_cast<char*>(&bytes[0]),
               static_cast<std::streamsize>(size));
    if (input.gcount() != static_cast<std::streamsize>(size) || input.bad()) {
        std::cerr << "input must contain exactly " << size << " bytes: " << path << '\n';
        return false;
    }
    char extra;
    if (input.get(extra) || input.bad() || !input.eof()) {
        std::cerr << "input must contain exactly " << size << " bytes: " << path << '\n';
        return false;
    }
    return true;
}

void write_be_long(std::uint8_t* bytes, std::uint32_t value) {
    bytes[0] = static_cast<std::uint8_t>(value >> 24);
    bytes[1] = static_cast<std::uint8_t>(value >> 16);
    bytes[2] = static_cast<std::uint8_t>(value >> 8);
    bytes[3] = static_cast<std::uint8_t>(value);
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: decode_animation_draw INPUT_RAM INPUT_OPERAND OUTPUT OBJECT_OFFSET\n";
        return 2;
    }
    std::size_t object_offset;
    if (!parse_offset(argv[4], object_offset)) {
        std::cerr << "object offset must be a decimal or 0x-prefixed integer from 0 to 65535\n";
        return 1;
    }
    const std::string ram_path(argv[1]);
    const std::string operand_path(argv[2]);
    const std::string output_path(argv[3]);
    if (same_file(ram_path, output_path) || same_file(operand_path, output_path)) {
        std::cerr << "output must identify a file distinct from both inputs\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    std::vector<std::uint8_t> operand;
    if (!read_bytes(ram_path, 65536, ram) || !read_bytes(operand_path, 7, operand)) {
        return 1;
    }
    ms5::AnimationDraw result;
    std::string error;
    if (!ms5::decode_animation_draw(ram, object_offset, operand, result, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::uint8_t bytes[20];
    write_be_long(bytes, result.skipped ? 1U : 0U);
    write_be_long(bytes + 4, result.d0);
    write_be_long(bytes + 8, result.d1);
    write_be_long(bytes + 12, result.d5);
    write_be_long(bytes + 16, result.d7);
    // All input checks complete before the output can be truncated.
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output: " << output_path << '\n';
        return 1;
    }
    output.write(reinterpret_cast<const char*>(bytes), 20);
    output.close();
    if (!output) {
        std::cerr << "cannot write output: " << output_path << '\n';
        return 1;
    }
    return 0;
}
