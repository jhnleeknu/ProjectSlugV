#include "ms5/scene_placement_resource.h"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
namespace { bool fail_next_allocation = false; }
void* operator new(std::size_t size) {
    if (fail_next_allocation) { fail_next_allocation = false; throw std::bad_alloc(); }
    void* pointer = std::malloc(size == 0 ? 1 : size); if (pointer == NULL) throw std::bad_alloc(); return pointer;
}
void operator delete(void* pointer) noexcept { std::free(pointer); }
namespace {
void append(std::vector<std::uint8_t>& bytes, unsigned int size, std::uint32_t value) {
    for (unsigned int i = 0; i < size; ++i) bytes.push_back(static_cast<std::uint8_t>(value >> (8*(size-i-1))));
}
ms5::FixedDataResource fixture() {
    ms5::FixedDataResource source; source.source_cpu_address = source.source_rom_offset = 0x60000;
    append(source.data,2,0x8000); append(source.data,2,2); append(source.data,2,0xffff); append(source.data,2,0x8000);
    append(source.data,4,0x12345679); append(source.data,4,0xffffffff); append(source.data,2,0xffff);
    append(source.data,2,0xfffe); append(source.data,2,0); append(source.data,2,0x7fff); append(source.data,2,0);
    append(source.data,4,0); append(source.data,4,0x00477e4); append(source.data,2,0xffff); return source;
}
bool same(const ms5::ScenePlacementResource& a, const ms5::ScenePlacementResource& b) {
    if (a.source.source_cpu_address != b.source.source_cpu_address || a.source.source_rom_offset != b.source.source_rom_offset ||
        a.source.data != b.source.data || a.terminal_cpu_address != b.terminal_cpu_address || a.terminal_rom_offset != b.terminal_rom_offset || a.records.size() != b.records.size()) return false;
    for (std::size_t i = 0; i < a.records.size(); ++i) {
        const ms5::ScenePlacementRecord& x = a.records[i]; const ms5::ScenePlacementRecord& y = b.records[i];
        if (x.source_cpu_address != y.source_cpu_address || x.source_rom_offset != y.source_rom_offset || x.next_cpu_address != y.next_cpu_address ||
            x.next_rom_offset != y.next_rom_offset || x.gate != y.gate || x.inline_byte_count != y.inline_byte_count || x.x != y.x || x.y != y.y ||
            x.bounds_pointer != y.bounds_pointer || x.callback != y.callback || x.inline_data != y.inline_data) return false;
    }
    return true;
}
}
int main() {
    ms5::FixedDataResource source = fixture(); ms5::ScenePlacementResource resource; std::string error;
    assert(ms5::decode_scene_placement(source,resource,error)); assert(resource.records.size() == 2);
    const ms5::ScenePlacementRecord& first = resource.records[0]; const ms5::ScenePlacementRecord& second = resource.records[1];
    assert(first.gate == 0x8000 && first.x == 0xffff && first.y == 0x8000 && first.inline_byte_count == 2 && first.inline_data.size() == 2);
    assert(first.bounds_pointer == 0x12345679 && first.callback == 0xffffffff && first.inline_data[0] == 255 && first.inline_data[1] == 255);
    assert(first.source_cpu_address == 0x60000 && first.source_rom_offset == 0x60000 && first.next_cpu_address == 0x60012 && first.next_rom_offset == 0x60012);
    assert(second.gate == 0xfffe && second.inline_data.empty() && second.source_cpu_address == 0x60012 && second.next_cpu_address == 0x60022);
    assert(resource.terminal_cpu_address == 0x60022 && resource.terminal_rom_offset == 0x60022);
    // Every raw field, including inaccessible pointer values and inlineffff, round-trips exactly.
    std::vector<std::uint8_t> reconstructed;
    for (std::size_t i = 0; i < resource.records.size(); ++i) {
        const ms5::ScenePlacementRecord& record = resource.records[i];
        append(reconstructed,2,record.gate); append(reconstructed,2,record.inline_byte_count); append(reconstructed,2,record.x); append(reconstructed,2,record.y);
        append(reconstructed,4,record.bounds_pointer); append(reconstructed,4,record.callback);
        reconstructed.insert(reconstructed.end(),record.inline_data.begin(),record.inline_data.end());
    }
    append(reconstructed,2,0xffff); assert(reconstructed == source.data);
    const ms5::ScenePlacementResource saved = resource;
    for (unsigned int mutation = 0; mutation < 12; ++mutation) {
        ms5::FixedDataResource bad = source;
        if (mutation == 0) bad.source_cpu_address |= 1;
        if (mutation == 1) ++bad.source_rom_offset;
        if (mutation == 2) bad.source_cpu_address = bad.source_rom_offset = 0x100000;
        if (mutation == 3) bad.source_cpu_address = bad.source_rom_offset = 0xffff0;
        if (mutation == 4) bad.data.clear();
        if (mutation == 5) bad.data.resize(1);
        if (mutation == 6) bad.data.resize(15);
        if (mutation == 7) bad.data[3] = 1;
        if (mutation == 8) { bad.data[2] = 0x80; bad.data[3] = 0; }
        if (mutation == 9) bad.data.resize(17);
        if (mutation == 10) bad.data.resize(bad.data.size()-2);
        if (mutation == 11) bad.data.push_back(0);
        assert(!ms5::decode_scene_placement(bad,resource,error)); assert(!error.empty() && same(resource,saved));
    }
    // Only exactffff is terminal, and a two-byte empty stream may end at the fixed-ROM limit.
    ms5::FixedDataResource empty; empty.source_cpu_address = empty.source_rom_offset = 0xffffe; append(empty.data,2,0xffff);
    assert(ms5::decode_scene_placement(empty,resource,error)); assert(resource.records.empty() && resource.terminal_cpu_address == 0xffffe);
    // Allocation errors during candidate creation preserve the complete previously decoded output.
    resource = saved; fail_next_allocation = true;
    assert(!ms5::decode_scene_placement(source,resource,error)); assert(!fail_next_allocation && same(resource,saved));
    assert(!ms5::load_scene_placement("/nonexistent/scene-placement.ms5d",resource,error)); assert(same(resource,saved));
    std::cout << "scene placement resource tests passed\n";
}
