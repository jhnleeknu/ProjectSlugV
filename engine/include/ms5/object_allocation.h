#ifndef MS5_OBJECT_ALLOCATION_H
#define MS5_OBJECT_ALLOCATION_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
struct AllocationState {
    std::uint32_t d0, a0, a1, a6;
    bool carry;
    AllocationState() : d0(0), a0(0), a1(0), a6(0), carry(false) {}
};
// Native 28ae. Unsigned D0.word threshold and zero callback return carry=false
// with A0=100e98, preserving RAM/D0/A1/A6. Success retains native access order.
// Dereferenced pointers must address aligned complete spans in 64KiB CPU RAM;
// native writes through zero/outside pointers are unsupported. Errors preserve
// RAM and the entire input state.
bool allocate_object(std::vector<std::uint8_t>& ram, AllocationState& state,
                     std::string& error);
// Native 4fb1a conditional wrapper; carry reports its allocation result,
// rather than full CCR. It writes live parent+62 to 0 on success, ff otherwise.
// Callback 4fb64 is stored only; executing that callback is outside this API.
bool request_game_object(std::vector<std::uint8_t>& ram, AllocationState& state,
                         std::string& error);
}
#endif
