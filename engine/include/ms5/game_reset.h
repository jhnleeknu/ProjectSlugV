#ifndef MS5_GAME_RESET_H
#define MS5_GAME_RESET_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
// Selected fixed-ROM reset entries b7a20,4d126,49a8e,4aa30,b4a24,
// 2ef90,46f2e,4d13c,4ddb6. RAM is exactly64KiB at CPU100000.
// Full D0/D1/D3 follow the native operand widths. Other registers/flags,
// stack effects and the remaining47570 callees are outside this API.
// Unsupported entries or RAM extents fail before mutation, preserving
// RAM and all three register outputs. Success clears error.
bool reset_game_subsystem(std::vector<std::uint8_t>& ram,
                          std::uint32_t entry_cpu_address,
                          std::uint32_t& d0,std::uint32_t& d1,
                          std::uint32_t& d3,std::string& error);
}
#endif
