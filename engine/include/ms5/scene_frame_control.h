#ifndef MS5_SCENE_FRAME_CONTROL_H
#define MS5_SCENE_FRAME_CONTROL_H
#include "ms5/scene_command.h"
namespace ms5 {
// Native1a2b4 condition,1a34c rectangle,1a29e raw duration reset,
//1a526 settings and1a3d6 shake. Reads live RAM or uniquely covered fixed
// windows only when used. Duration scans raw10-byte records with exactffff
// terminal and temporary1048576-record budget. Conditions return native carry;
// duration/settings/shake clear it. Failure preserves64KiB RAM/state/carry.
bool step_scene_frame_control(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneCommandState& state,
    bool& carry, std::string& error);
}
#endif
