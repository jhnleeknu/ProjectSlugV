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
    ram = fixture(); put(ram, 0x7f34+24+6, 0x1508); reject(ram, resources);
    ram = fixture(); put(ram, 0x7f34+24+2, 160*64+1); reject(ram, resources);
    ram = fixture(); put(ram, 0x7f34+24+10, 0x2952); reject(ram, resources);
    ram = fixture(); ram.pop_back(); reject(ram, resources);
    resources.push_back(resource); reject(fixture(), resources); resources.pop_back();
    // Sort before waiting, while the active consumer owns a different cursor.
    ram = fixture(); put(ram, 0x8d34, 2); put(ram, 0x8b34, 24); put(ram, 0x8b36, 12);
    ms5::SpritePreparePending pending;
    require(ms5::begin_sprite_queue(ram, pending, error), "begin failed with active consumer");
    require(pending.waiting && pending.cursor == 0 && ram[0x8b35] == 12 && ram[0x8b37] == 24,
            "begin did not sort before waiting");
    const std::vector<std::uint8_t> sorted = ram;
    require(!ms5::begin_sprite_queue(ram, pending, error), "begin accepted an existing wait");
    require(ram == sorted && pending.waiting && pending.cursor == 0, "rejected begin changed pending state");
    // Change keys after the sort: repeated waiting/resume must never sort again.
    put(ram, 0x7f34 + 12, 2); put(ram, 0x7f34 + 24, 0);
    const std::vector<std::uint8_t> paused = ram;
    const std::vector<ms5::CompositionResource> absent;
    for (unsigned int poll = 0; poll < 3; ++poll) {
        writes.resize(1); writes[0].address = 123; writes[0].value = 456;
        require(ms5::resume_sprite_queue(ram, absent, pending, writes, error), "wait polling failed");
        require(ram == paused && writes.empty() && pending.waiting && pending.cursor == 0,
                "wait polling reran sorting or changed RAM");
    }
    put(ram, 0x8d34, 0);
    const std::vector<std::uint8_t> synchronized = ram;
    writes.resize(1); writes[0].address = 123; writes[0].value = 456;
    require(!ms5::resume_sprite_queue(ram, absent, pending, writes, error), "missing resource accepted on release");
    require(ram == synchronized && pending.waiting && pending.cursor == 0 && writes.size() == 1 &&
            writes[0].address == 123 && writes[0].value == 456, "failed resume changed outputs");
    require(ms5::resume_sprite_queue(ram, resources, pending, writes, error), "synchronized resume failed");
    require(!pending.waiting && pending.cursor == 0 && writes.size() == 8 &&
            ram[0x8b35] == 12 && ram[0x8b37] == 24 && ram[0x8d37] == 4,
            "resume re-sorted or failed to publish queue");
    const std::vector<std::uint8_t> completed = ram;
    const std::vector<ms5::SpriteWrite> completed_writes = writes;
    require(!ms5::resume_sprite_queue(ram, resources, pending, writes, error), "resume accepted no pending wait");
    require(ram == completed && !pending.waiting && pending.cursor == 0 &&
            writes.size() == completed_writes.size() && writes[0].address == completed_writes[0].address &&
            writes[0].value == completed_writes[0].value, "invalid resume changed outputs");

    // Empty preparation still publishes ready and clears the old tag.
    ram = fixture(); put(ram, 0x8d38, 0); put(ram, 0x8d3a, 0); put(ram, 0x9150, 123);
    resources.clear();
    require(ms5::prepare_sprite_queue(ram, resources, writes, error), "empty preparation failed");
    require(writes.empty() && ram[0x8d3d] == 255 && ram[0x9150] == 0 && ram[0x9151] == 0,
            "empty preparation state wrong");
    require(ms5::begin_sprite_queue(ram, pending, error), "empty begin failed");
    require(pending.waiting, "empty begin must expose a wait even when synchronized");
    require(ms5::resume_sprite_queue(ram, resources, pending, writes, error), "empty resume failed");
    require(!pending.waiting && pending.cursor == 0 && writes.empty(), "empty resume did not clear pending");
    std::cout << "sprite_prepare_queue_test: passed\n";
}
