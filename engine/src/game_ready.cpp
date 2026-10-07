#include "ms5/game_ready.h"
#include "ms5/object_restart.h"
#include "ms5/object_removal.h"
#include "ms5/object_allocation.h"
#include "ms5/game_screen_reset.h"
#include <new>
namespace ms5 {
namespace {
bool address(std::uint32_t at) {
    return (at & 1U) == 0 && at >= 0x100000 && at <= 0x110000 - 0xc4;
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) | (static_cast<std::uint32_t>(ram[at + 1]) << 16) |
        (static_cast<std::uint32_t>(ram[at + 2]) << 8) | ram[at + 3];
}
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 24); ram[at + 1] = static_cast<std::uint8_t>(value >> 16);
    ram[at + 2] = static_cast<std::uint8_t>(value >> 8); ram[at + 3] = static_cast<std::uint8_t>(value);
}
}
bool step_game_ready(std::vector<std::uint8_t>& ram, GameReadyState& state,
                     std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || !address(state.a6) ||
        (state.next_pc != 0xc654 && state.next_pc != 0xc66a && state.next_pc != 0xc686 && state.next_pc != 0xc6c0)) {
        error = "game ready requires 64KiB RAM, complete aligned A6 and supported PC"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; GameReadyState next = state; std::vector<VideoPortWrite> output;
        if (next.next_pc == 0xc654) {
            std::vector<VideoPortWrite> restart_ports;
            if (!restart_static_object(candidate,0x100b30,0x477e4,static_cast<std::uint8_t>(next.d0),restart_ports,error,&next.d1,&next.d3)) return false;
            output.insert(output.end(),restart_ports.begin(),restart_ports.end()); next.d0 = 0;
            put(candidate,next.a6 - 0x100000,0xc66a); next.next_pc = 0xc66a;
        }
        if (next.next_pc == 0xc66a) {
            if (get(candidate,0xb30) != 0x270e && candidate[0x4cd4] == 1) next.next_pc = 0xc724;
            else next.next_pc = 0xc686;
        }
        if (next.next_pc == 0xc686) {
            RemovalState removal; removal.d0 = next.d0; removal.d1 = next.d1; removal.d3 = next.d3; removal.a6 = next.a6;
            std::vector<VideoPortWrite> removal_ports;
            if (!remove_objects(candidate,0xc4cc,0,removal,removal_ports,error)) return false;
            next.d0 = removal.d0; next.d1 = removal.d1; next.d3 = removal.d3; next.a6 = removal.a6;
            output.insert(output.end(),removal_ports.begin(),removal_ports.end());
            std::vector<VideoPortWrite> screen_ports;
            if (!reset_game_screen(candidate,0xcaf0,next.d0,next.d1,next.d3,screen_ports,error)) return false;
            output.insert(output.end(),screen_ports.begin(),screen_ports.end()); candidate[0x965] = 255;
            AllocationState allocation; allocation.d0 = next.d0 & 0xffff0000U; allocation.a0 = 0xe66aa; allocation.a1 = 0; allocation.a6 = next.a6;
            if (!allocate_object(candidate,allocation,error)) return false;
            next.d0 = allocation.d0;
            if (!address(next.a6)) { error = "game ready final A6 requires aligned c4-byte object"; return false; }
            const std::size_t object = next.a6 - 0x100000;
            candidate[object + 0x62] = 0; put(candidate,object,0xc6c0); next.next_pc = 0xc6c0;
        }
        if (next.next_pc == 0xc6c0) next.next_pc = candidate[next.a6 - 0x100000 + 0x62] == 0 ? 0xc73e : 0xc00444;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate game ready transaction"; return false; }
}
}
