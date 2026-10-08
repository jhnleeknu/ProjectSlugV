#ifndef MS5_PALETTE_BLEND_EXECUTION_H
#define MS5_PALETTE_BLEND_EXECUTION_H
#include "ms5/object_restart_execution.h"
namespace ms5 {
// Native8cda full15register/RAM effects. D0.low selects BYTE slot then
// becomes slot*16; A1/A2 identify the node. A nonzero reference enables
// D2 BYTE clamp, including whole-register MOVEQ32 for incoming BYTE>=32.
// Arbitrary A5 and all other registers are preserved. No ports/resources.
// Exact64KiB RAM required; failure preserves RAM/state. CCR/stack/cycles
// and subsequent palette interpolation are outside this API.
bool execute_palette_blend(std::vector<std::uint8_t>& ram,
    ObjectRestartState& state, std::string& error);
}
#endif
