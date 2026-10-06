#include "ms5/object_lists.h"

#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
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
    if (argc != 4) {
        std::cerr << "usage: init_objects RESOURCE.ms5i RAM_INPUT RAM_OUTPUT\n";
        return 2;
    }
    const std::string resource_path(argv[1]);
    const std::string input_path(argv[2]);
    const std::string output_path(argv[3]);
    if (same_file(resource_path, input_path) || same_file(input_path, output_path) ||
        same_file(resource_path, output_path)) {
        std::cerr << "resource, RAM input and RAM output must be distinct files\n";
        return 1;
    }
    std::string error;
    std::vector<ms5::ObjectBootRecord> records;
    if (!ms5::load_object_boot_resource(resource_path, records, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ifstream input(input_path.c_str(), std::ios::binary);
    if (!input) {
        std::cerr << "cannot open RAM input\n";
        return 1;
    }
    std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(input)),
                                   std::istreambuf_iterator<char>());
    if (input.bad()) {
        std::cerr << "cannot read RAM input\n";
        return 1;
    }
    input.close();
    if (bytes.empty() || bytes.size() % 65536 != 0) {
        std::cerr << "RAM input must be a nonempty sequence of 65536-byte images\n";
        return 1;
    }
    if (bytes.size() > static_cast<std::size_t>(
            (std::numeric_limits<std::streamsize>::max)())) {
        std::cerr << "RAM input exceeds output stream size limit\n";
        return 1;
    }
    for (std::size_t offset = 0; offset < bytes.size(); offset += 65536) {
        if (!ms5::initialize_object_lists(&bytes[offset], 65536, records, error)) {
            std::cerr << error << '\n';
            return 1;
        }
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open RAM output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&bytes[0]),
                 static_cast<std::streamsize>(bytes.size()));
    output.close();
    if (!output) {
        std::cerr << "cannot write RAM output\n";
        return 1;
    }
    return 0;
}
