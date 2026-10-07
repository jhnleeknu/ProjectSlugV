#include "ms5/video_control.h"
#include <cassert>
#include <iostream>
int main() {
    std::vector<std::uint8_t> ram(65536,0xaa);
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;std::uint16_t value=99;
    ram[0x4d90]=255;ram[0x4d91]=0xf7;
    assert(ms5::query_video_control(ram,value,error) && value==256);
    assert(ms5::set_video_control(ram,0,writes,error));
    assert(ram[0x4d90]==0 && ram[0x4d91]==255 && writes.size()==1);
    assert(writes[0].size==2 && writes[0].address==0x3c0006 && writes[0].value==255);
    assert(ms5::query_video_control(ram,value,error) && value==0);
    assert(ms5::set_video_control(ram,256,writes,error));
    assert(ms5::query_video_control(ram,value,error) && value==256 && writes[0].value==0xfff7);
    // Values larger than256 wrap the stored high byte, rather than clamp.
    assert(ms5::set_video_control(ram,257,writes,error));
    assert(ms5::query_video_control(ram,value,error) && value==1 && writes[0].value==0x00f7);
    assert(ms5::set_video_control(ram,65535,writes,error));
    assert(ms5::query_video_control(ram,value,error) && value==255 && writes[0].value==0xfef7);
    for(std::size_t i=0;i<ram.size();++i)if(i!=0x4d90 && i!=0x4d91)assert(ram[i]==0xaa);
    ram.resize(5);const std::vector<std::uint8_t> before=ram;
    value=99;
    assert(!ms5::query_video_control(ram,value,error) && value==99 && !error.empty());
    assert(!ms5::set_video_control(ram,0,writes,error) && ram==before && !error.empty());
    assert(writes.size()==1 && writes[0].size==2 && writes[0].address==0x3c0006 && writes[0].value==0xfef7);
    std::cout << "Video control word wrap, query range and failure preservation passed\n";
}
