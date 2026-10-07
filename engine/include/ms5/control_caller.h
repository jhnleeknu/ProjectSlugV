#ifndef MS5_CONTROL_CALLER_H
#define MS5_CONTROL_CALLER_H
#include "ms5/palette_resource.h"
#include "ms5/video_port.h"
namespace ms5 {
// Originalf5a after9136 returns: consume its low status byte, preserve/restore
// video and palette state and either loop or advance the counter. RAM maps
//64KiB at100000; object is even with a complete0x85-byte span. On success
// next_pc is ec4 (loop boundary), fee (before TRAP15), or0 (normal return).
// Trap success commits all preceding effects, unlike an unsupported-input
// failure. CPU registers/flags, ec4 execution and trap handler are excluded.
// Success replaces next_pc/writes. Failure preserves RAM/next_pc/writes.
bool consume_control_result(std::vector<std::uint8_t>& ram,
                            const std::vector<PaletteRecord>& records,
                            std::uint32_t object_address,std::uint32_t control_d0,
                            std::uint32_t& next_pc,std::vector<VideoPortWrite>& writes,
                            std::string& error);
}
#endif
