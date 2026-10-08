#include "ms5/stage_buffer_frame.h"
#include "ms5/sprite_submit_execution.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void set_word(std::uint32_t& value, std::uint32_t word) { value = (value & 0xffff0000U) | static_cast<std::uint16_t>(word); }
void set_byte(std::uint32_t& value, std::uint32_t byte) { value = (value & 0xffffff00U) | (byte & 255U); }
std::uint32_t swap(std::uint32_t value) { return (value << 16) | (value >> 16); }
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    unsigned int bank, std::uint32_t address, unsigned int size, std::uint32_t& result, std::string& error) {
    if ((size > 1 && (address & 1U)) || address > 0x1000000U - size) { error = "unaligned or overflowing stage buffer frame read"; return false; }
    const std::vector<std::uint8_t>* bytes = NULL; std::size_t at = 0;
    if (address >= 0x100000 && address + size <= 0x110000) { bytes = &ram; at = address - 0x100000; }
    else {
        unsigned int matches = 0;
        for (std::size_t i = 0; i < windows.size(); ++i) {
            const FixedDataResource& window = windows[i]; const std::uint32_t start = window.source_cpu_address;
            const bool fixed = (start & 1U) == 0 && start < 0x100000 && window.source_rom_offset == start && window.data.size() <= 0x100000 - start;
            const bool banked = (start & 1U) == 0 && start >= 0x200000 && start < 0x2ffff0 && window.data.size() <= 0x2ffff0 - start &&
                window.source_rom_offset == start + (bank == 3 ? 0x100000U : 0U);
            if (!(fixed || banked) || window.data.empty()) continue;
            const std::uint64_t end = static_cast<std::uint64_t>(start) + window.data.size();
            if (address < end && static_cast<std::uint64_t>(address) + size > start) {
                ++matches;
                if (address >= start && static_cast<std::uint64_t>(address) + size <= end) { bytes = &window.data; at = address - start; }
            }
        }
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or cross-window stage buffer frame read"; return false; }
    }
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at + i]; result = value; return true;
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address < 0x100000 || address > 0x110000 - size) { error = "stage buffer frame RAM write outside aligned span"; return false; }
    const std::size_t at = address - 0x100000;
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
    return true;
}
void emit(std::vector<VideoPortWrite>& ports, unsigned int size, std::uint32_t address, std::uint32_t value) {
    VideoPortWrite output; output.size = static_cast<std::uint8_t>(size); output.address = address; output.value = value; ports.push_back(output);
}
bool offset_read(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    std::uint32_t bank,std::uint32_t address,unsigned int offset,unsigned int size,std::uint32_t& value,std::string& error) {
    if (address > 0xffffffffU-offset) { error = "stage buffer frame address addition overflows"; return false; }
    return read(ram,windows,bank,address+offset,size,value,error);
}
bool reset_bank(std::vector<std::uint8_t>& ram,StageBufferFrameState& state,std::vector<VideoPortWrite>& ports,std::string& error) {
    if (!write(ram,0x100010,2,0,error)) return false;
    emit(ports,2,0x2ffff2,0x1000); emit(ports,2,0x2ffff0,0); state.bank = 2; return true;
}
void clear_saved(StageBufferFrameState& state) {
    state.phase = state.saved_a6 = state.saved_slot_a4 = state.saved_slot_d7 = 0;
    state.saved_d0 = state.saved_d1 = state.saved_d7 = state.saved_a0 = 0;
}
bool sprite(std::vector<std::uint8_t>& ram,StageBufferFrameState& state,unsigned int phase,bool resume,bool& waiting,std::string& error) {
    SpriteSubmitExecutionState submission; submission.registers = state.registers; submission.waiting = resume;
    SpriteSubmitStatus status = SpriteAccepted;
    if (!execute_sprite_submit(ram,submission,status,error)) return false;
    state.registers = submission.registers; waiting = submission.waiting;
    if (waiting) state.phase = phase;
    return true;
}
bool prepare_first(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,StageBufferFrameState& state,std::string& error) {
    SceneMapTransferState& s = state.registers; std::uint32_t value = 0; s.d[1] = 0xffff0000U;
    if (!offset_read(ram,windows,state.bank,state.a6,0x15,1,value,error)) return false;
    if (value&4U) set_word(s.d[1],4);
    if (!read(ram,windows,state.bank,s.a[0],4,value,error)) return false; s.d[0] = value; s.a[0] += 4;
    if (!offset_read(ram,windows,state.bank,state.a6,0x15,1,value,error)) return false;
    if (value&1U) { s.d[0] = swap(s.d[0]); set_word(s.d[0],0U-s.d[0]); s.d[0] = swap(s.d[0]); s.d[1] |= 1U; }
    if (!offset_read(ram,windows,state.bank,state.a6,0x15,1,value,error)) return false;
    if (value&2U) { set_word(s.d[0],0U-s.d[0]); s.d[1] |= 2U; }
    s.d[0] = swap(s.d[0]);
    if (!offset_read(ram,windows,state.bank,state.a6,0x42,2,value,error)) return false; set_word(s.d[0],s.d[0]+value);
    s.d[0] = swap(s.d[0]);
    if (!offset_read(ram,windows,state.bank,state.a6,0x46,2,value,error)) return false; set_word(s.d[0],s.d[0]+value);
    state.saved_d0 = s.d[0]; state.saved_d1 = s.d[1]; state.saved_d7 = s.d[7]; state.saved_a0 = s.a[0];
    s.d[5] = 0xffffffffU; return true;
}
bool prepare_second(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,StageBufferFrameState& state,std::string& error) {
    SceneMapTransferState& s = state.registers; std::uint32_t value = 0;
    s.a[0] = state.saved_a0; s.d[7] = state.saved_d7; s.d[1] = state.saved_d1; s.d[0] = state.saved_d0;
    state.saved_d0 = state.saved_d1 = state.saved_d7 = 0;
    if (!read(ram,windows,state.bank,s.a[0],2,value,error)) return false; set_word(s.d[2],value); s.a[0] += 2;
    if (!read(ram,windows,state.bank,s.a[0],2,value,error)) return false; set_word(s.d[3],value); s.a[0] += 2;
    set_word(s.d[1],s.d[1]^3U);
    if (!offset_read(ram,windows,state.bank,state.a6,0x15,1,value,error)) return false;
    if (value&1U) set_word(s.d[2],0U-s.d[2]);
    if (!offset_read(ram,windows,state.bank,state.a6,0x15,1,value,error)) return false;
    if (value&2U) set_word(s.d[3],0U-s.d[3]);
    s.d[0] = swap(s.d[0]); set_word(s.d[0],s.d[0]+s.d[2]); s.d[0] = swap(s.d[0]); set_word(s.d[0],s.d[0]+s.d[3]);
    state.saved_a0 = s.a[0]; s.d[5] = 0xffffffffU; return true;
}
bool finish_slot(std::vector<std::uint8_t>& ram,StageBufferFrameState& state,std::vector<VideoPortWrite>& ports,std::string& error) {
    state.registers.a[0] = state.saved_a0;
    if (!reset_bank(ram,state,ports,error)) return false;
    set_word(state.registers.d[7],state.saved_slot_d7); state.registers.a[4] = state.saved_slot_a4;
    return reset_bank(ram,state,ports,error);
}
bool normal(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,StageBufferFrameState& state,std::string& error) {
    SceneMapTransferState& s = state.registers; std::uint32_t value = 0; s.d[7] = 0;
    if (!read(ram,windows,state.bank,0x10dc88,4,value,error)) return false; s.a[0] = value;
    for (unsigned int i = 0; i < 16; ++i) {
        if (!read(ram,windows,state.bank,s.a[0],2,value,error)) return false;
        if (!write(ram,s.a[0],2,value>>1,error)) return false; s.a[0] += 2;
    }
    if (s.a[0] >= 0x10dc88) s.a[0] = 0x10db88;
    if (!write(ram,0x10dc88,4,s.a[0],error)) return false;
    if (!read(ram,windows,state.bank,0x10db85,1,value,error) || !write(ram,0x10db84,1,value,error) || !write(ram,0x10db85,1,0,error)) return false;
    if (!read(ram,windows,state.bank,0x10db87,1,value,error) || !write(ram,0x10db86,1,value,error) || !write(ram,0x10db87,1,0,error)) return false;
    if (!read(ram,windows,state.bank,0x10f001,1,value,error)) return false;
    if (value&1U) {
        if (!read(ram,windows,state.bank,0x104cab,1,value,error)) return false; set_byte(s.d[0],value);
        if (!read(ram,windows,state.bank,0x104cb1,1,value,error)) return false; set_byte(s.d[0],s.d[0]|value); set_byte(s.d[0],s.d[0]&128U);
        if ((s.d[0]&255U) != 0 && !write(ram,0x10db84,1,255,error)) return false;
    }
    s.a[4] = 0x10d746; s.a[3] = 0x10d918;
    if (!read(ram,windows,state.bank,0x10d744,1,value,error)) return false;
    if (!write(ram,0x10d744,1,value^128U,error)) return false;
    if (!(value&128U)) { const std::uint32_t temp = s.a[3]; s.a[3] = s.a[4]; s.a[4] = temp; }
    s.d[1] = 0xffffffffU;
    if (!write(ram,s.a[4]+0x1d0,2,0,error)) return false;
    for (unsigned int i = 0; i < 8; ++i) s.d[i] = 0;
    s.a[4] += 0xd0;
    // Predecrement MOVEM writes reverse register order, seven native blocks.
    for (unsigned int block = 0; block < 7; ++block) {
        const unsigned int count = block == 6 ? 4 : 8;
        for (unsigned int reg = count; reg > 0; --reg) {
            s.a[4] -= 4;
            if (!write(ram,s.a[4],4,s.d[reg-1],error)) return false;
        }
    }
    clear_saved(state); return true;
}
bool execute(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,StageBufferFrameState& state,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    SceneMapTransferState& s = state.registers; std::uint32_t value = 0; bool waiting = false;
    if (state.phase != 0) {
        const std::uint32_t phase = state.phase;
        if (!sprite(ram,state,phase,true,waiting,error)) return false;
        if (waiting) return true;
        if (phase == 1) {
            if (!prepare_second(ram,windows,state,error) || !sprite(ram,state,2,false,waiting,error)) return false;
            if (waiting) return true;
        }
        if (!finish_slot(ram,state,ports,error)) return false;
        set_word(s.d[7],s.d[7]+1U); s.a[4] += 8;
    } else {
        if (!read(ram,windows,state.bank,0x10f001,1,value,error)) return false;
        if (!(value&128U)) return normal(ram,windows,state,error);
        state.saved_a6 = state.a6; s.a[4] = 0x10daf8; s.d[7] = 0;
    }
    while (s.a[4] < 0x10db78) {
        if (!read(ram,windows,state.bank,s.a[4],4,value,error)) return false; state.a6 = value;
        if (!offset_read(ram,windows,state.bank,s.a[4],4,4,value,error)) return false; s.a[0] = value;
        if (state.a6 != 0 && s.a[0] != 0) {
            if (!offset_read(ram,windows,state.bank,state.a6,0x6d,1,value,error)) return false; set_byte(s.d[6],value); set_byte(s.d[6],s.d[6]&15U);
            if ((s.d[7]&255U) == (s.d[6]&255U)) {
                state.saved_slot_a4 = s.a[4]; state.saved_slot_d7 = low(s.d[7]); s.a[0] += 4; s.d[7] = 0x122b;
                if (!prepare_first(ram,windows,state,error) || !sprite(ram,state,1,false,waiting,error)) return false;
                if (waiting) return true;
                if (!prepare_second(ram,windows,state,error) || !sprite(ram,state,2,false,waiting,error)) return false;
                if (waiting) return true;
                if (!finish_slot(ram,state,ports,error)) return false;
            }
        }
        set_word(s.d[7],s.d[7]+1U); s.a[4] += 8;
    }
    state.a6 = state.saved_a6; return normal(ram,windows,state,error);
}
}
bool step_stage_buffer_frame(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    StageBufferFrameState& state,std::vector<VideoPortWrite>& ports,std::string& error) {
    const std::uint32_t slot = state.saved_slot_d7;
    if (ram.size() != 65536 || (state.bank != 2 && state.bank != 3) || state.phase > 2 ||
        (state.phase != 0 && (slot >= 16 || state.saved_slot_a4 != 0x10daf8+slot*8))) {
        error = "stage buffer frame requires64KiB RAM, bank2/3 and valid phase/slot metadata"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; StageBufferFrameState next = state; std::vector<VideoPortWrite> output;
        if (!execute(candidate,windows,next,output,error)) return false;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage buffer frame transaction"; return false; }
}
}
