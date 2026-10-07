#include "ms5/sound_service.h"
namespace ms5 {
namespace {
bool finish(std::vector<std::uint8_t>& ram,std::uint8_t status,const SoundWordPending& pending,
            std::uint8_t& reads,std::vector<VideoPortWrite>& writes,std::string& error) {
    reads=0;
    if(pending.kind!=0) return true;
    if(!service_sound_queue(ram,status,writes,error)) return false;
    reads=1;return true;
}
}
bool step_sound(std::vector<std::uint8_t>& ram,std::uint8_t external_status,
                std::uint8_t sound_status,SoundWordPending& pending,
                std::uint8_t& read_count,std::vector<VideoPortWrite>& writes,std::string& error) {
    if(ram.size()!=65536U) {error="sound service requires 64KiB RAM";return false;}
    std::vector<std::uint8_t> candidate=ram;SoundWordPending next;
    std::vector<VideoPortWrite> ports;std::uint8_t reads=0;
    unsigned int timer=(static_cast<unsigned int>(candidate[0xd68c])<<8)|candidate[0xd68d];
    if(timer!=0) {
        // BLE is signed word: negative values also take the increment path.
        const bool increment=timer<=15U || timer>=0x8000U;
        const unsigned int updated=increment ? ((timer+1U)&65535U) : 0U;
        candidate[0xd68c]=static_cast<std::uint8_t>(updated>>8);
        candidate[0xd68d]=static_cast<std::uint8_t>(updated);
        if(!increment) timer=0;
        const std::uint16_t command=static_cast<std::uint16_t>((timer+0x19c0U)&65535U);
        if(!enqueue_sound_word(candidate,command,external_status,next,error)) return false;
    }
    if(!finish(candidate,sound_status,next,reads,ports,error)) return false;
    ram.swap(candidate);pending=next;read_count=reads;writes.swap(ports);error.clear();return true;
}
bool resume_sound(std::vector<std::uint8_t>& ram,std::uint8_t sound_status,
                  SoundWordPending& pending,std::uint8_t& read_count,
                  std::vector<VideoPortWrite>& writes,std::string& error) {
    if(ram.size()!=65536U || pending.kind!=1) {
        error="sound service resume requires a pending overflow producer";return false;
    }
    std::vector<std::uint8_t> candidate=ram;SoundWordPending next=pending;
    std::vector<VideoPortWrite> ports;std::uint8_t reads=0;
    if(!resume_sound_word(candidate,next,error)) return false;
    if(!finish(candidate,sound_status,next,reads,ports,error)) return false;
    ram.swap(candidate);pending=next;read_count=reads;writes.swap(ports);error.clear();return true;
}
}
