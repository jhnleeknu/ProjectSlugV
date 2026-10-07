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
    bool begin = false, resume = false, registers_mode = false, ports_mode = false;
    std::uint32_t d1 = 0U, d3 = 0U;
    std::string ports_path;
    ms5::SpritePreparePending pending;
    while (argc > 1) {
        const std::string option(argv[1]);
        if (option == "--begin" || option == "--resume") {
            if (begin || resume) {
                std::cerr << "begin and resume modes must be unique and exclusive\n";
                return 1;
            }
            if (option == "--begin") { begin = true; --argc; ++argv; }
            else {
                std::uint32_t cursor = 0U;
                if (argc < 3 || !parse_integer(argv[2], 0xffffU, cursor)) {
                    std::cerr << "--resume requires decimal or 0x-prefixed uint16 CURSOR\n";
                    return 1;
                }
                resume = true; pending.waiting = true;
                pending.cursor = static_cast<std::uint16_t>(cursor);
                argc -= 2; argv += 2;
            }
        } else if (option == "--registers") {
            if (registers_mode || argc < 4 || !parse_integer(argv[2], 0xffffffffU, d1) ||
                !parse_integer(argv[3], 0xffffffffU, d3)) {
                std::cerr << "--registers requires unique decimal or 0x-prefixed uint32 D1 and D3\n";
                return 1;
            }
            registers_mode = true; argc -= 3; argv += 3;
        } else if (option == "--ports") {
            if (ports_mode || argc < 3) {
                std::cerr << "--ports requires one OUTPUT_PORTS path\n";
                return 1;
            }
            ports_mode = true; ports_path = argv[2]; argc -= 2; argv += 2;
        } else break;
    }
    if (argc < (begin || resume ? 4 : 5)) {
        std::cerr << "usage: prepare_sprite_queue [--begin | --resume CURSOR] [--registers D1 D3] [--ports OUTPUT_PORTS] INPUT_RAM OUTPUT_RAM OUTPUT_WRITES [RESOURCE.ms5c ...] (legacy requires at least one resource)\n"
                  << "output writes: raw BE16 address/value pairs\n";
        return 2;
    }
    std::vector<std::string> paths;
    std::vector<std::string> canonical;
    for (int index = 1; index < argc; ++index) paths.push_back(argv[index]);
    const std::size_t resource_end = paths.size();
    if (ports_mode) paths.push_back(ports_path);
    for (std::size_t index = 0; index < paths.size(); ++index) {
        std::string resolved;
        if (!canonical_path(paths[index], resolved)) {
            std::cerr << "cannot resolve file path: " << paths[index] << '\n';
            return 1;
        }
        for (std::size_t other = 0; other < canonical.size(); ++other) {
            if (resolved == canonical[other] || same_inode(paths[index], paths[other])) {
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
    for (std::size_t index = 3; index < resource_end; ++index) {
        ms5::CompositionResource resource;
        if (!ms5::load_composition_resource(paths[index], resource, error)) {
            std::cerr << error << '\n';
            return 1;
        }
        resources.push_back(resource);
    }
    std::vector<ms5::SpriteWrite> writes;
    std::vector<ms5::VideoPortWrite> ports;
    bool succeeded;
    if (begin) succeeded = ms5::begin_sprite_queue(ram, pending, error, registers_mode ? &d1 : NULL, registers_mode ? &d3 : NULL);
    else if (resume) succeeded = ms5::resume_sprite_queue(ram, resources, pending, writes, error,
        registers_mode ? &d1 : NULL, registers_mode ? &d3 : NULL, ports_mode ? &ports : NULL);
    else succeeded = ms5::prepare_sprite_queue(ram, resources, writes, error,
        registers_mode ? &d1 : NULL, registers_mode ? &d3 : NULL, ports_mode ? &ports : NULL);
    if (!succeeded) {
        std::cerr << error << '\n';
        return 1;
    }
    std::vector<std::uint8_t> output_bytes;
    for (std::size_t index = 0; index < writes.size(); ++index) {
        append_word(output_bytes, writes[index].address);
        append_word(output_bytes, writes[index].value);
    }
    std::vector<std::uint8_t> port_bytes;
    for (std::size_t index = 0; index < ports.size(); ++index) {
        const ms5::VideoPortWrite& port = ports[index];
        port_bytes.push_back(port.size);
        for (unsigned int shift = 24U; ; shift -= 8U) {
            port_bytes.push_back(static_cast<std::uint8_t>(port.address >> shift));
            if (shift == 0U) break;
        }
        for (unsigned int shift = 24U; ; shift -= 8U) {
            port_bytes.push_back(static_cast<std::uint8_t>(port.value >> shift));
            if (shift == 0U) break;
        }
    }
    // Validate all input, resource and queue data before opening either output.
    if (!save_bytes(paths[1], ram) || !save_bytes(paths[2], output_bytes) ||
        (ports_mode && !save_bytes(ports_path, port_bytes))) {
        std::cerr << "cannot write output files\n";
        return 1;
    }
    if (begin || resume || registers_mode || ports_mode) {
        std::cout << "{";
        bool separator = false;
        if (begin || resume) {
            std::cout << "\"waiting\":" << (pending.waiting ? "true" : "false")
                      << ",\"cursor\":" << pending.cursor;
            separator = true;
        }
        if (registers_mode) {
            if (separator) std::cout << ",";
            std::cout << "\"d1\":" << d1 << ",\"d3\":" << d3;
            separator = true;
        }
        if (ports_mode) {
            if (separator) std::cout << ",";
            std::cout << "\"ports\":" << ports.size();
        }
        std::cout << "}\n";
    }
    return 0;
}
