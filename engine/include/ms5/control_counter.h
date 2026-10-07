#ifndef MS5_CONTROL_COUNTER_H
#define MS5_CONTROL_COUNTER_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
// Originalfe2..1000: compare object+7e word with RAM000e, then advance both
// and call43dbc to set RAMd494=(old&1)+1. All addresses are CPU addresses;
// RAM maps64KiB at100000. Object must be even with a complete0x80-byte span.
// A mismatch succeeds with trap15=true and unchanged RAM, stopping before
// the original trap instruction. This does not execute its exception handler.
// Equal counters wrap at16bits. Sequential writes are preserved even if the
// object's counter aliases the phase byte. Invalid input preserves RAM/trap15.
bool advance_control_counter(std::vector<std::uint8_t>& ram,
                             std::uint32_t object_address,bool& trap15,
                             std::string& error);
}
#endif
