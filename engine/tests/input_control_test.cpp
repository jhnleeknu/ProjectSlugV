#include "ms5/input_control.h"
#include <cassert>
#include <iostream>
int main() {
    ms5::FixedDataResource absent,table;
    table.source_cpu_address=table.source_rom_offset=0xb58;table.data.assign(256,0);
    const std::vector<ms5::PaletteRecord> records;
    ms5::InputPortSamples ports={255,255,255,255,255};
    std::vector<std::uint8_t> ram(65536,0);
    ram[0x7df1]=1;ram[0x184]=1;ram[0x4d90]=255;ram[0x4d91]=0xf7;
    ram[0x16]=7;ram[0x4ca2]=5;
    const std::vector<std::uint8_t> before=ram;
    ms5::InputFrameResult result;result.next_pc=91;result.style=92;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=123;
    std::string error;
    std::uint32_t d1=0x1357abcdU,d3=0x98767000U;
    assert(!ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0xabcd,0x7000,0x1feffc,result,writes,error,NULL,NULL,&d1,&d3));
    assert(d1==0x1357abcdU && d3==0x98767000U);
    assert(ram==before && result.next_pc==91 && result.style==92 && writes.size()==1 && writes[0].address==123);
    ram[0x7ded]=128;
    assert(ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0xabcd,0x7000,0x1feffc,result,writes,error));
    assert(result.next_pc==0xec4 && result.style==0xab00 && result.read_count==5);
    assert(ram[0x1a]==7 && ram[0x16]==0 && ram[0x4ca2]==0 && ram[0x7df0]==1 && writes.size()==257);
    ram[0xf002]=1;ports.system=254;
    assert(ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0,0x7000,0x1feffc,result,writes,error));
    assert(result.next_pc==0 && ram[0x184]==2 && ram[0x0f]==1 && writes.size()==1);
    // A callback boundary bypasses all controller resources and stack checks.
    ram.assign(65536,0);ram[0x176]=0x12;ram[0x17d]=0xab;
    assert(ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0,0,1,result,writes,error));
    assert(result.next_pc==0xf3c && result.callback==0x12000000 && result.callback_context==0xab && writes.empty());
    // Full registers survive the input prefix across the callback boundary.
    ram.assign(65536,0);ram[0x176]=1;
    d1=0x1357abcdU;d3=0x98767000U;
    const std::vector<std::uint8_t> callback_register_before=ram;
    const ms5::InputFrameResult callback_register_result=result;
    assert(!ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0xabce,0x7000,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(!ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0xabcd,0x7001,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(ram==callback_register_before && d1==0x1357abcdU && d3==0x98767000U && writes.empty());
    assert(result.next_pc==callback_register_result.next_pc && result.style==callback_register_result.style);
    assert(ms5::step_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0xabcd,0x7000,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(result.next_pc==0xf3c && result.style==0xab00 && d1==0x1357ab00U && d3==0x98767000U);
    // Waiting bypasses resources/object/stack and clears stale output events.
    ram.assign(65536,0);ram[0x17]=2;ram[0x18]=91;
    const std::vector<std::uint8_t> waiting=ram;
    d1=0x13574567U;d3=0x98760000U;
    assert(ms5::poll_input_control(ram,absent,absent,absent,absent,records,ports,
        0xffff,0,0x4567,0,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(d1==0x13574567U && d3==0x98760000U);
    assert(ram==waiting && result.next_pc==0xef2 && result.style==0x4567 &&
           result.read_count==0 && result.callback==0 && writes.empty());
    const ms5::InputFrameResult waiting_result=result;
    writes.resize(1);writes[0].address=123;
    assert(!ms5::poll_input_control(ram,absent,absent,absent,absent,records,ports,
        0xffff,0,0x4568,0,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(!ms5::poll_input_control(ram,absent,absent,absent,absent,records,ports,
        0xffff,0,0x4567,1,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(ram==waiting && d1==0x13574567U && d3==0x98760000U);
    assert(result.next_pc==waiting_result.next_pc && result.style==waiting_result.style &&
           writes.size()==1 && writes[0].address==123);
    ram[0x16]=2;
    const std::vector<std::uint8_t> gate_before=ram;
    assert(!ms5::poll_input_control(ram,absent,absent,absent,absent,records,ports,
        0xffff,0x100100,0,0,0x1feffc,result,writes,error));
    assert(ram==gate_before && result.next_pc==0xef2);
    // Successful ready callback path commits video18 then input frame latch.
    ram[0x176]=1;
    assert(ms5::poll_input_control(ram,absent,table,absent,absent,records,ports,
        0xffff,0x100100,0,0,1,result,writes,error));
    assert(result.next_pc==0xf3c && ram[0x18]==255 && ram[0x1a]==2 && ram[0x16]==0);
    // Callback wait requires one signal even when threshold is zero.
    ram.assign(65536,0);ram[0x18]=91;
    const std::vector<std::uint8_t> callback_wait=ram;
    d1=0x1357beefU;d3=0x98760000U;
    assert(ms5::poll_callback_input_control(ram,absent,absent,absent,absent,records,ports,
        0,0xbeef,0,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(d1==0x1357beefU && d3==0x98760000U);
    assert(ram==callback_wait && result.next_pc==0xf4c && result.style==0xbeef &&
        result.read_count==0 && result.callback==0 && writes.empty());
    assert(!ms5::poll_callback_input_control(ram,absent,absent,absent,absent,records,ports,
        0,0xbeee,0,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(!ms5::poll_callback_input_control(ram,absent,absent,absent,absent,records,ports,
        0,0xbeef,1,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(ram==callback_wait && d1==0x1357beefU && d3==0x98760000U && writes.empty());
    assert(result.next_pc==0xf4c && result.style==0xbeef && result.read_count==0);
    // One signal suffices even below threshold255; RAM18 stays untouched.
    ram[0x16]=1;ram[0x17]=255;ram[0x176]=1;
    assert(ms5::poll_callback_input_control(ram,absent,table,absent,absent,records,ports,
        0x100100,0xbeef,0,1,result,writes,error));
    assert(result.next_pc==0xf3c && ram[0x18]==91 && ram[0x1a]==1 && ram[0x16]==0);
    ram[0x16]=1;const std::vector<std::uint8_t> callback_before=ram;
    const ms5::InputFrameResult old_result=result;
    writes.resize(1);writes[0].address=123;
    assert(!ms5::poll_callback_input_control(ram,absent,absent,absent,absent,records,ports,
        0x100100,0xbeef,0,1,result,writes,error,NULL,NULL,&d1,&d3));
    assert(d1==0x1357beefU && d3==0x98760000U);
    assert(ram==callback_before && result.next_pc==old_result.next_pc &&
        result.style==old_result.style && writes.size()==1 && writes[0].address==123);
    std::cout<<"Input/controller activation, resume, callback bypass and late rollback passed\n";
}
