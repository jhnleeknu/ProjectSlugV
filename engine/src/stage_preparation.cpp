#include "ms5/stage_preparation.h"
#include "ms5/object_removal.h"
#include <new>
namespace ms5 {
namespace {
void put_long(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (24 - 8*i));
}
bool valid(const std::vector<std::uint8_t>& ram, const StagePreparationState& state, std::string& error) {
    if (ram.size() != 65536 || (state.a6 & 1U) || state.a6 < 0x100000 || state.a6 > 0x110000 - 0xc4) {
        error = "stage preparation requires 64KiB RAM and aligned c4-byte A6 span"; return false;
    }
    return true;
}
}
bool clear_stage_objects(std::vector<std::uint8_t>& ram, StagePreparationState& state,
                         std::vector<VideoPortWrite>& ports, std::string& error) {
    if (!valid(ram,state,error)) return false;
    try {
        std::vector<std::uint8_t> candidate = ram; StagePreparationState next = state;
        std::vector<VideoPortWrite> output, removed;
        RemovalState removal; removal.d0 = next.d0; removal.d1 = next.d1; removal.d3 = next.d3; removal.a6 = next.a6;
        if (!remove_objects(candidate,0x2a0a,0,removal,output,error)) return false;
        if (!remove_objects(candidate,0x2a84,0x100bf4,removal,removed,error)) return false;
        output.insert(output.end(),removed.begin(),removed.end());
        next.d0 = 0; next.d1 = removal.d1; next.d3 = removal.d3; next.a6 = removal.a6;
        candidate[0x7dec] = 0; candidate[0x4d91] &= 0xef;
        put_long(candidate,6,0x3dcc); put_long(candidate,0xa,0x3dcc);
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage object transaction"; return false; }
}
bool prepare_stage_body(std::vector<std::uint8_t>& ram, const FixedDataResource& main_bindings,
                        const FixedDataResource& stage_bindings, StagePreparationState& state,
                        std::vector<VideoPortWrite>& ports, std::string& error) {
    if (!valid(ram,state,error)) return false;
    try {
        std::vector<std::uint8_t> candidate = ram; StagePreparationState next = state;
        std::vector<VideoPortWrite> output, removed;
        if (!initialize_stage_palettes(candidate,main_bindings,stage_bindings,next.d0,next.d1,next.d3,output,error)) return false;
        if (!clear_stage_objects(candidate,next,removed,error)) return false;
        output.insert(output.end(),removed.begin(),removed.end());
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage body transaction"; return false; }
}
}
