#include "ms5/stage_block_draw.h"

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

bool save_outputs(const std::vector<std::string>& paths,
    const std::vector<std::uint8_t>& ram, const std::vector<std::uint8_t>& ports,
    std::string& error) {
    ReservedOutput outputs[2];
    bool valid = reserve_output(paths[1],outputs[0]);
    if (valid) valid = reserve_output(paths[2],outputs[1]);
    if (!valid) error = "cannot reserve output files";
    if (valid && same_identity(outputs[0].identity,outputs[1].identity)) {
        error = "output files must be distinct"; valid = false;
    }
    // Recheck the actual reserved output inodes against every input/resource.
    // This also catches filesystem aliases which do not compare as path text.
    for (std::size_t i = 0; valid && i < paths.size(); ++i) {
        if (i == 1 || i == 2) continue;
        struct stat input;
        if (stat(paths[i].c_str(),&input) != 0) {
            error = "cannot inspect input resource before output write"; valid = false;
        } else if (same_identity(input,outputs[0].identity) ||
                   same_identity(input,outputs[1].identity)) {
            error = "outputs must be distinct from all input resources"; valid = false;
        }
    }
    if (!valid) {
        discard_reservation(paths[1],outputs[0]);
        discard_reservation(paths[2],outputs[1]);
        return false;
    }
    // Both descriptors are now distinct and protected inputs are excluded.
    // As before, an I/O failure here does not promise atomic pair replacement.
    bool written = write_output(outputs[0].fd,ram);
    if (written) written = write_output(outputs[1].fd,ports);
    const bool ram_closed = close(outputs[0].fd) == 0;
    const bool ports_closed = close(outputs[1].fd) == 0;
    if (!written || !ram_closed || !ports_closed) {
        error = "cannot write or close output files"; return false;
    }
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
    if (argc < 20) {
        std::cerr << "usage: execute_stage_block_draw ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [FIXED_MS5D ...]\n";
        return 2;
    }
    std::uint32_t entry = 0;
    if (!parse_integer(argv[1],0xffffffffU,entry)) {
        std::cerr << "invalid unsigned entry\n"; return 1;
    }
    ms5::ObjectRestartState state;
    for (unsigned int i = 0; i < 15; ++i) {
        std::uint32_t value = 0;
        if (!parse_integer(argv[i+2],0xffffffffU,value)) {
            std::cerr << "invalid unsigned register at argument " << i+2 << '\n'; return 1;
        }
        if (i < 8) state.d[i] = value;
        else state.a[i-8] = value;
    }
    std::vector<std::string> paths, canonical;
    for (int i = 17; i < 20; ++i) {
        paths.push_back(argv[i]);
        std::string resolved;
        if (!canonical_path(paths.back(),resolved)) {
            std::cerr << "cannot resolve path\n"; return 1;
        }
        for (std::size_t j = 0; j < canonical.size(); ++j) {
            if (canonical[j] == resolved || same_inode(paths.back(),paths[j])) {
                std::cerr << "all input and output files must be distinct\n"; return 1;
            }
        }
        canonical.push_back(resolved);
    }
    struct stat input_stat;
    if (stat(paths[0].c_str(),&input_stat) != 0 || !S_ISREG(input_stat.st_mode)) {
        std::cerr << "input RAM must be a regular file\n"; return 1;
    }
    std::ifstream input(paths[0].c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) {
        std::cerr << "RAM must contain exactly 65536 bytes\n"; return 1;
    }
    input.seekg(0);
    std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) {
        std::cerr << "cannot read RAM\n"; return 1;
    }
    input.close();
    std::vector<ms5::FixedDataResource> windows;
    std::string error;
    for (int i = 20; i < argc; ++i) {
        const std::string path(argv[i]);
        std::string resolved;
        if (!canonical_path(path,resolved)) {
            std::cerr << "cannot resolve resource path\n"; return 1;
        }
        struct stat resource_stat;
        if (stat(path.c_str(),&resource_stat) != 0 || !S_ISREG(resource_stat.st_mode)) {
            std::cerr << "fixed resources must be regular files\n"; return 1;
        }
        bool duplicate = false;
        for (std::size_t j = 0; j < paths.size(); ++j) {
            if (canonical[j] == resolved || same_inode(path,paths[j])) {
                if (j >= 3) { duplicate = true; break; }
                std::cerr << "resources must be distinct from input and outputs\n"; return 1;
            }
        }
        if (duplicate) continue;
        ms5::FixedDataResource window;
        if (!ms5::load_fixed_data_resource(path,window,error)) {
            std::cerr << error << '\n'; return 1;
        }
        paths.push_back(path); canonical.push_back(resolved); windows.push_back(window);
    }
    std::vector<ms5::VideoPortWrite> ports;
    if (!ms5::execute_stage_block_draw(ram,entry,windows,state,ports,error)) {
        std::cerr << error << '\n'; return 1;
    }
    std::vector<std::uint8_t> packed;
    packed.reserve(ports.size()*9U);
    for (std::size_t i = 0; i < ports.size(); ++i) {
        packed.push_back(ports[i].size);
        for (int shift = 24; shift >= 0; shift -= 8)
            packed.push_back(static_cast<std::uint8_t>(ports[i].address >> shift));
        for (int shift = 24; shift >= 0; shift -= 8)
            packed.push_back(static_cast<std::uint8_t>(ports[i].value >> shift));
    }
    if (!save_outputs(paths,ram,packed,error)) {
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
