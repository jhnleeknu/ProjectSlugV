#include "ms5/sound_service.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,unsigned int value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0);ms5::SoundWordPending p;std::string error;
    std::vector<ms5::VideoPortWrite> writes;std::uint8_t reads=99;
    put(ram,0xd68c,1);put(ram,0x4d82,0x422);put(ram,0x4d84,0x533);put(ram,0x4d86,0x644);
    put(ram,0x4d8c,6);put(ram,0x4d76,127);ram[0x4d7c]=0x55;
    assert(ms5::step_sound(ram,0,0,p,reads,writes,error));
    assert(p.kind==1 && p.phase==1 && reads==0 && writes.empty());
    assert(ram[0xd68d]==2 && ram[0x4d7c]==0x55);
    put(ram,0xd68c,0x1234);put(ram,0x4d74,1);
    assert(ms5::resume_sound(ram,0,p,reads,writes,error));
    assert(p.phase==2 && reads==0 && writes.empty() && ram[0xd68d]==0x34);
    put(ram,0x4d74,2);
    assert(ms5::resume_sound(ram,1,p,reads,writes,error));
    assert(p.kind==0 && reads==1 && writes.empty() && ram[0x4d7c]==1 && ram[0xd68d]==0x34);
    // Consumer failure cancels timer increment and word append, retaining outputs.
    ram.assign(65536,0);put(ram,0xd68c,1);put(ram,0x4d76,128);
    const std::vector<std::uint8_t> before=ram;reads=99;p.kind=2;
    ms5::VideoPortWrite prior;prior.size=2;prior.address=7;prior.value=9;writes.push_back(prior);
    assert(!ms5::step_sound(ram,0,0,p,reads,writes,error));
    assert(ram==before && reads==99 && p.kind==2 && writes.size()==1 && writes[0].value==9);
    // Negative signed timer wraps and uses the pre-increment command value.
    ram.assign(65536,0);put(ram,0xd68c,65535);
    assert(ms5::step_sound(ram,0,1,p,reads,writes,error));
    assert(ram[0xd68c]==0 && ram[0xd68d]==0 && ram[0x4d82]==0x19 && ram[0x4d83]==0xbf);
    assert(reads==1 && p.kind==0);
    assert(!ms5::resume_sound(ram,0,p,reads,writes,error));
    std::cout<<"Sound service production order, two waits, status sampling and rollback passed\n";
}
