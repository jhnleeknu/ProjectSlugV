#include "ms5/sound_queue.h"
#include <new>
namespace ms5 {
bool service_sound_queue(std::vector<std::uint8_t>& ram,std::uint8_t status,
                         std::vector<VideoPortWrite>& writes,std::string& error) {
    if(ram.size()!=65536U) {error="sound queue requires 64KiB RAM";return false;}
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        bool send=false;
        std::uint8_t command=0;
        candidate[0x4d7c]=status;
        const bool reset=(candidate[0x4d7b]&128U)!=0;
        candidate[0x4d7b]&=127U;
        if(reset) {
            candidate[0x4d7a]=255;command=3;send=true;
        } else if(status!=1) {
            const bool special=(candidate[0xf003]&128U)!=0;
            candidate[0xf003]&=127U;
            if(special) {
                candidate[0x4d7a]=255;command=127;send=true;
            } else {
                unsigned int head=(static_cast<unsigned int>(candidate[0x4d74])<<8)|candidate[0x4d75];
                const unsigned int tail=(static_cast<unsigned int>(candidate[0x4d76])<<8)|candidate[0x4d77];
                if(head!=tail) {
                    if(head>=128U || tail>=128U) {error="nonempty sound queue indices must be 0..127";return false;}
                    command=candidate[0x4cf4U+head];
                    do {head=(head+1U)&127U;}
                    while(head!=tail && candidate[0x4cf4U+head]==command);
                    candidate[0x4d74]=0;candidate[0x4d75]=static_cast<std::uint8_t>(head);
                    send=true;
                }
            }
        }
        if(send) {
            VideoPortWrite write;write.size=1;write.address=0x320000;write.value=command;
            pending.push_back(write);
        }
        ram.swap(candidate);writes.swap(pending);
    } catch(const std::bad_alloc&) {error="cannot allocate sound queue state";return false;}
    error.clear();return true;
}
}
