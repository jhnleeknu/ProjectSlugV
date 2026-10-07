#include "ms5/column_control.h"
namespace ms5 {
namespace {
unsigned int word(const std::vector<std::uint8_t>& ram,unsigned int at) {
    return (static_cast<unsigned int>(ram[at])<<8)|ram[at+1];
}
void emit(std::vector<VideoPortWrite>& writes,std::uint8_t size,std::uint32_t address,std::uint32_t value) {
    VideoPortWrite write;write.size=size;write.address=address;write.value=value;writes.push_back(write);
}
void refresh(std::vector<std::uint8_t>& ram,unsigned int at,std::uint32_t& d0,std::vector<VideoPortWrite>& writes) {
    if((ram[at+0x7a]&1U)==0) return;
    const bool ready=(ram[at+0x7a]&128U)!=0;
    ram[at+0x7a]&=127U;
    if(!ready) return;
    const unsigned int slot=word(ram,at+0x26);
    if((slot&0x8000U)!=0) return;
    unsigned int x=(word(ram,at+0x7c)<<7)&65535U;
    const unsigned int y=(word(ram,at+0x7e)<<7)&65535U;
    unsigned int x_address=(slot+0x8401U)&65535U;
    unsigned int y_address=(slot+0x8201U)&65535U;
    d0=(d0&0xffff0000U)|y;
    for(unsigned int i=0;i<32;++i) {
        const unsigned int test=(x+0x400U)&65535U;
        unsigned int column_y=y;
        if(test<0xa000U) column_y=(y+word(ram,at+0x3a+2*i))&65535U;
        emit(writes,4,0x3c0000,(x_address<<16)|x);
        x_address=(x_address+1U)&65535U;x=(x+0x800U)&65535U;
        emit(writes,4,0x3c0000,(y_address<<16)|column_y);
        y_address=(y_address+1U)&65535U;
    }
}
}
bool refresh_column_controls(std::vector<std::uint8_t>& ram,std::uint32_t object,
                             std::uint32_t& d0,std::vector<VideoPortWrite>& writes,std::string& error) {
    if(ram.size()!=65536U || object<0x100000U || object>0x10ff80U || (object&1U)!=0) {
        error="column control requires 64KiB RAM and an aligned 128-byte object";return false;
    }
    std::vector<std::uint8_t> candidate=ram;std::uint32_t next=d0;
    std::vector<VideoPortWrite> ports;
    refresh(candidate,object-0x100000U,next,ports);
    ram.swap(candidate);d0=next;writes.swap(ports);error.clear();return true;
}
bool refresh_scene_columns(std::vector<std::uint8_t>& ram,std::uint32_t& d0,
                           std::vector<VideoPortWrite>& writes,std::string& error) {
    if(ram.size()!=65536U) {error="scene columns require 64KiB RAM";return false;}
    std::vector<std::uint8_t> candidate=ram;std::uint32_t next=d0;
    std::vector<VideoPortWrite> ports;
    candidate[0x10]=0;candidate[0x11]=1;
    emit(ports,2,0x2ffff2,0x2000);emit(ports,2,0x2ffff0,0);
    const unsigned int objects[4]={0x9156,0xb1d6,0xd256,0xd2d6};
    for(unsigned int i=0;i<4;++i) refresh(candidate,objects[i],next,ports);
    candidate[0x10]=0;candidate[0x11]=0;
    emit(ports,2,0x2ffff2,0x1000);emit(ports,2,0x2ffff0,0);
    ram.swap(candidate);d0=next;writes.swap(ports);error.clear();return true;
}
}
