#include "ms5/stage_cue_frame.h"
#include "ms5/stage_cue_control.h"
#include "ms5/sprite_submit_execution.h"
#include "ms5/scene_node.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void word(std::uint32_t& value, std::uint32_t input) { value = (value & 0xffff0000U) | low(input); }
bool fixed(const FixedDataResource& w) {
    return !(w.source_cpu_address & 1U) && w.source_cpu_address < 0x100000 &&
        w.source_rom_offset == w.source_cpu_address && !w.data.empty() && w.data.size() <= 0x100000-w.source_cpu_address;
}
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int size, std::uint32_t& value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address > 0x1000000U-size) { error = "unaligned or overflowing stage cue frame read"; return false; }
    const std::vector<std::uint8_t>* bytes = NULL; std::size_t at = 0;
    if (address >= 0x100000 && address+size <= 0x110000) { bytes = &ram; at = address-0x100000; }
    else {
        unsigned int matches = 0;
        for (std::size_t i = 0; i < windows.size(); ++i) {
            const FixedDataResource& w = windows[i]; if (!fixed(w)) continue;
            const std::uint64_t end = static_cast<std::uint64_t>(w.source_cpu_address)+w.data.size();
            if (address < end && static_cast<std::uint64_t>(address)+size > w.source_cpu_address) {
                ++matches;
                if (address >= w.source_cpu_address && static_cast<std::uint64_t>(address)+size <= end) { bytes = &w.data; at = address-w.source_cpu_address; }
            }
        }
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or partial stage cue frame fixed read"; return false; }
    }
    value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at+i]; return true;
}
bool offset_read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    std::uint32_t address, unsigned int offset, unsigned int size, std::uint32_t& value, std::string& error) {
    if (address > 0xffffffffU-offset) { error = "stage cue frame address addition overflows"; return false; }
    return read(ram,windows,address+offset,size,value,error);
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address < 0x100000 || address > 0x110000-size) { error = "stage cue frame write requires aligned complete RAM span"; return false; }
    for (unsigned int i = 0; i < size; ++i) ram[address-0x100000+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1))); return true;
}
void swap(std::uint32_t& value) { value = (value<<16)|(value>>16); }
std::uint32_t indexed(std::uint32_t base,std::uint32_t index) {
    const std::uint32_t value = low(index);
    return base+(value < 0x8000U ? value : value-0x10000U);
}
bool position(std::vector<std::uint8_t>& ram,SceneMapTransferState& s,std::string& error) {
    SceneNodeState n;
    n.d0 = s.d[0]; n.d1 = s.d[1]; n.d2 = s.d[2]; n.d3 = s.d[3];
    n.d4 = s.d[4]; n.d5 = s.d[5]; n.d6 = s.d[6]; n.d7 = s.d[7];
    n.a0 = s.a[0]; n.a1 = s.a[1]; n.a2 = s.a[2]; n.a4 = s.a[4];
    if (!step_scene_node(ram,0x43e08,n,error)) return false;
    s.d[0] = n.d0; s.d[1] = n.d1; s.d[2] = n.d2; s.d[3] = n.d3;
    s.d[4] = n.d4; s.d[5] = n.d5; s.d[6] = n.d6; s.d[7] = n.d7;
    s.a[0] = n.a0; s.a[1] = n.a1; s.a[2] = n.a2; s.a[4] = n.a4;
    return true;
}
bool sprite(std::vector<std::uint8_t>& ram,StageCueFrameState& state,SpriteSubmitStatus& status,std::string& error) {
    SpriteSubmitExecutionState submission; submission.registers = state.registers; submission.waiting = state.waiting_for_sprite;
    if (!execute_sprite_submit(ram,submission,status,error)) return false;
    state.registers = submission.registers; state.waiting_for_sprite = submission.waiting; return true;
}
bool execute(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    StageCueFrameState& state,std::uint32_t a6,SpriteSubmitStatus& status,std::string& error) {
    if (state.waiting_for_sprite) return sprite(ram,state,status,error);
    SceneMapTransferState& s = state.registers; std::uint32_t value = 0; bool allocation_carry = false;
    if (!read(ram,windows,0x10de2f,1,value,error)) return false;
    if (value != 0) {
        if (!write(ram,0x10de2f,1,0,error)) return false;
        if (!read(ram,windows,0x10de26,4,value,error)) return false; s.a[0] = value;
        s.d[0] = 0;
        if (!offset_read(ram,windows,s.a[0],7,1,value,error)) return false; s.d[0] = value;
        word(s.d[0],s.d[0]-0x1cU);
        if ((s.d[0]&255U) < 0x20U) {
            const std::uint16_t index = low(s.d[0]);
            if (!step_stage_cue_control(ram,0xe8af4,windows,s,a6,allocation_carry,error)) return false;
            const std::uint16_t x = low(s.d[0]), y = low(s.d[1]);
            s.a[0] = 0xd5f16; word(s.d[0],0); s.a[1] = 0x100bf4;
            if (!step_stage_cue_control(ram,0x2986,windows,s,a6,allocation_carry,error)) return false;
            s.a[0] += 0x2e; s.a[1] = 0x10d38e; word(s.d[1],y); word(s.d[0],x);
            if (!position(ram,s,error)) return false;
            s.a[0] += 0x48; word(s.d[0],index); s.a[1] = 0xe8a0c;
            word(s.d[0],s.d[0]<<2); s.a[1] = indexed(s.a[1],s.d[0]);
            for (unsigned int i = 0; i < 2; ++i) {
                if (!read(ram,windows,s.a[1],2,value,error)) return false; s.a[1] += 2;
                if (!write(ram,s.a[0],2,value,error)) return false; s.a[0] += 2;
            }
        }
    }
    if (!read(ram,windows,0x10de2e,1,value,error)) return false;
    if (value == 0) {
        if (!step_stage_cue_control(ram,0xe8ad0,windows,s,a6,allocation_carry,error)) return false;
        s.a[1] = s.a[0]+4U;
        if (!write(ram,0x10de26,4,s.a[1],error)) return false;
    }
    if (!read(ram,windows,0x10f001,1,value,error)) return false;
    if (!(value&2U)) return true;
    s.a[1] = 0x10d38e;
    if (!read(ram,windows,0x10de26,4,value,error)) return false; s.a[0] = value;
    if (s.a[0] == 0) return true;
    if (!step_stage_cue_control(ram,0xe8af4,windows,s,a6,allocation_carry,error)) return false;
    if (!read(ram,windows,0x10d3a2,2,value,error)) return false; word(s.d[0],s.d[0]+value);
    if (!read(ram,windows,0x10d3a6,2,value,error)) return false; word(s.d[1],s.d[1]+value);
    swap(s.d[0]); word(s.d[0],s.d[1]); s.d[1] = 0xffff0000U;
    if (low(s.d[0]) >= 0x1e0U) s.d[1] |= 2U;
    s.d[5] = 0xffffffffU; s.d[7] = 0xba2b;
    return sprite(ram,state,status,error);
}
}
bool step_stage_cue_frame(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    StageCueFrameState& state,std::uint32_t parent_a6,SpriteSubmitStatus& debug_status,std::string& error) {
    if (ram.size() != 65536) { error = "stage cue frame requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; StageCueFrameState next = state; SpriteSubmitStatus status = debug_status;
        if (!execute(candidate,windows,next,parent_a6,status,error)) return false;
        ram.swap(candidate); state = next; debug_status = status; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage cue frame transaction"; return false; }
}
}
