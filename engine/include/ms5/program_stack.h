#ifndef MS5_PROGRAM_STACK_H
#define MS5_PROGRAM_STACK_H
#include "ms5/program_bus.h"
namespace ms5 {
// BYTE/WORD stride2, LONG stride4; A7 arithmetic wraps at32 bits. BYTE
// accesses touch only one byte (including odd A7), leaving padding untouched.
// Pop reads live bus memory. a7 and value must refer to distinct variables.
// Failure preserves RAM/A7/value; success clears error. Callers own frame
// ordering, return-target checks and transactions spanning multiple calls.
bool push_program_stack(std::vector<std::uint8_t>& ram, std::uint32_t& a7,
    unsigned int size, std::uint32_t value, std::string& error);
bool pop_program_stack(const std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, const ProgramBusState& bus,
    std::uint32_t& a7, unsigned int size, std::uint32_t& value, std::string& error);
}
#endif
