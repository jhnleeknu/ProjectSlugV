#ifndef MS5_OBJECT_REMOVAL_H
#define MS5_OBJECT_REMOVAL_H
#include "ms5/video_port.h"
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
struct RemovalState {
    std::uint32_t d0, d1, d3, a6;
    RemovalState() : d0(0), d1(0), d3(0), a6(0) {}
};
// Confirmed native entries 299c, 2a0a, 2a84 and c4cc. Target is 2a84's
// absolute CPU RAM A0; other entries ignore it. Used objects require aligned
// complete c4-byte RAM spans. Original TRAP and outside RAM writes excluded.
// A bounded 65536-operation budget rejects malformed loops. Errors preserve
// RAM, state and ports. Other registers, CCR and callback execution excluded.
bool remove_objects(std::vector<std::uint8_t>& ram, std::uint32_t entry,
                    std::uint32_t target, RemovalState& state,
                    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
