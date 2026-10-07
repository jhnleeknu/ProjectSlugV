#include "ms5/game_initialization.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,std::size_t at,std::uint32_t value) {
    ram[at]=static_cast<std::uint8_t>(value>>24);ram[at+1]=static_cast<std::uint8_t>(value>>16);
    ram[at+2]=static_cast<std::uint8_t>(value>>8);ram[at+3]=static_cast<std::uint8_t>(value);
}
ms5::FixedDataResource resource() {
    ms5::FixedDataResource r;r.source_cpu_address=r.source_rom_offset=0x4cf64;r.data.assign(320,0);
    r.data[1]=0x42;r.data[2]=0x53;r.data[10]=0x12;r.data[11]=0x34;
    r.data[12]=0xab;r.data[13]=0xcd;r.data[14]=0x56;r.data[15]=0x78;return r;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0xa5);put(ram,0xcb8,0x270e);put(ram,0xda8,0x270e);
    ram[0x12]=0;ram[0x4d8a]=ram[0x4d8b]=ram[0x4d8c]=ram[0x4d8d]=0;
    ram[0x4d74]=ram[0x4d75]=ram[0x4d76]=ram[0x4d77]=0;return ram;
}
}
int main() {
    ms5::FixedDataResource records=resource();std::string error;
    std::vector<std::uint8_t> ram=fixture();std::uint32_t d0=0x12345678,d1=0xabcdef12,d3=0x87654321;
    assert(ms5::finish_game_initialization(ram,records,d0,d1,d3,error));
    assert(d0==0&&d1==0&&d3==0&&error.empty());
    assert(ram[0xd694]==0&&ram[0xd695]==0x53&&ram[0xd696]==0x42&&ram[0xd697]==0xcd);
    assert(ram[0xd698]==0x12&&ram[0xd699]==0x34&&ram[0xd69c]==0&&ram[0xd69d]==0x53);
    assert(ram[6]==0&&ram[7]==0&&ram[8]==0x3d&&ram[9]==0xcc&&ram[13]==0xcc);
    assert(ram[0x4d91]==0xa5&&ram[0xd690]==0&&ram[0xd691]==0xa0&&ram[0xd692]==1&&ram[0xd693]==0x80);
    assert(ram[0xd732]==0xa5&&ram[0xd68f]==0xa5&&ram[0xdc8e]==0xa5);
    assert(ram[0xde2a]==0&&ram[0xde2b]==0x0e&&ram[0xde2c]==0x89&&ram[0xde2d]==0xec);
    // The prefix must also roll back when its successfully completed work is
    // followed by a bad resource in the suffix.
    for(unsigned int failure=0;failure<3;++failure) {
        ram=fixture();const std::vector<std::uint8_t> before=ram;
        ms5::GameInitializationState state;state.prelude.d0=1;state.prelude.d1=2;state.prelude.d3=3;
        std::uint8_t reads=99;ms5::FixedDataResource bad=records;
        if(failure==0)bad.data.pop_back();
        if(failure==1){state.prelude.phase=4;state.prelude.next_pc=0x475a4;state.prelude.byte.command=1;}
        if(failure==2)state.returned=true;
        assert(!ms5::initialize_game(ram,bad,0,state,reads,error));
        assert(ram==before&&reads==99&&state.prelude.d0==1&&state.prelude.d1==2&&state.prelude.d3==3);
    }
    ram=fixture();ms5::GameInitializationState state;std::uint8_t reads=99;
    assert(ms5::initialize_game(ram,records,0,state,reads,error));
    assert(state.returned&&state.prelude.phase==4&&state.prelude.next_pc==0x475a4&&reads==0);
    assert(state.prelude.d0==0&&state.prelude.d1==0&&state.prelude.d3==0);
    // Idle resource remains unused while a full byte queue suspends the prefix.
    ram=fixture();ram[0x4d75]=1;state=ms5::GameInitializationState();ms5::FixedDataResource unused;
    assert(ms5::initialize_game(ram,unused,0,state,reads,error));
    assert(!state.returned&&state.prelude.phase==2&&state.prelude.byte.waiting);
    const std::vector<std::uint8_t> waited=ram;
    const std::uint32_t saved0=state.prelude.d0,saved1=state.prelude.d1,saved3=state.prelude.d3;
    ram[0x4d75]=0;const std::vector<std::uint8_t> released=ram;reads=99;
    assert(!ms5::initialize_game(ram,unused,0,state,reads,error));
    assert(ram==released&&reads==99&&!state.returned&&state.prelude.d0==saved0&&state.prelude.d1==saved1&&state.prelude.d3==saved3);
    ram=waited;ram[0x4d75]=0;
    assert(ms5::initialize_game(ram,records,0,state,reads,error));assert(state.returned);
    std::cout<<"game initialization tests passed\n";
}
