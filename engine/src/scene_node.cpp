#include "ms5/scene_node.h"
#include "ms5/position_state.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram,at)) << 16) | word(ram,at + 2);
}
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    put_word(ram,at,static_cast<std::uint16_t>(value >> 16)); put_word(ram,at + 2,static_cast<std::uint16_t>(value));
}
std::int32_t signed_word(std::uint32_t value) {
    value &= 65535U; return value < 32768U ? static_cast<std::int32_t>(value) : static_cast<std::int32_t>(value) - 65536;
}
std::uint32_t scale(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value, bool y) {
    const std::uint32_t factor = word(ram,at + (y ? 0x2a : 0x28));
    const std::uint32_t product = (value & 65535U) * factor;
    const std::size_t fraction = at + (y ? 0x2d : 0x2c);
    const unsigned int sum = ram[fraction] + (product & 255U);
    ram[fraction] = static_cast<std::uint8_t>(sum);
    const std::uint32_t shifted = (product >> 8) | ((product & 0x80000000U) != 0 ? 0xff000000U : 0U);
    const std::int32_t signed_product = signed_word(value >> 16) * signed_word(factor);
    const std::uint32_t result = (static_cast<std::uint32_t>(signed_product) << 8) + shifted + (sum > 255U ? 1U : 0U);
    put(ram,at + (y ? 0x0c : 8),result); return result;
}
}
bool step_scene_node(std::vector<std::uint8_t>& ram, std::uint32_t entry,
                     SceneNodeState& state, std::string& error) {
    std::size_t span = 0x26;
    switch (entry) {
    case 0x16fac: span = 0x7b; break;
    case 0x16fee: case 0x1724c: case 0x1726c: span = 0x2e; break;
    case 0x17292: span = 0x2080; break;
    case 0x43dda: case 0x43e22: case 0x43e38: case 0x43ea8: case 0x1728c: break;
    default: error = "unsupported scene node entry"; return false;
    }
    if (ram.size() != 65536 || (state.a0 & 1U) != 0 || state.a0 < 0x100000 || state.a0 > 0x110000 - span) {
        error = "scene node requires 64KiB RAM and complete aligned A0 span"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneNodeState next = state; const std::size_t at = state.a0 - 0x100000;
        if (entry == 0x43dda || entry == 0x16fac) {
            next.d0 = 0;
            for (std::size_t offset = 0; offset < 0x26; ++offset) candidate[at + offset] = 0;
            if (entry == 0x16fac) {
                candidate[at + 0x2c] = 0; candidate[at + 0x2d] = 0; put(candidate,at + 0x2e,0);
                put_word(candidate,at + 0x32,0); put_word(candidate,at + 0x34,0); put(candidate,at + 0x36,0xffffffffU);
                put_word(candidate,at + 0x28,0x100); put_word(candidate,at + 0x2a,0x100); candidate[at + 0x7a] = 6;
            }
        } else if (entry == 0x17292) {
            next.d0 = 0;
            for (std::size_t offset = 0x80; offset < 0x2080; ++offset) candidate[at + offset] = 0;
            next.a1 = next.a0 + 0x2080;
        } else if (entry == 0x1724c) next.d0 = scale(candidate,at,next.d0,false);
        else if (entry == 0x1726c) next.d1 = scale(candidate,at,next.d1,true);
        else {
            if (entry == 0x16fee) put_word(candidate,at + 0x2c,0);
            if (entry == 0x43e22 || entry == 0x16fee) {
                put(candidate,at + 0x10,next.a1); put(candidate,at,next.d0); put(candidate,at + 4,next.d1); put_word(candidate,at + 0x24,0);
            }
            //43ea8 changes only local0/4 before43e3e captures old worldY and parent.
            next.d3 = get(candidate,at + 0x18); next.a1 = get(candidate,at + 0x10);
            const bool advance = entry == 0x43ea8 || entry == 0x1728c;
            if (!update_position(&candidate[0],candidate.size(),next.a0,advance,error)) return false;
            next.d0 = get(candidate,at + 0x14); next.d1 = get(candidate,at + 0x18);
        }
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene node transaction"; return false; }
}
}
