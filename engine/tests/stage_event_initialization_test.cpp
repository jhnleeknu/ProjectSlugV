#include "ms5/stage_event_initialization.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, unsigned int size, std::uint32_t v) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at, unsigned int size) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < size; ++i) v = (v << 8) | b[at+i]; return v;
}
ms5::ObjectRestartState initial(std::uint32_t stream, std::uint16_t target) {
    ms5::ObjectRestartState s; s.a[0] = stream; s.a[5] = 0x108000; s.a[6] = 0xabcd1235; s.d[0] = 0x12340000U | target; return s;
}
std::vector<std::uint8_t> ram() { std::vector<std::uint8_t> b(65536,0); b[0xc60] = 0xff; return b; }
bool same(const ms5::ObjectRestartState& a, const ms5::ObjectRestartState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 7; ++i) if (a.a[i] != b.a[i]) return false; return true;
}
}
int main() {
    std::vector<ms5::FixedDataResource> windows; std::string error; std::vector<ms5::VideoPortWrite> ports;
    std::vector<std::uint8_t> b = ram(); put(b,0x10,2,1); ms5::ObjectRestartState s = initial(0,7);
    assert(ms5::initialize_stage_events(b,windows,s,ports,error));
    assert(ports.size() == 1 && ports[0].address == 0x300001 && ports[0].value == 7 && get(b,0x10,2) == 1);
    assert(s.a[0] == 0x100bf4 && s.a[5] == 0x108000 && s.a[6] == 0xabcd1235 && s.d[0] == 7 && s.d[7] == 0 && get(b,0xc6a,4) == 0);
    // Zero target reads only the header, without reading/following its negative jump.
    b = ram(); put(b,0x5000,2,0xfffe); s = initial(0x105000,0);
    assert(ms5::initialize_stage_events(b,windows,s,ports,error));
    assert(s.a[1] == 0x105002 && s.d[1] == 0xfffffffe && s.d[7] == 0x105002 && get(b,0xc6a,4) == 0x105002 && ports.size() == 3);
    // D1.byte replaces only the header displacement low byte; signed jump is live.
    b = ram(); put(b,0x5000,2,0x1204); put(b,0x6208,2,1); s = initial(0x105000,1);
    assert(ms5::initialize_stage_events(b,windows,s,ports,error)); assert(s.a[1] == 0x106206 && s.d[1] == 0xffff1200);
    b = ram(); put(b,0x5000,2,0x1204); b[0x6206] = 0xff; s = initial(0x105000,1);
    assert(ms5::initialize_stage_events(b,windows,s,ports,error)); assert(s.d[1] == 0xffff12ff);
    // Walk a zero marker then select the next record; header low high-byte remains.
    b = ram(); put(b,0x5000,2,4); put(b,0x5008,2,1); put(b,0x500a,2,6); put(b,0x500e,2,2); s = initial(0x105000,2);
    assert(ms5::initialize_stage_events(b,windows,s,ports,error)); assert(s.a[1] == 0x10500c && s.d[7] == 0x10500c && s.d[1] == 0xffff0000);
    // Stream aliases the restarted object: callback/reset mutations supply the reads.
    b = ram(); s = initial(0x100bf4,1);
    assert(ms5::initialize_stage_events(b,windows,s,ports,error)); assert(get(b,0xbf4,4) == 0xe9150 && s.a[1] == 0x100c04 && get(b,0xc6a,4) == 0x100c04);
    // Incoming A5 chooses the object before the callee sets A5=108000.
    b = ram(); b[0xd60] = 0xff; put(b,0xc04,2,1); s = initial(0,0); s.a[5] = 0x108100;
    assert(ms5::initialize_stage_events(b,windows,s,ports,error)); assert(s.a[0] == 0x100cf4 && get(b,0xcf4,4) == 0xe9150 && get(b,0xc04,2) == 1 && s.a[5] == 0x108000);
    // Borrowed fixed resource, including a byte at an odd address.
    ms5::FixedDataResource w; w.source_cpu_address = w.source_rom_offset = 0x50000; w.data.assign(7,0); put(w.data,0,2,3); w.data[5] = 0xff; windows.push_back(w);
    b = ram(); s = initial(0x50000,1); assert(ms5::initialize_stage_events(b,windows,s,ports,error)); assert(s.a[1] == 0x50005 && s.d[1] == 0xffff00ff);
    // A marker trap after full restart rolls back RAM, registers and previous ports.
    b = ram(); put(b,0x5000,2,0); b[0x5002] = 2; s = initial(0x105000,1);
    const std::vector<std::uint8_t> before = b; const ms5::ObjectRestartState old = s;
    ms5::VideoPortWrite saved; saved.size = 4; saved.address = 0x3c0000; saved.value = 9; ports.assign(1,saved);
    assert(!ms5::initialize_stage_events(b,windows,s,ports,error)); assert(b == before && same(s,old) && ports.size() == 1 && ports[0].value == 9);
    windows.push_back(w); s = initial(0x50000,1); const ms5::ObjectRestartState ambiguous = s;
    assert(!ms5::initialize_stage_events(b,windows,s,ports,error)); assert(b == before && same(s,ambiguous));
    s = initial(0,0); s.a[5] = 0; assert(!ms5::initialize_stage_events(b,windows,s,ports,error)); assert(b == before);
    std::cout << "stage event initialization tests passed\n";
}
