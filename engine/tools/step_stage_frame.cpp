#include "ms5/stage_frame.h"

#include <cstdlib>
#include <cerrno>
#include <fcntl.h>
#include <unistd.h>
#include <algorithm>
#include <dirent.h>
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
    output.fd = open(path.c_str(),O_WRONLY | O_CREAT | O_EXCL,0666);
    if (output.fd >= 0) output.created = true;
    else if (errno == EEXIST) output.fd = open(path.c_str(),O_WRONLY);
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

bool load_windows(const std::string& directory, std::vector<std::string>& paths,
    std::vector<std::string>& canonical, std::vector<ms5::FixedDataResource>& windows, std::string& error) {
    std::vector<std::string> files, folders, seen;
    struct stat item;
    if (stat(directory.c_str(),&item) == 0 && S_ISREG(item.st_mode)) files.push_back(directory);
    else folders.push_back(directory);
    for (std::size_t n = 0; n < folders.size(); ++n) {
        std::string resolved;
        if (!canonical_path(folders[n],resolved)) { error = "cannot resolve resource directory"; return false; }
        if (std::find(seen.begin(),seen.end(),resolved) != seen.end()) continue;
        seen.push_back(resolved);
        DIR* folder = opendir(folders[n].c_str());
        if (folder == NULL) { error = "cannot open resource file or directory"; return false; }
        struct dirent* entry;
        while ((entry = readdir(folder)) != NULL) {
            const std::string name = entry->d_name;
            if (name == "." || name == "..") continue;
            const std::string path = folders[n]+"/"+name;
            if (stat(path.c_str(),&item) != 0) continue;
            if (S_ISDIR(item.st_mode)) folders.push_back(path);
            else if (S_ISREG(item.st_mode) && name.size() >= 5 && name.substr(name.size()-5) == ".ms5d") files.push_back(path);
        }
        closedir(folder);
    }
    std::sort(files.begin(),files.end());
    for (std::size_t i = 0; i < files.size(); ++i) {
        bool duplicate = false; std::string resolved;
        if (!canonical_path(files[i],resolved)) { error = "cannot resolve resource"; return false; }
        for (std::size_t j = 0; j < paths.size(); ++j) {
            if (canonical[j] == resolved || same_inode(files[i],paths[j])) {
                if (j >= 3) { duplicate = true; break; }
                error = "all input and output files must be distinct"; return false;
            }
        }
        if (duplicate) continue;
        std::ifstream header(files[i].c_str(),std::ios::binary); unsigned char kind[4] = {0}; header.seekg(8);
        if (!header.read(reinterpret_cast<char*>(kind),4)) { error = "resource header truncated"; return false; }
        const bool banked = kind[0] == 2 && kind[1] == 0 && kind[2] == 0 && kind[3] == 0;
        ms5::FixedDataResource resource;
        if (!(banked ? ms5::load_banked_data_resource(files[i],resource,error) : ms5::load_fixed_data_resource(files[i],resource,error))) return false;
        paths.push_back(files[i]); canonical.push_back(resolved); windows.push_back(resource);
    }
    return true;
}
} // namespace
int main(int argc, char** argv) {
    if (argc < 34) {
        std::cerr << "usage: step_stage_frame D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 BANK STAGE BUFFER_PHASE SAVED_A6 SAVED_SLOT_A4 SAVED_SLOT_D7 SAVED_D0 SAVED_D1 SAVED_D7 SAVED_A0 CUE_STATUS SOUND_KIND SOUND_PHASE SOUND_SAVED EXTERNAL INPUT_RAM OUTPUT_RAM OUTPUT_PORTS TABLE_MS5D [WINDOW_MS5D_OR_DIRECTORY ...]\n";
        return 2;
    }
    std::uint32_t values[29] = {0};
    for (unsigned int i = 0; i < 29; ++i) {
        std::uint32_t maximum = 0xffffffffU;
        if (i == 14 || i == 15 || i == 24 || i == 26) maximum = 3;
        else if (i == 16 || i == 25) maximum = 2;
        else if (i == 27) maximum = 65535;
        else if (i == 28) maximum = 255;
        if (!parse_integer(argv[i+1],maximum,values[i])) {
            std::cerr << "invalid unsigned number at argument " << i+1 << '\n';
            return 1;
        }
    }
    ms5::StageFrameState state;
    for (unsigned int i = 0; i < 8; ++i) state.buffer.registers.d[i] = values[i];
    for (unsigned int i = 0; i < 5; ++i) state.buffer.registers.a[i] = values[i+8];
    state.buffer.a6 = values[13];
    state.buffer.bank = values[14];
    state.stage = values[15];
    state.buffer.phase = values[16];
    state.buffer.saved_a6 = values[17];
    state.buffer.saved_slot_a4 = values[18];
    state.buffer.saved_slot_d7 = values[19];
    state.buffer.saved_d0 = values[20];
    state.buffer.saved_d1 = values[21];
    state.buffer.saved_d7 = values[22];
    state.buffer.saved_a0 = values[23];
    state.cue_status = static_cast<ms5::SpriteSubmitStatus>(values[24]);
    state.sound_kind = values[25];
    state.sound_phase = values[26];
    state.sound_saved = static_cast<std::uint16_t>(values[27]);

    std::vector<std::string> paths, canonical;
    for (int i = 30; i < 34; ++i) {
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
    ms5::FixedDataResource tables;
    std::vector<ms5::FixedDataResource> windows;
    std::string error;
    // File-format validation applies to supplied resources on every invocation.
    // The core conditionally checks scene/image requirements when reached.
    if (!ms5::load_fixed_data_resource(paths[3],tables,error)) {
        std::cerr << error << '\n'; return 1;
    }
    windows.push_back(tables);
    for (int i = 34; i < argc; ++i) {
        if (!load_windows(argv[i],paths,canonical,windows,error)) {
            std::cerr << error << '\n'; return 1;
        }
    }
    std::vector<ms5::VideoPortWrite> ports;
    std::uint8_t external_reads = 0;
    if (!ms5::step_stage_frame(ram,tables,windows,state,
            static_cast<std::uint8_t>(values[28]),external_reads,ports,error)) {
        std::cerr << error << '\n'; return 1;
    }
    std::vector<std::uint8_t> packed;
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
        std::cout << (i == 0 ? "" : ",") << "\"d" << i << "\":" << state.buffer.registers.d[i];
    for (unsigned int i = 0; i < 5; ++i)
        std::cout << ",\"a" << i << "\":" << state.buffer.registers.a[i];
    std::cout << ",\"a6\":" << state.buffer.a6
              << ",\"bank\":" << state.buffer.bank
              << ",\"stage\":" << state.stage
              << ",\"buffer_phase\":" << state.buffer.phase
              << ",\"saved_a6\":" << state.buffer.saved_a6
              << ",\"saved_slot_a4\":" << state.buffer.saved_slot_a4
              << ",\"saved_slot_d7\":" << state.buffer.saved_slot_d7
              << ",\"saved_d0\":" << state.buffer.saved_d0
              << ",\"saved_d1\":" << state.buffer.saved_d1
              << ",\"saved_d7\":" << state.buffer.saved_d7
              << ",\"saved_a0\":" << state.buffer.saved_a0
              << ",\"cue_status\":" << static_cast<unsigned int>(state.cue_status)
              << ",\"sound_kind\":" << state.sound_kind
              << ",\"sound_phase\":" << state.sound_phase
              << ",\"sound_saved\":" << state.sound_saved
              << ",\"external_reads\":" << static_cast<unsigned int>(external_reads)
              << "}\n";
    return 0;
}
