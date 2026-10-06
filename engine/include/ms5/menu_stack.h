#ifndef MS5_MENU_STACK_H
#define MS5_MENU_STACK_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
namespace ms5 {
struct StageGroupMenuContext;
// CPU a0a0: push one menu, redraw the previous head, then configure the new
// slot. Uses a single MS5D window containing both menus and their text.
// Preserves current-menu pointer, renderer, input source and slot+5.
// Full/invalid stacks and unsupported parent rendering fail transactionally.
// Stage context uses the parent's actual event5 callback entry A7, like
// draw_menu_text. For original a0a0 entry stack S, supply S-40; this function
// does not apply another stack adjustment. Hidden parents need no context.
bool push_menu(std::vector<std::uint8_t>& ram,
               const FixedDataResource& resource, std::uint32_t descriptor_address,
               std::uint16_t x, std::uint16_t y, std::uint16_t initial_line,
               std::vector<VideoPortWrite>& writes, std::string& error,
               const FixedDataResource* font = NULL,
               const StageGroupMenuContext* stage_context = NULL);
}
#endif
