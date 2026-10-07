#include "ms5/game_restart.h"
#include "ms5/object_removal.h"
#include "ms5/game_screen_reset.h"
#include "ms5/random_state.h"
#include "ms5/stage_state.h"
#include "ms5/input_sampler.h"
#include <new>
namespace ms5 {
namespace {
bool idle(const SoundBytePending& byte) {
    return !byte.waiting && byte.command == 0 && byte.tail == 0 && byte.next == 0;
}
bool fresh(const GamePreludeState& inner) {
    return inner.phase == 0 && inner.next_pc == 0x47570 && inner.word.kind == 0 &&
        inner.word.phase == 0 && inner.word.low == 0 && inner.word.cursor == 0 &&
        idle(inner.word.byte) && idle(inner.byte);
}
bool address(std::uint32_t at) {
    return (at & 1U) == 0 && at >= 0x100000 && at <= 0x110000 - 0xc4;
}
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1]);
}
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
}
bool restart_game(std::vector<std::uint8_t>& ram, const FixedDataResource& records,
                  const FixedDataResource& streams, std::uint8_t external,
                  GameRestartState& state, std::uint8_t& reads,
                  std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || !address(state.a6) || state.phase > 1 || state.initialization.returned ||
        (state.phase == 0 && !fresh(state.initialization.prelude)) ||
        (state.phase == 1 && (state.initialization.prelude.phase < 1 || state.initialization.prelude.phase > 3 ||
                             state.initialization.prelude.next_pc != 0x3aea))) {
        error = "invalid game restart RAM, object or continuation"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; GameRestartState next = state;
        GamePreludeState& inner = next.initialization.prelude;
        std::vector<VideoPortWrite> output; std::uint8_t next_reads = 0;
        if (next.phase == 0) {
            put_word(candidate,0xf02a,1); inner.d0 = 0;
            if (!seed_random(candidate,inner.d0,inner.d1,error)) return false;
            RemovalState removal; removal.d0 = inner.d0; removal.d1 = inner.d1; removal.d3 = inner.d3; removal.a6 = next.a6;
            std::vector<VideoPortWrite> removal_ports;
            if (!remove_objects(candidate,0xc4cc,0,removal,removal_ports,error)) return false;
            inner.d0 = removal.d0; inner.d1 = removal.d1; inner.d3 = removal.d3; next.a6 = removal.a6;
            output.insert(output.end(),removal_ports.begin(),removal_ports.end());
            std::vector<VideoPortWrite> screen_ports;
            if (!reset_game_screen(candidate,0xcaf0,inner.d0,inner.d1,inner.d3,screen_ports,error)) return false;
            output.insert(output.end(),screen_ports.begin(),screen_ports.end());
        }
        if (!initialize_game(candidate,records,external,next.initialization,next_reads,error)) return false;
        next.phase = 1;
        if (next.initialization.returned) {
            const std::uint16_t source = static_cast<std::uint16_t>(word(candidate,0xf02a) & 1U);
            put_word(candidate,0xf02a,source);
            inner.d0 = (inner.d0 & 0xffff0000U) | (source + 6U);
            if (!set_stage_state(candidate,SelectStage,static_cast<std::uint16_t>(inner.d0),error)) return false;
            inner.d0 = (inner.d0 & 0xffff0000U) | word(candidate,0xf02a);
            if (!initialize_input(candidate,streams,static_cast<std::uint16_t>(inner.d0),error)) return false;
            inner.d0 &= 0xffff0000U;
            if (!address(next.a6)) { error = "game restart final object requires aligned c4-byte RAM span"; return false; }
            const std::size_t object = next.a6 - 0x100000;
            put_word(candidate,object,0); put_word(candidate,object + 2,0xc654);
            next.phase = 2;
        }
        ram.swap(candidate); state = next; reads = next_reads; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate game restart transaction"; return false; }
}
}
