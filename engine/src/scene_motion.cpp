#include "ms5/scene_motion.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& data, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(data[at]) << 8) | data[at + 1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& data, std::size_t at) {
    return (static_cast<std::uint32_t>(word(data,at)) << 16) | word(data,at + 2);
}
void put_word(std::vector<std::uint8_t>& data, std::size_t at, std::uint16_t value) {
    data[at] = static_cast<std::uint8_t>(value >> 8); data[at + 1] = static_cast<std::uint8_t>(value);
}
void put_long(std::vector<std::uint8_t>& data, std::size_t at, std::uint32_t value) {
    put_word(data,at,static_cast<std::uint16_t>(value >> 16)); put_word(data,at + 2,static_cast<std::uint16_t>(value));
}
enum Factor { Identity, Left, Right1, Right2, Right3, Zero, Negate, NegLeft, NegRight1, NegRight2, NegRight3 };
const Factor factors[36] = {
    Left,Identity,Right1,Right2,Right3,Zero,NegRight3,NegRight2,NegRight1,Negate,NegLeft,
    NegLeft,Negate,NegRight1,NegRight2,NegRight3,Zero,Right3,Right2,Right1,Identity,Left,
    Identity,Right1,Right2,Zero,NegRight2,NegRight1,Negate,
    Negate,NegRight1,NegRight2,Zero,Right2,Right1,Identity
};
std::uint32_t scale(std::uint32_t value, Factor factor, unsigned int width) {
    const std::uint32_t mask = width == 16 ? 0xffffU : 0xffffffffU;
    value &= mask;
    if (factor == Zero) return 0;
    if (factor == Negate || factor == NegLeft || factor == NegRight1 || factor == NegRight2 || factor == NegRight3) value = (0U - value) & mask;
    if (factor == Left || factor == NegLeft) return (value << 1) & mask;
    unsigned int shift = 0;
    if (factor == Right1 || factor == NegRight1) shift = 1;
    if (factor == Right2 || factor == NegRight2) shift = 2;
    if (factor == Right3 || factor == NegRight3) shift = 3;
    if (shift != 0) return (value >> shift) | ((value & (width == 16 ? 0x8000U : 0x80000000U)) ? mask ^ (mask >> shift) : 0);
    return value;
}
bool reverse(unsigned int index) { return (index >= 11 && index < 22) || index >= 29; }
void interval(const FixedDataResource& path, std::size_t at, SceneCommandState& state) {
    const std::uint16_t type = word(path.data,at + 2); const unsigned int index = type / 4;
    state.d4 = (state.d4 & 0xffff0000U) | type;
    const std::uint16_t delta = static_cast<std::uint16_t>(reverse(index) ? word(path.data,at) - word(path.data,at + 10) : word(path.data,at + 10) - word(path.data,at));
    const std::uint16_t auxiliary = static_cast<std::uint16_t>(scale(delta,factors[index],16));
    if (index < 22) {
        state.d0 = (state.d0 & 0xffff0000U) | delta;
        state.d1 = factors[index] == Zero ? 0 : (state.d1 & 0xffff0000U) | auxiliary;
    } else {
        state.d1 = (state.d1 & 0xffff0000U) | delta;
        state.d0 = factors[index] == Zero ? 0 : (state.d0 & 0xffff0000U) | auxiliary;
    }
}

}
bool evaluate_scene_motion(std::vector<std::uint8_t>& ram, const FixedDataResource* path,
    SceneCommandState& state, std::string& error) {
    if (ram.size() != 65536) { error = "scene motion requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneCommandState next = state;
        next.a1 = longword(candidate,0xd3b4);
        if (next.a1 == 0) {
            next.d0 = static_cast<std::uint32_t>(word(candidate,0xd3b8)) << 16;
            next.d1 = static_cast<std::uint32_t>(word(candidate,0xd3ba)) << 16;
        } else {
            if (path == NULL || path->source_cpu_address == 0 || (path->source_cpu_address & 1U) || path->source_cpu_address != path->source_rom_offset ||
                path->source_cpu_address >= 0x100000 || path->data.size() < 14 || path->data.size() > 65536 || path->data.size() > 0x100000 - path->source_cpu_address ||
                (path->data.size() - 4) % 10 || word(path->data,path->data.size() - 2) != 0xffff) { error = "invalid exact scene motion resource"; return false; }
            const std::size_t records = (path->data.size() - 4) / 10;
            for (std::size_t i = 0; i < records; ++i) {
                const unsigned int type = word(path->data,i*10 + 2);
                if (type > 0x8c || (type & 3U)) { error = "unsupported scene motion type"; return false; }
            }
            if (next.a1 < path->source_cpu_address || next.a1 - path->source_cpu_address >= records*10 || (next.a1 - path->source_cpu_address) % 10) { error = "scene motion cursor is not a complete record"; return false; }
            std::size_t at = next.a1 - path->source_cpu_address;
            next.d7 = (next.d7 << 16) | (next.d7 >> 16);
            std::size_t budget = records*2 + 1;
            while (true) {
                if (budget-- == 0) { error = "scene motion selection exceeds operation bound"; return false; }
                const std::uint16_t time = static_cast<std::uint16_t>(next.d7);
                const std::uint16_t start = word(path->data,at), end = word(path->data,at + 10);
                if ((static_cast<std::uint16_t>(time - start) & 0x8000U) != 0) {
                    if (start == 0) { next.d7 = static_cast<std::uint32_t>(start) << 16; break; }
                    next.d4 = (next.d4 & 0xffff0000U) | word(path->data,at + 2);
                    next.d0 = (next.d0 & 0xffff0000U) | word(path->data,at + 6);
                    const std::size_t base = static_cast<std::uint16_t>(next.d4) < 0x58 ? 0xd3ba : 0xd3b8;
                    put_word(candidate,base,static_cast<std::uint16_t>(word(candidate,base) - next.d0));
                    if (at < 10) { error = "scene motion needs a previous record outside window"; return false; }
                    at -= 10; next.a1 = path->source_cpu_address + static_cast<std::uint32_t>(at);
                    interval(*path,at,next);
                    put_word(candidate,0xd3b8,static_cast<std::uint16_t>(word(candidate,0xd3b8) - next.d0));
                    put_word(candidate,0xd3ba,static_cast<std::uint16_t>(word(candidate,0xd3ba) - next.d1));
                    put_long(candidate,0xd3b4,next.a1);
                } else if ((static_cast<std::uint16_t>(time - end) & 0x8000U) != 0) {
                    next.d7 = (next.d7 << 16) | (next.d7 >> 16); break;
                } else if ((word(path->data,at + 12) & 0x8000U) != 0) {
                    next.d7 = (static_cast<std::uint32_t>(end) << 16) - 1U; break;
                } else {
                    interval(*path,at,next);
                    put_word(candidate,0xd3b8,static_cast<std::uint16_t>(word(candidate,0xd3b8) + next.d0));
                    put_word(candidate,0xd3ba,static_cast<std::uint16_t>(word(candidate,0xd3ba) + next.d1));
                    at += 10; next.a1 = path->source_cpu_address + static_cast<std::uint32_t>(at);
                    next.d4 = (next.d4 & 0xffff0000U) | word(path->data,at + 2);
                    next.d0 = (next.d0 & 0xffff0000U) | word(path->data,at + 6);
                    const std::size_t base = static_cast<std::uint16_t>(next.d4) < 0x58 ? 0xd3ba : 0xd3b8;
                    put_word(candidate,base,static_cast<std::uint16_t>(word(candidate,base) + next.d0));
                }
            }
            put_long(candidate,0xd3b4,next.a1);
            const std::uint16_t type = word(path->data,at + 2); const unsigned int index = type / 4;
            next.d4 = (next.d4 & 0xffff0000U) | type;
            const std::uint32_t start = static_cast<std::uint32_t>(word(path->data,at)) << 16;
            const std::uint32_t delta = reverse(index) ? start - next.d7 : next.d7 - start;
            const std::uint32_t auxiliary = scale(delta,factors[index],32);
            next.d0 = index < 22 ? delta : auxiliary; next.d1 = index < 22 ? auxiliary : delta;
            next.d0 = (static_cast<std::uint32_t>(static_cast<std::uint16_t>((next.d0 >> 16) + word(candidate,0xd3b8))) << 16) | (next.d0 & 0xffffU);
            next.d1 = (static_cast<std::uint32_t>(static_cast<std::uint16_t>((next.d1 >> 16) + word(candidate,0xd3ba))) << 16) | (next.d1 & 0xffffU);
            next.d2 = static_cast<std::uint32_t>(word(path->data,at + 8)) << 16;
            next.d4 = (next.d4 & 0xffff0000U) | type;
            if (type < 0x58) next.d1 += next.d2;
            next.d0 += next.d2;
        }
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene motion transaction"; return false; }
}

}
