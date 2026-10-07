#include "ms5/scene_map_transfer.h"
#include "ms5/scene_map_refresh.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void set_word(std::uint32_t& value, std::uint32_t word) { value = (value & 0xffff0000U) | static_cast<std::uint16_t>(word); }
void set_byte(std::uint32_t& value, std::uint32_t byte) { value = (value & 0xffffff00U) | (byte & 255U); }
std::uint32_t swap(std::uint32_t value) { return (value << 16) | (value >> 16); }
std::uint32_t signed_word(std::uint32_t value) { return low(value) < 0x8000 ? low(value) : 0xffff0000U | low(value); }
std::uint32_t add_signed_word(std::uint32_t address, std::uint32_t value) { return address + signed_word(value); }
bool read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    unsigned int bank, std::uint32_t address, unsigned int size, std::uint32_t& result, std::string& error) {
    if ((size > 1 && (address & 1U)) || address > 0x1000000U - size) { error = "unaligned or overflowing scene map read"; return false; }
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
        if (matches != 1 || bytes == NULL) { error = "missing, ambiguous or cross-window scene map read"; return false; }
    }
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value << 8) | (*bytes)[at + i]; result = value; return true;
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value, std::string& error) {
    if ((size > 1 && (address & 1U)) || address < 0x100000 || address > 0x110000 - size) { error = "scene map RAM write outside aligned span"; return false; }
    const std::size_t at = address - 0x100000;
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
    return true;
}
void emit(std::vector<VideoPortWrite>& ports, unsigned int size, std::uint32_t address, std::uint32_t value) {
    VideoPortWrite output; output.size = static_cast<std::uint8_t>(size); output.address = address; output.value = value; ports.push_back(output);
}
bool select_bank(std::vector<std::uint8_t>& ram, unsigned int& bank, unsigned int selected,
    std::vector<VideoPortWrite>& ports, std::string& error) {
    if (!write(ram,0x100010,2,selected == 3 ? 1 : 0,error)) return false;
    emit(ports,2,0x2ffff2,selected == 3 ? 0x2000 : 0x1000); emit(ports,2,0x2ffff0,0); bank = selected; return true;
}
}
bool transfer_scene_map(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& state, bool& copied, std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || (state.a[0] & 1U) || state.a[0] < 0x100000 || state.a[0] >= 0x110000 || (state.a[1] & 1U) || state.a[1] >= 0x110000) { error = "scene transfer requires64KiB RAM and aligned node"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state; std::vector<VideoPortWrite> output;
        unsigned int bank = 2; std::uint32_t value = 0; bool accepted = false;
        // Native clipping uses unsigned subtraction carry and WORD wrap.
        if (!read(candidate,windows,bank,next.a[1] + 4,2,value,error)) return false; set_word(next.d[7],value);
        set_word(next.d[2],next.d[2] - 1U); set_word(next.d[7],next.d[7] + next.d[2]); set_word(next.d[0],next.d[0] + next.d[2]);
        bool rejected = low(next.d[0]) >= low(next.d[7]);
        if (!rejected) {
            set_word(next.d[7],next.d[7] - next.d[2]); const bool borrow = low(next.d[0]) < low(next.d[2]); set_word(next.d[0],next.d[0] - next.d[2]);
            if (borrow) { set_word(next.d[4],next.d[4] - next.d[0]); set_word(next.d[2],next.d[2] + next.d[0]); next.d[0] = 0; }
            set_word(next.d[2],next.d[2] + 1U); set_word(next.d[7],next.d[7] - next.d[0]);
            const bool right = low(next.d[7]) < low(next.d[2]); set_word(next.d[7],next.d[7] - next.d[2]); if (right) set_word(next.d[2],next.d[2] + next.d[7]);
            if (!read(candidate,windows,bank,next.a[1] + 6,2,value,error)) return false; set_word(next.d[7],value);
            set_word(next.d[3],next.d[3] - 1U); set_word(next.d[7],next.d[7] + next.d[3]); set_word(next.d[1],next.d[1] + next.d[3]);
            rejected = low(next.d[1]) >= low(next.d[7]);
            if (!rejected) {
                set_word(next.d[7],next.d[7] - next.d[3]); const bool above = low(next.d[1]) < low(next.d[3]); set_word(next.d[1],next.d[1] - next.d[3]);
                if (above) { set_word(next.d[5],next.d[5] + next.d[1]); set_word(next.d[3],next.d[3] + next.d[1]); next.d[1] = 0; }
                set_word(next.d[3],next.d[3] + 1U); set_word(next.d[7],next.d[7] - next.d[1]);
                const bool below = low(next.d[7]) < low(next.d[3]); set_word(next.d[7],next.d[7] - next.d[3]); if (below) set_word(next.d[3],next.d[3] + next.d[7]);
            }
        }
        if (!rejected) {
            set_word(next.d[4],next.d[4] & 31U); set_word(next.d[5],(~next.d[5]) & 31U);
            std::uint16_t saved[6]; for (unsigned int i = 0; i < 6; ++i) saved[i] = low(next.d[i]);
            if (!select_bank(candidate,bank,3,output,error)) return false;
            if (!read(candidate,windows,bank,next.a[1],2,value,error)) return false; set_word(next.d[7],value);
            if (!read(candidate,windows,bank,0x200004,4,next.a[2],error)) return false;
            set_word(next.d[7],next.d[7] << 2);
            if (!read(candidate,windows,bank,add_signed_word(next.a[2],next.d[7]),4,next.a[2],error)) return false; next.a[2] += 4;
            if (!read(candidate,windows,bank,next.a[1] + 6,2,value,error)) return false; set_word(next.d[6],value);
            if (!read(candidate,windows,bank,next.a[0] + 0x26,2,value,error)) return false; set_word(next.d[7],value);
            if ((low(next.d[7]) & 0x8000U) == 0) {
                std::uint32_t cells = 0;
                next.d[0] = static_cast<std::uint32_t>(low(next.d[0])) * low(next.d[6]); next.d[1] &= 0xffff;
                next.d[0] += next.d[1]; next.d[0] <<= 2; next.a[2] += next.d[0]; set_word(next.d[6],next.d[6] << 2);
                if (!read(candidate,windows,bank,next.a[0] + 0x26,2,value,error)) return false; set_word(next.d[0],value + 1U); set_word(next.d[0],next.d[0] + next.d[0]);
                set_word(next.d[4],next.d[4] + next.d[4]); set_word(next.d[5],next.d[5] + next.d[5]); next.a[3] = next.a[0] + 0x3a;
                do {
                    if (!read(candidate,windows,bank,add_signed_word(next.a[3],next.d[4]),1,value,error)) return false; set_byte(next.d[1],value);
                    const unsigned int byte = next.d[1] & 255U; set_byte(next.d[1],(byte >> 3) | ((byte & 128U) ? 0xe0U : 0U));
                    set_byte(next.d[1],next.d[1] + next.d[1]); set_byte(next.d[1],next.d[1] + next.d[5]); set_word(next.d[1],next.d[1] & 0x3eU);
                    set_word(next.d[7],next.d[0]); set_word(next.d[7],next.d[7] + next.d[4]); set_word(next.d[7],next.d[7] << 5); set_word(next.d[7],next.d[7] + next.d[1]);
                    next.a[4] = next.a[2]; next.d[6] = swap(next.d[6]); set_word(next.d[6],next.d[3]);
                    do {
                        next.d[7] = swap(next.d[7]);
                        if (!read(candidate,windows,bank,next.a[4],2,value,error)) return false; next.a[4] += 2; set_word(next.d[7],value); emit(output,4,0x3c0000,next.d[7]);
                        next.d[7] += 0x10000;
                        if (!read(candidate,windows,bank,next.a[4],2,value,error)) return false; next.a[4] += 2; set_word(next.d[7],value);
                        if (++cells > 1048576U) { error = "scene primary temporary resource budget exceeded"; return false; }
                        emit(output,4,0x3c0000,next.d[7]);
                        next.d[7] = swap(next.d[7]); set_word(next.d[7],next.d[7] - 1U); set_word(next.d[7],next.d[7] - next.d[1]);
                        set_byte(next.d[1],next.d[1] + 2U); set_byte(next.d[1],next.d[1] & 0x3eU); set_byte(next.d[7],next.d[7] + next.d[1]);
                        set_word(next.d[6],next.d[6] - 1U);
                    } while (low(next.d[6]) != 0);
                    next.d[6] = swap(next.d[6]); next.a[2] = add_signed_word(next.a[2],next.d[6]);
                    set_word(next.d[4],next.d[4] + 2U); set_word(next.d[4],next.d[4] & 0x3eU); set_word(next.d[2],next.d[2] - 1U);
                } while (low(next.d[2]) != 0);
            }
            for (unsigned int i = 0; i < 6; ++i) next.d[i] = signed_word(saved[i]);
            if (!select_bank(candidate,bank,2,output,error)) return false;
            if (!read(candidate,windows,bank,next.a[1] + 2,2,value,error)) return false; set_word(next.d[7],value);
            if (low(next.d[7]) != 0) {
                if (!read(candidate,windows,bank,0x200010,4,next.a[2],error)) return false; set_word(next.d[7],next.d[7] << 2);
                if (!read(candidate,windows,bank,add_signed_word(next.a[2],next.d[7]),4,next.d[7],error)) return false;
                const bool empty = next.d[7] == 0xffffffff;
                std::uint32_t cells = 0;
                if (!empty) {
                    next.a[2] = next.d[7]; set_word(next.d[0],next.d[0] << 2); next.a[2] = add_signed_word(next.a[2],next.d[0]); set_word(next.d[1],next.d[1] << 2);
                }
                set_word(next.d[4],next.d[4] << 8); set_word(next.d[5],next.d[5] << 2); set_word(next.d[2],next.d[2] << 1);
                if (empty) next.d[0] = 0;
                do {
                    set_word(next.d[4],next.d[4] & 0x1f80U);
                    if (!empty) {
                        next.a[4] = next.a[2]; if (!read(candidate,windows,bank,next.a[2],2,value,error)) return false; next.a[2] += 2;
                        next.a[4] = add_signed_word(next.a[4],value); next.a[4] = add_signed_word(next.a[4],next.d[1]);
                    }
                    next.a[3] = add_signed_word(next.a[0] + 0x80,next.d[4]);
                    if (empty) set_word(next.d[7],next.d[5]); else set_word(next.d[0],next.d[5]); set_word(next.d[6],next.d[3]);
                    do {
                        if (empty) { set_word(next.d[7],next.d[7] & 0x7cU); if (!write(candidate,add_signed_word(next.a[3],next.d[7]),4,next.d[0],error)) return false; set_word(next.d[7],next.d[7] + 4U); }
                        else { set_word(next.d[0],next.d[0] & 0x7eU); if (!read(candidate,windows,bank,next.a[4],4,value,error)) return false; next.a[4] += 4; if (!write(candidate,add_signed_word(next.a[3],next.d[0]),4,value,error)) return false; set_word(next.d[0],next.d[0] + 4U); }
                        if (++cells > 1048576U) { error = "scene secondary temporary resource budget exceeded"; return false; }
                        set_word(next.d[6],next.d[6] - 1U);
                    } while (low(next.d[6]) != 0);
                    if (!empty) next.a[2] = add_signed_word(next.a[2],next.d[6]);
                    set_word(next.d[4],next.d[4] + 0x80U); set_word(next.d[2],next.d[2] - 1U);
                } while (low(next.d[2]) != 0);
            }
            if (!select_bank(candidate,bank,2,output,error)) return false;
            if (!read(candidate,windows,bank,next.a[0] + 0x7a,1,value,error) || !write(candidate,next.a[0] + 0x7a,1,value | 0x80,error)) return false;
            accepted = true;
        }
        ram.swap(candidate); state = next; copied = accepted; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene map transfer transaction"; return false; }
}
namespace {
std::uint32_t asr4(std::uint32_t value) { return (low(value) >> 4) | ((low(value) & 0x8000U) ? 0xf000U : 0); }
bool node_read(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, unsigned int offset, unsigned int size, std::uint32_t& value, std::string& error) {
    return read(ram,windows,2,s.a[0] + offset,size,value,error);
}
bool columns(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::string& error) {
    std::uint32_t value = 0; unsigned int searches = 0;
    if (!node_read(ram,windows,s,0x36,4,s.a[2],error) || !node_read(ram,windows,s,0x2e,4,s.a[1],error)) return false;
    set_word(s.d[6],s.d[2] - 1U);
    do {
        if (!read(ram,windows,2,s.a[1]+4,2,value,error)) return false;
        if (low(s.d[0]) < value) {
            set_word(s.d[7],(s.d[4] & 31U)*2U); s.a[3] = add_signed_word(s.a[0]+0x3a,s.d[7]);
            if (s.a[2] == 0) { if (!write(ram,s.a[3],2,0x21,error)) return false; }
            else if (s.a[2] == 0xffffffffU) { if (!write(ram,s.a[3],1,0,error)) return false; }
            else {
                for (;;) {
                    if (!read(ram,windows,2,s.a[2],2,value,error)) return false; set_word(s.d[7],value);
                    if (value == 0 || low(s.d[0]) >= value) break;
                    if (++searches > 1048576U) { error = "scene column temporary search budget exceeded"; return false; }
                    s.a[2] -= 4;
                }
                for (;;) {
                    s.a[4] = s.a[2]+4;
                    if (!read(ram,windows,2,s.a[4],2,value,error)) return false; set_word(s.d[7],value);
                    if ((value & 0x8000U) || low(s.d[0]) < value) break;
                    if (++searches > 1048576U) { error = "scene column temporary search budget exceeded"; return false; }
                    s.a[2] = s.a[4];
                }
                if (!read(ram,windows,2,s.a[2]+3,1,value,error)) return false; set_byte(s.d[7],value);
                if (!write(ram,s.a[3]+1,1,s.d[7],error)) return false;
                if (!node_read(ram,windows,s,0x35,1,value,error)) return false; set_byte(s.d[7],value);
                if (!read(ram,windows,2,s.a[2]+2,1,value,error)) return false;
                set_byte(s.d[7],s.d[7]-value); set_byte(s.d[7],s.d[7]+1U); set_byte(s.d[7],s.d[7]<<3);
                if (!write(ram,s.a[3],1,s.d[7],error)) return false;
            }
        }
        set_word(s.d[0],s.d[0]+1U); set_word(s.d[4],s.d[4]+1U); set_word(s.d[6],s.d[6]-1U);
    } while (low(s.d[6]) != 0xffffU);
    set_word(s.d[0],s.d[0]-s.d[2]); set_word(s.d[4],s.d[4]-s.d[2]);
    return write(ram,s.a[0]+0x36,4,s.a[2],error);
}
bool flag(const std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, unsigned int bit, bool& enabled, std::string& error) {
    std::uint32_t value = 0; if (!node_read(ram,windows,s,0x7a,1,value,error)) return false;
    enabled = (value & (1U << bit)) != 0; return true;
}
bool copy_map(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::vector<VideoPortWrite>& ports, bool restore, std::string& error) {
    std::uint16_t saved[6]; for (unsigned int i = 0; i < 6; ++i) saved[i] = low(s.d[i]);
    std::vector<VideoPortWrite> output; bool copied = false;
    if (!transfer_scene_map(ram,windows,s,copied,output,error)) return false;
    ports.insert(ports.end(),output.begin(),output.end());
    if (restore) for (unsigned int i = 0; i < 6; ++i) s.d[i] = signed_word(saved[i]);
    return true;
}
bool wrapped(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::vector<VideoPortWrite>& ports, std::string& error) {
    bool enabled = false; std::uint32_t dimension = 0;
    for (unsigned int i = 0; i < 2; ++i) {
        if (!flag(ram,windows,s,3+i,enabled,error)) return false;
        if (enabled) {
            if (!read(ram,windows,2,s.a[1]+4+2*i,2,dimension,error)) return false;
            if (low(s.d[i]) >= dimension) {
                if (dimension == 0) { error = "scene wrap zero divisor"; return false; }
                const std::uint32_t coordinate = low(s.d[i]);
                s.d[i] = ((coordinate / dimension) << 16) | (coordinate % dimension);
            }
        }
    }
    if (!columns(ram,windows,s,error) || !copy_map(ram,windows,s,ports,true,error)) return false;
    if (!flag(ram,windows,s,4,enabled,error)) return false;
    if (enabled) {
        std::uint16_t saved[6]; for (unsigned int i = 0; i < 6; ++i) saved[i] = low(s.d[i]);
        if (!read(ram,windows,2,s.a[1]+6,2,dimension,error)) return false; set_word(s.d[1],s.d[1]-dimension);
        if (!copy_map(ram,windows,s,ports,false,error)) return false;
        for (unsigned int i = 0; i < 6; ++i) s.d[i] = signed_word(saved[i]);
    }
    if (!flag(ram,windows,s,3,enabled,error)) return false;
    if (!enabled) return true;
    if (!read(ram,windows,2,s.a[1]+4,2,dimension,error)) return false; set_word(s.d[0],s.d[0]-dimension);
    if (!columns(ram,windows,s,error) || !copy_map(ram,windows,s,ports,true,error)) return false;
    if (!flag(ram,windows,s,4,enabled,error)) return false;
    if (enabled) {
        if (!read(ram,windows,2,s.a[1]+6,2,dimension,error)) return false; set_word(s.d[1],s.d[1]-dimension);
        if (!copy_map(ram,windows,s,ports,false,error)) return false;
    }
    return true;
}
bool scroll_coordinates(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::string& error) {
    std::uint32_t value = 0; set_word(s.d[0],s.d[4]); set_word(s.d[1],s.d[5]);
    if (!node_read(ram,windows,s,0x32,2,value,error)) return false; set_word(s.d[0],s.d[0]-value);
    if (!node_read(ram,windows,s,0x34,2,value,error)) return false; set_word(s.d[1],s.d[1]-value); set_word(s.d[1],0U-s.d[1]); return true;
}
bool refresh(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& s, std::vector<VideoPortWrite>& ports, bool moved, std::string& error) {
    std::uint32_t value = 0; bool enabled = false;
    if (!node_read(ram,windows,s,0x2e,4,s.a[1],error)) return false;
    if (s.a[1] == 0) return true;
    if (!moved) {
        set_word(s.d[4],0xffa0);
        if (!node_read(ram,windows,s,0x14,2,value,error)) return false; set_word(s.d[4],s.d[4]-value); set_word(s.d[4],asr4(s.d[4]));
        set_word(s.d[5],0x27f);
        if (!node_read(ram,windows,s,0x18,2,value,error)) return false; set_word(s.d[5],s.d[5]-value); set_word(s.d[5],asr4(s.d[5]));
        if (!scroll_coordinates(ram,windows,s,error)) return false;
        set_word(s.d[2],32); set_word(s.d[3],32); return wrapped(ram,windows,s,ports,error);
    }
    if (!flag(ram,windows,s,1,enabled,error)) return false;
    if (enabled) {
        if (!node_read(ram,windows,s,0x14,2,value,error)) return false; set_word(s.d[2],asr4(value));
        if (!node_read(ram,windows,s,0x1c,2,value,error)) return false; set_word(s.d[3],asr4(value)); set_word(s.d[2],s.d[2]-s.d[3]);
        if (low(s.d[2]) != 0) {
            s.d[4] = 0xfffffffaU; set_word(s.d[4],s.d[4]-s.d[3]); set_word(s.d[4],s.d[4]-s.d[2]);
            if (low(s.d[2]) & 0x8000U) { set_word(s.d[4],s.d[4]+32); set_word(s.d[4],s.d[4]+s.d[2]); set_word(s.d[2],0U-s.d[2]); }
            set_word(s.d[5],0x27);
            if (!node_read(ram,windows,s,0x18,2,value,error)) return false; set_word(s.d[3],asr4(value)); set_word(s.d[5],s.d[5]-s.d[3]); s.d[3] = 32;
            if (!scroll_coordinates(ram,windows,s,error) || !wrapped(ram,windows,s,ports,error)) return false;
        }
    }
    if (!flag(ram,windows,s,2,enabled,error)) return false;
    if (enabled) {
        if (!node_read(ram,windows,s,0x18,2,value,error)) return false; set_word(s.d[3],asr4(value));
        if (!node_read(ram,windows,s,0x20,2,value,error)) return false; set_word(s.d[2],asr4(value)); set_word(s.d[3],s.d[3]-s.d[2]);
        if (low(s.d[3]) != 0) {
            s.d[5] = 7; set_word(s.d[5],s.d[5]-s.d[2]);
            if (low(s.d[3]) & 0x8000U) { set_word(s.d[3],0U-s.d[3]); set_word(s.d[5],s.d[5]+32); set_word(s.d[5],s.d[5]+s.d[3]); }
            if (!node_read(ram,windows,s,0x14,2,value,error)) return false; set_word(s.d[2],asr4(value));
            set_word(s.d[4],0xfffa); set_word(s.d[4],s.d[4]-s.d[2]); s.d[2] = 32;
            if (!scroll_coordinates(ram,windows,s,error) || !wrapped(ram,windows,s,ports,error)) return false;
        }
    }
    return true;
}
bool refresh_transaction(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    SceneMapTransferState& state, std::vector<VideoPortWrite>& ports, std::string& error, unsigned int mode) {
    if (ram.size() != 65536 || (state.a[0]&1U) || state.a[0] < 0x100000 || state.a[0] >= 0x110000) { error = "scene refresh requires64KiB RAM and aligned node"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneMapTransferState next = state; std::vector<VideoPortWrite> output;
        bool success = false;
        if (mode == 0) success = columns(candidate,windows,next,error);
        else if (mode == 1) success = wrapped(candidate,windows,next,output,error);
        else success = refresh(candidate,windows,next,output,mode == 3,error);
        if (!success) return false;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene refresh transaction"; return false; }
}
}
bool update_scene_columns(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, SceneMapTransferState& state, std::vector<VideoPortWrite>& ports, std::string& error) { return refresh_transaction(ram,windows,state,ports,error,0); }
bool transfer_wrapped_scene_map(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, SceneMapTransferState& state, std::vector<VideoPortWrite>& ports, std::string& error) { return refresh_transaction(ram,windows,state,ports,error,1); }
bool refresh_scene_map(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, SceneMapTransferState& state, std::vector<VideoPortWrite>& ports, std::string& error) { return refresh_transaction(ram,windows,state,ports,error,2); }
bool refresh_moved_scene_map(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, SceneMapTransferState& state, std::vector<VideoPortWrite>& ports, std::string& error) { return refresh_transaction(ram,windows,state,ports,error,3); }

}
