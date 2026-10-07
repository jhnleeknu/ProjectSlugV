#ifndef MS5_FORMATTED_TEXT_H
#define MS5_FORMATTED_TEXT_H
#include "ms5/fixed_text.h"
namespace ms5 {
// CPU3a70 using renderer e84c8 (default) or direct glyph renderer3650.
// Formatter state at RAM104cd6 retains the selected native renderer address.
// Renderer3650 ignores font data and glyph lookahead for all style values.
// resources supplies fixed-ROM windows. Arguments and target data may be in
// RAM; optional argument_bytes maps a read-only pointer table at arguments_address
// (for callers whose original table lies on the CPU stack outside work RAM).
// Success replaces writes and RAM. Errors preserve both. Unsupported fonts,
// invalid memory accesses and original trap paths return errors.
bool format_fixed_text(std::vector<std::uint8_t>& ram,
                       const std::vector<FixedDataResource>& resources,
                       const FixedDataResource& font,
                       std::uint32_t format_address,
                       std::uint32_t arguments_address,
                       const std::vector<std::uint8_t>& argument_bytes,
                       std::uint16_t cursor, std::uint16_t style,
                       std::vector<VideoPortWrite>& writes, std::string& error,
                       std::uint32_t renderer = 0xe84c8U);
}
#endif
