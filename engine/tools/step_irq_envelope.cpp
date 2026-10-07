#include "ms5/irq_envelope.h"

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
    if (size != 0U) {
        output.write(reinterpret_cast<const char*>(bytes),
                     static_cast<std::streamsize>(size));
    }
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
    const bool finish = mode == "finish";
    if ((!begin && !finish) || (begin && argc != 10) || (finish && argc != 11)) {
        std::cerr << "usage: step_irq_envelope begin INPUT_RAM INPUT_STACK INPUT_REGS OUTPUT_RAM OUTPUT_STACK OUTPUT_REGS OUTPUT_PORTS STACK_BASE\n"
                  << "       step_irq_envelope finish INPUT_RAM INPUT_STACK INPUT_REGS OUTPUT_RAM OUTPUT_STACK OUTPUT_REGS OUTPUT_PORTS STACK_BASE VIDEO_STATUS\n";
        return 2;
    }
    std::uint32_t stack_base = 0U;
    std::uint32_t video_status = 0U;
    if (!parse_integer(argv[9], 0xffffffU, stack_base) ||
        (finish && !parse_integer(argv[10], 0xffffU, video_status))) {
        std::cerr << "STACK_BASE must be decimal or 0x-prefixed uint24; VIDEO_STATUS uint16\n";
        return 1;
    }
    if (stack_base < 0x110000U || (stack_base & 1U) != 0U) {
        std::cerr << "STACK_BASE must be even and at least 0x110000\n";
        return 1;
    }
    const std::string paths[7] = {argv[2], argv[3], argv[4], argv[5], argv[6], argv[7], argv[8]};
    for (std::size_t index = 1U; index < 7U; ++index) {
        for (std::size_t other = 0U; other < index; ++other) {
            if (same_file(paths[index], paths[other])) {
                std::cerr << "all inputs and outputs must be distinct files\n";
                return 1;
            }
        }
    }
    std::vector<std::uint8_t> ram;
    std::vector<std::uint8_t> register_bytes;
    if (!read_exact(paths[0], 65536U, ram) || !read_exact(paths[2], 64U, register_bytes)) {
        return 1;
    }
    std::ifstream stack_input(paths[1].c_str(), std::ios::binary | std::ios::ate);
    if (!stack_input) {
        std::cerr << "cannot open stack input\n";
        return 1;
    }
    const std::streamoff stack_size = stack_input.tellg();
    if (stack_size < 0 || stack_size > static_cast<std::streamoff>(0x1000000U - stack_base) ||
        (stack_size % 2) != 0) {
        std::cerr << "stack input must have even length within the 24-bit address space\n";
        return 1;
    }
    std::vector<std::uint8_t> stack(static_cast<std::size_t>(stack_size));
    stack_input.seekg(0, std::ios::beg);
    if (stack_size != 0 && !stack_input.read(reinterpret_cast<char*>(&stack[0]), stack_size)) {
        std::cerr << "cannot read stack input\n";
        return 1;
    }
    stack_input.close();
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
    ms5::IrqEnvelopeResult result;
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    const bool succeeded = begin ?
        ms5::begin_irq_envelope(ram, stack, stack_base, registers, result, writes, error) :
        ms5::finish_irq_envelope(ram, stack, stack_base, registers,
                                 static_cast<std::uint16_t>(video_status), result, writes, error);
    if (!succeeded) {
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
    if (!write_bytes(paths[3], &ram[0], ram.size()) ||
        !write_bytes(paths[4], stack.empty() ? NULL : &stack[0], stack.size()) ||
        !write_bytes(paths[5], &register_bytes[0], register_bytes.size())) {
        return 1;
    }
    std::ofstream output_writes(paths[6].c_str(), std::ios::binary | std::ios::trunc);
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
              << ",\"bios_handoff\":" << (result.bios_handoff ? "true" : "false")
              << ",\"stack_writes\":[";
    for (std::size_t index = 0U; index < result.stack_writes.size(); ++index) {
        if (index != 0U) {
            std::cout << ',';
        }
        const ms5::VideoPortWrite& write = result.stack_writes[index];
        std::cout << '[' << static_cast<unsigned int>(write.size) << ','
                  << write.address << ',' << write.value << ']';
    }
    std::cout << "]}\n";
    return 0;
}
