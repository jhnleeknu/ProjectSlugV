#include "ms5/fixed_data_resource.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <unistd.h>

namespace {

void check(bool value) {
    if (!value) {
        std::cerr << "fixed data resource test failed\n";
        std::exit(1);
    }
}

void put(std::vector<std::uint8_t>& bytes, std::size_t at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) {
        bytes[at + i] = static_cast<std::uint8_t>(value >> (i * 8));
    }
}

void save(const char* path, const std::vector<std::uint8_t>& bytes) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!bytes.empty()) {
        out.write(reinterpret_cast<const char*>(&bytes[0]), bytes.size());
    }
    out.close();
    check(!out.fail());
}

std::vector<std::uint8_t> fixture() {
    // Standard CRC32 check vector provides a checksum independent of the loader.
    const char payload[] = "123456789";
    std::vector<std::uint8_t> bytes(41, 0);
    bytes[0] = 'M'; bytes[1] = 'S'; bytes[2] = '5'; bytes[3] = 'D';
    put(bytes, 4, 1);
    put(bytes, 8, 1);
    put(bytes, 12, 0xffff7);
    put(bytes, 16, 0xffff7);
    put(bytes, 20, 9);
    put(bytes, 24, UINT32_C(0xcbf43926));
    for (std::size_t i = 0; i < 9; ++i) {
        bytes[32 + i] = static_cast<std::uint8_t>(payload[i]);
    }
    return bytes;
}

void reject(const char* path, const std::vector<std::uint8_t>& bytes,
            ms5::FixedDataResource& result, std::string& error) {
    const ms5::FixedDataResource before = result;
    save(path, bytes);
    error.clear();
    check(!ms5::load_fixed_data_resource(path, result, error));
    check(!error.empty());
    check(result.source_cpu_address == before.source_cpu_address);
    check(result.source_rom_offset == before.source_rom_offset);
    check(result.data == before.data);
}

} // namespace

int main() {
    char path[] = "/tmp/ms5-fixed-data-resource-XXXXXX";
    const int fd = mkstemp(path);
    check(fd >= 0);
    check(close(fd) == 0);
    const std::vector<std::uint8_t> bytes = fixture();
    ms5::FixedDataResource result;
    result.source_cpu_address = 0x1234;
    result.source_rom_offset = 0x5678;
    result.data.assign(3, 0xaa);
    std::string error = "previous failure";
    save(path, bytes);
    check(ms5::load_fixed_data_resource(path, result, error));
    check(error.empty());
    check(result.source_cpu_address == 0xffff7);
    check(result.source_rom_offset == 0xffff7);
    check(result.data == std::vector<std::uint8_t>(bytes.begin() + 32, bytes.end()));

    const unsigned int fields[] = {0, 3, 4, 8, 12, 16, 24, 28};
    for (unsigned int i = 0; i < sizeof(fields) / sizeof(fields[0]); ++i) {
        std::vector<std::uint8_t> bad = bytes;
        bad[fields[i]] ^= 1;
        reject(path, bad, result, error);
    }
    const std::uint32_t sizes[] = {0, 8, 10, 0x100001, UINT32_C(0xffffffff)};
    for (unsigned int i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i) {
        std::vector<std::uint8_t> bad = bytes;
        put(bad, 20, sizes[i]);
        reject(path, bad, result, error);
    }
    std::vector<std::uint8_t> bad = bytes;
    put(bad, 12, 0x100000);
    put(bad, 16, 0x100000);
    reject(path, bad, result, error);
    bad = bytes;
    bad[32] ^= 1;
    reject(path, bad, result, error);
    bad = bytes;
    bad.push_back(0);
    reject(path, bad, result, error);
    bad = bytes;
    bad.resize(40);
    reject(path, bad, result, error);
    bad.resize(31);
    reject(path, bad, result, error);
    bad.clear();
    reject(path, bad, result, error);
    bad.assign(32 + 1048577, 0);
    reject(path, bad, result, error);

    // The final fixed-ROM byte is a legal one-byte window.
    std::vector<std::uint8_t> last_byte = bytes;
    last_byte.resize(33);
    last_byte[32] = 0;
    put(last_byte, 12, 0xfffff);
    put(last_byte, 16, 0xfffff);
    put(last_byte, 20, 1);
    put(last_byte, 24, UINT32_C(0xd202ef8d));
    save(path, last_byte);
    check(ms5::load_fixed_data_resource(path, result, error));
    check(result.source_cpu_address == 0xfffff && result.source_rom_offset == 0xfffff);
    check(result.data.size() == 1 && result.data[0] == 0 && error.empty());

    // The full 1 MiB fixed-ROM window is legal at base zero. CRC from zlib.
    std::vector<std::uint8_t> full_window = bytes;
    full_window.resize(32 + 1048576, 0);
    for (std::size_t i = 32; i < full_window.size(); ++i) {
        full_window[i] = 0;
    }
    put(full_window, 12, 0);
    put(full_window, 16, 0);
    put(full_window, 20, 1048576);
    put(full_window, 24, UINT32_C(0xa738ea1c));
    save(path, full_window);
    check(ms5::load_fixed_data_resource(path, result, error));
    check(result.source_cpu_address == 0 && result.source_rom_offset == 0);
    check(result.data.size() == 1048576 && error.empty());

    std::vector<std::uint8_t> banked = bytes;
    put(banked,8,2); put(banked,12,0x200100); put(banked,16,0x300100);
    save(path,banked); check(ms5::load_banked_data_resource(path,result,error));
    check(result.source_cpu_address == 0x200100 && result.source_rom_offset == 0x300100);
    reject(path,banked,result,error);
    for (unsigned int kind = 0; kind < 6; ++kind) {
        std::vector<std::uint8_t> invalid = banked;
        if (kind == 0) put(invalid,8,1);
        if (kind == 1) put(invalid,16,0x300101);
        if (kind == 2) put(invalid,12,0x2fffee);
        if (kind == 3) put(invalid,16,0x800100);
        if (kind == 4) invalid[32] ^= 1;
        if (kind == 5) put(invalid,28,1);
        const ms5::FixedDataResource unchanged = result; save(path,invalid);
        check(!ms5::load_banked_data_resource(path,result,error));
        check(result.data == unchanged.data && result.source_cpu_address == unchanged.source_cpu_address && result.source_rom_offset == unchanged.source_rom_offset);
    }

    const ms5::FixedDataResource before = result;
    check(std::remove(path) == 0);
    check(!ms5::load_fixed_data_resource(path, result, error));
    check(!error.empty() && result.data == before.data);
    check(result.source_cpu_address == before.source_cpu_address);
    check(result.source_rom_offset == before.source_rom_offset);
    std::cout << "fixed_data_resource_test: passed\n";
}
