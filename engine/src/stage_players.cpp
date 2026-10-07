#include "ms5/stage_players.h"
#include "ms5/game_objects.h"
#include "ms5/object_restart.h"
#include "ms5/object_removal.h"
#include "ms5/random_state.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram,at)) << 16) | word(ram,at + 2);
}
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
bool table_valid(const FixedDataResource& table, std::string& error) {
    if (table.source_cpu_address != 0x476bc || table.source_rom_offset != 0x476bc || table.data.size() != 1040) {
        error = "stage players require exact476bc/1040-byte window"; return false;
    }
    for (unsigned int i = 0; i < 3; ++i) {
        if (longword(table.data,0x14 + i*4) != 0x476bcU + i*8U) {
            error = "stage player fixed pointer table mismatch"; return false;
        }
    }
    return true;
}
}
bool configure_stage_player(std::vector<std::uint8_t>& ram, StagePlayersState& state,
                            std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536) { error = "stage player requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; StagePlayersState next = state;
        std::vector<VideoPortWrite> output;
        const std::size_t object = (next.d0 & 65535U) == 0 ? 0xcb8 : 0xda8;
        const std::uint16_t saved_d1 = static_cast<std::uint16_t>(next.d1);
        if ((saved_d1 & 0x8000U) != 0) {
            if (word(candidate,object + 0x10) != 0) { error = "stage player removal excludes nonzero-depth native TRAP"; return false; }
            RemovalState removal; removal.d0 = next.d0; removal.d1 = next.d1; removal.d3 = next.d3;
            removal.a6 = static_cast<std::uint32_t>(0x100000 + object);
            if (!remove_objects(candidate,0x299c,0,removal,output,error)) return false;
            next.d0 = removal.d0; next.d1 = removal.d1; next.d3 = removal.d3;
        } else {
            if (longword(candidate,object) == 0x270e) {
                const std::uint16_t saved_d0 = static_cast<std::uint16_t>(next.d0);
                if (!restart_static_object(candidate,static_cast<std::uint32_t>(0x100000 + object),0x1d1f4,
                                           static_cast<std::uint8_t>(next.d0),output,error,&next.d1,&next.d3)) return false;
                next.d0 = 0;
                put_word(candidate,object + 0x78,saved_d0);
                if (!initialize_game_object(candidate,static_cast<std::uint32_t>(0x100000 + object),next.d0,error)) return false;
            }
            next.d0 = (next.d0 & 0xffff0000U) | saved_d1;
            if ((next.d0 & 65535U) >= 4) {
                if (!next_random(candidate,next.d0,error)) return false;
                next.d0 = (next.d0 & 0xffff0000U) | (next.d0 & 3U);
            }
            put_word(candidate,object + 0x76,static_cast<std::uint16_t>(next.d0));
        }
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage player transaction"; return false; }
}
bool configure_stage_players(std::vector<std::uint8_t>& ram, const FixedDataResource& table,
                             StagePlayersState& state, std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || (state.a6 & 1U) || state.a6 < 0x100000 || state.a6 > 0x110000 - 0xc4) {
        error = "stage players require64KiB RAM and aligned c4-byte A6 span"; return false;
    }
    if (!table_valid(table,error)) return false;
    try {
        std::vector<std::uint8_t> candidate = ram; StagePlayersState next = state;
        std::vector<VideoPortWrite> output;
        const std::size_t object = next.a6 - 0x100000;
        const unsigned int stage = candidate[object + 0x7c];
        const unsigned int group = stage >= 6 && stage <= 8 ? stage - 6 : 0;
        const unsigned int area = candidate[object + 0x7d];
        const std::size_t at = longword(table.data,0x14 + group*4) - 0x476bc + area*4;
        next.d0 = area*4;
        const std::size_t gates[2] = {0x9a8,0xa6c};
        for (unsigned int i = 0; i < 2; ++i) {
            next.d1 = (next.d1 & 0xffff0000U) | word(table.data,at + i*2);
            if (longword(candidate,gates[i]) == 0x270e) {
                next.d0 = i; std::vector<VideoPortWrite> player_ports;
                if (!configure_stage_player(candidate,next,player_ports,error)) return false;
                output.insert(output.end(),player_ports.begin(),player_ports.end());
            }
        }
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage players transaction"; return false; }
}
bool begin_stage_players(std::vector<std::uint8_t>& ram, const FixedDataResource& table,
                         StagePlayersState& state, std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536) { error = "stage player caller requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; StagePlayersState next = state;
        std::vector<VideoPortWrite> output;
        candidate[0xd681] = 255;
        next.d0 = (next.d0 & 0xffffff00U) | (3U & candidate[0xd684]);
        if ((next.d0 & 255U) != 0 && !configure_stage_players(candidate,table,next,output,error)) return false;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage player caller transaction"; return false; }
}

}
