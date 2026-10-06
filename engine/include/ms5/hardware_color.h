#ifndef MS5_HARDWARE_COLOR_H
#define MS5_HARDWARE_COLOR_H

#include <cstdint>

namespace ms5 {

struct RgbColor {
    std::uint8_t red;
    std::uint8_t green;
    std::uint8_t blue;
};

// Convert one Neo Geo palette word using the channel resistor lookup.
// Bit 15 selects the dark component; shadow selects the global shadow mode.
RgbColor hardware_color_to_rgb(std::uint16_t word, bool shadow);

} // namespace ms5

#endif
