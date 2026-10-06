#include "ms5/palette_allocator.h"

#include <cerrno>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

bool parse_number(const char* text, unsigned long maximum,
                  unsigned long& value) {
    if (text[0] == '\0' || text[0] == '-' || text[0] == '+' ||
        text[0] == ' ' || text[0] == '\t' || text[0] == '\n' ||
        text[0] == '\r' || text[0] == '\v' || text[0] == '\f') {
        return false;
    }
    char* end = NULL;
    errno = 0;
    value = std::strtoul(text, &end, 0);
    return errno == 0 && end != text && *end == '\0' && value <= maximum;
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: palette_allocator acquire|release INPUT OUTPUT OBJ [ID FLAGS]\n";
        return 2;
    }
    const std::string operation(argv[1]);
    const bool acquire = operation == "acquire";
    if ((!acquire && operation != "release") ||
        argc != (acquire ? 7 : 5)) {
        std::cerr << "usage: palette_allocator acquire|release INPUT OUTPUT OBJ [ID FLAGS]\n";
        return 2;
    }
    unsigned long object = 0;
    unsigned long id = 0;
    unsigned long flags = 0;
    if (!parse_number(argv[4], 65535, object) ||
        (acquire && (!parse_number(argv[5], 65535, id) ||
                     !parse_number(argv[6], 255, flags)))) {
        std::cerr << "invalid object offset, palette ID or flags\n";
        return 2;
    }
    const std::string input_path(argv[2]);
    const std::string output_path(argv[3]);
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
    std::vector<std::uint8_t> ram((std::istreambuf_iterator<char>(input)),
                                 std::istreambuf_iterator<char>());
    if (input.bad()) {
        std::cerr << "cannot read input\n";
        return 1;
    }
    input.close();
    if (ram.size() != 65536) {
        std::cerr << "input must contain exactly 65536 RAM bytes\n";
        return 1;
    }
    bool allocated = false;
    std::string error;
    const bool succeeded = acquire ?
        ms5::acquire_palette(ram, static_cast<std::size_t>(object),
                             static_cast<std::uint16_t>(id),
                             static_cast<std::uint8_t>(flags), allocated, error) :
        ms5::release_palettes(ram, static_cast<std::size_t>(object), error);
    if (!succeeded) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output(output_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output\n";
        return 1;
    }
    output.write(reinterpret_cast<const char*>(&ram[0]),
                 static_cast<std::streamsize>(ram.size()));
    output.close();
    if (!output) {
        std::cerr << "cannot write output\n";
        return 1;
    }
    if (acquire) {
        std::cout << (allocated ? 1 : 0) << '\n';
    }
    return 0;
}
