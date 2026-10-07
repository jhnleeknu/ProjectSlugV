#ifndef MS5_SCENE_SETUP_H
#define MS5_SCENE_SETUP_H
#include "ms5/scene_command.h"
namespace ms5 {
// Native43ffc setup; A0 selects a borrowed fixed-ROM descriptor or null.
// Exactly64KiB RAM. Errors preserve RAM, full state and ordered ports.
// Does not execute a caller; opcode08 restores its saved script A1 afterward.
bool setup_scene_resources(std::vector<std::uint8_t>& ram,
    const FixedDataResource* descriptor, SceneCommandState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
