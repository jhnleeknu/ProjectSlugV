#include "ms5/stage_buffer_frame.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,std::uint32_t value,unsigned int size = 2) {
    for (unsigned int i = 0; i < size; ++i) ram[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram,unsigned int at,unsigned int size = 4) {
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value<<8)|ram[at+i]; return value;
}
ms5::StageBufferFrameState initial() {
    ms5::StageBufferFrameState s;
    for (unsigned int i = 0; i < 8; ++i) s.registers.d[i] = 0xabcd1200U+i;
    for (unsigned int i = 0; i < 5; ++i) s.registers.a[i] = 0x76540000U+i;
    s.a6 = 0xdeadbeef; return s;
}
bool same(const ms5::StageBufferFrameState& a,const ms5::StageBufferFrameState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.registers.d[i] != b.registers.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.registers.a[i] != b.registers.a[i]) return false;
    return a.a6 == b.a6 && a.bank == b.bank && a.phase == b.phase && a.saved_a6 == b.saved_a6 && a.saved_slot_a4 == b.saved_slot_a4 && a.saved_slot_d7 == b.saved_slot_d7 && a.saved_d0 == b.saved_d0 && a.saved_d1 == b.saved_d1 && a.saved_d7 == b.saved_d7 && a.saved_a0 == b.saved_a0;
}
void prepare(std::vector<std::uint8_t>& ram,bool debug) {
    ram.assign(65536,0); put(ram,0xdc88,0x10db88,4); put(ram,0x9152,0xcd50,4);
    for (unsigned int i = 0; i < 16; ++i) put(ram,0xdb88+i*2,0x8001+i);
    ram[0xf001] = debug ? 0x80 : 0;
    if (debug) {
        put(ram,0xdaf8,0x100cb8,4); put(ram,0xdafc,0x101200,4);
        put(ram,0x1204,64,4); put(ram,0x1208,0); put(ram,0x120a,1); put(ram,0x8b36,0); put(ram,0x8b38,12);
    }
}
}
int main() {
    std::vector<std::uint8_t> ram; std::vector<ms5::FixedDataResource> windows; std::vector<ms5::VideoPortWrite> ports;
    ms5::StageBufferFrameState s; std::string error;
    // Buffer flip uses the old bit, zeros exactly208 bytes and separate counter.
    for (unsigned int flip = 0; flip < 2; ++flip) {
        prepare(ram,false); ram[0xd744] = flip ? 0x80 : 0; ram[0xdb85] = 0x12; ram[0xdb87] = 0x34;
        const unsigned int selected = flip ? 0xd746 : 0xd918;
        for (unsigned int i = 0; i < 208; ++i) ram[selected+i] = 0xff;
        put(ram,selected+0x1d0,0xffff); s = initial(); s.bank = 3; ports.resize(1);
        assert(ms5::step_stage_buffer_frame(ram,windows,s,ports,error));
        assert(s.phase == 0 && s.a6 == 0xdeadbeef && s.bank == 3 && ports.empty());
        assert(s.registers.a[4] == 0x100000+selected && s.registers.a[3] == (flip ? 0x10d918U : 0x10d746U));
        assert(s.registers.a[0] == 0x10dba8 && s.registers.a[1] == initial().registers.a[1] && s.registers.a[2] == initial().registers.a[2]);
        for (unsigned int i = 0; i < 8; ++i) assert(s.registers.d[i] == 0);
        for (unsigned int i = 0; i < 208; ++i) assert(ram[selected+i] == 0);
        assert(get(ram,selected+0x1d0,2) == 0 && ram[0xdb84] == 0x12 && ram[0xdb85] == 0 && ram[0xdb86] == 0x34 && ram[0xdb87] == 0);
        assert(get(ram,0xdb88,2) == 0x4000);
    }
    // Ring pointer can alias its own RAM metadata; wrapping is tested afterLSR.
    prepare(ram,false); put(ram,0xdc88,0x10dc88,4); ram[0xf001] = 1; ram[0x4cab] = 0x80; s = initial();
    assert(ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(get(ram,0xdc88) == 0x10db88 && s.registers.a[0] == 0x10db88 && ram[0xdb84] == 255);
    // Normal two sprites preserve outerA6 and issue both helper/outer resets.
    prepare(ram,true); s = initial(); s.bank = 3;
    assert(ms5::step_stage_buffer_frame(ram,windows,s,ports,error));
    assert(s.phase == 0 && s.a6 == initial().a6 && s.bank == 2 && ports.size() == 4 && get(ram,0x8d3a,2) == 4);
    assert(get(ram,0x7f34+8) == (0x20000000U|0x122bU) && get(ram,0x7f40+8) == (0x20800000U|0x122bU));
    for (unsigned int i = 0; i < 4; ++i) assert(ports[i].size == 2 && ports[i].address == (i%2 == 0 ? 0x2ffff2U : 0x2ffff0U) && ports[i].value == (i%2 == 0 ? 0x1000U : 0));
    assert(s.saved_a6 == 0 && s.saved_a0 == 0 && s.saved_slot_a4 == 0);
    // Slot filters: nulls and mismatched low nibble do not submit or resetbank.
    prepare(ram,true); ram[0xd25] = 1; s = initial(); s.bank = 3;
    assert(ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(ports.empty() && s.bank == 3 && get(ram,0x8d3a,2) == 0);
    // First pending, then live dimensions/flags produce second pending.
    prepare(ram,true); put(ram,0x8d34,2); put(ram,0x8d36,4); s = initial(); s.bank = 3;
    assert(ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(s.phase == 1 && ports.empty() && s.bank == 3 && s.a6 == 0x100cb8);
    assert(s.saved_a6 == initial().a6 && s.saved_slot_a4 == 0x10daf8 && s.saved_slot_d7 == 0 && s.saved_d0 == 64 && s.saved_d1 == 0xffff0000U && s.saved_d7 == 0x122b && s.saved_a0 == 0x101208);
    const ms5::StageBufferFrameState first = s; const std::vector<std::uint8_t> first_ram = ram;
    assert(ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(same(s,first) && ram == first_ram && ports.empty());
    put(ram,0x8d34,4); put(ram,0x8d36,6); put(ram,0x1208,3); put(ram,0x120a,5); ram[0xccd] = 1;
    assert(ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(s.phase == 2 && ports.empty() && s.bank == 3);
    assert(s.saved_d0 == 0 && s.saved_d1 == 0 && s.saved_d7 == 0 && s.saved_a0 == 0x10120c && s.registers.d[0] == 0xfffd0045U);
    const ms5::StageBufferFrameState second = s; put(ram,0x9152,0,4); put(ram,0x8d36,88); put(ram,0x8d3a,99);
    const std::vector<std::uint8_t> hold = ram;
    assert(ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(same(s,second) && ram == hold && ports.empty());
    put(ram,0x8d34,6);
    assert(ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(s.phase == 0 && s.a6 == initial().a6 && s.bank == 2 && ports.size() == 4 && get(ram,0x8d3a,2) == 4);
    // Late failure after both reset pairs preserves caller's old ports/stateRAM.
    prepare(ram,true); put(ram,0xdc88,0x10fff0,4); s = initial(); ports.resize(1); ports[0].size = 1; ports[0].address = 7; ports[0].value = 9;
    const std::vector<std::uint8_t> before = ram; const ms5::StageBufferFrameState saved = s;
    assert(!ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(ram == before && same(s,saved) && ports.size() == 1 && ports[0].value == 9);
    s = second; s.saved_slot_a4 += 8; const ms5::StageBufferFrameState bad = s;
    assert(!ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(ram == before && same(s,bad) && ports[0].value == 9);
    s = second; s.saved_slot_d7 = 0x10000; const ms5::StageBufferFrameState badword = s;
    assert(!ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(same(s,badword) && ram == before);
    s = initial(); s.bank = 1; const ms5::StageBufferFrameState badbank = s;
    assert(!ms5::step_stage_buffer_frame(ram,windows,s,ports,error)); assert(same(s,badbank) && ram == before);
    std::cout << "stage_buffer_frame_test passed\n";
}
