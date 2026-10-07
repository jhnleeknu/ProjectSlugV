#include "ms5/sound_byte.h"
#include "ms5/sound_queue.h"
#include <cassert>
#include <iostream>
int main() {
    std::vector<std::uint8_t> ram(65536,0);
    ram[0x4d75]=0;ram[0x4d77]=127;
    for(unsigned int i=0;i<127;++i) ram[0x4cf4+i]=static_cast<std::uint8_t>(i+10);
    const std::vector<std::uint8_t> full=ram;
    ms5::SoundBytePending pending;std::string error;
    assert(ms5::enqueue_sound_byte(ram,42,pending,error));
    assert(ram==full && pending.waiting && pending.tail==127 && pending.next==0);
    assert(ms5::resume_sound_byte(ram,pending,error));assert(ram==full && pending.waiting);
    std::vector<ms5::VideoPortWrite> writes;
    assert(ms5::service_sound_queue(ram,0,writes,error));
    assert(writes.size()==1 && writes[0].value==10 && ram[0x4d75]==1);
    // Resume uses the originally captured slot even if live tail changed.
    ram[0x4d77]=50;
    assert(ms5::resume_sound_byte(ram,pending,error));
    assert(!pending.waiting && pending.tail==127 && pending.next==0);
    assert(ram[0x4d73]==42 && ram[0x4d77]==0);
    const std::vector<std::uint8_t> done=ram;
    assert(!ms5::resume_sound_byte(ram,pending,error));assert(ram==done && !pending.waiting);
    ram[0x4d74]=255;ram[0x4d76]=255;
    assert(ms5::enqueue_sound_byte(ram,3,pending,error));
    assert(ram[0x4d7b]==255 && !pending.waiting && pending.command==3 && pending.tail==0 && pending.next==0);
    const std::vector<std::uint8_t> bad=ram;
    assert(!ms5::enqueue_sound_byte(ram,4,pending,error));assert(ram==bad && pending.command==3);
    pending.waiting=true;pending.command=42;pending.tail=127;pending.next=1;
    assert(!ms5::resume_sound_byte(ram,pending,error));assert(ram==bad && pending.next==1);
    pending.next=0;
    assert(!ms5::resume_sound_byte(ram,pending,error));assert(ram==bad && pending.waiting);
    std::cout<<"Sound producer captured-slot waiting, consumer release and priority bypass passed\n";
}
