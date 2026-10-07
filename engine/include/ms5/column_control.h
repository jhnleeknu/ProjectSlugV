#ifndef MS5_COLUMN_CONTROL_H
#define MS5_COLUMN_CONTROL_H
#include "ms5/video_port.h"
#include <string>
#include <vector>
namespace ms5 {
// Native1879c. Cache integer X/Y (14/18), subtracting flag25 bits0/1
// modulo16 bits. A changed coordinate sets flag7a bit7; no MMIO is emitted.
// D0/D1 high words survive; D3 becomes0 even when neither coordinate changes.
// Invalid RAM/object preserves all outputs.
bool prepare_column_controls(std::vector<std::uint8_t>& ram,std::uint32_t object,
                             std::uint32_t& d0,std::uint32_t& d1,
                             std::uint32_t& d3,std::string& error);
// Native1ae56: prepare the four scene records with ordered PVC bank writes.
// RAM0010 ends0. Final D0/D1 are the fourth record's coordinates; D3 is0.
bool prepare_scene_columns(std::vector<std::uint8_t>& ram,
                           std::uint32_t& d0,std::uint32_t& d1,std::uint32_t& d3,
                           std::vector<VideoPortWrite>& writes,std::string& error);
// Native 187d8. Object is an aligned 128-byte work RAM record. D0 output
// preserves upper word; active nonnegative-slot paths set low word to Y<<7.
bool refresh_column_controls(std::vector<std::uint8_t>& ram,std::uint32_t object,
                             std::uint32_t& d0,std::vector<VideoPortWrite>& writes,std::string& error);
// Native 1adf8. Four fixed records plus ordered PVC bank writes; RAM0010 ends0.
bool refresh_scene_columns(std::vector<std::uint8_t>& ram,std::uint32_t& d0,
                           std::vector<VideoPortWrite>& writes,std::string& error);
}
#endif
