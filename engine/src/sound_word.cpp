#include "ms5/sound_word.h"
#include <new>
namespace ms5 {
namespace {
struct WordRegisters {
    std::uint32_t d0, d1;
    std::uint8_t reads;
    WordRegisters(std::uint32_t initial0, std::uint32_t initial1) : d0(initial0), d1(initial1), reads(0) {}
};
void d1_word(WordRegisters* registers, unsigned int value) {
    if (registers != NULL) registers->d1 = (registers->d1 & 0xffff0000U) | value;
}
void d0_byte(WordRegisters* registers, std::uint8_t value) {
    if (registers != NULL) registers->d0 = (registers->d0 & 0xffffff00U) | value;
}
void byte_result(WordRegisters* registers, const SoundBytePending& byte) {
    if (byte.command != 3) d1_word(registers,byte.next);
}
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
bool send_low(std::vector<std::uint8_t>& ram, SoundWordPending& pending, std::string& error, WordRegisters* registers = NULL) {
    pending.phase = 2; d0_byte(registers,pending.low);
    if (!enqueue_sound_byte(ram,pending.low,pending.byte,error)) return false;
    byte_result(registers,pending.byte); return true;
}
bool send_pair(std::vector<std::uint8_t>& ram,unsigned int command,SoundWordPending& pending,std::string& error, WordRegisters* registers = NULL) {
    pending.low=static_cast<std::uint8_t>(command);pending.phase=1;
    d0_byte(registers,static_cast<std::uint8_t>(command >> 8));
    if(!enqueue_sound_byte(ram,static_cast<std::uint8_t>(command>>8),pending.byte,error)) return false;
    byte_result(registers,pending.byte);
    if(pending.byte.waiting) return true;
    return send_low(ram,pending,error,registers);
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
                   SoundWordPending& pending,std::string& error, WordRegisters* registers = NULL) {
    const unsigned int high=command&0xff00U;
    if (command >= 0x2000U || (command & 255U) < 0x20U) return true;
    d1_word(registers,high);
    if (high == 0x100U || high == 0x200U || high == 0x300U) return true;
    if (ram[0x12] == 1) {
        if (high == 0) return true;
        if (ram[0xfd82] != 0 && ram[0xfe80] == 0) {
            if (registers != NULL) registers->reads = 1;
            if (external != 0) return true;
        }
        if (ram[0xfd8d] == 0) return true;
    }
    if((ram[0x4d7e]!=0 && command>=0x1000U) || ((ram[0xf001]&32U)!=0 && high==0)) return true;
    if(!indices(ram,error)) return false;
    unsigned int cursor=word(ram,0x4d8a);
    d1_word(registers,cursor);
    const unsigned int tail=word(ram,0x4d8c);
    while(cursor!=tail) {
        const unsigned int at=0x4d82+cursor;cursor=(cursor+2U)&6U;
        d1_word(registers,cursor);
        if(word(ram,at)==command) {
            if(cursor!=tail) {
                put_word(ram,at,word(ram,0x4d82+cursor));put_word(ram,0x4d82+cursor,command);
            }
            return true;
        }
    }
    put_word(ram,0x4d82+cursor,command);cursor=(cursor+2U)&6U;
    d1_word(registers,cursor);
    put_word(ram,0x4d8c,cursor);
    if(cursor!=word(ram,0x4d8a)) return true;
    const unsigned int oldest=word(ram,0x4d82+cursor);
    put_word(ram,0x4d8a,(cursor+2U)&6U);
    d1_word(registers,(cursor+2U)&6U);
    if(oldest==0) return true;
    pending.kind=1;
    if(!send_pair(ram,oldest,pending,error,registers)) return false;
    if(!pending.byte.waiting) pending=SoundWordPending();
    return true;
}
bool continuation(const std::vector<std::uint8_t>& ram, const SoundWordPending& pending) {
    if(ram.size()!=65536U || (pending.kind!=1 && pending.kind!=2) ||
       (pending.phase!=1 && pending.phase!=2) || !pending.byte.waiting ||
       !index_valid(pending.cursor) || (pending.kind==1 && pending.cursor!=0) ||
       (pending.phase==2 && pending.byte.command!=pending.low)) {
        return false;
    }
    return true;
}
bool resume_pending(std::vector<std::uint8_t>& ram, SoundWordPending& pending, std::string& error, WordRegisters* registers = NULL) {
    if(!resume_sound_byte(ram,pending.byte,error)) return false;
    byte_result(registers,pending.byte);
    if(!pending.byte.waiting && pending.phase==1) {
        if(!send_low(ram,pending,error,registers)) return false;
    }
    if(!pending.byte.waiting) {
        if(pending.kind==1) pending=SoundWordPending();
        else {
            pending.cursor=static_cast<std::uint16_t>((pending.cursor+2U)&6U);
            if(!drain(ram,pending,error)) return false;
        }
    }
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
bool resume_sound_word(std::vector<std::uint8_t>& ram, SoundWordPending& pending, std::string& error) {
    if (!continuation(ram,pending)) { error = "invalid sound word continuation"; return false; }
    std::vector<std::uint8_t> candidate = ram; SoundWordPending next = pending;
    if (!resume_pending(candidate,next,error)) return false;
    ram.swap(candidate); pending = next; error.clear(); return true;
}
bool enqueue_sound_word_registers(std::vector<std::uint8_t>& ram, std::uint32_t& d0, std::uint32_t& d1,
    std::uint8_t external, SoundWordPending& pending, std::uint8_t& reads, std::string& error) {
    if (ram.size() != 65536) { error = "sound word registers require64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SoundWordPending next; WordRegisters registers(d0,d1);
        if (!start_enqueue(candidate,static_cast<std::uint16_t>(d0),external,next,error,&registers)) return false;
        ram.swap(candidate); pending = next; d0 = registers.d0; d1 = registers.d1; reads = registers.reads; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate sound word register transaction"; return false; }
}
bool resume_sound_word_registers(std::vector<std::uint8_t>& ram, std::uint32_t& d0, std::uint32_t& d1,
    SoundWordPending& pending, std::string& error) {
    if (!continuation(ram,pending) || pending.kind != 1 || (d0 & 255U) != pending.byte.command ||
        (d1 & 65535U) != pending.byte.next) { error = "invalid sound word register continuation"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SoundWordPending next = pending; WordRegisters registers(d0,d1);
        if (!resume_pending(candidate,next,error,&registers)) return false;
        ram.swap(candidate); pending = next; d0 = registers.d0; d1 = registers.d1; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate sound word register transaction"; return false; }
}
}
