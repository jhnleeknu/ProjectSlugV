#include "ms5/interrupt_service.h"

#include <fstream>
#include <iostream>
#include <cstdlib>
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
    // Resolve an existing parent as well so two names for a not-yet-created
    // output (including paths through a directory symlink) cannot collide.
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

bool read_exact(const std::string& path, std::size_t size,
                std::vector<std::uint8_t>& bytes) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        std::cerr << "cannot open input: " << path << '\n';
        return false;
    }
    if (input.tellg() != static_cast<std::streamoff>(size)) {
        std::cerr << "input must contain exactly " << size << " bytes: " << path << '\n';
        return false;
    }
    input.seekg(0, std::ios::beg);
    bytes.resize(size);
    if (!input.read(reinterpret_cast<char*>(&bytes[0]),
                    static_cast<std::streamsize>(size))) {
        std::cerr << "cannot read input: " << path << '\n';
        return false;
    }
    return true;
}

bool write_bytes(const std::string& path, const std::uint8_t* bytes,
                 std::size_t size) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        std::cerr << "cannot open output: " << path << '\n';
        return false;
    }
    output.write(reinterpret_cast<const char*>(bytes),
                 static_cast<std::streamsize>(size));
    output.close();
    if (!output) {
        std::cerr << "cannot write output: " << path << '\n';
        return false;
    }
    return true;
}

bool parse_integer(const std::string& text, std::uint32_t maximum,
                   std::uint32_t& result) {
    unsigned int base = 10;
    std::size_t start = 0;
    if (text.size() >= 2 && text[0] == '0' &&
        (text[1] == 'x' || text[1] == 'X')) {
        base = 16;
        start = 2;
    }
    if (start == text.size()) {
        return false;
    }
    std::uint32_t value = 0;
    for (std::size_t index = start; index < text.size(); ++index) {
        const char c = text[index];
        unsigned int digit;
        if (c >= '0' && c <= '9') {
            digit = static_cast<unsigned int>(c - '0');
        } else if (base == 16 && c >= 'a' && c <= 'f') {
            digit = static_cast<unsigned int>(c - 'a') + 10U;
        } else if (base == 16 && c >= 'A' && c <= 'F') {
            digit = static_cast<unsigned int>(c - 'A') + 10U;
        } else {
            return false;
        }
        if (digit >= base || digit > maximum || value > (maximum - digit) / base) {
            return false;
        }
        value = value * base + digit;
    }
    result = value;
    return true;
}

} // namespace

