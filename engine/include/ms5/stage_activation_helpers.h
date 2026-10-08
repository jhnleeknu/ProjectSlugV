#ifndef MS5_STAGE_ACTIVATION_HELPERS_H
#define MS5_STAGE_ACTIVATION_HELPERS_H
#include "ms5/object_restart_execution.h"
namespace ms5 {
// Native4e216/bee/16ed2/49f8c throughRTS. Carry updates only for4e216/bee;
// other entries preserve incoming bool, without claiming their full CCR.
// Actual reached RAM spans/alignment checked; A1 is opaque in49f8c.
// Success replaces ports(empty except49f8c's two PVC WORDs). Errors preserve
// whole64KiB RAM,15registers,carry and ports. Noncanonical A5 TRAP at49f8c
// is a checked failure; stack/cycles/hardware mirroring are excluded.
bool execute_stage_activation_helper(std::vector<std::uint8_t>& ram,
    std::uint32_t entry,ObjectRestartState& state,bool& carry,
    std::vector<VideoPortWrite>& ports,std::string& error);
}
#endif
