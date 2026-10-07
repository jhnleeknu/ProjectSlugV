#include "ms5/sound_queue.h"
#include <cassert>
#include <iostream>
int main() {
    std::vector<std::uint8_t> ram(65536,0);
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    ram[0x4d7b]=0xa5;ram[0xf003]=0xc3;
    ram[0x4d74]=0xff;ram[0x4d76]=0xee;
    assert(ms5::service_sound_queue(ram,1,writes,error));
    assert(writes.size()==1 && writes[0].value==3 && ram[0x4d7b]==0x25 && ram[0xf003]==0xc3);
    assert(ms5::service_sound_queue(ram,1,writes,error));
    assert(writes.empty() && ram[0xf003]==0xc3 && ram[0x4d7c]==1);
    assert(ms5::service_sound_queue(ram,0,writes,error));
    assert(writes.size()==1 && writes[0].value==127 && ram[0xf003]==0x43);
    const std::vector<std::uint8_t> before=ram;
    assert(!ms5::service_sound_queue(ram,2,writes,error));
    assert(ram==before && writes.size()==1 && writes[0].value==127);
    ram.assign(65536,0);ram[0x4d75]=127;ram[0x4d77]=3;
    ram[0x4d73]=42;ram[0x4cf4]=42;ram[0x4cf5]=42;ram[0x4cf6]=43;
    assert(ms5::service_sound_queue(ram,255,writes,error));
    assert(writes.size()==1 && writes[0].address==0x320000 && writes[0].size==1 && writes[0].value==42);
    assert(ram[0x4d75]==2);
    assert(ms5::service_sound_queue(ram,0,writes,error));
    assert(writes.size()==1 && writes[0].value==43 && ram[0x4d75]==3);
    assert(ms5::service_sound_queue(ram,0,writes,error));assert(writes.empty());
    // Equal invalid indices never access the queue in the original.
    ram[0x4d74]=ram[0x4d76]=255;ram[0x4d75]=ram[0x4d77]=255;
    assert(ms5::service_sound_queue(ram,0,writes,error));assert(writes.empty());
    ram.resize(65535);const std::vector<std::uint8_t> short_ram=ram;
    assert(!ms5::service_sound_queue(ram,0,writes,error));assert(ram==short_ram && writes.empty());
    std::cout<<"Sound status priority, ring deduplication and rollback passed\n";
}
