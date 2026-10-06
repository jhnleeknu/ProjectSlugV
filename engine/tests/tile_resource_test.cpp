#include "ms5/tile_resource.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <unistd.h>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

void set_u32(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) {
        bytes[offset + i] = static_cast<std::uint8_t>((value >> (i * 8)) & 255U);
    }
}

std::uint32_t crc32(const std::vector<std::uint8_t>& bytes) {
    std::uint32_t table[256];
    for (std::uint32_t i = 0; i < 256; ++i) {
        std::uint32_t entry = i;
        for (unsigned int bit = 0; bit < 8; ++bit) {
            entry = (entry >> 1) ^ ((entry & 1U) ? UINT32_C(0xedb88320) : 0U);
        }
        table[i] = entry;
    }
    std::uint32_t crc = UINT32_C(0xffffffff);
    for (std::size_t i = 32; i < bytes.size(); ++i) {
        crc = (crc >> 8) ^ table[(crc ^ bytes[i]) & 255U];
    }
    return crc ^ UINT32_C(0xffffffff);
}

void write_file(const std::string& path, const std::vector<std::uint8_t>& bytes) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(output), "open fixture");
    output.write(reinterpret_cast<const char*>(&bytes[0]), bytes.size());
    output.close();
    require(static_cast<bool>(output), "write fixture");
}

void rejected(const std::string& path, const std::vector<std::uint8_t>& bytes,
              ms5::TileResource& output, const char* message) {
    write_file(path, bytes);
    const ms5::TileResource before = output;
    std::string error;
    require(!ms5::load_tile_resource(path, output, error), message);
    require(!error.empty(), "failure describes reason");
    require(output.kind == before.kind && output.width == before.width &&
            output.height == before.height && output.count == before.count &&
            output.pixels == before.pixels, "failure is transactional");
}

} // namespace

int main() {
    char filename[] = "/tmp/ms5-tile-test-XXXXXX";
    const int descriptor = mkstemp(filename);
    require(descriptor >= 0, "create temporary fixture");
    close(descriptor);
    const std::string path(filename);
    std::vector<std::uint8_t> valid(32 + 4096 * 64, 0);
    valid[0] = 'M'; valid[1] = 'S'; valid[2] = '5'; valid[3] = 'T';
    set_u32(valid, 4, 1);
    set_u32(valid, 8, 2);
    set_u32(valid, 12, 8);
    set_u32(valid, 16, 8);
    set_u32(valid, 20, 4096);
    set_u32(valid, 24, 4096 * 64);
    // Known zlib CRC32 for 262144 zero bytes.
    set_u32(valid, 28, UINT32_C(0xe20eea22));
    require(crc32(valid) == UINT32_C(0xe20eea22), "fixture CRC matches zlib vector");
    write_file(path, valid);
    ms5::TileResource output;
    std::string error = "old error";
    require(ms5::load_tile_resource(path, output, error), "load fixed catalog");
    require(error.empty(), "success clears error");
    require(output.kind == 2 && output.width == 8 && output.height == 8 &&
            output.count == 4096 && output.pixels.size() == 262144, "loaded metadata");
    std::uint8_t pixel = 99;
    for (std::uint32_t tile = 0; tile < output.count; ++tile) {
        for (std::uint32_t y = 0; y < output.height; ++y) {
            for (std::uint32_t x = 0; x < output.width; ++x) {
                require(ms5::get_tile_pixel(output, tile, x, y, pixel) && pixel == 0,
                        "all valid pixel coordinates");
            }
        }
    }
    pixel = 99;
    require(!ms5::get_tile_pixel(output, 4096, 0, 0, pixel) && pixel == 99, "tile bounds");
    require(!ms5::get_tile_pixel(output, 0, 8, 0, pixel) && pixel == 99, "column bounds");
    require(!ms5::get_tile_pixel(output, 0, 0, 8, pixel) && pixel == 99, "row bounds");
    ms5::TileResource incomplete;
    incomplete.width = 8; incomplete.height = 8; incomplete.count = 4096;
    require(!ms5::get_tile_pixel(incomplete, 0, 0, 0, pixel), "incomplete payload bounds");
    incomplete.width = UINT32_MAX; incomplete.height = UINT32_MAX; incomplete.count = UINT32_MAX;
    require(!ms5::get_tile_pixel(incomplete, UINT32_MAX - 1, 0, 0, pixel), "lookup overflow bounds");

    std::vector<std::uint8_t> bad = valid;
    bad[0] = 'X'; rejected(path, bad, output, "magic validation");
    const std::size_t offsets[] = {4, 8, 12, 16, 20, 24};
    for (std::size_t i = 0; i < sizeof(offsets) / sizeof(offsets[0]); ++i) {
        bad = valid; set_u32(bad, offsets[i], 3);
        rejected(path, bad, output, "header field validation");
    }
    bad = valid; set_u32(bad, 8, 1);
    rejected(path, bad, output, "sprite dimensions and count validation");
    bad = valid; set_u32(bad, 12, UINT32_MAX); set_u32(bad, 16, UINT32_MAX);
    set_u32(bad, 20, UINT32_MAX);
    rejected(path, bad, output, "product overflow validation");
    bad = valid; set_u32(bad, 24, 134217729);
    rejected(path, bad, output, "payload cap validation");
    bad = valid; bad.resize(31); rejected(path, bad, output, "truncated header validation");
    bad = valid; bad.pop_back(); rejected(path, bad, output, "truncated payload validation");
    bad = valid; bad.push_back(0); rejected(path, bad, output, "trailing byte validation");
    bad = valid; bad[28] ^= 1; rejected(path, bad, output, "CRC validation");
    bad = valid; bad[32] = 16; set_u32(bad, 28, crc32(bad));
    rejected(path, bad, output, "palette index validation after valid CRC");

    // A distinct pattern checks tile/row/column indexing, including index 15.
    bad = valid;
    bad[32 + 123 * 64 + 4 * 8 + 5] = 15;
    bad[bad.size() - 1] = 7;
    set_u32(bad, 28, crc32(bad)); write_file(path, bad);
    require(ms5::load_tile_resource(path, output, error), "load nonzero payload");
    require(ms5::get_tile_pixel(output, 123, 5, 4, pixel) && pixel == 15, "pixel order");
    require(ms5::get_tile_pixel(output, 4095, 7, 7, pixel) && pixel == 7, "last pixel");
    require(std::remove(path.c_str()) == 0, "remove fixture");
    require(!ms5::load_tile_resource(path, output, error), "missing file validation");
    require(ms5::get_tile_pixel(output, 123, 5, 4, pixel) && pixel == 15,
            "missing file leaves output unchanged");
    std::cout << "tile_resource_test: passed\n";
    return 0;
}
