#ifndef MS5_STAGE_GROUP_MENU_H
#define MS5_STAGE_GROUP_MENU_H
#include "ms5/fixed_data_resource.h"
#include "ms5/stage_catalog.h"
#include "ms5/video_port.h"
namespace ms5 {
struct StageGroupMenuContext {
    const StageCatalog* catalog;
    // CPU0 prefix actually consumed when4827e returns a zero name pointer.
    const FixedDataResource* null_name;
    // Original A7 at callback entry; used to preserve formatter pointer state.
    // This API models an external diagnostic stack, outside the64KiB work RAM.
    std::uint32_t callback_stack;
    StageGroupMenuContext() : catalog(NULL), null_name(NULL), callback_stack(0) {}
};
// Callback9802 for descriptor978a: choose groups9..18, close, or draw FOR/name.
// Drawing requires font and context; other events do not require resources.
// Success updates RAM/A2 and replaces writes; failure preserves all outputs.
// Optional full D1/D3 reflect the callback with A2=current-slot context.
bool dispatch_stage_group_menu(std::vector<std::uint8_t>& ram,
                               const FixedDataResource& menu,
                               const FixedDataResource* font,
                               const StageGroupMenuContext* context,
                               std::uint16_t event, std::uint32_t& a2,
                               std::vector<VideoPortWrite>& writes,
                               std::string& error,
                               std::uint32_t* d1 = NULL, std::uint32_t* d3 = NULL);
}
#endif
