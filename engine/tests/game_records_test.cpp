#include "ms5/game_records.h"
#include <cstdlib>
#include <iostream>
namespace {
void require(bool condition, const char* message) {
    if (!condition) { std::cerr << message << '\n'; std::exit(1); }
}
ms5::FixedDataResource fixture() {
    ms5::FixedDataResource records; records.source_cpu_address = 0x4cf64; records.source_rom_offset = 0x4cf64;
    records.data.resize(320);
    for (unsigned int record = 0; record < 20; ++record) {
        for (unsigned int byte = 0; byte < 16; ++byte) records.data[record * 16 + byte] = static_cast<std::uint8_t>(record * 7 + byte);
    }
    return records;
}
void fails(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& resource,
           std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3) {
    const std::vector<std::uint8_t> before = ram; const std::uint32_t old0 = d0, old1 = d1, old3 = d3; std::string error;
    require(!ms5::configure_game_record(ram,resource,d0,d1,d3,error),"expected record failure");
    require(ram == before && d0 == old0 && d1 == old1 && d3 == old3 && !error.empty(),"record failure rollback");
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0xa5); ms5::FixedDataResource records = fixture(); std::string error;
    for (unsigned int selector = 0; selector < 4; ++selector) {
        for (unsigned int index = 0; index < 20; ++index) {
            ram.assign(65536,0xa5);
            std::uint32_t d0 = 0xabcd8000U | selector, d1 = 0xffff0000U | index, d3 = 0x98761234U;
            require(ms5::configure_game_record(ram,records,d0,d1,d3,error),"configure all indices/selectors");
            const unsigned int source = index * 16, destination = (selector & 1U) == 0 ? 0xd694 : 0xd69c;
            const unsigned int word_a = (static_cast<unsigned int>(records.data[source + 10]) << 8) | records.data[source + 11];
            const unsigned int word_c = (static_cast<unsigned int>(records.data[source + 12]) << 8) | records.data[source + 13];
            require(d0 == (0xabcd0000U | index) && d1 == word_c && d3 == (0x98760000U | word_a),"full register widths");
            require(ram[destination] == index && ram[destination + 1] == records.data[source + 2] &&
                ram[destination + 2] == records.data[source + 1] && ram[destination + 3] == records.data[source + 13],"byte mapping");
            for (unsigned int byte = 0; byte < 4; ++byte) {
                require(ram[destination + 4 + byte] == records.data[source + (byte < 2 ? 10 : 12) + byte],"word mapping");
            }
            for (unsigned int at = 0; at < 65536; ++at) {
                if (at < destination || at >= destination + 8) require(ram[at] == 0xa5,"record preserves unrelated RAM");
            }
        }
    }
    std::uint32_t d0 = 0x12345678, d1 = 20, d3 = 0x87654321; fails(ram,records,d0,d1,d3);
    d1 = 0xffff; fails(ram,records,d0,d1,d3); d1 = 19;
    ms5::FixedDataResource bad = records; bad.data.pop_back(); fails(ram,bad,d0,d1,d3);
    bad = records; bad.source_cpu_address++; fails(ram,bad,d0,d1,d3);
    bad = records; bad.source_rom_offset++; fails(ram,bad,d0,d1,d3);
    ram.resize(65535); fails(ram,records,d0,d1,d3);
    std::cout << "Game record mapping, unsigned trap boundary and register widths passed\n";
}
