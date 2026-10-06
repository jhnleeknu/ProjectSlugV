#include "ms5/composition_resource.h"

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

std::vector<unsigned char> fixture(unsigned int width, unsigned int height) {
    std::vector<unsigned char> bytes(32 + 8 + width * height * 4, 0);
    bytes[0] = 'M'; bytes[1] = 'S'; bytes[2] = '5'; bytes[3] = 'C';
    set_u32(bytes, 4, 1); set_u32(bytes, 8, 1);
    set_u32(bytes, 12, 0x2152); set_u32(bytes, 16, 0x234567);
    set_u32(bytes, 20, static_cast<std::uint32_t>(bytes.size() - 32));
    bytes[32] = 1;
    bytes[34] = 0xff; bytes[35] = 0xf0;
    bytes[36] = 0x12; bytes[37] = 0x34;
    bytes[38] = static_cast<unsigned char>(width);
    bytes[39] = static_cast<unsigned char>(height);
    for (std::size_t i = 40; i < bytes.size(); ++i) {
        bytes[i] = static_cast<unsigned char>(i);
    }
    set_u32(bytes, 24, crc32(bytes, 32));
    return bytes;
}

void rejected(const std::string& path, const std::vector<unsigned char>& bytes,
              ms5::CompositionResource& output, const char* message) {
    write_file(path, bytes);
    const ms5::CompositionResource before = output;
    std::string error;
    require(!ms5::load_composition_resource(path, output, error), message);
    require(!error.empty(), "failure describes reason");
    require(output.id == before.id && output.source_rom_offset == before.source_rom_offset &&
            output.data == before.data, "failure is transactional");
}

} // namespace

int main() {
    const unsigned char check[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    const std::vector<unsigned char> check_bytes(check, check + 9);
    require(crc32(check_bytes, 0) == UINT32_C(0xcbf43926), "ZIP CRC reference vector");
    char filename[] = "/tmp/ms5-composition-test-XXXXXX";
    const int descriptor = mkstemp(filename);
    require(descriptor >= 0, "create fixture");
    close(descriptor);
    const std::string path(filename);
    const std::vector<unsigned char> valid = fixture(2, 3);
    ms5::CompositionResource output;
    output.id = 0; output.source_rom_offset = 0;
    std::string error = "old error";
    write_file(path, valid);
    require(ms5::load_composition_resource(path, output, error), "load rectangle");
    require(error.empty(), "success clears error");
    require(output.id == 0x2152 && output.source_rom_offset == 0x234567,
            "source packed ID and offset retained");
    require(output.data == std::vector<unsigned char>(valid.begin() + 32, valid.end()),
            "original BE rectangle retained exactly");
    std::vector<unsigned char> bad = valid;
    bad[0] = 'X'; rejected(path, bad, output, "invalid magic");
    const std::size_t fields[] = {4, 8, 12, 16, 20, 28};
    for (unsigned int i = 0; i < sizeof(fields) / sizeof(fields[0]); ++i) {
        bad = valid; set_u32(bad, fields[i], 0xffffffffU);
        rejected(path, bad, output, "invalid header field");
    }
    bad = valid; set_u32(bad, 12, 6); rejected(path, bad, output, "invalid bank selector six");
    bad = valid; set_u32(bad, 12, 7); rejected(path, bad, output, "invalid bank selector seven");
    bad = valid; set_u32(bad, 16, 0x800000); rejected(path, bad, output, "offset equals ROM size");
    bad = valid; set_u32(bad, 16, 0x800000 - 31); rejected(path, bad, output, "source crosses ROM end");
    bad = valid; bad.resize(31); rejected(path, bad, output, "short header");
    bad = valid; bad.pop_back(); rejected(path, bad, output, "short payload");
    bad = valid; bad.push_back(0); rejected(path, bad, output, "trailing bytes");
    bad = valid; bad[24] ^= 1; rejected(path, bad, output, "CRC mismatch");
    bad = valid; bad[40] ^= 1; rejected(path, bad, output, "corrupt payload");
    const std::size_t payload_fields[] = {32, 33, 38, 39};
    const unsigned char payload_values[] = {2, 1, 0, 0};
    for (unsigned int i = 0; i < 4; ++i) {
        bad = valid; bad[payload_fields[i]] = payload_values[i];
        set_u32(bad, 24, crc32(bad, 32));
        rejected(path, bad, output, "invalid rectangle field with valid CRC");
    }
    bad = valid; bad[39] = 33; set_u32(bad, 24, crc32(bad, 32));
    rejected(path, bad, output, "height above cap");
    bad = valid; bad[38] = 3; set_u32(bad, 24, crc32(bad, 32));
    rejected(path, bad, output, "dimension length mismatch");
    bad = valid; set_u32(bad, 20, 8); bad.resize(40); set_u32(bad, 24, crc32(bad, 32));
    rejected(path, bad, output, "payload below minimum");
    bad = valid; bad.resize(32 + 32648 + 1);
    rejected(path, bad, output, "file above maximum");
    std::vector<unsigned char> maximum = fixture(255, 32);
    set_u32(maximum, 12, 0x7ffffd);
    set_u32(maximum, 16, 0x800000U - 32648U);
    write_file(path, maximum);
    require(ms5::load_composition_resource(path, output, error), "maximum rectangle and ROM end boundary");
    require(output.data.size() == 32648 && output.id == 0x7ffffd &&
            output.source_rom_offset == 0x800000U - 32648U, "maximum bounds retained");
    std::vector<unsigned char> minimum = fixture(1, 1);
    set_u32(minimum, 12, 0); set_u32(minimum, 16, 0);
    write_file(path, minimum);
    require(ms5::load_composition_resource(path, output, error), "minimum rectangle and zero ID");
    const ms5::CompositionResource before = output;
    require(std::remove(path.c_str()) == 0, "remove fixture");
    require(!ms5::load_composition_resource(path, output, error) && !error.empty() &&
            output.id == before.id && output.source_rom_offset == before.source_rom_offset &&
            output.data == before.data, "missing file preserves output");
    std::cout << "composition_resource_test: passed\n";
    return 0;
}
