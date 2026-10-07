#ifndef MS5_SCENE_UPDATE_H
#define MS5_SCENE_UPDATE_H
#include "ms5/scene_initialization.h"
namespace ms5 {
// Complete confirmed1a7a8: coordinate prefix, full-register1afda, then four
//19e64 path executions. Borrowed tables/windows live only for this call.
// Whole RAM/thirteen-register/ordered-port transaction; path/transfer budgets
// and supported resource spans remain those of the constituent APIs.
bool update_scene(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
