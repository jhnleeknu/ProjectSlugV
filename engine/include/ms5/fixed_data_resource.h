#ifndef MS5_FIXED_DATA_RESOURCE_H
#define MS5_FIXED_DATA_RESOURCE_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

struct FixedDataResource {
    std::uint32_t source_cpu_address;
    std::uint32_t source_rom_offset;
    std::vector<std::uint8_t> data;

    FixedDataResource() : source_cpu_address(0), source_rom_offset(0) {}
};

// MS5D v1 kind 1 preserves an immutable window of the fixed program ROM.
// CPU address equals ROM file offset; the window stays below 0x100000.
// A window does not establish the extent or semantics of any logical table.
// Failure preserves resource; success clears error.
bool load_fixed_data_resource(const std::string& path,
                              FixedDataResource& resource, std::string& error);

} // namespace ms5

#endif
