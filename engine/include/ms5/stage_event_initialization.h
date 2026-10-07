#ifndef MS5_STAGE_EVENT_INITIALIZATION_H
#define MS5_STAGE_EVENT_INITIALIZATION_H
#include "ms5/object_restart_execution.h"
#include "ms5/fixed_data_resource.h"
namespace ms5 {
// Nativee905c. A0 is the event stream, D0.low target, incoming A5 selects
// the event object at signed offset8bf4 before restart sets A5=108000.
// Fixed MS5D/RAM reads are live and checked; callbacke9150 is stored only.
// A temporary1048576-record budget bounds traversal. Failure preserves whole
// RAM, fifteen public registers and ordered ports, including late failures.
bool initialize_stage_events(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, ObjectRestartState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
