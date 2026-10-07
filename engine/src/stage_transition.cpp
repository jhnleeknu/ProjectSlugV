#include "ms5/stage_transition.h"
#include "ms5/palette_control.h"
#include "ms5/game_screen_reset.h"
#include "ms5/object_allocation.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void put_long(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    put_word(ram,at,static_cast<std::uint16_t>(value >> 16)); put_word(ram,at + 2,static_cast<std::uint16_t>(value));
}
std::int32_t signed_word(std::uint16_t value) {
    return value < 0x8000 ? static_cast<std::int32_t>(value) : static_cast<std::int32_t>(value) - 65536;
}
bool effect(std::vector<std::uint8_t>& ram, StageTransitionState& state, bool bright,
            unsigned int duration, std::string& error) {
    const std::uint16_t target = bright ? 0x1f00 : 0xe100;
    std::int32_t deltas[3]; bool changed = false;
    for (unsigned int i = 0; i < 3; ++i) {
        deltas[i] = signed_word(static_cast<std::uint16_t>(target - word(ram,0x7dc2 + 2*i)));
        changed = changed || deltas[i] != 0;
    }
    state.d0 = state.d1 = state.d2 = bright ? 31U : 0xffffffe1U;
    state.d3 = (state.d3 & 0xffff0000U) | duration;
    const std::uint16_t channel = bright ? 31 : 0xffe1;
    if (!set_palette_effect(ram,channel,channel,channel,static_cast<std::uint8_t>(duration),error)) return false;
    std::uint32_t* regs[3] = {&state.d0,&state.d1,&state.d2};
    if (!changed) {
        for (unsigned int i = 0; i < 3; ++i) *regs[i] &= 0xffff0000U;
        state.d3 &= 0xffff0000U;
    } else {
        state.d3 = duration == 0 ? 1 : duration;
        for (unsigned int i = 0; i < 3; ++i) {
            const std::int32_t divisor = static_cast<std::int32_t>(state.d3);
            const std::uint16_t quotient = static_cast<std::uint16_t>(deltas[i] / divisor);
            const std::uint16_t remainder = static_cast<std::uint16_t>(deltas[i] % divisor);
            *regs[i] = (static_cast<std::uint32_t>(remainder) << 16) | quotient;
        }
    }
    return true;
}
void append(std::vector<VideoPortWrite>& ports, std::uint8_t size, std::uint32_t address, std::uint32_t value) {
    VideoPortWrite write; write.size = size; write.address = address; write.value = value; ports.push_back(write);
}
void clear_screen(StageTransitionState& state, std::vector<VideoPortWrite>& ports) {
    append(ports,1,0x300001,0);
    for (unsigned int col = 0; col < 40; ++col) {
        for (unsigned int row = 0; row < 32; ++row) append(ports,4,0x3c0000,((0x7000U + col*32U + row) << 16) | 0x7000U);
    }
    append(ports,2,0x3c0004,0); append(ports,4,0x3c0000,0x82000000);
    state.d0 = (state.d0 & 0xffff0000U) | 0x7500;
    state.d1 = (state.d1 & 0xffff0000U) | 0x7000;
    state.d2 &= 0xffff0000U; state.d3 = 0x20; state.next_pc = 0x479b0;
}
bool supported(std::uint32_t pc) {
    return pc == 0x478c4 || pc == 0x478f0 || pc == 0x4791c || pc == 0x47934 ||
        pc == 0x4794c || pc == 0x47964 || pc == 0x478de || pc == 0x4790a || pc == 0x4798e;
}
}
bool step_stage_transition(std::vector<std::uint8_t>& ram, StageTransitionState& state,
                           std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || !supported(state.next_pc) || (state.a6 & 1U) ||
        state.a6 < 0x100000 || state.a6 > 0x110000 - 0xc4) {
        error = "invalid stage transition RAM, entry or object span"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; StageTransitionState next = state;
        std::vector<VideoPortWrite> output; const std::size_t object = next.a6 - 0x100000;
        std::uint32_t pc = next.next_pc;
        if (pc == 0x47934 || pc == 0x4794c || pc == 0x47964) {
            AllocationState allocation; allocation.d0 = next.d0 & 0xffff0000U;
            allocation.a0 = pc == 0x47934 ? 0x4fcb8 : (pc == 0x4794c ? 0x4fd0a : 0x4ff4c);
            allocation.a6 = next.a6;
            if (!allocate_object(candidate,allocation,error)) return false;
            next.d0 = allocation.d0;
            if (!allocation.carry) pc = 0x478c4;
            else {
                if (pc == 0x47964) {
                    if ((allocation.a0 & 1U) || allocation.a0 < 0x100000 || allocation.a0 > 0x110000 - 0x7a) {
                        error = "allocated stage object requires aligned 7a-byte RAM span"; return false;
                    }
                    const std::size_t child = allocation.a0 - 0x100000;
                    put_word(candidate,child + 0x76,word(candidate,0xd690));
                    put_word(candidate,child + 0x78,word(candidate,0xd692));
                }
                candidate[object + 0x62] = 0; put_long(candidate,object,0x4798e); pc = 0x4798e;
            }
        }
        if (pc == 0x478c4) {
            if (!effect(candidate,next,false,0,error)) return false;
            put_long(candidate,object,0x478de); next.next_pc = 0x480bc;
        } else if (pc == 0x478f0 || pc == 0x4791c) {
            const bool bright = pc == 0x4791c;
            if (bright) {
                std::vector<VideoPortWrite> screen;
                if (!reset_game_screen(candidate,0xcaf0,next.d0,next.d1,next.d3,screen,error)) return false;
                output.insert(output.end(),screen.begin(),screen.end()); next.d2 = 0;
            }
            put_word(candidate,object + 0x7a,bright ? 0x3c : 0x10);
            if (!effect(candidate,next,bright,bright ? 0x1e : 0x10,error)) return false;
            put_long(candidate,object,0x4790a); pc = 0x4790a;
        }
        if (pc == 0x4790a) {
            const std::uint16_t old = word(candidate,object + 0x7a);
            put_word(candidate,object + 0x7a,static_cast<std::uint16_t>(old - 1U));
            if (old != 0) next.next_pc = 0x480bc;
            else clear_screen(next,output);
        } else if (pc == 0x478de) {
            const std::uint8_t old = candidate[0x7ded];
            next.d0 = (next.d0 & 0xffffff00U) | static_cast<std::uint8_t>(old - 0x80);
            if (old >= 0x80) next.next_pc = 0x478de;
            else clear_screen(next,output);
        } else if (pc == 0x4798e) {
            if (candidate[object + 0x62] != 0) {
                if (!effect(candidate,next,false,0,error)) return false;
                put_long(candidate,object,0x479b0);
            }
            next.next_pc = 0x480bc;
        }
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage transition transaction"; return false; }
}
}
