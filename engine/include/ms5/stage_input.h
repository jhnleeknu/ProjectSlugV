#ifndef MS5_STAGE_INPUT_H
#define MS5_STAGE_INPUT_H
#include "ms5/scene_map_transfer.h"
namespace ms5 {
// Confirmed49ab4 mapping,49afe edge mask,49bb4 publication and
//49c20/49c32/49c66 callback setters. Fixed CPU=ROM windows are borrowed;
// reads use live RAM, byte masks may be odd, writes require aligned RAM.
// Default49ab0 mask must be supplied as data. Dynamic callback execution and
// full49b0c are excluded. Failure preserves64KiB RAM and thirteen registers.
bool step_stage_input(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::string& error);
}
#endif
