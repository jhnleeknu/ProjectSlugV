#include "ms5/sound_word.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,unsigned int value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
unsigned int word(const std::vector<std::uint8_t>& ram,unsigned int at) {
    return (static_cast<unsigned int>(ram[at])<<8)|ram[at+1];
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0);ms5::SoundWordPending p;std::string error;
    put(ram,0x4d82,0x422);put(ram,0x4d84,0x523);put(ram,0x4d86,0x624);put(ram,0x4d8c,6);
    assert(ms5::enqueue_sound_word(ram,0x422,0,p,error));
    assert(word(ram,0x4d82)==0x523 && word(ram,0x4d84)==0x422 && word(ram,0x4d86)==0x624);
    // Full byte queue: word overflow publishes word indices before suspending.
    put(ram,0x4d76,127);
    assert(ms5::enqueue_sound_word(ram,0x725,0,p,error));
    assert(p.kind==1 && p.phase==1 && p.low==0x23 && p.byte.command==5);
    assert(word(ram,0x4d8a)==2 && word(ram,0x4d8c)==0);
    // One slot allows high byte, then suspends on low byte.
    put(ram,0x4d74,1);
    assert(ms5::resume_sound_word(ram,p,error));
    assert(p.phase==2 && p.byte.command==0x23 && ram[0x4d73]==5);
    put(ram,0x4d74,2);
    assert(ms5::resume_sound_word(ram,p,error));assert(p.kind==0 && ram[0x4cf4]==0x23);
    // Drain retains cursor and low byte across a wait, not the live head/data.
    ram.assign(65536,0);put(ram,0x4d82,0x422);put(ram,0x4d8c,2);put(ram,0x4d76,127);
    assert(ms5::drain_sound_words(ram,p,error));assert(p.kind==2 && p.cursor==0 && p.low==0x22);
    put(ram,0x4d82,0xffff);put(ram,0x4d8a,6);put(ram,0x4d74,2);
    assert(ms5::resume_sound_word(ram,p,error));
    assert(p.kind==0 && word(ram,0x4d8a)==2 && ram[0x4d73]==4 && ram[0x4cf4]==0x22);
    // A late invalid tail rejects the entire resume, including emitted bytes.
    ram.assign(65536,0);put(ram,0x4d82,0x422);put(ram,0x4d8c,2);put(ram,0x4d76,127);
    assert(ms5::drain_sound_words(ram,p,error));put(ram,0x4d8c,3);put(ram,0x4d74,2);
    const std::vector<std::uint8_t> before=ram;
    assert(!ms5::resume_sound_word(ram,p,error));assert(ram==before && p.kind==2 && p.phase==1 && p.byte.tail==127);
    // Filtered commands never touch malformed ring indices.
    assert(ms5::enqueue_sound_word(ram,0x2000,0,p,error));assert(ram==before && p.kind==0);
    std::cout<<"Sound word duplicate swap, overflow, captured drain and rollback passed\n";
}
