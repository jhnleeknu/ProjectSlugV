#ifndef MS5_CONTROL_ACTIVATION_H
#define MS5_CONTROL_ACTIVATION_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Execute only the inactive (RAM offset 0x7df0 == 0) entry at CPU 0x009136.
// RAM is a caller-owned 65536-byte image based at CPU 0x100000.
// Success returns status 0 for activation or 1 for an unchanged idle state.
// Invalid RAM size or an already active state preserves RAM and status and
// sets error. Success clears error. Optional D1 receives the native result
// only when request evaluation runs; errors preserve it. Native D3 is unchanged.
// Other CPU scratch registers and flags are not modeled.
bool activate_control(std::vector<std::uint8_t>& ram,
                      std::uint8_t& status, std::string& error, std::uint32_t* d1 = NULL);

} // namespace ms5

#endif
