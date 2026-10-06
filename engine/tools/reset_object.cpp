#include "ms5/object_state.h"

#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <string>
#include <vector>
#include <sys/stat.h>

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: reset_object INPUT OUTPUT\n";
        return 2;
    }
    const std::string input_path(argv[1]);
    const std::string output_path(argv[2]);
    struct stat input_stat;
    struct stat output_stat;
    if (input_path == output_path ||
        (stat(input_path.c_str(), &input_stat) == 0 &&
         stat(output_path.c_str(), &output_stat) == 0 &&
         input_stat.st_dev == output_stat.st_dev &&
         input_stat.st_ino == output_stat.st_ino)) {
        std::cerr << "input and output must be distinct files\n";
        return 1;
    }
    std::ifstream input(input_path.c_str(), std::ios::binary);
    if (!input) {
        std::cerr << "cannot open input\n";
        return 1;
    }
    std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(input)),
                                   std::istreambuf_iterator<char>());
    if (input.bad()) {
        std::cerr << "cannot read input\n";
        return 1;
    }
    input.close();
    if (bytes.empty() || bytes.size() % 0xc4 != 0) {
        std::cerr << "input must contain a nonempty sequence of 196-byte objects\n";
        return 1;
    }
    if (bytes.size() > static_cast<std::size_t>(
            (std::numeric_limits<std::streamsize>::max)())) {
        std::cerr << "input exceeds output stream size limit\n";
        return 1;
    }
    for (std::size_t offset = 0; offset < bytes.size(); offset += 0xc4) {
        if (!ms5::reset_object_fields(&bytes[offset], 0xc4)) {
            std::cerr << "cannot reset object\n";
            return 1;
        }
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&bytes[0]),
                 static_cast<std::streamsize>(bytes.size()));
    output.close();
    if (!output) {
        std::cerr << "cannot write output\n";
        return 1;
    }
    return 0;
}
