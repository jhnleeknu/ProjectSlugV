#ifndef MS5_SOUND_QUEUE_H
#define MS5_SOUND_QUEUE_H
#include "ms5/video_port.h"
#include <string>
#include <vector>
namespace ms5 {
// Native 3cb2..3d38: consumes one supplied 320000 status byte. The producer
// call at 3cac/48156 is separate. Used nonempty queue indices must be 0..127.
// Failure preserves RAM/writes. Success emits zero or one sound-port byte write.
bool service_sound_queue(std::vector<std::uint8_t>& ram,std::uint8_t status,
                         std::vector<VideoPortWrite>& writes,std::string& error);
}
#endif
