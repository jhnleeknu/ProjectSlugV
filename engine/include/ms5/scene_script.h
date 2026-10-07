#ifndef MS5_SCENE_SCRIPT_H
#define MS5_SCENE_SCRIPT_H
#include "ms5/fixed_data_resource.h"
namespace ms5 {
struct SceneCommand {
    std::uint32_t source_cpu_address, next_cpu_address;
    std::uint16_t opcode;
    std::vector<std::uint8_t> operands, inline_data;
    SceneCommand() : source_cpu_address(0), next_cpu_address(0), opcode(0) {}
};
struct SceneScript {
    FixedDataResource source;
    std::vector<SceneCommand> commands;
    std::uint32_t terminator_cpu_address;
    std::uint16_t terminator_opcode;
    SceneScript() : terminator_cpu_address(0), terminator_opcode(0) {}
};
// Typed decoding only, not interpreter execution. Negative BE16 opcode is
// stored separately; exact window ends immediately after its two bytes.
// Opcode2c's third operand word is a nonnegative even opaque inline length.
// Failure preserves the complete caller output.
bool decode_scene_script(const FixedDataResource& resource, SceneScript& script, std::string& error);
bool load_scene_script(const std::string& path, SceneScript& script, std::string& error);
}
#endif
