#ifndef MS5_SCENE_NODE_H
#define MS5_SCENE_NODE_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
struct SceneNodeState {
    std::uint32_t d0, d1, d3, a0, a1;
    SceneNodeState() : d0(0), d1(0), d3(0), a0(0), a1(0) {}
};
// Confirmed fixed routines43dda/16fac/43e22/16fee/43e38/43ea8,
// aliases1728c, scales1724c/1726c and clear17292. Complete aligned RAM spans
// required; failures preserve all RAM/state. A0 preserved; other CPU scratch
// registers/CCR and hardware timing excluded. Arithmetic uses native widths.
bool step_scene_node(std::vector<std::uint8_t>& ram, std::uint32_t entry,
                     SceneNodeState& state, std::string& error);
}
#endif
