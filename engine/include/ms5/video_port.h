#ifndef MS5_VIDEO_PORT_H
#define MS5_VIDEO_PORT_H

#include <cstdint>

namespace ms5 {

// Ordered CPU hardware writes used by video/menu traces, including the
// watchdog port during object restart. size is measured in bytes;
// address is a CPU address and value preserves the full write width.
struct VideoPortWrite {
    std::uint32_t address;
    std::uint32_t value;
    std::uint8_t size;
};

} // namespace ms5

#endif
