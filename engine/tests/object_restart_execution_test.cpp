#include "ms5/object_restart_execution.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, unsigned int size, std::uint32_t v) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at, unsigned int size) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < size; ++i) v = (v << 8) | b[at+i]; return v;
}
ms5::ObjectRestartState initial() {
    ms5::ObjectRestartState s;
    for (unsigned int i = 0; i < 8; ++i) s.d[i] = 0x12340000+i;
    for (unsigned int i = 0; i < 7; ++i) s.a[i] = 0xabcd0000+i;
    s.a[0] = 0x102000; s.a[1] = 0xfedcba99; s.a[6] = 0x98765433; return s;
}
bool same(const ms5::ObjectRestartState& a, const ms5::ObjectRestartState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 7; ++i) if (a.a[i] != b.a[i]) return false;
    return true;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ram[0x206c] = 0xff;
    ms5::ObjectRestartState s = initial(); std::string error; std::vector<ms5::VideoPortWrite> ports;
    assert(ms5::restart_object_full(ram,s,ports,error));
    assert(get(ram,0x2000,4) == 0xfedcba99 && s.a[0] == 0x102000 && s.a[6] == 0x98765433 && s.a[5] == 0x108000);
    assert(s.d[0] == 0 && s.d[1] == 0xffffffff && s.d[7] == 0xffff && s.a[1] == 0xfedcba99);
    assert(ports.size() == 1 && ports[0].size == 1 && ports[0].address == 0x300001 && ports[0].value == 0);
    // Raw release accepts inconsistent list links and preserves D2/D3 high WORDs.
    ram.assign(65536,0); ram[0x206c] = 0xff; ram[0x201d] = 1; ram[0x2019] = 1;
    put(ram,0x4da2,2,0x20); put(ram,0x4da4,2,0x30); put(ram,0x4daa,2,1); put(ram,0x5d92,2,0x40);
    s = initial(); assert(ms5::restart_object_full(ram,s,ports,error));
    assert(s.d[2] == 0x12341000 && s.d[3] == 0x12340040 && s.d[7] == 0xffff && s.a[1] == 0x104d92 && s.a[2] == 0x104da2);
    assert(get(ram,0x4da2,2) == 0x40 && get(ram,0x4da4,2) == 0x1000 && get(ram,0x5d92,2) == 0x10 && get(ram,0x4dd4,2) == 0x10 && ram[0x4db1] == 2);
    // Sequential unlink aliases change the free head before its live reread.
    ram.assign(65536,0); ram[0x206c] = 0xff; ram[0x201d] = 1; ram[0x2019] = 1;
    put(ram,0x4da2,2,0x20); put(ram,0x4da4,2,0x1000); put(ram,0x4daa,2,1); put(ram,0x5d92,2,0x40);
    s = initial(); assert(ms5::restart_object_full(ram,s,ports,error)); assert(s.d[3] == 0x12340020 && get(ram,0x4da2,2) == 0x20 && get(ram,0x4db4,2) == 0x10);
    // A count above four is a raw loop, and unused zero-reference slots are accepted.
    ram.assign(65536,0); ram[0x206c] = 0xff; ram[0x201d] = 255; s = initial();
    assert(ms5::restart_object_full(ram,s,ports,error)); assert(s.d[7] == 0xffff);
    // Coordinate helper carries all twelve registers while preserving A3/A4/A6.
    ram.assign(65536,0); put(ram,0xd4e6,4,0x10000); put(ram,0xd4ea,4,0x20000); put(ram,0xd4fe,4,0x77778888);
    s = initial(); assert(ms5::restart_object_full(ram,s,ports,error));
    assert(get(ram,0xd4fa,4) == 0x10000 && get(ram,0xd4fe,4) == 0x20000 && s.d[3] == 0x77778888 && s.d[7] == 0);
    assert(s.a[1] == 0 && s.a[3] == 0xabcd0003 && s.a[4] == 0xabcd0004 && s.a[6] == 0x98765433);
    // Palette/object alias changes the initially static type and takes linked cleanup.
    ram.assign(65536,0); s = initial(); s.a[0] = 0x104d92;
    put(ram,0x4d96,4,0x103000); put(ram,0x4d9a,4,0x103100); put(ram,0x4daa,2,1); ram[0x4daf] = 1; ram[0x4dfe] = 0xff;
    put(ram,0x5d92,2,0x20); put(ram,0x4c9c,4,0x104000); put(ram,0x4ca0,2,0xffff);
    assert(ms5::restart_object_full(ram,s,ports,error));
    assert(get(ram,0x4c9c,4) == 0x104d92 && get(ram,0x4ca0,2) == 0 && get(ram,0x3008,4) == 0x103100 && get(ram,0x3104,4) == 0x103000);
    assert(get(ram,0x4d92,4) == 0xfedcba99 && get(ram,0x4da2,2) == 0x20 && s.a[0] == 0x104d92 && s.a[6] == 0x98765433);
    // Guard/trap errors preserve original RAM, all registers and existing ports.
    ram.assign(65536,0); ram[0x206c] = 8; s = initial(); const std::vector<std::uint8_t> before = ram; const ms5::ObjectRestartState saved = s;
    ms5::VideoPortWrite old; old.size = 2; old.address = 0x3c0000; old.value = 3; ports.assign(1,old);
    assert(!ms5::restart_object_full(ram,s,ports,error)); assert(ram == before && same(s,saved) && ports.size() == 1 && ports[0].value == 3);
    ram[0x206c] = 0xff; put(ram,0x2010,2,1); const std::vector<std::uint8_t> typed = ram;
    assert(!ms5::restart_object_full(ram,s,ports,error)); assert(ram == typed && same(s,saved));
    s.a[0] = 0x10ff40; assert(!ms5::restart_object_full(ram,s,ports,error)); s.a[0] = 0x102001; assert(!ms5::restart_object_full(ram,s,ports,error));
    std::cout << "object restart full execution tests passed\n";
}
