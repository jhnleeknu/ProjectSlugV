#ifndef MS5_SCENE_GENERAL_INITIALIZATION_H
#define MS5_SCENE_GENERAL_INITIALIZATION_H
#include "ms5/scene_update.h"
namespace ms5 {
// Full native1a5a4. Input A0 is script, D0.low target phase, A6 unchanged.
// Borrowed windows follow constituent fixed/banked resource contracts. Script
// and motion require unique fixed windows only when consumed. RAM motion is
// unsupported. A temporary1048576-phase iteration budget rejects nonprogress.
// Failure preserves whole64KiB RAM, thirteen registers and ordered ports.
bool initialize_scene(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
