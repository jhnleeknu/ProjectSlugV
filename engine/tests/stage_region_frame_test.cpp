#include "ms5/stage_region_frame.h"
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
    ms5::SceneMapTransferState s = initial(); bool carry = true; std::string error;
    // Activity clears false results and preserves D0.high; memory tests useBYTE.
    assert(ms5::step_stage_region_frame(ram,0x49392,windows,s,1,2,carry,error));
    assert(!carry && s.d[0] == 0xabcd0000U && s.a[0] == 0x100cb8);
    ram[0xd68e] = 2; s.d[0] = 0xabcdffffU;
    assert(ms5::step_stage_region_frame(ram,0x49392,windows,s,1,3,carry,error)); assert(carry && s.d[0] == 0xabcd0001U && s.a[0] == 0x100da8);
    // Inactive pointer leaves D0/A1; active pointer uses arbitrary A6.high.
    s = initial(); s.d[0] = 0xbeef0000U; const std::uint32_t old_a1 = s.a[1];
    assert(ms5::step_stage_region_frame(ram,0x4d9d6,windows,s,0x76543210,2,carry,error)); assert(s.a[0] == 0 && s.a[1] == old_a1 && s.d[0] == 0xbeef0000U && carry);
    put(ram,0xdcba,1); put(ram,0xdcc0,0x8001); put(ram,0xdcc2,0xabcdef01,4);
    assert(ms5::step_stage_region_frame(ram,0x4d9d6,windows,s,0x76543210,2,carry,error)); assert(s.d[0] == 0x76548001 && s.a[0] == 0x76548001 && s.a[1] == 0xabcdef01);
    // Fallback restores only D0.low; byte and bit0 selections differ for2.
    put(ram,0xdce6,1); put(ram,0xdcec,0); put(ram,0xd0e,0x101234,4); s = initial(); s.d[0] = 0xabcd0002U;
    assert(ms5::step_stage_region_frame(ram,0x1c028,windows,s,0x76543210,2,carry,error)); assert(s.d[0] == 0x76540000 && s.a[0] == 0x100cb8 && s.a[1] == 0x101234 && s.a[4] == 0x10dce6);
    // Alternation clears exactly six spaced WORDs and returns A1=A2.
    for (unsigned int parity = 0; parity < 2; ++parity) {
        put(ram,0xe,parity); const unsigned int begin = parity ? 0xdd98 : 0xdd5c;
        for (unsigned int i = 0; i < 60; ++i) ram[begin+i] = 0xaa;
        s = initial();
        assert(ms5::step_stage_region_frame(ram,0xb481e,windows,s,1,2,carry,error));
        assert(s.d[0] == 0 && s.a[1] == 0x100000+begin+60 && s.a[2] == s.a[1] && carry);
        for (unsigned int i = 0; i < 60; ++i) assert(ram[begin+i] == (i%10 < 2 ? 0 : 0xaa));
    }
    // Full frame MOVEM signextends before WORD coordinate wrap; source canalias.
    ram.assign(65536,0); ram[0xd68e] = 3; put(ram,0xe,0); put(ram,0xd0e,0x101000,4); put(ram,0xdfe,0x10dd48,4);
    put(ram,0x1000,0xffff); put(ram,0x1002,0x8000); put(ram,0x1004,0x7fff); put(ram,0x1006,0xffff);
    put(ram,0xcfa,2); put(ram,0xcfe,0x8000); put(ram,0xdea,3); put(ram,0xdee,4); ram[0xdd58] = 1; ram[0xdd5a] = 255;
    s = initial(); carry = false;
    assert(ms5::step_stage_region_frame(ram,0xb4a2a,windows,s,0x100000,2,carry,error));
    assert(!carry && get(ram,0xdd48) == 1 && get(ram,0xdd4a) == 0 && get(ram,0xdd50) == 4 && get(ram,0xdd52) == 4);
    assert(s.d[0] == 0 && s.d[1] == 4 && s.d[2] == 0x7fff && s.d[3] == 0xffffffffU && s.a[0] == 0x10dd5c && s.a[1] == 0x10dd98 && s.a[4] == 0x10dce6);
    assert(ram[0xdd58] == 0 && ram[0xdd5a] == 254);
    // Matching bank immutable source is selected independently of RAMshadow.
    for (unsigned int bank = 2; bank <= 3; ++bank) {
        ram.assign(65536,0); ram[0xd68e] = 2; put(ram,0xdfe,0x200000,4); put(ram,0x10,bank == 2 ? 1 : 0);
        windows.clear();
        for (unsigned int b = 2; b <= 3; ++b) {
            ms5::FixedDataResource w; w.source_cpu_address = 0x200000; w.source_rom_offset = b == 2 ? 0x200000 : 0x300000; w.data.resize(8,0);
            put(w.data,0,b); put(w.data,2,0x8000+b); put(w.data,4,0xfffe); put(w.data,6,0x7fff); windows.push_back(w);
        }
        s = initial(); carry = true;
        assert(ms5::step_stage_region_frame(ram,0xb4a2a,windows,s,0,bank,carry,error)); assert(get(ram,0xdd50) == bank && s.d[1] == 0xffff8000U+bank && carry);
    }
    // A late second source error preserves first publication and carry eitherway.
    for (unsigned int c = 0; c < 2; ++c) {
        ram.assign(65536,0); windows.clear(); ram[0xd68e] = 3; put(ram,0xd0e,0x101000,4); put(ram,0xdfe,0x10fffa,4);
        s = initial(); carry = c != 0; const std::vector<std::uint8_t> before = ram; const ms5::SceneMapTransferState saved = s;
        assert(!ms5::step_stage_region_frame(ram,0xb4a2a,windows,s,0,2,carry,error)); assert(ram == before && same(s,saved) && carry == (c != 0));
        assert(!ms5::step_stage_region_frame(ram,0,windows,s,0,2,carry,error)); assert(ram == before && same(s,saved));
        assert(!ms5::step_stage_region_frame(ram,0xb481e,windows,s,0,1,carry,error)); assert(ram == before && same(s,saved));
    }
    ram.resize(65535); const std::vector<std::uint8_t> short_ram = ram; const ms5::SceneMapTransferState saved = s;
    assert(!ms5::step_stage_region_frame(ram,0x49392,windows,s,0,2,carry,error)); assert(ram == short_ram && same(s,saved));
    std::cout << "stage_region_frame_test passed\n";
}
