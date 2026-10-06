#include "ms5/object_lists.h"
#include "ms5/object_state.h"

#include <fstream>

namespace {

std::uint32_t read_le32(const std::uint8_t* bytes) {
    return static_cast<std::uint32_t>(bytes[0]) |
           (static_cast<std::uint32_t>(bytes[1]) << 8) |
           (static_cast<std::uint32_t>(bytes[2]) << 16) |
           (static_cast<std::uint32_t>(bytes[3]) << 24);
}

std::uint16_t read_be16(const std::uint8_t* bytes) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(bytes[0]) << 8) | bytes[1]);
}

std::uint32_t read_be32(const std::uint8_t* bytes) {
    return (static_cast<std::uint32_t>(bytes[0]) << 24) |
           (static_cast<std::uint32_t>(bytes[1]) << 16) |
           (static_cast<std::uint32_t>(bytes[2]) << 8) | bytes[3];
}

void write_be16(std::uint8_t* bytes, std::uint16_t value) {
    bytes[0] = static_cast<std::uint8_t>(value >> 8);
    bytes[1] = static_cast<std::uint8_t>(value);
}

void write_be32(std::uint8_t* bytes, std::uint32_t value) {
    bytes[0] = static_cast<std::uint8_t>(value >> 24);
    bytes[1] = static_cast<std::uint8_t>(value >> 16);
    bytes[2] = static_cast<std::uint8_t>(value >> 8);
    bytes[3] = static_cast<std::uint8_t>(value);
}

std::uint32_t crc32(const std::uint8_t* bytes, std::size_t size) {
    std::uint32_t crc = 0xffffffffU;
    for (std::size_t i = 0; i < size; ++i) {
        crc ^= bytes[i];
        for (unsigned int bit = 0; bit < 8; ++bit) {
            crc = (crc >> 1) ^ ((crc & 1U) ? 0xedb88320U : 0U);
        }
    }
    return crc ^ 0xffffffffU;
}

bool validate_records(const std::vector<ms5::ObjectBootRecord>& records,
                      std::string& error) {
    if (records.size() != 8) {
        error = "object boot table must contain eight records";
        return false;
    }
    for (std::size_t i = 0; i < records.size(); ++i) {
        const ms5::ObjectBootRecord& record = records[i];
        if ((record.ram_address & 1U) != 0 ||
            record.ram_address < 0x100820U ||
            record.ram_address > 0x100e98U - 0xc4U) {
            error = "invalid boot object RAM address";
            return false;
        }
        if ((record.callback & 1U) != 0 || record.callback >= 0x100000U) {
            error = "invalid boot object callback address";
            return false;
        }
        for (std::size_t j = 0; j < i; ++j) {
            if (record.ram_address < records[j].ram_address + 0xc4U &&
                records[j].ram_address < record.ram_address + 0xc4U) {
                error = "overlapping boot objects";
                return false;
            }
        }
    }
    return true;
}

} // namespace

namespace ms5 {

bool load_object_boot_resource(const std::string& path,
                               std::vector<ObjectBootRecord>& records,
                               std::string& error) {
    std::ifstream input(path.c_str(), std::ios::binary);
    if (!input) {
        error = "cannot open object boot resource";
        return false;
    }
    // Read a bounded buffer and probe EOF, including trailing-byte rejection.
    std::uint8_t bytes[160];
    input.read(reinterpret_cast<char*>(bytes), sizeof(bytes));
    if (input.gcount() != static_cast<std::streamsize>(sizeof(bytes)) ||
        input.bad()) {
        error = "object boot resource must be exactly 160 bytes";
        return false;
    }
    char extra;
    if (input.get(extra) || input.bad() || !input.eof()) {
        error = "object boot resource must be exactly 160 bytes";
        return false;
    }
    if (bytes[0] != 'M' || bytes[1] != 'S' || bytes[2] != '5' || bytes[3] != 'I' ||
        read_le32(bytes + 4) != 1 || read_le32(bytes + 8) != 8 ||
        read_le32(bytes + 12) != 16 || read_le32(bytes + 16) != 0x268a ||
        read_le32(bytes + 20) != 128 || read_le32(bytes + 28) != 0) {
        error = "invalid MS5I v1 header";
        return false;
    }
    if (read_le32(bytes + 24) != crc32(bytes + 32, 128)) {
        error = "object boot resource payload CRC32 mismatch";
        return false;
    }
    std::vector<ObjectBootRecord> loaded(8);
    for (std::size_t i = 0; i < loaded.size(); ++i) {
        const std::uint8_t* record = bytes + 32 + i * 16;
        loaded[i].ram_address = read_be32(record);
        loaded[i].callback = read_be32(record + 4);
        for (std::size_t word = 0; word < 4; ++word) {
            loaded[i].words[word] = read_be16(record + 8 + word * 2);
        }
    }
    if (!validate_records(loaded, error)) {
        return false;
    }
    records.swap(loaded);
    error.clear();
    return true;
}

bool initialize_object_lists(std::uint8_t* ram, std::size_t size,
                             const std::vector<ObjectBootRecord>& records,
                             std::string& error) {
    if (ram == NULL || size < 65536) {
        error = "RAM must contain at least 65536 bytes at CPU 0x100000";
        return false;
    }
    if (!validate_records(records, error)) {
        return false;
    }
    for (std::size_t i = 0; i < records.size(); ++i) {
        const ObjectBootRecord& record = records[i];
        std::uint8_t* object = ram + record.ram_address - 0x100000U;
        reset_object_fields(object, 0xc4);
        write_be32(object, record.callback);
        for (std::size_t word = 0; word < 4; ++word) {
            write_be16(object + 0x76 + word * 2, record.words[word]);
        }
        write_be32(object + 0xc, 0);
        write_be16(object + 0x10, 0);
        if (i == 0) {
            write_be32(object + 4, record.ram_address);
            write_be32(object + 8, record.ram_address);
        } else {
            const std::uint32_t previous_address = records[i - 1].ram_address;
            std::uint8_t* previous = ram + previous_address - 0x100000U;
            const std::uint32_t next_address = read_be32(previous + 8);
            std::uint8_t* next = ram + next_address - 0x100000U;
            write_be32(next + 4, record.ram_address);
            write_be32(previous + 8, record.ram_address);
            write_be32(object + 4, previous_address);
            write_be32(object + 8, next_address);
        }
    }
    write_be16(ram + 0x4ca0, 0);
    write_be32(ram + 0x4c9c, 0x100f5cU);
    for (std::size_t i = 0; i < 80; ++i) {
        const std::size_t offset = 0xf5c + i * 0xc4;
        std::uint8_t* object = ram + offset;
        reset_object_fields(object, 0xc4);
        write_be32(object, 0x270eU);
        write_be16(ram + 0x4ca0, static_cast<std::uint16_t>(i + 1));
        write_be32(object + 8, i == 79 ? 0U :
                   static_cast<std::uint32_t>(0x100000U + offset + 0xc4));
    }
    write_be16(ram + 0x4ca2, 0);
    for (std::size_t offset = 0xe98; offset < 0xf5c; ++offset) {
        ram[offset] = 0;
    }
    write_be32(ram + 0xe98, 0x270eU);
    write_be32(ram + 0xe9c, 0x100e98U);
    write_be32(ram + 0xea0, 0x100e98U);
    write_be32(ram + 0xea4, 0x100e98U);
    error.clear();
    return true;
}

} // namespace ms5
