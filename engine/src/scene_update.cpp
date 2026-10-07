#include "ms5/scene_update.h"
#include "ms5/scene_coordinates.h"
#include "ms5/scene_path_execution.h"
#include <new>
namespace ms5 {
bool update_scene(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536) { error = "scene update requires64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state;
        std::vector<VideoPortWrite> output, part; SceneNodeState node;
        std::uint32_t* registers[] = {&node.d0,&node.d1,&node.d2,&node.d3,&node.d4,&node.d5,&node.d6,&node.d7};
        for (unsigned int i = 0; i < 8; ++i) *registers[i] = next.d[i];
        node.a0 = next.a[0]; node.a1 = next.a[1]; node.a2 = next.a[2]; node.a4 = next.a[4];
        if (!update_scene_coordinates(candidate,node,error)) return false;
        for (unsigned int i = 0; i < 8; ++i) next.d[i] = *registers[i];
        next.a[0] = node.a0; next.a[1] = node.a1; next.a[2] = node.a2; next.a[4] = node.a4;
        if (!update_scene_debug_registers(candidate,tables,next,part,error)) return false;
        output.insert(output.end(),part.begin(),part.end());
        const std::uint32_t nodes[] = {0x109156,0x10b1d6,0x10d256,0x10d2d6};
        const std::uint32_t metadata[] = {0x10d356,0x10d364,0x10d372,0x10d380};
        for (unsigned int i = 0; i < 4; ++i) {
            next.a[0] = nodes[i]; next.a[1] = metadata[i];
            if (!execute_scene_path(candidate,windows,next,part,error)) return false;
            output.insert(output.end(),part.begin(),part.end());
        }
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene update transaction"; return false; }
}
}
