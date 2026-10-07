#ifndef MS5_GAME_INITIALIZATION_H
#define MS5_GAME_INITIALIZATION_H
#include "ms5/game_prelude.h"
#include "ms5/fixed_data_resource.h"
namespace ms5 {
struct GameInitializationState {
    GamePreludeState prelude;
    bool returned;
    GameInitializationState() : returned(false) {}
};
// Native475ca..47640 RTS area suffix, shared by initial setup and area resume.
// Failure preserves full RAM and D0/D1/D3; no hardware writes occur.
bool reset_stage_area(std::vector<std::uint8_t>& ram, std::uint32_t& d0,
                      std::uint32_t& d1, std::uint32_t& d3, std::string& error);
// Original475a4..47642 suffix, including its confirmed nested callees.
// Failure preserves RAM and registers.
bool finish_game_initialization(std::vector<std::uint8_t>& ram,
    const FixedDataResource& records,std::uint32_t& d0,std::uint32_t& d1,
    std::uint32_t& d3,std::string& error);
// Original47570 or direct47594 through return or sound-producer wait. On returned=true the
// prelude data registers are final return values; phase4/next_pc475a4 record
// the last internal boundary, not the caller's return PC. Errors preserve all
// RAM/state/external_reads, including prefix changes before a suffix failure.
bool initialize_game(std::vector<std::uint8_t>& ram,const FixedDataResource& records,
    std::uint8_t external_status,GameInitializationState& state,
    std::uint8_t& external_reads,std::string& error);
}
#endif
