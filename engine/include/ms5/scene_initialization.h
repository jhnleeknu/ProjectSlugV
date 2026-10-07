#ifndef MS5_SCENE_INITIALIZATION_H
#define MS5_SCENE_INITIALIZATION_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
namespace ms5 {
// Native1afda debug update, including intentional repeated first-node check.
// Tables are the512-byte fixed CPU/ROM1af12 MS5D window. Errors preserve
// RAM/fullD0D1D3/orderedports. No otherregisters/CCR/hardwaretiming contract.
bool update_scene_debug(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
                        std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3,
                        std::vector<VideoPortWrite>& ports, std::string& error);
// Confirmed477e4 prefix: native1a5a4 with null scriptA0, to477ee boundary.
// Arbitrary nonzero scene scripts/19e64 traversal are outside this API.
bool initialize_stage_scene(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
                            std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3,
                            std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
