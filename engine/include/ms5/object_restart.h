#ifndef MS5_OBJECT_RESTART_H
#define MS5_OBJECT_RESTART_H

#include "ms5/video_port.h"

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Confirmed CPU 0x002a28 restart path for an object whose +0x10 word is zero.
// RAM is exactly 65536 bytes at CPU 0x100000. object_address is even and
// contains 0xc4 bytes in RAM; callback is an even fixed-ROM address <0x100000.
// Palette release and attached coordinate reset precede the object field reset.
// Success replaces writes with the single watchdog byte write at CPU 0x300001,
// installs callback at object +0, and clears error. Failure preserves RAM and
// writes. Nonzero +0x10 (the original TRAP path) and coordinate indices >=8
// without their high bit set are rejected. Linked object lists are outside
// this static-object path; CPU registers and stack effects are not modeled.
bool restart_static_object(std::vector<std::uint8_t>& ram,
                           std::uint32_t object_address,
                           std::uint32_t callback, std::uint8_t watchdog,
                           std::vector<VideoPortWrite>& writes,
                           std::string& error);

} // namespace ms5

#endif
