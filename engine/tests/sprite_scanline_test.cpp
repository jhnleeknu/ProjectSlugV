#include "ms5/sprite_scanline.h"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

static std::vector<std::uint16_t> blank_vram() {
    std::vector<std::uint16_t> vram(0x8800U, 0xdeadU);
    for (std::size_t sprite = 0; sprite < 381U; ++sprite) {
        vram[0x8200U | sprite] = 0;
    }
    return vram;
}

static std::uint16_t control(std::uint16_t y, std::uint16_t rows) {
    return static_cast<std::uint16_t>(((512U - y) & 511U) << 7 | rows);
}

static void rejected(std::vector<std::uint16_t>& vram, std::uint16_t scanline) {
    const std::vector<std::uint16_t> before(vram);
    std::string error;
    require(!ms5::parse_sprite_scanline(vram, scanline, error), "invalid input rejected");
    require(!error.empty() && vram == before, "failure preserves all VRAM");
}

static void selected(std::vector<std::uint16_t>& vram, std::uint16_t scanline,
                     const std::vector<std::uint16_t>& expected) {
    const std::vector<std::uint16_t> before(vram);
    const std::size_t base = (scanline & 1U) != 0U ? 0x8680U : 0x8600U;
    std::string error = "previous error";
    require(ms5::parse_sprite_scanline(vram, scanline, error), "valid input accepted");
    require(error.empty(), "success clears error");
    for (std::size_t index = 0; index < vram.size(); ++index) {
        if (index >= base && index <= base + 96U) {
            const std::size_t slot = index - base;
            require(vram[index] == (slot < expected.size() ? expected[slot] : 0U),
                    "selected sprite order and zero fill including entry 96");
        } else {
            require(vram[index] == before[index],
                    "opposite parity list and all other VRAM preserved");
        }
    }
}

int main() {
    std::vector<std::uint16_t> vram = blank_vram();
    rejected(vram, 512);
    rejected(vram, 65535);
    vram.pop_back(); rejected(vram, 0);
    vram.push_back(0); vram.push_back(0); rejected(vram, 511);
    vram.clear(); rejected(vram, 0);

    vram = blank_vram();
    const std::vector<std::uint16_t> none;
    selected(vram, 0, none);
    selected(vram, 511, none);

    // IDs 0 and 380 are both valid; no sprite above 380 is scanned.
    vram = blank_vram();
    vram[0x8200U] = control(0, 1);
    vram[0x8200U | 380U] = control(0, 1);
    vram[0x8200U | 381U] = control(0, 32);
    const std::vector<std::uint16_t> endpoints = {0, 380};
    selected(vram, 0, endpoints);
    selected(vram, 15, endpoints);
    selected(vram, 16, none);

    // A chain inherits both Y and rows, ignoring its own encoded fields.
    vram = blank_vram();
    vram[0x8200U] = control(100, 63) | 0x0040U;
    vram[0x8201U] = control(510, 1);
    vram[0x8202U] = control(100, 0) | 0x0040U;
    vram[0x8203U] = control(100, 63) | 0x0040U;
    vram[0x8204U] = control(0, 0);
    vram[0x8205U] = control(100, 63) | 0x0040U;
    const std::vector<std::uint16_t> chain = {1, 2, 3};
    selected(vram, 510, chain);
    selected(vram, 511, chain);
    selected(vram, 0, chain);
    selected(vram, 13, chain);
    selected(vram, 14, none);
    selected(vram, 509, none);

    // 31 rows end at 496 pixels; 32 and 63 rows cover all scanlines.
    vram = blank_vram();
    vram[0x8207U] = control(1, 31);
    vram[0x8208U] = control(2, 32);
    vram[0x8209U] = control(3, 63);
    const std::vector<std::uint16_t> three = {7, 8, 9};
    const std::vector<std::uint16_t> full_height = {8, 9};
    selected(vram, 1, three);
    selected(vram, 496, three);
    selected(vram, 497, full_height);
    selected(vram, 0, full_height);
    selected(vram, 511, full_height);

    vram = blank_vram();
    std::vector<std::uint16_t> saturated;
    for (std::uint16_t sprite = 0; sprite < 381U; ++sprite) {
        vram[0x8200U | sprite] = control(25, 32);
        if (sprite < 96U) {
            saturated.push_back(sprite);
        }
    }
    selected(vram, 100, saturated);
    selected(vram, 101, saturated);
    std::cout << "sprite_scanline_test: passed\n";
    return 0;
}
