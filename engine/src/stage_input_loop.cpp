#include "ms5/stage_input_loop.h"
#include "ms5/player_record_capture.h"
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
    if ((size > 1 && (address & 1U)) || address > 0x1000000U-size) { error = "unaligned or overflowing stage input loop read"; return false; }
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
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or partial stage input loop fixed read"; return false; }
    }
    value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at+i]; return true;
}
bool offset_read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int offset, unsigned int size, std::uint32_t& value, std::string& error) {
    if (address > 0xffffffffU-offset) { error = "stage input loop address addition overflows"; return false; }
    return read(ram,windows,address+offset,size,value,error);
}
bool player(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::string& error) {
    const bool second = (s.d[0]&255U) != 0;
    s.a[0] = second ? 0x100da8 : 0x100cb8; s.a[4] = second ? 0x10dce6 : 0x10dcba;
    std::uint32_t marker = 0, active = 0, index = 0;
    if (!read(ram,windows,s.a[0],4,marker,error)) return false;
    if (marker != 0x270e && !read(ram,windows,s.a[4],2,active,error)) return false;
    FixedDataResource dummy; const FixedDataResource* lookup = &dummy;
    if (marker != 0x270e && active != 0) {
        if (!offset_read(ram,windows,s.a[4],0x27,1,index,error)) return false;
        if (index != 0) {
            unsigned int matches = 0;
            for (std::size_t i = 0; i < windows.size(); ++i) {
                const FixedDataResource& w = windows[i];
                if (!fixed(w)) continue;
                const std::uint64_t end = static_cast<std::uint64_t>(w.source_cpu_address)+w.data.size();
                if (w.source_cpu_address < 0x4df60 && end > 0x4cf64) {
                    ++matches;
                    if (w.source_cpu_address == 0x4cf64 && w.data.size() == 4092) lookup = &w;
                }
            }
            if (matches != 1 || lookup == &dummy) { error = "stage input loop requires unique exact4cf64/4092-byte lookup"; return false; }
        }
    }
    PlayerRecordState p; p.d0 = s.d[0]; p.d1 = s.d[1]; p.d2 = s.d[2]; p.d3 = s.d[3];
    p.d4 = s.d[4]; p.d5 = s.d[5]; p.d6 = s.d[6];
    if (!read_player_record(ram,*lookup,p,error)) return false;
    s.d[0] = p.d0; s.d[1] = p.d1; s.d[2] = p.d2; s.d[3] = p.d3;
    s.d[4] = p.d4; s.d[5] = p.d5; s.d[6] = p.d6;
    if (marker != 0x270e && active != 0) s.a[4] = 0x4cf64+index*16U;
    return true;
}
bool crossing(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::uint32_t a6, std::string& error) {
    std::uint32_t value = 0; s.d[7] = 0;
    if (!offset_read(ram,windows,s.a[0],0x42,2,value,error)) return false; word(s.d[1],value);
    if (!read(ram,windows,0x10d3a2,2,value,error)) return false; word(s.d[1],s.d[1]-value);
    if (!offset_read(ram,windows,s.a[0],0xae,2,value,error)) return false; word(s.d[1],s.d[1]-value);
    bool reached = low(s.d[1]) == 0;
    if (!reached) {
        word(s.d[7],s.d[1]&0x8000U ? 8 : 4);
        if (!offset_read(ram,windows,s.a[0],0x4a,2,value,error)) return false; word(s.d[2],value);
        if (!read(ram,windows,0x10d3a2,2,value,error)) return false; word(s.d[2],s.d[2]-value);
        if (!offset_read(ram,windows,s.a[0],0xae,2,value,error)) return false; word(s.d[2],s.d[2]-value);
        word(s.d[1],s.d[1]^s.d[2]); reached = (s.d[1]&0x8000U) != 0;
    }
    if (!reached) return true;
    if (!offset_read(ram,windows,s.a[0],0x78,2,value,error)) return false; word(s.d[0],value);
    if (!player(ram,windows,s,error)) return false;
    if ((s.d[0]&255U) == 0) return true;
    if (!offset_read(ram,windows,s.a[0],0x78,2,value,error)) return false; word(s.d[0],value);
    return step_stage_input(ram,0x49c32,windows,s,error) &&
        step_stage_input_callback(ram,0x49f66,windows,s,a6,error);
}
bool execute(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& s, std::uint32_t a6, std::string& error) {
    if (entry == 0x4d7a6) return player(ram,windows,s,error);
    if (entry == 0x1da60) return crossing(ram,windows,s,a6,error);
    std::uint32_t value = 0;
    if (entry == 0x47642) {
        ram[0xd68e] = 0;
        for (unsigned int i = 0; i < 2; ++i) {
            s.a[0] = i == 0 ? 0x100cb8 : 0x100da8; s.d[0] = i;
            if (!read(ram,windows,s.a[0],4,value,error)) return false;
            if (value == 0x270e) continue;
            if (!offset_read(ram,windows,s.a[0],0x61,1,value,error)) return false;
            if (!(value&0x80U)) ram[0xd68e] |= static_cast<std::uint8_t>(1U << i);
        }
        return true;
    }
    for (unsigned int i = 0; i < 2; ++i) {
        s.d[7] = 0; s.d[6] = 0;
        if (!read(ram,windows,i == 0 ? 0x10d734 : 0x10d738,4,value,error)) return false;
        s.a[1] = value;
        if (s.a[1] != 0) {
            s.a[0] = i == 0 ? 0x100cb8 : 0x100da8;
            if (!read(ram,windows,s.a[0],4,value,error)) return false;
            if (value != 0x270e) {
                const std::uint32_t callback = s.a[1];
                if (callback == 0x1da60) {
                    if (!crossing(ram,windows,s,a6,error)) return false;
                } else if (!step_stage_input_callback(ram,callback,windows,s,a6,error)) return false;
                s.a[1] = i == 0 ? 0x10d726 : 0x10d72c;
                if (!step_stage_input(ram,0x49afe,windows,s,error)) return false;
            }
        } else {
            if (!read(ram,windows,i == 0 ? 0x104caa : 0x104cb0,1,value,error)) return false; byte(s.d[0],value);
            if (!read(ram,windows,i == 0 ? 0x104cab : 0x104cb1,1,value,error)) return false; byte(s.d[1],value);
            s.a[4] = i == 0 ? 0x10f01c : 0x10f020;
            if (!read(ram,windows,0x100012,1,value,error)) return false;
            if (value != 2) s.a[4] = 0x49ab0;
            if (!step_stage_input(ram,0x49ab4,windows,s,error)) return false;
        }
        s.a[1] = i == 0 ? 0x10d726 : 0x10d72c;
        if (!step_stage_input(ram,0x49bb4,windows,s,error)) return false;
    }
    return true;
}
}
bool step_stage_input_loop(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, std::string& error) {
    if (ram.size() != 65536 || (entry != 0x4d7a6 && entry != 0x1da60 && entry != 0x49b0c && entry != 0x47642)) {
        error = "stage input loop requires64KiB RAM and entry4d7a6/1da60/49b0c/47642"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state;
        if (!execute(candidate,entry,windows,next,parent_a6,error)) return false;
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage input loop transaction"; return false; }
}
}
