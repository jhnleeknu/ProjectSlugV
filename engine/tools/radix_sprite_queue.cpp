#include "ms5/sprite_queue.h"

#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

bool same_file(const std::string& left, const std::string& right) {
    struct stat left_stat;
    struct stat right_stat;
    return left == right ||
        (stat(left.c_str(), &left_stat) == 0 &&
         stat(right.c_str(), &right_stat) == 0 &&
         left_stat.st_dev == right_stat.st_dev &&
         left_stat.st_ino == right_stat.st_ino);
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: radix_sprite_queue INPUT OUTPUT\n";
        return 2;
    }
    const std::string input_path(argv[1]);
    const std::string output_path(argv[2]);
    if (same_file(input_path, output_path)) {
        std::cerr << "input and output must be distinct files\n";
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
    if (!ms5::radix_sort_sprite_queue(ram, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    // All arguments and RAM invariants are checked before opening the output.
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&ram[0]), 65536);
    output.close();
    if (!output) {
        std::cerr << "cannot write output\n";
        return 1;
    }
    return 0;
}
