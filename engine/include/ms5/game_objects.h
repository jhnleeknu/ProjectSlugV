#ifndef MS5_GAME_OBJECTS_H
#define MS5_GAME_OBJECTS_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
// Native 1bcfe (including fallthrough into 1bd12), or 1bd12 alone.
// Fixed objects at CPU 100cb8 and 100da8; D0 upper word is preserved.
// Any callback except 270e is active, including zero. Entry 1bd12 follows
// live object+8c pointers, requiring aligned 12-byte spans in CPU RAM.
// Errors preserve RAM and D0. Other data registers are untouched.
bool reset_game_objects(std::vector<std::uint8_t>& ram, std::uint32_t entry,
                        std::uint32_t& d0, std::string& error);
}
#endif
