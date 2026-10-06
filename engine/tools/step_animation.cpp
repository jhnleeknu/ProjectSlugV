#include "ms5/animation_step.h"

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
        if (digit >= base || value > (maximum - digit) / base) {
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
    if (argc != 7) {
        std::cerr << "usage: step_animation INPUT_RAM INPUT_SCRIPT OUTPUT_RAM OUTPUT_STATUS OBJECT_OFFSET SCRIPT_BASE\n";
        return 2;
    }
    std::uint32_t object_offset;
    std::uint32_t script_base;
    if (!parse_integer(argv[5], 65535U, object_offset) ||
        !parse_integer(argv[6], 0x1000000U, script_base)) {
        std::cerr << "object offset and script base must be decimal or 0x-prefixed integers in range\n";
        return 1;
    }
    const std::string ram_path(argv[1]);
    const std::string script_path(argv[2]);
    const std::string output_ram(argv[3]);
    const std::string output_status(argv[4]);
    if (same_file(output_ram, ram_path) || same_file(output_ram, script_path) ||
        same_file(output_status, ram_path) || same_file(output_status, script_path) ||
        same_file(output_ram, output_status)) {
        std::cerr << "outputs must identify files distinct from both inputs and each other\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    std::vector<std::uint8_t> script;
    if (!read_bytes(ram_path, 65536, true, ram) ||
        !read_bytes(script_path, 0x1000000, false, script)) {
        return 1;
    }
    bool carry = false;
    std::string error;
    if (!ms5::step_animation(ram, object_offset, script, script_base, carry, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    const std::uint8_t status[4] = {0, 0, 0, static_cast<std::uint8_t>(carry ? 1 : 0)};
    // All semantic and path checks complete before either output is truncated.
    if (!write_bytes(output_ram, &ram[0], ram.size()) ||
        !write_bytes(output_status, status, 4)) {
        return 1;
    }
    return 0;
}
