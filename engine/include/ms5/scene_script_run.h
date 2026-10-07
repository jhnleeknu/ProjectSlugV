#ifndef MS5_SCENE_SCRIPT_RUN_H
#define MS5_SCENE_SCRIPT_RUN_H
#include "ms5/scene_command.h"
namespace ms5 {
enum SceneScriptRunReason { NoScript = 0, Waiting = 1, Terminator = 2 };
struct SceneScriptRunResult {
    SceneScriptRunReason reason;
    std::uint32_t commands_executed;
    SceneScriptRunResult() : reason(NoScript), commands_executed(0) {}
};
// Native1a26a phase-gated command loop. Natural frame clock is not implemented.
// Null/initial wait does not inspect script or borrowed dependencies.
// Failure preserves RAM/full state/result/aggregate ports, including late errors.
bool run_scene_script(std::vector<std::uint8_t>& ram, const SceneScript& script,
    const FixedDataResource& node_pointers, SceneCommandState& state,
    SceneScriptRunResult& result, std::vector<VideoPortWrite>& ports, std::string& error,
    const std::vector<FixedDataResource>* dependencies = NULL);
}
#endif
