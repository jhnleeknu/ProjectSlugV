#ifndef MS5_SCENE_PATH_EXECUTION_H
#define MS5_SCENE_PATH_EXECUTION_H
#include "ms5/scene_map_transfer.h"
namespace ms5 {
// Native16ff8 and19e64 only. Raw borrowed fixed/bank2/bank3 windows use the
// transfer resource rules; metadata and stream may also be LIVE RAM. All RAM,
// registers and ordered ports publish only on success. A temporary1048576
// command budget rejects infinite/oversized execution rather than emulating it.
bool configure_scene_map_descriptor(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
bool execute_scene_path(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
