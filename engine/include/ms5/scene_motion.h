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
// Native19802 projection/reselection, restoring full D0/D1 after every1972a.
// Backward selection publishes its cursor immediately; forward selection is
// published only when the outer comparison finds a different record. Resource
// checks/selection bounds match evaluate_scene_motion. Null cursor ignores path
// and returns A1=0,D7=0. A temporary1048576-recompute budget bounds execution.
bool resolve_scene_motion_time(std::vector<std::uint8_t>& ram,
    const FixedDataResource* path, SceneCommandState& state, std::string& error);

}
#endif
