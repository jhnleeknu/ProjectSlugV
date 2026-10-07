#include "ms5/object_restart_execution.h"
#include "ms5/object_state.h"
#include "ms5/scene_node.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t v) { return static_cast<std::uint16_t>(v); }
void word(std::uint32_t& v, std::uint32_t w) { v = (v & 0xffff0000U) | low(w); }
std::uint32_t indexed(std::uint32_t base, std::uint32_t w) {
    return base + (low(w) < 0x8000 ? low(w) : (0xffff0000U | low(w)));
}
bool span(std::uint32_t address, unsigned int size, std::string& error) {
    if ((size > 1 && (address & 1U)) || address < 0x100000 || size > 65536 || address > 0x110000-size) {
        error = "object restart dereference requires aligned complete CPU RAM span"; return false;
    }
    return true;
}
bool read(const std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size,
    std::uint32_t& value, std::string& error) {
    if (!span(address,size,error)) return false;
    value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | ram[address-0x100000+i]; return true;
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size,
    std::uint32_t value, std::string& error) {
    if (!span(address,size,error)) return false;
    for (unsigned int i = 0; i < size; ++i) ram[address-0x100000+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
    return true;
}
bool release(std::vector<std::uint8_t>& ram, ObjectRestartState& s, std::string& error) {
    std::uint32_t value = 0; s.d[7] = 0;
    if (!read(ram,s.a[6]+0x1d,1,value,error)) return false; s.d[7] = value;
    const bool empty = low(s.d[7]) == 0; word(s.d[7],s.d[7]-1U);
    if (!empty) {
        s.a[1] = 0x104d92;
        for (;;) {
            s.d[0] = 0;
            if (!read(ram,indexed(s.a[6]+0x19,s.d[7]),1,value,error)) return false; s.d[0] = value;
            word(s.d[0],s.d[0] << 4); s.a[2] = indexed(s.a[1],s.d[0]);
            if (!read(ram,s.a[2]+8,2,value,error)) return false; word(s.d[1],value);
            if (low(s.d[1]) != 0 && low(s.d[1]) != 0xffff) {
                if (!write(ram,s.a[2]+8,2,s.d[1]-1U,error)) return false;
                if (low(s.d[1]) == 1) {
                    if (!read(ram,s.a[2],2,value,error)) return false; word(s.d[2],value);
                    if (!read(ram,s.a[2]+2,2,value,error)) return false; word(s.d[3],value);
                    if (!write(ram,indexed(s.a[1],s.d[3]),2,s.d[2],error)) return false;
                    if (!write(ram,indexed(s.a[1],s.d[2])+2,2,s.d[3],error)) return false;
                    word(s.d[2],0x1000);
                    if (!read(ram,indexed(s.a[1],s.d[2]),2,value,error)) return false; word(s.d[3],value);
                    if (!write(ram,s.a[2]+2,2,s.d[2],error) || !write(ram,s.a[2],2,s.d[3],error)) return false;
                    if (!write(ram,indexed(s.a[1],s.d[3])+2,2,s.d[0],error) || !write(ram,indexed(s.a[1],s.d[2]),2,s.d[0],error)) return false;
                    if (!write(ram,s.a[2]+0xa,2,0xffff,error) || !write(ram,s.a[2]+0xc,2,0xffff,error) || !write(ram,s.a[2]+0xf,1,2,error)) return false;
                }
            }
            const bool last = low(s.d[7]) == 0; word(s.d[7],s.d[7]-1U); if (last) break;
        }
    }
    return write(ram,s.a[6]+0x1d,1,0,error);
}
bool coordinate(std::vector<std::uint8_t>& ram, ObjectRestartState& s, std::string& error) {
    std::uint32_t value = 0; s.d[0] = 0;
    if (!read(ram,s.a[6]+0x6c,1,value,error)) return false; s.d[0] = value;
    if (value & 0x80U) return true;
    if (value >= 8) { error = "original object restart TRAP: coordinate index must be below eight or have bit7 set"; return false; }
    s.d[0] = low(s.d[0])*0x2cU; s.a[0] = indexed(0x10d4e6,s.d[0]);
    if (!write(ram,s.a[0]+0x26,2,0xffff,error) || !write(ram,s.a[0]+0x2a,2,2,error) || !write(ram,s.a[6]+0x6c,1,0xff,error)) return false;
    SceneNodeState n;
    n.d0 = s.d[0]; n.d1 = s.d[1]; n.d2 = s.d[2]; n.d3 = s.d[3];
    n.d4 = s.d[4]; n.d5 = s.d[5]; n.d6 = s.d[6]; n.d7 = s.d[7];
    n.a0 = s.a[0]; n.a1 = s.a[1]; n.a2 = s.a[2]; n.a4 = s.a[4];
    if (!step_scene_node(ram,0x43e38,n,error)) return false;
    s.d[0] = n.d0; s.d[1] = n.d1; s.d[2] = n.d2; s.d[3] = n.d3;
    s.d[4] = n.d4; s.d[5] = n.d5; s.d[6] = n.d6; s.d[7] = n.d7;
    s.a[0] = n.a0; s.a[1] = n.a1; s.a[2] = n.a2; s.a[4] = n.a4;
    return true;
}
bool reset(std::vector<std::uint8_t>& ram, ObjectRestartState& s, std::string& error) {
    if (!span(s.a[0],0xc4,error)) return false;
    if (!reset_object_fields(&ram[s.a[0]-0x100000],ram.size()-(s.a[0]-0x100000))) { error = "object reset requires c4-byte RAM span"; return false; }
    s.d[0] = 0; s.d[1] = 0xffffffff; return true;
}
bool cleanup(std::vector<std::uint8_t>& ram, ObjectRestartState& s, std::string& error) {
    if (!release(ram,s,error) || !coordinate(ram,s,error) || !write(ram,s.a[6],4,0x270e,error)) return false;
    std::uint32_t value = 0;
    if (!read(ram,s.a[6]+0x10,2,value,error)) return false;
    if (value == 0) { s.a[0] = s.a[6]; return reset(ram,s,error); }
    for (unsigned int iteration = 0; iteration < 65536U; ++iteration) {
        if (!read(ram,s.a[6]+8,4,s.a[0],error) || !read(ram,s.a[6]+0x10,2,value,error)) return false; word(s.d[0],value);
        if (!read(ram,s.a[0]+0x10,2,value,error)) return false;
        if (low(s.d[0]) < value) return true;
        s.a[0] = s.a[6]; if (!reset(ram,s,error)) return false;
        if (!read(ram,s.a[6]+4,4,s.a[0],error) || !read(ram,s.a[6]+8,4,s.a[1],error)) return false;
        if (!write(ram,s.a[1]+4,4,s.a[0],error) || !write(ram,s.a[0]+8,4,s.a[1],error)) return false;
        if (!read(ram,0x104c9c,4,value,error) || !write(ram,s.a[6]+8,4,value,error) || !write(ram,0x104c9c,4,s.a[6],error)) return false;
        if (!read(ram,0x104ca0,2,value,error) || !write(ram,0x104ca0,2,value+1U,error)) return false;
        s.a[6] = s.a[0];
        if (!read(ram,s.a[6],4,value,error)) return false; if (value != 0x270e) return true;
        if (!read(ram,s.a[6]+0x10,2,value,error)) return false; if (value == 0) return true;
    }
    error = "object restart linked cleanup budget exceeded"; return false;
}
}
bool restart_object_full(std::vector<std::uint8_t>& ram, ObjectRestartState& state,
    std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || !span(state.a[0],0xc4,error)) {
        if (ram.size() != 65536) error = "object restart requires exactly64KiB RAM";
        return false;
    }
    std::uint32_t type = 0; if (!read(ram,state.a[0]+0x10,2,type,error)) return false;
    if (type != 0) { error = "original object restart TRAP: initial object type is nonzero"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; ObjectRestartState next = state; std::vector<VideoPortWrite> output;
        const std::uint32_t object = next.a[0], callback = next.a[1], saved_a6 = next.a[6];
        next.a[6] = object; next.a[5] = 0x108000;
        VideoPortWrite watchdog; watchdog.size = 1; watchdog.address = 0x300001; watchdog.value = next.d[0] & 255U; output.push_back(watchdog);
        if (!cleanup(candidate,next,error)) return false;
        next.a[0] = object; if (!write(candidate,next.a[0],4,callback,error)) return false; next.a[6] = saved_a6;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate full object restart transaction"; return false; }
}
}
