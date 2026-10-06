#include "ms5/hardware_color.h"

namespace {

#include "color_lookup.inc"

} // namespace

namespace ms5 {

RgbColor hardware_color_to_rgb(std::uint16_t word, bool shadow) {
    const unsigned int bits = word;
    const unsigned int dark = bits >> 15;
    const unsigned int red = ((bits >> 14) & 1U) | ((bits >> 7) & 30U);
    const unsigned int green = ((bits >> 13) & 1U) | ((bits >> 3) & 30U);
    const unsigned int blue = ((bits >> 12) & 1U) | ((bits << 1) & 30U);
    const unsigned int column = dark + (shadow ? 2U : 0U);
    const RgbColor color = {
        kChannelLookup[red][column],
        kChannelLookup[green][column],
        kChannelLookup[blue][column]
    };
    return color;
}

} // namespace ms5
