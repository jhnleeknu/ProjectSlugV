#include "ms5/frame_gate.h"
#include <cassert>
#include <iostream>
int main() {
    std::vector<std::uint8_t> ram(65536,0xa5);
    ram[0x16]=1;ram[0x17]=2;
    const std::vector<std::uint8_t> before=ram;
    bool ready=true;std::string error;
    assert(ms5::poll_frame_gate(ram,0xffff,ready,error));assert(!ready && ram==before);
    ram[0x16]=2;
    const unsigned int input[]={0,0x7fff,0x8000,0x807f,0x8080,0xffff};
    const unsigned int expected[]={0,0,0,0,1,255};
    for(unsigned int i=0;i<6;++i) {
        assert(ms5::poll_frame_gate(ram,input[i],ready,error));
        assert(ready && ram[0x18]==expected[i] && ram[0x16]==2 && ram[0x17]==2);
    }
    ram[0x16]=0;ram[0x17]=0;
    assert(ms5::poll_frame_gate(ram,0xffff,ready,error));assert(ready && ram[0x18]==255);
    ram.resize(65535);const std::vector<std::uint8_t> short_ram=ram;
    assert(!ms5::poll_frame_gate(ram,0,ready,error));assert(ready && ram==short_ram);
    std::cout<<"Frame gate unsigned readiness, video boundaries and preservation passed\n";
}
