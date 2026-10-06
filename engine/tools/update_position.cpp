#include "ms5/position_state.h"

#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

std::uint32_t read_be_long(const std::vector<std::uint8_t>& bytes,
                           std::size_t offset) {
    return (static_cast<std::uint32_t>(bytes[offset]) << 24) |
           (static_cast<std::uint32_t>(bytes[offset + 1]) << 16) |
           (static_cast<std::uint32_t>(bytes[offset + 2]) << 8) |
           static_cast<std::uint32_t>(bytes[offset + 3]);
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: update_position INPUT OUTPUT\n";
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
    const std::size_t record_size = 8 + 65536;
    if (bytes.empty() || bytes.size() % record_size != 0) {
        std::cerr << "input must contain a nonempty sequence of 65544-byte records\n";
        return 1;
    }
    if (bytes.size() > static_cast<std::size_t>(
            (std::numeric_limits<std::streamsize>::max)())) {
        std::cerr << "input exceeds output stream size limit\n";
        return 1;
    }
    for (std::size_t offset = 0; offset < bytes.size(); offset += record_size) {
        const std::uint32_t address = read_be_long(bytes, offset);
        const std::uint32_t advance = read_be_long(bytes, offset + 4);
        if (advance > 1) {
            std::cerr << "advance must be 0 or 1 in record "
                      << offset / record_size << '\n';
            return 1;
        }
        std::string error;
        if (!ms5::update_position(&bytes[offset + 8], 65536, address,
                                  advance != 0, error)) {
            std::cerr << "invalid record " << offset / record_size
                      << ": " << error << '\n';
            return 1;
        }
    }
    // Every record has been checked before the output can be truncated.
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
