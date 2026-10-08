#ifndef MS5_STAGE_REGION_FRAME_H
#define MS5_STAGE_REGION_FRAME_H
#include "ms5/scene_map_transfer.h"
namespace ms5 {
// Confirmed b4a2a,49392,1c028,4d9d6,b481e. A6 and bank2/3 are read only;
// fixed and matching-bank windows are borrowed, with live64KiB RAM reads.
// Only49392 updates activity_carry; other entries preserve its API value.
// Failure preserves RAM, thirteen registers and activity_carry.
bool step_stage_region_frame(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, std::uint32_t bank, bool& activity_carry,
    std::string& error);
}
#endif
