#include "ms5/scene_setup.h"
#include "ms5/sprite_producer.h"
#include "ms5/sprite_pool.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t word(const std::vector<std::uint8_t>& data, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(data[at]) << 8) | data[at + 1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& data, std::size_t at) {
    return (static_cast<std::uint32_t>(word(data,at)) << 16) | word(data,at + 2);
}
std::uint32_t sign_word(std::uint16_t value) { return value < 0x8000 ? value : 0xffff0000U | value; }
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
void emit(std::vector<VideoPortWrite>& ports, std::uint8_t size, std::uint32_t address, std::uint32_t value) {
    VideoPortWrite write; write.size = size; write.address = address; write.value = value; ports.push_back(write);
}
bool slot_setup(std::vector<std::uint8_t>& ram, SceneCommandState& state,
    std::vector<VideoPortWrite>& ports, std::string& error) {
    if ((state.a0 & 1U) || state.a0 < 0x100000 || state.a0 > 0x110000 - 0x7b) {
        error = "scene slot setup requires an aligned complete node"; return false;
    }
    const std::size_t node = state.a0 - 0x100000;
    const std::uint16_t slot = static_cast<std::uint16_t>(state.d0);
    put_word(ram,node + 0x26,slot); state.d7 = (state.d7 & 0xffff0000U) | slot;
    if ((slot & 0x8000U) == 0) {
        state.a1 = 0x3c0000; state.d6 = (state.d6 & 0xffff0000U) | 0x3ffU;
        state.d7 = (state.d7 & 0xffff0000U) | static_cast<std::uint16_t>((slot + 1U) << 6);
        state.d7 = (state.d7 << 16) | (state.d7 >> 16); state.d7 &= 0xffff0000U;
        for (unsigned int i = 0; i < 1024; ++i) {
            emit(ports,4,0x3c0000,state.d7); state.d7 += 0x10000U;
            emit(ports,4,0x3c0000,state.d7); state.d7 += 0x10000U;
            state.d6 = (state.d6 & 0xffff0000U) | static_cast<std::uint16_t>(state.d6 - 1U);
        }
        emit(ports,1,0x300001,state.d0 & 255U);
    }
    ram[node + 0x7a] &= 0xfe; state.d7 = (state.d7 & 0xffff0000U) | slot;
    if ((slot & 0x8000U) == 0) {
        emit(ports,1,0x300001,state.d0 & 255U);
        state.d6 = (state.d6 & 0xffff0000U) | static_cast<std::uint16_t>(slot + 0x8001U);
        state.d7 = (state.d7 & 0xffff0000U) | static_cast<std::uint16_t>(slot + 0x8201U);
        state.d6 = (state.d6 << 16) | (state.d6 >> 16); state.d7 = (state.d7 << 16) | (state.d7 >> 16);
        state.d6 = (state.d6 & 0xffff0000U) | 0xfffU; state.d7 = (state.d7 & 0xffff0000U) | 0x8000U; state.d5 = 0x10000;
        for (unsigned int i = 0; i < 32; ++i) {
            emit(ports,4,0x3c0000,state.d7); state.d7 += 0x10000U;
            emit(ports,4,0x3c0000,state.d6); state.d6 += 0x10000U;
        }
    }
    state.d0 = 0;
    for (std::size_t i = node + 0x3a; i < node + 0x7a; ++i) ram[i] = 0;
    state.a1 = state.a0 + 0x7a; return true;
}
bool reset_setup(std::vector<std::uint8_t>& ram, SceneCommandState& state,
    std::vector<VideoPortWrite>& ports, std::string& error) {
    if (!initialize_sprite_queue(ram,error)) return false;
    state.d0 = 1; state.d1 = 0xffffffff; state.d2 = 0xffffffff;
    state.d7 = (state.d7 & 0xffff0000U) | 0xffff; state.a0 = 0x108d34; state.a4 = 0x108d46;
    put_word(ram,0x10,1); emit(ports,2,0x2ffff2,0x2000); emit(ports,2,0x2ffff0,0);
    const std::uint32_t nodes[4] = {0x109156,0x10b1d6,0x10d256,0x10d2d6};
    for (unsigned int i = 0; i < 4; ++i) {
        state.a0 = nodes[i]; state.d0 = 0xffffffff;
        if (!slot_setup(ram,state,ports,error)) return false;
    }
    put_word(ram,0x10,0); emit(ports,2,0x2ffff2,0x1000); emit(ports,2,0x2ffff0,0);
    state.a4 = 0x3c0000; state.d7 = 0x82010000; state.d6 = 0x8401f000;
    state.d5 = 0x8001ffff; state.d4 = 0x10000; state.d0 = (state.d0 & 0xffff0000U) | 0x17b;
    for (unsigned int i = 0; i < 380; ++i) {
        emit(ports,4,0x3c0000,state.d7); state.d7 += 0x10000;
        emit(ports,1,0x300001,state.d0 & 255U);
        emit(ports,4,0x3c0000,state.d6); state.d6 += 0x10000;
        emit(ports,1,0x300001,state.d0 & 255U);
        emit(ports,4,0x3c0000,state.d5); state.d5 += 0x10000;
        emit(ports,1,0x300001,state.d0 & 255U);
        state.d0 = (state.d0 & 0xffff0000U) | static_cast<std::uint16_t>(state.d0 - 1U);
    }
    put_word(ram,0xd496,0); put_word(ram,0xd498,0x17c); return true;
}

