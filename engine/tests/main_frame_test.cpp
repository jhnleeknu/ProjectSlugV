#include "ms5/main_frame.h"
#include <cassert>
#include <iostream>

namespace {
bool same_state(const ms5::MainFrameState& left,const ms5::MainFrameState& right) {
    return left.next_pc==right.next_pc && left.object_address==right.object_address &&
           left.d1==right.d1 && left.d3==right.d3;
}
}
int main() {
    ms5::FixedDataResource absent,debug,table;
    debug.source_cpu_address=debug.source_rom_offset=0xd56U;
    debug.data.assign(0xe40U-0xd56U,0);
    debug.data[0]='A';
    table.source_cpu_address=table.source_rom_offset=0xb58U;
    table.data.assign(256,0);
    const std::vector<ms5::PaletteRecord> records;
    const ms5::InputPortSamples ports={255,255,255,255,255};
    std::vector<std::uint8_t> ram(65536,0);
    ram[0xf000]=1;ram[0x184]=1;ram[0x17]=1;
    ms5::MainFrameState state;
    state.next_pc=0xec4U;state.object_address=0x100100U;
    state.d1=0x13570603U;state.d3=0x98767000U;
    ms5::InputFrameResult result;
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    // ec4 draws once, then parks at ef2 without touching input resources.
    assert(ms5::step_main_frame(ram,absent,absent,absent,absent,debug,records,ports,
                                0xffffU,1,state,result,writes,error));
    assert(state.next_pc==0xef2U && result.next_pc==state.next_pc && result.read_count==0);
    assert(state.d1==0x13570603U && state.d3==0x98767066U && !writes.empty());
    const std::vector<std::uint8_t> after_debug=ram;
    const ms5::MainFrameState waiting=state;
    // Invalid debug data proves that the waiting resume cannot draw again.
    assert(ms5::step_main_frame(ram,absent,absent,absent,absent,absent,records,ports,
                                0xffffU,1,state,result,writes,error));
    assert(ram==after_debug && same_state(state,waiting) && writes.empty());
    // Ready input stops at the callback boundary and keeps the full registers.
    ram[0x16]=1;ram[0x176]=1;
    assert(ms5::step_main_frame(ram,absent,table,absent,absent,absent,records,ports,
                                0xffffU,1,state,result,writes,error));
    assert(state.next_pc==0xf3cU && result.next_pc==state.next_pc && result.read_count==5);
    assert(state.d1==0x13570600U && state.d3==0x98767066U && writes.empty());
    assert(ram[0x16]==0 && ram[0x1a]==1 && ram[0x18]==255);
    // A ready failure after successful debug drawing rolls back every output.
    ram.assign(65536,0);ram[0xf000]=1;ram[0x184]=1;ram[0x16]=1;ram[0x17]=1;
    state.next_pc=0xec4U;state.object_address=0x100100U;
    state.d1=0x13570603U;state.d3=0x98767000U;
    const std::vector<std::uint8_t> before=ram;
    const ms5::MainFrameState before_state=state;
    result.next_pc=91;result.callback=92;result.callback_context=93;result.style=94;result.read_count=95;
    writes.resize(1);writes[0].address=123;writes[0].size=2;writes[0].value=456;
    assert(!ms5::step_main_frame(ram,absent,absent,absent,absent,debug,records,ports,
                                 0xffffU,1,state,result,writes,error));
    assert(ram==before && same_state(state,before_state) && !error.empty());
    assert(result.next_pc==91 && result.callback==92 && result.callback_context==93 &&
           result.style==94 && result.read_count==95);
    assert(writes.size()==1 && writes[0].address==123 && writes[0].size==2 && writes[0].value==456);
    std::cout << "Main frame debug-once, wait resume and transactional failure passed\n";
}
