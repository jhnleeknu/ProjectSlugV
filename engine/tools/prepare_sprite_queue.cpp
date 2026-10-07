#include "ms5/sprite_prepare_queue.h"

#include <cstdlib>
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

void append_word(std::vector<std::uint8_t>& bytes, std::uint16_t value) {
    bytes.push_back(static_cast<std::uint8_t>(value >> 8));
    bytes.push_back(static_cast<std::uint8_t>(value));
}

bool save_bytes(const std::string& path, const std::vector<std::uint8_t>& bytes) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        return false;
    }
    if (!bytes.empty()) {
        output.write(reinterpret_cast<const char*>(&bytes[0]),
                     static_cast<std::streamsize>(bytes.size()));
    }
    output.close();
    return static_cast<bool>(output);
}

bool parse_cursor(const std::string& text, std::uint16_t& result) {
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
        if (digit >= base || value > (65535U - digit) / base) return false;
        value = value * base + digit;
    }
    result = static_cast<std::uint16_t>(value);
    return true;
}

} // namespace

int main(int argc, char** argv) {
    bool begin = false, resume = false;
    ms5::SpritePreparePending pending;
    if (argc > 1 && std::string(argv[1]) == "--begin") {
        begin = true; --argc; ++argv;
    } else if (argc > 1 && std::string(argv[1]) == "--resume") {
        if (argc < 3 || !parse_cursor(argv[2], pending.cursor)) {
            std::cerr << "--resume requires decimal or 0x-prefixed uint16 CURSOR\n";
            return 1;
        }
        resume = true; pending.waiting = true;
        argc -= 2; argv += 2;
    }
    if (argc < (begin || resume ? 4 : 5)) {
        std::cerr << "usage: prepare_sprite_queue [--begin | --resume CURSOR] INPUT_RAM OUTPUT_RAM OUTPUT_WRITES [RESOURCE.ms5c ...] (legacy requires at least one resource)\n"
                  << "output writes: raw BE16 address/value pairs\n";
        return 2;
    }
    std::vector<std::string> paths;
    std::vector<std::string> canonical;
    for (int index = 1; index < argc; ++index) {
        paths.push_back(argv[index]);
        std::string resolved;
        if (!canonical_path(paths.back(), resolved)) {
            std::cerr << "cannot resolve file path: " << paths.back() << '\n';
            return 1;
        }
        for (std::size_t other = 0; other < canonical.size(); ++other) {
            if (resolved == canonical[other] || same_inode(paths.back(), paths[other])) {
                std::cerr << "RAM input, outputs and resources must all be distinct files\n";
                return 1;
            }
        }
        canonical.push_back(resolved);
    }
    std::ifstream input(paths[0].c_str(), std::ios::binary);
    if (!input) {
        std::cerr << "cannot open RAM input\n";
        return 1;
    }
    std::vector<std::uint8_t> ram(65536);
    input.read(reinterpret_cast<char*>(&ram[0]), 65536);
    if (input.gcount() != 65536 || input.bad()) {
        std::cerr << "RAM input must contain exactly 65536 bytes\n";
        return 1;
    }
    char extra;
    if (input.get(extra) || input.bad() || !input.eof()) {
        std::cerr << "RAM input must contain exactly 65536 bytes\n";
        return 1;
    }
    input.close();
    std::vector<ms5::CompositionResource> resources;
    std::string error;
    for (std::size_t index = 3; index < paths.size(); ++index) {
        ms5::CompositionResource resource;
        if (!ms5::load_composition_resource(paths[index], resource, error)) {
            std::cerr << error << '\n';
            return 1;
        }
        resources.push_back(resource);
    }
    std::vector<ms5::SpriteWrite> writes;
    bool succeeded;
    if (begin) succeeded = ms5::begin_sprite_queue(ram, pending, error);
    else if (resume) succeeded = ms5::resume_sprite_queue(ram, resources, pending, writes, error);
    else succeeded = ms5::prepare_sprite_queue(ram, resources, writes, error);
    if (!succeeded) {
        std::cerr << error << '\n';
        return 1;
    }
    std::vector<std::uint8_t> output_bytes;
    for (std::size_t index = 0; index < writes.size(); ++index) {
        append_word(output_bytes, writes[index].address);
        append_word(output_bytes, writes[index].value);
    }
    // Validate all input, resource and queue data before opening either output.
    if (!save_bytes(paths[1], ram) || !save_bytes(paths[2], output_bytes)) {
        std::cerr << "cannot write output files\n";
        return 1;
    }
    if (begin || resume) {
        std::cout << "{\"waiting\":" << (pending.waiting ? "true" : "false")
                  << ",\"cursor\":" << pending.cursor << "}\n";
    }
    return 0;
}
