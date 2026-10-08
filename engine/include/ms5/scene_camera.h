#ifndef MS5_SCENE_CAMERA_H
#define MS5_SCENE_CAMERA_H
#include "ms5/scene_motion.h"
namespace ms5 {
// Native19a40 X request,19ac8 Y request,19b96 complete camera progression.
// Standalone axes ignore path. Full progression borrows the exact motion
// resource only when cursor nonnull, through existing motion helpers. Native
// N-only tests, ADD/BGE overflow, Y prior-store and asymmetric bounds retained.
// Failure preserves64KiB RAM and twelve registers; ports/CCR are not exposed.
bool step_scene_camera(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const FixedDataResource* path, SceneCommandState& state, std::string& error);
}
#endif
