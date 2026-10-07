#include "ms5/scene_script.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(bytes[at]) << 8) | bytes[at + 1]);
}
}
bool decode_scene_script(const FixedDataResource& resource, SceneScript& script, std::string& error) {
    const std::uint32_t base = resource.source_cpu_address;
    if (base == 0 || (base & 1U) || base >= 0x100000 || base != resource.source_rom_offset ||
        resource.data.size() > 0x100000 - base) {
        error = "scene script requires a nonzero aligned fixed-ROM source window"; return false;
    }
    try {
        SceneScript candidate; candidate.source = resource;
        const unsigned int sizes[20] = {8,2,4,4,4,6,6,4,2,6,2,6,8,2,8,2,2,4,2,4};
        std::size_t cursor = 0;
        for (;;) {
            if (resource.data.size() - cursor < 2) { error = "scene script missing terminator or truncated opcode"; return false; }
            const std::size_t start = cursor; const std::uint16_t opcode = word(resource.data,cursor); cursor += 2;
            if ((opcode & 0x8000U) != 0) {
                if (cursor != resource.data.size()) { error = "scene script trailing bytes after terminator"; return false; }
                candidate.terminator_cpu_address = base + static_cast<std::uint32_t>(start); candidate.terminator_opcode = opcode;
                script.source.data.swap(candidate.source.data); script.commands.swap(candidate.commands);
                script.source.source_cpu_address = candidate.source.source_cpu_address;
                script.source.source_rom_offset = candidate.source.source_rom_offset;
                script.terminator_cpu_address = candidate.terminator_cpu_address;
                script.terminator_opcode = candidate.terminator_opcode;
                error.clear(); return true;
            }
            if (opcode > 0x4c || (opcode & 3U)) { error = "scene script unsupported opcode"; return false; }
            const std::size_t size = sizes[opcode/4];
            if (resource.data.size() - cursor < size) { error = "scene script truncated operands"; return false; }
            SceneCommand command; command.source_cpu_address = base + static_cast<std::uint32_t>(start); command.opcode = opcode;
            command.operands.assign(resource.data.begin() + cursor,resource.data.begin() + cursor + size);
            cursor += size;
            if (opcode == 0x2c) {
                const std::uint16_t skip = word(command.operands,4);
                if ((skip & 0x8001U) != 0) { error = "scene script inline length must be nonnegative and even"; return false; }
                if (resource.data.size() - cursor < skip) { error = "scene script truncated inline data"; return false; }
                command.inline_data.assign(resource.data.begin() + cursor,resource.data.begin() + cursor + skip); cursor += skip;
            }
            command.next_cpu_address = base + static_cast<std::uint32_t>(cursor); candidate.commands.push_back(command);
        }
    } catch (const std::bad_alloc&) { error = "cannot allocate scene script decoding"; return false; }
}
bool load_scene_script(const std::string& path, SceneScript& script, std::string& error) {
    FixedDataResource resource;
    if (!load_fixed_data_resource(path,resource,error)) return false;
    return decode_scene_script(resource,script,error);
}
}
