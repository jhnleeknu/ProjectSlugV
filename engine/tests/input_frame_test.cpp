#include "ms5/input_frame.h"
#include <cassert>
#include <iostream>
int main() {
    ms5::FixedDataResource table,streams,absent;
    table.source_cpu_address=table.source_rom_offset=0xb58;
    table.data.assign(256,0);
    streams.source_cpu_address=streams.source_rom_offset=0xf01fe;
    streams.data.assign(0x1810,1);
    std::vector<std::uint8_t> ram(65536,0);
    ram[0x16]=7;ram[0x4ca2]=5;ram[0x4ca3]=6;
    const ms5::InputPortSamples ports={255,254,253,251,247};
    ms5::InputFrameResult result;result.next_pc=91;result.style=92;
    std::string error;
    const std::vector<std::uint8_t> before=ram;
    std::uint32_t d1=0x1357abcdU,d3=0x98767000U;
    assert(!ms5::begin_input_frame(ram,absent,absent,ports,0x100000,0xabcd,result,error,&d1,&d3));
    assert(d1==0x1357abcdU && d3==0x98767000U);
    assert(!ms5::begin_input_frame(ram,absent,table,ports,0x100000,0xabce,result,error,&d1,&d3));
    assert(ram==before && result.next_pc==91 && result.style==92);
    assert(d1==0x1357abcdU && d3==0x98767000U);
    assert(ms5::begin_input_frame(ram,absent,table,ports,0x100000,0xabcd,result,error,&d1,&d3));
    assert(d1==0x1357ab08U && d3==0x98767000U);
    assert(result.next_pc==0xf54 && result.callback==0 && result.callback_context==0);
    assert(result.style==0xab08 && result.read_count==5);
    assert(ram[0x1a]==7 && ram[0x16]==0 && ram[0x4ca2]==0 && ram[0x4ca3]==0);
    // A callback pointer overlapping the cleared word must be read afterwards.
    ram.assign(65536,0);ram[0x4ca2]=0x12;ram[0x4ca3]=0x34;
    assert(ms5::begin_input_frame(ram,absent,table,ports,0x104c2c,0,result,error));
    assert(result.callback==0 && result.next_pc==0xf54);
    ram[0x76]=0x12;ram[0x79]=0x34;ram[0x7a]=0x89;ram[0x7d]=0xab;
    assert(ms5::begin_input_frame(ram,absent,table,ports,0x100000,0,result,error));
    assert(result.callback==0x12000034 && result.callback_context==0x890000ab && result.next_pc==0xf3c);
    // Replay bit15 event sets D1 high byte; a wait with the same generated
    // word must preserve incoming D1 high byte instead of copying that word.
    ram.assign(65536,0);ram[0x4cd4]=1;
    ram[0x4cc5]=0x0f;ram[0x4cc6]=1;ram[0x4cc7]=0xfe;
    streams.data[0]=0xf0;streams.data[1]=1;
    assert(ms5::begin_input_frame(ram,streams,table,ports,0x100000,0xabcd,result,error));
    assert(result.style==0x8000 && ram[0x4cc2]==0x80);
    ram[0x4cd0]=0;
    assert(ms5::begin_input_frame(ram,streams,table,ports,0x100000,0xabcd,result,error));
    assert(result.style==0xab00 && ram[0x4cc2]==0x80);
    const std::vector<std::uint8_t> saved=ram;
    const ms5::InputFrameResult saved_result=result;
    assert(!ms5::begin_input_frame(ram,streams,table,ports,0x10ff84,0,result,error));
    assert(ram==saved && result.style==saved_result.style && result.next_pc==saved_result.next_pc);
    std::uint16_t style=0x9876;std::uint8_t reads=91;
    assert(!ms5::step_input(ram,streams,absent,ports,reads,error,&style));
    assert(ram==saved && style==0x9876 && reads==91);
    std::cout<<"Input frame signal ordering, callback boundary and D1 propagation passed\n";
}
