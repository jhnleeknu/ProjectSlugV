#include "ms5/stage_input_loop.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,std::uint32_t value,unsigned int size = 2) {
    for (unsigned int i = 0; i < size; ++i) ram[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram,unsigned int at,unsigned int size = 2) {
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value<<8)|ram[at+i]; return value;
}
ms5::SceneMapTransferState initial() {
    ms5::SceneMapTransferState s;
    for (unsigned int i = 0; i < 8; ++i) s.d[i] = 0xabcd1200U+i;
    for (unsigned int i = 0; i < 5; ++i) s.a[i] = 0x76540000U+i;
    return s;
}
bool same(const ms5::SceneMapTransferState& a,const ms5::SceneMapTransferState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.a[i] != b.a[i]) return false;
    return true;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); std::vector<ms5::FixedDataResource> windows;
    ms5::SceneMapTransferState s = initial(); std::string error;
    // Activity returns second address/full D0=1 while preserving all other regs.
    ram[0xe09] = 0x80; ram[0xd68e] = 0xff;
    assert(ms5::step_stage_input_loop(ram,0x47642,windows,s,1,error));
    assert(ram[0xd68e] == 1 && s.a[0] == 0x100da8 && s.d[0] == 1 && s.d[7] == initial().d[7]);
    // Inactive lookup avoids absent resources and retains incoming D0.high.
    s = initial(); s.d[0] = 0xabcd0000; put(ram,0xcb8,0x270e,4);
    assert(ms5::step_stage_input_loop(ram,0x4d7a6,windows,s,0,error));
    assert(s.a[0] == 0x100cb8 && s.a[4] == 0x10dcba && s.d[0] == 0xabcd0000 && s.d[5] == 0xffffffffU && s.d[7] == initial().d[7]);
    put(ram,0xcb8,0,4); put(ram,0xdcba,1); ram[0xdce1] = 255;
    ms5::FixedDataResource lookup; lookup.source_cpu_address = lookup.source_rom_offset = 0x4cf64; lookup.data.resize(4092,0);
    put(lookup.data,4090,0xcafe); windows.push_back(lookup); s = initial(); s.d[0] = 0xabcd0000;
    ram[0xdcdf] = 0x9a; ram[0xdce0] = 0xbc; put(ram,0xdcd6,0x8001); put(ram,0xdcda,0x1234); ram[0xdce4] = 0xde;
    assert(ms5::step_stage_input_loop(ram,0x4d7a6,windows,s,0,error));
    assert(s.d[0] == 255 && s.d[1] == 0xabcd129aU && s.d[2] == 0xabcd12bcU && s.d[3] == 0xabcd8001U);
    assert(s.d[4] == 0xcafe && s.a[4] == 0x4df54 && s.a[0] == 0x100cb8 && s.a[1] == initial().a[1]);
    // Crossing into inactive selected player keeps the computed D7 direction.
    s = initial(); s.a[0] = 0x100e80; put(ram,0xec2,0xffff); put(ram,0xeca,1); put(ram,0xefe,0);
    put(ram,0xcb8,0x270e,4); windows.clear();
    assert(ms5::step_stage_input_loop(ram,0x1da60,windows,s,0,error)); assert(s.d[7] == 8 && s.a[0] == 0x100cb8 && s.d[0] == 0xabcd0000U);
    // Unknown callbacks are harmless for inactive objects; both masks publish.
    put(ram,0xda8,0x270e,4); put(ram,0xd734,0xdeadbeef,4); put(ram,0xd738,0xdeadbeef,4);
    put(ram,0xd72a,0xffff); put(ram,0xd730,0xffff); s = initial();
    assert(ms5::step_stage_input_loop(ram,0x49b0c,windows,s,0,error));
    assert(get(ram,0xd726,4) == 0 && get(ram,0xd72c,4) == 0 && s.a[1] == 0x10d72c && s.a[0] == 0x100da8);
    // RAM masks run without fixed resources. D0/D1 upper24 survive byte loads.
    put(ram,0xd734,0,4); put(ram,0xd738,0,4); ram[0x12] = 2;
    ram[0x4caa] = 0x35; ram[0x4cab] = 0x10; ram[0x4cb0] = 0xa6; ram[0x4cb1] = 0x80;
    const unsigned int masks[4] = {0x10,0x20,0x40,0x80};
    for (unsigned int i = 0; i < 4; ++i) { ram[0xf01c+i] = masks[i]; ram[0xf020+i] = masks[i]; }
    put(ram,0xd72a,0xffff); put(ram,0xd730,0xffff); s = initial();
    assert(ms5::step_stage_input_loop(ram,0x49b0c,windows,s,0,error));
    assert(get(ram,0xd726) == 0x15 && get(ram,0xd728) == 0x35 && get(ram,0xd72c) == 0x86 && get(ram,0xd72e) == 0xa6);
    assert(s.d[0] == 0xabcdffffU && s.d[1] == 0xabcd1280U && s.a[4] == 0x10f020);
    // First publication and mask replacement roll back if second callback fails.
    put(ram,0xda8,0,4); put(ram,0xd738,0xbad,4); put(ram,0xd72a,0x1234); s = initial();
    const std::vector<std::uint8_t> saved_ram = ram; const ms5::SceneMapTransferState saved = s;
    assert(!ms5::step_stage_input_loop(ram,0x49b0c,windows,s,0,error)); assert(ram == saved_ram && same(s,saved));
    assert(!ms5::step_stage_input_loop(ram,0,windows,s,0,error)); assert(ram == saved_ram && same(s,saved));
    ram.resize(65535); const std::vector<std::uint8_t> short_ram = ram;
    assert(!ms5::step_stage_input_loop(ram,0x47642,windows,s,0,error)); assert(ram == short_ram && same(s,saved));
    std::cout << "stage_input_loop_test passed\n";
}
