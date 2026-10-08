#ifndef MS5_STAGE_BLOCK_DRAW_H
#define MS5_STAGE_BLOCK_DRAW_H
#include "ms5/object_restart_execution.h"
#include "ms5/fixed_data_resource.h"
namespace ms5 {
// Native477a2/ddf9a/362a stream wrappers and35f0 block drawing. Borrowed
// unique fixed windows or live RAM supply aligned WORD/odd BYTE reads.
// All15register effects and ordered video writes are retained; RAM is unchanged.
// Zero width/height wrapping loops are unsupported and rejected explicitly.
// The native unsigned D7>=75000000 TRAP path is a checked failure. Failure
// preserves RAM/state/ports; success replaces ports. Banked streams, stack,
// CCR/cycles and rendered-pixel equivalence are excluded.
bool execute_stage_block_draw(std::vector<std::uint8_t>& ram,
    std::uint32_t entry, const std::vector<FixedDataResource>& windows,
    ObjectRestartState& state, std::vector<VideoPortWrite>& ports,
    std::string& error);
}
#endif