bool allocate_slots(std::vector<std::uint8_t>& ram, SceneCommandState& state, std::string& error) {
    if (ram[0xd49a] == 0) {
        state.d1 = (state.d1 & 0xffff0000U) | word(ram,0xd496);
        state.d3 = (state.d3 & 0xffff0000U) | word(ram,0xd498);
        state.d2 = (state.d2 & 0xffff0000U) | static_cast<std::uint16_t>(state.d1 + state.d0);
        if (static_cast<std::uint16_t>(state.d2) >= static_cast<std::uint16_t>(state.d3)) state.d2 = (state.d2 & 0xffff0000U) | static_cast<std::uint16_t>(state.d3);
        put_word(ram,0xd496,static_cast<std::uint16_t>(state.d2));
        state.d0 = (state.d0 & 0xffff0000U) | static_cast<std::uint16_t>(state.d0 - state.d2 + state.d1);
    } else {
        state.d2 = (state.d2 & 0xffff0000U) | word(ram,0xd498);
        state.d3 = (state.d3 & 0xffff0000U) | word(ram,0xd496);
        state.d1 = (state.d1 & 0xffff0000U) | static_cast<std::uint16_t>(state.d2 - state.d0);
        if (static_cast<std::uint16_t>(state.d1) < static_cast<std::uint16_t>(state.d3)) state.d1 = (state.d1 & 0xffff0000U) | static_cast<std::uint16_t>(state.d3);
        put_word(ram,0xd498,static_cast<std::uint16_t>(state.d1));
        state.d0 = (state.d0 & 0xffff0000U) | static_cast<std::uint16_t>(state.d0 - state.d2 + state.d1);
    }
    if (static_cast<std::uint16_t>(state.d0) != 0) { error = "scene allocation exceeds remaining slots"; return false; }
    return true;
}
bool pool_setup(std::vector<std::uint8_t>& ram, SceneCommandState& state, std::string& error) {
    const std::uint16_t selector = static_cast<std::uint16_t>(state.d0);
    const std::uint16_t lower = static_cast<std::uint16_t>(state.d1), upper = static_cast<std::uint16_t>(state.d2);
    if (!configure_sprite_pool(ram,selector,lower,upper,error)) return false;
    if (lower >= 380) state.d1 = 0xffffffff;
    if (static_cast<std::uint16_t>(state.d1) >= static_cast<std::uint16_t>(state.d2)) state.d2 = 0xffffffff;
    state.d1 = (state.d1 << 16) | (state.d1 >> 16);
    state.d1 = (state.d1 & 0xffff0000U) | static_cast<std::uint16_t>(state.d2);
    state.a4 = selector == 0 ? 0x108d3e : 0x108d46; return true;
}

