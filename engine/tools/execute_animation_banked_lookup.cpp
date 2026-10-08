#include "ms5/animation_banked_lookup.h"
#include "ms5/physical_rom_resource.h"

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
    } else if (text.size() > 1U && text[0] == '0') {
        base = 8U; start = 1U;
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


bool read_exact_file(const std::string& path, std::size_t size,
    std::vector<std::uint8_t>& bytes, std::string& error) {
    std::ifstream input(path.c_str(),std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(size)) {
        error = "input file must have exact declared byte size"; return false;
    }
    input.seekg(0); bytes.resize(size);
    if (!input.read(reinterpret_cast<char*>(&bytes[0]),size)) {
        error = "cannot read complete input file"; return false;
    }
    return true;
}

bool append_input(const std::string& path, std::vector<std::string>& paths,
    std::vector<std::string>& canonical, std::vector<struct stat>& identities,
    std::string& error) {
    std::string resolved; struct stat identity;
    if (!canonical_path(path,resolved)) { error = "cannot resolve input path"; return false; }
    if (stat(path.c_str(),&identity) != 0 || !S_ISREG(identity.st_mode)) {
        error = "inputs must be regular files"; return false;
    }
    if (resolved == canonical[1] || same_inode(path,paths[1])) {
        error = "output must be distinct from all input resources"; return false;
    }
    paths.push_back(path); canonical.push_back(resolved); identities.push_back(identity);
    return true;
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 20) {
        std::cerr << "usage: execute_animation_banked_lookup BANK_BASE A6 D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 INPUT_RAM OUTPUT_RAM VECTORS_128_OR_DASH PVC_8192_OR_DASH [MS5D ...]\n";
        return 2;
    }
    ms5::ProgramBusState bus;
    ms5::SceneMapTransferState registers;
    std::uint32_t a6 = 0;
    for (unsigned int i = 1; i <= 15; ++i) {
        std::uint32_t value = 0;
        if (!parse_integer(argv[i],0xffffffffU,value)) {
            std::cerr << "invalid unsigned integer at argument " << i << '\n'; return 1;
        }
        if (i == 1) bus.bank_base = value;
        else if (i == 2) a6 = value;
        else if (i <= 10) registers.d[i-3] = value;
        else registers.a[i-11] = value;
    }
    std::vector<std::string> paths, canonical;
    std::vector<struct stat> identities;
    for (int i = 16; i <= 17; ++i) {
        const std::string path(argv[i]); std::string resolved;
        if (!canonical_path(path,resolved)) { std::cerr << "cannot resolve input/output path\n"; return 1; }
        if (!paths.empty() && (resolved == canonical[0] || same_inode(path,paths[0]))) {
            std::cerr << "input and output files must be distinct\n"; return 1;
        }
        struct stat identity = {};
        if (i == 16 && (stat(path.c_str(),&identity) != 0 || !S_ISREG(identity.st_mode))) {
            std::cerr << "input RAM must be a regular file\n"; return 1;
        }
        paths.push_back(path); canonical.push_back(resolved); identities.push_back(identity);
    }
    std::string error;
    std::vector<std::uint8_t> ram, vectors, pvc;
    if (!read_exact_file(paths[0],65536,ram,error)) { std::cerr << error << '\n'; return 1; }
    for (unsigned int i = 18; i <= 19; ++i) {
        if (std::string(argv[i]) == "-") continue;
        if (!append_input(argv[i],paths,canonical,identities,error)) { std::cerr << error << '\n'; return 1; }
        std::vector<std::uint8_t>& view = i == 18 ? vectors : pvc;
        if (!read_exact_file(argv[i],i == 18 ? 128U : 8192U,view,error)) { std::cerr << error << '\n'; return 1; }
        if (i == 18) bus.vectors = &vectors;
        else bus.pvc = &pvc;
    }
    const std::size_t first_resource = paths.size();
    std::vector<ms5::FixedDataResource> windows;
    std::vector<ms5::PhysicalRomResource> physical_rom;
    for (int i = 20; i < argc; ++i) {
        const std::string path(argv[i]); std::string resolved; struct stat identity;
        if (!canonical_path(path,resolved)) { std::cerr << "cannot resolve resource path\n"; return 1; }
        if (stat(path.c_str(),&identity) != 0 || !S_ISREG(identity.st_mode)) {
            std::cerr << "MS5D resources must be regular files\n"; return 1;
        }
        bool duplicate = false;
        for (std::size_t j = 0; j < paths.size(); ++j) {
            if (resolved == canonical[j] || same_inode(path,paths[j])) {
                if (j >= first_resource) { duplicate = true; break; }
                std::cerr << "resources must be distinct from RAM, output and device inputs\n"; return 1;
            }
        }
        if (duplicate) continue;
        unsigned char header[12];
        std::ifstream input(path.c_str(),std::ios::binary);
        if (!input.read(reinterpret_cast<char*>(header),12)) {
            std::cerr << "MS5D resource header truncated\n"; return 1;
        }
        input.close();
        if (header[0] != 'M' || header[1] != 'S' || header[2] != '5' || header[3] != 'D') {
            std::cerr << "invalid MS5D resource magic\n"; return 1;
        }
        const std::uint32_t kind = static_cast<std::uint32_t>(header[8]) |
            (static_cast<std::uint32_t>(header[9]) << 8) |
            (static_cast<std::uint32_t>(header[10]) << 16) |
            (static_cast<std::uint32_t>(header[11]) << 24);
        ms5::FixedDataResource window;
        bool loaded = false;
        if (kind == 1) loaded = ms5::load_fixed_data_resource(path,window,error);
        else if (kind == 2) loaded = ms5::load_banked_data_resource(path,window,error);
        else if (kind == 3) {
            ms5::PhysicalRomResource physical;
            loaded = ms5::load_physical_rom_resource(path,physical,error);
            if (loaded) physical_rom.push_back(physical);
        }
        else { std::cerr << "unsupported MS5D resource kind\n"; return 1; }
        if (!loaded) { std::cerr << error << '\n'; return 1; }
        if (kind == 1 || kind == 2) windows.push_back(window);
        paths.push_back(path); canonical.push_back(resolved); identities.push_back(identity);
    }
    if (!physical_rom.empty()) bus.physical_rom = &physical_rom;
    if (!ms5::execute_animation_banked_lookup(ram,windows,bus,registers,a6,error) ||
        !save_output(paths,identities,ram,error)) { std::cerr << error << '\n'; return 1; }
    std::cout << "{";
    for (unsigned int i = 0; i < 8; ++i)
        std::cout << (i == 0 ? "" : ",") << "\"d" << i << "\":" << registers.d[i];
    for (unsigned int i = 0; i < 5; ++i)
        std::cout << ",\"a" << i << "\":" << registers.a[i];
    std::cout << "}\n";
    return 0;
}
