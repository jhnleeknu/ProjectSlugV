#include "ms5/sprite_refresh_queue.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,unsigned int value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0);std::vector<ms5::CompositionResource> resources;
    std::vector<ms5::SpriteWrite> writes;bool processed=true;std::string error;std::uint32_t d0=0x12345678;
    assert(ms5::refresh_sprite_queue(ram,resources,writes,processed,error,&d0));
    assert(!processed && d0==0x12345678);
    for(unsigned int direction=0;direction<2;++direction) {
        ram.assign(65536,0);ram[0x8d3c]=direction ? 128 : 0;ram[0x8d3d]=128;
        for(unsigned int at=0x8d3e;at<0x8d4e;++at) ram[at]=255;
        assert(ms5::refresh_sprite_queue(ram,resources,writes,processed,error,&d0));
        assert(processed && writes.empty() && d0==(direction ? 0x82008000U : 0x81ff8000U));
    }
    // Late missing resource rejection leaves D0 and caller outputs intact.
    ram.assign(65536,0);ram[0x8d3d]=128;put(ram,0x8d36,2);put(ram,0x7f38,65535);
    d0=0xabcdef00;processed=false;const std::vector<std::uint8_t> before=ram;
    assert(!ms5::refresh_sprite_queue(ram,resources,writes,processed,error,&d0));
    assert(d0==0xabcdef00 && !processed && ram==before && writes.empty());
    std::cout<<"Sprite refresh D0 early return, zero cleanup, disabled pools and rollback passed\n";
}
