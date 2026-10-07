#include "ms5/game_objects.h"
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
bool second(std::vector<std::uint8_t>& ram, std::size_t object, std::uint32_t& d0, std::string& error) {
    if (longword(ram,object) == 0x270e) return true;
    put_long(ram,object,0x1d1f4); ram[object + 0x15] = 0; ram[object + 0x61] = 0x80;
    ram[object + 0xa8] |= 0x10; ram[object + 0x81] = 0; ram[object + 0x82] = 0;
    const std::uint16_t selector = word(ram,object + 0x78);
    d0 = (d0 & 0xffff0000U) | selector;
    ram[selector == 0 ? 0xd487 : 0xd48f] = 0;
    const std::uint32_t pointer = longword(ram,object + 0x8c);
    if ((pointer & 1U) != 0 || pointer < 0x100000 || pointer > 0x110000 - 0x0c) {
        error = "game object live pointer requires aligned 12-byte RAM span"; return false;
    }
    const std::size_t at = pointer - 0x100000;
    ram[at + 2] = 0; ram[at + 1] = 0; put_word(ram,at + 0x0a,0);
    return true;
}
bool first(std::vector<std::uint8_t>& ram, std::size_t object, std::uint32_t& d0, std::string& error) {
    if (longword(ram,object) == 0x270e) return true;
    ram[object + 0x9e] = 0; ram[object + 0xa0] = 0; ram[object + 0x9f] = 0; ram[object + 0xa1] = 0;
    const std::uint16_t selector = word(ram,object + 0x78);
    d0 = (d0 & 0xffff0000U) | selector;
    const std::size_t chosen = selector == 0 ? 0xd450 : 0xd460;
    put_long(ram,object + 0x8c,static_cast<std::uint32_t>(0x100000 + chosen));
    ram[chosen + 6] = 1; ram[chosen + 7] = 10; ram[chosen + 4] = 0; ram[chosen + 5] = 0;
    put_word(ram,chosen + 0x0c,0xffff); ram[chosen + 3] = 255;
    d0 = (d0 & 0xffff0000U) | (selector & 1U);
    const std::size_t parity = (selector & 1U) == 0 ? 0xd450 : 0xd460;
    ram[parity] = 0; put_word(ram,parity + 8,0);
    return second(ram,object,d0,error);
}
}
bool reset_game_objects(std::vector<std::uint8_t>& ram, std::uint32_t entry,
                        std::uint32_t& d0, std::string& error) {
    if (ram.size() != 65536 || (entry != 0x1bcfe && entry != 0x1bd12)) {
        error = "game object reset requires 64KiB RAM and entry 1bcfe/1bd12"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; std::uint32_t next = d0;
        if (entry == 0x1bcfe && (!first(candidate,0x0cb8,next,error) || !first(candidate,0x0da8,next,error))) return false;
        put_word(candidate,0xd478,0); put_long(candidate,0xd474,0);
        if (!second(candidate,0x0cb8,next,error) || !second(candidate,0x0da8,next,error)) return false;
        ram.swap(candidate); d0 = next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate game object reset transaction"; return false; }
}
}
