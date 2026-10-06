#include "ms5/palette_upload.h"

namespace ms5 {

bool upload_dirty_palette_blocks(std::uint8_t* staging,
                                 std::size_t staging_size,
                                 std::uint8_t* palette,
                                 std::size_t palette_size,
                                 std::string& error) {
    if (staging == NULL || palette == NULL) {
        error = "staging and palette buffers must be nonnull";
        return false;
    }
    if (staging_size < 8192 || palette_size < 8192) {
        error = "staging and palette buffers must each contain at least 8192 bytes";
        return false;
    }
    for (std::size_t block = 0; block < 256; ++block) {
        const std::size_t offset = block * 32;
        const bool dirty = (staging[offset] & 0x80U) != 0;
        staging[offset] = static_cast<std::uint8_t>(staging[offset] & 0x7fU);
        if (dirty) {
            for (std::size_t byte = 0; byte < 32; ++byte) {
                palette[offset + byte] = staging[offset + byte];
            }
        }
    }
    error.clear();
    return true;
}

} // namespace ms5
