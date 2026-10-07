#include "ms5/main_frame.h"
#include "ms5/palette_resource.h"

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
    bool have_state = false, have_sound = false, have_sprite = false;
    ms5::MainFrameState state;
    while (argc > 1) {
        const std::string option(argv[1]);
        if (option == "--state") {
            if (have_state || argc < 5 || !parse_integer(argv[2], 0xffffffffU, state.next_pc) ||
                !parse_integer(argv[3], 0xffffffffU, state.d1) || !parse_integer(argv[4], 0xffffffffU, state.d3)) {
                std::cerr << "--state requires unique uint32 PC D1 D3\n"; return 1;
            }
            have_state = true; argc -= 4; argv += 4;
        } else if (option == "--sound") {
            std::uint32_t values[6] = {0, 0, 0, 0, 0, 0};
            const std::uint32_t maxima[6] = {255, 255, 65535, 255, 65535, 65535};
            if (have_sound || argc < 8) { std::cerr << "--sound requires PHASE LOW CURSOR COMMAND TAIL NEXT\n"; return 1; }
            for (unsigned int index = 0; index < 6; ++index) {
                if (!parse_integer(argv[index + 2], maxima[index], values[index])) {
                    std::cerr << "invalid unsigned sound continuation field\n"; return 1;
                }
            }
            state.sound.kind = 2; state.sound.phase = static_cast<std::uint8_t>(values[0]);
            state.sound.low = static_cast<std::uint8_t>(values[1]); state.sound.cursor = static_cast<std::uint16_t>(values[2]);
            state.sound.byte.waiting = true; state.sound.byte.command = static_cast<std::uint8_t>(values[3]);
            state.sound.byte.tail = static_cast<std::uint16_t>(values[4]); state.sound.byte.next = static_cast<std::uint16_t>(values[5]);
            have_sound = true; argc -= 7; argv += 7;
        } else if (option == "--sprite") {
            std::uint32_t cursor = 0;
            if (have_sprite || argc < 3 || !parse_integer(argv[2], 65535, cursor)) {
                std::cerr << "--sprite requires unique uint16 CURSOR\n"; return 1;
            }
            state.sprite.waiting = true; state.sprite.cursor = static_cast<std::uint16_t>(cursor);
            have_sprite = true; argc -= 2; argv += 2;
        } else break;
    }
    if (!have_state || argc < 6) {
        std::cerr << "usage: prepare_main_frame --state PC D1 D3 [--sound PHASE LOW CURSOR COMMAND TAIL NEXT] [--sprite CURSOR] VIDEO INPUT_RAM OUTPUT_RAM OUTPUT_PORTS PALETTES.ms5p [MS5C...]\n";
        return 2;
    }
    std::uint32_t video = 0;
    if (!parse_integer(argv[1], 65535, video)) { std::cerr << "VIDEO must be uint16\n"; return 1; }
    std::vector<std::string> paths, canonical;
    for (int index = 2; index < argc; ++index) {
        paths.push_back(argv[index]);
        std::string resolved;
        if (!canonical_path(paths.back(), resolved)) { std::cerr << "cannot resolve path\n"; return 1; }
        for (std::size_t other = 0; other < canonical.size(); ++other) {
            if (canonical[other] == resolved || same_inode(paths.back(), paths[other])) {
                std::cerr << "all inputs and outputs must be distinct files\n"; return 1;
            }
        }
        canonical.push_back(resolved);
    }
    std::ifstream input(paths[0].c_str(), std::ios::binary | std::ios::ate);
    if (!input || input.tellg() != static_cast<std::streamoff>(65536)) {
        std::cerr << "RAM input must contain exactly 65536 bytes\n"; return 1;
    }
    input.seekg(0); std::vector<std::uint8_t> ram(65536);
    if (!input.read(reinterpret_cast<char*>(&ram[0]), 65536)) { std::cerr << "cannot read RAM\n"; return 1; }
    std::string error;
    std::vector<ms5::PaletteRecord> palettes;
    if (!ms5::load_palette_resource(paths[3], palettes, error)) { std::cerr << error << '\n'; return 1; }
    std::vector<ms5::CompositionResource> resources;
    for (std::size_t index = 4; index < paths.size(); ++index) {
        ms5::CompositionResource resource;
        if (!ms5::load_composition_resource(paths[index], resource, error)) { std::cerr << error << '\n'; return 1; }
        resources.push_back(resource);
    }
    std::vector<ms5::VideoPortWrite> ports;
    if (!ms5::prepare_main_frame(ram, resources, palettes, static_cast<std::uint16_t>(video), state, ports, error)) {
        std::cerr << error << '\n'; return 1;
    }
    std::vector<std::uint8_t> bytes;
    for (std::size_t index = 0; index < ports.size(); ++index) {
        bytes.push_back(ports[index].size);
        for (unsigned int byte = 0; byte < 4; ++byte) bytes.push_back(static_cast<std::uint8_t>(ports[index].address >> (24 - byte * 8)));
        for (unsigned int byte = 0; byte < 4; ++byte) bytes.push_back(static_cast<std::uint8_t>(ports[index].value >> (24 - byte * 8)));
    }
    if (!save_bytes(paths[1], ram) || !save_bytes(paths[2], bytes)) { std::cerr << "cannot write outputs\n"; return 1; }
    const ms5::SoundWordPending& sound = state.sound;
    std::cout << "{\"next_pc\":" << state.next_pc << ",\"d1\":" << state.d1 << ",\"d3\":" << state.d3
              << ",\"writes\":" << ports.size() << ",\"sound\":{\"kind\":" << static_cast<unsigned int>(sound.kind)
              << ",\"phase\":" << static_cast<unsigned int>(sound.phase) << ",\"low\":" << static_cast<unsigned int>(sound.low)
              << ",\"cursor\":" << sound.cursor << ",\"waiting\":" << (sound.byte.waiting ? "true" : "false")
              << ",\"command\":" << static_cast<unsigned int>(sound.byte.command) << ",\"tail\":" << sound.byte.tail
              << ",\"next\":" << sound.byte.next << "},\"sprite\":{\"waiting\":" << (state.sprite.waiting ? "true" : "false")
              << ",\"cursor\":" << state.sprite.cursor << "}}\n";
    return 0;
}
