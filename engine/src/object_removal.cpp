#include "ms5/object_removal.h"
#include "ms5/object_state.h"
#include "ms5/palette_allocator.h"
#include "ms5/position_state.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram,at)) << 16) | word(ram,at + 2);
}
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void put_long(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    put_word(ram,at,static_cast<std::uint16_t>(value >> 16)); put_word(ram,at + 2,static_cast<std::uint16_t>(value));
}
bool object(std::uint32_t address, std::size_t& offset, std::string& error) {
    if ((address & 1U) != 0 || address < 0x100000U || address > 0x110000U - 0xc4U) {
        error = "removal object requires aligned c4-byte CPU RAM span"; return false;
    }
    offset = address - 0x100000U; return true;
}
bool step(unsigned int& budget, std::string& error) {
    if (budget == 0) { error = "object removal operation budget exhausted"; return false; }
    --budget; return true;
}
void reset(std::vector<std::uint8_t>& ram, std::size_t at, RemovalState& state) {
    reset_object_fields(&ram[at],ram.size() - at); state.d0 = 0; state.d1 = 0xffffffffU;
}
bool remove_one(std::vector<std::uint8_t>& ram, RemovalState& state,
                std::vector<VideoPortWrite>& ports, unsigned int& budget, std::string& error) {
    std::size_t at = 0;
    if (!step(budget,error) || !object(state.a6,at,error)) return false;
    VideoPortWrite watchdog; watchdog.size = 1; watchdog.address = 0x300001;
    watchdog.value = static_cast<std::uint8_t>(state.d0); ports.push_back(watchdog);
    if (!release_palettes(ram,at,error,&state.d3,&state.d1)) return false;
    const std::uint8_t index = ram[at + 0x6c]; state.d0 = index;
    if ((index & 0x80U) == 0) {
        if (index >= 8) { error = "removal coordinate index must be below eight or bit7 set"; return false; }
        const std::size_t coordinate = 0xd4e6U + index * 0x2cU;
        put_word(ram,coordinate + 0x26,0xffff); put_word(ram,coordinate + 0x2a,2); ram[at + 0x6c] = 255;
        state.d3 = longword(ram,coordinate + 0x18);
        if (!update_position(&ram[0],ram.size(),static_cast<std::uint32_t>(coordinate + 0x100000),false,error)) return false;
        state.d0 = longword(ram,coordinate + 0x14); state.d1 = longword(ram,coordinate + 0x18);
    }
    put_long(ram,at,0x270e);
    if (word(ram,at + 0x10) == 0) { reset(ram,at,state); return true; }
    for (;;) {
        if (!step(budget,error) || !object(state.a6,at,error)) return false;
        std::size_t next = 0;
        const std::uint32_t next_address = longword(ram,at + 8);
        state.d0 = (state.d0 & 0xffff0000U) | word(ram,at + 0x10);
        if (!object(next_address,next,error)) return false;
        if ((state.d0 & 65535U) < word(ram,next + 0x10)) return true;
        reset(ram,at,state);
        const std::uint32_t previous_address = longword(ram,at + 4);
        const std::uint32_t live_next_address = longword(ram,at + 8);
        std::size_t previous = 0;
        if (!object(previous_address,previous,error) || !object(live_next_address,next,error)) return false;
        put_long(ram,next + 4,previous_address); put_long(ram,previous + 8,live_next_address);
        put_long(ram,at + 8,longword(ram,0x4c9c)); put_long(ram,0x4c9c,state.a6);
        put_word(ram,0x4ca0,static_cast<std::uint16_t>(word(ram,0x4ca0) + 1U));
        state.a6 = previous_address;
        if (longword(ram,previous) != 0x270e || word(ram,previous + 0x10) == 0) return true;
    }
}
bool children(std::vector<std::uint8_t>& ram, RemovalState& state,
              std::vector<VideoPortWrite>& ports, unsigned int& budget, std::string& error) {
    for (;;) {
        std::size_t at = 0, next = 0;
        if (!step(budget,error) || !object(state.a6,at,error)) return false;
        state.d0 = (state.d0 & 0xffff0000U) | word(ram,at + 0x10);
        state.a6 = longword(ram,at + 8);
        if (!object(state.a6,next,error)) return false;
        if ((state.d0 & 65535U) >= word(ram,next + 0x10)) {
            state.a6 = longword(ram,next + 4); return true;
        }
        if (!remove_one(ram,state,ports,budget,error)) return false;
    }
}
bool target_group(std::vector<std::uint8_t>& ram, std::uint32_t target, RemovalState& state,
                  std::vector<VideoPortWrite>& ports, unsigned int& budget, std::string& error) {
    std::size_t at = 0, destination = 0;
    if (!object(state.a6,at,error) || !object(target,destination,error)) return false;
    if (word(ram,at + 0x10) != 0 || word(ram,destination + 0x10) != 0) {
        error = "original 2a84 depth-zero TRAP is unsupported"; return false;
    }
    const std::uint32_t saved = state.a6; state.a6 = target;
    if (!children(ram,state,ports,budget,error) || !remove_one(ram,state,ports,budget,error)) return false;
    state.a6 = saved; return true;
}
}
bool remove_objects(std::vector<std::uint8_t>& ram, std::uint32_t entry,
                    std::uint32_t target, RemovalState& state,
                    std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || (entry != 0x299c && entry != 0x2a0a && entry != 0x2a84 && entry != 0xc4cc)) {
        error = "removal requires 64KiB RAM and supported native entry"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; RemovalState next = state;
        std::vector<VideoPortWrite> output; unsigned int budget = 65536;
        bool okay = false;
        if (entry == 0x299c) okay = remove_one(candidate,next,output,budget,error);
        else if (entry == 0x2a0a) okay = children(candidate,next,output,budget,error);
        else if (entry == 0x2a84) okay = target_group(candidate,target,next,output,budget,error);
        else {
            candidate[0x4d91] &= 0xef; put_long(candidate,6,0x3dcc); put_long(candidate,10,0x3dcc);
            if (!children(candidate,next,output,budget,error)) return false;
            std::size_t at = 0;
            if (!object(next.a6,at,error)) return false;
            std::uint32_t current = longword(candidate,at + 8);
            while (current != 0x100820) {
                if (!step(budget,error) || !object(current,at,error)) return false;
                const std::uint32_t saved = current;
                if (!target_group(candidate,current,next,output,budget,error)) return false;
                if (!object(saved,at,error)) return false;
                current = longword(candidate,at + 8);
            }
            okay = true;
        }
        if (!okay) return false;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate object removal transaction"; return false; }
}
}
