#include "ms5/sprite_pool.h"
#include "ms5/sprite_prepare_queue.h"
#include "ms5/sprite_refresh_queue.h"
#include <cstdlib>
#include <iostream>

namespace {

void require(bool value, const char* message) {
    if (!value) { std::cerr << message << '\n'; std::exit(1); }
}

void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at + 1] = static_cast<std::uint8_t>(value);
}

void configuration_case(std::uint16_t selector, std::uint16_t lower,
                        std::uint16_t upper, std::uint16_t expected_lower,
                        std::uint16_t expected_upper) {
    std::vector<std::uint8_t> ram(65536);
    for (std::size_t index = 0; index < ram.size(); ++index) {
        ram[index] = static_cast<std::uint8_t>(index * 13U + 9U);
    }
    std::vector<std::uint8_t> expected(ram);
    const std::size_t pool = selector == 0 ? 0x8d3eU : 0x8d46U;
    put(expected, pool, expected_lower);
    put(expected, pool + 2, expected_upper);
    put(expected, pool + 4, expected_lower);
    put(expected, pool + 6, expected_upper);
    std::string error("stale");
    require(ms5::configure_sprite_pool(ram, selector, lower, upper, error),
            "configuration failed");
    require(ram == expected && error.empty(), "configuration altered wrong bytes");
}

std::vector<std::uint8_t> queue_fixture(bool forward, unsigned int disabled_pool) {
    std::vector<std::uint8_t> ram(65536, 0);
    ram[0x8d3c] = forward ? 0x80U : 0U;
    ram[0x8d3d] = 0xffU;
    put(ram, 0x8d36, 2); put(ram, 0x8d38, 2); put(ram, 0x8d3a, 2);
    put(ram, 0x8d40, 190); put(ram, 0x8d44, 190);
    put(ram, 0x8d46, 190); put(ram, 0x8d48, 380);
    put(ram, 0x8d4a, 190); put(ram, 0x8d4c, 380);
    const std::size_t pool = disabled_pool == 0 ? 0x8d3eU : 0x8d46U;
    for (unsigned int index = 0; index < 4; ++index) {
        put(ram, pool + index * 2, 0xffffU);
    }
    put(ram, 0x8b34, 12);
    put(ram, 0x7f40 + 2, 160 * 64);
    put(ram, 0x7f40 + 4, 0xffffU);
    put(ram, 0x7f40 + 6, disabled_pool == 0 ? 0x1500U : 0x1504U);
    put(ram, 0x7f40 + 10, 0x2152U);
    return ram;
}

bool dispatch(bool refresh, std::vector<std::uint8_t>& ram,
              const std::vector<ms5::CompositionResource>& resources,
              std::vector<ms5::SpriteWrite>& writes, bool& processed,
              std::string& error) {
    if (refresh) {
        return ms5::refresh_sprite_queue(ram, resources, writes, processed, error);
    }
    put(ram, 0x8d36, 0);
    return ms5::prepare_sprite_queue(ram, resources, writes, error);
}

void reject_queue(bool refresh, std::vector<std::uint8_t> ram,
                  const std::vector<ms5::CompositionResource>& resources) {
    if (!refresh) { put(ram, 0x8d36, 0); }
    const std::vector<std::uint8_t> before(ram);
    std::vector<ms5::SpriteWrite> writes(1);
    writes[0].address = 123; writes[0].value = 456;
    bool processed = false;
    std::string error;
    const bool valid = refresh
        ? ms5::refresh_sprite_queue(ram, resources, writes, processed, error)
        : ms5::prepare_sprite_queue(ram, resources, writes, error);
    require(!valid && !error.empty(), "invalid disabled queue accepted");
    require(ram == before && writes.size() == 1 && writes[0].address == 123 &&
            writes[0].value == 456 && !processed, "queue error changed caller state");
}

