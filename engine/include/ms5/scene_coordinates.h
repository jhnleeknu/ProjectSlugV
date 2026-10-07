#ifndef MS5_SCENE_COORDINATES_H
#define MS5_SCENE_COORDINATES_H
#include "ms5/scene_node.h"
namespace ms5 {
// Native1a7a8 coordinate prefix, stopping before1a8ca.
// Does not execute debug1afda or the later four19e64 scripts.
// Exactly64KiB RAM; failure preserves RAM and all twelve registers.
bool update_scene_coordinates(std::vector<std::uint8_t>& ram,
    SceneNodeState& state, std::string& error);
}
#endif
