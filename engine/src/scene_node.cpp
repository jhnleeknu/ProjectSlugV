#include "ms5/scene_node.h"
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
void scale(std::vector<std::uint8_t>& ram, std::size_t at, SceneNodeState& state, bool y) {
    const std::uint32_t input = y ? state.d1 : state.d0;
    const std::uint32_t factor = word(ram,at + (y ? 0x2a : 0x28));
    state.d7 = (state.d7 & 0xffff0000U) | factor;
    state.d6 = (input & 65535U) * factor;
    const std::size_t fraction = at + (y ? 0x2d : 0x2c);
    const unsigned int sum = ram[fraction] + (state.d6 & 255U);
    ram[fraction] = static_cast<std::uint8_t>(sum); state.d5 = sum > 255U ? 0xffffffffU : 0;
    state.d6 = ((state.d6 >> 8) | ((state.d6 & 0x80000000U) ? 0xff000000U : 0U)) - state.d5;
    const std::int32_t signed_product = signed_word(input >> 16) * signed_word(factor);
    const std::uint32_t result = (static_cast<std::uint32_t>(signed_product) << 8) + state.d6;
    if (y) state.d1 = result; else state.d0 = result;
    put(ram,at + (y ? 0x0c : 8),result);
}
bool position(std::vector<std::uint8_t>& ram, std::size_t at, SceneNodeState& state, bool advance, std::string& error) {
    if (advance) { put(ram,at,get(ram,at) + get(ram,at + 8)); put(ram,at + 4,get(ram,at + 4) + get(ram,at + 0xc)); }
    state.d2 = get(ram,at + 0x14); state.d3 = get(ram,at + 0x18); state.a1 = get(ram,at + 0x10);
    state.d0 = get(ram,at); state.d1 = get(ram,at + 4); state.d7 = 0;
    if (state.a1 != 0) {
        if ((state.a1 & 1U) || state.a1 < 0x100000 || state.a1 > 0x110000 - 0x26) { error = "invalid scene coordinate parent span"; return false; }
        const std::size_t parent = state.a1 - 0x100000;
        state.d4 = get(ram,parent + 0x14); state.d5 = get(ram,parent + 0x18);
        unsigned int sum = (state.d1 & 65535U) + (state.d5 & 65535U);
        state.d6 = (state.d6 & 0xffff0000U) | static_cast<std::uint16_t>(sum);
        const unsigned int carry_y = sum > 65535U ? 1 : 0;
        sum = (state.d0 & 65535U) + (state.d4 & 65535U);
        state.d6 = (state.d6 & 0xffff0000U) | static_cast<std::uint16_t>(sum);
        state.d7 = 2*carry_y + (sum > 65535U ? 1U : 0U);
        state.d7 = (state.d7 & 0xffffff00U) | ((state.d7 & 255U) | ram[parent + 0x25]);
        state.d0 += state.d4; state.d1 += state.d5;
    }
    ram[at + 0x25] = static_cast<std::uint8_t>(state.d7); put(ram,at + 0x14,state.d0); put(ram,at + 0x18,state.d1);
    state.d5 = (state.d5 & 0xffffff00U) | ram[0xd494]; state.d4 = (state.d4 & 0xffffff00U) | ram[at + 0x24];
    if ((state.d4 & 255U) == 0) {
        ram[at + 0x24] = static_cast<std::uint8_t>(state.d5); put(ram,at + 0x1c,state.d0); put(ram,at + 0x20,state.d1);
    } else if ((state.d4 & 255U) != (state.d5 & 255U)) {
        ram[at + 0x24] = static_cast<std::uint8_t>(state.d5); put(ram,at + 0x1c,state.d2); put(ram,at + 0x20,state.d3);
    }
    return true;
}
}
bool step_scene_node(std::vector<std::uint8_t>& ram, std::uint32_t entry,
                     SceneNodeState& state, std::string& error) {
    std::size_t span = 0x26;
    switch (entry) {
    case 0x16fac: span = 0x7b; break;
    case 0x16fee: case 0x1724c: case 0x1726c: span = 0x2e; break;
    case 0x17292: span = 0x2080; break;
    case 0x43dda: case 0x43e08: case 0x43e22: case 0x43e38: case 0x43ea8: case 0x1728c: break;
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
        } else if (entry == 0x1724c) scale(candidate,at,next,false);
        else if (entry == 0x1726c) scale(candidate,at,next,true);
        else {
            if (entry == 0x16fee) put_word(candidate,at + 0x2c,0);
            if (entry == 0x43e08) { next.d0 <<= 16; next.d1 <<= 16; }
            if (entry == 0x43e08 || entry == 0x43e22 || entry == 0x16fee) {
                put(candidate,at + 0x10,next.a1); put(candidate,at,next.d0); put(candidate,at + 4,next.d1); put_word(candidate,at + 0x24,0);
            }
            const bool advance = entry == 0x43ea8 || entry == 0x1728c;
            if (!position(candidate,at,next,advance,error)) return false;
        }
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene node transaction"; return false; }
}
}
