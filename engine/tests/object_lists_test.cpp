#include "ms5/object_lists.h"
#include "ms5/object_state.h"

#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <unistd.h>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

std::uint32_t be32(const std::vector<std::uint8_t>& ram, std::size_t offset) {
    return (static_cast<std::uint32_t>(ram[offset]) << 24) |
           (static_cast<std::uint32_t>(ram[offset + 1]) << 16) |
           (static_cast<std::uint32_t>(ram[offset + 2]) << 8) | ram[offset + 3];
}

std::uint16_t be16(const std::vector<std::uint8_t>& ram, std::size_t offset) {
    return static_cast<std::uint16_t>((ram[offset] << 8) | ram[offset + 1]);
}

void put32(std::vector<std::uint8_t>& bytes, std::size_t offset,
           std::uint32_t value, bool little) {
    for (std::size_t i = 0; i < 4; ++i) {
        bytes[offset + i] = static_cast<std::uint8_t>(value >> ((little ? i : 3 - i) * 8));
    }
}

void update_crc(std::vector<std::uint8_t>& bytes) {
    std::uint32_t crc = 0xffffffffU;
    for (std::size_t i = 32; i < 160; ++i) {
        crc ^= bytes[i];
        for (unsigned int bit = 0; bit < 8; ++bit) {
            crc = (crc >> 1) ^ ((crc & 1U) ? 0xedb88320U : 0U);
        }
    }
    put32(bytes, 24, crc ^ 0xffffffffU, true);
}

void save(const std::string& path, const std::vector<std::uint8_t>& bytes) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    output.write(reinterpret_cast<const char*>(&bytes[0]), bytes.size());
    output.close();
    require(static_cast<bool>(output), "save resource fixture");
}

bool equal_records(const std::vector<ms5::ObjectBootRecord>& left,
                   const std::vector<ms5::ObjectBootRecord>& right) {
    if (left.size() != right.size()) return false;
    for (std::size_t i = 0; i < left.size(); ++i) {
        if (left[i].ram_address != right[i].ram_address ||
            left[i].callback != right[i].callback) return false;
        for (std::size_t j = 0; j < 4; ++j) {
            if (left[i].words[j] != right[i].words[j]) return false;
        }
    }
    return true;
}

} // namespace

