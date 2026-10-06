#include "ms5/stage_catalog.h"
#include "ms5/fixed_data_resource.h"

#include <new>

namespace ms5 {
namespace {

const std::uint32_t fixed_limit = 0x100000U;
const std::uint32_t index_address = 0x474f4U;
const std::size_t group_count = 19U;

std::uint16_t read_u16(const std::uint8_t* bytes) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(bytes[0]) << 8) | bytes[1]);
}

std::uint32_t read_u32(const std::uint8_t* bytes) {
    return (static_cast<std::uint32_t>(bytes[0]) << 24) |
           (static_cast<std::uint32_t>(bytes[1]) << 16) |
           (static_cast<std::uint32_t>(bytes[2]) << 8) |
           static_cast<std::uint32_t>(bytes[3]);
}

bool fail(std::string& error, const char* message) {
    error = message;
    return false;
}

std::string resource_path(const std::string& directory, const std::string& file) {
    if (directory.empty() || directory[directory.size() - 1U] == '/') {
        return directory + file;
    }
    return directory + "/" + file;
}

bool valid_payload(const std::vector<std::uint8_t>& data) {
    if (data.size() < 20U || data.size() > 32766U || (data.size() & 1U)) {
        return false;
    }
    for (std::size_t i = 18U; i < data.size(); ++i) {
        if (data[i] == 0U) {
            return true;
        }
    }
    return false;
}

bool decode_group(const FixedDataResource& resource, StageGroup& group,
                  std::string& error) {
    const std::uint32_t base = resource.source_cpu_address;
    if ((base & 1U) || base >= fixed_limit || base != resource.source_rom_offset ||
        resource.data.size() < 4U || resource.data.size() > fixed_limit - base) {
        return fail(error, "stage group must map an even fixed ROM window of at least four bytes");
    }
    group.source_cpu_address = base;
    group.header = read_u16(&resource.data[0]);
    std::size_t cursor = 2U;
    for (;;) {
        if (resource.data.size() - cursor < 2U) {
            return fail(error, "stage group terminator is missing or truncated");
        }
        const std::uint16_t length = read_u16(&resource.data[cursor]);
        cursor += 2U;
        if (length == 0U) {
            if (cursor != resource.data.size()) {
                return fail(error, "stage group has trailing data after its terminator");
            }
            return true;
        }
        if (length < 20U || length >= 0x8000U || (length & 1U)) {
            return fail(error, "stage record length must be positive, even, and at least twenty bytes");
        }
        if (length > resource.data.size() - cursor) {
            return fail(error, "stage record payload is truncated");
        }
        if (group.records.size() >= 65535U) {
            return fail(error, "stage group exceeds the sixteen-bit record count");
        }
        StageRecord record;
        record.source_cpu_address = base + static_cast<std::uint32_t>(cursor);
        record.data.assign(resource.data.begin() + cursor,
                           resource.data.begin() + cursor + length);
        if (!valid_payload(record.data)) {
            return fail(error, "stage record text has no zero terminator");
        }
        group.records.push_back(record);
        cursor += length;
    }
}

bool validate_group(const StageGroup& group, std::string& error) {
    const std::uint32_t base = group.source_cpu_address;
    if ((base & 1U) || base >= fixed_limit || fixed_limit - base < 4U) {
        return fail(error, "stage group address must be even and within fixed ROM");
    }
    if (group.records.size() > 65535U) {
        return fail(error, "stage group exceeds the sixteen-bit record count");
    }
    std::uint32_t cursor = base + 2U;
    for (std::size_t i = 0; i < group.records.size(); ++i) {
        const StageRecord& entry = group.records[i];
        if (fixed_limit - cursor < 2U) {
            return fail(error, "stage record length word lies outside fixed ROM");
        }
        cursor += 2U;
        if (entry.source_cpu_address != cursor || !valid_payload(entry.data) ||
            entry.data.size() > fixed_limit - cursor) {
            return fail(error, "stage record payload or source address is invalid");
        }
        cursor += static_cast<std::uint32_t>(entry.data.size());
    }
    if (fixed_limit - cursor < 2U) {
        return fail(error, "stage group terminator lies outside fixed ROM");
    }
    return true;
}

} // namespace

bool load_stage_catalog(const std::string& directory, StageCatalog& catalog,
                        std::string& error) {
    StageCatalog candidate;
    try {
        FixedDataResource index;
        if (!load_fixed_data_resource(resource_path(directory, "stage_index.ms5d"),
                                      index, error)) {
            return false;
        }
        if (index.source_cpu_address != index_address || index.source_rom_offset != index_address ||
            index.data.size() != 76U) {
            return fail(error, "stage index must contain nineteen pointers at CPU address 0x474f4");
        }
        candidate.groups.resize(group_count);
        for (std::size_t i = 0; i < group_count; ++i) {
            std::string filename = "stage_group_";
            filename += static_cast<char>('0' + i / 10U);
            filename += static_cast<char>('0' + i % 10U);
            filename += ".ms5d";
            FixedDataResource resource;
            if (!load_fixed_data_resource(resource_path(directory, filename), resource, error)) {
                return false;
            }
            const std::uint32_t expected = read_u32(&index.data[i * 4U]);
            if (resource.source_cpu_address != expected) {
                return fail(error, "stage group source address does not match the index pointer");
            }
            if (!decode_group(resource, candidate.groups[i], error)) {
                return false;
            }
        }
    } catch (const std::bad_alloc&) {
        return fail(error, "cannot allocate stage catalog");
    }
    catalog.groups.swap(candidate.groups);
    error.clear();
    return true;
}

bool query_stage(const StageCatalog& catalog, std::uint16_t stage,
                 std::uint16_t area, std::uint16_t& count,
                 std::uint32_t& record, std::uint32_t& name,
                 std::string& error) {
    if (catalog.groups.size() != group_count) {
        return fail(error, "stage catalog must contain nineteen groups");
    }
    const std::size_t selected = stage < group_count ? stage : 0U;
    const StageGroup& group = catalog.groups[selected];
    if (!validate_group(group, error)) {
        return false;
    }
    const std::uint16_t result_count = static_cast<std::uint16_t>(group.records.size());
    std::uint32_t result_record = 0U;
    std::uint32_t result_name = 0U;
    if (area < group.records.size()) {
        result_record = group.records[area].source_cpu_address;
        result_name = result_record + 18U;
    }
    count = result_count;
    record = result_record;
    name = result_name;
    error.clear();
    return true;
}

} // namespace ms5
