#ifndef MS5_STAGE_READINESS_H
#define MS5_STAGE_READINESS_H
#include "ms5/object_restart_execution.h"
namespace ms5 {
// Whole native4847c chain1bdde/289e/4dee2/4e166. Actual reached accesses
// require complete CPU RAM spans and WORD/LONG alignment; skipped paths do
// not validate later addresses. All15register effects and returned carry
// retained; arbitrary A5 is preserved. RAM is unchanged. Failure preserves
// state/carry. No resources/ports; other CCR/stack/cycles are excluded.
bool execute_stage_readiness(const std::vector<std::uint8_t>& ram,
    ObjectRestartState& state,bool& carry,std::string& error);
}
#endif
