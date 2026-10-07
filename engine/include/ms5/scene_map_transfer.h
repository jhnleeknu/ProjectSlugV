#ifndef MS5_SCENE_MAP_TRANSFER_H
#define MS5_SCENE_MAP_TRANSFER_H
#include "ms5/fixed_data_resource.h"
#include "ms5/video_port.h"
namespace ms5 {
struct SceneMapTransferState {
    std::uint32_t d[8], a[5];
    SceneMapTransferState() { for (unsigned int i = 0; i < 8; ++i) d[i] = 0; for (unsigned int i = 0; i < 5; ++i) a[i] = 0; }
};
// Native183c6 through185f8 only. Borrowed fixed/bank2/bank3 windows are read
// independently; ambiguous/partial-window reads are errors. Rejected clipping
// is successful copied=false. Exact64KiB RAM, registers, copied and ports are
// transactional. Zero WORD loop counts execute65536 iterations. A temporary
// budget limits each primary/secondary loop to1048576 cells; exceeding it
// is an API error rather than a complete-native-support claim.
bool transfer_scene_map(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    bool& copied, std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
