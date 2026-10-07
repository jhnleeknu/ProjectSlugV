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

bool transfer_palette_banks(std::vector<std::uint8_t>& ram,
                            std::vector<std::uint8_t>& palette0,
                            std::vector<std::uint8_t>& palette1,
                            std::uint8_t& display_bank,
                            std::string& error) {
    if (&ram == &palette0 || &ram == &palette1 || &palette0 == &palette1) {
        error = "RAM and palette banks must be distinct vectors";
        return false;
    }
    if (ram.size() != 65536 || palette0.size() != 8192 || palette1.size() != 8192) {
        error = "RAM must contain exactly 65536 bytes and each palette bank exactly 8192 bytes";
        return false;
    }
    const std::uint16_t counter = static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(ram[0x7dea]) << 8) | ram[0x7deb]);
    if (counter == 0) {
        return transfer_palette_frame(ram, palette0, display_bank, error);
    }
    if (counter != 0x2000) {
        error = "unsupported out-of-window special-fill counter at RAM 0x7dea";
        return false;
    }
    // Confirmed CPU 0x00873a path; see docs/analysis/palette-fill.md.
    for (std::size_t offset = 0; offset < palette1.size(); ++offset) {
        palette1[offset] = ram[0x7da2 + offset % 32];
    }
    palette1[0] = 0;
    palette1[1] = 0;
    ram[0x7dea] = 0;
    ram[0x7deb] = 0;
    display_bank = ram[0x7dec] != 0 ? 1 : 0;
    error.clear();
    return true;
}

namespace {
std::uint32_t palette_long(const std::vector<std::uint8_t>& bytes,std::size_t at) {
    return (static_cast<std::uint32_t>(bytes[at])<<24)|
           (static_cast<std::uint32_t>(bytes[at+1])<<16)|
           (static_cast<std::uint32_t>(bytes[at+2])<<8)|bytes[at+3];
}
void palette_write(std::vector<VideoPortWrite>& writes,std::uint8_t size,
                   std::uint32_t address,std::uint32_t value) {
    VideoPortWrite write;write.size=size;write.address=address;write.value=value;writes.push_back(write);
}
}
bool transfer_palette_banks_traced(std::vector<std::uint8_t>& ram,
                                  std::vector<std::uint8_t>& palette0,
                                  std::vector<std::uint8_t>& palette1,
                                  std::uint8_t& display_bank,std::uint32_t& d0,
                                  std::vector<VideoPortWrite>& writes,std::string& error) {
    if(&ram==&palette0 || &ram==&palette1 || &palette0==&palette1) {
        error="RAM and palette banks must be distinct vectors";return false;
    }
    std::vector<std::uint8_t> next_ram=ram,next0=palette0,next1=palette1;
    std::uint8_t bank=display_bank;std::uint32_t next_d0=d0;
    if(!transfer_palette_banks(next_ram,next0,next1,bank,error)) return false;
    std::vector<VideoPortWrite> ports;
    const bool special=ram[0x7dea]!=0 || ram[0x7deb]!=0;
    if(special) {
        palette_write(ports,1,0x3a001f,d0&255U);
        next_d0=palette_long(ram,0x7da2);
        // MOVEM predecrement stores D7 first at the highest long address.
        for(unsigned int block=0;block<256;++block) {
            for(unsigned int reg=0;reg<8;++reg) {
                const unsigned int offset=8192U-32U*block-4U*(reg+1U);
                palette_write(ports,4,0x400000U+offset,palette_long(ram,0x7da2+4U*(7U-reg)));
            }
        }
        palette_write(ports,2,0x400000,0);
    } else {
        if((ram[0x7ded]&128U)!=0) {
            palette_write(ports,1,0x3a000f,d0&255U);
            for(unsigned int block=0;block<256;++block) {
                const unsigned int offset=32U*block;
                if((ram[0x5da2+offset]&128U)==0) continue;
                next_d0=palette_long(next0,offset);
                for(unsigned int reg=0;reg<8;++reg)
                    palette_write(ports,4,0x400000U+offset+4U*reg,palette_long(next0,offset+4U*reg));
            }
        }
        palette_write(ports,1,0x300001,next_d0&255U);
    }
    palette_write(ports,1,bank!=0 ? 0x3a001f : 0x3a000f,next_d0&255U);
    ram.swap(next_ram);palette0.swap(next0);palette1.swap(next1);
    display_bank=bank;d0=next_d0;writes.swap(ports);error.clear();return true;
}

} // namespace ms5
