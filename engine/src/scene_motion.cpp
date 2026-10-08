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

bool validate_motion(const FixedDataResource* path, std::uint32_t cursor,
    std::size_t& records, std::size_t& at, std::string& error) {
    if (path == NULL || path->source_cpu_address == 0 || (path->source_cpu_address & 1U) || path->source_cpu_address != path->source_rom_offset ||
        path->source_cpu_address >= 0x100000 || path->data.size() < 14 || path->data.size() > 65536 || path->data.size() > 0x100000 - path->source_cpu_address ||
        (path->data.size() - 4) % 10 || word(path->data,path->data.size() - 2) != 0xffff) { error = "invalid exact scene motion resource"; return false; }
    records = (path->data.size() - 4) / 10;
    for (std::size_t i = 0; i < records; ++i) {
        const unsigned int type = word(path->data,i*10 + 2);
        if (type > 0x8c || (type & 3U)) { error = "unsupported scene motion type"; return false; }
    }
    if (cursor < path->source_cpu_address || cursor - path->source_cpu_address >= records*10 || (cursor - path->source_cpu_address) % 10) { error = "scene motion cursor is not a complete record"; return false; }
    at = cursor - path->source_cpu_address;
    return true;
}
bool select_motion(std::vector<std::uint8_t>& ram, const FixedDataResource& path,
    SceneCommandState& state, std::size_t& at, std::size_t records, std::string& error) {
    state.d7 = (state.d7 << 16) | (state.d7 >> 16);
    std::size_t budget = records*2 + 1;
    while (true) {
        if (budget-- == 0) { error = "scene motion selection exceeds operation bound"; return false; }
        const std::uint16_t time = static_cast<std::uint16_t>(state.d7);
        const std::uint16_t start = word(path.data,at), end = word(path.data,at + 10);
        if ((static_cast<std::uint16_t>(time - start) & 0x8000U) != 0) {
            if (start == 0) { state.d7 = static_cast<std::uint32_t>(start) << 16; break; }
            state.d4 = (state.d4 & 0xffff0000U) | word(path.data,at + 2);
            state.d0 = (state.d0 & 0xffff0000U) | word(path.data,at + 6);
            const std::size_t base = static_cast<std::uint16_t>(state.d4) < 0x58 ? 0xd3ba : 0xd3b8;
            put_word(ram,base,static_cast<std::uint16_t>(word(ram,base) - state.d0));
            if (at < 10) { error = "scene motion needs a previous record outside window"; return false; }
            at -= 10; state.a1 = path.source_cpu_address + static_cast<std::uint32_t>(at);
            interval(path,at,state);
            put_word(ram,0xd3b8,static_cast<std::uint16_t>(word(ram,0xd3b8) - state.d0));
            put_word(ram,0xd3ba,static_cast<std::uint16_t>(word(ram,0xd3ba) - state.d1));
            put_long(ram,0xd3b4,state.a1);
        } else if ((static_cast<std::uint16_t>(time - end) & 0x8000U) != 0) {
            state.d7 = (state.d7 << 16) | (state.d7 >> 16); break;
        } else if ((word(path.data,at + 12) & 0x8000U) != 0) {
            state.d7 = (static_cast<std::uint32_t>(end) << 16) - 1U; break;
        } else {
            interval(path,at,state);
            put_word(ram,0xd3b8,static_cast<std::uint16_t>(word(ram,0xd3b8) + state.d0));
            put_word(ram,0xd3ba,static_cast<std::uint16_t>(word(ram,0xd3ba) + state.d1));
            at += 10; state.a1 = path.source_cpu_address + static_cast<std::uint32_t>(at);
            state.d4 = (state.d4 & 0xffff0000U) | word(path.data,at + 2);
            state.d0 = (state.d0 & 0xffff0000U) | word(path.data,at + 6);
            const std::size_t base = static_cast<std::uint16_t>(state.d4) < 0x58 ? 0xd3ba : 0xd3b8;
            put_word(ram,base,static_cast<std::uint16_t>(word(ram,base) + state.d0));
        }
    }
    return true;
}

void selected_position(const std::vector<std::uint8_t>& ram, const FixedDataResource& path, std::size_t at, SceneCommandState& state) {
    const std::uint16_t type = word(path.data,at + 2); const unsigned int index = type / 4;
    state.d4 = (state.d4 & 0xffff0000U) | type;
    const std::uint32_t start = static_cast<std::uint32_t>(word(path.data,at)) << 16;
    const std::uint32_t delta = reverse(index) ? start - state.d7 : state.d7 - start;
    const std::uint32_t auxiliary = scale(delta,factors[index],32);
    state.d0 = index < 22 ? delta : auxiliary; state.d1 = index < 22 ? auxiliary : delta;
    state.d0 = (static_cast<std::uint32_t>(static_cast<std::uint16_t>((state.d0 >> 16) + word(ram,0xd3b8))) << 16) | (state.d0 & 0xffffU);
    state.d1 = (static_cast<std::uint32_t>(static_cast<std::uint16_t>((state.d1 >> 16) + word(ram,0xd3ba))) << 16) | (state.d1 & 0xffffU);
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
            std::size_t records = 0, at = 0;
            if (!validate_motion(path,next.a1,records,at,error) || !select_motion(candidate,*path,next,at,records,error)) return false;
            put_long(candidate,0xd3b4,next.a1);
            selected_position(candidate,*path,at,next);
            const std::uint16_t type = word(path->data,at + 2);
            next.d2 = static_cast<std::uint32_t>(word(path->data,at + 8)) << 16;
            next.d4 = (next.d4 & 0xffff0000U) | type;
            if (type < 0x58) next.d1 += next.d2;
            next.d0 += next.d2;
        }
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene motion transaction"; return false; }
}

