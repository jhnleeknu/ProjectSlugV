#ifndef MS5_STAGE_COUNTER_H
#define MS5_STAGE_COUNTER_H
#include "ms5/object_restart_execution.h"
namespace ms5 {
// Native4843c throughRTS, including both SEQ BYTE effects. Source0 SBCD
// follows the independently audited external hardware reference in
// docs/analysis/stage-counter-contract.md; no local hardware run is claimed.
// Only actual reached BYTE RAM
// accesses are checked; arbitrary/odd A5 is preserved without mirroring.
// Failure preserves whole64KiB RAM and15registers. No resources/ports;
// CCR/stack/cycles and the caller's continuation are outside this API.
bool execute_stage_counter(std::vector<std::uint8_t>& ram,
    ObjectRestartState& state,std::string& error);
}
#endif
