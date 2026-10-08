#include "ms5/sound_byte_execution.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {
bool parse_u32(const std::string& text, std::uint32_t maximum, std::uint32_t& result) {
    unsigned int base = 10;
    std::size_t start = 0;
    if (text.size() >= 2 && text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) {
        base = 16; start = 2;
    }
    if (start == text.size()) return false;
    std::uint32_t value = 0;
    for (std::size_t i = start; i < text.size(); ++i) {
        const char c = text[i]; unsigned int digit;
        if (c >= '0' && c <= '9') digit = static_cast<unsigned int>(c-'0');
        else if (base == 16 && c >= 'a' && c <= 'f') digit = static_cast<unsigned int>(c-'a')+10U;
        else if (base == 16 && c >= 'A' && c <= 'F') digit = static_cast<unsigned int>(c-'A')+10U;
        else return false;
        if (digit >= base || digit > maximum || value > (maximum-digit)/base) return false;
        value = value*base+digit;
    }
    result = value; return true;
}

bool canonical_path(const std::string& path, std::string& result) {
    char* resolved = realpath(path.c_str(), NULL);
    if (resolved != NULL) { result.assign(resolved); std::free(resolved); return true; }
    const std::size_t slash = path.find_last_of('/');
    const std::string parent = slash == std::string::npos ? "." : (slash == 0 ? "/" : path.substr(0,slash));
    const std::string name = slash == std::string::npos ? path : path.substr(slash+1);
    if (name.empty() || name == "." || name == "..") return false;
    resolved = realpath(parent.c_str(), NULL);
    if (resolved == NULL) return false;
    result.assign(resolved); std::free(resolved); result += "/"+name; return true;
}

bool same_inode(const std::string& left, const std::string& right) {
    struct stat a, b;
    return stat(left.c_str(),&a) == 0 && stat(right.c_str(),&b) == 0 &&
        a.st_dev == b.st_dev && a.st_ino == b.st_ino;
}
} // namespace

int main(int argc, char** argv) {
    if (argc != 18) {
        std::cerr << "usage: execute_sound_byte D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 WAITING INPUT_RAM OUTPUT_RAM\n";
        return 2;
    }
    ms5::SoundByteExecutionState state;
    std::uint32_t a6 = 0, waiting = 0;
    for (unsigned int i = 0; i < 13; ++i) {
        std::uint32_t value = 0;
        if (!parse_u32(argv[i+1],0xffffffffU,value)) { std::cerr << "invalid unsigned register\n"; return 1; }
        if (i < 8) state.registers.d[i] = value;
        else state.registers.a[i-8] = value;
    }
    if (!parse_u32(argv[14],0xffffffffU,a6) || !parse_u32(argv[15],1,waiting)) {
        std::cerr << "invalid A6 or waiting\n"; return 1;
    }
    state.waiting = waiting != 0;
    const std::string input_path(argv[16]), output_path(argv[17]);
    std::string input_canonical, output_canonical;
    if (!canonical_path(input_path,input_canonical) || !canonical_path(output_path,output_canonical)) {
        std::cerr << "cannot resolve input/output path\n"; return 1;
    }
    if (input_canonical == output_canonical || same_inode(input_path,output_path)) {
        std::cerr << "input and output files must be distinct\n"; return 1;
    }
    std::ifstream input(input_path.c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) {
        std::cerr << "RAM must contain exactly65536 bytes\n"; return 1;
    }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    input.close();
    std::string error;
    if (!ms5::execute_sound_byte(ram,state,error)) { std::cerr << error << '\n'; return 1; }
    std::ofstream output(output_path.c_str(),std::ios::binary | std::ios::trunc);
    if (!output || !output.write(reinterpret_cast<const char*>(&ram[0]),65536)) { std::cerr << "cannot write output\n"; return 1; }
    output.close();
    if (!output) { std::cerr << "cannot close output\n"; return 1; }
    std::cout << "{";
    for (unsigned int i = 0; i < 8; ++i) std::cout << (i == 0 ? "" : ",") << "\"d" << i << "\":" << state.registers.d[i];
    for (unsigned int i = 0; i < 5; ++i) std::cout << ",\"a" << i << "\":" << state.registers.a[i];
    std::cout << ",\"a6\":" << a6 << ",\"waiting\":" << (state.waiting ? "true" : "false")
              << "}\n";
    return 0;
}
