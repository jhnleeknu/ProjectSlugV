#include "ms5/menu_redraw.h"
#include "ms5/stage_group_menu.h"

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
    if (argc != 7 && argc != 8 && argc != 10) {
        std::cerr << "usage: redraw_menu_stack INPUT_RAM MENU_MS5D OUTPUT_RAM OUTPUT_PORTS LAST_SLOT LINE [FONT_MS5D [STAGES_DIRECTORY CALLBACK_STACK]]\n";
        return 2;
    }
    std::uint32_t last_slot = 0U;
    std::uint32_t line = 0U;
    std::uint32_t callback_stack = 0U;
    if (!parse_integer(argv[5], 0xffffffU, last_slot) ||
        !parse_integer(argv[6], 0xffffU, line)) {
        std::cerr << "LAST_SLOT must be decimal or 0x-prefixed uint24; LINE must be decimal or 0x-prefixed uint16\n";
        return 1;
    }
    if (argc == 10 && !parse_integer(argv[9], 0xffffffU, callback_stack)) {
        std::cerr << "CALLBACK_STACK must be a uint24 integer\n";
        return 1;
    }
    const std::string ram_path(argv[1]);
    const std::string resource_path(argv[2]);
    const std::string output_ram_path(argv[3]);
    const std::string output_writes_path(argv[4]);
    if (same_file(ram_path, output_ram_path) ||
        same_file(resource_path, output_ram_path) ||
        same_file(ram_path, output_writes_path) ||
        same_file(resource_path, output_writes_path) ||
        same_file(output_ram_path, output_writes_path)) {
        std::cerr << "outputs must be distinct from both inputs and each other\n";
        return 1;
    }
    if (argc == 10) {
        std::vector<std::string> stage_inputs;
        stage_inputs.push_back(stage_resource_path(argv[8], "stage_index.ms5d"));
        stage_inputs.push_back(stage_resource_path(argv[8], "stage_null_name.ms5d"));
        for (unsigned int index = 0U; index < 19U; ++index) {
            std::string filename = "stage_group_";
            filename += static_cast<char>('0' + index / 10U);
            filename += static_cast<char>('0' + index % 10U);
            filename += ".ms5d";
            stage_inputs.push_back(stage_resource_path(argv[8], filename));
        }
        for (std::size_t index = 0U; index < stage_inputs.size(); ++index) {
            if (same_file(stage_inputs[index], output_ram_path) ||
                same_file(stage_inputs[index], output_writes_path)) {
                std::cerr << "stage inputs and outputs must be distinct\n";
                return 1;
            }
        }
    }
    std::vector<std::uint8_t> ram;
    ms5::FixedDataResource resource;
    std::string error;
    if (!read_ram(ram_path, ram)) {
        return 1;
    }
    ms5::FixedDataResource font;
    const ms5::FixedDataResource* font_pointer = NULL;
    if (argc == 8 || argc == 10) {
        if (same_file(argv[7], output_ram_path) || same_file(argv[7], output_writes_path)) {
            std::cerr << "font input and outputs must be distinct\n";
            return 1;
        }
        if (!ms5::load_fixed_data_resource(argv[7], font, error)) {
            std::cerr << error << '\n'; return 1;
        }
        font_pointer = &font;
    }
    ms5::StageCatalog catalog;
    ms5::FixedDataResource null_name;
    ms5::StageGroupMenuContext context;
    const ms5::StageGroupMenuContext* context_pointer = NULL;
    if (argc == 10) {
        if (!ms5::load_stage_catalog(argv[8], catalog, error) ||
            !ms5::load_fixed_data_resource(stage_resource_path(argv[8], "stage_null_name.ms5d"),
                                           null_name, error)) {
            std::cerr << error << '\n';
            return 1;
        }
        context.catalog = &catalog;
        context.null_name = &null_name;
        // Caller supplies original A7 at event-5 callback entry.
        context.callback_stack = callback_stack;
        context_pointer = &context;
    }
    std::vector<ms5::VideoPortWrite> writes;
    std::uint16_t final_line = static_cast<std::uint16_t>(line);
    if (!ms5::load_fixed_data_resource(resource_path, resource, error) ||
        !ms5::redraw_menu_stack(ram, resource, last_slot,
                                static_cast<std::uint16_t>(line), writes, error,
                                font_pointer, context_pointer, &final_line)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream output_ram(output_ram_path.c_str(), std::ios::binary | std::ios::trunc);
    std::ofstream output_writes(output_writes_path.c_str(), std::ios::binary | std::ios::trunc);
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
    std::cout << "{\"line\":" << final_line << "}\n";
    return 0;
}
