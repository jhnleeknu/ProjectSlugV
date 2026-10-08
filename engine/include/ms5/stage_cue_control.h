#ifndef MS5_STAGE_CUE_CONTROL_H
#define MS5_STAGE_CUE_CONTROL_H
#include "ms5/scene_map_transfer.h"
namespace ms5 {
// Confirmed e89fa/e8a1c selection, e8ad0 progression, e8af4 coordinates and
//2986 allocation wrapper. Borrowed fixed windows and live RAM support odd
//BYTE accesses; WORD/LONG accesses require complete aligned spans.
// A6 is unchanged. Only2986 changes allocation_carry. Failure preserves all
//64KiB RAM, thirteen registers and carry. Progression has no artificial cap;
// checked reads/address addition reject streams outside supported windows.
bool step_stage_cue_control(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, bool& allocation_carry, std::string& error);
}
#endif
