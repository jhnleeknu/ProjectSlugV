#include "ms5/object_sound_lookup.h"

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

bool save_output(const std::vector<std::string>& paths,
    const std::vector<struct stat>& identities,
    const std::vector<std::uint8_t>& ram, std::string& error) {
    ReservedOutput output;
    bool valid = reserve_output(paths[1],output);
    if (!valid) error = "cannot reserve regular output file";
    for (std::size_t i = 0; valid && i < paths.size(); ++i) {
        if (i == 1) continue;
        struct stat current;
        if (stat(paths[i].c_str(),&current) != 0 || !S_ISREG(current.st_mode)) {
            error = "cannot inspect regular input before output write"; valid = false;
        } else if (same_identity(output.identity,identities[i]) ||
                   same_identity(output.identity,current)) {
            error = "output must be distinct from all input resources"; valid = false;
        }
    }
    if (!valid) { discard_reservation(paths[1],output); return false; }
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
    if (argc < 24) {
        std::cerr << "usage: execute_object_sound_lookup D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 PHASE SAVED_A0 SOUND_PHASE SAVED_LOW WAITING EXTERNAL INPUT_RAM OUTPUT_RAM [FIXED_MS5D ...]\n";
        return 2;
    }
    ms5::ObjectSoundLookupState state;
    for (unsigned int i = 0; i < 15; ++i) {
        std::uint32_t value = 0;
        if (!parse_integer(argv[i+1],0xffffffffU,value)) {
            std::cerr << "invalid unsigned register at argument " << i+1 << '\n'; return 1;
        }
        if (i < 8) state.sound.byte.registers.d[i] = value;
        else if (i < 13) state.sound.byte.registers.a[i-8] = value;
        else if (i == 13) state.a5 = value;
        else state.a6 = value;
    }
    const std::uint32_t maximum[] = {1U,0xffffffffU,2U,255U,1U,255U};
    std::uint32_t values[6];
    for (unsigned int i = 0; i < 6; ++i) {
        if (!parse_integer(argv[16+i],maximum[i],values[i])) {
            std::cerr << "invalid continuation or external value at argument " << 16+i << '\n'; return 1;
        }
    }
    state.phase = values[0]; state.saved_a0 = values[1]; state.sound.phase = values[2];
    state.sound.saved_low = static_cast<std::uint8_t>(values[3]);
    state.sound.byte.waiting = values[4] != 0;
    const std::uint8_t external = static_cast<std::uint8_t>(values[5]);
    std::vector<std::string> paths, canonical;
    std::vector<struct stat> identities;
    for (int i = 22; i < 24; ++i) {
        const std::string path(argv[i]); std::string resolved;
        if (!canonical_path(path,resolved)) { std::cerr << "cannot resolve input/output path\n"; return 1; }
        if (!paths.empty() && (resolved == canonical[0] || same_inode(path,paths[0]))) {
            std::cerr << "input and output files must be distinct\n"; return 1;
        }
        struct stat identity = {};
        if (i == 22 && (stat(path.c_str(),&identity) != 0 || !S_ISREG(identity.st_mode))) {
            std::cerr << "input RAM must be a regular file\n"; return 1;
        }
        paths.push_back(path); canonical.push_back(resolved); identities.push_back(identity);
    }
    std::ifstream input(paths[0].c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) {
        std::cerr << "RAM must contain exactly 65536 bytes\n"; return 1;
    }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]),65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    input.close();
    std::string error;
    std::vector<ms5::FixedDataResource> windows;
    for (int i = 24; i < argc; ++i) {
        const std::string path(argv[i]); std::string resolved; struct stat identity;
        if (!canonical_path(path,resolved)) { std::cerr << "cannot resolve resource path\n"; return 1; }
        if (stat(path.c_str(),&identity) != 0 || !S_ISREG(identity.st_mode)) {
            std::cerr << "fixed resources must be regular files\n"; return 1;
        }
        bool duplicate = false;
        for (std::size_t j = 0; j < paths.size(); ++j) {
            if (resolved == canonical[j] || same_inode(path,paths[j])) {
                if (j >= 2) { duplicate = true; break; }
                std::cerr << "resources must be distinct from input and output\n"; return 1;
            }
        }
        if (duplicate) continue;
        ms5::FixedDataResource window;
        if (!ms5::load_fixed_data_resource(path,window,error)) { std::cerr << error << '\n'; return 1; }
        windows.push_back(window); paths.push_back(path); canonical.push_back(resolved); identities.push_back(identity);
    }
    std::uint8_t reads = 0;
    if (!ms5::execute_object_sound_lookup(ram,windows,state,external,reads,error) ||
        !save_output(paths,identities,ram,error)) { std::cerr << error << '\n'; return 1; }
    std::cout << "{";
    for (unsigned int i = 0; i < 8; ++i)
        std::cout << (i == 0 ? "" : ",") << "\"d" << i << "\":" << state.sound.byte.registers.d[i];
    for (unsigned int i = 0; i < 5; ++i)
        std::cout << ",\"a" << i << "\":" << state.sound.byte.registers.a[i];
    std::cout << ",\"a5\":" << state.a5 << ",\"a6\":" << state.a6
              << ",\"phase\":" << state.phase << ",\"saved_a0\":" << state.saved_a0
              << ",\"sound_phase\":" << state.sound.phase
              << ",\"saved_low\":" << static_cast<unsigned int>(state.sound.saved_low)
              << ",\"waiting\":" << (state.sound.byte.waiting ? "true" : "false")
              << ",\"external_reads\":" << static_cast<unsigned int>(reads) << "}\n";
    return 0;
}
