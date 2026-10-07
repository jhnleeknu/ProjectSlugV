#include "ms5/input_sampler.h"
#include <cassert>
#include <iostream>

namespace {
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, unsigned int value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at + 1] = static_cast<std::uint8_t>(value);
}
unsigned int word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1];
}
void stream_base(std::vector<std::uint8_t>& ram, unsigned int address) {
    put_word(ram, 0x4cc4, address >> 16);
    put_word(ram, 0x4cc6, address);
}
ms5::FixedDataResource streams() {
    ms5::FixedDataResource result;
    result.source_cpu_address = result.source_rom_offset = 0xf01fe;
    result.data.assign(0x1810, 0);
    return result;
}
ms5::InputPortSamples ports() {
    ms5::InputPortSamples result;
    result.system = 0xf5;
    result.player1_raw = 0xfe;
    result.player2_raw = 0xfd;
    result.player1_game = 0xfb;
    result.player2_game = 0xf7;
    return result;
}
void run(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& resource,
         unsigned int expected_reads) {
    std::uint8_t reads = 91;
    std::string error("prior error");
    assert(ms5::sample_input(ram, resource, ports(), reads, error));
    assert(reads == expected_reads && error.empty());
}
void fail(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& resource) {
    const std::vector<std::uint8_t> before = ram;
    std::uint8_t reads = 91;
    std::string error;
    assert(!ms5::sample_input(ram, resource, ports(), reads, error));
    assert(!error.empty() && ram == before && reads == 91);
}
std::vector<std::uint8_t> replay_ram() {
    std::vector<std::uint8_t> ram(65536, 0);
    ram[0x4cd4] = 1;
    stream_base(ram, 0xf01fe);
    return ram;
}
}

