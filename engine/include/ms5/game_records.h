#ifndef MS5_GAME_RECORDS_H
#define MS5_GAME_RECORDS_H
#include "ms5/fixed_data_resource.h"
namespace ms5 {
// Native 481de / 4d81c with the fixed 20-record window at CPU/ROM 4cf64.
// D0 bit0 selects RAM d694/d69c. Unsigned D1 word must be below 20.
// Errors preserve RAM and all three data registers.
bool configure_game_record(std::vector<std::uint8_t>& ram, const FixedDataResource& records,
                           std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3,
                           std::string& error);
}
#endif
