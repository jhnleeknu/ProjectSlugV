#include "ms5/interrupt_task.h"

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

} // namespace

int main(int argc, char** argv) {
    if (argc != 6) {
        std::cerr << "usage: restore_interrupt_task INPUT_RAM INPUT_REGS OUTPUT_RAM OUTPUT_REGS OUTPUT_PORTS\n";
        return 2;
    }
    const std::string paths[5] = {argv[1], argv[2], argv[3], argv[4], argv[5]};
    for (std::size_t index = 1U; index < 5U; ++index) {
        for (std::size_t other = 0U; other < index; ++other) {
            if (same_file(paths[index], paths[other])) {
                std::cerr << "all input and output paths must be distinct\n";
                return 1;
            }
        }
    }
    std::vector<std::uint8_t> ram;
    std::vector<std::uint8_t> register_bytes;
    if (!read_exact(paths[0], 65536U, ram) || !read_exact(paths[1], 64U, register_bytes)) {
        return 1;
    }
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
    ms5::InterruptTaskResult result;
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    if (!ms5::restore_interrupt_task(ram, registers, result, writes, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    for (std::size_t index = 0U; index < 16U; ++index) {
        const std::uint32_t value = index < 8U ? registers.d[index] : registers.a[index - 8U];
        const std::size_t offset = index * 4U;
        register_bytes[offset] = static_cast<std::uint8_t>(value >> 24);
        register_bytes[offset + 1U] = static_cast<std::uint8_t>(value >> 16);
        register_bytes[offset + 2U] = static_cast<std::uint8_t>(value >> 8);
        register_bytes[offset + 3U] = static_cast<std::uint8_t>(value);
    }
    if (!write_bytes(paths[2], &ram[0], ram.size()) ||
        !write_bytes(paths[3], &register_bytes[0], register_bytes.size())) {
        return 1;
    }
    std::ofstream output_writes(paths[4].c_str(), std::ios::binary | std::ios::trunc);
    if (!output_writes) {
        std::cerr << "cannot open port output\n";
        return 1;
    }
    // Diagnostic records: byte size, BE32 CPU port address, BE32 value.
    for (std::size_t index = 0; index < writes.size(); ++index) {
        const ms5::VideoPortWrite& write = writes[index];
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
    std::cout << "{\"next_pc\":" << result.next_pc
              << ",\"restored\":" << (result.restored ? "true" : "false")
              << ",\"stack_address\":[" << result.stack_address[0] << ',' << result.stack_address[1]
              << "],\"stack_value\":[" << result.stack_value[0] << ',' << result.stack_value[1]
              << "],\"writes\":" << writes.size() << "}\n";
    return 0;
}
