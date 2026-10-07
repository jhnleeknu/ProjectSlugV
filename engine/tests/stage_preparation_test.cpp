#include "ms5/stage_preparation.h"
#include "ms5/palette_state.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value, unsigned int size = 2) {
    for (unsigned int i = 0; i < size; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, std::size_t at, unsigned int size = 2) {
    std::uint32_t value = 0;
    for (unsigned int i = 0; i < size; ++i) value = (value << 8) | ram[at + i];
    return value;
}
ms5::FixedDataResource table(bool stage) {
    ms5::FixedDataResource resource;
    resource.source_cpu_address = resource.source_rom_offset = stage ? 0xe7bda : 0xe7b58;
    const unsigned int records = stage ? 4 : 17;
    resource.data.assign(records*6 + 2,0);
    for (unsigned int i = 0; i < records; ++i) {
        put(resource.data,i*6,(stage ? 17 : 0) + i); put(resource.data,i*6 + 2,stage ? 8 : 7);
        resource.data[i*6 + 4] = 2;
    }
    put(resource.data,records*6,0xffff); return resource;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0); std::string error;
    assert(ms5::initialize_palette_state(&ram[0],ram.size(),error));
    const std::size_t objects[2] = {0xb30,0xbf4};
    for (unsigned int i = 0; i < 2; ++i) {
        const std::size_t at = objects[i];
        put(ram,at + 4,0x100000 + at,4); put(ram,at + 8,0x100000 + at,4);
        ram[at + 0x6c] = 255;
    }
    ram[0x7dec] = 128; ram[0x4d91] = 255; return ram;
}
ms5::StagePreparationState initial() {
    ms5::StagePreparationState state; state.d0 = 0x123456ab; state.d1 = 0xabcd1234; state.d3 = 0x98761234; return state;
}
bool same(const ms5::StagePreparationState& a, const ms5::StagePreparationState& b) {
    return a.d0 == b.d0 && a.d1 == b.d1 && a.d3 == b.d3 && a.a6 == b.a6;
}
}
int main() {
    const ms5::FixedDataResource main_bindings = table(false); ms5::FixedDataResource stage_bindings = table(true);
    std::vector<std::uint8_t> ram = fixture(); ms5::StagePreparationState state = initial();
    std::vector<ms5::VideoPortWrite> ports; std::string error;
    ram[0x4d92 + 20*16 + 14] = 29;
    assert(ms5::initialize_stage_palettes(ram,main_bindings,stage_bindings,state.d0,state.d1,state.d3,ports,error));
    assert(state.d0 == 0xffff && state.d1 == 0xabcd0008 && state.d3 == 0x98760130);
    assert(ports.size() == 3 && ports[0].value == 0xab && ports[1].value == 0 && ports[2].value == 0x60);
    assert(get(ram,0x4d92 + 8*16 + 6) == 20*16);
    assert(ram[0x4d92 + 20*16 + 14] == 29 && get(ram,0x4d92 + 6*16 + 12) == 1);
    put(stage_bindings.data,20,0xffff); // Last sourceffff keeps IDsffff/flags2.
    ram = fixture(); state = initial();
    assert(ms5::initialize_stage_palettes(ram,main_bindings,stage_bindings,state.d0,state.d1,state.d3,ports,error));
    assert(state.d1 == 0xabcdffff && get(ram,0x4d92 + 20*16 + 10) == 0xffff && ram[0x4d92 + 20*16 + 15] == 2);
    stage_bindings = table(true);
    ram = fixture(); state = initial();
    assert(ms5::clear_stage_objects(ram,state,ports,error));
    assert(state.d0 == 0 && state.d1 == 0xffffffff && state.d3 == 0x98761234 && state.a6 == 0x100b30);
    assert(ports.size() == 1 && ports[0].value == 0);
    assert(ram[0x7dec] == 0 && ram[0x4d91] == 0xef && get(ram,6,4) == 0x3dcc && get(ram,10,4) == 0x3dcc);
    ram = fixture(); state = initial();
    assert(ms5::prepare_stage_body(ram,main_bindings,stage_bindings,state,ports,error));
    assert(state.d0 == 0 && state.d1 == 0xffffffff && state.d3 == 0x98760130 && state.a6 == 0x100b30);
    assert(ports.size() == 4 && ports[0].value == 0xab && ports[2].value == 0x60 && ports[3].value == 0);
    // A late object pointer error must discard all earlier palette/list writes.
    ram = fixture(); put(ram,0xbfc,0x100001,4); state = initial();
    ms5::VideoPortWrite marker = {123,456,2}; ports.assign(1,marker);
    const std::vector<std::uint8_t> before = ram; const ms5::StagePreparationState old = state;
    assert(!ms5::prepare_stage_body(ram,main_bindings,stage_bindings,state,ports,error));
    assert(ram == before && same(state,old) && ports.size() == 1 && ports[0].value == 456);
    ram = fixture(); state = initial(); stage_bindings.data[25] = 0;
    const std::vector<std::uint8_t> valid_ram = ram;
    assert(!ms5::prepare_stage_body(ram,main_bindings,stage_bindings,state,ports,error));
    assert(ram == valid_ram && same(state,old) && ports[0].value == 456);
    stage_bindings = table(true); put(stage_bindings.data,0,256);
    assert(!ms5::initialize_stage_palettes(ram,main_bindings,stage_bindings,state.d0,state.d1,state.d3,ports,error));
    assert(ram == valid_ram && same(state,old) && ports[0].value == 456);
    state.a6 |= 1; const ms5::StagePreparationState odd = state;
    assert(!ms5::clear_stage_objects(ram,state,ports,error));
    assert(ram == valid_ram && same(state,odd) && ports[0].value == 456);
    std::cout << "stage_preparation_test: passed\n";
}
