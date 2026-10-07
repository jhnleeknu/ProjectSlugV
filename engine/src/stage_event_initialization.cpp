#include "ms5/stage_event_initialization.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t v) { return static_cast<std::uint16_t>(v); }
void word(std::uint32_t& v, std::uint32_t w) { v = (v & 0xffff0000U) | low(w); }
std::uint32_t indexed(std::uint32_t base, std::uint32_t w) {
    return base + (low(w) < 0x8000 ? low(w) : (0xffff0000U | low(w)));
}
bool fixed(const FixedDataResource& w) {
    return !(w.source_cpu_address & 1U) && w.source_cpu_address < 0x100000 &&
        w.source_rom_offset == w.source_cpu_address && !w.data.empty() && w.data.size() <= 0x100000-w.source_cpu_address;
}
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int size, std::uint32_t& value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address > 0x1000000U-size) { error = "unaligned or overflowing stage event read"; return false; }
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
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or partial stage event fixed read"; return false; }
    }
    value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at+i]; return true;
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address < 0x100000 || address > 0x110000-size) { error = "stage event write requires aligned complete RAM span"; return false; }
    for (unsigned int i = 0; i < size; ++i) ram[address-0x100000+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
    return true;
}
void port(std::vector<VideoPortWrite>& output, std::uint32_t address, std::uint32_t value) {
    VideoPortWrite w; w.size = 2; w.address = address; w.value = value; output.push_back(w);
}
bool initialize(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    ObjectRestartState& s, std::vector<VideoPortWrite>& output, std::string& error) {
    const std::uint32_t stream = s.a[0]; const std::uint16_t target = low(s.d[0]);
    s.a[0] = indexed(s.a[5],0x8bf4); s.a[1] = 0xe9150;
    if (!restart_object_full(ram,s,output,error)) return false;
    word(s.d[0],target); s.d[7] = stream;
    if (stream == 0) return write(ram,s.a[0]+0x76,4,0,error);
    s.a[1] = s.d[7]; std::uint32_t value = 0;
    if (!read(ram,windows,s.a[1],2,value,error)) return false; word(s.d[1],value); s.a[1] += 2;
    if (low(s.d[0]) != 0) {
        s.a[1] = indexed(s.a[1],s.d[1]); bool selected = false;
        for (unsigned int iteration = 0; iteration < 1048576U; ++iteration) {
            if (!read(ram,windows,s.a[1],1,value,error)) return false;
            s.d[1] = (s.d[1] & 0xffffff00U) | value;
            if (value == 0xff) { selected = true; break; }
            if (value != 0) { error = "original stage event initialization TRAP: record marker must be00 orff"; return false; }
            if (!read(ram,windows,s.a[1]+2,2,value,error)) return false;
            if (low(s.d[0]) <= value) { selected = true; break; }
            if (!read(ram,windows,s.a[1]+4,2,value,error)) return false;
            s.a[1] = indexed(s.a[1],value);
        }
        if (!selected) { error = "stage event initialization temporary record budget exceeded"; return false; }
    }
    s.d[7] = s.a[1];
    if (!write(ram,s.a[0]+0x76,4,s.d[7],error) || !write(ram,indexed(s.a[5],0x8010),2,0,error)) return false;
    port(output,0x2ffff2,0x1000); port(output,0x2ffff0,0); return true;
}
}
bool initialize_stage_events(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, ObjectRestartState& state,
    std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536) { error = "stage event initialization requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; ObjectRestartState next = state; std::vector<VideoPortWrite> output;
        if (!initialize(candidate,windows,next,output,error)) return false;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage event initialization transaction"; return false; }
}
}
