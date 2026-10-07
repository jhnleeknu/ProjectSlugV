#include "ms5/game_records.h"
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(bytes[at]) << 8) | bytes[at + 1]);
}
void put(std::vector<std::uint8_t>& bytes, std::size_t at, std::uint16_t value) {
    bytes[at] = static_cast<std::uint8_t>(value >> 8); bytes[at + 1] = static_cast<std::uint8_t>(value);
}
}
bool configure_game_record(std::vector<std::uint8_t>& ram, const FixedDataResource& records,
                           std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3,
                           std::string& error) {
    const unsigned int index = d1 & 65535U;
    if (ram.size() != 65536 || records.source_cpu_address != 0x4cf64 || records.source_rom_offset != 0x4cf64 ||
        records.data.size() != 320 || index >= 20) {
        error = "game record requires 64KiB RAM, 320-byte window at 4cf64 and unsigned index below 20"; return false;
    }
    const std::size_t destination = (d0 & 1U) == 0 ? 0xd694 : 0xd69c;
    const std::size_t source = index * 16;
    const std::uint16_t value_a = word(records.data,source + 10);
    const std::uint16_t value_c = word(records.data,source + 12);
    const std::uint16_t value_e = word(records.data,source + 14);
    ram[destination] = static_cast<std::uint8_t>(index);
    ram[destination + 3] = static_cast<std::uint8_t>(value_c);
    ram[destination + 2] = records.data[source + 1];
    put(ram,destination + 4,value_a); put(ram,destination + 6,value_e);
    ram[destination + 1] = records.data[source + 2];
    d0 = (d0 & 0xffff0000U) | index; d1 = value_c; d3 = (d3 & 0xffff0000U) | value_a;
    error.clear(); return true;
}
}
