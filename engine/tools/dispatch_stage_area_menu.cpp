#include "ms5/stage_area_menu.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

std::string resolved_path(const std::string& path) {
    char* resolved = realpath(path.c_str(), NULL);
    if (resolved != NULL) {
        const std::string result(resolved);
        std::free(resolved);
        return result;
    }
    const std::string::size_type slash = path.find_last_of('/');
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
    return left == right || resolved_path(left) == resolved_path(right) ||
        (stat(left.c_str(), &left_stat) == 0 &&
         stat(right.c_str(), &right_stat) == 0 &&
         left_stat.st_dev == right_stat.st_dev &&
         left_stat.st_ino == right_stat.st_ino);
}

std::string stage_resource_path(const std::string& directory,
                                const std::string& filename) {
    if (directory.empty() || directory[directory.size() - 1U] == '/') {
        return directory + filename;
    }
    return directory + "/" + filename;
}

bool read_ram(const std::string& path, std::vector<std::uint8_t>& ram) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        std::cerr << "cannot open RAM input\n";
        return false;
    }
    if (input.tellg() != static_cast<std::streamoff>(65536U)) {
        std::cerr << "RAM input must contain exactly 65536 bytes\n";
        return false;
    }
    input.seekg(0, std::ios::beg);
    ram.resize(65536U);
    if (!input.read(reinterpret_cast<char*>(&ram[0]), 65536)) {
        std::cerr << "cannot read RAM input\n";
        return false;
    }
    return true;
}

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
        if (digit >= base || digit > maximum || value > (maximum - digit) / base) {
            return false;
        }
        value = value * base + digit;
    }
    result = value;
    return true;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 11) {
        std::cerr << "usage: dispatch_stage_area_menu INPUT_RAM MENU_MS5D FONT_MS5D STAGES_DIRECTORY OUTPUT_RAM OUTPUT_PORTS EVENT D1 D3 CALLBACK_STACK\n";
        return 2;
    }
    std::uint32_t event = 0U;
    std::uint32_t callback_stack = 0U;
    std::uint32_t d1 = 0U;
    std::uint32_t d3 = 0U;
    if (!parse_integer(argv[7], 0xffffU, event) ||
        !parse_integer(argv[8], 0xffffffffU, d1) ||
        !parse_integer(argv[9], 0xffffffffU, d3) ||
        !parse_integer(argv[10], 0xffffffU, callback_stack)) {
        std::cerr << "EVENT must be decimal or 0x-prefixed uint16; D1 and D3 uint32; CALLBACK_STACK uint24\n";
        return 1;
    }
    const std::string paths[5] = {argv[1], argv[2], argv[3], argv[5], argv[6]};
    for (std::size_t output = 3U; output < 5U; ++output) {
        for (std::size_t other = 0U; other < output; ++other) {
            if (same_file(paths[output], paths[other])) {
                std::cerr << "outputs must be distinct from inputs and each other\n";
                return 1;
            }
        }
    }
    std::vector<std::string> stage_inputs;
    stage_inputs.push_back(stage_resource_path(argv[4], "stage_index.ms5d"));
    stage_inputs.push_back(stage_resource_path(argv[4], "stage_null_name.ms5d"));
    for (unsigned int index = 0U; index < 19U; ++index) {
        std::string filename = "stage_group_";
        filename += static_cast<char>('0' + index / 10U);
        filename += static_cast<char>('0' + index % 10U);
        filename += ".ms5d";
        stage_inputs.push_back(stage_resource_path(argv[4], filename));
    }
    for (std::size_t index = 0U; index < stage_inputs.size(); ++index) {
        if (same_file(stage_inputs[index], paths[3]) || same_file(stage_inputs[index], paths[4])) {
            std::cerr << "stage inputs and outputs must be distinct\n";
            return 1;
        }
    }
    std::vector<std::uint8_t> ram;
    if (!read_ram(paths[0], ram)) {
        return 1;
    }
    ms5::FixedDataResource menu;
    ms5::FixedDataResource font;
    std::uint32_t a2 = (static_cast<std::uint32_t>(ram[0x7f12U]) << 24) |
        (static_cast<std::uint32_t>(ram[0x7f13U]) << 16) |
        (static_cast<std::uint32_t>(ram[0x7f14U]) << 8) | ram[0x7f15U];
    std::uint16_t line = static_cast<std::uint16_t>(d3);
    ms5::StageCatalog catalog;
    ms5::FixedDataResource null_name;
    ms5::StageGroupMenuContext context;
    context.catalog = &catalog;
    context.null_name = &null_name;
    context.callback_stack = callback_stack;
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    if (!ms5::load_fixed_data_resource(paths[1], menu, error) ||
        !ms5::load_fixed_data_resource(paths[2], font, error) ||
        !ms5::load_stage_catalog(argv[4], catalog, error) ||
        !ms5::load_fixed_data_resource(stage_resource_path(argv[4], "stage_null_name.ms5d"), null_name, error) ||
        !ms5::dispatch_stage_area_menu(ram, menu, &font, &context, static_cast<std::uint16_t>(event),
                                       line, a2, writes, error, &d1, &d3)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output_ram(paths[3].c_str(), std::ios::binary | std::ios::trunc);
    std::ofstream output_writes(paths[4].c_str(), std::ios::binary | std::ios::trunc);
    if (!output_ram || !output_writes) {
        std::cerr << "cannot open output files\n";
        return 1;
    }
    output_ram.write(reinterpret_cast<const char*>(&ram[0]),
                     static_cast<std::streamsize>(ram.size()));
    // Diagnostic records: byte size, BE32 CPU port address, BE32 value.
    for (std::size_t index = 0; index < writes.size(); ++index) {
        const ms5::VideoPortWrite& write = writes[index];
        const char bytes[9] = {
            static_cast<char>(write.size),
            static_cast<char>((write.address >> 24) & 0xffU),
            static_cast<char>((write.address >> 16) & 0xffU),
            static_cast<char>((write.address >> 8) & 0xffU),
            static_cast<char>(write.address & 0xffU),
            static_cast<char>((write.value >> 24) & 0xffU),
            static_cast<char>((write.value >> 16) & 0xffU),
            static_cast<char>((write.value >> 8) & 0xffU),
            static_cast<char>(write.value & 0xffU)
        };
        output_writes.write(bytes, sizeof(bytes));
    }
    output_ram.close();
    output_writes.close();
    if (!output_ram || !output_writes) {
        std::cerr << "cannot write output files\n";
        return 1;
    }
    std::cout << "{\"a2\":" << a2 << ",\"line\":" << line
              << ",\"d1\":" << d1 << ",\"d3\":" << d3 << "}\n";
    return 0;
}
