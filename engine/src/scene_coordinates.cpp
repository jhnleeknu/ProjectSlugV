#include "ms5/scene_coordinates.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram,at)) << 16) | word(ram,at + 2);
}
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (24 - i*8));
}
void add_scroll(std::vector<std::uint8_t>& ram, SceneNodeState& state) {
    const std::size_t at = state.a0 - 0x100000 + 0x18;
    state.d0 = (state.d0 & 0xffff0000U) | word(ram,0xd404);
    const std::uint16_t value = static_cast<std::uint16_t>(word(ram,at) + state.d0);
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
}
bool update_scene_coordinates(std::vector<std::uint8_t>& ram,
    SceneNodeState& state, std::string& error) {
    if (ram.size() != 65536) { error = "scene coordinates require exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneNodeState next = state;
        next.a0 = 0x10d38e;
        next.d0 = 0U - (get(candidate,0xd3bc) + get(candidate,0xd38e));
        next.d1 = 0U - (get(candidate,0xd3c0) + get(candidate,0xd392) - 0x01000000U);
        put(candidate,0xd396,next.d0); put(candidate,0xd39a,next.d1);
        if (!step_scene_node(candidate,0x43ea8,next,error)) return false;
        add_scroll(candidate,next);
        const std::uint32_t nodes[4] = {0x109156,0x10b1d6,0x10d256,0x10d2d6};
        for (unsigned int i = 0; i < 4; ++i) {
            next.a0 = nodes[i];
            if ((candidate[0xd40c] & (1U << (2*i))) == 0) {
                next.d0 = get(candidate,0xd396);
                if (!step_scene_node(candidate,0x1724c,next,error)) return false;
            }
            if ((candidate[0xd40c] & (1U << (2*i + 1))) == 0) {
                next.d1 = get(candidate,0xd39a);
                if (!step_scene_node(candidate,0x1726c,next,error)) return false;
            }
            if (!step_scene_node(candidate,0x1728c,next,error)) return false;
            add_scroll(candidate,next);
        }
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene coordinates transaction"; return false; }
}
}
