#ifndef MS5_GAME_STARTUP_H
#define MS5_GAME_STARTUP_H
#include "ms5/main_startup.h"
#include "ms5/palette_resource.h"
namespace ms5 {
struct GameStartupState {
    std::uint32_t next_pc,d0,d1,d3;
    std::size_t object_offset;
    GameStartupState() : next_pc(0xc52a),d0(0),d1(0),d3(0),object_offset(0) {}
};
// Native c52a starts fill/reset; c560 polls the live palette-fill counter.
// A wait returns c560. Completion returns c584 before external47570.
// Object is an even RAM offset with0x84 bytes. Resources are validated only
// when used. Full registers and ordered ports are transactional with RAM.
bool step_game_startup(std::vector<std::uint8_t>& ram,
                       const std::vector<PaletteRecord>& fill_catalog,
                       const FixedDataResource& bindings,GameStartupState& state,
                       std::vector<VideoPortWrite>& ports,std::string& error);
}
#endif
