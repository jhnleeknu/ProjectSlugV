#ifndef MS5_SOUND_SERVICE_H
#define MS5_SOUND_SERVICE_H
#include "ms5/sound_word.h"
#include "ms5/sound_queue.h"
namespace ms5 {
// Native 3cac: timer producer 48156, then consumer 3cb2. A pending producer
// leaves read_count=0 and emits no ports. Completed service reads status once.
// Supplied status is used only when the consumer is actually reached.
bool step_sound(std::vector<std::uint8_t>& ram,std::uint8_t external_status,
                std::uint8_t sound_status,SoundWordPending& pending,
                std::uint8_t& read_count,std::vector<VideoPortWrite>& writes,std::string& error);
// Resume an overflow producer from this service; do not run the timer again.
// Pass the sound status sampled at completion, not at the original suspension.
bool resume_sound(std::vector<std::uint8_t>& ram,std::uint8_t sound_status,
                  SoundWordPending& pending,std::uint8_t& read_count,
                  std::vector<VideoPortWrite>& writes,std::string& error);
}
#endif
