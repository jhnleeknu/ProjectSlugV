#ifndef MS5_SCENE_PLACEMENT_EXECUTION_H
#define MS5_SCENE_PLACEMENT_EXECUTION_H
#include "ms5/scene_command.h"
namespace ms5 {
// Native1a414 stream /1a442 single eligible record /1a470 direct record.
// Single-record execution does not read the returned next cursor.
// Windows are borrowed fixed CPU=ROM data.
// Reads are live, aligned and uniquely covered; writes require CPU RAM.
// Payload lengths must be even and below8000. Non-null motion requires an
// exact fixed motion resource; RAM motion is unsupported. A6 is unchanged.
// A temporary1048576-record loop budget bounds stream execution.
// Failure preserves the full64KiB RAM and twelve public registers.
bool execute_scene_placement(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneCommandState& state,
    std::uint32_t parent_a6, std::string& error);
}
#endif
