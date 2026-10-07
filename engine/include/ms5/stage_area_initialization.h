#ifndef MS5_STAGE_AREA_INITIALIZATION_H
#define MS5_STAGE_AREA_INITIALIZATION_H
#include "ms5/game_initialization.h"
namespace ms5 {
struct StageAreaInitializationState {
    std::uint32_t next_pc, d0, d1, d3, a6;
    std::uint8_t phase;
    GameInitializationState initialization;
    StageAreaInitializationState() : next_pc(0x479d0), d0(0), d1(0), d3(0), a6(0x100b30), phase(0) {}
};
// Native479d0..47a1c before subsequent body; phase1 resumes saved47594
// initialization at3aea without re-reading the area branch. Phase2 is terminal.
// Resources validate only when used. No MMIO writes; conditional external
// status read is counted. Errors preserve RAM, state and external_reads.
bool step_stage_area_initialization(std::vector<std::uint8_t>& ram,
    const FixedDataResource& records, const FixedDataResource& player_lookup,
    const FixedDataResource& selector_lookup, std::uint8_t external_status,
    StageAreaInitializationState& state, std::uint8_t& external_reads, std::string& error);
}
#endif
