#ifndef MS5_OBJECT_STATE_H
#define MS5_OBJECT_STATE_H

#include <cstddef>
#include <cstdint>

namespace ms5 {

// Memory effects of the original 68000 routine at CPU address 0x00271c,
// including its helper calls. Offsets below refer to the object byte buffer,
// not ROM file offsets. This is not a full emulator: registers, condition
// flags, and call-stack effects are outside this function's contract.
// Requires at least 0xc4 bytes. Invalid input returns false without writes.
// Success preserves every byte not written by the original routine.
bool reset_object_fields(std::uint8_t* object, std::size_t size);

} // namespace ms5

#endif
