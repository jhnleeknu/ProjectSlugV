#ifndef MS5_OBJECT_LISTS_H
#define MS5_OBJECT_LISTS_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

struct ObjectBootRecord {
    std::uint32_t ram_address;
    std::uint32_t callback;
    std::uint16_t words[4];
};

// MS5I v1 wraps eight original big-endian boot records. On failure, records
// are unchanged. Source offsets in the header are ROM file offsets.
bool load_object_boot_resource(const std::string& path,
                               std::vector<ObjectBootRecord>& records,
                               std::string& error);

// Memory effects of CPU 0x002790 through 0x00287c. ram begins at CPU
// 0x100000 and must contain at least 65536 bytes. CPU registers, flags and
// call-stack effects are outside this contract. Invalid inputs cause no writes.
bool initialize_object_lists(std::uint8_t* ram, std::size_t size,
                             const std::vector<ObjectBootRecord>& records,
                             std::string& error);

} // namespace ms5

#endif
