#ifndef MS5_PALETTE_EFFECT_EXECUTION_H
#define MS5_PALETTE_EFFECT_EXECUTION_H
#include "ms5/object_restart_execution.h"
namespace ms5 {
// Complete native8c16 register/RAM effects, including clamp MOVEQ widths and
// signed DIVS quotient/remainder packing. Incoming A5 is replaced by108000;
// D4..D7,A0..A4,A6 are preserved. No ports/resources/external reads.
// RAM must contain65536bytes; failure preserves RAM and all15registers.
// CCR/cycle behavior and subsequent palette interpolation are excluded.
bool execute_palette_effect(std::vector<std::uint8_t>& ram,
    ObjectRestartState& state, std::string& error);
}
#endif
