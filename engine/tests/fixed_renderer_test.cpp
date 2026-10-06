#include "ms5/fixed_renderer.h"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

static void rejected(const ms5::TileResource& tiles,
                     const std::vector<std::uint16_t>& vram,
                     const std::vector<std::uint16_t>& palette,
                     std::vector<std::uint16_t>& frame) {
    const std::vector<std::uint16_t> before(frame);
    std::string error;
    require(!ms5::render_fixed_layer_words(tiles, vram, palette, frame, error),
            "invalid input rejected");
    require(!error.empty() && frame == before, "failure is transactional");
}

int main() {
    ms5::TileResource tiles;
    tiles.kind = 2; tiles.width = 8; tiles.height = 8; tiles.count = 4096;
    tiles.pixels.resize(262144, 0);
    tiles.pixels[123 * 64 + 5 * 8 + 3] = 7;
    tiles.pixels[4095 * 64 + 7 * 8 + 7] = 15;
    std::vector<std::uint16_t> vram(1280, 0);
    vram[2 * 32 + 4] = 0x307b;
    vram[39 * 32 + 31] = 0xffff;
    std::vector<std::uint16_t> palette(256, 0);
    palette[3 * 16 + 7] = 0x87ab;
    palette[255] = 0xfedc;
    std::vector<std::uint16_t> frame(320 * 256, 0x1234);
    std::string error = "old";
    require(ms5::render_fixed_layer_words(tiles, vram, palette, frame, error),
            "valid render");
    require(error.empty(), "success clears error");
    for (std::size_t index = 0; index < frame.size(); ++index) {
        const std::uint16_t expected = index == 37 * 320 + 19 ? 0x87ab :
            (index == frame.size() - 1 ? 0xfedc : 0x1234);
        require(frame[index] == expected, "column-major placement and transparency");
    }
    tiles.kind = 1; rejected(tiles, vram, palette, frame); tiles.kind = 2;
    tiles.width = 16; rejected(tiles, vram, palette, frame); tiles.width = 8;
    tiles.height = 16; rejected(tiles, vram, palette, frame); tiles.height = 8;
    tiles.count = 4095; rejected(tiles, vram, palette, frame); tiles.count = 4096;
    tiles.pixels.pop_back(); rejected(tiles, vram, palette, frame);
    tiles.pixels.push_back(16); rejected(tiles, vram, palette, frame);
    tiles.pixels.back() = 15;
    vram.pop_back(); rejected(tiles, vram, palette, frame); vram.push_back(0xffff);
    vram.push_back(0); rejected(tiles, vram, palette, frame); vram.pop_back();
    palette.pop_back(); rejected(tiles, vram, palette, frame); palette.push_back(0xfedc);
    frame.pop_back(); rejected(tiles, vram, palette, frame); frame.push_back(0xfedc);
    frame.push_back(0); rejected(tiles, vram, palette, frame); frame.pop_back();
    // A caller can pass the frame as the palette; reads must remain stable.
    tiles.pixels[64 + 1] = 2;
    tiles.pixels[64 + 2] = 1;
    vram[0] = 1;
    frame[1] = 0xaaaa;
    frame[2] = 0xbbbb;
    frame[3 * 16 + 7] = 0x87ab;
    frame[255] = 0xfedc;
    require(ms5::render_fixed_layer_words(tiles, vram, frame, frame, error),
            "aliased palette accepted");
    require(frame[1] == 0xbbbb && frame[2] == 0xaaaa &&
            frame[37 * 320 + 19] == 0x87ab && frame.back() == 0xfedc,
            "aliased palette reads stable");
    std::cout << "fixed_renderer_test: passed\n";
    return 0;
}
