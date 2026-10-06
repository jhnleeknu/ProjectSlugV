#ifndef MS5_MENU_EVENT_H
#define MS5_MENU_EVENT_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
namespace ms5 {
struct StageGroupMenuContext;
struct MenuEventResult {
    std::uint32_t a2;
    std::uint32_t external_jump;
    MenuEventResult() : a2(0), external_jump(0) {}
};
// CPU 9b3e through the six control-menu callbacks and debug callback9aa8.
// Debug drawing requires font. Stage group callback9802 drawing additionally
// requires stage_context. Dispatches slot+8;
// event is the D0 word, initial_line is D3's text-line word. Returns A2
// because the caller's menu state machine uses it after callbacks.
// external_jump=c00444 requires a BIOS/host transition; that firmware is
// not executed here. Port writes include video and watchdog300001.
// Failure preserves RAM, result and writes. Pending slot+14 is not cleared
// here; that is the frame loop's responsibility.
bool dispatch_menu_event(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& resource,
                         std::uint16_t event, std::uint16_t initial_line,
                         MenuEventResult& result,
                         std::vector<VideoPortWrite>& writes, std::string& error,
                         const FixedDataResource* font = NULL,
                         const StageGroupMenuContext* stage_context = NULL);
}
#endif
