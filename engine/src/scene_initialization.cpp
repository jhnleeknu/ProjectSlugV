#include "ms5/scene_initialization.h"
#include "ms5/game_screen_reset.h"
#include "ms5/scene_node.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(bytes[at]) << 8) | bytes[at + 1]);
}
std::uint32_t get(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    return (static_cast<std::uint32_t>(word(bytes,at)) << 16) | word(bytes,at + 2);
}
void put(std::vector<std::uint8_t>& bytes, std::size_t at, std::uint32_t value) {
    bytes[at] = static_cast<std::uint8_t>(value >> 24); bytes[at + 1] = static_cast<std::uint8_t>(value >> 16);
    bytes[at + 2] = static_cast<std::uint8_t>(value >> 8); bytes[at + 3] = static_cast<std::uint8_t>(value);
}
std::uint16_t lookup(const std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
                     std::size_t node, unsigned int column, unsigned int row,
                     std::uint32_t& d0, std::uint32_t& d1) {
    const unsigned int x = (column * 8U - word(ram,node + 0x14)) & 0x1f8U;
    const unsigned int y = ((row * 8U + word(ram,node + 0x18)) & 0x1f8U) >> 2;
    const unsigned int offset = (x << 4) + y + 0x80;
    d0 = (d0 & 0xffff0000U) | offset; d1 = (d1 & 0xffff0000U) | y;
    const std::uint16_t tile = word(ram,node + offset);
    const unsigned int index = (static_cast<unsigned int>(tile) + 0x58U) & 255U;
    std::uint16_t result = word(tables.data,index * 2U);
    if (result != 0x320) result = static_cast<std::uint16_t>(result | word(tables.data,0xc0U + ((tile & 0xc000U) >> 13)));
    return result;
}
}
bool update_scene_debug(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
                        std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3,
                        std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || tables.source_cpu_address != 0x1af12 || tables.source_rom_offset != 0x1af12 || tables.data.size() != 512) {
        error = "scene debug requires64KiB RAM and512-byte fixed tables at1af12"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; std::uint32_t next0 = d0, next1 = d1, next3 = d3;
        std::vector<VideoPortWrite> output; const unsigned int bits = candidate[0xf000] & 0x18U; const std::uint8_t oldflag = candidate[0xd44e];
        if (bits == 0) {
            candidate[0xd44e] = 0;
            if (oldflag != 0 && !reset_game_screen(candidate,0xcaf0,next0,next1,next3,output,error)) return false;
        } else {
            const std::size_t masks[] = {0xd3a2,0xd3a6,0x916a,0x916e,0xb1ea,0xb1ee};
            for (unsigned int index = 0; index < 6; ++index) put(candidate,masks[index],get(candidate,masks[index]) & 0xfff80000U);
            candidate[0xd44e] = 255; bool draw = oldflag == 0;
            if (!draw) {
                //Native secondLEA selectsA1, but MOVEs continue usingA0=109156.
                for (unsigned int check = 0; check < 2; ++check) {
                    next0 = get(candidate,0x916a); next1 = get(candidate,0x916e);
                    const std::uint32_t previous_x = get(candidate,0x9172), previous_y = get(candidate,0x9176);
                    next3 = previous_y - next1 - (previous_x < next0 ? 1U : 0U);
                    if (previous_x != next0 || next3 != 0) { draw = true; break; }
                }
            }
            if (draw) {
                next3 = (next3 & 0xffff0000U) | 31U;
                for (int row = 31; row >= 0; --row) {
                    for (int column = 39; column >= 0; --column) {
                        std::uint16_t tile = 0x320;
                        if ((bits & 8U) != 0) tile = lookup(candidate,tables,0x9156,column,row,next0,next1);
                        if (tile == 0x320 && (bits & 16U) != 0) tile = lookup(candidate,tables,0xb1d6,column,row,next0,next1);
                        VideoPortWrite write; write.size = 4; write.address = 0x3c0000;
                        write.value = ((0x7000U + static_cast<unsigned int>(column) * 32U + static_cast<unsigned int>(row)) << 16) | tile;
                        output.push_back(write);
                    }
                }
                next3 = (next3 & 0xffff0000U) | 0xffffU;
            }
        }
        ram.swap(candidate); d0 = next0; d1 = next1; d3 = next3; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene debug transaction"; return false; }
}
namespace {
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void port(std::vector<VideoPortWrite>& ports, std::uint32_t address, std::uint32_t value) {
    VideoPortWrite write; write.size = 2; write.address = address; write.value = value; ports.push_back(write);
}
bool node(std::vector<std::uint8_t>& ram, std::uint32_t entry, std::uint32_t address,
          std::uint32_t parent, std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3, std::string& error) {
    SceneNodeState state; state.a0 = address; state.a1 = parent; state.d0 = d0; state.d1 = d1; state.d3 = d3;
    if (!step_scene_node(ram,entry,state,error)) return false;
    d0 = state.d0; d1 = state.d1; d3 = state.d3; return true;
}
bool initialize(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
                std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3,
                std::vector<VideoPortWrite>& ports, std::string& error) {
    d0 = 0; put_word(ram,0x10,1); port(ports,0x2ffff2,0x2000); port(ports,0x2ffff0,0);
    put_word(ram,0xd41c,0); put(ram,0xd412,0); put_word(ram,0xd416,0);
    const std::size_t zero_words[] = {0xd418,0xd42a,0xd42c,0xd448,0xd44a,0xd44c,0xd432,0xd43c,0xd40c};
    for (unsigned int index = 0; index < 9; ++index) put_word(ram,zero_words[index],0);
    put_word(ram,0xd426,0xa0); put_word(ram,0xd428,0x80); put_word(ram,0xd444,0x8000); put_word(ram,0xd446,0x8000);
    put_word(ram,0xd442,0x7fff); put_word(ram,0xd440,0x7fff); put_word(ram,0xd42e,0xffff); put_word(ram,0xd430,0xffff);
    put(ram,0xd434,0); put(ram,0xd438,0); ram[0xd44e] = 0;
    put_word(ram,0xd3b8,0); put_word(ram,0xd3ba,0); put(ram,0xd3bc,0); put(ram,0xd3c0,0); put(ram,0xd3b4,0);
    d1 = 0x01000000;
    if (!node(ram,0x43e22,0x10d38e,0,d0,d1,d3,error)) return false;
    put(ram,0xd422,0); put_word(ram,0xd41e,0x7fff); put_word(ram,0xd420,0x7fff); put_word(ram,0xd43e,0);
    ram[0xd3cc] = 0;
    const std::size_t zero_longs[] = {0xd3de,0xd3e2,0xd3fc,0xd400};
    for (unsigned int index = 0; index < 4; ++index) put(ram,zero_longs[index],0);
    put_word(ram,0xd3ee,0); put_word(ram,0xd3f0,0); put_word(ram,0xd3d6,0xa0); put_word(ram,0xd3d8,0x80);
    put_word(ram,0xd3da,0); put_word(ram,0xd3dc,0); put(ram,0xd3e6,0x60000); put(ram,0xd3ea,0x60000);
    put_word(ram,0xd3ce,0x7fff); put_word(ram,0xd3d0,0x7fff); put_word(ram,0xd3d2,0x8000); put_word(ram,0xd3d4,0x8000);
    const std::size_t nodes[] = {0x9156,0xb1d6,0xd256,0xd2d6}, metadata[] = {0xd356,0xd364,0xd372,0xd380};
    for (unsigned int index = 0; index < 4; ++index) {
        for (unsigned int byte = 0; byte < 12; ++byte) ram[metadata[index] + byte] = 0;
        ram[metadata[index] + 12] = 0x10;
        if (!node(ram,0x16fac,static_cast<std::uint32_t>(0x100000 + nodes[index]),0,d0,d1,d3,error)) return false;
        d0 = get(ram,0xd38e); d1 = get(ram,0xd392);
        if (!node(ram,0x16fee,static_cast<std::uint32_t>(0x100000 + nodes[index]),0,d0,d1,d3,error)) return false;
    }
    put_word(ram,0xd404,0); put_word(ram,0xd406,0); put(ram,0xd408,0); put(ram,0xd40e,0);
    if (!node(ram,0x17292,0x109156,0,d0,d1,d3,error) || !node(ram,0x17292,0x10b1d6,0,d0,d1,d3,error)) return false;
    //Null script1a26a and19e64 are no-ops in this specialization.
    put_word(ram,0xd418,0); put(ram,0xd3bc,0); put(ram,0xd3c0,0);
    put(ram,0xd396,0U - (get(ram,0xd3bc) + get(ram,0xd38e)));
    put(ram,0xd39a,0U - (get(ram,0xd3c0) + get(ram,0xd392) - 0x01000000U));
    if (!node(ram,0x43ea8,0x10d38e,0,d0,d1,d3,error)) return false;
    d0 = (d0 & 0xffff0000U) | word(ram,0xd404); put_word(ram,0xd3a6,static_cast<std::uint16_t>(word(ram,0xd3a6) + d0));
    for (unsigned int index = 0; index < 4; ++index) {
        if ((ram[0xd40c] & (1U << (index * 2U))) == 0) {
            d0 = get(ram,0xd396); if (!node(ram,0x1724c,static_cast<std::uint32_t>(0x100000 + nodes[index]),0,d0,d1,d3,error)) return false;
        }
        if ((ram[0xd40c] & (1U << (index * 2U + 1U))) == 0) {
            d1 = get(ram,0xd39a); if (!node(ram,0x1726c,static_cast<std::uint32_t>(0x100000 + nodes[index]),0,d0,d1,d3,error)) return false;
        }
        if (!node(ram,0x1728c,static_cast<std::uint32_t>(0x100000 + nodes[index]),0,d0,d1,d3,error)) return false;
        d0 = (d0 & 0xffff0000U) | word(ram,0xd404);
        put_word(ram,nodes[index] + 0x18,static_cast<std::uint16_t>(word(ram,nodes[index] + 0x18) + d0));
    }
    std::vector<VideoPortWrite> debug_ports;
    if (!update_scene_debug(ram,tables,d0,d1,d3,debug_ports,error)) return false;
    ports.insert(ports.end(),debug_ports.begin(),debug_ports.end());
    //The confirmed d418/d41c zero condition makes the native preparation loop run once.
    d0 = get(ram,0xd38e); d1 = get(ram,0xd392);
    if (!node(ram,0x43e22,0x10d38e,0,d0,d1,d3,error)) return false;
    for (unsigned int index = 0; index < 4; ++index) {
        d0 = get(ram,nodes[index]); d1 = get(ram,nodes[index] + 4);
        if (!node(ram,0x16fee,static_cast<std::uint32_t>(0x100000 + nodes[index]),0,d0,d1,d3,error)) return false;
    }
    //d41e>=d41c skips1a29e; d40e=0 selects1a414 null-script no-op.
    put_word(ram,0x10,0); port(ports,0x2ffff2,0x1000); port(ports,0x2ffff0,0); return true;
}
}
bool initialize_stage_scene(std::vector<std::uint8_t>& ram, const FixedDataResource& tables,
                            std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3,
                            std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536 || tables.source_cpu_address != 0x1af12 || tables.source_rom_offset != 0x1af12 || tables.data.size() != 512) {
        error = "stage scene null-script initializer requires64KiB RAM and512-byte1af12 window"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; std::uint32_t next0 = d0, next1 = d1, next3 = d3; std::vector<VideoPortWrite> output;
        if (!initialize(candidate,tables,next0,next1,next3,output,error)) return false;
        ram.swap(candidate); d0 = next0; d1 = next1; d3 = next3; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage scene initialization transaction"; return false; }
}

}
