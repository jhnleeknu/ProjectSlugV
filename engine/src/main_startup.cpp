#include "ms5/main_startup.h"
#include "ms5/palette_control.h"
#include <new>

namespace {
const std::size_t node_base = 0x4d92U;
const std::uint16_t free_sentinel = 0x1000U;
std::uint16_t word(const std::vector<std::uint8_t>& bytes,std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(bytes[at]) << 8) | bytes[at + 1]);
}
void put_word(std::vector<std::uint8_t>& bytes,std::size_t at,std::uint16_t value) {
    bytes[at] = static_cast<std::uint8_t>(value >> 8); bytes[at + 1] = static_cast<std::uint8_t>(value);
}
void put_long(std::vector<std::uint8_t>& bytes,std::size_t at,std::uint32_t value) {
    put_word(bytes,at,static_cast<std::uint16_t>(value >> 16));
    put_word(bytes,at + 2,static_cast<std::uint16_t>(value));
}
bool node(std::uint16_t value) { return value <= 0xff0U && (value & 15U) == 0; }
bool link(std::uint16_t value) {
    return node(value) || value == free_sentinel || (value <= 0xff4U && (value & 15U) == 4U);
}
bool ring(const std::vector<std::uint8_t>& ram,std::uint16_t sentinel,std::string& error) {
    std::uint16_t previous = sentinel;
    std::uint16_t current = word(ram,node_base + sentinel + 2);
    bool visited[256] = {};
    while (current != sentinel) {
        if (!node(current) || visited[current >> 4] || word(ram,node_base + current) != previous) {
            error = "corrupt startup palette ring"; return false;
        }
        visited[current >> 4] = true; previous = current;
        current = word(ram,node_base + current + 2);
    }
    if (word(ram,node_base + sentinel) != previous) {
        error = "corrupt startup palette sentinel tail"; return false;
    }
    return true;
}
bool unlink(std::vector<std::uint8_t>& ram,std::uint16_t current,std::string& error) {
    const std::uint16_t previous = word(ram,node_base + current);
    const std::uint16_t next = word(ram,node_base + current + 2);
    if (!link(previous) || !link(next) || previous == current || next == current ||
        word(ram,node_base + previous + 2) != current || word(ram,node_base + next) != current) {
        error = "corrupt startup palette node links"; return false;
    }
    put_word(ram,node_base + previous + 2,next); put_word(ram,node_base + next,previous);
    return true;
}
void watchdog(std::vector<ms5::VideoPortWrite>& ports,std::uint8_t value) {
    ms5::VideoPortWrite write;
    write.size = 1; write.address = 0x300001; write.value = value; ports.push_back(write);
}
bool bind_palettes(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& bindings,
                   std::uint32_t& d1, std::uint32_t& d3, std::string& error) {
    for (std::size_t record = 0; record + 2 < bindings.data.size(); record += 6) {
        const std::uint16_t offset = static_cast<std::uint16_t>(word(bindings.data,record) << 4);
        const std::uint16_t source = word(bindings.data,record + 2);
        d1 = (d1 & 0xffff0000U) | source;
        const std::uint16_t bucket = static_cast<std::uint16_t>((source & 255U) * 16U + 4U);
        const std::size_t at = node_base + offset;
        if (!ring(ram,bucket,error)) return false;
        if (word(ram,node_base + bucket + 2) != offset) {
            if (!unlink(ram,offset,error)) return false;
            const std::uint16_t old_head = word(ram,node_base + bucket + 2);
            d3 = (d3 & 0xffff0000U) | old_head;
            put_word(ram,node_base + old_head,offset);
            put_word(ram,at + 2,old_head); put_word(ram,at,bucket);
            put_word(ram,node_base + bucket + 2,offset);
        }
        put_word(ram,at + 8,0xffffU);
        put_word(ram,at + 10,source); put_word(ram,at + 12,source);
        ram[at + 15] = source == 0xffffU ? 2U : static_cast<std::uint8_t>(bindings.data[record + 4] | 128U);
    }
    return true;
}
}
namespace ms5 {
bool initialize_main_palettes(std::vector<std::uint8_t>& ram,
                           const FixedDataResource& bindings,std::uint32_t& d0,
                           std::uint32_t& d1,std::uint32_t& d3,
                           std::vector<VideoPortWrite>& ports,std::string& error) {
    if (ram.size() != 65536U) {
        error = "main palettes require 64KiB RAM"; return false;
    }
    if (bindings.source_cpu_address != 0xe7b58U || bindings.source_rom_offset != 0xe7b58U ||
        bindings.data.size() != 104U || word(bindings.data,102) != 0xffffU) {
        error = "main startup requires the exact e7b58 binding window"; return false;
    }
    for (std::size_t at = 0; at < 102; at += 6) {
        if (word(bindings.data,at) > 255U) { error = "startup palette slot must be a byte"; return false; }
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> output;
        std::uint32_t next_d3 = d3;
        watchdog(output,static_cast<std::uint8_t>(d0));
        for (unsigned int slot = 0; slot < 256; ++slot) {
            const std::uint16_t offset = static_cast<std::uint16_t>(slot << 4);
            const std::size_t at = node_base + offset;
            if (word(candidate,at + 8) != 0xffffU) continue;
            put_word(candidate,at + 8,0);
            if (!unlink(candidate,offset,error) || !ring(candidate,free_sentinel,error)) return false;
            const std::uint16_t old_tail = word(candidate,node_base + free_sentinel);
            next_d3 = (next_d3 & 0xffff0000U) | old_tail;
            put_word(candidate,at,old_tail); put_word(candidate,at + 2,free_sentinel);
            put_word(candidate,node_base + old_tail + 2,offset);
            put_word(candidate,node_base + free_sentinel,offset);
            put_word(candidate,at + 10,0xffffU); put_word(candidate,at + 12,0xffffU);
            candidate[at + 15] = 2;
        }
        watchdog(output,0);
        std::uint32_t binding_d1 = d1;
        if (!bind_palettes(candidate,bindings,binding_d1,next_d3,error)) return false;
        if (!set_palette_blend(candidate,6,1,12,error)) return false;
        ram.swap(candidate); ports.swap(output);
        d0 = 0x60U; d1 = (d1 & 0xffff0000U) | 1U; d3 = next_d3;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate main startup state"; return false;
    }
    error.clear(); return true;
}
bool initialize_stage_palettes(std::vector<std::uint8_t>& ram,
                               const FixedDataResource& main_bindings, const FixedDataResource& stage_bindings,
                               std::uint32_t& d0, std::uint32_t& d1, std::uint32_t& d3,
                               std::vector<VideoPortWrite>& ports, std::string& error) {
    try {
        std::vector<std::uint8_t> candidate = ram; std::vector<VideoPortWrite> output;
        std::uint32_t next_d0 = d0, next_d1 = d1, next_d3 = d3;
        if (!initialize_main_palettes(candidate,main_bindings,next_d0,next_d1,next_d3,output,error)) return false;
        if (stage_bindings.source_cpu_address != 0xe7bda || stage_bindings.source_rom_offset != 0xe7bda ||
            stage_bindings.data.size() != 26 || word(stage_bindings.data,24) != 0xffff) {
            error = "stage palettes require the exact e7bda binding window"; return false;
        }
        for (std::size_t at = 0; at < 24; at += 6) {
            if (word(stage_bindings.data,at) > 255) { error = "stage palette slot must be a byte"; return false; }
        }
        watchdog(output,static_cast<std::uint8_t>(next_d0));
        if (!bind_palettes(candidate,stage_bindings,next_d1,next_d3,error)) return false;
        ram.swap(candidate); ports.swap(output); d0 = 0xffff; d1 = next_d1; d3 = next_d3;
        error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage palette transaction"; return false; }
}
bool initialize_main_frame(std::vector<std::uint8_t>& ram,std::size_t object,
                           const FixedDataResource& bindings,std::uint32_t& d0,
                           std::uint32_t& d1,std::uint32_t& d3,
                           std::vector<VideoPortWrite>& ports,std::string& error) {
    if (ram.size() != 65536U || object > 65536U - 0x85U || (object & 1U) != 0) {
        error = "main startup requires 64KiB RAM and an even complete object offset"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> output;
        std::uint32_t next_d0 = d0, next_d1 = d1, next_d3 = d3;
        if (!initialize_main_palettes(candidate,bindings,next_d0,next_d1,next_d3,output,error)) return false;
        put_word(candidate,0x0e,0); put_word(candidate,object + 0x7e,0);
        candidate[object + 0x84] = 1; put_long(candidate,object + 0x76,0);
        candidate[0x7def] = 255; candidate[0x7dee] = 0; candidate[0x7df0] = 0; candidate[0x7df1] = 0;
        candidate[0x7dfe] = 0;
        for (std::size_t at = 0x7dff; at <= 0x7e06; ++at) candidate[at] = 0;
        put_long(candidate,object,0xe74U);
        ram.swap(candidate); ports.swap(output); d0 = 0; d1 = next_d1; d3 = next_d3;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate main startup state"; return false;
    }
    error.clear(); return true;
}

}
