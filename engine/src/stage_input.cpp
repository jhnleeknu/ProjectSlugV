#include "ms5/stage_input.h"
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
    if ((size > 1 && (address & 1U)) || address > 0x1000000U-size) { error = "unaligned or overflowing stage input read"; return false; }
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
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or partial stage input fixed read"; return false; }
    }
    value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at+i]; return true;
}
bool offset_read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int offset, unsigned int size, std::uint32_t& value, std::string& error) {
    if (address > 0xffffffffU-offset) { error = "stage input address addition overflows"; return false; }
    return read(ram,windows,address+offset,size,value,error);
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address < 0x100000 || address > 0x110000-size) { error = "stage input write requires aligned complete RAM span"; return false; }
    for (unsigned int i = 0; i < size; ++i) ram[address-0x100000+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1))); return true;
}
bool map(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, SceneMapTransferState& s, std::string& error) {
    s.d[7] = s.d[0] & 15U; byte(s.d[6],s.d[7]); s.d[2] = 4; std::uint32_t value = 0;
    do {
        if (!read(ram,windows,s.a[4],1,value,error)) return false; byte(s.d[5],value); s.a[4] += 1;
        byte(s.d[4],s.d[0]); byte(s.d[4],s.d[4] & s.d[5]);
        if ((s.d[4] & 255U) == (s.d[5] & 255U)) {
            s.d[7] |= 1U << (s.d[2] & 31U); byte(s.d[4],s.d[4] & s.d[1]);
            if (s.d[4] & 255U) s.d[6] |= 1U << (s.d[2] & 31U);
        }
        byte(s.d[2],s.d[2]+1U);
    } while ((s.d[2] & 255U) < 8);
    s.a[4] -= 4;
    if (!offset_read(ram,windows,s.a[4],2,1,value,error)) return false; byte(s.d[2],value);
    if (!offset_read(ram,windows,s.a[4],1,1,value,error)) return false; byte(s.d[2],s.d[2] & value);
    if ((s.d[2] & 255U) != 0 && (s.d[6] & 64U)) { s.d[7] &= ~32U; s.d[6] &= ~32U; }
    return true;
}
bool execute(std::vector<std::uint8_t>& ram, std::uint32_t entry, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::string& error) {
    if (entry == 0x49ab4) return map(ram,windows,s,error);
    std::uint32_t value = 0;
    if (entry == 0x49afe) {
        if (!offset_read(ram,windows,s.a[1],2,2,value,error)) return false; word(s.d[6],value);
        word(s.d[6],s.d[6] & 0xfff0U); word(s.d[6],s.d[6] ^ s.d[7]); word(s.d[6],s.d[6] & s.d[7]); return true;
    }
    if (entry == 0x49bb4) {
        if (!offset_read(ram,windows,s.a[1],4,2,value,error)) return false; word(s.d[0],value);
        if (!write(ram,s.a[1]+4,2,0xffff,error)) return false;
        word(s.d[7],s.d[7] & s.d[0]); word(s.d[6],s.d[6] & s.d[0]);
        return write(ram,s.a[1]+2,2,s.d[7],error) && write(ram,s.a[1],2,s.d[6],error);
    }
    if (entry == 0x49c32) s.a[0] = 0;
    else if (entry == 0x49c66) s.a[0] = 0x49e34;
    word(s.d[0],s.d[0] & 1U); word(s.d[0],s.d[0] << 2); s.a[1] = 0x10d734+low(s.d[0]);
    return write(ram,s.a[1],4,s.a[0],error);
}
}
bool step_stage_input(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state, std::string& error) {
    if (ram.size() != 65536 || (entry != 0x49ab4 && entry != 0x49afe && entry != 0x49bb4 && entry != 0x49c20 && entry != 0x49c32 && entry != 0x49c66)) {
        error = "stage input requires64KiB RAM and entry49ab4/49afe/49bb4/49c20/49c32/49c66"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state;
        if (!execute(candidate,entry,windows,next,error)) return false;
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage input transaction"; return false; }
}
}
