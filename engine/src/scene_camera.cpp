#include "ms5/scene_camera.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& b, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(b[at]) << 8) | b[at+1]);
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at) {
    return (static_cast<std::uint32_t>(word(b,at)) << 16) | word(b,at+2);
}
void put_word(std::vector<std::uint8_t>& b, std::size_t at, std::uint32_t value) {
    b[at] = static_cast<std::uint8_t>(value >> 8); b[at+1] = static_cast<std::uint8_t>(value);
}
void put(std::vector<std::uint8_t>& b, std::size_t at, std::uint32_t value) {
    put_word(b,at,value >> 16); put_word(b,at+2,value);
}
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void set_word(std::uint32_t& value, std::uint32_t input) { value = (value & 0xffff0000U) | low(input); }
std::int32_t signed_word(std::uint32_t value) { return low(value) < 0x8000 ? low(value) : static_cast<std::int32_t>(low(value))-65536; }
bool signed_less(std::uint32_t left, std::uint32_t right) { return (left ^ 0x80000000U) < (right ^ 0x80000000U); }
std::uint32_t asr(std::uint32_t value, unsigned int shift) {
    return (value >> shift) | ((value & 0x80000000U) ? (0xffffffffU << (32-shift)) : 0U);
}
void axis(std::vector<std::uint8_t>& ram, SceneCommandState& s, bool y) {
    const std::size_t minimum = y ? 0xd3d0 : 0xd3ce, maximum = y ? 0xd3d4 : 0xd3d2;
    const std::size_t center = y ? 0xd3d8 : 0xd3d6, margin = y ? 0xd3dc : 0xd3da;
    const std::size_t speed = y ? 0xd3ea : 0xd3e6, previous = y ? 0xd3e2 : 0xd3de;
    set_word(s.d0,word(ram,minimum)); set_word(s.d1,word(ram,maximum)); s.d7 = 0;
    set_word(s.d7,s.d0); set_word(s.d7,s.d7+s.d1);
    set_word(s.d7,(low(s.d7) >> 1) | ((s.d7 & 0x8000U) ? 0x8000U : 0U)); set_word(s.d7,s.d7-word(ram,center));
    set_word(s.d6,s.d7); set_word(s.d5,word(ram,margin)); set_word(s.d6,s.d6+s.d5);
    if (!(s.d6 & 0x8000U)) s.d6 = 0;
    set_word(s.d7,s.d7-s.d5); if (s.d7 & 0x8000U) s.d7 = 0;
    set_word(s.d7,s.d7+s.d6);
    set_word(s.d0,s.d0-(y ? 0x18U : 0x2cU)); if (s.d0 & 0x8000U) s.d0 = 0;
    if (signed_word(s.d7) > signed_word(s.d0)) set_word(s.d7,s.d0);
    set_word(s.d1,s.d1-(y ? 0xb8U : 0x114U)); if (!(s.d1 & 0x8000U)) s.d1 = 0;
    if (signed_word(s.d7) < signed_word(s.d1)) set_word(s.d7,s.d1);
    s.d7 = (s.d7 << 16) | (s.d7 >> 16);
    if (!(s.d7 & 0x80000000U)) s.d7 += 7;
    s.d7 = asr(s.d7,3); s.d0 = get(ram,speed);
    if (signed_less(s.d0,s.d7)) s.d7 = s.d0;
    const std::uint32_t left = s.d0, right = s.d7; s.d0 += s.d7;
    const bool overflow = ((~(left ^ right) & (left ^ s.d0)) & 0x80000000U) != 0;
    const bool negative = (s.d0 & 0x80000000U) != 0;
    if (negative != overflow) s.d7 -= s.d0;
    if (y) put(ram,previous,s.d7);
    s.d7 -= get(ram,previous); if (!(s.d7 & 0x80000000U)) s.d7 += 1;
    s.d7 = asr(s.d7,1); s.d7 += get(ram,previous);
    if (!y) put(ram,previous,s.d7);
}
void clear_bounds(std::vector<std::uint8_t>& ram) {
    put_word(ram,0xd3ce,0x7fff); put_word(ram,0xd3d2,0x8000); put_word(ram,0xd3d0,0x7fff); put_word(ram,0xd3d4,0x8000);
}
bool progress(std::vector<std::uint8_t>& ram, const FixedDataResource* path, SceneCommandState& s, std::string& error) {
    set_word(s.d4,word(ram,0xd3bc)); set_word(s.d5,word(ram,0xd3c0));
    set_word(s.d4,s.d4+word(ram,0xd3a2)); set_word(s.d5,s.d5+word(ram,0xd3a6));
    put_word(ram,0xd3ce,word(ram,0xd3ce)-s.d4); put_word(ram,0xd3d0,word(ram,0xd3d0)-s.d5);
    put_word(ram,0xd3d2,word(ram,0xd3d2)-s.d4); put_word(ram,0xd3d4,word(ram,0xd3d4)-s.d5);
    bool forward = true;
    if (word(ram,0xd3fa) != 0) {
        s.d0 = get(ram,0xd3bc); s.d1 = get(ram,0xd3c0);
        if (!resolve_scene_motion_time(ram,path,s,error)) return false;
        s.d6 = s.d7; s.d7 = static_cast<std::uint32_t>(word(ram,0xd3fa)) << 8; s.d7 += s.d6;
    } else {
        if (ram[0xd3cc] & 1U) axis(ram,s,false); else { s.d7 = get(ram,0xd3fc); put(ram,0xd3de,s.d7); }
        s.d7 += get(ram,0xd3bc); put(ram,0xd3c4,s.d7);
        if (ram[0xd3cc] & 2U) axis(ram,s,true); else { s.d7 = get(ram,0xd400); put(ram,0xd3e2,s.d7); }
        s.d7 += get(ram,0xd3c0); put(ram,0xd3c8,s.d7);
        bool carry = false; if (!step_scene_motion_pair(ram,0x19832,path,s,carry,error)) return false;
        forward = s.d7 >= s.d6;
    }
    s.d5 = static_cast<std::uint32_t>(word(ram,forward ? 0xd3ee : 0xd3f0)) << 16;
    if (forward && s.d7 >= s.d5) { if (s.d6 >= s.d5) s.d5 = s.d6; s.d7 = s.d5; }
    if (!forward && s.d7 < s.d5) { if (s.d6 < s.d5) s.d5 = s.d6; s.d7 = s.d5; }
    if (!step_scene_motion_bounds(ram,0x19978,path,s,error)) return false;
    bool accepted = true;
    if (word(ram,0xd3fa) == 0) {
        if (ram[0xd3cc] & 1U) {
            set_word(s.d1,word(ram,0xd3c4)); set_word(s.d1,s.d1-word(ram,0xd3bc));
            if (low(s.d1) != 0) {
                if (!(s.d1 & 0x8000U)) { set_word(s.d0,word(ram,0xd3ce)); set_word(s.d0,s.d0-0x2cU); accepted = !(s.d0 & 0x8000U); }
                else { set_word(s.d0,word(ram,0xd3d2)); set_word(s.d0,s.d0-0x114U); set_word(s.d0,s.d0+s.d1); accepted = (s.d0 & 0x8000U) != 0; }
            }
        }
        if (accepted && (ram[0xd3cc] & 2U)) {
            set_word(s.d1,word(ram,0xd3c8)); set_word(s.d1,s.d1-word(ram,0xd3c0));
            if (low(s.d1) != 0) {
                if (!(s.d1 & 0x8000U)) { set_word(s.d0,word(ram,0xd3d0)); set_word(s.d0,s.d0-0x18U); accepted = !(s.d0 & 0x8000U); }
                else { set_word(s.d0,word(ram,0xd3d4)); set_word(s.d0,s.d0-0xb8U); accepted = (s.d0 & 0x8000U) != 0; }
            }
        }
    }
    if (accepted) { put(ram,0xd3bc,get(ram,0xd3c4)); put(ram,0xd3c0,get(ram,0xd3c8)); }
    else { put(ram,0xd3de,0); put(ram,0xd3e2,0); }
    clear_bounds(ram); return true;
}
}
bool step_scene_camera(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const FixedDataResource* path, SceneCommandState& state, std::string& error) {
    if (ram.size() != 65536 || (entry != 0x19a40 && entry != 0x19ac8 && entry != 0x19b96)) {
        error = "scene camera requires64KiB RAM and entry19a40/19ac8/19b96"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneCommandState next = state;
        if (entry == 0x19b96) { if (!progress(candidate,path,next,error)) return false; }
        else axis(candidate,next,entry == 0x19ac8);
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene camera transaction"; return false; }
}
}