bool read_record(const FixedDataResource& descriptor, std::uint32_t address,
    std::size_t& offset, std::uint16_t& type, std::uint32_t& next, std::string& error) {
    if ((address & 1U) || address < descriptor.source_cpu_address || address - descriptor.source_cpu_address > descriptor.data.size() ||
        descriptor.data.size() - (address - descriptor.source_cpu_address) < 4) { error = "scene descriptor record outside window"; return false; }
    offset = address - descriptor.source_cpu_address; type = word(descriptor.data,offset + 2);
    if (type > 3 || (type == 1 && descriptor.data.size() - offset < 6) || (type == 2 && descriptor.data.size() - offset < 8)) { error = "invalid scene descriptor record type or span"; return false; }
    const std::uint16_t stride = word(descriptor.data,offset);
    const std::int64_t destination = static_cast<std::int64_t>(address) + (stride < 0x8000 ? stride : static_cast<std::int32_t>(stride) - 65536);
    if (type != 3 && ((stride & 1U) || stride >= 0x8000 || stride < (type == 1 ? 6 : type == 2 ? 8 : 4) || destination < 0 || destination > 0xffffffffLL)) { error = "invalid scene descriptor stride"; return false; }
    next = static_cast<std::uint32_t>(destination);
    if (type == 3 && offset + 4 != descriptor.data.size()) { error = "scene descriptor terminal must end window"; return false; }
    return true;
}
bool process_record(std::vector<std::uint8_t>& ram, const FixedDataResource& descriptor,
    SceneCommandState& state, std::vector<VideoPortWrite>& ports, std::string& error) {
    std::size_t at = 0; std::uint16_t type = 0; std::uint32_t next = 0;
    if (!read_record(descriptor,state.a0,at,type,next,error) || (type != 1 && type != 2)) return false;
    state.d0 = sign_word(word(descriptor.data,at)); state.d1 = sign_word(type);
    if (type == 1) {
        state.d0 = (state.d0 & 0xffff0000U) | word(descriptor.data,at + 4);
        if (!allocate_slots(ram,state,error)) return false;
        state.d0 = 1;
        if (!pool_setup(ram,state,error)) return false;
    } else {
        state.d0 = (state.d0 & 0xffff0000U) | 0x20;
        if (!allocate_slots(ram,state,error)) return false;
        state.d0 = (state.d0 & 0xffff0000U) | static_cast<std::uint16_t>(state.d1);
        state.a0 = longword(descriptor.data,at + 4);
        if (!slot_setup(ram,state,ports,error)) return false;
    }
    state.a0 = next; return true;
}

}
bool setup_scene_resources(std::vector<std::uint8_t>& ram, const FixedDataResource* descriptor,
    SceneCommandState& state, std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size() != 65536) { error = "scene setup requires exactly64KiB RAM"; return false; }
    if (state.a0 != 0 && (descriptor == NULL || descriptor->source_cpu_address != state.a0 || descriptor->source_rom_offset != state.a0 ||
        (state.a0 & 1U) || state.a0 >= 0x100000 || descriptor->data.size() < 4 || descriptor->data.size() > 65536 || descriptor->data.size() > 0x100000 - state.a0)) {
        error = "scene setup requires exact fixed descriptor window"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram; SceneCommandState next = state; std::vector<VideoPortWrite> output;
        const std::uint32_t original_a0 = next.a0;
        if (!reset_setup(candidate,next,output,error)) return false;
        next.a0 = original_a0;
        if (next.a0 != 0) {
            unsigned int budget = 65536; bool suffix = false;
            while (true) {
                if (budget-- == 0) { error = "scene descriptor traversal exceeds operation budget"; return false; }
                candidate[0xd49a] = 255;
                std::size_t at = 0; std::uint16_t type = 0; std::uint32_t after = 0;
                if (!read_record(*descriptor,next.a0,at,type,after,error)) return false;
                next.d0 = (next.d0 & 0xffff0000U) | type;
                if (type == 3) break;
                if (type == 0) { next.a0 = after; next.d7 = 0; candidate[0xd49a] = 0; suffix = true; break; }
                if (!process_record(candidate,*descriptor,next,output,error)) return false;
            }
            if (suffix) {
                std::vector<std::uint32_t> records;
                while (true) {
                    if (budget-- == 0) { error = "scene descriptor traversal exceeds operation budget"; return false; }
                    std::size_t at = 0; std::uint16_t type = 0; std::uint32_t after = 0;
                    if (!read_record(*descriptor,next.a0,at,type,after,error)) return false;
                    next.d0 = sign_word(word(descriptor->data,at)); next.d1 = sign_word(type);
                    if (type == 3) break;
                    if (type == 0) { error = "invalid suffix scene descriptor type"; return false; }
                    records.push_back(next.a0); next.d7 = (next.d7 & 0xffff0000U) | static_cast<std::uint16_t>(next.d7 + 1U); next.a0 = after;
                }
                while (!records.empty()) {
                    next.a0 = records.back(); records.pop_back();
                    next.d7 = (next.d7 & 0xffff0000U) | static_cast<std::uint16_t>(next.d7 - 1U);
                    const std::uint16_t count = static_cast<std::uint16_t>(next.d7);
                    if (!process_record(candidate,*descriptor,next,output,error)) return false;
                    next.d7 = (next.d7 & 0xffff0000U) | count;
                }
            }
        }
        next.d1 = (next.d1 & 0xffff0000U) | word(candidate,0xd496); next.d2 = (next.d2 & 0xffff0000U) | word(candidate,0xd498);
        put_word(candidate,0xd496,static_cast<std::uint16_t>(next.d2));
        next.d0 = (next.d0 & 0xffff0000U) | static_cast<std::uint16_t>(next.d2 - next.d1);
        next.d0 &= 0xffff0000U;
        if (!pool_setup(candidate,next,error)) return false;
        ram.swap(candidate); state = next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate scene setup transaction"; return false; }
}

}
