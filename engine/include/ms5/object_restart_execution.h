#ifndef MS5_OBJECT_RESTART_EXECUTION_H
#define MS5_OBJECT_RESTART_EXECUTION_H
#include "ms5/video_port.h"
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
struct ObjectRestartState {
    std::uint32_t d[8], a[7];
    ObjectRestartState() { for (unsigned int i = 0; i < 8; ++i) d[i] = 0; for (unsigned int i = 0; i < 7; ++i) a[i] = 0; }
};
// Full native2a28 through299c cleanup. A0 is an aligned c4-byte RAM object
// with initial type0; A1 is a raw stored callback. Live palette unlink/free
// operations preserve native ordering without imposing list integrity rules.
// A0/A6 restore, A5=108000; callback execution and stack/CCR are excluded.
// Checked RAM dereferences and65536 linked-loop budget; unsupported spans or
// traps preserve whole64KiB RAM, fifteen registers and ordered ports.
bool restart_object_full(std::vector<std::uint8_t>& ram, ObjectRestartState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
