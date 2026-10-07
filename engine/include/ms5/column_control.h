#ifndef MS5_COLUMN_CONTROL_H
#define MS5_COLUMN_CONTROL_H
#include "ms5/video_port.h"
#include <string>
#include <vector>
namespace ms5 {
// Native 187d8. Object is an aligned 128-byte work RAM record. D0 output
// preserves upper word; active nonnegative-slot paths set low word to Y<<7.
bool refresh_column_controls(std::vector<std::uint8_t>& ram,std::uint32_t object,
                             std::uint32_t& d0,std::vector<VideoPortWrite>& writes,std::string& error);
// Native 1adf8. Four fixed records plus ordered PVC bank writes; RAM0010 ends0.
bool refresh_scene_columns(std::vector<std::uint8_t>& ram,std::uint32_t& d0,
                           std::vector<VideoPortWrite>& writes,std::string& error);
}
#endif