int main(int argc, char** argv) {
    const std::string mode = argc > 1 ? argv[1] : "";
    const bool begin = mode == "begin";
    const bool task = mode == "task";
    const bool sound = mode == "sound";
    if ((!begin && !task && !sound) || ((begin || task) && argc < 10) ||
        (sound && argc != 17)) {
        std::cerr << "usage: step_interrupt begin|task INPUT_RAM INPUT_BANKS INPUT_REGS OUTPUT_RAM OUTPUT_BANKS OUTPUT_PORTS EXTERNAL STATUS [MS5C ...]\n"
                  << "       step_interrupt sound INPUT_RAM INPUT_BANKS INPUT_REGS OUTPUT_RAM OUTPUT_BANKS OUTPUT_PORTS EXTERNAL STATUS KIND PHASE LOW CURSOR BYTE_COMMAND BYTE_TAIL BYTE_NEXT\n";
        return 2;
    }
    std::uint32_t external = 0U;
    std::uint32_t status = 0U;
    if (!parse_integer(argv[8], 0xffU, external) || !parse_integer(argv[9], 0xffU, status)) {
        std::cerr << "EXTERNAL and STATUS must be decimal or 0x-prefixed uint8\n";
        return 1;
    }
    std::uint32_t fields[7] = {0U, 0U, 0U, 0U, 0U, 0U, 0U};
    if (sound) {
        const std::uint32_t limits[7] = {0xffU, 0xffU, 0xffU, 0xffffU, 0xffU, 0xffffU, 0xffffU};
        for (unsigned int index = 0U; index < 7U; ++index) {
            if (!parse_integer(argv[index + 10U], limits[index], fields[index])) {
                std::cerr << "KIND, PHASE, LOW and BYTE_COMMAND must be decimal or 0x-prefixed uint8; CURSOR, BYTE_TAIL and BYTE_NEXT uint16\n";
                return 1;
            }
        }
    }
    std::vector<std::string> paths;
    for (int index = 2; index < 8; ++index) {
        paths.push_back(argv[index]);
    }
    if (!sound) {
        for (int index = 10; index < argc; ++index) {
            paths.push_back(argv[index]);
        }
    }
    for (std::size_t index = 1U; index < paths.size(); ++index) {
        for (std::size_t other = 0U; other < index; ++other) {
            if (same_file(paths[index], paths[other])) {
                std::cerr << "all inputs, outputs and resources must be distinct files\n";
                return 1;
            }
        }
    }
    std::vector<std::uint8_t> ram;
    std::vector<std::uint8_t> banks;
    std::vector<std::uint8_t> register_bytes;
    if (!read_exact(paths[0], 65536U, ram) || !read_exact(paths[1], 16384U, banks) ||
        !read_exact(paths[2], 64U, register_bytes)) {
        return 1;
    }
    std::vector<std::uint8_t> palette0(banks.begin(), banks.begin() + 8192U);
    std::vector<std::uint8_t> palette1(banks.begin() + 8192U, banks.end());
    ms5::InterruptRegisters registers;
    for (std::size_t index = 0U; index < 16U; ++index) {
        const std::size_t offset = index * 4U;
        const std::uint32_t value =
            (static_cast<std::uint32_t>(register_bytes[offset]) << 24) |
            (static_cast<std::uint32_t>(register_bytes[offset + 1U]) << 16) |
            (static_cast<std::uint32_t>(register_bytes[offset + 2U]) << 8) |
            static_cast<std::uint32_t>(register_bytes[offset + 3U]);
        if (index < 8U) {
            registers.d[index] = value;
        } else {
            registers.a[index - 8U] = value;
        }
    }
    std::vector<ms5::CompositionResource> resources;
    std::string error;
    for (std::size_t index = 6U; index < paths.size(); ++index) {
        ms5::CompositionResource resource;
        if (!ms5::load_composition_resource(paths[index], resource, error)) {
            std::cerr << error << '\n';
            return 1;
        }
        resources.push_back(resource);
    }
    std::uint8_t display_bank = 0U;
    ms5::InterruptServiceResult result;
    std::vector<ms5::VideoPortWrite> ports;
    bool succeeded;
    if (begin) {
        succeeded = ms5::begin_interrupt_service(ram, palette0, palette1, display_bank,
                     resources, registers, static_cast<std::uint8_t>(external),
                     static_cast<std::uint8_t>(status), result, ports, error);
    } else if (task) {
        succeeded = ms5::continue_interrupt_service(ram, registers,
                     static_cast<std::uint8_t>(external), static_cast<std::uint8_t>(status),
                     result, ports, error);
    } else {
        result.phase = ms5::InterruptServiceSoundWait;
        result.sound.kind = static_cast<std::uint8_t>(fields[0]);
        result.sound.phase = static_cast<std::uint8_t>(fields[1]);
        result.sound.low = static_cast<std::uint8_t>(fields[2]);
        result.sound.cursor = static_cast<std::uint16_t>(fields[3]);
        result.sound.byte.waiting = true;
        result.sound.byte.command = static_cast<std::uint8_t>(fields[4]);
        result.sound.byte.tail = static_cast<std::uint16_t>(fields[5]);
        result.sound.byte.next = static_cast<std::uint16_t>(fields[6]);
        succeeded = ms5::resume_interrupt_service_sound(ram, static_cast<std::uint8_t>(status),
                                                        result, ports, error);
    }
    if (!succeeded) {
        std::cerr << error << '\n';
        return 1;
    }
    for (std::size_t index = 0U; index < 8192U; ++index) {
        banks[index] = palette0[index];
        banks[8192U + index] = palette1[index];
    }
    if (!write_bytes(paths[3], &ram[0], ram.size()) ||
        !write_bytes(paths[4], &banks[0], banks.size())) {
        return 1;
    }
    std::ofstream output_writes(paths[5].c_str(), std::ios::binary | std::ios::trunc);
    if (!output_writes) {
        std::cerr << "cannot open port output\n";
        return 1;
    }
    // Diagnostic records: byte size, BE32 CPU port address, BE32 value.
    for (std::size_t index = 0; index < ports.size(); ++index) {
        const ms5::VideoPortWrite& write = ports[index];
        const char bytes[9] = {
            static_cast<char>(write.size),
            static_cast<char>((write.address >> 24) & 0xffU),
            static_cast<char>((write.address >> 16) & 0xffU),
            static_cast<char>((write.address >> 8) & 0xffU),
            static_cast<char>(write.address & 0xffU),
            static_cast<char>((write.value >> 24) & 0xffU),
            static_cast<char>((write.value >> 16) & 0xffU),
            static_cast<char>((write.value >> 8) & 0xffU),
            static_cast<char>(write.value & 0xffU)
        };
        output_writes.write(bytes, sizeof(bytes));
    }
    output_writes.close();
    if (!output_writes) {
        std::cerr << "cannot write port output\n";
        return 1;
    }
    std::cout << "{\"service_phase\":" << result.phase << ",\"display_bank\":";
    if (begin) {
        std::cout << static_cast<unsigned int>(display_bank);
    } else {
        std::cout << "null";
    }
    std::cout << ",\"sound_reads\":" << static_cast<unsigned int>(result.sound_reads)
              << ",\"task_registers\":[";
    for (unsigned int index = 0U; index < 16U; ++index) {
        if (index != 0U) {
            std::cout << ',';
        }
        std::cout << (index < 8U ? result.task_registers.d[index] : result.task_registers.a[index - 8U]);
    }
    std::cout << "],\"task\":{\"next_pc\":" << result.task.next_pc
              << ",\"restored\":" << (result.task.restored ? "true" : "false")
              << ",\"stack_address\":[" << result.task.stack_address[0] << ',' << result.task.stack_address[1]
              << "],\"stack_value\":[" << result.task.stack_value[0] << ',' << result.task.stack_value[1]
              << "]},\"pending\":{\"kind\":" << static_cast<unsigned int>(result.sound.kind)
              << ",\"phase\":" << static_cast<unsigned int>(result.sound.phase)
              << ",\"low\":" << static_cast<unsigned int>(result.sound.low)
              << ",\"cursor\":" << result.sound.cursor
              << ",\"command\":" << static_cast<unsigned int>(result.sound.byte.command)
              << ",\"tail\":" << result.sound.byte.tail
              << ",\"next\":" << result.sound.byte.next << "}}\n";
    return 0;
}
