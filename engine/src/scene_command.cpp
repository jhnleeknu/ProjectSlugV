#include "ms5/scene_command.h"
#include "ms5/scene_node.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(bytes[at]) << 8) | bytes[at + 1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    return (static_cast<std::uint32_t>(word(bytes,at)) << 16) | word(bytes,at + 2);
}
void put_word(std::vector<std::uint8_t>& bytes, std::size_t at, std::uint16_t value) {
    bytes[at] = static_cast<std::uint8_t>(value >> 8); bytes[at + 1] = static_cast<std::uint8_t>(value);
}
void put_long(std::vector<std::uint8_t>& bytes, std::size_t at, std::uint32_t value) {
    put_word(bytes,at,static_cast<std::uint16_t>(value >> 16)); put_word(bytes,at + 2,static_cast<std::uint16_t>(value));
}
bool supported(unsigned int opcode) {
    return opcode == 0x0c || opcode == 0x14 || opcode == 0x18 || opcode == 0x1c || opcode == 0x20 ||
        opcode == 0x28 || opcode == 0x2c || opcode == 0x30 || opcode == 0x34 || opcode == 0x38 ||
        opcode == 0x3c || opcode == 0x40 || opcode == 0x44 || opcode == 0x48 || opcode == 0x4c;
}
bool select_node(const FixedDataResource& pointers, unsigned int selector, std::size_t span,
                 std::uint32_t& address, std::size_t& offset, std::string& error) {
    if (pointers.source_cpu_address != 0x1a08e || pointers.source_rom_offset != 0x1a08e || pointers.data.size() != 16 ||
        selector > 12 || (selector & 3U)) { error = "scene node selector requires fixed1a08e table and selector0/4/8/12"; return false; }
    address = longword(pointers.data,selector);
    if ((address & 1U) || address < 0x100000 || address > 0x110000 - span) {
        error = "scene command node requires aligned complete RAM span"; return false;
    }
    offset = address - 0x100000; return true;
}
}
bool execute_scene_command(std::vector<std::uint8_t>& ram, const SceneScript& script,
    const FixedDataResource& pointers, SceneCommandState& state,
    std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536) { error = "scene command requires exactly64KiB RAM"; return false; }
    try {
        SceneScript decoded;
        if (!decode_scene_script(script.source,decoded,error)) return false;
        const SceneCommand* command = NULL;
        for (std::size_t i = 0; i < decoded.commands.size(); ++i) {
            if (decoded.commands[i].source_cpu_address == state.a1) { command = &decoded.commands[i]; break; }
        }
        if (command == NULL || !supported(command->opcode)) { error = "scene command address or handler unsupported"; return false; }
        std::vector<std::uint8_t> candidate = ram; SceneCommandState next = state; std::vector<VideoPortWrite> output;
        const std::vector<std::uint8_t>& operands = command->operands;
        const unsigned int opcode = command->opcode;
        next.d7 = (next.d7 & 0xffff0000U) | opcode;
        next.a1 = command->source_cpu_address + 2;
        if (opcode == 0x0c) {
            next.a0 = longword(operands,0); put_long(candidate,0xd40e,next.a0);
        } else if (opcode == 0x30) {
            for (unsigned int i = 0; i < 4; ++i) put_word(candidate,0xd426 + i*2,word(operands,i*2));
        } else if (opcode == 0x34) {
            const unsigned int value = word(operands,0);
            next.d0 = (next.d0 & 0xffff0000U) | (((value << 1) | (value >> 15)) & 3U);
            next.d1 = (next.d1 & 0xffffff00U) | ((candidate[0xd3cc] & 0xfcU) | (next.d0 & 255U));
            candidate[0xd3cc] = static_cast<std::uint8_t>(next.d1);
        } else if (opcode == 0x38) {
            put_long(candidate,0xd3fc,longword(operands,0)); put_long(candidate,0xd400,longword(operands,4));
        } else if (opcode == 0x3c) put_word(candidate,0xd432,word(operands,0));
        else if (opcode == 0x44) { put_word(candidate,0xd42e,word(operands,0)); put_word(candidate,0xd430,word(operands,2)); }
        else if (opcode == 0x48) put_word(candidate,0xd43c,word(operands,0));
        else if (opcode == 0x4c) put_long(candidate,0xd434,longword(operands,0));
        else if (opcode == 0x28) put_word(candidate,0xd416,word(operands,0));
        else if (opcode == 0x20) {
            next.d7 = (next.d7 & 0xffffff00U) | ((candidate[0xd40c] & operands[0]) | operands[1]);
            candidate[0xd40c] = static_cast<std::uint8_t>(next.d7);
        } else if (opcode == 0x2c) {
            const std::uint16_t value = word(operands,0);
            next.d0 = (next.d0 & 0xffff0000U) | ((value & 0x8000U) ? 0x7fffU : value);
            put_word(candidate,0xd416,static_cast<std::uint16_t>(next.d0)); put_word(candidate,0xd41e,static_cast<std::uint16_t>(next.d0));
            next.d0 = (next.d0 & 0xffff0000U) | static_cast<std::uint16_t>(next.d0 - word(operands,2));
            put_word(candidate,0xd420,static_cast<std::uint16_t>(next.d0));
            next.d0 = (next.d0 & 0xffff0000U) | word(operands,4);
            put_long(candidate,0xd422,command->source_cpu_address + 8);
        } else if (opcode == 0x40) {
            const std::uint16_t original = word(operands,0);
            next.d0 = (next.d0 & 0xffff0000U) | static_cast<std::uint16_t>(original - 1U);
            candidate[0x4d90] = original == 0 ? 0 : static_cast<std::uint8_t>(next.d0);
            if (original == 0) candidate[0x4d91] |= 8; else candidate[0x4d91] &= 0xf7;
            VideoPortWrite write; write.size = 2; write.address = 0x3c0006; write.value = word(candidate,0x4d90); output.push_back(write);
        } else {
            const unsigned int selector = word(operands,0);
            next.d7 = (next.d7 & 0xffff0000U) | selector;
            std::size_t node = 0;
            const std::size_t span = opcode == 0x14 ? 0x2e : opcode == 0x18 ? 0x2c : 0x7b;
            if (!select_node(pointers,selector,span,next.a0,node,error)) return false;
            if (opcode == 0x14) {
                next.d0 = (static_cast<std::uint32_t>(word(operands,2)) << 16) + longword(candidate,0xd38e);
                next.d1 = (static_cast<std::uint32_t>(word(operands,4)) << 16) + longword(candidate,0xd392);
                next.d2 = longword(candidate,node + 0x14);
                const std::uint8_t old_stamp = candidate[0xd494];
                SceneNodeState position; position.d0 = next.d0; position.d1 = next.d1; position.d3 = next.d3; position.a0 = next.a0;
                if (!step_scene_node(candidate,0x16fee,position,error)) return false;
                next.d0 = position.d0; next.d1 = position.d1; next.d3 = position.d3; next.a0 = position.a0; next.d7 = 0;
                next.d4 &= 0xffffff00U;
                // History writes follow the native stamp read; retain its earlier
                // byte when the history span aliases the global stamp.
                const std::uint8_t stamp = 0xd494 >= node + 0x1c && 0xd494 < node + 0x24 ? old_stamp : candidate[0xd494];
                next.d5 = (next.d5 & 0xffffff00U) | stamp;
            } else if (opcode == 0x18) {
                put_word(candidate,node + 0x28,word(operands,2)); put_word(candidate,node + 0x2a,word(operands,4));
            } else {
                if (word(operands,2) != 0) candidate[node + 0x7a] |= 0x81;
                else {
                    candidate[node + 0x7a] &= 0xfe;
                    const std::uint16_t slot = word(candidate,node + 0x26);
                    next.d7 = (next.d7 & 0xffff0000U) | slot;
                    if ((slot & 0x8000U) == 0) {
                        VideoPortWrite write; write.size = 1; write.address = 0x300001; write.value = next.d0 & 255U; output.push_back(write);
                        next.d6 = (next.d6 & 0xffff0000U) | slot;
                        next.d7 = (next.d7 & 0xffff0000U) | static_cast<std::uint16_t>(slot + 0x8201U);
                        next.d6 = (next.d6 & 0xffff0000U) | static_cast<std::uint16_t>(slot + 0x8001U);
                        next.d7 = (next.d7 << 16) | (next.d7 >> 16);
                        next.d6 = (next.d6 << 16) | (next.d6 >> 16);
                        next.d6 = (next.d6 & 0xffff0000U) | 0x0fffU;
                        next.d7 = (next.d7 & 0xffff0000U) | 0x8000U;
                        next.d5 = 0x10000;
                        for (unsigned int i = 0; i < 32; ++i) {
                            write.size = 4; write.address = 0x3c0000; write.value = next.d7; output.push_back(write); next.d7 += 0x10000U;
                            write.value = next.d6; output.push_back(write); next.d6 += 0x10000U;
                        }
                    }
                }
            }
        }
        next.a1 = command->next_cpu_address;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene command transaction"; return false; }
}
}
