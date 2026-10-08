#include "ms5/program_stack.h"
namespace ms5 {
namespace {
bool stack_stride(unsigned int size, std::uint32_t& stride, std::string& error) {
    if (size != 1 && size != 2 && size != 4) {
        error = "Program stack size must be BYTE, WORD or LONG";
        return false;
    }
    stride = size == 4 ? 4 : 2;
    return true;
}
}
bool push_program_stack(std::vector<std::uint8_t>& ram, std::uint32_t& a7,
    unsigned int size, std::uint32_t value, std::string& error) {
    std::uint32_t stride;
    if (!stack_stride(size, stride, error)) return false;
    const std::uint32_t next = static_cast<std::uint32_t>(a7 - stride);
    if (!write_program_bus_ram(ram, next, size, value, error)) return false;
    a7 = next;
    return true;
}
bool pop_program_stack(const std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, const ProgramBusState& bus,
    std::uint32_t& a7, unsigned int size, std::uint32_t& value, std::string& error) {
    std::uint32_t stride;
    if (!stack_stride(size, stride, error)) return false;
    std::uint32_t candidate;
    if (!read_program_bus(ram, windows, bus, a7, size, candidate, error)) return false;
    a7 = static_cast<std::uint32_t>(a7 + stride);
    value = candidate;
    return true;
}
}
