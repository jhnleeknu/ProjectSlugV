#include "ms5/random_state.h"
namespace ms5 {
namespace {
const std::size_t begin = 0xd6b4U;
const std::size_t cursor_offset = 0xd722U;
std::uint16_t read_word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<std::uint16_t>(ram[at]) << 8) | ram[at+1]);
}
void write_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at+1] = static_cast<std::uint8_t>(value);
}
std::uint32_t read_long(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(read_word(ram,at)) << 16) | read_word(ram,at+2);
}
void write_long(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    write_word(ram,at,static_cast<std::uint16_t>(value >> 16));
    write_word(ram,at+2,static_cast<std::uint16_t>(value));
}
bool valid_ram(const std::vector<std::uint8_t>& ram, std::string& error) {
    if (ram.size()!=65536U) {error="random state requires exactly 64 KiB RAM";return false;}
    return true;
}
}
bool seed_random(std::vector<std::uint8_t>& ram, std::uint32_t& d0,
                 std::uint32_t& d1, std::string& error) {
    if (!valid_ram(ram,error)) return false;
    std::uint32_t first=d0,second=d1;
    if ((first&0xffffU)!=0U) {
        const std::uint16_t seed=static_cast<std::uint16_t>(read_word(ram,0xf02cU)+1U);
        first=(first&0xffff0000U)|seed;
        write_word(ram,0xf02cU,seed);
    }
    second=(second&0xffff0000U)|(first&0xffffU);
    for (unsigned int index=0;index<55U;++index) {
        const std::uint32_t word=(second+0x7925U+(first&0xffffU))&0xffffU;
        second=(word*word)>>8;
        const std::uint32_t previous=first;
        first=second;second=previous;
        write_word(ram,begin+index*2U,static_cast<std::uint16_t>(first));
    }
    write_long(ram,cursor_offset,0x10d720U);
    d0=first;d1=second;error.clear();return true;
}
bool next_random(std::vector<std::uint8_t>& ram, std::uint32_t& d0,
                 std::string& error) {
    if (!valid_ram(ram,error)) return false;
    const std::uint32_t address=read_long(ram,cursor_offset);
    if (address<0x10d6b4U || address>0x10d720U || (address&1U)!=0U) {
        error="random cursor must be even within CPU10d6b4..10d720";return false;
    }
    const std::uint16_t old=read_word(ram,address-0x100000U);
    std::uint32_t next=address+2U;
    if (next>=0x10d722U) next-=0x6eU;
    std::uint32_t target=next+0x2eU;
    if (target>=0x10d722U) target-=0x6eU;
    const std::size_t at=target-0x100000U;
    write_long(ram,cursor_offset,next);
    write_word(ram,at,static_cast<std::uint16_t>(read_word(ram,at)-old));
    d0=(d0&0xffff0000U)|old;error.clear();return true;
}
bool scale_random(std::vector<std::uint8_t>& ram, std::uint32_t& d0,
                  std::string& error) {
    const std::uint32_t limit=d0&0xffffU;
    std::uint32_t value=d0;
    if (!next_random(ram,value,error)) return false;
    const std::uint32_t product=(value&0xffffU)*limit;
    d0=(product<<16)|(product>>16);error.clear();return true;
}
}
