#include "ms5/stage_input_callback.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void word(std::uint32_t& value, std::uint32_t input) { value = (value & 0xffff0000U) | low(input); }
void byte(std::uint32_t& value, std::uint32_t input) { value = (value & 0xffffff00U) | (input & 255U); }
bool fixed(const FixedDataResource& w) {
    return !(w.source_cpu_address & 1U) && w.source_cpu_address < 0x100000 &&
        w.source_rom_offset == w.source_cpu_address && !w.data.empty() && w.data.size() <= 0x100000-w.source_cpu_address;
}
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int size, std::uint32_t& value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address > 0x1000000U-size) { error = "unaligned or overflowing stage input callback read"; return false; }
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
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or partial stage input callback fixed read"; return false; }
    }
    value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at+i]; return true;
}
bool offset_read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int offset, unsigned int size, std::uint32_t& value, std::string& error) {
    if (address > 0xffffffffU-offset) { error = "stage input callback address addition overflows"; return false; }
    return read(ram,windows,address+offset,size,value,error);
}
void swap(std::uint32_t& value) { value = (value << 16) | (value >> 16); }
bool negative(std::uint32_t value) { return (value & 0x8000U) != 0; }
void direction(SceneMapTransferState& s) {
    s.d[7] = 0;
    if (low(s.d[2]) != 0) s.d[7] = negative(s.d[2]) ? 8U : 4U;
}
bool supported(std::uint32_t entry) {
    const std::uint32_t entries[] = {0x49d88,0x49de6,0x49e34,0x49e38,0x49e9c,0x49eba,0x49ef0,0x49f2c,0x49f66,
        0x1bec0,0x1d5ac,0x1d5e2,0x1d61a,0x1d628,0x1d664,0x1d6c2,0x1d8cc,0xe73f2};
    for (unsigned int i = 0; i < 18; ++i) if (entry == entries[i]) return true;
    return false;
}
bool execute(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& w, SceneMapTransferState& s, std::uint32_t a6, std::string& error) {
    std::uint32_t value = 0;
    if (entry == 0x1d8cc) return true;
    if (entry == 0x49e34) { s.d[7] = 0; return true; }
    if (entry == 0xe73f2) {
        if (!read(ram,w,0x10de24,2,value,error)) return false;
        word(s.d[7],value); return true;
    }
    if (entry == 0x49f66) {
        s.d[0] = 0;
        if (s.a[0] == 0x100cb8 || s.a[0] == 0x100da8) {
            if (!read(ram,w,s.a[0] == 0x100cb8 ? 0x104caa : 0x104cb0,1,value,error)) return false;
            byte(s.d[0],value);
        }
        s.a[4] = 0x49ab0;
        return step_stage_input(ram,0x49ab4,w,s,error);
    }
    if (entry == 0x1d628) {
        if (!offset_read(ram,w,s.a[0],0x78,2,value,error)) return false;
        word(s.d[0],value);
        return step_stage_input(ram,0x49c32,w,s,error) && execute(ram,0x49f66,w,s,a6,error);
    }
    if (entry == 0x1d5ac) {
        if (!read(ram,w,0x10d683,1,value,error)) return false;
        if (value & 4U) {
            if (!offset_read(ram,w,s.a[0],0x78,2,value,error)) return false;
            word(s.d[0],value);
            if (!step_stage_input(ram,0x49c32,w,s,error)) return false;
        }
        s.d[7] = 0; return true;
    }
    if (entry == 0x1bec0 || entry == 0x1d5e2 || entry == 0x1d61a) {
        if (!offset_read(ram,w,s.a[0],0x15,1,value,error)) return false;
        if (entry == 0x1bec0) {
            if (value & 0x80U) {
                if (!offset_read(ram,w,s.a[0],0xa7,1,value,error)) return false;
                if (!(value & 0x80U)) { s.d[7] = 0; return true; }
            }
            if (!execute(ram,0x49f66,w,s,a6,error)) return false;
            word(s.d[7],s.d[7] & 15U); return true;
        }
        if (value & 0x80U) return execute(ram,0x1d628,w,s,a6,error);
        s.d[7] = 0;
        if (entry == 0x1d5e2) {
            if (!offset_read(ram,w,a6,0x3a,2,value,error)) return false;
            if (!negative(value)) word(s.d[7],8);
        }
        return true;
    }
    if (entry == 0x1d664 || entry == 0x1d6c2) {
        s.d[7] = 0;
        const bool y = entry == 0x1d6c2;
        if (!offset_read(ram,w,s.a[0],y ? 0x46 : 0x42,2,value,error)) return false;
        word(s.d[1],value);
        if (!read(ram,w,y ? 0x10d3a6 : 0x10d3a2,2,value,error)) return false;
        word(s.d[1],s.d[1]-value);
        if (!offset_read(ram,w,s.a[0],0xae,2,value,error)) return false;
        word(s.d[1],s.d[1]-value);
        if (low(s.d[1]) == 0) return execute(ram,0x1d628,w,s,a6,error);
        word(s.d[7],negative(s.d[1]) ? (y ? 1U : 8U) : (y ? 2U : 4U));
        if (!offset_read(ram,w,s.a[0],y ? 0x4e : 0x4a,2,value,error)) return false;
        word(s.d[2],value);
        if (!read(ram,w,y ? 0x10d3a6 : 0x10d3a2,2,value,error)) return false;
        word(s.d[2],s.d[2]-value);
        if (!offset_read(ram,w,s.a[0],0xae,2,value,error)) return false;
        word(s.d[2],s.d[2]-value); word(s.d[1],s.d[1]^s.d[2]);
        if (negative(s.d[1])) return execute(ram,0x1d628,w,s,a6,error);
        return true;
    }
    if (entry == 0x49e9c) {
        if (!execute(ram,0x49de6,w,s,a6,error)) return false;
        const std::uint32_t saved = s.d[0];
        word(s.d[0],s.d[7]); word(s.d[0],s.d[0]&12U);
        if (low(s.d[0]) == 0) s.d[7] = 32;
        s.d[0] = saved; return true;
    }
    if (entry == 0x49eba || entry == 0x49ef0) {
        byte(s.d[0],0);
        if (!read(ram,w,0x100cb8,4,value,error)) return false;
        if (s.a[0] != value) byte(s.d[0],1);
        const unsigned int bit = s.d[0]&7U;
        if (!read(ram,w,0x10d732,1,value,error)) return false;
        const bool set = (value & (1U << bit)) != 0;
        if (entry == 0x49eba) {
            if (!set) ram[0xd732] = static_cast<std::uint8_t>(value | (1U << bit));
            // The original post-call OR.W is discarded by restoring D0 LONG.
            return execute(ram,0x49de6,w,s,a6,error);
        }
        if (set) {
            if (!offset_read(ram,w,s.a[0],0x78,2,value,error)) return false;
            word(s.d[0],value); s.d[7] = 0; return true;
        }
        const std::uint32_t saved = s.d[0];
        if (!execute(ram,0x49de6,w,s,a6,error)) return false;
        s.d[1] = saved; word(s.d[2],s.d[7]); word(s.d[2],s.d[2]&12U);
        if (low(s.d[2]) == 0) ram[0xd732] |= static_cast<std::uint8_t>(1U << (s.d[1]&7U));
        return true;
    }
    if (entry == 0x49f2c) {
        s.d[7] = 0;
        if (!offset_read(ram,w,s.a[0],0x15,1,value,error)) return false;
        byte(s.d[1],value & 1U ? 255 : 0);
        if (!offset_read(ram,w,s.a[0],0x78,2,value,error)) return false;
        word(s.d[0],value);
        if (!read(ram,w,low(s.d[0]) == 0 ? 0x10d740 : 0x10d741,1,value,error)) return false;
        byte(s.d[2],value ? 255 : 0); byte(s.d[1],s.d[1]^s.d[2]);
        if (s.d[1]&255U) s.d[7] = s.d[2]&255U ? 4 : 8;
        return true;
    }
    // The three target callbacks deliberately retain their different read orders.
    if (entry == 0x49d88) {
        if (!offset_read(ram,w,s.a[0],0x42,4,value,error)) return false; s.d[2] = value;
        if (!offset_read(ram,w,s.a[0],0x4a,4,value,error)) return false; s.d[3] = value;
        if (!read(ram,w,0x10d3a2,4,value,error)) return false; s.d[2] -= value;
        if (!read(ram,w,0x10d3aa,4,value,error)) return false; s.d[3] -= value;
        swap(s.d[2]); swap(s.d[3]);
    } else s.d[7] = 0;
    if (entry != 0x49e38) {
        if (!offset_read(ram,w,s.a[0],0x78,2,value,error)) return false; word(s.d[0],value);
        if (!read(ram,w,low(s.d[0]) == 0 ? 0x10d73c : 0x10d73e,2,value,error)) return false; word(s.d[1],value);
    }
    if (entry == 0x49de6) {
        if (!offset_read(ram,w,s.a[0],0x42,4,value,error)) return false; s.d[2] = value;
        if (!read(ram,w,0x10d3a2,4,value,error)) return false; s.d[2] -= value;
        if (!offset_read(ram,w,s.a[0],0x4a,4,value,error)) return false; s.d[3] = value;
        if (!read(ram,w,0x10d3aa,4,value,error)) return false; s.d[3] -= value;
        swap(s.d[2]); swap(s.d[3]);
    }
    if (entry == 0x49e38) {
        if (!offset_read(ram,w,s.a[0],0x42,2,value,error)) return false; word(s.d[2],value);
        if (!offset_read(ram,w,s.a[0],0x4a,2,value,error)) return false; word(s.d[3],value);
        if (!read(ram,w,0x10d3a2,2,value,error)) return false; word(s.d[2],s.d[2]-value);
        if (!read(ram,w,0x10d3aa,2,value,error)) return false; word(s.d[3],s.d[3]-value);
        if (!offset_read(ram,w,s.a[0],0x78,2,value,error)) return false; word(s.d[0],value);
        if (!read(ram,w,low(s.d[0]) == 0 ? 0x10d73c : 0x10d73e,2,value,error)) return false; word(s.d[1],value);
    }
    word(s.d[2],s.d[2]-s.d[1]);
    bool reached = low(s.d[2]) == 0;
    if (entry == 0x49d88 || !reached) {
        word(s.d[3],s.d[3]-s.d[1]); word(s.d[3],s.d[3]^s.d[2]); reached = negative(s.d[3]);
    }
    if (entry == 0x49d88 && reached) {
        const std::uint16_t saved = low(s.d[2]); const std::uint32_t object = s.a[0];
        if (!step_stage_input(ram,0x49c32,w,s,error)) return false;
        s.a[0] = object; word(s.d[2],saved); word(s.d[2],0U-s.d[2]);
    } else if (entry == 0x49de6 && reached) return step_stage_input(ram,0x49c66,w,s,error);
    else if (entry == 0x49e38 && reached) {
        if (!offset_read(ram,w,s.a[0],0x15,1,value,error)) return false;
        if (value & 0x80U) { s.d[7] = 0; s.a[0] = 0x49f2c; return step_stage_input(ram,0x49c20,w,s,error); }
    }
    direction(s); return true;
}
}
bool step_stage_input_callback(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, std::string& error) {
    if (ram.size() != 65536 || !supported(entry)) { error = "stage input callback requires64KiB RAM and a supported entry"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state;
        if (!execute(candidate,entry,windows,next,parent_a6,error)) return false;
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage input callback transaction"; return false; }
}
}
