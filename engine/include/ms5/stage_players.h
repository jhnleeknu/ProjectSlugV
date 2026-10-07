#ifndef MS5_STAGE_PLAYERS_H
#define MS5_STAGE_PLAYERS_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
namespace ms5 {
struct StagePlayersState {
    std::uint32_t d0, d1, d3, a6;
    StagePlayersState() : d0(0), d1(0), d3(0), a6(0x100b30) {}
};
// Native47742; fixed player selected by D0.low==0, signed D1.low removes or
// configures. A6 is preserved without dereference. Errors preserve all outputs.
bool configure_stage_player(std::vector<std::uint8_t>& ram, StagePlayersState& state,
                            std::vector<VideoPortWrite>& ports, std::string& error);
// Native476dc fixed476bc/1040-byte window; stage/area read live from A6.
// Window includes code/data overlaps, not a declared logical table extent.
bool configure_stage_players(std::vector<std::uint8_t>& ram, const FixedDataResource& table,
                             StagePlayersState& state, std::vector<VideoPortWrite>& ports,
                             std::string& error);
// Native479ba..479d0 before subsequent body. LIVE flag gates wrapper; only
// called paths validate A6/table, preserving skipped-path register widths.
bool begin_stage_players(std::vector<std::uint8_t>& ram, const FixedDataResource& table,
                         StagePlayersState& state, std::vector<VideoPortWrite>& ports,
                         std::string& error);
}
#endif
