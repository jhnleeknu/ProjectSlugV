#include "ms5/sound_word.h"
namespace ms5 {
namespace {
unsigned int word(const std::vector<std::uint8_t>& ram,std::size_t at) {
    return (static_cast<unsigned int>(ram[at])<<8)|ram[at+1];
}
void put_word(std::vector<std::uint8_t>& ram,std::size_t at,unsigned int value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
bool index_valid(unsigned int index) { return index<=6U && (index&1U)==0; }
bool indices(const std::vector<std::uint8_t>& ram,std::string& error) {
    if(!index_valid(word(ram,0x4d8a)) || !index_valid(word(ram,0x4d8c))) {
        error="sound word indices must be 0, 2, 4 or 6";return false;
    }
    return true;
}
bool send_low(std::vector<std::uint8_t>& ram,SoundWordPending& pending,std::string& error) {
    pending.phase=2;
    return enqueue_sound_byte(ram,pending.low,pending.byte,error);
}
bool send_pair(std::vector<std::uint8_t>& ram,unsigned int command,SoundWordPending& pending,std::string& error) {
    pending.low=static_cast<std::uint8_t>(command);pending.phase=1;
    if(!enqueue_sound_byte(ram,static_cast<std::uint8_t>(command>>8),pending.byte,error)) return false;
    if(pending.byte.waiting) return true;
    return send_low(ram,pending,error);
}
bool drain(std::vector<std::uint8_t>& ram,SoundWordPending& pending,std::string& error) {
    for(;;) {
        const unsigned int tail=word(ram,0x4d8c);
        if(!index_valid(tail)) {error="sound word live tail must be 0, 2, 4 or 6";return false;}
        if(pending.cursor==tail) {
            put_word(ram,0x4d8a,pending.cursor);pending=SoundWordPending();return true;
        }
        const unsigned int command=word(ram,0x4d82+pending.cursor);
        if(command!=0) {
            if(!send_pair(ram,command,pending,error)) return false;
            if(pending.byte.waiting) return true;
        }
        pending.cursor=static_cast<std::uint16_t>((pending.cursor+2U)&6U);
    }
}
bool start_enqueue(std::vector<std::uint8_t>& ram,std::uint16_t command,std::uint8_t external,
                   SoundWordPending& pending,std::string& error) {
    const unsigned int high=command&0xff00U;
    if(command>=0x2000U || (command&255U)<0x20U || high==0x100U || high==0x200U || high==0x300U) return true;
    if(ram[0x12]==1 && (high==0 || (ram[0xfd82]!=0 && ram[0xfe80]==0 && external!=0) || ram[0xfd8d]==0)) return true;
    if((ram[0x4d7e]!=0 && command>=0x1000U) || ((ram[0xf001]&32U)!=0 && high==0)) return true;
    if(!indices(ram,error)) return false;
    unsigned int cursor=word(ram,0x4d8a);
    const unsigned int tail=word(ram,0x4d8c);
    while(cursor!=tail) {
        const unsigned int at=0x4d82+cursor;cursor=(cursor+2U)&6U;
        if(word(ram,at)==command) {
            if(cursor!=tail) {
                put_word(ram,at,word(ram,0x4d82+cursor));put_word(ram,0x4d82+cursor,command);
            }
            return true;
        }
    }
    put_word(ram,0x4d82+cursor,command);cursor=(cursor+2U)&6U;
    put_word(ram,0x4d8c,cursor);
    if(cursor!=word(ram,0x4d8a)) return true;
    const unsigned int oldest=word(ram,0x4d82+cursor);
    put_word(ram,0x4d8a,(cursor+2U)&6U);
    if(oldest==0) return true;
    pending.kind=1;
    if(!send_pair(ram,oldest,pending,error)) return false;
    if(!pending.byte.waiting) pending=SoundWordPending();
    return true;
}
}
bool enqueue_sound_word(std::vector<std::uint8_t>& ram,std::uint16_t command,
                        std::uint8_t external,SoundWordPending& pending,std::string& error) {
    if(ram.size()!=65536U) {error="sound word enqueue requires 64KiB RAM";return false;}
    std::vector<std::uint8_t> candidate=ram;SoundWordPending next;
    if(!start_enqueue(candidate,command,external,next,error)) return false;
    ram.swap(candidate);pending=next;error.clear();return true;
}
bool drain_sound_words(std::vector<std::uint8_t>& ram,SoundWordPending& pending,std::string& error) {
    if(ram.size()!=65536U) {error="sound word drain requires 64KiB RAM";return false;}
    if(!indices(ram,error)) return false;
    std::vector<std::uint8_t> candidate=ram;SoundWordPending next;
    next.kind=2;next.cursor=static_cast<std::uint16_t>(word(ram,0x4d8a));
    if(!drain(candidate,next,error)) return false;
    ram.swap(candidate);pending=next;error.clear();return true;
}
bool resume_sound_word(std::vector<std::uint8_t>& ram,SoundWordPending& pending,std::string& error) {
    if(ram.size()!=65536U || (pending.kind!=1 && pending.kind!=2) ||
       (pending.phase!=1 && pending.phase!=2) || !pending.byte.waiting ||
       !index_valid(pending.cursor) || (pending.kind==1 && pending.cursor!=0) ||
       (pending.phase==2 && pending.byte.command!=pending.low)) {
        error="invalid sound word continuation";return false;
    }
    std::vector<std::uint8_t> candidate=ram;SoundWordPending next=pending;
    if(!resume_sound_byte(candidate,next.byte,error)) return false;
    if(!next.byte.waiting && next.phase==1) {
        if(!send_low(candidate,next,error)) return false;
    }
    if(!next.byte.waiting) {
        if(next.kind==1) next=SoundWordPending();
        else {
            next.cursor=static_cast<std::uint16_t>((next.cursor+2U)&6U);
            if(!drain(candidate,next,error)) return false;
        }
    }
    ram.swap(candidate);pending=next;error.clear();return true;
}
}
