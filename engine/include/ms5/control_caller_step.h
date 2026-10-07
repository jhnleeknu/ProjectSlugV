#ifndef MS5_CONTROL_CALLER_STEP_H
#define MS5_CONTROL_CALLER_STEP_H
#include "ms5/control.h"
#include "ms5/control_caller.h"
namespace ms5 {
// Originalf54: call9136 at entry_stack-4, then consume its result atf5a.
// Supported native control/menu paths preserve the caller's A6 object address.
// Optional full D1/D3 and A1/global-renderer contract follow step_control.
// Boundary next_pc:0 normal return,ec4 loop,fee beforeTRAP15,c00444 BIOS.
// No code past those boundaries executes. Success commits even trap/BIOS
// boundaries; any unsupported-input error preserves all outputs and RAM.
bool step_control_caller(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& menu,const FixedDataResource& pause,
                         const std::vector<PaletteRecord>& records,
                         std::uint32_t object_address,std::uint16_t initial_style,
                         std::uint16_t initial_line,std::uint32_t entry_stack,
                         std::uint32_t& next_pc,std::vector<VideoPortWrite>& writes,
                         std::string& error,const FixedDataResource* font = NULL,
                         const StageGroupMenuContext* stage_context = NULL,
                         std::uint32_t* d1 = NULL,std::uint32_t* d3 = NULL);
}
#endif
