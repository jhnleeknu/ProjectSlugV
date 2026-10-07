#include "ms5/stage_transition.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value, unsigned int size = 4) {
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size = 4) {
    std::uint32_t value = 0;
    for (unsigned int i = 0; i < size; ++i) value = (value << 8) | ram[at + i];
    return value;
}
ms5::StageTransitionState initial(std::uint32_t pc) {
    ms5::StageTransitionState state; state.next_pc = pc;
    state.d0 = 0x12345678; state.d1 = 0xabcdefff; state.d2 = 0x76543210; state.d3 = 0x98765432;
    return state;
}
bool same(const ms5::StageTransitionState& a, const ms5::StageTransitionState& b) {
    return a.next_pc == b.next_pc && a.d0 == b.d0 && a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.a6 == b.a6;
}
void allocator(std::vector<std::uint8_t>& ram, std::uint32_t node) {
    put(ram,0x4c9c,node); put(ram,0x4ca0,1,2);
    put(ram,node - 0x100000 + 8,0);
    put(ram,0xb38,0x100820); put(ram,0xb40,4,2);
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); std::vector<ms5::VideoPortWrite> ports; std::string error;
    ms5::StageTransitionState state = initial(0x478c4);
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(state.next_pc == 0x480bc && get(ram,0xb30) == 0x478de && ports.empty());
    assert(state.d0 == 0x0000e100 && state.d1 == 0x0000e100 && state.d2 == 0x0000e100 && state.d3 == 1);
    assert(ram[0x7dd4] == 1 && get(ram,0x7dc8,2) == 0xe100);
    // Already-at-target effects preserve MOVEQ highwords and D3 highword.
    for (unsigned int i = 0; i < 3; ++i) put(ram,0x7dc2 + 2*i,0xe100,2);
    state = initial(0x478f0);
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(state.d0 == 0xffff0000 && state.d1 == 0xffff0000 && state.d2 == 0xffff0000 && state.d3 == 0x98760000);
    assert(get(ram,0xb30) == 0x4790a && get(ram,0xbAA,2) == 15 && ram[0x7dd4] == 0);
    // Signed remainder occupies the highword, including negative remainder.
    ram.assign(65536,0); put(ram,0x7dc2,0xe102,2);
    state = initial(0x478f0);
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(state.d0 == 0xfffe0000 && state.d1 == 0x0000fe10 && state.d3 == 16);
    state = initial(0x478de); ram[0x7ded] = 0x80;
    const std::vector<std::uint8_t> wait_ram = ram;
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(state.next_pc == 0x478de && state.d0 == 0x12345600 && ram == wait_ram && ports.empty());
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(ram == wait_ram && ports.empty());
    ram[0x7ded] = 0x7f;
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(state.next_pc == 0x479b0 && ports.size() == 1283);
    assert(ports[0].size == 1 && ports[0].address == 0x300001 && ports[0].value == 0);
    assert(ports[1].value == 0x70007000 && ports[1280].value == 0x74ff7000);
    assert(ports[1281].address == 0x3c0004 && ports[1282].value == 0x82000000);
    assert(state.d0 == 0x12347500 && state.d1 == 0xabcd7000 && state.d2 == 0x76540000 && state.d3 == 32);
    state = initial(0x4790a); put(ram,0xbaa,0,2);
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(get(ram,0xbaa,2) == 0xffff && state.next_pc == 0x479b0 && ports.size() == 1283);
    ram.assign(65536,0); state = initial(0x4791c);
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(state.next_pc == 0x480bc && get(ram,0xbaa,2) == 59 && ram[0x7dd4] == 30 && !ports.empty());
    ram.assign(65536,0); state = initial(0x47934);
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(get(ram,0xb30) == 0x478de && state.next_pc == 0x480bc && ports.empty());
    // Successful third allocation copies live globals and falls through gate.
    ram.assign(65536,0); allocator(ram,0x101800);
    put(ram,0xd690,0x1234,2); put(ram,0xd692,0x5678,2);
    state = initial(0x47964);
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(get(ram,0x1800) == 0x4ff4c && get(ram,0x1876) == 0x12345678);
    assert(get(ram,0xb30) == 0x4798e && ram[0xb92] == 0 && state.d0 == 0x12340005 && state.d1 == 0xabcdefff);
    state = initial(0x4798e);
    assert(ms5::step_stage_transition(ram,state,ports,error));
    assert(state.d0 == 0x12345678 && state.next_pc == 0x480bc);
    ram[0xb92] = 1;
    assert(ms5::step_stage_transition(ram,state = initial(0x4798e),ports,error));
    assert(get(ram,0xb30) == 0x479b0 && state.next_pc == 0x480bc);
    // Extra copy span fails after allocator's candidate mutations; everything rolls back.
    ram.assign(65536,0); allocator(ram,0x10ff90); state = initial(0x47964);
    ms5::VideoPortWrite sentinel = {0x1234,0x5678,2}; ports.assign(1,sentinel);
    const std::vector<std::uint8_t> before = ram; const ms5::StageTransitionState old = state;
    assert(!ms5::step_stage_transition(ram,state,ports,error));
    assert(ram == before && same(state,old) && ports.size() == 1 && ports[0].value == 0x5678);
    state = initial(0x480bc);
    const ms5::StageTransitionState invalid = state;
    assert(!ms5::step_stage_transition(ram,state,ports,error));
    assert(ram == before && same(state,invalid) && ports[0].value == 0x5678);
    std::cout << "stage_transition_test: passed\n";
}
