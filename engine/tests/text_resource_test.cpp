#include "ms5/text_resource.h"

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

void set_u32(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) {
        bytes[offset + i] = static_cast<std::uint8_t>(value >> (i * 8));
    }
}

std::uint32_t crc32(const std::vector<std::uint8_t>& bytes, std::size_t start) {
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

void write_file(const std::string& path, const std::vector<std::uint8_t>& bytes) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(output), "open fixture");
    output.write(reinterpret_cast<const char*>(&bytes[0]), bytes.size());
    output.close();
    require(static_cast<bool>(output), "write fixture");
}

bool equal_resource(const ms5::TextResource& first, const ms5::TextResource& second) {
    if (first.id != second.id || first.script != second.script ||
        first.bindings.size() != second.bindings.size()) {
        return false;
    }
    for (std::size_t i = 0; i < first.bindings.size(); ++i) {
        if (first.bindings[i].slot != second.bindings[i].slot ||
            first.bindings[i].source_id != second.bindings[i].source_id) {
            return false;
        }
    }
    return true;
}

void rejected(const std::string& path, const std::vector<std::uint8_t>& bytes,
              ms5::TextResource& output, const char* message) {
    write_file(path, bytes);
    const ms5::TextResource before = output;
    std::string error;
    require(!ms5::load_text_resource(path, output, error), message);
    require(!error.empty(), "failure describes reason");
    require(equal_resource(output, before), "failure is transactional");
}

} // namespace

int main() {
    const std::uint8_t check[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    const std::vector<std::uint8_t> check_bytes(check, check + 9);
    require(crc32(check_bytes, 0) == UINT32_C(0xcbf43926), "ZIP CRC reference vector");
    char filename[] = "/tmp/ms5-text-test-XXXXXX";
    const int descriptor = mkstemp(filename);
    require(descriptor >= 0, "create fixture");
    close(descriptor);
    const std::string path(filename);
    // Palette and location operands include zero bytes before the terminator.
    const std::uint8_t script[] = {'\\', 'c', 0x61, '\\', 'p', 0,
                                   '\\', 'l', 0, 0, 'A', 0};
    std::vector<std::uint8_t> valid(32 + 16 + sizeof(script), 0);
    valid[0] = 'M'; valid[1] = 'S'; valid[2] = '5'; valid[3] = 'X';
    set_u32(valid, 4, 1); set_u32(valid, 8, 1);
    set_u32(valid, 12, 0x7fffff); set_u32(valid, 16, 2);
    set_u32(valid, 20, static_cast<std::uint32_t>(valid.size() - 32));
    set_u32(valid, 32, 15); set_u32(valid, 36, 65535);
    set_u32(valid, 40, 0); set_u32(valid, 44, 0);
    for (std::size_t i = 0; i < sizeof(script); ++i) {
        valid[48 + i] = script[i];
    }
    set_u32(valid, 24, crc32(valid, 32));
    write_file(path, valid);
    ms5::TextResource output;
    std::string error = "old error";
    require(ms5::load_text_resource(path, output, error), "load valid text");
    require(error.empty(), "success clears error");
    require(output.id == 0x7fffff && output.bindings.size() == 2 &&
            output.bindings[0].slot == 15 && output.bindings[0].source_id == 65535 &&
            output.bindings[1].slot == 0 && output.bindings[1].source_id == 0,
            "binding and offset bounds retained");
    require(output.script == std::vector<std::uint8_t>(script, script + sizeof(script)),
            "script retains zero operands");
    std::vector<std::uint8_t> bad = valid;
    bad[0] = 'X'; rejected(path, bad, output, "invalid magic");
    const std::size_t fields[] = {4, 8, 12, 16, 20, 28};
    for (std::size_t i = 0; i < sizeof(fields) / sizeof(fields[0]); ++i) {
        bad = valid; set_u32(bad, fields[i], 0xffffffffU);
        rejected(path, bad, output, "invalid header field");
    }
    bad = valid; set_u32(bad, 12, 0x800000); rejected(path, bad, output, "offset over cap");
    bad = valid; set_u32(bad, 16, 0); rejected(path, bad, output, "empty bindings");
    bad = valid; set_u32(bad, 16, 17); rejected(path, bad, output, "binding count over cap");
    bad = valid; bad.resize(31); rejected(path, bad, output, "short header");
    bad = valid; bad.pop_back(); rejected(path, bad, output, "short payload");
    bad = valid; bad.push_back(0); rejected(path, bad, output, "trailing bytes");
    bad = valid; bad[24] ^= 1; rejected(path, bad, output, "CRC mismatch");
    bad = valid; set_u32(bad, 40, 15); set_u32(bad, 24, crc32(bad, 32));
    rejected(path, bad, output, "duplicate slots");
    bad = valid; set_u32(bad, 32, 16); set_u32(bad, 24, crc32(bad, 32));
    rejected(path, bad, output, "slot out of range");
    bad = valid; set_u32(bad, 36, 65536); set_u32(bad, 24, crc32(bad, 32));
    rejected(path, bad, output, "source ID out of range");
    bad = valid; bad.resize(48); set_u32(bad, 20, 16); set_u32(bad, 24, crc32(bad, 32));
    rejected(path, bad, output, "empty script");
    bad = valid; bad.resize(32 + 16 + 1048577); set_u32(bad, 20, 16 + 1048577);
    rejected(path, bad, output, "script cap independent of file cap");
    bad = valid; bad.resize(32 + 128 + 1048577);
    rejected(path, bad, output, "file cap");
    // Loader preserves raw syntax; the text decoder owns termination validation.
    valid.resize(49); valid[48] = 'A'; set_u32(valid, 20, 17);
    set_u32(valid, 24, crc32(valid, 32)); write_file(path, valid);
    require(ms5::load_text_resource(path, output, error) && output.script.size() == 1,
            "nonempty raw script has no naive terminator restriction");
    valid.resize(32 + 128 + 1048576, 0); set_u32(valid, 12, 0);
    set_u32(valid, 16, 16); set_u32(valid, 20, 128 + 1048576);
    for (std::uint32_t i = 0; i < 16; ++i) {
        set_u32(valid, 32 + i * 8, i); set_u32(valid, 36 + i * 8, 65535);
    }
    set_u32(valid, 24, crc32(valid, 32)); write_file(path, valid);
    require(ms5::load_text_resource(path, output, error), "maximum valid resource");
    require(output.id == 0 && output.bindings.size() == 16 && output.script.size() == 1048576,
            "maximum resource bounds");
    const ms5::TextResource before = output;
    require(std::remove(path.c_str()) == 0, "remove fixture");
    require(!ms5::load_text_resource(path, output, error) && equal_resource(output, before),
            "missing file preserves output");
    std::cout << "text_resource_test: passed\n";
    return 0;
}
