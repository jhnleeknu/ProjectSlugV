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
// Optional final_style receives D1.word after terminal controls, even when
// those controls are not stored in formatter RAM. Errors preserve it too.
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
                       std::uint32_t renderer = 0xe84c8U,
                       std::uint16_t* final_style = NULL);
// ec4 through ef2 (before frame gate): conditional direct diagnostic text.
// D1 upper word is preserved; lower word follows terminal formatter parsing.
// Disabled f000 bit0 bypasses object/resource; zero object+84 bypasses resource.
// Failure preserves RAM, D1 and writes. Other CPU registers/flags not returned.
bool step_main_debug(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& debug,std::uint32_t object_address,
                     std::uint32_t& d1,std::vector<VideoPortWrite>& writes,
                     std::string& error);
}
#endif
