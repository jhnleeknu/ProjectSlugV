#include "ms5/game_startup.h"
#include "ms5/palette_fill.h"
#include "ms5/random_state.h"
#include <new>
namespace {
void word(std::vector<std::uint8_t>& ram,std::size_t at,std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void port(std::vector<ms5::VideoPortWrite>& ports,std::uint32_t address,std::uint32_t value) {
    ms5::VideoPortWrite write;
    write.size = 2; write.address = address; write.value = value; ports.push_back(write);
}
}
namespace ms5 {
bool step_game_startup(std::vector<std::uint8_t>& ram,
                       const std::vector<PaletteRecord>& fill_catalog,
                       const FixedDataResource& bindings,GameStartupState& state,
                       std::vector<VideoPortWrite>& ports,std::string& error) {
    if (ram.size() != 65536U || state.object_offset > 65536U - 0x84U ||
        (state.object_offset & 1U) != 0 || (state.next_pc != 0xc52aU && state.next_pc != 0xc560U)) {
        error = "game startup requires 64KiB RAM, complete even object offset and c52a/c560 PC"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        GameStartupState next = state;
        std::vector<VideoPortWrite> output;
        if (state.next_pc == 0xc52aU) {
            candidate[0x7def] = 255;
            for (std::size_t offset = 0x76; offset <= 0x7e; offset += 2) word(candidate,state.object_offset + offset,0);
            candidate[state.object_offset + 0x80] = 0;
            candidate[state.object_offset + 0x81] = 0;
            candidate[state.object_offset + 0x83] = 0;
            next.d0 &= 0xffff0000U;
            port(output,0x2ffff2U,0x1000U); port(output,0x2ffff0U,0);
            if (!setup_palette_fill(candidate,fill_catalog,0,error)) return false;
            next.d0 <<= 5;
            port(output,0x2ffff2U,0x1000U); port(output,0x2ffff0U,0);
            word(candidate,state.object_offset,0); word(candidate,state.object_offset + 2,0xc560U);
        }
        const std::uint16_t remaining = static_cast<std::uint16_t>(
            (static_cast<unsigned int>(candidate[0x7dea]) << 8) | candidate[0x7deb]);
        next.d0 = (next.d0 & 0xffff0000U) | remaining;
        next.next_pc = 0xc560U;
        if (remaining == 0) {
            std::vector<VideoPortWrite> palette_ports;
            if (!initialize_main_palettes(candidate,bindings,next.d0,next.d1,next.d3,palette_ports,error)) return false;
            output.insert(output.end(),palette_ports.begin(),palette_ports.end());
            next.d0 = 0;
            if (!seed_random(candidate,next.d0,next.d1,error)) return false;
            candidate[0xf004] = 3;
            next.next_pc = 0xc584U;
        }
        ram.swap(candidate); state = next; ports.swap(output);
    } catch (const std::bad_alloc&) {
        error = "cannot allocate game startup state"; return false;
    }
    error.clear(); return true;
}
}
