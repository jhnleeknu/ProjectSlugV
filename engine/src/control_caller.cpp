#include "ms5/control_caller.h"
#include "ms5/control_counter.h"
#include "ms5/video_control.h"
#include "ms5/palette_snapshot.h"
#include "ms5/palette_control.h"
#include "ms5/palette_frame.h"
#include <new>
namespace ms5 {
bool consume_control_result(std::vector<std::uint8_t>& ram,
                            const std::vector<PaletteRecord>& records,
                            std::uint32_t object_address,std::uint32_t control_d0,
                            std::uint32_t& next_pc,std::vector<VideoPortWrite>& writes,
                            std::string& error,std::uint32_t* d1,std::uint32_t* d3) {
    if(ram.size()!=65536U || (object_address&1U)!=0 ||
       object_address<0x100000U || object_address>0x10ff7aU) {
        error="control caller requires 64KiB RAM and an even complete object span";return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        const std::size_t object=object_address-0x100000U;
        const std::uint8_t previous=candidate[object+0x84];
        const std::uint8_t status=static_cast<std::uint8_t>(control_d0);
        std::uint32_t next_d1=((d1!=NULL ? *d1 : 0)&0xffffff00U)|previous;
        std::uint32_t next_d3=d3!=NULL ? *d3 : 0;
        candidate[object+0x84]=status;
        std::uint32_t boundary=0;
        if(status==0) {
            if(previous!=0) {
                std::uint16_t saved=0;
                if(!query_video_control(candidate,saved,error))return false;
                candidate[object+0x82]=static_cast<std::uint8_t>(saved>>8);
                candidate[object+0x83]=static_cast<std::uint8_t>(saved);
                if(!set_video_control(candidate,0,pending,error))return false;
            }
            if(previous==1) {
                candidate[0x7dec]=0;
                if(!save_palette_effect(candidate,error))return false;
                candidate[object+0x80]=255;
                std::uint16_t deltas[3];
                for(unsigned int channel=0;channel<3;++channel) {
                    const std::size_t at=0x7dc2+channel*2;
                    const unsigned int current=(static_cast<unsigned int>(candidate[at])<<8)|candidate[at+1];
                    deltas[channel]=static_cast<std::uint16_t>(0xfc00U-current);
                }
                next_d1=0xffff0000U|deltas[1];
                next_d3=0;
                if((deltas[0]|deltas[1]|deltas[2])!=0) {
                    const std::int32_t delta=deltas[1]<0x8000U ? deltas[1] :
                        static_cast<std::int32_t>(deltas[1])-65536;
                    next_d1=(static_cast<std::uint32_t>(static_cast<std::uint16_t>(delta%4))<<16)|
                        static_cast<std::uint16_t>(delta/4);
                    next_d3=4;
                }
                if(!set_palette_effect(candidate,0xfffc,0xfffc,0xfffc,4,error))return false;
            }
            std::vector<VideoPortWrite> palette_writes;
            if(!step_palette_frame(candidate,records,error,&palette_writes,&next_d1,&next_d3))return false;
            pending.insert(pending.end(),palette_writes.begin(),palette_writes.end());
            boundary=0xec4;
        } else {
            if(previous==0) {
                const std::uint16_t saved=static_cast<std::uint16_t>(
                    (static_cast<unsigned int>(candidate[object+0x82])<<8)|candidate[object+0x83]);
                if(!set_video_control(candidate,saved,pending,error))return false;
                if(candidate[object+0x80]!=0) {
                    next_d1=(next_d1&0xffffff00U)|candidate[0x7dc4];
                    if(!restore_palette_effect(candidate,error))return false;
                    candidate[object+0x80]=0;
                }
            }
            bool trap=false;
            if(!advance_control_counter(candidate,object_address,trap,error))return false;
            if(trap)boundary=0xfee;
        }
        ram.swap(candidate);writes.swap(pending);next_pc=boundary;
        if(d1!=NULL)*d1=next_d1;
        if(d3!=NULL)*d3=next_d3;
    } catch(const std::bad_alloc&) {error="cannot allocate control caller state";return false;}
    error.clear();return true;
}
}
