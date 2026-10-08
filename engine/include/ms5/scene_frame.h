#ifndef MS5_SCENE_FRAME_H
#define MS5_SCENE_FRAME_H
#include "ms5/scene_update.h"
namespace ms5 {
// Complete native1a73c frame through RTS, using existing control/script,
// camera/motion, update and single-placement contracts in native order.
// Borrowed fixed/banked windows are read only; motion lookup uses the live
// cursor for each helper. A3 persists through twelve-register helpers, A6 is
// unchanged. Failure preserves64KiB RAM/thirteen registers/ordered ports;
// success replaces ports. Natural scheduling, stack and fullCCR are excluded.
bool step_scene_frame(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
