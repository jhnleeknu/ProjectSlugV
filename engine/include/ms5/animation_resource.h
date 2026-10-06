#ifndef MS5_ANIMATION_RESOURCE_H
#define MS5_ANIMATION_RESOURCE_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

struct AnimationResource {
    std::uint32_t source_cpu_address;
    std::uint32_t source_rom_offset;
    std::vector<std::uint8_t> data;

    AnimationResource() : source_cpu_address(0), source_rom_offset(0) {}
};

// MS5A v1 kind 1 preserves an immutable stream from the fixed program ROM.
// CPU address equals ROM file offset and the stream stays below 0x100000.
// The interpreter validates instruction semantics. Failure preserves resource;
// success clears error. No bytes from the source ROM are modified.
bool load_animation_resource(const std::string& path,
                             AnimationResource& resource, std::string& error);

} // namespace ms5

#endif
