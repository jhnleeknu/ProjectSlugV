#ifndef MS5_SOUND_WORD_H
#define MS5_SOUND_WORD_H
#include "ms5/sound_byte.h"
namespace ms5 {
// kind: 0 complete, 1 overflow enqueue, 2 drain.
// phase: 0 complete, 1 waiting for high byte, 2 waiting for low byte.
struct SoundWordPending {
    std::uint8_t kind,phase,low;
    std::uint16_t cursor;
    SoundBytePending byte;
    SoundWordPending() : kind(0),phase(0),low(0),cursor(0) {}
};
// Native 3af8. external_status supplies the conditional byte read at d00046.
bool enqueue_sound_word(std::vector<std::uint8_t>& ram,std::uint16_t command,
                        std::uint8_t external_status,SoundWordPending& pending,std::string& error);
// Native 3c08; head is published only after the drain reaches live tail.
bool drain_sound_words(std::vector<std::uint8_t>& ram,SoundWordPending& pending,std::string& error);
bool resume_sound_word(std::vector<std::uint8_t>& ram,SoundWordPending& pending,std::string& error);
}
#endif
