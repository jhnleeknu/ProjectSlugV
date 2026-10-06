#include "ms5/sprite_prepare_queue.h"
#include <cstdlib>
#include <iostream>

static void require(bool value, const char* message) {
    if (!value) { std::cerr << message << '\n'; std::exit(1); }
}
static void put(std::vector<std::uint8_t>& ram, std::size_t at, unsigned value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at+1] = static_cast<std::uint8_t>(value);
}
static std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536, 0);
    ram[0x8d3c] = 128;
    put(ram, 0x8d38, 4); put(ram, 0x8d3a, 4);
    put(ram, 0x8d40, 190); put(ram, 0x8d44, 190);
    put(ram, 0x8d46, 190); put(ram, 0x8d48, 380);
    put(ram, 0x8d4a, 190); put(ram, 0x8d4c, 380);
    for (unsigned i = 0; i < 2; ++i) {
        put(ram, 0x8b34+i*2, 12*(i+1));
        const unsigned record = 0x7f34+12*(i+1);
        put(ram, record, i); put(ram, record+2, 160*64);
        put(ram, record+4, 0xffff); put(ram, record+6, 0x1500);
        put(ram, record+10, 0x2152);
    }
    return ram;
}
static void reject(std::vector<std::uint8_t> ram,
                   const std::vector<ms5::CompositionResource>& resources) {
    const std::vector<std::uint8_t> before = ram;
    std::vector<ms5::SpriteWrite> writes(1);
    writes[0].address = 123; writes[0].value = 456;
    std::string error;
    require(!ms5::prepare_sprite_queue(ram, resources, writes, error), "invalid state accepted");
    require(ram == before && writes.size() == 1 && writes[0].address == 123 &&
            writes[0].value == 456 && !error.empty(), "error changed caller state");
}
int main() {
    ms5::CompositionResource resource;
    resource.id = 0x2152; resource.source_rom_offset = 0;
    const std::uint8_t data[] = {1,0,0,0,0,0,1,1,0,0,0,1};
    resource.data.assign(data, data+12);
    std::vector<ms5::CompositionResource> resources(1, resource);
    std::vector<std::uint8_t> ram = fixture();
    std::vector<ms5::SpriteWrite> writes;
    std::string error;
    require(ms5::prepare_sprite_queue(ram, resources, writes, error), "valid preparation failed");
    require(writes.size() == 8 && ram[0x8d3d] == 255 && ram[0x8d37] == 4 &&
            ram[0x8d39] == 4 && ram[0x8d35] == 0 && ram[0x8d3c] == 128, "wrong prepared state");
    ram = fixture(); put(ram, 0x8d34, 2); reject(ram, resources);
    ram = fixture(); put(ram, 0x8d38, 2); reject(ram, resources);
    ram = fixture(); put(ram, 0x914e, 512); reject(ram, resources);
    ram = fixture(); put(ram, 0x7f34+24+6, 0x1501); reject(ram, resources);
    ram = fixture(); put(ram, 0x7f34+24+2, 160*64+1); reject(ram, resources);
    ram = fixture(); put(ram, 0x7f34+24+10, 0x2952); reject(ram, resources);
    ram = fixture(); ram.pop_back(); reject(ram, resources);
    resources.push_back(resource); reject(fixture(), resources); resources.pop_back();
    // Empty preparation still publishes ready and clears the old tag.
    ram = fixture(); put(ram, 0x8d38, 0); put(ram, 0x8d3a, 0); put(ram, 0x9150, 123);
    resources.clear();
    require(ms5::prepare_sprite_queue(ram, resources, writes, error), "empty preparation failed");
    require(writes.empty() && ram[0x8d3d] == 255 && ram[0x9150] == 0 && ram[0x9151] == 0,
            "empty preparation state wrong");
    std::cout << "sprite_prepare_queue_test: passed\n";
}
