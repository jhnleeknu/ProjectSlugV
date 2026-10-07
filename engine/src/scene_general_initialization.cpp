#include "ms5/scene_general_initialization.h"
#include "ms5/scene_script_run.h"
#include "ms5/scene_motion.h"
#include "ms5/scene_node.h"
#include "ms5/scene_placement_execution.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void word(std::uint32_t& value, std::uint32_t input) { value = (value & 0xffff0000U) | low(input); }
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
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int size, std::uint32_t& value, std::string& error) {
    if ((address & 1U) || address > 0x1000000U-size) { error = "unaligned or overflowing scene initialization read"; return false; }
    if (address >= 0x100000 && address+size <= 0x110000) { value = get(ram,address-0x100000,size); return true; }
    const FixedDataResource* w = window(windows,address,size);
    if (w == NULL) { error = "missing, ambiguous or partial fixed initialization read"; return false; }
    value = get(w->data,address-w->source_cpu_address,size); return true;
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
bool node(std::vector<std::uint8_t>& ram, std::uint32_t entry, SceneMapTransferState& s, std::string& error) {
    SceneNodeState n;
    n.d0 = s.d[0]; n.d1 = s.d[1]; n.d2 = s.d[2]; n.d3 = s.d[3];
    n.d4 = s.d[4]; n.d5 = s.d[5]; n.d6 = s.d[6]; n.d7 = s.d[7];
    n.a0 = s.a[0]; n.a1 = s.a[1]; n.a2 = s.a[2]; n.a4 = s.a[4];
    if (!step_scene_node(ram,entry,n,error)) return false;
    s.d[0] = n.d0; s.d[1] = n.d1; s.d[2] = n.d2; s.d[3] = n.d3;
    s.d[4] = n.d4; s.d[5] = n.d5; s.d[6] = n.d6; s.d[7] = n.d7;
    s.a[0] = n.a0; s.a[1] = n.a1; s.a[2] = n.a2; s.a[4] = n.a4;
    return true;
}
bool duration(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, SceneMapTransferState& s, std::string& error) {
    put(ram,0xd422,4,0); s.a[1] = get(ram,0xd3b4,4);
    if (s.a[1] == 0) word(s.d[7],0x7fff);
    else {
        std::uint32_t value = 0; unsigned int scanned = 0;
        for (;;) {
            if (!read(ram,windows,s.a[1]+2,2,value,error)) return false;
            if (value == 0xffff) break;
            if (++scanned > 1048576U) { error = "scene duration temporary record budget exceeded"; return false; }
            s.a[1] += 10;
        }
        if (!read(ram,windows,s.a[1],2,value,error)) return false;
        word(s.d[7],value); word(s.d[7],s.d[7]-1U);
    }
    put(ram,0xd41e,2,s.d[7]); put(ram,0xd420,2,s.d[7]); put(ram,0xd43e,2,0); return true;
}
bool script(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::vector<VideoPortWrite>& output, std::string& error) {
    const std::uint32_t cursor = get(ram,0xd412,4); SceneScript decoded;
    if (cursor != 0 && get(ram,0xd418,2) >= get(ram,0xd416,2)) {
        const FixedDataResource* source = window(windows,cursor,2);
        if (source == NULL || !decode_scene_script(*source,decoded,error)) {
            if (source == NULL) error = "scene initializer requires unique fixed script cursor window";
            return false;
        }
    }
    FixedDataResource dummy; const FixedDataResource* pointers = window(windows,0x1a08e,16);
    SceneCommandState c = command_state(s); SceneScriptRunResult result; std::vector<VideoPortWrite> writes;
    if (!run_scene_script(ram,decoded,pointers == NULL ? dummy : *pointers,c,result,writes,error,&windows)) return false;
    apply(s,c); output.insert(output.end(),writes.begin(),writes.end()); return true;
}
bool motion(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, SceneMapTransferState& s, std::string& error) {
    const std::uint32_t cursor = get(ram,0xd3b4,4); const FixedDataResource* path = NULL;
    if (cursor != 0) {
        path = window(windows,cursor,2);
        if (path == NULL) { error = "scene initializer requires unique fixed motion window (RAM motion unsupported)"; return false; }
    }
    SceneCommandState c = command_state(s);
    if (!evaluate_scene_motion(ram,path,c,error)) return false;
    apply(s,c); return true;
}
bool initialize(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& s, std::uint32_t parent,
    std::vector<VideoPortWrite>& output, std::string& error) {
    put(ram,0x10,2,1); port(output,0x2ffff2,0x2000); port(output,0x2ffff0,0);
    put(ram,0xd41c,2,s.d[0]); put(ram,0xd412,4,s.a[0]); put(ram,0xd416,2,0);
    const std::size_t zeros[] = {0xd418,0xd42a,0xd42c,0xd448,0xd44a,0xd44c,0xd432,0xd43c,0xd40c};
    for (unsigned int i = 0; i < 9; ++i) put(ram,zeros[i],2,0);
    put(ram,0xd426,2,0xa0); put(ram,0xd428,2,0x80); put(ram,0xd444,2,0x8000); put(ram,0xd446,2,0x8000);
    put(ram,0xd442,2,0x7fff); put(ram,0xd440,2,0x7fff); put(ram,0xd42e,2,0xffff); put(ram,0xd430,2,0xffff);
    put(ram,0xd434,4,0); put(ram,0xd438,4,0); ram[0xd44e] = 0;
    s.a[1] = 0; s.d[0] = 0; s.d[1] = 0;
    put(ram,0xd3b8,2,0); put(ram,0xd3ba,2,0); put(ram,0xd3bc,4,0); put(ram,0xd3c0,4,0); put(ram,0xd3b4,4,0);
    s.d[1] = 0x01000000; s.a[0] = 0x10d38e;
    if (!node(ram,0x43e22,s,error) || !duration(ram,windows,s,error)) return false;
    ram[0xd3cc] = 0;
    const std::size_t zero_longs[] = {0xd3de,0xd3e2,0xd3fc,0xd400};
    for (unsigned int i = 0; i < 4; ++i) put(ram,zero_longs[i],4,0);
    put(ram,0xd3ee,2,0); put(ram,0xd3f0,2,0); put(ram,0xd3d6,2,0xa0); put(ram,0xd3d8,2,0x80);
    put(ram,0xd3da,2,0); put(ram,0xd3dc,2,0); put(ram,0xd3e6,4,0x60000); put(ram,0xd3ea,4,0x60000);
    put(ram,0xd3ce,2,0x7fff); put(ram,0xd3d0,2,0x7fff); put(ram,0xd3d2,2,0x8000); put(ram,0xd3d4,2,0x8000);
    const std::size_t nodes[] = {0x9156,0xb1d6,0xd256,0xd2d6}, metadata[] = {0xd356,0xd364,0xd372,0xd380};
    for (unsigned int i = 0; i < 4; ++i) {
        s.a[0] = static_cast<std::uint32_t>(0x100000+nodes[i]); s.a[1] = static_cast<std::uint32_t>(0x100000+metadata[i]);
        put(ram,metadata[i],4,0); for (unsigned int j = 4; j <= 10; j += 2) put(ram,metadata[i]+j,2,0); ram[metadata[i]+12] = 0x10;
        if (!node(ram,0x16fac,s,error)) return false;
        s.a[1] = 0; s.d[0] = get(ram,0xd38e,4); s.d[1] = get(ram,0xd392,4);
        if (!node(ram,0x16fee,s,error)) return false;
    }
    put(ram,0xd404,2,0); put(ram,0xd406,2,0); put(ram,0xd408,4,0);
    s.a[0] = 0; put(ram,0xd40e,4,s.a[0]);
    s.a[0] = 0x109156; if (!node(ram,0x17292,s,error)) return false;
    s.a[0] = 0x10b1d6; if (!node(ram,0x17292,s,error)) return false;
    bool done = false;
    for (unsigned int iteration = 0; iteration < 1048576U; ++iteration) {
        if (!script(ram,windows,s,output,error)) return false;
        s.a[1] = get(ram,0xd3b4,4);
        if (s.a[1] == 0) s.d[7] = 0;
        else { std::uint32_t value = 0; if (!read(ram,windows,s.a[1]+10,2,value,error)) return false; word(s.d[7],value); }
        word(s.d[6],get(ram,0xd41c,2));
        if (low(s.d[7]) < low(s.d[6])) {
            s.a[1] = get(ram,0xd3b4,4); bool terminal = s.a[1] == 0;
            if (!terminal) { std::uint32_t value = 0; if (!read(ram,windows,s.a[1]+12,2,value,error)) return false; terminal = (value & 0x8000U) != 0; }
            if (terminal) put(ram,0xd41c,2,s.d[7]);
        } else word(s.d[7],s.d[6]);
        word(s.d[6],get(ram,0xd416,2));
        if (low(s.d[7]) >= low(s.d[6])) word(s.d[7],s.d[6]);
        put(ram,0xd418,2,s.d[7]); s.d[7] = static_cast<std::uint32_t>(low(s.d[7])) << 16;
        if (!motion(ram,windows,s,error)) return false;
        put(ram,0xd3bc,4,s.d[0]); put(ram,0xd3c0,4,s.d[1]);
        std::vector<VideoPortWrite> writes;
        if (!update_scene(ram,tables,windows,s,writes,error)) return false;
        output.insert(output.end(),writes.begin(),writes.end());
        word(s.d[7],get(ram,0xd418,2));
        if (low(s.d[7]) >= get(ram,0xd41c,2)) { done = true; break; }
    }
    if (!done) { error = "scene initialization temporary phase budget exceeded"; return false; }
    s.a[0] = 0x10d38e; s.d[0] = get(ram,0xd38e,4); s.d[1] = get(ram,0xd392,4); s.a[1] = 0;
    if (!node(ram,0x43e22,s,error)) return false;
    for (unsigned int i = 0; i < 4; ++i) {
        s.a[0] = static_cast<std::uint32_t>(0x100000+nodes[i]); s.d[0] = get(ram,nodes[i],4); s.d[1] = get(ram,nodes[i]+4,4); s.a[1] = 0;
        if (!node(ram,0x16fee,s,error)) return false;
    }
    word(s.d[7],get(ram,0xd41e,2));
    if (low(s.d[7]) < get(ram,0xd41c,2) && !duration(ram,windows,s,error)) return false;
    SceneCommandState c = command_state(s);
    if (!execute_scene_placement(ram,0x1a414,windows,c,parent,error)) return false;
    apply(s,c); put(ram,0x10,2,0); port(output,0x2ffff2,0x1000); port(output,0x2ffff0,0); return true;
}
}
bool initialize_scene(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || tables.source_cpu_address != 0x1af12 || tables.source_rom_offset != 0x1af12 || tables.data.size() != 512) {
        error = "scene initialization requires64KiB RAM and512-byte fixed debug tables at1af12"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state; std::vector<VideoPortWrite> output;
        if (!initialize(candidate,tables,windows,next,parent_a6,output,error)) return false;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene initialization transaction"; return false; }
}
}
