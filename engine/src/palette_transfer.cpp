#include "ms5/palette_transfer.h"
#include "ms5/palette_upload.h"

namespace ms5 {

bool transfer_palette_frame(std::vector<std::uint8_t>& ram,
                            std::vector<std::uint8_t>& palette0,
                            std::uint8_t& display_bank,
                            std::string& error) {
    if (ram.size() != 65536 || palette0.size() != 8192) {
        error = "RAM must contain exactly 65536 bytes and palette bank 0 exactly 8192 bytes";
        return false;
    }
    if (ram[0x7dea] != 0 || ram[0x7deb] != 0) {
        error = "nonzero special-fill word at RAM 0x7dea is unsupported";
        return false;
    }
    std::vector<std::uint8_t> candidate_ram(ram);
    std::vector<std::uint8_t> candidate_palette(palette0);
    const bool pending = (candidate_ram[0x7ded] & 0x80U) != 0;
    candidate_ram[0x7ded] = static_cast<std::uint8_t>(candidate_ram[0x7ded] & 0x7fU);
    if (pending) {
        candidate_ram[0x5da2] = static_cast<std::uint8_t>(candidate_ram[0x5da2] & 0x80U);
        candidate_ram[0x5da3] = 0;
        if (!upload_dirty_palette_blocks(&candidate_ram[0x5da2], 8192,
                                         &candidate_palette[0], 8192, error)) {
            return false;
        }
    }
    const std::uint8_t candidate_bank = candidate_ram[0x7dec] != 0 ? 1 : 0;
    ram.swap(candidate_ram);
    palette0.swap(candidate_palette);
    display_bank = candidate_bank;
    error.clear();
    return true;
}

} // namespace ms5
