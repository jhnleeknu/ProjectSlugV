#include "ms5/stage_region_frame.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void set_word(std::uint32_t& value, std::uint32_t word) { value = (value & 0xffff0000U) | static_cast<std::uint16_t>(word); }
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    unsigned int bank, std::uint32_t address, unsigned int size, std::uint32_t& result, std::string& error) {
    if ((size > 1 && (address & 1U)) || address > 0x1000000U - size) { error = "unaligned or overflowing stage region frame read"; return false; }
    const std::vector<std::uint8_t>* bytes = NULL; std::size_t at = 0;
    if (address >= 0x100000 && address + size <= 0x110000) { bytes = &ram; at = address - 0x100000; }
    else {
        unsigned int matches = 0;
        for (std::size_t i = 0; i < windows.size(); ++i) {
            const FixedDataResource& window = windows[i]; const std::uint32_t start = window.source_cpu_address;
            const bool fixed = (start & 1U) == 0 && start < 0x100000 && window.source_rom_offset == start && window.data.size() <= 0x100000 - start;
            const bool banked = (start & 1U) == 0 && start >= 0x200000 && start < 0x2ffff0 && window.data.size() <= 0x2ffff0 - start &&
                window.source_rom_offset == start + (bank == 3 ? 0x100000U : 0U);
            if (!(fixed || banked) || window.data.empty()) continue;
            const std::uint64_t end = static_cast<std::uint64_t>(start) + window.data.size();
            if (address < end && static_cast<std::uint64_t>(address) + size > start) {
                ++matches;
                if (address >= start && static_cast<std::uint64_t>(address) + size <= end) { bytes = &window.data; at = address - start; }
            }
        }
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or cross-window stage region frame read"; return false; }
    }
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at + i]; result = value; return true;
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address < 0x100000 || address > 0x110000 - size) { error = "stage region frame RAM write outside aligned span"; return false; }
    const std::size_t at = address - 0x100000;
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
    return true;
}
bool offset_read(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    std::uint32_t bank,std::uint32_t address,unsigned int offset,unsigned int size,std::uint32_t& value,std::string& error) {
    if (address > 0xffffffffU-offset) { error = "stage region frame address addition overflows"; return false; }
    return read(ram,windows,bank,address+offset,size,value,error);
}
bool activity(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s,std::uint32_t bank,bool& carry,std::string& error) {
    s.a[0] = 0x100cb8; set_word(s.d[0],s.d[0]&1U);
    if (low(s.d[0]) != 0) s.a[0] = 0x100da8;
    std::uint32_t value = 0;
    if (!read(ram,windows,bank,0x10d68e,1,value,error)) return false;
    carry = (value&(1U << low(s.d[0]))) != 0; return true;
}
bool pointer(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s,std::uint32_t a6,std::uint32_t bank,std::string& error) {
    s.a[4] = (s.d[0]&255U) == 0 ? 0x10dcba : 0x10dce6; std::uint32_t value = 0;
    if (!read(ram,windows,bank,s.a[4],2,value,error)) return false;
    if (value == 0) { s.a[0] = 0; return true; }
    s.d[0] = a6;
    if (!offset_read(ram,windows,bank,s.a[4],6,2,value,error)) return false; set_word(s.d[0],value);
    if (low(s.d[0]) == 0) { s.a[0] = 0; return true; }
    s.a[0] = s.d[0];
    if (!offset_read(ram,windows,bank,s.a[4],8,4,value,error)) return false; s.a[1] = value;
    return true;
}
bool fallback(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s,std::uint32_t a6,std::uint32_t bank,std::string& error) {
    const std::uint16_t saved = low(s.d[0]);
    if (!pointer(ram,windows,s,a6,bank,error)) return false;
    set_word(s.d[0],saved);
    if (s.a[0] != 0) return true;
    s.a[0] = 0x100cb8; set_word(s.d[0],s.d[0]&1U);
    if (low(s.d[0]) != 0) s.a[0] = 0x100da8;
    std::uint32_t value = 0;
    if (!offset_read(ram,windows,bank,s.a[0],0x56,4,value,error)) return false; s.a[1] = value;
    return true;
}
bool alternating(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s,std::uint32_t bank,std::string& error) {
    std::uint32_t value = 0;
    if (!read(ram,windows,bank,0x10000e,2,value,error)) return false; set_word(s.d[0],value); set_word(s.d[0],s.d[0]&1U);
    s.a[1] = low(s.d[0]) == 0 ? 0x10dd5c : 0x10dd98; s.a[2] = s.a[1]+60U; s.d[0] = 0;
    while (s.a[1] != s.a[2]) {
        if (!write(ram,s.a[1],2,0,error)) return false; s.a[1] += 10;
    }
    return true;
}
bool publish(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s,std::uint32_t bank,std::uint32_t destination,std::string& error) {
    std::uint32_t value = 0;
    for (unsigned int i = 0; i < 4; ++i) {
        if (!offset_read(ram,windows,bank,s.a[1],i*2,2,value,error)) return false;
        s.d[i] = (value&0x8000U) ? value|0xffff0000U : value;
    }
    if (!offset_read(ram,windows,bank,s.a[0],0x42,2,value,error)) return false; set_word(s.d[0],s.d[0]+value);
    if (!offset_read(ram,windows,bank,s.a[0],0x46,2,value,error)) return false; set_word(s.d[1],s.d[1]+value);
    for (unsigned int i = 0; i < 4; ++i) if (!write(ram,destination+i*2,2,s.d[i],error)) return false;
    return true;
}
bool execute(std::vector<std::uint8_t>& ram,std::uint32_t entry,const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s,std::uint32_t a6,std::uint32_t bank,bool& carry,std::string& error) {
    if (entry == 0x49392) return activity(ram,windows,s,bank,carry,error);
    if (entry == 0x4d9d6) return pointer(ram,windows,s,a6,bank,error);
    if (entry == 0x1c028) return fallback(ram,windows,s,a6,bank,error);
    if (entry == 0xb481e) return alternating(ram,windows,s,bank,error);
    bool active = false;
    if (!write(ram,0x10dd48,2,0x8000,error)) return false; s.d[0] = 0;
    if (!activity(ram,windows,s,bank,active,error)) return false;
    if (active) {
        s.d[0] = 0;
        if (!fallback(ram,windows,s,a6,bank,error)) return false;
        if (s.a[1] != 0 && !publish(ram,windows,s,bank,0x10dd48,error)) return false;
    }
    if (!write(ram,0x10dd50,2,0x8000,error)) return false; s.d[0] = 1;
    if (!activity(ram,windows,s,bank,active,error)) return false;
    if (active) {
        s.d[0] = 1;
        if (!fallback(ram,windows,s,a6,bank,error)) return false;
        if (s.a[1] != 0 && !publish(ram,windows,s,bank,0x10dd50,error)) return false;
    }
    s.a[0] = 0x10dd58; std::uint32_t value = 0;
    for (unsigned int i = 0; i < 2; ++i) {
        if (!read(ram,windows,bank,s.a[0],1,value,error)) return false;
        if (value != 0 && !write(ram,s.a[0],1,value-1U,error)) return false;
        s.a[0] += 2;
    }
    return alternating(ram,windows,s,bank,error);
}
}
bool step_stage_region_frame(std::vector<std::uint8_t>& ram,std::uint32_t entry,
    const std::vector<FixedDataResource>& windows,SceneMapTransferState& state,
    std::uint32_t parent_a6,std::uint32_t bank,bool& activity_carry,std::string& error) {
    if (ram.size() != 65536 || (bank != 2 && bank != 3) || (entry != 0xb4a2a && entry != 0x49392 && entry != 0x1c028 && entry != 0x4d9d6 && entry != 0xb481e)) {
        error = "stage region frame requires64KiB RAM, bank2/3 and a supported entry"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state; bool carry = activity_carry;
        if (!execute(candidate,entry,windows,next,parent_a6,bank,carry,error)) return false;
        ram.swap(candidate); state = next; activity_carry = carry; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage region frame transaction"; return false; }
}
}
