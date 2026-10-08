#include "ms5/palette_effect_execution.h"

#include <cstdlib>
#include <cerrno>
#include <fcntl.h>
#include <unistd.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

// Canonicalize an existing path, or its existing parent for a new output.
bool canonical_path(const std::string& path, std::string& canonical) {
    char* resolved = realpath(path.c_str(), 0);
    if (resolved != 0) {
        canonical.assign(resolved);
        std::free(resolved);
        return true;
    }
    const std::size_t slash = path.find_last_of('/');
    const std::string parent = slash == std::string::npos ? "."
        : (slash == 0 ? "/" : path.substr(0, slash));
    const std::string basename = slash == std::string::npos ? path : path.substr(slash + 1);
    if (basename.empty() || basename == "." || basename == "..") {
        return false;
    }
    resolved = realpath(parent.c_str(), 0);
    if (resolved == 0) {
        return false;
    }
    canonical.assign(resolved);
    std::free(resolved);
    canonical += "/" + basename;
    return true;
}

bool same_inode(const std::string& left, const std::string& right) {
    struct stat left_stat;
    struct stat right_stat;
    return stat(left.c_str(), &left_stat) == 0 &&
        stat(right.c_str(), &right_stat) == 0 &&
        left_stat.st_dev == right_stat.st_dev &&
        left_stat.st_ino == right_stat.st_ino;
}

struct ReservedOutput {
    int fd;
    bool created;
    bool identified;
    struct stat identity;
    ReservedOutput() : fd(-1), created(false), identified(false) {}
};

bool same_identity(const struct stat& left, const struct stat& right) {
    return left.st_dev == right.st_dev && left.st_ino == right.st_ino;
}

bool reserve_output(const std::string& path, ReservedOutput& output) {
    output.fd = open(path.c_str(),O_WRONLY | O_NONBLOCK | O_CREAT | O_EXCL,0666);
    if (output.fd >= 0) output.created = true;
    else if (errno == EEXIST) output.fd = open(path.c_str(),O_WRONLY | O_NONBLOCK);
    if (output.fd < 0 || fstat(output.fd,&output.identity) != 0) return false;
    output.identified = true;
    return S_ISREG(output.identity.st_mode);
}

// A reservation failure may remove only a new, still-identical placeholder.
// Existing outputs and paths replaced since reservation must never be removed.
void discard_reservation(const std::string& path, ReservedOutput& output) {
    if (output.fd >= 0) close(output.fd);
    output.fd = -1;
    struct stat current;
    if (output.created && output.identified &&
        lstat(path.c_str(),&current) == 0 && same_identity(current,output.identity))
        unlink(path.c_str());
}

bool write_output(int fd, const std::vector<std::uint8_t>& bytes) {
    if (ftruncate(fd,static_cast<off_t>(bytes.size())) != 0) return false;
    std::size_t written = 0;
    while (written < bytes.size()) {
        const ssize_t count = write(fd,&bytes[written],bytes.size()-written);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return false;
        written += static_cast<std::size_t>(count);
    }
    return true;
}

bool save_output(const std::string& input_path, const std::string& output_path,
    const struct stat& input_identity, const std::vector<std::uint8_t>& ram,
    std::string& error) {
    ReservedOutput output;
    bool valid = reserve_output(output_path,output);
    if (!valid) error = "cannot reserve regular output file";
    if (valid) {
        struct stat current_input;
        if (stat(input_path.c_str(),&current_input) != 0 || !S_ISREG(current_input.st_mode)) {
            error = "cannot inspect regular input before output write"; valid = false;
        } else if (same_identity(output.identity,input_identity) ||
                   same_identity(output.identity,current_input)) {
            error = "input and output files must be distinct"; valid = false;
        }
    }
    if (!valid) { discard_reservation(output_path,output); return false; }
    const bool written = write_output(output.fd,ram);
    const bool closed = close(output.fd) == 0;
    if (!written || !closed) { error = "cannot write or close output file"; return false; }
    return true;
}

bool parse_integer(const std::string& text, std::uint32_t maximum, std::uint32_t& result) {
    unsigned int base = 10U;
    std::size_t start = 0U;
    if (text.size() >= 2U && text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) {
        base = 16U; start = 2U;
    }
    if (start == text.size()) return false;
    unsigned int value = 0U;
    for (std::size_t index = start; index < text.size(); ++index) {
        const char c = text[index];
        unsigned int digit;
        if (c >= '0' && c <= '9') digit = static_cast<unsigned int>(c - '0');
        else if (base == 16U && c >= 'a' && c <= 'f') digit = static_cast<unsigned int>(c - 'a') + 10U;
        else if (base == 16U && c >= 'A' && c <= 'F') digit = static_cast<unsigned int>(c - 'A') + 10U;
        else return false;
        if (digit >= base || digit > maximum || value > (maximum - digit) / base) return false;
        value = value * base + digit;
    }
    result = value;
    return true;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 18) {
        std::cerr << "usage: execute_palette_effect D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 INPUT_RAM OUTPUT_RAM\n";
        return 2;
    }
    ms5::ObjectRestartState state;
    for (unsigned int i = 0; i < 15; ++i) {
        std::uint32_t value = 0;
        if (!parse_integer(argv[i+1],0xffffffffU,value)) {
            std::cerr << "invalid unsigned register at argument " << i+1 << '\n'; return 1;
        }
        if (i < 8) state.d[i] = value;
        else state.a[i-8] = value;
    }
    const std::string input_path(argv[16]), output_path(argv[17]);
    std::string input_canonical, output_canonical;
    if (!canonical_path(input_path,input_canonical) || !canonical_path(output_path,output_canonical)) {
        std::cerr << "cannot resolve input/output path\n"; return 1;
    }
    if (input_canonical == output_canonical || same_inode(input_path,output_path)) {
        std::cerr << "input and output files must be distinct\n"; return 1;
    }
    struct stat input_identity;
    if (stat(input_path.c_str(),&input_identity) != 0 || !S_ISREG(input_identity.st_mode)) {
        std::cerr << "input RAM must be a regular file\n"; return 1;
    }
    std::ifstream input(input_path.c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) {
        std::cerr << "RAM must contain exactly 65536 bytes\n"; return 1;
    }
    input.seekg(0);
    std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) {
        std::cerr << "cannot read RAM\n"; return 1;
    }
    input.close();
    std::string error;
    if (!ms5::execute_palette_effect(ram,state,error)) {
        std::cerr << error << '\n'; return 1;
    }
    if (!save_output(input_path,output_path,input_identity,ram,error)) {
        std::cerr << error << '\n'; return 1;
    }
    std::cout << "{";
    for (unsigned int i = 0; i < 8; ++i)
        std::cout << (i == 0 ? "" : ",") << "\"d" << i << "\":" << state.d[i];
    for (unsigned int i = 0; i < 7; ++i)
        std::cout << ",\"a" << i << "\":" << state.a[i];
    std::cout << "}\n";
    return 0;
}
