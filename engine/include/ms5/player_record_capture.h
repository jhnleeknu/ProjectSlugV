#ifndef MS5_PLAYER_RECORD_CAPTURE_H
#define MS5_PLAYER_RECORD_CAPTURE_H
#include "ms5/fixed_data_resource.h"
namespace ms5 {
struct PlayerRecordState {
    std::uint32_t d0, d1, d2, d3, d4, d5, d6;
    PlayerRecordState() : d0(0), d1(0), d2(0), d3(0), d4(0), d5(0), d6(0) {}
};
// Native4d7a6 read-only RAM. Lookup4cf64/4092-byte source window is required
// only for active/source-nonzero paths. Native zero-index TRAP is API error.
bool read_player_record(const std::vector<std::uint8_t>& ram, const FixedDataResource& lookup,
                        PlayerRecordState& state, std::string& error);
// Native48180: destination selected before reading, with native store order.
bool capture_player_record(std::vector<std::uint8_t>& ram, const FixedDataResource& lookup,
                           PlayerRecordState& state, std::string& error);
// Native479ee..479fe before following body. Captures both players then475ca.
// Errors preserve RAM and returned full D0/D1/D3; no hardware writes occur.
bool resume_stage_area(std::vector<std::uint8_t>& ram, const FixedDataResource& lookup,
                       std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3, std::string& error);
}
#endif
