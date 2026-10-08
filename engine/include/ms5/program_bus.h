#ifndef MS5_PROGRAM_BUS_H
#define MS5_PROGRAM_BUS_H
#include "ms5/fixed_data_resource.h"
namespace ms5 {
struct ProgramBusState {
    std::uint32_t bank_base;
    // Borrowed declared device views; owners must outlive each API invocation.
    const std::vector<std::uint8_t>* vectors;
    const std::vector<std::uint8_t>* pvc;
    ProgramBusState() : bank_base(0x200000), vectors(NULL), pvc(NULL) {}
};
// Exact64KiB RAM; BYTE/WORD/LONG sizes only. Logical32-bit addresses wrap
// explicitly before24-bit bus masking. LONG comprises two independent WORD
// units. Reached ROM units require one complete, unique valid MS5D window.
// Device views are checked only when reached. Failure preserves value/RAM.
bool read_program_bus(const std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, const ProgramBusState& bus,
    std::uint32_t logical, unsigned int size, std::uint32_t& value, std::string& error);
bool write_program_bus_ram(std::vector<std::uint8_t>& ram,
    std::uint32_t logical, unsigned int size, std::uint32_t value, std::string& error);
}
#endif
