#include "ms5/fixed_text.h"

#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>
#include <sys/stat.h>

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: trace_fixed_text INPUT OUTPUT\n";
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
    const std::vector<std::uint8_t> script((std::istreambuf_iterator<char>(input)),
                                         std::istreambuf_iterator<char>());
    if (input.bad()) {
        std::cerr << "cannot read input\n";
        return 1;
    }
    input.close();
    std::vector<ms5::FixedWrite> writes;
    std::string error;
    if (!ms5::trace_fixed_text(script, 0, 0, writes, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 1;
    }
    for (std::size_t index = 0; index < writes.size(); ++index) {
        const ms5::FixedWrite& write = writes[index];
        const char bytes[4] = {
            static_cast<char>(write.address >> 8),
            static_cast<char>(write.address & 0xffU),
            static_cast<char>(write.value >> 8),
            static_cast<char>(write.value & 0xffU)
        };
        output.write(bytes, sizeof(bytes));
    }
    output.close();
    if (!output) {
        std::cerr << "cannot write output\n";
        return 1;
    }
    return 0;
}
