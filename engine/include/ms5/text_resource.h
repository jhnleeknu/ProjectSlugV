#ifndef MS5_TEXT_RESOURCE_H
#define MS5_TEXT_RESOURCE_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

struct TextPaletteBinding {
    std::uint32_t slot;
    std::uint32_t source_id;
};

struct TextResource {
    std::uint32_t id;
    std::vector<TextPaletteBinding> bindings;
    std::vector<std::uint8_t> script;

    TextResource() : id(0) {}
};

// MS5X v1 retains raw original fixed text bytes and explicit palette bindings.
// ID is a source ROM file offset. Script semantics are checked by the decoder,
// which permits zero operands. Failure preserves resource; success clears error.
bool load_text_resource(const std::string& path, TextResource& resource,
                        std::string& error);

} // namespace ms5

#endif
