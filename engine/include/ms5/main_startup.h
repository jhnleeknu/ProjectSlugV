#ifndef MS5_MAIN_STARTUP_H
#define MS5_MAIN_STARTUP_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
#include <cstddef>
namespace ms5 {
struct PaletteBindingState {
    std::uint32_t d0, d1, d2, d3, d4, a0, a1, a2, a4;
    PaletteBindingState() : d0(0), d1(0), d2(0), d3(0), d4(0), a0(0), a1(0), a2(0), a4(0) {}
};
// Generic native8da2 registration of an exact terminated fixed or banked ROM window.
// Failure preserves full RAM/state/ports; success replaces ordered writes.
bool bind_palette_resource(std::vector<std::uint8_t>& ram, const FixedDataResource& bindings,
    PaletteBindingState& state, std::vector<VideoPortWrite>& ports, std::string& error);

// Shared verified e7bf4 palette helper. Final full D0=0x60, D1.low=1
// with high word preserved; D3.low holds last relink with high preserved.
// A5=108000 is implicit; failure preserves RAM, registers and ports.
bool initialize_main_palettes(std::vector<std::uint8_t>& ram,
                              const FixedDataResource& bindings,std::uint32_t& d0,
                              std::uint32_t& d1,std::uint32_t& d3,
                              std::vector<VideoPortWrite>& ports,std::string& error);
// Native e7c36: main helper then four e7bda bindings. Final D0=ffff,
// D1.low=last source and D3.low=last actual relink, upper words preserved.
// Failure preserves RAM, full registers and ports, including late table errors.
bool initialize_stage_palettes(std::vector<std::uint8_t>& ram,
                               const FixedDataResource& main_bindings, const FixedDataResource& stage_bindings,
                               std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3,
                               std::vector<VideoPortWrite>& ports, std::string& error);
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
