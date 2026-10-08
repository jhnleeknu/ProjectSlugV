#include "ms5/stage_input_callback.h"
#include <cassert>
#include <iostream>
#include <cstring>
namespace {
void put(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t v, unsigned int size = 2) {
    for (unsigned int i = 0; i < size; ++i) ram[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
ms5::SceneMapTransferState initial() {
    ms5::SceneMapTransferState s;
    for (unsigned int i = 0; i < 8; ++i) s.d[i] = 0xabcd1200U+i;
    for (unsigned int i = 0; i < 5; ++i) s.a[i] = 0x76540000U+i;
    s.a[0] = 0x100cb8; return s;
}
bool same(const ms5::SceneMapTransferState& a, const ms5::SceneMapTransferState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.a[i] != b.a[i]) return false;
    return true;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); std::vector<ms5::FixedDataResource> w;
    ms5::SceneMapTransferState s = initial(); std::string error;
    assert(ms5::step_stage_input_callback(ram,0x1d8cc,w,s,1,error)); assert(same(s,initial()));
    put(ram,0xde24,0x8001); assert(ms5::step_stage_input_callback(ram,0xe73f2,w,s,0,error)); assert(s.d[7] == 0xabcd8001U);
    // LONG projection crossing restores A0 and only the saved low WORD of D2.
    s = initial(); put(ram,0xcfa,0xffff1234,4); put(ram,0xd02,0x00015678,4); put(ram,0xd30,1);
    assert(ms5::step_stage_input_callback(ram,0x49d88,w,s,0,error));
    assert(s.a[0] == 0x100cb8 && s.a[1] == 0x10d738 && s.d[0] == 0xabcd0004U);
    assert(s.d[2] == 0x12340001U && s.d[3] == 0x5678fffeU && s.d[7] == 4);
    // Equality tail does not subtract the target from D3, and installs stop.
    s = initial(); put(ram,0xcfa,0x00051234,4); put(ram,0xd02,0x00095678,4); put(ram,0xd73e,5);
    assert(ms5::step_stage_input_callback(ram,0x49de6,w,s,0,error));
    assert(s.d[3] == 0x56780009U && s.a[0] == 0x49e34 && s.d[7] == 0);
    // Absolute-memory CMPA chooses index0 even for a noncanonical object address.
    s = initial(); s.a[0] = 0x100e00; put(ram,0xcb8,s.a[0],4); put(ram,0xe42,0x00060000,4); put(ram,0xe4a,0x00070000,4);
    put(ram,0xe78,0); put(ram,0xd73c,0); ram[0xd732] = 0;
    assert(ms5::step_stage_input_callback(ram,0x49eba,w,s,0,error)); assert(ram[0xd732] == 1 && s.d[7] == 4);
    s = initial(); s.a[0] = 0x100e00; ram[0xd732] = 0;
    assert(ms5::step_stage_input_callback(ram,0x49ef0,w,s,0,error)); assert(s.d[1] == 0xabcd1200U && s.d[0] == 0xabcd0000U && s.d[2] == 4);
    // Already-set path avoids coordinate reads entirely.
    s = initial(); s.a[0] = 0x10ff86; put(ram,0xcb8,s.a[0],4); put(ram,0xfffe,0xbeef); ram[0xd732] = 1;
    assert(ms5::step_stage_input_callback(ram,0x49ef0,w,s,0,error)); assert(s.d[0] == 0xabcdbeefU && s.d[7] == 0);
    // BYTE SNE/EOR retain the upper24 register bits.
    s = initial(); ram[0xccd] = 1; put(ram,0xd30,0); ram[0xd740] = 0;
    assert(ms5::step_stage_input_callback(ram,0x49f2c,w,s,0,error));
    assert(s.d[1] == 0xabcd12ffU && s.d[2] == 0xabcd1200U && s.d[7] == 8);
    // A6 is an independent live WORD input and is only accessed on its branch.
    s = initial(); ram[0xccd] = 0; put(ram,0x203a,0x7fff);
    assert(ms5::step_stage_input_callback(ram,0x1d5e2,w,s,0x102000,error)); assert(s.d[7] == 8);
    put(ram,0x203a,0x8000); assert(ms5::step_stage_input_callback(ram,0x1d5e2,w,s,0x102000,error)); assert(s.d[7] == 0);
    // Clearing setter happens before the mapper; a missing mask rolls it back.
    s = initial(); put(ram,0xd30,1); put(ram,0xd738,0xdeadbeef,4);
    const std::vector<std::uint8_t> before = ram; const ms5::SceneMapTransferState saved = s;
    assert(!ms5::step_stage_input_callback(ram,0x1d628,w,s,0,error)); assert(ram == before && same(s,saved));
    ms5::FixedDataResource masks; masks.source_cpu_address = 0x49ab0; masks.source_rom_offset = 0x49ab0;
    masks.data.push_back(0x10); masks.data.push_back(0x20); masks.data.push_back(0x40); masks.data.push_back(0x80); w.push_back(masks);
    assert(ms5::step_stage_input_callback(ram,0x1d628,w,s,0,error));
    assert(s.a[0] == 0 && s.a[1] == 0x10d738 && s.a[4] == 0x49ab0 && s.d[0] == 0 && s.d[7] == 0);
    assert(ram[0xd738] == 0 && ram[0xd739] == 0 && ram[0xd73a] == 0 && ram[0xd73b] == 0);
    // Clear conditional uses d683.bit2; disabled branch does not inspect A0.
    s = initial(); s.a[0] = 1; ram[0xd683] = 0;
    assert(ms5::step_stage_input_callback(ram,0x1d5ac,w,s,1,error)); assert(s.a[0] == 1 && s.d[7] == 0);
    ram[0xd683] = 4; const ms5::SceneMapTransferState invalid = s; const std::vector<std::uint8_t> invalid_ram = ram;
    assert(!ms5::step_stage_input_callback(ram,0x1d5ac,w,s,1,error)); assert(same(s,invalid) && ram == invalid_ram);
    assert(!ms5::step_stage_input_callback(ram,0x49b0c,w,s,0,error)); assert(same(s,invalid) && ram == invalid_ram);
    ram.resize(65535); const std::vector<std::uint8_t> short_ram = ram;
    assert(!ms5::step_stage_input_callback(ram,0x1d8cc,w,s,0,error)); assert(ram == short_ram && same(s,invalid));
    std::cout << "stage_input_callback_test passed\n";
}
