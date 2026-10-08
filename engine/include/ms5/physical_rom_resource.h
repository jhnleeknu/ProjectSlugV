#ifndef MS5_PHYSICAL_ROM_RESOURCE_H
#define MS5_PHYSICAL_ROM_RESOURCE_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
// MS5D v1 kind3 raw physical program-ROM storage, with no CPU-address binding.
struct PhysicalRomResource {
    std::uint32_t source_rom_offset;
    std::vector<std::uint8_t> data;
    PhysicalRomResource() : source_rom_offset(0) {}
};
// Header CPU field is ffffffff; payload1..1MiB, contained in8MiB ROM.
// Exact file length and CRC32 are checked. Failure preserves resource;
// success clears error. Distinct from legacy fixed/banked resource types.
bool load_physical_rom_resource(const std::string& path,
    PhysicalRomResource& resource,std::string& error);
}
#endif