int main() {
    const ms5::FixedDataResource absent;
    // Mode0 consumes independent system/raw/game reads, without a stream.
    std::vector<std::uint8_t> ram(65536, 0);
    ram[0xfd94] = 0x63; ram[0xfd9a] = 0x87;
    ram[0x4cd2] = 11; ram[0x4cd3] = 3;
    ram[0x4cb4] = 2;
    run(ram, absent, 5);
    assert(ram[0x4cb4] == 10 && ram[0x4cb5] == 8);
    assert(ram[0x4cb8] == 1 && ram[0x4cbe] == 2);
    assert(ram[0x4caa] == 4 && ram[0x4cb0] == 8);
    assert(ram[0x4ca8] == 0x63 && ram[0x4cae] == 0x87);
    assert(ram[0x4cab] == 4 && ram[0x4cb1] == 8);
    assert(ram[0x4cb9] == 1 && ram[0x4cbf] == 2);
    assert(ram[0x4cad] == 11 && ram[0x4cbb] == 11);
    // No edge: zero timer wraps; timer1 repeats held input and reloads.
    ram[0x4cad] = 0; ram[0x4cb3] = 1;
    run(ram, absent, 5);
    assert(ram[0x4ca9] == 4 && ram[0x4cab] == 0);
    assert(ram[0x4cac] == 0 && ram[0x4cad] == 255);
    assert(ram[0x4cb2] == 8 && ram[0x4cb3] == 3);
    // Mode2 ignores even invalid resource metadata and feeds zero game input.
    ram[0x4cd4] = 2;
    run(ram, absent, 3);
    assert(ram[0x4caa] == 0 && ram[0x4cb0] == 0);
    assert(ram[0x4ca8] == 0x63 && ram[0x4cae] == 0x87);
    assert(ram[0x4cb8] == 1 && ram[0x4cbe] == 2);

    ms5::FixedDataResource resource = streams();
    // Exhaustion does not inspect the resource, but mode1 still feeds existing
    // replay input into game state during this call, even after setting mode2.
    ram = replay_ram(); put_word(ram, 0x4cce, 0x600);
    put_word(ram, 0x4cc2, 0x8142);
    run(ram, absent, 3);
    assert(ram[0x4cd4] == 2 && ram[0x4caa] == 0x81 && ram[0x4cb0] == 0x42);
    run(ram, absent, 3);
    assert(ram[0x4caa] == 0 && ram[0x4cb0] == 0);
    // Duration15 with a nonzero continuation postpones event processing.
    ram = replay_ram(); resource.data[0] = 0xff; resource.data[1] = 3;
    ram[0x4cd0] = 15;
    run(ram, resource, 3);
    assert(word(ram, 0x4cce) == 1 && word(ram, 0x4ccc) == 0);
    assert(ram[0x4cd0] == 1 && word(ram, 0x4cc2) == 0);
    // A zero continuation skips that byte and toggles event high nibble15.
    ram = replay_ram(); resource.data[1] = 0; resource.data[2] = 1;
    ram[0x4cd0] = 15;
    run(ram, resource, 3);
    assert(word(ram, 0x4cce) == 2 && word(ram, 0x4ccc) == 2);
    assert(word(ram, 0x4cc2) == 0x8000 && ram[0x4caa] == 0x80);
    assert(ram[0x4cd0] == 1);
    // Terminal event still updates replay input before changing mode.
    ram = replay_ram(); resource = streams(); resource.data[0x5ff] = 0xf0;
    put_word(ram, 0x4cce, 0x5ff); put_word(ram, 0x4ccc, 0x5ff);
    run(ram, resource, 3);
    assert(ram[0x4cd4] == 2 && word(ram, 0x4cc2) == 0x8000);
    assert(ram[0x4caa] == 0x80 && ram[0x4cb0] == 0);
    ram = replay_ram();
    put_word(ram, 0x4cce, 0x5ff); put_word(ram, 0x4ccc, 0x5ff);
    put_word(ram, 0x4cc2, 0x8000);
    run(ram, resource, 3);
    assert(word(ram, 0x4cc2) == 0 && ram[0x4caa] == 0);
    // Metadata is required only when an actual replay read is attempted.
    ram = replay_ram();
    ms5::FixedDataResource changed = resource;
    changed.source_rom_offset += 2; fail(ram, changed);
    changed = resource; changed.source_cpu_address += 2; fail(ram, changed);
    changed = resource; changed.data.pop_back(); fail(ram, changed);
    // An old indexffff is signed -1, so this event read fails after candidate
    // raw input writes and replay advancement. Both public outputs roll back.
    resource = streams(); put_word(ram, 0x4ccc, 0xffff);
    ram[0x4cb4] = 0xa5; ram[0x4cb8] = 0x55;
    fail(ram, resource);
    // The duration read succeeds at the last resource byte; its continuation
    // then fails beyond the resource. This is another late transactional error.
    ram = replay_ram(); resource.data.back() = 0xff;
    stream_base(ram, 0xf1a0d); ram[0x4cd0] = 15;
    fail(ram, resource);
    ram.resize(65535); fail(ram, resource);
    // Initializer selectors >=2 clear only gameplay blocks and mode. All other
    // bytes, including stale replay state and raw input blocks, must survive.
    ram.assign(65536, 0xa5);
    std::vector<std::uint8_t> expected=ram;
    for(std::size_t at=0x4ca8;at<0x4cb4;++at) expected[at]=0;
    expected[0x4cd4]=0;
    std::string error;
    assert(ms5::initialize_input(ram,absent,0xffff,error));
    assert(ram==expected && error.empty());
    // Different synthetic entries prove both pointer tables are consumed.
    resource=streams();
    for(unsigned int i=0;i<8;++i) {
        resource.data[0xc00+i]=static_cast<std::uint8_t>(0x20+i);
        resource.data[0x1808+i]=static_cast<std::uint8_t>(0x80+i);
    }
    for(unsigned int selector=0;selector<2;++selector) {
        ram.assign(65536,0xa5);expected=ram;
        for(std::size_t at=0x4ca8;at<0x4cb4;++at) expected[at]=0;
        expected[0x4cd4]=1;
        for(unsigned int i=0;i<4;++i) {
            expected[0x4cc4+i]=static_cast<std::uint8_t>(0x20+selector*4+i);
            expected[0x4cc8+i]=static_cast<std::uint8_t>(0x80+selector*4+i);
        }
        put_word(expected,0x4cc2,0);put_word(expected,0x4ccc,0);
        put_word(expected,0x4cce,0);expected[0x4cd0]=0;
        assert(ms5::initialize_input(ram,resource,selector,error));
        assert(ram==expected && error.empty());
        assert(!ms5::initialize_input(ram,absent,selector,error));
        assert(ram==expected && !error.empty());
    }
    std::cout << "Input sampler independent reads, repeat, replay and rollback passed\n";
}
