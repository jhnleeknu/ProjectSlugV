#ifndef MS5_SCENE_COMMAND_H
#define MS5_SCENE_COMMAND_H
#include "ms5/scene_script.h"
#include "ms5/video_port.h"
namespace ms5 {
struct SceneCommandState {
    std::uint32_t d0, d1, d2, d3, d4, d5, d6, d7, a0, a1, a2, a4;
    SceneCommandState() : d0(0), d1(0), d2(0), d3(0), d4(0), d5(0), d6(0), d7(0), a0(0), a1(0), a2(0), a4(0) {}
};
// A1 identifies an exact opcode address in the redecoded raw script source.
// Opcode1c flag-clear additionally emits the confirmed1701a slot clear.
// Twenty confirmed handlers; terminator is API error.
// Native1a0b6 dispatch through handler RTS. Node table is required only for
// 14/18/1c. Dependencies are borrowed only during this call.
// 00/04/08/10/24 consume exact fixed resource windows only when used. Errors preserve full RAM/state/ordered ports; no caller execution.
bool execute_scene_command(std::vector<std::uint8_t>& ram, const SceneScript& script,
    const FixedDataResource& node_pointers, SceneCommandState& state,
    std::vector<VideoPortWrite>& ports, std::string& error,
    const std::vector<FixedDataResource>* dependencies = NULL);
}
#endif