void disabled_queues() {
    ms5::CompositionResource resource;
    resource.id = 0x2152U; resource.source_rom_offset = 0;
    const std::uint8_t data[] = {1,0,0,0,0,0,1,1,0,0,0,1};
    resource.data.assign(data, data + 12);
    const std::vector<ms5::CompositionResource> resources(1, resource);
    for (unsigned int refresh = 0; refresh < 2; ++refresh) {
        for (unsigned int forward = 0; forward < 2; ++forward) {
            for (unsigned int pool_index = 0; pool_index < 2; ++pool_index) {
                const std::size_t pool = pool_index == 0 ? 0x8d3eU : 0x8d46U;
                std::vector<std::uint8_t> ram = queue_fixture(forward != 0, pool_index);
                std::vector<ms5::SpriteWrite> writes;
                std::string error("stale");
                bool processed = false;
                require(dispatch(refresh != 0, ram, resources, writes, processed, error),
                        "disabled queue failed");
                require(error.empty() && (refresh == 0 || processed),
                        "disabled queue success state wrong");
                for (unsigned int index = 0; index < 8; ++index) {
                    require(ram[pool + index] == 255, "disabled pool was changed");
                }
                // Refresh can clean the other active pool; disabled records emit nothing.
                require(writes.empty(), "disabled record emitted writes");
                for (unsigned int mixed_word = 0; mixed_word < 4; ++mixed_word) {
                    ram = queue_fixture(forward != 0, pool_index);
                    put(ram, pool + mixed_word * 2, 0);
                    reject_queue(refresh != 0, ram, resources);
                }
                ram = queue_fixture(forward != 0, pool_index);
                const std::size_t other_pool = pool_index == 0 ? 0x8d46U : 0x8d3eU;
                for (unsigned int index = 0; index < 4; ++index) {
                    put(ram, other_pool + index * 2, 0xffffU);
                }
                require(dispatch(refresh != 0, ram, resources, writes, processed, error) &&
                        writes.empty(), "two disabled pools failed");
                ram = queue_fixture(forward != 0, pool_index);
                put(ram, 0x7f40 + 6, pool_index == 0 ? 0x1504U : 0x1500U);
                require(dispatch(refresh != 0, ram, resources, writes, processed, error) &&
                        !writes.empty(), "disabled pool prevented active pool emission");
                ram = queue_fixture(forward != 0, pool_index);
                std::vector<ms5::CompositionResource> malformed(resources);
                malformed[0].data.pop_back(); reject_queue(refresh != 0, ram, malformed);
                malformed = resources; malformed[0].data[0] = 2;
                reject_queue(refresh != 0, ram, malformed);
                std::vector<ms5::CompositionResource> missing;
                reject_queue(refresh != 0, ram, missing);
                put(ram, 0x7f40 + 4, 0); reject_queue(refresh != 0, ram, resources);
                ram = queue_fixture(forward != 0, pool_index);
                put(ram, 0x7f40 + 6, 0x1501); reject_queue(refresh != 0, ram, resources);
                ram = queue_fixture(forward != 0, pool_index);
                put(ram, 0x7f40 + 2, 160 * 64 + 1); reject_queue(refresh != 0, ram, resources);
            }
        }
    }
}

} // namespace

int main() {
    configuration_case(0, 0, 190, 0, 190);
    configuration_case(1, 190, 380, 190, 380);
    configuration_case(0xffffU, 1, 0xffffU, 1, 0xffffU);
    configuration_case(0x8000U, 379, 380, 379, 380);
    configuration_case(0, 380, 381, 0xffffU, 0xffffU);
    configuration_case(0, 381, 0xffffU, 0xffffU, 0xffffU);
    configuration_case(1, 0xffffU, 0xffffU, 0xffffU, 0xffffU);
    configuration_case(1, 0x8000U, 0x7fffU, 0xffffU, 0xffffU);
    configuration_case(0, 0, 0, 0, 0xffffU);
    configuration_case(1, 379, 379, 379, 0xffffU);
    configuration_case(0, 379, 378, 379, 0xffffU);
    configuration_case(0, 1, 0x8000U, 1, 0x8000U);
    const std::size_t sizes[] = {0, 65535, 65537};
    for (unsigned int index = 0; index < 3; ++index) {
        std::vector<std::uint8_t> ram(sizes[index], 0x5aU);
        const std::vector<std::uint8_t> before(ram);
        std::string error;
        require(!ms5::configure_sprite_pool(ram, 0, 0, 190, error) &&
                ram == before && !error.empty(), "invalid RAM size was accepted or changed");
    }
    disabled_queues();
    std::cout << "sprite_pool_test: passed\n";
}
