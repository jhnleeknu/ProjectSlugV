#ifndef MS5_SCENE_MAP_REFRESH_H
#define MS5_SCENE_MAP_REFRESH_H
#include "ms5/scene_map_transfer.h"
namespace ms5 {
// Native16f0e/18702/1861a/18656. Borrowed resource windows use the same
// address/bank rules as transfer_scene_map. Every call publishes RAM/registers/
// ordered ports only on success. Column searches have a temporary1048576-step
// budget; zero DBRA column counts retain the native65536 iterations.
bool update_scene_columns(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& state, std::vector<VideoPortWrite>& ports, std::string& error);
bool transfer_wrapped_scene_map(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& state, std::vector<VideoPortWrite>& ports, std::string& error);
bool refresh_scene_map(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& state, std::vector<VideoPortWrite>& ports, std::string& error);
bool refresh_moved_scene_map(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& state, std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
