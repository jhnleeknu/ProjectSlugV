#include "ms5/scene_script_run.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram,at)) << 16) | word(ram,at + 2);
}
void put_long(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (24 - i*8));
}
}
bool run_scene_script(std::vector<std::uint8_t>& ram, const SceneScript& script,
    const FixedDataResource& pointers, SceneCommandState& state, SceneScriptRunResult& result,
    std::vector<VideoPortWrite>& ports, std::string& error,
    const std::vector<FixedDataResource>* dependencies) {
    if (ram.size() != 65536) { error = "scene script loop requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneCommandState next = state;
        SceneScriptRunResult outcome; std::vector<VideoPortWrite> output;
        next.a1 = longword(candidate,0xd412);
        SceneScript decoded; bool decoded_ready = false;
        if (next.a1 != 0) {
            while (true) {
                next.d0 = (next.d0 & 0xffff0000U) | word(candidate,0xd418);
                if (static_cast<std::uint16_t>(next.d0) < word(candidate,0xd416)) { outcome.reason = Waiting; break; }
                if (!decoded_ready) {
                    if (!decode_scene_script(script.source,decoded,error)) return false;
                    decoded_ready = true;
                }
                if (next.a1 == decoded.terminator_cpu_address) {
                    candidate[0xd416] = candidate[0xd417] = 255; outcome.reason = Terminator; break;
                }
                bool found = false;
                for (std::size_t i = 0; i < decoded.commands.size(); ++i) {
                    if (decoded.commands[i].source_cpu_address == next.a1) { found = true; break; }
                }
                if (!found || outcome.commands_executed >= decoded.commands.size()) { error = "scene script loop address or command bound invalid"; return false; }
                std::vector<VideoPortWrite> command_ports;
                if (!execute_scene_command(candidate,decoded,pointers,next,command_ports,error,dependencies)) return false;
                output.insert(output.end(),command_ports.begin(),command_ports.end());
                put_long(candidate,0xd412,next.a1); ++outcome.commands_executed;
            }
        }
        ram.swap(candidate); state = next; result = outcome; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene script loop transaction"; return false; }
}
}
