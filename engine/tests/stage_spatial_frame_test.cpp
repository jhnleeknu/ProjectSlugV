#include "ms5/stage_spatial_frame.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& r,unsigned int at,std::uint32_t v,unsigned int n=2) {
    for(unsigned int i=0;i<n;++i) r[at+i]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));
}
bool same(const ms5::SceneMapTransferState& a,const ms5::SceneMapTransferState& b) {
    for(unsigned int i=0;i<8;++i) if(a.d[i]!=b.d[i]) return false;
    for(unsigned int i=0;i<5;++i) if(a.a[i]!=b.a[i]) return false;
    return true;
}
}
int main() {
    std::vector<std::uint8_t> r(65536,0);std::vector<ms5::FixedDataResource> w;
    ms5::SceneMapTransferState s;s.a[0]=0x102000;s.a[3]=0xabcdef01;
    put(r,0x2026,0x106000,4);put(r,0x2020,128);put(r,0x2018,128);put(r,0x2014,32767);
    std::string e;
    // The X end overflows signed subtraction, but the native BLT is false.
    assert(ms5::step_stage_spatial_frame(r,0x46f52,w,s,2,e));
    assert(r[0xd67c]==1 && r[0xd67d]==1 && s.d[2]==65535 && s.a[3]==0xabcdef01);
    // Late category failure follows four valid WORD reads; all state rolls back.
    put(r,0x2026,0x10fff8,4);s.a[0]=0x102000;
    std::vector<std::uint8_t> old=r;ms5::SceneMapTransferState saved=s;
    assert(!ms5::step_stage_spatial_frame(r,0x46f52,w,s,2,e));assert(r==old && same(s,saved));
    // A full frame can alter its live counter through a wide spatial bitmap.
    // Subsequent unsupported source access must roll back even the initial clear.
    r.assign(65536,0);
    for(unsigned int i=0;i<8;++i) put(r,0xd61a-i*0x2c+0x26,0x80000000,4);
    put(r,0xd640,0x106000,4);put(r,0xd63a,128);put(r,0xd632,128);put(r,0x6004,256);
    old=r;saved=s;
    assert(!ms5::step_stage_spatial_frame(r,0x4701e,w,s,2,e));assert(r==old && same(s,saved));
    assert(!ms5::step_stage_spatial_frame(r,0,w,s,2,e));assert(r==old && same(s,saved));
    assert(!ms5::step_stage_spatial_frame(r,0x4701e,w,s,1,e));assert(r==old && same(s,saved));
    r.resize(65535);old=r;
    assert(!ms5::step_stage_spatial_frame(r,0x4701e,w,s,2,e));assert(r==old && same(s,saved));
    std::cout << "stage_spatial_frame_test passed\n";
}
