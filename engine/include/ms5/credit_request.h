#ifndef MS5_CREDIT_REQUEST_H
#define MS5_CREDIT_REQUEST_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
// Native bbe including a74/a2c/a4e. D0 is preserved/updated at native widths.
// RAM is exactly 64KiB. Other CPU register/flag outputs are not represented.
bool process_credit_request(std::vector<std::uint8_t>& ram,std::uint32_t& d0,std::string& error);
}
#endif
