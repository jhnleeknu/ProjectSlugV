#ifndef MS5_MAIN_STARTUP_H
#define MS5_MAIN_STARTUP_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
#include <cstddef>
namespace ms5 {
// Shared verified e7bf4 palette helper. Final full D0=0x60, D1.low=1
// with high word preserved; D3.low holds last relink with high preserved.
// A5=108000 is implicit; failure preserves RAM, registers and ports.
bool initialize_main_palettes(std::vector<std::uint8_t>& ram,
                              const FixedDataResource& bindings,std::uint32_t& d0,
                              std::uint32_t& d1,std::uint32_t& d3,
                              std::vector<VideoPortWrite>& ports,std::string& error);
// Native e4a..e74 startup. Object is an even RAM offset with 0x85 bytes.
// Bindings use the fixed e7b58 window: seventeen six-byte records and ffff.
// Releases fixed palette references, prepends bindings to bucket heads, sets
// slot6 blend and resets controller/object startup fields. Does not run e74.
// A5=108000 is implicit. Final D0=0; D1.low=1 with upper word preserved;
// D3.low is the last actual list relink value with upper word preserved.
// Success replaces ordered hardware writes; failure preserves every output.
bool initialize_main_frame(std::vector<std::uint8_t>& ram,std::size_t object,
                           const FixedDataResource& bindings,std::uint32_t& d0,
                           std::uint32_t& d1,std::uint32_t& d3,
                           std::vector<VideoPortWrite>& ports,std::string& error);
}
#endif
