#include "ms5/menu_input.h"

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

} // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: select_menu_input INPUT_RAM OUTPUT_RAM OUTPUT_ACTION\n";
        return 2;
    }
    const std::string input_path(argv[1]);
    const std::string output_ram_path(argv[2]);
    const std::string output_action_path(argv[3]);
    if (same_file(input_path, output_ram_path) ||
        same_file(input_path, output_action_path) ||
        same_file(output_ram_path, output_action_path)) {
        std::cerr << "outputs must be distinct from input and each other\n";
        return 1;
    }
    std::vector<std::uint8_t> ram;
    if (!read_ram(input_path, ram)) {
        return 1;
    }
    ms5::MenuInput action;
    std::string error;
    if (!ms5::select_menu_input(ram, action, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::ofstream ram_output(output_ram_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!ram_output) {
        std::cerr << "cannot open RAM output\n";
        return 1;
    }
    ram_output.write(reinterpret_cast<const char*>(&ram[0]), 65536);
    ram_output.close();
    if (!ram_output) {
        std::cerr << "cannot write RAM output\n";
        return 1;
    }
    const char bytes[3] = {
        static_cast<char>(action.kind),
        static_cast<char>(action.event),
        static_cast<char>(action.sources)
    };
    std::ofstream action_output(output_action_path.c_str(), std::ios::binary | std::ios::trunc);
    if (!action_output) {
        std::cerr << "cannot open action output\n";
        return 1;
    }
    action_output.write(bytes, sizeof(bytes));
    action_output.close();
    if (!action_output) {
        std::cerr << "cannot write action output\n";
        return 1;
    }
    return 0;
}
