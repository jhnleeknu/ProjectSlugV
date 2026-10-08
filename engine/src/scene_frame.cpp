#include "ms5/scene_frame.h"
#include "ms5/scene_frame_control.h"
#include "ms5/scene_camera.h"
#include "ms5/scene_script_run.h"
#include "ms5/scene_placement_execution.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size) {
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | ram[at+i]; return value;
}
void put(std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size, std::uint32_t value) {
    for (unsigned int i = 0; i < size; ++i) ram[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
bool fixed(const FixedDataResource& w) {
    return !(w.source_cpu_address & 1U) && w.source_cpu_address < 0x100000 &&
        w.source_rom_offset == w.source_cpu_address && !w.data.empty() && w.data.size() <= 0x100000-w.source_cpu_address;
}
const FixedDataResource* window(const std::vector<FixedDataResource>& windows, std::uint32_t address, unsigned int size) {
    const FixedDataResource* selected = NULL; unsigned int matches = 0;
    for (std::size_t i = 0; i < windows.size(); ++i) {
        const FixedDataResource& w = windows[i]; if (!fixed(w)) continue;
        const std::uint64_t end = static_cast<std::uint64_t>(w.source_cpu_address)+w.data.size();
        if (address < end && static_cast<std::uint64_t>(address)+size > w.source_cpu_address) {
            ++matches;
            if (address >= w.source_cpu_address && static_cast<std::uint64_t>(address)+size <= end) selected = &w;
        }
    }
    return matches == 1 ? selected : NULL;
}
void port(std::vector<VideoPortWrite>& output, std::uint32_t address, std::uint32_t value) {
    VideoPortWrite w; w.size = 2; w.address = address; w.value = value; output.push_back(w);
}
SceneCommandState command_state(const SceneMapTransferState& s) {
    SceneCommandState c;
    c.d0 = s.d[0]; c.d1 = s.d[1]; c.d2 = s.d[2]; c.d3 = s.d[3];
    c.d4 = s.d[4]; c.d5 = s.d[5]; c.d6 = s.d[6]; c.d7 = s.d[7];
    c.a0 = s.a[0]; c.a1 = s.a[1]; c.a2 = s.a[2]; c.a4 = s.a[4];
    return c;
}
void apply(SceneMapTransferState& s, const SceneCommandState& c) {
    s.d[0] = c.d0; s.d[1] = c.d1; s.d[2] = c.d2; s.d[3] = c.d3;
    s.d[4] = c.d4; s.d[5] = c.d5; s.d[6] = c.d6; s.d[7] = c.d7;
    s.a[0] = c.a0; s.a[1] = c.a1; s.a[2] = c.a2; s.a[4] = c.a4;
}
bool script(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::vector<VideoPortWrite>& output, std::string& error) {
    const std::uint32_t cursor = get(ram,0xd412,4); SceneScript decoded;
    if (cursor != 0 && get(ram,0xd418,2) >= get(ram,0xd416,2)) {
        const FixedDataResource* source = window(windows,cursor,2);
        if (source == NULL || !decode_scene_script(*source,decoded,error)) {
            if (source == NULL) error = "scene frame requires unique fixed script cursor window";
            return false;
        }
    }
    FixedDataResource dummy; const FixedDataResource* pointers = window(windows,0x1a08e,16);
    SceneCommandState c = command_state(s); SceneScriptRunResult result; std::vector<VideoPortWrite> writes;
    if (!run_scene_script(ram,decoded,pointers == NULL ? dummy : *pointers,c,result,writes,error,&windows)) return false;
    apply(s,c); output.insert(output.end(),writes.begin(),writes.end()); return true;
}
bool motion_path(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const FixedDataResource*& path, std::string& error) {
    const std::uint32_t cursor = get(ram,0xd3b4,4); path = NULL;
    if (cursor != 0) {
        path = window(windows,cursor,2);
        if (path == NULL) { error = "scene frame requires unique fixed motion cursor window (RAM motion unsupported)"; return false; }
    }
    return true;
}
bool control(std::vector<std::uint8_t>& ram, std::uint32_t entry, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, bool& carry, std::string& error) {
    SceneCommandState c = command_state(s);
    if (!step_scene_frame_control(ram,entry,windows,c,carry,error)) return false;
    apply(s,c); return true;
}
bool frame(std::vector<std::uint8_t>& ram, const FixedDataResource& tables, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::uint32_t parent, std::vector<VideoPortWrite>& output, std::string& error) {
    put(ram,0x10,2,1); port(output,0x2ffff2,0x2000); port(output,0x2ffff0,0);
    bool carry = false;
    if (!control(ram,0x1a2b4,windows,s,carry,error)) return false;
    if (carry && !script(ram,windows,s,output,error)) return false;
    if (!control(ram,0x1a526,windows,s,carry,error)) return false;
    const FixedDataResource* path = NULL; SceneCommandState c = command_state(s);
    if (!motion_path(ram,windows,path,error) || !step_scene_camera(ram,0x19b96,path,c,error)) return false;
    apply(s,c); c = command_state(s);
    if (!motion_path(ram,windows,path,error) || !step_scene_motion_bounds(ram,0x19d08,path,c,error)) return false;
    apply(s,c); s.d[0] = get(ram,0xd3bc,4); s.d[1] = get(ram,0xd3c0,4); c = command_state(s);
    if (!motion_path(ram,windows,path,error) || !resolve_scene_motion_time(ram,path,c,error)) return false;
    apply(s,c); s.d[7] = (s.d[7] << 16) | (s.d[7] >> 16);
    if (low(s.d[7]) >= get(ram,0xd418,2)) put(ram,0xd418,2,s.d[7]);
    if (!control(ram,0x1a3d6,windows,s,carry,error)) return false;
    std::vector<VideoPortWrite> writes;
    if (!update_scene(ram,tables,windows,s,writes,error)) return false;
    output.insert(output.end(),writes.begin(),writes.end()); c = command_state(s);
    if (!execute_scene_placement(ram,0x1a442,windows,c,parent,error)) return false;
    apply(s,c); put(ram,0x10,2,0); port(output,0x2ffff2,0x1000); port(output,0x2ffff0,0); return true;
}
}
bool step_scene_frame(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536) { error = "scene frame requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state; std::vector<VideoPortWrite> output;
        if (!frame(candidate,tables,windows,next,parent_a6,output,error)) return false;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene frame transaction"; return false; }
}
}
