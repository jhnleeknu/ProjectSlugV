// Development-only batch differential: expected values are native binary rows.
// Row schema1: BE inputWORD/outputWORD,15u32,32-byte RAM hash,u16 trace,u8 writes.
#include "ms5/stage_counter.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
#include <cstring>
static unsigned int be(const unsigned char* p,unsigned int n) {
    unsigned int v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|p[i];return v;
}
static std::vector<std::uint8_t> read(const char* name) {
    std::ifstream f(name,std::ios::binary);return std::vector<std::uint8_t>((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());
}
int main(int argc,char** argv) {
    if(argc!=5)return 2;
    const std::vector<std::uint8_t> rows=read(argv[1]);
    std::vector<std::uint8_t> profiles[3];
    for(unsigned int i=0;i<3;++i){profiles[i]=read(argv[i+2]);if(profiles[i].size()!=65536)return 3;}
    if(rows.size()!=65536U*99U)return 4;
    const unsigned int seeds[]={0U,0xffffffffU,0x81231234U};
    for(unsigned int word=0;word<65536;++word) {
        const unsigned char* row=&rows[word*99U];if(be(row,2)!=word)return 5;
        std::vector<std::uint8_t> ram=profiles[word%3];
        ram[0xd683]=16;ram[0xfdb6]=1;ram[0xfdb7]=0;
        ram[0xd67e]=static_cast<std::uint8_t>(word>>8);ram[0xd67f]=static_cast<std::uint8_t>(word);
        std::vector<std::uint8_t> expected=ram;expected[0xd67e]=row[2];expected[0xd67f]=row[3];
        ms5::ObjectRestartState state;
        for(unsigned int i=0;i<15;++i) {
            const std::uint32_t value=seeds[word%3]+i*0x01010101U;
            if(i<8)state.d[i]=value;else state.a[i-8]=value;
        }
        state.a[5]=0x108000;std::string error="stale";
        if(!ms5::execute_stage_counter(ram,state,error)||!error.empty()||ram!=expected) {
            std::cerr<<"RAM/API failure word "<<word<<" "<<error<<"\n";return 6;
        }
        for(unsigned int i=0;i<15;++i) {
            const unsigned int actual=i<8?state.d[i]:state.a[i-8];
            if(actual!=be(row+4+i*4,4)){std::cerr<<"register failure word "<<word<<" index "<<i<<"\n";return 7;}
        }
    }
    std::cout<<"{\"cases\":65536,\"full_RAM_15_registers_equal\":true}\n";return 0;
}
