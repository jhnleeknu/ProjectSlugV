#include "ms5/scene_map_transfer.h"
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
}
