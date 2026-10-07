#ifndef MS5_SOUND_BYTE_H
#define MS5_SOUND_BYTE_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
struct SoundBytePending {
    bool waiting;
    std::uint8_t command;
    std::uint16_t tail,next;
    SoundBytePending() : waiting(false),command(0),tail(0),next(0) {}
};
// Native 3ac8. Full queue returns waiting=true and retains captured write slot.
// Native command3 sets the priority flag, bypassing the ring indices.
// Normal used indices must be 0..127. Errors preserve RAM/pending.
bool enqueue_sound_byte(std::vector<std::uint8_t>& ram,std::uint8_t command,
                        SoundBytePending& pending,std::string& error);
// Native 3aea continuation: reads live head, but does not reload RAM tail.
bool resume_sound_byte(std::vector<std::uint8_t>& ram,SoundBytePending& pending,
                       std::string& error);
}
#endif
