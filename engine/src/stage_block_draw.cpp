#include "ms5/stage_block_draw.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void word(std::uint32_t& value,std::uint32_t input) { value=(value&0xffff0000U)|low(input); }
void byte(std::uint32_t& value,std::uint32_t input) { value=(value&0xffffff00U)|(input&255U); }
bool fixed(const FixedDataResource& w) {
    return w.source_cpu_address<0x100000 && w.source_rom_offset==w.source_cpu_address &&
        !w.data.empty() && w.data.size()<=0x100000-w.source_cpu_address;
}
bool read(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    std::uint32_t address,unsigned int size,std::uint32_t& result,std::string& error) {
    if ((size>1 && (address&1U)) || address>0x1000000U-size) {
        error="unaligned or overflowing stage block draw read"; return false;
    }
    const std::vector<std::uint8_t>* bytes=NULL; std::size_t at=0;
    if (address>=0x100000 && address+size<=0x110000) { bytes=&ram; at=address-0x100000; }
    else {
        unsigned int matches=0;
        for (std::size_t i=0;i<windows.size();++i) {
            const FixedDataResource& w=windows[i]; if (!fixed(w)) continue;
            const std::uint64_t end=static_cast<std::uint64_t>(w.source_cpu_address)+w.data.size();
            if (address<end && static_cast<std::uint64_t>(address)+size>w.source_cpu_address) {
                ++matches;
                if (address>=w.source_cpu_address && static_cast<std::uint64_t>(address)+size<=end) { bytes=&w.data; at=address-w.source_cpu_address; }
            }
        }
        if (matches!=1 || bytes==NULL) { error="missing, ambiguous or partial fixed stage block draw read"; return false; }
    }
    std::uint32_t value=0;
    for (unsigned int i=0;i<size;++i) value=(value<<8)|(*bytes)[at+i];
    result=value; return true;
}
bool next(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    ObjectRestartState& s,unsigned int size,std::uint32_t& value,std::string& error) {
    if (!read(ram,windows,s.a[0],size,value,error)) return false;
    if (s.a[0]>0xffffffffU-size) { error="stage block draw cursor addition overflows"; return false; }
    s.a[0]+=size; return true;
}
void emit(std::vector<VideoPortWrite>& ports,unsigned int size,std::uint32_t value) {
    VideoPortWrite write; write.size=static_cast<std::uint8_t>(size); write.address=0x3c0000; write.value=value; ports.push_back(write);
}
bool rectangle(ObjectRestartState& s,std::vector<VideoPortWrite>& ports,std::string& error) {
    if (low(s.d[2])==0 || low(s.d[3])==0) {
        error="stage block draw zero width/height wrapping loops are unsupported"; return false;
    }
    s.a[4]=0x3c0000;
    do {
        word(s.d[7],s.d[0]); s.d[7]=(s.d[7]<<16)|(s.d[7]>>16); word(s.d[7],s.d[1]);
        word(s.d[6],s.d[3]);
        do {
            if (s.d[7]>=0x75000000U) { error="original stage block draw TRAP15: tile address exceeds supported video range"; return false; }
            emit(ports,4,s.d[7]); s.d[7]+=0x10000U; byte(s.d[7],s.d[7]+0x10U);
            word(s.d[6],s.d[6]-1U);
        } while (low(s.d[6])!=0);
        byte(s.d[1],s.d[1]+1U); word(s.d[0],s.d[0]+0x20U); word(s.d[2],s.d[2]-1U);
    } while (low(s.d[2])!=0);
    emit(ports,2,0x8200); return true;
}
bool run(const std::vector<std::uint8_t>& ram,std::uint32_t entry,
    const std::vector<FixedDataResource>& windows,ObjectRestartState& s,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    if (entry==0x35f0) return rectangle(s,ports,error);
    if (entry==0x477a2) word(s.d[0],0x7162);
    if (entry==0x477a2 || entry==0xddf9a) s.a[0]=0xddfa4;
    for (;;) {
        std::uint32_t value=0;
        if (!next(ram,windows,s,2,value,error)) return false; word(s.d[1],value);
        if (low(s.d[1])==0xffff) return true;
        const std::uint16_t saved_d0=low(s.d[0]); word(s.d[0],s.d[0]+s.d[1]);
        s.d[2]=0; s.d[3]=0;
        if (!next(ram,windows,s,2,value,error)) return false; word(s.d[1],value);
        if (!next(ram,windows,s,1,value,error)) return false; byte(s.d[2],value);
        if (!next(ram,windows,s,1,value,error)) return false; byte(s.d[3],value);
        const std::uint32_t saved_a0=s.a[0];
        if (!rectangle(s,ports,error)) return false;
        s.a[0]=saved_a0; word(s.d[0],saved_d0);
    }
}
}
bool execute_stage_block_draw(std::vector<std::uint8_t>& ram,std::uint32_t entry,
    const std::vector<FixedDataResource>& windows,ObjectRestartState& state,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    if (ram.size()!=65536 || (entry!=0x477a2 && entry!=0xddf9a && entry!=0x362a && entry!=0x35f0)) {
        error="stage block draw requires64KiB RAM and supported477a2/ddf9a/362a/35f0 entry"; return false;
    }
    try {
        ObjectRestartState candidate=state; std::vector<VideoPortWrite> output;
        if (!run(ram,entry,windows,candidate,output,error)) return false;
        state=candidate; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error="cannot allocate stage block draw port transaction"; return false; }
}
}
