#ifndef MS5_STAGE_AREA_MENU_H
#define MS5_STAGE_AREA_MENU_H
#include "ms5/stage_group_menu.h"
namespace ms5 {
// Callback9602. Context stack denotes entry A7; nested event6 row callbacks
// receive entry-20. Selection and graphics are committed together on success.
// Optional full D1/D3 are transactional; D3.low16 must match line.
bool dispatch_stage_area_menu(std::vector<std::uint8_t>& ram,
                              const FixedDataResource& menu,
                              const FixedDataResource* font,
                              const StageGroupMenuContext* context,
                              std::uint16_t event,std::uint16_t& line,
                              std::uint32_t& a2,std::vector<VideoPortWrite>& writes,
                              std::string& error, std::uint32_t* d1 = NULL,
                              std::uint32_t* d3 = NULL);
}
#endif
