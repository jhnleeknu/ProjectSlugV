#ifndef MS5_STAGE_PREPARATION_H
#define MS5_STAGE_PREPARATION_H
#include "ms5/main_startup.h"
namespace ms5 {
struct StagePreparationState {
    std::uint32_t d0, d1, d3, a6;
    StagePreparationState() : d0(0), d1(0), d3(0), a6(0x100b30) {}
};
// Native477c2: remove descendants/current100bf4, then reset palette gate
// and IRQ callbacks. Full returned A6/Dregs retained; D0 ends0.
bool clear_stage_objects(std::vector<std::uint8_t>& ram, StagePreparationState& state,
                         std::vector<VideoPortWrite>& ports, std::string& error);
// Native479b0..479ba, before remaining body. Errors preserve every output.
bool prepare_stage_body(std::vector<std::uint8_t>& ram, const FixedDataResource& main_bindings,
                        const FixedDataResource& stage_bindings, StagePreparationState& state,
                        std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
