#ifndef MS5_SCENE_NODE_H
#define MS5_SCENE_NODE_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
struct SceneNodeState {
    std::uint32_t d0, d1, d2, d3, d4, d5, d6, d7, a0, a1, a2, a4;
    SceneNodeState() : d0(0), d1(0), d2(0), d3(0), d4(0), d5(0), d6(0), d7(0), a0(0), a1(0), a2(0), a4(0) {}
};
// Confirmed fixed routines43dda/16fac/43e08/43e22/16fee/43e38/43ea8,
// aliases1728c, scales1724c/1726c and clear17292. Complete aligned RAM spans
// required; failures preserve all RAM/state. Twelve data/address registers
// are carried;43e08 converts incoming lowWORDs to16.16 before position. CCR and hardware timing excluded. Arithmetic uses native widths.
bool step_scene_node(std::vector<std::uint8_t>& ram, std::uint32_t entry,
                     SceneNodeState& state, std::string& error);
}
#endif
