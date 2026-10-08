#include "ms5/stage_spatial_frame.h"
#include "ms5/scene_node.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void set_word(std::uint32_t& value, std::uint32_t word) { value = (value & 0xffff0000U) | static_cast<std::uint16_t>(word); }
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    unsigned int bank, std::uint32_t address, unsigned int size, std::uint32_t& result, std::string& error) {
    if ((size > 1 && (address & 1U)) || address > 0x1000000U - size) { error = "unaligned or overflowing stage spatial frame read"; return false; }
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
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or cross-window stage spatial frame read"; return false; }
    }
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at + i]; result = value; return true;
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address < 0x100000 || address > 0x110000 - size) { error = "stage spatial frame RAM write outside aligned span"; return false; }
    const std::size_t at = address - 0x100000;
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
    return true;
}
bool offset_read(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    std::uint32_t bank,std::uint32_t address,unsigned int offset,unsigned int size,std::uint32_t& value,std::string& error) {
    if (address > 0xffffffffU-offset) { error = "stage spatial frame address addition overflows"; return false; }
    return read(ram,windows,bank,address+offset,size,value,error);
}
std::int32_t signed_word(std::uint32_t value) {
    const std::uint32_t w = low(value); return w < 0x8000U ? static_cast<std::int32_t>(w) : static_cast<std::int32_t>(w)-65536;
}
void exchange(std::uint32_t& a,std::uint32_t& b) { const std::uint32_t temp = a; a = b; b = temp; }
bool bset(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,std::uint32_t bank,
    std::uint32_t address,std::uint32_t bit,std::string& error) {
    std::uint32_t value = 0;
    return read(ram,windows,bank,address,1,value,error) && write(ram,address,1,value|(1U << (bit&7U)),error);
}
bool node(std::vector<std::uint8_t>& ram,SceneMapTransferState& s,std::string& error) {
    SceneNodeState n;
    n.d0 = s.d[0]; n.d1 = s.d[1]; n.d2 = s.d[2]; n.d3 = s.d[3]; n.d4 = s.d[4]; n.d5 = s.d[5]; n.d6 = s.d[6]; n.d7 = s.d[7];
    n.a0 = s.a[0]; n.a1 = s.a[1]; n.a2 = s.a[2]; n.a4 = s.a[4];
    if (!step_scene_node(ram,0x43e38,n,error)) return false;
    s.d[0] = n.d0; s.d[1] = n.d1; s.d[2] = n.d2; s.d[3] = n.d3; s.d[4] = n.d4; s.d[5] = n.d5; s.d[6] = n.d6; s.d[7] = n.d7;
    s.a[0] = n.a0; s.a[1] = n.a1; s.a[2] = n.a2; s.a[4] = n.a4;
    return true;
}
bool region(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s,std::uint32_t bank,std::string& error) {
    std::uint32_t value = 0;
    if (!offset_read(ram,windows,bank,s.a[0],0x26,4,value,error)) return false; s.a[1] = value;
    const unsigned int fields[4] = {0x1c,0x20,0x14,0x18};
    for (unsigned int i = 0; i < 4; ++i) {
        if (!offset_read(ram,windows,bank,s.a[0],fields[i],2,value,error)) return false; set_word(s.d[i],value);
    }
    if (signed_word(s.d[0]) > signed_word(s.d[2])) exchange(s.d[0],s.d[2]);
    if (signed_word(s.d[1]) > signed_word(s.d[3])) exchange(s.d[1],s.d[3]);
    for (unsigned int i = 4; i < 8; ++i) {
        if (!read(ram,windows,bank,s.a[1],2,value,error)) return false; s.a[1] += 2;
        s.d[i] = (value&0x8000U) ? value|0xffff0000U : value;
    }
    set_word(s.d[7],s.d[7]+1U);
    for (unsigned int i = 4; i < 8; ++i) set_word(s.d[i],s.d[i]<<3);
    set_word(s.d[6],s.d[6]+s.d[4]); set_word(s.d[7],s.d[7]+s.d[5]);
    set_word(s.d[0],s.d[0]+s.d[4]); set_word(s.d[1],s.d[1]+s.d[5]); set_word(s.d[2],s.d[2]+s.d[6]); set_word(s.d[3],s.d[3]+s.d[7]);
    if (!read(ram,windows,bank,0x10d67c,2,value,error)) return false; set_word(s.d[7],value);
    s.d[6] = 0;
    if (!read(ram,windows,bank,s.a[1],1,value,error)) return false;
    s.d[6] = ((value<<2)|(value>>6))&255U; s.d[6] &= 3U;
    const bool borrow = low(s.d[6]) < 3U; set_word(s.d[6],s.d[6]-3U);
    if (borrow) {
        set_word(s.d[6],~s.d[6]); s.a[1] = 0x10d669;
        do {
            --s.a[1]; if (!bset(ram,windows,bank,s.a[1],s.d[7],error)) return false;
            set_word(s.d[6],s.d[6]-1U);
        } while (low(s.d[6]) != 0xffffU);
    }
    set_word(s.d[4],0xffa0); set_word(s.d[5],0x1ff);
    if (signed_word(s.d[0]) > 511) return true;
    bool less = signed_word(s.d[2]) < signed_word(s.d[4]); set_word(s.d[2],s.d[2]-s.d[4]);
    if (less) return true;
    less = signed_word(s.d[0]) < signed_word(s.d[4]); set_word(s.d[0],s.d[0]-s.d[4]);
    if (less) s.d[0] = 0;
    // Literal46fcc compares D1, despite the preceding X operations.
    if (signed_word(s.d[1]) > signed_word(s.d[5])) set_word(s.d[1],s.d[5]);
    set_word(s.d[4],0x80); set_word(s.d[5],0x1ff);
    if (signed_word(s.d[1]) > 511) return true;
    less = signed_word(s.d[3]) < signed_word(s.d[4]); set_word(s.d[3],s.d[3]-s.d[4]);
    if (less) return true;
    less = signed_word(s.d[1]) < signed_word(s.d[4]); set_word(s.d[1],s.d[1]-s.d[4]);
    if (less) s.d[1] = 0;
    if (signed_word(s.d[3]) > 511) set_word(s.d[3],s.d[5]);
    set_word(s.d[0],low(s.d[0])>>5); set_word(s.d[2],low(s.d[2])>>5); set_word(s.d[2],s.d[2]-s.d[0]);
    set_word(s.d[1],low(s.d[1])>>5); set_word(s.d[3],low(s.d[3])>>5); set_word(s.d[3],s.d[3]-s.d[1]);
    s.a[1] = 0x10d646+static_cast<std::uint32_t>(signed_word(s.d[0]));
    do {
        if (!bset(ram,windows,bank,s.a[1],s.d[7],error)) return false; ++s.a[1];
        set_word(s.d[2],s.d[2]-1U);
    } while (low(s.d[2]) != 0xffffU);
    s.a[1] = 0x10d656+static_cast<std::uint32_t>(signed_word(s.d[1]));
    do {
        if (!bset(ram,windows,bank,s.a[1],s.d[7],error)) return false; ++s.a[1];
        set_word(s.d[3],s.d[3]-1U);
    } while (low(s.d[3]) != 0xffffU);
    return true;
}
bool execute(std::vector<std::uint8_t>& ram,std::uint32_t entry,const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s,std::uint32_t bank,std::string& error) {
    if (entry == 0x46f52) return region(ram,windows,s,bank,error);
    s.a[0] = 0x10d646; s.d[0] = 0;
    for (unsigned int i = 0; i < 9; ++i) { if (!write(ram,s.a[0],4,0,error)) return false; s.a[0] += 4; }
    if (!write(ram,0x10d67c,2,7,error)) return false; s.a[0] = 0x10d61a;
    for (;;) {
        std::uint32_t value = 0;
        if (!offset_read(ram,windows,bank,s.a[0],0x2a,2,value,error)) return false; set_word(s.d[0],value);
        if (low(s.d[0]) != 0) {
            set_word(s.d[0],s.d[0]-1U);
            if (!write(ram,s.a[0]+0x2a,2,s.d[0],error) || !node(ram,s,error)) return false;
        }
        if (!offset_read(ram,windows,bank,s.a[0],0x26,2,value,error)) return false;
        if (!(value&0x8000U) && !region(ram,windows,s,bank,error)) return false;
        s.a[0] -= 0x2c;
        if (!read(ram,windows,bank,0x10d67c,2,value,error)) return false;
        if (!write(ram,0x10d67c,2,value-1U,error)) return false;
        if (value == 0) return true;
    }
}
}
bool step_stage_spatial_frame(std::vector<std::uint8_t>& ram,std::uint32_t entry,
    const std::vector<FixedDataResource>& windows,SceneMapTransferState& state,
    std::uint32_t bank,std::string& error) {
    if (ram.size() != 65536 || (bank != 2 && bank != 3) || (entry != 0x4701e && entry != 0x46f52)) {
        error = "stage spatial frame requires64KiB RAM, bank2/3 and entry4701e/46f52"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state;
        if (!execute(candidate,entry,windows,next,bank,error)) return false;
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage spatial frame transaction"; return false; }
}
}
