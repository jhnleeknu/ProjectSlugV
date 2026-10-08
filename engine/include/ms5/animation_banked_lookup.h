#ifndef MS5_ANIMATION_BANKED_LOOKUP_H
#define MS5_ANIMATION_BANKED_LOOKUP_H
#include "ms5/program_bus.h"
#include "ms5/scene_map_transfer.h"
namespace ms5 {
// Original4a382..4a3ac isolated handler, stopping before4a276. A1 points
// to selectorBYTE; no caller-pointer publication, D6 update, flags or dispatch.
// Errors preserve RAM and all13registers; a6 and borrowed bus state are inputs.
bool execute_animation_banked_lookup(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,const ProgramBusState& bus,
    SceneMapTransferState& registers,std::uint32_t a6,std::string& error);
}
#endif
