#include "ms5/scene_placement_execution.h"
#include "ms5/scene_motion.h"
#include "ms5/scene_node.h"
#include "ms5/object_allocation.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void word(std::uint32_t& value, std::uint32_t input) { value = (value & 0xffff0000U) | low(input); }
std::uint32_t swap(std::uint32_t value) { return (value << 16) | (value >> 16); }
std::int32_t signed_word(std::uint32_t value) { return low(value) < 0x8000 ? low(value) : static_cast<std::int32_t>(low(value))-65536; }
bool fixed(const FixedDataResource& w) {
    return !(w.source_cpu_address & 1U) && w.source_cpu_address < 0x100000 &&
        w.source_rom_offset == w.source_cpu_address && !w.data.empty() && w.data.size() <= 0x100000-w.source_cpu_address;
}
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int size, std::uint32_t& value, std::string& error) {
    if ((address & 1U) || address > 0x1000000U-size) { error = "unaligned or overflowing scene placement read"; return false; }
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
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or cross-window scene placement read"; return false; }
    }
    value = 0;
    for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at+i];
    return true;
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value, std::string& error) {
    if ((address & 1U) || address < 0x100000 || address > 0x110000-size) { error = "scene placement write requires aligned complete RAM span"; return false; }
    for (unsigned int i = 0; i < size; ++i) ram[address-0x100000+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
    return true;
}
bool time(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, SceneCommandState& s, std::string& error) {
    std::uint32_t cursor = 0; if (!read(ram,windows,0x10d3b4,4,cursor,error)) return false;
    const FixedDataResource* path = NULL;
    if (cursor != 0) {
        unsigned int matches = 0;
        for (std::size_t i = 0; i < windows.size(); ++i) {
            const FixedDataResource& w = windows[i]; if (!fixed(w)) continue;
            if (cursor >= w.source_cpu_address && static_cast<std::uint64_t>(cursor) < static_cast<std::uint64_t>(w.source_cpu_address)+w.data.size()) { ++matches; path = &w; }
        }
        if (matches != 1) { error = "scene placement motion requires unique fixed cursor window (RAM motion unsupported)"; return false; }
    }
    return resolve_scene_motion_time(ram,path,s,error);
}
bool position(std::vector<std::uint8_t>& ram, SceneCommandState& s, std::string& error) {
    SceneNodeState node;
    node.d0 = s.d0; node.d1 = s.d1; node.d2 = s.d2; node.d3 = s.d3;
    node.d4 = s.d4; node.d5 = s.d5; node.d6 = s.d6; node.d7 = s.d7;
    node.a0 = s.a0; node.a1 = s.a1; node.a2 = s.a2; node.a4 = s.a4;
    if (!step_scene_node(ram,0x43e08,node,error)) return false;
    s.d0 = node.d0; s.d1 = node.d1; s.d2 = node.d2; s.d3 = node.d3;
    s.d4 = node.d4; s.d5 = node.d5; s.d6 = node.d6; s.d7 = node.d7;
    s.a0 = node.a0; s.a1 = node.a1; s.a2 = node.a2; s.a4 = node.a4;
    return true;
}
bool record(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneCommandState& s, std::uint32_t parent, std::string& error) {
    const std::uint32_t source = s.a0; std::uint32_t value = 0;
    s.d7 = 0;
    if (!read(ram,windows,source,2,value,error)) return false; word(s.d7,value);
    if (!read(ram,windows,source+4,2,value,error)) return false; word(s.d0,value);
    if (!read(ram,windows,source+6,2,value,error)) return false; word(s.d1,value);
    s.d0 = swap(s.d0); s.d1 = swap(s.d1);
    if (!time(ram,windows,s,error)) return false;
    s.d0 = swap(s.d0); s.d1 = swap(s.d1); s.d7 = swap(s.d7);
    if (!read(ram,windows,0x10d418,2,value,error)) return false;
    bool skip = false;
    if (low(s.d7) < value) {
        s.d2 = 0; s.d3 = 0;
        if (!read(ram,windows,source+8,4,s.a1,error)) return false;
        if (s.a1 != 0) {
            if (!read(ram,windows,s.a1,4,s.d2,error)) return false; s.a1 += 4;
            if (!read(ram,windows,s.a1,4,s.d3,error)) return false; s.a1 += 4;
        }
        word(s.d2,s.d2+s.d1);
        if (!read(ram,windows,0x10d3a6,2,value,error)) return false; word(s.d2,s.d2-value);
        if (!read(ram,windows,0x10d3f8,2,value,error)) return false; skip = signed_word(s.d2) > signed_word(value);
        if (!skip) {
            word(s.d2,s.d2+s.d3);
            if (!read(ram,windows,0x10d3f6,2,value,error)) return false; skip = signed_word(s.d2) < signed_word(value);
        }
        if (!skip) {
            s.d2 = swap(s.d2); s.d3 = swap(s.d3); word(s.d2,s.d2+s.d0);
            if (!read(ram,windows,0x10d3a6,2,value,error)) return false; word(s.d2,s.d2-value);
            if (!read(ram,windows,0x10d3f4,2,value,error)) return false; skip = signed_word(s.d2) > signed_word(value);
        }
        if (!skip) {
            word(s.d2,s.d2+s.d3);
            if (!read(ram,windows,0x10d3f2,2,value,error)) return false; skip = signed_word(s.d2) < signed_word(value);
        }
    }
    if (!skip) {
        const std::uint16_t saved0 = low(s.d0), saved1 = low(s.d1);
        if (!read(ram,windows,source+12,4,s.a0,error)) return false; word(s.d0,0);
        AllocationState allocation; allocation.d0 = s.d0; allocation.a0 = s.a0; allocation.a1 = s.a1; allocation.a6 = parent;
        if (!allocate_object(ram,allocation,error)) return false;
        s.d0 = allocation.d0; s.a0 = allocation.a0; s.a1 = allocation.a1;
        word(s.d1,saved1); word(s.d0,saved0); s.a0 += 0x2e; s.a1 = 0x10d38e;
        if (!position(ram,s,error)) return false;
        s.a1 = s.a0+0x48; s.a0 = source;
    }
    if (!read(ram,windows,source+2,2,value,error)) return false; word(s.d0,value);
    if ((value & 1U) || value >= 0x8000) { error = "unsupported scene placement payload length (requires even WORD below8000)"; return false; }
    s.a0 = source+0x10;
    if (skip) s.a0 += static_cast<std::uint32_t>(signed_word(s.d0));
    else while (low(s.d0) != 0) {
        if (!read(ram,windows,s.a0,2,value,error)) return false; s.a0 += 2;
        if (!write(ram,s.a1,2,value,error)) return false; s.a1 += 2; word(s.d0,s.d0-2U);
    }
    return true;
}
}
bool execute_scene_placement(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneCommandState& state,
    std::uint32_t parent_a6, std::string& error) {
    if (ram.size() != 65536 || (entry != 0x1a414 && entry != 0x1a470)) { error = "scene placement requires64KiB RAM and entry1a414/1a470"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneCommandState next = state;
        if (entry == 0x1a470) { if (!record(candidate,windows,next,parent_a6,error)) return false; }
        else {
            if (!read(candidate,windows,0x10d40e,4,next.a0,error)) return false;
            if (next.a0 != 0) {
                unsigned int records = 0; std::uint32_t value = 0, phase = 0;
                for (;;) {
                    if (!read(candidate,windows,next.a0,2,value,error)) return false; word(next.d7,value);
                    if (value == 0xffff) break;
                    if (!read(candidate,windows,0x10d418,2,phase,error)) return false;
                    if (value > phase) break;
                    if (++records > 1048576U) { error = "scene placement temporary record budget exceeded"; return false; }
                    if (!record(candidate,windows,next,parent_a6,error) || !write(candidate,0x10d40e,4,next.a0,error)) return false;
                }
            }
        }
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene placement transaction"; return false; }
}
}
