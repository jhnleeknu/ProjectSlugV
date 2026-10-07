#include "ms5/scene_initialization.h"
#include <cstdlib>
#include <iostream>
namespace {
void require(bool condition, const char* message) {
    if (!condition) { std::cerr << message << '\n'; std::exit(1); }
}
void word(std::vector<std::uint8_t>& bytes, unsigned int at, unsigned int value) {
    bytes[at] = static_cast<std::uint8_t>(value >> 8); bytes[at + 1] = static_cast<std::uint8_t>(value);
}
void put(std::vector<std::uint8_t>& bytes, unsigned int at, std::uint32_t value) {
    word(bytes,at,value >> 16); word(bytes,at + 2,value);
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) | (static_cast<std::uint32_t>(ram[at + 1]) << 16) |
        (static_cast<std::uint32_t>(ram[at + 2]) << 8) | ram[at + 3];
}
ms5::FixedDataResource fixture() {
    ms5::FixedDataResource result; result.source_cpu_address = result.source_rom_offset = 0x1af12;
    result.data.assign(512,0); word(result.data,88 * 2,0x1111); word(result.data,89 * 2,0x2222);
    word(result.data,0xc2,0x4000); word(result.data,0xc4,0x8000); word(result.data,0xc6,0xc000); return result;
}
void fails(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& tables, bool debug) {
    const std::vector<std::uint8_t> before = ram; std::uint32_t d0 = 0x12345678, d1 = 0x87654321, d3 = 0xabcdef01;
    std::vector<ms5::VideoPortWrite> ports(1); ports[0].value = 0x3456; std::string error;
    const bool okay = debug ? ms5::update_scene_debug(ram,tables,d0,d1,d3,ports,error) : ms5::initialize_stage_scene(ram,tables,d0,d1,d3,ports,error);
    require(!okay && !error.empty() && ram == before && d0 == 0x12345678 && d1 == 0x87654321 && d3 == 0xabcdef01 &&
        ports.size() == 1 && ports[0].value == 0x3456,"scene initializer/debug rollback");
}
}
int main() {
    ms5::FixedDataResource tables = fixture(); std::vector<std::uint8_t> ram(65536,0);
    std::uint32_t d0 = 0x12345678, d1 = 0x87654321, d3 = 0xabcdef01; std::vector<ms5::VideoPortWrite> ports; std::string error;
    require(ms5::update_scene_debug(ram,tables,d0,d1,d3,ports,error) && d0 == 0x12345678 && d1 == 0x87654321 && d3 == 0xabcdef01 && ports.empty(),"debug disabled stable preserves regs");
    ram[0xd44e] = 255;
    require(ms5::update_scene_debug(ram,tables,d0,d1,d3,ports,error) && ports.size() == 2072 && ram[0xd44e] == 0 &&
        d0 == 0x75807500 && d1 == 0x7000 && d3 == 32,"disable transition actual screen reset");
    ram.assign(65536,0); ram[0xf000] = 24; d0 = 0x12345678; d1 = 0x87654321; d3 = 0xabcdef01;
    for (unsigned int at = 0xb1d6 + 0x80; at < 0xb1d6 + 0x2080; at += 2) word(ram,at,1);
    require(ms5::update_scene_debug(ram,tables,d0,d1,d3,ports,error) && ports.size() == 1280 &&
        ports.front().value == (0x74ff0000U | 0x1111) && ports.back().value == (0x70000000U | 0x1111) &&
        d0 == 0x12340080 && d1 == 0x87650000 && d3 == 0xabcdffff && ram[0xd44e] == 255,"first node priority and descending raster/register widths");
    word(tables.data,88 * 2,0x320); ram[0xd44e] = 0;
    require(ms5::update_scene_debug(ram,tables,d0,d1,d3,ports,error) && (ports.back().value & 65535U) == 0x2222,"transparent first falls through second node");
    // Native mistakenly repeats the first node, even though the second LEA writesA1.
    ram[0xd44e] = 255; put(ram,0xb1ea,0x80000); put(ram,0xb1f2,0);
    require(ms5::update_scene_debug(ram,tables,d0,d1,d3,ports,error) && ports.empty() && d0 == 0 && d1 == 0 && d3 == 0,"second-only movement does not redraw");
    put(ram,0x9172,8);
    require(ms5::update_scene_debug(ram,tables,d0,d1,d3,ports,error) && ports.size() == 1280 && d3 == 0xffff,"stickyZ requires X equality too");
    put(ram,0x916a,0x80000); put(ram,0x9172,0); put(ram,0x9176,0);
    require(ms5::update_scene_debug(ram,tables,d0,d1,d3,ports,error) && d3 == 0xffffffffU,"SUBX borrow retained in full D3 before raster lowword");
    // Null-script initializer fixes nodes and fields while preserving metadata+d.
    tables = fixture(); ram.assign(65536,0xa5); ram[0xf000] = 0; d0 = 1; d1 = 2; d3 = 3;
    require(ms5::initialize_stage_scene(ram,tables,d0,d1,d3,ports,error) && d0 == 0 && d1 == 0x01000000 && d3 == 0x01000000 && ports.size() == 4,"null-script prefix final registers/bank-only ports");
    require(ports[0].address == 0x2ffff2 && ports[0].value == 0x2000 && ports[1].address == 0x2ffff0 && ports[1].value == 0 &&
        ports[2].address == 0x2ffff2 && ports[2].value == 0x1000 && ports[3].address == 0x2ffff0 && ports[3].value == 0,"ordered bank enter/restore");
    require(get(ram,0xd38e) == 0 && get(ram,0xd392) == 0x01000000 && get(ram,0xd396) == 0 && get(ram,0xd39a) == 0 &&
        ram[0xd427] == 0xa0 && ram[0xd429] == 0x80 && ram[0x10] == 0 && ram[0x11] == 0 && ram[0xd363] == 0xa5 && ram[0xd362] == 0x10 &&
        ram[0xd44f] == 0xa5 && ram[0x9156 + 0x7a] == 6,"explicit defaults and preserved gaps");
    for (unsigned int at = 0x9156 + 0x80; at < 0x9156 + 0x2080; ++at) require(ram[at] == 0,"first tile buffer clear");
    for (unsigned int at = 0xb1d6 + 0x80; at < 0xb1d6 + 0x2080; ++at) require(ram[at] == 0,"second tile buffer clear");
    ram.assign(65536,0); ram[0xf000] = 8;
    require(ms5::initialize_stage_scene(ram,tables,d0,d1,d3,ports,error) && ports.size() == 1284 && ports[2].address == 0x3c0000 &&
        ports[2].value == (0x74ff0000U | 0x1111) && ports[1281].value == (0x70000000U | 0x1111) && ports[1282].value == 0x1000,"debug draw remains between ordered bank changes");
    ms5::FixedDataResource bad = tables; bad.data.pop_back(); fails(ram,bad,false); fails(ram,bad,true);
    bad = tables; bad.source_cpu_address++; fails(ram,bad,false); bad = tables; bad.source_rom_offset++; fails(ram,bad,true);
    ram.resize(65535); fails(ram,tables,false); fails(ram,tables,true);
    std::cout << "Scene null-script initializer/debug gate, lookup priority and transaction passed\n";
}
