#include "ms5/animation_resource.h"
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <unistd.h>

void check(bool value) { if (!value) { std::cerr << "animation resource test failed\n"; std::exit(1); } }
void put(std::vector<std::uint8_t>& bytes,std::size_t at,std::uint32_t value) {
    for (unsigned int i=0;i<4;++i) bytes[at+i]=static_cast<std::uint8_t>(value>>(i*8));
}
void save(const char* path,const std::vector<std::uint8_t>& bytes) {
    std::ofstream out(path,std::ios::binary|std::ios::trunc);
    out.write(reinterpret_cast<const char*>(&bytes[0]),bytes.size());out.close();check(!out.fail());
}
int main() {
    char path[]="/tmp/ms5-animation-resource-XXXXXX";int fd=mkstemp(path);check(fd>=0);close(fd);
    std::vector<std::uint8_t> bytes(33,0);bytes[0]='M';bytes[1]='S';bytes[2]='5';bytes[3]='A';
    put(bytes,4,1);put(bytes,8,1);put(bytes,12,0xfffff);put(bytes,16,0xfffff);put(bytes,20,1);bytes[32]=0x28;
    std::uint32_t crc=0xffffffffU;crc^=0x28;
    for (unsigned int i=0;i<8;++i) crc=(crc>>1)^((crc&1)?0xedb88320U:0);
    put(bytes,24,crc^0xffffffffU);
    ms5::AnimationResource result;std::string error;save(path,bytes);
    check(ms5::load_animation_resource(path,result,error));
    check(result.source_cpu_address==0xfffff && result.data.size()==1 && result.data[0]==0x28);
    const ms5::AnimationResource before=result;
    const unsigned int fields[]={0,4,8,12,16,20,24,28};
    for (unsigned int i=0;i<8;++i) {
        std::vector<std::uint8_t> bad=bytes;bad[fields[i]]^=1;save(path,bad);
        check(!ms5::load_animation_resource(path,result,error));
        check(result.data==before.data && result.source_cpu_address==before.source_cpu_address && result.source_rom_offset==before.source_rom_offset);
    }
    bytes.push_back(0);save(path,bytes);check(!ms5::load_animation_resource(path,result,error));
    bytes.resize(31);save(path,bytes);check(!ms5::load_animation_resource(path,result,error));
    check(std::remove(path)==0);
    std::cout << "animation_resource_test: passed\n";
}
