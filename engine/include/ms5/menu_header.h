#ifndef MS5_MENU_HEADER_H
#define MS5_MENU_HEADER_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Reproduce the header update at 68000 CPU address/ROM offset 0x009430,
// including its call to the request selector at 0x009086. RAM is owned by
// the caller and based at CPU address 0x100000. The original copies the
// stored head to A2 without validating or dereferencing it here.
// Invalid RAM size preserves RAM and A2; success clears error.
// Optional D1 returns the native full register; errors preserve it.
// Native D3 is unchanged.
bool update_menu_header(std::vector<std::uint8_t>& ram,
                        std::uint32_t& a2, std::string& error,
                        std::uint32_t* d1 = NULL);

} // namespace ms5

#endif
