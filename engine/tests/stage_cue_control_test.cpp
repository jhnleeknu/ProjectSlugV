#include "ms5/stage_cue_control.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,std::uint32_t value,unsigned int size = 2) {
    for (unsigned int i = 0; i < size; ++i) ram[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram,unsigned int at,unsigned int size = 4) {
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
    ms5::SceneMapTransferState s = initial(); std::string error; bool carry = true;
    s.a[0] = 0; assert(ms5::step_stage_cue_control(ram,0xe89fa,windows,s,1,carry,error));
    assert(s.a[0] == 0xe89ec && get(ram,0xde2a) == 0xe89ec && carry);
    s.a[0] = 0; assert(ms5::step_stage_cue_control(ram,0xe8a1c,windows,s,1,carry,error));
    assert(s.a[0] == 0xe89e4 && get(ram,0xde26) == 0xe89e4 && ram[0xde2e] == 255 && ram[0xde2f] == 0 && carry);
    s.a[0] = 0xffffffffU; carry = false;
    assert(ms5::step_stage_cue_control(ram,0xe89fa,windows,s,1,carry,error)); assert(get(ram,0xde2a) == 0xffffffffU && !carry);
    // Null stream leaves D0 intact and does not need any fixed resources.
    put(ram,0xde2a,0,4); s = initial();
    assert(ms5::step_stage_cue_control(ram,0xe8ad0,windows,s,1,carry,error)); assert(s.a[0] == 0 && s.d[0] == initial().d[0]);
    // Gates are unsigned WORDs, stride is12 bytes, and D0.high is retained.
    put(ram,0xde2a,0x102000,4); put(ram,0xd418,0x8000); put(ram,0x200c,0x7fff); put(ram,0x2018,0x8000); put(ram,0x2024,0x8001);
    assert(ms5::step_stage_cue_control(ram,0xe8ad0,windows,s,1,carry,error)); assert(s.a[0] == 0x102018 && get(ram,0xde2a) == 0x102018 && s.d[0] == 0xabcd8000U);
    // Coordinates wrap atWORD width and use d3bc/c0, retaining all upper bits.
    s = initial(); s.a[0] = 0x102100; put(ram,0x2100,0xffff); put(ram,0x2102,0x8000); ram[0x2104] = 3;
    put(ram,0xd3bc,2); put(ram,0xd3c0,0x8000); put(ram,0xd3a2,0x1234); carry = true;
    assert(ms5::step_stage_cue_control(ram,0xe8af4,windows,s,1,carry,error)); assert(s.d[0] == 0xabcd0001U && s.d[1] == 0xabcd0000U && carry);
    // Fixed record is borrowed; camera-relative flags are read separately.
    ms5::FixedDataResource record; record.source_cpu_address = record.source_rom_offset = 0x50000; record.data.resize(5,0);
    put(record.data,0,1); put(record.data,2,2); record.data[4] = 0; windows.push_back(record); s.a[0] = 0x50000;
    assert(ms5::step_stage_cue_control(ram,0xe8af4,windows,s,1,carry,error)); assert(s.d[0] == 0xabcd0001U && s.d[1] == 0xabcd0002U && windows[0].data == record.data);
    // Allocation failure still copies originalA6+6a, including odd source.
    s = initial(); s.a[0] = 0; s.a[1] = 1; ram[0x306b] = 0xa5; carry = true;
    assert(ms5::step_stage_cue_control(ram,0x2986,windows,s,0x103001,carry,error));
    assert(!carry && s.a[0] == 0x100e98 && s.a[1] == 1 && ram[0xf02] == 0xa5 && s.d[0] == initial().d[0]);
    // Successful allocation first copies temporary parent, then original parent.
    put(ram,0x4c9c,0x102000,4); put(ram,0x4ca0,1); put(ram,0x2008,0,4);
    put(ram,0x3008,0x104000,4); put(ram,0x3010,0xffff); ram[0x306a] = 0x11; ram[0x506b] = 0x77;
    s = initial(); s.d[0] = 0xabcd0000; s.a[0] = 0xd5f16; s.a[1] = 0x103000;
    assert(ms5::step_stage_cue_control(ram,0x2986,windows,s,0x105001,carry,error));
    assert(carry && s.d[0] == 0xabcd0000 && s.a[0] == 0x102000 && s.a[1] == 0x104000 && ram[0x206a] == 0x77);
    // Original-parent source is read LIVE after allocator's temporary-parent copy.
    put(ram,0x4c9c,0x102000,4); put(ram,0x4ca0,1); put(ram,0x2008,0,4); put(ram,0x3008,0x104000,4); ram[0x306a] = 0x33;
    s = initial(); s.d[0] = 0; s.a[0] = 0xd5f16; s.a[1] = 0x103000;
    assert(ms5::step_stage_cue_control(ram,0x2986,windows,s,0x102000,carry,error)); assert(carry && ram[0x206a] == 0x33);
    // Late invalid source rolls back allocator mutations, full state and carry.
    for (unsigned int c = 0; c < 2; ++c) {
        put(ram,0x4c9c,0x102000,4); put(ram,0x4ca0,1); put(ram,0x2008,0,4); put(ram,0x3008,0x104000,4);
        s = initial(); s.d[0] = 0; s.a[0] = 0xd5f16; s.a[1] = 0x103000; carry = c != 0;
        const std::vector<std::uint8_t> before = ram; const ms5::SceneMapTransferState saved = s;
        assert(!ms5::step_stage_cue_control(ram,0x2986,windows,s,0xffffffffU,carry,error)); assert(ram == before && same(s,saved) && carry == (c != 0));
    }
    // A stream lacking a later gate fails atomically rather than inventing a stop.
    put(ram,0xde2a,0x10fff2,4); put(ram,0xfffe,0); s = initial(); carry = true;
    const std::vector<std::uint8_t> before = ram; const ms5::SceneMapTransferState saved = s;
    assert(!ms5::step_stage_cue_control(ram,0xe8ad0,windows,s,0,carry,error)); assert(ram == before && same(s,saved) && carry);
    assert(!ms5::step_stage_cue_control(ram,0xe8a48,windows,s,0,carry,error)); assert(ram == before && same(s,saved) && carry);
    ram.resize(65535); const std::vector<std::uint8_t> short_ram = ram;
    assert(!ms5::step_stage_cue_control(ram,0xe89fa,windows,s,0,carry,error)); assert(ram == short_ram && same(s,saved) && carry);
    std::cout << "stage_cue_control_test passed\n";
}
