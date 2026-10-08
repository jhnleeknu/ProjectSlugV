#ifndef MS5_STAGE_SPATIAL_FRAME_H
#define MS5_STAGE_SPATIAL_FRAME_H
#include "ms5/scene_map_transfer.h"
namespace ms5 {
// Native4701e and46f52 with live RAM counters/DBRA and signed WORD arithmetic.
// Borrowed fixed/matching-bank2/3 windows; no bank switching. A6 is unused.
// Logical bin/count limits are not added: actual checked RAM accesses govern
// supported execution. Failure preserves all64KiB RAM and thirteen registers.
bool step_stage_spatial_frame(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t bank, std::string& error);
}
#endif
