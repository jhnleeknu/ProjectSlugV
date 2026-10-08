#include "ms5/stage_input.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& b, std::size_t at, std::uint32_t v, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) b[at+i] = static_cast<std::uint8_t>(v >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& b, std::size_t at, unsigned int size = 4) {
    std::uint32_t v = 0; for (unsigned int i = 0; i < size; ++i) v = (v << 8) | b[at+i]; return v;
}
bool same(const ms5::SceneMapTransferState& a, const ms5::SceneMapTransferState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.d[i] != b.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.a[i] != b.a[i]) return false; return true;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); std::vector<ms5::FixedDataResource> windows; ms5::SceneMapTransferState s; std::string error;
    ms5::FixedDataResource mask; mask.source_cpu_address = mask.source_rom_offset = 0x49ab0; mask.data.push_back(0x10); mask.data.push_back(0x20); mask.data.push_back(0x40); mask.data.push_back(0x80); windows.push_back(mask);
    // Supplied four-mask fixture maps all256 bytes; D0/D1 and A4 persist.
    for (unsigned int value = 0; value < 256; ++value) {
        s = ms5::SceneMapTransferState(); s.a[4] = 0x49ab0; s.d[0] = 0x12340000U | value; s.d[1] = 0x765432ff; s.d[6] = 0xabcd5600;
        assert(ms5::step_stage_input(ram,0x49ab4,windows,s,error)); assert(s.d[7] == value && s.d[6] == (0xabcd5600U | value) && s.a[4] == 0x49ab0 && s.d[0] == (0x12340000U | value) && s.d[1] == 0x765432ff && s.d[2] == 0);
    }
    // Edge bits use D1 only after full-mask match; direction nibble always copies.
    s = ms5::SceneMapTransferState(); s.a[4] = 0x49ab0; s.d[0] = 0xf3; s.d[1] = 0x20; s.d[4] = 0x12345678; s.d[5] = 0x76543210; s.d[6] = 0xabcd5600;
    assert(ms5::step_stage_input(ram,0x49ab4,windows,s,error)); assert(s.d[7] == 0xf3 && s.d[6] == 0xabcd5623 && s.d[4] == 0x12345600 && s.d[5] == 0x76543280);
    // Odd live RAM masks with overlaps trigger the native bit5 suppression.
    ram[0xf01d] = 0x10; ram[0xf01e] = 0x30; ram[0xf01f] = 0x30; ram[0xf020] = 0x80;
    s.a[4] = 0x10f01d; s.d[0] = 0xf0; s.d[1] = 0x30;
    assert(ms5::step_stage_input(ram,0x49ab4,windows,s,error)); assert(s.a[4] == 0x10f01d && s.d[7] == 0xd0 && s.d[6] == 0xabcd5650 && s.d[2] == 0x30);
    // Zero masks match without generating edge bits; no default bytes are built in.
    s.a[4] = 0x105000; s.d[0] = 15; s.d[1] = 0xff; assert(ms5::step_stage_input(ram,0x49ab4,windows,s,error)); assert(s.d[7] == 0xff && (s.d[6] & 255U) == 15);
    // Previous-value operation uses WORD widths and retains D6.high.
    s.a[1] = 0x105000; s.d[6] = 0xabcd0000; s.d[7] = 0x1234a55a; put(ram,0x5002,0xffff,2);
    assert(ms5::step_stage_input(ram,0x49afe,windows,s,error)); assert(s.d[6] == 0xabcd000a && s.d[7] == 0x1234a55a);
    // Publication reads the mask before replacing it and keeps register high words.
    put(ram,0x5004,0x0ff0,2); s.d[0] = 0xbeef0000; s.d[6] = 0xabcd55aa; s.d[7] = 0x1234aa55;
    assert(ms5::step_stage_input(ram,0x49bb4,windows,s,error)); assert(s.d[0] == 0xbeef0ff0 && s.d[6] == 0xabcd05a0 && s.d[7] == 0x12340a50 && get(ram,0x5004,2) == 0xffff && get(ram,0x5002,2) == 0xa50 && get(ram,0x5000,2) == 0x5a0);
    // Callback setters preserve A0 for49c20 and retain D0.high while selecting slot.
    s.a[0] = 0xffffffff; s.d[0] = 0xabcd1232; assert(ms5::step_stage_input(ram,0x49c20,windows,s,error)); assert(s.a[0] == 0xffffffff && s.a[1] == 0x10d734 && s.d[0] == 0xabcd0000 && get(ram,0xd734) == 0xffffffff);
    s.d[0] = 0xabcd1233; assert(ms5::step_stage_input(ram,0x49c32,windows,s,error)); assert(s.a[0] == 0 && s.a[1] == 0x10d738 && s.d[0] == 0xabcd0004 && get(ram,0xd738) == 0);
    assert(ms5::step_stage_input(ram,0x49c66,windows,s,error)); assert(s.a[0] == 0x49e34 && s.a[1] == 0x10d734 && get(ram,0xd734) == 0x49e34);
    // Truncated mask reads and publication outside RAM roll back RAM/all13regs.
    s.a[4] = 0x49ab1; const std::vector<std::uint8_t> before = ram; ms5::SceneMapTransferState saved = s;
    assert(!ms5::step_stage_input(ram,0x49ab4,windows,s,error)); assert(ram == before && same(s,saved));
    s.a[1] = 0x10fffc; saved = s; assert(!ms5::step_stage_input(ram,0x49bb4,windows,s,error)); assert(ram == before && same(s,saved));
    s.a[1] = 0x105001; saved = s; assert(!ms5::step_stage_input(ram,0x49afe,windows,s,error)); assert(ram == before && same(s,saved));
    assert(!ms5::step_stage_input(ram,0,windows,s,error)); assert(ram == before && same(s,saved));
    std::vector<std::uint8_t> bad(65535,0); const std::vector<std::uint8_t> bad_before = bad; assert(!ms5::step_stage_input(bad,0x49c20,windows,s,error)); assert(bad == bad_before && same(s,saved));
    windows.push_back(mask); s.a[4] = 0x49ab0; saved = s; assert(!ms5::step_stage_input(ram,0x49ab4,windows,s,error)); assert(ram == before && same(s,saved));
    std::cout << "stage input tests passed\n";
}
