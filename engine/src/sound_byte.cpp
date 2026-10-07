#include "ms5/sound_byte.h"
namespace ms5 {
namespace {
unsigned int word(const std::vector<std::uint8_t>& ram,std::size_t at) {
    return (static_cast<unsigned int>(ram[at])<<8)|ram[at+1];
}
bool advance(std::vector<std::uint8_t>& ram,SoundBytePending& pending,std::string& error) {
    const unsigned int head=word(ram,0x4d74);
    if(head>=128U) {error="sound byte queue head must be 0..127";return false;}
    pending.waiting=head==pending.next;
    if(!pending.waiting) {
        ram[0x4cf4U+pending.tail]=pending.command;
        ram[0x4d76]=0;ram[0x4d77]=static_cast<std::uint8_t>(pending.next);
    }
    error.clear();return true;
}
}
bool enqueue_sound_byte(std::vector<std::uint8_t>& ram,std::uint8_t command,
                        SoundBytePending& pending,std::string& error) {
    if(ram.size()!=65536U) {error="sound byte enqueue requires 64KiB RAM";return false;}
    SoundBytePending candidate;candidate.command=command;
    if(command==3) {
        ram[0x4d7b]=255;pending=candidate;error.clear();return true;
    }
    candidate.tail=static_cast<std::uint16_t>(word(ram,0x4d76));
    if(candidate.tail>=128U) {error="sound byte queue tail must be 0..127";return false;}
    candidate.next=static_cast<std::uint16_t>((candidate.tail+1U)&127U);
    if(!advance(ram,candidate,error)) return false;
    pending=candidate;return true;
}
bool resume_sound_byte(std::vector<std::uint8_t>& ram,SoundBytePending& pending,
                       std::string& error) {
    if(ram.size()!=65536U || !pending.waiting || pending.command==3 ||
       pending.tail>=128U || pending.next!=((pending.tail+1U)&127U)) {
        error="invalid pending sound byte continuation";return false;
    }
    SoundBytePending candidate=pending;
    if(!advance(ram,candidate,error)) return false;
    pending=candidate;return true;
}
}
