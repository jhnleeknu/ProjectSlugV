#ifndef MS5_CONTROL_REQUEST_H
#define MS5_CONTROL_REQUEST_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Read the byte produced at 68000 CPU addresses 0x009086..0x009134.
// RAM is a caller-owned 65536-byte image based at CPU address 0x100000.
// This routine does not modify RAM. Invalid RAM size preserves result and
// sets error; success assigns result and clears error. The game meaning of
// the returned request byte has not been established. Optional D1 receives
// the native full-register result; errors preserve it. Native D3 is unchanged.
bool read_control_request(const std::vector<std::uint8_t>& ram,
                          std::uint8_t& result, std::string& error, std::uint32_t* d1 = NULL);

} // namespace ms5

#endif