int main() {
    std::vector<ms5::ObjectBootRecord> records(8);
    std::vector<std::uint8_t> resource(160, 0);
    resource[0] = 'M'; resource[1] = 'S'; resource[2] = '5'; resource[3] = 'I';
    put32(resource, 4, 1, true); put32(resource, 8, 8, true);
    put32(resource, 12, 16, true); put32(resource, 16, 0x268a, true);
    put32(resource, 20, 128, true);
    // Descending addresses distinguish table order from memory order.
    for (std::size_t i = 0; i < 8; ++i) {
        records[i].ram_address = static_cast<std::uint32_t>(0x100820 + (7 - i) * 0xc4);
        records[i].callback = static_cast<std::uint32_t>(0x2800 + 2 * i);
        put32(resource, 32 + 16 * i, records[i].ram_address, false);
        put32(resource, 36 + 16 * i, records[i].callback, false);
        for (std::size_t j = 0; j < 4; ++j) {
            records[i].words[j] = static_cast<std::uint16_t>(0x8100 + 16 * i + j);
            resource[40 + 16 * i + 2 * j] = static_cast<std::uint8_t>(records[i].words[j] >> 8);
            resource[41 + 16 * i + 2 * j] = static_cast<std::uint8_t>(records[i].words[j]);
        }
    }
    update_crc(resource);
    char fixture_path[] = "/tmp/ms5-object-lists-XXXXXX";
    const int descriptor = mkstemp(fixture_path);
    require(descriptor >= 0, "create temporary fixture");
    close(descriptor);
    const std::string path(fixture_path);
    save(path, resource);
    std::string error;
    std::vector<ms5::ObjectBootRecord> loaded;
    require(ms5::load_object_boot_resource(path, loaded, error), "load valid resource");
    require(error.empty() && equal_records(loaded, records), "decoded endian values");
    for (std::size_t offset = 0; offset < resource.size(); ++offset) {
        std::vector<std::uint8_t> corrupt = resource;
        corrupt[offset] ^= 1;
        save(path, corrupt);
        require(!ms5::load_object_boot_resource(path, loaded, error), "reject corruption");
        require(!error.empty() && equal_records(loaded, records), "transactional failed load");
    }
    for (std::size_t length = 1; length <= 161; ++length) {
        if (length == 160) continue;
        std::vector<std::uint8_t> malformed = resource;
        malformed.resize(length);
        save(path, malformed);
        require(!ms5::load_object_boot_resource(path, loaded, error), "reject wrong length");
        require(equal_records(loaded, records), "wrong length preserves table");
    }
    const std::uint32_t invalid_values[] = {0x100821U, 0x10081eU, 0x100dd6U, 0x100820U};
    for (std::size_t i = 0; i < 4; ++i) {
        std::vector<std::uint8_t> malformed = resource;
        put32(malformed, 32, invalid_values[i], false);
        update_crc(malformed);
        save(path, malformed);
        require(!ms5::load_object_boot_resource(path, loaded, error), "reject invalid address or overlap");
        require(equal_records(loaded, records), "invalid record preserves table");
    }
    for (std::size_t i = 0; i < 2; ++i) {
        std::vector<std::uint8_t> malformed = resource;
        put32(malformed, 36, i == 0 ? 0x2801U : 0x100000U, false);
        update_crc(malformed);
        save(path, malformed);
        require(!ms5::load_object_boot_resource(path, loaded, error), "reject invalid callback");
    }
    std::remove(path.c_str());
    require(!ms5::load_object_boot_resource(path, loaded, error), "reject missing file");

    std::vector<std::uint8_t> ram(65536 + 19, 0xa5);
    for (std::size_t i = 0; i < ram.size(); ++i) ram[i] = static_cast<std::uint8_t>((i * 73 + 19) & 0xffU);
    const std::vector<std::uint8_t> before = ram;
    require(ms5::initialize_object_lists(&ram[0], ram.size(), records, error), "valid initialization");
    require(error.empty(), "success clears error");
    std::vector<std::uint8_t> touched(ram.size(), 0);
    for (std::size_t i = 0; i < 8; ++i) {
        const std::size_t offset = records[i].ram_address - 0x100000U;
        require(be32(ram, offset) == records[i].callback, "boot callback");
        require(be32(ram, offset + 4) == records[(i + 7) % 8].ram_address, "boot previous link");
        require(be32(ram, offset + 8) == records[(i + 1) % 8].ram_address, "boot next link");
        require(be32(ram, offset + 0xc) == 0 && be16(ram, offset + 0x10) == 0, "boot clears");
        for (std::size_t j = 0; j < 4; ++j) require(be16(ram, offset + 0x76 + j * 2) == records[i].words[j], "boot words");
        std::vector<std::uint8_t> expected(before.begin() + offset, before.begin() + offset + 0xc4);
        require(ms5::reset_object_fields(&expected[0], expected.size()), "reference reset");
        for (std::size_t j = 0; j < 0xc4; ++j) {
            touched[offset + j] = 1;
            if (j >= 0x12 && (j < 0x76 || j >= 0x7e)) require(ram[offset + j] == expected[j], "boot other fields preserved or reset");
        }
    }
    require(be16(ram, 0x4ca0) == 80 && be16(ram, 0x4ca2) == 0, "free and pending counts");
    require(be32(ram, 0x4c9c) == 0x100f5cU, "free head");
    for (std::size_t i = 0; i < 80; ++i) {
        const std::size_t offset = 0xf5c + 0xc4 * i;
        require(be32(ram, offset) == 0x270eU, "free callback");
        require(be32(ram, offset + 8) == (i == 79 ? 0U : 0x100000U + offset + 0xc4), "free next link");
        std::vector<std::uint8_t> expected(before.begin() + offset, before.begin() + offset + 0xc4);
        require(ms5::reset_object_fields(&expected[0], expected.size()), "reference free reset");
        for (std::size_t j = 0; j < 0xc4; ++j) {
            touched[offset + j] = 1;
            if (j >= 4 && (j < 8 || j >= 0xc)) require(ram[offset + j] == expected[j], "free fields preserve original reset behavior");
        }
        require(be32(ram, offset + 4) == be32(before, offset + 4), "free previous pointer preserved");
        require(be32(ram, offset + 0xc) == be32(before, offset + 0xc), "free auxiliary pointer preserved");
        require(be16(ram, offset + 0x10) == be16(before, offset + 0x10), "free word preserved");
    }
    for (std::size_t offset = 0xe98; offset < 0xf5c; ++offset) {
        touched[offset] = 1;
        if (offset >= 0xea8) require(ram[offset] == 0, "sentinel clear");
    }
    require(be32(ram, 0xe98) == 0x270eU && be32(ram, 0xe9c) == 0x100e98U &&
            be32(ram, 0xea0) == 0x100e98U && be32(ram, 0xea4) == 0x100e98U, "sentinel fields");
    for (std::size_t offset = 0x4c9c; offset < 0x4ca4; ++offset) touched[offset] = 1;
    for (std::size_t i = 0; i < ram.size(); ++i) if (!touched[i]) require(ram[i] == before[i], "unrelated RAM preserved");
    const std::vector<std::uint8_t> initialized = ram;
    require(ms5::initialize_object_lists(&ram[0], ram.size(), records, error), "repeat init");
    require(ram == initialized, "initialization idempotent");
    for (std::size_t length = 0; length < 65536; length += 127) {
        require(!ms5::initialize_object_lists(&ram[0], length, records, error), "short RAM rejected");
        require(ram == initialized, "short RAM no writes");
    }
    require(!ms5::initialize_object_lists(NULL, 65536, records, error), "null RAM rejected");
    for (std::size_t kind = 0; kind < 5; ++kind) {
        std::vector<ms5::ObjectBootRecord> invalid = records;
        if (kind == 0) invalid.pop_back();
        if (kind == 1) invalid[7].ram_address = invalid[0].ram_address;
        if (kind == 2) invalid[7].ram_address = 0x100000;
        if (kind == 3) invalid[7].callback = 0x270f;
        if (kind == 4) invalid[7].callback = 0x100000;
        require(!ms5::initialize_object_lists(&ram[0], ram.size(), invalid, error), "invalid table rejected");
        require(!error.empty() && ram == initialized, "invalid table no writes");
    }
    std::cout << "object_lists_test: passed\n";
    return 0;
}
