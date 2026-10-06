#ifndef MS5_STAGE_CATALOG_H
#define MS5_STAGE_CATALOG_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

struct StageRecord {
    // Address of the payload, immediately after its two-byte length word.
    std::uint32_t source_cpu_address;
    // Opaque 18-byte header, control-byte text, and original even padding.
    std::vector<std::uint8_t> data;

    StageRecord() : source_cpu_address(0) {}
};

struct StageGroup {
    std::uint32_t source_cpu_address;
    std::uint16_t header;
    std::vector<StageRecord> records;

    StageGroup() : source_cpu_address(0), header(0) {}
};

struct StageCatalog {
    std::vector<StageGroup> groups;
};

// Load stage_index.ms5d and stage_group_00.ms5d through stage_group_18.ms5d.
// Failure preserves catalog; success clears error. Text remains raw ROM bytes.
bool load_stage_catalog(const std::string& directory, StageCatalog& catalog,
                        std::string& error);

// Stage words >= 19 select group zero. Out-of-range areas return zero pointers.
// Record points to the payload and name points 18 bytes beyond it.
// Failure preserves all three output values; success clears error.
bool query_stage(const StageCatalog& catalog, std::uint16_t stage,
                 std::uint16_t area, std::uint16_t& count,
                 std::uint32_t& record, std::uint32_t& name,
                 std::string& error);

} // namespace ms5

#endif
