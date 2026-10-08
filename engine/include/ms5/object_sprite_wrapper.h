#ifndef MS5_OBJECT_SPRITE_WRAPPER_H
#define MS5_OBJECT_SPRITE_WRAPPER_H
#include "ms5/sprite_submit_execution.h"
namespace ms5 {
struct ObjectSpriteWrapperState {
    SpriteSubmitExecutionState sprite;
    std::uint32_t a5, a6;
    ObjectSpriteWrapperState() : a5(0x108000), a6(0) {}
};
// Full native16ea4 tail-call cd58 with default callback cd50. Fresh calls
// read the reached aligned object fields and set A5=108000. Captured waits
// require that A5 and resume only cd58's live consumer comparison, without
// reading the object again. A6 is preserved. RAM, fifteen registers, waiting
// and status are transactional on error; exact64KiB RAM is required.
bool execute_object_sprite_wrapper(std::vector<std::uint8_t>& ram,
    ObjectSpriteWrapperState& state, SpriteSubmitStatus& status,
    std::string& error);
}
#endif
