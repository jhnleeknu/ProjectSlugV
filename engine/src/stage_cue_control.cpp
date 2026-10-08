#include "ms5/stage_cue_control.h"
#include "ms5/object_allocation.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void word(std::uint32_t& value, std::uint32_t input) { value = (value & 0xffff0000U) | low(input); }
bool fixed(const FixedDataResource& w) {
    return !(w.source_cpu_address & 1U) && w.source_cpu_address < 0x100000 &&
        w.source_rom_offset == w.source_cpu_address && !w.data.empty() && w.data.size() <= 0x100000-w.source_cpu_address;
}
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int size, std::uint32_t& value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address > 0x1000000U-size) { error = "unaligned or overflowing stage cue control read"; return false; }
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
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or partial stage cue control fixed read"; return false; }
    }
    value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at+i]; return true;
}
bool offset_read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int offset, unsigned int size, std::uint32_t& value, std::string& error) {
    if (address > 0xffffffffU-offset) { error = "stage cue control address addition overflows"; return false; }
    return read(ram,windows,address+offset,size,value,error);
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address < 0x100000 || address > 0x110000-size) { error = "stage cue control write requires aligned complete RAM span"; return false; }
    for (unsigned int i = 0; i < size; ++i) ram[address-0x100000+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1))); return true;
}
bool execute(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& s,
    std::uint32_t a6, bool& carry, std::string& error) {
    std::uint32_t value = 0;
    if (entry == 0xe89fa) {
        if (s.a[0] == 0) s.a[0] = 0xe89ec;
        return write(ram,0x10de2a,4,s.a[0],error);
    }
    if (entry == 0xe8a1c) {
        if (s.a[0] == 0) s.a[0] = 0xe89e4;
        return write(ram,0x10de26,4,s.a[0],error) &&
            write(ram,0x10de2e,1,255,error) && write(ram,0x10de2f,1,0,error);
    }
    if (entry == 0xe8ad0) {
        if (!read(ram,windows,0x10de2a,4,value,error)) return false; s.a[0] = value;
        if (s.a[0] == 0) return true;
        if (!read(ram,windows,0x10d418,2,value,error)) return false; word(s.d[0],value);
        for (;;) {
            if (!offset_read(ram,windows,s.a[0],12,2,value,error)) return false;
            if (low(s.d[0]) < value) return write(ram,0x10de2a,4,s.a[0],error);
            if (s.a[0] > 0xffffffffU-12U) { error = "stage cue progression address addition overflows"; return false; }
            s.a[0] += 12;
        }
    }
    if (entry == 0xe8af4) {
        if (!read(ram,windows,s.a[0],2,value,error)) return false; word(s.d[0],value);
        if (!offset_read(ram,windows,s.a[0],2,2,value,error)) return false; word(s.d[1],value);
        if (!offset_read(ram,windows,s.a[0],4,1,value,error)) return false;
        if (value & 2U) {
            if (!read(ram,windows,0x10d3bc,2,value,error)) return false; word(s.d[0],s.d[0]+value);
        }
        if (!offset_read(ram,windows,s.a[0],4,1,value,error)) return false;
        if (value & 1U) {
            if (!read(ram,windows,0x10d3c0,2,value,error)) return false; word(s.d[1],s.d[1]+value);
        }
        return true;
    }
    AllocationState allocation; allocation.d0 = s.d[0]; allocation.a0 = s.a[0];
    allocation.a1 = s.a[1]; allocation.a6 = s.a[1]; allocation.carry = carry;
    if (!allocate_object(ram,allocation,error)) return false;
    s.d[0] = allocation.d0; s.a[0] = allocation.a0; s.a[1] = allocation.a1; carry = allocation.carry;
    if (!offset_read(ram,windows,a6,0x6a,1,value,error)) return false;
    if (s.a[0] > 0xffffffffU-0x6aU) { error = "stage cue allocation destination addition overflows"; return false; }
    return write(ram,s.a[0]+0x6a,1,value,error);
}
}
bool step_stage_cue_control(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, bool& allocation_carry, std::string& error) {
    if (ram.size() != 65536 || (entry != 0xe89fa && entry != 0xe8a1c && entry != 0xe8ad0 && entry != 0xe8af4 && entry != 0x2986)) {
        error = "stage cue control requires64KiB RAM and entrye89fa/e8a1c/e8ad0/e8af4/2986"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state; bool carry = allocation_carry;
        if (!execute(candidate,entry,windows,next,parent_a6,carry,error)) return false;
        ram.swap(candidate); state = next; allocation_carry = carry; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage cue control transaction"; return false; }
}
}
