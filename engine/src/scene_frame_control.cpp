#include "ms5/scene_frame_control.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void word(std::uint32_t& value, std::uint32_t input) { value = (value & 0xffff0000U) | low(input); }
std::int32_t signed_word(std::uint32_t value) { return low(value) < 0x8000 ? low(value) : static_cast<std::int32_t>(low(value))-65536; }
std::uint32_t swap(std::uint32_t value) { return (value << 16) | (value >> 16); }
bool fixed(const FixedDataResource& w) {
    return !(w.source_cpu_address & 1U) && w.source_cpu_address < 0x100000 &&
        w.source_rom_offset == w.source_cpu_address && !w.data.empty() && w.data.size() <= 0x100000-w.source_cpu_address;
}
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int size, std::uint32_t& value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address > 0x1000000U-size) { error = "unaligned or overflowing scene frame control read"; return false; }
    const std::vector<std::uint8_t>* bytes = NULL; std::size_t at = 0;
    if (address >= 0x100000 && address+size <= 0x110000) { bytes = &ram; at = address-0x100000; }
    else {
        unsigned int matches = 0;
        for (std::size_t i = 0; i < windows.size(); ++i) {
            const FixedDataResource& w = windows[i]; if (!fixed(w)) continue;
            const std::uint64_t end = static_cast<std::uint64_t>(w.source_cpu_address)+w.data.size();
            if (address < end && static_cast<std::uint64_t>(address)+size > w.source_cpu_address) {
                ++matches;
                if (address >= w.source_cpu_address && static_cast<std::uint64_t>(address)+size <= end) { bytes = &w.data; at = address-w.source_cpu_address; }
            }
        }
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or partial scene frame control fixed read"; return false; }
    }
    value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at+i]; return true;
}
bool offset_read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int offset, unsigned int size, std::uint32_t& value, std::string& error) {
    if (address > 0xffffffffU-offset) { error = "scene frame control address addition overflows"; return false; }
    return read(ram,windows,address+offset,size,value,error);
}
void put(std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size, std::uint32_t value) {
    for (unsigned int i = 0; i < size; ++i) ram[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size) {
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | ram[at+i]; return value;
}
bool duration(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, SceneCommandState& s, std::string& error) {
    put(ram,0xd422,4,0); s.a1 = get(ram,0xd3b4,4);
    if (s.a1 == 0) word(s.d7,0x7fff);
    else {
        std::uint32_t value = 0; unsigned int records = 0;
        for (;;) {
            if (!offset_read(ram,windows,s.a1,2,2,value,error)) return false;
            if (value == 0xffff) break;
            if (++records > 1048576U || s.a1 > 0xffffffffU-10U) { error = "scene duration scan exceeds record/address bound"; return false; }
            s.a1 += 10;
        }
        if (!read(ram,windows,s.a1,2,value,error)) return false; word(s.d7,value); word(s.d7,s.d7-1U);
    }
    put(ram,0xd41e,2,s.d7); put(ram,0xd420,2,s.d7); put(ram,0xd43e,2,0); return true;
}
bool rectangle(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneCommandState& s, bool& carry, std::string& error) {
    std::uint32_t value = 0;
    if (!read(ram,windows,s.a0,4,value,error)) return false;
    if (value == 0x270e) { carry = true; return true; }
    if (!offset_read(ram,windows,s.a0,0x15,1,value,error)) return false;
    if (!(value & 0x80U)) { carry = false; return true; }
    if (!read(ram,windows,s.a1,4,s.d4,error) || !offset_read(ram,windows,s.a1,4,4,s.d5,error)) return false; s.d5 += s.d4;
    if (!offset_read(ram,windows,s.a0,0x42,2,value,error)) return false; word(s.d0,value);
    if (!offset_read(ram,windows,s.a0,0x46,2,value,error)) return false; word(s.d1,value);
    word(s.d0,s.d0-get(ram,0xd3a2,2)); word(s.d1,s.d1-get(ram,0xd3a6,2));
    carry = false;
    if (signed_word(s.d1) < signed_word(s.d4) || signed_word(s.d1) >= signed_word(s.d5)) return true;
    s.d4 = swap(s.d4); s.d5 = swap(s.d5);
    carry = signed_word(s.d0) >= signed_word(s.d4) && signed_word(s.d0) < signed_word(s.d5); return true;
}
bool objects(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneCommandState& s, bool& carry, std::string& error) {
    s.a0 = 0x100cb8; if (!rectangle(ram,windows,s,carry,error)) return false;
    if (!carry) return true;
    s.a0 = 0x100da8; return rectangle(ram,windows,s,carry,error);
}
bool condition(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneCommandState& s, bool& carry, std::string& error) {
    s.a1 = get(ram,0xd422,4); if (s.a1 == 0) { carry = true; return true; }
    std::uint32_t value = 0; if (!read(ram,windows,s.a1,2,value,error)) return false; word(s.d0,value); s.a1 += 2;
    if (value == 0) {
        if (!read(ram,windows,s.a1,2,value,error)) return false; s.a1 += 2; put(ram,0xd43e,2,value);
        word(s.d0,get(ram,0xd418,2)); carry = low(s.d0) >= get(ram,0xd41e,2);
    } else if (value == 4 || value == 8) {
        if (ram[0xd68e] == 0) { carry = false; return true; }
        if (!objects(ram,windows,s,carry,error)) return false;
        if (!carry && value == 8) { s.a1 += 8; if (!objects(ram,windows,s,carry,error)) return false; }
    } else { error = "unsupported scene condition selector (requires0/4/8)"; return false; }
    if (carry) { if (!duration(ram,windows,s,error)) return false; carry = true; }
    return true;
}
void settings(std::vector<std::uint8_t>& ram, SceneCommandState& s) {
    word(s.d0,get(ram,0xd41e,2)); word(s.d1,get(ram,0xd420,2)); word(s.d2,get(ram,0xd440,2));
    if (low(s.d0) >= low(s.d2)) word(s.d0,s.d2);
    word(s.d2,get(ram,0xd442,2)); if (low(s.d1) >= low(s.d2)) word(s.d1,s.d2);
    put(ram,0xd3ee,2,s.d0); put(ram,0xd3f0,2,s.d1);
    word(s.d0,get(ram,0xd444,2)); word(s.d1,get(ram,0xd448,2));
    if (low(s.d0) == 0x8000) { word(s.d0,get(ram,0xd426,2)); word(s.d1,get(ram,0xd42a,2)); }
    put(ram,0xd3d6,2,s.d0); put(ram,0xd3da,2,s.d1);
    word(s.d0,get(ram,0xd446,2)); word(s.d1,get(ram,0xd44a,2));
    if (low(s.d0) == 0x8000) { word(s.d0,get(ram,0xd428,2)); word(s.d1,get(ram,0xd42c,2)); }
    put(ram,0xd3d8,2,s.d0); put(ram,0xd3dc,2,s.d1);
    word(s.d0,get(ram,0xd43e,2)); if (low(s.d0) < get(ram,0xd44c,2)) word(s.d0,get(ram,0xd44c,2)); put(ram,0xd3fa,2,s.d0);
}
void shake(std::vector<std::uint8_t>& ram, SceneCommandState& s) {
    s.d0 = get(ram,0xd408,4); s.d1 = (s.d0 >> 4) | ((s.d0 & 0x80000000U) ? 0xf0000000U : 0U);
    s.d0 = (0U-s.d0)+s.d1; put(ram,0xd408,4,s.d0); s.d0 += 0x8000; s.d0 = swap(s.d0);
    if (signed_word(s.d0) > 8) s.d0 = 8; else if (signed_word(s.d0) < -8) s.d0 = 0xfffffff8;
    put(ram,0xd406,2,get(ram,0xd404,2)); put(ram,0xd404,2,s.d0);
}
}
bool step_scene_frame_control(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneCommandState& state,
    bool& carry, std::string& error) {
    if (ram.size() != 65536 || (entry != 0x1a2b4 && entry != 0x1a34c && entry != 0x1a29e && entry != 0x1a526 && entry != 0x1a3d6)) {
        error = "scene frame control requires64KiB RAM and entry1a2b4/1a34c/1a29e/1a526/1a3d6"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneCommandState next = state; bool result = false;
        if (entry == 0x1a2b4) { if (!condition(candidate,windows,next,result,error)) return false; }
        else if (entry == 0x1a34c) { if (!rectangle(candidate,windows,next,result,error)) return false; }
        else if (entry == 0x1a29e) { if (!duration(candidate,windows,next,error)) return false; }
        else if (entry == 0x1a526) settings(candidate,next);
        else shake(candidate,next);
        ram.swap(candidate); state = next; carry = result; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene frame control transaction"; return false; }
}
}
