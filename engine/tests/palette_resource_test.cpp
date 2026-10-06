#include "ms5/palette_resource.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <unistd.h>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

void set_u32(std::vector<unsigned char>& bytes, std::size_t offset, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) {
        bytes[offset + i] = static_cast<unsigned char>(value >> (i * 8));
    }
}

std::uint32_t crc32(const std::vector<unsigned char>& bytes, std::size_t start) {
    std::uint32_t table[256];
    for (std::uint32_t i = 0; i < 256; ++i) {
        std::uint32_t entry = i;
        for (unsigned int bit = 0; bit < 8; ++bit) {
            entry = (entry >> 1) ^ ((entry & 1U) ? UINT32_C(0xedb88320) : 0U);
        }
        table[i] = entry;
    }
    std::uint32_t crc = UINT32_C(0xffffffff);
    for (std::size_t i = start; i < bytes.size(); ++i) {
        crc = (crc >> 8) ^ table[(crc ^ bytes[i]) & 255U];
    }
    return crc ^ UINT32_C(0xffffffff);
}

void write_file(const std::string& path, const std::vector<unsigned char>& bytes) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(output), "open fixture");
    output.write(reinterpret_cast<const char*>(&bytes[0]), bytes.size());
    output.close();
    require(static_cast<bool>(output), "write fixture");
}

bool equal_records(const std::vector<ms5::PaletteRecord>& a,
                   const std::vector<ms5::PaletteRecord>& b) {
    if (a.size() != b.size()) {
        return false;
    }
    for (std::size_t i = 0; i < a.size(); ++i) {
        if (a[i].id != b[i].id) {
            return false;
        }
        for (unsigned int word = 0; word < 16; ++word) {
            if (a[i].source_words[word] != b[i].source_words[word] ||
                a[i].hardware_words[word] != b[i].hardware_words[word]) {
                return false;
            }
        }
    }
    return true;
}

void rejected(const std::string& path, const std::vector<unsigned char>& bytes,
              std::vector<ms5::PaletteRecord>& output, const char* message) {
    write_file(path, bytes);
    const std::vector<ms5::PaletteRecord> before = output;
    std::string error;
    require(!ms5::load_palette_resource(path, output, error), message);
    require(!error.empty(), "failure describes reason");
    require(equal_records(output, before), "failure is transactional");
}

} // namespace

int main() {
    const unsigned char check[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    const std::vector<unsigned char> check_bytes(check, check + 9);
    require(crc32(check_bytes, 0) == UINT32_C(0xcbf43926), "ZIP CRC reference vector");
    char filename[] = "/tmp/ms5-palette-test-XXXXXX";
    const int descriptor = mkstemp(filename);
    require(descriptor >= 0, "create fixture");
    close(descriptor);
    const std::string path(filename);
    std::vector<unsigned char> valid(32 + 2 * 68, 0);
    valid[0] = 'M'; valid[1] = 'S'; valid[2] = '5'; valid[3] = 'P';
    set_u32(valid, 4, 1); set_u32(valid, 8, 2);
    set_u32(valid, 12, 68); set_u32(valid, 16, 136);
    set_u32(valid, 32, 1); set_u32(valid, 100, 65535);
    for (unsigned int record = 0; record < 2; ++record) {
        for (unsigned int word = 0; word < 16; ++word) {
            valid[32 + record * 68 + 4 + word * 2] = static_cast<unsigned char>(0x80 + word);
            valid[32 + record * 68 + 5 + word * 2] = static_cast<unsigned char>(record + word);
            if (word != 0) {
                valid[32 + record * 68 + 36 + word * 2] = 0xff;
                valid[32 + record * 68 + 37 + word * 2] = static_cast<unsigned char>(word);
            }
        }
    }
    set_u32(valid, 20, crc32(valid, 32));
    write_file(path, valid);
    std::vector<ms5::PaletteRecord> output;
    std::string error = "old error";
    require(ms5::load_palette_resource(path, output, error), "load sparse catalog");
    require(error.empty(), "success clears error");
    require(output.size() == 2 && output[0].id == 1 && output[1].id == 65535,
            "sparse source IDs");
    for (unsigned int record = 0; record < 2; ++record) {
        for (unsigned int word = 0; word < 16; ++word) {
            require(output[record].source_words[word] == ((0x80U + word) * 256 + record + word),
                    "source words are big endian and retained");
            require(output[record].hardware_words[word] == (word == 0 ? 0 : 0xff00U + word),
                    "hardware words are big endian and unrestricted");
        }
    }
    std::vector<unsigned char> bad = valid;
    bad[0] = 'X'; rejected(path, bad, output, "invalid magic");
    const std::size_t fields[] = {4, 8, 12, 16, 24, 28};
    for (unsigned int i = 0; i < sizeof(fields) / sizeof(fields[0]); ++i) {
        bad = valid; set_u32(bad, fields[i], 0xffffffffU);
        rejected(path, bad, output, "invalid header field");
    }
    bad = valid; set_u32(bad, 8, 0); rejected(path, bad, output, "empty catalog");
    bad = valid; set_u32(bad, 8, 65537); rejected(path, bad, output, "count over cap");
    bad = valid; bad.resize(31); rejected(path, bad, output, "short header");
    bad = valid; bad.pop_back(); rejected(path, bad, output, "short payload");
    bad = valid; bad.push_back(0); rejected(path, bad, output, "trailing payload");
    bad = valid; bad[20] ^= 1; rejected(path, bad, output, "CRC mismatch");
    bad = valid; set_u32(bad, 100, 1); set_u32(bad, 20, crc32(bad, 32));
    rejected(path, bad, output, "duplicate ID");
    bad = valid; set_u32(bad, 100, 0); set_u32(bad, 20, crc32(bad, 32));
    rejected(path, bad, output, "decreasing ID");
    bad = valid; set_u32(bad, 100, 65536); set_u32(bad, 20, crc32(bad, 32));
    rejected(path, bad, output, "ID out of range");
    bad = valid; bad[68] = 1; set_u32(bad, 20, crc32(bad, 32));
    rejected(path, bad, output, "nonzero hardware word zero");
    bad = valid; bad.resize(32 + 65536 * 68 + 1);
    rejected(path, bad, output, "file cap");
    // Full source-ID domain exercises the maximum valid allocation and ID zero.
    valid.assign(32 + 65536 * 68, 0);
    valid[0] = 'M'; valid[1] = 'S'; valid[2] = '5'; valid[3] = 'P';
    set_u32(valid, 4, 1); set_u32(valid, 8, 65536);
    set_u32(valid, 12, 68); set_u32(valid, 16, 65536 * 68);
    for (std::uint32_t i = 0; i < 65536; ++i) {
        set_u32(valid, 32 + static_cast<std::size_t>(i) * 68, i);
    }
    set_u32(valid, 20, crc32(valid, 32)); write_file(path, valid);
    require(ms5::load_palette_resource(path, output, error), "maximum valid catalog");
    require(output.size() == 65536 && output.front().id == 0 && output.back().id == 65535,
            "maximum valid catalog bounds");
    require(std::remove(path.c_str()) == 0, "remove fixture");
    require(!ms5::load_palette_resource(path, output, error) && output.size() == 65536,
            "missing file preserves output");
    std::cout << "palette_resource_test: passed\n";
    return 0;
}