bool resolve_scene_motion_time(std::vector<std::uint8_t>& ram, const FixedDataResource* path,
    SceneCommandState& state, std::string& error) {
    if (ram.size() != 65536) { error = "scene motion time requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneCommandState next = state;
        next.a1 = longword(candidate,0xd3b4);
        if (next.a1 == 0) next.d7 = 0;
        else {
            std::size_t records = 0, at = 0;
            if (!validate_motion(path,next.a1,records,at,error)) return false;
            bool done = false;
            for (unsigned int iteration = 0; iteration < 1048576U; ++iteration) {
                const std::uint32_t saved0 = next.d0, saved1 = next.d1;
                const std::uint16_t type = word(path->data,at+2); const unsigned int index = type/4;
                next.d4 = (next.d4 & 0xffff0000U) | type;
                const std::uint32_t axis = index < 22 ? next.d0 : next.d1;
                const std::uint16_t base = word(candidate,index < 22 ? 0xd3b8 : 0xd3ba);
                if (!reverse(index)) {
                    next.d7 = (axis<<16)|(axis>>16);
                    next.d7 = (next.d7 & 0xffff0000U) | static_cast<std::uint16_t>(next.d7-base);
                } else {
                    next.d7 = (static_cast<std::uint32_t>(base)<<16)-axis;
                    next.d7 = (next.d7<<16)|(next.d7>>16);
                }
                next.d7 = (next.d7 & 0xffff0000U) | static_cast<std::uint16_t>(next.d7+word(path->data,at));
                next.d7 = (next.d7<<16)|(next.d7>>16);
                if (!select_motion(candidate,*path,next,at,records,error)) return false;
                next.d0 = saved0; next.d1 = saved1;
                if (next.a1 == longword(candidate,0xd3b4)) { done = true; break; }
                put_long(candidate,0xd3b4,next.a1);
            }
            if (!done) { error = "scene motion time temporary recompute budget exceeded"; return false; }
        }
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene motion time transaction"; return false; }
}


namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void set_word(std::uint32_t& value, std::uint32_t input) { value = (value & 0xffff0000U) | low(input); }
std::uint32_t swap(std::uint32_t value) { return (value << 16) | (value >> 16); }
std::int32_t signed_word(std::uint32_t value) { return low(value) < 0x8000 ? low(value) : static_cast<std::int32_t>(low(value))-65536; }
void exchange(std::uint32_t& left, std::uint32_t& right) { const std::uint32_t saved = left; left = right; right = saved; }
bool span_motion(std::vector<std::uint8_t>& ram, const FixedDataResource* path, SceneCommandState& s, std::string& error) {
    s.a1 = longword(ram,0xd3b4);
    if (s.a1 == 0) {
        s.d0 = static_cast<std::uint32_t>(word(ram,0xd3b8)) << 16;
        s.d1 = static_cast<std::uint32_t>(word(ram,0xd3ba)) << 16;
        s.d2 = 0; s.d3 = 0; return true;
    }
    std::size_t records = 0, at = 0;
    if (!validate_motion(path,s.a1,records,at,error) || !select_motion(ram,*path,s,at,records,error)) return false;
    put_long(ram,0xd3b4,s.a1); selected_position(ram,*path,at,s); s.d2 = 0; s.d3 = 0;
    const std::uint16_t type = word(path->data,at+2); set_word(s.d4,type);
    const std::uint32_t extent = static_cast<std::uint32_t>(word(path->data,at+4)) << 16;
    if (type < 0x58) s.d3 = extent; else s.d2 = extent;
    return true;
}
bool clamp_motion(std::vector<std::uint8_t>& ram, const FixedDataResource* path, SceneCommandState& s, std::string& error) {
    if (!span_motion(ram,path,s,error)) return false;
    if (s.a1 == 0) { put_long(ram,0xd3c4,s.d0); put_long(ram,0xd3c8,s.d1); return true; }
    s.d3 += s.d1; if ((s.d3-s.d1) & 0x80000000U) exchange(s.d1,s.d3);
    s.d1 -= longword(ram,0xd3c8); if (!(s.d1 & 0x80000000U)) put_long(ram,0xd3c8,longword(ram,0xd3c8)+s.d1);
    s.d3 -= longword(ram,0xd3c8); if (s.d3 & 0x80000000U) put_long(ram,0xd3c8,longword(ram,0xd3c8)+s.d3);
    s.d2 += s.d0; if ((s.d2-s.d0) & 0x80000000U) exchange(s.d0,s.d2);
    s.d0 -= longword(ram,0xd3c4); if (!(s.d0 & 0x80000000U)) put_long(ram,0xd3c4,longword(ram,0xd3c4)+s.d0);
    s.d2 -= longword(ram,0xd3c4); if (s.d2 & 0x80000000U) put_long(ram,0xd3c4,longword(ram,0xd3c4)+s.d2);
    return true;
}
bool extend_bounds(std::vector<std::uint8_t>& ram, const FixedDataResource* path, SceneCommandState& s, std::string& error) {
    s.d7 = static_cast<std::uint32_t>(low(s.d7)) << 16;
    if (!span_motion(ram,path,s,error)) return false;
    s.d0 = swap(s.d0); s.d1 = swap(s.d1); s.d2 = swap(s.d2); s.d3 = swap(s.d3);
    set_word(s.d2,s.d2+s.d0); set_word(s.d3,s.d3+s.d1);
    if (signed_word(s.d2) < signed_word(s.d0)) exchange(s.d0,s.d2);
    if (signed_word(s.d3) < signed_word(s.d1)) exchange(s.d1,s.d3);
    if (signed_word(s.d0) < signed_word(word(ram,0xd3f2))) put_word(ram,0xd3f2,low(s.d0));
    if (signed_word(s.d1) < signed_word(word(ram,0xd3f6))) put_word(ram,0xd3f6,low(s.d1));
    if (signed_word(s.d2) > signed_word(word(ram,0xd3f4))) put_word(ram,0xd3f4,low(s.d2));
    if (signed_word(s.d3) > signed_word(word(ram,0xd3f8))) put_word(ram,0xd3f8,low(s.d3));
    return true;
}
void add_saturating_word(std::uint32_t& dest, std::uint32_t addend) {
    const std::uint16_t left = low(dest), right = low(addend), result = static_cast<std::uint16_t>(left+right);
    set_word(dest,result);
    if (((~(left^right) & (left^result)) & 0x8000U) != 0) set_word(dest,0x7fff);
}
bool bounds(std::vector<std::uint8_t>& ram, const FixedDataResource* path, SceneCommandState& s, std::string& error) {
    put_word(ram,0xd3f2,0x7fff); put_word(ram,0xd3f6,0x7fff); put_word(ram,0xd3f4,0x8000); put_word(ram,0xd3f8,0x8000);
    s.d0 = longword(ram,0xd3bc); s.d1 = longword(ram,0xd3c0);
    if (!resolve_scene_motion_time(ram,path,s,error)) return false;
    s.d7 = swap(s.d7); const std::uint16_t saved = low(s.d7);
    set_word(s.d6,word(ram,0xd418));
    if (low(s.d6) >= word(ram,0xd3ee)) set_word(s.d6,word(ram,0xd3ee));
    if (low(s.d7) < low(s.d6)) set_word(s.d7,s.d6);
    if (!extend_bounds(ram,path,s,error)) return false;
    set_word(s.d7,saved);
    if (low(s.d7) >= word(ram,0xd3f0)) set_word(s.d7,word(ram,0xd3f0));
    if (!extend_bounds(ram,path,s,error)) return false;
    set_word(s.d0,word(ram,0xd3a2)); put_word(ram,0xd3f2,static_cast<std::uint16_t>(word(ram,0xd3f2)+s.d0));
    set_word(s.d0,s.d0+0x140); add_saturating_word(s.d0,word(ram,0xd3f4)); put_word(ram,0xd3f4,low(s.d0));
    set_word(s.d1,word(ram,0xd3a6)); put_word(ram,0xd3f6,static_cast<std::uint16_t>(word(ram,0xd3f6)+s.d1));
    set_word(s.d1,s.d1+0x100); add_saturating_word(s.d1,word(ram,0xd3f8)); put_word(ram,0xd3f8,low(s.d1)); return true;
}
}
bool step_scene_motion_bounds(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const FixedDataResource* path, SceneCommandState& state, std::string& error) {
    if (ram.size() != 65536 || (entry != 0x198ee && entry != 0x19978 && entry != 0x19d98 && entry != 0x19d08)) {
        error = "scene motion bounds requires64KiB RAM and entry198ee/19978/19d98/19d08"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneCommandState next = state; bool success = false;
        if (entry == 0x198ee) success = span_motion(candidate,path,next,error);
        else if (entry == 0x19978) success = clamp_motion(candidate,path,next,error);
        else if (entry == 0x19d98) success = extend_bounds(candidate,path,next,error);
        else success = bounds(candidate,path,next,error);
        if (!success) return false;
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene motion bounds transaction"; return false; }
}
}
