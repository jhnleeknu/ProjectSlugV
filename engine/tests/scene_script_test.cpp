#include "ms5/scene_script.h"
#include <cassert>
#include <iostream>
namespace {
void append(std::vector<std::uint8_t>& bytes, unsigned int value) {
    bytes.push_back(static_cast<std::uint8_t>(value >> 8)); bytes.push_back(static_cast<std::uint8_t>(value));
}
ms5::FixedDataResource resource() {
    ms5::FixedDataResource source; source.source_cpu_address = source.source_rom_offset = 0x50000; return source;
}
void fails(const ms5::FixedDataResource& source, ms5::SceneScript& script) {
    const std::vector<std::uint8_t> old = script.source.data;
    const std::size_t count = script.commands.size(); const std::uint32_t terminator = script.terminator_cpu_address;
    std::string error;
    assert(!ms5::decode_scene_script(source,script,error));
    assert(script.source.data == old && script.commands.size() == count && script.terminator_cpu_address == terminator && !error.empty());
}
}
int main() {
    ms5::FixedDataResource source = resource();
    const unsigned int sizes[20] = {8,2,4,4,4,6,6,4,2,6,2,6,8,2,8,2,2,4,2,4};
    for (unsigned int i = 0; i < 20; ++i) {
        append(source.data,i*4);
        for (unsigned int j = 0; j < sizes[i]; ++j) source.data.push_back(static_cast<std::uint8_t>(j));
        if (i == 11) {
            source.data[source.data.size() - 2] = 0; source.data[source.data.size() - 1] = 4;
            append(source.data,0xffff); append(source.data,0x1234); // Opaque negative opcode is not a terminator.
        }
    }
    append(source.data,0x8001);
    ms5::SceneScript script; std::string error;
    assert(ms5::decode_scene_script(source,script,error));
    assert(script.commands.size() == 20 && script.source.data == source.data && script.terminator_opcode == 0x8001);
    std::uint32_t cursor = source.source_cpu_address;
    for (unsigned int i = 0; i < 20; ++i) {
        const ms5::SceneCommand& command = script.commands[i];
        assert(command.source_cpu_address == cursor && command.opcode == i*4 && command.operands.size() == sizes[i]);
        cursor += 2 + sizes[i] + (i == 11 ? 4 : 0);
        assert(command.next_cpu_address == cursor);
    }
    assert(script.commands[11].inline_data.size() == 4 && script.commands[11].inline_data[0] == 255 && script.terminator_cpu_address == cursor);
    ms5::FixedDataResource invalid = source; invalid.data.push_back(0); fails(invalid,script);
    invalid = source; invalid.data.resize(invalid.data.size() - 2); fails(invalid,script);
    invalid = resource(); append(invalid.data,3); append(invalid.data,0xffff); fails(invalid,script);
    invalid = resource(); append(invalid.data,0x50); append(invalid.data,0xffff); fails(invalid,script);
    invalid = resource(); append(invalid.data,0); append(invalid.data,0xffff); fails(invalid,script);
    invalid = resource(); append(invalid.data,0x2c); append(invalid.data,0); append(invalid.data,0); append(invalid.data,3); append(invalid.data,0xffff); fails(invalid,script);
    invalid.data[6] = 0x80; invalid.data[7] = 0; fails(invalid,script);
    invalid.data[6] = 0; invalid.data[7] = 8; fails(invalid,script);
    invalid = source; invalid.source_cpu_address |= 1; fails(invalid,script);
    invalid = source; invalid.source_cpu_address = invalid.source_rom_offset = 0; fails(invalid,script);
    invalid = source; invalid.source_cpu_address = invalid.source_rom_offset = 0xffffe; fails(invalid,script);
    invalid = resource(); append(invalid.data,0xfffe);
    assert(ms5::decode_scene_script(invalid,script,error));
    assert(script.commands.empty() && script.terminator_cpu_address == 0x50000 && script.terminator_opcode == 0xfffe);
    invalid.data.clear(); fails(invalid,script);
    assert(!ms5::load_scene_script("/nonexistent/scene.ms5d",script,error));
    assert(script.commands.empty() && script.terminator_opcode == 0xfffe);
    std::cout << "scene_script_test: passed\n";
}
