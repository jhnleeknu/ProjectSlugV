#ifndef MS5_SCENE_MOTION_H
#define MS5_SCENE_MOTION_H
#include "ms5/scene_command.h"
namespace ms5 {
// Native19938 motion selection/evaluation. Path is borrowed during the call.
// Current cursor comes from RAMd3b4; null does not inspect the resource.
// Raw10-byte records and final4-byte terminal use all36 types. Selection
// exceeding2*record_count+1 operations is rejected as unsupported cyclic input.
// Failure preserves exactly64KiB RAM and all twelve state registers.
bool evaluate_scene_motion(std::vector<std::uint8_t>& ram,
    const FixedDataResource* path, SceneCommandState& state, std::string& error);
}
#endif
