#ifndef MS5_STAGE_ENTRY_H
#define MS5_STAGE_ENTRY_H
#include "ms5/scene_initialization.h"
#include "ms5/sound_pair.h"
#include "ms5/stage_catalog.h"
namespace ms5 {
struct StageEntryState {
    std::uint32_t next_pc, d0, d1, d3, a6;
    std::uint8_t phase;
    SoundPairState sound;
    StageEntryState() : next_pc(0x477e4), d0(0), d1(0), d3(0), a6(0x100b30), phase(0) {}
};
// Native477e4/477ee prefix to3aea sound wait or actual selector dispatch target.
// Phase1 resumes only captured sound work. Phase2 is terminal, no body runs.
// Exact64KiB RAM/aligned c4-byte A6; all RAM/state/ports preserved on error.
// Empty-group native loop and unsupported selector trap/misalignment rejected.
bool step_stage_entry(std::vector<std::uint8_t>& ram, const StageCatalog& catalog,
                      const FixedDataResource& debug_tables, StageEntryState& state,
                      std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
