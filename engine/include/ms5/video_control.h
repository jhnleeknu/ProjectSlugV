#ifndef MS5_VIDEO_CONTROL_H
#define MS5_VIDEO_CONTROL_H
#include "ms5/video_port.h"
#include <string>
#include <vector>
namespace ms5 {
// Original3db2: query the software shadow at RAM4d90/91. The returned
// word is zero when bit3 is set, otherwise high byte+1 (range1..256).
// This does not read a hardware register. Invalid RAM preserves value.
bool query_video_control(const std::vector<std::uint8_t>& ram,
                         std::uint16_t& value,std::string& error);
// Original3d7e: input is a raw word, not a bounded1..256 setting. Zero
// selects high byte0 and sets low-byte bit3; otherwise store the low byte
// of value-1 and clear bit3. Other low-byte bits are preserved. Emit the
// complete shadow word to CPU port3c0006 as one word write.
// RAM must be64KiB at100000. Success replaces writes; failure preserves
// RAM/writes. Hardware timing and the other CPU register effects are excluded.
bool set_video_control(std::vector<std::uint8_t>& ram,std::uint16_t value,
                       std::vector<VideoPortWrite>& writes,std::string& error);
}
#endif
