#include "ms5/object_allocation.h"
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
bool pointer(std::uint32_t address, std::size_t span, std::size_t& offset, std::string& error) {
    if ((address & 1U) != 0 || address < 0x100000U || address > 0x110000U - span) {
        error = "object allocation dereference requires aligned complete CPU RAM span"; return false;
    }
    offset = address - 0x100000U; return true;
}
}
bool allocate_object(std::vector<std::uint8_t>& ram, AllocationState& state, std::string& error) {
    if (ram.size() != 65536) { error = "object allocation requires exactly 64KiB RAM"; return false; }
    if ((state.d0 & 65535U) >= word(ram,0x4ca0) || state.a0 == 0) {
        state.a0 = 0x100e98; state.carry = false; error.clear(); return true;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; AllocationState next = state;
        const std::uint32_t node_address = longword(candidate,0x4c9c);
        std::size_t node = 0, parent = 0, successor = 0;
        if (!pointer(node_address,0x6b,node,error)) return false;
        put_long(candidate,0x4c9c,longword(candidate,node + 8));
        put_word(candidate,0x4ca0,static_cast<std::uint16_t>(word(candidate,0x4ca0) - 1U));
        put_long(candidate,node + 0x0c,next.a6);
        if (!pointer(next.a6,0x6b,parent,error)) return false;
        next.d0 = (next.d0 & 0xffff0000U) | static_cast<std::uint16_t>(word(candidate,parent + 0x10) + 1U);
        put_word(candidate,node + 0x10,static_cast<std::uint16_t>(next.d0));
        next.a1 = longword(candidate,parent + 8);
        put_long(candidate,node + 4,next.a6);
        put_long(candidate,node + 8,next.a1);
        if (!pointer(next.a1,8,successor,error)) return false;
        put_long(candidate,successor + 4,node_address);
        put_long(candidate,parent + 8,node_address);
        put_long(candidate,node,next.a0);
        candidate[node + 0x6a] = candidate[parent + 0x6a];
        next.a0 = node_address; next.carry = true;
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate object allocation transaction"; return false; }
}
bool request_game_object(std::vector<std::uint8_t>& ram, AllocationState& state, std::string& error) {
    if (ram.size() != 65536) { error = "game object request requires exactly 64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; AllocationState next = state;
        if (candidate[0xfd82] != 0 && candidate[1] == 1) {
            next.a0 = 0x4fb64; next.d0 &= 0xffff0000U;
            if (!allocate_object(candidate,next,error)) return false;
        } else next.carry = false;
        std::size_t parent = 0;
        if (!pointer(next.a6,0x63,parent,error)) return false;
        candidate[parent + 0x62] = next.carry ? 0 : 255;
        ram.swap(candidate); state = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate game object request transaction"; return false; }
}

}
